# ============================================================
# Resume Models — Data Shapes
# ============================================================
# Models define the SHAPE of data — what fields exist, what
# types they are, and which ones are required.
#
# CONCEPT: Pydantic Models
# ────────────────────────
# Pydantic is a validation library. When data comes in (from
# a user, API, database), Pydantic checks:
#   1. Are all required fields present?
#   2. Are the types correct? (string, number, list, etc.)
#   3. Do values meet constraints? (min length, max value, etc.)
#
# If anything is wrong, it raises a clear error BEFORE your
# code even sees the bad data. This prevents bugs.
#
# Think of it as a bouncer at a club — checks IDs at the door
# so you don't have to check inside.
# ============================================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ResumeSection(BaseModel):
    """
    A single section of a parsed resume.
    
    When we parse a PDF, we break it into meaningful sections
    (education, skills, experience, etc.) because:
    1. Different sections match different job requirements
    2. Smaller chunks = better embeddings
    3. We can show users WHICH part of their resume matched
    
    CONCEPT: Chunking for Embeddings
    ────────────────────────────────
    Embedding models work best on focused text (100-500 words).
    A full 3-page resume crammed into one embedding loses detail.
    But "Python, FastAPI, Docker, Kubernetes" as a skills chunk
    produces a very focused, accurate embedding.
    """
    section_type: str  # "skills", "education", "experience", "projects", "summary"
    content: str       # The actual text of that section


class ResumeCreate(BaseModel):
    """
    Data we expect when a user uploads a resume.
    The PDF file itself is sent separately as form data —
    this model only describes the metadata sent alongside it.
    """
    # Optional because we can extract the name from the PDF filename
    title: Optional[str] = Field(
        default=None,
        description="A label for this resume, e.g. 'Software Engineer Resume'"
    )


class ResumeResponse(BaseModel):
    """
    What we send BACK to the user after uploading a resume.
    
    CONCEPT: Request vs Response Models
    ────────────────────────────────────
    We use DIFFERENT models for input and output:
    - ResumeCreate = what the user SENDS us (minimal)
    - ResumeResponse = what we SEND BACK (enriched with IDs, dates, etc.)
    
    Why? Because:
    1. Users shouldn't send us the ID — WE generate it
    2. Users shouldn't send the upload date — WE set it
    3. We might want to hide internal fields from the response
    """
    id: str
    title: str
    file_name: str
    raw_text: str
    sections: list[ResumeSection]
    word_count: int
    has_embedding: bool
    created_at: str
    message: str


class ResumeListItem(BaseModel):
    """
    Shortened resume info for listing all resumes.
    We don't include the full text — that would be wasteful
    when you just want to see a list.
    """
    id: str
    title: str
    file_name: str
    word_count: int
    has_embedding: bool
    created_at: str
