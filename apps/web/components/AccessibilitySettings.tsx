"use client";

import { useEffect, useMemo, useState } from "react";\nimport type { CSSProperties } from "react";

type Profile = {
  version: 1;
  display: { textScale: number; fontFamily: string; fontWeight: string; lineHeight: number; letterSpacing: number; contrast: string; theme: string; readingGuide: boolean };
  reading: { speechOutput: boolean; speechRate: number; highlightSpokenText: boolean; plainLanguage: boolean; detailLevel: string; preferredLanguage?: string | null };
  interaction: { voiceInput: boolean; largeTargets: boolean; keyboardFirst: boolean; showFocus: boolean; confirmDestructiveActions: boolean; saveProgress: boolean };
  content: { reduceClutter: boolean; stepByStep: boolean; showShortAnswerFirst: boolean; preserveCitations: true };
  sensory: { reduceMotion: boolean; disableAutoplay: boolean; muteNonessentialAudio: boolean; calmPresentation: boolean };
};

const defaults: Profile = {
  version: 1,
  display: { textScale: 1, fontFamily: "system", fontWeight: "normal", lineHeight: 1.5, letterSpacing: 0, contrast: "system", theme: "system", readingGuide: false },
  reading: { speechOutput: false, speechRate: 1, highlightSpokenText: false, plainLanguage: false, detailLevel: "balanced" },
  interaction: { voiceInput: false, largeTargets: false, keyboardFirst: false, showFocus: true, confirmDestructiveActions: true, saveProgress: false },
  content: { reduceClutter: false, stepByStep: false, showShortAnswerFirst: true, preserveCitations: true },
  sensory: { reduceMotion: false, disableAutoplay: true, muteNonessentialAudio: false, calmPresentation: false },
};

type Status = { message: string; kind: "idle" | "success" | "error" };

export default function AccessibilitySettings() {
  const [profile, setProfile] = useState<Profile>(defaults);
  const [status, setStatus] = useState<Status>({ message: "Loading your settings…", kind: "idle" });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    fetch("/api/accessibility/profile", { credentials: "same-origin" })
      .then(async (response) => {
        if (response.status === 401) throw new Error("Sign in to save a profile. You can still explore these settings in this session.");
        if (!response.ok) throw new Error("Could not load your saved settings.");
        return response.json();
      })
      .then((data) => { if (active) { setProfile(data.profile); setStatus({ message: data.saved ? "Your saved settings are loaded." : "Default settings are active. Sign in to save them across devices.", kind: "idle" }); } })
      .catch((error: Error) => { if (active) setStatus({ message: error.message, kind: "error" }); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const update = <K extends keyof Profile>(section: K, key: keyof Profile[K], value: unknown) => {
    setProfile((current) => ({
      ...current,
      [section]: { ...(current[section] as object), [key]: value },
    }));
  };

  const previewStyle = useMemo(() => ({
    "--preview-scale": String(profile.display.textScale),
    "--preview-line": String(profile.display.lineHeight),
  } as CSSProperties), [profile.display.textScale, profile.display.lineHeight]);

  async function save() {
    setStatus({ message: "Saving settings…", kind: "idle" });
    try {
      const response = await fetch("/api/accessibility/profile", {
        method: "PUT", credentials: "same-origin",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(profile),
      });
      if (response.status === 401) throw new Error("Sign in is required before settings can be saved to your account.");
      if (!response.ok) throw new Error("Settings could not be saved. Check the values and try again.");
      setStatus({ message: "Your accessibility settings have been saved.", kind: "success" });
    } catch (error) {
      setStatus({ message: error instanceof Error ? error.message : "An unexpected error occurred.", kind: "error" });
    }
  }

  async function reset() {
    setProfile(defaults);
    try {
      const response = await fetch("/api/accessibility/profile", { method: "DELETE", credentials: "same-origin" });
      if (response.status === 401) {
        setStatus({ message: "Defaults are active in this session. Sign in to delete a saved account profile.", kind: "idle" });
      } else if (!response.ok) {
        setStatus({ message: "Local settings were reset, but the saved profile could not be deleted.", kind: "error" });
      } else {
        setStatus({ message: "Saved accessibility preferences have been reset to defaults.", kind: "success" });
      }
    } catch {
      setStatus({ message: "Defaults are active in this session. The saved profile could not be reached.", kind: "error" });
    }
  }

  return (
    <section className="settings-card" aria-labelledby="settings-title">
      <div className="section-heading">
        <h2 id="settings-title">Accessibility preferences</h2>
        <p className="muted">Combine any settings. Change them whenever you need.</p>
      </div>
      <div className="settings-grid">
        <div className="setting">
          <label htmlFor="text-scale">Text size: {Math.round(profile.display.textScale * 100)}%</label>
          <input id="text-scale" type="range" min="0.8" max="2.5" step="0.1" value={profile.display.textScale} onChange={(e) => update("display", "textScale", Number(e.target.value))} />
        </div>
        <div className="setting">
          <label htmlFor="line-height">Line spacing</label>
          <input id="line-height" type="range" min="1.2" max="2.2" step="0.1" value={profile.display.lineHeight} onChange={(e) => update("display", "lineHeight", Number(e.target.value))} />
        </div>
        <div className="setting">
          <label htmlFor="contrast">Contrast</label>
          <select id="contrast" value={profile.display.contrast} onChange={(e) => update("display", "contrast", e.target.value)}>
            <option value="system">Use device setting</option><option value="standard">Standard</option><option value="high">High contrast</option><option value="more">More contrast</option>
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
            <option value="system">System default</option><option value="sans">Sans serif</option><option value="serif">Serif</option><option value="dyslexia_friendly">Alternative readable style</option>
          </select>
        </div>
        <div className="setting">
          <label htmlFor="detail">Answer detail</label>
          <select id="detail" value={profile.reading.detailLevel} onChange={(e) => update("reading", "detailLevel", e.target.value)}>
            <option value="concise">Concise</option><option value="balanced">Balanced</option><option value="detailed">Detailed</option>
          </select>
        </div>
        {([
          ["reading", "plainLanguage", "Use plain language"],
          ["reading", "speechOutput", "Offer spoken answers"],
          ["reading", "highlightSpokenText", "Highlight text while spoken"],
          ["interaction", "voiceInput", "Enable voice input preference"],
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
          ["display", "readingGuide", "Show a reading guide"],
        ] as const).map(([section, key, label]) => {
          const checked = Boolean((profile[section] as Record<string, unknown>)[key]);
          return (
            <label className="checkbox-row" key={section + key}>
              <input type="checkbox" checked={checked} onChange={(e) => update(section, key as never, e.target.checked)} />
              <span>{label}</span>
            </label>
          );
        })}
      </div>
      <div className="preview" style={previewStyle}>
        <strong>Reading preview</strong>
        <p className="preview-text">ORIOM7 can present information in a way that is easier for you to read. Your settings can be combined and changed at any time.</p>
      </div>
      <div className="actions">
        <button className="primary-button" type="button" onClick={save} disabled={loading}>Save preferences</button>
        <button className="secondary-button" type="button" onClick={reset}>Reset to defaults</button>
      </div>
      <p className="status" role="status" aria-live="polite" data-kind={status.kind}>{status.message}</p>
      <p className="note">ORIOM7 does not need to know your diagnosis. Voice input and spoken output are separate preferences; microphone permission is requested separately when voice input is actually used.</p>
    </section>
  );
}
