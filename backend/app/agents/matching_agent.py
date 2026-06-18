# ============================================================
# Matching Agent — Deep AI Analysis of Job-Resume Fit
# ============================================================
# This is the MOST IMPORTANT agent in the system.
#
# Vector similarity tells us "these texts are related."
# This agent tells us "here's WHY this job fits (or doesn't)."
#
# CONCEPT: Why Not Just Use Embeddings?
# ─────────────────────────────────────
# Embedding similarity catches SEMANTIC relevance but misses
# LOGICAL requirements. Example:
#
#   Resume: "Python, FastAPI, Docker — 0 years experience"
#   Job: "Python, FastAPI, Docker — 5 years required"
#   
#   Embedding similarity: 0.95 (very high! skills match!)
#   But you DON'T qualify. The LLM catches this.
#
# The matching agent does what embeddings can't:
#   1. Checks specific skill coverage (have 7/10 required skills)
#   2. Evaluates experience requirements (needs 5 years, you have 0)
#   3. Considers education match (needs MS, you have BS)
#   4. Assesses career growth (will this job advance your career?)
#   5. Gives actionable advice (what to highlight in application)
# ============================================================

import json

from app.services.ai_client import ai_generate
from app.models.match import MatchAnalysis

MATCHING_SYSTEM_PROMPT = """You are an expert career advisor and job matching specialist. 
Your task is to deeply analyze how well a candidate's resume matches a specific job posting.

Given a RESUME and a JOB DESCRIPTION, produce a detailed analysis as JSON:

{
  "skill_match_score": 0-10,
  "experience_fit_score": 0-10,
  "education_fit_score": 0-10,
  "overall_score": 0-10,
  "matching_skills": ["skills the candidate HAS that the job NEEDS"],
  "missing_skills": ["skills the job NEEDS but candidate LACKS"],
  "strong_points": ["where the candidate exceeds or uniquely fits"],
  "concerns": ["potential issues: experience gaps, missing quals, etc."],
  "recommendation": "APPLY / CONSIDER / SKIP — one word + brief reason",
  "reasoning": "2-3 sentences explaining the overall assessment"
}

SCORING GUIDE:
- 9-10: Exceptional match, candidate exceeds most requirements
- 7-8: Strong match, candidate meets most requirements
- 5-6: Partial match, some gaps but potentially viable
- 3-4: Weak match, significant gaps
- 1-2: Poor match, fundamental misalignment

RULES:
1. Be honest and specific. Don't inflate scores.
2. For a fresh graduate with relevant projects, experience_fit can be 4-6 even with 0 years
3. Consider project experience as partial real experience
4. Missing 1-2 non-critical skills shouldn't tank the score
5. Factor in growth potential — can the candidate learn quickly?
6. Return ONLY valid JSON, no markdown, no explanations outside JSON.
"""


async def analyze_match(resume_text: str, job_title: str, job_description: str,
                         job_requirements: dict | None = None) -> MatchAnalysis:
    """
    Use Gemini to deeply analyze how well a resume matches a job.
    
    Args:
        resume_text: Full resume text
        job_title: Job title
        job_description: Full job description
        job_requirements: Extracted requirements (from Phase 2 extraction agent)
    
    Returns:
        MatchAnalysis with scores, matching/missing skills, and recommendation
    """
    # Build context about the job requirements if we have extracted data
    requirements_context = ""
    if job_requirements:
        req_skills = job_requirements.get("required_skills", [])
        pref_skills = job_requirements.get("preferred_skills", [])
        exp_min = job_requirements.get("experience_years_min", 0)
        exp_max = job_requirements.get("experience_years_max", 0)
        education = job_requirements.get("education", "")
        seniority = job_requirements.get("seniority_level", "")

        requirements_context = f"""
EXTRACTED JOB REQUIREMENTS:
- Required Skills: {', '.join(req_skills) if req_skills else 'Not specified'}
- Preferred Skills: {', '.join(pref_skills) if pref_skills else 'None'}
- Experience: {exp_min}-{exp_max} years
- Education: {education or 'Not specified'}
- Seniority Level: {seniority or 'Not specified'}
"""

    user_message = f"""Analyze this job-resume match:

=== RESUME ===
{resume_text[:3000]}

=== JOB: {job_title} ===
{job_description[:2000]}
{requirements_context}

Produce your analysis as JSON."""

    try:
        result_text = await ai_generate(user_message, system=MATCHING_SYSTEM_PROMPT)
        result_text = result_text.strip()
        # Strip markdown code blocks if model wraps JSON
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            result_text = "\n".join(l for l in lines if not l.startswith("```")).strip()

        data = json.loads(result_text)

        analysis = MatchAnalysis(
            skill_match_score=min(10, max(0, float(data.get("skill_match_score", 0)))),
            experience_fit_score=min(10, max(0, float(data.get("experience_fit_score", 0)))),
            education_fit_score=min(10, max(0, float(data.get("education_fit_score", 0)))),
            overall_score=min(10, max(0, float(data.get("overall_score", 0)))),
            matching_skills=data.get("matching_skills", []),
            missing_skills=data.get("missing_skills", []),
            strong_points=data.get("strong_points", []),
            concerns=data.get("concerns", []),
            recommendation=data.get("recommendation", ""),
            reasoning=data.get("reasoning", ""),
        )

        print(f"   🎯 Match score: {analysis.overall_score}/10 — {analysis.recommendation}")
        return analysis

    except Exception as e:
        print(f"   ⚠️ Match analysis failed: {e}")
        return MatchAnalysis(reasoning=f"Analysis failed: {str(e)}")
