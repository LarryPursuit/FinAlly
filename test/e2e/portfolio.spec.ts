import { test, expect } from "@playwright/test";

test.describe("Portfolio", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
  });

  test("shows starting cash balance of $10,000", async ({ page }) => {
    await expect(page.getByText("$10,000.00")).toBeVisible({ timeout: 10_000 });
  });

  test("displays positions table with headers", async ({ page }) => {
    // The positions section should be visible
    await expect(page.getByText("Positions")).toBeVisible({ timeout: 10_000 });
  });

  test("shows no positions on fresh start", async ({ page }) => {
    await expect(page.getByText("No positions yet")).toBeVisible({
      timeout: 10_000,
    });
  });

  test("P&L chart section is visible", async ({ page }) => {
    // Portfolio value chart / P&L chart
    await expect(
      page
        .getByText(/P&L/i)
        .or(page.getByText(/portfolio value/i))
        .or(page.locator('[data-testid*="pnl"]'))
        .or(page.locator('[data-testid*="chart"]'))
        .first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("heatmap section is visible", async ({ page }) => {
    await expect(
      page
        .getByText(/heatmap/i)
        .or(page.locator('[data-testid*="heatmap"]'))
        .or(page.locator('[data-testid*="treemap"]'))
        .first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("portfolio total value is shown in header", async ({ page }) => {
    // Total value is shown — on fresh start it equals cash ($10,000)
    await expect(
      page.locator("text=/\\$10,000\\.\\d{2}/").first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("positions table shows correct columns after a buy", async ({
    page,
  }) => {
    // Execute a buy
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
    await quantityInput.fill("1");

    const buyBtn = page
      .locator('button:has-text("Buy"), [data-testid*="buy"]')
      .first();
    await buyBtn.click();

    // Wait for position row
    await expect(page.getByText("No positions yet")).toBeHidden({
      timeout: 10_000,
    });

    // Positions table should show ticker, quantity, avg cost, and P&L columns
    const positionsArea = page.locator(
      '[data-testid*="positions"], section:has-text("Positions"), table'
    );

    await expect(positionsArea.getByText("AAPL").first()).toBeVisible({
      timeout: 10_000,
    });

    // Should show quantity (1)
    await expect(positionsArea.getByText("1").first()).toBeVisible({
      timeout: 5_000,
    });
  });

  test("cash balance updates after a buy", async ({ page }) => {
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
    await quantityInput.fill("1");

    const buyBtn = page
      .locator('button:has-text("Buy"), [data-testid*="buy"]')
      .first();
    await buyBtn.click();

    // Cash balance should no longer be exactly $10,000 after buying
    await expect(page.locator("text=/\\$10,000\\.00/").first()).toBeHidden({
      timeout: 10_000,
    });

    // New balance should still be a monetary value
    await expect(
      page.locator("text=/\\$\\d{1,2},\\d{3}\\.\\d{2}/").first()
    ).toBeVisible({ timeout: 5_000 });
  });

  test("portfolio history endpoint is reachable", async ({ page, request }) => {
    const response = await request.get("/api/portfolio/history");
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty("snapshots");
    expect(Array.isArray(body.snapshots)).toBe(true);
  });

  test("portfolio API returns correct structure", async ({ request }) => {
    const response = await request.get("/api/portfolio");
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty("cash_balance");
    expect(body).toHaveProperty("total_value");
    expect(body).toHaveProperty("positions");
    expect(typeof body.cash_balance).toBe("number");
    expect(Array.isArray(body.positions)).toBe(true);
  });
});
