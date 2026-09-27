export type AgentState = { status: string; latest_message: string; elapsed_seconds?: number; error?: string };
export type Evidence = { path: string; start: number; end: number; note?: string };
export type TourStep = { step: number; title: string; path: string; start: number; end: number; narration: string };
export type ArchitectureSummary = { overview: string; modules: string[]; entry_points: string[]; data_flow: string };
export type Plan = { role: string; tour_steps: TourStep[]; architecture_summary: ArchitectureSummary | string; key_concepts: string[]; repo_context?: {repo_url:string; default_branch?:string; languages:string[]; file_count:number} };

const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
if (process.env.NODE_ENV === "production" && !configuredApiUrl) {
  throw new Error("NEXT_PUBLIC_API_URL must be configured for a production frontend build");
}
if (process.env.NODE_ENV === "production" && configuredApiUrl && !/^https:\/\//i.test(configuredApiUrl)) {
  throw new Error("NEXT_PUBLIC_API_URL must use HTTPS in production");
}

export const API_URL = (configuredApiUrl || "http://localhost:8000").replace(/\/$/, "");

export async function apiFetch<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), init?.timeoutMs ?? 30_000);
  try {
    const { timeoutMs: _timeoutMs, ...requestInit } = init || {};
    const headers = new Headers(requestInit.headers || {});
    if (!headers.has("Accept")) headers.set("Accept", "application/json");
    if (requestInit.body !== undefined && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    const res = await fetch(`${API_URL}${path}`, {
      ...requestInit,
      signal: requestInit.signal || controller.signal,
      headers,
      cache: "no-store",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || body.message || `HTTP ${res.status}`);
    }
    return res.json();
  } finally {
    clearTimeout(timeout);
  }
}

export function wsUrl(path: string) {
  const base = API_URL.replace(/^https:/, "wss:").replace(/^http:/, "ws:");
  return `${base}${path}`;
}
