"""Comité → 💼 Mi cartera con la piel de Khipus OS (2026-10-09, "el comité todavía no está actualizado").

engine/pfcommittee.js y engine/pfreports.js pintaban DENTRO del comité con los colores fijos del
tema oscuro viejo (#E8EDFB, #00E0FF, #2BE38B…): en el tema claro el texto quedaba invisible.
Ahora todo color es un token --os-* / --cm-* con el valor OSCURO de respaldo: var(--x, respaldo).

· Estático: ningún color hex/rgba suelto fuera de un respaldo var(--x, …), de una definición de
  token (--x:#…, ventana de impresión) o del mapa de respaldos del gráfico ('--x': '#…').
· Dinámico (node): se pintan las pantallas reales (perfil, diagnóstico, reportes con gráfico,
  noticias, pregúntale) y el HTML resultante cumple lo mismo; ids pfc-/pfr-/pfa- y data-* intactos.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
FILES = ['engine/pfcommittee.js', 'engine/pfreports.js']
LEGACY = ['#2BE38B', '#FF4D6A', '#FFB300', '#9BA6C4', '#E8EDFB', '#0B1222', '#00E0FF', '#5FC6E8',
          '#7C87A3', '#C9D2EA', '#7ecbff', '#24304a', '#5f6b8a', '#D5DCF0', '#06090F']
COLOR = re.compile(r'(?<![&\w])#[0-9a-fA-F]{3,8}\b|rgba?\(')


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
    """Colores que NO son respaldo de var(), ni definición de token, ni entrada del mapa de respaldos."""
    spans = _var_fallback_spans(text)
    bad = []
    for m in COLOR.finditer(text):
        p = m.start()
        if any(a < p < b for a, b in spans):
            continue
        before = text[max(0, p - 200):p]
        if re.search(r"--[\w-]+:[^;{}'\"]*$", before):        # --os-line:rgba(…) / --os-ink:#…
            continue
        if re.search(r"'--[\w-]+':\s*'$", before):             # DARK = { '--os-accent': '#4C8DF6' }
            continue
        bad.append(text[max(0, p - 40):p + 12].replace('\n', ' '))
    return bad


@pytest.mark.parametrize('rel', FILES)
def test_sin_colores_fijos_fuera_de_tokens(rel):
    src = open(os.path.join(ROOT, rel), encoding='utf-8').read()
    assert stray_colors(src) == []
    low = src.lower()
    assert [c for c in LEGACY if c.lower() in low] == []          # ni siquiera como respaldo
    assert 'var(--cm-warn,#B7791F)' in src                         # ámbar del comité con su respaldo
    assert 'Inter,' not in src                                     # letra de Khipus OS, no la vieja


def test_el_detector_si_detecta_colores_sueltos():
    assert stray_colors("style=\"color:#E8EDFB\"") and stray_colors("background:rgba(0,224,255,.12)")
    assert not stray_colors("color:var(--os-ink,#F2F2F5);border:1px solid var(--os-line,rgba(255,255,255,.07))")
    assert not stray_colors("background:var(--c,var(--os-ink-2,#A6A8B5))")
    assert not stray_colors(":root{--os-ink:#111216;--os-line:rgba(17,18,22,.14)}")


def test_foco_visible_y_texto_semantico_legible():
    """Foco de teclado con contorno de acento (no el anillo de 12 % casi invisible) y verde/rojo de TEXTO
    con los tokens --cm-good/--cm-bad (la impresión los define en claro)."""
    for rel in FILES:
        src = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        assert 'outline:none;box-shadow:0 0 0 3px var(--kos-accent-soft' not in src, rel
        assert 'outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px' in src, rel
        assert "GOOD = 'var(--cm-good,#2fbf5b)'" in src and "BAD = 'var(--cm-bad,#F47C7C)'" in src, rel
    rep = open(os.path.join(ROOT, 'engine/pfreports.js'), encoding='utf-8').read()
    assert '--cm-good:#066B06;--cm-bad:#A82424;--cm-warn:#7F5200;--cm-warn-fill:#B7791F;--cm-ai:#6236C9;' in rep


def test_grafico_lee_tokens_al_pintar():
    src = open(os.path.join(ROOT, 'engine/pfreports.js'), encoding='utf-8').read()
    assert 'getComputedStyle' in src and "getElementById('cm-ov')" in src
    # los atributos de presentación SVG no aceptan var(): el color va en style="stroke:var(--x, valor leído)"
    assert ' stroke="#' not in src and ' fill="#' not in src


JS = r"""
const ROOT = process.argv[1];
const store = {};
global.localStorage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } };
const reg = {};
const byId = id => (/-css$/.test(id) ? (reg[id] || null) : (reg[id] = reg[id] || { id: id, value: '', style: {}, scrollIntoView() {} }));
const styles = [];
global.document = { getElementById: byId, addEventListener() {}, hidden: false,
  createElement: () => ({ id: '', textContent: '' }), head: { appendChild(st) { reg[st.id] = st; styles.push(st.textContent); } } };
global.window = { LANG: 'es', NODE_BY_ID: { Nvidia: { label: 'NVIDIA', mkt: 'NVDA' } }, MKT: { pos: {} } };
const _st = global.setTimeout; global.setTimeout = (f, ms) => (ms >= 9000 ? 0 : _st(f, ms));
const curve = Array.from({ length: 30 }, (_, i) => ({ d: '2026-09-' + String(i + 1).padStart(2, '0'), idx: 100 + i * 0.3, spy_idx: 100 + i * 0.1 }));
const RES = { ok: true, health: { score: 64, verdict: 'Bien', tone: 'warn' }, kpis: { value_usd: 3870, vol_ann_pct: 41, max_drawdown_pct: -27, var95_1d_usd: 160 },
  profile: { label: 'Moderado', target_vol: 22, max_position: 25, max_sector: 40 }, performance: { pnl_usd: 620, pnl_pct: 19 },
  positions: [{ label: 'NVIDIA', symbol: 'NVDA', weight_pct: 60, risk_contrib_pct: 70, conviction: 30 }, { label: 'TSMC', symbol: 'TSM', weight_pct: 40, risk_contrib_pct: 30, conviction: null }],
  sectors: [{ label: 'Semis', weight_pct: 100 }],
  actions: [{ id: 'a1', kind: 'reduce', priority: 1, label: 'NVIDIA', entity_id: 'Nvidia', from_pct: 60, to_pct: 25, delta_usd: -900, why_es: 'Pesa mucho', why_en: 'Too big' }],
  explanation: { ai: true, text: 'Hola' }, coverage: { analyzed: 2, requested: 2, researched: 1, not_researched: [{ label: 'TSMC', entity_id: 'TSMC' }] }, excluded: [],
  geo_risks: [{ label: 'TSMC', items: [{ title_es: 'Taiwán', why_es: 'fábrica', severity: 72, source: 'GDELT', time: '2026-10-08', url: 'https://x.org' }] }],
  disclaimer: 'IA, no asesoría.', source: 'Yahoo', as_of: '2026-10-09', saved_id: 'r1' };
const REP = { ok: true, id: 'rp1', title: 'Reporte', performance: { value_now_usd: 3870, period_change_pct: 4, period_change_usd: 150, spy_period_pct: 2, vs_spy_pts: 2, initial_usd: 3000, since_start_pct: 29, period_max_drawdown_pct: -6 },
  summary: { ai: true, text: '**Bien**' }, curve: curve, contributions: [{ label: 'NVIDIA', contrib_usd: 200, change_pct: 7 }, { label: 'TSMC', contrib_usd: -50, change_pct: -5 }],
  advisor: { actions: [{ id: 'x', why_es: 'y' }], disclaimer: 'IA' }, news: [{ label: 'NVIDIA', freshness: 'new', published_at: '2026-10-09', title: 'T', url: 'https://x.org', holdings: ['NVDA'] }], source: 'Yahoo' };
global.fetch = (url) => {
  url = String(url); let b = {};
  if (url.includes('/api/committee/portfolio')) b = RES;
  else if (url.includes('kind=committee')) b = { reports: [{ id: 'r1', created_at: '2026-10-07T12:00:00Z', title: 'Mi tesis', summary: '64/100' }] };
  else if (url.includes('/api/portfolio-report/list')) b = { reports: [{ id: 'rp1', title: 'Reporte', read: false, change_pct: 4 }] };
  else if (url.includes('/watches')) b = { watches: [] };
  else if (url.includes('/generate')) b = REP;
  else if (url.includes('/api/news/portfolio')) b = { items: REP.news };
  else if (url.includes('/ask')) b = { answer: 'Por **NVIDIA**', sources: [{ label: 'Yahoo' }] };
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(b) });
};
window.KhipuPortfolios = { _list: () => [{ id: 'p1', name: 'Mi tesis', positions: [{ nodeId: 'Nvidia', shares: 10, avgPrice: 100 }], cash: 0, startCash: 1000, createdAt: 1 }] };
require(ROOT + '/engine/pfcommittee.js');
require(ROOT + '/engine/pfreports.js');
const tick = () => new Promise(r => _st(r, 20));
const el = { innerHTML: '', querySelectorAll: () => [], scrollIntoView() {} };
const out = {};
(async () => {
  window.KhipuPortfolioCommittee.render(el); out.profile_edit = el.innerHTML;
  localStorage.setItem('kh_investor_profile', JSON.stringify({ risk: 'moderado', involvement: 'informed', answers: {} }));
  window.KhipuPortfolioCommittee.render(el); out.idle = el.innerHTML;
  reg['pfc-run'].onclick(); await tick(); await tick(); out.diag = el.innerHTML;
  const ctx = { source: { key: 'pf:p1', label: 'Mi tesis', positions: [{ id: 'Nvidia', label: 'NVIDIA', symbol: 'NVDA', shares: 10 }] }, profile: { involvement: 'informed' } };
  const box = { innerHTML: '', querySelectorAll: () => [] };
  window.KhipuPortfolioExtras.render(box, 'reports', ctx); await tick(); out.reports = box.innerHTML;
  reg['pfr-gen'].onclick(); await tick(); await tick(); out.report = box.innerHTML;
  window.KhipuPortfolioExtras.render(box, 'news', ctx); await tick(); out.news = box.innerHTML;
  window.KhipuPortfolioExtras.render(box, 'ask', ctx); reg['pfa-q'].value = 'hola'; reg['pfa-send'].onclick(); await tick(); out.ask = box.innerHTML;
  out.css = styles;
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


def test_pantallas_pintadas_solo_con_tokens(screens):
    for name, html in screens.items():
        if name == 'css':
            continue
        assert html, name
        assert stray_colors(html) == [], name
        assert not [c for c in LEGACY if c.lower() in html.lower()], name
    assert len(screens['css']) == 2 and all(stray_colors(c) == [] for c in screens['css'])


def test_perfil_es_control_segmentado_y_conserva_datos(screens):
    h = screens['profile_edit']
    assert h.startswith('<div class="pfo">')
    assert h.count('class="pfo-seg" role="radiogroup"') == 4            # 3 preguntas + involucramiento
    for q in ('drop', 'horizon', 'goal', 'involvement'):
        assert 'data-q="%s"' % q in h
    assert 'data-v="sell"' in h and 'id="pfc-save-prof"' in h and 'cm-tab' not in h


def test_diagnostico_os_con_mascotas_y_mismos_controles(screens):
    i, d = screens['idle'], screens['diag']
    assert 'id="pfc-src"' in i and 'id="pfc-run"' in i and 'id="pfc-edit-prof"' in i
    assert 'role="tablist"' in i and all('data-sec="%s"' % s in i for s in ('diag', 'reports', 'news', 'ask'))
    assert 'pfo-ring' in d and 'pfo-kpis' in d and 'pfo-act' in d
    assert 'data-apply="a1"' in d                                        # aplicar en la SIMULACIÓN, igual que antes
    assert 'data-trade=' not in d                                        # cartera simulada: nada de órdenes
    # texto rojo/ámbar con los tokens de TEXTO del comité (4.5:1 sobre su píldora en el tema claro)
    assert 'var(--cm-bad,#F47C7C)' in d and 'var(--cm-warn,#B7791F)' in d
    assert 'var(--os-bad,' not in d and 'var(--os-good,' not in d
    assert 'data-past="r1"' in d                                         # análisis anteriores siguen listados


def test_reportes_grafico_y_chat_con_tokens(screens):
    assert 'data-rid="rp1"' in screens['reports'] and 'id="pfr-sched"' in screens['reports']
    rep = screens['report']
    assert 'id="pfr-print"' in rep and 'id="pfr-print-btn"' in rep and 'id="pfr-back"' in rep
    assert 'stroke:var(--os-accent,#4C8DF6)' in rep                     # tu cartera (respaldo oscuro sin DOM)
    assert 'stroke:var(--os-ink-3,#6E7080)' in rep and 'stroke-dasharray:5 4' in rep   # S&P 500 punteado
    assert 'class="pfe-seg" role="radiogroup"' in screens['news'] and 'data-nd="7"' in screens['news']
    ask = screens['ask']
    assert 'class="pfe-msg me"' in ask and 'id="pfa-q"' in ask and 'id="pfa-send"' in ask


def test_lo_que_dice_el_comite_muestra_negritas_no_asteriscos():
    """La explicación de la IA trae **negritas** (markdown): se ven en negrita, no con asteriscos (y sigue escapada)."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    s = open(os.path.join(root, 'engine', 'pfcommittee.js'), encoding='utf-8').read()
    assert "esc(r.explanation.text).replace(/\\*\\*([^*\\n]+)\\*\\*/g, '<b>$1</b>')" in s
