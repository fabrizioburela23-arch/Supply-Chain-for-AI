"""Agente de trading de la cuenta de la casa — /api/trade/agent/* (G5-05, lote I4: salió de server.py SIN cambiar
comportamiento).

Sus órdenes van por el MISMO camino que todo lo demás (brokerage.service.house_order → brokerage/alpaca.py, el único
archivo que hace POST/DELETE a /v2/orders|positions). Cada encendido/apagado/cambio es una decisión policy.change
(trade.agent_config); tras un despliegue queda APAGADO con aviso (BRECHAS #14).

Lo que es del servidor (claves y base de Alpaca, FINNHUB, el tope por orden, _paper, _trade_audit, las respuestas de
error…) se lee EN CADA LLAMADA por `_S` (server.py llama a bind()): un monkeypatch sobre `server` se ve aquí igual que
antes. Las pruebas que reemplazan funciones DEL AGENTE (p. ej. _agent_analyze) parchean este módulo.
"""
import json
import logging
import re
import threading
import time
import uuid

import requests
from flask import Blueprint, jsonify

from core.http import rate_limit
from core.pin import require_pin as _trade_auth

log = logging.getLogger('khipu')
trading_agent_bp = Blueprint('trading_agent', __name__)
_S = None          # el módulo del servidor (bind)


def bind(host):
    """server.py se pasa a sí mismo: la config y los ayudantes de la cuenta de la casa se leen de ahí en cada llamada."""
    global _S
    _S = host


# ── AI Trading Agent ─────────────────────────────────────────────────────────
# Endurecimiento (auditoría estructural 2026-09-30, #11/#12/#21):
#  · parámetros ACOTADOS (max_pos_pct 0.5-10, max_daily_loss_pct 0.5-5,
#    stop_loss_pct 0.5-20, min_confidence 50-100, órdenes/ciclo 1-5,
#    intervalo 5-1440 min) y mode ∈ {manual, auto}; arranque bajo lock (sin
#    dos hilos a la vez);
#  · modo AUTO (órdenes sin aprobación por orden) SOLO en cuenta de PAPEL: con
#    dinero real se rechaza (403 'auto_live_refused') y el ciclo no envía nada;
#  · interruptor BROKERAGE_TRADING_ENABLED=off → el agente no envía órdenes;
#  · una orden que Alpaca RECHAZA (4xx/5xx) queda como ERROR, nunca como
#    ejecutada; cada intento va a broker_audit (o al log sin base);
#  · stop-loss cripto con time_in_force 'gtc' (Alpaca no acepta 'day' en
#    cripto) y sin reenviar el cierre si ya hay uno pendiente;
#  · universo saneado: solo acciones de EE.UU. operables en Alpaca (los
#    tickers extranjeros del grafo se descartan; ya no van crudos a la URL).

_AGENT: dict = {
    'running': False,
    'mode': 'manual',          # 'manual' | 'auto'
    'interval_min': 15,
    'universe': ['NVDA','TSM','AMD','INTC','ASML','AMAT','QCOM','AVGO','MU','TSLA'],
    'max_pos_pct': 5.0,        # max % of equity per position
    'max_daily_loss_pct': 2.0, # daily circuit-breaker
    'stop_loss_pct': 3.0,      # per-position stop
    'min_confidence': 65,      # umbral para ejecutar (antes hardcodeado)
    'max_orders_per_cycle': 3, # freno duro anti-loop: máx órdenes nuevas por ciclo
    'log': [],
    'thread': None,
    'last_run': None,
    'status': 'stopped',
    'daily_pnl_pct': 0.0,
    'broker_error': None,      # último error de Alpaca (bilingüe) para diagnóstico
    'pending_close': {},       # símbolo (sin '/') → ts del último cierre enviado
    'signals': {},             # «1 toque» (modo manual): id → señal propuesta que una PERSONA aprueba con su PIN
}
_AGENT_LOCK = threading.Lock()          # arranque/parada/config
_AGENT_LOG_LOCK = threading.Lock()
_AGENT_LOG_MAX = 100
_AGENT_PENDING_CLOSE_S = 1800           # no reenviar un stop-loss en 30 min
_AGENT_BOUNDS = {                        # clave → (mínimo, máximo, tipo)
    'max_pos_pct': (0.5, 10.0, float),
    'max_daily_loss_pct': (0.5, 5.0, float),
    'stop_loss_pct': (0.5, 20.0, float),
    'min_confidence': (50, 100, int),
    'max_orders_per_cycle': (1, 5, int),
    'interval_min': (5, 1440, int),
}
_AGENT_MODES = ('manual', 'auto')
# Acciones de EE.UU. operables en Alpaca: 1-5 letras + clase opcional (BRK.B).
# Deja fuera sufijos de bolsas extranjeras del grafo (8411.T, SAP.DE, 0700.HK…).
_AGENT_SYM_RE = re.compile(r'^[A-Z]{1,5}(\.[A-C])?$')
_TRADABLE_CACHE: dict = {}
_AGENT_CFG_KEYS = ('mode', 'interval_min', 'max_pos_pct', 'max_daily_loss_pct', 'stop_loss_pct',
                   'min_confidence', 'max_orders_per_cycle', 'universe')


class _AgentOrderError(RuntimeError):
    """Alpaca no aceptó la orden (o no respondió): NO cuenta como ejecutada."""


def _agent_log(entry):
    entry.setdefault('ts', time.strftime('%H:%M:%S'))
    with _AGENT_LOG_LOCK:
        _AGENT['log'].append(entry)
        if len(_AGENT['log']) > _AGENT_LOG_MAX:
            _AGENT['log'] = _AGENT['log'][-_AGENT_LOG_MAX:]


def _agent_universe(raw):
    """→ (símbolos operables, descartados). None si `raw` no es una lista."""
    if not isinstance(raw, (list, tuple)):
        return None, []
    ok, skipped = [], []
    for t in list(raw)[:60]:
        sym = _S._safe_ticker(t)
        if sym and _AGENT_SYM_RE.match(sym):
            if sym not in ok:
                ok.append(sym)
        else:
            skipped.append(str(t)[:16])
    return ok[:30], skipped


def _agent_parse(data):
    """Valida y ACOTA la configuración → (cambios, avisos, (error_es, error_en)|None)."""
    changes, notes = {}, []
    for k, (lo, hi, typ) in _AGENT_BOUNDS.items():
        if k not in data or data[k] is None or data[k] == '':
            continue
        try:
            v = float(data[k])
            if v != v or v in (float('inf'), float('-inf')):
                raise ValueError
        except (TypeError, ValueError):
            return None, None, (f'{k} debe ser numérico', f'{k} must be numeric')
        cv = min(hi, max(lo, v))
        cv = int(round(cv)) if typ is int else float(cv)
        if cv != v:
            notes.append(f'{k}: {data[k]} → {cv}')
        changes[k] = cv
    if data.get('mode') not in (None, ''):
        m = str(data['mode']).strip().lower()
        if m not in _AGENT_MODES:
            return None, None, ("mode debe ser 'manual' o 'auto'", "mode must be 'manual' or 'auto'")
        changes['mode'] = m
    if data.get('universe') not in (None, [], ''):
        uni, skipped = _agent_universe(data['universe'])
        if uni is None:
            return None, None, ('universe debe ser una lista de tickers', 'universe must be a list of tickers')
        if not uni:
            return None, None, ('Ningún ticker del universo es una acción de EE.UU. operable en Alpaca',
                                'No ticker in the universe is a US stock tradable on Alpaca')
        changes['universe'] = uni
        if skipped:
            notes.append('descartados (no operables en Alpaca) · skipped (not tradable on Alpaca): '
                         + ', '.join(skipped[:12]) + ('…' if len(skipped) > 12 else ''))
    return changes, notes, None


def _agent_config_view():
    return {k: _AGENT[k] for k in _AGENT_CFG_KEYS}


def _auto_live_refused():
    log.warning('agente de trading: modo AUTO rechazado — la cuenta de Alpaca es de DINERO REAL')
    _S._trade_audit('agent_config', {'outcome': 'rejected', 'reason': 'auto_live_refused'})
    return _S._bad('El modo AUTO (órdenes sin tu aprobación una a una) solo se permite en la cuenta de PAPEL. '
                'Con dinero real usa el modo manual (consejos) y opera tú.',
                'AUTO mode (orders without your one-by-one approval) is only allowed on the PAPER account. '
                'With real money use manual mode (advice) and place orders yourself.',
                code='auto_live_refused', status=403)


def _agent_exec_block(account=None):
    """None si el agente puede enviar órdenes ahora; si no, el motivo (bilingüe).
    `account` (/v2/account): si su account_number no es de papel ('PA…') se
    bloquea aunque la URL parezca de papel."""
    if not _S._house_trading_enabled():
        return ('Interruptor general APAGADO (BROKERAGE_TRADING_ENABLED=off) · '
                'Master switch OFF (BROKERAGE_TRADING_ENABLED=off)')
    if not _S._paper() or _S._account_is_live(account) is True:
        return 'Cuenta de DINERO REAL: el modo auto no envía órdenes · REAL-MONEY account: auto mode sends no orders'
    return None


def _agent_analyze(ticker: str, price: float, prev: float, sentiment: float, facts=None) -> dict:
    """Ask Claude to analyze one ticker and recommend action. `facts` = contexto de Khipus (_agent_context:
    técnico de cierres reales + convicción de los analistas); sin él, solo precio y tono como antes."""
    pct = ((price - prev) / prev * 100) if prev else 0
    extra = ''.join(f'- {line}\n' for line in (facts or {}).get('lines') or [])
    prompt = (
        f"You are a quantitative trading analyst. Analyze {ticker}:\n"
        f"- Price: ${price:.2f} (prev close: ${prev:.2f}, change: {pct:+.2f}%)\n"
        f"- News sentiment score: {sentiment:.2f} (range -10 to +10)\n"
        f"{extra}\n"
        f"Weigh trend, momentum and the analysts' view; when signals conflict prefer hold. "
        f"Respond in JSON only, no markdown:\n"
        f'{{ "action": "buy"|"sell"|"hold", "confidence": 0-100, '
        f'"reason": "1-sentence reason", "size_pct": 1-5 }}'
    )
    try:
        # Ruta a través de la cascada multi-proveedor (Sonnet 5 con pensamiento
        # desactivado → respuesta inmediata; _extract_json tolera fences/prosa).
        text, _model = _S._ai_complete(
            'You are a quantitative trading analyst. Respond with a JSON object ONLY, no markdown.',
            prompt, max_tokens=250, tier='fast')
        out = _S._extract_json(text)
        if isinstance(out, dict):
            out['_model'] = _model          # paso 16: el modelo real queda en la decisión trade.agent_signal
            return out
        return {'action': 'hold', 'confidence': 0, 'reason': 'respuesta no-JSON', 'size_pct': 0}
    except Exception as e:  # noqa: BLE001
        return {'action': 'hold', 'confidence': 0, 'reason': _S._diag_redact(e)[:80], 'size_pct': 0}


def _agent_clean_analysis(a):
    """La IA puede devolver cualquier cosa: se normaliza sin reventar el ciclo."""
    a = a if isinstance(a, dict) else {}
    action = str(a.get('action') or 'hold').strip().lower()
    if action not in ('buy', 'sell', 'hold'):
        action = 'hold'
    try:
        confidence = int(float(a.get('confidence') or 0))
    except (TypeError, ValueError):
        confidence = 0
    try:
        size_pct = float(a.get('size_pct') or 0)
        if size_pct != size_pct:
            size_pct = 0.0
    except (TypeError, ValueError):
        size_pct = 0.0
    return action, max(0, min(100, confidence)), str(a.get('reason') or '')[:200], \
        max(0.0, min(size_pct, float(_AGENT['max_pos_pct'])))


def _agent_get_positions() -> dict:
    if not _S.ALPACA_KEY:
        return {}
    try:
        r = requests.get(f'{_S.ALPACA_BASE}/v2/positions', headers=_S._alpaca_hdrs(), timeout=10)
        if r.status_code == 200:
            return {p['symbol']: p for p in r.json()}
    except Exception:  # noqa: BLE001
        pass
    return {}


def _agent_open_order_symbols():
    """{símbolo sin '/': {lados}} de las órdenes ABIERTAS en Alpaca; None si no
    se pudo leer. El LADO importa: una compra límite abierta (p. ej. 'comprar
    la caída' GTC) NO es un cierre pendiente de una posición larga — antes
    cualquier orden abierta del símbolo apagaba el stop-loss."""
    try:
        r = requests.get(f'{_S.ALPACA_BASE}/v2/orders', params={'status': 'open', 'limit': 500},
                         headers=_S._alpaca_hdrs(), timeout=10)
        if r.status_code != 200:
            return None
        out = {}
        for o in (r.json() or []):
            if not isinstance(o, dict):
                continue
            sym = str(o.get('symbol') or '').replace('/', '').upper()
            out.setdefault(sym, set()).add(str(o.get('side') or '').strip().lower())
        return out
    except Exception:  # noqa: BLE001
        return None


def _agent_get_account() -> dict:
    if not _S.ALPACA_KEY:
        _AGENT['broker_error'] = 'ALPACA_KEY sin configurar · ALPACA_KEY not configured'
        return {}
    try:
        r = requests.get(f'{_S.ALPACA_BASE}/v2/account', headers=_S._alpaca_hdrs(), timeout=10)
        if r.status_code == 200:
            _AGENT['broker_error'] = None
            return r.json() or {}
        # Guardamos el status y un extracto del cuerpo para depurar (p.ej. 404 por
        # base mal configurada, 401/403 por claves inválidas).
        _AGENT['broker_error'] = f'Alpaca /v2/account HTTP {r.status_code}: {(r.text or "")[:120]}'
    except Exception as e:  # noqa: BLE001
        _AGENT['broker_error'] = f'Alpaca /v2/account: {_S._diag_redact(e)[:120]}'
    return {}


def _alpaca_tradable(sym):
    """¿Alpaca opera este símbolo? Caché 24 h. Si no se puede verificar → True
    (que Alpaca decida; su rechazo queda registrado como ERROR)."""
    e = _TRADABLE_CACHE.get(sym)
    if e and time.time() - e[0] < 86400:
        return e[1]
    try:
        from urllib.parse import quote as _q
        r = requests.get(f'{_S.ALPACA_BASE}/v2/assets/{_q(sym, safe="")}', headers=_S._alpaca_hdrs(), timeout=8)
        if r.status_code == 404:
            ok = False
        elif r.status_code == 200:
            a = r.json() or {}
            ok = bool(a.get('tradable')) and str(a.get('status') or 'active') == 'active'
        else:
            return True
    except Exception:  # noqa: BLE001
        return True
    _TRADABLE_CACHE[sym] = (time.time(), ok)
    return ok


# ── Contexto de Khipus para cada decisión (2026-10-20, «perfecciona el trading») ─────────────────────────────────
# Antes la IA veía solo precio de hoy + tono de noticias. Ahora también: técnico de CIERRES REALES de un año
# (core/risk_report.fetch_history → research/analytics.technical_indicators: RSI de Wilder, medias 50/200, retorno
# 1 mes, volatilidad 20 días, distancia al máximo) y la convicción de los analistas de Khipus (pizarra del comité).
# Caché 30 min por ticker: el ciclo no se vuelve lento ni gasta más pedidos.
_CTX_TTL_S = 1800
_CTX_CACHE: dict = {}
_BOARD_CACHE = {'ts': 0.0, 'by_sym': {}}
_TONE_CACHE: dict = {}
RSI_OVERBOUGHT = 75.0          # guarda: no se propone COMPRAR algo en sobrecompra extrema


def _agent_board_by_symbol():
    if time.time() - _BOARD_CACHE['ts'] < 600:
        return _BOARD_CACHE['by_sym']
    out = {}
    try:
        from ontology.db import ontology_available, session_scope
        if ontology_available():
            from core.semantic import _load_snapshot
            from research.committee import board
            snap = _load_snapshot()
            with session_scope() as s:
                items = board(s, limit=120).get('items') or []
            for x in items:
                n = snap['by_id'].get(x.get('entity_id')) or {}
                sym = str(n.get('mkt') or '').upper()
                if sym and x.get('overall_conviction') is not None:
                    out[sym] = {'conviction': x['overall_conviction'], 'label': x.get('label')}
    except Exception as e:  # noqa: BLE001
        log.info('agente: pizarra no disponible (%s)', type(e).__name__)
    _BOARD_CACHE.update(ts=time.time(), by_sym=out)
    return out


def _agent_context(ticker):
    """→ {'tech': {...}|None, 'conviction': float|None, 'lines': [texto para la IA]}. Nunca lanza."""
    e = _CTX_CACHE.get(ticker)
    if e and time.time() - e[0] < _CTX_TTL_S:
        return e[1]
    tech = None
    try:
        from core.risk_report import fetch_history
        from research.analytics import technical_indicators
        hist, _cur = fetch_history(ticker, '1y')
        series = sorted(hist.items()) if isinstance(hist, dict) else []
        tech, _txt = technical_indicators(series)
    except Exception as e:  # noqa: BLE001
        log.info('agente: técnico de %s no disponible (%s)', ticker, type(e).__name__)
    conv = (_agent_board_by_symbol().get(ticker) or {}).get('conviction')
    lines = []
    if tech:
        if tech.get('rsi14') is not None:
            lines.append(f"RSI(14, Wilder): {tech['rsi14']}")
        if tech.get('trend'):
            tr = {'alcista': 'up', 'bajista': 'down', 'mixta': 'mixed'}.get(tech['trend'], tech['trend'])
            lines.append(f"Trend (50/200-day averages): {tr}")
        if tech.get('ret_1m_pct') is not None:
            lines.append(f"1-month return: {tech['ret_1m_pct']}%")
        if tech.get('vol_20d_pct') is not None:
            lines.append(f"20-day annualized volatility: {tech['vol_20d_pct']}%")
        if tech.get('pct_from_52w_high') is not None:
            lines.append(f"Distance from 52-week high: {tech['pct_from_52w_high']}%")
    if conv is not None:
        lines.append(f"Khipus analysts' conviction: {conv:+.0f} (range -100 to +100)")
    out = {'tech': tech, 'conviction': conv, 'lines': lines}
    _CTX_CACHE[ticker] = (time.time(), out)
    return out


def _agent_guard(action, facts):
    """Regla FIJA sobre lo que diga la IA: motivo para no actuar, o None."""
    rsi = ((facts or {}).get('tech') or {}).get('rsi14')
    if action == 'buy' and rsi is not None and rsi >= RSI_OVERBOUGHT:
        return f'RSI {rsi} ≥ {RSI_OVERBOUGHT:.0f}: sobrecompra, no se compra · overbought, no buy'
    conv = (facts or {}).get('conviction')
    if action == 'buy' and conv is not None and conv <= -35:
        return f'analistas en contra (convicción {conv:+.0f}) · analysts against'
    return None


def _agent_tone(ticker):
    """Tono de noticias GDELT con caché de 30 min (antes un pedido de hasta 6 s por ticker en CADA ciclo)."""
    e = _TONE_CACHE.get(ticker)
    if e and time.time() - e[0] < _CTX_TTL_S:
        return e[1]
    tone = 0.0
    try:
        gr = requests.get('https://api.gdeltproject.org/api/v2/doc/doc',
                          params={'query': ticker, 'mode': 'tonechart', 'format': 'json', 'maxrecords': 5},
                          timeout=6)
        gdata = gr.json()
        tones = [float(x.get('avgtone', 0) or 0) for x in (gdata.get('tonechart') or [])[:5]]
        tone = sum(tones) / len(tones) if tones else 0.0
    except Exception:  # noqa: BLE001
        pass
    _TONE_CACHE[ticker] = (time.time(), tone)
    return tone


# ── «1 TOQUE» (2026-10-20): en modo MANUAL cada señal accionable queda PROPUESTA con todo listo (lado, monto, precio
# visto, stop, motivo, confianza). Una PERSONA la aprueba con su PIN (POST /api/trade/agent/signals/<id>/take) y sale
# por EL camino único (brokerage.service.house_order, source='ui', igual que el panel). Vence a los 15 min y se
# rechaza si el precio se movió más de 1,5 % en contra (salvo una salida por stop-loss: proteger nunca se frena).
SIGNAL_TTL_S = 15 * 60
SIGNAL_DRIFT_PCT = 1.5
_SIGNALS_MAX = 40
_SIGNALS_LOCK = threading.Lock()


def _signals_prune(now=None):
    now = now or time.time()
    sig = _AGENT.setdefault('signals', {})
    for k, v in list(sig.items()):
        if v['status'] == 'pending' and now > v['expires_ts']:
            v['status'] = 'expired'
        if now - v['ts'] > 6 * 3600:
            sig.pop(k, None)
    while len(sig) > _SIGNALS_MAX:
        sig.pop(next(iter(sig)))


def _signal_add(ticker, side, *, notional=None, qty=None, price=0.0, confidence=0, reason='', kind='entry',
                decision_id=None, facts=None):
    """Propone una señal (una pendiente por símbolo y lado: la nueva reemplaza a la vieja). → la señal."""
    now = time.time()
    with _SIGNALS_LOCK:
        _signals_prune(now)
        sig = _AGENT.setdefault('signals', {})
        for v in sig.values():
            if v['status'] == 'pending' and v['ticker'] == ticker and v['side'] == side:
                v['status'] = 'replaced'
        sid = uuid.uuid4().hex[:16]
        tech = (facts or {}).get('tech') or {}
        sig[sid] = {
            'id': sid, 'ts': now, 'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now)),
            'expires_ts': now + SIGNAL_TTL_S,
            'expires_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now + SIGNAL_TTL_S)),
            'ticker': ticker, 'side': side, 'kind': kind,
            'notional': round(float(notional), 2) if notional else None,
            'qty': qty, 'price': round(float(price or 0), 4), 'price_src': 'finnhub',
            'stop_loss_pct': _AGENT['stop_loss_pct'], 'confidence': int(confidence or 0), 'reason': str(reason)[:200],
            'rsi14': tech.get('rsi14'), 'trend': tech.get('trend'), 'conviction': (facts or {}).get('conviction'),
            'decision_id': decision_id, 'status': 'pending', 'paper': bool(_S._paper()),
        }
        return sig[sid]


def _signals_view():
    with _SIGNALS_LOCK:
        _signals_prune()
        items = sorted(_AGENT.get('signals', {}).values(), key=lambda v: -v['ts'])
    return [{k: v for k, v in x.items() if k not in ('ts', 'expires_ts')} for x in items]


def _agent_principal():
    """QUIÉN actúa en el hilo del agente: system:trading_agent (paso 5); fuera del hilo (pruebas) el mismo."""
    from core import identity
    cur = identity.current()
    return cur if cur is not None and cur.id.startswith('system:') else identity.system('trading_agent')


def _agent_signal_ctx(ticker, action, info):
    """trade.agent_signal (INFRA_OPERATIVA paso 16): lo que el agente decidió y POR QUÉ (precio que vio, tono de
    noticias, confianza, razón de la IA y su modelo, configuración vigente), escrito ANTES de actuar. Su hija es la
    order.preview de la orden (si la hubo). Sin base → None (no hay libro)."""
    try:
        from ontology.db import ontology_available
        if not ontology_available():
            return None
        from core import decisions
        ctx = decisions.DecisionCtx('trade.agent_signal', _agent_principal(),
                                    subject={'symbol': ticker, 'action': action, 'mode': _AGENT.get('mode')})
        if info.get('price'):
            ctx.quote({'ticker': ticker, 'px': info['price'], 'prev': info.get('prev'),
                       'src': info.get('price_src') or 'finnhub', 'currency': 'USD',
                       'as_of': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
        if info.get('model'):
            ctx.model = {'model': str(info['model'])[:80], 'agent': 'trading_agent'}
        ctx.extra['agent_config'] = {k: v for k, v in _agent_config_view().items() if k != 'universe'}
        ctx.output = {k: info.get(k) for k in ('action', 'confidence', 'reason', 'size_pct', 'sentiment', 'price',
                                               'notional', 'skipped', 'stop_loss_pl_pct') if info.get(k) is not None}
        return ctx
    except Exception as e:  # noqa: BLE001
        log.warning('agente: señal no preparada (%s)', type(e).__name__)
        return None


def _agent_record_signal(ctx, status):
    """Señal SIN orden (consejo en modo manual, o una orden que el agente decidió no enviar): su propia transacción.
    Nunca rompe el ciclo."""
    if ctx is None:
        return None
    try:
        from core import decisions
        from ontology.db import session_scope
        with session_scope() as s:
            return decisions.record(s, ctx, status=status)
    except Exception as e:  # noqa: BLE001
        log.warning('agente: señal no registrada en el libro (%s)', type(e).__name__)
        return None


def _agent_order(order, action, detail, signal=None, checks_mode='house_today'):
    """La orden del agente por EL camino único (brokerage.service.house_order, source='agent'): mismos controles,
    client_order_id, broker_audit y decisiones (trade.agent_signal → order.preview → order.confirm → order.submit).
    En papel no espera a nadie (el agente en AUTO lo encendió Fabrizio con su PIN); con dinero real quedaría
    pendiente de aprobación (y AUTO ya está prohibido en real). → payload (id, status…) o _AgentOrderError."""
    from brokerage import service as _bsvc
    from core import identity
    from ontology.db import ontology_available
    coid = 'kh-agent-' + uuid.uuid4().hex[:24]
    detail = dict(detail, client_order_id=coid, tif=order.get('time_in_force'))
    kw = dict(notional=order.get('notional'), qty=order.get('qty'), order_type='market',
              time_in_force=order.get('time_in_force'), client_order_id=coid, source='agent', channel='agent',
              requested_by='agente-trading', checks_mode=checks_mode,
              rationale=(signal.output.get('reason') if signal is not None and signal.output else None))
    _bsvc.send_trace_begin()
    try:
        with identity.use(_agent_principal()):
            if ontology_available():
                from core import decisions
                from ontology.db import session_scope
                with session_scope() as s:
                    sig_id = None
                    if signal is not None:          # la señal ANTES de la orden (misma transacción)
                        decisions.record(s, signal, status='executed')
                        sig_id = signal.id
                    res = _bsvc.house_order(s, order['symbol'], order['side'], parent_decision_id=sig_id, **kw)
            else:
                res = _bsvc.house_order(None, order['symbol'], order['side'], **kw)
    except Exception as e:  # noqa: BLE001 — base/libro caídos (D4: falla cerrado)
        sent = _bsvc.send_trace()
        _S._trade_audit(action, dict(detail, outcome='unknown_error', error=type(e).__name__,
                                  sent_to_broker=bool(sent)), actor='agente-trading')
        if sent:   # revisión batch E: salió hacia Alpaca y no se pudo guardar → DESCONOCIDA, nunca «nada salió»
            _bsvc.record_unknown_after_send(sent, 'agente-trading', type(e).__name__, source='agent')
            err = _AgentOrderError(f'orden enviada con estado DESCONOCIDO (no se pudo guardar) · order sent, state '
                                   f'UNKNOWN (could not be saved) ({type(e).__name__})')
            err.unknown = True
            _AGENT.setdefault('unknown_orders', {})[str(order.get('symbol') or '').replace('/', '').upper()] = \
                time.time()
            raise err from e
        raise _AgentOrderError(f'no se pudo procesar la orden · the order could not be processed '
                               f'({type(e).__name__})') from e
    payload, st = _S._house_http(res)
    ok = st == 200 and bool(payload.get('id'))
    _S._trade_audit(action, dict(detail, outcome='submitted' if ok else ('pending_approval' if st == 202 else 'rejected'),
                              http_status=st, code=None if ok else payload.get('code'),
                              alpaca_order_id=payload.get('id') if ok else None,
                              alpaca_status=payload.get('status') if ok else None,
                              alpaca_message=None if ok else (str(payload.get('error') or '')[:140] or None),
                              preview_id=payload.get('preview_id'), decision_id=payload.get('decision_id')),
                 actor='agente-trading')
    if not ok:
        raise _AgentOrderError(f"{payload.get('error') or 'orden no enviada'} · "
                               f"{payload.get('error_en') or 'order not sent'}"[:300])
    return payload


def _agent_place(ticker: str, side: str, notional: float, signal=None) -> dict:
    """Orden market por monto (USD). Lanza _AgentOrderError si no se envió."""
    return _agent_order({'symbol': ticker, 'side': side, 'notional': round(float(notional), 2),
                         'time_in_force': 'gtc' if '/' in ticker else 'day'},     # cripto: Alpaca exige gtc/ioc
                        'agent_order', {'symbol': ticker, 'side': side, 'notional': round(notional, 2)}, signal)


def _agent_stop_losses(positions, block):
    """Cierra las posiciones que superan el stop. Devuelve los símbolos tocados
    (no se vuelve a operar sobre ellos en este ciclo)."""
    touched = set()
    now = time.time()
    pend = _AGENT.setdefault('pending_close', {})
    for k in [k for k, ts in pend.items() if now - ts > _AGENT_PENDING_CLOSE_S]:
        pend.pop(k, None)
    open_syms = None
    for sym, p in list(positions.items()):
        try:
            pl_pct = float(p.get('unrealized_plpc') or 0) * 100
            qty = float(p.get('qty') or 0)
        except (TypeError, ValueError):
            continue
        if not qty or pl_pct > -_AGENT['stop_loss_pct']:
            continue
        key = str(sym).replace('/', '').upper()
        close_side = 'sell' if qty > 0 else 'buy'
        touched.add(sym)
        if block:
            _agent_log({'ticker': sym, 'level': 'warn',
                        'msg': f'🛑 Stop-loss {pl_pct:.1f}% NO enviado · NOT sent — {block}'})
            continue
        if open_syms is None:
            open_syms = _agent_open_order_symbols()
        # Solo cuenta como "cierre pendiente" una orden abierta del lado que CIERRA
        # (venta si es larga, compra si es corta); una del otro lado no apaga el stop.
        if key in pend or (open_syms is not None and close_side in open_syms.get(key, ())):
            _agent_log({'ticker': sym, 'level': 'info',
                        'msg': '⏳ Stop-loss: ya hay un cierre pendiente — no se reenvía · close already pending'})
            continue
        is_crypto = str(p.get('asset_class') or '') == 'crypto' or '/' in str(sym)
        from brokerage.service import crypto_pair as _crypto_pair
        order = {'symbol': _crypto_pair(sym) if is_crypto else str(sym).upper(), 'qty': float(_S._num_str(abs(qty))),
                 'side': close_side, 'time_in_force': 'gtc' if is_crypto else 'day'}
        sig = _agent_signal_ctx(str(sym), close_side, {'action': close_side, 'stop_loss_pl_pct': round(pl_pct, 2),
                                                       'reason': f'stop-loss {pl_pct:.1f}% '
                                                                 f'(≤ -{_AGENT["stop_loss_pct"]}%)'})
        try:
            res = _agent_order(order, 'agent_stop_loss', {'symbol': sym, 'side': close_side,
                                                          'qty': _S._num_str(abs(qty)), 'pl_pct': round(pl_pct, 2)},
                               sig, checks_mode='house_reduce')   # salida: nunca frenada por el tope por orden
            pend[key] = now
            _agent_log({'ticker': sym, 'level': 'warn', 'order_id': str(res.get('id') or '')[:12],
                        'msg': f'🛑 Stop-loss {pl_pct:.1f}% — orden de cierre enviada · close order sent '
                               f'({res.get("status") or "accepted"})'})
        except Exception as e:  # noqa: BLE001
            if getattr(e, 'unknown', False):
                pend[key] = now        # quizá ya salió: no reenviar otro cierre (podría abrir un corto)
            _agent_log({'ticker': sym, 'level': 'error',
                        'msg': f'Stop-loss error: {_S._diag_redact(e)[:160]}'})
    return touched


def _agent_stop_signals(positions):
    """Modo manual: una posición que pasó el stop NO se cierra sola; queda una señal de SALIDA (vender todo) para
    aprobar con un toque. Devuelve los símbolos tocados (no se les propone otra cosa en este ciclo)."""
    touched = set()
    for sym, p in list(positions.items()):
        try:
            pl_pct = float(p.get('unrealized_plpc') or 0) * 100
            qty = float(p.get('qty') or 0)
            px = float(p.get('current_price') or 0)
        except (TypeError, ValueError):
            continue
        if not qty or pl_pct > -_AGENT['stop_loss_pct']:
            continue
        touched.add(sym)
        side = 'sell' if qty > 0 else 'buy'
        pend = [v for v in _AGENT.get('signals', {}).values()
                if v['status'] == 'pending' and v['ticker'] == sym and v['kind'] == 'stop']
        if pend:
            continue
        _signal_add(str(sym), side, qty=float(_S._num_str(abs(qty))), price=px, confidence=100, kind='stop',
                    reason=f'stop-loss {pl_pct:.1f}% (≤ -{_AGENT["stop_loss_pct"]}%)')
        _agent_log({'ticker': sym, 'level': 'warn',
                    'msg': f'🛑 Stop-loss {pl_pct:.1f}%: señal de salida lista para aprobar · exit signal ready'})
    return touched


def _agent_run_cycle():
    """One analysis + execution cycle for all tickers in universe."""
    account = _agent_get_account()
    equity = float(account.get('equity', 0) or 0)
    if equity <= 0 and _S.ALPACA_KEY:
        be = _AGENT.get('broker_error') or 'Alpaca no devolvió capital · Alpaca returned no equity'
        _agent_log({'level': 'warn',
                    'msg': f'⚠️ No se pudo leer el capital de Alpaca · Could not read Alpaca equity — {be}'})
        return

    # P&L real del día desde Alpaca (equity vs cierre de ayer) — sin esto el
    # circuit-breaker de abajo nunca puede saltar
    last_equity = float(account.get('last_equity', 0) or 0)
    if last_equity > 0:
        _AGENT['daily_pnl_pct'] = (equity - last_equity) / last_equity * 100

    # Circuit-breaker diario: bloquea ENTRADAS NUEVAS pero NUNCA la protección
    # de salida (auditoría Track D 2026-08-01).
    breaker_on = _AGENT['daily_pnl_pct'] <= -_AGENT['max_daily_loss_pct']
    if breaker_on:
        _agent_log({'level': 'warn',
                    'msg': f'🛑 Daily loss limit hit ({_AGENT["daily_pnl_pct"]:.2f}%) — sin entradas nuevas; stop-loss sigue activo'})

    auto = _AGENT['mode'] == 'auto'
    block = _agent_exec_block(account) if auto else None
    if block:
        _agent_log({'level': 'warn', 'msg': f'⏸ Órdenes en pausa · Orders paused — {block}'})

    positions = _agent_get_positions()
    stopped = _agent_stop_losses(positions, block) if auto else _agent_stop_signals(positions)
    for sym in stopped:
        positions.pop(sym, None)

    # Con el breaker activo (o las órdenes en pausa) y en modo auto no hay nada
    # que ejecutar: ahorramos además el costo de analizar 10-30 tickers con IA.
    # En modo manual (solo consejos) se sigue analizando — el log asesor no
    # abre posiciones.
    if auto and (breaker_on or block):
        _AGENT['last_run'] = time.strftime('%Y-%m-%d %H:%M:%S')
        return

    universe, _skipped = _agent_universe(_AGENT['universe'])
    orders_this_cycle = 0
    _AGENT['last_start'] = time.strftime('%Y-%m-%d %H:%M:%S')
    _t0 = time.time()
    _agent_log({'level': 'info', 'msg': f'🔎 Revisando {len(universe or [])} acciones · Checking {len(universe or [])} stocks'})
    live = {}          # respaldo: la MISMA cascada de precios de la app (Finnhub → Yahoo), pedida una vez por ciclo
    no_price, seen = [], 0
    for ticker in universe or []:
        if not _AGENT['running']:
            break
        price, prev, sentiment = 0.0, 0.0, 0.0
        price_src = 'finnhub'
        if _S.FINNHUB:
            data, err = _S._fetch_quote_raw(ticker, timeout=8)
            if not err and isinstance(data, dict):
                try:
                    price = float(data.get('c') or 0)
                    prev = float(data.get('pc') or 0)
                except (TypeError, ValueError):
                    price = 0.0
        if price <= 0:
            # 2026-10-21 («no empieza el agente»): sin Finnhub (sin clave o con su límite agotado) el agente saltaba
            # TODAS las acciones sin decir nada. Ahora prueba la cascada de la app y, si tampoco hay precio, lo anota.
            if not live:
                try:
                    from core.quotes import fetch_quotes_live
                    live = (fetch_quotes_live(list(universe or [])) or {}).get('quotes') or {'_': None}
                except Exception as e:  # noqa: BLE001
                    log.info('agente: cascada de precios no disponible (%s)', type(e).__name__)
                    live = {'_': None}
            q = live.get(ticker) or {}
            try:
                price = float(q.get('live') or q.get('close') or 0)
                prev = float(q.get('prev') or 0)
                price_src = q.get('src') or 'yahoo'
            except (TypeError, ValueError):
                price = 0.0
        if price <= 0:
            no_price.append(ticker)
            continue
        seen += 1
        # progreso visible: antes el panel callaba hasta terminar el primer ticker (noticias + técnico + IA pueden tardar)
        _agent_log({'level': 'info', 'msg': f'⏳ {ticker} ({seen}/{len(universe or [])}): analizando… · analyzing…'})
        sentiment = _agent_tone(ticker)          # tono de noticias (GDELT, caché 30 min)
        facts = _agent_context(ticker)           # técnico de cierres reales + convicción de los analistas

        _raw = _agent_analyze(ticker, price, prev, sentiment, facts=facts)
        action, confidence, reason, size_pct = _agent_clean_analysis(_raw)
        guard = _agent_guard(action, facts)
        sig = (_agent_signal_ctx(ticker, action, {'action': action, 'confidence': confidence, 'reason': reason,
                                                  'size_pct': size_pct, 'sentiment': round(sentiment, 3),
                                                  'price': price, 'prev': prev, 'price_src': price_src,
                                                  'model': (_raw or {}).get('_model') if isinstance(_raw, dict)
                                                  else None})
               if action != 'hold' else None)
        entry = {
            'ts': time.strftime('%H:%M:%S'),
            'ticker': ticker,
            'price': price,
            'action': action,
            'confidence': confidence,
            'reason': reason,
            'executed': False,
            'level': 'info',
        }

        if guard and action != 'hold' and confidence >= _AGENT.get('min_confidence', 65):
            entry['skipped'] = guard
            if sig is not None:
                sig.output['skipped'] = guard
                _agent_record_signal(sig, 'noop')
        elif auto and _S.ALPACA_KEY and action != 'hold' and confidence >= _AGENT.get('min_confidence', 65):
            # Endurecimientos (auditoría Track D): freno duro de órdenes por
            # ciclo, no acumular por encima del tope en el mismo ticker, y no
            # vender sin tenencia (evita shorts no intencionados con margen).
            existing = positions.get(ticker) or {}
            try:
                existing_mv = abs(float(existing.get('market_value') or 0))
            except (TypeError, ValueError):
                existing_mv = 0.0
            skip = None
            if block:
                skip = block
            elif ticker in stopped:
                skip = 'stop-loss en este ciclo · stop-loss this cycle'
            elif time.time() - (_AGENT.get('unknown_orders') or {}).get(ticker.replace('/', '').upper(), 0) < \
                    _AGENT_PENDING_CLOSE_S:
                skip = 'orden anterior en estado desconocido · previous order in unknown state'
            elif orders_this_cycle >= _AGENT.get('max_orders_per_cycle', 3):
                skip = 'freno: tope de órdenes por ciclo'
            elif size_pct <= 0:
                skip = 'tamaño 0 · size 0'
            elif action == 'buy' and equity > 0 and existing_mv >= equity * _AGENT['max_pos_pct'] / 100:
                skip = f'posición ya en tope ({existing_mv / equity * 100:.1f}% ≥ {_AGENT["max_pos_pct"]}%)'
            elif action == 'sell' and not existing:
                skip = 'sin tenencia — no se abre corto'
            elif not _alpaca_tradable(ticker):
                skip = 'no operable en Alpaca · not tradable on Alpaca'
            if skip:
                entry['skipped'] = skip
                if sig is not None:
                    sig.output['skipped'] = skip
                    _agent_record_signal(sig, 'noop')
            else:
                notional = equity * size_pct / 100
                notional = max(1.0, min(notional, equity * _AGENT['max_pos_pct'] / 100, _S.MAX_ORDER_USD))
                if action == 'buy' and equity > 0:
                    # que la orden no empuje la posición total por encima del tope
                    room = equity * _AGENT['max_pos_pct'] / 100 - existing_mv
                    notional = min(notional, max(1.0, room))
                if sig is not None:
                    sig.output['notional'] = round(notional, 2)
                try:
                    result = _agent_place(ticker, action, notional, sig)
                    entry['executed'] = True
                    entry['order_id'] = str(result.get('id') or '')[:12]
                    entry['order_status'] = result.get('status')
                    entry['notional'] = round(notional, 2)
                    entry['level'] = 'success'
                    orders_this_cycle += 1
                except Exception as e:  # noqa: BLE001 — rechazo de Alpaca o red: ERROR, no ejecutada
                    entry['exec_error'] = _S._diag_redact(e)[:160]
                    entry['level'] = 'error'
        elif action != 'hold':         # consejo (modo manual) o señal por debajo del umbral: queda en el libro
            if sig is not None:
                sig.output['executed'] = False
            proposed = None
            if (not auto and _S.ALPACA_KEY and confidence >= _AGENT.get('min_confidence', 65)
                    and orders_this_cycle < _AGENT.get('max_orders_per_cycle', 3)):
                existing = positions.get(ticker) or {}
                try:
                    existing_mv = abs(float(existing.get('market_value') or 0))
                except (TypeError, ValueError):
                    existing_mv = 0.0
                if action == 'sell' and not existing:
                    entry['skipped'] = 'sin tenencia — no se abre corto'
                elif action == 'buy' and equity > 0 and existing_mv >= equity * _AGENT['max_pos_pct'] / 100:
                    entry['skipped'] = f'posición ya en tope ({existing_mv / equity * 100:.1f}%)'
                elif size_pct > 0 and equity > 0:
                    if action == 'sell':
                        try:
                            qty = abs(float(existing.get('qty') or 0))
                        except (TypeError, ValueError):
                            qty = 0.0
                        frac = min(1.0, (equity * size_pct / 100) / existing_mv) if existing_mv else 1.0
                        q = float(_S._num_str(qty * frac)) if qty else 0.0
                        proposed = {'qty': q} if q > 0 else None
                    else:
                        notional = max(1.0, min(equity * size_pct / 100, equity * _AGENT['max_pos_pct'] / 100,
                                                _S.MAX_ORDER_USD,
                                                max(1.0, equity * _AGENT['max_pos_pct'] / 100 - existing_mv)))
                        proposed = {'notional': notional}
            if proposed:
                if sig is not None:
                    sig.output['proposed'] = {k: (round(v, 2) if k == 'notional' else v) for k, v in proposed.items()}
                did = _agent_record_signal(sig, 'recorded')
                s1 = _signal_add(ticker, action, price=price, confidence=confidence, reason=reason,
                                 decision_id=did or getattr(sig, 'id', None), facts=facts,
                                 **proposed)
                entry['signal_id'] = s1['id']
                orders_this_cycle += 1
            else:
                _agent_record_signal(sig, 'recorded')

        _agent_log(entry)

    if no_price:
        _agent_log({'level': 'warn', 'msg': f'⚠ Sin precio ahora (ni Finnhub ni Yahoo): {", ".join(no_price)} · No price now'})
    _agent_log({'level': 'info', 'msg': f'✓ Revisión terminada: {seen} con precio, {orders_this_cycle} acción(es) '
                                        f'({time.time() - _t0:.0f} s) · Check done: {seen} priced, '
                                        f'{orders_this_cycle} action(s) ({time.time() - _t0:.0f} s)'})
    _AGENT['last_run'] = time.strftime('%Y-%m-%d %H:%M:%S')


def _agent_thread_fn():
    from core import identity as _identity
    _AGENT['status'] = 'running'
    _tok = _identity._CURRENT.set(_identity.system('trading_agent'))   # paso 5: el hilo actúa como system:…
    try:
        while _AGENT['running']:
            try:
                _agent_run_cycle()
            except Exception as e:  # noqa: BLE001
                _agent_log({'msg': f'Cycle error: {_S._diag_redact(e)}', 'level': 'error'})
            lo, hi, _t = _AGENT_BOUNDS['interval_min']
            interval = int(min(hi, max(lo, _AGENT['interval_min']))) * 60
            for _ in range(interval):
                if not _AGENT['running']:
                    break
                time.sleep(1)
    finally:
        _identity._CURRENT.reset(_tok)
        _AGENT['status'] = 'stopped'


# BRECHAS #14 (sin respuesta → lo recomendado): tras un despliegue el agente queda APAGADO con un aviso visible y SIN
# perder su configuración. Cada encendido/apagado/cambio es una decisión policy.change (subject.policy =
# trade.agent_config) en el libro append-only; la última se restaura al primer uso del panel del agente.
_AGENT_RESTORE = {'done': False}
_AGENT_NOTICE_ES = ('⏸ El agente quedó APAGADO tras una actualización de la app (no se reanuda solo). Tu configuración '
                    'se conservó: pulsa Iniciar para volver a encenderlo.')
_AGENT_NOTICE_EN = ('⏸ The agent was left OFF after an app update (it does not resume by itself). Your settings were '
                    'kept: press Start to turn it on again.')


def _agent_persist(running, reason, principal=None):
    """policy.change del agente: configuración + ¿debería estar corriendo? Nunca rompe la ruta (sin base: nada)."""
    try:
        from ontology.db import ontology_available
        if not ontology_available():
            return None
        from core import decisions, identity
        from ontology.db import session_scope
        p = principal
        if p is None:
            try:
                p = identity.principal_from_request()
            except Exception:  # noqa: BLE001
                p = _agent_principal()
        with session_scope() as s:
            with decisions.decision_scope('policy.change', p, session=s,
                                          subject={'policy': 'trade.agent_config'}) as ctx:
                ctx.output = {'config': _agent_config_view(), 'running': bool(running), 'reason': reason,
                              'paper': _S._paper()}
                ctx.status = 'executed'
        return str(ctx.id)
    except Exception as e:  # noqa: BLE001
        log.warning('agente: configuración no guardada en el libro (%s)', type(e).__name__)
        return None


def _agent_restore():
    """Una vez por proceso (= por despliegue): la última configuración del libro vuelve a _AGENT (acotada por
    _agent_parse); si el agente estaba corriendo, queda apagado con aviso y se anota el apagado (system)."""
    if _AGENT_RESTORE['done']:
        return
    try:
        from ontology.db import ontology_available
        if not ontology_available():
            _AGENT_RESTORE['done'] = True
            return
        from sqlalchemy import text
        from ontology.db import session_scope
        with session_scope() as s:
            row = s.execute(text(
                "SELECT output, recorded_at FROM decisions WHERE kind = 'policy.change' "
                "AND subject @> CAST(:sub AS jsonb) ORDER BY seq DESC LIMIT 1"),
                {'sub': json.dumps({'policy': 'trade.agent_config'})}).first()
        _AGENT_RESTORE['done'] = True
        if row is None or not isinstance(row[0], dict):
            return
        out = row[0]
        cfg = out.get('config') or {}
        changes, _notes, err = _agent_parse(cfg)
        with _AGENT_LOCK:
            if _AGENT['running']:            # ya lo encendieron en este proceso: manda lo de ahora
                return
            if not err and changes:
                if changes.get('mode') == 'auto' and not _S._paper():
                    changes['mode'] = 'manual'
                _AGENT.update(changes)
        if out.get('running'):
            _AGENT['notice'] = {'es': _AGENT_NOTICE_ES, 'en': _AGENT_NOTICE_EN,
                                'stopped_at': row[1].isoformat() if row[1] else None}
            _agent_log({'level': 'warn', 'msg': _AGENT_NOTICE_ES + ' · ' + _AGENT_NOTICE_EN})
            _agent_persist(False, 'stopped_by_restart', principal=_agent_principal())
    except Exception as e:  # noqa: BLE001 — base caída: se reintenta en el próximo uso
        log.warning('agente: no se restauró la configuración (%s)', type(e).__name__)


@trading_agent_bp.route('/api/trade/agent/start', methods=['POST'])
@rate_limit(limit=10, window=60)
@_trade_auth
def agent_start():
    if not _S.ALPACA_KEY:
        return _S._broker_missing_response()
    data, bad = _S._json_object_body()
    if bad:
        return bad
    changes, notes, err = _agent_parse(data)
    if err:
        return _S._bad(*err)
    if changes.get('mode', _AGENT['mode']) == 'auto' and not _S._paper():
        return _auto_live_refused()
    _agent_restore()
    with _AGENT_LOCK:
        _AGENT.update(changes)
        if _AGENT['running']:
            return jsonify({'status': 'already_running', 'mode': _AGENT['mode'], 'notes': notes,
                            'config': _agent_config_view()})
        prev_t = _AGENT.get('thread')
        if prev_t is not None and prev_t.is_alive():
            return _S._bad('El agente aún se está deteniendo; reintenta en unos segundos',
                        'The agent is still stopping; retry in a few seconds', code='agent_stopping', status=409)
        _AGENT['running'] = True
        _AGENT['daily_pnl_pct'] = 0.0
        _AGENT.pop('notice', None)
        t = threading.Thread(target=_agent_thread_fn, daemon=True, name='khipu-trading-agent')
        _AGENT['thread'] = t
        t.start()
    _agent_persist(True, 'start')
    _S._trade_audit('agent_start', {'outcome': 'started', **{k: v for k, v in _agent_config_view().items()
                                                          if k != 'universe'},
                                 'universe_n': len(_AGENT['universe'])})
    return jsonify({'status': 'started', 'mode': _AGENT['mode'], 'paper': _S._paper(), 'notes': notes,
                    'config': _agent_config_view()})


@trading_agent_bp.route('/api/trade/agent/stop', methods=['POST'])
@rate_limit(limit=20, window=60)
@_trade_auth
def agent_stop():
    _agent_restore()
    with _AGENT_LOCK:
        _AGENT['running'] = False
    _agent_persist(False, 'stop')
    _S._trade_audit('agent_stop', {'outcome': 'stopping'})
    return jsonify({'status': 'stopping'})


@trading_agent_bp.route('/api/trade/agent/status', methods=['GET'])
@rate_limit(limit=120, window=60)
@_trade_auth
def agent_status():
    _agent_restore()
    with _AGENT_LOG_LOCK:
        recent = list(_AGENT['log'][-20:])
    return jsonify({
        'running': _AGENT['running'],
        'status': _AGENT['status'],
        'mode': _AGENT['mode'],
        'interval_min': _AGENT['interval_min'],
        'universe': _AGENT['universe'],
        'max_pos_pct': _AGENT['max_pos_pct'],
        'max_daily_loss_pct': _AGENT['max_daily_loss_pct'],
        'stop_loss_pct': _AGENT['stop_loss_pct'],
        'min_confidence': _AGENT.get('min_confidence', 65),
        'max_orders_per_cycle': _AGENT.get('max_orders_per_cycle', 3),
        'paper': _S._paper(),
        'auto_allowed': _S._paper(),
        'trading_enabled': _S._house_trading_enabled(),
        'bounds': {k: [lo, hi] for k, (lo, hi, _t) in _AGENT_BOUNDS.items()},
        'last_run': _AGENT['last_run'],
        'daily_pnl_pct': _AGENT['daily_pnl_pct'],
        'broker_error': _AGENT.get('broker_error'),
        'notice': _AGENT.get('notice'),          # BRECHAS #14: apagado por una actualización (ES/EN)
        'log': recent,
        'signals': _signals_view(),
    })


@trading_agent_bp.route('/api/trade/agent/config', methods=['POST'])
@rate_limit(limit=20, window=60)
@_trade_auth
def agent_config():
    data, bad = _S._json_object_body()
    if bad:
        return bad
    changes, notes, err = _agent_parse(data)
    if err:
        return _S._bad(*err)
    if changes.get('mode', _AGENT['mode']) == 'auto' and not _S._paper():
        return _auto_live_refused()
    _agent_restore()
    with _AGENT_LOCK:
        _AGENT.update(changes)
    if changes:
        _agent_persist(_AGENT['running'], 'config')
        _S._trade_audit('agent_config', {'outcome': 'updated', **{k: v for k, v in changes.items() if k != 'universe'},
                                      **({'universe_n': len(changes['universe'])} if 'universe' in changes else {})})
    return jsonify({'status': 'updated', 'notes': notes, **_agent_config_view()})


# ── «1 toque»: señales del agente que aprueba una persona ─────────────────────────────────────────────────────────
@trading_agent_bp.route('/api/trade/agent/signals', methods=['GET'])
@rate_limit(limit=240, window=60)
@_trade_auth
def agent_signals():
    return jsonify({'signals': _signals_view(), 'paper': _S._paper(), 'running': _AGENT['running'],
                    'mode': _AGENT['mode'], 'ttl_s': SIGNAL_TTL_S, 'max_drift_pct': SIGNAL_DRIFT_PCT})


def _signal_get(sid):
    with _SIGNALS_LOCK:
        _signals_prune()
        return _AGENT.get('signals', {}).get(str(sid)[:32])


@trading_agent_bp.route('/api/trade/agent/signals/<sid>/take', methods=['POST'])
@rate_limit(limit=20, window=60)
@_trade_auth
def agent_signal_take(sid):
    """La persona aprueba la señal (su PIN = su confirmación): misma validación que /api/trade/order y EL camino
    único. 409 si venció, ya se usó o el precio se movió en contra más de SIGNAL_DRIFT_PCT."""
    if not _S.ALPACA_KEY:
        return _S._broker_missing_response()
    sg = _signal_get(sid)
    if sg is None:
        return _S._bad('Señal no encontrada (quizá venció)', 'Signal not found (it may have expired)',
                       code='signal_not_found', status=404)
    if sg['status'] != 'pending':
        return _S._bad(f"La señal ya no está pendiente ({sg['status']})", f"The signal is no longer pending "
                       f"({sg['status']})", code='signal_' + sg['status'], status=409)
    summary = {'symbol': sg['ticker'], 'side': sg['side'], 'signal_id': sg['id'], 'kind': sg['kind'],
               'notional': sg.get('notional'), 'qty': sg.get('qty')}
    if not _S._house_trading_enabled():
        _S._trade_audit('agent_signal_take', dict(summary, outcome='blocked_kill_switch'))
        return _S._trading_halted_response()
    lb = _S._house_ledger_block()
    if lb is not None:
        _S._trade_audit('agent_signal_take', dict(summary, outcome='blocked_ledger_chain'))
        return lb
    now_px = None
    if _S.FINNHUB and sg.get('price'):
        data, err = _S._fetch_quote_raw(sg['ticker'], timeout=6)
        if not err and isinstance(data, dict):
            try:
                now_px = float(data.get('c') or 0) or None
            except (TypeError, ValueError):
                now_px = None
    if now_px and sg['kind'] != 'stop':
        move = (now_px / sg['price'] - 1) * 100
        against = move if sg['side'] == 'buy' else -move
        if against > SIGNAL_DRIFT_PCT:
            _S._trade_audit('agent_signal_take', dict(summary, outcome='rejected', reason='price_moved',
                                                     now_px=now_px, signal_px=sg['price']))
            return _S._bad(f"El precio se movió {move:+.2f} % desde la señal ({sg['price']} → {now_px}): ya no es la "
                           f"misma oportunidad. Espera la próxima señal.",
                           f"The price moved {move:+.2f}% since the signal ({sg['price']} → {now_px}): it is no longer "
                           f"the same opportunity. Wait for the next signal.", code='price_moved', status=409)
    with _SIGNALS_LOCK:
        if sg['status'] != 'pending':
            return _S._bad('La señal ya se está usando', 'The signal is already being used', code='signal_busy',
                           status=409)
        sg['status'] = 'taking'
    channel = _S._identity_channel()
    kw = dict(order_type='market', time_in_force='gtc' if '/' in sg['ticker'] else 'day',
              client_order_id='kh-sig-' + sg['id'], source='ui', channel=channel, requested_by=_S._trade_actor(),
              rationale=f"señal del agente ({sg['confidence']}): {sg['reason']}"[:300])
    if sg.get('qty'):
        kw.update(qty=sg['qty'], checks_mode='house_reduce' if sg['kind'] == 'stop' or sg['side'] == 'sell'
                  else 'house_today')
    else:
        kw.update(notional=sg['notional'])
    res = _S._house_call('house_order', sg['ticker'], sg['side'], **kw)
    payload, st = _S._house_http(res)
    with _SIGNALS_LOCK:
        sg['status'] = 'taken' if st in (200, 202) else 'pending'
        if st in (200, 202):
            sg['order_id'] = payload.get('id')
            sg['taken_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    _S._trade_audit('agent_signal_take', dict(summary, outcome='submitted' if st == 200 else
                                             ('pending_approval' if st == 202 else 'rejected'), http_status=st,
                                             now_px=now_px, alpaca_order_id=payload.get('id') if st == 200 else None,
                                             decision_id=payload.get('decision_id')))
    payload = dict(payload, signal_id=sg['id'], signal_px=sg['price'], now_px=now_px)
    return jsonify(payload), st


@trading_agent_bp.route('/api/trade/agent/signals/<sid>/dismiss', methods=['POST'])
@rate_limit(limit=60, window=60)
@_trade_auth
def agent_signal_dismiss(sid):
    """Descartar una señal: queda en el libro (trade.agent_signal, status noop) quién la descartó."""
    sg = _signal_get(sid)
    if sg is None or sg['status'] != 'pending':
        return _S._bad('Señal no pendiente', 'Signal not pending', code='signal_not_pending', status=409)
    try:
        from ontology.db import ontology_available
        if ontology_available():
            from core import decisions, identity
            from ontology.db import session_scope
            ctx = decisions.DecisionCtx('trade.agent_signal', identity.current() or identity.principal_from_request(),
                                        subject={'symbol': sg['ticker'], 'action': sg['side'], 'mode': 'manual'})
            ctx.output = {'dismissed': True, 'signal_id': sg['id'], 'signal_decision_id': sg.get('decision_id')}
            with session_scope() as s:
                decisions.record(s, ctx, status='noop')
    except Exception as e:  # noqa: BLE001
        log.warning('agente: descarte no registrado (%s)', type(e).__name__)
    with _SIGNALS_LOCK:
        sg['status'] = 'dismissed'
    _S._trade_audit('agent_signal_dismiss', {'signal_id': sg['id'], 'symbol': sg['ticker'], 'side': sg['side']})
    return jsonify({'status': 'dismissed', 'signal_id': sg['id']})
