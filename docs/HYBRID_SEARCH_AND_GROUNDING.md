# ORIOM7 Hybrid Search and Evidence Grounding

## What is implemented

The API now has a provider-neutral retrieval contract and two retrieval paths:

1. **ORIOM7-owned index:** PostgreSQL full-text search over the `search_documents` table, using a weighted generated `tsvector`, GIN index, query ranking and highlighted excerpts.
2. **External web search:** an optional SerpApi Google organic-results adapter. It normalises result title, canonical URL, snippet, provider, retrieval time and source type into the same internal result model.

The retrieval service applies reciprocal-rank fusion across provider-ranked lists so incomparable provider score scales are not mixed directly, then deduplicates canonical URLs while retaining the strongest fused rank. External results are transient; this adapter does not crawl or persist third-party page content.

## Database setup

Apply migrations in order:

```bash
psql "$DATABASE_URL" -f services/api/migrations/001_accessibility_profiles.sql
psql "$DATABASE_URL" -f services/api/migrations/002_search_index.sql
```

The index searches only records where:
- `index_status = 'indexed'`
- `rights_basis` is non-empty
- `robots_status` is `allowed` or `not_applicable`
- `deleted_at IS NULL`

This is a query-time eligibility filter, not a substitute for a documented source approval process. A source must be reviewed for terms, rights, privacy, retention and deletion obligations before indexing.

The repository does not yet include a production crawler, ingestion UI or source-approval workflow. Populate the table only through a controlled, permission-aware ingestion process.

## External search configuration

Set `SERPAPI_API_KEY` in the backend secret manager. Optional `ORIOM7_SEARCH_COUNTRY` defaults to `gb`. Never put the secret in the web client or commit it to Git.

The adapter calls `https://serpapi.com/search.json` with `engine=google`, query, result count and country/language preferences. It consumes the `organic_results` fields `title`, `link` and `snippet`. It rejects non-HTTP(S) links and does not store the API key in application logs.

SerpApi reference: https://serpapi.com/search-api

## API usage

### Search

`POST /v1/search`

```json
{
  "query": "grid-scale battery storage",
  "sources": ["oriom7_index", "external"],
  "limit": 10,
  "language": "en-GB"
}
```

If a requested source is not configured, the response reports `status: partial` and lists `unavailable_sources`. It does not claim that an unavailable source was searched.

### Grounded assistant

`POST /v1/assistant/responses`

```json
{
  "input": "Compare current evidence on grid-scale batteries.",
  "mode": "research",
  "grounding": {
    "search": true,
    "minimum_sources": 2
  }
}
```

When grounding is requested, the API retrieves evidence before model invocation. It supplies labelled excerpts such as `[S1]` and instructs the model to cite only those labels. The API maps used labels back to source records and reports unknown labels as invalid references.

Grounding states:
- `grounded`: the requested minimum number of evidence records was retrieved.
- `insufficient_sources`: some evidence was retrieved, but fewer than requested.
- `no_results`: the retrieval paths returned no evidence.
- `not_requested`: grounding was explicitly disabled.

Citation validation states:
- `valid`: no unknown source labels were used.
- `no_citations`: evidence was supplied but the model cited none.
- `invalid_references`: the model used one or more labels that were not supplied.

A valid label only proves that the label maps to a retrieved result. It does not prove that the cited page supports the associated claim. Semantic claim-to-source verification, source fetching, passage-level quotations and independent fact checking remain future work.

## Current limitations

- PostgreSQL lexical retrieval only; semantic/vector retrieval and semantic reranking are not yet implemented.
- External provider support currently includes the optional SerpApi Google adapter only.
- The external adapter returns search snippets, not full page contents.
- No crawler, ingestion worker, content parser, source approval console or rights-review automation is included.
- No publication date is invented; missing dates remain null.
- No independent semantic entailment check is performed on citations.
- The assistant remains non-streaming.
- External provider failures fail the grounded request rather than silently pretending that provider succeeded.

## Quality and safety gates before launch

- Apply migrations and test with an approved, rights-reviewed corpus.
- Add source-level ingestion and deletion workflows.
- Verify external provider plan, permitted use, retention and privacy requirements.
- Test query syntax, language matching, ranking, canonical URL normalisation and duplicate handling.
- Add claim-to-passage citation evaluation and adversarial citation tests.
- Add per-tenant quotas, search-provider spend controls, timeout budgets and audit records.
- Benchmark latency and retrieval relevance before adding vector search.
