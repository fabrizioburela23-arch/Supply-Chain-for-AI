// scripts/export_graph_v0.js — Fase 0: exporta el grafo actual (embebido en
// app.html + nodes/*.js) a data/grafo_v0.json, replicando EXACTAMENTE la
// lógica de merge/alias que corre en el navegador (mismo orden de carga que
// los <script src> de app.html, mismos alias de NODE_ID_ALIAS, mismo filtro
// de LINKS). Es una herramienta de un solo uso para congelar el snapshot de
// migración — no forma parte del backend en producción.
//
// Uso: node scripts/export_graph_v0.js

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const sandbox = {};
sandbox.window = sandbox; // igual que en el navegador: window === global scope
sandbox.console = console;
// Stub mínimo de localStorage: el excerpt de app.html lee prefs (LANG, etc.)
// al cargar. Solo necesitamos que no lance error; los valores no importan
// para exportar el grafo.
const _ls = new Map();
sandbox.localStorage = {
  getItem: k => (_ls.has(k) ? _ls.get(k) : null),
  setItem: (k, v) => _ls.set(k, String(v)),
  removeItem: k => _ls.delete(k),
};
// Stub genérico de DOM: el excerpt tiene un par de líneas incidentales de UI
// (ej. document.body.classList.add(...) al fijar el tema) que no afectan a los
// datos que exportamos. Un Proxy "que traga todo" evita enumerar cada API DOM
// una por una — cualquier propiedad/llamada devuelve otro stub inocuo.
function makeDomStub() {
  const handler = {
    get(_target, prop) {
      if (prop === Symbol.toPrimitive || prop === 'toString' || prop === 'valueOf') return () => '';
      if (prop === 'then') return undefined; // no confundir con una Promise
      return stubFn;
    },
    apply() { return stub; },
  };
  const stubFn = new Proxy(function () {}, handler);
  const stub = new Proxy({}, handler);
  return stub;
}
sandbox.document = makeDomStub();
const ctx = vm.createContext(sandbox);

function run(code, label) {
  try {
    vm.runInContext(code, ctx, { filename: label });
  } catch (e) {
    console.error(`[export_graph_v0] ERROR ejecutando ${label}: ${e.message}`);
    throw e;
  }
}

function runFile(relPath) {
  const p = path.join(ROOT, relPath);
  run(fs.readFileSync(p, 'utf8'), relPath);
}

// 1) Mismo orden de <script src> que app.html (líneas 1289-1298 + 8530-8533)
[
  'nodes/nodes_expand.js',
  'nodes/nodes_expand2.js',
  'nodes/nodes_spacex.js',
  'nodes/nodes_expand3.js',
  'nodes/nodes_nuclear.js',
  'nodes/nodes_expand4.js',
  'nodes/preipo_intel.js',
  'nodes/links_all.js',
  'nodes/links_expand.js',
  'nodes/links_connect.js',
  'nodes/temporal_seed_facts.js',
  'nodes/temporal_seed_facts2.js',
  'nodes/ontology.js',
  'nodes/ontology_facts.js',
].forEach(runFile);

// 2) El bloque inline de app.html que define CATS, NODES (core), NODE_BY_ID,
//    los merges NODES_EXPAND*/NODES_SPACEX/NODES_NUCLEAR, NODE_ID_ALIAS,
//    RAW_LINKS (core) + merges LINKS_EXPAND/SPACEX/CONNECT/NUCLEAR/EXPAND4,
//    y la construcción final de LINKS. Verificado (Fase 0): sin llamadas DOM
//    de nivel superior en este rango — es solo definición de datos.
const appHtml = fs.readFileSync(path.join(ROOT, 'app.html'), 'utf8');
const lines = appHtml.split('\n');
// líneas 2153..4861 (1-indexed) = CATS ... window.LINKS = LINKS;
const excerpt = lines.slice(2152, 4861).join('\n');
run(excerpt, 'app.html:2153-4861 (excerpt)');

// 3) Extraer los datos ya mergeados (todo vive en window === ctx)
const NODES = ctx.NODES || [];
const LINKS = ctx.LINKS || [];
const CATS = ctx.CATS || {};
const CATS_NEW = ctx.CATS_NEW || {};
const PREIPO_INTEL = ctx.PREIPO_INTEL || {};
const TEMPORAL_SEED_FACTS = ctx.TEMPORAL_SEED_FACTS || [];
const ONTOLOGY = ctx.ONTOLOGY || { types: {}, rels: {}, objects: [] };

if (!NODES.length) throw new Error('NODES vacío tras el merge — revisar el rango de líneas del excerpt');
if (!LINKS.length) throw new Error('LINKS vacío tras el merge — revisar el rango de líneas del excerpt');

const out = {
  exported_at: null, // se completa fuera de vm (Date.now real, no el shim del sandbox)
  source: 'app.html + nodes/*.js (snapshot pre-ontología, Fase 0)',
  counts: {
    nodes: NODES.length,
    links: LINKS.length,
    categories: Object.keys(CATS).length + Object.keys(CATS_NEW).length,
    preipo_entries: Object.keys(PREIPO_INTEL).length,
    temporal_facts: TEMPORAL_SEED_FACTS.length,
    ontology_objects: ONTOLOGY.objects.length,
  },
  nodes: NODES,
  links: LINKS,
  categories: Object.assign({}, CATS, CATS_NEW),
  preipo_intel: PREIPO_INTEL,
  temporal_facts: TEMPORAL_SEED_FACTS,
  ontology: ONTOLOGY,
};
out.exported_at = new Date().toISOString();

const outPath = path.join(ROOT, 'data', 'grafo_v0.json');
fs.writeFileSync(outPath, JSON.stringify(out, null, 2));

console.log('✅ grafo_v0.json escrito en', outPath);
console.log('   nodos:', out.counts.nodes, '| links:', out.counts.links,
  '| categorías:', out.counts.categories, '| pre-IPO:', out.counts.preipo_entries,
  '| hechos temporales:', out.counts.temporal_facts, '| objetos ontología:', out.counts.ontology_objects);
