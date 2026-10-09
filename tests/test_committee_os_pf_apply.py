"""Comité → 💼 Mi cartera → "🧪 Aplicar en simulación" (revisión 2026-10-09).

doApply(a, src) usaba `aid`, que solo existe en apply(aid): en 'use strict' lanzaba
`ReferenceError: aid is not defined` DESPUÉS de vender/comprar en la cartera simulada, así que no
aparecía "✓ aplicado en la simulación", no se refrescaba nada y el mismo botón seguía activo (un
segundo clic aplicaba el consejo otra vez). Se corre el JS REAL en node con un DOM falso mínimo.
La confirmación (KhipuToast.confirm, modo 'sim') sigue siendo obligatoria: sin "sí" no se toca nada.
"""
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')

JS = r"""
const ROOT = process.argv[1];
const CONFIRM = process.argv[2] === 'yes';
const errors = [];
process.on('unhandledRejection', e => errors.push(String((e && e.message) || e)));
process.on('uncaughtException', e => errors.push(String((e && e.message) || e)));
const store = { kh_investor_profile: JSON.stringify({ risk: 'moderado', involvement: 'informed', answers: {} }) };
global.localStorage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } };
const reg = {};
const byId = id => (/-css$/.test(id) ? (reg[id] || null) : (reg[id] = reg[id] || { id: id, value: '', style: {}, scrollIntoView() {} }));
global.document = { getElementById: byId, addEventListener() {}, hidden: false,
  createElement: () => ({ id: '', textContent: '' }), head: { appendChild(st) { reg[st.id] = st; } } };
global.window = { LANG: 'es', NODE_BY_ID: { Nvidia: { label: 'NVIDIA', mkt: 'NVDA' } }, MKT: { pos: {} } };
const _st = global.setTimeout; global.setTimeout = (f, ms) => (ms >= 9000 ? 0 : _st(f, ms));
const RES = { ok: true, health: { score: 64, verdict: 'Bien', tone: 'warn' }, kpis: { value_usd: 3870, vol_ann_pct: 41, max_drawdown_pct: -27, var95_1d_usd: 160 },
  profile: { label: 'Moderado', target_vol: 22, max_position: 25, max_sector: 40 },
  positions: [{ label: 'NVIDIA', symbol: 'NVDA', weight_pct: 100, risk_contrib_pct: 100, conviction: 30 }], sectors: [],
  actions: [{ id: 'a1', kind: 'reduce', priority: 1, label: 'NVIDIA', entity_id: 'Nvidia', symbol: 'NVDA', from_pct: 60, to_pct: 25, delta_usd: -900, why_es: 'Pesa mucho', why_en: 'Too big' }],
  coverage: { analyzed: 1, requested: 1, researched: 1, not_researched: [] }, excluded: [], disclaimer: 'IA, no asesoría.', source: 'Yahoo', as_of: '2026-10-09' };
global.fetch = (url) => {
  url = String(url); let b = {};
  if (url.includes('/api/committee/portfolio')) b = RES;
  else if (url.includes('kind=committee')) b = { reports: [] };
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(b) });
};
const calls = { sell: [], buy: [], confirm: [], refresh: 0 };
window.KhipuPortfolios = {
  _list: () => [{ id: 'p1', name: 'Mi tesis', positions: [{ nodeId: 'Nvidia', shares: 10, avgPrice: 100 }], cash: 0, startCash: 1000, createdAt: 1 }],
  _sell: (pf, id, sh) => { calls.sell.push([pf, id, sh]); return { ok: true }; },
  _buy: (pf, id, o) => { calls.buy.push([pf, id, o]); return { ok: true }; },
  refresh: () => { calls.refresh++; },
};
window.KhipuToast = { confirm: (o) => { calls.confirm.push(o); return Promise.resolve(CONFIRM); } };
require(ROOT + '/engine/pfcommittee.js');
const tick = () => new Promise(r => _st(r, 20));
let applyBtns = [];
const el = { innerHTML: '', scrollIntoView() {},
  querySelectorAll: sel => {
    if (sel !== '[data-apply]') return [];
    applyBtns = (el.innerHTML.match(/data-apply="([^"]+)"/g) || []).map(m => {
      const id = m.slice(12, -1); return { getAttribute: () => id, onclick: null };
    });
    return applyBtns;
  } };
(async () => {
  window.KhipuPortfolioCommittee.render(el);
  reg['pfc-run'].onclick(); await tick(); await tick();
  const before = el.innerHTML;
  const btn = applyBtns.filter(b => b.getAttribute() === 'a1')[0];
  btn.onclick(); await tick(); await tick();
  process.stdout.write(JSON.stringify({ before, after: el.innerHTML, calls, errors }));
})().catch(e => { process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""


def _run(confirm):
    if not NODE:
        pytest.skip('requiere node')
    r = subprocess.run([NODE, '-e', JS, ROOT, 'yes' if confirm else 'no'], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_aplicar_en_simulacion_marca_aplicado_sin_error():
    o = _run(True)
    assert 'data-apply="a1"' in o['before']
    assert o['errors'] == []                                         # antes: "aid is not defined"
    assert o['calls']['confirm'] and o['calls']['confirm'][0]['mode'] == 'sim'
    assert len(o['calls']['sell']) == 1 and o['calls']['sell'][0][0] == 'p1' and o['calls']['buy'] == []
    assert o['calls']['refresh'] == 1                                # la cartera simulada se refresca
    assert 'aplicado en la simulación' in o['after']
    assert 'data-apply="a1"' not in o['after']                       # no se puede aplicar dos veces


def test_sin_confirmar_no_se_toca_la_cartera():
    o = _run(False)
    assert o['errors'] == [] and o['calls']['confirm']
    assert o['calls']['sell'] == [] and o['calls']['buy'] == [] and o['calls']['refresh'] == 0
    assert 'data-apply="a1"' in o['after'] and 'aplicado en la simulación' not in o['after']
