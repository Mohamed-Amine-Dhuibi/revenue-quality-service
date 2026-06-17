import type { AnalyseResponse } from "./types";

export const DEFAULT_API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";

export interface AnalyseParams {
  apiBase: string;
  apiKey: string;
  file: File;
  borrowerName?: string;
}

export async function analyse({
  apiBase,
  apiKey,
  file,
  borrowerName,
}: AnalyseParams): Promise<AnalyseResponse> {
  const form = new FormData();
  form.append("file", file);
  if (borrowerName?.trim()) form.append("borrower_name", borrowerName.trim());

  let res: Response;
  try {
    res = await fetch(`${apiBase.replace(/\/$/, "")}/analyse`, {
      method: "POST",
      headers: { "X-API-Key": apiKey },
      body: form,
    });
  } catch {
    throw new Error(
      `Could not reach the API at ${apiBase}. Is the backend running and is CORS allowed?`,
    );
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return (await res.json()) as AnalyseResponse;
}
