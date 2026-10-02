"""core/scenario_engine.py — ANÁLISIS ESTRUCTURAL de un escenario (sin IA).

Feedback (2026-10-02, captura "China prohíbe exportar HBM"): la simulación por
agentes sin IA (1) eligió XPO como semilla (la sigla aparece dentro de
"eXPOrtar"), (2) daba −8 % / −4 % fijos y (3) casi no explicaba nada.

Este módulo entiende el escenario con reglas y el grafo:
  · TEMA: qué producto/insumo está en juego (HBM, CoWoS, EUV, tierras raras,
    galio, litio, cobre, uranio, energía, obleas…) → sus PRODUCTORES en el grafo;
    si no hay tema conocido, búsqueda en las fichas (rol/suministros) del grafo.
  · ACTOR: qué país actúa (China, EE.UU., Taiwán, Corea, Japón, Europa…).
  · EVENTO: veto de exportación, arancel/veto de importación, disrupción
    (bloqueo, guerra, terremoto, huelga, apagón…) o impulso (subsidio, boom).
Con eso arma: quién recibe el golpe directo, quién podría GANAR cuota
(sustitutos fuera del país que actúa), y propaga por la cadena (clientes que
pierden suministro, proveedores que pierden demanda) con la fuerza de cada
vínculo. Cada impacto lleva su CAMINO ("SK Hynix → Nvidia: HBM para GPUs").

Todo es una ESTIMACIÓN estructural (rotulada así en la UI). La IA, si existe,
la recibe como base y la refina (core/sim_agents.py).
"""
import re
import unicodedata

# ── temas: producto/insumo → productores (ids del grafo) ────────────────────
THEMES = [
    {'key': 'hbm', 'rx': r'\bHBM\d?e?\b|memoria de alto ancho de banda|high.bandwidth memory',
     'es': 'memoria HBM (la memoria de las GPUs de IA)', 'en': 'HBM memory (the memory in AI GPUs)',
     'producers': ['SKHynix', 'Samsung', 'Micron', 'CXMT'],
     'watch_es': ['Precio y plazos de entrega de HBM', 'Guías de Nvidia y AMD sobre suministro de memoria',
                  'Licencias de exportación y respuestas de Corea/EE.UU.'],
     'watch_en': ['HBM pricing and lead times', 'Nvidia and AMD guidance on memory supply',
                  'Export licenses and responses from Korea/US']},
    {'key': 'dram', 'rx': r'\bDRAM\b|\bNAND\b|\bmemoria\b|\bmemory chips?\b',
     'es': 'chips de memoria', 'en': 'memory chips', 'producers': ['SKHynix', 'Samsung', 'Micron', 'CXMT'],
     'watch_es': ['Precios spot de DRAM/NAND', 'Inventarios de los fabricantes de PCs y servidores'],
     'watch_en': ['DRAM/NAND spot prices', 'PC and server makers inventories']},
    {'key': 'cowos', 'rx': r'CoWoS|empaquetado avanzado|advanced packaging',
     'es': 'empaquetado avanzado (CoWoS)', 'en': 'advanced packaging (CoWoS)', 'producers': ['TSMC', 'ASE', 'Amkor'],
     'watch_es': ['Capacidad CoWoS de TSMC', 'Envíos de GPUs de Nvidia'],
     'watch_en': ["TSMC's CoWoS capacity", 'Nvidia GPU shipments']},
    {'key': 'euv', 'rx': r'\bEUV\b|litograf|lithograph',
     'es': 'litografía (EUV)', 'en': 'lithography (EUV)', 'producers': ['ASML', 'Zeiss', 'Trumpf'],
     'watch_es': ['Cartera de pedidos de ASML', 'Planes de nuevas fábricas de chips'],
     'watch_en': ["ASML's order backlog", 'New fab plans']},
    {'key': 'gpu', 'rx': r'\bGPUs?\b|chips? de IA|AI chips?|aceleradores|accelerators',
     'es': 'chips de IA (GPUs)', 'en': 'AI chips (GPUs)', 'producers': ['Nvidia', 'AMD'],
     'watch_es': ['Pedidos de los hiperescaladores', 'Controles de exportación de chips'],
     'watch_en': ['Hyperscaler orders', 'Chip export controls']},
    {'key': 'foundry', 'rx': r'fundici[oó]n|foundry|fabricaci[oó]n de chips|chipmaking',
     'es': 'fabricación de chips', 'en': 'chip manufacturing', 'producers': ['TSMC', 'Samsung', 'Intel', 'SMIC'],
     'watch_es': ['Utilización de fábricas', 'Precios por oblea'], 'watch_en': ['Fab utilization', 'Wafer pricing']},
    {'key': 'rare_earths', 'rx': r'tierras raras|rare earths?|imanes|magnets',
     'es': 'tierras raras', 'en': 'rare earths',
     'producers': ['ChinaNorthernRareEarth', 'ChinaRareEarthGroup', 'MP_Materials', 'Lynas', 'IlukaResources'],
     'watch_es': ['Precio del neodimio', 'Cuotas de exportación chinas', 'Nuevas plantas fuera de China'],
     'watch_en': ['Neodymium price', 'Chinese export quotas', 'New plants outside China']},
    {'key': 'gallium', 'rx': r'galio|gallium|germanio|germanium',
     'es': 'galio y germanio', 'en': 'gallium and germanium', 'producers': ['TeckResources', 'Umicore'],
     'watch_es': ['Precio del galio', 'Licencias de exportación chinas'],
     'watch_en': ['Gallium price', 'Chinese export licenses']},
    {'key': 'lithium', 'rx': r'litio|lithium',
     'es': 'litio', 'en': 'lithium', 'producers': ['Albemarle', 'SQM', 'PiedmontLithium', 'SigmaLithium'],
     'watch_es': ['Precio del carbonato de litio'], 'watch_en': ['Lithium carbonate price']},
    {'key': 'copper', 'rx': r'\bcobre\b|copper',
     'es': 'cobre', 'en': 'copper', 'producers': ['FreeportMcMoRan', 'SouthernCopper', 'Antofagasta', 'BHP'],
     'watch_es': ['Precio del cobre en Londres (LME)'], 'watch_en': ['LME copper price']},
    {'key': 'uranium', 'rx': r'uranio|uranium|nuclear',
     'es': 'uranio / energía nuclear', 'en': 'uranium / nuclear power',
     'producers': ['Cameco', 'Kazatomprom', 'EnergyFuels'],
     'watch_es': ['Precio spot del uranio', 'Contratos nucleares de los centros de datos'],
     'watch_en': ['Uranium spot price', 'Data-center nuclear contracts']},
    {'key': 'power', 'rx': r'electricidad|energ[ií]a el[eé]ctrica|red el[eé]ctrica|power grid|apag[oó]n|blackout|\bpower\b',
     'es': 'electricidad para centros de datos', 'en': 'power for data centers',
     'producers': ['Vistra', 'Constellation', 'NextEraEnergy', 'GEVernova'],
     'watch_es': ['Precios de la electricidad', 'Conexiones a la red de nuevos centros de datos'],
     'watch_en': ['Power prices', 'Grid connections for new data centers']},
    {'key': 'gases', 'rx': r'\bhelio\b|helium|\bne[oó]n\b|gases? industriales|industrial gases?',
     'es': 'gases industriales (helio/neón)', 'en': 'industrial gases (helium/neon)', 'producers': ['Linde', 'AirLiquide'],
     'watch_es': ['Precio del helio y del neón'], 'watch_en': ['Helium and neon prices']},
    {'key': 'wafers', 'rx': r'polisilicio|polysilicon|\bobleas?\b|\bwafers?\b',
     'es': 'obleas de silicio', 'en': 'silicon wafers', 'producers': ['ShinEtsu', 'SUMCO', 'WackerChemie', 'Siltronic'],
     'watch_es': ['Precio de las obleas', 'Inventarios de las fundiciones'],
     'watch_en': ['Wafer prices', 'Foundry inventories']},
]

# ── actores (país que actúa) y normalización de países del catálogo ─────────
ACTORS = [
    ('china', r'\bChina\b|\bchin[oa]s?\b|Beijing|Pek[ií]n|\bPRC\b', 'China', 'China'),
    ('us', r'EE\.?\s?UU\.?|Estados Unidos|\bUSA?\b|Washington|\bUnited States\b|\bAmerica\b', 'EE.UU.', 'the US'),
    ('taiwan', r'Taiw[aá]n|estrecho de Taiw|Taiwan Strait', 'Taiwán', 'Taiwan'),
    ('korea', r'Corea|Korea', 'Corea del Sur', 'South Korea'),
    ('japan', r'Jap[oó]n|Japan', 'Japón', 'Japan'),
    ('netherlands', r'Pa[ií]ses Bajos|Holanda|Netherlands|Dutch', 'Países Bajos', 'the Netherlands'),
    ('europe', r'Europa|Uni[oó]n Europea|\bUE\b|\bEU\b|European Union', 'Europa', 'Europe'),
    ('russia', r'Rusia|Russia', 'Rusia', 'Russia'),
    ('india', r'\bIndia\b', 'India', 'India'),
]
_EUROPE = ('alemania', 'francia', 'europa', 'reino unido', 'reinounido', 'italia', 'suiza', 'dinamarca',
           'finlandia', 'lituania', 'poland', 'restoeuropa', 'germany', 'belgica', 'espana', 'suecia',
           'noruega', 'paises bajos', 'paisesbajos', 'netherlands')


def _plain(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode('ascii')
    return s.lower().strip()


def country_key(raw):
    c = _plain(raw)
    if not c:
        return None
    if c.startswith(('eeuu', 'estados unidos', 'usa', 'united states')):
        return 'us'
    if 'china' in c or 'hong kong' in c:
        return 'china'
    if 'taiwan' in c:
        return 'taiwan'
    if 'corea' in c or 'korea' in c:
        return 'korea'
    if 'japon' in c or 'japan' in c:
        return 'japan'
    if 'paises bajos' in c or 'paisesbajos' in c or 'netherlands' in c:
        return 'netherlands'
    if 'rusia' in c or 'russia' in c:
        return 'russia'
    if c.startswith('india'):
        return 'india'
    if any(c.startswith(e) for e in _EUROPE):
        return 'europe'
    return c


def _in_actor(node, actor):
    ck = country_key(node.get('country'))
    if actor == 'europe':
        return ck in ('europe', 'netherlands')
    return ck == actor


# ── tipo de evento ──────────────────────────────────────────────────────────
EVENTS = [
    ('export_ban', r'proh[ií]b\w*\s+(?:la\s+|las\s+|el\s+)?export|export(?:ation)?\s+ban|ban\w*\s+(?:the\s+)?export|'
                   r'restring\w*\s+(?:las\s+)?export|control\w*\s+(?:de\s+)?exportaci|export controls?|embargo|'
                   r'deja de (?:vender|exportar)|stops? (?:selling|exporting)'),
    ('import_ban', r'proh[ií]b\w*\s+(?:la\s+|las\s+)?import|import\s+ban|ban\w*\s+import|arancel|tariff|veto a'),
    ('boost', r'\bboom\b|aumenta la demanda|demand (?:surge|boom)|subsidi|aprueba|levanta|lifts?\b|acuerdo|\bdeal\b|'
              r'r[eé]cord|duplica|double'),
    ('disruption', r'bloque|invad|invasi[oó]n|guerra|\bwar\b|conflicto|terremoto|earthquake|incendio|\bfire\b|huelga|'
                   r'strike|apag[oó]n|blackout|cierr|shut|quiebra|bankrupt|escasez|shortage|sanci[oó]n|sanction|'
                   r'ataque|attack|hack|deja de producir|stops? producing|ca[ií]da|colapso|collapse'),
]

_STOP = set('''que qué pasa pasaría pasaria si con sin para por los las del una uno unos unas como cuando donde este
esta esto estos estas ese esa eso entre sobre todo toda todos todas más mas menos muy hay ser son era fue han
the and for with what would happen if from this that these those into over about more less very will can could
prohibe prohíbe exportar importar exports imports export import ban bans deja dejar escenario scenario empresas
companies mercado market precio precios china eeuu estados unidos taiwan taiwán corea japón japon europa'''.split())


def detect(scenario):
    """{'themes':[...], 'actor':key|None, 'actor_es','actor_en', 'event':str}"""
    t = scenario or ''
    themes = [th for th in THEMES if re.search(th['rx'], t, re.I)]
    # HBM ya implica memoria: no dupliques el tema genérico
    if any(th['key'] == 'hbm' for th in themes):
        themes = [th for th in themes if th['key'] != 'dram']
    found = sorted(((m.start(), k, es, en) for k, rx, es, en in ACTORS for m in [re.search(rx, t, re.I)] if m))
    actor = found[0][1:] if found else None
    target = found[1][1:] if len(found) > 1 else None      # "EE.UU. impone aranceles a chips de Taiwán"
    event = next((k for k, rx in EVENTS if re.search(rx, t, re.I)), 'disruption')
    return {'themes': themes, 'actor': actor[0] if actor else None,
            'actor_es': actor[1] if actor else None, 'actor_en': actor[2] if actor else None,
            'target': target[0] if target else None, 'target_es': target[1] if target else None,
            'target_en': target[2] if target else None, 'event': event}


def text_search(scenario, snap, limit=4):
    """Productores por búsqueda en las fichas del grafo cuando no hay tema conocido."""
    toks = [w for w in re.findall(r'[A-Za-zÁÉÍÓÚáéíóúñÑ0-9]{4,}', scenario or '') if _plain(w) not in _STOP]
    acr = re.findall(r'\b[A-Z]{3,6}\b', scenario or '')
    terms = list(dict.fromkeys(toks + acr))[:8]
    if not terms:
        return []
    scores = []
    for nid, n in snap['by_id'].items():
        sc = 0
        for term in terms:
            rx = re.compile(r'\b' + re.escape(term) + r'\b', re.I)
            if rx.search(n.get('label') or ''):
                sc += 5
            if rx.search((n.get('role') or '') + ' ' + (n.get('role_en') or '')):
                sc += 3
            if rx.search((n.get('supplies') or '') + ' ' + (n.get('supplies_en') or '')):
                sc += 2
        if sc >= 3:
            scores.append((sc, snap['deg'].get(nid, 0), nid))
    scores.sort(reverse=True)
    return [nid for _s, _d, nid in scores[:limit]]


def _w(l):
    w = l.get('w') or 1
    try:
        w = float(w)
    except (TypeError, ValueError):
        w = 1.0
    return max(0.1, min(1.0, w / 5.0 if w > 1 else w))


def _rel(l):
    return (l.get('rel') or l.get('type') or '').strip()[:90]


def analyze(scenario, snap, named_ids=(), lang='es'):
    """Análisis estructural. Devuelve dict con seeds, hit, benefit, impacts
    (severidad con signo, camino, canal), summary, watch, timeline y meta."""
    es = not str(lang).lower().startswith('en')
    det = detect(scenario)
    by_id = snap['by_id']
    producers = []
    for th in det['themes']:
        producers += [p for p in th['producers'] if p in by_id]
    producers += [i for i in named_ids if i in by_id]
    actor, event = det['actor'], det['event']
    target = det.get('target')

    def top_local(country, k=6):
        return sorted((i for i, n in by_id.items() if _in_actor(n, country) and n.get('mkt')),
                      key=lambda i: -snap['deg'].get(i, 0))[:k]
    if target and event == 'import_ban':
        # el país que SUFRE el arancel: sus productores (del tema) o sus empresas clave
        tp = [p for p in producers if _in_actor(by_id[p], target)]
        producers = tp or top_local(target)
    if not producers:
        producers = text_search(scenario, snap)
    if not producers and actor:
        producers = top_local(actor)          # "¿y si Taiwán es bloqueado?" → sus empresas clave
    producers = list(dict.fromkeys(producers))[:8]
    if not producers:
        return None
    hit, benefit = [], []
    note_es = note_en = ''
    if event in ('export_ban', 'import_ban') and actor:
        inside = [p for p in producers if _in_actor(by_id[p], actor)]
        outside = [p for p in producers if p not in inside]
        if event == 'export_ban':
            if inside:
                hit, benefit = inside, outside
                note_es = (f"Los productores de {det['actor_es']} pierden ventas al exterior; los de fuera pueden "
                           f"ganar cuota y los clientes que dependían de ellos sufren falta de suministro.")
                note_en = (f"Producers in {det['actor_en']} lose foreign sales; producers elsewhere can gain share "
                           f"and customers that depended on them face supply shortages.")
            else:
                hit, benefit = [], outside
                note_es = (f"En el grafo no hay productores relevantes dentro de {det['actor_es']}: el veto cambia "
                           f"poco la oferta mundial. El efecto principal sería político (represalias) y de "
                           f"sentimiento; los productores de fuera podrían incluso ganar poder de precio.")
                note_en = (f"The graph has no relevant producers inside {det['actor_en']}: the ban barely changes "
                           f"world supply. The main effect would be political (retaliation) and sentiment; "
                           f"producers elsewhere could even gain pricing power.")
        else:   # arancel / veto de importación: los de FUERA venden menos al país que actúa
            hit, benefit = outside, inside
            note_es = (f"Los productores de fuera de {det['actor_es']} venden menos o más caro en ese mercado; los "
                       f"locales ganan protección.")
            note_en = (f"Producers outside {det['actor_en']} sell less (or pricier) into that market; local ones "
                       f"gain protection.")
    elif event == 'boost':
        benefit = producers
        note_es = 'Impulso de demanda o apoyo: los productores y sus proveedores se benefician.'
        note_en = 'Demand boost or support: producers and their suppliers benefit.'
    else:   # disrupción: si hay país, sus empresas clave también reciben el golpe
        hit = list(producers)
        if actor and not det['themes']:
            local = sorted((i for i, n in by_id.items() if _in_actor(n, actor)),
                           key=lambda i: -snap['deg'].get(i, 0))[:6]
            hit = list(dict.fromkeys(hit + local))[:8]
        note_es = 'Disrupción de oferta: el golpe va de los afectados a sus clientes (falta de suministro) y a sus proveedores (menos pedidos).'
        note_en = 'Supply disruption: the hit flows from those affected to their customers (shortage) and suppliers (fewer orders).'

    base = {'export_ban': 1.0, 'disruption': 1.0, 'import_ban': 0.5, 'boost': 0.8}.get(event, 1.0)
    imp = {}   # id → {'sev', 'channel', 'path', 'via'}

    def put(nid, sev, channel, path):
        if nid not in by_id:
            return
        cur = imp.get(nid)
        if cur is None or abs(sev) > abs(cur['sev']):
            imp[nid] = {'sev': round(sev, 3), 'channel': channel, 'path': path}

    for h in hit:
        put(h, -base, 'direct', [h])
    for b in benefit:
        put(b, +0.55 * base if event != 'boost' else +base, 'substitute' if event != 'boost' else 'direct', [b])

    # propagación por la cadena (source PROVEE a target)
    sources = [(h, -base) for h in hit] + ([(b, +base) for b in benefit] if event == 'boost' else [])
    for root, sign in sources:
        # clientes (aguas abajo): 2 saltos
        frontier = [(root, abs(sign), [root])]
        for depth in (1, 2):
            nxt = []
            for nid, s, path in frontier:
                for l in sorted(snap['out'].get(nid, []), key=lambda x: -_w(x))[:12]:
                    t = l.get('target')
                    if not t or t in path or t in hit:
                        continue
                    sev = s * _w(l) * (0.7 if depth == 1 else 0.45)
                    if sev < 0.08:
                        continue
                    put(t, (1 if sign > 0 else -1) * sev, 'customer' if depth == 1 else 'second_order', path + [t])
                    nxt.append((t, sev, path + [t]))
            frontier = sorted(nxt, key=lambda x: -x[1])[:10]
        # proveedores (aguas arriba): pierden pedidos (o ganan, en un impulso)
        for l in sorted(snap['in'].get(root, []), key=lambda x: -_w(x))[:8]:
            sup = l.get('source')
            if not sup or sup in hit or sup in benefit:
                continue
            put(sup, sign * _w(l) * 0.3, 'supplier', [sup, root])

    def edge_rel(a, b):
        for l in snap['out'].get(a, []):
            if l.get('target') == b:
                return _rel(l)
        return ''

    def lbl(i):
        return (by_id.get(i) or {}).get('label') or i

    impacts = []
    for nid, v in imp.items():
        p = v['path']
        steps = []
        for a, b in zip(p, p[1:]):
            r = edge_rel(a, b)
            steps.append(f'{lbl(a)} → {lbl(b)}' + (f' ({r})' if r else ''))
        n = by_id[nid]
        impacts.append({'id': nid, 'label': lbl(nid), 'sev': v['sev'], 'channel': v['channel'],
                        'path': ' · '.join(steps), 'country': n.get('country'), 'sector': n.get('sector')})
    # orden: magnitud × relevancia (cotizada y conectada) — antes las startups
    # privadas diminutas copaban la lista
    def rank(x):
        n = by_id.get(x['id']) or {}
        rel = 0.45 + min(snap['deg'].get(x['id'], 0), 30) / 30 + (0.25 if n.get('mkt') else 0)
        return -abs(x['sev']) * rel
    impacts.sort(key=rank)
    impacts = impacts[:20]

    # resumen
    by_sec = {}
    for x in impacts:
        s = x['sector'] or '—'
        a = by_sec.setdefault(s, {'sector': s, 'n': 0, 'sum': 0.0})
        a['n'] += 1
        a['sum'] += x['sev']
    sectors = sorted(({'sector': k, 'n': v['n'], 'avg_sev': round(v['sum'] / v['n'], 3)} for k, v in by_sec.items()),
                     key=lambda x: x['avg_sev'])
    watch_es, watch_en = [], []
    for th in det['themes']:
        watch_es += th['watch_es']
        watch_en += th['watch_en']
    if actor:
        watch_es.append(f"Anuncios oficiales y posibles represalias de/contra {det['actor_es']}")
        watch_en.append(f"Official announcements and possible retaliation by/against {det['actor_en']}")
    big_customers = [x['label'] for x in impacts if x['channel'] == 'customer'][:3]
    if big_customers:
        watch_es.append('Qué dicen en sus próximos resultados: ' + ', '.join(big_customers))
        watch_en.append('What they say in their next earnings: ' + ', '.join(big_customers))

    theme_es = ', '.join(th['es'] for th in det['themes']) or None
    theme_en = ', '.join(th['en'] for th in det['themes']) or None
    hit_l, ben_l = [lbl(i) for i in hit], [lbl(i) for i in benefit]
    cust = [x['label'] for x in impacts if x['channel'] == 'customer' and x['sev'] < 0][:4]
    sup = [x['label'] for x in impacts if x['channel'] == 'supplier'][:3]
    t1_es = (f"Días 0-7: {', '.join(hit_l)} reciben el golpe directo." if hit_l else
             'Días 0-7: el anuncio mueve el sentimiento antes que la oferta.')
    t1_en = (f"Days 0-7: {', '.join(hit_l)} take the direct hit." if hit_l else
             'Days 0-7: the announcement moves sentiment before supply.')
    t2_es = ('Semanas 2-8: ' + ('; '.join(filter(None, [
        ('clientes con menos suministro: ' + ', '.join(cust)) if cust else '',
        ('ganan cuota: ' + ', '.join(ben_l)) if ben_l and event != 'boost' else '',
        ('se benefician: ' + ', '.join(ben_l)) if ben_l and event == 'boost' else '']))
        or 'el efecto se reparte por la cadena.'))
    t2_en = ('Weeks 2-8: ' + ('; '.join(filter(None, [
        ('customers with less supply: ' + ', '.join(cust)) if cust else '',
        ('gain share: ' + ', '.join(ben_l)) if ben_l and event != 'boost' else '',
        ('benefit: ' + ', '.join(ben_l)) if ben_l and event == 'boost' else '']))
        or 'the effect spreads through the chain.'))
    t3_es = ('Meses 2-6: ' + (f"sus proveedores ({', '.join(sup)}) ajustan pedidos; " if sup else '') +
             'los gobiernos responden (subsidios, controles o represalias) y el mercado reprecia el riesgo.')
    t3_en = ('Months 2-6: ' + (f"their suppliers ({', '.join(sup)}) adjust orders; " if sup else '') +
             'governments respond (subsidies, controls or retaliation) and the market reprices the risk.')
    return {
        'theme_es': theme_es, 'theme_en': theme_en, 'actor': actor, 'actor_es': det['actor_es'],
        'actor_en': det['actor_en'], 'event': event, 'producers': producers, 'hit': hit, 'benefit': benefit,
        'mechanism_es': note_es, 'mechanism_en': note_en, 'impacts': impacts,
        'summary': {'n_hit': sum(1 for x in impacts if x['sev'] < 0),
                    'n_benefit': sum(1 for x in impacts if x['sev'] > 0),
                    'sectors': sectors, 'countries': sorted({country_key(x['country']) or '—' for x in impacts})},
        'watch_es': list(dict.fromkeys(watch_es))[:6], 'watch_en': list(dict.fromkeys(watch_en))[:6],
        'timeline': [{'round': 1, 'events': [t1_es if es else t1_en]},
                     {'round': 2, 'events': [t2_es if es else t2_en]},
                     {'round': 3, 'events': [t3_es if es else t3_en]}],
    }
