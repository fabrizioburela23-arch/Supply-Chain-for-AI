"""core/ops_check.py — O1 (misión de reparación 2026-10-04): chequeo del
sistema EN el servidor, guardado y consultable.

Antes había ~60 tests del MCP con dobles, pero nada comprobaba el despliegue
VIVO ni quedaba un "último chequeo". Ahora:
  · `run_checks()` llama EN PROCESO a las herramientas MCP de SOLO LECTURA
    (`mcp_server.tools.call` con un principal de scope 'read'; cualquier
    herramienta que no sea de lectura se niega) + base de datos, snapshot,
    proveedores de IA (sin llamarlos: estado del corta-circuito), reloj del
    servidor, fuentes del World Monitor y diferencias catálogo↔base (G3).
    Nunca IA, nunca órdenes, nunca escrituras salvo su propia fila.
  · Cada corrida se guarda en `ops_checks` (append-only) y en memoria.
  · Reloj del servidor: 5 min después de cada arranque (= humo tras cada
    despliegue) y luego una vez cada 24 h (`ops_daily_check`).
  · `GET /api/ops/last_check` (sin PIN, sin secretos) y `POST /api/ops/check`
    (PIN de operador) para correrlo a mano.
"""
import logging
import threading
import time
import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ontology.models import Base

log = logging.getLogger('khipu')

ops_bp = Blueprint('ops', __name__, url_prefix='/api/ops')

DAILY_S = 24 * 3600
FIRST_AFTER_BOOT_S = 300
_LAST = {'data': None, 'ts': 0.0, 'boot_done': False}
_LOCK = threading.Lock()


class OpsCheck(Base):
    """Una corrida del chequeo (append-only)."""
    __tablename__ = 'ops_checks'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind = Column(String(20), nullable=False, default='daily')          # boot | daily | manual
    started_at = Column(DateTime(timezone=True), nullable=False)
    duration_ms = Column(Integer, nullable=True)
    ok = Column(Boolean, nullable=False)
    n_fail = Column(Integer, nullable=False, default=0)
    n_warn = Column(Integer, nullable=False, default=0)
    version = Column(String(40), nullable=True)
    result = Column(JSONB, nullable=False, default=dict)


# ── herramientas MCP de lectura que se prueban (nombre, args, claves que DEBEN venir)
SMOKE_TOOLS = (
    ('search_companies', {'query': 'TSMC', 'limit': 3}, ('results', 'as_of', 'source')),
    ('get_company', {'id_or_ticker': 'TSMC', 'include_live': False}, ('id', 'catalog', 'counts', 'network_risk_score')),
    ('get_supply_chain', {'id': 'TSMC', 'limit': 5}, ('edges', 'nodes', 'convention')),
    ('get_research_health', {}, ('ok', 'providers', 'queue')),
    ('get_world_events', {'layers': ['quakes', 'chokepoints'], 'limit': 5}, ('items', 'sources')),
    ('get_track_record', {}, ()),
    ('get_conclusions_board', {}, ()),
)


def _now():
    return datetime.now(timezone.utc)


def _version():
    try:
        import os
        import re
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, 'sw.js'), encoding='utf-8') as f:
            m = re.search(r"khipu-finance-v(\d+)", f.read(2048))
        return f'v{m.group(1)}' if m else None
    except Exception:  # noqa: BLE001
        return None


def _check(name, fn, critical=True):
    t0 = time.time()
    try:
        ok, detail = fn()
    except Exception as e:  # noqa: BLE001 — un chequeo roto se reporta, no tumba al resto
        ok, detail = False, f'{type(e).__name__}: {str(e)[:200]}'
    status = 'ok' if ok else ('fail' if critical else 'warn')
    return {'name': name, 'status': status, 'critical': critical, 'ms': int((time.time() - t0) * 1000),
            'detail': detail}


def _mcp_tool(name, args, must):
    def fn():
        from mcp_server import tools as T
        from mcp_server.auth import Principal
        t = T.REGISTRY.get(name)
        if t is None:
            return False, 'herramienta no registrada'
        if t.scope != 'read' or not t.annotations.get('readOnlyHint', False):
            return False, 'negado: el chequeo solo llama herramientas de LECTURA'
        ctx = T.Ctx(principal=Principal(token_id='ops-check', name='ops-check', scopes=frozenset({'read'})))
        res = T.call(name, args, ctx)
        missing = [k for k in must if k not in res]
        if missing:
            return False, f'faltan campos del contrato: {missing}'
        size = len(res.get('results') or res.get('edges') or res.get('items') or [])
        return True, f'ok · {len(res)} campos' + (f' · {size} elementos' if size else '')
    return fn


def _db():
    from ontology.db import ontology_available, session_scope
    if not ontology_available():
        return False, 'sin DATABASE_URL (la ontología está apagada)'
    from sqlalchemy import text
    with session_scope() as s:
        n_obj = s.execute(text('SELECT count(*) FROM objects')).scalar()
        n_link = s.execute(text('SELECT count(*) FROM links WHERE valid_to IS NULL')).scalar()
    return True, f'{n_obj} objetos · {n_link} vínculos vigentes'


def _snapshot():
    from mcp_server.tools import _snapshot as snap
    d = snap()
    n = len(d.get('nodes') or d.get('by_id') or [])
    return n >= 900, f'{n} nodos en el catálogo'


def _ai():
    from research.health import research_health
    h = research_health(light=True)
    avail = [p for p, v in h['providers'].items() if v['available']]
    paused = [p for p, v in h['providers'].items() if v['configured'] and v['circuit'].get('open')]
    return bool(avail), (f"disponibles: {', '.join(avail) or 'ninguno'}"
                         + (f" · en pausa: {', '.join(paused)}" if paused else ''))


def _scheduler():
    from core import scheduler
    st = scheduler.state()
    bad = {n: t['last_error'] for n, t in st.items() if t.get('last_error')}
    if not scheduler.enabled():
        return False, 'reloj del servidor apagado (KHIPU_SCHEDULER=off)'
    return not bad, ('tareas: ' + ', '.join(sorted(st)) if not bad else f'tareas con error: {bad}')


def _world():
    from core import world
    st = world.sources_state()
    paused = [n for n, v in st.items() if v.get('paused')]
    return not paused, ('fuentes en pausa: ' + ', '.join(f"{n} ({st[n]['error']})" for n in paused)
                        if paused else 'fuentes del World Monitor sin pausa')


def _graph_drift():
    from ontology.db import ontology_available, session_scope
    if not ontology_available():
        return True, 'sin base'
    from ontology import reconcile as R
    with session_scope() as s:
        plan = R.build_plan(s, R.load_snapshot())
    sm = plan['summary']
    tot = sum(sm[k] for k in R.CATEGORIES)
    return tot == 0, ('catálogo y base coinciden' if tot == 0 else
                      'diferencias catálogo↔base: ' + ', '.join(f'{k} {sm[k]}' for k in R.CATEGORIES if sm[k])
                      + ' (🩺 → Grafo: base vs catálogo)')


def run_checks(kind='manual', persist=True):
    t0 = time.time()
    started = _now()
    checks = [_check('base_de_datos', _db), _check('catalogo', _snapshot),
              _check('proveedores_ia', _ai, critical=False), _check('reloj_servidor', _scheduler, critical=False),
              _check('world_monitor', _world, critical=False), _check('grafo_vs_catalogo', _graph_drift, critical=False)]
    for name, args, must in SMOKE_TOOLS:
        checks.append(_check('mcp:' + name, _mcp_tool(name, args, must)))
    n_fail = sum(1 for c in checks if c['status'] == 'fail')
    n_warn = sum(1 for c in checks if c['status'] == 'warn')
    data = {'kind': kind, 'started_at': started.isoformat(timespec='seconds'),
            'duration_ms': int((time.time() - t0) * 1000), 'ok': n_fail == 0, 'n_fail': n_fail, 'n_warn': n_warn,
            'version': _version(), 'checks': checks}
    with _LOCK:
        _LAST.update(data=data, ts=time.time())
    if persist:
        try:
            from ontology.db import ontology_available, session_scope
            if ontology_available():
                with session_scope() as s:
                    s.add(OpsCheck(kind=kind, started_at=started, duration_ms=data['duration_ms'], ok=data['ok'],
                                   n_fail=n_fail, n_warn=n_warn, version=data['version'], result=data))
                data['saved'] = True
        except Exception as e:  # noqa: BLE001
            data['saved'] = False
            data['save_error'] = type(e).__name__
    if n_fail:
        log.warning('ops_check %s: %d fallos (%s)', kind, n_fail,
                    ', '.join(c['name'] for c in checks if c['status'] == 'fail'))
    return data


def scheduled():
    """Tarea del reloj (cada 5 min): corre una vez 5 min tras el arranque
    (humo del despliegue) y luego cada 24 h. Si no toca, no hace nada."""
    with _LOCK:
        boot_done, last_ts = _LAST['boot_done'], _LAST['ts']
    if not boot_done:
        with _LOCK:
            _LAST['boot_done'] = True
        return run_checks('boot')['ok']
    if time.time() - last_ts >= DAILY_S:
        return run_checks('daily')['ok']
    return 'skip'


def last_check(history=7):
    out = {'last': None, 'history': []}
    with _LOCK:
        out['last'] = _LAST['data']
    try:
        from ontology.db import ontology_available, session_scope
        if ontology_available():
            from sqlalchemy import select
            with session_scope() as s:
                rows = s.scalars(select(OpsCheck).order_by(OpsCheck.started_at.desc()).limit(history)).all()
                out['history'] = [{'kind': r.kind, 'started_at': r.started_at.isoformat(timespec='seconds'), 'ok': r.ok,
                                   'n_fail': r.n_fail, 'n_warn': r.n_warn, 'version': r.version} for r in rows]
                if out['last'] is None and rows:
                    out['last'] = rows[0].result
    except Exception as e:  # noqa: BLE001
        out['history_error'] = type(e).__name__
    return out


@ops_bp.route('/last_check')
def api_last_check():
    from core.http import rate_limit  # noqa: F401 — import diferido (evita ciclos)
    return jsonify(last_check())


def _register_manual_route():
    from core.http import rate_limit
    from core.pin import require_operator

    @ops_bp.route('/check', methods=['POST'])
    @require_operator
    @rate_limit(6, 600)
    def api_run_check():
        return jsonify(run_checks('manual'))


_register_manual_route()
