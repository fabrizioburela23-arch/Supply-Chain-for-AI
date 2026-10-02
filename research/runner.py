"""research/runner.py — ejecución de un ResearchJob (vertical slice → general).

identify entity → create job → select agents → build contexts → execute agents
→ validate → compute confidence → write claims/evidence (research_* SOLO) →
contradictions → synthesis. Todo observable en agent_runs.

Control de costo (docs/MODEL_ROUTING.md):
  RESEARCH_DAILY_BUDGET_USD   tope diario estimado (default 2.0)
  RESEARCH_MAX_AGENTS_PER_JOB agentes por trabajo (default 4)
  RESEARCH_DEDUPE_MINUTES     mismo pedido reciente → se reutiliza (default 30)
"""
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from research.agents import AGENTS_BY_TYPE
from research.confidence import compute_confidence
from research.context import AGENT_NEEDS, ContextBuilder
from research.contradictions import detect_for
from research.llm import LLMError, estimate_cost
from research.models import (DEPTHS, AgentRun, ClaimRelation, ResearchClaim, ResearchEvidence,
                             ResearchJob)

log = logging.getLogger('khipu')

DEFAULT_AGENTS = ('fundamental', 'news', 'technical', 'supply_chain')


def _now():
    return datetime.now(timezone.utc)


def _cfg(name, default, cast=float):
    try:
        return cast(os.getenv(name, default))
    except (TypeError, ValueError):
        return cast(default)


def spent_today(session):
    start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    v = session.query(func.coalesce(func.sum(AgentRun.est_cost_usd), 0.0)).filter(
        AgentRun.started_at >= start).scalar()
    return float(v or 0.0)


def _parse_dt(v):
    if not v:
        return None
    s = str(v)
    try:
        if len(s) == 16 and s[8] == 'T' and s.endswith('Z'):
            return datetime.strptime(s, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
        d = datetime.fromisoformat(s.replace('Z', '+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


_HZ_DAYS = {'INTRADAY': 2, 'SHORT_TERM': 90, 'MEDIUM_TERM': 365, 'LONG_TERM': 5 * 365, 'STRUCTURAL': None}


def create_job(session, entity_id, depth='STANDARD', agents=None, trigger=None, requested_by=None,
               force=False):
    """Crea (o REUTILIZA si hay uno igual reciente) un ResearchJob. No ejecuta."""
    depth = depth if depth in DEPTHS else 'STANDARD'
    max_agents = _cfg('RESEARCH_MAX_AGENTS_PER_JOB', 4, int)
    agents = [a for a in (agents or DEFAULT_AGENTS) if a in AGENTS_BY_TYPE][:max_agents]
    key = f'{entity_id}|{depth}|{",".join(sorted(agents))}'
    if not force:
        since = _now() - timedelta(minutes=_cfg('RESEARCH_DEDUPE_MINUTES', 30, int))
        prev = (session.query(ResearchJob).filter(ResearchJob.dedupe_key == key,
                                                  ResearchJob.created_at >= since,
                                                  ResearchJob.status.in_(('queued', 'running', 'done')))
                .order_by(ResearchJob.created_at.desc()).first())
        # Un job 'done' SIN ningún agente exitoso (p. ej. creado antes del fix
        # que lo marca 'failed') no se reutiliza: dejaría al usuario atascado.
        if prev and prev.status == 'done' and not (session.query(AgentRun)
                                                   .filter(AgentRun.job_id == prev.id,
                                                           AgentRun.status == 'done').first()):
            prev = None
        if prev:
            return prev, True
    job = ResearchJob(entity_id=entity_id, depth=depth, agents=agents, trigger=trigger or {'kind': 'user'},
                      requested_by=requested_by, status='queued', dedupe_key=key)
    session.add(job)
    session.flush()
    return job, False


def retract_unsupported(session, entity_id):
    """Retira (status='retracted') las claims ACTIVAS de la entidad cuyas cifras
    de dinero no aparecen en su propia evidencia guardada — p. ej. las escritas
    antes del guardián de cifras (Broadcom "~$350B", 2026-09-28). Devuelve n."""
    from core.numbers import evidence_numbers, unsupported_money
    claims = (session.query(ResearchClaim)
              .filter(ResearchClaim.subject_entity_id == entity_id, ResearchClaim.status == 'active').all())
    n = 0
    for c in claims:
        txt = ' '.join(filter(None, [c.statement_es, c.statement_en, c.reasoning_summary, c.object]))
        if not txt or not re.search(r'\d', txt):
            continue
        ev = session.query(ResearchEvidence).filter(ResearchEvidence.claim_id == c.id).all()
        vals = evidence_numbers([{'title': e.title, 'excerpt': e.excerpt} for e in ev])
        if unsupported_money(txt, vals):
            c.status = 'retracted'
            n += 1
    if n:
        session.flush()
    return n


def _completeness(ctx):
    need = set(AGENT_NEEDS.get(ctx['agent_type'], ()))
    got = {e['source_type'] for e in ctx['evidence']}
    want = {'financials': 'financials', 'profile': 'market', 'candles': 'market', 'news': 'news',
            'catalog': 'catalog', 'graph': 'graph'}
    targets = {want[n] for n in need if n in want}
    return (len(targets & got) / len(targets)) if targets else 1.0


def _prepare_run(session, job, agent_type):
    """Hilo principal: registra el AgentRun y revisa el presupuesto.
    Devuelve (run, prior_claims, listo?)."""
    agent = AGENTS_BY_TYPE[agent_type]
    run = AgentRun(job_id=job.id, agent_id=agent.agent_id, agent_type=agent_type,
                   entity_id=job.entity_id, trigger=job.trigger or {}, depth=job.depth,
                   status='running', started_at=_now())
    session.add(run)
    session.flush()
    budget = _cfg('RESEARCH_DAILY_BUDGET_USD', 2.0)
    if spent_today(session) >= budget:
        run.status = 'skipped'
        run.errors = [f'presupuesto diario agotado (≈${budget:.2f} estimados)']
        run.completed_at = _now()
        session.flush()
        return run, [], False
    prior = ContextBuilder(session=session)._prior_claims(job.entity_id, agent_type)
    return run, prior, True


def _agent_work(entity_id, trigger, depth, agent_type, provider, fetchers, prior):
    """SIN base de datos (corre en un hilo): arma el contexto y consulta a la IA.
    Devuelve dict {ctx, result, meta, error, skipped}."""
    agent = AGENTS_BY_TYPE[agent_type]
    t0 = time.time()
    out = {'ctx': None, 'result': None, 'meta': {}, 'error': None, 'skipped': None}
    try:
        ctx = ContextBuilder(fetchers=fetchers).build(entity_id, agent_type,
                                                      event=(trigger or {}).get('event'), depth=depth)
        ctx['prior_claims'] = prior
        out['ctx'] = ctx
        if not ctx['evidence']:
            out['skipped'] = 'sin evidencia disponible para esta entidad (no se consulta al modelo)'
            return out
        out['result'], out['meta'] = agent.run(ctx, provider)
    except LLMError as e:
        out['error'] = f'modelo: {str(e)[:400]}'
    except Exception as e:  # noqa: BLE001 — un agente roto no tumba el job
        out['error'] = f'{type(e).__name__}: {str(e)[:300]}'
        log.warning('research run %s/%s: %s', entity_id, agent_type, e)
    finally:
        out['seconds'] = time.time() - t0
    return out


def _finish_run(session, job, run, agent_type, work, fetchers=None, quotes=None):
    """Hilo principal: persiste claims/evidencia y cierra el AgentRun."""
    agent = AGENTS_BY_TYPE[agent_type]
    ctx = work.get('ctx')
    try:
        if ctx is not None:
            run.context_refs = ctx['refs_log']
            run.tools_used = ctx['tools_used']
        if work.get('skipped'):
            run.status, run.errors = 'skipped', [work['skipped']]
        elif work.get('error'):
            run.status, run.errors = 'failed', [work['error']]
        else:
            result, meta = work['result'], work['meta']
            run.model = meta.get('model')
            run.provider = meta.get('provider')
            run.tokens_in, run.tokens_out = meta.get('tokens_in'), meta.get('tokens_out')
            run.est_cost_usd = estimate_cost(run.model, run.tokens_in or 0, run.tokens_out or 0)
            run.validation = {'attempts': meta.get('attempts'), 'repaired': meta.get('repaired'),
                              'fallbacks': meta.get('fallbacks', []), 'errors': meta.get('errors', [])[:3]}
            run.summary = result.summary_es
            if quotes is None:
                quotes = baseline_quotes(job.entity_id, fetchers)
            n = persist_result(session, job, run, agent, ctx, result, quotes=quotes)
            run.claims_generated = n
            run.status = 'done'
            run.errors = ([{'unresolved_questions': result.unresolved_questions}]
                          if result.unresolved_questions else [])
    except Exception as e:  # noqa: BLE001
        run.status = 'failed'
        run.errors = [f'{type(e).__name__}: {str(e)[:300]}']
        log.warning('research persist %s/%s: %s', job.entity_id, agent_type, e)
    finally:
        run.completed_at = _now()
        run.latency_ms = int((work.get('seconds') or 0) * 1000)
        session.flush()
    return run


def run_agent(session, job, agent_type, provider=None, fetchers=None, quotes=None):
    """Ejecuta UN agente para el job (secuencial). Devuelve el AgentRun (siempre registrado).
    quotes: precios en vivo {símbolo: {...}} para la foto de partida (Phase 3)."""
    run, prior, ready = _prepare_run(session, job, agent_type)
    if not ready:
        return run
    work = _agent_work(job.entity_id, job.trigger, job.depth, agent_type, provider, fetchers, prior)
    return _finish_run(session, job, run, agent_type, work, fetchers=fetchers, quotes=quotes)


def persist_result(session, job, run, agent, ctx, result, quotes=None):
    """Escribe claims + evidencia. SOLO tablas research_* (+ registrar Source
    citada, idempotente). Nunca toca hechos del grafo ni datos de mercado.
    Phase 3: guarda la confianza CALIBRADA vigente (en confidence_components)
    y la foto de partida de la claim (claim_baselines) para calificarla después."""
    from core.entities import get_index
    ev_by_ref = {e['ref']: e for e in ctx['evidence']}
    known = get_index()['nodos']
    comp = _completeness(ctx)
    now = _now()
    cal_table = _calibration_table(session)
    n = 0
    for c in result.claims:
        support = [ev_by_ref[r] for r in c.evidence_refs if r in ev_by_ref]
        counter = [ev_by_ref[r] for r in c.counter_evidence_refs if r in ev_by_ref]
        if not support:
            continue   # sin evidencia de apoyo NO hay claim material (spec §3)
        conf, parts = compute_confidence(support, counter, c.agent_certainty, comp, now=now)
        cal = _calibration_for(agent.agent_type, conf, cal_table)
        if cal:
            parts = dict(parts, calibration=cal)
        affected = [x for x in c.affected_entities if x in known and x != job.entity_id][:15]
        days = _HZ_DAYS.get(c.horizon)
        claim = ResearchClaim(
            job_id=job.id, run_id=run.id, agent_id=agent.agent_id, agent_type=agent.agent_type,
            agent_version=agent.version, subject_entity_id=job.entity_id, predicate=c.predicate,
            object=c.object, claim_type=c.claim_type, topic=c.topic, stance=c.stance,
            statement_es=c.statement_es, statement_en=c.statement_en,
            reasoning_summary=c.reasoning_summary, horizon=c.horizon, depth=job.depth,
            valid_from=now, valid_to=(now + timedelta(days=days)) if days else None,
            confidence=conf, confidence_components=parts, affected_entity_ids=affected,
            falsifiers=c.falsifiers, status='active', model=run.model, prompt_version=agent.prompt_version)
        session.add(claim)
        session.flush()
        for stance, items in (('supporting', support), ('counter', counter)):
            for it in items:
                session.add(ResearchEvidence(
                    claim_id=claim.id, stance=stance, context_ref=it['ref'],
                    source_id=_register_source(session, it, agent),
                    source_type=it['source_type'], source_reference=it.get('reference'),
                    title=it.get('title'), excerpt=it.get('excerpt'),
                    published_at=_parse_dt(it.get('published_at')), retrieved_at=_parse_dt(it.get('retrieved_at')),
                    relevance=None, reliability=it.get('reliability')))
        # memoria: la conclusión previa del MISMO agente/tema/horizonte queda superada
        (session.query(ResearchClaim)
         .filter(ResearchClaim.subject_entity_id == job.entity_id, ResearchClaim.agent_type == agent.agent_type,
                 ResearchClaim.topic == c.topic, ResearchClaim.horizon == c.horizon,
                 ResearchClaim.status == 'active', ResearchClaim.id != claim.id)
         .update({'status': 'superseded'}, synchronize_session=False))
        detect_for(session, claim)
        _record_baseline(session, claim, quotes)
        n += 1
    session.flush()
    return n


# ── Phase 3 (research/outcomes.py): enganches que NUNCA rompen la investigación ──
def baseline_quotes(entity_id, fetchers=None):
    """Precio en vivo de la entidad y de SPY al crear las claims (auditoría de
    la foto de partida). Usa el fetcher 'profile' (caché 90 s; inyectable)."""
    try:
        from research.outcomes import BENCH, live_quotes, symbol_for
        sym = symbol_for(entity_id)
        if not sym:
            return {}
        prof = (fetchers or {}).get('profile')
        return live_quotes([sym, BENCH], profile_fn=prof)
    except Exception as e:  # noqa: BLE001
        log.warning('research baseline quotes %s: %s', entity_id, type(e).__name__)
        return {}


def _calibration_table(session):
    """Tabla de calibración (caché 10 min). La consulta va en un SAVEPOINT: si
    falla en Postgres (tablas de Phase 3 aún sin crear, tiempo agotado…) solo
    se deshace el SAVEPOINT y la transacción del job sigue sana."""
    try:
        from research.outcomes import calibration_table
        with session.begin_nested():
            return calibration_table(session)
    except Exception as e:  # noqa: BLE001
        log.warning('research calibration table: %s', type(e).__name__)
        return None


def _calibration_for(agent_type, conf, table):
    if table is None:
        return None
    try:
        from research.outcomes import calibration_detail
        return calibration_detail(agent_type, conf, table=table)
    except Exception:  # noqa: BLE001
        return None


def _record_baseline(session, claim, quotes):
    try:
        from research.outcomes import record_baseline
        with session.begin_nested():
            record_baseline(session, claim, quotes=quotes)
    except Exception as e:  # noqa: BLE001 — sin foto de partida, el backfill la crea después
        log.warning('research baseline %s: %s', claim.id, type(e).__name__)


def _register_source(session, item, agent):
    ref = item.get('reference') or ''
    if not ref.startswith('http'):
        return None
    try:
        from ontology.provenance import register_source
        return register_source(session, ref, kind=item.get('source_kind'), title=item.get('title') or '',
                               extractor='research', actor=f'research:{agent.agent_id}')
    except Exception:  # noqa: BLE001 — sin procedencia registrable, la evidencia guarda la URL igual
        return None


def synthesize(session, job):
    """Síntesis por horizonte: evidencia positiva, riesgos, preguntas abiertas y
    señales en conflicto. SIN comprar/vender/mantener (eso es Phase 3+)."""
    claims = (session.query(ResearchClaim).filter(ResearchClaim.subject_entity_id == job.entity_id,
                                                  ResearchClaim.status == 'active')
              .order_by(ResearchClaim.confidence.desc()).all())
    ids = {c.id for c in claims}
    rels = session.query(ClaimRelation).filter(ClaimRelation.claim_a.in_(ids) | ClaimRelation.claim_b.in_(ids)).all() if ids else []
    by = {}
    for c in claims:
        h = by.setdefault(c.horizon, {'positive': [], 'risks': [], 'neutral': []})
        item = {'claim_id': c.id, 'agent': c.agent_type, 'es': c.statement_es, 'en': c.statement_en,
                'confidence': c.confidence}
        (h['positive'] if c.stance == 'positive' else h['risks'] if c.stance == 'negative' else h['neutral']).append(item)
    runs = session.query(AgentRun).filter(AgentRun.job_id == job.id).all()
    open_q = []
    for r in runs:
        for e in (r.errors or []):
            if isinstance(e, dict):
                open_q += e.get('unresolved_questions', [])
    seen, uq = set(), []
    for q in open_q:
        k = str(q).strip().lower()
        if k and k not in seen:
            seen.add(k)
            uq.append(q)
    return {'by_horizon': by, 'conflicts': [{'a': r.claim_a, 'b': r.claim_b, 'reason': r.reason} for r in rels],
            'open_questions': uq[:10], 'generated_at': _now().isoformat(),
            'note': 'Síntesis de investigación: no es una recomendación de compra/venta.'}


def execute_job(session, job, provider_factory=None, fetchers=None, on_start=None, on_done=None):
    """on_start(agent_type) / on_done(agent_type, run): avisos opcionales (la sala del comité los narra)."""
    job.status = 'running'
    session.flush()
    ok = 0
    quotes = baseline_quotes(job.entity_id, fetchers) if job.agents else {}
    # Los agentes trabajan EN PARALELO (contexto + IA en hilos, sin base); la
    # base solo se toca aquí, en el hilo del job. Antes iban de a uno: 4 agentes
    # × ~40 s. RESEARCH_PARALLEL (3) acota la concurrencia hacia la IA.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    pending = []
    for agent_type in job.agents or []:
        run, prior, ready = _prepare_run(session, job, agent_type)
        if not ready:
            session.commit()
            if on_done:
                on_done(agent_type, run)
            continue
        pending.append((agent_type, run, prior))
    session.commit()
    if pending:
        par = max(1, min(_cfg('RESEARCH_PARALLEL', 3, int), len(pending)))
        with ThreadPoolExecutor(max_workers=par, thread_name_prefix='research-agent') as ex:
            futs = {}
            for agent_type, run, prior in pending:
                prov = provider_factory(agent_type) if provider_factory else None
                if on_start:
                    on_start(agent_type)
                futs[ex.submit(_agent_work, job.entity_id, job.trigger, job.depth, agent_type, prov,
                               fetchers, prior)] = (agent_type, run)
            for fut in as_completed(futs):
                agent_type, run = futs[fut]
                try:
                    work = fut.result()
                except Exception as e:  # noqa: BLE001
                    work = {'error': f'{type(e).__name__}: {str(e)[:300]}'}
                _finish_run(session, job, run, agent_type, work, fetchers=fetchers, quotes=quotes)
                ok += 1 if run.status == 'done' else 0
                session.commit()   # cada agente visible en vivo (feed de actividad)
                if on_done:
                    on_done(agent_type, run)
    # contradicciones SEMÁNTICAS (IA, acotadas) — solo Normal/Profunda
    if ok and job.depth != 'QUICK':
        try:
            from research.contradictions import detect_semantic
            prov = provider_factory('contradictions') if provider_factory else None
            if prov is None:
                from research.llm import RoutedProvider, route_for
                prov = RoutedProvider(route_for('contradictions'))
            detect_semantic(session, job.id, prov)
            session.commit()
        except Exception as e:  # noqa: BLE001
            log.warning('semantic contradictions: %s', type(e).__name__)
    job.synthesis = synthesize(session, job)
    # Si NINGÚN agente terminó bien, el job es 'failed' → el dedupe (que solo
    # reutiliza queued/running/done) deja reintentar enseguida.
    job.status = 'done' if ok or not job.agents else 'failed'
    if not ok and job.agents:
        job.error = 'ningún agente produjo resultado'
    job.completed_at = _now()
    session.flush()
    return job


def execute_job_async(job_id):
    """Corre el job en un hilo (gunicorn: 1 worker × 8 hilos). El cliente
    consulta /api/research/jobs/<id> para ver el progreso real."""
    def _work():
        from ontology.db import session_scope
        try:
            with session_scope() as s:
                job = s.get(ResearchJob, job_id)
                if job and job.status == 'queued':
                    execute_job(s, job)
        except Exception as e:  # noqa: BLE001
            log.warning('research job %s: %s', job_id, e)
            try:
                with session_scope() as s:
                    job = s.get(ResearchJob, job_id)
                    if job:
                        job.status, job.error, job.completed_at = 'failed', str(e)[:300], _now()
            except Exception:  # noqa: BLE001
                pass
    t = threading.Thread(target=_work, name=f'research-{job_id[:8]}', daemon=True)
    t.start()
    return t
