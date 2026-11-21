"""tests/test_ui_prefs.py — la interfaz APRENDE de cada persona (engine/uiprefs.js → context.ui_prefs → servidor).

Se blinda: el navegador solo manda TIPOS de bloque (nada personal); el servidor solo acepta tipos conocidos; las
preferencias cambian el ORDEN de los bloques y una línea del prompt, nunca las cifras ni qué bloques existen.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NODE = r"""
const fs = require('fs'), vm = require('vm');
const store = {}, listeners = {};
const ls = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } };
function closest(sel) { return this._kg ? this : null; }
const doc = { addEventListener: (t, f) => { listeners[t] = f; } };
const W = { document: doc, localStorage: ls, addEventListener: () => {} };
W.KhipuGenUI = { renderAnswer: (h, env) => 'ok' };
const ctx = vm.createContext({ window: W, localStorage: ls, setTimeout: (f) => f(), clearTimeout: () => {}, setInterval: () => 0,
  clearInterval: () => {}, WeakSet, Date, JSON, Math, Object, Array });
vm.runInContext(fs.readFileSync('engine/uiprefs.js', 'utf8'), ctx);
const U = W.KhipuUiPrefs;
const out = { before: U.ctx(), hooked: !!W.KhipuGenUI._uiprefs };
// 8 respuestas con línea + tabla; la persona toca la línea 5 veces y nunca la tabla
for (let i = 0; i < 8; i++) {
  const env = { blocks: [{ type: 'text' }, { type: 'chart.line', id: 'b1' }, { type: 'table', id: 'b2' }] };
  W.KhipuGenUI.renderAnswer(null, env);
  W.KhipuGenUI.renderAnswer(null, env);              // repintar el MISMO sobre no cuenta dos veces
  if (i < 5) {
    const el = { _kg: 1, getAttribute: a => (a === 'data-kg-type' ? 'chart.line' : 'b1-' + i), closest };
    listeners.click({ target: el });
  }
}
out.state = U._state();
out.ctx = U.ctx();
out.summary = U.summary('es');
out.stored = JSON.parse(store.kh_ui_prefs);
U.reset();
out.after = U.ctx();
console.log(JSON.stringify(out));
"""


def _run():
    r = subprocess.run(['node', '-e', NODE], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_browser_learns_used_and_skipped_block_types():
    o = _run()
    assert o['before'] is None and o['hooked']
    assert o['state']['shown'] == {'chart.line': 8, 'table': 8}            # texto no cuenta; repintar tampoco
    assert o['state']['used'] == {'chart.line': 5}
    assert o['ctx'] == {'more': ['chart.line'], 'less': ['table']}
    assert 'gráficos de evolución' in o['summary'] and 'tablas' in o['summary']
    assert set(o['stored']) == {'v', 'shown', 'used'}                       # solo contadores por tipo
    assert o['after'] is None


def test_server_accepts_only_known_types():
    from core.genui import clean_prefs
    assert clean_prefs({'more': ['chart.line', 'x<script>', 'chart.line'], 'less': ['table', 'chart.line']}) == \
        {'more': ['chart.line'], 'less': ['table']}
    assert clean_prefs({'more': [], 'less': []}) is None
    assert clean_prefs('chart.line') is None


def test_prefs_reorder_but_never_add_or_drop_blocks():
    from core.genui import prefer
    good = [{'type': 'table', 'n': 1}, {'type': 'chart.bar', 'n': 2}, {'type': 'chart.line', 'n': 3}]
    out = prefer(good, {'more': ['chart.line'], 'less': ['table']})
    assert [b['type'] for b in out] == ['chart.line', 'chart.bar', 'table']
    assert sorted(b['n'] for b in out) == [1, 2, 3]
    assert prefer(good, None) is good


def test_chat_request_keeps_prefs_and_prompt_mentions_them():
    from core.khipu_chat import build_prompt, validate_request
    req = validate_request({'message': '¿cómo va Nvidia?', 'context': {'ui_prefs': {'more': ['chart.line'],
                                                                                     'less': ['table', 'nope']}}})
    assert req['context']['ui_prefs'] == {'more': ['chart.line'], 'less': ['table']}
    p = build_prompt(req['message'], [], 'es', req['context'], [], 3, False)
    assert 'LO QUE ESTA PERSONA USA' in p and 'chart.line' in p and 'table' in p
    plain = validate_request({'message': 'hola'})
    assert 'ui_prefs' not in plain['context']


def test_wired_in_app_shell_sync_and_chat():
    html = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    assert html.index('engine/khipu_chat.js') < html.index('engine/uiprefs.js')
    sw = open(os.path.join(ROOT, 'sw.js'), encoding='utf-8').read()
    assert "'/engine/uiprefs.js'" in sw
    assert "'kh_ui_prefs'" in open(os.path.join(ROOT, 'engine/sync.js'), encoding='utf-8').read()
    from core.portfolio_reports_api import SYNC_KEYS
    assert 'kh_ui_prefs' in SYNC_KEYS
    assert 'ctx.ui_prefs' in open(os.path.join(ROOT, 'engine/khipu_chat.js'), encoding='utf-8').read()
