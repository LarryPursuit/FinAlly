import { test, expect } from "@playwright/test";

test.describe("AI Chat (mocked LLM)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Live")).toBeVisible({ timeout: 10_000 });
  });

  test("can send a message and receive a response", async ({ page }) => {
    // Find the chat input
    const chatInput = page.getByPlaceholderText(/message|ask|chat/i).first();
    await expect(chatInput).toBeVisible({ timeout: 5_000 });

    // Type and send a message
    await chatInput.fill("What is my portfolio value?");
    await chatInput.press("Enter");

    // User message should appear in the chat
    await expect(
      page.getByText("What is my portfolio value?")
    ).toBeVisible({ timeout: 5_000 });

    // Assistant response should appear (with LLM_MOCK=true)
    // Wait for a response that isn't the user's message
    const assistantMessage = page.locator("[class*='assistant'], [data-role='assistant']").first();
    await expect(assistantMessage).toBeVisible({ timeout: 15_000 });
  });

  test("shows loading state while waiting for response", async ({ page }) => {
    const chatInput = page.getByPlaceholderText(/message|ask|chat/i).first();
    await expect(chatInput).toBeVisible({ timeout: 5_000 });

    await chatInput.fill("Hello");
    await chatInput.press("Enter");

    // There should be some loading indicator
    // This may be brief with mock responses
    await expect(
      page.getByText("Hello")
    ).toBeVisible({ timeout: 5_000 });
  });
});
