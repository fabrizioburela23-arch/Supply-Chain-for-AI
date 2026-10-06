"""research/ask_agent.py — PREGUNTARLE A UN ANALISTA dentro de la conversación.

Pedido de Fabrizio (2026-10-04): "perfeccionar la integración de los agentes
de inversión para poder preguntarles, sacar información de todos o invocarlos
dentro de una conversación: así como le preguntas algo a Khipu y llamas al
analista de datos".

Cómo funciona
· `parse_mention(texto)` reconoce "@fundamental …", "@noticias …", "@todos …",
  "pregúntale al analista técnico …", "@comité …" → (puesto, pregunta).
· `ask(session, puesto, pregunta, entidad, lang)` arma el paquete del puesto:
  SUS HABILIDADES en vivo (research/agent_skills: cada rol busca lo suyo — la
  Cadena el tensor de proveedores/países/riesgo, el Técnico los indicadores de
  precio, el Fundamental estados/ratios/pares…) + sus conclusiones previas si
  existen, y le pide a la IA que responda EN PERSONA desde su rol (citando
  [S#]/[E#]/[C#]), con el guardián de cifras de core/ai. Ya NO exige una
  investigación previa (2026-10-06); sin IA, devuelve sus datos tal cual.
· `ask_all(...)`: una ronda corta con hasta 4 puestos (primero los que tienen
  conclusiones) en paralelo → respuesta de todos, uno por párrafo.
Todo es LECTURA: nunca propone órdenes.
"""
import logging
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

log = logging.getLogger('khipu')

MAX_CLAIMS = 8
MAX_SEATS_ALL = 4
ALL_DEFAULT = ('fundamental', 'supply_chain', 'technical', 'news')   # @todos sin conclusiones previas
ASK_TOKENS = 700

# palabra (sin acentos, minúsculas) → puesto
SEAT_WORDS = {
    'fundamental': 'fundamental', 'fundamentales': 'fundamental', 'financiero': 'fundamental', 'financiera': 'fundamental',
    'balance': 'fundamental', 'contable': 'fundamental',
    'tecnico': 'technical', 'tecnica': 'technical', 'technical': 'technical', 'grafico': 'technical', 'chartista': 'technical',
    'noticias': 'news', 'news': 'news', 'prensa': 'news', 'periodista': 'news',
    'cadena': 'supply_chain', 'suministro': 'supply_chain', 'supply': 'supply_chain', 'supply_chain': 'supply_chain', 'proveedores': 'supply_chain',
    'geopolitico': 'geopolitical', 'geopolitica': 'geopolitical', 'geopolitical': 'geopolitical', 'geo': 'geopolitical',
    'macro': 'macro', 'macroeconomico': 'macro', 'economista': 'macro',
    'cripto': 'crypto', 'crypto': 'crypto',
    'todos': 'all', 'todas': 'all', 'all': 'all', 'comite': 'all', 'committee': 'all', 'analistas': 'all', 'everyone': 'all',
}
_MENTION_RX = re.compile(r'^\s*@\s*([a-záéíóúñ_]+(?:\s+(?:de|del)\s+[a-záéíóúñ_]+)?)\s*[:,]?\s*(.*)$', re.I | re.S)
_ASK_RX = re.compile(r'^\s*(?:pregunta(?:le)?|preguntale|pregúntale|consulta(?:le)?|ask)\s+(?:al?|a la|the|to the)?\s*'
                     r'(?:analista|agente|analyst|agent|puesto|seat)?\s*(?:de\s+|del\s+|of\s+)?([a-záéíóúñ_ ]{3,30}?)\s*[:,]\s*(.+)$',
                     re.I | re.S)
_ASK_RX2 = re.compile(r'^\s*(?:pregunta(?:le)?|preguntale|pregúntale|consulta(?:le)?|ask)\s+(?:al?|a la|the|to the)?\s*'
                      r'(?:analista|agente|analyst|agent)\s+(?:de\s+|del\s+|of\s+)?([a-záéíóúñ_]+)\s+(.+)$', re.I | re.S)


def _fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', str(s or '').lower()) if unicodedata.category(c) != 'Mn')


def seat_from_words(txt):
    for w in _fold(txt).replace('_', ' ').split():
        if w in SEAT_WORDS:
            return SEAT_WORDS[w]
    return None


def parse_mention(message):
    """→ (seat | 'all' | None, pregunta). seat None = no es una mención."""
    m = _MENTION_RX.match(message or '')
    if m:
        seat = seat_from_words(m.group(1))
        if seat:
            return seat, (m.group(2) or '').strip()
        return None, message
    for rx in (_ASK_RX, _ASK_RX2):
        m = rx.match(message or '')
        if m:
            seat = seat_from_words(m.group(1))
            if seat:
                return seat, (m.group(2) or '').strip()
    return None, message


def seat_meta(seat):
    from research.deliberation import seat_name
    e, es, en = seat_name(seat)
    return {'seat': seat, 'emoji': e, 'name_es': es, 'name_en': en}


# ── datos ───────────────────────────────────────────────────────────────────
def _load_claims(session, entity_id, seat):
    from research.models import ResearchClaim
    now = datetime.now(timezone.utc)
    q = (session.query(ResearchClaim)
         .filter(ResearchClaim.subject_entity_id == entity_id, ResearchClaim.status == 'active'))
    if seat and seat != 'all':
        q = q.filter(ResearchClaim.agent_type == seat)
    rows = q.order_by(ResearchClaim.created_at.desc()).limit(60).all()
    out = []
    for c in rows:
        vt = c.valid_to
        if vt is not None and vt.tzinfo is None:
            vt = vt.replace(tzinfo=timezone.utc)
        if vt is not None and vt < now:
            continue
        out.append(c)
    return out


def _evidence(session, claim_ids):
    from research.committee import _evidence_rows
    return _evidence_rows(session, claim_ids)


def seats_with_claims(session, entity_id):
    from research.deliberation import SEAT_ORDER
    seen = {}
    for c in _load_claims(session, entity_id, 'all'):
        seen[c.agent_type] = seen.get(c.agent_type, 0) + 1
    order = {a: i for i, a in enumerate(SEAT_ORDER)}
    return sorted(seen, key=lambda a: (order.get(a, 99), a))


def _package(label, symbol, claims, ev):
    lines, refs = [], {}
    for i, c in enumerate(claims[:MAX_CLAIMS], 1):
        ref = f'C{i}'
        refs[ref] = c.id
        lines.append(f"{ref} [{c.horizon} · postura {c.stance} · confianza {float(c.confidence or 0):.2f}] "
                     f"<data>{c.statement_es}</data>")
        if c.reasoning_summary:
            lines.append(f'   razonamiento: <data>{c.reasoning_summary[:400]}</data>')
        if c.falsifiers:
            lines.append(f"   me haría cambiar de idea: <data>{'; '.join(list(c.falsifiers)[:2])}</data>")
        for j, e in enumerate((ev.get(c.id) or [])[:2], 1):
            lines.append(f"   evidencia C{i}.{j} ({e.get('type') or 'fuente'}{', ' + e['date'] if e.get('date') else ''}): "
                         f"<data>{(e.get('title') or '')[:120]} — {(e.get('excerpt') or '')[:360]}</data>")
    head = ['TUS CONCLUSIONES PREVIAS (investigación profunda) Y SU EVIDENCIA:']
    return '\n'.join(head + lines), refs


ASK_SYSTEM = """Eres {name} ({role}) del comité de inversión de Khipus Finance AI. Un inversionista te habla A TI,
no a Khipu en general: responde EN PERSONA, en {lang}, desde TU especialidad y nada más.
TU ENFOQUE: {focus}
Escribe 4 a 8 frases claras y concretas, como un analista senior que explica a un cliente: qué muestran TUS datos,
por qué importa para el valor de la empresa y qué tan sólida es la evidencia. Cita los ids entre corchetes:
[S#] (datos en vivo de tu rol), [E#] (paquete de evidencia) y [C#] (tus conclusiones previas, si las hay).
REGLAS: usa SOLO los datos del mensaje; si algo no está, dilo ("no tengo ese dato") y di qué mirarías.
Nunca inventes cifras ni fechas. No hagas un análisis general de la empresa: quédate en tu rol.
Sin relleno, sin frases genéricas, sin "como IA". Termina con UNA cosa concreta que vigilarías."""

ROLE = {'fundamental': ('analista fundamental: estados financieros, márgenes, deuda, valuación', 'fundamental analyst'),
        'technical': ('analista técnico: precio, tendencia, niveles, momentum', 'technical analyst'),
        'news': ('analista de noticias: hechos recientes y su impacto', 'news analyst'),
        'supply_chain': ('analista de cadena de suministro: proveedores, clientes, cuellos de botella', 'supply-chain analyst'),
        'geopolitical': ('analista geopolítico: países, sanciones, conflictos', 'geopolitical analyst'),
        'macro': ('analista macro: tasas, ciclo, divisas', 'macro analyst'),
        'crypto': ('analista cripto', 'crypto analyst')}


def _resolve(entity):
    from research.committee import _resolve_entity
    eid, node = _resolve_entity(entity)
    return eid, (node or {}).get('label') or eid, (node or {}).get('mkt')


def _strip_data(line):
    return re.sub(r'</?data>', '', str(line or '')).strip()


def _fallback_text(seat, label, packet, claims, lang, local=False):
    """Sin IA (ocupada / sin saldo, o Jev eligió 'local'): lo que muestran SUS datos, sin redactar nada nuevo."""
    en = lang == 'en'
    rows = [_strip_data(l)[3:] if re.match(r'^S\d+ ', l) else '' for l in (packet.get('text') or '').split('\n')]
    rows = [r for r in rows if r][:4]
    if not rows and claims:
        rows = [c.statement_es for c in claims[:3]]
    if not rows:
        return None
    if local:
        head = (f'What my data on {label} shows:' if en else f'Esto muestran mis datos de {label}:')
    else:
        head = (f"I couldn't write the full answer right now (the AI is busy), but this is what my data on {label} shows:"
                if en else f'No pude redactar la respuesta completa ahora (la IA está ocupada), pero esto muestran mis datos de {label}:')
    return head + '\n' + '\n'.join('· ' + r for r in rows)


def ask(session, seat, question, entity, lang='es', ai=None, skills=True, _pre=None, mode='deep'):
    """Respuesta de UN puesto, CON SUS HABILIDADES (research/agent_skills): cada rol trae al instante SU
    paquete de datos en vivo (Cadena → tensor de la cadena, países, riesgo aguas arriba/abajo; Técnico →
    indicadores de precio; Fundamental → estados, ratios y pares; …) y, si existen, sus conclusiones previas.
    Ya no hace falta una investigación previa para responder.
    → dict {ok, seat, emoji, name, entity, label, answer, refs, n_claims, needs_research, model, skill}.
    ai: inyectable para tests (callable(system, prompt, max_tokens, tier)). session puede ser None (sin base).
    mode (lo elige Jev, core/decide.chat_plan): 'deep' (modelo profundo, el de siempre) · 'fast' (modelo rápido)
    · 'local' (SIN IA: sus datos tal cual; si no tiene datos propios, cae a 'fast')."""
    from research import agent_skills as sk
    meta = seat_meta(seat)
    en = lang == 'en'
    name = meta['name_en'] if en else meta['name_es']
    try:
        eid, label, symbol = _resolve(entity)
    except Exception:  # noqa: BLE001
        return {'ok': False, 'seat': seat, 'emoji': meta['emoji'], 'name': name, 'entity': None,
                'answer': (f"I couldn't find “{entity}” in the Khipus graph. Which company do you mean?" if en
                           else f'No encontré «{entity}» en el grafo de Khipus. ¿A qué empresa te refieres?'),
                'refs': {}, 'n_claims': 0, 'needs_research': False}
    claims, ev = (_pre or ([], None))
    if _pre is None:
        try:                # sin base (session None) no hay conclusiones previas: solo sus habilidades
            claims = _load_claims(session, eid, seat)
        except Exception as e:  # noqa: BLE001
            log.info('ask: claims %s', type(e).__name__)
    packet = {'text': '', 'facts': {}, 'sources': [], 'n_evidence': 0, 'ok': False, 'listed': bool(symbol)}
    if skills:
        try:
            packet = sk.skill_packet(seat, eid)
        except Exception as e:  # noqa: BLE001
            log.info('ask: skills %s', type(e).__name__)
    skill = {'facts': packet.get('facts') or {}, 'sources': packet.get('sources') or [],
             'n_evidence': packet.get('n_evidence') or 0,
             'actions': sk.role_actions(seat, eid, label, packet.get('listed', bool(symbol))),
             'note_es': sk.note_for(seat, label, packet.get('facts') or {}, 'es'),
             'note_en': sk.note_for(seat, label, packet.get('facts') or {}, 'en')}
    base = {'ok': True, 'seat': seat, 'emoji': meta['emoji'], 'name': name, 'entity': eid, 'label': label,
            'n_claims': len(claims), 'needs_research': not claims, 'skill': skill}
    if not claims and not packet.get('ok'):
        return dict(base, refs={}, answer=(
            f"I have no data of my own on {label} right now. Want me to run the research?" if en
            else f'Ahora mismo no tengo datos propios de {label}. ¿Quieres que la investigue?'))
    parts = [f'EMPRESA: {label} ({symbol or "no cotiza"})', '']
    if packet.get('text'):
        parts.append(packet['text'])
    refs = {}
    if claims:
        if ev is None:
            ev = _evidence(session, [c.id for c in claims[:MAX_CLAIMS]])
        pkg, refs = _package(label, symbol, claims, ev)
        parts += ['', pkg]
    role = ROLE.get(seat, (seat, seat))[1 if en else 0]
    focus = (sk.FOCUS.get(seat) or ('', ''))[1 if en else 0]
    system = ASK_SYSTEM.format(name=name, role=role, focus=focus, lang='English' if en else 'español')
    prompt = '\n'.join(parts) + f'\n\nPREGUNTA DEL INVERSIONISTA: {question or ("¿Qué opinas de " + label + "?")}'
    if mode == 'local':
        loc = _fallback_text(seat, label, packet, claims, lang, local=True)
        if loc:
            return dict(base, answer=loc, refs={}, model=None, mode='local')
        mode = 'fast'
    call = ai
    if call is None:
        from core.ai import _ai_complete
        call = _ai_complete
    text, model = '', None
    try:
        text, model = call(system, prompt, ASK_TOKENS, 'fast' if mode == 'fast' else 'deep')
    except Exception as e:  # noqa: BLE001
        log.info('ask: ai %s', type(e).__name__)
    text = (text or '').strip()
    if not text:
        text = _fallback_text(seat, label, packet, claims, lang)
        if not text:
            raise RuntimeError('ai_unavailable')
        model = None
    used = {r: refs[r] for r in refs if f'[{r}]' in text}
    return dict(base, answer=text, refs=used, model=model, mode=mode)


def ask_all(session, question, entity, lang='es', ai=None, max_seats=MAX_SEATS_ALL, mode='deep'):
    """Todos los puestos con conclusiones (máx. max_seats) responden en paralelo."""
    en = lang == 'en'
    try:
        eid, label, _sym = _resolve(entity)
    except Exception:  # noqa: BLE001
        return {'ok': False, 'answers': [], 'answer': (f"I couldn't find “{entity}”." if en else f'No encontré «{entity}».')}
    # con conclusiones primero; el resto lo cubren sus habilidades en vivo (ya no hace falta investigar antes)
    try:
        with_claims = seats_with_claims(session, eid)
    except Exception as e:  # noqa: BLE001 — sin base (session None): ninguno tiene conclusiones
        log.info('ask_all: %s', type(e).__name__)
        with_claims = []
    seats = (with_claims + [s for s in ALL_DEFAULT if s not in with_claims])[:max_seats]
    # la sesión de base NO es segura entre hilos: conclusiones y evidencia se leen aquí, antes del paralelo
    pre = {}
    for st in seats:
        try:
            cl = _load_claims(session, eid, st) if st in with_claims else []
            pre[st] = (cl, _evidence(session, [c.id for c in cl[:MAX_CLAIMS]]) if cl else {})
        except Exception as e:  # noqa: BLE001
            log.info('ask_all pre %s: %s', st, type(e).__name__)
            pre[st] = ([], {})
    from core.ai_usage import bind
    with ThreadPoolExecutor(max_workers=max(1, min(4, len(seats)))) as ex:
        futs = [ex.submit(bind(ask), None, s, question, eid, lang, ai, True, pre[s], mode) for s in seats]
        answers = []
        for f in futs:
            try:
                answers.append(f.result(timeout=90))
            except Exception as e:  # noqa: BLE001
                log.warning('ask_all: %s', type(e).__name__)
    # quien no tiene NADA propio (ni conclusiones ni datos de su rol) no ocupa un párrafo
    has = [a for a in answers if a.get('n_claims') or ((a.get('skill') or {}).get('n_evidence'))]
    answers = has or answers
    parts = [f"**{a['emoji']} {a['name']}** — {a['answer']}" for a in answers if a.get('answer')]
    return {'ok': bool(parts), 'entity': eid, 'label': label, 'answers': answers,
            'model': next((a.get('model') for a in answers if a.get('model')), None),
            'needs_research': not with_claims, 'answer': '\n\n'.join(parts)}
