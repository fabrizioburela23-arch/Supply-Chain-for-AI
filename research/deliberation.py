"""research/deliberation.py — la SALA DEL COMITÉ: puestos y conversación visible.

Pedido (2026-10-02): "que el comité esté más claro y en vivo, que tenga
puestos, que se vea su comunicación".

Cada agente de investigación con conclusiones ocupa un PUESTO en la mesa
(📊 Fundamental, 📰 Noticias, 🔗 Cadena…) y a su lado se sientan la 📡 Mesa de
mercado (datos en vivo), el ⚠️ Oficial de riesgo (volatilidad medida), el
🧮 Núcleo cuantitativo (la cuenta) y el 🏛 Presidente.

REGLA DE ORO: nada de lo que "dicen" se inventa. Cada mensaje es una plantilla
sobre datos REALES del comité: el texto de la conclusión (claim) que el agente
ya escribió con evidencia citada, su fuente principal, su historial de aciertos,
las contradicciones detectadas (X#), el precio en vivo, el riesgo medido y la
regla de decisión. Por eso no hace falta otra llamada a la IA (ni costo, ni
riesgo de cifras falsas): la IA solo habla al final, como Presidente, y su memo
ya pasa por el guardián de cifras.

Los mensajes se publican en el registro de progreso del memo a medida que
ocurre cada etapa → GET /api/committee/memo/<id> los devuelve EN VIVO; al
terminar quedan guardados en memo.memo['transcript'] (y 'seats').
"""

SEAT_ORDER = ('fundamental', 'technical', 'news', 'supply_chain', 'geopolitical', 'macro', 'crypto',
              'risk_observation')
FOR_T = 0.15                 # postura neta > +0.15 → "a favor"; < −0.15 → "en contra"

# puestos fijos (no son agentes de investigación)
DESK = {
    'chair': ('🏛', 'Presidente', 'Chair'),
    'market': ('📡', 'Mesa de mercado', 'Market desk'),
    'risk_officer': ('🛡️', 'Oficial de riesgo', 'Risk officer'),
    'quant': ('🧮', 'Núcleo cuantitativo', 'Quant core'),
    'mandate': ('👤', 'Mandato del cliente', 'Client mandate'),
}
AGENT_NAMES = {
    'fundamental': ('📊', 'Analista fundamental', 'Fundamental analyst'),
    'technical': ('📈', 'Analista técnico', 'Technical analyst'),
    'news': ('📰', 'Analista de noticias', 'News analyst'),
    'supply_chain': ('🔗', 'Analista de cadena de suministro', 'Supply-chain analyst'),
    'geopolitical': ('🗺️', 'Analista geopolítico', 'Geopolitical analyst'),
    'macro': ('🌐', 'Analista macro', 'Macro analyst'),
    'crypto': ('₿', 'Analista cripto', 'Crypto analyst'),
    'risk_observation': ('⚠️', 'Analista de riesgos', 'Risk analyst'),
}
HZ_TXT = {'INTRADAY': ('intradía', 'intraday'), 'SHORT_TERM': ('corto plazo', 'short term'),
          'MEDIUM_TERM': ('mediano plazo', 'medium term'), 'LONG_TERM': ('largo plazo', 'long term'),
          'STRUCTURAL': ('estructural', 'structural')}
SIGN = {'positive': 1, 'negative': -1, 'neutral': 0, 'mixed': 0}


def seat_name(seat):
    return AGENT_NAMES.get(seat) or DESK.get(seat) or ('🤖', seat, seat)


def stance_of(v):
    return 'for' if v > FOR_T else 'against' if v < -FOR_T else 'neutral'


def _hz(h):
    return HZ_TXT.get(h, (str(h or '').lower(), str(h or '').lower()))


def _cut(s, n=320):
    s = ' '.join(str(s or '').split())
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _sent(s, n=320):
    """Recorta y quita el punto final (para encadenar frases sin '. ·')."""
    return _cut(s, n).rstrip(' .')


def build_seats(conv, views, track):
    """[{seat, emoji, name_es, name_en, stance, net, n_claims, n_pos, n_neg,
    reliability, n_scored, hits}] — un puesto por agente con conclusiones."""
    per = {}
    for r in conv.values():
        for c in r['claims']:
            p = per.setdefault(c['agent_type'], {'n': 0, 'pos': 0, 'neg': 0, 'rel': c['reliability']})
            p['n'] += 1
            s = SIGN.get(c['stance'], 0)
            if s > 0:
                p['pos'] += 1
            elif s < 0:
                p['neg'] += 1
    order = {a: i for i, a in enumerate(SEAT_ORDER)}
    seats = []
    for a in sorted(per, key=lambda x: (order.get(x, 99), x)):
        p = per[a]
        net = float(views.get(a, 0.0))
        tr = (track or {}).get(a) or {}
        e, es, en = seat_name(a)
        seats.append({'seat': a, 'emoji': e, 'name_es': es, 'name_en': en, 'stance': stance_of(net),
                      'net': round(net, 3), 'n_claims': p['n'], 'n_pos': p['pos'], 'n_neg': p['neg'],
                      'reliability': round(float(tr.get('reliability', p['rel'])), 3),
                      'n_scored': int(tr.get('n') or 0), 'hits': int(tr.get('hits') or 0)})
    return seats


def tally(seats):
    out = {'for': 0, 'against': 0, 'neutral': 0}
    for s in seats:
        out[s['stance']] += 1
    return out


def _msg(seat, kind, es, en, stance=None, refs=None, source=None, stage=None):
    e, n_es, n_en = seat_name(seat)
    m = {'seat': seat, 'emoji': e, 'name_es': n_es, 'name_en': n_en, 'kind': kind,
         'text_es': es, 'text_en': en or es}
    if stance:
        m['stance'] = stance
    if refs:
        m['refs'] = [r for r in refs if r]
    if source:
        m['source'] = source
    if stage:
        m['stage'] = stage
    return m


def _track_txt(seat):
    if seat['n_scored'] <= 0:
        return 'aún sin predicciones calificadas', 'no scored predictions yet'
    return (f"historial: {seat['hits']} de {seat['n_scored']} aciertos",
            f"track record: {seat['hits']} of {seat['n_scored']} hits")


def opening(label, symbol, seats, n_claims, n_rels):
    """Mensaje inaugural del Presidente."""
    if not seats:
        return [_msg('chair', 'open',
                     f'Abro la sesión sobre {label}. No hay conclusiones activas de los analistas: sin evidencia '
                     f'no hay debate. Recomiendo correr primero 🔬 Investigación IA.',
                     f'Opening the session on {label}. There are no active analyst conclusions: without evidence '
                     f'there is no debate. I recommend running 🔬 AI research first.')]
    names_es = ', '.join(s['emoji'] + ' ' + s['name_es'] for s in seats)
    names_en = ', '.join(s['emoji'] + ' ' + s['name_en'] for s in seats)
    x_es = f' Hay {n_rels} contradicción(es) entre ellos que vamos a discutir.' if n_rels else ''
    x_en = f' There are {n_rels} contradiction(s) between them that we will discuss.' if n_rels else ''
    tk = f' ({symbol})' if symbol else ''
    return [_msg('chair', 'open',
                 f'Abro la sesión sobre {label}{tk}. Tenemos {n_claims} conclusión(es) de {len(seats)} analista(s): '
                 f'{names_es}.{x_es} Cada uno expone su postura con su evidencia.',
                 f'Opening the session on {label}{tk}. We have {n_claims} conclusion(s) from {len(seats)} '
                 f'analyst(s): {names_en}.{x_en} Each one presents its stance with its evidence.')]


def positions(seats, conv, claims_by_id, cref, evidence=None):
    """Una intervención por puesto: su postura neta + su conclusión de mayor
    peso (texto real del claim) + su fuente principal + su historial."""
    evidence = evidence or {}
    out = []
    by_agent = {}
    for h, r in conv.items():
        for c in r['claims']:
            by_agent.setdefault(c['agent_type'], []).append(dict(c, horizon=h))
    for s in seats:
        cs = sorted(by_agent.get(s['seat'], []), key=lambda c: -c['weight'])
        if not cs:
            continue
        want = 1 if s['stance'] == 'for' else -1 if s['stance'] == 'against' else 0
        main = next((c for c in cs if SIGN.get(c['stance'], 0) == want), cs[0])
        c = claims_by_id.get(main['id'])
        if c is None:
            continue
        h_es, h_en = _hz(main['horizon'])
        lead_es = {'for': 'Estoy A FAVOR', 'against': 'Estoy EN CONTRA', 'neutral': 'Me mantengo NEUTRAL'}[s['stance']]
        lead_en = {'for': 'I am IN FAVOR', 'against': 'I am AGAINST', 'neutral': 'I stay NEUTRAL'}[s['stance']]
        tr_es, tr_en = _track_txt(s)
        extra_es = extra_en = ''
        if s['n_claims'] > 1:
            extra_es = f" ({s['n_pos']} a favor y {s['n_neg']} en contra entre mis {s['n_claims']} conclusiones)"
            extra_en = f" ({s['n_pos']} for and {s['n_neg']} against among my {s['n_claims']} conclusions)"
        conf = round(main['calibrated'] * 100)
        ref = cref.get(main['id'])
        out.append(_msg(
            s['seat'], 'position',
            f"{lead_es}{extra_es}. Mi punto principal ({h_es}, confianza {conf} %): {_sent(c.statement_es)} — {tr_es}.",
            f"{lead_en}{extra_en}. My main point ({h_en}, confidence {conf}%): "
            f"{_sent(c.statement_en or c.statement_es)} — {tr_en}.",
            stance=s['stance'], refs=[ref], source=evidence.get(main['id'])))
    return out


def rebuttals(rels, claims_by_id, cref, seats, max_n=3):
    """Réplicas: cada contradicción detectada (X#) se vuelve un cruce entre los
    dos puestos. Sin contradicciones pero con posturas opuestas, la minoría
    responde al argumento más fuerte de la mayoría."""
    out = []
    stance = {s['seat']: s['stance'] for s in seats}
    for j, r in enumerate(rels[:max_n], 1):
        a, b = claims_by_id.get(r.claim_a), claims_by_id.get(r.claim_b)
        if a is None or b is None:
            continue
        x = f'X{j}'
        if a.agent_type == b.agent_type:
            e, n_es, n_en = seat_name(a.agent_type)
            out.append(_msg(a.agent_type, 'rebuttal',
                            f'Debo reconocer una tensión entre dos de mis propias conclusiones: «{_cut(a.statement_es, 160)}» '
                            f'frente a «{_cut(b.statement_es, 160)}».',
                            f'I must acknowledge a tension between two of my own conclusions: '
                            f'“{_cut(a.statement_en or a.statement_es, 160)}” versus “{_cut(b.statement_en or b.statement_es, 160)}”.',
                            stance=stance.get(a.agent_type), refs=[cref.get(a.id), cref.get(b.id), x]))
            continue
        ea, na_es, na_en = seat_name(a.agent_type)
        out.append(_msg(b.agent_type, 'rebuttal',
                        f'Discrepo de {ea} {na_es}: dice «{_cut(a.statement_es, 140)}», pero mi evidencia muestra '
                        f'«{_cut(b.statement_es, 180)}».',
                        f'I disagree with {ea} {na_en}: it says “{_cut(a.statement_en or a.statement_es, 140)}”, '
                        f'but my evidence shows “{_cut(b.statement_en or b.statement_es, 180)}”.',
                        stance=stance.get(b.agent_type), refs=[cref.get(b.id), cref.get(a.id), x]))
        if r.reason:
            out.append(_msg('chair', 'moderate',
                            f'Tomo nota de la contradicción {x}: {_sent(r.reason, 220)}. Pesará menos en la convicción '
                            f'de ese plazo.',
                            f'Noted contradiction {x}: {_sent(r.reason, 220)}. It will weigh less in that horizon\'s '
                            f'conviction.', refs=[x]))
    if out or len(seats) < 2:
        return out
    fors = [s for s in seats if s['stance'] == 'for']
    agns = [s for s in seats if s['stance'] == 'against']
    if not fors or not agns:
        return out
    minority, majority = (agns, fors) if len(agns) <= len(fors) else (fors, agns)
    mi, ma = minority[0], max(majority, key=lambda s: abs(s['net']))
    e, n_es, n_en = seat_name(ma['seat'])
    out.append(_msg(mi['seat'], 'rebuttal',
                    f'Escuché a {e} {n_es}, pero sostengo mi postura: la mayoría puede estar subestimando lo que '
                    f'señalé arriba. Pido que conste como disenso.',
                    f'I heard {e} {n_en}, but I hold my position: the majority may be underestimating what I '
                    f'pointed out above. I ask that it be recorded as dissent.', stance=mi['stance']))
    return out


def market_msg(live, symbol):
    if not symbol:
        return _msg('market', 'data', 'Esta empresa no cotiza en bolsa: no hay precio en vivo que aportar.',
                    'This company is not listed: there is no live price to report.', stage='live')
    if not (live or {}).get('ok'):
        return _msg('market', 'data', 'No pude obtener el precio en vivo ahora mismo; el comité sigue sin ese dato.',
                    'I could not get the live price right now; the committee proceeds without it.', stage='live')
    if live.get('line'):
        return _msg('market', 'data', f"Dato en vivo: {live['line']}", f"Live data: {live['line']}", refs=['D1'],
                    stage='live')
    cur = live.get('currency') or ''
    chg = live.get('change_pct')
    chg_s = f" · {'+' if (chg or 0) > 0 else ''}{chg} % hoy" if chg is not None else ''
    chg_e = f" · {'+' if (chg or 0) > 0 else ''}{chg}% today" if chg is not None else ''
    cap = live.get('market_cap_usd_b')
    cap_s = f' · capitalización {cap} mil millones USD' if cap else ''
    cap_e = f' · market cap {cap} billion USD' if cap else ''
    return _msg('market', 'data',
                f"{symbol} cotiza a {live.get('price')} {cur}{chg_s}{cap_s} (fuente: {live.get('source') or '—'}).",
                f"{symbol} trades at {live.get('price')} {cur}{chg_e}{cap_e} (source: {live.get('source') or '—'}).",
                refs=['D1'], stage='live')


def _p(v):
    return '—' if v is None else f'{v:.1f}'.rstrip('0').rstrip('.') if isinstance(v, float) else str(v)


def risk_msg(risk, symbol):
    if not symbol:
        return None
    if not (risk or {}).get('ok'):
        return _msg('risk_officer', 'data',
                    'No pude medir el riesgo con precios reales; sin volatilidad no se calcula un tamaño de posición.',
                    'I could not measure risk with real prices; without volatility no position size is computed.',
                    stage='risk')
    vol, dd = risk.get('vol_ann_pct'), risk.get('max_drawdown_pct')
    beta = risk.get('beta_spy')
    calm_es = ('muy movida' if (vol or 0) >= 50 else 'movida' if (vol or 0) >= 30 else 'relativamente estable')
    calm_en = ('very volatile' if (vol or 0) >= 50 else 'volatile' if (vol or 0) >= 30 else 'relatively stable')
    return _msg('risk_officer', 'data',
                f'Medí 1 año de precios reales: volatilidad anual {_p(vol)} % ({calm_es}), máxima caída {_p(dd)} %, '
                f'beta frente al S&P 500 {_p(beta)}. A más volatilidad, menos dinero por posición.',
                f'I measured 1 year of real prices: annual volatility {_p(vol)}% ({calm_en}), max drawdown {_p(dd)}%, '
                f'beta vs the S&P 500 {_p(beta)}. More volatility means less money per position.',
                refs=['R1'], stage='risk')


def mandate_msg(client):
    if not client:
        return None
    if not client.get('ok'):
        return _msg('mandate', 'data', 'No pude leer la cuenta del cliente; el comité usa una referencia ilustrativa.',
                    'I could not read the client account; the committee uses an illustrative reference.',
                    stage='client')
    m = client.get('mandate') or {}
    has = bool((client.get('position') or {}).get('qty'))
    return _msg('mandate', 'data',
                f"Mandato del cliente: riesgo por posición {m.get('risk_budget', 0) * 100:.1f} %, tope por posición "
                f"{m.get('max_position', 0) * 100:.1f} %. {'Ya tiene posición en esta acción.' if has else 'Hoy no tiene esta acción.'}",
                f"Client mandate: risk per position {m.get('risk_budget', 0) * 100:.1f}%, max per position "
                f"{m.get('max_position', 0) * 100:.1f}%. {'Already holds this stock.' if has else 'Does not hold this stock today.'}",
                refs=['M1'], stage='client')


def quant_msg(overall, conv, decision, reason_es, reason_en, sizing, seats, dl):
    t = tally(seats)
    hz_es = ', '.join(f"{_hz(h)[0]} {conv[h]['score']:+.0f}" for h in conv if conv[h].get('horizon_weight', 1) > 0)
    hz_en = ', '.join(f"{_hz(h)[1]} {conv[h]['score']:+.0f}" for h in conv if conv[h].get('horizon_weight', 1) > 0)
    tw = (sizing or {}).get('target_weight_pct')
    tw_es = f' Tamaño objetivo: {tw:.2f} % del patrimonio (fórmula fija por volatilidad).' if tw else ''
    tw_en = f' Target size: {tw:.2f}% of equity (fixed volatility formula).' if tw else ''
    return _msg('quant', 'verdict',
                f"Hice la cuenta: {t['for']} a favor, {t['against']} en contra, {t['neutral']} neutral(es). "
                f"Convicción global {overall:+.0f} sobre 100 ({hz_es or 'sin plazos con peso'}). "
                f"Por las reglas fijas eso da: {dl[0]} — {reason_es}.{tw_es}",
                f"I ran the numbers: {t['for']} for, {t['against']} against, {t['neutral']} neutral. "
                f"Overall conviction {overall:+.0f} out of 100 ({hz_en or 'no weighted horizons'}). "
                f"By the fixed rules that gives: {dl[1]} — {reason_en}.{tw_en}",
                refs=['Q1'], stage='scoring')


def chair_close(body, final_decision, quant_decision, dl, ai_used):
    """Cierre del Presidente: respuesta a cada disenso + veredicto."""
    out = []
    for d in (body.get('dissent') or [])[:3]:
        e, n_es, n_en = seat_name(d.get('agent_type'))
        out.append(_msg('chair', 'reply',
                        f"A {e} {n_es}: tu objeción queda registrada — {_cut(d.get('view_es'), 220)}",
                        f"To {e} {n_en}: your objection is on record — {_cut(d.get('view_en') or d.get('view_es'), 220)}",
                        refs=d.get('refs')))
    if final_decision != quant_decision:
        note_es = body.get('chair_note_es') or ''
        note_en = body.get('chair_note_en') or note_es
        out.append(_msg('chair', 'verdict',
                        f'Rebajo la propuesta a {dl[0]}: {_cut(note_es, 300)}',
                        f'I downgrade the proposal to {dl[1]}: {_cut(note_en, 300)}', stage='chair'))
    who_es = '' if ai_used else ' (sin IA: memo armado con plantillas sobre los números)'
    who_en = '' if ai_used else ' (no AI: memo built from templates over the numbers)'
    conf = body.get('confidence')
    conf_es = f' Confianza del comité: {round(float(conf) * 100)} %.' if conf is not None else ''
    conf_en = f' Committee confidence: {round(float(conf) * 100)}%.' if conf is not None else ''
    out.append(_msg('chair', 'verdict',
                    f"Veredicto{who_es}: {dl[0]}. {_cut(body.get('summary_es'), 420)}{conf_es} "
                    f"Es una PROPUESTA: nada se ejecuta sin tu aprobación.",
                    f"Verdict{who_en}: {dl[1]}. {_cut(body.get('summary_en') or body.get('summary_es'), 420)}{conf_en} "
                    f"It is a PROPOSAL: nothing executes without your approval.", stage='chair'))
    return out
