# ============================================================
# Rozee.pk Scraper — Pakistan's Largest Job Board
# ============================================================
# Rozee.pk is the biggest job portal in Pakistan (~50k+ jobs).
# This scraper fetches their search results page and extracts
# job listings.
#
# CONCEPT: How Web Scraping Works
# ────────────────────────────────
# 1. We send an HTTP GET request (just like your browser does)
# 2. The server returns HTML (the page's source code)
# 3. We parse the HTML with BeautifulSoup
# 4. We find specific elements using CSS selectors or tag names
# 5. We extract the text/attributes we need
#
# It's like reading a newspaper with a highlighter —
# find the sections you care about and copy the info.
#
# IMPORTANT: Website Structure Changes
# ─────────────────────────────────────
# Websites change their HTML structure regularly. The CSS class
# names used below were chosen based on common patterns, but
# they MAY need updating if Rozee.pk redesigns their site.
# This is the biggest challenge of web scraping — fragility.
# ============================================================

from bs4 import BeautifulSoup

from app.models.job import JobRaw
from app.scrapers.base_scraper import BaseScraper


class RozeeScraper(BaseScraper):
    """Scraper for rozee.pk job listings."""

    BASE_URL = "https://www.rozee.pk"

    def __init__(self):
        super().__init__(source_name="rozee.pk")

    async def scrape_jobs(
        self, query: str, location: str = "Pakistan", max_pages: int = 3
    ) -> list[JobRaw]:
        """
        Scrape Rozee.pk search results.
        
        HOW ROZEE.PK SEARCH WORKS:
        ──────────────────────────
        URL pattern: https://www.rozee.pk/job/jsearch/q/{query}
        The search term goes directly in the URL path.
        Pagination uses ?fpn=2 for page 2, ?fpn=3 for page 3, etc.
        
        CONCEPT: URL Query Parameters
        ─────────────────────────────
        The part after ? in a URL is query parameters:
          https://rozee.pk/job/jsearch/q/python?fpn=2&sort=date
          
          fpn=2  → page number 2
          sort=date → sort by date
        
        These tell the server what data to return.
        """
        all_jobs: list[JobRaw] = []
        query_slug = query.replace(" ", "-")

        print(f"\n🔍 [{self.source_name}] Searching for: '{query}'")

        for page in range(1, max_pages + 1):
            try:
                # Build the search URL
                if page == 1:
                    url = f"{self.BASE_URL}/job/jsearch/q/{query_slug}"
                else:
                    url = f"{self.BASE_URL}/job/jsearch/q/{query_slug}?fpn={page}"

                # Fetch the page
                response = await self._rate_limited_get(url)

                # Check if request was successful
                # HTTP 200 = OK, 404 = Not Found, 403 = Forbidden, etc.
                if response.status_code != 200:
                    print(f"   ⚠️ Page {page}: HTTP {response.status_code}")
                    continue

                # Parse HTML with BeautifulSoup
                #
                # CONCEPT: HTML Parsing
                # ─────────────────────
                # BeautifulSoup takes raw HTML like:
                #   <div class="job"><h2>Python Dev</h2><span>Lahore</span></div>
                #
                # And lets you query it:
                #   soup.find("h2").text  → "Python Dev"
                #   soup.find("span").text → "Lahore"
                #
                # "html.parser" is Python's built-in HTML parser.
                soup = BeautifulSoup(response.text, "html.parser")

                # Find all job listing cards on the page.
                # We look for common container elements that Rozee uses.
                job_cards = soup.select("div.job") or soup.select("div[class*='job-listing']")

                # Fallback: if specific selectors don't work, try generic approach
                if not job_cards:
                    job_cards = soup.find_all("div", attrs={"data-job-id": True})

                # If still no jobs found, try finding any links that look like job URLs
                if not job_cards:
                    jobs_from_links = self._extract_from_links(soup)
                    all_jobs.extend(jobs_from_links)
                    print(f"   📄 Page {page}: {len(jobs_from_links)} jobs (from links)")
                    continue

                # Extract data from each job card
                page_jobs = []
                for card in job_cards:
                    job = self._parse_job_card(card)
                    if job:
                        page_jobs.append(job)

                all_jobs.extend(page_jobs)
                print(f"   📄 Page {page}: {len(page_jobs)} jobs found")

                # If no jobs found on this page, stop pagination
                # (we've gone past the last page)
                if len(page_jobs) == 0:
                    print(f"   ⏹️ No more results after page {page}")
                    break

            except Exception as e:
                print(f"   ❌ Page {page} error: {e}")
                continue

        print(f"   ✅ Total: {len(all_jobs)} jobs from {self.source_name}")
        return all_jobs

    def _parse_job_card(self, card) -> JobRaw | None:
        """
        Extract job data from a single HTML card element.
        
        CONCEPT: Defensive Parsing
        ──────────────────────────
        Web scraping is inherently fragile. An element might:
        - Not exist (the job doesn't list a salary)
        - Have different structure than expected
        - Contain unexpected whitespace/characters
        
        We use .get_text(strip=True) to handle whitespace and
        wrap everything in try/except to handle missing elements.
        The `or ""` pattern means "if None, use empty string."
        """
        try:
            # Title — usually in an <a> or <h2> tag
            title_el = (
                card.select_one("h2 a")
                or card.select_one("a[class*='title']")
                or card.select_one("h2")
                or card.select_one("a")
            )
            title = title_el.get_text(strip=True) if title_el else ""

            # URL — the link to the full job posting
            url = ""
            if title_el and title_el.get("href"):
                href = title_el["href"]
                # Handle relative URLs (just the path, no domain)
                if href.startswith("/"):
                    url = f"{self.BASE_URL}{href}"
                elif href.startswith("http"):
                    url = href
                else:
                    url = f"{self.BASE_URL}/{href}"

            # Company name
            company_el = (
                card.select_one("span[class*='company']")
                or card.select_one("div[class*='company']")
                or card.select_one(".cname")
            )
            company = company_el.get_text(strip=True) if company_el else ""

            # Location
            location_el = (
                card.select_one("span[class*='location']")
                or card.select_one("div[class*='location']")
                or card.select_one(".loc")
            )
            location = location_el.get_text(strip=True) if location_el else ""

            # Description preview (full description is on the job detail page)
            desc_el = (
                card.select_one("div[class*='desc']")
                or card.select_one("p")
            )
            description = desc_el.get_text(strip=True) if desc_el else ""

            # Skip if we couldn't extract a title (this card is probably not a job)
            if not title or len(title) < 3:
                return None

            return JobRaw(
                title=title,
                company=company,
                location=location,
                description=description,
                url=url,
                source=self.source_name,
            )

        except Exception as e:
            print(f"   ⚠️ Parse error: {e}")
            return None

    def _extract_from_links(self, soup) -> list[JobRaw]:
        """
        Fallback extraction: find job links if structured cards aren't found.
        
        Sometimes the page structure doesn't match our selectors.
        In that case, we look for any links that point to /job/ pages.
        We get less data this way (no company, location) but at least
        we capture the jobs.
        """
        jobs = []
        seen_urls = set()

        for link in soup.find_all("a", href=True):
            href = link["href"]

            # Only process links that look like job postings
            if "/job/" not in href and "/jobs/" not in href:
                continue

            # Build full URL
            if href.startswith("/"):
                full_url = f"{self.BASE_URL}{href}"
            elif href.startswith("http"):
                full_url = href
            else:
                continue

            # Skip duplicates
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
