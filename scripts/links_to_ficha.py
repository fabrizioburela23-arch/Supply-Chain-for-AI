"""scripts/links_to_ficha.py — vínculos investigados (JSON de los agentes) → fichas khipus.company/1 «de solo vínculos».

El piloto de engrosar conexiones (2026-10-26): agentes con búsqueda web investigan, para empresas que YA están en Khipus,
de quién compran y a quién venden. Cada vínculo trae fuente, cita textual y confianza. Este script los envuelve en una
ficha mínima por empresa (identidad tomada del catálogo) para que entren por el MISMO importador (📥): fusiona con la
empresa existente rellenando solo lo que falta —nunca pisa lo curado— y los vínculos pasan por las reglas de siempre
(vivo / propuesto / pendiente / cuarentena). Nada se escribe en la base: solo se arma el JSONL.

    python scripts/links_to_ficha.py out1.json out2.json ... --out fichas_links.jsonl [--min-conf 0.4]
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FLOW = ('supply', 'fab', 'cloud', 'license', 'ppa', 'deploy')
ROLES = {**{r: ('supplier', 'customer') for r in FLOW}, 'invest': ('investor', 'investee'),
         'owns': ('owner', 'owned'), 'partner': ('partner',)}
KINDS = ('primary', 'press', 'trade', 'corporate', 'rumor', 'aggregator', 'state')
STATUSES = ('active', 'ended', 'announced', 'planned', 'rumored', 'disputed')
KHIPUS_ID = re.compile(r'^[A-Za-z][A-Za-z0-9_]{1,79}$')
DATE = re.compile(r'^(1[0-9]|20)[0-9]{2}(-(0[1-9]|1[0-2])(-(0[1-9]|[12][0-9]|3[01]))?)?$')
URL = re.compile(r'^https?://[^\s/]+\.[^\s]+$')


def _clean_link(l, min_conf):
    """→ (vínculo limpio | None, motivo del descarte)."""
    rt, role = l.get('rel_type'), l.get('this_role')
    if rt not in ROLES or role not in ROLES[rt]:
        return None, 'rel_type/this_role'
    name = str(l.get('counterparty_name') or '').strip()
    if len(name) < 2:
        return None, 'sin contraparte'
    url, quote = str(l.get('source_url') or '').strip().replace(' ', '%20'), str(l.get('quote') or '').strip()
    if not URL.match(url) or not quote:
        return None, 'sin fuente o cita'
    kind = l.get('source_kind') if l.get('source_kind') in KINDS else 'press'
    status = l.get('status') if l.get('status') in STATUSES else 'active'
    try:
        conf = float(l.get('confidence'))
    except (TypeError, ValueError):
        return None, 'sin confianza'
    conf = max(0.0, min(1.0, conf))
    if kind == 'rumor' or status == 'rumored':
        conf, status = min(conf, 0.3), 'rumored'
    if kind != 'primary':
        conf = min(conf, 0.89)             # ≥ 0,9 solo con fuente primaria (regla de los lotes)
    if conf < min_conf:
        return None, 'confianza baja'
    as_of = str(l.get('as_of') or '').strip()
    if not DATE.match(as_of):
        as_of = dt.date.today().strftime('%Y-%m')
    cp = {'name': name[:160]}
    kid = str(l.get('counterparty_khipus_id') or '').strip()
    if kid:
        cp['khipus_id' if KHIPUS_ID.match(kid) else 'id_hint'] = kid
    if re.fullmatch(r'[A-Z]{2}', str(l.get('counterparty_country') or '')):
        cp['country'] = l['counterparty_country']
    rel = {'counterparty': cp, 'rel_type': rt, 'this_role': role,
           'label_es': str(l.get('label_es') or f'{name}')[:300], 'label_en': str(l.get('label_en') or f'{name}')[:300],
           'status': status, 'confidence': round(conf, 2),
           'evidence': [{'source_url': url, 'source_name': str(l.get('source_name') or '')[:300] or None,
                         'source_kind': kind, 'as_of': as_of, 'quote': quote[:500]}]}
    rel['evidence'][0] = {k: v for k, v in rel['evidence'][0].items() if v is not None}
    if len(rel['label_es']) < 3:
        rel['label_es'] = f'{name} ({rt})'
    if len(rel['label_en']) < 3:
        rel['label_en'] = f'{name} ({rt})'
    if l.get('product'):
        rel['product'] = str(l['product'])[:120]
    if rt in FLOW:
        try:
            crit = int(l.get('criticality'))
        except (TypeError, ValueError):
            crit = 2                       # sin dato: «uno de varios» (la media prudente); queda rotulado en la nota
        rel['dependency'] = {'criticality': max(1, min(6, crit))}
    return rel, None


def build(files, min_conf=0.4, today=None):
    """→ (fichas, resumen). Una ficha por empresa con ≥ 1 vínculo bueno; mismo vínculo repetido se deja una vez."""
    from core.import_normalize import iso2_of
    today = today or dt.datetime.now(dt.timezone.utc)
    snap = json.load(open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8'))
    nodes = {n['id']: n for n in snap['nodes']}
    by_co, dropped, notes = {}, {}, {}
    for f in files:
        d = json.load(open(f, encoding='utf-8'))
        for l in d.get('links') or []:
            if not isinstance(l, dict):
                continue
            rel, why = _clean_link(l, min_conf)
            cid = l.get('company_id')
            if rel is None:
                dropped[why] = dropped.get(why, 0) + 1
                continue
            by_co.setdefault(cid, []).append(rel)
        notes.update(d.get('notes') or {})
    fichas, resumen = [], {'companies': 0, 'links': 0, 'dropped': dropped, 'unknown_company': [], 'notes': notes}
    now = today.strftime('%Y-%m-%dT%H:%M:%SZ')
    for cid, rels in by_co.items():
        n = nodes.get(cid)
        if n is None:
            resumen['unknown_company'].append(cid)
            continue
        seen, uniq = set(), []
        for r in rels:
            k = (r['rel_type'], r['this_role'], (r['counterparty'].get('khipus_id') or r['counterparty'].get('id_hint')
                                                 or r['counterparty']['name']).lower())
            if k not in seen:
                seen.add(k)
                uniq.append(r)
        for i, r in enumerate(uniq, 1):
            r['relation_id'] = f'lnk-{i:03d}'
        first = uniq[0]['evidence'][0]
        base = {'source_url': first['source_url'], 'as_of': first['as_of'], 'confidence': 0.5}
        label = n.get('label') or cid
        iso = iso2_of(n.get('country')) or iso2_of((n.get('loc') or '')) or 'US'
        role_es = (n.get('role') or n.get('supplies') or f'Empresa del grafo Khipus: {label}.').strip()
        role_en = (n.get('role_en') or n.get('supplies_en') or role_es).strip()
        ficha = {
            'schema': 'khipus.company/1', 'record_id': f'fb-2026-lnk-{re.sub(r"[^A-Za-z0-9]", "", cid).lower()}'[:79],
            'research_meta': {'researcher': 'Claude (agentes con búsqueda web, piloto de vínculos)', 'researched_at': now,
                              'method': 'ai_assisted', 'tools': ['web_search', 'web_fetch'], 'tier': 'A', 'priority': 'P2',
                              'batch': f'lnk-{today.strftime("%Y-%m-%d")}', 'revision': 1,
                              'notes': ('Ficha SOLO de vínculos: la identidad sale del catálogo y no aporta datos nuevos. '
                                        + str((notes or {}).get(cid) or ''))[:2000]},
            'identity': {'legal_name': {**base, 'value': label},
                         'short_name': label[:120] if len(label) >= 2 else f'{label} ',
                         'status': {**base, 'value': 'public' if n.get('mkt') else 'private'},
                         'hq_country': {**base, 'value': iso}},
            'classification': {'cat': n.get('cat') or 'other'},
            # el MISMO texto del catálogo: así la fusión no lista diferencias en lo curado
            'profile': {'summary': {**base, 'value': role_es[:1200].ljust(10), 'value_en': role_en[:1200].ljust(10)}},
            'relations': uniq,
        }
        if KHIPUS_ID.match(cid):
            ficha['khipus_id_hint'] = cid
        fichas.append(ficha)
        resumen['companies'] += 1
        resumen['links'] += len(uniq)
    return fichas, resumen


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='+')
    ap.add_argument('--out', required=True)
    ap.add_argument('--min-conf', type=float, default=0.4)
    a = ap.parse_args(argv)
    from ontology import company_import as CI
    fichas, res = build(a.files, a.min_conf)
    san, _logs, _s = CI.sanitize_batch(fichas)
    valid, invalid = CI.validate_batch(san)
    with open(a.out, 'w', encoding='utf-8') as fh:
        for rec, _m in valid:
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print(f"{res['companies']} empresas · {res['links']} vínculos · válidas {len(valid)} · inválidas {len(invalid)} · "
          f"descartes {res['dropped']} · empresa desconocida {res['unknown_company']}")
    for i in invalid[:10]:
        print('  ✗', i.get('record_id'), [f"{e.get('path')}: {e.get('msg') or e.get('type')}" for e in i['errors']][:4])
    return 0 if not invalid else 1


if __name__ == '__main__':
    sys.exit(main())
