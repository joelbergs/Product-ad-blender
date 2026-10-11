// Deterministic capture: freeze Chromium's clock (virtual time), advance exactly 1/30 s per frame, screenshot each step (CDP).
// Input events are injected through CDP while the clock is frozen, so they do not depend on timers.
import fs from 'node:fs';
export async function makeStepper(context, page, { quality = 92, format = 'jpeg' } = {}) {
  const cdp = await context.newCDPSession(page);
  await cdp.send('Emulation.setVirtualTimePolicy', { policy: 'pause' });
  const advance = (ms) => new Promise((res, rej) => {
    const to = setTimeout(() => rej(new Error('virtual time step timed out')), 60000);
    cdp.once('Emulation.virtualTimeBudgetExpired', () => { clearTimeout(to); res(); });
    cdp.send('Emulation.setVirtualTimePolicy', { policy: 'pauseIfNetworkFetchesPending', budget: ms });
  });
  const grab = async (file) => { const r = await cdp.send('Page.captureScreenshot', { format, quality, fromSurface: true }); fs.writeFileSync(file, Buffer.from(r.data, 'base64')); };
  const mouse = (type, x, y) => cdp.send('Input.dispatchMouseEvent', { type, x, y, button: 'left', buttons: type === 'mouseReleased' ? 0 : 1, clickCount: 1, pointerType: 'mouse' });
  const tapAt = async (x, y, holdMs = 60) => { await mouse('mouseMoved', x, y); await mouse('mousePressed', x, y); await advance(holdMs); await mouse('mouseReleased', x, y); };
  const dragTo = async (x0, y0, x1, y1, ms, step = 1000 / 30, onFrame) => { await mouse('mouseMoved', x0, y0); await mouse('mousePressed', x0, y0); const n = Math.max(1, Math.round(ms / step)); for (let i = 1; i <= n; i++) { const k = i / n; await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: x0 + (x1 - x0) * k, y: y0 + (y1 - y0) * k, button: 'left', buttons: 1 }); await advance(step); if (onFrame) await onFrame(i); } await mouse('mouseReleased', x1, y1); };
  const resume = () => cdp.send('Emulation.setVirtualTimePolicy', { policy: 'advance' });
  return { cdp, advance, grab, mouse, tapAt, dragTo, resume };
}
