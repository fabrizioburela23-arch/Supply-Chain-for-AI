"""tests/test_committee_os_ui.py — el Comité de inversión con el look de Khipus OS (2026-10-09).

Fabrizio: "el comité todavía no está actualizado". engine/committee.js seguía con el tema oscuro viejo
(fondos #06090F/#0B1222, letra Inter) y personas humanas dibujadas (Valeria, Kenji…). Ahora:
  · los tokens --os-* del overlay son COPIA EXACTA de los de engine/cockpit.js (claro y oscuro)
  · los agentes son las MASCOTAS de engine/mascot.js (Analista, Radar, Cadena, Técnico, Comité)
    con una insignia de rol; KhipuCommittee.avatar() sigue existiendo (lo usa engine/khipu_chat.js)
  · no quedan nombres de personas ni fondos oscuros fijos
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
SRC = open(os.path.join(ROOT, 'engine', 'committee.js'), encoding='utf-8').read()
COCKPIT = open(os.path.join(ROOT, 'engine', 'cockpit.js'), encoding='utf-8').read()
needs_node = pytest.mark.skipif(not NODE, reason='requiere node')

# DOM falso: getElementById encuentra elementos con .id asignado y, si no, crea un "stub" estable para
# cualquier id que aparezca como id="…" en el HTML ya pintado (así render() puede pintar #cm, #cm-body…).
HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const ROOT = process.argv[1];
const LANG = process.argv[2] || 'es';
const WITH_MASCOT = process.argv[3] !== 'no-mascot';
const byId = {}, all = [];
function ClassList(el) { this.el = el; }
ClassList.prototype._get = function () { return (this.el._cls || '').split(/\s+/).filter(Boolean); };
ClassList.prototype.add = function (c) { const a = this._get(); if (a.indexOf(c) < 0) a.push(c); this.el._cls = a.join(' '); };
ClassList.prototype.remove = function (c) { this.el._cls = this._get().filter(x => x !== c).join(' '); };
ClassList.prototype.contains = function (c) { return this._get().indexOf(c) >= 0; };
class El {
  constructor(tag) { this.tagName = String(tag || 'div').toUpperCase(); this.children = []; this._cls = ''; this._html = ''; this._text = '';
    this._id = ''; this.style = {}; this.attrs = {}; this.listeners = {}; this.classList = new ClassList(this); all.push(this); }
  get id() { return this._id; } set id(v) { this._id = String(v); byId[this._id] = this; }
  get className() { return this._cls; } set className(v) { this._cls = String(v); }
  get innerHTML() { return this._html; } set innerHTML(v) { this._html = String(v); }
  get textContent() { return this._text || this._html; } set textContent(v) { this._text = String(v); }
  appendChild(c) { this.children.push(c); return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); } getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
  querySelectorAll() { return []; } querySelector() { return null; }
  getContext() { return {}; }
}
const store = { eco_lang: LANG };
const ctx = { console, Date, Math, JSON, Promise, encodeURIComponent, isNaN, Number, String,
  setTimeout: (fn, ms) => setTimeout(fn, Math.min(ms || 0, 5)), clearTimeout, setInterval: () => 0, clearInterval: () => {},
  localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } },
  getComputedStyle: () => ({ getPropertyValue: () => '' }),
};
ctx.window = ctx; ctx.globalThis = ctx; ctx.LANG = LANG;
const body = new El('body'); body._cls = 'dark';
ctx.document = { readyState: 'complete', body, head: new El('head'), documentElement: new El('html'),
  createElement: t => new El(t), addEventListener: () => {},
  getElementById: id => {
    if (byId[id]) return byId[id];
    if (all.some(e => e._html.indexOf('id="' + id + '"') >= 0)) { const s = new El('div'); s.id = id; return s; }
    return null;
  } };
const replies = {};
ctx.fetch = (url) => Promise.resolve({ status: 200, text: () => Promise.resolve(JSON.stringify(replies[url.replace(/\?.*$/, '')] || {})) });
vm.createContext(ctx);
if (WITH_MASCOT) vm.runInContext(fs.readFileSync(ROOT + '/engine/mascot.js', 'utf8'), ctx);
vm.runInContext(fs.readFileSync(ROOT + '/engine/committee.js', 'utf8'), ctx);
const KC = ctx.KhipuCommittee;
const out = {};
function css() { const s = ctx.document.head.children.find(c => c.id === 'cm-styles'); return s ? s.textContent : ''; }
"""

MEMO = {
    'memo_id': 'm1', 'entity_id': 'nvidia', 'label': 'NVIDIA', 'symbol': 'NVDA', 'status': 'proposed', 'decision': 'BUY',
    'overall_conviction': 42, 'ai_used': True, 'created_at': '2026-10-09T10:00:00Z',
    'sizing': {'target_weight_pct': 3.2, 'reference_only': True, 'per_10k': 320, 'steps_es': ['paso'], 'steps_en': ['step']},
    'conviction': {'SHORT_TERM': {'score': 30, 'n_claims': 3, 'n_pos': 2, 'n_neg': 1, 'contra_share': 0, 'penalty': 1, 'horizon_weight': 1}},
    'inputs': {'n_claims': 3, 'n_contradictions': 0,
               'risk': {'ok': True, 'vol_ann_pct': 40, 'max_drawdown_pct': -20, 'beta_spy': 1.5, 'source': 'yahoo', 'as_of': '2026-10-08'},
               'live': {'ok': True, 'price': 100, 'currency': 'USD'}},
    'memo': {
        'summary_es': 'Resumen del comité', 'summary_en': 'Committee summary', 'confidence': 0.6, 'review_date': '2026-11-01',
        'tally': {'for': 1, 'against': 1, 'neutral': 0, 'absent': 1},
        'track_validation': {'validated': False, 'min_n': 5, 'label_es': 'no validado', 'label_en': 'not validated', 'effect_es': 'mitad', 'effect_en': 'half'},
        'key_conclusions': [{'text_es': 'Conclusión', 'text_en': 'Conclusion', 'refs': ['C1']}],
        'debate': {'ai': True, 'n_ai': 2, 'n_rebuttals': 1, 'seconds': 30},
        'seats': [
            {'seat': 'fundamental', 'emoji': '📊', 'name_es': 'Analista fundamental', 'name_en': 'Fundamental analyst', 'stance': 'for', 'n_scored': 0, 'hits': 0, 'reliability': 0.5},
            {'seat': 'supply_chain', 'emoji': '🔗', 'name_es': 'Analista de cadena de suministro', 'name_en': 'Supply-chain analyst', 'stance': 'against', 'n_scored': 6, 'hits': 4, 'reliability': 0.6},
            {'seat': 'news', 'emoji': '📰', 'name_es': 'Analista de noticias', 'name_en': 'News analyst', 'stance': 'neutral', 'absent': True},
        ],
        'transcript': [
            {'seat': 'chair', 'emoji': '🏛', 'name_es': 'Presidente', 'name_en': 'Chair', 'kind': 'open', 'text_es': 'Abro la sesión', 'text_en': 'Opening'},
            {'seat': 'fundamental', 'emoji': '📊', 'name_es': 'Analista fundamental', 'name_en': 'Fundamental analyst', 'kind': 'position', 'stance': 'for',
             'text_es': 'Titular\nDetalle', 'text_en': 'Headline\nDetail', 'ai': True, 'secs': 12, 'refs': ['C1']},
            {'seat': 'supply_chain', 'emoji': '🔗', 'name_es': 'Analista de cadena de suministro', 'name_en': 'Supply-chain analyst', 'kind': 'position',
             'stance': 'against', 'text_es': 'Cuello de botella', 'text_en': 'Bottleneck'},
            {'seat': 'chair', 'emoji': '🏛', 'name_es': 'Presidente', 'name_en': 'Chair', 'kind': 'verdict', 'text_es': 'Veredicto', 'text_en': 'Verdict'},
        ],
    },
    'disclaimer_es': 'No es asesoría', 'disclaimer_en': 'Not advice',
}

PERSONAS = ['Valeria', 'Kenji', 'Amara', 'Diego', 'Leila', 'Henrik', 'Noa', 'Ingrid', 'Priya', 'Kwame', 'Mei', 'Isabel', 'Alex']


def _run(body, lang='es', mascot=True, timeout=60):
    js = HARNESS + body
    p = subprocess.run([NODE, '-e', js, ROOT, lang, 'mascot' if mascot else 'no-mascot'], capture_output=True, text=True, timeout=timeout)
    assert p.returncode == 0, p.stderr[-3000:]
    return json.loads(p.stdout.strip().splitlines()[-1])


def _decls(block):
    out = {}
    for part in block.split(';'):
        if ':' not in part:
            continue
        k, v = part.split(':', 1)
        k = k.strip()
        if k.startswith('--') or k == 'color-scheme':
            out[k] = ' '.join(v.split())
    return out


def _cockpit_tokens():
    light = re.search(r'body:not\(\.dark\) #bcp-ov\{(.*?)\}', COCKPIT, re.S)
    dark = re.search(r'body\.dark #bcp-ov[^{]*\{(.*?)\}', COCKPIT, re.S)
    shared = re.search(r'\n#bcp-ov\{(.*?)\}', COCKPIT, re.S)
    assert light and dark and shared, 'no encontré los tokens de Khipus OS en engine/cockpit.js'
    sh = {k: v for k, v in _decls(shared.group(1)).items() if k in ('--os-r', '--os-r-sm', '--os-font')}
    return _decls(light.group(1)), _decls(dark.group(1)), sh


# ── (a) mismos tokens que la Cabina, en claro y oscuro ──
@needs_node
def test_tokens_iguales_a_khipus_os():
    o = _run("KC.open(); out.css = css(); console.log(JSON.stringify(out));")
    cssx = o['css']
    light = re.search(r'body:not\(\.dark\) #cm-ov\{(.*?)\}', cssx)
    dark = re.search(r'body\.dark #cm-ov\{(.*?)\}', cssx)
    shared = re.search(r'\}#cm-ov\{(.*?)\}', cssx)
    assert light and dark and shared, cssx[:400]
    cl, cd, csh = _decls(light.group(1)), _decls(dark.group(1)), _decls(shared.group(1))
    kl, kd, ksh = _cockpit_tokens()
    assert len(kl) >= 20 and len(kd) >= 20
    for k, v in kl.items():
        assert cl.get(k) == v, ('claro', k, cl.get(k), v)
    for k, v in kd.items():
        assert cd.get(k) == v, ('oscuro', k, cd.get(k), v)
    for k, v in ksh.items():
        assert csh.get(k) == v, ('compartido', k, csh.get(k), v)
    # ámbar de aviso propio del comité, uno por tema: el vivo para rellenos/anillos y uno de TEXTO legible
    assert cl['--cm-warn-fill'] == '#B7791F' and cd['--cm-warn-fill'] == '#F2C46D'
    assert cl['--cm-warn'] == '#7F5200' and cd['--cm-warn'] == '#F2C46D'
    for k in ('--cm-good', '--cm-bad', '--cm-ai', '--cm-on-sem'):
        assert k in cl and k in cd, k
    # la hoja usa la letra y los tokens de Khipus OS
    sheet = re.search(r'#cm\{(.*?)\}', cssx).group(1)
    assert 'font-family:var(--os-font)' in sheet and 'background:var(--os-bg)' in sheet and 'var(--kos-shadow-lg)' in sheet
    assert 'background:var(--kos-scrim)' in shared.group(1)
    # móvil = hoja a pantalla completa
    assert re.search(r'@media\(max-width:760px\)\{#cm-ov\{align-items:stretch\}#cm\{[^}]*border-radius:0', cssx)


# ── (b) sin personas ──
def test_sin_nombres_de_personas():
    for n in PERSONAS:
        assert not re.search(r'\b' + n + r'\b', SRC), n
    for gone in ('CAST', 'HAIR', 'accSvg', 'avatarSvg', 'personName', 'castOf'):
        assert not re.search(r'\b' + gone + r'\b', SRC), gone


# ── (c) sin fondos oscuros fijos ni la letra vieja ──
def test_sin_fondos_oscuros_fijos():
    low = SRC.lower()
    for bad in ('#06090f', '#0b1222', 'rgba(11,18,34', 'rgba(21,28,45', 'rgba(3,6,12', '#3a4560', '#5f6b8a'):
        assert bad not in low, bad
    assert not re.search(r'font-family:\s*Inter', SRC)
    # los neones del tema viejo solo sobreviven en el PUENTE para módulos ajenos (pfcommittee.js)
    for neon in ('#00E0FF', '#2BE38B', '#FF4D6A', '#E8EDFB', '#FFB300'):
        assert SRC.count(neon) == 1, neon
        assert re.search(r"var LEGACY = \[[^;]*'" + re.escape(neon) + "'", SRC), neon


# ── (d) avatar = mascota + insignia ──
@needs_node
def test_avatar_es_la_mascota_con_insignia():
    o = _run(r"""
out.chain = KC.avatar('supply_chain', '🔗');
out.chair = KC.avatar('chair');
out.mini = KC.avatar('technical', '📈', true);
out.macro = KC.avatar('macro', '🌐');
out.crypto = KC.avatar('crypto', '₿', 48);
console.log(JSON.stringify(out));
""")
    assert 'class="km' in o['chain'] and 'aria-label="Cadena"' in o['chain']
    assert 'cm-badge' in o['chain'] and '<rect' in o['chain']           # insignia con el eslabón
    assert 'aria-label="Comité"' in o['chair'] and 'cm-badge' in o['chair']
    assert 'aria-label="Técnico"' in o['mini'] and 'cm-badge' not in o['mini']   # mini: sin insignia
    assert 'width:20px' in o['mini']
    assert 'aria-label="Analista"' in o['macro']
    assert 'aria-label="Radar"' in o['crypto'] and 'width:48px' in o['crypto']


@needs_node
def test_avatar_en_ingles_y_sin_mascot_js():
    o = _run("out.a = KC.avatar('supply_chain', '🔗'); console.log(JSON.stringify(out));", lang='en')
    assert 'aria-label="Chain"' in o['a']
    o = _run("out.a = KC.avatar('supply_chain', '🔗'); out.b = KC.avatar('chair'); console.log(JSON.stringify(out));", mascot=False)
    assert 'cm-mfb' in o['a'] and '🔗' in o['a'] and 'cm-badge' in o['a']   # círculo con el emoji del puesto
    assert '🏛' in o['b']
    assert 'var(--os-surface-2' in o['a']


# ── la sala del comité pintada con mascotas (memo real del servidor, simulado) ──
ROOM_JS = r"""
replies['/api/committee/entity/nvidia'] = { entity_id: 'nvidia', latest: MEMO, history: [MEMO, Object.assign({}, MEMO, { memo_id: 'm0', decision: 'HOLD' })] };
KC.open('nvidia');
setTimeout(function () {
  out.head = (byId['cm'] || {}).innerHTML || '';
  out.body = (byId['cm-body'] || {}).innerHTML || '';
  console.log(JSON.stringify(out));
}, 80);
"""


@needs_node
def test_sala_con_mascotas_es():
    o = _run('const MEMO = ' + json.dumps(MEMO) + ';' + ROOM_JS)
    head, body = o['head'], o['body']
    assert 'aria-label="Comité"' in head and 'Comité de inversión' in head and '🏛 Comité de inversión' not in head
    assert 'role="tablist"' in head and 'data-t="board"' in head
    # puestos: mascota + nombre + rol; quien habló último (la presidencia) está "hablando"
    for s in ('aria-label="Analista"', 'aria-label="Cadena"', 'aria-label="Radar"', 'aria-label="Técnico"', 'aria-label="Comité"'):
        assert s in body, s
    for s in ('Fundamental', 'Suministro', 'Presidencia', 'Mesa de mercado', 'Oficial de riesgo', 'Cuantitativo'):
        assert s in body, s
    assert 'cm-seat absent' in body and 'ausente' in body
    assert 'km-talk' in body and 'cm-badge' in body
    # burbujas: "<b>Analista</b> · Fundamental", postura teñida con tokens, titular de la IA
    assert '<b>Analista</b><span class="cm-role">· Fundamental</span>' in body
    assert '<b>Cadena</b><span class="cm-role">· Suministro</span>' in body
    assert 'class="cm-hl"' in body and '🧠 IA' in body
    # texto en el token LEGIBLE (--cm-good/--cm-bad), píldora teñida con el color vivo (--os-good/--os-bad)
    assert 'color-mix(in srgb,var(--os-good)' in body and 'color-mix(in srgb,var(--os-bad)' in body
    assert 'color:var(--cm-good)' in body and 'color:var(--cm-bad)' in body
    # decisión y avisos con tokens
    assert 'class="cm-dec" style="color:var(--cm-good)' in body
    assert 'var(--cm-warn)' in body
    for n in PERSONAS:
        assert not re.search(r'\b' + n + r'\b', head + body), n
    assert '#0B1222' not in body and '#E8EDFB' not in body


@needs_node
def test_sala_con_mascotas_en():
    o = _run('const MEMO = ' + json.dumps(MEMO) + ';' + ROOM_JS, lang='en')
    body = o['body']
    assert 'aria-label="Chain"' in body and 'aria-label="Analyst"' in body and 'aria-label="Committee"' in body
    assert '<b>Chain</b><span class="cm-role">· Supply</span>' in body
    assert 'Risk officer' in body and 'Market desk' in body and 'absent' in body
    assert '🧠 AI' in body and '🧠 IA' not in body                     # la etiqueta de IA también se traduce


def test_api_publica_intacta():
    for k in ('avatar: function (seat, emoji, mini)', 'open: open, close: close', 'openTab: function (tab)'):
        assert k in SRC, k
    # ids y cableado que otras pantallas/tests usan
    for k in ('id="cm-run"', 'id="cm-approve"', 'id="cm-reject"', 'id="cm-refresh"', 'id="cm-replay"', 'id="cm-feed"', 'id="cm-ent"',
              'id="cm-cli"', 'id="cm-eval"', 'id="cm-agsel"', 'data-go=', 'data-rs=', 'data-f=', 'data-t=', 'data-ref='):
        assert k in SRC, k


# ── revisión 2026-10-09: legibilidad del tema claro, foco, móvil y gráfico ──
def _lum(h):
    h = h.lstrip('#')
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(int(h[i:i + 2], 16)) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _mix(fill, base, p):
    f, b = fill.lstrip('#'), base.lstrip('#')
    return '#' + ''.join('%02x' % round(int(f[i:i + 2], 16) * p + int(b[i:i + 2], 16) * (1 - p)) for i in (0, 2, 4))


def _ratio(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


@needs_node
def test_texto_semantico_pasa_wcag_aa_en_ambos_temas():
    """Verde/rojo/ámbar/violeta usados como TEXTO (decisión, posturas, píldoras, aviso legal) llegan a 4.5:1
    sobre su píldora teñida (10–14 %) en cualquier superficie del comité; los vivos #0ca30c/#B7791F daban
    2.6–3.3:1 en claro."""
    o = _run("KC.open(); out.css = css(); console.log(JSON.stringify(out));")
    cssx = o['css']
    for theme, rx in (('claro', r'body:not\(\.dark\) #cm-ov\{(.*?)\}'), ('oscuro', r'body\.dark #cm-ov\{(.*?)\}')):
        t = _decls(re.search(rx, cssx).group(1))
        pairs = [('--cm-good', '--os-good'), ('--cm-bad', '--os-bad'), ('--cm-warn', '--cm-warn-fill'), ('--cm-ai', '--cm-ai')]
        for txt, fil in pairs:
            for base in ('--os-surface', '--os-surface-2', '--os-bg'):
                for p in (0.10, 0.12, 0.14):
                    r = _ratio(t[txt], _mix(t[fil], t[base], p))
                    assert r >= 4.5, (theme, txt, base, p, round(r, 2))
        # rol / historial de cada puesto (lo único que distingue a puestos con la misma mascota)
        assert _ratio(t['--os-ink-2'], t['--os-surface-2']) >= 4.5, theme
        # botón Aprobar: texto sobre el verde de texto
        assert _ratio(t['--cm-on-sem'], t['--cm-good']) >= 4.5, theme
    # el aviso legal y los avisos usan el ámbar de TEXTO; el fondo, el vivo
    assert re.search(r'#cm \.cm-disc\{[^}]*color:var\(--cm-warn\)[^}]*color-mix\(in srgb,var\(--cm-warn-fill\)', cssx)
    assert '#cm .cm-btn.ok{background:var(--cm-good);color:var(--cm-on-sem)}' in cssx


@needs_node
def test_puestos_legibles_y_foco_visible_y_pestanas_moviles():
    o = _run("KC.open(); out.css = css(); console.log(JSON.stringify(out));")
    cssx = o['css']
    # el texto del puesto nunca se apaga con opacity: lo que se atenúa es la mascota
    seat = re.search(r'#cm \.cm-seat\{([^}]*)\}', cssx).group(1)
    assert 'opacity' not in seat
    assert not re.search(r'#cm \.cm-seat\.(spoke|talk|absent)\{[^}]*opacity', cssx)
    assert re.search(r'#cm \.cm-seat:not\(\.spoke\):not\(\.talk\) \.cm-av\{[^}]*opacity', cssx)
    for cls in ('cm-sr', 'cm-rec', 'cm-ss'):
        rule = re.search(r'#cm \.cm-seat \.' + cls + r'\{([^}]*)\}', cssx).group(1)
        assert 'color:var(--os-ink-2)' in rule, cls
    assert re.search(r'#cm \.cm-seat \.cm-sr\{font-size:11px', cssx)
    # foco de teclado visible (no el anillo de 12 %)
    assert 'outline:none;box-shadow:0 0 0 3px var(--kos-accent-soft)' not in cssx
    assert re.search(r'#cm \.cm-tab:focus-visible[^{]*\{outline:2px solid var\(--os-accent\);outline-offset:2px\}', cssx)
    assert re.search(r'#cm input:focus-visible,#cm select:focus-visible\{outline:2px solid var\(--os-accent\)', cssx)
    # móvil: las pestañas se acomodan en varias filas (nada escondido a la derecha sin barra)
    mob = cssx[cssx.index('@media(max-width:760px)'):]
    mob = mob[:mob.index('}}') + 2]
    assert 'nowrap' not in mob and 'scrollbar-width:none' not in mob


def test_grafico_de_calibracion_usa_la_letra_de_khipus_os():
    i = SRC.index('function drawCal(')
    body = SRC[i:SRC.index('function evaluateNow(', i)]
    assert body.count('family: font') >= 5                  # 2 títulos de eje + 2 ejes de ticks + leyenda
    assert "ticks: { color: ink2, font: { family: font, size: 11 } }" in body
