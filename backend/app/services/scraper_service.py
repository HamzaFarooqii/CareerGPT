# ============================================================
# Scraper Service — Orchestrates Scraping + Extraction + Storage
# ============================================================
# KEY FIXES:
# 1. Every job now stores `search_query` AND `search_location`
# 2. Smart source routing: Pakistan → Rozee.pk; Remote → Remotive/RemoteOK
# 3. Location validation: jobs from remote boards marked as "Remote"
# ============================================================

import time
from datetime import datetime, timezone

from app.agents.extraction_agent import extract_job_requirements
from app.config.database import db
from app.models.job import JobRaw, ScrapeResult
from app.scrapers.remotive_scraper import RemotiveScraper
from app.scrapers.jobicy_scraper import JobicyScraper
from app.scrapers.rozee_scraper import RozeeScraper
from app.services.embedding_service import generate_embedding


# Maps which sources are actually useful for each location context
LOCATION_SOURCE_MAP = {
    "pakistan":   ["rozee.pk"],
    "remote":     ["remotive.com", "jobicy.com", "remoteok.com"],
    "worldwide":  ["remotive.com", "jobicy.com", "remoteok.com", "wellfound.com"],
    "usa":        ["remotive.com", "remoteok.com", "wellfound.com"],
    "uk":         ["remotive.com", "remoteok.com", "wellfound.com"],
    "canada":     ["remotive.com", "remoteok.com"],
    "australia":  ["remotive.com", "remoteok.com"],
    "germany":    ["remotive.com", "remoteok.com"],
    "uae":        ["remotive.com", "rozee.pk"],
}

# These sources only have remote jobs — don't pretend they have local jobs
REMOTE_ONLY_SOURCES = {"remotive.com", "jobicy.com", "remoteok.com", "wellfound.com"}

# Location override for remote-only boards
REMOTE_ONLY_LOCATION = "Remote"


def _get_scraper(source: str):
    """Return the correct scraper instance for a source name."""
    mapping = {
        "remotive.com": RemotiveScraper,
        "jobicy.com": JobicyScraper,
        "rozee.pk": RozeeScraper,
    }
    if source == "remoteok.com":
        try:
            from app.scrapers.remoteok_scraper import RemoteOKScraper
            return RemoteOKScraper()
        except ImportError:
            return None
    if source == "wellfound.com":
        try:
            from app.scrapers.wellfound_scraper import WellfoundScraper
            return WellfoundScraper()
        except ImportError:
            return None
    cls = mapping.get(source)
    return cls() if cls else None


def _smart_sources(requested_sources: list[str], location: str) -> list[str]:
    """
    Filter requested sources to only those relevant for the selected location.
    If user selects Pakistan, only Pakistan-capable sources are used.
    If user selects Remote/Worldwide, only remote boards are used.
    """
    loc_key = location.strip().lower()
    relevant = LOCATION_SOURCE_MAP.get(loc_key)

    if relevant is None:
        # Unknown location — use remote boards (they have global/international listings)
        relevant = list(REMOTE_ONLY_SOURCES)

    # Intersection: only sources that were requested AND are relevant
    filtered = [s for s in requested_sources if s in relevant]

    # If nothing matched, fall back to all requested sources
    return filtered if filtered else requested_sources


def _get_effective_location(source: str, user_location: str) -> str:
    """
    Return the effective location to store on the job document.
    Remote-only boards always return remote jobs regardless of what user typed.
    """
    if source in REMOTE_ONLY_SOURCES:
        return REMOTE_ONLY_LOCATION
    return user_location


async def scrape_and_store(
    query: str,
    location: str = "Pakistan",
    max_pages: int = 2,
    sources: list[str] | None = None,
    extract_with_llm: bool = True,
    generate_embeddings: bool = True,
) -> list[ScrapeResult]:
    """
    Full scraping pipeline: scrape → smart-filter by location → deduplicate → extract → embed → store.
    """
    if sources is None:
        sources = ["remotive.com", "jobicy.com"]

    # Smart source routing based on location
    effective_sources = _smart_sources(sources, location)
    skipped_sources = [s for s in sources if s not in effective_sources]

    if skipped_sources:
        print(f"\n⚠️  Skipping sources not relevant for '{location}': {skipped_sources}")

    results: list[ScrapeResult] = []
    collection = db.get_collection("jobs")

    # Pre-load existing URLs to avoid re-storing duplicates
    existing_urls: set[str] = set()
    async for doc in collection.find({}, {"url": 1}):
        if doc.get("url"):
            existing_urls.add(doc["url"])

    print(f"\n{'='*55}")
    print(f"🚀 CareerPilot scrape pipeline")
    print(f"   Query:    '{query}'")
    print(f"   Location: '{location}'")
    print(f"   Sources:  {effective_sources}")
    print(f"{'='*55}")

    # Add placeholder results for skipped sources
    for src in skipped_sources:
        results.append(ScrapeResult(
            source=src, jobs_found=0, jobs_new=0,
            jobs_duplicate=0,
            errors=[f"Skipped: not relevant for location '{location}'"],
            duration_seconds=0,
        ))

    for source in effective_sources:
        start_time = time.time()
        errors: list[str] = []

        scraper = _get_scraper(source)
        if not scraper:
            errors.append(f"Unknown or unavailable source: {source}")
            results.append(ScrapeResult(
                source=source, jobs_found=0, jobs_new=0,
                jobs_duplicate=0, errors=errors, duration_seconds=0,
            ))
            continue

        try:
            # For Pakistan-specific sources, pass Pakistan as location
            # For remote boards, location doesn't filter server-side (handled client-side by query)
            scrape_location = "Remote" if source in REMOTE_ONLY_SOURCES else location
            raw_jobs: list[JobRaw] = await scraper.scrape_jobs(query, scrape_location, max_pages)

            # Deduplicate
            new_jobs: list[JobRaw] = []
            duplicate_count = 0
            for job in raw_jobs:
                if job.url and job.url in existing_urls:
                    duplicate_count += 1
                else:
                    new_jobs.append(job)
                    if job.url:
                        existing_urls.add(job.url)

            print(f"\n   📊 {source}: {len(raw_jobs)} found, "
                  f"{len(new_jobs)} new, {duplicate_count} duplicates")

            # The effective location to store on the job
            stored_location = _get_effective_location(source, location)

            for i, job in enumerate(new_jobs):
                print(f"\n   [{i+1}/{len(new_jobs)}]: {job.title[:50]}...")

                job_doc: dict = {
                    "title": job.title,
                    "company": job.company,
                    # Use the job's own location if it has one, else the effective location
                    "location": job.location if job.location else stored_location,
                    "description": job.description,
                    "salary_range": job.salary_range,
                    "job_type": job.job_type,
                    "experience_required": job.experience_required,
                    "posted_date": job.posted_date,
                    "url": job.url,
                    "source": job.source,
                    # Store both search context fields for proper filtering
                    "search_query": query.strip().lower(),
                    "search_location": location.strip().lower(),
                    "created_at": datetime.now(timezone.utc),
                    "extracted": None,
                    "has_embedding": False,
                    "embedding": None,
                }

                # LLM extraction
                if extract_with_llm and job.description and len(job.description) > 20:
                    try:
                        extracted = await extract_job_requirements(job.title, job.description)
                        job_doc["extracted"] = extracted.model_dump()
                    except Exception as e:
                        errors.append(f"Extraction failed for '{job.title}': {e}")
                        print(f"   ⚠️ {errors[-1]}")

                # Generate embedding
                if generate_embeddings:
                    try:
                        embed_text = f"{job.title} {job.company} {job.description}"
                        if job_doc.get("extracted"):
                            skills = (
                                job_doc["extracted"].get("required_skills", [])
                                + job_doc["extracted"].get("preferred_skills", [])
                            )
                            if skills:
                                embed_text += " " + " ".join(skills)
                        embedding = await generate_embedding(embed_text[:2000])
                        job_doc["embedding"] = embedding
                        job_doc["has_embedding"] = True
                    except Exception as e:
                        errors.append(f"Embedding failed for '{job.title}': {e}")
                        print(f"   ⚠️ {errors[-1]}")

                await collection.insert_one(job_doc)

            duration = time.time() - start_time
            results.append(ScrapeResult(
                source=source,
                jobs_found=len(raw_jobs),
                jobs_new=len(new_jobs),
                jobs_duplicate=duplicate_count,
                errors=errors,
                duration_seconds=round(duration, 1),
            ))

        except Exception as e:
            duration = time.time() - start_time
            errors.append(f"Scraper crashed: {e}")
            results.append(ScrapeResult(
                source=source, jobs_found=0, jobs_new=0,
                jobs_duplicate=0, errors=errors,
                duration_seconds=round(duration, 1),
            ))

        finally:
            try:
                await scraper.close()
            except Exception:
                pass

    print(f"\n{'='*55}")
    print(f"✅ Scrape complete!")
    for r in results:
        emoji = "✅" if not r.errors else "⚠️"
        print(f"   {emoji} {r.source}: {r.jobs_new} new ({r.duration_seconds}s)")
    print(f"{'='*55}\n")

    return results
