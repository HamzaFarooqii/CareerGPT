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
    """A job listing as scraped — before AI processing."""
    title: str
    company: str
    location: str = ""
    description: str
    salary_range: str = ""
    job_type: str = ""
    experience_required: str = ""
    posted_date: str = ""         # Raw string as found on site ("2 days ago", "Jun 15")
    url: str                      # Direct link to the job posting
    source: str                   # "rozee.pk", "greenhouse", "lever", etc.
    canonical_url: str = ""       # Normalized URL for deduplication
    company_url: str = ""         # Company homepage


class JobExtracted(BaseModel):
    """Structured data extracted by LLM from raw description."""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_years_min: int = 0
    experience_years_max: int = 0
    education: str = ""
    job_type_normalized: str = ""
    seniority_level: str = ""
    industry: str = ""
    key_responsibilities: list[str] = Field(default_factory=list)


class SalaryNormalized(BaseModel):
    """Normalized salary information."""
    min_amount: Optional[int] = None
    max_amount: Optional[int] = None
    currency: str = "USD"
    period: str = "yearly"        # "yearly" | "monthly" | "hourly"
    raw: str = ""


class JobResponse(BaseModel):
    """Full job details sent to frontend."""
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
    canonical_url: str = ""
    company_url: str = ""
    extracted: Optional[JobExtracted] = None
    salary_normalized: Optional[SalaryNormalized] = None
    has_embedding: bool = False
    is_active: bool = True
    freshness_score: float = 1.0   # 0.0 (expired/old) → 1.0 (posted today)
    days_old: Optional[int] = None
    posted_at_parsed: Optional[str] = None
    created_at: str


class JobListItem(BaseModel):
    """Compact job listing for list/card views."""
    id: str
    title: str
    company: str
    location: str
    salary_range: str
    job_type: str
    source: str
    url: str = ""
    canonical_url: str = ""
    company_url: str = ""
    has_embedding: bool = False
    is_active: bool = True
    freshness_score: float = 1.0
    days_old: Optional[int] = None
    posted_date: str = ""
    created_at: str


class ScrapeResult(BaseModel):
    """Summary of a single scraping run per source."""
    source: str
    jobs_found: int
    jobs_new: int
    jobs_duplicate: int
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float


class ScrapeStartedResponse(BaseModel):
    """
    What POST /api/jobs/scrape actually returns: an immediate acknowledgement,
    not per-source results — scraping runs in the background afterward (so a
    slow scrape can't trip Render/Vercel's request timeout). Per-source
    ScrapeResult stats are only ever logged server-side, never returned here;
    the frontend should re-fetch the job list after a short delay instead of
    expecting counts in this response.
    """
    status: str
    message: str
