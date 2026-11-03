# ORIOM7 Adaptive Accessibility Design System

## Purpose

The global accessibility provider applies user-selected functional preferences consistently across the Next.js application. It is mounted in the root layout, so future Search, Research, Coding, Business, Education and account screens inherit the same settings without creating separate preference implementations.

The profile contains functional choices only. Do not add diagnosis fields, infer a user's condition or require medical disclosure.

## Integration points

- Provider: `apps/web/components/AccessibilityProvider.tsx`
- Settings screen: `apps/web/components/AccessibilitySettings.tsx`
- Shared profile and resolver: `packages/accessibility-engine/src/profile.ts`
- Global styles: `apps/web/app/globals.css`
- API: `services/api/accessibility.py`

Use the shared hook from a client component:

```tsx
"use client";

import { useAccessibility } from "./AccessibilityProvider";

export function ExamplePreferenceAwareControl() {
  const { profile } = useAccessibility();

  return (
    <section aria-label="Search preferences">
      {profile.content.showShortAnswerFirst ? <p>Short answer first</p> : null}
    </section>
  );
}
```

Do not create a second independent accessibility profile state in a feature area. Read the shared profile and use the shared update flow from the settings experience.

## Global presentation tokens

The provider exposes CSS custom properties on `.oriom7-accessibility-root`:

| Token | Meaning |
|---|---|
| `--oriom7-text-scale` | Selected text scale |
| `--oriom7-line-height` | Selected line height |
| `--oriom7-letter-spacing` | Selected letter spacing |
| `--oriom7-font-family` | Selected typeface family |
| `--oriom7-font-weight` | Selected text weight |

The provider also exposes data attributes for theme, contrast, large targets, focus visibility, reduced motion, autoplay preference, Calm Mode, reduced clutter and reading-guide preference. New components should inherit typography and colours rather than hard-code values.

The text-scale preference updates the document root font size so rem-based typography throughout the app scales together. Preserve responsive reflow; do not solve magnification by forcing horizontal scrolling.

## Component requirements

1. Use semantic HTML and native controls wherever possible.
2. Give every input a visible label; group related choices with headings or fieldsets.
3. Preserve a visible keyboard focus indicator. A preference may change its appearance but must not remove focus visibility.
4. Keep essential targets usable without precise pointer movement. Larger-target mode should increase hit areas.
5. Respect reduced motion and never introduce flashing or strobing content.
6. Disable autoplay when the user's preference requests it; provide captions and transcripts for media.
7. Keep all actions available by keyboard and provide alternatives to drag, hover, voice and gesture-only interaction.
8. Announce asynchronous status changes with appropriate live regions without repeatedly interrupting screen readers.
9. Maintain sufficient contrast in every theme and do not communicate state through colour alone.
10. Preserve source citations, uncertainty, safety warnings and essential context when content is simplified.

## Preference versus capability

A saved preference does not itself implement a service or grant permission.

- `speechOutput` records a preference; speech synthesis and playback controls still need to be connected.
- `voiceInput` and `voiceNavigation` record preferences; microphone permission must be requested separately at the point of use, with a clear listening indicator and a non-voice alternative.
- `plainLanguage`, `stepByStep` and `detailLevel` need to be consumed by the Search and Assistant response-formatting layer.
- `readingGuide` is stored, but a dedicated reading-guide interaction remains to be implemented.
- `saveProgress` is a preference; feature-specific resume storage must be designed separately.
- `disableAutoplay` is exposed globally; every future media component must consume it.

Never claim these capabilities are complete until the corresponding adapter and tests are delivered.

## Persistence and privacy

- Browser-local preferences work without an account, subject to browser storage availability.
- Account synchronisation uses the authenticated profile API.
- Do not store audio, transcripts, diagnoses or inferred health information in the preference profile.
- Provide reset and deletion; temporary overrides must not mutate the saved profile.
- Production identity must come from trusted authentication middleware, not client-supplied user identifiers.

## Validation checklist

- Keyboard-only navigation and visible focus.
- NVDA with Firefox/Chrome, VoiceOver with Safari and TalkBack with Android Chrome.
- 200% and 400% zoom with reflow and no loss of functionality.
- Text scaling, high contrast, dark/warm themes and reduced motion combinations.
- Larger targets and touch use.
- Screen-reader announcements for loading, save, error and reset states.
- Local-only mode with no account and account sync after authentication.
- Plain-language output preserving citations and warnings once the response adapter is connected.
- Disabled-user testing and a full WCAG 2.2 AA assessment before making conformance claims.

Automated checks are useful but do not replace assistive-technology testing or evaluation with disabled users.
