"""mcp_server/contract.py — EL contrato común de las respuestas MCP (ARQUITECTURA_V2 §15; BRECHAS L4-08).

Toda herramienta acepta dos parámetros comunes (se agregan solos al inputSchema de cada una):

  detail     'summary' | 'standard' (por defecto) | 'full'
               summary  = lo esencial, chico (get_company ≈ identidad + precio + NRS + 5 proveedores/clientes)
               standard = el resultado normal, acotado a max_chars (12.000 por defecto)
               full     = todo, hasta max_chars si se pide o hasta el tope del servidor (240.000)
  max_chars  tope de caracteres del JSON devuelto (1.000-200.000)

y toda respuesta trae, además de sus campos, `detail`, `as_of`, `known_at` (cuándo lo leyó Khipus), `sources`,
`method`, `truncated`, `tokens_estimate` y, si se recortó, `truncation` [{path, kept, total}] — el recorte es
ORDENADO (las listas ya vienen por relevancia/peso; se conserva la cabeza) y nunca a ciegas por posición del texto.
get_supply_chain además se ordena por relevancia R(e|Q) del motor de contexto con la cola resumida (`tail`).

La copia en texto que pide la especificación MCP (content[0].text) es el MISMO JSON compacto: el tamaño total
queda acotado a ~2 × max_chars en vez de 2 × 112k (get_supply_chain de Nvidia a 2 saltos).
"""
import copy
import json
import math
from datetime import datetime, timezone

DETAILS = ('summary', 'standard', 'full')
DEFAULT_DETAIL = 'standard'
DEFAULT_MAX_CHARS = 12_000
SUMMARY_MAX_CHARS = 4_000
HARD_MAX_CHARS = 200_000
MIN_MAX_CHARS = 1_000
_MAX_ROUNDS = 80

COMMON_PROPS = {
    'detail': {'type': 'string', 'enum': list(DETAILS), 'default': DEFAULT_DETAIL,
               'description': 'Response size: summary | standard | full.'},
    'max_chars': {'type': 'integer', 'minimum': MIN_MAX_CHARS, 'maximum': HARD_MAX_CHARS,
                  'default': DEFAULT_MAX_CHARS, 'description': 'Max JSON characters (ordered truncation).'},
}
COMMON_KEYS = tuple(COMMON_PROPS)


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _dump(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':'), default=str)


def _finite(v):
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: _finite(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_finite(x) for x in v]
    return v


# ── resúmenes por herramienta (detail='summary') ────────────────────────────
def _nb(x):
    if not isinstance(x, dict):
        return x
    return {k: x.get(k) for k in ('id', 'label', 'weight', 'type', 'confidence') if x.get(k) is not None
            and not (k == 'confidence' and x.get(k) == 1.0)}


def _sum_company(r):
    lm = r.get('live_market') or {}
    nrs = r.get('network_risk_score') or {}
    out = {k: r.get(k) for k in ('id', 'label', 'symbol', 'listed', 'sector', 'country') if r.get(k) is not None}
    if lm.get('available'):
        out['live_market'] = {k: lm.get(k) for k in ('price', 'currency', 'change_pct', 'market_cap_usd_b',
                                                       'source', 'as_of') if lm.get(k) is not None}
    pv = r.get('private_valuation') or {}
    if pv:
        out['private_valuation'] = {k: pv.get(k) for k in ('valuation_usd_b', 'as_of', 'round', 'source_url')
                                    if pv.get(k) is not None}
    if nrs:
        out['network_risk_score'] = {k: nrs.get(k) for k in ('value', 'level') if nrs.get(k) is not None}
    out['top_suppliers'] = [_nb(x) for x in (r.get('top_suppliers') or [])[:5]]
    out['top_customers'] = [_nb(x) for x in (r.get('top_customers') or [])[:5]]
    if r.get('counts'):
        out['counts'] = r['counts']
    st = r.get('structure') or {}
    if st:
        out['structure'] = {k: st.get(k) for k in ('supplier_concentration', 'downstream_cap_at_risk_usd_b',
                                                   'systemic_rank') if st.get(k) is not None}
    for k in ('as_of', 'sources'):
        if r.get(k):
            out[k] = r[k]
    return out


def _supply_chain(r, budget, question=None):
    try:
        from core.context_engine import pack_supply_chain
        out = pack_supply_chain(r, question=question, budget_chars=int(budget * (0.6 if budget <= SUMMARY_MAX_CHARS
                                                                                     else 1.0)))
    except Exception:  # noqa: BLE001
        return r
    if budget <= SUMMARY_MAX_CHARS:
        out.pop('edge_semantics', None)
        out['related'] = [{k: e.get(k) for k in ('source', 'target', 'type', 'w')}
                          for e in (out.get('related') or [])[:5] if isinstance(e, dict)]
        out['nodes'] = [{k: n.get(k) for k in ('id', 'label', 'hop', 'country') if n.get(k) is not None}
                        for n in (out.get('nodes') or []) if isinstance(n, dict)]
    else:
        rel = out.get('related') or []
        if len(rel) > 12:                       # socios/inversores: lo menos importante, acotado y contado
            out['related'] = rel[:12]
            out['related_omitted'] = len(rel) - 12
        for e in out.get('related') or []:
            if isinstance(e, dict) and isinstance(e.get('rel'), str) and len(e['rel']) > 90:
                e['rel'] = e['rel'][:90] + '…'
    return out


SUMMARIZERS = {'get_company': _sum_company}
# listas ordenadas de VIEJO a NUEVO: al recortar se conserva la COLA (lo más reciente), nunca la cabeza
# (revisión: get_history devolvía los precios de hace años junto a un as_of de hoy)
KEEP_TAIL = {'get_history': ('points',)}
# herramientas que se recortan por RELEVANCIA (no por posición) en standard/summary
RELEVANCE_PACKERS = {'get_supply_chain': _supply_chain}


# ── recorte ordenado genérico ───────────────────────────────────────────────
def _largest_list(x, path='', min_len=2, skip=()):
    """(tamaño serializado, ruta, contenedor, clave) de la lista más pesada con ≥ min_len elementos (sin entrar en
    las claves de primer nivel de `skip`)."""
    best = None
    if isinstance(x, dict):
        items = x.items()
    elif isinstance(x, list):
        items = enumerate(x)
    else:
        return None
    for k, v in items:
        if not path and k in skip:
            continue
        p = f'{path}.{k}' if path else str(k)
        if isinstance(v, list) and len(v) >= min_len:
            sz = len(_dump(v))
            if best is None or sz > best[0]:
                best = (sz, p, x, k)
        if isinstance(v, (dict, list)):
            sub = _largest_list(v, p, min_len)
            if sub and (best is None or sub[0] > best[0]):
                best = sub
    return best


def _longest_str(x, path='', min_len=160):
    best = None
    items = x.items() if isinstance(x, dict) else enumerate(x) if isinstance(x, list) else ()
    for k, v in items:
        p = f'{path}.{k}' if path else str(k)
        if isinstance(v, str) and len(v) > min_len:
            if best is None or len(v) > best[0]:
                best = (len(v), p, x, k)
        elif isinstance(v, (dict, list)):
            sub = _longest_str(v, p, min_len)
            if sub and (best is None or sub[0] > best[0]):
                best = sub
    return best


# claves que se pueden SACAR enteras cuando recortar listas y textos no alcanza (de menos a más importante);
# nunca la identidad (id/label/symbol), el precio, el NRS, las fuentes ni los campos del contrato
DROP_ORDER = ('catalog', 'edge_semantics', 'explain', 'tail', 'ranking', 'convention', 'related', 'geo_live',
              'structure', 'nodes', 'counts', 'resolved_from', 'sector_label', 'category', 'preipo')
PROTECTED = frozenset(('id', 'label', 'symbol', 'root', 'as_of', 'sources', 'source', 'method', 'detail', 'known_at',
                       'live_market', 'network_risk_score', 'truncated', 'truncation', 'max_chars', 'tokens_estimate',
                       'over_budget', 'error', 'code'))


def _size(out, trunc):
    return len(_dump(out)) + (len(_dump(list(trunc.values()))) + 16 if trunc else 0)


def _cut_list(trunc, ll, tail_paths, floor):
    _sz, p, cont, k = ll
    lst = cont[k]
    total = trunc.get(p, {}).get('total', len(lst))
    keep = max(floor, (len(lst) * 3) // 4 if len(lst) > 4 else len(lst) // 2)   # pasos de 25 %: cerca del tope
    if p in tail_paths:
        cont[k] = lst[-keep:] if keep else []
        trunc[p] = {'path': p, 'kept': keep, 'total': total, 'kept_end': 'newest'}
    else:
        cont[k] = lst[:keep]
        trunc[p] = {'path': p, 'kept': keep, 'total': total}


def fit(payload, max_chars, tail_paths=()):
    """Recorta `payload` (copia) hasta que su JSON compacto (más la lista `truncation`) entre en max_chars:
      1. la lista más pesada se corta un 25 % CONSERVANDO LA CABEZA (las herramientas ya ordenan por
         relevancia/peso) — o la COLA si su ruta está en `tail_paths` (series de viejo a nuevo) —, luego los textos
         largos (> 160);
      2. si no alcanza (muchos campos chicos — revisión: get_company devolvía 4.400 con max_chars 1.000), se SACAN
         claves enteras de poco valor en el orden de DROP_ORDER ('kept': 'dropped');
      3. y por último listas hasta vacías y textos > 40.
    Lo que aun así no entre lo marca `apply` con over_budget. → (payload, truncation[])."""
    out = copy.deepcopy(payload)
    trunc = {}
    for _ in range(_MAX_ROUNDS):
        if _size(out, trunc) <= max_chars:
            break
        ll = _largest_list(out)
        if ll is not None and ll[0] > 400:
            _cut_list(trunc, ll, tail_paths, 1)
            continue
        ls = _longest_str(out)
        if ls is not None:
            _n, p, cont, k = ls
            cont[k] = cont[k][:max(80, len(cont[k]) // 2)] + '…'
            trunc.setdefault(p, {'path': p, 'kept': 'clipped', 'total': None})
            continue
        break
    if isinstance(out, dict):
        for k in DROP_ORDER:
            if _size(out, trunc) <= max_chars:
                break
            if k in out and k not in PROTECTED:
                out.pop(k)
                for tp in [tp for tp in trunc if tp == k or tp.startswith(k + '.')]:
                    trunc.pop(tp)               # lo recortado dentro de una clave que ya no está
                d = trunc.setdefault('(dropped)', {'path': '(dropped)', 'kept': 'dropped', 'keys': []})
                d['keys'].append(k)
    for _ in range(_MAX_ROUNDS):
        if _size(out, trunc) <= max_chars:
            break
        ll = _largest_list(out, min_len=1, skip=PROTECTED)
        if ll is not None and ll[0] > 2:
            _cut_list(trunc, ll, tail_paths, 0)
            continue
        ls = _longest_str(out, min_len=40)
        if ls is not None:
            _n, p, cont, k = ls
            cont[k] = cont[k][:max(32, len(cont[k]) // 2)] + '…'
            trunc.setdefault(p, {'path': p, 'kept': 'clipped', 'total': None})
            continue
        break
    return out, list(trunc.values())


def _norm_detail(d):
    d = str(d or DEFAULT_DETAIL).strip().lower()
    return d if d in DETAILS else DEFAULT_DETAIL


def apply(name, res, detail=None, max_chars=None, question=None):
    """Resultado crudo de una herramienta → resultado con el contrato (nunca lanza; ante un fallo, el crudo)."""
    if not isinstance(res, dict):
        res = {'result': res}
    detail = _norm_detail(detail)
    asked = max_chars is not None
    try:
        mc = int(max_chars) if asked else None
    except (TypeError, ValueError):
        mc, asked = None, False
    if mc is None:
        mc = {'summary': SUMMARY_MAX_CHARS, 'standard': DEFAULT_MAX_CHARS, 'full': HARD_MAX_CHARS}[detail]
    mc = max(MIN_MAX_CHARS, min(HARD_MAX_CHARS, mc))
    try:
        out = _finite(res)
        if detail == 'summary' and name in SUMMARIZERS:
            out = SUMMARIZERS[name](out)
        elif detail != 'full' and name in RELEVANCE_PACKERS:
            out = RELEVANCE_PACKERS[name](out, int(mc * 0.55), question)   # el resto: cola, socios, contrato
        was_truncated = bool(out.get('truncated')) if isinstance(out.get('truncated'), bool) else False
        env = {'detail': detail, 'as_of': out.get('as_of') or _now_iso(), 'known_at': _now_iso(),
               'sources': out.get('sources') if isinstance(out.get('sources'), list) else
               ([out['source']] if out.get('source') else []),
               'method': out.get('method') or f'khipus:{name}'}
        out = {**out, **{k: v for k, v in env.items() if k not in out or k in ('detail', 'known_at')}}
        out.setdefault('sources', env['sources'])
        body, trunc = fit(out, mc - 160, KEEP_TAIL.get(name, ()))   # margen para los campos del contrato
        if trunc:
            body['truncation'] = trunc
        body['truncated'] = bool(trunc) or was_truncated
        body['max_chars'] = mc
        body['tokens_estimate'] = 0
        if len(_dump(body)) > mc:          # ni sacando claves entra (lo esencial ya pesa más): se DICE, nunca falso
            body['over_budget'] = True
            body['truncated'] = True
        body['tokens_estimate'] = math.ceil(len(_dump(body)) / 4)
        return body
    except Exception:  # noqa: BLE001
        return res


def split_common(args):
    """Saca detail/max_chars de los argumentos (para el handler) → (args_sin_comunes, detail, max_chars)."""
    args = dict(args or {})
    detail = args.pop('detail', None)
    mc = args.pop('max_chars', None)
    return args, detail, mc
