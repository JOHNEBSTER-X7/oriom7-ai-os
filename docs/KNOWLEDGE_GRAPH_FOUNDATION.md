# ORIOM7 Knowledge Graph Foundation

## Purpose

The knowledge graph stores entities and evidence-backed relationship assertions so ORIOM7 can connect information across indexed documents. It is a provenance layer over the search corpus, not an independent source of truth.

Initial entity types are intentionally extensible: people, organisations, locations, products, technologies, concepts, events and publications can be represented using a validated type key. Predicates are similarly extensible, for example `founded`, `headquartered_in`, `manufactures`, `uses_technology` or `located_in`.

## Data model

Migration `006_knowledge_graph.sql` adds the graph schema; migration `007_knowledge_assertion_dedup.sql` adds an idempotency index for repeated extraction runs.

- `knowledge_entities`: canonical name, entity type and Unicode-normalised lookup key.
- `knowledge_entity_aliases`: alternative names and normalised alias lookup.
- `knowledge_assertions`: directed subject–predicate–object claims linked to an indexed evidence document, a verbatim evidence excerpt, confidence, extraction method, submitter, reviewer and review status.

Entity identity is scoped by entity type plus Unicode NFKC/casefold/whitespace-normalised name. Aliases are stored separately; they do not silently merge two canonical entities. Entity resolution across ambiguous names, organisations and people remains a future capability.

## Evidence and trust model

A submitted assertion is always created as `unverified`. Its evidence document must currently be indexed, non-deleted, have a non-empty rights basis and an allowed/not-applicable robots status. Every assertion retains its source document ID and excerpt.

Only assertions with status `accepted` are returned by graph read endpoints. Unverified, rejected and superseded assertions are not represented as established graph facts. Acceptance requires an authenticated reviewer plus the separately configured `ORIOM7_GRAPH_REVIEW_TOKEN`; the reviewer identity is taken from trusted request authentication, not supplied by the caller. Configure this token in a backend secret manager and restrict it to the designated review service/operator.

Review is a human approval gate, not automated fact verification. Reviewers should compare the excerpt with the source document and assess context, date, ambiguity, negation and whether the predicate is actually supported. Confidence is an extraction signal, not a probability guarantee. A later source deletion removes the assertion from graph reads through the evidence eligibility join; it does not erase the audit record.

## API

All routes require the normal authenticated ORIOM7 user context.

### Submit candidate observations

`POST /v1/knowledge/observations`

Example:

```json
{
  "evidence_document_id": "00000000-0000-0000-0000-000000000001",
  "entities": [
    {"name": "Acme Energy", "entity_type": "organisation", "aliases": ["Acme"]},
    {"name": "Battery One", "entity_type": "product"}
  ],
  "relations": [
    {
      "subject_name": "Acme Energy",
      "subject_type": "organisation",
      "predicate": "manufactures",
      "object_name": "Battery One",
      "object_type": "product",
      "evidence_excerpt": "The source excerpt directly stating the relationship goes here.",
      "confidence": 0.91,
      "extraction_method": "human_or_model_candidate"
    }
  ]
}
```

The request returns HTTP 202 and assertion IDs. The evidence excerpt must be at least 20 characters. Relation endpoints must be included in the entity batch. Self-relations are rejected.

### Review an assertion

`POST /v1/knowledge/assertions/{assertion_id}/review`

Send `X-ORIOM7-GRAPH-REVIEW-TOKEN` and a body such as:

```json
{"decision": "accepted"}
```

The token must be configured as `ORIOM7_GRAPH_REVIEW_TOKEN`. Only unverified assertions with still-eligible evidence can be reviewed. A review records the authenticated reviewer and timestamp. This endpoint is a minimal protected gate; production should additionally enforce a dedicated reviewer role/permission in the identity provider and rotate/restrict the review token.

### Find entities

`GET /v1/knowledge/entities?q=Acme`

Searches canonical names and aliases.

### Read an entity neighbourhood

`GET /v1/knowledge/entities/{entity_id}`

Returns only accepted relationships, with source document IDs, evidence excerpts, confidence and timestamps. The response is a one-hop neighbourhood, not an unbounded graph traversal.

## Current boundaries

- Model-assisted extraction is optional and runs only when explicitly invoked or enabled in the crawler worker.
- Entity matching produces similarity suggestions only; no automatic entity merge or canonical identity rewrite.
- Temporal validity is optional and depends on explicit dates in source evidence.
- Conflict triage is limited to caller-designated single-valued predicates and does not resolve contradictions.
- Multi-hop traversal is bounded to three edges and does not imply causation or transitive truth.
- No graph visualisation or public graph export.
- No bulk review console or fine-grained reviewer role integration.
- Only one-hop accepted relationships are returned.
- Evidence excerpt provenance is recorded, but the API does not independently verify that the excerpt is an exact substring of the stored document. A future ingestion/extraction pipeline should derive offsets and excerpts directly from stored source text.
- Search ranking does not yet use graph features; graph expansion is a separate API surface.

## Deployment

Apply migrations 001 through 008 in order. Set `ORIOM7_GRAPH_REVIEW_TOKEN` only in the API secret manager. Do not put it in frontend configuration. Before production, integrate reviewer roles, audit monitoring, rate limits and source-deletion propagation tests.

## Model-assisted candidate extraction

The extraction service uses the configured ORIOM7 model orchestrator to propose entities and relationships from one eligible indexed document. It treats document content as untrusted input and instructs the model to return a strict JSON object, not executable instructions or prose.

### Request extraction

`POST /v1/knowledge/documents/{document_id}/extract`

The route requires normal user authentication and an available configured model provider. It loads only documents that are indexed, non-deleted, have a non-empty rights basis and an allowed/not-applicable robots status. The model receives the title and a bounded 12,000-character source excerpt.

The application then:
- Validates the JSON shape and Pydantic constraints.
- Requires relation endpoints to exist in the submitted entity list.
- Rejects self-relations and excessive entity/relation counts.
- Retains a proposed relation only when its evidence excerpt is an exact verbatim substring of the supplied source text.
- Deduplicates repeated assertions for the same entity pair, predicate, evidence document and excerpt.
- Persists every candidate as `unverified`; it never accepts model output automatically.

If a model produces no exact excerpt, no assertion is created. Model confidence is only a triage signal, not a probability guarantee. The extraction response reports provider/model metadata and whether fallback routing was used, but does not expose secrets.

### Optional worker integration

Set `ORIOM7_KNOWLEDGE_EXTRACTION_ENABLED=true` in the crawler worker environment to run extraction after a page has been indexed. This is disabled by default and requires configured model provider credentials and an explicit model ID. Extraction failure is logged without undoing successful lexical ingestion. Existing indexed documents can be processed by calling the authenticated extraction endpoint individually; a bulk backfill scheduler is not yet included.

### Deployment migrations

Apply migrations 001 through 007 in numerical order. Keep `ORIOM7_KNOWLEDGE_EXTRACTION_ENABLED` disabled until provider spend limits, privacy review and human-review operations are ready. The model receives source text, so confirm provider data-processing, retention and residency terms before enabling it on licensed or sensitive content.


## Model-assisted candidate extraction

The extraction service uses the configured ORIOM7 model orchestrator to propose entities and relationships from one eligible indexed document. It treats document content as untrusted input and instructs the model to return a strict JSON object, not executable instructions or prose.

### Request extraction

`POST /v1/knowledge/documents/{document_id}/extract`

The route requires normal user authentication and an available configured model provider. It loads only documents that are indexed, non-deleted, have a non-empty rights basis and an allowed/not-applicable robots status. The model receives the title and a bounded 12,000-character source excerpt.

The application then:
- Validates the JSON shape and Pydantic constraints.
- Requires relation endpoints to exist in the submitted entity list.
- Rejects self-relations and excessive entity/relation counts.
- Retains a proposed relation only when its evidence excerpt is an exact verbatim substring of the supplied source text.
- Deduplicates repeated assertions for the same entity pair, predicate, evidence document and excerpt.
- Persists every candidate as `unverified`; it never accepts model output automatically.

If a model produces no exact excerpt, no assertion is created. Model confidence is only a triage signal, not a probability guarantee. The extraction response reports provider/model metadata and whether fallback routing was used, but does not expose secrets.

### Optional worker integration

Set `ORIOM7_KNOWLEDGE_EXTRACTION_ENABLED=true` in the crawler worker environment to run extraction after a page has been indexed. This is disabled by default and requires configured model provider credentials and an explicit model ID. Extraction failure is logged without undoing successful lexical ingestion. Existing indexed documents can be processed by calling the authenticated extraction endpoint individually; a bulk backfill scheduler is not yet included.

### Deployment migrations

Apply migrations 001 through 007 in numerical order. Keep `ORIOM7_KNOWLEDGE_EXTRACTION_ENABLED` disabled until provider spend limits, privacy review and human-review operations are ready. The model receives source text, so confirm provider data-processing, retention and residency terms before enabling it on licensed or sensitive content.


## Graph intelligence: identity suggestions, time and paths

Migration `008_knowledge_graph_temporal_intelligence.sql` adds nullable `valid_from` and `valid_to` dates to relationship assertions. These dates describe when a sourced relationship is stated to be valid, not when ORIOM7 first learned it. They must be left null when the source does not provide reliable dates. The database rejects reversed ranges.

### Possible duplicate identities

`GET /v1/knowledge/entities/{entity_id}/resolution-candidates`

ORIOM7 compares the entity's canonical name with up to 500 recent entities of the same type and their aliases, then returns the strongest name-similarity candidates. The response includes similarity scores and exact alias matches. It does not merge entities, rewrite assertions or claim that two names refer to the same real-world subject. A future merge workflow needs a separately audited, reversible human decision and reference migration.

### Potentially conflicting claims

`GET /v1/knowledge/assertions/potential-conflicts?predicate=headquartered_in&single_valued=true`

This endpoint compares accepted assertions for the same subject and predicate where the objects differ and their recorded validity windows overlap. The caller must explicitly confirm that the predicate is single-valued. Do not use this option for multi-valued relationships such as `owns`, `operates`, `partners_with` or `sells_in`.

A returned pair is a *potential inconsistency*, not a proven contradiction. Different sources may refer to different scopes, subsidiaries, dates, roles or definitions. Every result includes both evidence excerpts and document IDs for human review. The system does not automatically reject, supersede or resolve either claim. This initial detector does not yet reason over negation, numerical disagreement, paraphrase, causal claims or complex natural-language contradictions.

### Bounded multi-hop paths

`GET /v1/knowledge/entities/{entity_id}/paths?max_depth=2&as_of=2026-01-01`

The recursive query follows accepted relationships in either direction, excludes cycles within a path, rechecks source eligibility at query time and limits traversal to one through three edges. Every edge includes the assertion ID, predicate, endpoints, source document ID, verbatim excerpt and temporal bounds. An optional `as_of` date filters out relationships whose recorded validity window does not include that date. Unknown bounds are treated as open; this is a data limitation, not evidence that a relationship existed indefinitely.

Paths are navigational connections, not proof of causation or transitive truth. For example, a path from a company to a technology through a supplier does not prove that the company uses that technology. The API returns provenance so the assistant can explain the chain and its limitations.

### Current boundaries

- Entity similarity uses string matching, not vector or contextual identity resolution.
- No automatic entity merges or canonical identity changes.
- Conflict detection is scoped to the exact same subject and predicate, different objects, and overlapping dates; it is not a general contradiction engine.
- Temporal values depend on explicit source evidence and may be unknown.
- Multi-hop paths are bounded and do not imply causal or transitive relationships.
- Human review, source deletion handling, reviewer permissions and audit monitoring remain operational responsibilities.

### Migration order

Apply migrations 001 through 009 in numerical order. Migration 008 is additive and leaves existing assertion validity dates null.


## Human review interface

The `/research/review` interface exposes a provenance-rich queue for eligible unverified assertions. Access requires both normal authentication and an explicit `ORIOM7_GRAPH_REVIEWER_SUBJECTS` allow-list; decisions additionally require the server-held graph review token. See [Evidence Verification Centre](EVIDENCE_VERIFICATION_CENTRE.md).
