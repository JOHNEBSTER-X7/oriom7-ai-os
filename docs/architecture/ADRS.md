# Architecture Decision Records

## ADR-001 — Hybrid search
**Status:** Accepted. Combine an independently operated search index with external search providers. This balances long-term differentiation and control with early coverage. Build ingestion/index/ranking and provider adapters; respect source rights and terms.

## ADR-002 — Hybrid multi-model
**Status:** Accepted. Support multiple hosted model providers and a consistent interface for future self-hosted models. Route by task quality, latency, cost, capability and policy.

## ADR-003 — Vercel plus managed backend
**Status:** Accepted. Vercel hosts the initial web frontend; managed backend services host API, data, search and workers. Keep long-running jobs outside the frontend runtime.

## ADR-004 — Three integrated MVP priorities
**Status:** Accepted. Search, AI assistant and developer API are co-equal initial priorities, sharing identity, usage, retrieval and provenance.

## ADR-005 — Progressive proprietary cloud and hardware
**Status:** Accepted. Pursue proprietary AI cloud and hardware progressively, not as launch dependencies. Gate investment on measured workloads, reliability, financing and technical validation.

## ADR-006 — Universal language, voice and low-literacy access
**Status:** Accepted. Treat voice-first use, multilingual search/translation, spoken answers, plain-language explanations and icon-led accessible interaction as core product requirements. Add provider-neutral speech-to-text, translation, language identification and text-to-speech adapters; locale preferences; multilingual retrieval and evaluation; audio consent/retention controls; and community-based language quality testing. Do not claim support for languages or dialects until evaluated.

## ADR-007 — Accessibility and inclusive interaction by design
**Status:** Accepted. ORIOM7 must support independent use by blind and low-vision users, people with hearing, motor or cognitive disabilities, and people using assistive technologies. Target WCAG 2.2 AA for the web experience; prioritise semantic HTML, screen-reader support, keyboard access, focus management, text alternatives, captions/transcripts and accessible streaming states. Validate with manual testing and disabled users, not automated scanners alone.

## ADR-008 — User-controlled adaptive accessibility
**Status:** Accepted. Provide combinable, optional accessibility preferences for visual, neurological, motor, cognitive, learning, mental-health-related and sensory access needs. Ask what accommodations help rather than requiring diagnostic disclosure. Do not infer diagnoses or emotional states from searches or behaviour. Preserve user control, privacy, source provenance, safety caveats and equivalent access to core functionality.
