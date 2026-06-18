# ============================================================
# Extraction Agent — LLM-Powered Job Requirement Extraction
# ============================================================
# Updated to use the unified ai_client (Groq → Gemini → OpenRouter)
# No longer tied to Gemini — works with any configured provider.
# ============================================================

import json
from app.services.ai_client import ai_generate
from app.models.job import JobExtracted


EXTRACTION_SYSTEM_PROMPT = """You are a job requirement extraction specialist. Extract structured information from job postings.

Return ONLY valid JSON — no explanations, no markdown, no extra text.

Required JSON format:
{
  "required_skills": ["list of required technical skills"],
  "preferred_skills": ["list of nice-to-have skills"],
  "experience_years_min": 0,
  "experience_years_max": 0,
  "education": "required degree or education level",
  "job_type_normalized": "one of: full-time, part-time, contract, remote, internship, hybrid",
  "seniority_level": "one of: intern, junior, mid, senior, lead, manager",
  "industry": "the industry or domain",
  "key_responsibilities": ["top 3-5 main responsibilities"]
}

RULES:
1. Normalize skill names (ReactJS → React, NodeJS → Node.js)
2. If experience is "fresh" or "entry level", set min=0, max=1
3. If experience is "2+ years", set min=2, max=5
4. If a field cannot be determined, use empty string or 0
5. Separate required vs preferred skills carefully
6. Return ONLY the JSON object, nothing else"""


async def extract_job_requirements(title: str, description: str) -> JobExtracted:
    """
    Use AI to extract structured requirements from a job posting.
    Works with any configured provider: Groq, Gemini, or OpenRouter.
    """
    user_message = f"""Extract structured requirements from this job posting:

JOB TITLE: {title}

JOB DESCRIPTION:
{description[:3000]}

Return ONLY the JSON object:"""

    try:
        result_text = await ai_generate(user_message, system=EXTRACTION_SYSTEM_PROMPT)
        result_text = result_text.strip()

        # Strip any markdown code blocks if model wraps JSON in them
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            result_text = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()

        data = json.loads(result_text)

        extracted = JobExtracted(
            required_skills=data.get("required_skills", []),
            preferred_skills=data.get("preferred_skills", []),
            experience_years_min=data.get("experience_years_min", 0),
            experience_years_max=data.get("experience_years_max", 0),
            education=data.get("education", ""),
            job_type_normalized=data.get("job_type_normalized", ""),
            seniority_level=data.get("seniority_level", ""),
            industry=data.get("industry", ""),
            key_responsibilities=data.get("key_responsibilities", []),
        )

        skills_count = len(extracted.required_skills) + len(extracted.preferred_skills)
        print(f"   🧠 Extracted: {skills_count} skills, "
              f"{extracted.experience_years_min}-{extracted.experience_years_max} yrs, "
              f"level={extracted.seniority_level}")

        return extracted

    except json.JSONDecodeError as e:
        print(f"   ⚠️ LLM returned invalid JSON: {e}")
        return JobExtracted()

    except Exception as e:
        print(f"   ⚠️ Extraction failed: {e}")
        return JobExtracted()
