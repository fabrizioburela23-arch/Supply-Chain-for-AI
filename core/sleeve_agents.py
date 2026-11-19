"""core/sleeve_agents.py — UN AGENTE POR CARTERA (docs/CARTERAS_Y_AGENTES.md fase 3, 2026-11-19).

Fabrizio: «tienes que poder programar agentes» + «más simple por fuera, más capaz por dentro». Cada cartera
(brokerage/sleeves) puede tener su agente, PROGRAMADO EN PALABRAS («compra chips de memoria cuando caigan 15 % y vende
si pierde 8 %»): la IA traduce el texto a una configuración ACOTADA (los mismos límites que el agente de la cuenta) que la
persona aprueba con su PIN. Nada de código libre.

Cómo corre: dentro del hilo del agente de trading (core/trading_agent: el reloj de la app no llama a la IA). Cada
vuelta del agente revisa las carteras con agente encendido y vencido su intervalo. Por cartera:
  · stop-loss: una posición que cae más que su stop → vender todo (auto) o proponer la venta (manual);
  · por cada acción de SU universo: el mismo análisis del agente (técnico real + convicción + tono + IA) y su guarda;
    regla extra «comprar solo en caídas» (buy_on_dip_pct: a X % o más bajo su máximo de 52 semanas);
  · compra ≤ efectivo libre de la cartera y ≤ su tope por posición (% del VALOR de la cartera); vende solo lo suyo;
  · AUTO solo en cuenta de PAPEL (con dinero real cae a manual: propone y la persona toca); toda orden por el camino
    único (trading_agent._agent_place → brokerage.service.house_order con sleeve_id → sus controles).
"""
import logging
import re
import threading
import time

log = logging.getLogger('khipu')

DEFAULT = {'enabled': False, 'mode': 'manual', 'universe': [], 'max_pos_pct': 20.0, 'stop_loss_pct': 8.0,
           'min_confidence': 65, 'interval_min': 60, 'buy_on_dip_pct': 0.0, 'rules': ''}
BOUNDS = {'max_pos_pct': (1.0, 100.0), 'stop_loss_pct': (0.5, 50.0), 'min_confidence': (50, 100),
          'interval_min': (15, 1440), 'buy_on_dip_pct': (0.0, 80.0)}
_LAST = {}            # sleeve_id → último ciclo (epoch)
_LOCK = threading.Lock()


def _num(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def clean_config(raw, safe_ticker=None):
    """dict cualquiera → configuración acotada + avisos. Nunca lanza."""
    raw = raw if isinstance(raw, dict) else {}
    out, notes = dict(DEFAULT), []
    out['enabled'] = bool(raw.get('enabled', False))
    out['mode'] = 'auto' if str(raw.get('mode') or '').lower() == 'auto' else 'manual'
    for k, (lo, hi) in BOUNDS.items():
        if raw.get(k) is None or raw.get(k) == '':
            continue
        x = _num(raw.get(k))
        if x is None:
            notes.append(f'{k}: valor inválido, uso {DEFAULT[k]}')
            continue
        y = min(hi, max(lo, x))
        if y != x:
            notes.append(f'{k}: {x:g} fuera de rango, uso {y:g}')
        out[k] = int(y) if k in ('min_confidence', 'interval_min') else round(y, 2)
    uni, bad = [], []
    for t in list(raw.get('universe') or [])[:30]:
        s = (safe_ticker(t) if safe_ticker else str(t or '').strip().upper()) or ''
        if s and re.fullmatch(r'[A-Z][A-Z0-9.\-/]{0,11}', s) and s not in uni:
            uni.append(s)
        elif t:
            bad.append(str(t)[:16])
    out['universe'] = uni[:20]
    if bad:
        notes.append('descartados: ' + ', '.join(bad))
    out['rules'] = str(raw.get('rules') or '')[:500]
    return out, notes


PARSE_SYSTEM = (
    'Eres el programador de agentes de Khipus. Conviertes lo que la persona quiere que haga el agente de UNA cartera en '
    'JSON con EXACTAMENTE estas claves: universe (lista de tickers de EE.UU., máx. 20; si nombra un sector, elige sus '
    'empresas más grandes), max_pos_pct (tope por acción, % del valor de la cartera, 1-100), stop_loss_pct (venta si '
    'una posición pierde ese %, 0.5-50), min_confidence (50-100; «conservador» 75, «normal» 65, «agresivo» 55), '
    'interval_min (cada cuántos minutos revisa, 15-1440), buy_on_dip_pct (comprar solo si está al menos ese % bajo su '
    'máximo de 52 semanas; 0 = sin condición), mode ("manual" = propone y la persona confirma, "auto" = opera solo en '
    'papel), summary_es (una frase simple de lo que hará). Si algo no se dice, usa: max_pos_pct 20, stop_loss_pct 8, '
    'min_confidence 65, interval_min 60, buy_on_dip_pct 0, mode "manual". SOLO el JSON.')


def parse_text(text, lang='es'):
    """Texto en palabras → (config, resumen, avisos). La IA solo PROPONE; nada se guarda aquí."""
    from core import ai as _ai
    from core.http import _safe_ticker
    t = str(text or '').strip()[:800]
    if not t:
        return None, '', ['texto vacío']
    try:
        data, _m = _ai._ai_json(PARSE_SYSTEM, f'LO QUE QUIERE LA PERSONA:\n{t}', 600, 'fast')
    except Exception as e:  # noqa: BLE001
        return None, '', [f'la IA no pudo leerlo ({type(e).__name__})']
    if not isinstance(data, dict):
        return None, '', ['la IA no devolvió una configuración']
    cfg, notes = clean_config(dict(data, enabled=True, rules=t), safe_ticker=_safe_ticker)
    if not cfg['universe']:
        notes.append('sin acciones: dile qué empresas o sector seguir')
    return cfg, str(data.get('summary_es') or '')[:300], notes


def describe(cfg, lang='es'):
    """Resumen legible (sin IA) de una configuración."""
    if not cfg:
        return ''
    en = lang == 'en'
    u = ', '.join(cfg.get('universe') or []) or ('—')
    dip = cfg.get('buy_on_dip_pct') or 0
    if en:
        return (f"Watches {u} every {cfg['interval_min']} min · buys{' only after a ' + format(dip, 'g') + '% drop from the high' if dip else ''} "
                f"up to {cfg['max_pos_pct']:g}% per stock · sells if one loses {cfg['stop_loss_pct']:g}% · "
                f"{'trades by itself (paper)' if cfg['mode'] == 'auto' else 'proposes and you confirm'}")
    return (f"Vigila {u} cada {cfg['interval_min']} min · compra{' solo tras caer ' + format(dip, 'g') + ' % desde su máximo' if dip else ''} "
            f"hasta {cfg['max_pos_pct']:g} % por acción · vende si una pierde {cfg['stop_loss_pct']:g} % · "
            f"{'opera solo (papel)' if cfg['mode'] == 'auto' else 'propone y tú confirmas'}")


# ── el ciclo (lo llama el hilo del agente) ───────────────────────────────────────────────────────────────────────
def _due(sid, cfg, now):
    with _LOCK:
        last = _LAST.get(sid)
        if last is not None and now - last < cfg['interval_min'] * 60:
            return False
        _LAST[sid] = now
        return True


def run_due(now=None):
    """Corre los agentes de cartera vencidos. → nº de carteras revisadas. Nunca lanza."""
    try:
        from ontology.db import ontology_available
        if not ontology_available():
            return 0
        from brokerage import service as svc
        from brokerage.models import BrokerSleeve
        from ontology.db import session_scope
        now = time.time() if now is None else now
        with session_scope() as s:
            rows = (s.query(BrokerSleeve).filter(BrokerSleeve.client_id == svc.HOUSE_ID,
                                                 BrokerSleeve.status == 'active').all())
            work = [(r.id, r.name, cfg) for r in rows
                    for cfg in [clean_config(getattr(r, 'agent', None) or {})[0]] if cfg['enabled']]
        n = 0
        for sid, name, cfg in work:
            if _due(sid, cfg, now):
                try:
                    run_one(sid, name, cfg)
                except Exception as e:  # noqa: BLE001 — una cartera nunca tumba a las demás
                    log.warning('agente de cartera %s: %s', name, type(e).__name__)
                n += 1
        return n
    except Exception as e:  # noqa: BLE001
        log.warning('agentes de cartera: %s', type(e).__name__)
        return 0


def _log(name, msg, level='info', **extra):
    from core import trading_agent as ta
    ta._agent_log(dict({'level': level, 'msg': f'💼 {name}: {msg}'}, **extra))


def _price(ticker):
    try:
        from core.quotes import fetch_quotes_live
        q = ((fetch_quotes_live([ticker]) or {}).get('quotes') or {}).get(ticker) or {}
        return _num(q.get('live') or q.get('close')) or 0.0, _num(q.get('prev')) or 0.0
    except Exception:  # noqa: BLE001
        return 0.0, 0.0


def run_one(sleeve_id, name, cfg):
    """Un ciclo del agente de UNA cartera."""
    from brokerage import sleeves as sv
    from core import trading_agent as ta
    from ontology.db import session_scope
    S = ta._S
    paper = bool(S._paper())
    auto = cfg['mode'] == 'auto' and paper            # dinero real: nunca solo
    with session_scope() as s:
        from brokerage.models import BrokerSleeve
        sl = s.query(BrokerSleeve).filter(BrokerSleeve.id == sleeve_id).first()
        if sl is None or sl.status != 'active':
            return
        lg = sv.ledger(s, sl)
    prices = {}
    value = lg['cash']
    for sym, q in lg['holdings'].items():
        px, _p = _price(sym)
        prices[sym] = px
        value += q * px if px else 0.0
    acted = 0
    # 1) stop-loss de SUS posiciones
    for sym, q in lg['holdings'].items():
        px, cost = prices.get(sym) or 0.0, lg['cost'].get(sym) or 0.0
        if not (px and cost and q):
            continue
        avg = cost / q
        if px <= avg * (1 - cfg['stop_loss_pct'] / 100):
            why = f'stop-loss: {sym} {px:.2f} ≤ {avg * (1 - cfg["stop_loss_pct"] / 100):.2f}'
            if auto:
                try:
                    ta._agent_order({'symbol': sym, 'side': 'sell', 'qty': float(S._num_str(q)),
                                     'time_in_force': 'gtc' if '/' in sym else 'day'}, 'agent_order',
                                    {'symbol': sym, 'side': 'sell', 'qty': q, 'sleeve_id': sleeve_id},
                                    checks_mode='house_reduce', sleeve_id=sleeve_id)
                    _log(name, f'🛑 vendí {sym} ({why})', 'success')
                except Exception as e:  # noqa: BLE001
                    _log(name, f'no se pudo vender {sym}: {str(e)[:120]}', 'error')
            else:
                ta._signal_add(sym, 'sell', qty=float(S._num_str(q)), price=px, confidence=100, reason=why,
                               kind='stop', sleeve_id=sleeve_id, sleeve_name=name)
                _log(name, f'🛑 propongo vender {sym} ({why})', 'warn')
            acted += 1
    # 2) entradas / salidas según el análisis del agente
    for ticker in cfg['universe']:
        if not ta._AGENT.get('running'):
            break
        price, prev = _price(ticker)
        if price <= 0:
            continue
        facts = ta._agent_context(ticker)
        raw = ta._agent_analyze(ticker, price, prev, ta._agent_tone(ticker), facts=facts)
        action, conf, reason, size_pct = ta._agent_clean_analysis(raw)
        if action == 'hold' or conf < cfg['min_confidence']:
            continue
        guard = ta._agent_guard(action, facts)
        tech = (facts or {}).get('tech') or {}
        if not guard and action == 'buy' and cfg['buy_on_dip_pct'] > 0:
            dd = _num(tech.get('pct_from_52w_high'))
            if dd is None or dd > -cfg['buy_on_dip_pct']:
                guard = f'regla: comprar solo {cfg["buy_on_dip_pct"]:g} % bajo el máximo (está a {dd} %)'
        have = lg['holdings'].get(ticker, 0.0)
        if not guard and action == 'sell' and have <= 0:
            guard = 'la cartera no la tiene'
        pos_mv = have * price
        cap = value * cfg['max_pos_pct'] / 100
        if not guard and action == 'buy':
            notional = min(max(1.0, value * max(size_pct, 1) / 100), cap - pos_mv, lg['available'], S.MAX_ORDER_USD)
            if notional < 1:
                guard = 'sin efectivo libre o ya en su tope'
        if guard:
            _log(name, f'{ticker}: {action} ({conf}) descartada — {guard}')
            continue
        if action == 'buy':
            order = {'notional': round(notional, 2)}
        else:
            order = {'qty': float(S._num_str(have))}
        if auto:
            try:
                if action == 'buy':
                    ta._agent_place(ticker, 'buy', order['notional'], None, sleeve_id=sleeve_id)
                else:
                    ta._agent_order({'symbol': ticker, 'side': 'sell', 'qty': order['qty'],
                                     'time_in_force': 'gtc' if '/' in ticker else 'day'}, 'agent_order',
                                    {'symbol': ticker, 'side': 'sell', 'qty': order['qty'], 'sleeve_id': sleeve_id},
                                    checks_mode='house_reduce', sleeve_id=sleeve_id)
                _log(name, f'✅ {"compré" if action == "buy" else "vendí"} {ticker} — {reason}', 'success')
                if action == 'buy':
                    lg['available'] -= order['notional']
            except Exception as e:  # noqa: BLE001
                _log(name, f'no se pudo operar {ticker}: {str(e)[:120]}', 'error')
        else:
            ta._signal_add(ticker, action, price=price, confidence=conf, reason=reason, facts=facts,
                           sleeve_id=sleeve_id, sleeve_name=name, **order)
            _log(name, f'💡 propongo {"comprar" if action == "buy" else "vender"} {ticker} — {reason}')
        acted += 1
    _log(name, f'✓ revisión terminada ({acted} acción/es)')
