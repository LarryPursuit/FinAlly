import { test, expect } from "@playwright/test";

test.describe("Trading", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Wait for prices to load so trades can execute
    await expect(page.getByText("Live")).toBeVisible({ timeout: 10_000 });
  });

  test("can buy shares and see position appear", async ({ page }) => {
    // Fill in the trade bar
    const tickerInput = page.getByPlaceholderText("AAPL");
    const qtyInput = page.getByPlaceholderText("Qty");
    const buyButton = page.getByRole("button", { name: "Buy" });

    // If ticker input exists and is editable, type into it
    if (await tickerInput.isVisible()) {
      await tickerInput.fill("AAPL");
    }
    await qtyInput.fill("5");
    await buyButton.click();

    // Should see a success message
    await expect(page.getByText(/Bought 5 AAPL/i)).toBeVisible({
      timeout: 10_000,
    });

    // Cash should decrease from $10,000
    await expect(page.getByText("$10,000.00")).not.toBeVisible({
      timeout: 5_000,
    });

    // AAPL should appear in positions
    const positions = page.locator("table, [class*='positions']");
    await expect(positions.getByText("AAPL").first()).toBeVisible({
      timeout: 5_000,
    });
  });

  test("can sell shares after buying", async ({ page }) => {
    // First buy some shares
    const qtyInput = page.getByPlaceholderText("Qty");
    const buyButton = page.getByRole("button", { name: "Buy" });
    const sellButton = page.getByRole("button", { name: "Sell" });

    await qtyInput.fill("10");
    await buyButton.click();

    // Wait for buy to complete
    await expect(page.getByText(/Bought 10/i)).toBeVisible({
      timeout: 10_000,
    });

    // Record the cash after buy
    await page.waitForTimeout(1000);

    // Now sell some shares
    await qtyInput.fill("3");
    await sellButton.click();

    // Should see a success message for the sell
    await expect(page.getByText(/Sold 3/i)).toBeVisible({
      timeout: 10_000,
    });
  });

  test("shows error when buying without quantity", async ({ page }) => {
    const buyButton = page.getByRole("button", { name: "Buy" });
    await buyButton.click();

    // Should show a validation error
    await expect(
      page.getByText(/enter a valid|quantity/i)
    ).toBeVisible({ timeout: 5_000 });
  });
});
