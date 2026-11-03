# ORIOM7 Research Intelligence Workspace

## Purpose

The Next.js application exposes a dedicated `/research` workspace for investigations that combine hybrid search, assistant synthesis and the accepted knowledge graph.

## User workflow

1. Submit a natural-language research question.
2. The workspace calls `POST /v1/search` for up to 12 search results and `GET /v1/knowledge/entities?q=...` for matching graph entities.
3. The assistant is asked for a research-mode response through `POST /v1/assistant/responses`. Search citations and graph citations remain separate.
4. Select a graph entity to load its accepted one-hop relationships and bounded paths (maximum depth 3).
5. Compare source titles, snippets, provider, language, publication date and retrieval date.
6. Explore accepted relationships in a hub-and-spoke diagram and in an equivalent text list.
7. Review the timeline using explicit validity dates where supplied, falling back to assertion creation time.
8. Export the current research question, synthesis, source results, graph relationships and citation references as a Markdown report.

## Web routes

The browser calls the same-origin Next.js proxy at `/api/research/*`. The catch-all proxy permits only these upstream API operations:

- `POST /v1/search`
- `POST /v1/assistant/responses`
- `GET /v1/knowledge/entities`
- `GET /v1/knowledge/entities/{entity_id}`
- `GET /v1/knowledge/entities/{entity_id}/paths`

The proxy forwards existing cookie and authorization headers and does not persist requests or responses.

## Accessibility

- Semantic headings, forms, labels, status announcements, tabs and lists.
- Keyboard-operable entity selection and tabs.
- The graph SVG has an accessible title and description; an equivalent relationship list is always rendered.
- Source information is available as text rather than colour or graph position alone.
- The layout reflows for mobile widths and inherits ORIOM7's global accessibility settings.
- Reduced-motion behavior is inherited from the existing global accessibility design system.

## Evidence and limitations

- Only accepted assertions whose evidence documents remain indexed, non-deleted, rights-cleared and robots-eligible are shown by graph APIs.
- Source comparison displays search results returned by configured providers; it does not imply independent verification or source agreement.
- The graph view visualises direct accepted relationships for the selected entity. Bounded multi-hop path records are displayed separately and are not presented as causal proof.
- The timeline uses explicit `valid_from`/`valid_to` when present. If validity is unknown, the UI falls back to the assertion creation timestamp and does not imply that this is the real-world event date.
- Potential inconsistencies are unresolved review signals, not verified contradictions.
- The Markdown export is generated in the browser from the current workspace state. It is not a signed, immutable or independently audited report.
- The workspace depends on API authentication, `ORIOM7_API_URL`, database migrations 001–008, indexed search sources, accepted graph assertions and configured model/search providers. A merged UI does not activate or deploy those services.
