# ORIOM7 Visual Interpretation V1

This milestone adds authenticated task-guided interpretation for four image classes through the existing operator-configured vision provider.

## Endpoint

`POST /v1/vision/interpret` (multipart form; ORIOM7 developer API key required)

- `file`: JPEG, PNG or WebP, maximum 10 MB.
- `task`: one of `chart`, `map`, `diagram`, `product`.
- `question`: optional additional question, maximum 2,000 characters.

The response includes the provider description, answer, visible object labels and detected text, plus task and a verification warning. One `vision` usage unit is recorded per successful request. The original image is held transiently and is not persisted by this endpoint.

## Scope and limitations

This is task-guided prompting, not a dedicated chart parser, GIS engine, OCR guarantee, product catalogue matcher or geospatial coordinate resolver. Provider capability and accuracy vary. Never use its output as the sole authority for financial decisions, navigation, safety-critical diagrams, exact measurements or product authenticity. Verify important values and locations independently.

Requires the existing `ORIOM7_VISION_ENDPOINT` provider configuration. Provider privacy, retention, data residency and contractual terms must be reviewed before sensitive uploads. No provider credentials or live provider tests are included in this change.
