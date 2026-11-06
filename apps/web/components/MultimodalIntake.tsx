"use client";

import { useState, type FormEvent } from "react";

type UploadKind = "document" | "audio";

type Props = {
  onTextExtracted: (text: string, source: string) => void;
};

type ExtractionResponse = {
  extracted_text?: string;
  text?: string;
  pages?: number;
  language?: string;
  duration_seconds?: number;
  detail?: string | { message?: string; code?: string };
  error?: string;
};

const DOCUMENT_TYPES = new Set(["application/pdf", "image/png", "image/jpeg", "image/tiff"]);
const AUDIO_TYPES = new Set(["audio/wav", "audio/x-wav", "audio/mpeg", "audio/ogg", "audio/webm", "audio/mp4", "audio/aac"]);
const MAX_DOCUMENT_BYTES = 15 * 1024 * 1024;
const MAX_AUDIO_BYTES = 25 * 1024 * 1024;
const SEARCH_CONTEXT_LIMIT = 1800;

export default function MultimodalIntake({ onTextExtracted }: Props) {
  const [apiKey, setApiKey] = useState("");
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [busy, setBusy] = useState<UploadKind | null>(null);
  const [status, setStatus] = useState("Upload a document, scanned page or audio recording to extract text for your research query.");
  const [preview, setPreview] = useState("");

  async function extract(kind: UploadKind, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = kind === "document" ? documentFile : audioFile;
    if (!file) {
      setStatus(kind === "document" ? "Choose a PDF or image first." : "Choose an audio file first.");
      return;
    }
    if (!apiKey.startsWith("oriom_live_")) {
      setStatus("Enter an ORIOM7 developer API key beginning with oriom_live_.");
      return;
    }
    const allowedTypes = kind === "document" ? DOCUMENT_TYPES : AUDIO_TYPES;
    const maxBytes = kind === "document" ? MAX_DOCUMENT_BYTES : MAX_AUDIO_BYTES;
    if (!allowedTypes.has(file.type)) {
      setStatus(kind === "document"
        ? "Supported document types are PDF, PNG, JPEG and TIFF."
        : "Use a supported WAV, MP3, OGG, WebM, MP4 or AAC audio file.");
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
      const response = await fetch(`/api/intelligence/${endpoint}`, {
        method: "POST",
        credentials: "same-origin",
        headers: { Authorization: `Bearer ${apiKey}` },
        body: form,
        cache: "no-store",
      });
      const payload = await response.json().catch(() => ({})) as ExtractionResponse;
      if (!response.ok) {
        const detail = typeof payload.detail === "string"
          ? payload.detail
          : payload.detail && typeof payload.detail === "object"
            ? payload.detail.message || payload.detail.code
            : payload.error;
        throw new Error(detail || `Extraction failed (${response.status}).`);
      }

      const extracted = (kind === "document" ? payload.extracted_text : payload.text)?.trim();
      if (!extracted) throw new Error("The provider returned no extractable text.");
      const excerpt = extracted.slice(0, SEARCH_CONTEXT_LIMIT);
      setPreview(excerpt);
      onTextExtracted(excerpt, kind === "document" ? "Document extract" : "Audio transcript");
      const truncation = extracted.length > SEARCH_CONTEXT_LIMIT
        ? ` The first ${SEARCH_CONTEXT_LIMIT} characters were added to your research query; edit them before searching.`
        : " The extracted text has been added to your research query.";
      const detail = kind === "document"
        ? ` ${payload.pages ?? "Unknown"} page(s).`
        : payload.language ? ` Detected language: ${payload.language}.` : "";
      setStatus(`Text extraction completed.${detail}${truncation} The uploaded file is not stored by ORIOM7's extraction endpoint.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "The extraction request could not be completed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="multimodal-intake" aria-labelledby="multimodal-intake-title">
      <div className="workspace-section-heading">
        <div>
          <p className="eyebrow">MULTIMODAL INPUT · V1</p>
          <h3 id="multimodal-intake-title">Search with documents and audio</h3>
        </div>
      </div>
      <p className="muted">Extract text from PDFs, scanned pages, images and audio recordings, then use that text as your research question. Image support here is OCR (reading text in an image), not visual object recognition.</p>

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
          <button className="secondary-button" type="submit" disabled={busy !== null || !documentFile}>
            {busy === "document" ? "Extracting…" : "Extract document text"}
          </button>
        </form>

        <form className="multimodal-upload-card" onSubmit={event => void extract("audio", event)}>
          <h4>Audio recording</h4>
          <label htmlFor="multimodal-audio">Choose WAV, MP3, OGG, WebM, MP4 or AAC</label>
          <input id="multimodal-audio" type="file" accept=".wav,.mp3,.ogg,.webm,.mp4,.m4a,.aac,audio/*"
            onChange={event => setAudioFile(event.target.files?.[0] || null)} />
          <p className="muted">{audioFile ? audioFile.name : "Maximum file size: 25 MB"}</p>
          <button className="secondary-button" type="submit" disabled={busy !== null || !audioFile}>
            {busy === "audio" ? "Transcribing…" : "Transcribe audio"}
          </button>
        </form>
      </div>

      <p className="status" role="status" aria-live="polite">{status}</p>
      {preview && <details className="multimodal-preview" open>
        <summary>Review extracted text before searching</summary>
        <p>{preview}</p>
      </details>}
      <p className="note">OCR and transcription require a configured ORIOM7 provider and a developer API key with access. Uploaded files are processed by the configured provider; review that provider's privacy, retention and data-residency terms before sending sensitive material.</p>
    </section>
  );
}
