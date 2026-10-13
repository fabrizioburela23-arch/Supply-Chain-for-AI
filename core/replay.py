"""core/replay.py — REPETIR UNA DECISIÓN (docs/INFRA_OPERATIVA.md §5.6; paso 24 del plan).

`replay(decision_id)` (modo 'audit') reconstruye lo que el sistema SABÍA y vuelve a correr el cálculo determinista:

  1. integridad   manifest_sha y output_sha recalculados; blobs presentes o PURGADOS (retención D3: se dice, nunca se
                  inventa); fila sellada (cadena de hashes) o pendiente del próximo sello;
  2. linaje       mismo linaje del libro → visibilidad exacta; otro (base restaurada) → `fidelity: approximate`;
  3. artefactos   el release de ENTONCES por hash (gov_releases → cuerpos de gov_artifacts verificados por hash; si el
                  release no tiene fila —selección por entorno—, el mapa de versiones del manifiesto); nunca el repo
                  "de hoy";
  4. conocimiento G(t, κ) = el grafo vigente en t tal como se conocía en la versión κ (ontology/bitemporal +
                  core/hotviews/views/asof.load) construido con los parámetros del kernel de ese release; la huella de
                  GraphCore se compara con hot_view_builds (prueba que la vista que se leyó era correcta);
  5. núcleo       REPLAYERS[kind] con la implementación retenida (core/impls): qué-pasaría-si (kernel), comité
                  (umbrales → tamaño), órdenes (run_checks), regresión de gobernanza (choques de una empresa); las
                  PUERTAS de cualquier decisión con su grafo foco guardado (IR por hash); comparación exacta;
  6. IA           nunca se vuelve a pedir: se verifican prompt_sha/output_sha de ai_calls y se re-corre el guardián de
                  cifras sobre el texto guardado contra las entradas guardadas.

Veredicto: `identical` (todo lo repetible coincide) · `differs` (diferencia campo a campo) · `not_replayable` (por
qué: texto de IA, blob purgado, datos en vivo no guardados, entradas anteriores al paso 24…). Deja un
decision_outcome 'replay' (deduplicado) y, si quien pide está autenticado (PIN, MCP, reloj), UNA decisión `audit.replay`
por auditor, decisión, veredicto, código y día (async, nunca suma latencia al usuario; una lectura anónima no la deja).

`sample_job()` (reloj, 1×/día UTC): N decisiones deterministas al azar (whatif.*, committee.run, order.*,
governance.validate) de las últimas 24 h + TODAS las de dinero; una `audit.replay` con los conteos; un 'differs'
pone el 🩺 en rojo. Lectura sin PIN (resumen, sin valores de clientes); con PIN, el detalle. Nunca IA.
"""
import json
import logging
import random
import re
import threading
import time
import uuid
import zlib
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

log = logging.getLogger('khipu')

VERDICTS = ('identical', 'differs', 'not_replayable')
DETERMINISTIC_KINDS = ('whatif.shock', 'whatif.factor_fire', 'committee.run', 'order.preview', 'order.confirm',
                       'governance.validate')
MONEY_KINDS = ('order.preview', 'order.confirm')
AI_KINDS = ('chat.answer', 'chat.route', 'research.run', 'committee.portfolio_advice', 'mcp.tool_call')
SAMPLE_N = 50                     # §5.6: 50 al azar de las últimas 24 h + todas las de dinero
SAMPLE_MONEY_MAX = 300
CACHE_MAX = 64
CACHE_TTL_S = 600
GRAPH_LRU = 4
_GEN_RX = re.compile(r'^g(\d+)\.r([0-9a-f]{8})\.c[0-9a-f]+\.([a-z_]+)$')

_CACHE = OrderedDict()            # (decision_id, full) → (t, resultado)
_GRAPHS = OrderedDict()           # (t, gv, lineage, release) → GraphCore reconstruido
_LOCK = threading.Lock()
_HEAVY = threading.BoundedSemaphore(1)       # una reconstrucción de grafo a la vez (no compite con los 12 hilos)
STATE = {'runs': 0, 'last_sample': None, 'last_error': None}

# ── textos ES/EN ─────────────────────────────────────────────────────────────────────────────────────────────────
REASONS = {
    'ai_text': ('es texto escrito por la IA: no se vuelve a pedir (sería otra respuesta); solo se comprueban sus '
                'entradas y el guardián de cifras',
                'it is text written by the AI: it is not asked again (that would be a different answer); only its '
                'inputs and the figures guard are checked'),
    'blob_purged': ('sus datos de entrada se vaciaron por la regla de retención (90 días): queda solo la huella',
                    'its input data was emptied by the retention rule (90 days): only the fingerprint remains'),
    'live_data': ('usó datos en vivo (precios, cuenta) que no se guardaron completos',
                  'it used live data (prices, account) that was not fully stored'),
    'external_model': ('la decidió un modelo externo (Jev) que no se vuelve a consultar: se verificaron sus huellas',
                       'an external model (Jev) decided it and it is not asked again: its fingerprints were verified'),
    'inputs_not_stored': ('es anterior al registro de entradas para repetir (paso 24): no hay con qué repetir el cálculo',
                          'it predates the replay-input record (step 24): there is nothing to repeat the computation with'),
    'no_deterministic_core': ('es una escritura o un registro, no un cálculo: se verificaron sus huellas',
                              'it is a write or a record, not a computation: its fingerprints were verified'),
    'lineage_changed': ('la base de datos cambió (restauración): las versiones del grafo de entonces no son las de hoy',
                        'the database changed (restore): the graph versions of then are not those of today'),
    'graph_from_snapshot': ('se calculó sobre el catálogo del código (sin base), que no queda en el libro',
                            'it was computed on the code catalog (no database), which is not in the ledger'),
    'graph_version_unknown': ('no se sabe qué versión del grafo usó', 'the graph version it used is unknown'),
    'release_unavailable': ('no se encontraron las reglas (release) de entonces', 'the rules (release) of then were not found'),
    'impl_missing': ('este despliegue no conserva el código que la calculó', 'this deployment no longer keeps the code that computed it'),
    'factor_missing': ('el factor ya no estaba en el grafo de entonces', 'the factor was not in the graph of then'),
    'regression_ledger_window': ('la parte de la regresión que lee el libro de los 30 días previos no se repite',
                                 'the regression part that reads the previous 30 days of the ledger is not repeated'),
    'error': ('el replay falló al ejecutarse', 'the replay failed while running'),
}
# «aproximada»: el cálculo coincide (o no), pero algo de lo que se usó para repetirlo no es bit a bit lo de entonces
APPROX_LABELS = {
    'ledger_lineage_changed': ('la base de datos es otra (restaurada): las versiones del grafo se leen en la nueva',
                               'the database is a different one (restored): graph versions are read in the new one'),
    'release_hash_mismatch': ('las reglas de entonces se armaron versión por versión (su huella de conjunto no cuadra)',
                              'the rules of then were rebuilt version by version (their set fingerprint does not match)'),
    'view_sha_differs': ('la vista rápida reconstruida no es idéntica bit a bit a la que se leyó (diferencia mínima de '
                         'redondeo); el resultado se comparó exacto',
                         'the rebuilt fast view is not bit-for-bit the one that was read (tiny rounding difference); the '
                         'result was compared exactly'),
    'graph_version_from_stamp': ('la versión del grafo sale del sello de la ficha, no de la vista que se leyó',
                                 'the graph version comes from the record stamp, not from the view that was read'),
    'as_of_direct_path': ('fue un viaje en el tiempo (fecha pasada): se recalcula por el camino directo',
                          'it was a time travel (past date): it is recomputed by the direct path'),
    'committee_inputs_from_package': ('memo anterior al registro de entradas: se repite con el paquete guardado del comité',
                                      'memo older than the input record: it is replayed from the stored committee package'),
    'policy_key_missing': ('una regla de hoy no existía en esa versión: se usó el valor del código',
                           "a rule of today did not exist in that version: the code's value was used"),
    'us_listing_recomputed': ('si cotiza en EE. UU. se volvió a deducir del símbolo (no estaba guardado)',
                              'whether it trades in the US was deduced again from the symbol (it was not stored)'),
    'scored_claims_from_count': ('el número de conclusiones que puntúan sale del total guardado',
                                 'the number of scoring conclusions comes from the stored total'),
}
STEP_LABELS = {
    'integrity': ('Integridad (huellas)', 'Integrity (fingerprints)'),
    'seal': ('Sello en la cadena', 'Seal in the chain'),
    'lineage': ('Linaje de la base', 'Database lineage'),
    'artifacts': ('Reglas de entonces (release)', 'Rules of then (release)'),
    'impl': ('Código retenido', 'Retained code'),
    'graph': ('Grafo de entonces G(t, κ)', 'Graph of then G(t, κ)'),
    'views_rebuilt': ('Vista reconstruida = la que se leyó', 'Rebuilt view = the one that was read'),
    'deterministic_core': ('Cálculo repetido', 'Repeated computation'),
    'gates': ('Puertas de validación', 'Validation gates'),
    'ai_steps': ('Pasos de IA (solo verificación)', 'AI steps (verification only)'),
    'error': ('Error al repetir', 'Replay error'),
}
KIND_LABELS = {
    'ontology.action': ('Acción en la ontología', 'Ontology action'),
    'ontology.raw_event': ('Evento crudo de la ontología', 'Raw ontology event'),
    'ontology.bulk_import': ('Importación en bloque', 'Bulk import'),
    'ontology.news_ingest': ('Noticias al grafo', 'News into the graph'),
    'proposal.create': ('Propuesta de un agente', 'Agent proposal'),
    'proposal.auto_apply': ('Propuesta aplicada sola', 'Auto-applied proposal'),
    'approval.grant': ('Aprobación', 'Approval'), 'approval.deny': ('Rechazo', 'Denial'),
    'order.preview': ('Orden: previsualización', 'Order: preview'),
    'order.confirm': ('Orden: confirmación', 'Order: confirmation'),
    'order.submit': ('Orden: envío al bróker', 'Order: sent to the broker'),
    'order.cancel': ('Orden: cancelación', 'Order: cancellation'), 'order.expire': ('Orden: vencida', 'Order: expired'),
    'trade.agent_signal': ('Señal del agente de trading', 'Trading agent signal'),
    'committee.run': ('Memo del comité', 'Committee memo'),
    'committee.portfolio_advice': ('Consejo de cartera', 'Portfolio advice'),
    'research.job': ('Pedido de investigación', 'Research request'), 'research.run': ('Analista', 'Analyst run'),
    'claim.status': ('Estado de una conclusión', 'Conclusion status'),
    'alert.rule': ('Regla de alerta', 'Alert rule'), 'alert.fire': ('Alerta disparada', 'Alert fired'),
    'whatif.shock': ('Qué pasaría si (choque)', 'What-if (shock)'),
    'whatif.factor_fire': ('Qué pasaría si (factor de crisis)', 'What-if (crisis factor)'),
    'whatif.agent_sim': ('Simulación por agentes', 'Agent simulation'),
    'simulation.save': ('Simulación guardada', 'Saved simulation'), 'insight.snapshot': ('Insights', 'Insights'),
    'chat.route': ('Chat: ruta', 'Chat: route'), 'chat.answer': ('Chat: respuesta', 'Chat: answer'),
    'mcp.tool_call': ('IA externa (MCP)', 'External AI (MCP)'),
    'reconcile.plan': ('Reconciliación: plan', 'Reconcile: plan'),
    'reconcile.apply': ('Reconciliación: aplicar', 'Reconcile: apply'),
    'reconcile.rollback': ('Reconciliación: deshacer', 'Reconcile: rollback'),
    'policy.change': ('Cambio de política', 'Policy change'),
    'governance.propose': ('Gobernanza: propuesta', 'Governance: proposal'),
    'governance.validate': ('Gobernanza: regresión', 'Governance: regression'),
    'governance.activate': ('Gobernanza: activación', 'Governance: activation'),
    'governance.ratify': ('Gobernanza: ratificación', 'Governance: ratification'),
    'retention.purge': ('Purga por retención', 'Retention purge'),
    'retention.migrate': ('Limpieza de datos viejos', 'Old data cleanup'),
    'ledger.lineage_break': ('Libro: linaje nuevo', 'Ledger: new lineage'),
    'ledger.chain_break': ('Libro: cadena rota', 'Ledger: chain broken'),
    'ledger.chain_ack': ('Libro: ruptura reconocida', 'Ledger: break acknowledged'),
    'audit.replay': ('Auditoría: repetición', 'Audit: replay'), 'audit.gates': ('Avisos de puertas', 'Gate warnings'),
    'data.backfill': ('Relleno de precios', 'Price backfill'),
}
STATUS_LABELS = {
    'executed': ('se ejecutó', 'was executed'), 'rejected': ('se rechazó', 'was rejected'), 'failed': ('falló', 'failed'),
    'blocked': ('la bloqueó una regla', 'was blocked by a rule'), 'approved': ('se aprobó', 'was approved'),
    'pending_approval': ('espera aprobación', 'awaits approval'), 'proposed': ('quedó propuesta', 'was proposed'),
    'noop': ('no cambió nada', 'changed nothing'), 'answered': ('se respondió', 'was answered'),
    'fired': ('se disparó', 'fired'), 'recorded': ('quedó registrada', 'was recorded'), 'expired': ('venció', 'expired'),
}


def kind_label(kind, lang='es'):
    a = KIND_LABELS.get(kind)
    return (a[1] if lang == 'en' else a[0]) if a else kind


def replayable_kind(kind):
    """¿Tiene núcleo determinista que se pueda repetir? (las puertas y la IA se verifican en todas)."""
    return kind in DETERMINISTIC_KINDS


# ── utilidades ───────────────────────────────────────────────────────────────────────────────────────────────────
class _Run:
    def __init__(self, d):
        self.d = d
        self.steps = []
        self.reasons = []
        self.approximations = []
        self.notes = []
        self.compared = 0
        self.differs = 0
        self.fidelity = 'exact'
        self.world = {}

    def step(self, name, ok, **kw):
        st = {'name': name, 'ok': ok, **kw}
        self.steps.append(st)
        return st

    def compare(self, name, recorded, replayed, **kw):
        from core import impls
        dif = impls.diff(recorded, replayed)
        self.compared += 1
        if dif:
            self.differs += 1
        return self.step(name, not dif, diffs=dif, **kw)

    def reason(self, code):
        if code not in self.reasons:
            self.reasons.append(code)

    def approx(self, code, **kw):
        self.approximations.append({'code': code, **kw})
        self.fidelity = 'approximate'


def _blob(session, sha):
    """(cuerpo, estado) — estado ∈ ok | purged | missing | corrupt. Verifica el sha del contenido."""
    if not sha:
        return None, 'missing'
    import hashlib

    from sqlalchemy import text
    r = session.execute(text('SELECT body FROM decision_blobs WHERE sha256 = :s'), {'s': sha}).first()
    if r is None:
        return None, 'missing'
    if r.body is None:
        return None, 'purged'
    raw = zlib.decompress(bytes(r.body))
    if hashlib.sha256(raw).hexdigest() != sha:
        return None, 'corrupt'
    return json.loads(raw), 'ok'


def _mf(run, session, key):
    """Campo del manifiesto (o de su blob de desborde)."""
    m = run.d.get('manifest') or {}
    if key in m:
        return m.get(key)
    ob = m.get('overflow_blob')
    if not ob:
        return None
    if '_overflow' not in run.__dict__:
        body, st = _blob(session, ob)
        run._overflow = body or {}
        run._overflow_state = st
        if st != 'ok':
            run.notes.append({'overflow_blob': st})
            run.reason('blob_purged' if st == 'purged' else 'inputs_not_stored')
    return run._overflow.get(key)


def _need_params(run, session):
    """request_params del qué-pasaría-si, o None (con su motivo honesto) si no están: nunca se repite «sin choques»."""
    rp = _mf(run, session, 'request_params')
    if not rp:
        if 'blob_purged' not in run.reasons:
            run.reason('inputs_not_stored')
        return None
    return rp


def _inputs_lost(run):
    """¿Las entradas que el replay necesita estaban en el blob de desborde y ya no están (purgado/ausente)? Entonces
    no se compara nada: el veredicto es «no repetible» con la razón honesta (nunca un «distinto» inventado)."""
    return getattr(run, '_overflow_state', 'ok') != 'ok'


def _iso(v):
    return v.isoformat() if isinstance(v, datetime) else v


# ── 1-2. integridad, sello y linaje ──────────────────────────────────────────────────────────────────────────────
def _integrity(run, session):
    from core import decisions
    d = run.d
    m = d.get('manifest') or {}
    ok_m = decisions.sha256_hex(m) == d.get('manifest_sha')
    out = d.get('output')
    ok_o = True
    if out is not None and d.get('output_sha'):
        if isinstance(out, dict) and out.get('truncated') and out.get('blob'):
            body, st = _blob(session, out['blob'])
            ok_o = st in ('ok', 'purged') and out['blob'] == d['output_sha']
        else:
            ok_o = decisions.sha256_hex(out) == d['output_sha']
    blobs = {}
    for sha in {x for x in (d.get('inputs_sha'), m.get('overflow_blob'), (m.get('replay') or {}).get('blob'),
                            m.get('transcript_blob'), (m.get('account') or {}).get('blob')) if x}:
        blobs[sha[:12]] = _blob(session, sha)[1]
    purged = sorted(k for k, v in blobs.items() if v == 'purged')
    bad = sorted(k for k, v in blobs.items() if v in ('missing', 'corrupt'))
    st = run.step('integrity', ok_m and ok_o and not bad, manifest_sha_ok=ok_m, output_sha_ok=ok_o, blobs=blobs)
    if not (ok_m and ok_o and not bad):
        run.compared += 1
        run.differs += 1
    if purged:
        run.reason('blob_purged')
        st['purged'] = purged
    seal = d.get('seal')
    try:
        from core import ledger
        chain = ledger.chain_state()
        broken = bool(chain.get('broken'))
    except Exception:  # noqa: BLE001
        broken = None
    # aún sin sellar (el sellador pasa cada 30 s) no es una falla: ok=None y pending=true
    run.step('seal', (not broken) if seal else None, seal_no=(seal or {}).get('seal_no'), pending=not bool(seal),
             chain_broken=broken)
    try:
        from core import ledger
        cur = ledger.lineage_id()
        lin = d.get('lineage_id')
        same = cur is not None and str(cur) == str(lin)
    except Exception:  # noqa: BLE001
        same = None
    run.step('lineage', bool(same), same_lineage=same)
    if same is False:
        run.approx('ledger_lineage_changed')


# ── 3. el release de entonces ────────────────────────────────────────────────────────────────────────────────────
def _art_body(session, aid, *, h=None, semver=None):
    """{semver, hash, params, kind} de gov_artifacts (por hash o por versión) o del archivo del repositorio, siempre
    verificado por hash. None si no existe."""
    from sqlalchemy import text

    from core import governance
    row = None
    try:
        with session.begin_nested():
            if h:
                row = session.execute(text('SELECT body FROM gov_artifacts WHERE hash = :h'), {'h': h}).first()
            elif semver:
                row = session.execute(text('SELECT body FROM gov_artifacts WHERE artifact_id = :a AND semver = :v'),
                                      {'a': aid, 'v': semver}).first()
    except Exception:  # noqa: BLE001 — sin tablas de gobernanza
        row = None
    body = None
    if row is not None:
        body = row.body if isinstance(row.body, dict) else json.loads(row.body)
    else:
        for (a, sv), doc in governance.scan_repo().items():
            if a != aid:
                continue
            if (h and governance.artifact_hash(doc) == h) or (not h and sv == semver):
                body = doc
                break
    if body is None:
        return None
    hh = governance.artifact_hash(body)
    if (h and hh != h) or body.get('id') != aid:
        return None
    return {'semver': body['semver'], 'hash': hh, 'params': body['params'], 'kind': body['kind']}


def release_artifacts(session, d):
    """(arts, info) del release que REGÍA la decisión. info = {source, release_hash_ok, missing, fallback}."""
    from sqlalchemy import text

    from core import governance
    m = d.get('manifest') or {}
    rel = m.get('release') or {}
    want = d.get('release_hash')
    refs, source = {}, None
    try:
        with session.begin_nested():
            row = session.execute(text('SELECT artifacts FROM gov_releases WHERE release_hash = :h'),
                                  {'h': want}).first()
    except Exception:  # noqa: BLE001
        row = None
    if row is not None:
        refs = {a: dict(v) for a, v in (row.artifacts or {}).items()}
        source = 'gov_releases'
    elif rel.get('semver'):
        refs = {a: {'semver': v} for a, v in rel['semver'].items()}
        source = 'manifest_semver'
    arts, missing = {}, []
    for aid, ref in sorted(refs.items()):
        a = _art_body(session, aid, h=ref.get('hash'), semver=ref.get('semver'))
        if a is None:
            missing.append(aid)
        else:
            arts[aid] = a
    ok = bool(arts) and not missing and governance.release_hash_of({a: v['hash'] for a, v in arts.items()}) == want
    fb = {}
    for aid, ref in sorted((rel.get('fallback') or {}).items()):
        a = _art_body(session, aid, h=ref.get('hash'), semver=ref.get('semver'))
        if a is not None:
            arts.setdefault(aid, a)
            fb[aid] = a['semver']
    return arts, {'source': source, 'release_hash_ok': ok, 'missing': missing, 'fallback': fb,
                  'semver': {a: v['semver'] for a, v in sorted(arts.items())}}


# ── 4. el grafo de entonces ─────────────────────────────────────────────────────────────────────────────────────
def _generation_of(run, session):
    """(graph_version, generation_id, source) de la vista 'impact' que leyó la decisión (o del sello)."""
    views = _mf(run, session, 'views') or []
    for v in views:
        if v.get('name') in ('impact', 'graph_core') and isinstance(v.get('version'), str):
            mt = _GEN_RX.match(v['version'])
            if mt:
                return int(mt.group(1)), v['version'], mt.group(3)
    con = _mf(run, session, 'computed_on') or {}
    if con.get('graph_version') is not None:          # camino directo: la versión leída AL CALCULAR (misma lectura)
        return int(con['graph_version']), None, 'pg'
    gv = run.d.get('graph_version')
    return (int(gv) if gv is not None else None), None, None


def _lineage_now(session):
    from sqlalchemy import text
    row = session.execute(text("SELECT to_regclass('events')::oid, to_regclass('kh_versions')::oid")).first()
    return f'{row[0]}.{row[1]}' if row else None


def _graph(run, session, arts, t=None, gv=None):
    """GraphCore de G(t, κ=gv) construido con los parámetros del kernel de `arts` (LRU pequeño)."""
    from core import impls
    from core.hotviews.views import asof, graph_core
    from ontology import bitemporal
    lin = _lineage_now(session)
    kh = (arts.get('kernel.params') or {}).get('hash')
    key = (_iso(t), gv, lin, kh)
    with _LOCK:
        hit = _GRAPHS.get(key)
        if hit is not None:
            _GRAPHS.move_to_end(key)
            return hit
    known = bitemporal.resolve(session, gv) if gv is not None else bitemporal.now_known(session)
    if not _HEAVY.acquire(timeout=30):
        raise TimeoutError('replay ocupado / replay busy')
    try:
        data = asof.load(session, t, known)
        with impls.under(arts):
            core = graph_core.build(data)
    finally:
        _HEAVY.release()
    with _LOCK:
        _GRAPHS[key] = core
        while len(_GRAPHS) > GRAPH_LRU:
            _GRAPHS.popitem(last=False)
    return core


def _view_check(run, session, gen, core):
    """¿La GraphCore reconstruida es la que la generación publicó? (hot_view_builds)."""
    if not gen:
        return
    from sqlalchemy import text
    try:
        with session.begin_nested():
            r = session.execute(text("SELECT content_sha FROM hot_view_builds WHERE name = 'graph_core' AND "
                                     "generation = :g ORDER BY id DESC LIMIT 1"), {'g': gen}).first()
    except Exception:  # noqa: BLE001
        r = None
    if r is None or not r[0]:
        run.step('views_rebuilt', None, content_sha_match=None, note='build_not_logged')
        return
    match = r[0] == core.content_sha
    if not match:
        # la vista publicada no es bit a bit la reconstruida (p. ej. una generación anterior al orden canónico de los
        # factores, paso 24: 1 ulp en la fragilidad). No decide el veredicto —lo decide el RESULTADO de la decisión, que se compara exacto—,
        # pero queda como aproximación visible
        run.approx('view_sha_differs', generation=gen)
    run.step('views_rebuilt', match, content_sha_match=match, generation=gen)


# ── 5. núcleos deterministas ─────────────────────────────────────────────────────────────────────────────────────
def _whatif_world(run, session, arts):
    gv, gen, src = _generation_of(run, session)
    if _inputs_lost(run):
        return None, None
    if src and src != 'pg':
        run.reason('graph_from_snapshot')
        return None, None
    if gv is None:
        run.reason('graph_version_unknown')
        return None, None
    con = _mf(run, session, 'computed_on') or {}
    if gen is None and con.get('graph_version') is None:
        run.approx('graph_version_from_stamp')
    lin_then = (con.get('graph_lineage') or
                ((run.d.get('manifest') or {}).get('knowledge') or {}).get('graph_lineage'))
    lin_now = _lineage_now(session)
    if lin_then and lin_now and lin_then != lin_now:
        run.reason('lineage_changed')
        return None, None
    run.world['graph_version'] = gv
    return gv, gen


def _output(run, session):
    """La salida registrada completa (si pasó de 8 KB está en un blob)."""
    out = run.d.get('output') or {}
    if isinstance(out, dict) and out.get('truncated') and out.get('blob'):
        body, st = _blob(session, out['blob'])
        if st == 'purged':
            run.reason('blob_purged')
        return body or {}
    return out


def _whatif_compare(run, impacts, extra=None, session=None):
    from core import decisions
    out = _output(run, session) if session is not None else (run.d.get('output') or {})
    top = sorted(impacts.items(), key=lambda kv: (-float(kv[1] or 0), kv[0]))[:50]
    rec = {'content_sha': out.get('content_sha'), 'n': out.get('n'), 'top': out.get('top')}
    rep = {'content_sha': decisions.sha256_hex(impacts), 'n': len(impacts), 'top': [[k, v] for k, v in top]}
    for k, v in (extra or {}).items():
        if k in out:
            rec[k], rep[k] = out[k], v
    return run.compare('deterministic_core', rec, rep, impl='propagate@1', compared=sorted(rec))


def _replay_whatif_shock(run, session, arts):
    import numpy as np

    from core import impls
    from core.hotviews.views import impact
    from matrix import engine as E
    rp = _need_params(run, session)
    if rp is None:
        return
    ep = rp.get('endpoint')
    as_of = rp.get('as_of')
    gv, gen = _whatif_world(run, session, arts)
    if gv is None:
        return
    with impls.under(arts):
        if ep in ('/api/hot/scenario', '/api/hot/scenario_pnl'):   # scenario_pnl: el mismo choque + κ (no se repite el dinero)
            core = _graph(run, session, arts, None, gv)
            _view_check(run, session, gen, core)
            x0 = np.zeros(len(core.ids))
            for it in rp.get('shocks') or [{'id': i, 'magnitude': 1.0} for i in rp.get('shock') or []]:
                oid = core.resolve(str(it.get('id') or '')[:120])
                if oid is not None:
                    x0[core.idx[oid]] = max(x0[core.idx[oid]], float(it.get('magnitude', 1.0)))
            sc = impact.scenario(core, x0, factors=rp.get('factors', 'active'), damping=rp.get('damping'),
                                 max_hops=rp.get('max_hops'), direction=rp.get('direction') or 'down')
            _whatif_compare(run, sc['impacts'], {'affected': sc['affected']}, session)
            return
        kw = dict(magnitude=rp.get('magnitude'), damping=rp.get('damping'), max_hops=rp.get('max_hops'),
                  rel_weights=rp.get('rel_weights'), nonlinear=bool(rp.get('nonlinear')))
        shock = [x for x in (rp.get('shock') or []) if isinstance(x, str)]
        if as_of is None:
            core = _graph(run, session, arts, None, gv)
            _view_check(run, session, gen, core)
            dt = core.dt if not kw['rel_weights'] else None
            ids_ok = [x for x in shock if x in core.idx]
            if dt is not None:
                imp, _c = E.propagate(core.mats, core.idx, core.ids, ids_ok, frag=core.frag, dt=dt, **kw)
            else:
                imp, _c = E.propagate(core.mats, core.idx, core.ids, ids_ok, frag=core.frag, **kw)
        else:
            from ontology import bitemporal
            from ontology.service import _parse_dt
            known = bitemporal.resolve(session, gv)
            run.approx('as_of_direct_path')
            mats, idx, ids = E.build_matrices(session, as_of=_parse_dt(as_of), known=known)
            factors = E.active_factors(session, as_of=_parse_dt(as_of), known=known)
            frag = E.fragility(idx, factors)
            imp, _c = E.propagate(mats, idx, ids, [x for x in shock if x in idx], frag=frag, **kw)
            run.world['as_of'] = as_of
        # (el 'affected' de /api/matrix/impact resta también los ids DESCONOCIDOS del pedido, que no se guardan:
        # no se compara; la huella del vector completo lo cubre)
        _whatif_compare(run, imp, None, session)


def _replay_whatif_fire(run, session, arts):
    from core import impls
    from matrix import engine as E
    from matrix.api import MAGNITUDE_MAX
    rp = _need_params(run, session)
    if rp is None:
        return
    gv, gen = _whatif_world(run, session, arts)
    if gv is None:
        return
    fid = rp.get('factor_id') or (run.d.get('subject') or {}).get('factor_id')
    with impls.under(arts):
        core = _graph(run, session, arts, None, gv)
        _view_check(run, session, gen, core)
        mats, idx, ids, factors = core.mats, core.idx, core.ids, core.factors
        target = next((f for f in factors if f['id'] == fid), None)
        if target is None:
            run.reason('factor_missing')
            return
        damping, max_hops, magnitude = rp.get('damping'), rp.get('max_hops'), rp.get('magnitude')
        member_coef = E._P('fire_mode', 'legacy') == 'member_coef'
        if member_coef:
            crisis = target.get('severity_crisis') or min(float(E._P('fire_crisis_default_max', 10.0)),
                                                          target['severity'] * 2)
        else:
            crisis = target.get('severity_crisis') or min(5.0, target['severity'] * 2)
        fc = [dict(f, severity=crisis) if f['id'] == fid else f for f in factors]
        frag = E.fragility(idx, fc)
        shock_ids = [m for m in target['members'] if m in idx]
        if member_coef:
            div = float(E._P('severity_divisor'))
            base = min(1.0, magnitude if magnitude is not None else max(0.0, float(crisis) / div))
            x0 = {m: base * min(1.0, max(0.0, float(target['members'][m]))) for m in shock_ids}
            imp, _c = E.propagate(mats, idx, ids, shock_ids, frag=frag, damping=damping, max_hops=max_hops, x0=x0)
        else:
            base = magnitude if magnitude is not None else max(0.0, min(MAGNITUDE_MAX, float(crisis) / 5.0))
            imp, _c = E.propagate(mats, idx, ids, shock_ids, frag=frag, magnitude=base, damping=damping,
                                  max_hops=max_hops)
            for m in shock_ids:
                coef = min(1.0, float(target['members'][m]))
                if m in imp:
                    imp[m] = round(imp[m] * coef, 2)
        rho = E.spectral_radius(mats, fc, idx, damping=damping)
        st = _whatif_compare(run, imp, None, session)
        rec = {'severity_crisis': rp.get('severity_crisis'), 'fire_mode': rp.get('fire_mode')}
        rep = {'severity_crisis': crisis, 'fire_mode': 'member_coef' if member_coef else 'legacy'}
        st['diffs'] = st['diffs'] + impls.diff(rec, rep)
        # ρ es una propiedad espectral DERIVADA (no el resultado del choque): hasta el paso 24 ARPACK arrancaba de un
        # vector aleatorio y ρ variaba en el 6.º decimal → se compara con tolerancia 1e-5 y se anota
        out = _output(run, session)
        if out.get('rho_crisis') is not None and rho.get('rho') is not None:
            st['compared'] = sorted(set(st.get('compared') or ()) | {'rho_crisis'})
            st['rho_tolerance'] = 1e-5
            if abs(float(out['rho_crisis']) - float(rho['rho'])) > 1e-5:
                st['diffs'].append({'path': 'rho_crisis', 'recorded': out['rho_crisis'], 'replayed': rho['rho']})
        if st['diffs'] and st['ok']:
            st['ok'] = False
            run.differs += 1


def _committee_legacy_inputs(run, session):
    """Entradas de un memo ANTERIOR al paso 24 (sin blob de replay) desde el paquete guardado — solo si no hubo
    cliente (la foto del cliente no estaba en el libro)."""
    subj = run.d.get('subject') or {}
    if subj.get('client_id'):
        run.reason('inputs_not_stored')
        return None
    body, st = _blob(session, run.d.get('inputs_sha'))
    if st != 'ok':
        run.reason('blob_purged' if st == 'purged' else 'inputs_not_stored')
        return None
    out = run.d.get('output') or {}
    conv = body.get('conviction') or {}
    agents = sorted({c.get('agent_type') for r in conv.values() for c in (r.get('claims') or []) if c.get('agent_type')})
    live = body.get('live') or {}
    risk = body.get('risk') or {}
    run.approx('committee_inputs_from_package')
    return {'symbol': subj.get('symbol'), 'has_client': False, 'client': None, 'us_listing': None,
            'price_is_usd': None, 'currency': live.get('currency'), 'mandate': body.get('mandate'),
            'vol_ann_pct': risk.get('vol_ann_pct') if risk.get('ok') else None,
            'price': live.get('price') if live.get('ok') else None, 'validated': out.get('validated'),
            'overall': out.get('overall_conviction'), 'n_claims': out.get('n_claims'), 'agent_types': agents,
            'conviction': conv,
            'expect': {'quant_decision': out.get('quant_decision'), 'decision': out.get('decision'),
                       'decision_code': out.get('decision_code'), 'quorum_ok': out.get('quorum_ok'),
                       'sizing': out.get('sizing')}, '_legacy': True}


def _replay_committee(run, session, arts):
    """Decisión por umbrales → tamaño, con policy.committee de ENTONCES (research.committee con esos números)."""
    from core import impls
    rpl = _mf(run, session, 'replay') or {}
    if rpl.get('blob'):
        inp, st = _blob(session, rpl['blob'])
        if st != 'ok':
            run.reason('blob_purged' if st == 'purged' else 'inputs_not_stored')
            return
        payload, pst = _blob(session, run.d.get('inputs_sha'))
        inp = dict(inp, conviction=(payload or {}).get('conviction') if pst == 'ok' else None)
    else:
        inp = _committee_legacy_inputs(run, session)
        if inp is None:
            return
    notes = []
    C = impls.module_view('research.committee', arts, notes)
    for n in notes:
        run.approx('policy_key_missing', **n)
    sym = inp.get('symbol')
    mandate = dict(inp.get('mandate') or C.mandate_from(None))
    cl = inp.get('client') or {}
    pos = cl.get('position') or {}
    equity = cl.get('equity') if cl and cl.get('ok') else None
    cur_val = float(pos.get('market_value') or 0.0)
    cur_w = (cur_val / equity) if equity else 0.0
    has_pos = bool(pos and (pos.get('qty') or 0) > 0)
    us = inp.get('us_listing')
    if us is None and sym:
        from research.outcomes import is_us_listing
        us = bool(is_us_listing(sym))
        run.approx('us_listing_recomputed')
    price_is_usd = inp.get('price_is_usd')
    if price_is_usd is None:
        price_is_usd = (inp.get('currency') or ('USD' if us else None)) == 'USD'
    tradable = bool(us) or not inp.get('has_client')
    asym = C.alpaca_symbol(sym) if sym else None
    blocked = bool(sym and ((sym in mandate['blocked_symbols'] or asym in mandate['blocked_symbols']) or
                            (mandate['allowed_symbols'] and sym not in mandate['allowed_symbols']
                             and asym not in mandate['allowed_symbols'])))
    conv = inp.get('conviction') or {}
    scored = sum(int(r.get('n_claims') or 0) for h, r in conv.items() if C.HZ_WEIGHTS.get(h, 0) > 0) if conv \
        else int(inp.get('n_claims') or 0)
    if not conv:
        run.approx('scored_claims_from_count')
    rows = int(inp.get('n_claims') or 0) > 0
    quorum = C.quorum_check(set(inp.get('agent_types') or ()))
    vol, validated, price = inp.get('vol_ann_pct'), bool(inp.get('validated')), inp.get('price')
    overall = float(inp.get('overall') or 0.0)
    tw = C.effective_target_weight(vol, mandate, validated)
    decision, _es, _en = C.decide(overall, investable=bool(sym), insufficient=scored < C.MIN_CLAIMS,
                                  has_position=has_pos, current_w=cur_w, target_w=tw, blocked=blocked,
                                  tradable=tradable, quorum=quorum if rows else None)
    code = 'INSUFFICIENT_DATA' if (rows and not quorum['ok'] and decision == 'HOLD') else None
    trim_reason = 'overweight' if (decision == 'TRIM' and overall > C.TRIM_T) else 'conviction'
    sizing = C.compute_sizing(decision, vol, mandate, equity=equity, current_value=cur_val,
                              current_qty=float(pos.get('qty') or 0.0), price=price,
                              buying_power=cl.get('buying_power') if cl else None, trim_reason=trim_reason,
                              price_is_usd=price_is_usd, validated=validated)
    if C.ACTIONABLE.get(decision) and equity is not None and sizing['notional'] < 1 and not sizing.get('qty'):
        decision = 'HOLD'
        sizing = C.compute_sizing('HOLD', vol, mandate, equity=equity, current_value=cur_val, price=price,
                                  price_is_usd=price_is_usd, validated=validated)
    exp = inp.get('expect') or {}
    final = exp.get('decision')
    if final and final != decision:            # el presidente rebajó a HOLD: mismo recálculo que el comité
        sizing = C.compute_sizing('HOLD', vol, mandate, equity=equity, current_value=cur_val, price=price,
                                  price_is_usd=price_is_usd, validated=validated)
    keys = ('target_weight_pct', 'raw_weight_pct', 'cap_pct', 'notional', 'qty', 'side', 'unvalidated',
            'unvalidated_factor', 'capped_by')
    rec_s = exp.get('sizing') or {}
    if inp.get('_legacy'):
        rec_s = {k: rec_s.get(k) for k in keys}
        rep_s = {k: sizing.get(k) for k in keys}
    else:
        rep_s = impls_clean(sizing)
    rec = {'quant_decision': exp.get('quant_decision'), 'decision_code': exp.get('decision_code'),
           'quorum_ok': exp.get('quorum_ok') if rows else None, 'sizing': rec_s}
    rep = {'quant_decision': decision, 'decision_code': code, 'quorum_ok': quorum['ok'] if rows else None,
           'sizing': rep_s}
    run.compare('deterministic_core', rec, rep, impl='compute_sizing@1',
                compared=['quant_decision', 'decision_code', 'quorum_ok', 'sizing'])


def impls_clean(v):
    from core.decision_sites import clean
    return clean(v)


def _replay_order(run, session, arts):
    """run_checks con policy.broker_risk de ENTONCES sobre el contexto guardado (cuenta del blob 'account_snapshot')."""
    from core import impls
    rpl = _mf(run, session, 'replay') or {}
    if not rpl.get('blob'):
        run.reason('inputs_not_stored')
        return
    body, st = _blob(session, rpl['blob'])
    if st != 'ok':
        run.reason('blob_purged' if st == 'purged' else 'inputs_not_stored')
        return
    ctx = dict(body.get('ctx') or {})
    if body.get('account_blob'):
        acc, ast = _blob(session, body['account_blob'])
        if ast != 'ok':
            run.reason('blob_purged' if ast == 'purged' else 'inputs_not_stored')
            return
        ctx['account'], ctx['positions'] = acc.get('account'), acc.get('positions') or []
    else:
        ctx['account'], ctx['positions'] = None, []
    if isinstance(ctx.get('ledger_chain'), list):
        ctx['ledger_chain'] = tuple(ctx['ledger_chain'])
    env = body.get('env') or {}
    notes = []
    R = impls.module_view('brokerage.risk', arts, notes)
    for n in notes:
        run.approx('policy_key_missing', **n)
    te, le = bool(env.get('trading_enabled', True)), bool(env.get('live_env_enabled', False))
    impls.view_with(R, trading_enabled=lambda: te, live_env_enabled=lambda: le)
    checks = R.run_checks(ctx)
    rep = [{k: c.get(k) for k in ('name', 'ok', 'severity', 'warn', 'shadow', 'detail')} for c in checks]
    run.compare('deterministic_core', {'checks': (body.get('expect') or {}).get('checks')},
                impls_clean({'checks': rep}), impl='run_checks@1', compared=['checks'])


def _replay_validate(run, session, arts):
    """Regresión de gobernanza: los choques de una empresa ANTES/DESPUÉS sobre el grafo de entonces."""
    from core import governance_preview, impls
    from core.hotviews.views import impact
    rep0, st = _blob(session, run.d.get('inputs_sha'))
    if st != 'ok':
        run.reason('blob_purged' if st == 'purged' else 'inputs_not_stored')
        return
    run.reason('regression_ledger_window')
    sh = rep0.get('shocks')
    gv = rep0.get('graph_version')
    if not sh or gv is None:
        return
    subj = run.d.get('subject') or {}
    new = _art_body(session, subj.get('artifact'), h=subj.get('hash'), semver=subj.get('semver'))
    if new is None:
        run.reason('release_unavailable')
        return
    after_arts = dict(arts, **{subj['artifact']: new})
    run.world['graph_version'] = int(gv)
    if not _HEAVY.acquire(timeout=60):
        raise TimeoutError('replay ocupado / replay busy')
    try:
        from core.hotviews.views import asof, graph_core
        from ontology import bitemporal
        known = bitemporal.resolve(session, int(gv))
        data = asof.load(session, None, known)
        with impls.under(arts):
            c0 = graph_core.build(data)
            i0 = impact.build(c0)
        with impls.under(after_arts):
            c1 = graph_core.build(data)
            i1 = impact.build(c1)
            k = governance_preview._kernel_compare((data, c0, i0), (data, c1, i1))
    finally:
        _HEAVY.release()
    k.pop('reference', None)
    rec = {kk: sh.get(kk) for kk in ('shocks', 'shocks_changed', 'reach_higher', 'reach_lower',
                                     'companies_with_changed_impact', 'mean_reach_before', 'mean_reach_after')}
    rp = {kk: k.get(kk) for kk in rec}
    run.compare('deterministic_core', rec, rp, impl='gov-regression@1', compared=sorted(rec))


REPLAYERS = {'whatif.shock': _replay_whatif_shock, 'whatif.factor_fire': _replay_whatif_fire,
             'committee.run': _replay_committee, 'order.preview': _replay_order, 'order.confirm': _replay_order,
             'governance.validate': _replay_validate}


# ── puertas (cualquier decisión con su grafo foco) ───────────────────────────────────────────────────────────────
def _ir_for(session, arts, ir_hash):
    """El IR compilado de `ir_hash`: el del release de entonces, otra versión registrada o un archivo del repo."""
    from sqlalchemy import text

    from core import governance
    from core.gates import engine as GE
    a = arts.get('ontology.shapes')
    cands = []
    if a and (a.get('params') or {}).get('ir_hash') == ir_hash:
        cands.append(a)
    if not cands:
        try:
            with session.begin_nested():
                for r in session.execute(text("SELECT body FROM gov_artifacts WHERE artifact_id = 'ontology.shapes' "
                                              "AND body->'params'->>'ir_hash' = :h"), {'h': ir_hash}):
                    b = r.body if isinstance(r.body, dict) else json.loads(r.body)
                    cands.append({'semver': b['semver'], 'params': b['params']})
        except Exception:  # noqa: BLE001
            pass
    if not cands:
        for (aid, _sv), doc in governance.scan_repo().items():
            if aid == 'ontology.shapes' and doc['params'].get('ir_hash') == ir_hash:
                cands.append({'semver': doc['semver'], 'params': doc['params']})
    for c in cands:
        ir = c['params'].get('ir') or {}
        if GE.ir_canonical_hash(ir) != ir_hash:
            continue
        comp = GE.compile_ir(ir)
        comp.semver = c['semver']
        return comp
    return None


def _replay_gates(run, session, arts):
    from core.gates import engine as GE
    from core.gates import report as GR
    entries = _mf(run, session, 'gate_focus') or []
    if not entries or _inputs_lost(run):
        return
    pg = (arts.get('policy.gates') or {}).get('params') or {}
    overrides = pg.get('severity_overrides') or {}
    done = 0
    rows = []
    for e in entries:
        if not e.get('blob'):
            rows.append({'gate': e.get('gate'), 'ok': None, 'note': e.get('skipped') or 'no_focus'})
            continue
        body, st = _blob(session, e['blob'])
        if st != 'ok':
            rows.append({'gate': e.get('gate'), 'ok': None, 'note': st})
            if st == 'purged':
                run.reason('blob_purged')
            continue
        comp = _ir_for(session, arts, e.get('ir_hash'))
        if comp is None:
            rows.append({'gate': e.get('gate'), 'ok': None, 'note': 'ir_unavailable'})
            continue
        from core.gates import focus as F
        triples = GR.decode_triples(body.get('triples'))
        foc = F.expand(body['focus']) if body.get('focus') else None
        rep = GR.build(e['gate'], GE.run(comp, triples), comp, e.get('mode') or 'shadow', overrides,
                       focus=F.IRI(foc) if foc else None)
        same = GR.results_sha(rep) == e.get('rsha') and rep['outcome'] == e.get('outcome')
        rows.append({'gate': e['gate'], 'ok': same, 'outcome_recorded': e.get('outcome'),
                     'outcome_replayed': rep['outcome'], 'n_recorded': e.get('n'), 'n_replayed': rep['n_results']})
        done += 1
    if done:
        bad = [r for r in rows if r.get('ok') is False]
        run.compared += 1
        if bad:
            run.differs += 1
        run.step('gates', not bad, impl='gate_eval@1', reports=rows,
                 diffs=[{'path': f"gates.{r['gate']}", 'recorded': r.get('outcome_recorded'),
                         'replayed': r.get('outcome_replayed')} for r in bad])
    else:
        run.step('gates', None, reports=rows)


# ── IA: solo verificación ────────────────────────────────────────────────────────────────────────────────────────
def _replay_ai(run, session, arts):
    from sqlalchemy import text

    from core import ai_calls, impls
    ids = [str(x) for x in ((run.d.get('model') or {}).get('ai_call_ids') or [])]
    try:
        with session.begin_nested():
            rows = session.execute(text(
                'SELECT id, prompt_sha, output_sha, input_blob, output_blob, guardian, started_at FROM ai_calls '
                'WHERE decision_id = CAST(:d AS uuid) OR id::text = ANY(:ids) ORDER BY started_at LIMIT 40'),
                {'d': str(run.d['id']), 'ids': ids or ['-']}).all()
    except Exception:  # noqa: BLE001
        rows = []
    kind = run.d['kind']
    if kind == 'committee.portfolio_advice':
        run.reason('live_data')            # precios y cartera en vivo que no se guardan enteros
    if not rows:
        # sin llamadas de IA registradas NO se dice «texto de IA»: mcp.tool_call es una lectura registrada (Khipus no
        # escribió texto), un chat respondido sin IA es una ficha local, chat.route lo decidió Jev (modelo externo).
        # Solo una ficha anterior a ai_calls (paso 21) que cita proveedor/modelo de IA fue texto de IA.
        mdl = run.d.get('model') or {}
        if kind == 'chat.route':
            run.reason('external_model')
        elif kind in AI_KINDS and kind != 'mcp.tool_call' and (mdl.get('provider') or mdl.get('model')):
            run.reason('ai_text')
        return
    run.reason('ai_text')
    N = impls.module_view('core.numbers', arts)
    checks, first_prompt = [], None
    for r in rows:
        inp, ist = _blob(session, r.input_blob)
        out, ost = _blob(session, r.output_blob) if r.output_blob else (None, 'missing')
        item = {'ai_call': str(r.id)}
        if ist == 'purged' or ost == 'purged':
            run.reason('blob_purged')
            item['purged'] = True
            checks.append(item)
            continue
        prompt = (inp or {}).get('prompt')
        item['prompt_sha_ok'] = prompt is not None and ai_calls.sha_text(prompt) == r.prompt_sha
        text_out = (out or {}).get('output')
        if r.output_sha:
            item['output_sha_ok'] = text_out is not None and ai_calls.sha_text(text_out) == r.output_sha
        g = r.guardian or {}
        if g and text_out is not None and prompt is not None:
            att = g.get('attempt')
            if att == 'first':
                first_prompt = prompt
            src = prompt if att == 'first' else first_prompt
            if src is not None:
                bad = N.unsupported_in(text_out, src, tuple(g.get('kinds') or ('money',)))
                want = g.get('unsupported') if att == 'first' else g.get('unsupported_retry')
                if want is not None:
                    item['guardian_ok'] = len(bad) == int(want)
                    item['guardian'] = {'recorded': int(want), 'replayed': len(bad)}
        checks.append(item)
    bad = [c for c in checks if c.get('prompt_sha_ok') is False or c.get('output_sha_ok') is False
           or c.get('guardian_ok') is False]
    checked = [c for c in checks if 'prompt_sha_ok' in c]
    if checked:
        run.compared += 1
        if bad:
            run.differs += 1
    run.step('ai_steps', (not bad) if checked else None, mode='stored_output', calls=checks[:10], n=len(checks),
             impl='numbers.guard@1')


# ── el replay ────────────────────────────────────────────────────────────────────────────────────────────────────
def _explain(run, verdict, d):
    when = str(d.get('recorded_at') or '')[:16].replace('T', ' ')
    gv = run.world.get('graph_version', d.get('graph_version'))
    sv = (run.world.get('release') or {}).get('semver') or {}
    rel_es = ', '.join(f'{a} {v}' for a, v in sorted(sv.items()) if a in ('kernel.params', 'policy.committee',
                                                                            'policy.broker_risk', 'ontology.shapes',
                                                                            'nrs.formula', 'policy.numbers_guard'))
    rs = [REASONS.get(r, (r, r)) for r in run.reasons]
    ap = []
    for a in run.approximations:
        lab = APPROX_LABELS.get(a.get('code'), (a.get('code'), a.get('code')))
        if lab not in ap:
            ap.append(lab)
    if verdict == 'identical' and ap:
        es = (f'El cálculo da el MISMO resultado con lo que el sistema sabía el {when} UTC (versión del grafo {gv}'
              f'{"; reglas " + rel_es if rel_es else ""}), pero la repetición es APROXIMADA porque '
              + '; '.join(x[0] for x in ap) + '.')
        en = (f'The computation gives the SAME result with what the system knew on {when} UTC (graph version {gv}'
              f'{"; rules " + rel_es if rel_es else ""}), but the replay is APPROXIMATE because '
              + '; '.join(x[1] for x in ap) + '.')
        if run.reasons:
            es += ' Lo que no se repite: ' + '; '.join(x[0] for x in rs) + '.'
            en += ' What is not repeated: ' + '; '.join(x[1] for x in rs) + '.'
    elif verdict == 'identical':
        es = (f'La decisión se reproduce EXACTAMENTE con lo que el sistema sabía el {when} UTC (versión del grafo {gv}'
              f'{"; reglas " + rel_es if rel_es else ""}).')
        en = (f'The decision reproduces EXACTLY with what the system knew on {when} UTC (graph version {gv}'
              f'{"; rules " + rel_es if rel_es else ""}).')
        if run.reasons:
            es += ' Lo que no se repite: ' + '; '.join(x[0] for x in rs) + '.'
            en += ' What is not repeated: ' + '; '.join(x[1] for x in rs) + '.'
    elif verdict == 'differs':
        nd = sum(len(s.get('diffs') or ()) for s in run.steps) or run.differs
        es = (f'Al repetirla con lo que el sistema sabía el {when} UTC sale DISTINTO en {nd} campo(s). Hay que revisarla: '
              'o cambió el código que la calcula, o algo del registro no cuadra.')
        en = (f'Repeating it with what the system knew on {when} UTC gives a DIFFERENT result in {nd} field(s). It needs '
              'review: either the code that computes it changed, or something in the record does not add up.')
    else:
        es = 'No se puede repetir: ' + ('; '.join(x[0] for x in rs) if rs else 'no tiene un cálculo determinista') + '.'
        en = 'It cannot be replayed: ' + ('; '.join(x[1] for x in rs) if rs else 'it has no deterministic computation') + '.'
    return {'es': es, 'en': en}


def _run(session, d):
    from core import impls
    run = _Run(d)
    _integrity(run, session)
    arts, info = release_artifacts(session, d)
    run.world['release'] = {'hash': d.get('release_hash'), **info}
    run.step('artifacts', bool(info['release_hash_ok']), release=(d.get('release_hash') or '')[:16],
             source=info['source'], semver=info['semver'], missing=info['missing'], fallback=info['fallback'])
    miss = impls.missing_for(d.get('manifest'))
    run.step('impl', not miss, missing=miss, impl=(d.get('manifest') or {}).get('impl'))
    kind = d['kind']
    if miss:
        run.reason('impl_missing')
    elif not arts:
        run.reason('release_unavailable')
    else:
        if not info['release_hash_ok']:
            run.approx('release_hash_mismatch')
        fn = REPLAYERS.get(kind)
        try:
            if fn is not None:
                fn(run, session, arts)
            _replay_gates(run, session, arts)
            _replay_ai(run, session, arts)
        except TimeoutError:
            raise
        except Exception as e:  # noqa: BLE001
            log.warning('replay %s (%s): %s', d.get('id'), kind, type(e).__name__, exc_info=True)
            run.reason('error')
            run.step('error', False, error=f'{type(e).__name__}: {str(e)[:160]}')
        if fn is None and not run.reasons:
            run.reason('no_deterministic_core')
    if run.differs:
        verdict = 'differs'
    elif any(st['name'] in ('deterministic_core', 'gates') and st.get('ok') for st in run.steps):
        verdict = 'identical'
    else:
        verdict = 'not_replayable'
        if not run.reasons:
            run.reason('no_deterministic_core')
    return run, verdict


def _redact_steps(steps):
    """Sin PIN: el veredicto por paso y las RUTAS de lo que difiere, sin valores (pueden traer datos de clientes)."""
    out = []
    for s in steps:
        r = {k: v for k, v in s.items() if k in ('name', 'ok', 'impl', 'content_sha_match', 'pending', 'seal_no',
                                                    'chain_broken', 'same_lineage', 'source', 'release', 'semver',
                                                    'missing', 'compared', 'n', 'mode', 'note')}
        if s.get('diffs'):
            r['diff_paths'] = [x['path'] for x in s['diffs']][:20]
        out.append(r)
    return out


def replay(decision_id, mode='audit', full=True, record=True, principal=None, use_cache=True):
    """El replay (modo 'audit'). → dict (ver docstring del módulo). LookupError si la decisión no existe;
    ValueError con un modo que no es 'audit'; TimeoutError si otra reconstrucción ocupa el motor."""
    if mode != 'audit':
        raise ValueError('modo no soportado: solo "audit" (el contrafactual vive en 🩺 → Gobernanza → Regresión)')
    did = str(uuid.UUID(str(decision_id)))
    key = (did, bool(full))
    if use_cache:
        with _LOCK:
            hit = _CACHE.get(key)
            if hit is not None and time.time() - hit[0] < CACHE_TTL_S:
                _CACHE.move_to_end(key)
                res = dict(hit[1], cached=True)
            else:
                res = None
        if res is not None:
            if record:                    # también desde la caché: quién pidió el replay queda (deduplicado)
                _record(res, principal)
            return res
    from core import decisions
    from ontology.db import get_session_factory
    t0 = time.perf_counter()
    s = get_session_factory()()
    try:
        s.connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': True})
        d = decisions.get(s, did, redact=False)
        if d is None:
            raise LookupError(f'decisión no encontrada: {did}')
        run, verdict = _run(s, d)
    finally:
        try:
            s.rollback()
        finally:
            s.close()
    out = {'decision_id': did, 'kind': d['kind'], 'kind_label': {'es': kind_label(d['kind']),
                                                                  'en': kind_label(d['kind'], 'en')},
           'mode': mode, 'verdict': verdict, 'reproduced': verdict == 'identical',
           'fidelity': run.fidelity, 'reasons': run.reasons,
           'reasons_text': [{'code': r, 'es': REASONS.get(r, (r, r))[0], 'en': REASONS.get(r, (r, r))[1]}
                            for r in run.reasons],
           'steps': [dict(st, label={'es': STEP_LABELS.get(st['name'], (st['name'],) * 2)[0],
                                     'en': STEP_LABELS.get(st['name'], (st['name'],) * 2)[1]})
                     for st in (run.steps if full else _redact_steps(run.steps))],
           'approximations': run.approximations if full else [a['code'] for a in run.approximations],
           'approximations_text': [{'code': c, 'es': APPROX_LABELS.get(c, (c, c))[0], 'en': APPROX_LABELS.get(c, (c, c))[1]}
                                   for c in dict.fromkeys(a['code'] for a in run.approximations)],
           'world': {'recorded_at': d.get('recorded_at'), 'valid_at': d.get('valid_at'),
                     'graph_version': run.world.get('graph_version', d.get('graph_version')),
                     'release': (d.get('release_hash') or '')[:16],
                     'release_semver': (run.world.get('release') or {}).get('semver'),
                     **({'as_of': run.world['as_of']} if run.world.get('as_of') else {})},
           'explanation': _explain(run, verdict, d), 'redacted': not full,
           'cost_ms': round((time.perf_counter() - t0) * 1000, 1)}
    with _LOCK:
        STATE['runs'] += 1
        _CACHE[key] = (time.time(), out)
        _CACHE.move_to_end(key)
        while len(_CACHE) > CACHE_MAX:
            _CACHE.popitem(last=False)
    if record:
        _record(out, principal)
    return out


_RECORDED = OrderedDict()         # (principal, decisión, veredicto, código, día) ya registrados por este proceso
_RECORDED_MAX = 4096


def _seen(key):
    with _LOCK:
        if key in _RECORDED:
            return True
        _RECORDED[key] = 1
        while len(_RECORDED) > _RECORDED_MAX:
            _RECORDED.popitem(last=False)
    return False


def _already_logged(principal_id, target, verdict, code, day):
    """¿Ya hay una audit.replay de este auditor sobre esta decisión, con este veredicto y este código, hoy (UTC)?"""
    from sqlalchemy import text

    from ontology.db import session_scope
    with session_scope() as s:
        return s.execute(text(
            "SELECT 1 FROM decisions WHERE kind = 'audit.replay' AND principal_id = :p AND subject->>'target_id' = :t "
            "AND output->>'verdict' = :v AND code_sha = :c "
            "AND recorded_at >= (CAST(:day AS timestamp) AT TIME ZONE 'UTC') LIMIT 1"),
            {'p': principal_id, 't': target, 'v': verdict, 'c': code, 'day': day}).first() is not None


def _record(out, principal=None):
    """decision_outcome 'replay' sobre la decisión repetida (dedup: una por decisión, veredicto, código y día) + la
    decisión audit.replay del auditor (cola del libro: nunca suma latencia).

    E8 (cierre del lote H): el libro es sellado y nunca se purga → un replay SIN autenticar (ui:anon, GET o POST) NO
    deja audit.replay (es una lectura; solo el resultado deduplicado). Con PIN, MCP o el reloj: UNA audit.replay por
    (auditor, decisión, veredicto, código, día) — repetir «Repetir» no suma filas."""
    try:
        from core import decisions, identity
        who = principal or identity.system('ledger_replay')
        day = datetime.now(timezone.utc).date().isoformat()
        code = decisions.code_sha()
        res = {'verdict': out['verdict'], 'fidelity': out['fidelity'], 'reasons': out['reasons'],
               'differs_in': [p for s in out['steps'] for p in ([x['path'] for x in s.get('diffs') or []]
                                                               or s.get('diff_paths') or [])][:20],
               'code_sha': code, 'dedup_key': f"replay:{out['verdict']}:{code}:{day}"}
        anon = not getattr(who, 'authenticated', True)
        key = ('anon' if anon else who.id, out['decision_id'], out['verdict'], code, day)
        if _seen(key):
            return

        def write_outcome(_did=None):
            from ontology.db import session_scope
            with session_scope() as s:
                decisions.outcome(s, out['decision_id'], 'replay', res, observed_at=datetime.now(timezone.utc),
                                  source='replay:audit')

        def build():
            if anon:                      # lectura anónima: solo el resultado deduplicado, sin ficha del auditor
                write_outcome()
                return None
            if _already_logged(who.id, out['decision_id'], out['verdict'], code, day):
                return None               # (tras un reinicio el registro en memoria está vacío: manda la base)
            ctx = decisions.DecisionCtx('audit.replay', who, durability='async',
                                        subject={'target_id': out['decision_id'], 'target_kind': out['kind'],
                                                 'mode': out['mode']})
            ctx.cause('decision', out['decision_id'])
            ctx.extra['impl'] = {'replay': 'replay@1'}
            ctx.output = {k: res[k] for k in ('verdict', 'fidelity', 'reasons', 'differs_in')}
            ctx.status = 'recorded'
            return ctx, write_outcome
        decisions.submit_async(build)
    except Exception as e:  # noqa: BLE001
        log.debug('replay: auditoría no registrada (%s)', type(e).__name__)


def cache_clear():
    with _LOCK:
        _CACHE.clear()
        _GRAPHS.clear()
        _RECORDED.clear()


# ── «¿Por qué?» en lenguaje simple ───────────────────────────────────────────────────────────────────────────────
def why(session, decision_id, full=False):
    """Explicación de una decisión: quién (tipo; el id solo con PIN), qué, cuándo, con qué conocimiento (versión del
    grafo, reglas por artefacto), evidencia, puertas y resultado. Sin PIN nada del sujeto ni de los clientes (de las
    cotizaciones citadas solo el NÚMERO: el ticker de una orden o de un memo dice qué compró un cliente)."""
    from core import decisions
    d = decisions.get(session, decision_id, redact=False)
    if d is None:
        return None
    m = d.get('manifest') or {}
    refs = d.get('refs') or []
    cnt = {}
    for r in refs:
        cnt.setdefault(r['role'], {}).setdefault(r['ref_kind'], 0)
        cnt[r['role']][r['ref_kind']] += 1
    sv = (m.get('release') or {}).get('semver') or {}
    gates = [{'gate': g.get('gate'), 'outcome': g.get('outcome'), 'n': g.get('n')}
             for g in (m.get('gate_reports') or [])]
    viol = [{'rule': v.get('rule_iri'), 'severity': v.get('severity')} for v in (d.get('violations') or [])][:20]
    quotes = [{k: q.get(k) for k in ('ticker', 'src', 'as_of') if q.get(k)} for q in (m.get('quotes') or [])][:10]
    pk = d.get('principal_kind')
    who_es = {'human': 'una persona', 'agent': 'un agente de IA', 'system': 'una tarea automática del sistema',
              'external_ai': 'una IA externa (MCP)'}.get(pk, pk)
    who_en = {'human': 'a person', 'agent': 'an AI agent', 'system': 'an automatic system task',
              'external_ai': 'an external AI (MCP)'}.get(pk, pk)
    if full:
        who_es += f" ({d.get('principal_id')}{', «' + d['declared_name'] + '»' if d.get('declared_name') else ''})"
        who_en += f" ({d.get('principal_id')}{', “' + d['declared_name'] + '”' if d.get('declared_name') else ''})"
    st = STATUS_LABELS.get(d.get('status'), (d.get('status'), d.get('status')))
    when = str(d.get('recorded_at') or '')[:16].replace('T', ' ')
    ev = sum(cnt.get('evidence', {}).values())
    eff = sum(cnt.get('effect', {}).values())
    rel_txt = ', '.join(f'{a} {v}' for a, v in sorted(sv.items()))
    vo = (d.get('verdict') or {}).get('outcome')
    gates_es = ('ninguna regla avisó' if not viol else f'{len(viol)} aviso(s) de reglas'
                + (' (bloqueó)' if vo == 'block' else ''))
    gates_en = ('no rule warned' if not viol else f'{len(viol)} rule warning(s)' + (' (blocked)' if vo == 'block' else ''))
    lines_es = [f"Qué: {kind_label(d['kind'])} — {st[0]}.", f'Quién: {who_es}, por el canal «{d.get("channel")}».',
                f'Cuándo: {when} UTC.',
                f"Con qué conocimiento: versión del grafo {d.get('graph_version')}; reglas vigentes: {rel_txt or '—'}.",
                f'Evidencia citada: {ev}; efectos escritos: {eff}' + (f'; cotizaciones con fuente y fecha: {len(quotes)}'
                                                                       if quotes else '') + '.',
                f'Puertas de validación: {gates_es}.']
    lines_en = [f"What: {kind_label(d['kind'], 'en')} — {st[1]}.", f'Who: {who_en}, via the “{d.get("channel")}” channel.',
                f'When: {when} UTC.',
                f"With what knowledge: graph version {d.get('graph_version')}; rules in force: {rel_txt or '—'}.",
                f'Evidence cited: {ev}; effects written: {eff}' + (f'; quotes with source and date: {len(quotes)}'
                                                                   if quotes else '') + '.',
                f'Validation gates: {gates_en}.']
    if d.get('outcomes'):
        lines_es.append(f"Resultados posteriores registrados: {len(d['outcomes'])}.")
        lines_en.append(f"Later outcomes recorded: {len(d['outcomes'])}.")
    out = {'decision_id': str(d['id']), 'kind': d['kind'], 'kind_label': {'es': kind_label(d['kind']),
                                                                          'en': kind_label(d['kind'], 'en')},
           'status': d.get('status'), 'status_label': {'es': st[0], 'en': st[1]}, 'recorded_at': d.get('recorded_at'),
           'principal_kind': pk, 'channel': d.get('channel'), 'graph_version': d.get('graph_version'),
           'release': (d.get('release_hash') or '')[:16], 'release_semver': sv, 'code_sha': d.get('code_sha'),
           'refs': cnt, 'gates': gates, 'violations': viol, 'verdict': vo, 'n_quotes': len(quotes),
           'impl': m.get('impl'), 'replayable': replayable_kind(d['kind']),
           'sealed': bool(d.get('seal')), 'lines_es': lines_es, 'lines_en': lines_en, 'redacted': not full}
    if full:
        out['subject'] = d.get('subject')
        out['principal_id'] = d.get('principal_id')
        out['output'] = d.get('output')
        out['request_params'] = m.get('request_params')
        out['quotes'] = quotes            # el ticker de una orden o de un memo identifica al cliente: solo con PIN
    return out


def recent(session, *, kind=None, principal=None, principal_kind=None, since=None, until=None, limit=30, full=False):
    """Lista para ⚖ Auditoría: decisiones recientes con su etiqueta ES/EN y si tienen cálculo repetible."""
    from sqlalchemy import select

    from core import decisions
    t = decisions._tables()[0]
    q = select(t.c.id, t.c.seq, t.c.kind, t.c.status, t.c.principal_kind, t.c.principal_id, t.c.channel,
               t.c.recorded_at, t.c.graph_version, t.c.release_hash, t.c.verdict, t.c.declared_name)
    if kind:
        q = q.where(t.c.kind == kind) if not kind.endswith('.') else q.where(t.c.kind.startswith(kind))
    if principal:
        q = q.where(t.c.principal_id == principal)
    if principal_kind:
        q = q.where(t.c.principal_kind == principal_kind)
    if since:
        q = q.where(t.c.recorded_at >= since)
    if until:
        q = q.where(t.c.recorded_at < until)
    q = q.order_by(t.c.seq.desc()).limit(max(1, min(int(limit or 30), 200)))
    out = []
    for r in session.execute(q):
        it = {'id': str(r.id), 'seq': r.seq, 'kind': r.kind, 'kind_label': {'es': kind_label(r.kind),
                                                                            'en': kind_label(r.kind, 'en')},
              'status': r.status, 'status_label': {'es': STATUS_LABELS.get(r.status, (r.status,) * 2)[0],
                                                   'en': STATUS_LABELS.get(r.status, (r.status,) * 2)[1]},
              'principal_kind': r.principal_kind, 'channel': r.channel,
              'recorded_at': _iso(r.recorded_at), 'graph_version': r.graph_version,
              'release': (r.release_hash or '')[:12], 'verdict_outcome': (r.verdict or {}).get('outcome'),
              'replayable': replayable_kind(r.kind)}
        if full:
            it['principal_id'] = r.principal_id
            it['declared_name'] = r.declared_name
        out.append(it)
    return out


def kinds_catalog():
    from core.decisions import KINDS
    return [{'kind': k, 'es': kind_label(k), 'en': kind_label(k, 'en'), 'replayable': replayable_kind(k)}
            for k in sorted(KINDS)]


# ── muestra nocturna ─────────────────────────────────────────────────────────────────────────────────────────────
def _sample_ids(session, n=SAMPLE_N, hours=24):
    from sqlalchemy import text
    det = [k for k in DETERMINISTIC_KINDS if k not in MONEY_KINDS]
    rows = session.execute(text(
        'SELECT id FROM decisions WHERE kind = ANY(:k) AND recorded_at >= clock_timestamp() - make_interval(hours => :h)'),
        {'k': det, 'h': int(hours)}).all()
    ids = [str(r[0]) for r in rows]
    rnd = random.Random(datetime.now(timezone.utc).date().toordinal())
    pick = rnd.sample(ids, min(len(ids), int(n)))
    money = [str(r[0]) for r in session.execute(text(
        'SELECT id FROM decisions WHERE kind = ANY(:k) AND recorded_at >= clock_timestamp() - make_interval(hours => :h) '
        'ORDER BY seq DESC LIMIT :m'), {'k': list(MONEY_KINDS), 'h': int(hours), 'm': SAMPLE_MONEY_MAX})]
    return pick + [m for m in money if m not in pick]


def _ran_today(session):
    from sqlalchemy import text
    r = session.execute(text("SELECT 1 FROM decisions WHERE kind = 'audit.replay' AND subject->>'mode' = 'sample' "
                             "AND recorded_at >= date_trunc('day', clock_timestamp() AT TIME ZONE 'UTC') "
                             "AT TIME ZONE 'UTC' LIMIT 1")).first()
    return r is not None


def sample(n=SAMPLE_N, hours=24, force=False):
    """Repite la muestra y deja UNA audit.replay (system:ledger_replay_sample) con los conteos. → resumen."""
    from core import decisions, identity
    from ontology.db import ontology_available, session_scope
    if not ontology_available():
        return {'skipped': 'no_database'}
    with session_scope() as s:
        if not force and _ran_today(s):
            return {'skipped': 'already_today'}
        ids = _sample_ids(s, n, hours)
    counts = {v: 0 for v in VERDICTS}
    by_kind, differs, errors = {}, [], 0
    t0 = time.perf_counter()
    for did in ids:
        try:
            r = replay(did, record=False, use_cache=False)
        except Exception as e:  # noqa: BLE001
            errors += 1
            log.warning('replay sample %s: %s', did, type(e).__name__)
            continue
        counts[r['verdict']] += 1
        bk = by_kind.setdefault(r['kind'], {v: 0 for v in VERDICTS})
        bk[r['verdict']] += 1
        if r['verdict'] == 'differs' and len(differs) < 20:
            differs.append({'decision_id': did, 'kind': r['kind'],
                            'paths': [p for st in r['steps'] for p in [x['path'] for x in st.get('diffs') or []]][:8]})
    summary = {'sampled': len(ids), 'counts': counts, 'by_kind': by_kind, 'differs': differs, 'errors': errors,
               'hours': hours, 'cost_ms': round((time.perf_counter() - t0) * 1000, 1),
               'at': datetime.now(timezone.utc).isoformat()}
    who = identity.system('ledger_replay_sample')
    ctx = decisions.DecisionCtx('audit.replay', who, subject={'mode': 'sample', 'sampled': len(ids)})
    ctx.extra['impl'] = {'replay': 'replay@1'}
    ctx.output = summary
    ctx.status = 'recorded'
    with session_scope() as s:
        decisions.record(s, ctx, status='recorded')
    with _LOCK:
        STATE['last_sample'] = summary
        STATE['last_error'] = None
    return summary


def sample_job(force=False):
    """`system:ledger_replay_sample` (el reloj mira cada hora; corre UNA vez por día UTC)."""
    try:
        return sample(force=force)
    except Exception as e:  # noqa: BLE001
        with _LOCK:
            STATE['last_error'] = f'{type(e).__name__}: {str(e)[:160]}'
        raise


def status(engine=None):
    """Para el 🩺: la última muestra (de la base) y si hubo 'differs'."""
    out = {'last': None, 'differs': 0, 'runs': STATE['runs'], 'error': STATE['last_error']}
    try:
        from sqlalchemy import text

        from ontology.db import _get_engine, ontology_available
        if not ontology_available():
            return out
        with (engine or _get_engine()).connect() as c:
            r = c.execute(text("SELECT recorded_at, output FROM decisions WHERE kind = 'audit.replay' AND "
                               "subject->>'mode' = 'sample' ORDER BY seq DESC LIMIT 1")).first()
        if r is not None:
            o = r.output or {}
            out['last'] = {'at': _iso(r.recorded_at), 'sampled': o.get('sampled'), 'counts': o.get('counts'),
                           'errors': o.get('errors')}
            out['differs'] = int((o.get('counts') or {}).get('differs') or 0)
            out['differs_list'] = (o.get('differs') or [])[:5]
    except Exception as e:  # noqa: BLE001
        out['error'] = type(e).__name__
    return out


def _reset_for_tests():
    cache_clear()
    with _LOCK:
        STATE.update(runs=0, last_sample=None, last_error=None)
