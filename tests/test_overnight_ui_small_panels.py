"""Khipus OS (2026-10-10) — paneles pequeños migrados a los tokens --os-* (claro/oscuro):
engine/aispend.js (🩺 → 💰 Gasto IA), engine/mcpconnect.js (🤖 Conectar IAs), engine/brief.js (brief matinal),
engine/insights.js (tarjetas de Análisis + ventana «Oportunidades» del OS) y engine/reconcile.js (🩺 grafo base vs catálogo).

Estático: sin colores/fuentes del tema oscuro viejo fuera de los respaldos de var(); todo var(--os-*) con respaldo;
.kos-themed en las raíces fuera de #bcp-ov; foco visible, movimiento reducido y móvil; APIs/ids públicos intactos.
Con node: tarjetas de Insights bilingües y Gasto IA pintado con tokens (sin colores fijos)."""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
FILES = ['aispend.js', 'mcpconnect.js', 'brief.js', 'insights.js', 'reconcile.js']


def _r(name):
    return open(os.path.join(ROOT, 'engine', name), encoding='utf-8').read()


SRC = {f: _r(f) for f in FILES}

# colores fijos del tema oscuro viejo (NEXUS) y sus fuentes
LEGACY = ['#0B1222', '#06090F', '#050912', '#0e1626', '#03141C', '#1a2234', '#24304a', '#1c2538', '#111827',
          '#E8EDFB', '#C9D4EC', '#BFE9FF', '#9EEBFF', '#9BA6C4', '#7C87A3', '#8791AC', '#c8d0e0', '#5E6884',
          '#00E0FF', '#5FC6E8', '#00a3ff', '#FFB300', '#2BE38B', '#FF4D6A', '#9D6BFF', '#e6a23c', '#fbbf24',
          '#f87171', '#fca5a5', '#4ade80', '#f59e0b', '#a78bfa', '#c4b5fd',
          'rgba(122,158,255', 'rgba(11,18,34', 'rgba(15,21,34', 'rgba(21,28,45', 'rgba(3,6,12', 'rgba(0,224,255']
LEGACY_FONTS = ['JetBrains Mono', 'Inter,', 'Fraunces']


def _strip_var_fallbacks(s):
    """Quita cada var(--x, respaldo) (respaldos anidados incluidos)."""
    out, i = [], 0
    while True:
        j = s.find('var(', i)
        if j < 0:
            out.append(s[i:])
            return ''.join(out)
        out.append(s[i:j])
        depth, k = 0, j + 3
        while k < len(s):
            if s[k] == '(':
                depth += 1
            elif s[k] == ')':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        i = k + 1


def _code_only(s):
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)                     # comentarios de bloque
    s = '\n'.join(l for l in s.split('\n') if not l.strip().startswith('//'))
    s = re.sub(r'\[style\*="[^"]*"( i)?\]', '[style]', s)            # puentes [style*="#FF4D6A" i] (selectores, no colores)
    return _strip_var_fallbacks(s)


@pytest.mark.parametrize('name', FILES)
def test_sin_colores_ni_fuentes_del_tema_oscuro_viejo(name):
    code = _code_only(SRC[name]).lower()
    for c in LEGACY + LEGACY_FONTS:
        assert c.lower() not in code, (name, c)


@pytest.mark.parametrize('name', FILES)
def test_todo_token_lleva_respaldo_oscuro(name):
    bare = re.findall(r'var\(--(?:os|kos)-[a-z0-9-]+\)', SRC[name])
    assert bare == [], (name, bare[:5])
    assert 'var(--os-' in SRC[name]


@pytest.mark.parametrize('name', FILES)
def test_foco_visible_y_movimiento_reducido(name):
    s = SRC[name]
    assert ':focus-visible' in s and 'outline:2px solid var(--os-accent' in s, name
    assert 'prefers-reduced-motion' in s, name


@pytest.mark.parametrize('name', FILES)
def test_raices_fuera_de_bcp_ov_llevan_kos_themed(name):
    assert 'kos-themed' in SRC[name], name


def test_overlays_a_pantalla_completa_en_movil():
    for name in ('mcpconnect.js', 'brief.js'):
        s = SRC[name]
        assert '@media(max-width:760px)' in s and '100vw' in s, name


def test_mcpconnect_api_ids_y_pin_intactos():
    s = SRC['mcpconnect.js']
    assert 'window.KhipuMCP = { open: open, close: close, installEntry: installEntry };' in s
    for i in ('kmcp-ov', "'kmcp'", 'kmcp-css', 'kmcp-entry', 'kmcp-name', 'kmcp-sr', 'kmcp-st', 'kmcp-client', 'kmcp-tok', 'kmcp-cfg',
              'sistema-tabseg', 'data-tab=', 'data-cfg=', 'data-revoke=', 'data-act="create"', 'data-act="copy-tok"',
              'data-act="copy-cfg"', 'data-act="approvals"', 'data-act="close"', 'data-act="new"'):
        assert i in s, i
    # el PIN sigue yendo SOLO por window._tradeFetch (nunca reimplementado)
    assert 'return window._tradeFetch(url, opts || {}, true);' in s and 'X-Trade-Pin' not in s.split('*/', 1)[1]
    assert "'</label>' + chip('human_approval')" in s and "chip('human_approval') + '</label>" not in s
    # las clases genéricas .tab/.tabs de app.html (barra clásica) ya no se cuelan en el panel
    assert 'class="kmcp-tab' in s and 'class="tab' not in s and 'class="tabs"' not in s


def test_aispend_api_e_ids_intactos():
    s = SRC['aispend.js']
    assert "window.KhipuSpend = { render: function (elId) { S.el = document.getElementById(elId); load(); } };" in s
    for i in ("'sp-styles'", 'sp-daily', 'sp-month', 'sp-who', "'sp-f-'", "'sp-p-'", 'id="sp-save"', 'id="sp-cancel"',
              'id="sp-edit"', 'id="sp-refresh"', 'data-days=', 'sp-billed', "window._tradeFetch((window.BASE || '') + '/api/ai/usage/limits', opts, true)"):
        assert i in s, i
    # colores de marca del proveedor SOLO como relleno (punto/barra), nunca como color de texto
    assert "'<b style=\"color:' + p[1]" not in s and 'dot(p[1])' in s


def test_reconcile_api_y_flujo_con_pin_intactos():
    s = SRC['reconcile.js']
    for i in ('window.KhipuReconcile = {', 'mount: function (id)', 'reload: function ()', 'data-cat="', 'data-act="apply"',
              'data-act="refresh"', 'data-act="undo"', 'data-run="', 'window._tradeFetch || fetch', 'confirm_db: _plan.db',
              'expect: expect', "explainRegister('reconcile'", 'requireCheck:'):
        assert i in s, i


def test_brief_api_ids_y_mascotas():
    s = SRC['brief.js']
    for i in ('window._briefOpen = function', 'window._briefClose = close', 'window._briefJump = function', 'window._briefCommittee = function',
              'window._briefAutoAllowed = function', "'brief-ov'", 'id="brief"', 'brief-lead', 'brief-cards', 'brief-src', 'brief-mute',
              "'brief-fab'", "'brief-styles'", 'z-index:7600', 'khipu_brief_day'):
        assert i in s, i
    # el agente Comité y Khipu aparecen como mascotas (engine/mascot.js), con el emoji solo de respaldo
    assert "mascot: 'comite'" in s and "KhipuMascot.svg('khipu', 22)" in s
    # tarjetas con acción = botón accesible
    assert 'role="button" tabindex="0"' in s


def test_insights_api_ids_y_ventana_del_os():
    s = SRC['insights.js']
    for i in ('window.renderKhipuInsights = function', 'window.renderInsightsHistory = function', 'window._insJump = function',
              'window._insShock = function', "getElementById('an-insights')", "getElementById('an-history')", 'class="ins-card"',
              'n.growth_live', "'en vivo' : 'del catálogo'"):
        assert i in s, i
    # la ventana «Oportunidades» (cockpit.js stageInsights) se re-tematiza SOLO dentro de su ventana, con clases que
    # cockpit.js realmente emite (si cockpit cambia sus clases, este test avisa)
    assert ".kd-win[data-kind=\"insights\"] " in s
    cockpit = open(os.path.join(ROOT, 'engine', 'cockpit.js'), encoding='utf-8').read()
    used = set(re.findall(r"W \+ '\.(bcp-[a-z-]+)", s))
    assert {'bcp-icard', 'bcp-lh', 'bcp-row', 'bcp-casc', 'bcp-fact', 'bcp-hyper-hd'} <= used
    for c in used:
        assert c in cockpit, c
    for col in ('#FF4D6A', '#2BE38B'):          # los style="" que stageInsights escribe (UP/DOWN) siguen siendo esos
        assert "'" + col + "'" in cockpit, col


def test_insights_textos_bilingues():
    s = SRC['insights.js']
    for es, en in (("'topología'", "'topology'"), ("'simular su caída'", "'simulate its fall'"), ("'abrir X-Ray'", "'open X-Ray'"),
                   ("'tu cartera'", "'your portfolio'"), ("'panorama sectorial'", "'sector overview'"), ("'concentración'", "'concentration'"),
                   ("'matriz · ponderado'", "'matrix · weighted'"), ("'ver onda de impacto'", "'see the impact wave'"),
                   ("'Generando lecturas de la red…'", "'Generating network readings…'"),
                   ("'Sin lecturas por ahora — el grafo aún carga.'", "'No readings yet — the graph is still loading.'"),
                   ("label: 'RIESGO'", "label_en: 'RISK'"), ("label: 'OPORTUNIDAD'", "label_en: 'OPPORTUNITY'")):
        assert es in s and en in s, (es, en)


# ── con node: el código real corre con un DOM mínimo ───────────────────────────────────────────

_DOM = r'''
const els = {}, styles = [];
function mk(id) {
  return els[id] || (els[id] = { id, innerHTML: '', textContent: '', style: {}, value: '', checked: false,
    classList: { s: new Set(), add(c) { this.s.add(c); }, remove(c) { this.s.delete(c); }, contains(c) { return this.s.has(c); } },
    querySelectorAll() { return []; }, addEventListener() {}, appendChild() {}, setAttribute() {} });
}
global.localStorage = { getItem: k => (k === 'eco_lang' ? __LANG__ : null), setItem() {} };
global.document = {
  readyState: 'complete', head: { appendChild(e) { styles.push(e); } }, documentElement: {},
  getElementById: id => (id === 'ins-styles' || id === 'sp-styles' ? null : mk(id)),
  createElement: () => ({ id: '', textContent: '', style: {} }),
};
global.window = global;
window.LANG = __LANG__;
const realSetTimeout = setTimeout;
const wait = ms => new Promise(r => realSetTimeout(r, ms));
'''


def _run(js):
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.mark.skipif(not NODE, reason='requiere node')
@pytest.mark.parametrize('lang', ['es', 'en'])
def test_insights_tarjetas_con_tokens_y_en_el_idioma(lang):
    js = (_DOM.replace('__LANG__', json.dumps(lang)) + r'''
window.NODES = [{ id: 'a', label: 'Alpha', country: 'Taiwan', cat: 'foundry', margin: 0.4, growth: '🟢' },
                { id: 'b', label: 'Beta', country: 'China', cat: 'foundry', margin: 0.3, growth: '🟡' },
                { id: 'c', label: 'Gamma', country: 'USA', cat: 'foundry', margin: 0.1, growth: '' }];
window.NODE_BY_ID = { a: NODES[0], b: NODES[1], c: NODES[2] };
window.computeDownstream = id => new Set(id === 'a' ? ['b', 'c'] : []);
window.computeNRS = id => ({ a: 30, b: 70, c: 50 })[id];
global.fetch = () => Promise.resolve({ ok: false });
''' + SRC['insights.js'] + r'''
(async () => {
  window.renderKhipuInsights(); await wait(30);
  const el = els['an-insights'];
  process.stdout.write(JSON.stringify({ html: el.innerHTML, cls: [...el.classList.s], css: styles.map(s => s.textContent).join('') }));
})();''')
    o = _run(js)
    assert 'kos-themed' in o['cls'] and 'ins-root' in o['cls']
    assert 'class="ins-card"' in o['html'] and 'var(--os-bad-ink,#F47C7C)' in o['html']
    assert '#00E0FF' not in o['html'] and 'rgba(15,21,34' not in o['html']
    assert '.kd-win[data-kind="insights"] .bcp-icard' in o['css']
    if lang == 'en':
        assert 'is the biggest single point of failure' in o['html'] and 'simulate its fall' in o['html'] and 'OPPORTUNITY' in o['html']
        assert 'arrastra' not in o['html']
    else:
        assert 'es el mayor punto único de fallo' in o['html'] and 'simular su caída' in o['html'] and 'OPORTUNIDAD' in o['html']


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_aispend_pinta_con_tokens_y_conserva_los_ids():
    usage = {'totals': {'today': 1.2, 'week': 4, 'month': 9, 'calls_today': 10},
             'limits': {'daily_usd': 1, 'monthly_usd': 40, 'blocked_providers': []},
             'by_provider': [{'key': 'nvidia', 'cost_usd': 1, 'calls': 2, 'tokens_in': 10, 'tokens_out': 5}],
             'by_feature': [{'key': 'chat', 'label': 'Chat', 'cost_usd': 1, 'calls': 2, 'tokens_in': 10, 'tokens_out': 5}],
             'by_day': [{'key': '2026-10-09', 'cost_usd': 1, 'calls': 2}], 'recent': [], 'note_es': 'n', 'note_en': 'n', 'source': 'db'}
    js = (_DOM.replace('__LANG__', json.dumps('es')) + r'''
global.fetch = u => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(u.indexOf('/api/ai/usage') >= 0 ? ''' + json.dumps(usage) + r''' : { available: false }) });
''' + SRC['aispend.js'] + r'''
(async () => {
  window.KhipuSpend.render('sistema-gasto'); await wait(40);
  const el = els['sistema-gasto'];
  process.stdout.write(JSON.stringify({ html: el.innerHTML, cls: [...el.classList.s], css: styles.map(s => s.textContent).join('') }));
})();''')
    o = _run(js)
    assert 'kos-themed' in o['cls'] and 'sp-root' in o['cls']
    for i in ('id="sp-edit"', 'id="sp-refresh"', 'data-days="30"', 'class="sp-billed"'):
        assert i in o['html'], i
    assert 'var(--os-bad,#f06565)' in o['html']                 # hoy 1.2 de 1.0 → barra en rojo (relleno semántico)
    assert '<b style="color:#76B900' not in o['html'] and 'background:#76B900' in o['html']   # marca = punto/barra, no texto
    assert '#00E0FF' not in o['html'] and '#FFB300' not in o['html'] and '#2BE38B' not in o['html']
    assert '.sp-root .sp-btn' in o['css'] and 'var(--os-btn,#F2F2F5)' in o['css']
