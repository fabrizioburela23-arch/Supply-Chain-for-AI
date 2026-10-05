"""tests/test_chat_commands.py — comandos y agentes en el chat de Khipu
(pedido 2026-10-05): /ayuda, /investigar, /comite, /cartera, @investigación,
"llama al agente de investigación…", "que el comité analice mi cartera"."""
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')

JS = r"""
const calls = [];
global.window = { LANG: process.argv[2], KhipuCommittee: { openTab: t => calls.push('tab:' + t), open: id => calls.push('open:' + id) } };
global.localStorage = { getItem: () => null };
global.document = { createElement: () => ({}), getElementById: () => null };
require(process.argv[1] + '/engine/khipu_chat.js');
const db = { nvidia: 'Nvidia', nvda: 'Nvidia', tsmc: 'TSMC', amd: 'AMD' };
const deps = { resolve: q => { const id = db[String(q).toLowerCase().trim()]; return id ? { node: { id, label: id }, score: 95 } : null; } };
const cases = JSON.parse(process.argv[3]);
(async () => {
  const out = {};
  for (const c of cases) {
    calls.length = 0;
    const r = window.KhipuChat.classify(c, deps);
    const o = { kind: r.kind, id: r.id || null };
    if (r.kind === 'command') o.answer = (await r.pending).answer;
    o.calls = calls.slice();
    out[c] = o;
  }
  process.stdout.write(JSON.stringify(out));
})();
"""


def _run(cases, lang='es'):
    res = subprocess.run([NODE, '-e', JS, ROOT, lang, json.dumps(cases)], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_agente_de_investigacion_desde_el_chat():
    out = _run(['/investigar NVDA', '@investigación AMD', 'llama al agente de investigación para TSMC',
                '@research tsmc?'])
    assert [out[c]['kind'] for c in out] == ['research'] * 4
    assert [out[c]['id'] for c in out] == ['Nvidia', 'AMD', 'TSMC', 'TSMC']


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_comite_de_cartera_y_de_empresa_desde_el_chat():
    out = _run(['/cartera', '/comite cartera', '@comité mi cartera', 'que el comité analice mi cartera', '/comite TSMC'])
    for c in ('/cartera', '/comite cartera', '@comité mi cartera', 'que el comité analice mi cartera'):
        assert out[c]['kind'] == 'command' and out[c]['calls'] == ['tab:portfolio'] and 'nunca una orden' in out[c]['answer']
    assert out['/comite TSMC']['calls'] == ['open:TSMC']


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_ayuda_bilingue_y_los_analistas_siguen_en_el_cerebro():
    es = _run(['/ayuda', '/xyz', '@fundamental ¿qué opinas de TSMC?', '¿cómo va mi cartera?'])
    assert '/investigar' in es['/ayuda']['answer'] and '/cartera' in es['/ayuda']['answer']
    assert 'No conozco el comando' in es['/xyz']['answer']
    assert es['@fundamental ¿qué opinas de TSMC?']['kind'] == 'brain' and es['¿cómo va mi cartera?']['kind'] == 'brain'
    en = _run(['/help'], lang='en')
    assert '/research' in en['/help']['answer'] and '/portfolio' in en['/help']['answer']
