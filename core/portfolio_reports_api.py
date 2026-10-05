"""core/portfolio_reports_api.py — /api/portfolio-report/* y /api/news/portfolio.

Reportes de cartera (core/portfolio_report), su historial y su programación
(diario / semanal / mensual), noticias de tu cartera (core/news_feed) y
"Pregúntale a tu cartera" (el cerebro de Khipu con tu cartera y tu último
reporte como contexto — estilo NotebookLM).

Dueño: cabecera X-Khipu-Owner = llave aleatoria del navegador (≥ 16 caracteres;
la genera engine/pfcommittee.js en localStorage 'kh_owner_key'). En la base se
guarda solo su SHA-256: sin esa llave nadie puede listar ni leer tus reportes.

Programación: un hilo revisa cada 20 min las carteras con reporte automático.
  daily   → después de las 21:00 UTC (cierre de EE.UU.), si el último tiene > 20 h
  weekly  → viernes después de las 21:00 UTC, si el último tiene > 6 días
  monthly → el día 1 (después de las 06:00 UTC) cubriendo el mes anterior
Cada reporte gasta IA solo en su resumen (y respeta los límites de 💰 Gasto IA).
"""
import hashlib
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request

from core.http import rate_limit

log = logging.getLogger('khipu')
portfolio_reports_bp = Blueprint('portfolio_reports', __name__)
SCHEDULES = ('off', 'daily', 'weekly', 'monthly')
KIND_PERIOD = {'daily': 'day', 'weekly': 'week', 'monthly': 'month', 'manual': None}
_STATE = {'thread': None}


def _owner():
    k = (request.headers.get('X-Khipu-Owner') or '').strip()
    if len(k) < 16 or len(k) > 128:
        return None
    return hashlib.sha256(k.encode()).hexdigest()


def _db():
    from ontology.db import ontology_available
    return ontology_available()


def _need_owner():
    return jsonify({'error': 'falta la llave del navegador (X-Khipu-Owner)', 'error_en': 'missing browser key (X-Khipu-Owner)'}), 401


def _no_db():
    return jsonify({'error': 'Guardar reportes necesita la base de datos (DATABASE_URL).',
                    'error_en': 'Saving reports needs the database (DATABASE_URL).'}), 503


def _clean_positions(raw):
    out = []
    for p in (raw or [])[:30]:
        if not isinstance(p, dict):
            continue
        sym = ''.join(ch for ch in str(p.get('symbol') or '') if ch.isalnum() or ch in '.-^=').upper()[:15]
        try:
            sh = float(p.get('shares'))
        except (TypeError, ValueError):
            continue
        if not sym or not sh > 0:
            continue
        cost = p.get('cost_usd')
        try:
            cost = float(cost) if cost not in (None, '') else None
        except (TypeError, ValueError):
            cost = None
        out.append({'id': str(p.get('id') or '')[:120] or None, 'symbol': sym, 'label': str(p.get('label') or sym)[:80],
                    'shares': sh, 'cost_usd': cost})
    return out


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _title(kind, rep, lang, name=None):
    es = lang != 'en'
    p = rep['performance']
    k = {'manual': ('Reporte', 'Report'), 'daily': ('Reporte diario', 'Daily report'),
         'weekly': ('Reporte semanal', 'Weekly report'), 'monthly': ('Reporte mensual', 'Monthly report')}[kind]
    return f"{k[0] if es else k[1]}{' · ' + name if name else ''} · {p['period_from']} → {p['period_to']}"[:200]


def _store(owner, kind, rep, watch_id=None, name=None):
    from ontology.db import session_scope
    from research.models import PortfolioReport
    with session_scope() as s:
        r = PortfolioReport(owner_hash=owner, watch_id=watch_id, kind=kind, title=_title(kind, rep, rep['lang'], name),
                            period_from=rep['performance']['period_from'], period_to=rep['performance']['period_to'],
                            summary=(rep.get('summary') or {}).get('text'), data=rep)
        s.add(r)
        s.flush()
        return r.id, r.title


@portfolio_reports_bp.route('/api/portfolio-report/generate', methods=['POST'])
@rate_limit(limit=40, window=3600)
def generate():
    from core import portfolio_report
    from core.ai_usage import ai_context
    body = request.get_json(silent=True) or {}
    lang = 'en' if str(body.get('lang', 'es')).lower().startswith('en') else 'es'
    pos = _clean_positions(body.get('positions'))
    if not pos:
        return jsonify({'ok': False, 'error': 'No hay posiciones cotizadas en esa cartera.',
                        'error_en': 'That portfolio has no listed positions.'}), 422
    with ai_context('reporte_cartera', str(body.get('actor') or '').strip()[:120] or None):
        rep = portfolio_report.build(pos, start_value=_f(body.get('start_value')), start_date=body.get('start_date'),
                                     period=str(body.get('period') or 'month'), profile=body.get('profile') or {},
                                     cash_usd=_f(body.get('cash_usd')) or 0.0, lang=lang)
    if not rep.get('ok'):
        return jsonify(rep), 422
    owner = _owner()
    if owner and _db() and body.get('save', True):
        try:
            rep['id'], rep['title'] = _store(owner, 'manual', rep, name=str(body.get('name') or '')[:60] or None)
        except Exception as e:  # noqa: BLE001 — sin guardar, el reporte igual se muestra
            log.warning('portfolio report store: %s', e)
    return jsonify(rep)


@portfolio_reports_bp.route('/api/portfolio-report/list')
@rate_limit(limit=240, window=3600)
def list_reports():
    owner = _owner()
    if not owner:
        return _need_owner()
    if not _db():
        return jsonify({'reports': [], 'unread': 0, 'available': False})
    from ontology.db import session_scope
    from research.models import PortfolioReport
    with session_scope() as s:
        q = s.query(PortfolioReport).filter(PortfolioReport.owner_hash == owner)
        # los análisis del comité (kind='committee') tienen su propia lista: ?kind=committee
        q = q.filter(PortfolioReport.kind == 'committee') if request.args.get('kind') == 'committee' \
            else q.filter(PortfolioReport.kind != 'committee')
        rows = (q.order_by(PortfolioReport.created_at.desc()).limit(60).all())
        out = []
        for r in rows:
            p = (r.data or {}).get('performance') or {}
            out.append({'id': r.id, 'title': r.title, 'kind': r.kind, 'read': r.read,
                        'created_at': r.created_at.isoformat() if r.created_at else None,
                        'period_from': r.period_from, 'period_to': r.period_to,
                        'change_pct': p.get('period_change_pct'), 'value_usd': p.get('value_now_usd'),
                        'summary': (r.summary or '')[:220]})
    return jsonify({'reports': out, 'unread': sum(1 for x in out if not x['read']), 'available': True})


@portfolio_reports_bp.route('/api/portfolio-report/<rid>', methods=['GET', 'DELETE'])
@rate_limit(limit=240, window=3600)
def one_report(rid):
    owner = _owner()
    if not owner:
        return _need_owner()
    if not _db():
        return _no_db()
    from ontology.db import session_scope
    from research.models import PortfolioReport
    with session_scope() as s:
        r = s.get(PortfolioReport, str(rid)[:40])
        if r is None or r.owner_hash != owner:
            return jsonify({'error': 'reporte no encontrado', 'error_en': 'report not found'}), 404
        if request.method == 'DELETE':
            s.delete(r)
            return jsonify({'ok': True})
        r.read = True
        return jsonify({**(r.data or {}), 'id': r.id, 'title': r.title, 'kind': r.kind,
                        'created_at': r.created_at.isoformat() if r.created_at else None})


@portfolio_reports_bp.route('/api/portfolio-report/watch', methods=['POST'])
@rate_limit(limit=60, window=3600)
def save_watch():
    """Programa (o apaga) los reportes automáticos de UNA cartera."""
    owner = _owner()
    if not owner:
        return _need_owner()
    if not _db():
        return _no_db()
    body = request.get_json(silent=True) or {}
    sched = str(body.get('schedule') or 'off')
    if sched not in SCHEDULES:
        return jsonify({'error': f'schedule debe ser uno de {SCHEDULES}', 'error_en': f'schedule must be one of {SCHEDULES}'}), 400
    key = str(body.get('source_key') or '').strip()[:80]
    pos = _clean_positions(body.get('positions'))
    if not key or (sched != 'off' and not pos):
        return jsonify({'error': 'falta la cartera o sus posiciones', 'error_en': 'missing portfolio or positions'}), 400
    from ontology.db import session_scope
    from research.models import PortfolioWatch
    with session_scope() as s:
        w = (s.query(PortfolioWatch).filter(PortfolioWatch.owner_hash == owner, PortfolioWatch.source_key == key).first())
        if w is None:
            w = PortfolioWatch(owner_hash=owner, source_key=key, name=str(body.get('name') or key)[:160])
            s.add(w)
        w.name = str(body.get('name') or w.name)[:160]
        w.owner_name = str(body.get('actor') or '')[:120] or w.owner_name
        if pos:
            w.positions = pos
        w.start_value_usd = _f(body.get('start_value'))
        w.start_date = str(body.get('start_date') or '')[:10] or w.start_date
        w.cash_usd = _f(body.get('cash_usd')) or 0.0
        w.profile = body.get('profile') if isinstance(body.get('profile'), dict) else (w.profile or {})
        w.schedule = sched
        w.updated_at = datetime.now(timezone.utc)
        s.flush()
        out = {'ok': True, 'id': w.id, 'schedule': w.schedule}
    _ensure_scheduler()
    return jsonify(out)


@portfolio_reports_bp.route('/api/portfolio-report/watches')
@rate_limit(limit=240, window=3600)
def list_watches():
    owner = _owner()
    if not owner:
        return _need_owner()
    if not _db():
        return jsonify({'watches': [], 'available': False})
    from ontology.db import session_scope
    from research.models import PortfolioWatch
    with session_scope() as s:
        rows = s.query(PortfolioWatch).filter(PortfolioWatch.owner_hash == owner).all()
        return jsonify({'available': True, 'watches': [{'id': w.id, 'source_key': w.source_key, 'name': w.name,
                                                        'schedule': w.schedule, 'n_positions': len(w.positions or []),
                                                        'last_report_at': w.last_report_at.isoformat() if w.last_report_at else None}
                                                       for w in rows]})


@portfolio_reports_bp.route('/api/news/portfolio', methods=['POST'])
@rate_limit(limit=120, window=3600)
def news_portfolio():
    from core import news_feed
    body = request.get_json(silent=True) or {}
    hold = [h for h in (body.get('holdings') or []) if isinstance(h, dict)][:20]
    lang = 'en' if str(body.get('lang', 'es')).lower().startswith('en') else 'es'
    try:
        days = int(body.get('days') or 7)
    except (TypeError, ValueError):
        days = 7
    return jsonify(news_feed.portfolio_news(
        [{'entity_id': str(h.get('id') or '')[:120] or None, 'label': str(h.get('label') or '')[:80],
          'symbol': str(h.get('symbol') or '')[:15] or None, 'weight_pct': _f(h.get('weight_pct'))} for h in hold],
        days=days, limit=30, lang=lang))


@portfolio_reports_bp.route('/api/portfolio-report/ask', methods=['POST'])
@rate_limit(limit=60, window=3600)
def ask():
    """"Pregúntale a tu cartera": el cerebro de Khipu con tu cartera + tu reporte como contexto."""
    from core import khipu_chat
    from core.ai_usage import ai_context
    body = request.get_json(silent=True) or {}
    q = str(body.get('question') or '').strip()
    if not q:
        return jsonify({'error': 'escribe una pregunta', 'error_en': 'type a question'}), 400
    lang = 'en' if str(body.get('lang', 'es')).lower().startswith('en') else 'es'
    pos = _clean_positions(body.get('positions'))
    notes = str(body.get('notes') or '')[:3500]
    rid = str(body.get('report_id') or '')[:40]
    owner = _owner()
    if rid and owner and _db():
        try:
            from ontology.db import session_scope
            from research.models import PortfolioReport
            with session_scope() as s:
                r = s.get(PortfolioReport, rid)
                if r is not None and r.owner_hash == owner:
                    notes = (notes + '\n' + _report_notes(r.data or {}))[:3500]
        except Exception as e:  # noqa: BLE001
            log.info('portfolio ask report: %s', type(e).__name__)
    ctx = {'portfolio': [{'symbol': p['symbol'], 'shares': p['shares']} for p in pos], 'portfolio_notes': notes,
           'tab': 'portfolio'}
    hist = body.get('history') if isinstance(body.get('history'), list) else []
    try:
        req = khipu_chat.validate_request({'message': q, 'history': hist, 'lang': lang})
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200]}), 400
    with ai_context('pregunta_cartera', str(body.get('actor') or '').strip()[:120] or None):
        out = khipu_chat.run_chat(req['message'], req['history'], lang, context=ctx, app=current_app._get_current_object())
    return jsonify(out)


def _report_notes(rep):
    p = rep.get('performance') or {}
    lines = [f"Reporte {p.get('period_from')}→{p.get('period_to')}: valor {p.get('value_now_usd')} USD, cambio "
             f"{p.get('period_change_pct')} % (S&P 500 {p.get('spy_period_pct')} %), desde el inicio {p.get('since_start_pct')} %."]
    for c in (rep.get('contributions') or [])[:8]:
        lines.append(f"{c['label']} ({c['symbol']}): {c['change_pct']} % en el periodo, aportó {c['contrib_usd']} USD, vale {c['value_usd']} USD.")
    adv = rep.get('advisor') or {}
    for a in (adv.get('actions') or [])[:4]:
        lines.append(f"Acción sugerida {a['id']}: {a['kind']} {a['label']} de {a['from_pct']} % a {a['to_pct']} % — {a['why_es']}")
    for n in (rep.get('news') or [])[:5]:
        lines.append(f"Noticia {n.get('published_at', '')[:10]} ({', '.join(n.get('holdings') or [])}): {n.get('title')}")
    return '\n'.join(lines)


# ── sincronización entre dispositivos ───────────────────────────────────────
SYNC_KEYS = ('kh_portfolios', 'kh_pf_active', 'kh_investor_profile', 'eco_pos')
SYNC_MAX_BYTES = 300_000


@portfolio_reports_bp.route('/api/user-state', methods=['GET', 'PUT'])
@rate_limit(limit=600, window=3600)
def user_state():
    """GET → {key: {value, updated_at}} · PUT {key, value, updated_at?} (último que escribe gana)."""
    owner = _owner()
    if not owner:
        return _need_owner()
    if not _db():
        return jsonify({'available': False, 'state': {}})
    import json as _json

    from ontology.db import session_scope
    from research.models import UserState
    if request.method == 'GET':
        with session_scope() as s:
            rows = s.query(UserState).filter(UserState.owner_hash == owner, UserState.key.in_(SYNC_KEYS)).all()
            return jsonify({'available': True, 'state': {r.key: {'value': r.value, 'updated_at': r.updated_at.isoformat()}
                                                         for r in rows}})
    body = request.get_json(silent=True) or {}
    key = str(body.get('key') or '')
    if key not in SYNC_KEYS:
        return jsonify({'error': 'clave no sincronizable', 'error_en': 'key not syncable'}), 400
    if len(_json.dumps(body.get('value'), default=str)) > SYNC_MAX_BYTES:
        return jsonify({'error': 'demasiado grande', 'error_en': 'too large'}), 413
    now = datetime.now(timezone.utc)
    try:
        ts = datetime.fromisoformat(str(body.get('updated_at')).replace('Z', '+00:00')) if body.get('updated_at') else now
        ts = min(ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc), now)
    except ValueError:
        ts = now
    with session_scope() as s:
        r = s.get(UserState, (owner, key))
        if r is not None and r.updated_at and r.updated_at > ts:
            return jsonify({'ok': False, 'stale': True, 'updated_at': r.updated_at.isoformat(), 'value': r.value}), 409
        if r is None:
            r = UserState(owner_hash=owner, key=key)
            s.add(r)
        r.value, r.updated_at = body.get('value'), ts
    return jsonify({'ok': True, 'updated_at': ts.isoformat()})


def current_positions(owner, source_key):
    """Posiciones ACTUALES de una cartera sincronizada (para los reportes programados):
    pf:<id> → kh_portfolios · market → eco_pos. None si no hay datos sincronizados."""
    try:
        from core.semantic import _load_snapshot
        from ontology.db import session_scope
        from research.models import UserState
        snap = _load_snapshot()
        key = 'kh_portfolios' if source_key.startswith('pf:') else 'eco_pos' if source_key == 'market' else None
        if not key:
            return None
        with session_scope() as s:
            r = s.get(UserState, (owner, key))
            val = r.value if r is not None else None
        if val is None:
            return None
        rows = []
        if key == 'kh_portfolios':
            pf = next((p for p in (val or []) if isinstance(p, dict) and 'pf:' + str(p.get('id')) == source_key), None)
            if pf is None:
                return None
            for p in pf.get('positions') or []:
                n = snap['by_id'].get(p.get('nodeId')) or {}
                if n.get('mkt'):
                    rows.append({'id': p.get('nodeId'), 'symbol': n['mkt'], 'label': n.get('label'),
                                 'shares': p.get('shares'), 'cost_usd': (p.get('shares') or 0) * (p.get('avgPrice') or 0)})
            return {'positions': _clean_positions(rows), 'cash': pf.get('cash'), 'start_value': pf.get('startCash')}
        for nid, p in (val or {}).items():
            n = snap['by_id'].get(nid) or {}
            if n.get('mkt') and isinstance(p, dict):
                rows.append({'id': nid, 'symbol': n['mkt'], 'label': n.get('label'), 'shares': p.get('sh'),
                             'cost_usd': (p.get('sh') or 0) * (p.get('bp') or 0)})
        return {'positions': _clean_positions(rows)}
    except Exception as e:  # noqa: BLE001
        log.info('current_positions: %s', type(e).__name__)
        return None


# ── programación ─────────────────────────────────────────────────────────────
def due(w, now):
    last = w.last_report_at
    if w.schedule == 'daily':
        return now.hour >= 21 and (last is None or now - last > timedelta(hours=20))
    if w.schedule == 'weekly':
        return now.weekday() == 4 and now.hour >= 21 and (last is None or now - last > timedelta(days=6))
    if w.schedule == 'monthly':
        return now.day == 1 and now.hour >= 6 and (last is None or (last.year, last.month) != (now.year, now.month))
    return False


def run_due(now=None, build=None):
    """Genera los reportes vencidos (lo llama el hilo; también los tests)."""
    from core import portfolio_report
    from core.ai_usage import ai_context
    from ontology.db import session_scope
    from research.models import PortfolioWatch
    now = now or datetime.now(timezone.utc)
    build = build or portfolio_report.build
    done = 0
    with session_scope() as s:
        todo = [(w.id, w.owner_hash, w.schedule, w.name, list(w.positions or []), w.start_value_usd, w.start_date,
                 w.cash_usd, dict(w.profile or {}), w.owner_name, w.source_key)
                for w in s.query(PortfolioWatch).filter(PortfolioWatch.schedule != 'off').all() if due(w, now)]
    for wid, owner, sched, name, pos, sv, sd, cash, prof, who, skey in todo:
        try:
            cur = current_positions(owner, skey or '')     # la cartera de HOY si está sincronizada
            if cur and cur.get('positions'):
                pos = cur['positions']
                cash = cur.get('cash') if cur.get('cash') is not None else cash
                sv = cur.get('start_value') or sv
            lang = 'en' if str(prof.get('lang') or 'es').startswith('en') else 'es'
            with ai_context('reporte_cartera', who or 'programado'):
                rep = build(pos, start_value=sv, start_date=sd, period=KIND_PERIOD[sched], profile=prof,
                            cash_usd=cash or 0.0, lang=lang)
            if rep.get('ok'):
                _store(owner, sched, rep, watch_id=wid, name=name)
                done += 1
        except Exception as e:  # noqa: BLE001
            log.warning('scheduled portfolio report %s: %s', wid, e)
        finally:
            with session_scope() as s:
                w = s.get(PortfolioWatch, wid)
                if w is not None:
                    w.last_report_at = now
    return done


def _ensure_scheduler():
    t = _STATE['thread']
    if t is not None and t.is_alive():
        return
    try:
        if current_app.config.get('TESTING'):
            return
    except RuntimeError:
        pass

    def loop():
        time.sleep(60)
        while True:
            try:
                if _db():
                    run_due()
            except Exception as e:  # noqa: BLE001
                log.warning('portfolio report scheduler: %s', e)
            time.sleep(1200)
    t = threading.Thread(target=loop, name='portfolio-reports', daemon=True)
    _STATE['thread'] = t
    t.start()


@portfolio_reports_bp.before_app_request
def _boot_scheduler():
    if _STATE['thread'] is None:
        _ensure_scheduler()
