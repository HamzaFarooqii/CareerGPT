# ============================================================
# Cover Letter Agent — Tailored Application Letters
# ============================================================
# This agent generates cover letters that are:
#   1. Specific to the job (mentions company, role, requirements)
#   2. Specific to the candidate (highlights relevant experience)
#   3. Professional but personal (not generic template garbage)
#
# CONCEPT: RAG in Action
# ──────────────────────
# This is a perfect example of RAG (Retrieval-Augmented Generation):
#   - RETRIEVAL: We fetch the candidate's resume + job description
#   - AUGMENTATION: We feed both as context to the LLM
#   - GENERATION: The LLM produces a tailored cover letter
#
# Without the resume context, the LLM would write generic text.
# With it, the letter mentions specific projects, skills, and
# experiences that match the job. That's the power of RAG.
# ============================================================

import json

from app.services.ai_client import ai_generate

COVER_LETTER_PROMPT = """You are an expert career coach writing a cover letter for a job application.

RULES:
1. Keep it under 300 words — hiring managers skim
2. Opening paragraph: Why you're excited about THIS specific role at THIS company
3. Middle paragraph: 2-3 specific experiences/projects from the resume that match the job requirements
4. Closing paragraph: Express enthusiasm, mention you'd welcome an interview
5. Be confident but not arrogant
6. Use natural language — no clichés like "I am writing to express my interest"
7. Mention specific technologies/skills from both the resume and job
8. If the candidate is a fresh graduate, emphasize projects and learning speed

Return a JSON object:
{
  "cover_letter": "The full cover letter text",
  "key_highlights": ["3 bullet points summarizing what makes this candidate strong for this role"]
}
"""


async def generate_cover_letter(resume_text: str, job_title: str, 
                                 company: str, job_description: str,
                                 matching_skills: list[str] = None,
                                 strong_points: list[str] = None) -> dict:
    """
    Generate a tailored cover letter using the candidate's resume and job details.
    
    Args:
        resume_text: Full resume text
        job_title: Title of the job
        company: Company name
        job_description: Full job description
        matching_skills: Skills the candidate has that match (from matching agent)
        strong_points: Strong points identified by matching agent
    
    Returns:
        Dict with "cover_letter" (text) and "key_highlights" (list)
    """
    # Build extra context from matching analysis if available
    match_context = ""
    if matching_skills:
        match_context += f"\nMATCHING SKILLS: {', '.join(matching_skills)}"
    if strong_points:
        match_context += f"\nSTRONG POINTS: {', '.join(strong_points)}"

    user_message = f"""Write a cover letter for this application:

CANDIDATE'S RESUME:
{resume_text[:2500]}

JOB TITLE: {job_title}
COMPANY: {company or 'the company'}
JOB DESCRIPTION:
{job_description[:1500]}
{match_context}

Generate the cover letter as JSON."""

    try:
        result_text = await ai_generate(user_message, system=COVER_LETTER_PROMPT)
        result_text = result_text.strip()
        # Strip markdown code blocks if model wraps JSON
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            result_text = "\n".join(l for l in lines if not l.startswith("```")).strip()

        data = json.loads(result_text)

        result = {
            "cover_letter": data.get("cover_letter", ""),
            "key_highlights": data.get("key_highlights", []),
        }

        print(f"   ✉️ Cover letter generated ({len(result['cover_letter'])} chars)")
        return result

    except Exception as e:
        print(f"   ⚠️ Cover letter generation failed: {e}")
        return {"cover_letter": "", "key_highlights": []}
