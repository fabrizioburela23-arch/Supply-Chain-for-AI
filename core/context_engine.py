"""core/context_engine.py — EL motor de contexto (ARQUITECTURA_V2 §13; BRECHAS bloque 4: L4-01, L4-05, L4-10).

Antes cada parte de la app armaba por su cuenta lo que le contaba a la IA (chat, investigación, habilidades de los
agentes, búsqueda profunda, MCP) y hasta detectaban empresas DISTINTAS en la misma pregunta (3 detectores). Ahora:

  1. detect(texto)          UN solo detector de empresas (nombre exacto, nombre sin mayúsculas/tildes/espacios,
                            ticker real; los tickers que son palabras —"AI", "NOW"— solo cuentan por su nombre).
                            core/live_facts.detect_entities, core/semantic.extract_companies y el chat delegan aquí.
  2. intent(texto)          'impact' | 'upstream' | 'downstream' | 'general' (reglas, sin IA).
  3. relevance(semillas)    R(v|Q) = π_Q(v) · (ε + I_v) · (1 + λ_u·U_v)            (§13.3; frescura = 1: estructura)
                              π_Q  = PageRank personalizado desde las semillas sobre el grafo de FLUJO, orientado según
                                     la intención (proveedores → hacia atrás, clientes → hacia adelante); en preguntas
                                     de impacto, además Ψ[v, S] de la vista Impact (el MISMO kernel, propagate_many).
                              I_v  = importancia sistémica: Σ impacto de su colapso (vista Impact), en escala log 0-1.
                              U_v  = 1 − confianza media de sus vínculos (lo incierto que importa se MUESTRA).
                            Arista: R(e=(u,v)|Q) = √(R(u)·R(v)) · w̃ · c.
  4. pack(...)              empaquetado bajo presupuesto: cobertura ponderada (facility location, monótona y
                            submodular) con voraz perezoso por ΔF/costo y comparación con el mejor elemento solo
                            (≥ ½(1−1/e) del óptimo); lo descartado se resume con estadísticos suficientes (cola).
  5. subgraph(...)          vecindario de FLUJO ordenado por R + cola ("otros 230 vínculos: 41 % del peso…").
     pack_supply_chain(...) lo mismo sobre un resultado ya calculado de get_supply_chain (chat y MCP).
  6. FactBook               tabla de hechos [F#] con fuente y as_of (el chat la devuelve en `facts`; la ficha
                            chat.answer del libro de decisiones los registra).

Sin IA, sin red, sin base: lee la generación vigente del grafo (core/hotviews/hot.graph()) y lo derivado se arma UNA
vez por generación (hot.cached). Determinista: mismo grafo + misma pregunta → mismo contexto, mismo orden.
"""
import heapq
import json
import logging
import math
import re
import threading
import unicodedata
from collections import OrderedDict
from datetime import datetime, timezone

log = logging.getLogger('khipu')

METHOD = 'R(v|Q)=PPR_flow(S_Q)·(ε+I_v)·(1+λ·U_v); R(e)=√(R(u)R(v))·w̃·c; facility-location greedy under budget'
EPS = 0.15            # piso del término de impacto: un nodo cercano poco sistémico igual entra
LAMBDA_U = 0.2        # peso de la incertidumbre (pequeño: marca, no domina)
BETA = 0.85           # PageRank personalizado: probabilidad de seguir caminando
PPR_ITERS = 40
W_REF = 3.0           # peso "fuerte" del catálogo (1-3): w̃ = min(1, w / 3)
IMPACT_MIX = 0.25     # en preguntas de impacto: π = max(Ψ[v,S], 0.25·PPR)
DEFAULT_BUDGET_CHARS = 6000
MAX_DEPTH = 3

# ════════════════════════════════════════════════════════════════════════════
# 1. UN detector de entidades
# ════════════════════════════════════════════════════════════════════════════
MAX_ENTITIES = 6
# tickers que también son palabras o siglas comunes: "AI" (C3.ai) hacía que TODO texto sobre IA trajera los
# datos de C3.ai (visto en la simulación del IPO de OpenAI, 2026-10-05). Solo cuentan por su NOMBRE.
AMBIGUOUS_TICKERS = {'AI', 'IT', 'ON', 'ALL', 'NOW', 'ONE', 'ARE', 'CAN', 'GO', 'SO', 'BIG', 'LOW', 'KEY', 'ANY', 'DO',
                     'SEE', 'RUN', 'EV', 'US', 'UK', 'EU', 'CEO', 'CFO', 'IPO', 'ETF', 'GDP', 'USD', 'HBM', 'GPU', 'CPU',
                     'TPU', 'PPA', 'LLM', 'API', 'IOT', 'OPEN', 'LIFE', 'REAL', 'PLAY', 'CASH', 'BEST', 'FAST', 'NEXT',
                     'SAFE', 'TRUE', 'WELL', 'HOLD', 'GOOD', 'PEAK', 'CARE', 'CORE', 'EDGE', 'DATA', 'GRID', 'NET'}
# 2026-10-06 (Fabrizio escribe en el celular "analiza open ai", "que tal nvidia", "sk hynix"): también sin
# mayúsculas, sin tildes y sin espacios ("open ai" → OpenAI). Para no confundir palabras comunes con empresas, la
# versión tolerante exige ≥ 5 letras y excluye nombres que son palabras de uso diario; esos siguen detectándose
# con su mayúscula (pasada exacta).
COMMON_WORDS = {'switch', 'shell', 'disco', 'canon', 'cohere', 'glean', 'formic', 'imbue', 'oneline', 'dayone',
                'terna', 'sessa', 'apple', 'oracle', 'amazon', 'block', 'unity', 'square', 'target', 'visa', 'ring'}
COMMON_SHORT = {'meta', 'vale', 'toto', 'wing', 'ring', 'visa', 'nuro', 'rumo', 'sify', 'hoya', 'adia', 'cohu',
                'enel', 'isda', 'kbra', 'lseg', 'msci', 'mufg', 'nbim', 'pboc', 'smbc', 'smee', 'snap', 'data'}
SHORT_OK = {'amd'}
# revisión (2026-10-13): países/regiones y palabras de diccionario que solo llegaban al mapa tolerante como ALIAS
# ("State Grid (China)" → 'china', "PIF (Saudi Arabia)", cohete Electron, robot Digit) hacían que "¿Qué pasa si
# China bloquea Taiwán?" detectara State Grid. Nunca cuentan en la pasada tolerante; las etiquetas con su
# mayúscula siguen en la pasada exacta.
GEO_WORDS = {
    'china', 'taiwan', 'japan', 'japon', 'korea', 'corea', 'southkorea', 'coreadelsur', 'india', 'usa', 'eeuu',
    'estadosunidos', 'unitedstates', 'europe', 'europa', 'germany', 'alemania', 'france', 'francia', 'saudiarabia',
    'arabiasaudita', 'israel', 'russia', 'rusia', 'brasil', 'brazil', 'mexico', 'canada', 'reinounido',
    'unitedkingdom', 'singapore', 'singapur', 'netherlands', 'paisesbajos', 'holanda', 'spain', 'espana', 'italy',
    'italia', 'australia', 'chile', 'peru', 'argentina', 'asia', 'africa', 'hongkong', 'vietnam', 'indonesia',
    'malaysia', 'malasia', 'thailand', 'tailandia', 'iran', 'ukraine', 'ucrania', 'qatar', 'catar', 'emirates',
    'switzerland', 'suiza', 'sweden', 'suecia', 'norway', 'noruega', 'finland', 'finlandia', 'denmark', 'dinamarca',
    'ireland', 'irlanda', 'belgium', 'belgica', 'poland', 'polonia', 'turkey', 'turquia', 'egypt', 'egipto',
    'philippines', 'filipinas', 'europeanunion', 'unioneuropea', 'middleeast', 'orientemedio'}
ALIAS_COMMON = {'electron', 'digit'}

_DET_LOCK = threading.Lock()
_DET = {'gen': None, 'rx': None, 'by_label': None, 'cmap': None}


def _collapse(s):
    s = unicodedata.normalize('NFD', str(s or '').lower())
    return re.sub(r'[^a-z0-9]', '', ''.join(c for c in s if unicodedata.category(c) != 'Mn'))


def _detector(idx):
    """(regex de etiquetas exactas, etiqueta→id, mapa colapsado) — UNA vez por generación del índice (antes se
    armaba una vez por PROCESO: una empresa incorporada después nunca se detectaba)."""
    gen = idx.get('generation')
    cur = _DET
    if cur['rx'] is not None and cur['gen'] == gen:
        return cur['rx'], cur['by_label'], cur['cmap']
    with _DET_LOCK:
        if _DET['rx'] is not None and _DET['gen'] == gen:
            return _DET['rx'], _DET['by_label'], _DET['cmap']
        by_label = {}
        for nid, n in idx['nodos'].items():
            lab = (n.get('label') or '').strip()
            if not lab:
                continue
            by_label.setdefault(lab, nid)
            # "Microsoft (Azure)", "Alphabet (Google Cloud)": también cuenta el nombre sin el paréntesis
            base = re.split(r'\s*\(', lab)[0].strip()
            if base and base != lab and len(base) >= 4:
                by_label.setdefault(base, nid)
        labels = sorted((x for x in by_label if len(x) >= 4), key=len, reverse=True)
        rx = re.compile(r'(?<![\w])(' + '|'.join(re.escape(x) for x in labels) + r')(?![\w])') if labels else None
        cmap = {}

        def add(key, nid):
            k = _collapse(key)
            if k in COMMON_WORDS or k in GEO_WORDS or k in ALIAS_COMMON:
                return
            if len(k) >= 5 or (len(k) == 4 and k not in COMMON_SHORT) or k in SHORT_OK:
                cmap.setdefault(k, nid)
        for nid, n in idx['nodos'].items():
            lab = (n.get('label') or '').strip()
            add(nid, nid)
            if lab:
                add(lab, nid)
                add(re.split(r'\s*\(', lab)[0], nid)
        for al, nid in (idx.get('por_alias') or {}).items():
            if isinstance(nid, str):
                add(al, nid)
        _DET.update(gen=gen, rx=rx, by_label=by_label, cmap=cmap)
        return rx, by_label, cmap


def _fuzzy_hits(text, cmap):
    """(pos, id) por n-gramas de 1-3 palabras comparados sin mayúsculas/tildes/espacios."""
    words = [(m.start(), m.group(0)) for m in re.finditer(r'[\w&.\-]+', text)]
    out, used = [], set()
    for n in (3, 2, 1):
        for i in range(len(words) - n + 1):
            if any(j in used for j in range(i, i + n)):
                continue
            nid = cmap.get(_collapse(''.join(w for _p, w in words[i:i + n])))
            if nid:
                out.append((words[i][0], nid))
                used.update(range(i, i + n))
    return out


def detect(text, limit=MAX_ENTITIES, resolve_short=False):
    """Ids del grafo mencionados en `text`, en orden de aparición (sin repetir).

    resolve_short=True: si no se detecta nada y el texto es corto (≤ 40 caracteres, p. ej. "tsmc?"), se intenta
    el resolvedor de core/entities (prefijo/subcadena inequívocos) sobre el texto entero."""
    from core.entities import get_index
    if not text:
        return []
    text = str(text)
    idx = get_index()
    rx, by_label, cmap = _detector(idx)
    hits = []   # (pos, id)
    try:
        hits.extend(_fuzzy_hits(text, cmap))
    except Exception:  # noqa: BLE001
        pass
    if rx is not None:
        for m in rx.finditer(text):
            nid = by_label.get(m.group(1))
            if nid:
                hits.append((m.start(), nid))
    for m in re.finditer(r'(?<![\w.$])([A-Z]{2,5}(?:\.[A-Z]{1,2})?)(?![\w])', text):
        if m.group(1) in AMBIGUOUS_TICKERS:
            continue
        nid = idx['por_ticker'].get(m.group(1))
        if nid:
            hits.append((m.start(), nid))
    out = []
    for _pos, nid in sorted(hits):
        if nid not in out:
            out.append(nid)
        if len(out) >= limit:
            break
    if not out and resolve_short:
        short = re.sub(r'[¿?¡!.,]', ' ', text).strip()
        if 0 < len(short) <= 40:
            nid = canon(short)
            if nid:
                out = [nid]
    return out


def canon(x, umbral=None):
    """Texto/ticker/id/alias → id CANÓNICO del grafo, o None (core/entities.resolve, umbral de BÚSQUEDA)."""
    if x is None or not str(x).strip():
        return None
    from core.entities import UMBRAL_BUSQUEDA, resolve
    try:
        r = resolve(str(x)[:120], umbral=UMBRAL_BUSQUEDA if umbral is None else umbral)
    except Exception:  # noqa: BLE001
        return None
    return r['id'] if r else None


# ════════════════════════════════════════════════════════════════════════════
# 2. intención
# ════════════════════════════════════════════════════════════════════════════
_INTENT_RX = (
    ('impact', re.compile(r'qu[eé] pasa(r[ií]a)? si|si (cae|colapsa|falla|cierra|bloquea|sancion)|what if|'
                          r'if .{0,40}(fails|collapses|falls|is blocked|is banned)|impact|golpe|qui[eé]n(es)? '
                          r'(sufre|pierde|caer)|who (loses|suffers|gets hit)|expuest|exposed|contagi|escenario|'
                          r'scenario|shock|choque|bloqueo|blockade|ban\b|prohibici|aranc|tariff', re.I)),
    ('downstream', re.compile(r'a qui[eé]n(es)? (les? )?(vende|provee|abastece)|who (does .{0,30})?(sells?|supplies) to|'
                              r'who buys', re.I)),
    ('upstream', re.compile(r'proveed|supplier|depend|insumo|input|qui[eé]n(es)? (les? )?(vende|provee|fabrica)|'
                            r'who (sells|supplies|makes)|aguas arriba|upstream|fabrica (sus|los)', re.I)),
    ('downstream', re.compile(r'client|customer|a qui[eé]n (le )?vende|qui[eé]n (le )?compra|who buys|'
                              r'aguas abajo|downstream|arrastra', re.I)),
)


def intent(text):
    t = str(text or '')
    for name, rx in _INTENT_RX:
        if rx.search(t):
            return name
    return 'general'


# ════════════════════════════════════════════════════════════════════════════
# 3. relevancia R(v|Q) sobre la generación vigente
# ════════════════════════════════════════════════════════════════════════════
class _Flow:
    """Lo que el motor necesita del grafo, armado UNA vez por generación (hot.cached)."""
    __slots__ = ('ids', 'idx', 'meta', 'out', 'inn', 'rel_out', 'rel_in', 'fwd', 'rev', 'sym', 'imp', 'unc',
                 'generation', 'graph_version', 'as_of', 'source', 'lru', 'lru_lock')


def _trust(link):
    """(verified, conf) del vínculo: lo que trae el grafo; si no, la regla del texto (G4c)."""
    from ontology.vocabulary import UNVERIFIED_CONF, UNVERIFIED_RX
    conf, ver = link.get('conf'), link.get('verified')
    if conf is not None or ver is not None:
        try:
            conf = None if conf is None else max(0.0, min(1.0, float(conf)))
        except (TypeError, ValueError):
            conf = None
        if ver is None:
            ver = conf is None or conf >= 1.0
        if conf is None:
            conf = 1.0 if ver else UNVERIFIED_CONF
        return bool(ver), conf
    bad = bool(UNVERIFIED_RX.search(str(link.get('rel') or '')))
    return (not bad), (UNVERIFIED_CONF if bad else 1.0)


def _build_flow(view):
    import numpy as np
    from scipy import sparse

    from ontology.vocabulary import flow_relation_types
    flow = set(flow_relation_types())
    f = _Flow()
    nodes = view.by_id
    f.ids = sorted(nodes)
    f.idx = {k: i for i, k in enumerate(f.ids)}
    f.meta = {k: {'label': n.get('label') or k, 'country': n.get('country'), 'sector': n.get('sector'),
                  'ticker': n.get('mkt') or None} for k, n in nodes.items()}
    f.out, f.inn, f.rel_out, f.rel_in = {}, {}, {}, {}
    rows, cols, vals = [], [], []
    conf_sum, conf_n = {}, {}
    for lk in view.links:
        s, t = lk.get('source'), lk.get('target')
        if s not in f.idx or t not in f.idx or s == t:
            continue
        typ = lk.get('type') or 'supply'
        ver, conf = _trust(lk)
        try:
            w = float(lk.get('w') or 0)
        except (TypeError, ValueError):
            w = 0.0
        e = {'source': s, 'target': t, 'type': typ, 'w': lk.get('w'), 'rel': lk.get('rel'), 'conf': conf,
             'verified': ver}
        if typ in flow:
            f.out.setdefault(s, []).append(e)
            f.inn.setdefault(t, []).append(e)
            rows.append(f.idx[s])
            cols.append(f.idx[t])
            vals.append(max(w, 0.1) * conf)
            for k in (s, t):
                conf_sum[k] = conf_sum.get(k, 0.0) + conf
                conf_n[k] = conf_n.get(k, 0) + 1
        else:
            f.rel_out.setdefault(s, []).append(e)
            f.rel_in.setdefault(t, []).append(e)
    n = len(f.ids)
    A = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n)) if n else sparse.csr_matrix((0, 0))

    def rownorm(M):
        d = np.asarray(M.sum(axis=1)).ravel()
        d[d == 0] = 1.0
        return sparse.diags(1.0 / d) @ M
    f.fwd = rownorm(A).tocsr()          # paso hacia los CLIENTES (aguas abajo)
    f.rev = rownorm(A.T.tocsr()).tocsr()  # paso hacia los PROVEEDORES (aguas arriba)
    f.sym = rownorm((A + A.T).tocsr()).tocsr()
    imp = np.zeros(n)
    try:
        st = view.impact.stats if view.impact is not None else {}
        for k, s in st.items():
            i = f.idx.get(k)
            if i is not None:
                imp[i] = math.log1p(max(0.0, float(s.get('sum_impact') or 0.0)))
        mx = imp.max() if n else 0.0
        if mx > 0:
            imp = imp / mx
    except Exception:  # noqa: BLE001
        pass
    f.imp = imp
    unc = np.zeros(n)
    for k, cnt in conf_n.items():
        unc[f.idx[k]] = max(0.0, 1.0 - conf_sum[k] / cnt)
    f.unc = unc
    f.generation, f.graph_version = view.generation, view.graph_version
    f.source = view.source
    f.as_of = view.built_at
    f.lru, f.lru_lock = OrderedDict(), threading.Lock()
    return f


def flow(view=None):
    from core.hotviews import hot
    v = view if view is not None else hot.graph()
    if v is None:
        raise RuntimeError('grafo no disponible / graph unavailable')
    return hot.cached('context_engine.flow', _build_flow, view=v), v


def _orientation(intent_name, direction=None):
    if direction == 'up' or (direction is None and intent_name == 'upstream'):
        return 'rev'
    if direction == 'down' or (direction is None and intent_name in ('downstream', 'impact')):
        return 'fwd'
    return 'sym'


def ppr(f, seeds, orientation='sym'):
    """PageRank personalizado desde las semillas (vector numpy, máx = 1 fuera de las semillas). Caché LRU por
    generación (64 consultas)."""
    import numpy as np
    key = (tuple(sorted(seeds)), orientation)
    with f.lru_lock:
        hit = f.lru.get(key)
        if hit is not None:
            f.lru.move_to_end(key)
            return hit
    n = len(f.ids)
    e = np.zeros(n)
    idx = [f.idx[s] for s in seeds if s in f.idx]
    if not idx or n == 0:
        return np.zeros(n)
    e[idx] = 1.0 / len(idx)
    P = {'fwd': f.fwd, 'rev': f.rev}.get(orientation, f.sym)
    PT = P.T.tocsr()
    pi = e.copy()
    for _ in range(PPR_ITERS):
        nxt = (1 - BETA) * e + BETA * (PT @ pi)
        if np.abs(nxt - pi).sum() < 1e-9:
            pi = nxt
            break
        pi = nxt
    mask = np.ones(n, dtype=bool)
    mask[idx] = False
    mx = pi[mask].max() if mask.any() else 0.0
    out = pi / mx if mx > 0 else pi
    out[idx] = 1.0
    out = np.minimum(out, 1.0)
    with f.lru_lock:
        f.lru[key] = out
        while len(f.lru) > 64:
            f.lru.popitem(last=False)
    return out


def relevance(seeds, question=None, intent_name=None, direction=None, view=None):
    """→ (R: dict id→R en [0,1] solo para nodos con R>0, info). Semillas = ids canónicos."""
    import numpy as np
    f, v = flow(view)
    seeds = [s for s in dict.fromkeys(seeds or []) if s in f.idx]
    it = intent_name or intent(question)
    pi = ppr(f, seeds, _orientation(it, direction))
    if it == 'impact' and v.impact is not None and seeds:
        psi = np.zeros(len(f.ids))
        for s in seeds:
            vic = v.impact.victims.get(s)
            if not vic:
                continue
            for k, p in zip(vic[0], vic[1]):
                i = f.idx.get(k)
                if i is not None:
                    psi[i] = max(psi[i], float(p) / 100.0)
        pi = np.maximum(psi, IMPACT_MIX * pi)
        for s in seeds:
            pi[f.idx[s]] = 1.0
    R = pi * ((EPS + f.imp) / (1.0 + EPS)) * ((1.0 + LAMBDA_U * f.unc) / (1.0 + LAMBDA_U))   # normalizado a [0, 1]
    for s in seeds:
        R[f.idx[s]] = 1.0
    nz = np.nonzero(R > 1e-9)[0].tolist()
    return {f.ids[i]: float(R[i]) for i in nz}, {'intent': it, 'seeds': seeds, 'generation': f.generation,
                                                 'graph_version': f.graph_version, 'method': METHOD}


def edge_score(R, e):
    try:
        w = float(e.get('w') or 0)
    except (TypeError, ValueError):
        w = 0.0
    c = e.get('conf', e.get('confidence'))
    c = 1.0 if c is None else float(c)
    return math.sqrt(R.get(e['source'], 0.0) * R.get(e['target'], 0.0)) * min(1.0, max(w, 0.1) / W_REF) * c


# ════════════════════════════════════════════════════════════════════════════
# 4. empaquetado bajo presupuesto (cobertura ponderada, voraz perezoso)
# ════════════════════════════════════════════════════════════════════════════
def pack(items, budget, eligible=None, on_choose=None):
    """items: [{'key', 'R', 'cost', 'groups': [(clave, sim)]}] → (elegidos en orden de elección, descartados).

    F(S) = Σ_g R(g) · max_{f∈S} sim(f, g) con sim(f,f)=1 y sim(f,g)=s si comparten una clave de grupo (la mayor).
    Voraz perezoso por ΔF/costo + comparación con el mejor elemento solo (Khuller-Moss-Naor). `eligible(item,
    elegidos)` (opcional): un elemento que todavía no es elegible (p. ej. una arista de 2.º salto cuyo 1.er salto no
    entró) espera y se reconsidera cuando entra otro. Determinista (desempate por orden de entrada)."""
    n = len(items)
    if n == 0:
        return [], []
    members = {}
    for i, it in enumerate(items):
        for g, s in it.get('groups') or ():
            members.setdefault(g, []).append((i, s))
    nbr = []
    for i, it in enumerate(items):
        d = {i: 1.0}
        for g, s in it.get('groups') or ():
            for j, s2 in members[g]:
                if j != i:
                    d[j] = max(d.get(j, 0.0), min(s, s2))
        nbr.append(d)
    cover = [0.0] * n

    def gain(i):
        return sum(items[j]['R'] * max(0.0, s - cover[j]) for j, s in nbr[i].items())

    heap = [(-gain(i) / max(1.0, items[i]['cost']), i) for i in range(n)]
    heapq.heapify(heap)
    chosen, chosen_set, used, parked = [], set(), 0.0, []
    while heap:
        negr, i = heapq.heappop(heap)
        if i in chosen_set:
            continue
        cost = max(1.0, items[i]['cost'])
        if used + cost > budget:
            continue
        g = gain(i)
        r = g / cost
        if heap and r + 1e-15 < -heap[0][0]:
            heapq.heappush(heap, (-r, i))            # cota vieja: se re-evalúa más tarde
            continue
        if eligible is not None and not eligible(items[i], chosen_set):
            parked.append(i)
            continue
        chosen.append(i)
        chosen_set.add(i)
        used += cost
        if on_choose is not None:
            on_choose(items[i])
        for j, s in nbr[i].items():
            cover[j] = max(cover[j], s)
        if parked:
            for j in parked:
                heapq.heappush(heap, (-gain(j) / max(1.0, items[j]['cost']), j))
            parked = []
    # el mejor elemento solo (garantía de la mochila)
    best = max((i for i in range(n) if items[i]['cost'] <= budget
                and (eligible is None or eligible(items[i], chosen_set))),
               key=lambda i: (items[i]['R'], -i), default=None)
    total = sum(items[j]['R'] * cover[j] for j in range(n))
    if best is not None and best not in chosen_set:
        single = sum(items[j]['R'] * s for j, s in nbr[best].items())
        if single > total and best not in parked:
            chosen, chosen_set = [best], {best}
    return [items[i] for i in chosen], [items[i] for i in range(n) if i not in chosen_set]


# ════════════════════════════════════════════════════════════════════════════
# 5. subgrafo por relevancia + cola
# ════════════════════════════════════════════════════════════════════════════
def _jlen(x):
    return len(json.dumps(x, ensure_ascii=False, separators=(',', ':'), default=str))


def tail_summary(omitted, meta_of, lang='en'):
    """Estadísticos suficientes de lo que NO entró: conteo, % del peso, máximo, por salto, por tipo, países."""
    if not omitted:
        return None
    tot_w = sum(float(e.get('w') or 0) for e in omitted)
    by_hop, by_type, ctry = {}, {}, {}
    mx = None
    for e in omitted:
        h = str(e.get('hop') or 1)
        by_hop[h] = by_hop.get(h, 0) + 1
        by_type[e.get('type') or 'supply'] = by_type.get(e.get('type') or 'supply', 0) + 1
        far = e.get('_far') or e.get('target')
        c = (meta_of(far) or {}).get('country') or '?'
        ctry[c] = ctry.get(c, 0.0) + float(e.get('w') or 0)
        if mx is None or float(e.get('w') or 0) > float(mx.get('w') or 0):
            mx = e
    top_c = sorted(ctry.items(), key=lambda kv: (-kv[1], kv[0]))[:4]
    return {'omitted_edges': len(omitted), 'omitted_weight': round(tot_w, 2),
            'by_hop': dict(sorted(by_hop.items())), 'by_type': dict(sorted(by_type.items(), key=lambda kv: -kv[1])[:6]),
            'top_countries_by_weight': [{'country': c, 'weight': round(w, 2)} for c, w in top_c],
            'max_edge': {'source': mx.get('source'), 'target': mx.get('target'), 'w': mx.get('w'),
                         'type': mx.get('type')} if mx else None}


def _edge_row(e, R):
    row = {'source': e['source'], 'target': e['target'], 'type': e.get('type'), 'w': e.get('w'),
           'hop': e.get('hop', 1), 'direction': e.get('direction')}
    c = e.get('conf', e.get('confidence'))
    if c is not None and float(c) < 1.0:
        row['conf'] = round(float(c), 2)
    rel = e.get('rel') or e.get('relation')
    if rel:
        row['rel'] = str(rel)[:90]
    row['r'] = round(edge_score(R, e), 4)
    return row


def pack_edges(edges, seeds, question=None, budget_chars=DEFAULT_BUDGET_CHARS, direction=None, view=None,
               max_nodes=None):
    """Aristas candidatas (dicts con source/target/type/w/conf/hop/direction) → (filas elegidas ordenadas por R(e|Q),
    cola, R). Coherencia de caminos: una arista de salto h entra solo si su extremo cercano es semilla o ya está
    unido por una arista elegida. Grupos de similitud: mismo par (s,t) = 1 (no repetir la contraparte por cada tipo
    de relación) y misma contraparte lejana a 2+ saltos = 0,5."""
    R, info = relevance(seeds, question, direction=direction, view=view)
    seedset = set(info['seeds'])
    # un par (proveedor, cliente) = UNA fila: la de mayor peso; los otros tipos del mismo par van en `also`
    best, order = {}, []
    for e in edges:
        k = (e['source'], e['target'])
        cur = best.get(k)
        if cur is None:
            best[k] = dict(e)
            order.append(k)
        else:
            w_new, w_cur = float(e.get('w') or 0), float(cur.get('w') or 0)
            other_t = e.get('type') if w_new <= w_cur else cur.get('type')
            if w_new > w_cur:
                keep_also = cur.get('also') or []
                best[k] = dict(e)
                best[k]['also'] = keep_also
            if other_t and other_t != best[k].get('type'):
                best[k]['also'] = sorted(set((best[k].get('also') or []) + [other_t]))
    meta = None
    try:
        f, _v = flow(view)
        meta = f.meta
    except Exception:  # noqa: BLE001
        meta = {}
    items = []
    for k, pair in enumerate(order):
        e = best[pair]
        if e.get('direction') == 'up':
            near, far = e['target'], e['source']
        elif e.get('direction') == 'down':
            near, far = e['source'], e['target']
        else:
            near, far = (e['source'], e['target']) if e['source'] in seedset else (e['target'], e['source'])
        row = _edge_row(e, R)
        if e.get('also'):
            row['also'] = e['also']
        groups = [(('far', far), 0.5)] if (e.get('hop') or 1) > 1 else []
        m = meta.get(far) or {}
        node_cost = 60 + len(str(m.get('label') or far)) + len(str(m.get('country') or ''))   # su fila en `nodes`
        items.append({'key': k, 'R': row['r'] + 1e-9 * (len(order) - k), 'cost': _jlen(row) + 1 + node_cost,
                      'groups': groups, 'row': row, 'near': near, 'far': far, 'edge': e})

    joined = set(seedset)

    def eligible(it, _chosen):
        if (it['edge'].get('hop') or 1) > 1 and it['near'] not in seedset and it['near'] not in joined:
            return False                     # su primer salto todavía no entró
        if max_nodes is not None and it['far'] not in joined and len(joined) - len(seedset) >= max_nodes:
            return False
        return True

    def on_choose(it):
        joined.add(it['far'])
    budget = max(200, int(budget_chars))
    sides = {}
    for it in items:
        sides.setdefault(it['edge'].get('direction') if it['edge'].get('direction') in ('up', 'down') else 'x', []).append(it)
    # Reparto del presupuesto: los DOS lados de la cadena (proveedores y clientes, según la intención) y, dentro de
    # cada lado, 1.er salto primero y hasta 30 % para el 2.º/3.er salto si existen. Lo que una fase no usa pasa a la
    # siguiente. Sin esto, en "¿cómo es la cadena de TSMC?" casi todo eran clientes y a 2 saltos nada del 2.º nivel.
    share_up = {'upstream': 0.75, 'downstream': 0.25}.get(info['intent'], 0.5)
    if direction is None and 'up' in sides and 'down' in sides:
        order = [('up', share_up), ('down', 1 - share_up)] if share_up >= 0.5 else [('down', 1 - share_up), ('up', share_up)]
    else:
        order = [(k, 1.0 / len(sides)) for k in sorted(sides)]
    chosen, omitted, left = [], [], 0
    for k, share in order:
        lst = sides.get(k, []) + (sides.get('x', []) if k != 'x' and k == order[0][0] else [])
        b_side = int(budget * share) + left
        h1 = [it for it in lst if (it['edge'].get('hop') or 1) <= 1]
        h2 = [it for it in lst if (it['edge'].get('hop') or 1) > 1]
        c1, o1 = pack(h1, int(b_side * (0.7 if h2 else 1.0)), eligible=eligible, on_choose=on_choose)
        used = sum(it['cost'] for it in c1)
        c2, o2 = pack(h2, b_side - used, eligible=eligible, on_choose=on_choose) if h2 else ([], [])
        used += sum(it['cost'] for it in c2)
        left = max(0, b_side - used)
        chosen += c1 + c2
        omitted += o1 + o2
    chosen.sort(key=lambda it: (-it['row']['r'], it['key']))
    return chosen, omitted, R, info


def _meta_fn(f):
    return lambda k: f.meta.get(k)


def subgraph(seeds, question=None, depth=2, direction='both', budget_chars=DEFAULT_BUDGET_CHARS,
             include_partners=False, min_weight=0.0, min_conf=0.0, max_nodes=None, view=None):
    """Vecindario de FLUJO de las semillas hasta `depth` saltos, ordenado por R(v|Q)/R(e|Q) y recortado al
    presupuesto, con la cola resumida. Las semillas pueden ser texto (se resuelven aquí)."""
    f, v = flow(view)
    ids, unknown = [], []
    for s in seeds or []:
        cid = s if s in f.idx else canon(s)
        (ids if cid else unknown).append(cid or str(s)[:80])
    ids = list(dict.fromkeys(ids))
    depth = max(1, min(MAX_DEPTH, int(depth or 1)))
    dirs = ['up', 'down'] if direction in (None, 'both') else [direction]
    cand, seen_e = [], set()
    frontier = {d: list(ids) for d in dirs}
    reached = {d: set(ids) for d in dirs}
    seedset = set(ids)
    for hop in range(1, depth + 1):
        for d in dirs:
            nxt = []
            for nid in frontier[d]:
                lst = (f.inn.get(nid, []) if d == 'up' else f.out.get(nid, []))
                if include_partners:
                    lst = lst + (f.rel_in.get(nid, []) if d == 'up' else f.rel_out.get(nid, []))
                for e in lst:
                    if float(e.get('w') or 0) < min_weight or e['conf'] < min_conf:
                        continue
                    other = e['source'] if d == 'up' else e['target']
                    if hop > 1 and other in seedset:
                        continue                 # vuelta a la semilla: ya está como vínculo de 1 salto
                    k = (e['source'], e['target'], e['type'])
                    if k not in seen_e:
                        seen_e.add(k)
                        cand.append(dict(e, hop=hop, direction=d))
                    if other not in reached[d]:
                        reached[d].add(other)
                        nxt.append(other)
            frontier[d] = nxt
    chosen, omitted, R, info = pack_edges(cand, ids, question, budget_chars,
                                          direction=None if direction in (None, 'both') else direction,
                                          view=v, max_nodes=max_nodes)
    keep_nodes = list(ids)
    for it in chosen:
        for k in (it['row']['source'], it['row']['target']):
            if k not in keep_nodes:
                keep_nodes.append(k)
    hop_of = {k: 0 for k in ids}
    for it in chosen:
        hop_of.setdefault(it['far'], it['row']['hop'])
    nodes = []
    for k in keep_nodes:
        m = f.meta.get(k) or {}
        nodes.append({'id': k, 'label': m.get('label') or k, 'hop': hop_of.get(k, 1), 'r': round(R.get(k, 0.0), 4),
                      'country': m.get('country'), 'sector': m.get('sector'), 'symbol': m.get('ticker')})
    nodes.sort(key=lambda x: (x['hop'] > 0, -x['r'], x['id']))
    related = []
    if not include_partners:
        for k in ids:
            for e in (f.rel_in.get(k, []) + f.rel_out.get(k, [])):
                related.append({'source': e['source'], 'target': e['target'], 'type': e['type'], 'w': e['w']})
        related.sort(key=lambda e: (-(float(e.get('w') or 0)), e['source'], e['target']))
    tail = tail_summary([dict(it['edge'], _far=it['far']) for it in omitted], _meta_fn(f))
    tot_w = sum(float(e.get('w') or 0) for e in cand) or 1.0
    kept_w = sum(float(it['edge'].get('w') or 0) for it in chosen)
    return {'seeds': ids, 'unknown_seeds': unknown, 'question': (str(question)[:200] if question else None),
            'intent': info['intent'], 'depth': depth, 'direction': direction or 'both',
            'nodes': nodes, 'edges': [it['row'] for it in chosen],
            'related': related[:8], 'related_note': 'partner/invest: shown apart, they do NOT transmit damage by default',
            'counts': {'candidate_edges': len(cand), 'kept_edges': len(chosen), 'nodes': len(nodes),
                       'kept_weight_pct': round(100.0 * kept_w / tot_w, 1)},
            'tail': tail, 'truncated': bool(omitted), 'budget_chars': int(budget_chars),
            'method': METHOD, 'generation': f.generation, 'graph_version': f.graph_version,
            'as_of': f.as_of, 'convention': 'edge source SUPPLIES target'}


def pack_supply_chain(res, question=None, budget_chars=DEFAULT_BUDGET_CHARS):
    """Un resultado de get_supply_chain (MCP) → el MISMO resultado con `edges` ordenadas por R(e|Q) y recortadas al
    presupuesto (los 2 saltos según relevancia, no por posición), `nodes` solo los que aparecen, y `tail` con lo que
    quedó afuera. `counts` conserva los totales reales. Nunca lanza: ante un problema devuelve `res` tal cual."""
    try:
        root = res.get('root')
        edges = [e for e in (res.get('edges') or []) if isinstance(e, dict) and e.get('source') and e.get('target')]
        if not root or not edges:
            return res
        cand = [dict(e, conf=e.get('confidence', e.get('conf', 1.0))) for e in edges]
        d = res.get('direction')
        chosen, omitted, R, _info = pack_edges(cand, [root], question, budget_chars,
                                               direction=d if d in ('up', 'down') else None)
        out = {k: v for k, v in res.items() if k not in ('edges', 'nodes')}
        out['edges'] = [it['row'] for it in chosen]
        keep = {root} | {it['row']['source'] for it in chosen} | {it['row']['target'] for it in chosen}
        out['nodes'] = [{k: n.get(k) for k in ('id', 'label', 'symbol', 'hop', 'country', 'sector', 'listed')
                         if n.get(k) is not None}
                        for n in (res.get('nodes') or []) if isinstance(n, dict) and n.get('id') in keep]
        try:
            f, _v = flow()
            meta = _meta_fn(f)
        except Exception:  # noqa: BLE001
            meta = lambda k: None  # noqa: E731
        if omitted:
            out['tail'] = tail_summary([dict(it['edge'], _far=it['far']) for it in omitted], meta)
            out['truncated'] = True
        out['ranking'] = 'edges ordered by relevance R(e|Q) (context engine); tail = what was left out'
        return out
    except Exception as e:  # noqa: BLE001
        log.info('context_engine.pack_supply_chain: %s', type(e).__name__)
        return res


def rank_neighbors(nid, side, limit=8, question=None, view=None):
    """Vecinos de FLUJO de `nid` ('up' proveedores / 'down' clientes) ordenados por R(e|Q). → [arista]"""
    f, v = flow(view)
    lst = f.inn.get(nid, []) if side == 'up' else f.out.get(nid, [])
    if not lst:
        return []
    R, _ = relevance([nid], question, direction=side, view=v)
    return sorted(lst, key=lambda e: (-edge_score(R, e), -(float(e.get('w') or 0)), e['source'], e['target']))[:limit]


# ════════════════════════════════════════════════════════════════════════════
# 6. hechos [F#]
# ════════════════════════════════════════════════════════════════════════════
def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class FactBook:
    """Tabla de hechos de UNA respuesta: cada resultado que se le da a la IA lleva un id [F#] con su fuente y as_of.
    `public()` = lo que va en la respuesta del chat (`facts`) y en la ficha chat.answer (sin cuerpos)."""

    def __init__(self):
        self.facts = []
        self._by_key = {}

    def add(self, kind, entity=None, source=None, as_of=None, key=None):
        if key is not None and key in self._by_key:
            return self._by_key[key]
        fid = f'F{len(self.facts) + 1}'
        self.facts.append({'id': fid, 'kind': str(kind)[:40], 'entity': (str(entity)[:80] if entity else None),
                           'source': (str(source)[:160] if source else None),
                           'as_of': (str(as_of)[:40] if as_of else None)})
        if key is not None:
            self._by_key[key] = fid
        return fid

    def get(self, key):
        return self._by_key.get(key)

    def public(self):
        return [{k: v for k, v in f.items() if v is not None} for f in self.facts]


def result_source(res):
    """(fuente, as_of) declarados por un resultado de herramienta (primer nivel)."""
    if not isinstance(res, dict):
        return None, None
    src = res.get('source')
    if not src and isinstance(res.get('sources'), list) and res['sources']:
        s0 = res['sources'][0]
        src = s0.get('label') if isinstance(s0, dict) else s0
    if not src and isinstance(res.get('catalog'), dict):
        src = res['catalog'].get('source')
    as_of = res.get('as_of') or (res.get('catalog') or {}).get('as_of') if isinstance(res.get('catalog'), dict) \
        else res.get('as_of')
    return (str(src)[:160] if src else None), (str(as_of)[:40] if as_of else None)
