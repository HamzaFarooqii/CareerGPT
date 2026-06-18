# ============================================================
# Base Scraper — Abstract Pattern for All Scrapers
# ============================================================
# This is the BLUEPRINT that all scrapers follow.
#
# CONCEPT: Abstract Base Class (ABC)
# ───────────────────────────────────
# An abstract class defines WHAT a scraper should do, but not
# HOW. Each specific scraper (Rozee, Indeed) fills in the HOW.
#
# Think of it like a recipe template:
#   Abstract: "Step 1: Get ingredients. Step 2: Cook. Step 3: Serve."
#   Rozee:    "Step 1: Fetch rozee.pk. Step 2: Parse their HTML. Step 3: Return jobs."
#   Indeed:   "Step 1: Fetch indeed.pk. Step 2: Parse their HTML. Step 3: Return jobs."
#
# WHY use this pattern?
# 1. Consistency — all scrapers behave the same way
# 2. Easy to add new sources — just implement the template
# 3. The orchestrator doesn't care which scraper it's using
#
# CONCEPT: Polite Scraping
# ────────────────────────
# Web scraping is legal but you should be polite:
# - Add delays between requests (don't DDoS the server)
# - Identify yourself with a User-Agent header
# - Respect robots.txt (some sites say "don't scrape these pages")
# - Don't scrape behind login walls
# ============================================================

import asyncio
import time
from abc import ABC, abstractmethod

import httpx

from app.models.job import JobRaw


class BaseScraper(ABC):
    """
    Abstract base class for all job board scrapers.
    
    Every scraper MUST implement:
      - scrape_jobs(query, location, max_pages) → list of JobRaw
    
    Every scraper GETS for free:
      - HTTP client with proper headers
      - Rate limiting
      - Error handling
      - Logging
    """

    def __init__(self, source_name: str):
        # Name of this source (used in logs and database)
        self.source_name = source_name

        # HTTP client with browser-like headers.
        #
        # CONCEPT: User-Agent Header
        # ──────────────────────────
        # When your browser visits a website, it sends a "User-Agent"
        # header saying "I'm Chrome on Windows." Websites use this to:
        # 1. Serve the right version of the page
        # 2. Block bots (if User-Agent says "Python-httpx", some sites block you)
        #
        # We set a realistic User-Agent so websites treat us like a real browser.
        # This is standard practice — NOT deceptive. We're just reading public pages.
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=30.0,       # Wait max 30 seconds per request
            follow_redirects=True,  # Follow URL redirects automatically
        )

        # Rate limiting: minimum seconds between requests
        self.request_delay = 2.0  # Be polite — wait 2 seconds between requests
        self._last_request_time = 0.0

    async def _rate_limited_get(self, url: str) -> httpx.Response:
        """
        Make an HTTP GET request with rate limiting.
        
        CONCEPT: Rate Limiting
        ──────────────────────
        Without this, our scraper would fire 100 requests in 1 second,
        which:
        1. Might get our IP blocked
        2. Puts unnecessary load on the website
        3. Is just rude
        
        We enforce a minimum delay between requests.
        """
        # Calculate how long to wait
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_delay:
            wait_time = self.request_delay - elapsed
            await asyncio.sleep(wait_time)

        self._last_request_time = time.time()

        # Make the request
        response = await self.client.get(url)
        print(f"   🌐 [{self.source_name}] GET {url[:80]}... → {response.status_code}")
        return response

    @abstractmethod
    async def scrape_jobs(
        self, query: str, location: str = "Pakistan", max_pages: int = 3
    ) -> list[JobRaw]:
        """
        Scrape job listings matching the query.
        
        Args:
            query: Search term (e.g., "software engineer", "python developer")
            location: Job location filter
            max_pages: Maximum pages of results to scrape (more pages = more jobs but slower)
        
        Returns:
            List of raw job listings
        
        This method MUST be implemented by each specific scraper.
        The @abstractmethod decorator ensures you get an error if
        you forget to implement it.
        """
        pass

    async def close(self):
        """Close the HTTP client. Call this when done scraping."""
        await self.client.aclose()
