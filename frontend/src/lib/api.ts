import type { ApiErrorBody } from "../types";

export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

const API_URL = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = null;
    }
    const err = body?.error;
    throw new ApiError(
      response.status,
      err?.code ?? "INTERNAL",
      err?.message ?? response.statusText,
      err?.details,
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function apiDelete(path: string): Promise<void> {
  return request<void>(path, { method: "DELETE" });
}

export function apiUpload<T>(
  path: string,
  files: File[],
  options: Record<string, unknown>,
): Promise<T> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  form.append("options", JSON.stringify(options));
  return request<T>(path, { method: "POST", body: form });
}

export function apiDownloadUrl(path: string): string {
  return `${API_URL}${path}`;
}