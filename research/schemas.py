"""research/schemas.py — contrato de la salida de un agente (Pydantic v2).

El modelo NO escribe texto libre al grafo: devuelve un AgentResearchResult que
se valida aquí antes de persistir. Reglas duras (además de tipos):
  · toda claim cita ≥1 evidencia de apoyo, y SOLO ids del paquete de contexto
    (E1..En) — una fuente que no se le dio no existe (anti-alucinación);
  · horizonte, postura y tema salen de vocabularios cerrados;
  · toda claim dice qué la refutaría (falsifiers ≥1).
Si no cumple: reintento con el error como feedback → reparación → rechazo.
Nunca se guarda JSON inválido.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from research.models import HORIZONS, STANCES

TOPICS = ('revenue_growth', 'margins', 'profitability', 'cash_flow', 'balance_sheet',
          'valuation', 'demand', 'competition', 'supply_chain', 'regulation',
          'geopolitics', 'macro', 'technology', 'management', 'capital_allocation',
          'momentum', 'volatility', 'sentiment', 'other')
CLAIM_TYPES = ('observation', 'risk', 'opportunity', 'forecast')


class ClaimOut(BaseModel):
    predicate: str = Field(min_length=3, max_length=80,
                           description='UPPER_SNAKE verbo-frase, p.ej. MAY_FACE_MARGIN_PRESSURE')
    object: Optional[str] = Field(default=None, max_length=300)
    claim_type: str
    topic: str
    stance: str
    horizon: str
    statement_es: str = Field(min_length=10, max_length=600)
    statement_en: str = Field(min_length=10, max_length=600)
    reasoning_summary: str = Field(min_length=10, max_length=900,
                                   description='resumen auditable de POR QUÉ (no chain-of-thought)')
    agent_certainty: float = Field(ge=0, le=1)
    evidence_refs: List[str] = Field(min_length=1, max_length=8)
    counter_evidence_refs: List[str] = Field(default_factory=list, max_length=8)
    affected_entities: List[str] = Field(default_factory=list, max_length=15)
    falsifiers: List[str] = Field(min_length=1, max_length=5)

    @field_validator('predicate')
    @classmethod
    def _pred(cls, v):
        v = v.strip().upper().replace(' ', '_').replace('-', '_')
        return ''.join(ch for ch in v if ch.isalnum() or ch == '_')[:80]

    @field_validator('claim_type')
    @classmethod
    def _ct(cls, v):
        v = str(v).strip().lower()
        if v not in CLAIM_TYPES:
            raise ValueError(f'claim_type debe ser uno de {CLAIM_TYPES}')
        return v

    @field_validator('topic')
    @classmethod
    def _topic(cls, v):
        v = str(v).strip().lower()
        if v not in TOPICS:
            raise ValueError(f'topic debe ser uno de {TOPICS}')
        return v

    @field_validator('stance')
    @classmethod
    def _stance(cls, v):
        v = str(v).strip().lower()
        if v not in STANCES:
            raise ValueError(f'stance debe ser uno de {STANCES}')
        return v

    @field_validator('horizon')
    @classmethod
    def _hz(cls, v):
        v = str(v).strip().upper()
        if v not in HORIZONS:
            raise ValueError(f'horizon debe ser uno de {HORIZONS}')
        return v

    @field_validator('evidence_refs', 'counter_evidence_refs')
    @classmethod
    def _refs(cls, v):
        return [str(x).strip().upper() for x in v if str(x).strip()]


class AgentResearchResult(BaseModel):
    summary_es: str = Field(min_length=10, max_length=1200)
    summary_en: str = Field(min_length=10, max_length=1200)
    claims: List[ClaimOut] = Field(default_factory=list, max_length=8)
    unresolved_questions: List[str] = Field(default_factory=list, max_length=8)


def check_refs(result, valid_refs):
    """Reglas que dependen del contexto (no expresables en el tipo): cada ref
    citada debe existir en el paquete; una misma ref no puede ser a la vez a
    favor y en contra de la misma claim. Devuelve lista de errores (vacía=ok)."""
    valid = {r.upper() for r in valid_refs}
    errs = []
    for i, c in enumerate(result.claims):
        bad = [r for r in c.evidence_refs + c.counter_evidence_refs if r not in valid]
        if bad:
            errs.append(f'claim[{i}] cita evidencia inexistente: {bad} (válidas: {sorted(valid)})')
        both = set(c.evidence_refs) & set(c.counter_evidence_refs)
        if both:
            errs.append(f'claim[{i}] usa {sorted(both)} a favor Y en contra')
    return errs


def json_schema_hint():
    """Esquema compacto para el prompt (lo que el modelo debe devolver)."""
    return {
        'summary_es': 'str', 'summary_en': 'str',
        'claims': [{
            'predicate': 'UPPER_SNAKE, p.ej. REVENUE_GROWTH_REMAINS_STRONG',
            'object': 'str|null (complemento corto)',
            'claim_type': '|'.join(CLAIM_TYPES), 'topic': '|'.join(TOPICS),
            'stance': '|'.join(STANCES), 'horizon': '|'.join(HORIZONS),
            'statement_es': 'una frase clara para un inversionista no experto',
            'statement_en': 'the same in English',
            'reasoning_summary': 'por qué, citando los E# (sin razonamiento privado extenso)',
            'agent_certainty': '0..1', 'evidence_refs': ['E1'], 'counter_evidence_refs': ['E3'],
            'affected_entities': ['ids de entidad del contexto'],
            'falsifiers': ['qué dato futuro demostraría que es incorrecta'],
        }],
        'unresolved_questions': ['str'],
    }
