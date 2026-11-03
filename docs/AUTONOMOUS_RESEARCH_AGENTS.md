# ORIOM7 Autonomous Research Agents

## Durable multi-agent workflow

Research is now queued for a separate worker process. A user submits an objective and receives a run ID immediately. The worker leases jobs from PostgreSQL using row locks and `SKIP LOCKED`, records progress and results, retries bounded failures, and recovers abandoned jobs after a lease expires.

The workflow uses three specialist roles with explicit stages:
1. **Research planner** — proposes two to four focused search questions.
2. **Evidence retriever** — queries configured first-party lexical/semantic and external search providers, then deduplicates canonical URLs.
3. **Research synthesiser** — prepares a brief using only retrieved excerpts and exact source labels.

These are separate role prompts/stages in the current worker, not separate independently deployed agent services or different model instances. Model provider fallback remains controlled by the shared orchestrator.

## Recurring research

Authenticated users can create schedules from 60 minutes to 30 days. The worker checks due schedules and creates ordinary research runs; schedules can be listed, paused and resumed. Schedules are opt-in, scoped to their owner and use the same bounded source and evidence rules. They do not discover or crawl new sites. The worker must be running for due schedules to execute.

## API

- `POST /v1/research/agents/runs` — enqueue a run (HTTP 202).
- `GET /v1/research/agents/runs` — list the authenticated user's runs.
- `GET /v1/research/agents/runs/{run_id}` — inspect status, plan and result.
- `POST /v1/research/agents/schedules` — create recurring research.
- `GET /v1/research/agents/schedules` — list the user's schedules.
- `PATCH /v1/research/agents/schedules/{schedule_id}` — pause/resume with `{"enabled":true|false}`.

## Deployment

Apply migrations 001 through 010 in order. Run the API and a separate worker process from `services/api`:

```bash
python worker.py
```

Configure `DATABASE_URL`, at least one model provider and the desired search provider on the worker. The worker uses PostgreSQL lexical search, optional pgvector semantic retrieval, and configured external search; configure the same database and model/search secrets in the worker environment. The worker also continues to process the existing approved-source crawl queue.

## Trust and safety

- Every job and schedule is tied to an authenticated subject; list/detail and schedule operations are owner-filtered.
- Worker leases permit multiple workers to claim different jobs without duplicate concurrent claims.
- Retries are bounded (maximum three attempts by default); expired leases can be reclaimed.
- Retrieved excerpts are untrusted input. Citation labels are mapped to retrieved source records, not semantically entailment-verified.
- Optional graph extraction is opt-in, limited to five eligible owned-index documents, and all candidate assertions remain unverified for human review.
- No arbitrary URL browsing, code execution, purchases, messaging or permission expansion.
- Schedule cadence is bounded between one hour and 30 days. Disable schedules to stop future run creation.

## Current limitations

- Specialist roles are sequential stages in one worker process and share the configured model orchestrator; independent agent runtimes and inter-agent negotiation are future work.
- Run execution is durable and asynchronous, but progress is currently coarse-grained (queued/running/completed/partial/failed); per-stage event streaming is not yet implemented.
- A recurring schedule creates another bounded run; it does not compare successive results or send notifications.
- No semantic claim-entailment verification, comprehensive contradiction engine or factual guarantee.
- Production deployment, worker supervision, database migration and provider credentials must be configured and verified separately.
