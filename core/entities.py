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
import os
import re
import threading
import unicodedata

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SNAPSHOT = os.path.join(_ROOT, 'data', 'grafo_v0.json')

_lock = threading.Lock()
_index = None   # se construye una vez, es de solo lectura

# Umbrales recomendados. Distintos a propósito: escribir en la ontología con un
# match flojo corrompe el grafo en silencio; buscar desde la UI no.
UMBRAL_ESCRITURA = 85   # agentes que crean hechos: solo exacto/ticker/alias
UMBRAL_BUSQUEDA = 60    # búsqueda humana: admite prefijo/fuzzy

_PUNCT = re.compile(r'[^\w\s]', re.UNICODE)
_WS = re.compile(r'\s+')
# Sufijos societarios: "NVIDIA Corporation" y "NVIDIA" son la misma empresa.
_SUFIJOS = (
    'corporation', 'corp', 'incorporated', 'inc', 'limited', 'ltd', 'llc',
    'plc', 'sa', 'sas', 'ag', 'nv', 'bv', 'co', 'company', 'holdings',
    'holding', 'group', 'technologies', 'technology', 'systems',
)


def norm(txt):
    """minúsculas + sin acentos + sin puntuación + espacios colapsados."""
    if not txt:
        return ''
    s = unicodedata.normalize('NFD', str(txt))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
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


def _build_index(snapshot_path=None):
    """Índice de resolución desde el snapshot canónico. Incluye la tabla de
    alias del merge (`node_id_alias`), que antes no cruzaba al servidor."""
    path = snapshot_path or _SNAPSHOT
    with open(path, encoding='utf-8') as fh:
        snap = json.load(fh)

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

    return {'nodos': nodos, 'por_id': por_id, 'por_ticker': por_ticker,
            'por_label': por_label, 'por_label_corto': por_label_corto,
            'por_alias': por_alias, 'alias_tbl': alias_tbl}


def get_index(force=False, snapshot_path=None):
    global _index
    with _lock:
        if _index is None or force:
            _index = _build_index(snapshot_path)
        return _index


def resolve(texto, umbral=UMBRAL_BUSQUEDA):
    """Resuelve un texto libre a una entidad del grafo.

    Devuelve `{id, label, score, method, matched}` o None si no llega al
    umbral. `method` dice CÓMO se resolvió — auditable, y permite exigir más
    rigor a quien escribe en la ontología que a quien solo busca.

    Escalera de mayor a menor certeza:
      100 id exacto · 98 ticker · 95 label exacto · 92 alias
      88 label sin sufijo societario ('NVIDIA Corporation' → Nvidia)
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

    # Prefijo/subcadena SOLO si son inequívocos: dos candidatos = ninguno.
    # Un match ambiguo que se resuelve "a lo que salga" corrompe el grafo.
    if len(n) >= 4:
        claves = list(idx['por_label'].items()) + list(idx['por_label_corto'].items())
        pref = {nid for k, nid in claves if k.startswith(n)}
        if len(pref) == 1:
            return hit(pref.pop(), 70, 'prefijo', n)
        sub = {nid for k, nid in claves if n in k}
        if len(sub) == 1:
            return hit(sub.pop(), 60, 'subcadena', n)

    return None


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
