import { test, expect } from '@playwright/test';

/**
 * E2E tests for FormBar component tooltip behavior
 *
 * Tests verify that:
 * 1. Only one tooltip shows at a time when hovering over fight squares
 * 2. Tooltips contain correct fight information
 * 3. Tooltip positioning is correct
 * 4. Visual appearance matches design specs
 */

test.describe('FormBar Tooltip Behavior', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the home page where fighter cards are displayed
    await page.goto('/');

    // Wait for the page to load and fighter cards to appear
    await page.waitForSelector('[data-testid="form-bar"]', { timeout: 10000 });
  });

  test('should display only one tooltip at a time when hovering over different squares', async ({
    page,
  }) => {
    // Find the first fighter card with a form bar
    const formBar = page.locator('[data-testid="form-bar"]').first();

    // Wait for the form bar to be visible
    await expect(formBar).toBeVisible();

    // Get all fight squares
    const squares = formBar.locator('[data-testid^="form-square-"]');
    const squareCount = await squares.count();

    console.log(`Found ${squareCount} fight squares to test`);

    // Test each square individually
    for (let i = 0; i < squareCount; i++) {
      const square = squares.nth(i);

      // Hover over the current square
      await square.hover();

      // Wait a moment for tooltip to appear
      await page.waitForTimeout(200);

      // Check that exactly one tooltip is visible
      const visibleTooltips = page.locator('[data-testid^="form-tooltip-"]');
      const tooltipCount = await visibleTooltips.count();

      expect(tooltipCount).toBe(1);

      // Verify it's the correct tooltip for this square
      const expectedTooltip = page.locator(
        `[data-testid="form-tooltip-${i}"]`
      );
      await expect(expectedTooltip).toBeVisible();

      // Move mouse away to hide tooltip
      await page.mouse.move(0, 0);
      await page.waitForTimeout(200);

      // Verify tooltip is gone
      await expect(expectedTooltip).not.toBeVisible();
    }
  });

  test('should show tooltip with correct fight information', async ({
    page,
  }) => {
    // Find the first form bar
    const formBar = page.locator('[data-testid="form-bar"]').first();
    await expect(formBar).toBeVisible();

    // Hover over the first square
    const firstSquare = formBar.locator('[data-testid="form-square-0"]');
    await firstSquare.hover();

    // Wait for tooltip
    await page.waitForTimeout(200);

    // Get the tooltip
    const tooltip = page.locator('[data-testid="form-tooltip-0"]');
    await expect(tooltip).toBeVisible();

    // Verify tooltip contains expected content
    const tooltipText = await tooltip.textContent();
    expect(tooltipText).toBeTruthy();

    // Should contain result type (W/L/D/NC) and "vs" indicating opponent
    expect(tooltipText).toMatch(/(W|L|D|NC)\s+vs\s+/);
  });

  test('should capture screenshots of each tooltip state', async ({
    page,
  }) => {
    const formBar = page.locator('[data-testid="form-bar"]').first();
    await expect(formBar).toBeVisible();

    const squares = formBar.locator('[data-testid^="form-square-"]');
    const squareCount = await squares.count();

    // Capture screenshot of each tooltip
    for (let i = 0; i < squareCount; i++) {
      const square = squares.nth(i);

      // Hover over square
      await square.hover();
      await page.waitForTimeout(300);

      // Verify tooltip is visible
      const tooltip = page.locator(`[data-testid="form-tooltip-${i}"]`);
      await expect(tooltip).toBeVisible();

      // Take screenshot of the fighter card with tooltip
      const card = page.locator('[data-testid="form-bar"]').first();
      await card
        .locator('..')
        .screenshot({
          path: `tests/e2e/screenshots/form-tooltip-${i}.png`,
        });

      // Move mouse away
      await page.mouse.move(0, 0);
      await page.waitForTimeout(200);
    }
  });

  test('should not show overlapping tooltips', async ({ page }) => {
    const formBar = page.locator('[data-testid="form-bar"]').first();
    await expect(formBar).toBeVisible();

    const squares = formBar.locator('[data-testid^="form-square-"]');
    const squareCount = await squares.count();

    // Quickly hover over multiple squares
    for (let i = 0; i < Math.min(squareCount, 3); i++) {
      const square = squares.nth(i);
      await square.hover();

      // Check that only one tooltip is visible
      const visibleTooltips = page.locator(
        '[data-testid^="form-tooltip-"]:visible'
      );
      const count = await visibleTooltips.count();

      expect(count).toBeLessThanOrEqual(1);
    }
  });

  test('should have correct tooltip positioning above the square', async ({
    page,
  }) => {
    const formBar = page.locator('[data-testid="form-bar"]').first();
    await expect(formBar).toBeVisible();

    const firstSquare = formBar.locator('[data-testid="form-square-0"]');
    await firstSquare.hover();
    await page.waitForTimeout(200);

    const tooltip = page.locator('[data-testid="form-tooltip-0"]');
    await expect(tooltip).toBeVisible();

    // Get bounding boxes
    const squareBox = await firstSquare.boundingBox();
    const tooltipBox = await tooltip.boundingBox();

    expect(squareBox).toBeTruthy();
    expect(tooltipBox).toBeTruthy();

    // Tooltip should be above the square (lower y value)
    if (squareBox && tooltipBox) {
      expect(tooltipBox.y + tooltipBox.height).toBeLessThan(squareBox.y);
    }
  });

  test('should display tooltip with proper styling', async ({ page }) => {
    const formBar = page.locator('[data-testid="form-bar"]').first();
    await expect(formBar).toBeVisible();

    const firstSquare = formBar.locator('[data-testid="form-square-0"]');
    await firstSquare.hover();
    await page.waitForTimeout(200);

    const tooltip = page.locator('[data-testid="form-tooltip-0"]');
    await expect(tooltip).toBeVisible();

    // Check tooltip has expected classes for styling
    const className = await tooltip.getAttribute('class');
    expect(className).toContain('bg-black/90');
    expect(className).toContain('rounded-lg');
    expect(className).toContain('px-3');
    expect(className).toContain('py-2');
  });
});

test.describe('FormBar Visual Regression', () => {
  test('should match baseline screenshot for form bar with tooltip', async ({
    page,
  }) => {
    await page.goto('/');

    const formBar = page.locator('[data-testid="form-bar"]').first();
    await expect(formBar).toBeVisible();

    // Hover over middle square
    const middleSquare = formBar.locator('[data-testid="form-square-2"]');
    await middleSquare.hover();
    await page.waitForTimeout(300);

    // Take full page screenshot for visual comparison
    await expect(page).toHaveScreenshot('form-bar-tooltip-baseline.png', {
      fullPage: false,
      clip: {
        x: 0,
        y: 0,
        width: 1280,
        height: 800,
      },
    });
  });
});
