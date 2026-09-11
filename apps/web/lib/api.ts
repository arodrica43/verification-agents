export function getApiUrl(): string {
  // Always same-origin: Next.js rewrites /platform-api/* → the real API.
  // Avoids Windows localhost↔IPv6 issues and SSR/client hydration mismatches.
  return "/platform-api";
}

export class ApiError extends Error {
  status?: number;
  body?: unknown;

  constructor(message: string, status?: number, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = `${getApiUrl()}${path.startsWith("/") ? path : `/${path}`}`;
  const headers: Record<string, string> = {
    Accept: "application/json",
    "X-Principal-Id": process.env.NEXT_PUBLIC_PRINCIPAL_ID ?? "dev-user",
    ...(init?.body ? { "Content-Type": "application/json" } : {}),
    ...(init?.headers as Record<string, string> | undefined),
  };
  const apiKey = process.env.NEXT_PUBLIC_API_KEY;
  if (apiKey) {
    headers.Authorization = `Bearer ${apiKey}`;
  }
  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers,
      signal: init?.signal ?? AbortSignal.timeout(15_000),
    });
  } catch (err) {
    const detail =
      err instanceof Error && err.name === "TimeoutError"
        ? "timed out"
        : "unreachable";
    throw new ApiError(
      `Cannot reach API at ${getApiUrl()} (${detail}). Is the Formal Platform API running?`,
    );
  }

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    const detail =
      typeof data === "object" &&
      data !== null &&
      "detail" in data &&
      (data as { detail: unknown }).detail !== undefined
        ? JSON.stringify((data as { detail: unknown }).detail)
        : response.statusText;
    throw new ApiError(
      `API ${response.status}: ${detail}`,
      response.status,
      data,
    );
  }

  return data as T;
}
