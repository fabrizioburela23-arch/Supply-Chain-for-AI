"""tests/test_overnight_ui_xray_research.py — X-Ray (engine/xray.js) e Investigación IA (engine/research.js)
entran a Khipus OS (2026-10-10).

Antes eran "isla oscura": fondos #0B1222/#06090F, tinta #E8EDFB, neón #00E0FF, letra Inter/JetBrains Mono y
bordes por todos lados; cockpit.js los forzaba a oscuro (LEGACY_DARK) para que se leyeran en el tema claro.
Ahora:
  · solo tokens --os-* / --kos-* de engine/cockpit.js, siempre con respaldo oscuro dentro de var()
  · los overlays que viven FUERA de #bcp-ov (#xray-ov, #rs-ov) llevan .kos-themed (tokens claro/oscuro)
  · colores semánticos de TEXTO = *-ink (AA); los vivos (--os-good/--os-bad) solo para rellenos y barras
  · los AGENTES se dibujan con sus mascotas (engine/mascot.js); sin el módulo, el emoji de antes
  · se conservan TODAS las APIs públicas, ids, clases y data-* que usan otros módulos
Se corre el JS REAL en node (vm) con un DOM falso mínimo.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
XRAY = open(os.path.join(ROOT, 'engine', 'xray.js'), encoding='utf-8').read()
RS = open(os.path.join(ROOT, 'engine', 'research.js'), encoding='utf-8').read()
COCKPIT = open(os.path.join(ROOT, 'engine', 'cockpit.js'), encoding='utf-8').read()
needs_node = pytest.mark.skipif(not NODE, reason='requiere node')


def _strip_var_fallbacks(src):
    """Quita cada var(--x, respaldo) completo (el respaldo puede tener paréntesis): lo que queda son colores FIJOS."""
    out, i = [], 0
    while True:
        j = src.find('var(--', i)
        if j < 0:
            out.append(src[i:])
            break
        out.append(src[i:j])
        depth, k = 0, j
        while k < len(src):
            if src[k] == '(':
                depth += 1
            elif src[k] == ')':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        out.append('VAR')
        i = k + 1
    return ''.join(out)


# piel vieja (NEXUS oscura): fondos, tintas, neón, bordes azulados y letras
LEGACY = ['#0B1222', '#06090F', '#0a1120', '#E8EDFB', '#00E0FF', '#9BA6C4', '#7C87A3', '#5b6580', '#AEB7CF', '#5FC6E8',
          '#FF4D6A', '#2BE38B', '#FFB300', '#03141C', 'rgba(21,28,45', 'rgba(11,18,34', 'rgba(6,9,15', 'rgba(3,6,12',
          'rgba(122,158,255', 'rgba(0,224,255', 'rgba(255,77,106', 'rgba(43,227,139', 'rgba(255,179,0']
FONTS = ["'Inter'", 'Inter,', 'JetBrains', 'Fraunces', 'Cascadia']


@pytest.mark.parametrize('name,src', [('xray', XRAY), ('research', RS)])
def test_sin_colores_ni_letras_de_la_piel_vieja(name, src):
    rest = _strip_var_fallbacks(src)
    low = rest.lower()
    for c in LEGACY:
        assert c.lower() not in low, '%s: color fijo de la piel vieja fuera de var(): %s' % (name, c)
    for f in FONTS:
        assert f not in rest, '%s: letra vieja: %s' % (name, f)


@pytest.mark.parametrize('name,src', [('xray', XRAY), ('research', RS)])
def test_solo_quedan_colores_fijos_permitidos(name, src):
    """Fuera de var(): solo el color de DATOS por defecto de un sector (relleno) y el selector-puente #7ecbff."""
    rest = _strip_var_fallbacks(src)
    found = re.findall(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|rgba?\([^)]*\)', rest)
    allowed = {'#4C8DF6', '#7ecbff'}
    assert set(found) <= allowed, (name, sorted(set(found) - allowed))


@pytest.mark.parametrize('name,src', [('xray', XRAY), ('research', RS)])
def test_cada_token_existe_en_cockpit(name, src):
    used = set(re.findall(r'var\((--(?:os|kos)-[a-z0-9-]+)', src))
    assert used, name
    for tok in used:
        assert tok + ':' in COCKPIT, '%s usa %s y cockpit.js no lo define' % (name, tok)


def test_overlays_fuera_de_bcp_ov_llevan_kos_themed():
    assert "ov.className = 'kos-themed'" in XRAY and "ov.id = 'xray-ov'" in XRAY
    assert "ov.className = 'kos-themed'" in RS and "ov.id = 'rs-ov'" in RS
    # el tema lo resuelve cockpit.js (claro = body sin .dark, oscuro = body.dark)
    assert 'body:not(.dark) .kos-themed' in COCKPIT and 'body.dark .kos-themed' in COCKPIT


def test_texto_semantico_con_tokens_ink_y_movimiento_reducido():
    for src in (XRAY, RS):
        assert 'var(--os-good-ink' in src and 'var(--os-bad-ink' in src and 'var(--os-warn-ink' in src
        assert 'prefers-reduced-motion' in src
        assert 'outline:2px solid var(--os-accent' in src          # foco de teclado visible
        assert "82%,var(--os-ink" in src                          # acento como TEXTO ≥ 4.5:1 sobre --os-surface-2
    assert '@media(max-width:760px)' in RS and '@media(max-width:760px)' in XRAY


def test_api_publica_e_ids_del_xray_se_conservan():
    for api in ('window.openXRay', 'window.buildXRayHTML', 'window.wireXRay', 'window.xrayEnsureStyles',
                'window.xrayImpactViaState', 'window.xrayComputeWinners', 'window._xrayJump', 'window._xrayClose',
                'window._xrayShock', 'window._xrayTKG', 'window._xrayCompare'):
        assert api + ' =' in XRAY, api
    for frag in ("'xray-ov'", 'id="xray"', 'id="xr-px"', 'id="xr-lin"', 'id="xr-impact"', 'id="xr-struct"', "'xray-styles'",
                 'xray-scope', 'xr-full', 'xr-close', 'xr-mcap', 'xr-emp', 'xr-rev', 'thread-scroll',
                 'data-live="employees"', 'data-live="mcap"', 'data-live="revenue"', 'data-live="margin"', 'data-live="growth"',
                 'data-live-label="revenue"', 'data-live-label="growth"', 'data-live-sub="margin"', 'data-live-fmt="k"'):
        assert frag in XRAY, frag
    # desktop.js esconde el ✕ propio dentro de una ventana; resolve.js cierra #xray-ov por id
    assert '.xray-scope .xr-close' in open(os.path.join(ROOT, 'engine', 'desktop.js'), encoding='utf-8').read()


def test_api_publica_e_ids_de_investigacion_se_conservan():
    assert re.search(r'window\.KhipuResearch = \{ open: open, close: close, run: run, why: why, renderInline: renderInline,\s*'
                     r'back: function', RS)
    for frag in ("'rs-ov'", 'id="rs"', 'id="rs-depth"', 'id="rs-go"', 'id="rs-complete"', 'id="rs-act"', "'rs-styles'",
                 'class="rs-tab', 'data-t="', 'rs-why', 'rs-claim'):
        assert frag in RS, frag


# ── JS real en node con un DOM falso ─────────────────────────────────────────
HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const ROOT = process.argv[1];
const LANG = process.argv[2] || 'es';
const WITH_MASCOT = process.argv[3] !== 'no-mascot';
const WHAT = process.argv[4] || 'research';
const byId = {}, all = [];
function ClassList(el) { this.el = el; }
ClassList.prototype._get = function () { return (this.el._cls || '').split(/\s+/).filter(Boolean); };
ClassList.prototype.add = function (c) { const a = this._get(); if (a.indexOf(c) < 0) a.push(c); this.el._cls = a.join(' '); };
ClassList.prototype.remove = function (c) { this.el._cls = this._get().filter(x => x !== c).join(' '); };
ClassList.prototype.contains = function (c) { return this._get().indexOf(c) >= 0; };
ClassList.prototype.toggle = function (c, f) { if (f === undefined ? !this.contains(c) : f) this.add(c); else this.remove(c); };
function findId(id) {
  if (byId[id]) return byId[id];
  if (all.some(e => e._html.indexOf('id="' + id + '"') >= 0)) { const s = new El('div'); s.id = id; return s; }
  return null;
}
class El {
  constructor(tag) { this.tagName = String(tag || 'div').toUpperCase(); this.children = []; this._cls = ''; this._html = ''; this._text = '';
    this._id = ''; this.style = {}; this.attrs = {}; this.listeners = {}; this.classList = new ClassList(this); this.isConnected = true; all.push(this); }
  get id() { return this._id; } set id(v) { this._id = String(v); byId[this._id] = this; }
  get className() { return this._cls; } set className(v) { this._cls = String(v); }
  get innerHTML() { return this._html; } set innerHTML(v) { this._html = String(v); }
  get textContent() { return this._text || this._html; } set textContent(v) { this._text = String(v); }
  appendChild(c) { this.children.push(c); return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); } getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
  querySelectorAll() { return []; }
  querySelector(sel) { return sel && sel[0] === '#' ? findId(sel.slice(1)) : null; }
  getClientRects() { return [1]; }
}
const store = { eco_lang: LANG };
const ctx = { console, Date, Math, JSON, Promise, encodeURIComponent, isNaN, isFinite, Number, String, Object, Array, Set, Map,
  setTimeout: (fn, ms) => setTimeout(fn, Math.min(ms || 0, 5)), clearTimeout, setInterval: () => 1, clearInterval: () => {},
  localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } },
  getComputedStyle: () => ({ getPropertyValue: () => '' }),
};
ctx.window = ctx; ctx.globalThis = ctx; ctx.LANG = LANG;
const body = new El('body'); body._cls = 'dark';
ctx.document = { readyState: 'complete', body, head: new El('head'), documentElement: new El('html'), hidden: false,
  createElement: t => new El(t), addEventListener: () => {}, getElementById: findId };
const replies = JSON.parse(process.env.REPLIES || '{}');
ctx.fetch = (url) => Promise.resolve({ ok: true, status: 200,
  json: () => Promise.resolve(replies[url.replace(/\?.*$/, '')] || null),
  text: () => Promise.resolve(JSON.stringify(replies[url.replace(/\?.*$/, '')] || {})) });
vm.createContext(ctx);
if (WITH_MASCOT) vm.runInContext(fs.readFileSync(ROOT + '/engine/mascot.js', 'utf8'), ctx);
function css(id) { const s = ctx.document.head.children.find(c => c.id === id); return s ? s.textContent : ''; }
const out = {};
if (WHAT === 'research') {
  vm.runInContext(fs.readFileSync(ROOT + '/engine/research.js', 'utf8'), ctx);
  ctx.KhipuCommittee = { open: () => {} };
  const KR = ctx.KhipuResearch;
  out.api = Object.keys(KR).sort();
  KR.open('Nvidia');
  setTimeout(() => {
    out.ovClass = (byId['rs-ov'] || {})._cls;
    out.main = (byId['rs'] || {})._html;
    out.act = (byId['rs-act'] || {})._html;
    out.css = css('rs-styles');
    KR.why('c3');
    setTimeout(() => {
      out.why = (byId['rs'] || {})._html;
      const host = new El('div');
      KR.renderInline(host, 'Nvidia');
      setTimeout(() => { out.inline = host._html; console.log(JSON.stringify(out)); }, 40);
    }, 40);
  }, 60);
} else {
  ctx.NODE_BY_ID = { Nvidia: { id: 'Nvidia', label: 'Nvidia', cat: 'fabless', ticker: 'NVDA', mkt: 'NVDA', country: 'USA', margin: 0.6, growth: '+50%' },
                     TSMC: { id: 'TSMC', label: 'TSMC', cat: 'foundry', country: 'TWN' }, AMD: { id: 'AMD', label: 'AMD', cat: 'fabless' },
                     OpenAI: { id: 'OpenAI', label: 'OpenAI', cat: 'ailab' } };
  ctx.NODES = Object.values(ctx.NODE_BY_ID);
  ctx.LINKS = [{ source: 'TSMC', target: 'Nvidia', w: 5, rel: 'fab', type: 'fab' }, { source: 'Nvidia', target: 'OpenAI', w: 4, rel: 'supply', type: 'supply' }];
  ctx.NODE_META = { Nvidia: { founded: 1993, employees: 36000, mktcap_b: 4400 } };
  ctx.computeNRSBreakdown = () => ({ total: 64, terms: [{ key: 'Cadena', detail: 'grado 2', val: 20, max: 25, hot: true }, { key: 'Margen', detail: '60%', val: 0, max: 20 }] });
  ctx.computeNRS = () => 50;
  ctx.KhipuState = { simulate: () => ({ impact: new Map([['OpenAI', 70], ['AMD', 2]]) }) };
  ctx.KhipuResearch = { open: () => {} }; ctx.KhipuCommittee = { open: () => {} }; ctx._openSecondBrain = () => {};
  ctx.openFinCard = () => {}; ctx.openCompare = () => {}; ctx.__tkgOpenObj = () => {};
  vm.runInContext(fs.readFileSync(ROOT + '/engine/xray.js', 'utf8'), ctx);
  out.apis = ['openXRay', 'buildXRayHTML', 'wireXRay', 'xrayEnsureStyles', 'xrayImpactViaState', 'xrayComputeWinners',
              '_xrayJump', '_xrayClose', '_xrayShock', '_xrayTKG', '_xrayCompare'].filter(k => typeof ctx[k] === 'function');
  ctx.openXRay('Nvidia');
  out.ovClass = (byId['xray-ov'] || {})._cls;
  out.ovHtml = (byId['xray-ov'] || {})._html;
  const root = byId['xray'] || findId('xray');
  setTimeout(() => {
    out.drawer = root._html;
    out.impact = (byId['xr-impact'] || {})._html;
    out.struct = (byId['xr-struct'] || {})._html;
    out.full = ctx.buildXRayHTML('Nvidia', { full: true });
    out.css = css('xray-styles');
    out.keys = !!(root.listeners.keydown && root.listeners.keydown.length);
    console.log(JSON.stringify(out));
  }, 60);
}
"""

ENTITY = {
    'entity_id': 'Nvidia',
    'by_agent': {
        'fundamental': [{'claim_id': 'c1', 'agent_type': 'fundamental', 'stance': 'positive', 'horizon': 'MEDIUM_TERM', 'confidence': .72,
                         'statement_es': 'Los ingresos crecen.', 'statement_en': 'Revenue grows.', 'n_supporting': 3, 'n_counter': 1,
                         'created_at': '2026-10-10T06:00:00Z'}],
        'supply_chain': [{'claim_id': 'c3', 'agent_type': 'supply_chain', 'stance': 'negative', 'horizon': 'SHORT_TERM', 'confidence': .64,
                          'statement_es': 'Depende de TSMC.', 'statement_en': 'Depends on TSMC.', 'n_supporting': 2, 'n_counter': 1,
                          'created_at': '2026-10-10T06:00:00Z'}],
    },
    'contradictions': [],
    'last_job': {'status': 'partial', 'coverage': {'complete': False, 'missing': ['macro'], 'note_es': 'Falta Macro.', 'note_en': 'Macro missing.'}},
}
ACT = {'activity': [{'started_at': '2026-10-10T06:00:00Z', 'agent_type': 'supply_chain', 'status': 'done', 'claims_generated': 1,
                     'trigger': {'kind': 'request', 'by': 'Fabrizio'}},
                    {'started_at': '2026-10-10T06:00:00Z', 'agent_type': 'geopolitical', 'status': 'failed', 'trigger': {'kind': 'event'},
                     'hint_es': 'IA ocupada', 'hint_en': 'AI busy', 'errors': ['503']}]}
WHY = {'claim': dict(ENTITY['by_agent']['supply_chain'][0], falsifiers=['x']),
       'supporting': [{'ref': 'E1', 'title': 't', 'excerpt': 'e', 'source_type': 'news', 'reliability': .8, 'source_reference': 'https://example.com/a'}],
       'counter': [], 'affected_nodes': [{'id': 'TSMC', 'label': 'TSMC'}], 'contradicts': [], 'run': {}}
TENSOR = {'supplier_concentration': {'level': 'alta', 'n_suppliers': 3, 'top': [{'label': 'TSMC', 'share_pct': 60}]},
          'supplier_countries': [{'country': 'TWN', 'share_pct': 70}], 'downstream': {'cap_at_risk_usd_b': 500, 'systemic_rank': 1},
          'upstream_risk_sources': [{'id': 'TSMC', 'label': 'TSMC', 'exposure_pct': 40, 'direct': True}], 'peers': [{'id': 'AMD', 'label': 'AMD'}]}


def _run(what, lang='es', mascot=True):
    replies = {'/api/research/entity/Nvidia': ENTITY, '/api/research/activity': ACT, '/api/research/claims/c3': WHY,
               '/api/committee/track-record': {'agents': [], 'min_n': 5}, '/api/committee/calibration': {'table': {}, 'k': 10, 'min_n': 5},
               '/api/tensor/node/Nvidia': TENSOR}
    env = dict(os.environ, REPLIES=json.dumps(replies))
    r = subprocess.run([NODE, '-e', HARNESS, ROOT, lang, 'mascot' if mascot else 'no-mascot', what],
                       capture_output=True, text=True, timeout=60, env=env)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


@needs_node
def test_investigacion_pinta_mascotas_y_tokens():
    o = _run('research')
    assert o['api'] == ['back', 'close', 'open', 'renderInline', 'run', 'why']
    assert 'kos-themed' in o['ovClass']
    main = o['main']
    # pestañas por agente con su mascota (no emoji) + el equipo en el encabezado
    assert 'class="rs-tab on"' in main and 'class="km' in main and 'km-stack' in main
    assert '📊 Fundamental' not in main and '🔗 Cadena' not in main
    # cobertura parcial: aviso ámbar + botón «Completar lo que falta» con su id
    assert 'class="rs-msg bad"' in main and 'id="rs-complete"' in main and 'rs-btn warn' in main
    assert 'id="rs-depth"' in main and 'id="rs-go"' in main and 'rs-btn ghost' in main
    # actividad real: mascota del agente + pista ámbar con clase (sin colores fijos)
    assert 'class="km' in o['act'] and 'rs-hint' in o['act'] and '#FFB300' not in o['act']
    # ¿Por qué?: evidencia, nodos como botones, mascota del agente
    assert 'rs-ev' in o['why'] and '<button type="button" class="rs-node"' in o['why'] and 'class="km' in o['why']
    # bloque compacto del mapa: sin neón, con tokens que caen a las variables de app.html
    assert '#00E0FF' not in o['inline'] and 'var(--os-btn,var(--ink' in o['inline'] and 'class="km' in o['inline']
    css = o['css']
    assert 'background:var(--os-bg' in css and '#0B1222' not in css and 'Inter' not in css


@needs_node
def test_investigacion_en_ingles_y_sin_mascot_js():
    o = _run('research', lang='en', mascot=False)
    assert 'AI research' in o['main'] and 'Conclusions by perspective' in o['main'] and 'Complete the missing part' in o['main']
    assert 'Investigación IA' not in o['main']
    # sin engine/mascot.js: el emoji de antes como respaldo (nunca un hueco)
    assert 'rs-mfb' in o['main'] and '📊' in o['main']


@needs_node
def test_xray_cajon_y_escenario_con_tokens():
    o = _run('xray')
    assert sorted(o['apis']) == sorted(['openXRay', 'buildXRayHTML', 'wireXRay', 'xrayEnsureStyles', 'xrayImpactViaState',
                                        'xrayComputeWinners', '_xrayJump', '_xrayClose', '_xrayShock', '_xrayTKG', '_xrayCompare'])
    assert 'kos-themed' in o['ovClass'] and 'class="xray-scope"' in o['ovHtml']
    d = o['drawer']
    # botones de verdad + mascotas para los agentes (Comité, Investigación IA, Análisis IA)
    assert '<button type="button" class="xrb pri"' in d and d.count('class="km') >= 3
    assert '🏛' not in d and '🧠' not in d
    # filas clicables alcanzables con teclado
    assert 'class="thread" role="button" tabindex="0"' in d and o['keys'] is True
    assert '#E8EDFB' not in d and '#00E0FF' not in d and '#7C87A3' not in d
    # NRS 64 → texto rojo con contraste AA (token *-ink)
    assert 'var(--os-bad-ink' in d
    # onda de impacto: celdas "hot" y víctimas con role=button; sin verdes/rojos fijos
    imp = o['impact']
    assert 'icell hot' in imp and 'xr-victim" role="button"' in imp and '#FF4D6A' not in imp and '#2BE38B' not in imp
    # estructura: concentración "alta" con el token de texto rojo
    assert 'var(--os-bad-ink' in o['struct'] and '#E8EDFB' not in o['struct']
    assert 'xr-cols' in o['full']
    css = o['css']
    assert '#xray{' in css and 'background:var(--os-bg' in css and 'JetBrains' not in css
