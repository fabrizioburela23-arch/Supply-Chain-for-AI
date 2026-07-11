#!/usr/bin/env node
/* ============================================================================
   scripts/export_graph_v0.js — Exporta el grafo canónico a data/grafo_v0.json
   v2 (Etapa 2, 2026-07): carga los nodes/*.js reales en un sandbox vm y usa
   LA MISMA función de merge que el navegador (nodes/merge_graph.js).
   La versión anterior ejecutaba app.html por rangos de línea HARDCODEADOS
   que se desfasaban con cada edición — eliminada.

   Uso:  node scripts/export_graph_v0.js
   ============================================================================ */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const ctx = vm.createContext({ window: {}, console });

const DATA_FILES = [
  'nodes/nodes_seed.js',
  'nodes/nodes_expand.js', 'nodes/nodes_expand2.js', 'nodes/nodes_spacex.js',
  'nodes/nodes_expand3.js', 'nodes/nodes_nuclear.js', 'nodes/nodes_expand4.js',
  'nodes/nodes_expand5.js',
  'nodes/preipo_intel.js',
  'nodes/links_all.js', 'nodes/links_expand.js', 'nodes/links_connect.js',
  'nodes/temporal_seed_facts.js', 'nodes/temporal_seed_facts2.js',
  'nodes/ontology.js', 'nodes/ontology_facts.js',
  'nodes/merge_graph.js',
];
for (const f of DATA_FILES) {
  vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf-8'), ctx, { filename: f });
}
const g = n => vm.runInContext(
  `typeof ${n} !== 'undefined' ? ${n} : (window.${n} !== undefined ? window.${n} : null)`, ctx);

const NODES = g('NODES');
const NODE_BY_ID = {};
NODES.forEach(n => { NODE_BY_ID[n.id] = n; });

const result = g('buildKhipusGraph')({
  NODES, NODE_BY_ID,
  NODE_ID_ALIAS: g('NODE_ID_ALIAS'),
  RAW_LINKS: g('RAW_LINKS'),
  expansions: ['NODES_EXPAND', 'NODES_EXPAND2', 'NODES_SPACEX', 'NODES_EXPAND3',
               'NODES_NUCLEAR', 'NODES_EXPAND4', 'NODES_EXPAND5'].map(g),
  linkArrays: ['LINKS_EXPAND', 'LINKS_SPACEX', 'LINKS_CONNECT', 'LINKS_NUCLEAR',
               'LINKS_EXPAND4', 'LINKS_EXPAND5'].map(g),
  warn: m => console.warn('⚠', m),
});

const CATS = Object.assign({}, g('CATS'), g('CATS_NEW'));
const CAT_TO_SECTOR = g('CAT_TO_SECTOR');
const W = g('window');
const out = {
  exported_at: new Date().toISOString(),
  source: 'nodes/*.js vía nodes/merge_graph.js (misma implementación que el navegador)',
  counts: {
    nodes: NODES.length,
    links: result.LINKS.length,
    categories: Object.keys(CATS).length,
    sectors: Object.keys(g('SECTORS9') || {}).length,
    preipo_entries: Object.keys(g('PREIPO_INTEL') || {}).length,
    temporal_facts: (W.TEMPORAL_SEED_FACTS || []).length,
    ontology_objects: ((W.ONTOLOGY || {}).objects || []).length,
  },
  nodes: NODES.map(n => Object.assign({ sector: CAT_TO_SECTOR[n.cat] || 'cloud_ia' }, n)),
  links: result.LINKS,
  categories: CATS,
  sectors9: g('SECTORS9'),
  cat_to_sector: CAT_TO_SECTOR,
  preipo_intel: g('PREIPO_INTEL') || {},
  temporal_facts: W.TEMPORAL_SEED_FACTS || [],
  ontology: W.ONTOLOGY || null,
};

const outPath = path.join(ROOT, 'data', 'grafo_v0.json');
fs.writeFileSync(outPath, JSON.stringify(out, null, 1), 'utf-8');
console.log('✓ data/grafo_v0.json —', JSON.stringify(out.counts));
