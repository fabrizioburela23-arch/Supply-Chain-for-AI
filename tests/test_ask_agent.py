"""Preguntarle a un analista dentro de la conversación (research/ask_agent + ruta @ en el chat)."""
import types

import pytest

from research import agent_skills as sk
from research import ask_agent as aa


@pytest.fixture(autouse=True)
def _sin_red(monkeypatch):
    """Las habilidades de los agentes salen a la red (tensor, World Monitor, Yahoo): en estas pruebas, vacías."""
    monkeypatch.setattr(sk, 'skill_packet', lambda seat, eid: {'text': '', 'facts': {}, 'sources': [], 'n_evidence': 0,
                                                               'ok': False, 'listed': True})


def test_parse_mention_formas():
    assert aa.parse_mention('@fundamental ¿qué opinas de TSMC?') == ('fundamental', '¿qué opinas de TSMC?')
    assert aa.parse_mention('@analista de noticias: qué pasó con Nvidia') == ('news', 'qué pasó con Nvidia')
    assert aa.parse_mention('@todos qué piensan de Micron') == ('all', 'qué piensan de Micron')
    assert aa.parse_mention('pregúntale al analista técnico: ¿Nvidia está cara?') == ('technical', '¿Nvidia está cara?')
    assert aa.parse_mention('pregúntale al analista de cadena qué pasa con SK Hynix')[0] == 'supply_chain'
    assert aa.parse_mention('¿quién fabrica para Nvidia?') == (None, '¿quién fabrica para Nvidia?')
    assert aa.parse_mention('@desconocido hola')[0] is None


def _claim(i, seat='fundamental', stance='positive'):
    return types.SimpleNamespace(id=f'c{i}', agent_type=seat, stance=stance, horizon='MEDIUM_TERM', confidence=0.6,
                                 statement_es=f'Conclusión {i} sobre márgenes.', reasoning_summary='porque sí',
                                 falsifiers=['margen < 60%'], valid_to=None, created_at=None, status='active',
                                 subject_entity_id='Nvidia')


def test_ask_responde_en_persona_con_refs(monkeypatch):
    monkeypatch.setattr(aa, '_resolve', lambda e: ('Nvidia', 'Nvidia', 'NVDA'))
    monkeypatch.setattr(aa, '_load_claims', lambda s, eid, seat: [_claim(1), _claim(2)])
    monkeypatch.setattr(aa, '_evidence', lambda s, ids: {'c1': [{'title': 'Reporte anual', 'excerpt': 'margen bruto 74%', 'type': 'filing', 'date': '2026-02-01'}]})
    seen = {}

    def fake_ai(system, prompt, max_tokens, tier):
        seen['system'], seen['prompt'] = system, prompt
        return 'Según mis conclusiones [C1] y la evidencia [C1.1], los márgenes son sólidos. Vigilaría el margen bruto.', 'gemini:x'
    r = aa.ask(None, 'fundamental', '¿los márgenes aguantan?', 'Nvidia', 'es', ai=fake_ai)
    assert r['ok'] and r['seat'] == 'fundamental' and r['name'] == 'Analista fundamental' and r['n_claims'] == 2
    assert r['refs'] == {'C1': 'c1'} and 'Analista fundamental' in seen['system']
    assert 'C1 [' in seen['prompt'] and 'evidencia C1.1' in seen['prompt'] and '¿los márgenes aguantan?' in seen['prompt']
    assert r['needs_research'] is False


def test_ask_sin_conclusiones_ofrece_investigar(monkeypatch):
    monkeypatch.setattr(aa, '_resolve', lambda e: ('Micron', 'Micron', 'MU'))
    monkeypatch.setattr(aa, '_load_claims', lambda s, eid, seat: [])
    r = aa.ask(None, 'news', 'qué pasó', 'Micron', 'es', ai=lambda *a: ('no', 'x'))
    assert r['needs_research'] and 'investigue' in r['answer'].lower()


def test_ask_entidad_desconocida():
    def boom(e):
        raise ValueError('entidad desconocida')
    import pytest
    orig = aa._resolve
    aa._resolve = boom
    try:
        r = aa.ask(None, 'news', 'q', 'Empresa Inexistente XYZ', 'es', ai=lambda *a: ('', ''))
    finally:
        aa._resolve = orig
    assert r['ok'] is False and 'No encontré' in r['answer']


def test_ask_all_combina(monkeypatch):
    monkeypatch.setattr(aa, '_resolve', lambda e: ('Nvidia', 'Nvidia', 'NVDA'))
    monkeypatch.setattr(aa, 'seats_with_claims', lambda s, eid: ['fundamental', 'news'])
    monkeypatch.setattr(aa, '_load_claims', lambda s, eid, seat: [_claim(1, seat)])
    monkeypatch.setattr(aa, '_evidence', lambda s, ids: {})
    r = aa.ask_all(None, '¿qué opinan?', 'Nvidia', 'es', ai=lambda sy, pr, mt, ti: ('Opino que bien [C1].', 'm'))
    assert len(r['answers']) == 2 and '📊 Analista fundamental' in r['answer'] and '📰 Analista de noticias' in r['answer']


def test_ruta_arroba_en_el_chat(monkeypatch):
    from core import khipu_chat as kc
    monkeypatch.setattr('ontology.db.ontology_available', lambda: True)

    class _S:
        def __enter__(self): return None
        def __exit__(self, *a): return False
    monkeypatch.setattr('ontology.db.session_scope', lambda: _S())
    monkeypatch.setattr(aa, 'ask', lambda s, seat, q, ent, lang, **k: {'ok': True, 'seat': seat, 'emoji': '📊', 'name': 'Analista fundamental',
                                                                   'entity': ent, 'label': ent, 'answer': 'Mi respuesta [C1].', 'refs': {'C1': 'c1'},
                                                                   'n_claims': 3, 'needs_research': False, 'model': 'gemini:x'})
    out = kc.run_chat('@fundamental ¿qué opinas de Nvidia?', [], 'es', {})
    assert out['answer'] == 'Mi respuesta [C1].' and out['agent']['seat'] == 'fundamental' and out['answer_source'] == 'agent'
    # sin empresa en el mensaje: la toma de la conversación previa
    out2 = kc.run_chat('@fundamental ¿y los márgenes?', [{'role': 'user', 'content': 'háblame de Nvidia'}], 'es', {})
    assert out2['agent'].get('entity') == 'Nvidia'
    # sin empresa en ningún lado → pregunta cuál
    out3 = kc.run_chat('@fundamental ¿y los márgenes?', [], 'es', {})
    assert 'empresa' in out3['answer'].lower()


# ── HABILIDADES PROPIAS de cada agente (2026-10-06) ─────────────────────────────────────────────
_PKT = {'text': 'S1 <data>Concentración de proveedores: Microsoft (Azure) 17,2 % del peso</data>\n'
                'S2 <data>Países de sus proveedores: EEUU 100,0 %</data>',
        'facts': {'top_suppliers': [{'id': 'Microsoft', 'label': 'Microsoft (Azure)', 'share_pct': 17.2}],
                  'risk_sources': [{'id': 'Oracle', 'label': 'Oracle (OCI)', 'pct': 18.1, 'direct': True}]},
        'sources': [{'label': 'Tensor de la cadena Khipus', 'as_of': '2026-10-06T00:00:00Z'}],
        'n_evidence': 2, 'ok': True, 'listed': False}


def test_cadena_responde_desde_su_rol_sin_investigacion_previa(monkeypatch):
    monkeypatch.setattr(aa, '_resolve', lambda e: ('OpenAI', 'OpenAI', None))
    monkeypatch.setattr(aa, '_load_claims', lambda s, eid, seat: [])
    asked = {}

    def pkt(seat, eid):
        asked['seat'], asked['eid'] = seat, eid
        return dict(_PKT)
    monkeypatch.setattr(sk, 'skill_packet', pkt)
    seen = {}

    def fake_ai(system, prompt, max_tokens, tier):
        seen['system'], seen['prompt'] = system, prompt
        return 'OpenAI depende sobre todo de Microsoft [S1].', 'gemini:x'
    r = aa.ask(None, 'supply_chain', 'analiza open ai', 'OpenAI', 'es', ai=fake_ai)
    assert asked == {'seat': 'supply_chain', 'eid': 'OpenAI'}
    assert r['ok'] and r['answer'].startswith('OpenAI depende') and r['needs_research'] is True
    # su enfoque y SUS datos van al modelo; no un análisis general
    assert 'CADENA DE SUMINISTRO' in seen['system'] and 'quédate en tu rol' in seen['system']
    assert 'S1 <data>Concentración' in seen['prompt'] and 'analiza open ai' in seen['prompt']
    # la ventana de su rol y una nota determinista con sus datos
    assert r['skill']['actions'] == [{'type': 'open_window', 'arg': {'kind': 'supplychain', 'id': 'OpenAI'}}]
    assert 'Microsoft (Azure)' in r['skill']['note_es'] and '17,2 %' in r['skill']['note_es']
    assert '17.2%' in r['skill']['note_en']


def test_sin_ia_devuelve_sus_datos_tal_cual(monkeypatch):
    monkeypatch.setattr(aa, '_resolve', lambda e: ('OpenAI', 'OpenAI', None))
    monkeypatch.setattr(aa, '_load_claims', lambda s, eid, seat: [])
    monkeypatch.setattr(sk, 'skill_packet', lambda seat, eid: dict(_PKT))

    def busy(*a):
        raise RuntimeError('AIBusy')
    r = aa.ask(None, 'supply_chain', '?', 'OpenAI', 'es', ai=busy)
    assert r['ok'] and r['model'] is None and 'IA está ocupada' in r['answer']
    assert '· Concentración de proveedores: Microsoft (Azure) 17,2 % del peso' in r['answer']
    assert '<data>' not in r['answer']


def test_cada_rol_tiene_su_enfoque_y_su_ventana():
    for seat in ('supply_chain', 'fundamental', 'technical', 'news', 'geopolitical', 'macro', 'crypto'):
        es, en = sk.FOCUS[seat]
        assert es and en and es != en
    assert sk.role_actions('technical', 'Nvidia', 'Nvidia', True) == [{'type': 'chart', 'arg': 'precio de Nvidia 1 año'}]
    assert sk.role_actions('technical', 'OpenAI', 'OpenAI', False) == []
    assert sk.role_actions('fundamental', 'Nvidia', 'Nvidia', True)[0] == {'type': 'open_window', 'arg': {'kind': 'glance', 'id': 'Nvidia'}}
    assert sk.EXTRAS['supply_chain'] is sk._supply_extras


def test_skill_packet_une_evidencia_y_habilidades(monkeypatch):
    monkeypatch.undo()          # el fixture de arriba vacía skill_packet: aquí se prueba el de verdad
    monkeypatch.setattr(sk, '_context', lambda eid, seat: {'entity': {'mkt': None}, 'evidence': [
        {'ref': 'E1', 'source_type': 'graph', 'title': 'Relaciones', 'excerpt': 'x', 'published_at': None, 'retrieved_at': 'hoy'}]})
    monkeypatch.setattr('research.context.render_context', lambda ctx: 'E1 [graph] Relaciones')
    monkeypatch.setitem(sk.EXTRAS, 'supply_chain', lambda eid: (['línea A', 'línea B'], {'n_suppliers': 3}, [{'label': 'Tensor', 'as_of': None}]))
    p = sk.skill_packet('supply_chain', 'OpenAI')
    assert p['ok'] and p['n_evidence'] == 3 and p['facts'] == {'n_suppliers': 3} and p['listed'] is False
    assert 'E1 [graph]' in p['text'] and 'S1 <data>línea A</data>' in p['text'] and 'S2 <data>línea B</data>' in p['text']
    assert [x['label'] for x in p['sources']] == ['Tensor', 'Relaciones']


def test_skill_packet_nunca_lanza(monkeypatch):
    monkeypatch.undo()

    def boom(*a):
        raise RuntimeError('x')
    monkeypatch.setattr(sk, '_context', boom)
    monkeypatch.setitem(sk.EXTRAS, 'supply_chain', boom)
    p = sk.skill_packet('supply_chain', 'OpenAI')
    assert p['ok'] is False and p['n_evidence'] == 0


def test_ask_all_sin_conclusiones_responden_con_habilidades(monkeypatch):
    monkeypatch.setattr(aa, '_resolve', lambda e: ('Nvidia', 'Nvidia', 'NVDA'))
    monkeypatch.setattr(aa, 'seats_with_claims', lambda s, eid: [])
    monkeypatch.setattr(sk, 'skill_packet', lambda seat, eid: dict(_PKT))
    r = aa.ask_all(None, '¿qué opinan?', 'Nvidia', 'es', ai=lambda sy, pr, mt, ti: ('Mi lectura [S1].', 'm'))
    assert r['ok'] and [a['seat'] for a in r['answers']] == list(aa.ALL_DEFAULT) and r['model'] == 'm'


def test_ruta_arroba_sin_base_usa_habilidades_y_abre_la_ventana_del_rol(monkeypatch):
    from core import khipu_chat as kc
    monkeypatch.setattr('ontology.db.ontology_available', lambda: False)
    got = {}

    def fake_ask(s, seat, q, ent, lang, **k):
        got.update(session=s, seat=seat, ent=ent)
        return {'ok': True, 'seat': seat, 'emoji': '⛓', 'name': 'Analista de cadena', 'entity': 'OpenAI', 'label': 'OpenAI',
                'answer': 'Depende de Microsoft [S1].', 'refs': {}, 'n_claims': 0, 'needs_research': True, 'model': 'gemini:x',
                'skill': {'facts': {}, 'sources': [{'label': 'Tensor de la cadena Khipus', 'as_of': '2026-10-06T00:00:00Z'}],
                          'n_evidence': 2, 'actions': [{'type': 'open_window', 'arg': {'kind': 'supplychain', 'id': 'OpenAI'}}],
                          'note_es': 'OpenAI depende sobre todo de Microsoft', 'note_en': 'OpenAI depends most on Microsoft'}}
    monkeypatch.setattr(aa, 'ask', fake_ask)
    out = kc.run_chat('@cadena analiza open ai', [], 'es', {})
    assert got == {'session': None, 'seat': 'supply_chain', 'ent': 'OpenAI'}     # "open ai" (minúsculas, con espacio)
    assert out['answer'] == 'Depende de Microsoft [S1].' and out['answer_source'] == 'agent'
    assert out['actions'][0] == {'type': 'open_window', 'arg': {'kind': 'supplychain', 'id': 'OpenAI'}, 'label': 'OpenAI'}
    assert out['actions'][1]['type'] == 'open_research'
    assert out['sources'][0]['label'].startswith('Tensor')
    ag = out['agents_used'][0]
    assert ag['agent'] == 'cadena' and ag['note_es'] == 'OpenAI depende sobre todo de Microsoft'


def test_validate_actions_open_window():
    from core.khipu_chat import validate_actions
    ok = validate_actions([{'type': 'open_window', 'arg': {'kind': 'supplychain', 'id': 'nvidia'}}])
    assert ok and ok[0]['arg'] == {'kind': 'supplychain', 'id': 'Nvidia'}
    assert validate_actions([{'type': 'open_window', 'arg': {'kind': 'broker', 'id': 'Nvidia'}}]) == []
    assert validate_actions([{'type': 'open_window', 'arg': {'kind': 'glance', 'id': 'no existe xyz'}}]) == []
    assert validate_actions([{'type': 'open_window', 'arg': 'Nvidia'}]) == []


def test_detecta_empresas_escritas_en_minusculas_o_separadas():
    """"analiza open ai" no encontraba a OpenAI (por eso Cadena terminaba en la investigación general)."""
    from core.live_facts import detect_entities
    ids = lambda t: [e if isinstance(e, str) else e.get('id') for e in detect_entities(t)]
    assert 'OpenAI' in ids('Analiza open ai')
    assert 'Nvidia' in ids('que tal nvidia')
    assert 'SKHynix' in ids('y sk hynix?')
    assert {'TSMC', 'ASML'} <= set(ids('tsmc y asml'))
    for t in ('la meta del año', 'vale la pena', 'una disco'):
        assert ids(t) == [], t


def test_perfiles_muestran_las_habilidades_y_coinciden_con_el_cliente():
    import os
    import re
    from core.agents_api import build_profiles
    out = build_profiles('es')
    by = {a['id']: a for a in out['agents']}
    assert by['cadena']['skills'] == sk.SKILLS['cadena'][0] and by['cadena']['skills_en'] == sk.SKILLS['cadena'][1]
    assert by['khipu']['skills'] == [] and by['comite']['skills'] == []
    js = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine', 'oswindows.js'), encoding='utf-8').read()
    for mid, (es, en) in sk.SKILLS.items():          # el respaldo estático del cliente dice lo mismo
        for txt in es + en:
            assert txt in js, (mid, txt)
    assert re.search(r"Habilidades cuando le hablas', 'Skills when you talk to it'", js)
