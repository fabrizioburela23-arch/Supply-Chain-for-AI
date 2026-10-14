"""core/entities.py — Phase 1 · M2: identidad de entidad en el servidor.

El problema (ver docs/ARCHITECTURE.md §3): había CUATRO resolvedores
divergentes, con tablas de alias y umbrales distintos:

  - engine/resolve.js  → cliente, fuzzy + ~230 alias de voz, umbral 60
  - core/semantic.py   → id / ticker / label exacto, sin alias, sin score
  - ontology/agents.py → slug o label exacto, SIN alias ni fuzzy…
                         …y es justo el que consume nombres generados por un LLM
  - scripts/ingest_enrichment_md.py → el más completo, pero offline

Y `NODE_ID_ALIAS` (la tabla canónica del merge) vivía solo en JS: el exportador
la usaba como entrada pero no la sacaba al snapshot, así que el servidor no la
veía. Consecuencia concreta: un modelo que dijera "NVIDIA Corporation" o "NVDA"
no lograba pegar el hecho a su entidad, y el dato se perdía en silencio.

Este módulo es el resolvedor ÚNICO del servidor. No sustituye al del cliente
(que además maneja transcripción de voz), pero sí a los tres server-side.

Devuelve SIEMPRE cómo resolvió, no solo qué resolvió: `{id, score, method,
matched}`. Eso permite auditar por qué un texto acabó en una entidad, y poner
umbrales distintos según quién pregunta (un humano escribiendo puede aceptar
un fuzzy flojo; un agente escribiendo en la ontología, no).
"""
import json
import re
import threading
import time
import unicodedata
from array import array
from bisect import bisect_left

# Paso 8 (INFRA_OPERATIVA §4.7): el índice sale de la vista `graph` de la generación vigente
# (core/hotviews/hot.graph(): Postgres si existe, el snapshot si no) y se reconstruye cuando cambia la
# generación — antes se armaba UNA vez desde data/grafo_v0.json y una empresa nueva nunca resolvía.
_lock = threading.Lock()
_index = None   # {'generation': …, …} de solo lectura; se renueva con la generación

# Umbrales recomendados. Distintos a propósito: escribir en la ontología con un
# match flojo corrompe el grafo en silencio; buscar desde la UI no.
UMBRAL_ESCRITURA = 85   # agentes que crean hechos: solo exacto/ticker/alias
UMBRAL_BUSQUEDA = 60    # búsqueda humana: admite prefijo/fuzzy

_PUNCT = re.compile(r'[^\w\s]', re.UNICODE)
_NO_ASCII = re.compile(r'[^\x00-\x7f]')
_WS = re.compile(r'\s+')
# Sufijos societarios: "NVIDIA Corporation" y "NVIDIA" son la misma empresa.
_SUFIJOS = (
    'corporation', 'corp', 'incorporated', 'inc', 'limited', 'ltd', 'llc',
    'plc', 'sa', 'sas', 'ag', 'nv', 'bv', 'co', 'company', 'holdings',
    'holding', 'group', 'technologies', 'technology', 'systems',
)


def _sin_marca(m):
    c = m.group()
    return '' if unicodedata.category(c) == 'Mn' else c


def norm(txt):
    """minúsculas + sin acentos + sin puntuación + espacios colapsados."""
    if not txt:
        return ''
    s = str(txt)
    if not s.isascii():          # ASCII: NFD no cambia nada y no hay marcas (Mn) — mismo resultado, más rápido
        # quita las marcas (categoría Mn, nunca ASCII) mirando solo los caracteres no ASCII: E1.5, 4× más rápido
        s = _NO_ASCII.sub(_sin_marca, unicodedata.normalize('NFD', s))
    s = _PUNCT.sub(' ', s.lower())
    return _WS.sub(' ', s).strip()


def strip_suffix(txt):
    """Quita sufijos societarios finales ('nvidia corporation' → 'nvidia')."""
    palabras = norm(txt).split()
    while len(palabras) > 1 and palabras[-1] in _SUFIJOS:
        palabras.pop()
    return ' '.join(palabras)


def parse_ticker(raw):
    """El campo `ticker` del catálogo mezcla símbolo y bolsa: 'RGTI · Nasdaq',
    'IBM · NYSE (división)'. Devuelve (simbolo, bolsa) — solo la parte limpia
    es utilizable como identificador externo."""
    if not raw:
        return None, None
    partes = re.split(r'[·|]', str(raw), maxsplit=1)
    simbolo = partes[0].strip().upper() or None
    bolsa = None
    if len(partes) > 1:
        bolsa = re.sub(r'\(.*?\)', '', partes[1]).strip() or None
    if simbolo and not re.match(r'^[A-Z0-9.\-]{1,15}$', simbolo):
        simbolo = None
    return simbolo, bolsa


def external_ids(node):
    """Identificadores externos estructurados de un nodo del catálogo.
    `mkt` es el símbolo limpio; `ticker` trae símbolo + bolsa mezclados."""
    simbolo, bolsa = parse_ticker(node.get('ticker'))
    out = {}
    mkt = (node.get('mkt') or '').strip().upper()
    if mkt:
        out['ticker'] = mkt
    elif simbolo:
        out['ticker'] = simbolo
    if bolsa:
        out['exchange'] = bolsa
    return out


def _build_index(snapshot_path=None, view=None):
    """Índice de resolución desde el grafo vigente (vista `graph`) o, si se pasa, desde un archivo con la forma
    del snapshot (solo pruebas/herramientas). Incluye la tabla de alias del merge (`node_id_alias`) y, con
    Postgres, las fusiones (FusionarEntidad: merged_into)."""
    if snapshot_path:
        with open(snapshot_path, encoding='utf-8') as fh:
            snap = json.load(fh)
        generation = f'file:{snapshot_path}'
    else:
        from core.hotviews import hot
        view = view or hot.graph()
        snap = view.snapshot
        generation = view.generation

    nodos = {n['id']: n for n in snap.get('nodes', [])}
    alias_tbl = snap.get('node_id_alias') or {}

    # alias → canónico, siguiendo cadenas (A→B→C) con tope para no ciclar
    def canonico(objetivo, saltos=5):
        visto = set()
        while objetivo in alias_tbl and saltos > 0 and objetivo not in visto:
            visto.add(objetivo)
            objetivo = alias_tbl[objetivo]
            saltos -= 1
        return objetivo

    por_id = {}          # id normalizado → id canónico
    por_ticker = {}      # símbolo → id
    por_label = {}       # label normalizado → id
    por_label_corto = {} # label sin sufijo societario → id
    por_alias = {}       # alias normalizado → id

    for nid, n in nodos.items():
        por_id[norm(nid)] = nid
        ids = external_ids(n)
        if ids.get('ticker'):
            por_ticker.setdefault(ids['ticker'], nid)
        # lote K: los listados SECUNDARIOS declarados (TOELY = ADR OTC de TEL) también resuelven por ticker, como
        # claves blandas (setdefault: el símbolo principal de otra empresa siempre gana)
        for l in (n.get('listings') or []) if isinstance(n.get('listings'), (list, tuple)) else []:
            ys = str((l.get('yahoo_symbol') if isinstance(l, dict) else '') or '').strip().upper()
            if ys:
                por_ticker.setdefault(ys, nid)
        lbl = n.get('label') or ''
        if lbl:
            por_label.setdefault(norm(lbl), nid)
            corto = strip_suffix(lbl)
            if corto:
                por_label_corto.setdefault(corto, nid)
            # "Microsoft (Azure)" → también "microsoft" y "azure"
            m = re.match(r'^(.*?)\s*\((.+?)\)\s*$', lbl)
            if m:
                for parte in (m.group(1), m.group(2)):
                    if norm(parte):
                        por_alias.setdefault(norm(parte), nid)

    for alias, destino in alias_tbl.items():
        can = canonico(destino)
        if can in nodos:
            por_alias.setdefault(norm(alias), can)
            por_alias.setdefault(strip_suffix(alias), can)

    # Nombres legales/alternativos (nodes/legal_names.js → snapshot): así
    # "Taiwan Semiconductor Manufacturing Company" o "Google" llegan a TSMC /
    # Alphabet. Ids inexistentes se ignoran. Van DESPUÉS de los alias del
    # merge: si chocan, gana la tabla canónica.
    for nombre, destino in (snap.get('legal_names') or {}).items():
        can = canonico(destino)
        if can in nodos:
            por_alias.setdefault(norm(nombre), can)
            por_alias.setdefault(strip_suffix(nombre), can)

    # G5-19 (lote I1): alias de VOZ del navegador ("en vidia", "open ai", "taiwan semi") — la MISMA tabla que
    # engine/resolve.js (nodes/legal_names.js → snapshot). Aparte de por_alias a propósito: el detector de
    # entidades del contexto (core/context_engine) recorre por_alias sobre texto libre, y alias amplios como
    # 'video' o 'applied' no deben marcar empresas en una frase. Aquí solo valen para el texto ENTERO.
    por_voz = {}
    for alias, destino in (snap.get('voice_aliases') or {}).items():
        can = canonico(destino)
        if can in nodos and norm(alias):
            por_voz.setdefault(norm(alias), can)
    stop = frozenset(snap.get('resolve_stopwords') or ())

    # E1.6: nombres alternativos de la FICHA importada (identity.other_names → props.other_names [{name, kind,
    # lang}] + props.aliases [str]): siglas, marcas, nombres anteriores y escritura local ("宁德时代" → CATL).
    # Van al final (setdefault): si chocan con un alias del merge o un nombre legal, gana lo curado. El catálogo
    # de hoy no trae ninguno, así que resolve() no cambia para lo que ya existía.
    for nid, n in nodos.items():
        for nombre in _other_names(n):
            k = norm(nombre)
            if len(k) >= 2:
                por_alias.setdefault(k, nid)
                corto = strip_suffix(nombre)
                if corto:
                    por_alias.setdefault(corto, nid)

    alias_inv = {}      # canónico → ids viejos que apuntan a él (entity_ids_for)
    for a in alias_tbl:
        alias_inv.setdefault(canonico(a), []).append(a)

    out = {'nodos': nodos, 'por_id': por_id, 'por_ticker': por_ticker,
           'por_label': por_label, 'por_label_corto': por_label_corto,
           'por_alias': por_alias, 'alias_tbl': alias_tbl, 'alias_inv': alias_inv,
           'por_voz': por_voz, 'stopwords': stop,
           'preipo_intel': snap.get('preipo_intel') or {}, 'generation': generation}
    out['identificadores'] = _indice_identificadores(nodos)
    return out


# ── E1.6 (docs/expansion/EXPANSION_5K.md): resolver por IDENTIFICADORES ───────────────────────────────────────────
# Lo que la ficha khipus.company/1 escribe en las propiedades del objeto (contrato 3 del lote K): `ids` {lei, isin,
# cik, qid, figi, domain, yahoo_symbol, ticker, mic}, `listings` [{symbol, mic, yahoo_symbol, isin, figi}], y lo que
# el catálogo ya trae (`mkt` = símbolo de Yahoo con su sufijo de bolsa; `ticker` = "8035 · TSE", texto). Un ticker
# SIN bolsa nunca identifica nada ("3750" es HK, TSE o TWSE); con su MIC se convierte al símbolo de Yahoo esperado
# (core.import_normalize.yahoo_symbol_for) y se busca ahí. Un identificador que dos empresas reclaman (el mismo ISIN
# en dos ids) no elige a ninguna: se devuelve como conflicto.
_ID_KINDS = ('lei', 'isin', 'cik', 'qid', 'figi', 'yahoo', 'ticker_mic', 'domain')
_ID_SCORE = {'lei': 100, 'isin': 99, 'cik': 99, 'qid': 99, 'figi': 98, 'yahoo_symbol': 97, 'ticker_mic': 96}
_YAHOO_RX = re.compile(r'^[A-Z0-9^][A-Z0-9.=\-^]{0,19}$')


def _lista(v):
    if v is None or v == '':
        return []
    if isinstance(v, (list, tuple, set)):
        return [x for x in v if x not in (None, '')]
    return [v]


def _cik(v):
    d = re.sub(r'\D', '', str(v or ''))
    return d.zfill(10) if d and len(d) <= 10 else None


def _dominio(v):
    d = str(v or '').strip().lower()
    d = re.sub(r'^[a-z]+://', '', d)
    d = d.split('/', 1)[0]
    if d.startswith('www.'):
        d = d[4:]
    return d or None


def _other_names(n):
    """Nombres alternativos declarados en la ficha: props.other_names (dicts o cadenas) + props.aliases."""
    out = []
    for o in _lista(n.get('other_names')):
        nombre = o.get('name') if isinstance(o, dict) else o
        if isinstance(nombre, str) and nombre.strip():
            out.append(nombre.strip())
    for a in _lista(n.get('aliases')):
        if isinstance(a, str) and a.strip():
            out.append(a.strip())
    return out


def _simbolos_del_catalogo(n):
    """Símbolos "de casa" que el TEXTO del catálogo declara ("005930 · KRX" → 005930.KS; "ENR · Xetra" → ENR.DE),
    como claves BLANDAS del índice por símbolo de Yahoo (solo si nadie las declara de verdad). Sin bolsa reconocible
    → nada: un código suelto no identifica."""
    try:
        from core.instruments import _EURONEXT, _VENUE_SUFFIX
    except Exception:  # noqa: BLE001
        return []
    out = []
    txt = str(n.get('ticker') or '')
    for part in [p.strip() for p in re.split(r'\s/\s|/|;', txt) if p.strip()]:
        m = re.match(r'^([0-9A-Za-z][0-9A-Za-z.\-]*)\s*·\s*(.+)$', part)
        if not m:
            continue
        code, venue = m.group(1).upper(), m.group(2)
        if '.' in code:
            cand = code                                    # ya trae su sufijo ("0981.HK · HKEX")
        elif 'OTC' in venue.upper() or venue.strip().upper().startswith(('NYSE', 'NASDAQ')):
            cand = code.replace('.', '-')
        elif 'Euronext' in venue and code in _EURONEXT:
            cand = f'{code}.{_EURONEXT[code]}'
        else:
            cand = None
            for key, suf in _VENUE_SUFFIX:
                if key in venue:
                    cand = f'{code.zfill(4) if suf == "HK" and code.isdigit() else code}.{suf}'
                    break
        if cand and _YAHOO_RX.match(cand):
            out.append(cand)
    return out


def _indice_identificadores(nodos):
    """{tipo: {clave: id}} + 'conflictos' {(tipo, clave): [ids]} de la generación. Primero lo DECLARADO (ids,
    listings, mkt), después las claves blandas derivadas del texto del catálogo (nunca pisan ni crean conflictos)."""
    try:
        from core.import_normalize import yahoo_symbol_for
    except Exception:  # noqa: BLE001
        yahoo_symbol_for = None
    tablas = {k: {} for k in _ID_KINDS}
    conflictos = {}

    def put(kind, key, nid):
        if not key:
            return
        tb = tablas[kind]
        cur = tb.get(key)
        if cur is None:
            tb[key] = nid
        elif cur != nid:
            lst = conflictos.setdefault((kind, key), [cur])
            if nid not in lst:
                lst.append(nid)

    for nid, n in nodos.items():
        ids = n.get('ids') if isinstance(n.get('ids'), dict) else {}
        if ids.get('lei'):
            put('lei', str(ids['lei']).strip().upper(), nid)
        for x in _lista(ids.get('isin')):
            put('isin', str(x).strip().upper(), nid)
        if ids.get('cik'):
            put('cik', _cik(ids['cik']), nid)
        qid = ids.get('qid') or ids.get('wikidata_qid')
        if qid:
            put('qid', str(qid).strip().upper(), nid)
        for x in _lista(ids.get('figi')):
            put('figi', str(x).strip().upper(), nid)
        if ids.get('domain'):
            put('domain', _dominio(ids['domain']), nid)
        if ids.get('yahoo_symbol'):
            put('yahoo', str(ids['yahoo_symbol']).strip().upper(), nid)
        mic = ids.get('mic') or ids.get('exchange_mic')
        if ids.get('ticker') and mic:
            put('ticker_mic', (str(ids['ticker']).strip().upper(), str(mic).strip().upper()), nid)
        mkt = str(n.get('mkt') or '').strip().upper()
        if mkt:
            put('yahoo', mkt, nid)                 # el símbolo de Yahoo del catálogo (con su sufijo de bolsa)
        for l in _lista(n.get('listings')):
            if not isinstance(l, dict):
                continue
            ys = str(l.get('yahoo_symbol') or '').strip().upper()
            if ys:
                put('yahoo', ys, nid)
            sym, lmic = str(l.get('symbol') or l.get('ticker') or '').strip().upper(), \
                str(l.get('mic') or l.get('exchange_mic') or '').strip().upper()
            if sym and lmic:
                put('ticker_mic', (sym, lmic), nid)
                if yahoo_symbol_for is not None:
                    put('yahoo', yahoo_symbol_for(sym, lmic), nid)
            if l.get('isin'):
                put('isin', str(l['isin']).strip().upper(), nid)
            if l.get('figi'):
                put('figi', str(l['figi']).strip().upper(), nid)
    # claves blandas del texto del catálogo: solo donde no hay nada declarado, sin conflictos
    yahoo = tablas['yahoo']
    for nid, n in nodos.items():
        for cand in _simbolos_del_catalogo(n):
            yahoo.setdefault(cand, nid)
    # un identificador reclamado por dos empresas no identifica a ninguna
    for (kind, key) in conflictos:
        tablas[kind].pop(key, None)
    tablas['conflictos'] = conflictos
    return tablas


def _umbrales_nombre():
    """(escritura, posible duplicado) de policy.import si está en el release; si no, los de este módulo."""
    try:
        from core import governance
        p = governance.section('policy.import') or {}
        return int(p.get('name_write_threshold', UMBRAL_ESCRITURA)), int(p.get('name_possible_threshold', UMBRAL_BUSQUEDA))
    except Exception:  # noqa: BLE001
        return UMBRAL_ESCRITURA, UMBRAL_BUSQUEDA


def resolve_ids(ids, name=None):
    """Contrato E1.6 (lote K): identificadores → {'id', 'method', 'score', 'conflicts': [...]} o None.

    `ids` puede traer lei, isin (uno o lista), cik, qid (wikidata_qid), figi, yahoo_symbol, ticker + mic
    (exchange_mic), domain. Orden de fuerza: lei > isin/cik/qid > figi > yahoo_symbol / ticker@MIC > dominio (solo
    CANDIDATO, nunca coincidencia) > nombre ≥ umbral de escritura (60-84 = 'possible_duplicate' en conflicts, NO
    coincidencia). Un ticker sin MIC NUNCA resuelve. Identificadores que apuntan a empresas distintas se devuelven
    como `id_conflict`; uno que dos empresas reclaman, como `ambiguous_id` (y no elige). Sin coincidencia pero con
    conflictos → {'id': None, 'method': None, 'score': 0, 'conflicts': [...]}; sin nada → None.
    Lee el índice de la generación vigente (Postgres: props ids/listings/other_names; catálogo: ticker/mkt)."""
    ids = dict(ids or {})
    idx = get_index()
    tb = idx.get('identificadores') or _indice_identificadores(idx['nodos'])
    nodos = idx['nodos']
    conflicts, hits = [], []

    def look(kind, key, method, score):
        if not key:
            return
        conf = tb['conflictos'].get((kind, key))
        if conf:
            conflicts.append({'kind': 'ambiguous_id', 'method': method, 'ids': list(conf), 'key': str(key)})
            return
        oid = tb[kind].get(key)
        if oid and oid in nodos:
            hits.append((method, oid, score))

    if ids.get('lei'):
        look('lei', str(ids['lei']).strip().upper(), 'lei', _ID_SCORE['lei'])
    for x in _lista(ids.get('isin')):
        look('isin', str(x).strip().upper(), 'isin', _ID_SCORE['isin'])
    if ids.get('cik'):
        look('cik', _cik(ids['cik']), 'cik', _ID_SCORE['cik'])
    qid = ids.get('qid') or ids.get('wikidata_qid')
    if qid:
        look('qid', str(qid).strip().upper(), 'qid', _ID_SCORE['qid'])
    for x in _lista(ids.get('figi')):
        look('figi', str(x).strip().upper(), 'figi', _ID_SCORE['figi'])
    if ids.get('yahoo_symbol'):
        look('yahoo', str(ids['yahoo_symbol']).strip().upper(), 'yahoo_symbol', _ID_SCORE['yahoo_symbol'])
    mic = ids.get('mic') or ids.get('exchange_mic')
    if ids.get('ticker') and mic:
        t, m = str(ids['ticker']).strip().upper(), str(mic).strip().upper()
        formas = [t]
        if m == 'XHKG' and t.isdigit() and len(t) < 4:
            formas.append(t.zfill(4))                   # HKEX: "981" y "0981" son el mismo código
        for f in formas:
            look('ticker_mic', (f, m), 'ticker_mic', _ID_SCORE['ticker_mic'])
            try:
                from core.import_normalize import yahoo_symbol_for
                look('yahoo', yahoo_symbol_for(f, m), 'ticker_mic', _ID_SCORE['ticker_mic'])
            except Exception:  # noqa: BLE001
                pass
    # un ticker SIN bolsa se ignora a propósito ("3750" → None): el mismo código vive en HK, Tokio y Taipéi

    best = None
    for method, oid, score in hits:
        if best is None:
            best = {'id': oid, 'method': method, 'score': score}
        elif oid != best['id'] and not any(c.get('kind') == 'id_conflict' and c.get('id') == oid
                                           and c.get('method') == method for c in conflicts):
            conflicts.append({'kind': 'id_conflict', 'method': method, 'id': oid, 'vs': best['id']})
    if ids.get('domain'):
        cand = tb['domain'].get(_dominio(ids['domain']))
        if cand and best is None:
            conflicts.append({'kind': 'domain_candidate', 'id': cand})
        elif cand and cand != best['id']:
            conflicts.append({'kind': 'domain_conflict', 'id': cand, 'vs': best['id']})
    if name and str(name).strip():
        escr, posible = _umbrales_nombre()
        r = resolve(str(name)[:120], umbral=min(escr, posible))
        if r is not None:
            if best is None and r['score'] >= escr:
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


def identifier_conflicts():
    """Identificadores que dos empresas reclaman en la generación vigente: [{'kind','key','ids'}] (🩺 / revisión)."""
    tb = (get_index().get('identificadores') or {}).get('conflictos') or {}
    return [{'kind': k, 'key': key if isinstance(key, str) else '@'.join(key), 'ids': list(v)}
            for (k, key), v in sorted(tb.items(), key=lambda kv: (kv[0][0], str(kv[0][1])))]


def get_index(force=False, snapshot_path=None):
    """Índice de la generación VIGENTE (se reconstruye solo si cambió). `snapshot_path` = un archivo aparte
    (no toca el índice compartido)."""
    global _index
    if snapshot_path:
        return _build_index(snapshot_path)
    from core.hotviews import hot
    view = hot.graph()
    cur = _index
    if cur is not None and not force and cur.get('generation') == view.generation:
        return cur
    with _lock:
        if _index is None or force or _index.get('generation') != view.generation:
            _index = _build_index(view=view)
        return _index


def graph_version():
    """La generación del grafo que usa este módulo (tests/test_ops_single_source.py)."""
    return get_index().get('generation')


def entity_ids_for(eid):
    """[eid] + los ids VIEJOS (alias del catálogo y fusiones) que hoy apuntan a eid.
    Revisión G1b/G1d: lo guardado con un id que luego se fusionó (claims de
    investigación, memos) sigue apareciendo bajo la empresa canónica."""
    if not eid:
        return []
    try:
        tbl = get_index().get('alias_inv') or {}
    except Exception:  # noqa: BLE001
        tbl = {}
    return [eid] + [a for a in tbl.get(eid, []) if a != eid]


def resolve(texto, umbral=UMBRAL_BUSQUEDA):
    """Resuelve un texto libre a una entidad del grafo.

    Devuelve `{id, label, score, method, matched}` o None si no llega al
    umbral. `method` dice CÓMO se resolvió — auditable, y permite exigir más
    rigor a quien escribe en la ontología que a quien solo busca.

    Escalera de mayor a menor certeza:
      100 id exacto · 98 ticker · 95 label exacto · 92 alias
      88 label sin sufijo societario ('NVIDIA Corporation' → Nvidia)
      80 alias de voz del navegador ('en vidia' → Nvidia; solo búsqueda)
      70 prefijo único · 60 subcadena única
    """
    if not texto or not str(texto).strip():
        return None
    idx = get_index()
    crudo = str(texto).strip()
    n = norm(crudo)
    if not n:
        return None

    def hit(nid, score, method, matched):
        if score < umbral:
            return None
        nodo = idx['nodos'].get(nid) or {}
        return {'id': nid, 'label': nodo.get('label') or nid,
                'score': score, 'method': method, 'matched': matched}

    if n in idx['por_id']:
        return hit(idx['por_id'][n], 100, 'id', crudo)

    up = crudo.upper().strip()
    if up in idx['por_ticker']:
        return hit(idx['por_ticker'][up], 98, 'ticker', up)

    if n in idx['por_label']:
        return hit(idx['por_label'][n], 95, 'label', crudo)

    if n in idx['por_alias']:
        return hit(idx['por_alias'][n], 92, 'alias', crudo)

    corto = strip_suffix(crudo)
    if corto and corto in idx['por_alias']:
        return hit(idx['por_alias'][corto], 90, 'alias_sufijo', corto)
    if corto and corto in idx['por_label_corto']:
        return hit(idx['por_label_corto'][corto], 88, 'label_sufijo', corto)
    if corto and corto in idx['por_label']:
        return hit(idx['por_label'][corto], 88, 'label_sufijo', corto)

    # alias de voz (texto entero, sin palabras vacías del dictado): 80 = búsqueda sí, ESCRITURA (85) nunca
    voz = idx.get('por_voz') or {}
    if voz:
        sin_stop = ' '.join(w for w in n.split() if w not in (idx.get('stopwords') or ())) or n
        for k in (n, sin_stop):
            if k in voz:
                return hit(voz[k], 80, 'voice_alias', k)

    # Prefijo/subcadena SOLO si son inequívocos: dos candidatos = ninguno.
    # Un match ambiguo que se resuelve "a lo que salga" corrompe el grafo.
    # E1.5: los candidatos salen del índice (prefijos + trigramas) en vez de recorrer todas las etiquetas; los
    # conjuntos son los mismos que el recorrido lineal sobre por_label + por_label_corto (y los alias de voz).
    if len(n) >= 4:
        ix = _indice_resolver(idx)
        pref = {nid for _k, nid in ix['etiquetas'].prefijo(n)}
        if len(pref) == 1:
            return hit(pref.pop(), 70, 'prefijo', n)
        sub = {nid for _k, nid in ix['etiquetas'].contiene(n)}
        if len(sub) == 1:
            return hit(sub.pop(), 60, 'subcadena', n)
        # prefijo de un alias de voz ('taiwan semi' → 'taiwan semiconductor' → TSMC), solo si no hubo otro
        # candidato y es inequívoco — mismo paso 5 que engine/resolve.js
        if voz and not pref and not sub:
            vp = {nid for _k, nid in ix['voz'].prefijo(n)}
            if len(vp) == 1:
                return hit(vp.pop(), 70, 'voice_prefijo', n)

    return None


# ── E1.5 (docs/expansion/EXPANSION_5K.md): búsqueda por índice ───────────────────────────────────────────
# A 5k empresas el recorrido lineal (difuso de resolve + search_companies del MCP) pasaba de 50 a 224 ms. Por
# generación del grafo se arma UNA vez (perezoso: en la primera búsqueda que lo necesita) un índice de PREFIJOS
# (claves ordenadas + bisect) y de TRIGRAMAS (subcadena: se verifica con `in` solo la lista del trigrama más raro
# de la consulta) sobre id/etiqueta/ticker/alias/alias de voz, más la descripción normalizada de cada nodo. El
# índice solo ELIGE candidatos: el puntaje es la MISMA escalera de antes, así que el resultado es idéntico al
# recorrido lineal (tests/test_scale_search.py lo compara en 200 consultas, a 937 y a 5k).
_LOCK_BUSQ = threading.Lock()
_DESC_KEYS = ('role_en', 'supplies_en', 'role', 'supplies')


def _trigramas(s):
    return {s[i:i + 3] for i in range(len(s) - 2)}


class _Claves:
    """Cadenas normalizadas → cargas (ids o posiciones). `prefijo(n)`/`contiene(n)` devuelven [(clave, carga)] de las
    claves que empiezan por n / contienen n — exactamente las que daría recorrerlas todas."""
    __slots__ = ('claves', 'carga', 'tri')

    def __init__(self, pares, trigramas=True):
        por = {}
        for k, v in pares:
            if k:
                por.setdefault(k, []).append(v)
        self.claves = sorted(por)
        self.carga = [tuple(por[k]) for k in self.claves]
        self.tri = None
        if trigramas:
            tri = {}
            for i, k in enumerate(self.claves):
                for g in _trigramas(k):
                    lst = tri.get(g)
                    if lst is None:
                        tri[g] = lst = array('I')
                    lst.append(i)
            self.tri = tri

    def _salida(self, posiciones):
        cl, ca = self.claves, self.carga
        return [(cl[i], v) for i in posiciones for v in ca[i]]

    def prefijo(self, n):
        cl = self.claves
        i = j = bisect_left(cl, n)       # las claves con prefijo n son un tramo contiguo desde bisect_left(n)
        while j < len(cl) and cl[j].startswith(n):
            j += 1
        return self._salida(range(i, j))

    def contiene(self, n):
        cl = self.claves
        if self.tri is None or len(n) < 3:
            return self._salida(i for i, k in enumerate(cl) if n in k)
        rara = None
        for g in _trigramas(n):          # toda clave que contiene n contiene CADA trigrama de n
            p = self.tri.get(g)
            if p is None:
                return []
            if rara is None or len(p) < len(rara):
                rara = p
        return self._salida(i for i in rara if n in cl[i])


def _indice_resolver(idx):
    """La parte del índice que usa resolve(): etiquetas (+ sin sufijo) y alias de voz. Una vez por índice."""
    ix = idx.get('_ix_resolver')
    if ix is not None:
        return ix
    with _LOCK_BUSQ:
        ix = idx.get('_ix_resolver')
        if ix is None:
            ix = {'etiquetas': _Claves(list(idx['por_label'].items()) + list(idx['por_label_corto'].items())),
                  'voz': _Claves((idx.get('por_voz') or {}).items(), trigramas=False)}
            idx['_ix_resolver'] = ix
        return ix


def _indice_busqueda(idx):
    """La parte del índice de search_scores(): campos normalizados por nodo + prefijos/trigramas + alias."""
    ix = idx.get('_ix_busqueda')
    if ix is not None:
        return ix
    with _LOCK_BUSQ:
        ix = idx.get('_ix_busqueda')
        if ix is not None:
            return ix
        t0 = time.perf_counter()
        nodos = idx['nodos']
        ids = tuple(nodos)
        lab = tuple(norm(n.get('label') or '') for n in nodos.values())
        nidn = tuple(norm(i) for i in ids)
        sym = tuple((n.get('mkt') or '').upper() for n in nodos.values())
        desc = tuple(norm(' '.join(str(n.get(k) or '') for k in _DESC_KEYS)) for n in nodos.values())
        por_sym = {}
        for i, s in enumerate(sym):
            if s:
                por_sym.setdefault(s, []).append(i)
        ix = {'ids': ids, 'lab': lab, 'nidn': nidn, 'sym': sym, 'desc': desc, 'por_sym': por_sym,
              'lab_ix': _Claves((lab[i], i) for i in range(len(ids))),
              'nid_ix': _Claves(((nidn[i], i) for i in range(len(ids))), trigramas=False),
              'alias_ix': _Claves(idx['por_alias'].items(), trigramas=False)}
        ix['ms'] = round((time.perf_counter() - t0) * 1000, 1)
        idx['_ix_busqueda'] = ix
        return ix


def _puntaje_nodo(n, up, rx, lab, nidn, sym, desc):
    """LA escalera por nodo de search_companies (la de siempre): ticker 98 · etiqueta 95 · prefijo 75 · prefijo del
    id 72 · palabra 66 · subcadena 60 · descripción 40. → (puntaje, método) o None."""
    if sym and sym == up:
        return 98, 'ticker'
    if lab == n:
        return 95, 'label'
    if lab.startswith(n):
        return 75, 'prefix'
    if nidn.startswith(n):
        return 72, 'id_prefix'
    if len(n) >= 3 and rx.search(lab):
        return 66, 'word'
    if len(n) >= 3 and n in lab:
        return 60, 'substring'
    if len(n) >= 4 and n in desc:
        return 40, 'description'
    return None


def search_scores(query):
    """Búsqueda de empresas (MCP search_companies): {id: (puntaje, método)} con la escalera de siempre —
    resolve() con el umbral de búsqueda → alias exacto 92 / prefijo de alias 78 → la escalera por nodo — pero con
    candidatos del índice de la generación vigente (sin recorrer todos los nodos). Ante empate gana lo anterior."""
    q = str(query or '').strip()
    n = norm(q)
    if not n:
        return {}
    idx = get_index()
    nodos = idx['nodos']
    cands = {}

    def add(nid, score, method):
        if nid in nodos and score > cands.get(nid, (0, ''))[0]:
            cands[nid] = (score, method)

    top = resolve(q[:120], umbral=UMBRAL_BUSQUEDA)
    if top:
        add(top['id'], top['score'], top['method'])
    ix = _indice_busqueda(idx)
    a = idx['por_alias'].get(n)
    if a is not None:
        add(a, 92, 'alias')
    if len(n) >= 3:
        for k, nid in ix['alias_ix'].prefijo(n):
            if k != n:
                add(nid, 78, 'alias_prefix')
    up = q.upper()
    pos = set(ix['por_sym'].get(up, ()))
    pos.update(i for _k, i in ix['lab_ix'].prefijo(n))
    pos.update(i for _k, i in ix['nid_ix'].prefijo(n))
    if len(n) >= 3:
        pos.update(i for _k, i in ix['lab_ix'].contiene(n))
    if len(n) >= 4:
        pos.update(i for i, d in enumerate(ix['desc']) if n in d)
    rx = re.compile(r'(^|\s)' + re.escape(n)) if len(n) >= 3 else None
    ids, lab, nidn, sym, desc = ix['ids'], ix['lab'], ix['nidn'], ix['sym'], ix['desc']
    for i in pos:
        r = _puntaje_nodo(n, up, rx, lab[i], nidn[i], sym[i], desc[i])
        if r is not None:
            add(ids[i], r[0], r[1])
    return cands


def resolve_many(textos, umbral=UMBRAL_BUSQUEDA):
    """Resuelve una lista; devuelve (resueltos {texto: info}, no_resueltos[])."""
    ok, fallos = {}, []
    for t in textos or []:
        r = resolve(t, umbral=umbral)
        if r:
            ok[t] = r
        else:
            fallos.append(t)
    return ok, fallos
