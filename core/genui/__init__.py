"""core/genui — INTERFAZ GENERATIVA del chat (docs/CHAT_UI_GENERATIVA.md, contrato kblocks/1). Fase F1: el servidor
construye el sobre `ui` a partir de los resultados de herramientas que la respuesta YA usó; nada de IA, nada de E/S
extra, ninguna cifra sin dueño.

    mode()                          'off' | 'shadow' | 'on'  (variable GENUI; por defecto off)
    wants(context)                  ¿esta petición pidió bloques? (context.genui = 1, la bandera del navegador)
    build_ui(message, calls, entities, plan=None, lang='es', ctx=None) → (sobre, texto)
    rebuild(inputs)                 el MISMO cálculo desde las entradas guardadas en el libro (replay)
    stats()                         métricas para el 🩺 (ms, KB, descartes, cifras sin procedencia)

Con GENUI=off no se construye nada (costo 0). `shadow` construye, mide y guarda en el libro (blob `ui_blocks` +
`ui_sha` en la decisión chat.answer) SIN enviarlo. `on` lo envía solo a quien lo pide (context.genui = 1); los
clientes viejos reciben exactamente lo de siempre. Implementación retenida: genui.build@1 (core/impls.py).

Capas del guardián de cifras (§5.5): 1) esquema (core/genui/validate.py) — una cifra sin src/as_of no valida;
2) procedencia (core/genui/provenance.py) — cada número del bloque existe en el resultado citado; 3) la prosa sigue
por core/numbers.py como siempre; 4) el Plan de la IA (F5) no admite números.
"""
import json
import logging
import os
import threading
import time
from collections import Counter, deque

from core.genui import alt as _alt
from core.genui import builders as _b
from core.genui import layout as _layout
from core.genui import provenance as _prov
from core.genui import validate as _val
from core.genui.util import entity as _entity
from core.genui.util import now_iso

log = logging.getLogger('khipu')

IMPL = 'genui.build@1'
VERSION = 'kblocks/1'
MAX_BLOCKS = 14
MAX_BYTES = 48 * 1024
REPLAY_MAX_BYTES = 400 * 1024
# herramientas / vistas que un bloque puede citar en `prov.name` (§4.3)
GENUI_SOURCES = frozenset(_b.BUILDERS) | {'hot.impact', 'hot.card', 'hot.geo', 'hot.quote'}


def mode():
    v = (os.getenv('GENUI') or 'off').strip().lower()
    return v if v in ('off', 'shadow', 'on') else 'off'


def wants(context):
    """La bandera del navegador (kh_genui → context.genui = 1)."""
    return bool(isinstance(context, dict) and context.get('genui'))


def enabled(context):
    """¿Se ENVÍA el sobre en esta respuesta? Solo con GENUI=on y si el cliente lo pidió."""
    return mode() == 'on' and wants(context)


# ── métricas (memoria del proceso; 1 worker) ─────────────────────────────────────────────────────────────────────
_LOCK = threading.Lock()
_STATS = {'built': 0, 'sent': 0, 'errors': 0, 'figures_checked': 0, 'unprovenanced_blocks': 0,
          'ms': deque(maxlen=500), 'bytes': deque(maxlen=500), 'dropped': Counter(), 'types': Counter(),
          'last_at': None, 'last_error': None, 'recent': deque(maxlen=500),
          # F3: parciales por respuesta (core/khipu_chat._ProgUI.report) — armados, ms en total, retenciones
          'prog_answers': 0, 'prog_builds': 0, 'prog_held': 0, 'prog_ms': deque(maxlen=500)}
# el 🩺 juzga una VENTANA (no todo lo acumulado desde el arranque): un error de hace dos días ya no lo pone en rojo,
# y el p95 solo cuenta con suficientes muestras (un único armado lento en frío no lo dispara)
WINDOW_S = 24 * 3600
P95_MIN_SAMPLES = 20


def _recent(kind):
    cut = time.monotonic() - WINDOW_S
    return sum(1 for t, k in _STATS['recent'] if k == kind and t >= cut)


def _pct(xs, q):
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def stats():
    with _LOCK:
        ms, by = list(_STATS['ms']), list(_STATS['bytes'])
        return {'mode': mode(), 'impl': IMPL, 'version': VERSION, 'built': _STATS['built'], 'sent': _STATS['sent'],
                'errors': _STATS['errors'], 'ms_p50': _pct(ms, 0.5), 'ms_p95': _pct(ms, 0.95),
                'kb_p95': round(_pct(by, 0.95) / 1024, 1) if by else None,
                'figures_checked': _STATS['figures_checked'],
                'unprovenanced_blocks': _STATS['unprovenanced_blocks'],
                'dropped': dict(_STATS['dropped']), 'types': dict(_STATS['types']),
                'last_at': _STATS['last_at'], 'last_error': _STATS['last_error'],
                'errors_24h': _recent('error'), 'unprovenanced_24h': _recent('unprov'), 'samples': len(ms),
                'window_h': WINDOW_S // 3600, 'p95_min_samples': P95_MIN_SAMPLES,
                'progressive': {'answers': _STATS['prog_answers'], 'builds': _STATS['prog_builds'],
                                'held': _STATS['prog_held'], 'ms_p50': _pct(list(_STATS['prog_ms']), 0.5),
                                'ms_p95': _pct(list(_STATS['prog_ms']), 0.95)}}


def healthy(st=None):
    """¿La tarjeta del 🩺 va en verde? Sin errores ni cifras sin fuente en la ventana, y p95 ≤ 25 ms (si hay muestras)."""
    st = st or stats()
    p95 = st.get('ms_p95')
    slow = p95 is not None and st.get('samples', 0) >= P95_MIN_SAMPLES and p95 > 25
    return not st.get('errors_24h') and not st.get('unprovenanced_24h') and not slow


def note_sent():
    with _LOCK:
        _STATS['sent'] += 1


def note_progressive(builds, ms, held=0):
    """F3: lo que costaron los parciales de UNA respuesta (armados, ms sumados, publicaciones retenidas)."""
    if not builds:
        return
    with _LOCK:
        _STATS['prog_answers'] += 1
        _STATS['prog_builds'] += int(builds)
        _STATS['prog_held'] += int(held or 0)
        _STATS['prog_ms'].append(round(float(ms), 2))


def _record(ms, size, env, dropped, checked, unprov, error=None):
    with _LOCK:
        if error:
            _STATS['recent'].append((time.monotonic(), 'error'))
            _STATS['errors'] += 1
            _STATS['last_error'] = str(error)[:160]
            return
        _STATS['built'] += 1
        _STATS['ms'].append(ms)
        _STATS['bytes'].append(size)
        _STATS['figures_checked'] += checked
        _STATS['unprovenanced_blocks'] += unprov
        if unprov:
            _STATS['recent'].append((time.monotonic(), 'unprov'))
        for d in dropped:
            _STATS['dropped'][d.get('reason', 'invalid')] += 1
        for b in (env or {}).get('blocks') or []:
            _STATS['types'][b.get('type')] += 1
        _STATS['last_at'] = now_iso()


def reset_stats():
    with _LOCK:
        _STATS.update(built=0, sent=0, errors=0, figures_checked=0, unprovenanced_blocks=0, last_at=None,
                      last_error=None, prog_answers=0, prog_builds=0, prog_held=0)
        _STATS['prog_ms'].clear()
        _STATS['ms'].clear()
        _STATS['recent'].clear()
        _STATS['bytes'].clear()
        _STATS['dropped'].clear()
        _STATS['types'].clear()


# ── metadatos que los constructores no pueden leer solos (se guardan con las entradas: replay) ───────────────────
def gather_meta(calls):
    """Rótulos de las empresas que un resultado cita solo por id (get_history): lectura en memoria de la vista del
    grafo, nunca red. Se guardan con las entradas (replay)."""
    meta = {'labels': {}}
    want = {r['id'] for (n, _a, ok, r) in calls or [] if ok and n == 'get_history' and isinstance(r, dict)
            and isinstance(r.get('id'), str)}
    if not want:
        return meta
    try:
        from core.hotviews import hot
        # SIN esperar: si la vista aún no tiene generación (arranque en frío) el rótulo cae al id; nunca se bloquea el
        # hilo de la petición dentro del armado (presupuesto §8: sin E/S extra)
        by_id = getattr(hot.graph(wait=False), 'by_id', None) or {}
    except Exception:  # noqa: BLE001
        by_id = {}
    for i in sorted(want):
        n = by_id.get(i) or {}
        if n.get('label'):
            meta['labels'][i] = n['label']
    return meta


# ── el armado ────────────────────────────────────────────────────────────────────────────────────────────────────
def _strip(blk):
    blk = dict(blk)
    blk.pop('_meta', None)
    return blk


def _check(blk, calls):
    """(ok, motivo, cifras revisadas). Procedencia contra el/los resultado(s) citado(s) + esquema del bloque."""
    m = blk.get('_meta') or {}
    idx = [i for i in m.get('calls') or [] if 0 <= i < len(calls)]
    if not idx or any(not calls[i][2] for i in idx):
        return False, 'bad_ref', 0
    if (blk.get('prov') or {}).get('name') not in GENUI_SOURCES:
        return False, 'bad_ref', 0
    clean = _strip(blk)
    if blk['type'] != 'callout' or (blk.get('data') or {}).get('variant') != 'disclaimer':
        clean['alt'] = _alt.alt_of(clean) or clean.get('alt')
    figs = _prov.figures_of(clean)
    bad = _prov.assert_from(clean, [calls[i][3] for i in idx], m.get('transforms') or (), m.get('bases'))
    if bad:
        log.warning('genui: bloque %s (%s) descartado: %d cifra(s) sin procedencia, p. ej. %s', blk['type'],
                    m.get('tool'), len(bad), bad[0])
        return False, 'no_provenance', len(figs)
    errs = _val.errors(clean, 'Block')
    if errs:
        log.warning('genui: bloque %s (%s) no cumple el esquema: %s', blk['type'], m.get('tool'), errs[0])
        return False, 'invalid', len(figs)
    blk['alt'] = clean['alt']
    return True, None, len(figs)


def _candidates(calls, lang, fact_of, args_of, meta):
    """Todos los bloques posibles de esta respuesta (en orden de llamada), con sus metadatos internos."""
    out = []
    hist, comps = [], []
    for i, (name, _args, ok, res) in enumerate(calls or []):
        if not ok or not isinstance(res, dict):
            continue
        fn = _b.BUILDERS.get(name)
        if fn is None:
            continue
        fact = fact_of[i] if fact_of and i < len(fact_of) else None
        args = args_of[i] if args_of and i < len(args_of) else ''
        b = _b.Ctx(lang, i, fact, args, meta=meta)
        if name == 'get_history':
            hist.append((res, b))
        if name == 'get_company':
            comps.append((res, b))
        try:
            out.extend(fn(res, b))
        except Exception as e:  # noqa: BLE001 — un constructor nunca rompe la respuesta
            log.warning('genui: constructor %s falló (%s)', name, type(e).__name__, exc_info=True)
    if len(hist) >= 2:
        try:
            out.extend(_b.history_compare(hist, hist[0][1]))
        except Exception as e:  # noqa: BLE001
            log.warning('genui: comparación de series falló (%s)', type(e).__name__)
    if len(comps) >= 2:
        try:
            out.extend(_b.company_comparison(comps, comps[0][1]))
        except Exception as e:  # noqa: BLE001
            log.warning('genui: comparación de empresas falló (%s)', type(e).__name__)
    # la ficha lleva la serie de precio si en la misma respuesta hubo get_history de esa empresa
    spark = {}
    for res, b in hist:
        s, _ = _b.history_series(res, b)
        if s and res.get('id'):
            spark.setdefault(res['id'], (s, b.call))
    for blk in out:
        if blk['type'] == 'company.card':
            cid = (blk.get('data') or {}).get('company', {}).get('id')
            if cid in spark:
                s, ci = spark[cid]
                blk['data']['spark'] = {k: s[k] for k in ('name', 'values', 'points', 'entity', 'adjusted') if k in s}
                blk['data']['spark']['points'] = _lttb_small(s['points'])
                blk['_meta']['calls'] = list(blk['_meta']['calls']) + [ci]
    return out


def _lttb_small(points, n=60):
    from core.genui.util import lttb
    return lttb(points, n)


def build_core(inputs):
    """El cálculo PURO (sin E/S, sin reloj): lo que se guarda en el libro alcanza para repetirlo idéntico."""
    t0 = time.perf_counter()
    calls = [tuple(c) for c in inputs.get('calls') or []]
    lang = 'en' if inputs.get('lang') == 'en' else 'es'
    mode_ = inputs.get('mode') or 'simple'
    meta = inputs.get('meta') or {}
    ents = [e for e in (_entity(x.get('id'), x.get('label')) for x in inputs.get('entities') or []
                        if isinstance(x, dict)) if e]
    primary = ents[0]['id'] if ents else None
    cands = _candidates(calls, lang, inputs.get('fact_of'), inputs.get('args_of'), meta)
    dropped, checked, unprov = [], 0, 0
    good = []
    for i, blk in enumerate(cands):
        ok, why, n = _check(blk, calls)
        checked += n
        if ok:
            good.append(blk)
        else:
            if why == 'no_provenance':
                unprov += 1
            dropped.append({'index': i, 'type': blk['type'], 'reason': 'invalid' if why == 'no_provenance' else why})
    mains, secs, over = _layout.select(good, inputs.get('intent'), primary, mode_)
    for blk in over:
        dropped.append({'index': cands.index(blk), 'type': blk['type'], 'reason': 'over_budget'})
    texts = _layout.text_blocks(inputs.get('answer') or '', lang, ents)
    head, tail = texts[:1], texts[1:]
    if head and len(_layout.paragraphs(head[0]['data']['md'])) > 1:
        # el titular es SOLO el primer párrafo; el resto del primer trozo va después del bloque principal
        paras = _layout.paragraphs(head[0]['data']['md'])
        head = _layout.text_blocks(paras[0], lang, ents, start=1)
        tail = _layout.text_blocks('\n\n'.join(paras[1:] + [t['data']['md'] for t in tail]), lang, ents, start=2)
    visual = mains + secs
    seq = 0
    for blk in visual:
        seq += 1
        blk['id'] = f'b{seq}'
    blocks = head + mains + tail + secs
    if any((b.get('_meta') or {}).get('disclaimer') for b in visual):
        blocks.append(_layout.disclaimer_block())
    act = _layout.actions_block(inputs.get('actions'), next((e for e in ents if e['id'] == primary), None))
    if act:
        blocks.append(act)
    src = _layout.sources_block(inputs.get('facts'), inputs.get('sources'))
    if src:
        blocks.append(src)
    blocks = [_strip(b) for b in blocks]
    # presupuesto de bloques (los textos se funden si hiciera falta) y de bytes (§5.8)
    while len(blocks) > MAX_BLOCKS:
        k = next((i for i in range(len(blocks) - 1, -1, -1) if blocks[i]['type'] not in ('sources', 'actions')), None)
        if k is None:
            break
        dropped.append({'index': k, 'type': blocks[k]['type'], 'reason': 'over_budget'})
        blocks.pop(k)
    env = {'v': VERSION, 'lang': lang, 'state': 'final', 'layout': 'auto', 'as_of': inputs.get('now') or now_iso(),
           'impl': IMPL, 'blocks': blocks}
    sp = _alt.spoken_of(blocks)
    if sp:
        env['spoken'] = sp
    if dropped:
        env['dropped'] = dropped[:20]
    _fit(env)
    errs = _val.errors(env, 'Envelope')
    if errs:
        log.warning('genui: sobre inválido (%s); se manda solo el texto', errs[0])
        env['blocks'] = [b for b in env['blocks'] if b['type'] in ('text', 'sources')]
        env.pop('spoken', None)
        env['dropped'] = (env.get('dropped') or [])[:19] + [{'reason': 'invalid'}]
        if _val.errors(env, 'Envelope'):
            env = None
    ms = (time.perf_counter() - t0) * 1000
    return env, {'ms': ms, 'dropped': (env or {}).get('dropped') or dropped, 'checked': checked, 'unprov': unprov}


def _size(env):
    return len(json.dumps(env, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))


def _fit(env):
    """≤ 48 KB: primero se adelgazan las series (LTTB, puntos que existen), después salen los secundarios."""
    from core.genui.util import lttb
    if _size(env) <= MAX_BYTES:
        return
    for n in (200, 120, 60):
        for b in env['blocks']:
            if b['type'] == 'chart.line':
                for s in b['data']['series']:
                    s['points'] = lttb(s['points'], n)
        if _size(env) <= MAX_BYTES:
            return
    vis = [i for i, b in enumerate(env['blocks']) if b['type'] not in ('text', 'actions', 'sources', 'callout')]
    while _size(env) > MAX_BYTES and vis:
        k = vis.pop()
        b = env['blocks'].pop(k)
        env.setdefault('dropped', []).append({'index': k, 'type': b['type'], 'reason': 'over_budget'})
        env['dropped'] = env['dropped'][:20]
        vis = [i for i, bb in enumerate(env['blocks']) if bb['type'] not in ('text', 'actions', 'sources', 'callout')]


# herramientas con constructor cuyos argumentos son SOLO ids, tickers o enumerados (van al «¿De dónde sale?» y al blob
# ui_inputs). Las que admiten texto libre (run_scenario.scenario, y toda herramienta sin constructor: web_search,
# search_companies…) NO: el modelo suele copiar ahí la pregunta del usuario, que el libro solo guarda como HMAC
_ARGS_SAFE = ('get_company', 'get_supply_chain', 'rank_companies', 'market_movers', 'get_world_events', 'get_news',
              'get_committee_memo', 'get_conclusions_board', 'get_research', 'get_risk_report', 'get_history')
_SOURCE_KEYS = ('label', 'url', 'as_of', 'tool', 'published')


def _clean_sources(sources):
    """Solo lo que pinta el bloque `sources` (enlaces públicos de los RESULTADOS de herramientas, con su as_of), nada
    más; mismo filtro que layout.sources_block. Van al blob de 90 días como el texto de la respuesta (D3)."""
    out = []
    for x in sources or []:
        if not isinstance(x, dict):
            continue
        u = x.get('url')
        if not (isinstance(u, str) and u.startswith(('http://', 'https://')) and len(u) <= 500):
            continue
        out.append({k: x[k] for k in _SOURCE_KEYS if x.get(k) is not None})
        if len(out) >= 12:
            break
    return out


def inputs_for(message, calls, entities, lang, ctx):
    """Las entradas del cálculo puro. El MENSAJE del usuario no se guarda: solo la intención derivada (privacidad).
    Tampoco los argumentos de herramientas que admiten texto libre (_ARGS_SAFE)."""
    ctx = ctx or {}
    clean_calls, args_of = [], list(ctx.get('args_of') or [])
    for i, c in enumerate(calls or []):
        name, _args, ok, res = c
        clean_calls.append([name, None, bool(ok), res if (ok and name in _b.BUILDERS) else None])
        if i < len(args_of) and name not in _ARGS_SAFE:
            args_of[i] = ''
    args_of = [str(a)[:200] if isinstance(a, str) else '' for a in args_of[:len(clean_calls)]]
    return {'v': 1, 'impl': IMPL, 'lang': 'en' if lang == 'en' else 'es', 'mode': ctx.get('mode') or 'simple',
            'intent': _layout.intent_of(message), 'now': ctx.get('now') or now_iso(),
            'entities': [{'id': e.get('id'), 'label': e.get('label')} for e in entities or [] if isinstance(e, dict)],
            'answer': ctx.get('answer') or '', 'actions': ctx.get('actions') or [],
            'sources': _clean_sources(ctx.get('sources')), 'facts': ctx.get('facts') or [],
            'fact_of': list(ctx.get('fact_of') or []), 'args_of': args_of,
            'meta': ctx.get('meta') if isinstance(ctx.get('meta'), dict) else gather_meta(calls), 'calls': clean_calls}


def build_ui(message, calls, entities, plan=None, lang='es', ctx=None):
    """→ (sobre | None, texto). `plan` (el layout de la IA) llega en F5: hoy siempre el orden automático, y el texto
    es `ctx['answer']` tal cual. Nunca lanza: ante cualquier error, (None, texto) y la respuesta sigue igual."""
    ctx = ctx or {}
    answer = ctx.get('answer') or ''
    t0 = time.perf_counter()
    try:
        inputs = inputs_for(message, calls, entities, lang, ctx)
        env, info = build_core(inputs)
        ms = (time.perf_counter() - t0) * 1000
        size = _size(env) if env else 0
        _record(ms, size, env, info['dropped'], info['checked'], info['unprov'])
        if env is not None:
            env['_inputs'] = inputs          # lo quita quien lo envía (khipu_chat); va al libro para el replay
        return env, answer
    except Exception as e:  # noqa: BLE001
        log.warning('genui: no se pudo armar el sobre (%s)', type(e).__name__, exc_info=True)
        _record(0, 0, None, [], 0, 0, error=type(e).__name__)
        return None, answer


def rebuild(inputs):
    """Repetir (replay): el sobre que se construyó con esas entradas. Determinista (mismo código = mismo sobre)."""
    env, _info = build_core(inputs)
    return env


def finite(obj):
    """Copia con NaN/Infinity → None (el libro guarda JSON estricto)."""
    import math
    if isinstance(obj, dict):
        return {k: finite(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [finite(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def public(env):
    """El sobre tal como se envía (sin las entradas internas)."""
    if not isinstance(env, dict):
        return None
    return {k: v for k, v in env.items() if not k.startswith('_')}
