import { enterTree } from './flow.mjs'; import { shot, hideLogBox } from './capture_lib.mjs';
const { browser, page } = await enterTree();
const labels = async () => page.evaluate(() => [...document.querySelectorAll('[role],[aria-label],a')].map((e) => ({ role: e.getAttribute('role'), label: e.getAttribute('aria-label'), r: (({x,y,width,height}) => [Math.round(x),Math.round(y),Math.round(width),Math.round(height)])(e.getBoundingClientRect()) })).filter((o) => o.r[2] > 0 && o.r[1] > 700 && o.r[1] < 900));
console.log('bottom area:', JSON.stringify(await labels()));
for (const name of ['Home', 'Explore', 'Playlists', 'Profile', 'Tree']) {
  try {
    await page.locator(`[aria-label="${name}"]`).first().click({ timeout: 6000 }); await page.waitForTimeout(3500); await hideLogBox(page);
    console.log(name, page.url().replace('http://localhost:8099', ''), await shot(page, `tab_${name.toLowerCase()}_v1`));
  } catch (e) { console.log(name, 'FAILED', String(e).split('\n')[0].slice(0, 100)); }
}
await browser.close();
