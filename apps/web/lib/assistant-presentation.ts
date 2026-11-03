export type AssistantPresentation = {
  language: string;
  language_source: "user_preference" | "automatic_detection";
  plain_language: boolean;
  detail_level: "concise" | "balanced" | "detailed";
  short_answer_first: boolean;
  step_by_step: boolean;
  reduced_content_density: boolean;
  preserve_citations: true;
  preserve_uncertainty: true;
  preserve_safety_warnings: true;
  speech_output_requested: boolean;
  speech_rate: number;
  highlight_spoken_text: boolean;
  calm_presentation: boolean;
  provider_execution: "not_connected";
};

export type AssistantPresentationResult = {
  presentation: AssistantPresentation;
  profile_saved: boolean;
  overrides_persisted: false;
  status: "ready_for_orchestrator";
};

export async function getAssistantPresentation(
  overrides: Record<string, unknown> = {},
): Promise<AssistantPresentationResult> {
  const response = await fetch("/api/assistant/presentation", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ overrides }),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(
      response.status === 401
        ? "Sign in to use your saved assistant preferences."
        : "ORIOM7 could not prepare your assistant presentation preferences.",
    );
  }

  return response.json() as Promise<AssistantPresentationResult>;
}
