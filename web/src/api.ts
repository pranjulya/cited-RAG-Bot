import { getApiKey } from "./auth";

export function apiBaseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE_URL as string | undefined;
  return (raw ?? "http://localhost:8000").replace(/\/$/, "");
}

export function apiUrl(path: string): string {
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${apiBaseUrl()}${suffix}`;
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const key = getApiKey();
  if (key) {
    headers.set("Authorization", `Bearer ${key}`);
  }
  return fetch(apiUrl(path), { ...init, headers });
}
