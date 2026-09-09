# ============================================================
# PDF Routes — Resume & Cover Letter PDF Download Endpoints
# ============================================================

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from app.services.pdf_service import (
    generate_resume_pdf,
    generate_resume_pdf_from_text,
    generate_cover_letter_pdf,
)

router = APIRouter(prefix="/api/pdf", tags=["PDF Generation"])


class ResumePDFRequest(BaseModel):
    """Request to generate a structured resume PDF."""
    name: str
    job_title: str = ""
    contact: dict = {}
    summary: str = ""
    skills: list[str] = []
    experience: list[dict] = []
    education: list[dict] = []
    projects: list[dict] = []
    certifications: list[str] = []
    matched_keywords: list[str] = []


class ResumeTextPDFRequest(BaseModel):
    """Request to generate a PDF from raw ATS-optimized resume text."""
    optimized_text: str
    name: str = "Candidate"
    job_title: str = ""


class CoverLetterPDFRequest(BaseModel):
    """Request to generate a cover letter PDF."""
    cover_letter_text: str
    name: str
    company: str
    job_title: str
    contact: Optional[dict] = None


@router.post("/resume")
async def download_resume_pdf(body: ResumePDFRequest):
    """
    Generate and return a professional ATS-compliant resume PDF.
    Returns the PDF file as a binary response (Content-Disposition: attachment).
    """
    try:
        pdf_bytes = generate_resume_pdf(
            name=body.name,
            contact=body.contact,
            summary=body.summary,
            skills=body.skills,
            experience=body.experience,
            education=body.education,
            projects=body.projects,
            certifications=body.certifications,
            job_title=body.job_title,
            matched_keywords=body.matched_keywords,
        )

        filename = f"{body.name.replace(' ', '_')}_Resume.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.post("/resume-from-text")
async def download_resume_pdf_from_text(body: ResumeTextPDFRequest):
    """
    Generate a resume PDF from raw ATS-optimized text.
    The text is automatically parsed into sections.
    """
    try:
        pdf_bytes = generate_resume_pdf_from_text(
            optimized_text=body.optimized_text,
            name=body.name,
            job_title=body.job_title,
        )

        filename = f"{body.name.replace(' ', '_')}_ATS_Resume.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.post("/cover-letter")
async def download_cover_letter_pdf(body: CoverLetterPDFRequest):
    """Generate and return a professional cover letter PDF."""
    try:
        pdf_bytes = generate_cover_letter_pdf(
            cover_letter_text=body.cover_letter_text,
            name=body.name,
            company=body.company,
            job_title=body.job_title,
            contact=body.contact,
        )

        filename = f"{body.name.replace(' ', '_')}_{body.company}_Cover_Letter.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cover letter PDF failed: {str(e)}")
