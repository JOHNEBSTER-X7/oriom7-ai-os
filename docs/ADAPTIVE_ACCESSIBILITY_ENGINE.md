# ORIOM7 Adaptive Accessibility Engine — Technical Design

**Version:** 1.0  
**Status:** Reference package and integration contract; production integration pending.

## 1. Objective

Provide one consistent accessibility preference model across the ORIOM7 web application, Search, AI Assistant and Developer API. The engine resolves user-selected settings into presentation and interaction instructions. It does not classify users, diagnose conditions or infer needs from behaviour.

## 2. Logical architecture

```text
User settings / local preferences / optional account profile
                         |
                         v
             Profile validation boundary
                         |
                         v
             Adaptive profile resolver
                |                |
                v                v
       Presentation adapters   Interaction adapters
                |                |
                v                v
      Search + Assistant UI   Keyboard / touch / voice
                |
                v
      Answer-formatting adapter
                |
                v
   Canonical answer + citations + caveats
                |
                v
  Plain language / stepwise / speech-ready variants
```

The canonical answer and evidence remain the source of truth. Accessibility transformations may change format, order and reading complexity, but must not silently change factual claims, remove citations, hide warnings or weaken safety language.

## 3. Profile domains

| Domain | Representative settings | Applied to |
|---|---|---|
| Display | text scale, font, weight, line height, letter spacing, theme, contrast | Web design system |
| Reading | speech output, speech rate, spoken-text highlighting, plain language, detail level, preferred language | Search and assistant responses |
| Interaction | voice input, large targets, keyboard-first preference, visible focus, destructive-action confirmation, save progress | Search, navigation and controls |
| Content | reduced clutter, step-by-step presentation, short answer first, citation preservation | Results and assistant |
| Sensory | reduced motion, disable autoplay, mute nonessential audio, calm presentation | All UI surfaces |

The schema is allow-listed. Unknown fields are discarded; a field named `diagnosis` or similar is not part of the model. Defaults are conservative and do not activate speech capture.

## 4. Resolution precedence

1. Platform/browser accessibility settings are respected by the UI and are not overwritten by the engine.
2. Explicit temporary session overrides take precedence over saved preferences for that session.
3. Saved user preferences take precedence over product defaults.
4. Product defaults apply when no preference is available.

Temporary overrides must not mutate or persist to the saved profile. Users can reset to defaults at any time.

## 5. API contract

All routes are versioned under `/v1`, authenticated where they access account data, tenant-scoped and protected by rate limits.

### GET /v1/accessibility/profile

Returns the authenticated user's saved profile, or the default profile if none exists. A local-only anonymous experience should not require account creation.

### PUT /v1/accessibility/profile

Replaces the authenticated user's profile after schema validation. The server must derive the owner from the authenticated principal; it must not trust a caller-supplied user identifier.

Example request:

```json
{
  "version": 1,
  "display": { "textScale": 1.4, "contrast": "high" },
  "reading": { "plainLanguage": true, "detailLevel": "concise" },
  "interaction": { "largeTargets": true, "confirmDestructiveActions": true },
  "content": { "reduceClutter": true, "preserveCitations": true },
  "sensory": { "reduceMotion": true, "disableAutoplay": true }
}
```

Return the validated canonical profile. Reject malformed payloads with a stable validation error; do not silently accept unsupported enum values at the API boundary.

### DELETE /v1/accessibility/profile

Deletes the saved profile and restores defaults. Deletion must be scoped to the authenticated principal and recorded in the normal security audit trail without copying the profile contents into logs.

### POST /v1/accessibility/resolve

Resolves a saved or default profile with temporary session overrides. The response is ephemeral and must not write to persistent storage.

## 6. Search and assistant integration

- Search ranking, retrieval, source eligibility and result order are not changed merely because a user enables an accessibility preference.
- Result cards expose semantic headings, accessible names, keyboard operation and source metadata.
- Search status, result counts, loading, empty states and errors are announced accessibly.
- The assistant retains a canonical evidence-backed answer and a structured representation of citations.
- Plain-language and stepwise variants preserve uncertainty, safety warnings, dates, units, quotations and source references.
- Speech output is an optional presentation adapter. It does not require microphone permission.
- Voice input is a separate opt-in capability with a visible recording state, cancel action and explicit capture permission.
- Translated answers retain access to the original source language and clearly indicate when translation is machine-generated.

## 7. Security, privacy and abuse controls

- No diagnosis, disability category, emotional-state or health-condition field.
- No inference from query content, voice, typing cadence, reading speed, navigation or engagement.
- No use of preferences for advertising, eligibility decisions or search ranking.
- Store only the settings required to deliver the selected experience.
- Make account synchronisation optional; local/session preferences should be possible.
- Provide reset and deletion; define retention and backup deletion behaviour.
- Do not log speech transcripts or preference payloads by default.
- Voice and image capture require independent permission; enabling voice output does not authorise voice input.
- Validate profiles on both client and server; enforce ownership and tenant isolation.
- Keep destructive actions reversible where possible and confirm them when configured.

## 8. Quality and acceptance gates

### Functional tests
- Missing profile returns defaults.
- Out-of-range numeric values are rejected at API boundary and safely bounded by the local resolver.
- Unknown fields are discarded by the resolver.
- Temporary overrides do not mutate saved preferences.
- Citations remain enabled in every resolved profile.
- Combined settings work together without one setting disabling another.

### Accessibility tests
- Keyboard-only operation for all essential flows.
- NVDA and VoiceOver on supported desktop/browser combinations; TalkBack on supported Android combinations.
- Browser zoom and text scaling without content loss or horizontal scrolling for ordinary content.
- Contrast, focus visibility, reduced motion and target sizing.
- Voice and speech controls with equivalent non-voice paths.
- Manual evaluation of headings, landmarks, status announcements, dialogs and error recovery.

### Human evaluation
Run task-based sessions with people who use screen readers, magnification, alternative input, plain-language support and reduced-stimulation settings. Measure task completion, errors, comprehension and perceived effort. Do not claim accessibility conformance from automated scan scores alone.

## 9. Standards baseline

Target WCAG 2.2 Level AA for the web experience. WCAG 2.2 is the W3C Recommendation and covers a broad range of visual, auditory, motor, speech, photosensitivity and cognitive access needs; it does not address every individual need. The implementation must be assessed against the full set of applicable success criteria: https://www.w3.org/TR/WCAG22/.

## 10. Delivery stages

1. **Foundation:** profile schema, resolver, safe defaults, local preference UI and semantic design-system hooks.
2. **Core integration:** Search and Assistant presentation adapters; accessible streaming/status announcements.
3. **Account sync:** authenticated profile endpoints, reset/delete, audit and tenant-isolation tests.
4. **Advanced interaction:** speech, voice input, reading guide, switch-compatible patterns and session recovery.
5. **Validation:** assistive-technology testing, disabled-user research and remediation before any conformance claim.

## 11. Implementation status

Committed to the repository:
- TypeScript profile model, defaults, normalisation and temporary override resolver.
- JSON Schema for the profile contract and framework-neutral resolver test cases.
- FastAPI GET, PUT, DELETE and temporary-resolve endpoints.
- In-memory development/test store and PostgreSQL storage adapter.
- PostgreSQL migration for per-subject JSONB profiles.
- Next.js settings page, accessible form controls and same-origin API proxy routes.
- GitHub Actions workflow for API tests and web type checking.

Integration requirements and limitations:
- Production authentication middleware must verify the OIDC/session identity and set `request.state.user_id`; the API does not yet include a complete identity-provider integration.
- Apply the SQL migration and configure `DATABASE_URL` for durable storage. Production startup refuses to use the in-memory store.
- The development user header is disabled by default and must never be enabled on a public or production deployment.
- The global Next.js provider now applies text scaling, typography, themes, contrast, larger targets and reduced-motion settings across the application. Local-only browser storage is available, with optional account synchronisation.
- Speech synthesis, microphone capture, reading-guide rendering, switch-device adapters and Search/Assistant content adapters are not yet connected.
- CI has been configured, but a passing workflow result has not yet been observed in this work session.
- Independent accessibility audit or WCAG conformance assessment has not been performed.
