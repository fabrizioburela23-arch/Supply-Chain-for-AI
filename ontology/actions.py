"""ontology/actions.py — Fase 2 del roadmap: Acciones, el ADN de "escritura
auditada" de Palantir. El usuario deja de solo mirar: registra tesis,
anotaciones, correcciones y decisiones que se vuelven parte de la ontología,
con autor, fecha y razonamiento — nunca un UPDATE silencioso.

Cada Acción:
  1. Se valida con un esquema Pydantic (equivalente a Zod del roadmap original).
  2. Ejecuta su efecto de dominio con eventos normales (ObjectCreated/Updated,
     LinkCreated/Removed) vía ontology.service.apply_event().
  3. SIEMPRE deja además un evento `ActionExecuted` — el rastro auditable que
     alimenta el panel "📋 Registro" (timeline filtrable por autor/tipo/objeto).

No reemplaza POST /api/ontology/events (Fase 1, escritura de bajo nivel para
pipelines internos) — lo complementa como el camino recomendado y seguro
para escritura HUMANA, con validación por tipo y trazabilidad automática.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from ontology.models import Event, ObjectRecord, LinkRecord
from ontology.service import apply_event, OntologyError, _utcnow


class ActionError(ValueError):
    pass


# ── Esquemas de entrada (uno por Acción del catálogo) ────────────────────────

class CrearTesisInput(BaseModel):
    company_id: str
    stance: str = Field(pattern='^(long|short|watch|avoid)$')
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=4000)


class AnotarObjetoInput(BaseModel):
    object_id: str
    texto: str = Field(min_length=1, max_length=2000)


class MarcarRiesgoInput(BaseModel):
    company_id: str
    nivel: int = Field(ge=0, le=100)
    razon: str = Field(min_length=1, max_length=1000)


class ProponerVinculoInput(BaseModel):
    from_id: str
    to_id: str
    tipo: str = Field(min_length=1, max_length=40)
    metadata: dict = Field(default_factory=dict)
    fuente: str = Field(min_length=1, max_length=200)


class ResolverVinculoInput(BaseModel):
    link_id: str


class RegistrarDecisionInput(BaseModel):
    decision: str = Field(min_length=1, max_length=2000)
    company_id: Optional[str] = None
    contexto: dict = Field(default_factory=dict)  # ej. {'origin':'stress_test','affected_count':12}


class AjustarPosicionInput(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    delta: float
    razon: str = Field(min_length=1, max_length=1000)
    decision_id: Optional[str] = None


class CorregirDatoInput(BaseModel):
    object_id: str
    campo: str = Field(min_length=1, max_length=100)
    valor_nuevo: object
    fuente: str = Field(min_length=1, max_length=200)


class IncorporarEmpresaInput(BaseModel):
    """Alta de una empresa nueva detectada en vivo (Radar). Reversible con
    RetirarEmpresa; todo queda como eventos inmutables."""
    company_id: str = Field(min_length=2, max_length=80)
    label: str = Field(min_length=2, max_length=120)
    cat: str = Field(default='aisoft', max_length=40)
    country: str = Field(default='', max_length=40)
    role: str = Field(default='', max_length=500)
    link_to: Optional[str] = None          # nodo existente con el que se relaciona
    rel_type: str = Field(default='partner', max_length=20)
    link_rel: str = Field(default='', max_length=300)
    razon: str = Field(min_length=1, max_length=1000)
    fuente: str = Field(default='radar', max_length=200)


class RetirarEmpresaInput(BaseModel):
    """Baja lógica (reversible): marca retired=true; el objeto y su historia
    quedan intactos en la ontología."""
    company_id: str
    razon: str = Field(min_length=1, max_length=1000)
    restaurar: bool = False                # true = deshacer el retiro


# ── Handlers: reciben (session, input_validado, actor) → dict de resultado ──

def _log_action(session, action_type, object_id, target_id, payload, actor, source='manual'):
    """Evento ActionExecuted — el rastro auditable, siempre presente."""
    return apply_event(
        session, 'ActionExecuted', payload={'action': action_type, **payload},
        valid_from=_utcnow(), source=source, actor=actor,
        object_id=object_id, target_id=target_id,
    )


def _require_object(session, object_id):
    obj = session.get(ObjectRecord, object_id)
    if not obj:
        raise ActionError(f'objeto no encontrado: {object_id}')
    return obj


def crear_tesis(session, inp: CrearTesisInput, actor):
    _require_object(session, inp.company_id)
    thesis_id = f'thesis_{uuid.uuid4().hex[:12]}'
    apply_event(session, 'ObjectCreated', {
        'label': f'Tesis de {actor} sobre {inp.company_id}', 'type': 'Thesis',
        'properties': {'company_id': inp.company_id, 'stance': inp.stance,
                        'confidence': inp.confidence, 'rationale': inp.rationale, 'author': actor},
    }, valid_from=_utcnow(), source='manual', actor=actor, object_id=thesis_id)
    apply_event(session, 'LinkCreated', {'rel_type': 'about', 'properties': {}},
                valid_from=_utcnow(), source='manual', actor=actor,
                object_id=thesis_id, target_id=inp.company_id)
    _log_action(session, 'CrearTesis', inp.company_id, thesis_id,
                {'stance': inp.stance, 'confidence': inp.confidence}, actor)
    return {'thesis_id': thesis_id}


def anotar_objeto(session, inp: AnotarObjetoInput, actor):
    _require_object(session, inp.object_id)
    ann_id = f'ann_{uuid.uuid4().hex[:12]}'
    apply_event(session, 'ObjectCreated', {
        'label': f'Nota de {actor}', 'type': 'Annotation',
        'properties': {'target_object_id': inp.object_id, 'texto': inp.texto, 'author': actor},
    }, valid_from=_utcnow(), source='manual', actor=actor, object_id=ann_id)
    apply_event(session, 'LinkCreated', {'rel_type': 'about', 'properties': {}},
                valid_from=_utcnow(), source='manual', actor=actor,
                object_id=ann_id, target_id=inp.object_id)
    _log_action(session, 'AnotarObjeto', inp.object_id, ann_id, {'texto': inp.texto[:200]}, actor)
    return {'annotation_id': ann_id}


def marcar_riesgo(session, inp: MarcarRiesgoInput, actor):
    _require_object(session, inp.company_id)
    apply_event(session, 'ObjectUpdated', {
        'properties': {'nrs_override': inp.nivel, 'nrs_override_reason': inp.razon,
                        'nrs_override_by': actor},
    }, valid_from=_utcnow(), source='manual', actor=actor, object_id=inp.company_id)
    _log_action(session, 'MarcarRiesgo', inp.company_id, None,
                {'nivel': inp.nivel, 'razon': inp.razon}, actor)
    return {'company_id': inp.company_id, 'nivel': inp.nivel}


def proponer_vinculo(session, inp: ProponerVinculoInput, actor):
    _require_object(session, inp.from_id)
    _require_object(session, inp.to_id)
    ev = apply_event(session, 'LinkCreated', {
        'rel_type': inp.tipo, 'properties': {**inp.metadata, 'status': 'proposed',
                                              'proposed_by': actor, 'proposed_source': inp.fuente},
    }, valid_from=_utcnow(), source='manual', actor=actor, object_id=inp.from_id, target_id=inp.to_id)
    # el id del LinkRecord recién creado: lo buscamos por ser el más reciente para este par
    link = session.scalars(
        select(LinkRecord).where(
            LinkRecord.source_id == inp.from_id, LinkRecord.target_id == inp.to_id,
            LinkRecord.rel_type == inp.tipo, LinkRecord.valid_to.is_(None),
        ).order_by(LinkRecord.valid_from.desc())
    ).first()
    link_id = str(link.id) if link else None
    _log_action(session, 'ProponerVinculo', inp.from_id, inp.to_id,
                {'tipo': inp.tipo, 'link_id': link_id, 'fuente': inp.fuente}, actor)
    return {'link_id': link_id, 'status': 'proposed'}


def _resolver_vinculo(session, inp: ResolverVinculoInput, actor, resolution):
    try:
        link_uuid = uuid.UUID(inp.link_id)
    except ValueError:
        raise ActionError(f'link_id inválido: {inp.link_id}')
    link = session.get(LinkRecord, link_uuid)
    if not link:
        raise ActionError(f'vínculo no encontrado: {inp.link_id}')
    props = dict(link.properties or {})
    props['status'] = resolution
    props[f'{resolution}_by'] = actor
    link.properties = props
    if resolution == 'rejected':
        # El cierre va como EVENTO (no mutación directa): sin LinkRemoved en el
        # log, el replay as_of mostraba los vínculos rechazados como vigentes
        # para siempre. apply_event materializa el valid_to por nosotros.
        apply_event(session, 'LinkRemoved', {
            'rel_type': link.rel_type,
            'properties': {'reason': 'rejected', 'rejected_by': actor,
                           'link_id': inp.link_id},
        }, valid_from=_utcnow(), source='manual', actor=actor,
            object_id=link.source_id, target_id=link.target_id)
    _log_action(session, 'ConfirmarVinculo' if resolution == 'confirmed' else 'RechazarVinculo',
                link.source_id, link.target_id, {'link_id': inp.link_id, 'resolution': resolution}, actor)
    return {'link_id': inp.link_id, 'status': resolution}


def confirmar_vinculo(session, inp: ResolverVinculoInput, actor):
    return _resolver_vinculo(session, inp, actor, 'confirmed')


def rechazar_vinculo(session, inp: ResolverVinculoInput, actor):
    return _resolver_vinculo(session, inp, actor, 'rejected')


def registrar_decision(session, inp: RegistrarDecisionInput, actor):
    if inp.company_id:
        _require_object(session, inp.company_id)
    decision_id = f'decision_{uuid.uuid4().hex[:12]}'
    apply_event(session, 'ObjectCreated', {
        'label': f'Decisión de {actor}', 'type': 'Decision',
        'properties': {'decision': inp.decision, 'contexto': inp.contexto,
                        'company_id': inp.company_id, 'author': actor},
    }, valid_from=_utcnow(), source='manual', actor=actor, object_id=decision_id)
    if inp.company_id:
        apply_event(session, 'LinkCreated', {'rel_type': 'about', 'properties': {}},
                    valid_from=_utcnow(), source='manual', actor=actor,
                    object_id=decision_id, target_id=inp.company_id)
    _log_action(session, 'RegistrarDecision', inp.company_id, decision_id,
                {'decision': inp.decision[:200], 'contexto': inp.contexto}, actor)
    return {'decision_id': decision_id}


def ajustar_posicion(session, inp: AjustarPosicionInput, actor):
    # resuelve la empresa por ticker (properties.mkt) para poder vincular la ficha
    company = session.scalars(
        select(ObjectRecord).where(ObjectRecord.type == 'Company')
    ).all()
    match = next((c for c in company if (c.properties or {}).get('mkt') == inp.ticker), None)
    if inp.decision_id:
        _require_object(session, inp.decision_id)
    adj_id = f'posadj_{uuid.uuid4().hex[:12]}'
    apply_event(session, 'ObjectCreated', {
        'label': f'Ajuste de posición {inp.ticker}', 'type': 'PositionAdjustment',
        'properties': {'ticker': inp.ticker, 'delta': inp.delta, 'razon': inp.razon,
                        'decision_id': inp.decision_id, 'author': actor,
                        'company_id': match.id if match else None},
    }, valid_from=_utcnow(), source='manual', actor=actor, object_id=adj_id)
    if match:
        apply_event(session, 'LinkCreated', {'rel_type': 'about', 'properties': {}},
                    valid_from=_utcnow(), source='manual', actor=actor,
                    object_id=adj_id, target_id=match.id)
    if inp.decision_id:
        apply_event(session, 'LinkCreated', {'rel_type': 'justified_by', 'properties': {}},
                    valid_from=_utcnow(), source='manual', actor=actor,
                    object_id=adj_id, target_id=inp.decision_id)
    _log_action(session, 'AjustarPosicion', match.id if match else None, inp.decision_id,
                {'ticker': inp.ticker, 'delta': inp.delta, 'razon': inp.razon}, actor)
    return {'adjustment_id': adj_id, 'company_id': match.id if match else None}


def corregir_dato(session, inp: CorregirDatoInput, actor):
    obj = _require_object(session, inp.object_id)
    valor_anterior = (obj.properties or {}).get(inp.campo)
    apply_event(session, 'ObjectUpdated', {
        'properties': {inp.campo: inp.valor_nuevo},
    }, valid_from=_utcnow(), source='correction', actor=actor, object_id=inp.object_id)
    _log_action(session, 'CorregirDato', inp.object_id, None, {
        'campo': inp.campo, 'valor_anterior': valor_anterior, 'valor_nuevo': inp.valor_nuevo,
        'fuente': inp.fuente,
    }, actor, source='correction')
    return {'object_id': inp.object_id, 'campo': inp.campo,
            'valor_anterior': valor_anterior, 'valor_nuevo': inp.valor_nuevo}


def incorporar_empresa(session, inp: IncorporarEmpresaInput, actor):
    """Alta viva de empresa (Radar/humano). Crea el objeto + link opcional al
    grafo. Falla si el id ya existe (usar CorregirDato para actualizar)."""
    if session.get(ObjectRecord, inp.company_id):
        raise ActionError(f'la empresa ya existe: {inp.company_id}')
    props = {k: v for k, v in {'cat': inp.cat, 'country': inp.country,
                               'role': inp.role, 'added_live': True}.items() if v}
    apply_event(session, 'ObjectCreated',
                {'label': inp.label, 'type': 'Company', 'properties': props},
                valid_from=_utcnow(), source=inp.fuente, actor=actor,
                object_id=inp.company_id)
    link = None
    if inp.link_to:
        if not session.get(ObjectRecord, inp.link_to):
            raise ActionError(f'link_to no existe: {inp.link_to}')
        apply_event(session, 'LinkCreated',
                    {'rel_type': inp.rel_type or 'partner', 'weight': 1,
                     'properties': {'rel_label': inp.link_rel or inp.razon[:120],
                                    'proposed': True}},
                    valid_from=_utcnow(), source=inp.fuente, actor=actor,
                    object_id=inp.company_id, target_id=inp.link_to)
        link = {'from': inp.company_id, 'to': inp.link_to, 'rel_type': inp.rel_type}
    _log_action(session, 'IncorporarEmpresa', inp.company_id, inp.link_to, {
        'label': inp.label, 'cat': inp.cat, 'razon': inp.razon, 'fuente': inp.fuente,
    }, actor, source=inp.fuente)
    return {'company_id': inp.company_id, 'label': inp.label, 'link': link}


def retirar_empresa(session, inp: RetirarEmpresaInput, actor):
    """Baja lógica reversible: properties.retired = true/false. La historia
    completa queda en events — nada se borra jamás."""
    obj = _require_object(session, inp.company_id)
    retired = not inp.restaurar
    apply_event(session, 'ObjectUpdated',
                {'properties': {'retired': retired, 'retired_razon': inp.razon}},
                valid_from=_utcnow(), source='radar', actor=actor,
                object_id=inp.company_id)
    _log_action(session, 'RetirarEmpresa', inp.company_id, None, {
        'razon': inp.razon, 'restaurar': inp.restaurar,
    }, actor, source='radar')
    return {'company_id': inp.company_id, 'retired': retired}


# ── Catálogo: nombre → (esquema Pydantic, handler) ───────────────────────────
ACTION_CATALOG = {
    'CrearTesis':        (CrearTesisInput, crear_tesis),
    'AnotarObjeto':       (AnotarObjetoInput, anotar_objeto),
    'MarcarRiesgo':       (MarcarRiesgoInput, marcar_riesgo),
    'ProponerVinculo':    (ProponerVinculoInput, proponer_vinculo),
    'ConfirmarVinculo':   (ResolverVinculoInput, confirmar_vinculo),
    'RechazarVinculo':    (ResolverVinculoInput, rechazar_vinculo),
    'RegistrarDecision':  (RegistrarDecisionInput, registrar_decision),
    'AjustarPosicion':    (AjustarPosicionInput, ajustar_posicion),
    'CorregirDato':       (CorregirDatoInput, corregir_dato),
    'IncorporarEmpresa':  (IncorporarEmpresaInput, incorporar_empresa),
    'RetirarEmpresa':     (RetirarEmpresaInput, retirar_empresa),
}


def execute_action(session, action_type, payload, actor):
    """Punto de entrada único: valida con el esquema del catálogo y ejecuta.
    Lanza ActionError/ValidationError si algo no es válido — nunca escribe a
    medias (el caller hace rollback si esto lanza, vía session_scope)."""
    entry = ACTION_CATALOG.get(action_type)
    if not entry:
        raise ActionError(f'Acción desconocida: {action_type}. Catálogo: {", ".join(ACTION_CATALOG)}')
    schema, handler = entry
    try:
        validated = schema(**(payload or {}))
    except ValidationError as e:
        raise ActionError(f'Entrada inválida para {action_type}: {e.errors()}')
    if not actor or not str(actor).strip():
        raise ActionError('actor es requerido — toda Acción queda atribuida a alguien')
    return handler(session, validated, actor)


def list_actions(session, actor=None, action_type=None, object_id=None, limit=100):
    """Para el panel '📋 Registro': timeline de ActionExecuted, filtrable."""
    q = select(Event).where(Event.event_type == 'ActionExecuted')
    if actor:
        q = q.where(Event.actor == actor)
    if action_type:
        q = q.where(Event.payload['action'].astext == action_type)
    if object_id:
        from sqlalchemy import or_
        q = q.where(or_(Event.object_id == object_id, Event.target_id == object_id))
    q = q.order_by(Event.recorded_at.desc()).limit(min(limit, 500))
    return session.scalars(q).all()
