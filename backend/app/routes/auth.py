# ============================================================
# Auth Routes — Register, Login, Profile, Applications
# ============================================================

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Header
from typing import Optional

from app.config.database import db
from app.models.user import (
    UserRegister, UserLogin, UserResponse, TokenResponse,
    ProfileUpdate, ApplicationUpdate, UserProfile, JobApplication,
)
from app.services.auth_service import hash_password, verify_password, create_token, verify_token

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def _format_user(doc: dict) -> UserResponse:
    """Convert MongoDB document to UserResponse."""
    profile_data = doc.get("profile", {})
    profile = UserProfile(**profile_data) if profile_data else UserProfile()

    apps_raw = doc.get("applications", [])
    applications = [JobApplication(**a) for a in apps_raw]

    return UserResponse(
        id=str(doc["_id"]),
        name=doc.get("name", ""),
        email=doc.get("email", ""),
        profile=profile,
        saved_jobs=doc.get("saved_jobs", []),
        applications=applications,
        created_at=doc.get("created_at", datetime.now(timezone.utc)).isoformat(),
    )


async def _get_current_user(authorization: str = "") -> dict:
    """Extract and verify user from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ", 1)[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    col = db.get_collection("users")
    try:
        user = await col.find_one({"_id": ObjectId(payload["sub"])})
    except Exception:
        raise HTTPException(status_code=401, detail="User not found")

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# ── Register ──────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse)
async def register(body: UserRegister):
    """Create a new account."""
    col = db.get_collection("users")

    # Check duplicate email
    existing = await col.find_one({"email": body.email.lower().strip()})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    if len(body.name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")

    # Create user document
    user_doc = {
        "name": body.name.strip(),
        "email": body.email.lower().strip(),
        "password_hash": hash_password(body.password),
        "profile": {},
        "saved_jobs": [],
        "applications": [],
        "created_at": datetime.now(timezone.utc),
    }

    result = await col.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id

    token = create_token(str(result.inserted_id), user_doc["email"])
    return TokenResponse(access_token=token, user=_format_user(user_doc))


# ── Login ─────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin):
    """Login with email and password."""
    col = db.get_collection("users")

    user = await col.find_one({"email": body.email.lower().strip()})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(str(user["_id"]), user["email"])
    return TokenResponse(access_token=token, user=_format_user(user))


# ── Get current user ──────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(authorization: Optional[str] = Header(default=None)):
    """Get current authenticated user."""
    user = await _get_current_user(authorization or "")
    return _format_user(user)


# ── Update profile ────────────────────────────────────────

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    body: ProfileUpdate,
    authorization: Optional[str] = Header(default=None),
):
    """Update user profile."""
    user = await _get_current_user(authorization or "")
    col = db.get_collection("users")

    updates: dict = {}
    if body.name:
        updates["name"] = body.name.strip()
    if body.profile:
        updates["profile"] = body.profile.model_dump()

    if updates:
        await col.update_one({"_id": user["_id"]}, {"$set": updates})
        user.update(updates)

    return _format_user(user)


# ── Save / unsave job ─────────────────────────────────────

@router.post("/saved-jobs/{job_id}")
async def toggle_saved_job(
    job_id: str,
    authorization: Optional[str] = Header(default=None),
):
    """Save or unsave a job."""
    user = await _get_current_user(authorization or "")
    col = db.get_collection("users")

    saved = user.get("saved_jobs", [])
    if job_id in saved:
        await col.update_one({"_id": user["_id"]}, {"$pull": {"saved_jobs": job_id}})
        return {"saved": False, "message": "Job removed from saved"}
    else:
        await col.update_one({"_id": user["_id"]}, {"$addToSet": {"saved_jobs": job_id}})
        return {"saved": True, "message": "Job saved!"}


# ── Track job application ─────────────────────────────────

@router.post("/applications", response_model=UserResponse)
async def add_application(
    body: ApplicationUpdate,
    authorization: Optional[str] = Header(default=None),
):
    """Add or update a job application."""
    user = await _get_current_user(authorization or "")
    col = db.get_collection("users")

    app_doc = {
        "job_id": body.job_id,
        "job_title": body.job_title,
        "company": body.company,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "status": body.status,
        "notes": body.notes,
    }

    # Remove existing application for same job
    await col.update_one(
        {"_id": user["_id"]},
        {"$pull": {"applications": {"job_id": body.job_id}}}
    )

    # Add new/updated
    await col.update_one(
        {"_id": user["_id"]},
        {"$push": {"applications": app_doc}}
    )

    updated = await col.find_one({"_id": user["_id"]})
    return _format_user(updated)


# ── Delete application ────────────────────────────────────

@router.delete("/applications/{job_id}", response_model=UserResponse)
async def remove_application(
    job_id: str,
    authorization: Optional[str] = Header(default=None),
):
    """Remove a job application."""
    user = await _get_current_user(authorization or "")
    col = db.get_collection("users")

    await col.update_one(
        {"_id": user["_id"]},
        {"$pull": {"applications": {"job_id": job_id}}}
    )

    updated = await col.find_one({"_id": user["_id"]})
    return _format_user(updated)
