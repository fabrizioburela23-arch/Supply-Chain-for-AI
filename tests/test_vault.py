"""tests/test_vault.py — la bóveda de Obsidian (vault/) existe, está AL DÍA y es segura.

La genera scripts/build_vault.py (determinista, sin IA ni red). Si cambias módulos,
rutas o variables de entorno y no regeneras, esta prueba falla: corre
`python scripts/build_vault.py` y vuelve a commitear.
"""
import glob
import json
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT = os.path.join(ROOT, 'vault')
SCRIPT = os.path.join(ROOT, 'scripts', 'build_vault.py')

# Lista INDEPENDIENTE de la del generador: si alguien achica FUENTES, esto lo detecta.
MODULE_GLOBS = [
    'core/*.py', 'core/providers/*.py', 'research/*.py', 'research/agents/*.py', 'ontology/*.py',
    'matrix/*.py', 'mcp_server/*.py', 'brokerage/*.py', 'scripts/*.py', 'scripts/*.js',
    'engine/*.js', 'sim/*.js', 'nodes/*.js', 'server.py', 'app.html', 'sw.js',
]
REQUIRED_EDGE_TYPES = {'imports', 'uses_global', 'calls_endpoint', 'defines_endpoint', 'tested_by',
                       'reads_env', 'mentions_in_session'}
WIKILINK = re.compile(r'\[\[([^\]|#^]+)(?:[#^][^\]|]*)?(?:\|[^\]]*)?\]\]')


def _vault_files(ext=None):
    out = []
    for dp, _dn, fns in os.walk(VAULT):
        if os.sep + '.obsidian' in dp + os.sep and ext == '.md':
            continue
        for fn in fns:
            if ext is None or fn.endswith(ext):
                out.append(os.path.join(dp, fn))
    return sorted(out)


def _read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def _front_matter(text):
    m = re.match(r'---\n(.*?)\n---\n', text, re.S)
    meta = {}
    if m:
        for ln in m.group(1).split('\n'):
            k, _, v = ln.partition(':')
            v = v.strip()
            try:
                meta[k.strip()] = json.loads(v)
            except ValueError:
                meta[k.strip()] = v
    return meta


@pytest.fixture(scope='module')
def check_run():
    """(a) + (d): el generador corre y --check pasa contra la bóveda commiteada."""
    return subprocess.run([sys.executable, SCRIPT, '--check'], cwd=ROOT, capture_output=True, text=True,
                          timeout=600)


def test_generator_runs_and_vault_is_fresh(check_run):
    assert check_run.returncode == 0, (
        'La bóveda vault/ está DESACTUALIZADA o el generador falló. Corre:  python scripts/build_vault.py\n'
        + check_run.stdout[-3000:] + check_run.stderr[-3000:])
    assert 'Bóveda al día' in check_run.stdout


def test_vault_has_home_report_guide_and_graph():
    for rel in ('00 Mapa de Khipus.md', '01 Reporte del grafo.md', '02 Cómo usar esta bóveda.md',
                '_grafo/graph.json', '_grafo/mapa.html', '.obsidian/app.json', '.obsidian/graph.json'):
        assert os.path.isfile(os.path.join(VAULT, rel)), rel
    g = json.loads(_read(os.path.join(VAULT, '_grafo', 'graph.json')))
    assert g['nodes'] and g['edges']
    types = {e['type'] for e in g['edges']}
    assert REQUIRED_EDGE_TYPES <= types, REQUIRED_EDGE_TYPES - types
    ids = {n['id'] for n in g['nodes']}
    for e in g['edges']:
        assert e['source'] in ids and e['target'] in ids, e
    for n in g['nodes']:
        assert {'id', 'label', 'layer', 'type', 'lines', 'path'} <= set(n), n
    # el grafo de Obsidian ya viene coloreado por capa
    og = json.loads(_read(os.path.join(VAULT, '.obsidian', 'graph.json')))
    queries = {c['query'] for c in og['colorGroups']}
    for layer in g['layers']:
        assert 'tag:#' + layer['tag'] in queries, layer


def test_every_module_has_a_note():
    rutas = set()
    for p in _vault_files('.md'):
        r = _front_matter(_read(p)).get('ruta')
        if isinstance(r, str):
            rutas.add(r)
    missing = []
    for pat in MODULE_GLOBS:
        for f in glob.glob(os.path.join(ROOT, pat)):
            rel = os.path.relpath(f, ROOT).replace(os.sep, '/')
            if rel not in rutas:
                missing.append(rel)
    assert not missing, f'Archivos sin nota en vault/ (corre python scripts/build_vault.py): {missing}'


def test_every_wikilink_resolves():
    notes = {os.path.splitext(os.path.basename(p))[0].lower() for p in _vault_files('.md')}
    broken = []
    for p in _vault_files('.md'):
        for m in WIKILINK.finditer(_read(p)):
            target = m.group(1).strip()
            if target.lower() not in notes:
                broken.append((os.path.relpath(p, VAULT), target))
    assert not broken, broken[:20]


def test_note_names_are_unique_and_portable():
    seen = {}
    for p in _vault_files('.md'):
        name = os.path.basename(p)[:-3]
        assert not re.search(r'[\\/:*?"<>|#^\[\]]', name), name     # válido en Windows y como [[enlace]]
        assert name.lower() not in seen, (p, seen.get(name.lower()))
        seen[name.lower()] = p


SECRET_PATTERNS = [
    re.compile(r'sk-[A-Za-z0-9_-]{20,}'),             # Anthropic / OpenAI
    re.compile(r'sk_[A-Za-z0-9]{24,}'),               # ElevenLabs
    re.compile(r'AIza[0-9A-Za-z_-]{30,}'),            # Google / Gemini
    re.compile(r'xi-[A-Za-z0-9]{20,}'),
    re.compile(r'kmcp_[A-Za-z0-9_-]{16,}'),           # tokens MCP de Khipus
    re.compile(r'nvapi-[A-Za-z0-9_-]{20,}'),          # NVIDIA
    re.compile(r'Bearer\s+[A-Za-z0-9._-]{20,}'),
    re.compile(r'(?<![0-9a-fA-F])[0-9a-f]{32,}(?![0-9a-fA-F])'),          # hex largo
    re.compile(r'(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/=])'),  # base64 largo (ver _looks_random)
    re.compile(r'postgres(?:ql)?://[^\s"\'`]+:[^\s"\'`]+@'),               # DSN con contraseña
]


def _looks_random(tok):
    """Una clave en base64 mezcla mayúsculas, minúsculas y varios dígitos; el texto o las rutas no."""
    return (sum(c.isdigit() for c in tok) >= 3 and any(c.isupper() for c in tok) and any(c.islower() for c in tok)
            and tok.count('/') <= 2)


def test_vault_has_no_secret_values():
    hits = []
    texts = [(p, _read(p)) for p in _vault_files() if p.endswith(('.md', '.json', '.html'))]
    for p, t in texts:
        for rx in SECRET_PATTERNS:
            for m in rx.finditer(t):
                if rx is SECRET_PATTERNS[8] and not _looks_random(m.group(0)):
                    continue        # "VaR/CVaR/volatilidad/…" o una ruta /api/… no son secretos
                hits.append((os.path.relpath(p, VAULT), m.group(0)[:24] + '…'))
    assert not hits, f'Posibles secretos en la bóveda: {hits[:10]}'
    # y ningún VALOR real de las variables secretas de este entorno (solo nombres)
    from core.http import secret_values
    vals = [v for v in secret_values(min_len=8)]
    for p, t in texts:
        for v in vals:
            assert v not in t, f'Valor de una variable secreta dentro de {os.path.relpath(p, VAULT)}'


def test_env_notes_have_names_only():
    for p in glob.glob(os.path.join(VAULT, 'Entorno', 'ENV *.md')):
        meta = _front_matter(_read(p))
        assert meta.get('tipo') == 'variable'
        assert re.fullmatch(r'[A-Z][A-Z0-9_{}X]*', meta.get('nombre', '')), p


def test_map_html_is_self_contained_and_loads_only_cdnjs():
    html = _read(os.path.join(VAULT, '_grafo', 'mapa.html'))
    assert '<title>Mapa de Khipus</title>' in html
    srcs = re.findall(r'<script[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', html, re.I)
    assert srcs == ['https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js'], srcs
    assert not re.search(r'<link[^>]+href\s*=\s*["\']https?:', html, re.I)
    assert not re.search(r'\bimport\s*\(|@import', html)
    # datos en línea (autocontenido) y temas claro/oscuro con tokens en :root
    assert '<script id="data" type="application/json">' in html
    assert ':root{' in html and 'prefers-color-scheme: dark' in html
    assert 'lang="es"' in html


def test_gitignore_keeps_obsidian_local_files_out():
    """De vault/.obsidian/ solo se versionan app.json y graph.json (workspace, caché, apariencia, plugins… son de
    cada PC y no deben aparecer como cambios en GitHub Desktop)."""
    gi = _read(os.path.join(ROOT, '.gitignore')).splitlines()
    assert 'vault/.obsidian/*' in gi
    assert '!vault/.obsidian/app.json' in gi and '!vault/.obsidian/graph.json' in gi
    try:
        r = subprocess.run(['git', 'check-ignore', '--no-index', 'vault/.obsidian/workspace.json',
                            'vault/.obsidian/appearance.json', 'vault/.obsidian/core-plugins.json',
                            'vault/.obsidian/plugins/x/main.js', 'vault/.obsidian/cache'],
                           cwd=ROOT, capture_output=True, text=True, timeout=30)
        r2 = subprocess.run(['git', 'check-ignore', '--no-index', 'vault/.obsidian/app.json',
                             'vault/.obsidian/graph.json', 'vault/00 Mapa de Khipus.md'],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        pytest.skip('git no disponible')
    if r.returncode == 128:
        pytest.skip('no es un repositorio git')
    assert len(r.stdout.split('\n')) - 1 == 5, r.stdout
    assert r2.stdout.strip() == '', r2.stdout


def test_vault_not_in_docker_image():
    lines = [ln.strip() for ln in _read(os.path.join(ROOT, '.dockerignore')).splitlines()]
    assert 'vault' in lines or 'vault/' in lines


@pytest.fixture(scope='module')
def bv():
    import importlib.util
    spec = importlib.util.spec_from_file_location('build_vault', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope='module')
def graph():
    return json.loads(_read(os.path.join(VAULT, '_grafo', 'graph.json')))


def _edges(graph, etype):
    return {(e['source'], e['target']) for e in graph['edges'] if e['type'] == etype}


def test_plain_words_are_not_dynamic_imports(bv, graph):
    """'server' o 'matrix' como texto (categoría de error, clave de dict) NO es importar ese módulo; un texto con
    puntos o el argumento de import_module/__import__/sys.modules.get sí."""
    import ast
    src = (
        "import importlib, sys\n"
        "CAT = 'server'\n"
        "d = {'matrix': 1, 'research': 2}\n"
        "m = importlib.import_module('core.world')\n"
        "s = sys.modules.get('server')\n"
        "BPS = (('brokerage.api', 'brokerage_bp'),)\n"
        "x = __import__('ontology')\n"
    )
    refs = set(bv.dyn_module_refs(ast.parse(src)))
    assert {'core.world', 'server', 'brokerage.api', 'ontology'} <= refs
    assert 'matrix' not in refs and 'research' not in refs
    imports = _edges(graph, 'imports')
    # core/company_data.py tiene el texto 'server' (categoría de error): no depende de server.py
    assert ('core/company_data.py', 'server.py') not in imports
    for pair in (('core/canvas_spec.py', 'matrix/__init__.py'), ('core/risk_report.py', 'matrix/__init__.py'),
                 ('brokerage/api.py', 'brokerage/__init__.py'), ('research/runner.py', 'research/__init__.py'),
                 ('mcp_server/auth.py', 'research/__init__.py')):
        assert pair not in imports, pair
    # importaciones dinámicas reales siguen contando
    assert ('server.py', 'core/khipu_chat.py') in imports            # tupla de blueprints
    assert ('mcp_server/tools.py', 'research/health.py') in imports  # _module('research.health', …)
    assert ('mcp:run_research', 'research/__init__.py') not in imports


def test_vault_test_is_not_a_caller_or_coverage(graph):
    """Esta prueba nombra rutas y archivos como datos: no llama rutas ni "cubre" módulos (solo al generador)."""
    me = 'tests/test_vault.py'
    assert not [e for e in graph['edges'] if e['type'] == 'calls_endpoint' and e['source'] == me]
    assert {a for a, b in _edges(graph, 'tested_by') if b == me} == {'scripts/build_vault.py'}


def test_base_prefix_joins_relative_paths(bv, graph):
    """var API = '/api/brokerage' en clients.js: solo cuenta lo que el archivo arma sobre la base."""
    code = "var API = '/api/brokerage';\ncall('GET', '/clients/' + encodeURIComponent(id) + '/audit?limit=30');\n" \
           "call('POST', API + '/orders/preview');\nvar r = /a'b/;"
    chains = bv.js_concat_chains(code)
    assert '/clients/◊/audit?limit=30' in chains and '◊/orders/preview' in chains
    assert not any(c.startswith('/audit') for c in chains)        # '/audit' a mitad de cadena no va solo
    assert bv.relative_refs(chains) == ['/clients/◊/audit', '/orders/preview']
    calls = _edges(graph, 'calls_endpoint')
    cj = 'engine/clients.js'
    assert (cj, 'endpoint:GET /api/brokerage/clients/<client_id>/audit') in calls
    assert (cj, 'endpoint:GET /api/brokerage/audit') not in calls          # solo la llama una prueba
    assert (cj, 'endpoint:GET /api/brokerage/oauth/callback') not in calls  # la llama Alpaca
    assert bv.route_is_external('/api/brokerage/oauth/callback')
    # una prueba que solo AFIRMA que '/api/trade' no aparece no llama a las 12 rutas de trading
    assert not [b for a, b in calls if a == 'tests/test_khipus_os_windows.py' and '/api/trade/' in b]


def test_object_keys_and_markup_text_are_not_global_uses(bv, graph):
    assert 'LINKS' not in bv.js_identifiers('return { LINKS: x, other: 1 };', skip_keys=True)[0]
    assert 'LINKS' in bv.js_identifiers('return { a: LINKS };', skip_keys=True)[0]
    assert 'b' in bv.js_identifiers('var y = a ? b : c;', skip_keys=True)[0]     # ternario ≠ clave
    uses = _edges(graph, 'uses_global')
    # G5-06: el JS que era inline en app.html vive en engine/app_*.js (LINKS y buildKhipusGraph(…) en app_main.js)
    for host in ('app.html', 'engine/app_main.js'):
        assert ('nodes/merge_graph.js', host) not in uses         # solo `return { LINKS: … }`
    for host in ('app.html', 'engine/app_main.js', 'engine/app_coordinator.js'):
        assert (host, 'engine/khipu_lang.js') not in uses         # 'KHIPU&gt;' / 'KHIPU TRADING' son texto
    assert ('engine/app_main.js', 'nodes/merge_graph.js') in uses  # app_main.js sí llama buildKhipusGraph(…)


def test_obsidian_config_is_merged_not_overwritten(bv):
    gen = bv.obsidian_files()
    assert bv.merge_obsidian_config('.obsidian/app.json', '{"x": 1}', gen['.obsidian/app.json']) is None
    old = {'scale': 2.5, 'repelStrength': 3, 'colorGroups': [
        {'query': 'path:Mis notas', 'color': {'a': 1, 'rgb': 1}},
        {'query': 'tag:#capa/dinero', 'color': {'a': 1, 'rgb': 2}}]}
    merged = json.loads(bv.merge_obsidian_config('.obsidian/graph.json', json.dumps(old), gen['.obsidian/graph.json']))
    assert merged['scale'] == 2.5 and merged['repelStrength'] == 3           # lo que movió la persona
    assert merged['colorGroups'][0]['query'] == 'path:Mis notas'             # sus grupos primero (ganan)
    dinero = [g for g in merged['colorGroups'] if g['query'] == 'tag:#capa/dinero']
    assert len(dinero) == 1 and dinero[0]['color']['rgb'] != 2               # el color de capa se repone
    assert 'linkDistance' in merged                                         # claves que faltaban
    again = bv.merge_obsidian_config('.obsidian/graph.json', json.dumps(merged), gen['.obsidian/graph.json'])
    assert again is None                                                    # sin cambios → no reescribe


def test_layer_colors_are_distinct_and_api_groups_follow_prefix(bv):
    import colorsys
    import math

    def lab(h):
        r, g, b = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
        r, g, b = f(r), f(g), f(b)
        X = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
        Y = 0.2126 * r + 0.7152 * g + 0.0722 * b
        Z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
        t = lambda v: v ** (1 / 3) if v > 0.008856 else 7.787 * v + 16 / 116  # noqa: E731
        return 116 * t(Y) - 16, 500 * (t(X) - t(Y)), 200 * (t(Y) - t(Z))

    colored = [c for c in bv.CAPAS
               if colorsys.rgb_to_hls(*[int(c[3][i:i + 2], 16) / 255 for i in (1, 3, 5)])[2] > 0.15]
    assert len(colored) >= 11
    for i, a in enumerate(colored):
        for b in colored[i + 1:]:
            assert math.dist(lab(a[3]), lab(b[3])) >= 20, (a[0], b[0])
    for name, capa in (('API trade', 'dinero'), ('API portfolio', 'dinero'), ('API voice', 'voz'),
                       ('API quote', 'vivo'), ('API crypto', 'vivo'), ('API news', 'vivo')):
        meta = _front_matter(_read(os.path.join(VAULT, 'API', name + '.md')))
        assert meta['capa'] == bv.CAPA[capa][1], name


def test_session_mentions_without_extension(bv):
    files = {'core/decide.py': {'role': 'code'}, 'matrix/engine.py': {'role': 'code'},
             'engine/statematrix.js': {'role': 'code'}, 'research/ask_agent.py': {'role': 'code'}}
    got = bv._mentions('`core/decide.chat_plan` manda; matrix/engine y engine/statematrix; research/ask_agent. '
                       'research/agents/ es una carpeta', files, {}, {})
    assert got == set(files)


def test_no_deprecation_and_honest_guide(bv):
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        assert bv.endpoint_ref('/api/x?y=1') == '/api/x'
    guide = _read(os.path.join(VAULT, '02 Cómo usar esta bóveda.md'))
    assert 'la primera vez' not in guide and 'necesita internet cada vez' in guide


def test_generator_is_deterministic_helpers(bv):
    """Nombres seguros y escapes de Markdown (no dependen de la hora ni del sistema)."""
    assert bv.safe_name('SESIÓN 2026-10-06: a/b <c> | d?') == 'SESIÓN 2026-10-06 - a-b c d'
    assert '[[' not in bv.prose('matriz [[1,2],[3,4]]')
    assert bv.prose('') == ''
    assert bv.endpoint_ref('◊/api/x/◊?y=1') == '/api/x/◊'
    routes = {'/api/brokerage/clients/<cid>': [], '/api/quote/<t>': []}
    assert bv.match_routes('/api/quote/', routes) == ['/api/quote/<t>']
    assert bv.match_routes('/api/brokerage', routes) == ['/api/brokerage/clients/<cid>']
    assert bv.match_routes('/api/brokerage', routes, prefix=False) == []
