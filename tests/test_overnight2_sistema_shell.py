"""Khipus OS (2026-10-10) — el armazón de 🩺 Sistema (window.openSistema) migrado a los tokens --os-*.

app.html: #sistema-panel / #sistema-overlay llevan .kos-themed (tokens claro/oscuro fuera de #bcp-ov), título en
Nunito (sin Fraunces), pestañas = control segmentado de píldoras, tarjetas OS del diagnóstico con texto AA por nivel
(ok = --os-good-ink · aviso = --os-warn-ink · falla = --os-bad-ink), foco visible y ≤760 px a pantalla completa.
La insignia 👥 Clientes deja el #FFB300 fijo. Los ids, funciones y flujos con PIN (_tradeFetch) no cambian.

Con node: la tarjeta del diagnóstico elige detail_en / fixes[].en / fix_en en inglés si el servidor los manda
(la voz ya lo hace), cae al texto original si no, y no repite el «— QUÉ HACER:» que el detalle de la voz ya trae."""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
HTML = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()


def _css_section():
    a = HTML.index('/* ----- 🩺 Sistema — Khipus OS')
    b = HTML.index('@media(prefers-reduced-motion:reduce){\n  #sistema-panel', a)
    return HTML[a:HTML.index('}\n}', b) + 3]


def _markup():
    a = HTML.index('<div class="settings-overlay kos-themed" id="sistema-overlay"')
    return HTML[a:HTML.index('</aside>', a) + 8]


def _rule(css, selector):
    m = re.search(re.escape(selector) + r'\{([^}]*)\}', css)
    assert m, 'falta la regla ' + selector
    return m.group(1)


def _js_section():
    a = HTML.index('/* ── Estado del Sistema — diagnóstico en vivo')
    b = HTML.index('window.closePropuestas = function', a)
    return HTML[a:b]


def _strip_var_fallbacks(s):
    """Quita cada var(--x, respaldo) (respaldos anidados incluidos) → quedan solo colores FIJOS."""
    out, i = [], 0
    while True:
        j = s.find('var(', i)
        if j < 0:
            out.append(s[i:])
            return ''.join(out)
        out.append(s[i:j])
        depth, k = 0, j
        while k < len(s):
            if s[k] == '(':
                depth += 1
            elif s[k] == ')':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        i = k + 1


CSS = _css_section()
MARKUP = _markup()
JS = _js_section()
LEGACY_HEX = ['#FFB300', '#1a1200', '#1db954', '#e23b3b', '#e6a23c', '#43C896', '#04241a', '#8a5aff', '#7aa2ff',
              '#d9a441', '#f87171', '#888']


# ── armazón: .kos-themed, sin ancho en línea, ids y funciones intactos ─────────────────────────────────
def test_panel_and_overlay_are_kos_themed():
    panel = re.search(r'<aside[^>]*id="sistema-panel"[^>]*>', MARKUP).group(0)
    assert 'kos-themed' in panel and 'settings-panel' in panel        # .settings-panel conserva el .show/transform
    assert 'width:520px' not in panel                                  # el ancho vive en el CSS (≤760 px → 100 %)
    ov = re.search(r'<div[^>]*id="sistema-overlay"[^>]*>', MARKUP).group(0)
    assert 'kos-themed' in ov
    assert '#sistema-overlay{background:var(--kos-scrim' in CSS


def test_ids_functions_and_pin_flows_kept():
    for i in ('sistema-overlay', 'sistema-panel', 'sistema-title', 'sistema-close', 'sistema-tabseg', 'sistema-diag',
              'diag-refresh', 'diag-summary', 'diag-body', 'recon-box', 'sistema-registro', 'registro-filter-actor',
              'registro-refresh', 'registro-body', 'sistema-propuestas', 'propuestas-run', 'propuestas-refresh',
              'propuestas-summary', 'investigar-q', 'investigar-go', 'investigar-status', 'propuestas-body', 'sistema-gasto'):
        assert f'id="{i}"' in MARKUP, i
    for t in ('diag', 'registro', 'propuestas', 'gasto'):
        assert f'data-t="{t}"' in MARKUP
    for fn in ('window.openSistema = function', 'window.closeSistema = function', 'window.openDiagnostics = async function',
               'window.openRegistro = async function', 'window.openPropuestas = async function', 'window.runAgentes = function',
               'window.lanzarInvestigacion = async function', 'function _resolveProposal(card, id, verb)'):
        assert fn in HTML, fn
    # escrituras de la ontología siguen pasando por el PIN de operador (_tradeFetch), sin rutas nuevas
    assert JS.count('window._tradeFetch(') == 3
    assert "/api/ontology/agents/proposals/${encodeURIComponent(id)}/${verb}" in JS
    assert "/api/ontology/agents/run" in JS and "/api/ontology/agents/investigar" in JS
    # los manejadores siguen encontrando sus piezas
    for cls in ('prop-card', 'prop-approve', 'prop-reject', 'prop-status', 'prop-field', 'data-k='):
        assert cls in JS, cls
    assert 'data-id="${esc(p.id)}"' in JS


# ── título sin Fraunces, tipografía del OS ───────────────────────────────────────────────────────────────
def test_title_uses_os_font_not_fraunces():
    assert 'id="sistema-title" class="ksys-title"' in MARKUP
    title = _rule(CSS, '#sistema-panel .ksys-title')
    assert 'Fraunces' not in title and 'font-display' not in title
    assert 'font-family:var(--os-font' in title
    panel = _rule(CSS, '#sistema-panel')
    assert 'font-family:var(--os-font' in panel and 'Fraunces' not in panel
    assert 'Fraunces' not in CSS


# ── estados con texto AA y punto de estado relleno ───────────────────────────────────────────────────────
def test_status_levels_use_aa_ink_tokens():
    assert '--ksys-ink:var(--os-good-ink' in _rule(CSS, '.ksys-lv-ok')
    assert '--ksys-ink:var(--os-warn-ink' in _rule(CSS, '.ksys-lv-warn')
    assert '--ksys-ink:var(--os-bad-ink' in _rule(CSS, '.ksys-lv-bad')
    assert '--ksys-fill:var(--os-good' in _rule(CSS, '.ksys-lv-ok')
    assert '--ksys-fill:var(--os-bad' in _rule(CSS, '.ksys-lv-bad')
    # el texto de estado y el «Qué hacer» leen la tinta AA del nivel; el punto lee el relleno vivo
    assert 'color:var(--ksys-ink' in _rule(CSS, '#sistema-panel .ksys-st')
    assert 'color:var(--ksys-ink' in _rule(CSS, '#sistema-panel .ksys-fix-h')
    assert 'background:var(--ksys-fill' in _rule(CSS, '#sistema-panel .ksys-dot')
    # tarjetas OS: sin bordes duros, radio y sombra del tema
    card = _rule(CSS, '#sistema-panel .ksys-card')
    assert 'border:' not in card and 'border-left' not in card
    assert 'var(--os-r' in card and 'var(--os-shadow' in card and 'var(--os-surface' in card
    # la tarjeta marca su nivel (ok/warn/bad/off) y el punto + título + estado + detalle + «Qué hacer»
    for piece in ('ksys-lv-${lv}', 'data-level="${lv}"', 'class="ksys-dot"', 'class="ksys-name"', 'class="ksys-st"',
                  'class="ksys-detail"', 'class="ksys-fix"', 'class="ksys-fix-h"'):
        assert piece in JS, piece


def test_no_fixed_legacy_colors_in_sistema_shell():
    fixed_css = _strip_var_fallbacks(CSS)
    fixed_js = _strip_var_fallbacks(JS)
    for hx in LEGACY_HEX:
        assert hx.lower() not in fixed_css.lower(), hx
        assert hx.lower() not in fixed_js.lower(), hx
        assert hx.lower() not in MARKUP.lower(), hx
    # sin estilos en línea viejos en las tarjetas
    assert 'border-left:3px solid' not in JS
    assert "font-family:'JetBrains Mono'" not in JS


# ── pestañas segmentadas, botones píldora, foco visible, móvil ───────────────────────────────────────────
def test_segmented_pill_tabs_and_pill_buttons():
    seg = _rule(CSS, '#sistema-panel #sistema-tabseg')
    assert 'border-radius:999px' in seg and 'background:var(--os-surface-3' in seg
    btn = _rule(CSS, '#sistema-panel #sistema-tabseg button')
    assert 'border-radius:999px' in btn and 'color:var(--os-ink-2' in btn
    act = _rule(CSS, '#sistema-panel #sistema-tabseg button.active')
    assert 'background:var(--os-surface' in act and 'color:var(--os-ink' in act
    assert 'role="tablist"' in MARKUP and MARKUP.count('role="tab"') == 4
    assert "b.setAttribute('aria-selected'" in HTML
    kb = _rule(CSS, '#sistema-panel .key-btn')
    assert 'border-radius:999px' in kb and 'border:0' in kb
    assert 'background:var(--os-btn' in _rule(CSS, '#sistema-panel .key-btn.ksys-pri')
    # 🤖 Conectar IAs (lo crea mcpconnect.js con estilo en línea) → tarjeta OS
    entry = _rule(CSS, '#sistema-panel #kmcp-entry')
    assert 'background:var(--os-surface' in entry and 'border:0' in entry and 'height:auto' in entry


def test_focus_visible_and_mobile_full_screen():
    assert re.search(r'#sistema-panel button:focus-visible,[^{]*\{outline:2px solid var\(--os-accent', CSS)
    m = re.search(r'@media\(max-width:760px\)\{(.*?)\n\}', CSS, re.S)
    assert m
    mob = m.group(1)
    assert re.search(r'#sistema-panel\{width:100%;max-width:100%;border-radius:0', mob)
    assert 'grid-template-columns:repeat(2' in mob
    assert '@media(prefers-reduced-motion:reduce)' in CSS


# ── insignia 👥 Clientes ──────────────────────────────────────────────────────────────────────────────────
def test_clients_badge_uses_tokens():
    tag = re.search(r'<b id="tab-clients-badge"[^>]*>', HTML).group(0)
    assert 'kos-themed' in tag and '#FFB300' not in tag and 'background:' not in tag
    rule = _rule(HTML, '#tab-clients-badge')
    assert 'background:var(--os-warn' in rule and 'border-radius:999px' in rule
    assert 'font-family:var(--os-font' in rule


# ── textos del armazón en ES y EN ────────────────────────────────────────────────────────────────────────
def test_shell_strings_are_bilingual():
    m = re.search(r'const SYS_I18N = \{\s*es:\{(.*?)\},\s*en:\{(.*?)\},\s*\};', HTML, re.S)
    assert m
    key_re = re.compile(r"(\w+):'")
    es, en = set(key_re.findall(m.group(1))), set(key_re.findall(m.group(2)))
    assert es == en and len(es) >= 20
    used = set(re.findall(r'data-ksys-(?:t|h|ph|al)="(\w+)"', MARKUP))
    assert used and used <= es, used - es
    for t in ('diag', 'registro', 'propuestas', 'gasto'):
        assert 't_' + t in es
    # tarjetas de registro/propuestas también en los dos idiomas
    for es_s, en_s in (("'Aprobar', 'Approve'", None), ("'Rechazar', 'Reject'", None), ("'por', 'by'", None),
                       ("'Fuentes citadas', 'Cited sources'", None), ("'Sin verificar', 'Unverified'", None)):
        assert es_s in JS, es_s
    assert 'PROPOSAL_FIELD_LABELS_EN' in JS


# ── con node: selección bilingüe del detalle / «Qué hacer» ──────────────────────────────────────────────
_HARNESS = r"""
const vm = require('vm');
const src = %s;
const cases = %s;
const out = {};
for (const lang of ['es', 'en']) {
  const ctx = { window: { LANG: lang }, out: null };
  ctx.esc = s => String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  vm.createContext(ctx);
  vm.runInContext(src + '\n;out = {card: (k, s) => _diagCard(k, s), level: s => _diagLevel(s), texts: (s, l) => _diagTexts(s, l)};', ctx);
  const r = {};
  for (const [name, c] of Object.entries(cases)) {
    const lv = ctx.out.level(c.s);
    r[name] = { level: lv, card: ctx.out.card(c.k, c.s), texts: ctx.out.texts(c.s, lv) };
  }
  out[lang] = r;
}
console.log(JSON.stringify(out));
"""

VOICE = {
    'configured': True, 'agent_configured': True, 'ok': True, 'latency_ms': 900,
    'checks': [{'id': 'overrides', 'level': 'warn', 'es': 'Sin idioma por sesión.', 'en': 'No per-session language.'}],
    'fixes': [{'es': 'Activa "Language" en Overrides.', 'en': 'Enable "Language" in Overrides.'},
              {'es': 'Sincroniza las instrucciones.', 'en': 'Sync the instructions.'}],
    'detail': 'Khipu (voz) conecta, con avisos: • Sin idioma por sesión. — QUÉ HACER: 1) Activa "Language" en Overrides. '
              '2) Sincroniza las instrucciones.',
    'detail_en': 'Khipu (voice) connects, with warnings: • No per-session language. — WHAT TO DO: 1) Enable "Language" in '
                 'Overrides. 2) Sync the instructions.',
}
CASES = {
    'voice': {'k': 'elevenlabs', 's': VOICE},
    'plain_es_only': {'k': 'gemini', 's': {'configured': True, 'ok': True, 'detail': 'Key válida — gemini respondió.'}},
    'flat_fix': {'k': 'fmp', 's': {'configured': True, 'ok': False, 'detail': 'Falla <b>x</b>', 'detail_en': 'Fails <b>x</b>',
                                   'fix_es': 'Cambia el plan.', 'fix_en': 'Change the plan.'}},
    'arrow_hint': {'k': 'claude', 's': {'configured': True, 'ok': False,
                                        'detail': 'FAST: m ✗ (400) → Saldo agotado: recarga en la consola del proveedor.'}},
    'off': {'k': 'nvidia', 's': {'configured': False, 'ok': False, 'detail': 'NVIDIA_KEY no está.'}},
    'quota': {'k': 'finnhub', 's': {'configured': True, 'ok': True, 'quota': True, 'detail': 'Cuota agotada (HTTP 429).'}},
}


@pytest.fixture(scope='module')
def rendered():
    if not NODE:
        pytest.skip('node no disponible')
    js = _HARNESS % (json.dumps(JS[:JS.index('window.openDiagnostics = async function')]), json.dumps(CASES))
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_levels(rendered):
    lv = {k: v['level'] for k, v in rendered['es'].items()}
    assert lv == {'voice': 'warn', 'plain_es_only': 'ok', 'flat_fix': 'bad', 'arrow_hint': 'bad', 'off': 'off', 'quota': 'warn'}
    assert 'ksys-lv-warn' in rendered['es']['voice']['card']
    assert 'CON AVISOS' in rendered['es']['voice']['card'] and 'WARNINGS' in rendered['en']['voice']['card']
    assert 'NO CONFIGURADO' in rendered['es']['off']['card'] and 'NOT SET UP' in rendered['en']['off']['card']


def test_voice_card_picks_english_detail_and_fixes(rendered):
    en, es = rendered['en']['voice'], rendered['es']['voice']
    assert en['texts']['detail'] == 'Khipu (voice) connects, with warnings: • No per-session language.'
    assert en['texts']['fixes'] == ['Enable "Language" in Overrides.', 'Sync the instructions.']
    assert 'What to do' in en['card'] and 'WHAT TO DO' not in en['card'] and 'QUÉ HACER' not in en['card']
    assert 'Activa' not in en['card'] and 'conecta, con avisos' not in en['card']
    assert '<li>No per-session language.</li>' in en['card']         # «• …» → lista
    assert '<ol><li>Enable &quot;Language&quot; in Overrides.</li>' in en['card']
    # en español: el detalle original sin repetir el «— QUÉ HACER:», y los arreglos en español
    assert es['texts']['detail'] == 'Khipu (voz) conecta, con avisos: • Sin idioma por sesión.'
    assert es['texts']['fixes'] == ['Activa "Language" en Overrides.', 'Sincroniza las instrucciones.']
    assert 'Qué hacer' in es['card'] and es['card'].count('QUÉ HACER') == 0
    assert 'Khipu / ElevenLabs' in es['card']


def test_fallbacks_and_flat_fix_fields(rendered):
    # sin detail_en: en inglés se muestra el texto del servidor tal cual (nunca vacío) con etiquetas en inglés
    en = rendered['en']['plain_es_only']
    assert en['texts']['detail'] == 'Key válida — gemini respondió.' and 'OPERATIONAL' in en['card']
    assert 'Backup AI channel' in en['card'] and 'Canal de respaldo' in rendered['es']['plain_es_only']['card']
    # fix_es / fix_en planos
    assert rendered['en']['flat_fix']['texts'] == {'detail': 'Fails <b>x</b>', 'fixes': ['Change the plan.']}
    assert rendered['es']['flat_fix']['texts'] == {'detail': 'Falla <b>x</b>', 'fixes': ['Cambia el plan.']}
    assert '&lt;b&gt;x&lt;/b&gt;' in rendered['en']['flat_fix']['card'] and '<b>x</b>' not in rendered['en']['flat_fix']['card']
    # la pista « → …» del servidor pasa al bloque «Qué hacer»
    ah = rendered['es']['arrow_hint']['texts']
    assert ah == {'detail': 'FAST: m ✗ (400)', 'fixes': ['Saldo agotado: recarga en la consola del proveedor.']}
    # sin arreglos ni pista → sin bloque «Qué hacer»
    assert 'ksys-fix' not in rendered['es']['plain_es_only']['card']
