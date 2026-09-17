export const API_KEY_STORAGE_KEY = "cited_rag_api_key";

export function getApiKey(): string | null {
  return sessionStorage.getItem(API_KEY_STORAGE_KEY);
}

export function setApiKey(key: string): void {
  sessionStorage.setItem(API_KEY_STORAGE_KEY, key);
}

export function clearApiKey(): void {
  sessionStorage.removeItem(API_KEY_STORAGE_KEY);
}
