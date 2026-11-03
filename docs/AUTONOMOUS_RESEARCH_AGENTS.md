# ORIOM7 Autonomous Research Agents

## Initial capability

The first supervised research agent is user-initiated and bounded. It:
1. Accepts one research objective.
2. Uses a configured model to propose two to four focused search questions.
3. Searches configured ORIOM7-owned and external retrieval providers for each question.
4. Deduplicates results by canonical URL and caps the evidence set.
5. Produces a research synthesis from retrieved excerpts with source labels.
6. Returns the plan, per-question result counts, source provenance, citation mapping and limitations.
7. Optionally extracts graph candidates from up to five eligible ORIOM7-indexed documents. Candidates remain unverified and enter the existing human review queue.

## API

- `POST /v1/research/agents/runs` starts a run.
- `GET /v1/research/agents/runs` lists only the authenticated user's runs.
- `GET /v1/research/agents/runs/{run_id}` retrieves one of that user's runs.

The request bounds the question to 2,000 characters, source count to 3–30 and graph candidate extraction to an explicit opt-in. The model plan is constrained to 2–4 focused questions. The agent performs retrieval only; it does not browse arbitrary URLs, execute code, send messages, purchase goods, or take external actions.

## Persistence and isolation

Migration 009 creates `research_agent_runs`. Runs are associated with the authenticated subject. List and detail endpoints filter by that subject. Plan and output are persisted for review and continuity.

## Evidence and safety controls

- Search excerpts are treated as untrusted data, not instructions.
- Only retrieved evidence is supplied as source material for synthesis.
- Citation labels are mapped to retrieved records, but this does not establish semantic entailment.
- Invalid citation labels are surfaced.
- Candidate extraction is limited to owned-index documents and uses the existing exact-excerpt checks.
- Every graph candidate is stored as `unverified`; only an authorised human reviewer can accept or reject it.
- The agent does not automatically change the knowledge graph's accepted facts.

## Current limitations

- Execution is synchronous within the HTTP request; this is not yet a durable background job queue, recurring agent or continuous monitoring service.
- No task delegation between multiple specialised agents yet; the first agent uses a plan-and-retrieve loop.
- No automatic source discovery or crawl permission expansion. Ingestion still uses the existing approved-source controls.
- No claim-level semantic entailment validation, general contradiction engine or fact-verification guarantee.
- Provider rate limits, latency and retrieval coverage depend on deployment configuration.
- A client timeout may interrupt the request even though the run row has been created. A future durable worker should claim and resume runs using leases.
