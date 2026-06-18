# ============================================================
# Jobicy API Scraper — Free Remote Jobs API
# ============================================================
# Jobicy.com provides another FREE public JSON API.
# Good for remote software engineering roles.
#
# API: https://jobicy.com/api/v2/remote-jobs
# Params: count, geo, industry, tag
#
# Using MULTIPLE free APIs gives us more job coverage.
# ============================================================

from app.models.job import JobRaw
from app.scrapers.base_scraper import BaseScraper


class JobicyScraper(BaseScraper):
    """Scraper using Jobicy.com's free public API."""

    API_URL = "https://jobicy.com/api/v2/remote-jobs"

    # Jobicy uses industry slugs
    INDUSTRY_MAP = {
        "software": "tech",
        "developer": "tech",
        "engineer": "tech",
        "python": "tech",
        "react": "tech",
        "data": "tech",
        "ai": "tech",
        "devops": "tech",
        "marketing": "marketing",
        "design": "design",
    }

    def __init__(self):
        super().__init__(source_name="jobicy.com")

    def _resolve_industry(self, query: str) -> str:
        query_lower = query.lower()
        for keyword, industry in self.INDUSTRY_MAP.items():
            if keyword in query_lower:
                return industry
        return "tech"

    async def scrape_jobs(
        self, query: str, location: str = "", max_pages: int = 3
    ) -> list[JobRaw]:
        """
        Fetch jobs from Jobicy's API.
        
        Jobicy API returns JSON like:
        {
          "jobs": [
            {
              "id": 12345,
              "url": "https://jobicy.com/jobs/...",
              "jobTitle": "Senior Python Developer",
              "companyName": "Acme Corp",
              "jobIndustry": ["tech"],
              "jobType": ["full-time"],
              "jobGeo": "Anywhere",
              "pubDate": "2026-05-01 10:00:00",
              "jobDescription": "Full description text...",
              "annualSalaryMin": "80000",
              "annualSalaryMax": "120000",
              "salaryCurrency": "USD"
            }, ...
          ]
        }
        """
        industry = self._resolve_industry(query)
        count = max_pages * 20

        # Jobicy uses 'tag' for keyword search and 'industry' for category
        tag = query.replace(" ", "-").lower()
        url = f"{self.API_URL}?count={count}&industry={industry}&tag={tag}"

        print(f"\n🔍 [{self.source_name}] Searching: industry='{industry}', tag='{tag}'")

        try:
            response = await self._rate_limited_get(url)

            if response.status_code != 200:
                print(f"   ⚠️ HTTP {response.status_code}")
                # Try without tag filter as fallback
                url_fallback = f"{self.API_URL}?count={count}&industry={industry}"
                response = await self._rate_limited_get(url_fallback)
                if response.status_code != 200:
                    return []

            data = response.json()
            all_jobs = data.get("jobs", [])

            # ── Strict relevance filtering ────────────────────────
            GENERIC_WORDS = {
                "developer", "engineer", "dev", "software", "senior", "junior",
                "lead", "staff", "principal", "mid", "remote", "job", "jobs",
                "position", "role", "opportunity", "specialist", "expert",
            }

            query_lower = query.lower()
            query_words = [w for w in query_lower.split() if len(w) > 2]
            specific_words = [w for w in query_words if w not in GENERIC_WORDS]

            def _job_score(job: dict) -> int:
                title = job.get("jobTitle", "").lower()
                desc_snippet = job.get("jobDescription", "")[:400].lower()

                score = 0
                if query_lower in title:
                    score += 100
                for w in specific_words:
                    if w in title:
                        score += 30
                    elif w in desc_snippet:
                        score += 5
                for w in query_words:
                    if w in title:
                        score += 5
                return score

            scored = [(job, _job_score(job)) for job in all_jobs]

            if specific_words:
                filtered_jobs = [j for j, s in scored if s >= 10]
                filtered_jobs.sort(key=lambda j: _job_score(j), reverse=True)
            else:
                filtered_jobs = [j for j, s in scored if s > 0]
                filtered_jobs.sort(key=lambda j: _job_score(j), reverse=True)

            if len(filtered_jobs) < 5:
                scored.sort(key=lambda x: x[1], reverse=True)
                filtered_jobs = [j for j, s in scored[:30] if s > 0] or all_jobs[:20]


            # Convert to JobRaw
            results: list[JobRaw] = []
            for job in filtered_jobs:
                # Build salary string
                salary = ""
                sal_min = job.get("annualSalaryMin")
                sal_max = job.get("annualSalaryMax")
                currency = job.get("salaryCurrency", "USD")
                if sal_min and sal_max:
                    salary = f"{currency} {sal_min} - {sal_max}"
                elif sal_min:
                    salary = f"{currency} {sal_min}+"

                job_types = job.get("jobType", [])
                job_type_str = ", ".join(job_types) if isinstance(job_types, list) else str(job_types)

                results.append(JobRaw(
                    title=job.get("jobTitle", ""),
                    company=job.get("companyName", ""),
                    location=job.get("jobGeo", "Remote"),
                    description=job.get("jobDescription", "")[:3000],
                    salary_range=salary,
                    job_type=job_type_str,
                    url=job.get("url", ""),
                    source=self.source_name,
                    posted_date=job.get("pubDate", ""),
                ))

            print(f"   ✅ {len(results)} jobs found (filtered from {len(all_jobs)} total)")
            return results

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return []
