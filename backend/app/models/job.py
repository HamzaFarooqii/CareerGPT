# ============================================================
# Job Models — Data Shapes for Scraped Jobs
# ============================================================
# These models define what a "job" looks like in our system.
#
# A job goes through a pipeline:
#   1. RAW: Scraped from website (messy HTML, inconsistent fields)
#   2. STRUCTURED: LLM extracts clean data (skills, salary, etc.)
#   3. EMBEDDED: Vector embedding generated for matching
#
# We have separate models for each stage because the data
# evolves as it moves through the pipeline.
# ============================================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JobRaw(BaseModel):
    """
    A job listing as scraped from the website — before any AI processing.
    
    This is the RAWEST form of data. Some fields might be missing,
    formatting is inconsistent, skills are buried in free text.
    
    CONCEPT: Why keep raw data?
    ───────────────────────────
    Always save the original. If your LLM extraction has a bug,
    you can re-run extraction on the raw data without re-scraping.
    In data engineering, this is called "keeping the raw layer."
    """
    title: str
    company: str
    location: str = ""
    description: str                  # Full job description (raw text/HTML)
    salary_range: str = ""            # "80k-120k" or "" if not listed
    job_type: str = ""                # "Full-time", "Part-time", "Contract"
    experience_required: str = ""     # "2-3 years" or "Fresh" — raw text
    posted_date: str = ""
    url: str                          # Direct link to the job posting
    source: str                       # "rozee.pk", "indeed.pk", etc.


class JobExtracted(BaseModel):
    """
    Structured data that the LLM extracts from the raw description.
    
    This is the CLEAN version — normalized, consistent, ready for
    comparison against resumes.
    
    CONCEPT: Structured Extraction
    ──────────────────────────────
    The raw description says: "We need someone who knows React,
    preferably with Redux experience, 2+ years, MERN stack"
    
    The LLM extracts:
    {
        "required_skills": ["React", "JavaScript", "MongoDB", "Express", "Node.js"],
        "preferred_skills": ["Redux"],
        "experience_years_min": 2,
        "education": "Bachelor's in CS or related"
    }
    
    Now we can PROGRAMMATICALLY compare this against a resume.
    "Does the candidate know React?" becomes a simple list lookup
    instead of fuzzy text matching.
    """
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_years_min: int = 0
    experience_years_max: int = 0
    education: str = ""
    job_type_normalized: str = ""     # "full-time" | "part-time" | "contract" | "remote" | "internship"
    seniority_level: str = ""         # "intern" | "junior" | "mid" | "senior" | "lead"
    industry: str = ""
    key_responsibilities: list[str] = Field(default_factory=list)


class JobResponse(BaseModel):
    """What we send back when listing/viewing jobs."""
    id: str
    title: str
    company: str
    location: str
    description: str
    salary_range: str
    job_type: str
    experience_required: str
    posted_date: str
    url: str
    source: str
    extracted: Optional[JobExtracted] = None
    has_embedding: bool = False
    created_at: str


class JobListItem(BaseModel):
    """Compact job listing for list views."""
    id: str
    title: str
    company: str
    location: str
    salary_range: str
    job_type: str
    source: str
    has_embedding: bool = False
    created_at: str


class ScrapeResult(BaseModel):
    """Summary of a scraping run."""
    source: str
    jobs_found: int
    jobs_new: int
    jobs_duplicate: int
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float
