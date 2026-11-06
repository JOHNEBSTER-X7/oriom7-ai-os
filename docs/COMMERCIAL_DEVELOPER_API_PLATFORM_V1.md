# ORIOM7 Commercial Developer API Platform V1

## Current implementation status

This release establishes the developer-platform foundation and a first server-side embedding endpoint. It is not a fully launched paid API marketplace.

| Product | Current status | What is still required |
|---|---|---|
| Multilingual Translation | Preview when configured | Configure trusted HTTPS provider, language-quality evaluation and commercial monitoring |
| OCR & Document Intelligence | Preview when configured | Configure trusted HTTPS provider, retention/data-residency review, malware scanning and extraction evaluation |
| Speech & Transcription | Preview when configured | Trusted HTTPS transcription provider, language/accuracy evaluation, audio consent and retention controls |
| Text-to-Speech | Preview when configured | Trusted HTTPS synthesis provider, voice rights, safety and quality controls |
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


## Translation API preview

`POST /v1/translation/text` is implemented as a provider-backed preview. It accepts `{ "text": "Hello", "source": "en", "target": "fr", "format": "text" }` and returns translated text plus input-character usage. The provider is an operator-configured LibreTranslate-compatible HTTPS endpoint (`ORIOM7_TRANSLATION_ENDPOINT`) with an optional server-side `ORIOM7_TRANSLATION_API_KEY`; callers cannot choose the endpoint or provider credential. Requests are bounded to 50,000 characters, redirects are disabled, provider failures are surfaced as gateway errors, and usage is recorded only after successful translation. Configure and evaluate a provider before enabling this preview for customers.


## OCR & Document Intelligence API preview

`POST /v1/documents/ocr` accepts a multipart upload with fields `file` and optional `language`. Supported file types are PDF, PNG, JPEG and TIFF; file signatures are checked and uploads are limited to 15 MB. The provider receives the file over HTTPS using the operator-configured `ORIOM7_OCR_ENDPOINT` and optional server-side `ORIOM7_OCR_API_KEY`. It must return JSON shaped as `{"text":"...","pages":1}`. The API validates extracted text and page count, records successful usage in pages, and returns a SHA-256 digest and extracted text. Original files are held in memory for the request and are not persisted by ORIOM7. The configured OCR provider will receive the document, so operators must assess provider retention, data residency, confidentiality and contractual terms before enabling the endpoint. Without a configured provider the product remains planned and requests return HTTP 503.

The upload route is intended for documents the caller is authorised to process. It does not yet provide malware scanning, encrypted object storage, durable document records, asynchronous jobs, redaction, table/field extraction, or a provider-independent OCR engine. Do not use it for sensitive production documents until the provider and deployment controls have been reviewed.


## Speech Intelligence V1

### Speech-to-text

`POST /v1/speech/transcriptions` accepts multipart fields `file` and optional `language`, requires an ORIOM7 developer API key, and supports WAV, MP3, OGG, WebM, MP4 and AAC media types with basic signature checks. Uploads are limited to 25 MB. The operator configures `ORIOM7_SPEECH_ENDPOINT` and optional server-side `ORIOM7_SPEECH_API_KEY`; the provider must return JSON containing `text` and numeric `duration_seconds`, with optional `language` and `segments`. Segment entries use `start`, `end`, `text` and optional provider-supplied `speaker`. ORIOM7 validates response bounds and meters rounded-up audio seconds. Original audio is not persisted by ORIOM7.

### Text-to-speech

`POST /v1/speech/synthesis` accepts JSON `{ "text": "Hello", "voice": "default", "format": "mp3" }`, with text limited to 10,000 characters. The operator configures `ORIOM7_TTS_ENDPOINT` and optional `ORIOM7_TTS_API_KEY`. The provider receives text, voice and format and returns audio bytes with a supported audio content type. Output is limited to 20 MB, returned with `Cache-Control: no-store`, and metered by input characters.

These are provider adapters, not proprietary speech models. Timestamping and speaker labels are included only when returned by the configured transcription provider. Neither product is available until its provider is configured and evaluated. Provider privacy, data residency, consent, voice licensing, retention and security terms must be reviewed before production use. The API does not currently provide streaming synthesis, asynchronous jobs, speaker diarisation itself, voice cloning, or a built-in speech engine.


## Real-Time Voice Intelligence V1

### End-to-end voice turn

`POST /v1/assistant/voice-turn` is an authenticated user endpoint that connects the configured speech recognition provider, the existing ORIOM7 assistant response pipeline, the user's saved accessibility presentation preferences, and the configured text-to-speech provider.

It accepts multipart `file` audio (same 25 MB audio limit and supported media signatures as the transcription endpoint), optional `language`, and optional `conversation_history` JSON. Conversation history is a list of at most 12 messages; roles are limited to `user` and `assistant`, each message is limited to 2,000 characters, and total history is limited to 8,000 characters. The latest transcript is appended as the current user turn. The assistant call uses the existing model orchestrator and accessibility profile; web/knowledge retrieval is disabled for this initial voice-turn path to keep conversational voice responses focused and predictable.

The response body contains synthesized audio bytes. The transcript and assistant response are available as URL-safe base64 UTF-8 in `X-ORIOM7-Transcript-B64` and `X-ORIOM7-Response-B64` headers (each capped at 3,000 characters). Additional headers report language, detected input duration and that context is request-scoped. Clients should send the prior user/assistant messages on the next request if they want continuity.

This is a sequential request/response voice pipeline, not low-latency duplex streaming. Conversation history is supplied by the client and is not saved by this endpoint. No live speech providers are configured by default. The pipeline requires both speech providers and at least one model provider, plus authenticated user identity and profile storage. Provider privacy, consent, retention, language accuracy and voice licensing remain launch gates.
