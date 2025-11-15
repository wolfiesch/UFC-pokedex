# E2E Testing with Playwright

## FormBar Tooltip Testing

This directory contains Playwright end-to-end tests for the UFC Pokedex frontend, with a focus on testing the FormBar component's tooltip behavior.

## Setup

### Install Playwright

```bash
pnpm add -D @playwright/test
npx playwright install chromium
```

### Start Development Server

The tests require the frontend dev server to be running:

```bash
# From project root
make dev

# Or from frontend directory
pnpm dev
```

## Running Tests

### Run All E2E Tests

```bash
cd frontend
npx playwright test
```

### Run FormBar Tooltip Tests Only

Using the dedicated script:

```bash
cd frontend
./scripts/test-form-bar-tooltips.sh
```

Or manually:

```bash
npx playwright test tests/e2e/specs/form-bar-tooltips.spec.ts --project=chromium
```

### Run Tests in UI Mode (Interactive)

```bash
npx playwright test --ui
```

### Debug a Specific Test

```bash
npx playwright test --debug tests/e2e/specs/form-bar-tooltips.spec.ts
```

## FormBar Tooltip Test Suite

The FormBar tooltip tests verify the following behavior:

### 1. Single Tooltip Display
- **Test:** Only one tooltip shows at a time when hovering over different fight squares
- **Purpose:** Ensures tooltips don't overlap or show simultaneously
- **What it does:** Hovers over each square sequentially and verifies exactly one tooltip is visible

### 2. Correct Information
- **Test:** Tooltip contains correct fight information
- **Purpose:** Validates tooltip content accuracy
- **What it does:** Checks tooltip text includes result (W/L/D/NC), opponent name, and "vs"

### 3. Screenshot Capture
- **Test:** Captures screenshots of each tooltip state
- **Purpose:** Visual regression testing and manual review
- **What it does:** Saves PNG screenshots to `tests/e2e/screenshots/form-tooltip-{index}.png`

### 4. No Overlapping
- **Test:** Rapid hover interactions don't cause overlapping tooltips
- **Purpose:** Stress test for tooltip state management
- **What it does:** Quickly hovers over multiple squares and verifies ≤1 tooltip visible

### 5. Positioning
- **Test:** Tooltip appears above the fight square
- **Purpose:** Verifies correct CSS positioning
- **What it does:** Compares bounding boxes to ensure tooltip Y position is above square

### 6. Styling
- **Test:** Tooltip has correct Tailwind classes
- **Purpose:** Visual consistency check
- **What it does:** Verifies presence of expected CSS classes (bg-black/90, rounded-lg, etc.)

### 7. Visual Baseline
- **Test:** Screenshot comparison against baseline
- **Purpose:** Catch unintended visual regressions
- **What it does:** Compares current screenshot to saved baseline

## Screenshots

Screenshots are saved to:
```
frontend/tests/e2e/screenshots/
├── form-tooltip-0.png  # First fight square tooltip
├── form-tooltip-1.png  # Second fight square tooltip
├── form-tooltip-2.png  # Third fight square tooltip
├── form-tooltip-3.png  # Fourth fight square tooltip
└── form-tooltip-4.png  # Fifth fight square tooltip
```

## Test Reports

After running tests, view the HTML report:

```bash
npx playwright show-report
```

Reports include:
- Test results (pass/fail)
- Screenshots on failure
- Video recordings (if enabled)
- Trace files for debugging

## Configuration

Playwright configuration is in `tests/e2e/playwright.config.ts`:

- **Base URL:** `http://localhost:3002` (configurable via `APP_URL` env var)
- **Browsers:** Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari
- **Retries:** 2 on CI, 0 locally
- **Timeout:** Default 30s per test
- **Screenshots:** On failure only
- **Videos:** Retained on failure

## Troubleshooting

### Dev server not running
```
Error: page.goto: net::ERR_CONNECTION_REFUSED
```
**Solution:** Start the dev server with `make dev`

### Playwright not installed
```
Error: Executable doesn't exist
```
**Solution:** Run `npx playwright install`

### Tooltips not appearing
- Ensure fight history data is loaded (may require backend to be running)
- Check browser console for errors
- Verify FormBar component is rendering with `data-testid="form-bar"`

### Screenshots empty or missing content
- Add longer wait times: `await page.waitForTimeout(500)`
- Ensure viewport is large enough
- Check Z-index and positioning of tooltip elements

## Best Practices

1. **Always wait for elements** before interacting:
   ```ts
   await expect(element).toBeVisible();
   await element.hover();
   ```

2. **Use data-testid attributes** for reliable selectors:
   ```ts
   const tooltip = page.locator('[data-testid="form-tooltip-0"]');
   ```

3. **Clean up state between tests**:
   ```ts
   await page.mouse.move(0, 0); // Move mouse away
   await page.waitForTimeout(200); // Wait for animations
   ```

4. **Take screenshots for debugging**:
   ```ts
   await page.screenshot({ path: 'debug.png' });
   ```

## CI/CD Integration

To run tests in CI:

```yaml
- name: Install Playwright
  run: pnpm add -D @playwright/test && npx playwright install --with-deps

- name: Run E2E Tests
  run: pnpm exec playwright test
  env:
    APP_URL: http://localhost:3000
```

## Further Reading

- [Playwright Documentation](https://playwright.dev/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Visual Testing Guide](https://playwright.dev/docs/test-snapshots)
