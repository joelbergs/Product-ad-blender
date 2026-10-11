import { enterTree } from './flow.mjs';
const { browser, page } = await enterTree();
const out = await page.evaluate(() => [...document.querySelectorAll('[role=tab]')].map((t) => [t.getAttribute('aria-label'), t.outerHTML.replace(/class="[^"]*"/g, '').slice(0, 700)]));
console.log(JSON.stringify(out[2]));
await browser.close();
