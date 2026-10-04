"""research/api.py — blueprint /api/research/* (Phase 2).

POST /jobs                 {entity, depth?, agents?, actor}   → crea (o reutiliza) y ejecuta en hilo
GET  /jobs/<id>            estado real + ejecuciones + claims del job
GET  /entity/<id>          claims ACTIVAS por perspectiva + contradicciones + última síntesis
GET  /claims/<id>          "¿POR QUÉ?": claim, evidencia a favor/en contra, fuentes, nodos, ejecución
GET  /activity             feed de ejecuciones REALES de agentes (agent_runs)
GET  /agents               registro: qué existe, qué lee/escribe, modelos, eventos
POST /events               evento → router → agentes relevantes (Phase 2 event-driven)
GET  /budget               gasto estimado del día vs tope
Sin DATABASE_URL → 503 (mismo patrón que la ontología).
"""
from flask import Blueprint, jsonify, request

from core.http import rate_limit
from ontology.db import ontology_available, session_scope

research_bp = Blueprint('research', __name__, url_prefix='/api/research')


def _unavailable():
    return jsonify({'error': 'investigación no disponible', 'available': False,
                    'detail': 'Falta DATABASE_URL (la investigación se guarda en la ontología).'}), 503


def _iso(d):
    return d.isoformat() if d else None


def _claim_dict(c, n_sup=None, n_cnt=None):
    return {'claim_id': c.id, 'agent_id': c.agent_id, 'agent_type': c.agent_type,
            'agent_version': c.agent_version, 'subject_entity_id': c.subject_entity_id,
            'predicate': c.predicate, 'object': c.object, 'claim_type': c.claim_type, 'topic': c.topic,
            'stance': c.stance, 'statement_es': c.statement_es, 'statement_en': c.statement_en,
            'horizon': c.horizon, 'depth': c.depth, 'confidence': c.confidence,
            'confidence_components': c.confidence_components, 'affected_entity_ids': c.affected_entity_ids,
            'falsifiers': c.falsifiers, 'status': c.status, 'model': c.model,
            'prompt_version': c.prompt_version, 'created_at': _iso(c.created_at),
            'valid_from': _iso(c.valid_from), 'valid_to': _iso(c.valid_to),
            'n_supporting': n_sup, 'n_counter': n_cnt, 'job_id': c.job_id, 'run_id': c.run_id}


def _run_dict(r):
    from research.errors import run_hint
    hint = run_hint(r.errors) if r.status in ('failed', 'skipped') else (None, None)
    return {'hint_es': hint[0], 'hint_en': hint[1],'run_id': r.id, 'job_id': r.job_id, 'agent_id': r.agent_id, 'agent_type': r.agent_type,
            'entity_id': r.entity_id, 'trigger': r.trigger, 'depth': r.depth, 'status': r.status,
            'model': r.model, 'provider': r.provider, 'tokens_in': r.tokens_in, 'tokens_out': r.tokens_out,
            'est_cost_usd': r.est_cost_usd, 'claims_generated': r.claims_generated,
            'tools_used': r.tools_used, 'context_refs': r.context_refs, 'validation': r.validation,
            'errors': r.errors, 'summary': r.summary, 'started_at': _iso(r.started_at),
            'completed_at': _iso(r.completed_at), 'latency_ms': r.latency_ms}


def _resolve(entity):
    from core.entities import UMBRAL_BUSQUEDA, resolve
    r = resolve(entity, umbral=UMBRAL_BUSQUEDA)
    return r['id'] if r else None


@research_bp.route('/agents')
def agents():
    from research.agents import AGENTS
    return jsonify({'agents': [a.describe() for a in AGENTS]})


@research_bp.route('/jobs', methods=['POST'])
@rate_limit(limit=12, window=3600)
def create():
    if not ontology_available():
        return _unavailable()
    from core.ai import _ai_configured
    body = request.get_json(silent=True) or {}
    actor = str(body.get('actor') or '').strip()[:120]
    if not actor:
        return jsonify({'error': 'actor obligatorio'}), 400
    eid = _resolve(str(body.get('entity') or '')[:120])
    if not eid:
        return jsonify({'error': 'entidad no encontrada'}), 404
    if not _ai_configured():
        return jsonify({'error': 'ningún proveedor de IA configurado'}), 503
    from research.runner import create_job, execute_job_async
    agents_req = body.get('agents') if isinstance(body.get('agents'), list) else None

    def _crear():
        from research.runner import budget_exhausted, defer_job
        with session_scope() as s:
            job, reused = create_job(s, eid, depth=str(body.get('depth') or 'STANDARD').upper(),
                                     agents=agents_req, trigger={'kind': 'user', 'by': actor},
                                     requested_by=actor, force=bool(body.get('force')),
                                     only_missing=bool(body.get('only_missing')))
            if not reused and job.status == 'queued' and budget_exhausted(s):
                defer_job(s, job)          # R5: se reanuda solo mañana (no se pierde el pedido)
            return job.id, reused, {'job_id': job.id, 'entity_id': eid, 'status': job.status,
                                    'reused': reused, 'agents': job.agents, 'depth': job.depth,
                                    'resume_after': (job.trigger or {}).get('resume_after'),
                                    'error': job.error}
    try:
        try:
            jid, reused, out = _crear()
        except Exception as e:  # noqa: BLE001
            # AUTO-REPARACIÓN: si la base arrancó después que la app, las tablas
            # research_* pueden no existir aún → se crean y se reintenta una vez.
            if 'does not exist' not in str(e) and 'UndefinedTable' not in type(e).__name__ + str(e):
                raise
            from ontology.db import init_schema
            init_schema(retries=1)
            jid, reused, out = _crear()
    except Exception as e:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning('research create: %s', e)
        return jsonify({'error': 'no se pudo crear la investigación',
                        'detail': f'{type(e).__name__}: {str(e)[:240]}'}), 500
    if not reused and out['status'] == 'queued':
        execute_job_async(jid)
    return jsonify(out), (200 if reused else 202)


@research_bp.route('/jobs/<job_id>')
def job(job_id):
    if not ontology_available():
        return _unavailable()
    from research.models import AgentRun, ResearchClaim, ResearchJob
    with session_scope() as s:
        j = s.get(ResearchJob, job_id[:40])
        if not j:
            return jsonify({'error': 'job no encontrado'}), 404
        runs = s.query(AgentRun).filter(AgentRun.job_id == j.id).order_by(AgentRun.started_at).all()
        claims = s.query(ResearchClaim).filter(ResearchClaim.job_id == j.id).all()
        from research.runner import coverage_of, queue_position, research_queue_state
        qs = research_queue_state()
        return jsonify({'job_id': j.id, 'entity_id': j.entity_id, 'status': j.status, 'depth': j.depth,
                        'agents': j.agents, 'trigger': j.trigger, 'created_at': _iso(j.created_at),
                        'completed_at': _iso(j.completed_at), 'error': j.error, 'synthesis': j.synthesis,
                        'coverage': coverage_of(runs, j.agents or []),
                        'queue_position': queue_position(j.id) if j.status == 'queued' else None,
                        'queue_length': qs['jobs_queued'], 'jobs_running': qs['jobs_running'],
                        'runs': [_run_dict(r) for r in runs], 'claims': [_claim_dict(c) for c in claims]})


@research_bp.route('/entity/<entity_id>')
def entity(entity_id):
    if not ontology_available():
        return _unavailable()
    from sqlalchemy import func

    from research.models import ClaimRelation, ResearchClaim, ResearchEvidence, ResearchJob
    eid = _resolve(entity_id[:120]) or entity_id[:120]
    try:
        from research.runner import retract_unsupported
        with session_scope() as s:
            retract_unsupported(s, eid)
    except Exception:  # noqa: BLE001 — nunca impide mostrar la investigación
        pass
    with session_scope() as s:
        claims = (s.query(ResearchClaim).filter(ResearchClaim.subject_entity_id == eid,
                                                ResearchClaim.status == 'active')
                  .order_by(ResearchClaim.created_at.desc()).limit(60).all())
        ids = [c.id for c in claims]
        counts = {}
        if ids:
            for cid, st, n in (s.query(ResearchEvidence.claim_id, ResearchEvidence.stance, func.count())
                               .filter(ResearchEvidence.claim_id.in_(ids))
                               .group_by(ResearchEvidence.claim_id, ResearchEvidence.stance).all()):
                counts.setdefault(cid, {})[st] = n
        rels = (s.query(ClaimRelation).filter(ClaimRelation.claim_a.in_(ids) | ClaimRelation.claim_b.in_(ids)).all()
                if ids else [])
        last = (s.query(ResearchJob).filter(ResearchJob.entity_id == eid)
                .order_by(ResearchJob.created_at.desc()).first())
        by_agent = {}
        for c in claims:
            by_agent.setdefault(c.agent_type, []).append(
                _claim_dict(c, counts.get(c.id, {}).get('supporting', 0), counts.get(c.id, {}).get('counter', 0)))
        cmap = {c.id: c for c in claims}

        def _side(cid):
            c = cmap.get(cid)
            return {'agent_type': c.agent_type, 'stance': c.stance, 'topic': c.topic, 'horizon': c.horizon} if c else None
        return jsonify({'entity_id': eid, 'by_agent': by_agent,
                        'contradictions': [{'a': r.claim_a, 'b': r.claim_b, 'type': r.rel_type, 'reason': r.reason,
                                            'a_info': _side(r.claim_a), 'b_info': _side(r.claim_b)}
                                           for r in rels],
                        'last_job': ({'job_id': last.id, 'status': last.status, 'created_at': _iso(last.created_at),
                                      'completed_at': _iso(last.completed_at), 'synthesis': last.synthesis,
                                      'coverage': _coverage(s, last), 'error': last.error}
                                     if last else None)})


def _coverage(session, job):
    """Cobertura guardada (jobs terminados) o calculada en vivo (en curso)."""
    try:
        syn = job.synthesis if isinstance(job.synthesis, dict) else None
        if syn and syn.get('coverage'):
            return syn['coverage']
        from research.runner import job_coverage
        return job_coverage(session, job)
    except Exception:  # noqa: BLE001
        return None


@research_bp.route('/claims/<claim_id>')
def claim_why(claim_id):
    """¿POR QUÉ? claim → resumen de razonamiento → evidencia → fuentes →
    nodos afectados → contra-evidencia → ejecución que la produjo."""
    if not ontology_available():
        return _unavailable()
    from core.entities import get_index
    from ontology.models import ObjectRecord
    from ontology.provenance import source_to_dict
    from research.models import AgentRun, ClaimRelation, ResearchClaim, ResearchEvidence
    with session_scope() as s:
        c = s.get(ResearchClaim, claim_id[:40])
        if not c:
            return jsonify({'error': 'claim no encontrada'}), 404
        ev = s.query(ResearchEvidence).filter(ResearchEvidence.claim_id == c.id).all()
        srcs = {}
        sids = [e.source_id for e in ev if e.source_id]
        if sids:
            srcs = {o.id: source_to_dict(o) for o in s.query(ObjectRecord).filter(ObjectRecord.id.in_(sids)).all()}

        def edict(e):
            return {'evidence_id': e.id, 'ref': e.context_ref, 'source_type': e.source_type,
                    'source_reference': e.source_reference, 'title': e.title, 'excerpt': e.excerpt,
                    'published_at': _iso(e.published_at), 'retrieved_at': _iso(e.retrieved_at),
                    'reliability': e.reliability, 'source': srcs.get(e.source_id)}
        run = s.get(AgentRun, c.run_id) if c.run_id else None
        rels = s.query(ClaimRelation).filter((ClaimRelation.claim_a == c.id) | (ClaimRelation.claim_b == c.id)).all()
        other_ids = [r.claim_b if r.claim_a == c.id else r.claim_a for r in rels]
        others = {o.id: o for o in s.query(ResearchClaim).filter(ResearchClaim.id.in_(other_ids)).all()} if other_ids else {}
        nodes = get_index()['nodos']
        return jsonify({
            'claim': _claim_dict(c), 'reasoning_summary': c.reasoning_summary,
            'supporting': [edict(e) for e in ev if e.stance == 'supporting'],
            'counter': [edict(e) for e in ev if e.stance == 'counter'],
            'affected_nodes': [{'id': i, 'label': (nodes.get(i) or {}).get('label', i)}
                               for i in [c.subject_entity_id] + list(c.affected_entity_ids or [])],
            'contradicts': [{'claim_id': oid, 'reason': r.reason,
                             'agent_type': getattr(others.get(oid), 'agent_type', None),
                             'statement_es': getattr(others.get(oid), 'statement_es', None),
                             'statement_en': getattr(others.get(oid), 'statement_en', None)}
                            for r, oid in zip(rels, other_ids)],
            'run': _run_dict(run) if run else None})


@research_bp.route('/activity')
def activity():
    """Feed LIVE AGENT ACTIVITY: solo ejecuciones reales registradas."""
    if not ontology_available():
        return _unavailable()
    from research.models import AgentRun
    try:
        limit = min(max(int(request.args.get('limit', 25)), 1), 100)
    except (TypeError, ValueError):
        limit = 25
    ent = request.args.get('entity')
    with session_scope() as s:
        q = s.query(AgentRun)
        if ent:
            q = q.filter(AgentRun.entity_id == ent[:120])
        rows = q.order_by(AgentRun.started_at.desc()).limit(limit).all()
        return jsonify({'activity': [_run_dict(r) for r in rows]})


@research_bp.route('/budget')
def budget():
    if not ontology_available():
        return _unavailable()
    import os

    from research.runner import spent_today
    with session_scope() as s:
        return jsonify({'spent_today_usd_est': round(spent_today(s), 4),
                        'daily_budget_usd': float(os.getenv('RESEARCH_DAILY_BUDGET_USD', 2.0))})


@research_bp.route('/events', methods=['POST'])
@rate_limit(limit=30, window=3600)
def events():
    """Evento → relevancia (entidades afectadas vía grafo) → agentes suscritos."""
    if not ontology_available():
        return _unavailable()
    body = request.get_json(silent=True) or {}
    actor = str(body.get('actor') or '').strip()[:120]
    if not actor:
        return jsonify({'error': 'actor obligatorio'}), 400
    from research.router import dispatch_event
    with session_scope() as s:
        out = dispatch_event(s, body.get('event') or {}, actor=actor,
                             execute=bool(body.get('execute', True)))
    return jsonify(out)
