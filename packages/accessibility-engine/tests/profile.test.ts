import {
  ACCESSIBLE_STARTER_PROFILE,
  DEFAULT_ACCESSIBILITY_PROFILE,
  normalizeAccessibilityProfile,
  resolveAccessibilityProfile,
} from "../src/profile";

// Framework-neutral examples: adapt describe/it/expect to the repository test runner.

export function runAccessibilityProfileContractTests(assert: (condition: boolean, message: string) => void) {
  const defaults = normalizeAccessibilityProfile(null);
  assert(defaults.display.textScale === 1, "missing profile returns safe defaults");
  assert(defaults.interaction.showFocus === true, "visible focus is enabled by default");
  assert(defaults.sensory.disableAutoplay === true, "autoplay is disabled by default");
  assert(defaults.content.preserveCitations === true, "citations cannot be disabled");

  const starter = normalizeAccessibilityProfile(ACCESSIBLE_STARTER_PROFILE);
  assert(starter.display.textScale > 1, "starter preset increases text size");
  assert(starter.display.contrast === "high", "starter preset enables high contrast");
  assert(starter.interaction.largeTargets, "starter preset enables larger controls");
  assert(starter.reading.speechOutput, "starter preset enables read-aloud preference");
  assert(starter.reading.plainLanguage, "starter preset enables plain language");
  assert(starter.sensory.calmPresentation, "starter preset enables Calm Mode");
  assert(starter.interaction.voiceNavigation, "starter preset offers voice navigation");
  assert(!starter.interaction.voiceInput, "starter preset does not grant microphone permission");
  assert(starter.display.readingGuide && starter.reading.highlightSpokenText, "reading assistance is enabled");
  assert(starter.interaction.saveProgress, "starter preset remembers progress");

  const bounded = normalizeAccessibilityProfile({
    display: { textScale: 9, lineHeight: 0.1 },
    reading: { speechRate: -2 },
  });
  assert(bounded.display.textScale === 2.5, "text scale is bounded");
  assert(bounded.display.lineHeight === 1.2, "line height is bounded");
  assert(bounded.reading.speechRate === 0.6, "speech rate is bounded");

  const sanitized = normalizeAccessibilityProfile({
    diagnosis: "must-not-be-stored",
    reading: { plainLanguage: true },
  } as unknown);
  assert(!("diagnosis" in sanitized), "unknown and diagnosis fields are discarded");
  assert(sanitized.reading.plainLanguage, "valid functional preference is retained");

  const temporary = resolveAccessibilityProfile(
    DEFAULT_ACCESSIBILITY_PROFILE,
    { display: { textScale: 1.6 }, sensory: { calmPresentation: true } },
  );
  assert(temporary.display.textScale === 1.6, "temporary override is applied");
  assert(DEFAULT_ACCESSIBILITY_PROFILE.display.textScale === 1, "defaults are not mutated");
  assert(temporary.content.preserveCitations === true, "temporary settings cannot remove citations");
}
