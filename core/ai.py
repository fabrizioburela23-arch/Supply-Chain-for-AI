"""core/ai.py — cascada multi-proveedor de IA (Claude → Gemini → NVIDIA).

Compartida por las rutas del server, los agentes de la ontología y (próximo)
el motor de matrices. Un solo lugar para proveedores, orden y parsing.

Endurecimiento (auditoría estructural 2026-09-30):
  · #2 hambre de hilos: gunicorn corre 1 worker con pocos hilos; el cliente de
    Anthropic por defecto espera hasta 10 min y reintenta 2 veces → unas pocas
    llamadas colgadas dejaban la app entera sin hilos. Ahora: timeout corto
    (AI_CLAUDE_TIMEOUT_S, 60 s fast / 110 s deep), SIN reintentos del SDK en
    timeouts (un cuelgue no se repite: la cascada pasa a Gemini/NVIDIA) y UN
    reintento propio, corto, solo para 429/5xx/529 (sobrecarga pasajera). Un
    SEMÁFORO limita las llamadas de IA simultáneas (AI_MAX_CONCURRENCY, 4); si
    no hay cupo en AI_BUSY_WAIT_S (20 s) se lanza AIBusyError ("IA ocupada /
    AI busy") y el caller devuelve su error normal en vez de colgar un hilo más.
  · Cupo RESERVADO para el usuario (revisión 2026-09-30): el trabajo de fondo
    (hilos sin petición HTTP: research, comité, ciclo de agentes, agente de
    trading…) solo puede ocupar AI_MAX_CONCURRENCY − AI_INTERACTIVE_RESERVE
    cupos (4 − 1 = 3). Así una tanda de investigaciones automáticas no deja a
    Khipu (voz/texto) respondiendo "IA ocupada". Un hilo se considera de fondo
    si no tiene contexto de petición de Flask; `ai_background()` lo fuerza.
    Los pings del 🩺 (max_tokens ≤ 4) no piden cupo: un diagnóstico no debe
    informar "falla" solo porque la IA está ocupada.
  · #13 fugas de secretos: la key de Gemini viaja en la cabecera
    x-goog-api-key (antes en la URL ?key=, y la URL acababa dentro del texto de
    las excepciones de requests); los errores de proveedor se redactan con
    core.http.redact_secrets antes de salir de aquí.
"""
import json
import logging
import os
import re
import threading
import time
from contextlib import contextmanager

import requests

from core.config import (AI_MODEL_DEEP, AI_MODEL_FAST, AI_ORDER, CLAUDE,
                         GEMINI_KEY, GEMINI_MODEL, NVIDIA_KEY, NVIDIA_MODEL)

log = logging.getLogger(__name__)


def _env_num(name, default, lo, hi, cast=float):
    try:
        v = cast(os.getenv(name, default))
    except (TypeError, ValueError):
        v = cast(default)
    return max(lo, min(hi, v))


# ── Límite de concurrencia de IA (auditoría #2) ─────────────────────────────
AI_MAX_CONCURRENCY = _env_num('AI_MAX_CONCURRENCY', 4, 1, 32, int)
AI_BUSY_WAIT_S = _env_num('AI_BUSY_WAIT_S', 20, 1, 120)
CLAUDE_TIMEOUT_FAST_S = _env_num('AI_CLAUDE_TIMEOUT_S', 60, 5, 600)
CLAUDE_TIMEOUT_DEEP_S = _env_num('AI_CLAUDE_TIMEOUT_DEEP_S', 110, 5, 600)
# cupos que el trabajo de fondo NUNCA puede ocupar (quedan para el usuario)
AI_INTERACTIVE_RESERVE = _env_num('AI_INTERACTIVE_RESERVE', 1, 0, 16, int)
AI_PING_MAX_TOKENS = 4      # llamadas de ≤ 4 tokens = ping de diagnóstico → sin cupo
CLAUDE_RETRY_SLEEP_S = 1.0  # espera antes del único reintento por 429/5xx/529
_AI_SEM = threading.BoundedSemaphore(AI_MAX_CONCURRENCY)
_AI_BG_SEM = threading.BoundedSemaphore(max(1, AI_MAX_CONCURRENCY - AI_INTERACTIVE_RESERVE))
_AI_TLS = threading.local()


class AIBusyError(RuntimeError):
    """Demasiadas llamadas de IA simultáneas: se rechaza en vez de colgar un hilo."""

    def __init__(self, msg=None):
        super().__init__(msg or 'IA ocupada: demasiadas consultas a la vez, reintenta en unos segundos '
                                '/ AI busy: too many concurrent requests, retry in a few seconds')


def _is_background():
    """¿Este hilo es trabajo de FONDO? `ai_background()` manda; si no, un hilo
    sin contexto de petición de Flask (research, comité, ciclo de agentes,
    agente de trading, warmers) es de fondo y una petición HTTP es interactiva."""
    forced = getattr(_AI_TLS, 'background', None)
    if forced is not None:
        return bool(forced)
    try:
        from flask import has_request_context
        return not has_request_context()
    except Exception:  # noqa: BLE001 — sin Flask: se trata como interactivo
        return False


@contextmanager
def ai_background(flag=True):
    """Marca explícitamente las llamadas de IA de este hilo como de fondo
    (flag=True) o interactivas (flag=False), p. ej. un hilo que atiende a un
    usuario que espera la respuesta."""
    prev = getattr(_AI_TLS, 'background', None)
    _AI_TLS.background = flag
    try:
        yield
    finally:
        _AI_TLS.background = prev


@contextmanager
def _ai_slot(max_tokens=None):
    """Ocupa un cupo del semáforo de IA. REENTRANTE por hilo: la cascada
    (_ai_complete_raw) toma el cupo una vez y los proveedores que llama no
    vuelven a pedirlo; research/llm.py y el 🩺 llaman a los proveedores directo
    y así también quedan limitados. El trabajo de fondo pasa ANTES por
    _AI_BG_SEM (más chico) → nunca ocupa los AI_INTERACTIVE_RESERVE cupos del
    usuario. max_tokens ≤ AI_PING_MAX_TOKENS (ping del 🩺) → sin cupo."""
    depth = getattr(_AI_TLS, 'depth', 0)
    if depth > 0 or (max_tokens is not None and _small(max_tokens)):
        _AI_TLS.depth = depth + 1
        try:
            yield
        finally:
            _AI_TLS.depth -= 1
        return
    sem = _AI_SEM
    bg_sem = _AI_BG_SEM if _is_background() else None   # se libera EL MISMO que se tomó
    t0 = time.monotonic()
    if bg_sem is not None and not bg_sem.acquire(timeout=AI_BUSY_WAIT_S):
        log.warning('IA ocupada (fondo): cupos de fondo llenos tras %.0f s', AI_BUSY_WAIT_S)
        raise AIBusyError()
    left = max(0.05, AI_BUSY_WAIT_S - (time.monotonic() - t0))
    if not sem.acquire(timeout=left):
        if bg_sem is not None:
            bg_sem.release()
        log.warning('IA ocupada: %d llamadas en curso, se rechaza una más tras %.0f s',
                    AI_MAX_CONCURRENCY, AI_BUSY_WAIT_S)
        raise AIBusyError()
    _AI_TLS.depth = 1
    try:
        yield
    finally:
        _AI_TLS.depth = 0
        sem.release()
        if bg_sem is not None:
            bg_sem.release()


def _small(max_tokens):
    try:
        return int(max_tokens) <= AI_PING_MAX_TOKENS
    except (TypeError, ValueError):
        return False


def _redact(e, limit=160):
    """Texto de error SIN secretos (valores de env + patrones key=/Bearer/…)."""
    try:
        from core.http import redact_secrets
        return redact_secrets(e, extra=(CLAUDE, GEMINI_KEY, NVIDIA_KEY), limit=limit)
    except Exception:  # noqa: BLE001 — nunca romper el camino de error
        return type(e).__name__ if isinstance(e, BaseException) else '(error)'


def _usage():
    from core import ai_usage
    return ai_usage


def _complete_claude(system, prompt, max_tokens, tier='fast', model=None):
    _usage().check('claude', max_tokens)          # límite de gasto: no se llama (ni se cobra)
    with _ai_slot(max_tokens):
        return _complete_claude_inner(system, prompt, max_tokens, tier, model)


def _complete_claude_inner(system, prompt, max_tokens, tier='fast', model=None):
    import anthropic
    # timeout corto y SIN reintentos del SDK (el default: 10 min y 2 reintentos →
    # un hilo de gunicorn podía quedar atado media hora a una llamada colgada; y
    # el SDK también reintenta los TIMEOUTS, lo que duplicaba el cuelgue). Solo
    # 429/5xx/529 se reintentan UNA vez, aquí abajo, tras CLAUDE_RETRY_SLEEP_S.
    client = anthropic.Anthropic(api_key=CLAUDE, max_retries=0,
                                 timeout=CLAUDE_TIMEOUT_DEEP_S if tier == 'deep' else CLAUDE_TIMEOUT_FAST_S)
    _net_errors = tuple(c for c in (getattr(anthropic, 'APITimeoutError', None),
                                    getattr(anthropic, 'APIConnectionError', None)) if c)
    _status_error = getattr(anthropic, 'APIStatusError', None)

    def _transient(e):
        # sobrecarga/límite pasajero: 408/409/429 o 5xx (incluye 529 overloaded)
        if not (_status_error and isinstance(e, _status_error)):
            return False
        code = getattr(e, 'status_code', None) or getattr(getattr(e, 'response', None), 'status_code', 0) or 0
        return code in (408, 409, 429) or code >= 500

    def _create(**kw):
        t0 = time.monotonic()
        try:
            msg = client.messages.create(**kw)
        except Exception as e:  # noqa: BLE001
            if not _transient(e):
                raise
            time.sleep(CLAUDE_RETRY_SLEEP_S)
            msg = client.messages.create(**kw)     # un solo reintento; si falla, sale
        try:   # gasto: tokens REALES que reporta Anthropic (incluida la caché)
            u = getattr(msg, 'usage', None)
            tin = (getattr(u, 'input_tokens', 0) or 0) + (getattr(u, 'cache_creation_input_tokens', 0) or 0) \
                + int((getattr(u, 'cache_read_input_tokens', 0) or 0) * 0.1)
            _usage().record('claude', getattr(msg, 'model', kw.get('model')), tin, getattr(u, 'output_tokens', 0) or 0,
                            ms=(time.monotonic() - t0) * 1000, estimated=u is None)
        except Exception:  # noqa: BLE001
            pass
        return msg
    # Híbrido: el tier elige el modelo (misma ANTHROPIC_KEY). `model` lo SOBRESCRIBE
    # para elegir el mejor modelo POR TAREA (p.ej. claude-opus-4-8 en la capa
    # proactiva, donde el juicio importa más que la latencia).
    tier_model = AI_MODEL_DEEP if tier == 'deep' else AI_MODEL_FAST
    base = dict(max_tokens=max_tokens, system=system or '',
                messages=[{'role': 'user', 'content': prompt or ''}])
    # Lista de modelos Claude a probar EN ORDEN. Si la key no tiene acceso al
    # modelo pedido, caemos a otro modelo Claude que SÍ funcione (haiku) — SIEMPRE
    # Claude antes de degradar a Gemini/NVIDIA. (Bug 2026-07-14: sonnet-5 fallaba
    # y la cascada usaba NVIDIA.)
    candidates = []
    for m in (model, tier_model, AI_MODEL_FAST, 'claude-haiku-4-5'):
        if m and m not in candidates:
            candidates.append(m)

    def _text_of(msg):
        # el primer bloque de texto NO vacío (salta bloques de "thinking")
        for block in msg.content:
            if getattr(block, 'type', None) == 'text' and (block.text or '').strip():
                return block.text
        return ''

    # CAUSA RAÍZ (2026-07-14): Sonnet 5 piensa por defecto; con presupuesto chico
    # el pensamiento consume TODO el max_tokens y el bloque de texto sale VACÍO →
    # la cascada lo tomaba como "sin respuesta" y usaba NVIDIA. Por modelo:
    #  intento 1 → desactivar el pensamiento (budget normal, respuesta directa);
    #  intento 2 → sin ese kwarg (por si el SDK es viejo) pero con MUCHO más
    #              presupuesto, para que quepan pensamiento + respuesta.
    last_err = None
    for m in candidates:
        attempts = [
            ({'thinking': {'type': 'disabled'}}, max_tokens),
            ({}, max(int(max_tokens) * 4, 6000)),
        ]
        for extra, mt in attempts:
            try:
                msg = _create(
                    model=m, max_tokens=mt, system=base['system'],
                    messages=base['messages'], **extra)
            except TypeError:
                continue           # SDK no conoce `thinking` → intento sin él
            except Exception as e:  # noqa: BLE001 — error de API con este modelo
                if _net_errors and isinstance(e, _net_errors):
                    # timeout / red caída: probar OTRO modelo Claude no ayuda y
                    # ataría el hilo N veces más → pasa directo a Gemini/NVIDIA.
                    raise RuntimeError(f'{type(e).__name__}: ' + _redact(e, 120)) from None
                last_err = e
                break              # prueba el siguiente modelo Claude
            text = _text_of(msg)
            if text.strip():
                return text, msg.model
            # texto vacío (el pensamiento se comió el budget) → siguiente intento
    if last_err is not None:
        raise RuntimeError(_redact(last_err, 160)) from None
    raise RuntimeError('claude: sin texto de ningún modelo')


def _complete_gemini(system, prompt, max_tokens, tier='fast', json_mode=False):
    _usage().check('gemini', max_tokens)
    with _ai_slot(max_tokens):
        return _complete_gemini_inner(system, prompt, max_tokens, tier, json_mode)


def _gemini_post(url, body, timeout):
    """POST a Gemini con la key en la CABECERA x-goog-api-key (nunca en la URL:
    la URL termina dentro del texto de las excepciones de requests → logs/🩺)."""
    try:
        return requests.post(url, json=body, timeout=timeout,
                             headers={'x-goog-api-key': GEMINI_KEY, 'Content-Type': 'application/json'})
    except requests.exceptions.Timeout:
        raise RuntimeError('Gemini timeout') from None
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f'Gemini red ({type(e).__name__})') from None


def _complete_gemini_inner(system, prompt, max_tokens, tier='fast', json_mode=False):  # noqa: ARG001 — tier no aplica
    """json_mode (lo usa research/): pide JSON estricto (responseMimeType), da
    más presupuesto y apaga el "pensamiento" en modelos flash — en 2.5 el
    pensamiento consume maxOutputTokens y cortaba el JSON a la mitad
    ("Unterminated string", visto en prod 2026-09-28)."""
    gen = {'maxOutputTokens': max_tokens, 'temperature': 0.6}
    if json_mode:
        gen.update({'responseMimeType': 'application/json', 'temperature': 0.3,
                    'maxOutputTokens': max(max_tokens, 8192)})
        if 'flash' in GEMINI_MODEL:
            gen['thinkingConfig'] = {'thinkingBudget': 0}
    body = {'contents': [{'parts': [{'text': (system + '\n\n' + prompt) if system else prompt}]}],
            'generationConfig': gen}
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent'
    r = _gemini_post(url, body, 90 if json_mode else 45)
    if r.status_code == 400 and 'thinkingConfig' in gen:
        gen.pop('thinkingConfig')            # modelo que no acepta apagar el pensamiento
        r = _gemini_post(url, body, 90)
    if not r.ok:
        # solo el código + el estado simbólico de Google (NOT_FOUND, PERMISSION_DENIED…):
        # nada del cuerpo libre, que podría repetir datos de la petición.
        st = ''
        try:
            st = str(((r.json() or {}).get('error') or {}).get('status') or '')
        except Exception:  # noqa: BLE001
            st = ''
        st = st if re.fullmatch(r'[A-Z_]{3,40}', st or '') else ''
        raise RuntimeError(f'Gemini HTTP {r.status_code}' + (f' {st}' if st else ''))
    data = r.json() or {}
    try:   # gasto: usageMetadata de Google (el "pensamiento" se cobra como salida)
        um = data.get('usageMetadata') or {}
        _usage().record('gemini', GEMINI_MODEL, um.get('promptTokenCount') or _usage().estimate_tokens(body['contents'][0]['parts'][0]['text']),
                        (um.get('candidatesTokenCount') or 0) + (um.get('thoughtsTokenCount') or 0),
                        estimated=not um)
    except Exception:  # noqa: BLE001
        pass
    cands = data.get('candidates') or []
    if not cands:
        raise RuntimeError('Gemini sin candidates')
    parts = cands[0].get('content', {}).get('parts', [])
    text = ''.join(p.get('text', '') for p in parts if not p.get('thought'))
    if json_mode and cands[0].get('finishReason') == 'MAX_TOKENS':
        raise RuntimeError('Gemini cortó la respuesta (MAX_TOKENS)')
    return text, 'gemini:' + GEMINI_MODEL


def _complete_nvidia(system, prompt, max_tokens, tier='fast'):
    _usage().check('nvidia', max_tokens)
    with _ai_slot(max_tokens):
        return _complete_nvidia_inner(system, prompt, max_tokens, tier)


def _complete_nvidia_inner(system, prompt, max_tokens, tier='fast'):  # noqa: ARG001 — tier no aplica
    # modelos de razonamiento gastan tokens "pensando": más margen para que quepa la respuesta
    body = {'model': NVIDIA_MODEL, 'max_tokens': max(int(max_tokens) * 2, 2048) if int(max_tokens) > 4 else max_tokens,
            'temperature': 0.6,
            'messages': [{'role': 'system', 'content': system or ''},
                         {'role': 'user', 'content': prompt or ''}]}
    try:
        r = requests.post('https://integrate.api.nvidia.com/v1/chat/completions',
                          headers={'Authorization': f'Bearer {NVIDIA_KEY}', 'Accept': 'application/json'},
                          json=body, timeout=45)
    except requests.exceptions.Timeout:
        raise RuntimeError('NVIDIA timeout') from None
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f'NVIDIA red ({type(e).__name__})') from None
    if not r.ok:
        raise RuntimeError(f'NVIDIA HTTP {r.status_code}')
    data = r.json()
    try:
        u = data.get('usage') or {}
        _usage().record('nvidia', NVIDIA_MODEL, u.get('prompt_tokens') or _usage().estimate_tokens((system or '') + (prompt or '')),
                        u.get('completion_tokens') or 0, estimated=not u)
    except Exception:  # noqa: BLE001
        pass
    return (data['choices'][0]['message']['content']), 'nvidia:' + NVIDIA_MODEL


_AI_PROVIDERS = {
    'claude': (lambda: bool(CLAUDE), _complete_claude),
    'gemini': (lambda: bool(GEMINI_KEY), _complete_gemini),
    'nvidia': (lambda: bool(NVIDIA_KEY), _complete_nvidia),
}


def _ai_configured():
    return any(cfg() for cfg, _ in _AI_PROVIDERS.values())


def _ai_complete(system, prompt, max_tokens=1000, tier='fast', model=None, verify_numbers=True):
    """Llamada de IA con GUARDIÁN DE CIFRAS (2026-09-28, pedido explícito:
    "necesito que todo esté en vivo; los datos falsos perjudican la tesis").
    Toda cifra de dinero de la respuesta debe estar en el input (system+prompt);
    si no: 1 reintento con el error como feedback y, si persiste, la cifra se
    MARCA "(⚠ cifra no verificada)". verify_numbers=False solo para diagnóstico."""
    if not verify_numbers:
        return _ai_complete_raw(system, prompt, max_tokens, tier, model)
    from core.live_facts import live_facts_block
    from core.numbers import NUMBERS_RULE, mark_unsupported, unsupported_in
    prompt = (prompt or '') + live_facts_block(prompt)   # cifras CORRECTAS, en vivo
    source = f'{system or ""}\n{prompt or ""}'
    sys2 = (system or '') + NUMBERS_RULE
    text, used = _ai_complete_raw(sys2, prompt, max_tokens, tier, model)
    bad = unsupported_in(text, source)
    if bad:
        log.warning('guardián de cifras: %s sin respaldo → reintento', bad)
        try:
            fb = (prompt + '\n\nTU RESPUESTA ANTERIOR USÓ CIFRAS QUE NO ESTÁN EN LOS DATOS: ' + ', '.join(bad) +
                  '. Reescribe la respuesta completa (mismo formato) usando SOLO cifras de los datos dados, '
                  'o sin esas cifras.')
            text2, used2 = _ai_complete_raw(sys2, fb, max_tokens, tier, model)
            bad2 = unsupported_in(text2, source)
            if len(bad2) <= len(bad):
                text, used, bad = text2, used2, bad2
        except Exception as e:  # noqa: BLE001
            log.warning('guardián de cifras: reintento falló (%s)', str(e)[:80])
        text = mark_unsupported(text, bad)
    return text, used


def _ai_complete_raw(system, prompt, max_tokens=1000, tier='fast', model=None):
    """Intenta cada proveedor configurado en orden (AI_ORDER); si uno falla,
    pasa al siguiente. Devuelve (texto, etiqueta_modelo).

    tier: 'fast' (AI_MODEL_FAST/Haiku) o 'deep' (AI_MODEL_DEEP/Sonnet 5).
    model: sobrescribe el modelo de Claude para elegir el mejor POR TAREA
    (p.ej. 'claude-opus-4-8'); solo aplica al proveedor Claude."""
    tier = 'deep' if tier == 'deep' else 'fast'
    # "Sonnet 5 para TODO" (pedido del usuario): Claude SIEMPRE primero cuando la
    # key existe; Gemini/NVIDIA quedan solo de respaldo si Claude cae. Esto
    # neutraliza una variable AI_ORDER vieja en Railway (gemini,nvidia,claude)
    # que hacía que la sim usara NVIDIA aunque Sonnet 5 funcionaba. (2026-07-14)
    order = list(AI_ORDER)
    if CLAUDE:
        order = ['claude'] + [n for n in order if n != 'claude']
    errors = []
    # UN cupo del semáforo para toda la cascada (los proveedores son reentrantes):
    # si no hay cupo, AIBusyError sale tal cual — probar el siguiente proveedor
    # esperaría otra vez y ataría el hilo el triple.
    with _ai_slot():
        for name in order:
            prov = _AI_PROVIDERS.get(name)
            if not prov or not prov[0]():
                continue
            try:
                if name == 'claude':
                    text, used = prov[1](system, prompt, max_tokens, tier, model=model)
                else:
                    text, used = prov[1](system, prompt, max_tokens, tier)
                text = strip_reasoning(text)
                if text and text.strip():
                    return text, used
                errors.append(f'{name}: respuesta vacía')
            except AIBusyError:
                raise
            except Exception as e:  # noqa: BLE001
                if type(e).__name__ == 'AIBudgetError' and getattr(e, 'scope', None) != 'provider':
                    raise              # límite de gasto: los demás proveedores tampoco deben gastar
                errors.append(f'{name}: {_redact(e, 100)}')
    raise RuntimeError('Ningún proveedor de IA respondió. ' + ('; '.join(errors) or 'sin keys configuradas'))


# Compat: las features existentes llaman _claude_complete → ahora multi-proveedor.
def _claude_complete(system, prompt, max_tokens, tier='fast'):
    return _ai_complete(system, prompt, max_tokens, tier)


_THINK_RX = re.compile(r'<(think|thinking|reasoning)>.*?</\1>', re.S | re.I)


def strip_reasoning(text):
    """Quita el "razonamiento oculto" que algunos modelos (NVIDIA/DeepSeek, Qwen…)
    escriben en <think>…</think>. Si el bloque quedó sin cerrar (se acabaron los
    tokens pensando), no hay respuesta útil → ''. (2026-10-03: el chat mostraba
    respuestas cortadas a la mitad por esto.)"""
    t = str(text or '')
    t = _THINK_RX.sub('', t)
    m = re.search(r'<(think|thinking|reasoning)>', t, re.I)
    if m:
        t = t[:m.start()]
    if re.search(r'</(think|thinking|reasoning)>', t, re.I):
        t = re.split(r'</(?:think|thinking|reasoning)>', t, flags=re.I)[-1]
    return t.strip()


def _extract_json(text):
    """Extrae un objeto JSON de la respuesta del modelo aunque venga con fences
    markdown o rodeado de texto explicativo (Gemini/NVIDIA a veces lo hacen).
    Devuelve el dict/list ya parseado o lanza json.JSONDecodeError."""
    raw = (text or '').strip()
    # 1) quitar fences ```json … ```
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # 2) recortar del primer { (o [) al último } (o ]) correspondiente
    for open_c, close_c in (('{', '}'), ('[', ']')):
        i, j = cleaned.find(open_c), cleaned.rfind(close_c)
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(cleaned[i:j + 1])
            except json.JSONDecodeError:
                continue
    # 3) primer objeto JSON válido aunque le siga texto ("Extra data")
    dec = json.JSONDecoder()
    for m in re.finditer(r'[{\[]', cleaned):
        try:
            return dec.raw_decode(cleaned[m.start():])[0]
        except json.JSONDecodeError:
            continue
    # 4) sin remedio → propagar el error para que el caller lo maneje
    return json.loads(cleaned)
