"""core/ai.py — cascada multi-proveedor de IA (Claude → Gemini → NVIDIA).

Compartida por las rutas del server, los agentes de la ontología y (próximo)
el motor de matrices. Un solo lugar para proveedores, orden y parsing.
"""
import json
import re

import requests

from core.config import (AI_MODEL_DEEP, AI_MODEL_FAST, AI_ORDER, CLAUDE,
                         GEMINI_KEY, GEMINI_MODEL, NVIDIA_KEY, NVIDIA_MODEL)


def _complete_claude(system, prompt, max_tokens, tier='fast', model=None):
    import anthropic
    client = anthropic.Anthropic(api_key=CLAUDE)
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
                msg = client.messages.create(
                    model=m, max_tokens=mt, system=base['system'],
                    messages=base['messages'], **extra)
            except TypeError:
                continue           # SDK no conoce `thinking` → intento sin él
            except Exception as e:  # noqa: BLE001 — error de API con este modelo
                last_err = e
                break              # prueba el siguiente modelo Claude
            text = _text_of(msg)
            if text.strip():
                return text, msg.model
            # texto vacío (el pensamiento se comió el budget) → siguiente intento
    raise last_err or RuntimeError('claude: sin texto de ningún modelo')


def _complete_gemini(system, prompt, max_tokens, tier='fast'):  # noqa: ARG001 — tier no aplica
    body = {'contents': [{'parts': [{'text': (system + '\n\n' + prompt) if system else prompt}]}],
            'generationConfig': {'maxOutputTokens': max_tokens, 'temperature': 0.6}}
    r = requests.post(
        f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}',
        json=body, timeout=45)
    if not r.ok:
        raise RuntimeError(f'Gemini HTTP {r.status_code}')
    cands = (r.json() or {}).get('candidates') or []
    if not cands:
        raise RuntimeError('Gemini sin candidates')
    text = ''.join(p.get('text', '') for p in cands[0].get('content', {}).get('parts', []))
    return text, 'gemini:' + GEMINI_MODEL


def _complete_nvidia(system, prompt, max_tokens, tier='fast'):  # noqa: ARG001 — tier no aplica
    body = {'model': NVIDIA_MODEL, 'max_tokens': max_tokens, 'temperature': 0.6,
            'messages': [{'role': 'system', 'content': system or ''},
                         {'role': 'user', 'content': prompt or ''}]}
    r = requests.post('https://integrate.api.nvidia.com/v1/chat/completions',
                      headers={'Authorization': f'Bearer {NVIDIA_KEY}', 'Accept': 'application/json'},
                      json=body, timeout=45)
    if not r.ok:
        raise RuntimeError(f'NVIDIA HTTP {r.status_code}')
    return (r.json()['choices'][0]['message']['content']), 'nvidia:' + NVIDIA_MODEL


_AI_PROVIDERS = {
    'claude': (lambda: bool(CLAUDE), _complete_claude),
    'gemini': (lambda: bool(GEMINI_KEY), _complete_gemini),
    'nvidia': (lambda: bool(NVIDIA_KEY), _complete_nvidia),
}


def _ai_configured():
    return any(cfg() for cfg, _ in _AI_PROVIDERS.values())


def _ai_complete(system, prompt, max_tokens=1000, tier='fast', model=None):
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
    for name in order:
        prov = _AI_PROVIDERS.get(name)
        if not prov or not prov[0]():
            continue
        try:
            if name == 'claude':
                text, used = prov[1](system, prompt, max_tokens, tier, model=model)
            else:
                text, used = prov[1](system, prompt, max_tokens, tier)
            if text and text.strip():
                return text, used
            errors.append(f'{name}: respuesta vacía')
        except Exception as e:  # noqa: BLE001
            errors.append(f'{name}: {str(e)[:80]}')
    raise RuntimeError('Ningún proveedor de IA respondió. ' + ('; '.join(errors) or 'sin keys configuradas'))


# Compat: las features existentes llaman _claude_complete → ahora multi-proveedor.
def _claude_complete(system, prompt, max_tokens, tier='fast'):
    return _ai_complete(system, prompt, max_tokens, tier)


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
    # 3) sin remedio → propagar el error para que el caller lo maneje
    return json.loads(cleaned)
