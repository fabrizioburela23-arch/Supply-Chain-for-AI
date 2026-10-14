"""ontology/company_import.py — importador de fichas khipus.company/1 (docs/expansion/EXPANSION_5K.md, bloque E2).

Flujo: fichas (JSONL/JSON) → `validate_batch` (espejo Pydantic, ontology/company_schema) → `resolve_batch` (identidad:
lei > isin/cik/qid > yahoo_symbol / ticker@MIC > dominio (solo candidato) > nombre ≥ 85; 60-84 = "posible duplicado")
→ `plan` PURO (qué se crea / fusiona / actualiza / omite y por qué; categorías por aprobar; vínculos ruteados
vivo / propuesta / pendiente / cuarentena; "¿qué cambia?" del kernel sobre una copia en memoria; `plan_sha`) →
`apply_run` (PIN; `expect.plan_sha` + misma generación del grafo o 409; UNA decisión `ontology.bulk_import`; UNA
transacción; escritura por bloques E2.8; puertas en sombra; una sola reconstrucción de las vistas) → `rollback_run`
(de la más nueva a la más vieja, con retracciones DIRIGIDAS y decisión `ontology.import_rollback`).

Reglas: conflicto con un dato curado = SE LISTA, nunca se pisa (F-6); vínculo vivo solo con confianza ≥ 0,5 y fuente
con trust ≥ 2 (F-5); lo demás entra como PROPUESTA (status proposed, confianza 0 hasta que una persona confirme);
contraparte desconocida = PENDIENTE (import_pending_links); `owns` con menos del 50 % = invest (policy.import).
Fecha de cada vínculo = `start` de la ficha (sin start → GENESIS "desde que se rastrea", nunca "ahora"); `end` →
valid_to. Nada se borra: deshacer = más eventos.
"""
import csv
import hashlib
import json
import logging
import os
import re
import time
import uuid
from collections import Counter, OrderedDict
from datetime import datetime, timezone

log = logging.getLogger('khipu')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN_SCHEMA = 'import-plan/1'
SOURCE_PREFIX = 'import:'            # Event.source de una corrida: import:<run_id>  (String(60))
ROLLBACK_PREFIX = 'import_rb:'
PROVENANCE = 'research_import'       # properties.source de los vínculos (no es fuente de bulto: peso entero)
ACTOR = 'script:import_companies'
ROUTES = ('live', 'proposed', 'pending', 'quarantine')
ACTIONS = ('create', 'merge', 'update', 'skip')
CHOKEPOINTS_TOP = 20
TSMC_ID = 'TSMC'
# políticas del artefacto policy.import@1.0.0 (los valores de HOY; el artefacto manda cuando está)
POLICY_DEFAULTS = {
    'live_min_confidence': 0.5, 'live_min_trust': 2, 'block_size': 250, 'max_records_per_run': 5000,
    'conflicts': 'list', 'owns_min_pct': 50, 'unverified_confidence': 0.4, 'name_write_threshold': 85,
    'name_possible_threshold': 60, 'upload_chunk_max_bytes': 921600, 'proposal_statuses': ['rumored', 'disputed'],
    'quarantine_supplier_types': ['Country', 'Policy'],
}
# claves del catálogo que son DATOS CURADOS: en una fusión nunca se pisan (se listan como conflicto)
_CURATED_KEYS = ('cat', 'sector', 'country', 'ticker', 'mkt', 'role', 'role_en', 'supplies', 'supplies_en', 'moat',
                 'moat_en', 'growth', 'growth_en', 'label', 'margin', 'preipo')
_TEXT_KEYS = ('role', 'supplies', 'moat', 'risk', 'growth')
_EN_PENDING = '[EN pendiente] '
_AGGREGATOR_HOSTS = ('wikipedia.org', 'sec.gov', 'github.com', 'finance.yahoo.com', 'openfigi.com', 'gleif.org',
                     'bloomberg.com', 'reuters.com', 'crunchbase.com', 'linkedin.com')


class ImportProblem(ValueError):
    """Mensaje en español (args[0]) + inglés (`en`) + código corto para la API."""
    def __init__(self, es, en=None, code='import_error'):
        super().__init__(es)
        self.en = en or es
        self.code = code


# ── política ────────────────────────────────────────────────────────────────────────────────────────────────────
def policy(key=None):
    """Valor de policy.import (gobernanza) o el de hoy si el artefacto no está en el release."""
    try:
        from core import governance
        p = governance.section('policy.import')
    except Exception:  # noqa: BLE001
        p = {}
    merged = dict(POLICY_DEFAULTS)
    merged.update({k: v for k, v in (p or {}).items() if k in POLICY_DEFAULTS})
    return merged if key is None else merged[key]


def _now():
    return datetime.now(timezone.utc)


def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str)


def _sha(obj):
    return hashlib.sha256(_canon(obj).encode('utf-8')).hexdigest()


# ── fichas ──────────────────────────────────────────────────────────────────────────────────────────────────────
def load_bundle(path):
    """Archivo → {'records': [...], 'updates': [...], 'approve_categories': [...], 'batch': str|None}.
    `.jsonl`: una ficha por línea (líneas vacías o `#` se ignoran). `.json`: una lista de fichas o un paquete
    {schema: 'khipus.import/1', batch, records, updates, approve_categories}."""
    with open(path, encoding='utf-8') as fh:
        text = fh.read()
    return parse_bundle(text, name=os.path.basename(path))


def parse_bundle(text, name='import.json'):
    text = text.lstrip('﻿')
    stripped = text.strip()
    if name.endswith('.jsonl') or (stripped and stripped[0] == '{' and '\n{' in stripped and not stripped.startswith('{"schema": "khipus.import/1"')
                                   and not stripped.startswith('{"schema":"khipus.import/1"')):
        records = []
        for n, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                records.append({'_parse_error': f'línea {n}: {e.msg} / line {n}: {e.msg}', '_line': n})
        return {'records': records, 'updates': [], 'approve_categories': [], 'batch': None}
    data = json.loads(stripped) if stripped else []
    if isinstance(data, list):
        return {'records': data, 'updates': [], 'approve_categories': [], 'batch': None}
    if isinstance(data, dict) and 'records' in data:
        return {'records': list(data.get('records') or []), 'updates': list(data.get('updates') or []),
                'approve_categories': list(data.get('approve_categories') or []), 'batch': data.get('batch')}
    if isinstance(data, dict) and data.get('schema') == 'khipus.company/1':
        return {'records': [data], 'updates': [], 'approve_categories': [], 'batch': None}
    raise ImportProblem('el archivo no trae fichas khipus.company/1', 'the file holds no khipus.company/1 records',
                        'bad_file')


def validate_batch(records):
    """[(dict, CompanyRecord)] válidos + [{record_id, index, errors}] inválidos. Puro."""
    from ontology import company_schema as CS
    valid, invalid, seen = [], [], set()
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            invalid.append({'index': i, 'record_id': None, 'errors': [{'path': '(raíz)', 'type': 'dict_type',
                                                                       'msg_es': 'la ficha no es un objeto',
                                                                       'msg_en': 'the record is not an object'}]})
            continue
        if rec.get('_parse_error'):
            invalid.append({'index': i, 'record_id': None, 'errors': [{'path': '(raíz)', 'type': 'json_invalid',
                                                                       'msg_es': rec['_parse_error'],
                                                                       'msg_en': rec['_parse_error']}]})
            continue
        model, errs = CS.validate_record(rec)
        rid = rec.get('record_id') if isinstance(rec.get('record_id'), str) else None
        if errs:
            invalid.append({'index': i, 'record_id': rid, 'errors': errs[:40], 'n_errors': len(errs)})
            continue
        if rid in seen:
            invalid.append({'index': i, 'record_id': rid, 'errors': [{'path': 'record_id', 'type': 'duplicate',
                                                                     'msg_es': f'record_id repetido en el lote: {rid}',
                                                                     'msg_en': f'duplicate record_id in batch: {rid}'}]})
            continue
        seen.add(rid)
        valid.append((rec, model))
    return valid, invalid


# ── identidad: índice de identificadores de la generación vigente ───────────────────────────────────────────────
_IDX = {'generation': None, 'index': None}


class _IdIndex:
    """Identificadores de las empresas del grafo vigente (props ids/listings/mkt del catálogo y de Postgres)."""
    __slots__ = ('generation', 'lei', 'isin', 'cik', 'qid', 'figi', 'yahoo', 'ticker_mic', 'domain', 'ids', 'labels')

    def __init__(self, view):
        from core.import_normalize import yahoo_symbol_for
        self.generation = view.generation
        self.lei, self.isin, self.cik, self.qid, self.figi = {}, {}, {}, {}, {}
        self.yahoo, self.ticker_mic, self.domain, self.labels = {}, {}, {}, {}
        self.ids = set()
        for n in view.nodes:
            oid = n.get('id')
            if not oid:
                continue
            self.ids.add(oid)
            self.labels[oid] = n.get('label') or oid
            ids = n.get('ids') if isinstance(n.get('ids'), dict) else {}
            if ids.get('lei'):
                self.lei.setdefault(str(ids['lei']).upper(), oid)
            for x in (ids.get('isin') or []) if isinstance(ids.get('isin'), list) else ([ids['isin']] if ids.get('isin') else []):
                self.isin.setdefault(str(x).upper(), oid)
            if ids.get('cik'):
                self.cik.setdefault(str(ids['cik']).zfill(10), oid)
            if ids.get('qid') or ids.get('wikidata_qid'):
                self.qid.setdefault(str(ids.get('qid') or ids.get('wikidata_qid')).upper(), oid)
            for x in (ids.get('figi') or []) if isinstance(ids.get('figi'), list) else ([ids['figi']] if ids.get('figi') else []):
                self.figi.setdefault(str(x).upper(), oid)
            if ids.get('domain'):
                self.domain.setdefault(str(ids['domain']).lower(), oid)
            if ids.get('yahoo_symbol'):
                self.yahoo.setdefault(str(ids['yahoo_symbol']).upper(), oid)
            mkt = (n.get('mkt') or '').strip().upper()
            if mkt:
                self.yahoo.setdefault(mkt, oid)           # el símbolo de Yahoo del catálogo (con su sufijo de bolsa)
            for l in (n.get('listings') or []) if isinstance(n.get('listings'), list) else []:
                if not isinstance(l, dict):
                    continue
                if l.get('yahoo_symbol'):
                    self.yahoo.setdefault(str(l['yahoo_symbol']).upper(), oid)
                if l.get('symbol') and l.get('mic'):
                    self.ticker_mic.setdefault((str(l['symbol']).upper(), str(l['mic']).upper()), oid)
                    ys = yahoo_symbol_for(l['symbol'], l['mic'])
                    if ys:
                        self.yahoo.setdefault(ys, oid)
                if l.get('isin'):
                    self.isin.setdefault(str(l['isin']).upper(), oid)
                if l.get('figi'):
                    self.figi.setdefault(str(l['figi']).upper(), oid)


def id_index(view=None):
    from core.hotviews import hot
    view = view or hot.graph()
    cur = _IDX['index']
    if cur is not None and cur.generation == view.generation:
        return cur
    ix = _IdIndex(view)
    _IDX.update(generation=view.generation, index=ix)
    return ix


def _is_current(view):
    """¿`view` es la generación VIGENTE? Entonces core.entities (el resolvedor único, E1.6) ve el mismo grafo."""
    if view is None:
        return True
    try:
        from core.hotviews import hot
        cur = hot.graph(wait=False)
        return cur is not None and cur.generation == view.generation
    except Exception:  # noqa: BLE001
        return False


def resolve_ids(ids, name=None, view=None):
    """Contrato E1.6: {'id','method','score','conflicts'} o None. DELEGA en core.entities.resolve_ids (el resolvedor
    único: detecta identificadores ambiguos, HKEX con ceros, other_names) siempre que la vista sea la vigente (el
    caso normal del plan y de la API); el índice propio de abajo queda SOLO para vistas que no son la publicada
    (pruebas con grafos sintéticos): mismo orden lei > isin/cik/qid > yahoo_symbol / ticker@MIC > dominio (solo
    candidato) > nombre ≥ umbral de escritura (60-84 = 'possible_duplicate' en conflicts, NO coincidencia). Un ticker
    sin MIC nunca resuelve."""
    ids = dict(ids or {})
    try:
        from core import entities
        if hasattr(entities, 'resolve_ids') and _is_current(view):
            return entities.resolve_ids(ids, name)
    except Exception:  # noqa: BLE001 — el resolvedor compartido falló: el de aquí da la misma respuesta
        pass
    from core import entities
    from core.import_normalize import yahoo_symbol_for
    ix = id_index(view)
    conflicts = []
    hits = []

    def hit(method, oid, score):
        if oid:
            hits.append((method, oid, score))
    if ids.get('lei'):
        hit('lei', ix.lei.get(str(ids['lei']).upper()), 100)
    for x in (ids.get('isin') or []) if isinstance(ids.get('isin'), list) else ([ids['isin']] if ids.get('isin') else []):
        hit('isin', ix.isin.get(str(x).upper()), 99)
    if ids.get('cik'):
        hit('cik', ix.cik.get(str(ids['cik']).zfill(10)), 99)
    if ids.get('qid') or ids.get('wikidata_qid'):
        hit('qid', ix.qid.get(str(ids.get('qid') or ids.get('wikidata_qid')).upper()), 99)
    for x in (ids.get('figi') or []) if isinstance(ids.get('figi'), list) else ([ids['figi']] if ids.get('figi') else []):
        hit('figi', ix.figi.get(str(x).upper()), 98)
    if ids.get('yahoo_symbol'):
        hit('yahoo_symbol', ix.yahoo.get(str(ids['yahoo_symbol']).upper()), 97)
    if ids.get('ticker') and ids.get('mic'):
        hit('ticker_mic', ix.ticker_mic.get((str(ids['ticker']).upper(), str(ids['mic']).upper())), 96)
        ys = yahoo_symbol_for(ids['ticker'], ids['mic'])
        if ys:
            hit('ticker_mic', ix.yahoo.get(ys), 96)
    best = None
    for method, oid, score in hits:
        if best is None:
            best = {'id': oid, 'method': method, 'score': score}
        elif oid != best['id']:
            conflicts.append({'kind': 'id_conflict', 'method': method, 'id': oid, 'vs': best['id']})
    if ids.get('domain'):
        cand = ix.domain.get(str(ids['domain']).lower())
        if cand and best is None:
            conflicts.append({'kind': 'domain_candidate', 'id': cand})
        elif cand and cand != best['id']:
            conflicts.append({'kind': 'domain_conflict', 'id': cand, 'vs': best['id']})
    if name:
        r = entities.resolve(name, umbral=policy('name_possible_threshold'))
        if r is not None and r['id'] in ix.ids:
            if r['score'] >= policy('name_write_threshold') and best is None:
                best = {'id': r['id'], 'method': 'name:' + r['method'], 'score': r['score']}
            elif best is not None and r['id'] != best['id']:
                conflicts.append({'kind': 'name_conflict', 'id': r['id'], 'score': r['score'], 'vs': best['id']})
            elif best is None:
                conflicts.append({'kind': 'possible_duplicate', 'id': r['id'], 'score': r['score'],
                                  'method': r['method']})
    if best is None:
        return {'id': None, 'method': None, 'score': 0, 'conflicts': conflicts} if conflicts else None
    best['conflicts'] = conflicts
    return best


def _suffix(sym):
    s = str(sym or '').strip().upper()
    return s.rsplit('.', 1)[1] if '.' in s else ''


def _base_symbol(sym):
    """'RTX.MX' → 'RTX'; 'BMW.DE' → 'BMW'; '7240.T' → '7240' (la misma acción en otra bolsa comparte la base)."""
    s = str(sym or '').strip().upper()
    if not s:
        return None
    return s.rsplit('.', 1)[0] if '.' in s else s


def _ids_of(model):
    ids = model.identity.ids
    out = {}
    if ids is not None:
        out = {k: v for k, v in ids.model_dump(exclude_none=True).items() if k != 'national_registry'}
        if 'wikidata_qid' in out:
            out['qid'] = out.pop('wikidata_qid')
        if 'exchange_mic' in out:
            out['mic'] = out.pop('exchange_mic')
    prim = next((l for l in (model.listings or []) if l.is_primary), None)
    if prim is not None:
        out.setdefault('yahoo_symbol', prim.yahoo_symbol)
        out.setdefault('ticker', prim.ticker)
        out.setdefault('mic', prim.exchange_mic)
        if prim.isin:
            out.setdefault('isin', [])
            if isinstance(out['isin'], list) and prim.isin not in out['isin']:
                out['isin'] = list(out['isin']) + [prim.isin]
    return out


def resolve_batch(valid, view=None):
    """[(dict, model)] → {record_id: {'action', 'id', 'method', 'score', 'conflicts', 'reason'}}. Puro (lee el grafo
    vigente). Dos fichas del lote que caen en la misma empresa: la segunda se omite (duplicate_in_batch)."""
    from core.import_normalize import is_khipus_id, khipus_id_from
    ix = id_index(view)
    out, taken, taken_ids = OrderedDict(), {}, set()
    nodes = view.by_id if view is not None else {}
    for rec, model in valid:
        rid = model.record_id
        ids = _ids_of(model)
        r = resolve_ids(ids, model.identity.short_name, view=view)
        hint = model.khipus_id_hint
        conflicts = list((r or {}).get('conflicts') or [])
        blocked = None            # candidato por nombre descartado: la pista (derivada del mismo nombre) tampoco vale
        if r is not None and r.get('id') and str(r.get('method') or '').startswith('name'):
            cand = r['id']
            if r['method'] == 'name:ticker':
                # el NOMBRE coincide con un ticker del catálogo (NOK = Nippon Mektron ≠ Nokia): no es una coincidencia
                conflicts.append({'kind': 'possible_duplicate', 'id': cand, 'score': r['score'], 'method': 'ticker'})
                r, blocked = None, cand
            else:
                mine, theirs = ids.get('yahoo_symbol'), (nodes.get(cand) or {}).get('mkt')
                if mine and theirs and _suffix(mine) == _suffix(theirs) and _base_symbol(mine) != _base_symbol(theirs):
                    # misma etiqueta pero OTRA acción en la MISMA bolsa (SoftBank Corp. 9434.T ≠ SoftBank Group 9984.T):
                    # es otra empresa. Con bolsas distintas (ADR vs. casa) no se puede saber: se fusiona y se lista.
                    conflicts.append({'kind': 'listing_mismatch', 'id': cand, 'score': r['score'], 'record_symbol': mine,
                                      'catalog_symbol': theirs})
                    r, blocked = None, cand
                elif mine and theirs and _base_symbol(mine) != _base_symbol(theirs):
                    from core.import_normalize import iso2_of
                    rec_hq = model.identity.hq_country.value
                    cat_hq = iso2_of((nodes.get(cand) or {}).get('country'))
                    if rec_hq and cat_hq and rec_hq != 'ZZ' and rec_hq != cat_hq:
                        # otra acción Y otra sede (MOL Hungría ≠ MOL Japón; SAIC EE.UU. ≠ SAIC Motor China): otra empresa
                        conflicts.append({'kind': 'country_mismatch', 'id': cand, 'score': r['score'], 'record_symbol': mine,
                                          'catalog_symbol': theirs, 'record_hq': rec_hq, 'catalog_hq': cat_hq})
                        r, blocked = None, cand
                    else:
                        conflicts.append({'kind': 'listing_differs', 'id': cand, 'record_symbol': mine, 'catalog_symbol': theirs})
        if r is not None and r.get('id'):
            cid, method, score = r['id'], r['method'], r['score']
            if hint and hint != cid and hint in ix.ids:
                conflicts.append({'kind': 'hint_mismatch', 'hint': hint, 'resolved': cid})
            action = 'merge'
        elif hint and hint in ix.ids and hint != blocked:
            cid, method, score, action = hint, 'hint', 90, 'merge'
        else:
            action, method, score = 'create', 'new', 0
            base = hint if (hint and is_khipus_id(hint) and hint not in ix.ids) else khipus_id_from(model.identity.short_name)
            cid = base
            n = 2
            while cid in ix.ids or cid in taken_ids:
                cid = f'{base}_{n}'
                n += 1
        entry = {'action': action, 'id': cid, 'method': method, 'score': score, 'conflicts': conflicts}
        if cid in taken:
            entry.update(action='skip', reason='duplicate_in_batch', duplicate_of=taken[cid])
        else:
            taken[cid] = rid
            taken_ids.add(cid)
        out[rid] = entry
    return out


# ── categorías ──────────────────────────────────────────────────────────────────────────────────────────────────
def graph_key(view):
    """Clave ESTABLE del grafo que vio el plan: fuente + versión + contenido del núcleo (el id de generación cambia
    con cada arranque del proceso; esta clave no: el mismo grafo en la terminal y en el servidor da la misma huella)."""
    core = getattr(view, 'core', None)
    sha = getattr(core, 'content_sha', None) if core is not None else None
    return f"{view.source}:g{view.graph_version}:{(sha or 'nocore')[:16]}"


def _catalog_cats(view):
    cats = dict(view.catalog.get('categories') or {}) if view is not None else {}
    c2s = dict(view.catalog.get('cat_to_sector') or {}) if view is not None else {}
    return cats, c2s


def nearest_category(cat_id, sector, cats, c2s):
    """Categoría EXISTENTE más parecida (misma sector + más palabras en común en el id; empate: la más usada en el
    catálogo, luego alfabético). Determinista. None si el sector no tiene categorías."""
    same = [c for c in cats if c2s.get(c) == sector]
    if not same:
        return None
    words = set(str(cat_id or '').split('_'))

    def score(c):
        return (-len(words & set(c.split('_'))), c)
    return sorted(same, key=score)[0]


# ── vínculos ────────────────────────────────────────────────────────────────────────────────────────────────────
def _best_evidence(evidence):
    """(source_url, trust, kind) de la evidencia con MÁS trust (empate: la primera citada)."""
    from ontology.provenance import source_trust
    best = None
    for e in evidence or []:
        t = source_trust(getattr(e, 'source_kind', None))
        if best is None or t > best[1]:
            best = (e.source_url, t, e.source_kind)
    return best or (None, 0, None)


def _source_entry(url, kind, title='', as_of=None):
    from ontology.provenance import publisher_from_url, source_id_for, source_trust
    sid = source_id_for(url)
    if not sid:
        return None
    return {'id': sid, 'url': url, 'kind': kind or 'corporate', 'trust': source_trust(kind or 'corporate'),
            'title': (title or '')[:200], 'publisher': publisher_from_url(url), 'as_of': as_of}


def _direction(this_id, other_id, rel_type, this_role):
    """Forma canónica "source PROVEE a target" a partir del papel de ESTA empresa."""
    if this_role in ('supplier', 'investor', 'owner', 'partner'):
        return this_id, other_id
    return other_id, this_id


def _route_link(rel, counterparty_id, counterparty_type, resolved_how, pol):
    """('live'|'proposed'|'pending'|'quarantine', motivo). Reglas F-5 e I-1 + lo que dice la ficha."""
    if counterparty_id is None:
        return 'pending', 'counterparty_unknown'
    if counterparty_type in (pol['quarantine_supplier_types'] or ()) and rel.rel_type in ('supply', 'fab', 'cloud',
                                                                                          'license', 'ppa', 'deploy') \
            and rel.this_role == 'customer':
        return 'quarantine', 'flow_supplier_type'
    _url, trust, _kind = _best_evidence(rel.evidence)
    if rel.status in (pol['proposal_statuses'] or ()):
        return 'proposed', f'status_{rel.status}'
    if resolved_how in ('name', 'possible'):
        return 'proposed', 'counterparty_by_name_only'
    if rel.confidence < float(pol['live_min_confidence']):
        return 'proposed', 'low_confidence'
    if trust < int(pol['live_min_trust']):
        return 'proposed', 'source_trust_low'
    return 'live', 'ok'


def _resolve_counterparty(cp, batch_ids, view):
    """(id, cómo) de la contraparte: khipus_id del grafo > record_id del lote > identificadores > nombre."""
    ix = id_index(view)
    if cp.khipus_id and cp.khipus_id in ix.ids:
        return cp.khipus_id, 'khipus_id'
    if cp.record_id and cp.record_id in batch_ids:
        return batch_ids[cp.record_id], 'record_id'
    ids = _counterparty_ids(cp)
    r = resolve_ids(ids, cp.name, view=view) if (ids or cp.name) else None
    if r and r.get('id'):
        return r['id'], ('name' if str(r['method']).startswith('name') else 'ids')
    return None, 'unknown'


def _counterparty_ids(cp):
    """Identificadores de la contraparte de una relación (dict plano: qid/mic normalizados), {} si no trae."""
    if cp is None or cp.ids is None:
        return {}
    ids = {k: v for k, v in cp.ids.model_dump(exclude_none=True).items() if k != 'national_registry'}
    if 'wikidata_qid' in ids:
        ids['qid'] = ids.pop('wikidata_qid')
    if 'exchange_mic' in ids:
        ids['mic'] = ids.pop('exchange_mic')
    return ids


def _counterparty_dict(cp, cp_id, cp_how):
    out = {'name': cp.name, 'id': cp_id, 'how': cp_how, 'object_type': cp.object_type or 'Company'}
    ids = _counterparty_ids(cp)
    if ids:
        out['ids'] = ids        # un vínculo PENDIENTE se vuelve a resolver con ellos (no solo por nombre)
    if cp.record_id:
        out['record_id'] = cp.record_id
    return out


def _link_spec(this_id, rec_id, rel, cp_id, cp_how, cp_type, pol):
    """Un vínculo listo para el plan: dirección canónica, peso = criticidad, fechas reales, fuentes, ruta."""
    from core.import_normalize import valid_from_of, valid_to_of
    route, reason = _route_link(rel, cp_id, cp_type, cp_how, pol)
    src, tgt = _direction(this_id, cp_id, rel.rel_type, rel.this_role) if cp_id else (None, None)
    url, trust, kind = _best_evidence(rel.evidence)
    sources = []
    for e in rel.evidence:
        s = _source_entry(e.source_url, e.source_kind, e.source_name or '', e.as_of)
        if s and s['id'] not in {x['id'] for x in sources}:
            sources.append(s)
    primary = _source_entry(url, kind) if url else None
    vf, known = valid_from_of(rel.start)
    dep = rel.dependency.model_dump(exclude_none=True)
    props = {
        'rel_label': rel.label_es, 'rel_label_en': rel.label_en, 'product': rel.product,
        'dependency': dep, 'status': rel.status, 'external_id': f'{rec_id}:{rel.relation_id}',
        'source': PROVENANCE, 'confidence': rel.confidence, 'verified': bool(trust >= int(pol['live_min_trust'])
                                                                             and rel.confidence >= float(pol['live_min_confidence'])),
        'evidenced_by': [s['id'] for s in sources], 'since': rel.start, 'until': rel.end,
        'this_role': rel.this_role, 'record_id': rec_id, 'relation_id': rel.relation_id,
    }
    props = {k: v for k, v in props.items() if v is not None}
    if route == 'proposed':
        # D-1: una PROPUESTA de verdad (status proposed, confianza 0 hasta que una persona confirme)
        props.update({'status': 'proposed', 'proposed': True, 'declared_status': rel.status,
                      'declared_confidence': rel.confidence, 'confidence': 0.0, 'proposed_reason': reason})
    weight = float(rel.dependency.criticality)
    return {'relation_id': rel.relation_id, 'record_id': rec_id, 'rel_type': rel.rel_type, 'source': src, 'target': tgt,
            'counterparty': _counterparty_dict(rel.counterparty, cp_id, cp_how),
            'weight': weight, 'properties': props, 'valid_from': vf, 'valid_from_known': known,
            'valid_to': valid_to_of(rel.end), 'source_id': primary['id'] if primary else None,
            'confidence': rel.confidence, 'route': route, 'reason': reason, 'sources': sources}


def _holding_links(this_id, rec_id, model, batch_ids, view, pol):
    """corporate.parent / subsidiaries / major_shareholders → owns (≥ owns_min_pct) o invest; siempre PROPUESTA si la
    contraparte se resolvió solo por nombre; pendiente si no existe."""
    from core.import_normalize import valid_from_of, valid_to_of
    out = []
    corp = model.corporate
    if corp is None:
        return out
    items = []
    for h in (corp.major_shareholders or []):
        items.append(('in', h))
    if corp.parent is not None:
        items.append(('in', corp.parent))
    for h in (corp.subsidiaries or []):
        items.append(('out', h))
    for n, (direction, h) in enumerate(items, 1):
        cp_id, how = _resolve_counterparty(h.entity, batch_ids, view)
        pct = float(h.pct.value)
        rel_type = 'owns' if pct >= float(pol['owns_min_pct']) else 'invest'
        src, tgt = ((cp_id, this_id) if direction == 'in' else (this_id, cp_id)) if cp_id else (None, None)
        s = _source_entry(h.pct.source_url, h.pct.source_kind, h.pct.source_name or '', h.pct.as_of)
        route = 'pending' if cp_id is None else ('proposed' if how == 'name' or float(h.pct.confidence) < float(
            pol['live_min_confidence']) or (s or {}).get('trust', 0) < int(pol['live_min_trust']) else 'live')
        vf, known = valid_from_of(h.since)
        props = {'rel_label': f'{"posee" if rel_type == "owns" else "participa en"} {pct:g} %',
                 'rel_label_en': f'{"owns" if rel_type == "owns" else "holds"} {pct:g}%', 'share_pct': pct,
                 'external_id': f'{rec_id}:holding-{n:03d}', 'source': PROVENANCE, 'confidence': float(h.pct.confidence),
                 'evidenced_by': [s['id']] if s else [], 'since': h.since, 'until': h.until, 'record_id': rec_id}
        props = {k: v for k, v in props.items() if v is not None}
        if route == 'proposed':
            props.update({'status': 'proposed', 'proposed': True, 'declared_confidence': float(h.pct.confidence),
                          'confidence': 0.0, 'proposed_reason': 'holding_unverified'})
        out.append({'relation_id': f'holding-{n:03d}', 'record_id': rec_id, 'rel_type': rel_type, 'source': src,
                    'target': tgt, 'counterparty': {'name': h.entity.name, 'id': cp_id, 'how': how,
                                                    'object_type': h.entity.object_type or 'Company'},
                    'weight': 1.0 if rel_type == 'invest' else max(1.0, min(6.0, round(pct / 100 * 6, 2))),
                    'properties': props, 'valid_from': vf, 'valid_from_known': known, 'valid_to': valid_to_of(h.until),
                    'source_id': s['id'] if s else None, 'confidence': float(h.pct.confidence), 'route': route,
                    'reason': 'ok' if route == 'live' else route, 'sources': [s] if s else []})
    return out


# ── propiedades del objeto Company ──────────────────────────────────────────────────────────────────────────────
def _fact(f):
    """Un fact → su value (None si no hay)."""
    return None if f is None else f.value


def _text_pair(f):
    """f_text_es → (es, en); el inglés marcado "[EN pendiente]" cuenta como ausente."""
    if f is None:
        return None, None
    en = f.value_en
    if en and en.startswith(_EN_PENDING):
        en = None
    return f.value, en


def company_props(model, rec, cid, cats, c2s, approved, pol, warnings):
    """Propiedades del objeto Company (contrato E2): catálogo (cat/sector/country/ticker/mkt/role…) + ids +
    listings + hq/incorporation (ISO-2) + market_position + facilities + texts + valuation (privadas) + verified +
    research_meta. `warnings` recibe los avisos de la ficha."""
    from core.import_normalize import catalog_key_of, exchange_label
    idn, cls, prof = model.identity, model.classification, model.profile
    hq = idn.hq_country.value
    props = {'imported': True, 'record_id': model.record_id, 'legal_name': idn.legal_name.value,
             'status': idn.status.value, 'hq_country': hq, 'country_iso2': hq, 'country': catalog_key_of(hq)}
    if hq == 'ZZ':                    # sede desconocida (código ISO de uso privado): sin país real, a revisar
        props.update({'hq_country': None, 'country_iso2': None, 'country': 'RestoMundo', 'hq_unknown': True})
        warnings.append({'code': 'hq_unknown', 'es': 'sede desconocida: se ubica en «Resto del mundo» hasta revisarla',
                         'en': 'unknown HQ: placed under "Rest of world" until reviewed'})
    if idn.incorporation_country is not None:
        props['incorporation_country'] = idn.incorporation_country.value
    if idn.founded is not None:
        props['founded'] = idn.founded.value
    if idn.website:
        props['website'] = idn.website
    if idn.hq_city is not None:
        props['hq_city'] = idn.hq_city.value
    if idn.hq_coords is not None:
        props['hq_coords'] = idn.hq_coords.model_dump(exclude_none=True)
    if idn.other_names:
        props['other_names'] = [o.model_dump(exclude_none=True) for o in idn.other_names]
        props['aliases'] = [o.name for o in idn.other_names]
    # categoría (un alias del catálogo —`battery_components`— cae en su id consolidado: data/categories.json)
    cat = cls.cat
    cat_prop = cls.cat_proposed.model_dump() if cls.cat_proposed is not None else None
    if cat not in cats:                  # también si viene en `approved`: un alias del catálogo nunca nace como categoría
        try:
            from ontology.vocabulary import resolve_category
            alias_of = resolve_category(cat)
        except Exception:  # noqa: BLE001
            alias_of = None
        if alias_of and alias_of in cats and alias_of != cat:
            props['cat_declared'] = cat
            cat = alias_of
            if cat_prop and cat_prop.get('id') not in cats:
                cat_prop = None          # la «nueva» ya existe fusionada en el catálogo: nada que aprobar
    if cat in cats:
        sector = c2s.get(cat)
    elif cat in approved:
        sector = approved[cat].get('sector')
        props['cat_approved_in_run'] = True
    else:
        sector = (cat_prop or {}).get('sector') or None
        near = nearest_category(cat, sector, cats, c2s) if sector else None
        if cat_prop is None:
            cat_prop = {'id': cat, 'label_es': cat, 'label_en': cat, 'sector': sector}
        warnings.append({'code': 'cat_unknown', 'cat': cat, 'nearest': near,
                         'es': f'categoría «{cat}» no está en el catálogo: se usa «{near}» y queda propuesta',
                         'en': f'category "{cat}" is not in the catalog: "{near}" is used and it stays proposed'})
        cat = near or cat
    props['cat'] = cat
    if sector:
        props['sector'] = sector
    if cat_prop:
        props['cat_proposed'] = cat_prop
    if cls.chain_layers:
        props['chain_layers'] = list(cls.chain_layers)
    if cls.cats_secondary:
        props['cats_secondary'] = list(cls.cats_secondary)
    if cls.naics:
        props['naics'] = cls.naics
    if cls.gics_industry:
        props['gics_industry'] = cls.gics_industry
    # identificadores y cotizaciones
    ids = {}
    if idn.ids is not None:
        d = idn.ids.model_dump(exclude_none=True)
        for k_src, k in (('lei', 'lei'), ('isin', 'isin'), ('cik', 'cik'), ('wikidata_qid', 'qid'), ('figi', 'figi'),
                         ('domain', 'domain'), ('yahoo_symbol', 'yahoo_symbol')):
            if d.get(k_src) is not None:
                ids[k] = d[k_src]
    listings = []
    primary = None
    for l in model.listings or []:
        d = l.model_dump(exclude_none=True)
        entry = {'symbol': d['ticker'], 'mic': d['exchange_mic'], 'yahoo_symbol': d['yahoo_symbol'],
                 'is_primary': bool(d['is_primary']), 'kind': d['kind'], 'currency': d['currency']}
        for k in ('isin', 'figi', 'ordinary_per_depositary', 'listed_since', 'delisted_at', 'share_class',
                  'finnhub_symbol', 'confidence'):
            if k in d:
                entry[k] = d[k]
        entry['exchange'] = exchange_label(d['exchange_mic'])
        listings.append(entry)
        if entry['is_primary'] and primary is None:
            primary = entry
    n_primary = sum(1 for l in listings if l['is_primary'])
    if n_primary > 1:
        warnings.append({'code': 'many_primary_listings', 'n': n_primary,
                         'es': f'{n_primary} cotizaciones marcadas como principal', 'en': f'{n_primary} listings marked primary'})
    if listings and primary is None:
        warnings.append({'code': 'no_primary_listing',
                         'es': 'cotiza pero ninguna cotización es la principal: sin precio en vivo hasta revisarla',
                         'en': 'listed but no listing is primary: no live price until reviewed'})
    if ids:
        props['ids'] = ids
    if listings:
        props['listings'] = listings
    if primary is not None:
        props['mkt'] = primary['yahoo_symbol']
        props['ticker'] = f"{primary['symbol']} · {primary['exchange']}"
        props['listing'] = {'symbol': primary['symbol'], 'mic': primary['mic'], 'yahoo_symbol': primary['yahoo_symbol'],
                            'currency': primary['currency'], 'kind': primary['kind']}
        if primary.get('isin'):
            ids.setdefault('isin', [])
            if isinstance(ids['isin'], list) and primary['isin'] not in ids['isin']:
                ids['isin'] = list(ids['isin']) + [primary['isin']]
            props['ids'] = ids
    # textos (catálogo + contrato `texts`)
    role_es, role_en = _text_pair(prof.summary)
    sup_es, sup_en = _text_pair(prof.what_it_supplies)
    moat_es, moat_en = _text_pair(prof.moat)
    growth_es, growth_en = _text_pair(prof.growth)
    risk_es, risk_en = _text_pair(prof.geo_risk)
    texts = {'role_es': role_es, 'role_en': role_en, 'supplies_es': sup_es, 'supplies_en': sup_en, 'moat_es': moat_es,
             'moat_en': moat_en, 'risk_es': risk_es, 'risk_en': risk_en, 'growth_es': growth_es, 'growth_en': growth_en}
    props['texts'] = texts
    for k_es, k_en, es, en in (('role', 'role_en', role_es, role_en), ('supplies', 'supplies_en', sup_es, sup_en),
                               ('moat', 'moat_en', moat_es, moat_en), ('growth', 'growth_en', growth_es, growth_en),
                               ('geo_risk', 'geo_risk_en', risk_es, risk_en)):
        if es:
            props[k_es] = es
        if en:
            props[k_en] = en
    if role_en is None:
        warnings.append({'code': 'en_missing', 'es': 'perfil sin traducción al inglés', 'en': 'profile without English text'})
    desc_es, desc_en = _text_pair(prof.description)
    if desc_es:
        props['desc'] = desc_es
    if desc_en:
        props['desc_en'] = desc_en
    if prof.employees is not None:
        props['employees'] = int(prof.employees.value)
    if prof.technologies:
        props['technologies'] = list(prof.technologies)
    if prof.key_people:
        props['key_people'] = [k.model_dump(exclude_none=True) for k in prof.key_people]
    # mercado, plantas, productos, exposición, regulación, riesgos, línea de tiempo (con su procedencia)
    if model.market_position:
        props['market_position'] = [m.model_dump(exclude_none=True) for m in model.market_position]
    if model.facilities:
        props['facilities'] = [f.model_dump(exclude_none=True) for f in model.facilities]
    if model.products:
        props['products'] = [p.model_dump(exclude_none=True) for p in model.products]
    if model.exposure is not None:
        props['exposure'] = model.exposure.model_dump(exclude_none=True)
    if model.regulatory is not None:
        props['regulatory'] = model.regulatory.model_dump(exclude_none=True)
    if model.risks:
        props['risks'] = [r.model_dump(exclude_none=True) for r in model.risks]
    if model.timeline:
        props['timeline'] = [t.model_dump(exclude_none=True) for t in model.timeline]
    if model.financials is not None:
        props['financials'] = model.financials.model_dump(exclude_none=True)
        ann = model.financials.annual or []
        last = max(ann, key=lambda a: a.fiscal_year) if ann else None
        if last is not None and last.gross_margin_pct is not None:
            from core.import_normalize import pct
            props['margin'] = pct(last.gross_margin_pct.value)
    if model.innovation is not None:
        props['innovation'] = model.innovation.model_dump(exclude_none=True)
    if model.esg is not None:
        props['esg'] = model.esg.model_dump(exclude_none=True)
    if model.live_hooks is not None:
        props['live_hooks'] = model.live_hooks.model_dump(exclude_none=True)
    # valuación SOLO de privadas (última ronda cerrada con valuación post-money)
    if idn.status.value in ('private', 'subsidiary', 'state_owned', 'cooperative') and model.funding:
        closed = [f for f in model.funding if f.post_money_valuation is not None and (f.status or 'closed') == 'closed']
        if closed:
            last = max(closed, key=lambda f: f.date)
            props['valuation'] = {'value': last.post_money_valuation, 'currency': last.currency or 'USD',
                                  'as_of': last.date, 'source_url': last.source_url, 'round': last.round,
                                  'confidence': last.confidence}
            props['preipo'] = True
    if model.funding:
        props['funding'] = [f.model_dump(exclude_none=True) for f in model.funding]
    # verificación y meta
    rm = model.research_meta
    verified = bool(idn.legal_name.confidence >= float(pol['live_min_confidence']))
    props['verified'] = verified
    props['research_meta'] = {'batch': rm.batch, 'priority': rm.priority, 'tier': rm.tier, 'researcher': rm.researcher,
                              'researched_at': rm.researched_at.isoformat(), 'revision': rm.revision or 1,
                              'method': rm.method, 'not_found': list(rm.not_found or [])}
    if rm.notes:
        props['research_meta']['notes'] = rm.notes
    return {k: v for k, v in props.items() if v is not None}


def _record_sources(model):
    """Todas las fuentes citadas por la ficha (facts + evidencias) → [{id,url,kind,trust,title,publisher}] sin
    repetir. Recorre el dict exportado buscando pares source_url/source_kind."""
    out = {}

    def walk(x):
        if isinstance(x, dict):
            u = x.get('source_url')
            if isinstance(u, str) and u.startswith('http'):
                s = _source_entry(u, x.get('source_kind'), x.get('source_name') or '', x.get('as_of'))
                if s and s['id'] not in out:
                    out[s['id']] = s
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(model.model_dump(exclude_none=True, by_alias=True))
    return list(out.values())


# ── el plan ─────────────────────────────────────────────────────────────────────────────────────────────────────
def plan(records, updates=None, *, view=None, batch=None, approve_categories=None, pending=None, what_changes=True):
    """PURO: no escribe nada. Devuelve el plan (qué se crea / fusiona / actualiza / omite y por qué; categorías por
    aprobar; vínculos por ruta; fuentes nuevas; "¿qué cambia?" del kernel) con `plan_sha` (huella de lo que se
    aplicaría sobre ESTA generación del grafo). `records` = fichas (dicts); `updates` = [{khipus_id, props, source}]
    para empresas existentes (p. ej. países verificados); `approve_categories` = [{id,label_es,label_en,sector}] que
    Fabrizio aprueba en este lote (F-8); `pending` = filas de import_pending_links (dicts) a reintentar."""
    from core.hotviews import hot
    view = view or hot.graph()
    if view is None:
        raise ImportProblem('grafo no disponible', 'graph unavailable', 'graph_unavailable')
    t0 = time.perf_counter()
    pol = policy()
    cats, c2s = _catalog_cats(view)
    approved = {c['id']: c for c in (approve_categories or []) if isinstance(c, dict) and c.get('id')}
    ix = id_index(view)
    valid, invalid = validate_batch(records or [])
    if len(valid) > int(pol['max_records_per_run']):
        raise ImportProblem(f'el lote trae {len(valid)} fichas; el máximo por corrida es {pol["max_records_per_run"]}',
                            f'the batch has {len(valid)} records; the maximum per run is {pol["max_records_per_run"]}',
                            'batch_too_large')
    res = resolve_batch(valid, view=view)
    batch_ids = {rid: r['id'] for rid, r in res.items() if r['action'] != 'skip'}
    items, sources, cat_to_approve = [], OrderedDict(), OrderedDict()
    counts = Counter()
    link_counts = Counter()
    for rec, model in valid:
        rid = model.record_id
        r = res[rid]
        warnings = []
        item = {'record_id': rid, 'name': model.identity.short_name, 'action': r['action'], 'id': r['id'],
                'method': r['method'], 'score': r['score'], 'conflicts': list(r['conflicts']), 'priority':
                model.research_meta.priority, 'tier': model.research_meta.tier, 'warnings': warnings, 'links': []}
        if r['action'] == 'skip':
            item['reason'] = r.get('reason')
            item['duplicate_of'] = r.get('duplicate_of')
            counts['skip'] += 1
            items.append(item)
            continue
        props = company_props(model, rec, r['id'], cats, c2s, approved, pol, warnings)
        if props.get('cat_proposed') and props['cat'] != props['cat_proposed'].get('id'):
            cp = props['cat_proposed']
            e = cat_to_approve.setdefault(cp['id'], {**cp, 'n': 0, 'examples': []})
            e['n'] += 1
            if len(e['examples']) < 3:
                e['examples'].append(model.identity.short_name)
        if r['action'] == 'merge':
            cur = view.by_id.get(r['id']) or {}
            add, conflicts = {}, []
            for k, v in props.items():
                if k in ('imported', 'record_id'):
                    add[k] = v
                    continue
                if k not in cur or cur.get(k) in (None, '', [], {}):
                    add[k] = v
                elif k in _CURATED_KEYS:
                    if k == 'country':
                        from core.import_normalize import iso2_of
                        same = iso2_of(cur.get(k)) is not None and iso2_of(cur.get(k)) == iso2_of(v)
                    else:
                        same = cur.get(k) == v
                    if not same:
                        conflicts.append({'kind': 'curated_differs', 'key': k, 'current': _short(cur.get(k)),
                                          'proposed': _short(v)})
                elif cur.get(k) != v and k in ('ids', 'listings', 'texts'):
                    add[k] = _merge_nested(k, cur.get(k), v, conflicts)
                elif cur.get(k) != v:
                    conflicts.append({'kind': 'value_differs', 'key': k, 'current': _short(cur.get(k)),
                                      'proposed': _short(v)})
            if 'listings' in add and cur.get('mkt'):
                # la empresa ya tiene su cotización principal (curada): lo que trae la ficha entra como SECUNDARIA
                add['listings'] = [dict(l, is_primary=(l.get('yahoo_symbol') == cur.get('mkt'))) for l in add['listings']]
                if any(l.get('is_primary') for l in props.get('listings') or []) and not any(l['is_primary'] for l in add['listings']):
                    warnings.append({'code': 'listing_added_secondary',
                                     'es': f"cotización {props['listings'][0]['yahoo_symbol']} entra como secundaria: la principal sigue siendo {cur.get('mkt')}",
                                     'en': f"listing {props['listings'][0]['yahoo_symbol']} enters as secondary: primary stays {cur.get('mkt')}"})
            add.pop('listing', None)
            if cur.get('mkt'):
                warnings[:] = [w for w in warnings if w.get('code') != 'no_primary_listing']
            item['conflicts'] += conflicts
            item['props'] = add
            item['label'] = cur.get('label') or model.identity.short_name
            counts['merge'] += 1
        else:
            item['props'] = props
            item['label'] = model.identity.short_name
            counts['create'] += 1
            lst = props.get('listings') or []
            if lst and not any(l.get('is_primary') for l in lst) and not any(
                    c.get('kind') == 'possible_duplicate' for c in item['conflicts']):
                # solo cotiza por certificados (GDR/ADR/CEDEAR): suele ser una empresa que YA existe con otro nombre
                item['conflicts'].append({'kind': 'possible_duplicate', 'id': None, 'score': 0,
                                          'method': 'only_depositary_listing'})
        item['founded'] = _fact(model.identity.founded)
        # fuentes de la ficha
        rec_sources = _record_sources(model)
        item['sources'] = [s['id'] for s in rec_sources]
        for s in rec_sources:
            sources.setdefault(s['id'], s)
        # vínculos
        this_id = r['id']
        for rel in model.relations or []:
            cp_id, how = _resolve_counterparty(rel.counterparty, batch_ids, view)
            cp_type = rel.counterparty.object_type or 'Company'
            if cp_id is not None and cp_id in ix.ids:
                cp_type = (view.by_id.get(cp_id) or {}).get('type') or cp_type
            if cp_id == this_id:
                spec = {'relation_id': rel.relation_id, 'record_id': rid, 'rel_type': rel.rel_type, 'route': 'quarantine',
                        'reason': 'self_link', 'counterparty': {'name': rel.counterparty.name, 'id': cp_id}}
            else:
                spec = _link_spec(this_id, rid, rel, cp_id, how, cp_type, pol)
            for s in spec.get('sources') or []:
                sources.setdefault(s['id'], s)
            spec.pop('sources', None)
            item['links'].append(spec)
            link_counts[spec['route']] += 1
        for spec in _holding_links(this_id, rid, model, batch_ids, view, pol):
            for s in spec.get('sources') or []:
                sources.setdefault(s['id'], s)
            spec.pop('sources', None)
            item['links'].append(spec)
            link_counts[spec['route']] += 1
        items.append(item)
    # actualizaciones de empresas existentes (p. ej. países verificados del lote 1)
    upd_items = []
    for u in updates or []:
        if not isinstance(u, dict) or not u.get('khipus_id'):
            continue
        oid = view.canonical(u['khipus_id'])
        cur = view.by_id.get(oid)
        if cur is None:
            upd_items.append({'khipus_id': u['khipus_id'], 'action': 'skip', 'reason': 'not_in_graph', 'props': {}})
            counts['skip'] += 1
            continue
        add, conflicts = {}, []
        for k, v in (u.get('props') or {}).items():
            if k not in cur or cur.get(k) in (None, ''):
                add[k] = v
            elif cur.get(k) != v:
                conflicts.append({'kind': 'value_differs', 'key': k, 'current': _short(cur.get(k)), 'proposed': _short(v)})
        src = u.get('source') if isinstance(u.get('source'), dict) else None
        sid = None
        if src and src.get('url'):
            s = _source_entry(src['url'], src.get('kind'), src.get('title') or '', src.get('as_of'))
            if s:
                sources.setdefault(s['id'], s)
                sid = s['id']
        if add:
            add['country_facts'] = {k: {'value': v, 'source_id': sid, 'method': (src or {}).get('method') or u.get('method'),
                                        'confidence': (src or {}).get('confidence'), 'quote': (src or {}).get('quote'),
                                        'as_of': (src or {}).get('as_of')}
                                    for k, v in add.items() if k in ('hq_country', 'incorporation_country', 'country_iso2')}
        upd_items.append({'khipus_id': oid, 'label': cur.get('label') or oid, 'action': 'update' if add else 'skip',
                          'reason': None if add else 'nothing_new', 'props': add, 'conflicts': conflicts,
                          'source_id': sid, 'confidence': (src or {}).get('confidence')})
        counts['update' if add else 'skip'] += 1
    # pendientes de corridas anteriores que ahora resuelven: contra el grafo O contra la contraparte que llega en
    # ESTE lote (por record_id, identificadores o nombre). pending_links() ya excluye los consumidos.
    pend_items = []
    from core.entities import norm as _norm
    batch_by_name = {}
    batch_by_ids = {}
    for rec, model in valid:
        rid = model.record_id
        if rid not in batch_ids:
            continue
        batch_by_name.setdefault(_norm(model.identity.short_name), batch_ids[rid])
        for k, v in _ids_of(model).items():
            for x in (v if isinstance(v, list) else [v]):
                if k in ('lei', 'isin', 'cik', 'qid', 'figi', 'yahoo_symbol') and x:
                    batch_by_ids.setdefault((k, str(x).upper()), batch_ids[rid])
    for p in pending or []:
        cp = p.get('counterparty') or {}
        if not cp:
            continue
        r = resolve_ids(cp.get('ids') or {}, cp.get('name'), view=view)
        cid = (r or {}).get('id') if r else None
        method = str((r or {}).get('method') or '')
        if cid is None and cp.get('record_id') and cp['record_id'] in batch_ids:
            cid, method = batch_ids[cp['record_id']], 'record_id'
        if cid is None:
            for k, v in (cp.get('ids') or {}).items():
                for x in (v if isinstance(v, list) else [v]):
                    hit = batch_by_ids.get((k, str(x).upper())) if x else None
                    if hit:
                        cid, method = hit, k
                        break
                if cid:
                    break
        if cid is None and cp.get('name') and _norm(cp['name']) in batch_by_name:
            cid, method = batch_by_name[_norm(cp['name'])], 'name:batch'
        if cid is None or cid == p.get('company_id'):
            continue
        pl = dict(p.get('payload') or {})
        role = (pl.get('properties') or {}).get('this_role')
        src, tgt = _direction(p['company_id'], cid, pl.get('rel_type'), role or 'supplier')
        pl.update(source=src, target=tgt, route='live' if not method.startswith('name') else 'proposed',
                  reason='pending_resolved', from_pending=str(p.get('id')))
        pend_items.append(pl)
        link_counts[pl['route']] += 1
    new_sources = [s for sid, s in sources.items() if sid not in ix.ids]
    out = {
        'schema': PLAN_SCHEMA, 'batch': batch, 'generation': view.generation, 'graph_key': graph_key(view),
        'graph_version': view.graph_version, 'graph_source': view.source, 'policy': pol,
        'counts': {'records': len(records or []), 'valid': len(valid), 'invalid': len(invalid),
                   'create': counts['create'], 'merge': counts['merge'], 'update': counts['update'],
                   'skip': counts['skip'], 'links': {k: link_counts.get(k, 0) for k in ROUTES},
                   'sources_new': len(new_sources), 'categories_to_approve': len(cat_to_approve)},
        'items': items, 'updates': upd_items, 'pending_resolved': pend_items, 'invalid': invalid,
        'sources': new_sources, 'categories': {'to_approve': list(cat_to_approve.values()),
                                               'approved_now': sorted(approved)},
    }
    out['counts']['events_estimated'] = _events_estimate(out)
    out['plan_sha'] = plan_sha(out)
    if what_changes:
        try:
            out['what_changes'] = kernel_what_changes(view, out)
        except Exception as e:  # noqa: BLE001 — el "¿qué cambia?" nunca impide ver el plan
            out['what_changes'] = {'error': f'{type(e).__name__}: {str(e)[:160]}'}
    out['built_at'] = _now().isoformat()
    out['build_ms'] = round((time.perf_counter() - t0) * 1000, 1)
    return out


def _short(v):
    s = v if isinstance(v, (int, float, bool)) or v is None else (v if isinstance(v, str) else _canon(v))
    return s if not isinstance(s, str) or len(s) <= 160 else s[:157] + '…'


def _merge_nested(key, cur, new, conflicts):
    """ids/listings/texts de una fusión: se AÑADE lo que falta, lo que difiere se lista."""
    if key == 'ids' and isinstance(cur, dict) and isinstance(new, dict):
        out = dict(cur)
        for k, v in new.items():
            if k not in out or out[k] in (None, '', []):
                out[k] = v
            elif isinstance(out[k], list) and isinstance(v, list):
                out[k] = list(out[k]) + [x for x in v if x not in out[k]]
            elif out[k] != v:
                conflicts.append({'kind': 'id_differs', 'key': f'ids.{k}', 'current': _short(out[k]), 'proposed': _short(v)})
        return out
    if key == 'listings' and isinstance(cur, list) and isinstance(new, list):
        have = {(l.get('symbol'), l.get('mic')) for l in cur if isinstance(l, dict)}
        return list(cur) + [l for l in new if (l.get('symbol'), l.get('mic')) not in have]
    if key == 'texts' and isinstance(cur, dict) and isinstance(new, dict):
        out = dict(cur)
        for k, v in new.items():
            if not out.get(k) and v:
                out[k] = v
        return out
    return cur


def _events_estimate(p):
    n = len(p['sources'])
    for it in p['items']:
        if it['action'] in ('create', 'merge'):
            n += 1 + sum(1 for l in it['links'] if l['route'] in ('live', 'proposed'))
    n += sum(1 for u in p['updates'] if u['action'] == 'update')
    n += len(p.get('pending_resolved') or [])
    return n


def plan_sha(p):
    """Huella de lo que SE APLICARÍA: ítems, actualizaciones, fuentes, categorías, política y generación del grafo
    (otro grafo = otra huella → 409 al aplicar)."""
    body = {k: p.get(k) for k in ('items', 'updates', 'pending_resolved', 'sources', 'categories', 'policy', 'graph_key',
                                  'batch', 'invalid')}
    return _sha(body)


# ── "¿qué cambia?" (E2.6): el MISMO kernel sobre una copia en memoria ─────────────────────────────────────────
def kernel_what_changes(view, p):
    """ρ, top-20 de cuellos de botella y a cuántas empresas golpea TSMC, ANTES (la vista Impact publicada) y DESPUÉS
    (los nodos + vínculos vivos del plan sobre una copia de las matrices; propagate_many, el mismo kernel). Un lote
    vacío → antes == después. Avisa que kernel.calibration queda viejo si entran vínculos vivos."""
    import numpy as np
    from matrix import engine as E
    core = view.core
    imp = view.impact
    if core is None or imp is None:
        return {'available': False, 'reason': 'views_not_ready'}
    t0 = time.perf_counter()
    new_ids = sorted({it['id'] for it in p['items'] if it['action'] == 'create'})
    new_triples = []
    for it in p['items']:
        if it['action'] not in ('create', 'merge'):
            continue
        for l in it['links']:
            if l['route'] != 'live' or not l.get('source') or not l.get('target'):
                continue
            props = l.get('properties') or {}
            new_triples.append((l['source'], l['target'], l['rel_type'],
                                E._eff_weight(l['weight'], props.get('source'), E.link_confidence(props))))
    for l in p.get('pending_resolved') or []:
        if l.get('route') == 'live':
            props = l.get('properties') or {}
            new_triples.append((l['source'], l['target'], l['rel_type'],
                                E._eff_weight(l.get('weight'), props.get('source'), E.link_confidence(props))))
    before = {
        'nodes': len(core.ids), 'links': int(core.n_links), 'rho': (core.rho or {}).get('rho') if isinstance(core.rho, dict) else None,
        'damping_rho': (core.rho or {}).get('damping_rho') if isinstance(core.rho, dict) else None,
        'tsmc_hit': (imp.stats.get(TSMC_ID) or {}).get('reach_1'),
        'chokepoints': [{'id': k, 'reach_1': imp.stats[k]['reach_1'], 'sum_impact': imp.stats[k]['sum_impact']}
                        for k in (imp.by_sum if E._P('chokepoint_rank_by', 'count') == 'sum' else imp.by_count)[:CHOKEPOINTS_TOP]],
    }
    if not new_ids and not new_triples:
        after = dict(before)
        return {'available': True, 'identical': True, 'before': before, 'after': after, 'added_nodes': 0,
                'added_links': 0, 'calibration_stale': False, 'ms': round((time.perf_counter() - t0) * 1000, 1),
                'note_es': 'lote sin nodos ni vínculos nuevos: el kernel no cambia',
                'note_en': 'batch with no new nodes or links: the kernel does not change'}
    ids = list(core.ids) + [i for i in new_ids if i not in core.idx]
    idx = {oid: i for i, oid in enumerate(ids)}
    triples = []
    for rel, m in core.mats.items():
        coo = m.tocoo() if hasattr(m, 'tocoo') else None
        if coo is not None:
            for i, j, w in zip(coo.row.tolist(), coo.col.tolist(), coo.data.tolist()):
                triples.append((core.ids[i], core.ids[j], rel, w))
        else:
            nz = np.nonzero(m)
            for i, j in zip(nz[0].tolist(), nz[1].tolist()):
                triples.append((core.ids[i], core.ids[j], rel, float(m[i, j])))
    triples += [t for t in new_triples if t[0] in idx and t[1] in idx]
    mats, _idx, ids2 = E.build_matrices_from_triples(triples, idx, sparse=None)
    frag = E.fragility(idx, core.factors)
    dt = E.dependency_transpose(mats)
    agg = None
    for m in mats.values():
        agg = m.copy() if agg is None else agg + m
    out_w, in_w = E._rowsum(agg), E._colsum(agg)
    sources = [oid for oid, i in idx.items() if not (out_w[i] == 0 and in_w[i] == 0)]
    res = E.propagate_many(mats, idx, ids2, sources, frag=frag, dt=dt)
    stats = {}
    for oid in sources:
        impacts, _hops = res[oid]
        others = [v for k, v in impacts.items() if k != oid]
        stats[oid] = {'reach_1': max(0, sum(1 for v in impacts.values() if v >= 1.0) - 1),
                      'sum_impact': round(sum(others) / 100.0, 4)}
    by_sum = sorted(sources, key=lambda k: (-stats[k]['sum_impact'], -stats[k]['reach_1'], k))
    by_count = sorted(sources, key=lambda k: (-stats[k]['reach_1'], -stats[k]['sum_impact'], k))
    try:
        rho = E.spectral_radius(mats, factors=core.factors, idx=idx)
    except Exception:  # noqa: BLE001
        rho = {}
    after = {
        'nodes': len(ids), 'links': len(triples), 'rho': rho.get('rho'), 'damping_rho': rho.get('damping_rho'),
        'tsmc_hit': (stats.get(TSMC_ID) or {}).get('reach_1'),
        'chokepoints': [{'id': k, 'reach_1': stats[k]['reach_1'], 'sum_impact': stats[k]['sum_impact']}
                        for k in (by_sum if E._P('chokepoint_rank_by', 'count') == 'sum' else by_count)[:CHOKEPOINTS_TOP]],
    }
    stale = bool(new_triples)
    return {'available': True, 'identical': False, 'before': before, 'after': after, 'added_nodes': len(new_ids),
            'added_links': len(new_triples), 'calibration_stale': stale,
            'ms': round((time.perf_counter() - t0) * 1000, 1),
            'note_es': ('entran vínculos vivos: kernel.calibration (escenario → dinero) queda VIEJO; recalibrar tras aplicar'
                        if stale else 'solo entran empresas sin vínculos vivos: ρ y los cuellos de botella no cambian'),
            'note_en': ('live links enter: kernel.calibration (scenario → money) becomes STALE; recalibrate after applying'
                        if stale else 'only companies without live links enter: ρ and chokepoints do not change')}


# ── foco de la puerta G-IMPORT (governance/shapes/company.ttl, sombra) ──────────────────────────────────────────
def import_triples(item, pol=None):
    """(tripletas, foco) de UN ítem del plan para `ontology.g_import`: la ficha `a kh:ImportRecord` y cada vínculo
    `a kh:ImportRelation`. Solo propiedades derivadas (la forma no repite números de política: entran como literales)."""
    from core.gates import focus as F
    pol = pol or policy()
    t = F._T()
    R = F.node('import', item['record_id'])
    t.add(R, F.TYPE, F.kh('ImportRecord'))
    t.add(R, F.kh('recordId'), str(item['record_id']))
    t.add(R, F.kh('action'), str(item['action']))
    t.add(R, F.kh('schemaValid'), bool(item.get('schema_valid', True)))   # un ítem del plan ya validó; False solo en pruebas
    props = item.get('props') or {}
    codes = {w.get('code') for w in item.get('warnings') or []}
    hq = props.get('hq_country') or item.get('hq_country') or ('ZZ' if 'hq_unknown' in codes else '')
    t.add(R, F.kh('hqCountry'), str(hq))
    t.add(R, F.kh('hqKnown'), bool(hq and hq != 'ZZ'))
    t.add(R, F.kh('catKnown'), 'cat_unknown' not in codes)
    t.add(R, F.kh('summaryEn'), 'en_missing' not in codes)
    t.add(R, F.kh('primaryListings'), F.num(sum(1 for l in props.get('listings') or [] if l.get('is_primary'))))
    verified = props.get('verified')
    conf = (props.get('research_meta') or {}).get('confidence')
    t.add(R, F.kh('unverifiedHighConf'), bool(verified is False and conf is not None and conf > float(pol['unverified_confidence'])))
    t.add(R, F.kh('possibleDuplicate'), any(c.get('kind') == 'possible_duplicate' for c in item.get('conflicts') or []))
    from ontology.company_schema import FORBIDDEN_KEYS
    t.add(R, F.kh('forbiddenKeys'), F.num(sum(1 for k in props if k in FORBIDDEN_KEYS)))
    for l in item.get('links') or []:
        L = F.node('importrel', f"{item['record_id']}:{l.get('relation_id')}")
        t.add(L, F.TYPE, F.kh('ImportRelation'))
        t.add(L, F.kh('record'), R)
        t.add(L, F.kh('relType'), str(l.get('rel_type')))
        t.add(L, F.kh('route'), str(l.get('route')))
        dep = (l.get('properties') or {}).get('dependency') or {}
        if 'criticality' in dep:
            t.add(L, F.kh('criticality'), F.num(dep.get('criticality')))
        t.add(L, F.kh('confidence'), F.num(l.get('confidence')))
        t.add(L, F.kh('liveMinConf'), F.num(pol['live_min_confidence']))
        t.add(L, F.kh('liveMinTrust'), F.num(pol['live_min_trust']))
        t.add(L, F.kh('counterpartyResolved'), l.get('route') != 'pending')
        t.add(L, F.kh('liveWithoutTrust'), bool(l.get('route') == 'live' and not (l.get('properties') or {}).get('verified')))
        if l.get('rel_type') == 'owns':
            sp = (l.get('properties') or {}).get('share_pct')
            if sp is not None:
                t.add(L, F.kh('ownsSharePct'), F.num(sp))
                t.add(L, F.kh('ownsMinPct'), F.num(pol['owns_min_pct']))
    return list(t), R


def gate_plan(items, session=None):
    """G-IMPORT en bloque (sombra): un reporte para todos los ítems, registrado en la decisión en curso."""
    try:
        import core.gates as _gates
        from core.gates import report as _gr
        pol = policy()
        triples = []
        for it in items:
            if it.get('action') in ('create', 'merge'):
                t, _f = import_triples(it, pol)
                triples += t
        if not triples:
            return None
        rep = _gates.evaluate('ontology.g_import', list(dict.fromkeys(triples)), None)
        if rep is None:
            return None
        _gr.record(rep, session=session)
        if _gates.blocks(rep):
            raise _gates.GateViolation(rep)
        return {'mode': rep['mode'], 'outcome': rep['outcome'], 'checked': len(items), 'by_rule': _gr.by_rule_of(rep),
                'truncated': rep.get('truncated', 0), 'latency_us': rep.get('latency_us')}
    except Exception as e:  # noqa: BLE001
        if getattr(e, 'code', None) == 'gate_violation':
            raise
        return None


# ── eventos del plan (determinista) ─────────────────────────────────────────────────────────────────────────────
def events_of(p, run_id, revive_ids=None):
    """El plan → la lista de eventos que apply_run escribe (en este orden): fuentes nuevas, empresas (crear/fusionar),
    actualizaciones, vínculos vivos y propuestos, pendientes resueltos. Y aparte los vínculos PENDIENTES (filas de
    import_pending_links) y las cuarentenas (solo en el resumen). `revive_ids` = ids del plan ('create') que existen
    en la base RETIRADOS (una corrida deshecha): su ObjectCreated trae retired=False/merged_into=None/rollback_run=None
    para que vuelvan a ser visibles (el camino rápido fusiona sobre el objeto que ya existe)."""
    from ontology.provenance import SOURCE_TYPE
    from ontology.service import GENESIS_SENTINEL
    revive_ids = set(revive_ids or ())
    evs, pend, quar = [], [], []
    for s in p['sources']:
        evs.append({'event_type': 'ObjectCreated', 'object_id': s['id'], 'payload': {
            'label': (s.get('title') or s.get('publisher') or s['url'])[:200], 'type': SOURCE_TYPE,
            'properties': {'url': s['url'], 'kind': s['kind'], 'trust': s['trust'], 'title': s.get('title') or '',
                           'publisher': s.get('publisher') or '', 'published_at': s.get('as_of') or '',
                           'retrieved_at': '', 'extractor': 'company_import', 'raw_ref': ''}},
            'valid_from': GENESIS_SENTINEL, 'kind': 'source'})
    for it in p['items']:
        if it['action'] == 'skip':
            continue
        founded = it.get('founded')
        vf = GENESIS_SENTINEL
        if founded:
            from core.import_normalize import partial_date
            pd = partial_date(founded)
            if pd:
                vf = pd[0].isoformat()
        primary_src = it['sources'][0] if it.get('sources') else None
        if it['action'] == 'create':
            props = dict(it['props'], import_run=run_id)
            if it['id'] in revive_ids:
                props.update(retired=False, merged_into=None, rollback_run=None, retired_razon=None)
            evs.append({'event_type': 'ObjectCreated', 'object_id': it['id'],
                        'payload': {'label': it['label'], 'type': 'Company', 'properties': props,
                                    **({'revives': True} if it['id'] in revive_ids else {})},
                        'valid_from': vf, 'source_id': primary_src, 'kind': 'company_create',
                        'record_id': it['record_id']})
        else:
            if it['props']:
                evs.append({'event_type': 'ObjectUpdated', 'object_id': it['id'],
                            'payload': {'properties': dict(it['props'], import_run=run_id),
                                        'properties_prev': None, 'merge_from_record': it['record_id']},
                            'valid_from': _now().isoformat(), 'source_id': primary_src, 'kind': 'company_merge',
                            'record_id': it['record_id']})
        for l in it['links']:
            if l['route'] == 'quarantine':
                quar.append(l)
            elif l['route'] == 'pending':
                pend.append({'record_id': it['record_id'], 'relation_id': l['relation_id'], 'company_id': it['id'],
                             'counterparty': l.get('counterparty'), 'payload': {k: v for k, v in l.items() if k != 'counterparty'},
                             'reason': l.get('reason') or 'counterparty_unknown'})
            else:
                evs.append({'event_type': 'LinkCreated', 'object_id': l['source'], 'target_id': l['target'],
                            'payload': {'rel_type': l['rel_type'], 'weight': l['weight'],
                                        'properties': dict(l['properties'], import_run=run_id)},
                            'valid_from': l['valid_from'], 'valid_to': l.get('valid_to'), 'source_id': l.get('source_id'),
                            'confidence': l.get('properties', {}).get('confidence', l.get('confidence')), 'kind': 'link'})
    for u in p['updates']:
        if u['action'] != 'update':
            continue
        evs.append({'event_type': 'ObjectUpdated', 'object_id': u['khipus_id'],
                    'payload': {'properties': dict(u['props'], import_run=run_id), 'properties_prev': None,
                                'update_kind': 'country_facts'},
                    'valid_from': _now().isoformat(), 'source_id': u.get('source_id'), 'confidence': u.get('confidence'),
                    'kind': 'update'})
    for l in p.get('pending_resolved') or []:
        evs.append({'event_type': 'LinkCreated', 'object_id': l['source'], 'target_id': l['target'],
                    'payload': {'rel_type': l['rel_type'], 'weight': l['weight'],
                                'properties': dict(l.get('properties') or {}, import_run=run_id, from_pending=l.get('from_pending'))},
                    'valid_from': l['valid_from'], 'valid_to': l.get('valid_to'), 'source_id': l.get('source_id'),
                    'confidence': (l.get('properties') or {}).get('confidence', l.get('confidence')), 'kind': 'link'})
    return evs, pend, quar


# ── aplicar ─────────────────────────────────────────────────────────────────────────────────────────────────────
def new_run_id():
    return _now().strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:6]


def _who(principal):
    if principal is not None:
        return principal
    from core import identity
    return identity.system('import_cli')


def _rej_status(exc):
    """Qué estado deja la decisión si la acción falla: 'rejected' = lo frenó una regla (plan/grafo cambiado, base no
    confirmada, otra corrida en curso); 'failed' = error del sistema."""
    from ontology.reconcile import ReconcileError
    return 'rejected' if isinstance(exc, (ImportProblem, ValueError, ReconcileError)) else 'failed'


def _confirm(session, confirm_db):
    """confirm_db debe ser EXACTAMENTE el nombre de la base (misma regla que reconcile). None = no se exige (solo
    desde Python; la API y el script lo exigen siempre). Error con código → 400 'confirm_db'."""
    from ontology.reconcile import ReconcileError, _check_confirm
    if confirm_db is None:
        return None
    try:
        return _check_confirm(session, confirm_db)
    except ReconcileError as e:
        raise ImportProblem(str(e), e.en, 'confirm_db') from e


def _busy_import():
    return ImportProblem('otra importación o reconciliación (aplicar o deshacer) está en curso; inténtalo en un minuto',
                         'another import or reconciliation (apply or undo) is running; try again in a minute', 'busy')


def _check_expect(p, expect, view):
    if not expect or not isinstance(expect.get('plan_sha'), str):
        raise ImportProblem('falta expect.plan_sha (la huella del plan que revisaste)',
                            'expect.plan_sha (the fingerprint of the plan you reviewed) is required', 'expect_required')
    if expect['plan_sha'] != p.get('plan_sha'):
        raise ImportProblem('el plan cambió desde que lo revisaste (otra huella): vuelve a mirarlo antes de aplicar',
                            'the plan changed since you reviewed it (different fingerprint): review it again',
                            'plan_changed')
    if view is not None and p.get('graph_key') != graph_key(view):
        raise ImportProblem('el grafo cambió desde que se armó el plan: vuelve a planear',
                            'the graph changed since the plan was built: plan again', 'graph_changed')


def apply_run(session_scope, p, principal=None, *, confirm_db=None, expect=None, file_sha=None, run_id=None,
              log=None, view=None):
    """Aplica el plan: UNA decisión `ontology.bulk_import`, UNA transacción, escritura por bloques (E2.8), puertas
    en sombra evaluadas en bloque, una sola reconstrucción de las vistas (builder.coalesced). Exige `expect.plan_sha`
    y que el grafo siga en la misma generación (si no → ImportProblem plan_changed/graph_changed → 409 en la API).
    Devuelve {run_id, decision_id, counts, graph_version_before/after, elapsed_ms}."""
    from sqlalchemy import text

    from core.hotviews import builder, hot
    from ontology import import_models
    from ontology.db import _get_engine
    from ontology.reconcile import LOCK_KEY
    log = log or (lambda *_: None)
    view = view or hot.graph()
    _check_expect(p, expect, view)
    who = _who(principal)
    run_id = run_id or new_run_id()
    if not import_models.ensure_tables():
        raise ImportProblem('las tablas del importador no están disponibles', 'import tables are unavailable',
                            'import_tables_unavailable')
    conn = _get_engine().connect()
    try:
        if not conn.execute(text('SELECT pg_try_advisory_lock(:k)'), {'k': LOCK_KEY}).scalar():
            raise _busy_import()
        try:
            with builder.coalesced('import'):
                return _apply_locked(session_scope, p, who, confirm_db, file_sha, run_id, log)
        finally:
            conn.execute(text('SELECT pg_advisory_unlock(:k)'), {'k': LOCK_KEY})
    finally:
        conn.close()


def _apply_locked(session_scope, p, who, confirm_db, file_sha, run_id, log):
    from sqlalchemy import select

    from core import decisions
    from core.hotviews import signals
    from ontology.bulk_import import write_events_fast
    from ontology.import_models import ImportPendingLink, ImportRun
    from ontology.models import ObjectRecord
    t0 = time.perf_counter()
    source = (SOURCE_PREFIX + run_id)[:60]
    block = int(policy('block_size'))
    out = {'run_id': run_id, 'batch': p.get('batch'), 'plan_sha': p['plan_sha'], 'source_channel': source}
    with session_scope() as s, decisions.decision_scope(
            'ontology.bulk_import', who, session=s, rejection_status=_rej_status,
            subject={'import': True, 'run_id': run_id, 'batch': (p.get('batch') or '')[:60], 'plan_sha': p['plan_sha'],
                     'file_sha': file_sha, 'n_records': p['counts']['valid'], 'generation': p.get('generation')}) as dctx:
        out['db'] = _confirm(s, confirm_db)
        out['decision_id'] = str(dctx.id)
        try:
            v0 = signals.read_db_version(s)
            out['graph_version_before'] = v0[0] if v0 else None
        except Exception:  # noqa: BLE001
            v0 = None
            out['graph_version_before'] = None
        # el plan se armó sobre la vista rápida; con el candado tomado, la BASE manda: si otra escritura confirmada
        # movió la versión desde entonces (aunque la vista aún no se haya reconstruido) no se aplica (409)
        if p.get('graph_source') == 'pg' and v0 and p.get('graph_version') is not None and v0[0] != p['graph_version']:
            raise ImportProblem(f"el grafo cambió desde que se armó el plan (versión {p['graph_version']} → {v0[0]}): "
                                'vuelve a planear', f"the graph changed since the plan was built (version "
                                f"{p['graph_version']} → {v0[0]}): plan again", 'graph_changed')
        # ids que el plan CREA pero existen retirados en la base (una corrida deshecha): se reviven
        create_ids = [it['id'] for it in p['items'] if it['action'] == 'create']
        revive = set()
        for i in range(0, len(create_ids), 500):
            for oid, props in s.execute(select(ObjectRecord.id, ObjectRecord.properties)
                                        .where(ObjectRecord.id.in_(create_ids[i:i + 500]))).all():
                if isinstance(props, dict) and props.get('retired') is True:
                    revive.add(oid)
        evs, pend, quar = events_of(p, run_id, revive_ids=revive)
        out.update(events=len(evs), pending=len(pend), quarantine=len(quar), objects_revived=len(revive))
        if file_sha:
            dctx.evidence('import_file', file_sha)
        dctx.evidence('import_plan', p['plan_sha'])
        dctx.policy('policy.import')
        dctx.blob('plan', {'counts': p['counts'], 'categories': p['categories'], 'generation': p['generation'],
                           'items': [{k: it.get(k) for k in ('record_id', 'id', 'action', 'method', 'score')}
                                     for it in p['items']]})
        # puerta G-IMPORT (sombra) sobre el plan, antes de escribir
        out['gate_import'] = gate_plan(p['items'], session=s)
        # escritura por bloques: el bloque = `block` fichas de eventos (E2.8); UNA transacción
        res = write_events_fast(s, evs, source=source, actor=who.id, chunk=max(50, block * 4))
        out.update({k: res[k] for k in ('objects_created', 'objects_updated', 'links_created', 'links_dedup')})
        out['objects_created'] += len(revive)       # un id revivido cuenta como creado (el plan decía 'create')
        out['objects_updated'] -= len(revive)
        out['gate_links'] = res.get('gate')
        # pendientes: la contraparte aún no existe
        for q in pend:
            s.add(ImportPendingLink(id=uuid.uuid4(), run_id=uuid.UUID(_run_uuid(run_id)), record_id=q['record_id'][:80],
                                    relation_id=str(q['relation_id'])[:40], company_id=q['company_id'],
                                    counterparty=q['counterparty'] or {}, payload=q['payload'], reason=q['reason'][:40]))
        summary = {'counts': p['counts'], 'events': len(evs), 'pending': len(pend), 'quarantine': len(quar),
                   'objects_created': res['objects_created'] + len(revive), 'objects_revived': len(revive),
                   'objects_updated': res['objects_updated'] - len(revive),
                   'links_created': res['links_created'], 'links_dedup': res['links_dedup'],
                   'created_ids': [it['id'] for it in p['items'] if it['action'] == 'create'],
                   'categories_approved': p['categories'].get('approved_now') or []}
        s.add(ImportRun(id=uuid.UUID(_run_uuid(run_id)), kind='apply', batch=(p.get('batch') or None), source_channel=source,
                        file_sha=file_sha, plan_sha=p['plan_sha'], decision_id=dctx.id, principal_id=who.id[:96],
                        status='applied', graph_version_before=out['graph_version_before'], summary=summary))
        s.flush()
        dctx.output = {k: v for k, v in summary.items() if k != 'created_ids'}
        dctx.output['run_id'] = run_id
        if not evs:
            dctx.status = 'noop'
    with session_scope() as s:
        try:
            v1 = signals.read_db_version(s)
            out['graph_version_after'] = v1[0] if v1 else None
        except Exception:  # noqa: BLE001
            out['graph_version_after'] = None
    out['elapsed_ms'] = round((time.perf_counter() - t0) * 1000, 1)
    log(f"importación {run_id}: {out['events']} eventos en {out['elapsed_ms']} ms")
    return out


def _run_uuid(run_id):
    """run_id (texto) → UUID determinista para las filas de import_runs/import_pending_links."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'khipus:import:' + str(run_id)))


# ── deshacer ────────────────────────────────────────────────────────────────────────────────────────────────────
def list_runs(session, limit=20):
    from sqlalchemy import select
    from ontology import import_models
    import_models.ensure_tables()
    rows = session.scalars(select(import_models.ImportRun).order_by(import_models.ImportRun.created_at.desc())
                           .limit(limit)).all()
    after = _versions_after(session, [r.decision_id for r in rows if r.decision_id])
    out = []
    for r in rows:
        out.append({'id': str(r.id), 'run_id': r.source_channel.split(':', 1)[1] if ':' in r.source_channel else r.source_channel,
                    'kind': r.kind, 'batch': r.batch, 'status': r.status, 'plan_sha': r.plan_sha, 'file_sha': r.file_sha,
                    'decision_id': str(r.decision_id) if r.decision_id else None, 'principal': r.principal_id,
                    'rolled_back_run': str(r.rolled_back_run) if r.rolled_back_run else None,
                    'graph_version_before': r.graph_version_before,
                    'graph_version_after': r.graph_version_after if r.graph_version_after is not None
                    else after.get(r.decision_id),
                    'summary': {k: v for k, v in (r.summary or {}).items() if k != 'created_ids'},
                    'created_at': r.created_at.isoformat() if r.created_at else None})
    return out


def _versions_after(session, decision_ids):
    """{decision_id: versión del grafo que confirmó esa transacción} desde kh_tx_versions (la fila de import_runs es
    append-only y nace ANTES del commit: la versión 'después' solo se conoce por el txid de su decisión)."""
    if not decision_ids:
        return {}
    from sqlalchemy import text
    try:
        with session.begin_nested():     # un SAVEPOINT: si la consulta falla (base vieja) la transacción sigue sana
            rows = session.execute(text(
                "SELECT d.id, t.version FROM decisions d JOIN kh_tx_versions t ON t.txid = d.txid AND t.name = 'graph' "
                "WHERE d.id = ANY(CAST(:ids AS uuid[]))"), {'ids': [str(x) for x in decision_ids]}).all()
    except Exception:  # noqa: BLE001 — sin contador (base vieja) queda null
        return {}
    return {r[0]: int(r[1]) for r in rows}


def rollback_run(session, run_id, principal=None, *, confirm_db=None):
    """Deshace una corrida con eventos NUEVOS (canal import_rb:<run_id>) en UNA decisión `ontology.import_rollback`:
    vínculos creados → LinkRemoved DIRIGIDO (retracts_event_id, promote_dedups); empresas creadas → retiradas
    (ObjectUpdated retired); fusiones/actualizaciones → se restauran los valores previos. Solo la corrida MÁS NUEVA
    sin deshacer (de la más nueva a la más vieja)."""
    from core import decisions
    who = _who(principal)
    with decisions.decision_scope('ontology.import_rollback', who, session=session, rejection_status=_rej_status,
                                  subject={'run_id': str(run_id)[:60]}) as dctx:
        out = _rollback_body(session, run_id, who, confirm_db)
        dctx.output = out
        out['decision_id'] = str(dctx.id)
    return out


def _rollback_body(session, run_id, who, confirm_db):
    from sqlalchemy import select, text

    from ontology import import_models
    from ontology.bulk_import import write_events_fast
    from ontology.models import Event, EventType
    from ontology.reconcile import LOCK_KEY
    _confirm(session, confirm_db)
    import_models.ensure_tables()
    if not session.execute(text('SELECT pg_try_advisory_xact_lock(:k)'), {'k': LOCK_KEY}).scalar():
        raise _busy_import()
    runs = list_runs(session, limit=500)
    mine = next((r for r in runs if r['run_id'] == run_id and r['kind'] == 'apply'), None)
    if mine is None:
        raise ImportProblem(f'no existe la corrida {run_id}', f'run {run_id} does not exist', 'run_not_found')
    rolled = {r['rolled_back_run'] for r in runs if r['kind'] == 'rollback' and r['rolled_back_run']}
    if mine['id'] in rolled:
        raise ImportProblem(f'la corrida {run_id} ya fue deshecha', f'run {run_id} was already undone', 'already_rolled_back')
    later = [r['run_id'] for r in runs if r['kind'] == 'apply' and r['id'] not in rolled and r['created_at'] > mine['created_at']]
    if later:
        raise ImportProblem(f'primero deshaz las corridas posteriores (de la más nueva a la más vieja): {", ".join(later)}',
                            f'undo the later runs first (newest to oldest): {", ".join(later)}', 'later_runs')
    source = (SOURCE_PREFIX + run_id)[:60]
    evs = session.scalars(select(Event).where(Event.source == source).order_by(Event.recorded_at.desc(), Event.id.desc())).all()
    if not evs:
        raise ImportProblem(f'no hay eventos de la corrida {run_id}', f'no events for run {run_id}', 'run_empty')
    rb = (ROLLBACK_PREFIX + run_id)[:60]
    now = _now().isoformat()
    undo, done = [], {'links_retracted': 0, 'objects_retired': 0, 'objects_restored': 0, 'skipped': 0}
    for ev in evs:
        p = ev.payload or {}
        props = p.get('properties') or {}
        if ev.event_type == EventType.LINK_CREATED.value:
            if props.get('dedup_of'):
                done['skipped'] += 1
                continue
            undo.append({'event_type': 'LinkRemoved', 'object_id': ev.object_id, 'target_id': ev.target_id,
                         'payload': {'rel_type': p.get('rel_type') or 'supply',
                                     'properties': {'retracts_event_id': str(ev.id), 'reason': f'rollback import {run_id}',
                                                    'promote_dedups': True}},
                         'valid_from': ev.valid_from})
            done['links_retracted'] += 1
        elif ev.event_type == EventType.OBJECT_CREATED.value:
            if p.get('type') == 'Company':
                undo.append({'event_type': 'ObjectUpdated', 'object_id': ev.object_id,
                             'payload': {'properties': {'retired': True, 'merged_into': None,
                                                        'retired_razon': f'rollback import {run_id}', 'rollback_run': run_id}},
                             'valid_from': now})
                done['objects_retired'] += 1
            else:
                done['skipped'] += 1            # una fuente (Source) compartida por URL no se retira
        elif ev.event_type == EventType.OBJECT_UPDATED.value:
            keys = [k for k in (p.get('properties') or {}) if k != 'import_run']
            prev = p.get('properties_prev') if isinstance(p.get('properties_prev'), dict) else {}
            restore = {k: prev.get(k) for k in keys}
            restore['import_run'] = None
            restore['rollback_run'] = run_id
            undo.append({'event_type': 'ObjectUpdated', 'object_id': ev.object_id,
                         'payload': {'properties': restore, 'restores_event_id': str(ev.id)}, 'valid_from': now})
            done['objects_restored'] += 1
        else:
            done['skipped'] += 1
    res = write_events_fast(session, undo, source=rb, actor=who.id, gate=False)
    session.add(import_models.ImportRun(id=uuid.uuid4(), kind='rollback', batch=mine.get('batch'), source_channel=rb,
                                        plan_sha=mine.get('plan_sha'), file_sha=mine.get('file_sha'),
                                        principal_id=who.id[:96], status='rolled_back',
                                        rolled_back_run=uuid.UUID(mine['id']),
                                        summary={**done, 'events_reverted': len(evs), 'events_written': len(res['ids'])}))
    session.flush()
    return {'run_id': run_id, 'rollback_channel': rb, **done, 'events_reverted': len(evs),
            'events_written': len(res['ids']), 'links_closed': res['links_closed']}


def consumed_pending_ids(session):
    """Ids de import_pending_links que YA produjeron un LinkCreated (properties.from_pending) en una corrida
    import:*. La tabla es append-only (nunca se marca una fila): el consumo se lee de los eventos. Deshacer esa
    corrida retracta el vínculo pero NO revive el pendiente (decisión explícita: la relación vuelve a entrar con la
    ficha que la trae, nunca sola)."""
    from sqlalchemy import text
    try:
        with session.begin_nested():
            rows = session.execute(text(
                "SELECT DISTINCT payload->'properties'->>'from_pending' FROM events "
                "WHERE event_type = 'LinkCreated' AND source LIKE :src "
                "AND payload->'properties'->>'from_pending' IS NOT NULL"), {'src': SOURCE_PREFIX + '%'}).all()
    except Exception:  # noqa: BLE001 — sin tabla de eventos no hay pendientes consumidos
        return set()
    return {str(r[0]) for r in rows if r[0]}


def pending_links(session, limit=500, include_consumed=False):
    """Vínculos a la espera de su contraparte, SIN los que una corrida ya resolvió (consumed_pending_ids)."""
    from sqlalchemy import select
    from ontology import import_models
    import_models.ensure_tables()
    rows = session.scalars(select(import_models.ImportPendingLink)
                           .order_by(import_models.ImportPendingLink.created_at.desc()).limit(limit)).all()
    done = set() if include_consumed else consumed_pending_ids(session)
    return [{'id': str(r.id), 'run_id': str(r.run_id), 'record_id': r.record_id, 'relation_id': r.relation_id,
             'company_id': r.company_id, 'counterparty': r.counterparty, 'payload': r.payload, 'reason': r.reason,
             'created_at': r.created_at.isoformat() if r.created_at else None} for r in rows if str(r.id) not in done]


# ── resumen legible del plan (para el documento y la terminal) ──────────────────────────────────────────────────
def render_summary(p, lang='es', limit=25):
    """Markdown corto: conteos, categorías por aprobar, ¿qué cambia?, conflictos principales."""
    es = lang != 'en'
    c = p['counts']
    L = []
    L.append(('# Plan de importación' if es else '# Import plan') + (f" — {p.get('batch')}" if p.get('batch') else ''))
    L.append('')
    L.append(f"- {'Huella del plan' if es else 'Plan fingerprint'} (`plan_sha`): `{p['plan_sha']}`")
    L.append(f"- {'Generación del grafo' if es else 'Graph generation'}: `{p['generation']}`")
    L.append(f"- {'Fichas' if es else 'Records'}: {c['records']} · {'válidas' if es else 'valid'} {c['valid']} · "
             f"{'inválidas' if es else 'invalid'} {c['invalid']}")
    L.append(f"- {'Se crean' if es else 'Create'}: **{c['create']}** · {'se fusionan' if es else 'merge'}: **{c['merge']}** · "
             f"{'se actualizan' if es else 'update'}: **{c['update']}** · {'se omiten' if es else 'skip'}: {c['skip']}")
    lk = c['links']
    L.append(f"- {'Vínculos' if es else 'Links'}: {'vivos' if es else 'live'} {lk['live']} · "
             f"{'propuestos' if es else 'proposed'} {lk['proposed']} · {'pendientes' if es else 'pending'} {lk['pending']} · "
             f"{'cuarentena' if es else 'quarantine'} {lk['quarantine']}")
    L.append(f"- {'Fuentes nuevas' if es else 'New sources'}: {c['sources_new']} · {'eventos estimados' if es else 'estimated events'}: "
             f"{c['events_estimated']}")
    cats = p['categories']['to_approve']
    L.append('')
    L.append(('## Categorías por aprobar' if es else '## Categories to approve') + f' ({len(cats)})')
    for ct in sorted(cats, key=lambda x: -x['n'])[:limit]:
        L.append(f"- `{ct['id']}` ({ct.get('sector')}) — {ct.get('label_es') if es else ct.get('label_en')} · {ct['n']} "
                 f"{'empresas' if es else 'companies'} · {'p. ej.' if es else 'e.g.'} {', '.join(ct.get('examples') or [])}")
    wc = p.get('what_changes') or {}
    L.append('')
    L.append('## ¿Qué cambia en el kernel?' if es else '## What changes in the kernel?')
    if wc.get('available'):
        b, a = wc['before'], wc['after']
        L.append(f"- {'Nodos' if es else 'Nodes'}: {b['nodes']} → {a['nodes']} · {'vínculos' if es else 'links'}: {b['links']} → {a['links']}")
        L.append(f"- ρ: {b.get('rho')} → {a.get('rho')} · damping·ρ: {b.get('damping_rho')} → {a.get('damping_rho')}")
        L.append(f"- TSMC {'golpea a' if es else 'hits'}: {b.get('tsmc_hit')} → {a.get('tsmc_hit')} {'empresas' if es else 'companies'}")
        L.append(f"- {wc.get('note_es' if es else 'note_en')}")
        top_b = ', '.join(x['id'] for x in b.get('chokepoints') or [])
        top_a = ', '.join(x['id'] for x in a.get('chokepoints') or [])
        L.append(f"- Top-20 {'cuellos de botella antes' if es else 'chokepoints before'}: {top_b}")
        L.append(f"- Top-20 {'después' if es else 'after'}: {top_a}")
    else:
        L.append(f"- {'no disponible' if es else 'unavailable'}: {wc.get('reason') or wc.get('error')}")
    conf = [(it['name'], cft) for it in p['items'] for cft in it.get('conflicts') or []]
    L.append('')
    L.append(('## Conflictos principales' if es else '## Top conflicts') + f' ({len(conf)})')
    for name, cft in conf[:limit]:
        L.append(f"- {name}: {cft.get('kind')} {cft.get('key') or cft.get('id') or ''} "
                 f"{'(' + str(cft.get('current')) + ' ≠ ' + str(cft.get('proposed')) + ')' if cft.get('current') is not None else ''}")
    warn = Counter(w.get('code') for it in p['items'] for w in it.get('warnings') or [])
    L.append('')
    L.append('## Avisos' if es else '## Warnings')
    for code, n in warn.most_common():
        L.append(f'- {code}: {n}')
    if p.get('invalid'):
        L.append('')
        L.append(('## Fichas inválidas' if es else '## Invalid records') + f" ({len(p['invalid'])})")
        for inv in p['invalid'][:limit]:
            first = (inv.get('errors') or [{}])[0]
            L.append(f"- {inv.get('record_id')}: {first.get('msg_es' if es else 'msg_en')}")
    return '\n'.join(L) + '\n'


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Adaptador del lote 2026-10-14 (CSV de la investigación externa → fichas nivel A khipus.company/1)
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
LOTE1_DIR = os.path.join(ROOT, 'data', 'import', 'lotes', '2026-10-14')
LOTE1_BATCH = 'lote-2026-10-14'
LOTE1_AS_OF = '2026-10-14'
_US_MICS = ('XNAS', 'XNYS', 'XASE', 'ARCX', 'BATS', 'XNGS', 'XNMS', 'XNCM')
_DEPOSITARY_MICS = ('XBUE', 'OTCM', 'XSTU', 'XBER', 'XDUS', 'XHAM', 'XHAN', 'XMUN', 'XFRA')
# bolsa → país (ISO-2) para la regla "la cotización principal es la de la bolsa de la sede"
MIC_COUNTRY = {
    **{m: 'US' for m in _US_MICS}, 'OTCM': 'US', 'XTKS': 'JP', 'XJPX': 'JP', 'XOSE': 'JP', 'XHKG': 'HK', 'XASX': 'AU', 'XSHG': 'CN',
    'XSHE': 'CN', 'XTAI': 'TW', 'ROCO': 'TW', 'XKRX': 'KR', 'XKOS': 'KR', 'XETR': 'DE', 'XFRA': 'DE', 'XSTU': 'DE',
    'XBER': 'DE', 'XDUS': 'DE', 'XHAM': 'DE', 'XHAN': 'DE', 'XMUN': 'DE', 'XLON': 'GB', 'XPAR': 'FR', 'XAMS': 'NL',
    'XBRU': 'BE', 'XMIL': 'IT', 'XMAD': 'ES', 'XLIS': 'PT', 'XHEL': 'FI', 'XDUB': 'IE', 'XWBO': 'AT', 'XSTO': 'SE',
    'XCSE': 'DK', 'XOSL': 'NO', 'XSWX': 'CH', 'XWAR': 'PL', 'MISX': 'RU', 'XNSE': 'IN', 'XBOM': 'IN', 'XSES': 'SG',
    'XIDX': 'ID', 'DSMD': 'QA', 'XSAU': 'SA', 'XTAE': 'IL', 'XJSE': 'ZA', 'XNZE': 'NZ', 'XTSE': 'CA', 'XTSX': 'CA',
    'NEOE': 'CA', 'XCNQ': 'CA', 'XMEX': 'MX', 'BVMF': 'BR', 'XKLS': 'MY', 'XBKK': 'TH', 'XSGO': 'CL', 'XIST': 'TR',
    'XBUE': 'AR', 'XLIM': 'PE', 'XBOG': 'CO', 'ASEX': 'GR', 'XPRA': 'CZ', 'XBUD': 'HU', 'XLIT': 'LT', 'XDFM': 'AE',
    'XADS': 'AE', 'XICE': 'IS', 'XRIS': 'LV', 'XTAL': 'EE', 'XZAG': 'HR', 'XBSE': 'RO', 'XLJU': 'SI', 'XKAR': 'PK',
    'XCAI': 'EG', 'XCAS': 'MA', 'XTUN': 'TN', 'XNAI': 'KE', 'XLUX': 'LU', 'XMAL': 'MT', 'XCYS': 'CY',
}
_TICKER_RX = re.compile(r'^[A-Z0-9][A-Z0-9.\-]{0,14}$')
_YAHOO_RX = re.compile(r'^[A-Z0-9^][A-Z0-9.=\-^]{0,19}$')
_ISIN_RX = re.compile(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')
_FIGI_RX = re.compile(r'^BBG[A-Z0-9]{9}$')
_DOMAIN_RX = re.compile(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$')


def _read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def _domain_of(url):
    from urllib.parse import urlsplit
    try:
        host = urlsplit(url).netloc.split('@')[-1].split(':')[0].lower()
    except ValueError:
        return None
    host = host[4:] if host.startswith('www.') else host
    if not host or any(host == h or host.endswith('.' + h) for h in _AGGREGATOR_HOSTS):
        return None
    return host if _DOMAIN_RX.match(host) else None


_REGIONAL_MICS = ('XSTU', 'XBER', 'XDUS', 'XHAM', 'XHAN', 'XMUN', 'OTCM')   # plazas donde cotizan sobre todo certificados
_DEPOSITARY_NAME_RX = re.compile(r'\b(ADRs?|GDRs?|CEDEARs?|Sp\.\s*ADRs?|Depositary|Dep\.?\s*Rec)\b', re.I)
_ISIN_COUNTRY_OF = {'US': 'US', 'DE': 'DE'}


def _primary_rule(mic, hq, isin, legal_name=None):
    """(es_principal, aviso). Principal = bolsa del país de la sede; CN→HK vale; CEDEAR/OTC/regionales alemanas en
    el extranjero NO; otra bolsa extranjera = principal con aviso para revisar. Revisión lote K: una plaza REGIONAL
    (Stuttgart, Berlín, Düsseldorf, Hamburgo, Hannover, Múnich, OTC) en el país de la sede tampoco es principal cuando
    el nombre legal dice ADR/GDR/Depositary o el ISIN es de otro país (Siemens «Sp. ADRs» en XSTU con ISIN US…);
    Fráncfort/XETRA siguen siendo principales para DE."""
    mc = MIC_COUNTRY.get(mic)
    if mc is None:
        return True, 'mic_unknown'
    if mc == hq or (hq == 'CN' and mic == 'XHKG'):
        if mic in _REGIONAL_MICS:
            dep_name = bool(legal_name and _DEPOSITARY_NAME_RX.search(str(legal_name)))
            isin_cc = str(isin or '')[:2].upper() or None
            if dep_name or (isin_cc and hq and hq != 'ZZ' and isin_cc != hq and isin_cc not in ('XS',)):
                return False, 'primary_is_depositary'
        return True, None
    if mic in _DEPOSITARY_MICS:
        return False, 'primary_is_depositary'
    return True, 'listing_abroad_check'


def _listing_kind(mic, hq, kind=None):
    if kind in ('equity', 'a_share', 'h_share', 'adr', 'gdr', 'otc', 'preferred', 'dual_class'):
        return kind
    if mic in ('XSHG', 'XSHE'):
        return 'a_share'
    if mic == 'XHKG' and hq == 'CN':
        return 'h_share'
    if mic == 'OTCM':
        return 'otc'
    return 'equity'


def _listing(symbol, mic, yahoo, hq, isin=None, figi=None, currency=None, kind=None, source_url=None, as_of=LOTE1_AS_OF,
             is_primary=True, confidence=None, warnings=None):
    """Una cotización del esquema o None (con el motivo en `warnings`)."""
    from core.import_normalize import currency_of_mic, yahoo_matches_mic, yahoo_symbol_for
    warnings = warnings if warnings is not None else []
    symbol = (symbol or '').strip().upper()
    mic = (mic or '').strip().upper()
    if not symbol or not mic:
        return None
    if not _TICKER_RX.match(symbol):
        warnings.append({'code': 'symbol_invalid', 'symbol': symbol, 'mic': mic,
                         'es': f'símbolo «{symbol}» fuera del formato del esquema: cotización omitida',
                         'en': f'symbol "{symbol}" outside the schema format: listing omitted'})
        return None
    ys = (yahoo or '').strip().upper() or yahoo_symbol_for(symbol, mic)
    if not ys or not _YAHOO_RX.match(ys):
        warnings.append({'code': 'yahoo_symbol_invalid', 'symbol': symbol, 'mic': mic,
                         'es': f'sin símbolo de Yahoo válido para {symbol}@{mic}: cotización omitida',
                         'en': f'no valid Yahoo symbol for {symbol}@{mic}: listing omitted'})
        return None
    if yahoo and yahoo_matches_mic(ys, mic) is False:
        warnings.append({'code': 'yahoo_mic_mismatch', 'symbol': ys, 'mic': mic,
                         'es': f'el sufijo de {ys} no es el de la bolsa {mic}', 'en': f'the suffix of {ys} is not the one of {mic}'})
    ccy = (currency or '').strip().upper() or currency_of_mic(mic) or ('USD' if mic in _US_MICS + ('OTCM',) else None)
    if not ccy:
        warnings.append({'code': 'currency_unknown', 'symbol': symbol, 'mic': mic,
                         'es': f'sin moneda conocida para la bolsa {mic}: cotización omitida',
                         'en': f'unknown currency for exchange {mic}: listing omitted'})
        return None
    from core.instruments import MINOR_UNITS
    if ccy in MINOR_UNITS:
        ccy = MINOR_UNITS[ccy][0]
    out = {'ticker': symbol, 'exchange_mic': mic, 'yahoo_symbol': ys, 'currency': ccy,
           'kind': _listing_kind(mic, hq, kind), 'is_primary': bool(is_primary),
           'source_url': source_url or 'https://github.com/JerBouma/FinanceDatabase', 'as_of': as_of}
    if isin and _ISIN_RX.match(isin):
        out['isin'] = isin
    if figi and _FIGI_RX.match(figi):
        out['figi'] = figi
    if confidence is not None:
        out['confidence'] = confidence
    return out


_DEP_SUFFIX_RX = re.compile(r'^(.*?\S)\s*\((GDRs?|ADRs?|CEDEARs?|Sp\.\s*ADRs?|Depositary Receipts?)\)\s*$', re.I)


def _strip_depositary_suffix(name):
    """'Samsung Electronics (GDR)' → ('Samsung Electronics', 'GDR'); otro nombre → (name, None)."""
    m = _DEP_SUFFIX_RX.match(name or '')
    if not m:
        return name, None
    return m.group(1).strip(), m.group(2)


def adapt_lote_2026_10_14(path=None, categories=None):
    """CSV del lote 1 → {'records': fichas nivel A, 'updates': países de las 937, 'approve_categories': las 56
    propuestas (consolidadas), 'warnings': [...], 'batch'}. No toca el grafo."""
    from core.import_normalize import khipus_id_from
    d = path or LOTE1_DIR
    rows = _read_csv(os.path.join(d, 'empresas_nuevas.csv'))
    ver = {v['nombre']: v for v in _read_csv(os.path.join(d, 'empresas_nuevas_verificacion.csv'))}
    cats = _read_csv(os.path.join(d, 'categorias_propuestas.csv'))
    paises = _read_csv(os.path.join(d, 'existentes_paises.csv'))
    cat_by_id = {c['id']: c for c in cats}
    pol = policy()
    records, warnings = [], []
    for n, r in enumerate(rows, 1):
        w = []
        name_raw = r['nombre'].strip()
        v = ver.get(name_raw) or {}
        # «Samsung Electronics (GDR)» → nombre «Samsung Electronics» (el sufijo del certificado va a other_names y
        # el ítem queda marcado como posible duplicado para revisar)
        name, dep_suffix = _strip_depositary_suffix(name_raw)
        hq = (r['pais_iso2'] or '').strip().upper()
        if not hq:
            hq = 'ZZ'                 # ISO 3166 de uso privado: "sede desconocida" (se lista para revisar)
            w.append({'code': 'hq_unknown', 'es': 'sin país de sede en la investigación: queda como desconocida (ZZ)',
                      'en': 'no HQ country in the research: left unknown (ZZ)'})
        verificado = (v.get('verificado') or 'no').strip()
        metodo = (v.get('metodo') or 'conocimiento').strip()
        if verificado == 'si':
            conf, skind, researcher = 0.8, 'corporate', 'investigacion-externa (web)'
        elif verificado == 'agregador':
            conf, skind, researcher = 0.7, 'aggregator', 'investigacion-externa (FinanceDatabase)'
        else:
            conf, skind, researcher = float(pol['unverified_confidence']), 'corporate', 'investigacion-externa (sin verificar)'
        src = (r['fuente_url'] or '').strip()
        if not src.startswith('http'):
            src = 'https://github.com/JerBouma/FinanceDatabase'
        fact = {'source_url': src, 'source_kind': skind, 'as_of': LOTE1_AS_OF, 'confidence': conf,
                'retrieved_at': LOTE1_AS_OF}
        cat_raw = (r['categoria'] or '').strip()
        cat_proposed = None
        if cat_raw.startswith('NUEVA:'):
            cid = cat_raw[6:]
            c = cat_by_id.get(cid) or {}
            cat_proposed = {'id': cid, 'label_es': (c.get('label_es') or cid)[:60], 'label_en': (c.get('label_en') or cid)[:60],
                            'sector': (c.get('sector') or r['sector'] or '')[:30]}
            cat = cid
        else:
            cat = cat_raw
        ids = {}
        isin = (r['identificador'] or '').strip().upper() if (r['tipo_identificador'] or '').upper() == 'ISIN' else None
        if not (isin and _ISIN_RX.match(isin)):
            isin = None
        figi = (v.get('figi') or '').strip().upper()
        if not (figi and _FIGI_RX.match(figi)):
            figi = None
        dom = _domain_of(src) if src else None
        if dom:
            ids['domain'] = dom
        listings = []
        mic = (r['bolsa_mic'] or '').strip().upper()
        if r['ticker'].strip() and mic:
            primary, note = _primary_rule(mic, hq, isin, legal_name=r.get('nombre_legal') or '')
            l = _listing(r['ticker'], mic, r['simbolo_yahoo'], hq, isin=isin, figi=figi, is_primary=primary,
                         source_url=(src if verificado == 'si' else None), confidence=conf, warnings=w)
            if l:
                listings.append(l)
                if primary:       # un CEDEAR/OTC no identifica a la empresa: los ids solo salen de la principal
                    ids['ticker'], ids['exchange_mic'], ids['yahoo_symbol'] = l['ticker'], l['exchange_mic'], l['yahoo_symbol']
                    if isin:
                        ids['isin'] = [isin]
                    if figi:
                        ids['figi'] = [figi]
                # si no es principal, el ISIN/FIGI queda SOLO dentro de listings[] (revisión lote K)
                if note:
                    w.append({'code': note, 'mic': mic, 'hq': hq,
                              'es': {'primary_is_depositary': f'la cotización en {mic} es un certificado/secundaria: no es la principal',
                                     'listing_abroad_check': f'cotiza en {mic} ({MIC_COUNTRY.get(mic)}) y la sede está en {hq}: revisar',
                                     'mic_unknown': f'bolsa {mic} desconocida'}[note],
                              'en': {'primary_is_depositary': f'the {mic} listing is a depositary/secondary one: not primary',
                                     'listing_abroad_check': f'listed on {mic} ({MIC_COUNTRY.get(mic)}) while HQ is in {hq}: review',
                                     'mic_unknown': f'unknown exchange {mic}'}[note]})
        elif isin or figi:
            # sin cotización: el identificador de la investigación sí es de la empresa
            if isin:
                ids['isin'] = [isin]
            if figi:
                ids['figi'] = [figi]
        try:
            sec = json.loads(v.get('secundarias') or '[]')
        except (ValueError, TypeError):
            sec = []
        for s in sec if isinstance(sec, list) else []:
            if not isinstance(s, dict):
                continue
            l = _listing(s.get('symbol'), s.get('mic'), None, hq, isin=(s.get('isin') or None), figi=(s.get('figi') or None),
                         currency=s.get('currency'), kind=s.get('kind'), is_primary=False, confidence=conf, warnings=w)
            if l and len(listings) < 12:
                listings.append(l)
        por_que = (r['por_que'] or '').strip()
        if len(por_que) < 10:
            por_que = f'{name}: empresa del lote {LOTE1_BATCH} sin descripción.'
        rec = {
            'schema': 'khipus.company/1', 'record_id': f'l20261014-{n:04d}', 'khipus_id_hint': khipus_id_from(name),
            'research_meta': {'researcher': researcher, 'researched_at': '2026-10-14T00:00:00Z', 'method': 'ai_assisted',
                              'tools': ['FinanceDatabase'] if metodo == 'base_de_datos' else [metodo][:1], 'tier': 'A',
                              'priority': (r['prioridad'] or 'P3').strip(), 'batch': LOTE1_BATCH, 'revision': 1,
                              'not_found': ['profile.summary.value_en'],
                              'notes': f'verificado={verificado}; metodo={metodo}; sector_csv={r["sector"]}; capa={r["capa"]}'[:2000]},
            'identity': {'legal_name': {'value': (r['nombre_legal'] or name).strip()[:2000], **fact},
                         'short_name': name[:120],
                         'status': {'value': (r['estado'] or 'private').strip(), **fact},
                         'hq_country': {'value': hq, **fact}},
            'classification': {'cat': cat},
            'profile': {'summary': {'value': por_que[:1200], 'value_en': (_EN_PENDING + por_que)[:1200], **fact}},
        }
        if ids:
            rec['identity']['ids'] = ids
        if dep_suffix:
            rec['identity']['other_names'] = [{'name': name_raw[:160], 'kind': 'common'}]
            w.append({'code': 'depositary_name', 'suffix': dep_suffix,
                      'es': f'el nombre trae «({dep_suffix})»: es un certificado de una empresa que quizá ya existe (revisar)',
                      'en': f'the name carries "({dep_suffix})": a depositary receipt of a company that may already exist (review)'})
        if dom:
            rec['identity']['website'] = src
        if listings:
            rec['listings'] = listings
        if cat_proposed:
            rec['classification']['cat_proposed'] = cat_proposed
        capa = (r['capa'] or '').strip()
        if capa:
            rec['classification']['chain_layers'] = [capa]
        records.append(rec)
        for x in w:
            warnings.append({'record_id': rec['record_id'], 'name': name, **x})
    updates = []
    for p in paises:
        hq = (p['hq_country'] or '').strip().upper()
        if not hq:
            warnings.append({'record_id': None, 'name': p['khipus_id'], 'code': 'hq_unknown',
                             'es': 'sin país de sede en la revisión', 'en': 'no HQ country in the review'})
            continue
        props = {'hq_country': hq, 'country_iso2': hq}
        inc = (p['incorporation_country'] or '').strip().upper()
        if inc:
            props['incorporation_country'] = inc
        src = {'method': (p['metodo'] or '').strip()}
        if (p['fuente_url'] or '').startswith('http'):
            src.update(url=p['fuente_url'].strip(), kind=(p['source_kind'] or 'aggregator').strip(),
                       quote=(p['quote'] or '')[:500], as_of=LOTE1_AS_OF)
        try:
            src['confidence'] = float(p['confidence']) if p['confidence'] else (0.5 if src['method'] == 'mapeo' else 0.6)
        except ValueError:
            src['confidence'] = 0.5
        updates.append({'khipus_id': p['khipus_id'].strip(), 'props': props, 'source': src,
                        'note': (p['nota'] or '')[:300] or None})
    from ontology.vocabulary import categories as _known_cats, resolve_category as _resolve_cat
    known = _known_cats()
    approve = []
    for c in cats:
        label_es, label_en, sector = c['label_es'][:60], c['label_en'][:60], c['sector'][:30]
        if not (label_es and label_en and sector):
            # «(sin consolidar)» en el CSV (battery_components): etiqueta y sector de la categoría consolidada del
            # catálogo (data/categories.json: alias → battery_cells); si tampoco existe, queda vacío y el plan lo lista.
            k = known.get(_resolve_cat(c['id']) or c['id']) or {}
            label_es, label_en, sector = label_es or k.get('es', ''), label_en or k.get('en', ''), sector or k.get('sector', '')
        approve.append({'id': c['id'], 'label_es': label_es, 'label_en': label_en, 'sector': sector,
                        'n_declared': int(c['empresas'] or 0), 'groups': c.get('agrupa')})
    return {'schema': 'khipus.import/1', 'batch': LOTE1_BATCH, 'records': records, 'updates': updates,
            'approve_categories': approve, 'warnings': warnings}
