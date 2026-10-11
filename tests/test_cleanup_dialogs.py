"""tests/test_cleanup_dialogs.py — limpieza de cabos sueltos (2026-10-11): diálogos nativos y el "actor".

Antes:
  · Flujos de dinero (Clientes: reiniciar máximo, margen, DINERO REAL, claves reales, aprobar/rechazar) y otros
    (investigación profunda, revocar conexión MCP, renombrar/borrar cartera, comité) usaban window.confirm /
    window.prompt — contra la regla "toda compra/venta confirma y notifica por KhipuToast".
  · engine/clients.js reimplementaba el header X-Trade-Pin como respaldo de tfetch.
  · 5 sitios pedían el nombre con window.prompt (dos solo en español) y ~14 actor() locales tenían OTRO valor
    por defecto ('ui', 'operador', 'anónimo', 'ui (PIN)'…) → el registro de auditoría quedaba inconsistente.
Ahora:
  · KhipuToast.prompt(opts) → Promise<string|null> (password:true → type=password + autocomplete=off).
  · window.khipuActor(): UN ayudante, UN valor por defecto ('usuario'); {ask:true} pregunta una vez.
  · Ningún engine/*.js (salvo livesim.js/cockpit.js, de otro dueño) llama a confirm/prompt/alert nativos.
  · clients.js va SIEMPRE por window._tradeFetch (sin él: error claro, nada se envía).
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, 'engine')
NODE = shutil.which('node')
needs_node = pytest.mark.skipif(not NODE, reason='node no disponible')

# livesim.js y cockpit.js tienen otro dueño (se reportan aparte); no hay archivos de terceros en engine/
EXCLUDED = {'livesim.js', 'cockpit.js'}


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


TOAST = _r('engine', 'toast.js')
CLIENTS = _r('engine', 'clients.js')
ENGINE_FILES = sorted(f for f in os.listdir(ENGINE) if f.endswith('.js') and f not in EXCLUDED)

# llamada NATIVA: confirm( / prompt( / alert( sueltos o con window./self./globalThis.; NO cuenta un método de otro
# objeto (KhipuToast.confirm(, K.prompt(, T.confirmOrder…) ni una definición «function confirm(».
NATIVE_RE = re.compile(r'(?<![\w.$])(?<!function )(?:window\.|self\.|globalThis\.)?(?:confirm|prompt|alert)\s*\(')


def test_regex_distingue_nativo_de_metodos():
    for s in ('window.confirm("x")', 'if (!confirm(a))', 'x = prompt("n")', ' alert(1)', 'self.alert(1)', '(globalThis.prompt(1))'):
        assert NATIVE_RE.search(s), s
    for s in ('KhipuToast.confirm({})', 'K.prompt({})', 'T.confirmOrder(o)', 'window.KhipuToast.prompt(o)', 'askConfirm(x)',
              'function confirm(o) {', 'x.alert(1)', 'confirmDlg(opts)', 'promptDlg(opts)', "'reemplaza window.prompt'"):
        assert not NATIVE_RE.search(s), s


@pytest.mark.parametrize('name', ENGINE_FILES)
def test_sin_dialogos_nativos_en_engine(name):
    src = _r('engine', name)
    hits = [(i + 1, ln.strip()[:120]) for i, ln in enumerate(src.split('\n')) if NATIVE_RE.search(ln)]
    assert not hits, '%s usa diálogos nativos: %r' % (name, hits)


# ── toast.js: la API nueva ────────────────────────────────────────────────────────────────────────────────
def test_toast_expone_prompt_con_password():
    m = re.search(r'window\.KhipuToast = \{(.*?)\n  \};', TOAST, re.S)
    assert m and 'prompt: promptDlg' in m.group(1)
    a = TOAST.index('function promptDlg(opts)')
    body = TOAST[a:TOAST.index('function khipuActor(opts)')]
    # PIN: campo de contraseña sin autocompletar
    assert "var pw = opts.password === true;" in body
    assert "'<input class=\"khm-in\" id=\"khm-in\" type=\"' + (pw ? 'password' : 'text') + '\" autocomplete=\"off\"'" in body
    # accesible: diálogo modal con título, etiqueta unida al campo (o el título como etiqueta)
    assert 'role="dialog" aria-modal="true" aria-labelledby="khm-t"' in body
    assert '<label class="khm-lbl" id="khm-lbl" for="khm-in">' in body and "' aria-labelledby=\"khm-t\"'" in body
    # todo texto interpolado se escapa
    for k in ('opts.title', 'opts.body', 'opts.label', 'opts.placeholder', 'opts.okText', 'opts.cancelText'):
        assert ('esc(' + k) in body, k
    assert "esc(opts.value == null ? '' : opts.value)" in body
    # Enter = Aceptar · Esc = null · foco en el campo · un solo diálogo a la vez · mismo tema que confirm
    assert "if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(null); return; }" in body
    assert "e.key === 'Enter' && e.target === inp && !e.isComposing" in body
    assert 'try { inp.focus(); if (inp.value) inp.select(); } catch (e) {}' in body
    assert "if (_dlg) _dlg.close(false, 'dismissed');" in body
    assert "ov.id = 'khm-ov';\n    ov.className = 'kos-themed';" in body
    # botones bilingües por defecto
    assert "L('Aceptar', 'OK')" in body and "L('Cancelar', 'Cancel')" in body


def test_toast_confirm_sin_body_nunca_confirma():
    a = TOAST.index('function confirmDlg(opts)')
    assert 'if (!document.body) return Promise.resolve(false);' in TOAST[a:a + 600]
    # botón rojo sólido para acciones de dinero/irreversibles (mismo rojo que DINERO REAL)
    assert "'.khm-ok.danger{color:#fff;background:#c42b2b}'" in TOAST
    assert "(opts.danger ? 'danger' : tone === 'info' ? '' : tone)" in TOAST


def test_khipu_actor_unico():
    assert 'window.khipuActor = khipuActor;' in TOAST
    assert "var ACTOR_DEFAULT = 'usuario';" in TOAST
    a = TOAST.index('function khipuActor(opts)')
    body = TOAST[a:a + 1600]
    assert 'if (!(opts && opts.ask)) return a || ACTOR_DEFAULT;' in body
    assert "try { localStorage.setItem('khipu_actor', n); } catch (e) {}" in body
    assert "L('¿Tu nombre?', 'Your name?')" in body and 'Queda en el registro de auditoría' in body and 'It goes into the audit log' in body
    assert 'khipuActor.stored = storedActor;' in TOAST
    s = TOAST.index('function storedActor()')
    assert "try { return String(localStorage.getItem('khipu_actor') || '').trim(); } catch (e) { return ''; }" in TOAST[s:s + 200]


def test_toast_carga_antes_que_sus_usuarios():
    html = _r('app.html')
    pos = {m.group(1): m.start() for m in re.finditer(r'<script src="engine/([\w-]+\.js)"', html)}
    for f in ('research.js', 'mcpconnect.js', 'portfolios.js', 'clients.js', 'khipu_lang.js', 'temporal-graph.js',
              'reconcile.js', 'aispend.js', 'committee.js', 'pfcommittee.js', 'pfreports.js', 'khipu_chat.js'):
        assert pos['toast.js'] < pos[f], f


# ── actor(): un solo ayudante, un solo valor por defecto ──────────────────────────────────────────────────
ACTOR_DEF = re.compile(r'function (actor|_getActor|_getActorKhipu)\s*\(\s*\)\s*\{')


@pytest.mark.parametrize('name', ENGINE_FILES)
def test_actor_local_delega_en_khipu_actor(name):
    src = _r('engine', name)
    for m in ACTOR_DEF.finditer(src):
        assert 'khipuActor' in src[m.end():m.end() + 300], '%s: %s() no usa window.khipuActor' % (name, m.group(1))
    # ningún valor por defecto distinto para el actor
    for bad in ("|| 'operador'", "|| 'anónimo'", "'ui (PIN)'", "return a || 'ui';"):
        assert bad not in src, (name, bad)


def test_clientes_pin_solo_por_trade_fetch_y_confirmaciones_de_dinero():
    assert "'X-Trade-Pin'" not in CLIENTS   # el header lo pone SOLO window._tradeFetch (app.html)
    assert 'if (window._tradeFetch) return window._tradeFetch(url, opts || {}, interactive !== false);' in CLIENTS
    assert "if (!window._tradeFetch) return Promise.resolve({ ok: false, error: NO_TF.es, error_en: NO_TF.en, code: 'no_trade_fetch' });" in CLIENTS
    # reiniciar máximo / margen / DINERO REAL / claves reales: KhipuToast.confirm con botón rojo
    for t in ("L('¿Reiniciar el máximo histórico?', 'Reset the high-water mark?')",
              "L('¿Permitir MARGEN (dinero prestado)?', 'Allow MARGIN (borrowed money)?')",
              "L('🔴 ¿Habilitar DINERO REAL para este cliente?', '🔴 Enable REAL MONEY for this client?')",
              "L('🔴 ¿Conectar claves de DINERO REAL?', '🔴 Connect REAL-MONEY keys?')"):
        a = CLIENTS.index(t)
        assert 'ask({' in CLIENTS[a - 120:a] and 'danger: true' in CLIENTS[a:a + 1200], t
    # habilitar dinero real: casilla obligatoria dentro del diálogo + insignia 🔴
    a = CLIENTS.index("L('🔴 ¿Habilitar DINERO REAL para este cliente?'")
    blk = CLIENTS[a:a + 1400]
    assert "mode: 'live'" in blk and "requireCheck: L('Entiendo que esto habilita operaciones con DINERO REAL.', 'I understand this enables REAL-MONEY trading.')" in blk
    # sin engine/toast.js: nada se da por confirmado
    assert "function askOrder(x, opts) {" in CLIENTS and 'return noDialog();' in CLIENTS
    # el nombre se pide UNA vez antes de las acciones que escriben (no a mitad del flujo)
    assert 'var need = WRITE_ACTS[act] ? ensureActor() : null;' in CLIENTS


# ── comportamiento: node (sin DOM) y navegador real ──────────────────────────────────────────────────────
NODE_JS = r"""
const fs = require('fs'), vm = require('vm');
const ROOT = process.argv[1];
const store = {};
const native = [];
const ctx = { console, Promise, String, Object, Array, Math, JSON, Date, isFinite, setTimeout, clearTimeout,
  localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } },
  confirm: () => { native.push('confirm'); return true; }, prompt: () => { native.push('prompt'); return 'x'; } };
ctx.window = ctx;
ctx.document = { body: null, getElementById: () => null, createElement: () => ({}), addEventListener: () => {} };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(ROOT + '/engine/toast.js', 'utf8'), ctx);
(async () => {
  const out = {};
  out.def = ctx.khipuActor();
  out.storedEmpty = ctx.khipuActor.stored();
  out.askNoBody = await ctx.khipuActor({ ask: true });          // sin <body>: no hay a quién preguntar → 'usuario'
  out.savedAfter = store.khipu_actor === undefined;
  store.khipu_actor = '  Ana  ';
  out.sync = ctx.khipuActor();
  const p = ctx.khipuActor({ ask: true });
  out.askIsPromise = typeof p.then === 'function';
  out.ask = await p;
  out.confirmNoBody = await ctx.KhipuToast.confirm({ title: 'x' });
  out.promptNoBody = await ctx.KhipuToast.prompt({ title: 'x' });
  out.native = native;
  process.stdout.write(JSON.stringify(out));
})().catch(e => process.stdout.write(JSON.stringify({ error: String(e && e.stack || e) })));
"""


@needs_node
def test_khipu_actor_y_dialogos_sin_body_en_node():
    r = subprocess.run([NODE, '-e', NODE_JS, ROOT], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    assert 'error' not in o, o.get('error')
    assert o['def'] == 'usuario' and o['storedEmpty'] == '' and o['askNoBody'] == 'usuario' and o['savedAfter']
    assert o['sync'] == 'Ana' and o['askIsPromise'] and o['ask'] == 'Ana'
    assert o['confirmNoBody'] is False and o['promptNoBody'] is None
    assert o['native'] == []   # nunca cae a window.confirm / window.prompt


def _chromium(p):
    for kw in ({}, {'executable_path': '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', 'args': ['--no-sandbox']}):
        try:
            return p.chromium.launch(**kw)
        except Exception:  # noqa: BLE001
            continue
    return None


@pytest.fixture(scope='module')
def browser():
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        b = _chromium(p)
        if not b:
            pytest.skip('Chromium no disponible')
        yield b
        b.close()


PAGE = ('<!doctype html><html lang="es"><head><meta charset="utf-8"></head><body>'
        '<button id="opener">abrir</button></body></html>')

FLOW = r"""async () => {
  const T = window.KhipuToast, opener = document.getElementById('opener');
  const native = []; window.prompt = () => { native.push('prompt'); return 'x'; }; window.confirm = () => { native.push('confirm'); return true; };
  const out = {};
  const key = (k, el) => (el || document.activeElement).dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true }));
  const typeIn = (v) => { const i = document.getElementById('khm-in'); i.value = v; };
  // 1) PIN: campo de contraseña, foco en el campo, Enter = Aceptar, el foco vuelve a quien abrió
  opener.focus();
  let p = T.prompt({ title: 'PIN <b>x</b>', body: 'Se recuerda 12 h', label: 'PIN', password: true });
  await new Promise(r => setTimeout(r, 20));
  const inp = document.getElementById('khm-in'), box = document.querySelector('#khm-ov .khm');
  out.pin = { type: inp.type, ac: inp.getAttribute('autocomplete'), focused: document.activeElement === inp,
    role: box.getAttribute('role'), modal: box.getAttribute('aria-modal'), labelFor: document.querySelector('#khm-ov label').htmlFor,
    titleHtml: document.getElementById('khm-t').innerHTML, themed: document.getElementById('khm-ov').classList.contains('kos-themed'),
    ok: document.querySelector('#khm-ov .khm-ok').textContent, cancel: document.querySelector('#khm-ov .khm-cancel').textContent };
  typeIn('4321'); key('Enter', inp);
  out.pin.value = await p; out.pin.closed = !document.getElementById('khm-ov'); out.pin.focusBack = document.activeElement === opener;
  // 2) Esc / Cancelar / ✕ / fondo → null
  for (const how of ['esc', 'cancel', 'x', 'backdrop']) {
    p = T.prompt({ title: 'Nombre', value: 'Ana' });
    await new Promise(r => setTimeout(r, 10));
    const ov = document.getElementById('khm-ov');
    if (how === 'esc') key('Escape'); else if (how === 'cancel') ov.querySelector('.khm-cancel').click();
    else if (how === 'x') ov.querySelector('.khm-x').click(); else ov.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
    out[how] = await p;
  }
  // 3) valor inicial seleccionado; Aceptar con clic devuelve el texto tal cual; sin label → el título etiqueta el campo
  p = T.prompt({ title: 'Renombrar', value: 'Mi cartera' });
  await new Promise(r => setTimeout(r, 10));
  const i2 = document.getElementById('khm-in');
  out.sel = [i2.selectionStart, i2.selectionEnd, i2.value.length]; out.labelledby = i2.getAttribute('aria-labelledby'); out.type2 = i2.type;
  i2.value = ' Nueva '; document.querySelector('#khm-ov .khm-ok').click();
  out.clicked = await p;
  // 4) khipuActor: pregunta UNA vez, guarda y luego responde sin diálogo
  localStorage.removeItem('khipu_actor');
  out.actorDefault = window.khipuActor();
  const a1 = window.khipuActor({ ask: true }), a2 = window.khipuActor({ ask: true });
  await new Promise(r => setTimeout(r, 10));
  out.sameAsk = a1 === a2; out.askTitle = document.getElementById('khm-t').textContent;
  typeIn('  Fabrizio '); key('Enter', document.getElementById('khm-in'));
  out.actor = await a1; out.stored = localStorage.getItem('khipu_actor');
  const a3 = window.khipuActor({ ask: true });
  await new Promise(r => setTimeout(r, 10));
  out.noDialogWhenStored = !document.getElementById('khm-ov'); out.actor3 = await a3; out.actorSync = window.khipuActor();
  // 5) cancelar la pregunta → 'usuario' y no se guarda nada
  localStorage.removeItem('khipu_actor');
  const a4 = window.khipuActor({ ask: true });
  await new Promise(r => setTimeout(r, 10));
  key('Escape'); out.actorCancel = await a4; out.storedAfterCancel = localStorage.getItem('khipu_actor');
  // 6) un confirm abierto se cierra (null) si se abre otro diálogo; danger → botón rojo
  p = T.prompt({ title: 'uno' });
  const c = T.confirm({ title: 'dos', danger: true });
  out.superseded = await p;
  await new Promise(r => setTimeout(r, 10));
  out.dangerCls = document.querySelector('#khm-ov .khm-ok').className;
  out.dangerBg = getComputedStyle(document.querySelector('#khm-ov .khm-ok')).backgroundColor;
  document.querySelector('#khm-ov .khm-cancel').click(); out.dangerResult = await c;
  out.native = native;
  return out;
}"""


def test_navegador_prompt_y_actor(browser):
    c = browser.new_context(viewport={'width': 1280, 'height': 800}, service_workers='block')

    def handler(route):
        return route.fulfill(status=200, content_type='text/html', body=PAGE)
    c.route('http://khipu.test/**', handler)
    pg = c.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://khipu.test/')
    pg.add_script_tag(content=TOAST)
    o = pg.evaluate(FLOW)
    pin = o['pin']
    assert pin['type'] == 'password' and pin['ac'] == 'off' and pin['focused'], pin
    assert pin['role'] == 'dialog' and pin['modal'] == 'true' and pin['labelFor'] == 'khm-in' and pin['themed'], pin
    assert pin['titleHtml'] == 'PIN &lt;b&gt;x&lt;/b&gt;', pin            # escapado, nunca HTML crudo
    assert pin['ok'] == 'Aceptar' and pin['cancel'] == 'Cancelar', pin
    assert pin['value'] == '4321' and pin['closed'] and pin['focusBack'], pin
    for k in ('esc', 'cancel', 'x', 'backdrop'):
        assert o[k] is None, (k, o[k])
    assert o['sel'] == [0, 10, 10] and o['labelledby'] == 'khm-t' and o['type2'] == 'text', o
    assert o['clicked'] == ' Nueva '                                       # tal cual: quien llama recorta
    assert o['actorDefault'] == 'usuario' and o['sameAsk'] and o['askTitle'] == '¿Tu nombre?', o
    assert o['actor'] == 'Fabrizio' and o['stored'] == 'Fabrizio', o
    assert o['noDialogWhenStored'] and o['actor3'] == 'Fabrizio' and o['actorSync'] == 'Fabrizio', o
    assert o['actorCancel'] == 'usuario' and o['storedAfterCancel'] is None, o
    assert o['superseded'] is None and 'danger' in o['dangerCls'].split() and o['dangerBg'] == 'rgb(196, 43, 43)', o
    assert o['dangerResult'] is False
    assert o['native'] == [] and not errs, (o['native'], errs)
    c.close()
