"""Evidence-linked knowledge graph candidate ingestion and read API.

Submitted relations remain unverified until an explicit review workflow accepts
them. Only accepted assertions are returned by graph read endpoints.
"""
from __future__ import annotations

import hmac
import os
import unicodedata
from datetime import date
from difflib import SequenceMatcher
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from accessibility import authenticated_subject

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge-graph"])


def normalise_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(value.split())


class GraphEntityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=200)
    entity_type: str = Field(pattern=r"^[a-z][a-z0-9_]{1,39}$")
    aliases: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("entity name is too short")
        return value

    @field_validator("aliases")
    @classmethod
    def clean_aliases(cls, values):
        cleaned = [" ".join(value.split()) for value in values]
        if any(len(value) < 2 or len(value) > 200 for value in cleaned):
            raise ValueError("aliases must contain 2 to 200 characters")
        return list(dict.fromkeys(cleaned))


class GraphRelationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_name: str = Field(min_length=2, max_length=200)
    subject_type: str = Field(pattern=r"^[a-z][a-z0-9_]{1,39}$")
    predicate: str = Field(pattern=r"^[a-z][a-z0-9_]{1,79}$")
    object_name: str = Field(min_length=2, max_length=200)
    object_type: str = Field(pattern=r"^[a-z][a-z0-9_]{1,39}$")
    evidence_excerpt: str = Field(min_length=20, max_length=2000)
    confidence: float = Field(ge=0, le=1)
    valid_from: date | None = None
    valid_to: date | None = None
    extraction_method: str = Field(default="human_or_model_candidate", max_length=80)

    @field_validator("subject_name", "object_name")
    @classmethod
    def clean_endpoint_names(cls, value):
        return " ".join(value.split())

    @field_validator("evidence_excerpt")
    @classmethod
    def clean_excerpt(cls, value):
        return value.strip()


    @model_validator(mode="after")
    def reject_self_relation(self):
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError("valid_from must not be later than valid_to")
        if (self.subject_type, normalise_name(self.subject_name)) == (self.object_type, normalise_name(self.object_name)):
            raise ValueError("self-relations are not allowed")
        return self

class KnowledgeObservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_document_id: UUID
    entities: list[GraphEntityInput] = Field(min_length=2, max_length=50)
    relations: list[GraphRelationInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_relation_entities(self):
        known = {(item.entity_type, normalise_name(item.name)) for item in self.entities}
        for relation in self.relations:
            if (relation.subject_type, normalise_name(relation.subject_name)) not in known:
                raise ValueError("relation subject must be included in entities")
            if (relation.object_type, normalise_name(relation.object_name)) not in known:
                raise ValueError("relation object must be included in entities")
        return self


@router.post("/observations", status_code=202)
async def submit_observations(
    payload: KnowledgeObservationRequest,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail={"code": "knowledge_graph_database_unavailable"})

    async with pool.acquire() as connection:
        async with connection.transaction():
            evidence = await connection.fetchrow(
                """SELECT document_id FROM search_documents
                   WHERE document_id = $1 AND deleted_at IS NULL
                     AND index_status = 'indexed'
                     AND rights_basis IS NOT NULL AND btrim(rights_basis) <> ''
                     AND robots_status IN ('allowed', 'not_applicable')""",
                payload.evidence_document_id,
            )
            if evidence is None:
                raise HTTPException(status_code=422, detail={"code": "ineligible_evidence_document"})

            entity_ids: dict[tuple[str, str], str] = {}
            for entity in payload.entities:
                normalised = normalise_name(entity.name)
                row = await connection.fetchrow(
                    """INSERT INTO knowledge_entities (entity_type, canonical_name, normalised_name)
                       VALUES ($1, $2, $3)
                       ON CONFLICT (entity_type, normalised_name) DO UPDATE
                         SET updated_at = NOW()
                       RETURNING entity_id::text""",
                    entity.entity_type, entity.name, normalised,
                )
                entity_id = row["entity_id"]
                entity_ids[(entity.entity_type, normalised)] = entity_id
                for alias in entity.aliases:
                    await connection.execute(
                        """INSERT INTO knowledge_entity_aliases
                           (entity_id, alias, normalised_alias)
                           VALUES ($1::uuid, $2, $3)
                           ON CONFLICT (entity_id, normalised_alias) DO NOTHING""",
                        entity_id, alias, normalise_name(alias),
                    )

            assertion_ids = []
            for relation in payload.relations:
                subject_id = entity_ids[(relation.subject_type, normalise_name(relation.subject_name))]
                object_id = entity_ids[(relation.object_type, normalise_name(relation.object_name))]
                row = await connection.fetchrow(
                    """INSERT INTO knowledge_assertions
                       (subject_entity_id, predicate, object_entity_id, evidence_document_id,
                        evidence_excerpt, confidence, valid_from, valid_to, extraction_method, submitted_by, status)
                       VALUES ($1::uuid, $2, $3::uuid, $4, $5, $6, $7, $8, $9, $10, 'unverified')
                       RETURNING assertion_id::text""",
                    subject_id, relation.predicate, object_id, payload.evidence_document_id,
                    relation.evidence_excerpt, relation.confidence, relation.valid_from, relation.valid_to,
                    relation.extraction_method, subject,
                )
                assertion_ids.append(row["assertion_id"])

    return {
        "status": "submitted_for_review",
        "entities_upserted": len(entity_ids),
        "assertions_submitted": len(assertion_ids),
        "assertion_ids": assertion_ids,
        "graph_visibility": "unverified assertions are excluded from graph reads",
    }


@router.get("/entities")
async def find_entities(
    request: Request,
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=10, ge=1, le=50),
    subject: str = Depends(authenticated_subject),
):
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail={"code": "knowledge_graph_database_unavailable"})
    needle = normalise_name(q)
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """SELECT DISTINCT e.entity_id::text, e.entity_type, e.canonical_name
               FROM knowledge_entities e
               LEFT JOIN knowledge_entity_aliases a ON a.entity_id = e.entity_id
               WHERE e.normalised_name LIKE '%' || $1 || '%'
                  OR a.normalised_alias LIKE '%' || $1 || '%'
               ORDER BY e.canonical_name LIMIT $2""",
            needle, limit,
        )
    return {"query": q, "entities": [
        {"id": row["entity_id"], "type": row["entity_type"], "name": row["canonical_name"]}
        for row in rows
    ]}


@router.get("/entities/{entity_id}")
async def get_entity_graph(
    entity_id: UUID,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    subject: str = Depends(authenticated_subject),
):
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail={"code": "knowledge_graph_database_unavailable"})
    async with pool.acquire() as connection:
        entity = await connection.fetchrow(
            """SELECT entity_id::text, entity_type, canonical_name
               FROM knowledge_entities WHERE entity_id = $1""",
            entity_id,
        )
        if entity is None:
            raise HTTPException(status_code=404, detail={"code": "knowledge_entity_not_found"})
        relations = await connection.fetch(
            """SELECT a.assertion_id::text, a.predicate, a.evidence_excerpt, a.confidence,
                      a.evidence_document_id::text, a.created_at, a.valid_from, a.valid_to,
                      s.entity_id::text AS subject_id, s.canonical_name AS subject_name,
                      s.entity_type AS subject_type,
                      o.entity_id::text AS object_id, o.canonical_name AS object_name,
                      o.entity_type AS object_type,
                      d.title AS evidence_title, d.canonical_url AS evidence_url,
                      d.published_at AS evidence_published_at, d.fetched_at AS evidence_retrieved_at
               FROM knowledge_assertions a
               JOIN knowledge_entities s ON s.entity_id = a.subject_entity_id
               JOIN knowledge_entities o ON o.entity_id = a.object_entity_id
               JOIN search_documents d ON d.document_id = a.evidence_document_id
               WHERE a.status = 'accepted'
                 AND d.deleted_at IS NULL AND d.index_status = 'indexed'
                 AND d.rights_basis IS NOT NULL AND btrim(d.rights_basis) <> ''
                 AND d.robots_status IN ('allowed', 'not_applicable')
               AND (a.subject_entity_id = $1 OR a.object_entity_id = $1)
               ORDER BY a.confidence DESC, a.created_at DESC LIMIT $2""",
            entity_id, limit,
        )
    return {
        "entity": {"id": entity["entity_id"], "type": entity["entity_type"], "name": entity["canonical_name"]},
        "relations": [{
            "id": row["assertion_id"], "subject": {"id": row["subject_id"], "name": row["subject_name"], "type": row["subject_type"]},
            "predicate": row["predicate"],
            "object": {"id": row["object_id"], "name": row["object_name"], "type": row["object_type"]},
            "evidence": {
                "document_id": row["evidence_document_id"], "excerpt": row["evidence_excerpt"],
                "title": row["evidence_title"], "url": row["evidence_url"],
                "published_at": row["evidence_published_at"].isoformat() if row["evidence_published_at"] else None,
                "retrieved_at": row["evidence_retrieved_at"].isoformat(),
            },
            "confidence": row["confidence"], "created_at": row["created_at"].isoformat(),
            "valid_from": row["valid_from"].isoformat() if row["valid_from"] else None,
            "valid_to": row["valid_to"].isoformat() if row["valid_to"] else None,
        } for row in relations],
        "note": "Only reviewed, accepted assertions are returned.",
    }


def require_graph_reviewer(subject: str) -> None:
    """Require an explicit server-side reviewer subject allow-list."""
    configured = os.getenv("ORIOM7_GRAPH_REVIEWER_SUBJECTS", "")
    reviewers = {item.strip() for item in configured.split(",") if item.strip()}
    if not reviewers:
        raise HTTPException(status_code=503, detail={"code": "graph_reviewers_not_configured"})
    if subject not in reviewers:
        raise HTTPException(status_code=403, detail={"code": "graph_reviewer_forbidden"})


@router.get("/assertions/review-queue")
async def list_assertion_review_queue(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    predicate: str | None = Query(default=None, min_length=2, max_length=80),
    subject: str = Depends(authenticated_subject),
):
    """List pending assertions with complete source provenance for human review."""
    require_graph_reviewer(subject)
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail={"code": "knowledge_graph_database_unavailable"})
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """SELECT a.assertion_id::text, a.predicate, a.evidence_excerpt, a.confidence,
                      a.extraction_method, a.submitted_by, a.created_at, a.valid_from, a.valid_to,
                      s.entity_id::text AS subject_id, s.entity_type AS subject_type,
                      s.canonical_name AS subject_name,
                      o.entity_id::text AS object_id, o.entity_type AS object_type,
                      o.canonical_name AS object_name,
                      d.document_id::text AS document_id, d.title AS source_title,
                      d.canonical_url AS source_url, d.provider AS source_provider,
                      d.language AS source_language, d.published_at, d.fetched_at,
                      d.rights_basis, d.robots_status
               FROM knowledge_assertions a
               JOIN knowledge_entities s ON s.entity_id=a.subject_entity_id
               JOIN knowledge_entities o ON o.entity_id=a.object_entity_id
               JOIN search_documents d ON d.document_id=a.evidence_document_id
               WHERE a.status='unverified'
                 AND d.deleted_at IS NULL AND d.index_status='indexed'
                 AND d.rights_basis IS NOT NULL AND btrim(d.rights_basis)<>''
                 AND d.robots_status IN ('allowed','not_applicable')
                 AND ($1::text IS NULL OR a.predicate=$1)
               ORDER BY a.created_at ASC, a.assertion_id
               LIMIT $2 OFFSET $3""",
            predicate, limit, offset,
        )
        total = await connection.fetchval(
            """SELECT count(*) FROM knowledge_assertions a
               JOIN search_documents d ON d.document_id=a.evidence_document_id
               WHERE a.status='unverified'
                 AND d.deleted_at IS NULL AND d.index_status='indexed'
                 AND d.rights_basis IS NOT NULL AND btrim(d.rights_basis)<>''
                 AND d.robots_status IN ('allowed','not_applicable')
                 AND ($1::text IS NULL OR a.predicate=$1)""",
            predicate,
        )
    return {
        "items": [{
            "assertion_id": row["assertion_id"],
            "subject": {"id": row["subject_id"], "type": row["subject_type"], "name": row["subject_name"]},
            "predicate": row["predicate"],
            "object": {"id": row["object_id"], "type": row["object_type"], "name": row["object_name"]},
            "evidence": {
                "document_id": row["document_id"], "excerpt": row["evidence_excerpt"],
                "title": row["source_title"], "url": row["source_url"],
                "provider": row["source_provider"], "language": row["source_language"],
                "published_at": row["published_at"].isoformat() if row["published_at"] else None,
                "retrieved_at": row["fetched_at"].isoformat(),
                "rights_basis": row["rights_basis"], "robots_status": row["robots_status"],
            },
            "confidence": row["confidence"], "extraction_method": row["extraction_method"],
            "submitted_by": row["submitted_by"], "created_at": row["created_at"].isoformat(),
            "valid_from": row["valid_from"].isoformat() if row["valid_from"] else None,
            "valid_to": row["valid_to"].isoformat() if row["valid_to"] else None,
            "status": "unverified",
        } for row in rows],
        "total": total, "limit": limit, "offset": offset,
        "note": "Queue contains only unverified assertions with currently eligible source documents. A reviewer must assess source context before deciding.",
    }


class AssertionReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(accepted|rejected)$")


@router.post("/assertions/{assertion_id}/review")
async def review_assertion(
    assertion_id: UUID,
    payload: AssertionReviewRequest,
    request: Request,
    review_token: str | None = Header(default=None, alias="X-ORIOM7-GRAPH-REVIEW-TOKEN"),
    subject: str = Depends(authenticated_subject),
):
    require_graph_reviewer(subject)
    configured = os.getenv("ORIOM7_GRAPH_REVIEW_TOKEN")
    if not configured:
        raise HTTPException(status_code=503, detail={"code": "graph_review_not_configured"})
    if not review_token or not hmac.compare_digest(review_token, configured):
        raise HTTPException(status_code=401, detail={"code": "invalid_graph_review_token"})
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail={"code": "knowledge_graph_database_unavailable"})
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """UPDATE knowledge_assertions a
               SET status = $2, reviewed_by = $3, reviewed_at = NOW()
               WHERE a.assertion_id = $1 AND a.status = 'unverified'
                 AND EXISTS (
                    SELECT 1 FROM search_documents d
                    WHERE d.document_id = a.evidence_document_id
                      AND d.deleted_at IS NULL AND d.index_status = 'indexed'
                      AND d.rights_basis IS NOT NULL AND btrim(d.rights_basis) <> ''
                      AND d.robots_status IN ('allowed', 'not_applicable')
                 )
               RETURNING assertion_id::text, status, reviewed_at""",
            assertion_id, payload.decision, subject,
        )
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "reviewable_assertion_not_found"})
    return {
        "assertion_id": row["assertion_id"],
        "status": row["status"],
        "reviewed_at": row["reviewed_at"].isoformat(),
    }


@router.post("/documents/{document_id}/extract", status_code=202)
async def extract_document_graph_candidates(
    document_id: UUID,
    request: Request,
    subject: str = Depends(authenticated_subject),
):
    """Request model-assisted extraction; results remain unverified for review."""
    orchestrator = getattr(request.app.state, "model_orchestrator", None)
    if orchestrator is None or not orchestrator.providers:
        raise HTTPException(status_code=503, detail={"code": "knowledge_extraction_model_unavailable"})
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail={"code": "knowledge_graph_database_unavailable"})
    from knowledge_extraction import ExtractionError, extract_document_candidates
    try:
        result = await extract_document_candidates(
            pool, orchestrator, document_id, submitted_by=subject
        )
    except ExtractionError as exc:
        code = str(exc)
        status_code = 422 if code == "ineligible_evidence_document" else 502
        raise HTTPException(status_code=status_code, detail={"code": code}) from exc
    return result



def rank_entity_match_candidates(target_name: str, candidates: list[dict], limit: int = 10):
    """Rank possible duplicate entities; suggestions never merge or rewrite identities."""
    target = normalise_name(target_name)
    ranked = []
    for candidate in candidates:
        names = [candidate["canonical_name"], *candidate.get("aliases", [])]
        score = max(
            (SequenceMatcher(None, target, normalise_name(name)).ratio() for name in names),
            default=0.0,
        )
        if score >= 0.65:
            ranked.append({
                "id": candidate["entity_id"],
                "type": candidate["entity_type"],
                "name": candidate["canonical_name"],
                "similarity": round(score, 4),
                "matched_aliases": [
                    alias for alias in candidate.get("aliases", [])
                    if normalise_name(alias) == target
                ],
            })
    return sorted(ranked, key=lambda item: (-item["similarity"], item["name"]))[:limit]


def temporal_ranges_overlap(a_from: date | None, a_to: date | None,
                            b_from: date | None, b_to: date | None) -> bool:
    """Unknown bounds are treated as open intervals for conflict triage."""
    return (a_to is None or b_from is None or a_to >= b_from) and (
        b_to is None or a_from is None or b_to >= a_from
    )


@router.get("/entities/{entity_id}/resolution-candidates")
async def entity_resolution_candidates(
    entity_id: UUID,
    request: Request,
    limit: int = Query(default=10, ge=1, le=25),
    subject: str = Depends(authenticated_subject),
):
    """Suggest possible duplicate identities without automatically merging them."""
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail={"code": "knowledge_graph_database_unavailable"})
    async with pool.acquire() as connection:
        target = await connection.fetchrow(
            "SELECT entity_id::text, entity_type, canonical_name FROM knowledge_entities WHERE entity_id=$1",
            entity_id,
        )
        if target is None:
            raise HTTPException(status_code=404, detail={"code": "knowledge_entity_not_found"})
        rows = await connection.fetch(
            """SELECT e.entity_id::text, e.entity_type, e.canonical_name,
                      COALESCE(array_agg(a.alias) FILTER (WHERE a.alias IS NOT NULL), ARRAY[]::text[]) AS aliases
               FROM knowledge_entities e
               LEFT JOIN knowledge_entity_aliases a ON a.entity_id=e.entity_id
               WHERE e.entity_type=$1 AND e.entity_id<>$2
               GROUP BY e.entity_id
               ORDER BY e.updated_at DESC LIMIT 500""",
            target["entity_type"], entity_id,
        )
    candidates = rank_entity_match_candidates(
        target["canonical_name"], [dict(row) for row in rows], limit
    )
    return {
        "entity": {"id": target["entity_id"], "type": target["entity_type"], "name": target["canonical_name"]},
        "candidates": candidates,
        "automatic_merge": False,
        "note": "Similarity is a review aid, not proof that two records identify the same real-world entity.",
    }


@router.get("/assertions/potential-conflicts")
async def potential_assertion_conflicts(
    request: Request,
    predicate: str = Query(min_length=2, max_length=80),
    single_valued: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    subject: str = Depends(authenticated_subject),
):
    """Find overlapping accepted claims with different objects for a caller-designated single-valued predicate."""
    if not single_valued:
        raise HTTPException(
            status_code=400,
            detail={"code": "single_valued_predicate_confirmation_required",
                    "message": "Set single_valued=true only when this predicate should have one object per subject at a time."},
        )
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail={"code": "knowledge_graph_database_unavailable"})
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """SELECT a.assertion_id::text AS assertion_a, b.assertion_id::text AS assertion_b,
                      s.entity_id::text AS subject_id, s.canonical_name AS subject_name,
                      a.predicate,
                      oa.canonical_name AS object_a, ob.canonical_name AS object_b,
                      a.evidence_document_id::text AS evidence_a,
                      b.evidence_document_id::text AS evidence_b,
                      a.evidence_excerpt AS excerpt_a, b.evidence_excerpt AS excerpt_b,
                      a.valid_from AS a_from, a.valid_to AS a_to,
                      b.valid_from AS b_from, b.valid_to AS b_to
               FROM knowledge_assertions a
               JOIN knowledge_assertions b
                 ON b.subject_entity_id=a.subject_entity_id
                AND b.predicate=a.predicate
                AND b.object_entity_id<>a.object_entity_id
                AND b.assertion_id>a.assertion_id
               JOIN knowledge_entities s ON s.entity_id=a.subject_entity_id
               JOIN knowledge_entities oa ON oa.entity_id=a.object_entity_id
               JOIN knowledge_entities ob ON ob.entity_id=b.object_entity_id
               JOIN search_documents da ON da.document_id=a.evidence_document_id
               JOIN search_documents db ON db.document_id=b.evidence_document_id
               WHERE a.status='accepted' AND b.status='accepted'
                 AND a.predicate=$1
                 AND (a.valid_to IS NULL OR b.valid_from IS NULL OR a.valid_to>=b.valid_from)
                 AND (b.valid_to IS NULL OR a.valid_from IS NULL OR b.valid_to>=a.valid_from)
                 AND da.deleted_at IS NULL AND da.index_status='indexed'
                 AND da.rights_basis IS NOT NULL AND btrim(da.rights_basis)<>''
                 AND da.robots_status IN ('allowed','not_applicable')
                 AND db.deleted_at IS NULL AND db.index_status='indexed'
                 AND db.rights_basis IS NOT NULL AND btrim(db.rights_basis)<>''
                 AND db.robots_status IN ('allowed','not_applicable')
               ORDER BY s.canonical_name LIMIT $2""",
            predicate, limit,
        )
    return {
        "status": "potential_conflicts",
        "predicate": predicate,
        "count": len(rows),
        "conflicts": [{
            "subject": {"id": row["subject_id"], "name": row["subject_name"]},
            "claim_a": {"assertion_id": row["assertion_a"], "object": row["object_a"],
                        "evidence_document_id": row["evidence_a"], "excerpt": row["excerpt_a"],
                        "valid_from": row["a_from"].isoformat() if row["a_from"] else None,
                        "valid_to": row["a_to"].isoformat() if row["a_to"] else None},
            "claim_b": {"assertion_id": row["assertion_b"], "object": row["object_b"],
                        "evidence_document_id": row["evidence_b"], "excerpt": row["excerpt_b"],
                        "valid_from": row["b_from"].isoformat() if row["b_from"] else None,
                        "valid_to": row["b_to"].isoformat() if row["b_to"] else None},
            "classification": "overlapping_different_objects_requires_human_assessment",
        } for row in rows],
        "note": "These are potential inconsistencies, not proven contradictions. Check source dates, context, scope and predicate semantics.",
    }


@router.get("/entities/{entity_id}/paths")
async def get_entity_paths(
    entity_id: UUID,
    request: Request,
    max_depth: int = Query(default=2, ge=1, le=3),
    as_of: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    subject: str = Depends(authenticated_subject),
):
    """Return bounded multi-hop paths made only from accepted, currently eligible evidence."""
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail={"code": "knowledge_graph_database_unavailable"})
    async with pool.acquire() as connection:
        entity = await connection.fetchrow(
            "SELECT entity_id::text, entity_type, canonical_name FROM knowledge_entities WHERE entity_id=$1",
            entity_id,
        )
        if entity is None:
            raise HTTPException(status_code=404, detail={"code": "knowledge_entity_not_found"})
        rows = await connection.fetch(
            """WITH RECURSIVE walk(current_entity_id, depth, path_ids, edges) AS (
                 SELECT $1::uuid, 0, ARRAY[$1::uuid], '[]'::jsonb
                 UNION ALL
                 SELECT
                   CASE WHEN a.subject_entity_id=w.current_entity_id
                        THEN a.object_entity_id ELSE a.subject_entity_id END,
                   w.depth+1,
                   w.path_ids || CASE WHEN a.subject_entity_id=w.current_entity_id
                        THEN a.object_entity_id ELSE a.subject_entity_id END,
                   w.edges || jsonb_build_array(jsonb_build_object(
                     'assertion_id', a.assertion_id,
                     'subject_id', a.subject_entity_id,
                     'predicate', a.predicate,
                     'object_id', a.object_entity_id,
                     'evidence_document_id', a.evidence_document_id,
                     'evidence_excerpt', a.evidence_excerpt,
                     'valid_from', a.valid_from,
                     'valid_to', a.valid_to
                   ))
                 FROM walk w
                 JOIN knowledge_assertions a
                   ON a.subject_entity_id=w.current_entity_id
                   OR a.object_entity_id=w.current_entity_id
                 JOIN search_documents d ON d.document_id=a.evidence_document_id
                 WHERE w.depth<$2 AND a.status='accepted'
                   AND d.deleted_at IS NULL AND d.index_status='indexed'
                   AND d.rights_basis IS NOT NULL AND btrim(d.rights_basis)<>''
                   AND d.robots_status IN ('allowed','not_applicable')
                   AND NOT (
                     CASE WHEN a.subject_entity_id=w.current_entity_id
                          THEN a.object_entity_id ELSE a.subject_entity_id END = ANY(w.path_ids)
                   )
                   AND ($3::date IS NULL OR a.valid_from IS NULL OR a.valid_from<=$3)
                   AND ($3::date IS NULL OR a.valid_to IS NULL OR a.valid_to>=$3)
               )
               SELECT depth, path_ids::text[], edges
               FROM walk WHERE depth>0
               ORDER BY depth, path_ids::text
               LIMIT $4""",
            entity_id, max_depth, as_of, limit,
        )
    return {
        "start": {"id": entity["entity_id"], "type": entity["entity_type"], "name": entity["canonical_name"]},
        "max_depth": max_depth,
        "as_of": as_of.isoformat() if as_of else None,
        "paths": [{
            "depth": row["depth"],
            "entity_ids": row["path_ids"],
            "edges": row["edges"],
        } for row in rows],
        "note": "Paths contain accepted assertions only. Every edge carries its source evidence; traversal is bounded and is not proof of causation.",
    }
