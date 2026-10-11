import { chromium } from '/opt/node-tools/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const browser = await chromium.launch({ args: ['--no-sandbox', '--enable-begin-frame-control', '--run-all-compositor-stages-before-draw', '--disable-new-content-rendering-timeout', '--disable-threaded-animation', '--disable-threaded-scrolling', '--disable-checker-imaging', '--disable-image-animation-resync', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
console.log('browser', browser.version());
const context = await browser.newContext({ viewport: { width: 402, height: 874 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true, colorScheme: 'dark' });
const page = await context.newPage();
const cdp = await context.newCDPSession(page);
try {
  const r = await cdp.send('HeadlessExperimental.enable'); console.log('HeadlessExperimental.enable ok');
} catch (e) { console.log('HeadlessExperimental unsupported:', String(e).slice(0, 120)); }
await page.goto('http://localhost:8099/', { waitUntil: 'commit', timeout: 120000 }).catch((e) => console.log('goto:', String(e).slice(0, 80)));
await new Promise((r) => setTimeout(r, 6000));
try {
  const res = await cdp.send('HeadlessExperimental.beginFrame', { screenshot: { format: 'jpeg', quality: 80 } });
  console.log('beginFrame ok, hasDamage', res.hasDamage, 'screenshot bytes', res.screenshotData ? res.screenshotData.length : 0);
  if (res.screenshotData) fs.writeFileSync('bf_test.jpg', Buffer.from(res.screenshotData, 'base64'));
} catch (e) { console.log('beginFrame failed:', String(e).slice(0, 160)); }
await browser.close();
