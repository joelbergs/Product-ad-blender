import { enterTree } from './flow.mjs'; import { shot, hideLogBox } from './capture_lib.mjs';
const { browser, page } = await enterTree();
const html = await page.evaluate(() => { const t = document.querySelector('[role=tab][aria-selected=true]') || document.querySelector('[role=tab]'); return [t.getAttribute('aria-label'), t.getAttribute('aria-selected'), t.outerHTML.slice(0, 900)]; });
console.log(JSON.stringify(html));
const prof = await page.evaluate(() => { const t = document.querySelector('[role=tab][aria-label="Profile"]'); const r = t.getBoundingClientRect(); const e = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return { rect: [r.x, r.y, r.width, r.height], atPoint: e && (e.getAttribute('aria-label') || e.tagName), pe: getComputedStyle(t).pointerEvents }; });
console.log('profile tab:', JSON.stringify(prof));
await page.locator('[aria-label="Profile"]').first().click({ force: true, timeout: 8000 }).then(() => console.log('forced click ok')).catch((e) => console.log('force failed', String(e).slice(0, 80)));
await page.waitForTimeout(4000); await hideLogBox(page); console.log(page.url(), await shot(page, 'tab_profile_v1'));
await browser.close();
