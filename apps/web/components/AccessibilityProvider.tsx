"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from "react";
import {
  ACCESSIBLE_STARTER_PROFILE,
  DEFAULT_ACCESSIBILITY_PROFILE,
  normalizeAccessibilityProfile,
  type AccessibilityProfile,
} from "../../../packages/accessibility-engine/src/profile";

const LOCAL_PROFILE_KEY = "oriom7.accessibility.profile.v1";

type AccessibilityContextValue = {
  profile: AccessibilityProfile;
  setProfile: Dispatch<SetStateAction<AccessibilityProfile>>;
  saveProfile: () => Promise<string>;
  resetProfile: () => Promise<string>;
  applyStarterProfile: () => void;
  ready: boolean;
};

const AccessibilityContext = createContext<AccessibilityContextValue | null>(null);

export function useAccessibility(): AccessibilityContextValue {
  const value = useContext(AccessibilityContext);
  if (!value) throw new Error("useAccessibility must be used within AccessibilityProvider");
  return value;
}

export default function AccessibilityProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<AccessibilityProfile>(DEFAULT_ACCESSIBILITY_PROFILE);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;

    async function hydrate() {
      let localProfile: AccessibilityProfile | null = null;
      try {
        const stored = window.localStorage.getItem(LOCAL_PROFILE_KEY);
        if (stored) localProfile = normalizeAccessibilityProfile(JSON.parse(stored));
      } catch {
        // Private browsing or storage restrictions: continue with defaults.
      }
      if (active && localProfile) setProfile(localProfile);

      try {
        const response = await fetch("/api/accessibility/profile", {
          credentials: "same-origin",
          cache: "no-store",
        });
        if (response.ok) {
          const data = await response.json();
          if (active && data.saved && data.profile) {
            const remote = normalizeAccessibilityProfile(data.profile);
            setProfile(remote);
            try { window.localStorage.setItem(LOCAL_PROFILE_KEY, JSON.stringify(remote)); } catch { /* optional cache */ }
          }
        }
      } catch {
        // Local-only preferences remain usable while the API is unavailable.
      } finally {
        if (active) setReady(true);
      }
    }

    void hydrate();
    return () => { active = false; };
  }, []);

  const saveProfile = useCallback(async () => {
    const canonical = normalizeAccessibilityProfile(profile);
    setProfile(canonical);
    try { window.localStorage.setItem(LOCAL_PROFILE_KEY, JSON.stringify(canonical)); } catch {
      // Continue to account sync; the browser may prohibit local storage.
    }

    try {
      const response = await fetch("/api/accessibility/profile", {
        method: "PUT",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(canonical),
      });
      if (response.ok) return "Preferences saved on this device and to your account.";
      if (response.status === 401) return "Preferences saved on this device only. Sign in to sync them across devices.";
      return "Preferences saved on this device. Account sync is temporarily unavailable.";
    } catch {
      return "Preferences saved on this device. Account sync is temporarily unavailable.";
    }
  }, [profile]);

  const resetProfile = useCallback(async () => {
    setProfile(DEFAULT_ACCESSIBILITY_PROFILE);
    try { window.localStorage.removeItem(LOCAL_PROFILE_KEY); } catch { /* optional cache */ }

    try {
      const response = await fetch("/api/accessibility/profile", {
        method: "DELETE",
        credentials: "same-origin",
      });
      if (response.ok || response.status === 204) return "This device and your saved account profile have been reset.";
      if (response.status === 401) return "This device has been reset. Sign in if you also need to delete a saved account profile.";
      return "This device has been reset. Account reset is temporarily unavailable.";
    } catch {
      return "This device has been reset. Account reset is temporarily unavailable.";
    }
  }, []);

  const applyStarterProfile = useCallback(() => {
    setProfile(normalizeAccessibilityProfile(ACCESSIBLE_STARTER_PROFILE));
  }, []);

  useEffect(() => {
    const originalFontSize = document.documentElement.style.fontSize;
    document.documentElement.style.fontSize = `${profile.display.textScale * 100}%`;
    return () => { document.documentElement.style.fontSize = originalFontSize; };
  }, [profile.display.textScale]);

  const style = useMemo(() => ({
    "--oriom7-text-scale": `${profile.display.textScale}rem`,
    "--oriom7-line-height": String(profile.display.lineHeight),
    "--oriom7-letter-spacing": `${profile.display.letterSpacing}em`,
    "--oriom7-font-family": profile.display.fontFamily === "serif"
      ? "Georgia, serif"
      : profile.display.fontFamily === "dyslexia_friendly"
        ? "Verdana, Arial, sans-serif"
        : profile.display.fontFamily === "sans"
          ? "Arial, Helvetica, sans-serif"
          : "system-ui, sans-serif",
    "--oriom7-font-weight": profile.display.fontWeight === "bold" ? "700" : profile.display.fontWeight === "medium" ? "550" : "400",
  } as CSSProperties), [profile]);

  const value = useMemo(() => ({
    profile, setProfile, saveProfile, resetProfile, applyStarterProfile, ready,
  }), [profile, saveProfile, resetProfile, applyStarterProfile, ready]);

  return (
    <AccessibilityContext.Provider value={value}>
      <div
        className="oriom7-accessibility-root"
        style={style}
        data-theme={profile.display.theme}
        data-contrast={profile.display.contrast}
        data-large-targets={profile.interaction.largeTargets}
        data-show-focus={profile.interaction.showFocus}
        data-reduce-motion={profile.sensory.reduceMotion}
        data-disable-autoplay={profile.sensory.disableAutoplay}
        data-calm={profile.sensory.calmPresentation}
        data-reduce-clutter={profile.content.reduceClutter}
        data-reading-guide={profile.display.readingGuide}
      >
        {children}
      </div>
    </AccessibilityContext.Provider>
  );
}
