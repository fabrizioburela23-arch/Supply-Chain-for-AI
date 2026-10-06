"""tests/test_khipus_os_server.py — Khipus OS, lado servidor (docs/KHIPUS_OS.md §3.2 y §3.3).

· /api/khipu/chat: req_id + progreso en vivo (GET /api/khipu/chat/progress/<req_id>), agents_used con
  notas DETERMINISTAS (solo valores de las herramientas), entities, cards, sources[].as_of — en el camino
  con IA, en el de respaldo sin IA y en la ruta @analista; modo simple/pro y agentes activos en el prompt;
  ficha + DATOS EN VIVO en PARALELO; el analista responde en el idioma de la petición.
· /api/agents/profiles: 6 mascotas, bilingüe, sin base de datos → 200 con db:false.
· research/committee.board: caché de 60 s por argumentos, con huella e invalidación.
Sin red y sin DATABASE_URL: la IA es un guion falso y el perfil en vivo se simula."""
import json
import os
import re
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask  # noqa: E402

from core import ai as core_ai  # noqa: E402
from core import khipu_chat as kc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = {'available': True, 'price': 183.25, 'change_pct': 1.234, 'currency': 'USD', 'market_cap_usd_b': 4470.2,
        'source': 'yahoo', 'as_of': '2026-10-06T14:32:05+00:00'}


class FakeAI:
    def __init__(self, script, on_call=None):
        self.script = list(script)
        self.systems, self.prompts, self.times = [], [], []
        self.on_call = on_call

    def __call__(self, system, prompt, max_tokens=1000, tier='fast', model=None, verify_numbers=True, **kw):
        self.systems.append(system)
        self.prompts.append(prompt)
        self.times.append(time.monotonic())
        if self.on_call:
            self.on_call(len(self.prompts))
        if not self.script:
            return json.dumps({'final': {'answer': 'listo', 'actions': []}}), 'fake:model'
        item = self.script.pop(0)
        return (item if isinstance(item, str) else json.dumps(item)), 'fake:model'


@pytest.fixture
def fake_ai(monkeypatch):
    def install(script, configured=True, on_call=None):
        f = FakeAI(script, on_call)
        monkeypatch.setattr(core_ai, '_ai_complete', f)
        monkeypatch.setattr(core_ai, '_ai_configured', lambda: configured)
        return f
    return install


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """Sin red: perfil en vivo simulado (con precio), sin base del MCP, sin bloque DATOS EN VIVO."""
    from core import live_facts
    from mcp_server import tools as mt
    monkeypatch.setattr(mt, '_live_profile', lambda sym: dict(LIVE, symbol=sym))
    monkeypatch.setattr(mt._auth, 'db_available', lambda: False)
    monkeypatch.setattr(live_facts, 'live_facts_block', lambda text, *a, **k: '')


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(kc.khipu_chat_bp)
    return app.test_client()


Q = '¿Cómo está Nvidia y cuál es su mayor riesgo?'
OLD_KEYS = ('answer', 'actions', 'tools_used', 'sources', 'model', 'answer_source', 'ai', 'lang', 'steps',
            'elapsed_ms', 'as_of')


# ════════════════════════════════════════════════════════════════════════════
# mapa herramienta → agente (contrato §3.2)
# ════════════════════════════════════════════════════════════════════════════
def test_mapa_herramienta_agente_es_el_del_contrato():
    assert kc.TOOL_AGENT == {
        'get_company': 'analista', 'search_companies': 'analista', 'get_research': 'analista',
        'get_claim_evidence': 'analista', 'get_supply_chain': 'cadena', 'rank_companies': 'cadena',
        'get_news': 'radar', 'get_world_events': 'radar', 'web_search': 'radar', 'scenario_exposure': 'radar',
        'market_movers': 'tecnico', 'get_option_greeks': 'tecnico', 'get_risk_report': 'tecnico',
        'get_committee_memo': 'comite', 'get_conclusions_board': 'comite', 'get_track_record': 'comite'}
    assert kc.tool_agent('get_space_summary') == 'khipu' and kc.tool_agent('get_research_health') == 'khipu'
    for seat, ag in (('fundamental', 'analista'), ('macro', 'analista'), ('news', 'radar'), ('geopolitical', 'radar'),
                     ('crypto', 'radar'), ('supply_chain', 'cadena'), ('technical', 'tecnico'),
                     ('risk_observation', 'tecnico'), ('all', 'comite'), ('técnico', 'tecnico'),
                     ('noticias', 'radar'), ('todos', 'comite')):
        assert kc.tool_agent('ask_agent', {'seat': seat}) == ag, seat


def test_mapa_de_puestos_igual_que_mascot_js():
    path = os.path.join(ROOT, 'engine', 'mascot.js')
    if not os.path.exists(path):
        pytest.skip('engine/mascot.js todavía no está en esta rama (lo integra otro constructor)')
    src = open(path, encoding='utf-8').read()
    js = {}
    for ag, seats in re.findall(r"\{\s*id:\s*'(\w+)'.*?seats:\s*\[([^\]]*)\]", src, re.S):
        for s in re.findall(r"'([^']+)'", seats):
            js[s] = ag
    assert js and js == kc.SEAT_AGENT


# ════════════════════════════════════════════════════════════════════════════
# progreso en vivo
# ════════════════════════════════════════════════════════════════════════════
def test_progreso_ciclo_de_vida(fake_ai):
    rid = 'os-test_1'
    seen = {}

    def spy(n):
        seen[n] = kc.progress_get(rid)
    fake_ai([{'tool': 'get_supply_chain', 'args': {'id': 'Nvidia', 'direction': 'up'}},
             {'final': {'answer': 'Depende de TSMC.', 'actions': []}}], on_call=spy)
    assert kc.progress_get(rid) == {'req_id': rid, 'done': False, 'elapsed_ms': 0, 'phase': None, 'agents': []}
    out = kc.run_chat(Q, [], 'es', {}, req_id=rid)
    assert out['req_id'] == rid
    # 1.ª llamada a la IA: la ficha pre-consultada ya terminó (Analista)
    assert seen[1]['done'] is False and seen[1]['phase'] == 'thinking'
    assert seen[1]['agents'] == [{'agent': 'analista', 'tool': 'get_company', 'state': 'done'}]
    # 2.ª: Cadena trabajó con get_supply_chain
    assert {'agent': 'cadena', 'tool': 'get_supply_chain', 'state': 'done'} in seen[2]['agents']
    fin = kc.progress_get(rid)
    assert fin['done'] is True and fin['phase'] == 'done' and fin['elapsed_ms'] >= 0
    assert all(a['state'] in ('done', 'error') for a in fin['agents'])


def test_progreso_endpoint_propio_y_desconocido(client, fake_ai):
    fake_ai([{'final': {'answer': 'Nvidia va bien.', 'actions': []}}])
    r = client.get('/api/khipu/chat/progress/no-existe_123')
    assert r.status_code == 200 and r.get_json() == {'req_id': 'no-existe_123', 'done': False, 'elapsed_ms': 0,
                                                     'phase': None, 'agents': []}
    assert r.headers.get('Cache-Control') == 'no-store'
    assert client.get('/api/khipu/chat/progress/' + 'x' * 65).status_code == 400
    assert client.get('/api/khipu/chat/progress/a.b').status_code == 400
    r = client.post('/api/khipu/chat', json={'message': Q, 'lang': 'es', 'req_id': 'k1-abc'})
    d = r.get_json()
    assert r.status_code == 200 and d['req_id'] == 'k1-abc'
    p = client.get('/api/khipu/chat/progress/k1-abc').get_json()
    assert p['done'] is True and p['agents'][0]['agent'] == 'analista'
    # req_id inválido en el pedido: se ignora (no rompe) y el servidor da uno propio
    d2 = client.post('/api/khipu/chat', json={'message': 'hola', 'req_id': 'mal id!'}).get_json()
    assert d2['req_id'] and d2['req_id'] != 'mal id!' and kc.valid_req_id(d2['req_id'])
    # el límite de tasa del progreso es OTRO que el del chat (clave = nombre de la función)
    assert kc.chat_progress_endpoint.__name__ != kc.chat_endpoint.__name__


def test_progreso_tope_y_vencimiento(monkeypatch):
    monkeypatch.setattr(kc, 'PROGRESS_MAX', 3)
    for i in range(5):
        kc.progress_begin(f'cap-{i}')
    assert kc.progress_get('cap-0')['agents'] == [] and kc.progress_get('cap-0')['phase'] is None   # desalojado
    kc.progress_add('cap-4', 'get_news')
    assert kc.progress_get('cap-4')['agents'] == [{'agent': 'radar', 'tool': 'get_news', 'state': 'working'}]
    kc.progress_end('cap-4')
    assert kc.progress_get('cap-4')['agents'][0]['state'] == 'error'        # no llegó a tiempo
    monkeypatch.setattr(kc, 'PROGRESS_TTL_S', -1)
    assert kc.progress_get('cap-4')['done'] is False                         # vencido → desconocido
    assert kc.progress_add(None, 'get_news') is None                         # sin req_id: no-op


# ════════════════════════════════════════════════════════════════════════════
# agents_used / entities / cards / sources.as_of
# ════════════════════════════════════════════════════════════════════════════
def _check_new_fields(out):
    for k in OLD_KEYS:
        assert k in out, k
    for k in ('req_id', 'entities', 'agents_used', 'cards'):
        assert k in out, k
    assert all('as_of' in s for s in out['sources'])
    for a in out['agents_used']:
        assert set(a) >= {'agent', 'tools', 'ok', 'note_es', 'note_en'} and a['agent'] in kc.AGENT_IDS
        assert a['note_es'] and a['note_en']


def test_camino_con_ia_suma_agentes_tarjetas_y_entidades(fake_ai):
    fake_ai([{'tool': 'get_supply_chain', 'args': {'id': 'Nvidia', 'direction': 'up'}},
             {'final': {'answer': 'TEXTO DEL MODELO 98765.', 'actions': []}}])
    out = kc.run_chat(Q, [], 'es', {})
    _check_new_fields(out)
    assert out['answer'] == 'TEXTO DEL MODELO 98765.' and out['answer_source'] == 'ai'
    assert out['entities'][0] == {'id': 'Nvidia', 'label': 'Nvidia'}
    ag = {a['agent']: a for a in out['agents_used']}
    assert [a['agent'] for a in out['agents_used']] == ['analista', 'cadena']
    an = ag['analista']
    assert an['tools'] == ['get_company'] and an['ok'] is True
    assert '183,25 USD' in an['note_es'] and '+1,23 %' in an['note_es'] and '4.470 mil millones USD' in an['note_es']
    assert '183.25 USD' in an['note_en'] and '$4,470B' in an['note_en'] and 'NRS' in an['note_en']
    assert an['source'] == 'Yahoo Finance' and an['as_of'] == LIVE['as_of']
    cd = ag['cadena']
    assert 'get_supply_chain' in cd['tools'] and 'TSMC' in cd['note_es'] and 'TSMC' in cd['note_en']
    # la nota NUNCA es texto del modelo
    assert all('98765' not in a['note_es'] + a['note_en'] for a in out['agents_used'])
    card = out['cards']['company']
    assert card['id'] == 'Nvidia' and card['price'] == 183.25 and card['market_cap_usd_b'] == 4470.2
    assert card['source'] == 'yahoo' and card['as_of'] == LIVE['as_of'] and isinstance(card['nrs'], int)
    assert card['top_suppliers'] and set(card['top_suppliers'][0]) >= {'id', 'label', 'weight', 'type'}
    assert card['top_customers'] and card['structure']['risk_sources']
    assert 'committee' not in out['cards']
    live_src = [s for s in out['sources'] if s['label'].endswith('(live)')]
    assert live_src and live_src[0]['as_of'] == LIVE['as_of']


def test_camino_sin_ia_tambien_trae_los_campos(fake_ai):
    fake_ai([], configured=False)
    out = kc.run_chat('How is Nvidia doing and what is its biggest risk?', [], 'en', {})
    _check_new_fields(out)
    assert out['answer_source'] == 'fallback' and out['degraded'] == 'no_ai'
    assert out['entities'][0]['id'] == 'Nvidia' and out['cards']['company']['price'] == 183.25
    ag = {a['agent']: a for a in out['agents_used']}
    assert 'analista' in ag and '183.25 USD' in ag['analista']['note_en']
    # "riesgo" en la pregunta → Cadena aporta desde la estructura de la ficha
    assert 'cadena' in ag and ag['cadena']['tools'] == ['get_company'] and 'upstream' in ag['cadena']['note_en']
    # sin palabra de riesgo/proveedores: Cadena no se cuelga de la ficha
    out2 = kc.run_chat('¿Qué opinas de Nvidia?', [], 'es', {})
    assert [a['agent'] for a in out2['agents_used']] == ['analista']
    # con Cadena desactivada tampoco
    out3 = kc.run_chat(Q, [], 'es', {'agents_enabled': ['khipu', 'analista']})
    assert [a['agent'] for a in out3['agents_used']] == ['analista']


def test_sin_empresa_campos_vacios_pero_presentes(fake_ai):
    fake_ai([{'final': {'answer': 'El VaR es…', 'actions': []}}])
    out = kc.run_chat('¿qué es el VaR?', [], 'es', {})
    _check_new_fields(out)
    assert out['entities'] == [] and out['agents_used'] == [] and out['cards'] == {} and out['req_id']


def test_herramienta_fallida_nota_honesta(fake_ai):
    fake_ai([{'tool': 'get_supply_chain', 'args': {'id': 'empresa-que-no-existe-zzqq'}},
             {'final': {'answer': 'No la encontré.', 'actions': []}}])
    out = kc.run_chat('proveedores de zzqq', [], 'es', {})
    cd = next(a for a in out['agents_used'] if a['agent'] == 'cadena')
    assert cd['ok'] is False and cd['note_es'] == 'No pudo obtener los datos ahora'
    assert cd['note_en'] == 'Could not get the data right now'


def test_notas_y_tarjeta_del_comite_deterministas():
    memo = {'memo_id': 'm1', 'entity_id': 'Nvidia', 'label': 'Nvidia', 'status': 'proposed', 'decision': 'BUY',
            'overall_conviction': 42.0, 'created_at': '2026-10-05T10:00:00+00:00', 'expired': False,
            'conviction': {'LONG_TERM': {'score': 50.6}}, 'source': 'Khipus investment committee',
            'memo': {'decision_label_es': 'COMPRAR', 'decision_label_en': 'BUY', 'decision_code': None,
                     'thesis': [{'horizon': 'LONG_TERM', 'thesis_es': 'Demanda asegurada.', 'thesis_en': 'Secured demand.'}],
                     'key_risks': [{'risk_es': 'Depende de TSMC.', 'risk_en': 'Depends on TSMC.'}],
                     'track_validation': {'label_es': 'no validado', 'label_en': 'not validated'}}}
    board = {'items': [{'entity_id': 'TSMC', 'label': 'TSMC', 'conviction': 50.6, 'committee': None},
                       {'entity_id': 'Nvidia', 'label': 'Nvidia', 'conviction': 42.0,
                        'committee': {'decision': 'BUY', 'status': 'proposed'}}],
             'source': 'Khipus research claims + committee memos', 'as_of': 'x'}
    calls = [('get_committee_memo', {'entity': 'Nvidia'}, True, memo),
             ('get_conclusions_board', {}, True, board)]
    ents = kc.chat_entities(Q, calls)
    assert ents[0]['id'] == 'Nvidia'
    used = kc.agents_used(calls, Q, {}, ents)
    assert len(used) == 1 and used[0]['agent'] == 'comite'
    assert used[0]['note_es'].startswith('Propone comprar (convicción +42) · espera tu revisión')
    assert 'Convicción de los agentes en Nvidia: +42,0 · comité: comprar' in used[0]['note_es']
    assert used[0]['note_en'].startswith('Proposes buy (conviction +42) · awaiting your review')
    card = kc.chat_cards(calls, ents)['committee']
    assert card['memo_id'] == 'm1' and card['decision_label_es'] == 'COMPRAR' and card['overall_conviction'] == 42.0
    assert card['thesis_es'] == ['Demanda asegurada.'] and card['risks_en'] == ['Depends on TSMC.']
    assert card['by_horizon'] == {'LONG_TERM': 50.6} and card['expired'] is False
    insuf = dict(memo, memo=dict(memo['memo'], decision_code='INSUFFICIENT_DATA'), decision='HOLD')
    n = kc.agents_used([('get_committee_memo', {}, True, insuf)], Q, {}, ents)[0]
    assert n['note_es'].startswith('Sin veredicto: faltan analistas')


def test_notas_de_radar_y_tecnico():
    calls = [
        ('get_news', {'company': 'Nvidia'}, True, {'company': {'id': 'Nvidia'}, 'items': [
            {'title': 'Nvidia presenta un chip nuevo', 'outlet': 'Reuters', 'url': 'https://x.test/a'}],
            'source': 'Finnhub company news', 'as_of': '2026-10-06T10:00:00+00:00'}),
        ('market_movers', {'direction': 'down'}, True, {'direction': 'down', 'items': [
            {'label': 'Intel', 'change_pct': -4.25}, {'label': 'AMD', 'change_pct': -2.1}], 'source': 'Yahoo', 'as_of': 'y'}),
        ('get_risk_report', {}, True, {'vol_ann_pct': 38.2, 'var95': {'hist_1d_pct': 2.913}, 'max_drawdown_pct': -27.4,
                                      'as_of': '2026-10-03'}),
    ]
    used = {a['agent']: a for a in kc.agents_used(calls, 'qué pasa hoy', {}, [])}
    assert used['radar']['note_es'] == 'Última noticia: «Nvidia presenta un chip nuevo» (Reuters)'
    assert used['radar']['note_en'] == 'Latest news: "Nvidia presenta un chip nuevo" (Reuters)'
    t = used['tecnico']
    assert t['tools'] == ['market_movers', 'get_risk_report']
    assert t['note_es'] == 'Más caen hoy: Intel (-4,2 %), AMD (-2,1 %) · Volatilidad anual 38,2 % · VaR 95 % a 1 día 2,91 % · peor caída -27,4 %'
    assert 'Top losers today: Intel (-4.2%)' in t['note_en']


def test_cifras_formateadas_sin_perder_precision_ni_cortarse():
    assert kc._price(0.012345, 'es') == '0,0123' and kc._price(1234.5, 'en') == '1,234.50'
    assert kc._usd_b(0.45, 'es') == '450 millones USD' and kc._usd_b(0.45, 'en') == '$450M'
    assert kc._usd_b(52.34, 'es') == '52,3 mil millones USD' and kc._usd_b(4470.2, 'en') == '$4,470B'
    assert kc._usd_b(None, 'es') is None and kc._usd_b(True, 'es') is None and kc._pct('x', 'es') is None
    # dos fichas largas: la 2.ª solo entra si cabe ENTERA (nunca "4.47…")
    def comp(nid, label):
        return ('get_company', {'id_or_ticker': nid}, True,
                {'id': nid, 'label': label + ' ' + 'x' * 70, 'listed': True, 'network_risk_score': {'value': 40},
                 'live_market': dict(LIVE)})
    used = kc.agents_used([comp('Nvidia', 'Nvidia'), comp('AMD', 'AMD')], 'compara', {}, [])
    note = used[0]['note_es']
    assert '…' not in note and len(note) <= kc._NOTE_MAX and note.count('183,25 USD') == 1


def test_ruta_arroba_trae_los_campos_y_usa_la_empresa_en_pantalla(monkeypatch):
    from research import ask_agent as aa
    monkeypatch.setattr('ontology.db.ontology_available', lambda: True)

    class _S:
        def __enter__(self):
            return None

        def __exit__(self, *a):
            return False
    monkeypatch.setattr('ontology.db.session_scope', lambda: _S())
    seen = {}

    def fake_ask(s, seat, q, ent, lang):
        seen.update(seat=seat, ent=ent, lang=lang)
        return {'ok': True, 'seat': seat, 'emoji': '📈', 'name': 'Technical analyst', 'entity': ent, 'label': ent,
                'answer': 'My view [C1].', 'refs': {}, 'n_claims': 3, 'needs_research': False, 'model': 'x'}
    monkeypatch.setattr(aa, 'ask', fake_ask)
    ctx = kc.validate_request({'message': '@technical what about the trend?', 'lang': 'en',
                               'context': {'selected_node': 'NVDA'}})['context']
    out = kc.run_chat('@technical what about the trend?', [], 'en', ctx, req_id='men-1')
    assert seen == {'seat': 'technical', 'ent': 'Nvidia', 'lang': 'en'}       # la empresa EN PANTALLA
    _check_new_fields(out)
    assert out['answer_source'] == 'agent' and out['req_id'] == 'men-1'
    assert out['agents_used'] == [{'agent': 'tecnico', 'tools': ['ask_agent'], 'ok': True,
                                   'note_es': 'Respondió con sus 3 conclusiones vigentes sobre Nvidia',
                                   'note_en': 'Answered from its 3 current conclusions on Nvidia',
                                   'source': 'Khipus research claims', 'as_of': None}]
    assert out['entities'] == [{'id': 'Nvidia', 'label': 'Nvidia'}]
    assert kc.progress_get('men-1')['agents'] == [{'agent': 'tecnico', 'tool': 'ask_agent', 'state': 'done'}]


# ════════════════════════════════════════════════════════════════════════════
# modo simple / pro y agentes activos
# ════════════════════════════════════════════════════════════════════════════
def test_modo_y_agentes_en_la_validacion():
    d = kc.validate_request({'message': 'hola'})
    assert d['context']['mode'] == 'simple' and d['context']['agents_enabled'] == list(kc.AGENT_IDS)
    assert d['req_id'] is None
    d = kc.validate_request({'message': 'hola', 'req_id': 'abc-1',
                             'context': {'mode': 'PRO', 'agents_enabled': ['comite', 'analista', 'hacker', 7]}})
    assert d['context']['mode'] == 'pro' and d['context']['agents_enabled'] == ['khipu', 'analista', 'comite']
    assert d['req_id'] == 'abc-1'
    assert kc.validate_request({'message': 'x', 'context': {'mode': 'turbo'}})['context']['mode'] == 'simple'
    assert kc.validate_request({'message': 'x', 'context': {'agents_enabled': []}})['context']['agents_enabled'] == ['khipu']


def test_modo_y_agentes_cambian_el_prompt(fake_ai):
    base = kc.build_system('es')
    assert 'MODO SIMPLE' not in base and 'MODO PRO' not in base and 'DESACTIVADOS' not in base
    simple = kc.build_system('es', 'simple', list(kc.AGENT_IDS))
    assert 'MODO SIMPLE' in simple and 'En resumen:' in simple and 'DESACTIVADOS' not in simple
    pro = kc.build_system('en', 'pro', ['khipu', 'analista', 'comite'])
    assert 'MODO PRO' in pro and 'inversionista EXPERTO' in pro and 'nunca inventes' in pro
    off = pro.split('DESACTIVADOS')[1].split('\n')[0]
    assert 'get_supply_chain' in off and 'get_news' in off and 'market_movers' in off
    assert 'get_company' not in off and 'Prioriza las herramientas de los agentes activos' in pro
    # por el endpoint: el sistema que ve la IA cambia con el contexto
    f = fake_ai([{'final': {'answer': 'ok', 'actions': []}}])
    req = kc.validate_request({'message': '¿qué es el VaR?', 'context': {'mode': 'pro', 'agents_enabled': ['analista']}})
    kc.run_chat(req['message'], [], 'es', req['context'])
    assert 'MODO PRO' in f.systems[0] and 'DESACTIVADOS' in f.systems[0]


# ════════════════════════════════════════════════════════════════════════════
# ficha y DATOS EN VIVO en paralelo
# ════════════════════════════════════════════════════════════════════════════
def test_prefetch_y_datos_en_vivo_en_paralelo(fake_ai, monkeypatch):
    from core import live_facts
    from mcp_server import tools as mt
    kc.execute_tool('get_company', {'id_or_ticker': 'Nvidia'})          # calienta el modelo de flujo (1.ª vez)

    def slow_live(text, *a, **k):
        time.sleep(1.0)
        return 'DATOS EN VIVO (prueba): Nvidia 183,25 USD'

    def slow_profile(sym):
        time.sleep(1.0)
        return dict(LIVE, symbol=sym)
    monkeypatch.setattr(live_facts, 'live_facts_block', slow_live)
    monkeypatch.setattr(mt, '_live_profile', slow_profile)
    f = fake_ai([{'final': {'answer': 'Nvidia sube.', 'actions': []}}])
    t0 = time.monotonic()
    out = kc.run_chat(Q, [], 'es', {})
    first_ai = f.times[0] - t0
    assert first_ai < 1.75, first_ai                  # en serie serían ≥ 2,0 s
    assert out['answer'] == 'Nvidia sube.'
    p = f.prompts[0]
    assert 'DATOS EN VIVO (prueba)' in p and 'get_company({"id_or_ticker": "Nvidia"})' in p and '183.25' in p
    assert out['tools_used'][0]['name'] == 'get_company' and out['cards']['company']['price'] == 183.25


# ════════════════════════════════════════════════════════════════════════════
# el analista responde en el idioma de la PETICIÓN (antes: siempre español)
# ════════════════════════════════════════════════════════════════════════════
def test_ask_agent_usa_el_idioma_de_la_peticion(monkeypatch, fake_ai):
    from research import ask_agent as aa
    monkeypatch.setattr('ontology.db.ontology_available', lambda: True)

    class _S:
        def __enter__(self):
            return None

        def __exit__(self, *a):
            return False
    monkeypatch.setattr('ontology.db.session_scope', lambda: _S())
    langs = []
    monkeypatch.setattr(aa, 'ask', lambda s, seat, q, ent, lang: (langs.append(lang) or
                                                                  {'ok': True, 'seat': seat, 'entity': 'Nvidia',
                                                                   'label': 'Nvidia', 'answer': 'ok', 'n_claims': 2}))
    monkeypatch.setattr(aa, 'ask_all', lambda s, q, ent, lang: (langs.append(('all', lang)) or
                                                                {'ok': True, 'answers': [], 'answer': 'ok'}))
    ok, res = kc.execute_tool('ask_agent', {'seat': 'technical', 'question': 'trend?', 'company': 'Nvidia'}, lang='en')
    assert ok and langs[-1] == 'en'
    # aunque el modelo mande otro idioma, manda el de la petición
    kc.execute_tool('ask_agent', {'seat': 'all', 'question': 'q', 'company': 'Nvidia', 'lang': 'es'}, lang='en')
    assert langs[-1] == ('all', 'en')
    kc.execute_tool('ask_agent', {'seat': 'news', 'question': 'q', 'company': 'Nvidia'})
    assert langs[-1] == 'es'                                                     # por defecto, español
    # por el bucle del chat en inglés
    fake_ai([{'tool': 'ask_agent', 'args': {'seat': 'technical', 'question': 'is the trend ok?', 'company': 'Nvidia'}},
             {'final': {'answer': 'The technical analyst says ok.', 'actions': []}}])
    out = kc.run_chat('ask the technical analyst about Nvidia trend', [], 'en', {})
    assert langs[-1] == 'en'
    t = next(x for x in out['tools_used'] if x['name'] == 'ask_agent')
    assert 'en' not in t['args_summary'].split(', ')
    assert any(a['agent'] == 'tecnico' and 'ask_agent' in a['tools'] for a in out['agents_used'])


# ════════════════════════════════════════════════════════════════════════════
# /api/agents/profiles
# ════════════════════════════════════════════════════════════════════════════
@pytest.fixture
def agents_client(monkeypatch):
    from core import agents_api
    agents_api.clear_cache()
    monkeypatch.setattr(agents_api, '_db_ok', lambda: False)
    app = Flask(__name__)
    app.register_blueprint(agents_api.agents_bp)
    yield app.test_client()
    agents_api.clear_cache()


def test_perfiles_sin_base_de_datos(agents_client):
    from research.context import AGENT_NEEDS
    for lang in ('es', 'en'):
        r = agents_client.get('/api/agents/profiles?lang=' + lang)
        assert r.status_code == 200
        d = r.get_json()
        assert d['db'] is False and d['lang'] == lang and d['as_of'] and d['note_es'] and d['note_en']
        assert [a['id'] for a in d['agents']] == ['khipu', 'analista', 'radar', 'cadena', 'tecnico', 'comite']
        for a in d['agents']:
            for k in ('es', 'en', 'role_es', 'role_en', 'does_es', 'does_en'):
                assert isinstance(a[k], str) and a[k].strip(), (a['id'], k)
            for k in ('data_es', 'data_en', 'outputs_es', 'outputs_en'):
                assert a[k] and all(isinstance(x, str) and x for x in a[k]), (a['id'], k)
            assert len(a['data_es']) == len(a['data_en']) and len(a['outputs_es']) == len(a['outputs_en'])
            assert a['track'] is None and a['stats_30d'] is None
            assert a['name'] == a[lang] and a['does'] == a['does_' + lang]
        by = {a['id']: a for a in d['agents']}
        assert by['analista']['windows'] == ['glance'] and by['cadena']['windows'] == ['supplychain']
        assert by['comite']['windows'] == ['conviction'] and by['radar']['windows'] == []
        assert by['analista']['research_types'] == ['fundamental', 'macro']
        assert by['tecnico']['research_types'] == ['technical', 'risk_observation']
        # "datos que usa" = lo que el armador de contexto REALMENTE trae (AGENT_NEEDS), en palabras de persona
        assert set(by['tecnico']['data_keys']) == set(AGENT_NEEDS['technical']) | set(AGENT_NEEDS['risk_observation'])
        assert any('FMP' in x for x in by['analista']['data_es']) and any('Yahoo' in x for x in by['tecnico']['data_en'])
        assert any(re.search(r'\d+ empresas', x) for x in by['cadena']['data_es'])
        assert 'get_supply_chain' in by['cadena']['tools'] and 'get_company' in by['analista']['tools']
        assert 'get_committee_memo' in by['comite']['tools'] and 'ask_agent' not in by['khipu']['tools']
        for a in d['agents']:
            assert all(kc.tool_agent(t) == a['id'] for t in a['tools'] if t != 'ask_agent')


def test_perfiles_cache_60s(agents_client, monkeypatch):
    from core import agents_api
    n = {'k': 0}
    real = agents_api.build_profiles

    def counted(lang='es'):
        n['k'] += 1
        return real(lang)
    monkeypatch.setattr(agents_api, 'build_profiles', counted)
    agents_client.get('/api/agents/profiles?lang=es')
    agents_client.get('/api/agents/profiles?lang=es')
    assert n['k'] == 1
    agents_client.get('/api/agents/profiles?lang=en')
    assert n['k'] == 2


def test_historial_agrupado_honesto():
    from core.agents_api import aggregate_track
    tr = {'agents': [{'agent_type': 'fundamental', 'n_scored': 3, 'hits': 2, 'brier': 0.2,
                      'interim': {'n_scored': 2, 'hits': 1}},
                     {'agent_type': 'macro', 'n_scored': 4, 'hits': 3, 'brier': 0.1, 'interim': {}},
                     {'agent_type': 'news', 'n_scored': 1, 'hits': 0, 'brier': 0.5, 'interim': {}}],
          'overall': {'n_scored': 8, 'hits': 5, 'brier': 0.18}, 'min_n': 5, 'benchmark': 'SPY'}
    a = aggregate_track(tr, ['fundamental', 'macro'])
    assert (a['n_scored'], a['hits'], a['sufficient']) == (7, 5, True)
    assert a['hit_rate'] == round(5 / 7, 4) and a['brier'] == round((0.2 * 3 + 0.1 * 4) / 7, 4)
    assert a['interim'] == {'n_scored': 2, 'hits': 1}
    assert a['note_es'] == 'Acertó 5 de 7 conclusiones calificadas (71 %) frente al S&P 500.'
    r = aggregate_track(tr, ['news'])
    assert r['sufficient'] is False and 'Historial corto' in r['note_es'] and 'Short record' in r['note_en']
    z = aggregate_track(tr, ['supply_chain'])
    assert z['n_scored'] == 0 and z['hit_rate'] is None and z['reliability'] == 0.5
    assert z['note_es'].startswith('Sin historial suficiente todavía')
    c = aggregate_track(tr, [], scope='overall')
    assert c['n_scored'] == 8 and c['note_es'].startswith('El comité no se califica solo')


def test_servidor_registra_perfiles_y_sincroniza_preferencias():
    src = open(os.path.join(ROOT, 'server.py'), encoding='utf-8').read()
    assert 'from core.agents_api import agents_bp' in src and 'app.register_blueprint(agents_bp)' in src
    from core.portfolio_reports_api import SYNC_KEYS
    assert 'kh_agent_prefs' in SYNC_KEYS


# ════════════════════════════════════════════════════════════════════════════
# caché de la pizarra del comité (60 s)
# ════════════════════════════════════════════════════════════════════════════
@pytest.fixture
def board_env(monkeypatch):
    from research import committee as rc
    rc.invalidate_board_cache()
    st = {'fp': ('a',), 'builds': 0, 'delay': 0.0}

    def fake_uncached(session, limit=40):
        st['builds'] += 1
        if st['delay']:
            time.sleep(st['delay'])
        return {'items': [{'entity_id': 'Nvidia', 'overall_conviction': 42.0}], 'limit': limit}
    monkeypatch.setattr(rc, '_board_uncached', fake_uncached)
    monkeypatch.setattr(rc, '_board_fingerprint', lambda s: st['fp'])
    yield rc, st
    rc.invalidate_board_cache()


def test_pizarra_cache_por_argumentos_y_huella(board_env, monkeypatch):
    rc, st = board_env
    b1 = rc.board(None, limit=40)
    b1['items'][0]['overall_conviction'] = -999            # el llamador muta su copia…
    b2 = rc.board(None, limit=40)
    assert st['builds'] == 1 and b2['items'][0]['overall_conviction'] == 42.0   # …la caché no se entera
    rc.board(None, limit=80)
    assert st['builds'] == 2                                 # otra clave
    st['fp'] = ('b',)                                        # cambió la base (conclusión o memo nuevo)
    rc.board(None, limit=40)
    assert st['builds'] == 3
    rc.invalidate_board_cache()                              # memo guardado/aprobado (_audit)
    rc.board(None, limit=40)
    assert st['builds'] == 4
    monkeypatch.setattr(rc, 'BOARD_TTL_S', -1)               # vencida
    rc.board(None, limit=40)
    assert st['builds'] == 5
    st['fp'] = None                                          # sin huella → sin caché
    monkeypatch.setattr(rc, 'BOARD_TTL_S', 60.0)
    rc.board(None, limit=40)
    rc.board(None, limit=40)
    assert st['builds'] == 7


def test_pizarra_una_sola_construccion_concurrente(board_env):
    rc, st = board_env
    st['delay'] = 0.3
    outs = []
    th = [threading.Thread(target=lambda: outs.append(rc.board(None, limit=40))) for _ in range(6)]
    for t in th:
        t.start()
    for t in th:
        t.join()
    assert st['builds'] == 1 and len(outs) == 6 and all(o['items'][0]['entity_id'] == 'Nvidia' for o in outs)


def test_audit_vacia_la_cache_de_la_pizarra(board_env):
    import types
    rc, st = board_env
    rc.board(None, limit=40)
    rc._audit(types.SimpleNamespace(audit=[], updated_at=None), 'fabrizio', 'approved')
    rc.board(None, limit=40)
    assert st['builds'] == 2
