# ============================================================
# User Model — MongoDB document schema for user accounts
# ============================================================

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserProfile(BaseModel):
    phone: str = ""
    location: str = ""
    skills: list[str] = []
    preferred_job_titles: list[str] = []
    preferred_locations: list[str] = []
    bio: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""


class JobApplication(BaseModel):
    job_id: str
    job_title: str = ""
    company: str = ""
    applied_at: str = ""
    status: str = "applied"  # applied | interviewing | offered | rejected | withdrawn
    notes: str = ""


class UserRegister(BaseModel):
    name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    profile: UserProfile = UserProfile()
    saved_jobs: list[str] = []
    applications: list[JobApplication] = []
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    profile: Optional[UserProfile] = None


class ApplicationUpdate(BaseModel):
    job_id: str
    job_title: str = ""
    company: str = ""
    status: str = "applied"
    notes: str = ""
