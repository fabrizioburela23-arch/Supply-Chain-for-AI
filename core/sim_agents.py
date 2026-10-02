"""core/sim_agents.py — Motor de simulación POR AGENTES (interno).

Visión de Fabrizio (verbatim): "un clon de MiroFish en estructura que simule a
través de agentes, donde cada nodo es un agente más los agentes gobierno u
otros externos".

Nota histórica: MiroFish era un microservicio EXTERNO que se usó al principio.
Se retiró (2026-09); este módulo, que nació imitando su estructura, es hoy el
motor de agentes de la app. No queda ninguna dependencia de aquel servicio.

Idea: ante un escenario (p.ej. "China prohíbe exportar galio y germanio") armamos
un ELENCO de agentes —cada empresa relevante del grafo + agentes externos
(gobiernos, geopolítica, mercado de capitales, sectores)— y dejamos que Sonnet 5
razone, EN RONDAS, cómo reacciona cada uno y cómo se propaga el golpe por la
cadena de suministro. Devolvemos impactos con magnitudes REALISTAS y acotadas
(el bug reportado: "OpenAI descubre AGI → +30%" es absurdo), una narrativa para
no-expertos y el roster de agentes.

FUNCIÓN PÚBLICA (firma EXACTA):

    run(scenario: str, seeds: list, lang: str) -> dict

Forma EXACTA del dict devuelto:
    {
      "ok": True,
      "narrative": str,
      "impacts": [{"id": str, "label": str, "pct": float, "rationale": str}],
      "agents":  [{"name": str, "type": str, "stance": str}],
      "rounds":  [{"round": int, "events": [str]}],
    }

Robustez: si la IA no está disponible o falla, devuelve un fallback determinista
razonable (propagación por la cadena con magnitudes acotadas) para que la DEMO
nunca se caiga. NUNCA lanza excepción hacia arriba.

Depende solo de `core.ai` (cascada multi-IA, tier='deep' = Sonnet 5) y
`core.semantic` (snapshot data/grafo_v0.json). No importa server ni la BD.
"""
import json
import os

from core import ai, semantic

# ── Parámetros del motor ────────────────────────────────────────────────────
ROUNDS = 2                 # 2-3 rondas de simulación (2 mantiene la demo ágil)
MAX_COMPANIES = 14         # tope de agentes-empresa en el elenco
NEIGHBORS_PER_SEED = 4     # vecinos de cada semilla que entran al elenco
MAX_EDGES = 44             # relaciones de la cadena que se le pasan a la IA

# Cota de movimiento por tipo/tamaño de empresa (en % en el corto plazo).
# Mega-caps diversificadas se mueven poco; pre-revenue / small caps más.
_BOUNDS = {'mega': 12.0, 'mid': 20.0, 'small': 35.0}


# ── Micro-dict bilingüe (solo para textos que generamos nosotros) ───────────
def _es(lang):
    return not str(lang or 'es').lower().startswith('en')


# ── Catálogo de agentes EXTERNOS siempre presentes ──────────────────────────
_EXTERNALS = [
    {'type': 'gobierno', 'es': 'Gobierno EE.UU.', 'en': 'US Government',
     'stance_es': 'Regulación · subsidios · controles de exportación',
     'stance_en': 'Regulation · subsidies · export controls'},
    {'type': 'gobierno', 'es': 'Gobierno China', 'en': 'China Government',
     'stance_es': 'Contramedidas · autosuficiencia',
     'stance_en': 'Countermeasures · self-sufficiency'},
    {'type': 'geopolitica', 'es': 'Geopolítica / Taiwán', 'en': 'Geopolitics / Taiwan',
     'stance_es': 'Riesgo del estrecho', 'stance_en': 'Taiwan Strait risk'},
    {'type': 'mercado', 'es': 'Mercado de capitales', 'en': 'Capital markets',
     'stance_es': 'Flujos y sentimiento', 'stance_en': 'Flows and sentiment'},
]


# ── sectores9 (etiquetas bonitas de sector) — lectura cacheada del snapshot ──
_SEC = {'data': None}


def _sectors9():
    if _SEC['data'] is None:
        try:
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'data', 'grafo_v0.json')
            with open(path, 'r', encoding='utf-8') as f:
                g = json.load(f)
            _SEC['data'] = g.get('sectors9') or {}
        except Exception:  # noqa: BLE001
            _SEC['data'] = {}
    return _SEC['data']


def _sector_label(sec, lang):
    m = _sectors9().get(sec) or {}
    if _es(lang):
        return m.get('label') or (sec or 'sector')
    return m.get('en') or m.get('label') or (sec or 'sector')


# ── Heurísticas de nodo (autocontenidas, sin BD) ────────────────────────────
def _size_class(n):
    """mega (diversificada) · small (pre-revenue/preipo) · mid (resto)."""
    if n.get('big'):
        return 'mega'
    m = n.get('margin')
    if n.get('preipo') or (isinstance(m, (int, float)) and m <= 0):
        return 'small'
    return 'mid'


def _approx_nrs(snap, nid):
    """NRS aproximado 0-100 (más alto = más frágil). Réplica ligera de la idea
    del NRS del cliente usando solo campos del snapshot; es CONTEXTO para la IA,
    no la fórmula canónica (esa vive en el cliente / ontology.agents)."""
    n = snap['by_id'].get(nid) or {}
    score = 45.0
    m = n.get('margin')
    if isinstance(m, (int, float)):
        if m <= 0:
            score += 22
        elif m < 0.10:
            score += 8
        elif m > 0.30:
            score -= 12
    else:
        score += 6
    country = (n.get('country') or '').strip().lower()
    if country in ('china', 'taiwan', 'taiwán'):
        score += 14
    elif country in ('rusia', 'russia'):
        score += 10
    deg = snap['deg'].get(nid, 0)
    if deg <= 1:
        score += 10
    elif deg >= 12:
        score += 6
    if n.get('preipo'):
        score += 8
    return int(max(5, min(95, round(score))))


def _neighbors(snap, nid, k):
    cand = []
    for l in snap['in'].get(nid, []):
        cand.append((l.get('w') or 0, l.get('source')))
    for l in snap['out'].get(nid, []):
        cand.append((l.get('w') or 0, l.get('target')))
    cand.sort(key=lambda x: -(x[0] or 0))
    out = []
    for _, x in cand:
        if x and x != nid and x in snap['by_id'] and x not in out:
            out.append(x)
        if len(out) >= k:
            break
    return out


def _mentioned(nid, snap, text):
    """¿La empresa aparece como PALABRA completa en el escenario? (antes "XPO"
    entraba como semilla porque la sigla está dentro de "eXPOrtar")."""
    n = snap['by_id'].get(nid) or {}
    import re as _re
    for cand in (n.get('label'), n.get('mkt'), nid):
        c = str(cand or '').strip()
        if len(c) >= 2 and _re.search(r'(?<![\w])' + _re.escape(c) + r'(?![\w])', text, _re.I):
            return True
    return False


def _inside_word(nid, snap, text):
    n = snap['by_id'].get(nid) or {}
    low = (text or '').lower()
    return any(len(str(c or '')) >= 2 and str(c).lower() in low for c in (n.get('label'), n.get('mkt'), nid))


def _seed_ids(seeds, snap, scenario=''):
    ids = semantic.resolve_ids(seeds) if seeds else []
    ids = [i for i in ids if i in snap['by_id']]
    if scenario:
        # se descarta una semilla SOLO si su nombre/sigla aparece DENTRO de otra palabra
        # y nunca como palabra completa ("XPO" en "eXPOrtar"); una semilla explícita
        # (voz, usuario) que no figura en el texto se respeta
        ids = [i for i in ids if _mentioned(i, snap, scenario) or not _inside_word(i, snap, scenario)]
    if not ids and scenario:
        # las empresas NOMBRADAS en el texto del escenario (nombre o ticker)
        try:
            from core.live_facts import detect_entities
            ids = [i for i in detect_entities(scenario, limit=6) if i in snap['by_id']]
        except Exception:  # noqa: BLE001
            ids = []
    # Sin semillas: NO se inventa un elenco (antes: los 3 mayores chokepoints,
    # con % para empresas que el escenario ni menciona — 2026-09-29).
    return list(dict.fromkeys(ids))


def _no_seeds(lang):
    msg = ('No reconocí ninguna empresa en el escenario. Nombra al menos una (p. ej. '
           '"¿qué pasa si TSMC deja de producir?") para simular a quién afecta.'
           if _es(lang) else
           'I did not recognize any company in the scenario. Name at least one (e.g. '
           '"what if TSMC stops producing?") to simulate who is affected.')
    return {'ok': True, 'no_seeds': True, 'narrative': msg, 'impacts': [],
            'agents': _external_agents([], lang), 'rounds': []}


def _build_company_agents(seed_ids, snap):
    ids = list(seed_ids)
    for sid in list(seed_ids):
        for nb in _neighbors(snap, sid, NEIGHBORS_PER_SEED):
            if nb not in ids:
                ids.append(nb)
            if len(ids) >= MAX_COMPANIES:
                break
        if len(ids) >= MAX_COMPANIES:
            break
    ids = ids[:MAX_COMPANIES]
    seedset = set(seed_ids)
    agents = []
    for nid in ids:
        n = snap['by_id'][nid]
        agents.append({
            'id': nid,
            'label': n.get('label') or nid,
            'sector': n.get('sector'),
            'country': n.get('country'),
            'nrs': _approx_nrs(snap, nid),
            'role': (n.get('role') or n.get('role_en') or '')[:160],
            'size': _size_class(n),
            'is_seed': nid in seedset,
        })
    return agents


def _cast_edges(cast_ids, snap):
    idset = set(cast_ids)
    edges, seen = [], set()
    for cid in cast_ids:
        for l in snap['out'].get(cid, []):
            t = l.get('target')
            if t in idset:
                key = (cid, t, l.get('type'))
                if key in seen:
                    continue
                seen.add(key)
                edges.append({'from': cid, 'to': t, 'type': l.get('type'),
                              'rel': (l.get('rel') or '')[:80]})
                if len(edges) >= MAX_EDGES:
                    return edges
    return edges


def _sector_agents(company_agents, lang, limit=3):
    counts = {}
    for a in company_agents:
        s = a.get('sector')
        if s:
            counts[s] = counts.get(s, 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:limit]
    out = []
    for sec, _ in top:
        out.append({
            'name': _sector_label(sec, lang),
            'type': 'sector',
            'stance': 'Sector en foco' if _es(lang) else 'Sector in focus',
        })
    return out


def _external_agents(company_agents, lang):
    out = []
    for e in _EXTERNALS:
        out.append({
            'name': e['es'] if _es(lang) else e['en'],
            'type': e['type'],
            'stance': e['stance_es'] if _es(lang) else e['stance_en'],
        })
    out.extend(_sector_agents(company_agents, lang))
    return out


# ── Clamp de magnitudes ─────────────────────────────────────────────────────
def _clamp_pct(pct, size):
    b = _BOUNDS.get(size, 20.0)
    try:
        p = float(pct)
    except (TypeError, ValueError):
        p = 0.0
    if p > b:
        p = b
    elif p < -b:
        p = -b
    return round(p, 1)


def _stance_from_pct(pct, lang):
    if pct >= 3:
        return 'Beneficiado' if _es(lang) else 'Benefiting'
    if pct <= -3:
        return 'Perjudicado' if _es(lang) else 'Hit'
    return 'Neutral'


# ── Prompt / IA ─────────────────────────────────────────────────────────────
def _system(lang):
    idioma = 'español' if _es(lang) else 'English'
    return (
        "Eres el MOTOR de una simulación financiera POR AGENTES de la cadena de "
        "suministro global de IA, semiconductores, espacio y energía. Cada empresa "
        "es un AGENTE con intereses propios; además hay agentes EXTERNOS (gobiernos, "
        "geopolítica, mercado de capitales, sectores). Simulas cómo un escenario se "
        "PROPAGA por la cadena: quién sube, quién baja y por qué.\n\n"
        "REGLAS DE REALISMO (obligatorias):\n"
        "- Las magnitudes deben ser REALISTAS y acotadas. Una sola noticia rara vez "
        "mueve a una empresa grande y diversificada más de ~10-12% en el corto plazo; "
        "empresas medianas hasta ~20%; pre-revenue / small caps hasta ~35%. Respeta "
        "el campo 'limite_pct' de cada empresa: NO lo superes en valor absoluto.\n"
        "- NO todos se mueven igual ni en la misma dirección: algunos SUBEN "
        "(sustitutos, beneficiarios, competidores que ganan cuota) y otros BAJAN "
        "(proveedores que pierden un cliente, clientes que pierden suministro). "
        "Prohibido 'todos +30%'.\n"
        "- Explica CADA movimiento con un 'rationale' breve y concreto.\n"
        "- Piensa la reacción de los agentes EXTERNOS (¿el gobierno responde con "
        "controles, subsidios, contramedidas? ¿el mercado castiga el riesgo?).\n\n"
        f"Redacta TODOS los textos (events, rationale, narrative) en {idioma}.\n"
        "Devuelve EXCLUSIVAMENTE un objeto JSON válido, sin texto fuera del JSON."
    )


def _round_prompt(scenario, company_agents, externals, edges, state, rnd, total, lang, analysis=None):
    empresas = [{
        'id': a['id'], 'label': a['label'], 'sector': a['sector'],
        'pais': a['country'], 'nrs': a['nrs'], 'tamano': a['size'],
        'limite_pct': _BOUNDS.get(a['size'], 20.0), 'rol': a['role'],
        'semilla': a['is_seed'],
    } for a in company_agents]
    externos = [{'nombre': e['name'], 'tipo': e['type']} for e in externals]
    estado = {k: round(v['pct'], 1) for k, v in state.items()}
    payload = {
        'escenario': scenario,
        'idioma': 'es' if _es(lang) else 'en',
        'ronda': rnd, 'rondas_totales': total,
        'empresas': empresas,
        'agentes_externos': externos,
        'cadena_de_suministro': edges,
        'estado_acumulado_previo_pct': estado,
    }
    if analysis:
        payload['analisis_estructural'] = {
            'tema': analysis.get('theme_es'), 'actor': analysis.get('actor_es'), 'evento': analysis.get('event'),
            'mecanismo': analysis.get('mechanism_es'),
            'impactos_por_cadena': [{'id': x['id'], 'canal': x['channel'], 'severidad': x['sev'],
                                     'camino': x['path']} for x in analysis['impacts'][:14]]}
    forma = (
        '{\n'
        '  "events": ["hecho concreto de esta ronda", ...],\n'
        '  "impacts": [{"id": "<id de empresa>", "pct": <número, impacto ACUMULADO en %>, '
        '"rationale": "<por qué, breve>"}, ...],\n'
        '  "narrative": "<síntesis breve para un inversor NO experto>",\n'
        '  "quotes": [{"agent": "<nombre del agente>", "quote": "<qué diría, 1 frase>"}, ...],\n'
        '  "watch": ["<dato concreto que conviene vigilar>", ...]\n'
        '}'
    )
    return (
        f"Contexto de la simulación (JSON):\n{json.dumps(payload, ensure_ascii=False)}\n\n"
        f"Es la ronda {rnd} de {total}. Razona cómo reacciona CADA agente al escenario "
        f"y cómo se propaga por la cadena de suministro, partiendo del estado acumulado. "
        f"Actualiza los impactos ACUMULADOS (no incrementales) de las empresas afectadas, "
        f"respetando 'limite_pct'. Usa 'analisis_estructural' (si existe) como base: quién recibe el golpe, "
        f"quién podría ganar y por qué camino; corrígelo si tu razonamiento lo justifica. "
        f"Devuelve SOLO este JSON:\n{forma}"
    )


# ── Síntesis / fallback de textos ───────────────────────────────────────────
def _synth_narrative(scenario, impacts, lang):
    if not impacts:
        if _es(lang):
            return f"Escenario «{scenario}»: sin impactos materiales detectados en el elenco simulado."
        return f"Scenario '{scenario}': no material impacts detected across the simulated cast."
    top = impacts[:3]
    def fmt(i):
        sign = '+' if i['pct'] >= 0 else ''
        return f"{i['label']} {sign}{i['pct']}%"
    movs = ', '.join(fmt(i) for i in top)
    if _es(lang):
        return (f"Escenario «{scenario}»: los movimientos más fuertes son {movs}. "
                f"El golpe se propaga por la cadena de suministro; algunos actores "
                f"se benefician y otros se ven perjudicados según su rol.")
    return (f"Scenario '{scenario}': the strongest moves are {movs}. "
            f"The shock propagates through the supply chain; some players benefit "
            f"and others are hit depending on their role.")


def _default_event(rnd, lang):
    if _es(lang):
        return f"Ronda {rnd}: los agentes reajustan posiciones y el impacto se propaga por la cadena."
    return f"Round {rnd}: agents readjust and the impact propagates through the chain."


# ── Análisis estructural (core/scenario_engine) → impactos y extras ─────────
def _struct_pct(sev, size, direct=False):
    return _clamp_pct(sev * _BOUNDS.get(size, 20.0) * (1.0 if direct else 0.7), size)


_CHANNEL = {
    'direct': ('Golpe directo del escenario.', 'Direct hit from the scenario.'),
    'substitute': ('Podría ganar cuota como alternativa.', 'Could gain share as an alternative.'),
    'customer': ('Cliente: depende de ese suministro.', 'Customer: depends on that supply.'),
    'second_order': ('Efecto de segundo orden por la cadena.', 'Second-order effect through the chain.'),
    'supplier': ('Proveedor: cambian sus pedidos.', 'Supplier: its orders change.'),
}


def _struct_impacts(analysis, snap, lang):
    out = []
    for x in analysis['impacts']:
        n = snap['by_id'].get(x['id']) or {}
        p = _struct_pct(x['sev'], _size_class(n), direct=x['channel'] == 'direct')
        if abs(p) < 0.5:
            continue
        ch = _CHANNEL.get(x['channel'], ('', ''))
        why = ch[0] if _es(lang) else ch[1]
        out.append({'id': x['id'], 'label': x['label'], 'pct': p, 'channel': x['channel'],
                    'path': x['path'], 'rationale': (why + (' ' + x['path'] if x['path'] and '→' in x['path'] else '')).strip()})
    return out          # orden del análisis: magnitud × relevancia (no solo el %)


def _struct_extras(analysis, lang):
    es = _es(lang)
    return {'mechanism': analysis['mechanism_es'] if es else analysis['mechanism_en'],
            'theme': analysis['theme_es'] if es else analysis['theme_en'],
            'actor': analysis['actor_es'] if es else analysis['actor_en'],
            'event': analysis['event'],
            'watch': analysis['watch_es'] if es else analysis['watch_en'],
            'summary': analysis['summary']}


def _struct_narrative(scenario, analysis, impacts, lang):
    es = _es(lang)
    losers = [i for i in impacts if i['pct'] < 0][:3]
    winners = [i for i in impacts if i['pct'] > 0][:3]
    f = lambda i: f"{i['label']} {'+' if i['pct'] >= 0 else ''}{i['pct']}%"  # noqa: E731
    parts = []
    th = analysis['theme_es'] if es else analysis['theme_en']
    if th:
        parts.append((f'En juego: {th}.' if es else f'At stake: {th}.'))
    mech = analysis['mechanism_es'] if es else analysis['mechanism_en']
    if mech:
        parts.append(mech)
    if losers:
        parts.append(('Más perjudicadas: ' if es else 'Most hit: ') + ', '.join(f(i) for i in losers) + '.')
    if winners:
        parts.append(('Posibles ganadoras: ' if es else 'Possible winners: ') + ', '.join(f(i) for i in winners) + '.')
    return ' '.join(parts) or _synth_narrative(scenario, impacts, lang)


# ── Fallback determinista (IA caída) ────────────────────────────────────────
def _fallback(scenario, seed_ids, company_agents, externals, snap, lang, analysis=None):
    if analysis:
        impacts = _struct_impacts(analysis, snap, lang)
        prefix = '(estimación estructural, sin IA) ' if _es(lang) else '(structural estimate, no AI) '
        agents = _roster(company_agents, externals, {i['id']: i['pct'] for i in impacts}, lang)
        out = {'ok': True, 'fallback': True, 'structural': True, 'seeds': list(seed_ids),
               'narrative': prefix + _struct_narrative(scenario, analysis, impacts, lang),
               'impacts': impacts, 'agents': agents, 'rounds': analysis['timeline']}
        out.update(_struct_extras(analysis, lang))
        return out
    return _fallback_basic(scenario, seed_ids, company_agents, externals, snap, lang)


def _fallback_basic(scenario, seed_ids, company_agents, externals, snap, lang):
    """Propagación acotada por la cadena, sin IA. Las semillas reciben un golpe
    base y los vecinos lo reciben atenuado. Magnitudes SIEMPRE acotadas."""
    seedset = set(seed_ids)
    size_by = {a['id']: a['size'] for a in company_agents}
    label_by = {a['id']: a['label'] for a in company_agents}
    base = -8.0
    raw = {}
    for a in company_agents:
        nid = a['id']
        if nid in seedset:
            raw[nid] = base
        else:
            # ¿está conectado a alguna semilla? (proveedor o cliente directo)
            linked = False
            for sid in seed_ids:
                outs = {l.get('target') for l in snap['out'].get(sid, [])}
                ins = {l.get('source') for l in snap['in'].get(sid, [])}
                if nid in outs or nid in ins:
                    linked = True
                    break
            raw[nid] = base * 0.5 if linked else base * 0.2
    impacts = []
    for nid, pct in raw.items():
        p = _clamp_pct(pct, size_by.get(nid, 'mid'))
        if p == 0:
            continue
        if _es(lang):
            rat = ("Empresa semilla del escenario; recibe el golpe directo."
                   if nid in seedset else
                   "Expuesta a la semilla por la cadena de suministro (estimación).")
        else:
            rat = ("Scenario seed company; takes the direct hit."
                   if nid in seedset else
                   "Exposed to the seed through the supply chain (estimate).")
        impacts.append({'id': nid, 'label': label_by.get(nid, nid), 'pct': p, 'rationale': rat})
    impacts.sort(key=lambda i: -abs(i['pct']))

    prefix = '(estimación sin IA) ' if _es(lang) else '(estimate without AI) '
    narrative = prefix + _synth_narrative(scenario, impacts, lang)
    agents = _roster(company_agents, externals, {i['id']: i['pct'] for i in impacts}, lang)
    if _es(lang):
        rounds = [
            {'round': 1, 'events': ['El escenario golpea primero a las empresas semilla.']},
            {'round': 2, 'events': ['El impacto se propaga a proveedores y clientes directos.']},
        ]
    else:
        rounds = [
            {'round': 1, 'events': ['The scenario first hits the seed companies.']},
            {'round': 2, 'events': ['The impact propagates to direct suppliers and customers.']},
        ]
    # fallback=True: el cliente dibuja el motor ESTRUCTURAL (severidad 0-100,
    # misma matemática que matrix/engine.py) desde `seeds`, rotulado sin IA;
    # estos % base fijos quedan solo como referencia para otros consumidores.
    return {'ok': True, 'fallback': True, 'seeds': list(seed_ids), 'narrative': narrative,
            'impacts': impacts, 'agents': agents, 'rounds': rounds}


def _roster(company_agents, externals, pct_by_id, lang):
    """Elenco final: cada empresa es un agente (con postura según su impacto) +
    los agentes externos + agentes de sector."""
    agents = []
    for a in company_agents:
        agents.append({
            'name': a['label'],
            'type': 'empresa',
            'stance': _stance_from_pct(pct_by_id.get(a['id'], 0.0), lang),
        })
    agents.extend(externals)
    return agents


# ── API pública ─────────────────────────────────────────────────────────────
def run(scenario, seeds, lang='es'):
    """Simula un escenario por agentes. Firma EXACTA: run(scenario, seeds, lang).

    Devuelve el dict del contrato (ver docstring del módulo). NUNCA lanza."""
    try:
        return _run_impl(str(scenario or '').strip(), list(seeds or []), lang)
    except Exception as e:  # noqa: BLE001 — la demo nunca se cae
        # Último recurso: intentar un fallback mínimo; si hasta eso falla,
        # devolver una forma válida vacía.
        try:
            snap = semantic._load_snapshot()
            seed_ids = _seed_ids(seeds, snap, str(scenario or ''))
            if not seed_ids:
                return _no_seeds(lang)
            company_agents = _build_company_agents(seed_ids, snap)
            externals = _external_agents(company_agents, lang)
            return _fallback(str(scenario or ''), seed_ids, company_agents, externals, snap, lang)
        except Exception:  # noqa: BLE001
            prefix = '(estimación sin IA) ' if _es(lang) else '(estimate without AI) '
            return {'ok': True,
                    'narrative': prefix + (f'error interno: {str(e)[:120]}'),
                    'impacts': [], 'agents': _external_agents([], lang), 'rounds': []}


def _cast_from_analysis(analysis, snap):
    seedset = set(analysis['hit']) | set(analysis['benefit']) | set(analysis['producers'])
    agents = []
    for x in analysis['impacts'][:MAX_COMPANIES]:
        n = snap['by_id'][x['id']]
        agents.append({'id': x['id'], 'label': n.get('label') or x['id'], 'sector': n.get('sector'),
                       'country': n.get('country'), 'nrs': _approx_nrs(snap, x['id']),
                       'role': (n.get('role') or n.get('role_en') or '')[:160], 'size': _size_class(n),
                       'is_seed': x['id'] in seedset})
    return agents


def _run_impl(scenario, seeds, lang):
    from core import scenario_engine
    snap = semantic._load_snapshot()
    seed_ids = _seed_ids(seeds, snap, scenario)
    try:
        analysis = scenario_engine.analyze(scenario, snap, named_ids=seed_ids, lang=lang)
    except Exception:  # noqa: BLE001 — el análisis estructural nunca rompe la simulación
        analysis = None
    if analysis:
        seed_ids = list(dict.fromkeys(analysis['hit'] + analysis['benefit'] + seed_ids))
    if not seed_ids:
        return _no_seeds(lang)
    company_agents = _cast_from_analysis(analysis, snap) if analysis else _build_company_agents(seed_ids, snap)
    externals = _external_agents(company_agents, lang)
    edges = _cast_edges([a['id'] for a in company_agents], snap)
    cast_by_id = {a['id']: a for a in company_agents}

    if not ai._ai_configured():
        return _fallback(scenario, seed_ids, company_agents, externals, snap, lang, analysis)

    state = {}          # id -> {'pct': float, 'rationale': str}
    quotes, watch_ai = [], []
    rounds_out = []
    model_narrative = ''
    ai_ok = False
    used_model = ''     # qué IA razonó de verdad (transparencia en la UI)
    dbg = ['agents=%d' % len(company_agents)]

    for r in range(1, ROUNDS + 1):
        try:
            raw, _model = ai._ai_complete(
                _system(lang),
                _round_prompt(scenario, company_agents, externals, edges, state, r, ROUNDS, lang, analysis),
                max_tokens=1900, tier='deep')
            data = ai._extract_json(raw)
        except Exception as e:  # noqa: BLE001 — una ronda que falla no rompe la demo
            dbg.append('r%d EXC: %s' % (r, str(e)[:200]))
            break
        if not isinstance(data, dict):
            dbg.append('r%d nodict raw=%s' % (r, str(raw)[:150]))
            break
        dbg.append('r%d ok model=%s keys=%s' % (r, _model, list(data.keys())))
        ai_ok = True
        if _model:
            used_model = _model

        evs = [str(e).strip() for e in (data.get('events') or []) if str(e).strip()][:8]
        if not evs:
            evs = [_default_event(r, lang)]
        rounds_out.append({'round': r, 'events': evs})

        for imp in (data.get('impacts') or []):
            if not isinstance(imp, dict):
                continue
            nid = imp.get('id')
            if nid in cast_by_id:
                prev = state.get(nid, {})
                state[nid] = {
                    'pct': imp.get('pct', prev.get('pct', 0)),
                    'rationale': str(imp.get('rationale') or prev.get('rationale') or '')[:200],
                }
        nar = str(data.get('narrative') or '').strip()
        if nar:
            model_narrative = nar
        for q in (data.get('quotes') or []):
            if isinstance(q, dict) and q.get('agent') and q.get('quote'):
                quotes.append({'agent': str(q['agent'])[:60], 'quote': str(q['quote'])[:260]})
        watch_ai = [str(w)[:160] for w in (data.get('watch') or []) if str(w).strip()][:4] or watch_ai

    if not ai_ok or not state:
        _res = _fallback(scenario, seed_ids, company_agents, externals, snap, lang, analysis)
        _res['_dbg'] = dbg + ['-> fallback (ai_ok=%s state=%d)' % (ai_ok, len(state))]
        return _res

    impacts = []
    for nid, v in state.items():
        a = cast_by_id[nid]
        p = _clamp_pct(v['pct'], a['size'])
        impacts.append({'id': nid, 'label': a['label'], 'pct': p,
                        'rationale': v['rationale'] or ''})
    impacts.sort(key=lambda i: -abs(i['pct']))

    narrative = model_narrative or _synth_narrative(scenario, impacts, lang)
    agents = _roster(company_agents, externals, {i['id']: i['pct'] for i in impacts}, lang)

    out = {'ok': True, 'narrative': narrative, 'impacts': impacts,
           'agents': agents, 'rounds': rounds_out, 'model': used_model, 'quotes': quotes[:8]}
    if analysis:
        paths = {x['id']: x['path'] for x in analysis['impacts']}
        chans = {x['id']: x['channel'] for x in analysis['impacts']}
        for i in impacts:
            i.setdefault('path', paths.get(i['id'], ''))
            i.setdefault('channel', chans.get(i['id']))
        out.update(_struct_extras(analysis, lang))
        if watch_ai:
            out['watch'] = list(dict.fromkeys(watch_ai + out.get('watch', [])))[:7]
    return out
