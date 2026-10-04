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
    monkeypatch.setattr(ai, '_CIRCUIT', {})
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
    assert ai.ai_circuit_state()['gemini'] == pytest.approx(ai.ai_circuit_state()['gemini'])
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
        return _ok_result()

    ts = [threading.Thread(target=lambda e=e: _run(e, ['fundamental', 'news'], {'fundamental': [slow], 'news': [slow]}))
          for e in ('Nvidia', 'AMD')]
    for t in ts:
        t.start()
    for t in ts:
        t.join(30)
    assert state['max'] == 1            # antes: cada job abría su propio pool → 2-4 a la vez


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
    order, state, lock = [], {'now': 0, 'max': 0}, threading.Lock()

    def fake_exec(session, job, **kw):
        with lock:
            state['now'] += 1
            state['max'] = max(state['max'], state['now'])
        order.append(job.entity_id)
        time.sleep(0.2)
        job.status, job.completed_at = 'done', runner._now()
        with lock:
            state['now'] -= 1

    monkeypatch.setattr(runner, 'execute_job', fake_exec)
    ids = []
    with session_scope() as s:
        for e in ('Nvidia', 'AMD', 'TSMC'):
            job, _ = create_job(s, e, agents=['fundamental'], force=True)
            ids.append(job.id)
    for jid in ids:
        runner.execute_job_async(jid)
    st = runner.research_queue_state()
    assert st['job_concurrency'] == 1 and st['jobs_queued'] + st['jobs_running'] >= 2
    pos = runner.queue_position(ids[2])
    assert pos is None or pos >= 1
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
