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
