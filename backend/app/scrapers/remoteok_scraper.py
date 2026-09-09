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

        # ── Strict relevance filtering ────────────────────────
        # Generic words that appear in ALL dev job titles — ignore for
        # matching so "developer" alone doesn't pass everything through.
        GENERIC_WORDS = {
            "developer", "engineer", "dev", "software", "senior", "junior",
            "lead", "staff", "principal", "mid", "remote", "job", "jobs",
            "position", "role", "opportunity", "specialist", "expert",
        }
        query_terms = [t.lower() for t in query.split() if len(t) > 2]
        specific_terms = [t for t in query_terms if t not in GENERIC_WORDS]

        matched: list[JobRaw] = []

        for item in data:
            if not isinstance(item, dict):
                continue

            title = item.get("position", "") or ""
            tags = item.get("tags", []) or []
            description = item.get("description", "") or ""
            company = item.get("company", "") or ""

            # Relevance gate: a specific word (e.g. "android") in the TITLE is
            # the reliable signal — titles are written to describe the actual
            # role. Falling back to "any specific word anywhere in the
            # description" is too loose for multi-word queries: a common word
            # like "data" turns up incidentally in unrelated postings (an
            # Irrigation Technician job mentioning "field data" would
            # otherwise match "data scientist"). So when title doesn't match,
            # require ALL specific words to co-occur somewhere, not just one.
            title_lower = title.lower()
            if specific_terms:
                if not any(term in title_lower for term in specific_terms):
                    searchable = f"{title_lower} {' '.join(tags)} {description}".lower()
                    if not all(term in searchable for term in specific_terms):
                        continue
            elif query_terms and not any(term in title_lower for term in query_terms):
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
