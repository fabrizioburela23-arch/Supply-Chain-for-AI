"""brokerage/crypto.py — cifrado de credenciales de clientes (Fernet).

Clave:
  1. `BROKERAGE_ENC_KEY` (recomendado): una clave Fernet (44 caracteres
     base64-url). Generarla UNA vez con:
         python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
     y pegarla en Railway. Si se pierde, las credenciales guardadas ya no se
     pueden descifrar (hay que volver a conectar cada cuenta).
  2. Si falta, se DERIVA de `SECRET_KEY` (SHA-256 → base64-url) y se registra
     una advertencia: funciona, pero cambiar SECRET_KEY deja ilegibles las
     credenciales guardadas. Con el SECRET_KEY por defecto del repo la clave es
     pública → `key_source()` devuelve 'default' y el 🩺/status lo muestra.

Reglas: nada de este módulo registra (log) ni devuelve un secreto. Para
mostrar algo en la UI se usa `mask()` → '****1234'.
"""
import base64
import hashlib
import hmac
import json
import logging
import os

log = logging.getLogger('khipu')

_DEFAULT_SECRET = 'khipu-dev-secret-change-me'
_warned = set()


class CryptoUnavailable(RuntimeError):
    pass


def _warn_once(key, msg):
    if key not in _warned:
        _warned.add(key)
        log.warning(msg)


def _raw_key_material():
    """(bytes de la clave Fernet, origen). Se lee del entorno en cada llamada
    (barato) para que un cambio de variable no requiera reiniciar módulos."""
    env_key = (os.getenv('BROKERAGE_ENC_KEY') or '').strip()
    if env_key:
        return env_key.encode(), 'env'
    secret = os.getenv('SECRET_KEY') or _DEFAULT_SECRET
    derived = base64.urlsafe_b64encode(hashlib.sha256(('khipu-brokerage|' + secret).encode()).digest())
    if secret == _DEFAULT_SECRET:
        _warn_once('default', '⚠️  brokerage: BROKERAGE_ENC_KEY y SECRET_KEY sin configurar — las credenciales '
                              'de clientes se cifran con una clave PÚBLICA. Configura BROKERAGE_ENC_KEY en Railway.')
        return derived, 'default'
    _warn_once('derived', 'brokerage: BROKERAGE_ENC_KEY sin configurar — clave derivada de SECRET_KEY '
                          '(si cambias SECRET_KEY, las credenciales guardadas quedarán ilegibles).')
    return derived, 'secret_key'


def key_source():
    """'env' | 'secret_key' | 'default' — para el panel de estado (sin secretos)."""
    return _raw_key_material()[1]


def _fernet():
    try:
        from cryptography.fernet import Fernet
    except Exception as e:  # noqa: BLE001
        raise CryptoUnavailable('falta el paquete "cryptography" (requirements.txt)') from e
    key, _src = _raw_key_material()
    try:
        return Fernet(key)
    except Exception as e:  # noqa: BLE001
        raise CryptoUnavailable('BROKERAGE_ENC_KEY no es una clave Fernet válida (44 caracteres base64-url)') from e


def crypto_available():
    try:
        _fernet()
        return True
    except CryptoUnavailable:
        return False


def _in_production():
    return any((os.getenv(n) or '').strip() for n in
               ('RAILWAY_ENVIRONMENT', 'RAILWAY_ENVIRONMENT_NAME', 'RAILWAY_PROJECT_ID'))


def encrypt_json(data):
    """dict → token Fernet (str). Lanza CryptoUnavailable si no hay cifrado.

    Auditoría #15 (defensa en profundidad; service.set_credentials/oauth ya lo
    rechazan antes): en PRODUCCIÓN (Railway) con la clave derivada del
    SECRET_KEY por defecto —pública— NUNCA se cifra/guarda una credencial."""
    if key_source() == 'default' and _in_production():
        raise CryptoUnavailable('Falta BROKERAGE_ENC_KEY y SECRET_KEY es la de por defecto: no se guardan '
                                'credenciales en producción · BROKERAGE_ENC_KEY missing and SECRET_KEY is the '
                                'default: credentials are not stored in production')
    return _fernet().encrypt(json.dumps(data or {}, separators=(',', ':')).encode()).decode()


def decrypt_json(token):
    """token → dict. Devuelve {} si está vacío; lanza CryptoUnavailable si la
    clave no coincide (p. ej. cambió BROKERAGE_ENC_KEY/SECRET_KEY)."""
    if not token:
        return {}
    try:
        from cryptography.fernet import InvalidToken
    except Exception as e:  # noqa: BLE001
        raise CryptoUnavailable('falta el paquete "cryptography"') from e
    try:
        return json.loads(_fernet().decrypt(token.encode()).decode())
    except InvalidToken as e:
        raise CryptoUnavailable('no se pudieron descifrar las credenciales (¿cambió BROKERAGE_ENC_KEY o '
                                'SECRET_KEY?) — vuelve a conectar la cuenta') from e


def mask(value, keep=4):
    """'PKABCDEF1234' → '****1234'. Nunca devuelve más de `keep` caracteres."""
    s = str(value or '')
    if not s:
        return ''
    if len(s) <= keep + 2:
        return '****'
    return '****' + s[-keep:]


def sign(message):
    """HMAC-SHA256 (hex, 32 chars) con una clave derivada de la de cifrado —
    firma el `state` de OAuth para que no se pueda fabricar."""
    key, _src = _raw_key_material()
    mac = hmac.new(hashlib.sha256(b'oauth-state|' + key).digest(), message.encode(), hashlib.sha256)
    return mac.hexdigest()[:32]


def verify(message, signature):
    return hmac.compare_digest(sign(message), str(signature or ''))
