"""ontology/link_review.py — COLA DE REVISIÓN de vínculos PROPUESTOS (2026-10-21, tras importar los lotes 2-4).

Los importadores dejan como PROPUESTA (status proposed, confianza 0) todo vínculo que no cumple las reglas para entrar
vivo (rumor, contraparte solo por nombre, confianza < 0,5, participación sin %, fuente débil…). Mientras nadie los
confirme, el kernel NO los cuenta: muchas empresas nuevas quedan sin conexiones (atNorth: grado 0).

Aquí solo se LEE y se ORDENA por importancia; confirmar / rechazar sigue siendo la Acción auditada de siempre
(POST /api/ontology/actions/ConfirmarVinculo | RechazarVinculo, PIN, una decisión en el libro).

Prioridad (sin IA): flujo (supply/fab/cloud/license/ppa/deploy/owns) pesa 3 frente a socio/inversor 1 · × criticidad
declarada (1-6; sin dato 1) · × confianza declarada (sin dato 0,5) · × importancia de los extremos (log del grado de
flujo vivo de cada uno: un vínculo de una empresa muy conectada mueve más el grafo).
"""
import math

REASON_TEXT = {
    'low_confidence': ('confianza declarada baja (< 0,5)', 'low declared confidence (< 0.5)'),
    'rumored': ('la fuente lo da como rumor', 'the source calls it a rumor'),
    'counterparty_by_name_only': ('la otra empresa se reconoció solo por el nombre', 'the other company was matched by name only'),
    'holding_without_pct': ('participación sin % declarado', 'holding without a declared %'),
    'owns_without_control_pct': ('propiedad sin un % de control declarado', 'ownership without a declared control %'),
    'source_trust_low': ('fuente de poca confianza (agregador, wiki…)', 'low-trust source (aggregator, wiki…)'),
    'flow_supplier_type': ('el tipo de proveedor no suele dar flujo directo', 'this supplier type rarely gives direct flow'),
    'not_verified': ('sin verificar', 'not verified'),
    'holding_unverified': ('participación sin fuente que la confirme', 'holding without a confirming source'),
    'status_disputed': ('la relación está en disputa', 'the relationship is disputed'),
}


def _flow_types():
    try:
        from ontology.vocabulary import flow_relation_types
        return set(flow_relation_types())
    except Exception:  # noqa: BLE001
        return {'supply', 'fab', 'cloud', 'license', 'ppa', 'deploy', 'owns'}


def priority(rel_type, props, deg_s, deg_t, flow=None):
    flow = _flow_types() if flow is None else flow
    p = props or {}
    dep = p.get('dependency') if isinstance(p.get('dependency'), dict) else {}
    try:
        crit = float(dep.get('criticality') or p.get('criticality') or 1)
    except (TypeError, ValueError):
        crit = 1.0
    try:
        conf = float(p.get('declared_confidence') if p.get('declared_confidence') is not None else 0.5)
    except (TypeError, ValueError):
        conf = 0.5
    base = 3.0 if rel_type in flow else 1.0
    imp = math.log2(2 + (deg_s or 0)) + math.log2(2 + (deg_t or 0))
    return round(base * max(1.0, min(6.0, crit)) * max(0.05, min(1.0, conf)) * imp, 4)


def queue(session, limit=30, offset=0, q=None, lang='es'):
    """→ {'total', 'items': [...], 'by_reason': {...}} de los vínculos propuestos vigentes, por prioridad."""
    from sqlalchemy import func, select
    from ontology.models import LinkRecord, ObjectRecord
    es = not str(lang).startswith('en')
    flow = _flow_types()
    rows = session.scalars(select(LinkRecord).where(LinkRecord.valid_to.is_(None),
                                                    LinkRecord.properties['status'].astext == 'proposed')).all()
    # grado de FLUJO vivo de cada empresa (los propuestos no cuentan)
    deg = {}
    live = session.execute(select(LinkRecord.source_id, LinkRecord.target_id, LinkRecord.rel_type)
                           .where(LinkRecord.valid_to.is_(None),
                                  func.coalesce(LinkRecord.properties['status'].astext, '') != 'proposed')).all()
    for s_, t_, r_ in live:
        if r_ in flow:
            deg[s_] = deg.get(s_, 0) + 1
            deg[t_] = deg.get(t_, 0) + 1
    ids = {x.source_id for x in rows} | {x.target_id for x in rows}
    src_ids = {sid for x in rows for sid in ((x.properties or {}).get('evidenced_by') or [])[:3]}
    objs = {o.id: o for o in session.scalars(select(ObjectRecord).where(ObjectRecord.id.in_(ids | src_ids))).all()} \
        if (ids or src_ids) else {}

    def label(i):
        o = objs.get(i)
        return (o.label if o is not None and o.label else i)

    items, by_reason = [], {}
    ql = (q or '').strip().lower()
    for x in rows:
        p = x.properties or {}
        rs = p.get('proposed_reason') or 'not_verified'
        by_reason[rs] = by_reason.get(rs, 0) + 1
        sl, tl = label(x.source_id), label(x.target_id)
        if ql and ql not in sl.lower() and ql not in tl.lower() and ql not in str(p.get('product') or '').lower():
            continue
        srcs = []
        for sid in (p.get('evidenced_by') or [])[:3]:
            o = objs.get(sid)
            pr = (o.properties or {}) if o is not None else {}
            if pr.get('url'):
                srcs.append({'url': pr.get('url'), 'kind': pr.get('kind') or pr.get('source_kind'),
                             'name': pr.get('publisher') or pr.get('name') or (o.label if o is not None else None)})
        dep = p.get('dependency') if isinstance(p.get('dependency'), dict) else {}
        rt = REASON_TEXT.get(rs)
        items.append({
            'link_id': str(x.id), 'rel_type': x.rel_type, 'flow': x.rel_type in flow,
            'source': {'id': x.source_id, 'label': sl, 'degree': deg.get(x.source_id, 0)},
            'target': {'id': x.target_id, 'label': tl, 'degree': deg.get(x.target_id, 0)},
            'label': p.get('rel_label') if es else (p.get('rel_label_en') or p.get('rel_label')),
            'product': p.get('product'), 'criticality': dep.get('criticality') or p.get('criticality'),
            'declared_confidence': p.get('declared_confidence'), 'declared_status': p.get('declared_status'),
            'reason': rs, 'reason_text': (rt[0] if es else rt[1]) if rt else rs,
            'since': p.get('since'), 'sources': srcs, 'record_id': p.get('record_id'),
            'priority': priority(x.rel_type, p, deg.get(x.source_id, 0), deg.get(x.target_id, 0), flow),
        })
    items.sort(key=lambda i: (-i['priority'], i['link_id']))
    return {'total': len(rows), 'matching': len(items), 'by_reason': by_reason,
            'items': items[offset:offset + limit], 'offset': offset, 'limit': limit}
