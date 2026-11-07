"use client";

import { useState, type FormEvent } from "react";

type UploadKind = "document" | "audio";
type Props = { onTextExtracted: (text: string, source: string) => void };
type ExtractionResponse = {
  extracted_text?: string; text?: string; pages?: number; language?: string;
  detail?: string | { message?: string; code?: string }; error?: string;
};

const DOCUMENT_TYPES = new Set(["application/pdf", "image/png", "image/jpeg", "image/tiff"]);
const AUDIO_TYPES = new Set(["audio/wav", "audio/x-wav", "audio/mpeg", "audio/ogg", "audio/webm", "audio/mp4", "audio/aac"]);
const IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const MAX_DOCUMENT_BYTES = 15 * 1024 * 1024;
const MAX_AUDIO_BYTES = 25 * 1024 * 1024;
const SEARCH_CONTEXT_LIMIT = 1800;

export default function MultimodalIntake({ onTextExtracted }: Props) {
  const [apiKey, setApiKey] = useState("");
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [visualFile, setVisualFile] = useState<File | null>(null);
  const [visualQuestion, setVisualQuestion] = useState("Describe this image and answer any question I ask about it.");
  const [busy, setBusy] = useState<UploadKind | null>(null);
  const [visualBusy, setVisualBusy] = useState(false);
  const [status, setStatus] = useState("Upload a document, scanned page or audio recording to extract text for your research query.");
  const [preview, setPreview] = useState("");

  async function extract(kind: UploadKind, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = kind === "document" ? documentFile : audioFile;
    if (!file) { setStatus(kind === "document" ? "Choose a PDF or image first." : "Choose an audio file first."); return; }
    if (!apiKey.startsWith("oriom_live_")) { setStatus("Enter an ORIOM7 developer API key beginning with oriom_live_."); return; }
    const allowedTypes = kind === "document" ? DOCUMENT_TYPES : AUDIO_TYPES;
    const maxBytes = kind === "document" ? MAX_DOCUMENT_BYTES : MAX_AUDIO_BYTES;
    if (!allowedTypes.has(file.type)) {
      setStatus(kind === "document" ? "Supported document types are PDF, PNG, JPEG and TIFF." : "Use a supported WAV, MP3, OGG, WebM, MP4 or AAC audio file.");
      return;
    }
    if (file.size === 0 || file.size > maxBytes) {
      setStatus(kind === "document" ? "The document must be smaller than 15 MB." : "The audio file must be smaller than 25 MB.");
      return;
    }
    setBusy(kind);
    setStatus(kind === "document" ? "Extracting text from your document…" : "Transcribing your audio…");
    setPreview("");
    const form = new FormData();
    form.append("file", file);
    form.append("language", "auto");
    try {
      const endpoint = kind === "document" ? "documents/ocr" : "speech/transcriptions";
      const response = await fetch("/api/intelligence/" + endpoint, {
        method: "POST", credentials: "same-origin",
        headers: { Authorization: "Bearer " + apiKey }, body: form, cache: "no-store",
      });
      const payload = await response.json().catch(() => ({})) as ExtractionResponse;
      if (!response.ok) {
        const detail = typeof payload.detail === "string" ? payload.detail
          : payload.detail && typeof payload.detail === "object" ? payload.detail.message || payload.detail.code
          : payload.error;
        throw new Error(detail || "Extraction failed (" + response.status + ").");
      }
      const extracted = (kind === "document" ? payload.extracted_text : payload.text)?.trim();
      if (!extracted) throw new Error("The provider returned no extractable text.");
      const excerpt = extracted.slice(0, SEARCH_CONTEXT_LIMIT);
      setPreview(excerpt);
      onTextExtracted(excerpt, kind === "document" ? "Document extract" : "Audio transcript");
      const truncation = extracted.length > SEARCH_CONTEXT_LIMIT
        ? " The first " + SEARCH_CONTEXT_LIMIT + " characters were added to your research query; edit them before searching."
        : " The extracted text has been added to your research query.";
      const detail = kind === "document" ? " " + (payload.pages ?? "Unknown") + " page(s)." : payload.language ? " Detected language: " + payload.language + "." : "";
      setStatus("Text extraction completed." + detail + truncation + " The uploaded file is not stored by ORIOM7's extraction endpoint.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "The extraction request could not be completed.");
    } finally { setBusy(null); }
  }

  async function analyzeVisual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!visualFile) { setStatus("Choose a JPEG, PNG or WebP image first."); return; }
    if (!apiKey.startsWith("oriom_live_")) { setStatus("Enter an ORIOM7 developer API key beginning with oriom_live_."); return; }
    if (!IMAGE_TYPES.has(visualFile.type)) { setStatus("Visual analysis currently supports JPEG, PNG and WebP images."); return; }
    if (visualFile.size === 0 || visualFile.size > 10 * 1024 * 1024) { setStatus("The image must be smaller than 10 MB."); return; }
    if (!visualQuestion.trim() || visualQuestion.length > 2000) { setStatus("Enter a visual question of up to 2,000 characters."); return; }
    setVisualBusy(true);
    setStatus("Analysing image and preparing a description…");
    setPreview("");
    const form = new FormData();
    form.append("file", visualFile);
    form.append("question", visualQuestion.trim());
    try {
      const response = await fetch("/api/intelligence/vision/analyze", {
        method: "POST", credentials: "same-origin",
        headers: { Authorization: "Bearer " + apiKey }, body: form, cache: "no-store",
      });
      const payload = await response.json().catch(() => ({})) as {
        description?: string; answer?: string | null; objects?: string[];
        text_found?: string[]; detail?: string; error?: string;
      };
      if (!response.ok) throw new Error(payload.detail || payload.error || "Visual analysis failed (" + response.status + ").");
      if (!payload.description?.trim()) throw new Error("The visual provider returned no description.");
      const result = [
        "Question: " + visualQuestion.trim(),
        "Image description: " + payload.description,
        payload.answer ? "Answer: " + payload.answer : "",
        payload.objects?.length ? "Visible items: " + payload.objects.join(", ") : "",
        payload.text_found?.length ? "Text detected in image: " + payload.text_found.join(" | ") : "",
      ].filter(Boolean).join("\n\n");
      setPreview(result);
      onTextExtracted(result.slice(0, SEARCH_CONTEXT_LIMIT), "Visual analysis");
      setStatus("Visual analysis completed. Its description has been added to your research query for review. The original image is not stored by ORIOM7's endpoint.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "The visual analysis request could not be completed.");
    } finally { setVisualBusy(false); }
  }

  return (
    <section className="multimodal-intake" aria-labelledby="multimodal-intake-title">
      <div className="workspace-section-heading">
        <div><p className="eyebrow">MULTIMODAL INPUT · V1</p><h3 id="multimodal-intake-title">Search with documents, audio and images</h3></div>
      </div>
      <p className="muted">Extract text from documents and recordings, or ask questions about photographs, charts, diagrams and scenes.</p>
      <div className="multimodal-key-field">
        <label htmlFor="multimodal-api-key">ORIOM7 developer API key</label>
        <input id="multimodal-api-key" type="password" autoComplete="off" value={apiKey}
          onChange={event => setApiKey(event.target.value)} placeholder="oriom_live_…" />
        <small>The key is held in this component's memory and sent to ORIOM7 for authentication. It is not saved in local storage.</small>
      </div>
      <div className="multimodal-upload-grid">
        <form className="multimodal-upload-card" onSubmit={event => void extract("document", event)}>
          <h4>Document or scanned image</h4>
          <label htmlFor="multimodal-document">Choose PDF, PNG, JPEG or TIFF</label>
          <input id="multimodal-document" type="file" accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,application/pdf,image/png,image/jpeg,image/tiff"
            onChange={event => setDocumentFile(event.target.files?.[0] || null)} />
          <p className="muted">{documentFile ? documentFile.name : "Maximum file size: 15 MB"}</p>
          <button className="secondary-button" type="submit" disabled={busy !== null || visualBusy || !documentFile}>{busy === "document" ? "Extracting…" : "Extract document text"}</button>
        </form>
        <form className="multimodal-upload-card" onSubmit={event => void extract("audio", event)}>
          <h4>Audio recording</h4>
          <label htmlFor="multimodal-audio">Choose WAV, MP3, OGG, WebM, MP4 or AAC</label>
          <input id="multimodal-audio" type="file" accept=".wav,.mp3,.ogg,.webm,.mp4,.m4a,.aac,audio/*"
            onChange={event => setAudioFile(event.target.files?.[0] || null)} />
          <p className="muted">{audioFile ? audioFile.name : "Maximum file size: 25 MB"}</p>
          <button className="secondary-button" type="submit" disabled={busy !== null || visualBusy || !audioFile}>{busy === "audio" ? "Transcribing…" : "Transcribe audio"}</button>
        </form>
      </div>
      <form className="multimodal-visual-card" onSubmit={event => void analyzeVisual(event)}>
        <div><h4>Ask a question about an image</h4><p className="muted">Visual understanding for photographs, charts, diagrams and scenes—not only text recognition.</p></div>
        <label htmlFor="multimodal-visual-image">Choose JPEG, PNG or WebP</label>
        <input id="multimodal-visual-image" type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
          onChange={event => setVisualFile(event.target.files?.[0] || null)} />
        <p className="muted">{visualFile ? visualFile.name : "Maximum file size: 10 MB"}</p>
        <label htmlFor="multimodal-visual-question">What would you like to know?</label>
        <textarea id="multimodal-visual-question" rows={3} maxLength={2000} value={visualQuestion}
          onChange={event => setVisualQuestion(event.target.value)} />
        <button className="secondary-button" type="submit" disabled={busy !== null || visualBusy || !visualFile}>{visualBusy ? "Analysing image…" : "Analyse image"}</button>
      </form>
      <p className="status" role="status" aria-live="polite">{status}</p>
      {preview && <details className="multimodal-preview" open><summary>Review extracted or analysed content</summary><p>{preview}</p></details>}
      <p className="note">OCR, transcription and visual analysis require configured providers and a developer API key with access. Uploaded content is forwarded to the configured provider; review its privacy, retention and data-residency terms before sending sensitive material.</p>
    </section>
  );
}
