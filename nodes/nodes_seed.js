/* ============================================================================
   nodes/nodes_seed.js — DATOS SEMILLA (extraídos de app.html, 2026-07)
   Catálogo base v7/v8: categorías, países, 137 nodos seed, 546 links seed,
   metadatos por empresa, aliases de ids y tablas laterales de mercado.
   Se carga ANTES que los demás nodes_*.js y del bloque inline principal;
   los const declarados aquí son visibles en todos los <script> clásicos.
   Regla: los DATOS viven en nodes/, no en app.html.
   ============================================================================ */

const CATS = {
  quantum_hw:        {label:'Hardware Cuántico',      en:'Quantum Hardware',     cssVar:'--c-quantum_hw',        x:.05},
  quantum_infra:     {label:'Criogenia / Infra Q',    en:'Cryogenics / Q-Infra', cssVar:'--c-quantum_infra',     x:.09},
  eda:               {label:'EDA / IP',               en:'EDA / IP',             cssVar:'--c-eda',               x:.15},
  optics:            {label:'Óptica / Componentes',   en:'Optics / Components',  cssVar:'--c-optics',            x:.19},
  equip:             {label:'Equipamiento Fab',       en:'Fab Equipment',        cssVar:'--c-equip',             x:.24},
  materials:         {label:'Obleas / Materiales',    en:'Wafers / Materials',   cssVar:'--c-materials',         x:.30},
  chemicals:         {label:'Químicos / Gases',       en:'Chemicals / Gases',    cssVar:'--c-chemicals',         x:.34},
  foundry:           {label:'Foundry / IDM',          en:'Foundry / IDM',        cssVar:'--c-foundry',           x:.42},
  fabless:           {label:'Diseño (Fabless)',       en:'Design (Fabless)',     cssVar:'--c-fabless',           x:.50},
  memory:            {label:'Memoria',                en:'Memory',               cssVar:'--c-memory',            x:.55},
  substrates:        {label:'Sustratos / OSAT / Test',en:'Substrates / OSAT / Test',cssVar:'--c-substrates',     x:.60},
  networking:        {label:'Networking',             en:'Networking',           cssVar:'--c-networking',        x:.68},
  power:             {label:'Energía / Cooling',      en:'Power / Cooling',      cssVar:'--c-power',             x:.71},
  connectivity_infra:{label:'Fibra / Submarinos',     en:'Fiber / Subsea',       cssVar:'--c-connectivity_infra',x:.74},
  servers:           {label:'Servidores IA',          en:'AI Servers',           cssVar:'--c-servers',           x:.78},
  cloud:             {label:'Cloud / Neoclouds',      en:'Cloud / Neoclouds',    cssVar:'--c-cloud',             x:.86},
  ailab:             {label:'Labs IA Frontera',       en:'Frontier AI Labs',     cssVar:'--c-ailab',             x:.91},
  robotics_physical: {label:'IA Física / Robótica',   en:'Physical AI / Robotics',cssVar:'--c-robotics_physical',x:.95},
  aisoft:            {label:'Software IA',            en:'AI Software',          cssVar:'--c-aisoft',            x:.98},
};

const CATS_NEW = {
  space_launch:  {label:'Lanzamiento Espacial', en:'Space Launch',    cssVar:'--c-space_launch',  x:.01},
  space_infra:   {label:'Infraestructura Espacial', en:'Space Infra', cssVar:'--c-space_infra',   x:.02},
  satellite:     {label:'Satélites / LEO',       en:'Satellite / LEO', cssVar:'--c-satellite',     x:.03},
  earth_obs:     {label:'Observación Terrestre', en:'Earth Obs',      cssVar:'--c-earth_obs',     x:.05},
  rare_earth:    {label:'Tierras Raras',          en:'Rare Earth',     cssVar:'--c-rare_earth',    x:.03},
  battery_mat:   {label:'Baterías/Materiales',   en:'Battery Matls',  cssVar:'--c-battery_mat',   x:.07},
  asic_custom:   {label:'ASICs Custom',           en:'Custom ASICs',   cssVar:'--c-asic_custom',   x:.52},
  edge_ai:       {label:'Edge AI Silicon',        en:'Edge AI',        cssVar:'--c-edge_ai',       x:.54},
  photonics_si:  {label:'Fotónica Si',            en:'Si Photonics',   cssVar:'--c-photonics_si',  x:.57},
  dc_reit:       {label:'DC REITs',               en:'DC REITs',       cssVar:'--c-dc_reit',       x:.82},
  cdn_edge:      {label:'CDN / Edge DC',          en:'CDN / Edge DC',  cssVar:'--c-cdn_edge',      x:.84},
  hpc_super:     {label:'HPC / Supercomputación', en:'HPC / Supercomp',cssVar:'--c-hpc_super',     x:.80},
  neuromorphic:  {label:'Neuromórfica',           en:'Neuromorphic',   cssVar:'--c-neuromorphic',  x:.07},
  ai_defense:    {label:'IA Defensa',             en:'Defense AI',     cssVar:'--c-ai_defense',    x:.88},
  ai_health:     {label:'IA Salud',               en:'Health AI',      cssVar:'--c-ai_health',     x:.89},
  ai_finance:    {label:'IA Finanzas',            en:'Finance AI',     cssVar:'--c-ai_finance',    x:.90},
  ai_auto:       {label:'IA Automotriz',          en:'Automotive AI',  cssVar:'--c-ai_auto',       x:.92},
  ai_agents:     {label:'Agentes IA',             en:'AI Agents',      cssVar:'--c-ai_agents',     x:.95},
  // Categories used in expanded node files that were missing:
  equip:         {label:'Equipamiento',           en:'Equipment',      cssVar:'--c-equip',         x:.22},
  memory:        {label:'Memoria',                en:'Memory',         cssVar:'--c-memory',        x:.30},
  networking:    {label:'Networking',             en:'Networking',     cssVar:'--c-networking',    x:.75},
  quantum_hw:    {label:'Quantum HW',             en:'Quantum HW',     cssVar:'--c-quantum_hw',    x:.09},
  eda:           {label:'EDA / Software CAD',     en:'EDA / CAD SW',   cssVar:'--c-eda',           x:.20},
  substrates:    {label:'Sustratos',              en:'Substrates',     cssVar:'--c-substrates',    x:.13},
  optics:        {label:'Óptica',                 en:'Optics',         cssVar:'--c-optics',        x:.26},
  nuclear_smr:   {label:'Nuclear · SMR',           en:'Nuclear · SMR',  cssVar:'--c-nuclear_smr',   x:.70},
  nuclear_fusion:{label:'Nuclear · Fusión',        en:'Nuclear · Fusion',cssVar:'--c-nuclear_fusion',x:.72},
  uranium:       {label:'Uranio',                  en:'Uranium',        cssVar:'--c-uranium',       x:.68},
};

const COUNTRIES = {
  EEUU:        {es:'EE.UU.',          en:'USA',            x:.17, y:.45, c:'#2E6FB7', cd:'#6FAAE8'},
  ReinoUnido:  {es:'Reino Unido',     en:'United Kingdom', x:.16, y:.10, c:'#0C7370', cd:'#3FB5A8'},
  PaisesBajos: {es:'Países Bajos',    en:'Netherlands',    x:.33, y:.12, c:'#D97A1F', cd:'#F0A050'},
  Alemania:    {es:'Alemania',        en:'Germany',        x:.48, y:.10, c:'#9A6310', cd:'#D89A3E'},
  Francia:     {es:'Francia',         en:'France',         x:.62, y:.12, c:'#7B2FBE', cd:'#BD8AF0'},
  RestoEuropa: {es:'Resto de Europa', en:'Rest of Europe', x:.78, y:.10, c:'#5F6B52', cd:'#9AA888'},
  Japon:       {es:'Japón',           en:'Japan',          x:.86, y:.38, c:'#C2185B', cd:'#F06CA0'},
  Corea:       {es:'Corea del Sur',   en:'South Korea',    x:.86, y:.70, c:'#6B5DD3', cd:'#A99EEC'},
  Taiwan:      {es:'Taiwán',          en:'Taiwan',         x:.62, y:.78, c:'#18A05A', cd:'#4BD693'},
  China:       {es:'China',           en:'China',          x:.38, y:.82, c:'#C8392F', cd:'#F07B68'},
  RestoMundo:  {es:'Resto del mundo', en:'Rest of World',  x:.13, y:.86, c:'#8A857A', cd:'#B5B0A4'},
};

const NODES = [
  {"id":"IBMQuantum","label":"IBM Quantum","ticker":"IBM · NYSE (división)","cat":"quantum_hw","port":"","role":"División cuántica de IBM, líder en qubits superconductores con la hoja de ruta más creíble del sector.","supplies":"Acceso a procesadores Quantum System Two (Heron/Flamingo) vía nube y la IBM Quantum Network a 250+ corporaciones, gobiernos y laboratorios; también instala sistemas on-premise en Japón, Alemania y Corea.","moat":"Hoja de ruta pública con destino Starling (2029): computación tolerante a fallos con qubits lógicos. ~$1B de ingresos acumulados y el balance de IBM detrás — nadie más combina escala, fab propia y paciencia financiera. Riesgo: el calendario puede deslizarse.","loc":"EE.UU.","growth":"🔵 +30% e. 2026 (división, base pequeña)","margin":null,"capex_2026":"n/s — integrado en CAPEX de IBM","backlog_status":"Quantum Network: 250+ miembros; ~$1B de ingresos acumulados","country":"EEUU","mkt":"IBM","role_en":"IBM's quantum division, the leader in superconducting qubits with the sector's most credible roadmap.","supplies_en":"Cloud access to Quantum System Two processors (Heron/Flamingo) and the IBM Quantum Network for 250+ corporations, governments and labs; also installs on-premise systems in Japan, Germany and Korea.","moat_en":"Public roadmap targeting Starling (2029): fault-tolerant computing with logical qubits. ~$1B in cumulative revenue and IBM's balance sheet behind it — no one else combines scale, an in-house fab and financial patience. Risk: the timeline may slip.","growth_en":"🔵 +30% 2026e (division, small base)","capex_2026_en":"n/a — folded into IBM's CAPEX","backlog_status_en":"Quantum Network: 250+ members; ~$1B cumulative revenue"},
  {"id":"Rigetti","label":"Rigetti Computing","ticker":"RGTI · Nasdaq","cat":"quantum_hw","port":"","role":"Pionero de qubits superconductores con fabricación propia, en carrera por escalar antes que su caja.","supplies":"Sistemas Ankaa-3 (84 qubits) y la QPU Novera de 9 qubits para laboratorios y gobiernos; acceso vía nube propia, AWS Braket y Azure Quantum. Fabrica sus propios chips en Fab-1, su fábrica de Fremont, California.","moat":"Una de las pocas cuánticas con fab dedicada propia (Fab-1), lo que acelera la iteración de diseño. Pero con ingresos de ~$10–20M frente a rivales mucho mejor capitalizados, su supervivencia depende de hitos técnicos y de seguir diluyendo al accionista.","loc":"EE.UU.","growth":"🔵 +40% 2026e (base ínfima)","margin":-2.5,"capex_2026":"$20–30M (Fab-1)","backlog_status":"Contratos DARPA/AFRL; libro de órdenes corto","country":"EEUU","mkt":"RGTI","role_en":"Superconducting-qubit pioneer with in-house fabrication, racing to scale before its cash runs out.","supplies_en":"Ankaa-3 systems (84 qubits) and the 9-qubit Novera QPU for labs and governments; access via its own cloud, AWS Braket and Azure Quantum. Makes its own chips at Fab-1, its Fremont, California fab.","moat_en":"One of the few quantum players with its own dedicated fab (Fab-1), which speeds up design iteration. But with revenue of ~$10–20M against far better-capitalized rivals, its survival hinges on technical milestones and continued shareholder dilution.","growth_en":"🔵 +40% 2026e (tiny base)","capex_2026_en":"$20–30M (Fab-1)","backlog_status_en":"DARPA/AFRL contracts; short order book"},
  {"id":"IonQ","label":"IonQ","ticker":"IONQ · NYSE","cat":"quantum_hw","port":"","role":"Líder comercial en iones atrapados y la cuántica cotizada de referencia para el mercado.","supplies":"Sistemas Forte Enterprise y Tempo accesibles en AWS Braket, Azure Quantum y Google Cloud; vende sistemas completos a gobiernos (AFRL, EAU) y redes cuánticas seguras tras adquirir Qubitekk e ID Quantique.","moat":"La mayor fidelidad de puerta del sector (>99.9%) sin criogenia de dilución: sus iones operan casi a temperatura ambiente. La compra de Oxford Ionics (2025) le aporta trampas de iones en obleas CMOS estándar. Quema caja intensa y valoración exigente.","loc":"EE.UU.","growth":"⚡ +80% 2026e","margin":-1.5,"capex_2026":"$50–100M (sistemas Tempo, redes)","backlog_status":"Bookings > ingresos; contrato AFRL de $54.5M","country":"EEUU","mkt":"IONQ","role_en":"Commercial leader in trapped ions and the market's benchmark listed quantum stock.","supplies_en":"Forte Enterprise and Tempo systems available on AWS Braket, Azure Quantum and Google Cloud; sells full systems to governments (AFRL, UAE) and secure quantum networks after acquiring Qubitekk and ID Quantique.","moat_en":"The sector's highest gate fidelity (>99.9%) without dilution cryogenics: its ions run at near room temperature. The Oxford Ionics acquisition (2025) adds ion traps on standard CMOS wafers. Heavy cash burn and a demanding valuation.","growth_en":"⚡ +80% 2026e","capex_2026_en":"$50–100M (Tempo systems, networks)","backlog_status_en":"Bookings > revenue; $54.5M AFRL contract"},
  {"id":"PsiQuantum","label":"PsiQuantum","ticker":"Pre-IPO ~$7B","cat":"quantum_hw","port":"","role":"Startup fotónica pre-IPO que apuesta por saltar directo al millón de qubits con fabricación CMOS.","supplies":"Chips cuánticos fotónicos fabricados por GlobalFoundries en procesos CMOS estándar; construye computadoras tolerantes a fallos a escala de centro de datos para los gobiernos de Australia (Brisbane) e Illinois (Chicago).","moat":"Único enfoque que usa fabs de silicio convencionales a escala de oblea: si funciona, la escala industrial es inmediata. $1B+ levantados en 2025 con Nvidia entre los inversores; valorada ~$7B. Riesgo binario: aún no ha demostrado un sistema completo operativo.","loc":"EE.UU.","growth":"⭐ PRE-IPO (~$7B); ingresos incipientes","margin":null,"capex_2026":"$500M+ (Brisbane y Chicago)","backlog_status":"Megaproyectos estatales: Brisbane (Australia) e Illinois (EE.UU.)","preipo":true,"country":"EEUU","role_en":"Pre-IPO photonics startup betting on jumping straight to a million qubits with CMOS fabrication.","supplies_en":"Photonic quantum chips made by GlobalFoundries on standard CMOS processes; building fault-tolerant, data-center-scale computers for the governments of Australia (Brisbane) and Illinois (Chicago).","moat_en":"The only approach using conventional silicon fabs at wafer scale: if it works, industrial scale is immediate. $1B+ raised in 2025 with Nvidia among the investors; valued at ~$7B. Binary risk: it has yet to demonstrate a complete working system.","growth_en":"⭐ PRE-IPO (~$7B); nascent revenue","capex_2026_en":"$500M+ (Brisbane and Chicago)","backlog_status_en":"State megaprojects: Brisbane (Australia) and Illinois (US)"},
  {"id":"DWave","label":"D-Wave Quantum","ticker":"QBTS · NYSE","cat":"quantum_hw","port":"","role":"Especialista en quantum annealing, la única cuántica con clientes en producción comercial real.","supplies":"Sistemas Advantage2 (4,400+ qubits de annealing) y acceso cloud Leap para optimización logística y de planificación: Ford Otosan, NTT Docomo o Pattison Food Group los usan en producción, no en pilotos.","moat":"Monopolio de facto en annealing con 20+ años de patentes y la única base de clientes cuánticos en explotación diaria. Su límite es también su techo: el annealing no es computación universal, y los sistemas de puertas lógicas podrían absorber su nicho hacia 2030.","loc":"Canadá","growth":"⚡ +50% 2026e (ventas de sistemas irregulares)","margin":-1.5,"capex_2026":"~$15M — modelo ligero","backlog_status":"Bookings récord; clientes recurrentes en producción","country":"RestoMundo","mkt":"QBTS","role_en":"Quantum annealing specialist, the only quantum company with customers in real commercial production.","supplies_en":"Advantage2 systems (4,400+ annealing qubits) and Leap cloud access for logistics and scheduling optimization: Ford Otosan, NTT Docomo and Pattison Food Group use them in production, not in pilots.","moat_en":"De facto monopoly in annealing with 20+ years of patents and the only quantum customer base in daily commercial use. Its limit is also its ceiling: annealing is not universal computing, and gate-based systems could absorb its niche by 2030.","growth_en":"⚡ +50% 2026e (lumpy system sales)","capex_2026_en":"~$15M — asset-light model","backlog_status_en":"Record bookings; recurring customers in production"},
  {"id":"Quantinuum","label":"Quantinuum","ticker":"Pre-IPO ~$10B (Honeywell)","cat":"quantum_hw","port":"","role":"Líder en computación cuántica de iones atrapados (Helios); récords de volumen cuántico; mayoría de Honeywell","supplies":"Ordenadores cuánticos Helios de iones atrapados, acceso cloud y software (TKET, claves Quantum Origin) para gobiernos, bancos y centros HPC.","moat":"Mayor volumen cuántico del sector y fidelidades de dos qubits >99,9%; respaldo de Honeywell (mayoría) y JPMorgan; valoración ~$10.000M. Riesgo: los iones escalan más despacio que los chips superconductores de IBM/Google.","loc":"EE.UU. / Reino Unido","country":"EEUU","growth":"⭐ PRE-IPO · ingresos >+50% desde base ~$100M","margin":-2,"capex_2026":"Alto: fabricación Helios; roadmap Apollo","backlog_status":"Contratos plurianuales gov/HPC; demanda Helios sólida","role_en":"Trapped-ion quantum computing leader (Helios); quantum volume record-holder; Honeywell majority-owned","supplies_en":"Helios trapped-ion quantum computers, cloud access and software (TKET, Quantum Origin key generation) for governments, banks and HPC centers.","moat_en":"Industry-leading quantum volume and two-qubit fidelities above 99.9%; backed by majority owner Honeywell and JPMorgan at a ~$10B valuation. Risk: trapped ions scale more slowly than IBM/Google superconducting chips.","growth_en":"⭐ PRE-IPO · revenue >+50% off a ~$100M base","capex_2026_en":"High: Helios builds; Apollo roadmap","backlog_status_en":"Multi-year gov/HPC contracts; solid Helios demand","preipo":true},
  {"id":"Pasqal","label":"Pasqal","ticker":"Pre-IPO · Francia","cat":"quantum_hw","port":"","role":"Campeón cuántico francés y europeo; procesadores de átomos neutros de 100-1.000 qubits para HPC","supplies":"Procesadores cuánticos de átomos neutros (serie Orion) instalados en centros HPC europeos (GENCI, Jülich) y vendidos a Oriente Medio y Corea; acceso cloud y librerías de optimización.","moat":"Los átomos neutros escalan barato (láseres y pinzas ópticas, sin criogenia de dilución); respaldo del Estado francés y la UE, con QPUs ya instaladas en HPC. Riesgo: fidelidades por detrás de iones/superconductores y competencia directa de QuEra.","loc":"Francia","country":"Francia","growth":"⭐ PRE-IPO · contratos HPC europeos en expansión","margin":-2.5,"capex_2026":"Moderado: fab de Massy y líneas exteriores","backlog_status":"Pedidos EuroHPC/GENCI firmados; pipeline soberano","role_en":"France's and Europe's quantum champion; 100-1,000 qubit neutral-atom processors for HPC","supplies_en":"Neutral-atom quantum processors (Orion series) installed at European HPC centers (GENCI, Jülich) and sold into the Middle East and Korea; cloud access and optimization libraries.","moat_en":"Neutral atoms scale cheaply (lasers and optical tweezers, no dilution cryogenics); backed by the French state and the EU, with QPUs already installed at HPC sites. Risk: fidelities trail ions/superconductors and QuEra competes head-on.","growth_en":"⭐ PRE-IPO · European HPC contracts expanding","capex_2026_en":"Moderate: Massy fab plus overseas lines","backlog_status_en":"EuroHPC/GENCI orders signed; sovereign pipeline","preipo":true},
  {"id":"Bluefors","label":"Bluefors","ticker":"Privada · Finlandia","cat":"quantum_infra","port":"","role":"Líder mundial en criostatos de dilución: el frío extremo del que depende casi toda la cuántica.","supplies":"Refrigeradores de dilución (~10 mK, más frío que el espacio profundo) para IBM, Google, Rigetti, AWS y laboratorios de todo el mundo; su plataforma KIDE refrigera el Quantum System Two de IBM.","moat":"Cuota dominante (~60–70%) en refrigeración de dilución: es el cuello de botella físico de toda la cuántica superconductora. Rentable y privada — rareza absoluta en el sector. Riesgo: Oxford Instruments compite en la gama alta y los clientes grandes exploran criogenia propia.","loc":"Finlandia","growth":"🔵 +25% 2026e","margin":0.22,"capex_2026":"€50M+ (capacidad Helsinki y EE.UU.)","backlog_status":"Lista de espera de 12–18 meses en criostatos grandes","preipo":true,"country":"RestoEuropa","role_en":"World leader in dilution cryostats: the extreme cold nearly all of quantum computing depends on.","supplies_en":"Dilution refrigerators (~10 mK, colder than deep space) for IBM, Google, Rigetti, AWS and labs worldwide; its KIDE platform cools IBM's Quantum System Two.","moat_en":"Dominant share (~60–70%) in dilution refrigeration: the physical bottleneck of all superconducting quantum. Profitable and private — an absolute rarity in the sector. Risk: Oxford Instruments competes at the high end and large customers are exploring in-house cryogenics.","growth_en":"🔵 +25% 2026e","capex_2026_en":"€50M+ (Helsinki and US capacity)","backlog_status_en":"12–18 month wait list for large cryostats"},
  {"id":"OxfordInstruments","label":"Oxford Instruments","ticker":"OXIG · LSE","cat":"quantum_infra","port":"","role":"Grupo británico de instrumentación científica y criogenia, proveedor clave de los laboratorios cuánticos.","supplies":"Criostatos de dilución Proteox, imanes superconductores y equipos de deposición y grabado para universidades, laboratorios nacionales y fabricantes de qubits; además, microscopía y análisis de materiales para semiconductores.","moat":"Décadas de física criogénica e imanes superconductores difíciles de replicar; segundo actor tras Bluefors en dilución. Su diversificación en semiconductores y ciencia de materiales amortigua el ciclo de financiación cuántica.","loc":"Reino Unido","growth":"🟢 +8% FY2026","margin":0.17,"capex_2026":"~£30M","backlog_status":"Cartera de pedidos ~6 meses de ingresos","country":"ReinoUnido","mkt":"OXINF","role_en":"British scientific instrumentation and cryogenics group, a key supplier to quantum labs.","supplies_en":"Proteox dilution refrigerators, superconducting magnets and deposition and etch equipment for universities, national labs and qubit makers; plus microscopy and materials analysis for semiconductors.","moat_en":"Decades of cryogenic physics and superconducting magnets that are hard to replicate; the number two in dilution behind Bluefors. Its diversification into semiconductors and materials science cushions the quantum funding cycle.","growth_en":"🟢 +8% FY2026","capex_2026_en":"~£30M","backlog_status_en":"Order book ~6 months of revenue"},
  {"id":"QuantumMachines","label":"Quantum Machines","ticker":"Pre-IPO · Israel","cat":"quantum_infra","port":"","role":"Controladores OPX: la electrónica que orquesta y lee los qubits en la mayoría de labs del mundo","supplies":"Controladores OPX1000 y lenguaje QUA: control y lectura en tiempo real que calibra qubits y ejecuta corrección de errores; integración con Nvidia (DGX Quantum).","moat":"Sus controladores están en cientos de labs (>50% de cuota estimada) y son agnósticos a la modalidad: gana sea cual sea el qubit vencedor. Riesgo: Zurich Instruments y Keysight presionan y el mercado de control aún se mide en cientos de millones.","loc":"Israel","country":"RestoMundo","growth":"⭐ PRE-IPO · ventas creciendo ~40% anual","margin":-0.5,"capex_2026":"Bajo: modelo fabless, I+D en Tel Aviv","backlog_status":"Cartera creciente: labs, HPC y programas nacionales","role_en":"OPX controllers: the electronics that orchestrate and read out qubits in most labs worldwide","supplies_en":"OPX1000 controllers and the QUA language: real-time control and readout that calibrate qubits and run error correction; integrates with Nvidia (DGX Quantum).","moat_en":"Its controllers sit in hundreds of labs (est. >50% share) and are qubit-agnostic: it wins whichever modality prevails. Risk: Zurich Instruments and Keysight push hard, and the control market is still measured in hundreds of millions.","growth_en":"⭐ PRE-IPO · sales growing ~40% a year","capex_2026_en":"Low: fabless model, R&D in Tel Aviv","backlog_status_en":"Growing book: labs, HPC centers, national programs","preipo":true},
  {"id":"FormFactor","label":"FormFactor","ticker":"FORM · Nasdaq","cat":"quantum_infra","port":"","role":"Nº1 en probe cards para test de obleas y sistemas criogénicos; puente entre semis avanzados y cuántica","supplies":"Probe cards a medida para test de obleas DRAM/HBM y lógica avanzada; sistemas criogénicos y de metrología (HPD, FRT) para labs cuánticos y empaquetado avanzado.","moat":"Nº1 mundial en probe cards (~35% de cuota); cada diseño de chip exige una tarjeta a medida, ingreso casi consumible; HBM4 multiplica la intensidad de test por oblea y FRT/HPD aportan el puente criogénico. Riesgo: ciclicidad de memoria.","loc":"EE.UU.","country":"EEUU","growth":"🔵 +18% por test HBM4 y criogenia","margin":0.14,"capex_2026":"~$60M en capacidad de probe cards","backlog_status":"Sólido, ligado a las rampas de HBM4","role_en":"No. 1 in wafer-test probe cards plus cryogenic systems; the bridge between advanced semis and quantum","supplies_en":"Custom probe cards for DRAM/HBM and advanced-logic wafer test; cryogenic and metrology systems (HPD, FRT) for quantum labs and advanced packaging.","moat_en":"World No. 1 in probe cards (~35% share); every chip design needs a custom card, making revenue near-consumable; HBM4 multiplies test intensity per wafer and FRT/HPD add the cryogenic bridge. Risk: memory cyclicality.","growth_en":"🔵 +18% on HBM4 test and cryogenics","capex_2026_en":"~$60M on probe card capacity","backlog_status_en":"Solid, tied to HBM4 ramps","mkt":"FORM"},
  {"id":"Synopsys","label":"Synopsys","ticker":"SNPS · Nasdaq","cat":"eda","port":"","role":"Líder mundial en software EDA; con Ansys (2025) domina diseño y simulación de chips.","supplies":"Herramientas de síntesis lógica, verificación formal y simulación con las que Nvidia, AMD y Broadcom diseñan sus chips antes de fabricarlos. Tras integrar Ansys (2025), suma simulación multifísica para chips 3D, fotónica y térmica de packaging avanzado.","moat":"Duopolio con Cadence (~70–75% del mercado EDA entre ambos). Sin sus herramientas, ningún chip avanzado puede diseñarse — es el AutoCAD del semiconductor. Ansys eleva el coste de cambio: diseño y física en un solo flujo.","loc":"EE.UU.","growth":"🟢 +12–15% orgánico (Ansys consolidado)","margin":0.38,"capex_2026":"~$200M — software ligero","backlog_status":"Backlog no cancelable >$10B (multianual)","country":"EEUU","mkt":"SNPS","role_en":"World leader in EDA software; with Ansys (2025) it dominates chip design and simulation.","supplies_en":"Logic synthesis, formal verification and simulation tools Nvidia, AMD and Broadcom use to design their chips before fabrication. After integrating Ansys (2025), it adds multiphysics simulation for 3D chips, photonics and advanced-packaging thermals.","moat_en":"Duopoly with Cadence (~70–75% of the EDA market combined). Without its tools, no advanced chip can be designed — it is the AutoCAD of semiconductors. Ansys raises switching costs: design and physics in a single flow.","growth_en":"🟢 +12–15% organic (Ansys consolidated)","capex_2026_en":"~$200M — asset-light software","backlog_status_en":"Non-cancelable backlog >$10B (multi-year)"},
  {"id":"Cadence","label":"Cadence","ticker":"CDNS · Nasdaq","cat":"eda","port":"","role":"Desarrollador de software EDA, especialista en diseño analógico y verificación.","supplies":"Software de automatización de diseño (Virtuoso, Genus) y simulación de transistores para Nvidia, Qualcomm y Apple. Estándar de facto junto con Synopsys; su hardware de emulación (Palladium) se vende con meses de espera por la ola de ASICs de IA.","moat":"Duopolio con Synopsys. Indispensable en el flujo de diseño de toda la industria: ~85% de ingresos recurrentes y costes de cambio prohibitivos a mitad de un diseño de 2nm.","loc":"EE.UU.","growth":"🟢 +13–16% anual","margin":0.42,"capex_2026":"~$150M — software ligero","backlog_status":"Backlog ~$6.5B; Palladium con lista de espera","country":"EEUU","mkt":"CDNS","role_en":"EDA software developer, specialist in analog design and verification.","supplies_en":"Design automation software (Virtuoso, Genus) and transistor simulation for Nvidia, Qualcomm and Apple. De facto standard alongside Synopsys; its Palladium emulation hardware sells with months-long waits on the AI ASIC wave.","moat_en":"Duopoly with Synopsys. Indispensable across the industry's design flow: ~85% recurring revenue and prohibitive switching costs midway through a 2nm design.","growth_en":"🟢 +13–16% per year","capex_2026_en":"~$150M — asset-light software","backlog_status_en":"Backlog ~$6.5B; Palladium wait-listed"},
  {"id":"ARM","label":"ARM","ticker":"ARM · Nasdaq","cat":"eda","port":"C2","role":"Proveedor de la arquitectura de CPU bajo licencia que vertebra el cómputo de IA.","supplies":"Diseños de núcleos de CPU/GPU que otras empresas licencian: Grace de Nvidia, Graviton de AWS y Cobalt de Microsoft son ARM. Más del 95% de los smartphones del mundo usan su arquitectura.","moat":"Monopolio virtual en mobile y arquitectura por defecto de la CPU en data centers de IA. Cobra royalties por cada chip fabricado — modelo que escala con todo el sector. Riesgo a largo plazo: RISC-V como alternativa abierta.","loc":"Reino Unido","growth":"🔵 +22–28% anual","margin":0.45,"capex_2026":"n/s — modelo de licencias, capex mínimo","backlog_status":"RPO ~$3B; royalties crecen con cada chip vendido","country":"ReinoUnido","mkt":"ARM","role_en":"Provider of the licensed CPU architecture that underpins AI compute.","supplies_en":"CPU/GPU core designs other companies license: Nvidia's Grace, AWS's Graviton and Microsoft's Cobalt are ARM. More than 95% of the world's smartphones use its architecture.","moat_en":"Virtual monopoly in mobile and the default CPU architecture in AI data centers. Collects royalties on every chip made — a model that scales with the entire sector. Long-term risk: RISC-V as an open alternative.","growth_en":"🔵 +22–28% per year","capex_2026_en":"n/a — licensing model, minimal capex","backlog_status_en":"RPO ~$3B; royalties grow with every chip sold"},
  {"id":"SiemensEDA","label":"Siemens EDA","ticker":"vía Siemens · Frankfurt","cat":"eda","port":"","role":"Tercer jugador del oligopolio EDA (ex-Mentor Graphics), dentro de Siemens.","supplies":"Herramientas de diseño de PCB, verificación física (Calibre, estándar de facto en el sign-off) y emulación (Veloce). Especialmente fuerte en automotive y sistemas embebidos.","moat":"Tercer jugador relevante tras Synopsys y Cadence; Calibre es prácticamente obligatorio en la verificación final de cualquier chip que va a TSMC. Respaldado por el balance de Siemens.","loc":"Alemania","growth":"🟡 +8–11% anual","margin":0.3,"capex_2026":"n/s — división de software de Siemens","backlog_status":"Contratos plurianuales; sin desglose público","country":"Alemania","mkt":"SIEGY","role_en":"Third player in the EDA oligopoly (formerly Mentor Graphics), within Siemens.","supplies_en":"PCB design tools, physical verification (Calibre, the de facto sign-off standard) and emulation (Veloce). Especially strong in automotive and embedded systems.","moat_en":"The relevant third player behind Synopsys and Cadence; Calibre is practically mandatory for final verification of any chip headed to TSMC. Backed by Siemens' balance sheet.","growth_en":"🟡 +8–11% per year","capex_2026_en":"n/a — Siemens software division","backlog_status_en":"Multi-year contracts; no public breakdown"},
  {"id":"Zeiss","label":"Zeiss SMT","ticker":"Privada (25% ASML)","cat":"optics","port":"","role":"Fabricante en monopolio de las ópticas para las máquinas EUV de ASML.","supplies":"Espejos pulidos a nivel atómico para ASML — las superficies más lisas del mundo (rugosidad <1 ángstrom). Sin estas ópticas, el EUV no funciona; cada sistema High-NA incorpora su óptica anamórfica de nueva generación.","moat":"Monopolio absoluto en ópticas EUV. ASML posee ~25% de Zeiss SMT — relación simbiótica exclusiva e irremplazable, con décadas de know-how de pulido imposibles de replicar.","loc":"Alemania","growth":"🔵 +20–25% anual (vía ASML)","margin":0.28,"capex_2026":"€600M+ (ampliación de Oberkochen)","backlog_status":"Acoplado al backlog EUV/High-NA de ASML (años)","preipo":true,"country":"Alemania","role_en":"Monopoly maker of the optics for ASML's EUV machines.","supplies_en":"Mirrors polished to the atomic level for ASML — the smoothest surfaces in the world (roughness <1 angstrom). Without these optics EUV does not work; every High-NA system carries its next-generation anamorphic optics.","moat_en":"Absolute monopoly in EUV optics. ASML owns ~25% of Zeiss SMT — an exclusive, irreplaceable symbiotic relationship, with decades of polishing know-how impossible to replicate.","growth_en":"🔵 +20–25% per year (via ASML)","capex_2026_en":"€600M+ (Oberkochen expansion)","backlog_status_en":"Tied to ASML's EUV/High-NA backlog (years)"},
  {"id":"Trumpf","label":"Trumpf","ticker":"Privada (familiar)","cat":"optics","port":"","role":"Proveedor único del láser CO₂ de alta potencia que genera la luz EUV.","supplies":"El láser que vaporiza microgotas de estaño 50,000 veces por segundo para generar la luz EUV dentro de la máquina de ASML. Además, líder mundial en láseres industriales y máquina-herramienta.","moat":"Único proveedor del láser esencial para EUV — relación exclusiva con ASML, sin sustituto en el horizonte. El negocio EUV crece con fuerza aunque su división de máquina-herramienta sea cíclica.","loc":"Alemania","growth":"🔵 +18–22% anual (vía ASML)","margin":0.09,"capex_2026":"~€400M (capacidad láser EUV)","backlog_status":"Producción EUV comprometida con años de antelación","preipo":true,"country":"Alemania","role_en":"Sole supplier of the high-power CO₂ laser that generates EUV light.","supplies_en":"The laser that vaporizes tin microdroplets 50,000 times per second to generate EUV light inside ASML's machine. Also the world leader in industrial lasers and machine tools.","moat_en":"Sole supplier of the laser essential to EUV — an exclusive relationship with ASML, with no substitute on the horizon. The EUV business is growing strongly even though its machine-tool division is cyclical.","growth_en":"🔵 +18–22% per year (via ASML)","capex_2026_en":"~€400M (EUV laser capacity)","backlog_status_en":"EUV output committed years in advance"},
  {"id":"MitsuiChemicals","label":"Mitsui Chemicals","ticker":"4183 · TSE","cat":"optics","port":"","role":"Químico japonés, proveedor crítico de pellicles EUV.","supplies":"Membranas de carbono de ~50nm de grosor (pellicles) que protegen la máscara EUV de partículas durante la exposición, suministradas al ecosistema ASML/TSMC. Completa con química de alto valor para packaging y automoción.","moat":"Uno de los poquísimos calificados en pellicles EUV — un componente donde un solo defecto arruina la máscara. El negocio crece con cada capa EUV añadida por nodo; el grupo químico diversificado financia la expansión.","loc":"Japón","growth":"🔵 +25–35% (negocio pellicles)","margin":0.07,"capex_2026":"~¥180B grupo; ampliación pellicles","backlog_status":"Capacidad de pellicles comprometida con TSMC/ASML","country":"Japon","mkt":"MITUY","role_en":"Japanese chemicals maker, a critical supplier of EUV pellicles.","supplies_en":"Carbon membranes ~50nm thick (pellicles) that shield the EUV mask from particles during exposure, supplied to the ASML/TSMC ecosystem. Rounded out with high-value chemistry for packaging and automotive.","moat_en":"One of the very few qualified in EUV pellicles — a component where a single defect ruins the mask. The business grows with every EUV layer added per node; the diversified chemicals group funds the expansion.","growth_en":"🔵 +25–35% (pellicle business)","capex_2026_en":"~¥180B group; pellicle expansion","backlog_status_en":"Pellicle capacity committed to TSMC/ASML"},
  {"id":"Toto","label":"Toto","ticker":"5332 · TSE","cat":"optics","port":"","role":"Ceramista japonés que fabrica los mandriles electrostáticos (ESC) de los fabs.","supplies":"Platos cerámicos (ESC) que sujetan la oblea con precisión nanométrica dentro de los equipos de grabado y deposición de Lam, Applied Materials o TEL. Conocido por sanitarios, su cerámica avanzada es la joya oculta del grupo.","moat":"Líder y titular de patentes clave en ESC — sin ellos la oblea no se procesa. Décadas de know-how cerámico difícil de copiar; su negocio de semiconductores crece muy por encima del resto del grupo.","loc":"Japón","growth":"🟢 +10–15% anual","margin":0.08,"capex_2026":"~¥55B grupo; nueva capacidad cerámica","backlog_status":"ESC con lista de espera; ampliando hasta 2027","country":"Japon","mkt":"TOTDY","role_en":"Japanese ceramics maker that builds the electrostatic chucks (ESCs) used in fabs.","supplies_en":"Ceramic plates (ESCs) that hold the wafer with nanometer precision inside etch and deposition tools from Lam, Applied Materials and TEL. Known for sanitaryware, its advanced ceramics are the group's hidden gem.","moat_en":"Leader and holder of key ESC patents — without them the wafer cannot be processed. Decades of hard-to-copy ceramics know-how; its semiconductor business is growing well ahead of the rest of the group.","growth_en":"🟢 +10–15% per year","capex_2026_en":"~¥55B group; new ceramics capacity","backlog_status_en":"ESCs wait-listed; expanding through 2027"},
  {"id":"Hoya","label":"Hoya","ticker":"7741 · TSE","cat":"optics","port":"","role":"Duopolio con AGC en mask blanks EUV: el sustrato de vidrio sobre el que se escribe cada máscara","supplies":"Mask blanks EUV (el sustrato ultrapuro de cada máscara de vanguardia) y blanks de fotomáscara; sustratos de vidrio para HDD nearline y óptica médica/oftálmica.","moat":"Duopolio EUV con AGC (~2/3 de cuota Hoya); control de defectos casi atómico que nadie más domina; el vidrio para HDD nearline reacelera con el almacenamiento IA. Riesgo: estructura de conglomerado (salud ~60% de ventas) diluye la historia semi.","loc":"Japón","country":"Japon","growth":"🟢 +9%: blanks EUV y vidrio HDD tiran del grupo","margin":0.29,"capex_2026":"~¥100.000M: blanks EUV y vidrio HDD","backlog_status":"Capacidad EUV comprometida a >12 meses","role_en":"EUV mask-blank duopoly with AGC: the glass substrate every leading-edge mask is written on","supplies_en":"EUV mask blanks (the ultra-pure substrate behind every leading-edge mask) and photomask blanks; glass substrates for nearline HDDs plus medical/ophthalmic optics.","moat_en":"EUV duopoly with AGC (Hoya ~2/3 share); near-atomic defect control nobody else masters; nearline HDD glass reaccelerates with AI storage. Risk: conglomerate structure (healthcare ~60% of sales) dilutes the semis story.","growth_en":"🟢 +9%: EUV blanks and HDD glass lead the group","capex_2026_en":"~¥100B: EUV blanks and HDD glass","backlog_status_en":"EUV capacity committed 12+ months out","mkt":"HOCPY"},
  {"id":"ASML","label":"ASML","ticker":"ASML · Nasdaq","cat":"equip","port":"C1+C2","role":"Único fabricante mundial de máquinas de litografía EUV; cuello de botella de toda la cadena.","supplies":"Escáneres EUV de hasta €350M la unidad y la nueva generación High-NA EXE:5200, que graban transistores a escala atómica. Clientes: TSMC, Samsung, Intel y Micron — los tres primeros ya imprimen con High-NA.","moat":"Monopolio absoluto: sin ASML no existe ningún chip de vanguardia y replicarlo tomaría más de una década. Zeiss (ópticas) y Trumpf (láser) son proveedores exclusivos suyos; el único freno real son los controles de exportación a China.","loc":"Países Bajos","growth":"🔵 +19% 2026, +20% 2027","margin":0.35,"capex_2026":"~€2B (capacidad Veldhoven)","backlog_status":"Cartera ~€40B+; High-NA EXE:5200 ya en TSMC, Intel y Samsung","big":true,"country":"PaisesBajos","mkt":"ASML","role_en":"The world's only maker of EUV lithography machines; the bottleneck of the entire chain.","supplies_en":"EUV scanners of up to €350M apiece and the new-generation High-NA EXE:5200, which print transistors at atomic scale. Customers: TSMC, Samsung, Intel and Micron — the first three already printing with High-NA.","moat_en":"Absolute monopoly: without ASML no leading-edge chip exists, and replicating it would take more than a decade. Zeiss (optics) and Trumpf (laser) are its exclusive suppliers; the only real brake is export controls on China.","growth_en":"🔵 +19% 2026, +20% 2027","capex_2026_en":"~€2B (Veldhoven capacity)","backlog_status_en":"Backlog ~€40B+; High-NA EXE:5200 already at TSMC, Intel and Samsung"},
  {"id":"AMAT","label":"Applied Materials","ticker":"AMAT · Nasdaq","cat":"equip","port":"C1+C2","role":"Mayor proveedor mundial de equipamiento de fabricación; el portafolio más amplio de la industria.","supplies":"Sistemas de deposición de capas (CVD, ALD, PVD), implantación iónica y pulido CMP para TSMC, Samsung, Intel y los fabricantes de memoria. Cubre más pasos del proceso que cualquier rival.","moat":"Big Five del equipamiento. Amplitud inigualable: cada cambio de arquitectura (GAA, backside power) le vende en casi todos los pasos. Su CEO guió +20% de crecimiento para 2026. Riesgo: ~30% de ventas a China bajo controles de exportación.","loc":"EE.UU.","growth":"🔵 +20%+ revenue 2026","margin":0.3,"capex_2026":"~$2.5B (centro EPIC)","backlog_status":"Cartera ~$20B; visibilidad >12 meses","country":"EEUU","mkt":"AMAT","role_en":"The world's largest supplier of fab equipment, with the industry's broadest portfolio.","supplies_en":"Layer deposition (CVD, ALD, PVD), ion implantation and CMP polishing systems for TSMC, Samsung, Intel and the memory makers. Covers more process steps than any rival.","moat_en":"Equipment Big Five. Unmatched breadth: every architecture shift (GAA, backside power) sells it into nearly every step. Its CEO guided to +20% growth for 2026. Risk: ~30% of sales to China under export controls.","growth_en":"🔵 +20%+ revenue 2026","capex_2026_en":"~$2.5B (EPIC center)","backlog_status_en":"Backlog ~$20B; >12 months visibility"},
  {"id":"Lam","label":"Lam Research","ticker":"LRCX · Nasdaq","cat":"equip","port":"C1+C2","role":"Líder mundial en grabado por plasma; indispensable para memoria 3D y HBM.","supplies":"Máquinas de grabado que esculpen las estructuras 3D de los chips: críticas para la NAND de 200+ capas, el apilado de HBM de SK Hynix y los nodos lógicos avanzados de TSMC y Samsung.","moat":"Big Five. Domina el grabado de alta relación de aspecto — sin Lam no se fabrica memoria moderna. El superciclo de HBM4 para Vera Rubin y la recuperación de NAND juegan a su favor. Top pick de Bank of America en 2026.","loc":"EE.UU.","growth":"🔵 +15–20% anual","margin":0.33,"capex_2026":"~$0.9B","backlog_status":"Ingresos diferidos ~$2B; ciclo NAND/HBM en aceleración","country":"EEUU","mkt":"LRCX","role_en":"World leader in plasma etch; indispensable for 3D memory and HBM.","supplies_en":"Etch machines that sculpt chips' 3D structures: critical for 200+ layer NAND, SK Hynix's HBM stacking and the advanced logic nodes of TSMC and Samsung.","moat_en":"Big Five. Dominates high-aspect-ratio etch — without Lam, modern memory cannot be made. The HBM4 supercycle for Vera Rubin and the NAND recovery work in its favor. Bank of America top pick for 2026.","growth_en":"🔵 +15–20% per year","capex_2026_en":"~$0.9B","backlog_status_en":"Deferred revenue ~$2B; NAND/HBM cycle accelerating"},
  {"id":"KLA","label":"KLA","ticker":"KLAC · Nasdaq","cat":"equip","port":"C2","role":"Líder en inspección y metrología de obleas; los mejores márgenes del equipamiento.","supplies":"Sistemas que detectan defectos a nivel atómico en cada oblea y metrología de proceso para TSMC, Samsung e Intel. Sin su control de calidad, el rendimiento de los nodos de 2nm colapsa.","moat":"Big Five. Cuota >55% en inspección de proceso. La intensidad de inspección crece con cada generación: 2nm/1.4nm y el empaquetado avanzado (CoWoS) exigen más KLA por oblea. Margen operativo líder absoluto del sector.","loc":"EE.UU.","growth":"🔵 +15–18% anual","margin":0.41,"capex_2026":"~$0.4B — ligero","backlog_status":"RPO ~$13B (~18 meses de ingresos)","country":"EEUU","mkt":"KLAC","role_en":"Leader in wafer inspection and metrology, with the best margins in equipment.","supplies_en":"Systems that detect atomic-level defects on every wafer, plus process metrology for TSMC, Samsung and Intel. Without its quality control, yields at 2nm nodes collapse.","moat_en":"Big Five. >55% share in process inspection. Inspection intensity rises with every generation: 2nm/1.4nm and advanced packaging (CoWoS) demand more KLA per wafer. The sector's outright leader in operating margin.","growth_en":"🔵 +15–18% per year","capex_2026_en":"~$0.4B — asset-light","backlog_status_en":"RPO ~$13B (~18 months of revenue)"},
  {"id":"TEL","label":"Tokyo Electron","ticker":"8035 · TSE","cat":"equip","port":"","role":"Casi monopolio mundial en pistas de fotorresistencia (coater/developer).","supplies":"Máquinas que aplican y revelan las fotorresistencias antes y después de cada exposición litográfica — acopladas en línea a los escáneres EUV de ASML en TSMC, Samsung e Intel. También grabado y deposición.","moat":"Big Five. ~90% de cuota en pistas para EUV: cada máquina de ASML necesita una pista de TEL al lado. Riesgo: ~40% de sus ventas van a China, expuestas a controles de exportación.","loc":"Japón","growth":"🔵 +15–18% anual","margin":0.29,"capex_2026":"~¥200B (~$1.3B)","backlog_status":"Órdenes 6–9 meses; pistas EUV ligadas 1:1 a entregas de ASML","country":"Japon","mkt":"TOELY","role_en":"Near-monopoly worldwide in photoresist tracks (coater/developer).","supplies_en":"Machines that apply and develop photoresists before and after each lithography exposure — coupled in-line to ASML's EUV scanners at TSMC, Samsung and Intel. Also etch and deposition.","moat_en":"Big Five. ~90% share in EUV tracks: every ASML machine needs a TEL track beside it. Risk: ~40% of its sales go to China, exposed to export controls.","growth_en":"🔵 +15–18% per year","capex_2026_en":"~¥200B (~$1.3B)","backlog_status_en":"Orders 6–9 months; EUV tracks tied 1:1 to ASML deliveries"},
  {"id":"ASMInt","label":"ASM International","ticker":"ASM · Euronext","cat":"equip","port":"C2","role":"Líder mundial en deposición de capas atómicas (ALD).","supplies":"Reactores ALD y de epitaxia que depositan películas de pocos átomos de grosor — críticas para transistores GAA de 3nm/2nm y menores. Proveedor preferido de TSMC, Samsung e Intel en los pasos más finos del proceso.","moat":"Cuota >55% en ALD de oblea única. Cada transición de nodo multiplica los pasos ALD: GAA y backside power amplían su contenido por oblea. Más expuesto que sus pares a la lógica de vanguardia — ventaja en 2026.","loc":"Países Bajos","growth":"🔵 +18–22% anual","margin":0.27,"capex_2026":"~€350M","backlog_status":"Cartera ~€1.5B; pedidos GAA 2nm en máximos","country":"PaisesBajos","mkt":"ASMIY","role_en":"World leader in atomic layer deposition (ALD).","supplies_en":"ALD and epitaxy reactors that deposit films a few atoms thick — critical for GAA transistors at 3nm/2nm and below. Preferred supplier to TSMC, Samsung and Intel for the finest process steps.","moat_en":"Share >55% in single-wafer ALD. Each node transition multiplies ALD steps: GAA and backside power expand its content per wafer. More exposed than peers to leading-edge logic — an advantage in 2026.","growth_en":"🔵 +18–22% per year","capex_2026_en":"~€350M","backlog_status_en":"Backlog ~€1.5B; 2nm GAA orders at record highs"},
  {"id":"Nikon","label":"Nikon","ticker":"7731 · TSE","cat":"equip","port":"","role":"Segundo fabricante de litografía DUV; especialista en nodos maduros.","supplies":"Escáneres DUV ArF/KrF de inmersión para nodos de 10–38nm: fabs chinas (SMIC y otras), automoción y sensores. También litografía para paneles y equipos de medición óptica.","moat":"Segundo en DUV tras ASML, sin presencia en EUV. Su nicho son las fabs chinas que no acceden a equipos de vanguardia — negocio rentable pero rehén de los controles de exportación de EE.UU. y Japón.","loc":"Japón","growth":"🟡 +5–8% anual","margin":0.06,"capex_2026":"~¥50B (~$330M)","backlog_status":"Pedidos DUV ~2 años en nodos maduros; demanda china volátil","country":"Japon","mkt":"NINOY","role_en":"Second-largest DUV lithography maker; mature-node specialist.","supplies_en":"ArF/KrF immersion DUV scanners for 10–38nm nodes: Chinese fabs (SMIC and others), automotive and sensors. Also panel lithography and optical measurement equipment.","moat_en":"Second in DUV behind ASML, with no EUV presence. Its niche is Chinese fabs locked out of leading-edge tools — a profitable business but hostage to US and Japanese export controls.","growth_en":"🟡 +5–8% per year","capex_2026_en":"~¥50B (~$330M)","backlog_status_en":"DUV orders ~2 years at mature nodes; volatile Chinese demand"},
  {"id":"Canon","label":"Canon","ticker":"7751 · TSE","cat":"equip","port":"","role":"Litografía DUV de nodos maduros y apuesta disruptiva por nanoimprint (NIL).","supplies":"Escáneres DUV i-line/KrF para nodos maduros (fabs chinas, automoción) y sistemas de nanoimprint NIL desarrollados con Kioxia, que estampan patrones de ~14nm sin óptica de proyección a una fracción del costo del EUV.","moat":"Tercero en litografía. El NIL es su opción asimétrica: si escala en memoria 3D con Kioxia, abarata el patrón frente al EUV. Mientras tanto, el negocio DUV maduro depende de China y del grupo de imaging/impresión.","loc":"Japón","growth":"🟡 +5–10% anual","margin":0.08,"capex_2026":"~¥200B (grupo)","backlog_status":"NIL en producción piloto con Kioxia; DUV maduro estable","country":"Japon","mkt":"CAJPY","role_en":"Mature-node DUV lithography and a disruptive bet on nanoimprint (NIL).","supplies_en":"i-line/KrF DUV scanners for mature nodes (Chinese fabs, automotive) and NIL nanoimprint systems developed with Kioxia, which stamp ~14nm patterns without projection optics at a fraction of EUV's cost.","moat_en":"Third in lithography. NIL is its asymmetric option: if it scales in 3D memory with Kioxia, it makes patterning cheaper than EUV. Meanwhile, the mature DUV business depends on China and on the imaging/printing group.","growth_en":"🟡 +5–10% per year","capex_2026_en":"~¥200B (group)","backlog_status_en":"NIL in pilot production with Kioxia; mature DUV stable"},
  {"id":"Disco","label":"Disco","ticker":"6146 · TSE","cat":"equip","port":"","role":"Cuasi-monopolio (~80%) en corte (dicing) y rectificado de obleas; crítico para adelgazar HBM","supplies":"Sierras de dicing, rectificadoras y láser para cortar y adelgazar obleas; las hojas consumibles aportan ingresos recurrentes. El apilado HBM4 exige adelgazar DRAM a <30µm.","moat":"~80% de cuota mundial en dicing y grinding; consumibles (blades) cautivos y recurrentes; cada capa adicional de HBM añade pasos de adelgazado a <30µm. Riesgo: alta exposición al ciclo de memoria y concentración en SK Hynix/Samsung.","loc":"Japón","country":"Japon","growth":"🔵 +25% impulsado por thinning HBM4","margin":0.4,"capex_2026":"~¥60.000M: Kuwana y Nagano ampliándose","backlog_status":"Récord; trimestres de visibilidad por HBM4","role_en":"Near-monopoly (~80%) in wafer dicing and grinding; critical for HBM wafer thinning","supplies_en":"Dicing saws, grinders and laser tools to cut and thin wafers; consumable blades add recurring revenue. HBM4 stacking requires thinning DRAM below 30µm.","moat_en":"~80% global share in dicing and grinding; captive, recurring consumable blades; every extra HBM layer adds sub-30µm thinning steps. Risk: heavy memory-cycle exposure and customer concentration in SK Hynix/Samsung.","growth_en":"🔵 +25% driven by HBM4 thinning","capex_2026_en":"~¥60B: Kuwana and Nagano expansions","backlog_status_en":"Record; quarters of visibility on HBM4","mkt":"DSCSY"},
  {"id":"Screen","label":"Screen Holdings","ticker":"7735 · TSE","cat":"equip","port":"","role":"Screen Holdings, líder mundial en limpieza húmeda de obleas, el paso más repetido de la fab","supplies":"Equipos de limpieza húmeda monooblea y por lotes para foundries y memoria; cada oblea avanzada pasa por cientos de limpiezas. También coaters/developers y equipos de impresión.","moat":"~45% de cuota en limpieza húmeda; el cleaning se repite en cientos de pasos y crece con cada nodo (GAA, backside power). Riesgo: 30-40% de ventas a China bajo presión regulatoria y Naura copiando desde abajo.","loc":"Japón","country":"Japon","growth":"🟢 +10% en un año de WFE récord","margin":0.17,"capex_2026":"~¥40.000M, capacidad en Hikone","backlog_status":"Sano; GAA y HBM compensan la caída china","role_en":"Screen Holdings, world leader in wafer wet cleaning, the fab's most repeated process step","supplies_en":"Single-wafer and batch wet-cleaning tools for foundries and memory; every advanced wafer undergoes hundreds of cleans. Also coater/developers and printing equipment.","moat_en":"~45% share in wet cleaning; cleans recur across hundreds of steps and grow with each node (GAA, backside power). Risk: 30-40% of sales to China under regulatory pressure, with Naura copying from below.","growth_en":"🟢 +10% in a record WFE year","capex_2026_en":"~¥40B, Hikone capacity build-out","backlog_status_en":"Healthy; GAA and HBM offset the China decline","mkt":"DINRF"},
  {"id":"Naura","label":"Naura Technology","ticker":"002371 · SZSE","cat":"equip","port":"","role":"Mayor fabricante chino de equipos de semiconductores; buque insignia de la sustitución doméstica","supplies":"Grabado, depósito (CVD/PVD/ALD), hornos y limpieza para SMIC, Hua Hong, YMTC y CXMT; el portfolio de equipos más amplio de China.","moat":"Las sanciones obligan a SMIC, Hua Hong y YMTC a comprar local: demanda cautiva con respaldo del Big Fund. Portfolio más amplio de China (grabado, depo, limpieza). Riesgo: 1-2 generaciones por detrás de AMAT/Lam y sin componentes occidentales críticos.","loc":"China","country":"China","growth":"🔵 +35% por sustitución doméstica forzada","margin":0.2,"capex_2026":"Elevado: nuevos campus en Pekín","backlog_status":"Récord: las fabs chinas compran todo lo local","role_en":"China's largest chip-equipment maker; flagship of forced domestic substitution","supplies_en":"Etch, deposition (CVD/PVD/ALD), furnace and clean tools for SMIC, Hua Hong, YMTC and CXMT; the broadest equipment portfolio in China.","moat_en":"Sanctions force SMIC, Hua Hong and YMTC to buy local: captive demand backed by the Big Fund. Broadest toolkit in China (etch, deposition, clean). Risk: 1-2 generations behind AMAT/Lam and cut off from critical Western components.","growth_en":"🔵 +35% on forced domestic substitution","capex_2026_en":"Heavy: new Beijing campuses","backlog_status_en":"Record: Chinese fabs buy everything local"},
  {"id":"AMEC","label":"AMEC","ticker":"688012 · STAR","cat":"equip","port":"","role":"Especialista chino en grabado por plasma; histórico proveedor de TSMC y campeón doméstico del etch","supplies":"Grabadores de plasma CCP e ICP para lógica avanzada y NAND 3D; expansión a depósito (LPCVD, EPI). Proveedor clave de SMIC, YMTC y, históricamente, TSMC.","moat":"Único equipero chino cualificado históricamente en TSMC (hasta 5nm); el grabado es el paso más crítico de la NAND 3D y AMEC es el estándar local. Riesgo: fuera de China compite contra Lam/TEL y aún depende de subsidios y componentes importados.","loc":"China","country":"China","growth":"🔵 +35% con las fabs chinas a plena carga","margin":0.22,"capex_2026":"Alto: campus de Lingang en expansión","backlog_status":"Fuerte; pedidos prioritarios de SMIC y YMTC","role_en":"China's plasma-etch specialist; historic TSMC supplier and domestic etch champion","supplies_en":"CCP and ICP plasma etchers for advanced logic and 3D NAND; expanding into deposition (LPCVD, EPI). Key supplier to SMIC, YMTC and, historically, TSMC.","moat_en":"The only Chinese toolmaker historically qualified at TSMC (down to 5nm); etch is 3D NAND's most critical step and AMEC is the local standard. Risk: outside China it faces Lam/TEL head-on and still leans on subsidies and imported parts.","growth_en":"🔵 +35% with Chinese fabs at full tilt","capex_2026_en":"High: Lingang campus expansion","backlog_status_en":"Strong; priority orders from SMIC and YMTC"},
  {"id":"ShinEtsu","label":"Shin-Etsu Chemical","ticker":"4063 · TSE","cat":"materials","port":"C2","role":"Mayor proveedor mundial de obleas de silicio de 300mm; la base física de todo chip avanzado.","supplies":"Discos de silicio de 300mm de pureza extrema — la \"hoja en blanco\" sobre la que se graban los transistores — para TSMC, Samsung y Micron. También fotorresistencias EUV y siliconas especiales.","moat":"Con SUMCO controla ~60% del mercado global de obleas; la escasez proyectada hasta 2027-2028 le da poder de precio. Su calidad epitaxial tarda décadas en replicarse.","loc":"Japón","growth":"🟢 +10–14% anual","margin":0.3,"capex_2026":"~$3B (¥450B, grupo)","backlog_status":"LTAs con prepagos hasta 2027–2028","country":"Japon","mkt":"SHECY","role_en":"The world's largest supplier of 300mm silicon wafers; the physical foundation of every advanced chip.","supplies_en":"Ultra-pure 300mm silicon discs — the \"blank sheet\" on which transistors are printed — for TSMC, Samsung and Micron. Also EUV photoresists and specialty silicones.","moat_en":"With SUMCO it controls ~60% of the global wafer market; the shortage projected through 2027-2028 gives it pricing power. Its epitaxial quality takes decades to replicate.","growth_en":"🟢 +10–14% per year","capex_2026_en":"~$3B (¥450B, group)","backlog_status_en":"LTAs with prepayments through 2027–2028"},
  {"id":"SUMCO","label":"SUMCO","ticker":"3436 · TSE","cat":"materials","port":"","role":"Segundo mayor fabricante mundial de obleas de silicio; pure-play del sustrato base.","supplies":"Obleas de silicio de 300mm pulidas y epitaxiales para lógica y memoria. Proveedor clave de TSMC, Samsung y Micron bajo contratos de largo plazo prepagados.","moat":"Oligopolio con Shin-Etsu (~60% conjunto en 300mm). Construir capacidad de obleas de alta calidad toma décadas, y la demanda de IA absorbe la oferta disponible hasta 2028.","loc":"Japón","growth":"🟢 +8–12% anual","margin":0.15,"capex_2026":"~$1.6B (¥240B)","backlog_status":"LTAs prepagados hasta 2029","country":"Japon","mkt":"SUOPY","role_en":"The world's second-largest silicon wafer maker; a pure play on the base substrate.","supplies_en":"Polished and epitaxial 300mm silicon wafers for logic and memory. Key supplier to TSMC, Samsung and Micron under prepaid long-term contracts.","moat_en":"Oligopoly with Shin-Etsu (~60% combined in 300mm). Building high-quality wafer capacity takes decades, and AI demand absorbs the available supply through 2028.","growth_en":"🟢 +8–12% per year","capex_2026_en":"~$1.6B (¥240B)","backlog_status_en":"Prepaid LTAs through 2029"},
  {"id":"Siltronic","label":"Siltronic","ticker":"WAF · Frankfurt","cat":"materials","port":"","role":"Único fabricante europeo de obleas de silicio; tercer-cuarto proveedor global.","supplies":"Obleas 300mm pulidas y epitaxiales para TSMC, Samsung y las fabs europeas. Su nueva planta de Singapur añade la capacidad que servirá el ciclo de IA.","moat":"Única alternativa europea en un oligopolio de cinco jugadores — valor estratégico para la soberanía de la UE. Riesgo: escala menor que Shin-Etsu/SUMCO y margen presionado por la depreciación de Singapur.","loc":"Alemania","growth":"🟢 +7–10% anual","margin":0.08,"capex_2026":"~€350–450M (post-pico)","backlog_status":"LTAs plurianuales, algunos renegociados","country":"Alemania","mkt":"SSLLF","role_en":"Europe's only silicon wafer maker; the third-to-fourth global supplier.","supplies_en":"Polished and epitaxial 300mm wafers for TSMC, Samsung and Europe's fabs. Its new Singapore plant adds the capacity that will serve the AI cycle.","moat_en":"The only European alternative in a five-player oligopoly — strategic value for EU sovereignty. Risk: smaller scale than Shin-Etsu/SUMCO and margin pressured by Singapore depreciation.","growth_en":"🟢 +7–10% per year","capex_2026_en":"~€350–450M (post-peak)","backlog_status_en":"Multi-year LTAs, some renegotiated"},
  {"id":"GlobalWafers","label":"GlobalWafers","ticker":"6488 · TWSE","cat":"materials","port":"","role":"Tercer-cuarto proveedor global de obleas; el más diversificado geográficamente.","supplies":"Obleas 200/300mm, epitaxiales y SOI para RF y automotive a TSMC, Samsung y GlobalFoundries. Su fab nueva de Sherman, Texas — primera de 300mm en EE.UU. en 20+ años — sirve la relocalización americana.","moat":"Cuarto proveedor global con 18 fabs en 9 países; única oblea avanzada \"Made in USA\", favorecida por el CHIPS Act. Riesgo principal: la ejecución de la rampa de Texas.","loc":"Taiwán","growth":"🟢 +8–11% anual","margin":0.22,"capex_2026":"~$1B (rampa Texas)","backlog_status":"LTAs con prepagos; Texas en rampa 2026","country":"Taiwan","role_en":"Third-to-fourth global wafer supplier; the most geographically diversified.","supplies_en":"200/300mm, epitaxial and SOI wafers for RF and automotive to TSMC, Samsung and GlobalFoundries. Its new Sherman, Texas fab — the first 300mm in the US in 20+ years — serves American reshoring.","moat_en":"Fourth global supplier with 18 fabs in 9 countries; the only advanced \"Made in USA\" wafer, favored by the CHIPS Act. Main risk: execution of the Texas ramp.","growth_en":"🟢 +8–11% per year","capex_2026_en":"~$1B (Texas ramp)","backlog_status_en":"LTAs with prepayments; Texas ramping in 2026"},
  {"id":"Ajinomoto","label":"Ajinomoto","ticker":"2802 · TSE","cat":"chemicals","port":"C2","role":"Monopolio del film ABF — joya electrónica camuflada como empresa de alimentos.","supplies":"ABF (Ajinomoto Build-up Film): la película aislante que forma las capas de los sustratos de TODOS los chips de IA — sin ABF no existe el H100 ni el GB200. La suministra a Ibiden, Unimicron y el resto de sustrateros.","moat":"Monopolio efectivo sin sustituto calificado: ningún rival ha pasado la calificación en 25 años. El mercado la valora como empresa de MSG y sopas → oportunidad de re-rating estructural.","loc":"Japón","growth":"🔵 +18–25% anual (división electrónica)","margin":0.11,"capex_2026":"~$900M (grupo; ABF +50% capacidad)","backlog_status":"ABF en asignación; capacidad comprometida 2027","country":"Japon","mkt":"AJINY","role_en":"ABF film monopoly — an electronics gem disguised as a food company.","supplies_en":"ABF (Ajinomoto Build-up Film): the insulating film that forms the substrate layers of ALL AI chips — without ABF there is no H100 or GB200. Supplied to Ibiden, Unimicron and the rest of the substrate makers.","moat_en":"Effective monopoly with no qualified substitute: no rival has passed qualification in 25 years. The market values it as an MSG-and-soup company → a structural re-rating opportunity.","growth_en":"🔵 +18–25% per year (electronics division)","capex_2026_en":"~$900M (group; ABF capacity +50%)","backlog_status_en":"ABF on allocation; capacity committed through 2027"},
  {"id":"JSR","label":"JSR","ticker":"Estatizada (JIC 2024)","cat":"chemicals","port":"","role":"Líder en fotorresistencias EUV, estatizada por el fondo JIC como activo estratégico de Japón.","supplies":"Las sustancias fotosensibles que permiten grabar los patrones del chip con luz EUV, para TSMC, Samsung e Intel. Declarada activo estratégico nacional por Japón.","moat":"Uno de los dos únicos proveedores calificados de resists EUV del mundo (duopolio con Tokyo Ohka). El gobierno japonés financia su expansión vía JIC — capital paciente sin presión bursátil.","loc":"Japón","growth":"🔵 +15–22% anual","margin":0.09,"capex_2026":"~$400M (financiado por JIC)","backlog_status":"Calificada en las rampas 2nm de TSMC/Samsung","country":"Japon","role_en":"Leader in EUV photoresists, nationalized by the JIC fund as a strategic asset of Japan.","supplies_en":"The photosensitive compounds that allow chip patterns to be printed with EUV light, for TSMC, Samsung and Intel. Declared a national strategic asset by Japan.","moat_en":"One of only two qualified EUV resist suppliers in the world (duopoly with Tokyo Ohka). The Japanese government funds its expansion via JIC — patient capital with no stock-market pressure.","growth_en":"🔵 +15–22% per year","capex_2026_en":"~$400M (funded by JIC)","backlog_status_en":"Qualified in TSMC/Samsung 2nm ramps"},
  {"id":"Entegris","label":"Entegris","ticker":"ENTG · Nasdaq","cat":"chemicals","port":"","role":"Líder en sistemas de pureza, filtración y manejo de materiales para fabs.","supplies":"Filtración de químicos y gases ultra-puros, y los contenedores FOUP que transportan obleas sin contaminarlas, para TSMC, Micron, Samsung e Intel. Más del 75% de sus ventas son consumibles recurrentes.","moat":"Sin Entegris los químicos contaminan las obleas: cada salto de nodo (2nm/1nm) exige más pasos de filtración y multiplica su contenido por oblea. Cuota dominante en FOUPs y filtración de líquidos.","loc":"EE.UU.","growth":"🟢 +12–15% anual","margin":0.2,"capex_2026":"~$400M (Colorado, Kaohsiung)","backlog_status":"Visibilidad 12+ meses ligada a fabs nuevas","country":"EEUU","mkt":"ENTG","role_en":"Leader in purity systems, filtration and materials handling for fabs.","supplies_en":"Ultra-pure chemical and gas filtration, plus the FOUP pods that carry wafers without contaminating them, for TSMC, Micron, Samsung and Intel. More than 75% of sales are recurring consumables.","moat_en":"Without Entegris, chemicals contaminate the wafers: every node jump (2nm/1nm) requires more filtration steps and multiplies its content per wafer. Dominant share in FOUPs and liquid filtration.","growth_en":"🟢 +12–15% per year","capex_2026_en":"~$400M (Colorado, Kaohsiung)","backlog_status_en":"12+ months visibility tied to new fabs"},
  {"id":"TokyoOhka","label":"Tokyo Ohka Kogyo","ticker":"4186 · TSE","cat":"chemicals","port":"","role":"Mayor fabricante mundial de fotorresistencias por volumen; duopolio EUV con JSR.","supplies":"Resists DUV/EUV, developers y químicos de litografía para TSMC, Samsung, SK Hynix y Micron. Líder en resists para empaquetado avanzado y grabado de alta relación de aspecto en NAND.","moat":"Duopolio con JSR en resists EUV (~70–80% conjunto); calificar una receta con un fab toma años. A diferencia de JSR sigue cotizada — el pure-play accesible del segmento.","loc":"Japón","growth":"🟢 +12–16% anual","margin":0.18,"capex_2026":"~$300M (¥45B)","backlog_status":"Capacidad EUV comprometida con los 3 grandes","country":"Japon","role_en":"The world's largest photoresist maker by volume; EUV duopoly with JSR.","supplies_en":"DUV/EUV resists, developers and lithography chemicals for TSMC, Samsung, SK Hynix and Micron. Leader in resists for advanced packaging and high-aspect-ratio NAND etch.","moat_en":"Duopoly with JSR in EUV resists (~70–80% combined); qualifying a recipe with a fab takes years. Unlike JSR it remains listed — the segment's accessible pure play.","growth_en":"🟢 +12–16% per year","capex_2026_en":"~$300M (¥45B)","backlog_status_en":"EUV capacity committed to the big three"},
  {"id":"MerckKGaA","label":"Merck KGaA","ticker":"MRK · Frankfurt","cat":"chemicals","port":"","role":"Conglomerado alemán cuya división Electronics es top-3 mundial en materiales de semiconductores.","supplies":"Precursores CVD/ALD (heredados de Versum), gases especiales, solventes ultra-puros y materiales de patterning para TSMC, Samsung e Intel. Su unidad de delivery systems instala la distribución química dentro de las fabs.","moat":"El portafolio de materiales más amplio del sector tras comprar Versum ($6.5B) e Intermolecular. La división Electronics crece a doble dígito, pero queda diluida en un grupo de farma y life science.","loc":"Alemania","growth":"🟢 +9–13% anual","margin":0.19,"capex_2026":"~€2B (grupo)","backlog_status":"Pedidos ligados a rampas 2nm; 6–12 meses","country":"Alemania","mkt":"MKKGY","role_en":"German conglomerate whose Electronics division ranks top-3 worldwide in semiconductor materials.","supplies_en":"CVD/ALD precursors (inherited from Versum), specialty gases, ultra-pure solvents and patterning materials for TSMC, Samsung and Intel. Its delivery systems unit installs the chemical distribution inside the fabs.","moat_en":"The broadest materials portfolio in the sector after acquiring Versum ($6.5B) and Intermolecular. The Electronics division grows at double digits, but is diluted within a pharma and life science group.","growth_en":"🟢 +9–13% annually","capex_2026_en":"~€2B (group)","backlog_status_en":"Orders tied to 2nm ramps; 6–12 months"},
  {"id":"Linde","label":"Linde","ticker":"LIN · Nasdaq","cat":"chemicals","port":"","role":"Mayor gasista industrial del mundo; el nitrógeno y el helio de cada fab avanzada.","supplies":"N₂, Ar, H₂ y He ultra-puros más NF₃ y gases de proceso, con plantas on-site dentro de las fabs de TSMC, Samsung e Intel bajo contratos take-or-pay de 15–20 años.","moat":"Mayor empresa global de gases con disciplina de precio probada; una vez instalada la planta on-site, cambiar de proveedor es casi imposible. Ingresos tipo infraestructura con clientes cautivos.","loc":"Irlanda / EE.UU.","growth":"🟢 +9–13% anual (BPA)","margin":0.28,"capex_2026":"~$5–5.5B","backlog_status":"Backlog de proyectos >$10B (on-site)","country":"EEUU","mkt":"LIN","role_en":"World's largest industrial gas company; the nitrogen and helium behind every advanced fab.","supplies_en":"Ultra-pure N₂, Ar, H₂ and He plus NF₃ and process gases, with on-site plants inside TSMC, Samsung and Intel fabs under 15–20 year take-or-pay contracts.","moat_en":"The world's largest gas company with proven pricing discipline; once the on-site plant is installed, switching suppliers is nearly impossible. Infrastructure-like revenue with captive customers.","growth_en":"🟢 +9–13% annually (EPS)","capex_2026_en":"~$5–5.5B","backlog_status_en":"Project backlog >$10B (on-site)"},
  {"id":"AirLiquide","label":"Air Liquide","ticker":"AI · Euronext","cat":"chemicals","port":"","role":"Segundo gasista mundial; líder en precursores ALD para deposición atómica.","supplies":"Gases ultra-puros y precursores ALD/CVD avanzados (vía Air Liquide Electronics) con servicio on-site para TSMC, Samsung y las fabs nuevas de EE.UU. y Europa.","moat":"Número 2 en gases con fortaleza diferencial en moléculas ALD, justo donde los nodos 2nm multiplican los pasos de deposición. Contratos on-site de 15 años hacen los ingresos casi inamovibles.","loc":"Francia","growth":"🟢 +8–11% anual","margin":0.19,"capex_2026":"~€4B","backlog_status":"Cartera de inversión ~€4.5B decidida","country":"Francia","mkt":"AIQUY","role_en":"World's second-largest industrial gas company; leader in ALD precursors for atomic-layer deposition.","supplies_en":"Ultra-pure gases and advanced ALD/CVD precursors (via Air Liquide Electronics) with on-site service for TSMC, Samsung and the new fabs in the US and Europe.","moat_en":"Number 2 in gases with differentiated strength in ALD molecules, precisely where 2nm nodes multiply deposition steps. 15-year on-site contracts make revenue nearly immovable.","growth_en":"🟢 +8–11% annually","capex_2026_en":"~€4B","backlog_status_en":"Investment pipeline of ~€4.5B already committed"},
  {"id":"TSMC","label":"TSMC","ticker":"TSM · NYSE","cat":"foundry","port":"C1+C2","role":"La fundición que fabrica el 90%+ de los chips de vanguardia del mundo.","supplies":"Fabricación de chips lógicos de 3nm y 2nm más empaquetado avanzado CoWoS para Nvidia, Apple, AMD y Qualcomm. El nodo N2 entra en rampa de volumen en 2026, con fabs en expansión en Arizona, Japón y Alemania.","moat":"Monopolio técnico estructural: sin TSMC no hay iPhone, ni Vera Rubin, ni chip de AMD. Es el punto de fallo único más crítico de toda la cadena, irremplazable en 10+ años; su riesgo es la concentración geopolítica en Taiwán.","loc":"Taiwán (+ Arizona, Japón, Alemania)","growth":"🔵 +35% 2026, +26% 2027","margin":0.49,"capex_2026":"$52–56B","backlog_status":"CoWoS agotado hasta 2027","big":true,"country":"Taiwan","mkt":"TSM","role_en":"The foundry that manufactures 90%+ of the world's leading-edge chips.","supplies_en":"3nm and 2nm logic chip manufacturing plus advanced CoWoS packaging for Nvidia, Apple, AMD and Qualcomm. The N2 node enters volume ramp in 2026, with fabs expanding in Arizona, Japan and Germany.","moat_en":"Structural technical monopoly: without TSMC there is no iPhone, no Vera Rubin, no AMD chip. The most critical single point of failure in the entire chain, irreplaceable for 10+ years; its risk is geopolitical concentration in Taiwan.","growth_en":"🔵 +35% 2026, +26% 2027","capex_2026_en":"$52–56B","backlog_status_en":"CoWoS sold out through 2027"},
  {"id":"Samsung","label":"Samsung Electronics","ticker":"005930 · KRX","cat":"foundry","port":"","role":"IDM integrado: líder histórico en memoria y segunda foundry avanzada del mundo.","supplies":"DRAM, NAND y HBM, SoCs Exynos y la segunda foundry más avanzada del mundo (3nm/2nm GAA). Ganó el chip AI6 de Tesla (contrato ~$16.5B en su fab de Taylor, Texas) y comparte la fabricación del AI5 con TSMC.","moat":"Único rival cercano a TSMC en foundry de vanguardia, aunque con rendimientos inferiores en GAA; en HBM persigue a SK Hynix (~64% de cuota). Conglomerado integrado verticalmente con escala inigualada en memoria.","loc":"Corea del Sur","growth":"🔵 +15–20% 2026 (ciclo de memoria)","margin":0.2,"capex_2026":"~$45B (memoria + foundry)","backlog_status":"Contrato Tesla ~$16.5B; HBM vendida para 2026","country":"Corea","mkt":"SSNLF","role_en":"Integrated IDM: historic leader in memory and the world's second most advanced foundry.","supplies_en":"DRAM, NAND and HBM, Exynos SoCs and the world's second most advanced foundry (3nm/2nm GAA). Won Tesla's AI6 chip (~$16.5B contract at its Taylor, Texas fab) and shares AI5 production with TSMC.","moat_en":"The only close rival to TSMC in leading-edge foundry, albeit with lower GAA yields; in HBM it chases SK Hynix (~64% share). Vertically integrated conglomerate with unmatched scale in memory.","growth_en":"🔵 +15–20% 2026 (memory cycle)","capex_2026_en":"~$45B (memory + foundry)","backlog_status_en":"Tesla contract ~$16.5B; HBM sold out for 2026"},
  {"id":"Intel","label":"Intel","ticker":"INTC · Nasdaq","cat":"foundry","port":"","role":"IDM estadounidense en plena reconversión, con respaldo directo del gobierno de EE.UU.","supplies":"CPUs Core y Xeon más Intel Foundry, que con el nodo 18A en rampa en Arizona busca fabricar para terceros. Nvidia invirtió $5B y co-diseña CPUs x86 con chiplets de GPU para data center y PC.","moat":"El gobierno de EE.UU. tomó ~10% del capital (ago 2025): es la apuesta soberana occidental frente a TSMC. La ejecución del 18A y los rendimientos del futuro 14A son el factor decisivo de su recuperación tras años de retrasos.","loc":"EE.UU.","growth":"🟡 +5–8% 2026","margin":0.05,"capex_2026":"~$20–25B","backlog_status":"18A: Microsoft y AWS como clientes externos iniciales","country":"EEUU","mkt":"INTC","role_en":"US IDM in the midst of a turnaround, with direct backing from the US government.","supplies_en":"Core and Xeon CPUs plus Intel Foundry, which with the 18A node ramping in Arizona aims to manufacture for third parties. Nvidia invested $5B and co-designs x86 CPUs with GPU chiplets for data center and PC.","moat_en":"The US government took ~10% of the equity (Aug 2025): it is the Western sovereign bet against TSMC. Execution on 18A and yields on the future 14A are the decisive factor in its recovery after years of delays.","growth_en":"🟡 +5–8% 2026","capex_2026_en":"~$20–25B","backlog_status_en":"18A: Microsoft and AWS as initial external customers"},
  {"id":"GF","label":"GlobalFoundries","ticker":"GFS · Nasdaq","cat":"foundry","port":"","role":"Principal foundry estadounidense de nodos maduros y especializados.","supplies":"Chips de 12 a 180nm para RF, automotive, IoT y defensa, más fotónica de silicio: fabrica los chips fotónicos de PsiQuantum y componentes para la interconexión óptica de data centers de IA.","moat":"Estratégico para la seguridad nacional de EE.UU. y beneficiario del CHIPS Act; sin ambiciones en vanguardia, compite por especialización y contratos de largo plazo. La fotónica de silicio le da una opción cuántica y de IA.","loc":"EE.UU.","growth":"🟡 +5–9% 2026","margin":0.1,"capex_2026":"~$1.5–2B","backlog_status":"LTAs plurianuales; rampa fotónica con PsiQuantum","country":"EEUU","mkt":"GFS","role_en":"Leading US foundry for mature and specialty nodes.","supplies_en":"12 to 180nm chips for RF, automotive, IoT and defense, plus silicon photonics: it manufactures PsiQuantum's photonic chips and components for the optical interconnect of AI data centers.","moat_en":"Strategic for US national security and a CHIPS Act beneficiary; with no leading-edge ambitions, it competes on specialization and long-term contracts. Silicon photonics gives it a quantum and AI option.","growth_en":"🟡 +5–9% 2026","capex_2026_en":"~$1.5–2B","backlog_status_en":"Multi-year LTAs; photonics ramp with PsiQuantum"},
  {"id":"SMIC","label":"SMIC","ticker":"688981 · STAR","cat":"foundry","port":"","role":"La mayor foundry de China y pieza central de su autosuficiencia en chips.","supplies":"Nodos de 14–180nm — y 7nm vía DUV multipatterning a bajo rendimiento — para Huawei, las fabless chinas y automotive. Bloqueada de acceder al EUV de ASML por las sanciones de EE.UU.","moat":"Respaldo estatal masivo y demanda china cautiva por la localización forzada de chips; pero sin EUV su costo por oblea sub-7nm es estructuralmente alto y la brecha con TSMC se ensancha cada nodo.","loc":"China","growth":"🟢 +10–15% 2026","margin":0.12,"capex_2026":"~$7–7.5B","backlog_status":"Utilización >85%; demanda doméstica cautiva (Huawei)","country":"China","mkt":"SMICY","role_en":"China's largest foundry and the centerpiece of its chip self-sufficiency drive.","supplies_en":"14–180nm nodes — and 7nm via low-yield DUV multipatterning — for Huawei, Chinese fabless players and automotive. Blocked from ASML's EUV by US sanctions.","moat_en":"Massive state backing and captive Chinese demand from forced chip localization; but without EUV its sub-7nm cost per wafer is structurally high and the gap with TSMC widens with every node.","growth_en":"🟢 +10–15% 2026","capex_2026_en":"~$7–7.5B","backlog_status_en":"Utilization >85%; captive domestic demand (Huawei)"},
  {"id":"Rapidus","label":"Rapidus","ticker":"Estatal (no cotiza)","cat":"foundry","port":"","role":"Foundry estatal japonesa que apunta a producir 2nm en 2027 con tecnología de IBM.","supplies":"Aún pre-ingresos: línea piloto de 2nm GAA operativa en Chitose (Hokkaido) desde 2025, con primeros prototipos para diseñadores de chips de IA y objetivo de producción en volumen en 2027.","moat":"Respaldo estatal de $35B+ y licencia del proceso 2nm de IBM, pero sin historial de fabricación en volumen: debe demostrar rendimientos y atraer clientes desde cero frente a TSMC y Samsung.","loc":"Japón","growth":"⭐ PRE-IPO · pre-ingresos; 2nm en volumen 2027","margin":null,"capex_2026":"~$5–7B (fondos estatales)","backlog_status":"Sin órdenes firmes; MOUs (Tenstorrent, PFN)","preipo":true,"country":"Japon","role_en":"Japanese state-backed foundry targeting 2nm production in 2027 with IBM technology.","supplies_en":"Still pre-revenue: a 2nm GAA pilot line operating in Chitose (Hokkaido) since 2025, with first prototypes for AI chip designers and volume production targeted for 2027.","moat_en":"$35B+ in state backing and a license to IBM's 2nm process, but no volume manufacturing track record: it must prove yields and attract customers from scratch against TSMC and Samsung.","growth_en":"⭐ PRE-IPO · pre-revenue; 2nm in volume 2027","capex_2026_en":"~$5–7B (state funds)","backlog_status_en":"No firm orders; MOUs (Tenstorrent, PFN)"},
  {"id":"TexasInstruments","label":"Texas Instruments","ticker":"TXN · Nasdaq","cat":"foundry","port":"","role":"Líder mundial en chips analógicos; gestión de energía y señal presente en cada servidor y data center","supplies":"Catálogo de ~80.000 chips analógicos y embebidos: gestión de potencia, conversión de datos y sensado para data centers, industria y automoción; potencia 48V para racks de IA.","moat":"Fabs propias 300mm en EE.UU. (Sherman, Lehi) con ventaja de coste ~40% por chip y subsidios CHIPS; catálogo de 80.000 referencias con venta directa a 100.000 clientes. Riesgo: digestión de un capex de ~$5.000M/año y guerra de precios analógica en China.","loc":"EE.UU.","country":"EEUU","growth":"🟢 +12%: ciclo analógico + potencia para DC","margin":0.38,"capex_2026":"~$5.000M: Sherman fase 2 en rampa","backlog_status":"Normalizado; reactivación industrial incipiente","role_en":"World leader in analog chips; power and signal management inside every server and data center","supplies_en":"Catalog of ~80,000 analog and embedded chips: power management, data conversion and sensing for data centers, industrial and automotive; 48V power for AI racks.","moat_en":"Own US 300mm fabs (Sherman, Lehi) with a ~40% per-chip cost edge plus CHIPS subsidies; an 80,000-part catalog sold direct to 100,000 customers. Risk: digesting ~$5B/year of capex and an analog price war in China.","growth_en":"🟢 +12%: analog upcycle plus DC power","capex_2026_en":"~$5B: Sherman phase 2 ramping","backlog_status_en":"Normalized; early industrial restocking","mkt":"TXN"},
  {"id":"Infineon","label":"Infineon","ticker":"IFX · Frankfurt","cat":"foundry","port":"","role":"Nº1 mundial en semiconductores de potencia; SiC/GaN y módulos 800 VDC para data centers de IA","supplies":"Módulos de potencia y MOSFETs SiC/GaN para la conversión 800 VDC de racks de IA (socio de Nvidia); microcontroladores y potencia para automoción e industria.","moat":"Nº1 mundial en potencia (~20% de cuota) y socio de Nvidia en la arquitectura 800 VDC; fab SiC de 200mm en Kulim; negocio de potencia IA duplicándose hacia ~€1.500M. Riesgo: automoción (~50% de ventas) débil y sobrecapacidad china en SiC.","loc":"Alemania","country":"Alemania","growth":"🟢 +9%: potencia IA duplica, automoción plana","margin":0.2,"capex_2026":"~€2.500M: Kulim SiC y Dresde 300mm","backlog_status":"Auto normalizado; pedidos IA 800 VDC acelerando","role_en":"World No. 1 in power semiconductors; SiC/GaN and 800 VDC modules for AI data centers","supplies_en":"Power modules and SiC/GaN MOSFETs for 800 VDC conversion in AI racks (Nvidia partner); microcontrollers and power chips for automotive and industrial.","moat_en":"World No. 1 in power semis (~20% share) and Nvidia's partner on the 800 VDC architecture; 200mm SiC fab in Kulim; AI power business doubling toward ~€1.5B. Risk: autos (~50% of sales) stay soft and Chinese SiC overcapacity bites.","growth_en":"🟢 +9%: AI power doubles, autos flat","capex_2026_en":"~€2.5B: Kulim SiC and Dresden 300mm","backlog_status_en":"Autos normalized; 800 VDC AI orders accelerating","mkt":"IFNNY"},
  {"id":"onsemi","label":"onsemi","ticker":"ON · Nasdaq","cat":"foundry","port":"","role":"Especialista en SiC y potencia inteligente para data centers de IA, vehículo eléctrico e industria","supplies":"MOSFETs y módulos EliteSiC para distribución de potencia en data centers IA y tracción EV; sensores de imagen para ADAS; gestión de potencia industrial.","moat":"Integración vertical en SiC (del sustrato al módulo) y LTSAs plurianuales con OEMs; el pivote a potencia de data center amortigua el bache del EV. Riesgo: la sobrecapacidad china ha hundido precios SiC ~30% y la automoción tarda en recuperar.","loc":"EE.UU.","country":"EEUU","growth":"🟡 +4%: data center compensa el bache auto","margin":0.2,"capex_2026":"Recortado a ~$600M; giro fab-lite","backlog_status":"LTSAs renegociados; diseños DC en construcción","role_en":"SiC and intelligent-power specialist for AI data centers, EVs and industrial markets","supplies_en":"EliteSiC MOSFETs and modules for AI data-center power distribution and EV traction; image sensors for ADAS; industrial power management.","moat_en":"Vertically integrated in SiC (substrate to module) with multi-year OEM LTSAs; the pivot to data-center power cushions the EV slump. Risk: Chinese overcapacity has cut SiC prices ~30% and autos are slow to recover.","growth_en":"🟡 +4%: data center offsets the auto slump","capex_2026_en":"Cut to ~$600M; fab-lite shift","backlog_status_en":"LTSAs reworked; DC design wins building","mkt":"ON"},
  {"id":"Nvidia","label":"Nvidia","ticker":"NVDA · Nasdaq","cat":"fabless","port":"C1+C2","role":"Líder absoluto en GPUs y aceleradores de IA; el nodo más valioso de toda la cadena.","supplies":"GPUs Blackwell y la plataforma Vera Rubin en rampa, más networking NVLink/Spectrum-X, para hyperscalers, CoreWeave, labs de IA y gobiernos. Su plataforma de software CUDA amarra a todo el ecosistema.","moat":"Monopolio de facto: CUDA, un foso de software de 20 años, es imposible de reemplazar a corto plazo. Backlog ~$500B hasta 2027; inversiones tácticas ($5B en Intel, participación en CoreWeave) blindan su cadena de suministro y su demanda.","loc":"EE.UU.","growth":"⚡ +50–70% revenue FY2026","margin":0.62,"capex_2026":"~$4–5B — fabless ligero","backlog_status":"Backlog ~$500B hasta 2027","big":true,"country":"EEUU","mkt":"NVDA","role_en":"Undisputed leader in GPUs and AI accelerators; the most valuable node in the entire chain.","supplies_en":"Blackwell GPUs and the ramping Vera Rubin platform, plus NVLink/Spectrum-X networking, for hyperscalers, CoreWeave, AI labs and governments. Its CUDA software platform locks in the entire ecosystem.","moat_en":"De facto monopoly: CUDA, a 20-year software moat, is impossible to replace in the short term. Backlog of ~$500B through 2027; tactical investments ($5B in Intel, a stake in CoreWeave) shore up both its supply chain and its demand.","growth_en":"⚡ +50–70% revenue FY2026","capex_2026_en":"~$4–5B — asset-light fabless","backlog_status_en":"Backlog ~$500B through 2027"},
  {"id":"AMD","label":"AMD","ticker":"AMD · Nasdaq","cat":"fabless","port":"C1+C2","role":"El único rival serio de Nvidia en GPUs de IA y de Intel en x86.","supplies":"CPUs EPYC/Ryzen, GPUs Instinct y FPGAs (Xilinx). Cerró con OpenAI un acuerdo de 6 GW de GPUs Instinct con warrants sobre ~10% de su capital — el primer gigavatio (MI450) se despliega en H2 2026; también suministra a CoreWeave y Oracle.","moat":"Segundo en GPU de IA con la única alternativa de rack completo a Nvidia (Helios), aunque su stack ROCm aún persigue a CUDA. El acuerdo con OpenAI valida la hoja de ruta MI400 y asegura demanda plurianual.","loc":"EE.UU.","growth":"🔵 +25–35% 2026","margin":0.22,"capex_2026":"n/s — fabless ligero (~$1B)","backlog_status":"6 GW OpenAI (1er GW en H2 2026); MI400 plurianual","country":"EEUU","mkt":"AMD","role_en":"Nvidia's only serious rival in AI GPUs, and Intel's in x86.","supplies_en":"EPYC/Ryzen CPUs, Instinct GPUs and FPGAs (Xilinx). Signed a 6 GW Instinct GPU deal with OpenAI including warrants over ~10% of its equity — the first gigawatt (MI450) deploys in H2 2026; also supplies CoreWeave and Oracle.","moat_en":"Number two in AI GPUs with the only full-rack alternative to Nvidia (Helios), though its ROCm stack still trails CUDA. The OpenAI deal validates the MI400 roadmap and secures multi-year demand.","growth_en":"🔵 +25–35% 2026","capex_2026_en":"n/a — asset-light fabless (~$1B)","backlog_status_en":"6 GW OpenAI (1st GW in H2 2026); multi-year MI400"},
  {"id":"Qualcomm","label":"Qualcomm","ticker":"QCOM · Nasdaq","cat":"fabless","port":"","role":"Líder global en SoCs para smartphones premium, ahora entrando al data center de IA.","supplies":"SoCs Snapdragon y módems 5G para Android premium, automotive (Digital Chassis) y PCs; desde 2025 vende aceleradores de inferencia AI200/AI250 para data centers, con Humain (Arabia Saudita) como cliente ancla.","moat":"Dominio en módems y SoCs Android premium, con licencias QTL de alto margen; riesgo de internalización por parte de Apple. En aceleradores parte desde cero contra Nvidia y AMD, apalancando su NPU Hexagon de bajo consumo.","loc":"EE.UU.","growth":"🟢 +10–15% 2026","margin":0.29,"capex_2026":"~$1.5B — fabless","backlog_status":"AI200 en rampa 2026: ancla Humain (Arabia Saudita)","country":"EEUU","mkt":"QCOM","role_en":"Global leader in premium smartphone SoCs, now entering the AI data center.","supplies_en":"Snapdragon SoCs and 5G modems for premium Android, automotive (Digital Chassis) and PCs; since 2025 it sells AI200/AI250 inference accelerators for data centers, with Humain (Saudi Arabia) as anchor customer.","moat_en":"Dominance in modems and premium Android SoCs, with high-margin QTL licensing; risk of in-sourcing by Apple. In accelerators it starts from scratch against Nvidia and AMD, leveraging its low-power Hexagon NPU.","growth_en":"🟢 +10–15% 2026","capex_2026_en":"~$1.5B — fabless","backlog_status_en":"AI200 ramping in 2026: Humain (Saudi Arabia) as anchor"},
  {"id":"Apple","label":"Apple","ticker":"AAPL · Nasdaq","cat":"fabless","port":"","role":"Diseñador de los chips serie A/M de sus dispositivos; mayor cliente de TSMC en nodos punteros.","supplies":"Chips serie A (iPhone), M (Mac/iPad) y C (módem propio), diseñados internamente y fabricados en exclusiva por TSMC en los nodos más avanzados; reserva la primera capacidad de N2.","moat":"Sus chips marcan los benchmarks de eficiencia por vatio y anclan un ecosistema de 2,300M+ de dispositivos activos. Como cliente ancla de cada nodo de TSMC, asegura la capacidad puntera antes que nadie.","loc":"EE.UU.","growth":"🟢 +10–13% 2026","margin":0.32,"capex_2026":"~$13–15B","backlog_status":"Capacidad N2 de TSMC reservada como cliente ancla","country":"EEUU","mkt":"AAPL","role_en":"Designer of the A/M-series chips in its devices; TSMC's largest customer at leading-edge nodes.","supplies_en":"A-series (iPhone), M-series (Mac/iPad) and C-series (in-house modem) chips, designed internally and manufactured exclusively by TSMC at the most advanced nodes; it reserves the first N2 capacity.","moat_en":"Its chips set the efficiency-per-watt benchmarks and anchor an ecosystem of 2,300M+ active devices. As anchor customer for every TSMC node, it secures leading-edge capacity ahead of everyone else.","growth_en":"🟢 +10–13% 2026","capex_2026_en":"~$13–15B","backlog_status_en":"TSMC N2 capacity reserved as anchor customer"},
  {"id":"Cambricon","label":"Cambricon","ticker":"688256 · STAR","cat":"fabless","port":"","role":"La 'Nvidia china': aceleradores Siyuan para el mercado de IA vetado a los chips americanos","supplies":"Aceleradores de IA Siyuan 590/690 y stack de software Neuware para nubes y operadores chinos (ByteDance, telecos estatales); fabricados en SMIC.","moat":"Beneficiario directo del veto a Nvidia: las nubes chinas deben comprar local y Siyuan es la alternativa cotizada; software Neuware estilo CUDA madurando. Riesgo: la capacidad de SMIC sin EUV limita volúmenes, Huawei Ascend compite y cotiza a >60x ventas.","loc":"China","country":"China","growth":"⚡ +150% con Nvidia vetada en China","margin":0.25,"capex_2026":"Bajo: fabless; prepagos de oblea a SMIC","backlog_status":"Sobredemanda; la oblea de SMIC es el cuello","role_en":"The 'Chinese Nvidia': Siyuan accelerators for the AI market barred from US chips","supplies_en":"Siyuan 590/690 AI accelerators and the Neuware software stack for Chinese clouds and carriers (ByteDance, state telecoms); manufactured at SMIC.","moat_en":"Direct beneficiary of the Nvidia ban: Chinese clouds must buy local and Siyuan is the listed alternative; CUDA-style Neuware software maturing. Risk: EUV-less SMIC capacity caps volumes, Huawei's Ascend competes, and the stock trades above 60x sales.","growth_en":"⚡ +150% with Nvidia barred from China","capex_2026_en":"Low: fabless; wafer prepayments to SMIC","backlog_status_en":"Oversubscribed; SMIC wafers are the bottleneck"},
  {"id":"HiSilicon","label":"HiSilicon (Huawei)","ticker":"vía Huawei (no cotiza)","cat":"fabless","port":"","role":"Filial de diseño de chips de Huawei; el Ascend 910C es la alternativa china a Nvidia, fabricado en SMIC","supplies":"Aceleradores Ascend 910C/920 y stack CANN/MindSpore para los clusters CloudMatrix de Huawei; SoCs Kirin para smartphones. Fabricación en SMIC N+2 (7nm sin EUV).","moat":"Integración vertical Huawei del chip al rack y a la nube (CloudMatrix 384) con prioridad en compras estatales; el 910C compensa con escala lo que cede en nodo. Riesgo: yields de SMIC 7nm sin EUV y sin acceso a la HBM coreana de última generación.","loc":"China","country":"China","growth":"⭐ No cotiza · envíos Ascend duplicándose al año","margin":0.15,"capex_2026":"Vía Huawei: líneas cautivas y SMIC","backlog_status":"La demanda estatal supera la capacidad de SMIC","role_en":"Huawei's chip-design arm; the Ascend 910C is China's Nvidia alternative, built at SMIC","supplies_en":"Ascend 910C/920 accelerators and the CANN/MindSpore stack for Huawei's CloudMatrix clusters; Kirin smartphone SoCs. Manufactured at SMIC N+2 (EUV-less 7nm).","moat_en":"Huawei's vertical integration from chip to rack to cloud (CloudMatrix 384) with priority in state procurement; the 910C offsets its node deficit with sheer scale. Risk: SMIC 7nm yields without EUV and no access to leading-edge Korean HBM.","growth_en":"⭐ Unlisted · Ascend shipments doubling yearly","capex_2026_en":"Via Huawei: captive lines plus SMIC","backlog_status_en":"State demand outstrips SMIC capacity","preipo":true},
  {"id":"SKHynix","label":"SK Hynix","ticker":"000660 · KRX","cat":"memory","port":"C1+C2","role":"Proveedor #1 mundial de memoria HBM, socio crítico de Nvidia.","supplies":"Memoria HBM3e que se apila sobre cada GPU de IA — sin SK Hynix no existirían los H100/B200. HBM4 en calificación para la plataforma Vera Rubin de Nvidia; también DRAM DDR5 para servidores de Dell y los racks de CoreWeave.","moat":"~64% de cuota global en HBM con 12–18 meses de ventaja tecnológica sobre Samsung. Único proveedor calificado de HBM3e para Nvidia hoy; toda su capacidad HBM de 2026 está vendida por adelantado con precios pactados.","loc":"Corea del Sur","growth":"⚡ +80–100% revenue 2026","margin":0.52,"capex_2026":"~$22B (M15X y capacidad HBM)","backlog_status":"HBM agotada todo 2026; HBM4 en calificación para Vera Rubin","country":"Corea","mkt":"HXSCL","role_en":"World's #1 supplier of HBM memory and a critical Nvidia partner.","supplies_en":"HBM3e memory stacked on every AI GPU — without SK Hynix the H100/B200 would not exist. HBM4 in qualification for Nvidia's Vera Rubin platform; also DDR5 DRAM for Dell servers and CoreWeave racks.","moat_en":"~64% global HBM share with a 12–18 month technology lead over Samsung. The only qualified HBM3e supplier to Nvidia today; its entire 2026 HBM capacity is pre-sold at agreed prices.","growth_en":"⚡ +80–100% revenue 2026","capex_2026_en":"~$22B (M15X and HBM capacity)","backlog_status_en":"HBM sold out for all of 2026; HBM4 in qualification for Vera Rubin"},
  {"id":"Micron","label":"Micron","ticker":"MU · Nasdaq","cat":"memory","port":"C2","role":"Único gran fabricante de memoria occidental.","supplies":"DRAM DDR5, NAND 3D y memoria HBM3E/HBM4 para IA — proveedor alternativo de Nvidia y AMD, y de DDR5 para servidores Dell. El único productor de memoria a escala fuera de Asia.","moat":"Relevancia geopolítica crítica protege sus subsidios del CHIPS Act. Superciclo de DRAM hasta 2028 con precios contratados por adelantado; tercero en HBM tras SK Hynix y Samsung, ganando calificaciones en HBM4.","loc":"EE.UU.","growth":"🔵 +30–40% anual","margin":0.42,"capex_2026":"$14–16B (fabs Idaho/NY)","backlog_status":"HBM 2026 vendida íntegramente; precios pactados a 2027","country":"EEUU","mkt":"MU","role_en":"The only major Western memory manufacturer.","supplies_en":"DDR5 DRAM, 3D NAND and HBM3E/HBM4 memory for AI — alternative supplier to Nvidia and AMD, and of DDR5 for Dell servers. The only at-scale memory producer outside Asia.","moat_en":"Critical geopolitical relevance protects its CHIPS Act subsidies. DRAM supercycle through 2028 with prices contracted in advance; third in HBM behind SK Hynix and Samsung, winning HBM4 qualifications.","growth_en":"🔵 +30–40% annually","capex_2026_en":"$14–16B (Idaho/NY fabs)","backlog_status_en":"2026 HBM fully sold out; prices locked through 2027"},
  {"id":"Kioxia","label":"Kioxia","ticker":"285A · TSE","cat":"memory","port":"C2","role":"Inventores de la memoria Flash y segundo mayor fabricante de NAND.","supplies":"Memoria NAND Flash 3D de hasta 218 capas y eSSDs para data centers de IA. Opera fabs compartidas con SanDisk mediante la joint venture de Yokkaichi y Kitakami.","moat":"Inventores originales del Flash (1987). Joint venture exclusiva de fabs con SanDisk que reparte el CAPEX. +4,300% desde su IPO de dic. 2024 y miembro del Nikkei 225 desde abril 2026.","loc":"Japón","growth":"⚡ +60–80% FY2026; +4,300% desde IPO","margin":0.3,"capex_2026":"~¥600B (fab K2, Kitakami)","backlog_status":"Demanda eSSD de IA supera la oferta; K2 en rampa","country":"Japon","role_en":"Inventor of Flash memory and the second-largest NAND manufacturer.","supplies_en":"3D NAND Flash memory with up to 218 layers and eSSDs for AI data centers. Operates fabs shared with SanDisk through the Yokkaichi and Kitakami joint venture.","moat_en":"Original inventor of Flash (1987). Exclusive fab joint venture with SanDisk that splits the CAPEX. Up +4,300% since its Dec. 2024 IPO and a Nikkei 225 member since April 2026.","growth_en":"⚡ +60–80% FY2026; +4,300% since IPO","capex_2026_en":"~¥600B (K2 fab, Kitakami)","backlog_status_en":"AI eSSD demand exceeds supply; K2 ramping"},
  {"id":"SanDisk","label":"SanDisk","ticker":"SNDK · Nasdaq","cat":"memory","port":"C1","role":"Fabricante puro de NAND y SSDs enterprise, recién independiente.","supplies":"Memoria NAND Flash y SSDs de alta capacidad para data centers (cliente clave: Dell). Separada de Western Digital en feb. 2025 e IPO en mayo 2026; el segmento data center superó al móvil por primera vez en 2026.","moat":"Segunda empresa pura de NAND tras Kioxia, con escala asegurada vía la JV de fabs compartidas. Beneficiaria directa del déficit de NAND enterprise, que sostiene precios y expande su margen operativo.","loc":"EE.UU.","growth":"⚡ +80–120% revenue FY2026","margin":0.28,"capex_2026":"~$3B (vía JV con Kioxia)","backlog_status":"eSSD enterprise comprometido para todo 2026","country":"EEUU","mkt":"SNDK","role_en":"Pure-play NAND and enterprise SSD maker, newly independent.","supplies_en":"NAND Flash memory and high-capacity SSDs for data centers (key customer: Dell). Spun off from Western Digital in Feb. 2025 with an IPO in May 2026; the data center segment overtook mobile for the first time in 2026.","moat_en":"Second pure-play NAND company after Kioxia, with scale secured via the shared-fab JV. Direct beneficiary of the enterprise NAND shortage, which supports prices and expands its operating margin.","growth_en":"⚡ +80–120% revenue FY2026","capex_2026_en":"~$3B (via JV with Kioxia)","backlog_status_en":"Enterprise eSSD committed for all of 2026"},
  {"id":"YMTC","label":"YMTC","ticker":"No cotiza (estatal)","cat":"memory","port":"","role":"Campeón estatal chino de NAND; 294 capas logradas con equipos domésticos pese a las sanciones","supplies":"NAND 3D con arquitectura Xtacking (294 capas) y SSDs para smartphones, PCs y servidores chinos; cliente ancla de los equiperos domésticos Naura y AMEC.","moat":"Xtacking propio y prioridad absoluta del Estado (Big Fund III); única memoria china competitiva y ancla del equipamiento doméstico. Riesgo: lista de entidades, sin herramientas US, coste por bit superior y techo tecnológico sin litografía avanzada.","loc":"China","country":"China","growth":"⭐ Estatal · bits +30%, precios presionados","margin":0.05,"capex_2026":"Masivo y subvencionado: Fab 3 en Wuhan","backlog_status":"Demanda doméstica cautiva asegurada","role_en":"China's state NAND champion; 294 layers achieved on domestic tools despite sanctions","supplies_en":"3D NAND on its Xtacking architecture (294 layers) plus SSDs for Chinese smartphones, PCs and servers; anchor customer for domestic toolmakers Naura and AMEC.","moat_en":"Proprietary Xtacking and absolute state priority (Big Fund III); China's only competitive memory maker and anchor for domestic tools. Risk: Entity List status, no US tools, higher cost per bit and a technology ceiling without advanced lithography.","growth_en":"⭐ State-owned · bits +30%, pricing under pressure","capex_2026_en":"Massive, subsidized: Wuhan Fab 3","backlog_status_en":"Captive domestic demand assured","preipo":true},
  {"id":"Ibiden","label":"Ibiden","ticker":"4062 · TSE","cat":"substrates","port":"C2","role":"Líder en sustratos ABF de alta gama para chips de IA.","supplies":"Los sustratos ABF que conectan el silicio de Nvidia, Intel y AMD con la placa del servidor, fabricados con la película ABF de Ajinomoto — un insumo monopólico sin sustituto calificado.","moat":"Oligopolio con Unimicron en ABF de gama alta. Cuello de botella documentado de la industria — sin Ibiden no se puede armar un H100. Cada tramo de capacidad nueva queda absorbido antes de entrar en línea.","loc":"Japón","growth":"🔵 +20–28% anual","margin":0.2,"capex_2026":"~¥220B (planta Ono, fase 2)","backlog_status":"Capacidad ABF comprometida hasta 2027","country":"Japon","mkt":"IBIDF","role_en":"Leader in high-end ABF substrates for AI chips.","supplies_en":"The ABF substrates that connect Nvidia, Intel and AMD silicon to the server board, built with Ajinomoto's ABF film — a monopoly input with no qualified substitute.","moat_en":"Oligopoly with Unimicron in high-end ABF. A documented industry bottleneck — without Ibiden an H100 cannot be assembled. Every tranche of new capacity is absorbed before it comes online.","growth_en":"🔵 +20–28% annually","capex_2026_en":"~¥220B (Ono plant, phase 2)","backlog_status_en":"ABF capacity committed through 2027"},
  {"id":"Unimicron","label":"Unimicron","ticker":"3037 · TWSE","cat":"substrates","port":"","role":"Segundo mayor fabricante mundial de sustratos ABF.","supplies":"Sustratos ABF y PCBs de alta densidad para AMD, Intel y Nvidia — el complemento indispensable de Ibiden en el oligopolio del empaquetado de alto rendimiento.","moat":"Oligopolio con Ibiden. Su expansión de capacidad está financiada por contratos take-or-pay firmados por los propios clientes, que asumen el riesgo de volumen y blindan la utilización de las plantas.","loc":"Taiwán","growth":"🔵 +18–24% anual","margin":0.16,"capex_2026":"~NT$35B (expansión ABF)","backlog_status":"Take-or-pay cubre la nueva capacidad hasta 2027","country":"Taiwan","role_en":"World's second-largest manufacturer of ABF substrates.","supplies_en":"ABF substrates and high-density PCBs for AMD, Intel and Nvidia — Ibiden's indispensable counterpart in the high-performance packaging oligopoly.","moat_en":"Oligopoly with Ibiden. Its capacity expansion is funded by take-or-pay contracts signed by the customers themselves, who bear the volume risk and lock in plant utilization.","growth_en":"🔵 +18–24% annually","capex_2026_en":"~NT$35B (ABF expansion)","backlog_status_en":"Take-or-pay covers the new capacity through 2027"},
  {"id":"ASE","label":"ASE Technology","ticker":"ASX · NYSE","cat":"substrates","port":"","role":"Mayor empresa de empaquetado y testing (OSAT) del mundo.","supplies":"Empaqueta y prueba chips que otros fabrican: empaquetado avanzado y control de calidad tercerizado para Qualcomm, AMD, Broadcom y Nvidia, con capacidad que descomprime el CoWoS agotado de TSMC.","moat":"~30% de cuota del mercado OSAT global, el doble que Amkor. El boom del empaquetado avanzado de IA desplaza valor hacia el back-end, donde ASE fija los estándares técnicos y de capacidad.","loc":"Taiwán","growth":"🔵 +18–22% anual","margin":0.12,"capex_2026":"~$3B (empaquetado avanzado)","backlog_status":"Empaquetado avanzado vendido para todo 2026","country":"Taiwan","mkt":"ASX","role_en":"The world's largest packaging and testing (OSAT) company.","supplies_en":"Packages and tests chips that others manufacture: advanced packaging and outsourced quality control for Qualcomm, AMD, Broadcom and Nvidia, with capacity that relieves TSMC's sold-out CoWoS.","moat_en":"~30% share of the global OSAT market, double Amkor's. The AI advanced-packaging boom shifts value toward the back-end, where ASE sets the technical and capacity standards.","growth_en":"🔵 +18–22% annually","capex_2026_en":"~$3B (advanced packaging)","backlog_status_en":"Advanced packaging sold out for all of 2026"},
  {"id":"Advantest","label":"Advantest","ticker":"6857 · TSE","cat":"substrates","port":"C2","role":"Líder mundial en equipos de testing automatizado (ATE) de chips.","supplies":"Los testers que validan cada chip antes de enviarse: cada chip HBM de SK Hynix o Micron pasa horas conectado a un tester Advantest. También prueba SoCs, GPUs y aceleradores de IA de Nvidia y los hyperscalers.","moat":"Líder global en testing de HBM y chips de IA, con más de la mitad del mercado de ATE para SoC. HBM4 multiplica las horas de test por chip — su revenue creció 43% interanual.","loc":"Japón","growth":"🔵 +20–25% anual","margin":0.32,"capex_2026":"~¥60B — modelo ligero en capital","backlog_status":"Libro de órdenes >12 meses; testers HBM4 agotados","country":"Japon","mkt":"ATEYY","role_en":"World leader in automated test equipment (ATE) for chips.","supplies_en":"The testers that validate every chip before shipment: each SK Hynix or Micron HBM chip spends hours hooked up to an Advantest tester. Also tests SoCs, GPUs and AI accelerators for Nvidia and the hyperscalers.","moat_en":"Global leader in HBM and AI chip testing, with more than half of the SoC ATE market. HBM4 multiplies test hours per chip — its revenue grew 43% year over year.","growth_en":"🔵 +20–25% annually","capex_2026_en":"~¥60B — capital-light model","backlog_status_en":"Order book >12 months; HBM4 testers sold out"},
  {"id":"Amkor","label":"Amkor","ticker":"AMKR · Nasdaq","cat":"substrates","port":"","role":"Segundo OSAT mundial y única alternativa de empaquetado avanzado en EE.UU.","supplies":"Empaquetado avanzado y testing para Qualcomm, AMD y Apple. Su planta de Peoria, Arizona (financiada por el CHIPS Act) empaqueta los chips fabricados en TSMC Arizona, cerrando la cadena completa en suelo estadounidense.","moat":"#2 OSAT global y socio designado del ecosistema TSMC Arizona/Apple; relevante para el DoD. Su foso es geográfico: nadie más ofrece empaquetado avanzado a escala dentro de EE.UU.","loc":"EE.UU.","growth":"🟢 +14–18% anual","margin":0.1,"capex_2026":"~$1.6B (Peoria, Arizona)","backlog_status":"Arizona reservada para TSMC AZ/Apple desde el arranque","country":"EEUU","mkt":"AMKR","role_en":"World's #2 OSAT and the only advanced-packaging alternative in the US.","supplies_en":"Advanced packaging and testing for Qualcomm, AMD and Apple. Its Peoria, Arizona plant (funded by the CHIPS Act) packages the chips made at TSMC Arizona, closing the full chain on US soil.","moat_en":"Global #2 OSAT and designated partner of the TSMC Arizona/Apple ecosystem; relevant to the DoD. Its moat is geographic: no one else offers advanced packaging at scale inside the US.","growth_en":"🟢 +14–18% annually","capex_2026_en":"~$1.6B (Peoria, Arizona)","backlog_status_en":"Arizona reserved for TSMC AZ/Apple from day one"},
  {"id":"Teradyne","label":"Teradyne","ticker":"TER · Nasdaq","cat":"substrates","port":"","role":"Mitad del duopolio mundial de test de chips (ATE) con Advantest; además robótica colaborativa (UR)","supplies":"Testers UltraFLEX+ para SoCs y aceleradores de IA, testers de memoria Magnum para HBM; robots colaborativos Universal Robots y móviles MiR.","moat":"Duopolio ATE con Advantest (~40% de cuota); los aceleradores de >200.000M de transistores disparan los minutos de test por chip; Universal Robots lidera cobots. Riesgo: Advantest domina el test de HBM y la robótica sigue cíclica.","loc":"EE.UU.","country":"EEUU","growth":"🔵 +20% por test de aceleradores IA","margin":0.26,"capex_2026":"~$200M; modelo fab-lite ligero","backlog_status":"Creciente: ASICs de IA y test de HBM","role_en":"Half of the global chip-test (ATE) duopoly with Advantest; also collaborative robotics (UR)","supplies_en":"UltraFLEX+ testers for SoCs and AI accelerators, Magnum memory testers for HBM; Universal Robots cobots and MiR mobile robots.","moat_en":"ATE duopoly with Advantest (~40% share); accelerators with 200B+ transistors balloon test minutes per chip; Universal Robots leads cobots. Risk: Advantest owns HBM test and robotics remains cyclical.","growth_en":"🔵 +20% on AI accelerator test demand","capex_2026_en":"~$200M; asset-light fab-lite model","backlog_status_en":"Building: AI ASIC and HBM test orders","mkt":"TER"},
  {"id":"Besi","label":"BE Semiconductor","ticker":"BESI · Euronext","cat":"substrates","port":"","role":"Líder en hybrid bonding, el empaquetado avanzado que une HBM4 y chiplets cobre contra cobre","supplies":"Máquinas de die-attach y hybrid bonding con precisión <100nm para TSMC, Intel, Samsung y OSATs; solución integrada con Applied Materials para el empaquetado cobre-cobre de HBM4 y chiplets.","moat":"~80% del naciente mercado de hybrid bonding y co-desarrollo con Applied Materials y TSMC; HBM4 y los chiplets de Vera Rubin lo convierten en estándar de volumen. Riesgo: valoración exigente y ASMPT/Hanmi atacando el segundo escalón.","loc":"Países Bajos","country":"PaisesBajos","growth":"⚡ +55%: el hybrid bonding entra en volumen","margin":0.36,"capex_2026":"Ligero: ensamblaje en Malasia/Singapur","backlog_status":"Pedidos récord de TSMC, OSATs y memoria","role_en":"Hybrid-bonding leader: the advanced packaging that joins HBM4 and chiplets copper-to-copper","supplies_en":"Die-attach and hybrid-bonding machines with sub-100nm accuracy for TSMC, Intel, Samsung and OSATs; integrated solution with Applied Materials for copper-to-copper HBM4 and chiplet packaging.","moat_en":"~80% of the nascent hybrid-bonding market, co-developed with Applied Materials and TSMC; HBM4 and Vera Rubin chiplets make it a volume standard. Risk: demanding valuation, with ASMPT/Hanmi attacking the second tier.","growth_en":"⚡ +55% as hybrid bonding hits volume","capex_2026_en":"Light: assembly in Malaysia/Singapore","backlog_status_en":"Record orders from TSMC, OSATs and memory","mkt":"BESIY"},
  {"id":"Arista","label":"Arista Networks","ticker":"ANET · NYSE","cat":"networking","port":"C1","role":"Líder en switches Ethernet 400G/800G para data centers de IA.","supplies":"Switches Ethernet 400G/800G que conectan decenas de miles de GPUs. Microsoft y Meta son sus mayores clientes; su Ethernet abierto gana terreno frente al InfiniBand propietario de Nvidia.","moat":"Fundador del AI Ethernet Consortium y dueño del software EOS, muy difícil de reemplazar en clientes establecidos. Riesgo: los switches whitebox con Tomahawk de Broadcom presionan precios en hyperscalers.","loc":"EE.UU.","growth":"🔵 +20–25% 2026","margin":0.45,"capex_2026":"n/s — fabless/asset-light","backlog_status":"Visibilidad de pedidos IA hasta 2027 (Microsoft y Meta)","country":"EEUU","mkt":"ANET","role_en":"Leader in 400G/800G Ethernet switches for AI data centers.","supplies_en":"400G/800G Ethernet switches that connect tens of thousands of GPUs. Microsoft and Meta are its largest customers; its open Ethernet is gaining ground against Nvidia's proprietary InfiniBand.","moat_en":"Founder of the AI Ethernet Consortium and owner of the EOS software, very hard to displace at established customers. Risk: whitebox switches running Broadcom's Tomahawk pressure pricing at hyperscalers.","growth_en":"🔵 +20–25% 2026","capex_2026_en":"n/a — fabless/asset-light","backlog_status_en":"AI order visibility through 2027 (Microsoft and Meta)"},
  {"id":"Cisco","label":"Cisco","ticker":"CSCO · Nasdaq","cat":"networking","port":"","role":"Gigante maduro del networking reactivado por la IA con su ASIC Silicon One.","supplies":"Switches y routers con Silicon One, su ASIC propio fabricado en TSMC, para el back-end de clusters de IA. Ganó el networking del proyecto Stargate de OpenAI/Oracle y vende sistemas 800G a hyperscalers, gobiernos y empresas.","moat":"Base instalada empresarial inigualable y stack completo: silicio, óptica, software y seguridad. Silicon One le devolvió relevancia en hyperscalers, pero Arista y los whitebox crecen más rápido que él.","loc":"EE.UU.","growth":"🟡 +5–7% 2026; órdenes de IA aceleran","margin":0.32,"capex_2026":"~$1B — fabless vía TSMC","backlog_status":"Órdenes de infraestructura IA >$3B; Stargate en despliegue","country":"EEUU","mkt":"CSCO","role_en":"Mature networking giant reenergized by AI with its Silicon One ASIC.","supplies_en":"Switches and routers built on Silicon One, its in-house ASIC made at TSMC, for the back-end of AI clusters. Won the networking for OpenAI/Oracle's Stargate project and sells 800G systems to hyperscalers, governments and enterprises.","moat_en":"Unmatched enterprise installed base and a full stack: silicon, optics, software and security. Silicon One restored its relevance at hyperscalers, but Arista and the whiteboxes are growing faster.","growth_en":"🟡 +5–7% 2026; AI orders accelerating","capex_2026_en":"~$1B — fabless via TSMC","backlog_status_en":"AI infrastructure orders >$3B; Stargate deploying"},
  {"id":"Broadcom","label":"Broadcom","ticker":"AVGO · Nasdaq","cat":"networking","port":"C2","role":"El motor oculto del silicio propio de los hyperscalers y rey del switching.","supplies":"Diseña el TPU de Google, el MTIA de Meta y el ASIC custom de 10 GW de OpenAI. Suministra los switches Tomahawk/Jericho que arman las redes de IA, y VMware añade ingresos recurrentes de software.","moat":"Duopolio con Marvell en ASICs personalizados — sin Broadcom no existe el silicio propio de las grandes tecnológicas. Tomahawk domina el switching mercante y VMware aporta márgenes de software.","loc":"EE.UU.","growth":"🔵 +25–30% 2026 (semis de IA +60%)","margin":0.6,"capex_2026":"~$1.5B — fabless","backlog_status":"Backlog IA >$100B; ASIC OpenAI 10 GW hasta 2029","big":true,"country":"EEUU","mkt":"AVGO","role_en":"The hidden engine behind hyperscalers' in-house silicon and the king of switching.","supplies_en":"Designs Google's TPU, Meta's MTIA and OpenAI's 10 GW custom ASIC. Supplies the Tomahawk/Jericho switches that build out AI networks, and VMware adds recurring software revenue.","moat_en":"Duopoly with Marvell in custom ASICs — without Broadcom, big tech's in-house silicon would not exist. Tomahawk dominates merchant switching and VMware contributes software margins.","growth_en":"🔵 +25–30% 2026 (AI semis +60%)","capex_2026_en":"~$1.5B — fabless","backlog_status_en":"AI backlog >$100B; 10 GW OpenAI ASIC through 2029"},
  {"id":"Marvell","label":"Marvell","ticker":"MRVL · Nasdaq","cat":"networking","port":"C2","role":"Diseñador de ASICs custom, DSPs ópticos y silicio fotónico para IA.","supplies":"ASICs personalizados (Trainium de AWS, Maia de Microsoft), DSPs ópticos que gobiernan los transceptores 800G/1.6T y silicio fotónico para conectar racks con fibra óptica.","moat":"Duopolio con Broadcom en ASICs custom y liderazgo creciente en silicio fotónico, la próxima frontera del interconnect. Riesgo: los hyperscalers pueden internalizar diseños, como ocurrió con parte de Trainium.","loc":"EE.UU.","growth":"🔵 +25–30% 2026","margin":0.33,"capex_2026":"n/s — fabless (~$0.4B)","backlog_status":"Programas ASIC plurianuales: Trainium y Maia hasta 2027+","country":"EEUU","mkt":"MRVL","role_en":"Designer of custom ASICs, optical DSPs and photonic silicon for AI.","supplies_en":"Custom ASICs (AWS's Trainium, Microsoft's Maia), optical DSPs that drive 800G/1.6T transceivers, and photonic silicon to connect racks over optical fiber.","moat_en":"Duopoly with Broadcom in custom ASICs and growing leadership in photonic silicon, the next frontier of interconnect. Risk: hyperscalers can bring designs in-house, as happened with part of Trainium.","growth_en":"🔵 +25–30% 2026","capex_2026_en":"n/a — fabless (~$0.4B)","backlog_status_en":"Multi-year ASIC programs: Trainium and Maia through 2027+"},
  {"id":"Credo","label":"Credo Technology","ticker":"CRDO · Nasdaq","cat":"networking","port":"C1","role":"Fabricante de la conectividad invisible del data center: los cables activos AEC.","supplies":"Cables eléctricos activos (AECs) y chips SerDes en TSMC 3nm que conectan GPUs y switches dentro del rack. Amazon y Microsoft están entre sus mayores clientes; revenue +200% año contra año.","moat":"Líder indiscutido en AECs, que desplazan a la óptica de corto alcance por costo y fiabilidad. Riesgo: concentración extrema en clientes hyperscaler y valuación exigente tras 6x de crecimiento en 2 años.","loc":"EE.UU.","growth":"⚡ >100% FY2026; +40–50% FY2027e","margin":0.36,"capex_2026":"n/s — fabless ligero","backlog_status":"Pedidos de AECs cubiertos 12+ meses (Amazon, Microsoft)","country":"EEUU","mkt":"CRDO","role_en":"Maker of the data center's invisible connectivity: active AEC cables.","supplies_en":"Active electrical cables (AECs) and SerDes chips on TSMC 3nm that connect GPUs and switches within the rack. Amazon and Microsoft are among its largest customers; revenue +200% year over year.","moat_en":"Undisputed leader in AECs, which are displacing short-reach optics on cost and reliability. Risk: extreme concentration in hyperscaler customers and a demanding valuation after 6x growth in 2 years.","growth_en":"⚡ >100% FY2026; +40–50% FY2027e","capex_2026_en":"n/a — asset-light fabless","backlog_status_en":"AEC orders covered 12+ months out (Amazon, Microsoft)"},
  {"id":"Astera","label":"Astera Labs","ticker":"ALAB · Nasdaq","cat":"networking","port":"C1","role":"Diseñador de retimers y switching PCIe 6 para racks de IA.","supplies":"Retimers Aries y switches Scorpio PCIe 6 que coordinan la comunicación GPU–CPU–memoria dentro del rack. Partner de NVLink Fusion de Nvidia; presente en plataformas de AWS, Microsoft y los racks Vera Rubin.","moat":"Líder en switching PCIe para IA con su software COSMOS como ancla en hyperscalers. La alianza NVLink Fusion lo mete en los racks de Nvidia. Riesgo: valuación elevada y Broadcom entrando en PCIe 6.","loc":"EE.UU.","growth":"⚡ +80–90% 2026","margin":0.33,"capex_2026":"n/s — fabless ligero","backlog_status":"Scorpio en rampa; diseños NVLink Fusion para 2026–27","country":"EEUU","mkt":"ALAB","role_en":"Designer of retimers and PCIe 6 switching for AI racks.","supplies_en":"Aries retimers and Scorpio PCIe 6 switches that coordinate GPU–CPU–memory communication within the rack. Nvidia NVLink Fusion partner; present in AWS and Microsoft platforms and in Vera Rubin racks.","moat_en":"Leader in PCIe switching for AI with its COSMOS software as the anchor at hyperscalers. The NVLink Fusion alliance puts it inside Nvidia's racks. Risk: elevated valuation and Broadcom entering PCIe 6.","growth_en":"⚡ +80–90% 2026","capex_2026_en":"n/a — asset-light fabless","backlog_status_en":"Scorpio ramping; NVLink Fusion designs for 2026–27"},
  {"id":"Coherent","label":"Coherent","ticker":"COHR · NYSE","cat":"networking","port":"C2","role":"Proveedor de transceptores ópticos 800G/1.6T para interconexión de IA.","supplies":"Transceptores ópticos 800G/1.6T que conectan racks entre sí con luz, con láseres propios de fosfuro de indio. Co-packaged optics en desarrollo con Nvidia; cada rack de IA necesita docenas de módulos.","moat":"Integración vertical en InP (fabrica sus propios láseres) que pocos rivales igualan; la demanda de 1.6T escala con cada generación de GPU. Riesgo: competencia china (Innolight) en módulos terminados.","loc":"EE.UU.","growth":"🔵 +20–25% 2026","margin":0.18,"capex_2026":"~$0.7B (capacidad InP)","backlog_status":"Capacidad 800G/1.6T comprometida hasta 2027","country":"EEUU","mkt":"COHR","role_en":"Supplier of 800G/1.6T optical transceivers for AI interconnect.","supplies_en":"800G/1.6T optical transceivers that link racks together with light, using its own indium phosphide lasers. Co-packaged optics in development with Nvidia; every AI rack needs dozens of modules.","moat_en":"Vertical integration in InP (it makes its own lasers) that few rivals can match; 1.6T demand scales with every GPU generation. Risk: Chinese competition (Innolight) in finished modules.","growth_en":"🔵 +20–25% 2026","capex_2026_en":"~$0.7B (InP capacity)","backlog_status_en":"800G/1.6T capacity committed through 2027"},
  {"id":"Ciena","label":"Ciena","ticker":"CIEN · NYSE","cat":"networking","port":"","role":"Óptica coherente DWDM de larga distancia; líder en interconexión entre data centers (DCI) para hyperscalers","supplies":"Módems coherentes WaveLogic 6 (1,6 Tb/s), sistemas de línea Waveserver y pluggables 800ZR+ para enlaces DCI metro, terrestres y submarinos. Cloud/IA ya supera el 40% de los pedidos.","moat":"~40% de cuota en DCI y la única óptica coherente verticalmente integrada de Occidente; WaveLogic 6 lidera en alcance por vatio. Riesgo: los pluggables ZR comoditizan el enlace y Cisco/Nokia presionan precios.","loc":"EE.UU.","country":"EEUU","growth":"🔵 Ingresos +17% FY2026; pedidos cloud récord","margin":0.12,"capex_2026":"~$130M; modelo asset-light","backlog_status":"Backlog ~$2,8B; book-to-bill cloud >1,2","role_en":"Long-haul coherent DWDM optics; leader in data center interconnect (DCI) for hyperscalers","supplies_en":"WaveLogic 6 coherent modems (1.6 Tb/s), Waveserver line systems and 800ZR+ pluggables for metro, terrestrial and subsea DCI links. Cloud/AI now exceeds 40% of orders.","moat_en":"~40% DCI share and the West's only vertically integrated coherent optics house; WaveLogic 6 leads in reach per watt. Risk: ZR pluggables commoditize the link while Cisco/Nokia pressure pricing.","growth_en":"🔵 Revenue +17% FY2026; record cloud orders","capex_2026_en":"~$130M; asset-light model","backlog_status_en":"Backlog ~$2.8B; cloud book-to-bill >1.2","mkt":"CIEN"},
  {"id":"Lumentum","label":"Lumentum","ticker":"LITE · Nasdaq","cat":"networking","port":"","role":"Láseres EML/CW y transceptores datacom; apuesta por co-packaged optics frente a Coherent","supplies":"Láseres EML 200G/carril y láseres CW para fotónica de silicio, transceptores 800G/1.6T y switches ópticos de circuito (OCS); suministra a Nvidia, Google y a fabricantes de módulos como Innolight.","moat":"Uno de los tres fabricantes de EML del mundo (con Coherent y Mitsubishi); su capacidad de InP está vendida con años de antelación. Riesgo: la transición a CPO puede saltarse el transceptor tradicional y reordenar la cadena.","loc":"EE.UU.","country":"EEUU","growth":"⚡ Ingresos +55% FY2026 por datacom IA","margin":0.14,"capex_2026":"~$350M; ampliación fab de InP","backlog_status":"EMLs agotados hasta 2027; asignación racionada","role_en":"EML/CW lasers and datacom transceivers; betting on co-packaged optics against rival Coherent","supplies_en":"200G/lane EML lasers and CW lasers for silicon photonics, 800G/1.6T transceivers and optical circuit switches (OCS); supplies Nvidia, Google and module makers including Innolight.","moat_en":"One of only three EML makers worldwide (with Coherent and Mitsubishi); its InP capacity is sold out years ahead. Risk: the CPO transition can bypass the traditional transceiver and reshuffle the supply chain.","growth_en":"⚡ Revenue +55% FY2026 on AI datacom","capex_2026_en":"~$350M; InP fab expansion","backlog_status_en":"EMLs sold out into 2027; allocation rationed","mkt":"LITE"},
  {"id":"Innolight","label":"Innolight","ticker":"300308 · SZSE","cat":"networking","port":"","role":"#1 mundial en transceptores ópticos 800G/1.6T; proveedor crítico de Nvidia y hyperscalers","supplies":"Transceptores 800G en volumen y 1.6T en plena rampa para las redes Vera Rubin; módulos LPO/LRO y desarrollo CPO. Clientes: Nvidia, Google, Meta y Amazon.","moat":"~30% de cuota mundial en datacom de alta velocidad y escala fabril inigualada (Tailandia/China). Riesgos: aranceles EE.UU.-China, el CPO de Nvidia/Broadcom internaliza la óptica y depende de EMLs de terceros.","loc":"China","country":"China","growth":"⚡ Ingresos +60% 2026; rampa 1.6T","margin":0.25,"capex_2026":"~$700M; capacidad en Tailandia","backlog_status":"Capacidad 1.6T comprometida para todo 2026","role_en":"World #1 in 800G/1.6T optical transceivers; critical supplier to Nvidia and hyperscalers","supplies_en":"800G transceivers at volume and 1.6T in full ramp for Vera Rubin networks; LPO/LRO modules and CPO development. Customers: Nvidia, Google, Meta and Amazon.","moat_en":"~30% global share in high-speed datacom and unmatched manufacturing scale (Thailand/China). Risks: US-China tariffs, Nvidia/Broadcom CPO internalizing the optics, and reliance on third-party EMLs.","growth_en":"⚡ Revenue +60% 2026; 1.6T ramp","capex_2026_en":"~$700M; Thailand capacity","backlog_status_en":"1.6T capacity fully committed through 2026"},
  {"id":"Amphenol","label":"Amphenol","ticker":"APH · NYSE","cat":"networking","port":"","role":"Conectores, cables y backplanes de alta velocidad presentes en cada rack de IA","supplies":"Interconexión 224G/carril, backplanes, cable assemblies y conectores de potencia para racks GB300 de Nvidia y diseños propios de hyperscalers; además defensa, automoción e industrial.","moat":"Décadas de co-diseño con Nvidia/hyperscalers y M&A disciplinado; el contenido por rack crece con cada generación de GPU. La diversificación amortigua ciclos. Riesgo: concentración creciente en IT datacom (~40% de ventas).","loc":"EE.UU.","country":"EEUU","growth":"🔵 Ingresos +28% 2026; IT datacom +80%","margin":0.24,"capex_2026":"~$1,2B (4% ventas); capacidad IA","backlog_status":"Book-to-bill >1,1; pedidos datacom récord","role_en":"High-speed connectors, cables and backplanes inside every AI rack","supplies_en":"224G/lane interconnects, backplanes, cable assemblies and power connectors for Nvidia GB300 racks and hyperscaler custom designs; plus defense, auto and industrial.","moat_en":"Decades of co-design with Nvidia/hyperscalers and disciplined M&A; content per rack rises with every GPU generation. Diversification cushions cycles. Risk: growing concentration in IT datacom (~40% of sales).","growth_en":"🔵 Revenue +28% 2026; IT datacom +80%","capex_2026_en":"~$1.2B (4% of sales); AI capacity","backlog_status_en":"Book-to-bill >1.1; record datacom orders","mkt":"APH"},
  {"id":"Vertiv","label":"Vertiv","ticker":"VRT · NYSE","cat":"power","port":"C1","role":"El \"electricista y plomero\" del data center de IA.","supplies":"Enfriamiento líquido (CDUs, cold plates), PDUs, busways y UPS para racks de GPUs de Nvidia; equipa los data centers de CoreWeave, Oracle y los hyperscalers. Sin Vertiv, los racks NVL72 se sobrecalientan.","moat":"Líder en enfriamiento líquido para racks de IA, con backlog de $15B y órdenes +252% YoY. Diseño de referencia junto a Nvidia para la arquitectura de 800 VDC de Vera Rubin; Eaton y Schneider presionan, pero su base instalada y red de servicio lo protegen.","loc":"EE.UU.","growth":"🔵 +28–32% 2026; órdenes +252% YoY","margin":0.21,"capex_2026":"~$0.4B (capacidad de cooling)","backlog_status":"Backlog $15B; órdenes +252% YoY","country":"EEUU","mkt":"VRT","role_en":"The \"electrician and plumber\" of the AI data center.","supplies_en":"Liquid cooling (CDUs, cold plates), PDUs, busways and UPS for Nvidia GPU racks; outfits the data centers of CoreWeave, Oracle and the hyperscalers. Without Vertiv, NVL72 racks overheat.","moat_en":"Leader in liquid cooling for AI racks, with a $15B backlog and orders +252% YoY. Reference design alongside Nvidia for Vera Rubin's 800 VDC architecture; Eaton and Schneider are pressing, but its installed base and service network protect it.","growth_en":"🔵 +28–32% 2026; orders +252% YoY","capex_2026_en":"~$0.4B (cooling capacity)","backlog_status_en":"Backlog $15B; orders +252% YoY"},
  {"id":"MPWR","label":"Monolithic Power","ticker":"MPWR · Nasdaq","cat":"power","port":"C2","role":"Diseñador de chips de gestión de energía para servidores de IA.","supplies":"VRMs y módulos de potencia que regulan la electricidad en las placas de GPUs de Nvidia (Blackwell y Vera Rubin) y en servidores de Dell y HPE. Sin ellos, las GPUs son ineficientes o se queman.","moat":"Líder en power management para servidores de IA: su segmento enterprise creció +97% YoY. Proceso BCD propietario sobre foundries externas; riesgos: segunda fuente (Infineon, Renesas) en futuras plataformas y valoración exigente (~60x).","loc":"EE.UU.","growth":"🔵 +25–35% anual","margin":0.28,"capex_2026":"n/s — fabless ligero","backlog_status":"Design wins en Vera Rubin; visibilidad 12+ meses","country":"EEUU","mkt":"MPWR","role_en":"Designer of power-management chips for AI servers.","supplies_en":"VRMs and power modules that regulate electricity on Nvidia GPU boards (Blackwell and Vera Rubin) and in Dell and HPE servers. Without them, GPUs run inefficiently or burn out.","moat_en":"Leader in power management for AI servers: its enterprise segment grew +97% YoY. Proprietary BCD process run on external foundries; risks: second-sourcing (Infineon, Renesas) on future platforms and a demanding valuation (~60x).","growth_en":"🔵 +25–35% per year","capex_2026_en":"n/a — asset-light fabless","backlog_status_en":"Design wins on Vera Rubin; 12+ months visibility"},
  {"id":"Eaton","label":"Eaton","ticker":"ETN · NYSE","cat":"power","port":"","role":"Proveedor de la columna vertebral eléctrica del data center de IA.","supplies":"Switchgear, transformadores, busways, UPS y distribución de media tensión que llevan los megavatios desde la red hasta el rack. Vende a hyperscalers, colocations y megaproyectos tipo Stargate; el segmento eléctrico americano es su motor.","moat":"Backlog eléctrico récord con cobertura multianual: transformadores y switchgear sufren plazos de entrega de 2–3 años en toda la industria, y su capacidad instalada en Norteamérica es difícil de replicar. Duopolio práctico con Schneider en data centers.","loc":"Irlanda / EE.UU.","growth":"🟢 +9–12% orgánico 2026 (eléctrico >15%)","margin":0.21,"capex_2026":"~$1B (capacidad eléctrica EE.UU.)","backlog_status":"Backlog eléctrico récord; cobertura >2 años","country":"EEUU","mkt":"ETN","role_en":"Supplier of the electrical backbone of the AI data center.","supplies_en":"Switchgear, transformers, busways, UPS and medium-voltage distribution carrying megawatts from the grid to the rack. Sells to hyperscalers, colocation providers and Stargate-style megaprojects; the Americas electrical segment is its engine.","moat_en":"Record electrical backlog with multi-year coverage: transformers and switchgear face 2–3 year lead times across the industry, and its installed North American capacity is hard to replicate. A practical duopoly with Schneider in data centers.","growth_en":"🟢 +9–12% organic 2026 (electrical >15%)","capex_2026_en":"~$1B (US electrical capacity)","backlog_status_en":"Record electrical backlog; >2 years of coverage"},
  {"id":"Schneider","label":"Schneider Electric","ticker":"SU · Euronext","cat":"power","port":"","role":"Líder global en infraestructura eléctrica y de cooling para data centers.","supplies":"Distribución eléctrica de media y baja tensión, UPS Galaxy, racks prefabricados y, vía Motivair (adquirida en 2025), enfriamiento líquido directo al chip. Partner de referencia de Nvidia para el diseño de data centers de IA de alta densidad.","moat":"Los data centers ya rondan el 25% de sus ventas y co-diseña con Nvidia las arquitecturas de 800 VDC para Vera Rubin. Escala global, portafolio completo (energía + cooling + software EcoStruxure) que ni Eaton ni Vertiv igualan de extremo a extremo.","loc":"Francia","growth":"🟢 +8–10% orgánico 2026 (DC >15%)","margin":0.19,"capex_2026":"€1.5–2B","backlog_status":"Libro de órdenes récord; DC ~25% de ventas","country":"Francia","mkt":"SBGSY","role_en":"Global leader in electrical and cooling infrastructure for data centers.","supplies_en":"Medium- and low-voltage power distribution, Galaxy UPS, prefabricated racks and, via Motivair (acquired in 2025), direct-to-chip liquid cooling. Nvidia's reference partner for designing high-density AI data centers.","moat_en":"Data centers already account for ~25% of sales, and it co-designs the 800 VDC architectures for Vera Rubin with Nvidia. Global scale and a complete portfolio (power + cooling + EcoStruxure software) that neither Eaton nor Vertiv matches end to end.","growth_en":"🟢 +8–10% organic 2026 (DC >15%)","capex_2026_en":"€1.5–2B","backlog_status_en":"Record order book; DC ~25% of sales"},
  {"id":"GEVernova","label":"GE Vernova","ticker":"GEV · NYSE","cat":"power","port":"","role":"Turbinas de gas y equipos de red eléctrica; ganador directo del boom eléctrico de los data centers","supplies":"Turbinas de gas HA (~20 GW/año tras la ampliación), aeroderivadas, transformadores, switchgear y servicios de red; energiza campus de Stargate y otros hyperscalers.","moat":"Slots de turbinas de gas vendidos hasta 2029 con reservas no reembolsables; duopolio efectivo con Siemens Energy/Mitsubishi en turbinas grandes. Riesgo: el offshore wind sigue quemando caja.","loc":"EE.UU.","country":"EEUU","growth":"🟢 Ingresos +12-14% 2026; margen en expansión","margin":0.09,"capex_2026":"~$1B; +capacidad turbinas 9HA","backlog_status":"Backlog récord ~$140B; gas vendido hasta 2029","role_en":"Gas turbines and grid equipment; direct winner of the data center power boom","supplies_en":"HA gas turbines (~20 GW/yr after expansion), aeroderivatives, transformers, switchgear and grid services; powering Stargate campuses and other hyperscalers.","moat_en":"Gas turbine slots sold out to 2029 with non-refundable reservation fees; effective duopoly with Siemens Energy/Mitsubishi in large turbines. Risk: offshore wind still burns cash.","growth_en":"🟢 Revenue +12-14% 2026; margin expanding","capex_2026_en":"~$1B; added 9HA turbine capacity","backlog_status_en":"Record ~$140B backlog; gas sold out to 2029","mkt":"GEV"},
  {"id":"Constellation","label":"Constellation Energy","ticker":"CEG · Nasdaq","cat":"power","port":"","role":"Mayor flota nuclear de EE.UU. (~22 GW); energía firme 24/7 libre de carbono para hyperscalers","supplies":"Electricidad vía PPAs de largo plazo: Crane (ex-Three Mile Island, 835 MW) para Microsoft, acuerdos con Meta; tras absorber Calpine es el mayor generador independiente del país.","moat":"Activos nucleares irreplicables con licencias a décadas y suelo de precio vía PTC nuclear ($43,75/MWh). PPAs de 20 años dan visibilidad única. Riesgos: regulación FERC de co-ubicación y precios del gas.","loc":"EE.UU.","country":"EEUU","growth":"🟢 BPA +10-13% anual; repricing nuclear","margin":0.2,"capex_2026":"~$3B; uprates y arranque de Crane","backlog_status":"PPAs a 20 años (Microsoft, Meta); demanda firme","role_en":"Largest US nuclear fleet (~22 GW); firm 24/7 carbon-free power for hyperscalers","supplies_en":"Power via long-term PPAs: Crane (ex-Three Mile Island, 835 MW) for Microsoft, deals with Meta; after absorbing Calpine it is the largest independent power producer in the US.","moat_en":"Irreplicable nuclear assets with decades-long licenses and a price floor via the nuclear PTC ($43.75/MWh). 20-year PPAs give unique visibility. Risks: FERC co-location rules and gas prices.","growth_en":"🟢 EPS +10-13% per year; nuclear repricing","capex_2026_en":"~$3B; uprates and Crane restart","backlog_status_en":"20-year PPAs (Microsoft, Meta); firm demand","mkt":"CEG"},
  {"id":"SiemensEnergy","label":"Siemens Energy","ticker":"ENR · Frankfurt","cat":"power","port":"","role":"Turbinas, HVDC y transformadores; el cuello de botella de la red eléctrica global","supplies":"Turbinas de gas de gran tamaño y tecnología de red (HVDC, transformadores, switchgear) con Grid Technologies creciendo >20%; aerogeneradores Siemens Gamesa en reestructuración.","moat":"Con GE Vernova e Hitachi forma el oligopolio de HVDC/transformadores, con plazos de entrega de 3-5 años y backlog récord ~€140B. Riesgo: el onshore de Siemens Gamesa sigue en pérdidas.","loc":"Alemania","country":"Alemania","growth":"🟢 Ingresos +13-14% FY2026; órdenes récord","margin":0.07,"capex_2026":"~€1,2B; capacidad de transformadores","backlog_status":"Récord ~€140B; HVDC con cola de 4 años","role_en":"Turbines, HVDC and transformers; the bottleneck of the global power grid","supplies_en":"Large gas turbines and grid technology (HVDC, transformers, switchgear) with Grid Technologies growing >20%; Siemens Gamesa wind unit under restructuring.","moat_en":"With GE Vernova and Hitachi it forms the HVDC/transformer oligopoly, with 3-5 year lead times and a record ~€140B backlog. Risk: Siemens Gamesa onshore remains loss-making.","growth_en":"🟢 Revenue +13-14% FY2026; record orders","capex_2026_en":"~€1.2B; transformer capacity","backlog_status_en":"Record ~€140B; 4-year HVDC queue","mkt":"SMNEY"},
  {"id":"DeltaElectronics","label":"Delta Electronics","ticker":"2308 · TWSE","cat":"power","port":"","role":"Fuentes de poder y módulos de potencia de los racks GB300; partner de Nvidia en 800 VDC","supplies":"Power shelves de 33-100 kW por rack, sidecars de potencia 800 VDC para Kyber/Rubin Ultra, fuentes de servidor y liquid cooling; el contenido de potencia por rack se multiplica con cada generación.","moat":"~50% de cuota en fuentes de servidor y co-diseño temprano con Nvidia en la arquitectura 800 VDC. Riesgos: competencia de Lite-On/Vertiv y exposición a la cadencia de producto de Nvidia.","loc":"Taiwán","country":"Taiwan","growth":"🔵 Ingresos +30% 2026; potencia IA se dobla","margin":0.12,"capex_2026":"~$1B; fábricas EE.UU. y Tailandia","backlog_status":"Power shelves GB300 comprometidos todo 2026","role_en":"Power supplies and power modules for GB300 racks; Nvidia's 800 VDC partner","supplies_en":"33-100 kW power shelves per rack, 800 VDC power sidecars for Kyber/Rubin Ultra, server PSUs and liquid cooling; power content per rack multiplies with each generation.","moat_en":"~50% share in server power supplies and early co-design with Nvidia on the 800 VDC architecture. Risks: Lite-On/Vertiv competition and exposure to Nvidia's product cadence.","growth_en":"🔵 Revenue +30% 2026; AI power doubling","capex_2026_en":"~$1B; US and Thailand plants","backlog_status_en":"GB300 power shelves committed through 2026"},
  {"id":"SubCom","label":"SubCom","ticker":"Privada (Cerberus)","cat":"connectivity_infra","port":"","role":"Uno de los 3 grandes instaladores de cables submarinos del mundo.","supplies":"Diseña, fabrica y tiende cables submarinos de fibra óptica con flota propia de barcos cableros. Tiende los cables transoceánicos de Google y Meta y ejecuta proyectos de defensa para el gobierno de EE.UU.","moat":"Oligopolio de 3 (con ASN y NEC) que controla ~85% del tendido global. Único actor estadounidense — favorito geopolítico para rutas alineadas con Washington. Un barco cablero nuevo tarda años en construirse.","loc":"EE.UU.","growth":"⭐ PRE-IPO (Cerberus); demanda récord","margin":null,"capex_2026":"~$0.5B (ampliación de flota)","backlog_status":"Cartera plurianual: rutas de Google y Meta hasta 2029","preipo":true,"country":"EEUU","role_en":"One of the world's big 3 subsea cable installers.","supplies_en":"Designs, manufactures and lays subsea fiber-optic cables with its own fleet of cable ships. Lays Google's and Meta's transoceanic cables and executes defense projects for the US government.","moat_en":"Oligopoly of 3 (with ASN and NEC) controlling ~85% of global cable-laying. The only US player — a geopolitical favorite for Washington-aligned routes. A new cable ship takes years to build.","growth_en":"⭐ PRE-IPO (Cerberus); record demand","capex_2026_en":"~$0.5B (fleet expansion)","backlog_status_en":"Multi-year backlog: Google and Meta routes through 2029"},
  {"id":"NEC","label":"NEC","ticker":"6701 · TSE","cat":"connectivity_infra","port":"","role":"Conglomerado japonés de TI y uno de los 3 grandes en cables submarinos.","supplies":"Sistemas de cable submarino (con fibra de su filial OCC) para rutas transpacíficas de Google, Meta y telcos asiáticas. El grupo además vende software de gobierno, biometría y redes para Japón.","moat":"Miembro del oligopolio de 3 del tendido submarino y campeón nacional japonés: las rutas del Indo-Pacífico alineadas con Tokio y Washington pasan por él. El negocio submarino es pequeño dentro del grupo.","loc":"Japón","growth":"🟡 +4–6% grupo; submarino a doble dígito","margin":0.08,"capex_2026":"~¥150B (grupo)","backlog_status":"Fábrica de cable OCC llena hasta 2028","country":"Japon","mkt":"NIPNF","role_en":"Japanese IT conglomerate and one of the Big 3 in submarine cables.","supplies_en":"Submarine cable systems (with fiber from its OCC subsidiary) for transpacific routes serving Google, Meta and Asian telcos. The group also sells government software, biometrics and networking for Japan.","moat_en":"Member of the 3-player subsea cable-laying oligopoly and Japan's national champion: Indo-Pacific routes aligned with Tokyo and Washington run through it. The submarine business is small within the group.","growth_en":"🟡 +4–6% group; subsea at double digits","capex_2026_en":"~¥150B (group)","backlog_status_en":"OCC cable plant fully booked through 2028"},
  {"id":"ASN","label":"Alcatel Submarine Networks","ticker":"Estatal Francia (80%)","cat":"connectivity_infra","port":"","role":"Mayor flota cablera del mundo, nacionalizada por Francia como activo estratégico.","supplies":"Fabrica y tiende cables submarinos de fibra: 2Africa (el cable más largo del mundo) y Amitié para Meta, más rutas para Google y telcos globales. Opera la mayor flota de barcos cableros del planeta.","moat":"El Estado francés compró el 80% a Nokia (2024) — activo soberano protegido y miembro del oligopolio de 3 con SubCom y NEC. Riesgo: la gobernanza estatal puede restar agilidad comercial frente a SubCom.","loc":"Francia","growth":"⭐ PRE-IPO — estatal (Francia 80%)","margin":null,"capex_2026":"n/d — renovación de flota","backlog_status":"Cartera récord plurianual (2Africa, Amitié, Medusa)","preipo":true,"country":"Francia","role_en":"World's largest cable-laying fleet, nationalized by France as a strategic asset.","supplies_en":"Manufactures and lays subsea fiber cables: 2Africa (the world's longest cable) and Amitié for Meta, plus routes for Google and global telcos. Operates the planet's largest fleet of cable-laying ships.","moat_en":"The French state bought 80% from Nokia (2024) — a protected sovereign asset and member of the 3-player oligopoly with SubCom and NEC. Risk: state governance may blunt commercial agility versus SubCom.","growth_en":"⭐ PRE-IPO — state-owned (France 80%)","capex_2026_en":"n/a — fleet renewal","backlog_status_en":"Record multi-year backlog (2Africa, Amitié, Medusa)"},
  {"id":"Lumen","label":"Lumen Technologies","ticker":"LUMN · NYSE","cat":"connectivity_infra","port":"","role":"Dueño de la mayor red de fibra continental de EE.UU., reconvertida en autopista de la IA.","supplies":"Fibra oscura y rutas nuevas vía acuerdos PCF (Private Connectivity Fabric) con Microsoft, AWS y Meta para interconectar sus data centers de IA entre estados. El negocio de conectividad empresarial legado sigue en declive.","moat":"Rutas y conductos intercity casi irreplicables — reconstruirlos exigiría décadas de permisos y obra civil. Riesgo: deuda alta (~$18B) en reestructuración y un negocio legado que se encoge cada trimestre.","loc":"EE.UU.","growth":"🔴 Ingresos −3–5%; PCF inflecta el mix","margin":0.1,"capex_2026":"$4.2–4.7B (rutas de fibra IA)","backlog_status":"PCF >$9B contratados (Microsoft, AWS, Meta)","country":"EEUU","mkt":"LUMN","role_en":"Owner of the largest US intercity fiber network, repurposed as an AI superhighway.","supplies_en":"Dark fiber and new routes via PCF (Private Connectivity Fabric) deals with Microsoft, AWS and Meta to interconnect their AI data centers across states. The legacy enterprise connectivity business keeps declining.","moat_en":"Nearly irreplicable intercity routes and conduits — rebuilding them would take decades of permitting and civil works. Risk: high debt (~$18B) under restructuring and a legacy business that shrinks every quarter.","growth_en":"🔴 Revenue −3–5%; PCF inflects the mix","capex_2026_en":"$4.2–4.7B (AI fiber routes)","backlog_status_en":"PCF >$9B contracted (Microsoft, AWS, Meta)"},
  {"id":"Corning","label":"Corning","ticker":"GLW · NYSE","cat":"connectivity_infra","port":"","role":"Mayor fabricante mundial de fibra óptica; la fibra física de los corredores de IA de los hyperscalers","supplies":"Fibra y cable (el segmento óptico supera el 40% de ventas), soluciones pre-conectorizadas para data centers y fibra de núcleo hueco; acuerdos plurianuales con Lumen, AT&T e hyperscalers.","moat":"Escala y un siglo de know-how en procesos de vidrio; la capacidad de fibra de EE.UU. está comprometida bajo contratos take-or-pay. Riesgo: ciclicidad en displays y exposición a consumo (Gorilla Glass).","loc":"EE.UU.","country":"EEUU","growth":"🔵 Óptica enterprise +25%; grupo +12%","margin":0.19,"capex_2026":"~$1,8B; ampliación fibra EE.UU.","backlog_status":"Fibra vendida a años vista; take-or-pay firmados","role_en":"World's largest optical fiber maker; the physical fiber behind hyperscaler AI corridors","supplies_en":"Fiber and cable (optical segment now over 40% of sales), pre-connectorized data center solutions and hollow-core fiber; multi-year deals with Lumen, AT&T and hyperscalers.","moat_en":"Scale plus a century of glass process know-how; US fiber capacity is locked under take-or-pay contracts. Risk: display cyclicality and consumer exposure (Gorilla Glass).","growth_en":"🔵 Enterprise optical +25%; group +12%","capex_2026_en":"~$1.8B; US fiber expansion","backlog_status_en":"Fiber sold out years ahead; take-or-pay signed","mkt":"GLW"},
  {"id":"Dell","label":"Dell Technologies","ticker":"DELL · NYSE","cat":"servers","port":"C1","role":"Fabricante de servidores de IA con el mayor canal enterprise.","supplies":"Servidores PowerEdge XE que integran GPUs de Nvidia y AMD, entregados a escala de rack listos para instalar. Llena los data centers de CoreWeave y suministra, junto a Super Micro, el superclúster Colossus de xAI.","moat":"~20% de cuota en servidores de IA y backlog de $43B. Relaciones enterprise profundas, logística global y gobernanza sólida — sin los problemas regulatorios de SMCI. El margen de integración es estrecho, pero el volumen, el storage y los servicios compensan.","loc":"EE.UU.","growth":"🔵 +25–35% ISG anual","margin":0.07,"capex_2026":"~$3B","backlog_status":"Backlog servidores IA $43B","country":"EEUU","mkt":"DELL","role_en":"AI server maker with the largest enterprise channel.","supplies_en":"PowerEdge XE servers integrating Nvidia and AMD GPUs, delivered at rack scale ready to install. Fills CoreWeave's data centers and, alongside Super Micro, supplies xAI's Colossus supercluster.","moat_en":"~20% share in AI servers and a $43B backlog. Deep enterprise relationships, global logistics and solid governance — without SMCI's regulatory troubles. The integration margin is thin, but volume, storage and services make up for it.","growth_en":"🔵 +25–35% ISG per year","capex_2026_en":"~$3B","backlog_status_en":"AI server backlog $43B"},
  {"id":"HPE","label":"Hewlett Packard Ent.","ticker":"HPE · NYSE","cat":"servers","port":"","role":"Fabricante de servidores IA, supercomputación Cray y cloud híbrido soberano.","supplies":"Servidores ProLiant con GPUs Nvidia, supercomputadoras Cray para laboratorios nacionales y soluciones de IA soberana para gobiernos de Europa y Asia. Con Juniper, añade networking propio a todo el stack.","moat":"~15% de cuota en servidores de IA y posición casi monopólica en supercomputación exascale (Cray). Diferenciado en sovereign AI; la adquisición de Juniper le permite atacar el networking de IA frente a Cisco y Arista.","loc":"EE.UU.","growth":"🔵 +20–25% anual","margin":0.09,"capex_2026":"~$2.5B","backlog_status":"Backlog de sistemas IA ~$9B","country":"EEUU","mkt":"HPE","role_en":"Maker of AI servers, Cray supercomputing and sovereign hybrid cloud.","supplies_en":"ProLiant servers with Nvidia GPUs, Cray supercomputers for national laboratories and sovereign AI solutions for governments across Europe and Asia. With Juniper, it adds in-house networking to the full stack.","moat_en":"~15% share in AI servers and a near-monopoly position in exascale supercomputing (Cray). Differentiated in sovereign AI; the Juniper acquisition lets it attack AI networking against Cisco and Arista.","growth_en":"🔵 +20–25% per year","capex_2026_en":"~$2.5B","backlog_status_en":"AI systems backlog ~$9B"},
  {"id":"Lenovo","label":"Lenovo","ticker":"0992 · HKEX","cat":"servers","port":"","role":"Fabricante de servidores de IA y puente comercial entre China y Occidente.","supplies":"Servidores con GPUs de Nvidia bajo el modelo TruScale (infraestructura como servicio) para clientes de Asia, Europa y América. Hereda la ingeniería x86 de IBM y vende a ambos lados de la frontera tecnológica.","moat":"~11% de cuota en servidores de IA y acceso único a los mercados chino y occidental. Ese mismo puente es su riesgo: un endurecimiento de los controles de exportación de EE.UU. podría cortarle el suministro de GPUs avanzadas.","loc":"China","growth":"🔵 +15–20% (ISG ~+30%)","margin":0.04,"capex_2026":"~$1.5B","backlog_status":"Cartera ISG en máximos; sin cifra pública","country":"China","mkt":"LNVGY","role_en":"AI server maker and commercial bridge between China and the West.","supplies_en":"Servers with Nvidia GPUs under the TruScale model (infrastructure as a service) for customers across Asia, Europe and the Americas. Inherits IBM's x86 engineering and sells on both sides of the technology divide.","moat_en":"~11% share in AI servers and unique access to both the Chinese and Western markets. That same bridge is its risk: tighter US export controls could cut off its supply of advanced GPUs.","growth_en":"🔵 +15–20% (ISG ~+30%)","capex_2026_en":"~$1.5B","backlog_status_en":"ISG backlog at record highs; no public figure"},
  {"id":"Foxconn","label":"Hon Hai (Foxconn)","ticker":"2317 · TWSE","cat":"servers","port":"","role":"Mayor ensamblador electrónico (EMS) del mundo; los servidores IA ya superan a los iPhones como motor.","supplies":"Ensambla los racks GB200/GB300 NVL72 de Nvidia — incluida la nueva planta de Houston construida con Nvidia — y servidores de IA para hyperscalers, además de ~70% de los iPhones de Apple.","moat":"Escala inigualable: nadie más ensambla racks de 120 kW a volumen en tres continentes. Socio manufacturero preferente de Nvidia en EE.UU., México y Taiwán; su riesgo estructural es el margen operativo fino (~3%) típico del negocio EMS.","loc":"Taiwán","growth":"🟢 +12–16% (servidores IA ~+100%)","margin":0.03,"capex_2026":"NT$150B+ (~$4.5B, plantas IA EE.UU./México)","backlog_status":"Racks NVL72 con visibilidad hasta 2027","country":"Taiwan","mkt":"HNHPF","role_en":"World's largest electronics assembler (EMS); AI servers now outweigh iPhones as its growth engine.","supplies_en":"Assembles Nvidia's GB200/GB300 NVL72 racks — including the new Houston plant built with Nvidia — and AI servers for hyperscalers, plus ~70% of Apple's iPhones.","moat_en":"Unmatched scale: no one else assembles 120 kW racks at volume on three continents. Nvidia's preferred manufacturing partner in the US, Mexico and Taiwan; its structural risk is the thin operating margin (~3%) typical of the EMS business.","growth_en":"🟢 +12–16% (AI servers ~+100%)","capex_2026_en":"NT$150B+ (~$4.5B, US/Mexico AI plants)","backlog_status_en":"NVL72 racks with visibility through 2027"},
  {"id":"SuperMicro","label":"Super Micro","ticker":"SMCI · Nasdaq","cat":"servers","port":"","role":"Pionero en servidores líquido-refrigerados — hoy bajo riesgo regulatorio severo.","supplies":"Servidores de IA con enfriamiento líquido directo, de los primeros en enviar racks Blackwell a volumen. Sigue siendo proveedor del superclúster Colossus de xAI junto a Dell, pese a su situación legal.","moat":"Primer mover en líquido y velocidad de diseño únicas, pero el indictment del DOJ (marzo 2026) destruye la confianza: clientes y proveedores migran hacia Dell y HPE. ⚠️ EXCLUIDA de carteras hasta resolución legal.","loc":"EE.UU.","growth":"⚡ +100% YoY previo; en riesgo por DOJ","margin":0.06,"capex_2026":"~$0.5B (campus San José y Malasia)","backlog_status":"⚠️ Backlog en riesgo: fuga de clientes tras indictment","risk":true,"country":"EEUU","mkt":"SMCI","role_en":"Pioneer in liquid-cooled servers — now under severe regulatory risk.","supplies_en":"AI servers with direct liquid cooling, among the first to ship Blackwell racks at volume. Remains a supplier to xAI's Colossus supercluster alongside Dell, despite its legal situation.","moat_en":"First mover in liquid cooling with unique design speed, but the DOJ indictment (March 2026) destroys confidence: customers and suppliers are migrating to Dell and HPE. ⚠️ EXCLUDED from portfolios until legal resolution.","growth_en":"⚡ +100% YoY prior; at risk from DOJ","capex_2026_en":"~$0.5B (San Jose and Malaysia campuses)","backlog_status_en":"⚠️ Backlog at risk: customer flight after indictment"},
  {"id":"Quanta","label":"Quanta Computer","ticker":"2382 · TWSE","cat":"servers","port":"","role":"ODM líder de servidores de IA para hyperscalers (QCT); fabrica racks GB300 para Meta, Microsoft y AWS","supplies":"Racks NVL72 GB300 integrados de extremo a extremo (L10-L12) con refrigeración líquida, servidores cloud generales y portátiles; los servidores de IA ya superan el 70% de su negocio de servidores.","moat":"Décadas de relación directa con hyperscalers y capacidad de integración líquida a escala; la expansión en EE.UU./México mitiga aranceles. Riesgos: márgenes ODM finos (~4%) y poder de negociación de Nvidia y clientes.","loc":"Taiwán","country":"Taiwan","growth":"⚡ Ingresos +60% 2026; servidores IA x2","margin":0.04,"capex_2026":"~$1B; plantas EE.UU. y México","backlog_status":"Slots GB300/Vera Rubin asignados hasta 2027","role_en":"Leading AI server ODM for hyperscalers (QCT); builds GB300 racks for Meta, Microsoft and AWS","supplies_en":"End-to-end integrated GB300 NVL72 racks (L10-L12) with liquid cooling, general cloud servers and notebooks; AI servers now exceed 70% of its server business.","moat_en":"Decades-long direct hyperscaler relationships and liquid-cooled integration at scale; US/Mexico expansion mitigates tariffs. Risks: thin ODM margins (~4%) and bargaining power of Nvidia and customers.","growth_en":"⚡ Revenue +60% 2026; AI servers 2x","capex_2026_en":"~$1B; US and Mexico plants","backlog_status_en":"GB300/Vera Rubin slots allocated into 2027"},
  {"id":"Celestica","label":"Celestica","ticker":"CLS · NYSE","cat":"servers","port":"","role":"ODM/EMS de servidores IA y switches 800G para hyperscalers; acción multiplicada por el boom de IA","supplies":"Switches Ethernet 800G de diseño propio (HPS) para Google, Meta y AWS, servidores de IA a medida y almacenamiento; su segmento CCS crece >40% anual.","moat":"El modelo HPS de diseño propio rinde márgenes superiores al EMS puro (~7% operativo) y ya ganó sockets 1.6T para 2027. Riesgos: concentración extrema (2 clientes >50% de ventas) y competencia de Accton/ODMs taiwaneses.","loc":"Canadá","country":"RestoMundo","growth":"🔵 Ingresos +30% 2026; guía elevada dos veces","margin":0.07,"capex_2026":"~$200M (~1,5% de ventas)","backlog_status":"Programas 800G/1.6T comprometidos hasta 2027","role_en":"AI server and 800G switch ODM/EMS for hyperscalers; stock multiplied by the AI boom","supplies_en":"Own-design 800G Ethernet switches (HPS) for Google, Meta and AWS, custom AI servers and storage; its CCS segment grows >40% per year.","moat_en":"Own-design HPS model yields margins above pure EMS (~7% operating) and has already won 1.6T sockets for 2027. Risks: extreme concentration (2 customers >50% of sales) and competition from Accton/Taiwanese ODMs.","growth_en":"🔵 Revenue +30% 2026; guidance raised twice","capex_2026_en":"~$200M (~1.5% of sales)","backlog_status_en":"800G/1.6T programs committed through 2027","mkt":"CLS"},
  {"id":"Jabil","label":"Jabil","ticker":"JBL · NYSE","cat":"servers","port":"","role":"EMS diversificado: racks de IA, fotónica y liquid cooling fabricados en EE.UU. y México","supplies":"Integración de racks GPU, transceptores y fotónica, liquid cooling y manufactura para salud, automoción y cloud; ingresos ligados a IA ~$10B en FY2026 y acuerdo para fabricar humanoides de Apptronik.","moat":"Huella fabril en EE.UU. (nueva planta de ~$500M) ventajosa bajo aranceles y relación profunda con Nvidia/hyperscalers en racks. Riesgos: márgenes EMS de ~5% y rotación de programas de consumo.","loc":"EE.UU.","country":"EEUU","growth":"🟢 Ingresos +12% FY2026; IA +40%","margin":0.055,"capex_2026":"~$1B; nueva planta en EE.UU.","backlog_status":"Pipeline IA ~$10B; pedidos de racks crecientes","role_en":"Diversified EMS: AI racks, photonics and liquid cooling built in the US and Mexico","supplies_en":"GPU rack integration, transceivers and photonics, liquid cooling plus health, auto and cloud manufacturing; AI-related revenue ~$10B in FY2026 and a deal to build Apptronik humanoids.","moat_en":"US manufacturing footprint (new ~$500M plant) advantaged under tariffs and deep rack relationships with Nvidia/hyperscalers. Risks: ~5% EMS margins and consumer program churn.","growth_en":"🟢 Revenue +12% FY2026; AI +40%","capex_2026_en":"~$1B; new US plant","backlog_status_en":"~$10B AI pipeline; rack orders rising","mkt":"JBL"},
  {"id":"Microsoft","label":"Microsoft (Azure)","ticker":"MSFT · Nasdaq","cat":"cloud","port":"","role":"Hyperscaler (Azure), mayor inversor de OpenAI y ahora también socio de Anthropic.","supplies":"Azure aloja a OpenAI y, desde nov 2025, sirve a Anthropic con un acuerdo de cómputo de $30B tras invertir $5B en el lab. Copilot integra IA en toda su suite y diseña su propio chip Maia para inferencia.","moat":"La forma más estable de tener exposición a OpenAI — y ahora a Anthropic. Negocio diversificado, muy rentable y con la mayor base enterprise del mundo; el riesgo es digerir $120B+ de CAPEX sin erosionar márgenes.","loc":"EE.UU.","growth":"🔵 Azure +30% anual","margin":0.45,"capex_2026":"$120B+ (data centers)","backlog_status":"RPO comercial ~$400B; incluye $30B de Anthropic","big":true,"country":"EEUU","mkt":"MSFT","role_en":"Hyperscaler (Azure), OpenAI's largest investor and now also an Anthropic partner.","supplies_en":"Azure hosts OpenAI and, since Nov 2025, serves Anthropic under a $30B compute deal after investing $5B in the lab. Copilot embeds AI across its entire suite, and it designs its own Maia chip for inference.","moat_en":"The most stable way to get exposure to OpenAI — and now to Anthropic. A diversified, highly profitable business with the world's largest enterprise base; the risk is digesting $120B+ of CAPEX without eroding margins.","growth_en":"🔵 Azure +30% per year","capex_2026_en":"$120B+ (data centers)","backlog_status_en":"Commercial RPO ~$400B; includes $30B from Anthropic"},
  {"id":"Amazon","label":"Amazon (AWS)","ticker":"AMZN · Nasdaq","cat":"cloud","port":"","role":"Mayor nube del mundo (AWS) e inversor ancla de Anthropic.","supplies":"AWS es el cloud líder. Invirtió $8B en Anthropic, que entrena Claude en 500K chips Trainium 2/3 propios de Amazon dentro del Project Rainier — el mayor clúster de silicio custom fuera del ecosistema Nvidia.","moat":"La forma más estable de tener exposición a Anthropic. Escala de AWS irreplicable y silicio propio (Trainium) que reduce su dependencia de Nvidia; el riesgo es ceder cuota de cargas de IA frente a Azure y Google Cloud.","loc":"EE.UU.","growth":"🔵 AWS +20%+ anual","margin":0.11,"capex_2026":"~$125B","backlog_status":"Backlog de AWS ~$250B en compromisos plurianuales","country":"EEUU","mkt":"AMZN","role_en":"World's largest cloud (AWS) and Anthropic's anchor investor.","supplies_en":"AWS is the leading cloud. It invested $8B in Anthropic, which trains Claude on 500K of Amazon's own Trainium 2/3 chips within Project Rainier — the largest custom-silicon cluster outside the Nvidia ecosystem.","moat_en":"The most stable way to get exposure to Anthropic. Irreplicable AWS scale and in-house silicon (Trainium) that reduces its dependence on Nvidia; the risk is ceding AI workload share to Azure and Google Cloud.","growth_en":"🔵 AWS +20%+ per year","capex_2026_en":"~$125B","backlog_status_en":"AWS backlog ~$250B in multi-year commitments"},
  {"id":"Alphabet","label":"Alphabet (Google Cloud)","ticker":"GOOGL · Nasdaq","cat":"cloud","port":"C2","role":"El único hyperscaler con cloud + modelo + chip propios (Gemini, TPU).","supplies":"Google Cloud + Gemini + TPU: la pila completa. Gemini subió de 5.7% a 21.5% del tráfico web en 12 meses, y por primera vez vende TPUs fuera de casa — ~1 GW comprometido con Anthropic, de quien además es inversor.","moat":"La apuesta de IA más completa e invertible HOY: posee toda la pila verticalmente y el TPU es la única alternativa real a Nvidia en entrenamiento a escala. Único lab frontera que se puede comprar en bolsa.","loc":"EE.UU.","growth":"🔵 Cloud +30%+ anual","margin":0.33,"capex_2026":"~$92B","backlog_status":"Backlog de Cloud ~$240B; TPUs a Anthropic (~1 GW)","big":true,"country":"EEUU","mkt":"GOOGL","role_en":"The only hyperscaler with its own cloud + model + chip (Gemini, TPU).","supplies_en":"Google Cloud + Gemini + TPU: the full stack. Gemini climbed from 5.7% to 21.5% of web traffic in 12 months, and for the first time it sells TPUs externally — ~1 GW committed to Anthropic, in which it is also an investor.","moat_en":"The most complete AI bet investable TODAY: it owns the entire stack vertically, and the TPU is the only real alternative to Nvidia for training at scale. The only frontier lab you can buy on the stock market.","growth_en":"🔵 Cloud +30%+ per year","capex_2026_en":"~$92B","backlog_status_en":"Cloud backlog ~$240B; TPUs to Anthropic (~1 GW)"},
  {"id":"Oracle","label":"Oracle (OCI)","ticker":"ORCL · NYSE","cat":"cloud","port":"C2","role":"Nube empresarial (OCI) y socio central del proyecto Stargate de OpenAI.","supplies":"OCI provee cómputo a escala y es el pilar de Stargate, uno de los mayores despliegues de data centers de IA de la historia. También aloja cargas de Meta y xAI — el arrendador favorito de los labs frontera.","moat":"OCI crece 50%+ anual y Stargate le da un RPO de ~$500B, el mayor backlog contratado del cloud. Riesgos: concentración extrema en OpenAI y deuda creciente para financiar la construcción antes de cobrar.","loc":"EE.UU.","growth":"🔵 OCI +40–50% anual","margin":0.3,"capex_2026":"~$35–40B","backlog_status":"RPO ~$500B (ancla: Stargate/OpenAI)","big":true,"country":"EEUU","mkt":"ORCL","role_en":"Enterprise cloud (OCI) and central partner in OpenAI's Stargate project.","supplies_en":"OCI provides compute at scale and is the pillar of Stargate, one of the largest AI data center buildouts in history. It also hosts Meta and xAI workloads — the frontier labs' favorite landlord.","moat_en":"OCI is growing 50%+ per year, and Stargate gives it an RPO of ~$500B, the largest contracted backlog in cloud. Risks: extreme concentration in OpenAI and rising debt to finance construction before collecting.","growth_en":"🔵 OCI +40–50% per year","capex_2026_en":"~$35–40B","backlog_status_en":"RPO ~$500B (anchor: Stargate/OpenAI)"},
  {"id":"CoreWeave","label":"CoreWeave","ticker":"CRWV · Nasdaq","cat":"cloud","port":"C1","role":"Neocloud líder — alquila cómputo GPU puro a labs de IA e hyperscalers.","supplies":"Capacidad de cómputo con GPUs Nvidia para labs e hyperscalers: contratos con OpenAI ($22B+) y Meta ($14B). Q1 2026: ingresos de $2.08B (+112% YoY).","moat":"El neocloud público más limpio y Nvidia es inversor. Pero alta deuda (financia GPUs con bonos respaldados por contratos), fuerte concentración de cliente y valuación exigente — especulativa.","loc":"EE.UU.","growth":"⚡ +112% YoY (Q1 2026)","margin":0.15,"capex_2026":"$25B+ (GPUs y data centers)","backlog_status":"RPO $99.4B","country":"EEUU","mkt":"CRWV","role_en":"Leading neocloud — rents pure GPU compute to AI labs and hyperscalers.","supplies_en":"Nvidia GPU compute capacity for labs and hyperscalers: contracts with OpenAI ($22B+) and Meta ($14B). Q1 2026: revenue of $2.08B (+112% YoY).","moat_en":"The cleanest public neocloud, with Nvidia as an investor. But high debt (it finances GPUs with contract-backed bonds), heavy customer concentration and a demanding valuation — speculative.","growth_en":"⚡ +112% YoY (Q1 2026)","capex_2026_en":"$25B+ (GPUs and data centers)","backlog_status_en":"RPO $99.4B"},
  {"id":"Nebius","label":"Nebius","ticker":"NBIS · Nasdaq","cat":"cloud","port":"","role":"Neocloud full-stack europeo en hipercrecimiento.","supplies":"Nube vertical para IA desde Ámsterdam: Q1 2026 con ingresos de $399M (+684% YoY). Contratos plurianuales de $19.4B con Microsoft y $27B con Meta que anclan toda su expansión de capacidad.","moat":"Full-stack para IA y menos deuda que CoreWeave, con $46B+ ya contratados. Pero cotiza a ~62x ventas — extremadamente cara; cualquier retraso en desplegar capacidad castigaría el múltiplo. Muy especulativa.","loc":"Países Bajos","growth":"⚡ +684% YoY (Q1 2026)","margin":-0.1,"capex_2026":"~$8–10B","backlog_status":"$46.4B contratados (Microsoft $19.4B + Meta $27B)","country":"PaisesBajos","mkt":"NBIS","role_en":"European full-stack neocloud in hypergrowth.","supplies_en":"Vertical AI cloud run from Amsterdam: Q1 2026 revenue of $399M (+684% YoY). Multi-year contracts of $19.4B with Microsoft and $27B with Meta anchor its entire capacity expansion.","moat_en":"Full-stack for AI with less debt than CoreWeave and $46B+ already contracted. But it trades at ~62x sales — extremely expensive; any delay in deploying capacity would punish the multiple. Highly speculative.","growth_en":"⚡ +684% YoY (Q1 2026)","capex_2026_en":"~$8–10B","backlog_status_en":"$46.4B contracted (Microsoft $19.4B + Meta $27B)"},
  {"id":"Equinix","label":"Equinix","ticker":"EQIX · Nasdaq","cat":"cloud","port":"","role":"Mayor REIT de data centers neutrales: 270+ centros en 35 países y el tejido de interconexión global","supplies":"Colocation e interconexión neutral (Equinix Fabric, 480.000+ cross-connects) en más de 270 data centers; campus xScale para hyperscalers e IA.","moat":"Efecto red único: 480.000+ cross-connects y ecosistemas de nubes, carriers y finanzas que no pueden mudarse; el boom eléctrico de la IA revaloriza su potencia ya contratada. Riesgo: deuda sensible a tipos y el capex xScale diluye retornos a corto.","loc":"EE.UU.","country":"EEUU","growth":"🟢 +8% ingresos; AFFO por acción +9%","margin":0.17,"capex_2026":"~$4.000M propios + JVs xScale $15.000M","backlog_status":"Pipeline xScale récord; potencia agotada en hubs","role_en":"Largest neutral data-center REIT: 270+ sites in 35 countries and the global interconnection fabric","supplies_en":"Neutral colocation and interconnection (Equinix Fabric, 480,000+ cross-connects) across 270+ data centers; xScale campuses for hyperscalers and AI.","moat_en":"Unmatched network effect: 480,000+ cross-connects and cloud/carrier/finance ecosystems that cannot relocate; the AI power crunch re-rates its already-secured electricity. Risk: rate-sensitive debt and xScale capex diluting near-term returns.","growth_en":"🟢 +8% revenue; AFFO per share +9%","capex_2026_en":"~$4B own + $15B xScale JVs","backlog_status_en":"Record xScale pipeline; power sold out in key hubs","mkt":"EQIX"},
  {"id":"DigitalRealty","label":"Digital Realty","ticker":"DLR · NYSE","cat":"cloud","port":"","role":"REIT global de data centers (300+ instalaciones); capacidad arrendada a hyperscalers y neoclouds","supplies":"Colocation y capacidad hiperescala en 25+ países, campus de IA con densidades >150 kW/rack y liquid cooling; interconexión ServiceFabric entre nubes y operadores.","moat":"Suelo más energía asegurada (varios GW en pipeline) en mercados saturados como Ashburn: irreplicable a corto plazo. Riesgos: deuda sensible a tipos y hyperscalers autoconstruyendo capacidad.","loc":"EE.UU.","country":"EEUU","growth":"🟢 Core FFO +8-10% 2026; leasing récord","margin":0.15,"capex_2026":"~$3,5B desarrollo; >70% pre-arrendado","backlog_status":"Backlog de leasing récord >$1B anualizado","role_en":"Global data center REIT (300+ facilities); capacity leased to hyperscalers and neoclouds","supplies_en":"Colocation and hyperscale capacity across 25+ countries, AI campuses with >150 kW/rack densities and liquid cooling; ServiceFabric interconnection across clouds and carriers.","moat_en":"Land plus secured power (multi-GW pipeline) in saturated markets like Ashburn: irreplicable near term. Risks: rate-sensitive debt and hyperscalers self-building capacity.","growth_en":"🟢 Core FFO +8-10% 2026; record leasing","capex_2026_en":"~$3.5B development; >70% pre-leased","backlog_status_en":"Record leasing backlog >$1B annualized","mkt":"DLR"},
  {"id":"OpenAI","label":"OpenAI","ticker":"Pre-IPO ~sept 2026","cat":"ailab","port":"","role":"Laboratorio de IA frontera — creador de ChatGPT/GPT; IPO apuntada a ~sept 2026.","supplies":"Los modelos GPT que potencian ChatGPT y miles de aplicaciones. Construye Stargate con Oracle/Microsoft y diversifica su silicio: 6 GW con AMD (con warrants), 10 GW de ASICs custom con Broadcom y un contrato de $20B con Cerebras.","moat":"Líder en IA generativa por adopción, aunque pierde cuota ante Gemini (de 86.7% a 64.5%). Sus compromisos de cómputo superan el billón de dólares: el foso es la escala, el riesgo es financiarla. Pre-IPO: exposición indirecta vía Microsoft.","loc":"EE.UU.","growth":"⭐ PRE-IPO ~sept 2026","margin":-1.2,"capex_2026":"vía socios (Stargate/Oracle)","backlog_status":"Compromisos de cómputo >$1T firmados","preipo":true,"big":true,"country":"EEUU","role_en":"Frontier AI lab — creator of ChatGPT/GPT; IPO targeted for ~Sept 2026.","supplies_en":"The GPT models powering ChatGPT and thousands of applications. Building Stargate with Oracle/Microsoft and diversifying its silicon: 6 GW with AMD (with warrants), 10 GW of custom ASICs with Broadcom and a $20B contract with Cerebras.","moat_en":"Leader in generative AI by adoption, though losing share to Gemini (from 86.7% to 64.5%). Its compute commitments exceed one trillion dollars: the moat is scale, the risk is financing it. Pre-IPO: indirect exposure via Microsoft.","growth_en":"⭐ PRE-IPO ~Sept 2026","capex_2026_en":"via partners (Stargate/Oracle)","backlog_status_en":"Compute commitments >$1T signed"},
  {"id":"Anthropic","label":"Anthropic","ticker":"Pre-IPO (filed jun 2026)","cat":"ailab","port":"","role":"Laboratorio de IA frontera — creador de Claude; IPO confidencial presentada el 1 jun 2026.","supplies":"Los modelos Claude y Claude Code, líderes en programación y uso empresarial. Run-rate de ingresos ~$47B, entrenando sobre 500K Trainium de Amazon, ~1 GW de TPUs de Google y $30B de cómputo en Azure.","moat":"Mayor valoración de IA del mundo (~$965B) y primer gran lab en salir a bolsa. El triple respaldo de hyperscalers (Amazon $8B, Google, Microsoft $5B) diversifica su cómputo; hasta el IPO, exposición indirecta vía sus inversores.","loc":"EE.UU.","growth":"⭐ PRE-IPO (filed 1 jun 2026)","margin":-0.3,"capex_2026":"n/s — cómputo vía AWS/GCP/Azure","backlog_status":"Cómputo asegurado: 500K Trainium + ~1 GW TPU + $30B Azure","preipo":true,"big":true,"country":"EEUU","role_en":"Frontier AI lab — creator of Claude; confidential IPO filed June 1, 2026.","supplies_en":"The Claude and Claude Code models, leaders in coding and enterprise use. Revenue run-rate of ~$47B, training on 500K Amazon Trainium chips, ~1 GW of Google TPUs and $30B of Azure compute.","moat_en":"The world's highest AI valuation (~$965B) and the first major lab to go public. Triple hyperscaler backing (Amazon $8B, Google, Microsoft $5B) diversifies its compute; until the IPO, indirect exposure via its investors.","growth_en":"⭐ PRE-IPO (filed June 1, 2026)","capex_2026_en":"n/a — compute via AWS/GCP/Azure","backlog_status_en":"Compute secured: 500K Trainium + ~1 GW TPU + $30B Azure"},
  {"id":"xAI","label":"xAI (+SpaceX)","ticker":"Pre-IPO finales 2026","cat":"ailab","port":"","role":"Laboratorio de IA frontera fusionado con SpaceX — creador de Grok.","supplies":"El modelo Grok, integrado con X. Opera el superclúster Colossus 1/2 en Memphis con servidores de Dell y Super Micro. IPO combinada con SpaceX apuntada a finales de 2026 (~$2T), buscando levantar $75B+.","moat":"Respaldado por Musk e integrado verticalmente con X/SpaceX (datos, distribución, energía). Sería una de las mayores IPOs de la historia, pero quema caja a ritmo extremo y su proveedor Super Micro arrastra un indictment del DOJ.","loc":"EE.UU.","growth":"⭐ PRE-IPO finales 2026 (~$2T)","margin":-1.5,"capex_2026":"$15–20B (Colossus 1/2)","backlog_status":"Colossus 2 en expansión; demanda cautiva de X/SpaceX","preipo":true,"country":"EEUU","role_en":"Frontier AI lab merged with SpaceX — creator of Grok.","supplies_en":"The Grok model, integrated with X. Operates the Colossus 1/2 supercluster in Memphis on Dell and Super Micro servers. Combined IPO with SpaceX targeted for late 2026 (~$2T), aiming to raise $75B+.","moat_en":"Backed by Musk and vertically integrated with X/SpaceX (data, distribution, energy). It would be one of the largest IPOs in history, but it burns cash at an extreme pace and its supplier Super Micro is dragging a DOJ indictment.","growth_en":"⭐ PRE-IPO late 2026 (~$2T)","capex_2026_en":"$15–20B (Colossus 1/2)","backlog_status_en":"Colossus 2 expanding; captive demand from X/SpaceX"},
  {"id":"Mistral","label":"Mistral AI","ticker":"Pre-IPO · Europa","cat":"ailab","port":"","role":"Laboratorio de IA europeo — campeón open-weight y soberano.","supplies":"Modelos open-weight (Mistral Large, Codestral) como alternativa soberana europea a los labs de EE.UU., distribuidos vía Azure por su partnership con Microsoft y desplegados en empresas y gobiernos de la UE.","moat":"Campeón europeo de IA con viento regulatorio a favor (soberanía de datos) y ASML como inversor ancla. Menor escala que OpenAI/Anthropic y compite contra modelos abiertos gratuitos. Pre-IPO.","loc":"Francia","growth":"⭐ PRE-IPO · Europa","margin":-0.8,"capex_2026":"~€1–2B (clúster propio en Francia)","backlog_status":"Contratos enterprise y de gobiernos UE en expansión","preipo":true,"country":"Francia","role_en":"European AI lab — open-weight and sovereign champion.","supplies_en":"Open-weight models (Mistral Large, Codestral) as Europe's sovereign alternative to US labs, distributed via Azure through its Microsoft partnership and deployed across EU companies and governments.","moat_en":"Europe's AI champion with regulatory tailwinds (data sovereignty) and ASML as anchor investor. Smaller scale than OpenAI/Anthropic and competes against free open models. Pre-IPO.","growth_en":"⭐ PRE-IPO · Europe","capex_2026_en":"~€1–2B (own cluster in France)","backlog_status_en":"Expanding enterprise and EU government contracts"},
  {"id":"Meta","label":"Meta","ticker":"META · Nasdaq","cat":"ailab","port":"","role":"Hyperscaler de consumo y laboratorio de IA (LLaMA) — invertible vía META.","supplies":"Los modelos LLaMA open-weight y la IA que monetiza a sus 3,500M de usuarios. Diseña su chip MTIA con Broadcom y compra cómputo externo a CoreWeave ($14B), Nebius ($27B) y Oracle.","moat":"Escala de distribución masiva y un negocio publicitario que autofinancia el CAPEX de IA. Su estrategia open-weight comoditiza a los rivales; el riesgo es que MTIA no madure y siga cautiva del silicio de Nvidia.","loc":"EE.UU.","growth":"🔵 +15–18% ingresos 2026","margin":0.4,"capex_2026":"$66B+ (IA y data centers)","backlog_status":"n/a — autoconsumo; cómputo externo contratado a neoclouds","country":"EEUU","mkt":"META","role_en":"Consumer hyperscaler and AI lab (LLaMA) — investable via META.","supplies_en":"The open-weight LLaMA models and the AI monetizing its 3,500M users. Designs its MTIA chip with Broadcom and buys external compute from CoreWeave ($14B), Nebius ($27B) and Oracle.","moat_en":"Massive distribution scale and an advertising business that self-funds its AI CAPEX. Its open-weight strategy commoditizes rivals; the risk is that MTIA fails to mature, leaving it captive to Nvidia silicon.","growth_en":"🔵 +15–18% revenue 2026","capex_2026_en":"$66B+ (AI and data centers)","backlog_status_en":"n/a — self-consumption; external compute contracted with neoclouds"},
  {"id":"DeepSeek","label":"DeepSeek","ticker":"No cotiza · China","cat":"ailab","port":"","role":"Lab chino de IA de eficiencia extrema; R2/V4 alcanzan la frontera con una fracción del cómputo","supplies":"Modelos open-weight R2 (razonamiento) y V4, entrenados e inferidos sobre Huawei Ascend; API con precios 10-20x por debajo de los rivales occidentales que ancla el precio mundial del token.","moat":"Eficiencia algorítmica demostrada (MoE, MLA) que convierte la escasez de cómputo en ventaja, con respaldo financiero de High-Flyer. Riesgos: sanciones limitan el cómputo, monetización incipiente y techo regulatorio chino.","loc":"China","country":"China","growth":"⭐ PRE-IPO; adopción de API en explosión","margin":null,"capex_2026":"Cómputo Ascend; financia High-Flyer","backlog_status":"N/A; demanda de API racionada por cómputo","role_en":"Chinese extreme-efficiency AI lab; R2/V4 reach the frontier with a fraction of the compute","supplies_en":"Open-weight R2 (reasoning) and V4 models, trained and served on Huawei Ascend; an API priced 10-20x below Western rivals that anchors the global token price.","moat_en":"Proven algorithmic efficiency (MoE, MLA) that turns compute scarcity into an edge, backed financially by High-Flyer. Risks: sanctions cap compute, monetization is nascent and Chinese regulatory ceiling.","growth_en":"⭐ PRE-IPO; API adoption exploding","capex_2026_en":"Ascend compute; High-Flyer funded","backlog_status_en":"N/A; API demand rationed by compute","preipo":true},
  {"id":"Qwen","label":"Alibaba (Qwen)","ticker":"BABA · NYSE","cat":"ailab","port":"","role":"Familia Qwen de Alibaba: el open-weight más usado del mundo; invertible vía BABA","supplies":"Modelos Qwen3 abiertos, del edge a la frontera, con 600M+ descargas y ~170.000 derivados en Hugging Face; motor del crecimiento de Alibaba Cloud y del asistente Quark.","moat":"Efecto ecosistema: estándar de facto open-weight en Asia y emergentes, integrado con la nube #1 de China. Riesgos: monetización indirecta (vía cloud) y sanciones que limitan el cómputo disponible de Alibaba.","loc":"China","country":"China","growth":"🔵 Alibaba Cloud +28% impulsado por IA","margin":0.13,"capex_2026":"Dentro del plan BABA ~$53B/3 años","backlog_status":"N/A; inferencia limitada por capacidad","role_en":"Alibaba's Qwen family: the world's most used open-weight models; investable via BABA","supplies_en":"Open Qwen3 models from edge to frontier, with 600M+ downloads and ~170,000 derivatives on Hugging Face; the engine behind Alibaba Cloud's growth and the Quark assistant.","moat_en":"Ecosystem effect: de facto open-weight standard across Asia and emerging markets, integrated with China's #1 cloud. Risks: indirect monetization (via cloud) and sanctions limiting Alibaba's available compute.","growth_en":"🔵 Alibaba Cloud +28% driven by AI","capex_2026_en":"Within BABA's ~$53B/3-yr plan","backlog_status_en":"N/A; inference capped by capacity","mkt":"BABA"},
  {"id":"Tesla","label":"Tesla","ticker":"TSLA · Nasdaq","cat":"robotics_physical","port":"C2","role":"Autonomía + robótica + energía — plataforma de IA física.","supplies":"FSD (8.4B millas conducidas), robotaxi Cybercab (producción abr 2026), robot Optimus y su chip propio AI5, fabricado por TSMC y Samsung. Morgan Stanley la define como plataforma de IA, no automotriz.","moat":"Foso de datos de conducción único. Opcionalidad masiva en robotaxi ($10T TAM según Ark) y robótica. Pero cotiza a 320x earnings y el FCF es negativo en 2026 (capex $25B).","loc":"EE.UU.","growth":"🔵 +15–20% 2026 (Cybercab/energía)","margin":0.07,"capex_2026":"$25B","backlog_status":"Megapack vendido ~12 meses; Cybercab en rampa","big":true,"country":"EEUU","mkt":"TSLA","role_en":"Autonomy + robotics + energy — a physical AI platform.","supplies_en":"FSD (8.4B miles driven), the Cybercab robotaxi (production Apr 2026), the Optimus robot and its own AI5 chip, manufactured by TSMC and Samsung. Morgan Stanley frames it as an AI platform, not a carmaker.","moat_en":"A unique driving-data moat. Massive optionality in robotaxi ($10T TAM per Ark) and robotics. But it trades at 320x earnings and FCF is negative in 2026 (capex $25B).","growth_en":"🔵 +15–20% 2026 (Cybercab/energy)","capex_2026_en":"$25B","backlog_status_en":"Megapack sold out ~12 months; Cybercab ramping"},
  {"id":"Figure","label":"Figure AI","ticker":"Pre-IPO ~$39B","cat":"robotics_physical","port":"","role":"Robots humanoides — el mejor financiado del sector.","supplies":"Robots humanoides Figure 03, fabricados en la planta BotQ (uno cada 90 minutos). Pilotos con BMW y UPS. Backers: Microsoft, OpenAI, Nvidia y Bezos.","moat":"El humanoide mejor financiado (~$39B de valoración). Pero esa cifra descansa sobre ingresos ínfimos — decenas de millones de ARR. Pre-IPO, sin S-1 presentado.","loc":"EE.UU.","growth":"⭐ PRE-IPO (sin S-1 aún)","margin":null,"capex_2026":"~$1B (escalado de BotQ)","backlog_status":"Pilotos BMW/UPS; sin libro de órdenes público","preipo":true,"big":true,"country":"EEUU","role_en":"Humanoid robots — the best funded in the sector.","supplies_en":"Figure 03 humanoid robots, built at the BotQ plant (one every 90 minutes). Pilots with BMW and UPS. Backers: Microsoft, OpenAI, Nvidia and Bezos.","moat_en":"The best-funded humanoid (~$39B valuation). But that figure rests on tiny revenue — tens of millions in ARR. Pre-IPO, no S-1 filed.","growth_en":"⭐ PRE-IPO (no S-1 yet)","capex_2026_en":"~$1B (BotQ scale-up)","backlog_status_en":"BMW/UPS pilots; no public order book"},
  {"id":"BostonDynamics","label":"Boston Dynamics","ticker":"vía Hyundai (no cotiza)","cat":"robotics_physical","port":"","role":"Pionero de la robótica dinámica — subsidiaria de Hyundai; humanoides para logística.","supplies":"Atlas eléctrico en pilotos logísticos con Hyundai (Metaplant de Georgia) y DHL; robots Spot y Stretch ya comerciales. La IA embarcada corre sobre cómputo Jetson de Nvidia.","moat":"Tres décadas de liderazgo en locomoción y manipulación — el catálogo robótico más probado del sector. Riesgo: monetización lenta frente a rivales mejor financiados; solo invertible vía Hyundai.","loc":"EE.UU.","growth":"⭐ No cotiza — subsidiaria de Hyundai","margin":null,"capex_2026":"n/d — financiada por Hyundai","backlog_status":"Atlas en pilotos (Hyundai, DHL); Spot/Stretch comerciales","preipo":true,"country":"EEUU","role_en":"Pioneer of dynamic robotics — Hyundai subsidiary; humanoids for logistics.","supplies_en":"Electric Atlas in logistics pilots with Hyundai (Georgia Metaplant) and DHL; Spot and Stretch robots already commercial. Onboard AI runs on Nvidia Jetson compute.","moat_en":"Three decades of leadership in locomotion and manipulation — the most proven robot lineup in the sector. Risk: slow monetization versus better-funded rivals; only investable via Hyundai.","growth_en":"⭐ Not listed — Hyundai subsidiary","capex_2026_en":"n/a — funded by Hyundai","backlog_status_en":"Atlas in pilots (Hyundai, DHL); Spot/Stretch commercial"},
  {"id":"OneX","label":"1X Technologies","ticker":"Pre-IPO","cat":"robotics_physical","port":"","role":"Robots humanoides NEO para el hogar — respaldado por OpenAI.","supplies":"Humanoide NEO para tareas domésticas: preórdenes abiertas desde finales de 2025 (~$20,000 o suscripción mensual) y primeras entregas en hogares de EE.UU. Respaldado por OpenAI y EQT.","moat":"El único humanoide que apunta primero al hogar, no a la fábrica — el mercado más grande y el más difícil técnicamente. Pre-IPO temprano: ingresos incipientes, dependiente de nuevas rondas.","loc":"Noruega","growth":"⭐ PRE-IPO temprano","margin":null,"capex_2026":"n/d — fábrica propia en escalado","backlog_status":"Preórdenes de NEO abiertas; entregas iniciales EE.UU.","preipo":true,"country":"RestoEuropa","role_en":"NEO humanoid robots for the home — backed by OpenAI.","supplies_en":"NEO humanoid for household chores: preorders open since late 2025 (~$20,000 or a monthly subscription), with first deliveries to US homes. Backed by OpenAI and EQT.","moat_en":"The only humanoid targeting the home first, not the factory — the largest market and the hardest technically. Early pre-IPO: nascent revenue, dependent on new funding rounds.","growth_en":"⭐ Early PRE-IPO","capex_2026_en":"n/a — own factory scaling up","backlog_status_en":"NEO preorders open; initial US deliveries"},
  {"id":"Unitree","label":"Unitree Robotics","ticker":"Pre-IPO · China","cat":"robotics_physical","port":"","role":"Robots cuadrúpedos y humanoides G1/H2 a precios disruptivos; IPO prevista en el STAR Market","supplies":"Humanoides G1 (~$16.000) y H2, cuadrúpedos Go2/B2 y actuadores propios; vende miles de unidades a laboratorios, industria y consumo apoyado en la cadena de suministro china de bajo coste.","moat":"Integración vertical de actuadores y motores que sitúa sus precios 5-10x por debajo de rivales occidentales, con volumen real de ventas único en el sector. Riesgo: el software y la autonomía van por detrás del hardware.","loc":"China","country":"China","growth":"⭐ PRE-IPO; ventas estimadas x2-3 anual","margin":null,"capex_2026":"Escala fábrica de Hangzhou pre-IPO","backlog_status":"Pedidos sobre capacidad; meses de espera","role_en":"Quadruped robots and G1/H2 humanoids at disruptive prices; STAR Market IPO planned","supplies_en":"G1 (~$16,000) and H2 humanoids, Go2/B2 quadrupeds and in-house actuators; ships thousands of units to labs, industry and consumers on the back of China's low-cost supply chain.","moat_en":"Vertical integration of actuators and motors puts pricing 5-10x below Western rivals, with real sales volume unique in the sector. Risk: software and autonomy lag the hardware.","growth_en":"⭐ PRE-IPO; sales estimated 2-3x yearly","capex_2026_en":"Scaling Hangzhou plant pre-IPO","backlog_status_en":"Orders above capacity; months-long waits","preipo":true},
  {"id":"Apptronik","label":"Apptronik","ticker":"Pre-IPO · EE.UU.","cat":"robotics_physical","port":"","role":"Humanoide Apollo para logística e industria; inversión de Google, pilotos con Mercedes y GXO","supplies":"Robots Apollo (carga 25 kg, batería intercambiable) en pilotos con Mercedes-Benz, GXO y GE Appliances; manufactura escalable vía acuerdo con Jabil e IA de Google DeepMind (Gemini Robotics).","moat":"Herencia de la NASA (Valkyrie), ~$403M de Serie A liderada por Google y vía de manufactura con Jabil. Riesgos: aún pre-ingresos relevantes, Tesla/Figure/Unitree compiten y el ROI del humanoide está sin probar.","loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO; de pilotos a despliegue 2026-27","margin":null,"capex_2026":"Financiado por Serie A ~$403M","backlog_status":"Pilotos Mercedes/GXO; sin pedidos en volumen","role_en":"Apollo humanoid for logistics and industry; Google-backed, pilots with Mercedes and GXO","supplies_en":"Apollo robots (25 kg payload, swappable battery) in pilots with Mercedes-Benz, GXO and GE Appliances; scalable manufacturing via the Jabil deal and Google DeepMind AI (Gemini Robotics).","moat_en":"NASA heritage (Valkyrie), ~$403M Series A led by Google and a manufacturing path with Jabil. Risks: still pre-meaningful revenue, Tesla/Figure/Unitree compete and humanoid ROI remains unproven.","growth_en":"⭐ PRE-IPO; pilots to deployment 2026-27","capex_2026_en":"Funded by ~$403M Series A","backlog_status_en":"Mercedes/GXO pilots; no volume orders yet","preipo":true},
  {"id":"Palantir","label":"Palantir","ticker":"PLTR · Nasdaq","cat":"aisoft","port":"","role":"Software de IA para empresas y defensa — plataforma AIP.","supplies":"Plataforma AIP que aplica LLMs a operaciones de empresas y gobierno/defensa, integrando modelos de OpenAI y Anthropic sobre los datos del cliente. El segmento comercial de EE.UU. crece >50%.","moat":"Líder en IA aplicada a defensa, con contratos federales pegajosos y una ontología propietaria difícil de replicar. El riesgo es el múltiplo, no el negocio: valuación extrema, 200x+ earnings.","loc":"EE.UU.","growth":"🔵 +35–45% 2026","margin":0.32,"capex_2026":"n/s — asset-light sobre hyperscalers","backlog_status":"RPO ~$3–4B; cartera total de contratos >$10B","country":"EEUU","mkt":"PLTR","role_en":"AI software for enterprises and defense — the AIP platform.","supplies_en":"The AIP platform applies LLMs to enterprise and government/defense operations, integrating OpenAI and Anthropic models on top of client data. The US commercial segment is growing >50%.","moat_en":"Leader in defense-applied AI, with sticky federal contracts and a proprietary ontology that is hard to replicate. The risk is the multiple, not the business: extreme valuation, 200x+ earnings.","growth_en":"🔵 +35–45% 2026","capex_2026_en":"n/a — asset-light on hyperscalers","backlog_status_en":"RPO ~$3–4B; total contract book >$10B"},
  {"id":"CrowdStrike","label":"CrowdStrike","ticker":"CRWD · Nasdaq","cat":"aisoft","port":"","role":"Ciberseguridad nativa de IA — plataforma Falcon.","supplies":"Plataforma Falcon de protección de endpoints, nube e identidad, con el agente Charlotte AI para triaje autónomo de amenazas. Modelo modular: casi la mitad de los clientes usa 6+ módulos.","moat":"Líder en endpoint security; su telemetría masiva entrena la IA y crea un efecto red de amenazas. Beneficiario doble: la IA potencia su producto y multiplica los ataques de los que defiende.","loc":"EE.UU.","growth":"🔵 +20–25% 2026","margin":0.22,"capex_2026":"~$250M (SaaS ligero)","backlog_status":"ARR ~$5.5B; RPO >$6B","country":"EEUU","mkt":"CRWD","role_en":"AI-native cybersecurity — the Falcon platform.","supplies_en":"Falcon platform for endpoint, cloud and identity protection, with the Charlotte AI agent for autonomous threat triage. Modular model: nearly half of customers use 6+ modules.","moat_en":"Leader in endpoint security; its massive telemetry trains the AI and creates a threat network effect. A double beneficiary: AI powers its product and multiplies the attacks it defends against.","growth_en":"🔵 +20–25% 2026","capex_2026_en":"~$250M (asset-light SaaS)","backlog_status_en":"ARR ~$5.5B; RPO >$6B"},
  {"id":"Snowflake","label":"Snowflake","ticker":"SNOW · NYSE","cat":"aisoft","port":"","role":"Data cloud empresarial — la capa de datos donde aterriza la IA generativa.","supplies":"Almacén y compartición de datos multi-nube sobre AWS, Azure y GCP. Cortex AI integra Claude y GPT directamente sobre los datos del cliente, sin sacarlos de su gobernanza. Más de 11,000 clientes.","moat":"Efecto red del data sharing: miles de empresas intercambian datos vivos dentro de su nube. Riesgo: paga la infraestructura a los hyperscalers que también compiten con ella, y Databricks presiona precios.","loc":"EE.UU.","growth":"🔵 +25–30% producto 2026","margin":0.08,"capex_2026":"n/s — corre sobre AWS/Azure/GCP","backlog_status":"RPO ~$7.5B (+30% YoY)","country":"EEUU","mkt":"SNOW","role_en":"Enterprise data cloud — the data layer where generative AI lands.","supplies_en":"Multi-cloud data warehousing and sharing on AWS, Azure and GCP. Cortex AI integrates Claude and GPT directly on top of customer data without taking it outside their governance. More than 11,000 customers.","moat_en":"Network effect from data sharing: thousands of companies exchange live data inside its cloud. Risk: it pays infrastructure costs to the hyperscalers that also compete with it, and Databricks pressures pricing.","growth_en":"🔵 +25–30% product 2026","capex_2026_en":"n/a — runs on AWS/Azure/GCP","backlog_status_en":"RPO ~$7.5B (+30% YoY)"},
  /* ===== v7 · M8: nuevos nodos ===== */
  {"id":"Huawei","label":"Huawei","ticker":"Privada (Shenzhen)","cat":"fabless","port":"","role":"Conglomerado chino sancionado: líder en telecom, dueño de HiSilicon y Ascend AI.","supplies":"Chips Ascend 910B para IA, chips Kirin para móviles, equipos 5G para 170 países.","moat":"Ecosistema cerrado pero completo: diseño (HiSilicon), manufactura (vía SMIC), software (MindSpore). Sancionado por EE.UU. desde 2019.","loc":"China","growth":"🔵 +15% recuperación post-sanciones","margin":0.14,"capex_2026":"~$10B","backlog_status":"Backlog 5G activo en 170 países","country":"China","role_en":"Sanctioned Chinese conglomerate: telecom leader, HiSilicon and Ascend AI owner.","supplies_en":"Ascend 910B AI chips, Kirin mobile chips, 5G equipment in 170 countries.","moat_en":"Closed but complete ecosystem: design (HiSilicon), manufacturing (via SMIC), software (MindSpore). US-sanctioned since 2019.","growth_en":"🔵 +15% post-sanctions recovery","capex_2026_en":"~$10B","backlog_status_en":"Active 5G backlog in 170 countries"},
  {"id":"MediaTek","label":"MediaTek","ticker":"2454 · TWSE","cat":"fabless","port":"","role":"2º fabless global por volumen: SoCs para smartphones Android, IoT y TV.","supplies":"Dimensity SoCs (TSMC 4nm/3nm), Helio para gama media, chips WiFi 7 y 5G para Xiaomi, OPPO, Samsung.","moat":"Domina gama media-alta Android con >40% market share en smartphones. Competidor directo de Qualcomm en precio/rendimiento.","loc":"Taiwán","growth":"🟢 +18% impulsado por AIoT y edge AI","margin":0.49,"capex_2026":"Bajo: fabless","backlog_status":"Backlog sólido en gama media","country":"Taiwan","role_en":"2nd global fabless by volume: SoCs for Android smartphones, IoT and TV.","supplies_en":"Dimensity SoCs (TSMC 4nm/3nm), Helio for mid-range, WiFi 7 and 5G chips for Xiaomi, OPPO, Samsung.","moat_en":"Dominates mid-to-high Android with >40% smartphone market share. Direct Qualcomm competitor on price/performance.","growth_en":"🟢 +18% driven by AIoT and edge AI","capex_2026_en":"Low: fabless","backlog_status_en":"Solid mid-range backlog"},
  {"id":"Groq","label":"Groq","ticker":"Privada (Series D)","cat":"ailab","port":"","preipo":true,"role":"LPU (Language Processing Unit): el chip de inferencia más rápido del mundo — rival de Nvidia para serving.","supplies":"GroqCloud: inferencia a 500+ tokens/s en Llama-3, Mixtral. LPU fabricado en TSMC. Target: hyperscalers y empresas con latencia crítica.","moat":"Arquitectura LPU diseñada desde cero para inferencia secuencial, no entrenamiento. 10x menor latencia que GPU para serving. Riesgo: Nvidia contraataca con Blackwell inference.","loc":"EE.UU.","growth":"⚡ Pre-revenue pero >1M users en GroqCloud","margin":null,"capex_2026":"Series D ~$640M para escalar fab","backlog_status":"GroqCloud en beta pública; waitlist enterprise","country":"EEUU","role_en":"LPU (Language Processing Unit): the fastest inference chip in the world — Nvidia rival for serving.","supplies_en":"GroqCloud: inference at 500+ tokens/s on Llama-3, Mixtral. LPU fabricated at TSMC. Target: hyperscalers and latency-critical enterprises.","moat_en":"LPU architecture designed from scratch for sequential inference, not training. 10x lower latency than GPU for serving. Risk: Nvidia counters with Blackwell inference.","growth_en":"⚡ Pre-revenue but >1M users on GroqCloud","capex_2026_en":"Series D ~$640M to scale fab","backlog_status_en":"GroqCloud in public beta; enterprise waitlist"},
  {"id":"SambaNova","label":"SambaNova","ticker":"Privada (Series D)","cat":"ailab","port":"","preipo":true,"role":"Full-stack IA: chip RDU (Reconfigurable Dataflow Unit) + software + modelos para enterprise.","supplies":"SambaNova Suite: hardware + modelos preentrenados para banca, salud y gobierno. National AI Cloud en partenariado con EE.UU. DoE.","moat":"Vende el paquete completo (chip+software+modelo), no solo hardware. Clientes como DoE, Samsung y servicios financieros. Compite con Nvidia en el nicho enterprise regulado.","loc":"EE.UU.","growth":"🔵 +80% e. 2025 (base pequeña)","margin":null,"capex_2026":"~$300M Series D (2023)","backlog_status":"National AI Cloud activo en laboratorios DoE","country":"EEUU","role_en":"Full-stack AI: RDU chip + software + models for enterprise.","supplies_en":"SambaNova Suite: hardware + pretrained models for banking, health and government. National AI Cloud partnered with US DoE.","moat_en":"Sells the complete package (chip+software+model), not just hardware. Clients include DoE, Samsung and financial services. Competes with Nvidia in regulated enterprise niche.","growth_en":"🔵 +80% est. 2025 (small base)","capex_2026_en":"~$300M Series D (2023)","backlog_status_en":"National AI Cloud active at DoE labs"},
  {"id":"WesternDigital","label":"Western Digital","ticker":"WDC · Nasdaq","cat":"memory","port":"","role":"Spin-off SanDisk completado: WD se enfoca en HDD y enterprise SSD tras separar NAND flash.","supplies":"HDDs enterprise para datacenters (HAMR technology), SSDs NVMe para servidores.","moat":"Líder HDD junto a Seagate; HAMR lleva densidad a 40TB+. Datacenters necesitan ambos HDD y SSD en distintas capas del storage hierarchy.","loc":"EE.UU.","growth":"🟡 +8% ciclo storage en recuperación","margin":0.22,"capex_2026":"~$1.5B","backlog_status":"HDD enterprise con demanda recuperándose","country":"EEUU","mkt":"WDC","role_en":"SanDisk spin-off completed: WD focuses on HDD and enterprise SSD after separating NAND flash.","supplies_en":"Enterprise HDDs for datacenters (HAMR technology), NVMe SSDs for servers.","moat_en":"HDD leader alongside Seagate; HAMR pushes density to 40TB+. Datacenters need both HDD and SSD in different storage hierarchy layers.","growth_en":"🟡 +8% storage cycle recovery","capex_2026_en":"~$1.5B","backlog_status_en":"Enterprise HDD demand recovering"},
  {"id":"Naver","label":"Naver (HyperCLOVA X)","ticker":"035420 · KOSPI","cat":"cloud","port":"","role":"Hyperscaler coreano: HyperCLOVA X (82B params) compite con ChatGPT en coreano.","supplies":"CLOVA Studio API, búsqueda Naver (70% Korea), Webtoon, cloud NAVER Cloud Platform.","moat":"Dominancia lingüística coreana — ningún modelo occidental lo supera en coreano/japonés. Infraestructura soberana Corea fuera del alcance de sanciones EE.UU.","loc":"Corea del Sur","growth":"🔵 +25% NAVER Cloud impulsado por HyperCLOVA","margin":0.28,"capex_2026":"~$1B en infraestructura IA","backlog_status":">100K empresas en NAVER Cloud Korea","country":"Corea","role_en":"Korean hyperscaler: HyperCLOVA X (82B params) competes with ChatGPT in Korean.","supplies_en":"CLOVA Studio API, Naver search (70% Korea), Webtoon, NAVER Cloud Platform.","moat_en":"Korean linguistic dominance — no Western model beats it in Korean/Japanese. Sovereign Korean infrastructure outside US sanction reach.","growth_en":"🔵 +25% NAVER Cloud driven by HyperCLOVA","capex_2026_en":"~$1B in AI infrastructure","backlog_status_en":">100K companies on NAVER Cloud Korea"},
  /* ===== v7 · nodos de soporte (referenciados por links M1/M8) ===== */
  {"id":"SoftBank","label":"SoftBank Group","ticker":"9984 · TSE","cat":"cloud","port":"","role":"Conglomerado inversor japonés: dueño de ARM, líder de la ronda de OpenAI y socio del megaproyecto Stargate.","supplies":"Capital a escala: Vision Funds, ~90% de ARM, participaciones en OpenAI y robótica; co-construye datacenters IA Stargate en EE.UU. con OpenAI y Oracle.","moat":"Pocas entidades pueden firmar cheques de $30B+ por una sola tesis. Su control de ARM le da exposición a casi todo chip móvil del planeta. Riesgo: apalancamiento y concentración extrema en IA.","loc":"Japón","growth":"🔵 NAV ligado a ARM y cartera IA","margin":0.10,"capex_2026":"$19B comprometidos en Stargate (fase 1)","backlog_status":"Stargate: objetivo $100–500B en 4 años","country":"Japon","role_en":"Japanese investment conglomerate: ARM owner, leader of the OpenAI round and Stargate megaproject partner.","supplies_en":"Capital at scale: Vision Funds, ~90% of ARM, stakes in OpenAI and robotics; co-builds Stargate AI datacenters in the US with OpenAI and Oracle.","moat_en":"Few entities can write $30B+ checks on a single thesis. ARM control gives exposure to nearly every mobile chip on the planet. Risk: leverage and extreme AI concentration.","growth_en":"🔵 NAV tied to ARM and AI portfolio","capex_2026_en":"$19B committed to Stargate (phase 1)","backlog_status_en":"Stargate: $100–500B target over 4 years"},
  {"id":"Xiaomi","label":"Xiaomi","ticker":"1810 · HKEX","cat":"fabless","port":"","role":"Gigante chino de electrónica de consumo que ya diseña su propio silicio (XRING O1) y fabrica EVs.","supplies":"Smartphones (3º global), SoC XRING O1 (TSMC N4), EVs SU7/YU7, ecosistema AIoT de 900M+ dispositivos.","moat":"Integración hardware-software-EV única en China; canal directo a cientos de millones de usuarios. Riesgo: dependencia de TSMC y Qualcomm bajo controles de exportación.","loc":"China","growth":"🟢 +30% impulsado por EV y gama premium","margin":0.06,"capex_2026":"~$4B (EV + chips)","backlog_status":"SU7: ~150K pedidos pendientes","country":"China","role_en":"Chinese consumer-electronics giant now designing its own silicon (XRING O1) and building EVs.","supplies_en":"Smartphones (#3 global), XRING O1 SoC (TSMC N4), SU7/YU7 EVs, AIoT ecosystem of 900M+ devices.","moat_en":"Unique hardware-software-EV integration in China; direct channel to hundreds of millions of users. Risk: dependence on TSMC and Qualcomm under export controls.","growth_en":"🟢 +30% driven by EV and premium tier","capex_2026_en":"~$4B (EV + chips)","backlog_status_en":"SU7: ~150K pending orders"},
  {"id":"BMW","label":"BMW Group","ticker":"BMW · XETRA","cat":"robotics_physical","port":"","role":"Fabricante premium alemán — primer cliente industrial de los humanoides Figure 02 en su planta de Spartanburg.","supplies":"Vehículos premium y EVs (Neue Klasse); banco de pruebas industrial para humanoides y automatización con IA.","moat":"Marca y manufactura de precisión centenarias; su adopción temprana de humanoides marca el estándar para la automoción occidental.","loc":"Alemania","growth":"🟡 +5% — ciclo Neue Klasse","margin":0.08,"capex_2026":"~€9B","backlog_status":"Neue Klasse: lanzamientos 2026–2028","country":"Alemania","role_en":"German premium carmaker — first industrial customer of Figure 02 humanoids at its Spartanburg plant.","supplies_en":"Premium vehicles and EVs (Neue Klasse); industrial testbed for humanoids and AI automation.","moat_en":"Century-old brand and precision manufacturing; its early humanoid adoption sets the standard for Western automotive.","growth_en":"🟡 +5% — Neue Klasse cycle","capex_2026_en":"~€9B","backlog_status_en":"Neue Klasse: 2026–2028 launches"},
  {"id":"Hyundai","label":"Hyundai Motor","ticker":"005380 · KRX","cat":"robotics_physical","port":"","role":"3º fabricante mundial de coches y propietario de Boston Dynamics — la apuesta coreana por la IA física.","supplies":"Vehículos (Hyundai/Kia/Genesis), Metaplant Georgia con robots Atlas/Spot/Stretch, inversión de $21B en EE.UU. 2025–2028.","moat":"Único automotor que posee un líder de robótica humanoide (Boston Dynamics, $1.1B en 2021). Manufactura verticalizada Corea–EE.UU.","loc":"Corea del Sur","growth":"🟡 +6% — EVs e hibridación","margin":0.09,"capex_2026":"~$16B (grupo)","backlog_status":"Metaplant: 300K EVs/año en rampa","country":"Corea","role_en":"World's #3 carmaker and Boston Dynamics owner — Korea's bet on physical AI.","supplies_en":"Vehicles (Hyundai/Kia/Genesis), Georgia Metaplant with Atlas/Spot/Stretch robots, $21B US investment 2025–2028.","moat_en":"The only automaker owning a humanoid robotics leader (Boston Dynamics, $1.1B in 2021). Vertically integrated Korea–US manufacturing.","growth_en":"🟡 +6% — EVs and hybridization","capex_2026_en":"~$16B (group)","backlog_status_en":"Metaplant: 300K EVs/yr ramping"},
  {"id":"SAIC","label":"SAIC Motor","ticker":"600104 · SSE","cat":"robotics_physical","port":"","role":"Mayor grupo automotor de China (~5M coches/año) — primera línea de producción con humanoides Unitree G1.","supplies":"Vehículos MG/Roewe/IM Motors y joint-ventures con VW y GM; banco de pruebas de robots humanoides en línea de montaje.","moat":"Escala estatal: ~5M vehículos/año y acceso preferente al ecosistema robótico chino (Unitree, Agibot). Riesgo: aranceles UE/EE.UU. a EVs chinos.","loc":"China","growth":"🟡 +3% — presión de precios EV","margin":0.03,"capex_2026":"~$7B","backlog_status":"MG: expansión UE/LatAm","country":"China","role_en":"China's largest auto group (~5M cars/yr) — first production line with Unitree G1 humanoids.","supplies_en":"MG/Roewe/IM Motors vehicles and JVs with VW and GM; humanoid-robot testbed on the assembly line.","moat_en":"State scale: ~5M vehicles/yr and preferred access to China's robotics ecosystem (Unitree, Agibot). Risk: EU/US tariffs on Chinese EVs.","growth_en":"🟡 +3% — EV price pressure","capex_2026_en":"~$7B","backlog_status_en":"MG: EU/LatAm expansion"}
];

const RAW_LINKS = [

  /* ---- Capa cuántica ---- */
  /* ---- EDA / IP ---- */
  /* ---- Óptica ---- */
  /* ---- Equipamiento ---- */
  /* ---- Materiales ---- */
  /* ---- Foundry ---- */
  /* ---- Fabless/Diseño ---- */
  /* ---- Memoria ---- */
  /* ---- Substrates/Packaging ---- */
  /* ---- Networking ---- */
  /* ---- Power ---- */
  /* ---- Conectividad ---- */
  /* ---- Servidores/ODM ---- */
  /* ---- Cloud ---- */
  /* ---- AI Labs ---- */
  /* ---- Robótica ---- */
  /* ---- AI Software ---- */
  ['Bluefors','IBMQuantum',3,'Criostatos de dilución para qubits superconductores','supply'],
  ['Bluefors','Rigetti',2,'Criostatos de dilución (~10 mK)','supply'],
  ['Bluefors','PsiQuantum',3,'Criogenia a escala industrial para fotónica','supply'],
  ['Bluefors','DWave',2,'Criostatos para annealers cuánticos','supply'],
  ['OxfordInstruments','IBMQuantum',1,'Componentes criogénicos e instrumentación','supply'],
  ['OxfordInstruments','Rigetti',2,'Sistemas de dilución Proteox','supply'],
  ['OxfordInstruments','DWave',1,'Instrumentación criogénica','supply'],
  ['GF','PsiQuantum',3,'Fabrica sus chips cuánticos fotónicos','fab'],
  ['IonQ','Amazon',2,'Computación cuántica vía AWS Braket','cloud'],
  ['IonQ','Microsoft',2,'Computación cuántica vía Azure Quantum','cloud'],
  ['Rigetti','Amazon',1,'Acceso a QPUs vía AWS Braket','cloud'],
  ['Rigetti','Microsoft',1,'Acceso a QPUs vía Azure Quantum','cloud'],
  ['DWave','Amazon',1,'Annealing cuántico vía AWS Braket','cloud'],
  ['Synopsys','Nvidia',2,'Software EDA para diseño de GPUs','license'],
  ['Synopsys','AMD',2,'Herramientas de síntesis y verificación','license'],
  ['Synopsys','Broadcom',2,'Herramientas de verificación de ASICs','license'],
  ['Synopsys','Intel',2,'Flujo EDA para el nodo 18A','license'],
  ['Cadence','Nvidia',2,'Software EDA y simulación','license'],
  ['Cadence','Apple',2,'Herramientas EDA para chips A/M','license'],
  ['Cadence','Qualcomm',2,'Software de diseño analógico','license'],
  ['Cadence','Marvell',1,'Flujo de diseño de chips de red','license'],
  ['ARM','Apple',3,'Arquitectura de los chips serie A/M','license'],
  ['ARM','Qualcomm',3,'Arquitectura de los Snapdragon','license'],
  ['ARM','Nvidia',2,'Arquitectura de las CPUs Grace/Vera','license'],
  ['ARM','Amazon',2,'Arquitectura de las CPUs Graviton','license'],
  ['ARM','Microsoft',1,'Arquitectura de la CPU Cobalt','license'],
  ['SiemensEDA','Intel',1,'Verificación y diseño de PCB','license'],
  ['SiemensEDA','Broadcom',1,'Herramientas de emulación Veloce','license'],
  ['Zeiss','ASML',5,'Ópticas EUV pulidas a nivel atómico — monopolio','supply'],
  ['Trumpf','ASML',4,'Láser CO₂ que genera la luz EUV','supply'],
  ['MitsuiChemicals','ASML',2,'Pellicles EUV (membranas de ~50nm)','supply'],
  ['MitsuiChemicals','TSMC',1,'Pellicles para máscaras de producción','supply'],
  ['Toto','Lam',2,'Mandriles electrostáticos (ESC) cerámicos','supply'],
  ['Toto','AMAT',1,'Componentes cerámicos de cámara','supply'],
  ['Toto','TEL',2,'ESC para equipos de pista y grabado','supply'],
  ['ASML','TSMC',6,'Máquinas EUV y High-NA (€350M c/u)','supply'],
  ['ASML','Samsung',4,'Litografía EUV para foundry y memoria','fab'],
  ['ASML','Intel',3,'High-NA EUV para el nodo 18A/14A','fab'],
  ['ASML','Micron',2,'EUV para DRAM 1γ','supply'],
  ['ASML','SKHynix',2,'EUV para DRAM y HBM','supply'],
  ['ASML','Rapidus',2,'EUV para el nodo 2nm japonés','fab'],
  ['AMAT','TSMC',3,'Deposición, implantación y CMP','supply'],
  ['AMAT','Samsung',3,'Equipos de deposición','supply'],
  ['AMAT','Intel',3,'Deposición y materiales de ingeniería','supply'],
  ['AMAT','Micron',2,'Equipos para fabricación de memoria','fab'],
  ['AMAT','SKHynix',2,'Deposición para HBM','supply'],
  ['Lam','TSMC',3,'Grabado por plasma','supply'],
  ['Lam','Samsung',3,'Grabado para memoria 3D','supply'],
  ['Lam','SKHynix',3,'Grabado para HBM y DRAM','supply'],
  ['Lam','Micron',3,'Grabado para NAND de 200+ capas','supply'],
  ['Lam','Kioxia',2,'Grabado de canales NAND 3D','supply'],
  ['KLA','TSMC',3,'Inspección y metrología de obleas','supply'],
  ['KLA','Samsung',2,'Detección de defectos atómicos','supply'],
  ['KLA','Intel',2,'Control de proceso del 18A','fab'],
  ['TEL','TSMC',3,'Pistas de fotorresistencias (coater/developer)','supply'],
  ['TEL','Samsung',2,'Coater/developer de resists','supply'],
  ['TEL','SKHynix',2,'Equipos de pista y grabado','supply'],
  ['TEL','Rapidus',2,'Socio clave de equipamiento del 2nm','cloud'],
  ['ASMInt','TSMC',2,'Reactores ALD para nodos avanzados','supply'],
  ['ASMInt','Samsung',2,'Deposición de capas atómicas','supply'],
  ['ASMInt','Intel',2,'ALD para transistores GAA','fab'],
  ['Nikon','Intel',1,'Escáneres DUV para capas no críticas','supply'],
  ['Nikon','SMIC',2,'Litografía DUV (alternativa a ASML)','fab'],
  ['Canon','SMIC',2,'Litografía DUV para nodos maduros','fab'],
  ['Canon','Kioxia',2,'Nanoimprint (NIL) co-desarrollada para NAND','supply'],
  ['ShinEtsu','TSMC',3,'Obleas de silicio 300mm de pureza extrema','supply'],
  ['ShinEtsu','Samsung',2,'Obleas y fotorresistencias EUV','supply'],
  ['ShinEtsu','Micron',2,'Obleas para memoria','supply'],
  ['ShinEtsu','SKHynix',2,'Obleas 300mm para DRAM/HBM','supply'],
  ['SUMCO','TSMC',2,'Obleas de silicio 300mm','supply'],
  ['SUMCO','Samsung',2,'Obleas de silicio','supply'],
  ['SUMCO','Kioxia',2,'Obleas para NAND','supply'],
  ['Siltronic','Intel',1,'Obleas europeas 300mm','supply'],
  ['Siltronic','Samsung',1,'Obleas de silicio','supply'],
  ['GlobalWafers','TSMC',2,'Obleas 200/300mm','supply'],
  ['GlobalWafers','GF',2,'Obleas desde su fab de Texas','supply'],
  ['GlobalWafers','Intel',1,'Obleas SOI y epitaxiales','supply'],
  ['Ajinomoto','Ibiden',5,'Film ABF — monopolio sin sustituto','supply'],
  ['Ajinomoto','Unimicron',5,'Film ABF para sustratos de IA','supply'],
  ['JSR','TSMC',3,'Fotorresistencias EUV de alta resolución','supply'],
  ['JSR','Samsung',2,'Fotorresistencias EUV','supply'],
  ['JSR','Intel',2,'Resists para litografía avanzada','fab'],
  ['TokyoOhka','TSMC',2,'Resists DUV/EUV y developers','supply'],
  ['TokyoOhka','SKHynix',2,'Fotorresistencias para memoria','supply'],
  ['TokyoOhka','Samsung',2,'Resists de alta resolución','supply'],
  ['Entegris','TSMC',2,'Filtración ultra-pura y FOUPs','supply'],
  ['Entegris','Micron',2,'Filtración de químicos y gases','supply'],
  ['Entegris','Intel',1,'Sistemas de manejo de materiales','supply'],
  ['Entegris','SKHynix',1,'Pureza de proceso para HBM','fab'],
  ['MerckKGaA','TSMC',2,'Precursores CVD/ALD y gases especiales','supply'],
  ['MerckKGaA','Samsung',2,'Materiales de deposición (Versum)','supply'],
  ['MerckKGaA','Intel',1,'Químicos de proceso','fab'],
  ['Linde','TSMC',2,'Gases UHP con plantas on-site','supply'],
  ['Linde','Samsung',2,'N₂, Ar, H₂ de ultra-alta pureza','supply'],
  ['Linde','Intel',2,'Gases industriales para fabs de EE.UU.','supply'],
  ['Linde','Micron',1,'Gases de proceso','fab'],
  ['AirLiquide','TSMC',2,'Gases UHP y precursores ALD','supply'],
  ['AirLiquide','Samsung',1,'Gases especiales','supply'],
  ['AirLiquide','SMIC',1,'Gases industriales','supply'],
  ['TSMC','Nvidia',6,'Fabrica sus GPUs en 3nm/2nm + CoWoS','fab'],
  ['TSMC','AMD',5,'Fabrica CPUs EPYC y GPUs Instinct','fab'],
  ['TSMC','Apple',6,'Fabrica los chips A/M en nodos punteros','fab'],
  ['TSMC','Qualcomm',4,'Fabrica los SoCs Snapdragon','fab'],
  ['TSMC','Broadcom',4,'Fabrica TPUs y ASICs custom','fab'],
  ['TSMC','Marvell',3,'Fabrica chips de red y DSPs','fab'],
  ['TSMC','Cisco',2,'Fabrica el ASIC Silicon One','fab'],
  ['TSMC','Credo',2,'Fabrica chips SerDes en 3nm','fab'],
  ['TSMC','Astera',2,'Fabrica chips PCIe 6','fab'],
  ['TSMC','Tesla',3,'Fabrica el chip AI5 de conducción','license'],
  ['Samsung','Qualcomm',2,'Foundry alternativa para Snapdragon','supply'],
  ['Samsung','Tesla',2,'Segunda fuente del AI5/AI6','supply'],
  ['Samsung','Nvidia',2,'Memoria HBM3E y foundry alternativa','supply'],
  ['Intel','Dell',3,'CPUs Xeon para servidores','supply'],
  ['Intel','HPE',3,'CPUs para servidores enterprise','supply'],
  ['Intel','Lenovo',2,'Procesadores para servidores y PCs','supply'],
  ['SMIC','Lenovo',1,'Chips de nodos maduros para mercado chino','supply'],
  ['GF','Qualcomm',1,'Chips de RF y nodos maduros','supply'],
  ['SKHynix','Nvidia',6,'HBM3E/HBM4 apilada sobre cada GPU','supply'],
  ['SKHynix','AMD',2,'HBM para GPUs Instinct','supply'],
  ['SKHynix','Dell',2,'DRAM para servidores','supply'],
  ['SKHynix','SuperMicro',1,'Memoria para servidores GPU','supply'],
  ['Micron','Nvidia',3,'HBM3E/HBM4 (segunda fuente)','supply'],
  ['Micron','AMD',2,'DRAM y HBM','supply'],
  ['Micron','Dell',2,'DDR5 para servidores','supply'],
  ['Micron','HPE',1,'Memoria para data centers','supply'],
  ['Kioxia','SanDisk',3,'Joint venture de fabs NAND compartidas','supply'],
  ['Kioxia','Dell',2,'SSDs enterprise','supply'],
  ['Kioxia','HPE',1,'NAND para almacenamiento','supply'],
  ['SanDisk','Dell',2,'SSDs de alta capacidad','supply'],
  ['SanDisk','Lenovo',1,'Almacenamiento flash','supply'],
  ['Ibiden','Nvidia',5,'Sustratos ABF del B200/Vera Rubin','supply'],
  ['Ibiden','AMD',3,'Sustratos de alto rendimiento','supply'],
  ['Ibiden','Intel',3,'Sustratos de empaquetado','supply'],
  ['Unimicron','Nvidia',3,'Sustratos ABF complementarios','supply'],
  ['Unimicron','AMD',2,'Sustratos de alta densidad','supply'],
  ['Unimicron','Broadcom',2,'Sustratos para ASICs','supply'],
  ['ASE','Nvidia',3,'Empaquetado avanzado (desborde de CoWoS)','supply'],
  ['ASE','AMD',2,'Empaquetado 2.5D/3D','supply'],
  ['ASE','Qualcomm',2,'Empaquetado y testing de SoCs','supply'],
  ['ASE','Broadcom',2,'Empaquetado de ASICs','supply'],
  ['ASE','Apple',2,'Empaquetado SiP','supply'],
  ['Amkor','Apple',2,'Empaquetado en Arizona (junto a TSMC AZ)','supply'],
  ['Amkor','Qualcomm',2,'Empaquetado y testing','supply'],
  ['Amkor','Nvidia',1,'Capacidad OSAT en EE.UU.','supply'],
  ['Advantest','TSMC',2,'Testers para validación de obleas','supply'],
  ['Advantest','SKHynix',3,'Testing de cada pila de HBM','supply'],
  ['Advantest','Micron',2,'Testing de DRAM/HBM','supply'],
  ['Advantest','Samsung',2,'Testing de memoria y SoCs','supply'],
  ['Nvidia','Dell',6,'GPUs para servidores PowerEdge XE','supply'],
  ['Nvidia','HPE',4,'GPUs para ProLiant y Cray','supply'],
  ['Nvidia','SuperMicro',3,'GPUs para servidores líquido-refrigerados','supply'],
  ['Nvidia','Lenovo',2,'GPUs para TruScale','supply'],
  ['Nvidia','Foxconn',3,'GPUs y diseño de racks GB300 NVL72','license'],
  ['Nvidia','CoreWeave',6,'GPUs que forman el neocloud — y es inversor','cloud'],
  ['Nvidia','Nebius',4,'GPUs para la nube de IA','cloud'],
  ['Nvidia','Oracle',5,'GPUs para OCI / Stargate','cloud'],
  ['Nvidia','Microsoft',5,'GPUs para Azure','cloud'],
  ['Nvidia','Amazon',4,'GPUs para AWS','cloud'],
  ['Nvidia','Alphabet',3,'GPUs para Google Cloud','cloud'],
  ['Nvidia','Meta',4,'GPUs para los clústeres de LLaMA','supply'],
  ['Nvidia','xAI',5,'GPUs del superclúster Colossus','supply'],
  ['Nvidia','Mistral',2,'GPUs y partnership de cómputo','license'],
  ['Nvidia','Tesla',3,'GPUs para entrenar FSD/Optimus','supply'],
  ['Nvidia','Figure',2,'Cómputo embarcado para humanoides','supply'],
  ['Nvidia','BostonDynamics',2,'Jetson Thor para el Atlas eléctrico','supply'],
  ['AMD','Dell',3,'CPUs EPYC y GPUs Instinct','supply'],
  ['AMD','HPE',3,'EPYC e Instinct para servidores','supply'],
  ['AMD','Microsoft',3,'GPUs MI350 para Azure','cloud'],
  ['AMD','Oracle',3,'GPUs Instinct para OCI','cloud'],
  ['AMD','Meta',2,'EPYC e Instinct en sus data centers','supply'],
  ['AMD','OpenAI',4,'Acuerdo de 6 GW de GPUs Instinct + warrants','supply'],
  ['Qualcomm','Apple',1,'Módems 5G (en transición a chip propio)','license'],
  ['Apple','Foxconn',3,'Diseños de iPhone/Mac para ensamblaje','license'],
  ['Broadcom','Alphabet',4,'Co-diseña y suministra las TPU','cloud'],
  ['Broadcom','Meta',3,'Co-diseña el ASIC MTIA','supply'],
  ['Broadcom','OpenAI',4,'ASIC custom de 10 GW en desarrollo','supply'],
  ['Broadcom','Arista',3,'Chips de switching Tomahawk','supply'],
  ['Broadcom','Cisco',1,'Chips de red complementarios','supply'],
  ['Broadcom','Dell',2,'Controladoras y conectividad','supply'],
  ['Broadcom','Apple',2,'Chips de RF y wireless','supply'],
  ['Marvell','Microsoft',3,'Co-diseña el acelerador Maia','cloud'],
  ['Marvell','Amazon',3,'Co-diseña Trainium con Annapurna','cloud'],
  ['Marvell','Coherent',2,'DSPs para módulos ópticos','supply'],
  ['Marvell','Dell',1,'Chips de infraestructura de datos','supply'],
  ['Credo','Microsoft',3,'Cables eléctricos activos (AEC) para Azure','cloud'],
  ['Credo','Amazon',3,'AECs para los racks de AWS','cloud'],
  ['Credo','xAI',2,'Conectividad de cobre para Colossus','supply'],
  ['Astera','Dell',2,'Retimers PCIe 6 para racks de IA','supply'],
  ['Astera','Amazon',2,'Conectividad PCIe para AWS','cloud'],
  ['Astera','Microsoft',2,'Retimers y switching para Azure','cloud'],
  ['Astera','SuperMicro',1,'Conectividad PCIe','supply'],
  ['Coherent','Arista',2,'Transceptores ópticos para switches','supply'],
  ['Coherent','Cisco',2,'Módulos ópticos 800G','supply'],
  ['Coherent','Microsoft',2,'Transceptores 800G/1.6T para Azure','cloud'],
  ['Coherent','CoreWeave',2,'Óptica de interconexión del data center','cloud'],
  ['Coherent','Nvidia',2,'Co-packaged optics (partnership)','supply'],
  ['Arista','Microsoft',3,'Switches Ethernet — su mayor cliente','cloud'],
  ['Arista','Meta',3,'Switches 800G para clústeres de IA','supply'],
  ['Arista','Oracle',2,'Red Ethernet para OCI','cloud'],
  ['Arista','CoreWeave',2,'Switching del neocloud','cloud'],
  ['Cisco','Microsoft',2,'Routers y switches para Azure','cloud'],
  ['Cisco','Amazon',1,'Equipos de red para AWS','cloud'],
  ['Cisco','Oracle',2,'Networking del proyecto Stargate','cloud'],
  ['SubCom','Alphabet',3,'Tiende sus cables submarinos privados','cloud'],
  ['SubCom','Meta',3,'Instala el cable Waterworth (40.000 km)','supply'],
  ['SubCom','Microsoft',2,'Cables transatlánticos','cloud'],
  ['SubCom','Amazon',2,'Sistemas submarinos para AWS','cloud'],
  ['NEC','Meta',2,'Cables transpacíficos','supply'],
  ['NEC','Amazon',2,'Sistemas submarinos de fibra','cloud'],
  ['NEC','Microsoft',1,'Cables de fibra óptica submarina','cloud'],
  ['ASN','Meta',2,'Cables 2Africa/Amitié','supply'],
  ['ASN','Alphabet',1,'Sistemas submarinos europeos','cloud'],
  ['ASN','Microsoft',1,'Cables transatlánticos','cloud'],
  ['Lumen','Microsoft',3,'Fibra continental dedicada para IA','cloud'],
  ['Lumen','Amazon',2,'Red PCF para interconectar data centers','cloud'],
  ['Lumen','Meta',2,'Capacidad de fibra de larga distancia','supply'],
  ['Lumen','Oracle',1,'Fibra entre campus de Stargate','cloud'],
  ['Vertiv','Dell',2,'Enfriamiento líquido para racks','supply'],
  ['Vertiv','CoreWeave',3,'Cooling y energía del data center','cloud'],
  ['Vertiv','Oracle',3,'Infraestructura térmica de Stargate','cloud'],
  ['Vertiv','Microsoft',2,'Distribución eléctrica y cooling','cloud'],
  ['Vertiv','xAI',2,'Enfriamiento líquido de Colossus','supply'],
  ['MPWR','Nvidia',3,'VRMs en cada placa de GPU','supply'],
  ['MPWR','Dell',2,'Chips de gestión de energía','supply'],
  ['MPWR','SuperMicro',1,'Power management para servidores','supply'],
  ['Eaton','Microsoft',2,'Switchgear y distribución eléctrica','cloud'],
  ['Eaton','Amazon',2,'UPS y transformadores para AWS','cloud'],
  ['Eaton','Oracle',2,'Infraestructura eléctrica de Stargate','cloud'],
  ['Schneider','Microsoft',2,'Infraestructura eléctrica de DC','cloud'],
  ['Schneider','Alphabet',2,'Distribución y gestión energética','cloud'],
  ['Schneider','CoreWeave',2,'Diseño eléctrico + cooling Motivair','license'],
  ['Schneider','Nebius',1,'Infraestructura de data center','cloud'],
  ['Dell','CoreWeave',4,'Servidores que llenan el neocloud','cloud'],
  ['Dell','xAI',3,'Servidores GPU para Colossus','supply'],
  ['Dell','Microsoft',2,'PowerEdge para Azure','cloud'],
  ['Dell','Oracle',2,'Servidores para OCI','cloud'],
  ['HPE','Oracle',2,'Servidores para cloud','cloud'],
  ['HPE','Microsoft',1,'Infraestructura para Azure','cloud'],
  ['Lenovo','Microsoft',1,'Servidores para Azure','cloud'],
  ['Lenovo','Nebius',1,'Hardware para la nube de IA','cloud'],
  ['Foxconn','Microsoft',2,'Ensambla racks GB300 como ODM','cloud'],
  ['Foxconn','Amazon',2,'Servidores ODM para AWS','cloud'],
  ['Foxconn','Oracle',2,'Racks NVL72 para Stargate','cloud'],
  ['Foxconn','CoreWeave',1,'Ensamblaje de servidores GPU','cloud'],
  ['SuperMicro','CoreWeave',2,'Servidores líquido-refrigerados','cloud'],
  ['SuperMicro','xAI',3,'Mitad de los racks de Colossus','supply'],
  ['SuperMicro','Oracle',1,'Servidores para el data center','cloud'],
  ['Microsoft','OpenAI',6,'Azure aloja a OpenAI; mayor inversor','cloud'],
  ['Microsoft','Anthropic',3,'Inversión $5B + acuerdo Azure de $30B','invest'],
  ['Microsoft','Mistral',1,'Partnership de distribución en Azure','license'],
  ['Microsoft','Figure',2,'Inversor de Figure AI','cloud'],
  ['Amazon','Anthropic',6,'AWS + $8B; Claude entrena en Trainium','cloud'],
  ['Amazon','Snowflake',2,'AWS aloja la mayoría de sus cargas','cloud'],
  ['Amazon','CrowdStrike',2,'Falcon corre sobre AWS','cloud'],
  ['Alphabet','Anthropic',4,'Inversor + hasta 1 GW de TPUs','cloud'],
  ['Oracle','OpenAI',6,'OCI es el socio central de Stargate','cloud'],
  ['Oracle','xAI',2,'Capacidad OCI para entrenar Grok','cloud'],
  ['Oracle','Meta',2,'Acuerdo de cómputo multianual','cloud'],
  ['CoreWeave','OpenAI',5,'Contratos de cómputo por $22B+','cloud'],
  ['CoreWeave','Microsoft',3,'Capacidad GPU de desborde para Azure','cloud'],
  ['CoreWeave','Meta',3,'Contrato de cómputo de $14B','cloud'],
  ['Nebius','Microsoft',3,'Contrato de cómputo de $19.4B','cloud'],
  ['Nebius','Meta',3,'Contrato de cómputo de $27B','cloud'],
  ['Microsoft','Snowflake',1,'Azure como segunda nube','cloud'],
  ['OpenAI','Palantir',1,'Modelos GPT en aplicaciones enterprise','supply'],
  ['OpenAI','Snowflake',1,'GPT integrado en Cortex AI','supply'],
  ['OpenAI','CrowdStrike',1,'LLMs detrás de Charlotte AI','supply'],
  ['OpenAI','Figure',2,'Modelos para el humanoide (histórico) e inversor','supply'],
  ['OpenAI','OneX',2,'Inversor y socio de modelos','cloud'],
  ['Anthropic','Palantir',2,'Claude en defensa vía FedStart','supply'],
  ['Anthropic','Snowflake',2,'Claude integrado en Cortex AI','supply'],
  ['QuantumMachines','IBMQuantum',1,'Electrónica de control de qubits','supply'],
  ['QuantumMachines','Rigetti',2,'Controladores OPX','supply'],
  ['QuantumMachines','PsiQuantum',1,'Orquestación de qubits fotónicos','supply'],
  ['QuantumMachines','Pasqal',2,'Control de átomos neutros','supply'],
  ['Bluefors','Quantinuum',2,'Criogenia para trampas de iones','supply'],
  ['OxfordInstruments','Quantinuum',1,'Instrumentación criogénica','supply'],
  ['FormFactor','IBMQuantum',1,'Probes criogénicos','supply'],
  ['FormFactor','Rigetti',1,'Test criogénico de QPUs','supply'],
  ['FormFactor','TSMC',2,'Probe cards para test de obleas','supply'],
  ['Quantinuum','Microsoft',2,'Qubits lógicos con Azure Quantum','cloud'],
  ['Pasqal','Microsoft',1,'Acceso vía Azure Quantum','cloud'],
  ['Disco','SKHynix',3,'Sierras y rectificado para apilar HBM','supply'],
  ['Disco','TSMC',2,'Dicing de obleas','supply'],
  ['Disco','Micron',2,'Thinning para HBM','supply'],
  ['Screen','TSMC',2,'Limpieza de obleas','supply'],
  ['Screen','Samsung',2,'Equipos de limpieza húmeda','license'],
  ['Screen','SMIC',1,'Equipos de nodos maduros','supply'],
  ['Naura','SMIC',3,'Equipamiento doméstico chino','supply'],
  ['Naura','YMTC',2,'Deposición y grabado para NAND','supply'],
  ['AMEC','SMIC',3,'Grabado por plasma chino','supply'],
  ['AMEC','YMTC',2,'Grabado para NAND 3D','supply'],
  ['Hoya','TSMC',2,'Mask blanks EUV','supply'],
  ['Hoya','Samsung',2,'Sustratos de fotomáscara','supply'],
  ['Teradyne','TSMC',2,'Testers de producción','supply'],
  ['Teradyne','Micron',2,'Test de memoria','supply'],
  ['Teradyne','Qualcomm',2,'Test de SoCs','supply'],
  ['Besi','TSMC',3,'Hybrid bonding para chiplets/SoIC','supply'],
  ['Besi','SKHynix',2,'Bonding para HBM4','supply'],
  ['Besi','Intel',1,'Empaquetado avanzado Foveros','supply'],
  ['TexasInstruments','Dell',1,'Analógicos de gestión en servidores','supply'],
  ['TexasInstruments','Tesla',1,'Chips analógicos automotrices','supply'],
  ['TexasInstruments','Foxconn',1,'Componentes para ensamblaje','supply'],
  ['Infineon','Vertiv',2,'Módulos de potencia SiC','supply'],
  ['Infineon','Tesla',2,'SiC para inversores','supply'],
  ['Infineon','DeltaElectronics',2,'Semiconductores de potencia','supply'],
  ['onsemi','Tesla',2,'SiC para tracción','supply'],
  ['onsemi','Vertiv',1,'Potencia para infraestructura DC','supply'],
  ['SMIC','HiSilicon',4,'Fabrica los Ascend 910C en 7nm','fab'],
  ['SMIC','Cambricon',3,'Foundry doméstica de aceleradores','supply'],
  ['HiSilicon','DeepSeek',3,'Clústeres Ascend para entrenar','supply'],
  ['HiSilicon','Qwen',2,'Cómputo Ascend para Alibaba','supply'],
  ['Cambricon','DeepSeek',1,'Aceleradores alternativos','supply'],
  ['Cambricon','Qwen',2,'Inferencia doméstica china','supply'],
  ['YMTC','HiSilicon',2,'NAND china para Huawei','supply'],
  ['YMTC','Lenovo',1,'Memoria flash doméstica','supply'],
  ['Qwen','Unitree',1,'Modelos open-weight para robots','supply'],
  ['Lumentum','Nvidia',2,'Láseres para co-packaged optics','supply'],
  ['Lumentum','Cisco',2,'Componentes ópticos','supply'],
  ['Innolight','Nvidia',3,'Transceptores 800G/1.6T','supply'],
  ['Innolight','Alphabet',2,'Óptica para Google Cloud','cloud'],
  ['Innolight','Meta',2,'Transceptores para clústeres IA','supply'],
  ['Marvell','Innolight',2,'DSPs para sus módulos ópticos','supply'],
  ['Ciena','Microsoft',2,'DWDM para interconexión de DCs','cloud'],
  ['Ciena','Lumen',2,'Equipos ópticos de larga distancia','supply'],
  ['Ciena','Meta',1,'Interconexión entre regiones','supply'],
  ['Amphenol','Nvidia',2,'Conectores y backplanes de rack','supply'],
  ['Amphenol','Dell',2,'Cableado de alta velocidad','cloud'],
  ['Amphenol','Foxconn',1,'Conectores para ensamblaje','supply'],
  ['Corning','Lumen',3,'La fibra física de las rutas PCF','supply'],
  ['Corning','SubCom',2,'Fibra para cables submarinos','supply'],
  ['Corning','ASN',1,'Fibra óptica de ultra-baja pérdida','supply'],
  ['GEVernova','Microsoft',2,'Turbinas de gas y equipos de red','cloud'],
  ['GEVernova','Amazon',2,'Generación para campus de AWS','cloud'],
  ['GEVernova','Oracle',2,'Energía para Stargate','cloud'],
  ['Constellation','Microsoft',3,'PPA nuclear 20 años (Crane/TMI)','cloud'],
  ['Constellation','Meta',2,'PPA nuclear (Clinton)','supply'],
  ['SiemensEnergy','Amazon',2,'HVDC y transformadores','cloud'],
  ['SiemensEnergy','Equinix',2,'Infraestructura eléctrica','cloud'],
  ['DeltaElectronics','Foxconn',2,'Fuentes de poder para racks','supply'],
  ['DeltaElectronics','Quanta',2,'Power shelves GB300','supply'],
  ['DeltaElectronics','Dell',1,'Módulos de potencia','supply'],
  ['Nvidia','Quanta',3,'GPUs para servidores ODM','supply'],
  ['Nvidia','Celestica',2,'GPUs para sistemas hyperscale','supply'],
  ['Nvidia','Jabil',2,'GPUs para racks de IA','supply'],
  ['Quanta','Meta',3,'Servidores ODM para sus DCs','supply'],
  ['Quanta','Microsoft',2,'Servidores cloud directos','cloud'],
  ['Quanta','Amazon',2,'Hardware ODM para AWS','cloud'],
  ['Celestica','Alphabet',2,'Switches y servidores 800G','cloud'],
  ['Celestica','Amazon',2,'Sistemas de red para AWS','cloud'],
  ['Jabil','Amazon',1,'Manufactura de infraestructura','cloud'],
  ['Jabil','CoreWeave',1,'Racks de IA en EE.UU.','cloud'],
  ['Equinix','Oracle',2,'Colocación e interconexión','cloud'],
  ['Equinix','CoreWeave',2,'Espacio de data center','cloud'],
  ['Equinix','Microsoft',1,'Puntos de interconexión','cloud'],
  ['DigitalRealty','Microsoft',2,'Capacidad de data center','cloud'],
  ['DigitalRealty','Amazon',2,'Campus arrendados','cloud'],
  ['DigitalRealty','Nebius',1,'Espacio para el neocloud','cloud'],
  ['Nvidia','Unitree',2,'Jetson para humanoides G1/H2','supply'],
  ['Nvidia','Apptronik',2,'Cómputo embarcado para Apollo','supply'],
  ['Alphabet','Apptronik',2,'Inversor (Google) y modelos Gemini','cloud'],
  ['IBMQuantum','QuantumMachines',2,'Usa controladores OPX para orquestar sus qubits','supply'],
  ['IBMQuantum','Microsoft',2,'Acceso a QPUs IBM vía Azure Quantum','cloud'],
  ['IBMQuantum','Amazon',1,'Acceso a QPUs IBM vía AWS Braket','cloud'],
  ['IBMQuantum','Alphabet',1,'Integración Google Cloud Quantum Computing Service','cloud'],
  ['PsiQuantum','GF',4,'GlobalFoundries fabrica sus chips fotónicos cuánticos en CMOS','fab'],
  ['PsiQuantum','Microsoft',2,'Colaboración en simulación cuántica y acceso nube','cloud'],
  ['IBMQuantum','Rapidus',3,'Tecnología de proceso 2nm bajo licencia de IBM Research','license'],
  ['Rapidus','AMAT',2,'Equipos de deposición y CMP para la fab de Chitose','supply'],
  ['Rapidus','TEL',2,'Pistas fotorresistencia para proceso EUV en Chitose','fab'],
  ['xAI','Nvidia',5,'Colossus Memphis: 200K GPUs H100/H200 — mayor clúster IA privado','supply'],
  ['xAI','Oracle',3,'Infraestructura cloud OCI para entrenamiento Grok','cloud'],
  ['xAI','SuperMicro',3,'Servidores de rack para clúster Colossus','supply'],
  ['xAI','Tesla',2,'Implementa Grok en los vehículos y la plataforma de Tesla','supply'],
  ['xAI','Dell',2,'Servidores PowerEdge para edge inference de Grok','supply'],
  ['Mistral','Microsoft',3,'Acuerdo Azure: los modelos Mistral corren en Azure AI Studio','cloud'],
  ['Mistral','Amazon',2,'Modelos Mistral disponibles en Amazon Bedrock','cloud'],
  ['Mistral','Nvidia',2,'Entrenamiento en clusters H100/H200 para Mistral Large 2','supply'],
  ['Meta','Nvidia',5,'Mayor comprador individual de H100/H200: >600K GPUs en 2024–25','supply'],
  ['Meta','TSMC',4,'Fabrica sus ASICs MTIA (Meta Training & Inference Accelerator)','fab'],
  ['Meta','Broadcom',3,'Co-desarrollo del ASIC MTIA2 para inferencia IA a escala','supply'],
  ['Meta','Amazon',2,'Usa AWS para algunos workloads de datos y redundancia','cloud'],
  ['Meta','Equinix',2,'Interconexión en datacenters Equinix para backbone global','cloud'],
  ['DeepSeek','Nvidia',3,'Entrenamiento en H800/H100 antes de restricciones; ahora H20','supply'],
  ['DeepSeek','HiSilicon',3,'Migración a chips Ascend 910B de Huawei ante sanciones EE.UU.','supply'],
  ['DeepSeek','SMIC',2,'Dependencia indirecta de SMIC para chips Ascend de HiSilicon','supply'],
  ['Tesla','TSMC',4,'Fabrica los chips Dojo D1, HW4 y FSD en TSMC 7nm/5nm','fab'],
  ['Tesla','Samsung',2,'Produce chips FSD en nodos maduros Samsung (secundario)','supply'],
  ['Tesla','Nvidia',2,'Usa GPUs Nvidia para entrenamiento de modelos FSD (pre-Dojo)','supply'],
  ['Tesla','onsemi',3,'Mayor cliente de onsemi en SiC para inversores del tren eléctrico','supply'],
  ['Tesla','Broadcom',2,'Chipsets de red y conectividad para los vehículos Tesla','supply'],
  ['Figure','Nvidia',3,'OpenRobotics: procesador IA Jetson Thor para cerebro del robot 02','supply'],
  ['Figure','Microsoft',2,'Partnership estratégico y acceso a Azure OpenAI para Figure 02','license'],
  ['Figure','OpenAI',3,'Integración de GPT-4o para razonamiento del robot Figure 02','supply'],
  ['BostonDynamics','Nvidia',3,'Spot y Atlas usan módulos Jetson para percepción IA en campo','supply'],
  ['BostonDynamics','Amazon',2,'Piloto de Stretch en centros logísticos de Amazon','cloud'],
  ['OneX','Nvidia',2,'Plataforma Jetson para procesamiento visual de NEO Gamma','supply'],
  ['OneX','Amazon',1,'Piloto industrial en almacenes Amazon Europa','cloud'],
  ['Unitree','HiSilicon',3,'Módulos Ascend 310 de Huawei en robots G1/H1 para visión IA','supply'],
  ['Unitree','Nvidia',2,'Usa Jetson AGX Orin en modelos premium para mercado internacional','supply'],
  ['Unitree','SMIC',2,'Dependencia indirecta chips domésticos vía Huawei','supply'],
  ['Apptronik','Nvidia',3,'Plataforma Jetson Thor para el sistema nervioso IA de Apollo','supply'],
  ['Apptronik','Amazon',2,'Piloto de robots Apollo en centros de fulfillment de Amazon','cloud'],
  ['Apptronik','Alphabet',1,'Google como inversor estratégico y cliente piloto de Apollo','cloud'],
  ['Palantir','Amazon',3,'AIP corre sobre AWS — mayor proveedor de infra de Palantir','license'],
  ['Palantir','Microsoft',3,'AIP disponible en Azure; contrato MSFT US Gov (JEDI/JWCC)','license'],
  ['Palantir','Oracle',2,'Implementaciones AIP sobre OCI para clientes gubernamentales','license'],
  ['Palantir','Dell',2,'Dispositivos edge (MetaConstellation) con hardware Dell PowerEdge','supply'],
  ['CrowdStrike','Amazon',3,'Falcon corre en AWS — infraestructura primaria de CrowdStrike','cloud'],
  ['CrowdStrike','Microsoft',2,'Integración profunda con Azure Sentinel y Microsoft 365 Defender','cloud'],
  ['CrowdStrike','Nvidia',1,'Usa GPUs Nvidia para detección de amenazas con IA en tiempo real','supply'],
  ['Snowflake','Amazon',4,'~60% de la infra Snowflake corre sobre AWS (multirregión)','cloud'],
  ['Snowflake','Microsoft',3,'Snowflake sobre Azure — segunda nube más grande de su mix','cloud'],
  ['Snowflake','Alphabet',2,'Snowflake sobre Google Cloud — tercer proveedor del mix','cloud'],
  ['Snowflake','Nvidia',2,'Snowflake Cortex AI usa GPUs Nvidia para modelos in-database','supply'],
  ['Microsoft','OpenAI',5,'Inversión acumulada $13B — Azure es el único cloud de OpenAI','invest'],
  ['Amazon','Anthropic',4,'Inversión $4B — AWS es la nube primaria de Anthropic (Bedrock)','invest'],
  ['Alphabet','Anthropic',3,'Inversión $500M — Google Cloud como nube alternativa de Anthropic','invest'],
  ['Nvidia','CoreWeave',4,'Financiación masiva + suministro de 100K+ GPUs en 2023','invest'],
  ['OpenAI','Microsoft',5,'GPT-4/o1 corre exclusivamente en Azure (Microsoft es el único proveedor cloud)','cloud'],
  ['OpenAI','Nvidia',4,'ChatGPT usa clusters de H100/H200 para inferencia a 100M+ usuarios','supply'],
  ['Anthropic','Amazon',5,'Claude corre en AWS Bedrock — Amazon es el socio cloud primario','cloud'],
  ['Anthropic','Alphabet',2,'Claude disponible en Google Cloud Vertex AI como segunda nube','cloud'],
  ['Anthropic','Nvidia',3,'Entrenamiento de Claude 3/4 en clusters H100 a gran escala','supply'],
  ['Qwen','Nvidia',3,'Alibaba usa clusters H800/H20 para entrenamiento Qwen 2.5/3','supply'],
  ['Qwen','TSMC',2,'Alibaba fabrica ASICs Hanguang 800 para inferencia en TSMC','fab'],
  ['Qwen','SMIC',2,'Alternativa chips domésticos vía SMIC para reducir dependencia','supply'],
  ['Arista','Microsoft',3,'Switches 400/800G para la red interna de Azure DC','cloud'],
  ['Arista','Alphabet',3,'Switches de red para centros de datos de Google','cloud'],
  ['Arista','Amazon',3,'Infraestructura de red para la red interna de AWS','cloud'],
  ['Arista','Meta',3,'Switches 400G para red fabric interna de Meta AI','supply'],
  ['Coherent','Microsoft',3,'Transceptores 400G/800G para interconexión Azure DC','cloud'],
  ['Coherent','Amazon',3,'Módulos ópticos para la red global AWS','cloud'],
  ['Coherent','Alphabet',2,'Transceptores para Google Cloud interconnect','cloud'],
  ['Astera','Nvidia',3,'Retimers PCIe 6.0 críticos para los NVL72 racks Blackwell','supply'],
  ['Astera','Microsoft',2,'Chips de interfaz para los racks IA de Azure','cloud'],
  ['Constellation','Microsoft',4,'Acuerdo PPA nuclear 20 años: Crane Clean Energy Center para Azure','cloud'],
  ['Constellation','Amazon',2,'PPAs de energía nuclear y eólica para centros AWS','cloud'],
  ['Constellation','Alphabet',2,'PPAs de energía limpia para Google Cloud','cloud'],
  ['GEVernova','Amazon',3,'Transformadores y UPS de alta potencia para centros AWS','cloud'],
  ['GEVernova','Microsoft',3,'Infraestructura eléctrica para la expansión masiva de Azure','cloud'],
  ['Vertiv','Nvidia',3,'Sistemas de cooling líquido para racks DGX GB200 NVL72','supply'],
  ['Vertiv','Microsoft',3,'UPS y gestión térmica para centros de datos Azure','cloud'],
  ['Vertiv','Alphabet',3,'Infraestructura de potencia y cooling para Google Cloud','cloud'],
  ['MPWR','Nvidia',3,'Módulos de regulación de potencia para GPUs H100/B200 Blackwell','supply'],
  ['MPWR','Dell',2,'VRMs para servidores PowerEdge con GPUs Nvidia','supply'],
  ['SKHynix','Nvidia',5,'Proveedor exclusivo HBM3e para H100/H200/B200 — monopolio de facto','supply'],
  ['SKHynix','Microsoft',2,'HBM para Maia 100 (ASIC Azure IA)','cloud'],
  ['Micron','Amazon',3,'HBM3e y DRAM para servidores AWS Trainium/Inferentia','cloud'],
  ['Micron','Microsoft',2,'DRAM y almacenamiento para servidores Azure','cloud'],
  ['TSMC','Nvidia',6,'Fabrica TODOS los chips Blackwell/Hopper en N4P/N3E — relación exclusiva','fab'],
  ['TSMC','AMD',5,'Fabrica Instinct MI300X, EPYC Turin en N3/N4 — cliente 2º por volumen','fab'],
  ['TSMC','Apple',5,'Fabrica A18/M4 Pro en N3E — Apple es el 1º cliente por ingresos','fab'],
  ['Samsung','SKHynix',2,'Compite en DRAM/NAND — referencia de proceso para HBM4','fab'],
  ['GF','ARM',1,'GlobalFoundries usa arquitectura ARM en nodos maduros FD-SOI','license'],
  ['Corning','SubCom',3,'Fibra óptica para cables submarinos de SubCom','supply'],
  ['Corning','NEC',2,'Fibra óptica para sistemas de cable submarino de NEC','supply'],
  ['SubCom','Amazon',3,'Instala cables submarinos para la red global AWS (p.ej. CURIE)','cloud'],
  ['SubCom','Alphabet',4,'Mayor cliente: cables Dunant, Grace Hopper, Firmina para Google','cloud'],
  ['SubCom','Microsoft',2,'Cables MAREA y Echo para interconexión global Azure','cloud'],
  ['NEC','Amazon',2,'Cable JIMBI y otros para conectar regiones AWS Pacífico','cloud'],
  ['SuperMicro','Nvidia',3,'SuperMicro ensamble sistemas DGX/HGX para clusters IA','supply'],
  ['SuperMicro','CoreWeave',4,'Principal proveedor de racks para los clusters de CoreWeave','cloud'],
  ['Quanta','Alphabet',3,'Diseña servidores OCP custom para datacenters Google','cloud'],
  ['Quanta','Meta',2,'Servidores custom OCP para Meta AI clusters','supply'],
  ['Celestica','Cisco',3,'Manufacturing de switches y routers para Cisco','fab'],
  ['Foxconn','Nvidia',3,'Ensambla servidores GB200/H100 para los mayores clientes de Nvidia','supply'],
  ['Dell','Nvidia',3,'Distribuidor oficial de sistemas DGX B200; mayor canal empresarial','supply'],
  ['HPE','Nvidia',3,'HPE Cray EX con GPUs Nvidia para HPC y IA (Oak Ridge, etc.)','supply'],
  ['OpenAI','Anthropic',1,'Competencia directa en modelos frontier — ex-empleados de OpenAI fundaron Anthropic','partner'],
  ['Meta','OpenAI',1,'Competencia directa; Meta ofrece Llama como open source frente a OpenAI','partner'],
  ['Mistral','OpenAI',1,'Competencia directa europea; modelos open-weights frente a GPT-4','partner'],
  ['Tesla','OpenAI',1,'Elon Musk co-fundó OpenAI; ahora competidores directos','supply'],
  ['Figure','OpenAI',2,'Figure integra modelos multimodales de OpenAI en Figure 02','supply'],
  ['BostonDynamics','OpenAI',1,'Boston Dynamics usa GPT-4V para comprensión semántica de entornos','supply'],
  ['Microsoft','Anthropic',2,'Microsoft invierte adicionalmente en Anthropic; Claude en Copilot','invest'],
  ['Oracle','OpenAI',2,'OpenAI acuerdo multi-cloud OCI para capacidad adicional de inferencia','cloud'],

  /* ===== v7 · M1: despliegues (deploy) ===== */
  ['Unitree','SAIC',2,'Despliega robots G1 en línea de producción de SAIC (fabrica ~5M coches/año)','deploy'],
  ['BostonDynamics','Hyundai',3,'Atlas y Spot desplegados en la Metaplant de Hyundai en Georgia para logística y ensamblaje','deploy'],
  ['Figure','BMW',3,'Robots Figure 02 desplegados en planta BMW Spartanburg — primer cliente industrial','deploy'],
  ['BostonDynamics','Amazon',3,'Stretch desplegado en 12 centros de fulfillment Amazon para paletizado','deploy'],
  ['Apptronik','Amazon',2,'Apollo en piloto en centros de fulfillment Amazon GXO','deploy'],
  ['Palantir','Dell',2,'AIP Edge desplegado en dispositivos MetaConstellation con hardware Dell PowerEdge','deploy'],
  ['CrowdStrike','Dell',3,'Falcon desplegado como EDR estándar en todos los endpoints Dell Technologies','deploy'],
  ['Snowflake','Nvidia',2,'Snowflake Cortex AI desplegado como capa analítica sobre clusters GPU de Nvidia','deploy'],
  ['Microsoft','OpenAI',3,'Copilot desplegado en suite M365 de 400M+ usuarios enterprise','deploy'],
  ['OpenAI','Microsoft',2,'ChatGPT Enterprise desplegado en stack IT de Fortune 500 vía Microsoft','deploy'],
  ['Palantir','Amazon',3,'AIP desplegado sobre infraestructura AWS para contratos DoD y CIA','deploy'],
  ['CrowdStrike','Microsoft',3,'Falcon integrado como XDR nativo en Azure Sentinel y Microsoft 365 Defender','deploy'],
  ['Snowflake','Amazon',2,'Data Cloud desplegado en producción sobre infraestructura AWS multi-región','deploy'],
  ['Figure','Microsoft',2,'Figure 02 con OpenAI integrado desplegado en pilotos Microsoft manufacturing','deploy'],
  ['BostonDynamics','Alphabet',1,'Spot desplegado en campus de Google para inspección de infraestructura','deploy'],

  /* ===== v7 · M1: inversiones (invest) ===== */
  ['SoftBank','ARM',5,'SoftBank propietario del ~90% de ARM tras adquisición 2016 por $32B','invest'],
  ['Samsung','QuantumMachines',2,'Samsung invierte en ronda Series B de QuantumMachines','invest'],
  ['Intel','IonQ',2,'Intel Capital invirtió en IonQ antes de su salida a bolsa vía SPAC','invest'],
  ['Alphabet','IonQ',2,'Google invierte en IonQ como parte de su estrategia cuántica','invest'],
  ['Hyundai','BostonDynamics',4,'Hyundai adquirió Boston Dynamics en 2021 por $1.1B — propietario mayoritario','invest'],
  ['Microsoft','Figure',3,'Microsoft lideró ronda $675M en Figure AI (enero 2024)','invest'],
  ['Samsung','Figure',2,'Samsung invirtió en la ronda $675M de Figure AI','invest'],
  ['Amazon','Figure',2,'Amazon invirtió en la ronda $675M de Figure AI','invest'],
  ['BMW','Figure',2,'BMW invierte y es cliente: piloto en Spartanburg tras la ronda','invest'],
  ['SoftBank','Nvidia',2,'SoftBank históricamente uno de los mayores accionistas de Nvidia vía fondos Vision','invest'],
  ['SoftBank','OpenAI',5,'SoftBank lidera la ronda de $40B en OpenAI (2025) y el proyecto Stargate','invest'],
  ['Nvidia','PsiQuantum',2,'Nvidia entre los inversores de la ronda de $1B+ de PsiQuantum (2025)','invest'],

  /* ===== v7 · M1: partnerships (partner) ===== */
  ['ARM','TSMC',4,'PDK optimizado para cada nodo TSMC (N3, N2) — ARM como IP preferente de TSMC','partner'],
  ['ARM','Samsung',3,'Exynos basado en arquitectura ARM v9 — acuerdo de proceso preferencial','partner'],
  ['Synopsys','TSMC',4,'Reference flow N3/N2: Synopsys entrega el flujo EDA certificado para TSMC','partner'],
  ['Cadence','Samsung',3,'SF3 EDA Flow: Cadence certified para proceso Samsung Foundry SF3','partner'],
  ['ASML','Intel',4,'Co-desarrollo High-NA EUV (0.55 NA) — Intel es el primer cliente de High-NA','partner'],
  ['IBMQuantum','Samsung',3,'IBM y Samsung co-investigan nodo SF2 y dispositivos GAA de próxima generación','partner'],
  ['Dell','Nvidia',4,'Dell DGX-Ready Program — reseller oficial certificado de sistemas DGX/HGX','partner'],
  ['HPE','Nvidia',4,'HPE Cray EX con módulos Nvidia GH200 para supercomputadoras HPC e IA','partner'],
  ['CoreWeave','Microsoft',4,'GPU cloud dedicada a Microsoft: 23,000+ GPUs H100 reservados para Azure AI','partner'],
  ['Nebius','Nvidia',3,'Nebius como cloud partner exclusivo de Nvidia en Europa — GPU clusters H100/H200','partner'],

  /* ===== v7 · M8: links de los nuevos nodos ===== */
  ['SMIC','Huawei',4,'SMIC fabrica chips Kirin y Ascend 910B para Huawei en 7nm sin EUV','fab'],
  ['HiSilicon','Huawei',5,'HiSilicon es la división de diseño de chips de Huawei — relación matriz-filial','supply'],
  ['YMTC','Huawei',3,'YMTC suministra NAND flash para smartphones y SSD Huawei','supply'],
  ['Huawei','DeepSeek',3,'Huawei suministra hardware Ascend 910B para entrenar y servir modelos DeepSeek','supply'],
  ['Huawei','Unitree',2,'Unitree usa módulos Ascend de Huawei en sus robots G1/H1 para IA visual','supply'],
  ['TSMC','MediaTek',5,'TSMC fabrica chips Dimensity en N4/N3 para MediaTek','fab'],
  ['ARM','MediaTek',4,'MediaTek licencia arquitectura ARM v9 para todos sus cores CPU','license'],
  ['Synopsys','MediaTek',2,'MediaTek usa herramientas EDA Synopsys para diseño de Dimensity','license'],
  ['MediaTek','Samsung',3,'Samsung usa chips Dimensity en gama media Galaxy A serie','supply'],
  ['MediaTek','Xiaomi',3,'Xiaomi usa Dimensity 9300/9400 en modelos premium y mid-range','supply'],
  ['TSMC','Groq',4,'TSMC fabrica el LPU GroqChip en proceso 14nm','fab'],
  ['Synopsys','Groq',2,'Groq usa herramientas EDA Synopsys para diseño del LPU','license'],
  ['Amazon','Groq',2,'GroqCloud disponible como opción de inferencia en AWS Marketplace','cloud'],
  ['Groq','OpenAI',1,'Groq compite directamente con OpenAI en inference serving — más rápido en tokens/s','partner'],
  ['Groq','Microsoft',1,'Groq disponible en Azure AI Studio como inferencia alternativa','cloud'],
  ['TSMC','SambaNova',3,'TSMC fabrica el chip RDU de SambaNova en 7nm','fab'],
  ['Amazon','SambaNova',2,'SambaNova disponible vía AWS Marketplace para enterprise','cloud'],
  ['Alphabet','SambaNova',1,'SambaNova y Google colaboran en benchmarks de inferencia','partner'],
  ['SambaNova','Microsoft',2,'SambaNova Suite disponible en Azure para clientes enterprise regulados','cloud'],
  ['SambaNova','Amazon',1,'SambaNova en AWS GovCloud para clientes de defensa','cloud'],
  ['TSMC','WesternDigital',1,'TSMC fabrica controladores SSD de Western Digital','fab'],
  ['Lam','WesternDigital',2,'Lam equipa las fábricas de NAND de Western Digital','supply'],
  ['AMAT','WesternDigital',2,'AMAT provee equipos de deposición para fábricas NAND de WD','supply'],
  ['WesternDigital','Amazon',3,'WD Gold HDDs y SSDs enterprise usados masivamente en datacenters AWS','supply'],
  ['WesternDigital','Microsoft',2,'WD enterprise storage en servidores Azure y backup','supply'],
  ['SKHynix','Naver',2,'SK Hynix suministra HBM y DRAM para los servidores de Naver Cloud','supply'],
  ['Samsung','Naver',3,'Samsung fabrica ASICs y suministra DRAM/NAND para NAVER Cloud','supply'],
  ['Nvidia','Naver',3,'Naver usa GPUs H100 para entrenamiento de HyperCLOVA X','supply'],
  ['Naver','Samsung',2,'Naver Cloud es plataforma preferida para Samsung en Corea','cloud'],
  ['Naver','Alphabet',1,'Naver compite con Google en búsqueda coreana — también colabora en APIs','partner'],

  /* ===== v7 · nodos de soporte: conexiones adicionales ===== */
  ['Qualcomm','Xiaomi',3,'Snapdragon 8 Elite en los buques insignia de Xiaomi','supply'],
  ['Xiaomi','Unitree',1,'Xiaomi y Unitree compiten en robótica de consumo china — CyberDog frente a Go2','partner']
];

const SHARES_OUTSTANDING_B = {
  'NVDA': 24.5, 'MSFT': 7.44, 'AAPL': 15.0, 'GOOGL': 12.1, 'AMZN': 10.7, 'META': 2.53,
  'ORCL': 2.76, 'CRWV': 1.0,
  'AVGO': 4.73, 'AMD': 1.62, 'INTC': 4.25, 'QCOM': 1.12, 'ARM': 1.05,
  'TSM': 5.18, 'ASML': 0.395,
  'MU': 1.11,
  'LRCX': 1.38, 'KLAC': 1.40, 'AMAT': 8.55, 'ANET': 3.1,
  'VRT': 3.84, 'MPWR': 0.047, 'ETN': 4.0, 'GEV': 1.37, 'CEG': 0.32,
  'DELL': 1.33, 'HPE': 1.28,
  'RKLB': 4.5, 'ASTS': 2.3, 'IRDM': 0.135, 'GSAT': 1.9, 'PL': 0.25,
  'VSAT': 0.145, 'BKSY': 0.075,
  'CSCO': 4.06,
  'NOC': 0.153, 'LHX': 0.19, 'RTX': 1.34, 'GD': 0.28, 'KTOS': 0.18, 'PLTR': 2.1,
  'MBLY': 0.42, 'AUR': 1.68, 'LAZR': 0.36,
  'HXL': 0.121, 'ATI': 0.15, 'CRS': 0.043, 'MP': 0.17,
  'ALB': 0.117, 'SQM': 0.28,
  'TEM': 0.18, 'RXRX': 0.22,
  'MSCI': 0.08, 'PENG': 0.07,
  'MXL': 0.075, 'SITS': 0.014,
  'TMUS': 1.19, 'MOG': 0.045, 'PH': 1.28,
};

const NODE_META = {
  "IBMQuantum": {
    "founded": 2016,
    "employees": 3000,
    "revenue_2025": "div. ~$200M",
    "mktcap_b": "div. IBM",
    "risk": "medium",
    "geo_risk": "Regulación EE.UU. limita exportación a China",
    "key_clients": [
      "Mitsubishi UFJ",
      "Cleveland Clinic",
      "Argonne Lab"
    ]
  },
  "Rigetti": {
    "founded": 2013,
    "employees": 230,
    "revenue_2025": "~$15M",
    "mktcap_b": 0.7,
    "risk": "high",
    "geo_risk": "Fab propia en EE.UU.",
    "key_clients": [
      "DARPA",
      "AFRL",
      "Rigetti Cloud"
    ]
  },
  "IonQ": {
    "founded": 2015,
    "employees": 400,
    "revenue_2025": "~$50M",
    "mktcap_b": 4.0,
    "risk": "high",
    "geo_risk": "Sin restricciones hoy",
    "key_clients": [
      "AFRL",
      "Emirates Gov",
      "GE"
    ]
  },
  "PsiQuantum": {
    "founded": 2016,
    "employees": 350,
    "revenue_2025": "pre-rev",
    "mktcap_b": 7.0,
    "risk": "high",
    "geo_risk": "GF fab en EE.UU.",
    "key_clients": [
      "Australia Gov",
      "Illinois Gov",
      "DARPA"
    ]
  },
  "DWave": {
    "founded": 1999,
    "employees": 200,
    "revenue_2025": "~$30M",
    "mktcap_b": 0.9,
    "risk": "medium",
    "geo_risk": "Canadá — no sujeto a controles EE.UU.",
    "key_clients": [
      "Ford Otosan",
      "NTT Docomo",
      "Pattison Food"
    ]
  },
  "Quantinuum": {
    "founded": 2021,
    "employees": 500,
    "revenue_2025": "~$120M",
    "mktcap_b": 10.0,
    "risk": "medium",
    "geo_risk": "EE.UU. / Reino Unido",
    "key_clients": [
      "JPMorgan",
      "Honeywell",
      "Gov UK"
    ]
  },
  "Pasqal": {
    "founded": 2019,
    "employees": 280,
    "revenue_2025": "~€30M",
    "mktcap_b": 1.8,
    "risk": "high",
    "geo_risk": "Francia — apoyada UE",
    "key_clients": [
      "GENCI",
      "Jülich HPC",
      "Saudi Aramco"
    ]
  },
  "Bluefors": {
    "founded": 2008,
    "employees": 700,
    "revenue_2025": "~€130M",
    "mktcap_b": null,
    "risk": "low",
    "geo_risk": "Finlandia — sin restricciones",
    "key_clients": [
      "IBM",
      "Google",
      "Rigetti"
    ]
  },
  "OxfordInstruments": {
    "founded": 1959,
    "employees": 2200,
    "revenue_2025": "~£670M",
    "mktcap_b": 2.1,
    "risk": "low",
    "geo_risk": "UK — mínima",
    "key_clients": [
      "MIT",
      "IBM",
      "TSMC"
    ]
  },
  "QuantumMachines": {
    "founded": 2018,
    "employees": 200,
    "revenue_2025": "~$25M",
    "mktcap_b": null,
    "risk": "medium",
    "geo_risk": "Israel — geopolítica regional",
    "key_clients": [
      "IBM",
      "Google",
      "Pasqal"
    ]
  },
  "FormFactor": {
    "founded": 1993,
    "employees": 2900,
    "revenue_2025": "~$850M",
    "mktcap_b": 3.1,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "SK Hynix",
      "Micron",
      "Samsung"
    ]
  },
  "Synopsys": {
    "founded": 1986,
    "employees": 20000,
    "revenue_2025": "~$6.1B",
    "mktcap_b": 73.0,
    "risk": "low",
    "geo_risk": "Restricciones EDA China (EAR)",
    "key_clients": [
      "Nvidia",
      "Intel",
      "TSMC"
    ]
  },
  "Cadence": {
    "founded": 1988,
    "employees": 12800,
    "revenue_2025": "~$4.5B",
    "mktcap_b": 68.0,
    "risk": "low",
    "geo_risk": "Restricciones EDA China (EAR)",
    "key_clients": [
      "Apple",
      "Qualcomm",
      "Samsung"
    ]
  },
  "ARM": {
    "founded": 1990,
    "employees": 6800,
    "revenue_2025": "~$4.0B",
    "mktcap_b": 145.0,
    "risk": "low",
    "geo_risk": "Softbank propietario — riesgo Japón-China",
    "key_clients": [
      "Apple",
      "Qualcomm",
      "Nvidia"
    ]
  },
  "SiemensEDA": {
    "founded": 2017,
    "employees": 5000,
    "revenue_2025": "~$1.5B",
    "mktcap_b": null,
    "risk": "low",
    "geo_risk": "División de Siemens",
    "key_clients": [
      "Intel",
      "Broadcom",
      "Stellantis"
    ]
  },
  "Zeiss": {
    "founded": 1846,
    "employees": 43000,
    "revenue_2025": "~€10B (grupo)",
    "mktcap_b": null,
    "risk": "low",
    "geo_risk": "División SMT — monopolio sin restricciones",
    "key_clients": [
      "ASML (exclusivo)"
    ]
  },
  "Trumpf": {
    "founded": 1923,
    "employees": 18500,
    "revenue_2025": "~€5.6B",
    "mktcap_b": null,
    "risk": "low",
    "geo_risk": "Familiar — sin cotización",
    "key_clients": [
      "ASML (exclusivo)"
    ]
  },
  "MitsuiChemicals": {
    "founded": 1955,
    "employees": 15000,
    "revenue_2025": "~¥1.7T",
    "mktcap_b": 5.5,
    "risk": "low",
    "geo_risk": "Japón — aliada EE.UU.",
    "key_clients": [
      "ASML",
      "TSMC",
      "Samsung"
    ]
  },
  "Toto": {
    "founded": 1917,
    "employees": 33000,
    "revenue_2025": "~¥700B",
    "mktcap_b": 4.0,
    "risk": "low",
    "geo_risk": "Japón — aliada EE.UU.",
    "key_clients": [
      "Lam",
      "AMAT",
      "TEL"
    ]
  },
  "Hoya": {
    "founded": 1941,
    "employees": 37000,
    "revenue_2025": "~¥840B",
    "mktcap_b": 22.0,
    "risk": "low",
    "geo_risk": "Japón — aliada EE.UU.",
    "key_clients": [
      "ASML",
      "TSMC",
      "Intel"
    ]
  },
  "ASML": {
    "founded": 1984,
    "employees": 42000,
    "revenue_2025": "~€28B",
    "mktcap_b": 270.0,
    "risk": "medium",
    "geo_risk": "Controles exportación China (máximo riesgo político)",
    "key_clients": [
      "TSMC",
      "Samsung",
      "Intel"
    ]
  },
  "AMAT": {
    "founded": 1967,
    "employees": 35000,
    "revenue_2025": "~$28B",
    "mktcap_b": 155.0,
    "risk": "medium",
    "geo_risk": "~30% ventas China bajo controles EAR",
    "key_clients": [
      "TSMC",
      "Samsung",
      "SK Hynix"
    ]
  },
  "Lam": {
    "founded": 1980,
    "employees": 18000,
    "revenue_2025": "~$16B",
    "mktcap_b": 95.0,
    "risk": "medium",
    "geo_risk": "~30% China — controles EAR",
    "key_clients": [
      "SK Hynix",
      "TSMC",
      "Samsung"
    ]
  },
  "KLA": {
    "founded": 1975,
    "employees": 14500,
    "revenue_2025": "~$11B",
    "mktcap_b": 95.0,
    "risk": "medium",
    "geo_risk": "~30% China — controles EAR",
    "key_clients": [
      "TSMC",
      "Samsung",
      "Intel"
    ]
  },
  "TEL": {
    "founded": 1963,
    "employees": 16000,
    "revenue_2025": "~¥2.4T",
    "mktcap_b": 65.0,
    "risk": "medium",
    "geo_risk": "~40% China — sujeto a controles japoneses",
    "key_clients": [
      "TSMC",
      "Samsung",
      "SK Hynix"
    ]
  },
  "ASMInt": {
    "founded": 1968,
    "employees": 4300,
    "revenue_2025": "~€3.2B",
    "mktcap_b": 24.0,
    "risk": "medium",
    "geo_risk": "Baja exposición China en ALD",
    "key_clients": [
      "TSMC",
      "Samsung",
      "Intel"
    ]
  },
  "Nikon": {
    "founded": 1917,
    "employees": 19000,
    "revenue_2025": "~¥350B",
    "mktcap_b": 5.0,
    "risk": "medium",
    "geo_risk": "~50% demanda China DUV",
    "key_clients": [
      "SMIC",
      "CXMT",
      "Hua Hong"
    ]
  },
  "Canon": {
    "founded": 1937,
    "employees": 180000,
    "revenue_2025": "~¥4.2T",
    "mktcap_b": 32.0,
    "risk": "low",
    "geo_risk": "Grupo diversificado",
    "key_clients": [
      "Kioxia",
      "SMIC",
      "GlobalWafers"
    ]
  },
  "Disco": {
    "founded": 1937,
    "employees": 5400,
    "revenue_2025": "~¥180B",
    "mktcap_b": 22.0,
    "risk": "low",
    "geo_risk": "~25% China — menor riesgo que Big 5",
    "key_clients": [
      "SK Hynix",
      "Samsung",
      "TSMC"
    ]
  },
  "Screen": {
    "founded": 1943,
    "employees": 9000,
    "revenue_2025": "~¥350B",
    "mktcap_b": 8.0,
    "risk": "medium",
    "geo_risk": "~35% China bajo presión regulatoria",
    "key_clients": [
      "TSMC",
      "SK Hynix",
      "Intel"
    ]
  },
  "Naura": {
    "founded": 2001,
    "employees": 8000,
    "revenue_2025": "~¥10B",
    "mktcap_b": 12.0,
    "risk": "high",
    "geo_risk": "Empresa china — sancionada/vigilada",
    "key_clients": [
      "SMIC",
      "YMTC",
      "CXMT"
    ]
  },
  "AMEC": {
    "founded": 2004,
    "employees": 3200,
    "revenue_2025": "~¥3B",
    "mktcap_b": 6.0,
    "risk": "high",
    "geo_risk": "Empresa china — vigilada EE.UU.",
    "key_clients": [
      "SMIC",
      "Hua Hong",
      "YMTC"
    ]
  },
  "ShinEtsu": {
    "founded": 1926,
    "employees": 40000,
    "revenue_2025": "~¥2.6T",
    "mktcap_b": 48.0,
    "risk": "low",
    "geo_risk": "Japón — aliada, líder 300mm",
    "key_clients": [
      "TSMC",
      "Samsung",
      "Intel"
    ]
  },
  "SUMCO": {
    "founded": 2002,
    "employees": 11000,
    "revenue_2025": "~¥350B",
    "mktcap_b": 4.5,
    "risk": "low",
    "geo_risk": "Japón — mínima",
    "key_clients": [
      "Samsung",
      "TSMC",
      "SK Hynix"
    ]
  },
  "Siltronic": {
    "founded": 1968,
    "employees": 4300,
    "revenue_2025": "~€1.4B",
    "mktcap_b": 1.8,
    "risk": "low",
    "geo_risk": "Alemania — bajo",
    "key_clients": [
      "Intel",
      "GlobalFoundries",
      "Infineon"
    ]
  },
  "GlobalWafers": {
    "founded": 2011,
    "employees": 11000,
    "revenue_2025": "~NT$90B",
    "mktcap_b": 5.0,
    "risk": "low",
    "geo_risk": "Taiwán — geopolítica latente",
    "key_clients": [
      "TSMC",
      "Samsung",
      "Intel"
    ]
  },
  "Ajinomoto": {
    "founded": 1909,
    "employees": 36000,
    "revenue_2025": "~¥1.7T",
    "mktcap_b": 12.0,
    "risk": "low",
    "geo_risk": "Japón — bajo",
    "key_clients": [
      "Intel",
      "TSMC",
      "Samsung"
    ]
  },
  "JSR": {
    "founded": 1957,
    "employees": 11000,
    "revenue_2025": "~¥280B",
    "mktcap_b": null,
    "risk": "low",
    "geo_risk": "Nacionalizado Japón 2023 — estratégico",
    "key_clients": [
      "TSMC",
      "Intel",
      "Samsung"
    ]
  },
  "Entegris": {
    "founded": 1966,
    "employees": 9700,
    "revenue_2025": "~$3.6B",
    "mktcap_b": 17.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "TSMC",
      "Intel",
      "Samsung"
    ]
  },
  "TokyoOhka": {
    "founded": 1936,
    "employees": 3800,
    "revenue_2025": "~¥180B",
    "mktcap_b": 3.5,
    "risk": "low",
    "geo_risk": "Japón — bajo",
    "key_clients": [
      "TSMC",
      "Samsung",
      "Intel"
    ]
  },
  "MerckKGaA": {
    "founded": 1668,
    "employees": 63000,
    "revenue_2025": "~€22B",
    "mktcap_b": 56.0,
    "risk": "low",
    "geo_risk": "Alemania — bajo",
    "key_clients": [
      "TSMC",
      "Samsung",
      "SK Hynix"
    ]
  },
  "Linde": {
    "founded": 1879,
    "employees": 42000,
    "revenue_2025": "~$33B",
    "mktcap_b": 215.0,
    "risk": "low",
    "geo_risk": "EE.UU./Alemania — bajo",
    "key_clients": [
      "TSMC",
      "Intel",
      "Samsung"
    ]
  },
  "AirLiquide": {
    "founded": 1902,
    "employees": 68000,
    "revenue_2025": "~€28B",
    "mktcap_b": 85.0,
    "risk": "low",
    "geo_risk": "Francia — bajo",
    "key_clients": [
      "Samsung",
      "SK Hynix",
      "GlobalFoundries"
    ]
  },
  "TSMC": {
    "founded": 1987,
    "employees": 75000,
    "revenue_2025": "~$105B",
    "mktcap_b": 1050.0,
    "risk": "high",
    "geo_risk": "RIESGO GEOPOLÍTICO MÁXIMO: Taiwán — China",
    "key_clients": [
      "Apple",
      "Nvidia",
      "AMD"
    ]
  },
  "Samsung": {
    "founded": 1969,
    "employees": 270000,
    "revenue_2025": "~$220B",
    "mktcap_b": 310.0,
    "risk": "medium",
    "geo_risk": "Corea — riesgo moderado NK",
    "key_clients": [
      "Apple (memoria)",
      "Qualcomm",
      "Google"
    ]
  },
  "Intel": {
    "founded": 1968,
    "employees": 120000,
    "revenue_2025": "~$54B",
    "mktcap_b": 115.0,
    "risk": "medium",
    "geo_risk": "EE.UU. — IDM bajo riesgo",
    "key_clients": [
      "Microsoft",
      "Dell",
      "HP"
    ]
  },
  "GF": {
    "founded": 2009,
    "employees": 15000,
    "revenue_2025": "~$7B",
    "mktcap_b": 25.0,
    "risk": "low",
    "geo_risk": "EE.UU./Malasya — favorecido por CHIPS Act",
    "key_clients": [
      "AMD",
      "Qualcomm",
      "AWS"
    ]
  },
  "SMIC": {
    "founded": 2000,
    "employees": 21000,
    "revenue_2025": "~$9B",
    "mktcap_b": 22.0,
    "risk": "critical",
    "geo_risk": "SANCIONADO por EE.UU. — sin acceso a EUV",
    "key_clients": [
      "HiSilicon",
      "Cambricon",
      "YMTC"
    ]
  },
  "Rapidus": {
    "founded": 2022,
    "employees": 800,
    "revenue_2025": "~$0",
    "mktcap_b": null,
    "risk": "high",
    "geo_risk": "Japón — proyecto soberano",
    "key_clients": [
      "Proyecto soberano 2nm 2027"
    ]
  },
  "TexasInstruments": {
    "founded": 1951,
    "employees": 34000,
    "revenue_2025": "~$17B",
    "mktcap_b": 185.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "Automoción",
      "Industrial",
      "Consumer"
    ]
  },
  "Infineon": {
    "founded": 1999,
    "employees": 58000,
    "revenue_2025": "~€16B",
    "mktcap_b": 28.0,
    "risk": "low",
    "geo_risk": "Alemania — bajo",
    "key_clients": [
      "Automoción",
      "Energía",
      "IoT"
    ]
  },
  "onsemi": {
    "founded": 1999,
    "employees": 33000,
    "revenue_2025": "~$7.5B",
    "mktcap_b": 17.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "Tesla",
      "Stellantis",
      "Onsemi EV"
    ]
  },
  "Nvidia": {
    "founded": 1993,
    "employees": 32000,
    "revenue_2025": "~$130B",
    "mktcap_b": 3200.0,
    "risk": "medium",
    "geo_risk": "Controles exportación China A100/H100",
    "key_clients": [
      "Microsoft",
      "Meta",
      "Google"
    ]
  },
  "AMD": {
    "founded": 1969,
    "employees": 25000,
    "revenue_2025": "~$27B",
    "mktcap_b": 250.0,
    "risk": "medium",
    "geo_risk": "Restricciones China (MI300)",
    "key_clients": [
      "Microsoft",
      "Meta",
      "Oracle"
    ]
  },
  "Qualcomm": {
    "founded": 1985,
    "employees": 51000,
    "revenue_2025": "~$44B",
    "mktcap_b": 175.0,
    "risk": "medium",
    "geo_risk": "~60% ventas China — riesgo alto",
    "key_clients": [
      "Samsung",
      "Apple",
      "Xiaomi"
    ]
  },
  "Apple": {
    "founded": 1976,
    "employees": 164000,
    "revenue_2025": "~$400B",
    "mktcap_b": 3700.0,
    "risk": "medium",
    "geo_risk": "~18% ventas China — iPhone China risk",
    "key_clients": [
      "Consumidor final"
    ]
  },
  "Cambricon": {
    "founded": 2016,
    "employees": 2800,
    "revenue_2025": "~¥1.2B",
    "mktcap_b": 8.0,
    "risk": "critical",
    "geo_risk": "China — sancionada",
    "key_clients": [
      "SMIC",
      "Lenovo China",
      "Gov China"
    ]
  },
  "HiSilicon": {
    "founded": 2004,
    "employees": 6000,
    "revenue_2025": "~$3B est",
    "mktcap_b": null,
    "risk": "critical",
    "geo_risk": "División Huawei — sancionada",
    "key_clients": [
      "Huawei",
      "DeepSeek",
      "Unitree"
    ]
  },
  "SKHynix": {
    "founded": 1983,
    "employees": 53000,
    "revenue_2025": "~$65B",
    "mktcap_b": 90.0,
    "risk": "medium",
    "geo_risk": "Corea — HBM exclusivo para Nvidia",
    "key_clients": [
      "Nvidia",
      "Dell",
      "Microsoft"
    ]
  },
  "Micron": {
    "founded": 1978,
    "employees": 47000,
    "revenue_2025": "~$32B",
    "mktcap_b": 110.0,
    "risk": "medium",
    "geo_risk": "EE.UU. — único DRAM americano",
    "key_clients": [
      "Nvidia",
      "Apple",
      "Dell"
    ]
  },
  "Kioxia": {
    "founded": 2017,
    "employees": 15000,
    "revenue_2025": "~¥1.8T",
    "mktcap_b": 9.0,
    "risk": "medium",
    "geo_risk": "Japón — aliada EE.UU.",
    "key_clients": [
      "Western Digital",
      "Dell",
      "HP"
    ]
  },
  "SanDisk": {
    "founded": 1988,
    "employees": 7000,
    "revenue_2025": "~$7B",
    "mktcap_b": null,
    "risk": "medium",
    "geo_risk": "Spin-off WD — bajo",
    "key_clients": [
      "Dell",
      "Amazon",
      "Microsoft"
    ]
  },
  "YMTC": {
    "founded": 2016,
    "employees": 15000,
    "revenue_2025": "~$5B est",
    "mktcap_b": null,
    "risk": "critical",
    "geo_risk": "China — sancionada por EE.UU.",
    "key_clients": [
      "Huawei",
      "China OEM",
      "Gov China"
    ]
  },
  "Ibiden": {
    "founded": 1912,
    "employees": 12000,
    "revenue_2025": "~¥550B",
    "mktcap_b": 7.5,
    "risk": "low",
    "geo_risk": "Japón — cuasi-monopolio ABF",
    "key_clients": [
      "Intel",
      "Nvidia",
      "AMD"
    ]
  },
  "Unimicron": {
    "founded": 1990,
    "employees": 22000,
    "revenue_2025": "~NT$80B",
    "mktcap_b": 5.0,
    "risk": "medium",
    "geo_risk": "Taiwán — geopolítica",
    "key_clients": [
      "Apple",
      "Qualcomm",
      "MediaTek"
    ]
  },
  "ASE": {
    "founded": 1984,
    "employees": 93000,
    "revenue_2025": "~$25B",
    "mktcap_b": 18.0,
    "risk": "medium",
    "geo_risk": "Taiwán — mayor OSAT del mundo",
    "key_clients": [
      "Nvidia",
      "Qualcomm",
      "AMD"
    ]
  },
  "Advantest": {
    "founded": 1954,
    "employees": 5600,
    "revenue_2025": "~¥450B",
    "mktcap_b": 18.0,
    "risk": "low",
    "geo_risk": "Japón — aliada EE.UU.",
    "key_clients": [
      "SK Hynix",
      "TSMC",
      "Nvidia"
    ]
  },
  "Amkor": {
    "founded": 1968,
    "employees": 33000,
    "revenue_2025": "~$6.5B",
    "mktcap_b": 5.5,
    "risk": "low",
    "geo_risk": "EE.UU./Korea — bajo",
    "key_clients": [
      "Qualcomm",
      "Apple",
      "Samsung"
    ]
  },
  "Teradyne": {
    "founded": 1960,
    "employees": 6300,
    "revenue_2025": "~$2.7B",
    "mktcap_b": 17.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "SK Hynix",
      "Micron",
      "TSMC"
    ]
  },
  "Besi": {
    "founded": 1995,
    "employees": 3600,
    "revenue_2025": "~€950M",
    "mktcap_b": 10.0,
    "risk": "medium",
    "geo_risk": "Países Bajos — CHIPS Act beneficiario",
    "key_clients": [
      "SK Hynix",
      "Nvidia",
      "Intel"
    ]
  },
  "Arista": {
    "founded": 2004,
    "employees": 9800,
    "revenue_2025": "~$8.0B",
    "mktcap_b": 85.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "Microsoft",
      "Meta",
      "Google"
    ]
  },
  "Cisco": {
    "founded": 1984,
    "employees": 84000,
    "revenue_2025": "~$55B",
    "mktcap_b": 230.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "Telcos",
      "Enterprise",
      "Gov"
    ]
  },
  "Broadcom": {
    "founded": 1991,
    "employees": 39000,
    "revenue_2025": "~$57B",
    "mktcap_b": 1100.0,
    "risk": "medium",
    "geo_risk": "Restricciones China ASICs",
    "key_clients": [
      "Apple",
      "Meta",
      "Google"
    ]
  },
  "Marvell": {
    "founded": 1997,
    "employees": 8700,
    "revenue_2025": "~$5.8B",
    "mktcap_b": 57.0,
    "risk": "medium",
    "geo_risk": "EE.UU. — menor riesgo",
    "key_clients": [
      "Amazon",
      "Google",
      "Microsoft"
    ]
  },
  "Credo": {
    "founded": 2008,
    "employees": 700,
    "revenue_2025": "~$280M",
    "mktcap_b": 3.0,
    "risk": "low",
    "geo_risk": "EE.UU./Taiwán — bajo",
    "key_clients": [
      "Microsoft",
      "Amazon",
      "Meta"
    ]
  },
  "Astera": {
    "founded": 2017,
    "employees": 400,
    "revenue_2025": "~$250M",
    "mktcap_b": 4.5,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "Microsoft",
      "Meta",
      "Nvidia"
    ]
  },
  "Coherent": {
    "founded": 1971,
    "employees": 25000,
    "revenue_2025": "~$5B",
    "mktcap_b": 18.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "Microsoft",
      "Google",
      "Meta"
    ]
  },
  "Ciena": {
    "founded": 1992,
    "employees": 7000,
    "revenue_2025": "~$4.0B",
    "mktcap_b": 9.5,
    "risk": "low",
    "geo_risk": "EE.UU./Canada — bajo",
    "key_clients": [
      "AT&T",
      "SubCom",
      "NTT"
    ]
  },
  "Lumentum": {
    "founded": 1994,
    "employees": 5800,
    "revenue_2025": "~$1.6B",
    "mktcap_b": 3.5,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "SubCom",
      "Cisco",
      "Infinera"
    ]
  },
  "Innolight": {
    "founded": 2008,
    "employees": 3000,
    "revenue_2025": "~$600M",
    "mktcap_b": null,
    "risk": "medium",
    "geo_risk": "China — vigilada",
    "key_clients": [
      "Arista",
      "Cisco",
      "Microsoft"
    ]
  },
  "Amphenol": {
    "founded": 1932,
    "employees": 95000,
    "revenue_2025": "~$16B",
    "mktcap_b": 93.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "Dell",
      "Cisco",
      "Arista"
    ]
  },
  "Vertiv": {
    "founded": 2016,
    "employees": 23000,
    "revenue_2025": "~$7.5B",
    "mktcap_b": 36.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "Microsoft",
      "Google",
      "Equinix"
    ]
  },
  "MPWR": {
    "founded": 1997,
    "employees": 3900,
    "revenue_2025": "~$2.0B",
    "mktcap_b": 19.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "Nvidia",
      "Dell",
      "SuperMicro"
    ]
  },
  "Eaton": {
    "founded": 1911,
    "employees": 93000,
    "revenue_2025": "~$24B",
    "mktcap_b": 120.0,
    "risk": "low",
    "geo_risk": "EE.UU./Irlanda — bajo",
    "key_clients": [
      "Equinix",
      "Microsoft",
      "Amazon"
    ]
  },
  "Schneider": {
    "founded": 1836,
    "employees": 168000,
    "revenue_2025": "~€36B",
    "mktcap_b": 140.0,
    "risk": "low",
    "geo_risk": "Francia — bajo",
    "key_clients": [
      "Equinix",
      "Google",
      "Amazon"
    ]
  },
  "GEVernova": {
    "founded": 2023,
    "employees": 77000,
    "revenue_2025": "~$34B",
    "mktcap_b": 75.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "Amazon",
      "Microsoft",
      "Constellation"
    ]
  },
  "Constellation": {
    "founded": 1999,
    "employees": 13000,
    "revenue_2025": "~$22B",
    "mktcap_b": 68.0,
    "risk": "low",
    "geo_risk": "EE.UU. — nuclear",
    "key_clients": [
      "Microsoft",
      "Amazon",
      "Google"
    ]
  },
  "SiemensEnergy": {
    "founded": 2020,
    "employees": 99000,
    "revenue_2025": "~€35B",
    "mktcap_b": 50.0,
    "risk": "low",
    "geo_risk": "Alemania — bajo",
    "key_clients": [
      "Schneider",
      "Equinix",
      "Azure DC"
    ]
  },
  "DeltaElectronics": {
    "founded": 1971,
    "employees": 89000,
    "revenue_2025": "~NT$400B",
    "mktcap_b": 20.0,
    "risk": "low",
    "geo_risk": "Taiwán — menor riesgo",
    "key_clients": [
      "Dell",
      "HP",
      "Nvidia"
    ]
  },
  "SubCom": {
    "founded": 1955,
    "employees": 2000,
    "revenue_2025": "~$1.2B",
    "mktcap_b": null,
    "risk": "medium",
    "geo_risk": "EE.UU. — contratista clave del Pentágono",
    "key_clients": [
      "Google",
      "Facebook",
      "Amazon"
    ]
  },
  "NEC": {
    "founded": 1899,
    "employees": 120000,
    "revenue_2025": "~¥3.3T",
    "mktcap_b": 16.0,
    "risk": "low",
    "geo_risk": "Japón — aliada EE.UU.",
    "key_clients": [
      "KDDI",
      "Softbank",
      "Japan Gov"
    ]
  },
  "ASN": {
    "founded": 1998,
    "employees": 2200,
    "revenue_2025": "~€900M",
    "mktcap_b": null,
    "risk": "medium",
    "geo_risk": "Div. Nokia-Alcatel — competencia China con HMN",
    "key_clients": [
      "Google",
      "Orange",
      "Telecom"
    ]
  },
  "Lumen": {
    "founded": 1997,
    "employees": 22000,
    "revenue_2025": "~$13B",
    "mktcap_b": 1.5,
    "risk": "high",
    "geo_risk": "EE.UU. — deuda masiva",
    "key_clients": [
      "Microsoft",
      "AWS",
      "Government"
    ]
  },
  "Corning": {
    "founded": 1851,
    "employees": 57000,
    "revenue_2025": "~$14B",
    "mktcap_b": 37.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "SubCom",
      "NEC",
      "AT&T"
    ]
  },
  "Dell": {
    "founded": 1984,
    "employees": 120000,
    "revenue_2025": "~$96B",
    "mktcap_b": 85.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "Microsoft",
      "Google",
      "Palantir"
    ]
  },
  "HPE": {
    "founded": 2015,
    "employees": 62000,
    "revenue_2025": "~$32B",
    "mktcap_b": 22.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "AWS",
      "Azure",
      "Enterprise"
    ]
  },
  "Lenovo": {
    "founded": 1984,
    "employees": 77000,
    "revenue_2025": "~$65B",
    "mktcap_b": 9.0,
    "risk": "medium",
    "geo_risk": "China — riesgo geopolítico",
    "key_clients": [
      "Enterprise China",
      "SMB",
      "Gov China"
    ]
  },
  "Foxconn": {
    "founded": 1974,
    "employees": 700000,
    "revenue_2025": "~NT$6.8T",
    "mktcap_b": 55.0,
    "risk": "medium",
    "geo_risk": "Taiwán/China — enorme exposición geopolítica",
    "key_clients": [
      "Apple",
      "Nvidia",
      "Microsoft"
    ]
  },
  "SuperMicro": {
    "founded": 1993,
    "employees": 5700,
    "revenue_2025": "~$15B",
    "mktcap_b": 15.0,
    "risk": "medium",
    "geo_risk": "EE.UU. — auditoría pendiente",
    "key_clients": [
      "CoreWeave",
      "xAI",
      "Meta"
    ]
  },
  "Quanta": {
    "founded": 1988,
    "employees": 88000,
    "revenue_2025": "~NT$1.3T",
    "mktcap_b": 20.0,
    "risk": "medium",
    "geo_risk": "Taiwán — menor riesgo",
    "key_clients": [
      "Google",
      "Facebook",
      "Amazon"
    ]
  },
  "Celestica": {
    "founded": 1996,
    "employees": 12000,
    "revenue_2025": "~$3.5B",
    "mktcap_b": 7.0,
    "risk": "low",
    "geo_risk": "Canadá — bajo",
    "key_clients": [
      "Cisco",
      "Juniper",
      "HyperScalers"
    ]
  },
  "Jabil": {
    "founded": 1966,
    "employees": 260000,
    "revenue_2025": "~$28B",
    "mktcap_b": 18.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "Apple",
      "Amazon",
      "Cisco"
    ]
  },
  "Microsoft": {
    "founded": 1975,
    "employees": 228000,
    "revenue_2025": "~$270B",
    "mktcap_b": 3500.0,
    "risk": "low",
    "geo_risk": "EE.UU. — líder cloud IA",
    "key_clients": [
      "OpenAI",
      "Enterprise",
      "Gov"
    ]
  },
  "Amazon": {
    "founded": 1994,
    "employees": 1525000,
    "revenue_2025": "~$700B",
    "mktcap_b": 2400.0,
    "risk": "low",
    "geo_risk": "EE.UU. — líder cloud",
    "key_clients": [
      "Anthropic",
      "Netflix",
      "NASA"
    ]
  },
  "Alphabet": {
    "founded": 1998,
    "employees": 180000,
    "revenue_2025": "~$380B",
    "mktcap_b": 2500.0,
    "risk": "low",
    "geo_risk": "EE.UU. — antitrust en curso",
    "key_clients": [
      "Anthropic (via Google)",
      "Waymo",
      "YouTube"
    ]
  },
  "Oracle": {
    "founded": 1977,
    "employees": 165000,
    "revenue_2025": "~$56B",
    "mktcap_b": 430.0,
    "risk": "low",
    "geo_risk": "EE.UU. — OCI crecimiento acelerado",
    "key_clients": [
      "xAI",
      "Nvidia",
      "Gov EE.UU."
    ]
  },
  "CoreWeave": {
    "founded": 2017,
    "employees": 1600,
    "revenue_2025": "~$2.5B",
    "mktcap_b": 35.0,
    "risk": "high",
    "geo_risk": "EE.UU. — deuda GPU masiva",
    "key_clients": [
      "Microsoft",
      "Meta",
      "Cohere"
    ]
  },
  "Nebius": {
    "founded": 2024,
    "employees": 3000,
    "revenue_2025": "~$120M",
    "mktcap_b": 5.0,
    "risk": "high",
    "geo_risk": "Europa — spin-off Yandex",
    "key_clients": [
      "AI startups EU",
      "Research labs",
      "SMB"
    ]
  },
  "Equinix": {
    "founded": 1998,
    "employees": 13700,
    "revenue_2025": "~$8.8B",
    "mktcap_b": 82.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "Microsoft",
      "Google",
      "Amazon"
    ]
  },
  "DigitalRealty": {
    "founded": 2004,
    "employees": 4800,
    "revenue_2025": "~$5.6B",
    "mktcap_b": 50.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "Oracle",
      "IBM",
      "Meta"
    ]
  },
  "OpenAI": {
    "founded": 2015,
    "employees": 3500,
    "revenue_2025": "~$4B",
    "mktcap_b": 300.0,
    "risk": "medium",
    "geo_risk": "EE.UU. — regulación emergente IA",
    "key_clients": [
      "Microsoft",
      "Enterprise",
      "Consumers"
    ]
  },
  "Anthropic": {
    "founded": 2021,
    "employees": 1000,
    "revenue_2025": "~$1.5B",
    "mktcap_b": 60.0,
    "risk": "medium",
    "geo_risk": "EE.UU. — regulación emergente",
    "key_clients": [
      "Amazon",
      "Google",
      "Enterprise"
    ]
  },
  "xAI": {
    "founded": 2023,
    "employees": 700,
    "revenue_2025": "~$1B",
    "mktcap_b": 50.0,
    "risk": "high",
    "geo_risk": "EE.UU. — concentración poder Musk",
    "key_clients": [
      "Tesla",
      "X (Twitter)",
      "Gov"
    ]
  },
  "Mistral": {
    "founded": 2023,
    "employees": 200,
    "revenue_2025": "~€100M",
    "mktcap_b": 6.2,
    "risk": "high",
    "geo_risk": "Francia — compite con OpenAI",
    "key_clients": [
      "Microsoft Azure",
      "BNP Paribas",
      "Orange"
    ]
  },
  "Meta": {
    "founded": 2004,
    "employees": 67000,
    "revenue_2025": "~$165B",
    "mktcap_b": 1700.0,
    "risk": "low",
    "geo_risk": "EE.UU. — regulación social",
    "key_clients": [
      "Advertisers",
      "Llama API users",
      "Enterprise"
    ]
  },
  "DeepSeek": {
    "founded": 2023,
    "employees": 200,
    "revenue_2025": "~$50M est",
    "mktcap_b": null,
    "risk": "critical",
    "geo_risk": "China — regulación IA, acceso chip restringido",
    "key_clients": [
      "Huawei",
      "HiSilicon",
      "Research China"
    ]
  },
  "Qwen": {
    "founded": 2023,
    "employees": 500,
    "revenue_2025": "div. Alibaba",
    "mktcap_b": null,
    "risk": "high",
    "geo_risk": "China — Alibaba Cloud",
    "key_clients": [
      "Alibaba Cloud",
      "China Enterprise",
      "Research"
    ]
  },
  "Tesla": {
    "founded": 2003,
    "employees": 127000,
    "revenue_2025": "~$100B",
    "mktcap_b": 1100.0,
    "risk": "medium",
    "geo_risk": "EE.UU./China — Gigafactory Shanghai",
    "key_clients": [
      "Consumidor EV",
      "FleetOp",
      "Dojo cloud"
    ]
  },
  "Figure": {
    "founded": 2022,
    "employees": 700,
    "revenue_2025": "~$50M",
    "mktcap_b": 3.0,
    "risk": "high",
    "geo_risk": "EE.UU. — muy pronto para revenue",
    "key_clients": [
      "BMW",
      "Amazon (piloto)",
      "Microsoft"
    ]
  },
  "BostonDynamics": {
    "founded": 1992,
    "employees": 600,
    "revenue_2025": "~$200M",
    "mktcap_b": null,
    "risk": "medium",
    "geo_risk": "EE.UU. — Hyundai dueño",
    "key_clients": [
      "Amazon",
      "Hyundai",
      "DoD EE.UU."
    ]
  },
  "OneX": {
    "founded": 2014,
    "employees": 200,
    "revenue_2025": "~$30M",
    "mktcap_b": null,
    "risk": "high",
    "geo_risk": "Noruega — menor riesgo",
    "key_clients": [
      "Pilot industrial",
      "NEK",
      "Research"
    ]
  },
  "Unitree": {
    "founded": 2016,
    "employees": 700,
    "revenue_2025": "~$200M est",
    "mktcap_b": null,
    "risk": "high",
    "geo_risk": "China — vigilada export control",
    "key_clients": [
      "China industrial",
      "Research",
      "DeepSeek R&D"
    ]
  },
  "Apptronik": {
    "founded": 2016,
    "employees": 200,
    "revenue_2025": "~$20M",
    "mktcap_b": null,
    "risk": "high",
    "geo_risk": "EE.UU. — early stage",
    "key_clients": [
      "NASA",
      "Amazon (piloto)",
      "GXO Logistics"
    ]
  },
  "Palantir": {
    "founded": 2003,
    "employees": 3800,
    "revenue_2025": "~$3.4B",
    "mktcap_b": 60.0,
    "risk": "low",
    "geo_risk": "EE.UU. — Gov contracts",
    "key_clients": [
      "US DoD",
      "NHS UK",
      "Airbus"
    ]
  },
  "CrowdStrike": {
    "founded": 2011,
    "employees": 10400,
    "revenue_2025": "~$4.4B",
    "mktcap_b": 80.0,
    "risk": "low",
    "geo_risk": "EE.UU. — July 2024 incident",
    "key_clients": [
      "Fortune 500",
      "Gov EE.UU.",
      "NHS"
    ]
  },
  "Snowflake": {
    "founded": 2012,
    "employees": 8200,
    "revenue_2025": "~$4.0B",
    "mktcap_b": 50.0,
    "risk": "low",
    "geo_risk": "EE.UU. — bajo",
    "key_clients": [
      "DoorDash",
      "Capital One",
      "Adobe"
    ]
  },
  /* ===== v7 · M8 + soporte: meta de los nuevos nodos ===== */
  "Huawei":        {"founded":1987,"employees":207000,"revenue_2025":"~$99B est","mktcap_b":null,"risk":"critical","geo_risk":"SANCIONADA: entidad lista EE.UU. desde 2019; sin acceso a chips americanos o EDA","key_clients":["China Telecom","China Mobile","Brasil Gov"]},
  "MediaTek":      {"founded":1997,"employees":20000,"revenue_2025":"~NT$550B","mktcap_b":55.0,"risk":"medium","geo_risk":"Taiwán — geopolítica latente; ~40% ventas China","key_clients":["Xiaomi","OPPO","Samsung Mid-range"]},
  "Groq":          {"founded":2016,"employees":500,"revenue_2025":"pre-rev","mktcap_b":2.8,"risk":"low","geo_risk":"EE.UU. — bajo","key_clients":["GroqCloud users","DoE piloto","Enterprise waitlist"]},
  "SambaNova":     {"founded":2017,"employees":500,"revenue_2025":"~$200M","mktcap_b":5.0,"risk":"low","geo_risk":"EE.UU. — bajo","key_clients":["US DoE","Samsung","Financial services"]},
  "WesternDigital":{"founded":1970,"employees":12000,"revenue_2025":"~$13B","mktcap_b":22.0,"risk":"low","geo_risk":"EE.UU. — bajo","key_clients":["Amazon","Google","Microsoft"]},
  "Naver":         {"founded":1999,"employees":14000,"revenue_2025":"~KRW9.7T","mktcap_b":18.0,"risk":"medium","geo_risk":"Corea del Sur — riesgo NK latente","key_clients":["Korean enterprise","Webtoon","LINE Japan"]},
  "SoftBank":      {"founded":1981,"employees":65000,"revenue_2025":"~¥7.0T","mktcap_b":135.0,"risk":"low","geo_risk":"Japón — bajo; exposición indirecta a China vía cartera","key_clients":["ARM","OpenAI / Stargate","Vision Fund portfolio"]},
  "Xiaomi":        {"founded":2010,"employees":45000,"revenue_2025":"~CN¥430B","mktcap_b":150.0,"risk":"medium","geo_risk":"China — expuesta a controles de exportación de semiconductores avanzados","key_clients":["Consumo global","India","Europa"]},
  "BMW":           {"founded":1916,"employees":155000,"revenue_2025":"~€150B","mktcap_b":55.0,"risk":"low","geo_risk":"Alemania — bajo; exposición a aranceles China/EE.UU.","key_clients":["Consumo premium global","China","EE.UU."]},
  "Hyundai":       {"founded":1967,"employees":120000,"revenue_2025":"~KRW180T","mktcap_b":45.0,"risk":"medium","geo_risk":"Corea del Sur — riesgo NK latente; aranceles EE.UU.","key_clients":["EE.UU.","Europa","India"]},
  "SAIC":          {"founded":1955,"employees":200000,"revenue_2025":"~CN¥750B","mktcap_b":20.0,"risk":"medium","geo_risk":"China — aranceles UE/EE.UU. a EVs; SOE bajo escrutinio","key_clients":["China consumo","MG Europa","JV Volkswagen/GM"]}
};

const NODE_ID_ALIAS = {
  // Cloud aliases
  'AWS': 'Amazon', 'Azure': 'Microsoft', 'GCP': 'Alphabet', 'Google': 'Alphabet',
  // Chip companies — canonical ID mismatch fixes
  'NVIDIA': 'Nvidia',
  'Lam_Research': 'Lam',             // links_expand uses Lam_Research, node is Lam
  'Applied_Materials': 'AMAT',       // links_expand uses Applied_Materials, node is AMAT
  'Tokyo_Electron': 'TEL',           // links_expand uses Tokyo_Electron, node is TEL
  'SK_Hynix': 'SKHynix',             // links_expand uses SK_Hynix, node is SKHynix
  'MetaPlatforms': 'Meta',           // links_expand uses MetaPlatforms, node is Meta
  'Electron': 'RocketLab',           // Electron is RocketLab's rocket; maps to company node
  'Alibaba': 'AlibabaCloud',         // parent; maps to Alibaba Cloud node
  // Other normalization
  'Texas_Instruments': 'TexasInstruments', 'TI': 'TexasInstruments',
  'STMicro': 'STMicroelectronics', 'Xilinx': 'AMD',
  'BoozAllen': 'Booz_Allen', 'CACI_Int': 'CACI',
  // Recover dropped link endpoints that reference real companies by alt names
  'SK Hynix': 'SKHynix', 'Western Digital': 'WesternDigital',
  'Alibaba Cloud': 'AlibabaCloud', 'Microsoft Azure': 'Microsoft',
  'Softbank': 'SoftBank', 'Facebook': 'Meta', 'Apple (memoria)': 'Apple',

  // ── RESOLUCIÓN DE ENTIDADES (2026-07, Etapa 2) ────────────────────────────
  // Cada clave es un id DUPLICADO de la misma empresa: el merge absorbe sus
  // campos faltantes en el canónico, redirige sus links y lo quita de NODES.
  // NODE_BY_ID conserva la clave alias apuntando al nodo canónico (compat:
  // hechos temporales, presets y jumpTo con ids viejos siguen funcionando).
  'Arm_Holdings': 'ARM',
  'Oxford_Instruments': 'OxfordInstruments',
  'Ansys': 'Synopsys',                    // adquirida por Synopsys (2025)
  'Siemens_EDA': 'SiemensEDA',
  'ASML_EUV': 'ASML',                     // línea de producto
  'IntelLoihi': 'Intel', 'Intel_Loihi': 'Intel',   // chip de investigación
  'GlobalFoundries': 'GF',
  'NVidia_Networking': 'Nvidia', 'NVIDIA_NIM': 'Nvidia',  // divisiones
  'Qualcomm_Infra': 'Qualcomm',
  'ASEGroup': 'ASE',
  'BroadcomASIC': 'Broadcom',
  'MonolithicPower': 'MPWR', 'Monolithic_Power': 'MPWR',
  'EatonCorp': 'Eaton',
  'CrayHPE': 'HPE', 'HPE_Cray': 'HPE',
  'Supermicro_Liquid': 'SuperMicro',
  'Quanta_Computer': 'Quanta',
  'AWS_Ground': 'Amazon',                 // AWS Ground Station = servicio de Amazon
  'OracleCloud': 'Oracle',
  'Palantir_Gov': 'Palantir',
  'Groq_AI': 'Groq',
  'Western_Digital': 'WesternDigital',
  'C3ai': 'C3AI',
  'Ampere_Computing': 'AmpereComputing',
  'EsperantoTech': 'Esperanto', 'Esperanto_Tech': 'Esperanto',
  'ViaviSolutions': 'Viavi',
  'Mobileye_Auto': 'Mobileye',
  'Luminar_Lidar': 'Luminar',
  'TempusAI': 'Tempus',
  'ButterflyNetwork': 'Butterfly',
  'InsilicoBio': 'Insilico',
  'CognitionAI': 'Cognition',
  'AdeptAI': 'Adept',
  'EutelsatOneWeb': 'Eutelsat',           // fusionadas (2023)
  'Spire_Global': 'SpireGlobal',
  'LatticeSemi': 'Lattice', 'Lattice_Semiconductor': 'Lattice',
  'MaxLinear_Optical': 'MaxLinear',
  'Silicon_Labs': 'SiliconLabs',
  'Energy_Fuels': 'EnergyFuels',
  'Relativity': 'RelativitySpace',
  'Allegro_Micro': 'Allegro',
  'CEVA': 'Ceva',
  'Indie_Semi': 'Indie',
  'Cohere_NLP': 'Cohere', 'Cohere_AI': 'Cohere',
  'ViaSatCom': 'Viasat',
  'Onto_Innovation': 'OntoInnovation',
  'Cabot_Micro': 'CMC_Materials',         // Cabot Micro se renombró CMC Materials
  'TowerSemi': 'TowerSemiconductor',
  'Kratos': 'Kratos_Defense',
  'Scale_AI': 'ScaleAI',
  // NO fusionados a propósito (colisión de ticker, no duplicado): HashiCorp≠IBM,
  // Qwen≠AlibabaCloud, Aerojet⊂L3Harris, Altium⊂Renesas, Agility≠Amazon.
};

const LOGO_DOMAIN = {
  NVIDIA:'nvidia.com', AMD:'amd.com', Intel:'intel.com', TSMC:'tsmc.com', Samsung:'samsung.com',
  Qualcomm:'qualcomm.com', Broadcom:'broadcom.com', Marvell:'marvell.com', Micron:'micron.com',
  SK_Hynix:'skhynix.com', WesternDigital:'westerndigital.com', Seagate:'seagate.com',
  ASML:'asml.com', Applied_Materials:'appliedmaterials.com', Lam_Research:'lamresearch.com',
  KLA:'kla.com', Tokyo_Electron:'tel.com', Synopsys:'synopsys.com', Cadence:'cadence.com',
  NXPI:'nxp.com', TI:'ti.com', STMicro:'st.com', Infineon:'infineon.com',
  Renesas:'renesas.com', Murata:'murata.com', TDK:'tdk.com', Kyocera:'kyocera.com',
  AWS:'amazon.com', Google_Cloud:'cloud.google.com', Azure:'microsoft.com',
  OracleCloud:'oracle.com', AlibabaCloud:'alibabacloud.com', IBMCloud:'ibm.com',
  OpenAI:'openai.com', Anthropic:'anthropic.com', Meta_AI:'meta.com',
  Mistral:'mistral.ai', Stability_AI:'stability.ai', DeepMind:'deepmind.com',
  xAI:'x.ai', Cohere_AI:'cohere.com', HuggingFace:'huggingface.co',
  TSMC_Advanced:'tsmc.com', GlobalFoundries:'gf.com', UMC:'umc.com', SMIC:'smics.com',
  Samsung_Foundry:'samsung.com', TowerSemi:'towersemi.com',
  SpaceX:'spacex.com', RocketLab:'rocketlabusa.com', ULA:'ulalaunch.com',
  Northrop:'northropgrumman.com', Lockheed:'lockheedmartin.com', Raytheon:'rtx.com',
  Boeing:'boeing.com', Airbus:'airbus.com', L3Harris:'l3harris.com',
  Palantir:'palantir.com', C3AI:'c3.ai', Datadog:'datadoghq.com',
  CrowdStrike:'crowdstrike.com', SentinelOne:'sentinelone.com', PaloAltoNetworks:'paloaltonetworks.com',
  MongoDB:'mongodb.com', Elastic:'elastic.co', Snowflake:'snowflake.com',
  Cloudflare:'cloudflare.com', Twilio:'twilio.com', HashiCorp:'hashicorp.com',
  Databricks:'databricks.com', Scale_AI:'scale.com',
  Mobileye:'mobileye.com', Waymo:'waymo.com',
  Tesla:'tesla.com', Rivian:'rivian.com', Lucid:'lucidmotors.com',
  CATL:'catl.com', QuantumScape:'quantumscape.com', SolidPower:'solidpowerbattery.com',
  Coherent:'ii-vi.com', Lumentum:'lumentum.com', ViaviSolutions:'viavi.com',
  Satellogic:'satellogic.com', SpireGlobal:'spire.com', PlanetLabs:'planet.com',
  DigitalBridge:'digitalbridge.com', Equinix:'equinix.com', IronMountain:'ironmountain.com',
  Viasat:'viasat.com', ViaSat:'viasat.com', OneWeb:'oneweb.net',
  NexTracker:'nextracker.com', Array_Technologies:'arraytechinc.com',
  EnergyFuels:'energyfuels.com', Lynas:'lynasrareearths.com',
  PiedmontLithium:'piedmontlithium.com', SigmaLithium:'sigmalithium.com',
  Wolfspeed:'wolfspeed.com', onsemi:'onsemi.com',
  Entegris:'entegris.com', Cabot_Micro:'cabotmicro.com', Dupont:'dupont.com',
  Sherwin:'sherwin-williams.com', JSR:'jsr.co.jp', ShinEtsu:'shinetsu.co.jp',
  Sumco:'sumco.co.jp', Siltronic:'siltronic.com',
  AXT:'axt.com', IQE:'iqep.com', Coherus:'coherus.com',
  FormFactor:'formfactor.com', Teradyne:'teradyne.com', OntoInnovation:'ontoinnovation.com',
  Advantest:'advantest.com', Cohu:'cohu.com',
  CirrusLogic:'cirrus.com', Semtech:'semtech.com', Lattice_Semiconductor:'latticesemi.com',
  Cirrus_Logic:'cirrus.com', GenDigital:'gendigital.com', Verint:'verint.com',
  Trimble_Inc:'trimble.com', Rockwell_Automation:'rockwellautomation.com',
  Cerebras:'cerebras.net', Groq_AI:'groq.com',
};

const INVEST_PATH={
  // Subsidiarias — invertir vía empresa matriz
  Waymo:{ticker:'GOOGL',parent:'Alphabet (Google)',note:'División de conducción autónoma 100% de Alphabet'},
  Zoox:{ticker:'AMZN',parent:'Amazon',note:'Subsidiaria de Amazon adquirida en 2020'},
  DeepMind:{ticker:'GOOGL',parent:'Alphabet (Google)',note:'División de investigación IA de Alphabet'},
  Kensho:{ticker:'SPGI',parent:'S&P Global',note:'Adquirida por S&P Global (2018) por $550M'},
  Quantinuum:{ticker:'HON',parent:'Honeywell',note:'JV computación cuántica (Honeywell 54%)'},
  IntelLoihi:{ticker:'INTC',parent:'Intel',note:'Proyecto neuromorphic de Intel'},
  OracleCloud:{ticker:'ORCL',parent:'Oracle',note:'División cloud de Oracle'},
  AlibabaCloud:{ticker:'BABA',parent:'Alibaba Group',note:'División cloud de Alibaba'},
  // Adquiridas — invertir vía acquirer
  HashiCorp:{ticker:'IBM',parent:'IBM',note:'Adquirida por IBM (2024) por $6.4B'},
  ArcadiumLithium:{ticker:'RIO',parent:'Rio Tinto',note:'Adquirida por Rio Tinto (2024) por $6.7B'},
  Ansys:{ticker:'SNPS',parent:'Synopsys',note:'Adquirida por Synopsys (2024) por $35B'},
  Graphcore:{ticker:'9984.T',parent:'SoftBank Group (Tokio)',note:'Adquirida por SoftBank (2024)'},
  Lightsource_BP:{ticker:'BP.L',parent:'BP (LSE)',note:'BP posee 50% de Lightsource bp'},
  Agility:{ticker:'AMZN',parent:'Amazon',note:'Amazon es socio exclusivo y principal deploy partner'},
  Vedanta_Semi:{ticker:'VEDL.NS',parent:'Vedanta Limited (NSE)',note:'JV Vedanta (51%) + Foxconn (49%) para fab en India'},
  QTS:{ticker:'BX',parent:'Blackstone',note:'Adquirida por Blackstone REIT (2021)'},
  CYRUSONE:{ticker:'KKR',parent:'KKR',note:'Adquirida por KKR & GIP (2022)'},
  SWITCH:{ticker:'DBRG',parent:'DigitalBridge',note:'Adquirida por DigitalBridge (2022)'},
  Altium:{ticker:'6723.T',parent:'Renesas (Tokio)',note:'Adquirida por Renesas (2024) por $5.9B'},
  Cepton:{ticker:'7276.T',parent:'KOITO Manufacturing (Tokio)',note:'Adquirida por KOITO (2023)'},
  // Privadas con exposición vía inversores cotizados
  OpenAI:{ticker:'MSFT',parent:'Microsoft (14% stake)',note:'OpenAI privada — Microsoft es inversor principal ($13B)'},
  Anthropic:{ticker:'GOOGL',parent:'Alphabet ($300M+)',note:'Privada — Google y Amazon son principales inversores. AMZN hasta $4B'},
  SpaceX:{etf:'ARKX',etfName:'ARK Space Exploration ETF',note:'SpaceX privada — exposición indirecta vía ARKX o fondos de capital privado'},
  StarLink:{etf:'ARKX',etfName:'ARK Space Exploration ETF',note:'Filial de SpaceX (privada) — misma ruta de inversión indirecta'},
  Mistral:{note:'Privada (FR). Inversores: Andreessen Horowitz, Lightspeed. Sin exposición bursátil directa. Pre-IPO'},
  Databricks:{note:'Pre-IPO. Valoración ~$62B (2024). IPO anticipada. Sin ticker actual'},
  Scale_AI:{note:'Pre-IPO. Valoración $13.8B. Contratos DoD/OpenAI. IPO pendiente'},
  HuggingFace:{note:'Pre-IPO. Valoración $4.5B. Inversores: Salesforce, Google, NVIDIA. Sin ticker'},
  Cohere_AI:{note:'Pre-IPO. Valoración $5B. Enterprise AI. Sin ticker actual'},
  Figure:{note:'Pre-IPO. Valoración $2.6B. Backed: Microsoft, OpenAI, Nvidia, Bezos. Sin ticker'},
  Tenstorrent:{note:'Pre-IPO. $100M ronda. Samsung + LG partnership. Sin ticker'},
  Groq_AI:{note:'Pre-IPO. $640M Series D. $2.8B valoración. Sin ticker'},
  Cerebras:{ticker:'CBRS',parent:'Cerebras Systems (Nasdaq)',note:'IPO realizada en Nasdaq 2024 bajo ticker CBRS'},
  Ampere_Computing:{note:'Pre-IPO. $1.5B ARR. OCI + Azure + GCP. IPO planeada ~2025-2026'},
};
