# ORIOM7 Adaptive Accessibility System

**Status:** Core product direction — proposed feature specification, 3 November 2026.

## 1. Purpose

ORIOM7 should adapt how people search, perceive, understand and operate the platform. It should support people with visual, neurological, motor, cognitive, learning, mental-health-related and sensory access needs.

This is an accessibility and information-access product, not a diagnostic, medical or therapeutic service. ORIOM7 must not infer a diagnosis from user behaviour or promise to treat a condition. Users choose the accommodations that help them.

Design principles:
- One platform, multiple accessible ways to use it.
- Preferences are optional, user-controlled, reversible and combinable.
- Do not require a user to disclose a diagnosis.
- Do not reduce search quality or hide functionality in an accessibility mode.
- Provide equivalent ways to perceive and operate essential information.
- Co-design and test with people who use the accommodations.

## 2. Adaptive accessibility profile

Provide an optional profile with user-selectable settings such as:
- text size, font, weight, spacing and line width;
- contrast and colour themes;
- screen reader and speech output preferences;
- voice input and spoken response preferences;
- reading speed and word highlighting;
- reduced motion and reduced sensory stimulation;
- simplified language and information density;
- larger touch targets and alternative input;
- reminders of current task, saved progress and session recovery.

Do not ask “Which condition do you have?” as a prerequisite. Offer settings by functional need and allow multiple settings to be combined. Preferences should work without an account where practical; synchronisation across devices is opt-in.

## 3. Visual and eye-related access

Potential users include people with blindness, low vision, cataracts, glaucoma, macular degeneration, colour-vision deficiencies, photophobia and other visual conditions.

Features:
- text and interface magnification without loss of content or functionality;
- scalable typography, adjustable line height, letter spacing and line width;
- high contrast, user-selectable foreground/background and colour-filter options;
- clear focus indicators and large, well-spaced controls;
- screen-reader semantics and keyboard navigation;
- text-to-speech with pause, replay and adjustable speed;
- reading ruler, focus line or paragraph highlighting as optional aids;
- OCR and spoken descriptions for user-selected images and documents;
- accessible text equivalents for charts, maps, diagrams and image results.

Do not assume one font, theme or colour combination suits every person. Avoid using colour as the only signal. Respect operating-system zoom, contrast and text-size preferences.

## 4. Neurological, nerve and motor-related access

Potential users include people with Parkinson's disease, multiple sclerosis, tremor, peripheral neuropathy, stroke-related impairments, acquired brain injury, motor coordination difficulties and fluctuating fatigue.

Features:
- large touch targets with adequate spacing;
- keyboard, switch-device and assistive input support;
- voice search and voice navigation where supported;
- adjustable interaction timing and optional confirmation before consequential actions;
- undo, cancel and easy error recovery;
- no drag-only interaction or gesture-only controls;
- save-and-resume, draft preservation and session recovery;
- adjustable pace, reduced-motion and simplified interaction paths;
- no unnecessary time limits.

Do not infer a user's motor ability or make voice input mandatory. Every essential action should have another accessible route.

## 5. Cognitive, learning and neurodivergent access

Potential users include people with dyslexia, ADHD, autism, learning disabilities, memory difficulties, dementia and cognitive effects of neurological conditions or brain injury.

Features:
- plain-language explanations with adjustable detail;
- short answer first, with optional deeper explanation;
- structured headings, bullets and one task per step;
- familiar, consistent navigation and control labels;
- text-to-speech with synchronised phrase or word highlighting;
- optional reading ruler, spacing and typography preferences;
- spell-tolerant query input and gentle query suggestions;
- visible progress, context and breadcrumbs;
- saved searches, bookmarks, recent activity and “continue where I left off”;
- no forced memory tests, hidden gestures or unnecessary multi-step forms;
- clear error messages with recovery instructions.

Simplification must preserve essential meaning, uncertainty, safety information and source context. Do not label a user's preferred mode as a disability mode.

## 6. Mental health, stress and emotional wellbeing

Potential users may be experiencing anxiety, depression, PTSD, stress, grief, concentration difficulties or sensory overload.

Features:
- optional Calm Mode with uncluttered layout and fewer competing elements;
- no autoplay, unexpected audio or unnecessary animation;
- user-controlled information density and notification settings;
- clear, predictable navigation and non-pressuring language;
- pause, save and return without losing work;
- optional content preferences and filters, with transparent explanations;
- easy access to reputable support information when users seek it.

ORIOM7 must not diagnose mental health conditions, infer emotional states, claim to provide therapy or make treatment recommendations as a substitute for qualified care. Do not exploit distress to increase engagement. Any crisis-related information must be carefully sourced, region-aware and clearly distinguished from emergency services.

## 7. Photosensitivity, migraine and sensory sensitivity

Features:
- avoid flashing, strobing and rapidly blinking content;
- respect reduced-motion preferences;
- disable autoplay and animated carousels by default where practical;
- provide pause/stop controls for moving media;
- user-controlled sound, speech and notification levels;
- stable layouts and low-distraction presentation;
- offer light, dark and other contrast themes without claiming one is medically suitable.

Do not introduce visual effects that could trigger discomfort. Provide text alternatives to animated or audiovisual information.

## 8. Combined and fluctuating needs

Users can combine any settings. Example combinations:
- screen reader + translated speech + voice search;
- large text + high contrast + reduced motion;
- Calm Mode + plain-language answers + save-and-resume;
- voice navigation + large touch targets + confirmation prompts.

Allow temporary changes without permanently changing the user's profile. Provide a quick way to return to default settings. Do not require a user to identify with a medical category.

## 9. Implementation architecture

Extend the shared accessibility and personalisation layer with:
- **Preference service:** stores only user-selected settings and consent.
- **Accessible design system:** semantic components, responsive typography, contrast, focus, target sizing and reduced motion.
- **Presentation adapters:** text, speech, screen-reader semantics, captions, text alternatives and structured summaries.
- **Interaction adapters:** keyboard, pointer, touch, voice and switch-compatible operation.
- **Content adaptation:** plain language, summaries, stepwise explanations and user-controlled detail.
- **Session continuity:** saved state, drafts, bookmarks and recovery.
- **Safety and provenance:** preserve source references, uncertainty and safety caveats through every transformed format.

The preference service must not store diagnostic labels unless a user explicitly supplies information for a clearly justified feature and gives informed consent. In general, functional preferences are sufficient.

## 10. Standards and evaluation

Target WCAG 2.2 Level AA for web experiences. Use W3C cognitive accessibility guidance (COGA) as supplemental design guidance. Use semantic HTML and native platform accessibility before adding custom ARIA behaviour.

Testing must include:
- automated accessibility checks in CI;
- keyboard-only and switch-access tests;
- screen-reader testing with NVDA, VoiceOver and TalkBack on supported platforms;
- magnification, text resizing, contrast and reduced-motion testing;
- speech, caption and transcript testing;
- usability sessions with people with relevant lived experience;
- testing of combined access needs and mobile devices.

Automated tools cannot prove that a product is accessible. Measure task completion, error recovery, comprehension and user-reported effort with participants who use the relevant accommodations.

## 11. Privacy and ethical safeguards

- Never infer diagnoses from searches, voice, reading speed, navigation or usage patterns.
- Do not use accessibility preferences for advertising, profiling or eligibility decisions.
- Collect the minimum data needed; make synchronisation optional.
- Keep voice and image capture permission-based and transparent.
- Provide deletion and reset controls.
- Do not use sensitive search topics to infer mental-health status.
- Ensure personalisation does not silently remove important warnings or information.
- Provide accessible privacy notices and consent flows.

## 12. Acceptance criteria

1. Users can combine multiple accessibility preferences.
2. Users can change or reset preferences without disclosing a diagnosis.
3. Core search and assistant flows work with keyboard and supported screen readers.
4. Text resizing, zoom and contrast changes do not break the interface.
5. Essential controls work without fine motor gestures.
6. Users can pause, resume, undo and recover from common mistakes.
7. Motion and audio can be controlled and are not forced.
8. Summaries and simplified answers preserve evidence and caveats.
9. Accessibility is evaluated with disabled users and people with relevant lived experience.
10. No diagnosis or emotional state is inferred for personalisation, advertising or ranking.

## 13. Delivery priorities

### MVP foundation
- Semantic design system, keyboard and screen-reader support.
- Text resizing, contrast, focus and reduced-motion support.
- Plain-language answer option, accessible audio controls and save/resume.
- Large touch targets and clear error recovery.

### Next release
- User-selectable accessibility profiles and combinations.
- Reading ruler, synchronised text highlighting and advanced typography controls.
- Voice and switch navigation improvements.
- Calm Mode and adjustable information density.

### Later expansion
- More advanced OCR/image descriptions and multimodal access.
- Additional assistive technology integrations.
- Community-designed features and research into emerging accessibility needs.

## 14. Product rule

A user should not need to explain a diagnosis to use ORIOM7 comfortably. Ask what would make the experience easier, provide the relevant controls, and let the user remain in charge.
