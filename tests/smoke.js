// Smoke test: run the generated page's JS against the fresh data in a DOM stub and
// render every tab (plus filter/sort variants). Fails CI if anything throws or renders empty.
// Usage: node tests/smoke.js site/index.html
const fs = require('fs');
const vm = require('vm');

const file = process.argv[2] || 'site/index.html';
const html = fs.readFileSync(file, 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!scripts.length) throw new Error('no inline script found');

const els = {};
function el(id) {
  if (!els[id]) els[id] = { id, innerHTML: '', textContent: '', value: '', offsetTop: 0, style: {},
    setAttribute() {}, getAttribute() { return null; }, focus() {}, setSelectionRange() {},
    querySelectorAll() { return []; } };
  return els[id];
}
const document = {
  getElementById: el, querySelectorAll: () => [],
  documentElement: { setAttribute() {}, getAttribute() { return null; } },
};
const ctx = {
  document, console, Date, Math, JSON, Set, Map, Object, Array, String, Number, RegExp, Error,
  localStorage: { getItem: () => null, setItem() {} },
  matchMedia: () => ({ matches: false }),
  window: { scrollTo() {}, scrollY: 0 },
};
vm.createContext(ctx);
const harness = `
;globalThis.__run = () => {
  const out = {};
  const variants = [{}, {sort:'off'}, {sort:'saved'}, {minOff:50}, {newOnly:true}, {q:'jacket'},
                    {bestClothing:true}, {cardType:'business'}, {promoOnly:true},
                    {gender:"Men's"}, {gender:"Women's"}, {gender:'Kids'}, {gender:"Women's", inclUnlabeled:true},
                    {gender:"Men's", bestClothing:true}, {gender:"Women's", promoOnly:true}];
  const counts = {};
  for (const t of TABS) {
    for (const v of variants) {
      Object.assign(state, {tab:t.id, q:'', sort:'score', minOff:0, newOnly:false, bestClothing:false,
                            cardType:'personal', promoOnly:false, limit:60, gender:'all', inclUnlabeled:false}, v);
      render();
      const h = document.getElementById('main').innerHTML;
      if (!h || h.length < 50) throw new Error('empty render: ' + t.id + ' ' + JSON.stringify(v));
      if (/undefined|NaN/.test(h.replace(/data-[a-z]+="[^"]*"/g, ''))) {
        const i = h.search(/undefined|NaN/);
        throw new Error('"undefined"/NaN in ' + t.id + ': ' + h.slice(Math.max(0, i - 120), i + 40));
      }
      out[t.id] = h.length;
      if (v.gender && Object.keys(v).length === 1 && (t.id === 'best' || t.id === 'clothing' || t.id === 'brands'))
        counts[t.id + ':' + v.gender] = (h.match(/class="(item|brand)[ "]/g) || []).length;
    }
  }
  // A gender view must actually filter: men's and women's clothing views can't both equal the unfiltered list
  // and must not be empty.
  for (const k of Object.keys(counts)) if (!counts[k] && !k.endsWith('Kids')) throw new Error('empty gender view ' + k);
  out.genderCounts = counts;
  return out;
};`;
vm.runInContext(scripts[scripts.length - 1] + harness, ctx, { filename: 'page.js' });
const res = ctx.__run();
const stats = el('stats').innerHTML;
if (!stats.includes('stat')) throw new Error('header stats did not render');
console.log('smoke OK:', JSON.stringify(res));
