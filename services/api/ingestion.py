"""Controlled, allow-listed single-page ingestion for the ORIOM7 search index.

Only operator-approved hosts can be fetched. This endpoint is protected by a
separate ingestion token and does not recursively crawl links.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import os
import socket
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from uuid import UUID

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

router = APIRouter(prefix="/v1/ingestion", tags=["ingestion"])
USER_AGENT = "ORIOM7Bot/1.0 (+https://oriom7.ai/bot)"
MAX_BODY_BYTES = 2_000_000
MAX_TEXT_CHARS = 100_000


class SourceRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(min_length=8, max_length=2048)
    rights_basis: str = Field(min_length=8, max_length=1000)
    approval_reference: str = Field(min_length=2, max_length=500)
    approved_by: str = Field(min_length=2, max_length=200)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Approved source base_url must be an HTTPS origin without credentials")
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("Register an HTTPS origin only; path-scoped sources are not yet supported")
        if parsed.port not in (None, 443):
            raise ValueError("Only standard HTTPS port 443 is allowed")
        return urlunsplit(("https", parsed.netloc.lower(), "", "", ""))


class CrawlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=8, max_length=2048)
    language: str | None = Field(default=None, max_length=35)


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.in_title = False
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        if tag in {"script", "style", "noscript", "svg", "iframe", "template"}:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        if tag in {"script", "style", "noscript", "svg", "iframe", "template"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        clean = " ".join(data.split())
        if not clean or self.skip_depth:
            return
        if self.in_title:
            self.title_parts.append(clean)
        else:
            self.text_parts.append(clean)

    @property
    def title(self):
        return " ".join(self.title_parts).strip()[:500]

    @property
    def text(self):
        return " ".join(self.text_parts).strip()[:MAX_TEXT_CHARS]


def require_ingestion_token(request: Request, supplied: str | None) -> None:
    expected = os.getenv("ORIOM7_INGESTION_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail={"code": "ingestion_not_configured"})
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail={"code": "ingestion_unauthorised"})


def get_pool(request: Request):
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail={"code": "database_not_configured"})
    return pool


def normalise_page_url(url: str, approved_host: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=422, detail={"code": "invalid_page_url"})
    if parsed.port not in (None, 443) or parsed.hostname.lower() != approved_host.lower():
        raise HTTPException(status_code=403, detail={"code": "host_not_approved"})
    return urlunsplit(("https", parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))


async def assert_public_dns(host: str) -> None:
    try:
        records = await asyncio.to_thread(
            socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM
        )
    except OSError as exc:
        raise HTTPException(status_code=422, detail={"code": "host_dns_failed"}) from exc
    addresses = {record[4][0] for record in records}
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise HTTPException(status_code=403, detail={"code": "non_public_host_blocked"})


async def bounded_get(client: httpx.AsyncClient, url: str, maximum: int):
    async with client.stream("GET", url) as response:
        chunks = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > maximum:
                raise HTTPException(status_code=413, detail={"code": "response_too_large"})
            chunks.append(chunk)
        return response.status_code, dict(response.headers), b"".join(chunks)


async def fetch_allowed_page(url: str, host: str) -> tuple[str, str, str]:
    await assert_public_dns(host)
    timeout = httpx.Timeout(12.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers={"User-Agent": USER_AGENT}) as client:
        robots_url = f"https://{host}/robots.txt"
        try:
            robots_status, _, robots_content = await bounded_get(client, robots_url, 200_000)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail={"code": "robots_fetch_failed"}) from exc
        if robots_status >= 400:
            # A missing robots file (404) is treated as no published disallow rules.
            if robots_status != 404:
                raise HTTPException(status_code=403, detail={"code": "robots_unavailable"})
            robots_text = ""
        else:
            robots_text = robots_content.decode("utf-8", errors="replace")
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(robots_text.splitlines())
        if not parser.can_fetch(USER_AGENT, url):
            raise HTTPException(status_code=403, detail={"code": "robots_disallowed"})

        try:
            page_status, page_headers, page_content = await bounded_get(client, url, MAX_BODY_BYTES)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail={"code": "page_fetch_failed"}) from exc
        if 300 <= page_status < 400:
            raise HTTPException(status_code=403, detail={"code": "redirect_not_followed"})
        if page_status != 200:
            raise HTTPException(status_code=422, detail={"code": "page_not_successful", "status": page_status})
        content_type = page_headers.get("content-type", "").lower()
        if not (content_type.startswith("text/html") or content_type.startswith("text/plain")):
            raise HTTPException(status_code=415, detail={"code": "unsupported_content_type"})
        charset = "utf-8"
        for part in content_type.split(";")[1:]:
            if part.strip().lower().startswith("charset="):
                charset = part.split("=", 1)[1].strip().strip('"')
        try:
            body = page_content.decode(charset, errors="replace")
        except LookupError:
            body = page_content.decode("utf-8", errors="replace")
        if content_type.startswith("text/html"):
            extractor = PageText()
            extractor.feed(body)
            title, text = extractor.title or urlsplit(url).hostname or "Untitled page", extractor.text
        else:
            title, text = urlsplit(url).path.rsplit("/", 1)[-1] or host, body[:MAX_TEXT_CHARS]
        if len(text.strip()) < 100:
            raise HTTPException(status_code=422, detail={"code": "insufficient_extractable_text"})
        return title[:500], text, content_type


@router.post("/sources", status_code=201)
async def register_source(
    payload: SourceRegistration,
    request: Request,
    ingestion_token: str | None = Header(default=None, alias="X-ORIOM7-INGESTION-TOKEN"),
):
    require_ingestion_token(request, ingestion_token)
    pool = get_pool(request)
    parsed = urlsplit(payload.base_url)
    host = parsed.hostname.lower()
    await assert_public_dns(host)
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """INSERT INTO search_sources
               (base_url, host, rights_basis, approval_reference, approved_by)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (base_url) DO UPDATE SET
                 rights_basis = EXCLUDED.rights_basis,
                 approval_reference = EXCLUDED.approval_reference,
                 approved_by = EXCLUDED.approved_by,
                 status = 'approved', updated_at = NOW()
               RETURNING source_id::text, base_url, host, status, created_at""",
            payload.base_url, host, payload.rights_basis.strip(),
            payload.approval_reference.strip(), payload.approved_by.strip(),
        )
    return dict(row)


@router.post("/queue", status_code=202)
async def enqueue_page(
    payload: CrawlRequest,
    request: Request,
    ingestion_token: str | None = Header(default=None, alias="X-ORIOM7-INGESTION-TOKEN"),
):
    """Queue one approved page for a separate worker; never fetch in the API process."""
    require_ingestion_token(request, ingestion_token)
    pool = get_pool(request)
    parsed = urlsplit(payload.url)
    if not parsed.hostname:
        raise HTTPException(status_code=422, detail={"code": "invalid_page_url"})
    async with pool.acquire() as connection:
        source = await connection.fetchrow(
            "SELECT source_id, host FROM search_sources WHERE host = $1 AND status = 'approved'",
            parsed.hostname.lower(),
        )
        if source is None:
            raise HTTPException(status_code=403, detail={"code": "source_not_approved"})
        url = normalise_page_url(payload.url, source["host"])
        row = await connection.fetchrow(
            """INSERT INTO search_crawl_jobs (source_id, url, language)
               VALUES ($1, $2, $3)
               ON CONFLICT (source_id, url) DO UPDATE SET
                 status = CASE WHEN search_crawl_jobs.status IN ('completed', 'failed', 'blocked', 'rejected')
                               THEN 'pending' ELSE search_crawl_jobs.status END,
                 available_at = CASE WHEN search_crawl_jobs.status IN ('completed', 'failed', 'blocked', 'rejected')
                                      THEN NOW() ELSE search_crawl_jobs.available_at END,
                 updated_at = NOW()
               RETURNING job_id::text, status, created_at""",
            source["source_id"], url, payload.language,
        )
    return {"job_id": row["job_id"], "status": row["status"], "url": url}

@router.post("/crawl", status_code=202)
async def crawl_one_page(
    payload: CrawlRequest,
    request: Request,
    ingestion_token: str | None = Header(default=None, alias="X-ORIOM7-INGESTION-TOKEN"),
):
    require_ingestion_token(request, ingestion_token)
    pool = get_pool(request)
    parsed = urlsplit(payload.url)
    if not parsed.hostname:
        raise HTTPException(status_code=422, detail={"code": "invalid_page_url"})
    async with pool.acquire() as connection:
        source = await connection.fetchrow(
            "SELECT * FROM search_sources WHERE host = $1 AND status = 'approved'",
            parsed.hostname.lower(),
        )
    if source is None:
        raise HTTPException(status_code=403, detail={"code": "source_not_approved"})
    url = normalise_page_url(payload.url, source["host"])
    started = datetime.now(timezone.utc)
    try:
        title, body, content_type = await fetch_allowed_page(url, source["host"])
    except HTTPException as exc:
        async with pool.acquire() as connection:
            await connection.execute(
                """INSERT INTO search_ingestion_runs
                   (source_id, requested_url, outcome, detail, completed_at)
                   VALUES ($1, $2, $3, $4, NOW())""",
                source["source_id"], url,
                "blocked" if exc.status_code == 403 else "failed",
                str(exc.detail)[:1000],
            )
        raise

    content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    async with pool.acquire() as connection:
        async with connection.transaction():
            existing = await connection.fetchrow(
                """SELECT document_id::text FROM search_documents
                   WHERE canonical_url = $1 AND content_hash = $2 AND deleted_at IS NULL""",
                url, content_hash,
            )
            if existing:
                await connection.execute(
                    "UPDATE search_documents SET fetched_at = NOW(), updated_at = NOW() WHERE document_id = $1::uuid",
                    existing["document_id"],
                )
                document_id = existing["document_id"]
                outcome = "unchanged"
            else:
                await connection.execute(
                    "UPDATE search_documents SET deleted_at = NOW(), index_status = 'rejected', updated_at = NOW() WHERE canonical_url = $1 AND deleted_at IS NULL",
                    url,
                )
                row = await connection.fetchrow(
                    """INSERT INTO search_documents
                       (canonical_url, title, body_text, provider, language, fetched_at,
                        content_hash, rights_basis, robots_status, index_status)
                       VALUES ($1, $2, $3, 'oriom7_owned_crawler', $4, NOW(),
                               $5, $6, 'allowed', 'indexed')
                       RETURNING document_id::text""",
                    url, title, body, payload.language, content_hash, source["rights_basis"],
                )
                document_id = row["document_id"]
                outcome = "indexed"
            await connection.execute(
                """INSERT INTO search_ingestion_runs
                   (source_id, requested_url, final_url, outcome, detail, document_id, started_at, completed_at)
                   VALUES ($1, $2, $2, $3, $4, $5::uuid, $6, NOW())""",
                source["source_id"], url, outcome, content_type, document_id, started,
            )
    return {"status": outcome, "document_id": document_id, "url": url, "title": title, "characters_indexed": len(body)}
