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

    # Jobicy industry slugs — MUST be one of the values from
    # GET /api/v2/remote-jobs?get=industries (verified live on 2026-09-09,
    # API v2.2.16). Passing anything else (e.g. the old "tech"/"design"
    # slugs this map used to use) makes the whole request fail with
    # HTTP 400, so every search silently returned zero jobs.
    INDUSTRY_MAP = {
        "software": "engineering",
        "developer": "engineering",
        "engineer": "engineering",
        "engineering": "engineering",
        "android": "engineering",
        "ios": "engineering",
        "mobile": "engineering",
        "python": "engineering",
        "react": "engineering",
        "frontend": "engineering",
        "backend": "engineering",
        "fullstack": "engineering",
        "full-stack": "engineering",
        "web": "engineering",
        "devops": "engineering",
        "cybersecurity": "cybersecurity",
        "security": "cybersecurity",
        "data": "data-science",
        "machine learning": "data-science",
        "ai": "data-science",
        "qa": "qa-testing",
        "testing": "qa-testing",
        "design": "design-multimedia",
        "ux": "web-app-design",
        "ui": "web-app-design",
        "product": "management",
        "marketing": "marketing",
        "sales": "seller",
        "seo": "seo",
    }

    def __init__(self):
        super().__init__(source_name="jobicy.com")

    def _resolve_industry(self, query: str) -> str:
        query_lower = query.lower()
        for keyword, industry in self.INDUSTRY_MAP.items():
            if keyword in query_lower:
                return industry
        return "engineering"

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

        # ── Relevance setup (computed up front — also drives the API tag) ──
        GENERIC_WORDS = {
            "developer", "engineer", "dev", "software", "senior", "junior",
            "lead", "staff", "principal", "mid", "remote", "job", "jobs",
            "position", "role", "opportunity", "specialist", "expert",
        }

        query_lower = query.lower()
        query_words = [w for w in query_lower.split() if len(w) > 2]
        specific_words = [w for w in query_words if w not in GENERIC_WORDS]

        # Jobicy's 'tag' param wants a SINGLE bare keyword (e.g. "android"),
        # not a hyphenated compound phrase like "android-developer" — passing
        # the whole query as one slug matches nothing even when real, relevant
        # jobs exist. Use the most specific word alone, or skip the tag
        # entirely for a generic query and let 'industry' alone narrow it.
        tag = specific_words[0] if specific_words else ""
        url = f"{self.API_URL}?count={count}&industry={industry}"
        if tag:
            url += f"&tag={tag}"

        print(f"\n🔍 [{self.source_name}] Searching: industry='{industry}', tag='{tag or '(none)'}'")

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

            def _mentions_specific_word(job: dict) -> bool:
                """True if this job is actually about the specific (non-generic)
                query word(s). This is the real relevance gate; _job_score is
                only used for ranking among jobs that already pass this gate.

                A specific word in the title is enough on its own (titles
                describe the actual role). Without a title hit, require ALL
                specific words to co-occur in the description — a single
                common word (e.g. "data") turning up incidentally in an
                unrelated posting shouldn't qualify a multi-word query like
                "data scientist".
                """
                title = job.get("jobTitle", "").lower()
                if any(w in title for w in specific_words):
                    return True
                desc_snippet = job.get("jobDescription", "")[:400].lower()
                return all(w in desc_snippet for w in specific_words)

            scored = [(job, _job_score(job)) for job in all_jobs]

            # If we have specific words (e.g. "android"), a job MUST mention one
            # of them somewhere to qualify. No numeric threshold: a generic word
            # like "developer" scoring points is never enough on its own. If
            # nothing mentions the specific term, the honest answer is zero
            # results from this source — never unrelated titles to pad the count.
            if specific_words:
                filtered_jobs = [j for j, s in scored if _mentions_specific_word(j)]
                filtered_jobs.sort(key=lambda j: _job_score(j), reverse=True)
            else:
                # No specific words (broad query) — safe to relax further.
                filtered_jobs = [j for j, s in scored if s > 0]
                filtered_jobs.sort(key=lambda j: _job_score(j), reverse=True)
                if len(filtered_jobs) < 5:
                    by_score = sorted(scored, key=lambda x: x[1], reverse=True)
                    filtered_jobs = [j for j, _ in by_score[:30]] or all_jobs[:20]


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
