"""tests/test_genui_review_fixes.py — RESPUESTAS VISUALES (kblocks/1): arreglos de la revisión F2 (2026-10-14), lado
servidor. Cada prueba fallaba antes de su arreglo (las del navegador están en tests/test_genui_browser.py).

  · marcas del texto en UNIDADES UTF-16 (el cliente las usa igual) con emojis delante;
  · la cartera de la cascada: `usd` por posición sobrevive a validate_request y el SERVIDOR la pone en run_scenario
    (lo que escriba el modelo se descarta); sin cartera → `no_positions`;
  · comparación: una cifra vieja nunca sale con la hora de otra fresca;
  · cascada con magnitudes de muchos decimales (1/3) no se descarta;
  · privacidad: el blob ui_inputs no guarda argumentos de texto libre (web_search…);
  · gather_meta no espera a la vista del grafo; el 🩺 juzga una ventana (no contadores de toda la vida);
  · «Preguntar sobre esto» llega al servidor (context.ref_block validado) y al prompt;
  · get_history / run_scenario tienen mascota; la tarjeta 🩺 genui se pinta.
"""
import copy
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import genui  # noqa: E402
from core import khipu_chat as kc  # noqa: E402
from core.genui import builders as B  # noqa: E402
from core.genui.layout import marks_of  # noqa: E402

FIXT = os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools')
SECRET = 'mi cartera privada tiene 48.250 USD en Calle Falsa 123'


def _fx(name):
    with open(os.path.join(FIXT, name + '.json'), encoding='utf-8') as fh:
        return json.load(fh)['result']


def _u16(s, i):
    return len(s[:i].encode('utf-16-le')) // 2


# ── marcas ───────────────────────────────────────────────────────────────────────────────────────────────────────
def test_marcas_en_utf16_con_emojis():
    md = '📈 Nvidia sube 3 % [F1] (⚠ cifra no verificada)'
    mk = marks_of(md, [{'id': 'Nvidia', 'label': 'Nvidia'}])
    u16 = md.encode('utf-16-le')
    got = {m['kind']: u16[2 * m['s']:2 * m['e']].decode('utf-16-le') for m in mk}
    assert got == {'entity': 'Nvidia', 'fact': '[F1]', 'unverified': '(⚠ cifra no verificada)'}
    assert max(m['e'] for m in mk) == len(u16) // 2              # la del final no se sale del texto (en UTF-16)
    # el cliente indexa igual (String.prototype.slice), no por puntos de código
    g = open(os.path.join(ROOT, 'engine', 'genui.js'), encoding='utf-8').read()
    assert 'Array.from(md)' not in g and 'md.slice(0, m.s)' in g and 'm.e > md.length' in g


# ── cartera de la cascada ────────────────────────────────────────────────────────────────────────────────────────
def test_usd_por_posicion_sobrevive_y_lo_pone_el_servidor():
    v = kc.validate_request({'message': 'que pasa si cae TSMC', 'context': {'portfolio': {'positions': [
        {'symbol': 'NVDA', 'shares': 10, 'usd': 1800.5}, {'symbol': 'AMD', 'shares': 2},
        {'symbol': 'AAPL', 'shares': 1, 'usd': float('nan')}, {'symbol': 'TSM', 'shares': 1, 'usd': -5}]}}})
    pf = v['context']['portfolio']
    assert pf[0] == {'symbol': 'NVDA', 'shares': 10.0, 'usd': 1800.5}
    assert all('usd' not in p for p in pf[1:])                   # sin precio / no finito / negativo: sin usd
    # lo que el modelo ponga en positions se descarta; el servidor pone la cartera validada
    model = {'shocks': [{'id': 'TSMC'}], 'positions': [{'symbol': 'NVDA', 'usd': 12345}]}
    a = kc._server_args('run_scenario', model, v['context'])
    assert a == {'shocks': [{'id': 'TSMC'}], 'positions': [{'symbol': 'NVDA', 'usd': 1800.5}]}
    assert kc._server_args('run_scenario', model, {}) == {'shocks': [{'id': 'TSMC'}]}
    assert model['positions'][0]['usd'] == 12345                 # sin mutar lo del modelo
    assert kc._server_args('get_company', {'id_or_ticker': 'x', 'positions': 1}, v['context'])['positions'] == 1
    # el modelo ni siquiera ve el argumento en el catálogo del chat
    sig = [t for t in kc.tool_catalog() if t[0] == 'run_scenario'][0][1]
    assert 'positions' not in sig and 'shocks' in sig
    # y el bucle de herramientas pasa por _server_args
    src = open(os.path.join(ROOT, 'core', 'khipu_chat.py'), encoding='utf-8').read()
    assert "execute_tool, c['tool'], _server_args(c['tool'], c['args'], context)" in src


def test_cascada_sin_cartera_dice_no_positions():
    r = _fx('run_scenario__tsmc')
    assert 'portfolio' not in r
    blk = B.BUILDERS['run_scenario'](copy.deepcopy(r), B.Ctx('es', 0, 'F1', ''))[0]
    assert blk['data']['portfolio'] == {'state': 'no_positions'}


def test_cascada_con_magnitud_de_muchos_decimales():
    r = copy.deepcopy(_fx('run_scenario__tsmc'))
    for s in r['shocks']:
        s['magnitude'] = 1 / 3
    env, _ = genui.build_ui('que pasa si cae TSMC', [('run_scenario', {}, True, r)],
                            [{'id': 'TSMC', 'label': 'TSMC'}], None, 'es', {'answer': 'Golpe amplio.'})
    blk = [b for b in env['blocks'] if b['type'] == 'impact.cascade']
    assert blk and blk[0]['data']['severity'] == 33.3333
    # la composición no afloja el resto: un % que NO está en la fuente sigue sin pasar
    from core.genui import provenance as P
    assert P._ok(33.3333, P._Pool([{'m': 1 / 3}]), {'scale100_round'}, (), None)
    assert not P._ok(33.4, P._Pool([{'m': 1 / 3}]), {'scale100_round'}, (), None)


# ── comparación ──────────────────────────────────────────────────────────────────────────────────────────────────
def _cmp(amd_time):
    a, b = _fx('get_company__nvidia'), copy.deepcopy(_fx('get_company__amd'))
    b['live_market']['market_time'] = amd_time
    b['live_market']['as_of'] = amd_time
    env, _ = genui.build_ui('compara Nvidia vs AMD', [('get_company', {}, True, a), ('get_company', {}, True, b)],
                            [{'id': 'Nvidia', 'label': 'Nvidia'}, {'id': 'AMD', 'label': 'AMD'}], None, 'es',
                            {'answer': 'x'})
    c = [x for x in env['blocks'] if x['type'] == 'comparison']
    return {m['key']: m for m in c[0]['data']['metrics']} if c else {}


def test_comparacion_nunca_pone_hora_fresca_a_una_cifra_vieja():
    old = _cmp('2026-10-02T19:58:00Z')                          # AMD 11 días más vieja
    assert old and 'price' not in old and 'change' not in old    # la comparación sigue, sin las filas viejas
    near = _cmp('2026-10-13T17:58:00Z')                         # 2 h de diferencia: va, con la hora MÁS VIEJA
    assert near['price']['values']['as_of'] == '2026-10-13T17:58:00Z'
    # formatos mezclados: se comparan en UTC, no como texto
    assert B._ts('2026-10-13T15:58:00-04:00') == B._ts('2026-10-13T19:58:00Z')


# ── privacidad del libro ─────────────────────────────────────────────────────────────────────────────────────────
def test_entradas_sin_argumentos_de_texto_libre():
    d = _fx('get_company__nvidia')
    calls = [('get_company', {'id_or_ticker': 'Nvidia'}, True, d), ('web_search', {'query': SECRET}, True, {'results': []}),
             ('run_scenario', {'scenario': SECRET}, False, {'error': 'x'})]
    args_of = [kc._args_summary(c[1]) for c in calls]
    env, _ = genui.build_ui(SECRET, calls, [{'id': 'Nvidia', 'label': 'Nvidia'}], None, 'es', {
        'answer': 'x', 'args_of': args_of,
        'sources': [{'label': 'Reuters', 'url': 'https://r.example/a', 'as_of': '2026-10-13T10:00:00Z', 'note': SECRET},
                    {'label': 'mal', 'url': 'javascript:alert(1)', 'as_of': '2026-10-13T10:00:00Z'}]})
    raw = json.dumps(env['_inputs'], ensure_ascii=False) + json.dumps(genui.public(env), ensure_ascii=False)
    assert 'Calle Falsa' not in raw and '48.250' not in raw
    assert env['_inputs']['args_of'] == ['Nvidia', '', '']           # solo herramientas de ids/enumerados
    assert env['_inputs']['sources'] == [{'label': 'Reuters', 'url': 'https://r.example/a', 'as_of': '2026-10-13T10:00:00Z'}]


def test_gather_meta_no_espera_a_la_vista(monkeypatch):
    from core.hotviews import hot
    seen = []
    monkeypatch.setattr(hot, 'graph', lambda wait=True, timeout=None: seen.append(wait) or None)
    m = genui.gather_meta([('get_history', {}, True, {'id': 'Nvidia'})])
    assert seen == [False] and m == {'labels': {}}


# ── 🩺 ───────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_salud_por_ventana_y_con_muestras(monkeypatch):
    genui.reset_stats()
    try:
        genui._record(757, 1000, None, [], 0, 0)                  # un armado lento en frío no pone la tarjeta en rojo
        assert genui.healthy()
        genui._record(0, 0, None, [], 0, 0, error='X')
        assert not genui.healthy() and genui.stats()['errors_24h'] == 1
        import time as _t
        real = _t.monotonic
        monkeypatch.setattr(genui.time, 'monotonic', lambda: real() + genui.WINDOW_S + 5)
        assert genui.healthy() and genui.stats()['errors'] == 1   # el total sigue, la ventana ya no lo cuenta
    finally:
        genui.reset_stats()
    js = open(os.path.join(ROOT, 'engine', 'app_main.js'), encoding='utf-8').read()
    order = re.search(r"const order = \[([^\]]+)\];", js).group(1)
    assert "'genui'" in order and re.search(r"\n  genui:\s+\{ icon:", js)


# ── «Preguntar sobre esto» ───────────────────────────────────────────────────────────────────────────────────────
def test_ref_block_llega_validado_al_prompt():
    v = kc.validate_request({'message': 'y eso?', 'context': {'genui': 1, 'ref_block': {
        'id': 'b1', 'prov': {'name': 'get_company', 'args': 'Nvidia <script>', 'fact': 'F2'}}}})
    assert v['context']['ref_block'] == {'id': 'b1', 'tool': 'get_company', 'args': 'Nvidia script', 'fact': 'F2'}
    for bad in ({'id': 'b1', 'prov': {'name': 'place_order'}}, {'id': '<x>', 'prov': {'name': 'get_company'}}, 'x'):
        assert 'ref_block' not in kc.validate_request({'message': 'x', 'context': {'genui': 1, 'ref_block': bad}})['context']
    p = kc.build_prompt('y eso?', [], 'es', v['context'], [], 3, False)
    assert 'BLOQUE VISUAL' in p and 'get_company(Nvidia script)' in p


# ── mascotas ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_herramientas_nuevas_con_mascota():
    from core import agents_registry as ar
    ta = ar.TOOL_AGENT
    assert ta['get_history'] == 'tecnico' and ta['run_scenario'] == 'cadena'
