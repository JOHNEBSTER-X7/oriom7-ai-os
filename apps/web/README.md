# ORIOM7 Web Application

Next.js, React and TypeScript application targeting Vercel.

## Run locally

```bash
npm install
cp .env.example .env.local
npm run dev
```

Set `ORIOM7_API_URL` to the FastAPI origin. The app uses same-origin Next.js route handlers to proxy accessibility profile requests. The API must receive the authenticated session or bearer token and must have trusted authentication middleware configured.

## Current UI

The first page contains an interactive accessibility preference screen with display, reading, interaction, content and sensory settings. It requires a signed-in session to persist account preferences. The page can still be used to explore settings without signing in, but the current settings are not stored locally between reloads.

The controls configure preferences; they do not themselves provide microphone capture, speech synthesis, switch-device support or full screen-reader certification. Those capabilities require the corresponding adapters and testing.

Keep provider credentials and orchestration logic server-side; never embed secrets in client bundles.


## Developer portal

- `/developer` — product catalogue, API key management and usage overview.
- `/api-docs` — API authentication and endpoint reference.

The portal uses same-origin Next.js route handlers to forward requests to `ORIOM7_API_URL`. It requires the API deployment's trusted identity middleware for account-scoped key management. The usage panel requires the developer's API key and does not persist it in browser storage. Billing is not configured and planned products are labelled as such.
