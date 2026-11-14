"""brokerage/sleeves.py — VARIAS CARTERAS sobre UNA cuenta de Alpaca (docs/CARTERAS_Y_AGENTES.md, fase 2).

Decisión de Fabrizio (2026-11-10): «todas en 1 cuenta Alpaca» — Khipus lleva la contabilidad de cada cartera.

    · Cartera = nombre + objetivo + perfil + efectivo ASIGNADO (broker_sleeves).
    · Sus posiciones y su caja salen SOLO de sus órdenes ejecutadas (broker_orders.meta.sleeve_id, filled_qty ×
      filled_avg_price). Lo que no está en ninguna cartera es la «Principal» (cuenta − suma de carteras).
    · Antes de CADA orden con cartera, `check_order` exige: comprar ≤ su efectivo disponible (descontando compras aún
      abiertas) y vender ≤ lo que ES SUYO. Si no cumple, la orden no nace (no hay decisión ni fila).
    · Alta, cambio y archivo = policy.change 'broker.sleeve' en el libro (misma transacción). El dinero sigue saliendo
      SOLO por brokerage.service (preview_order → confirm_order); este módulo no habla con Alpaca.

API (PIN, cuenta de la casa): GET/POST /api/trade/sleeves · PATCH /api/trade/sleeves/<id> ·
POST /api/trade/sleeves/<id>/archive.
"""
import logging

from flask import Blueprint, jsonify, request

from core.http import rate_limit
from core.pin import require_pin as _trade_auth

log = logging.getLogger('khipu')

sleeves_bp = Blueprint('broker_sleeves', __name__)

OPEN_STATUSES = ('previewed', 'pending_approval', 'approved', 'submitted', 'accepted', 'new', 'partially_filled')
EPS = 1e-9
MAX_SLEEVES = 20


def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _orders(session, client_id, sleeve_id):
    from brokerage.models import BrokerOrder
    from sqlalchemy import text
    return (session.query(BrokerOrder)
            .filter(BrokerOrder.client_id == client_id,
                    text("broker_orders.meta->>'sleeve_id' = :sid")).params(sid=sleeve_id).all())


def ledger(session, sleeve):
    """{'cash', 'reserved', 'available', 'holdings': {sym: qty}, 'cost': {sym: usd}} de UNA cartera."""
    cash = float(sleeve.alloc_usd or 0.0)
    reserved = 0.0
    holdings, cost = {}, {}
    for o in _orders(session, sleeve.client_id, sleeve.id):
        fq = _f(o.filled_qty) or 0.0
        fp = _f(o.filled_avg_price) or _f(o.est_price) or 0.0
        if fq > EPS:
            if o.side == 'buy':
                cash -= fq * fp
                holdings[o.symbol] = holdings.get(o.symbol, 0.0) + fq
                cost[o.symbol] = cost.get(o.symbol, 0.0) + fq * fp
            else:
                cash += fq * fp
                q0 = holdings.get(o.symbol, 0.0)
                if q0 > EPS:
                    cost[o.symbol] = cost.get(o.symbol, 0.0) * max(0.0, (q0 - fq) / q0)
                holdings[o.symbol] = q0 - fq
        if o.side == 'buy' and o.status in OPEN_STATUSES:
            est = _f(o.est_usd) or ((_f(o.notional) or 0.0))
            reserved += max(0.0, est - fq * fp)
    holdings = {k: round(v, 9) for k, v in holdings.items() if v > EPS}
    cost = {k: round(v, 2) for k, v in cost.items() if k in holdings}
    return {'cash': round(cash, 2), 'reserved': round(reserved, 2), 'available': round(cash - reserved, 2),
            'holdings': holdings, 'cost': cost}


def _get(session, client_id, sleeve_id):
    from brokerage.models import BrokerSleeve
    return (session.query(BrokerSleeve)
            .filter(BrokerSleeve.client_id == client_id, BrokerSleeve.id == str(sleeve_id or '')[:40]).first())


def check_order(session, client_id, sleeve_id, symbol, side, notional=None, qty=None, price=None):
    """→ (ok, motivo_es, motivo_en). La cartera debe existir, estar activa y alcanzar (efectivo / acciones)."""
    sl = _get(session, client_id, sleeve_id)
    if sl is None:
        return False, 'esa cartera no existe en esta cuenta', 'that portfolio does not exist in this account'
    if sl.status != 'active':
        return False, f'la cartera «{sl.name}» está archivada', f'portfolio “{sl.name}” is archived'
    lg = ledger(session, sl)
    px = _f(price)
    if side == 'buy':
        need = _f(notional) if _f(notional) else ((_f(qty) or 0.0) * (px or 0.0))
        if not need:
            return False, 'no se pudo estimar el monto de la compra', 'could not estimate the purchase amount'
        if need > lg['available'] + 0.01:
            return (False, f'la cartera «{sl.name}» tiene US${lg["available"]:,.2f} disponibles y la compra es de '
                           f'US${need:,.2f}', f'portfolio “{sl.name}” has US${lg["available"]:,.2f} available and the '
                           f'purchase is US${need:,.2f}')
        return True, f'cartera «{sl.name}»: alcanza el efectivo', f'portfolio “{sl.name}”: enough cash'
    return _check_sell(sl, lg, symbol, notional, qty, px)


def _check_sell(sl, lg, symbol, notional, qty, price):
    have = lg['holdings'].get(symbol, 0.0)
    q = _f(qty) if _f(qty) else ((_f(notional) or 0.0) / _f(price) if _f(price) else None)
    if q is None:
        return False, 'no se pudo estimar la cantidad a vender', 'could not estimate the quantity to sell'
    if q > have + 1e-6:
        return (False, f'la cartera «{sl.name}» tiene {have:g} de {symbol} y la venta es de {q:g}',
                f'portfolio “{sl.name}” holds {have:g} of {symbol} and the sale is {q:g}')
    return True, '', ''


def _view(session, sl, prices):
    lg = ledger(session, sl)
    value = lg['cash']
    pos = []
    for sym, q in sorted(lg['holdings'].items()):
        px = _f(prices.get(sym))
        mv = round(q * px, 2) if px else None
        if mv is not None:
            value += mv
        pos.append({'symbol': sym, 'qty': q, 'cost_usd': lg['cost'].get(sym), 'price': px, 'market_value': mv})
    return {'id': sl.id, 'name': sl.name, 'objective': sl.objective, 'risk_profile': sl.risk_profile,
            'alloc_usd': round(float(sl.alloc_usd or 0), 2), 'cash_usd': lg['cash'], 'reserved_usd': lg['reserved'],
            'available_usd': lg['available'], 'positions': pos, 'value_usd': round(value, 2),
            'pnl_usd': round(value - float(sl.alloc_usd or 0), 2), 'status': sl.status}


def list_view(session, client_id, account=None, positions=None):
    """Carteras activas + la «Principal» (lo no asignado) con valores en vivo de la cuenta."""
    from brokerage.models import BrokerSleeve
    prices = {str(p.get('symbol')): _f(p.get('current_price')) for p in positions or [] if isinstance(p, dict)}
    rows = (session.query(BrokerSleeve).filter(BrokerSleeve.client_id == client_id, BrokerSleeve.status == 'active')
            .order_by(BrokerSleeve.created_at).all())
    items = [_view(session, r, prices) for r in rows]
    eq = _f((account or {}).get('equity'))
    cash = _f((account or {}).get('cash'))
    main = None
    if eq is not None:
        main = {'id': None, 'name': 'Principal', 'value_usd': round(eq - sum(i['value_usd'] for i in items), 2),
                'cash_usd': round((cash or 0.0) - sum(i['cash_usd'] for i in items), 2)}
    # conciliación: lo que las carteras dicen tener no puede superar lo que hay en Alpaca
    have = {}
    for p in positions or []:
        if isinstance(p, dict):
            have[str(p.get('symbol'))] = _f(p.get('qty')) or 0.0
    issues = []
    for sym in {x['symbol'] for i in items for x in i['positions']}:
        claimed = sum(x['qty'] for i in items for x in i['positions'] if x['symbol'] == sym)
        if claimed > have.get(sym, 0.0) + 1e-6:
            issues.append({'symbol': sym, 'claimed': claimed, 'in_account': have.get(sym, 0.0)})
    return {'items': items, 'main': main, 'reconcile_issues': issues}


def unallocated_cash(session, client_id, account_cash):
    from brokerage.models import BrokerSleeve
    rows = (session.query(BrokerSleeve).filter(BrokerSleeve.client_id == client_id, BrokerSleeve.status == 'active')
            .all())
    return round(float(account_cash or 0.0) - sum(ledger(session, r)['cash'] for r in rows), 2)


def _snap(sl):
    return {'name': sl.name, 'objective': sl.objective, 'risk_profile': sl.risk_profile,
            'alloc_usd': round(float(sl.alloc_usd or 0), 2), 'status': sl.status}


def _decide(session, sl, before, actor):
    from brokerage import service as svc
    from core import decision_sites
    decision_sites.policy_change(session, 'broker.sleeve', before, _snap(sl),
                                 subject={'client_id': sl.client_id, 'sleeve_id': sl.id}, p=svc._principal(actor))


def _clean_text(v, n):
    s = str(v or '').strip()
    return s[:n] if s else None


def create(session, client_id, name, objective=None, alloc_usd=0.0, risk_profile='moderado', actor='ui',
           account_cash=None):
    from brokerage.models import BrokerSleeve
    nm = _clean_text(name, 80)
    if not nm:
        return {'ok': False, 'code': 'bad_request', 'error': 'falta el nombre', 'error_en': 'name is required'}
    if nm.lower() == 'principal':
        return {'ok': False, 'code': 'bad_request', 'error': '«Principal» es el nombre de lo no asignado',
                'error_en': '“Principal” is reserved for the unallocated part'}
    q = session.query(BrokerSleeve).filter(BrokerSleeve.client_id == client_id, BrokerSleeve.status == 'active')
    if q.count() >= MAX_SLEEVES:
        return {'ok': False, 'code': 'too_many', 'error': f'máximo {MAX_SLEEVES} carteras',
                'error_en': f'at most {MAX_SLEEVES} portfolios'}
    if any(r.name.lower() == nm.lower() for r in q.all()):
        return {'ok': False, 'code': 'name_taken', 'error': 'ya hay una cartera con ese nombre',
                'error_en': 'a portfolio with that name already exists'}
    amt = _f(alloc_usd)
    if amt is None or amt < 0:
        return {'ok': False, 'code': 'bad_request', 'error': 'monto inválido', 'error_en': 'invalid amount'}
    if account_cash is not None and amt > unallocated_cash(session, client_id, account_cash) + 0.01:
        return {'ok': False, 'code': 'not_enough_cash',
                'error': f'solo hay US${unallocated_cash(session, client_id, account_cash):,.2f} sin asignar',
                'error_en': f'only US${unallocated_cash(session, client_id, account_cash):,.2f} is unallocated'}
    sl = BrokerSleeve(client_id=client_id, name=nm, objective=_clean_text(objective, 600), alloc_usd=round(amt, 2),
                      risk_profile=(risk_profile if risk_profile in ('conservador', 'moderado', 'agresivo')
                                    else 'moderado'), created_by=str(actor)[:120])
    session.add(sl)
    session.flush()
    _decide(session, sl, None, actor)
    return {'ok': True, 'sleeve': _snap(sl) | {'id': sl.id}}


def update(session, client_id, sleeve_id, patch, actor='ui', account_cash=None):
    sl = _get(session, client_id, sleeve_id)
    if sl is None or sl.status != 'active':
        return {'ok': False, 'code': 'not_found', 'error': 'cartera no encontrada', 'error_en': 'portfolio not found'}
    before = _snap(sl)
    patch = patch if isinstance(patch, dict) else {}
    if 'name' in patch:
        nm = _clean_text(patch.get('name'), 80)
        if not nm or nm.lower() == 'principal':
            return {'ok': False, 'code': 'bad_request', 'error': 'nombre inválido', 'error_en': 'invalid name'}
        sl.name = nm
    if 'objective' in patch:
        sl.objective = _clean_text(patch.get('objective'), 600)
    if patch.get('risk_profile') in ('conservador', 'moderado', 'agresivo'):
        sl.risk_profile = patch['risk_profile']
    if 'alloc_usd' in patch:
        new = _f(patch.get('alloc_usd'))
        if new is None or new < 0:
            return {'ok': False, 'code': 'bad_request', 'error': 'monto inválido', 'error_en': 'invalid amount'}
        delta = new - float(sl.alloc_usd or 0)
        lg = ledger(session, sl)
        if delta < 0 and -delta > lg['available'] + 0.01:      # retirar más de lo libre de la cartera: no
            return {'ok': False, 'code': 'not_enough_cash',
                    'error': f'la cartera solo tiene US${lg["available"]:,.2f} libres para retirar',
                    'error_en': f'the portfolio only has US${lg["available"]:,.2f} free to withdraw'}
        if delta > 0 and account_cash is not None and delta > unallocated_cash(session, client_id, account_cash) + 0.01:
            return {'ok': False, 'code': 'not_enough_cash', 'error': 'no hay tanto efectivo sin asignar',
                    'error_en': 'there is not that much unallocated cash'}
        sl.alloc_usd = round(new, 2)
    session.flush()
    _decide(session, sl, before, actor)
    return {'ok': True, 'sleeve': _snap(sl) | {'id': sl.id}}


def archive(session, client_id, sleeve_id, actor='ui'):
    sl = _get(session, client_id, sleeve_id)
    if sl is None or sl.status != 'active':
        return {'ok': False, 'code': 'not_found', 'error': 'cartera no encontrada', 'error_en': 'portfolio not found'}
    lg = ledger(session, sl)
    if lg['holdings'] or lg['reserved'] > 0.01:
        return {'ok': False, 'code': 'not_empty',
                'error': 'vende sus posiciones (o espera sus órdenes abiertas) antes de archivarla',
                'error_en': 'sell its positions (or wait for its open orders) before archiving it'}
    before = _snap(sl)
    sl.status = 'archived'
    session.flush()
    _decide(session, sl, before, actor)
    return {'ok': True}


# ── API (cuenta de la casa, con PIN) ─────────────────────────────────────────────────────────────────────────────
def _db():
    try:
        from ontology.db import ontology_available
        return ontology_available()
    except Exception:  # noqa: BLE001
        return False


def _no_db():
    return jsonify({'error': 'Las carteras con dinero necesitan la base de datos', 'error_en': 'Money portfolios need '
                    'the database', 'code': 'db_unavailable'}), 503


def _http(res):
    if res.get('ok'):
        return jsonify(res), 200
    code = res.get('code') or 'bad_request'
    return jsonify(res), {'not_found': 404, 'name_taken': 409, 'not_empty': 409}.get(code, 400)


def _actor():
    try:
        from core import identity
        p = identity.principal()
        return p.id if p else 'ui'
    except Exception:  # noqa: BLE001
        return 'ui'


@sleeves_bp.route('/api/trade/sleeves', methods=['GET'])
@rate_limit(30, 60)
@_trade_auth
def sleeves_list():
    if not _db():
        return _no_db()
    from brokerage import service as svc
    from ontology.db import session_scope
    with session_scope() as s:
        svc.ensure_house_client(s)
        snap = svc.account_snapshot(s, svc.HOUSE_ID)
        out = list_view(s, svc.HOUSE_ID, snap.get('account') or {}, snap.get('positions') or [])
        acc = snap.get('account') or {}
        out['unallocated_cash_usd'] = (unallocated_cash(s, svc.HOUSE_ID, acc.get('cash'))
                                       if acc.get('cash') is not None else None)
        out['paper'] = (snap.get('client') or {}).get('mode') == 'paper' if snap.get('client') else None
        out['account_ok'] = bool(snap.get('ok'))
    return jsonify(out)


@sleeves_bp.route('/api/trade/sleeves', methods=['POST'])
@rate_limit(10, 60)
@_trade_auth
def sleeves_create():
    if not _db():
        return _no_db()
    data = request.get_json(silent=True) or {}
    from brokerage import service as svc
    from ontology.db import session_scope
    with session_scope() as s:
        svc.ensure_house_client(s)
        snap = svc.account_snapshot(s, svc.HOUSE_ID)
        cash = (snap.get('account') or {}).get('cash')
        if cash is None:
            return jsonify({'error': 'no se pudo leer la cuenta del bróker', 'error_en': 'could not read the broker '
                            'account', 'code': 'broker_error'}), 502
        res = create(s, svc.HOUSE_ID, data.get('name'), data.get('objective'), data.get('alloc_usd') or 0,
                     data.get('risk_profile') or 'moderado', actor=_actor(), account_cash=cash)
    return _http(res)


@sleeves_bp.route('/api/trade/sleeves/<sleeve_id>', methods=['PATCH'])
@rate_limit(20, 60)
@_trade_auth
def sleeves_update(sleeve_id):
    if not _db():
        return _no_db()
    data = request.get_json(silent=True) or {}
    from brokerage import service as svc
    from ontology.db import session_scope
    with session_scope() as s:
        cash = None
        if 'alloc_usd' in data:
            cash = (svc.account_snapshot(s, svc.HOUSE_ID).get('account') or {}).get('cash')
        res = update(s, svc.HOUSE_ID, sleeve_id, data, actor=_actor(), account_cash=cash)
    return _http(res)


@sleeves_bp.route('/api/trade/sleeves/<sleeve_id>/archive', methods=['POST'])
@rate_limit(10, 60)
@_trade_auth
def sleeves_archive(sleeve_id):
    if not _db():
        return _no_db()
    from brokerage import service as svc
    from ontology.db import session_scope
    with session_scope() as s:
        res = archive(s, svc.HOUSE_ID, sleeve_id, actor=_actor())
    return _http(res)
