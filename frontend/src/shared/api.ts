/** Infrastructure boundary: HTTP access only, no operational rules. */
export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const response = await fetch(input, { ...init, headers });
  return response;
}
export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await apiFetch(`${API}${path}`, { signal });
  if (!response.ok) throw new Error(`HTTP ${response.status} — ${path}`);
  return response.json() as Promise<T>;
}
export async function apiSend<T>(path: string, method: string, body?: unknown): Promise<T> {
  const response = await apiFetch(`${API}${path}`, {
    method, headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status} — ${path}`);
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}
