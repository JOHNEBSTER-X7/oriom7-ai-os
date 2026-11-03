# ORIOM7 Evidence Verification Centre

## Purpose

The `/research/review` interface provides a human review queue for model-extracted or manually submitted knowledge assertions. It is a governance surface: candidate relationships remain unverified until an explicitly authorised reviewer accepts or rejects them.

## Review queue API

`GET /v1/knowledge/assertions/review-queue?limit=20&offset=0`

Optional `predicate` filters by exact relationship predicate. The endpoint returns only assertions with status `unverified` whose evidence document is still indexed, non-deleted, rights-cleared and robots-eligible. Each record includes subject, predicate, object, exact evidence excerpt, source title and URL, provider, language, publication/retrieval timestamps, rights basis, robots status, extraction method, model confidence, submitter and temporal validity.

The endpoint requires normal API authentication and an explicit reviewer identity allow-list. Configure `ORIOM7_GRAPH_REVIEWER_SUBJECTS` as a comma-separated list of trusted authenticated subject identifiers. If it is missing, the queue fails closed with 503; non-allow-listed identities receive 403.

## Review decision API

`POST /v1/knowledge/assertions/{assertion_id}/review`

Body: `{"decision":"accepted"}` or `{"decision":"rejected"}`.

The endpoint requires all of:
- Normal API authentication.
- Authenticated subject present in `ORIOM7_GRAPH_REVIEWER_SUBJECTS`.
- A configured `ORIOM7_GRAPH_REVIEW_TOKEN` and matching `X-ORIOM7-GRAPH-REVIEW-TOKEN` header.
- Assertion still unverified and source evidence still eligible.

The Next.js same-origin proxy injects the review token from its server environment only. The token is never returned to or stored in browser code. Configure the same strong secret in the API and web server environments. Never use a `NEXT_PUBLIC_` variable for this secret.

## Interface safeguards

- The reviewer must tick a source-inspection confirmation before either decision control is enabled.
- A browser confirmation is shown before a decision is submitted.
- Each decision is recorded against the authenticated reviewer identity by the API.
- The queue can filter by predicate and paginate.
- The source itself is linked separately from the extracted excerpt.
- Model confidence is explicitly labelled as an extraction score, not a probability that the claim is true.
- Only accepted assertions enter graph reads and graph-aware assistant context.
- The interface does not automatically accept, merge, rewrite or promote assertions.

## Deployment configuration

Set on the API service:

```env
ORIOM7_GRAPH_REVIEWER_SUBJECTS=trusted-subject-id-1,trusted-subject-id-2
ORIOM7_GRAPH_REVIEW_TOKEN=use-a-long-random-secret
```

Set the identical `ORIOM7_GRAPH_REVIEW_TOKEN` on the Next.js server as a private server-side environment variable, alongside `ORIOM7_API_URL`. Do not prefix it with `NEXT_PUBLIC_`. The reviewer subject identifiers must match the trusted subject values produced by the API authentication middleware.

## Operational limitations

The existing review API supports one-way accept/reject decisions only. This interface does not yet provide reversal, amendment, bulk decisions, reviewer assignment, two-person approval, immutable external audit export or an appeal workflow. Rejected assertions remain stored with status `rejected`; they are not deleted. A decision cannot be undone in this UI. For high-impact claims, use independent review and a documented correction procedure.
