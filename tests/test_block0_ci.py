"""Bloque 0 (docs/BRECHAS_V2.md, G5-02): las pruebas corren en CI antes de desplegar.

· .github/workflows/ci.yml corre `pytest tests/ -q` con Python 3.11 + constraints.txt,
  Node y Postgres 16 (DATABASE_URL=…/khipus_test) en cada push/PR a main y claude/**.
· En CI no hay Playwright ni Chromium: toda prueba de navegador debe SALTARSE (no
  fallar). Se comprueba de verdad corriendo una con `playwright` bloqueado.
· No se rompe el humo del MCP (smoke-mcp.yml)."""
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CI = os.path.join(ROOT, '.github', 'workflows', 'ci.yml')


def _ci():
    with open(CI, encoding='utf-8') as fh:
        return fh.read()


def test_workflow_de_ci_corre_toda_la_suite_con_postgres():
    y = _ci()
    for must in ('pytest tests/ -q', 'postgres:16', 'python-version: \'3.11\'',
                 'pip install -r requirements.txt -c constraints.txt', "node-version: '20'",
                 'DATABASE_URL: postgresql://postgres:devpass@localhost:5432/khipus_test',
                 'POSTGRES_PASSWORD: devpass', 'POSTGRES_DB: khipus_test', 'pg_isready',
                 "branches: [main, 'claude/**']", 'pull_request:', '  pytest:\n    name: pytest'):
        assert must in y, must
    assert 'KHIPU_SCHEDULER' in y               # el reloj del servidor apagado en pruebas (conftest también)


def test_el_humo_del_mcp_sigue_intacto():
    with open(os.path.join(ROOT, '.github', 'workflows', 'smoke-mcp.yml'), encoding='utf-8') as fh:
        y = fh.read()
    assert 'name: smoke-mcp' in y and 'scripts/smoke_mcp.py' in y and 'KHIPU_MCP_TOKEN' in y


def test_toda_prueba_de_navegador_se_salta_sin_playwright():
    """Si una prueba usara Playwright sin importorskip, en CI (sin Playwright) daría ERROR."""
    bad = []
    for path in glob.glob(os.path.join(ROOT, 'tests', '*.py')):
        if os.path.basename(path) == os.path.basename(__file__):
            continue
        with open(path, encoding='utf-8') as fh:
            src = fh.read()
        if 'sync_playwright' in src and "importorskip('playwright" not in src:
            bad.append(os.path.basename(path))
        if 'from playwright' in src or 'import playwright' in src:
            bad.append(os.path.basename(path) + ' (import directo)')
    assert not bad, bad


def test_sin_playwright_la_prueba_de_navegador_queda_saltada(tmp_path):
    block = tmp_path / 'playwright'
    block.mkdir()
    (block / '__init__.py').write_text('# paquete vacío: tapa al Playwright instalado → playwright.sync_api no existe\n')
    env = dict(os.environ, PYTHONPATH=str(tmp_path) + os.pathsep + os.environ.get('PYTHONPATH', ''))
    env.pop('DATABASE_URL', None)
    r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                        'tests/test_cleanup_dialogs.py::test_navegador_prompt_y_actor'],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert '1 skipped' in r.stdout, r.stdout[-2000:]
