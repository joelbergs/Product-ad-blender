import { enterTree } from './flow.mjs'; import fs from 'node:fs';
const T0 = Date.now(); const log = (...a) => console.log(((Date.now() - T0) / 1000).toFixed(1) + 's', ...a);
const withTimeout = (p, ms, label) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error('TIMEOUT ' + label)), ms))]);
const ctx = await enterTree({ dpr: 2, bf: true }); const { browser, page, bf } = ctx; log('entered tree (pump running)');
const box = await page.locator('[aria-label^="Travel,"]').first().boundingBox(); log('box', JSON.stringify(box));
await page.waitForTimeout(1500); await bf.stopPump(); log('pump stopped');
const cdp = bf.cdp;
try {
  const r = await withTimeout(cdp.send('Emulation.setVirtualTimePolicy', { policy: 'pause', initialVirtualTime: 1700000000 }), 15000, 'pause'); log('virtual time paused', JSON.stringify(r));
  const base = r.virtualTimeTicksBase;
  for (let i = 0; i < 3; i++) {
    const done = new Promise((res) => cdp.once('Emulation.virtualTimeBudgetExpired', res));
    await cdp.send('Emulation.setVirtualTimePolicy', { policy: 'pauseIfNetworkFetchesPending', budget: 33.3 });
    await withTimeout(done, 15000, `budget expired step ${i}`); log('budget expired', i);
    const f = await withTimeout(cdp.send('HeadlessExperimental.beginFrame', { frameTimeTicks: base + (i + 1) * 33.3, interval: 33.3, screenshot: { format: 'jpeg', quality: 90 } }), 30000, 'beginFrame'); log('beginFrame ok', i, 'damage', f.hasDamage, f.screenshotData ? f.screenshotData.length : 0);
    if (f.screenshotData) fs.writeFileSync(`vt_test/t${i}.jpg`, Buffer.from(f.screenshotData, 'base64'));
  }
} catch (e) { log('ERROR', String(e).slice(0, 200)); }
await browser.close(); log('done');
