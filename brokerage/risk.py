"""brokerage/risk.py — controles de riesgo PRE-orden por cliente.

Cada control devuelve {name, ok, detail, severity}:
  · severity 'block' → si ok=False la orden NO se puede enviar.
  · severity 'warn'  → aviso que no bloquea (ok queda True y `warn`=True).
Los textos van en español simple (la UI los muestra tal cual); `detail_en`
lleva la versión en inglés.

Perfiles (rellenan los límites que el cliente no haya fijado a mano):

  perfil        pos. máx.  orden máx.  diario máx.  stop caída  clases
  conservador     10 %     US$1.000    US$2.500       10 %      acciones EE.UU.
  moderado        20 %     US$5.000    US$15.000      20 %      acciones + cripto
  agresivo        35 %     US$25.000   US$75.000      35 %      acciones + cripto

  pos. máx.  = tamaño máximo de UNA posición como % del patrimonio, DESPUÉS
               de la compra (max_position_pct).
  orden máx. = monto máximo por COMPRA (max_order_usd). Mínimo US$1.
  diario máx.= suma de COMPRAS enviadas en el día de mercado (max_daily_usd).
  stop caída = si el patrimonio cae más de X % desde su máximo observado
               (high-water mark), se bloquean COMPRAS nuevas (las ventas
               siguen permitidas) (max_drawdown_stop_pct).

Ventas: solo se vende lo que se tiene (sin cortos) y NO cuentan contra la orden
máx. ni el diario máx. — reducir riesgo (salir de una posición en una caída)
nunca debe exigir partir la venta en varios días.

Margen: por defecto una compra debe caber en el EFECTIVO (min(cash,
buying_power); cripto: non_marginable_buying_power). Solo con
mandate.allow_margin=true se usa el buying_power de Alpaca (que incluye
préstamo 2x/4x).
"""
import math
import os
import re
from datetime import datetime, time as dtime, timedelta, timezone

from brokerage.alpaca import is_crypto

# INFRA_OPERATIVA paso 9: los topes y perfiles son POLÍTICA aprobada → artefacto `policy.broker_risk` del release
# vigente (governance/artifacts/policy.broker_risk@<semver>.json; manda el aprobado en la base). Ninguno se
# declara aquí:
#   HARD_MAX_ORDER_USD  — tope absoluto por orden (1.0.0: US$100.000, igual que /api/trade/order);
#   MIN_ORDER_USD, DUPLICATE_WINDOW_S, LIMIT_DEVIATION_PCT (precio límite vs. mercado: más lejos → bloqueo/aviso);
#   PROFILES            — la tabla del docstring (conservador / moderado / agresivo); ASSET_CLASSES.
from core import governance as _gov  # noqa: E402
(
    HARD_MAX_ORDER_USD, MIN_ORDER_USD, DUPLICATE_WINDOW_S, LIMIT_DEVIATION_PCT, PROFILES, ASSET_CLASSES,
) = _gov.bind(globals(), 'policy.broker_risk', {
    'HARD_MAX_ORDER_USD': 'hard_max_order_usd', 'MIN_ORDER_USD': 'min_order_usd',
    'DUPLICATE_WINDOW_S': 'duplicate_window_s', 'LIMIT_DEVIATION_PCT': 'limit_deviation_pct',
    'PROFILES': 'profiles', 'ASSET_CLASSES': ('asset_classes', tuple)})
LIMIT_KEYS = ('max_position_pct', 'max_order_usd', 'max_daily_usd', 'max_drawdown_stop_pct')

# INFRA_OPERATIVA paso 15 — UN SOLO CAMINO: la cuenta de la casa por sus rutas clásicas (/api/trade/order,
# /api/trade/close, el agente de trading, la voz, cripto y la terminal) pasa por estos MISMOS controles. Mientras
# Fabrizio no fije los límites de su cuenta (BRECHAS #1, sin respuesta) rigen los de HOY: tope US$100.000 por orden
# (también en ventas, como hasta ahora) y NINGÚN tope nuevo. Los controles que esas rutas no tenían se evalúan igual
# pero en SOMBRA (avisan y quedan en el libro de decisiones, nunca bloquean) — así Fabrizio ve qué habrían frenado
# antes de decidir. Bloquear con ellos = policy.broker_risk@1.1.0 aprobado con PIN (paso 17), no un cambio de código.
CHECK_MODES = ('standard', 'house_today', 'house_reduce')
HOUSE_TODAY_SHADOW = ('daily_limit', 'position_limit', 'drawdown_stop', 'buying_power', 'holdings', 'duplicate',
                      'limit_price')


def check_policy(mode=None):
    """Política de controles por camino: 'standard' (👥 Clientes, MCP, comité) o 'house_today' (rutas clásicas de
    la casa con los límites de hoy). → {shadow, limits, cap_sells, allow_margin} (vacío = estándar)."""
    if mode in ('house_today', 'house_reduce'):
        pol = {'mode': mode, 'shadow': HOUSE_TODAY_SHADOW,
               'limits': {'max_order_usd': HARD_MAX_ORDER_USD}, 'cap_sells': True, 'allow_margin': True}
        if mode == 'house_reduce':
            # SALIDAS de la casa (botón CLOSE, stop-loss del agente): hoy nunca tuvieron tope por orden (antes eran
            # DELETE /v2/positions o una venta directa) — la orden que REDUCE o aplana una posición existente, hasta la
            # cantidad que se tiene, no se frena por el tope de US$100.000. Lo que abra o aumente exposición, sí.
            pol['reduce_only'] = True
        return pol
    return {}


def reduces_position(order, positions):
    """True si `order` (por CANTIDAD) solo reduce o cierra una posición existente: del lado contrario a la posición
    (venta de una larga, compra de una corta) y sin pasar de la cantidad que hay. Por monto (notional) → False."""
    od = order or {}
    try:
        q = float(od.get('qty')) if od.get('qty') is not None else None
    except (TypeError, ValueError):
        q = None
    if not q or q <= 0:
        return False
    key = str(od.get('symbol') or '').upper().replace('/', '')
    pos = next((p for p in positions or [] if str(p.get('symbol') or '').upper().replace('/', '') == key), None)
    if pos is None:
        return False
    try:
        pq = float(pos.get('qty') or 0)
    except (TypeError, ValueError):
        return False
    short = str(pos.get('side') or '').lower() == 'short' or pq < 0
    held = abs(pq)
    return held > 0 and od.get('side') == ('buy' if short else 'sell') and q <= held + 1e-9

_STOCK_RE = re.compile(r'^[A-Z][A-Z0-9.\-]{0,9}$')


def env_on(name, default='off'):
    return (os.getenv(name, default) or default).strip().lower() in ('on', '1', 'true', 'yes', 'si', 'sí')


def trading_enabled():
    """Interruptor global del CORRETAJE. Por defecto ENCENDIDO (el papel debe
    funcionar); BROKERAGE_TRADING_ENABLED=off bloquea al instante toda orden
    nueva que pase por brokerage/ (👥 Clientes, agentes MCP, comité y — desde el paso 15 — las rutas clásicas
    /api/trade/order y /api/trade/close y el agente de trading de server.py, que ya salen por aquí)."""
    return env_on('BROKERAGE_TRADING_ENABLED', 'on')


def live_env_enabled():
    """Primer candado del dinero real (el segundo es client.live_enabled)."""
    return env_on('BROKERAGE_LIVE_ENABLED', 'off')


def auto_approve_paper():
    return env_on('BROKERAGE_AUTO_APPROVE_PAPER', 'off')


def effective_limits(profile, overrides=None, mandate=None):
    """Límites numéricos efectivos = perfil + overrides del cliente."""
    base = dict(PROFILES.get(profile or 'moderado') or PROFILES['moderado'])
    out = {k: float(base[k]) for k in LIMIT_KEYS}
    for src in (mandate or {}, overrides or {}):
        for k in LIMIT_KEYS:
            v = src.get(k) if isinstance(src, dict) else None
            try:
                if v is not None and v != '' and float(v) > 0:
                    out[k] = float(v)
            except (TypeError, ValueError):
                pass
    out['max_order_usd'] = min(out['max_order_usd'], HARD_MAX_ORDER_USD)
    out['max_position_pct'] = min(out['max_position_pct'], 100.0)
    out['max_drawdown_stop_pct'] = min(out['max_drawdown_stop_pct'], 100.0)
    return out


def effective_mandate(profile, mandate=None):
    base = PROFILES.get(profile or 'moderado') or PROFILES['moderado']
    m = mandate if isinstance(mandate, dict) else {}
    classes = m.get('allowed_asset_classes')
    if not isinstance(classes, list) or not classes:
        classes = list(base['allowed_asset_classes'])
    classes = [c for c in classes if c in ASSET_CLASSES] or ['us_equity']

    def syms(key):
        raw = m.get(key) or []
        if isinstance(raw, str):
            raw = re.split(r'[,;\s]+', raw)
        return sorted({str(x).strip().upper() for x in raw if str(x).strip()})
    return {'allowed_asset_classes': classes, 'restricted_symbols': syms('restricted_symbols'),
            'allowed_symbols': syms('allowed_symbols'), 'notes': str(m.get('notes') or '')[:500],
            # préstamo (margen) de Alpaca: APAGADO salvo que el mandato lo pida por escrito
            'allow_margin': m.get('allow_margin') is True}


def asset_class(symbol):
    return 'crypto' if is_crypto(symbol) else 'us_equity'


def valid_symbol(symbol):
    s = str(symbol or '').upper().strip()
    if '/' in s:
        return is_crypto(s)
    try:
        from core.http import _safe_ticker
        t = _safe_ticker(s)
    except Exception:  # noqa: BLE001
        t = s
    return bool(t) and bool(_STOCK_RE.match(t))


def _ny_now(now):
    try:
        from zoneinfo import ZoneInfo
        return now.astimezone(ZoneInfo('America/New_York'))
    except Exception:  # noqa: BLE001 — sin tzdata: aproximación UTC-4 (horario de verano)
        return now.astimezone(timezone(timedelta(hours=-4)))


def trading_day_start(now=None):
    """Inicio (UTC) del día de mercado de Nueva York que contiene `now`."""
    now = now or datetime.now(timezone.utc)
    ny = _ny_now(now)
    start = ny.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(timezone.utc)


def market_open_approx(now=None):
    ny = _ny_now(now or datetime.now(timezone.utc))
    if ny.weekday() >= 5:
        return False
    return dtime(9, 30) <= ny.time() < dtime(16, 0)


def _c(name, ok, es, en, severity='block'):
    d = {'name': name, 'ok': bool(ok), 'detail': es, 'detail_en': en, 'severity': severity}
    if severity == 'warn':
        d['warn'] = not ok
        d['ok'] = True
    return d


def _usd(v):
    try:
        return f'US${float(v):,.2f}'
    except (TypeError, ValueError):
        return '—'


def _num(v):
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _min(*vals):
    xs = [v for v in vals if v is not None]
    return min(xs) if xs else None


def run_checks(ctx):
    """ctx: dict con
        client: {status, mode, live_enabled, connected, risk_profile, risk_limits, mandate, hwm_equity}
        order:  {symbol, side, notional, qty, order_type, limit_price}
        account: {equity, cash, buying_power, non_marginable_buying_power?} | None ; account_error: str | None
        positions: [{symbol, qty, market_value, current_price}]
        price: float | None (precio usado para estimar el monto)
        ref_price: float | None (precio de MERCADO de referencia; compara el límite)
        est_usd: float | None
        daily_used_usd: float (solo COMPRAS de hoy)
        recent_duplicate: bool ; unresolved_order: bool (orden con estado desconocido)
        market_open: bool | None (None = desconocido) ; clock_source: 'alpaca' | 'approx'
    Devuelve la lista de controles."""
    cl, od = ctx.get('client') or {}, ctx.get('order') or {}
    acct = ctx.get('account') or {}
    sym = str(od.get('symbol') or '').upper()
    side = od.get('side')
    est = ctx.get('est_usd')
    pol = ctx.get('policy') or {}
    limits, mandate = _limits_and_mandate(cl, pol)
    checks = []

    # 1. interruptor global
    on = trading_enabled()
    checks.append(_c('kill_switch', on,
                     'Interruptor general encendido' if on else
                     'Interruptor general APAGADO (BROKERAGE_TRADING_ENABLED=off): no se envía ninguna orden',
                     'Master switch on' if on else 'Master switch OFF (BROKERAGE_TRADING_ENABLED=off): no orders are sent'))

    # 2. modo papel / dinero real
    mode = cl.get('mode') or 'paper'
    if mode != 'live':
        checks.append(_c('mode', True, '🧪 Cuenta de PAPEL (dinero simulado)', '🧪 PAPER account (simulated money)'))
    else:
        env_ok, cli_ok = live_env_enabled(), bool(cl.get('live_enabled'))
        ok = env_ok and cli_ok
        if ok:
            es, en = '🔴 DINERO REAL habilitado (servidor y cliente)', '🔴 REAL MONEY enabled (server and client)'
        elif not env_ok:
            es = '🔴 Cuenta de DINERO REAL bloqueada: el servidor no tiene BROKERAGE_LIVE_ENABLED=on'
            en = '🔴 REAL MONEY account blocked: server lacks BROKERAGE_LIVE_ENABLED=on'
        else:
            es = '🔴 Cuenta de DINERO REAL bloqueada: este cliente no tiene "dinero real habilitado"'
            en = '🔴 REAL MONEY account blocked: this client does not have "real money enabled"'
        checks.append(_c('mode', ok, es, en))
        # 2b. INFRA_OPERATIVA paso 7: cadena del libro de decisiones íntegra (o reconocida con PIN). Solo
        # DINERO REAL: el papel nunca se bloquea por esto. Sin poder comprobarla → bloquea (falla cerrado).
        lc = ctx.get('ledger_chain')
        if lc is None:
            try:
                from core.ledger import money_gate
                lc = money_gate()
            except Exception:  # noqa: BLE001
                lc = (False, 'No se pudo comprobar la cadena del libro de decisiones: dinero real bloqueado',
                      'Could not check the decision-ledger chain: real money blocked')
        checks.append(_c('ledger_chain', bool(lc[0]), lc[1], lc[2]))

    # 3. estado del cliente
    st = cl.get('status') or 'active'
    checks.append(_c('client_status', st == 'active',
                     'Cliente activo' if st == 'active' else 'Cliente PAUSADO: reactívalo para operar',
                     'Client active' if st == 'active' else 'Client PAUSED: resume it to trade'))

    # 4. cuenta conectada y legible
    if not cl.get('connected'):
        checks.append(_c('account', False, 'La cuenta de Alpaca no está conectada', 'The Alpaca account is not connected'))
    elif ctx.get('account_error'):
        checks.append(_c('account', False, f'No se pudo leer la cuenta de Alpaca: {ctx["account_error"]}',
                         f'Could not read the Alpaca account: {ctx["account_error"]}'))
    else:
        checks.append(_c('account', True, 'Cuenta de Alpaca leída en vivo', 'Alpaca account read live'))

    # 5. símbolo y clase de activo
    if not valid_symbol(sym):
        checks.append(_c('symbol', False, f'Símbolo inválido: «{sym}» (acciones: NVDA; cripto: BTC/USD)',
                         f'Invalid symbol: "{sym}" (stocks: NVDA; crypto: BTC/USD)'))
    else:
        ac = asset_class(sym)
        ok = ac in mandate['allowed_asset_classes']
        name_es = 'cripto' if ac == 'crypto' else 'acciones de EE.UU.'
        name_en = 'crypto' if ac == 'crypto' else 'US stocks'
        checks.append(_c('symbol', ok, f'{sym} · {name_es}' + ('' if ok else ' — el mandato no permite esta clase de activo'),
                         f'{sym} · {name_en}' + ('' if ok else ' — the mandate does not allow this asset class')))

    # 6. símbolos restringidos / lista permitida
    restricted = sym in mandate['restricted_symbols']
    not_allowed = bool(mandate['allowed_symbols']) and sym not in mandate['allowed_symbols']
    ok = not (restricted or not_allowed)
    checks.append(_c('restricted', ok,
                     'Símbolo permitido por el mandato' if ok else
                     (f'{sym} está RESTRINGIDO en el mandato del cliente' if restricted else
                      f'{sym} no está en la lista de símbolos permitidos del cliente'),
                     'Symbol allowed by the mandate' if ok else
                     (f"{sym} is RESTRICTED in the client's mandate" if restricted else
                      f"{sym} is not in the client's allowed list")))

    # 7. tamaño de la orden (las VENTAS no tienen tope por orden: el tope es lo que se tiene)
    if est is None:
        checks.append(_c('order_size', False,
                         'No se pudo estimar el monto en USD (sin precio de referencia): usa un monto en USD',
                         'Could not estimate the USD amount (no reference price): use a USD amount'))
    elif est < MIN_ORDER_USD:
        checks.append(_c('order_size', False, f'Monto demasiado pequeño ({_usd(est)}; mínimo US$1)',
                         f'Amount too small ({_usd(est)}; minimum US$1)'))
    elif side == 'sell' and not pol.get('cap_sells'):
        checks.append(_c('order_size', True,
                         f'Venta de {_usd(est)}: las ventas no tienen tope por orden (solo se vende lo que se tiene)',
                         f'Sale of {_usd(est)}: sells have no per-order cap (only what is held can be sold)'))
    elif pol.get('reduce_only') and reduces_position(od, ctx.get('positions')):
        checks.append(_c('order_size', True,
                         f'Cierre de una posición existente ({_usd(est)}): las salidas no tienen tope por orden '
                         f'(solo hasta la cantidad que se tiene)',
                         f'Closing an existing position ({_usd(est)}): exits have no per-order cap (only up to '
                         f'the quantity held)'))
    elif est > limits['max_order_usd']:
        checks.append(_c('order_size', False,
                         f'Monto {_usd(est)} supera el máximo por orden del cliente ({_usd(limits["max_order_usd"])})',
                         f'Amount {_usd(est)} exceeds the client per-order max ({_usd(limits["max_order_usd"])})'))
    else:
        checks.append(_c('order_size', True, f'Monto {_usd(est)} dentro del máximo por orden ({_usd(limits["max_order_usd"])})',
                         f'Amount {_usd(est)} within the per-order max ({_usd(limits["max_order_usd"])})'))

    # 8. límite diario (solo COMPRAS; vender para reducir riesgo nunca lo consume)
    used = float(ctx.get('daily_used_usd') or 0)
    if side == 'sell':
        checks.append(_c('daily_limit', True,
                         f'Las ventas no consumen el límite diario (compras de hoy: {_usd(used)} de {_usd(limits["max_daily_usd"])})',
                         f'Sells do not use the daily limit (buys today: {_usd(used)} of {_usd(limits["max_daily_usd"])})'))
    elif est is not None:
        tot = used + est
        ok = tot <= limits['max_daily_usd']
        checks.append(_c('daily_limit', ok,
                         f'Hoy: {_usd(used)} comprado + {_usd(est)} = {_usd(tot)} de {_usd(limits["max_daily_usd"])} diarios'
                         + ('' if ok else ' — supera el límite diario'),
                         f'Today: {_usd(used)} bought + {_usd(est)} = {_usd(tot)} of {_usd(limits["max_daily_usd"])} daily'
                         + ('' if ok else ' — exceeds the daily limit')))

    positions = ctx.get('positions') or []
    pos = next((p for p in positions if str(p.get('symbol') or '').upper().replace('/', '') == sym.replace('/', '')), None)
    pos_mv = float((pos or {}).get('market_value') or 0)
    pos_qty = float((pos or {}).get('qty') or 0)
    equity = acct.get('equity')

    if side == 'buy':
        # 9. dinero disponible SIN préstamo (salvo mandato allow_margin)
        crypto = asset_class(sym) == 'crypto'
        bp, cash = _num(acct.get('buying_power')), _num(acct.get('cash'))
        nmbp = _num(acct.get('non_marginable_buying_power'))
        margin = bool(mandate.get('allow_margin'))
        if margin:
            avail = (nmbp if nmbp is not None else _min(bp, cash)) if crypto else bp
        else:
            avail = _min(bp, cash, nmbp if crypto else None)
        if avail is None or est is None:
            checks.append(_c('buying_power', False, 'Dinero disponible desconocido (Alpaca no informó efectivo ni poder de compra)',
                             'Available funds unknown (Alpaca did not report cash or buying power)'))
        else:
            ok = est <= avail
            if margin:
                es = f'Poder de compra {_usd(avail)} (el mandato PERMITE margen/préstamo)'
                en = f'Buying power {_usd(avail)} (the mandate ALLOWS margin/borrowing)'
            else:
                es = (f'Disponible sin préstamo {_usd(avail)} (efectivo {_usd(cash)}; poder de compra de Alpaca {_usd(bp)}'
                      + (f'; cripto sin margen {_usd(nmbp)}' if crypto and nmbp is not None else '') + ')')
                en = (f'Available without borrowing {_usd(avail)} (cash {_usd(cash)}; Alpaca buying power {_usd(bp)}'
                      + (f'; non-marginable {_usd(nmbp)}' if crypto and nmbp is not None else '') + ')')
            checks.append(_c('buying_power', ok, es + ('' if ok else f' — insuficiente para {_usd(est)}'),
                             en + ('' if ok else f' — not enough for {_usd(est)}')))
        # 10. tamaño de la posición después de la compra
        if equity and float(equity) > 0 and est is not None:
            after = (pos_mv + est) / float(equity) * 100.0
            ok = after <= limits['max_position_pct'] + 1e-9
            checks.append(_c('position_limit', ok,
                             f'{sym} pasaría a ser {after:.1f}% del patrimonio (máx. {limits["max_position_pct"]:.0f}%)',
                             f'{sym} would become {after:.1f}% of equity (max {limits["max_position_pct"]:.0f}%)'))
        else:
            checks.append(_c('position_limit', False, 'Patrimonio desconocido: no se puede medir el tamaño de la posición',
                             'Equity unknown: cannot size the position'))
        # 11. stop por caída desde el máximo (solo bloquea compras)
        hwm = cl.get('hwm_equity')
        if hwm and equity is not None and float(hwm) > 0:
            dd = max(0.0, (float(hwm) - float(equity)) / float(hwm) * 100.0)
            ok = dd <= limits['max_drawdown_stop_pct']
            checks.append(_c('drawdown_stop', ok,
                             f'Caída desde el máximo: {dd:.1f}% (stop en {limits["max_drawdown_stop_pct"]:.0f}%)'
                             + ('' if ok else ' — compras BLOQUEADAS; las ventas siguen permitidas'),
                             f'Drawdown from peak: {dd:.1f}% (stop at {limits["max_drawdown_stop_pct"]:.0f}%)'
                             + ('' if ok else ' — buys BLOCKED; sells still allowed')))
        else:
            checks.append(_c('drawdown_stop', True, 'Stop por caída: aún sin máximo registrado',
                             'Drawdown stop: no peak recorded yet'))
    elif side == 'sell':
        # 9b. sin ventas en corto: solo se vende lo que se tiene
        if not pos:
            checks.append(_c('holdings', False, f'El cliente no tiene {sym}: no se permiten ventas en corto',
                             f'The client holds no {sym}: short selling is not allowed'))
        else:
            q = od.get('qty')
            if q is not None:
                ok = float(q) <= pos_qty + 1e-9
                checks.append(_c('holdings', ok, f'Tiene {pos_qty:g} {sym}' + ('' if ok else f' — no alcanza para vender {float(q):g}'),
                                 f'Holds {pos_qty:g} {sym}' + ('' if ok else f' — not enough to sell {float(q):g}')))
            else:
                ok = est is not None and est <= pos_mv * 1.001
                checks.append(_c('holdings', ok, f'Posición de {sym}: {_usd(pos_mv)}' + ('' if ok else f' — menor que {_usd(est)}'),
                                 f'{sym} position: {_usd(pos_mv)}' + ('' if ok else f' — smaller than {_usd(est)}')))

    # 12. duplicado (misma orden en los últimos 60 s)
    dup = bool(ctx.get('recent_duplicate'))
    checks.append(_c('duplicate', not dup,
                     'Sin órdenes iguales en el último minuto' if not dup else
                     f'Ya se envió una orden {side} de {sym} para este cliente hace menos de {DUPLICATE_WINDOW_S} s',
                     'No identical orders in the last minute' if not dup else
                     f'A {side} order for {sym} was already sent for this client less than {DUPLICATE_WINDOW_S}s ago'))

    # 12b. orden anterior con estado DESCONOCIDO (la red falló al enviarla: puede
    # que Alpaca la tenga) → no se repite hasta sincronizar
    if ctx.get('unresolved_order'):
        checks.append(_c('unresolved', False,
                         f'Hay una orden {side} de {sym} de este cliente con estado DESCONOCIDO (falló la conexión con '
                         'Alpaca al enviarla y puede haberse ejecutado): pulsa ⇅ Sincronizar en Órdenes antes de repetirla',
                         f'There is a {side} order for {sym} for this client in UNKNOWN state (the connection to Alpaca '
                         'failed while sending it and it may have executed): press ⇅ Sync in Orders before repeating it'))

    # 12c. precio límite vs. mercado (un límite muy lejos del mercado suele ser un error de tipeo)
    if od.get('order_type') == 'limit' and od.get('limit_price'):
        lp, ref = _num(od.get('limit_price')), _num(ctx.get('ref_price'))
        if not ref or ref <= 0:
            checks.append(_c('limit_price', False,
                             'Sin precio de mercado para comparar el límite: el monto se estimó con el precio límite',
                             'No market price to compare the limit with: the amount was estimated at the limit price',
                             severity='warn'))
        else:
            dev = (lp - ref) / ref * 100.0
            marketable = (side == 'sell' and dev < -LIMIT_DEVIATION_PCT) or (side == 'buy' and dev > LIMIT_DEVIATION_PCT)
            passive = (side == 'sell' and dev > LIMIT_DEVIATION_PCT) or (side == 'buy' and dev < -LIMIT_DEVIATION_PCT)
            where_es = 'por debajo' if dev < 0 else 'por encima'
            where_en = 'below' if dev < 0 else 'above'
            base_es = f'Límite {_usd(lp)} está {abs(dev):.1f}% {where_es} del mercado ({_usd(ref)})'
            base_en = f'Limit {_usd(lp)} is {abs(dev):.1f}% {where_en} the market ({_usd(ref)})'
            if marketable:
                checks.append(_c('limit_price', False,
                                 base_es + f' — se ejecutaría a precio de mercado; revisa el precio (máx. ±{LIMIT_DEVIATION_PCT:.0f}%)',
                                 base_en + f' — it would fill at market; check the price (max ±{LIMIT_DEVIATION_PCT:.0f}%)'))
            elif passive:
                checks.append(_c('limit_price', False, base_es + ' — probablemente no se ejecute pronto',
                                 base_en + ' — it will probably not fill soon', severity='warn'))
            else:
                checks.append(_c('limit_price', True, base_es, base_en, severity='warn'))

    # 13. horario de mercado (aviso, no bloquea)
    if asset_class(sym) == 'us_equity' and valid_symbol(sym):
        mo = ctx.get('market_open')
        approx = ctx.get('clock_source') != 'alpaca'
        suf_es = ' (estimado por horario, sin feriados)' if approx else ''
        suf_en = ' (estimated from hours, no holidays)' if approx else ''
        if mo is False:
            checks.append(_c('market_hours', False,
                             'Mercado de EE.UU. CERRADO: la orden quedará en cola hasta la apertura' + suf_es,
                             'US market CLOSED: the order will queue until the open' + suf_en, severity='warn'))
        else:
            checks.append(_c('market_hours', True, 'Mercado de EE.UU. abierto' + suf_es,
                             'US market open' + suf_en, severity='warn'))
    return _apply_shadow(checks, pol.get('shadow'))


def _limits_and_mandate(cl, pol=None):
    """Límites y mandato EFECTIVOS de un contexto (perfil + overrides del cliente + política del camino)."""
    pol = pol or {}
    limits = effective_limits(cl.get('risk_profile'), cl.get('risk_limits'))
    for k, v in (pol.get('limits') or {}).items():
        limits[k] = float(v)
    mandate = effective_mandate(cl.get('risk_profile'), cl.get('mandate'))
    if pol.get('allow_margin'):
        mandate['allow_margin'] = True
    return limits, mandate


_SHADOW_ES = ' — solo aviso: tus límites aún no están fijados (BRECHAS #1), no bloquea'
_SHADOW_EN = ' — warning only: your limits are not set yet (BRECHAS #1), it does not block'


def _apply_shadow(checks, shadow):
    """Los controles en SOMBRA se evalúan igual (mismo texto, misma cifra) pero nunca bloquean: quedan como aviso
    (`shadow: true`, `warn` = habría bloqueado) y entran al libro de decisiones como violaciones de aviso."""
    names = set(shadow or ())
    if not names:
        return checks
    for c in checks:
        if c['name'] in names and c.get('severity', 'block') == 'block':
            would_block = not c['ok']
            c.update(severity='warn', ok=True, warn=would_block, shadow=True)
            if would_block:
                c['detail'] = c['detail'] + _SHADOW_ES
                c['detail_en'] = (c.get('detail_en') or c['detail']) + _SHADOW_EN
    return checks


def is_blocked(checks):
    return any((not c.get('ok')) and c.get('severity', 'block') == 'block' for c in checks or [])


def failed(checks):
    return [c for c in checks or [] if (not c.get('ok')) and c.get('severity', 'block') == 'block']


# ════════════════════════════════════════════════════════════════════════════
# Paso 17 — los MISMOS controles como HECHOS del grafo foco de las puertas SHACL (governance/shapes/order.ttl)
# ════════════════════════════════════════════════════════════════════════════
# Cada control de run_checks → una o más reglas con IRI estable (khr:order.*). tests/test_gates_orders_parity.py
# exige que, sobre miles de contextos aleatorios, run_checks y las puertas compiladas den EXACTAMENTE el mismo
# veredicto por control. Las reglas nuevas (sector, país, cadena, frescura, origen IA, lectura por voz, política
# cambiada) solo existen en las puertas (en SOMBRA hasta que Fabrizio apruebe sus topes, BRECHAS #1).
CHECK_RULES = {
    'kill_switch': ('khr:order.kill_switch',),
    'mode': ('khr:order.mode_live_enabled',),
    'ledger_chain': ('khr:order.ledger_chain',),
    'client_status': ('khr:order.client_active',),
    'account': ('khr:order.account_readable',),
    'symbol': ('khr:order.symbol_tradable', 'khr:order.asset_class_allowed'),
    'restricted': ('khr:order.restricted', 'khr:order.not_allowed'),
    'order_size': ('khr:order.price_known', 'khr:order.min_order_usd', 'khr:order.max_order_usd'),
    'daily_limit': ('khr:order.daily_cap',),
    'buying_power': ('khr:order.buying_power',),
    'position_limit': ('khr:order.position_pct_after',),
    'drawdown_stop': ('khr:order.drawdown_stop',),
    'holdings': ('khr:order.no_short',),
    'duplicate': ('khr:order.duplicate_window',),
    'unresolved': ('khr:order.unresolved',),
    'limit_price': ('khr:order.limit_deviation', 'khr:order.limit_passive', 'khr:order.limit_reference'),
    'market_hours': ('khr:order.market_hours',),
}
POSITION_TOL = 1e-9          # la tolerancia de run_checks en el % de la posición (se aplica al HECHO, igual)


def _available(acct, mandate, crypto):
    bp, cash = _num(acct.get('buying_power')), _num(acct.get('cash'))
    nmbp = _num(acct.get('non_marginable_buying_power'))
    if mandate.get('allow_margin'):
        return (nmbp if nmbp is not None else _min(bp, cash)) if crypto else bp
    return _min(bp, cash, nmbp if crypto else None)


def order_facts(ctx, extra=None):
    """Los hechos de una orden para el grafo foco (core/gates/focus.order_triples), con EXACTAMENTE la semántica de
    run_checks (mismas fórmulas, mismos límites efectivos, misma política del camino). `extra` agrega los hechos de
    las reglas nuevas: origin, channel, readback_sha, paper_auto_approved, quote_age_s, account_age_s, pesos
    después de la orden (sector/país/cadena, de la vista AccountRisk), policy_changed y sus límites de política."""
    cl, od = ctx.get('client') or {}, ctx.get('order') or {}
    acct = ctx.get('account') or {}
    pol = ctx.get('policy') or {}
    limits, mandate = _limits_and_mandate(cl, pol)
    sym = str(od.get('symbol') or '').upper()
    side = od.get('side')
    est = ctx.get('est_usd')
    mode = cl.get('mode') or 'paper'
    f = {'id': od.get('id') or 'req', 'symbol': sym, 'side': side, 'order_type': od.get('order_type') or 'market',
         'trading_enabled': trading_enabled(), 'account_mode': mode, 'client_status': cl.get('status') or 'active',
         'account_readable': bool(cl.get('connected')) and not ctx.get('account_error'),
         'symbol_valid': valid_symbol(sym), 'restricted_symbols': mandate['restricted_symbols'],
         'allowed_symbols': mandate['allowed_symbols'], 'duplicate_recent': bool(ctx.get('recent_duplicate')),
         'unresolved': bool(ctx.get('unresolved_order')), 'min_order_usd': MIN_ORDER_USD, 'est_usd': est}
    if mode == 'live':
        f['live_env_enabled'] = live_env_enabled()
        f['client_live_enabled'] = bool(cl.get('live_enabled'))
        lc = ctx.get('ledger_chain')
        if lc is None:
            try:
                from core.ledger import money_gate
                lc = money_gate()
            except Exception:  # noqa: BLE001
                lc = (False, '', '')
        f['ledger_chain_ok'] = bool(lc[0])
    if f['symbol_valid']:
        f['asset_class'] = asset_class(sym)
        f['allowed_asset_classes'] = list(mandate['allowed_asset_classes'])
    if (side != 'sell' or pol.get('cap_sells')) and not (pol.get('reduce_only')
                                                          and reduces_position(od, ctx.get('positions'))):
        f['max_order_usd'] = limits['max_order_usd']
    if side != 'sell' and est is not None:
        f['daily_after_usd'] = float(ctx.get('daily_used_usd') or 0) + est
        f['max_daily_usd'] = limits['max_daily_usd']
    positions = ctx.get('positions') or []
    pos = next((p for p in positions if str(p.get('symbol') or '').upper().replace('/', '') == sym.replace('/', '')),
               None)
    pos_mv = float((pos or {}).get('market_value') or 0)
    pos_qty = float((pos or {}).get('qty') or 0)
    equity = acct.get('equity')
    if side == 'buy':
        f['needs_funds'] = True
        f['available_usd'] = _available(acct, mandate, asset_class(sym) == 'crypto')
        f['max_position_pct'] = limits['max_position_pct']
        if equity and float(equity) > 0 and est is not None:
            after = (pos_mv + est) / float(equity) * 100.0
            mx = limits['max_position_pct']
            f['position_pct_after'] = after if after > mx + POSITION_TOL else min(after, mx)
        hwm = cl.get('hwm_equity')
        if hwm and equity is not None and float(hwm) > 0:
            f['drawdown_pct'] = max(0.0, (float(hwm) - float(equity)) / float(hwm) * 100.0)
            f['max_drawdown_pct'] = limits['max_drawdown_stop_pct']
    elif side == 'sell':
        if not pos:
            short = True
        elif od.get('qty') is not None:
            short = not (float(od['qty']) <= pos_qty + 1e-9)
        else:
            short = not (est is not None and est <= pos_mv * 1.001)
        f['short_sale'] = short
    if od.get('order_type') == 'limit' and od.get('limit_price'):
        lp, ref = _num(od.get('limit_price')), _num(ctx.get('ref_price'))
        f['ref_price_known'] = bool(ref and ref > 0)
        if ref and ref > 0:
            f['limit_dev_pct'] = (lp - ref) / ref * 100.0
            f['max_limit_dev_pct'] = LIMIT_DEVIATION_PCT
            f['min_limit_dev_pct'] = -LIMIT_DEVIATION_PCT
    if asset_class(sym) == 'us_equity' and valid_symbol(sym):
        f['market_open'] = ctx.get('market_open') is not False
    for k, v in (extra or {}).items():
        if v is not None:
            f[k] = v
    return f
