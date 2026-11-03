# ORIOM7 API Service

Target runtime: Python 3.12+ and FastAPI.

Responsibilities: authentication and tenant context; request validation, quotas and rate limits; versioned search and assistant endpoints; search/model orchestration; usage and request telemetry.

Do not run long crawling or indexing jobs in HTTP handlers. Dispatch work to managed queues and workers.
