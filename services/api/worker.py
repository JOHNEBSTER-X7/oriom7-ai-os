"""Queue-backed ORIOM7 crawler worker.

Run as a separate process: python worker.py. The API only enqueues jobs.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import socket
from datetime import datetime, timedelta, timezone

import asyncpg
from fastapi import HTTPException

from ingestion import fetch_allowed_page, normalise_page_url
from semantic_index import build_embedding_provider_from_env

logger = logging.getLogger("oriom7.crawl_worker")


def retry_delay_seconds(attempt: int) -> int:
    """Bounded exponential retry delay: 30s, 60s, ... capped at 6h."""
    return min(30 * (2 ** max(0, attempt - 1)), 21_600)


def permanent_failure(status_code: int) -> bool:
    return status_code in {403, 404, 410, 413, 415, 422}


class CrawlWorker:
    def __init__(self, pool, worker_id: str | None = None, embedder=None):
        self.pool = pool
        self.worker_id = worker_id or socket.gethostname()
        self.embedder = embedder

    async def claim(self):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """UPDATE search_crawl_jobs
                       SET status = 'failed', locked_at = NULL, locked_by = NULL,
                           last_error = 'worker lease expired after maximum attempts', updated_at = NOW()
                       WHERE status = 'running' AND attempts >= max_attempts
                         AND locked_at < NOW() - INTERVAL '10 minutes'"""
                )
                row = await connection.fetchrow(
                    """
                    SELECT j.job_id, j.source_id, j.url, j.language, j.attempts,
                           j.max_attempts, s.host, s.rights_basis, s.min_interval_seconds
                    FROM search_crawl_jobs j
                    JOIN search_sources s ON s.source_id = j.source_id
                    WHERE s.status = 'approved'
                      AND s.next_allowed_at <= NOW()
                      AND (
                        (j.status = 'pending' AND j.available_at <= NOW())
                        OR (j.status = 'running' AND j.locked_at < NOW() - INTERVAL '10 minutes')
                      )
                      AND (
                        SELECT COUNT(*) FROM search_ingestion_runs r
                        WHERE r.source_id = s.source_id
                          AND r.started_at >= NOW() - INTERVAL '24 hours'
                      ) + (
                        SELECT COUNT(*) FROM search_crawl_jobs active
                        WHERE active.source_id = s.source_id AND active.status = 'running'
                          AND active.locked_at >= NOW() - INTERVAL '24 hours'
                      ) < s.max_pages_per_day
                    ORDER BY j.available_at, j.created_at
                    FOR UPDATE OF j, s SKIP LOCKED
                    LIMIT 1
                    """
                )
                if row is None:
                    return None
                await connection.execute(
                    """UPDATE search_sources
                       SET next_allowed_at = NOW() + ($2 * INTERVAL '1 second'),
                           updated_at = NOW()
                       WHERE source_id = $1""",
                    row["source_id"], row["min_interval_seconds"],
                )
                await connection.execute(
                    """UPDATE search_crawl_jobs
                       SET status = 'running', attempts = attempts + 1,
                           locked_at = NOW(), locked_by = $2, updated_at = NOW()
                       WHERE job_id = $1""",
                    row["job_id"], self.worker_id,
                )
                return dict(row)

    async def complete_page(self, job: dict, title: str, body: str, content_type: str):
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                existing = await connection.fetchrow(
                    """SELECT document_id::text FROM search_documents
                       WHERE canonical_url = $1 AND content_hash = $2 AND deleted_at IS NULL""",
                    job["url"], digest,
                )
                if existing:
                    document_id = existing["document_id"]
                    await connection.execute(
                        """UPDATE search_documents SET fetched_at = NOW(), updated_at = NOW()
                           WHERE document_id = $1::uuid""", document_id,
                    )
                else:
                    await connection.execute(
                        """UPDATE search_documents SET deleted_at = NOW(), index_status = 'rejected',
                           updated_at = NOW() WHERE canonical_url = $1 AND deleted_at IS NULL""",
                        job["url"],
                    )
                    row = await connection.fetchrow(
                        """INSERT INTO search_documents
                           (canonical_url, title, body_text, provider, language, fetched_at,
                            content_hash, rights_basis, robots_status, index_status)
                           VALUES ($1, $2, $3, 'oriom7_owned_crawler', $4, NOW(),
                                   $5, $6, 'allowed', 'indexed')
                           RETURNING document_id::text""",
                        job["url"], title, body, job["language"], digest, job["rights_basis"],
                    )
                    document_id = row["document_id"]
                await connection.execute(
                    """INSERT INTO search_ingestion_runs
                       (source_id, requested_url, final_url, outcome, detail, document_id, completed_at)
                       VALUES ($1, $2, $2, 'indexed', $3, $4::uuid, NOW())""",
                    job["source_id"], job["url"], content_type, document_id,
                )
                await connection.execute(
                    """UPDATE search_crawl_jobs
                       SET status = 'completed', document_id = $2::uuid, locked_at = NULL,
                           locked_by = NULL, last_error = NULL, updated_at = NOW()
                       WHERE job_id = $1""",
                    job["job_id"], document_id,
                )

    async def record_failure(self, job: dict, error: str, status_code: int | None = None):
        now = datetime.now(timezone.utc)
        blocked = status_code == 403
        terminal = blocked or (status_code is not None and permanent_failure(status_code))
        exhausted = job["attempts"] + 1 >= job["max_attempts"]
        next_status = "blocked" if blocked else "rejected" if terminal else "failed" if exhausted else "pending"
        delay = retry_delay_seconds(job["attempts"] + 1)
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """INSERT INTO search_ingestion_runs
                       (source_id, requested_url, outcome, detail, started_at, completed_at)
                       VALUES ($1, $2, $3, $4, $5, NOW())""",
                    job["source_id"], job["url"],
                    "blocked" if blocked else "rejected" if terminal else "failed",
                    error[:1000], now,
                )
                await connection.execute(
                    """UPDATE search_crawl_jobs
                       SET status = $2, available_at = NOW() + ($3 * INTERVAL '1 second'),
                           locked_at = NULL, locked_by = NULL, last_error = $4, updated_at = NOW()
                       WHERE job_id = $1""",
                    job["job_id"], next_status, delay, error[:1000],
                )

    async def run_once(self) -> bool:
        job = await self.claim()
        if job is None:
            return False
        try:
            url = normalise_page_url(job["url"], job["host"])
            title, body, content_type = await fetch_allowed_page(url, job["host"])
            await self.complete_page(job, title, body, content_type)
        except HTTPException as exc:
            await self.record_failure(job, str(exc.detail), exc.status_code)
        except Exception as exc:
            logger.exception("crawl_job_failed", extra={"job_id": str(job["job_id"])})
            await self.record_failure(job, type(exc).__name__)
        return True


async def serve():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for the crawler worker")
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    worker = CrawlWorker(pool, os.getenv("ORIOM7_CRAWL_WORKER_ID"))
    idle_seconds = float(os.getenv("ORIOM7_CRAWL_IDLE_SECONDS", "3"))
    try:
        while True:
            worked = await worker.run_once()
            if not worked:
                await asyncio.sleep(idle_seconds)
    finally:
        await pool.close()


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    asyncio.run(serve())
