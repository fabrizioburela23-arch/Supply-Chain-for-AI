#!/usr/bin/env node
/* ============================================================================
   scripts/link_origins.js — ¿de qué arreglo del catálogo viene cada vínculo?
   (BRECHAS_V2 L3-11 / PROP-14, bloque 5: revisión de la escala de pesos.)

   El catálogo mezcla DOS escalas de peso: la mayoría de los arreglos usa 1-6 y
   LINKS_EXPAND5 (nodes/nodes_expand5.js) usa 0-1. El snapshot (data/grafo_v0.json)
   ya no dice de dónde vino cada fila, así que un peso 1 es ambiguo. Este
   ayudante carga los MISMOS archivos que scripts/export_graph_v0.js (sin
   ejecutar el merge) y lista, por fila cruda, su arreglo de origen con los ids
   ya resueltos por NODE_ID_ALIAS. Lo usa scripts/build_graph_review.py.

   Uso:  node scripts/link_origins.js   → JSON por stdout. Sin red, determinista.
   ============================================================================ */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { DATA_FILES } = require('./export_graph_v0.js');

const ROOT = path.join(__dirname, '..');
// mismo orden que buildSnapshot (RAW_LINKS primero; luego linkArrays)
const ARRAYS = ['RAW_LINKS', 'LINKS_EXPAND', 'LINKS_SPACEX', 'LINKS_CONNECT', 'LINKS_NUCLEAR',
  'LINKS_EXPAND4', 'LINKS_EXPAND5', 'LINKS_CHINA', 'LINKS_MULTICAPA'];

function origins() {
  const ctx = vm.createContext({ window: {}, console: { log() {}, warn() {}, error() {} } });
  for (const f of DATA_FILES) {
    if (f === 'nodes/merge_graph.js') continue;
    vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf-8'), ctx, { filename: f });
  }
  const g = n => vm.runInContext(
    `typeof ${n} !== 'undefined' ? ${n} : (window.${n} !== undefined ? window.${n} : null)`, ctx);
  const ALIAS = g('NODE_ID_ALIAS') || {};
  const resolve = (id) => { let cur = id, hops = 0; while (ALIAS[cur] !== undefined && hops++ < 5) cur = ALIAS[cur]; return cur; };
  const rows = [];
  const summary = {};
  for (const name of ARRAYS) {
    const arr = g(name) || [];
    const h = { n: arr.length, lt1: 0, eq1: 0, gt1: 0 };
    arr.forEach(function (l) {
      // misma normalización que merge_graph.js (w ausente → 2; type ausente → supply)
      const raw = Array.isArray(l) ? [l[0], l[1], l[2] || 2, l[4] || 'supply'] : [l.s, l.t, l.w || 2, l.type || 'supply'];
      const w = +raw[2];
      if (w < 1) h.lt1++; else if (w === 1) h.eq1++; else h.gt1++;
      rows.push([resolve(raw[0]), resolve(raw[1]), raw[3], w, name]);
    });
    summary[name] = h;
  }
  return { arrays: summary, rows: rows };
}

if (require.main === module) {
  process.stdout.write(JSON.stringify(origins()));
}

module.exports = { origins, ARRAYS };
