// Capture harness (Playwright + Chromium). Runs the COPY of the Lacrydia app in the browser at the real device size
// (402 x 874 pt @3x = 1206 x 2622 px), in the app's own development guest mode (sample world). Nothing in the app is changed:
// remote demo photos/avatars (blocked in this sandbox) are answered from the app's own bundled photographs, by theme.
import { chromium } from '/opt/node-tools/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';

export const ROOT = '/home/user/Product-ad-blender/Lacrydia_Ad';
export const PHOTOS = `${ROOT}/assets/lacrydia/photos`;
const demo = JSON.parse(fs.readFileSync(`${ROOT}/capture/app/src/dev/demoPhotos.json`, 'utf8'));
const P = (...n) => n.map((i) => `${PHOTOS}/p${i}.jpg`);
const POOLS = {
  travel: P(2, 4, 3, 13, 1), italy: P(13, 8, 19, 21), rome: P(8, 13, 1), amalfi: P(3, 28, 13), japan: P(20, 11, 22, 10), tokyo: P(1, 20, 22),
  kyoto: P(13, 17, 20), stockholm: P(1, 8, 26), summer: P(3, 28, 26, 17), cars: P(7, 1), volvo: P(7, 3), bmw: P(7, 1), supercars: P(7),
  nightdrive: P(15, 12, 7), friends: P(9, 23, 24, 25), alex: P(23, 18, 27), marcus: P(18, 27, 9), emma: P(24, 25, 26),
  inspiration: P(14, 15, 12, 6), architecture: P(1, 8, 13), fashion: P(6, 14, 12, 18), design: P(14, 15, 19, 22), nature: P(16, 17, 28, 2),
  mountains: P(16, 4), ocean: P(3, 28, 26),
};
const FACES = P(23, 24, 25, 26);
const byFile = new Map();
for (const [theme, list] of Object.entries(demo)) list.forEach((e, i) => byFile.set(decodeURIComponent(e.n.split('?')[0]), [theme, i]));

export function localFor(url) {
  const u = new URL(url);
  if (u.hostname === 'i.pravatar.cc') return FACES[Number(u.searchParams.get('img') || 0) % FACES.length];
  const m = decodeURIComponent(u.pathname).match(/\/\d+px-(.+)$/);
  const hit = m && byFile.get(m[1]);
  if (hit) { const pool = POOLS[hit[0]] || POOLS.nature; return pool[hit[1] % pool.length]; }
  return null;
}

const BF_ARGS = ['--enable-begin-frame-control', '--run-all-compositor-stages-before-draw', '--disable-new-content-rendering-timeout', '--disable-threaded-animation', '--disable-threaded-scrolling', '--disable-checker-imaging', '--disable-image-animation-resync'];
export async function openApp({ video = false, size = { width: 402, height: 874 }, dpr = 3, bf = false } = {}) {
  const browser = await chromium.launch({ args: ['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl', '--hide-scrollbars',
    ...(bf ? [...BF_ARGS, `--force-device-scale-factor=${dpr}`, `--window-size=${size.width},${size.height}`] : [])] });
  // begin-frame mode needs the REAL device scale factor (flag) instead of emulation, otherwise screenshots come out at 1x
  const context = await browser.newContext({ ...(bf ? { viewport: null } : { viewport: size, deviceScaleFactor: dpr, isMobile: true, hasTouch: true }), colorScheme: 'dark',
    ...(video ? { recordVideo: { dir: `${ROOT}/capture/video`, size: { width: size.width * 2, height: size.height * 2 } } } : {}) });
  const page = await context.newPage();
  const misses = new Set(), errors = [];
  await page.route(/upload\.wikimedia\.org|i\.pravatar\.cc/, async (route) => {
    const f = localFor(route.request().url());
    if (f) return route.fulfill({ status: 200, contentType: 'image/jpeg', body: fs.readFileSync(f), headers: { 'access-control-allow-origin': '*' } });
    misses.add(route.request().url()); return route.abort();
  });
  // Skia on web needs CanvasKit BEFORE the app bundle runs (the native-first app does not load it itself): serve it from the local
  // canvaskit-wasm and release the original bundle only after initialisation. Harness-only; the app is untouched.
  const CK = `${ROOT}/capture/app/node_modules/canvaskit-wasm/bin`;
  await page.route('**/__ck/**', (route) => {
    const f = path.join(CK, new URL(route.request().url()).pathname.replace('/__ck/', ''));
    route.fulfill({ status: 200, contentType: f.endsWith('.wasm') ? 'application/wasm' : 'text/javascript', body: fs.readFileSync(f) });
  });
  await page.route((u) => u.origin === 'http://localhost:8099' && !u.pathname.includes('.') , async (route) => {
    if (route.request().resourceType() !== 'document') return route.continue();
    const res = await route.fetch(); let html = await res.text();
    const m = html.match(/<script[^>]+src="([^"]*entry\.bundle[^"]*)"[^>]*><\/script>/);
    if (!m) return route.fulfill({ response: res, body: html });
    html = html.replace(m[0], `<script src="/__ck/canvaskit.js"></script><script>CanvasKitInit({locateFile:function(f){return '/__ck/'+f}}).then(function(ck){window.CanvasKit=ck;var s=document.createElement('script');s.src=${JSON.stringify(m[1])};document.body.appendChild(s)})</script>`);
    return route.fulfill({ response: res, body: html });
  });
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 200)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  let bfApi = null;
  if (bf) {                                   // begin-frame mode: nothing renders unless we ask for a frame, so a pump keeps the page alive during setup
    const cdp = await context.newCDPSession(page);
    await cdp.send('HeadlessExperimental.enable');
    let pumping = false, loop = null;
    bfApi = { cdp,
      startPump() { if (pumping) return; pumping = true; loop = (async () => { while (pumping) { await cdp.send('HeadlessExperimental.beginFrame', {}).catch(() => {}); await new Promise((r) => setTimeout(r, 8)); } })(); },
      async stopPump() { pumping = false; await loop; } };
    bfApi.startPump();
  }
  return { browser, context, page, misses, errors, bf: bfApi };
}
export const shot = async (page, name) => { const f = `${ROOT}/capture/shots/${name}.png`; fs.mkdirSync(path.dirname(f), { recursive: true }); await page.screenshot({ path: f }); return f; };

// dev-only React warnings show a LogBox toast on web; hide it in captures (visual only, the app is untouched)
export async function hideLogBox(page) {
  // Expo's dev error toast/overlay is a shadow-DOM host (#error-toast) under <body>, outside the app root: hide it with CSS (visual only).
  await page.addStyleTag({ content: '#error-toast,#error-overlay,[id^="expo-dev"],[data-expo-overlay]{display:none!important;visibility:hidden!important} [role=tab] svg{position:relative;z-index:2}' }).catch(() => {});
}
export const clickText = async (page, re, opts = {}) => { await page.getByText(re, { exact: false }).first().click({ timeout: 20000, ...opts }); };
export const settle = async (page, ms = 1500) => { await page.waitForTimeout(ms); await hideLogBox(page); };
