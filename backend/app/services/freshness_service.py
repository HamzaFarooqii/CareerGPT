# ============================================================
# Freshness Service — Job Age Scoring & Date Parsing
# ============================================================
# Every job gets a freshness_score from 0.0 to 1.0:
#   1.0 = posted today
#   0.5 = posted 7 days ago
#   0.0 = posted 30+ days ago or expired
#
# Source reliability multipliers reward structured API sources
# (Greenhouse, Lever) over HTML scrapers (Rozee, Remotive).
# ============================================================

import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urlunparse
from typing import Optional


# Source reliability weights (higher = more trustworthy)
SOURCE_RELIABILITY: dict[str, float] = {
    "greenhouse":   1.00,
    "lever":        1.00,
    "ashby":        1.00,
    "remoteok.com": 0.92,
    "remotive.com": 0.90,
    "wellfound.com": 0.88,
    "jobicy.com":   0.85,
    "rozee.pk":     0.82,
    "mustakbil.com": 0.78,
    "indeed.com":   0.88,
}

# Age → score mapping (linear decay between milestones)
AGE_SCORE_MILESTONES = [
    (0,  1.00),   # today
    (1,  0.95),   # 1 day old
    (2,  0.88),   # 2 days old
    (3,  0.80),   # 3 days old
    (5,  0.65),   # 5 days old
    (7,  0.50),   # 1 week old
    (14, 0.25),   # 2 weeks old
    (21, 0.12),   # 3 weeks old
    (30, 0.05),   # 1 month old
]


def _age_to_score(days_old: float) -> float:
    """Linear interpolation between age milestones."""
    if days_old <= 0:
        return 1.0
    for i in range(len(AGE_SCORE_MILESTONES) - 1):
        d0, s0 = AGE_SCORE_MILESTONES[i]
        d1, s1 = AGE_SCORE_MILESTONES[i + 1]
        if d0 <= days_old <= d1:
            t = (days_old - d0) / (d1 - d0)
            return round(s0 + t * (s1 - s0), 4)
    return 0.02  # older than 30 days


def compute_freshness_score(
    posted_at: Optional[datetime],
    source: str,
    created_at: Optional[datetime] = None,
) -> tuple[float, Optional[int]]:
    """
    Compute a job's freshness score and days_old.

    Returns:
        (freshness_score: float, days_old: int | None)
    """
    now = datetime.now(timezone.utc)

    reference_date = posted_at or created_at
    if reference_date is None:
        return (0.70, None)  # unknown age, give moderate score

    if reference_date.tzinfo is None:
        reference_date = reference_date.replace(tzinfo=timezone.utc)

    days_old = (now - reference_date).days
    if days_old < 0:
        days_old = 0

    age_score = _age_to_score(days_old)
    reliability = SOURCE_RELIABILITY.get(source.lower(), 0.75)
    final_score = round(age_score * reliability, 4)

    return (final_score, days_old)


def parse_posted_date(raw_date: str) -> Optional[datetime]:
    """
    Parse various raw date strings scraped from job boards into a datetime.

    Handles formats like:
      - "2 days ago", "1 hour ago", "just now"
      - "Jun 15, 2025", "15 Jun 2025", "2025-06-15"
      - "Posted: June 15"
    """
    if not raw_date:
        return None

    now = datetime.now(timezone.utc)
    text = raw_date.lower().strip()

    # ── Relative dates ──────────────────────────────────────
    if "just now" in text or "today" in text or "moments ago" in text:
        return now

    if "hour" in text:
        m = re.search(r"(\d+)\s*hour", text)
        hours = int(m.group(1)) if m else 1
        return now - timedelta(hours=hours)

    if "day" in text:
        m = re.search(r"(\d+)\s*day", text)
        days = int(m.group(1)) if m else 1
        return now - timedelta(days=days)

    if "week" in text:
        m = re.search(r"(\d+)\s*week", text)
        weeks = int(m.group(1)) if m else 1
        return now - timedelta(weeks=weeks)

    if "month" in text:
        m = re.search(r"(\d+)\s*month", text)
        months = int(m.group(1)) if m else 1
        return now - timedelta(days=months * 30)

    if "yesterday" in text:
        return now - timedelta(days=1)

    # ── Absolute dates ──────────────────────────────────────
    patterns = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d",
        "%b %d",
    ]

    cleaned = re.sub(r"posted[:\s]*", "", raw_date, flags=re.IGNORECASE).strip()

    for fmt in patterns:
        try:
            dt = datetime.strptime(cleaned, fmt)
            # If no year in format, assume current year
            if dt.year == 1900:
                dt = dt.replace(year=now.year)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def build_canonical_url(url: str) -> str:
    """
    Normalize a URL for deduplication purposes.
    - Lowercase scheme + host
    - Strip tracking params (utm_*, ref, etc.)
    - Remove trailing slashes
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        # Rebuild without query/fragment for canonical form
        canonical = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            "",
            "",
            "",
        ))
        return canonical
    except Exception:
        return url.strip().lower()


def is_job_stale(days_old: Optional[int], max_age_days: int = 30) -> bool:
    """Return True if the job is older than max_age_days."""
    if days_old is None:
        return False
    return days_old > max_age_days
