# ORIOM7 Adaptive Accessibility Engine

**Status:** Shared profile resolver is integrated into the Next.js accessibility provider and settings interface. The FastAPI profile API and PostgreSQL adapter support persistence; production authentication integration and end-to-end validation remain deployment tasks.

## Purpose

A shared, user-controlled preference engine for Search, the AI Assistant and Developer API. It converts functional preferences into deterministic presentation and interaction settings. It does not diagnose users, infer conditions or assess emotional state.

## Package contents

- `src/profile.ts`: typed profile model, safe defaults, normalisation and temporary override resolution.
- `src/profile.ts`: optional `ACCESSIBLE_STARTER_PROFILE` preset covering larger text and controls, high contrast, read-aloud, plain language, Calm Mode, voice-navigation preference, reading assistance and saved progress.\n- `apps/web/components/AccessibilityProvider.tsx`: global preference context, local-only storage, optional account sync and design-token application.
- `schemas/accessibility-profile.schema.json`: JSON Schema contract for API and persistence validation.
- `tests/profile.test.ts`: framework-neutral test cases to port into the repository's configured test runner.

## Starter preset behaviour

The preset is opt-in; it does not change defaults for every ORIOM7 user. It selects a 1.25 text scale, larger targets, high contrast, speech output, plain-language answers, a reading guide, spoken-text highlighting, Calm Mode, reduced motion, step-by-step presentation and save-progress preference.

Voice navigation is a preference only. The preset deliberately leaves microphone input disabled. The application must obtain explicit microphone permission separately, show when listening is active, and provide cancel and non-voice alternatives.

## Integration sequence

1. Validate profile input at the API boundary using the JSON Schema.
2. Load an account profile only after authentication and authorisation; otherwise use local/session preferences or defaults.
3. Resolve temporary session overrides over saved preferences without writing them back.
4. Pass the resolved profile to UI presentation adapters and answer-formatting adapters.
5. Keep search ranking, source selection, factual content and safety policy independent of accessibility preferences.
6. Return accessible output metadata (for example, structured headings, transcript availability and text alternatives) without removing the canonical answer or citations.

## Proposed API

- `GET /v1/accessibility/profile` — return the caller's profile or defaults.
- `PUT /v1/accessibility/profile` — validate and replace the caller's profile.
- `DELETE /v1/accessibility/profile` — delete the saved profile and return to defaults.
- `POST /v1/accessibility/resolve` — resolve a profile with temporary overrides for the current session.

All profile endpoints require normal API authentication and ownership checks. Do not accept a user ID from the request body as authority to read or modify another person's profile.

## Data and privacy rules

- Store functional settings only; never require diagnostic labels.
- Do not infer settings from search history, voice, typing, reading speed or interaction patterns.
- Keep profile sync optional. Support local-only use where practical.
- Treat voice and image capture as separate, explicit permissions; preferences do not grant capture consent.
- Provide reset and deletion. Avoid using profile data for advertising, eligibility or ranking.
- Temporary overrides are ephemeral and must not mutate the saved profile.

## Accessibility and quality guardrails

- A preference changes presentation or interaction, not the truth, completeness or evidential basis of a result.
- Plain-language summaries must retain uncertainty, warnings and source references.
- Every essential action must remain available through an accessible alternative.
- Respect operating-system and browser accessibility settings; do not override them unexpectedly.
- Test with disabled users and assistive technologies. Automated checks alone do not establish conformance.

## Standards

ORIOM7 targets WCAG 2.2 Level AA for web experiences. WCAG 2.2 is the W3C Recommendation; conformance must be assessed against the full success criteria, not inferred from the presence of this package. See https://www.w3.org/TR/WCAG22/.

## Current limitation

The shared profile resolver, Next.js provider and preference interface are integrated. This does not mean ORIOM7 has completed production authentication, full voice services, switch-device support or an independent accessibility audit.
