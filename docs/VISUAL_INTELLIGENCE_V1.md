# ORIOM7 Visual Intelligence V1

## Purpose

Visual Intelligence accepts a customer-authorised image and a question, forwards them to an operator-configured vision provider, and returns a bounded structured response for human review. It is designed to support visual discovery in the ORIOM7 research workspace.

This is a provider integration, not a claim that ORIOM7 has trained or hosts its own vision foundation model.

## API

`POST /v1/vision/analyze`

Authentication: ORIOM7 developer API key in the Authorization bearer header.

Multipart fields:

- `file`: required JPEG, PNG or WebP image, maximum 10 MB.
- `question`: optional question, maximum 2,000 characters. Defaults to a clear image description request.

Successful JSON response includes:

- `description`: required provider-generated description.
- `answer`: optional answer to the supplied question.
- `objects`: optional bounded list of visible item labels.
- `text_found`: optional bounded list of text detected in the image.
- `sha256`, `media_type`, `usage`, and `storage`.

Original image bytes are held in memory for the request and are not persisted by this endpoint. The configured provider receives the image. Operators must assess the provider's privacy terms, retention, processing region, security posture and contractual obligations before enabling the feature for sensitive data.

## Provider configuration

Set these server-side environment variables:

- `ORIOM7_VISION_ENDPOINT`: trusted HTTPS endpoint implementing the ORIOM7 provider JSON contract.
- `ORIOM7_VISION_API_KEY`: optional provider bearer credential.
- `ORIOM7_VISION_MODEL`: optional provider model identifier; defaults to `default`.

The provider receives JSON:

```json
{
  "model": "default",
  "question": "What is shown in this image?",
  "image": {
    "media_type": "image/jpeg",
    "data_base64": "<base64-encoded image bytes>"
  }
}
```

The provider must return JSON with a non-empty `description` string. Optional `answer` must be a string; `objects` and `text_found` must be arrays of bounded strings. Responses larger than 1 MB or outside the schema are rejected.

Only HTTPS endpoints are accepted. Redirects are disabled. The endpoint is operator-controlled and cannot be supplied by API callers.

## Usage and limitations

Successful analyses are metered as one `vision` unit per image. The original image is not stored by ORIOM7. Provider-side handling is outside ORIOM7's storage boundary and must be evaluated separately.

V1 supports still-image understanding for JPEG, PNG and WebP. It does not provide video understanding, real-time camera streams, image generation, biometric identification, medical diagnosis, or guaranteed factual correctness. Users should verify measurements, chart interpretations, labels and other consequential claims against the original source.

## Research workspace

The multimodal intake allows a user to submit an image question. The returned description and answer are shown for review and copied into the research query field (subject to the interface's 1,800-character context limit). Users can edit the query before running research. Image bytes are not sent to the ordinary text search endpoint.

## Validation

Automated API tests cover successful analysis, usage metering, invalid signatures, unsupported media types, missing provider configuration, HTTPS enforcement and invalid provider responses. Provider-backed staging tests and manual accessibility checks remain required before production use.
