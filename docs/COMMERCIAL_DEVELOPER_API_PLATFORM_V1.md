# ORIOM7 Commercial Developer API Platform V1

## Current implementation status

This release establishes the developer-platform foundation and a first server-side embedding endpoint. It is not a fully launched paid API marketplace.

| Product | Current status | What is still required |
|---|---|---|
| Multilingual Translation | Planned | Select provider, configure credentials, quality evaluation, usage/billing |
| OCR & Document Intelligence | Planned | Secure upload/object storage, OCR provider, retention controls, evaluation |
| Speech & Transcription | Planned | Speech provider, audio upload limits, consent and retention controls |
| Text-to-Speech | Planned | Speech synthesis provider, voice rights and safety controls |
| Text Embeddings | Preview | Configured embedding provider, production auth integration, quotas and billing |
| Multilingual Search | Existing core preview | Cross-language evaluation, developer auth, quotas and billing |

## Endpoints

### Product catalogue
`GET /v1/developer/products`

Returns product codes, descriptions, metering units and explicit readiness status. It does not claim that planned products are available.

### Create an API key
`POST /v1/developer/keys`

Requires trusted authentication middleware to set `request.state.user_id`. Request:

```json
{ "name": "My integration", "plan_code": "starter" }
```

The response contains the secret once. The database stores only its SHA-256 hash and a short prefix. Never log or persist the returned plaintext key. Key issuance is not available until trusted identity middleware and PostgreSQL are configured.

Supported plan labels are placeholders for entitlement configuration: starter, builder, business and enterprise. They are not payment plans and do not imply billing has been activated.

### Manage API keys
`GET /v1/developer/keys` lists the authenticated user's key metadata without returning secrets. `DELETE /v1/developer/keys/{api_key_id}` revokes a key owned by the authenticated user. Both require trusted identity middleware. Create a replacement key before revoking an in-use key to avoid integration downtime.

### Text embeddings
`POST /v1/embeddings/text`

Requires an active ORIOM7 developer API key in the Bearer header and a server-side embedding provider configured with the existing ORIOM7 embedding environment variables.

Request:

```json
{ "input": ["A search engine for everyone", "Recherche multilingue"] }
```

The endpoint returns vectors, model identifier and dimensions. It accepts 1–64 non-empty text inputs, each no longer than 12,000 characters. Only the configured model is callable; a caller cannot select arbitrary provider models. Usage is recorded in input characters after successful provider completion.

### Usage summary
`GET /v1/developer/usage`

Returns the current calendar month's request and unit totals by product for the presented API key. It is a usage ledger, not an invoice.

## Database setup

Apply migrations 001–012 in order. Migration 012 creates:
- `developer_api_keys`: owner, key prefix, hash, plan label, lifecycle timestamps;
- `developer_api_usage`: product, request count, units, status, optional cost estimate and metadata.

Do not apply this migration to production until a backup and migration rehearsal have completed.

## Security and production gates

Before public launch:
1. Integrate trusted OIDC/session authentication and populate `request.state.user_id` only from verified identity claims.
2. Add key listing, revocation and rotation endpoints with owner-scoped authorization.
3. Add atomic quotas, rate limiting, abuse detection and idempotency controls.
4. Integrate a payment processor, customer/plan entitlements, tax handling, invoices, refunds and webhook signature verification.
5. Store provider credentials in a secret manager; never in browser code.
6. Add tenant isolation, audit logging, retention/deletion controls and incident response.
7. Add provider adapters for translation, OCR, speech transcription and speech synthesis.
8. Run load, security, privacy, language-quality and accessibility tests.
9. Publish prices only after measuring provider cost, infrastructure cost, support overhead and gross margin.

The product catalogue deliberately reports `billing_status: not_configured`. No charges are taken and no daily revenue is implied by this code.
