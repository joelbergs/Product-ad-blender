import { enterTree } from './flow.mjs'; import { hideLogBox } from './capture_lib.mjs'; import { makeStepper } from './vt_lib.mjs';
import fs from 'node:fs'; import { execSync } from 'node:child_process';
const { browser, context, page } = await enterTree({ dpr: 2 });
const box = await page.locator('[aria-label^="Travel,"]').first().boundingBox();
const S = await makeStepper(context, page);
fs.rmSync('vt_test', { recursive: true, force: true }); fs.mkdirSync('vt_test', { recursive: true });
const t0 = Date.now();
await S.grab('vt_test/f000.jpg');
await S.tapAt(box.x + box.width / 2, box.y + box.height / 2);
for (let i = 1; i <= 60; i++) { await S.advance(1000 / 30); await S.grab(`vt_test/f${String(i).padStart(3, '0')}.jpg`); }
console.log(`60 frames in ${((Date.now() - t0) / 1000).toFixed(1)} s real time`);
await browser.close();
