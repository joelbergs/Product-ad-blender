import { enterTree } from './flow.mjs'; import { shot, hideLogBox } from './capture_lib.mjs';
const { browser, page } = await enterTree({ dpr: 1 });
const labels = async () => page.evaluate(() => [...new Set([...document.querySelectorAll('[aria-label],[role=button]')].filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.y < 874 && r.y > -10; }).map((e) => (e.getAttribute('aria-label') || e.innerText || '').replace(/\n/g, ' ').slice(0, 44)).filter(Boolean))].slice(0, 36));
const step = async (name, fn, wait = 3500) => { try { await fn(); } catch (e) { console.log('  step failed:', String(e).split('\n')[0].slice(0, 90)); } await page.waitForTimeout(wait); await hideLogBox(page); await shot(page, name); console.log(name, page.url().replace('http://localhost:8099', ''), '\n   ', JSON.stringify(await labels())); };
await step('e01_travel', () => page.locator('[aria-label^="Travel,"]').first().click({ force: true }), 4500);
await step('e02_open', () => page.getByText('Open', { exact: true }).first().click({ force: true }));
await step('e03_first_photo', async () => { const r = await page.evaluate(() => { const imgs = [...document.querySelectorAll('img, [style*="background-image"]')].map((e) => e.getBoundingClientRect()).filter((r) => r.width > 60 && r.height > 60 && r.y > 120 && r.y < 700); return imgs[0] ? { x: imgs[0].x + imgs[0].width / 2, y: imgs[0].y + imgs[0].height / 2 } : null; }); console.log('  first photo at', JSON.stringify(r)); if (r) await page.mouse.click(r.x, r.y); });
await step('e04_after_photo_tap', async () => {});
await browser.close();
