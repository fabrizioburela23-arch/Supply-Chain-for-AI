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

    from ontology.db import ontology_available, init_schema, session_scope, _get_engine
    if not ontology_available():
        print('❌ DATABASE_URL no está configurada. Exporta la variable antes de correr esta migración.')
        sys.exit(1)

    with open(args.graph, 'r', encoding='utf-8') as f:
        g = json.load(f)

    nodes = g['nodes']
    links = g['links']
    ontology_objects = (g.get('ontology') or {}).get('objects', [])
    temporal_facts = g.get('temporal_facts') or []

    print(f'Snapshot: {len(nodes)} empresas, {len(links)} links crudos, '
          f'{len(ontology_objects)} objetos de ontología, {len(temporal_facts)} hechos temporales')

    if args.dry_run:
        edges_in_facts = [f for f in temporal_facts if f.get('object_type') == 'node']
        print(f'[dry-run] Se crearían: {len(nodes) + len(ontology_objects)} objetos, '
              f'{len(links)} links base (GENESIS) + {len(edges_in_facts)} links con fecha real (hechos temporales)')
        return

    from ontology.models import Base
    from ontology.service import apply_event

    engine = _get_engine()
    if args.reset:
        print('⚠️  --reset: eliminando tablas existentes…')
        Base.metadata.drop_all(engine)
    init_schema()

    t0 = time.time()
    known_ids = {n['id'] for n in nodes} | {o['id'] for o in ontology_objects}

    with session_scope() as s:
        # 1) Objetos: empresas
        for n in nodes:
            props = {k: v for k, v in n.items() if k not in ('id', 'label')}
            apply_event(s, 'ObjectCreated', {'label': n.get('label') or n['id'], 'type': 'Company', 'properties': props},
                        valid_from=GENESIS, source='migration_v0', actor='script:migrate_v0_to_ontology',
                        object_id=n['id'])
        # 2) Objetos: entidades de ontología (Tech/Policy/Country/Energy/Material/Product/Org)
        for o in ontology_objects:
            apply_event(s, 'ObjectCreated', {'label': o.get('label') or o['id'], 'type': o.get('type', 'Org'), 'properties': {}},
                        valid_from=GENESIS, source='migration_v0', actor='script:migrate_v0_to_ontology',
                        object_id=o['id'])
        s.flush()
        print(f'✅ {len(nodes) + len(ontology_objects)} objetos creados ({time.time()-t0:.1f}s)')

        # 3) Links base (sin fecha propia → GENESIS)
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
        print(f'✅ {len(links) - skipped} links base creados ({skipped} saltados por ids no resueltos) ({time.time()-t0:.1f}s)')

        # 4) Hechos temporales curados con fecha real (valor añadido del time-travel)
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
        print(f'✅ {len(edges) - skipped_t} hechos temporales con fecha real creados ({skipped_t} saltados) ({time.time()-t0:.1f}s)')

    print(f'🎉 Migración completa en {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
