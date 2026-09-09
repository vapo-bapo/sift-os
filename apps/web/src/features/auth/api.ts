import type { MeResponse } from "./types";

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
    this.name = "ApiClientError";
  }

  static async fromResponse(response: Response): Promise<ApiClientError> {
    let message = response.statusText || "Request failed";
    let code: string | undefined;
    try {
      const body = await response.json() as { error?: { message?: string; code?: string } };
      message = body.error?.message ?? message;
      code = body.error?.code;
    } catch {
      // An error response does not have to be JSON for the client to be safe.
    }
    return new ApiClientError(message, response.status, code);
  }
}

function csrfToken(): string | undefined {
  const entry = document.cookie.split("; ").find((value) => value.startsWith("sift_os_csrf="));
  return entry?.split("=").slice(1).join("=");
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const method = init.method ?? "GET";
  const csrf = csrfToken();
  if (csrf && !["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase())) {
    headers.set("X-CSRF-Token", decodeURIComponent(csrf));
  }

  const response = await fetch(`/api${path}`, { ...init, headers, credentials: "include" });
  if (!response.ok) throw await ApiClientError.fromResponse(response);
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}

export function exchangeSso(ticket: string): Promise<void> {
  return apiRequest("/auth/sso/exchange", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticket }),
  });
}

export function getMe(): Promise<MeResponse> {
  return apiRequest<MeResponse>("/me");
}

export function logout(): Promise<void> {
  return apiRequest("/logout", { method: "POST" });
}
