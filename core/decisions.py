"""core/decisions.py — EL servicio de decisiones (docs/INFRA_OPERATIVA.md §2.2-§2.7; paso 6 del plan).

Una sola puerta para escribir el libro de decisiones (ontology/ledger_models.py). Cada acción deja una ficha que
nadie puede borrar ni cambiar: quién (principal tipado de core/identity), qué (kind del vocabulario cerrado,
estado, sujeto), con qué conocimiento (graph_version, release_hash, code_sha, linaje, manifiesto manifest/1),
qué evidencia y qué efectos (decision_refs) y qué salió.

    with decision_scope('ontology.action', principal, session=s, subject={...}) as ctx:
        ctx.payload_blob(validated)          # entradas exactas (blob direccionado por hash, retención legal)
        ...efectos (apply_event anota cada evento como ref 'effect' solo)...
        ctx.output = resultado
    # al salir sin error → record(session, ctx, status='executed') en la MISMA transacción que los efectos:
    #   si la escritura del libro falla, la excepción revierte también el efecto (no hay efecto sin ficha).
    # al salir con error → record_rejection(ctx): sesión AUTÓNOMA (otra conexión) que sobrevive al rollback.

Reglas:
  · append-only: nada aquí hace UPDATE/DELETE (la base lo impide igual: core/ledger_ddl);
  · el reloj es el de la base (clock_timestamp), nunca el del contenedor; `valid_at` es el "cuándo" de la pregunta;
  · forma canónica = json.dumps(sort_keys, separators compactos, ensure_ascii=False, sin NaN): sellar,
    verificar y deduplicar blobs usan EXACTAMENTE la misma función (`canonical`);
  · privacidad (§2.7): ningún texto personal en claro — `private_text()` guarda HMAC-SHA256 con clave derivada
    (HKDF de SECRET_KEY, `key_id`), largo e idioma; el dueño/IP siempre como hash (core/identity.hash_id);
  · durabilidad por prefijo del kind (sync para dinero/ontología/aprobaciones…; async para el resto). Hoy el
    camino async escribe de inmediato en una sesión autónoma y NUNCA lanza (lo perdido se cuenta en STATS).
"""
import contextvars
import hashlib
import hmac
import json
import logging
import os
import threading
import time
import uuid
import zlib
from contextlib import contextmanager
from datetime import datetime, timezone

log = logging.getLogger('khipu')

SCHEMA = 'manifest/1'
MANIFEST_MAX = 16 * 1024
OUTPUT_MAX = 8 * 1024

# §2.3 — vocabulario CERRADO (espejo del artefacto `ledger.kinds` de gobernanza, paso 9)
KINDS = frozenset((
    'ontology.action', 'ontology.raw_event', 'ontology.bulk_import', 'ontology.news_ingest',
    'proposal.create', 'proposal.auto_apply',
    'approval.grant', 'approval.deny',
    'order.preview', 'order.confirm', 'order.submit', 'order.cancel', 'order.expire',
    'trade.agent_signal', 'committee.run', 'committee.portfolio_advice',
    'research.job', 'research.run', 'claim.status',
    'alert.rule', 'alert.fire',
    'whatif.shock', 'whatif.factor_fire', 'simulation.save', 'insight.snapshot',
    'chat.route', 'chat.answer', 'mcp.tool_call',
    'reconcile.plan', 'reconcile.apply', 'reconcile.rollback',
    'policy.change', 'governance.propose', 'governance.validate', 'governance.activate', 'governance.ratify',
    'retention.purge', 'ledger.lineage_break', 'ledger.chain_break', 'ledger.chain_ack', 'audit.replay',
    'audit.gates',
))
SYNC_PREFIXES = ('order.', 'approval.', 'ontology.', 'proposal.', 'committee.', 'research.', 'claim.', 'alert.rule',
                 'reconcile.', 'policy.', 'governance.', 'trade.', 'audit.', 'retention.', 'ledger.')
STATUSES = ('proposed', 'pending_approval', 'approved', 'rejected', 'blocked', 'executed', 'failed', 'noop',
            'answered', 'fired', 'recorded', 'expired')
GENESIS = '0' * 64

_CTX = contextvars.ContextVar('kh_decision', default=None)
_LOCK = threading.Lock()
STATS = {'recorded': 0, 'rejections': 0, 'rejection_errors': 0, 'async_dropped': 0, 'last_record_ms': None,
         'last_error': None}


class LedgerUnavailable(RuntimeError):
    """El libro no se pudo escribir (base caída / tablas ausentes): el efecto NO debe confirmarse."""


# ── forma canónica y hashes ──────────────────────────────────────────────────
def canonical(obj):
    """bytes canónicos: claves ordenadas, separadores compactos, UTF-8, sin NaN/Infinity."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False,
                      default=_json_default).encode('utf-8')


def _json_default(o):
    if isinstance(o, datetime):
        return o.isoformat()
    if isinstance(o, uuid.UUID):
        return str(o)
    if isinstance(o, (set, frozenset, tuple)):
        return sorted(o, key=str) if isinstance(o, (set, frozenset)) else list(o)
    if hasattr(o, 'model_dump'):
        return o.model_dump()
    return str(o)


def sha256_hex(b):
    return hashlib.sha256(b if isinstance(b, (bytes, bytearray)) else canonical(b)).hexdigest()


# ── privacidad (§2.7) ────────────────────────────────────────────────────────
def _hkdf(ikm, info, length=32, salt=b''):
    prk = hmac.new(salt or b'\x00' * 32, ikm, hashlib.sha256).digest()
    out, t, i = b'', b'', 1
    while len(out) < length:
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
        out += t
        i += 1
    return out[:length]


def pii_key():
    """(clave, key_id, débil). k_pii = HKDF(SECRET_KEY, 'khipus-ledger-pii'); key_id NO revela la clave."""
    try:
        from core.pin import DEFAULT_SECRET_KEY, secret_key_default
        weak = secret_key_default()
    except Exception:  # noqa: BLE001
        DEFAULT_SECRET_KEY, weak = 'khipu-dev-secret-change-me', True
    sk = (os.getenv('SECRET_KEY') or DEFAULT_SECRET_KEY).encode()
    k = _hkdf(sk, b'khipus-ledger-pii')
    return k, 'k1-' + hashlib.sha256(k).hexdigest()[:8], weak


def pii_hmac(text, lang=None):
    """Huella de un texto personal: {hmac, key_id, len, lang}. En producción con SECRET_KEY por defecto no se
    calcula (sería forjable): {privacy_key_weak: true, len, lang}."""
    s = '' if text is None else str(text)
    k, key_id, weak = pii_key()
    out = {'len': len(s)}
    if lang:
        out['lang'] = str(lang)[:5]
    try:
        from core.pin import in_production
        prod = in_production()
    except Exception:  # noqa: BLE001
        prod = False
    if weak and prod:
        out['privacy_key_weak'] = True
        return out
    out['hmac'] = hmac.new(k, s.encode('utf-8'), hashlib.sha256).hexdigest()
    out['key_id'] = key_id
    if weak:
        out['weak_key'] = True
    return out


# ── sello del mundo (κ) ──────────────────────────────────────────────────────
def code_sha():
    v = (os.getenv('RAILWAY_GIT_COMMIT_SHA') or '').strip()
    return v[:40] if v else 'unknown'


def stamp():
    """graph_version y linaje del grafo (en memoria, sin SQL), release_hash y code_sha."""
    out = {'graph_version': None, 'graph_lineage': None, 'release_hash': GENESIS, 'release_label': 'none',
           'code_sha': code_sha()}
    try:
        from core.hotviews import signals
        k = signals.known()
        out['graph_version'] = int(k.get('v') or 0)
        out['graph_lineage'] = k.get('lineage')
        rel, label = signals.release_hash()
        out['release_hash'], out['release_label'] = rel, label
    except Exception:  # noqa: BLE001
        pass
    try:   # paso 9: qué versión de cada artefacto regía (manifest/1 → release.semver)
        from core import governance
        out['release_semver'] = {a: v['semver'] for a, v in sorted(governance.active().artifacts.items())}
        fb = governance.fallbacks()   # artefactos que el release de la base no trae (leídos del repo, sin aprobar)
        if fb:
            out['release_fallback'] = fb
    except Exception:  # noqa: BLE001
        pass
    return out


def default_durability(kind):
    return 'sync' if any(kind == p or kind.startswith(p) for p in SYNC_PREFIXES) else 'async'


# ── contexto de una decisión ─────────────────────────────────────────────────
class DecisionCtx:
    """Se llena desde los puntos instrumentados (apply_event → effect) o a mano. Nunca escribe por sí solo."""

    def __init__(self, kind, principal, *, subject=None, durability=None, parent_id=None, supersedes_id=None,
                 correlation_id=None, valid_at=None, expires_at=None):
        if kind not in KINDS:
            raise ValueError(f'kind de decisión fuera del vocabulario (ledger.kinds): {kind!r}')
        self.id = uuid.uuid4()
        self.kind = kind
        self.principal = principal
        self.subject = dict(subject or {})
        self.durability = durability or default_durability(kind)
        self.parent_id = parent_id
        self.supersedes_id = supersedes_id
        self.correlation_id = (str(correlation_id)[:64] if correlation_id else None)
        self.valid_at = valid_at or datetime.now(timezone.utc)
        self.expires_at = expires_at
        self.stamp = stamp()
        self.refs = {}                    # (role, ref_kind, ref_id) → {ref_hash, as_of, note}
        self.blobs = {}                   # sha → (kind, canonical bytes, retention)
        self.inputs_sha = None
        self.output = None
        self.status = None
        self.verdict = {}
        self.violations = []
        self.model = None
        self.extra = {}                   # campos extra del manifiesto (views, quotes, privacy, channel_proof…)
        self.recorded = False
        self.error = None
        self.t0 = time.perf_counter()

    # -- referencias
    def ref(self, role, ref_kind, ref_id, *, ref_hash=None, as_of=None, **note):
        if ref_id is None:
            return
        key = (role, str(ref_kind)[:20], str(ref_id)[:128])
        cur = self.refs.get(key)
        if cur is None:
            self.refs[key] = {'ref_hash': ref_hash, 'as_of': as_of, 'note': note or None}
        elif note:
            cur['note'] = {**(cur['note'] or {}), **note}

    def evidence(self, ref_kind, ref_id, *, ref_hash=None, as_of=None, **note):
        self.ref('evidence', ref_kind, ref_id, ref_hash=ref_hash, as_of=as_of, **note)

    def effect(self, ref_kind, ref_id, **note):
        self.ref('effect', ref_kind, ref_id, **note)

    def cause(self, ref_kind, ref_id, **note):
        self.ref('cause', ref_kind, ref_id, **note)

    def policy(self, artifact, artifact_hash=None):
        self.ref('policy', 'artifact', artifact, ref_hash=artifact_hash)

    def read_view(self, name, generation, content_sha=None, key=None):
        rid = f'{name}@{generation}' + (f':{key}' if key else '')
        self.ref('view', 'view', rid[:128], ref_hash=content_sha)
        self.extra.setdefault('views', []).append(
            {k: v for k, v in (('name', name), ('version', generation), ('key', key), ('content_sha', content_sha))
             if v is not None})

    def quote(self, q):
        q = {k: q.get(k) for k in ('ticker', 'px', 'prev', 'currency', 'src', 'as_of') if q.get(k) is not None}
        self.extra.setdefault('quotes', []).append(q)
        if q.get('ticker'):
            self.ref('evidence', 'quote', f"{q['ticker']}@{q.get('as_of') or ''}"[:128], ref_hash=sha256_hex(q))

    def ai_call(self, ai_call_id):
        self.ref('input', 'ai_call', ai_call_id)
        m = self.model or {}
        m.setdefault('ai_call_ids', []).append(str(ai_call_id))
        self.model = m

    def params(self, **overrides):
        self.extra.setdefault('request_params', {}).update(overrides)

    def channel_proof(self, **proof):
        self.extra['channel_proof'] = proof

    def private_text(self, field, text, lang=None):
        """Texto PERSONAL (mensaje del chat, nota libre de un usuario sin PIN): solo su huella HMAC."""
        self.extra.setdefault('privacy', {})[str(field)[:40]] = pii_hmac(text, lang)

    def gate(self, report):
        """Veredicto de una puerta (paso 10+): {outcome, shapes_hash?, violations:[{rule_iri, severity, focus, value}]}."""
        order = {'pass': 0, 'warn': 1, 'requires_approval': 2, 'block': 3}
        cur = self.verdict.get('outcome', 'pass')
        new = (report or {}).get('outcome', 'pass')
        self.verdict['outcome'] = new if order.get(new, 0) >= order.get(cur, 0) else cur
        for v in (report or {}).get('violations') or ():
            self.violations.append({**v, 'shapes_hash': (report or {}).get('shapes_hash') or GENESIS})

    def blob(self, kind, obj, retention='legal'):
        """Contenido direccionado por hash. Devuelve el sha (de los bytes canónicos SIN comprimir)."""
        b = canonical(obj)
        sha = hashlib.sha256(b).hexdigest()
        self.blobs[sha] = (str(kind)[:24], b, retention)
        return sha

    def payload_blob(self, obj):
        self.inputs_sha = self.blob('payload', obj)
        return self.inputs_sha


def current():
    return _CTX.get()


def note_event(ev):
    """Hook de ontology.service.apply_event: cada evento escrito dentro de un scope es un EFECTO de la decisión."""
    ctx = _CTX.get()
    if ctx is not None and not ctx.recorded:
        try:
            ctx.effect('event', str(ev.id), type=ev.event_type)
        except Exception:  # noqa: BLE001
            pass


# ── filas ────────────────────────────────────────────────────────────────────
def _tables():
    from ontology.ledger_models import (Decision, DecisionBlob, DecisionOutcome, DecisionRef,
                                        DecisionViolation)
    return (Decision.__table__, DecisionRef.__table__, DecisionBlob.__table__, DecisionViolation.__table__,
            DecisionOutcome.__table__)


def _manifest(ctx, lineage_id, rejected=False):
    st = ctx.stamp
    m = {'schema': SCHEMA, 'valid_at': ctx.valid_at.isoformat(),
         'knowledge': {'graph_version': st['graph_version'], 'graph_lineage': st['graph_lineage'],
                       'lineage_id': str(lineage_id), 'source': 'pg'},
         'release': {'hash': st['release_hash'], 'label': st['release_label'],
                     **({'semver': st['release_semver']} if st.get('release_semver') else {}),
                     **({'fallback': st['release_fallback']} if st.get('release_fallback') else {})},
         'code_sha': st['code_sha'],
         'principal': {'id': ctx.principal.id, 'kind': ctx.principal.kind, 'auth': ctx.principal.auth,
                       'channel': ctx.principal.channel},
         'impl': {'decisions': 'record@1'}}
    if getattr(ctx.principal, 'pin_source', None):
        m['principal']['pin_source'] = ctx.principal.pin_source
    if ctx.inputs_sha:
        m['inputs_blob'] = ctx.inputs_sha
    for k, v in ctx.extra.items():
        if k == 'impl' and isinstance(v, dict):
            m['impl'].update(v)
        else:
            m[k] = v
    ev = sum(1 for (r, _k, _i) in ctx.refs if r == 'evidence')
    if ev:
        m['evidence_summary'] = {'refs': ev}
    if rejected and ctx.parent_id:
        m['parent_pending'] = str(ctx.parent_id)
    if len(canonical(m)) > MANIFEST_MAX:          # lo grande va a un blob; el manifiesto guarda su sha
        big = {k: m.pop(k) for k in list(m) if k in ('views', 'quotes', 'request_params', 'channel_proof')}
        m['overflow_blob'] = ctx.blob('inputs', big)
    return m


def _rows(ctx, status, lineage_id, output, rejected=False):
    if status not in STATUSES:
        raise ValueError(f'estado de decisión inválido: {status!r}')
    manifest = _manifest(ctx, lineage_id, rejected)
    out = output
    out_sha = None
    if out is not None:
        ob = canonical(out)
        out_sha = hashlib.sha256(ob).hexdigest()
        if len(ob) > OUTPUT_MAX:
            ctx.blobs[out_sha] = ('output', ob, 'legal' if ctx.durability == 'sync' else 'standard_90d')
            out = {'blob': out_sha, 'size': len(ob), 'truncated': True}
    p = ctx.principal
    dec = {
        'id': ctx.id, 'kind': ctx.kind, 'kind_version': 1, 'durability': ctx.durability, 'status': status,
        'parent_id': None if rejected else ctx.parent_id, 'supersedes_id': None if rejected else ctx.supersedes_id,
        'correlation_id': ctx.correlation_id, 'principal_id': p.id[:96], 'principal_kind': p.kind,
        'auth': p.auth, 'channel': (p.channel or 'api')[:12],
        # las columnas son String(80)/String(96): una etiqueta larga NUNCA debe tumbar el libro (y con él la Acción)
        'declared_name': ((p.declared_name or '')[:80] or None),
        'on_behalf_of': ((p.on_behalf_of or '')[:96] or None), 'subject': ctx.subject, 'valid_at': ctx.valid_at,
        'expires_at': ctx.expires_at, 'lineage_id': lineage_id, 'graph_version': ctx.stamp['graph_version'],
        'release_hash': ctx.stamp['release_hash'], 'code_sha': ctx.stamp['code_sha'], 'manifest': manifest,
        'manifest_sha': sha256_hex(manifest), 'inputs_sha': ctx.inputs_sha, 'output': out, 'output_sha': out_sha,
        'verdict': ctx.verdict or {}, 'model': ctx.model,
    }
    retention = 'legal' if ctx.durability == 'sync' else 'standard_90d'
    # D3: blobs de decisiones sync = 'legal' (para siempre); de las async (chat, qué-pasaría-si) = 90 días
    blobs = [{'sha256': sha, 'kind': kind, 'body': zlib.compress(b, 6), 'size_bytes': len(b),
              'retention_class': 'legal' if (ret == 'legal' and retention == 'legal') else 'standard_90d'}
             for sha, (kind, b, ret) in ctx.blobs.items()]
    refs = [] if rejected else [
        {'decision_id': ctx.id, 'role': r, 'ref_kind': k, 'ref_id': i, 'ref_hash': v['ref_hash'],
         'as_of': v['as_of'], 'note': v['note']} for (r, k, i), v in ctx.refs.items()]
    if rejected:          # en un rechazo solo cuenta lo que se CITÓ, no lo que se intentó escribir
        refs = [{'decision_id': ctx.id, 'role': r, 'ref_kind': k, 'ref_id': i, 'ref_hash': v['ref_hash'],
                 'as_of': v['as_of'], 'note': v['note']} for (r, k, i), v in ctx.refs.items() if r != 'effect']
    viols = [{'decision_id': ctx.id, 'ord': n, 'rule_iri': str(v.get('rule_iri'))[:96],
              'severity': v.get('severity', 'info'), 'focus': str(v.get('focus', ''))[:128],
              'value': v.get('value'), 'shapes_hash': v.get('shapes_hash') or GENESIS}
             for n, v in enumerate(ctx.violations[:200])]
    return dec, blobs, refs, viols


_DEC_COLS = ('id', 'kind', 'kind_version', 'durability', 'status', 'parent_id', 'supersedes_id', 'correlation_id',
             'principal_id', 'principal_kind', 'auth', 'channel', 'declared_name', 'on_behalf_of', 'subject',
             'valid_at', 'expires_at', 'lineage_id', 'graph_version', 'release_hash', 'code_sha', 'manifest',
             'manifest_sha', 'inputs_sha', 'output', 'output_sha', 'verdict', 'model')
_DEC_CAST = {'id': 'uuid', 'parent_id': 'uuid', 'supersedes_id': 'uuid', 'lineage_id': 'uuid', 'subject': 'jsonb',
             'manifest': 'jsonb', 'output': 'jsonb', 'verdict': 'jsonb', 'model': 'jsonb', 'valid_at': 'timestamptz',
             'expires_at': 'timestamptz'}
# UNA sola ida y vuelta a la base: blobs + decisión + referencias en la misma sentencia (CTE). Las FK de
# decisions→blobs y refs→decisions se comprueban al final de la sentencia y ven las filas de las CTE hermanas.
_INSERT_SQL = (
    "WITH b AS (INSERT INTO decision_blobs (sha256, kind, body, size_bytes, retention_class) "
    "SELECT x.sha256, x.kind, decode(x.body, 'base64'), x.size_bytes, x.retention_class "
    "FROM jsonb_to_recordset(CAST(:blobs AS jsonb)) AS x(sha256 text, kind text, body text, size_bytes int, "
    "retention_class text) ON CONFLICT (sha256) DO NOTHING RETURNING 1), "
    "d AS (INSERT INTO decisions (" + ', '.join(_DEC_COLS) + ") VALUES (" +
    ', '.join(f'CAST(:{c} AS {_DEC_CAST[c]})' if c in _DEC_CAST else f':{c}' for c in _DEC_COLS) +
    ") RETURNING id) "
    "INSERT INTO decision_refs (decision_id, role, ref_kind, ref_id, ref_hash, as_of, note) "
    "SELECT CAST(:id AS uuid), r.role, r.ref_kind, r.ref_id, r.ref_hash, r.as_of, r.note "
    "FROM jsonb_to_recordset(CAST(:refs AS jsonb)) AS r(role text, ref_kind text, ref_id text, ref_hash text, "
    "as_of timestamptz, note jsonb) ON CONFLICT DO NOTHING")


def _dumps(v):
    return None if v is None else json.dumps(v, ensure_ascii=False, separators=(',', ':'), default=_json_default)


def _insert(conn_or_session, ctx, status, output, lineage_id, rejected=False):
    import base64

    from sqlalchemy import text
    dec, blobs, refs, viols = _rows(ctx, status, lineage_id, output, rejected)
    params = {c: dec[c] for c in _DEC_COLS}
    for c in ('id', 'parent_id', 'supersedes_id', 'lineage_id'):
        params[c] = str(params[c]) if params[c] is not None else None
    for c in ('subject', 'manifest', 'output', 'verdict', 'model'):
        params[c] = _dumps(params[c])
    params['blobs'] = _dumps([{**b, 'body': base64.b64encode(b['body']).decode('ascii')} for b in blobs])
    params['refs'] = _dumps([{k: v for k, v in r.items() if k != 'decision_id'} for r in refs])
    conn_or_session.execute(text(_INSERT_SQL), params)
    if viols:
        t_viol = _tables()[3]
        conn_or_session.execute(t_viol.insert().values(viols))
    return dec


def _lineage(session=None):
    from core import ledger
    return ledger.lineage_id()


def _g8(ctx, status):
    """Meta-puerta G8 (paso 10, SOMBRA): la ficha misma cumple decision.ttl (kind del vocabulario, principal
    tipado, release presente, cotizaciones con fecha y fuente, dinero ejecutado sin bloqueo). Lo que encuentre
    queda en las violaciones de ESTA decisión. Nunca lanza."""
    try:
        from core import gates
        from core.gates import focus as gf
        from core.gates import report as gr
        triples, foc = gf.gather_decision(ctx, status)
        rep = gates.evaluate('ledger.g8', triples, foc)
        if rep is not None and rep['results']:
            gr.attach(ctx, rep)
    except Exception:  # noqa: BLE001
        pass


def record(session, ctx, *, status='executed', output=None, expires_at=None):
    """Escribe la decisión. sync: en la MISMA sesión que el efecto (si falla, lanza y el caller revierte todo).
    async: sesión autónoma, nunca lanza (lo perdido se cuenta)."""
    if ctx.recorded:
        return ctx.id
    if output is not None:
        ctx.output = output
    if expires_at is not None:
        ctx.expires_at = expires_at
    ctx.status = status
    _g8(ctx, status)
    t0 = time.perf_counter()
    if ctx.durability == 'async':
        try:
            _autonomous(lambda s: _insert(s, ctx, status, ctx.output, _lineage()))
        except Exception as e:  # noqa: BLE001
            with _LOCK:
                STATS['async_dropped'] += 1
                STATS['last_error'] = f'{type(e).__name__}: {str(e)[:160]}'
            log.warning('decisions: decisión async perdida (%s)', type(e).__name__)
            return None
    else:
        try:
            _insert(session, ctx, status, ctx.output, _lineage())
        except Exception as e:  # noqa: BLE001 — sin ficha no hay efecto: que el caller revierta
            with _LOCK:
                STATS['last_error'] = f'{type(e).__name__}: {str(e)[:160]}'
            raise LedgerUnavailable(f'no se pudo registrar la decisión ({type(e).__name__}): '
                                    f'{str(e).splitlines()[0][:200] if str(e) else ""}') from e
    ctx.recorded = True
    ms = round((time.perf_counter() - t0) * 1000, 3)
    with _LOCK:
        STATS['recorded'] += 1
        STATS['last_record_ms'] = ms
    return ctx.id


def _autonomous(fn):
    """Transacción PROPIA (otra conexión del pool): confirma aunque la del caller se revierta. lock_timeout corto:
    nunca espera a la transacción del mismo hilo (que no avanzaría mientras esperamos)."""
    from sqlalchemy import text

    from ontology.db import get_session_factory
    s = get_session_factory()()
    try:
        s.execute(text("SET LOCAL lock_timeout = '2s'"))
        out = fn(s)
        s.commit()
        return out
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def safe_error(exc):
    """Resumen del error SIN valores de entrada (Pydantic incluye el input del usuario en sus errores)."""
    out = {'type': type(exc).__name__}
    try:
        from pydantic import ValidationError
        ve = exc if isinstance(exc, ValidationError) else (
            exc.__cause__ if isinstance(getattr(exc, '__cause__', None), ValidationError) else None)
        if ve is not None:
            out['code'] = 'invalid_input'
            out['errors'] = [{'loc': [str(x) for x in (e.get('loc') or ())], 'type': e.get('type')}
                             for e in ve.errors()[:20]]
            return out
    except Exception:  # noqa: BLE001
        pass
    code = getattr(exc, 'code', None)
    if isinstance(code, str):
        out['code'] = code[:40]
    out['message'] = (str(exc).splitlines()[0] if str(exc) else '')[:300]
    return out


def record_rejection(ctx, status='rejected', error=None, report=None):
    """Rechazo/bloqueo/fallo en una sesión AUTÓNOMA: queda aunque el caller revierta su transacción.
    Nunca lanza (devuelve None si ni siquiera se pudo escribir; se cuenta en STATS)."""
    if ctx.recorded:
        return ctx.id
    if report is not None:
        ctx.gate(report)
    _g8(ctx, status)
    out = {'error': safe_error(error)} if error is not None else (ctx.output or None)

    def _do(s):
        try:
            with s.begin_nested():
                return _insert(s, ctx, status, out, _lineage(), rejected=True)
        except Exception:  # noqa: BLE001 — p. ej. el blob lo tiene sin confirmar la transacción del caller
            ctx.blobs.clear()
            ctx.inputs_sha = None
            ctx.extra['inputs_blob_unavailable'] = True
            return _insert(s, ctx, status, out, _lineage(), rejected=True)
    try:
        _autonomous(_do)
    except Exception as e:  # noqa: BLE001
        with _LOCK:
            STATS['rejection_errors'] += 1
            STATS['last_error'] = f'{type(e).__name__}: {str(e)[:160]}'
        log.warning('decisions: no se registró el rechazo %s (%s)', ctx.kind, type(e).__name__)
        return None
    ctx.recorded = True
    ctx.status = status
    with _LOCK:
        STATS['rejections'] += 1
    return ctx.id


def _set_guc(session, value):
    from sqlalchemy import text
    session.execute(text("SELECT set_config('khipus.decision_id', :v, true)"), {'v': value or ''})


@contextmanager
def decision_scope(kind, principal, *, session, subject=None, durability=None, parent_id=None,
                   supersedes_id=None, correlation_id=None, valid_at=None, rejection_status=None):
    """Reserva decision_id, marca la transacción (`khipus.decision_id`, guardia del paso 22) y abre el contexto.
    Al salir: record(status=ctx.status or 'executed'); con excepción → record_rejection y se relanza.
    `rejection_status(exc)` → 'rejected' | 'failed' | 'blocked' (por defecto: 'rejected' para errores de
    validación/dominio — ValueError y subclases —, 'failed' para el resto)."""
    outer = _CTX.get()
    if parent_id is None and outer is not None:
        parent_id = outer.id
    ctx = DecisionCtx(kind, principal, subject=subject, durability=durability, parent_id=parent_id,
                      supersedes_id=supersedes_id, correlation_id=correlation_id or (outer.correlation_id
                                                                                       if outer else None),
                      valid_at=valid_at)
    tok = _CTX.set(ctx)
    try:
        if session is not None and ctx.durability == 'sync':
            _set_guc(session, str(ctx.id))
        yield ctx
        if session is not None:     # paso 10: puertas G1 diferidas (objetos/factores) sobre el estado FINAL
            try:
                from core import gates as _gates
                _gates.flush_deferred(session)
            except Exception:  # noqa: BLE001
                pass
    except BaseException as e:
        _CTX.reset(tok)
        tok = None
        ctx.error = e
        if isinstance(e, Exception):
            st = (rejection_status(e) if rejection_status else
                  ('rejected' if isinstance(e, ValueError) else 'failed'))
            record_rejection(ctx, status=st, error=e)
        raise
    finally:
        if tok is not None:
            _CTX.reset(tok)
    record(session, ctx, status=ctx.status or 'executed')
    if session is not None and outer is not None and outer.durability == 'sync':
        try:
            _set_guc(session, str(outer.id))
        except Exception:  # noqa: BLE001
            pass


# ── después de la decisión: aprobar, enlazar, resultados, corrección ────────
def approve(session, target_id, principal, *, verdict='grant', effective_from=None, note=None):
    """approval.grant | approval.deny con parent_id = la decisión aprobada. Exige un HUMANO con PIN; si quien
    pidió fue un agente, una IA (MCP) o el reloj, el aprobador siempre es distinto del solicitante (§2.2). Una
    decisión que pidió el propio operador SÍ la puede aprobar él (D1: un solo aprobador, op:fabrizio).
    Solo se aprueba lo que ESPERA aprobación (proposed | pending_approval) y una sola vez: un segundo
    approval.* sobre la misma decisión → ValueError (candado de asesoría por decisión contra la carrera)."""
    from sqlalchemy import select, text
    if verdict not in ('grant', 'deny'):
        raise ValueError("verdict debe ser 'grant' o 'deny'")
    if not getattr(principal, 'is_human_pin', False):
        raise PermissionError('aprobar exige una persona autenticada con PIN (op:…)')
    t_dec = _tables()[0]
    tid = _uuid(target_id)
    # dos aprobaciones simultáneas de la misma decisión: la segunda espera y luego ve la primera
    session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))'), {'k': f'approve:{tid}'})
    row = session.execute(select(t_dec.c.id, t_dec.c.principal_id, t_dec.c.principal_kind, t_dec.c.kind,
                                 t_dec.c.status).where(t_dec.c.id == tid)).first()
    if row is None:
        raise LookupError(f'decisión no encontrada: {target_id}')
    if row.principal_kind in ('agent', 'external_ai', 'system') and row.principal_id == principal.id:
        raise PermissionError('el aprobador debe ser distinto del solicitante')
    if row.status not in ('proposed', 'pending_approval'):
        raise ValueError(f'la decisión no espera aprobación (estado {row.status!r})')
    prior = session.execute(select(t_dec.c.id).where(t_dec.c.parent_id == row.id,
                                                     t_dec.c.kind.in_(('approval.grant', 'approval.deny')))
                            .limit(1)).first()
    if prior is not None:
        raise ValueError(f'la decisión ya fue resuelta por {prior[0]}')
    kind = 'approval.grant' if verdict == 'grant' else 'approval.deny'
    with decision_scope(kind, principal, session=session, parent_id=row.id,
                        subject={'target_id': str(row.id), 'target_kind': row.kind}) as ctx:
        ctx.cause('decision', str(row.id))
        if note:
            ctx.extra['note_blob'] = ctx.blob('payload', {'note': str(note)[:2000]})
        ctx.output = {'verdict': verdict, 'effective_from': effective_from.isoformat()
                      if isinstance(effective_from, datetime) else effective_from}
        ctx.status = 'approved' if verdict == 'grant' else 'rejected'
    return ctx.id


def link(session, decision_id, role, ref_kind, ref_id, *, ref_hash=None, as_of=None, **note):
    """Añade una referencia DESPUÉS (solo INSERT; repetirla es un no-op)."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    t_ref = _tables()[1]
    session.execute(pg_insert(t_ref).values(
        decision_id=_uuid(decision_id), role=role, ref_kind=str(ref_kind)[:20], ref_id=str(ref_id)[:128],
        ref_hash=ref_hash, as_of=as_of, note=note or None).on_conflict_do_nothing())


def link_effect(session, decision_id, ref_kind, ref_id, **note):
    link(session, decision_id, 'effect', ref_kind, ref_id, **note)


def outcome(session, decision_id, outcome_kind, result, *, observed_at, source):
    """Resultado posterior (nunca se pisa; el vigente es el último). Con result['dedup_key'] no se repite."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    t_out = _tables()[4]
    res = session.execute(pg_insert(t_out).values(
        decision_id=_uuid(decision_id), outcome_kind=outcome_kind, observed_at=observed_at,
        source=str(source)[:40], result=result, release_hash=stamp()['release_hash'],
    ).on_conflict_do_nothing().returning(t_out.c.id)).first()
    return res[0] if res else None


def supersede(session, old_id, principal, reason, *, kind=None, output=None):
    """Corrección: decisión NUEVA con supersedes_id (nunca un UPDATE). 'superseded' se deriva, no es un estado."""
    from sqlalchemy import select
    t_dec = _tables()[0]
    row = session.execute(select(t_dec.c.id, t_dec.c.kind).where(t_dec.c.id == _uuid(old_id))).first()
    if row is None:
        raise LookupError(f'decisión no encontrada: {old_id}')
    with decision_scope(kind or row.kind, principal, session=session, supersedes_id=row.id,
                        subject={'supersedes': str(row.id)}) as ctx:
        ctx.cause('decision', str(row.id))
        ctx.extra['reason_blob'] = ctx.blob('payload', {'reason': str(reason)[:2000]})
        ctx.output = output
        ctx.status = 'recorded'
    return ctx.id


def _uuid(v):
    return v if isinstance(v, uuid.UUID) else uuid.UUID(str(v))


# ── lectura ──────────────────────────────────────────────────────────────────
PUBLIC_FIELDS = ('id', 'seq', 'kind', 'status', 'durability', 'principal_kind', 'channel', 'recorded_at',
                 'graph_version', 'release_hash', 'code_sha', 'manifest_sha', 'inputs_sha', 'output_sha',
                 'parent_id', 'supersedes_id')


def _row_dict(r, redact):
    d = dict(r._mapping)
    for k, v in list(d.items()):
        if isinstance(v, uuid.UUID):
            d[k] = str(v)
        elif isinstance(v, datetime):
            d[k] = v.isoformat()
    d['txid'] = str(d['txid']) if d.get('txid') is not None else None
    d['verdict_outcome'] = (d.get('verdict') or {}).get('outcome')
    if redact:
        d = {k: d.get(k) for k in PUBLIC_FIELDS + ('verdict_outcome',)}
        d['redacted'] = True
    return d


def list_decisions(session, *, kind=None, principal=None, status=None, entity=None, since=None, limit=50,
                   redact=True):
    from sqlalchemy import select
    t_dec = _tables()[0]
    q = select(t_dec)
    if kind:
        q = q.where(t_dec.c.kind == kind)
    if principal:
        q = q.where(t_dec.c.principal_id == principal)
    if status:
        q = q.where(t_dec.c.status == status)
    if entity:
        q = q.where(t_dec.c.subject.contains({'entity_ids': [entity]}))
    if since:
        q = q.where(t_dec.c.recorded_at >= since)
    q = q.order_by(t_dec.c.seq.desc()).limit(max(1, min(int(limit or 50), 500)))
    return [_row_dict(r, redact) for r in session.execute(q)]


def get(session, decision_id, *, redact=True, with_blobs=False):
    from sqlalchemy import select, text
    t_dec, t_ref, t_blob, t_viol, t_out = _tables()
    did = _uuid(decision_id)
    r = session.execute(select(t_dec).where(t_dec.c.id == did)).first()
    if r is None:
        return None
    d = _row_dict(r, redact)
    if redact:
        return d
    d['refs'] = [{**{k: (str(v) if isinstance(v, uuid.UUID) else v.isoformat() if isinstance(v, datetime) else v)
                     for k, v in dict(x._mapping).items() if k != 'txid'}}
                 for x in session.execute(select(t_ref).where(t_ref.c.decision_id == did))]
    d['violations'] = [dict(x._mapping) for x in session.execute(select(t_viol).where(t_viol.c.decision_id == did))]
    for v in d['violations']:
        v['decision_id'] = str(v['decision_id'])
    d['outcomes'] = [{k: (str(v) if isinstance(v, uuid.UUID) else v.isoformat() if isinstance(v, datetime)
                          else v) for k, v in dict(x._mapping).items() if k != 'txid'}
                     for x in session.execute(select(t_out).where(t_out.c.decision_id == did)
                                              .order_by(t_out.c.id))]
    d['children'] = [str(x[0]) for x in session.execute(select(t_dec.c.id).where(
        (t_dec.c.parent_id == did) | (t_dec.c.supersedes_id == did)).order_by(t_dec.c.seq))]
    seal = session.execute(text("SELECT seal_no, hash, sealed_at FROM ledger_seals "
                                "WHERE row_table = 'decisions' AND row_id = :i"), {'i': str(did)}).first()
    d['seal'] = ({'seal_no': seal[0], 'hash': seal[1], 'sealed_at': seal[2].isoformat()} if seal else None)
    if with_blobs:
        shas = {x for x in (d.get('inputs_sha'), (d.get('output') or {}).get('blob') if isinstance(d.get('output'), dict)
                            else None, (d.get('manifest') or {}).get('overflow_blob')) if x}
        d['blobs'] = {}
        for sha in shas:
            b = session.execute(select(t_blob).where(t_blob.c.sha256 == sha)).first()
            if b is None:
                continue
            d['blobs'][sha] = {'kind': b.kind, 'retention_class': b.retention_class, 'size_bytes': b.size_bytes,
                               'purged': b.body is None,
                               'body': json.loads(zlib.decompress(bytes(b.body))) if b.body is not None else None}
    return d


def explain(d, lang='es'):
    """Explicación de una línea en lenguaje simple (ES/EN) a partir de get(..., redact=False)."""
    en = lang == 'en'
    who = d.get('declared_name') and f"{d.get('principal_id')} ({d.get('declared_name')})" or d.get('principal_id')
    st = {'executed': ('se ejecutó', 'was executed'), 'rejected': ('se rechazó', 'was rejected'),
          'failed': ('falló', 'failed'), 'blocked': ('fue bloqueada por una regla', 'was blocked by a rule'),
          'approved': ('se aprobó', 'was approved'), 'pending_approval': ('espera aprobación', 'awaits approval')}
    s = st.get(d.get('status'), (d.get('status'), d.get('status')))[1 if en else 0]
    n_eff = sum(1 for r in d.get('refs') or () if r.get('role') == 'effect')
    if en:
        return (f"{d.get('kind')} by {who} via {d.get('channel')} {s}; it saw graph version "
                f"{d.get('graph_version')} and wrote {n_eff} event(s).")
    return (f"{d.get('kind')} de {who} por {d.get('channel')} {s}; vio la versión {d.get('graph_version')} "
            f"del grafo y escribió {n_eff} evento(s).")


def stats():
    with _LOCK:
        return dict(STATS)
