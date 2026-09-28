"""research/llm.py — abstracción de proveedor de modelos (no acoplada a nadie).

LLMProvider: generate() / structured_generate() / tool_call() (reservado).
Los proveedores reales envuelven las funciones de core/ai.py (Claude, Gemini,
NVIDIA) de a UNO — la cascada la hace el Router aquí, no un proveedor.

Routing por agente vía entorno (docs/MODEL_ROUTING.md):
  RESEARCH_MODEL_<AGENTTYPE>=claude:claude-sonnet-5,gemini,nvidia
  RESEARCH_MODEL_DEFAULT=claude:deep,gemini,nvidia
Formato de cada paso: <proveedor>[:<modelo|deep|fast>]. El primer paso que
responde gana; los siguientes son fallback.
"""
import json
import os
import time

from pydantic import ValidationError

from core.ai import _extract_json

# precio aproximado USD por 1M tokens (entrada, salida) — SOLO para el
# control de presupuesto; se rotula "estimado" en la UI.
_PRICE = {
    'claude-sonnet': (3.0, 15.0), 'claude-haiku': (1.0, 5.0), 'claude-opus': (15.0, 75.0),
    'claude': (3.0, 15.0), 'gemini': (0.3, 2.5), 'nvidia': (0.0, 0.0), 'fake': (0.0, 0.0),
}


def estimate_tokens(text):
    return max(1, len(text or '') // 4)


def estimate_cost(model_label, tokens_in, tokens_out):
    ml = (model_label or '').lower()
    key = next((k for k in ('claude-opus', 'claude-sonnet', 'claude-haiku', 'claude', 'gemini', 'nvidia', 'fake')
                if k in ml), 'claude')
    pin, pout = _PRICE[key]
    return round((tokens_in * pin + tokens_out * pout) / 1e6, 6)


class LLMError(RuntimeError):
    pass


class LLMProvider:
    name = 'base'

    def available(self):
        return False

    def generate(self, system, prompt, max_tokens=1500):
        """-> (texto, etiqueta_modelo)"""
        raise NotImplementedError

    def structured_generate(self, system, prompt, schema_model, max_tokens=2500,
                            max_attempts=2, extra_check=None):
        """Genera y VALIDA contra un modelo Pydantic. Reintenta con el error como
        feedback; si sigue mal, levanta LLMError (nunca devuelve JSON inválido).
        Devuelve (objeto_validado, meta{model, attempts, repaired, tokens_in, tokens_out})."""
        meta = {'attempts': 0, 'repaired': False, 'tokens_in': 0, 'tokens_out': 0, 'model': None,
                'errors': []}
        feedback = ''
        for attempt in range(1, max_attempts + 1):
            meta['attempts'] = attempt
            p = prompt + (feedback and ('\n\nTU RESPUESTA ANTERIOR NO ES VÁLIDA:\n' + feedback +
                                        '\nDevuelve SOLO el JSON corregido.'))
            text, model = self.generate(system, p, max_tokens)
            meta['model'] = model
            meta['tokens_in'] += estimate_tokens(system) + estimate_tokens(p)
            meta['tokens_out'] += estimate_tokens(text)
            try:
                data = _extract_json(text)
                obj = schema_model.model_validate(data)
                errs = extra_check(obj) if extra_check else []
                if errs:
                    raise ValueError('; '.join(errs))
                meta['repaired'] = attempt > 1
                return obj, meta
            except (ValidationError, ValueError, json.JSONDecodeError, TypeError) as e:
                feedback = str(e)[:1500]
                meta['errors'].append(feedback[:300])
        raise LLMError('salida inválida tras %d intentos: %s' % (meta['attempts'], feedback[:300]))

    def tool_call(self, *a, **k):   # reservado (Phase 2+: herramientas nativas)
        raise NotImplementedError


class CoreProvider(LLMProvider):
    """Un proveedor de core/ai.py (claude|gemini|nvidia), sin cascada interna."""

    def __init__(self, provider, model=None):
        self.provider = provider
        self.model = model   # 'deep' | 'fast' | id de modelo (solo Claude)
        self.name = provider + (':' + model if model else '')

    def available(self):
        from core import ai
        prov = ai._AI_PROVIDERS.get(self.provider)
        return bool(prov and prov[0]())

    def generate(self, system, prompt, max_tokens=1500):
        from core import ai
        prov = ai._AI_PROVIDERS.get(self.provider)
        if not prov or not prov[0]():
            raise LLMError(f'{self.provider} sin clave')
        if self.provider == 'claude':
            tier = 'deep' if self.model in (None, 'deep') else 'fast'
            model = self.model if self.model not in (None, 'deep', 'fast') else None
            text, used = prov[1](system, prompt, max_tokens, tier, model=model)
        else:
            text, used = prov[1](system, prompt, max_tokens, 'deep')
        if not text or not text.strip():
            raise LLMError(f'{self.provider}: respuesta vacía')
        return text, used


class FakeProvider(LLMProvider):
    """Para tests: devuelve respuestas guionadas (texto o callable(prompt))."""
    name = 'fake'

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def available(self):
        return True

    def generate(self, system, prompt, max_tokens=1500):
        self.calls.append(prompt)
        if not self.responses:
            raise LLMError('fake: sin respuestas')
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return (r(prompt) if callable(r) else r), 'fake-model'


def _parse_route(spec):
    out = []
    for step in (spec or '').split(','):
        step = step.strip()
        if not step:
            continue
        prov, _, model = step.partition(':')
        out.append(CoreProvider(prov.strip().lower(), model.strip() or None))
    return out


DEFAULT_ROUTE = 'claude:deep,gemini,nvidia'


def route_for(agent_type):
    spec = (os.getenv('RESEARCH_MODEL_' + agent_type.upper())
            or os.getenv('RESEARCH_MODEL_DEFAULT') or DEFAULT_ROUTE)
    return _parse_route(spec)


class RoutedProvider(LLMProvider):
    """Cascada de proveedores para UN agente: si uno falla (red, clave, modelo
    retirado o salida inválida tras reintentos) pasa al siguiente."""

    def __init__(self, providers):
        self.providers = [p for p in providers if p]
        self.name = '>'.join(p.name for p in self.providers) or 'none'
        self.fallbacks = []

    def available(self):
        return any(p.available() for p in self.providers)

    def generate(self, system, prompt, max_tokens=1500):
        errs = []
        for p in self.providers:
            if not p.available():
                continue
            try:
                return p.generate(system, prompt, max_tokens)
            except Exception as e:  # noqa: BLE001
                errs.append(f'{p.name}: {str(e)[:120]}')
                self.fallbacks.append(p.name)
        raise LLMError('ningún proveedor respondió: ' + '; '.join(errs or ['sin proveedores configurados']))

    def structured_generate(self, system, prompt, schema_model, max_tokens=2500,
                            max_attempts=2, extra_check=None):
        errs = []
        t0 = time.time()
        for p in self.providers:
            if not p.available():
                continue
            try:
                obj, meta = p.structured_generate(system, prompt, schema_model, max_tokens,
                                                  max_attempts, extra_check)
                meta['provider'] = p.name
                meta['fallbacks'] = list(self.fallbacks)
                meta['seconds'] = round(time.time() - t0, 2)
                return obj, meta
            except Exception as e:  # noqa: BLE001
                errs.append(f'{p.name}: {str(e)[:200]}')
                self.fallbacks.append(p.name)
        raise LLMError('; '.join(errs) or 'sin proveedores configurados')
