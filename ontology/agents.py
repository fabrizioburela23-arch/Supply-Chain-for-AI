"""ontology/agents.py — Fase 3: agentes que observan la ontología y PROPONEN
Acciones. Nada se ejecuta sin aprobación humana (salvo lo que el usuario
marque como auto-aprobable, no implementado aún — todo pasa por la cola).

Runtime: Railway corre `gunicorn --workers 2`. Un scheduler en proceso
(APScheduler) correría cada agente 2 VECES (uno por worker) y duplicaría
propuestas — es un bug clásico de correr cron dentro de workers de gunicorn.
En vez de eso, los agentes corren bajo demanda vía `POST /api/ontology/agents/run`
(un humano lo dispara desde el botón "🔍 Revisar ahora", o se puede apuntar un
cron externo de Railway/GitHub Actions a esa URL — documentado en ESTADO.md).
Cada agente además deduplica sus propias propuestas (no repite una señal ya
pendiente o resuelta recientemente para el mismo objeto).

Contrato de un agente: observe(session) -> list[Signal]; propose(session, Signal)
-> dict|None con {action_type, payload, object_id, confidence, explanation}.
"""
import time as _time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func as sqlfunc

from ontology.models import ObjectRecord, LinkRecord, ProposedAction, Event


def _utcnow():
    return datetime.now(timezone.utc)


def _recently_proposed(session, agent, action_type, object_id, hours=24):
    """Evita re-proponer lo mismo en cada corrida — solo si ya hay una
    propuesta pendiente O resuelta (approved/rejected) en la ventana."""
    cutoff = _utcnow() - timedelta(hours=hours)
    q = select(ProposedAction).where(
        ProposedAction.agent == agent, ProposedAction.action_type == action_type,
        ProposedAction.object_id == object_id, ProposedAction.created_at >= cutoff,
    )
    return session.scalars(q).first() is not None


def _ai_explain(prompt, fallback):
    """Genera la explicación en lenguaje natural con el mismo patrón
    multi-proveedor del servidor (_ai_complete). Si falla, usa un fallback
    determinista — un agente nunca debe bloquearse por la IA."""
    try:
        import server  # el módulo Flask ya expone _ai_complete
        text, _model = server._ai_complete(
            'Eres un analista senior de riesgo de cadena de suministro. Responde en '
            'español, 1-2 frases, concreto y sin relleno.', prompt, max_tokens=200)
        return text.strip() if text else fallback
    except Exception:
        return fallback


# ── Agente 1: Centinela NRS ──────────────────────────────────────────────────
# Vigila: recálculo topológico + geo tras cada corrida. Propone: MarcarRiesgo
# cuando el score cruza un umbral y no hay ya un nrs_override reciente.

GEO_RISK = {'China': 28, 'Taiwan': 25, 'Korea': 15, 'Japan': 12, 'EEUU': 8, 'Europa': 10, 'Israel': 18}


def _compute_server_nrs(session, company):
    """Réplica server-side de la fórmula NRS del cliente (app.html computeNRS):
    geo (país) + grado en el grafo (centralidad proxy) + margen + concentración.
    No pretende ser idéntica al pixel — es la misma heurística de riesgo."""
    props = company.properties or {}
    geo = GEO_RISK.get(props.get('country'), 15)
    degree = session.scalar(
        select(sqlfunc.count(LinkRecord.id)).where(
            (LinkRecord.source_id == company.id) | (LinkRecord.target_id == company.id),
            LinkRecord.valid_to.is_(None),
        )
    ) or 0
    chain = min(25, degree * 2.5)
    margin = props.get('margin')
    # clamp [0,20]: el cliente (app.html computeNRS) tiene esta misma fórmula
    # SIN este límite inferior, así que un margen muy negativo (ej. -2.5 en
    # empresas pre-revenue) puede inflar 'market' muy por encima de 20 allá.
    # Aquí sí lo acotamos para que el score sea comparable entre empresas —
    # nota para el usuario: vale la pena revisar/alinear la fórmula del cliente.
    market = max(0, min(20, round((1 - min(1, (margin if margin is not None else 0.15) / 0.4)) * 20)))
    concentration = 10 if props.get('country') in ('Taiwan', 'China') else 4
    return max(0, min(100, round(geo + chain + market + concentration)))


class CentinelaNRS:
    name = 'centinela_nrs'
    THRESHOLD = 70

    def observe(self, session):
        companies = session.scalars(select(ObjectRecord).where(ObjectRecord.type == 'Company')).all()
        signals = []
        for c in companies:
            existing_override = (c.properties or {}).get('nrs_override')
            score = _compute_server_nrs(session, c)
            if score >= self.THRESHOLD and existing_override != score:
                signals.append({'company': c, 'score': score})
        return signals

    def propose(self, session, signal):
        c, score = signal['company'], signal['score']
        if _recently_proposed(session, self.name, 'MarcarRiesgo', c.id):
            return None
        explanation = _ai_explain(
            f'La empresa {c.label} ({(c.properties or {}).get("country","?")}) tiene un NRS calculado de {score}/100 '
            f'(riesgo geopolítico + concentración de cadena de suministro). Explica en 1 frase por qué esto importa para un inversor.',
            f'{c.label} cruzó el umbral de riesgo (NRS {score}/100) por su concentración geográfica y de cadena de suministro.')
        return {
            'action_type': 'MarcarRiesgo', 'object_id': c.id, 'confidence': min(0.95, score / 100),
            'payload': {'company_id': c.id, 'nivel': score, 'razon': explanation},
            'explanation': explanation,
        }


# ── Agente 2: Lector GDELT ────────────────────────────────────────────────────
# Vigila: noticias que mencionen empresas del grafo. Propone: AnotarObjeto con
# un resumen. Limitado a una muestra pequeña por corrida (rate-limit GDELT).

class LectorGDELT:
    name = 'lector_gdelt'
    SAMPLE_SIZE = 5

    def observe(self, session):
        # muestra: las empresas con más vínculos vigentes (más relevantes / chokepoints)
        rows = session.execute(
            select(LinkRecord.source_id, sqlfunc.count(LinkRecord.id).label('deg'))
            .where(LinkRecord.valid_to.is_(None)).group_by(LinkRecord.source_id)
            .order_by(sqlfunc.count(LinkRecord.id).desc()).limit(self.SAMPLE_SIZE)
        ).all()
        ids = [r[0] for r in rows]
        companies = session.scalars(select(ObjectRecord).where(ObjectRecord.id.in_(ids))).all() if ids else []
        return [{'company': c} for c in companies]

    def propose(self, session, signal):
        c = signal['company']
        if _recently_proposed(session, self.name, 'AnotarObjeto', c.id, hours=20):
            return None
        try:
            import requests
            r = requests.get('https://api.gdeltproject.org/api/v2/doc/doc',
                              params={'query': c.label, 'mode': 'artlist', 'maxrecords': 3, 'format': 'json'},
                              timeout=6)
            arts = (r.json() or {}).get('articles', []) if r.ok else []
        except Exception:
            arts = []
        if not arts:
            return None
        titles = '; '.join(a.get('title', '') for a in arts[:3] if a.get('title'))
        if not titles:
            return None
        summary = _ai_explain(
            f'Resume en 1 frase para un inversor qué implican estas noticias sobre {c.label}: {titles}',
            f'Noticias recientes sobre {c.label}: {titles[:180]}')
        return {
            'action_type': 'AnotarObjeto', 'object_id': c.id, 'confidence': 0.6,
            'payload': {'object_id': c.id, 'texto': f'[GDELT] {summary}'},
            'explanation': summary,
        }


# ── Agente 3: Guardián de cartera ────────────────────────────────────────────
# Vigila: posiciones (derivadas de PositionAdjustment, ver ontology/actions.py
# AjustarPosicion) vs. riesgo. Propone: AjustarPosicion (reducir exposición).
# LIMITACIÓN HONESTA: el portafolio "real" del usuario hoy vive en localStorage
# del navegador (ver docs/AUDITORIA.md) — este agente solo ve posiciones que
# se hayan registrado EN LA ONTOLOGÍA vía la Acción AjustarPosicion. Si el
# usuario nunca la usó, observe() devuelve una lista vacía (comportamiento
# correcto, no un error).

class GuardianCartera:
    name = 'guardian_cartera'
    RISK_THRESHOLD = 75

    def _holdings(self, session):
        adjustments = session.scalars(
            select(ObjectRecord).where(ObjectRecord.type == 'PositionAdjustment')
        ).all()
        net = {}
        for a in adjustments:
            p = a.properties or {}
            cid = p.get('company_id')
            if not cid:
                continue
            net[cid] = net.get(cid, 0) + float(p.get('delta') or 0)
        return {cid: qty for cid, qty in net.items() if qty > 0}

    def observe(self, session):
        holdings = self._holdings(session)
        if not holdings:
            return []
        signals = []
        for cid, qty in holdings.items():
            c = session.get(ObjectRecord, cid)
            if not c:
                continue
            score = (c.properties or {}).get('nrs_override') or _compute_server_nrs(session, c)
            if score >= self.RISK_THRESHOLD:
                signals.append({'company': c, 'qty': qty, 'score': score})
        return signals

    def propose(self, session, signal):
        c, qty, score = signal['company'], signal['qty'], signal['score']
        if _recently_proposed(session, self.name, 'AjustarPosicion', c.id, hours=48):
            return None
        reduce_by = -round(qty * 0.2, 2)
        explanation = _ai_explain(
            f'Tengo {qty} unidades de {c.label}, cuyo riesgo (NRS {score}/100) es alto. Sugiere en 1 frase si conviene reducir exposición.',
            f'{c.label} tiene riesgo elevado (NRS {score}/100) — considera reducir exposición ~20%.')
        return {
            'action_type': 'AjustarPosicion', 'object_id': c.id, 'confidence': 0.5,
            'payload': {'ticker': (c.properties or {}).get('mkt') or c.id, 'delta': reduce_by,
                        'razon': explanation},
            'explanation': explanation,
        }


# ── Agente 4: Cartógrafo ──────────────────────────────────────────────────────
# Vigila: inconsistencias del grafo (nodos aislados sin vínculos vigentes).
# Propone: AnotarObjeto señalando la brecha para revisión humana.

class Cartografo:
    name = 'cartografo'

    def observe(self, session):
        companies = session.scalars(select(ObjectRecord).where(ObjectRecord.type == 'Company')).all()
        linked_ids = set()
        for row in session.execute(
            select(LinkRecord.source_id, LinkRecord.target_id).where(LinkRecord.valid_to.is_(None))
        ).all():
            linked_ids.add(row[0]); linked_ids.add(row[1])
        isolated = [c for c in companies if c.id not in linked_ids]
        return [{'company': c} for c in isolated]

    def propose(self, session, signal):
        c = signal['company']
        if _recently_proposed(session, self.name, 'AnotarObjeto', c.id, hours=24 * 30):
            return None  # esto no cambia seguido — ventana larga
        return {
            'action_type': 'AnotarObjeto', 'object_id': c.id, 'confidence': 0.9,
            'payload': {'object_id': c.id, 'texto': '[Cartógrafo] Objeto sin relaciones de cadena de suministro mapeadas — revisar.'},
            'explanation': f'{c.label} no tiene ningún vínculo vigente en la ontología.',
        }


AGENTS = [CentinelaNRS(), LectorGDELT(), GuardianCartera(), Cartografo()]
AGENTS_BY_NAME = {a.name: a for a in AGENTS}


def run_agents(session, only=None, max_proposals_per_agent=8):
    """Corre observe()+propose() de cada agente habilitado, inserta las
    propuestas nuevas en `proposed_actions`. Devuelve un resumen por agente."""
    summary = {}
    agents = [a for a in AGENTS if not only or a.name in only]
    for agent in agents:
        t0 = _time.time()
        created = 0
        try:
            signals = agent.observe(session)
            for sig in signals[:max_proposals_per_agent * 3]:  # margen por si muchas se dedupan
                if created >= max_proposals_per_agent:
                    break
                try:
                    proposal = agent.propose(session, sig)
                except Exception as e:  # noqa: BLE001 — un agente roto no debe tumbar a los demás
                    proposal = None
                if not proposal:
                    continue
                pa = ProposedAction(
                    agent=agent.name, action_type=proposal['action_type'],
                    payload=proposal['payload'], object_id=proposal.get('object_id'),
                    confidence=proposal.get('confidence'), explanation=proposal.get('explanation'),
                    status='pending',
                )
                session.add(pa)
                created += 1
            summary[agent.name] = {'ok': True, 'signals': len(signals), 'proposals': created,
                                    'ms': int((_time.time() - t0) * 1000)}
        except Exception as e:  # noqa: BLE001
            summary[agent.name] = {'ok': False, 'error': str(e)[:200], 'ms': int((_time.time() - t0) * 1000)}
    return summary


# ── Agente 5: Cronista (Brief Matinal) — informativo, sin aprobación ─────────

def brief_matinal(session, hours=24):
    """Resumen de lo que pasó en la ontología en las últimas `hours` horas:
    eventos nuevos, acciones humanas, propuestas de agentes. No requiere
    aprobación — es un reporte de lectura."""
    cutoff = _utcnow() - timedelta(hours=hours)
    actions = session.scalars(
        select(Event).where(Event.event_type == 'ActionExecuted', Event.recorded_at >= cutoff)
        .order_by(Event.recorded_at.desc())
    ).all()
    proposals = session.scalars(
        select(ProposedAction).where(ProposedAction.created_at >= cutoff).order_by(ProposedAction.created_at.desc())
    ).all()
    facts_new = session.scalar(
        select(sqlfunc.count(Event.id)).where(
            Event.event_type == 'LinkCreated', Event.recorded_at >= cutoff, Event.source != 'migration_v0_links',
        )
    ) or 0

    items = []
    for a in actions[:20]:
        p = a.payload or {}
        items.append(f"{p.get('action', a.event_type)} por {a.actor} sobre {a.object_id or a.target_id or '—'}")
    for p in proposals[:20]:
        items.append(f"[propuesta pendiente] {p.agent} sugiere {p.action_type} — {p.explanation or ''}")

    text = None
    if items:
        text = _ai_explain(
            'Resume en 3-5 frases, en español, para un inversor que abre la app en la mañana, '
            'qué pasó en su ontología de inversión en las últimas ' + str(hours) + ' horas:\n' + '\n'.join(items[:25]),
            None)
    if not text:
        text = (f'{len(actions)} acciones registradas y {len(proposals)} propuestas de agentes '
                f'en las últimas {hours}h.' if (actions or proposals) else
                'Sin actividad nueva en la ontología en las últimas horas.')

    return {
        'hours': hours, 'summary': text, 'actions_count': len(actions),
        'proposals_count': len(proposals), 'new_links': facts_new,
        'pending_proposals': [{'agent': p.agent, 'action_type': p.action_type, 'explanation': p.explanation,
                                'confidence': p.confidence} for p in proposals if p.status == 'pending'][:10],
    }


# ── Fase 4: evaluador de alertas ──────────────────────────────────────────────
# Regla: {entity, metric:'price'|'nrs', op:'>'|'<'|'>='|'<=', value} o
# {region, event_type:'news'}. No requiere aprobación (a diferencia de las
# Acciones) — es una notificación, no una escritura de dominio.

def _get_live_price(ticker):
    """Precio en vivo vía Finnhub, reusando server._fetch_quote_raw (mismo
    helper que /api/quote/<ticker>). Devuelve None si no hay key o falla."""
    try:
        import server
        if not server.FINNHUB:
            return None
        data, err = server._fetch_quote_raw(ticker)
        if err or not data or not data.get('c'):
            return None
        return float(data['c'])
    except Exception:
        return None


_OPS = {
    '>': lambda a, b: a > b, '<': lambda a, b: a < b,
    '>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b, '=': lambda a, b: a == b,
}


def evaluate_alert(session, rule):
    """Evalúa UNA regla y devuelve (fired: bool, current_value, detail)."""
    metric = rule.get('metric')
    if metric == 'price':
        entity = rule.get('entity')
        obj = session.get(ObjectRecord, entity)
        ticker = (obj.properties.get('mkt') if obj else None) or entity
        price = _get_live_price(ticker)
        if price is None:
            return False, None, 'sin precio en vivo disponible'
        op = _OPS.get(rule.get('op'), _OPS['>'])
        fired = op(price, float(rule.get('value', 0)))
        return fired, price, f'{ticker} = {price}'
    if metric == 'nrs':
        entity = rule.get('entity')
        obj = session.get(ObjectRecord, entity)
        if not obj:
            return False, None, 'objeto no encontrado'
        score = (obj.properties or {}).get('nrs_override')
        if score is None:
            score = _compute_server_nrs(session, obj)
        op = _OPS.get(rule.get('op'), _OPS['>'])
        fired = op(score, float(rule.get('value', 0)))
        return fired, score, f'NRS({obj.label}) = {score}'
    if metric == 'news_region':
        region = (rule.get('region') or '').lower()
        cutoff = _utcnow() - timedelta(hours=24)
        recent = session.scalars(
            select(Event).where(Event.event_type == 'ActionExecuted', Event.recorded_at >= cutoff)
        ).all()
        hits = [e for e in recent if region in str((e.payload or {}).get('texto', '')).lower()]
        return bool(hits), len(hits), f'{len(hits)} anotaciones sobre "{region}" en 24h'
    return False, None, f'métrica desconocida: {metric}'


def check_alerts(session, owner=None):
    """Evalúa todas las alertas activas (o las de `owner`), marca last_fired_at
    en las que dispararon, y devuelve la lista de las que dispararon AHORA
    (para que el cliente muestre la notificación del navegador)."""
    from ontology.models import Alert
    q = select(Alert).where(Alert.is_active.is_(True))
    if owner:
        q = q.where(Alert.owner == owner)
    alerts = session.scalars(q).all()
    fired_now = []
    for a in alerts:
        fired, value, detail = evaluate_alert(session, a.rule)
        if fired:
            a.last_fired_at = _utcnow()
            fired_now.append({'id': str(a.id), 'rule': a.rule, 'value': value, 'detail': detail})
    return fired_now
