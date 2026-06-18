# ============================================================
# Match Models — Data Shapes for Job-Resume Matches
# ============================================================
# A "match" is the result of comparing a resume against a job.
# It contains:
#   - Similarity score (from vector math)
#   - AI analysis (from LLM deep reasoning)
#   - Generated cover letter (tailored to this specific job)
#
# CONCEPT: Multi-Signal Scoring
# ─────────────────────────────
# We don't rely on a single score. We combine multiple signals:
#   1. Vector similarity (embedding math) → broad relevance
#   2. Skill match score (LLM analysis) → specific requirement fit
#   3. Experience fit (LLM analysis) → seniority alignment
#   4. Overall score (weighted combination) → final ranking
#
# This is more robust than any single method alone.
# ============================================================

from typing import Optional

from pydantic import BaseModel, Field


class MatchAnalysis(BaseModel):
    """
    Deep analysis produced by the matching agent (LLM).
    
    This is the LLM's "reasoning" about why a job does or
    doesn't fit the candidate. Much richer than a simple score.
    """
    skill_match_score: float = Field(0, description="0-10: how many required skills the candidate has")
    experience_fit_score: float = Field(0, description="0-10: does experience level match")
    education_fit_score: float = Field(0, description="0-10: does education match")
    overall_score: float = Field(0, description="0-10: overall fit considering everything")
    matching_skills: list[str] = Field(default_factory=list, description="Skills the candidate HAS that the job NEEDS")
    missing_skills: list[str] = Field(default_factory=list, description="Skills the job NEEDS but candidate LACKS")
    strong_points: list[str] = Field(default_factory=list, description="Where the candidate exceeds requirements")
    concerns: list[str] = Field(default_factory=list, description="Potential issues or gaps")
    recommendation: str = Field("", description="One-line recommendation: apply/consider/skip")
    reasoning: str = Field("", description="Brief explanation of the scoring")


class MatchResult(BaseModel):
    """Complete match result combining vector similarity + LLM analysis."""
    job_id: str
    resume_id: str
    similarity_score: float = Field(description="0-1: cosine similarity between embeddings")
    analysis: Optional[MatchAnalysis] = None
    cover_letter: Optional[str] = None
    created_at: str = ""


class MatchResponse(BaseModel):
    """What we send to the frontend for display."""
    id: str
    job_id: str
    resume_id: str
    similarity_score: float
    analysis: Optional[MatchAnalysis] = None
    cover_letter: Optional[str] = None
    created_at: str
    # Job info (embedded so frontend doesn't need a second call)
    job_title: str = ""
    job_company: str = ""
    job_location: str = ""
    job_url: str = ""
    job_source: str = ""


class MatchRequest(BaseModel):
    """What the user sends to trigger matching."""
    resume_id: str
    top_k: int = Field(default=15, ge=1, le=50, description="Number of top matches to return")
    generate_cover_letters: bool = Field(default=True, description="Generate cover letters for top matches")
    cover_letter_count: int = Field(default=3, ge=1, le=10, description="How many cover letters to generate")
