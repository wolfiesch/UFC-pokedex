# Playwright Testing with Claude Code

This guide explains how to use Playwright MCP integration with Claude Code to automate testing and visual analysis of the UFC Pokedex frontend.

## Setup Complete ✅

The following has been configured for you:

1. **`.mcp.json`** - Model Context Protocol configuration for Playwright
2. **`frontend/tests/e2e/playwright.config.ts`** - Playwright test configuration
3. **`frontend/tests/e2e/specs/`** - Example test directory with sample tests
4. **Browser binaries** - Chromium, Firefox, WebKit installed

## How It Works

### Playwright MCP Integration

Claude Code can now autonomously:
- Write Playwright test scripts
- Navigate your application (local or Cloudflare tunnel)
- Interact with UI elements (click, type, scroll)
- Capture screenshots at any point
- Validate functionality and report bugs
- Generate reusable test files

### Two Ways to Analyze Your Frontend

#### 1. Manual Screenshots (Simple & Quick)

**Steps:**
1. Visit your app in a browser (localhost or Cloudflare tunnel)
2. Take a screenshot:
   - macOS: `Shift + Cmd + Ctrl + 4` (saves to clipboard)
   - Or use browser DevTools screenshot
3. In Claude Code terminal, paste with **Control+V** (NOT Command+V)
4. Ask Claude to analyze

**Example prompts:**
- "Here's my homepage - how can I improve the layout?"
- "This search feature isn't working - what's the issue?"
- "Compare this design mockup to my current implementation"

#### 2. Automated Testing with Playwright (Powerful)

**Steps:**
1. Just ask Claude Code to test your app!
2. Claude will autonomously write and execute Playwright scripts
3. Get screenshots, test results, and bug reports

**Example prompts:**
- "Test the fighter search functionality"
- "Capture screenshots of the homepage in desktop, tablet, and mobile viewports"
- "Generate a test that validates the favorites feature works correctly"
- "Check if all fighter cards render properly on the grid"
- "Test navigation from homepage to fighter detail page"

## Running Tests

### Via Claude Code (Recommended)

Simply ask Claude to run tests:
```
"Run the example homepage test and show me the results"
"Test the frontend on mobile and desktop viewports"
```

### Manual Test Execution

If you want to run tests manually:

```bash
# Install Playwright locally (if not already done)
npm install -D @playwright/test

# Run all tests
npx playwright test -c frontend/tests/e2e/playwright.config.ts

# Run specific test file
npx playwright test frontend/tests/e2e/specs/example-homepage.spec.ts -c frontend/tests/e2e/playwright.config.ts

# Run in headed mode (see browser)
npx playwright test --headed -c frontend/tests/e2e/playwright.config.ts

# Run with specific browser
npx playwright test --project=chromium -c frontend/tests/e2e/playwright.config.ts

# Open test report
npx playwright show-report
```

## Environment Variables

### Testing Against Different URLs

```bash
# Test against localhost (default)
npx playwright test -c frontend/tests/e2e/playwright.config.ts

# Test against Cloudflare tunnel
APP_URL=https://divine-floral-contributing-total.trycloudflare.com npx playwright test -c frontend/tests/e2e/playwright.config.ts

# Test against production
APP_URL=https://your-production-url.com npx playwright test -c frontend/tests/e2e/playwright.config.ts
```

## Example Workflows

### Workflow 1: Design Review
1. Make UI changes to your frontend
2. Take screenshot with `Shift+Cmd+Ctrl+4`
3. Paste into Claude Code with `Control+V`
4. Ask: "Review this UI - any suggestions for improvement?"

### Workflow 2: Feature Testing
1. Implement a new feature (e.g., fighter search)
2. Ask Claude: "Generate a Playwright test for the fighter search feature"
3. Claude writes and runs the test
4. Review screenshots and test results
5. Fix any issues Claude identifies
6. Save the generated test for regression testing

### Workflow 3: Responsive Design
1. Ask Claude: "Test the homepage on mobile, tablet, and desktop viewports"
2. Claude generates responsive tests automatically
3. Review screenshots for each breakpoint
4. Iterate on design issues

### Workflow 4: Bug Investigation
1. Screenshot the bug in your browser
2. Paste into Claude Code
3. Ask: "What's causing this layout issue?"
4. Claude analyzes and suggests fixes
5. Ask: "Generate a test that validates this is fixed"

## Tips & Best Practices

### For Manual Screenshots
- Use `Control+V` to paste (NOT `Command+V` on macOS)
- Include relevant context in the screenshot (full page or specific area)
- You can paste multiple screenshots in sequence
- Describe what you want analyzed: "This is the fighter grid - improve spacing"

### For Automated Testing
- Be specific about what to test: "Test the search feature" vs "Test the app"
- Ask for screenshots when you want visual verification
- Generated tests are saved - reuse them for regression testing
- Tests can run against localhost OR Cloudflare tunnel URLs

### Cloudflare Tunnel URLs
Your current tunnel URLs:
- **Frontend:** https://divine-floral-contributing-total.trycloudflare.com
- **Backend API:** https://direction-moving-bunch-remain.trycloudflare.com

**Note:** These URLs are temporary and will change if you restart the tunnels.

## Common Use Cases

### "Generate a test for [feature]"
Claude will write a complete Playwright test that:
- Navigates to your app
- Interacts with the UI
- Validates expected behavior
- Captures screenshots
- Reports pass/fail

### "Test responsive design"
Claude will:
- Test multiple viewport sizes
- Capture screenshots for each
- Identify layout issues
- Suggest improvements

### "Debug this error [screenshot]"
Claude will:
- Analyze the screenshot
- Identify the issue
- Suggest code fixes
- Optionally generate a test to prevent regression

### "Validate accessibility"
Claude can:
- Check for accessibility issues
- Test keyboard navigation
- Validate ARIA labels
- Test screen reader compatibility

## File Structure

```
UFC-pokedex/
├── .mcp.json                                  # MCP configuration (Playwright)
├── frontend/
│   └── tests/
│       └── e2e/
│           ├── playwright.config.ts           # Playwright settings
│           ├── specs/
│           │   └── example-homepage.spec.ts   # Example test suite
│           └── screenshots/                   # Generated screenshots
└── docs/guides/PLAYWRIGHT_GUIDE.md            # This file
```

## Troubleshooting

### "MCP server not found"
- Restart Claude Code session
- Check `.mcp.json` is in project root
- Run `npx @playwright/mcp@latest` manually to verify it works

### "Browser not found"
- Run `npx playwright install` to download browsers

### "Tests failing with CORS errors"
- Make sure backend CORS is configured to allow the frontend URL
- Check `.env` has correct `CORS_ALLOW_ORIGINS`

### "Screenshots not appearing"
- Check `frontend/tests/e2e/screenshots/` directory
- Ensure test has write permissions

## Next Steps

1. **Try it out!** Paste a screenshot or ask Claude to test a feature
2. **Generate tests** for your key user flows (search, favorites, detail pages)
3. **Build a test suite** by saving Claude's generated tests
4. **Integrate into CI/CD** by adding Playwright tests to your pipeline

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Playwright MCP Server](https://github.com/Ejb503/mcp-playwright-server)
- [Claude Code Docs](https://docs.claude.com/claude-code)
