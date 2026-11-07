"use client";

import { useState } from "react";
import {
  normalizeAccessibilityProfile,
  type AccessibilityProfile,
} from "../../../packages/accessibility-engine/src/profile";
import { useAccessibility } from "./AccessibilityProvider";
import AccessibilityTools from "./AccessibilityTools";

type Status = { message: string; kind: "idle" | "success" | "error" };

export default function AccessibilitySettings() {
  const { profile, setProfile, saveProfile, resetProfile, applyStarterProfile, ready } = useAccessibility();
  const [status, setStatus] = useState<Status>({ message: "Preferences apply immediately. Save to keep them on this device and sync when signed in.", kind: "idle" });

  function update(section: keyof AccessibilityProfile, key: string, value: unknown) {
    const currentSection = profile[section] as unknown as Record<string, unknown>;
    const next = normalizeAccessibilityProfile({
      ...profile,
      [section]: { ...currentSection, [key]: value },
    });
    setProfile(next);
  }

  async function save() {
    setStatus({ message: "Saving preferences…", kind: "idle" });
    try {
      setStatus({ message: await saveProfile(), kind: "success" });
    } catch {
      setStatus({ message: "Your preferences could not be saved.", kind: "error" });
    }
  }

  async function reset() {
    setStatus({ message: await resetProfile(), kind: "success" });
  }

  const toggles = [
    ["reading", "plainLanguage", "Use plain language"],
    ["reading", "speechOutput", "Offer spoken answers"],
    ["reading", "highlightSpokenText", "Highlight text while spoken"],
    ["interaction", "voiceInput", "Allow voice input when separately authorised"],
    ["interaction", "voiceNavigation", "Offer voice navigation controls"],
    ["interaction", "largeTargets", "Use larger buttons and controls"],
    ["interaction", "keyboardFirst", "Prefer keyboard navigation"],
    ["interaction", "showFocus", "Emphasise keyboard focus"],
    ["interaction", "confirmDestructiveActions", "Confirm destructive actions"],
    ["interaction", "saveProgress", "Offer save and resume"],
    ["content", "reduceClutter", "Reduce visual clutter"],
    ["content", "stepByStep", "Break instructions into steps"],
    ["content", "showShortAnswerFirst", "Show the short answer first"],
    ["sensory", "reduceMotion", "Reduce motion and animation"],
    ["sensory", "disableAutoplay", "Disable autoplay"],
    ["sensory", "muteNonessentialAudio", "Mute non-essential audio"],
    ["sensory", "calmPresentation", "Use a calmer presentation"],
    ["display", "readingGuide", "Enable reading guide preference"],
  ] as const;

  return (
    <section className="settings-card" aria-labelledby="settings-title">
      <div className="section-heading">
        <h2 id="settings-title">Accessibility preferences</h2>
        <p className="muted">Combine any settings. Change them whenever you need. No diagnosis is required.</p>
      </div>

      <div className="settings-grid">
        <div className="setting">
          <label htmlFor="text-scale">Text size: {Math.round(profile.display.textScale * 100)}%</label>
          <input id="text-scale" type="range" min="0.8" max="2.5" step="0.1" value={profile.display.textScale} onChange={(e) => update("display", "textScale", Number(e.target.value))} />
        </div>
        <div className="setting">
          <label htmlFor="line-height">Line spacing: {profile.display.lineHeight.toFixed(1)}</label>
          <input id="line-height" type="range" min="1.2" max="2.2" step="0.1" value={profile.display.lineHeight} onChange={(e) => update("display", "lineHeight", Number(e.target.value))} />
        </div>
        <div className="setting">
          <label htmlFor="letter-spacing">Letter spacing</label>
          <input id="letter-spacing" type="range" min="0" max="0.12" step="0.01" value={profile.display.letterSpacing} onChange={(e) => update("display", "letterSpacing", Number(e.target.value))} />
        </div>
        <div className="setting">
          <label htmlFor="contrast">Contrast</label>
          <select id="contrast" value={profile.display.contrast} onChange={(e) => update("display", "contrast", e.target.value)}>
            <option value="system">Use device setting</option><option value="standard">Standard</option><option value="high">High contrast</option><option value="more">Maximum contrast</option>
          </select>
        </div>
        <div className="setting">
          <label htmlFor="theme">Colour theme</label>
          <select id="theme" value={profile.display.theme} onChange={(e) => update("display", "theme", e.target.value)}>
            <option value="system">Use device setting</option><option value="light">Light</option><option value="dark">Dark</option><option value="warm">Warm</option>
          </select>
        </div>
        <div className="setting">
          <label htmlFor="font">Typeface</label>
          <select id="font" value={profile.display.fontFamily} onChange={(e) => update("display", "fontFamily", e.target.value)}>
            <option value="system">System default</option><option value="sans">Sans serif</option><option value="serif">Serif</option><option value="dyslexia_friendly">Alternative readable sans serif</option>
          </select>
        </div>
        <div className="setting">
          <label htmlFor="font-weight">Text weight</label>
          <select id="font-weight" value={profile.display.fontWeight} onChange={(e) => update("display", "fontWeight", e.target.value)}>
            <option value="normal">Normal</option><option value="medium">Medium</option><option value="bold">Bold</option>
          </select>
        </div>
        <div className="setting">
          <label htmlFor="detail">Answer detail</label>
          <select id="detail" value={profile.reading.detailLevel} onChange={(e) => update("reading", "detailLevel", e.target.value)}>
            <option value="concise">Concise</option><option value="balanced">Balanced</option><option value="detailed">Detailed</option>
          </select>
        </div>
        <div className="setting">
          <label htmlFor="speech-rate">Speech speed: {profile.reading.speechRate.toFixed(1)}×</label>
          <input id="speech-rate" type="range" min="0.6" max="1.8" step="0.1" value={profile.reading.speechRate} onChange={(e) => update("reading", "speechRate", Number(e.target.value))} />
        </div>
        <div className="setting">
          <label htmlFor="preferred-language">Preferred answer language</label>
          <input id="preferred-language" type="text" maxLength={35} placeholder="e.g. en-GB, fr, sw" value={profile.reading.preferredLanguage ?? ""} onChange={(e) => update("reading", "preferredLanguage", e.target.value || undefined)} />
        </div>

        {toggles.map(([section, key, label]) => {
          const checked = Boolean((profile[section] as unknown as Record<string, unknown>)[key]);
          return (
            <label className="checkbox-row" key={section + key}>
              <input type="checkbox" checked={checked} onChange={(e) => update(section, key, e.target.checked)} />
              <span>{label}</span>
            </label>
          );
        })}
      </div>

      <div className="preview" aria-label="Live preview of your reading preferences">
        <strong>Live reading preview</strong>
        <p className="preview-text">ORIOM7 applies your display preferences across this application. Your selected settings can be combined and changed whenever you need.</p>
        <p className="muted">Your source citations and important warnings remain available when content is simplified.</p>
      </div>

      <AccessibilityTools />

      <div className="actions">
        <button className="primary-button" type="button" onClick={save} disabled={!ready}>Save preferences</button>
        <button className="secondary-button" type="button" onClick={applyStarterProfile}>Try accessible starter preset</button>
        <button className="secondary-button" type="button" onClick={reset}>Reset preferences</button>
      </div>
      <p className="status" role="status" aria-live="polite" data-kind={status.kind}>{status.message}</p>
      <p className="note">Local preferences work without an account. Signing in allows account synchronisation. Voice preferences never grant microphone permission; microphone access is requested separately when voice input is used.</p>
    </section>
  );
}
