"""Khipus OS v1 — la "cáscara" (engine/cockpit.js + engine/desktop.js + aterrizaje en app.html).

Contrato: docs/KHIPUS_OS.md §1-§3.1. Pruebas estáticas (tokens, claves, reglas de dinero) y de
comportamiento en node vm (geometría de los flancos, registro de ventanas nativas), sin navegador.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')


def _r(p):
    with open(os.path.join(ROOT, p), encoding='utf-8') as f:
        return f.read()


# ── §1 tokens: valores EXACTOS de la tabla de la especificación ──────────────
LIGHT = {
    '--os-bg': '#EDEDF5', '--os-surface': '#FFFFFF', '--os-surface-2': '#F2F2F7', '--os-surface-3': '#E7E7EF',
    '--os-ink': '#111216', '--os-ink-2': '#5B5E6B', '--os-ink-3': '#8D90A0', '--os-line': 'rgba(17,18,22,.08)',
    '--os-shadow': '0 1px 2px rgba(17,18,40,.04), 0 8px 28px rgba(17,18,40,.06)',
    '--os-accent': '#2F6BEA', '--os-pos': '#2F6BEA', '--os-neg': '#E8623A', '--os-mute': '#C9CAD6',
    '--os-good': '#0ca30c', '--os-bad': '#d03b3b', '--os-btn': '#111216', '--os-btn-ink': '#FFFFFF',
}
DARK = {
    '--os-bg': '#0E0F14', '--os-surface': '#17181F', '--os-surface-2': '#1F2029', '--os-surface-3': '#2A2B36',
    '--os-ink': '#F2F2F5', '--os-ink-2': '#A6A8B5', '--os-ink-3': '#6E7080', '--os-line': 'rgba(255,255,255,.07)',
    '--os-shadow': '0 1px 2px rgba(0,0,0,.4), 0 10px 30px rgba(0,0,0,.35)',
    '--os-accent': '#4C8DF6', '--os-pos': '#4C8DF6', '--os-neg': '#F07A52', '--os-mute': '#3A3C4A',
    '--os-good': '#2fbf5b', '--os-bad': '#f06565', '--os-btn': '#F2F2F5', '--os-btn-ink': '#111216',
}


def _block(css, selector_start):
    i = css.index(selector_start)
    j = css.index('}', i)
    body = css[css.index('{', i) + 1:j]
    out = {}
    for decl in re.split(r';(?![^(]*\))', body):
        if ':' in decl:
            k, v = decl.split(':', 1)
            out[k.strip()] = v.strip()
    return out


def test_tokens_claro_y_oscuro_exactos_de_la_especificacion():
    s = _r('engine/cockpit.js')
    light = _block(s, 'body:not(.dark) #bcp-ov,body:not(.dark) .kos-themed{')   # .kos-themed: overlays fuera del OS
    dark = _block(s, 'body.dark #bcp-ov,body.dark .kos-themed,body #bcp-ov.kos-classic,#bcp-ov .kd-legacy-dark{')
    for k, v in LIGHT.items():
        assert light.get(k) == v, (k, light.get(k), v)
    for k, v in DARK.items():
        assert dark.get(k) == v, (k, dark.get(k), v)
    shared = _block(s, '#bcp-ov{--os-r:18px')
    assert shared['--os-r'] == '18px' and shared['--os-r-sm'] == '12px'
    assert shared['--os-font'].startswith("'Nunito', 'Geist'")   # 2026-10-06: letra ligeramente redondeada (Fabrizio)
    # la fuente 'Inter' no se carga en app.html: ya no se usa en la cáscara
    assert "'Inter'" not in s


def test_ventanas_del_escritorio_solo_con_tokens():
    d = _r('engine/desktop.js')
    css = d[d.index("var css = '' +"):d.index("var st = document.createElement('style'); st.id = 'kd-styles'")]
    # el cromo de la ventana, la barra y los menús leen variables (cambiar de tema no re-inyecta estilos)
    for rule in ("'.kd-win{", "'#kd-bar{", "'#kd-menu{", "'.kd-task{"):
        seg = css[css.index(rule):css.index("}'", css.index(rule))]
        assert 'var(--os-' in seg, rule
        assert '#070B14' not in seg and 'rgba(6,10,19' not in seg, rule
    assert '.kd-body.kd-legacy-dark{' in css   # isla oscura legible para escenas viejas en tema claro


def test_escenas_viejas_marcadas_kd_legacy_dark():
    s = _r('engine/cockpit.js')
    m = re.search(r"var LEGACY_DARK = \[([^\]]*)\]", s)
    kinds = set(re.findall(r"'(\w+)'", m.group(1)))
    assert {'broker', 'scalp', 'insights', 'screener', 'deep', 'research', 'agentsim', 'compare', 'sim', 'pick', 'xray'} <= kinds
    assert "body.classList.toggle('kd-legacy-dark', LEGACY_DARK.indexOf(kind) >= 0)" in s


def test_clave_nueva_kh_desk_flank_sin_tocar_kh_desk_layout():
    d = _r('engine/desktop.js')
    assert "LS_FLANK = 'kh_desk_flank'" in d
    # kh_desk_layout está reservada para K4 (espacios guardados): no se lee ni se escribe
    code = re.sub(r'//[^\n]*|/\*[\s\S]*?\*/', '', d)
    assert 'kh_desk_layout' not in code


def test_aterriza_siempre_en_khipus_os_salvo_vista_clasica():
    h = _r('app.html')
    i = h.index('(function boot(){')
    blk = h[i:h.index('/* ---- Contadores animados', i)]
    assert "sessionStorage.getItem('kh_os_classic') === '1'" in blk
    assert "getItem('kh_bixby_landed')" not in blk          # ya no es "una vez por sesión"
    assert 'fadeBoot' in blk and 'tries < 90' in blk          # coordinación con el splash + respaldo de ~9 s
    s = _r('engine/cockpit.js')
    assert "sessionStorage.removeItem('kh_os_classic')" in s   # abrir el OS sale de la vista clásica
    assert "sessionStorage.setItem('kh_os_classic', '1')" in s


def test_esc_nunca_cierra_khipus_os():
    s = _r('engine/cockpit.js')
    i = s.index("  document.addEventListener('keydown', function (e) {\n    if (!open) return;")
    blk = s[i:s.index('}, true);', i)]
    # solo cierra la paleta, un menú, la demostración o la ventana enfocada
    assert not re.search(r'(?<![\w.])close\(\)', blk), 'Esc no debe llamar close()'
    assert 'desk().close(f)' in blk and 'palClose()' in blk and '_popClose()' in blk
    assert '_osOnTop()' in blk          # otro overlay (comité, órdenes) maneja su propio Esc
    # el ⌘K va primero a la paleta (captura) y no reabre/re-pinta la Cabina
    assert "(k === 'k' || k === 'K')" in blk and 'palOpen' in blk


def test_saldo_de_la_barra_nunca_pide_pin_y_lleva_insignia():
    s = _r('engine/cockpit.js')
    i = s.index('  function _balRefresh() {')
    blk = s[i:s.index('  function _balGo() {', i)]
    assert '_tradeAccountInfo(false, false)' in blk
    assert '_tradeAccountInfo(true' not in blk and '_tradeFetch' not in blk
    assert '🧪' in blk and '🔴' in blk
    # sin saber si es papel o dinero real, el saldo del bróker NO se muestra
    assert 'sin saber papel/real NO se muestra' in blk


def test_textos_nuevos_bilingues():
    s = _r('engine/cockpit.js')
    for es, en in [('Busca una empresa o abre una pantalla…', 'Search a company or open a screen…'),
                   ('Pregúntale lo que quieras, como a un analista.', 'Ask anything, the way you would ask an analyst.'),
                   ('Vista clásica', 'Classic view'), ('Nueva conversación', 'New conversation'),
                   ('Cuenta de práctica', 'Practice account')]:
        assert es in s and en in s, es
    d = _r('engine/desktop.js')
    assert "flankHint: ['Pregúntale algo a Khipu y aquí aparecerán las ventanas', 'Ask Khipu something and the windows will appear here']" in d


# ── comportamiento (node vm, sin navegador) ───────────────────────────────────
_STUBS = r"""
const fs = require('fs'), vm = require('vm');
const ROOT = process.argv[1];
const store = {};
function el() { return { style: {}, classList: { add(){}, remove(){}, toggle(){}, contains(){ return false; } },
  appendChild(){}, querySelector(){ return null; }, querySelectorAll(){ return []; }, addEventListener(){},
  setAttribute(){}, getAttribute(){ return null; } }; }
const ctx = { console, setTimeout, clearTimeout, setInterval, clearInterval, Math, JSON, Date, Event: function(){}, CustomEvent: function(){},
  localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } },
  sessionStorage: { getItem: () => null, setItem(){}, removeItem(){} },
  navigator: { platform: 'Linux', userAgent: 'node' }, innerWidth: 1440, innerHeight: 900,
  matchMedia: () => ({ matches: false }), addEventListener(){}, removeEventListener(){}, dispatchEvent(){} };
ctx.window = ctx; ctx.globalThis = ctx;
ctx.document = { addEventListener(){}, getElementById(){ return null; }, querySelector(){ return null; },
  querySelectorAll(){ return []; }, createElement: el, head: el(), body: el(), documentElement: el() };
vm.createContext(ctx);
"""


def _node(script, *args):
    p = subprocess.run([NODE, '-e', _STUBS + script, ROOT] + list(args), capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.mark.skipif(not NODE, reason='node no instalado')
def test_geometria_de_flancos_nunca_tapa_el_chat():
    out = _node(r"""
vm.runInContext(fs.readFileSync(ROOT + '/engine/desktop.js', 'utf8'), ctx);
const D = ctx.KhipuDesk, res = {};
res.minW = D._centerMinW;
for (const W of [1100, 1280, 1440, 1680, 1920, 2560]) res[W] = D._geom(W, 776);
console.log(JSON.stringify(res));
""")
    assert out['minW'] <= 1100   # a 1100 px de ventana el chat al centro cabe (con flancos ≥ 300 px)
    for W in ('1100', '1280', '1440', '1680', '1920', '2560'):
        g = out[W]
        w = int(W)
        assert 440 <= g['cw'] <= 680, (W, g['cw'])
        if 440 < round(w * 0.38) < 680:
            assert g['cw'] == round(w * 0.38), (W, g['cw'])   # 38 % del ancho
        L, R = g['L'], g['R']
        assert L['x'] >= 0 and L['x'] + L['w'] <= g['cx'], (W, 'flanco izq. tapa el chat')
        assert R['x'] >= g['cx'] + g['cw'] and R['x'] + R['w'] <= w, (W, 'flanco der. tapa el chat')
        assert L['w'] >= 300 and R['w'] >= 300, (W, L['w'], R['w'])
        assert abs((g['cx'] + g['cw'] / 2) - w / 2) <= 1   # el chat queda centrado


@pytest.mark.skipif(not NODE, reason='node no instalado')
def test_registro_de_ventanas_nativas_contrato_3_1():
    out = _node(r"""
const calls = [];
ctx.KhipuDesk = { enabled: () => true, active: () => false, configure: h => calls.push(h), isCentered: () => false };
// un módulo que cargó ANTES que la Cabina deja su ventana en la cola
ctx.__kosKindQueue = [['agents', { icon: '◍', es: 'Tus agentes', en: 'Your agents', render: function(){} }]];
vm.runInContext(fs.readFileSync(ROOT + '/engine/cockpit.js', 'utf8'), ctx);
const C = ctx.BixbyCockpit, r = {};
r.api = ['open','close','isOpen','stage','registerKind','isCentered','palette','screens','openScreen','classicView'].filter(k => typeof C[k] !== 'function');
r.ok = C.registerKind('glance', { icon: '◉', es: 'En una mirada', en: 'At a glance', multi: true, render: function(b, a){} });
r.badChat = C.registerKind('chat', { render: function(){} });
r.badNoRender = C.registerKind('x', { es: 'x' });
const last = calls[calls.length - 1];
r.multi = last.multiKinds;
r.hooks = Object.keys(calls[0]).sort();
r.centered = C.isCentered();
ctx.__kosKindQueue.push(['conviction', { es: 'Convicción', en: 'Conviction', render: function(){} }]);
r.noPf = C.screens().some(s => s.id === 'portfolios');   // sin el módulo de carteras no se ofrece la entrada
ctx.KhipuPortfolios = { mount(){} };
r.screens = C.screens();
console.log(JSON.stringify(r));
""")
    assert out['api'] == [], out['api']
    assert out['ok'] is True and out['badChat'] is False and out['badNoRender'] is False
    assert 'glance' in out['multi'] and 'xray' in out['multi'] and 'sim' in out['multi']
    for h in ('render', 'title', 'icon', 'iconHTML', 'onLayout', 'onClose', 'resume', 'adoptKinds', 'multiKinds'):
        assert h in out['hooks'], h
    assert out['centered'] is False
    assert out['noPf'] is False
    ids = [s['id'] for s in out['screens']]
    assert len(ids) == len(set(ids))
    assert 'agents' in ids                       # vino de la cola previa a la carga
    for s in out['screens']:
        assert s['es'] and s['en'] and s['icon'], s
    for must in ('graph', 'market', 'terminal', 'geo', 'space', 'simulation', 'crypto', 'portfolios', 'insights', 'screener', 'canvas', 'guia'):
        assert must in ids, must


def test_carteras_es_ventana_y_ya_no_cierra_el_os():
    s = _r('engine/cockpit.js')
    assert "portfolios: { panel: 'portfolios-panel'" in s
    assert "'portfolios'" in s[s.index('adoptKinds: ['):s.index(']', s.index('adoptKinds: ['))]
    assert "if (route.screen === 'portfolios') { stage('portfolios'); return; }" in s
    # el Universo es un overlay encima del OS: abrirlo no cierra Khipus OS
    assert "if (route.screen === 'universe') { if (window._go3D) window._go3D(); return; }" in s


def test_una_sola_peticion_de_insights_al_arrancar():
    s = _r('engine/cockpit.js')
    # inicio y Oportunidades comparten caché; stage('empty') no pinta dos veces seguidas
    assert s.count("fetch('/api/matrix/insights'") == 1
    assert 'function _matrixInsights(en)' in s
    assert "_paintHome(Date.now() - _homeTs > 30000)" in s
    assert 'if (!D.wall().children.length) stageEmpty(D.wall());' not in s


def test_marca_tools_e_invocar():
    """2026-10-06 (Fabrizio): nombre Khipus Finance Intelligence, letra redondeada (Nunito), botón principal
    Tools/Herramientas y tocar un agente lo INVOCA a la conversación."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    s = open(os.path.join(root, 'engine', 'cockpit.js'), encoding='utf-8').read()
    app = open(os.path.join(root, 'app.html'), encoding='utf-8').read()
    assert 'Khipus<span class="sub">Finance Intelligence</span>' in s and '<title>Khipus Finance Intelligence · 2026</title>' in app
    assert 'Khipus Finance AI' not in app and 'family=Nunito:wght@' in app
    assert "L('Herramientas', 'Tools')" in s and 'SVG.tools' in s and "L('Más', 'More')" not in s
    # invocar: la mascota en la barra, el token del agente se antepone al enviar, ✕ lo despide
    assert '<span id="kos-inv" hidden></span>' in s and "invokeAgent(id);" in s
    assert "v = (ckLang() === 'en' ? AGENT_TOK[_inv][1] : AGENT_TOK[_inv][0]) + ' ' + v;" in s
    assert "L('Invocar', 'Invoke')" in s and "L('Despedir a ', 'Dismiss ')" in s
    w = open(os.path.join(root, 'engine', 'oswindows.js'), encoding='utf-8').read()
    assert "L('Invocar a ' + a.es, 'Invoke ' + a.en)" in w and 'cc.invoke(aid)' in w
