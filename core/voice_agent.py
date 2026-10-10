"""core/voice_agent.py — Khipu (voz) ↔ ElevenLabs Agents Platform (oct-2026).

UN solo lugar para hablar con la API REST de ElevenLabs desde el servidor:
sesión firmada, diagnóstico accionable (🩺) y reparación del agente (sync).
La clave vive SOLO aquí (env ELEVENLABS_KEY vía server.py); nada de esto llega
al navegador salvo la URL firmada de un solo uso.

Contrato verificado contra los SDK oficiales publicados en oct-2026
(@elevenlabs/elevenlabs-js 2.71.0, @elevenlabs/client 1.27.0,
@elevenlabs/types 0.24.0) — elevenlabs.io no es alcanzable desde el sandbox:
  · URL firmada: GET /v1/convai/conversation/get-signed-url?agent_id=…
    (antes get_signed_url con guion bajo: se prueba como respaldo si la ruta
    nueva respondiera 404 "Not Found"/405).
  · Herramientas: `conversation_config.agent.prompt.tools` (en línea) está
    DEPRECADO → las herramientas son recursos propios (/v1/convai/tools,
    {tool_config:{type:'client', name, description, parameters,
    expects_response, response_timeout_secs}}) y el agente las referencia con
    `prompt.tool_ids`. Mandar `tools` y `tool_ids` juntos se rechaza.
  · TTS de agentes: eleven_flash_v2(_5), eleven_multilingual_v2,
    eleven_v3_conversational, eleven_v4, eleven_v4_turbo; eleven_turbo_v2 y
    eleven_turbo_v2_5 están deprecados (→ flash). flash_v2/turbo_v2 = solo inglés.
  · Overrides por conversación: los permite el AGENTE en
    platform_settings.overrides.conversation_config_override.agent
    {prompt:{prompt}, language, first_message}. Si el cliente manda un campo
    no permitido, el servidor cierra el WebSocket (error_type override_error,
    cierre 1008) — por eso la sesión le dice al navegador QUÉ está permitido.
  · Eventos al cliente: conversation.client_events debe incluir
    client_tool_call para que las herramientas del navegador funcionen.
Todas las funciones reciben `http` (requests o un doble de pruebas) y NUNCA
lanzan: devuelven dicts con ok/error.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time

EL_API = 'https://api.elevenlabs.io'

# ── Catálogo (SDK oct-2026) ──────────────────────────────────────────────────
TTS_MODELS = ('eleven_flash_v2', 'eleven_flash_v2_5', 'eleven_multilingual_v2',
              'eleven_v3_conversational', 'eleven_v4', 'eleven_v4_turbo',
              'eleven_turbo_v2', 'eleven_turbo_v2_5')
TTS_DEPRECATED = {'eleven_turbo_v2': 'eleven_flash_v2', 'eleven_turbo_v2_5': 'eleven_flash_v2_5'}
TTS_ENGLISH_ONLY = ('eleven_flash_v2', 'eleven_turbo_v2')
TTS_DEFAULT = 'eleven_flash_v2_5'          # multilingüe y la de menor latencia
TTS_TUNABLE = tuple(m for m in TTS_MODELS if m not in TTS_DEPRECATED)

AUDIO_FORMATS = ('pcm_8000', 'pcm_16000', 'pcm_22050', 'pcm_24000', 'pcm_44100', 'pcm_48000', 'ulaw_8000')

# Eventos que el navegador (engine/voice.js) necesita recibir.
REQUIRED_CLIENT_EVENTS = ('conversation_initiation_metadata', 'audio', 'interruption',
                          'user_transcript', 'agent_response', 'agent_response_correction',
                          'client_tool_call', 'ping',
                          'agent_tool_response')   # end_call → dejar terminar la despedida (opcional en el SDK)

LANGUAGES = ('es', 'en', 'pt', 'pt-br', 'fr', 'de', 'it')

# LLM del agente: los retirados por los proveedores (Gemini 1.5/2.0, Claude 3,
# GPT-3.5/4 clásicos, previews con fecha) hacen que el agente falle en
# silencio ("llm_error"). El sync los sube a ELEVENLABS_LLM (o a este default,
# que está en el enum del SDK de oct-2026).
LLM_DEFAULT = 'gemini-3.5-flash'
_LLM_LEGACY_RE = re.compile(r'^(gemini-1\.|gemini-2\.0|claude-3|gpt-3\.5|gpt-4-0|gpt-4-turbo|grok-beta)')


def llm_is_legacy(llm) -> bool:
    s = str(llm or '').strip().lower()
    if not s:
        return False
    return bool(_LLM_LEGACY_RE.match(s)) or s in ('gpt-4',) or bool(re.search(r'preview-\d\d', s))


def llm_target() -> str:
    v = (os.getenv('ELEVENLABS_LLM') or '').strip()
    return v if re.match(r'^[A-Za-z0-9_.@:\-]{2,60}$', v or '') else LLM_DEFAULT


# Familias VIEJAS conocidas que no están en el catálogo (v1 retirados / solo inglés) → se reemplazan.
_TTS_LEGACY_RE = re.compile(r'^eleven_(monolingual_v1|multilingual_v1|english_|turbo_v1)')


def tts_model_unknown(model) -> bool:
    """¿Un modelo que no conocemos (p. ej. uno NUEVO de ElevenLabs que el dueño eligió)? Se deja como está."""
    m = str(model or '').strip()
    return bool(m) and m not in TTS_MODELS and not _TTS_LEGACY_RE.match(m)


def tts_fix_for(model, language='es'):
    """Modelo TTS al que hay que pasar (o None si el actual sirve). Solo se cambian los deprecados, los viejos
    conocidos, los de solo inglés en un agente que no es inglés y el vacío; uno DESCONOCIDO (más nuevo que esta
    lista) se respeta — el 🩺 avisa, pero el arranque nunca lo vuelve a flash_v2_5."""
    m = str(model or '').strip()
    lang = str(language or 'es').lower()
    if m in TTS_DEPRECATED:
        rep = TTS_DEPRECATED[m]
        return TTS_DEFAULT if (lang != 'en' and rep in TTS_ENGLISH_ONLY) else rep
    if not m or _TTS_LEGACY_RE.match(m):
        return TTS_DEFAULT
    if m not in TTS_MODELS:
        return None
    if lang != 'en' and m in TTS_ENGLISH_ONLY:
        return TTS_DEFAULT
    return None


def override_env_on() -> bool:
    return (os.getenv('ELEVENLABS_ALLOW_OVERRIDE') or '').strip().lower() in ('1', 'true', 'yes', 'on', 'si', 'sí')


def _hdr(key, json_body=False):
    h = {'xi-api-key': key}
    if json_body:
        h['Content-Type'] = 'application/json'
    return h


def _json(resp):
    try:
        d = resp.json()
        return d if d is not None else {}
    except Exception:  # noqa: BLE001
        return {}


# ── Errores de ElevenLabs → código + texto bilingüe + arreglo ───────────────
# Cuerpo típico: {"detail": {"status": "invalid_api_key", "message": "…"}}
# (401 también para cuota agotada y permisos faltantes de claves restringidas)
# o {"detail": "Not Found"} / {"detail": [{"loc":…, "msg":…}]} (422).
def classify_error(status_code, body=None, exc=None) -> dict:
    if exc is not None:
        return {'code': 'network', 'http': None, 'message': str(exc)[:200]}
    status_code = int(status_code or 0)
    text = ''
    st = ''
    if isinstance(body, (bytes, bytearray)):
        body = body.decode('utf-8', 'replace')
    if isinstance(body, str):
        text = body
        try:
            body = json.loads(body)
        except Exception:  # noqa: BLE001
            body = None
    if isinstance(body, dict):
        det = body.get('detail', body)
        if isinstance(det, dict):
            st = str(det.get('status') or det.get('code') or det.get('error_type') or '').lower()
            text = str(det.get('message') or det.get('msg') or text or '')
        elif isinstance(det, list):
            text = '; '.join(str((d or {}).get('msg') or d) for d in det[:3])
            st = st or 'validation'
        elif det is not None:
            text = str(det)
    low = (st + ' ' + text).lower()
    perm = None
    for m in re.finditer(r'permission[s]?\s+[\'"]?([a-z_]+)', low):
        if m.group(1) not in ('to', 'for', 'the', 'is', 'are', 'you', 'and', 'or'):
            perm = m.group(1)
            break
    if 'invalid_api_key' in low or 'invalid api key' in low or (status_code == 401 and 'api key' in low and 'permission' not in low and 'quota' not in low):
        code = 'invalid_api_key'
    elif 'missing_permission' in low or 'missing the permission' in low or ('permission' in low and status_code in (401, 403)):
        code = 'missing_permissions'
    elif 'quota' in low or 'credits' in low or 'max_character_limit' in low or 'character limit' in low:
        code = 'quota_exceeded'
    elif 'unusual' in low or 'free tier' in low or 'free_tier' in low or 'abuse' in low:
        code = 'unusual_activity'
    elif status_code == 402 or 'payment' in low or 'past_due' in low or 'subscription' in low and 'inactive' in low:
        code = 'payment_required'
    elif status_code == 404:
        code = 'not_found'
    elif status_code == 429 or 'too_many' in low or 'concurrent' in low or 'rate limit' in low or 'busy' in low:
        code = 'rate_limited'
    elif status_code == 422 or st == 'validation' or status_code == 400:
        code = 'validation'
    elif status_code in (401, 403):
        code = 'invalid_api_key'
    elif status_code >= 500:
        code = 'server_error'
    else:
        code = 'unknown'
    out = {'code': code, 'http': status_code or None, 'message': (text or '')[:240]}
    if perm:
        out['permission'] = perm
    return out


def describe(err: dict, what='key') -> dict:
    """Mensaje bilingüe y arreglo concreto (clics) para un error clasificado.
    `what`: 'key' (la clave) · 'agent' (el agente) · 'session' (conectar)."""
    code = (err or {}).get('code') or 'unknown'
    http = (err or {}).get('http')
    perm = (err or {}).get('permission')
    msg = (err or {}).get('message') or ''
    if code == 'invalid_api_key':
        return {'es': 'La clave de ElevenLabs (ELEVENLABS_KEY) es inválida o fue borrada.',
                'en': 'The ElevenLabs key (ELEVENLABS_KEY) is invalid or was deleted.',
                'fix_es': 'En elevenlabs.io: Developers → API Keys → Create key (o copia la que pagaste). '
                          'En Railway: tu servicio → Variables → ELEVENLABS_KEY = la clave nueva → guardar (redeploy solo).',
                'fix_en': 'On elevenlabs.io: Developers → API Keys → Create key. In Railway: your service → '
                          'Variables → ELEVENLABS_KEY = the new key → save (it redeploys).'}
    if code == 'missing_permissions':
        p = f' «{perm}»' if perm else ''
        return {'es': f'La clave de ElevenLabs no tiene el permiso{p}.',
                'en': f'The ElevenLabs key lacks the permission{p}.',
                'fix_es': 'En elevenlabs.io: Developers → API Keys → tu clave → Edit → activa "ElevenLabs Agents" '
                          '(Write), "Voices" (Read) y "User" (Read) → Save. O crea una clave sin restricciones.',
                'fix_en': 'On elevenlabs.io: Developers → API Keys → your key → Edit → enable "ElevenLabs Agents" '
                          '(Write), "Voices" (Read) and "User" (Read) → Save. Or create an unrestricted key.'}
    if code == 'quota_exceeded':
        return {'es': 'Se acabaron los créditos/minutos de ElevenLabs de este período.',
                'en': 'ElevenLabs credits/minutes for this period are used up.',
                'fix_es': 'En elevenlabs.io: tu avatar → Subscription → sube de plan o activa "Usage-based billing"; '
                          'o espera la fecha de renovación. Revisa que la clave sea de la cuenta que pagaste.',
                'fix_en': 'On elevenlabs.io: your avatar → Subscription → upgrade or enable usage-based billing, '
                          'or wait for the reset date. Check the key belongs to the account you paid for.'}
    if code == 'unusual_activity':
        return {'es': 'ElevenLabs bloqueó el uso gratuito de esta cuenta (actividad inusual / plan gratis).',
                'en': 'ElevenLabs blocked free usage on this account (unusual activity / free tier).',
                'fix_es': 'Usa una clave de la cuenta con plan pagado (elevenlabs.io → Developers → API Keys) '
                          'y ponla en Railway → Variables → ELEVENLABS_KEY.',
                'fix_en': 'Use a key from the paid account (elevenlabs.io → Developers → API Keys) and set it '
                          'in Railway → Variables → ELEVENLABS_KEY.'}
    if code == 'payment_required':
        return {'es': 'ElevenLabs reporta un problema de pago o suscripción inactiva.',
                'en': 'ElevenLabs reports a payment problem or an inactive subscription.',
                'fix_es': 'En elevenlabs.io: tu avatar → Subscription → revisa facturas pendientes / método de pago.',
                'fix_en': 'On elevenlabs.io: your avatar → Subscription → check open invoices / payment method.'}
    if code == 'not_found':
        if what in ('agent', 'session'):
            return {'es': 'El agente ELEVENLABS_AGENT_ID no existe o no es de la cuenta de esta clave.',
                    'en': 'The agent ELEVENLABS_AGENT_ID does not exist or belongs to another account.',
                    'fix_es': 'En elevenlabs.io: Agents → abre "Khipu" → copia su ID (empieza con agent_…). '
                              'En Railway → Variables → ELEVENLABS_AGENT_ID = ese ID. La clave debe ser de la MISMA cuenta.',
                    'fix_en': 'On elevenlabs.io: Agents → open "Khipu" → copy its ID (starts with agent_…). '
                              'In Railway → Variables → ELEVENLABS_AGENT_ID = that ID. The key must be from the SAME account.'}
        return {'es': 'ElevenLabs no encontró el recurso pedido (HTTP 404).',
                'en': 'ElevenLabs could not find the requested resource (HTTP 404).', 'fix_es': '', 'fix_en': ''}
    if code == 'rate_limited':
        return {'es': 'ElevenLabs está saturado o se alcanzó el límite de conversaciones simultáneas.',
                'en': 'ElevenLabs is busy or the concurrent-conversation limit was reached.',
                'fix_es': 'Espera unos segundos y vuelve a intentar. Si pasa seguido, tu plan permite pocas '
                          'conversaciones a la vez (elevenlabs.io → Subscription).',
                'fix_en': 'Wait a few seconds and retry. If it keeps happening, your plan allows few concurrent '
                          'conversations (elevenlabs.io → Subscription).'}
    if code == 'validation':
        return {'es': f'ElevenLabs rechazó los datos enviados (HTTP {http}): {msg[:140]}',
                'en': f'ElevenLabs rejected the request data (HTTP {http}): {msg[:140]}',
                'fix_es': 'Avísale a soporte técnico con este texto; la voz sigue con la configuración anterior.',
                'fix_en': 'Report this text to support; the voice keeps its previous configuration.'}
    if code == 'network':
        return {'es': 'No se pudo contactar con ElevenLabs (red o tiempo agotado).',
                'en': 'Could not reach ElevenLabs (network or timeout).',
                'fix_es': 'Reintenta en un minuto. Si sigue, mira status.elevenlabs.io.',
                'fix_en': 'Retry in a minute. If it persists, check status.elevenlabs.io.'}
    if code == 'server_error':
        return {'es': f'ElevenLabs tuvo un error interno (HTTP {http}).',
                'en': f'ElevenLabs had an internal error (HTTP {http}).',
                'fix_es': 'Reintenta en un minuto. Si sigue, mira status.elevenlabs.io.',
                'fix_en': 'Retry in a minute. If it persists, check status.elevenlabs.io.'}
    return {'es': f'ElevenLabs respondió HTTP {http}: {msg[:140]}',
            'en': f'ElevenLabs returned HTTP {http}: {msg[:140]}', 'fix_es': '', 'fix_en': ''}


def _http_err(resp, what='key'):
    try:
        body = resp.text
    except Exception:  # noqa: BLE001
        body = ''
    e = classify_error(getattr(resp, 'status_code', 0), body)
    e.update(describe(e, what))
    return e


def _exc_err(exc, what='key'):
    e = classify_error(None, exc=exc)
    e.update(describe(e, what))
    return e


# ── Agente (lectura con caché corta) ────────────────────────────────────────
_AGENT_CACHE: dict = {}
_AGENT_LOCK = threading.Lock()
AGENT_CACHE_TTL = 600
READ_RETRY_WAITS_S = (2.0, 5.0)     # sync: reintentos de LEER el agente ante un error pasajero


def _sleep(seconds):                 # inyectable en tests
    time.sleep(seconds)


def get_agent(key, agent_id, http, *, cached=True, timeout=8):
    """→ (cfg | None, err | None). Caché 10 min (la usa /api/voice/session)."""
    now = time.time()
    if cached:
        with _AGENT_LOCK:
            hit = _AGENT_CACHE.get(agent_id)
            if hit and now - hit[0] < AGENT_CACHE_TTL:
                return hit[1], None
    try:
        r = http.get(f'{EL_API}/v1/convai/agents/{agent_id}', headers=_hdr(key), timeout=timeout)
    except Exception as e:  # noqa: BLE001
        return None, _exc_err(e, 'agent')
    if getattr(r, 'status_code', 0) >= 400:
        return None, _http_err(r, 'agent')
    cfg = _json(r)
    with _AGENT_LOCK:
        _AGENT_CACHE[agent_id] = (now, cfg)
    return cfg, None


def forget_agent(agent_id=None):
    with _AGENT_LOCK:
        if agent_id is None:
            _AGENT_CACHE.clear()
        else:
            _AGENT_CACHE.pop(agent_id, None)


def _cc(cfg):
    return (cfg or {}).get('conversation_config') or {}


def agent_summary(cfg) -> dict:
    """Lo relevante del agente, con nombres planos."""
    cc = _cc(cfg)
    agent = cc.get('agent') or {}
    prompt = agent.get('prompt') or {}
    tts = cc.get('tts') or {}
    asr = cc.get('asr') or {}
    conv = cc.get('conversation') or {}
    ov = ((((cfg or {}).get('platform_settings') or {}).get('overrides') or {})
          .get('conversation_config_override') or {})
    ova = ov.get('agent') or {}
    ovp = ova.get('prompt') or {}
    ovt = ov.get('tts') or {}
    return {
        'name': (cfg or {}).get('name'),
        'language': agent.get('language'),
        'first_message': agent.get('first_message') or '',
        'llm': prompt.get('llm'),
        'prompt_text': prompt.get('prompt') or '',
        'tool_ids': list(prompt.get('tool_ids') or []),
        'legacy_tools': [t.get('name') for t in (prompt.get('tools') or []) if isinstance(t, dict)],
        'tts_model': tts.get('model_id'),
        'voice_id': tts.get('voice_id'),
        'output_format': tts.get('agent_output_audio_format') or 'pcm_16000',
        'input_format': asr.get('user_input_audio_format') or 'pcm_16000',
        'client_events': conv.get('client_events'),
        'max_duration_s': conv.get('max_duration_seconds'),
        'overrides': {'prompt': bool(ovp.get('prompt')), 'language': bool(ova.get('language')),
                      'first_message': bool(ova.get('first_message')), 'voice_id': bool(ovt.get('voice_id'))},
    }


def session_hints(cfg) -> dict:
    """Lo que el navegador necesita para NO mandar overrides prohibidos."""
    s = agent_summary(cfg)
    return {'overrides': s['overrides'], 'language': s['language'] or 'es',
            'has_first_message': bool((s['first_message'] or '').strip()),
            'output_format': s['output_format'], 'input_format': s['input_format']}


# ── Sesión firmada ───────────────────────────────────────────────────────────
SIGNED_URL_PATHS = ('/v1/convai/conversation/get-signed-url', '/v1/convai/conversation/get_signed_url')


def get_signed_url(key, agent_id, http, timeout=10) -> dict:
    last = None
    for i, path in enumerate(SIGNED_URL_PATHS):
        try:
            r = http.get(EL_API + path, params={'agent_id': agent_id}, headers=_hdr(key), timeout=timeout)
        except Exception as e:  # noqa: BLE001
            return {'ok': False, 'error': _exc_err(e, 'session')}
        sc = getattr(r, 'status_code', 0)
        if sc < 400:
            d = _json(r)
            url = d.get('signed_url') or d.get('signedUrl')
            if url and str(url).startswith('wss://'):
                return {'ok': True, 'signed_url': url, 'path': path}
            last = {'code': 'validation', 'http': sc, 'message': 'respuesta sin signed_url'}
            last.update(describe(last, 'session'))
            return {'ok': False, 'error': last}
        # ruta inexistente (FastAPI: {"detail":"Not Found"}) o método no permitido → probar la otra
        body = _json(r)
        route_missing = sc == 405 or (sc == 404 and body.get('detail') == 'Not Found')
        last = _http_err(r, 'session')
        if not (route_missing and i == 0):
            break
    return {'ok': False, 'error': last}


# ── Herramientas (recursos /v1/convai/tools) ────────────────────────────────
def list_tools(key, http, max_pages=5, timeout=12):
    """→ ({tool_id: tool_config}, err|None). Todas las del workspace (paginado)."""
    out, cursor = {}, None
    for _ in range(max_pages):
        params = {'page_size': 100}
        if cursor:
            params['cursor'] = cursor
        try:
            r = http.get(f'{EL_API}/v1/convai/tools', params=params, headers=_hdr(key), timeout=timeout)
        except Exception as e:  # noqa: BLE001
            return out, _exc_err(e, 'agent')
        if getattr(r, 'status_code', 0) >= 400:
            return out, _http_err(r, 'agent')
        d = _json(r)
        for t in d.get('tools') or []:
            if isinstance(t, dict) and t.get('id'):
                out[t['id']] = t.get('tool_config') or {}
        cursor = d.get('next_cursor')
        if not d.get('has_more') or not cursor:
            break
    return out, None


def _subset_equal(want, have) -> bool:
    """¿`have` (lo que devuelve la API, con campos extra en null) contiene `want`?"""
    if isinstance(want, dict):
        if not isinstance(have, dict):
            return False
        return all(_subset_equal(v, have.get(k)) for k, v in want.items())
    if isinstance(want, list):
        if not isinstance(have, list) or len(want) != len(have):
            return False
        if all(isinstance(x, str) for x in want):
            return sorted(want) == sorted(str(x) for x in have)
        return all(_subset_equal(a, b) for a, b in zip(want, have))
    return want == have


def tool_payload(spec: dict) -> dict:
    """Spec interna (la de server._bixby_client_tools) → tool_config de la API."""
    cfg = {'type': 'client', 'name': spec['name'], 'description': spec.get('description') or spec['name'],
           'expects_response': bool(spec.get('expects_response', True))}
    t = spec.get('response_timeout_secs')
    if t:
        cfg['response_timeout_secs'] = int(max(1, min(120, int(t))))
    params = spec.get('parameters') or {}
    if params.get('properties'):
        cfg['parameters'] = {'type': 'object', 'properties': params['properties'],
                             'required': list(params.get('required') or [])}
    return cfg


def ensure_tools(key, http, specs, current_ids, timeout=15) -> dict:
    """Crea/actualiza las herramientas cliente de Khipu y devuelve sus ids.
    Reusa (por nombre) las que el agente ya referencia — incluidas las que
    ElevenLabs migró solas desde el viejo `prompt.tools` — y las actualiza
    solo si cambiaron. → {ok, ids_by_name, keep_ids, created, updated, errors}"""
    listing, err = list_tools(key, http)
    names = {s['name'] for s in specs}
    current_ids = list(current_ids or [])
    if err and not listing and not current_ids:
        # no se pudo listar y el agente no referencia ninguna: crear a ciegas DUPLICARÍA las que ya existen en
        # el workspace → nada de POST; sync_agent cae al formato en línea (o solo prompt) y reintenta luego
        return {'ok': False, 'ids_by_name': {}, 'keep_ids': [], 'created': [], 'updated': [],
                'errors': [], 'list_error': err}
    if err and current_ids:
        # sin permiso de listar: leer una por una las que ya tiene el agente
        for tid in current_ids[:60]:
            try:
                r = http.get(f'{EL_API}/v1/convai/tools/{tid}', headers=_hdr(key), timeout=timeout)
                if getattr(r, 'status_code', 0) < 400:
                    listing[tid] = (_json(r).get('tool_config') or {})
            except Exception:  # noqa: BLE001
                pass
    by_name: dict = {}
    for tid, cfg in listing.items():
        nm = (cfg or {}).get('name')
        if nm in names and (cfg or {}).get('type', 'client') == 'client':
            by_name.setdefault(nm, []).append(tid)
    ids_by_name, created, updated, errors = {}, [], [], []
    for spec in specs:
        want = tool_payload(spec)
        cands = by_name.get(spec['name']) or []
        tid = next((c for c in cands if c in current_ids), None) or (cands[0] if cands else None)
        try:
            if tid:
                if not _subset_equal(want, listing.get(tid) or {}):
                    r = http.patch(f'{EL_API}/v1/convai/tools/{tid}', headers=_hdr(key, True),
                                   json={'tool_config': want}, timeout=timeout)
                    if getattr(r, 'status_code', 0) >= 400:
                        errors.append({'tool': spec['name'], **_http_err(r, 'agent')})
                    else:
                        updated.append(spec['name'])
                ids_by_name[spec['name']] = tid
            else:
                r = http.post(f'{EL_API}/v1/convai/tools', headers=_hdr(key, True),
                              json={'tool_config': want}, timeout=timeout)
                if getattr(r, 'status_code', 0) >= 400:
                    errors.append({'tool': spec['name'], **_http_err(r, 'agent')})
                    continue
                new_id = _json(r).get('id')
                if new_id:
                    ids_by_name[spec['name']] = new_id
                    created.append(spec['name'])
        except Exception as e:  # noqa: BLE001
            errors.append({'tool': spec['name'], **_exc_err(e, 'agent')})
    # ids que el agente ya tenía y NO son de Khipu (webhooks/MCP del dueño): se conservan
    managed = {tid for lst in by_name.values() for tid in lst}
    keep = [tid for tid in current_ids if tid not in managed and tid not in ids_by_name.values()]
    return {'ok': bool(ids_by_name), 'ids_by_name': ids_by_name, 'keep_ids': keep, 'created': created, 'updated': updated,
            'errors': errors[:10], 'list_error': err}


# ── Sync (reparación) ────────────────────────────────────────────────────────
def build_agent_patch(cur_summary: dict, prompt: str, tool_ids, *, language='es',
                      allow_overrides=False, legacy_tools=None) -> tuple:
    """→ (payload PATCH, cambios{tts_fixed, llm_fixed, client_events_fixed, overrides_enabled})."""
    prompt_cfg = {'prompt': prompt}
    if legacy_tools is not None:
        prompt_cfg['tools'] = legacy_tools
    elif tool_ids is not None:
        prompt_cfg['tool_ids'] = list(tool_ids)
    changes = {'tts_fixed': None, 'llm_fixed': None, 'client_events_fixed': False, 'overrides_enabled': False}
    if llm_is_legacy(cur_summary.get('llm')):
        prompt_cfg['llm'] = llm_target()
        changes['llm_fixed'] = {'from': cur_summary.get('llm'), 'to': prompt_cfg['llm']}
    cc = {'agent': {'prompt': prompt_cfg, 'language': language}}
    fix = tts_fix_for(cur_summary.get('tts_model'), language)
    if fix:
        tts = {'model_id': fix}
        if cur_summary.get('voice_id'):
            tts['voice_id'] = cur_summary['voice_id']          # conservar SU voz
        cc['tts'] = tts
        changes['tts_fixed'] = {'from': cur_summary.get('tts_model'), 'to': fix}
    ev = cur_summary.get('client_events')
    if isinstance(ev, list):
        missing = [e for e in REQUIRED_CLIENT_EVENTS if e not in ev]
        if missing:
            cc['conversation'] = {'client_events': list(ev) + missing}
            changes['client_events_fixed'] = missing
    payload = {'conversation_config': cc}
    if allow_overrides:
        ov = cur_summary.get('overrides') or {}
        if not (ov.get('language') and ov.get('first_message')):
            payload['platform_settings'] = {'overrides': {'conversation_config_override': {
                'agent': {'language': True, 'first_message': True}}}}
            changes['overrides_enabled'] = True
    return payload, changes


def sync_agent(key, agent_id, prompt, tool_specs, *, http, language='es', allow_overrides=False) -> dict:
    """Empuja el cerebro de Khipu al agente: prompt + herramientas (recursos
    con tool_ids) + idioma, y REPARA lo viejo: TTS deprecado o solo-inglés,
    LLM retirado, client_events sin client_tool_call y (si
    ELEVENLABS_ALLOW_OVERRIDE) habilita los overrides de idioma/primer mensaje.
    Idempotente. Si el API de herramientas no está disponible, cae al formato
    en línea viejo y, en último caso, solo al prompt."""
    if not (key and agent_id):
        return {'ok': False, 'error': 'ELEVENLABS_KEY / ELEVENLABS_AGENT_ID no configurados',
                'error_en': 'ELEVENLABS_KEY / ELEVENLABS_AGENT_ID are not set'}
    url = f'{EL_API}/v1/convai/agents/{agent_id}'
    cfg, err = get_agent(key, agent_id, http, cached=False, timeout=15)
    for wait_s in READ_RETRY_WAITS_S:
        # un tropiezo pasajero de ElevenLabs al arrancar (red, 5xx, 429) se reintenta; uno definitivo no
        if cfg is not None or (err or {}).get('code') not in ('network', 'server_error', 'rate_limited', 'unknown'):
            break
        _sleep(wait_s)
        cfg, err = get_agent(key, agent_id, http, cached=False, timeout=15)
    if cfg is None:
        # SIN la configuración real del agente NO se parchea nada: un resumen vacío haría creer que no tiene
        # modelo de voz (→ bajaría eleven_v4 a flash_v2_5) ni herramientas propias (→ borraría los webhooks
        # del dueño) y ensure_tools volvería a crear las 28. Se reintenta en el próximo arranque o con 🩺.
        err = err or {}
        return {'ok': False, 'stage': 'read_agent', 'error': err.get('es') or 'no se pudo leer el agente',
                'error_en': err.get('en') or 'could not read the agent', 'code': err.get('code') or 'unknown',
                'fix_es': err.get('fix_es'), 'fix_en': err.get('fix_en'), 'detail': err.get('message')}
    cur = agent_summary(cfg)
    tools = ensure_tools(key, http, tool_specs, cur['tool_ids'])
    res = {'tools_expected': len(tool_specs), 'tools_created': tools['created'],
           'tools_updated': tools['updated'], 'tool_errors': tools['errors']}
    attempts = []
    if tools['ids_by_name']:
        ids = [tools['ids_by_name'][s['name']] for s in tool_specs if s['name'] in tools['ids_by_name']]
        attempts.append(('tool_ids', ids + tools['keep_ids'], None))
    attempts.append(('legacy_inline', None, [tool_payload(s) for s in tool_specs]))
    attempts.append(('prompt_only', None, None))
    attempts.append(('prompt_minimal', None, None))
    last_err = None
    for mode, ids, legacy in attempts:
        payload, changes = build_agent_patch(cur, prompt, ids, language=language,
                                             allow_overrides=allow_overrides, legacy_tools=legacy)
        if mode == 'prompt_minimal':
            # último recurso: SOLO el texto del prompt (sin idioma/TTS/LLM/eventos que
            # pudieran ser el campo rechazado) — Khipu al menos queda con sus instrucciones
            payload = {'conversation_config': {'agent': {'prompt': {'prompt': prompt}}}}
            changes = {'tts_fixed': None, 'llm_fixed': None, 'client_events_fixed': False,
                       'overrides_enabled': False}
        try:
            r = http.patch(url, json=payload, headers=_hdr(key, True), timeout=25)
        except Exception as e:  # noqa: BLE001
            last_err = _exc_err(e, 'agent')
            break
        if getattr(r, 'status_code', 0) < 400:
            forget_agent(agent_id)
            chk, _ = get_agent(key, agent_id, http, cached=False, timeout=15)
            after = agent_summary(chk or {})
            registered = None
            if mode == 'tool_ids' and chk is not None:
                registered = len([i for i in (ids or []) if i in after['tool_ids']][:len(tool_specs)])
            elif mode == 'legacy_inline' and chk is not None:
                registered = len(after['legacy_tools'] or after['tool_ids'])
            res.update({'ok': True, 'mode': mode, 'status': r.status_code, 'tools_registered': registered,
                        'tts_fixed': bool(changes['tts_fixed']), 'tts_change': changes['tts_fixed'],
                        'llm_fixed': changes['llm_fixed'], 'client_events_fixed': changes['client_events_fixed'],
                        'overrides_enabled': changes['overrides_enabled'],
                        'tts_model': after.get('tts_model'), 'llm': after.get('llm')})
            if last_err:
                res['fallback_reason'] = last_err.get('message') or last_err.get('es')
            return res
        last_err = _http_err(r, 'agent')
        if last_err.get('code') in ('invalid_api_key', 'missing_permissions', 'not_found', 'quota_exceeded'):
            break
    res.update({'ok': False, 'mode': 'failed', 'status': (last_err or {}).get('http'),
                'error': (last_err or {}).get('es'), 'error_en': (last_err or {}).get('en'),
                'code': (last_err or {}).get('code'), 'detail': (last_err or {}).get('message'),
                'fix_es': (last_err or {}).get('fix_es'), 'fix_en': (last_err or {}).get('fix_en')})
    return res


# ── Diagnóstico accionable (🩺) ──────────────────────────────────────────────
def _check(cid, level, es, en, fix_es='', fix_en=''):
    return {'id': cid, 'level': level, 'ok': level == 'ok', 'es': es, 'en': en, 'fix_es': fix_es, 'fix_en': fix_en}


_SYNC_FIX_ES = ('Se arregla solo al reiniciar el servidor (Railway → tu servicio → Deployments → ⋮ → Redeploy); '
                'el arranque sincroniza a Khipu con ElevenLabs.')
_SYNC_FIX_EN = ('Fixed automatically on server restart (Railway → your service → Deployments → ⋮ → Redeploy); '
                'boot syncs Khipu with ElevenLabs.')


def diagnose(key, agent_id, *, http, expected_tools=(), prompt=None, full=False) -> dict:
    """Revisa clave, saldo, agente, LLM, voz, modelo TTS, overrides,
    herramientas, eventos y prompt. → {configured, ok, checks[], fixes[],
    detail (ES), detail_en, subscription, agent, latency_ms}."""
    t0 = time.time()
    checks = []
    out = {'configured': bool(key), 'agent_configured': bool(agent_id), 'checks': checks}
    if not key:
        checks.append(_check('key', 'error', 'ELEVENLABS_KEY no está en el servidor: Khipu (voz) no puede conectar.',
                             'ELEVENLABS_KEY is not set on the server: Khipu (voice) cannot connect.',
                             'Railway → tu servicio → Variables → New Variable → ELEVENLABS_KEY = tu clave de '
                             'elevenlabs.io (Developers → API Keys).',
                             'Railway → your service → Variables → New Variable → ELEVENLABS_KEY = your key '
                             'from elevenlabs.io (Developers → API Keys).'))
        return _finish(out, t0)

    # 1) clave + saldo
    sub = None
    try:
        r = http.get(f'{EL_API}/v1/user/subscription', headers=_hdr(key), timeout=8)
        if getattr(r, 'status_code', 0) < 400:
            sub = _json(r)
        else:
            e = _http_err(r, 'key')
            if e['code'] == 'missing_permissions':
                checks.append(_check('key', 'warn', 'Clave válida, pero sin permiso para leer el saldo (User: Read).',
                                     'Key is valid but cannot read the balance (User: Read).',
                                     e['fix_es'], e['fix_en']))
            else:
                checks.append(_check('key', 'error', e['es'], e['en'], e['fix_es'], e['fix_en']))
                if e['code'] in ('invalid_api_key', 'unusual_activity', 'payment_required'):
                    out['key_error'] = e['code']
                    return _finish(out, t0)
    except Exception as e:  # noqa: BLE001
        ee = _exc_err(e)
        checks.append(_check('key', 'error', ee['es'], ee['en'], ee['fix_es'], ee['fix_en']))
        return _finish(out, t0)
    if sub is not None:
        checks.append(_check('key', 'ok', 'Clave de ElevenLabs válida.', 'ElevenLabs key is valid.'))
        used, limit = sub.get('character_count'), sub.get('character_limit')
        tier, status = str(sub.get('tier') or ''), str(sub.get('status') or '')
        pct = None
        try:
            if limit:
                pct = round(100.0 * float(used or 0) / float(limit), 1)
        except Exception:  # noqa: BLE001
            pct = None
        reset = sub.get('next_character_count_reset_unix')
        out['subscription'] = {'tier': tier, 'status': status, 'used': used, 'limit': limit, 'pct': pct,
                               'resets_at': (time.strftime('%Y-%m-%d', time.gmtime(int(reset))) if reset else None),
                               'can_extend': sub.get('can_extend_character_limit')}
        extend = sub.get('can_extend_character_limit') and sub.get('max_credit_limit_extension') not in (0, '0', None)
        if status in ('past_due', 'incomplete', 'free_disabled'):
            e = describe({'code': 'payment_required'})
            checks.append(_check('plan', 'error', f'Suscripción «{tier}» en estado {status}. ' + e['es'],
                                 f'Subscription "{tier}" is {status}. ' + e['en'], e['fix_es'], e['fix_en']))
        elif tier == 'free' or status == 'free':
            checks.append(_check('plan', 'warn',
                                 'La clave es de una cuenta en plan GRATIS. Si ya pagaste, esta clave es de otra cuenta.',
                                 'The key belongs to a FREE-plan account. If you paid, this key is from another account.',
                                 'En la cuenta que pagaste: elevenlabs.io → Developers → API Keys → Create key; '
                                 'ponla en Railway → Variables → ELEVENLABS_KEY.',
                                 'In the paid account: elevenlabs.io → Developers → API Keys → Create key; '
                                 'set it in Railway → Variables → ELEVENLABS_KEY.'))
        else:
            checks.append(_check('plan', 'ok', f'Plan «{tier}» activo.', f'Plan "{tier}" active.'))
        if pct is not None and pct >= 100 and not extend:
            e = describe({'code': 'quota_exceeded'})
            checks.append(_check('quota', 'error', e['es'] + f' ({pct}% usado)', e['en'] + f' ({pct}% used)',
                                 e['fix_es'], e['fix_en']))
        elif pct is not None and pct >= 90:
            checks.append(_check('quota', 'warn', f'Créditos casi agotados: {pct}% usado.',
                                 f'Credits almost used up: {pct}% used.',
                                 'elevenlabs.io → tu avatar → Subscription (sube de plan o espera la renovación'
                                 + (f' del {out["subscription"]["resets_at"]}' if out['subscription']['resets_at'] else '') + ').',
                                 'elevenlabs.io → your avatar → Subscription (upgrade or wait for the reset).'))
        elif pct is not None:
            checks.append(_check('quota', 'ok', f'Créditos: {pct}% usado.', f'Credits: {pct}% used.'))

    # 2) agente
    if not agent_id:
        checks.append(_check('agent', 'error', 'Falta ELEVENLABS_AGENT_ID: Khipu no sabe a qué agente conectar.',
                             'ELEVENLABS_AGENT_ID is missing: Khipu does not know which agent to use.',
                             'elevenlabs.io → Agents → "Khipu" → copia el ID (agent_…). Railway → Variables → '
                             'ELEVENLABS_AGENT_ID = ese ID.',
                             'elevenlabs.io → Agents → "Khipu" → copy the ID (agent_…). Railway → Variables → '
                             'ELEVENLABS_AGENT_ID = that ID.'))
        return _finish(out, t0)
    cfg, err = get_agent(key, agent_id, http, cached=False, timeout=8)
    if err:
        out['agent_ok'] = False
        checks.append(_check('agent', 'error', err['es'], err['en'], err['fix_es'], err['fix_en']))
        return _finish(out, t0)
    out['agent_ok'] = True
    s = agent_summary(cfg)
    lang = (s['language'] or 'en')
    checks.append(_check('agent', 'ok', f'Agente «{s["name"] or agent_id}» encontrado.',
                         f'Agent "{s["name"] or agent_id}" found.'))

    # LLM
    if not s['llm']:
        checks.append(_check('llm', 'warn', 'El agente no declara LLM (usa el predeterminado de ElevenLabs).',
                             'The agent declares no LLM (ElevenLabs default).'))
    elif llm_is_legacy(s['llm']):
        checks.append(_check('llm', 'error', f'El LLM del agente («{s["llm"]}») es un modelo retirado o viejo: '
                                             f'Khipu puede no responder o fallar al usar herramientas (se cambiará a '
                                             f'{llm_target()}).',
                             f'The agent LLM ("{s["llm"]}") is retired/old: Khipu may not answer or fail with tools '
                             f'(it will move to {llm_target()}).',
                             _SYNC_FIX_ES, _SYNC_FIX_EN))
    else:
        checks.append(_check('llm', 'ok', f'LLM: {s["llm"]}.', f'LLM: {s["llm"]}.'))

    # TTS
    fix = tts_fix_for(s['tts_model'], lang)
    if fix:
        why_es = ('deprecado' if s['tts_model'] in TTS_DEPRECATED else
                  'solo inglés' if s['tts_model'] in TTS_ENGLISH_ONLY else 'desconocido o vacío')
        why_en = ('deprecated' if s['tts_model'] in TTS_DEPRECATED else
                  'English-only' if s['tts_model'] in TTS_ENGLISH_ONLY else 'unknown or empty')
        checks.append(_check('tts', 'error' if s['tts_model'] in TTS_ENGLISH_ONLY and lang != 'en' else 'warn',
                             f'Modelo de voz «{s["tts_model"] or "—"}» ({why_es}) para un agente en «{lang}» '
                             f'(se cambiará a {fix}, conservando la voz).',
                             f'Voice model "{s["tts_model"] or "—"}" ({why_en}) for a "{lang}" agent '
                             f'(it will move to {fix}, keeping the voice).',
                             _SYNC_FIX_ES, _SYNC_FIX_EN))
    elif tts_model_unknown(s['tts_model']):
        checks.append(_check('tts', 'warn',
                             f'Modelo de voz «{s["tts_model"]}»: no está en la lista que conoce Khipus; se deja como está.',
                             f'Voice model "{s["tts_model"]}": not in the list Khipus knows; it is left as is.',
                             'Si Khipu no habla o suena mal: elevenlabs.io → Agents → Khipu → Voice → elige '
                             f'{TTS_DEFAULT} → Publish.',
                             'If Khipu does not speak or sounds wrong: elevenlabs.io → Agents → Khipu → Voice → pick '
                             f'{TTS_DEFAULT} → Publish.'))
    else:
        checks.append(_check('tts', 'ok', f'Modelo de voz: {s["tts_model"]}.', f'Voice model: {s["tts_model"]}.'))
    if not s['voice_id']:
        checks.append(_check('voice', 'warn', 'El agente no tiene voz elegida.', 'The agent has no voice selected.',
                             'elevenlabs.io → Agents → Khipu → Voice → elige una voz en español → Publish.',
                             'elevenlabs.io → Agents → Khipu → Voice → pick a Spanish voice → Publish.'))
    elif full:
        try:
            vr = http.get(f'{EL_API}/v1/voices/{s["voice_id"]}', headers=_hdr(key), timeout=6)
            if getattr(vr, 'status_code', 0) < 400:
                out['voice_name'] = _json(vr).get('name')
                checks.append(_check('voice', 'ok', f'Voz: {out["voice_name"] or s["voice_id"]}.',
                                     f'Voice: {out["voice_name"] or s["voice_id"]}.'))
            elif getattr(vr, 'status_code', 0) == 404:
                checks.append(_check('voice', 'error', 'La voz configurada en el agente ya no existe en la cuenta.',
                                     'The agent voice no longer exists in the account.',
                                     'elevenlabs.io → Agents → Khipu → Voice → elige otra voz → Publish.',
                                     'elevenlabs.io → Agents → Khipu → Voice → pick another voice → Publish.'))
        except Exception:  # noqa: BLE001
            pass

    # Eventos al navegador
    ev = s['client_events']
    if isinstance(ev, list):
        miss = [e for e in ('audio', 'client_tool_call', 'interruption') if e not in ev]
        if miss:
            checks.append(_check('events', 'error', 'El agente no envía al navegador: ' + ', '.join(miss)
                                 + ' (sin esto Khipu no habla o no controla la app).',
                                 'The agent does not send to the browser: ' + ', '.join(miss) + '.',
                                 _SYNC_FIX_ES, _SYNC_FIX_EN))
        else:
            checks.append(_check('events', 'ok', 'Eventos del cliente correctos.', 'Client events OK.'))

    # Herramientas
    want = [t if isinstance(t, str) else t.get('name') for t in (expected_tools or [])]
    if want:
        have_names = set(n for n in s['legacy_tools'] if n)
        if s['tool_ids']:
            listing, lerr = list_tools(key, http, max_pages=(3 if full else 2), timeout=(8 if full else 6))
            for tid in s['tool_ids']:
                nm = (listing.get(tid) or {}).get('name')
                if nm:
                    have_names.add(nm)
            if lerr and not have_names:
                have_names = None
        missing = None if have_names is None else [n for n in want if n not in have_names]
        out['tools'] = {'expected': len(want), 'tool_ids': len(s['tool_ids']),
                        'missing': (missing or [])[:30] if missing is not None else None}
        if missing is None:
            checks.append(_check('tools', 'warn', f'El agente tiene {len(s["tool_ids"])} herramientas (no pude '
                                                  'leer sus nombres).',
                                 f'The agent has {len(s["tool_ids"])} tools (could not read their names).'))
        elif len(missing) == len(want):
            checks.append(_check('tools', 'error', 'El agente NO tiene las herramientas de Khipu: puede hablar '
                                                   'pero no abrir empresas, simular ni consultar datos.',
                                 'The agent has NONE of the Khipu tools: it can talk but cannot open companies, '
                                 'simulate or query data.', _SYNC_FIX_ES, _SYNC_FIX_EN))
        elif missing:
            checks.append(_check('tools', 'warn', f'Faltan {len(missing)} de {len(want)} herramientas de Khipu '
                                                  f'({", ".join(missing[:4])}…).',
                                 f'{len(missing)} of {len(want)} Khipu tools are missing.', _SYNC_FIX_ES, _SYNC_FIX_EN))
        else:
            checks.append(_check('tools', 'ok', f'Las {len(want)} herramientas de Khipu están registradas.',
                                 f'All {len(want)} Khipu tools are registered.'))

    # Prompt
    if prompt:
        same = (s['prompt_text'] or '').strip() == prompt.strip()
        checks.append(_check('prompt', 'ok' if same else 'warn',
                             'Instrucciones de Khipu al día.' if same else
                             'Las instrucciones del agente no son las de esta versión de Khipu.',
                             'Khipu instructions up to date.' if same else
                             'The agent instructions differ from this Khipu version.',
                             '' if same else _SYNC_FIX_ES, '' if same else _SYNC_FIX_EN))

    # Overrides (idioma por usuario)
    ov = s['overrides']
    env_on = override_env_on()
    if ov['language']:
        checks.append(_check('overrides', 'ok', 'El agente permite cambiar el idioma por sesión (ES/EN).',
                             'The agent allows per-session language (ES/EN).'))
    else:
        checks.append(_check('overrides', 'warn' if env_on else 'info',
                             'El agente no permite cambiar el idioma por sesión: en inglés Khipu seguirá '
                             'escuchando en español. (La app ya no se corta por esto.)',
                             'The agent does not allow per-session language: in English Khipu still listens '
                             'in Spanish. (The app no longer disconnects because of it.)',
                             'elevenlabs.io → Agents → Khipu → pestaña Security → Overrides → activa "Language" y '
                             '"First message" → Save. O pon ELEVENLABS_ALLOW_OVERRIDE=true en Railway y reinicia.',
                             'elevenlabs.io → Agents → Khipu → Security tab → Overrides → enable "Language" and '
                             '"First message" → Save. Or set ELEVENLABS_ALLOW_OVERRIDE=true in Railway and restart.'))
    out['agent'] = {'name': s['name'], 'llm': s['llm'], 'llm_legacy': llm_is_legacy(s['llm']),
                    'voice_id': s['voice_id'], 'voice_name': out.get('voice_name'),
                    'tts_model': s['tts_model'], 'tts_fix': fix, 'language': s['language'],
                    'output_format': s['output_format'], 'input_format': s['input_format'],
                    'overrides': ov, 'first_message': (s['first_message'] or '')[:120],
                    'client_events': ev, 'tool_ids': len(s['tool_ids'])}
    return _finish(out, t0)


def _finish(out, t0):
    checks = out.get('checks') or []
    errs = [c for c in checks if c['level'] == 'error']
    warns = [c for c in checks if c['level'] == 'warn']
    out['ok'] = bool(out.get('configured')) and bool(out.get('agent_configured')) and not errs
    out['latency_ms'] = int((time.time() - t0) * 1000)
    fixes = []
    for c in errs + warns:
        if c.get('fix_es') and {'es': c['fix_es'], 'en': c['fix_en']} not in fixes:
            fixes.append({'es': c['fix_es'], 'en': c['fix_en']})
    out['fixes'] = fixes
    if out['ok'] and not warns:
        head_es, head_en = 'Todo en orden: Khipu (voz) debería conectar y usar sus herramientas.', \
            'All good: Khipu (voice) should connect and use its tools.'
    elif out['ok']:
        head_es, head_en = 'Khipu (voz) conecta, con avisos:', 'Khipu (voice) connects, with warnings:'
    else:
        head_es, head_en = 'Khipu (voz) tiene problemas:', 'Khipu (voice) has problems:'
    probs_es = ' '.join(f'• {c["es"]}' for c in errs + warns)
    probs_en = ' '.join(f'• {c["en"]}' for c in errs + warns)
    fx_es = ' '.join(f'{i}) {f["es"]}' for i, f in enumerate(fixes, 1))
    fx_en = ' '.join(f'{i}) {f["en"]}' for i, f in enumerate(fixes, 1))
    out['detail'] = (head_es + (' ' + probs_es if probs_es else '')
                     + (' — QUÉ HACER: ' + fx_es if fx_es else '')).strip()
    out['detail_en'] = (head_en + (' ' + probs_en if probs_en else '')
                        + (' — WHAT TO DO: ' + fx_en if fx_en else '')).strip()
    return out
