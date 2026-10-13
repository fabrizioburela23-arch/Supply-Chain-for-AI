"""core/decision_sites.py — decisiones del COMITÉ, la INVESTIGACIÓN, las PROPUESTAS y las ALERTAS
(docs/INFRA_OPERATIVA.md §2.5; pasos 18 y 19 del plan).

Los sitios de llamada viven en sus módulos (research/committee.py, research/runner.py, research/falsifiers.py,
research/outcomes.py, ontology/agents.py, ontology/api.py, brokerage/service.py, core/ai_usage.py); aquí está lo que
comparten, para que cada sitio sea una o dos líneas y todos escriban la ficha igual:

  comité        committee.run (al guardar el memo; claims citados con su huella, política policy.committee, cotización
                con fuente y fecha, paquete COMPLETO como blob — sin el corte de 12.000 caracteres —, transcripción,
                puerta G5 en sombra) · approval.grant / approval.deny sobre el memo (envuelven la previsualización,
                que queda como hija) · committee.portfolio_advice (después de responder: nunca suma latencia)
  política      policy.change con valor ANTERIOR y nuevo (límites de un cliente de corretaje, límites de gasto de IA;
                el agente de trading ya lo hacía desde el paso 16)
  investigación research.job (al crear el pedido; otra al cerrarlo: done/partial → executed, failed, deferred → noop)
                · research.run (una por analista, en la MISMA transacción que sus claims: claims y evidencia E# con
                huella, modelo y versión del prompt) · claim.status (superseded / retracted / falsified, con la
                regla, la métrica y el valor) · decision_outcomes 'claim_eval' sobre el research.run que creó el claim
  propuestas    proposal.create (agente; la puerta G-PROP queda en ESTA ficha) · proposal.auto_apply (system:auto_apply,
                cita policy.auto_apply; la ontology.action queda como hija) · approval.grant / approval.deny humanos
  alertas       alert.rule (alta y baja, dueño solo como hash) · alert.fire (async, fuera del camino del usuario; una
                por alerta y ventana de FIRE_GAP_S para no inundar el libro con el mismo disparo en cada sondeo)

Reglas: append-only (solo INSERT; las correcciones son decisiones nuevas), sync = misma transacción que el efecto
(si la ficha no se escribe, el efecto se revierte), ningún texto personal en claro (el dueño de una alerta o de una
cartera va como hash con clave), sin IA. Las búsquedas en el libro van dentro de un SAVEPOINT: si el libro no
existe, la transacción del caller sigue sana.
"""
import logging
import math
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

log = logging.getLogger('khipu')

FIRE_GAP_S = 600          # alert.fire: como mucho una ficha por alerta cada 10 min (el sondeo es cada ~1 min;
                          # alert_fire_due lleva la última ficha escrita: un episodio largo deja una cada 10 min)
MAX_REFS = 200            # tope de referencias por decisión (claims, evidencia)


# ── utilidades ───────────────────────────────────────────────────────────────
def principal(task, declared=None):
    """QUIÉN: el principal del hilo (identity.use) o de la petición; sin contexto, `system:<task>`."""
    from core import identity
    p = None
    try:
        p = identity.current()
        if p is None:
            from flask import has_request_context
            if has_request_context():
                p = identity.principal_from_request(declared=declared)
    except Exception:  # noqa: BLE001
        p = None
    return p or identity.system(task, declared=declared)


def clean(v):
    """JSON seguro para el libro: NaN/inf → None, fechas → ISO, recursivo (la forma canónica rechaza NaN)."""
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [clean(x) for x in v]
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, uuid.UUID):
        return str(v)
    return v


def _sha(obj):
    from core.decisions import sha256_hex
    return sha256_hex(clean(obj))


def claim_hash(c):
    """Huella de un claim tal como se VIO (texto, confianza, método conf-v2, estado) — §2.6."""
    comp = getattr(c, 'confidence_components', None) or {}
    return _sha({'statement_es': getattr(c, 'statement_es', None), 'statement_en': getattr(c, 'statement_en', None),
                 'confidence': getattr(c, 'confidence', None),
                 'method': comp.get('method') if isinstance(comp, dict) else None,
                 'status': getattr(c, 'status', None)})


def evidence_hash(e):
    """Huella de una evidencia E#: su referencia (URL/fuente) y su fecha."""
    pub = getattr(e, 'published_at', None)
    return _sha({'ref': getattr(e, 'source_reference', None) or getattr(e, 'title', None),
                 'published_at': pub.isoformat() if isinstance(pub, datetime) else pub})


def cite_policy(ctx, aid):
    try:
        from core import governance
        ref, h = governance.policy_ref(aid)
        ctx.policy(ref, h)
    except Exception:  # noqa: BLE001
        pass


def find_decisions(session, ref_kind, ref_ids, kinds):
    """{ref_id: decision_id más reciente} de las decisiones `kinds` que tienen (ref_kind, ref_id) como EFECTO.
    Dentro de un SAVEPOINT: sin libro (tablas ausentes) devuelve {} y la transacción del caller sigue sana."""
    ids = [str(x) for x in (ref_ids or ()) if x is not None]
    if not ids or session is None:
        return {}
    from sqlalchemy import text
    try:
        with session.begin_nested():
            rows = session.execute(text(
                "SELECT DISTINCT ON (r.ref_id) r.ref_id, d.id FROM decision_refs r JOIN decisions d "
                "ON d.id = r.decision_id WHERE r.role = 'effect' AND r.ref_kind = :k AND r.ref_id = ANY(:ids) "
                "AND d.kind = ANY(:kinds) ORDER BY r.ref_id, d.seq DESC"),
                {'k': ref_kind, 'ids': ids, 'kinds': list(kinds)}).all()
        return {r[0]: r[1] for r in rows}
    except Exception as e:  # noqa: BLE001
        log.debug('decision_sites: búsqueda en el libro falló (%s)', type(e).__name__)
        return {}


def find_decision(session, ref_kind, ref_id, kinds):
    return find_decisions(session, ref_kind, [ref_id], kinds).get(str(ref_id))


def after_response(fn, what):
    """Corre `fn()` FUERA del camino del usuario (la cola del libro de core/decisions si existe; si no, un hilo).
    Nunca lanza; sin base no hace nada."""
    try:
        from ontology.db import ontology_available
        if not ontology_available():
            return False
    except Exception:  # noqa: BLE001
        return False

    def run():
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            log.warning('decision_sites: %s no registrada (%s)', what, type(e).__name__)
        return None
    try:
        from core import decisions
        sub = getattr(decisions, 'submit_async', None)
        if sub is not None:
            return bool(sub(run))
    except Exception:  # noqa: BLE001
        pass
    threading.Thread(target=run, name=f'ledger-{what}', daemon=True).start()
    return True


def flush():
    """Pruebas: espera lo encolado por after_response."""
    try:
        from core import decisions
        if hasattr(decisions, 'flush_async'):
            decisions.flush_async()
    except Exception:  # noqa: BLE001
        pass


# ── política ─────────────────────────────────────────────────────────────────
def _changed_keys(before, after):
    b, a = before or {}, after or {}
    if not isinstance(b, dict) or not isinstance(a, dict):
        return [] if b == a else ['*']
    return sorted(k for k in set(b) | set(a) if clean(b.get(k)) != clean(a.get(k)))


def policy_change(session, policy, before, after, *, subject=None, task='policy', declared=None, p=None):
    """policy.change (sync, misma sesión) con el valor ANTERIOR y el nuevo. Sin cambio real → no escribe nada."""
    changed = _changed_keys(before, after)
    if before is not None and not changed:
        return None
    from core import decisions
    who = p or principal(task, declared)
    with decisions.decision_scope('policy.change', who, session=session,
                                  subject=clean(dict(subject or {}, policy=policy))) as ctx:
        ctx.payload_blob(clean({'policy': policy, 'before': before, 'after': after}))
        ctx.output = clean({'policy': policy, 'before': before, 'after': after, 'changed': changed})
        ctx.status = 'executed'
    return ctx.id


# ── comité (paso 18) ─────────────────────────────────────────────────────────
def memo_facts(memo, now=None):
    """Hechos del memo para la puerta G5 (core/gates/focus.memo_triples). Los topes salen del release vigente."""
    sz = memo.sizing or {}
    body = memo.memo or {}
    inp = memo.inputs or {}
    tv = body.get('track_validation') or inp.get('track_validation') or {}
    q = body.get('quorum') or inp.get('quorum') or {}
    validated = tv.get('validated') if isinstance(tv, dict) and 'validated' in tv else None
    try:
        from core import governance
        factor = float(governance.param('policy.committee', 'unvalidated_factor'))
        ttl = float(governance.param('policy.committee', 'memo_ttl_hours'))
    except Exception:  # noqa: BLE001
        factor, ttl = 0.5, 72.0
    try:
        from research.committee import _ttl_hours
        ttl = float(_ttl_hours())          # COMMITTEE_MEMO_TTL_HOURS manda igual que en approve_memo
    except Exception:  # noqa: BLE001
        pass
    raw, mx = sz.get('raw_weight_pct'), sz.get('max_position_pct')
    max_unv = None
    if validated is False and isinstance(raw, (int, float)) and isinstance(mx, (int, float)):
        max_unv = round(min(float(raw), float(mx)) * factor, 4) + 0.001     # holgura de redondeo (3 decimales)
    age = None
    if memo.created_at is not None:
        ca = memo.created_at if memo.created_at.tzinfo else memo.created_at.replace(tzinfo=timezone.utc)
        age = round(max(0.0, ((now or datetime.now(timezone.utc)) - ca).total_seconds() / 3600.0), 3)
    return {'id': memo.id, 'decision': memo.decision, 'quant_decision': memo.quant_decision,
            'decision_code': body.get('decision_code'), 'validated': validated,
            'sizing_unvalidated': sz.get('unvalidated') if 'unvalidated' in sz else None,
            'target_weight_pct': sz.get('target_weight_pct'), 'max_position_pct': mx,
            'max_unvalidated_weight_pct': max_unv, 'age_hours': age, 'ttl_hours': ttl,
            'quorum_ok': q.get('ok') if isinstance(q, dict) else None, 'n_claims': inp.get('n_claims'),
            'ai_used': bool(memo.ai_used)}


def gate_memo(memo, session=None, now=None):
    """Puerta G5 (SOMBRA): el reporte queda en la decisión en curso (committee.run o approval.*). Nunca lanza."""
    try:
        import core.gates as _gates
        from core.gates import focus as _gf
        return _gates.check('committee.g5', _gf.gather_memo, memo_facts(memo, now), session=session)
    except Exception:  # noqa: BLE001
        return None


def committee_run(session, memo, claims, *, package=None, rels=0, decision_id=None):
    """committee.run (sync) al guardar el memo 'proposed', en la MISMA transacción: si la ficha no se escribe, el
    memo tampoco (el hilo lo marca fallido)."""
    from core import decisions
    body = memo.memo or {}
    inp = memo.inputs or {}
    who = principal('committee', memo.requested_by)
    claims = list(claims or ())
    subject = {'entity_ids': [memo.entity_id], 'memo_id': memo.id, 'symbol': memo.symbol,
               'claim_ids': [c.id for c in claims[:MAX_REFS]]}
    if memo.client_id:
        subject['client_id'] = memo.client_id
    with decisions.decision_scope('committee.run', who, session=session, subject=clean(subject),
                                  correlation_id=f'memo:{memo.id}', decision_id=decision_id) as ctx:
        for c in claims[:MAX_REFS]:
            ctx.evidence('claim', c.id, ref_hash=claim_hash(c), agent=c.agent_type, horizon=c.horizon,
                         stance=c.stance)
        cite_policy(ctx, 'policy.committee')
        live = inp.get('live') or {}
        if memo.symbol and live.get('ok') and live.get('price') is not None:
            ctx.quote({'ticker': memo.symbol, 'px': live.get('price'), 'currency': live.get('currency'),
                       'src': live.get('source'), 'as_of': live.get('as_of')})
        ctx.payload_blob(clean({'package': package if package is not None else inp.get('package'),
                                'valid_refs': inp.get('valid_refs'), 'thresholds': inp.get('thresholds'),
                                'mandate': inp.get('mandate'), 'risk': inp.get('risk'), 'live': live,
                                'track_record': inp.get('track_record'), 'n_contradictions': rels,
                                'dominant_horizon': inp.get('dominant_horizon'), 'conviction': memo.conviction}))
        if body.get('transcript'):
            ctx.extra['transcript_blob'] = ctx.blob('transcript', clean(body.get('transcript')))
        ctx.extra['impl'] = {'committee': memo.method or 'committee-v1', 'sizing': 'compute_sizing@1',
                             'conviction': 'conviction_by_horizon@1'}
        if memo.ai_used:
            try:
                from research.committee import PROMPT_VERSION
            except Exception:  # noqa: BLE001
                PROMPT_VERSION = None
            ctx.model = {'provider': memo.provider, 'model': memo.model, 'prompt_version': PROMPT_VERSION}
        gate_memo(memo, session=session)
        ctx.effect('memo', memo.id)
        sz = memo.sizing or {}
        tv = body.get('track_validation') or {}
        ctx.output = clean({
            'memo_id': memo.id, 'decision': memo.decision, 'quant_decision': memo.quant_decision,
            'decision_code': body.get('decision_code'), 'overall_conviction': memo.overall_conviction,
            'validated': tv.get('validated'), 'validation_status': tv.get('status'),
            'quorum_ok': (body.get('quorum') or {}).get('ok'), 'ai_used': bool(memo.ai_used),
            'sizing': {k: sz.get(k) for k in ('target_weight_pct', 'raw_weight_pct', 'cap_pct', 'notional', 'qty',
                                              'side', 'unvalidated', 'unvalidated_factor', 'capped_by')},
            'memo_sha': _sha(body), 'n_claims': len(claims)})
        ctx.status = 'proposed'          # espera la aprobación humana (approval.grant | approval.deny)
    return ctx.id


def reserve_id():
    """decision_id reservado ANTES del trabajo de IA (comité, analistas): las filas de ai_calls de ese trabajo lo
    llevan (core/ai_calls.attribute, durabilidad sync → retención 'legal', D3) y la decisión se abre después con
    ese mismo id (decision_scope(decision_id=…))."""
    return uuid.uuid4()


@contextmanager
def ai_attributed(decision_id):
    """Atribuye las llamadas de IA del bloque (y de los hilos que lo hereden con core/ai_usage.bind) a la decisión
    reservada. Devuelve la lista de ids de ai_calls (vacía si no hubo IA). Nunca lanza por sí solo."""
    ids = []
    try:
        from core import ai_calls
        cm = ai_calls.attribute(decision_id, ids, durability='sync')
    except Exception:  # noqa: BLE001
        cm = None
    if cm is None:
        yield ids
        return
    with cm:
        yield ids


def record_reserved_failure(kind, decision_id, who, *, subject=None, error=None):
    """El trabajo con IA atribuida a `decision_id` falló ANTES de abrir su decisión: se escribe esa decisión como
    'failed' (sesión autónoma) para que las filas de ai_calls no apunten a una ficha que nunca existe."""
    try:
        from core import decisions
        ctx = decisions.DecisionCtx(kind, who, subject=clean(subject or {}), decision_id=decision_id)
        return decisions.record_rejection(ctx, status='failed', error=error)
    except Exception:  # noqa: BLE001
        return None


class _Approval:
    def __init__(self, ctx, verdict):
        self.ctx, self.verdict = ctx, verdict

    def gate(self, memo, session=None):
        return gate_memo(memo, session=session)

    def finish(self, out, memo=None):
        out = out or {}
        ok = bool(out.get('ok'))
        if ok:
            self.ctx.status = 'approved' if self.verdict == 'grant' else 'rejected'
        else:
            self.ctx.status = 'rejected' if out.get('code') in ('not_found', 'bad_status', 'expired') else 'failed'
        pv = out.get('preview') or {}
        m = out.get('memo') or {}
        self.ctx.output = clean({'verdict': self.verdict, 'ok': ok, 'code': out.get('code'),
                                 'memo_status': m.get('status'), 'preview_id': pv.get('preview_id') or pv.get('id'),
                                 'preview_status': pv.get('status'), 'executed': bool(out.get('executed')),
                                 'withdrawn': bool((out.get('withdrawn') or {}).get('ok')) if out.get('withdrawn')
                                 else None})


@contextmanager
def approval(session, verdict, *, target_kind, target_ref, parent_id=None, note=None, actor=None, task='approval',
             subject=None):
    """approval.grant | approval.deny que ENVUELVE el efecto (la previsualización del memo, la Acción de la propuesta):
    lo que se escriba dentro queda como hija. Una excepción dentro → ficha 'rejected'/'failed' (sesión autónoma) y
    se relanza. El texto del operador (nota/motivo) va a un blob legal (auditable por diseño, §2.7)."""
    from core import decisions
    kind = 'approval.grant' if verdict == 'grant' else 'approval.deny'
    who = principal(task, actor)
    rk, rid = target_ref
    sub = dict(subject or {}, target_kind=target_kind, **{f'{rk}_id': str(rid)})
    if parent_id:
        sub['target_id'] = str(parent_id)
    with decisions.decision_scope(kind, who, session=session, parent_id=parent_id, subject=clean(sub)) as ctx:
        if parent_id:
            ctx.cause('decision', str(parent_id))
        ctx.effect(rk, str(rid))
        if note:
            ctx.extra['note_blob'] = ctx.blob('payload', {'note': clean(note) if isinstance(note, (dict, list))
                                                          else str(note)[:2000]})
        ap = _Approval(ctx, verdict)
        yield ap
        if ctx.status is None:
            ctx.status = 'approved' if verdict == 'grant' else 'rejected'
            ctx.output = ctx.output or {'verdict': verdict}


@contextmanager
def memo_approval(session, memo_id, verdict, actor=None, note=None):
    run_id = find_decision(session, 'memo', str(memo_id or '')[:40], ('committee.run',))
    with approval(session, verdict, target_kind='committee.run', target_ref=('memo', str(memo_id or '')[:40]),
                  parent_id=run_id, note=note, actor=actor, task='committee_approval') as ap:
        yield ap


def portfolio_advice(analysis, *, positions=None, profile=None, owner_hash=None, lang='es', saved_id=None,
                     actor=None):
    """committee.portfolio_advice DESPUÉS de responder (consejo, no escribe nada del dominio): la ficha se arma en la
    cola del libro. Retención legal (comité = para siempre, D3). Posiciones en un blob; el dueño solo como hash."""
    if not isinstance(analysis, dict) or not analysis.get('ok'):
        return False
    who = principal('portfolio_committee', actor)
    if owner_hash and not who.on_behalf_of:
        from dataclasses import replace
        who = replace(who, on_behalf_of=f'owner:{str(owner_hash)[:40]}')
    snap = clean({'positions': [p for p in (positions or []) if isinstance(p, dict)][:60], 'profile': profile or {},
                  'kpis': analysis.get('kpis'), 'sectors': analysis.get('sectors'), 'as_of': analysis.get('as_of'),
                  'source': analysis.get('source')})
    acts = [clean({k: a.get(k) for k in ('type', 'action', 'symbol', 'entity_id', 'delta_usd', 'priority')})
            for a in (analysis.get('actions') or []) if isinstance(a, dict)][:8]
    out = clean({'health': analysis.get('health'), 'actions': acts, 'lang': lang,
                 'n_positions': (analysis.get('kpis') or {}).get('n_positions'), 'saved_id': saved_id,
                 'coverage': analysis.get('coverage')})
    ents = [r.get('entity_id') for r in (analysis.get('positions') or []) if isinstance(r, dict) and r.get('entity_id')]

    def write():
        from core import decisions
        from ontology.db import session_scope
        with session_scope() as s:
            with decisions.decision_scope('committee.portfolio_advice', who, session=s,
                                          subject=clean({'entity_ids': ents[:60]})) as ctx:
                ctx.payload_blob(snap)
                if saved_id:
                    ctx.effect('report', str(saved_id))
                ctx.extra['impl'] = {'advisor': 'portfolio_advisor.analyze@1'}
                ctx.output = out
                ctx.status = 'recorded'
    return after_response(write, 'committee.portfolio_advice')


# ── investigación (paso 19) ──────────────────────────────────────────────────
_TRIGGER_TASK = {'event': 'research_router', 'board': 'research_board', 'committee': 'committee',
                 'anomaly': 'research_anomaly', 'earnings': 'research_earnings'}
_JOB_STATUS = {'done': 'executed', 'partial': 'executed', 'failed': 'failed', 'deferred': 'noop'}
_RUN_STATUS = {'done': 'executed', 'failed': 'failed', 'skipped': 'noop'}


def research_job(session, job):
    """research.job (sync) al CREAR un pedido nuevo (los reutilizados no escriben nada): quién, disparador, analistas."""
    from core import decisions
    trig = job.trigger or {}
    who = principal(_TRIGGER_TASK.get(trig.get('kind'), 'research'), job.requested_by)
    with decisions.decision_scope('research.job', who, session=session,
                                  subject={'entity_ids': [job.entity_id], 'job_id': str(job.id)},
                                  correlation_id=f'job:{job.id}') as ctx:
        ctx.effect('job', str(job.id))
        if trig.get('completes'):
            ctx.cause('job', str(trig['completes']))
        ctx.output = clean({'job_id': job.id, 'entity_id': job.entity_id, 'depth': job.depth,
                            'agents': list(job.agents or []),
                            'trigger': {k: trig.get(k) for k in ('kind', 'event_key', 'completes') if trig.get(k)}})
        ctx.status = 'recorded'
    return ctx.id


def research_job_closed(session, job, coverage=None):
    """Cierre del pedido (sync): hija del research.job de creación. done/partial → executed, failed, deferred → noop."""
    from core import decisions
    st = _JOB_STATUS.get(job.status)
    if st is None:
        return None
    parent = find_decision(session, 'job', str(job.id), ('research.job',))
    who = principal('research_runner', job.requested_by)
    trig = job.trigger or {}
    with decisions.decision_scope('research.job', who, session=session, parent_id=parent,
                                  subject={'entity_ids': [job.entity_id], 'job_id': str(job.id)},
                                  correlation_id=f'job:{job.id}') as ctx:
        ctx.cause('job', str(job.id))
        ctx.output = clean({'job_id': job.id, 'job_status': job.status, 'error': (job.error or '')[:300] or None,
                            'coverage': coverage if coverage is not None else (job.synthesis or {}).get('coverage'),
                            'resume_after': trig.get('resume_after')})
        ctx.status = st
    return ctx.id


def _run_principal(agent_type, version):
    from core import identity
    try:
        return identity.agent(agent_type, version or '1')
    except Exception:  # noqa: BLE001 — un analista fuera del registro único queda como tarea del sistema
        return identity.system('research_runner', declared=agent_type)


@contextmanager
def research_run(session, job, run, agent, decision_id=None):
    """research.run (sync) de UN analista, en la MISMA transacción que sus claims y su evidencia. Lo que pase
    dentro (claim.status por claims superados) queda como hija. Al salir: estado del AgentRun, claims creados
    (efecto) y evidencia E# citada (con huella), modelo y versión del prompt."""
    from core import decisions
    parent = find_decision(session, 'job', str(job.id), ('research.job',))
    who = _run_principal(getattr(agent, 'agent_type', None) or run.agent_type, getattr(agent, 'version', None))
    with decisions.decision_scope('research.run', who, session=session, parent_id=parent,
                                  subject={'entity_ids': [job.entity_id], 'job_id': str(job.id), 'run_id': str(run.id),
                                           'agent_type': run.agent_type},
                                  correlation_id=f'job:{job.id}', decision_id=decision_id) as ctx:
        ctx.ref('input', 'job', str(job.id))
        yield ctx
        _close_run(session, ctx, job, run, agent)


def _close_run(session, ctx, job, run, agent):
    from research.models import ResearchClaim, ResearchEvidence
    claims = session.query(ResearchClaim).filter(ResearchClaim.run_id == run.id).all() if run.id else []
    for c in claims[:MAX_REFS]:
        ctx.effect('claim', c.id, agent=c.agent_type, horizon=c.horizon, stance=c.stance, h=claim_hash(c)[:16])
    if claims:
        evs = (session.query(ResearchEvidence).filter(ResearchEvidence.claim_id.in_([c.id for c in claims]))
               .limit(MAX_REFS).all())
        for e in evs:
            pub = e.published_at
            ctx.evidence('evidence', e.id, ref_hash=evidence_hash(e), as_of=pub, ref=e.context_ref,
                         stance=e.stance, source_type=e.source_type)
    ctx.model = clean({'provider': run.provider, 'model': run.model, 'agent': run.agent_id,
                       'agent_version': getattr(agent, 'version', None),
                       'prompt_version': getattr(agent, 'prompt_version', None),
                       'tokens_in': run.tokens_in, 'tokens_out': run.tokens_out, 'est_cost_usd': run.est_cost_usd})
    ctx.output = clean({'run_id': run.id, 'run_status': run.status, 'claims': len(claims),
                        'claim_ids': [c.id for c in claims[:MAX_REFS]],
                        'errors': [str(x)[:200] for x in (run.errors or [])][:3] or None,
                        'latency_ms': run.latency_ms})
    ctx.status = _RUN_STATUS.get(run.status, 'failed')


def claim_status(session, claim_ids, to_status, *, from_status='active', reason=None, notes=None, parent_id=None,
                 task='research'):
    """claim.status (sync): la transición de estado de uno o varios claims (superseded, retracted, falsified), con
    la regla/métrica/valor de cada uno en la nota del efecto. Dentro de un research.run abierto queda como hija."""
    ids = [str(x) for x in (claim_ids or ()) if x]
    if not ids:
        return None
    from core import decisions
    cur = decisions.current()
    who = cur.principal if cur is not None else principal(task)
    notes = notes or {}
    with decisions.decision_scope('claim.status', who, session=session, parent_id=parent_id,
                                  subject={'claim_ids': ids[:MAX_REFS], 'to': to_status}) as ctx:
        for cid in ids[:MAX_REFS]:
            ctx.effect('claim', cid, to=to_status, **clean(notes.get(cid) or {}))
        ctx.output = clean({'from': from_status, 'to': to_status, 'n': len(ids), 'reason': reason})
        ctx.status = 'executed'
    return ctx.id


def claim_evals(session, rows, source='outcomes:outcome-v1'):
    """decision_outcomes 'claim_eval' sobre el research.run que CREÓ cada claim (dedup claim:checkpoint). Es un
    resultado POSTERIOR (no un efecto): si el libro falla, la calificación sigue (SAVEPOINT + aviso)."""
    rows = [r for r in (rows or ()) if r is not None]
    if not rows:
        return 0
    from core import decisions
    owners = find_decisions(session, 'claim', [r.claim_id for r in rows], ('research.run',))
    n = 0
    for r in rows:
        did = owners.get(str(r.claim_id))
        if did is None:
            continue
        try:
            with session.begin_nested():
                decisions.outcome(session, did, 'claim_eval', clean({
                    'claim_id': r.claim_id, 'checkpoint': r.checkpoint, 'result': r.result, 'final': r.final,
                    'excess_return': r.excess_return, 'eval_date': r.eval_date, 'symbol': r.symbol,
                    'claim_status': r.claim_status, 'dedup_key': f'{r.claim_id}:{r.checkpoint}'}),
                    observed_at=_as_dt(r.eval_date) or datetime.now(timezone.utc), source=source)
            n += 1
        except Exception as e:  # noqa: BLE001
            log.warning('decision_sites: claim_eval no registrado (%s)', type(e).__name__)
    return n


def _as_dt(d):
    if not d:
        return None
    try:
        v = datetime.fromisoformat(str(d)[:10] + 'T21:00:00+00:00')      # cierre NYSE ≈ 21:00 UTC
        return v
    except ValueError:
        return None


# ── propuestas (paso 19) ─────────────────────────────────────────────────────
def agent_principal(agent_name):
    """Los agentes de la ontología trabajan para el Radar (registro único): agent:radar@1 + su nombre de etiqueta."""
    from core import identity
    try:
        return identity.agent('radar', '1', declared=agent_name)
    except Exception:  # noqa: BLE001
        return identity.system('ontology_agents', declared=agent_name)


@contextmanager
def proposal_create(session, agent_name, proposal):
    """proposal.create (sync): envuelve la creación de la propuesta (la puerta G-PROP queda en ESTA ficha). El caller
    llama `done(pa)` tras añadir y volcar la fila."""
    from core import decisions
    oid = proposal.get('object_id')
    with decisions.decision_scope('proposal.create', agent_principal(agent_name), session=session,
                                  subject=clean({'entity_ids': [oid] if oid else [],
                                                 'action_type': proposal.get('action_type')})) as ctx:
        ctx.payload_blob(clean({'action_type': proposal.get('action_type'), 'payload': proposal.get('payload'),
                                'explanation': proposal.get('explanation'), 'agent': agent_name}))

        def done(pa):
            ctx.effect('proposal', str(pa.id))
            ctx.subject = dict(ctx.subject, proposal_id=str(pa.id))
            ctx.output = clean({'proposal_id': pa.id, 'action_type': pa.action_type, 'object_id': pa.object_id,
                                'confidence': pa.confidence, 'agent': agent_name,
                                'gate_outcome': (pa.gate_report or {}).get('outcome')})
            ctx.status = 'proposed'
        yield done
        if ctx.status is None:
            ctx.status = 'noop'


@contextmanager
def proposal_auto_apply(session, p, min_conf=None):
    """proposal.auto_apply (sync, system:auto_apply): cita policy.auto_apply (D6 sin respuesta: 1.0.0, el
    comportamiento de hoy). La ontology.action que ejecuta queda como hija."""
    from core import decisions, identity
    parent = find_decision(session, 'proposal', str(p.id), ('proposal.create',))
    with decisions.decision_scope('proposal.auto_apply', identity.system('auto_apply', declared=p.agent),
                                  session=session, parent_id=parent,
                                  subject=clean({'proposal_id': p.id, 'action_type': p.action_type,
                                                 'entity_ids': [p.object_id] if p.object_id else []}),
                                  correlation_id=f'proposal:{p.id}') as ctx:
        cite_policy(ctx, 'policy.auto_apply')
        ctx.effect('proposal', str(p.id))
        if parent:
            ctx.cause('decision', str(parent))
        yield ctx
        ctx.output = clean({'proposal_id': p.id, 'action_type': p.action_type, 'confidence': p.confidence,
                            'auto_min_confidence': min_conf})
        ctx.status = 'executed'


def proposal_parent(session, pid):
    return find_decision(session, 'proposal', str(pid), ('proposal.create',))


# ── alertas (paso 19) ────────────────────────────────────────────────────────
def owner_hash(owner):
    from core import identity
    return identity.hash_id(owner) if owner else None


def alert_rule(session, alert, op, actor=None):
    """alert.rule (sync): alta o baja de una regla. El dueño (texto libre) SOLO como hash con clave."""
    from core import decisions
    who = principal('alerts', actor)
    oh = owner_hash(alert.owner)
    rule = alert.rule if isinstance(alert.rule, dict) else {}
    ent = rule.get('entity')
    with decisions.decision_scope('alert.rule', who, session=session,
                                  subject=clean({'alert_id': alert.id, 'owner_hash': oh, 'op': op,
                                                 'entity_ids': [ent] if ent else []})) as ctx:
        ctx.effect('alert', str(alert.id))
        ctx.output = clean({'op': op, 'alert_id': alert.id, 'rule': rule, 'channel': alert.channel,
                            'is_active': alert.is_active})
        ctx.status = 'executed'
    return ctx.id


_LEDGERED = {}                # alert_id → última vez que se escribió su alert.fire (memoria; un solo worker)
_LEDGERED_LOCK = threading.Lock()


def alert_fire_due(alert_id, prev_fired_at, now):
    """¿Toca escribir alert.fire para esta alerta que disparó AHORA? Límite de RITMO (revisión paso 19): como
    mucho una ficha cada FIRE_GAP_S mientras la condición siga verdadera — antes se comparaba con last_fired_at,
    que se pisa en CADA sondeo (~1 min) y nunca llegaba a 10 min: solo quedaba el primer disparo del episodio.
    Sin memoria (reinicio): un episodio nuevo (sin disparo previo o con ≥ FIRE_GAP_S de pausa) se escribe ya; uno
    que seguía en curso se escribe a los FIRE_GAP_S."""
    key = str(alert_id)
    with _LEDGERED_LOCK:
        last = _LEDGERED.get(key)
        if last is None:
            due = prev_fired_at is None or (now - prev_fired_at).total_seconds() >= FIRE_GAP_S
            if not due:
                _LEDGERED[key] = now          # episodio en curso tras un reinicio: la próxima ficha en FIRE_GAP_S
                return False
        else:
            due = (now - last).total_seconds() >= FIRE_GAP_S
        if due:
            if len(_LEDGERED) > 20000:
                _LEDGERED.clear()
            _LEDGERED[key] = now
        return due


def alert_fires(items):
    """alert.fire (async, fuera del camino del usuario): una ficha por alerta disparada (system:alerts) con valor,
    umbral y detalle. `items`: [{alert_id, owner, rule, value, detail}] (ya filtrados por FIRE_GAP_S)."""
    items = [i for i in (items or ()) if i]
    if not items:
        return False
    snap = [clean({'alert_id': i.get('alert_id'), 'owner_hash': owner_hash(i.get('owner')), 'rule': i.get('rule'),
                   'value': i.get('value'), 'detail': str(i.get('detail') or '')[:200]}) for i in items]

    def write():
        from core import decisions, identity
        for it in snap:
            rule = it.get('rule') or {}
            ent = rule.get('entity') if isinstance(rule, dict) else None
            ctx = decisions.DecisionCtx('alert.fire', identity.system('alerts'), durability='async',
                                        subject={'alert_id': it['alert_id'], 'owner_hash': it['owner_hash'],
                                                 'entity_ids': [ent] if ent else []})
            ctx.cause('alert', str(it['alert_id']))
            ctx.output = {'metric': rule.get('metric') if isinstance(rule, dict) else None,
                          'op': rule.get('op') if isinstance(rule, dict) else None,
                          'threshold': rule.get('value') if isinstance(rule, dict) else None,
                          'value': it.get('value'), 'detail': it.get('detail')}
            decisions.record(None, ctx, status='fired')
    return after_response(write, 'alert.fire')

