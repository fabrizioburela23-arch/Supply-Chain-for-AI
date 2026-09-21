#!/usr/bin/env python3
"""scripts/migrate_v0_to_ontology.py — Fase 1: migra data/grafo_v0.json (el
snapshot congelado en Fase 0) a la ontología (Postgres, tabla events + vistas
materializadas objects/links).

Reglas de fecha (documentadas — no son arbitrarias):
- Empresas y objetos de ontología (Tech/Policy/Country/…): valid_from =
  GENESIS ('2000-01-01'). No tenemos fecha de fundación real para las 463
  empresas; GENESIS representa "desde que empezamos a rastrear este universo"
  — es anterior a todos los hechos temporales curados (el más antiguo es de
  2010), así que ningún as_of relevante los excluye por accidente.
- Relaciones de cadena de suministro SIN fecha propia (los 1163 links crudos):
  valid_from = GENESIS también (fuente: 'migration_v0_links'). Representan
  "según nuestro conocimiento, esta relación siempre estuvo vigente" — es una
  aproximación honesta: no inventamos una fecha de inicio que no tenemos.
- Hechos temporales curados (105 en temporal_facts, 86 son aristas): usan su
  valid_from/valid_until REAL (fuente: 'migration_v0_temporal'). Estos son los
  que dan valor real al time-travel (ej. Qualcomm perdió a Huawei 2019-2021).

Es NORMAL que una misma pareja (source,target) tenga más de una fila en
`links`: una genérica desde GENESIS y otra con fecha real desde los hechos
temporales — son evidencias distintas, no un error. Bitemporal = puede haber
más de una "versión de la verdad" para el mismo par en el tiempo.

Uso:
    export DATABASE_URL=postgresql://...
    python scripts/migrate_v0_to_ontology.py [--dry-run] [--reset]
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GENESIS = '2000-01-01'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='no escribe nada, solo valida y cuenta')
    ap.add_argument('--reset', action='store_true', help='DROP + CREATE de las tablas antes de migrar (destructivo)')
    ap.add_argument('--graph', default=os.path.join(os.path.dirname(__file__), '..', 'data', 'grafo_v0.json'))
    args = ap.parse_args()
    ok = run_migration(reset=args.reset, dry_run=args.dry_run, graph_path=args.graph)
    if not ok:
        sys.exit(1)


def run_migration(reset=False, dry_run=False, graph_path=None, log=print):
    """Núcleo reutilizable de la migración v0 → ontología. Lo llama main() (CLI)
    y el hook REMIGRATE_ON_BOOT del server (para re-migrar producción sin CLI).
    `log`: función de progreso (print o logger.info). reset=True es DESTRUCTIVO
    (DROP de tablas). Devuelve True si migró (o dry-run), False si falló."""
    graph_path = graph_path or os.path.join(os.path.dirname(__file__), '..', 'data', 'grafo_v0.json')

    from ontology.db import ontology_available, init_schema, session_scope, _get_engine
    if not ontology_available():
        log('❌ DATABASE_URL no está configurada.')
        return False

    with open(graph_path, 'r', encoding='utf-8') as f:
        g = json.load(f)

    nodes = g['nodes']
    links = g['links']
    ontology_objects = (g.get('ontology') or {}).get('objects', [])
    temporal_facts = g.get('temporal_facts') or []

    log(f'Snapshot: {len(nodes)} empresas, {len(links)} links crudos, '
        f'{len(ontology_objects)} objetos de ontología, {len(temporal_facts)} hechos temporales')

    if dry_run:
        edges_in_facts = [f for f in temporal_facts if f.get('object_type') == 'node']
        log(f'[dry-run] Se crearían: {len(nodes) + len(ontology_objects)} objetos, '
            f'{len(links)} links base (GENESIS) + {len(edges_in_facts)} links con fecha real')
        return True

    from ontology.models import Base
    from ontology.service import apply_event

    engine = _get_engine()
    if reset:
        log('⚠️  --reset: eliminando tablas existentes…')
        Base.metadata.drop_all(engine)
    init_schema()

    t0 = time.time()
    known_ids = {n['id'] for n in nodes} | {o['id'] for o in ontology_objects}

    with session_scope() as s:
        for n in nodes:
            props = {k: v for k, v in n.items() if k not in ('id', 'label')}
            apply_event(s, 'ObjectCreated', {'label': n.get('label') or n['id'], 'type': 'Company', 'properties': props},
                        valid_from=GENESIS, source='migration_v0', actor='script:migrate_v0_to_ontology',
                        object_id=n['id'])
        for o in ontology_objects:
            apply_event(s, 'ObjectCreated', {'label': o.get('label') or o['id'], 'type': o.get('type', 'Org'), 'properties': {}},
                        valid_from=GENESIS, source='migration_v0', actor='script:migrate_v0_to_ontology',
                        object_id=o['id'])
        s.flush()
        log(f'✅ {len(nodes) + len(ontology_objects)} objetos creados ({time.time()-t0:.1f}s)')

        skipped = 0
        for l in links:
            src, tgt = l.get('source'), l.get('target')
            if src not in known_ids or tgt not in known_ids or src == tgt:
                skipped += 1
                continue
            apply_event(s, 'LinkCreated',
                        {'rel_type': l.get('type') or 'supply', 'weight': l.get('w'),
                         'properties': {'rel_label': l.get('rel') or ''}},
                        valid_from=GENESIS, source='migration_v0_links', actor='script:migrate_v0_to_ontology',
                        object_id=src, target_id=tgt)
        s.flush()
        log(f'✅ {len(links) - skipped} links base creados ({skipped} saltados) ({time.time()-t0:.1f}s)')

        edges = [f for f in temporal_facts if f.get('object_type') == 'node']
        skipped_t = 0
        for f in edges:
            subj, obj = f.get('subject'), f.get('object')
            if subj not in known_ids or obj not in known_ids or subj == obj:
                skipped_t += 1
                continue
            apply_event(s, 'LinkCreated',
                        {'rel_type': f.get('rel') or 'supply',
                         'properties': {'headline': (f.get('meta') or {}).get('headline', ''),
                                        'confidence': f.get('confidence'), 'predicate': f.get('predicate')}},
                        valid_from=f.get('valid_from') or GENESIS, valid_to=f.get('valid_until'),
                        source='migration_v0_temporal', actor='script:migrate_v0_to_ontology',
                        object_id=subj, target_id=obj)
        s.flush()
        log(f'✅ {len(edges) - skipped_t} hechos temporales creados ({skipped_t} saltados) ({time.time()-t0:.1f}s)')

        # ── Factores sistémicos + Asientos (capa multicapa) ──────────────────
        # NO vienen en grafo_v0.json (ese snapshot son empresas y sus links):
        # viven en data/multicapa_factors_seats.json, que produjo
        # scripts/ingest_multicapa.py a partir del documento de Fabrizio.
        # Sin este paso, una re-migración deja la ontología a medias: sin
        # factores no hay FACTOR LIST/FIRE, ni hiperaristas en la fragilidad
        # del motor de matrices, y Activar/DesactivarFactor quedan sin objeto.
        n_fact, n_aff, n_seat = _restore_factors_and_seats(s, known_ids, log)
        s.flush()
        log(f'✅ {n_fact} factores (latentes) + {n_aff} vínculos affects + {n_seat} asientos ({time.time()-t0:.1f}s)')

    log(f'🎉 Migración completa en {time.time()-t0:.1f}s')
    return True


# Nivel LATENTE de los factores. Lección registrada en docs/ESTADO.md: cargar
# los ~70 factores a su severidad de CRISIS pone ρ(T) en 2.63 y satura las
# cascadas (todo al 100%) — "todas las crisis a la vez" no es un escenario
# real. Viven en 1.0 y su nivel de crisis queda en `severity_crisis`, que es
# lo que disparan /api/matrix/factor/fire (what-if) y la Acción ActivarFactor
# (persistente). OJO con la escala: el documento usa 0-10, no 0-5.
FACTOR_LATENT_SEVERITY = 1.0


def _restore_factors_and_seats(s, known_ids, log=print):
    """Carga data/multicapa_factors_seats.json en la ontología. Devuelve
    (n_factores, n_links_affects, n_asientos). Si el archivo no está, no es un
    error: se avisa y se sigue (la migración base ya es útil)."""
    from ontology.service import apply_event

    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'multicapa_factors_seats.json')
    if not os.path.exists(path):
        log('⚠️  data/multicapa_factors_seats.json no está — se omiten factores y asientos.')
        return 0, 0, 0
    with open(path, 'r', encoding='utf-8') as fh:
        data = json.load(fh)

    factors = data.get('factors') or []
    seats = data.get('seats') or []

    n_fact = n_aff = 0
    for f in factors:
        fid = (f.get('id') or '').strip()
        if not fid:
            continue
        members = f.get('members') or {}
        # Solo miembros que EXISTEN: un link 'affects' colgante corrompería la
        # matriz (mismo criterio que la Acción CrearFactor).
        pairs = [(m, float(c)) for m, c in members.items() if m in known_ids]
        if not pairs:
            continue
        apply_event(s, 'ObjectCreated', {
            'label': f.get('label') or fid, 'type': 'Factor',
            'properties': {
                'severity': FACTOR_LATENT_SEVERITY,
                'severity_crisis': float(f['severity']) if f.get('severity') is not None else None,
                'razon': f.get('rationale') or '',
                'fuente': 'multicapa', 'activo': False,
            },
        }, valid_from=GENESIS, source='migration_multicapa',
           actor='script:migrate_v0_to_ontology', object_id=fid)
        n_fact += 1
        for m, coef in pairs:
            apply_event(s, 'LinkCreated',
                        {'rel_type': 'affects', 'weight': coef, 'properties': {'factor': True}},
                        valid_from=GENESIS, source='migration_multicapa',
                        actor='script:migrate_v0_to_ontology', object_id=fid, target_id=m)
            n_aff += 1

    n_seat = 0
    for st in seats:
        sid = (st.get('id') or '').strip()
        if not sid:
            continue
        apply_event(s, 'ObjectCreated', {
            'label': st.get('label') or sid, 'type': 'Seat',
            'properties': st.get('props') or {},
        }, valid_from=GENESIS, source='migration_multicapa',
           actor='script:migrate_v0_to_ontology', object_id=sid)
        n_seat += 1

    return n_fact, n_aff, n_seat


if __name__ == '__main__':
    main()
