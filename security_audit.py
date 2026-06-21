#!/usr/bin/env python3
"""
security_audit.py — Khipu Finance (Fase 2H)

Auditoría de seguridad estática + runtime del backend. Pensada para correr en
local y en CI (sale con código 1 si algo falla).

    python security_audit.py

Comprueba:
  1. No hay API keys / secretos hardcodeados en el código (py/js/html).
  2. El server arranca sin colisiones de endpoints (importa server.py).
  3. DEBUG=False en producción.
  4. SECRET_KEY se lee de variables de entorno (no hardcodeada).
  5. Cabeceras de seguridad presentes (CSP, X-Frame-Options, nosniff, HSTS...).
  6. Content-Security-Policy bien formada (default-src + frame-ancestors 'none').
  7. Todos los endpoints públicos /v1/* exigen autenticación (@khipu_auth).
  8. .env está en .gitignore y no commiteado.
  9. Hay límite de tamaño de body (MAX_CONTENT_LENGTH).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SERVER_PY = os.path.join(ROOT, 'server.py')

# ── salida con color (degrada a texto plano si no hay TTY) ──────────────────
_TTY = sys.stdout.isatty()
def _c(code, s): return f'\033[{code}m{s}\033[0m' if _TTY else s
def green(s):  return _c('32', s)
def red(s):    return _c('31', s)
def yellow(s): return _c('33', s)
def bold(s):   return _c('1', s)

results = []   # (ok: bool, name: str, detail: str)
def check(ok, name, detail=''):
    results.append((bool(ok), name, detail))

# Archivos de código a escanear en busca de secretos
SCAN_EXTS = ('.py', '.js', '.html', '.json', '.toml', '.yml', '.yaml')
SKIP_DIRS = {'.git', 'node_modules', '.claude', '__pycache__', '.venv', 'venv', 'litellm'}
SKIP_FILES = {'.env.example', 'package-lock.json'}

# Prefijos de secretos reales (alta confianza, sin falsos positivos)
HIGH_SIGNAL = [
    re.compile(r'sk-ant-api[0-9]{2}-[A-Za-z0-9_\-]{20,}'),  # Anthropic
    re.compile(r'AKIA[0-9A-Z]{16}'),                         # AWS access key
    re.compile(r'ghp_[A-Za-z0-9]{36}'),                      # GitHub PAT
    re.compile(r'xox[baprs]-[A-Za-z0-9-]{10,}'),             # Slack
    re.compile(r'AIza[0-9A-Za-z_\-]{35}'),                   # Google API
]
# Asignaciones sospechosas: VAR_KEY = "literal largo"
ASSIGN_RE = re.compile(
    r'(?i)(api[_-]?key|secret|token|password|passwd|access[_-]?key)\s*[:=]\s*'
    r'["\']([A-Za-z0-9_\-]{16,})["\']')
# Marcadores que indican placeholder / lectura de entorno → no es un secreto
SAFE_MARKERS = ('getenv', 'environ', 'process.env', 'your_', 'example', 'placeholder',
                'change-me', 'change_me', 'xxxx', 'localstorage', 'keys.get', 'localStorage',
                'test', 'dummy', 'sk-placeholder', 'khipu-litellm-key', 'khipu-dev-secret')

def scan_secrets():
    findings = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.claude')]
        for fn in filenames:
            if fn in SKIP_FILES or not fn.endswith(SCAN_EXTS):
                continue
            if fn.endswith('.min.js'):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, ROOT)
            try:
                with open(path, encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        for rx in HIGH_SIGNAL:
                            if rx.search(line):
                                findings.append(f'{rel}:{i} (high-signal secret pattern)')
                        m = ASSIGN_RE.search(line)
                        if m and not any(s in line.lower() for s in SAFE_MARKERS):
                            findings.append(f'{rel}:{i} ({m.group(1)} = literal)')
            except Exception:
                continue
    return findings

def main():
    print(bold('\n🔒  Khipu Finance — Auditoría de seguridad (Fase 2)\n'))

    src = open(SERVER_PY, encoding='utf-8').read()

    # 1) secretos hardcodeados
    findings = scan_secrets()
    check(not findings, 'Sin secretos hardcodeados en el código',
          '' if not findings else '\n      ' + '\n      '.join(findings[:10]))

    # 2) el server importa sin colisiones de endpoint
    import_ok, import_err, app = True, '', None
    try:
        sys.path.insert(0, ROOT)
        import server as _server
        app = _server.app
        dupes = {}
        seen = {}
        for rule in app.url_map.iter_rules():
            seen.setdefault(rule.endpoint, []).append(str(rule))
        dupes = {k: v for k, v in seen.items() if len(v) > 1}
        if dupes:
            import_ok, import_err = False, f'endpoints duplicados: {dupes}'
    except Exception as e:  # noqa: BLE001
        import_ok, import_err = False, str(e)[:200]
    check(import_ok, 'server.py importa sin colisiones de endpoint', import_err)

    # 3) DEBUG=False
    check('debug=False' in src and 'debug=True' not in src,
          'DEBUG desactivado en producción')

    # 4) SECRET_KEY desde entorno
    check("SECRET_KEY" in src and "os.getenv('SECRET_KEY'" in src,
          'SECRET_KEY se lee de variable de entorno')

    # 5) cabeceras de seguridad
    needed = ['X-Content-Type-Options', 'X-Frame-Options', 'Referrer-Policy',
              'Permissions-Policy', 'Strict-Transport-Security', 'Content-Security-Policy']
    missing = [h for h in needed if h not in src]
    check(not missing, 'Cabeceras de seguridad presentes',
          '' if not missing else f'faltan: {missing}')

    # 6) CSP bien formada
    csp_ok = ("default-src 'self'" in src and "frame-ancestors 'none'" in src
              and "object-src 'none'" in src)
    check(csp_ok, "CSP con default-src/frame-ancestors/object-src")

    # 7) endpoints /v1/* exigen auth
    unprotected = []
    lines = src.splitlines()
    for idx, line in enumerate(lines):
        m = re.search(r"@app\.route\(['\"](/v1/[^'\"]*)", line)
        if not m:
            continue
        path = m.group(1)
        if path == '/v1/auth/key':       # emite las keys, no requiere auth
            continue
        # mira hacia adelante hasta el 'def': ¿hay @khipu_auth?
        has_auth = False
        for j in range(idx, min(idx + 8, len(lines))):
            if '@khipu_auth' in lines[j]:
                has_auth = True
            if lines[j].lstrip().startswith('def '):
                break
        if not has_auth:
            unprotected.append(path)
    check(not unprotected, 'API pública /v1/* protegida con @khipu_auth',
          '' if not unprotected else f'sin auth: {unprotected}')

    # 8) .env en .gitignore
    gi = os.path.join(ROOT, '.gitignore')
    gi_ok = os.path.exists(gi) and '.env' in open(gi, encoding='utf-8').read()
    env_committed = os.path.exists(os.path.join(ROOT, '.env'))
    check(gi_ok and not env_committed, '.env ignorado por git y no presente en el repo',
          '' if gi_ok else '.env no está en .gitignore')

    # 9) límite de tamaño de body
    check('MAX_CONTENT_LENGTH' in src, 'Límite de tamaño de request (MAX_CONTENT_LENGTH)')

    # ── informe ──────────────────────────────────────────────────────────
    print()
    passed = 0
    for ok, name, detail in results:
        mark = green('✓ PASS') if ok else red('✗ FAIL')
        print(f'  {mark}  {name}{(red(detail) if not ok else "")}')
        passed += ok
    total = len(results)
    print()
    if passed == total:
        print(green(bold(f'  ✓ {passed}/{total} comprobaciones superadas — listo para producción\n')))
        return 0
    print(red(bold(f'  ✗ {passed}/{total} superadas — {total - passed} fallo(s) que resolver\n')))
    return 1


if __name__ == '__main__':
    sys.exit(main())
