# ============================================================
# ATS Score Engine — Keyword Analysis & Resume Scoring
# ============================================================
# Computes how well a resume would score in an ATS system
# for a specific job description.
#
# ATS Score = (matched_keywords / total_jd_keywords) × 100
# Adjusted by section coverage and keyword prominence.
# ============================================================

import re
from dataclasses import dataclass, field


# Common tech stopwords to exclude from keyword extraction
STOPWORDS = {
    "the", "and", "or", "for", "with", "from", "are", "have", "will",
    "can", "you", "our", "your", "this", "that", "they", "their",
    "able", "also", "both", "well", "such", "each", "most", "some",
    "work", "team", "join", "help", "build", "make", "use", "get",
    "good", "great", "strong", "excellent", "experience", "ability",
    "skills", "knowledge", "understanding", "familiarity",
}

# High-value tech keywords (weighted higher in ATS scoring)
TECH_KEYWORDS = {
    "python", "javascript", "typescript", "react", "vue", "angular",
    "node", "nodejs", "express", "fastapi", "django", "flask",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "docker", "kubernetes", "aws", "azure", "gcp", "terraform",
    "git", "github", "ci/cd", "devops", "microservices", "rest", "graphql",
    "machine learning", "deep learning", "tensorflow", "pytorch",
    "nlp", "llm", "gpt", "bert", "transformer", "embedding",
    "data science", "pandas", "numpy", "scikit-learn",
    "java", "kotlin", "swift", "golang", "rust", "c++", "c#",
    "linux", "bash", "shell", "agile", "scrum", "jira",
}


@dataclass
class ATSReport:
    """Detailed ATS analysis result."""
    score: int                              # 0-100
    keyword_match_pct: float               # % of JD keywords found in resume
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    section_scores: dict = field(default_factory=dict)
    total_jd_keywords: int = 0
    matched_count: int = 0


def _extract_keywords(text: str, min_len: int = 3) -> set[str]:
    """
    Extract meaningful keywords from text.
    Returns a set of lowercase normalized keywords.
    """
    text = text.lower()

    # Extract multi-word tech terms first
    multi_word = set()
    for term in TECH_KEYWORDS:
        if " " in term and term in text:
            multi_word.add(term)

    # Extract single words
    words = re.findall(r"\b[a-z][a-z+#./-]{2,}\b", text)
    single = {w for w in words if w not in STOPWORDS and len(w) >= min_len}

    return single | multi_word


def _normalize_keyword(kw: str) -> str:
    """Normalize keyword variants (e.g., 'nodejs' → 'node.js')."""
    normalizations = {
        "nodejs": "node.js",
        "reactjs": "react",
        "vuejs": "vue",
        "angularjs": "angular",
        "postgres": "postgresql",
        "mongo": "mongodb",
        "k8s": "kubernetes",
        "tf": "terraform",
        "ml": "machine learning",
        "dl": "deep learning",
    }
    return normalizations.get(kw.lower(), kw)


def _check_sections(resume_text: str) -> dict[str, int]:
    """
    Check presence and quality of key resume sections.
    Returns a dict of section_name → score (0–100).
    """
    text_lower = resume_text.lower()
    sections = {
        "summary":      any(kw in text_lower for kw in ["summary", "objective", "profile"]),
        "experience":   any(kw in text_lower for kw in ["experience", "employment", "work history"]),
        "skills":       any(kw in text_lower for kw in ["skills", "competencies", "expertise"]),
        "education":    any(kw in text_lower for kw in ["education", "degree", "bachelor", "master", "university"]),
        "projects":     any(kw in text_lower for kw in ["project", "built", "developed", "deployed"]),
    }
    return {sec: (100 if present else 0) for sec, present in sections.items()}


def compute_ats_score(
    resume_text: str,
    job_description: str,
) -> ATSReport:
    """
    Compute ATS compatibility score between a resume and job description.

    Algorithm:
    1. Extract all meaningful keywords from the JD
    2. Check which keywords appear in the resume
    3. Weight tech keywords higher than generic words
    4. Assess section coverage
    5. Compute composite score

    Returns:
        ATSReport with score, matched/missing keywords, and suggestions
    """
    if not resume_text or not job_description:
        return ATSReport(score=0, keyword_match_pct=0.0)

    # Extract JD keywords
    jd_keywords = _extract_keywords(job_description)
    jd_keywords = {_normalize_keyword(k) for k in jd_keywords}

    # Extract resume keywords
    resume_keywords = _extract_keywords(resume_text)
    resume_keywords = {_normalize_keyword(k) for k in resume_keywords}

    # Match keywords
    matched = jd_keywords & resume_keywords
    missing = jd_keywords - resume_keywords

    total = len(jd_keywords)
    matched_count = len(matched)

    if total == 0:
        keyword_match_pct = 0.0
    else:
        keyword_match_pct = round(matched_count / total * 100, 1)

    # Weight tech keywords higher
    tech_matched = matched & TECH_KEYWORDS
    tech_missing = (missing & TECH_KEYWORDS)

    # Section analysis
    section_scores = _check_sections(resume_text)
    section_avg = sum(section_scores.values()) / max(len(section_scores), 1)

    # Compute base score
    base_score = keyword_match_pct * 0.70 + section_avg * 0.30

    # Bonus for tech keyword coverage
    tech_total = len(jd_keywords & TECH_KEYWORDS)
    if tech_total > 0:
        tech_pct = len(tech_matched) / tech_total * 100
        base_score = base_score * 0.85 + tech_pct * 0.15

    final_score = min(100, max(0, int(round(base_score))))

    # Generate actionable suggestions
    suggestions = []
    if tech_missing:
        top_tech = sorted(tech_missing)[:5]
        suggestions.append(f"Add missing technical skills: {', '.join(top_tech)}")
    if not section_scores.get("summary"):
        suggestions.append("Add a professional summary section to improve ATS parsing")
    if not section_scores.get("skills"):
        suggestions.append("Add a dedicated Skills section with a keyword-rich list")
    if not section_scores.get("projects"):
        suggestions.append("Add a Projects section to demonstrate hands-on experience")
    if keyword_match_pct < 60:
        suggestions.append("Mirror more keywords from the job description naturally in your resume")
    if keyword_match_pct >= 80:
        suggestions.append("Excellent keyword coverage! Focus on quantifying achievements")

    return ATSReport(
        score=final_score,
        keyword_match_pct=keyword_match_pct,
        matched_keywords=sorted(matched)[:30],
        missing_keywords=sorted(missing & TECH_KEYWORDS)[:20],  # Focus on tech gaps
        suggestions=suggestions,
        section_scores=section_scores,
        total_jd_keywords=total,
        matched_count=matched_count,
    )
