import { expect, test } from "@playwright/test";

test("end-user chat: connect, see a ready document, ask, and open the cited source on a narrow screen", async ({ page }) => {
  const collectionId = "11111111-1111-1111-1111-111111111111";
  const documentId = "22222222-2222-2222-2222-222222222222";
  const versionId = "44444444-4444-4444-4444-444444444444";

  await page.route("http://localhost:8000/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === "/v1/collections" && request.method() === "GET") {
      await route.fulfill({ json: [{ collection_id: collectionId, name: "HR policies", status: "ACTIVE" }] });
      return;
    }
    if (url.pathname === `/v1/collections/${collectionId}/documents`) {
      await route.fulfill({
        json: [{ document_id: documentId, logical_name: "acme-hr-policy.pdf", status: "READY" }],
      });
      return;
    }
    if (url.pathname === `/v1/collections/${collectionId}/query`) {
      await route.fulfill({
        json: {
          request_id: "33333333-3333-3333-3333-333333333333",
          status: "ANSWERED",
          answer: "Full-time employees receive 24 days of paid annual leave per calendar year.",
          citations: [
            { document_id: documentId, document_version_id: versionId, document_name: "acme-hr-policy.pdf", page_start: 1, page_end: 1 },
          ],
          reason: null,
          generation_backend: "heuristic",
          trace: {
            correlation_id: "corr-chat",
            stages: [],
            evidence: [
              {
                id: "E1",
                document_id: documentId,
                document_version_id: versionId,
                document_name: "acme-hr-policy.pdf",
                page_start: 1,
                page_end: 1,
                text: "Full-time employees receive 24 days of paid annual leave per calendar year.",
                truncated: false,
              },
            ],
          },
        },
      });
      return;
    }
    if (url.pathname === `/v1/documents/${documentId}/content`) {
      await route.fulfill({ contentType: "application/pdf", body: "%PDF-1.4\n%%EOF\n" });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: "not mocked" } });
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/chat");
  await page.getByLabel("Access key").fill("replace-me");
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page.getByRole("button", { name: "Documents (1 ready)" })).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`/chat/${collectionId}$`));

  await page.getByLabel("Your question").fill("How many days of annual leave?");
  await page.getByLabel("Your question").press("Enter");
  const conversation = page.getByRole("region", { name: "Conversation" });
  await expect(conversation.getByText("Full-time employees receive 24 days")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

  await conversation.getByRole("button", { name: "Source 1: acme-hr-policy.pdf, page 1" }).click();
  const viewer = page.getByRole("complementary", { name: "Source viewer" });
  await expect(viewer.getByRole("region", { name: "Quoted passage" })).toContainText("24 days of paid annual leave");
  await expect(viewer.getByRole("link", { name: "Open PDF in a new tab" })).toBeVisible();
  await page.screenshot({ path: "test-results/ui-09-chat-narrow.png", fullPage: true });
});
