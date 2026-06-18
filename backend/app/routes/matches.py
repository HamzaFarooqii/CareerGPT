# ============================================================
# Matches Routes — API Endpoints for AI Job Matching
# ============================================================
# These endpoints let you:
#   1. Run matching (resume → find best jobs → analyze → rank)
#   2. View match results (ranked list with scores & cover letters)
#   3. Sync vectors (ensure ChromaDB is up to date)
# ============================================================

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.config.database import db
from app.models.match import MatchRequest, MatchResponse
from app.services.matching_service import run_matching
from app.services.vector_store import vector_store

router = APIRouter(prefix="/api/matches", tags=["Matches"])


@router.post("/run-body", response_model=list[MatchResponse])
async def trigger_matching(request: MatchRequest):
    """
    Run the full matching pipeline for a resume.
    
    This is the MAIN feature:
    1. Takes your resume
    2. Finds similar jobs using vector search
    3. LLM deeply analyzes each match
    4. Generates cover letters for top matches
    5. Returns ranked results
    
    Note: This can take 30-90 seconds depending on how many
    jobs are analyzed and how many cover letters are generated.
    """
    try:
        matches = await run_matching(
            resume_id=request.resume_id,
            top_k=request.top_k,
            generate_cover_letters=request.generate_cover_letters,
            cover_letter_count=request.cover_letter_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Matching failed: {str(e)}")

    # Enrich results with job details for the frontend
    jobs_col = db.get_collection("jobs")
    results: list[MatchResponse] = []

    for match in matches:
        # Fetch job info
        job_doc = None
        try:
            job_doc = await jobs_col.find_one(
                {"_id": ObjectId(match.job_id)},
                {"embedding": 0, "extracted": 0}
            )
        except Exception:
            pass

        results.append(MatchResponse(
            id=f"{match.resume_id}_{match.job_id}",
            job_id=match.job_id,
            resume_id=match.resume_id,
            similarity_score=match.similarity_score,
            analysis=match.analysis,
            cover_letter=match.cover_letter,
            created_at=match.created_at,
            job_title=job_doc.get("title", "") if job_doc else "",
            job_company=job_doc.get("company", "") if job_doc else "",
            job_location=job_doc.get("location", "") if job_doc else "",
            job_url=job_doc.get("url", "") if job_doc else "",
            job_source=job_doc.get("source", "") if job_doc else "",
        ))

    return results


@router.post("/run")
async def trigger_matching_query_params(
    resume_id: str = Query(..., description="Resume ID to match against"),
    top_k: int = Query(default=10, ge=1, le=50),
    generate_cover_letters: bool = Query(default=False),
):
    """
    Run matching using URL query parameters (for easy frontend fetch calls).
    Embeds the resume if it doesn't have one yet, then finds best matching jobs.
    """
    resumes_col = db.get_collection("resumes")
    jobs_col = db.get_collection("jobs")

    # ── Auto-embed resume if needed ──────────────────────────
    try:
        from app.services.embedding_service import generate_embedding
        resume_doc = await resumes_col.find_one({"_id": ObjectId(resume_id)})
        if not resume_doc:
            raise HTTPException(status_code=404, detail="Resume not found")

        if not resume_doc.get("full_embedding"):
            print(f"🔄 Auto-embedding resume: {resume_doc.get('title', resume_id)}")
            raw_text = resume_doc.get("raw_text", "")
            if raw_text:
                emb = await generate_embedding(raw_text)
                await resumes_col.update_one(
                    {"_id": ObjectId(resume_id)},
                    {"$set": {"full_embedding": emb, "has_embedding": True}}
                )
                resume_doc["full_embedding"] = emb
                resume_doc["has_embedding"] = True
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume prep failed: {e}")

    # ── Auto-embed jobs that are missing embeddings ───────────
    try:
        from app.services.embedding_service import generate_embedding as ge
        jobs_without_emb = jobs_col.find(
            {"has_embedding": {"$ne": True}, "description": {"$ne": ""}},
            {"_id": 1, "description": 1, "title": 1}
        )
        jobs_to_embed = []
        async for j in jobs_without_emb:
            jobs_to_embed.append(j)
            if len(jobs_to_embed) >= 20:  # Batch limit
                break

        for j in jobs_to_embed:
            text = f"{j.get('title', '')} {j.get('description', '')}"[:6000]
            emb = await ge(text)
            await jobs_col.update_one(
                {"_id": j["_id"]},
                {"$set": {"embedding": emb, "has_embedding": True}}
            )
        if jobs_to_embed:
            print(f"🔄 Auto-embedded {len(jobs_to_embed)} jobs")
    except Exception as e:
        print(f"⚠️ Auto-embed jobs failed: {e}")

    # ── Run the matching pipeline ─────────────────────────────
    try:
        matches = await run_matching(
            resume_id=resume_id,
            top_k=top_k,
            generate_cover_letters=generate_cover_letters,
            cover_letter_count=3,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Matching failed: {str(e)}")

    enriched: list[MatchResponse] = []
    for match in matches:
        job_doc = None
        try:
            job_doc = await jobs_col.find_one({"_id": ObjectId(match.job_id)}, {"embedding": 0})
        except Exception:
            pass
        enriched.append(MatchResponse(
            id=f"{match.resume_id}_{match.job_id}",
            job_id=match.job_id,
            resume_id=match.resume_id,
            similarity_score=match.similarity_score,
            analysis=match.analysis,
            cover_letter=match.cover_letter,
            created_at=match.created_at,
            job_title=job_doc.get("title", "") if job_doc else "",
            job_company=job_doc.get("company", "") if job_doc else "",
            job_location=job_doc.get("location", "") if job_doc else "",
            job_url=job_doc.get("url", "") if job_doc else "",
            job_source=job_doc.get("source", "") if job_doc else "",
        ))
    return enriched


@router.get("", response_model=list[MatchResponse])
async def list_matches(resume_id: str = Query(..., description="Resume ID to get matches for")):
    """Get previously computed matches for a resume (no re-computation)."""
    matches_col = db.get_collection("matches")
    jobs_col = db.get_collection("jobs")

    cursor = matches_col.find({"resume_id": resume_id}).sort("analysis.overall_score", -1).limit(30)
    results: list[MatchResponse] = []

    async for doc in cursor:
        job_doc = None
        try:
            job_doc = await jobs_col.find_one({"_id": ObjectId(doc["job_id"])}, {"embedding": 0})
        except Exception:
            pass

        from app.models.match import MatchAnalysis
        analysis = MatchAnalysis(**doc["analysis"]) if doc.get("analysis") else None

        results.append(MatchResponse(
            id=str(doc["_id"]),
            job_id=doc["job_id"],
            resume_id=doc["resume_id"],
            similarity_score=doc.get("similarity_score", 0),
            analysis=analysis,
            cover_letter=doc.get("cover_letter"),
            created_at=doc.get("created_at", datetime.now(timezone.utc)).isoformat(),
            job_title=job_doc.get("title", "") if job_doc else "",
            job_company=job_doc.get("company", "") if job_doc else "",
            job_location=job_doc.get("location", "") if job_doc else "",
            job_url=job_doc.get("url", "") if job_doc else "",
            job_source=job_doc.get("source", "") if job_doc else "",
        ))

    return results



@router.get("/resume/{resume_id}", response_model=list[MatchResponse])
async def get_matches_for_resume(resume_id: str):
    """
    Get previously computed matches for a resume.
    
    Results are loaded from MongoDB (no re-computation).
    Use POST /run to generate fresh matches.
    """
    matches_col = db.get_collection("matches")
    jobs_col = db.get_collection("jobs")

    cursor = matches_col.find(
        {"resume_id": resume_id}
    ).sort("analysis.overall_score", -1)

    results: list[MatchResponse] = []
    async for doc in cursor:
        job_doc = None
        try:
            job_doc = await jobs_col.find_one(
                {"_id": ObjectId(doc["job_id"])},
                {"embedding": 0, "extracted": 0}
            )
        except Exception:
            pass

        from app.models.match import MatchAnalysis
        analysis = MatchAnalysis(**doc["analysis"]) if doc.get("analysis") else None

        results.append(MatchResponse(
            id=str(doc["_id"]),
            job_id=doc["job_id"],
            resume_id=doc["resume_id"],
            similarity_score=doc.get("similarity_score", 0),
            analysis=analysis,
            cover_letter=doc.get("cover_letter"),
            created_at=doc.get("created_at", datetime.now(timezone.utc)).isoformat(),
            job_title=job_doc.get("title", "") if job_doc else "",
            job_company=job_doc.get("company", "") if job_doc else "",
            job_location=job_doc.get("location", "") if job_doc else "",
            job_url=job_doc.get("url", "") if job_doc else "",
            job_source=job_doc.get("source", "") if job_doc else "",
        ))

    return results


@router.post("/sync-vectors")
async def sync_vectors():
    """
    Sync all embeddings from MongoDB into ChromaDB.
    
    Use this if ChromaDB got out of sync (e.g., after a restart
    or if you manually added data to MongoDB).
    """
    jobs_col = db.get_collection("jobs")
    resumes_col = db.get_collection("resumes")

    # Get all jobs with embeddings
    job_count = 0
    async for doc in jobs_col.find({"has_embedding": True, "embedding": {"$ne": None}}):
        vector_store.add_job(
            job_id=str(doc["_id"]),
            embedding=doc["embedding"],
            title=doc.get("title", ""),
            company=doc.get("company", ""),
            source=doc.get("source", ""),
            document=doc.get("description", "")[:500],
        )
        job_count += 1

    resume_count = 0
    async for doc in resumes_col.find({"full_embedding": {"$ne": None}}):
        vector_store.add_resume(
            resume_id=str(doc["_id"]),
            embedding=doc["full_embedding"],
            title=doc.get("title", ""),
            document=doc.get("raw_text", "")[:500],
        )
        resume_count += 1

    return {
        "message": "✅ Vector store synced",
        "jobs_synced": job_count,
        "resumes_synced": resume_count,
        **vector_store.get_stats(),
    }


@router.get("/stats")
async def match_stats():
    """Get matching system statistics."""
    matches_col = db.get_collection("matches")
    total_matches = await matches_col.count_documents({})

    return {
        "total_matches": total_matches,
        **vector_store.get_stats(),
    }
