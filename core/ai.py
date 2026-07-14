"""core/ai.py — cascada multi-proveedor de IA (Claude → Gemini → NVIDIA).

Compartida por las rutas del server, los agentes de la ontología y (próximo)
el motor de matrices. Un solo lugar para proveedores, orden y parsing.
"""
import json
import re

import requests

from core.config import (AI_MODEL_DEEP, AI_MODEL_FAST, AI_ORDER, CLAUDE,
                         GEMINI_KEY, GEMINI_MODEL, NVIDIA_KEY, NVIDIA_MODEL)


def _complete_claude(system, prompt, max_tokens, tier='fast'):
    import anthropic
    client = anthropic.Anthropic(api_key=CLAUDE)
    # Híbrido: el tier SOLO cambia el modelo de Claude (misma ANTHROPIC_KEY).
    model = AI_MODEL_DEEP if tier == 'deep' else AI_MODEL_FAST
    # Sonnet 5 activa el "pensamiento adaptativo" por defecto: consumiría parte
    # del presupuesto de max_tokens razonando (respuesta más lenta y, con budgets
    # pequeños, riesgo de truncar el texto/JSON). La app se diseñó para respuestas
    # inmediatas y deterministas, así que lo desactivamos. `thinking` es un kwarg
    # de los SDK recientes; si uno viejo no lo conoce, reintentamos sin él.
    kwargs = dict(model=model, max_tokens=max_tokens, system=system or '',
                  messages=[{'role': 'user', 'content': prompt or ''}])
    try:
        msg = client.messages.create(thinking={'type': 'disabled'}, **kwargs)
    except TypeError:
        msg = client.messages.create(**kwargs)
    text = ''
    for block in msg.content:
        if getattr(block, 'type', None) == 'text':
            text = block.text
            break
    return text, msg.model


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


def _ai_complete(system, prompt, max_tokens=1000, tier='fast'):
    """Intenta cada proveedor configurado en orden (AI_ORDER); si uno falla,
    pasa al siguiente. Devuelve (texto, etiqueta_modelo).

    tier: 'fast' (default, AI_MODEL_FAST/Haiku) o 'deep' (AI_MODEL_DEEP/Sonnet 5).
    SOLO cambia el modelo del proveedor Claude; Gemini/NVIDIA quedan igual."""
    tier = 'deep' if tier == 'deep' else 'fast'
    errors = []
    for name in AI_ORDER:
        prov = _AI_PROVIDERS.get(name)
        if not prov or not prov[0]():
            continue
        try:
            text, model = prov[1](system, prompt, max_tokens, tier)
            if text and text.strip():
                return text, model
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
