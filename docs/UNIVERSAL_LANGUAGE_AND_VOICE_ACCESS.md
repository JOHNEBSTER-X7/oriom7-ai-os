# ORIOM7 Universal Language, Voice and Low-Literacy Access

**Product principle:** Knowledge must be accessible regardless of a person's literacy level, spoken language, reading ability, disability, device, connectivity or technical confidence.

**Status:** Core product requirement — approved direction, 3 November 2026.

## 1. Vision

ORIOM7 is not only a multilingual search engine. It must let a person who cannot read or write still ask questions, understand answers, discover useful information and complete supported tasks through natural speech and simple visual interaction.

The experience should work for:
- people who are non-literate or have limited reading confidence;
- people who speak local, regional, minority or under-served languages;
- people who speak a language different from the language used by a website or document;
- people with visual, hearing, motor or cognitive accessibility needs;
- people using low-cost phones, limited data plans or intermittent connectivity.

Do not treat literacy as a proxy for intelligence, education, capability or trustworthiness. Design with communities, not assumptions about them.

## 2. Core capabilities

### 2.1 Voice-first search
- Prominent microphone action that can be used without typing.
- Speech recognition for supported languages and dialects.
- Spoken confirmation of the recognised question when confidence is low.
- Ability to correct a misunderstood phrase by speaking again.
- Search results read aloud in the user's chosen language.
- Hands-free follow-up questions and clear stop/replay controls.

### 2.2 Two-way language bridge
- Detect or let users choose their preferred spoken language.
- Translate the user's question into one or more search languages.
- Search across sources published in different languages.
- Translate retrieved titles, snippets and relevant passages back into the user's preferred language.
- Generate the final explanation in the selected language.
- Offer original-language source text alongside translation.
- Support transliteration where a language is commonly written in multiple scripts.
- Preserve names, dates, measurements, currency and legal/technical terms carefully.

Translation must be bidirectional across the workflow: user speech → recognised text → query translation → multilingual retrieval → evidence translation → answer generation → spoken response.

### 2.3 Spoken explanations and adjustable simplicity
Answers should support:
- spoken playback;
- short, plain-language explanation;
- step-by-step explanation;
- repeat, pause and slower playback;
- visual summaries and simple diagrams where useful;
- a choice to hear more detail or ask a follow-up.

A “simple explanation” must preserve important qualifications and uncertainty. It must not remove safety-critical information or misrepresent the source.

### 2.4 Icon-led, low-text interface
- Large, clearly labelled microphone, speaker, repeat, back and help controls.
- Consistent icons paired with spoken labels.
- One primary action per screen where possible.
- Short sentences and familiar words.
- Visual progress and confirmation instead of text-only instructions.
- Avoid relying on colour alone to communicate meaning.
- Provide an easy route back, cancel and ask for help.

Icons must be tested with users from the intended communities; symbols are not universally understood.

### 2.5 Multimodal input
Where devices and permissions allow, progressively support:
- camera capture of signs, forms, labels and printed material;
- OCR and translation of photographed text;
- image-based questions such as “What is this?”;
- audio input and spoken responses.

Always explain when a camera or microphone is active. Ask permission before capture and provide a clear way to stop.

### 2.6 Low-bandwidth and offline-aware use
- Lightweight interface and compressed audio options.
- Adaptive audio quality and graceful fallback to text.
- Cache language packs and selected help content where licensing and device storage permit.
- Queue non-urgent actions when connectivity returns.
- Make it clear when a result is cached, stale or requires a connection.
- Do not promise full offline AI or web search unless the required models, content and capabilities are actually available offline.

## 3. Example user journey

1. A person opens ORIOM7 and selects their language by listening to spoken language names or choosing a familiar flag/icon plus audio sample. Do not rely on flags alone because languages cross borders.
2. The person taps the large microphone and asks a question in their own words.
3. ORIOM7 transcribes the speech and plays back a short confirmation if needed.
4. The query planner translates and expands the query for relevant languages.
5. Hybrid retrieval searches the ORIOM7 index and permitted external search providers.
6. Results are normalised, deduplicated, ranked and checked for source provenance.
7. The assistant produces a grounded answer in plain language.
8. Text-to-speech reads the answer aloud. The user can say “repeat”, “slower”, “explain more” or ask another question.
9. The interface presents sources and lets the user hear the original passage or its translation.

## 4. Architecture additions

Add a Language and Accessibility Orchestration layer alongside search and model orchestration.

Core components:
- **Locale profile:** preferred spoken language, script, dialect/locale, voice preference, accessibility preferences and consent state.
- **Speech-to-text adapter:** provider-neutral interface for speech recognition.
- **Language identification:** identify likely language and return confidence; ask rather than assume when uncertain.
- **Translation service:** text translation, query expansion, passage translation and back-translation checks where useful.
- **Multilingual retrieval planner:** searches across language-specific indexes and external providers, with locale-aware ranking.
- **Text simplification service:** rewrites for clarity while retaining evidence and material caveats.
- **Text-to-speech adapter:** natural speech output, voice selection, speed and playback controls.
- **Accessibility presentation layer:** voice-first flows, screen-reader semantics, keyboard/switch support and adjustable text.
- **Language evaluation service:** community-reviewed test sets and quality metrics per language and dialect.

All components use provider adapters so ORIOM7 is not tied to one speech, translation or model vendor.

## 5. Data and privacy requirements

- Collect only the audio and language data needed for the requested feature.
- Make recording, retention and model-training policies explicit and obtain appropriate consent.
- Prefer transient audio processing; do not retain raw recordings by default.
- Provide deletion and retention controls for any stored audio or transcripts.
- Protect transcripts as potentially sensitive personal data.
- Never expose one user's voice recordings or transcript to another tenant.
- Redact sensitive data from logs and traces.
- Offer clear disclosure when translation or transcription is performed by a third-party provider.
- Treat speech transcripts, OCR and translated pages as untrusted input; they must not override system policy or tool permissions.

## 6. Quality, safety and trust

Measure quality separately for each supported language, dialect, accent and relevant user group. Do not claim a language is supported merely because a provider lists it.

Evaluation should include:
- word error rate and task-level speech recognition success;
- translation adequacy, meaning preservation and named-entity accuracy;
- retrieval relevance across source and target languages;
- answer groundedness and citation integrity after translation;
- text-to-speech intelligibility and pronunciation;
- task completion by people with varied literacy levels;
- accessibility testing with assistive technologies;
- performance under noisy environments and weak connectivity.

For medical, legal, financial, emergency and other consequential topics:
- preserve warnings, uncertainty and source context;
- show or speak that machine translation may be imperfect;
- encourage confirmation with a qualified human or official source when appropriate;
- never imply that translated output is certified or legally authoritative unless it has actually been certified.

Prioritise language quality through community participation, native-speaker review and transparent feedback. Avoid presenting dialects as incorrect forms of a language.

## 7. Rollout plan

### Phase A — foundation
- Add locale and accessibility preferences to the user profile.
- Establish provider-neutral speech, translation and text-to-speech interfaces.
- Define privacy and consent behaviour.
- Select a small pilot set of languages based on user/community needs and measurable provider quality.

### Phase B — voice search and spoken answers
- Microphone-first query flow.
- Speech transcription with confirmation and correction.
- Spoken answer playback, repeat and speed controls.
- Plain-language answer option.

### Phase C — cross-language search
- Query translation and multilingual retrieval.
- Translate result titles and snippets.
- Preserve original source links and original text.
- Evaluate ranking and citation correctness across languages.

### Phase D — low-literacy and multimodal access
- Icon-led guided journeys and audio onboarding.
- Camera/OCR translation and image questions.
- Accessibility testing with community partners.
- Low-bandwidth improvements and offline-aware caching.

### Phase E — responsible expansion
- Add languages and dialects only after evaluation and user testing.
- Build community review and correction workflows.
- Publish capability limitations and quality indicators by language.

## 8. Initial acceptance criteria

The first meaningful release of this capability should demonstrate that:
1. A user can submit a search question by voice without typing.
2. The user can select a preferred output language.
3. The system can translate a query and retrieve relevant results from at least one other language, where supported.
4. The answer can be read aloud in the selected language.
5. The user can replay, pause and request a simpler explanation.
6. Sources remain visible or otherwise accessible and are not hidden by translation.
7. The user can correct speech recognition errors.
8. Audio consent, retention and deletion behaviour is documented and implemented.
9. Unsupported languages and low-confidence translations are clearly disclosed.
10. Testing includes people with limited literacy, not only fluent technical staff.

## 9. Product commitment

ORIOM7's language and voice capabilities are not a decorative add-on or a late-stage enhancement. They are a core product pillar and must influence interface design, API contracts, retrieval, model routing, privacy, evaluation and the delivery roadmap from the beginning.
