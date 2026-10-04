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
import random
import time

from pydantic import ValidationError

from core.ai import AIBusyError, _extract_json

# R2 (misión de reparación 2026-10-04): "IA ocupada" (AIBusyError) es escasez
# GLOBAL de cupos del semáforo, no un fallo del proveedor → cambiar de
# proveedor no ayuda y triplica la espera (3 × AI_BUSY_WAIT_S = 60 s en prod,
# exactamente la latencia de los agentes caídos de TSMC). Ahora se espera con
# backoff + jitter y se reintenta el MISMO proveedor; agotados los reintentos
# el agente falla con un motivo claro y NO prueba el siguiente proveedor.
BUSY_BACKOFF_S = (3.0, 6.0, 12.0, 24.0)
BUSY_JITTER = 0.3


def _busy_retries():
    try:
        return max(0, min(8, int(os.getenv('RESEARCH_BUSY_RETRIES', '4'))))
    except (TypeError, ValueError):
        return 4


def _busy_wait_s(i):
    base = BUSY_BACKOFF_S[min(i, len(BUSY_BACKOFF_S) - 1)]
    return base * (1.0 + random.uniform(-BUSY_JITTER, BUSY_JITTER))


def _sleep(seconds):          # inyectable en tests
    time.sleep(seconds)


class _BusyExhausted(Exception):
    pass

def estimate_tokens(text):
    return max(1, len(text or '') // 4)


def estimate_cost(model_label, tokens_in, tokens_out):
    """USD estimados. R5: UNA sola tabla de precios para todo (core.ai_usage.PRICES
    + AI_PRICES_JSON): antes research tenía la suya (claude-sonnet 3/15 vs 2/10)
    y "presupuesto research" y "💰 Gasto IA" no cuadraban. 'fake' (tests) = $0."""
    ml = (model_label or '').lower()
    if not ml or ml.startswith('fake'):
        return 0.0
    from core.ai_usage import cost_of
    provider = 'gemini' if ml.startswith('gemini') else 'nvidia' if ml.startswith('nvidia') \
        else 'typesafe' if ml.startswith('typesafe') else 'claude'
    return round(cost_of(provider, ml, tokens_in or 0, tokens_out or 0), 6)


class LLMError(RuntimeError):
    """`meta` (opcional): tokens ya gastados antes de fallar — el presupuesto los cuenta (R5)."""

    def __init__(self, msg, meta=None):
        super().__init__(msg)
        self.meta = meta


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
        raise LLMError('salida inválida tras %d intentos: %s' % (meta['attempts'], feedback[:300]), meta=meta)

    def tool_call(self, *a, **k):   # reservado (Phase 2+: herramientas nativas)
        raise NotImplementedError


class CoreProvider(LLMProvider):
    """Un proveedor de core/ai.py (claude|gemini|nvidia), sin cascada interna."""

    def __init__(self, provider, model=None):
        self.provider = provider
        self.model = model   # 'deep' | 'fast' | id de modelo (solo Claude)
        self.name = provider + (':' + model if model else '')

    def available(self):
        """Clave presente y SIN pausa activa (corta-circuito R1): un proveedor
        sin saldo / clave inválida / modelo retirado se salta sin tocar la red."""
        from core import ai
        return ai.provider_available(self.provider)

    def generate(self, system, prompt, max_tokens=1500):
        from core import ai
        prov = ai._AI_PROVIDERS.get(self.provider)
        if not prov or not prov[0]():
            raise LLMError(f'{self.provider} sin clave')
        paused = ai.circuit_open(self.provider)
        if paused:
            raise LLMError(f"{self.provider} en pausa hasta {paused['until_hhmm']} UTC ({paused['reason_es']}) / "
                           f"paused until {paused['until_hhmm']} UTC ({paused['reason_en']})")
        if self.provider == 'claude':
            tier = 'deep' if self.model in (None, 'deep') else 'fast'
            model = self.model if self.model not in (None, 'deep', 'fast') else None
            text, used = prov[1](system, prompt, max_tokens, tier, model=model)
        elif self.provider == 'gemini':
            text, used = prov[1](system, prompt, max_tokens, 'deep', json_mode=True)
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
        self.busy_retries = 0
        self.spent = {'tokens_in': 0, 'tokens_out': 0, 'attempts': 0, 'model': None}   # tokens de intentos fallidos

    def _note_spent(self, e):
        m = getattr(e, 'meta', None) or {}
        for k in ('tokens_in', 'tokens_out', 'attempts'):
            self.spent[k] += int(m.get(k) or 0)
        if m.get('model'):
            self.spent['model'] = m['model']

    def available(self):
        return any(p.available() for p in self.providers)

    def _with_busy_retry(self, fn):
        """Ejecuta fn(); ante AIBusyError espera (backoff + jitter) y reintenta el
        MISMO proveedor hasta RESEARCH_BUSY_RETRIES veces; agotado → _BusyExhausted."""
        i = 0
        while True:
            try:
                return fn()
            except AIBusyError:
                if i >= _busy_retries():
                    raise _BusyExhausted(i) from None
                w = _busy_wait_s(i)
                i += 1
                self.busy_retries += 1
                _sleep(w)

    @staticmethod
    def _busy_error(n):
        return LLMError(f'IA ocupada tras {n} esperas (cupos de IA llenos: comité/chat/otras investigaciones); '
                        f'se reintentará / AI busy after {n} waits (AI slots full); will be retried')

    def generate(self, system, prompt, max_tokens=1500):
        errs = []
        for p in self.providers:
            if not p.available():
                continue
            try:
                return self._with_busy_retry(lambda: p.generate(system, prompt, max_tokens))
            except _BusyExhausted as e:
                raise self._busy_error(e.args[0]) from None
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
                obj, meta = self._with_busy_retry(
                    lambda: p.structured_generate(system, prompt, schema_model, max_tokens, max_attempts, extra_check))
                meta['provider'] = p.name
                meta['fallbacks'] = list(self.fallbacks)
                meta['busy_retries'] = self.busy_retries
                meta['tokens_in'] = int(meta.get('tokens_in') or 0) + self.spent['tokens_in']
                meta['tokens_out'] = int(meta.get('tokens_out') or 0) + self.spent['tokens_out']
                meta['seconds'] = round(time.time() - t0, 2)
                return obj, meta
            except _BusyExhausted as e:
                raise self._busy_error(e.args[0]) from None
            except Exception as e:  # noqa: BLE001
                self._note_spent(e)
                errs.append(f'{p.name}: {str(e)[:200]}')
                self.fallbacks.append(p.name)
        raise LLMError('; '.join(errs) or 'sin proveedores configurados', meta=dict(self.spent))
