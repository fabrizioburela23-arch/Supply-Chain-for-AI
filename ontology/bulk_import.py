"""ontology/bulk_import.py — ingesta masiva idempotente y validada (Wikidata/GLEIF).

La capa ANCHA del grafo (decenas de miles de nodos) vendrá de fuentes externas.
Este módulo implementa las reglas de escala del spec
(spec_matrices_dispersas_centralidad §"Ponderación de datos importados en bulto"
y §"Estabilidad estructural a escala") ANTES de que exista el conector concreto,
para que cualquier importación futura siga la misma regla:

- PROCEDENCIA: cada link importado se marca con properties.source (p.ej.
  'wikidata'/'gleif'). El motor de matrices (matrix.engine._eff_weight) le aplica
  UN descuento de peso (IMPORT_BULK_WEIGHT_FACTOR, default 0.5) en la LECTURA —
  aquí se guarda el peso NOMINAL sin descontar para no descontar dos veces.
- INTEGRIDAD: se pone en CUARENTENA (no se descarta en silencio) todo registro
  cuyo source/target no exista como objeto, o cuyo rel_type no sea canónico.
- IDEMPOTENCIA: re-correr no duplica. Identidad estable por `external_id` (o por
  (source,target,rel_type)); si ya hay un link vigente igual, se OMITE.
- POR LOTES: se procesa en lotes (batch_size), validando e informando por lote,
  no en una sola carga masiva — un error se aísla temprano.

La función `validate_bulk_links` es PURA (sin DB) → totalmente testeable en
tests/test_bulk_import.py. `import_links_bulk` es la envoltura fina que aplica
los aceptados vía apply_event (auditado, append-only, con time-travel intacto).
"""
from matrix.engine import REL_TYPES

# Peso NOMINAL por defecto de un link importado cuando la fuente no trae uno.
# El descuento de bulto se aplica aparte en la lectura (no aquí) — así el peso
# efectivo es inferior al de una relación curada, pero queda DEFINIDO (no None).
BULK_DEFAULT_WEIGHT = 1.0


def validate_bulk_links(records, existing_ids, valid_rel_types=None):
    """PURA (sin DB). Valida y normaliza registros de links importados.

    records: iterable de dicts con al menos {source, target, rel_type}; opcional
    {weight, external_id, properties}. existing_ids: set de ids de objetos que
    YA existen. valid_rel_types: tipos canónicos permitidos (default REL_TYPES).

    Devuelve (accepted, quarantined):
    - accepted: dicts normalizados listos para aplicar (source, target, rel_type,
      weight, external_id, properties).
    - quarantined: [{record, reason}] — NUNCA se descarta en silencio.
    """
    valid_rel_types = set(valid_rel_types or REL_TYPES)
    existing_ids = existing_ids if isinstance(existing_ids, (set, frozenset)) else set(existing_ids)
    accepted, quarantined = [], []
    for rec in records:
        if not isinstance(rec, dict):
            quarantined.append({'record': rec, 'reason': 'registro no es un objeto'})
            continue
        src = rec.get('source') or rec.get('source_id')
        tgt = rec.get('target') or rec.get('target_id')
        rel = rec.get('rel_type') or rec.get('rel')
        if not src or not tgt:
            quarantined.append({'record': rec, 'reason': 'falta source o target'})
            continue
        if src == tgt:
            quarantined.append({'record': rec, 'reason': 'auto-vínculo (source == target)'})
            continue
        if rel not in valid_rel_types:
            quarantined.append({'record': rec, 'reason': f'rel_type no canónico: {rel!r}'})
            continue
        if src not in existing_ids:
            quarantined.append({'record': rec, 'reason': f'source inexistente: {src!r}'})
            continue
        if tgt not in existing_ids:
            quarantined.append({'record': rec, 'reason': f'target inexistente: {tgt!r}'})
            continue
        try:
            weight = float(rec['weight']) if rec.get('weight') is not None else BULK_DEFAULT_WEIGHT
        except (TypeError, ValueError):
            quarantined.append({'record': rec, 'reason': f'weight no numérico: {rec.get("weight")!r}'})
            continue
        accepted.append({
            'source': src, 'target': tgt, 'rel_type': rel, 'weight': weight,
            'external_id': rec.get('external_id'),
            'properties': dict(rec.get('properties') or {}),
        })
    return accepted, quarantined


def _idempotency_key(rec, provenance):
    """Clave de identidad estable para deduplicar entre corridas."""
    if rec.get('external_id'):
        return ('ext', provenance, str(rec['external_id']))
    return ('triple', rec['source'], rec['target'], rec['rel_type'])


def import_links_bulk(session, records, provenance, batch_size=1000,
                      valid_from=None, actor='bulk_import'):
    """Aplica links importados de forma VALIDADA, IDEMPOTENTE y POR LOTES.

    provenance: 'wikidata' | 'gleif' | … → se guarda en Event.source Y en
    LinkRecord.properties.source (esto último lo lee el motor para descontar el
    peso). Devuelve un resumen {created, skipped, quarantined, batches, ...}.

    Idempotencia: se omite un registro si ya existe un link VIGENTE con la misma
    clave (external_id o triple source/target/rel_type + misma procedencia).
    """
    from datetime import datetime, timezone

    from sqlalchemy import select

    from ontology.models import LinkRecord, ObjectRecord

    valid_from = valid_from or datetime.now(timezone.utc).isoformat()
    existing_ids = {r for (r,) in session.execute(select(ObjectRecord.id)).all()}
    accepted, quarantined = validate_bulk_links(records, existing_ids)

    # índice de idempotencia: links vigentes ya importados con esta procedencia
    seen = set()
    for l in session.scalars(select(LinkRecord).where(LinkRecord.valid_to.is_(None))).all():
        props = l.properties or {}
        if props.get('source') == provenance:
            if props.get('external_id'):
                seen.add(('ext', provenance, str(props['external_id'])))
            seen.add(('triple', l.source_id, l.target_id, l.rel_type))

    created, skipped, batches = 0, 0, 0
    batch = []
    for rec in accepted:
        key = _idempotency_key(rec, provenance)
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        seen.add(('triple', rec['source'], rec['target'], rec['rel_type']))
        batch.append(rec)
        if len(batch) >= batch_size:
            created += _flush_batch(session, batch, provenance, valid_from, actor)
            batches += 1
            batch = []
    if batch:
        created += _flush_batch(session, batch, provenance, valid_from, actor)
        batches += 1

    return {'input': len(accepted) + len(quarantined), 'created': created,
            'skipped_duplicates': skipped, 'quarantined': quarantined,
            'quarantined_count': len(quarantined), 'batches': batches,
            'provenance': provenance}


def _flush_batch(session, batch, provenance, valid_from, actor):
    from ontology.service import apply_event
    n = 0
    for rec in batch:
        props = dict(rec['properties'])
        props['source'] = provenance          # ← el motor lo lee para descontar el peso
        if rec.get('external_id'):
            props['external_id'] = str(rec['external_id'])
        apply_event(session, 'LinkCreated', {
            'rel_type': rec['rel_type'], 'weight': rec['weight'], 'properties': props,
        }, valid_from=valid_from, source=provenance, actor=actor,
            object_id=rec['source'], target_id=rec['target'])
        n += 1
    session.flush()   # aísla errores por lote sin cerrar la transacción entera
    return n
