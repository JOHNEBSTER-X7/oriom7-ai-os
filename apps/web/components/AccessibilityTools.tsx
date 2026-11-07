"use client";

import { useEffect, useRef, useState } from "react";
import { useAccessibility } from "./AccessibilityProvider";

const SAMPLE = "ORIOM7 helps people discover information in the language and format that works best for them. You can change these preferences at any time.";

export default function AccessibilityTools() {
  const { profile } = useAccessibility();
  const [speaking, setSpeaking] = useState(false);
  const [speechMessage, setSpeechMessage] = useState("Read-aloud uses the speech voices available on this device or browser.");
  const [guideY, setGuideY] = useState<number | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    if (!profile.display.readingGuide) {
      setGuideY(null);
      return;
    }

    const onPointer = (event: PointerEvent) => setGuideY(event.clientY);
    const onFocus = (event: FocusEvent) => {
      const target = event.target;
      if (target instanceof HTMLElement) {
        const rect = target.getBoundingClientRect();
        setGuideY(Math.max(0, Math.min(window.innerHeight - 1, rect.top + rect.height / 2)));
      }
    };
    window.addEventListener("pointermove", onPointer, { passive: true });
    document.addEventListener("focusin", onFocus);
    return () => {
      window.removeEventListener("pointermove", onPointer);
      document.removeEventListener("focusin", onFocus);
    };
  }, [profile.display.readingGuide]);

  useEffect(() => () => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }, []);

  function stopSpeaking() {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    utteranceRef.current = null;
    setSpeaking(false);
    setSpeechMessage("Read-aloud stopped.");
  }

  function readSample() {
    if (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") {
      setSpeechMessage("Read-aloud is not supported by this browser. Use your device's built-in screen reader or another supported browser.");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(SAMPLE);
    utterance.rate = profile.reading.speechRate;
    if (profile.reading.preferredLanguage) utterance.lang = profile.reading.preferredLanguage;
    utterance.onstart = () => {
      setSpeaking(true);
      setSpeechMessage("Reading the sample aloud.");
    };
    utterance.onend = () => {
      setSpeaking(false);
      setSpeechMessage("Read-aloud finished.");
      utteranceRef.current = null;
    };
    utterance.onerror = () => {
      setSpeaking(false);
      setSpeechMessage("The device could not play this sample. Check browser audio and speech settings.");
      utteranceRef.current = null;
    };
    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  }

  return (
    <>
      <section className="accessibility-tools" aria-labelledby="accessibility-tools-title">
        <h3 id="accessibility-tools-title">Try your access tools</h3>
        <p>Test spoken output with the speed and language selected above. This sample is spoken locally by your browser; it is not sent to ORIOM7.</p>
        <div className="accessibility-tool-actions">
          <button className="primary-button" type="button" onClick={readSample} disabled={speaking}>Read sample aloud</button>
          <button className="secondary-button" type="button" onClick={stopSpeaking} disabled={!speaking}>Stop speaking</button>
        </div>
        <p className="preview accessibility-speech-sample">{SAMPLE}</p>
        <p className="status" role="status" aria-live="polite">{speechMessage}</p>
        <p className="note">Browser speech availability and voice quality vary by device and language. This preview does not replace full screen-reader support or the ORIOM7 voice assistant.</p>
      </section>
      {profile.display.readingGuide && guideY !== null ? (
        <div className="reading-guide-band" style={{ top: Math.max(0, guideY - 20) }} aria-hidden="true" />
      ) : null}
    </>
  );
}
