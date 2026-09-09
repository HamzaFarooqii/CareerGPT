# ============================================================
# Ranking Service — Composite Job Score Engine
# ============================================================
# Combines multiple signals into a single rank score so jobs
# are ordered by true relevance, not just vector similarity.
#
# Composite Score Formula:
#   rank = semantic_similarity × 0.30
#         + skill_match         × 0.25
#         + freshness           × 0.20
#         + experience_fit      × 0.15
#         + source_reliability  × 0.10
#
# This ensures a job posted today with 80% skill match beats
# a 3-week-old job with 95% skill match.
# ============================================================

from typing import Optional
from app.services.freshness_service import SOURCE_RELIABILITY


# Scoring weights (must sum to 1.0)
WEIGHTS = {
    "semantic":     0.30,
    "skill_match":  0.25,
    "freshness":    0.20,
    "experience":   0.15,
    "source":       0.10,
}

# Seniority level compatibility matrix
# Maps (resume_level, job_level) → experience_fit_bonus (0.0–1.0)
SENIORITY_FIT = {
    ("intern",   "intern"):  1.0,
    ("junior",   "junior"):  1.0,
    ("junior",   "intern"):  0.9,   # Overqualified but ok
    ("mid",      "mid"):     1.0,
    ("mid",      "junior"):  0.85,
    ("mid",      "senior"):  0.6,
    ("senior",   "senior"):  1.0,
    ("senior",   "lead"):    0.8,
    ("senior",   "mid"):     0.9,
    ("lead",     "lead"):    1.0,
    ("lead",     "senior"):  0.95,
}


def compute_rank_score(
    semantic_score: float,          # 0.0–1.0 (cosine similarity)
    skill_match_score: float,       # 0.0–10.0 (from LLM analysis)
    experience_fit_score: float,    # 0.0–10.0 (from LLM analysis)
    freshness_score: float,         # 0.0–1.0 (from freshness service)
    source: str,
) -> float:
    """
    Compute a composite rank score combining all signals.
    Returns a float 0.0–1.0.
    """
    # Normalize LLM scores from 0–10 to 0–1
    skill_norm = min(1.0, skill_match_score / 10.0)
    exp_norm = min(1.0, experience_fit_score / 10.0)
    source_reliability = SOURCE_RELIABILITY.get(source.lower(), 0.75)

    score = (
        WEIGHTS["semantic"]    * semantic_score
        + WEIGHTS["skill_match"] * skill_norm
        + WEIGHTS["freshness"]   * freshness_score
        + WEIGHTS["experience"]  * exp_norm
        + WEIGHTS["source"]      * source_reliability
    )

    return round(min(1.0, max(0.0, score)), 4)


def generate_explanation(
    job_title: str,
    company: str,
    skill_match_score: float,
    experience_fit_score: float,
    freshness_score: float,
    days_old: Optional[int],
    source: str,
    recommendation: str,
    missing_skills: list[str],
    matching_skills: list[str],
    location: str = "",
) -> str:
    """
    Generate a human-readable explanation for why this job was recommended.

    Example output:
    "Recommended because: 92% skill match · Posted 1 day ago · Remote position"
    """
    reasons = []

    # Skill match
    skill_pct = int(skill_match_score * 10)
    if skill_pct >= 80:
        reasons.append(f"✅ {skill_pct}% skill match")
    elif skill_pct >= 60:
        reasons.append(f"🟡 {skill_pct}% skill match")
    else:
        reasons.append(f"⚠️ {skill_pct}% skill match")

    # Freshness
    if days_old is not None:
        if days_old == 0:
            reasons.append("🟢 Posted today")
        elif days_old == 1:
            reasons.append("🟢 Posted yesterday")
        elif days_old <= 3:
            reasons.append(f"🟢 Posted {days_old} days ago")
        elif days_old <= 7:
            reasons.append(f"🟡 Posted {days_old} days ago")
        else:
            reasons.append(f"🔴 Posted {days_old} days ago")

    # Location / remote
    if location:
        loc_lower = location.lower()
        if "remote" in loc_lower:
            reasons.append("🌐 Remote position")
        elif "pakistan" in loc_lower or "pk" in loc_lower:
            reasons.append("🇵🇰 Pakistan-based role")

    # Source
    source_labels = {
        "greenhouse": "via Greenhouse (verified)",
        "lever": "via Lever (verified)",
        "rozee.pk": "via Rozee.pk",
        "remotive.com": "via Remotive",
        "remoteok.com": "via RemoteOK",
        "wellfound.com": "via Wellfound",
    }
    if source in source_labels:
        reasons.append(f"📋 {source_labels[source]}")

    # Missing skills warning
    if missing_skills:
        top_missing = missing_skills[:3]
        reasons.append(f"📚 Missing: {', '.join(top_missing)}")

    explanation = " · ".join(reasons)

    # Add recommendation framing
    rec = recommendation.upper().split()[0] if recommendation else ""
    if rec == "APPLY":
        return f"🎯 Strong match — {explanation}"
    elif rec == "CONSIDER":
        return f"💡 Worth considering — {explanation}"
    else:
        return explanation
