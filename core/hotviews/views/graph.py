"""Vista `graph` (V1, parte de lectura — INFRA_OPERATIVA §4.7, paso 8): el grafo en la forma del CATÁLOGO para
los 13 lectores del servidor (core/world, core/entities, core/screener, core/sim_agents, core/semantic,
core/portfolio_ai, research/router, research/context, matrix/tensor, mcp_server/tools).

Antes cada uno abría data/grafo_v0.json por su cuenta y lo guardaba PARA SIEMPRE: una empresa creada con
IncorporarEmpresa no aparecía en ninguno, y cada uno tenía "su" versión del grafo. Ahora todos leen ESTA vista
de la generación vigente (core/hotviews/hot.graph()): Postgres cuando existe, el snapshot si no, con el mismo
código; sus cachés se claves con la generación (`hot.cached`), así que una escritura económica los renueva.

Es INMUTABLE: los nodos y vínculos son `FrozenDict` (un dict que no se deja modificar; `dict(x)` da una copia
normal), las tablas son `MappingProxyType` y las listas, tuplas. Quien necesite cambiar algo, copia.
"""
import copy
import hashlib
import json
import time
from types import MappingProxyType

READ_ONLY_MSG = ('vista del grafo de solo lectura (core/hotviews): copia con dict(x) antes de modificar / '
                 'read-only graph view: copy with dict(x) before changing it')


class FrozenDict(dict):
    """dict de solo lectura. json.dumps, {**x}, dict(x), copy/deepcopy y pickle dan dicts normales."""
    __slots__ = ()

    def _ro(self, *a, **k):
        raise TypeError(READ_ONLY_MSG)

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _ro

    def copy(self):
        return dict(self)

    def __copy__(self):
        return dict(self)

    def __deepcopy__(self, memo):
        return copy.deepcopy(dict(self), memo)

    def __reduce__(self):
        return (dict, (dict(self),))

    def __hash__(self):          # dict no es hasheable; tampoco esto (evita que alguien lo use de clave)
        raise TypeError('unhashable type: FrozenDict')


def freeze(x):
    if isinstance(x, FrozenDict):
        return x
    if isinstance(x, dict):
        return FrozenDict((k, freeze(v)) for k, v in x.items())
    if isinstance(x, (list, tuple)):
        return tuple(freeze(v) for v in x)
    if isinstance(x, (set, frozenset)):
        return frozenset(freeze(v) for v in x)
    return x


class GraphView:
    """El grafo de lectura de UNA generación. Atributos de solo lectura (ver el docstring del módulo)."""
    __slots__ = ('nodes', 'by_id', 'links', 'alias', 'catalog', 'flow_degree', 'coverage', 'stats',
                 'content_sha', 'n_nodes', 'n_links', 'build_ms', '_gen', '_fallback', '_snapshot')

    # ── la generación a la que pertenece (se fija UNA vez, antes de publicarla) ──
    def attach(self, g, fallback=False):
        if getattr(self, '_gen', None) is not None and self._gen is not g:
            raise TypeError(READ_ONLY_MSG)
        object.__setattr__(self, '_gen', g)
        object.__setattr__(self, '_fallback', bool(fallback))
        return self

    @property
    def generation_obj(self):
        return self._gen

    @property
    def generation(self):
        return self._gen.id if self._gen is not None else None

    @property
    def graph_version(self):
        return self._gen.graph_version if self._gen is not None else None

    @property
    def source(self):
        return self._gen.source if self._gen is not None else None

    @property
    def lineage(self):
        return self._gen.lineage if self._gen is not None else None

    @property
    def built_at(self):
        return self._gen.built_at if self._gen is not None else None

    @property
    def fallback(self):
        """True = la generación publicada no servía (base sin el catálogo, caída o calentando) y los lectores
        usan el snapshot por su cuenta (marcado stale si hay base configurada)."""
        return bool(self._fallback)

    @property
    def core(self):
        return self._gen.views.get('graph_core') if self._gen is not None else None

    @property
    def impact(self):
        return self._gen.views.get('impact') if self._gen is not None else None

    @property
    def stale(self):
        if self._gen is None:
            return True
        if self._fallback:
            try:
                from ontology.db import ontology_available
                return bool(ontology_available())
            except Exception:  # noqa: BLE001
                return True
        from core.hotviews import registry
        return bool(registry.lag(self._gen)[1])

    @property
    def snapshot(self):
        """Mapping con la forma de data/grafo_v0.json (nodes, links, node_id_alias, sectors9, categories,
        legal_names, preipo_intel, cat_to_sector, counts, exported_at) — para el código que ya leía ese dict."""
        return self._snapshot

    def node(self, oid):
        return self.by_id.get(oid)

    def canonical(self, oid, hops=5):
        """Sigue la tabla de alias (catálogo + fusiones de la base) hasta el id canónico."""
        seen = set()
        while oid in self.alias and hops > 0 and oid not in seen:
            seen.add(oid)
            oid = self.alias[oid]
            hops -= 1
        return oid

    def meta(self):
        """Lo que cada lector puede reportar de su fuente (sin cuerpos)."""
        return {'generation': self.generation, 'graph_version': self.graph_version, 'source': self.source,
                'lineage': self.lineage, 'built_at': self.built_at, 'fallback': self.fallback,
                'stale': self.stale, 'nodes': self.n_nodes, 'links': self.n_links,
                'coverage': self.coverage, 'content_sha': self.content_sha}

    def __setattr__(self, k, v):
        if getattr(self, '_gen', None) is not None or k in ('_gen', '_fallback'):
            raise TypeError(READ_ONLY_MSG)
        object.__setattr__(self, k, v)


def build(data):
    """GraphData → GraphView, o None si la foto no trae el grafo de lectura (data.nodes is None)."""
    nodes_in = getattr(data, 'nodes', None)
    if nodes_in is None:
        return None
    from ontology import vocabulary as vocab
    t0 = time.perf_counter()
    cat = dict(getattr(data, 'catalog', None) or {})
    v = GraphView.__new__(GraphView)
    object.__setattr__(v, '_gen', None)
    object.__setattr__(v, '_fallback', False)
    nodes = tuple(freeze(n) for n in nodes_in if n.get('id'))
    by_id = {}
    for n in nodes:
        by_id.setdefault(n['id'], n)
    links = tuple(freeze(l) for l in (getattr(data, 'links', None) or ()))
    alias = dict(cat.get('node_id_alias') or {})
    v.nodes = nodes
    v.by_id = MappingProxyType(by_id)
    v.links = links
    v.alias = MappingProxyType(alias)
    meta = {k: freeze(cat.get(k)) for k in ('sectors9', 'categories', 'cat_to_sector', 'legal_names',
                                              'preipo_intel', 'counts', 'exported_at', 'source', 'snapshot_sha',
                                              'voice_aliases', 'resolve_stopwords')}
    v.catalog = FrozenDict(meta)
    v.flow_degree = MappingProxyType(dict(vocab.flow_degree(links)))
    cids = cat.get('catalog_ids') or frozenset()
    v.coverage = round(len(cids & set(by_id)) / len(cids), 4) if cids else 1.0
    stats = dict(cat.get('stats') or {})
    miss = list(stats.get('missing_from_db') or [])
    stats['missing_from_db_n'] = len(miss)
    stats['missing_from_db'] = miss[:25]
    v.stats = freeze(stats)
    v.n_nodes, v.n_links = len(nodes), len(links)
    h = hashlib.sha256()
    h.update(json.dumps([nodes, links, sorted(alias.items())], sort_keys=True, default=str).encode())
    v.content_sha = h.hexdigest()
    snap = {'nodes': nodes, 'links': links, 'node_id_alias': v.alias}
    for k in ('sectors9', 'categories', 'cat_to_sector', 'legal_names', 'preipo_intel', 'counts', 'exported_at',
              'voice_aliases', 'resolve_stopwords'):
        snap[k] = meta[k] if meta[k] is not None else (FrozenDict() if k not in ('exported_at',) else None)
    v._snapshot = MappingProxyType(snap)
    v.build_ms = round((time.perf_counter() - t0) * 1000, 1)
    return v


def status(v):
    if v is None:
        return None
    return {'nodes': v.n_nodes, 'links': v.n_links, 'coverage': v.coverage, 'content_sha': v.content_sha,
            'build_ms': v.build_ms, 'fallback': v.fallback, 'stats': dict(v.stats)}
