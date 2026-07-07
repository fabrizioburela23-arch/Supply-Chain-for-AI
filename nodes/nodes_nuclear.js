// nodes/nodes_nuclear.js — Sector Energía Nuclear (Khipu Finance)
// SMR (reactores modulares pequeños) + Fusión + Uranio. La demanda 24/7 de
// energía de la IA es la tesis: los hyperscalers firman PPAs nucleares.
// Schema idéntico al resto del proyecto. Categorías: nuclear_smr, nuclear_fusion, uranium.

var NODES_NUCLEAR = [
  // ── SMR ────────────────────────────────────────────────────────────────────
  {
    "id":"Oklo","label":"Oklo Inc.","ticker":"OKLO · NYSE","cat":"nuclear_smr","port":"",
    "role":"Reactor Aurora de fisión rápida de pequeña escala (~15-75 MWe) alimentado con HALEU.",
    "supplies":"Reactores Aurora bajo modelo build-own-operate para Meta (1.2 GW Ohio), Switch y data centers; también recicla combustible nuclear usado.",
    "moat":"Primer non-LWR en romper tierra en INL; ~14 GW en cartas de intención; Sam Altman como ex-chairman. Modelo de vender electricidad, no reactores.",
    "loc":"EE.UU.","country":"EEUU","growth":"🟢 Mkt cap ~$9B; PDC de la NRC en proceso; primer poder 2027-28",
    "margin":null,"capex_2026":"Alto — construcción Aurora-INL","backlog_status":"~14 GW en LOIs; anchor Meta","mkt":"OKLO",
    "role_en":"Aurora fast-fission micro-reactor (~15-75 MWe) fueled by HALEU.",
    "supplies_en":"Aurora reactors under a build-own-operate model for Meta (1.2 GW Ohio), Switch and data centers; also recycles used nuclear fuel.",
    "moat_en":"First non-LWR to break ground at INL; ~14 GW in letters of intent; Sam Altman as ex-chairman. Sells electricity, not reactors.",
    "growth_en":"🟢 ~$9B mkt cap; NRC licensing underway; first power 2027-28"
  },
  {
    "id":"Xenergy","label":"X-energy","ticker":"XE · NYSE","cat":"nuclear_smr","port":"",
    "role":"Reactor Xe-100 (HTGR, 80 MWe) y la fábrica TRISO-X — primer combustible nuclear nuevo licenciado en EE.UU. en décadas.",
    "supplies":"Xe-100 para Amazon (5+ GW para 2039) y Dow Chemical (Seadrift TX); combustible de pebbles TRISO-X.",
    "moat":"TRISO-X: combustible único licenciado por la NRC; Amazon como anchor con miles de millones movilizados. Combustible + reactor integrados.",
    "loc":"EE.UU.","country":"EEUU","growth":"🟢 IPO 2026 (~$11B); FONSI récord de la NRC",
    "margin":null,"capex_2026":"Alto — planta TRISO-X","backlog_status":"Amazon 5+ GW; Dow Seadrift","mkt":"XE",
    "role_en":"Xe-100 reactor (HTGR, 80 MWe) and the TRISO-X fuel plant — first new US nuclear fuel licensed in decades.",
    "supplies_en":"Xe-100 for Amazon (5+ GW by 2039) and Dow Chemical (Seadrift TX); TRISO-X pebble fuel.",
    "moat_en":"TRISO-X: the only NRC-licensed new fuel; Amazon anchor with billions mobilized. Integrated fuel + reactor.",
    "growth_en":"🟢 2026 IPO (~$11B); record NRC FONSI"
  },
  {
    "id":"NuScale","label":"NuScale Power","ticker":"SMR · NYSE","cat":"nuclear_smr","port":"",
    "role":"Único SMR con certificación de diseño de la NRC. Reactor modular VOYGR (77 MWe).",
    "supplies":"VOYGR de 6 módulos para el proyecto Doicești (Rumanía) y acuerdos con utilities; diseño escalable a 12 módulos.",
    "moat":"Su certificación NRC es una barrera regulatoria que ningún rival tiene aún. Primer mover regulatorio, pero ejecución comercial lenta.",
    "loc":"EE.UU.","country":"EEUU","growth":"🟡 Volátil; depende de financiar el primer proyecto",
    "margin":null,"backlog_status":"Rumanía Doicești; pipeline de utilities","mkt":"SMR",
    "role_en":"The only SMR with NRC design certification. VOYGR modular reactor (77 MWe).",
    "supplies_en":"6-module VOYGR for the Doicești project (Romania) and utility agreements; scalable to 12 modules.",
    "moat_en":"Its NRC certification is a regulatory barrier no rival has yet. Regulatory first-mover, but slow commercial execution.",
    "growth_en":"🟡 Volatile; hinges on financing the first project"
  },
  {
    "id":"KairosPower","label":"Kairos Power","ticker":"Pre-IPO","cat":"nuclear_smr","port":"",
    "role":"Reactor de sales fundidas refrigerado con fluoruro (KP-FHR) — fisión avanzada de bajo costo.",
    "supplies":"Reactor de demostración Hermes en Oak Ridge; 500 MW comprometidos con Google (Alphabet) para data centers.",
    "moat":"Enfoque iterativo 'rapid prototyping' respaldado por el DOE; deal con Google valida el camino a data centers.",
    "loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO; demo Hermes 2027, comercial ~2030",
    "margin":null,"preipo":true,"backlog_status":"Google 500 MW; demo Hermes en construcción","mkt":"",
    "role_en":"Fluoride salt-cooled high-temperature reactor (KP-FHR) — low-cost advanced fission.",
    "supplies_en":"Hermes demo reactor at Oak Ridge; 500 MW committed to Google (Alphabet) for data centers.",
    "moat_en":"Iterative 'rapid prototyping' approach backed by the DOE; the Google deal validates the data-center path.",
    "growth_en":"⭐ PRE-IPO; Hermes demo 2027, commercial ~2030"
  },
  {
    "id":"TerraPower","label":"TerraPower","ticker":"Pre-IPO","cat":"nuclear_smr","port":"",
    "role":"Reactor Natrium de sodio rápido (345 MWe) con almacenamiento de sal fundida — fundada por Bill Gates.",
    "supplies":"Natrium en construcción en Kemmerer (Wyoming); 8 plantas comprometidas con Meta; respaldo de Nvidia (Serie E).",
    "moat":"Almacenamiento térmico integrado que permite seguir la carga de la red; Gates + Nvidia + Meta como respaldo y demanda.",
    "loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO (~$3.4B levantados); primer poder 2030-31",
    "margin":null,"preipo":true,"backlog_status":"Meta 8 plantas; Kemmerer en obra","mkt":"",
    "role_en":"Natrium sodium fast reactor (345 MWe) with molten-salt storage — founded by Bill Gates.",
    "supplies_en":"Natrium under construction in Kemmerer (Wyoming); 8 plants committed with Meta; Nvidia backing (Series E).",
    "moat_en":"Integrated thermal storage that enables load-following; Gates + Nvidia + Meta as backing and demand.",
    "growth_en":"⭐ PRE-IPO (~$3.4B raised); first power 2030-31"
  },
  // ── Fusión ──────────────────────────────────────────────────────────────────
  {
    "id":"CommonwealthFusion","label":"Commonwealth Fusion Systems","ticker":"Pre-IPO","cat":"nuclear_fusion","port":"",
    "role":"Fusión tokamak con magnetos superconductores de alta temperatura (HTS) — spin-off del MIT.",
    "supplies":"SPARC (demostrador, ~75% completo); ARC (planta comercial en Virginia); PPAs firmados con Google y Eni.",
    "moat":"La fusión mejor capitalizada (~$6.85B); magnetos HTS validados por el DOE — la apuesta más creíble del sector.",
    "loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO; SPARC primer plasma 2026-27; ARC early 2030s",
    "margin":null,"preipo":true,"backlog_status":"PPAs Google + Eni; SPARC en montaje","mkt":"",
    "role_en":"Tokamak fusion with high-temperature superconducting (HTS) magnets — MIT spin-off.",
    "supplies_en":"SPARC (demonstrator, ~75% complete); ARC (commercial plant in Virginia); PPAs signed with Google and Eni.",
    "moat_en":"The best-capitalized fusion company (~$6.85B); HTS magnets validated by the DOE — the sector's most credible bet.",
    "growth_en":"⭐ PRE-IPO; SPARC first plasma 2026-27; ARC early 2030s"
  },
  {
    "id":"Helion","label":"Helion Energy","ticker":"Pre-IPO","cat":"nuclear_fusion","port":"",
    "role":"Fusión pulsada por configuración de campo invertido (FRC); primer PPA comercial de fusión del mundo.",
    "supplies":"Polaris (7º dispositivo): plasma a 150M°C; planta comercial Orion en Malaga (WA); PPA de 50 MW con Microsoft.",
    "moat":"Primer en obtener licencias regulatorias comerciales de fusión; Microsoft como cliente y Sam Altman como mayor accionista.",
    "loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO (~$15.5B valuation); poder a Microsoft objetivo 2028",
    "margin":null,"preipo":true,"backlog_status":"Microsoft PPA 50 MW; Orion en obra","mkt":"",
    "role_en":"Pulsed field-reversed-configuration (FRC) fusion; world's first commercial fusion PPA.",
    "supplies_en":"Polaris (7th device): 150M°C plasma; Orion commercial plant in Malaga (WA); 50 MW PPA with Microsoft.",
    "moat_en":"First to obtain commercial fusion regulatory licenses; Microsoft as customer and Sam Altman as largest shareholder.",
    "growth_en":"⭐ PRE-IPO (~$15.5B valuation); power to Microsoft targeted 2028"
  },
  {
    "id":"TAETechnologies","label":"TAE Technologies","ticker":"Pre-IPO","cat":"nuclear_fusion","port":"",
    "role":"Fusión aneutrónica de configuración FRC con haces de partículas (p-B11) — sin neutrones de alta energía.",
    "supplies":"Reactor Norman/Copernicus; spin-offs de tecnología (power management, salud) que financian la I+D de fusión.",
    "moat":"Enfoque p-B11 que evitaría la radiactividad de la fusión D-T; ~$1.8B levantados; Google como socio de cómputo/ML.",
    "loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO (~$3B); Copernicus hacia net energy",
    "margin":null,"preipo":true,"backlog_status":"Copernicus en construcción","mkt":"",
    "role_en":"Aneutronic FRC fusion with particle beams (p-B11) — no high-energy neutrons.",
    "supplies_en":"Norman/Copernicus reactor; technology spin-offs (power management, health) that fund fusion R&D.",
    "moat_en":"p-B11 approach that would avoid D-T fusion radioactivity; ~$1.8B raised; Google as compute/ML partner.",
    "growth_en":"⭐ PRE-IPO (~$3B); Copernicus toward net energy"
  },
  // ── Uranio ──────────────────────────────────────────────────────────────────
  {
    "id":"Cameco","label":"Cameco Corporation","ticker":"CCJ · NYSE","cat":"uranium","port":"",
    "role":"Mayor productor de uranio del mundo occidental (fuera de Rusia/Kazajistán).",
    "supplies":"Uranio de Cigar Lake y McArthur River (Saskatchewan); 49% de Westinghouse (reactores AP1000); suministro a utilities globales.",
    "moat":"~20% de la producción mundial occidental y minas de la ley más alta del planeta; integración aguas abajo vía Westinghouse.",
    "loc":"Canadá","country":"Canada","growth":"🟢 Ingresos ~$3.5B FY2025; net +243% YoY por precios del uranio",
    "margin":0.17,"backlog_status":"Contratos a largo plazo con utilities","mkt":"CCJ",
    "role_en":"Largest uranium producer in the Western world (outside Russia/Kazakhstan).",
    "supplies_en":"Uranium from Cigar Lake and McArthur River (Saskatchewan); 49% of Westinghouse (AP1000 reactors); supply to global utilities.",
    "moat_en":"~20% of Western world production and the highest-grade mines on the planet; downstream integration via Westinghouse.",
    "growth_en":"🟢 ~$3.5B revenue FY2025; net +243% YoY on uranium prices"
  },
  {
    "id":"UraniumEnergy","label":"Uranium Energy Corp","ticker":"UEC · NYSE","cat":"uranium","port":"",
    "role":"Productor de uranio por recuperación in-situ (ISR) en EE.UU. — sin deuda, puro juego doméstico.",
    "supplies":"Burke Hollow ISR (Texas, mayor proyecto ISR de EE.UU. en una década) y Christensen Ranch (Wyoming).",
    "moat":"Sin deuda y totalmente sin coberturas: máxima exposición al precio spot; la Section 232 crea un premium doméstico.",
    "loc":"EE.UU.","country":"EEUU","growth":"🟢 Primer año de producción real; +53% en 2025",
    "margin":0.12,"backlog_status":"Burke Hollow en rampa","mkt":"UEC",
    "role_en":"In-situ recovery (ISR) uranium producer in the US — debt-free, pure domestic play.",
    "supplies_en":"Burke Hollow ISR (Texas, largest US ISR project in a decade) and Christensen Ranch (Wyoming).",
    "moat_en":"Debt-free and fully unhedged: maximum spot-price exposure; Section 232 creates a domestic premium.",
    "growth_en":"🟢 First year of real production; +53% in 2025"
  }
];
window.NODES_NUCLEAR = NODES_NUCLEAR;

// Links inter-sector: PPAs nucleares con hyperscalers + cadena de uranio
var LINKS_NUCLEAR = [
  // ── CANONIZADO (Etapa 2, 2026-07): source PROVEE a target; customer→supply,
  // investor→invest. Direcciones adjudicadas arista por arista (clasificador +
  // revisión manual). Formato uniforme [s, t, w, rel, type]. ──
  ['Oklo','Meta',3,'PPA energía 24/7','ppa'],
  ['TerraPower','Meta',3,'8 plantas Natrium','ppa'],
  ['Nvidia','TerraPower',2,'inversor (Serie E)','invest'],
  ['Xenergy','Amazon',3,'PPA 5+ GW','ppa'],
  ['Helion','Microsoft',3,'PPA fusión 50 MW','ppa'],
  ['CommonwealthFusion','Alphabet',2,'PPA fusión','ppa'],
  ['KairosPower','Alphabet',2,'PPA 500 MW','ppa'],
  ['TAETechnologies','Alphabet',1,'socio cómputo/ML','partner'],
  ['Cameco','Oklo',2,'suministro combustible','supply'],
  ['Cameco','NuScale',2,'suministro combustible','supply'],
  ['UraniumEnergy','Xenergy',2,'suministro combustible','supply'],
];
window.LINKS_NUCLEAR = LINKS_NUCLEAR;
