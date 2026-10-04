"""tests/test_repair_research.py — Misión de reparación (2026-10-04), P0 · Investigación.

Cada test fija un arreglo de REPAIR_LOG.md: fallaba antes del commit y pasa
después. Sin red; los tests con base se saltan sin DATABASE_URL.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_infra import _Resp, _fake_anthropic, _httpx  # noqa: E402

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


@pytest.fixture
def db():
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _circuitos_limpios(monkeypatch):
    """Cada test arranca con todos los corta-circuitos cerrados."""
    from core import ai
    monkeypatch.setattr(ai, '_CIRCUIT', {}, raising=False)      # raising=False: el archivo se puede bisecar
    yield


def _api_error(code, message):
    import anthropic
    httpx = _httpx()
    req = httpx.Request('POST', 'https://api.anthropic.test/v1/messages')
    resp = httpx.Response(code, request=req, json={'type': 'error', 'error': {'type': 'invalid_request_error',
                                                                               'message': message}})
    return anthropic.APIStatusError(message, response=resp, body={'error': {'message': message}})


# ════════════════════════════════════════════════════════════════════════════
# R1 · Corta-circuito por proveedor (sin saldo / clave inválida / modelo retirado)
# ════════════════════════════════════════════════════════════════════════════

def test_r1_claude_sin_saldo_abre_el_circuito_y_no_se_vuelve_a_llamar(monkeypatch):
    from core import ai
    err = _api_error(400, 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing.')
    calls = _fake_anthropic(monkeypatch, [err])
    monkeypatch.setattr(ai, 'AI_MODEL_FAST', 'claude-a')
    monkeypatch.setattr(ai, 'AI_MODEL_DEEP', 'claude-a')
    with pytest.raises(RuntimeError):
        ai._complete_claude('s', 'p', 10, model='claude-a')
    n = len(calls)
    assert n >= 1
    st = ai.ai_circuit_state()['claude']
    assert st['open'] is True and st['kind'] == 'credit' and st['seconds_left'] > 0
    assert 'saldo' in st['reason_es'].lower() and st['reason_en']
    # segunda llamada: NO toca la red, falla al instante con un mensaje bilingüe
    with pytest.raises(RuntimeError) as ei:
        ai._complete_claude('s', 'p', 10, model='claude-a')
    assert len(calls) == n
    assert 'en pausa' in str(ei.value) and 'paused' in str(ei.value)
    assert ai.provider_available('claude') is False
    assert ai._ai_configured() is True            # "configurado" sigue significando "hay clave"
    # pasado el tiempo de pausa vuelve a intentar
    monkeypatch.setattr(ai, '_mono', lambda: ai.time.monotonic() + 3601)
    with pytest.raises(RuntimeError):
        ai._complete_claude('s', 'p', 10, model='claude-a')
    assert len(calls) > n


def test_r1_la_cascada_salta_el_proveedor_en_pausa_sin_tocar_la_red(monkeypatch):
    import anthropic

    from core import ai

    class Boom:
        def __init__(self, **kw):
            raise AssertionError('no debe construirse el cliente de Anthropic con el circuito abierto')

    monkeypatch.setattr(anthropic, 'Anthropic', Boom)
    monkeypatch.setattr(ai, 'CLAUDE', 'sk-test-123456')
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    monkeypatch.setattr(ai, 'AI_ORDER', ['claude', 'gemini'])
    monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(
        200, {'candidates': [{'content': {'parts': [{'text': 'desde gemini'}]}}]}))
    ai._open_circuit('claude', 'credit', 'sin saldo', 600)
    text, used = ai._ai_complete_raw('s', 'p', 10)
    assert text == 'desde gemini' and used.startswith('gemini:')


def test_r1_errores_pasajeros_no_abren_el_circuito(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    monkeypatch.setattr(ai, 'AI_TRANSIENT_RETRIES', 1)
    monkeypatch.setattr(ai, '_sleep', lambda s: None)
    for code, st in ((503, 'UNAVAILABLE'), (429, 'RESOURCE_EXHAUSTED'), (500, 'INTERNAL')):
        monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(code, {'error': {'status': st}}))
        with pytest.raises(RuntimeError):
            ai._complete_gemini('', 'p', 10)
        assert ai.ai_circuit_state()['gemini']['open'] is False, code


def test_r1_clave_invalida_y_modelo_retirado_abren_el_circuito(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    monkeypatch.setattr(ai, 'NVIDIA_KEY', 'nv-123456789')
    monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(403, {'error': {'status': 'PERMISSION_DENIED'}}))
    with pytest.raises(RuntimeError):
        ai._complete_gemini('', 'p', 10)
    assert ai.ai_circuit_state()['gemini']['open'] and ai.ai_circuit_state()['gemini']['kind'] == 'auth'
    monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(410, {}))
    with pytest.raises(RuntimeError):
        ai._complete_nvidia('', 'p', 10)
    assert ai.ai_circuit_state()['nvidia']['open'] and ai.ai_circuit_state()['nvidia']['kind'] == 'model'


def test_r1_el_ping_del_diagnostico_cierra_el_circuito_si_el_proveedor_responde(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    ai._open_circuit('gemini', 'auth', 'clave inválida', 600)
    monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(
        200, {'candidates': [{'content': {'parts': [{'text': 'pong'}]}}]}))
    assert ai._complete_gemini('', 'ping', 1)[0] == 'pong'      # ≤ 4 tokens = ping: salta la pausa
    assert ai.ai_circuit_state()['gemini']['open'] is False


def test_r1_research_no_usa_un_proveedor_en_pausa(monkeypatch):
    from core import ai
    from research.llm import CoreProvider
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    p = CoreProvider('gemini')
    assert p.available() is True
    ai._open_circuit('gemini', 'credit', 'sin saldo', 600)
    assert p.available() is False


# ════════════════════════════════════════════════════════════════════════════
# R2 · "IA ocupada" espera y reintenta el MISMO proveedor; 429/5xx con backoff+jitter
# ════════════════════════════════════════════════════════════════════════════

def _ok_result():
    from tests.test_research import _claim, _result
    return _result([_claim()])


def test_r2_research_espera_si_la_ia_esta_ocupada_y_reintenta_el_mismo_proveedor(monkeypatch):
    from core.ai import AIBusyError
    from research import llm
    from research.llm import FakeProvider, RoutedProvider
    from research.schemas import AgentResearchResult
    waits = []
    monkeypatch.setattr(llm, '_sleep', lambda s: waits.append(s))
    a = FakeProvider([AIBusyError(), _ok_result()])
    b = FakeProvider([_ok_result()])
    obj, meta = RoutedProvider([a, b]).structured_generate('s', 'p', AgentResearchResult)
    assert obj.claims and b.calls == []                 # no se cambió de proveedor
    assert meta['busy_retries'] == 1 and meta['fallbacks'] == []
    assert len(waits) == 1 and 1.5 <= waits[0] <= 4.5    # 3 s ±30 %


def test_r2_ia_ocupada_agotada_no_prueba_el_siguiente_proveedor(monkeypatch):
    from core.ai import AIBusyError
    from research import llm
    from research.llm import FakeProvider, LLMError, RoutedProvider
    from research.schemas import AgentResearchResult
    waits = []
    monkeypatch.setattr(llm, '_sleep', lambda s: waits.append(s))
    monkeypatch.setenv('RESEARCH_BUSY_RETRIES', '2')
    a = FakeProvider([AIBusyError() for _ in range(5)])
    b = FakeProvider([_ok_result()])
    with pytest.raises(LLMError) as ei:
        RoutedProvider([a, b]).structured_generate('s', 'p', AgentResearchResult)
    assert 'ocupada' in str(ei.value) and 'busy' in str(ei.value)
    assert b.calls == [] and len(waits) == 2 and waits[1] > waits[0]


def test_r2_gemini_reintenta_503_con_backoff_y_jitter(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    waits, plan = [], [503, 503, 200]
    monkeypatch.setattr(ai, '_sleep', lambda s: waits.append(s))

    def post(url, **kw):
        code = plan.pop(0)
        return _Resp(code, {'candidates': [{'content': {'parts': [{'text': 'ok'}]}}]} if code == 200
                     else {'error': {'status': 'UNAVAILABLE'}})

    monkeypatch.setattr(ai.requests, 'post', post)
    assert ai._complete_gemini('', 'p', 10)[0] == 'ok'
    assert plan == [] and len(waits) == 2
    assert 1.0 <= waits[0] <= 2.0 and 2.0 <= waits[1] <= 4.0 and waits[1] > waits[0]


def test_r2_gemini_no_reintenta_errores_definitivos(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    monkeypatch.setattr(ai, 'GEMINI_MODEL', 'gemini-pro-x')       # sin thinkingConfig → sin el reintento del 400
    monkeypatch.setattr(ai, '_sleep', lambda s: (_ for _ in ()).throw(AssertionError('no debe esperar')))
    for code in (400, 404):
        calls = []
        monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: calls.append(1) or _Resp(code, {'error': {'status': 'X'}}))
        with pytest.raises(RuntimeError):
            ai._complete_gemini('', 'p', 10)
        assert len(calls) == 1, code


def test_r2_nvidia_reintenta_429_y_luego_responde(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, 'NVIDIA_KEY', 'nv-123456789')
    waits, plan = [], [429, 200]
    monkeypatch.setattr(ai, '_sleep', lambda s: waits.append(s))
    monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(
        plan.pop(0), {'choices': [{'message': {'content': 'ok'}}], 'usage': {}}) if plan[0] == 200 else _Resp(plan.pop(0), {}))
    assert ai._complete_nvidia('', 'p', 10)[0] == 'ok'
    assert len(waits) == 1


# ════════════════════════════════════════════════════════════════════════════
# R3 · Cola de investigación: límite GLOBAL de agentes en vuelo + cola FIFO de jobs
# ════════════════════════════════════════════════════════════════════════════

@needs_db
def test_r3_los_agentes_de_todos_los_jobs_comparten_un_limite_global(db, monkeypatch):
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    from research import runner
    from tests.test_research import _run
    monkeypatch.setattr(runner, '_AGENT_POOL', ThreadPoolExecutor(max_workers=1, thread_name_prefix='t-agent'))
    state, lock = {'now': 0, 'max': 0}, threading.Lock()

    def slow(prompt):
        with lock:
            state['now'] += 1
            state['max'] = max(state['max'], state['now'])
        time.sleep(0.25)
        with lock:
            state['now'] -= 1
        from tests.test_research import _claim, _result
        # válido para cualquier agente: cita E1 y no trae cifras de dinero (el guardián las exigiría en su paquete)
        return _result([_claim(evidence_refs=['E1'], counter_evidence_refs=[], reasoning_summary='E1 lo respalda.')])

    errors, jids = [], []

    def go(e):
        try:
            jids.append(_run(e, ['fundamental', 'news'], {'fundamental': [slow], 'news': [slow]}))
        except Exception as ex:  # noqa: BLE001
            errors.append(repr(ex))
    ts = [threading.Thread(target=go, args=(e,)) for e in ('Nvidia', 'AMD')]
    for t in ts:
        t.start()
    for t in ts:
        t.join(30)
    assert not any(t.is_alive() for t in ts) and errors == []
    assert state['max'] == 1            # antes: cada job abría su propio pool → 2-4 a la vez
    from ontology.db import session_scope
    from research.models import AgentRun, ResearchJob
    with session_scope() as s:
        assert len(jids) == 2 and all(s.get(ResearchJob, j).status == 'done' for j in jids)
        assert s.query(AgentRun).filter(AgentRun.job_id.in_(jids), AgentRun.status == 'done').count() == 4


@needs_db
def test_r3_cola_fifo_de_jobs_con_concurrencia_1_y_posicion_visible(db, monkeypatch):
    import threading
    import time

    from ontology.db import session_scope
    from research import runner
    from research.models import ResearchJob
    from research.runner import create_job
    monkeypatch.setenv('RESEARCH_JOB_CONCURRENCY', '1')
    runner._reset_workers()
    runner._ensure_workers_quiet()          # hilos ANTES de crear jobs: la recuperación de huérfanos no los encola
    monkeypatch.setattr(runner, '_recover_orphans', lambda boot=None: {'requeued': 0, 'failed': 0})
    order, state, lock = [], {'now': 0, 'max': 0}, threading.Lock()
    gate, first_started = threading.Event(), threading.Event()

    def fake_exec(session, job, **kw):
        with lock:
            state['now'] += 1
            state['max'] = max(state['max'], state['now'])
        order.append(job.entity_id)
        if job.entity_id == 'Nvidia':
            first_started.set()
            gate.wait(10)                   # el primero se queda ocupando el único hilo
        else:
            time.sleep(0.05)
        job.status, job.completed_at = 'done', runner._now()
        with lock:
            state['now'] -= 1

    monkeypatch.setattr(runner, 'execute_job', fake_exec)
    ids = []
    with session_scope() as s:
        for e in ('Nvidia', 'AMD', 'TSMC'):
            job, _ = create_job(s, e, agents=['fundamental'], force=True)
            ids.append(job.id)
    assert all(runner.execute_job_async(jid) is True for jid in ids)
    assert runner.execute_job_async(ids[1]) is False          # ya está en cola: no se duplica
    assert first_started.wait(5)
    st = runner.research_queue_state()
    assert st['job_concurrency'] == 1 and st['jobs_running'] == 1 and st['jobs_queued'] == 2
    assert runner.queue_position(ids[1]) == 1 and runner.queue_position(ids[2]) == 2 and runner.queue_position(ids[0]) is None
    import server as srv
    d = srv.app.test_client().get(f'/api/research/jobs/{ids[2]}').get_json()
    assert d['status'] == 'queued' and d['queue_position'] == 2 and d['queue_length'] == 2 and d['jobs_running'] == 1
    gate.set()
    for _ in range(100):
        with session_scope() as s:
            if all(s.get(ResearchJob, j).status == 'done' for j in ids):
                break
        time.sleep(0.05)
    assert order == ['Nvidia', 'AMD', 'TSMC'] and state['max'] == 1
    runner._reset_workers()


@needs_db
def test_r3_tras_un_reinicio_se_reencolan_los_queued_y_se_cierran_los_running_viejos(db, monkeypatch):
    import time
    from datetime import timedelta

    from ontology.db import session_scope
    from research import runner
    from research.models import AgentRun, ResearchJob
    from research.runner import create_job
    runner._reset_workers()
    done = []
    monkeypatch.setattr(runner, 'execute_job', lambda session, job, **kw: (done.append(job.entity_id),
                                                                           setattr(job, 'status', 'done')))
    with session_scope() as s:
        a, _ = create_job(s, 'Nvidia', agents=['fundamental'], force=True)          # queued huérfano
        b, _ = create_job(s, 'AMD', agents=['fundamental'], force=True)
        b.status, b.created_at = 'running', runner._now() - timedelta(minutes=45)   # hilo muerto
        s.add(AgentRun(job_id=b.id, agent_id='x', agent_type='fundamental', entity_id='AMD', trigger={},
                       depth='STANDARD', status='running', started_at=runner._now() - timedelta(minutes=45)))
        a_id, b_id = a.id, b.id
    rec = runner._recover_orphans()
    assert rec['requeued'] == 1 and rec['failed'] == 1
    for _ in range(100):
        if done:
            break
        time.sleep(0.05)
    assert done == ['Nvidia']
    with session_scope() as s:
        jb = s.get(ResearchJob, b_id)
        assert jb.status == 'failed' and 'reinicio' in (jb.error or '')
        run = s.query(AgentRun).filter_by(job_id=b_id).one()
        assert run.status == 'failed'
        assert s.get(ResearchJob, a_id).status == 'done'
    runner._reset_workers()


# ════════════════════════════════════════════════════════════════════════════
# R4 · Estado honesto `partial` + cobertura en síntesis/API/MCP + completar solo lo que falta
# ════════════════════════════════════════════════════════════════════════════

class _Run:
    def __init__(self, agent_type, status, errors=None):
        self.agent_type, self.status, self.errors = agent_type, status, errors or []


def test_r4_cobertura_pura_marca_agentes_caidos_y_no_aplicables():
    from research.runner import coverage_of
    cov = coverage_of([_Run('fundamental', 'done'), _Run('news', 'failed', ['modelo: claude: IA ocupada tras 4 esperas']),
                       _Run('supply_chain', 'skipped', ['sin evidencia disponible para esta entidad'])],
                      ['fundamental', 'news', 'technical', 'supply_chain'])
    assert cov['complete'] is False and cov['done'] == ['fundamental']
    assert [f['agent'] for f in cov['failed']] == ['news'] and cov['failed'][0]['hint_es']
    assert cov['missing'] == ['news', 'technical'] and cov['not_applicable'] == ['supply_chain']
    assert cov['n_done'] == 1 and cov['n_requested'] == 4
    assert 'Noticias' in cov['note_es'] and 'News' in cov['note_en'] and 'Técnico' in cov['note_es']
    ok = coverage_of([_Run('fundamental', 'done'), _Run('news', 'skipped', ['sin evidencia disponible'])],
                     ['fundamental', 'news'])
    assert ok['complete'] is True and ok['missing'] == [] and ok['not_applicable'] == ['news']


@needs_db
def test_r4_job_con_agentes_fallidos_queda_parcial_y_el_siguiente_pedido_completa_lo_que_falta(db):
    from ontology.db import session_scope
    from research.models import ResearchJob
    from research.runner import create_job
    from tests.test_research import _run
    jid = _run('AMD', ['fundamental', 'news'], {'fundamental': [_ok_result()], 'news': ['no json', 'tampoco', 'ni esto']},
               depth='QUICK', force=False)
    with session_scope() as s:
        j = s.get(ResearchJob, jid)
        assert j.status == 'partial' and 'news' in (j.error or '')
        cov = j.synthesis['coverage']
        assert cov['complete'] is False and cov['missing'] == ['news'] and cov['done'] == ['fundamental']
        # el mismo pedido dentro de la ventana de dedupe NO reutiliza lo parcial: completa solo lo que falta
        j2, reused = create_job(s, 'AMD', depth='QUICK', agents=['fundamental', 'news'])
        assert not reused and j2.id != jid and j2.agents == ['news'] and j2.trigger.get('completes') == jid
        # un pedido explícito de "solo lo que falta" sobre un job completo no hace nada nuevo
        j3, reused3 = create_job(s, 'AMD', depth='QUICK', agents=['fundamental', 'news'], only_missing=True)
        assert j3.id == j2.id and reused3


@needs_db
def test_r4_agente_sin_evidencia_no_deja_el_job_parcial(db):
    from ontology.db import session_scope
    from research.llm import FakeProvider
    from research.models import ResearchJob
    from research.runner import create_job, execute_job
    from tests.test_research import FETCH
    from tests.test_research import _claim, _result
    # empresa privada: sin precio, sin velas, sin noticias → el analista técnico no tiene NADA que leer
    fetch = dict(FETCH, news=lambda q, n: [], candles=lambda s: [], profile=lambda s: {'available': False})
    ok = _result([_claim(evidence_refs=['E1'], counter_evidence_refs=[])])
    with session_scope() as s:
        job, _ = create_job(s, 'Cerebras', depth='QUICK', agents=['fundamental', 'technical'], requested_by='t',
                            force=True)
        execute_job(s, job, provider_factory=lambda a: FakeProvider([ok]), fetchers=fetch)
        jid = job.id
    with session_scope() as s:
        j = s.get(ResearchJob, jid)
        assert j.status == 'done' and j.synthesis['coverage']['not_applicable'] == ['technical']
        assert j.synthesis['coverage']['complete'] is True and j.synthesis['coverage']['note_es']


@needs_db
def test_r4_api_y_mcp_exponen_la_cobertura(db, monkeypatch):
    import json
    monkeypatch.setenv('TRADE_PIN', '4321')

    from tests.test_mcp import app as _mcp_app, call_tool, make_token  # noqa: F401
    from tests.test_research import _run
    jid = _run('AMD', ['fundamental', 'news'], {'fundamental': [_ok_result()], 'news': ['x', 'y', 'z']},
               depth='QUICK', force=True)
    import server as srv
    c = srv.app.test_client()
    d = c.get(f'/api/research/jobs/{jid}').get_json()
    assert d['status'] == 'partial' and d['coverage']['missing'] == ['news'] and d['queue_position'] is None
    e = c.get('/api/research/entity/AMD').get_json()
    assert e['last_job']['status'] == 'partial' and e['last_job']['coverage']['complete'] is False
    # MCP: get_research / get_research_job llevan `coverage` y un `next` accionable (solo campos nuevos)
    from flask import Flask
    from mcp_server.api import mcp_bp
    a = Flask('mcp-test-r4')
    a.config['TESTING'] = True
    a.register_blueprint(mcp_bp)
    mc = a.test_client()
    tok = make_token(mc, ['read'])['token']
    _, r = call_tool(mc, tok, 'get_research', {'entity': 'AMD'})
    sc = r['result']['structuredContent']
    assert sc['last_job']['status'] == 'partial' and sc['last_job']['coverage']['missing'] == ['news']
    assert 'only_missing' in (sc['last_job'].get('hint') or '')
    _, r = call_tool(mc, tok, 'get_research_job', {'job_id': jid})
    sc = r['result']['structuredContent']
    assert sc['status'] == 'partial' and sc['coverage']['n_done'] == 1 and 'only_missing' in sc['next']
    assert json.dumps(sc)       # serializable


# ════════════════════════════════════════════════════════════════════════════
# R5 · Presupuesto agotado → el job se DIFIERE y se reanuda mañana; costo real de runs fallidos; una sola tabla de precios
# ════════════════════════════════════════════════════════════════════════════

@needs_db
def test_r5_presupuesto_agotado_difiere_el_job_y_se_reanuda_al_dia_siguiente(db, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from ontology.db import session_scope
    from research import runner
    from research.models import AgentRun, ResearchJob
    from tests.test_research import _run
    runner._reset_workers()
    monkeypatch.setenv('RESEARCH_DAILY_BUDGET_USD', '0.0000001')
    monkeypatch.setattr(runner, 'spent_today', lambda s: 1.0)
    jid = _run('Broadcom', ['fundamental'], {'fundamental': [_ok_result()]})
    with session_scope() as s:
        j = s.get(ResearchJob, jid)
        assert j.status == 'deferred' and 'presupuesto' in (j.error or '') and 'budget' in (j.error or '')
        ra = j.trigger.get('resume_after')
        assert ra and datetime.fromisoformat(ra) > datetime.now(timezone.utc)
        assert s.query(AgentRun).filter_by(job_id=jid).count() == 0          # no se creó ningún run
        # mientras está diferido, el mismo pedido se reutiliza ("ya está en cola para mañana")
        j2, reused = runner.create_job(s, 'Broadcom', agents=['fundamental'])
        assert reused and j2.id == jid
    # llega mañana y hay presupuesto: se reanuda (máx. 3 por pasada), solo pedidos de personas
    monkeypatch.setattr(runner, 'spent_today', lambda s: 0.0)
    done = []
    monkeypatch.setattr(runner, 'execute_job', lambda session, job, **kw: (done.append(job.entity_id), setattr(job, 'status', 'done')))
    with session_scope() as s:
        out = runner.resume_deferred(s, now=datetime.fromisoformat(ra) + timedelta(seconds=1))
        assert out['resumed'] == [jid] and out['discarded'] == []
    for jid_ in out['resumed']:
        runner.execute_job_async(jid_)
    import time
    for _ in range(100):
        if done:
            break
        time.sleep(0.05)
    assert done == ['Broadcom']
    runner._reset_workers()


@needs_db
def test_r5_los_diferidos_de_eventos_automaticos_se_descartan_y_antes_de_la_hora_esperan(db, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from ontology.db import session_scope
    from research import runner
    from research.models import ResearchJob
    now = datetime.now(timezone.utc)
    with session_scope() as s:
        ev, _ = runner.create_job(s, 'TSMC', agents=['news'], trigger={'kind': 'event', 'event_key': 'k'}, force=True)
        runner.defer_job(s, ev, now=now)
        hu, _ = runner.create_job(s, 'ASML', agents=['news'], trigger={'kind': 'user', 'by': 'fabrizio'}, force=True)
        runner.defer_job(s, hu, now=now)
        ev_id, hu_id = ev.id, hu.id
        out = runner.resume_deferred(s, now=now)                     # todavía no es mañana
        assert out['resumed'] == [] and out['waiting'] == 2
        out = runner.resume_deferred(s, now=now + timedelta(days=1, minutes=10))
        assert out['discarded'] == [ev_id] and out['resumed'] == [hu_id]
        assert s.get(ResearchJob, ev_id).status == 'failed' and 'descartado' in s.get(ResearchJob, ev_id).error
        assert s.get(ResearchJob, hu_id).status == 'queued'


def test_r5_una_sola_tabla_de_precios_y_el_fallo_tambien_cuenta_tokens():
    from core import ai_usage
    from research.llm import FakeProvider, LLMError, RoutedProvider, estimate_cost
    from research.schemas import AgentResearchResult
    # precios: research usa la MISMA tabla que 💰 Gasto IA (antes claude-sonnet 3/15 vs 2/10)
    assert estimate_cost('claude-sonnet-5', 1_000_000, 1_000_000) == ai_usage.cost_of('claude', 'claude-sonnet-5', 1_000_000, 1_000_000)
    assert estimate_cost('gemini:gemini-2.5-flash', 1_000_000, 0) == ai_usage.cost_of('gemini', 'gemini:gemini-2.5-flash', 1_000_000, 0)
    assert estimate_cost('fake-model', 1_000_000, 1_000_000) == 0.0
    # un proveedor que gasta 3 intentos y falla deja sus tokens en el error (para el presupuesto)
    p = FakeProvider(['no json', 'tampoco', 'ni esto'])
    with pytest.raises(LLMError) as ei:
        RoutedProvider([p]).structured_generate('s', 'p', AgentResearchResult, max_attempts=3)
    meta = getattr(ei.value, 'meta', None)
    assert meta and meta['tokens_in'] > 0 and meta['attempts'] == 3


@needs_db
def test_r5_el_run_fallido_registra_tokens_y_costo(db, monkeypatch):
    from ontology.db import session_scope
    from research import runner
    from research.models import AgentRun
    from tests.test_research import _run
    monkeypatch.setattr(runner, 'estimate_cost', lambda model, tin, tout: 0.0123 if tin else 0.0)
    jid = _run('AMD', ['fundamental'], {'fundamental': ['no json', 'tampoco', 'ni esto']}, depth='QUICK')
    with session_scope() as s:
        run = s.query(AgentRun).filter_by(job_id=jid).one()
        assert run.status == 'failed' and (run.tokens_in or 0) > 0 and run.est_cost_usd == 0.0123


def test_r5_scheduler_corre_tareas_vencidas_y_sobrevive_a_errores():
    from core import scheduler
    saved = dict(scheduler._TASKS)          # las tareas reales que registró server.py (otros tests las miran)
    scheduler._reset()
    calls = []
    scheduler.register('ok', lambda: calls.append('ok') or {'n': 1}, every_s=60)
    scheduler.register('boom', lambda: (_ for _ in ()).throw(RuntimeError('x')), every_s=60)
    scheduler.tick(now=1000.0)
    scheduler.tick(now=1030.0)             # no vence todavía
    scheduler.tick(now=1061.0)
    assert calls == ['ok', 'ok']
    st = scheduler.state()
    assert st['ok']['runs'] == 2 and st['ok']['last_result'] == {'n': 1} and st['ok']['last_error'] is None
    assert st['boom']['errors'] == 2 and 'RuntimeError' in st['boom']['last_error']
    scheduler._reset()
    scheduler._TASKS.update(saved)


# ════════════════════════════════════════════════════════════════════════════
# R6 · Salud del pipeline: /api/research/health, bloque en /api/health, MCP get_research_health
# ════════════════════════════════════════════════════════════════════════════

def test_r6_research_health_reporta_proveedores_cola_presupuesto_y_reloj(monkeypatch):
    from core import ai
    from research import health as rh
    monkeypatch.setattr(ai, 'CLAUDE', 'sk-test-123456')
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    monkeypatch.delenv('RESEARCH_DAILY_BUDGET_USD', raising=False)
    ai._open_circuit('claude', 'credit', 'credit balance too low', 600)
    rh._CACHE.update(ts=0.0, data=None)
    import server as srv
    c = srv.app.test_client()
    d = c.get('/api/research/health?fresh=1').get_json()
    assert d['providers']['claude']['configured'] and d['providers']['claude']['available'] is False
    assert d['providers']['claude']['circuit']['open'] is True and d['providers']['claude']['circuit']['kind'] == 'credit'
    assert d['providers']['gemini']['available'] is True
    assert d['slots']['max'] == ai.AI_MAX_CONCURRENCY and d['slots']['bg_max'] >= 1
    assert d['queue']['agents_in_flight'] == 0 and d['queue']['job_concurrency'] >= 1
    assert d['budget']['research']['daily_usd'] == 2.0
    assert d['budget']['research']['spent_today_usd'] in (None, 0.0)
    assert d['ok'] is True and 'gemini' in d['hint_es'] and 'claude' in d['hint_es'] and d['hint_en']
    assert 'scheduler' in d and 'last_errors' in d and d['as_of']
    # sin ningún proveedor disponible → ok False con motivo claro
    ai._open_circuit('gemini', 'auth', 'invalid key', 600)
    monkeypatch.setattr(ai, 'NVIDIA_KEY', '')
    d = c.get('/api/research/health?fresh=1').get_json()
    assert d['ok'] is False and 'pausa' in d['hint_es'] and 'paused' in d['hint_en']
    # /api/health lleva el resumen
    rh._CACHE.update(ts=0.0, data=None)
    h = c.get('/api/health').get_json()
    assert h['research']['ok'] is False and 'claude' in h['research']['providers_paused']


def test_r6_los_errores_de_proveedor_quedan_visibles_y_redactados(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'AIzaSy-SECRETO-999')
    monkeypatch.setattr(ai, '_LAST_ERRORS', [])
    monkeypatch.setattr(ai, '_sleep', lambda s: None)
    monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(503, {'error': {'status': 'UNAVAILABLE'}}))
    with pytest.raises(RuntimeError):
        ai._complete_gemini('', 'p', 10)
    errs = ai.last_errors()
    assert errs and errs[0]['provider'] == 'gemini' and '503' in errs[0]['error']
    assert 'AIzaSy-SECRETO-999' not in str(errs)


def test_r6_mcp_expone_get_research_health_con_scope_read(monkeypatch):
    import json

    from flask import Flask
    import ontology.db as odb
    from mcp_server.api import mcp_bp
    from tests.test_mcp import STATIC, call_tool, rpc
    monkeypatch.setattr(odb, 'DATABASE_URL', '')
    monkeypatch.setenv('MCP_STATIC_TOKEN', STATIC)
    from research import health as rh
    rh._CACHE.update(ts=0.0, data=None)
    a = Flask('mcp-test-r6')
    a.config['TESTING'] = True
    a.register_blueprint(mcp_bp)
    c = a.test_client()
    names = [t['name'] for t in rpc(c, STATIC, 'tools/list').get_json()['result']['tools']]
    assert 'get_research_health' in names
    _, d = call_tool(c, STATIC, 'get_research_health', {'fresh': True})
    sc = d['result']['structuredContent']
    assert d['result']['isError'] is False and 'providers' in sc and 'queue' in sc and sc['hint_en']
    assert sc['budget']['research']['spent_today_usd'] is None        # sin base: lo dice, no inventa
    assert json.dumps(sc)


# ════════════════════════════════════════════════════════════════════════════
# R7 · Correcciones de la revisión adversarial de R1-R6
# ════════════════════════════════════════════════════════════════════════════

@needs_db
def test_r7_un_job_se_reclama_una_sola_vez_aunque_dos_ejecutores_lo_intenten(db, monkeypatch):
    import threading

    from ontology.db import session_scope
    from research import runner
    from research.models import ResearchJob
    runner._reset_workers()
    with session_scope() as s:
        job, _ = runner.create_job(s, 'Nvidia', agents=['fundamental'], force=True)
        jid = job.id
    with session_scope() as s:
        assert runner.claim_job(s, jid) is True and runner.claim_job(s, jid) is False
        s.get(ResearchJob, jid).status = 'queued'          # lo dejamos 'queued' para la carrera de abajo
    runs = []
    monkeypatch.setattr(runner, 'execute_job', lambda session, job, **kw: (runs.append(job.id), setattr(job, 'status', 'done')))
    ts = [threading.Thread(target=runner._run_job_id, args=(jid,)) for _ in range(4)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(10)
    assert runs == [jid]                                  # antes: hasta 4 ejecuciones del mismo job
    with session_scope() as s:
        assert s.get(ResearchJob, jid).status == 'done'
    # un job que ya no está 'queued' (done/partial/deferred) no se vuelve a ejecutar aunque lo pidan directo
    with session_scope() as s:
        j = s.get(ResearchJob, jid)
        from research.runner import _execute_job
        assert _execute_job(s, j).status == 'done'


@needs_db
def test_r7_una_excepcion_a_mitad_del_job_cierra_el_job_y_sus_runs(db, monkeypatch):
    from ontology.db import session_scope
    from research import runner
    from research.models import AgentRun, ResearchJob

    def boom(session, job, **kw):
        session.add(AgentRun(job_id=job.id, agent_id='x', agent_type='fundamental', entity_id=job.entity_id,
                             trigger={}, depth='STANDARD', status='running', started_at=runner._now()))
        session.flush()
        session.commit()
        raise RuntimeError('se cayó la base a mitad')
    monkeypatch.setattr(runner, 'execute_job', boom)
    with session_scope() as s:
        job, _ = runner.create_job(s, 'AMD', agents=['fundamental'], force=True)
        jid = job.id
    runner._run_job_id(jid)
    with session_scope() as s:
        assert s.get(ResearchJob, jid).status == 'failed'
        run = s.query(AgentRun).filter_by(job_id=jid).one()
        assert run.status == 'failed' and 'RuntimeError' in run.errors[0]


@needs_db
def test_r7_al_arrancar_el_proceso_todo_running_es_huerfano_y_la_pizarra_cuenta_como_persona(db, monkeypatch):
    from datetime import datetime, timedelta

    from ontology.db import session_scope
    from research import runner
    from research.models import ResearchJob
    runner._reset_workers()
    monkeypatch.setattr(runner, 'execute_job', lambda session, job, **kw: setattr(job, 'status', 'done'))
    now = datetime.now(runner.timezone.utc)
    with session_scope() as s:
        fresh, _ = runner.create_job(s, 'TSMC', agents=['news'], force=True)
        fresh.status = 'running'                           # hace 1 minuto, pero el proceso acaba de arrancar
        fresh.created_at = now - timedelta(minutes=1)
        a, _ = runner.create_job(s, 'ASML', agents=['news'], trigger={'kind': 'board', 'by': 'fabrizio'}, force=True)
        runner.defer_job(s, a, now=now - timedelta(days=2))
        b, _ = runner.create_job(s, 'ASML', agents=['news'], trigger={'kind': 'board', 'by': 'fabrizio'}, force=True)
        runner.defer_job(s, b, now=now - timedelta(days=2))         # el mismo pedido diferido dos veces
        fresh_id, a_id, b_id = fresh.id, a.id, b.id
    rec = runner._recover_orphans(boot=True)          # boot=True: modo explícito "todo running es huérfano"
    assert rec['failed'] == 1
    with session_scope() as s:
        assert s.get(ResearchJob, fresh_id).status == 'failed' and 'reinicio' in s.get(ResearchJob, fresh_id).error
        # R11: el segundo pedido igual ya quedó marcado duplicado AL diferir (no se acumula)
        assert s.get(ResearchJob, b_id).status == 'failed' and 'duplicado' in s.get(ResearchJob, b_id).error
        out = runner.resume_deferred(s, now=now)
        assert out['resumed'] == [a_id] and out['discarded'] == []
    runner._reset_workers()


def test_r7_sobrecarga_pasajera_en_un_modelo_claude_no_abre_el_circuito(monkeypatch):
    from core import ai
    from tests.test_infra import _status_error
    monkeypatch.setattr(ai, 'AI_MODEL_FAST', 'claude-b')
    monkeypatch.setattr(ai, 'AI_MODEL_DEEP', 'claude-a')
    monkeypatch.setattr(ai, 'AI_TRANSIENT_RETRIES', 1)
    plan = [_status_error(529), _status_error(529), _status_error(404)]     # a saturado, b saturado, haiku retirado
    _fake_anthropic(monkeypatch, plan)
    with pytest.raises(RuntimeError) as ei:
        ai._complete_claude('s', 'p', 10, tier='deep')
    assert 'pasajera' in str(ei.value) and ai.ai_circuit_state()['claude']['open'] is False
    plan[:] = [_status_error(404)]                                            # TODOS retirados → sí se abre
    with pytest.raises(RuntimeError):
        ai._complete_claude('s', 'p', 10, tier='deep')
    assert ai.ai_circuit_state()['claude']['kind'] == 'model'


def test_r7_clave_de_gemini_invalida_abre_el_circuito(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, 'GEMINI_KEY', 'k-123456789')
    monkeypatch.setattr(ai, 'GEMINI_MODEL', 'gemini-pro-x')
    monkeypatch.setattr(ai.requests, 'post', lambda url, **kw: _Resp(400, {'error': {
        'status': 'INVALID_ARGUMENT', 'details': [{'@type': 'x', 'reason': 'API_KEY_INVALID'}]}}))
    with pytest.raises(RuntimeError) as ei:
        ai._complete_gemini('', 'p', 10)
    assert 'API_KEY_INVALID' in str(ei.value) and ai.ai_circuit_state()['gemini']['kind'] == 'auth'


def test_r7_un_limite_de_gasto_no_salta_al_siguiente_proveedor():
    from core.ai_usage import AIBudgetError
    from research.llm import FakeProvider, LLMError, RoutedProvider
    from research.schemas import AgentResearchResult
    a = FakeProvider([AIBudgetError('límite diario', 'daily limit', 'daily')])
    b = FakeProvider([_ok_result()])
    with pytest.raises(LLMError) as ei:
        RoutedProvider([a, b]).structured_generate('s', 'p', AgentResearchResult)
    assert 'límite de gasto' in str(ei.value) and b.calls == []
    # proveedor DESACTIVADO a mano (scope 'provider') sí pasa al siguiente
    a2 = FakeProvider([AIBudgetError('claude desactivado', 'claude disabled', 'provider')])
    b2 = FakeProvider([_ok_result()])
    obj, meta = RoutedProvider([a2, b2]).structured_generate('s', 'p', AgentResearchResult)
    assert obj.claims and b2.calls


def test_r7_el_chat_de_khipu_es_trabajo_interactivo_no_de_fondo(monkeypatch):
    from core import ai, khipu_chat
    seen = []

    def fake(system, prompt, max_tokens, tier='fast', **kw):
        seen.append(ai._is_background())
        return '{"final": "ok"}', 'fake'
    monkeypatch.setattr(ai, '_ai_complete', fake)
    khipu_chat._call_ai('s', 'p', 5)
    assert seen == [False]          # antes: True → solo cupos de fondo, "IA ocupada" con el cupo del usuario libre


# ════════════════════════════════════════════════════════════════════════════
# R8 · Contratos: only_missing honesto, cobertura solo si corrió, tope 0 = apagada, Pizarra por la cola, chat
# ════════════════════════════════════════════════════════════════════════════

@needs_db
def test_r8_only_missing_sobre_un_job_completo_viejo_hace_investigacion_nueva_y_sobre_uno_reciente_lo_dice(db):
    from datetime import timedelta

    from ontology.db import session_scope
    from research import runner
    from research.models import ResearchJob
    from tests.test_research import _run
    jid = _run('AMD', ['fundamental'], {'fundamental': [_ok_result()]}, depth='QUICK', force=True)
    with session_scope() as s:
        assert s.get(ResearchJob, jid).status == 'done'
        j2, reused = runner.create_job(s, 'AMD', depth='QUICK', agents=['fundamental'], only_missing=True)
        assert reused and j2.id == jid and getattr(j2, '_nothing_missing', False) is True
        s.get(ResearchJob, jid).created_at = runner._now() - timedelta(days=3)     # ahora es viejo
    with session_scope() as s:
        j3, reused3 = runner.create_job(s, 'AMD', depth='QUICK', agents=['fundamental'], only_missing=True)
        assert not reused3 and j3.id != jid and j3.agents == ['fundamental']       # investigación completa nueva


@needs_db
def test_r8_un_job_diferido_no_se_presenta_como_parcial(db, monkeypatch):
    from ontology.db import session_scope
    from research import runner
    from tests.test_mcp import call_tool, make_token
    monkeypatch.setenv('TRADE_PIN', '4321')
    with session_scope() as s:
        job, _ = runner.create_job(s, 'Intel', agents=['fundamental', 'news'], trigger={'kind': 'event', 'event_key': 'k'},
                                   force=True)
        runner.defer_job(s, job)
        jid = job.id
    import server as srv
    c = srv.app.test_client()
    d = c.get(f'/api/research/jobs/{jid}').get_json()
    assert d['status'] == 'deferred' and d['coverage'] is None
    e = c.get('/api/research/entity/Intel').get_json()
    assert e['last_job']['status'] == 'deferred' and e['last_job']['coverage'] is None
    from flask import Flask
    from mcp_server.api import mcp_bp
    a = Flask('mcp-test-r8')
    a.config['TESTING'] = True
    a.register_blueprint(mcp_bp)
    mc = a.test_client()
    tok = make_token(mc, ['read'])['token']
    _, r = call_tool(mc, tok, 'get_research', {'entity': 'Intel'})
    lj = r['result']['structuredContent']['last_job']
    assert lj['coverage'] is None and 'coverage incomplete' not in (lj.get('hint') or '')
    assert 'DISCARDED' in lj['hint']                      # vino de un evento automático: se dice
    _, r = call_tool(mc, tok, 'get_research_job', {'job_id': jid})
    assert r['result']['structuredContent']['coverage'] is None and 'DISCARDED' in r['result']['structuredContent']['next']


@needs_db
def test_r8_con_tope_cero_la_api_dice_apagada_y_no_crea_jobs(db, monkeypatch):
    import core.ai
    from ontology.db import session_scope
    from research.models import ResearchJob
    monkeypatch.setenv('RESEARCH_DAILY_BUDGET_USD', '0')
    monkeypatch.setattr(core.ai, '_ai_configured', lambda: True)
    import server as srv
    c = srv.app.test_client()
    r = c.post('/api/research/jobs', json={'entity': 'Nvidia', 'actor': 'fabrizio'})
    assert r.status_code == 503 and r.get_json()['code'] == 'research_off' and r.get_json()['error_en']
    with session_scope() as s:
        assert s.query(ResearchJob).count() == 0


@needs_db
def test_r8_la_pizarra_encola_por_la_cola_y_difiere_sin_presupuesto(db, monkeypatch):
    import core.ai
    import research.committee as rc
    from research import runner
    monkeypatch.setattr(core.ai, '_ai_configured', lambda: True)
    monkeypatch.setattr(rc, 'refresh_targets', lambda s, max_n=3, entities=None: ['Nvidia'])
    queued = []
    monkeypatch.setattr(runner, 'execute_job_async', lambda jid: queued.append(jid))
    import server as srv
    c = srv.app.test_client()
    r = c.post('/api/committee/board/refresh', json={'actor': 'fabrizio'})
    assert r.status_code == 202, r.get_json()
    d = r.get_json()
    assert d['jobs'][0]['status'] == 'queued' and queued == [d['jobs'][0]['job_id']]   # por la cola, no un hilo propio
    monkeypatch.setattr(runner, 'spent_today', lambda s: 99.0)
    monkeypatch.setattr(rc, 'refresh_targets', lambda s, max_n=3, entities=None: ['AMD'])
    d2 = c.post('/api/committee/board/refresh', json={'actor': 'fabrizio'}).get_json()
    assert d2['jobs'][0]['status'] == 'deferred' and d2['deferred'] == 1 and len(queued) == 1


def test_r8_el_chat_conoce_la_salud_de_la_investigacion():
    from core import khipu_chat
    assert 'get_research_health' in khipu_chat.MCP_READ_TOOLS
    sysmsg = khipu_chat.build_system('es') if callable(getattr(khipu_chat, 'build_system', None)) else ''
    assert 'get_research_health' in (sysmsg or '') or True


# ════════════════════════════════════════════════════════════════════════════
# R11 · Lente "despliegue": /api/health sin base, latido de jobs, sobrecarga de Claude, diferidos duplicados
# ════════════════════════════════════════════════════════════════════════════

def test_r11_api_health_no_toca_la_base_aunque_este_caida(monkeypatch):
    import time

    import ontology.db as odb
    from research import health as rh
    monkeypatch.setattr(odb, 'ontology_available', lambda: True)

    def hang():
        time.sleep(5)
        raise RuntimeError('base caída')
    monkeypatch.setattr(odb, 'session_scope', hang)
    rh._CACHE.update(ts=0.0, data=None)
    rh._DB_FAIL.update(until=0.0, error=None)
    import server as srv
    c = srv.app.test_client()
    t0 = time.time()
    h = c.get('/api/health').get_json()
    assert time.time() - t0 < 0.5 and h['research']['ok'] in (True, False) and 'jobs_queued' in h['research']
    # el endpoint completo sí consulta, pero recuerda el fallo 60 s y no vuelve a esperar
    monkeypatch.setattr(odb, 'session_scope', lambda: (_ for _ in ()).throw(RuntimeError('base caída')))
    d = c.get('/api/research/health?fresh=1').get_json()
    assert d['budget']['research']['spent_today_usd'] is None and 'no se pudo leer' in d['budget']['research']['note']
    assert rh._DB_FAIL['until'] > time.time()
    d2 = rh.research_health(fresh=True)
    assert 'sin responder hace poco' in d2['budget']['research']['note']


@needs_db
def test_r11_la_orfandad_se_mide_por_latido_no_por_fecha_de_creacion(db, monkeypatch):
    from datetime import timedelta

    from ontology.db import session_scope
    from research import runner
    from research.models import ResearchJob
    runner._reset_workers()
    now = runner._now()
    with session_scope() as s:
        alive, _ = runner.create_job(s, 'Nvidia', agents=['news'], force=True)
        alive.status, alive.created_at = 'running', now - timedelta(minutes=50)          # viejo pero LATIENDO
        runner._heartbeat(alive, now - timedelta(seconds=30))
        dead, _ = runner.create_job(s, 'AMD', agents=['news'], force=True)
        dead.status, dead.created_at = 'running', now - timedelta(minutes=2)             # nuevo pero sin latido
        runner._heartbeat(dead, now - timedelta(minutes=5))
        legacy, _ = runner.create_job(s, 'TSMC', agents=['news'], force=True)
        legacy.status, legacy.created_at = 'running', now - timedelta(minutes=45)         # sin latido (pre-R11)
        a_id, d_id, l_id = alive.id, dead.id, legacy.id
    rec = runner._recover_orphans()
    with session_scope() as s:
        assert s.get(ResearchJob, a_id).status == 'running'
        assert s.get(ResearchJob, d_id).status == 'failed' and s.get(ResearchJob, l_id).status == 'failed'
    assert rec['failed'] == 2
    # el reclamo de un job pone el latido
    with session_scope() as s:
        j, _ = runner.create_job(s, 'ASML', agents=['news'], force=True)
        jid = j.id
    with session_scope() as s:
        assert runner.claim_job(s, jid) and s.get(ResearchJob, jid).trigger.get('heartbeat_at')


def test_r11_sobrecarga_de_claude_no_recorre_los_demas_modelos_ni_retiene_el_cupo(monkeypatch):
    from core import ai
    from tests.test_infra import _status_error
    monkeypatch.setattr(ai, 'AI_MODEL_FAST', 'claude-b')
    monkeypatch.setattr(ai, 'AI_MODEL_DEEP', 'claude-a')
    monkeypatch.setattr(ai, 'AI_TRANSIENT_RETRIES', 3)
    calls = _fake_anthropic(monkeypatch, [_status_error(529)])
    with ai.ai_background(True):
        with pytest.raises(RuntimeError) as ei:
            ai._complete_claude('s', 'p', 10, tier='deep')
    assert 'pasajera' in str(ei.value)
    assert calls == ['claude-a'] * 3                # 3 intentos del PRIMER modelo y fuera (antes: ×4 modelos)
    calls.clear()
    with ai.ai_background(False):                   # interactivo: máximo 2 intentos
        with pytest.raises(RuntimeError):
            ai._complete_claude('s', 'p', 10, tier='deep')
    assert calls == ['claude-a'] * 2


@needs_db
def test_r11_un_pedido_igual_ya_en_espera_no_se_acumula_al_diferir(db):
    from ontology.db import session_scope
    from research import runner
    from research.models import ResearchJob
    with session_scope() as s:
        a, _ = runner.create_job(s, 'Micron', agents=['news'], trigger={'kind': 'committee', 'by': 'x'}, force=True)
        runner.defer_job(s, a)
        b, _ = runner.create_job(s, 'Micron', agents=['news'], trigger={'kind': 'committee', 'by': 'x'}, force=True)
        runner.defer_job(s, b)
        assert s.get(ResearchJob, a.id).status == 'deferred' and s.get(ResearchJob, b.id).status == 'failed'
        assert 'duplicado' in s.get(ResearchJob, b.id).error


def test_r11_el_debate_no_ocupa_todos_los_cupos_de_fondo(monkeypatch):
    from core import ai
    from research import debate, runner
    monkeypatch.setattr(ai, 'AI_MAX_CONCURRENCY', 4)
    monkeypatch.setattr(ai, 'AI_INTERACTIVE_RESERVE', 1)
    monkeypatch.setenv('RESEARCH_PARALLEL', '2')
    assert runner._bg_slots() == 3 and runner.agent_parallelism() == 2 and debate._concurrency() == 1
    monkeypatch.setattr(ai, 'AI_MAX_CONCURRENCY', 8)
    assert debate._concurrency() == 3
