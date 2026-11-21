"""ontology/news_facts.py — LA ONTOLOGÍA SE ACTUALIZA SOLA desde las noticias (2026-11-21, pedido de Fabrizio: «que el
agente de noticias vaya dotando de nuevos hechos y otro agente los incorpore, si no, ¿de qué sirve?»).

Dos agentes, una cadena:

  1. 📰 LECTOR DE HECHOS (`LectorHechos`, agente 'lector_hechos'): toma pocas empresas por vuelta (las más conectadas
     que no leyó en las últimas `HOURS_BETWEEN` horas), trae sus titulares REALES (Finnhub con resumen + GDELT, vía
     core/news_feed) y le pide al modelo PEQUEÑO que los convierta en HECHOS de un vocabulario cerrado:
        supplier / customer / partner / investor  → un VÍNCULO nuevo en el grafo
        ipo / deal / guidance / key_person / regulatory / disruption / litigation → una NOTA con su fuente
     Cada hecho debe citar el número de la noticia de donde sale. El modelo NO escribe URLs ni fechas: esas salen de
     la noticia citada.

  2. 🧹 CURADOR (`curate`): el filtro antes de que nada entre. Un hecho se DESCARTA si:
        · cita una noticia que no existe, o la contraparte / la cifra no aparecen en el texto de esa noticia
          (anti-invención, el mismo espíritu del guardián de cifras);
        · la contraparte no se resuelve a una empresa del grafo con el umbral de ESCRITURA (85: id, ticker, nombre
          exacto o alias) → queda como nota «posible relación con X» para una persona;
        · el vínculo ya existe vigente, o ya se propuso en los últimos 30 días (sin duplicados);
        · es de una persona clave (key_person) y la fuente no es prensa seria o primaria (sin chismes).
     La CONFIANZA se calcula (no la dice el modelo): base + confianza de la fuente (vocabulario source_kinds) +
     corroboración (cuántos medios distintos lo dicen). Con ≥ policy.auto_apply.auto_min_confidence (0,55) el ciclo
     automático la aplica sola (actor system:auto_apply, con su decisión en el libro); con menos, espera a una persona
     en 🩺 → Propuestas. Un vínculo entra como `proposed` (el cálculo lo pondera por su confianza) y una persona lo
     confirma con un clic: confirmar sin persona sería ampliar SAFE_AUTO, que es un cambio MAJOR con PIN.

Quién lo hace correr: el ciclo de agentes de siempre (ontology.agents.auto_cycle), que ahora también late desde el
SERVIDOR (ontology/curation_loop.py), no solo cuando alguien tiene la app abierta. Costo acotado: ≤ PER_CYCLE empresas
por vuelta y ≤ ONTOLOGY_NEWS_DAILY (60) al día, una llamada pequeña por empresa (feature 'ontology_news' en 💰).
ONTOLOGY_NEWS_FACTS=off lo apaga. Nunca toca dinero.
"""
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func as sqlfunc

from ontology.models import ObjectRecord, LinkRecord, ProposedAction

NAME = 'lector_hechos'
PER_CYCLE = 3
HOURS_BETWEEN = 20
NEWS_DAYS = 5
LINK_KINDS = {'supplier', 'customer', 'partner', 'investor'}
NOTE_KINDS = {'ipo', 'deal', 'guidance', 'key_person', 'regulatory', 'disruption', 'litigation'}
NOTE_ICON = {'ipo': '🔔 Salida a bolsa', 'deal': '🤝 Acuerdo', 'guidance': '📈 Previsión', 'key_person': '👤 Persona clave',
             'regulatory': '⚖️ Regulación', 'disruption': '⚠️ Interrupción', 'litigation': '⚖️ Litigio'}
# dirección ÚNICA del grafo: source PROVEE a target
LINK_REL = {'supplier': 'supply', 'customer': 'supply', 'partner': 'partner', 'investor': 'invest'}

_SEEN = {}                    # company_id → última lectura (epoch); se pierde al reiniciar (inofensivo)
_DAY = {'day': None, 'n': 0}
_LOCK = threading.Lock()

SYSTEM = (
    'Eres el LECTOR DE HECHOS de Khipus. Recibes titulares numerados [0], [1]… sobre UNA empresa. Extrae SOLO hechos '
    'concretos que el titular o su resumen digan EXPLÍCITAMENTE (nunca rumores tuyos, nunca deducciones). '
    'Tipos permitidos: supplier (la contraparte le PROVEE a la empresa), customer (la contraparte le COMPRA a la '
    'empresa), partner (alianza), investor (la contraparte invierte en la empresa), ipo, deal, guidance, key_person '
    '(salida, llegada, salud o escándalo de un directivo — solo si es un hecho publicado), regulatory, disruption, '
    'litigation. Devuelve JSON: {"facts":[{"kind":"…","news":<número>,"counterpart":"nombre tal como aparece o vacío",'
    '"amount":"cifra tal como aparece o vacío","text":"una frase corta en español con el hecho"}]}. '
    'Máximo 4 hechos. Si no hay hechos concretos devuelve {"facts":[]}. No inventes URLs ni fechas.')


def enabled():
    return (os.getenv('ONTOLOGY_NEWS_FACTS') or 'on').strip().lower() not in ('off', '0', 'false', 'no')


def daily_cap():
    try:
        return max(0, int(os.getenv('ONTOLOGY_NEWS_DAILY') or 60))
    except ValueError:
        return 60


def _has_ai():
    try:
        from core import config as c
        return bool(getattr(c, 'CLAUDE', '') or getattr(c, 'GEMINI_KEY', '') or getattr(c, 'NVIDIA_KEY', ''))
    except Exception:  # noqa: BLE001
        return False


def _take_budget(n=1):
    today = datetime.now(timezone.utc).date().isoformat()
    with _LOCK:
        if _DAY['day'] != today:
            _DAY['day'], _DAY['n'] = today, 0
        if _DAY['n'] + n > daily_cap():
            return False
        _DAY['n'] += n
        return True


def _norm(s):
    s = str(s or '').lower()
    s = re.sub(r'[^a-z0-9áéíóúñü%$.,]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def _strip_suffix(name):
    return re.sub(r'\b(inc|corp|corporation|co|ltd|limited|plc|ag|sa|se|nv|holdings?|group|llc)\b\.?', '', _norm(name)).strip()


def _mentions(text, name):
    """¿La contraparte aparece en el texto? (nombre normalizado, sin sufijo societario; ≥ 3 letras)."""
    t, n = _norm(text), _strip_suffix(name)
    return len(n) >= 3 and re.search(r'(^|\s)' + re.escape(n) + r'($|\s|\.|,)', t) is not None


def _digits(s):
    return re.sub(r'[^0-9]', '', str(s or ''))


def _amount_in(text, amount):
    d = _digits(amount)
    return not d or d in _digits(text) or d.lstrip('0') in _digits(text)


def _trust(url, outlet=''):
    try:
        from ontology.provenance import guess_kind, source_trust
        kind = guess_kind(url or '')
        if kind == 'aggregator' and outlet:          # Finnhub trae el medio por nombre (Reuters, CNBC…)
            o = _norm(outlet)
            if any(p in o for p in ('reuters', 'bloomberg', 'cnbc', 'financial times', 'wall street journal', 'wsj',
                                    'associated press', 'nikkei', 'barron')):
                kind = 'press'
        return kind, source_trust(kind)
    except Exception:  # noqa: BLE001
        return 'aggregator', 1


def confidence(kind, trust, n_outlets):
    """Confianza CALCULADA: base por tipo + fuente (0-3) + corroboración. Un agregador solo (trust 1) queda bajo el
    umbral de aplicación automática (0,55) → lo revisa una persona; prensa seria (trust 2) entra sola."""
    base = 0.35 if kind in LINK_KINDS else 0.40
    c = base + 0.10 * max(0, min(3, int(trust or 0))) + 0.10 * max(0, min(3, n_outlets - 1))
    return round(min(0.9, c), 2)


# ── 1. observar: qué empresas leer ───────────────────────────────────────────
def pick_companies(session, n=PER_CYCLE):
    rows = session.execute(
        select(LinkRecord.source_id, sqlfunc.count(LinkRecord.id))
        .where(LinkRecord.valid_to.is_(None)).group_by(LinkRecord.source_id)
        .order_by(sqlfunc.count(LinkRecord.id).desc()).limit(200)).all()
    ids = [r[0] for r in rows]
    now = time.time()
    fresh = [i for i in ids if now - _SEEN.get(i, 0) > HOURS_BETWEEN * 3600]
    if not fresh:
        return []
    objs = session.scalars(select(ObjectRecord).where(ObjectRecord.id.in_(fresh[:n * 4]))).all()
    by = {o.id: o for o in objs if not (o.properties or {}).get('retired')}
    return [by[i] for i in fresh if i in by][:n]


def fetch_news(company, days=NEWS_DAYS, getter=None):
    from core.news_feed import _company_news
    p = company.properties or {}
    sym = p.get('mkt') or p.get('ticker') or ''
    arts = _company_news(company.id, company.label, sym, days, getter=getter) or []
    out, seen = [], set()
    for a in arts:
        url, title = a.get('url') or '', (a.get('title') or '').strip()
        if not title or not re.match(r'^https?://', url):
            continue
        k = _norm(title)[:90]
        if k in seen:
            continue
        seen.add(k)
        pub = a.get('published_at')
        out.append({'title': title[:240], 'summary': (a.get('summary') or '')[:320], 'url': url[:500],
                    'outlet': (a.get('outlet') or '')[:60],
                    'date': pub.date().isoformat() if hasattr(pub, 'date') else ''})
        if len(out) >= 10:
            break
    return out


def extract(company, news, ai_json=None):
    """Titulares → hechos crudos (lo que dijo el modelo pequeño). Nunca lanza."""
    if not news:
        return []
    lines = '\n'.join(f'[{i}] {a["title"]}' + (f' — {a["summary"]}' if a['summary'] else '') for i, a in enumerate(news))
    prompt = f'EMPRESA: {company.label} (id {company.id})\nNOTICIAS:\n{lines}'
    try:
        if ai_json is None:
            from core import ai as _ai
            from core.ai_usage import ai_context
            from core.model_router import models
            with ai_context(feature='ontology_news', who=f'agent:{NAME}'):
                data, _m = _ai._ai_json(SYSTEM, prompt, max_tokens=700, tier='fast', model=models()['small'])
        else:
            data = ai_json(SYSTEM, prompt)
    except Exception:  # noqa: BLE001 — sin IA no hay hechos (nunca inventarlos)
        return []
    facts = (data or {}).get('facts') if isinstance(data, dict) else data
    return [f for f in (facts or []) if isinstance(f, dict)][:4]


# ── 2. curar: qué entra y con qué confianza ──────────────────────────────────
def _resolve(name):
    try:
        from core.entities import resolve, UMBRAL_ESCRITURA
        r = resolve(str(name)[:120], umbral=UMBRAL_ESCRITURA)
        return r['id'] if r else None
    except Exception:  # noqa: BLE001
        return None


def _link_exists(session, a, b, rel):
    q = select(LinkRecord.id).where(LinkRecord.source_id == a, LinkRecord.target_id == b,
                                    LinkRecord.rel_type == rel, LinkRecord.valid_to.is_(None)).limit(1)
    return session.execute(q).first() is not None


def _already_proposed(session, action_type, key, days=30):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = session.scalars(select(ProposedAction).where(
        ProposedAction.agent == NAME, ProposedAction.action_type == action_type,
        ProposedAction.created_at >= since)).all()
    for p in rows:
        pl = p.payload or {}
        k = (pl.get('from_id'), pl.get('to_id'), pl.get('tipo')) if action_type == 'ProponerVinculo' \
            else (pl.get('object_id'), _norm(pl.get('texto'))[:80])
        if k == key:
            return True
    return False


def curate(session, company, news, facts, resolver=None):
    """Hechos crudos → propuestas listas para run_agents (o nada). Devuelve (propuestas, descartes)."""
    resolver = resolver or _resolve
    props, dropped = [], []
    for f in facts:
        kind = str(f.get('kind') or '').strip().lower()
        try:
            idx = int(f.get('news'))
        except (TypeError, ValueError):
            idx = -1
        if kind not in LINK_KINDS | NOTE_KINDS or not (0 <= idx < len(news)):
            dropped.append((kind, 'tipo o noticia inválida'))
            continue
        art = news[idx]
        body = f'{art["title"]} {art["summary"]}'
        cp, amount = str(f.get('counterpart') or '').strip(), str(f.get('amount') or '').strip()
        text = re.sub(r'\s*\(⚠[^)]*\)', '', str(f.get('text') or '')).strip()[:300] or art['title'][:200]
        if amount and not _amount_in(body, amount):
            dropped.append((kind, 'cifra que no está en la noticia'))
            continue
        if cp and not _mentions(body, cp):
            dropped.append((kind, 'contraparte que no está en la noticia'))
            continue
        kind_src, trust = _trust(art['url'], art['outlet'])
        if kind == 'key_person' and trust < 2:
            dropped.append((kind, 'persona clave sin prensa seria'))
            continue
        # corroboración: cuántos medios distintos nombran a la contraparte (o repiten el titular)
        outlets = {a['outlet'] or a['url'].split('/')[2] for a in news
                   if (cp and _mentions(f'{a["title"]} {a["summary"]}', cp)) or a is art}
        conf = confidence(kind, trust, len(outlets))
        evidence = {'url': art['url'], 'title': art['title'][:200], 'outlet': art['outlet'], 'date': art['date'],
                    'source_kind': kind_src, 'outlets': len(outlets)}
        when = f'{art["date"]} · ' if art['date'] else ''
        cite = f'{when}{art["outlet"] or kind_src} — {art["url"]}'
        if kind in LINK_KINDS:
            other = resolver(cp) if cp else None
            if not other or other == company.id:
                note = f'[Noticia · posible relación] {text} (contraparte «{cp or "?"}» no está en el grafo) · {cite}'
                key = (company.id, _norm(note)[:80])
                if cp and not _already_proposed(session, 'AnotarObjeto', key):
                    props.append({'action_type': 'AnotarObjeto', 'object_id': company.id, 'confidence': min(conf, 0.5),
                                  'payload': {'object_id': company.id, 'texto': note[:2000]},
                                  'explanation': f'📰 {text} — falta {cp} en el grafo: revisar', 'evidence': evidence})
                else:
                    dropped.append((kind, 'contraparte sin resolver'))
                continue
            a, b = (other, company.id) if kind in ('supplier', 'investor') else (company.id, other)
            rel = LINK_REL[kind]
            if _link_exists(session, a, b, rel) or _already_proposed(session, 'ProponerVinculo', (a, b, rel)):
                dropped.append((kind, 'ya existe o ya se propuso'))
                continue
            props.append({'action_type': 'ProponerVinculo', 'object_id': company.id, 'confidence': conf,
                          'payload': {'from_id': a, 'to_id': b, 'tipo': rel, 'fuente': art['url'][:200],
                                      'metadata': {'confidence': conf, 'weight': 0.3, 'via': NAME,
                                                   'headline': art['title'][:200], 'evidence': [evidence]}},
                          'explanation': f'📰 {text} ({art["outlet"] or kind_src}, {art["date"] or "s/f"})',
                          'evidence': evidence})
        else:
            note = f'[Noticia · {NOTE_ICON[kind]}] {text} · {cite}'
            key = (company.id, _norm(note)[:80])
            if _already_proposed(session, 'AnotarObjeto', key):
                dropped.append((kind, 'ya anotado'))
                continue
            props.append({'action_type': 'AnotarObjeto', 'object_id': company.id, 'confidence': conf,
                          'payload': {'object_id': company.id, 'texto': note[:2000]},
                          'explanation': f'📰 {text}', 'evidence': evidence})
    return props, dropped


# ── el agente (interfaz observe/propose de ontology.agents.run_agents) ──────
class LectorHechos:
    name = NAME

    def __init__(self, fetch=None, ai_json=None, resolver=None):
        self._fetch, self._ai_json, self._resolver = fetch, ai_json, resolver
        self.last = {}

    def observe(self, session):
        """Una señal por HECHO ya curado (la IA corre aquí, acotada). Sin IA o apagado → nada."""
        injected = self._ai_json is not None
        if not enabled() or (not injected and not _has_ai()):
            return []
        signals, report = [], {'companies': [], 'facts': 0, 'dropped': []}
        for c in pick_companies(session):
            if not _take_budget():
                report['budget'] = 'daily_cap'
                break
            _SEEN[c.id] = time.time()
            try:
                news = (self._fetch or fetch_news)(c)
            except Exception:  # noqa: BLE001
                news = []
            facts = extract(c, news, ai_json=self._ai_json)
            props, dropped = curate(session, c, news, facts, resolver=self._resolver)
            report['companies'].append({'id': c.id, 'news': len(news), 'facts': len(facts), 'kept': len(props)})
            report['facts'] += len(facts)
            report['dropped'] += [f'{c.id}: {k} ({why})' for k, why in dropped][:6]
            signals += [{'proposal': p} for p in props]
        self.last = report
        return signals

    def propose(self, session, signal):
        p = dict(signal['proposal'])
        p.pop('evidence', None)
        return p
