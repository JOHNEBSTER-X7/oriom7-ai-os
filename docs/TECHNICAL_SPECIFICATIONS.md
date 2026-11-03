# ORIOM7 Technical Specifications

**Version:** 1.0 — 3 November 2026

## 1. Reference stack

| Area | Initial choice / approach |
|---|---|
| Web | Next.js, React, TypeScript |
| Hosting | Vercel |
| API | Python, FastAPI, OpenAPI 3.1 |
| Primary data | Managed PostgreSQL |
| Cache / rate limits | Managed Redis |
| Search | Managed OpenSearch/Elasticsearch-compatible service or equivalent |
| Vector retrieval | Qdrant or equivalent, subject to evaluation |
| Object storage | S3-compatible managed object storage |
| Queue | Managed queue first; Kafka only when justified |
| Identity | OIDC provider; hashed API keys for developer access |
| CI/CD | GitHub Actions |
| Runtime | Managed API runtime plus separate background workers |

These services are candidates, not locked vendors. Benchmark against security, region, cost, operations and workload.

## 2. API conventions

- Base path: `/v1`.
- JSON request and response bodies.
- UTC ISO-8601 timestamps.
- Correlation header: `X-Request-ID`.
- Authentication: end-user OIDC session or developer API key.
- Pagination: opaque cursor for large collections.
- Errors: stable machine-readable code, human-readable message and request ID.
- Rate-limit responses use HTTP 429 and a retry hint where appropriate.

## 3. Search request

`POST /v1/search`

Example:
```json
{
  "query": "renewable energy storage policy",
  "sources": ["oriom7_index", "external"],
  "limit": 10,
  "language": "en",
  "region": "GB"
}
```

Each result includes a stable ID, title, canonical URL, snippet, source type, provider, retrieval timestamp and optional publication timestamp. Do not invent publication dates or source metadata.

## 4. Assistant request

`POST /v1/assistant/responses`

Example:
```json
{
  "input": "Compare the latest evidence on grid-scale batteries",
  "conversation_id": null,
  "mode": "research",
  "stream": true,
  "grounding": {
    "search": true,
    "minimum_sources": 3
  }
}
```

The response stream should expose typed events such as response start, text delta, source reference, usage and completion. Define a stable event schema before shipping streaming clients. Streaming status, source announcements and errors must be exposed accessibly to screen readers without excessive repeated announcements.

## 5. Model registry

Each model entry should include provider and model identifier; capability tags; supported regions and data-handling constraints; context/output limits; indicative cost metadata and effective date; availability/health state; and routing eligibility.

Model metadata and price data must be verified from providers and kept current; never hard-code unverified prices into user-facing estimates.

## 6. Search indexing pipeline

1. Source discovery from approved sources.
2. Fetch with rate limits, robots/terms and source-specific policies.
3. Parse and extract text and metadata.
4. Canonicalise URL and normalise content.
5. Deduplicate using URL and content fingerprints.
6. Apply safety, copyright, privacy and retention checks.
7. Split into passages with stable document and passage IDs.
8. Generate embeddings if enabled.
9. Index lexical fields and vectors.
10. Track freshness, errors and re-crawl schedule.

Suggested document fields: `document_id`, `canonical_url`, `title`, `body_ref`, `language`, `region`, `publisher`, `published_at`, `fetched_at`, `content_hash`, `rights_basis`, `robots_status`, `index_status`, `deleted_at`.

## 7. Data model domains

Core relational entities: tenants, users, memberships, API keys (hashed); conversations, messages, response runs; search requests/results and source records; model providers, registry and routing policies; usage events, quotas and plans; crawl sources/jobs, documents and index jobs; audit events and deletion requests.

Use migrations, foreign keys and tenant-aware query patterns. Store API-key hashes, not plaintext keys.

## 8. Accessibility requirements

- Target WCAG 2.2 Level AA for the web experience.
- Prefer semantic HTML; use ARIA only to supplement native semantics.
- Every interactive control has an accessible name, role, state and keyboard operation.
- Maintain logical focus order, visible focus, skip navigation and no keyboard traps.
- Announce asynchronous search results, streaming states and errors to assistive technology.
- Provide text alternatives for informative images, charts, maps and spoken output.
- Support text resizing, zoom, contrast preferences and reduced motion.
- Captions/transcripts accompany relevant audio/video; no essential alert is sound-only.
- Test manually with screen readers, keyboard-only use and disabled participants. Automated scanners alone are not sufficient.

See `UNIVERSAL_ACCESSIBILITY_AND_INCLUSION.md` for the full product requirements.

## 9. Initial quality gates

- Unit tests for policy, adapters and normalisation.
- Contract tests against OpenAPI.
- Integration tests for PostgreSQL, cache, queue and provider mocks.
- Search relevance and citation-grounding evaluation.
- Load tests for concurrent search and streaming.
- Dependency, secret and static-analysis scans.
- Privacy and tenant-isolation tests.
- Keyboard, screen-reader and automated accessibility checks.

## 10. Adaptive accessibility and personalisation

- Provide optional user-selected functional preferences; do not require diagnostic disclosure.
- Support combinations of text scaling, contrast, typography/spacing, screen-reader/speech, voice input, reduced motion, information density, larger targets and session continuity.
- Persist preferences only with user consent; allow reset, export and deletion.
- Never infer diagnoses, emotional states or health conditions from search queries, voice, reading speed or interaction patterns.
- Ensure simplified content retains caveats, warnings, uncertainty and source references.
- Essential controls must work without fine motor gestures and have keyboard/switch-compatible alternatives.
- Avoid forced audio, autoplay, flashing, strobing and uncontrolled motion.

Full product requirements: `ADAPTIVE_ACCESSIBILITY_SYSTEM.md`.

## 11. Adaptive Accessibility Engine package

The reference package is at `packages/accessibility-engine/` and currently contains:
- Typed TypeScript profile interfaces and safe defaults.
- Allow-listed profile normalisation and bounded numeric settings.
- Session-only override resolution.
- JSON Schema contract for profile validation.
- Framework-neutral contract test cases.

The package is not yet connected to the FastAPI persistence layer or Next.js design system. Integration routes and UI work are tracked in `docs/ADAPTIVE_ACCESSIBILITY_ENGINE.md`.
