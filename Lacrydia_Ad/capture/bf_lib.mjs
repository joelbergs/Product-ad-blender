// Deterministic frame recorder: virtual clock frozen, each frame = advance 1/30 s of virtual time + one explicit BeginFrame with screenshot.
import fs from 'node:fs';
export async function makeRecorder({ cdp }, { fps = 30, quality = 93, format = 'jpeg' } = {}) {
  const step = 1000 / fps;
  const { virtualTimeTicksBase } = await cdp.send('Emulation.setVirtualTimePolicy', { policy: 'pause', initialVirtualTime: 1700000000 });
  let elapsed = 0;
  const advance = (ms) => new Promise((res, rej) => {
    const to = setTimeout(() => rej(new Error('virtual time step timed out')), 120000);
    cdp.once('Emulation.virtualTimeBudgetExpired', () => { clearTimeout(to); res(); });
    cdp.send('Emulation.setVirtualTimePolicy', { policy: 'pauseIfNetworkFetchesPending', budget: ms });
  });
  const frame = async (file) => {                                   // one video frame
    await advance(step); elapsed += step;
    const r = await cdp.send('HeadlessExperimental.beginFrame', { frameTimeTicks: virtualTimeTicksBase + elapsed, interval: step, screenshot: { format, quality } });
    if (file && r.screenshotData) fs.writeFileSync(file, Buffer.from(r.screenshotData, 'base64'));
    return !!r.hasDamage;
  };
  const idle = async (n) => { for (let i = 0; i < n; i++) await frame(null); };   // advance time/animations without saving
  const mouse = (type, x, y, buttons = 1) => cdp.send('Input.dispatchMouseEvent',
    type === 'mouseMoved' ? (buttons ? { type, x, y, button: 'left', buttons } : { type, x, y }) : { type, x, y, button: 'left', buttons: type === 'mousePressed' ? 1 : 0, clickCount: 1 });
  // Input events are fire-and-forget while the clock is frozen (the page only handles them once time advances), awaited at the end.
  const tap = async (x, y, holdFrames = 2, nextFile = null) => {   // nextFile() -> path: the tap frames are saved too (no gaps in the sequence)
    const ps = [mouse('mouseMoved', x, y, 0), mouse('mousePressed', x, y)];
    for (let i = 0; i < holdFrames; i++) await frame(nextFile ? nextFile() : null);
    ps.push(mouse('mouseReleased', x, y, 0)); await frame(nextFile ? nextFile() : null); await Promise.all(ps);
  };
  const drag = async (x0, y0, x1, y1, frames, onFrame) => {
    const ps = [mouse('mouseMoved', x0, y0, 0), mouse('mousePressed', x0, y0)]; await frame(null);
    for (let i = 1; i <= frames; i++) { const k = i / frames, e = k * k * (3 - 2 * k); ps.push(mouse('mouseMoved', x0 + (x1 - x0) * e, y0 + (y1 - y0) * e)); await frame(onFrame ? await onFrame(i) : null); }
    ps.push(mouse('mouseReleased', x1, y1, 0)); await frame(null); await Promise.all(ps);
  };
  return { frame, idle, tap, drag, mouse, advance, get elapsed() { return elapsed; } };
}
