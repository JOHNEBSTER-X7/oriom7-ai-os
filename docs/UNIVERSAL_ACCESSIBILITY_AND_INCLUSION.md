# ORIOM7 Universal Accessibility and Assistive Experience

**Status:** Core product requirement — approved direction, 3 November 2026.

## 1. Product commitment

ORIOM7 must be usable by people with blindness, low vision, deafness, hearing loss, motor disabilities, cognitive disabilities, limited literacy and limited digital confidence. No user should be excluded from the core search and assistant experience because of a disability.

The platform must support different ways to perceive, understand and operate the same functionality. Accessibility is an architectural and product requirement, not a visual theme or optional add-on.

## 2. Blind and low-vision experience

### 2.1 Screen-reader-first interaction
- Semantic HTML landmarks, headings, buttons, forms, lists and status messages.
- Correct accessible names, roles, states and descriptions for every interactive control.
- Predictable heading hierarchy and meaningful page titles.
- Search results announced as structured results, with title, source, relevance context and available actions.
- Loading, errors, streaming completion and result-count changes announced through appropriate live regions without overwhelming the user.
- Dialogs, menus and popovers manage focus correctly and return focus to the invoking control.
- No controls whose purpose is conveyed only through an image, icon, position or colour.
- Avoid redundant announcements and inaccessible custom widgets; prefer native semantic controls.

### 2.2 Keyboard and alternative navigation
- All features operable without a mouse or touch gesture.
- Logical tab order and visible focus indicator.
- Skip links to main content and search results.
- Keyboard shortcuts are optional, discoverable and remappable; never intercept essential assistive-technology shortcuts.
- No keyboard traps; provide escape and clear navigation paths.
- Support switch devices and other alternative input methods through standard platform semantics.

### 2.3 Voice-first access
- A user can start a search, ask follow-up questions, navigate result summaries, hear answers and request repetition through voice where device/browser capabilities permit.
- Microphone permission is requested only when needed, with a clear explanation and an alternative input route.
- Voice is an additional access route, not a requirement: users must still be able to use screen readers and keyboards without enabling a microphone.
- Provide clear spoken feedback for success, errors, uncertainty and confirmation.

### 2.4 Low-vision presentation
- Responsive text resizing and browser zoom without loss of content or functionality.
- Strong text/background contrast and support for high-contrast modes.
- Do not rely on colour alone.
- Respect reduced-motion preferences; avoid flashing and unnecessary animation.
- Clear spacing, readable typography and adjustable text density.
- Avoid auto-playing audio or moving content that cannot be paused.

### 2.5 Images, charts and visual results
- Meaningful alternative text for informative images; empty alt text for decorative images.
- Charts and visualisations must have an equivalent text summary and accessible data table where appropriate.
- Maps and complex diagrams need a structured textual alternative.
- OCR and image descriptions should be available when users choose to inspect an image, with uncertainty disclosed.
- Never make essential information available only visually.

## 3. Deaf and hard-of-hearing experience

- All audio/video content has captions or a text transcript where applicable.
- Spoken assistant answers are also available as text.
- Voice input has a text alternative.
- Important alerts and confirmations are visual and accessible to assistive technology, not sound-only.
- Consider sign-language support as a research and community partnership area; do not claim automated sign-language translation is reliable without rigorous validation with Deaf communities.

## 4. Cognitive and learning accessibility

- Plain-language mode with short sentences and clear structure.
- Step-by-step explanations and progressive disclosure.
- Consistent navigation and predictable control placement.
- Ability to pause, repeat, review and resume.
- Avoid time pressure, unexplained jargon and unnecessary cognitive load.
- Preserve important warnings, caveats and uncertainty when simplifying content.

## 5. Four Universal ORIOM7 pillars

1. **Universal Search** — discover information across sources and languages.
2. **Universal Intelligence** — understand, explain and help solve problems using evidence.
3. **Universal Access** — use voice, translation, spoken answers and low-literacy interaction.
4. **Universal Accessibility and Inclusion** — provide independent, dignified access for people with disabilities, including blind and low-vision users.

These pillars are one integrated product promise, not separate products.

## 6. Accessibility architecture

Add accessibility requirements across every layer:

- **Design system:** semantic components, accessible tokens, contrast, focus, motion and text scaling.
- **Web experience:** screen-reader semantics, keyboard support, responsive layout and accessible streaming.
- **Assistant orchestration:** concise spoken responses, structured answer summaries, pronunciation-aware output and user-controlled verbosity.
- **Search results:** semantic result structure, source metadata and predictable navigation.
- **Media services:** optional speech recognition and text-to-speech with accessible controls.
- **Language services:** selected language and locale, preserving meaning and source attribution.
- **Evaluation:** automated checks plus manual assistive-technology and disabled-user testing.

Do not create separate, inferior “disabled” search results. Accessibility should expose the same search, assistant and developer capabilities through appropriate interaction modes.

## 7. Standards and implementation baseline

Use WCAG 2.2 Level AA as the target for the web product, with relevant WAI-ARIA Authoring Practices and platform accessibility guidance. Apply semantic HTML first; ARIA supplements native semantics rather than replacing them.

Test with:
- keyboard-only navigation;
- screen readers on supported desktop and mobile platforms (for example, NVDA, VoiceOver and TalkBack);
- browser zoom and text resizing;
- high contrast and reduced motion;
- automated accessibility checks in CI;
- manual usability sessions with blind and low-vision participants and people with other access needs.

Automated scanners are useful but cannot establish full accessibility or replace testing with disabled users.

## 8. Privacy, consent and dignity

- Do not infer or require a diagnosis to provide accessible controls.
- Accessibility preferences are optional and user-controlled.
- Store only preferences necessary to provide the experience.
- Ask permission before microphone or camera use.
- Explain any third-party processing of speech, images or documents.
- Never assume a person wants audio, simplified language or a particular navigation mode; allow preferences to be changed at any time.
- Avoid patronising language and preserve user agency.

## 9. Acceptance criteria

A release is not accessibility-ready unless:
1. Core search and assistant journeys can be completed with a screen reader.
2. Core journeys can be completed using keyboard alone.
3. Search results, source references, streaming status and errors are announced meaningfully.
4. Focus is visible, logical and never trapped.
5. Text can be enlarged and the interface remains usable.
6. Informative images and complex visual outputs have text alternatives.
7. Spoken answers have a text equivalent and audio is controllable.
8. Captions or transcripts exist for relevant audio/video content.
9. Colour, sound or visual position is never the only means of conveying essential information.
10. Disabled users participate in usability testing and prioritisation.

## 10. Rollout

### Foundation
- Audit the initial design system and web shell against WCAG 2.2 AA.
- Build semantic controls, keyboard navigation, focus management and screen-reader announcements into shared components.
- Include accessibility checks in CI.

### Accessible MVP
- Complete keyboard and screen-reader support for search, assistant and source navigation.
- Ensure streaming responses and errors are announced.
- Provide text equivalents for all spoken output and accessible playback controls.

### Expanded inclusion
- Add low-vision preferences, high contrast, reduced motion and adjustable text density.
- Improve voice navigation and image/OCR assistance.
- Conduct paid usability research with disabled participants.
- Publish known limitations and a feedback channel.

## 11. Product rule

A feature is not complete merely because it works for a sighted mouse-and-keyboard user. It must have an accessible interaction path, an equivalent way to perceive its important information, and evidence from testing with people who use assistive technologies.
