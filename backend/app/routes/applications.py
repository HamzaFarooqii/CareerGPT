# ============================================================
# Applications Routes — Job Application Tracker API
# ============================================================

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId

from app.config.database import db
from app.models.application import (
    ApplicationPackage,
    CreateApplicationRequest,
    UpdateApplicationStatusRequest,
    VALID_STATUSES,
)

router = APIRouter(prefix="/api/applications", tags=["Applications"])


def _doc_to_package(doc: dict) -> ApplicationPackage:
    """Convert MongoDB document to ApplicationPackage."""
    created = doc.get("created_at", datetime.now(timezone.utc))
    updated = doc.get("updated_at", created)
    applied = doc.get("applied_at")

    return ApplicationPackage(
        id=str(doc["_id"]),
        user_id=doc.get("user_id"),
        job_id=doc.get("job_id", ""),
        resume_id=doc.get("resume_id", ""),
        job_title=doc.get("job_title", ""),
        company=doc.get("company", ""),
        job_url=doc.get("job_url", ""),
        canonical_url=doc.get("canonical_url", ""),
        company_url=doc.get("company_url", ""),
        status=doc.get("status", "draft"),
        ats_score=doc.get("ats_score"),
        match_score=doc.get("match_score"),
        cover_letter_text=doc.get("cover_letter_text", ""),
        optimized_resume_text=doc.get("optimized_resume_text", ""),
        notes=doc.get("notes", ""),
        applied_at=applied.isoformat() if applied and hasattr(applied, "isoformat") else str(applied) if applied else None,
        created_at=created.isoformat() if hasattr(created, "isoformat") else str(created),
        updated_at=updated.isoformat() if hasattr(updated, "isoformat") else str(updated),
    )


@router.post("", response_model=ApplicationPackage)
async def create_application(body: CreateApplicationRequest):
    """Save a new job application package to the tracker."""
    col = db.get_collection("applications")
    now = datetime.now(timezone.utc)

    doc = {
        "job_id": body.job_id,
        "resume_id": body.resume_id,
        "job_title": body.job_title,
        "company": body.company,
        "job_url": body.job_url,
        "canonical_url": body.canonical_url,
        "company_url": body.company_url,
        "status": "draft",
        "ats_score": body.ats_score,
        "match_score": body.match_score,
        "cover_letter_text": body.cover_letter_text,
        "optimized_resume_text": body.optimized_resume_text,
        "notes": body.notes,
        "applied_at": None,
        "created_at": now,
        "updated_at": now,
    }

    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _doc_to_package(doc)


@router.get("", response_model=list[ApplicationPackage])
async def list_applications(
    status: str = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
):
    """List all saved applications, optionally filtered by status."""
    col = db.get_collection("applications")

    query: dict = {}
    if status and status in VALID_STATUSES:
        query["status"] = status

    cursor = col.find(query).sort("updated_at", -1).skip(skip).limit(limit)
    results = []
    async for doc in cursor:
        results.append(_doc_to_package(doc))
    return results


@router.get("/{app_id}", response_model=ApplicationPackage)
async def get_application(app_id: str):
    """Get a single application by ID."""
    col = db.get_collection("applications")
    try:
        doc = await col.find_one({"_id": ObjectId(app_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid application ID")
    if not doc:
        raise HTTPException(status_code=404, detail="Application not found")
    return _doc_to_package(doc)


@router.patch("/{app_id}/status", response_model=ApplicationPackage)
async def update_application_status(app_id: str, body: UpdateApplicationStatusRequest):
    """Update the status of an application (e.g., draft → applied → interviewing)."""
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {VALID_STATUSES}")

    col = db.get_collection("applications")
    now = datetime.now(timezone.utc)

    update: dict = {"status": body.status, "updated_at": now}
    if body.notes is not None:
        update["notes"] = body.notes
    if body.status == "applied":
        update["applied_at"] = now

    try:
        result = await col.find_one_and_update(
            {"_id": ObjectId(app_id)},
            {"$set": update},
            return_document=True,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid application ID")

    if not result:
        raise HTTPException(status_code=404, detail="Application not found")

    return _doc_to_package(result)


@router.delete("/{app_id}")
async def delete_application(app_id: str):
    """Delete an application from the tracker."""
    col = db.get_collection("applications")
    try:
        result = await col.delete_one({"_id": ObjectId(app_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid application ID")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"message": "Application deleted"}


@router.get("/stats/summary")
async def get_application_stats():
    """Return application counts by status for dashboard display."""
    col = db.get_collection("applications")
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cursor = col.aggregate(pipeline)
    by_status: dict = {}
    async for doc in cursor:
        by_status[doc["_id"]] = doc["count"]

    total = sum(by_status.values())
    return {"total": total, "by_status": by_status}
