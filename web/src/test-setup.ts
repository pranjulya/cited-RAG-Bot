import "@testing-library/jest-dom/vitest";

afterEach(() => {
  sessionStorage.clear();
  localStorage.clear();
  window.history.replaceState({}, "", "/");
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});
