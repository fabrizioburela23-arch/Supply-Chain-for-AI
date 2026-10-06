"""research/agent_skills.py — HABILIDADES PROPIAS de cada agente (2026-10-06).

Pedido de Fabrizio: "le hablé específicamente al agente de supply (Cadena) y me respondió con la investigación
general. Necesito capacidades específicas de cada agente: una programación que busque las cosas de su área y
muestre cosas relacionadas con su rol; que cada uno tenga incorporadas skills de su área."

Antes, al hablarle a un analista (@cadena, @tecnico…) solo podía responder con conclusiones de una investigación
previa; sin ellas decía "todavía no investigué". Ahora CADA puesto trae, al instante y sin investigación previa,
SU paquete de datos en vivo (lo que un analista de ese rol miraría) y responde con un enfoque propio:

  supply_chain (Cadena)  → grafo de proveedores/clientes con su relación, tensor de la cadena (concentración,
                           países de los proveedores, fuentes de riesgo directas e indirectas, valor de mercado
                           que arrastra si cae, comparables) y eventos en vivo que tocan a sus proveedores.
  fundamental (Analista) → perfil en vivo, estados anuales, ratios calculados, pares y fundamentales vivos.
  technical (Técnico)    → velas de 1 año → SMA50/200, RSI, retornos, máximo/mínimo, caída máxima, fuerza vs SPY.
  news (Radar)           → noticias de la empresa (Finnhub/GDELT/SEC) + eventos en vivo que la nombran.
  geopolitical (Radar)   → países/sanciones/estrechos: de su sede Y de sus proveedores (tensor + World Monitor).
  macro (Analista)       → contexto de la empresa + índice de riesgo geopolítico global (GPR, Reserva Federal).
  crypto (Radar)         → noticias y ficha.

Cada paquete numera su evidencia: E# (research/context.py, la MISMA tubería de la investigación profunda en
modo rápido) y S# (habilidades extra de este módulo). La respuesta cita esos ids; el guardián de cifras de
core/ai rechaza cifras que no estén en el paquete. Además devuelve `facts` (datos estructurados para la UI),
`note_es/en` (resumen DETERMINISTA, nunca texto del modelo) y `actions` (la ventana o gráfico de su rol).
Todo es LECTURA. Nunca propone órdenes.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FutTimeout

log = logging.getLogger('khipu')

_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix='agent-skill')
_GEO_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix='agent-skill-geo')
GEO_TIMEOUT_S = 3.0
CTX_TIMEOUT_S = 9.0
EXTRA_TIMEOUT_S = 5.0

# ── el ENFOQUE de cada rol: qué mira y cómo responde (va en el prompt) ─────────────────────────
FOCUS = {
    'supply_chain': (
        "Eres el analista de CADENA DE SUMINISTRO. Responde SOLO desde tu especialidad, en este orden: "
        "1) de quién depende (proveedores críticos, cuánto pesa cada uno y qué le dan); "
        "2) dónde está ese riesgo en el mapa (países de los proveedores, estrechos y eventos en vivo que los tocan); "
        "3) a quién arrastra si falla (clientes y valor de mercado expuesto aguas abajo); "
        "4) qué tan concentrada y sustituible es su cadena (comparables con cadenas parecidas); "
        "5) UNA cosa concreta que vigilarías. No opines del precio de la acción ni de la valuación.",
        "You are the SUPPLY-CHAIN analyst. Answer ONLY from your specialty, in this order: 1) who it depends on "
        "(critical suppliers, how much each weighs and what they provide); 2) where that risk sits on the map "
        "(supplier countries, straits and live events touching them); 3) who it drags down if it fails (customers "
        "and downstream market value exposed); 4) how concentrated and replaceable its chain is (peers with similar "
        "chains); 5) ONE concrete thing you would watch. Do not opine on the share price or valuation."),
    'fundamental': (
        "Eres el analista FUNDAMENTAL. Responde SOLO sobre el negocio: ingresos y su crecimiento, márgenes, caja "
        "libre, deuda, rentabilidad sobre el capital, dilución y valuación frente a pares; qué parece descontar el "
        "precio. Usa las cifras del paquete con su año. Si es privada, dilo y usa su última valuación verificada.",
        "You are the FUNDAMENTAL analyst. Answer ONLY about the business: revenue and growth, margins, free cash "
        "flow, debt, return on capital, dilution and valuation versus peers; what the price seems to discount. Use "
        "the package figures with their year. If it is private, say so and use its last verified valuation."),
    'technical': (
        "Eres el analista TÉCNICO. Responde SOLO sobre el precio: tendencia (medias de 50 y 200 días), fuerza (RSI), "
        "retornos a 1/3/6/12 meses, distancia al máximo y mínimo de 52 semanas, caída máxima y fuerza frente al S&P "
        "500; niveles a vigilar. No opines del negocio. Si no cotiza, dilo y explica qué se puede seguir en su lugar.",
        "You are the TECHNICAL analyst. Answer ONLY about price: trend (50/200-day averages), strength (RSI), 1/3/6/12-"
        "month returns, distance to the 52-week high/low, max drawdown and strength versus the S&P 500; levels to "
        "watch. Do not opine on the business. If it is not listed, say so and explain what can be tracked instead."),
    'news': (
        "Eres el analista de NOTICIAS. Responde SOLO con hechos recientes con su fecha y fuente: qué pasó, cuál de "
        "esos hechos importa de verdad para la empresa y por qué, y qué es lo próximo a mirar. Separa hechos de rumores.",
        "You are the NEWS analyst. Answer ONLY with recent facts with their date and source: what happened, which of "
        "those facts truly matters for the company and why, and what to watch next. Separate facts from rumours."),
    'geopolitical': (
        "Eres el analista GEOPOLÍTICO. Responde SOLO sobre exposición a países, sanciones y controles de exportación, "
        "conflictos y estrechos: desde su sede Y desde los países de sus proveedores; qué evento en vivo la toca hoy "
        "y qué escenario la golpearía más.",
        "You are the GEOPOLITICAL analyst. Answer ONLY about exposure to countries, sanctions and export controls, "
        "conflicts and straits: from its headquarters AND from its suppliers' countries; which live event touches it "
        "today and which scenario would hurt it most."),
    'macro': (
        "Eres el analista MACRO. Responde SOLO sobre cómo le afectan las tasas, el ciclo, las divisas y el riesgo "
        "geopolítico global (índice GPR) a esta empresa en particular, según su negocio y su cadena.",
        "You are the MACRO analyst. Answer ONLY about how rates, the cycle, currencies and global geopolitical risk "
        "(GPR index) affect this particular company, given its business and its chain."),
    'crypto': (
        "Eres el analista CRIPTO. Responde SOLO sobre su exposición a cripto: hechos recientes, riesgos regulatorios y de mercado.",
        "You are the CRYPTO analyst. Answer ONLY about its crypto exposure: recent facts, regulatory and market risks."),
}

# lo que cada MASCOTA sabe hacer al instante cuando le hablas (@cadena…) — lo muestra su ficha
# (core/agents_api → ventana «Agentes»; respaldo estático en engine/oswindows.js con el mismo texto)
SKILLS = {
    'analista': (['Lee sus estados financieros y ratios calculados al momento', 'La compara con sus pares en vivo',
                  'Márgenes y crecimiento reales de los últimos 12 meses', 'Abre «En una mirada» y el Dossier'],
                 ['Reads its financial statements and computed ratios on the spot', 'Compares it with live peers',
                  'Real margins and growth over the last 12 months', 'Opens "At a glance" and the Dossier']),
    'cadena': (['Mide cuánto depende de cada proveedor (tensor de la cadena)', 'En qué países están sus proveedores',
                'De dónde le llega el riesgo si un proveedor falla', 'A quién arrastra si falla ella y cuánto valor expone',
                'Eventos en vivo que tocan a sus proveedores', 'Abre la ventana «Cadena de suministro»'],
               ['Measures how much it depends on each supplier (chain tensor)', 'Which countries its suppliers are in',
                'Where risk comes from if a supplier fails', 'Who it drags down if it fails and how much value is exposed',
                'Live events touching its suppliers', 'Opens the "Supply chain" window']),
    'tecnico': (['Calcula medias de 50/200 días, RSI y retornos con precios de 1 año', 'Distancia al máximo y mínimo de 52 semanas',
                 'Caída máxima y fuerza frente al S&P 500', 'Dibuja el gráfico de precio'],
                ['Computes 50/200-day averages, RSI and returns from 1-year prices', 'Distance to the 52-week high and low',
                 'Max drawdown and strength versus the S&P 500', 'Draws the price chart']),
    'radar': (['Noticias de la empresa con fecha y fuente', 'Eventos en vivo que la nombran o la tocan',
               'Exposición geopolítica: su país y los de sus proveedores', 'Índice de riesgo geopolítico global (GPR)'],
              ['Company news with date and source', 'Live events that name or touch it',
               'Geopolitical exposure: its country and its suppliers’ countries', 'Global geopolitical risk index (GPR)']),
}


# la ventana / el gráfico que muestra cada rol (Khipus OS: engine/oswindows.js; gráficos: chat inline)
def role_actions(seat, eid, label, listed):
    if seat == 'supply_chain':
        return [{'type': 'open_window', 'arg': {'kind': 'supplychain', 'id': eid}}]
    if seat == 'fundamental':
        return [{'type': 'open_window', 'arg': {'kind': 'glance', 'id': eid}}, {'type': 'dossier', 'arg': eid}]
    if seat == 'technical' and listed:
        return [{'type': 'chart', 'arg': f'precio de {label} 1 año'}]
    if seat == 'geopolitical':
        return [{'type': 'open_world', 'arg': None}, {'type': 'open_window', 'arg': {'kind': 'supplychain', 'id': eid}}]
    if seat == 'news':
        return [{'type': 'dossier', 'arg': eid}]       # el Dossier trae sus noticias con fecha y fuente
    return []


def _fmt_pct(v, en=False):
    try:
        t = f'{float(v):.1f} %'
        return t.replace(' %', '%') if en else t.replace('.', ',')
    except (TypeError, ValueError):
        return '?'


def _supply_extras(eid):
    """S#: el tensor de la cadena (matrix/tensor.py) + eventos en vivo en sus proveedores."""
    lines, facts, sources = [], {}, []
    try:
        from matrix import tensor
        st = tensor.structure(eid) or {}
    except Exception as e:  # noqa: BLE001
        log.info('skills tensor: %s', type(e).__name__)
        st = {}
    if st:
        sc = st.get('supplier_concentration') or {}
        top = sc.get('top') or []
        if top:
            lines.append('Concentración de proveedores (tensor de flujo Khipus): nivel ' + str(sc.get('level')) +
                         f" (HHI {sc.get('hhi')}), {sc.get('n_suppliers')} proveedores; los que más pesan: " +
                         ', '.join(f"{t['label']} {_fmt_pct(t['share_pct'])} del peso" for t in top[:5]))
        if st.get('supplier_countries'):
            lines.append('Países de sus proveedores (por peso de los vínculos): ' +
                         ', '.join(f"{c['country']} {_fmt_pct(c['share_pct'])}" for c in st['supplier_countries'][:5]))
        if st.get('upstream_risk_sources'):
            lines.append('De dónde le llega el riesgo si un proveedor falla (impacto simulado en la red): ' +
                         ', '.join(f"{u['label']} {_fmt_pct(u['exposure_pct'])}" + ('' if u.get('direct') else ' (indirecto)')
                                   for u in st['upstream_risk_sources'][:5]))
        dn = st.get('downstream') or {}
        if dn.get('n_companies'):
            cap = dn.get('cap_at_risk_usd_b')
            lines.append(f"Si falla, arrastra a {dn['n_companies']} empresas aguas abajo" +
                         (f"; valor de mercado expuesto USD {str(cap).replace('.', ',')} mil millones (cobertura de capitalización {dn.get('cap_coverage_pct')} %)" if cap else '') +
                         f"; puesto sistémico {dn.get('systemic_rank')} de {dn.get('of')}. Más golpeadas: " +
                         ', '.join(f"{t['label']} {_fmt_pct(t['impact_pct'])}" for t in
                                   sorted(dn.get('top') or [], key=lambda t: -float(t.get('impact_pct') or 0))[:4]))
        if st.get('peers'):
            lines.append('Cadenas parecidas (comparables estructurales): ' + ', '.join(p['label'] for p in st['peers'][:4]))
        facts.update({'concentration': sc.get('level'), 'n_suppliers': sc.get('n_suppliers'),
                      'top_suppliers': [{'id': t['id'], 'label': t['label'], 'share_pct': t['share_pct']} for t in top[:5]],
                      'countries': (st.get('supplier_countries') or [])[:4],
                      'risk_sources': [{'id': u['id'], 'label': u['label'], 'pct': u['exposure_pct'], 'direct': u.get('direct')}
                                       for u in (st.get('upstream_risk_sources') or [])[:4]],
                      'downstream_n': dn.get('n_companies'), 'cap_at_risk_usd_b': dn.get('cap_at_risk_usd_b'),
                      'systemic_rank': dn.get('systemic_rank')})
        sources.append({'label': 'Tensor de la cadena Khipus (grafo curado + capitalizaciones en vivo)', 'as_of': st.get('caps_as_of')})
        ids = [eid] + [t['id'] for t in top[:3]]
    else:
        ids = [eid]
    try:
        from core.world import entity_geo_risks
        # con su PROPIO plazo: si el World Monitor está frío, la cadena (tensor) igual llega
        geo = _GEO_POOL.submit(entity_geo_risks, ids, wait=2.5).result(timeout=GEO_TIMEOUT_S) or {}
        for nid in ids:
            for it in (geo.get(nid) or [])[:2]:
                who = 'la empresa' if nid == eid else f'su proveedor {nid}'
                lines.append(f"Evento en vivo que toca a {who}: {it.get('title_es')} (severidad {it.get('severity')}, "
                             f"{it.get('why_es')}, fuente {it.get('source')}, {it.get('time') or 's/f'})")
        if any(geo.get(n) for n in ids):
            sources.append({'label': 'World Monitor Khipus (capas en vivo y oficiales)', 'as_of': None})
    except Exception as e:  # noqa: BLE001
        log.info('skills geo: %s', type(e).__name__)
    return lines, facts, sources


def _geo_extras(eid):
    lines, facts, sources = _supply_extras(eid)
    keep = [l for l in lines if l.startswith(('Países', 'Evento'))]
    return keep, {'countries': facts.get('countries'), 'risk_sources': facts.get('risk_sources')}, sources


def _news_extras(eid):
    lines, sources = [], []
    try:
        from core.world import entity_geo_risks
        for it in (entity_geo_risks([eid], wait=2.5) or {}).get(eid, [])[:3]:
            lines.append(f"Evento en vivo que la nombra o la toca: {it.get('title_es')} ({it.get('why_es')}, "
                         f"fuente {it.get('source')}, {it.get('time') or 's/f'})")
        if lines:
            sources.append({'label': 'World Monitor Khipus', 'as_of': None})
    except Exception:  # noqa: BLE001
        pass
    return lines, {}, sources


def _fund_extras(eid):
    lines, facts, sources = [], {}, []
    try:
        from core.live_fundamentals import get_all
        f = ((get_all() or {}).get('fund') or {}).get(eid) or {}
        if f:
            parts = []
            for k, lab in (('operating_margin', 'margen operativo'), ('profit_margin', 'margen neto'),
                           ('gross_margin', 'margen bruto'), ('revenue_growth_q', 'crecimiento de ingresos del último trimestre')):
                if f.get(k) is not None:
                    parts.append(f'{lab} {_fmt_pct(f[k])}')
            if f.get('revenue_ttm_usd_b') is not None:
                parts.append(f"ingresos 12 meses USD {f['revenue_ttm_usd_b']} mil millones")
            if parts:
                lines.append('Fundamentales en vivo (' + str(f.get('source') or 'yahoo') + '): ' + ', '.join(parts))
                sources.append({'label': 'Fundamentales en vivo (' + str(f.get('source') or 'Yahoo') + ')', 'as_of': f.get('as_of')})
                facts.update({k: f.get(k) for k in ('operating_margin', 'revenue_growth_q', 'revenue_ttm_usd_b')})
    except Exception:  # noqa: BLE001
        pass
    return lines, facts, sources


def _macro_extras(eid):
    lines, sources = [], []
    try:
        from core.gpr import gpr_cached
        g = gpr_cached()
        d = (g or {}).get('daily') or {}
        if d.get('value') is not None:
            lines.append(f"Índice de riesgo geopolítico global (GPR, Caldara-Iacoviello): {d.get('value')} "
                         f"(100 = promedio 1985-2019; promedio 30 días {d.get('avg30')}), dato del {d.get('date') or 's/f'}")
            sources.append({'label': 'GPR — Reserva Federal (Caldara & Iacoviello)', 'as_of': g.get('as_of')})
    except Exception:  # noqa: BLE001
        pass
    return lines, {}, sources


EXTRAS = {'supply_chain': _supply_extras, 'geopolitical': _geo_extras, 'news': _news_extras,
          'fundamental': _fund_extras, 'macro': _macro_extras}
DEPTH = {'fundamental': 'STANDARD'}     # el fundamental necesita pares (no vienen en QUICK)


def _context(eid, seat):
    from research.context import ContextBuilder
    return ContextBuilder().build(eid, seat, depth=DEPTH.get(seat, 'QUICK'))


def _indicator_facts(ctx):
    """Para el Técnico: los indicadores calculados que trae la evidencia 'analysis' de research/context."""
    for x in (ctx or {}).get('evidence') or []:
        if x.get('source_type') in ('analysis', 'candles', 'computed') and 'RSI' in str(x.get('excerpt') or ''):
            return {'indicators': str(x.get('excerpt'))[:400]}
    return {}


def skill_packet(seat, eid):
    """→ {text, facts, sources, n_evidence, ok}. Corre la evidencia del rol y sus extras EN PARALELO; nunca lanza."""
    from research.context import render_context
    fut_ctx = _POOL.submit(_context, eid, seat)
    fut_ex = _POOL.submit(EXTRAS[seat], eid) if seat in EXTRAS else None
    ctx, ex_lines, facts, sources = None, [], {}, []
    try:
        ctx = fut_ctx.result(timeout=CTX_TIMEOUT_S)
    except _FutTimeout:
        log.info('skills ctx timeout %s %s', seat, eid)
    except Exception as e:  # noqa: BLE001
        log.info('skills ctx %s: %s', seat, type(e).__name__)
    if fut_ex is not None:
        try:
            ex_lines, facts, sources = fut_ex.result(timeout=EXTRA_TIMEOUT_S)
        except Exception as e:  # noqa: BLE001
            log.info('skills extra %s: %s', seat, type(e).__name__)
    parts = []
    if ctx:
        parts.append(render_context(ctx))
        for x in ctx.get('evidence') or []:
            sources.append({'label': x.get('title') or x.get('source_type'), 'as_of': x.get('published_at') or x.get('retrieved_at')})
        if seat == 'technical':
            facts.update(_indicator_facts(ctx))
    if ex_lines:
        parts.append('HABILIDADES DE TU ROL (datos en vivo; cítalos como [S#]):')
        parts.extend(f'S{i} <data>{l}</data>' for i, l in enumerate(ex_lines, 1))
    n_ev = len((ctx or {}).get('evidence') or []) + len(ex_lines)
    return {'text': '\n'.join(parts), 'facts': facts, 'sources': sources[:10], 'n_evidence': n_ev, 'ok': n_ev > 0,
            'listed': bool(((ctx or {}).get('entity') or {}).get('mkt'))}


_pct = _fmt_pct


def note_for(seat, label, facts, lang='es'):
    """Resumen DETERMINISTA (para la tarjeta de aportes del chat): solo valores de `facts`."""
    en = lang == 'en'

    def _fmt_pct(v):
        return _pct(v, en)
    if seat == 'supply_chain' and facts.get('top_suppliers'):
        t = facts['top_suppliers'][0]
        rs = facts.get('risk_sources') or []
        risk = (f"; mayor riesgo: {rs[0]['label']} ({_fmt_pct(rs[0]['pct'])})" if rs and not en else
                f"; biggest risk: {rs[0]['label']} ({_fmt_pct(rs[0]['pct'])})" if rs else '')
        return (f"{label} depends most on {t['label']} ({_fmt_pct(t['share_pct'])} of supplier weight){risk}" if en else
                f"{label} depende sobre todo de {t['label']} ({_fmt_pct(t['share_pct'])} del peso de sus proveedores){risk}")
    if seat == 'fundamental' and facts.get('operating_margin') is not None:
        return (f"Live operating margin {_fmt_pct(facts['operating_margin'])}" if en else
                f"Margen operativo en vivo {_fmt_pct(facts['operating_margin'])}")
    if seat == 'geopolitical' and facts.get('countries'):
        c = facts['countries'][0]
        return (f"Main supplier country: {c['country']} ({_fmt_pct(c['share_pct'])})" if en else
                f"País principal de sus proveedores: {c['country']} ({_fmt_pct(c['share_pct'])})")
    return None
