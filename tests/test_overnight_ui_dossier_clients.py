"""tests/test_overnight_ui_dossier_clients.py — el Dossier (engine/fincard.js) y Clientes (engine/clients.js)
entran a Khipus OS (2026-10-10).

Antes eran "isla oscura": fondos #0B1222/#06090F, tinta #E8EDFB, neón #00E0FF, letra Inter/JetBrains Mono y
bordes por todos lados — ilegibles en el tema claro de Khipus OS. Ahora:
  · solo tokens --os-* / --kos-* de engine/cockpit.js, siempre con respaldo oscuro dentro de var()
  · los dos overlays viven FUERA de #bcp-ov (#fc-ov, #kc-ov) y llevan .kos-themed (tokens claro/oscuro)
  · colores semánticos de TEXTO = *-ink (AA); los vivos (--os-good/--os-bad) solo para rellenos y barras
  · los gráficos del Dossier (canvas) leen los tokens con getComputedStyle y se re-pintan al cambiar el tema
  · el COMITÉ (agente de Khipus) se dibuja con su mascota en Clientes; las IAs externas (MCP) siguen con 🤖
  · se conservan TODAS las APIs públicas, ids, clases y data-* que usan otros módulos
  · el flujo de dinero de Clientes (PIN vía _tradeFetch, preview → confirmo → confirm, cola de aprobación)
    queda IGUAL — este cambio es solo de presentación
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
FC = open(os.path.join(ROOT, 'engine', 'fincard.js'), encoding='utf-8').read()
KC = open(os.path.join(ROOT, 'engine', 'clients.js'), encoding='utf-8').read()
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


# piel vieja (NEXUS oscura): fondos, tintas, neón, bordes azulados, ámbar/rosa de los avisos y letras
LEGACY = ['#0B1222', '#06090F', '#0a1120', '#E8EDFB', '#00E0FF', '#9BA6C4', '#7C87A3', '#5b6580', '#8FA0C0', '#C9D4EC',
          '#5FC6E8', '#FF4D6A', '#2BE38B', '#FFB300', '#FF9DAE', '#7CF0B8', '#FFD27A', '#FF6B84', '#fbbf24', '#fcd34d',
          '#f59e0b', 'rgba(21,28,45', 'rgba(11,18,34', 'rgba(6,9,15', 'rgba(3,6,12', 'rgba(122,158,255', 'rgba(0,224,255',
          'rgba(255,77,106', 'rgba(43,227,139', 'rgba(255,179,0', 'rgba(245,158,11']
FONTS = ["'Inter'", 'Inter,', 'JetBrains', 'Fraunces', 'Cascadia', 'monospace']


@pytest.mark.parametrize('name,src', [('fincard', FC), ('clients', KC)])
def test_no_legacy_dark_colors_or_fonts(name, src):
    bare = _strip_var_fallbacks(src).lower()
    left = [c for c in LEGACY if c.lower() in bare]
    assert not left, f'{name}: quedan colores de la piel oscura vieja fuera de var(): {left}'
    fonts = [f for f in FONTS if f.lower() in src.lower()]
    assert not fonts, f'{name}: quedan letras viejas: {fonts}'
    # ningún style="" con un color hex fijo en el HTML que se pinta
    assert not re.search(r'style="[^"]*color:\s*#', src), f'{name}: style="" con color fijo'
    assert not re.search(r"style=\"[^\"]*'\s*\+\s*col\s*\+", src), f'{name}: color calculado en style=""'


@pytest.mark.parametrize('name,src', [('fincard', FC), ('clients', KC)])
def test_tokens_always_have_dark_fallback(name, src):
    # todo var(--os-*/--kos-*) usado como VALOR de CSS lleva respaldo oscuro (por si cockpit.js no inyectó sus tokens)
    naked = re.findall(r'var\(--(?:os|kos)-[a-z0-9-]+\)', src)
    assert not naked, f'{name}: var() sin respaldo: {sorted(set(naked))[:8]}'


def test_overlays_are_kos_themed_and_tokens_exist():
    assert "ov.className = 'kos-themed'" in FC
    assert "ov.className = 'kos-themed'" in KC
    # la clase que usamos de verdad define los tokens en claro y en oscuro
    assert 'body:not(.dark) .kos-themed' in COCKPIT and 'body.dark .kos-themed' in COCKPIT
    for tok in ('--os-good-ink', '--os-bad-ink', '--os-warn-ink', '--os-btn-ink', '--kos-scrim'):
        assert tok in COCKPIT


def test_semantic_text_uses_ink_tokens():
    # texto verde/rojo/ámbar = *-ink (AA); los vivos solo en rellenos (barras, puntos, tintes)
    for src in (FC, KC):
        for m in re.finditer(r'(?<![-\w])color:var\(--os-(good|bad|warn)[,)]', src):
            raise AssertionError('texto con color vivo (no -ink): ' + src[m.start():m.start() + 60])
    assert '.fc-up{color:var(--os-good-ink' in FC and '.fc-dn{color:var(--os-bad-ink' in FC
    assert "'#kc .up{color:var(--os-good-ink" in KC and '#kc .dn{color:var(--os-bad-ink' in KC


def test_mobile_and_reduced_motion():
    for src, sel in ((FC, '#fc'), (KC, '#kc')):
        assert '@media (max-width:760px)' in src or '@media(max-width:760px)' in src
        assert 'prefers-reduced-motion' in src
        assert 'focus-visible{outline:2px solid var(--os-accent' in src
    # Dossier: los gráficos sin animación si el sistema lo pide
    assert "prefers-reduced-motion: reduce" in FC and 'animation: reducedMotion() ? false' in FC
    # Clientes: anula las .tabs/.tab globales de app.html (mayúsculas, letra mono, raya ::after)
    assert "#kc .tab{font-family:inherit;letter-spacing:normal;text-transform:none" in KC
    assert "#kc .tab::after{content:none" in KC


def test_public_api_and_ids_kept():
    for s in ('window.openFinCard = function (idOrTicker, labelHint)', 'window._finCardCompare', 'window._finCardOpenParent',
              'window._finCardClose = close', "id = 'fc-ov'", 'id="fc"', 'id="fc-live"', 'fc-tile-px', 'id="fc-lv-x"',
              "'#fc .fc-name'", 'id="fc-src"', 'id="fc-body"', 'id="fc-foot-src"', 'id="fc-news"', 'id="fc-news-st"',
              'id="fc-news-list"', 'id="fc-hist"', 'id="fc-hist-list"', 'id="fc-valnews"', "'fincard-styles'",
              'class="fc-tile" data-x="', "classList.add('show')"):
        assert s in FC, s
    for s in ('window.KhipuClients = { open: open, close: close, pendingCount: pendingCount }', "ov.id = 'kc-ov'", 'id="kc"',
              "'kc-css'", 'id="kc-sel"', 'id="kc-o-sym"', 'id="kc-o-amt"', 'id="kc-confirm-ck"', 'id="kc-live-ck"', 'id="kc-exp"',
              'id="kc-c-key"', 'id="kc-c-sec"', 'id="kc-o-cli"', 'class="badge live"', 'class="badge paper"', 'data-tab="'):
        assert s in KC, s
    for act in ('close', 'reload', 'legal', 'toggle-new', 'open-client', 'goto-new', 'goto-orders', 'snap', 'create', 'pause',
                'reset-hwm', 'save-limits', 'live-on', 'live-off', 'creds', 'oauth', 'preview', 'confirm', 'approve', 'reject',
                'cancel', 'sync'):
        assert ("data-act=\"" + act + "\"") in KC or ("act === '" + act + "'") in KC, act


def test_money_flow_untouched():
    # PIN: SIEMPRE por window._tradeFetch (core/pin.py del lado del server); nunca un camino propio
    assert 'if (window._tradeFetch) return window._tradeFetch(url, opts || {}, interactive !== false);' in KC
    assert "o.headers = Object.assign({}, o.headers, { 'X-Trade-Pin': pin });" in KC
    raw = re.findall(r'(?<![\w.])fetch\(', KC)
    assert len(raw) == 2, 'solo /status (público) y el respaldo de tfetch usan fetch() directo'
    # badges sin prompt de PIN
    assert "if (!pin) return Promise.resolve(null);" in KC and "call('GET', '/approvals', null, false)" in KC
    # preview → «confirmo» → confirm; dinero real = además el pop-up con resumen
    assert "if (!checked('kc-confirm-ck')) { flash('err'" in KC
    assert "'/orders/' + encodeURIComponent(p.preview_id) + '/confirm', { confirm: true, actor: actor() }" in KC
    assert "(p.mode === 'live'\n        ? askOrder(p," in KC
    # aprobar/rechazar propuestas de IA/comité: pop-up + humano; habilitar dinero real: casilla + confirm
    assert "'/approvals/' + encodeURIComponent(id) + '/approve', { actor: actor() }" in KC
    assert "if (!checked('kc-live-ck')) { flash('err'" in KC
    assert "patchClient({ live_enabled: true, confirm_live: true }" in KC
    # el envío con DINERO REAL sigue siendo el botón rojo (ahora sólido)
    assert "(p.mode === 'live' ? 'bad solid' : 'ok')" in KC


def test_bilingual_new_strings():
    assert "L('Cerrar', 'Close')" in FC and "L('Cerrar', 'Close')" in KC
    # la marca del rango 52 sem. ya no es "blanca" (en claro es oscura): texto neutro en los dos idiomas
    assert 'La marca blanca' not in FC and 'The white marker' not in FC
    assert 'La marca sobre la barra muestra' in FC and 'The marker on the bar shows' in FC


# ── JS real en node con un DOM falso ─────────────────────────────────────────────────────────────────
HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const ROOT = process.argv[1], WHICH = process.argv[2], LANG = process.argv[3] || 'es', WITH_MASCOT = process.argv[4] !== 'no-mascot';
const byId = {}, all = [];
function ClassList(el) { this.el = el; }
ClassList.prototype._get = function () { return (this.el._cls || '').split(/\s+/).filter(Boolean); };
ClassList.prototype.add = function (c) { const a = this._get(); if (a.indexOf(c) < 0) a.push(c); this.el._cls = a.join(' '); };
ClassList.prototype.remove = function (c) { this.el._cls = this._get().filter(x => x !== c).join(' '); };
ClassList.prototype.contains = function (c) { return this._get().indexOf(c) >= 0; };
ClassList.prototype.toggle = function (c, on) { if (on === undefined) on = !this.contains(c); if (on) this.add(c); else this.remove(c); };
class El {
  constructor(tag) { this.tagName = String(tag || 'div').toUpperCase(); this.children = []; this._cls = ''; this._html = ''; this._text = '';
    this._id = ''; this.style = {}; this.attrs = {}; this.listeners = {}; this.classList = new ClassList(this); all.push(this); }
  get id() { return this._id; } set id(v) { this._id = String(v); byId[this._id] = this; }
  get className() { return this._cls; } set className(v) { this._cls = String(v); }
  get innerHTML() { return this._html; } set innerHTML(v) { this._html = String(v); }
  get textContent() { return this._text || this._html; } set textContent(v) { this._text = String(v); }
  get parentNode() { return this._parent || (this._parent = new El('div')); }
  appendChild(c) { this.children.push(c); c._parent = this; return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); } getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
  querySelectorAll() { return []; } querySelector() { return null; }
  contains() { return true; }
}
const store = { eco_lang: LANG, khipu_trade_pin: '1234', khipu_trade_pin_exp: String(Date.now() + 3600e3) };
const ctx = { console, Date, Math, JSON, Promise, encodeURIComponent, isNaN, isFinite, Number, String, Object, Array,
  setTimeout: (fn, ms) => setTimeout(fn, Math.min(ms || 0, 5)), clearTimeout, setInterval: () => 0, clearInterval: () => {},
  localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } },
  getComputedStyle: () => ({ getPropertyValue: () => '' }), matchMedia: () => ({ matches: false }),
};
ctx.window = ctx; ctx.globalThis = ctx; ctx.LANG = LANG;
// el PIN vigente lo lee app.html (_tradePinStored); aquí, el mismo contrato mínimo
ctx._tradePinStored = () => store.khipu_trade_pin || '';
const body = new El('body'); body._cls = 'dark';
ctx.document = { readyState: 'complete', body, head: new El('head'), documentElement: new El('html'), hidden: false,
  createElement: t => new El(t), addEventListener: () => {}, querySelector: () => null, querySelectorAll: () => [],
  getElementById: id => {
    if (byId[id]) return byId[id];
    if (all.some(e => e._html.indexOf('id="' + id + '"') >= 0)) { const s = new El('div'); s.id = id; return s; }
    return null;
  } };
const NOW = new Date().toISOString();
const R = {
  '/api/company/live/NVDA': { available: true, name: 'NVIDIA', symbol: 'NVDA', currency: 'USD', price: 182.4, change_pct: 1.8, market_cap_usd_b: 4441,
    week52_low: 86, week52_high: 195, sources: ['yahoo'], as_of: NOW, market_time: NOW, market_state: 'REGULAR' },
  '/api/findossier/NVDA': { available: false, reason: 'sin estados', tried: ['fmp'] },
  '/api/candles/NVDA': { s: 'no_data' },
  '/api/brokerage/status': { available: true, trading_enabled: true },
  '/api/brokerage/status/detail': { live_enabled_env: false, oauth_configured: false, encryption: { key_source: 'env' } },
  '/api/brokerage/clients': { clients: [{ id: 'c1', name: 'Ana', mode: 'paper', status: 'active', connected: true, auth_type: 'api_keys', limits: {}, mandate: {} }] },
  '/api/brokerage/approvals': { approvals: [
    { preview_id: 'p1', client_id: 'c1', client_name: 'Ana', mode: 'paper', source: 'committee', summary_es: 'COMPRAR', summary_en: 'BUY',
      checks: [{ name: 'order_size', ok: false, detail: 'x' }, { name: 'mode', ok: true, warn: true, detail: 'y' }, { name: 'kill_switch', ok: true, detail: 'z' }] },
    { preview_id: 'p2', client_id: 'c1', client_name: 'Ana', mode: 'live', source: 'mcp', summary_es: 'VENDER', summary_en: 'SELL', checks: [] }] },
  '/api/brokerage/orders': { orders: [{ id: 'o1', client_id: 'c1', client_name: 'Ana', mode: 'paper', side: 'sell', symbol: 'AMD', qty: 2, status: 'rejected',
    source: 'committee', created_at: NOW, error: 'bloqueada', error_en: 'blocked' }] },
};
const calls = [];
ctx.fetch = (url, opts) => { calls.push({ url, pin: opts && opts.headers && opts.headers['X-Trade-Pin'] });
  const body = R[String(url).replace(/\?.*$/, '')] || {};
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(JSON.stringify(body))) }); };
vm.createContext(ctx);
if (WITH_MASCOT) vm.runInContext(fs.readFileSync(ROOT + '/engine/mascot.js', 'utf8'), ctx);
const out = {};
function css(id) { const s = ctx.document.head.children.find(c => c.id === id); return s ? s.textContent : ''; }
(async () => {
  if (WHICH === 'fincard') {
    vm.runInContext(fs.readFileSync(ROOT + '/engine/fincard.js', 'utf8'), ctx);
    out.api = ['openFinCard', '_finCardCompare', '_finCardOpenParent', '_finCardClose'].map(k => typeof ctx[k]);
    ctx.openFinCard('NVDA');
    await new Promise(r => setTimeout(r, 60));
    const ov = byId['fc-ov'];
    out.ovClass = ov && ov.className;
    out.ovHtml = ov && ov.innerHTML;
    out.fc = byId['fc'] ? byId['fc'].innerHTML : '';
    out.live = byId['fc-live'] ? byId['fc-live'].innerHTML : '';
    out.body = byId['fc-body'] ? byId['fc-body'].innerHTML : '';
    out.css = css('fincard-styles');
    ctx._finCardClose();
    out.closed = !ov.classList.contains('show');
  } else {
    vm.runInContext(fs.readFileSync(ROOT + '/engine/clients.js', 'utf8'), ctx);
    out.api = ['open', 'close', 'pendingCount'].map(k => typeof ctx.KhipuClients[k]);
    ctx.KhipuClients.open('approvals');
    await new Promise(r => setTimeout(r, 60));
    out.ovClass = byId['kc-ov'].className;
    out.ovHtml = byId['kc-ov'].innerHTML;
    out.approvals = byId['kc'].innerHTML;
    ctx.KhipuClients.open('orders');
    await new Promise(r => setTimeout(r, 60));
    out.orders = byId['kc'].innerHTML;
    out.pending = await ctx.KhipuClients.pendingCount();
    out.css = css('kc-css');
    out.pins = calls.filter(c => c.url.indexOf('/api/brokerage/') === 0 && c.url !== '/api/brokerage/status').map(c => c.pin);
  }
  process.stdout.write(JSON.stringify(out));
})().catch(e => { process.stdout.write(JSON.stringify({ error: String(e && e.stack || e) })); });
"""


def _run(which, lang='es', mascot=True):
    r = subprocess.run([NODE, '-e', HARNESS, ROOT, which, lang, 'mascot' if mascot else 'no-mascot'],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert 'error' not in d, d.get('error')
    return d


@needs_node
def test_fincard_runs_themed_in_node():
    d = _run('fincard')
    assert d['api'] == ['function'] * 4
    assert 'kos-themed' in d['ovClass'].split() and d['closed']
    assert 'role="dialog"' in d['ovHtml'] and 'aria-modal="true"' in d['ovHtml']
    assert 'class="fc-name"' in d['fc'] and 'aria-label="Cerrar"' in d['fc']
    # franja en vivo: datos tocables y accesibles con teclado
    assert 'class="fc-tile" data-x="price" role="button" tabindex="0" id="fc-tile-px"' in d['live']
    assert 'EN VIVO' in d['live']
    # sin estados → la nota honesta (nunca un overlay vacío)
    assert 'No rellenamos los huecos con cifras inventadas' in d['body']
    css = d['css']
    assert '#fc-ov{' in css and 'background:var(--os-bg,#0E0F14)' in css and 'var(--kos-scrim' in css
    bare = _strip_var_fallbacks(css).lower()
    assert not [c for c in LEGACY if c.lower() in bare]


@needs_node
def test_fincard_english():
    d = _run('fincard', 'en')
    assert 'LIVE' in d['live'] and 'Price' in d['live'] and 'aria-label="Close"' in d['fc']
    assert 'We do not fill the gaps with made-up figures' in d['body']


@needs_node
def test_clients_runs_themed_with_mascot_and_pin():
    d = _run('clients')
    assert d['api'] == ['function'] * 3
    assert 'kos-themed' in d['ovClass'].split() and 'role="dialog"' in d['ovHtml']
    a = d['approvals']
    # el comité es un agente de Khipus → su mascota; la IA externa por MCP sigue con 🤖
    assert '<span class="src"><span class="km"' in a and 'comité' in a
    assert '<span class="src">🤖 agente (MCP)</span>' in a
    # controles con clases semánticas (sin colores fijos), insignias obligatorias 🧪 / 🔴
    assert '<i class="dn">✗</i>' in a and '<i class="wn">⚠</i>' in a and '<i class="up">✓</i>' in a
    assert 'class="badge paper">🧪 PAPEL' in a and 'class="badge live">🔴 DINERO REAL' in a
    assert 'data-act="approve" data-id="p1"' in a and 'data-act="reject" data-id="p1"' in a
    o = d['orders']
    assert '<b class="dn">VENTA</b>' in o and '<div class="s err">bloqueada</div>' in o
    assert d['pending'] == 2
    # TODA llamada de corretaje (salvo /status público) lleva el PIN guardado
    assert d['pins'] and all(p == '1234' for p in d['pins'])
    bare = _strip_var_fallbacks(d['css']).lower()
    assert not [c for c in LEGACY if c.lower() in bare]


@needs_node
def test_clients_without_mascot_module_falls_back_to_emoji():
    d = _run('clients', 'en', mascot=False)
    a = d['approvals']
    assert '<span class="src">🏛 committee</span>' in a and '<span class="src">🤖 agent (MCP)</span>' in a
    assert 'aria-label="Close"' in a and 'class="badge live">🔴 REAL MONEY' in a
