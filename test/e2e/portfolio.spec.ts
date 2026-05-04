import { test, expect } from "@playwright/test";

test.describe("Portfolio visualization", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Live")).toBeVisible({ timeout: 10_000 });
  });

  test("heatmap renders after buying positions", async ({ page }) => {
    // Buy some shares to create a position for the heatmap
    const qtyInput = page.getByPlaceholderText("Qty");
    const buyButton = page.getByRole("button", { name: "Buy" });

    await qtyInput.fill("5");
    await buyButton.click();
    await expect(page.getByText(/Bought 5/i)).toBeVisible({ timeout: 10_000 });

    // The heatmap/treemap should render — look for canvas or SVG elements
    // in the heatmap area
    const heatmapArea = page.locator("canvas, svg, [class*='heatmap'], [class*='treemap']");
    await expect(heatmapArea.first()).toBeVisible({ timeout: 10_000 });
  });

  test("P&L chart area is visible", async ({ page }) => {
    // The P&L chart area should be present even before trades
    // It uses portfolio_snapshots which has an initial seed entry
    const chartArea = page.locator(
      "canvas, [class*='pnl'], [class*='chart']"
    );
    await expect(chartArea.first()).toBeVisible({ timeout: 10_000 });
  });

  test("positions table updates after trade", async ({ page }) => {
    // Verify no positions initially
    await expect(page.getByText("No positions yet")).toBeVisible({
      timeout: 5_000,
    });

    // Execute a trade
    const qtyInput = page.getByPlaceholderText("Qty");
    const buyButton = page.getByRole("button", { name: "Buy" });

    await qtyInput.fill("10");
    await buyButton.click();
    await expect(page.getByText(/Bought 10/i)).toBeVisible({ timeout: 10_000 });

    // "No positions yet" should be replaced by actual position data
    await expect(page.getByText("No positions yet")).not.toBeVisible({
      timeout: 5_000,
    });
  });
});
