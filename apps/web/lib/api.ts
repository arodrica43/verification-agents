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
  init?: RequestInit & { timeoutMs?: number },
): Promise<T> {
  const url = `${getApiUrl()}${path.startsWith("/") ? path : `/${path}`}`;
  const timeoutMs = init?.timeoutMs ?? 15_000;
  const { timeoutMs: _ignored, ...fetchInit } = init ?? {};
  const headers: Record<string, string> = {
    Accept: "application/json",
    "X-Principal-Id": process.env.NEXT_PUBLIC_PRINCIPAL_ID ?? "dev-user",
    ...(fetchInit.body ? { "Content-Type": "application/json" } : {}),
    ...(fetchInit.headers as Record<string, string> | undefined),
  };
  const apiKey = process.env.NEXT_PUBLIC_API_KEY;
  if (apiKey) {
    headers.Authorization = `Bearer ${apiKey}`;
  }
  let response: Response;
  try {
    response = await fetch(url, {
      ...fetchInit,
      headers,
      signal: fetchInit.signal ?? AbortSignal.timeout(timeoutMs),
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

export async function apiDownload(
  path: string,
  filename: string,
): Promise<void> {
  const url = `${getApiUrl()}${path.startsWith("/") ? path : `/${path}`}`;
  const headers: Record<string, string> = {
    "X-Principal-Id": process.env.NEXT_PUBLIC_PRINCIPAL_ID ?? "dev-user",
  };
  const apiKey = process.env.NEXT_PUBLIC_API_KEY;
  if (apiKey) headers.Authorization = `Bearer ${apiKey}`;
  const response = await fetch(url, {
    headers,
    signal: AbortSignal.timeout(60_000),
  });
  if (!response.ok) {
    throw new ApiError(`Download failed: ${response.status}`, response.status);
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(objectUrl);
}
