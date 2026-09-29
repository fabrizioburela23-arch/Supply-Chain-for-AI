"""research/contradictions.py — detección INICIAL de tensiones entre claims.

Regla v1 (determinista, auditable): dos claims ACTIVAS sobre la misma entidad,
el mismo tema y el MISMO horizonte, con posturas opuestas (positive vs
negative) → POTENTIALLY_CONTRADICTS. No se decide quién tiene razón (Phase 3).

Regla v2 (2026-09-29): también entre TEMAS RELACIONADOS (familias fijas y
auditables: márgenes/rentabilidad/flujo de caja, crecimiento/demanda,
momentum/sentimiento, geopolítica/regulación) — "márgenes se expanden" vs
"rentabilidad cae" es la misma tensión aunque el agente eligió otro tema.

Distinto horizonte NO es contradicción: "bajista a corto" y "crecimiento
sólido a largo" coexisten (spec §4). Tampoco se compara una claim contra
otra del MISMO agente y tema/horizonte: eso es una actualización (la vieja
pasa a 'superseded' en runner.py).
"""
from research.models import ClaimRelation, ResearchClaim

OPPOSITE = {('positive', 'negative'), ('negative', 'positive')}

TOPIC_FAMILIES = (
    ('margins', 'profitability', 'cash_flow'),
    ('revenue_growth', 'demand'),
    ('momentum', 'sentiment'),
    ('geopolitics', 'regulation'),
)


def related_topics(topic):
    """El tema y los de su familia (si tiene)."""
    for fam in TOPIC_FAMILIES:
        if topic in fam:
            return fam
    return (topic,)


def detect_for(session, claim):
    """Crea relaciones para UNA claim nueva. Devuelve las creadas."""
    rows = (session.query(ResearchClaim)
            .filter(ResearchClaim.subject_entity_id == claim.subject_entity_id,
                    ResearchClaim.topic.in_(related_topics(claim.topic)),
                    ResearchClaim.horizon == claim.horizon,
                    ResearchClaim.status == 'active',
                    ResearchClaim.id != claim.id).all())
    created = []
    for other in rows:
        if other.agent_type == claim.agent_type:
            continue
        if (claim.stance, other.stance) not in OPPOSITE:
            continue
        exists = session.query(ClaimRelation).filter(
            ((ClaimRelation.claim_a == claim.id) & (ClaimRelation.claim_b == other.id)) |
            ((ClaimRelation.claim_a == other.id) & (ClaimRelation.claim_b == claim.id))).first()
        if exists:
            continue
        tema = (claim.topic if other.topic == claim.topic
                else f'temas relacionados ({claim.topic} y {other.topic})')
        rel = ClaimRelation(claim_a=claim.id, claim_b=other.id, rel_type='POTENTIALLY_CONTRADICTS',
                            reason=(f'{claim.agent_type} ve «{claim.stance}» y {other.agent_type} ve '
                                    f'«{other.stance}» sobre {tema} en el mismo horizonte '
                                    f'({claim.horizon}). No se resuelve aquí: queda para el comité (Phase 3).'))
        session.add(rel)
        created.append(rel)
    session.flush()
    return created


# ── v3 (2026-09-29): contradicciones SEMÁNTICAS con IA, acotadas ────────────
# Pares que la regla no ve: mismo sujeto y horizonte, agentes distintos,
# posturas opuestas, temas NO relacionados ("la demanda de IA crece" vs
# "la regulación china frenará las ventas"). Un modelo decide si de verdad se
# contradicen y por qué; salida validada. Máx MAX_SEMANTIC_PAIRS por job.
MAX_SEMANTIC_PAIRS = 6

try:
    from pydantic import BaseModel, Field

    class SemanticVerdict(BaseModel):
        contradicts: bool
        reason_es: str = Field(min_length=8, max_length=400)
        reason_en: str = Field(min_length=8, max_length=400)
except Exception:  # noqa: BLE001
    SemanticVerdict = None

_SYS = ('Eres un revisor de investigación financiera. Te doy DOS conclusiones de analistas distintos '
        'sobre la MISMA empresa y el MISMO horizonte. Decide si se CONTRADICEN (no pueden ser ciertas a '
        'la vez, o una debilita directamente a la otra) o si solo hablan de cosas distintas que pueden '
        'convivir. Sé estricto: temas distintos NO es contradicción. No recomiendes comprar ni vender. '
        'Responde SOLO JSON: {"contradicts": true|false, "reason_es": "...", "reason_en": "..."}')


def semantic_pairs(session, job_id):
    claims = session.query(ResearchClaim).filter(ResearchClaim.job_id == job_id,
                                                 ResearchClaim.status == 'active').all()
    if not claims:
        return []
    subject = claims[0].subject_entity_id
    pool = session.query(ResearchClaim).filter(ResearchClaim.subject_entity_id == subject,
                                               ResearchClaim.status == 'active').all()
    pairs, seen = [], set()
    for a in claims:
        for b in pool:
            if a.id == b.id or a.agent_type == b.agent_type or a.horizon != b.horizon:
                continue
            if (a.stance, b.stance) not in OPPOSITE or b.topic in related_topics(a.topic):
                continue          # ya lo cubre la regla v1/v2 (o no son opuestas)
            k = frozenset((a.id, b.id))
            if k in seen:
                continue
            seen.add(k)
            exists = session.query(ClaimRelation).filter(
                ((ClaimRelation.claim_a == a.id) & (ClaimRelation.claim_b == b.id)) |
                ((ClaimRelation.claim_a == b.id) & (ClaimRelation.claim_b == a.id))).first()
            if not exists:
                pairs.append((a, b))
    pairs.sort(key=lambda p: -((p[0].confidence or 0) + (p[1].confidence or 0)))
    return pairs[:MAX_SEMANTIC_PAIRS]


def detect_semantic(session, job_id, provider):
    """Revisa con IA los pares candidatos del job. Devuelve relaciones creadas.
    Un fallo del modelo en un par NO rompe nada: ese par se omite."""
    if SemanticVerdict is None or provider is None:
        return []
    created = []
    for a, b in semantic_pairs(session, job_id):
        prompt = (f'Horizonte: {a.horizon}\n'
                  f'A ({a.agent_type}, postura {a.stance}, tema {a.topic}): {a.statement_es}\n'
                  f'   razonamiento: {a.reasoning_summary or ""}\n'
                  f'B ({b.agent_type}, postura {b.stance}, tema {b.topic}): {b.statement_es}\n'
                  f'   razonamiento: {b.reasoning_summary or ""}')
        try:
            v, _meta = provider.structured_generate(_SYS, prompt, SemanticVerdict, max_tokens=500, max_attempts=2)
        except Exception:  # noqa: BLE001
            continue
        if not v.contradicts:
            continue
        rel = ClaimRelation(claim_a=a.id, claim_b=b.id, rel_type='POTENTIALLY_CONTRADICTS',
                            reason=f'(revisión IA) {v.reason_es} | EN: {v.reason_en}'[:900])
        session.add(rel)
        created.append(rel)
    session.flush()
    return created
