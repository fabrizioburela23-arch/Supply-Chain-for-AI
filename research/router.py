"""research/router.py — evento → relevancia → agentes (Phase 2 event-driven).

Los agentes NO corren todos todo el tiempo: un evento activa solo a los
suscritos (Agent.subscribed_events) y solo sobre las entidades relevantes.

Relevancia (grafo, con límites configurables para no explotar):
  semillas  = entidades nombradas en el evento + entidades del país citado
  expansión = BFS por relaciones (default: aguas ABAJO — a quién provee)
  límites   = max_depth, max_nodes, relationship_types, min_weight
Deduplicación: el mismo evento (tipo + titular/entidades) dentro de 24 h no
dispara investigaciones de nuevo. Profundidad QUICK (económica) por defecto.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone

from core.entities import UMBRAL_BUSQUEDA, get_index, resolve
from research.agents import AGENTS
from research.models import ResearchJob

DEFAULT_LIMITS = {'max_depth': 2, 'max_nodes': 12, 'relationship_types': None, 'min_weight': 2,
                  'max_jobs': 3, 'direction': 'down'}


def agents_for(event_type):
    et = str(event_type or '').upper()
    return [a.agent_type for a in AGENTS if et in a.subscribed_events]


def _country_nodes(country, limit=8):
    if not country:
        return []
    nodes = get_index()['nodos']
    c = str(country).lower()
    hits = [n for n in nodes.values() if str(n.get('country') or '').lower() == c]
    hits.sort(key=lambda n: (not n.get('big'), n.get('id')))
    return [n['id'] for n in hits[:limit]]


def relevant_entities(event, limits=None):
    """Devuelve lista ordenada [{id, label, distance, via}] acotada por límites."""
    lim = dict(DEFAULT_LIMITS, **(limits or {}))
    idx = get_index()
    nodes = idx['nodos']
    seeds = []
    for name in (event.get('entities') or [])[:10]:
        r = resolve(str(name), umbral=UMBRAL_BUSQUEDA)
        if r and r['id'] not in seeds:
            seeds.append(r['id'])
    for nid in _country_nodes(event.get('country')):
        if nid not in seeds:
            seeds.append(nid)
    if not seeds:
        return []
    links = idx.get('_links')
    if links is None:
        from core.entities import _SNAPSHOT
        with open(_SNAPSHOT, encoding='utf-8') as fh:
            links = json.load(fh).get('links', [])
        idx['_links'] = links
    out = [{'id': s, 'label': (nodes.get(s) or {}).get('label', s), 'distance': 0, 'via': None} for s in seeds]
    seen = set(seeds)
    frontier = list(seeds)
    for d in range(1, lim['max_depth'] + 1):
        nxt = []
        cand = []
        for l in links:
            src, tgt = l.get('source'), l.get('target')
            if lim['relationship_types'] and l.get('type') not in lim['relationship_types']:
                continue
            if (l.get('w') or 0) < lim['min_weight']:
                continue
            if lim['direction'] in ('down', 'both') and src in frontier and tgt not in seen:
                cand.append((l.get('w') or 0, tgt, src))
            if lim['direction'] in ('up', 'both') and tgt in frontier and src not in seen:
                cand.append((l.get('w') or 0, src, tgt))
        cand.sort(key=lambda x: -x[0])
        for w, other, via in cand:
            if len(out) >= lim['max_nodes']:
                break
            if other in seen:
                continue
            seen.add(other)
            nxt.append(other)
            out.append({'id': other, 'label': (nodes.get(other) or {}).get('label', other),
                        'distance': d, 'via': via, 'weight': w})
        frontier = nxt
        if not frontier or len(out) >= lim['max_nodes']:
            break
    return out


def event_key(event):
    raw = json.dumps({'t': str(event.get('type') or '').upper(), 'h': (event.get('headline') or '')[:200],
                      'e': sorted(event.get('entities') or []), 'c': event.get('country')}, sort_keys=True)
    return 'evt:' + hashlib.sha1(raw.encode()).hexdigest()[:20]


def dispatch_event(session, event, actor='system', execute=True, limits=None, now=None):
    """Clasifica el evento, calcula relevancia y crea jobs QUICK para las
    entidades más relevantes con los agentes suscritos. Idempotente 24 h."""
    from research.runner import create_job, execute_job_async
    now = now or datetime.now(timezone.utc)
    etype = str(event.get('type') or '').upper()
    agents = agents_for(etype)
    if not agents:
        return {'event_type': etype, 'agents': [], 'jobs': [], 'reason': 'ningún agente suscrito a ese evento'}
    key = event_key(event)
    dup = (session.query(ResearchJob).filter(ResearchJob.trigger['event_key'].astext == key,
                                             ResearchJob.created_at >= now - timedelta(hours=24)).first())
    if dup:
        return {'event_type': etype, 'agents': agents, 'jobs': [], 'duplicate_of': dup.id,
                'reason': 'evento duplicado (24 h): no se re-investiga'}
    lim = dict(DEFAULT_LIMITS, **(limits or {}))
    rel = relevant_entities(event, lim)
    jobs = []
    for ent in rel[:lim['max_jobs']]:
        job, reused = create_job(session, ent['id'], depth=str(event.get('depth') or 'QUICK').upper(),
                                 agents=agents, requested_by=actor,
                                 trigger={'kind': 'event', 'event_key': key, 'event': {
                                     'type': etype, 'headline': (event.get('headline') or '')[:300],
                                     'source_url': event.get('source_url'), 'distance': ent['distance']}})
        jobs.append({'job_id': job.id, 'entity_id': ent['id'], 'reused': reused})
    session.flush()
    if execute:
        session.commit()
        for j in jobs:
            if not j['reused']:
                execute_job_async(j['job_id'])
    return {'event_type': etype, 'event_key': key, 'agents': agents, 'relevant': rel, 'jobs': jobs}
