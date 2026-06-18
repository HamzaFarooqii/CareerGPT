# ============================================================
# Apply Agent Routes — Powered by ai_client (multi-provider)
# ============================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.ai_client import ai_generate

router = APIRouter(prefix="/api/apply", tags=["Apply Agent"])


class CoverLetterRequest(BaseModel):
    resume_text: str
    job_title: str
    company: str
    job_description: str
    tone: str = "professional"


class ATSResumeRequest(BaseModel):
    resume_text: str
    job_title: str
    job_description: str


class ScreeningRequest(BaseModel):
    questions: list[str]
    resume_text: str
    job_title: str
    company: str = ""


@router.post("/cover-letter")
async def generate_cover_letter(body: CoverLetterRequest):
    """Generate a personalized, ATS-optimized cover letter."""
    try:
        tone_desc = {
            "professional": "formal and polished",
            "enthusiastic": "energetic and passionate",
            "concise": "brief and impactful (under 250 words)",
        }.get(body.tone, "professional and polished")

        prompt = f"""Write a {tone_desc} cover letter for this application.

Job: {body.job_title} at {body.company}

Job Description:
{body.job_description[:1500]}

Candidate's Resume:
{body.resume_text[:2000]}

Requirements:
- Address hiring manager professionally
- Strong opening hook
- 2-3 paragraphs connecting experience to requirements
- Specific achievements with metrics
- Strong closing with clear call to action

Write only the cover letter text:"""

        letter = await ai_generate(prompt)
        return {
            "cover_letter": letter,
            "job_title": body.job_title,
            "company": body.company,
            "tone": body.tone,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ats-resume")
async def generate_ats_resume(body: ATSResumeRequest):
    """Rewrite resume to be ATS-optimized for a specific job."""
    try:
        prompt = f"""Rewrite this resume to be perfectly optimized for the following job.

Target Job: {body.job_title}

Job Description:
{body.job_description[:1500]}

Original Resume:
{body.resume_text[:2000]}

Instructions:
1. Mirror keywords from the job description naturally
2. Reorder bullet points to prioritize relevant experience
3. Quantify achievements wherever possible
4. Use standard section headers (Summary, Experience, Skills, Education)
5. Remove irrelevant information
6. Ensure all required skills appear in the resume
7. Keep formatting ATS-friendly (no tables, no graphics)

Write the complete optimized resume:"""

        optimized = await ai_generate(prompt)
        return {"optimized_resume": optimized, "job_title": body.job_title}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screening-answers")
async def generate_screening_answers(body: ScreeningRequest):
    """Auto-generate answers to application screening questions."""
    try:
        questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(body.questions)])

        prompt = f"""Help a candidate answer these job application screening questions.

Role: {body.job_title} at {body.company or 'the company'}

Candidate's Background:
{body.resume_text[:1500]}

Screening Questions:
{questions_text}

For each question provide:
- A compelling, honest answer highlighting strengths
- Concrete examples from their background
- 50-150 words per answer

Format as:
**Question 1:** [restate question]
**Answer:** [your answer]

[repeat for each question]"""

        answers = await ai_generate(prompt)
        return {
            "answers": answers,
            "question_count": len(body.questions),
            "job_title": body.job_title,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
