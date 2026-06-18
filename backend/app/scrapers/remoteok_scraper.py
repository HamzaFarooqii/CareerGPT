# ============================================================
# RemoteOK Scraper — Uses RemoteOK's Public JSON API
# ============================================================
# RemoteOK exposes a public API at remoteok.com/api
# Returns JSON with all current remote jobs — no HTML parsing needed.
# ============================================================

import json
from app.models.job import JobRaw
from app.scrapers.base_scraper import BaseScraper


class RemoteOKScraper(BaseScraper):
    """Scraper for RemoteOK.com using their public JSON API."""

    API_URL = "https://remoteok.com/api"

    def __init__(self):
        super().__init__(source_name="remoteok.com")

    async def scrape_jobs(
        self, query: str, location: str = "Remote", max_pages: int = 2
    ) -> list[JobRaw]:
        """
        Fetch jobs from RemoteOK's public API and filter by query.
        RemoteOK returns all jobs in one call — we filter client-side.
        """
        print(f"\n🔍 [{self.source_name}] Fetching jobs for: '{query}'")

        try:
            response = await self._rate_limited_get(self.API_URL)
            if response.status_code != 200:
                print(f"   ⚠️ RemoteOK API returned {response.status_code}")
                return []

            data = response.json()
            # First element is metadata, skip it
            if isinstance(data, list) and data:
                data = data[1:]  # Skip the first metadata object

        except Exception as e:
            print(f"   ❌ RemoteOK API error: {e}")
            return []

        # Filter by query terms
        query_terms = [t.lower() for t in query.split()]
        matched: list[JobRaw] = []

        for item in data:
            if not isinstance(item, dict):
                continue

            title = item.get("position", "") or ""
            tags = item.get("tags", []) or []
            description = item.get("description", "") or ""
            company = item.get("company", "") or ""

            # Check if job matches query
            searchable = f"{title} {' '.join(tags)} {description}".lower()
            if not any(term in searchable for term in query_terms):
                continue

            job_url = item.get("url", "") or f"https://remoteok.com/l/{item.get('id', '')}"

            # Clean description (RemoteOK sometimes includes HTML)
            clean_desc = description.replace("<p>", "\n").replace("</p>", "").replace("<br>", "\n")

            matched.append(JobRaw(
                title=title,
                company=company,
                location="Remote",
                description=clean_desc[:3000],
                salary_range=item.get("salary", "") or "",
                job_type="Remote",
                posted_date=item.get("date", "") or "",
                url=job_url,
                source=self.source_name,
            ))

            if len(matched) >= max_pages * 15:
                break

        print(f"   ✅ {len(matched)} matching jobs from {self.source_name}")
        return matched
