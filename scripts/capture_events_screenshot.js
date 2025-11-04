const { chromium } = require('playwright');

async function captureScreenshot() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('Navigating to http://localhost:3000/events...');
  await page.goto('http://localhost:3000/events');

  console.log('Waiting 5 seconds for data to load...');
  await page.waitForTimeout(5000);

  console.log('Reloading the page...');
  await page.reload();

  console.log('Waiting another 3 seconds...');
  await page.waitForTimeout(3000);

  console.log('Taking full-page screenshot...');
  await page.screenshot({
    path: '.playwright-mcp/events-final-with-data.png',
    fullPage: true
  });

  console.log('Screenshot saved to .playwright-mcp/events-final-with-data.png');

  await browser.close();
}

captureScreenshot().catch(console.error);
