# ============================================================
# Matching Service — Orchestrates the Full Matching Pipeline
# ============================================================
# This is the BRAIN of Phase 3. It ties together:
#   1. Vector store (find similar jobs fast)
#   2. Matching agent (LLM scores each match deeply)
#   3. Cover letter agent (generates tailored letters)
#   4. MongoDB (stores results)
#
# THE MATCHING PIPELINE:
# ──────────────────────
#   Step 1: RETRIEVE — Get the resume embedding from MongoDB
#   Step 2: SEARCH — ChromaDB finds top N similar jobs
#   Step 3: ENRICH — Load full job data from MongoDB
#   Step 4: ANALYZE — LLM deeply scores each match
#   Step 5: RANK — Sort by overall score
#   Step 6: GENERATE — Write cover letters for top matches
#   Step 7: STORE — Save match results to MongoDB
#   Step 8: RETURN — Send ranked results to the user
# ============================================================

from datetime import datetime, timezone

from bson import ObjectId

from app.agents.cover_letter_agent import generate_cover_letter
from app.agents.matching_agent import analyze_match
from app.config.database import db
from app.models.match import MatchResult
from app.services.vector_store import vector_store


async def run_matching(
    resume_id: str,
    top_k: int = 15,
    generate_cover_letters: bool = True,
    cover_letter_count: int = 3,
) -> list[MatchResult]:
    """
    Full matching pipeline: find jobs → analyze → rank → generate cover letters.
    
    Args:
        resume_id: MongoDB ObjectId of the resume to match
        top_k: Number of top matches to return
        generate_cover_letters: Whether to generate cover letters
        cover_letter_count: How many top matches get cover letters
    
    Returns:
        List of MatchResult objects, ranked by overall score
    """
    resumes_col = db.get_collection("resumes")
    jobs_col = db.get_collection("jobs")
    matches_col = db.get_collection("matches")

    # ── Step 1: Get resume ────────────────────────────────
    print(f"\n{'='*50}")
    print(f"🎯 Starting matching pipeline for resume: {resume_id}")
    print(f"{'='*50}")

    try:
        resume_doc = await resumes_col.find_one({"_id": ObjectId(resume_id)})
    except Exception:
        raise ValueError(f"Invalid resume ID: {resume_id}")

    if not resume_doc:
        raise ValueError(f"Resume not found: {resume_id}")

    if not resume_doc.get("full_embedding"):
        raise ValueError("Resume has no embedding. Upload it again to generate embeddings.")

    resume_text = resume_doc.get("raw_text", "")
    resume_embedding = resume_doc["full_embedding"]

    print(f"📄 Resume: {resume_doc.get('title', 'Untitled')} ({len(resume_text)} chars)")

    # ── Step 2: Sync vectors to ChromaDB ──────────────────
    # Ensure ChromaDB has all the latest job embeddings
    jobs_with_embeddings = jobs_col.find(
        {"has_embedding": True, "embedding": {"$ne": None}},
        {"embedding": 1, "title": 1, "company": 1, "source": 1, "description": 1}
    )

    job_sync_count = 0
    async for job_doc in jobs_with_embeddings:
        vector_store.add_job(
            job_id=str(job_doc["_id"]),
            embedding=job_doc["embedding"],
            title=job_doc.get("title", ""),
            company=job_doc.get("company", ""),
            source=job_doc.get("source", ""),
            document=job_doc.get("description", "")[:500],
        )
        job_sync_count += 1

    print(f"🔄 Synced {job_sync_count} jobs to ChromaDB")

    if job_sync_count == 0:
        raise ValueError("No jobs with embeddings found. Scrape some jobs first!")

    # ── Step 3: Vector similarity search ──────────────────
    print(f"🔍 Searching for top {top_k} similar jobs...")

    search_results = vector_store.find_similar_jobs(
        query_embedding=resume_embedding,
        top_k=top_k,
    )

    # Extract results
    job_ids = search_results["ids"][0] if search_results["ids"] else []
    distances = search_results["distances"][0] if search_results["distances"] else []

    if not job_ids:
        print("   ❌ No similar jobs found")
        return []

    # Convert distances to similarity scores
    # ChromaDB cosine distance: similarity = 1 - distance
    similarities = [round(1 - d, 4) for d in distances]

    print(f"   Found {len(job_ids)} candidates (similarity range: "
          f"{min(similarities):.3f} — {max(similarities):.3f})")

    # ── Step 4: Load full job data + LLM analysis ─────────
    match_results: list[MatchResult] = []

    for i, (job_id, similarity) in enumerate(zip(job_ids, similarities)):
        print(f"\n   [{i+1}/{len(job_ids)}] Analyzing job: {job_id} (similarity: {similarity:.3f})")

        # Load full job data from MongoDB
        try:
            job_doc = await jobs_col.find_one(
                {"_id": ObjectId(job_id)},
                {"embedding": 0}  # Exclude embedding to save memory
            )
        except Exception:
            continue

        if not job_doc:
            continue

        job_title = job_doc.get("title", "")
        job_desc = job_doc.get("description", "")
        job_extracted = job_doc.get("extracted")

        # Run LLM matching analysis
        analysis = await analyze_match(
            resume_text=resume_text,
            job_title=job_title,
            job_description=job_desc,
            job_requirements=job_extracted,
        )

        match_result = MatchResult(
            job_id=job_id,
            resume_id=resume_id,
            similarity_score=similarity,
            analysis=analysis,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        match_results.append(match_result)

    # ── Step 5: Rank by overall score ─────────────────────
    match_results.sort(
        key=lambda m: (m.analysis.overall_score if m.analysis else 0),
        reverse=True,
    )

    print(f"\n📊 Rankings:")
    for i, m in enumerate(match_results[:10]):
        score = m.analysis.overall_score if m.analysis else 0
        rec = m.analysis.recommendation if m.analysis else "?"
        print(f"   #{i+1}: score={score}/10, similarity={m.similarity_score:.3f} — {rec}")

    # ── Step 6: Generate cover letters for top matches ────
    if generate_cover_letters:
        for i, match in enumerate(match_results[:cover_letter_count]):
            print(f"\n   ✉️ Generating cover letter for match #{i+1}...")

            job_doc = await jobs_col.find_one(
                {"_id": ObjectId(match.job_id)},
                {"embedding": 0}
            )
            if not job_doc:
                continue

            result = await generate_cover_letter(
                resume_text=resume_text,
                job_title=job_doc.get("title", ""),
                company=job_doc.get("company", ""),
                job_description=job_doc.get("description", ""),
                matching_skills=match.analysis.matching_skills if match.analysis else None,
                strong_points=match.analysis.strong_points if match.analysis else None,
            )

            match.cover_letter = result.get("cover_letter", "")

    # ── Step 7: Store results in MongoDB ──────────────────
    if match_results:
        # Delete previous matches for this resume
        await matches_col.delete_many({"resume_id": resume_id})

        # Insert new matches
        docs = []
        for m in match_results:
            doc = {
                "job_id": m.job_id,
                "resume_id": m.resume_id,
                "similarity_score": m.similarity_score,
                "analysis": m.analysis.model_dump() if m.analysis else None,
                "cover_letter": m.cover_letter,
                "created_at": datetime.now(timezone.utc),
            }
            docs.append(doc)

        await matches_col.insert_many(docs)
        print(f"\n💾 Saved {len(docs)} match results to MongoDB")

    print(f"\n{'='*50}")
    print(f"✅ Matching complete! {len(match_results)} matches analyzed")
    print(f"{'='*50}\n")

    return match_results
