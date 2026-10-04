"""research/ask_agent.py — PREGUNTARLE A UN ANALISTA dentro de la conversación.

Pedido de Fabrizio (2026-10-04): "perfeccionar la integración de los agentes
de inversión para poder preguntarles, sacar información de todos o invocarlos
dentro de una conversación: así como le preguntas algo a Khipu y llamas al
analista de datos".

Cómo funciona
· `parse_mention(texto)` reconoce "@fundamental …", "@noticias …", "@todos …",
  "pregúntale al analista técnico …", "@comité …" → (puesto, pregunta).
· `ask(session, puesto, pregunta, entidad, lang)` arma el paquete del puesto
  (SUS conclusiones activas sobre la empresa, con evidencia citada, igual que
  en la sala del comité — research/debate.seat_package) y le pide a la IA que
  responda EN PERSONA (3-7 frases, citando [C#]/[E#]), con el guardián de
  cifras de core/ai. Sin conclusiones → lo dice y ofrece investigar (acción
  run_research), nunca inventa.
· `ask_all(...)`: una ronda corta con cada puesto que tenga conclusiones
  (máx. 4, en paralelo) → respuesta de todos, uno por párrafo.
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
            lines.append(f"   evidencia E{i}.{j} ({e.get('type') or 'fuente'}{', ' + e['date'] if e.get('date') else ''}): "
                         f"<data>{(e.get('title') or '')[:120]} — {(e.get('excerpt') or '')[:360]}</data>")
    head = [f'EMPRESA: {label} ({symbol or "no cotiza"})', '', 'TUS CONCLUSIONES ACTIVAS Y SU EVIDENCIA:']
    return '\n'.join(head + lines), refs


ASK_SYSTEM = """Eres {name} ({role}) del comité de inversión de Khipus Finance AI. Un inversionista NO experto te hace
una pregunta en una conversación. Responde EN PERSONA, en {lang}, en 3 a 7 frases claras y concretas, como un
analista senior que explica a un cliente: qué sabes, por qué importa para el valor de la empresa, en qué plazo y
qué tan sólida es tu evidencia. Cita tus conclusiones y evidencia entre corchetes ([C1], [E1.2]).
REGLAS: usa SOLO las conclusiones y datos del mensaje; si la pregunta va más allá de lo que investigaste, dilo con
claridad ("no lo investigué") y di qué harías para averiguarlo. Nunca inventes cifras ni fechas. Sin relleno, sin
frases genéricas, sin "como IA". Termina, si aplica, con UNA cosa concreta que vigilarías."""

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


def ask(session, seat, question, entity, lang='es', ai=None):
    """Respuesta de UN puesto. → dict {ok, seat, emoji, name, entity, label, answer, refs, n_claims,
    needs_research, model}. ai: inyectable para tests (callable(system, prompt, max_tokens, tier))."""
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
    claims = _load_claims(session, eid, seat)
    if not claims:
        return {'ok': True, 'seat': seat, 'emoji': meta['emoji'], 'name': name, 'entity': eid, 'label': label,
                'answer': (f"I haven't researched {label} yet, so I have no conclusions to stand on. Want me to run the research now?"
                           if en else f'Todavía no investigué {label}, así que no tengo conclusiones propias. ¿Quieres que la investigue ahora?'),
                'refs': {}, 'n_claims': 0, 'needs_research': True}
    ev = _evidence(session, [c.id for c in claims[:MAX_CLAIMS]])
    pkg, refs = _package(label, symbol, claims, ev)
    role = ROLE.get(seat, (seat, seat))[1 if en else 0]
    system = ASK_SYSTEM.format(name=name, role=role, lang='English' if en else 'español')
    prompt = pkg + f'\n\nPREGUNTA DEL INVERSIONISTA: {question or ("¿Qué opinas de " + label + "?")}'
    call = ai
    if call is None:
        from core.ai import _ai_complete
        call = _ai_complete
    text, model = call(system, prompt, ASK_TOKENS, 'deep')
    text = (text or '').strip()
    used = {r: refs[r] for r in refs if f'[{r}]' in text}
    return {'ok': True, 'seat': seat, 'emoji': meta['emoji'], 'name': name, 'entity': eid, 'label': label,
            'answer': text, 'refs': used, 'n_claims': len(claims), 'needs_research': False, 'model': model}


def ask_all(session, question, entity, lang='es', ai=None, max_seats=MAX_SEATS_ALL):
    """Todos los puestos con conclusiones (máx. max_seats) responden en paralelo."""
    en = lang == 'en'
    try:
        eid, label, _sym = _resolve(entity)
    except Exception:  # noqa: BLE001
        return {'ok': False, 'answers': [], 'answer': (f"I couldn't find “{entity}”." if en else f'No encontré «{entity}».')}
    seats = seats_with_claims(session, eid)[:max_seats]
    if not seats:
        return {'ok': True, 'entity': eid, 'label': label, 'answers': [], 'needs_research': True,
                'answer': (f'Nobody has researched {label} yet. Want me to run the research?' if en
                           else f'Nadie ha investigado {label} todavía. ¿Quieres que la investigue?')}
    from core.ai_usage import bind
    with ThreadPoolExecutor(max_workers=min(3, len(seats))) as ex:
        futs = [ex.submit(bind(ask), session, s, question, eid, lang, ai) for s in seats]
        answers = []
        for f in futs:
            try:
                answers.append(f.result(timeout=90))
            except Exception as e:  # noqa: BLE001
                log.warning('ask_all: %s', type(e).__name__)
    parts = [f"**{a['emoji']} {a['name']}** — {a['answer']}" for a in answers if a.get('answer')]
    return {'ok': True, 'entity': eid, 'label': label, 'answers': answers, 'needs_research': False,
            'answer': '\n\n'.join(parts)}
