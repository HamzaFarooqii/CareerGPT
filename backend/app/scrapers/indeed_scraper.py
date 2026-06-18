# ============================================================
# Indeed.pk Scraper — Global Job Board, Pakistan Edition
# ============================================================
# Indeed is available worldwide. The Pakistan version is at
# pk.indeed.com. Their HTML structure is different from Rozee,
# so we need a separate parser — but the overall flow is identical
# because we inherit from BaseScraper.
#
# CONCEPT: Why Multiple Scrapers?
# ────────────────────────────────
# Different job boards have different jobs. A company might post
# on Rozee but not Indeed, or vice versa. By scraping multiple
# sources, we maximize coverage and give users the best matches.
# ============================================================

from bs4 import BeautifulSoup

from app.models.job import JobRaw
from app.scrapers.base_scraper import BaseScraper


class IndeedScraper(BaseScraper):
    """Scraper for pk.indeed.com job listings."""

    BASE_URL = "https://pk.indeed.com"

    def __init__(self):
        super().__init__(source_name="indeed.pk")

    async def scrape_jobs(
        self, query: str, location: str = "Pakistan", max_pages: int = 3
    ) -> list[JobRaw]:
        """
        Scrape Indeed Pakistan search results.
        
        HOW INDEED SEARCH WORKS:
        ────────────────────────
        URL: https://pk.indeed.com/jobs?q=software+engineer&l=Lahore&start=10
        
        Parameters:
          q = search query
          l = location
          start = result offset (0 = page 1, 10 = page 2, 20 = page 3)
        
        Indeed shows 10-15 jobs per page.
        """
        all_jobs: list[JobRaw] = []

        print(f"\n🔍 [{self.source_name}] Searching for: '{query}' in '{location}'")

        for page in range(max_pages):
            try:
                # Indeed uses "start" offset: 0, 10, 20, 30...
                start = page * 10

                url = (
                    f"{self.BASE_URL}/jobs"
                    f"?q={query.replace(' ', '+')}"
                    f"&l={location.replace(' ', '+')}"
                    f"&start={start}"
                )

                response = await self._rate_limited_get(url)

                if response.status_code != 200:
                    print(f"   ⚠️ Page {page + 1}: HTTP {response.status_code}")
                    continue

                soup = BeautifulSoup(response.text, "html.parser")

                # Indeed uses different container classes. Try multiple selectors.
                #
                # CONCEPT: CSS Selectors
                # ──────────────────────
                # CSS selectors are patterns for finding HTML elements:
                #   div.job-card       → <div class="job-card">
                #   div[data-jk]       → <div data-jk="abc123">
                #   h2 > a             → <h2><a>...</a></h2>
                #   span.company       → <span class="company">
                #
                # The ">" means direct child. A space means any descendant.
                job_cards = (
                    soup.select("div.job_seen_beacon")
                    or soup.select("div.jobsearch-SerpJobCard")
                    or soup.select("div[data-jk]")
                    or soup.select("div.result")
                    or soup.select("li.css-5lfssm")
                )

                if not job_cards:
                    # Fallback: extract from any links to /viewjob
                    jobs_from_links = self._extract_from_links(soup)
                    all_jobs.extend(jobs_from_links)
                    print(f"   📄 Page {page + 1}: {len(jobs_from_links)} jobs (from links)")
                    if len(jobs_from_links) == 0:
                        break
                    continue

                page_jobs = []
                for card in job_cards:
                    job = self._parse_job_card(card)
                    if job:
                        page_jobs.append(job)

                all_jobs.extend(page_jobs)
                print(f"   📄 Page {page + 1}: {len(page_jobs)} jobs found")

                if len(page_jobs) == 0:
                    print(f"   ⏹️ No more results after page {page + 1}")
                    break

            except Exception as e:
                print(f"   ❌ Page {page + 1} error: {e}")
                continue

        print(f"   ✅ Total: {len(all_jobs)} jobs from {self.source_name}")
        return all_jobs

    def _parse_job_card(self, card) -> JobRaw | None:
        """Extract job data from an Indeed job card element."""
        try:
            # Title
            title_el = (
                card.select_one("h2.jobTitle a")
                or card.select_one("a[data-jk]")
                or card.select_one("h2 a")
                or card.select_one("a[class*='title']")
            )
            title = ""
            url = ""
            if title_el:
                # Indeed sometimes wraps title text in a <span>
                title_span = title_el.select_one("span")
                title = (title_span or title_el).get_text(strip=True)

                href = title_el.get("href", "")
                if href.startswith("/"):
                    url = f"{self.BASE_URL}{href}"
                elif href.startswith("http"):
                    url = href

            # Company
            company_el = (
                card.select_one("span[data-testid='company-name']")
                or card.select_one("span.companyName")
                or card.select_one("span.company")
                or card.select_one("div[class*='company']")
            )
            company = company_el.get_text(strip=True) if company_el else ""

            # Location
            location_el = (
                card.select_one("div[data-testid='text-location']")
                or card.select_one("div.companyLocation")
                or card.select_one("span[class*='location']")
            )
            location = location_el.get_text(strip=True) if location_el else ""

            # Description snippet
            desc_el = (
                card.select_one("div.job-snippet")
                or card.select_one("div[class*='snippet']")
                or card.select_one("table td.snip")
            )
            description = desc_el.get_text(strip=True) if desc_el else ""

            # Salary (Indeed sometimes shows salary)
            salary_el = (
                card.select_one("div[class*='salary']")
                or card.select_one("span[class*='salary']")
                or card.select_one("div.metadata.salary-snippet-container")
            )
            salary = salary_el.get_text(strip=True) if salary_el else ""

            if not title or len(title) < 3:
                return None

            return JobRaw(
                title=title,
                company=company,
                location=location,
                description=description,
                salary_range=salary,
                url=url,
                source=self.source_name,
            )

        except Exception as e:
            print(f"   ⚠️ Parse error: {e}")
            return None

    def _extract_from_links(self, soup) -> list[JobRaw]:
        """Fallback: extract jobs from links that look like job postings."""
        jobs = []
        seen_urls = set()

        for link in soup.find_all("a", href=True):
            href = link["href"]

            if "/viewjob" not in href and "/rc/clk" not in href:
                continue

            if href.startswith("/"):
                full_url = f"{self.BASE_URL}{href}"
            elif href.startswith("http"):
                full_url = href
            else:
                continue

            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            title = link.get_text(strip=True)
            if title and len(title) > 5 and len(title) < 200:
                jobs.append(JobRaw(
                    title=title,
                    company="",
                    location="",
                    description="",
                    url=full_url,
                    source=self.source_name,
                ))

        return jobs
