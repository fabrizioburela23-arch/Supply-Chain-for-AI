"""tests/test_context_engine.py — EL motor de contexto (core/context_engine.py; BRECHAS bloque 4: L4-01, L4-05, L4-07,
L4-10, L4-11). Sin red, sin base: lee el grafo vigente (snapshot) y la IA es un guion falso."""
import json
import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import context_engine as ce  # noqa: E402


# ── 1. un solo detector ──────────────────────────────────────────────────────
QUESTIONS = ['¿Cómo va nvidia frente a TSMC?', 'analiza open ai', 'que tal sk hynix', 'Compare NVDA vs AMD',
             'AI chips export controls hit Microsoft (Azure) and Oracle', 'meta capex', 'riesgo de ASML en China']


def test_un_solo_detector_para_chat_mcp_investigacion_y_datos_en_vivo():
    from core import khipu_chat as kc
    from core.live_facts import detect_entities
    from core.semantic import extract_companies
    for q in QUESTIONS:
        base = ce.detect(q, limit=4)
        assert detect_entities(q, limit=4) == base, q
        assert extract_companies(q, limit=4) == (base or ce.detect(q, limit=4, resolve_short=True)), q
        assert kc._entities_in(q) == (base[:3] or ce.detect(q, limit=3, resolve_short=True)), q
    assert ce.detect('¿Cómo va nvidia frente a TSMC?')[:2] == ['Nvidia', 'TSMC']
    assert ce.detect('analiza open ai') == ['OpenAI']
    assert 'C3ai' not in ce.detect('AI chips and AI profitability')          # "AI" es una palabra, no C3.ai
    assert ce.detect('Compare NVDA vs AMD')[:2] == ['Nvidia', 'AMD']


def test_paises_y_palabras_comunes_no_son_empresas():
    """Revisión: "State Grid (China)" metía 'china' en el mapa tolerante → toda pregunta sobre China detectaba State
    Grid (y 'electron' → Rocket Lab, 'digit' → Agility) en el chat, live_facts, semantic, portfolio_ai e investigación."""
    assert ce.detect('¿Qué pasa si China bloquea Taiwán?') == []
    assert ce.detect('what if china blockades taiwan') == []
    assert ce.detect('the electron and every digit') == []
    assert ce.detect('PIF de Saudi Arabia') == []
    assert ce.detect('State Grid China') == ['StateGridChina']         # el nombre propio sigue funcionando
    assert ce.detect('Rocket Lab Electron') == ['RocketLab']
    assert 'Microsoft' in ce.detect('Microsoft (Azure)') and ce.detect('foxconn') == ['Foxconn']


def test_l405_el_recorte_no_deja_citas_a_hechos_borrados():
    """Revisión: el recorte por caracteres desde la cabeza sacaba la ficha [F1] y dejaba «ver [F1]» apuntando a nada."""
    from core import khipu_chat as kc
    f1 = '[F1] get_company({"id_or_ticker": "TSMC"}) → ' + 'a' * 9000
    old = '[F2] get_supply_chain({"id": "TSMC"}) → ' + 'b' * 9000
    mid = '[F3] get_supply_chain({"id": "Samsung"}) → ' + 'c' * 9000
    ref = 'get_company({"id_or_ticker": "TSMC"}) → ya consultado arriba: ver [F1] (mismo resultado)'
    txt = kc._trim_scratch([f1, old, mid, '[4] ' + ref], 20000)
    assert '[F1] get_company' in txt and 'ver [F1]' in txt and '[F2]' not in txt and len(txt) <= 20000 + 40
    # si ni lo citado entra, sale también y la cita deja de decir «ver arriba»
    txt = kc._trim_scratch([f1, mid, '[3] ' + ref], 5000)
    assert '[F1] get_company' not in txt and 'ver [F1]' not in txt and 'recortado por espacio' in txt
    assert kc._trim_scratch(['[1] x', '[2] y'], 100) == '[1] x\n[2] y'      # bajo el tope: intacto


def test_detector_se_rearma_por_generacion_del_grafo(monkeypatch):
    from core import entities
    idx = dict(entities.get_index())
    nodos = dict(idx['nodos'])
    nodos['ZetaQuantumWidgets'] = {'id': 'ZetaQuantumWidgets', 'label': 'Zeta Quantum Widgets'}
    idx.update(nodos=nodos, generation='gen-de-prueba')
    monkeypatch.setattr(entities, 'get_index', lambda *a, **k: idx)
    assert ce.detect('¿qué hace Zeta Quantum Widgets?') == ['ZetaQuantumWidgets']    # antes: regex de por vida


def test_intencion():
    assert ce.intent('¿Qué pasa si China bloquea Taiwán?') == 'impact'
    assert ce.intent('¿Quiénes son los proveedores de Apple?') == 'upstream'
    assert ce.intent('¿a quién le vende TSMC?') == 'downstream'
    assert ce.intent('háblame de Nvidia') == 'general'


# ── 2. relevancia ────────────────────────────────────────────────────────────
def test_relevancia_acotada_determinista_y_semillas_en_1():
    R1, info = ce.relevance(['Nvidia'], '¿cadena de Nvidia?')
    R2, _ = ce.relevance(['Nvidia'], '¿cadena de Nvidia?')
    assert R1 == R2 and R1['Nvidia'] == 1.0 and info['intent'] == 'general'
    assert all(0.0 <= v <= 1.0 for v in R1.values())
    # proveedores directos importantes de Nvidia > una empresa lejana cualquiera
    assert R1.get('TSMC', 0) > R1.get('Codelco', 0)
    # preguntas de impacto: Ψ del kernel (las víctimas del colapso de TSMC suben)
    Ri, info_i = ce.relevance(['TSMC'], '¿qué pasa si cae TSMC?')
    assert info_i['intent'] == 'impact' and Ri.get('Nvidia', 0) >= 0.25


def test_empaquetado_cobertura_ponderada_y_mejor_elemento():
    items = [{'key': 'a', 'R': 1.0, 'cost': 10, 'groups': [('g', 1.0)]},
             {'key': 'b', 'R': 0.99, 'cost': 10, 'groups': [('g', 1.0)]},     # casi igual a 'a': no suma
             {'key': 'c', 'R': 0.5, 'cost': 10, 'groups': []}]
    chosen, omitted = ce.pack(items, 20)
    assert [x['key'] for x in chosen] == ['a', 'c'] and [x['key'] for x in omitted] == ['b']
    # mochila: un solo elemento grande y valioso le gana a varios chicos sin valor
    items = [{'key': 'big', 'R': 10.0, 'cost': 100, 'groups': []}] + \
            [{'key': f's{i}', 'R': 0.5, 'cost': 1, 'groups': []} for i in range(5)]
    chosen, _ = ce.pack(items, 100)
    assert [x['key'] for x in chosen] == ['big']


# ── 3. subgrafo por relevancia ───────────────────────────────────────────────
def _flow_types():
    from ontology.vocabulary import flow_relation_types
    return set(flow_relation_types())


def test_subgrafo_solo_flujo_dos_lados_dos_saltos_cola_y_presupuesto():
    sg = ce.subgraph(['Nvidia'], '¿cómo es la cadena completa de Nvidia?', depth=2, budget_chars=6000)
    flow = _flow_types()
    assert sg['seeds'] == ['Nvidia'] and sg['edges']
    assert all(e['type'] in flow for e in sg['edges'])                       # socios/inversores: solo en related
    assert all(e['type'] not in flow for e in sg['related'])
    ups = [e for e in sg['edges'] if e['target'] == 'Nvidia']
    downs = [e for e in sg['edges'] if e['source'] == 'Nvidia']
    assert len(ups) >= 3 and len(downs) >= 3                                  # los dos lados
    assert any(e['hop'] == 2 for e in sg['edges'])                           # también el 2.º nivel
    # coherencia: toda arista de 2.º salto cuelga de un nodo unido por una arista elegida
    joined = {'Nvidia'} | {e['source'] for e in sg['edges'] if e['hop'] == 1} | {e['target'] for e in sg['edges'] if e['hop'] == 1}
    for e in sg['edges']:
        if e['hop'] == 2:
            assert (e['target'] if e['direction'] == 'up' else e['source']) in joined, e
    # cola: lo que no entró se cuenta (pares distintos) y se resume
    assert sg['tail']['omitted_edges'] > 0 and sg['tail']['top_countries_by_weight']
    edges_chars = len(json.dumps(sg['edges'], ensure_ascii=False, separators=(',', ':')))
    assert edges_chars <= 6000
    # orden por relevancia, determinista
    rs = [e['r'] for e in sg['edges']]
    assert rs == sorted(rs, reverse=True)
    assert ce.subgraph(['Nvidia'], '¿cómo es la cadena completa de Nvidia?', depth=2, budget_chars=6000)['edges'] == sg['edges']
    # una contraparte = una fila (el par TSMC→Nvidia tiene fab y supply)
    pairs = [(e['source'], e['target']) for e in sg['edges']]
    assert len(pairs) == len(set(pairs))
    tsmc = [e for e in sg['edges'] if e['source'] == 'TSMC' and e['target'] == 'Nvidia']
    assert tsmc and tsmc[0]['w'] == max(l['w'] for l in ce.flow()[0].inn['Nvidia'] if l['source'] == 'TSMC')


def test_subgrafo_intencion_proveedores_prioriza_aguas_arriba():
    sg = ce.subgraph(['Apple'], '¿quiénes son los proveedores de Apple?', depth=1, budget_chars=2500)
    ups = sum(1 for e in sg['edges'] if e['target'] == 'Apple')
    downs = sum(1 for e in sg['edges'] if e['source'] == 'Apple')
    assert sg['intent'] == 'upstream' and ups >= downs


def test_pack_supply_chain_respeta_totales_y_raiz():
    from mcp_server import tools as T
    from mcp_server.auth import Principal
    ctx = T.Ctx(principal=Principal(token_id='x', name='t', scopes=frozenset({'read'})))
    r = T.call('get_supply_chain', {'id': 'Nvidia', 'depth': 2}, ctx)
    p = ce.pack_supply_chain(r, '¿cadena completa?', budget_chars=4000)
    assert p['counts'] == r['counts'] and p['root'] == 'Nvidia' and p['truncated'] is True
    ids = {n['id'] for n in p['nodes']}
    assert 'Nvidia' in ids and all(e['source'] in ids and e['target'] in ids for e in p['edges'])
    assert p['tail']['omitted_edges'] + len(p['edges']) <= len(r['edges'])
    assert any(e['hop'] == 2 for e in p['edges'])


def test_hechos_con_id_fuente_y_as_of():
    fb = ce.FactBook()
    f1 = fb.add('get_company', 'Nvidia', 'Yahoo', '2026-10-13', key='k1')
    assert f1 == 'F1' and fb.add('get_company', 'Nvidia', key='k1') == 'F1' and fb.get('k1') == 'F1'
    assert fb.add('get_news', 'TSMC') == 'F2'
    assert fb.public()[0] == {'id': 'F1', 'kind': 'get_company', 'entity': 'Nvidia', 'source': 'Yahoo',
                              'as_of': '2026-10-13'}
    assert ce.result_source({'source': 'X', 'as_of': 'T'}) == ('X', 'T')


# ── 4. el chat usa el motor ──────────────────────────────────────────────────
class FakeAI:
    def __init__(self, script, by_tier=False):
        self.script, self.prompts, self.tiers = list(script), [], []

    def __call__(self, system, prompt, max_tokens=1000, tier='fast', model=None, verify_numbers=True, **kw):
        self.prompts.append(prompt)
        self.tiers.append(tier)
        item = self.script.pop(0) if self.script else {'final': {'answer': 'ok final de prueba', 'actions': []}}
        if isinstance(item, Exception):
            raise item
        return (item if isinstance(item, str) else json.dumps(item)), f'fake:{tier}'


@pytest.fixture
def offline(monkeypatch):
    from core import ai as core_ai
    from mcp_server import tools as mt
    monkeypatch.setattr(mt, '_live_profile', lambda sym: {'available': False, 'reason': 'test (offline)'})
    monkeypatch.setattr(mt._auth, 'db_available', lambda: False)
    monkeypatch.setattr('core.live_facts.live_facts_block', lambda m: '')
    monkeypatch.setattr(core_ai, '_ai_configured', lambda: True)
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    monkeypatch.delenv('TYPESAFE_KEY', raising=False)
    return core_ai


def test_l405_la_ficha_preconsultada_no_se_pega_dos_veces(offline, monkeypatch):
    from core import khipu_chat as kc
    f = FakeAI([{'tool': 'get_company', 'args': {'id_or_ticker': 'nvidia'}},
                {'final': {'answer': 'Nvidia va bien según la ficha.', 'actions': []}}])
    monkeypatch.setattr(offline, '_ai_complete', f)
    out = kc.run_chat('¿Cómo va Nvidia?', [], 'es', {})
    last = f.prompts[-1]
    assert last.count('"top_suppliers"') == 1                     # antes: 2 (≈49 % del prompt repetido)
    assert 'ya consultado arriba: ver [F1]' in last and '[F1] get_company' in last
    assert len(last) <= len(f.prompts[0]) + 600
    # los hechos [F#] vuelven en la respuesta con su fuente (los registra la ficha chat.answer)
    assert out['facts'] and out['facts'][0]['id'] == 'F1' and out['facts'][0]['entity'] == 'Nvidia'
    assert out['facts'][0].get('source')


def test_l405_clave_canonica_de_la_cache():
    from core import khipu_chat as kc
    a = kc._cache_key('get_company', {'id_or_ticker': 'nvidia'})
    assert a == kc._cache_key('get_company', {'id_or_ticker': 'NVDA', 'include_live': True})
    assert a == kc._cache_key('get_company', {'id_or_ticker': 'Nvidia', 'detail': 'summary'})
    assert a != kc._cache_key('get_company', {'id_or_ticker': 'Nvidia', 'include_live': False})


def test_l410_cadena_a_dos_saltos_en_el_chat(offline, monkeypatch):
    from core import khipu_chat as kc
    f = FakeAI([{'tool': 'get_supply_chain', 'args': {'id': 'Nvidia', 'depth': 2}},
                {'final': {'answer': 'La cadena de Nvidia depende de TSMC.', 'actions': []}}])
    monkeypatch.setattr(offline, '_ai_complete', f)
    kc.run_chat('¿Cuál es la cadena completa de Nvidia a dos niveles?', [], 'es', {})
    block = f.prompts[-1].split('get_supply_chain(', 1)[1]
    d = json.loads(block.split(') → ', 1)[1].split('\n\n', 1)[0])
    edges = [e for e in d['edges'] if isinstance(e, dict)]
    assert any(e.get('hop') == 2 for e in edges)                 # antes: 12 aristas, todas de 1 salto
    assert d['tail']['omitted_edges'] > 0 and d['counts']['edges'] > len(edges)        # el total real sigue a la vista


def test_l407_analisis_el_rapido_solo_junta_y_el_profundo_escribe(offline, monkeypatch):
    from core import decide
    from core import khipu_chat as kc
    monkeypatch.setenv('TYPESAFE_API_KEY', 'ts-test')
    monkeypatch.delenv('DECIDE_CONTROL', raising=False)
    monkeypatch.setattr(decide, '_persist', lambda row: None)
    ans = {'route': {'choice': 'needs_deep_reasoning',
                     'probabilities': {'needs_deep_reasoning': 0.9, 'needs_tools': 0.05, 'local_fact': 0.05}},
           'about_portfolio': {'score': 0.0}, 'trade_intent': {'score': 0.0}}
    monkeypatch.setattr(decide, 'ask', lambda state, q, feature=None, timeout=None: ans)
    # el profundo falla → la redacción de respaldo es del rápido (nunca "LISTO" como respuesta)
    f = FakeAI([{'final': {'answer': 'LISTO', 'actions': []}}, 'no es json {', 'no es json {'])
    monkeypatch.setattr(offline, '_ai_complete', f)
    seen = []

    def fake_synth(message, history, lang, context, scratch, timeout, tier='fast'):
        seen.append(tier)
        return 'Redacción de respaldo con los datos consultados.', f'fake:{tier}'
    monkeypatch.setattr(kc, 'synthesize', fake_synth)
    out = kc.run_chat('¿cuál es la tesis de Nvidia a 3 años?', [], 'es', {})
    assert kc.DEEP_GATHER_NOTE in f.prompts[0]                  # el rápido no redacta: solo junta datos
    assert out['answer'] != 'LISTO' and out['answer'].startswith('Redacción de respaldo')
    assert seen == ['fast']                                      # no se vuelve a intentar el profundo
    assert kc.is_ready_marker('Listo.') and not kc.is_ready_marker('Listo: Nvidia sube 3 %')


# ── 5. investigación: subgrafo del motor + pool de evidencia ─────────────────
def test_investigacion_usa_el_motor_y_dice_lo_que_quedo_afuera():
    from research.context import ContextBuilder
    sub = ContextBuilder().subgraph('TSMC', max_nodes=6, max_depth=1, rel_types=_flow_types())
    assert len(sub['nodes']) <= 6 and sub['tail']['omitted_edges'] > 0
    assert all(e['type'] in _flow_types() for e in sub['edges'])
    from tests.test_research import FETCH
    ctx = ContextBuilder(fetchers=FETCH).build('Nvidia', 'supply_chain', depth='STANDARD')
    g = [e for e in ctx['evidence'] if e['source_type'] == 'graph'][0]
    assert 'vínculos fuera de este resumen' in g['excerpt'] and len(g['excerpt']) > 700


def test_l411_pool_de_evidencia_un_pedido_por_fuente_y_job():
    from research.context import pooled_fetchers
    calls = {'n': 0, 'fail': 0}
    lock = threading.Lock()

    def news(label, limit):
        with lock:
            calls['n'] += 1
        time.sleep(0.05)
        return [{'title': 't', 'url': 'https://x'}]

    def flaky(sym):
        calls['fail'] += 1
        raise RuntimeError('caída')
    pool = pooled_fetchers({'news': news, 'profile': flaky})
    res = []
    th = [threading.Thread(target=lambda: res.append(pool['news']('Nvidia', 8))) for _ in range(8)]
    [t.start() for t in th]
    [t.join() for t in th]
    assert calls['n'] == 1 and len(res) == 8 and all(r == res[0] for r in res)
    assert pool['news']('TSMC', 8) and calls['n'] == 2               # otra empresa: otro pedido
    for _ in range(2):
        with pytest.raises(RuntimeError):
            pool['profile']('NVDA')
    assert calls['fail'] == 2                                         # un fallo no se memoriza
