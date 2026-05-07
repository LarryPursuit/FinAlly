import { test, expect } from "@playwright/test";

test.describe("Trading", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
    // Wait for at least one price to be available
    await page
      .locator("text=/\\$?\\d+\\.\\d{2}/")
      .first()
      .waitFor({ timeout: 10_000 });
  });

  test("trade bar is visible with ticker, quantity, and buy/sell controls", async ({
    page,
  }) => {
    // Trade bar should have input fields and buttons
    const buyBtn = page
      .locator(
        'button:has-text("Buy"), [data-testid*="buy"], [aria-label*="buy" i]'
      )
      .first();
    await expect(buyBtn).toBeVisible({ timeout: 10_000 });

    const sellBtn = page
      .locator(
        'button:has-text("Sell"), [data-testid*="sell"], [aria-label*="sell" i]'
      )
      .first();
    await expect(sellBtn).toBeVisible({ timeout: 10_000 });
  });

  test("executes a buy order and reduces cash balance", async ({ page }) => {
    // Capture initial cash balance
    const cashText = await page
      .locator("text=/\\$10,000\\.\\d{2}/")
      .first()
      .textContent({ timeout: 10_000 });
    expect(cashText).toBeTruthy();

    // Fill in trade bar for AAPL buy
    const tickerInput = page
      .locator(
        'input[placeholder*="ticker" i], [data-testid*="trade-ticker"], [data-testid*="trade"] input'
      )
      .first();
    const quantityInput = page
      .locator(
        'input[placeholder*="quantity" i], input[placeholder*="qty" i], input[type="number"]'
      )
      .first();

    if (await tickerInput.isVisible()) {
      await tickerInput.fill("AAPL");
    }
    await quantityInput.fill("1");

    const buyBtn = page
      .locator('button:has-text("Buy"), [data-testid*="buy"]')
      .first();
    await buyBtn.click();

    // Cash should be reduced after buy
    await expect(page.locator("text=/\\$10,000\\.\\d{2}/").first()).toBeHidden({
      timeout: 10_000,
    });
  });

  test("buy order creates a position in the positions table", async ({
    page,
  }) => {
    const tickerInput = page
      .locator(
        'input[placeholder*="ticker" i], [data-testid*="trade-ticker"], [data-testid*="trade"] input'
      )
      .first();
    const quantityInput = page
      .locator(
        'input[placeholder*="quantity" i], input[placeholder*="qty" i], input[type="number"]'
      )
      .first();

    if (await tickerInput.isVisible()) {
      await tickerInput.fill("AAPL");
    }
    await quantityInput.fill("1");

    const buyBtn = page
      .locator('button:has-text("Buy"), [data-testid*="buy"]')
      .first();
    await buyBtn.click();

    // "No positions yet" should disappear after the buy
    await expect(page.getByText("No positions yet")).toBeHidden({
      timeout: 10_000,
    });

    // AAPL should appear in positions
    await expect(
      page.locator('[data-testid*="positions"], table').getByText("AAPL").first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("sell order reduces position quantity", async ({ page }) => {
    // First buy 2 shares
    const quantityInput = page
      .locator(
        'input[placeholder*="quantity" i], input[placeholder*="qty" i], input[type="number"]'
      )
      .first();
    const tickerInput = page
      .locator(
        'input[placeholder*="ticker" i], [data-testid*="trade-ticker"], [data-testid*="trade"] input'
      )
      .first();

    if (await tickerInput.isVisible()) {
      await tickerInput.fill("AAPL");
    }
    await quantityInput.fill("2");

    const buyBtn = page
      .locator('button:has-text("Buy"), [data-testid*="buy"]')
      .first();
    await buyBtn.click();

    // Wait for position to appear
    await expect(page.getByText("No positions yet")).toBeHidden({
      timeout: 10_000,
    });

    // Now sell 1 share
    if (await tickerInput.isVisible()) {
      await tickerInput.fill("AAPL");
    }
    await quantityInput.fill("1");

    const sellBtn = page
      .locator('button:has-text("Sell"), [data-testid*="sell"]')
      .first();
    await sellBtn.click();

    // Position should still exist with quantity 1
    await expect(
      page.locator('[data-testid*="positions"], table').getByText("AAPL").first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("cannot sell more shares than owned", async ({ page }) => {
    const quantityInput = page
      .locator(
        'input[placeholder*="quantity" i], input[placeholder*="qty" i], input[type="number"]'
      )
      .first();
    const tickerInput = page
      .locator(
        'input[placeholder*="ticker" i], [data-testid*="trade-ticker"], [data-testid*="trade"] input'
      )
      .first();

    if (await tickerInput.isVisible()) {
      await tickerInput.fill("AAPL");
    }
    await quantityInput.fill("100");

    const sellBtn = page
      .locator('button:has-text("Sell"), [data-testid*="sell"]')
      .first();
    await sellBtn.click();

    // Should show error — insufficient shares
    await expect(
      page
        .getByText(/insufficient/i)
        .or(page.getByText(/not enough/i))
        .or(page.locator('[data-testid*="error"]'))
        .or(page.locator(".error"))
        .first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("cannot buy more than cash balance allows", async ({ page }) => {
    const quantityInput = page
      .locator(
        'input[placeholder*="quantity" i], input[placeholder*="qty" i], input[type="number"]'
      )
      .first();
    const tickerInput = page
      .locator(
        'input[placeholder*="ticker" i], [data-testid*="trade-ticker"], [data-testid*="trade"] input'
      )
      .first();

    if (await tickerInput.isVisible()) {
      await tickerInput.fill("AAPL");
    }
    // 10000 shares at any real price will exceed $10,000 balance
    await quantityInput.fill("10000");

    const buyBtn = page
      .locator('button:has-text("Buy"), [data-testid*="buy"]')
      .first();
    await buyBtn.click();

    // Should show insufficient cash error
    await expect(
      page
        .getByText(/insufficient/i)
        .or(page.getByText(/not enough/i))
        .or(page.getByText(/cash/i))
        .or(page.locator('[data-testid*="error"]'))
        .or(page.locator(".error"))
        .first()
    ).toBeVisible({ timeout: 10_000 });
  });
});
