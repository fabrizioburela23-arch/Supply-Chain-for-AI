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
        acc = {
            'source': src, 'target': tgt, 'rel_type': rel, 'weight': weight,
            'external_id': rec.get('external_id'),
            'properties': props,
            'evidenced_by': evidence_ids(rec, props),
        }
        # D-3 (EXPANSION_5K E2.8): la fecha REAL del hecho viaja con el registro (valid_from/valid_to); sin ella el
        # llamador decide (import_links_bulk: la de la corrida). Nunca se inventa aquí.
        for k in ('valid_from', 'valid_to'):
            if rec.get(k) is not None:
                acc[k] = rec[k]
        accepted.append(acc)
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
        }, valid_from=rec.get('valid_from') or valid_from, valid_to=rec.get('valid_to'),   # D-3: fecha del registro
            source=provenance, actor=actor,
            object_id=rec['source'], target_id=rec['target'],
            # D-3: la fuente principal (la que la puerta acreditó) y la confianza declarada van al EVENTO
            source_id=rec.get('source_id') if 'source_id' in rec else (ev_by[0] if ev_by else None),
            confidence=props.get('confidence'))
        if not ((ev.payload or {}).get('properties') or {}).get('dedup_of'):
            n += 1                            # G5: un duplicado de otra fuente no cuenta como creado
    session.flush()   # aísla errores por lote sin cerrar la transacción entera
    return n


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# E2.8 (EXPANSION_5K): escritura POR BLOQUES — los MISMOS eventos que apply_event (campo a campo), con executemany
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# apply_event escribe un evento por viaje (INSERT + materializar + puertas); 21.000 eventos tardaban 144 s. Aquí un
# bloque entra en UNA sentencia executemany (events), otra para objects y otra para links, con lo mismo que
# apply_event deja: tipos del registro, valid_from REAL (el llamador la pone: la de la ficha o GENESIS, nunca
# "ahora"), source_id/confidence del evento, release_hash, recorded_at = clock_timestamp(), dedup G2 de un vínculo
# idéntico ya vigente, versión del grafo (hotviews.mark), efecto en la decisión en curso (note_event) y las puertas
# evaluadas EN BLOQUE antes de escribir (G-BULK para vínculos; G1 de objetos diferida al cierre de la decisión).
# Sigue siendo append-only: nada aquí hace UPDATE/DELETE sobre events.
_FAST_SQL = (
    'INSERT INTO events (id, event_type, object_id, target_id, payload, valid_from, valid_to, recorded_at, source, '
    'actor, source_id, confidence, release_hash) VALUES (CAST(:id AS uuid), :event_type, :object_id, :target_id, '
    'CAST(:payload AS jsonb), :valid_from, :valid_to, clock_timestamp(), :source, :actor, :source_id, :confidence, '
    ':release_hash)')


def _json(v):
    import json
    return json.dumps(v if v is not None else {}, ensure_ascii=False, separators=(',', ':'), default=str)


class _EvRef:
    """Lo que los ganchos (hotviews.mark, decisions.note_event) leen de un evento, sin instanciar el ORM."""
    __slots__ = ('id', 'event_type', 'object_id', 'target_id', 'payload', 'valid_from', 'valid_to', 'source')

    def __init__(self, row):
        self.id = row['id']
        self.event_type = row['event_type']
        self.object_id = row['object_id']
        self.target_id = row['target_id']
        self.payload = row['_payload']
        self.valid_from = row['valid_from']
        self.valid_to = row['valid_to']
        self.source = row['source']


def _preload_objects(session, ids):
    from sqlalchemy import select

    from ontology.models import ObjectRecord
    out = {}
    for part in _chunks(sorted(ids), 500):
        for oid, otype, label, props in session.execute(
                select(ObjectRecord.id, ObjectRecord.type, ObjectRecord.label, ObjectRecord.properties)
                .where(ObjectRecord.id.in_(part))).all():
            out[oid] = {'type': otype, 'label': label, 'props': dict(props or {})}
    return out


def _preload_live_links(session, pairs):
    """{(source, target, rel): [{id, event_id, valid_from, weight}]} vigentes (valid_to IS NULL) de esos pares."""
    from sqlalchemy import select, tuple_

    from ontology.models import LinkRecord
    out = {}
    for part in _chunks(sorted(pairs), 500):
        for l in session.scalars(select(LinkRecord).where(
                tuple_(LinkRecord.source_id, LinkRecord.target_id).in_(part), LinkRecord.valid_to.is_(None))).all():
            out.setdefault((l.source_id, l.target_id, l.rel_type), []).append(
                {'id': l.id, 'event_id': l.event_id, 'valid_from': l.valid_from, 'weight': l.weight})
    return out


def _dedup_twin(twins, valid_from, weight):
    """La MISMA regla que ontology.service._dedup_link_payload: una fila vigente del par/rel con el mismo peso que
    empezó antes o igual ya lo cubre → el nuevo evento es un no-op (dedup_of)."""
    from ontology.service import _same_weight
    for t in sorted(twins, key=lambda x: x['valid_from']):
        if t['valid_from'] <= valid_from and _same_weight(t['weight'], weight):
            return t
    return None


def write_events_fast(session, events, *, source, actor, chunk=1000, gate=True):
    """Escribe `events` en bloques. Cada evento: {event_type, object_id, target_id, payload, valid_from (OBLIGATORIA),
    valid_to, source_id, confidence}. Devuelve {'ids': [uuid…] en el orden de entrada, 'objects_created',
    'objects_updated', 'links_created', 'links_dedup', 'links_closed', 'gate'}.

    Admite ObjectCreated/ObjectUpdated, LinkCreated y LinkRemoved DIRIGIDO (retracts_event_id). Cualquier otro
    evento (LinkRemoved comodín, LinkStatusChanged…) sale por apply_event, uno a uno (mismo resultado, más lento)."""
    import uuid as _uuid

    from sqlalchemy import insert, text

    from ontology.models import LinkRecord, ObjectRecord
    from ontology.service import (VALID_EVENT_TYPES, OntologyError, _parse_dt, _release_hash, _vigilar_vocabulario,
                                  apply_event, _promote_dedup)
    try:
        from core.hotviews import signals as _sig
    except Exception:  # noqa: BLE001
        _sig = None
    try:
        from core import decisions as _dec
    except Exception:  # noqa: BLE001
        _dec = None
    try:
        import core.gates as _gates
    except Exception:  # noqa: BLE001
        _gates = None
    source = (str(source) if source is not None else '')[:60]
    out = {'ids': [], 'objects_created': 0, 'objects_updated': 0, 'links_created': 0, 'links_dedup': 0,
           'links_closed': 0, 'gate': None, 'slow_path': 0}
    rel_hash = _release_hash()
    events = list(events)
    for ev in events:
        if ev.get('event_type') not in VALID_EVENT_TYPES:
            raise OntologyError(f'event_type desconocido: {ev.get("event_type")}')
        if ev.get('valid_from') is None:
            raise OntologyError('write_events_fast: valid_from es obligatoria (la fecha real, nunca "ahora")')
    for block in _chunks(events, chunk):
        _write_block(session, block, source, actor, rel_hash, out, insert, text, LinkRecord, ObjectRecord,
                     _parse_dt, _vigilar_vocabulario, apply_event, _promote_dedup, _sig, _dec, _gates, gate, _uuid)
    return out


def _write_block(session, block, source, actor, rel_hash, out, insert, text, LinkRecord, ObjectRecord, _parse_dt,
                 _vigilar, apply_event, _promote_dedup, _sig, _dec, _gates, gate, _uuid):
    from ontology.models import EventType
    OC, OU, LC, LR = (EventType.OBJECT_CREATED.value, EventType.OBJECT_UPDATED.value, EventType.LINK_CREATED.value,
                      EventType.LINK_REMOVED.value)
    obj_ids = set()
    pairs = set()
    for ev in block:
        if ev['event_type'] in (OC, OU, LC, LR):
            if ev.get('object_id'):
                obj_ids.add(ev['object_id'])
            if ev.get('target_id'):
                obj_ids.add(ev['target_id'])
            if ev['event_type'] == LC:
                pairs.add((ev['object_id'], ev['target_id']))
    objs = _preload_objects(session, obj_ids)
    live = _preload_live_links(session, pairs) if pairs else {}
    rows, obj_new, obj_upd, link_rows, closes, slow = [], {}, [], [], [], []
    confs = {}
    for ev in block:
        et = ev['event_type']
        vf = _parse_dt(ev['valid_from'])
        vt = _parse_dt(ev.get('valid_to'))
        payload = dict(ev.get('payload') or {})
        oid, tid = ev.get('object_id'), ev.get('target_id')
        conf = ev.get('confidence')
        if conf is not None:
            try:
                conf = max(0.0, min(1.0, float(conf)))
            except (TypeError, ValueError):
                conf = None
        if et not in (OC, OU, LC, LR) or (et == LR and not ((payload.get('properties') or {}).get('retracts_event_id'))):
            slow.append(ev)
            rows.append(None)
            continue
        if et in (OC, OU) and not oid:
            from ontology.service import OntologyError
            raise OntologyError(f'{et} requiere object_id')
        if et in (LC, LR) and (not oid or not tid):
            from ontology.service import OntologyError
            raise OntologyError(f'{et} requiere object_id (source) y target_id')
        eid = _uuid.uuid4()
        prev_type = None
        if et in (OC, OU):
            cur = objs.get(oid)
            prev_type = cur['type'] if cur else None
            new_props = payload.get('properties') or {}
            label = payload.get('label') or (cur['label'] if cur else oid)
            otype = payload.get('type') or (cur['type'] if cur else 'Company')
            _vigilar('object_type', otype)
            if cur is None:
                objs[oid] = {'type': otype, 'label': label, 'props': dict(new_props), 'new': True, 'prev': None}
                obj_new[oid] = {'id': oid, 'type': otype, 'label': label, 'properties': dict(new_props)}
                out['objects_created'] += 1
            else:
                prev_props = dict(cur['props'])
                if et == OU and 'properties_prev' in payload and payload['properties_prev'] is None:
                    # el valor ANTERIOR de cada clave tocada queda en el evento: deshacer lo restaura exacto
                    payload['properties_prev'] = {k: prev_props.get(k) for k in new_props}
                merged = dict(cur['props'])
                merged.update(new_props)
                cur.update(type=otype, label=label, props=merged)
                if oid in obj_new:
                    obj_new[oid].update(type=otype, label=label, properties=merged)
                else:
                    cur.setdefault('prev', prev_props)
                    obj_upd.append(oid)
                    out['objects_updated'] += 1
            if _gates is not None:
                touches = any(k in new_props for k in ('severity', 'activo', 'severity_crisis'))
                _gates.defer_object(session, oid, prev_type, (objs[oid].get('prev') if cur else None), touches)
        elif et == LC:
            rel = payload.get('rel_type') or payload.get('type') or 'supply'
            _vigilar('rel_type', rel)
            props = dict(payload.get('properties') or {})
            twins = live.get((oid, tid, rel)) or []
            twin = None if (vt is not None or props.get('allow_duplicate')) else _dedup_twin(twins, vf, payload.get('weight'))
            if twin is not None:
                props['dedup_of'] = str(twin['id'])
                if twin.get('event_id'):
                    props['dedup_event_id'] = str(twin['event_id'])
                payload['properties'] = props
                out['links_dedup'] += 1
            else:
                lid = _uuid.uuid4()
                link_rows.append({'id': lid, 'source_id': oid, 'target_id': tid, 'rel_type': rel,
                                  'weight': payload.get('weight'), 'properties': props, 'valid_from': vf,
                                  'valid_to': vt, 'event_id': eid})
                live.setdefault((oid, tid, rel), []).append({'id': lid, 'event_id': eid, 'valid_from': vf,
                                                            'weight': payload.get('weight')})
                out['links_created'] += 1
                confs[eid] = (props.get('confidence'), ev.get('source_id'))
        elif et == LR:
            rid = (payload.get('properties') or {}).get('retracts_event_id')
            try:
                rid_u = _uuid.UUID(str(rid))
            except ValueError:
                from ontology.service import OntologyError
                raise OntologyError(f'retracts_event_id inválido: {rid}')
            closes.append({'rid': rid_u, 'vt': vf, 'promote': bool((payload.get('properties') or {}).get('promote_dedups'))})
        rows.append({'id': str(eid), '_uuid': eid, 'event_type': et, 'object_id': oid, 'target_id': tid,
                     'payload': _json(payload), '_payload': payload, 'valid_from': vf, 'valid_to': vt,
                     'source': source, 'actor': actor, 'source_id': ev.get('source_id'), 'confidence': conf,
                     'release_hash': rel_hash, '_prev_type': prev_type})
    # 1) eventos (una sentencia por bloque; recorded_at = clock_timestamp() por fila, como apply_event)
    real = [r for r in rows if r is not None]
    if real:
        session.execute(text(_FAST_SQL), [{k: v for k, v in r.items() if not k.startswith('_')} for r in real])
    # 2) materialización
    if obj_new:
        session.execute(insert(ObjectRecord), list(obj_new.values()))
    for oid in obj_upd:
        o = session.get(ObjectRecord, oid)
        if o is not None:
            o.properties, o.label, o.type = objs[oid]['props'], objs[oid]['label'], objs[oid]['type']
    if link_rows:
        session.execute(insert(LinkRecord), link_rows)
    for c in closes:
        n = session.execute(text('UPDATE links SET valid_to = :vt WHERE event_id = CAST(:rid AS uuid) AND valid_to IS NULL'),
                            {'vt': c['vt'], 'rid': str(c['rid'])}).rowcount
        out['links_closed'] += int(n or 0)
        if c['promote'] and n:
            for r in session.execute(text('SELECT source_id, target_id, rel_type, weight FROM links WHERE event_id = '
                                          'CAST(:rid AS uuid)'), {'rid': str(c['rid'])}).all():
                _promote_dedup(session, r[0], r[1], r[2], r[3])
    session.flush()
    # 3) ganchos: versión del grafo + efecto de la decisión en curso
    for r in real:
        ref = _EvRef(r)
        if _sig is not None:
            _sig.mark(session, ref, r['_prev_type'])
        if _dec is not None:
            _dec.note_event(ref)
        out['ids'].append(r['_uuid'])
    # 4) puertas de los vínculos del bloque (G-BULK: la MISMA forma que G1 para cada uno, con SU valid_from)
    if gate and link_rows:
        out['gate'] = gate_links_block(session, link_rows, confs) or out['gate']
    # 5) lo que el camino rápido no cubre: apply_event (idéntico, uno a uno)
    for ev in slow:
        e = apply_event(session, ev['event_type'], ev.get('payload') or {}, valid_from=ev['valid_from'], source=source,
                        actor=actor, object_id=ev.get('object_id'), target_id=ev.get('target_id'),
                        valid_to=ev.get('valid_to'), source_id=ev.get('source_id'), confidence=ev.get('confidence'))
        out['ids'].append(e.id)
        out['slow_path'] += 1
    # el orden de `ids` sigue el de entrada: los lentos van al final solo si existen (lo normal: ninguno)
    if slow:
        fast_ids = iter(out['ids'][:len(real)])
        slow_ids = iter(out['ids'][len(real):])
        out['ids'] = [next(fast_ids) if r is not None else next(slow_ids) for r in rows]


def gate_links_block(session, link_rows, confs=None):
    """G-BULK para vínculos ya materializados en el bloque (cada uno con su valid_from): reporte único, registrado
    en la decisión en curso; en bloqueo (policy.gates@2.0.0) lanza GateViolation ANTES de confirmar."""
    try:
        import core.gates as _gates
        from core.gates import focus as _gf
        from core.gates import report as _gr
        accepted = [{'source': r['source_id'], 'target': r['target_id'], 'rel_type': r['rel_type'], 'weight': r['weight'],
                     'properties': r['properties'], 'external_id': (r['properties'] or {}).get('external_id'),
                     'evidenced_by': list((r['properties'] or {}).get('evidenced_by') or ()),
                     'source_id': (confs or {}).get(r['event_id'], (None, None))[1]} for r in link_rows]
        ctx = _bulk_context(session, accepted)
        ends_all, sources_all, inv_all = ctx
        lim, flow = _gf._limits(), _gf._flow_rels()
        triples = []
        for r, rec in zip(link_rows, accepted):
            props = rec['properties'] or {}
            ends = {x: ends_all.get(x) or {'type': None, 'live': False} for x in (rec['source'], rec['target'])}
            ev_by = [rec['source_id']] if rec.get('source_id') else []
            srcs = {sid: sources_all[sid] for sid in ev_by if sid in sources_all}
            inv = inv_all.get((rec['target'], rec['source'], rec['rel_type'])) or ()
            t, _f = _gf.link_triples({'id': str(r['id']), 'source': rec['source'], 'target': rec['target'],
                                      'rel': rec['rel_type'], 'weight': rec['weight'],
                                      'confidence': props.get('confidence'), 'valid_from': r['valid_from'],
                                      'valid_to': r.get('valid_to'),
                                      'rel_label': props.get('rel_label') or props.get('label'),
                                      'evidenced_by': ev_by,
                                      'dated': bool(props.get('predicate') or props.get('since'))},
                                     ends, inv, srcs, lim, flow)
            triples += t
        rep = _gates.evaluate('ontology.g_bulk', list(dict.fromkeys(triples)), None)
        if rep is None:
            return None
        _gr.record(rep, session=session)
        if _gates.blocks(rep):
            raise _gates.GateViolation(rep)
        return {'mode': rep['mode'], 'outcome': rep['outcome'], 'checked': len(link_rows),
                'by_rule': _gr.by_rule_of(rep), 'truncated': rep.get('truncated', 0), 'latency_us': rep.get('latency_us')}
    except Exception as e:  # noqa: BLE001
        if getattr(e, 'code', None) == 'gate_violation':
            raise
        return None
