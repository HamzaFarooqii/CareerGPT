# ============================================================
# Lever Scraper — Public Postings API
# ============================================================
# Lever is an ATS used by Netflix, Carta, Figma, GitHub,
# GitLab, Shopify, Coinbase, and many others.
#
# Public API: https://api.lever.co/v0/postings/{company}?mode=json
# Returns clean JSON with all job details.
# ============================================================

import asyncio
import re
from datetime import datetime, timezone

import httpx

from app.models.job import JobRaw
from app.scrapers.base_scraper import BaseScraper


LEVER_COMPANIES = [
    "netflix", "carta", "github", "gitlab", "shopify",
    "coinbase", "lyft", "twitch", "discord", "canva",
    "attentive", "benchling", "cameo", "chainalysis",
    "checkr", "clickup", "degreed", "domo", "draftkings",
    "envoy", "fastly", "flexport", "gem", "grail",
    "hashicorp", "heap", "hopin", "hubspot", "intercom",
    "ironclad", "jumpcloud", "klaviyo", "komodo",
    "limeade", "loom", "magicleap", "mavenwave",
    "miro", "mixpanel", "momentive", "monday",
    "nearmap", "netlify", "noom", "nowports",
    "outreach", "palantir", "paperspace", "persona",
    "pipe", "postman", "prismatic", "procore",
    "qualified", "qualtrics", "recurse", "reddit",
    "riskified", "rivian", "robinhood", "roots",
    "samsara", "scout24", "scribd", "segment",
    "sendbird", "sentry", "signifyd", "snowflake",
    "sourcegraph", "squarespace", "stark", "strava",
    "superhuman", "swiftly", "sword", "tacobelltech",
    "talend", "tandemdiabetes", "textura", "thoughtful",
    "tinder", "toast", "together", "tonal",
    "transunion", "tripadvisor", "twilio", "twingate",
    "ui-path", "vanta", "veeva", "vercel",
    "veritone", "vidyard", "wealthsimple", "webflow",
    "whoop", "workato", "xero", "yext", "zendesk",
    "zipline", "zoom",
]


class LeverScraper(BaseScraper):
    """
    Scraper for Lever-hosted job boards.
    Uses the public JSON API endpoint.
    """

    API_BASE = "https://api.lever.co/v0/postings"

    def __init__(self):
        super().__init__(source_name="lever")
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "CareerGPT/2.0 (job aggregator)",
                "Accept": "application/json",
            },
            timeout=12.0,
            follow_redirects=True,
        )

    async def scrape_jobs(
        self, query: str, location: str = "Remote", max_pages: int = 2
    ) -> list[JobRaw]:
        """Search Lever boards across companies for matching jobs."""
        batch_size = min(len(LEVER_COMPANIES), max_pages * 8)
        companies = LEVER_COMPANIES[:batch_size]
        query_lower = query.lower()

        all_jobs: list[JobRaw] = []
        print(f"\\n🔍 [Lever] Scanning {len(companies)} company boards for: '{query}'")

        batch = 5
        for i in range(0, len(companies), batch):
            chunk = companies[i:i + batch]
            tasks = [self._fetch_company_jobs(c, query_lower) for c in chunk]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    all_jobs.extend(r)
            await asyncio.sleep(0.5)

        print(f"   ✅ [Lever] Found {len(all_jobs)} matching jobs")
        return all_jobs

    async def _fetch_company_jobs(self, company: str, query: str) -> list[JobRaw]:
        """Fetch jobs from a single Lever company board."""
        try:
            url = f"{self.API_BASE}/{company}?mode=json"
            resp = await self.client.get(url, timeout=10.0)
            if resp.status_code != 200:
                return []

            postings = resp.json()
            if not isinstance(postings, list):
                return []

            matched: list[JobRaw] = []
            for posting in postings:
                title = posting.get("text", "")
                categories = posting.get("categories", {})
                team = categories.get("team", "")
                dept = categories.get("department", "")

                # Build searchable text
                description = self._build_description(posting)

                if not self._matches_query(title, description, query):
                    continue

                location_str = categories.get("location", "") or posting.get("workplaceType", "Remote")
                posted_at_ts = posting.get("createdAt", 0)
                posted_date = self._ts_to_relative(posted_at_ts)

                apply_url = posting.get("hostedUrl", "")
                if not apply_url:
                    apply_url = f"https://jobs.lever.co/{company}/{posting.get('id', '')}"

                matched.append(JobRaw(
                    title=title,
                    company=company.replace("-", " ").title(),
                    location=location_str,
                    description=description[:4000],
                    salary_range=self._extract_salary(description),
                    job_type=categories.get("commitment", "Full-time"),
                    experience_required="",
                    posted_date=posted_date,
                    url=apply_url,
                    source="lever",
                    canonical_url=apply_url,
                    company_url=f"https://jobs.lever.co/{company}",
                ))

            return matched

        except Exception:
            return []

    def _build_description(self, posting: dict) -> str:
        """Combine description sections into full text."""
        parts = []
        for block in posting.get("descriptionBody", {}).get("blocks", []):
            if block.get("text"):
                parts.append(block["text"])
        for section in posting.get("lists", []):
            parts.append(section.get("text", ""))
            for item in section.get("content", "").split("<li>"):
                clean = re.sub(r"<[^>]+>", "", item).strip()
                if clean:
                    parts.append(f"• {clean}")
        full = " ".join(parts)
        return re.sub(r"\s+", " ", full).strip()

    def _matches_query(self, title: str, content: str, query: str) -> bool:
        query_words = query.lower().split()
        combined = (title + " " + content[:300]).lower()
        for word in query_words:
            if len(word) < 3:
                continue
            if word not in combined:
                return False
        return True

    def _ts_to_relative(self, ts_ms: int) -> str:
        """Convert epoch milliseconds to relative date string."""
        if not ts_ms:
            return ""
        try:
            dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            days = (datetime.now(timezone.utc) - dt).days
            if days == 0:
                return "today"
            if days == 1:
                return "1 day ago"
            return f"{days} days ago"
        except Exception:
            return ""

    def _extract_salary(self, text: str) -> str:
        """Try to find salary info in description."""
        m = re.search(r"\$[\d,]+\s*[-–]\s*\$[\d,]+", text)
        return m.group(0) if m else ""
