"""tests/test_ai_calls.py — INFRA_OPERATIVA paso 21 (GV-11) + BRECHAS L4-06: el registro `ai_calls`.

Garantiza:
  · UNA sola puerta: solo core/ai.py arma y encola filas de ai_calls (grep sobre el repo);
  · cada pedido de texto deja una fila: modelo REAL, nivel, prompt_sha/system_sha, tokens (caché leída y escrita
    por separado), costo, latencia y el veredicto del guardián de cifras (primer intento y reintento);
  · la fila se arma en memoria y se escribe en segundo plano: el hilo del usuario solo encola (µs);
  · atribución: dentro de `ai_calls.attribute(...)` o de un decision_scope la fila lleva decision_id, y lo hereda
    un hilo del pool vía core/ai_usage.bind; dentro de una decisión sync los blobs son 'legal', si no 90 días;
  · en la base: append-only (UPDATE/DELETE fallan), sellada por core/ledger, textos en blobs direccionados por
    hash (el system se guarda UNA vez), quién como hash (nunca en claro);
  · caché de prompts de Anthropic: el system largo va con cache_control; el corto, como texto (sin cambio).
"""
import json
import os
import re
import sys
import threading
import uuid
import zlib
from concurrent.futures import ThreadPoolExecutor

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
LONG_SYSTEM = 'Eres el analista de Khipus. ' + 'Regla estable del sistema. ' * 120


@pytest.fixture
def held_rows(monkeypatch):
    """Captura lo que core/ai encola (sin base)."""
    from core import ai_calls
    rows = []
    monkeypatch.setattr(ai_calls, '_db_on', lambda: True)
    monkeypatch.setattr(ai_calls, '_ensure_writer', lambda: None)
    ai_calls._reset_for_tests()
    yield rows
    with ai_calls._LOCK:
        rows.extend(ai_calls._Q)
    ai_calls._reset_for_tests()


def _queued():
    from core import ai_calls
    with ai_calls._LOCK:
        return list(ai_calls._Q)


def test_una_sola_puerta_solo_core_ai_escribe_ai_calls():
    rx = re.compile(r'ai_calls\.(begin|finish|submit|held)\(|aic\.(begin|finish|submit|held)\(')
    bad = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', 'vault', 'tests', '__pycache__')]
        for f in files:
            if not f.endswith('.py'):
                continue
            p = os.path.join(base, f)
            rel = os.path.relpath(p, ROOT)
            if rel in ('core/ai.py', 'core/ai_calls.py'):
                continue
            with open(p, encoding='utf-8', errors='ignore') as fh:
                if rx.search(fh.read()):
                    bad.append(rel)
    assert bad == [], f'solo core/ai.py escribe ai_calls: {bad}'


def test_fila_por_pedido_con_modelo_real_tokens_y_guardian(held_rows, monkeypatch):
    from core import ai, ai_usage

    def cascade(system, prompt, max_tokens=1000, tier='fast', model=None, want_json=False, timeout_s=None):
        ai_usage.record('claude', 'claude-haiku-4-5-20251001', 3000, 80, cache_read=2000, cache_write=0)
        return 'NVDA cerró en 181,20 USD.', 'claude-haiku-4-5-20251001'
    monkeypatch.setattr(ai, '_cascade', cascade)
    monkeypatch.setattr(ai_usage, '_ensure_writer', lambda: None)
    text, used = ai._ai_complete('sistema', 'DATOS: NVDA precio 181,20 USD', 200, live_facts=False)
    assert used == 'claude-haiku-4-5-20251001' and '181,20' in text
    rows = _queued()
    assert len(rows) == 1
    r = rows[0]
    assert r['provider'] == 'claude' and r['model'] == 'claude-haiku-4-5-20251001' and r['tier'] == 'fast'
    assert r['ok'] and r['tokens_in'] == 3000 and r['cache_read_tokens'] == 2000 and r['tokens_out'] == 80
    assert r['cost_usd'] == pytest.approx(ai_usage.cost_of('claude', 'claude-haiku-4-5', 3000, 80, cache_read=2000))
    assert r['guardian']['outcome'] == 'pass' and r['guardian']['attempt'] == 'first'
    assert r['retention_class'] == 'standard_90d' and r['decision_id'] is None


def test_guardian_reintento_deja_dos_filas_con_su_veredicto(held_rows, monkeypatch):
    from core import ai
    outs = iter([('El precio es 999 USD.', 'gemini:gemini-3.8-flash'), ('El precio es 181,20 USD.', 'gemini:gemini-3.8-flash')])
    monkeypatch.setattr(ai, '_cascade', lambda *a, **k: next(outs))
    text, _ = ai._ai_complete('s', 'DATOS: precio 181,20 USD', 200, live_facts=False)
    assert '181,20' in text
    rows = _queued()
    assert [r['guardian']['attempt'] for r in rows] == ['first', 'retry']
    assert all(r['guardian']['retried'] and r['guardian']['outcome'] == 'fixed' for r in rows)
    assert rows[0]['provider'] == 'gemini' and rows[0]['model'] == 'gemini:gemini-3.8-flash'


def test_fallo_de_la_cascada_deja_fila_ok_false(held_rows, monkeypatch):
    from core import ai

    def boom(*a, **k):
        raise RuntimeError('Ningún proveedor de IA respondió. claude: HTTP 529')
    monkeypatch.setattr(ai, '_cascade', boom)
    with pytest.raises(RuntimeError):
        ai._ai_complete_raw('s', 'p', 100)
    rows = _queued()
    assert len(rows) == 1 and rows[0]['ok'] is False and 'HTTP 529' in rows[0]['error'] and rows[0]['provider'] is None


def test_ping_y_ia_ocupada_no_dejan_fila(held_rows, monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, '_cascade', lambda *a, **k: ('ok', 'claude-x'))
    ai._ai_complete_raw('s', 'p', 2)                      # ping del 🩺 (≤ 4 tokens)

    def busy(*a, **k):
        raise ai.AIBusyError()
    monkeypatch.setattr(ai, '_cascade', busy)
    with pytest.raises(ai.AIBusyError):
        ai._ai_complete_raw('s', 'p', 100)
    assert _queued() == []


def test_atribucion_a_la_decision_y_herencia_en_el_pool(held_rows, monkeypatch):
    from core import ai, ai_calls, ai_usage
    monkeypatch.setattr(ai, '_cascade', lambda *a, **k: ('texto', 'claude-haiku-4-5'))
    did, ids = uuid.uuid4(), []
    with ai_calls.attribute(did, ids):
        ai._ai_complete_raw('s', 'p', 100)
        with ThreadPoolExecutor(1) as pool:      # como khipu_chat._submit_ai: el hilo hereda la atribución
            pool.submit(ai_usage.bind(lambda: ai._ai_complete_raw('s', 'p2', 100))).result()
    ai._ai_complete_raw('s', 'fuera', 100)
    rows = _queued()
    assert [r['decision_id'] for r in rows] == [str(did), str(did), None]
    assert ids == [str(rows[0]['id']), str(rows[1]['id'])]


def test_dentro_de_una_decision_sync_los_blobs_son_legales(held_rows, monkeypatch):
    from core import ai, ai_calls, decisions, identity
    monkeypatch.setattr(ai, '_cascade', lambda *a, **k: ('texto', 'claude-haiku-4-5'))
    ctx = decisions.DecisionCtx('committee.run', identity.system('test'))
    tok = decisions._CTX.set(ctx)
    try:
        ai._ai_complete_raw('s', 'p', 100)
    finally:
        decisions._CTX.reset(tok)
    r = _queued()[0]
    assert r['decision_id'] == str(ctx.id) and r['retention_class'] == 'legal'
    assert ai_calls.stats()['queued'] >= 1


def test_el_hilo_del_usuario_solo_encola(held_rows, monkeypatch):
    """Armar y encolar la fila cuesta microsegundos (los sha y los blobs se calculan en el hilo escritor)."""
    import time
    from core import ai_calls
    big_s, big_p = 'x' * 40000, 'y' * 40000
    t0 = time.perf_counter()
    for _ in range(200):
        r = ai_calls.begin(big_s, big_p, tier='fast', max_tokens=1600)
        ai_calls.submit(ai_calls.finish(r, text='z' * 2000, used='claude-haiku-4-5', acc={'tokens_in': 1, 'tokens_out': 1}))
    per_ms = (time.perf_counter() - t0) * 1000 / 200
    assert per_ms < 1.0, per_ms


def test_claude_system_largo_con_cache_control_y_corto_sin_cambios():
    from core import ai
    assert ai.claude_system('corto') == 'corto'
    assert ai.claude_system(None) == ''
    blk = ai.claude_system(LONG_SYSTEM)
    assert blk == [{'type': 'text', 'text': LONG_SYSTEM, 'cache_control': {'type': 'ephemeral'}}]


def test_claude_envia_cache_control_y_registra_la_cache_aparte(monkeypatch):
    """El SDK de Anthropic recibe el system con cache_control; usage.cache_* llega a ai_usage por separado."""
    import anthropic
    from core import ai, ai_usage
    seen = {}

    class U:
        input_tokens, output_tokens = 120, 30
        cache_creation_input_tokens, cache_read_input_tokens = 0, 1800

    class B:
        type, text = 'text', 'respuesta'

    class M:
        content, model, stop_reason, usage = [B()], 'claude-sonnet-5-5', 'end_turn', U()

    class Msgs:
        def create(self, **kw):
            seen.update(kw)
            return M()

    class C:
        def __init__(self, *a, **k):
            self.messages = Msgs()
    rec = []
    monkeypatch.setattr(anthropic, 'Anthropic', C)
    monkeypatch.setattr(ai_usage, 'record', lambda *a, **k: rec.append((a, k)))
    text, model = ai._complete_claude_inner(LONG_SYSTEM, 'pregunta', 400, 'deep')
    assert text == 'respuesta'
    assert seen['system'][0]['cache_control'] == {'type': 'ephemeral'} and seen['system'][0]['text'] == LONG_SYSTEM
    a, k = rec[0]
    assert a[2] == 120 + 1800 and k['cache_read'] == 1800 and k['cache_write'] == 0


def test_gemini_registra_la_cache_implicita(monkeypatch):
    from core import ai, ai_usage
    rec = []

    class R:
        status_code, ok = 200, True

        def json(self):
            return {'candidates': [{'content': {'parts': [{'text': 'hola'}]}, 'finishReason': 'STOP'}],
                    'usageMetadata': {'promptTokenCount': 5000, 'candidatesTokenCount': 40,
                                      'cachedContentTokenCount': 4096}}
    monkeypatch.setattr(ai, '_gemini_post', lambda *a, **k: R())
    monkeypatch.setattr(ai_usage, 'record', lambda *a, **k: rec.append((a, k)))
    text, used = ai._gemini_once('gemini-3.8-flash', 's', 'p', 100)
    assert text == 'hola' and rec[0][0][2] == 5000 and rec[0][1]['cache_read'] == 4096


# ── en la base ──────────────────────────────────────────────────────────────
@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    yield
    Base.metadata.drop_all(engine)


@needs_db
def test_en_la_base_append_only_sellada_y_sin_texto_en_claro(db, monkeypatch):
    from sqlalchemy import text

    from core import ai, ai_calls, ledger
    from ontology.db import session_scope
    ai_calls._reset_for_tests()
    monkeypatch.setattr(ai, '_cascade', lambda *a, **k: ('respuesta de la IA', 'claude-haiku-4-5'))
    from core.ai_usage import ai_context
    with ai_context('khipu_chat', 'Juan Pérez García'):
        for i in range(3):
            ai._ai_complete_raw(LONG_SYSTEM, f'pregunta {i}', 100)
    ai_calls.flush()             # (el hilo escritor pudo adelantarse: flush espera su lote en curso)
    with session_scope() as s:
        rows = s.execute(text('SELECT id, system_sha, system_blob, input_blob, output_blob, who_hash, feature, '
                              'prompt_sha FROM ai_calls ORDER BY seq')).all()
        assert len(rows) == 3 and len({r.system_blob for r in rows}) == 1        # el system se guarda UNA vez
        assert all(r.who_hash and 'Juan' not in r.who_hash for r in rows) and rows[0].feature == 'khipu_chat'
        body = s.execute(text('SELECT body, retention_class FROM decision_blobs WHERE sha256 = :b'),
                         {'b': rows[0].input_blob}).first()
        assert json.loads(zlib.decompress(bytes(body.body)))['prompt'] == 'pregunta 0'
        assert body.retention_class == 'standard_90d'
    with pytest.raises(Exception, match='append-only'):
        with session_scope() as s:
            s.execute(text("UPDATE ai_calls SET ok = false WHERE id = :i"), {'i': str(rows[0].id)})
    with pytest.raises(Exception, match='append-only'):
        with session_scope() as s:
            s.execute(text('DELETE FROM ai_calls'))
    out = ledger.seal()
    assert out.get('by_table', {}).get('ai_calls') == 3, out
    v = ledger.verify()
    assert v['ok'], v


@needs_db
def test_el_hilo_escritor_escribe_solo(db, monkeypatch):
    import time

    from sqlalchemy import text

    from core import ai, ai_calls
    from ontology.db import session_scope
    monkeypatch.setattr(ai, '_cascade', lambda *a, **k: ('x', 'claude-haiku-4-5'))
    with session_scope() as s:
        n0 = s.execute(text('SELECT count(*) FROM ai_calls')).scalar()
    ai._ai_complete_raw('s', 'hilo escritor', 100)
    t_end = time.time() + 6
    while time.time() < t_end:
        with session_scope() as s:
            if s.execute(text('SELECT count(*) FROM ai_calls')).scalar() == n0 + 1:
                break
        time.sleep(0.1)
    else:
        pytest.fail(f'el hilo escritor no escribió: {ai_calls.stats()}')
    assert any(t.name == 'ai-calls-writer' for t in threading.enumerate())


# ── revisión: los pedidos de UN proveedor (analistas, comité) también dejan fila ─────────────────────────────────
def test_research_coreprovider_deja_fila_y_hereda_el_id_reservado(held_rows, monkeypatch):
    """research/llm.CoreProvider llamaba a los proveedores directo (sin _ai_complete_raw): los analistas, el debate y
    el presidente del comité —lo más caro— no dejaban fila. Ahora pasan por core/ai._complete_single; dentro de
    decision_sites.ai_attributed(<id reservado>) la fila lleva ese decision_id con retención 'legal'."""
    from core import ai, ai_usage
    from core import decision_sites as ds
    from research.llm import CoreProvider

    def fake(system, prompt, max_tokens, tier='fast', model=None, **k):
        ai_usage.record('claude', 'claude-sonnet-5-5', 1200, 300)
        return '{"ok": 1}', 'claude-sonnet-5-5'
    monkeypatch.setitem(ai._AI_PROVIDERS, 'claude', (lambda: True, fake))
    monkeypatch.setattr(ai, 'circuit_open', lambda p: None)
    monkeypatch.setattr(ai_usage, '_ensure_writer', lambda: None)
    rid = ds.reserve_id()
    with ds.ai_attributed(rid) as ids:
        with ThreadPoolExecutor(1) as pool:           # como el pool de analistas del runner
            text, used = pool.submit(ai_usage.bind(
                lambda: CoreProvider('claude').generate('sys', 'research analyst prompt', 900))).result()
    CoreProvider('claude').generate('sys', 'sin decisión', 900)
    assert used == 'claude-sonnet-5-5' and text == '{"ok": 1}'
    rows = _queued()
    assert len(rows) == 2
    r = rows[0]
    assert r['prompt'] == 'research analyst prompt' and r['ok'] and r['route']['single'] == 'claude'
    assert r['model'] == 'claude-sonnet-5-5' and r['tier'] == 'deep' and r['tokens_in'] == 1200
    assert r['decision_id'] == str(rid) and r['retention_class'] == 'legal' and ids == [str(r['id'])]
    assert rows[1]['decision_id'] is None and rows[1]['retention_class'] == 'standard_90d'


def test_research_coreprovider_fallo_deja_fila_ok_false(held_rows, monkeypatch):
    from core import ai
    from research.llm import CoreProvider

    def boom(*a, **k):
        raise RuntimeError('HTTP 529 overloaded')
    monkeypatch.setitem(ai._AI_PROVIDERS, 'gemini', (lambda: True, boom))
    monkeypatch.setattr(ai, 'circuit_open', lambda p: None)
    with pytest.raises(RuntimeError):
        CoreProvider('gemini').generate('s', 'p', 500)
    rows = _queued()
    assert len(rows) == 1 and rows[0]['ok'] is False and '529' in rows[0]['error']
    assert rows[0]['route']['tried'] == ['gemini'] and rows[0]['route']['json'] is True
