# ORIOM7 Model Provider Configuration

## Provider architecture

ORIOM7 uses a provider-neutral adapter contract and the Responses API format. The initial hosted adapters are:

- OpenAI: `https://api.openai.com/v1/responses`
- DeepSeek: `https://api.deepseek.com/responses`

DeepSeek documents an OpenAI Responses-compatible endpoint. Both adapters normalize the response text, model identifier and token usage into ORIOM7's internal result contract. Provider-specific features remain behind the adapter boundary.

Official references:
- OpenAI Responses API and migration guidance: https://platform.openai.com/docs/guides/migrate-to-responses
- DeepSeek Responses API: https://api-docs.deepseek.com/api/create-response/
- DeepSeek Responses API guide: https://api-docs.deepseek.com/guides/responses_api/

## Environment configuration

Set these variables in the deployment secret manager or local untracked environment file. Never commit API keys.

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI secret |
| `ORIOM7_OPENAI_MODEL` | Explicit OpenAI model ID |
| `ORIOM7_OPENAI_BASE_URL` | Optional OpenAI-compatible base URL; defaults to OpenAI API |
| `DEEPSEEK_API_KEY` | DeepSeek secret |
| `ORIOM7_DEEPSEEK_MODEL` | Explicit DeepSeek model ID |
| `ORIOM7_DEEPSEEK_BASE_URL` | Optional DeepSeek base URL |
| `ORIOM7_MODEL_PRIMARY` | Preferred provider; defaults to `openai` |
| `ORIOM7_MODEL_FALLBACK` | Secondary provider; defaults to `deepseek` |
| `ORIOM7_OPENAI_INPUT_USD_PER_MILLION` | Optional configured input-token price |
| `ORIOM7_OPENAI_OUTPUT_USD_PER_MILLION` | Optional configured output-token price |
| `ORIOM7_DEEPSEEK_INPUT_USD_PER_MILLION` | Optional configured input-token price |
| `ORIOM7_DEEPSEEK_OUTPUT_USD_PER_MILLION` | Optional configured output-token price |

A provider is registered only when both its API key and explicit model ID are configured. ORIOM7 does not assume a model name or silently choose one. Configure model-specific prices from the provider's current pricing page; estimates remain unavailable when rates are omitted.

## Runtime behaviour

- The primary provider is attempted first, then the configured fallback.
- Network, HTTP, malformed-response and empty-response failures are treated as provider failures.
- The request payload and user prompt are not written to application logs.
- Logs record provider, model, latency, token usage, estimated cost when configured, and whether fallback was used.
- API keys are only read from server environment variables.
- The current endpoint uses non-streaming responses and requests `store: false`.
- Conversation persistence, streaming, retrieval grounding, source validation and provider-specific tool execution are not implemented in this slice.

## API

Authenticated endpoint: `POST /v1/assistant/responses`

Example request:

```json
{
  "input": "Explain hybrid search in simple terms.",
  "mode": "education",
  "max_output_tokens": 1200
}
```

The response includes the generated text, provider/model metadata, token usage and the active accessibility presentation directives. It currently returns `grounding.status = not_connected` and an empty source list. This is deliberate: the model must not imply that independent search or citation verification has occurred.

## Local verification

From `services/api`:

```bash
pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=. pytest -q
```

Tests use fake providers; they do not require paid provider credentials or make external API calls.
