/**
 * GraphView — Grafo 2D con d3-force (migración del grafo D3 de app.html).
 *
 * Datos: intenta `GET /api/ontology/graph` (vía api/client.js); si el server
 * no está, cae al snapshot local `data/grafo_v0.json` (555 nodos / 1623 links).
 * Colores por macro-sector: usa `sectors9` + `cat_to_sector` DEL payload o del
 * snapshot — nunca listas propias (regla 4 de MIGRATION.md: el vocabulario de
 * relaciones viene del VocabularyContext; los sectores viajan con el grafo).
 *
 * D3 es dueño del DOM dentro del <svg> (patrón clásico: join + ticked);
 * React es dueño del estado (carga, error, nodo seleccionado, tarjeta).
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  forceCenter,
  forceLink,
  forceManyBody,
  forceSimulation,
  select,
  zoom as d3zoom,
} from 'd3';
import { get } from '../api/client.js';
import { useVocabulary, relLabel } from '../context/VocabularyContext.jsx';
import snapshot from '../data/grafo_v0.json';

/** Dimensiones lógicas del lienzo (el svg escala con viewBox → responsivo). */
const W = 960;
const H = 640;

/** Color de reserva para nodos sin sector catalogado. */
const FALLBACK_COLOR = '#7a8aa0';

/** Máximo de conexiones listadas en la tarjeta lateral. */
const MAX_CONNECTIONS = 12;

/**
 * @typedef {Object} GraphNode
 * @property {string} id
 * @property {string} label
 * @property {string} cat
 * @property {string} sector - Macro-sector (puede venir vacío; se resuelve via cat_to_sector).
 * @property {string} role - Descripción del rol (español).
 *
 * @typedef {Object} GraphLink
 * @property {string} source
 * @property {string} target
 * @property {number} w
 * @property {string} rel - Texto descriptivo de la relación.
 * @property {string} type - Tipo estructural ('supply', 'cloud', …).
 *
 * @typedef {Object} GraphData
 * @property {GraphNode[]} nodes
 * @property {GraphLink[]} links
 * @property {Object<string, {label?: string, es?: string, en?: string, color?: string}>} sectors9
 * @property {Object<string, string>} catToSector
 * @property {'api'|'snapshot'} origin
 */

/**
 * Normaliza un payload de grafo (API u snapshot) a la forma interna.
 * Tolerante con variantes de campo (props anidados de la ontología, s/t en
 * links) y filtra links colgantes (d3.forceLink lanza si falta un extremo).
 *
 * @param {any} payload
 * @param {'api'|'snapshot'} origin
 * @returns {GraphData|null} null si no trae nodos utilizables.
 */
export function normalizeGraph(payload, origin) {
  const rawNodes = Array.isArray(payload?.nodes) ? payload.nodes : [];
  if (!rawNodes.length) return null;

  const nodes = rawNodes
    .filter((n) => n && (n.id != null))
    .map((n) => {
      const p = n.props && typeof n.props === 'object' ? n.props : n;
      return {
        id: String(n.id),
        label: p.label || p.name || String(n.id),
        cat: p.cat || n.type || '',
        sector: p.sector || '',
        role: p.role || '',
      };
    });

  const ids = new Set(nodes.map((n) => n.id));
  const rawLinks = Array.isArray(payload?.links) ? payload.links : [];
  const links = rawLinks
    .map((l) => ({
      source: String(l.source ?? l.s ?? ''),
      target: String(l.target ?? l.t ?? ''),
      w: Number(l.w ?? l.weight ?? 1) || 1,
      rel: l.rel || '',
      type: l.type || l.rel_type || '',
    }))
    .filter((l) => ids.has(l.source) && ids.has(l.target));

  return {
    nodes,
    links,
    // Sectores: del payload si los trae; si no, los del snapshot (nunca listas propias).
    sectors9: payload?.sectors9 || snapshot.sectors9 || {},
    catToSector: payload?.cat_to_sector || snapshot.cat_to_sector || {},
    origin,
  };
}

/**
 * Panel del Grafo 2D: fuerzas d3, zoom/pan, color por sector, radio por grado
 * y tarjeta lateral al clicar un nodo.
 *
 * @returns {JSX.Element}
 */
export default function GraphView() {
  const { vocab } = useVocabulary();
  const svgRef = useRef(/** @type {SVGSVGElement|null} */ (null));
  const [graph, setGraph] = useState(/** @type {GraphData|null} */ (null));
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(/** @type {string|null} */ (null));

  // Carga: API viva primero, snapshot local como fallback.
  useEffect(() => {
    let alive = true;
    get('/api/ontology/graph')
      .then((payload) => {
        if (!alive) return;
        setGraph(normalizeGraph(payload, 'api') || normalizeGraph(snapshot, 'snapshot'));
        setLoading(false);
      })
      .catch(() => {
        if (!alive) return;
        setGraph(normalizeGraph(snapshot, 'snapshot'));
        setLoading(false);
      });
    return () => { alive = false; };
  }, []);

  /** Índices derivados — UNA sola pasada sobre nodes/links (no por nodo). */
  const indexes = useMemo(() => {
    const nodeById = new Map();
    const degree = new Map();
    /** @type {Map<string, Array<{otherId: string, type: string, rel: string, out: boolean}>>} */
    const adjacency = new Map();
    if (!graph) return { nodeById, degree, adjacency };
    for (const n of graph.nodes) {
      nodeById.set(n.id, n);
      degree.set(n.id, 0);
      adjacency.set(n.id, []);
    }
    for (const l of graph.links) {
      degree.set(l.source, (degree.get(l.source) || 0) + 1);
      degree.set(l.target, (degree.get(l.target) || 0) + 1);
      adjacency.get(l.source).push({ otherId: l.target, type: l.type, rel: l.rel, out: true });
      adjacency.get(l.target).push({ otherId: l.source, type: l.type, rel: l.rel, out: false });
    }
    return { nodeById, degree, adjacency };
  }, [graph]);

  /** Sector resuelto de un nodo (campo directo o via cat_to_sector). */
  const sectorOf = (node) => node.sector || graph?.catToSector?.[node.cat] || '';
  const sectorMeta = (sectorId) => graph?.sectors9?.[sectorId] || null;
  const colorOf = (node) => sectorMeta(sectorOf(node))?.color || FALLBACK_COLOR;
  const sectorName = (sectorId) => {
    const m = sectorMeta(sectorId);
    return (m && (m.es || m.label)) || sectorId || '—';
  };

  // Montaje D3: simulación + zoom. Se recrea si cambia el grafo; se limpia al desmontar.
  useEffect(() => {
    if (!graph || !svgRef.current) return;
    const { degree } = indexes;

    // Copias: d3 muta nodos (x/y) y links (source/target → objetos); el
    // snapshot importado y el estado React deben quedar intactos.
    const nodes = graph.nodes.map((n) => ({ ...n }));
    const links = graph.links.map((l) => ({ ...l }));

    const radius = (id) => 4 + Math.min(14, Math.sqrt(degree.get(id) || 0) * 1.6);

    const svg = select(svgRef.current);
    svg.selectAll('*').remove();
    const root = svg.append('g').attr('class', 'graph-root');

    const linkSel = root.append('g')
      .attr('stroke', '#39415a')
      .attr('stroke-opacity', 0.45)
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke-width', (d) => Math.min(3, 0.5 + d.w * 0.4));

    const nodeSel = root.append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', (d) => radius(d.id))
      .attr('fill', (d) => colorOf(d))
      .attr('stroke', '#0b0e17')
      .attr('stroke-width', 1)
      .attr('data-node-id', (d) => d.id)
      .style('cursor', 'pointer')
      .on('click', (_event, d) => setSelectedId(d.id));

    nodeSel.append('title').text((d) => d.label);

    const ticked = () => {
      linkSel
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y);
      nodeSel
        .attr('cx', (d) => d.x)
        .attr('cy', (d) => d.y);
    };

    const sim = forceSimulation(nodes)
      .force('link', forceLink(links).id((d) => d.id).distance(55)
        .strength((l) => Math.min(1, l.w / 4)))
      .force('charge', forceManyBody().strength(-70))
      .force('center', forceCenter(W / 2, H / 2))
      .on('tick', ticked);

    // Posiciones iniciales visibles aunque aún no haya corrido ningún tick
    // (forceSimulation ya asigna x/y al construirse).
    ticked();

    const zoomBehavior = d3zoom()
      .scaleExtent([0.2, 8])
      .on('zoom', (event) => root.attr('transform', event.transform));
    svg.call(zoomBehavior);

    return () => {
      sim.stop();
      svg.on('.zoom', null);
      svg.selectAll('*').remove();
    };
    // colorOf/sectorOf derivan solo de `graph`, ya en deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph, indexes]);

  const selected = selectedId ? indexes.nodeById.get(selectedId) : null;
  const connections = selected
    ? (indexes.adjacency.get(selected.id) || []).slice(0, MAX_CONNECTIONS)
    : [];

  if (loading) {
    return (
      <div className="panel-card">
        <h3>Grafo 2D</h3>
        <div className="loading">Cargando el grafo…</div>
      </div>
    );
  }

  if (!graph || !graph.nodes.length) {
    return (
      <div className="panel-card">
        <h3>Grafo 2D</h3>
        <div className="error-box" role="alert">
          No se pudo cargar el grafo: ni el servidor ni el snapshot local
          trajeron nodos.
        </div>
      </div>
    );
  }

  return (
    <div className="panel-card">
      <h3>
        Grafo 2D{' '}
        <small style={{ fontWeight: 'normal', opacity: 0.65 }}>
          {graph.nodes.length} nodos · {graph.links.length} relaciones ·{' '}
          {graph.origin === 'api' ? 'datos vivos' : 'snapshot local'}
        </small>
      </h3>
      <div style={{ position: 'relative' }}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="xMidYMid meet"
          style={{
            width: '100%',
            height: 'auto',
            display: 'block',
            background: '#0b0e17',
            borderRadius: 8,
          }}
          role="img"
          aria-label="Grafo de la cadena de suministro"
        />
        {selected && (
          <aside
            data-testid="graph-card"
            style={{
              position: 'absolute',
              top: 8,
              right: 8,
              width: 'min(300px, 80%)',
              maxHeight: 'calc(100% - 16px)',
              overflowY: 'auto',
              background: 'rgba(13, 17, 28, 0.95)',
              border: `1px solid ${colorOf(selected)}`,
              borderRadius: 8,
              padding: '10px 12px',
              fontSize: 13,
            }}
          >
            <button
              type="button"
              onClick={() => setSelectedId(null)}
              aria-label="Cerrar tarjeta"
              style={{
                float: 'right',
                background: 'none',
                border: 'none',
                color: 'inherit',
                cursor: 'pointer',
                fontSize: 14,
              }}
            >
              ✕
            </button>
            <h4 style={{ margin: '0 0 4px' }}>{selected.label}</h4>
            <div style={{ color: colorOf(selected), marginBottom: 6 }}>
              {sectorName(sectorOf(selected))}
            </div>
            {selected.role && (
              <p style={{ margin: '0 0 8px', opacity: 0.85 }}>{selected.role}</p>
            )}
            <strong>Conexiones</strong>{' '}
            <span style={{ opacity: 0.65 }}>
              ({indexes.degree.get(selected.id) || 0}
              {(indexes.degree.get(selected.id) || 0) > MAX_CONNECTIONS
                ? `, mostrando ${MAX_CONNECTIONS}`
                : ''})
            </span>
            <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
              {connections.map((c, i) => {
                const other = indexes.nodeById.get(c.otherId);
                return (
                  <li key={`${c.otherId}-${i}`} style={{ marginBottom: 2 }}>
                    {c.out ? '→' : '←'} {other ? other.label : c.otherId}{' '}
                    <span style={{ opacity: 0.65 }}>
                      · {relLabel(vocab, c.type)}
                    </span>
                  </li>
                );
              })}
              {!connections.length && (
                <li style={{ opacity: 0.65 }}>Sin conexiones registradas.</li>
              )}
            </ul>
          </aside>
        )}
      </div>
    </div>
  );
}
