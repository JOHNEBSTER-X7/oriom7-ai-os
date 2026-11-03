"""Queue-backed ORIOM7 crawler worker.

Run as a separate process: python worker.py. The API only enqueues jobs.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import socket
from datetime import datetime, timedelta, timezone

import asyncpg
from fastapi import HTTPException

from ingestion import fetch_allowed_page, normalise_page_url
from semantic_index import build_embedding_provider_from_env
from model_orchestration import build_orchestrator_from_env
from retrieval import PostgresLexicalIndex, RetrievalService, build_external_search_providers_from_env
from semantic_index import PostgresVectorIndex
from research_agent_runtime import execute_research_job, fail_research_job

logger = logging.getLogger("oriom7.crawl_worker")


def retry_delay_seconds(attempt: int) -> int:
    """Bounded exponential retry delay: 30s, 60s, ... capped at 6h."""
    return min(30 * (2 ** max(0, attempt - 1)), 21_600)


def permanent_failure(status_code: int) -> bool:
    return status_code in {403, 404, 410, 413, 415, 422}


class CrawlWorker:
    def __init__(self, pool, worker_id: str | None = None, embedder=None, extraction_orchestrator=None):
        self.pool = pool
        self.worker_id = worker_id or socket.gethostname()
        self.embedder = embedder
        self.extraction_orchestrator = extraction_orchestrator

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
                outcome = "unchanged" if existing else "indexed"
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
                       VALUES ($1, $2, $2, $3, $4, $5::uuid, NOW())""",
                    job["source_id"], job["url"], outcome, content_type, document_id,
                )
                await connection.execute(
                    """UPDATE search_crawl_jobs
                       SET status = 'completed', document_id = $2::uuid, locked_at = NULL,
                           locked_by = NULL, last_error = NULL, updated_at = NOW()
                       WHERE job_id = $1""",
                    job["job_id"], document_id,
                )
        if self.embedder is not None:
            try:
                await self.embedder.index_document(self.pool, document_id, title + chr(10) + body, digest)
            except Exception:
                logger.exception("document_embedding_failed", extra={"document_id": document_id})
        if self.extraction_orchestrator is not None:
            try:
                from knowledge_extraction import extract_document_candidates
                await extract_document_candidates(
                    self.pool, self.extraction_orchestrator, document_id,
                    submitted_by="worker:" + self.worker_id,
                )
            except Exception as exc:
                logger.warning("knowledge_extraction_skipped", extra={
                    "document_id": document_id, "reason": type(exc).__name__,
                })

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



class ResearchAgentWorker:
    """Lease-based worker for durable research jobs and recurring schedules."""
    def __init__(self, pool, retrieval, orchestrator, worker_id=None):
        self.pool=pool; self.retrieval=retrieval; self.orchestrator=orchestrator
        self.worker_id=worker_id or socket.gethostname()+":research"

    async def enqueue_due_schedules(self):
        async with self.pool.acquire() as con:
            async with con.transaction():
                rows=await con.fetch("""SELECT * FROM research_agent_schedules
                  WHERE enabled=TRUE AND next_run_at<=NOW()
                  ORDER BY next_run_at LIMIT 10 FOR UPDATE SKIP LOCKED""")
                for row in rows:
                    run_id=await con.fetchval("""INSERT INTO research_agent_runs
                      (owner_subject,research_question,status)
                      VALUES($1,$2,'queued') RETURNING run_id""",row["owner_subject"],row["research_question"])
                    payload={"question":row["research_question"],"max_sources":row["max_sources"],
                             "extract_graph_candidates":row["extract_graph_candidates"]}
                    await con.execute("""INSERT INTO research_agent_jobs(run_id,owner_subject,payload)
                      VALUES($1,$2,$3::jsonb)""",run_id,row["owner_subject"],json.dumps(payload))
                    await con.execute("""UPDATE research_agent_schedules
                      SET next_run_at=NOW()+(interval_minutes*INTERVAL '1 minute'),
                          last_run_id=$2,updated_at=NOW() WHERE schedule_id=$1""",row["schedule_id"],run_id)

    async def claim(self):
        async with self.pool.acquire() as con:
            async with con.transaction():
                await con.execute("""UPDATE research_agent_jobs SET status='failed',locked_at=NULL,
                  locked_by=NULL,last_error='worker lease expired; attempts exhausted',updated_at=NOW()
                  WHERE status='running' AND attempts>=max_attempts
                    AND locked_at<NOW()-INTERVAL '15 minutes'""")
                await con.execute("""UPDATE research_agent_runs r SET status='failed',
                  error_code='worker_lease_exhausted',completed_at=NOW()
                  FROM research_agent_jobs j WHERE j.run_id=r.run_id AND j.status='failed'
                    AND r.status='running' AND j.last_error='worker lease expired; attempts exhausted'""")
                row=await con.fetchrow("""SELECT job_id,run_id::text,owner_subject,payload,attempts,max_attempts
                  FROM research_agent_jobs
                  WHERE (status='pending' AND available_at<=NOW())
                     OR (status='running' AND locked_at<NOW()-INTERVAL '15 minutes')
                  ORDER BY available_at LIMIT 1 FOR UPDATE SKIP LOCKED""")
                if row is None: return None
                await con.execute("""UPDATE research_agent_jobs SET status='running',attempts=attempts+1,
                  locked_at=NOW(),locked_by=$2,updated_at=NOW() WHERE job_id=$1""",row["job_id"],self.worker_id)
                await con.execute("UPDATE research_agent_runs SET status='running' WHERE run_id=$1::uuid",row["run_id"])
                claimed=dict(row)
                if isinstance(claimed.get("payload"),str): claimed["payload"]=json.loads(claimed["payload"])
                return claimed

    async def run_once(self):
        await self.enqueue_due_schedules()
        job=await self.claim()
        if job is None: return False
        try:
            await execute_research_job(self.pool,job["run_id"],job["owner_subject"],
                                       job["payload"],self.retrieval,self.orchestrator)
        except Exception as exc:
            logger.exception("research_agent_job_failed",extra={"run_id":job["run_id"]})
            retry=job["attempts"]+1<job["max_attempts"]
            await fail_research_job(self.pool,job["run_id"],job["owner_subject"],type(exc).__name__,retry)
        return True


async def serve():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for the crawler worker")
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    extraction_enabled = os.getenv("ORIOM7_KNOWLEDGE_EXTRACTION_ENABLED", "false").lower() == "true"
    extraction_orchestrator = build_orchestrator_from_env() if extraction_enabled else None
    if extraction_orchestrator is not None and not extraction_orchestrator.providers:
        logger.warning("knowledge_extraction_enabled_without_model_provider")
        extraction_orchestrator = None
    worker = CrawlWorker(
        pool,
        os.getenv("ORIOM7_CRAWL_WORKER_ID"),
        build_embedding_provider_from_env() if os.getenv("ORIOM7_SEMANTIC_SEARCH_ENABLED", "false").lower() == "true" else None,
        extraction_orchestrator,
    )
    research_orchestrator=build_orchestrator_from_env()
    research_embedding_provider = build_embedding_provider_from_env() if os.getenv("ORIOM7_SEMANTIC_SEARCH_ENABLED", "false").lower() == "true" else None
    research_semantic_index = PostgresVectorIndex(pool, research_embedding_provider) if research_embedding_provider is not None else None
    research_worker=ResearchAgentWorker(
        pool,
        RetrievalService(PostgresLexicalIndex(pool), build_external_search_providers_from_env(), research_semantic_index),
        research_orchestrator,
        os.getenv("ORIOM7_RESEARCH_WORKER_ID"),
    ) if research_orchestrator.providers else None
    idle_seconds = float(os.getenv("ORIOM7_CRAWL_IDLE_SECONDS", "3"))
    try:
        while True:
            worked = await worker.run_once()
            research_worked = await research_worker.run_once() if research_worker else False
            if not worked and not research_worked:
                await asyncio.sleep(idle_seconds)
    finally:
        await pool.close()


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    asyncio.run(serve())
