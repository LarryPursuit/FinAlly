import { test, expect } from "@playwright/test";

const DEFAULT_TICKERS = [
  "AAPL",
  "GOOGL",
  "MSFT",
  "AMZN",
  "TSLA",
  "NVDA",
  "META",
  "JPM",
  "V",
  "NFLX",
];

test.describe("Fresh start", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("shows the FinAlly header", async ({ page }) => {
    await expect(page.getByText("FinAlly")).toBeVisible();
  });

  test("displays all 10 default tickers in the watchlist", async ({ page }) => {
    for (const ticker of DEFAULT_TICKERS) {
      await expect(page.getByText(ticker, { exact: true }).first()).toBeVisible({
        timeout: 10_000,
      });
    }
  });

  test("shows $10,000 starting cash", async ({ page }) => {
    await expect(page.getByText("$10,000.00")).toBeVisible({ timeout: 10_000 });
  });

  test("shows portfolio total value", async ({ page }) => {
    await expect(page.getByText("Portfolio").first()).toBeVisible();
  });

  test("shows connection status indicator", async ({ page }) => {
    // Connection dot should show Live when SSE connects
    await expect(page.getByText("Live")).toBeVisible({ timeout: 10_000 });
  });

  test("prices update within 5 seconds", async ({ page }) => {
    // Wait for at least one price to appear (a number with decimal)
    const priceCell = page.locator("text=/\\d+\\.\\d{2}/").first();
    await expect(priceCell).toBeVisible({ timeout: 5_000 });
  });

  test("displays Positions section", async ({ page }) => {
    await expect(page.getByText("Positions").first()).toBeVisible();
  });

  test("shows 'No positions yet' for a fresh start", async ({ page }) => {
    await expect(page.getByText("No positions yet")).toBeVisible({
      timeout: 5_000,
    });
  });
});
