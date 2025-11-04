const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  console.log('Navigating to http://localhost:3000/events...');
  await page.goto('http://localhost:3000/events');

  console.log('Waiting 2 seconds for page to load...');
  await page.waitForTimeout(2000);

  console.log('Taking full-page screenshot...');
  await page.screenshot({
    path: '.playwright-mcp/events-page.png',
    fullPage: true
  });

  console.log('Screenshot saved to .playwright-mcp/events-page.png');

  await browser.close();
})();
