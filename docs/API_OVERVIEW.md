# ORIOM7 API Overview

Base path: `/v1`

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/status` | Liveness/status information |
| GET | `/models` | Models enabled for caller |
| POST | `/search` | Hybrid search |
| POST | `/assistant/responses` | Evidence-aware assistant response |
| GET | `/usage` | Caller usage summary |

All endpoints require an authenticated context except a deliberately configured public health endpoint. Enforce tenant, scope, quota and request-size policies server-side. Detailed contract: `../contracts/openapi.json`.
