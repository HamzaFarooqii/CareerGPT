# ============================================================
# Wellfound Scraper — Startup Jobs via Public API
# ============================================================
# Wellfound (formerly AngelList) has a public job search.
# We use their search endpoint which returns JSON.
# ============================================================

from app.models.job import JobRaw
from app.scrapers.base_scraper import BaseScraper


class WellfoundScraper(BaseScraper):
    """Scraper for Wellfound.com startup jobs."""

    BASE_URL = "https://wellfound.com"

    def __init__(self):
        super().__init__(source_name="wellfound.com")

    async def scrape_jobs(
        self, query: str, location: str = "Remote", max_pages: int = 2
    ) -> list[JobRaw]:
        """
        Fetch startup jobs from Wellfound.
        Uses their public job listing search with query params.
        """
        print(f"\n🔍 [{self.source_name}] Searching for: '{query}'")
        all_jobs: list[JobRaw] = []
        query_slug = query.replace(" ", "%20")

        try:
            from bs4 import BeautifulSoup

            for page in range(1, min(max_pages, 3) + 1):
                url = f"{self.BASE_URL}/jobs?q={query_slug}&page={page}"
                response = await self._rate_limited_get(url)

                if response.status_code != 200:
                    print(f"   ⚠️ Page {page}: HTTP {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, "html.parser")

                # Wellfound job card selectors
                cards = (
                    soup.select("div[data-test='StartupResult']") or
                    soup.select("div.styles_component__Ey28k") or
                    soup.select("div[class*='JobListing']") or
                    soup.find_all("div", {"class": lambda c: c and "job" in c.lower() if c else False})
                )

                if not cards:
                    # Fallback: extract any job-like links
                    for link in soup.find_all("a", href=True):
                        href = link.get("href", "")
                        if "/jobs/" in href or "/l/" in href:
                            title = link.get_text(strip=True)
                            if title and 5 < len(title) < 150:
                                full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                                all_jobs.append(JobRaw(
                                    title=title,
                                    company="Startup",
                                    location=location,
                                    description="",
                                    url=full_url,
                                    source=self.source_name,
                                ))
                    break

                for card in cards:
                    try:
                        title_el = card.select_one("a[data-test='job-title']") or card.select_one("h2") or card.select_one("a")
                        title = title_el.get_text(strip=True) if title_el else ""
                        if not title or len(title) < 3:
                            continue

                        company_el = card.select_one("a[data-test='company-link']") or card.select_one("span[class*='company']")
                        company = company_el.get_text(strip=True) if company_el else ""

                        url_el = card.select_one("a[href]")
                        href = url_el.get("href", "") if url_el else ""
                        job_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

                        location_el = card.select_one("span[class*='location']") or card.select_one("[class*='loc']")
                        loc = location_el.get_text(strip=True) if location_el else location

                        all_jobs.append(JobRaw(
                            title=title,
                            company=company,
                            location=loc,
                            description="",
                            url=job_url,
                            source=self.source_name,
                        ))
                    except Exception:
                        continue

                if not cards:
                    break

        except Exception as e:
            print(f"   ❌ Wellfound error: {e}")

        print(f"   ✅ {len(all_jobs)} jobs from {self.source_name}")
        return all_jobs
