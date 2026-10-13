"""Voz de Khipu — rutas /api/voice/* (G5-05, lote I4: salieron de server.py SIN cambiar comportamiento).

Aquí viven el prompt del agente de ElevenLabs (BIXBY_SYSTEM_PROMPT), el contrato de 17 herramientas
(_bixby_client_tools, RETIRED_VOICE_TOOLS, VOICE_*), la sincronización del agente, la sesión firmada y el audio del
recorrido. ElevenLabs se llama SOLO a través de core/voice_agent.py (único cliente REST; un test lo vigila).

La configuración (ELEVENLABS_KEY / ELEVENLABS_AGENT_ID) y `_diag_redact` siguen siendo del servidor y se leen EN CADA
LLAMADA por `_S` (server.py llama a bind() antes de registrar el blueprint): un cambio o un monkeypatch sobre `server`
se ve aquí igual que antes. server.py re-exporta los nombres que leen el 🩺 y las pruebas.
"""
import hashlib
import json
import logging
import os
import re
import threading
import time

import requests
from flask import Blueprint, Response, jsonify, request

from core.http import rate_limit
from core.pin import require_operator as _require_operator

log = logging.getLogger('khipu')
voice_bp = Blueprint('voice', __name__)
_S = None          # el módulo del servidor (bind)


def bind(host):
    """server.py se pasa a sí mismo: la config de ElevenLabs y _diag_redact se leen de ahí en cada llamada."""
    global _S
    _S = host


# ── Voz de Khipu: diagnóstico y ajuste FINO del agente ElevenLabs ────────────
# La lógica vive en core/voice_agent.py (contrato ElevenLabs oct-2026: herramientas
# como recursos con tool_ids, get-signed-url, modelos TTS vigentes, overrides).


@voice_bp.route('/api/voice/agent-diag')
@rate_limit(limit=10, window=300)  # pública: 4-6 llamadas a ElevenLabs por pedido → sin bucles que gasten la cuota
def voice_agent_diag():
    """Diagnóstico ACCIONABLE de la voz: clave, saldo/plan, agente, LLM, voz,
    modelo TTS, eventos, herramientas, prompt y overrides — con la lista de
    arreglos en español e inglés. Solo lectura. Conserva los campos planos de
    antes (voice_id, voice_name, tts_model, language, llm, first_message)."""
    from core import voice_agent as _va
    try:
        d = _va.diagnose(_S.ELEVENLABS_KEY, _S.ELEVENLABS_AGENT_ID, http=requests,
                         expected_tools=[t['name'] for t in _bixby_client_tools()],
                         retired_tools=RETIRED_VOICE_TOOLS, prompt=BIXBY_SYSTEM_PROMPT, full=True)
    except Exception as e:  # noqa: BLE001 — el diagnóstico jamás rompe
        return jsonify({'ok': False, 'error': _S._diag_redact(e)[:160]})
    # sin PIN: nada de datos de facturación (plan, caracteres usados/límite, renovación) — el 🩺 los ve por
    # /api/diagnostics; aquí quedan solo los chequeos accionables
    d.pop('subscription', None)
    ag = d.get('agent') or {}
    d.update({'name': ag.get('name'), 'voice_id': ag.get('voice_id'), 'voice_name': ag.get('voice_name'),
              'tts_model': ag.get('tts_model'), 'language': ag.get('language'), 'llm': ag.get('llm'),
              'first_message': ag.get('first_message')})
    if not (_S.ELEVENLABS_KEY and _S.ELEVENLABS_AGENT_ID):
        d['reason'] = 'ELEVENLABS_KEY/AGENT_ID no configurados'
    return jsonify(d)


# Rutas de administración de la voz: PIN de operador (core.pin.require_operator, mismo contador
# anti-adivinanza que el trading). Sin TRADE_PIN configurado se permiten (modo desarrollo) con aviso en el log.


@voice_bp.route('/api/voice/voices')
@rate_limit(limit=20, window=3600)
@_require_operator
def voice_voices():
    """Voces disponibles: las de la cuenta + las mejor valoradas EN ESPAÑOL de
    la biblioteca compartida de ElevenLabs (para arreglar la 'voz rara': el
    agente tenía una voz en inglés hablando español). Solo lectura, pero gasta
    la clave del servidor y lista la cuenta → PIN de operador + límite
    (limpieza 2026-10-11: antes era pública y sin límite)."""
    if not _S.ELEVENLABS_KEY:
        return jsonify({'error': 'ELEVENLABS_KEY no configurada', 'error_en': 'ELEVENLABS_KEY is not set'}), 400
    from core.voice_agent import list_voices
    return jsonify(list_voices(_S.ELEVENLABS_KEY, requests))


# Rutas que REESCRIBEN el agente de ElevenLabs (voz, modelo, idioma, prompt):
# además del candado ELEVENLABS_ALLOW_OVERRIDE exigen el PIN de operador
# (core.pin.require_operator, mismo contador anti-adivinanza que el trading).
# Sin TRADE_PIN configurado se permiten (modo desarrollo) con aviso en el log.

_SAFE_PATH_SEG = re.compile(r'^[A-Za-z0-9_\-]{1,80}$')


def _voice_override_off():
    return jsonify({'error': 'ELEVENLABS_ALLOW_OVERRIDE no está activo',
                    'error_en': 'ELEVENLABS_ALLOW_OVERRIDE is not enabled'}), 403


# ── Decisiones de la administración de la voz (G5-05, lote I4) ──────────────────────────────────────────────────
# adopt / agent-tune / sync-agent CAMBIAN el agente de ElevenLabs (voz, modelo, idioma, prompt, herramientas): cada
# uso deja UNA decisión policy.change (policy 'voice.agent') con QUÉ se pidió — ids públicos, modelo, idioma, huella
# del prompt, nombres de herramientas; NUNCA la clave — escrita ANTES de llamar a ElevenLabs (como order.submit antes
# de Alpaca). Si ElevenLabs FALLA, un decision_outcomes 'error' con su código (después de responder; sin 'error' = se
# aplicó). Con base configurada y libro caído no se toca ElevenLabs (503 ledger_unavailable). Sin DATABASE_URL todo
# sigue como antes.
def _ledger_503():
    return jsonify({'error': 'El libro de decisiones no está disponible: no se cambió nada',
                    'error_en': 'The decision ledger is unavailable: nothing was changed',
                    'code': 'ledger_unavailable'}), 503


def _voice_decision(action, after, before=None):
    """policy.change voice.agent ANTES de tocar ElevenLabs → (decision_id | None, respuesta_503 | None)."""
    try:
        from ontology.db import ontology_available
        if not ontology_available():
            return None, None
    except Exception:  # noqa: BLE001 — sin sqlalchemy: modo desarrollo
        return None, None
    try:
        from core import decision_sites
        from ontology.db import session_scope
        with session_scope() as s:
            subj = {'action': action, 'agent_id': _S.ELEVENLABS_AGENT_ID or None}
            did = decision_sites.policy_change(s, 'voice.agent', before, after, task='voice_admin', subject=subj)
            if did is None:
                # revisión lote I: «sin cambio» según la CACHÉ del agente (600 s) no es «sin escritura»: el PATCH a
                # ElevenLabs sale igual (y la caché pudo quedar vieja si alguien tocó el panel) → SIEMPRE una ficha
                did = decision_sites.policy_change(s, 'voice.agent', None, after, task='voice_admin',
                                                   subject=dict(subj, same_as_cache=True))
        return did, None
    except Exception as e:  # noqa: BLE001 — libro caído: falla cerrado
        log.warning('voz: %s sin decisión en el libro (%s) — no se toca ElevenLabs', action, type(e).__name__)
        return None, _ledger_503()


def _voice_outcome(did, res):
    """Si ElevenLabs falló: decision_outcomes 'error' (código, HTTP) DESPUÉS de responder; nunca rompe la ruta.
    (outcome_kind es un vocabulario cerrado con CHECK en la base: no se inventa uno nuevo.)"""
    res = res if isinstance(res, dict) else {}
    if not did or res.get('ok'):
        return
    keep = ('code', 'http', 'mode', 'status', 'tools_expected', 'tools_registered', 'tts_change', 'llm_fixed',
            'overrides_enabled', 'voice_id')
    result = {k: res[k] for k in keep if res.get(k) is not None}
    result['ok'] = bool(res.get('ok'))

    def _write():
        from datetime import datetime, timezone
        from core import decision_sites, decisions
        from ontology.db import session_scope
        with session_scope() as s:
            decisions.outcome(s, did, 'error', decision_sites.clean(dict(result, what='voice.agent')),
                              observed_at=datetime.now(timezone.utc), source='elevenlabs')
    try:
        from core import decision_sites
        decision_sites.after_response(_write, 'voice_error')
    except Exception as e:  # noqa: BLE001
        log.warning('voz: resultado no anotado (%s)', type(e).__name__)


def _agent_before(fields):
    """Valor ANTERIOR del agente SOLO si ya está en la caché de core/voice_agent (cero red, cero latencia)."""
    try:
        from core import voice_agent as _va
        cfg = _va.cached_agent(_S.ELEVENLABS_AGENT_ID)
        if not cfg:
            return None
        cur = _va.agent_summary(cfg)
        return {k: cur.get(k) for k in fields}
    except Exception:  # noqa: BLE001
        return None


@voice_bp.route('/api/voice/adopt', methods=['POST'])
@rate_limit(limit=10, window=3600)
@_require_operator
def voice_adopt():
    """Adopta una voz de la biblioteca compartida a la cuenta (paso previo a
    asignarla al agente). Mismo candado que agent-tune + PIN de operador. Body:
    {public_owner_id, voice_id, name}."""
    from core.voice_agent import override_env_on
    if not override_env_on():
        return _voice_override_off()
    if not _S.ELEVENLABS_KEY:
        return jsonify({'error': 'ELEVENLABS_KEY no configurada', 'error_en': 'ELEVENLABS_KEY is not set'}), 400
    b = request.get_json(silent=True)
    b = b if isinstance(b, dict) else {}
    po, vid, name = b.get('public_owner_id'), b.get('voice_id'), (b.get('name') or 'Khipu ES')
    if not po or not vid:
        return jsonify({'error': 'public_owner_id y voice_id requeridos',
                        'error_en': 'public_owner_id and voice_id are required'}), 400
    po, vid = str(po), str(vid)
    if not (_SAFE_PATH_SEG.match(po) and _SAFE_PATH_SEG.match(vid)):    # van en la URL de ElevenLabs
        return jsonify({'error': 'public_owner_id / voice_id inválidos',
                        'error_en': 'invalid public_owner_id / voice_id'}), 400
    did, bad = _voice_decision('adopt', {'public_owner_id': po, 'voice_id': vid, 'name': str(name)[:80]})
    if bad:
        return bad
    from core.voice_agent import adopt_shared_voice
    res = adopt_shared_voice(_S.ELEVENLABS_KEY, po, vid, name, requests)
    err0 = res.get('error') if isinstance(res.get('error'), dict) else {}
    _voice_outcome(did, dict(res, code=err0.get('code'), http=err0.get('http')))
    if not res.get('ok'):
        err = res.get('error') or {}
        return jsonify({'error': err.get('es') or err.get('message') or 'ElevenLabs falló',
                        'error_en': err.get('en') or err.get('message') or 'ElevenLabs failed',
                        'code': err.get('code'), 'http': err.get('http')}), 502
    return jsonify(res)


@voice_bp.route('/api/voice/agent-tune', methods=['POST'])
@rate_limit(limit=10, window=3600)
@_require_operator
def voice_agent_tune():
    """Ajuste FINO del agente (modelo TTS / idioma / voice_id). Requiere
    ELEVENLABS_ALLOW_OVERRIDE=1 (mismo candado que adopt) + PIN de operador.
    Solo toca los campos enviados; valida el modelo contra la lista VIGENTE de
    ElevenLabs (oct-2026: turbo_v2/_v2_5 deprecados; v3_conversational y v4)."""
    from core import voice_agent as _va
    if not _va.override_env_on():
        return _voice_override_off()
    if not (_S.ELEVENLABS_KEY and _S.ELEVENLABS_AGENT_ID):
        return jsonify({'error': 'ELEVENLABS_KEY/AGENT_ID no configurados',
                        'error_en': 'ELEVENLABS_KEY/AGENT_ID are not set'}), 400
    body = request.get_json(silent=True)
    body = body if isinstance(body, dict) else {}
    tts = {}
    if body.get('tts_model'):
        m = str(body['tts_model']).strip()[:60]
        if m not in _va.TTS_TUNABLE:
            return jsonify({'error': f'modelo de voz no válido para agentes: {m}',
                            'error_en': f'invalid TTS model for agents: {m}',
                            'valid': list(_va.TTS_TUNABLE)}), 400
        tts['model_id'] = m
    if body.get('voice_id'):
        vid = str(body['voice_id']).strip()[:60]
        if not _SAFE_PATH_SEG.match(vid):
            return jsonify({'error': 'voice_id inválido', 'error_en': 'invalid voice_id'}), 400
        tts['voice_id'] = vid
    agent = {}
    if body.get('language'):
        lang = str(body['language']).strip().lower()[:8]
        if not re.match(r'^[a-z]{2}(-[a-z]{2})?$', lang):
            return jsonify({'error': 'idioma inválido', 'error_en': 'invalid language'}), 400
        agent['language'] = lang
    if not tts and not agent:
        return jsonify({'error': 'nada que ajustar (tts_model / voice_id / language)',
                        'error_en': 'nothing to tune (tts_model / voice_id / language)'}), 400
    patch = {'conversation_config': {}}
    if tts:
        patch['conversation_config']['tts'] = tts
    if agent:
        patch['conversation_config']['agent'] = agent
    asked = {k: v for k, v in (('tts_model', tts.get('model_id')), ('voice_id', tts.get('voice_id')),
                               ('language', agent.get('language'))) if v}
    did, bad = _voice_decision('tune', asked, before=_agent_before(sorted(asked)))
    if bad:
        return bad
    try:
        r = requests.patch(f'{_va.EL_API}/v1/convai/agents/{_S.ELEVENLABS_AGENT_ID}',
                           headers={'xi-api-key': _S.ELEVENLABS_KEY,
                                    'Content-Type': 'application/json'},
                           json=patch, timeout=12)
        if not r.ok:
            e = _va.classify_error(r.status_code, r.text)
            e.update(_va.describe(e, 'agent'))
            _voice_outcome(did, {'ok': False, 'code': e.get('code'), 'http': r.status_code})
            return jsonify({'error': e['es'], 'error_en': e['en'], 'code': e['code'],
                            'fix_es': e.get('fix_es'), 'fix_en': e.get('fix_en'), 'body': r.text[:200]}), 502
        _va.forget_agent(_S.ELEVENLABS_AGENT_ID)
        _voice_outcome(did, {'ok': True})
        return jsonify({'ok': True, 'applied': patch})
    except Exception as e:  # noqa: BLE001
        _voice_outcome(did, {'ok': False, 'code': 'unreachable'})
        return jsonify({'error': 'No se pudo contactar con ElevenLabs', 'error_en': 'Could not reach ElevenLabs',
                        'detail': _S._diag_redact(e)[:160]}), 502


# Pantallas del menú "Herramientas / Tools" que la voz puede abrir (ids de BixbyCockpit.screens() en
# engine/cockpit.js, con el nombre VISIBLE — un test los compara). Las de una empresa (X-Ray, comparar,
# investigación, tesis, simular) van por open_company / compare_companies / quick_thesis / run_live_simulation.
VOICE_SCREENS = {
    'graph': ('Mapa de la cadena', 'Supply-chain map'),
    'market': ('Mercado', 'Market'),
    'terminal': ('Terminal', 'Terminal'),
    'geo': ('Geopolítica', 'Geopolitics'),
    'space': ('Espacio', 'Space'),
    'simulation': ('Simulación', 'Simulation'),
    'crypto': ('Cripto', 'Crypto'),
    'tkg': ('Grafo temporal', 'Temporal graph'),
    'portfolios': ('Carteras de práctica', 'Practice portfolios'),
    'broker': ('Mi cuenta (bróker)', 'My account (broker)'),
    'committee': ('Comité de inversión', 'Investment committee'),
    'risk': ('Riesgo de cartera', 'Portfolio risk'),
    'clients': ('Clientes', 'Clients'),
    'scalp': ('Scalping', 'Scalping'),
    'insights': ('Oportunidades', 'Opportunities'),
    'screener': ('Explosivas', 'Breakouts'),
    'canvas': ('Gráfico a pedido', 'Chart on demand'),
    'agents': ('Tus agentes', 'Your agents'),
    'brief': ('Brief de hoy', 'Today’s brief'),
    'guia': ('Guía', 'Guide'),
    'sistema': ('Sistema', 'System'),
    'mcp': ('Conectar IAs', 'Connect AIs'),
    'universe': ('Universo 3D', '3D universe'),
}
# qué hay en cada pantalla (para que la voz elija bien; el nombre visible sale de VOICE_SCREENS)
_VOICE_SCREEN_HINTS = {
    'graph': 'the supply-chain graph, 13 macro-sectors, ⏱ time slider and events layer',
    'market': 'live prices, positions and P&L',
    'terminal': 'multi-chart price terminal',
    'geo': 'World Monitor: live conflicts, disasters, sanctions and export controls on a globe, and who is exposed',
    'space': 'Space Monitor: launches and satellites',
    'simulation': 'war room: scenario presets and simulations',
    'crypto': 'live top-100 crypto + the curated "Expediente Khipus" of the top 50',
    'tkg': 'how the relations changed over time',
    'portfolios': 'SIMULATED practice portfolios and their assistant — never real orders',
    'broker': 'the broker account: practice (paper) or REAL money, positions and orders',
    'committee': 'Investment Committee: conviction, memo and the conclusions board',
    'risk': 'portfolio risk report (VaR) and option greeks',
    'clients': 'brokerage clients and the approval queue',
    'scalp': 'fast intraday trading view',
    'insights': 'what the hypergraph sees now: insights, risks and the relation matrices',
    'screener': 'breakout / momentum screener',
    'canvas': 'charts drawn on demand',
    'agents': 'the agent team (mascots), what each does and their preferences',
    'brief': 'the daily intelligence summary',
    'guia': 'help and how to use the app',
    'sistema': 'system health, AI spend and the activity log',
    'mcp': 'connect external AIs (Claude, ChatGPT…) to Khipus',
    'universe': '3D universe view of the network',
}

# ── Khipu voice — system prompt for ElevenLabs agent configuration ──────────
BIXBY_SYSTEM_PROMPT = """You are Khipu, the voice of Khipus Finance Intelligence — a Bloomberg + Palantir-style platform for the global semiconductor, AI, space, energy and nuclear supply chain: hundreds of curated companies and their typed relations (9 relation types) modeled as numeric matrices, plus macro layers. You are a full investment analyst who lives inside KHIPUS OS, the app's interface: you answer questions, open windows, run simulations and lead the agent team — all by silently calling your client tools.

## GOLDEN RULES OF SPEECH (CRITICAL — NEVER BREAK THESE)
- You act by CALLING YOUR CLIENT TOOLS. Tools are silent and instant.
- NEVER say, spell, read aloud or mention any command, token, tool name, bracket, code or internal id. The user must never hear anything technical — no "open_company", no "[XRAY:...]", no "puedes escribir TSMC XRAY", no "@cadena". Nothing of the sort, ever.
- NEVER tell the user to type a command, press a key or click a button to get something you can do yourself — just DO it with your tools and narrate the RESULT naturally. (Typing a PIN on screen and approving on screen are the only things the user does by hand.)
- Speak like a sharp human analyst: "Te abrí la radiografía de Nvidia al lado del chat — su mayor riesgo es la dependencia de TSMC…". Never like a machine.
- Company names: pass them to tools as plain names or tickers (e.g. "Nvidia", "NVDA", "TSMC") — the app resolves them, any casing works (it even fixes voice-transcription typos like "en vidia").
- If a tool returns {success:false} with an "error" text and/or "did_you_mean" suggestions, read that error text to the user AS-IS (it is already in the user's language, with no technical tokens) and offer the suggested companies naturally.

## TURN-TAKING / PATIENCE (IMPORTANT)
- When an action, analysis or lookup takes a few seconds, briefly say "dame un momento, lo estoy preparando" and then WAIT calmly for it.
- NEVER threaten to disconnect, and NEVER pressure the user about their silence. The user staying quiet while waiting for a result is completely normal — do NOT say things like "si no me respondes me desconecto". Just keep the conversation open patiently.
- If a tool result comes back with pending:true, the work is still running and will appear on screen: say so briefly ("sigue cargando, en unos segundos lo verás en pantalla") — never say it failed, and never call the same tool again right away.
- Keep spoken replies short and to the point.

## KHIPUS OS — WHAT THE USER SEES
- The conversation sits in the CENTER of the screen. What you ask the brain shows up there too: the user's spoken question, the agents working and the full answer with its sources. So SPEAK A SHORT SUMMARY — never read a long answer word by word; the details stay written in the chat.
- Every screen opens as a WINDOW beside the chat (on the sides on wide screens, on top on small screens and phones). Windows can be moved, minimized, closed and arranged.
- Top bar: the Khipus logo, the command palette (⌘K), the "Herramientas / Tools" menu where EVERY screen lives (groups Explorar, Invertir, Descubrir, Ayuda y sistema), the agent mascots, the money badge (the practice portfolios 🧪, or — once the trading PIN was typed — the broker account: 🧪 PAPER / 🔴 REAL money), the ES/EN switch and the light/dark switch.
- Call screens and windows by their VISIBLE names, in the user's language. The screens of the Herramientas menu:
{screens}
- Windows about one company: "<empresa> en una mirada", X-Ray, Cadena de suministro, Dossier, Comparar, the simulation windows (Caída simulada, Auge de demanda, Shock de precio, Sanción), Tesis rápida, Investigación con evidencia and Comité.
- Never take the user out of Khipus OS (there is an old classic view; do not send them there).

## THE AGENTS — the team the user sees as mascots
{agents}
- The user can INVOKE an agent by tapping its mascot or writing its name with @. You can do the same: ask_khipu_brain with that agent, and it answers from its own role. When you say who found something, use the mascot's name.
- The COMMITTEE (Comité) weighs every conclusion by its confidence and by each analyst's track record and computes a conviction from −100 to +100. It may PROPOSE buy / hold / sell, but it ALWAYS waits for human approval — never present a committee proposal as an executed order.

## THREE KINDS OF RESEARCH — never mix up their names
- "Investigación con evidencia": the analyst team writes conclusions with cited evidence, a horizon and a computed confidence (the "¿Por qué?" button shows the evidence). Open it with open_company and view research; starting a NEW study is the user's click on screen.
- "Tesis rápida": ONE AI answer about one company (quick_thesis) — fast, without cited evidence.
- "Búsqueda profunda": a free, complex question investigated in several steps, 30-90 seconds (deep_search).
All of it is information, not advice.

## YOUR TOOLS — when to call each (silently; results come back to you as data)
- ask_khipu_brain(question, agent?): THE DEFAULT for any question that needs facts or analysis, and for follow-ups. Add agent ONLY when the question is about ONE specific company AND the user names a mascot or the question clearly belongs to one: news about that company → radar · its suppliers, customers, dependencies → cadena · its price and momentum → tecnico · its fundamentals and valuation → analista · "what does the committee / the team think of it" → comite. ALWAYS write the company's name in the question (for "esta empresa" use the selected company's name). General questions — market news, world events, conflicts, sectors, no single company — go WITHOUT agent: Khipu's brain has the news and world tools.
- open_company(company_name, view): show ONE company. "Muéstrame X" → glance. Deep question about one company ("desármame X", "¿por qué X es riesgosa?", "¿qué pasa si cae?") → xray. Suppliers and customers → supply_chain. On the map → map. Price chart → chart. Financials and fundamentals → dossier. "¿Qué concluyeron los analistas?" → research. "¿Qué dice el comité de X?" → committee. Then narrate the 2-3 most interesting facts it returned.
- get_company_info(company_name): a quick fact without opening anything (price, market cap, employees, founded, valuation…).
- open_screen(screen): any screen of the Herramientas menu (market, geopolitics, space, crypto, practice portfolios, my account, committee, portfolio risk, opportunities, agents, guide, system…).
- compare_companies(company_a, company_b): "compara X con Y".
- run_live_simulation(company_name, kind, severity): "¿qué pasa si X cae / la sancionan / se dispara su demanda / sube su precio?" — kind collapse | demand | sanction | price.
- run_agent_simulation(scenario or preset, companies?): open-ended "¿qué pasaría si…?" questions where a debate adds value, or a war-room preset (Taiwan conflict, total chip ban to China, HBM shortage 2027, OpenAI IPO, Starshield).
- show_opportunities(): "¿dónde invierto?", "oportunidades", "¿qué ves en el grafo?", "¿qué está en riesgo?".
- create_visualization(query): any chart or table — never ask the user to describe the format, just render something smart.
- quick_thesis(company_name) and deep_search(question): see THREE KINDS OF RESEARCH.
- place_order, open_order_ticket, get_account_status: see MONEY below.
- get_space_summary(query?): satellites, constellations and launches — never say you do not know, this tool has the real numbers (or tells you they are unavailable).
- control_interface(action): new conversation, arrange / close / minimize windows, simple or pro explanations, light or dark theme, Spanish or English — only when the user asks for it.
- run_guided_demo(action): the one-minute tour — see THE ONE-MINUTE TOUR below.

You may receive [CONTEXT_UPDATE] {json} messages — silent snapshots of Khipus OS (language, open windows, focused window, selected company, invoked agent, simple/pro explanations, money mode, listen_only during a tour started from the button). Use them to be sharper ("esta empresa" = the selected company; money_mode: "paper" or "live" = the broker account ("Mi cuenta") is practice (paper) or REAL money; "practice" = only the simulated practice portfolios are known and the broker account's mode is NOT known; "none" = nothing known. Unless it is "paper" or "live", call get_account_status before telling the user whether their account is practice or real). Never read them aloud or acknowledge them.

## THE ONE-MINUTE TOUR (run_guided_demo)
- Start it ONLY when the user explicitly asks for a demo, a tour or to be shown the app — never on your own, never at the start of a session, never on a greeting.
- YOU narrate it with your voice, and THE APP keeps the pace: run_guided_demo with action start shows the first step and returns a "say" line — say EXACTLY that line, with nothing added before or after. Then the app moves the screen and sends you each next line as a message that starts with [TOUR n/N] (for example "[TOUR 2/9] Este es el mapa…"): say EXACTLY the text after the tag, nothing before or after, and do NOT call any tool for it. Never read the tag aloud. After the last line, stay quiet and wait for the user.
- If the user interrupts during the tour, answer briefly and ask whether to continue (yes → run_guided_demo with action next, no → action stop). If a result says stopped:true or done:true, the tour is over: do not continue it.
- When the user pressed the tour button on screen, the app opens your voice ONLY TO LISTEN: a [CONTEXT_UPDATE] says listen_only:true (no microphone). Then just narrate the tour — do not ask questions, do not greet again, and after done:true say nothing more. If listen_only becomes false, the user turned the microphone on: you can talk normally.

## MONEY — ALWAYS TELL THE TRUTH (RULES YOU MUST NEVER BREAK)
- Two different things — never confuse them: "Carteras de práctica" are SIMULATED portfolios to try ideas (they never send orders); "Mi cuenta (bróker)" is the user's broker account, which can be a PRACTICE (paper) account OR REAL MONEY depending on how it is set up. Every order summary and the "Mi cuenta" window show which one (🧪 / 🔴); if you do not know it, call get_account_status — never guess "practice".
- place_order and get_account_status return "mode": paper = say it is a simulated operation with practice money; live = say clearly, before anything else, that it is REAL MONEY. Never call an order simulated unless the result says paper.
- NEVER execute an order without explicit verbal confirmation. ALWAYS two steps: (1) place_order with confirmed=false returns a summary WITHOUT executing — read it (symbol, buy or sell, amount in dollars, practice or REAL money) and ask if they confirm. (2) ONLY after an explicit yes ("sí", "confirmo", "dale", "yes"), call place_order again with the SAME parameters and confirmed=true. Silence, hesitation or an ambiguous answer is NOT a yes — ask again or drop it. With REAL money, repeat the amount and the words "dinero real" in your question.
- If a PIN is needed, the user types it on screen — never ask them to say it aloud and never repeat it.
- open_order_ticket only opens the order ticket so the user decides on screen; nothing is sent.
- Around a trade you execute exactly what the user asked and report the result — you never push them to trade. If they ask what to buy you may give a CAUTIOUS stance (see below), never a blunt "buy/sell".
- If a tool returns an error message, read it to the user AS-IS (it is already user-friendly, in their language) and do NOT retry on your own.
- Amounts are in US dollars (notional): minimum $1, maximum $100,000 per order.

## DOMAIN KNOWLEDGE — DEEP EXPERTISE

NRS (Network Risk Score): 0-100, HIGHER = RISKIER. Sum of: country geo-risk (0-30), supply-chain centrality (0-25, from how many supply relations it has), margin-based market risk (0-20), fundamentals (0-15: pre-IPO, weak growth), country concentration (0-10). >70=HIGH (red), 40-70=MEDIUM (yellow), <40=LOW (green). For a company's actual NRS use the app's tools — never quote an NRS from memory.

Critical chokepoints (structural roles; for scores, prices or market caps use the app's live data, never memory):
- TSMC: leading advanced foundry; Apple/NVIDIA/AMD/Qualcomm depend on it.
- ASML: EUV lithography monopoly; no leading-edge nodes without them.
- NVIDIA: dominant AI training GPU supplier.
- SK Hynix: leading HBM supplier for AI accelerators.
- Arm: CPU ISA licensed across mobile and many data-center chips.
- Synopsys/Cadence: EDA duopoly; needed to design modern chips.

Supply chains (know the full stack):
- AI data center: NVIDIA GPU → TSMC fab → ASML litho → SK Hynix HBM → Broadcom switch
- Smartphone: Apple/Qualcomm SoC → TSMC fab → ARM ISA → Sony camera → Samsung display
- Space: SpaceX Falcon/Starship → Rocket Lab Electron → Maxar/Planet satellites → Iridium comms
- Automotive AI: NXP/Renesas SoC → STMicro power → Mobileye vision → LiDAR (Luminar)
- Quantum: IBM/IonQ/Rigetti systems → Oxford Instruments cryo → Keysight control

Geopolitical risks (qualitative; quote numbers only from live data or sourced context):
- Taiwan Strait: most leading-edge fab capacity (TSMC, UMC, ASE) is concentrated there. Conflict → global chip shortage
- US-China: export controls on advanced AI GPUs to China; Huawei building an alternative stack (Ascend)
- Rare earths: China dominates supply and processing; MP Materials/Lynas are US/AU alternatives
- Korea: Samsung + SK Hynix concentrate most DRAM/HBM supply

War-room presets (5; HYPOTHETICAL — outcomes come from running the simulation, never from memory):
1. Taiwan Strait conflict — TSMC blockade and its cascade
2. Total US chip export ban to China
3. HBM memory shortage 2027
4. OpenAI IPO and the AI ecosystem
5. SpaceX Starshield defense program

## ANALYST BEHAVIOR RULES
- For ANY question that needs facts or analysis, call ask_khipu_brain FIRST and answer from what it returns (it has live data and sources); only answer from your own knowledge for pure definitions or small talk.
- Never quote a price, market cap, NRS or valuation from memory — use the tools. When a figure comes with a date or a source and it matters, say it ("al cierre de ayer", "según el catálogo").
- You are a financial analyst first, voice assistant second. Give real insight, not just navigation.
- ACT FIRST, TALK SECOND: on almost every request, call the right tool immediately, then narrate what appeared on screen with 1-3 sentences of real insight. Never ask permission to open a window or look something up (orders are the exception: they always need the confirmation above).
- "What if…" questions → run_live_simulation, then narrate: how many companies are affected and the 2-3 biggest victims, USING THE % THE SIMULATION RETURNED — always say they are simulated estimates of a hypothetical scenario, never real prices. If it returns barely_hit_rivals, you may say those rivals are barely hit (hit_pct is the DAMAGE they take, not a gain): NEVER state a gain % or say anyone "wins X %".
- Multi-agent and war-room narration: describe the cascade ("TSMC absorbe el primer golpe, luego caen los fabless…"), the consensus and where the agents disagreed.
- Confirm actions naturally and briefly: "Te la abrí al lado del chat…", "Mira el mapa — se tiñe en rojo…".
- Be concise (2-3 sentences of analysis) — no over-explanation.
- Match the user's language exactly (Spanish/English/mixed — follow their lead). Default to Spanish.
- When asked investment questions, give a CAUTIOUS take WITH A STANCE — you may lean ("me inclinaría por… / sería cauto con TSMC porque…"), name the 2-3 key factors and a confidence level (alta/media/baja), but NEVER a blunt "compra/vende". ALWAYS close with a short reminder that this is analysis, not formal financial advice, and the decision is theirs. This soft-stance rule applies to stocks AND crypto.
- You are a Bloomberg Terminal AI co-pilot for serious investors, not a general chatbot"""
# Los agentes del prompt salen del registro ÚNICO (engine/agents_registry.js, limpieza 2026-10-11):
# si cambia una mascota, la voz la conoce sin tocar este texto.
from core.agents_registry import AGENTS as _REG_AGENTS, AGENT_NAMES as _REG_SEATS  # noqa: E402
BIXBY_SYSTEM_PROMPT = BIXBY_SYSTEM_PROMPT.replace('{agents}', '\n'.join(
    f"- {a['es']} / {a['en']} (agent: {a['id']}) — {a['role_en']}" + (
        ' (analysts: ' + ', '.join(_REG_SEATS[x][2] for x in a['seats'] if x in _REG_SEATS) + ')'
        if any(x in _REG_SEATS for x in a['seats']) else '')
    for a in _REG_AGENTS if a['id'] != 'khipu')).replace('{screens}', '\n'.join(
    f'- "{es}" / "{en}" — {_VOICE_SCREEN_HINTS[k]}' for k, (es, en) in VOICE_SCREENS.items()))


# ── Khipu — client tools registradas en el agente de ElevenLabs vía API ──────
# Cada entrada espeja un `case` de _handleToolCall en engine/voice.js.
# El agente las llama en silencio (el usuario nunca oye nombres de herramientas).
# Desde 2025-26 ElevenLabs las guarda como RECURSOS (/v1/convai/tools) y el agente
# las referencia con tool_ids — core/voice_agent.ensure_tools las crea/actualiza.
# response_timeout_secs (1-120): cuánto espera el agente la respuesta del navegador.
# Las lentas (cerebro, sim por agentes, investigación) necesitan más que el default;
# engine/voice.js responde SIEMPRE antes de ese tope (TOOL_TIMEOUT_S de allá).
# Contrato v2 (2026-10-11, voz para Khipus OS): 17 herramientas en vez de 31. Las respuestas van al chat
# CENTRAL y cada pantalla se abre como VENTANA; las viejas (pestañas, X-Ray suelto, "papel" fijo…) se
# retiraron y la sincronización las SUELTA del agente (RETIRED_VOICE_TOOLS). voice.js conserva alias para
# esos nombres mientras un agente viejo siga conectado durante un despliegue.
_VOICE_TOOL_TIMEOUTS = {'ask_khipu_brain': 60, 'open_company': 15, 'get_company_info': 15,
                        'run_agent_simulation': 90, 'quick_thesis': 90, 'show_opportunities': 15,
                        'place_order': 45, 'get_account_status': 45, 'get_space_summary': 20,
                        'run_guided_demo': 30}

RETIRED_VOICE_TOOLS = (
    'open_cockpit', 'switch_tab', 'show_chart', 'open_terminal', 'navigate_to_company', 'open_xray',
    'open_second_brain', 'open_dossier', 'get_risk_score', 'get_supply_chain_links', 'get_news',
    'get_market_summary', 'get_portfolio_risk', 'list_companies', 'get_opportunities', 'show_insights',
    'run_stress_test', 'run_simulation', 'deep_research', 'deep_analysis', 'place_paper_trade', 'place_trade',
    'get_portfolio_status', 'get_nrs_top10', 'show_matrices',
)

VOICE_SCREEN_ALIASES = {'map': 'graph', 'analysis': 'insights'}
VOICE_SIM_PRESETS = ('taiwan_conflict', 'china_chip_ban_total', 'hbm_shortage_2027', 'openai_ipo_impact',
                     'starshield_reveal')
VOICE_COMPANY_VIEWS = ('glance', 'xray', 'supply_chain', 'map', 'chart', 'dossier', 'research', 'committee')
VOICE_TOUR_ACTIONS = ('start', 'next', 'stop')
VOICE_UI_ACTIONS = ('new_conversation', 'arrange_windows', 'close_all_windows', 'minimize_all_windows', 'simple_mode',
                    'pro_mode', 'light_theme', 'dark_theme', 'spanish', 'english')


def _bixby_client_tools():
    def T(name, desc, props=None, required=None):
        return {
            'type': 'client', 'name': name, 'description': desc,
            'expects_response': True,
            'response_timeout_secs': _VOICE_TOOL_TIMEOUTS.get(name, 10),
            'parameters': {'type': 'object',
                           'properties': props or {},
                           'required': required or []},
        }
    S = lambda d: {'type': 'string', 'description': d}  # noqa: E731
    N = lambda d: {'type': 'number', 'description': d}  # noqa: E731
    E = lambda vals, d: {'type': 'string', 'enum': list(vals), 'description': d}  # noqa: E731
    company = {'company_name': S('Company name or ticker, any casing (e.g. "Nvidia", "NVDA", "tsmc")')}
    team = [a for a in _REG_AGENTS if a['id'] != 'khipu']
    agent_doc = '; '.join(f"{a['id']} = {a['es']} ({a['role_en']})" for a in team)
    screens_doc = '; '.join(f'{k} = "{es}" ({_VOICE_SCREEN_HINTS[k]})' for k, (es, _en) in VOICE_SCREENS.items())
    return [
        T('ask_khipu_brain', 'THE DEFAULT TOOL FOR ANY QUESTION. Sends the question to the Khipus analyst brain — the '
          'SAME brain as the center chat of Khipus OS: the user sees the question and the sourced answer appear in the '
          'chat while you speak, and the brain may open the relevant window by itself. It LOOKS UP real data (company '
          'profiles, supply chain, live prices and news, research conclusions with evidence, portfolio risk, '
          'geopolitical and space events, committee memos, track record). Use it for every analysis/knowledge question '
          'and for follow-ups. Optional agent: route the question to ONE mascot of the team when the user names it '
          '("pregúntale a Cadena…") or the question is clearly theirs; comite = the whole team. Read the returned '
          'answer aloud briefly (summarize long lists), never contradict its figures with your memory, and when '
          '"agents" is not empty say which mascots worked on it. Read-only: it never places orders.',
          {'question': S('The user question, in their own words, with enough context for follow-ups '
                         '(e.g. "and who depends on TSMC?").'),
           'agent': E([a['id'] for a in team], 'Optional mascot to ask: ' + agent_doc + '. Leave empty for Khipu.')},
          ['question']),
        T('open_company', 'Open ONE company in a window of Khipus OS and get its key facts to narrate. view: glance = '
          '"<company> en una mirada" summary (default) · xray = X-Ray (NRS term by term, dependency threads and the '
          'impact wave: who suffers and who WINS if it falls) · supply_chain = its suppliers and customers · map = the '
          'supply-chain map centered on it · chart = price chart in the Terminal (listed companies only) · dossier = '
          'the financial Dossier (statements; for private companies: owner, valuation, news) · research = '
          '"Investigación con evidencia" (the analyst team\'s conclusions with cited evidence — it shows what exists; '
          'starting a new study is the user\'s click) · committee = the Investment Committee on that company. Returns '
          'NRS with its terms, top suppliers/customers and, when available, the price with its source and time.',
          dict(company, view=E(VOICE_COMPANY_VIEWS, 'Which view to open (default glance).')), ['company_name']),
        T('get_company_info', 'Instant facts about ONE company WITHOUT opening anything: live price and market cap '
          'with source and time (listed companies), NRS risk with its terms, sector, country, role, moat, growth, '
          'margin, employees / founded / revenue when known (catalog_* fields are undated: say "según el catálogo"), '
          'number of suppliers and customers, listing status and, for private companies, the last VERIFIED valuation '
          'with its date. ALWAYS call this before saying you do not know a fact about a company.',
          company, ['company_name']),
        T('open_screen', 'Open a screen of the "Herramientas / Tools" menu as a window of Khipus OS, beside the chat. '
          'Screens: ' + screens_doc + '. Returns the visible title that opened.',
          {'screen': E(list(VOICE_SCREENS), 'The screen to open.')}, ['screen']),
        T('compare_companies', 'Compare two companies side by side in a window: the NRS risk of each and which one '
          'carries lower risk.', {'company_a': S('First company name/ticker'), 'company_b': S('Second company name/ticker')},
          ['company_a', 'company_b']),
        T('run_live_simulation', 'HYPOTHETICAL what-if on the live supply-chain matrices: what happens to the network '
          'if one company collapses, booms, suffers a price shock or is sanctioned. Opens the simulation window and '
          'returns how many companies are affected, the most impacted (with %) and, for falls, the rivals that are '
          'barely hit (barely_hit_rivals.hit_pct = the damage they take, NOT a gain; never state a gain %). Always '
          'present the % as simulated estimates of a hypothetical scenario, never as real prices.',
          dict(company, kind=E(('collapse', 'demand', 'price', 'sanction'),
                               'collapse = the company falls · demand = demand boom · price = price shock · '
                               'sanction = sanctions (default collapse)'),
               severity=N('How strong the shock is, 1-100 (default 100 = total)')), ['company_name']),
        T('run_agent_simulation', 'MULTI-AGENT simulation: several analyst agents debate an open-ended scenario and '
          'project impacts on the supply chain (up to a minute; it appears on screen). Use for "¿qué pasaría si…?" '
          'questions where a debate adds value, or for one of the war-room presets. Give scenario OR preset. Narrate '
          'the consensus, the biggest impacts and where the agents disagreed — always hypothetical.',
          {'scenario': S('The scenario in natural language, e.g. "China prohíbe exportar HBM"'),
           'companies': S('Optional companies/tickers to center it on, comma-separated (e.g. "Nvidia, TSMC")'),
           'preset': E(VOICE_SIM_PRESETS, 'Optional war-room preset: taiwan_conflict = Taiwan Strait conflict · '
                       'china_chip_ban_total = total US chip export ban to China · hbm_shortage_2027 = HBM memory '
                       'shortage · openai_ipo_impact = OpenAI IPO · starshield_reveal = SpaceX Starshield')}),
        T('show_opportunities', 'Open the "Oportunidades" window and get what the system sees NOW: live insights of the '
          'hypergraph (active systemic factors + supply-chain cascade) and the most resilient companies (low NRS + '
          'growth + margin). Use for "¿dónde invierto?", "oportunidades", "¿qué ves en el grafo?", "¿qué está en '
          'riesgo?". Narrate 2-3 insights naming companies; it is analysis, not advice.'),
        T('create_visualization', 'Draw a chart or table on demand in a "Gráfico" window from a natural-language '
          'description (e.g. "márgenes de Nvidia, TSMC y ASML", "precio de bitcoin del último año"). It is drawn on '
          'screen: describe it only in general terms.',
          {'query': S('What to chart, in natural language')}, ['query']),
        T('quick_thesis', 'QUICK THESIS ("Tesis rápida") on one company: ONE AI answer with sector panorama, '
          'competitors, geopolitical exposure, chokepoints, risks and an investment thesis, WITHOUT cited evidence. '
          'Opens its window and returns the thesis to summarize. For conclusions WITH cited evidence use open_company '
          'with view research instead.', company, ['company_name']),
        T('deep_search', 'DEEP SEARCH ("Búsqueda profunda"): a free, complex investment question investigated in '
          'several steps (plan → context → simulation → synthesis). Takes 30-90 seconds and the result appears in its '
          'own window — tell the user you are investigating and it will appear shortly. Only one runs at a time.',
          {'question': S('The complete question, in the user language')}, ['question']),
        T('place_order', 'Buy or sell on the user\'s broker account ("Mi cuenta"). That account may be a PRACTICE '
          '(paper) account or REAL money — every result says which in "mode" (paper | live). STRICT TWO STEPS: (1) '
          'call with confirmed=false: it returns an order summary WITHOUT executing and shows it on screen; read the '
          'summary aloud (symbol, buy/sell, amount, and whether it is simulated or REAL money) and ask for '
          'confirmation. (2) ONLY after an explicit verbal yes, call again with the SAME parameters and '
          'confirmed=true. If a PIN is needed the user types it on screen — never ask them to say it aloud. If it '
          'returns an error, read it as-is and do not retry.', {
              'symbol_or_name': S('Ticker, crypto pair or company/asset name, any casing (e.g. "NVDA", "Nvidia", '
                                  '"BTC/USD", "bitcoin")'),
              'side': E(('buy', 'sell'), 'buy or sell'),
              'notional_usd': N('Amount in US dollars (e.g. 100 = $100). Min 1, max 100000. Give notional_usd OR '
                                'qty.'),
              'qty': N('Number of shares/units, when the user says a quantity instead of dollars (e.g. "vende mis 3 '
                       'acciones" → 3). Give notional_usd OR qty, never invent the other.'),
              'confirmed': {'type': 'boolean', 'description': 'false = preview only (returns the summary to read to '
                            'the user). true = EXECUTE — only allowed after the user explicitly said yes to it.'},
          }, ['symbol_or_name', 'side', 'confirmed']),
        T('open_order_ticket', 'Open the KHIPU TRADING order ticket for a company so the user reviews and places the '
          'order THEMSELVES on screen. Nothing is sent by this tool.', company, ['company_name']),
        T('get_account_status', 'Status of the user\'s broker account ("Mi cuenta"): cash, equity, buying power, open '
          'positions with P&L, and whether it is a practice (paper) account or REAL money ("mode"). Opens that '
          'window. For the simulated practice portfolios open the "portfolios" screen instead.'),
        T('get_space_summary', 'Satellite counts per constellation (Starlink, OneWeb, Planet Labs, Iridium, GPS) from '
          'CelesTrak plus the next launch, with source and time. Use whenever the user asks about satellites, '
          'constellations, space or launches. If the result says the data is unavailable, say so — never invent a '
          'number.', {'query': S('Optional operator/constellation the user asked about, e.g. "Starlink". Leave empty '
                                 'for the overall summary.')}),
        T('run_guided_demo', 'The ONE-MINUTE GUIDED TOUR of Khipus OS, narrated by YOU while the app keeps the pace. '
          'STRICT RULE: start it ONLY when the user EXPLICITLY asks for a demo or tour ("demo", "demostración", '
          '"tour", "recorrido", "hazme una demo", "muéstrame la app") — NEVER at session start, on greetings, because '
          'the user seems new, or proactively. Flow: action start → say EXACTLY the returned "say" line (nothing '
          'before or after). The app then sends each next line as a message "[TOUR n/N] <line>": say EXACTLY the line '
          '(never the tag) and call no tool for it; after the last one stay quiet. Use action next only to RESUME '
          'after the user interrupted and said yes; it returns the next "say" line or done:true. Action stop ends it. '
          'If a result says stopped:true or done:true the tour is over: do not continue.',
          {'action': E(VOICE_TOUR_ACTIONS, 'start = begin the tour (default) · next = resume after an interruption '
                       '· stop = end it')}),
        T('control_interface', 'Adjust Khipus OS itself, only when the user asks: new_conversation (clear the chat) · '
          'arrange_windows (tidy the windows beside the chat) · close_all_windows · minimize_all_windows · '
          'simple_mode / pro_mode (how detailed the agents explain) · light_theme / dark_theme · spanish / english '
          '(interface language).', {'action': E(VOICE_UI_ACTIONS, 'What to change')}, ['action']),
    ]


def _sync_bixby_agent():
    """Empuja el cerebro de Khipu (system prompt + client tools + idioma) al
    agente de ElevenLabs — así Fabrizio no configura nada a mano. Idempotente.

    2026-10 (contrato ElevenLabs vigente, core/voice_agent.sync_agent): las
    herramientas son RECURSOS (/v1/convai/tools) referenciados con tool_ids —
    el viejo `prompt.tools` en línea está deprecado y el PATCH caía en silencio
    a "solo prompt" (Khipu hablaba pero no podía abrir nada). Además repara:
    TTS deprecado/solo-inglés (conservando la voz; ya NO baja eleven_v4 a
    flash), LLM retirado, client_events sin client_tool_call y, con
    ELEVENLABS_ALLOW_OVERRIDE, habilita los overrides de idioma/primer mensaje."""
    from core import voice_agent as _va
    try:
        return _va.sync_agent(_S.ELEVENLABS_KEY, _S.ELEVENLABS_AGENT_ID, BIXBY_SYSTEM_PROMPT,
                              _bixby_client_tools(), http=requests, language='es',
                              allow_overrides=_va.override_env_on(), retired_names=RETIRED_VOICE_TOOLS)
    except Exception as e:  # noqa: BLE001
        return {'ok': False, 'error': _S._diag_redact(e)[:300]}


@voice_bp.route('/api/voice/sync-agent', methods=['GET', 'POST'])
@rate_limit(limit=6, window=3600)
@_require_operator
def voice_sync_agent():
    """Sincroniza el agente de ElevenLabs con el cerebro definido aquí (PATCH
    del agente). PIN de operador: antes cualquiera podía dispararlo en bucle.
    El autosync del arranque no pasa por aquí. Deja policy.change voice.agent (lote I4) con la huella del prompt y los
    NOMBRES de las herramientas (nunca la clave)."""
    from core import voice_agent as _va
    did, bad = _voice_decision('sync', {
        'prompt_sha': hashlib.sha256(BIXBY_SYSTEM_PROMPT.encode('utf-8')).hexdigest(),
        'tools': sorted(t['name'] for t in _bixby_client_tools()), 'retired': len(RETIRED_VOICE_TOOLS),
        'language': 'es', 'allow_overrides': bool(_va.override_env_on())})
    if bad:
        return bad
    res = _sync_bixby_agent()
    _voice_outcome(did, res)
    return jsonify(res), (200 if res.get('ok') else 502)


def _voice_autosync_log(res):
    if res.get('ok'):
        log.info('Khipu sincronizado con ElevenLabs (%s, tools=%s/%s, creadas=%d, tts=%s, llm=%s)',
                 res.get('mode'), res.get('tools_registered'), res.get('tools_expected'),
                 len(res.get('tools_created') or []), res.get('tts_change'), res.get('llm_fixed'))
        if res.get('mode') != 'tool_ids':
            log.warning('Khipu autosync: modo %s — las herramientas pueden no estar registradas (%s)',
                        res.get('mode'), (res.get('tool_errors') or [])[:2])
    else:
        log.warning('Khipu autosync falló (la app sigue): %s', {k: res.get(k) for k in
                    ('stage', 'code', 'error', 'status', 'detail')})


def start_autosync():
    """Auto-sync al arrancar (BIXBY_AUTOSYNC=0 para desactivar). En background para no retrasar el boot; idempotente aunque los 2 workers de gunicorn lo llamen.
    Lo llama server.py tras bind() (antes corría al importar server.py)."""
    if os.getenv('BIXBY_AUTOSYNC', '1').strip().lower() not in ('0', 'false', 'no'):
        def _bixby_autosync():
            time.sleep(4)
            _voice_autosync_log(_sync_bixby_agent())
        try:
            if _S.ELEVENLABS_KEY and _S.ELEVENLABS_AGENT_ID:
                threading.Thread(target=_bixby_autosync, daemon=True).start()
        except Exception as _e:  # noqa: BLE001
            log.warning('Khipu autosync no arrancó: %s', _e)


@voice_bp.route('/api/voice/bixby-prompt', methods=['GET'])
def bixby_system_prompt():
    """Returns Khipu's system prompt for ElevenLabs agent configuration."""
    # allow_override: ELEVENLABS_ALLOW_OVERRIDE=true/1/yes (MISMO criterio que
    # adopt/agent-tune; antes aquí solo valía "true" y con "1" el sync se
    # activaba pero el navegador no). Desde 2026-10 /api/voice/session dice
    # además QUÉ overrides permite el agente de verdad, y voice.js reintenta
    # sin overrides si ElevenLabs cierra por override_error.
    from core.voice_agent import override_env_on
    allow_override = override_env_on()
    return jsonify({
        'system_prompt': BIXBY_SYSTEM_PROMPT,
        'agent_name': 'Khipu',
        'platform': 'Khipu Finance',
        'allow_override': allow_override,
    })


# ── Khipu voice — sesión firmada de ElevenLabs ───────────────────────────────
@voice_bp.route('/api/voice/session', methods=['POST'])
@rate_limit(limit=40, window=600)
def voice_session():
    """URL firmada (un solo uso, la clave NUNCA sale del server) + qué overrides
    permite el agente, para que el navegador no mande uno prohibido (ElevenLabs
    cierra el socket con override_error). Errores en ES/EN con el arreglo.
    Rate limit: cada sesión gasta minutos pagados de ElevenLabs."""
    from core import voice_agent as _va
    if not _S.ELEVENLABS_KEY:
        return jsonify({'error': 'La voz no está configurada en el servidor (falta ELEVENLABS_KEY).',
                        'error_en': 'Voice is not configured on the server (ELEVENLABS_KEY missing).',
                        'code': 'not_configured'}), 400
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    # el agente es el del server; el del navegador (preferencia vieja en
    # localStorage) solo se acepta si el server no tiene uno.
    agent_id = _S.ELEVENLABS_AGENT_ID
    if not agent_id:
        cand = str(data.get('agent_id') or '').strip()
        agent_id = cand if _SAFE_PATH_SEG.match(cand) else ''
    if not agent_id:
        return jsonify({'error': 'Falta ELEVENLABS_AGENT_ID en el servidor.',
                        'error_en': 'ELEVENLABS_AGENT_ID is missing on the server.',
                        'code': 'agent_missing'}), 400
    res = _va.get_signed_url(_S.ELEVENLABS_KEY, agent_id, requests)
    if not res.get('ok'):
        e = res.get('error') or {}
        code = e.get('code') or 'unknown'
        status = {'invalid_api_key': 502, 'missing_permissions': 502, 'quota_exceeded': 402,
                  'payment_required': 402, 'unusual_activity': 402, 'not_found': 404,
                  'rate_limited': 429}.get(code, 502)
        return jsonify({'error': _S._diag_redact(e.get('es') or 'ElevenLabs no respondió'),
                        'error_en': _S._diag_redact(e.get('en') or 'ElevenLabs did not respond'),
                        'code': code, 'fix_es': e.get('fix_es'), 'fix_en': e.get('fix_en')}), status
    out = {'signed_url': res['signed_url'], 'agent_id': agent_id,
           'override_env': _va.override_env_on()}
    try:
        cfg, _err = _va.get_agent(_S.ELEVENLABS_KEY, agent_id, requests, cached=True, timeout=4)
        if cfg:
            out.update(_va.session_hints(cfg))
    except Exception:  # noqa: BLE001 — sin pistas, voice.js decide con override_env + reintento
        pass
    return jsonify(out)



# ── Recorrido de un minuto con la voz de Khipu (2026-10-11) ─────────────────────────────────────
# Sin conversación de voz abierta, el recorrido (engine/cockpit.js) se narra con audio de la MISMA voz
# del agente de ElevenLabs. Solo frases del guion (engine/tour_script.js vía core/tour.py) — nunca texto
# libre — y en caché por (voz, modelo, frase): ~2.000 caracteres por idioma una vez por arranque.
_TOUR_AUDIO = {}                      # (voice_id, lang, step, hash) → (bytes, modelo)
_TOUR_AUDIO_LOCK = threading.Lock()


@voice_bp.route('/api/voice/tour/<lang>/<int:step>', methods=['GET'])
@rate_limit(limit=60, window=300)
def voice_tour_audio(lang, step):
    """Audio MP3 de la frase `step` del recorrido guiado, con la voz del agente de Khipu. 404 sin voz
    configurada o paso inexistente (el navegador muestra la narración escrita, como siempre)."""
    from core import tour as _tour
    from core import voice_agent as _va
    lang = str(lang or '').lower()
    if lang not in _tour.LANGS:
        return jsonify({'error': 'Idioma no válido.', 'error_en': 'Invalid language.', 'code': 'bad_lang'}), 400
    text = _tour.line(step, lang)
    if not text:
        return jsonify({'error': 'Ese paso del recorrido no existe.', 'error_en': 'That tour step does not exist.',
                        'code': 'not_found'}), 404
    if not (_S.ELEVENLABS_KEY and _S.ELEVENLABS_AGENT_ID):
        return jsonify({'error': 'La voz de Khipu no está configurada: el recorrido se muestra escrito.',
                        'error_en': 'Khipu voice is not configured: the tour is shown as text.',
                        'code': 'not_configured', 'available': False}), 404
    # la voz QUE USA el agente en ese idioma, con sus ajustes y su modelo (2026-10-12: el botón sonaba a la "voz
    # vieja"); lectura fresca (≤60 s) para que un cambio de voz en ElevenLabs se oiga enseguida
    cfg, err = _va.get_agent(_S.ELEVENLABS_KEY, _S.ELEVENLABS_AGENT_ID, requests, cached=True, timeout=6, max_age=60)
    tv = _va.tour_voice(cfg, lang) if cfg else {}
    voice_id = tv.get('voice_id')
    if not voice_id:
        e = err or {}
        return jsonify({'error': _S._diag_redact(e.get('es') or 'No pude leer la voz del agente de Khipu.'),
                        'error_en': _S._diag_redact(e.get('en') or 'Could not read the Khipu agent voice.'),
                        'code': e.get('code') or 'no_voice', 'available': False}), 502
    settings = tv.get('voice_settings') or {}
    sig = hashlib.sha1(json.dumps([voice_id, tv.get('models'), settings, _tour.text_hash(text)],
                                  sort_keys=True).encode('utf-8')).hexdigest()[:20]
    etag = f'"{sig}"'
    # el navegador revalida SIEMPRE (no-cache + ETag): misma voz → 304 sin bajar nada; voz nueva → audio nuevo
    if etag in [t.strip() for t in str(request.headers.get('If-None-Match') or '').split(',')]:
        resp = Response(status=304)
        resp.headers['ETag'] = etag
        resp.headers['Cache-Control'] = 'private, no-cache'
        return resp
    key = (sig, lang, step)
    hit = _TOUR_AUDIO.get(key)
    if not hit:
        with _TOUR_AUDIO_LOCK:                              # dos pestañas a la vez → UNA sola síntesis
            hit = _TOUR_AUDIO.get(key)
            if not hit:
                res = _va.synthesize(_S.ELEVENLABS_KEY, voice_id, text, requests, models=tv.get('models'),
                                     voice_settings=settings)
                if not res.get('ok'):
                    code = res.get('code') or 'unknown'
                    status = {'quota_exceeded': 402, 'payment_required': 402, 'rate_limited': 429}.get(code, 502)
                    return jsonify({'error': _S._diag_redact(res.get('es') or 'ElevenLabs no respondió'),
                                    'error_en': _S._diag_redact(res.get('en') or 'ElevenLabs did not respond'),
                                    'code': code, 'available': False}), status
                hit = (res['audio'], res.get('model'))
                if len(_TOUR_AUDIO) > 80:                     # tope: cambios de voz no acumulan sin fin
                    _TOUR_AUDIO.clear()
                _TOUR_AUDIO[key] = hit
    resp = Response(hit[0], mimetype='audio/mpeg')
    resp.headers['Cache-Control'] = 'private, no-cache'
    resp.headers['ETag'] = etag
    resp.headers['X-Tour-Model'] = str(hit[1] or '')
    return resp
