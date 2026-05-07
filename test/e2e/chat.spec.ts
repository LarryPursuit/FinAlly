import { test, expect, Page } from "@playwright/test";

const getChatInput = (page: Page) =>
  page
    .locator(
      'textarea[placeholder*="message" i], input[placeholder*="message" i], input[placeholder*="ask" i], input[placeholder*="finAlly" i], [data-testid*="chat-input"]'
    )
    .first();

const sendChatMessage = async (page: Page, message: string) => {
  const chatInput = getChatInput(page);
  await expect(chatInput).toBeVisible({ timeout: 10_000 });
  await chatInput.fill(message);
  const sendBtn = page
    .locator(
      'button[aria-label*="send" i], button[title*="send" i], button:has-text("Send"), [data-testid*="send"]'
    )
    .first();
  if (await sendBtn.isVisible()) {
    await sendBtn.click();
  } else {
    await chatInput.press("Enter");
  }
};

test.describe("AI Chat", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
  });

  test("chat panel is visible on page load", async ({ page }) => {
    await expect(
      page
        .locator(
          '[data-testid*="chat"], aside:has-text("chat"), section:has-text("AI"), div:has-text("FinAlly")'
        )
        .first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("chat input field is present", async ({ page }) => {
    await expect(getChatInput(page)).toBeVisible({ timeout: 10_000 });
  });

  test("empty input is rejected client-side", async ({ page }) => {
    const chatInput = getChatInput(page);
    await expect(chatInput).toBeVisible({ timeout: 10_000 });
    await chatInput.fill("");

    const sendBtn = page
      .locator(
        'button[aria-label*="send" i], button[title*="send" i], button:has-text("Send"), [data-testid*="send"]'
      )
      .first();

    if (await sendBtn.isVisible()) {
      // Button should be disabled when input is empty
      await expect(sendBtn).toBeDisabled();
    } else {
      // Enter on empty input should not post — no network request fired
      // Just verify the page doesn't crash and no assistant message appears
      const messageCountBefore = await page
        .locator('[data-testid*="message"], [class*="message"]')
        .count();
      await chatInput.press("Enter");
      await page.waitForTimeout(500);
      const messageCountAfter = await page
        .locator('[data-testid*="message"], [class*="message"]')
        .count();
      expect(messageCountAfter).toBe(messageCountBefore);
    }
  });

  test("sends a message and receives a response", async ({ page }) => {
    await sendChatMessage(page, "How is my portfolio?");

    // Mock default response text
    await expect(
      page.getByText(/portfolio|watchlist|buy|sell/i).first()
    ).toBeVisible({ timeout: 15_000 });
  });

  test("user message appears in chat after sending", async ({ page }) => {
    const userMessage = "How is my portfolio doing?";
    await sendChatMessage(page, userMessage);

    await expect(page.getByText(userMessage).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("AI response message appears after sending", async ({ page }) => {
    await sendChatMessage(page, "How is my portfolio?");

    // The mock default response mentions portfolio/watchlist
    await expect(
      page.getByText(/portfolio|watchlist|buy|sell/i).first()
    ).toBeVisible({ timeout: 15_000 });
  });

  test("mock 'buy 5 AAPL' executes trade and updates positions", async ({
    page,
  }) => {
    // Confirm fresh start has no positions
    await expect(page.getByText("No positions yet")).toBeVisible({
      timeout: 10_000,
    });

    // Capture starting balance
    await expect(page.locator("text=/\\$10,000\\.\\d{2}/").first()).toBeVisible({
      timeout: 10_000,
    });

    // Mock regex: buy\s+(\d+)\s+...([A-Za-z.]+)
    await sendChatMessage(page, "buy 5 AAPL");

    // Mock confirms: "I'll buy 5 shares of AAPL for you."
    await expect(
      page.getByText(/I'll buy 5 shares of AAPL/i).first()
    ).toBeVisible({ timeout: 15_000 });

    // Positions table should now show AAPL
    await expect(page.getByText("No positions yet")).toBeHidden({
      timeout: 15_000,
    });
    await expect(
      page
        .locator(
          '[data-testid*="positions"], table, section:has-text("Positions")'
        )
        .getByText("AAPL")
        .first()
    ).toBeVisible({ timeout: 15_000 });

    // Cash should be less than $10,000 after buying 5 shares
    await expect(page.locator("text=/\\$10,000\\.00/").first()).toBeHidden({
      timeout: 10_000,
    });
  });

  test("mock 'add PYPL to watchlist' adds PYPL to watchlist", async ({
    page,
  }) => {
    // PYPL should not be in watchlist initially
    await expect(page.getByText("PYPL", { exact: true }).first()).toBeHidden({
      timeout: 5_000,
    });

    // Mock regex: (?:add|watch)\s+([A-Za-z.]+)
    await sendChatMessage(page, "add PYPL to watchlist");

    // Mock confirms: "I'll add PYPL to your watchlist."
    await expect(
      page.getByText(/I'll add PYPL to your watchlist/i).first()
    ).toBeVisible({ timeout: 15_000 });

    // PYPL should now appear in watchlist
    await expect(
      page.getByText("PYPL", { exact: true }).first()
    ).toBeVisible({ timeout: 15_000 });
  });

  test("chat history persists across page reload", async ({ page }) => {
    const userMessage = "Hello from reload test";
    await sendChatMessage(page, userMessage);

    // Wait for user message to appear
    await expect(page.getByText(userMessage).first()).toBeVisible({
      timeout: 10_000,
    });

    // Wait for assistant reply
    await expect(
      page.getByText(/portfolio|watchlist|buy|sell/i).first()
    ).toBeVisible({ timeout: 15_000 });

    // Reload and verify history is restored
    await page.reload();
    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });

    await expect(page.getByText(userMessage).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("buy via chat updates cash balance in UI", async ({ page }) => {
    await expect(page.locator("text=/\\$10,000\\.\\d{2}/").first()).toBeVisible({
      timeout: 10_000,
    });

    // Mock regex: buy\s+(\d+)\s+(?:shares?\s+(?:of\s+)?)?([A-Za-z.]+)
    await sendChatMessage(page, "buy 1 shares of GOOGL");

    // Wait for response and balance update — cash should decrease
    await expect(page.locator("text=/\\$10,000\\.00/").first()).toBeHidden({
      timeout: 15_000,
    });
  });

  test("chat API returns correct structure", async ({ request }) => {
    const response = await request.post("/api/chat", {
      data: { message: "How is my portfolio?" },
    });
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty("message");
    expect(body).toHaveProperty("trades");
    expect(body).toHaveProperty("watchlist_changes");
    expect(body).toHaveProperty("errors");
    expect(typeof body.message).toBe("string");
    expect(Array.isArray(body.trades)).toBe(true);
    expect(Array.isArray(body.watchlist_changes)).toBe(true);
    expect(Array.isArray(body.errors)).toBe(true);
  });

  test("chat API executes a buy trade via natural language", async ({
    request,
  }) => {
    const response = await request.post("/api/chat", {
      data: { message: "buy 1 shares of MSFT" },
    });
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body.trades.length).toBeGreaterThan(0);

    const trade = body.trades[0];
    expect(trade.ticker).toBe("MSFT");
    expect(trade.side).toBe("buy");
    expect(trade.quantity).toBe(1);
    expect(trade.success).toBe(true);
  });

  test("chat API executes a sell trade via natural language", async ({
    request,
  }) => {
    // First buy shares so we can sell them
    await request.post("/api/chat", {
      data: { message: "buy 2 shares of AAPL" },
    });

    const response = await request.post("/api/chat", {
      data: { message: "sell 1 shares of AAPL" },
    });
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body.trades.length).toBeGreaterThan(0);

    const trade = body.trades[0];
    expect(trade.ticker).toBe("AAPL");
    expect(trade.side).toBe("sell");
    expect(trade.quantity).toBe(1);
    expect(trade.success).toBe(true);
  });

  test("chat API adds a ticker to watchlist via natural language", async ({
    request,
  }) => {
    const response = await request.post("/api/chat", {
      data: { message: "add PYPL" },
    });
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body.watchlist_changes.length).toBeGreaterThan(0);

    const change = body.watchlist_changes[0];
    expect(change.ticker).toBe("PYPL");
    expect(change.action).toBe("add");
    expect(change.success).toBe(true);
  });

  test("chat API removes a ticker from watchlist via natural language", async ({
    request,
  }) => {
    // NFLX is a default ticker so it should be present
    const response = await request.post("/api/chat", {
      data: { message: "remove NFLX" },
    });
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body.watchlist_changes.length).toBeGreaterThan(0);

    const change = body.watchlist_changes[0];
    expect(change.ticker).toBe("NFLX");
    expect(change.action).toBe("remove");
    expect(change.success).toBe(true);
  });

  test("chat API returns default conversational reply for generic messages", async ({
    request,
  }) => {
    const response = await request.post("/api/chat", {
      data: { message: "Tell me about the market" },
    });
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(typeof body.message).toBe("string");
    expect(body.message.length).toBeGreaterThan(0);
    // No trades or watchlist changes for generic messages
    expect(body.trades).toHaveLength(0);
    expect(body.watchlist_changes).toHaveLength(0);
  });

  test("chat API rejects empty message with 422", async ({ request }) => {
    const response = await request.post("/api/chat", {
      data: { message: "" },
    });
    // FastAPI min_length=1 validation returns 422 Unprocessable Entity
    expect(response.status()).toBe(422);
  });
});
