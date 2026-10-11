import { openApp, shot, clickText, settle } from './capture_lib.mjs';
const { browser, page, errors } = await openApp();
await page.goto('http://localhost:8099/', { waitUntil: 'load', timeout: 300000 });
await page.waitForTimeout(3000);
await clickText(page, /^Skip$/); await page.waitForTimeout(2000);
await clickText(page, /Look around without an account/); await page.waitForTimeout(7000);
await clickText(page, /^Start exploring$/).catch(() => {}); await page.waitForTimeout(2500);
// what does the LogBox toast look like in the DOM?
const lb = await page.evaluate(() => { const e = document.elementFromPoint(120, 840); const out = []; let n = e; for (let i = 0; i < 8 && n; i++, n = n.parentElement) out.push(n.tagName + '|' + (n.getAttribute('data-testid') || '') + '|' + (n.getAttribute('role') || '') + '|' + (n.className || '').toString().slice(0, 30) + '|' + getComputedStyle(n).position); return out; });
console.log('logbox chain:', lb);
const els = await page.evaluate(() => [...document.querySelectorAll('[role=tab],[role=button],[aria-label],a')].map((e) => ({ role: e.getAttribute('role'), label: e.getAttribute('aria-label'), text: (e.innerText || '').slice(0, 16), r: (({ x, y, width, height }) => [Math.round(x), Math.round(y), Math.round(width), Math.round(height)])(e.getBoundingClientRect()) })).filter((o) => o.r[2] > 0));
console.log(JSON.stringify(els.slice(0, 40)));
console.log('shot', await shot(page, 'x3_tree_clean'));
await browser.close();
