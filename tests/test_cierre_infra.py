"""tests/test_cierre_infra.py — auditoría de cierre de la infraestructura operativa (docs/CIERRE_INFRA.md).

Fija la lista de RUTAS DE ESCRITURA (POST/PUT/PATCH/DELETE) y de TIPOS DE DECISIÓN, para que nada nuevo quede fuera del
libro de decisiones sin que alguien lo decida a propósito:

  1. Toda ruta de escritura del servidor está clasificada: o deja una decisión (CON_DECISION, con su tipo) o está en
     SIN_DECISION con su motivo. Una ruta NUEVA sin clasificar rompe la CI: hay que darle su decisión
     (core/decisions.decision_scope / submit_async) o justificar por qué no la necesita.
  2. Las BRECHAS (rutas que cambian algo y todavía no dejan decisión) solo pueden achicarse: una brecha nueva rompe la
     CI; cerrar una brecha = mover la ruta a CON_DECISION.
  3. Los tipos del vocabulario (core/decisions.KINDS) que ningún código escribe solo pueden achicarse.
  4. Con base (DATABASE_URL): una muestra de rutas CON_DECISION deja de verdad >= 1 decisión del tipo esperado (incluye
     las brechas E1/E4 que el lote H cerró; las que quedan abiertas no cambian el grafo ni el dinero).

Sin red y sin IA real. Solo lectura del código salvo la base desechable de la prueba (drop/create como las demás).
"""
import glob
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = '4321'
WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

# ── 1. Rutas que dejan decisión (tipo/s que escriben) ─────────────────────────────────────────────────────────────
CON_DECISION = {
    'POST /api/ai/usage/limits': 'policy.change (ai.spend_limits)',
    'POST /api/brokerage/approvals/<preview_id>/approve': 'approval.grant → order.confirm/order.submit',
    'POST /api/brokerage/approvals/<preview_id>/reject': 'approval.deny',
    'POST /api/brokerage/clients': 'policy.change (broker.client_limits)',
    'PATCH /api/brokerage/clients/<client_id>': 'policy.change (broker.client_limits / client_account)',
    'POST /api/brokerage/clients/<client_id>/credentials': 'policy.change (broker.client_account)',
    'POST /api/brokerage/orders/<order_id>/cancel': 'order.cancel',
    'POST /api/brokerage/orders/<preview_id>/confirm': 'order.confirm → order.submit',
    'POST /api/brokerage/orders/preview': 'order.preview',
    'POST /api/committee/board/refresh': 'committee.run (uno por empresa refrescada)',
    'POST /api/committee/memo/<memo_id>/approve': 'approval.grant',
    'POST /api/committee/memo/<memo_id>/reject': 'approval.deny',
    'POST /api/committee/outcomes/evaluate': 'claim.status + decision_outcomes (si algo cambia)',
    'POST /api/committee/portfolio': 'committee.portfolio_advice (async)',
    'POST /api/committee/portfolio/ask': 'committee.portfolio_advice (async, si hubo respuesta)',
    'POST /api/committee/run': 'committee.run',
    'POST /api/governance/activate': 'governance.activate',
    'POST /api/governance/cancel': 'governance.activate (cancelación)',
    'POST /api/governance/propose': 'governance.propose',
    'POST /api/governance/ratify': 'governance.ratify',
    'POST /api/governance/validate': 'governance.validate',
    'POST /api/hot/scenario': 'whatif.shock (async)',
    'POST /api/hot/scenario_pnl': 'whatif.shock (async; record:false solo en la vista automática del X-Ray)',
    'POST /api/khipu/chat': 'chat.answer + chat.route (async)',
    'POST /api/ledger/chain_ack': 'ledger.chain_ack',
    'POST /api/ledger/replay/<decision_id>': 'audit.replay (async) + decision_outcomes replay (paso 24)',
    'POST /api/matrix/factor/fire': 'whatif.factor_fire (async)',
    'POST /api/matrix/impact': 'whatif.shock (async)',
    'POST /api/matrix/insights': 'insight.snapshot (async)',
    'POST /api/matrix/simulations': 'simulation.save (cierre del lote H, E4)',
    'POST /api/ontology/actions/<action_type>': 'ontology.action',
    'POST /api/ontology/agents/cycle': 'proposal.create / proposal.auto_apply (en su hilo)',
    'POST /api/ontology/agents/investigar': 'proposal.create',
    'POST /api/ontology/agents/proposals/<proposal_id>/approve': 'approval.grant + ontology.action',
    'POST /api/ontology/agents/proposals/<proposal_id>/reject': 'approval.deny',
    'POST /api/ontology/agents/run': 'proposal.create / proposal.auto_apply',
    'POST /api/ontology/alerts': 'alert.rule',
    'DELETE /api/ontology/alerts/<alert_id>': 'alert.rule',
    'POST /api/ontology/bulk/import': 'ontology.bulk_import',
    'POST /api/ontology/events': 'ontology.raw_event (cierre del lote H, E1)',
    'POST /api/ontology/ingest/news': 'ontology.news_ingest (cierre del lote H, E3)',
    'POST /api/ontology/reconcile/apply': 'reconcile.apply (una por categoría; cierre del lote H, E2)',
    'POST /api/ontology/reconcile/rollback': 'reconcile.rollback (cierre del lote H, E2)',
    'POST /api/ontology/import/files': 'ontology.bulk_import (etapa upload: guarda el archivo en import_files; lote K, E2.4)',
    'POST /api/ontology/import/apply': 'ontology.bulk_import (UNA por corrida; lote K, E2.4)',
    'POST /api/ontology/import/rollback': 'ontology.import_rollback (lote K, E2.4)',
    'POST /api/portfolio-report/ask': 'chat.answer (async)',
    'POST /api/prices/backfill': 'data.backfill',
    'POST /api/prices/backfill/stop': 'data.backfill',
    'POST /api/research/events': 'research.job',
    'POST /api/research/jobs': 'research.job',
    'POST /api/trade/agent/config': 'policy.change (trading_agent)',
    'POST /api/trade/agent/start': 'policy.change (trading_agent)',
    'POST /api/trade/agent/stop': 'policy.change (trading_agent)',
    'POST /api/trade/close': 'order.preview → order.confirm → order.submit',
    'POST /api/trade/order': 'order.preview → order.confirm → order.submit',
    'POST /mcp': 'mcp.tool_call (async; órdenes: order.* sync)',
    # lote I4 (Fase 2+): la administración de la voz (ANTES de llamar a ElevenLabs; resultado en decision_outcomes)
    'POST /api/voice/adopt': 'policy.change (voice.agent: ids públicos de la voz, nunca la clave)',
    'POST /api/voice/agent-tune': 'policy.change (voice.agent: modelo/voz/idioma con el valor anterior si está en caché)',
    'POST /api/voice/sync-agent': 'policy.change (voice.agent: huella del prompt + nombres de herramientas)',
    # lote I1 (Fase 2+): las últimas brechas fuera de la voz
    'POST /api/sim/agents': 'whatif.agent_sim (async)',
    'POST /api/mcp/tokens': 'policy.change (mcp.tokens: id + alcances, nunca el secreto)',
    'POST /api/mcp/tokens/<token_id>/revoke': 'policy.change (mcp.tokens)',
    'POST /oauth/register': 'policy.change (mcp.oauth: cliente + alcances)',
    'POST /oauth/authorize': 'policy.change (mcp.oauth: consentimiento tras el PIN; nunca el código)',
    'POST /oauth/token': 'policy.change (mcp.oauth: canje sync; rotación del refresh async)',
    'POST /oauth/revoke': 'policy.change (mcp.oauth)',
}

# ── 2. Rutas sin decisión, con su motivo ─────────────────────────────────────────────────────────────────────────
# categoría: lectura (calcula y responde, no cambia nada) · ia (respuesta de IA: queda solo en ai_calls) ·
# personal (datos privados del dueño del navegador, D3) · sesion (credencial técnica de sesión) ·
# telemetria (chequeo de salud / diagnóstico: escribe su propia fila de control, no toca el grafo ni el dinero) ·
# resultado (actualiza resultados de decisiones existentes) · v1 (API pública monetizada: intocable) ·
# brecha (CAMBIA algo y todavía no deja decisión: pendiente, ver docs/CIERRE_INFRA.md)
SIN_DECISION = {
    'POST /api/quotes/live': 'lectura',
    'POST /api/ontology/import/plan': 'lectura',   # plan PURO (lote K, E2.3): no escribe nada
    'POST /api/news/portfolio': 'lectura',
    'POST /api/portfolio/risk_report': 'lectura',
    'POST /api/portfolio/vega_report': 'lectura',
    'POST /api/portfolio-risk': 'lectura',
    'POST /api/tensor/suggest': 'lectura',
    'POST /api/ai/analyze': 'ia',
    'POST /api/canvas/generate': 'ia',
    'POST /api/crypto/analyze': 'ia',
    'POST /api/deep/analyze': 'ia',
    'POST /api/thesis/quick': 'ia',
    'POST /api/portfolio/advice': 'ia',
    'POST /api/portfolio/comment': 'ia',
    'POST /api/portfolio-ai/ask': 'ia',
    'POST /api/portfolio-ai/propose': 'ia',
    'PUT /api/user-state': 'personal',
    'POST /api/portfolio-report/generate': 'personal',
    'POST /api/portfolio-report/watch': 'personal',
    'DELETE /api/portfolio-report/<rid>': 'personal',
    'POST /api/diag': 'sesion',
    'POST /api/ws-key': 'sesion',
    'POST /api/voice/session': 'sesion',
    'DELETE /mcp': 'sesion',
    'POST /api/brokerage/clients/<client_id>/oauth/start': 'sesion',      # la cuenta queda en el callback (policy.change)
    'POST /api/brokerage/clients/<client_id>/sync': 'resultado',          # broker_fills + decision_outcomes
    'POST /api/ops/check': 'telemetria',                                  # una fila ops_checks, ninguna decision_outcome
    'POST /v1/auth/key': 'v1',
    'POST /v1/risk/portfolio': 'v1',
    # ── brechas abiertas (docs/CIERRE_INFRA.md §3) ──
    # (lote I1: /api/sim/agents, /api/mcp/tokens[/<id>/revoke] y /oauth/* ya dejan decisión → CON_DECISION)
    # (lote I4: /api/voice/adopt|agent-tune|sync-agent ya dejan policy.change voice.agent → CON_DECISION)
    # 'POST /api/grafo/seed' (escribía en Neo4j) se BORRÓ el 2026-10-13 con Neo4j (decisión #6): brecha cerrada.
}
CATEGORIAS = {'lectura', 'ia', 'personal', 'sesion', 'telemetria', 'resultado', 'v1', 'brecha'}
# Foto de las brechas al cierre (2026-10-13, tras cerrar E1-E4; sin POST /api/grafo/seed desde que se retiró Neo4j):
# la lista de arriba solo puede quedarse con un SUBCONJUNTO de esta.
BRECHAS_AL_CIERRE = frozenset((
    'POST /api/sim/agents',
    'POST /api/mcp/tokens', 'POST /api/mcp/tokens/<token_id>/revoke', 'POST /oauth/authorize', 'POST /oauth/register',
    'POST /oauth/token', 'POST /oauth/revoke', 'POST /api/voice/adopt', 'POST /api/voice/agent-tune',
    'POST /api/voice/sync-agent'))
BRECHAS_CONOCIDAS = {k for k, v in SIN_DECISION.items() if v == 'brecha'}

# ── 3. Tipos del vocabulario sin ningún escritor en el código (solo pueden achicarse) ────────────────────────────
KINDS_SIN_ESCRITOR_CONOCIDOS = {
    'reconcile.plan',          # ver el plan es una LECTURA (GET); el tipo queda en ledger.kinds para un plan guardado
}


def _write_routes():
    import server
    out = set()
    for r in server.app.url_map.iter_rules():
        for m in sorted((r.methods or set()) & WRITE_METHODS):
            out.add(f'{m} {r.rule}')
    return out


def test_toda_ruta_de_escritura_esta_clasificada():
    routes = _write_routes()
    assert not set(CON_DECISION) & set(SIN_DECISION), 'una ruta no puede estar en las dos listas'
    assert set(SIN_DECISION.values()) <= CATEGORIAS
    nuevas = sorted(routes - set(CON_DECISION) - set(SIN_DECISION))
    assert not nuevas, (
        'Ruta(s) de escritura NUEVA(S) sin clasificar: ' + ', '.join(nuevas) + '. Toda acción debe dejar su decisión '
        '(core/decisions.decision_scope o submit_async) → añádela a CON_DECISION con su tipo; si de verdad no cambia '
        'nada (lectura, sesión, datos personales) añádela a SIN_DECISION con su motivo. Ver docs/CIERRE_INFRA.md.')
    viejas = sorted((set(CON_DECISION) | set(SIN_DECISION)) - routes)
    assert not viejas, 'Rutas listadas que ya no existen (quítalas de la lista): ' + ', '.join(viejas)


def test_las_brechas_solo_se_achican():
    nuevas = BRECHAS_CONOCIDAS - BRECHAS_AL_CIERRE
    assert not nuevas, ('Brecha(s) NUEVA(S) (rutas que cambian algo sin decisión): ' + ', '.join(sorted(nuevas))
                        + ' — dales su decisión en vez de sumarlas a la lista.')


def _kinds_with_writer():
    from core.decisions import KINDS
    files = [f for f in glob.glob(os.path.join(ROOT, '**', '*.py'), recursive=True)
             if os.sep + 'tests' + os.sep not in f and os.sep + 'vault' + os.sep not in f
             and os.sep + 'scripts' + os.sep not in f and not f.endswith(os.path.join('core', 'decisions.py'))]
    text = ''.join(open(f, encoding='utf-8', errors='ignore').read() for f in files)
    # Una ETIQUETA de un diccionario ('kind': ('texto ES', 'text EN'), p. ej. core/replay.py) no es un escritor: se
    # descarta el uso seguido de «: (» para que nombrar un tipo en la UI no esconda que nadie lo escribe.
    return {k for k in KINDS
            if re.search(r"['\"]" + re.escape(k) + r"['\"](?!\s*:\s*\()", text)}, set(KINDS)


def test_tipos_de_decision_sin_escritor_solo_se_achican():
    with_writer, kinds = _kinds_with_writer()
    sin = kinds - with_writer
    nuevos = sin - KINDS_SIN_ESCRITOR_CONOCIDOS
    assert not nuevos, ('Tipo(s) de decisión del vocabulario que ningún código escribe: ' + ', '.join(sorted(nuevos))
                        + ' — o se escriben, o se quitan de ledger.kinds con su versión de gobernanza.')


# ── 4. Comprobación con base: la muestra deja de verdad su decisión ────────────────────────────────────────────────
@pytest.fixture(scope='module')
def db():
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import brokerage.models  # noqa: F401
    import mcp_server.models  # noqa: F401
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db, monkeypatch):
    import requests

    def _offline(*_a, **_k):
        raise requests.ConnectionError('sin red en la prueba')
    for name in ('request', 'get', 'post', 'delete'):
        monkeypatch.setattr(requests, name, _offline)
    monkeypatch.setenv('TRADE_PIN', PIN)
    import ontology.db as odb
    import server
    from core import http as h
    from core.hotviews import builder, registry
    real = odb.ontology_available
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    registry.reset()
    builder.build_once()                       # vistas del snapshot (la base de la prueba está vacía)
    monkeypatch.setattr(odb, 'ontology_available', real)
    with h._rate_lock:
        h._rate_buckets.clear()
    yield server.app.test_client()
    registry.reset()


def _counts():
    from sqlalchemy import text
    from core import decisions
    from ontology.db import session_scope
    decisions.flush_async(timeout=10)
    with session_scope() as s:
        return {r[0]: r[1] for r in s.execute(text('SELECT kind, count(*) FROM decisions GROUP BY kind'))}


def _delta(before, after):
    return {k: after.get(k, 0) - before.get(k, 0) for k in set(after) | set(before) if after.get(k, 0) != before.get(k, 0)}


H = {'X-Trade-Pin': PIN, 'X-Khipu-Owner': 'cierre-infra-owner-0001'}

MUESTRA = [
    ('POST', '/api/hot/scenario', {'shocks': ['TSMC']}, 'whatif.shock'),
    ('POST', '/api/hot/scenario_pnl', {'shocks': ['TSMC'], 'positions': [{'id': 'Nvidia', 'usd': 1000}]},
     'whatif.shock'),
    ('POST', '/api/ontology/alerts', {'owner': 'cierre-infra-owner-0001',
                                      'rule': {'entity': 'Nvidia', 'metric': 'price', 'op': '>', 'value': 1000}},
     'alert.rule'),
    ('POST', '/api/ontology/bulk/import', {'actor': 'pytest', 'links': []}, 'ontology.bulk_import'),
    ('POST', '/api/ai/usage/limits', {'actor': 'pytest', 'limits': {'daily_usd': 3.5}}, 'policy.change'),
    # brechas E1 y E4 cerradas en el lote H (antes eran xfail: el evento se escribía y el libro no se enteraba)
    ('POST', '/api/ontology/events', {'actor': 'pytest', 'event_type': 'ObjectCreated', 'object_id': 'CierreInfraObj',
                                      'valid_from': '2026-10-13', 'source': 'pytest',
                                      'payload': {'label': 'Cierre', 'type': 'Company', 'properties': {}}},
     'ontology.raw_event'),
    ('POST', '/api/matrix/simulations', {'name': 'cierre', 'targets': ['TSMC'], 'affected': 3}, 'simulation.save'),
]


@needs_db
@pytest.mark.parametrize('method,url,body,kind', MUESTRA, ids=[m[1] for m in MUESTRA])
def test_la_muestra_con_decision_la_deja_de_verdad(client, method, url, body, kind):
    assert f'{method} {url}' in CON_DECISION or any(
        re.fullmatch(re.sub(r'<[^>]+>', '[^/]+', k.split(' ', 1)[1]), url) for k in CON_DECISION if k.startswith(method))
    before = _counts()
    r = client.open(url, method=method, json=body, headers=H)
    assert r.status_code < 300, (r.status_code, r.get_data(as_text=True)[:300])
    d = _delta(before, _counts())
    assert d.get(kind, 0) >= 1, (url, d)


def test_documento_de_cierre_existe_y_nombra_cada_brecha():
    path = os.path.join(ROOT, 'docs', 'CIERRE_INFRA.md')
    assert os.path.exists(path)
    doc = open(path, encoding='utf-8').read()
    for k in sorted(BRECHAS_CONOCIDAS):
        assert k.split(' ', 1)[1] in doc, f'docs/CIERRE_INFRA.md no menciona la brecha {k}'
    with open(os.path.join(ROOT, 'docs', 'BRECHAS_V2.md'), encoding='utf-8') as f:
        ids = re.findall(r'^\*\*([A-Za-z0-9-]+) · ', f.read(), flags=re.M)
    assert len(ids) == 99
    falta = [i for i in ids if not re.search(r'(?<![A-Za-z0-9-])' + re.escape(i) + r'(?![0-9])', doc)]
    assert not falta, 'docs/CIERRE_INFRA.md no da estado a: ' + ', '.join(falta)


def test_json_de_rutas_es_serializable():
    # la tabla de §3 del documento se genera de estas listas: deben ser JSON simple
    json.dumps({'con': CON_DECISION, 'sin': SIN_DECISION})
