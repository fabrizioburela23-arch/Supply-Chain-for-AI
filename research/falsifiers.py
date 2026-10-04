"""research/falsifiers.py — falsadores ESTRUCTURADOS y verificables (C8, misión de reparación 2026-10-04).

Antes los falsadores eran solo texto ("el precio rompe el máximo…"): nadie los
evaluaba, ninguna conclusión pasaba a 'falsada', y el presidente copiaba
falsadores de conclusiones con OTRA postura (uno confirmaba la compra).

Ahora, además del texto, una conclusión puede traer reglas {metric, op,
threshold, by} que el job diario (research/outcomes.evaluate_due) comprueba con
PRECIOS REALES: si se dispara, la claim pasa a 'falsified', queda una fila
ClaimOutcome ('falsifier', miss) y su foto de partida deja de calificarse.
Métricas v1 (solo lo que se verifica gratis): precio y exceso vs SPY.
"""
import re
from datetime import date

from pydantic import BaseModel, Field, field_validator

METRICS = ('price', 'excess_vs_spy')
OPS = ('<', '>')
BULLISH = {'positive', 'BUY', 'ADD'}
BEARISH = {'negative', 'SELL', 'AVOID', 'TRIM'}
METRIC_ES = {'price': 'precio', 'excess_vs_spy': 'exceso vs SPY'}
METRIC_EN = {'price': 'price', 'excess_vs_spy': 'excess vs SPY'}


class FalsifierRule(BaseModel):
    metric: str
    op: str
    threshold: float
    by: str

    @field_validator('metric')
    @classmethod
    def _m(cls, v):
        v = str(v).strip().lower()
        if v not in METRICS:
            raise ValueError(f'metric debe ser una de {METRICS}')
        return v

    @field_validator('op')
    @classmethod
    def _o(cls, v):
        v = str(v).strip()
        v = {'<=': '<', '>=': '>', 'lt': '<', 'gt': '>', 'below': '<', 'above': '>'}.get(v.lower(), v)
        if v not in OPS:
            raise ValueError(f'op debe ser una de {OPS}')
        return v

    @field_validator('by')
    @classmethod
    def _by(cls, v):
        s = str(v).strip()[:10]
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', s):
            raise ValueError('by debe ser YYYY-MM-DD')
        date.fromisoformat(s)
        return s


def normalize(rules):
    """Lista de dicts válidos (ignora entradas rotas en vez de romper)."""
    out = []
    for r in rules or []:
        try:
            if isinstance(r, FalsifierRule):
                out.append(r.model_dump())
            elif isinstance(r, dict):
                out.append(FalsifierRule.model_validate(r).model_dump())
        except Exception:  # noqa: BLE001
            continue
    return out


def direction_errors(stance_or_decision, rules):
    """Un falsador debe CONTRADECIR la postura: para una postura/decisión
    alcista el precio (o el exceso) tiene que CAER (op '<'); para una bajista,
    SUBIR (op '>'). Devuelve los errores (vacío = ok)."""
    errs = []
    want = '<' if stance_or_decision in BULLISH else '>' if stance_or_decision in BEARISH else None
    if want is None:
        return errs
    for i, r in enumerate(rules or []):
        d = r.model_dump() if isinstance(r, FalsifierRule) else dict(r)
        if d.get('op') != want:
            errs.append(f"falsifier_rules[{i}] a favor de la tesis: con postura '{stance_or_decision}' la regla "
                        f"{d.get('metric')} debe usar '{want}' (algo que la contradiga), no '{d.get('op')}'")
    return errs


def describe(rule, lang='es'):
    d = rule.model_dump() if isinstance(rule, FalsifierRule) else dict(rule)
    m = (METRIC_EN if lang == 'en' else METRIC_ES).get(d.get('metric'), d.get('metric'))
    unit = '%' if d.get('metric') == 'excess_vs_spy' else ''
    if lang == 'en':
        return f"{m} {d.get('op')} {d.get('threshold')}{unit} by {d.get('by')}"
    return f"{m} {d.get('op')} {d.get('threshold')}{unit} antes del {d.get('by')}"


def check_rules(rules, baseline_date, series, bench=None, today=None):
    """¿Alguna regla se disparó entre la foto de partida y hoy? Devuelve
    {rule, date, value} de la PRIMERA que se dispara, o None. Reglas vencidas
    (by < hoy) sin disparo simplemente expiran."""
    if not rules or not series:
        return None
    today = today or date.today()
    keys = sorted(k for k in series if k > baseline_date)
    p0 = None
    k0 = max((k for k in series if k <= baseline_date), default=None)
    if k0 is not None:
        p0 = series[k0]
    for r in normalize(rules):
        by = r['by']
        for k in keys:
            if k > by or k > today.isoformat():
                break
            px = series.get(k)
            if px is None:
                continue
            if r['metric'] == 'price':
                val = float(px)
            else:
                if not p0 or not bench:
                    continue
                kb0 = max((kk for kk in bench if kk <= baseline_date), default=None)
                if kb0 is None or k not in bench or not bench[kb0]:
                    continue
                val = ((float(px) / p0 - 1.0) - (float(bench[k]) / float(bench[kb0]) - 1.0)) * 100.0
            hit = val < r['threshold'] if r['op'] == '<' else val > r['threshold']
            if hit:
                return {'rule': r, 'date': k, 'value': round(val, 4)}
    return None


def apply_falsifiers(session, now, get_series, today):
    """Recorre las claims ACTIVAS con reglas y foto de partida calificable; si
    una regla se disparó → status 'falsified' + ClaimOutcome('falsifier', miss,
    final) + baseline.scoreable=False (sus checkpoints futuros ya no cuentan:
    el fallo ya quedó registrado). Idempotente por (claim_id, 'falsifier')."""
    from datetime import timedelta

    from sqlalchemy.exc import IntegrityError

    from research.models import ClaimBaseline, ClaimOutcome, ResearchClaim
    rows = (session.query(ResearchClaim, ClaimBaseline)
            .join(ClaimBaseline, ClaimBaseline.claim_id == ResearchClaim.id)
            .filter(ResearchClaim.status == 'active', ResearchClaim.falsifier_rules.isnot(None),
                    ClaimBaseline.scoreable.is_(True)).all())
    n = 0
    for claim, b in rows:
        rules = normalize(claim.falsifier_rules)
        if not rules or not b.symbol:
            continue
        since = date.fromisoformat(b.baseline_date) - timedelta(days=15)
        series = get_series(b.symbol, since)
        bench = get_series(b.benchmark_symbol or 'SPY', since) if any(r['metric'] == 'excess_vs_spy' for r in rules) else None
        hit = check_rules(rules, b.baseline_date, series, bench, today)
        if not hit:
            continue
        r = hit['rule']
        unit = '%' if r['metric'] == 'excess_vs_spy' else ''
        reason = (f"falsador disparado: {describe(r)} → el {hit['date']} valió {hit['value']}{unit} "
                  f"(postura {claim.stance})")
        reason_en = (f"falsifier triggered: {describe(r, 'en')} → on {hit['date']} it was {hit['value']}{unit} "
                     f"({claim.stance} stance)")
        row = ClaimOutcome(claim_id=claim.id, baseline_id=b.id, entity_id=claim.subject_entity_id,
                           agent_type=claim.agent_type, horizon=claim.horizon, stance=claim.stance,
                           confidence=float(claim.confidence or 0), checkpoint='falsifier', checkpoint_days=0,
                           final=True, due_date=hit['date'], symbol=b.symbol, eval_date=hit['date'],
                           eval_price=(hit['value'] if r['metric'] == 'price' else None), band=b.band, result='miss',
                           reason=reason[:900], reason_en=reason_en[:900], claim_status='falsified',
                           price_source='cierres diarios ajustados', method='falsifier-v1', evaluated_at=now)
        try:
            with session.begin_nested():
                session.add(row)
                session.flush()
        except IntegrityError:
            continue
        claim.status = 'falsified'
        claim.valid_to = now
        b.scoreable = False
        b.na_reason = 'falsada por una regla verificable (' + describe(r) + ')'
        n += 1
    if n:
        session.flush()
    return n
