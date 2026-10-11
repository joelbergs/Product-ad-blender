import { openApp, shot, hideLogBox, clickText, settle } from './capture_lib.mjs';
const { browser, page, misses, errors } = await openApp();
await page.goto('http://localhost:8099/', { waitUntil: 'load', timeout: 300000 });
await settle(page, 3000);
await clickText(page, /^Skip$/); await settle(page, 2500);
console.log('after skip:', page.url()); console.log('shot', await shot(page, 'x2_after_skip'));
const btns = await page.locator('[role=button]').allInnerTexts(); console.log('buttons:', btns.slice(0, 10));
await clickText(page, /Look around without an account/); await settle(page, 6000);
console.log('guest url:', page.url()); console.log('shot', await shot(page, 'x2_guest_first'));
for (const tab of ['Home', 'Explore', 'Playlists', 'Profile', 'Tree']) {
  try { await page.getByText(new RegExp(`^${tab}$`)).first().click({ timeout: 8000 }); await settle(page, 4000); console.log(tab, await shot(page, `x2_tab_${tab.toLowerCase()}`), page.url()); }
  catch (e) { console.log('tab', tab, 'failed:', String(e).slice(0, 100)); }
}
console.log('missed images:', [...misses].slice(0, 5)); await browser.close();
