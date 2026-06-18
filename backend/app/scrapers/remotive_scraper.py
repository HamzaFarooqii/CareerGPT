# ============================================================
# Remotive API Scraper — Free Remote Jobs API
# ============================================================
# Remotive.com provides a FREE public JSON API — no auth needed.
# It returns real remote tech job listings with full descriptions.
#
# API Docs: https://remotive.com/api/remote-jobs
#
# CONCEPT: API vs HTML Scraping
# ─────────────────────────────
# HTML scraping is fragile — sites change their HTML, use JavaScript
# rendering, or block scrapers entirely (like Rozee.pk and Indeed).
#
# APIs are RELIABLE — they return structured JSON data that doesn't
# change without notice. Always prefer APIs over scraping when available.
#
# LESSON: Rozee.pk uses a JavaScript SPA (empty HTML without browser).
# Indeed returns 403 to non-browser requests. Both would need Playwright
# (headless browser) which adds complexity. APIs are the smart choice.
# ============================================================

from bs4 import BeautifulSoup

from app.models.job import JobRaw
from app.scrapers.base_scraper import BaseScraper


class RemotiveScraper(BaseScraper):
    """Scraper using Remotive.com's free public API."""

    API_URL = "https://remotive.com/api/remote-jobs"

    # Remotive uses category slugs, not free-text search.
    # We map common search terms to their categories.
    CATEGORY_MAP = {
        "software": "software-dev",
        "developer": "software-dev",
        "engineer": "software-dev",
        "python": "software-dev",
        "react": "software-dev",
        "frontend": "software-dev",
        "backend": "software-dev",
        "fullstack": "software-dev",
        "full-stack": "software-dev",
        "web": "software-dev",
        "mobile": "software-dev",
        "devops": "devops",
        "data": "data",
        "machine learning": "data",
        "ai": "data",
        "design": "design",
        "product": "product",
        "qa": "qa",
        "marketing": "marketing",
    }

    def __init__(self):
        super().__init__(source_name="remotive.com")

    def _resolve_category(self, query: str) -> str:
        """Map a search query to a Remotive category slug."""
        query_lower = query.lower()
        for keyword, category in self.CATEGORY_MAP.items():
            if keyword in query_lower:
                return category
        return "software-dev"  # Default to software dev

    async def scrape_jobs(
        self, query: str, location: str = "", max_pages: int = 3
    ) -> list[JobRaw]:
        """
        Fetch jobs from Remotive's API.
        
        Remotive API returns JSON like:
        {
          "job-count": 150,
          "jobs": [
            {
              "id": 12345,
              "url": "https://remotive.com/remote-jobs/software-dev/...",
              "title": "Senior Python Developer",
              "company_name": "Acme Corp",
              "category": "Software Development",
              "tags": ["python", "fastapi", "docker"],
              "job_type": "full_time",
              "publication_date": "2026-05-01T00:00:00",
              "candidate_required_location": "Worldwide",
              "salary": "$80k - $120k",
              "description": "<p>Full HTML description...</p>"
            }, ...
          ]
        }
        """
        category = self._resolve_category(query)
        limit = max_pages * 20  # ~20 jobs per "page"

        url = f"{self.API_URL}?category={category}&limit={limit}"

        print(f"\n🔍 [{self.source_name}] Searching category: '{category}' (from query: '{query}')")

        try:
            response = await self._rate_limited_get(url)

            if response.status_code != 200:
                print(f"   ⚠️ HTTP {response.status_code}")
                return []

            data = response.json()
            all_jobs = data.get("jobs", [])

            # ── Strict relevance filtering ────────────────────────
            # Generic words that appear in ALL dev job titles — ignore for scoring
            GENERIC_WORDS = {
                "developer", "engineer", "dev", "software", "senior", "junior",
                "lead", "staff", "principal", "mid", "remote", "job", "jobs",
                "position", "role", "opportunity", "specialist", "expert",
            }

            query_lower = query.lower()
            # The "specific" words are the non-generic ones (e.g. "android", "python")
            query_words = [w for w in query_lower.split() if len(w) > 2]
            specific_words = [w for w in query_words if w not in GENERIC_WORDS]

            def _job_score(job: dict) -> int:
                """Score a job by relevance to query. Higher = more relevant."""
                title = job.get("title", "").lower()
                tags = " ".join(job.get("tags", [])).lower()
                desc_snippet = job.get("description", "")[:500].lower()

                score = 0
                # Full phrase in title: best match
                if query_lower in title:
                    score += 100
                # Each specific word in title
                for w in specific_words:
                    if w in title:
                        score += 30
                    elif w in tags:
                        score += 10
                    elif w in desc_snippet:
                        score += 3
                # Any generic word in title (minimum bar)
                for w in query_words:
                    if w in title:
                        score += 5
                return score

            # Score & filter all jobs
            scored = [(job, _job_score(job)) for job in all_jobs]

            # If we have specific words, require at least one match in title or tags
            if specific_words:
                filtered_jobs = [
                    job for job, score in scored
                    if score >= 10  # At least one specific word in title or tags
                ]
                # Sort by relevance
                filtered_jobs.sort(key=lambda j: _job_score(j), reverse=True)
            else:
                # No specific words — just sort by any match
                filtered_jobs = [job for job, score in scored if score > 0]
                filtered_jobs.sort(key=lambda j: _job_score(j), reverse=True)

            # Fallback: if filtering is too strict, take best matches
            if len(filtered_jobs) < 5:
                scored.sort(key=lambda x: x[1], reverse=True)
                filtered_jobs = [j for j, s in scored[:30] if s > 0] or all_jobs[:20]

            # Also filter by location if specified (and it's not just "Pakistan" for remote jobs)
            if location and location.lower() not in ["pakistan", "worldwide", "", "remote"]:
                location_filtered = []
                for job in filtered_jobs:
                    req_location = job.get("candidate_required_location", "").lower()
                    if location.lower() in req_location or "worldwide" in req_location:
                        location_filtered.append(job)
                if location_filtered:
                    filtered_jobs = location_filtered

            # Convert to our JobRaw model
            results: list[JobRaw] = []
            for job in filtered_jobs:
                # Clean HTML from description
                desc_html = job.get("description", "")
                desc_text = BeautifulSoup(desc_html, "html.parser").get_text(separator=" ", strip=True)

                results.append(JobRaw(
                    title=job.get("title", ""),
                    company=job.get("company_name", ""),
                    location=job.get("candidate_required_location", "Remote"),
                    description=desc_text[:3000],
                    salary_range=job.get("salary", ""),
                    job_type=job.get("job_type", "").replace("_", " "),
                    url=job.get("url", ""),
                    source=self.source_name,
                    posted_date=job.get("publication_date", ""),
                ))

            print(f"   ✅ {len(results)} jobs found (filtered from {len(all_jobs)} total)")
            return results

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return []
