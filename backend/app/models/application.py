# ============================================================
# Application Model — Job Application Tracker
# ============================================================

from typing import Optional
from pydantic import BaseModel, Field


class ApplicationPackage(BaseModel):
    """A stored job application with all generated assets."""
    id: str = ""
    user_id: Optional[str] = None
    job_id: str = ""
    resume_id: str = ""
    job_title: str
    company: str
    job_url: str = ""
    canonical_url: str = ""
    company_url: str = ""
    status: str = "draft"               # draft | applied | interviewing | offered | rejected | withdrawn
    ats_score: Optional[int] = None
    match_score: Optional[float] = None
    cover_letter_text: str = ""
    optimized_resume_text: str = ""
    notes: str = ""
    applied_at: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class CreateApplicationRequest(BaseModel):
    """Request body for creating a new application package."""
    job_id: str = ""
    resume_id: str = ""
    job_title: str
    company: str
    job_url: str = ""
    canonical_url: str = ""
    company_url: str = ""
    cover_letter_text: str = ""
    optimized_resume_text: str = ""
    ats_score: Optional[int] = None
    match_score: Optional[float] = None
    notes: str = ""


class UpdateApplicationStatusRequest(BaseModel):
    """Request to update application status."""
    status: str  # draft | applied | interviewing | offered | rejected | withdrawn
    notes: Optional[str] = None


VALID_STATUSES = {"draft", "applied", "interviewing", "offered", "rejected", "withdrawn"}
