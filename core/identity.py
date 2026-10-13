"""core/identity.py — QUIÉN actúa (docs/INFRA_OPERATIVA.md §1.2 paso 1, §2.2 y §8.1; paso 5 del plan).

Antes cada ruta tomaba el campo libre `actor` del cuerpo como la identidad: `actor:"otra-persona-inventada"`
quedaba registrado tal cual (G-4, GV-06). Ahora la identidad sale de CÓMO se autenticó la petición y el texto
libre queda solo como etiqueta para mostrar (`declared_name`):

  · PIN de operador válido (core/pin.py)  → `op:fabrizio`  (artefacto `identity.operators`, decisión D1)
  · token MCP                              → `mcp:<token_id>` (+ nombre del cliente como declared_name)
  · agente del registro único               → `agent:<id>@<versión>` (solo ids de engine/agents_registry.js)
  · reloj del servidor (core/scheduler.py)  → `system:<tarea>`
  · interfaz sin autenticar                 → `ui:anon` (+ hash del dueño en on_behalf_of si viene X-Khipu-Owner)

`X-Khipu-Channel` es el canal DECLARADO por el cliente (ui|voice|chat|terminal|crypto|mcp|agent|…): se guarda
como metadato y NUNCA autoriza nada. `X-Khipu-Pin-Source` (prompted|stored) dice si el PIN se tecleó ahora o
se reusó de los 12 h guardados (limitación conocida §8.2: un PIN compartido no prueba presencia).

Nada aquí habla con la base ni con la IA; lo importan core/pin.py, ontology/api.py, brokerage/api.py,
server.py, mcp_server/api.py, core/scheduler.py y core/decisions.py.
"""
import contextvars
import hashlib
import hmac
import os
import re
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from typing import Optional

# D1 (por defecto mientras Fabrizio no responda): un solo aprobador; el PIN de TRADE_PIN es "op:fabrizio".
# Será el artefacto `identity.operators` del registro de gobernanza (paso 9); hasta entonces vive aquí.
OPERATORS = {'op:fabrizio': {'pin_env': 'TRADE_PIN'}}
DEFAULT_OPERATOR = 'op:fabrizio'

CHANNELS = ('ui', 'voice', 'chat', 'terminal', 'crypto', 'mcp', 'agent', 'scheduler', 'system', 'cli', 'api')
KINDS = ('human', 'agent', 'system', 'external_ai')
AUTHS = ('pin', 'mcp_token', 'oauth', 'agent_registry', 'scheduler', 'none')
PIN_SOURCES = ('prompted', 'stored')
ANON_ID = 'ui:anon'

_ID_RX = re.compile(r'[^a-z0-9_.@:\-]+')
_CTRL_RX = re.compile(r'[\x00-\x1f\x7f]+')

_CURRENT = contextvars.ContextVar('kh_principal', default=None)


@dataclass(frozen=True)
class Principal:
    id: str                       # op:fabrizio · agent:cadena@1 · mcp:<token_id> · system:<tarea> · ui:anon
    kind: str                     # human | agent | system | external_ai
    auth: str                     # pin | mcp_token | oauth | agent_registry | scheduler | none
    channel: str                  # canal DECLARADO (metadato, nunca autoriza)
    declared_name: Optional[str] = None    # lo que el cliente escribió en "actor": SOLO para mostrar
    on_behalf_of: Optional[str] = None     # client_id u owner_hash
    pin_source: Optional[str] = None       # prompted | stored (solo auth='pin')

    @property
    def is_human_pin(self):
        return self.kind == 'human' and self.auth == 'pin'

    @property
    def authenticated(self):
        return self.auth != 'none'

    def as_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}

    def label(self):
        """Etiqueta corta para mostrar: 'op:fabrizio (Fabrizio)'. NO es la identidad registrada."""
        return f'{self.id} ({self.declared_name})' if self.declared_name else self.id


# ── normalización ────────────────────────────────────────────────────────────
def slug(s, n=48):
    s = _ID_RX.sub('-', str(s or '').strip().lower()).strip('-')
    return (s or 'unknown')[:n]


def clean_declared(s, n=80):
    """Etiqueta libre → texto de una línea sin controles, ≤ n caracteres; '' → None."""
    if s is None:
        return None
    s = _CTRL_RX.sub(' ', str(s)).strip()
    return s[:n] or None


def normalize_channel(ch, default='api'):
    ch = str(ch or '').strip().lower()
    return ch if ch in CHANNELS else default


def _secret():
    try:
        from core.pin import DEFAULT_SECRET_KEY
    except Exception:  # noqa: BLE001
        DEFAULT_SECRET_KEY = 'khipu-dev-secret-change-me'
    return (os.getenv('SECRET_KEY') or DEFAULT_SECRET_KEY).encode()


def hash_id(value, purpose='owner', n=16):
    """Hash con clave (HMAC-SHA256 de SECRET_KEY) de un identificador del cliente (dueño, IP): nunca en claro."""
    if not value:
        return None
    mac = hmac.new(_secret(), f'{purpose}:{value}'.encode(), hashlib.sha256).hexdigest()
    return mac[:n]


# ── constructores ────────────────────────────────────────────────────────────
def operator(channel='ui', declared=None, pin_source=None, op_id=DEFAULT_OPERATOR):
    ps = pin_source if pin_source in PIN_SOURCES else None
    return Principal(op_id, 'human', 'pin', normalize_channel(channel, 'ui'), clean_declared(declared), None, ps)


def anon(channel='ui', declared=None, owner=None):
    return Principal(ANON_ID, 'human', 'none', normalize_channel(channel, 'ui'), clean_declared(declared),
                     (f'owner:{hash_id(owner)}' if owner else None))


def system(task, declared=None):
    return Principal(f'system:{slug(task)}', 'system', 'scheduler', 'scheduler', clean_declared(declared))


def mcp(token_id, client_name=None, oauth=False):
    return Principal(f'mcp:{slug(token_id, 64)}', 'external_ai', 'oauth' if oauth else 'mcp_token', 'mcp',
                     clean_declared(client_name))


def registry_agent_ids():
    try:
        from core.agents_registry import AGENT_IDS, SEATS
        return set(AGENT_IDS) | set(SEATS)
    except Exception:  # noqa: BLE001
        return set()


def agent(name, version='1', declared=None):
    """`agent:<id>@<versión>` SOLO para ids del registro único (mascotas y puestos). Otro nombre → ValueError
    (un agente no se inventa su identidad)."""
    aid = slug(name, 40)
    if aid not in registry_agent_ids():
        raise ValueError(f'agente no registrado en engine/agents_registry.js: {name!r}')
    return Principal(f'agent:{aid}@{slug(version, 12)}', 'agent', 'agent_registry', 'agent', clean_declared(declared))


_PREFIX_KIND = {'op': ('human', 'pin'), 'agent': ('agent', 'agent_registry'), 'system': ('system', 'scheduler'),
                'mcp': ('external_ai', 'mcp_token'), 'ui': ('human', 'none')}


def legacy(actor, channel='api'):
    """Llamadas de BIBLIOTECA anteriores al paso 5 (scripts, tests, ciclos internos) que solo traen un texto:
    queda `legacy:<texto>` sin autenticación — se ve en el libro como lo que es."""
    a = clean_declared(actor, 80) or 'unknown'      # 80 = decisions.declared_name (String(80))
    return Principal(f'legacy:{slug(a, 80)}', 'system', 'none', normalize_channel(channel), a)


# ── contexto (por hilo / por petición) ───────────────────────────────────────
def current():
    """Principal activo: el de `use()` en este contexto, o el que una ruta ató a la petición (MCP)."""
    p = _CURRENT.get()
    if p is not None:
        return p
    try:
        from flask import g, has_request_context
        if has_request_context():
            return getattr(g, 'kh_principal', None)
    except Exception:  # noqa: BLE001
        pass
    return None


@contextmanager
def use(principal):
    tok = _CURRENT.set(principal)
    try:
        yield principal
    finally:
        _CURRENT.reset(tok)


def bind_request(principal):
    """Ata un principal a la petición Flask actual (lo usa /mcp tras validar el token)."""
    from flask import g
    g.kh_principal = principal
    return principal


def note_pin_ok(op_id=DEFAULT_OPERATOR):
    """core/pin.check lo llama al aceptar el PIN: la petición queda autenticada como ese operador."""
    try:
        from flask import g, has_request_context
        if has_request_context():
            g.kh_operator = op_id
    except Exception:  # noqa: BLE001
        pass


def operator_for_pin_env(env_name='TRADE_PIN'):
    for op_id, spec in OPERATORS.items():
        if spec.get('pin_env') == env_name:
            return op_id
    return DEFAULT_OPERATOR


def channel_from_request(default='api'):
    try:
        from flask import request
        return normalize_channel(request.headers.get('X-Khipu-Channel'), default)
    except Exception:  # noqa: BLE001
        return default


def principal_from_request(declared=None, channel=None):
    """Principal de la petición Flask actual. `declared` = el 'actor' del cuerpo (solo etiqueta).
    El PIN solo cuenta si un decorador (require_pin/require_operator) o pin.check lo VERIFICÓ en esta
    petición: aquí nunca se compara un PIN (sin efectos sobre el contador de fallos)."""
    from flask import g, has_request_context, request
    if not has_request_context():
        return current() or legacy(declared or 'unknown')
    hdr_actor = request.headers.get('X-Khipu-Actor')
    decl = clean_declared(declared if declared not in (None, '') else hdr_actor)
    bound = current()
    if bound is not None:
        return replace(bound, declared_name=decl or bound.declared_name)
    ch = normalize_channel(channel) if channel else channel_from_request('api')
    op_id = getattr(g, 'kh_operator', None)
    if op_id:
        return operator(ch, decl, (request.headers.get('X-Khipu-Pin-Source') or '').strip().lower(), op_id)
    return anon(ch, decl, request.headers.get('X-Khipu-Owner'))
