"""Evidence-linked knowledge graph candidate ingestion and read API.

Submitted relations remain unverified until an explicit review workflow accepts
them. Only accepted assertions are returned by graph read endpoints.
"""
from __future__ import annotations

import hmac
import os
import unicodedata
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
    extraction_method: str = Field(default="human_or_model_candidate", max_length=80)

    @field_validator("subject_name", "object_name")
    @classmethod
    def clean_endpoint_names(cls, value):
        return " ".join(value.split())

    @field_validator("evidence_excerpt")
    @classmethod
    def clean_excerpt(cls, value):
        return value.strip()


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
                        evidence_excerpt, confidence, extraction_method, submitted_by, status)
                       VALUES ($1::uuid, $2, $3::uuid, $4, $5, $6, $7, $8, 'unverified')
                       RETURNING assertion_id::text""",
                    subject_id, relation.predicate, object_id, payload.evidence_document_id,
                    relation.evidence_excerpt, relation.confidence,
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
                      a.evidence_document_id::text, a.created_at,
                      s.entity_id::text AS subject_id, s.canonical_name AS subject_name,
                      s.entity_type AS subject_type,
                      o.entity_id::text AS object_id, o.canonical_name AS object_name,
                      o.entity_type AS object_type
               FROM knowledge_assertions a
               JOIN knowledge_entities s ON s.entity_id = a.subject_entity_id
               JOIN knowledge_entities o ON o.entity_id = a.object_entity_id
               JOIN search_documents d ON d.document_id = a.evidence_document_id
               WHERE a.status = 'accepted'
                 AND d.deleted_at IS NULL AND d.index_status = 'indexed'
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
            "evidence": {"document_id": row["evidence_document_id"], "excerpt": row["evidence_excerpt"]},
            "confidence": row["confidence"], "created_at": row["created_at"].isoformat(),
        } for row in relations],
        "note": "Only reviewed, accepted assertions are returned.",
    }


class AssertionReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(accepted|rejected)$")
    reviewer: str = Field(min_length=2, max_length=120)


@router.post("/assertions/{assertion_id}/review")
async def review_assertion(
    assertion_id: UUID,
    payload: AssertionReviewRequest,
    request: Request,
    review_token: str | None = Header(default=None, alias="X-ORIOM7-GRAPH-REVIEW-TOKEN"),
    subject: str = Depends(authenticated_subject),
):
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
            assertion_id, payload.decision, payload.reviewer,
        )
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "reviewable_assertion_not_found"})
    return {
        "assertion_id": row["assertion_id"],
        "status": row["status"],
        "reviewed_at": row["reviewed_at"].isoformat(),
    }
