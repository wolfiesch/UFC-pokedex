/**
 * Example Playwright Test for UFC Pokedex
 *
 * This demonstrates how to test your application using Playwright.
 * You can ask Claude Code to generate tests like this automatically
 * by using the Playwright MCP integration.
 *
 * Usage with Claude Code:
 * - "Test the homepage and take a screenshot"
 * - "Generate a test that validates fighter search"
 * - "Check if all fighter cards load correctly"
 */

import { test, expect } from '@playwright/test';

// Use environment variable or default to Cloudflare tunnel
const BASE_URL = process.env.APP_URL || 'http://localhost:3002';

test.describe('UFC Pokedex Homepage', () => {
  test('should load the homepage successfully', async ({ page }) => {
    // Navigate to the homepage
    await page.goto(BASE_URL);

    // Wait for the page to load
    await page.waitForLoadState('networkidle');

    // Check that the title is correct
    await expect(page).toHaveTitle(/UFC Fighter Pokedex/);

    // Check for main heading
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible();

    // Take a screenshot for visual verification
    await page.screenshot({
      path: 'tests/e2e/screenshots/homepage.png',
      fullPage: true
    });

    console.log('✓ Homepage loaded successfully');
  });

  test('should display fighter grid', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Wait for fighter cards to appear (adjust selector based on your implementation)
    await page.waitForSelector('[data-testid="fighter-card"], .fighter-card, article', {
      timeout: 10000
    });

    // Count how many fighter cards are visible
    const fighterCards = await page.locator('[data-testid="fighter-card"], .fighter-card, article').count();

    console.log(`✓ Found ${fighterCards} fighter cards`);
    expect(fighterCards).toBeGreaterThan(0);

    // Take a screenshot
    await page.screenshot({
      path: 'tests/e2e/screenshots/fighter-grid.png'
    });
  });

  test('should navigate to fighter detail page', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Click the first fighter card (adjust selector as needed)
    const firstFighter = page.locator('[data-testid="fighter-card"], .fighter-card, article').first();
    await firstFighter.waitFor({ state: 'visible' });
    await firstFighter.click();

    // Wait for navigation
    await page.waitForLoadState('networkidle');

    // Check that we're on a detail page
    expect(page.url()).toContain('/fighters/');

    // Take a screenshot of the detail page
    await page.screenshot({
      path: 'tests/e2e/screenshots/fighter-detail.png',
      fullPage: true
    });

    console.log('✓ Fighter detail page loaded');
  });
});

test.describe('Responsive Design', () => {
  test('should work on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Take mobile screenshot
    await page.screenshot({
      path: 'tests/e2e/screenshots/homepage-mobile.png',
      fullPage: true
    });

    console.log('✓ Mobile viewport tested');
  });

  test('should work on tablet viewport', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });

    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Take tablet screenshot
    await page.screenshot({
      path: 'tests/e2e/screenshots/homepage-tablet.png',
      fullPage: true
    });

    console.log('✓ Tablet viewport tested');
  });
});
