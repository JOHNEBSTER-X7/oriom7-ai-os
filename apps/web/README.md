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

## LAB OS workspace

The `/labs` route provides the initial research-operations workspace:
- Create and select research projects.
- Register experiment plans and hypotheses.
- Record controlled status transitions through append-only events.
- Register and view laboratory equipment metadata.

The same-origin proxy is `/api/labs/[...path]`; it forwards the existing session cookie
or bearer token to the FastAPI service. Set `ORIOM7_API_URL` to the API origin and
configure trusted authentication middleware there. The persistent LAB OS endpoints
also require PostgreSQL migration `011_lab_os.sql`.

The UI records research plans and notebook entries, manages equipment assets, calibration and maintenance histories, and books equipment time slots. It does not run experiments, control instruments, book physical facilities, or verify scientific results.


The LAB OS workspace now includes a Digital Notebook for project-level or experiment-linked notes, hypotheses, observations, measurements, results, decisions, protocols, reviews and deviations. Notebook entries are append-only and require database migration `012_lab_digital_notebook.sql` after migration 011. This is not a validated regulated LIMS or electronic-signature system.


The Equipment Manager provides asset selection/status, calibration records and due dates, maintenance history, and equipment bookings with conflict rejection. Apply `013_equipment_manager.sql` after `012_lab_digital_notebook.sql`. Records remain owner-scoped; calibration and maintenance entries are append-only.


## LAB inventory and procurement

The `/labs` workspace now includes inventory and procurement controls for stock item registration, supplier records, purchase requisitions, purchase orders, goods receipts, lot tracking, stock on hand and procurement metrics. Apply API migration `014_lab_inventory_procurement.sql` after 011–013.

The stock movement ledger is append-only. Goods receipts and stock issues are traceable to batch/lot records; normal issues require accepted, unexpired lots. Hazard classifications and Safety Data Sheet references are informational records only and do not authorize hazardous-material handling or purchasing.


## LAB quality, compliance and analytics

The `/labs` workspace includes lot inspection records, automatic quarantine and non-conformance creation for failed/conditional results, CAPA tracking and status history, compliance-document review/expiry monitoring, inspection history and supplier quality scorecards. Apply migration `015_lab_quality_compliance.sql` after 011–014.

A passing inspection records lot acceptance; failed and conditional inspections quarantine the lot. CAPA actions must reach completed before they can be verified. Document references are not independently authenticated, and this module is not a validated QMS or legal compliance service.
