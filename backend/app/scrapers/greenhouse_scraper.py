# ============================================================
# Greenhouse Scraper — Public Job Board API
# ============================================================
# Greenhouse is an ATS used by Stripe, Airbnb, Figma, Notion,
# Linear, Vercel, and hundreds of tech companies.
#
# Their job board API is COMPLETELY PUBLIC — no auth, no scraping.
# URL: https://boards-api.greenhouse.io/v1/boards/{company}/jobs
# Returns structured JSON with title, location, content, apply URL.
#
# This is far more reliable than HTML scraping because:
# 1. It's an official API (won't break on design changes)
# 2. Returns clean structured data
# 3. No CAPTCHA or anti-bot measures
# 4. Always returns full job descriptions
# ============================================================

import asyncio
import re
from typing import Optional

import httpx

from app.models.job import JobRaw
from app.scrapers.base_scraper import BaseScraper


# Global companies using Greenhouse
GREENHOUSE_GLOBAL_COMPANIES = [
    "stripe", "airbnb", "figma", "notion", "linear", "vercel",
    "retool", "rippling", "brex", "deel", "plaid", "ramp",
    "lattice", "coda", "mercury", "anduril", "scale",
    "gusto", "benchling", "cockroachdb", "dbtlabs", "motherduck",
    "replit", "render", "fly", "supabase", "turso",
    "anthropic", "cohere", "huggingface", "weights-and-biases",
    "stability", "runway", "perplexity",
]

# Pakistan-adjacent / remote companies that hire from Pakistan
GREENHOUSE_REMOTE_COMPANIES = [
    "motive", "contentsquare", "talabat", "careem",
    "gaditek", "netsol", "systems-limited",
    "arbisoft", "folio3", "10pearls", "devsinc",
    "navisite", "tkxel", "nextbridge",
]


class GreenhouseScraper(BaseScraper):
    """
    Scraper for Greenhouse-hosted job boards.
    Uses the public JSON API — no HTML parsing needed.
    """

    API_BASE = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(self):
        super().__init__(source_name="greenhouse")
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "CareerGPT/2.0 (job aggregator; contact@careergpt.io)",
                "Accept": "application/json",
            },
            timeout=15.0,
            follow_redirects=True,
        )

    async def scrape_jobs(
        self, query: str, location: str = "Remote", max_pages: int = 2
    ) -> list[JobRaw]:
        """
        Search Greenhouse boards across multiple companies for matching jobs.
        'max_pages' is repurposed as the max number of company boards to scan.
        """
        # Choose company lists based on location context
        loc = location.lower()
        if "pakistan" in loc or "uae" in loc:
            companies = GREENHOUSE_REMOTE_COMPANIES + GREENHOUSE_GLOBAL_COMPANIES[:15]
        else:
            companies = GREENHOUSE_GLOBAL_COMPANIES

        # Limit companies per run based on max_pages setting (pages → company batches)
        batch_size = min(len(companies), max_pages * 8)
        companies_to_scan = companies[:batch_size]

        all_jobs: list[JobRaw] = []
        query_lower = query.lower()

        print(f"\\n🔍 [Greenhouse] Scanning {len(companies_to_scan)} company boards for: '{query}'")

        # Scan companies in parallel batches of 5 to stay polite
        batch = 5
        for i in range(0, len(companies_to_scan), batch):
            chunk = companies_to_scan[i:i + batch]
            tasks = [self._fetch_company_jobs(company, query_lower) for company in chunk]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    all_jobs.extend(result)
            await asyncio.sleep(0.5)  # Be polite between batches

        print(f"   ✅ [Greenhouse] Found {len(all_jobs)} matching jobs")
        return all_jobs

    async def _fetch_company_jobs(self, company: str, query: str) -> list[JobRaw]:
        """Fetch and filter jobs from a single company's Greenhouse board."""
        try:
            url = f"{self.API_BASE}/{company}/jobs?content=true"
            resp = await self.client.get(url, timeout=10.0)
            if resp.status_code != 200:
                return []

            data = resp.json()
            jobs_data = data.get("jobs", [])

            matched: list[JobRaw] = []
            for job in jobs_data:
                title = job.get("title", "")
                if not self._matches_query(title, job.get("content", ""), query):
                    continue

                location_info = ""
                if job.get("offices"):
                    location_info = ", ".join(
                        o.get("name", "") for o in job["offices"] if o.get("name")
                    )
                elif job.get("location"):
                    location_info = job["location"].get("name", "")

                # Strip HTML from content
                description = self._strip_html(job.get("content", ""))

                matched.append(JobRaw(
                    title=title,
                    company=company.replace("-", " ").title(),
                    location=location_info or "Remote",
                    description=description[:4000],
                    salary_range="",
                    job_type=self._extract_job_type(title, description),
                    experience_required="",
                    posted_date=self._parse_gh_date(job.get("updated_at", "")),
                    url=job.get("absolute_url", f"https://boards.greenhouse.io/{company}/jobs/{job.get('id', '')}"),
                    source="greenhouse",
                    canonical_url=job.get("absolute_url", ""),
                    company_url=f"https://greenhouse.io/boards/{company}",
                ))

            return matched

        except Exception as e:
            return []

    def _matches_query(self, title: str, content: str, query: str) -> bool:
        """Check if a job matches the search query."""
        query_words = query.lower().split()
        title_lower = title.lower()
        content_lower = content.lower()[:500]

        # All query words must appear in title or content
        for word in query_words:
            if len(word) < 3:
                continue
            if word not in title_lower and word not in content_lower:
                # Try partial match for tech acronyms
                if not any(word in t for t in title_lower.split()):
                    return False
        return True

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags from description."""
        clean = re.sub(r"<[^>]+>", " ", html)
        clean = re.sub(r"&[a-z]+;", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def _parse_gh_date(self, date_str: str) -> str:
        """Convert ISO date to human readable."""
        if not date_str:
            return ""
        try:
            from datetime import datetime, timezone, timedelta
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days = (now - dt).days
            if days == 0:
                return "today"
            if days == 1:
                return "1 day ago"
            return f"{days} days ago"
        except Exception:
            return date_str[:10]

    def _extract_job_type(self, title: str, desc: str) -> str:
        """Heuristic job type extraction."""
        text = (title + " " + desc[:200]).lower()
        if "intern" in text:
            return "Internship"
        if "contract" in text or "freelance" in text:
            return "Contract"
        if "part-time" in text or "part time" in text:
            return "Part-time"
        return "Full-time"
