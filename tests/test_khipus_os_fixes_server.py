"""tests/test_khipus_os_fixes_server.py — correcciones de la revisión de Khipus OS v1 (lado servidor).

Cada prueba FALLABA antes del arreglo (índice n de la revisión entre corchetes):
  [3]  /api/matrix/insights: la plantilla SIN IA de una IP sin presupuesto ya no se comparte con
       quien espera el mismo cálculo (calcula con SU presupuesto).
  [4]  research.committee.board: si la huella falla, la pizarra se arma en la MISMA sesión
       (savepoint) en vez de quedar con la transacción de Postgres abortada.
  [5]/[13] nota de la pizarra en agents_used: respeta `side`, cuenta lo MOSTRADO y no llama
       «la más favorable» a la menos negativa.
  [8]  nota de la pizarra: sin quórum, rechazado o vencido NO se muestra como veredicto vigente;
       la pizarra trae decision_code/expired y el chat los completa si la herramienta no los da.
  [11] las llamadas de IA del chat (hilos del pool) quedan atribuidas a 'khipu_chat'.
  [12] «hoy» solo con la sesión abierta; la hora mostrada es la del PRECIO (market_time).
Sin red y sin DATABASE_URL."""
import json
import os
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import khipu_chat as kc  # noqa: E402


# ════════════════════════════════════════════════════════════════════════════
# [3] /api/matrix/insights — solo se comparte lo cacheable
# ════════════════════════════════════════════════════════════════════════════
class _FakeSession:
    def execute(self, *a, **k):
        class _R:
            def all(self):
                return []
        return _R()


@contextmanager
def _fake_scope():
    yield _FakeSession()


@pytest.fixture
def insights_env(monkeypatch):
    import numpy as np

    import matrix.api as M
    import matrix.engine as E
    from core import http as h
    with h._rate_lock:
        h._rate_buckets.clear()
    monkeypatch.setattr(M, '_TTL_CACHE', {})
    monkeypatch.setattr(M, '_INFLIGHT', {})
    monkeypatch.setattr(M, '_db', lambda: _fake_scope)
    monkeypatch.setattr(E, '_graph_epoch', lambda s: 'EPOCH-FIX3')
    calls = {'build': 0, 'narrate': 0, 'persist': 0}

    def build_matrices(s, as_of=None):
        calls['build'] += 1
        time.sleep(0.5)                                   # el primero sigue armando cuando llega el 2.º
        ids = ['A', 'B', 'C']
        return {'supply': np.array([[0, 1, 0], [0, 0, 1], [0, 0, 0]], float)}, {k: i for i, k in enumerate(ids)}, ids

    def narrate(situation, lang, tier):
        calls['narrate'] += 1
        return [{'title': 'IA', 'detail': 'narrada', 'kind': 'estructura'}], 'fake:' + tier

    monkeypatch.setattr(E, 'build_matrices', build_matrices)
    monkeypatch.setattr(E, 'active_factors', lambda s, as_of=None: [])
    monkeypatch.setattr(E, 'fragility', lambda idx, factors: None)
    monkeypatch.setattr(E, 'propagate', lambda mats, idx, ids, shock, magnitude=1.0, frag=None:
                        ({'B': 1.0, 'C': 0.5}, [{'id': 'C', 'impact': 0.5, 'hop': 1}]))
    monkeypatch.setattr(M, '_narrate_insights', narrate)
    monkeypatch.setattr(M, '_persist_insight', lambda *a, **k: calls.__setitem__('persist', calls['persist'] + 1))

    # presupuesto de narración POR IP: la IP "sin-cupo" lo agotó, la otra no
    def compute_allowed(name, per_ip, glob=None):
        from flask import request
        return request.headers.get('X-Test-Ip') != 'sin-cupo'
    monkeypatch.setattr(M, '_compute_allowed', compute_allowed)
    from flask import Flask
    app = Flask('khipus_os_fix3')
    app.config['TESTING'] = True
    app.register_blueprint(M.matrix_bp)
    yield app, calls, M
    with h._rate_lock:
        h._rate_buckets.clear()


def _post_two(app, ips, gap=0.15):
    out = [None, None]

    def run(i):
        r = app.test_client().post('/api/matrix/insights', json={'lang': 'es'}, headers={'X-Test-Ip': ips[i]})
        out[i] = (r.status_code, r.get_json())
    ths = []
    for i in range(2):
        t = threading.Thread(target=run, args=(i,))
        t.start()
        ths.append(t)
        time.sleep(gap)
    for t in ths:
        t.join(timeout=20)
        assert not t.is_alive()
    return out


def test_fix3_plantilla_sin_ia_de_una_ip_no_se_comparte(insights_env):
    app, calls, M = insights_env
    leader, follower = _post_two(app, ['sin-cupo', 'con-cupo'])
    assert leader[0] == 200 and leader[1]['model'] == 'plantilla'          # su IP agotó el cupo
    assert follower[0] == 200
    # ANTES: recibía la plantilla del primero marcada cached/shared. AHORA calcula con SU cupo.
    assert follower[1]['model'] == 'fake:fast', follower[1]
    assert not follower[1].get('shared')
    assert calls['narrate'] == 1 and calls['persist'] == 1
    assert M._INFLIGHT == {}


def test_fix3_lo_narrado_si_se_sigue_compartiendo(insights_env):
    app, calls, M = insights_env
    a, b = _post_two(app, ['con-cupo', 'otra'])
    assert a[1]['model'] == b[1]['model'] == 'fake:fast'
    assert b[1].get('shared') is True and calls['narrate'] == 1 and calls['build'] == 1


def test_fix3_insights_build_marca_que_es_compartible(insights_env):
    _app, _calls, M = insights_env
    with _app.test_request_context('/api/matrix/insights', headers={'X-Test-Ip': 'sin-cupo'}):
        meta = {}
        p = M._insights_build(_fake_scope, 'E', 'ck-x', None, 'es', 'fast', None, meta=meta)
        assert p['model'] == 'plantilla' and meta['shareable'] is False
    with _app.test_request_context('/api/matrix/insights', headers={'X-Test-Ip': 'con-cupo'}):
        meta = {}
        p = M._insights_build(_fake_scope, 'E', 'ck-y', None, 'es', 'fast', None, meta=meta)
        assert p['model'] == 'fake:fast' and meta['shareable'] is True


# ════════════════════════════════════════════════════════════════════════════
# [4] pizarra: la huella que falla no envenena la transacción
# ════════════════════════════════════════════════════════════════════════════
class _InFailedSqlTransaction(Exception):
    pass


class _PgLikeSession:
    """Imita a Postgres: tras un error la transacción queda ABORTADA hasta un ROLLBACK (o un
    ROLLBACK TO SAVEPOINT si el error ocurrió dentro de begin_nested)."""

    def __init__(self, fail_fingerprint=True):
        self.aborted = False
        self.fail = fail_fingerprint
        self.savepoints = 0

    def _check(self):
        if self.aborted:
            raise _InFailedSqlTransaction('current transaction is aborted, commands ignored until end of '
                                          'transaction block')

    def query(self, *a, **k):
        self._check()
        return _PgLikeQuery(self)

    @contextmanager
    def begin_nested(self):
        self._check()
        self.savepoints += 1
        try:
            yield self
        except Exception:
            self.aborted = False                       # ROLLBACK TO SAVEPOINT: la transacción sigue viva
            raise


class _PgLikeQuery:
    def __init__(self, s):
        self.s = s

    def filter(self, *a, **k):
        return self

    def scalar_subquery(self):
        return self

    def one(self):
        self.s._check()
        if self.s.fail:
            self.s.aborted = True
            raise RuntimeError('QueryCanceled: canceling statement due to statement timeout')
        return (1, 2, 3, 4, 5, 6)


def test_fix4_huella_fallida_no_aborta_la_sesion(monkeypatch):
    import research.committee as rc
    rc.invalidate_board_cache()

    def uncached(session, limit=40):
        session.query('ResearchClaim')                  # la 1.ª consulta de la pizarra real
        return {'items': [], 'generated_at': 'x'}
    monkeypatch.setattr(rc, '_board_uncached', uncached)
    s = _PgLikeSession(fail_fingerprint=True)
    # ANTES: InFailedSqlTransaction (→ 500 en /api/committee/board, MCP get_conclusions_board roto)
    out = rc.board(s, limit=40)
    assert out == {'items': [], 'generated_at': 'x'}
    assert s.savepoints == 1 and s.aborted is False
    assert rc._board_fingerprint(_PgLikeSession(fail_fingerprint=False)) == ('1', '2', '3', '4', '5', '6')
    rc.invalidate_board_cache()


def test_fix4_tabla_que_falta_sigue_propagandose(monkeypatch):
    import research.committee as rc

    class _S(_PgLikeSession):
        def begin_nested(self):
            raise RuntimeError('UndefinedTable: relation "research_claims" does not exist')
    with pytest.raises(RuntimeError):
        rc._board_fingerprint(_S())


# ════════════════════════════════════════════════════════════════════════════
# [5]/[13] nota de la pizarra: side, conteo de lo MOSTRADO
# ════════════════════════════════════════════════════════════════════════════
BOARD_SRC = 'Khipus research claims + committee memos'


def _board(items):
    return {'items': items, 'n': len(items), 'source': BOARD_SRC, 'as_of': '2026-10-06T10:00:00+00:00'}


def test_fix5_13_desfavorables_nombra_la_mas_en_contra():
    res = _board([{'entity_id': 'Intel', 'label': 'Intel', 'conviction': -62.0},
                  {'entity_id': 'AMD', 'label': 'AMD', 'conviction': -8.5}])
    es, en, src, _ = kc._note_board(res, {'side': 'unfavorable', 'limit': 2}, {})
    assert 'más favorable' not in es and 'most favorable' not in en
    assert es == '2 empresas en contra mostradas; la más en contra: Intel (-62,0)'
    assert en == '2 unfavorable companies shown; most unfavorable: Intel (-62.0)'
    assert src == BOARD_SRC


def test_fix5_13_conteo_es_lo_mostrado_no_la_pizarra():
    items = [{'entity_id': f'E{i}', 'label': f'E{i}', 'conviction': 50.0 - i} for i in range(20)]
    es, en, _s, _a = kc._note_board(_board(items), {}, {})
    assert 'en la pizarra' not in es and 'on the board' not in en
    assert es == '20 empresas de la pizarra mostradas; la más favorable: E0 (+50,0)'
    assert en == '20 board companies shown; most favorable: E0 (+50.0)'


def test_fix5_13_todas_negativas_no_se_llama_favorable():
    res = _board([{'entity_id': 'A', 'label': 'A', 'conviction': -3.0},
                  {'entity_id': 'B', 'label': 'B', 'conviction': -30.0}])
    es, en, _s, _a = kc._note_board(res, {'side': 'all'}, {})
    assert es == '2 empresas de la pizarra mostradas; la de mayor convicción: A (-3,0)'
    assert en == '2 board companies shown; highest conviction: A (-3.0)'


def test_fix5_13_filtro_vacio_no_dice_pizarra_vacia():
    es, en, _s, _a = kc._note_board(_board([]), {'side': 'unfavorable'}, {})
    assert 'vacía' not in es and 'empty' not in en
    assert es == 'Ninguna empresa de la pizarra tiene convicción en contra'
    assert en == 'No company on the board has negative conviction'
    es, en, _s, _a = kc._note_board(_board([]), {}, {})
    assert es == 'La pizarra está vacía: todavía no hay investigación'


# ════════════════════════════════════════════════════════════════════════════
# [8] comité en la nota de la pizarra: sin quórum / rechazado / vencido
# ════════════════════════════════════════════════════════════════════════════
def _nv(committee):
    return _board([{'entity_id': 'Nvidia', 'label': 'Nvidia', 'conviction': 12.3, 'committee': committee}])


def test_fix8_rechazado_no_es_veredicto_vigente():
    now = datetime.now(timezone.utc).isoformat()
    es, en, _s, _a = kc._note_board(_nv({'decision': 'BUY', 'status': 'rejected', 'date': now,
                                         'decision_code': None, 'expired': False}), {}, {'primary': 'Nvidia'})
    assert es == 'Convicción de los agentes en Nvidia: +12,3 · comité: propuesta de comprar rechazada'
    assert en == "Agents' conviction on Nvidia: +12.3 · committee: proposal to buy rejected"


def test_fix8_sin_quorum_no_dice_mantener():
    now = datetime.now(timezone.utc).isoformat()
    es, en, _s, _a = kc._note_board(_nv({'decision': 'HOLD', 'status': 'proposed', 'date': now,
                                         'decision_code': 'INSUFFICIENT_DATA', 'expired': False}), {},
                                    {'primary': 'Nvidia'})
    assert 'mantener' not in es and 'hold' not in en.lower()
    assert es.endswith('· comité: sin veredicto (datos insuficientes)')
    assert en.endswith('· committee: no verdict (insufficient data)')


def test_fix8_vencido_se_marca_con_su_fecha_aunque_la_herramienta_no_traiga_expired():
    old = (datetime.now(timezone.utc) - timedelta(days=35)).replace(microsecond=0)
    es, en, _s, _a = kc._note_board(_nv({'decision': 'BUY', 'status': 'approved', 'date': old.isoformat()}), {},
                                    {'primary': 'Nvidia'})
    d = old.date().isoformat()
    assert es == f'Convicción de los agentes en Nvidia: +12,3 · comité: comprar · memo vencido ({d})'
    assert en == f"Agents' conviction on Nvidia: +12.3 · committee: buy · expired memo ({d})"
    # vigente: sin marca (y sin cambiar el texto de siempre)
    fresh = datetime.now(timezone.utc).isoformat()
    es, _en, _s, _a = kc._note_board(_nv({'decision': 'BUY', 'status': 'proposed', 'date': fresh}), {},
                                     {'primary': 'Nvidia'})
    assert es == 'Convicción de los agentes en Nvidia: +12,3 · comité: comprar'


class _Q:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def all(self):
        return list(self.rows)


class _BoardSession:
    def __init__(self, claims, memos):
        self.claims, self.memos = claims, memos

    def query(self, model, *a):
        from research.models import ClaimRelation, CommitteeMemo, ResearchClaim
        return _Q({ResearchClaim: self.claims, ClaimRelation: [], CommitteeMemo: self.memos}[model])


def test_fix8_pizarra_trae_decision_code_y_vencimiento(monkeypatch):
    import research.committee as rc
    import research.outcomes as ro
    monkeypatch.setattr(ro, 'calibration_table', lambda session=None, force=False: {})
    monkeypatch.setattr(rc, '_resolve_entity', lambda e: (e, {'label': e}))
    now = datetime.now(timezone.utc)
    claims = [SimpleNamespace(id=f'c{i}', subject_entity_id=e, created_at=now - timedelta(hours=i),
                              agent_type='fundamental', stance='positive', horizon='LONG_TERM', confidence=0.7,
                              statement_es='x', statement_en='x') for i, e in enumerate(('Nvidia', 'AMD'))]
    memos = [SimpleNamespace(id='m1', entity_id='Nvidia', decision='HOLD', status='proposed', created_at=now,
                             memo={'decision_code': 'INSUFFICIENT_DATA'}),
             SimpleNamespace(id='m2', entity_id='AMD', decision='BUY', status='approved',
                             created_at=now - timedelta(days=30), memo={})]
    out = rc._board_uncached(_BoardSession(claims, memos), limit=10)
    by = {x['entity_id']: x['memo'] for x in out['items']}
    assert by['Nvidia']['decision_code'] == 'INSUFFICIENT_DATA' and by['Nvidia']['expired'] is False
    assert by['AMD']['decision_code'] is None and by['AMD']['expired'] is True and by['AMD']['expires_at']


def test_fix8_el_chat_completa_lo_que_la_herramienta_no_trae(monkeypatch):
    """get_conclusions_board (MCP) no pasa decision_code/expired: el chat los toma de la MISMA
    pizarra (misma fecha de memo) para que la nota no diga «comité: mantener» sin quórum."""
    import research.committee as rc
    from mcp_server import tools as mt
    date = '2026-10-06T09:00:00+00:00'
    tool_out = _board([{'entity_id': 'Nvidia', 'label': 'Nvidia', 'conviction': 12.3,
                        'committee': {'decision': 'HOLD', 'status': 'proposed', 'date': date,
                                      'ai_debate': False, 'conclusion': None}},
                       {'entity_id': 'AMD', 'label': 'AMD', 'conviction': 5.0,
                        'committee': {'decision': 'BUY', 'status': 'proposed', 'date': 'otra-fecha'}}])
    monkeypatch.setattr(mt, 'call', lambda name, args, ctx: json.loads(json.dumps(tool_out)))

    class _S:
        def __enter__(self):
            return 'S'

        def __exit__(self, *a):
            return False
    monkeypatch.setattr('ontology.db.session_scope', lambda: _S())
    monkeypatch.setattr(rc, 'board', lambda s, limit=40: {'items': [
        {'entity_id': 'Nvidia', 'memo': {'created_at': date, 'decision_code': 'INSUFFICIENT_DATA', 'expired': False,
                                         'expires_at': '2026-10-09T09:00:00+00:00'}},
        {'entity_id': 'AMD', 'memo': {'created_at': '2026-09-01T00:00:00+00:00', 'decision_code': None,
                                      'expired': True}}]})
    ok, res = kc.execute_tool('get_conclusions_board', {})
    assert ok
    nv, amd = res['items'][0]['committee'], res['items'][1]['committee']
    assert nv['decision_code'] == 'INSUFFICIENT_DATA' and nv['expired'] is False
    assert 'decision_code' not in amd                       # otro memo (otra fecha): no se mezcla
    es, _en, _s, _a = kc._note_board(res, {}, {'primary': 'Nvidia'})
    assert es.endswith('· comité: sin veredicto (datos insuficientes)')
    # sin base: la herramienta sigue funcionando igual
    monkeypatch.setattr('ontology.db.session_scope', lambda: (_ for _ in ()).throw(RuntimeError('sin base')))
    ok, res2 = kc.execute_tool('get_conclusions_board', {})
    assert ok and 'decision_code' not in res2['items'][0]['committee']


# ════════════════════════════════════════════════════════════════════════════
# [11] la IA del chat se atribuye a 'khipu_chat' (no a 'fondo')
# ════════════════════════════════════════════════════════════════════════════
def test_fix11_ia_del_chat_atribuida_a_khipu_chat(monkeypatch):
    from flask import Flask

    from core import ai as core_ai
    from core import ai_usage, live_facts
    from core import http as h
    from mcp_server import tools as mt
    monkeypatch.setattr(mt, '_live_profile', lambda sym: {'available': False, 'symbol': sym})
    monkeypatch.setattr(mt._auth, 'db_available', lambda: False)
    monkeypatch.setattr(live_facts, 'live_facts_block', lambda text, *a, **k: '')
    seen = []

    def fake(system, prompt, max_tokens=1000, tier='fast', model=None, verify_numbers=True, **kw):
        seen.append(dict(ai_usage.current(), thread=threading.current_thread().name))
        return json.dumps({'final': {'answer': 'El VaR mide la pérdida probable.', 'actions': []}}), 'fake:model'
    monkeypatch.setattr(core_ai, '_ai_complete', fake)
    monkeypatch.setattr(core_ai, '_ai_configured', lambda: True)
    with h._rate_lock:
        h._rate_buckets.clear()
    app = Flask('khipus_os_fix11')
    app.register_blueprint(kc.khipu_chat_bp)
    r = app.test_client().post('/api/khipu/chat', json={'message': '¿qué es el VaR?', 'lang': 'es',
                                                        'actor': 'Fabrizio'})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert seen, 'la IA no se llamó'
    assert all(x['thread'].startswith('khipu-chat') for x in seen)          # sí corre en el pool
    # ANTES: {'feature': 'fondo', 'who': 'sistema'} → la tarjeta de Khipu decía «sin actividad»
    assert all(x['feature'] == 'khipu_chat' for x in seen), seen
    assert all(x['who'] == 'Fabrizio' for x in seen), seen


def test_fix11_submit_ai_lleva_el_contexto_del_que_pide():
    from flask import Flask

    from core import ai_usage
    app = Flask('khipus_os_fix11b')
    with app.test_request_context('/api/khipu/chat', method='POST', json={'actor': 'ana'}):
        got = kc._submit_ai(ai_usage.current).result(timeout=5)
    assert got == {'feature': 'khipu_chat', 'who': 'ana'}
    with ai_usage.ai_context('riesgo_cartera', 'bob'):              # el informe de cartera usa run_chat
        got = kc._submit_ai(ai_usage.current).result(timeout=5)
    assert got == {'feature': 'riesgo_cartera', 'who': 'bob'}


# ════════════════════════════════════════════════════════════════════════════
# [12] «hoy» solo con la sesión abierta; hora = la del precio
# ════════════════════════════════════════════════════════════════════════════
FRI_CLOSE = '2026-10-02T20:00:00Z'


def _company(**lm):
    base = {'available': True, 'price': 182.35, 'change_pct': 1.234, 'currency': 'USD', 'source': 'yahoo',
            'as_of': '2026-10-04T10:00:00+00:00'}
    base.update(lm)
    return {'id': 'Nvidia', 'label': 'Nvidia', 'listed': True, 'live_market': base,
            'network_risk_score': {'value': 40}, 'as_of': '2026-10-04T10:00:00+00:00'}


def test_fix12_cierre_del_viernes_no_es_hoy():
    res = _company(market_state='CLOSED', market_time=FRI_CLOSE)
    es, en, src, as_of = kc._note_company(res, {}, {})
    assert 'hoy' not in es and 'today' not in en
    assert 'Nvidia: 182,35 USD (+1,23 % vs. cierre anterior, sesión del 2026-10-02)' in es
    assert 'Nvidia: 182.35 USD (+1.23% vs. prior close, session of 2026-10-02)' in en
    assert src == 'Yahoo Finance' and as_of == FRI_CLOSE                 # la hora del PRECIO, no la consulta
    card = kc._company_card(res)
    assert card['as_of'] == FRI_CLOSE and card['market_state'] == 'CLOSED' and card['session_live'] is False
    srcs = []
    kc._collect_sources('get_company', res, srcs, 'es')
    live = [x for x in srcs if x['label'].endswith('(live)')]
    assert live and live[0]['as_of'] == FRI_CLOSE


def test_fix12_sesion_abierta_si_dice_hoy():
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    es, en, _src, as_of = kc._note_company(_company(market_state='REGULAR', market_time=now), {}, {})
    assert '(+1,23 % hoy)' in es and '(+1.23% today)' in en and as_of == now
    # sin estado (Finnhub / gráfico de Yahoo): decide la hora real del precio
    es, _en, _s, _a = kc._note_company(_company(market_time=now), {}, {})
    assert '(+1,23 % hoy)' in es
    es, _en, _s, _a = kc._note_company(_company(market_time=FRI_CLOSE), {}, {})
    assert 'sesión del 2026-10-02' in es and 'hoy' not in es


def test_fix12_respaldo_sin_ia_tampoco_dice_hoy():
    res = _company(market_state='PRE', market_time=FRI_CLOSE)
    es = kc.company_summary(res, 'es')
    en = kc.company_summary(res, 'en')
    assert '% hoy' not in es and '(+1.23 % vs. cierre anterior, sesión del 2026-10-02)' in es
    assert '% today' not in en and '(+1.23 % vs. prior close, session of 2026-10-02)' in en


def test_fix12_movers_fuera_de_sesion_dicen_ultima_sesion(monkeypatch):
    import core.live_caps as lc
    ts = int(datetime(2026, 10, 2, 20, 0, tzinfo=timezone.utc).timestamp())
    monkeypatch.setattr(lc, 'get_caps', lambda: {'as_of': '2026-10-04T10:00:00+00:00', 'caps': {
        'Nvidia': {'change_pct': 2.5, 'price': 182.35, 'currency': 'USD', 'mcap_b': 4470.0, 'symbol': 'NVDA',
                   'market_state': 'CLOSED', 'price_ts': ts},
        'AMD': {'change_pct': -1.2, 'price': 160.0, 'currency': 'USD', 'mcap_b': 260.0, 'symbol': 'AMD',
                'market_state': 'CLOSED', 'price_ts': ts}}})
    res = kc.x_market_movers('up', 5)
    row = res['items'][0]
    assert row['market_state'] == 'CLOSED' and row['market_time'] == FRI_CLOSE
    es, en, _s, _a = kc._note_movers(res, {}, {})
    assert es.startswith('Más suben (última sesión): ') and en.startswith('Top gainers (last session): ')
    assert 'hoy' not in es and 'today' not in en
    # con la sesión abierta sigue diciendo «hoy»
    for r in res['items']:
        r['market_state'] = 'REGULAR'
    es, en, _s, _a = kc._note_movers(res, {}, {})
    assert es.startswith('Más suben hoy: ') and en.startswith('Top gainers today: ')
