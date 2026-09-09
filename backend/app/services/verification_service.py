# ============================================================
# Verification Service — Daily Job Health Checking
# ============================================================
# Periodically verifies that stored job URLs are still live.
# Dead jobs (404, 410, connection refused) are marked inactive.
# ============================================================

import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass

import httpx

from app.config.database import db


@dataclass
class VerificationResult:
    checked: int
    still_active: int
    marked_inactive: int
    errors: int
    duration_seconds: float


# 403 deliberately excluded: it means the SITE is blocking this request (and
# this checker identifies itself as "CareerGPT-Bot", which many sites will
# reject on sight), not that the posting itself is gone. Treating it as dead
# would mass-deactivate perfectly live jobs from any bot-averse site. 301 is
# excluded too — a redirect (e.g. to a "similar jobs" page after a reorg)
# isn't proof of deletion either.
DEAD_STATUS_CODES = {404, 410}


async def _check_url(client: httpx.AsyncClient, url: str) -> bool:
    """HEAD request a URL. Returns True if job is still live."""
    if not url:
        return True  # Can't verify, assume active
    try:
        resp = await client.head(url, timeout=10.0, follow_redirects=True)
        if resp.status_code in DEAD_STATUS_CODES:
            return False
        return True
    except Exception:
        # Network errors are not definitive — don't mark inactive
        return True


async def verify_jobs_batch(limit: int = 100) -> VerificationResult:
    """
    Check a batch of active jobs to see if their URLs are still live.
    Call this daily via the admin endpoint.

    - Only checks jobs that haven't been verified in 24+ hours
    - Marks dead jobs as is_active=False
    """
    import time
    start = time.time()

    jobs_col = db.get_collection("jobs")
    now = datetime.now(timezone.utc)
    one_day_ago = now.timestamp() - 86400

    # Find jobs that need verification: active + not verified recently
    cursor = jobs_col.find(
        {
            "is_active": {"$ne": False},
            "$or": [
                {"last_verified_at": {"$exists": False}},
                {"last_verified_at": {"$lt": datetime.fromtimestamp(one_day_ago, timezone.utc)}},
            ]
        },
        {"_id": 1, "url": 1, "canonical_url": 1}
    ).limit(limit)

    docs = []
    async for doc in cursor:
        docs.append(doc)

    if not docs:
        return VerificationResult(0, 0, 0, 0, 0.0)

    checked = 0
    still_active = 0
    marked_inactive = 0
    errors = 0

    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (compatible; CareerGPT-Bot/1.0)"},
        timeout=12.0,
        follow_redirects=True,
    ) as client:
        # Process in small batches to avoid overwhelming servers
        batch_size = 10
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i + batch_size]
            tasks = []
            for doc in batch:
                url = doc.get("url") or doc.get("canonical_url", "")
                tasks.append(_check_url(client, url))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, (doc, result) in enumerate(zip(batch, results)):
                checked += 1
                is_alive = result if isinstance(result, bool) else True

                update_data: dict = {"last_verified_at": now}
                if not is_alive:
                    update_data["is_active"] = False
                    marked_inactive += 1
                    print(f"   💀 Dead job detected: {doc.get('url', '')[:60]}")
                else:
                    still_active += 1

                await jobs_col.update_one(
                    {"_id": doc["_id"]},
                    {"$set": update_data}
                )

            # Polite delay between batches
            await asyncio.sleep(1.0)

    duration = round(time.time() - start, 1)
    print(f"✅ Verification complete: {checked} checked, {marked_inactive} inactive, {duration}s")

    return VerificationResult(
        checked=checked,
        still_active=still_active,
        marked_inactive=marked_inactive,
        errors=errors,
        duration_seconds=duration,
    )


async def cleanup_stale_jobs(older_than_days: int = 30) -> int:
    """
    Remove jobs older than N days from the database.
    Returns the number of deleted jobs.
    """
    from datetime import timedelta

    jobs_col = db.get_collection("jobs")
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)

    result = await jobs_col.delete_many({
        "created_at": {"$lt": cutoff},
        "is_active": {"$ne": True},
    })

    deleted = result.deleted_count
    print(f"🗑️  Cleaned up {deleted} stale jobs older than {older_than_days} days")
    return deleted


async def recompute_freshness_scores() -> int:
    """
    Recompute freshness_score for all active jobs in the DB.
    Run this daily to keep scores up to date as jobs age.
    Returns count of updated jobs.
    """
    from app.services.freshness_service import compute_freshness_score

    jobs_col = db.get_collection("jobs")
    updated = 0

    cursor = jobs_col.find({"is_active": {"$ne": False}}, {"_id": 1, "posted_at_parsed": 1, "created_at": 1, "source": 1})
    async for doc in cursor:
        posted_at = doc.get("posted_at_parsed")
        created_at = doc.get("created_at")
        source = doc.get("source", "")

        score, days_old = compute_freshness_score(posted_at, source, created_at)
        await jobs_col.update_one(
            {"_id": doc["_id"]},
            {"$set": {"freshness_score": score, "days_old": days_old}},
        )
        updated += 1

    print(f"♻️  Recomputed freshness scores for {updated} jobs")
    return updated
