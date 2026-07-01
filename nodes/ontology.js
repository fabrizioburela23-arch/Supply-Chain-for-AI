// nodes/ontology.js — Ontología (estilo Palantir) para Khipus AI Finance
// Define TIPOS DE OBJETO (más allá de "empresa") y TIPOS DE RELACIÓN tipadas,
// además de los objetos no-empresa (tecnologías, políticas, países, energía,
// materiales, productos, organismos). Las empresas siguen viniendo de NODE_BY_ID.
// El Grafo Temporal resuelve entidades desde NODE_BY_ID + ONTOLOGY._byId.

window.ONTOLOGY = {
  // Tipos de objeto: color + icono para el grafo y la leyenda.
  types: {
    Company:  { label: 'Empresa',    color: '#a78bfa', icon: '🏢' },
    Tech:     { label: 'Tecnología', color: '#38bdf8', icon: '⚙️' },
    Policy:   { label: 'Política',   color: '#f87171', icon: '📜' },
    Country:  { label: 'País',       color: '#fbbf24', icon: '🌍' },
    Energy:   { label: 'Energía',    color: '#4ade80', icon: '🔌' },
    Material: { label: 'Material',   color: '#22d3ee', icon: '⛏️' },
    Product:  { label: 'Producto',   color: '#fb923c', icon: '📦' },
    Org:      { label: 'Organismo',  color: '#c084fc', icon: '🏛️' },
  },
  // Tipos de relación: verbo + color para las aristas.
  rels: {
    fabrica:   { label: 'fabrica',      color: '#60a5fa' },
    abastece:  { label: 'abastece a',   color: '#4ade80' },
    usa:       { label: 'usa',          color: '#38bdf8' },
    invierte:  { label: 'invierte en',  color: '#fbbf24' },
    sanciona:  { label: 'sanciona',     color: '#ef4444' },
    restringe: { label: 'restringe',    color: '#f87171' },
    controla:  { label: 'controla',     color: '#fb923c' },
    depende:   { label: 'depende de',   color: '#c084fc' },
    energiza:  { label: 'da energía a', color: '#34d399' },
    alberga:   { label: 'alberga',      color: '#eab308' },
    compite:   { label: 'compite con',  color: '#fb7185' },
    domina:    { label: 'domina',       color: '#a78bfa' },
  },
  // Objetos NO-empresa (las empresas ya están en NODE_BY_ID).
  objects: [
    // ── Tecnologías ──────────────────────────────────────────────────────────
    { id: 'ONT_EUV',        type: 'Tech', label: 'Litografía EUV' },
    { id: 'ONT_HighNA',     type: 'Tech', label: 'EUV High-NA' },
    { id: 'ONT_DUV',        type: 'Tech', label: 'Litografía DUV' },
    { id: 'ONT_HBM',        type: 'Tech', label: 'Memoria HBM' },
    { id: 'ONT_HBM3e',      type: 'Tech', label: 'HBM3e' },
    { id: 'ONT_CoWoS',      type: 'Tech', label: 'Empaquetado CoWoS' },
    { id: 'ONT_2nm',        type: 'Tech', label: '2nm / GAA' },
    { id: 'ONT_CUDA',       type: 'Tech', label: 'CUDA (software)' },
    { id: 'ONT_SiC',        type: 'Tech', label: 'Carburo de silicio (SiC)' },
    { id: 'ONT_GaN',        type: 'Tech', label: 'Nitruro de galio (GaN)' },
    // ── Materiales ───────────────────────────────────────────────────────────
    { id: 'ONT_RareEarths', type: 'Material', label: 'Tierras raras' },
    { id: 'ONT_Gallium',    type: 'Material', label: 'Galio' },
    { id: 'ONT_Germanium',  type: 'Material', label: 'Germanio' },
    { id: 'ONT_Photoresist',type: 'Material', label: 'Fotoresinas' },
    { id: 'ONT_Wafer',      type: 'Material', label: 'Obleas de silicio' },
    // ── Políticas ────────────────────────────────────────────────────────────
    { id: 'ONT_EntityList', type: 'Policy', label: 'US Entity List' },
    { id: 'ONT_AIControls', type: 'Policy', label: 'Controles chips IA (BIS)' },
    { id: 'ONT_CHIPSAct',   type: 'Policy', label: 'CHIPS Act (EE.UU.)' },
    { id: 'ONT_GaGeBan',    type: 'Policy', label: 'Veto China Ga/Ge' },
    { id: 'ONT_DUVBan',     type: 'Policy', label: 'Restricción DUV a China' },
    // ── Países ───────────────────────────────────────────────────────────────
    { id: 'ONT_China',      type: 'Country', label: 'China' },
    { id: 'ONT_Taiwan',     type: 'Country', label: 'Taiwán' },
    { id: 'ONT_USA',        type: 'Country', label: 'EE.UU.' },
    { id: 'ONT_Korea',      type: 'Country', label: 'Corea del Sur' },
    { id: 'ONT_Japan',      type: 'Country', label: 'Japón' },
    { id: 'ONT_NL',         type: 'Country', label: 'Países Bajos' },
    // ── Energía ──────────────────────────────────────────────────────────────
    { id: 'ONT_SMR',        type: 'Energy', label: 'Reactores SMR' },
    { id: 'ONT_Fusion',     type: 'Energy', label: 'Fusión nuclear' },
    { id: 'ONT_Grid',       type: 'Energy', label: 'Energía datacenters' },
    // ── Productos ────────────────────────────────────────────────────────────
    { id: 'ONT_Blackwell',  type: 'Product', label: 'GPU Blackwell' },
    { id: 'ONT_TPU',        type: 'Product', label: 'Google TPU' },
    // ── Organismos ───────────────────────────────────────────────────────────
    { id: 'ONT_BIS',        type: 'Org', label: 'BIS (Comercio EE.UU.)' },
  ],
};

// Índice por id para resolución rápida.
window.ONTOLOGY._byId = {};
window.ONTOLOGY.objects.forEach(function (o) { window.ONTOLOGY._byId[o.id] = o; });
