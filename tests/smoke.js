// Smoke test: run the generated page's JS against the fresh data in a DOM stub.
//  1. render every tab x filter/gender variant (fails on throw, empty output, "undefined"/NaN)
//  2. CLICK every wired control (tabs, chips, segmented switches, buttons) so a broken
//     onclick handler fails CI too (e.g. 2026-11-18: tab clicks threw on a removed state field)
// Usage: node tests/smoke.js site/index.html
const fs = require('fs');
const vm = require('vm');

const file = process.argv[2] || 'site/index.html';
const html = fs.readFileSync(file, 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!scripts.length) throw new Error('no inline script found');

const els = {};
function el(id) {
  if (!els[id]) els[id] = { id, innerHTML: '', textContent: '', value: '', href: '', offsetTop: 0, style: {}, dataset: {},
    setAttribute() {}, getAttribute() { return null; }, focus() {}, setSelectionRange() {}, querySelectorAll: qsa };
  return els[id];
}
// Minimal querySelectorAll: builds stub elements (with dataset) from the rendered HTML,
// so handlers the page assigns can be clicked afterwards.
const lastLists = [];
function qsa(sel) {
  let src, attrRe;
  if (sel === '#tabs button') { src = el('tabs').innerHTML; attrRe = /data-tab="([^"]*)"/g; }
  else if (sel.includes('[data-g]')) { src = el('main').innerHTML; attrRe = /data-g="([^"]*)"/g; }
  else if (sel.includes('[data-v]')) { src = el('main').innerHTML; attrRe = /<button[^>]*data-v="([^"]*)"/g; }
  else if (sel === '.chip') { src = el('main').innerHTML; attrRe = /class="chip[^"]*" data-k="([^"]*)" data-v="([^"]*)"/g; }
  else return [];
  const out = [...src.matchAll(attrRe)].map(m => {
    const unesc = s => s.replace(/&#39;/g, "'").replace(/&amp;/g, '&').replace(/&quot;/g, '"');
    const ds = sel === '#tabs button' ? { tab: m[1] } : sel.includes('[data-g]') ? { g: unesc(m[1]) }
             : sel === '.chip' ? { k: m[1], v: unesc(m[2]) } : { v: unesc(m[1]) };
    return { dataset: ds, onclick: null };
  });
  lastLists.push(out);
  return out;
}
const document = { getElementById: el, querySelectorAll: qsa, addEventListener() {}, body: { appendChild() {} },
  documentElement: { setAttribute() {}, getAttribute() { return null; } } };
const ctx = { document, console, Date, Math, JSON, Set, Map, Object, Array, String, Number, RegExp, Error,
  localStorage: { getItem: () => null, setItem() {} }, matchMedia: () => ({ matches: false }),
  window: { scrollTo() {}, scrollY: 0 } };
ctx.__lastLists = lastLists;
ctx.__el = el;
vm.createContext(ctx);

const harness = `
;globalThis.__run = () => {
  const out = {};
  const check = (label) => {
    const h = document.getElementById('main').innerHTML;
    if (!h || h.length < 50) throw new Error('empty render: ' + label);
    const clean = h.replace(/data-[a-z]+="[^"]*"/g, '');
    const bad = clean.search(/undefined|NaN/);
    if (bad >= 0) throw new Error('"undefined"/NaN in ' + label + ': ' + clean.slice(Math.max(0, bad - 120), bad + 40));
    return h;
  };
  const reset = (tab) => Object.assign(state, {tab, q:'', sort:'score', minOff:0, maxPrice:0, newOnly:false, bestClothing:false,
      promoOnly:false, limit:60, gender:'all', inclUnlabeled:false, source:'', wcats:new Set(), wsub:new Set()});
  const variants = [{}, {sort:'off'}, {sort:'saved'}, {sort:'ends'}, {minOff:50}, {newOnly:true}, {q:'jacket'}, {bestClothing:true},
                    {promoOnly:true}, {gender:"Men's"}, {gender:"Women's"}, {gender:'Kids'},
                    {gender:"Women's", inclUnlabeled:true}, {gender:"Men's", bestClothing:true}, {gender:"Women's", promoOnly:true}];
  const counts = {};
  for (const t of TABS) for (const v of variants) {
    reset(t.id); Object.assign(state, v); render();
    const h = check(t.id + ' ' + JSON.stringify(v));
    out[t.id] = h.length;
    if (Object.keys(v).length <= 1 && (v.gender || !Object.keys(v).length) && ['best','clothing','brands'].includes(t.id))
      counts[t.id + ':' + (v.gender || 'all')] = (h.match(/class="(item|brand)[ "]/g) || []).length;
  }
  // Watching: each watched thing, each of its sub-filters, the price limit, and a 👀 badge jump
  let watchChecks = 0;
  for (const w of WATCH_LABELS) {
    reset('watch'); state.wcats = new Set([w]); render(); check('watch ' + w); watchChecks++;
    for (const s of (WATCH_SUBS[w] || [])) { state.wsub = new Set([s]); render(); check('watch ' + w + ' / ' + s); watchChecks++; }
    state.wsub = new Set(['__other__']); state.wcats.delete(w); pruneSubs();
    if (state.wsub.size) throw new Error('sub-filter left behind after unpicking ' + w);
  }
  for (const p of [25, 100]) { reset('watch'); state.maxPrice = p; render(); check('watch max $' + p); reset('all'); state.maxPrice = p; render(); check('all max $' + p); }
  if (WATCH_LABELS.length) { reset('best'); openWatch(WATCH_LABELS[0]); check('openWatch'); if (state.tab !== 'watch') throw new Error('badge jump did not open Watching'); }
  // "New for you": a visit long ago makes every watched deal new (badge on cards, "· N new" on the chips)
  if (WATCH_LABELS.length) {
    watchSeen = '2000-01-01T00:00'; reset('watch'); render(); const hw = check('watch new for you');
    if (!hw.includes('New for you') || !hw.includes(' new</small>')) throw new Error('"New for you" badge or chip count missing');
    watchSeen = null;
  }
  out.watchChecks = watchChecks;
  // a gender view may only be empty if the unfiltered view is empty too (e.g. --quick skips brand stores)
  for (const k of Object.keys(counts))
    if (!counts[k] && !k.endsWith('Kids') && counts[k.split(':')[0] + ':all']) throw new Error('empty gender view ' + k);

  // --- click everything ---
  let clicks = 0;
  const click = (b, label) => { if (b && typeof b.onclick === 'function') { b.onclick(); clicks++; check('after click ' + label); } };
  renderTabs();
  const tabButtons = __lastLists[__lastLists.length - 1].slice();
  for (const tb of tabButtons) {
    click(tb, 'tab ' + tb.dataset.tab);
    const before = __lastLists.length;
    render();  // re-render so this tab's controls are wired, then click each control list once
    const lists = __lastLists.slice(before).map(l => l.slice());
    for (const l of lists) for (const b of l) { click(b, tb.dataset.tab + ' ' + JSON.stringify(b.dataset)); reset(tb.dataset.tab); render(); }
    for (const id of ['newBtn', 'promoBtn', 'more', 'unlab', 'sort', 'minOff', 'maxPrice', 'source']) {
      const e = __el(id);
      if (typeof e.onclick === 'function') click(e, tb.dataset.tab + ' #' + id);
      if (typeof e.onchange === 'function') { e.value = id === 'sort' ? 'off' : id === 'minOff' || id === 'maxPrice' ? '50' : ''; e.onchange({target: e}); clicks++; check(tb.dataset.tab + ' change #' + id); }
      if (typeof e.oninput === 'function') { e.oninput({target: {value: 'a', selectionStart: 1}}); clicks++; check(tb.dataset.tab + ' input #' + id); }
      e.onclick = e.onchange = null;
    }
    const q = __el('q'); if (typeof q.oninput === 'function') { q.oninput({target: {value: 'shoe', selectionStart: 4}}); clicks++; check(tb.dataset.tab + ' search'); q.oninput = null; }
    reset(tb.dataset.tab);
  }
  out.genderCounts = counts;
  out.clicks = clicks;
  return out;
};`;
vm.runInContext(scripts[scripts.length - 1] + harness, ctx, { filename: 'page.js' });
const res = ctx.__run();
if (!el('stats').innerHTML.includes('stat')) throw new Error('header stats did not render');
if (res.clicks < 30) throw new Error('too few controls exercised: ' + res.clicks);
console.log('smoke OK:', JSON.stringify(res));
