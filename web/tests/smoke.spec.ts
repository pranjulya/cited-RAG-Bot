import { expect, test } from "@playwright/test";

test("connects, opens a collection, and renders a grounded query on a narrow screen", async ({ page }) => {
  const collectionId = "11111111-1111-1111-1111-111111111111";

  await page.route("http://localhost:8000/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === "/health" || url.pathname === "/ready") {
      await route.fulfill({ json: { status: "ok" } });
      return;
    }
    if (url.pathname === "/v1/collections" && request.method() === "GET") {
      await route.fulfill({ json: [] });
      return;
    }
    if (url.pathname === "/v1/collections" && request.method() === "POST") {
      await route.fulfill({ status: 201, json: { collection_id: collectionId, name: "Acme HR", status: "ACTIVE" } });
      return;
    }
    if (url.pathname === `/v1/collections/${collectionId}/documents`) {
      await route.fulfill({ json: [] });
      return;
    }
    if (url.pathname === `/v1/collections/${collectionId}/query`) {
      await route.fulfill({
        json: {
          request_id: "33333333-3333-3333-3333-333333333333",
          status: "ANSWERED",
          answer: "Employees receive 20 days of leave.",
          citations: [],
          reason: null,
          generation_backend: "heuristic",
          trace: {
            correlation_id: "corr-smoke",
            stages: [{ name: "query.generation", duration_ms: 2, status: "ok" }],
            evidence: [],
          },
        },
      });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: "not mocked" } });
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByLabel("API key").fill("replace-me");
  await page.getByRole("button", { name: "Connect" }).click();
  await expect(page.getByLabel("API status")).toBeVisible();

  await page.getByLabel("Collection name").fill("Acme HR");
  await page.getByRole("button", { name: "Create collection" }).click();
  await page.getByRole("link", { name: "Acme HR" }).click();
  await expect(page.getByRole("heading", { name: "Acme HR" })).toBeVisible();

  await page.getByLabel("Question").fill("How much leave?");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByRole("heading", { name: "Answer" })).toBeVisible();
  await expect(page.getByText("Employees receive 20 days of leave.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Trace" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/ui-08-ask-narrow.png", fullPage: true });
});
