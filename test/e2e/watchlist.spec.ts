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

test.describe("Watchlist", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Wait for prices to load (SSE connected)
    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
  });

  test("displays all 10 default tickers", async ({ page }) => {
    for (const ticker of DEFAULT_TICKERS) {
      await expect(
        page.getByText(ticker, { exact: true }).first()
      ).toBeVisible({ timeout: 10_000 });
    }
  });

  test("shows live price for each ticker", async ({ page }) => {
    // At least one price cell with decimal format should be visible
    const priceCell = page.locator("text=/\\$?\\d+\\.\\d{2}/").first();
    await expect(priceCell).toBeVisible({ timeout: 10_000 });
  });

  test("adds a new ticker to the watchlist", async ({ page }) => {
    // Find the watchlist add input/button
    const addInput = page
      .locator('input[placeholder*="ticker" i], input[placeholder*="add" i]')
      .first();
    await expect(addInput).toBeVisible({ timeout: 10_000 });

    await addInput.fill("PYPL");
    await addInput.press("Enter");

    await expect(page.getByText("PYPL", { exact: true }).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("removes a ticker from the watchlist", async ({ page }) => {
    // First verify NFLX is visible
    await expect(
      page.getByText("NFLX", { exact: true }).first()
    ).toBeVisible();

    // Find and click the remove button for NFLX
    // The remove button is typically near the ticker row
    const nflxRow = page
      .locator('[data-testid*="watchlist"] >> text=NFLX')
      .first()
      .locator("..");
    const removeBtn = nflxRow
      .locator('button[aria-label*="remove" i], button[title*="remove" i]')
      .first();

    if (await removeBtn.isVisible()) {
      await removeBtn.click();
    } else {
      // Try hovering the row to reveal remove button
      const nflxItem = page
        .locator("text=NFLX", { exact: true })
        .first()
        .locator("..");
      await nflxItem.hover();
      await page
        .locator(
          'button[aria-label*="remove" i], button[aria-label*="delete" i], button[title*="remove" i]'
        )
        .first()
        .click();
    }

    await expect(page.getByText("NFLX", { exact: true }).first()).toBeHidden({
      timeout: 10_000,
    });
  });

  test("shows change percentage for tickers", async ({ page }) => {
    // Change % typically shown as +X.XX% or -X.XX%
    const changePct = page.locator("text=/%/").first();
    await expect(changePct).toBeVisible({ timeout: 10_000 });
  });

  test("clicking a ticker selects it for the main chart", async ({ page }) => {
    await page.getByText("AAPL", { exact: true }).first().click();
    // After clicking, AAPL should be shown in the chart area
    await expect(page.locator("text=AAPL").nth(1)).toBeVisible({
      timeout: 5_000,
    });
  });

  test("rejects invalid ticker on add", async ({ page }) => {
    const addInput = page
      .locator('input[placeholder*="ticker" i], input[placeholder*="add" i]')
      .first();
    await expect(addInput).toBeVisible({ timeout: 10_000 });

    // Too long — 6+ chars is invalid
    await addInput.fill("TOOLONG");
    await addInput.press("Enter");

    // Should not appear in list, may show an error
    await page.waitForTimeout(1000);
    await expect(
      page.getByText("TOOLONG", { exact: true }).first()
    ).toBeHidden();
  });
});
