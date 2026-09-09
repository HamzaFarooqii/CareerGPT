# ============================================================
# Admin Routes — System Management & Quality Control
# ============================================================

from fastapi import APIRouter, Query
from app.config.database import db
from app.services.verification_service import (
    verify_jobs_batch,
    cleanup_stale_jobs,
    recompute_freshness_scores,
)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.post("/verify-jobs")
async def run_job_verification(
    limit: int = Query(default=100, ge=10, le=500, description="Max jobs to verify per run")
):
    """HEAD-check job URLs and mark dead ones as inactive."""
    result = await verify_jobs_batch(limit=limit)
    return {
        "checked": result.checked,
        "still_active": result.still_active,
        "marked_inactive": result.marked_inactive,
        "errors": result.errors,
        "duration_seconds": result.duration_seconds,
    }


@router.post("/cleanup-stale")
async def cleanup_old_jobs(
    older_than_days: int = Query(default=30, ge=7, le=180)
):
    """Delete jobs older than N days that are marked inactive."""
    deleted = await cleanup_stale_jobs(older_than_days=older_than_days)
    return {"deleted": deleted, "older_than_days": older_than_days}


@router.post("/recompute-freshness")
async def trigger_freshness_recompute():
    """Recompute freshness scores for all active jobs."""
    updated = await recompute_freshness_scores()
    return {"updated": updated, "message": "Freshness scores recomputed successfully"}


@router.get("/stats")
async def get_quality_stats():
    """Return database quality metrics for the dashboard."""
    jobs_col = db.get_collection("jobs")
    resumes_col = db.get_collection("resumes")
    matches_col = db.get_collection("matches")

    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    one_week_ago = now - timedelta(days=7)
    one_day_ago = now - timedelta(days=1)

    total_jobs = await jobs_col.count_documents({})
    active_jobs = await jobs_col.count_documents({"is_active": {"$ne": False}})
    inactive_jobs = total_jobs - active_jobs
    fresh_jobs = await jobs_col.count_documents({
        "created_at": {"$gte": one_day_ago},
        "is_active": {"$ne": False},
    })
    week_jobs = await jobs_col.count_documents({
        "created_at": {"$gte": one_week_ago},
        "is_active": {"$ne": False},
    })
    embedded_jobs = await jobs_col.count_documents({"has_embedding": True})
    total_resumes = await resumes_col.count_documents({})
    total_matches = await matches_col.count_documents({})

    # Jobs by source
    pipeline = [
        {"$match": {"is_active": {"$ne": False}}},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    source_cursor = jobs_col.aggregate(pipeline)
    jobs_by_source = {}
    async for doc in source_cursor:
        jobs_by_source[doc["_id"]] = doc["count"]

    embedding_coverage = round(embedded_jobs / max(active_jobs, 1) * 100, 1)

    return {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "inactive_jobs": inactive_jobs,
        "fresh_today": fresh_jobs,
        "added_this_week": week_jobs,
        "embedding_coverage_pct": embedding_coverage,
        "total_resumes": total_resumes,
        "total_matches": total_matches,
        "jobs_by_source": jobs_by_source,
    }
