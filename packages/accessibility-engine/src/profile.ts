/**
 * ORIOM7 Adaptive Accessibility Engine — profile resolver.
 *
 * Functional preferences only. No diagnosis fields and no inference.
 * Temporary overrides are resolved in memory and are never persisted here.
 */

export type DetailLevel = "concise" | "balanced" | "detailed";
export type Theme = "system" | "light" | "dark" | "warm";
export type Contrast = "system" | "standard" | "high" | "more";
export type FontFamily = "system" | "sans" | "serif" | "dyslexia_friendly";
export type FontWeight = "normal" | "medium" | "bold";

export interface AccessibilityProfile {
  version: 1;
  display: {
    textScale: number;
    fontFamily: FontFamily;
    fontWeight: FontWeight;
    lineHeight: number;
    letterSpacing: number;
    contrast: Contrast;
    theme: Theme;
    readingGuide: boolean;
  };
  reading: {
    speechOutput: boolean;
    speechRate: number;
    highlightSpokenText: boolean;
    plainLanguage: boolean;
    detailLevel: DetailLevel;
    preferredLanguage?: string;
  };
  interaction: {
    voiceInput: boolean;
    voiceNavigation: boolean;
    largeTargets: boolean;
    keyboardFirst: boolean;
    showFocus: boolean;
    confirmDestructiveActions: boolean;
    saveProgress: boolean;
  };
  content: {
    reduceClutter: boolean;
    stepByStep: boolean;
    showShortAnswerFirst: boolean;
    preserveCitations: true;
  };
  sensory: {
    reduceMotion: boolean;
    disableAutoplay: boolean;
    muteNonessentialAudio: boolean;
    calmPresentation: boolean;
  };
}

export const DEFAULT_ACCESSIBILITY_PROFILE: AccessibilityProfile = {
  version: 1,
  display: {
    textScale: 1,
    fontFamily: "system",
    fontWeight: "normal",
    lineHeight: 1.5,
    letterSpacing: 0,
    contrast: "system",
    theme: "system",
    readingGuide: false,
  },
  reading: {
    speechOutput: false,
    speechRate: 1,
    highlightSpokenText: false,
    plainLanguage: false,
    detailLevel: "balanced",
  },
  interaction: {
    voiceInput: false,
    voiceNavigation: false,
    largeTargets: false,
    keyboardFirst: false,
    showFocus: true,
    confirmDestructiveActions: true,
    saveProgress: false,
  },
  content: {
    reduceClutter: false,
    stepByStep: false,
    showShortAnswerFirst: true,
    preserveCitations: true,
  },
  sensory: {
    reduceMotion: false,
    disableAutoplay: true,
    muteNonessentialAudio: false,
    calmPresentation: false,
  },
};

/**
 * Optional starter preset matching the requested ORIOM7 accessibility set.
 * It is applied only when the user chooses it; it is not the global default.
 * Voice navigation is a saved preference, not microphone consent. The
 * application must request capture permission separately before listening.
 */
export const ACCESSIBLE_STARTER_PROFILE: AccessibilityProfile = {
  version: 1,
  display: {
    textScale: 1.25,
    fontFamily: "system",
    fontWeight: "medium",
    lineHeight: 1.7,
    letterSpacing: 0.02,
    contrast: "high",
    theme: "system",
    readingGuide: true,
  },
  reading: {
    speechOutput: true,
    speechRate: 1,
    highlightSpokenText: true,
    plainLanguage: true,
    detailLevel: "balanced",
  },
  interaction: {
    voiceInput: false,
    voiceNavigation: true,
    largeTargets: true,
    keyboardFirst: false,
    showFocus: true,
    confirmDestructiveActions: true,
    saveProgress: true,
  },
  content: {
    reduceClutter: true,
    stepByStep: true,
    showShortAnswerFirst: true,
    preserveCitations: true,
  },
  sensory: {
    reduceMotion: true,
    disableAutoplay: true,
    muteNonessentialAudio: false,
    calmPresentation: true,
  },
};

type DeepPartial<T> = {
  [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K];
};

export type AccessibilityOverrides = DeepPartial<AccessibilityProfile>;

const oneOf = <T extends string>(value: unknown, allowed: readonly T[], fallback: T): T =>
  typeof value === "string" && allowed.includes(value as T) ? (value as T) : fallback;

const bounded = (value: unknown, min: number, max: number, fallback: number): number =>
  typeof value === "number" && Number.isFinite(value)
    ? Math.min(max, Math.max(min, value))
    : fallback;

const bool = (value: unknown, fallback: boolean): boolean =>
  typeof value === "boolean" ? value : fallback;

/**
 * Validate untrusted input by rebuilding an allow-listed profile.
 * Unknown keys (including diagnosis/health fields) are discarded.
 */
export function normalizeAccessibilityProfile(input: unknown): AccessibilityProfile {
  const root = input && typeof input === "object" ? (input as Record<string, any>) : {};
  const d = root.display && typeof root.display === "object" ? root.display : {};
  const r = root.reading && typeof root.reading === "object" ? root.reading : {};
  const i = root.interaction && typeof root.interaction === "object" ? root.interaction : {};
  const c = root.content && typeof root.content === "object" ? root.content : {};
  const s = root.sensory && typeof root.sensory === "object" ? root.sensory : {};
  const defaults = DEFAULT_ACCESSIBILITY_PROFILE;

  const language =
    typeof r.preferredLanguage === "string" &&
    r.preferredLanguage.length >= 2 &&
    r.preferredLanguage.length <= 35
      ? r.preferredLanguage
      : undefined;

  return {
    version: 1,
    display: {
      textScale: bounded(d.textScale, 0.8, 2.5, defaults.display.textScale),
      fontFamily: oneOf(d.fontFamily, ["system", "sans", "serif", "dyslexia_friendly"], defaults.display.fontFamily),
      fontWeight: oneOf(d.fontWeight, ["normal", "medium", "bold"], defaults.display.fontWeight),
      lineHeight: bounded(d.lineHeight, 1.2, 2.2, defaults.display.lineHeight),
      letterSpacing: bounded(d.letterSpacing, 0, 0.12, defaults.display.letterSpacing),
      contrast: oneOf(d.contrast, ["system", "standard", "high", "more"], defaults.display.contrast),
      theme: oneOf(d.theme, ["system", "light", "dark", "warm"], defaults.display.theme),
      readingGuide: bool(d.readingGuide, defaults.display.readingGuide),
    },
    reading: {
      speechOutput: bool(r.speechOutput, defaults.reading.speechOutput),
      speechRate: bounded(r.speechRate, 0.6, 1.8, defaults.reading.speechRate),
      highlightSpokenText: bool(r.highlightSpokenText, defaults.reading.highlightSpokenText),
      plainLanguage: bool(r.plainLanguage, defaults.reading.plainLanguage),
      detailLevel: oneOf(r.detailLevel, ["concise", "balanced", "detailed"], defaults.reading.detailLevel),
      ...(language ? { preferredLanguage: language } : {}),
    },
    interaction: {
      voiceInput: bool(i.voiceInput, defaults.interaction.voiceInput),
      voiceNavigation: bool(i.voiceNavigation, defaults.interaction.voiceNavigation),
      largeTargets: bool(i.largeTargets, defaults.interaction.largeTargets),
      keyboardFirst: bool(i.keyboardFirst, defaults.interaction.keyboardFirst),
      showFocus: bool(i.showFocus, defaults.interaction.showFocus),
      confirmDestructiveActions: bool(i.confirmDestructiveActions, defaults.interaction.confirmDestructiveActions),
      saveProgress: bool(i.saveProgress, defaults.interaction.saveProgress),
    },
    content: {
      reduceClutter: bool(c.reduceClutter, defaults.content.reduceClutter),
      stepByStep: bool(c.stepByStep, defaults.content.stepByStep),
      showShortAnswerFirst: bool(c.showShortAnswerFirst, defaults.content.showShortAnswerFirst),
      preserveCitations: true,
    },
    sensory: {
      reduceMotion: bool(s.reduceMotion, defaults.sensory.reduceMotion),
      disableAutoplay: bool(s.disableAutoplay, defaults.sensory.disableAutoplay),
      muteNonessentialAudio: bool(s.muteNonessentialAudio, defaults.sensory.muteNonessentialAudio),
      calmPresentation: bool(s.calmPresentation, defaults.sensory.calmPresentation),
    },
  };
}

/**
 * Resolve saved preferences plus session-only overrides.
 * The returned profile is a new object; neither input is mutated.
 */
export function resolveAccessibilityProfile(
  saved: unknown,
  temporary: AccessibilityOverrides = {},
): AccessibilityProfile {
  const base = normalizeAccessibilityProfile(saved);
  const merged = {
    ...base,
    display: { ...base.display, ...(temporary.display ?? {}) },
    reading: { ...base.reading, ...(temporary.reading ?? {}) },
    interaction: { ...base.interaction, ...(temporary.interaction ?? {}) },
    content: { ...base.content, ...(temporary.content ?? {}), preserveCitations: true },
    sensory: { ...base.sensory, ...(temporary.sensory ?? {}) },
  };
  return normalizeAccessibilityProfile(merged);
}
