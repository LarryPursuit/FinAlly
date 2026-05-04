import { test, expect } from "@playwright/test";

test.describe("Watchlist management", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Wait for watchlist to load
    await expect(page.getByText("AAPL", { exact: true }).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("can add a ticker to the watchlist", async ({ page }) => {
    // Look for the add-ticker input
    const tickerInput = page.getByPlaceholderText(/ticker/i).first();
    await tickerInput.fill("PYPL");
    await tickerInput.press("Enter");

    // PYPL should appear in the watchlist
    await expect(page.getByText("PYPL", { exact: true }).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("can remove a ticker from the watchlist", async ({ page }) => {
    // First verify NFLX is present
    const nflxElement = page.getByText("NFLX", { exact: true }).first();
    await expect(nflxElement).toBeVisible();

    // Find and click the remove button near NFLX
    // The remove button is typically an X or close icon next to the ticker
    const nflxRow = page.locator("[data-ticker='NFLX']").or(
      nflxElement.locator("..")
    );
    const removeButton = nflxRow.getByRole("button").first();
    if (await removeButton.isVisible()) {
      await removeButton.click();
    } else {
      // Try right-clicking or hover to reveal remove option
      await nflxElement.hover();
      const hoverRemove = page.getByRole("button", { name: /remove|delete|×/i }).first();
      await hoverRemove.click();
    }

    // NFLX should no longer be visible
    await expect(
      page.getByText("NFLX", { exact: true })
    ).not.toBeVisible({ timeout: 5_000 });
  });
});
