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
        props = dict(rec.get('properties') or {})
        accepted.append({
            'source': src, 'target': tgt, 'rel_type': rel, 'weight': weight,
            'external_id': rec.get('external_id'),
            'properties': props,
            'evidenced_by': evidence_ids(rec, props),
        })
    return accepted, quarantined


def evidence_ids(rec, props=None):
    """Fuentes (`Source`, ontology/provenance.py) que el registro CITA: `evidenced_by` (lista o texto) y/o
    `source_id`, en el registro o en sus `properties`. Sin duplicados, en orden. La confiabilidad (trust) nunca la
    declara el registro: se lee del objeto Source (como en G1). Ojo: un registro SIN `source` usa `source_id` como
    extremo de origen (validate_bulk_links): ahí no es una fuente citada."""
    props = rec.get('properties') if props is None else props
    out = []
    for d in (rec, props or {}):
        if not isinstance(d, dict):
            continue
        for key in ('evidenced_by', 'source_id'):
            if d is rec and key == 'source_id' and not rec.get('source'):
                continue          # sin `source`, el `source_id` del registro es el EXTREMO de origen (validate), no una fuente
            v = d.get(key)
            for sid in (v if isinstance(v, (list, tuple)) else [v]):
                if isinstance(sid, str) and sid.strip() and sid.strip() not in out:
                    out.append(sid.strip())
    return out


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

    # G5 (revisión): si esta FUENTE ya afirmó la tripla (aunque se haya
    # deduplicado contra una fila de otra fuente), no se vuelve a escribir: antes
    # cada re-ejecución añadía un evento no-op y 'created' lo contaba. La PRIMERA
    # afirmación sí se registra (dedup_of): si luego se deshace la fila gemela,
    # el hecho independiente de esta fuente no se pierde.
    from ontology.models import Event
    for e in session.scalars(select(Event).where(
            Event.event_type == 'LinkCreated', Event.source == provenance,
            Event.payload['properties']['dedup_of'].astext.isnot(None))).all():
        p = e.payload or {}
        seen.add(('triple', e.object_id, e.target_id, p.get('rel_type') or 'supply'))
        ext = (p.get('properties') or {}).get('external_id')
        if ext:
            seen.add(('ext', provenance, str(ext)))

    # D-2/D-3: contexto del lote en pocas consultas; la fuente PRINCIPAL de cada vínculo (la citada con más trust)
    # es la que la puerta acredita Y la que se escribe en el evento (source_id) — antes la puerta acreditaba fuentes
    # que la escritura tiraba (G1, replay y auditoría no las veían)
    try:
        ctx = _bulk_context(session, accepted)
    except Exception:  # noqa: BLE001 — sin contexto la puerta corre igual (sin fuentes acreditadas)
        ctx = None
    _mark_primary_source(accepted, ctx[1] if ctx else {})
    # INFRA_OPERATIVA paso 10 (G-BULK, SOMBRA): el lote aceptado contra las formas de vínculo en UNA pasada
    # compilada (17 ms / 1.000 vínculos frente a 204 s de pySHACL); G1 no se repite vínculo por vínculo.
    gate = _gate_bulk(session, accepted, existing_ids, valid_from, ctx)
    session.info['kh_gate_skip_g1'] = True
    try:
        created, skipped, batches = _apply_accepted(session, accepted, seen, provenance, valid_from, actor,
                                                    batch_size)
    finally:
        session.info.pop('kh_gate_skip_g1', None)
    return {'gate': gate, 'input': len(accepted) + len(quarantined), 'created': created,
            'skipped_duplicates': skipped, 'quarantined': quarantined,
            'quarantined_count': len(quarantined), 'batches': batches,
            'provenance': provenance}


def _apply_accepted(session, accepted, seen, provenance, valid_from, actor, batch_size):
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
    return created, skipped, batches


def _chunks(xs, n=500):
    xs = list(xs)
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def _bulk_context(session, accepted):
    """Lo que las formas de vínculo leen además del vínculo (D-2, EXPANSION_5K E1.8) — el MISMO contenido que
    core/gates/focus.gather_link arma para G1, en pocas consultas para todo el lote:
      · extremos: {id: {type, live}} (live = existe y no está retirado);
      · fuentes citadas: {source_id: trust} (del objeto Source; sin objeto o sin trust = no cuenta como confiable);
      · inversos vigentes: {(source, target, rel): [{id, source, target, rel, live}]} — los de la base (valid_to
        nulo; live = no rechazado, como G1) y los del PROPIO lote (estado resultante del lote: si trae A→B y B→A
        del mismo tipo, los dos quedan marcados)."""
    from sqlalchemy import select, tuple_

    from ontology.models import LinkRecord, ObjectRecord
    ends = {}
    ids = {x for r in accepted for x in (r['source'], r['target'])}
    for part in _chunks(sorted(ids)):
        for oid, otype, props in session.execute(select(ObjectRecord.id, ObjectRecord.type, ObjectRecord.properties)
                                                 .where(ObjectRecord.id.in_(part))).all():
            ends[oid] = {'type': otype, 'live': not (props or {}).get('retired')}
    sources = {}
    sids = {sid for r in accepted for sid in r.get('evidenced_by') or ()}
    for part in _chunks(sorted(sids)):
        for oid, props in session.execute(select(ObjectRecord.id, ObjectRecord.properties)
                                          .where(ObjectRecord.id.in_(part))).all():
            tr = (props or {}).get('trust')
            if tr is not None:
                sources[oid] = tr
    inv = {}
    rev = {(r['target'], r['source']) for r in accepted}
    vivos = set()
    for part in _chunks(sorted(rev)):
        for l in session.scalars(select(LinkRecord).where(tuple_(LinkRecord.source_id, LinkRecord.target_id).in_(part),
                                                          LinkRecord.valid_to.is_(None))).all():
            key = (l.source_id, l.target_id, l.rel_type)
            vivos.add(key)
            inv.setdefault(key, []).append({'id': str(l.id), 'source': l.source_id, 'target': l.target_id,
                                            'rel': l.rel_type,
                                            'live': (l.properties or {}).get('status') != 'rejected'})
    lote = {}
    for n, r in enumerate(accepted):
        key = (r['source'], r['target'], r['rel_type'])
        if key not in vivos and key not in lote and (r['source'], r['target']) in rev:   # su inverso está en el lote
            lote[key] = {'id': f"bulk:{r.get('external_id') or n}", 'source': r['source'], 'target': r['target'],
                         'rel': r['rel_type'], 'live': True}
    for key, ref in lote.items():
        inv.setdefault(key, []).append(ref)
    return ends, sources, inv


def _trust_num(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _mark_primary_source(accepted, sources):
    """rec['source_id'] = la fuente citada con MÁS trust (empate → la primera citada; ninguna con trust → la
    primera). Es la que se escribe en el evento (como G1, que acredita solo el source_id del evento)."""
    for rec in accepted:
        ev = list(rec.get('evidenced_by') or ())
        best, best_t = (ev[0] if ev else None), None
        for sid in ev:
            t = _trust_num(sources.get(sid))
            if t is not None and (best_t is None or t > best_t):
                best, best_t = sid, t
        rec['source_id'] = best


def _gate_bulk(session, accepted, existing_ids, valid_from, ctx=None):
    """G-BULK: un reporte para todo el lote (resumen en la respuesta; detalle en el libro). En sombra nunca lanza; con
    policy.gates@2.0.0 (bloqueo) un lote con una regla 'block' se rechaza ENTERO (GateViolation, antes de escribir).
    D-2: cada vínculo lleva al foco lo mismo que G1 (focus.gather_link): evidencia con su trust, tipo y vigencia de
    los extremos, inversos vigentes, etiqueta y si es un hecho fechado — sin eso, todo flujo con confianza ≥ 0,5
    salía «sin fuente» y las reglas de País/Política como proveedor, inverso y hecho fechado nunca corrían."""
    try:
        import core.gates as _gates
        from core.gates import focus as _gf
        from core.gates import report as _gr
        triples = []
        foc = None
        lim, flow = _gf._limits(), _gf._flow_rels()
        ends_all, sources_all, inv_all = ctx if ctx is not None else _bulk_context(session, accepted)
        for n, rec in enumerate(accepted):
            props = rec.get('properties') or {}
            ends = {x: ends_all.get(x) or {'type': None, 'live': False} for x in (rec['source'], rec['target'])}
            sid0 = rec.get('source_id') if 'source_id' in rec else (list(rec.get('evidenced_by') or ()) or [None])[0]
            ev_by = [sid0] if sid0 else []     # lo que se ESCRIBE (source_id del evento), igual que G1
            srcs = {sid: sources_all[sid] for sid in ev_by if sid in sources_all}
            inv = inv_all.get((rec['target'], rec['source'], rec['rel_type'])) or ()
            t, f = _gf.link_triples({'id': f"bulk:{rec.get('external_id') or n}", 'source': rec['source'],
                                     'target': rec['target'], 'rel': rec['rel_type'], 'weight': rec['weight'],
                                     'confidence': props.get('confidence'), 'valid_from': valid_from,
                                     'rel_label': props.get('rel_label') or props.get('label'),
                                     'evidenced_by': ev_by,
                                     'dated': bool(props.get('predicate') or props.get('since'))},
                                    ends, inv, srcs, lim, flow)
            triples += t
            foc = foc or f
        rep = _gates.evaluate('ontology.g_bulk', list(dict.fromkeys(triples)), None)
        if rep is None:
            return None
        _gr.record(rep, session=session)
        if _gates.blocks(rep):                 # paso 11 (bloqueo): el lote entero se rechaza (422 con el reporte)
            raise _gates.GateViolation(rep)
        by_rule = _gr.by_rule_of(rep)          # conteo completo (también lo que pasó de MAX_RESULTS)
        return {'mode': rep['mode'], 'outcome': rep['outcome'], 'checked': len(accepted), 'by_rule': by_rule,
                'truncated': rep.get('truncated', 0), 'latency_us': rep.get('latency_us')}
    except Exception as e:  # noqa: BLE001
        if getattr(e, 'code', None) == 'gate_violation':
            raise
        return None


def _flush_batch(session, batch, provenance, valid_from, actor):
    from ontology.service import apply_event
    n = 0
    for rec in batch:
        props = dict(rec['properties'])
        props['source'] = provenance          # ← el motor lo lee para descontar el peso
        if rec.get('external_id'):
            props['external_id'] = str(rec['external_id'])
        ev_by = list(rec.get('evidenced_by') or ())
        if ev_by and not props.get('evidenced_by'):
            props['evidenced_by'] = ev_by     # D-3: las fuentes citadas quedan con el vínculo (auditoría)
        ev = apply_event(session, 'LinkCreated', {
            'rel_type': rec['rel_type'], 'weight': rec['weight'], 'properties': props,
        }, valid_from=valid_from, source=provenance, actor=actor,
            object_id=rec['source'], target_id=rec['target'],
            # D-3: la fuente principal (la que la puerta acreditó) y la confianza declarada van al EVENTO
            source_id=rec.get('source_id') if 'source_id' in rec else (ev_by[0] if ev_by else None),
            confidence=props.get('confidence'))
        if not ((ev.payload or {}).get('properties') or {}).get('dedup_of'):
            n += 1                            # G5: un duplicado de otra fuente no cuenta como creado
    session.flush()   # aísla errores por lote sin cerrar la transacción entera
    return n
