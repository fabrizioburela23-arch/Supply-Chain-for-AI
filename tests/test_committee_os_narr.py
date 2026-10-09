"""tests/test_committee_os_narr.py — la sala del comité habla con la voz de Khipus OS (2026-10-09).

Pedido de Fabrizio: "el comité todavía no está actualizado". Al encargar la investigación, el presidente
nombra a los analistas por su MASCOTA (Analista, Radar, Cadena, Técnico) y cada uno dice lo que de verdad hace
(research/agent_skills.WORKING, coherente con FOCUS) — antes todos repetían "Investigando: leyendo estados
financieros, noticias y datos en vivo…". Si la empresa no cotiza, el Técnico lo dice en su voz en vez de un
error técnico. Sin red; el test de punta a punta con la base se salta sin DATABASE_URL.
"""
import os
import re
import sys
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')

OLD_LINE = 'Investigando: leyendo estados financieros, noticias y datos en vivo…'


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


def _drive(monkeypatch, eid, agents, runs, index=None):
    """Corre _auto_research con create_job/execute_job falsos. runs = {agent_type: run}; devuelve los mensajes."""
    from research import committee as cm
    from research import runner
    said = []
    calls = {}

    def fake_create(session, entity_id, **kw):
        calls['create'] = (entity_id, kw)
        return SimpleNamespace(agents=list(agents), entity_id=entity_id), False

    def fake_exec(session, job, provider_factory=None, fetchers=None, on_start=None, on_done=None):
        for a in job.agents:
            on_start(a)
        for a in job.agents:
            on_done(a, runs[a])
        return job

    monkeypatch.setattr(runner, 'create_job', fake_create)
    monkeypatch.setattr(runner, 'execute_job', fake_exec)
    if index is not None:
        import core.entities as ents
        monkeypatch.setattr(ents, 'get_index', lambda: {'nodos': index})
    cm._auto_research(None, eid, eid, 'pytest', lambda *m: said.extend(x for x in m if x), {}, agents=None)
    return said, calls


def _ok(n=2):
    return SimpleNamespace(status='done', claims_generated=n, errors=[])


def _fail(err):
    return SimpleNamespace(status='failed', claims_generated=0, errors=[err])


# ════════════════════════════════════════════════════════════════════════════
# 1 · cada analista dice lo que hace (bilingüe, distinto por rol)
# ════════════════════════════════════════════════════════════════════════════

def test_working_cubre_todos_los_analistas_y_es_bilingue():
    from research.agent_skills import WORKING, working_line
    from research.agents.registry import AGENTS_BY_TYPE
    assert set(AGENTS_BY_TYPE) <= set(WORKING)                    # todo agente de investigación tiene su frase
    es_all = [WORKING[a][0] for a in AGENTS_BY_TYPE]
    en_all = [WORKING[a][1] for a in AGENTS_BY_TYPE]
    assert len(set(es_all)) == len(es_all) and len(set(en_all)) == len(en_all)
    for a in AGENTS_BY_TYPE:
        es, en = working_line(a)
        assert es and en and es != en and OLD_LINE not in (es, en)
    assert working_line('nada_raro')[0] and working_line('nada_raro')[1]   # respaldo, nunca vacío


def test_working_coincide_con_el_enfoque_de_cada_rol():
    from research.agent_skills import WORKING
    f_es, f_en = WORKING['fundamental']
    assert all(w in f_es for w in ('estados financieros', 'márgenes', 'caja', 'deuda', 'pares'))
    assert all(w in f_en for w in ('financial statements', 'margins', 'cash', 'debt', 'peers'))
    n_es, n_en = WORKING['news']
    assert 'fecha' in n_es and 'fuente' in n_es and 'rumores' in n_es
    assert 'date' in n_en and 'source' in n_en and 'rumors' in n_en
    t_es, t_en = WORKING['technical']
    assert all(w in t_es for w in ('precio', 'último año', 'tendencia', 'máximo', 'mínimo', 'S&P 500'))
    assert all(w in t_en for w in ('price', 'last year', 'trend', 'high', 'low', 'S&P 500'))
    s_es, s_en = WORKING['supply_chain']
    assert 'de quién depende' in s_es and 'países' in s_es and 'proveedores' in s_es
    assert 'who it depends on' in s_en and 'countries' in s_en and 'suppliers' in s_en
    g_es, g_en = WORKING['geopolitical']
    assert all(w in g_es for w in ('países', 'sanciones', 'estrechos'))
    assert all(w in g_en for w in ('countries', 'sanctions', 'straits'))
    m_es, m_en = WORKING['macro']
    assert all(w in m_es for w in ('tasas', 'ciclo', 'monedas', 'conflictos'))
    assert all(w in m_en for w in ('rates', 'cycle', 'currency', 'conflicts'))
    assert 'cripto' in WORKING['crypto'][0] and 'crypto' in WORKING['crypto'][1]


def test_working_sin_jerga_y_en_ingles_estadounidense():
    """La sala la lee un inversionista no experto: nada de siglas sin explicar (RSI, GPR, medias de 50/200);
    esas quedan en SKILLS/FOCUS. El inglés de la app es estadounidense (analyze, rumors)."""
    from research.agent_skills import WORKING
    from research.committee import UNLISTED_TECH, UNLISTED_TECH_START
    lines = [x for pair in WORKING.values() for x in pair] + list(UNLISTED_TECH) + list(UNLISTED_TECH_START)
    for t in lines:
        for jargon in ('RSI', 'GPR', '50 y 200', '50/200', 'medias móviles', 'moving average'):
            assert jargon not in t, (jargon, t)
        low = t.lower()
        for brit in ('analys', 'rumour', 'colour', 'behaviour'):
            assert brit not in low, (brit, t)


def test_started_dice_lo_suyo_en_vez_de_la_frase_generica(monkeypatch):
    from research.agent_skills import WORKING
    agents = ['fundamental', 'news', 'technical', 'supply_chain']
    said, calls = _drive(monkeypatch, 'Nvidia', agents, {a: _ok() for a in agents})
    assert calls['create'][0] == 'Nvidia' and calls['create'][1]['force'] is True     # el pedido no cambió
    started = [m for m in said if m['seat'] != 'chair' and m['text_es'] in {v[0] for v in WORKING.values()}]
    assert [m['seat'] for m in started] == agents
    assert len({m['text_es'] for m in started}) == 4 and len({m['text_en'] for m in started}) == 4
    for m in started:
        assert (m['text_es'], m['text_en']) == WORKING[m['seat']]
        assert m['kind'] == 'data' and m['stage'] == 'research'
    assert not any(OLD_LINE in m['text_es'] for m in said)
    done = [m for m in said if m['text_es'].startswith('Listo: 2 conclusión')]
    assert len(done) == 4 and all(m['text_en'].startswith('Done: 2 conclusion') for m in done)


def test_mensajes_conservan_el_esquema_de_la_sala(monkeypatch):
    from research import deliberation as dl8
    keys = set(dl8._msg('chair', 'moderate', 'a', 'b', stage='research'))
    said, _ = _drive(monkeypatch, 'Nvidia', ['fundamental', 'technical'], {'fundamental': _ok(), 'technical': _ok()})
    assert said and all(set(m) == keys for m in said)


# ════════════════════════════════════════════════════════════════════════════
# 2 · el presidente nombra a cada analista por su mascota
# ════════════════════════════════════════════════════════════════════════════

def test_presidente_nombra_a_las_mascotas(monkeypatch):
    agents = ['fundamental', 'news', 'technical', 'supply_chain']
    said, _ = _drive(monkeypatch, 'Nvidia', agents, {a: _ok() for a in agents})
    chair = said[0]
    assert chair['seat'] == 'chair' and chair['kind'] == 'moderate' and chair['stage'] == 'research'
    assert ('pido a Analista (fundamental), Radar (noticias), Técnico y Cadena que investiguen ahora con datos '
            'en vivo (cada uno tarda ~20-60 s)') in chair['text_es']
    assert ('I ask Analyst (fundamentals), Radar (news), Technical and Chain to research now with live data '
            '(each takes ~20-60 s)') in chair['text_en']
    assert 'No hay investigación reciente suficiente sobre Nvidia' in chair['text_es']
    for old in ('📊', 'Analista fundamental', 'Analista de noticias', 'Fundamental analyst', 'News analyst'):
        assert old not in chair['text_es'] and old not in chair['text_en']


def test_presidente_en_singular_cuando_falta_uno(monkeypatch):
    said, _ = _drive(monkeypatch, 'Nvidia', ['geopolitical'], {'geopolitical': _ok()})
    assert 'pido a Radar (geopolítica) que investigue ahora con datos en vivo (tarda ~20-60 s)' in said[0]['text_es']
    assert 'I ask Radar (geopolitics) to research now with live data (it takes ~20-60 s)' in said[0]['text_en']


def test_nombres_de_puesto():
    from research.agent_skills import join_names, seat_call_name, seat_mascot
    assert seat_call_name('fundamental') == 'Analista (fundamental)'
    assert seat_call_name('macro', 'en') == 'Analyst (macro)'
    assert seat_call_name('crypto') == 'Radar (cripto)'
    assert seat_call_name('technical') == 'Técnico' and seat_call_name('technical', 'en') == 'Technical'
    assert seat_call_name('risk_observation') == 'Técnico (riesgos)'
    assert seat_call_name('supply_chain') == 'Cadena' and seat_call_name('supply_chain', 'en') == 'Chain'
    assert seat_mascot('chair') == 'comite' and seat_mascot('desconocido') is None
    assert join_names(['A']) == 'A' and join_names(['A', 'B']) == 'A y B'
    assert join_names(['A', 'B', 'C'], 'en') == 'A, B and C' and join_names([]) == ''


def test_mapeo_puesto_mascota_igual_que_el_cliente_y_el_chat():
    """SEAT_MASCOT (servidor, sin dependencias) = engine/mascot.js seats = core/khipu_chat.SEAT_AGENT."""
    from research.agent_skills import MASCOT_NAME, SEAT_MASCOT
    js = _read('engine/mascot.js')
    js_map = {}
    for mid, seats in re.findall(r"\{\s*id:\s*'(\w+)'.*?seats:\s*\[([^\]]*)\]", js, re.S):
        for s in re.findall(r"'(\w+)'", seats):
            js_map[s] = mid
    assert js_map, 'no se pudo leer engine/mascot.js'
    for seat, mid in SEAT_MASCOT.items():
        assert js_map.get(seat) == mid, seat
    from core.khipu_chat import AGENT_LABEL, SEAT_AGENT
    for seat, mid in SEAT_MASCOT.items():
        assert SEAT_AGENT.get(seat) == mid, seat
    assert MASCOT_NAME == AGENT_LABEL


# ════════════════════════════════════════════════════════════════════════════
# 3 · el Técnico ante una empresa que no cotiza
# ════════════════════════════════════════════════════════════════════════════

def test_tecnico_sin_cotizacion_lo_dice_en_su_voz(monkeypatch):
    from research.committee import UNLISTED_TECH
    agents = ['fundamental', 'technical']
    # la detección mira el ticker del catálogo, NO el texto del error: aquí el error no dice "sin evidencia"
    runs = {'fundamental': _ok(), 'technical': _fail('ValueError: algo raro')}
    said, _ = _drive(monkeypatch, 'OpenAI', agents, runs)           # snapshot real: OpenAI sin `mkt`
    tech = [m for m in said if m['seat'] == 'technical']
    assert tech[-1]['text_es'] == UNLISTED_TECH[0] and tech[-1]['text_en'] == UNLISTED_TECH[1]
    assert tech[-1]['text_es'].startswith('No cotiza por separado en bolsa: no hay precio propio que analizar.')
    assert 'El resto del comité sigue' in tech[-1]['text_es'] and 'Not listed on its own' in tech[-1]['text_en']
    assert 'No pude concluir' not in tech[-1]['text_es'] and 'algo raro' not in tech[-1]['text_es']
    # neutral: no todo lo que no cotiza es una "empresa privada" (divisiones, fusionadas, bancos centrales…)
    assert 'privad' not in UNLISTED_TECH[0] and 'private' not in UNLISTED_TECH[1]
    # al EMPEZAR ya no dice "analizo su precio del último año" para luego desdecirse
    from research.agent_skills import WORKING
    from research.committee import UNLISTED_TECH_START
    assert (tech[0]['text_es'], tech[0]['text_en']) == UNLISTED_TECH_START
    assert WORKING['technical'][0] not in [m['text_es'] for m in tech]


def test_tecnico_sin_cotizacion_usa_la_nota_del_catalogo(monkeypatch):
    """División / fusionada / comprada: la nota verificada de nodes/listing_status.js explica dónde está su
    exposición bursátil (p. ej. la acción de IBM), en vez de llamarla "empresa privada"."""
    from research.committee import UNLISTED_TECH, _unlisted_tech_lines
    idx = {'Div': {'id': 'Div', 'mkt': None, 'listing': {'status': 'subsidiary', 'parent_ticker': 'IBM',
                                                          'note_es': 'División de IBM; su exposición es la acción de IBM',
                                                          'note_en': 'An IBM division; its exposure is IBM stock.'}},
           'Priv': {'id': 'Priv', 'mkt': None}}
    said, _ = _drive(monkeypatch, 'Div', ['technical'], {'technical': _fail('sin evidencia')}, index=idx)
    es, en = said[-1]['text_es'], said[-1]['text_en']
    assert es == ('No cotiza por separado en bolsa: no hay precio propio que analizar. División de IBM; su exposición '
                  'es la acción de IBM. El resto del comité sigue.')
    assert en == ('Not listed on its own: there is no price of its own to analyze. An IBM division; its exposure is '
                  'IBM stock. The rest of the committee carries on.')
    import core.entities as ents
    monkeypatch.setattr(ents, 'get_index', lambda: {'nodos': idx})
    assert _unlisted_tech_lines('Priv') == UNLISTED_TECH


def test_tecnico_sin_cotizacion_tambien_si_se_salta(monkeypatch):
    from research.committee import UNLISTED_TECH
    idx = {'PrivCo': {'id': 'PrivCo', 'label': 'PrivCo', 'mkt': ''}}
    runs = {'technical': SimpleNamespace(status='skipped', claims_generated=0,
                                         errors=['sin evidencia para technical'])}
    said, _ = _drive(monkeypatch, 'PrivCo', ['technical'], runs, index=idx)
    assert (said[-1]['text_es'], said[-1]['text_en']) == UNLISTED_TECH


def test_otros_puestos_de_privada_y_fallas_de_cotizada_siguen_con_friendly(monkeypatch):
    from research.errors import friendly
    busy = 'AIBusyError: IA ocupada tras 4 esperas'
    hes, hen = friendly(busy)
    # empresa privada: el que falla NO es el técnico → texto de siempre
    said, _ = _drive(monkeypatch, 'OpenAI', ['news'], {'news': _fail(busy)})
    assert said[-1]['text_es'] == f'No pude concluir nada sólido: {hes}'
    assert said[-1]['text_en'] == f'I could not reach a solid conclusion: {hen}'
    # empresa que cotiza: el técnico que falla conserva el friendly()
    said, _ = _drive(monkeypatch, 'Nvidia', ['technical'], {'technical': _fail(busy)})
    assert said[-1]['text_es'] == f'No pude concluir nada sólido: {hes}'
    assert said[-1]['text_en'] == f'I could not reach a solid conclusion: {hen}'
    # cotizada, técnico listo pero sin conclusiones → tampoco dice "no cotiza"
    said, _ = _drive(monkeypatch, 'Nvidia', ['technical'], {'technical': SimpleNamespace(status='done',
                                                                                         claims_generated=0, errors=[])})
    assert said[-1]['text_es'] == 'No pude concluir nada sólido: done'


def test_privada_con_conclusiones_tecnicas_dice_listo(monkeypatch):
    said, _ = _drive(monkeypatch, 'OpenAI', ['technical'], {'technical': _ok(1)})
    assert said[-1]['text_es'] == 'Listo: 1 conclusión(es) con evidencia citada.'


def test_si_no_se_sabe_si_cotiza_no_se_afirma(monkeypatch):
    from research.committee import _entity_listed
    import core.entities as ents
    monkeypatch.setattr(ents, 'get_index', lambda: {'nodos': {'X': {'mkt': 'XYZ'}, 'P': {'mkt': None}}})
    assert _entity_listed('X') is True and _entity_listed('P') is False and _entity_listed('fuera') is None
    said, _ = _drive(monkeypatch, 'fuera', ['technical'], {'technical': _fail('timeout')},
                     index={'X': {'mkt': 'XYZ'}})
    assert said[-1]['text_es'].startswith('No pude concluir nada sólido')

    def boom():
        raise RuntimeError('snapshot roto')
    monkeypatch.setattr(ents, 'get_index', boom)
    assert _entity_listed('X') is None


@needs_db
def test_punta_a_punta_con_el_runner_real(monkeypatch):
    """create_job/execute_job de verdad: privada sin velas → el Técnico dice 'No cotiza'; el resto, su línea."""
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    import research.models  # noqa: F401
    from research.agent_skills import WORKING
    from research.committee import UNLISTED_TECH, _auto_research
    from research.llm import FakeProvider
    from tests.test_research import FETCH, _claim, _result
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    try:
        fetch = dict(FETCH, news=lambda q, n: [], candles=lambda s: [], profile=lambda s: {'available': False})
        ok = _result([_claim(evidence_refs=['E1'], counter_evidence_refs=[])])
        said = []
        with session_scope() as s:
            _auto_research(s, 'OpenAI', 'OpenAI', 'pytest', lambda *m: said.extend(m),
                           {'research_provider_factory': lambda a: FakeProvider([ok]), 'fetchers': fetch},
                           agents=['fundamental', 'technical'])
        assert 'Analista (fundamental) y Técnico' in said[0]['text_es']
        tech = [m for m in said if m['seat'] == 'technical']
        assert (tech[-1]['text_es'], tech[-1]['text_en']) == UNLISTED_TECH
        fund = [m['text_es'] for m in said if m['seat'] == 'fundamental']
        assert WORKING['fundamental'][0] in fund
    finally:
        Base.metadata.drop_all(engine)


# ════════════════════════════════════════════════════════════════════════════
# 4 · la Guía explica las mascotas y el "invocar" (ES/EN)
# ════════════════════════════════════════════════════════════════════════════

def test_guia_habla_de_mascotas_e_invocar():
    s = _read('engine/guide.js')
    for old in ('Valeria', 'Kenji', 'Amara', 'personaje', 'a character'):
        assert old not in s, old
    es = next(ln for ln in s.splitlines() if "['🏛 Comité de inversión'" in ln)
    en = next(ln for ln in s.splitlines() if "['🏛 Investment committee'" in ln)
    for w in ('mascotas', 'Analista', 'Radar', 'Cadena', 'Técnico', 'Comité', 'invócala', 'Sala del comité', 'PIN'):
        assert w in es, w
    for w in ('mascots', 'Analyst', 'Radar', 'Chain', 'Technical', 'Committee', 'invoke', 'Committee room', 'PIN'):
        assert w in en, w
    # el sujeto no cambia a mitad de frase: es la MASCOTA la que entra y responde, no la persona
    assert 'toca su mascota en la pantalla de inicio y entrará a la conversación para responderte desde su rol' in es
    assert 'entra a la conversación para responderte' not in es


# ════════════════════════════════════════════════════════════════════════════
# 5 · dentro del TEXTO de la sala, cada analista se llama como su mascota
# ════════════════════════════════════════════════════════════════════════════

def test_textos_de_deliberacion_usan_nombres_de_mascota():
    """research/deliberation.py escribe "📊 Analista fundamental" dentro de los mensajes (apertura, réplicas,
    cierre del presidente); la sala los pasa por _mascot_voice → "Analista (fundamental)", "Técnico"…"""
    from research import deliberation as dl8
    from research.committee import _mascot_voice
    seats = [{'seat': a, 'emoji': dl8.seat_name(a)[0], 'name_es': dl8.seat_name(a)[1], 'name_en': dl8.seat_name(a)[2],
              'stance': 'for', 'absent': a == 'geopolitical'}
             for a in ('fundamental', 'news', 'technical', 'supply_chain', 'geopolitical')]
    msgs = [dl8._msg('chair', 'open', 'Tenemos: ' + ', '.join(s['emoji'] + ' ' + s['name_es'] for s in seats[:4]) +
                     ' (sin conclusiones: ' + seats[4]['name_es'] + ')',
                     'We have: ' + ', '.join(s['emoji'] + ' ' + s['name_en'] for s in seats[:4]) +
                     ' (no conclusions: ' + seats[4]['name_en'] + ')')]
    body = {'dissent': [{'agent_type': 'technical', 'view_es': 'el precio cae', 'view_en': 'price is falling'}]}
    msgs += dl8.chair_close(body, 'HOLD', 'HOLD', ('MANTENER', 'HOLD'), True)
    out = [_mascot_voice(m) for m in msgs]
    es = ' | '.join(m['text_es'] for m in out)
    en = ' | '.join(m['text_en'] for m in out)
    for old in ('Analista fundamental', 'Analista de noticias', 'Analista técnico', 'Analista de cadena de suministro',
                'Analista geopolítico', '📊', '📈'):
        assert old not in es, old
    for old in ('Fundamental analyst', 'News analyst', 'Technical analyst', 'Supply-chain analyst', 'Geopolitical analyst'):
        assert old not in en, old
    assert 'Analista (fundamental), Radar (noticias), Técnico, Cadena (sin conclusiones: Radar (geopolítica))' in es
    assert 'Analyst (fundamentals), Radar (news), Technical, Chain (no conclusions: Radar (geopolitics))' in en
    assert 'A Técnico: tu objeción queda registrada' in es and 'To Technical: your objection is on record' in en
    # mismo esquema, mismo puesto; idempotente; palabras que solo EMPIEZAN igual no se tocan
    assert [set(m) for m in out] == [set(m) for m in msgs] and [m['seat'] for m in out] == [m['seat'] for m in msgs]
    assert [_mascot_voice(m) for m in out] == out
    m = _mascot_voice(dl8._msg('chair', 'moderate', 'Analista macroeconómico', 'Macro analysts'))
    assert m['text_es'] == 'Analista macroeconómico' and m['text_en'] == 'Macro analysts'


def test_la_sala_traduce_en_su_unico_punto_de_salida():
    src = _read('research/committee.py')
    assert 'msgs = [_mascot_voice(m) for m in msgs if m]' in src
    assert 'el presidente IA' not in src.replace('Llama al presidente IA', '')       # la UI dice "presidencia"
    assert 'la presidencia (IA) no se consulta' in src
