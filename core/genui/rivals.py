"""core/genui/rivals.py — «ganadores» de un choque = RIVALES POCO GOLPEADOS (porte EXACTO de KhipuHot.rivals,
engine/hotclient.js; tests/test_genui_rivals.py corre las dos versiones sobre las mismas entradas y exige el mismo
resultado).

Regla (sin inventar nada, solo filtra cifras del kernel): un rubro (`cat`) con al menos una empresa golpeada ≥ 40 %
tiene «demanda huérfana»; sus empresas que NO son semilla del choque y quedaron golpeadas < 15 % son los rivales que
podrían captarla. Se muestran con su % de DAÑO (nunca un % de ganancia). Orden: cuántas caídas hay en su rubro, su
capitalización (la misma que ve el navegador: la EN VIVO, 0 si no hay) y el id.
"""
import math
import re

DAMAGED_MIN = 40.0
RIVAL_MAX = 15.0
_JS_NUM = re.compile(r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$')


def js_number(v):
    """`Number(v) || 0` de JavaScript (texto numérico → número; 'div. IBM', None, NaN → 0)."""
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return 0.0 if math.isnan(float(v)) else float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return 0.0
        if s in ('Infinity', '+Infinity', '-Infinity'):
            return float(s.replace('Infinity', 'inf'))
        if _JS_NUM.match(s):
            return float(s)
        if s.lower().startswith(('0x',)):
            try:
                return float(int(s, 16))
            except ValueError:
                return 0.0
    return 0.0


def js_round1(x):
    """Math.round(x * 10) / 10 (redondeo hacia +∞ en .5, como JavaScript)."""
    return math.floor(x * 10 + 0.5) / 10


def rivals(seed_ids, impacts, nodes, cap_of=None, max_n=4):
    """seed_ids: ids del choque · impacts: {id: % de daño} · nodes: [{id, cat}] (todas las empresas) ·
    cap_of: {id: capitalización} → [{id, hit, cat_damaged, cap}] (≤ max_n)."""
    cap_of = cap_of or {}
    get = (lambda i: impacts.get(i) or 0)
    seeds = set(seed_ids or ())
    by_id = {}
    for n in nodes or ():
        if isinstance(n, dict) and n.get('id') and n['id'] not in by_id:
            by_id[n['id']] = n
    damaged = {}
    for i in list(impacts or {}):
        if get(i) < DAMAGED_MIN:
            continue
        n = by_id.get(i)
        if not n or not n.get('cat'):
            continue
        damaged[n['cat']] = damaged.get(n['cat'], 0) + 1
    out = []
    for n in nodes or ():
        if not isinstance(n, dict) or not n.get('id') or n['id'] in seeds:
            continue
        dmg = damaged.get(n.get('cat'))
        if not dmg:
            continue
        hit = get(n['id'])
        if hit >= RIVAL_MAX:
            continue
        out.append({'id': n['id'], 'hit': js_round1(hit), 'cat_damaged': dmg, 'cap': js_number(cap_of.get(n['id']))})
    out.sort(key=lambda r: (-r['cat_damaged'], -r['cap'], _js_key(r['id'])))
    return out[:max_n or 4]


def _js_key(s):
    """Orden de cadenas de JavaScript (< compara unidades UTF-16)."""
    return s.encode('utf-16-be')
