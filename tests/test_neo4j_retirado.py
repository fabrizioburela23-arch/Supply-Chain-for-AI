"""tests/test_neo4j_retirado.py — Neo4j se RETIRÓ el 2026-10-13 (decisión #6 de Fabrizio, docs/BRECHAS_V2.md §2).

Nadie lo leía: solo recibía hechos (POST /api/grafo/seed) y el 🩺 probaba la conexión. Postgres es la única base
(docs/ARQUITECTURA_V2.md): la memoria temporal vive en la ontología bitemporal y el Grafo Temporal es NATIVO.
Esta prueba es estática (lee el código, sin red ni base) y vigila que no vuelva por la puerta de atrás:

  1. ningún módulo importa el driver `neo4j` ni lee variables `NEO4J_*`;
  2. requirements.txt / constraints.txt no lo instalan;
  3. el servidor ya no tiene POST /api/grafo/seed y /api/grafo/estado dice siempre 'native', sin campos de Neo4j;
  4. el cliente ya no siembra ni pinta insignias de Neo4j.

Se excluyen docs/, vault/ (generada) y tests/ (que lo nombran para vigilarlo).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

_SKIP_DIRS = {'.git', 'vault', 'docs', 'tests', 'node_modules', '__pycache__', '.venv', 'venv'}
_CODE_EXT = ('.py', '.js', '.html', '.yml', '.yaml', '.toml', '.cfg', '.ini', '.sh', '.json')
_CODE_NAMES = ('Dockerfile', 'Procfile', 'requirements.txt', 'constraints.txt', 'requirements-dev.txt')

# Uso real en el código (no un comentario que cuente la historia, que va con «Neo4j» en mayúscula):
# importar el driver, leer NEO4J_*, identificadores _neo4j…/neo4j_…, neo4j.<algo> o la cadena 'neo4j'.
_USE = re.compile(r"(?:^|\s)(?:import|from)\s+neo4j\b|NEO4J_|[A-Za-z_]neo4j|neo4j_|neo4j\.|['\"`]neo4j", re.M)


def _code_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith('.') or d == '.github']
        for fn in filenames:
            if fn.endswith(_CODE_EXT) or fn in _CODE_NAMES:
                yield os.path.join(dirpath, fn)


def test_ningun_codigo_importa_ni_lee_neo4j():
    hits = []
    for path in _code_files():
        try:
            text = open(path, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        for m in _USE.finditer(text):
            line = text.count('\n', 0, m.start()) + 1
            hits.append(f'{os.path.relpath(path, ROOT)}:{line}: {m.group(0).strip()}')
    assert not hits, ('Neo4j se retiró (decisión #6, 2026-10-13) y no se reintroduce — Postgres es la única base. '
                      'Uso encontrado:\n  ' + '\n  '.join(hits[:30]))


def test_dependencias_sin_neo4j():
    for fn in ('requirements.txt', 'constraints.txt'):
        text = open(os.path.join(ROOT, fn), encoding='utf-8').read().lower()
        assert 'neo4j' not in text, f'{fn} todavía instala o nombra neo4j'
    # pytz solo lo traía el driver de neo4j
    assert 'pytz' not in open(os.path.join(ROOT, 'constraints.txt'), encoding='utf-8').read()


def test_servidor_sin_seed_y_estado_nativo():
    import server
    rules = {r.rule: (r.methods or set()) for r in server.app.url_map.iter_rules()}
    assert '/api/grafo/seed' not in rules, 'POST /api/grafo/seed escribía en Neo4j: se borró con él'
    for name in ('_temporal_mode', '_neo4j_available', '_get_neo4j_driver', '_neo4j_add_fact', '_neo4j_estado_cache',
                 'NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD'):
        assert not hasattr(server, name), f'server.{name} sigue existiendo'
    r = server.app.test_client().get('/api/grafo/estado')
    assert r.status_code == 200 and r.get_json() == {'store': 'native'}
    card = server._diag_grafo()
    assert card['ok'] is True and card['store'] == 'native' and 'fix_es' not in card
    assert 'neo4j' not in (card['detail'] + card['detail_en']).lower()
    assert 'Postgres' in card['detail'] and 'Postgres' in card['detail_en']


def test_cliente_sin_siembra_ni_insignia_neo4j():
    js = open(os.path.join(ROOT, 'engine', 'temporal-graph.js'), encoding='utf-8').read()
    for bad in ('_seedBackend', '/api/grafo/seed', 'neo4j_connected', 'tkg_seeded_neo4j'):
        assert bad not in js, bad
    # la insignia nativa sigue, en los dos idiomas (regla bilingüe)
    assert "storeNative: { es: 'memoria: nativa', en: 'memory: native' }" in js
    html = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    assert 'neo4j' not in html.lower()
