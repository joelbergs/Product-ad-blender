import { chromium } from '/opt/node-tools/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const DPR = 2;
const browser = await chromium.launch({ args: ['--no-sandbox', '--enable-begin-frame-control', '--run-all-compositor-stages-before-draw', '--disable-new-content-rendering-timeout', '--disable-threaded-animation', '--disable-threaded-scrolling', '--disable-checker-imaging', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', `--force-device-scale-factor=${DPR}`, '--window-size=402,874', '--hide-scrollbars'] });
const context = await browser.newContext({ viewport: null, colorScheme: 'dark' });
const page = await context.newPage();
const cdp = await context.newCDPSession(page);
await cdp.send('HeadlessExperimental.enable');
await page.goto('http://localhost:8099/tour', { waitUntil: 'commit' }).catch(() => {});
for (let i = 0; i < 30; i++) { await cdp.send('HeadlessExperimental.beginFrame', {}); await new Promise((r) => setTimeout(r, 200)); }
console.log('inner', await page.evaluate(() => [innerWidth, innerHeight, devicePixelRatio]));
const res = await cdp.send('HeadlessExperimental.beginFrame', { screenshot: { format: 'png' } });
fs.writeFileSync('bf_test2.png', Buffer.from(res.screenshotData, 'base64'));
const sz = (await import('node:child_process')).execSync('python3 -I -c "from PIL import Image; print(Image.open(\'bf_test2.png\').size)"').toString();
console.log('screenshot size', sz.trim());
// mouse test
try { await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 100, y: 100 }); console.log('mouseMoved ok'); } catch (e) { console.log('mouseMoved err', String(e).slice(0, 100)); }
try { await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: 100, y: 100, button: 'left', buttons: 1, clickCount: 1 }); await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: 100, y: 100, button: 'left', buttons: 0, clickCount: 1 }); console.log('click ok'); } catch (e) { console.log('click err', String(e).slice(0, 100)); }
await browser.close();
