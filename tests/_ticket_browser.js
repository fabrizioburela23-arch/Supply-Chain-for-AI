let chromium; try { ({ chromium } = require('playwright')); } catch (e) { process.exit(77); }
const assert = require('assert');
const fs = require('fs');
(async () => {
  const b = await chromium.launch(); const pg = await b.newPage();
  const errs = []; pg.on('pageerror', e => errs.push(String(e))); pg.on('request', r => { if (/api\/trade|alpaca/.test(r.url())) errs.push('REQ ' + r.url()); });
  await pg.route('http://t.test/', r => r.fulfill({contentType:'text/html', body:'<html><body></body></html>'})); await pg.goto('http://t.test/'); await pg.setContent(`<div id=tp><span id=tp-ticker-badge>NVDA</span><button id=tp-side-buy-btn class="active"></button><button id=tp-side-sell-btn></button>
  <select id=tp-order-type><option value=market>m</option><option value=limit>l</option></select><select id=tp-tif><option>day</option></select>
  <input id=tp-qty value=10><input id=tp-limit-price value=200><div id=tp-order-status></div><button id=tp-submit-btn data-tpt=submit>ENVIAR ORDEN</button></div>`);
  await pg.evaluate(() => {
    window.LANG = 'es'; window.__sent = 0;
    window.MKT = { pos: { NVDA_ID: { sh: 5, bp: 100 } }, quotes: { NVDA: { close: 180, prev: 178, src: 'finnhub', as_of: new Date().toISOString(), live: 180 } } };
    window.NODE_BY_ID = { NVDA_ID: { ticker: 'NVDA' } }; window.quotePx = q => q.live || q.close; window.quoteIsLive = q => !!q.live;
    window.openTradePanelFn = function () { window.__orig = 1; }; window.submitTradePanelOrder = function () { window.__sent++; }; window._tpRelabel = function () { document.getElementById('tp-submit-btn').textContent = 'ENVIAR ORDEN'; };
    window.savePos = function () { window.__saved = JSON.stringify(window.MKT.pos); };
  });
  await pg.addScriptTag({ content: fs.readFileSync(require('path').join(__dirname, '..', 'engine', 'ticket.js'), 'utf8') });
  const out = {};
  await pg.evaluate(() => window.openTradePanelFn('NVDA_ID', 'NVDA', 'Nvidia'));
  out.sentBroker = await pg.evaluate(() => { submitTradePanelOrder(); return window.__sent; });
  await pg.selectOption('#tp-mode-sel', 'ticket');
  out.btn = await pg.textContent('#tp-submit-btn');
  await pg.fill('#tp-qty', '10'); await pg.selectOption('#tp-order-type', 'limit'); await pg.fill('#tp-limit-price', '200');
  await pg.evaluate(() => submitTradePanelOrder());
  out.sentAfter = await pg.evaluate(() => window.__sent);
  out.card = await pg.textContent('#tp-ticket-card');
  await pg.click('text=Ya lo ejecuté'); const ins = await pg.$$('#tp-ticket-rec input'); await ins[0].fill('10'); await ins[1].fill('181.5');
  await pg.click('text=Guardar en mi cartera');
  out.saved = await pg.evaluate(() => window.__saved); out.status = await pg.textContent('#tp-order-status');
  await pg.selectOption('#tp-mode-sel', 'broker'); out.btnBack = await pg.textContent('#tp-submit-btn');
  await b.close();
  assert.deepStrictEqual(errs, []);
  assert.strictEqual(out.sentBroker, 1);            // modo broker: llama a la función original
  assert.strictEqual(out.sentAfter, 1);             // modo ticket: NO la llama
  assert.strictEqual(out.btn, 'CREAR TICKET');
  assert.ok(/NO ENVIADO/.test(out.card) && /ENCIMA/.test(out.card));
  assert.strictEqual(JSON.parse(out.saved).NVDA_ID.sh, 15);
  assert.ok(Math.abs(JSON.parse(out.saved).NVDA_ID.bp - 154.3333) < 0.01);
  assert.strictEqual(out.btnBack, 'ENVIAR ORDEN');
})();
