// Shared flow: open the app, skip the tour, enter the app's own dev guest mode, dismiss the coach card.
import { openApp, hideLogBox, clickText } from './capture_lib.mjs';
export async function enterTree(opts = {}) {
  const ctx = await openApp(opts); const { page } = ctx;
  await page.goto('http://localhost:8099/', { waitUntil: 'load', timeout: 300000 }); await page.waitForTimeout(2500);
  await clickText(page, /^Skip$/); await page.waitForTimeout(1800);
  await clickText(page, /Look around without an account/); await page.waitForTimeout(6500);
  await clickText(page, /^Start exploring$/).catch(() => {}); await page.waitForTimeout(1500);
  await hideLogBox(page); await page.waitForTimeout(800); await hideLogBox(page);
  return ctx;
}
