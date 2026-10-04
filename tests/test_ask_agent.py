"""Preguntarle a un analista dentro de la conversación (research/ask_agent + ruta @ en el chat)."""
import types

from research import ask_agent as aa


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
        return 'Según mis conclusiones [C1] y la evidencia [E1.1], los márgenes son sólidos. Vigilaría el margen bruto.', 'gemini:x'
    r = aa.ask(None, 'fundamental', '¿los márgenes aguantan?', 'Nvidia', 'es', ai=fake_ai)
    assert r['ok'] and r['seat'] == 'fundamental' and r['name'] == 'Analista fundamental' and r['n_claims'] == 2
    assert r['refs'] == {'C1': 'c1'} and 'Analista fundamental' in seen['system']
    assert 'C1 [' in seen['prompt'] and 'evidencia E1.1' in seen['prompt'] and '¿los márgenes aguantan?' in seen['prompt']
    assert r['needs_research'] is False


def test_ask_sin_conclusiones_ofrece_investigar(monkeypatch):
    monkeypatch.setattr(aa, '_resolve', lambda e: ('Micron', 'Micron', 'MU'))
    monkeypatch.setattr(aa, '_load_claims', lambda s, eid, seat: [])
    r = aa.ask(None, 'news', 'qué pasó', 'Micron', 'es', ai=lambda *a: ('no', 'x'))
    assert r['needs_research'] and 'no investigué' in r['answer'].lower() or 'Todavía no investigué' in r['answer']


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
    monkeypatch.setattr(aa, 'ask', lambda s, seat, q, ent, lang: {'ok': True, 'seat': seat, 'emoji': '📊', 'name': 'Analista fundamental',
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
