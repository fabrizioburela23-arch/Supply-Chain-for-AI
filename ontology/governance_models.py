"""ontology/governance_models.py — REGISTRO DE GOBERNANZA (docs/INFRA_OPERATIVA.md §5.1; paso 9 del plan).

Dos tablas que SOLO crecen (core/ledger_ddl les pone `kh_append_only()`):

  gov_artifacts  cada versión de un artefacto (parámetros del kernel, fórmula NRS, políticas, formas SHACL…):
                 su identidad es sha256 del JSON canónico del cuerpo (`core.decisions.canonical`). Registrar un
                 artefacto NO lo pone en vigor.
  gov_releases   un release = {artifact_id: hash}; release_hash = sha256(canónico de ese mapa) — SIN el código
                 (cada deploy pediría aprobación; el code_sha se anota aparte en cada decisión). El vigente es el
                 de mayor effective_from ≤ now(). `ratified=false` solo para el bootstrap (1.0.0 con los valores
                 de hoy); la ratificación con PIN es una DECISIÓN `governance.ratify` (nunca un UPDATE): el estado
                 "ratificado/propuesto/validado" se DERIVA de las decisiones governance.*.

Nunca IA. Nunca UPDATE/DELETE. Las escribe solo core/governance.py.
"""
from sqlalchemy import CHAR, Boolean, CheckConstraint, Column, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ontology.sqltypes import XID8, txid_default
from ontology.models import Base

_NOW = text('clock_timestamp()')
CHANGE_KINDS = ('initial', 'patch', 'minor', 'major')


class GovArtifact(Base):
    __tablename__ = 'gov_artifacts'
    hash = Column(CHAR(64), primary_key=True)
    artifact_id = Column(String(48), nullable=False)
    semver = Column(String(16), nullable=False)
    change_kind = Column(String(8), nullable=False)
    parent_hash = Column(CHAR(64), nullable=True)
    body = Column(JSONB, nullable=False)
    changelog_es = Column(Text, nullable=False)
    changelog_en = Column(Text, nullable=False)
    proposed_by = Column(String(96), nullable=False)
    proposal_decision_id = Column(UUID(as_uuid=True), nullable=False)
    txid = Column(XID8(), nullable=False, server_default=txid_default())
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=_NOW)
    __table_args__ = (
        CheckConstraint("change_kind IN ('initial', 'patch', 'minor', 'major')", name='ck_gov_change_kind'),
        Index('ux_gov_artifact_semver', 'artifact_id', 'semver', unique=True),
    )


class GovRelease(Base):
    __tablename__ = 'gov_releases'
    release_hash = Column(CHAR(64), primary_key=True)
    semver = Column(String(16), nullable=False)
    artifacts = Column(JSONB, nullable=False)                 # {artifact_id: {hash, semver}}
    effective_from = Column(DateTime(timezone=True), nullable=False)
    approval_decision_id = Column(UUID(as_uuid=True), nullable=False)
    validation_blob = Column(CHAR(64), nullable=True)
    ratified = Column(Boolean, nullable=False, server_default=text('true'))
    note_es = Column(Text, nullable=True)
    note_en = Column(Text, nullable=True)
    txid = Column(XID8(), nullable=False, server_default=txid_default())
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=_NOW)
    __table_args__ = (Index('ix_gov_release_effective', text('effective_from DESC')),)


GOV_TABLES = ('gov_artifacts', 'gov_releases')
