"""Carteras de práctica (engine/portfolios.js) y Reporte de riesgo (engine/riskreport.js) con la piel de
Khipus OS (2026-10-10).

Antes pintaban con la paleta oscura vieja fija (#0B1222, #E8EDFB, #00E0FF, Inter…): la Cabina tenía que
forzarlas a una "isla oscura" (LEGACY_DARK) y en el tema claro desentonaban. Ahora todo color es un token
--os-* con el valor OSCURO de respaldo: var(--x, respaldo), en claro y en oscuro.

· Estático: ningún color hex/rgba suelto fuera de un respaldo var(--x, …), de la paleta de impresión
  (papel blanco) o del mapa de respaldos que lee Chart.js; nada de la paleta ni de la letra viejas;
  API pública, ids, clases y data-* que usan otros módulos siguen ahí.
· Dinámico (node + DOM mínimo): se pintan las pantallas reales (cartera con posiciones, compra, nueva
  cartera, asistente, propuesta, chat, vacío; riesgo inicio/resultado/detalle/IA, Vega) y el HTML y el CSS
  resultantes cumplen lo mismo; el contenedor toma .kos-themed solo FUERA de Khipus OS.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
PF, RR = 'engine/portfolios.js', 'engine/riskreport.js'
FILES = [PF, RR]
LEGACY = ['#0B1222', '#06090F', '#0E1426', '#E8EDFB', '#00E0FF', '#C9D4EC', '#9BA6C4', '#9AA6C4', '#7C87A3',
          '#2BE38B', '#FF4D6A', '#FF6B85', '#FF9DB0', '#FF8FA3', '#FFB300', '#FFD27A', '#FFC400', '#fbbf24',
          '#f59e0b', '#5FC6E8', '#4A7BFF', '#04121C', 'rgba(122,158,255', 'rgba(20,26,44', 'rgba(11,18,34',
          'rgba(21,28,45', 'rgba(14,20,38', 'rgba(0,224,255', 'rgba(3,6,12', 'rgba(255,77,106', 'rgba(43,227,139']
COLOR = re.compile(r'(?<![&\w])#[0-9a-fA-F]{3,8}\b|rgba?\(')
OLD_FONT = re.compile(r'\bInter\b|Fraunces')


def _src(rel):
    return open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _var_fallback_spans(text):
    """[(coma, cierre)] de cada var(--x, respaldo): lo que está entre la coma y el ')' es respaldo."""
    spans = []
    for m in re.finditer(r'var\(\s*--[\w-]+\s*,', text):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            depth += {'(': 1, ')': -1}.get(text[i], 0)
            i += 1
        spans.append((m.end() - 1, i))
    return spans


def stray_colors(text):
    """Colores que NO son respaldo de var(), ni definición de token (--x:#…), ni una línea marcada como
    paleta de impresión / mapa de respaldos de Chart.js."""
    spans = _var_fallback_spans(text)
    bad = []
    for m in COLOR.finditer(text):
        p = m.start()
        if any(a < p < b for a, b in spans):
            continue
        before = text[max(0, p - 200):p]
        if re.search(r"--[\w-]+:[^;{}'\"]*$", before):             # --os-ink:#111216 (paleta de impresión)
            continue
        line_end = text.find('\n', p)
        line = text[text.rfind('\n', 0, p) + 1:line_end if line_end >= 0 else len(text)]
        if 'token-fallback' in line or 'print-palette' in line:
            continue
        bad.append(text[max(0, p - 40):p + 12].replace('\n', ' '))
    return bad


def strip_mascots(html):
    # las burbujas de engine/mascot.js llevan su degradado propio en atributos SVG (no es de estos módulos)
    return re.sub(r'<span class="km[^"]*"[^>]*>[\s\S]*?</svg></span>', '', html)


def test_el_detector_si_detecta_colores_sueltos():
    assert stray_colors('style="color:#E8EDFB"') and stray_colors('background:rgba(0,224,255,.12)')
    assert not stray_colors('color:var(--os-ink,#F2F2F5);box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4))')
    assert not stray_colors("body{--os-ink:#111216;--os-line:rgba(17,18,22,.14)}")
    assert stray_colors("var DARK = { bad: '#f06565' };") and not stray_colors("var DARK = { bad: '#f06565' };   // token-fallback")


@pytest.mark.parametrize('rel', FILES)
def test_sin_paleta_vieja_ni_colores_fijos(rel):
    src = _src(rel)
    assert stray_colors(src) == []
    low = src.lower()
    assert [c for c in LEGACY if c.lower() in low] == []           # ni siquiera como respaldo
    assert not OLD_FONT.search(src)                                 # letra de Khipus OS (--os-font), no Inter/Fraunces
    assert 'var(--os-font,' in src
    # foco de teclado visible y movimiento reducido
    assert 'outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px' in src
    assert 'prefers-reduced-motion' in src


def test_carteras_api_publica_ids_y_tema():
    s = _src(PF)
    api = s[s.index('window.KhipuPortfolios = {'):]
    for k in ('mount:', 'refresh:', '_list: loadAll', '_buy: buy', '_sell: sell', '_stats: pfStats', '_priceOf: priceOf'):
        assert k in api, k
    for i in ('kpf-select', 'kpf-rename', 'kpf-delete', 'kpf-new', 'kpf-new2', 'kpf-refresh', 'kpf-risk', 'kpf-nn', 'kpf-nc',
              'kpf-create', 'kpf-cancel', 'kpf-search', 'kpf-search-clear', 'kpf-chat', 'kpf-ask', 'kpf-ask-go', 'kpf-usepf',
              'kpf-amt', 'kpf-excl', 'kpf-prop-go'):
        assert ('id="%s"' % i) in s or ("'%s'" % i) in s, i
    for c in ('kpf-buyopen', 'kpf-buy-usd', 'kpf-buy-sh', 'kpf-buy-go', 'kpf-sell-sh', 'kpf-sell-go', 'kpf-tab', 'kpf-tab-ai',
              'kpf-mode', 'kpf-opt', 'kpf-theme', 'kpf-sugg', 'kpf-create', 'kpf-goto', 'kpf-riskgo', 'kpf-hide-sm'):
        assert c in s, c
    for k in ("'kh_portfolios'", "'kh_pf_active'", "'kh_pf_view'"):
        assert k in s
    # tema: dentro de una ventana hereda los tokens de #bcp-ov; fuera se marca .kos-themed
    assert "_container.closest('#bcp-ov')" in s and "toggle('kos-themed', !inOS)" in s
    # se adapta al ANCHO DE LA VENTANA (flancos ~400 px), no solo al de la pantalla
    assert 'container:kpf/inline-size' in s and '@container kpf (max-width:600px)' in s
    # el asistente es un AGENTE → mascota de Khipus OS
    assert 'window.KhipuMascot' in s and "PF_AGENT = 'portfolio'" in s
    # bilingüe: textos nuevos en los dos idiomas
    for es, en in (('Cartera activa', 'Active portfolio'), ('Acciones a vender', 'Shares to sell'), ('Tu pregunta', 'Your question')):
        assert "T('%s', '%s')" % (es, en) in s


def test_riesgo_api_publica_ids_y_tema():
    s = _src(RR)
    api = s[s.index('window.KhipuRisk = {'):]
    for k in ('open: function', 'close: close', 'isOpen: isOpen'):
        assert k in api, k
    for i in ('krr-ov', 'krr-css', 'krr-hist', 'krr-amt', 'krr-q', 'krr-sugg', 'krr-man', 'kv-q', 'kv-sugg', 'kv-n'):
        assert i in s, i
    for a in ('close', 'lang', 'print', 'runquick', 'qclear', 'adv', 'runman', 'back', 'retry', 'detail', 'vdetail', 'ai',
              'vminus', 'vplus', 'addopt', 'runvega'):
        assert ("data-act=\"%s\"" % a) in s or ("a === '%s'" % a) in s, a
    for e in ("'/api/portfolio/risk_report'", "'/api/portfolio/vega_report'", "'/api/options/chain/'", "'kh_options'", "'kh_risk_quick'"):
        assert e in s, e
    assert "ov.className = 'kos-themed'" in s                       # overlay fuera de #bcp-ov con los tokens del OS
    # semáforo: el color sale de la clase (.light.low/.mid/.high → tokens), no de un hex en level()
    lv = s[s.index('function level(r)'):s.index('function avgCorr')]
    assert 'c:' not in lv and "k: 'high'" in lv
    assert "'#krr .light.high{--krr-fill:var(--os-bad,#f06565);--krr-ink:var(--os-bad-ink,#F47C7C)}'" in s
    # Chart.js pinta en canvas: lee los tokens con getComputedStyle (y repinta si cambia el tema)
    assert "getPropertyValue(n)" in s and "tok('--os-bad', DARK.bad)" in s and 'MutationObserver' in s
    # la impresión es papel blanco: paleta clara fija de Khipus OS
    assert "PRINT_CSS = 'body{--os-ink:#111216;" in s and '--os-bad-ink:#A82424' in s
    # móvil: hoja a pantalla completa que CRECE con el contenido (con align-items:stretch el fondo se cortaba)
    mob = s[s.index("'@media(max-width:760px){'"):]
    assert 'min-height:100%' in mob[:400] and 'align-items:stretch' not in mob[:400]
    assert 'window.KhipuMascot' in s                                # "Explícame con IA" lo dice un agente → mascota


JS = r"""
const ROOT = process.argv[1];
const store = {};
global.localStorage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } };
function cl(init) { const s = new Set(String(init || '').split(/\s+/).filter(Boolean));
  return { add: (...c) => c.forEach(x => s.add(x)), remove: (...c) => c.forEach(x => s.delete(x)), contains: c => s.has(c),
    toggle: (c, on) => { const v = on === undefined ? !s.has(c) : !!on; if (v) s.add(c); else s.delete(c); return v; }, toString: () => [...s].join(' ') }; }
function parse(html) {
  const out = [], re = /<([a-zA-Z][\w-]*)((?:\s+[\w:-]+(?:="[^"]*")?)*)\s*\/?>/g; let m;
  while ((m = re.exec(html))) { const attrs = {}; m[2].replace(/([\w:-]+)(?:="([^"]*)")?/g, (_, k, v) => { attrs[k] = v == null ? '' : v; return ''; }); out.push(El(m[1].toLowerCase(), attrs)); }
  return out;
}
function matches(el, sel) {
  const m = sel.trim().match(/^([a-z]+)?(#[\w-]+)?((?:\.[\w-]+)*)((?:\[[^\]]+\])*)$/); if (!m) return false;
  if (m[1] && el.tag !== m[1]) return false;
  if (m[2] && el.attrs.id !== m[2].slice(1)) return false;
  const cls = (el.attrs.class || '').split(/\s+/);
  for (const c of (m[3].match(/\.[\w-]+/g) || [])) if (cls.indexOf(c.slice(1)) < 0) return false;
  for (const a of (m[4].match(/\[[^\]]+\]/g) || [])) { const mm = a.match(/\[([\w-]+)(?:="([^"]*)")?\]/); if (!(mm[1] in el.attrs)) return false; if (mm[2] != null && el.attrs[mm[1]] !== mm[2]) return false; }
  return true;
}
function El(tag, attrs) {
  attrs = attrs || {}; let html = ''; let kids = [];
  const el = { tag, attrs, id: attrs.id || '', value: attrs.value || '', checked: 'checked' in attrs, disabled: 'disabled' in attrs,
    style: {}, className: attrs.class || '', textContent: '', scrollTop: 0, scrollHeight: 0, selectionStart: 0,
    classList: cl(attrs.class), getAttribute: k => (k in attrs ? attrs[k] : null), setAttribute: (k, v) => { attrs[k] = String(v); },
    addEventListener() {}, focus() {}, setSelectionRange() {}, scrollIntoView() {}, closest: () => null,
    querySelector: s => kids.find(k => matches(k, s)) || null, querySelectorAll: s => kids.filter(k => matches(k, s)) };
  Object.defineProperty(el, 'innerHTML', { get: () => html, set: v => { html = String(v); kids = parse(html); } });
  return el;
}
const reg = {}, css = {};
global.document = {
  getElementById: id => (/-css$/.test(id) || id === 'krr-ov' ? (reg[id] || null) : (reg[id] = reg[id] || El('div', { id }))),
  createElement: t => El(t, {}), addEventListener() {}, hidden: false,
  head: { appendChild(st) { reg[st.id] = st; css[st.id] = st.textContent; } },
  body: { classList: cl('dark'), appendChild(el) { reg[el.id] = el; } },
};
document.documentElement = document.head;
const NODES = [
  { id: 'Nvidia', label: 'Nvidia', mkt: 'NVDA' }, { id: 'TSMC', label: 'TSMC', mkt: 'TSM' }, { id: 'AMD', label: 'AMD', mkt: 'AMD' },
  { id: 'OpenAI', label: 'OpenAI', mkt: null, ticker: 'Pre-IPO ~$852B' }, { id: 'Microsoft', label: 'Microsoft (Azure)', mkt: 'MSFT' },
  { id: 'Broadcom', label: 'Broadcom', mkt: 'AVGO' }, { id: 'ASML', label: 'ASML', mkt: 'ASML' }];
const NB = {}; NODES.forEach(n => { NB[n.id] = n; });
global.window = { LANG: 'es', NODES, NODE_BY_ID: NB, MKT: { quotes: { NVDA: { close: 181.2 }, TSM: { close: 198.4 }, AMD: { close: 211.7 } }, pos: { Nvidia: { sh: 10 } } },
  DataLayer: { aiComplete: () => Promise.resolve('Piensa en una carretera con curvas.') } };
store.kh_portfolios = JSON.stringify([{ id: 'p1', name: 'Mi tesis', cash: 41250.5, startCash: 100000, createdAt: 1, positions: [
  { nodeId: 'Nvidia', shares: 120, avgPrice: 150 }, { nodeId: 'TSMC', shares: 80, avgPrice: 210 }, { nodeId: 'OpenAI', shares: 2, avgPrice: 852 }] }]);
store.kh_pf_active = 'p1';
store.kh_risk_quick = JSON.stringify([{ sym: 'NVDA', label: 'Nvidia', usd: 2000 }]);
store.kh_options = JSON.stringify([{ symbol: 'NVDA', kind: 'call', strike: 185, expiry: '2026-11-21', contracts: 1, label: 'Nvidia' }]);
const PROP = { ok: true, as_of: '2026-10-09', disclaimer_es: 'Educativo.', excluded: [{ label: 'OpenAI', reason: 'no cotiza' }], portfolios: [
  { id: 'q1', name_es: 'Equilibrio IA', method: 'inverse_vol', rationale_source: 'ai', rationale: 'Mezcla.', risks_es: ['Caen juntas.'], notes: [{ es: 'Tope 25%', en: 'Cap 25%' }],
    metrics: { vol_ann_pct: 31.4, var95_1d_usd: 412, max_drawdown_pct: -27.9, diversification_ratio: 1.42, n_names: 2, n_sectors: 1, n_countries: 1, as_of: '2026-10-09', from: '2025-10-09', days: 251, amount_usd: 10000 },
    positions: [{ node_id: 'Nvidia', symbol: 'NVDA', label: 'Nvidia', sector: 'Semis', country: 'US', weight: .5, usd: 5000, price: 181.2, vol_ann_pct: 48 },
                { node_id: 'TSMC', symbol: 'TSM', label: 'TSMC', sector: 'Semis', country: 'TW', weight: .5, usd: 5000, price: 198.4, vol_ann_pct: 39 }] }] };
const RISK = { ok: true, source: 'Yahoo', from: '2025-10-09', as_of: '2026-10-09', days: 251, horizon_days: 10, portfolio_value_usd: 49234, vol_ann_pct: 38.6, vol_daily_pct: 2.4,
  var95: { hist_1d_usd: 1934, hist_1d_pct: 3.9, param_1d_usd: 1966, cvar_1d_usd: 2710, cvar_1d_pct: 5.5, hist_nd_usd: 6116, hist_nd_pct: 12.4 }, var99: { hist_1d_usd: 3020, hist_1d_pct: 6.1, cvar_1d_usd: 3550 },
  beta_spy: 1.62, corr_spy: .74, sharpe: .88, return_ann_pct: 31.2, risk_free_pct: 4.1, diversification_ratio: 1.18, max_drawdown_pct: -29.4, max_drawdown_date: '2026-04-08',
  backtest95: { method: 'rolling_oos', days: 126, window: 125, breaches: 11, expected: 6.3, kupiec_p: .07, verdict: 'subestima' }, labels: { NVDA: 'Nvidia', TSM: 'TSMC' },
  positions: [{ symbol: 'NVDA', value_usd: 21744, weight_pct: 44, risk_contrib_pct: 70, vol_ann_pct: 49 }, { symbol: 'TSM', value_usd: 19022, weight_pct: 56, risk_contrib_pct: 30, vol_ann_pct: 38 }],
  worst_days: [{ date: '2026-04-04', pct: -8.7, usd: -4283 }], correlation: { symbols: ['NVDA', 'TSM'], matrix: [[1, .66], [.66, 1]] },
  histogram: { edges_pct: [-4, 0, 4], counts: [3, 9] }, converted: [{ symbol: 'NVDA', usd: 2000, price_usd: 181.2, shares: 11.04, date: '2026-10-09' }], excluded: [{ symbol: 'X', label: 'X', reason: 'sin historia' }] };
const CHAIN = { available: true, spot: 181.2, expirations: ['2026-11-21'], strikes: [175, 180, 185, 190] };
const VEGA = { ok: true, model: 'Black-Scholes', rate: { value_pct: 4.1, source: '^IRX' }, totals: { vega_usd: 62.4, value_usd: 1830, delta_shares: 54, theta_usd_day: -9.1, gamma: 2.1 },
  vol_scenarios: [{ shock_pts: -10, pnl_usd: -560 }, { shock_pts: 10, pnl_usd: 660 }],
  positions: [{ symbol: 'NVDA', kind: 'call', strike: 185, expiry: '2026-11-21', contracts: 1, days: 42, spot: 181.2, iv_pct: 47.5, iv_source: 'live', model_price: 18.3, market_mid: 18.1, vega_usd: 62.4, delta_shares: 54, gamma: 2.1, theta_usd_day: -9.1 }], excluded: [] };
global.fetch = (url) => {
  url = String(url); let b = {};
  if (url.includes('/api/portfolio-ai/themes')) b = { themes: [{ key: 'semis', label: 'Semiconductores', count: 64 }] };
  else if (url.includes('/api/portfolio-ai/propose')) b = PROP;
  else if (url.includes('/api/portfolio-ai/ask')) b = { answer: 'Diversificar es repartir.', answer_source: 'ai', sources: [{ label: 'Grafo' }] };
  else if (url.includes('/api/portfolio/risk_report')) b = RISK;
  else if (url.includes('/api/portfolio/vega_report')) b = VEGA;
  else if (url.includes('/api/options/chain/')) b = CHAIN;
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(b) });
};
require(ROOT + '/engine/mascot.js');
require(ROOT + '/engine/portfolios.js');
require(ROOT + '/engine/riskreport.js');
const tick = () => new Promise(r => setTimeout(r, 15));
const click = (box, sel) => { const e = box.querySelector(sel); if (!e || !e.onclick) throw new Error('sin botón ' + sel); e.onclick(); };
const out = {};
(async () => {
  const P = window.KhipuPortfolios;
  // fuera de Khipus OS (pestaña clásica)
  const page = El('section', { id: 'portfolios-panel' });
  P.mount(page); out.pf = page.innerHTML; out.pf_classes = page.classList.toString();
  click(page, '#kpf-new'); out.pf_new = page.innerHTML; click(page, '#kpf-cancel');
  const s = page.querySelector('#kpf-search'); s.value = 'nvid'; s.oninput();
  click(page, '.kpf-buyopen[data-id="Nvidia"]'); out.pf_buy = page.innerHTML;
  click(page, '#kpf-search-clear');
  click(page, '.kpf-tab[data-view="ai"]'); await tick(); out.ai_form = page.innerHTML;
  click(page, '#kpf-prop-go'); out.ai_busy = page.innerHTML; await tick(); await tick(); out.ai_prop = page.innerHTML;
  click(page, '.kpf-create[data-i="0"]'); out.pf_after_create = page.innerHTML;
  click(page, '.kpf-tab[data-view="ai"]'); click(page, '.kpf-mode[data-mode="ask"]');
  const q = page.querySelector('#kpf-ask'); q.value = '¿Qué es diversificar?'; click(page, '#kpf-ask-go'); out.ai_thinking = page.innerHTML;
  await tick(); await tick(); out.ai_ask = page.innerHTML;
  click(page, '.kpf-tab[data-view="pf"]');
  // dentro de una ventana de Khipus OS: hereda los tokens de #bcp-ov (sin .kos-themed)
  const win = El('section', { id: 'portfolios-panel' }); win.closest = sel => (sel === '#bcp-ov' ? {} : null);
  P.mount(win); out.win_classes = win.classList.toString();
  store.kh_portfolios = '[]'; P.mount(page); out.pf_empty = page.innerHTML;
  // reporte de riesgo
  const R = window.KhipuRisk;
  R.open({ tab: 'var' }); const box = document.getElementById('krr'); out.rr_start = box.innerHTML;
  out.rr_ov_class = document.getElementById('krr-ov').className;
  click(box, '[data-act="runquick"]'); out.rr_busy = box.innerHTML; await tick(); await tick(); out.rr_result = box.innerHTML;
  click(box, '[data-act="ai"]'); await tick(); await tick(); out.rr_ai = box.innerHTML;
  click(box, '[data-act="detail"]'); out.rr_detail = box.innerHTML;
  click(box, '[data-tab="vega"]'); click(box, '[data-vsym="NVDA"]'); await tick(); await tick(); await tick(); out.rr_vega = box.innerHTML;
  click(box, '[data-act="runvega"]'); await tick(); await tick(); click(box, '[data-act="vdetail"]'); out.rr_vega_detail = box.innerHTML;
  out.open = R.isOpen(); R.close(); out.closed = !R.isOpen();
  out.css = css;
  process.stdout.write(JSON.stringify(out));
})().catch(e => { process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""


@pytest.fixture(scope='module')
def screens():
    if not NODE:
        pytest.skip('requiere node')
    r = subprocess.run([NODE, '-e', JS, ROOT], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


HTML_KEYS = ['pf', 'pf_new', 'pf_buy', 'ai_form', 'ai_busy', 'ai_prop', 'pf_after_create', 'ai_thinking', 'ai_ask', 'pf_empty',
             'rr_start', 'rr_busy', 'rr_result', 'rr_ai', 'rr_detail', 'rr_vega', 'rr_vega_detail']


def test_pantallas_pintadas_solo_con_tokens(screens):
    for name in HTML_KEYS:
        html = screens[name]
        assert html, name
        clean = strip_mascots(html)
        assert stray_colors(clean) == [], name
        assert not [c for c in LEGACY if c.lower() in html.lower()], name
        assert not OLD_FONT.search(html), name
    for sid in ('kpf-css', 'krr-css'):
        assert stray_colors(screens['css'][sid]) == [], sid
        assert not OLD_FONT.search(screens['css'][sid]), sid


def test_tema_del_contenedor_y_overlay(screens):
    assert 'kpf-host' in screens['pf_classes'] and 'kos-themed' in screens['pf_classes'] and 'kpf-page' in screens['pf_classes']
    assert 'kpf-host' in screens['win_classes'] and 'kos-themed' not in screens['win_classes']
    assert screens['rr_ov_class'] == 'kos-themed'
    assert screens['open'] and screens['closed']


def test_carteras_conservan_controles_y_tarjetas(screens):
    pf = screens['pf']
    assert pf.startswith('<div class="kpf-root"><div class="kpf-wrap">')
    for i in ('kpf-select', 'kpf-rename', 'kpf-delete', 'kpf-new', 'kpf-refresh', 'kpf-risk', 'kpf-search'):
        assert 'id="%s"' % i in pf, i
    assert 'class="kpf-badge">🧪 SIMULADO' in pf                          # insignia obligatoria de simulación
    assert 'data-l="Acciones"' in pf and 'data-l="P. actual"' in pf       # etiquetas para la vista de tarjeta
    assert 'kpf-sell-go" data-id="Nvidia"' in pf and 'kpf-sell-sh" data-id="Nvidia"' in pf
    assert 'color:var(--os-good-ink,#2fbf5b)' in pf and 'color:var(--os-bad-ink,#F47C7C)' in pf
    assert 'id="kpf-nn"' in screens['pf_new'] and 'id="kpf-create"' in screens['pf_new']
    assert 'kpf-buy-go" data-id="Nvidia"' in screens['pf_buy'] and 'kpf-buy-usd' in screens['pf_buy']
    assert 'id="kpf-new2"' in screens['pf_empty'] and 'kpf-tab-ai' in screens['pf_empty']
    # crear la propuesta guarda una cartera SIMULADA y vuelve a "Mis carteras"
    assert '🤖 Equilibrio IA' in screens['pf_after_create']


def test_asistente_con_mascota_y_mismos_controles(screens):
    f = screens['ai_form']
    assert 'class="kpf-tabs"' in f and 'data-view="ai"' in f and 'aria-pressed="true"' in f
    assert f.count('class="kpf-opt"') + f.count('class="kpf-opt on"') == 9 and f.count('class="kpf-opt on"') == 3 and 'id="kpf-prop-go"' in f and 'id="kpf-amt"' in f and 'id="kpf-excl"' in f
    assert 'class="km' in f                                               # mascota del asistente (agente)
    assert 'km-think' in screens['ai_busy']                               # piensa mientras calcula
    p = screens['ai_prop']
    assert 'class="kpf-disc"' in p and 'kpf-create" data-i="0"' in p and 'kpf-wbar' in p and 'kpf-src kpf-src-ai' in p
    a = screens['ai_ask']
    assert 'class="kpf-msg kpf-me"' in a and 'kpf-botrow' in a and 'class="kpf-msg kpf-bot"' in a
    assert 'id="kpf-ask"' in a and 'id="kpf-ask-go"' in a and 'class="kpf-chip kpf-sugg"' in a
    assert 'kpf-thinking' in screens['ai_thinking'] and 'km-think' in screens['ai_thinking']


def test_riesgo_semaforo_mapa_y_vega_con_tokens(screens):
    st = screens['rr_start']
    assert 'class="ktabs"' in st and 'data-src="market"' in st and 'data-ex="semis"' in st and 'id="krr-q"' in st
    r = screens['rr_result']
    assert 'class="light high"' in r and 'style="border-color' not in r     # semáforo por clase, sin hex
    assert 'data-act="ai"' in r and 'class="km' in r                       # "Explícame con IA" con la mascota
    assert '<div class="ai"><span class="km' in screens['rr_ai'] and 'class="txt"' in screens['rr_ai']
    d = screens['rr_detail']
    assert 'id="krr-hist"' in d and 'class="chartbox"' in d and 'class="scroll tcard"' in d
    assert 'color-mix(in srgb,var(--os-bad,#f06565)' in d                  # correlaciones teñidas con tokens
    v = screens['rr_vega']
    assert 'data-vk="185"' in v and 'data-vkind="call"' in v and 'class="good"' in v and 'data-act="addopt"' in v
    vd = screens['rr_vega_detail']
    assert 'class="good"' in vd and 'class="bad"' in vd and 'Vega' in vd
