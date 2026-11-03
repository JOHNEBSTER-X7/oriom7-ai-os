# Infrastructure

Initial model: Vercel web frontend; managed API runtime supporting streaming; separate managed background workers; managed PostgreSQL, Redis, search, object storage and queue; GitHub Actions CI/CD.

Use separate environments, least-privilege service identities and managed secrets. Keep long-running crawlers out of the frontend runtime.
