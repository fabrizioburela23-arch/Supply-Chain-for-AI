"""tests/test_genui_f3_server.py — RESPUESTAS VISUALES PROGRESIVAS (kblocks/1, fase F3, paso 22), lado servidor
(docs/CHAT_UI_GENERATIVA.md §6.1). Sin red: la IA es un guion falso y las herramientas leen el snapshot local.

  · el progreso (_PROG) lleva un `seq` MONÓTONO y `?since=<seq>` devuelve solo lo nuevo; un id desconocido sigue
    dando exactamente lo de siempre;
  · bloques provisionales SOLO con GENUI=on + context.genui = 1 (shadow los arma pero nunca los envía; off nada);
  · cada provisional sale del MISMO cálculo que el sobre final (constructores, procedencia, esquema, orden): valida
    contra el esquema, y el que el sobre final usa es idéntico (mismo id, mismo JSON); el que no usa quedó fuera del
    sobre por presupuesto (va plegado en el cliente);
  · esqueleto `planned` para el bloque principal mientras su herramienta corre; si la herramienta falla, `error` con
    su motivo bilingüe (nunca un hueco eterno);
  · un bloque se publica en cuanto SU herramienta vuelve (no cuando vuelve la última);
  · topes del parcial: ≤ 14 bloques y ≤ 64 KB por consulta; el resto en la siguiente (`ui.seq`);
  · costo: armar un parcial ≤ 25 ms p95 (§8).
"""
import json
import os
import sys
import threading
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import ai as core_ai  # noqa: E402
from core import genui  # noqa: E402
from core import khipu_chat as kc  # noqa: E402
from core.genui import validate as V  # noqa: E402


class FakeAI:
    def __init__(self, script, on_call=None):
        self.script = list(script)
        self.on_call = on_call
        self.n = 0

    def __call__(self, system, prompt, max_tokens=1000, tier='fast', model=None, verify_numbers=True, **kw):
        self.n += 1
        if self.on_call:
            self.on_call(self.n)
        item = self.script.pop(0) if self.script else {'final': {'answer': 'Listo.', 'actions': []}}
        return (item if isinstance(item, str) else json.dumps(item)), 'fake:model'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    from mcp_server import tools as mt
    monkeypatch.setattr(mt, '_live_profile', lambda sym: {'available': False, 'reason': 'test (offline)'})
    monkeypatch.setattr(mt._auth, 'db_available', lambda: False)
    monkeypatch.setattr(core_ai, '_ai_configured', lambda: True)
    genui.reset_stats()


SCRIPT = [
    {'tool': 'run_scenario', 'args': {'shocks': [{'id': 'TSMC'}]}, 'why': 'choque'},
    {'final': {'answer': '**TSMC** fabrica los chips de la mayoría [F1].\n\nSi cae, el golpe llega lejos [F2].',
               'actions': [{'type': 'open_xray', 'arg': 'TSMC'}]}},
]
Q = '¿Qué pasa si cae TSMC?'


def _run(monkeypatch, rid, context, mode='on', script=SCRIPT, msg=Q, on_call=None):
    """→ (respuesta, estados del progreso tras CADA publicación de bloques, estado al llamar a la IA)."""
    monkeypatch.setenv('GENUI', mode)
    states, at_ai = [], {}
    real = kc.progress_ui

    def spy(req_id, blocks, as_of=None):
        n = real(req_id, blocks, as_of)
        states.append(kc.progress_get(req_id))
        return n
    monkeypatch.setattr(kc, 'progress_ui', spy)

    def call(n):
        at_ai[n] = kc.progress_get(rid)
        if on_call:
            on_call(n)
    monkeypatch.setattr(core_ai, '_ai_complete', FakeAI(script, call))
    out = kc.run_chat(msg, [], 'es', dict(context), req_id=rid)
    return out, states, at_ai


def _blocks(p):
    return (p.get('ui') or {}).get('blocks') or []


# ── seq y since ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_seq_monotono_y_since_devuelve_solo_lo_nuevo(monkeypatch):
    out, states, at_ai = _run(monkeypatch, 'f3-seq', {'genui': 1, 'mode': 'pro'})
    seqs = [s['seq'] for s in states]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs), seqs           # monótono, cada publicación avanza
    fin = kc.progress_get('f3-seq')
    assert fin['done'] is True and fin['seq'] >= seqs[-1]
    allb = _blocks(fin)
    assert allb and all(b['seq'] <= fin['seq'] for b in allb)
    # since = lo ya visto → solo lo nuevo; since = todo → nada (y sin clave `ui`)
    mid = sorted(b['seq'] for b in allb)[0]
    newer = _blocks(kc.progress_get('f3-seq', since=mid))
    assert newer and all(b['seq'] > mid for b in newer)
    assert {b['id'] for b in newer} < {b['id'] for b in allb} or len(newer) < len(allb)
    assert 'ui' not in kc.progress_get('f3-seq', since=fin['seq'])
    # since inválido = sin filtro (nunca un error)
    for bad in ('abc', '-3', None, '', '1e9x'):
        assert len(_blocks(kc.progress_get('f3-seq', since=bad))) == len(allb), bad
    # pregunta de IMPACTO: la ficha pre-consultada NO sale antes que el bloque principal (el sobre final la plegaría y
    # la cascada saltaría arriba); lo primero que se ve es el esqueleto / la cascada de run_scenario
    assert not _blocks(at_ai[1]) and at_ai[1]['done'] is False
    first = next(b for st in states for b in _blocks(st))
    assert first['type'] == 'impact.cascade', first


def test_pregunta_de_empresa_muestra_la_ficha_antes_de_la_ia(monkeypatch):
    """Intención «empresa»: la ficha pre-consultada ES el bloque principal → sale antes de la primera llamada a la IA."""
    script = [{'final': {'answer': '**Nvidia** diseña GPUs [F1].', 'actions': []}}]
    out, states, at_ai = _run(monkeypatch, 'f3-company', {'genui': 1, 'mode': 'simple'}, script=script,
                              msg='¿Cómo está Nvidia?')
    assert _blocks(at_ai[1]) and at_ai[1]['done'] is False
    fin_keys = {kc._ui_key(b) for b in out['ui']['blocks']}
    assert all(kc._ui_key(b) in fin_keys for b in _blocks(at_ai[1])), 'nada de lo mostrado antes se pliega'


def test_impacto_sin_la_herramienta_principal_publica_al_cerrar_la_ronda(monkeypatch):
    """Si la ronda termina sin la herramienta principal, lo retenido (la ficha) sale igual: nunca se queda oculto."""
    script = [{'tool': 'get_company', 'args': {'id_or_ticker': 'TSMC'}, 'why': 'ficha'},
              {'final': {'answer': '**TSMC** fabrica chips [F1].', 'actions': []}}]
    out, states, at_ai = _run(monkeypatch, 'f3-hold', {'genui': 1, 'mode': 'simple'}, script=script)
    assert not _blocks(at_ai[1])
    assert _blocks(kc.progress_get('f3-hold'))


def test_desconocido_igual_que_siempre_y_endpoint_con_since(monkeypatch):
    assert kc.progress_get('nadie-f3') == {'req_id': 'nadie-f3', 'done': False, 'elapsed_ms': 0, 'phase': None,
                                           'agents': []}
    assert kc.progress_get('nadie-f3', since=4) == kc.progress_get('nadie-f3')
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(kc.khipu_chat_bp)
    _run(monkeypatch, 'f3-ep', {'genui': 1})
    c = app.test_client()
    full = c.get('/api/khipu/chat/progress/f3-ep').get_json()
    assert full['ui']['v'] == 'kblocks/1' and full['ui']['state'] == 'partial' and V.errors(full['ui']) == []
    part = c.get('/api/khipu/chat/progress/f3-ep?since=%d' % full['ui']['seq']).get_json()
    assert 'ui' not in part and part['seq'] == full['seq']
    r = c.get('/api/khipu/chat/progress/f3-ep?since=nope')
    assert r.status_code == 200 and len(r.get_json()['ui']['blocks']) == len(full['ui']['blocks'])
    assert r.headers.get('Cache-Control') == 'no-store'


# ── solo con la bandera ─────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize('mode,ctx,sent', [('on', {'genui': 1}, True), ('on', {}, False), ('off', {'genui': 1}, False),
                                           ('shadow', {'genui': 1}, False), ('shadow', {}, False)])
def test_provisionales_solo_con_la_bandera(monkeypatch, mode, ctx, sent):
    rid = 'f3-flag-%s-%d' % (mode, len(ctx))
    out, states, at_ai = _run(monkeypatch, rid, ctx, mode=mode)
    fin = kc.progress_get(rid)
    assert ('ui' in fin) is sent
    assert 'ui' not in at_ai[1]          # impacto: la ficha pre-consultada espera a la cascada (nunca antes de la IA)
    assert any('ui' in st for st in states) is sent
    assert ('ui' in out) is sent                         # el sobre final sigue la MISMA regla (contrato F1)
    assert fin['agents'] and fin['done'] is True         # el progreso de siempre no cambia
    if mode == 'shadow' and ctx:
        assert states and all('ui' not in s for s in states)   # en sombra se arma pero NUNCA sale al cliente
    if mode == 'off' or not ctx:
        assert not states


# ── el mismo cálculo que el sobre final ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize('mode', ['pro', 'simple'])
def test_mismos_ids_y_mismo_json_que_el_final(monkeypatch, mode):
    rid = 'f3-same-' + mode
    cap = {}
    real_core = genui.build_core

    def spy_core(inputs):
        cap['inputs'] = inputs                      # la ÚLTIMA llamada es la del sobre final
        return real_core(inputs)
    monkeypatch.setattr(genui, 'build_core', spy_core)
    out, states, _ = _run(monkeypatch, rid, {'genui': 1, 'mode': mode})
    final = out['ui']
    # los candidatos VÁLIDOS del sobre final (constructores + procedencia + esquema), antes de elegir el orden
    inputs = cap['inputs']
    calls = [tuple(c) for c in inputs['calls']]
    good = []
    for c in genui._candidates(calls, inputs['lang'], inputs['fact_of'], inputs['args_of'], inputs['meta']):
        if genui._check(c, calls)[0]:
            good.append({k: v for k, v in genui._strip(c).items() if k != 'id'})
    fin_by_key = {kc._ui_key(b): b for b in final['blocks']}
    prov = _blocks(kc.progress_get(rid))
    assert prov
    used = 0
    for b in prov:
        assert V.errors(b, 'Block') == [], (b['type'], V.errors(b, 'Block'))
        assert b['state'] in ('ready', 'planned', 'error')
        k = kc._ui_key(b)
        x = dict(b)
        x.pop('seq')
        if k in fin_by_key:
            used += 1
            assert x == fin_by_key[k], k                        # mismo bloque, mismo id → el cliente no repinta
        else:
            # lo que el sobre final no usa es un candidato válido de ESE mismo cálculo que el orden dejó fuera (el
            # cliente lo pliega en «Más datos de esta respuesta»): nunca algo que el sobre final no podría traer
            assert b['state'] == 'ready'
            assert {k: v for k, v in x.items() if k != 'id'} in good, k
    assert used >= 1
    # ningún provisional es texto, acciones ni fuentes (eso llega solo con la respuesta)
    assert not {b['type'] for b in prov} & {'text', 'actions', 'sources'}
    # el parcial completo valida como sobre kblocks/1
    env = kc.progress_get(rid)['ui']
    assert V.errors(env, 'Envelope') == [] and len(json.dumps(env).encode()) <= kc.PROGRESS_UI_MAX_BYTES


def test_esqueleto_del_principal_y_luego_listo(monkeypatch):
    out, states, _ = _run(monkeypatch, 'f3-skel', {'genui': 1, 'mode': 'pro'})
    planned = [b for s in states for b in _blocks(s) if b['state'] == 'planned']
    assert planned and planned[0]['type'] == 'impact.cascade' and planned[0]['prov']['name'] == 'run_scenario'
    assert planned[0]['title']['es'] and planned[0]['title']['en'] and 'data' not in planned[0]
    key = kc._ui_key(planned[0])
    last = [b for b in _blocks(kc.progress_get('f3-skel')) if kc._ui_key(b) == key]
    assert len(last) == 1 and last[0]['state'] == 'ready'                   # la MISMA identidad, ya lista
    casc = next(b for b in out['ui']['blocks'] if b['type'] == 'impact.cascade')
    assert kc._ui_key(casc) == key and casc['id'] == last[0]['id']


def test_herramienta_que_falla_deja_error_honesto(monkeypatch):
    real = kc.execute_tool

    def boom(name, args, app=None, lang=None):
        if name == 'run_scenario':
            return False, {'error': 'kernel down (test)'}
        return real(name, args, app, lang)
    monkeypatch.setattr(kc, 'execute_tool', boom)
    out, states, _ = _run(monkeypatch, 'f3-fail', {'genui': 1, 'mode': 'pro'})
    errs = [b for b in _blocks(kc.progress_get('f3-fail')) if b['state'] == 'error']
    assert len(errs) == 1 and errs[0]['type'] == 'impact.cascade'
    assert errs[0]['error']['es'].startswith('No se pudo') and errs[0]['error']['en'].startswith('Could not')
    assert V.errors(errs[0], 'Block') == []
    assert 'impact.cascade' not in [b['type'] for b in out['ui']['blocks']]   # el sobre final no inventa nada


def test_se_publica_cuando_vuelve_cada_herramienta(monkeypatch):
    """Dos herramientas en la misma ronda: la rápida se ve mientras la lenta sigue corriendo."""
    real = kc.execute_tool
    gate = threading.Event()

    def slow(name, args, app=None, lang=None):
        if name == 'get_news':
            gate.wait(5)
        return real(name, args, app, lang)
    monkeypatch.setattr(kc, 'execute_tool', slow)
    seen = []
    orig = kc.progress_ui

    def spy(req_id, blocks, as_of=None):
        n = orig(req_id, blocks, as_of)
        seen.append([b['type'] for b in blocks if b['state'] == 'ready'])
        if any(b['type'] == 'graph.mini' for b in blocks):
            gate.set()                                   # la lenta termina SOLO después de publicarse la rápida
        return n
    monkeypatch.setattr(kc, 'progress_ui', spy)
    monkeypatch.setenv('GENUI', 'on')
    script = [{'calls': [{'tool': 'get_supply_chain', 'args': {'id': 'Nvidia'}}, {'tool': 'get_news', 'args': {'query': 'Nvidia'}}]},
              {'final': {'answer': 'Depende de TSMC.', 'actions': []}}]
    monkeypatch.setattr(core_ai, '_ai_complete', FakeAI(script))
    t0 = time.monotonic()
    kc.run_chat('proveedores de Nvidia', [], 'es', {'genui': 1, 'mode': 'pro'}, req_id='f3-each')
    assert time.monotonic() - t0 < 5                     # no esperó al tope: la rápida liberó a la lenta
    assert any('graph.mini' in s for s in seen), seen


# ── topes del parcial ───────────────────────────────────────────────────────────────────────────────────────────────
def test_topes_14_bloques_y_64kb_por_consulta():
    rid = 'f3-cap'
    kc.progress_begin(rid, ui={'send': True, 'lang': 'es'})
    big = 'x' * 9000
    blocks = [{'id': 'b%d' % i, 'type': 'callout', 'state': 'ready', 'prov': {'kind': 'tool', 'name': 'get_research', 'call': i},
               'data': {'variant': 'info', 'origin': 'tool', 'text': {'es': big, 'en': big}}} for i in range(20)]
    kc.progress_ui(rid, blocks, '2026-10-14T10:00:00Z')
    got, since, rounds = [], None, 0
    while rounds < 10:
        rounds += 1
        p = kc.progress_get(rid, since=since)
        if 'ui' not in p:
            break
        size = len(json.dumps(p['ui']['blocks']).encode())
        assert len(p['ui']['blocks']) <= kc.PROGRESS_UI_MAX_BLOCKS and size <= kc.PROGRESS_UI_MAX_BYTES + 2048
        got += [b['id'] for b in p['ui']['blocks']]
        since = p['ui']['seq']
    assert sorted(got) == sorted(b['id'] for b in blocks) and rounds >= 3     # todo llega, en varias consultas
    # una publicación igual no genera seq nuevo; un cambio sí (y conserva su lugar)
    s0 = kc.progress_get(rid)['seq']
    kc.progress_ui(rid, blocks[:1])
    assert kc.progress_get(rid)['seq'] == s0
    kc.progress_ui(rid, [dict(blocks[0], id='b9')])
    p = kc.progress_get(rid, since=s0)
    ids = {b['id'] for b in p['ui']['blocks']}
    assert 'b9' in ids and any(i.startswith('q') for i in ids)           # el viejo b9 cede su id: nunca dos iguales
    kc.progress_end(rid)
    s1 = kc.progress_get(rid)['seq']
    assert kc.progress_ui(rid, [dict(blocks[1], id='b7')]) == 0           # terminado: ya no se publica nada
    assert kc.progress_get(rid)['seq'] == s1


def test_armar_un_parcial_cuesta_poco():
    import glob
    calls, facts = [], None
    for p in sorted(glob.glob(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', '*.json'))):
        with open(p, encoding='utf-8') as fh:
            d = json.load(fh)
        calls.append((d['tool'], d.get('args') or {}, True, d['result']))
    # 3 pasadas (la 1.ª calienta cachés); vale la MEJOR p95: con la máquina cargada (CI, carga 17 en 4 CPU) una sola
    # pasada medía 31 ms aunque el armado no cambió
    p95s = []
    for rep in range(3):
        rid = 'f3-cost' + ('' if rep == 2 else str(rep))
        kc.progress_begin(rid, ui={'send': True, 'lang': 'es'})
        pui = kc._ProgUI(rid, '¿Qué pasa si cae TSMC?', 'es', {'genui': 1, 'mode': 'pro'})
        ms = []
        for k in range(1, len(calls) + 1):
            t0 = time.perf_counter()
            pui.publish(calls[:k], [''] * k, facts, round_end=True)
            ms.append((time.perf_counter() - t0) * 1000)
        ms.sort()
        p95s.append(ms[int(0.95 * (len(ms) - 1))])
    print('\n[genui F3] parcial p95 por pasada (ms):', [round(x, 2) for x in p95s])
    assert min(p95s) <= 25.0, p95s
    blocks = _blocks(kc.progress_get(rid))
    assert blocks and all(V.errors(b, 'Block') == [] for b in blocks)
    assert genui.stats()['built'] == 0                   # los parciales no ensucian las métricas del sobre final


def test_los_provisionales_se_sueltan_al_minuto_de_responder(monkeypatch):
    """Memoria (1 worker): los bloques provisionales de una respuesta ya entregada no se guardan 5 min."""
    rid = 'f3-mem'
    kc.progress_begin(rid, ui={'send': True, 'lang': 'es'})
    kc.progress_ui(rid, [{'id': 'b1', 'type': 'callout', 'state': 'ready', 'prov': {'kind': 'tool', 'name': 'get_research', 'call': 0},
                          'data': {'variant': 'info', 'origin': 'tool', 'text': {'es': 'x', 'en': 'x'}}}])
    kc.progress_end(rid)
    assert 'ui' in kc.progress_get(rid)                       # una consulta tardía (justo al terminar) aún los ve
    real = time.time
    monkeypatch.setattr(kc.time, 'time', lambda: real() + kc.PROGRESS_UI_KEEP_S + 1)
    p = kc.progress_get(rid)
    assert 'ui' not in p and p['done'] is True                # el resto del progreso sigue igual
