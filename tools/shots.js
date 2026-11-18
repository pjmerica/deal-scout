// Real-browser check of BOTH live sites (Deal Scout + Card Scout) via headless Chrome/Edge over the
// DevTools protocol (no puppeteer needed; Node 18+ has fetch + WebSocket built in).
// It loads each site, clicks every tab and the Women filter, records JS exceptions/console errors,
// horizontal overflow and broken images, and saves desktop (1440px) + phone (390px) screenshots.
//
// Usage (Windows example; any Chromium works):
//   "C:/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --remote-debugging-port=9333 \
//       --user-data-dir=<temp dir> --hide-scrollbars about:blank &
//   node tools/shots.js 9333 <output dir>
//   DS_URL=file:///.../deal-scout/site/index.html CS_URL=file:///.../card-scout/site/index.html node tools/shots.js 9333 out
//   (for local builds, also start Chrome with --allow-file-access-from-files)
// Then look at the PNGs. Used on 2026-11-18 to find blank brand thumbnails, a tall phone header, etc.
const fs = require('fs');
const path = require('path');
const [, , port, outdir] = process.argv;
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  for (let i = 0; i < 40; i++) {
    try { await fetch(`http://127.0.0.1:${port}/json/version`); break; } catch { await sleep(250); }
  }
  const t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise(r => (ws.onopen = r));
  let id = 0;
  const pending = new Map();
  const errors = [];
  const waiters = [];
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
    if (m.method === 'Runtime.exceptionThrown') errors.push('EXCEPTION ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text).split('\n')[0]);
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errors.push('console.error ' + m.params.args.map(a => a.value || a.description).join(' ').slice(0, 200));
    for (const w of waiters.splice(0)) if (w.method === m.method) w.resolve(); else waiters.push(w);
  };
  const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  const waitFor = method => new Promise(resolve => waiters.push({ method, resolve }));
  await send('Page.enable'); await send('Runtime.enable');
  return { send, waitFor, errors, ws };
}

async function main() {
  const c = await connect();
  const { send } = c;
  const evalJS = async expr => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;
  const viewport = (w, h, mobile) => send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: mobile ? 2 : 1, mobile });
  const shot = async (name, h) => {
    const r = await send('Page.captureScreenshot', { format: 'png', ...(h ? { clip: { x: 0, y: 0, width: await evalJS('innerWidth'), height: h, scale: 1 }, captureBeyondViewport: true } : {}) });
    fs.writeFileSync(path.join(outdir, name + '.png'), Buffer.from(r.result.data, 'base64'));
  };
  const go = async url => { const l = c.waitFor('Page.loadEventFired'); await send('Page.navigate', { url: url + '?v=' + Date.now() }); await l; await sleep(2500); };
  const click = async sel => { await evalJS(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); if(!e) return 'missing'; e.click(); return 'ok';})()`); await sleep(900); };
  const metrics = async label => {
    const m = await evalJS(`(()=>({
      overflowX: document.documentElement.scrollWidth - innerWidth,
      items: document.querySelectorAll('#main .item, #main .brand, #main tbody tr').length,
      imgs: document.querySelectorAll('#main img').length,
      broken: [...document.querySelectorAll('#main img')].filter(i=>i.complete&&i.naturalWidth===0).length,
      tab: document.querySelector('#tabs [aria-selected=true]')?.textContent.trim(),
      h: document.documentElement.scrollHeight }))()`);
    console.log(label.padEnd(34), JSON.stringify(m));
    return m;
  };
  const report = [];

  // ---------------- Deal Scout ----------------
  await viewport(1440, 1100, false);
  await go(process.env.DS_URL || 'https://pjmerica.github.io/deal-scout/');
  await metrics('DS desktop Best');
  await shot('ds-1-best');
  await click('.seg button[data-g="Women\'s"]');
  await metrics('DS desktop Best (Women)');
  await shot('ds-2-best-women');
  await click('.seg button[data-g="all"]');
  for (const t of ['clothing', 'brands', 'bf', 'all', 'roundups', 'how']) {
    await click(`#tabs button[data-tab="${t}"]`);
    await metrics('DS desktop tab ' + t);
    if (t === 'clothing' || t === 'brands') await shot('ds-3-' + t);
  }
  await click('#tabs button[data-tab="best"]');
  await viewport(390, 844, true);
  await sleep(800);
  await metrics('DS mobile Best');
  await shot('ds-4-mobile-best');
  await click('#tabs button[data-tab="brands"]');
  await metrics('DS mobile Brands');
  await shot('ds-5-mobile-brands');
  report.push(['deal-scout', c.errors.splice(0)]);

  // ---------------- Card Scout ----------------
  await viewport(1440, 1100, false);
  await go(process.env.CS_URL || 'https://pjmerica.github.io/card-scout/');
  await metrics('CS desktop Offers');
  await shot('cs-1-offers');
  for (const t of ['news', 'cashback', 'playbook', 'how']) {
    await click(`#tabs button[data-tab="${t}"]`);
    await metrics('CS desktop tab ' + t);
    if (t === 'news' || t === 'cashback') await shot('cs-2-' + t);
  }
  await click('#tabs button[data-tab="offers"]');
  await viewport(390, 844, true);
  await sleep(800);
  await metrics('CS mobile Offers');
  await shot('cs-3-mobile-offers');
  report.push(['card-scout', c.errors.splice(0)]);

  for (const [site, errs] of report) console.log(`JS errors on ${site}:`, errs.length ? errs : 'none');
  c.ws.close();
}
main().catch(e => { console.error('DRIVER FAILED', e); process.exit(1); });
