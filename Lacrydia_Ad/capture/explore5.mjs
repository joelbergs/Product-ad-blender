import { enterTree } from './flow.mjs';
const { browser, page } = await enterTree();
const info = await page.evaluate(() => [...document.body.children].map((n) => ({ tag: n.tagName, id: n.id, pos: getComputedStyle(n).position, disp: getComputedStyle(n).display, kids: n.children.length, text: (n.innerText || '').slice(0, 60).replace(/\n/g, '|'), rect: (({x,y,width,height}) => [Math.round(x),Math.round(y),Math.round(width),Math.round(height)])(n.getBoundingClientRect()) })));
console.log(JSON.stringify(info, null, 0));
const at = await page.evaluate(() => { const e = document.elementFromPoint(120, 840); return e ? [e.tagName, (e.innerText || '').slice(0, 40), e.parentElement && e.parentElement.tagName, e.getRootNode() === document ? 'document' : 'shadow'] : null; });
console.log('at point:', at);
await browser.close();
