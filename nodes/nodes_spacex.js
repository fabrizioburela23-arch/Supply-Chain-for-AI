// nodes/nodes_spacex.js — Ecosistema SpaceX y sector espacial completo

const NODES_SPACEX = [

{"id":"SpaceX","label":"SpaceX","ticker":"No cotiza · privada ~$350B (Musk)","cat":"space_launch",
"port":"","preipo":true,"big":true,
"role":"Mayor empresa privada de lanzamiento espacial; opera Starlink (6,000+ satélites LEO), Starshield (defensa) y desarrolla Starship para colonización lunar/marciana.",
"role_en":"World's largest private launch company; operates Starlink (6,000+ LEO satellites), Starshield (defense) and develops Starship for lunar/Martian colonization.",
"supplies":"Servicios de lanzamiento a NASA, DoD, clientes comerciales; internet Starlink a 4M+ suscriptores; Starshield para inteligencia gubernamental clasificada.",
"moat":"Costo de lanzamiento 10x menor que competencia por reusabilidad; verticalización extrema (fabrica 90%+ en-house incluyendo ASICs Starlink); Starship habilita economía lunar.",
"loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO ~$350B; Starlink ARR ~$8B +80% anual",
"margin":0.12,"mkt":null,
"thesis":"La única empresa que ha reducido el costo de acceso al espacio en un orden de magnitud.",
"founded":2002,"employees":14000,"revenue_2025":"~$15B","geo_risk":"EE.UU. — ITAR, DoD contractor crítico"},

{"id":"RocketLab","label":"Rocket Lab","ticker":"RKLB · Nasdaq","cat":"space_launch",
"port":"","mkt":"RKLB",
"role":"Segundo mayor operador de cohetes reutilizables; Electron (smallsat) + Neutron (mid-class, 2026).",
"role_en":"Second-largest reusable rocket operator; Electron (smallsat) + Neutron (mid-class, 2026).",
"supplies":"Lanzamientos dedicados de smallsats para Planet Labs, BlackSky, DoD, DARPA.",
"moat":"Único competidor con cohete reutilizable operacional a escala (Electron 53+ misiones).",
"loc":"EE.UU./Nueva Zelanda","country":"EEUU","growth":"🔵 +35% 2026",
"margin":0.08,"mkt":"RKLB","founded":2006,"employees":2200,"revenue_2025":"~$450M","geo_risk":"EE.UU./NZ — bajo"},

{"id":"BlueOrigin","label":"Blue Origin","ticker":"Pre-IPO (Bezos)","cat":"space_launch",
"port":"","preipo":true,
"role":"Empresa espacial de Jeff Bezos; New Glenn orbital + BE-4 motores para ULA + turismo Blue Shepard.",
"moat":"$1B+/año de Bezos; BE-4 es el único motor americano competidor de Raptor de SpaceX.",
"loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO; New Glenn en rampa 2026",
"founded":2000,"employees":10000,"revenue_2025":"~$500M est","geo_risk":"EE.UU. — bajo"},

{"id":"Hexcel","label":"Hexcel","ticker":"HXL · NYSE","cat":"materials","mkt":"HXL",
"role":"Líder en materiales compuestos de fibra de carbono para aeroespacial y espacio.",
"supplies":"Fibra de carbono y preimpregnados para etapas de Falcon 9, Falcon Heavy y Starship.",
"moat":"Oligopolio con Solvay y Toray; SpaceX es uno de sus mayores clientes de crecimiento.",
"loc":"EE.UU.","country":"EEUU","growth":"🟢 +12%","margin":0.18,"founded":1948,"employees":9500,"revenue_2025":"~$1.8B","geo_risk":"EE.UU. — bajo"},

{"id":"TorayIndustries","label":"Toray Industries","ticker":"3402 · TSE","cat":"materials",
"role":"Mayor productor mundial de fibra de carbono T800/T1100; proveedor crítico de SpaceX y Boeing.",
"moat":"Tecnología propietaria de PAN precursor; cuota ~35% del mercado global de CF aeroespacial.",
"loc":"Japón","country":"Japon","growth":"🟢 +10%","margin":0.09,"founded":1926,"employees":47000,"revenue_2025":"~¥2.5T","geo_risk":"Japón — aliada EE.UU."},

{"id":"AlleghenyTech","label":"Allegheny Technologies","ticker":"ATI · NYSE","cat":"materials","mkt":"ATI",
"role":"Productor de aleaciones de titanio y níquel de alta temperatura para motores Raptor de SpaceX.",
"moat":"Cuota dominante en aleaciones especiales aeroespaciales EE.UU.",
"loc":"EE.UU.","country":"EEUU","growth":"🔵 +18%","margin":0.14,"founded":1996,"employees":8700,"revenue_2025":"~$4.3B","geo_risk":"EE.UU. — bajo"},

{"id":"CarpenterTech","label":"Carpenter Technology","ticker":"CRS · NYSE","cat":"materials","mkt":"CRS",
"role":"Aceros especiales y aleaciones para componentes de alta precisión en cohetes y satélites.",
"moat":"Niche líder en aceros de ultra-alta resistencia para aplicaciones extremas.",
"loc":"EE.UU.","country":"EEUU","growth":"🟢 +12%","margin":0.13,"founded":1889,"employees":4700,"revenue_2025":"~$2.6B","geo_risk":"EE.UU. — bajo"},

{"id":"ParkerHannifin","label":"Parker Hannifin","ticker":"PH · NYSE","cat":"equip","mkt":"PH",
"role":"Sistemas hidráulicos, neumáticos y conectores de alta presión para ground systems espaciales.",
"moat":"Proveedor industrial diversificado que aprovecha el boom espacial.",
"loc":"EE.UU.","country":"EEUU","growth":"🟢 +9%","margin":0.2,"founded":1917,"employees":62000,"revenue_2025":"~$20B","geo_risk":"EE.UU. — bajo"},

{"id":"Moog","label":"Moog Inc.","ticker":"MOG.A · NYSE","cat":"equip","mkt":"MOG",
"role":"Actuadores de vuelo y válvulas de alta presión para cohetes y satélites.",
"moat":"Cuota dominante en actuadores de precisión para espacio y defensa.",
"loc":"EE.UU.","country":"EEUU","growth":"🟢 +10%","margin":0.12,"founded":1951,"employees":13000,"revenue_2025":"~$3.3B","geo_risk":"EE.UU. — bajo"},

{"id":"MaxLinear","label":"MaxLinear","ticker":"MXL · Nasdaq","cat":"fabless","mkt":"MXL",
"role":"SoCs de demodulación satelital para terminales Starlink v3; líder en banda ancha satelital.",
"moat":"Diseños calificados directamente con SpaceX para terminales Starlink.",
"loc":"EE.UU.","country":"EEUU","growth":"🔵 +25%","margin":0.22,"founded":2003,"employees":1100,"revenue_2025":"~$500M","geo_risk":"EE.UU. — bajo"},

{"id":"SiTime","label":"SiTime","ticker":"SITS · Nasdaq","cat":"fabless","mkt":"SITS",
"role":"Osciladores MEMS de precisión para timing crítico en satélites LEO.",
"moat":"Líder en MEMS timing con >85% de cuota; único proveedor calificado en múltiples constelaciones LEO.",
"loc":"EE.UU.","country":"EEUU","growth":"🔵 +30%","margin":0.35,"founded":2005,"employees":280,"revenue_2025":"~$250M","geo_risk":"EE.UU. — bajo"},

{"id":"T_Mobile","label":"T-Mobile USA","ticker":"TMUS · Nasdaq","cat":"connectivity_infra","mkt":"TMUS",
"role":"Mayor operadora móvil de EE.UU.; socio de Starlink Direct-to-Cell ($12B acuerdo).",
"moat":"Único operador con cobertura DTC satelital masiva desde 2025.",
"loc":"EE.UU.","country":"EEUU","growth":"🟢 +8%","margin":0.2,"founded":1994,"employees":75000,"revenue_2025":"~$80B","geo_risk":"EE.UU. — bajo"},

{"id":"AST_SpaceMobile","label":"AST SpaceMobile","ticker":"ASTS · Nasdaq","cat":"satellite","mkt":"ASTS",
"role":"Red satelital Direct-to-Cell para smartphones estándar; BlueBird constellation 2026.",
"moat":"Único aprobado por FCC para DTC 4G/5G en smartphones estándar; acuerdos con 45+ operadoras.",
"loc":"EE.UU.","country":"EEUU","growth":"⚡ +200%","margin":-0.5,"founded":2017,"employees":850,"revenue_2025":"~$50M est","geo_risk":"EE.UU. — bajo"},

{"id":"Iridium","label":"Iridium Communications","ticker":"IRDM · Nasdaq","cat":"satellite","mkt":"IRDM",
"role":"Constelación LEO de 66 satélites; cobertura polar global; líder en IoT marítimo/aviation/defensa.",
"moat":"Única constelación con cobertura verdaderamente polar y global.",
"loc":"EE.UU.","country":"EEUU","growth":"🟢 +8%","margin":0.28,"founded":1991,"employees":1800,"revenue_2025":"~$800M","geo_risk":"EE.UU. — activo defensa estratégico"},

{"id":"Globalstar","label":"Globalstar","ticker":"GSAT · Nasdaq","cat":"satellite","mkt":"GSAT",
"role":"Constelación LEO; proveedor de Apple Emergency SOS y satellite messaging en iPhone 14+.",
"moat":"Contrato Apple de $1.5B prepagado asegura ingresos.",
"loc":"EE.UU.","country":"EEUU","growth":"🟢 +15%","margin":0.15,"founded":1991,"employees":800,"revenue_2025":"~$270M","geo_risk":"EE.UU. — bajo"},

{"id":"EutelsatOneWeb","label":"Eutelsat / OneWeb","ticker":"ETL · Euronext","cat":"satellite",
"role":"Constelación LEO OneWeb (648 sats) + flota GEO Eutelsat; competidor directo de Starlink en enterprise.",
"moat":"Respaldo gubernamental francés y británico; OneWeb ya tiene 648 sats en órbita.",
"loc":"Francia/UK","country":"Francia","growth":"🟡 +5%","margin":0.05,"founded":2019,"employees":1800,"revenue_2025":"~€1.5B","geo_risk":"Francia — bajo pero financieramente frágil"},

{"id":"Viasat","label":"Viasat","ticker":"VSAT · Nasdaq","cat":"satellite","mkt":"VSAT",
"role":"GEO HTS y aviation in-flight connectivity; ViaSat-3 en órbita.",
"moat":"Líder en aviation IFC con contratos plurianuales con aerolíneas.",
"loc":"EE.UU.","country":"EEUU","growth":"🟡 +3%","margin":0.07,"founded":1986,"employees":7800,"revenue_2025":"~$2.4B","geo_risk":"EE.UU. — defensa ITAR"},

{"id":"PlanetLabs","label":"Planet Labs","ticker":"PL · NYSE","cat":"earth_obs","mkt":"PL",
"role":"200+ satélites Dove/SkySat; imagen diaria de toda la Tierra; líder en EO comercial.",
"moat":"La mayor flota de satélites de observación del mundo; revisita diaria de cualquier punto.",
"loc":"EE.UU.","country":"EEUU","growth":"🟢 +18%","margin":-0.2,"founded":2010,"employees":900,"revenue_2025":"~$230M","geo_risk":"EE.UU. — ITAR (imágenes defensa)"},

{"id":"BlackSky","label":"BlackSky Technology","ticker":"BKSY · Nasdaq","cat":"earth_obs","mkt":"BKSY",
"role":"EO de alta revisita + AI analytics en 90 minutos desde el pedido.",
"moat":"Mayor cadencia de revisita del mercado; plataforma Spectra AI embebida.",
"loc":"EE.UU.","country":"EEUU","growth":"🟢 +22%","margin":-0.3,"founded":2014,"employees":300,"revenue_2025":"~$85M","geo_risk":"EE.UU. — ITAR"},

{"id":"ICEYE","label":"ICEYE","ticker":"Pre-IPO · Finlandia","cat":"earth_obs","preipo":true,
"role":"Líder en SAR (radar) todo-tiempo; imágenes 25cm en cualquier clima.",
"moat":"SAR penetra nubes y opera de noche — ventaja absoluta en insurance y defensa.",
"loc":"Finlandia","country":"RestoEuropa","growth":"⭐ PRE-IPO; +60% revenue","margin":-0.3,"founded":2014,"employees":600,"revenue_2025":"~$80M est","geo_risk":"Finlandia — aliada OTAN"},

{"id":"Kratos_Defense","label":"Kratos Defense & Security","ticker":"KTOS · Nasdaq","cat":"ai_defense","mkt":"KTOS",
"role":"Software de ground para satélites DoD y Starshield; drones kamikaze OpenWing.",
"moat":"Único proveedor de ground software calificado para Starshield (clasificado).",
"loc":"EE.UU.","country":"EEUU","growth":"🔵 +20%","margin":0.08,"founded":1994,"employees":4000,"revenue_2025":"~$1.1B","geo_risk":"EE.UU. — ITAR, defensa crítica"},

{"id":"AWS_Ground","label":"AWS Ground Station","ticker":"div. AMZN","cat":"cloud",
"role":"Ground-as-a-service: 12 estaciones globales para descargar datos de satélites en segundos.",
"moat":"Red de 12 antenas conectadas directamente a AWS backbone.",
"loc":"EE.UU.","country":"EEUU","growth":"🔵 +40%","founded":2018,"revenue_2025":"Parte de AWS $107B","geo_risk":"EE.UU. — bajo"},

{"id":"MP_Materials","label":"MP Materials","ticker":"MP · NYSE","cat":"rare_earth","mkt":"MP",
"role":"Única mina de tierras raras activa en EE.UU. (Mountain Pass, California); estratégica para defensa.",
"moat":"Único productor integrado de tierras raras en EE.UU.; soberanía total ante China.",
"loc":"EE.UU.","country":"EEUU","growth":"🔵 +35%","margin":0.08,"founded":2017,"employees":500,"revenue_2025":"~$300M","geo_risk":"EE.UU. — activo soberano estratégico"},

{"id":"Lynas","label":"Lynas Rare Earths","ticker":"LYC · ASX","cat":"rare_earth",
"role":"Segundo mayor productor de tierras raras fuera de China; procesa en Malasia y Texas.",
"moat":"Único productor de escala fuera de China capaz de suministrar a EE.UU. y Europa.",
"loc":"Australia/Malasia/EE.UU.","country":"RestoMundo","growth":"🔵 +25%","margin":0.15,"founded":2003,"employees":1500,"revenue_2025":"~$900M","geo_risk":"Australia — aliada pero exposición a Malasia","mkt":"LYC.AX"},

{"id":"Albemarle","label":"Albemarle","ticker":"ALB · NYSE","cat":"battery_mat","mkt":"ALB",
"role":"Mayor productor mundial de litio; insumo crítico para baterías de vehículos eléctricos y storage.",
"moat":"Tier 1 en litio con minas en Chile (Atacama), Australia y Nevada.",
"loc":"EE.UU.","country":"EEUU","growth":"🟡 +5%","margin":0.15,"founded":1994,"employees":8000,"revenue_2025":"~$5.4B","geo_risk":"EE.UU./Chile — riesgo político Chile bajo"},

{"id":"SQM","label":"SQM","ticker":"SQM · NYSE","cat":"battery_mat","mkt":"SQM",
"role":"Segundo mayor productor de litio; Salar de Atacama (Chile), el yacimiento más rico del mundo.",
"moat":"Costo de producción más bajo del mundo (Atacama $2-4/kg vs $8-15 avg).",
"loc":"Chile","country":"RestoMundo","growth":"🟡 +3%","margin":0.25,"founded":1968,"employees":7000,"revenue_2025":"~$4.0B","geo_risk":"Chile — riesgo regulatorio/político MEDIO"},

{"id":"Anduril","label":"Anduril Industries","ticker":"Pre-IPO ~$28B","cat":"ai_defense","preipo":true,
"role":"IA para defensa nacional: autonomía, drones, sensores. Palmer Luckey (Oculus). El 'SpaceX de defensa'.",
"moat":"Software-defined defense que corre en hardware commodity; el único contratista sin costos incrementales del Pentágono.",
"loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO ~$28B","margin":-0.1,"founded":2017,"employees":2500,"revenue_2025":"~$1B est","geo_risk":"EE.UU. — ITAR extremo"},

{"id":"ShieldAI","label":"Shield AI","ticker":"Pre-IPO ~$2.7B","cat":"ai_defense","preipo":true,
"role":"Piloto de IA para aeronaves militares (HIVEMIND); F-16 autónomo vs piloto humano.",
"moat":"HIVEMIND es el único piloto de IA que ha demostrado superar a pilotos humanos en combate simulado.",
"loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO","margin":-0.2,"founded":2015,"employees":800,"revenue_2025":"~$200M est","geo_risk":"EE.UU. — máximo secreto"},

{"id":"Mobileye","label":"Mobileye","ticker":"MBLY · Nasdaq","cat":"ai_auto","mkt":"MBLY",
"role":"Líder mundial en sistemas ADAS y chips EyeQ para conducción autónoma; 125M+ coches equipados.",
"moat":"125M+ coches con EyeQ = el mayor mapa de conducción real del mundo (REM).",
"loc":"Israel","country":"RestoMundo","growth":"🟢 +15%","margin":0.22,"founded":1999,"employees":4200,"revenue_2025":"~$1.9B","geo_risk":"Israel — riesgo regional ALTO"},

{"id":"AuroraInnovation","label":"Aurora Innovation","ticker":"AUR · Nasdaq","cat":"ai_auto","mkt":"AUR",
"role":"Software de conducción autónoma nivel 4; Aurora Driver en trucks comerciales.",
"moat":"El único con deployment comercial L4 en trucks en EE.UU.",
"loc":"EE.UU.","country":"EEUU","growth":"⚡ De 0 a revenue comercial 2024-25","margin":-2.0,"founded":2017,"employees":1600,"revenue_2025":"~$30M","geo_risk":"EE.UU. — regulación AV NHTSA"},

{"id":"Luminar","label":"Luminar Technologies","ticker":"LAZR · Nasdaq","cat":"ai_auto","mkt":"LAZR",
"role":"Lidar de largo alcance (250m) para autonomía Level 3-4; IRIS+ en Volvo EX90.",
"moat":"El único lidar en producción en masa en un OEM top (Volvo).",
"loc":"EE.UU.","country":"EEUU","growth":"🔵 +40%","margin":-1.5,"founded":2012,"employees":850,"revenue_2025":"~$100M","geo_risk":"EE.UU. — bajo"},

{"id":"TempusAI","label":"Tempus AI","ticker":"TEM · Nasdaq","cat":"ai_health","mkt":"TEM",
"role":"Mayor plataforma de IA para oncología; secuencia genómica + IA para decisiones clínicas.",
"moat":"La mayor base de datos clínico-genómica del mundo (200B+ data points, 1M+ patients).",
"loc":"EE.UU.","country":"EEUU","growth":"🔵 +30%","margin":-0.3,"founded":2015,"employees":3500,"revenue_2025":"~$700M","geo_risk":"EE.UU. — regulación FDA/HIPAA"},

{"id":"Recursion","label":"Recursion Pharmaceuticals","ticker":"RXRX · Nasdaq","cat":"ai_health","mkt":"RXRX",
"role":"Drug discovery con IA a escala industrial; la mayor base de datos de fenotipos celulares.",
"moat":"Impossible to replicate dataset (10+ years, $1B+ de inversión en microscopy). NVIDIA partnership.",
"loc":"EE.UU.","country":"EEUU","growth":"🔵 +25%","margin":-0.8,"founded":2013,"employees":1000,"revenue_2025":"~$80M","geo_risk":"EE.UU. — bajo"},

{"id":"AlphaSense","label":"AlphaSense","ticker":"Pre-IPO ~$4B","cat":"ai_finance","preipo":true,
"role":"IA para investigación financiera; el Bloomberg para analistas de buy-side.",
"moat":"1,600+ clientes enterprise incluyendo Goldman, JP Morgan, BlackRock.",
"loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO; +45% ARR anual","margin":-0.1,"founded":2011,"employees":1200,"revenue_2025":"~$500M est","geo_risk":"EE.UU. — bajo"},

{"id":"MSCI","label":"MSCI","ticker":"MSCI · NYSE","cat":"ai_finance","mkt":"MSCI",
"role":"Proveedor de índices, analytics y ESG data para $15T de activos bajo gestión.",
"moat":"El índice MSCI EM es el benchmark de $2T en ETFs — si MSCI lo cambia, los fondos DEBEN comprar/vender.",
"loc":"EE.UU.","country":"EEUU","growth":"🟢 +12%","margin":0.52,"founded":1998,"employees":4600,"revenue_2025":"~$2.5B","geo_risk":"EE.UU. — bajo"},

{"id":"ElevenLabs","label":"ElevenLabs","ticker":"Pre-IPO ~$3.3B","cat":"ai_agents","preipo":true,
"role":"Plataforma de síntesis de voz y agentes conversacionales de IA; THE voice layer del stack IA.",
"moat":"Calidad de voz líder con 29 idiomas; Conversational AI con tool calling.",
"loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO ~$3.3B; +300% YoY","margin":-0.2,"founded":2022,"employees":200,"revenue_2025":"~$100M est","geo_risk":"EE.UU. — bajo"},

{"id":"Cohere","label":"Cohere","ticker":"Pre-IPO ~$2.2B","cat":"ai_agents","preipo":true,
"role":"LLMs enterprise para empresas; el rival 'seguro' de OpenAI para el mercado B2B.",
"moat":"El único LLM con opción real de on-premise seguro para enterprise regulado.",
"loc":"Canadá","country":"RestoMundo","growth":"⭐ PRE-IPO","margin":-0.3,"founded":2019,"employees":600,"revenue_2025":"~$200M est","geo_risk":"Canadá — bajo"},

{"id":"ScaleAI","label":"Scale AI","ticker":"Pre-IPO ~$13.8B","cat":"ai_agents","preipo":true,
"role":"La fábrica de datos de entrenamiento de IA; todo modelo de IA frontera usa Scale.",
"moat":"Todos los labs frontera dependen de Scale para RLHF y data quality.",
"loc":"EE.UU.","country":"EEUU","growth":"⭐ PRE-IPO ~$13.8B","margin":0.1,"founded":2016,"employees":1000,"revenue_2025":"~$1.5B est","geo_risk":"EE.UU. — ITAR (DoD)"},

{"id":"Penguin_Solutions","label":"Penguin Solutions","ticker":"PENG · Nasdaq","cat":"hpc_super","mkt":"PENG",
"role":"Integradores de HPC y AI infrastructure para laboratorios nacionales y enterprise.",
"moat":"Relaciones de décadas con laboratorios nacionales; único integrador con clasificaciones DoE.",
"loc":"EE.UU.","country":"EEUU","growth":"🟢 +15%","margin":0.08,"founded":2001,"employees":1500,"revenue_2025":"~$600M","geo_risk":"EE.UU. — bajo"},

{"id":"FujitsuHPC","label":"Fugaku / Fujitsu","ticker":"6702 · TSE","cat":"hpc_super",
"role":"Fugaku: el supercomputador más rápido del mundo (ARM-based); Fujitsu como proveedor HPC Asia.",
"moat":"Arquitectura propietaria A64FX que combina CPU y HBM en el mismo package.",
"loc":"Japón","country":"Japon","growth":"🟡 +6%","margin":0.05,"founded":1935,"employees":130000,"revenue_2025":"~¥3.7T","geo_risk":"Japón — bajo"}

]; // FIN NODES_SPACEX
