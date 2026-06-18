# ============================================================
# Jobs Routes — API Endpoints for Job Scraping & Browsing
# ============================================================
# These endpoints let you:
#   1. Trigger a scrape (search for jobs and store them)
#   2. Browse stored jobs (list, view details, filter)
#   3. Get scraping stats
#
# CONCEPT: Background Tasks
# ─────────────────────────
# Scraping takes time (30-120 seconds). We don't want the user
# staring at a loading spinner that long. Instead:
#   - The API returns immediately with "scraping started"
#   - Scraping runs in the background
#   - User can check results by listing jobs
#
# FastAPI's BackgroundTasks handles this — it runs a function
# AFTER the response is sent, without blocking the request.
# ============================================================

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.config.database import db
from app.models.job import JobExtracted, JobListItem, JobResponse, ScrapeResult
from app.services.scraper_service import scrape_and_store

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


# ── Scrape trigger endpoint ──────────────────────────────

@router.post("/scrape", response_model=list[ScrapeResult])
async def trigger_scrape(
    query: str = Query(
        ...,
        description="Search term (e.g., 'software engineer', 'python developer')",
        examples=["software engineer", "python developer", "react developer"],
    ),
    location: str = Query(
        default="Pakistan",
        description="Job location filter",
    ),
    max_pages: int = Query(
        default=2,
        ge=1,
        le=5,
        description="Pages to scrape per source (1-5).",
    ),
    sources: str = Query(
        default="remotive.com,jobicy.com",
        description="Comma-separated sources: remotive.com, jobicy.com, rozee.pk, remoteok.com, wellfound.com",
    ),
    extract: bool = Query(
        default=True,
        description="Run LLM extraction on job descriptions (uses API credits)",
    ),
    embed: bool = Query(
        default=True,
        description="Generate embeddings for matching (uses API credits)",
    ),
):
    """
    Trigger a job scraping run.
    
    This endpoint:
    1. Scrapes the specified job boards for the query
    2. Deduplicates against existing jobs in the database
    3. Optionally extracts structured requirements with LLM
    4. Optionally generates embeddings for matching
    5. Stores everything in MongoDB
    
    Returns a summary of what was scraped.
    
    EXAMPLE USAGE:
    ─────────────
    POST /api/jobs/scrape?query=python+developer&max_pages=2
    
    This will scrape 2 pages from both Rozee.pk and Indeed.pk
    for "python developer" jobs.
    
    CONCEPT: Query Parameters with Validation
    ──────────────────────────────────────────
    Query(...) defines URL parameters with validation:
      ge=1       → greater or equal to 1
      le=5       → less or equal to 5
      examples   → shown in the Swagger docs
    
    If someone sends max_pages=100, FastAPI automatically
    rejects it with a clear error message.
    """
    source_list = [s.strip() for s in sources.split(",") if s.strip()]

    results = await scrape_and_store(
        query=query,
        location=location,
        max_pages=max_pages,
        sources=source_list,
        extract_with_llm=extract,
        generate_embeddings=embed,
    )

    return results


# ── List all jobs ─────────────────────────────────────────

@router.get("", response_model=list[JobListItem])
async def list_jobs(
    source: str = Query(default=None, description="Filter by source (e.g., 'rozee.pk')"),
    search: str = Query(default=None, description="Filter by job title keyword"),
    query: str = Query(default=None, description="Filter by original search query (e.g., 'python developer')"),
    location: str = Query(default=None, description="Filter by location (e.g., 'Pakistan', 'Remote')"),
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
    skip: int = Query(default=0, ge=0, description="Skip N results (for pagination)"),
):
    """
    List all scraped jobs with optional filters.
    
    CONCEPT: Pagination with skip/limit
    ────────────────────────────────────
    If you have 1000 jobs, you don't want to return all 1000
    at once (slow, wastes bandwidth). Instead:
    
      GET /api/jobs?limit=20&skip=0   → jobs 1-20  (page 1)
      GET /api/jobs?limit=20&skip=20  → jobs 21-40 (page 2)
      GET /api/jobs?limit=20&skip=40  → jobs 41-60 (page 3)
    
    This is the skip/limit pagination pattern.
    
    CONCEPT: MongoDB Queries with Filters
    ──────────────────────────────────────
    We build the query dynamically based on which filters
    the user provided. This is more flexible than separate
    endpoints for each filter combination.
    """
    collection = db.get_collection("jobs")

    # Build query filter
    query_filter: dict = {}

    if source:
        query_filter["source"] = source

    if search:
        # Case-insensitive regex search in title
        query_filter["title"] = {"$regex": search, "$options": "i"}

    # KEY FIX: filter by the original search query used during scraping
    if query:
        query_filter["search_query"] = {"$regex": query.strip().lower(), "$options": "i"}

    # Location filter — match by either stored location field OR search_location
    if location and location.lower() not in ("worldwide", "all", ""):
        loc_lower = location.strip().lower()
        query_filter["$or"] = [
            {"location": {"$regex": loc_lower, "$options": "i"}},
            {"search_location": {"$regex": loc_lower, "$options": "i"}},
        ]

    # Execute query with projection (exclude large fields)
    cursor = collection.find(
        query_filter,
        {
            "description": 0,
            "extracted": 0,
            "embedding": 0,
        }
    ).sort("created_at", -1).skip(skip).limit(limit)

    jobs = []
    async for doc in cursor:
        jobs.append(JobListItem(
            id=str(doc["_id"]),
            title=doc.get("title", ""),
            company=doc.get("company", ""),
            location=doc.get("location", ""),
            salary_range=doc.get("salary_range", ""),
            job_type=doc.get("job_type", ""),
            source=doc.get("source", ""),
            has_embedding=doc.get("has_embedding", False),
            created_at=doc.get("created_at", datetime.now(timezone.utc)).isoformat(),
        ))

    return jobs


# ── Get single job with full details ─────────────────────

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    Get full details of a single job including extracted requirements.
    
    This returns EVERYTHING we know about the job:
    - Original scraped data (title, company, description)
    - LLM-extracted requirements (skills, experience, etc.)
    - Whether it has an embedding (ready for matching)
    """
    collection = db.get_collection("jobs")

    try:
        obj_id = ObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    doc = await collection.find_one(
        {"_id": obj_id},
        {"embedding": 0}  # Exclude the raw embedding vector (768 numbers)
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")

    # Convert extracted data to Pydantic model (if exists)
    extracted = None
    if doc.get("extracted"):
        extracted = JobExtracted(**doc["extracted"])

    return JobResponse(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        company=doc.get("company", ""),
        location=doc.get("location", ""),
        description=doc.get("description", ""),
        salary_range=doc.get("salary_range", ""),
        job_type=doc.get("job_type", ""),
        experience_required=doc.get("experience_required", ""),
        posted_date=doc.get("posted_date", ""),
        url=doc.get("url", ""),
        source=doc.get("source", ""),
        extracted=extracted,
        has_embedding=doc.get("has_embedding", False),
        created_at=doc.get("created_at", datetime.now(timezone.utc)).isoformat(),
    )


# ── Delete a job ──────────────────────────────────────────

@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """Delete a single job by ID."""
    collection = db.get_collection("jobs")

    try:
        obj_id = ObjectId(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    result = await collection.delete_one({"_id": obj_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"message": f"✅ Job {job_id} deleted"}


# ── Stats endpoint ────────────────────────────────────────

@router.get("/stats/overview")
async def get_job_stats():
    """
    Get statistics about scraped jobs.
    
    CONCEPT: MongoDB Aggregation Pipeline
    ──────────────────────────────────────
    Aggregation pipelines let you do complex queries:
    - $group: Group documents by a field (like SQL GROUP BY)
    - $count: Count documents
    - $match: Filter documents
    
    This is more efficient than fetching all documents and
    counting in Python — MongoDB does the math on its own.
    """
    collection = db.get_collection("jobs")

    # Total jobs
    total = await collection.count_documents({})

    # Jobs per source
    pipeline = [
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    sources_cursor = collection.aggregate(pipeline)
    by_source = {}
    async for doc in sources_cursor:
        by_source[doc["_id"] or "unknown"] = doc["count"]

    # Jobs with embeddings
    with_embeddings = await collection.count_documents({"has_embedding": True})

    # Jobs with LLM extraction
    with_extraction = await collection.count_documents({"extracted": {"$ne": None}})

    return {
        "total_jobs": total,
        "by_source": by_source,
        "with_embeddings": with_embeddings,
        "with_extraction": with_extraction,
        "without_embeddings": total - with_embeddings,
    }
