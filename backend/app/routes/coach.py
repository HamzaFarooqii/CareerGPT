# ============================================================
# Career Coach Routes — Powered by ai_client (multi-provider)
# ============================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.ai_client import ai_generate

router = APIRouter(prefix="/api/coach", tags=["Career Coach"])

COACH_SYSTEM = """You are CareerPilot AI — an expert career coach and resume specialist with 15+ years of experience helping professionals land jobs at top tech companies.

You are helpful, specific, actionable, and encouraging. You give concrete, personalized advice — not generic tips. When reviewing resumes, you are detailed. When preparing for interviews, you give real questions and sample answers. You communicate in a professional but friendly tone.

Always format your responses clearly with bullet points, sections, and examples where relevant."""


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ResumeReviewRequest(BaseModel):
    resume_text: str
    target_role: str = ""


class InterviewPrepRequest(BaseModel):
    job_title: str
    job_description: str = ""
    resume_text: str = ""


class RoadmapRequest(BaseModel):
    current_skills: list[str]
    target_role: str
    years_experience: int = 0


class ATSRequest(BaseModel):
    resume_text: str
    job_description: str


@router.post("/chat")
async def career_chat(body: ChatRequest):
    """Conversational AI career coach."""
    try:
        history_text = ""
        if body.history:
            for msg in body.history[-6:]:
                role = "Career Coach" if msg.get("role") == "ai" else "User"
                history_text += f"\n{role}: {msg.get('content', '')}"

        prompt = f"""Previous conversation:{history_text}

User: {body.message}

Career Coach:"""

        reply = await ai_generate(prompt, system=COACH_SYSTEM)
        return {"reply": reply, "role": "ai"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume-review")
async def review_resume(body: ResumeReviewRequest):
    """Get detailed AI feedback on a resume."""
    try:
        target = f" for a {body.target_role} position" if body.target_role else ""
        prompt = f"""Perform a detailed resume review{target}. Analyze this resume and provide:

1. **Overall Score** (out of 10) with brief justification
2. **Strengths** (3-5 specific strong points)
3. **Areas for Improvement** (3-5 specific weaknesses with fixes)
4. **Missing Sections** (what's absent that should be added)
5. **Keyword Optimization** (important keywords missing for ATS)
6. **Action Items** (prioritized list of changes to make)

Resume:
{body.resume_text[:3000]}

Provide specific, actionable feedback:"""

        feedback = await ai_generate(prompt, system=COACH_SYSTEM)
        return {"feedback": feedback, "target_role": body.target_role}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interview-prep")
async def interview_prep(body: InterviewPrepRequest):
    """Generate tailored interview questions and answers."""
    try:
        resume_context = f"\n\nCandidate's background:\n{body.resume_text[:1500]}" if body.resume_text else ""
        job_context = f"\n\nJob Description:\n{body.job_description[:1000]}" if body.job_description else ""

        prompt = f"""Generate a comprehensive interview preparation guide for a {body.job_title} role.{job_context}{resume_context}

Include:
1. **Top 5 Behavioral Questions** (STAR format) with sample answers
2. **Top 5 Technical Questions** with detailed answers
3. **Questions to Ask the Interviewer** (5 impressive questions)
4. **Red Flags to Avoid**
5. **Salary Negotiation Tips** for this role

Make answers specific and impressive:"""

        guide = await ai_generate(prompt, system=COACH_SYSTEM)
        return {"prep_guide": guide, "job_title": body.job_title}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/roadmap")
async def career_roadmap(body: RoadmapRequest):
    """Generate a personalized career roadmap."""
    try:
        skills_str = ", ".join(body.current_skills) if body.current_skills else "general tech skills"

        prompt = f"""Create a detailed 6-month career roadmap for someone wanting to become a {body.target_role}.

Current skills: {skills_str}
Years of experience: {body.years_experience}

Format:
**Month 1-2: Foundation** — skills, projects, certs
**Month 3-4: Intermediate** — advanced topics, portfolio
**Month 5-6: Job Ready** — application strategy, interviews
**Key Resources:** free courses, books, communities
**Skill Gap Analysis:** what's missing, what to learn first

Be specific with resources and timelines:"""

        roadmap = await ai_generate(prompt, system=COACH_SYSTEM)
        return {
            "roadmap": roadmap,
            "target_role": body.target_role,
            "current_skills": body.current_skills,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ats-score")
async def ats_score(body: ATSRequest):
    """Calculate ATS compatibility score."""
    try:
        prompt = f"""You are an ATS (Applicant Tracking System) expert. Analyze this resume against the job description.

Job Description:
{body.job_description[:2000]}

Resume:
{body.resume_text[:2000]}

Provide:
1. **ATS Score**: X/100
2. **Keyword Match Rate**: X%
3. **Matched Keywords**: [list]
4. **Missing Critical Keywords**: [list]
5. **Format Issues**: [ATS-unfriendly formatting problems]
6. **Recommendations**: [specific fixes]"""

        analysis = await ai_generate(prompt, system=COACH_SYSTEM)
        return {
            "analysis": analysis,
            "resume_length": len(body.resume_text),
            "jd_length": len(body.job_description),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
