# ============================================================
# Mustakbil Scraper — Pakistan's Second-Largest Job Board
# ============================================================

import re
from bs4 import BeautifulSoup
from app.models.job import JobRaw
from app.scrapers.base_scraper import BaseScraper


class MustakbilScraper(BaseScraper):
    """Scraper for mustakbil.com job listings."""

    BASE_URL = "https://mustakbil.com"

    def __init__(self):
        super().__init__(source_name="mustakbil.com")

    async def scrape_jobs(
        self, query: str, location: str = "Pakistan", max_pages: int = 2
    ) -> list[JobRaw]:
        all_jobs: list[JobRaw] = []
        query_slug = query.replace(" ", "+")

        print(f"\n🔍 [mustakbil.com] Searching for: '{query}'")

        for page in range(1, max_pages + 1):
            try:
                url = f"{self.BASE_URL}/jobs/?q={query_slug}&page={page}"
                response = await self._rate_limited_get(url)
                if response.status_code != 200:
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                jobs = self._parse_jobs(soup)
                if not jobs:
                    break
                all_jobs.extend(jobs)
                print(f"   📄 [mustakbil.com] Page {page}: {len(jobs)} jobs")

            except Exception as e:
                print(f"   ⚠️ [mustakbil.com] Page {page} failed: {e}")
                break

        return all_jobs

    def _parse_jobs(self, soup: BeautifulSoup) -> list[JobRaw]:
        jobs = []

        # Mustakbil uses various container classes — try multiple selectors
        containers = (
            soup.find_all("div", class_=re.compile(r"job[-_]?card|job[-_]?item|listing", re.I))
            or soup.find_all("article", class_=re.compile(r"job", re.I))
            or soup.find_all("li", class_=re.compile(r"job", re.I))
        )

        for item in containers[:20]:
            try:
                # Title
                title_el = (
                    item.find("h2") or item.find("h3")
                    or item.find("a", class_=re.compile(r"title|position", re.I))
                )
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                # Company
                company_el = item.find(class_=re.compile(r"company|employer|org", re.I))
                company = company_el.get_text(strip=True) if company_el else "Company"

                # Location
                loc_el = item.find(class_=re.compile(r"location|city", re.I))
                location = loc_el.get_text(strip=True) if loc_el else "Pakistan"

                # URL
                link = item.find("a", href=True)
                job_url = ""
                if link:
                    href = link["href"]
                    job_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

                # Description snippet
                desc_el = item.find(class_=re.compile(r"desc|summary|excerpt", re.I))
                description = desc_el.get_text(strip=True) if desc_el else f"{title} at {company} in {location}"

                # Posted date
                date_el = item.find(class_=re.compile(r"date|time|ago|posted", re.I))
                posted = date_el.get_text(strip=True) if date_el else ""

                # Salary
                salary_el = item.find(class_=re.compile(r"salary|pay|compensation", re.I))
                salary = salary_el.get_text(strip=True) if salary_el else ""

                if title and len(title) > 3:
                    jobs.append(JobRaw(
                        title=title,
                        company=company,
                        location=location if location else "Pakistan",
                        description=description,
                        salary_range=salary,
                        job_type="Full-time",
                        experience_required="",
                        posted_date=posted,
                        url=job_url,
                        source="mustakbil.com",
                        canonical_url=job_url,
                        company_url="https://mustakbil.com",
                    ))
            except Exception:
                continue

        return jobs
