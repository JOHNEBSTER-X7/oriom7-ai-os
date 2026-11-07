# ORIOM7 OCEANGRID V1

## Purpose
OCEANGRID provides an evidence-aware coastal site screening API for potential GPU compute cooling locations. V1 scores structured inputs and preserves source provenance. It is not a live satellite platform or a feasibility certificate.

## API
Authenticated developer endpoints:
- `POST /v1/oceangrid/assess` evaluates one candidate.
- `GET /v1/oceangrid/readiness` reports connector readiness.

Inputs include coordinates, sea temperature, salinity, currents, water depth, bathymetry confidence, grid capacity, renewable share, fibre distance, protected-area overlap, environmental screening, permit status and cooling water strategy. Evidence records identify source, source type, observed/modelled/user-supplied data kind, licence, timestamp, resolution and optional URL.

## Scoring
The implementation uses weighted factors: thermal resource 15%, salinity/corrosion 8%, currents 5%, bathymetry 8%, grid 18%, renewable share 12%, fibre 10%, environmental constraints 12%, permits 7%, water strategy 5%. Unknown values are omitted from the weighted score and reduce evidence coverage. Protected-area overlap or restricted environmental status triggers exclusion review. A high score does not establish feasibility.

## Data roadmap
Potential adapters, subject to access terms and validation: Copernicus Marine, EUMETSAT, Copernicus Sentinel, NASA SWOT, NOAA, Argo and licensed commercial satellite imagery. Products have different resolutions, revisit intervals, coverage and licences. Satellite surface observations do not reveal full water-column conditions or seabed engineering suitability.

## Environmental and regulatory controls
Future site evaluation must consider national and EEZ jurisdiction, marine protected areas, habitats, fisheries, thermal discharge, environmental assessment, water intake/discharge, seabed rights, cable routes, ports, grid and planning permits. Prefer waterless or recycled-water systems. Seawater heat exchange requires isolated loops and assessment of intake, discharge temperature, corrosion and biofouling. Do not assume freshwater availability.

## V1 limitations
- No live satellite, ocean, bathymetry, grid, fibre or regulatory ingestion.
- No global spatial database or automated EEZ/protected-area overlays.
- No production ranking of actual coastlines.
- No engineering, legal, ecological or investment certification.
- Submitted evidence is not independently verified.

## Next milestones
1. Provider catalogue, licences and ingestion contracts.
2. Copernicus Marine and official EEZ/protected-area overlays.
3. Spatial storage and time-aware grid tiles with provenance.
4. Satellite/in-situ fusion, uncertainty and freshness scoring.
5. Heat-rejection models and GPU power/fibre economics.
6. Pilot engineering, environmental assessment and permits.

## Batch coastal ranking API
Authenticated `POST /v1/oceangrid/rank` accepts 1–200 candidate records and a configurable minimum evidence-coverage threshold (default 60%). It ranks eligible submitted candidates by screening score, using evidence coverage as a tie-breaker. Environmental exclusion flags and insufficient-coverage records are returned separately with reasons. Usage is metered by the number of submitted candidate sites.

This is a ranking engine for a supplied candidate set, not a ranking of every coastline on Earth. The endpoint explicitly returns `ranking_scope=submitted_candidates_only` and `global_coverage=false`. Global rankings require licensed global shoreline segmentation, global ocean and infrastructure data, EEZ/jurisdiction overlays, protected-area data and validated time-aware spatial ingestion. Never interpret a preliminary score as permission to build.
