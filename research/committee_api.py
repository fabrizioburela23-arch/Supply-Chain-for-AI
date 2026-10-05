"""research/committee_api.py — blueprint /api/committee/* (PHASE 3).

POST /run                         {entity, client_id?, actor, sync?} → corre el comité (segundo plano;
                                  sync solo con PIN; dedupe por entidad+cliente; tope simultáneo → 429)
GET  /memo/<id>                   memo completo (si tiene cliente: montos solo con X-Trade-Pin)
GET  /entity/<id>                 último memo + historial de memos de la entidad
POST /memo/<id>/approve           (X-Trade-Pin) aprobación humana → previsualización en corretaje
POST /memo/<id>/reject            (X-Trade-Pin) rechazo con motivo
GET  /track-record[?agent=]       historial por agente (aciertos, Brier, fiabilidad)
GET  /calibration                 tabla de calibración + fotos periódicas
POST /outcomes/evaluate           (X-Trade-Pin) califica predicciones vencidas (también 1×/día solo)
GET  /outcomes/recent             últimas calificaciones (auditoría)
GET  /clients                     (X-Trade-Pin) clientes del módulo de corretaje (para elegir)
Sin DATABASE_URL → 503. Sin IA → memo determinista rotulado "sin IA".
PIN: header X-Trade-Pin == env TRADE_PIN vía core.pin (auditoría #7): MISMO contador
por IP y GLOBAL que /api/trade, /api/brokerage, /api/mcp y la ontología (antes se
comparaba aquí sin freno → adivinanza ilimitada del PIN). Sin TRADE_PIN → 403.
"""
import logging
import threading

from flask import Blueprint, current_app, jsonify, request

from core import pin as _core_pin
from core.http import rate_limit
from ontology.db import ontology_available, session_scope

log = logging.getLogger('khipu')

committee_bp = Blueprint('committee', __name__, url_prefix='/api/committee')


def _unavailable():
    return jsonify({'error': 'comité no disponible', 'error_en': 'committee not available', 'available': False,
                    'detail': 'Falta DATABASE_URL (el comité guarda sus memos en la ontología).'}), 503


def _pin_status():
    """None si el PIN es válido; si no, (respuesta, código). core.pin: cuenta los
    fallos en el contador COMPARTIDO y respeta el bloqueo por IP y global."""
    return _core_pin.pin_error(where='committee', strict=True)


def _pin_ok():
    """¿PIN válido? (para mostrar montos del cliente). Un PIN vacío no cuenta
    como fallo, así la vista redactada no suma al contador."""
    return _core_pin.check(where='committee', strict=True) is None


def _actor(body):
    return str((body or {}).get('actor') or '').strip()[:120]


def _with_schema(fn):
    """Si las tablas de Phase 3 aún no existen (base que arrancó después), las crea y reintenta."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        if 'does not exist' not in str(e) and 'UndefinedTable' not in type(e).__name__ + str(e):
            raise
        from ontology.db import init_schema
        init_schema(retries=1)
        return fn()


def _run_async(memo_id, eid, actor, client_id):
    """Corre el comité en un hilo. El cupo (acquire_run_slot) ya se tomó: se
    libera al terminar, pase lo que pase."""
    def _work():
        from research.committee import fail_memo, progress_clear, progress_set, release_run_slot, run_committee
        progress_set(memo_id, 'claims')
        try:
            with session_scope() as s:
                run_committee(s, eid, actor, client_id=client_id, memo_id=memo_id)
        except Exception as e:  # noqa: BLE001
            log.warning('committee %s: %s', memo_id, e)
            try:
                with session_scope() as s:
                    fail_memo(s, memo_id, f'{type(e).__name__}: {str(e)[:300]}')
            except Exception:  # noqa: BLE001
                pass
        finally:
            release_run_slot()
            progress_clear(memo_id)
    t = threading.Thread(target=_work, name=f'committee-{memo_id[:8]}', daemon=True)
    t.start()
    return t


def _busy():
    return jsonify({'error': 'el comité ya está deliberando otros pedidos; intenta en un minuto',
                    'error_en': 'the committee is already deliberating other requests; try again in a minute',
                    'code': 'busy'}), 429


@committee_bp.route('/run', methods=['POST'])
@rate_limit(limit=10, window=3600)
def run():
    """Corre el comité (asíncrono: 202 + memo_id). Con client_id exige PIN.
    `sync: true` (espera la respuesta en el hilo del pedido) SOLO con PIN válido
    o en tests: sin eso, unos pocos pedidos en paralelo ocuparían los 8 hilos
    del servidor. Mismo (entidad, cliente) deliberando o recién propuesto → se
    reutiliza ese memo (no se gasta IA dos veces). Tope de comités simultáneos:
    COMMITTEE_MAX_CONCURRENT (2) → 429."""
    if not ontology_available():
        return _unavailable()
    body = request.get_json(silent=True) or {}
    actor = _actor(body)
    if not actor:
        return jsonify({'error': 'actor obligatorio', 'error_en': 'actor is required'}), 400
    from core.entities import UMBRAL_BUSQUEDA, resolve
    r = resolve(str(body.get('entity') or '')[:120], umbral=UMBRAL_BUSQUEDA)
    if not r:
        return jsonify({'error': 'entidad no encontrada', 'error_en': 'entity not found'}), 404
    eid = r['id']
    client_id = str(body.get('client_id') or '').strip()[:60] or None
    if client_id:
        bad = _pin_status()          # datos de la cuenta de un cliente → PIN
        if bad:
            return bad
    sync = bool(body.get('sync')) and (current_app.config.get('TESTING') or _pin_ok())
    from research.committee import (acquire_run_slot, create_placeholder, recent_memo, release_run_slot,
                                    run_committee)
    try:
        def _reuse():
            with session_scope() as s:
                m = recent_memo(s, eid, client_id)
                return (m.id, m.status) if m else None
        prev = _with_schema(_reuse)
    except Exception as e:  # noqa: BLE001
        log.warning('committee run (dedupe): %s', e)
        prev = None
    if prev and not sync:
        return jsonify({'memo_id': prev[0], 'entity_id': eid, 'status': prev[1], 'reused': True}), 202
    if not acquire_run_slot():
        return _busy()
    started = False
    try:
        if sync:
            def _sync():
                with session_scope() as s:
                    out = run_committee(s, eid, actor, client_id=client_id)
                if out and out.get('memo_id'):
                    from research.committee import progress_clear
                    progress_clear(out['memo_id'])
                return out
            return jsonify(_with_schema(_sync))

        def _ph():
            with session_scope() as s:
                return create_placeholder(s, eid, actor, client_id).id
        mid = _with_schema(_ph)
        _run_async(mid, eid, actor, client_id)
        started = True
    except Exception as e:  # noqa: BLE001
        log.warning('committee run: %s', e)
        return jsonify({'error': 'no se pudo correr el comité', 'error_en': 'the committee could not run',
                        'detail': f'{type(e).__name__}: {str(e)[:240]}'}), 500
    finally:
        if not started:
            release_run_slot()           # el hilo libera el cupo solo si arrancó
    return jsonify({'memo_id': mid, 'entity_id': eid, 'status': 'running'}), 202


@committee_bp.route('/memo/<memo_id>')
@rate_limit(limit=120, window=60)
def memo(memo_id):
    if not ontology_available():
        return _unavailable()
    from research.committee import fail_memo, get_memo, progress_get
    with session_scope() as s:
        d = get_memo(s, memo_id, redact_client=not _pin_ok())
        if d and d.get('status') == 'running':
            prog = progress_get(memo_id)
            if prog:
                d['progress'] = prog
            elif _age_s(d.get('created_at')) > 90:
                # nadie lo está calculando (reinicio del servidor a mitad): no
                # dejar la pantalla "cargando" para siempre
                fail_memo(s, memo_id, 'se interrumpió (el servidor se reinició); vuelve a correr el comité',
                          'interrupted (the server restarted); run the committee again')
                d = get_memo(s, memo_id, redact_client=not _pin_ok())
    if not d:
        return jsonify({'error': 'memo no encontrado', 'error_en': 'memo not found'}), 404
    return jsonify(d)


def _age_s(iso):
    from datetime import datetime, timezone
    try:
        t = datetime.fromisoformat(str(iso).replace('Z', '+00:00'))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - t).total_seconds()
    except Exception:  # noqa: BLE001
        return 0


@committee_bp.route('/entity/<entity_id>')
@rate_limit(limit=120, window=60)
def entity(entity_id):
    if not ontology_available():
        return _unavailable()
    from core.entities import UMBRAL_BUSQUEDA, resolve
    from research.committee import latest_memo, list_memos
    r = resolve(entity_id[:120], umbral=UMBRAL_BUSQUEDA)
    eid = r['id'] if r else entity_id[:120]
    try:
        def _q():
            with session_scope() as s:
                return {'entity_id': eid, 'latest': latest_memo(s, eid, redact_client=not _pin_ok()),
                        'history': list_memos(s, eid, limit=20)}
        return jsonify(_with_schema(_q))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo leer el comité', 'error_en': 'could not read the committee', 'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500


def _decide(memo_id, fn):
    if not ontology_available():
        return _unavailable()
    bad = _pin_status()
    if bad:
        return bad
    body = request.get_json(silent=True) or {}
    actor = _actor(body)
    if not actor:
        return jsonify({'error': 'actor obligatorio', 'error_en': 'actor is required'}), 400
    with session_scope() as s:
        out = fn(s, memo_id, actor, body)
    code = 200 if out.get('ok') else {'not_found': 404, 'expired': 409, 'bad_status': 409, 'order_sent': 409,
                                      'preview_failed': 409, 'confirm_failed': 409, 'not_tradable': 409,
                                      'brokerage_unavailable': 409, 'withdraw_failed': 409}.get(out.get('code'), 400)
    return jsonify(out), code


@committee_bp.route('/memo/<memo_id>/approve', methods=['POST'])
@rate_limit(limit=30, window=3600)
def approve(memo_id):
    from research.committee import approve_memo
    return _decide(memo_id, lambda s, mid, actor, b: approve_memo(s, mid, actor, note=str(b.get('note') or '')))


@committee_bp.route('/memo/<memo_id>/reject', methods=['POST'])
@rate_limit(limit=30, window=3600)
def reject(memo_id):
    from research.committee import reject_memo
    return _decide(memo_id, lambda s, mid, actor, b: reject_memo(s, mid, actor, reason=str(b.get('reason') or '')))


@committee_bp.route('/portfolio', methods=['POST'])
@rate_limit(limit=30, window=3600)
def portfolio_committee():
    """Comité de CARTERA (core/portfolio_advisor): riesgo medido + perfil +
    investigación → acciones concretas como consejo. Nunca ejecuta nada."""
    from core import portfolio_advisor as pa
    from core.ai_usage import ai_context
    body = request.get_json(silent=True) or {}
    positions = body.get('positions') if isinstance(body.get('positions'), list) else []
    lang = 'en' if str(body.get('lang', 'es')).lower().startswith('en') else 'es'
    profile = body.get('profile') if isinstance(body.get('profile'), dict) else {}
    with ai_context('comite_cartera', str(body.get('actor') or '').strip()[:120] or None):
        try:
            out = pa.analyze(positions, profile=profile, lang=lang, cash_usd=body.get('cash_usd') or 0)
        except Exception as e:  # noqa: BLE001
            log.warning('portfolio committee: %s', e)
            return jsonify({'ok': False, 'error': 'no se pudo analizar la cartera', 'error_en': 'could not analyze the portfolio',
                            'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500
        if out.get('ok'):
            _attach_geo(out)
        if out.get('ok') and body.get('explain', True):
            out['explanation'] = pa.explain(out, lang)
    if out.get('ok') and body.get('save', True):
        _register_portfolio_analysis(out, body, lang)
    return jsonify(out), (200 if out.get('ok') else 422)


def _attach_geo(a):
    """Cruza cada posición con la geopolítica EN VIVO (core/world.entity_geo_risks). Nunca rompe el análisis."""
    try:
        from core.world import entity_geo_risks
        rows = [r for r in (a.get('positions') or []) if r.get('entity_id')]
        risks = entity_geo_risks([r['entity_id'] for r in rows])
        a['geo_risks'] = [{'entity_id': r['entity_id'], 'label': r.get('label'), 'symbol': r.get('symbol'),
                           'items': risks[r['entity_id']]} for r in rows if r['entity_id'] in risks]
    except Exception as e:  # noqa: BLE001
        log.info('committee geo: %s', e)
        a['geo_risks'] = []
    a['geo_exposure'] = _geo_exposure(a)
    return a


def _geo_exposure(a):
    """Exposición geopolítica ESTRUCTURAL de la cartera (2026-10-05: la pregunta "¿cuáles son los riesgos
    geopolíticos de mi cartera?" necesita esto aunque hoy no haya eventos en vivo): peso por país (con el
    riesgo-país curado de la Sala de Situación) y estrechos de los que dependen las posiciones."""
    try:
        from core.geosit import CHOKEPOINTS, COUNTRIES
        from core.world import _graph
        g = _graph()
        inst = {c['ck']: c for c in COUNTRIES}
        by_c, chk = {}, []
        rows = [r for r in (a.get('positions') or []) if r.get('entity_id')]
        for r in rows:
            ck = (g['by_id'].get(r['entity_id']) or {}).get('country_key') or '—'
            d = by_c.setdefault(ck, {'country': ck, 'weight_pct': 0.0, 'labels': []})
            d['weight_pct'] += float(r.get('weight_pct') or 0)
            d['labels'].append(r.get('label'))
        countries = []
        for ck, d in by_c.items():
            c = inst.get(ck) or {}
            countries.append({**d, 'weight_pct': round(d['weight_pct'], 1), 'country_es': c.get('es') or ck,
                              'country_en': c.get('en') or ck, 'risk_base': c.get('base')})
        countries.sort(key=lambda x: -x['weight_pct'])
        for c in CHOKEPOINTS:
            hit = [r for r in rows if r['entity_id'] in (c.get('affected') or [])]
            if hit:
                chk.append({'es': c['es'], 'en': c['en'], 'risk_base': c.get('base'), 'why_es': c.get('why_es'),
                            'why_en': c.get('why_en'), 'labels': [r.get('label') for r in hit],
                            'weight_pct': round(sum(float(r.get('weight_pct') or 0) for r in hit), 1)})
        chk.sort(key=lambda x: -x['weight_pct'])
        return {'countries': countries[:8], 'chokepoints': chk[:6], 'note_es': 'riesgo-país y estrechos: base curada '
                '(Sala de Situación), no un evento de hoy', 'note_en': 'country risk and straits: curated base '
                '(Situation Room), not an event from today'}
    except Exception as e:  # noqa: BLE001
        log.info('committee geo exposure: %s', e)
        return {'countries': [], 'chokepoints': []}


def portfolio_notes(a, lang='es'):
    """Análisis del comité de cartera → texto verificado para el cerebro de Khipu (contexto
    'portfolio_notes'): KPIs, cada posición, acciones sugeridas, lo que quedó fuera."""
    k, h, P = a.get('kpis') or {}, a.get('health') or {}, a.get('profile') or {}
    cv = a.get('coverage') or {}
    lines = [f"Salud de la cartera {h.get('score')}/100 frente al perfil {P.get('label')}: {h.get('verdict')}.",
             f"Valor {k.get('value_usd')} USD (efectivo {k.get('cash_usd')} USD); volatilidad anual {k.get('vol_ann_pct')} % "
             f"(objetivo del perfil {P.get('target_vol')} %); peor caída del año {k.get('max_drawdown_pct')} %; "
             f"VaR 95 % a 1 día {k.get('var95_1d_usd')} USD; beta vs S&P 500 {k.get('beta_spy')}.",
             f"Tope sugerido por posición {P.get('max_position')} % y por sector {P.get('max_sector')} %.",
             f"Cobertura: {cv.get('analyzed')} de {cv.get('requested')} posiciones medidas; "
             f"{cv.get('researched')} con opinión de los analistas."]
    for r in (a.get('positions') or [])[:40]:
        conv = 'sin investigar' if r.get('conviction') is None else f"{r['conviction']:+.0f}"
        lines.append(f"{r.get('label')} ({r.get('symbol')}): peso {r.get('weight_pct')} %, aporta {r.get('risk_contrib_pct')} % "
                     f"del riesgo, volatilidad {r.get('vol_ann_pct')} %, valor {r.get('value_usd')} USD, sector "
                     f"{r.get('sector') or '—'}, convicción de los analistas {conv}.")
    for x in (a.get('actions') or [])[:8]:
        lines.append(f"Acción sugerida {x['id']} ({x['kind']}, prioridad {x['priority']}): {x.get('label') or ''} de "
                     f"{x['from_pct']} % a {x['to_pct']} % ({x['delta_usd']} USD) — {x['why_es']}")
    for s in (a.get('sectors') or [])[:8]:
        lines.append(f"Sector {s.get('label')}: {s.get('weight_pct')} % ({s.get('n')} posiciones).")
    for p in (a.get('correlated_pairs') or [])[:3]:
        lines.append(f"Se mueven juntas: {p['a']} y {p['b']} (correlación {p['corr']}).")
    for x in (a.get('excluded') or [])[:10]:
        lines.append(f"No analizada: {x.get('label') or x.get('symbol')} — {x.get('reason')}.")
    gx = a.get('geo_exposure') or {}
    for c in gx.get('countries') or []:
        lines.append(f"Exposición por país: {c['country_es']} {c['weight_pct']} % de la cartera ({', '.join(c['labels'][:6])})"
                     f"{'; riesgo-país estructural ' + str(c['risk_base']) + '/100' if c.get('risk_base') is not None else ''}.")
    for c in gx.get('chokepoints') or []:
        lines.append(f"Dependen del {c['es']} (riesgo estructural {c['risk_base']}/100): {', '.join(c['labels'])} "
                     f"= {c['weight_pct']} % de la cartera. {c.get('why_es') or ''}")
    if not (a.get('geo_risks') or []):
        lines.append('Geopolítica EN VIVO: hoy no hay reglas/sanciones que nombren a estas empresas, ni caídas de tráfico '
                     'en sus estrechos, ni eventos cerca de sus sedes conocidas.')
    for gr in (a.get('geo_risks') or [])[:12]:
        for it in gr['items']:
            lines.append(f"Geopolítica EN VIVO para {gr['label']} ({gr['symbol']}): {it['title_es']} — {it['why_es']}"
                         f"{' a ' + str(it['distance_km']) + ' km' if it.get('distance_km') is not None else ''}; "
                         f"severidad {it['severity']}; fuente {it['source']} ({str(it.get('time') or '')[:10]}).")
    lines.append(f"Datos: {a.get('source')} al {a.get('as_of')}. Es consejo educativo, nunca una orden.")
    return '\n'.join(str(x) for x in lines)


def portfolio_fallback(a, lang='es'):
    """Respuesta SIN IA, solo con el análisis calculado (nunca una lista genérica del mundo)."""
    es = lang != 'en'
    h, gx = a.get('health') or {}, a.get('geo_exposure') or {}
    out = [f"**{h.get('score')}/100** — {h.get('verdict')}"]
    for x in (a.get('actions') or [])[:3]:
        out.append(f"- {x.get('label')}: {x['from_pct']:.0f} % → {x['to_pct']:.0f} % — {x['why_es'] if es else x['why_en']}")
    geo_live = [(g['label'], it) for g in (a.get('geo_risks') or []) for it in g['items']]
    out.append('**Geopolítica en vivo:**' if es else '**Live geopolitics:**')
    if geo_live:
        for lab, it in geo_live[:5]:
            out.append(f"- {lab}: {it['title_es'] if es else it['title_en']} — {it['why_es'] if es else it['why_en']}")
    else:
        out.append('- Hoy no hay eventos, reglas ni sanciones en vivo que toquen directamente tus posiciones.' if es else
                   '- No live events, rules or sanctions touch your holdings directly today.')
    if gx.get('countries') or gx.get('chokepoints'):
        out.append('**Exposición estructural:**' if es else '**Structural exposure:**')
        for c in (gx.get('countries') or [])[:3]:
            out.append(f"- {c['country_es'] if es else c['country_en']}: {c['weight_pct']} %"
                       + (f" (riesgo-país {c['risk_base']}/100)" if es and c.get('risk_base') is not None else
                          f" (country risk {c['risk_base']}/100)" if c.get('risk_base') is not None else ''))
        for c in (gx.get('chokepoints') or [])[:3]:
            out.append(f"- {c['es'] if es else c['en']}: {', '.join(c['labels'])} ({c['weight_pct']} %)")
    return '\n'.join(out)


def portfolio_card(a):
    """Resumen compacto para la tarjeta dentro del chat."""
    return {'score': (a.get('health') or {}).get('score'), 'tone': (a.get('health') or {}).get('tone'),
            'verdict': (a.get('health') or {}).get('verdict'), 'value_usd': (a.get('kpis') or {}).get('value_usd'),
            'vol_ann_pct': (a.get('kpis') or {}).get('vol_ann_pct'), 'coverage': a.get('coverage'),
            'profile': (a.get('profile') or {}).get('label'),
            'actions': [{k: x.get(k) for k in ('id', 'kind', 'label', 'from_pct', 'to_pct', 'delta_usd', 'priority', 'why_es', 'why_en')}
                        for x in (a.get('actions') or [])[:4]],
            'excluded': [x.get('label') or x.get('symbol') for x in (a.get('excluded') or [])][:8],
            'geo': [{'label': g['label'], 'title_es': it['title_es'], 'title_en': it['title_en'], 'why_es': it['why_es'],
                     'why_en': it['why_en'], 'severity': it['severity'], 'url': it.get('url')}
                    for g in (a.get('geo_risks') or []) for it in g['items'][:1]][:4]}


@committee_bp.route('/portfolio/ask', methods=['POST'])
@rate_limit(limit=30, window=3600)
def portfolio_ask():
    """El COMITÉ DE CARTERA dentro del chat (pedido 2026-10-05: "/cartera dime si debería
    reducir…" debía RESPONDER, no abrir una pantalla): mide la cartera (core/portfolio_advisor,
    precios reales), guarda el análisis en el historial y el cerebro de Khipu contesta la
    pregunta con ese análisis como contexto verificado. Nunca da órdenes."""
    from core import khipu_chat as kc
    from core import portfolio_advisor as pa
    from core.ai_usage import ai_context
    body = request.get_json(silent=True) or {}
    lang = 'en' if str(body.get('lang', 'es')).lower().startswith('en') else 'es'
    q = str(body.get('question') or '').strip()[:1500] or (
        'Analyze my portfolio: its health, main risks and what you would change.' if lang == 'en'
        else 'Analiza mi cartera: su salud, los riesgos principales y qué cambiarías.')
    positions = body.get('positions') if isinstance(body.get('positions'), list) else []
    profile = body.get('profile') if isinstance(body.get('profile'), dict) else {}
    who = str(body.get('actor') or '').strip()[:120] or None
    label = str(body.get('source_label') or '').strip()[:60]
    agent = {'name': 'Comité de cartera' if lang == 'es' else 'Portfolio committee', 'emoji': '💼', 'seat': 'portfolio',
             'label': label or None}
    # UN analista concreto sobre la cartera (2026-10-05: "quisiera preguntarle a un agente específico… no que me
    # obligue a analizar con todo el comité"): responde SOLO desde su especialidad, sin la tarjeta del comité.
    from research.ask_agent import ROLE
    from research.deliberation import AGENT_NAMES
    seat = str(body.get('seat') or '').strip()
    seat = seat if seat in ROLE else None
    if seat:
        em, n_es, n_en = AGENT_NAMES.get(seat, ('🤖', seat, seat))
        agent = {'name': n_en if lang == 'en' else n_es, 'emoji': em, 'seat': seat, 'label': label or None}
        q = (f"[Answer ONLY as the {ROLE[seat][1]} of the committee, from your specialty, about the user's portfolio. "
             f"Do not give the whole committee's verdict.] {q}" if lang == 'en' else
             f"[Responde SOLO como {ROLE[seat][0]} del comité, desde tu especialidad, sobre la cartera del usuario. "
             f"No des el veredicto de todo el comité.] {q}")
    with ai_context('comite_cartera_chat', who):
        try:
            a = pa.analyze(positions, profile=profile, lang=lang, cash_usd=body.get('cash_usd') or 0)
        except Exception as e:  # noqa: BLE001
            log.warning('portfolio ask: %s', e)
            a = {'ok': False, 'error': f'{type(e).__name__}'}
        if not a.get('ok'):
            msg = (a.get('error_en') if lang == 'en' else None) or a.get('error') or 'could not analyze'
            return jsonify({'ok': False, 'agent': agent, 'degraded': True,
                            'answer': (f"I could not measure your portfolio: {msg}" if lang == 'en'
                                       else f"No pude medir tu cartera: {msg}"),
                            'excluded': a.get('excluded') or []}), 200
        _attach_geo(a)
        if body.get('save', True) and not seat:
            _register_portfolio_analysis(a, {'source_label': label}, lang)
        hist = body.get('history') if isinstance(body.get('history'), list) else []
        try:
            req = kc.validate_request({'message': q, 'history': hist, 'lang': lang})
        except Exception:  # noqa: BLE001
            req = {'message': q[:1500], 'history': [], 'lang': lang}
        ctx = {'portfolio_notes': portfolio_notes(a, lang)}
        # Respuesta ENFOCADA en la cartera: una sola redacción con el análisis ya calculado (sin el bucle de
        # herramientas, que se iba a "conflictos del mundo" y se quedaba sin tiempo — feedback 2026-10-05).
        out = {}
        try:
            text, model = kc.synthesize(req['message'], req['history'], lang, ctx, [], 40)
            if text:
                out = {'answer': text, 'ai': True, 'model': model}
        except Exception as e:  # noqa: BLE001
            log.info('portfolio ask synth: %s', e)
        if not out:
            out = {'answer': portfolio_fallback(a, lang), 'ai': False, 'degraded': True,
                   'ai_detail_es': 'La IA no respondió a tiempo; te muestro el análisis calculado.',
                   'ai_detail_en': 'The AI did not answer in time; here is the computed analysis.'}
    out = dict(out or {})
    out.update(ok=True, agent=agent, portfolio=None if seat else portfolio_card(a), saved_id=a.get('saved_id'))
    acts = [x for x in (out.get('actions') or []) if isinstance(x, dict)]
    acts.append({'type': 'open_pf_committee', 'arg': None})
    out['actions'] = acts
    return jsonify(out)


def _register_portfolio_analysis(out, body, lang):
    """Pedido 2026-10-05 ("que se registre"): cada análisis del comité de cartera
    queda guardado por dueño (X-Khipu-Owner) como reporte kind='committee', para
    volver a verlo en Comité → 💼 Mi cartera → Análisis anteriores. Sin llave o
    sin base, el análisis igual se devuelve (solo no se guarda)."""
    try:
        from core.portfolio_reports_api import _db, _owner
        owner = _owner()
        if not owner or not _db():
            return
        import json
        from datetime import datetime, timezone

        from research.models import PortfolioReport
        name = str(body.get('source_label') or '').strip()[:60]
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        h = out.get('health') or {}
        title = f"{'Committee' if lang == 'en' else 'Comité'}{' · ' + name if name else ''} · {today}"[:200]
        with session_scope() as s:
            r = PortfolioReport(owner_hash=owner, kind='committee', title=title, period_from=today, period_to=today,
                                summary=f"{h.get('score', '')}/100 · {h.get('verdict') or ''}"[:500],
                                data=json.loads(json.dumps({**out, 'source_label': name or None}, default=str)), read=True)
            s.add(r)
            s.flush()
            out['saved_id'] = r.id
    except Exception as e:  # noqa: BLE001 — guardar nunca rompe el análisis
        log.warning('portfolio committee store: %s', e)


@committee_bp.route('/board')
def board_route():
    if not ontology_available():
        return _unavailable()
    from research.committee import board
    try:
        lim = max(1, min(int(request.args.get('limit', 40)), 80))
    except (TypeError, ValueError):
        lim = 40
    try:
        def _q():
            with session_scope() as s:
                return board(s, limit=lim)
        return jsonify(_with_schema(_q))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo armar la pizarra', 'error_en': 'could not build the board',
                        'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500


@committee_bp.route('/board/refresh', methods=['POST'])
@rate_limit(limit=4, window=3600)
def board_refresh():
    """Encarga investigación para hasta 3 empresas (viejas, pedidas o clave) y la
    corre EN SERIE en un hilo (una a la vez: respeta el presupuesto y la IA)."""
    if not ontology_available():
        return _unavailable()
    from core.ai import _ai_configured
    body = request.get_json(silent=True) or {}
    actor = str(body.get('actor') or '').strip()[:120]
    if not actor:
        return jsonify({'error': 'actor obligatorio', 'error_en': 'actor required'}), 400
    if not _ai_configured():
        return jsonify({'error': 'ningún proveedor de IA configurado', 'error_en': 'no AI provider configured'}), 503
    from research.committee import refresh_targets
    from research.runner import budget_exhausted, create_job, daily_budget, defer_job, execute_job_async
    if daily_budget() <= 0:
        return jsonify({'error': 'la investigación está apagada (RESEARCH_DAILY_BUDGET_USD = 0)',
                        'error_en': 'research is switched off (RESEARCH_DAILY_BUDGET_USD = 0)', 'code': 'research_off'}), 503
    ents = body.get('entities') if isinstance(body.get('entities'), list) else None
    try:
        def _plan():
            with session_scope() as s:
                targets = refresh_targets(s, max_n=3, entities=ents)
                jobs = []
                for eid in targets:
                    job, reused = create_job(s, eid, depth='STANDARD', trigger={'kind': 'board', 'by': actor},
                                             requested_by=actor)
                    # R8: sin presupuesto, el pedido de la persona queda DIFERIDO (no se pierde)
                    if not reused and job.status == 'queued' and budget_exhausted(s):
                        defer_job(s, job)
                    jobs.append({'entity_id': eid, 'job_id': job.id, 'reused': reused, 'status': job.status,
                                 'resume_after': (job.trigger or {}).get('resume_after')})
                return jobs
        jobs = _with_schema(_plan)
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo encargar la investigación', 'error_en': 'could not queue research',
                        'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500
    # R8: por la cola FIFO (RESEARCH_JOB_CONCURRENCY), no en un hilo propio: respeta cupos y es visible en salud
    for j in jobs:
        if not j['reused'] and j['status'] == 'queued':
            execute_job_async(j['job_id'])
    return jsonify({'jobs': jobs, 'n': len(jobs), 'deferred': sum(1 for j in jobs if j['status'] == 'deferred')}), 202


@committee_bp.route('/track-record')
def track_record():
    if not ontology_available():
        return _unavailable()
    from research.outcomes import track_record as tr
    agent = (request.args.get('agent') or '').strip()[:40] or None
    try:
        def _q():
            with session_scope() as s:
                return tr(s, agent_type=agent)
        return jsonify(_with_schema(_q))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo calcular el historial', 'error_en': 'could not compute the track record', 'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500


@committee_bp.route('/calibration')
def calibration():
    if not ontology_available():
        return _unavailable()
    from research.outcomes import BUCKETS, CAL_METHOD, MIN_N, calibration_table, k_default, snapshots
    try:
        def _q():
            with session_scope() as s:
                return {'table': calibration_table(s), 'k': k_default(), 'min_n': MIN_N, 'method': CAL_METHOD,
                        'buckets': [list(b) for b in BUCKETS],
                        'formula': '(aciertos_tramo + k·cruda) / (n_tramo + k)',
                        'snapshots': snapshots(s, limit=60)}
        return jsonify(_with_schema(_q))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo leer la calibración', 'error_en': 'could not read the calibration', 'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500


@committee_bp.route('/outcomes/evaluate', methods=['POST'])
@rate_limit(limit=12, window=3600)
def evaluate():
    if not ontology_available():
        return _unavailable()
    bad = _pin_status()
    if bad:
        return bad
    from research.outcomes import evaluate_due
    try:
        def _q():
            with session_scope() as s:
                return evaluate_due(s)
        return jsonify(_with_schema(_q))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo evaluar', 'error_en': 'could not score', 'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500


@committee_bp.route('/outcomes/recent')
def outcomes_recent():
    if not ontology_available():
        return _unavailable()
    from research.outcomes import recent_outcomes
    try:
        limit = min(max(int(request.args.get('limit', 30)), 1), 100)
    except (TypeError, ValueError):
        limit = 30
    agent = (request.args.get('agent') or '').strip()[:40] or None
    try:
        def _q():
            with session_scope() as s:
                return {'outcomes': recent_outcomes(s, limit=limit, agent_type=agent)}
        return jsonify(_with_schema(_q))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo leer', 'error_en': 'could not read', 'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500


@committee_bp.route('/clients')
@rate_limit(limit=60, window=60)
def clients():
    if not ontology_available():
        return _unavailable()
    bad = _pin_status()
    if bad:
        return bad
    from research.committee import brokerage_service
    svc = brokerage_service()
    if svc is None:
        return jsonify({'available': False, 'clients': [],
                        'detail': 'módulo de corretaje no instalado o no disponible'})
    try:
        with session_scope() as s:
            rows = svc.list_clients(s) or []
    except Exception as e:  # noqa: BLE001
        return jsonify({'available': False, 'clients': [], 'detail': f'{type(e).__name__}: {str(e)[:200]}'})
    keep = ('id', 'client_id', 'name', 'display_name', 'mode', 'status', 'live_enabled')
    return jsonify({'available': True, 'clients': [{k: c.get(k) for k in keep if k in c} for c in rows]})
