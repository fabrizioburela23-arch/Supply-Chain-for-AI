// nodes/meta_fill.js — Fichas generadas para las 187 empresas sin metadata
// (2026-07-12, workflow de 26 agentes: 13 generadores + 13 verificadores
// cruzados). Solo rellena HUECOS: nunca pisa un dato existente de NODE_META.
// Datos aproximados marcados con ~. Regenerable con el workflow fill-company-meta.

var META_FILL = {
 "L3Harris": {
  "founded": 2019,
  "employees": 48000,
  "revenue_2025": "~$21.5B",
  "geo_risk": "Sede en Melbourne, Florida; ~75% de ingresos depende del presupuesto del DoD/gobierno de EEUU, con exposición a ciclos presupuestarios y demanda ligada a Ucrania/Indo-Pacífico.",
  "desc": "Contratista de defensa nacido de la fusión L3 Technologies + Harris (2019): comunicaciones tácticas, guerra electrónica, sensores espaciales y motores de cohetes (Aerojet Rocketdyne). Importa como integrador clave de electrónica militar y carga útil espacial que absorbe semiconductores y IA embarcada."
 },
 "CACI": {
  "founded": 1962,
  "employees": 25000,
  "revenue_2025": "~$8.6B",
  "geo_risk": "Sede en Reston/Arlington, Virginia; ~95% de ingresos proviene de contratos del gobierno federal de EEUU (defensa e inteligencia), riesgo concentrado en el ciclo presupuestario y shutdowns.",
  "desc": "Contratista de servicios tecnológicos para defensa e inteligencia de EEUU: guerra electrónica, señales (SIGINT), ciberoperaciones y modernización de TI. Importa como canal por el que la IA y el software entran en las agencias de inteligencia y el Pentágono."
 },
 "SentinelOne": {
  "founded": 2013,
  "employees": 2800,
  "revenue_2025": "~$1.0B",
  "geo_risk": "Sede en Mountain View (California) con raíces y R&D significativo en Israel; exposición al conflicto regional israelí y a la competencia feroz de CrowdStrike/Microsoft en EEUU.",
  "desc": "Ciberseguridad de endpoints con detección autónoma basada en IA (plataforma Singularity, XDR y data lake). Importa porque protege la infraestructura de empresas y gobiernos que sostienen la cadena de IA, y compite directamente con CrowdStrike."
 },
 "C3AI": {
  "founded": 2009,
  "employees": 1000,
  "revenue_2025": "~$390M (FY2025)",
  "geo_risk": "Sede en Redwood City, California; fuerte dependencia de contratos federales/defensa de EEUU y de la alianza histórica con Baker Hughes (petróleo y gas), con concentración de clientes elevada.",
  "desc": "Software de aplicaciones de IA empresarial (mantenimiento predictivo, cadena de suministro, defensa) fundada por Tom Siebel. Importa como una de las pocas plataformas puras de IA aplicada cotizadas, muy usada por DoD y energía."
 },
 "AmpereComputing": {
  "founded": 2017,
  "employees": 1500,
  "revenue_2025": "N/D privada (~$200M est.)",
  "geo_risk": "Sede en Santa Clara pero adquirida por SoftBank (Japón, acuerdo ~$6.5B anunciado en 2025) y fabricación dependiente de TSMC en Taiwán; cliente ancla Oracle concentra la demanda.",
  "desc": "Diseña CPUs de servidor basadas en Arm (AmpereOne) optimizadas para cloud e inferencia de IA, fundada por Renée James (ex-Intel). Importa como alternativa Arm a x86 en datacenters y pieza de la estrategia de silicio de SoftBank/Arm."
 },
 "Tenstorrent": {
  "founded": 2016,
  "employees": 800,
  "revenue_2025": "N/D privada (~$100M+ en contratos de licencias)",
  "geo_risk": "Origen en Toronto con HQ en Santa Clara; fabrica con Samsung Foundry y GlobalFoundries (menos dependencia de TSMC) y su capital viene de Samsung, Hyundai y Bezos, atándola a Corea/Japón.",
  "desc": "Chips de IA y IP RISC-V liderada por Jim Keller; licencia núcleos y vende aceleradores (Wormhole/Blackhole) como alternativa abierta a NVIDIA. Importa por su modelo de licenciamiento que siembra silicio de IA en terceros (LG, Hyundai, Japón/Rapidus)."
 },
 "dMatrix": {
  "founded": 2019,
  "employees": 300,
  "revenue_2025": "pre-revenue (Corsair en rampa inicial)",
  "geo_risk": "Sede en Santa Clara, fabricación en TSMC (Taiwán) y capital de Temasek (Singapur) y Microsoft M12; depende de que los hyperscalers adopten inferencia fuera de NVIDIA.",
  "desc": "Desarrolla aceleradores de inferencia de IA con cómputo digital en memoria y chiplets (plataforma Corsair), enfocados en LLMs con mejor coste/vatio que las GPU. Importa como apuesta especializada en el segmento de inferencia, el de mayor crecimiento."
 },
 "Esperanto": {
  "founded": 2014,
  "employees": 100,
  "revenue_2025": "pre-revenue / mínimos",
  "geo_risk": "Sede en Mountain View, California; startup pequeña dependiente de financiación privada y de TSMC, con informes en 2025 de repliegue de su negocio de silicio.",
  "desc": "Fundada por Dave Ditzel, diseñó el ET-SoC-1 con ~1.000 núcleos RISC-V de bajo consumo para inferencia de IA. Importa como pionera del RISC-V masivo para IA, aunque en 2025 se reportó que reducía/cerraba su desarrollo de chips."
 },
 "Viavi": {
  "founded": 2015,
  "employees": 3600,
  "revenue_2025": "~$1.1B (FY2025)",
  "geo_risk": "Sede en Chandler, Arizona (heredera de JDSU); expuesta al capex cíclico de telecos globales y a ventas/competencia en China, con parte de la manufactura en Asia.",
  "desc": "Test y medición de redes (5G, fibra, data centers) más pigmentos ópticos anti-falsificación, escindida de JDS Uniphase en 2015. Importa porque valida y monitoriza la infraestructura óptica y de red que interconecta los data centers de IA."
 },
 "AyarLabs": {
  "founded": 2015,
  "employees": 300,
  "revenue_2025": "pre-revenue (muestras y programas piloto)",
  "geo_risk": "Sede en San José, California; fabrica su fotónica con GlobalFoundries en EEUU (ventaja de resiliencia) y su cap table incluye a NVIDIA, AMD e Intel, lo que la ata al ecosistema americano.",
  "desc": "Chiplets de E/S óptica (TeraPHY) y fuentes de luz (SuperNova) que sacan datos del chip con luz en vez de cobre. Importa porque la interconexión óptica co-empaquetada es el cuello de botella clave para escalar clusters de IA, y NVIDIA/AMD/Intel son inversores."
 },
 "BrainChip": {
  "founded": 2004,
  "employees": 70,
  "revenue_2025": "~$1M (ingresos mínimos)",
  "geo_risk": "Cotiza en Australia (ASX) pero opera desde Laguna Hills, California; empresa micro-cap que depende de licenciatarios (MegaChips, Renesas) y de fundiciones asiáticas.",
  "desc": "Desarrolla Akida, procesador neuromórfico de ultra bajo consumo para IA en el borde (spiking neural networks), que licencia como IP. Importa como uno de los pocos jugadores neuromórficos comerciales cotizados, aunque con tracción comercial aún mínima."
 },
 "SpiNNcloud": {
  "founded": 2021,
  "employees": 40,
  "revenue_2025": "N/D privada (primeros sistemas entregados)",
  "geo_risk": "Spin-off de TU Dresden en Alemania, dentro del clúster 'Silicon Saxony'; depende de subvenciones europeas/alemanas y de clientes institucionales como Sandia Labs (EEUU).",
  "desc": "Comercializa SpiNNaker2, supercomputación neuromórfica basada en la arquitectura de Steve Furber con miles de núcleos Arm de bajo consumo para IA event-driven. Importa como la apuesta europea más avanzada en cómputo neuromórfico a escala."
 },
 "QTS": {
  "founded": 2003,
  "employees": 1500,
  "revenue_2025": "N/D privada (Blackstone; ~$1.5B est.)",
  "geo_risk": "Sede en Overland Park, Kansas, con campus en Virginia, Atlanta, Dallas y Phoenix; riesgo concentrado en la disponibilidad de energía en EEUU y en el apalancamiento de Blackstone.",
  "desc": "Operador de mega-campus de data centers comprado por Blackstone en 2021 (~$10B) y convertido en su mayor apuesta de infraestructura de IA, con decenas de GW en desarrollo. Importa como uno de los mayores caseros de los hyperscalers para cargas de IA."
 },
 "DataBank": {
  "founded": 2005,
  "employees": 800,
  "revenue_2025": "N/D privada (~$500M est.)",
  "geo_risk": "Sede en Dallas, Texas, con ~65 data centers solo en EEUU (mercados edge/secundarios); controlada por DigitalBridge con recapitalización de AustralianSuper, sensible a energía y tipos de interés.",
  "desc": "Colocation y data centers 'edge' en ciudades secundarias de EEUU, ahora expandiéndose a campus para IA/HPC. Importa porque acerca capacidad de inferencia y cómputo a mercados fuera de los grandes hubs, dentro del portafolio digital de DigitalBridge."
 },
 "Switch": {
  "founded": 2000,
  "employees": 1100,
  "revenue_2025": "N/D privada (~$1B est.)",
  "geo_risk": "Campus solo en EEUU (Las Vegas, Reno, Atlanta, Grand Rapids); dependencia del agua/energía de Nevada mitigada por 100% renovables, y propiedad de DigitalBridge/IFM tras salir de bolsa en 2022.",
  "desc": "Fundada por Rob Roy, opera mega-campus de data centers de altísima densidad (diseño Tier 5) comprados por DigitalBridge e IFM por ~$11B en 2022. Importa como proveedor premium de capacidad para IA con energía renovable dedicada en EEUU."
 },
 "Fastly": {
  "founded": 2011,
  "employees": 1300,
  "revenue_2025": "~$580M",
  "geo_risk": "Sede en San Francisco (EEUU) con red global de PoPs; negocio distribuido pero compite contra Cloudflare/Akamai y depende de clientes hiperescala concentrados.",
  "desc": "CDN y plataforma de edge computing (Compute@Edge) que acelera y protege el tráfico web de grandes plataformas. Importa como capa de entrega/inferencia en el borde para aplicaciones y APIs de IA."
 },
 "Edgio": {
  "founded": 2001,
  "revenue_2025": "N/D — en liquidación (Chapter 11 en 2024; clientes vendidos a Akamai, cesó operaciones CDN a inicios de 2025)",
  "geo_risk": "Empresa estadounidense efectivamente desaparecida; su quiebra consolidó aún más el mercado CDN en Akamai/Cloudflare, aumentando la concentración de la capa de entrega.",
  "desc": "Ex-Limelight Networks, CDN y servicios de edge/video que se declaró en bancarrota en 2024 y transfirió su base de clientes a Akamai. Relevante hoy sobre todo como caso de consolidación del sector CDN."
 },
 "Imperva": {
  "founded": 2002,
  "employees": 1500,
  "revenue_2025": "~$600M (consolidado dentro de Thales, no se reporta por separado)",
  "geo_risk": "Sede en California pero propiedad del grupo francés Thales desde 2023; fuerte herencia de I+D israelí, lo que la expone a la geopolítica de Israel y a prioridades de defensa europeas.",
  "desc": "Ciberseguridad de aplicaciones y datos: WAF, protección DDoS, seguridad de APIs y bases de datos. Protege la capa de aplicaciones/APIs sobre la que corren los servicios de IA; adquirida por Thales por ~$3.6B."
 },
 "Zscaler": {
  "founded": 2007,
  "employees": 8500,
  "revenue_2025": "~$2.7B (año fiscal 2025)",
  "geo_risk": "Sede en San José (EEUU) con centro grande de I+D en India e Israel; modelo cloud global con baja dependencia de hardware, pero expuesto a regulación de datos por país.",
  "desc": "Líder en seguridad Zero Trust en la nube (SASE/SSE): enruta e inspecciona todo el tráfico corporativo sin VPN. Es la capa de seguridad de acceso para empresas que adoptan SaaS e IA generativa."
 },
 "Mobileye": {
  "founded": 1999,
  "employees": 4300,
  "revenue_2025": "~$1.7B",
  "geo_risk": "Sede en Jerusalén (exposición directa al conflicto en Israel), controlada por Intel; ~un tercio de sus ingresos depende de OEMs chinos y sus chips EyeQ se fabrican en fundiciones externas (ST/TSMC).",
  "desc": "Pionera en visión por computador para conducción asistida y autónoma: sus chips EyeQ equipan a decenas de fabricantes de autos. Es el eslabón dominante de ADAS por cámara en la cadena de IA automotriz."
 },
 "Luminar": {
  "founded": 2012,
  "employees": 400,
  "revenue_2025": "~$70M",
  "geo_risk": "EEUU (Orlando), pero fabrica vía socios contract-manufacturing en México y Tailandia (Celestica/Fabrinet) y depende fuertemente del programa de Volvo; situación financiera frágil tras despidos masivos y salida de su fundador.",
  "desc": "Fabricante de lidar de largo alcance (1550 nm) para conducción autónoma, con Volvo como cliente ancla. Importa como apuesta occidental de lidar frente al dominio chino de Hesai/RoboSense, aunque en reestructuración."
 },
 "Waymo": {
  "founded": 2009,
  "employees": 2500,
  "revenue_2025": "N/D (dentro de Alphabet; ingresos de robotaxi aún incipientes, cientos de millones como mucho)",
  "geo_risk": "Filial de Alphabet en EEUU; su flota depende de vehículos extranjeros (Jaguar del Reino Unido, Zeekr/Geely de China — expuesta a aranceles a EVs chinos) y de sensores/cómputo propios.",
  "desc": "Líder mundial en robotaxis autónomos (ex proyecto de Google, spin-off en 2016), con servicio comercial sin conductor en Phoenix, San Francisco, LA y Austin. Es el mayor consumidor real de la pila completa de IA para conducción autónoma."
 },
 "Zoox": {
  "founded": 2014,
  "employees": 2500,
  "revenue_2025": "pre-revenue (lanzamiento comercial de robotaxi en Las Vegas en curso)",
  "geo_risk": "Propiedad de Amazon (EEUU) desde 2020; integración vertical alta pero dependiente de la cadena global de sensores y semiconductores para su vehículo diseñado desde cero.",
  "desc": "Robotaxi de Amazon: vehículo autónomo bidireccional diseñado desde cero, sin volante. Importa como la apuesta vertical de Amazon en movilidad autónoma frente a Waymo y Tesla."
 },
 "Hesai": {
  "founded": 2014,
  "employees": 1800,
  "revenue_2025": "~$400M",
  "geo_risk": "Sede en Shanghái; líder chino de lidar incluido en listas del Pentágono de empresas vinculadas al ejército chino (litigio en curso), muy expuesto a sanciones, aranceles y a la desconfianza de OEMs occidentales.",
  "desc": "Mayor fabricante mundial de lidar automotriz por volumen, proveedor de los principales EVs chinos y de flotas de robotaxis. Es el punto de concentración china en sensores para conducción autónoma."
 },
 "Cepton": {
  "founded": 2016,
  "employees": 130,
  "revenue_2025": "~$15M (ya dentro de Koito)",
  "geo_risk": "Empresa de San José adquirida en 2025 por el japonés Koito Manufacturing (su principal socio/accionista); dependía casi por completo de programas OEM vía Koito, en particular de General Motors.",
  "desc": "Desarrollador de lidar MMT de bajo costo para automoción, absorbido por Koito (mayor fabricante mundial de faros). Importa como vía japonesa para integrar lidar en la cadena de suministro automotriz tradicional."
 },
 "Tempus": {
  "founded": 2015,
  "employees": 2800,
  "revenue_2025": "~$1.2B (guía tras adquirir Ambry Genetics)",
  "geo_risk": "Sede en Chicago con negocio casi todo en EEUU; su riesgo es regulatorio (FDA, privacidad de datos clínicos) más que geopolítico, con dependencia de secuenciadores Illumina.",
  "desc": "Plataforma de medicina de precisión que combina secuenciación genómica con IA sobre una de las mayores bases de datos clínico-moleculares del mundo. Es el puente comercial más grande entre IA y oncología en EEUU."
 },
 "Recursion": {
  "founded": 2013,
  "employees": 600,
  "revenue_2025": "~$60M (hitos y colaboraciones farma; sin fármacos aprobados)",
  "geo_risk": "Sede en Salt Lake City con operaciones en Reino Unido tras fusionarse con Exscientia (2024); depende críticamente de GPUs NVIDIA (supercomputadora BioHive-2) y de capital paciente.",
  "desc": "Descubrimiento de fármacos con IA a escala industrial: cribado celular automatizado más modelos fundacionales biológicos, respaldada por NVIDIA. Es el referente cotizado de 'TechBio' y del uso masivo de cómputo en biología."
 },
 "Veracyte": {
  "founded": 2008,
  "employees": 1300,
  "revenue_2025": "~$490M",
  "geo_risk": "Sede en el sur de San Francisco; negocio concentrado en reembolsos de Medicare/aseguradoras de EEUU y en secuenciación dependiente de proveedores como Illumina; baja exposición geopolítica directa.",
  "desc": "Diagnósticos genómicos para cáncer (tiroides con Afirma, próstata con Decipher) que usan clasificadores de machine learning sobre expresión génica. Importa como caso maduro de IA diagnóstica ya reembolsada a escala."
 },
 "Butterfly": {
  "founded": 2011,
  "employees": 380,
  "revenue_2025": "~$90M",
  "geo_risk": "Sede en Massachusetts; su chip de ultrasonido-en-silicio se fabrica en fundición externa (TSMC), heredando la concentración de riesgo en Taiwán de todo el semiconductor avanzado.",
  "desc": "Creadora del Butterfly iQ, ecógrafo de bolsillo basado en un chip semiconductor (ultrasound-on-chip) con IA de guiado e interpretación. Democratiza la imagen médica y conecta la cadena de chips con la salud."
 },
 "PathAI": {
  "founded": 2016,
  "employees": 500,
  "revenue_2025": "N/D privada (vendió su negocio de laboratorio a Quest Diagnostics en 2024)",
  "geo_risk": "Privada con sede en Boston; tras vender sus laboratorios a Quest depende de acuerdos con farmacéuticas y grandes laboratorios de EEUU, con riesgo regulatorio FDA más que geopolítico.",
  "desc": "IA para patología digital: algoritmos que analizan biopsias para diagnóstico y ensayos clínicos farmacéuticos, ahora enfocada en software (AISight) tras vender su laboratorio a Quest. Es un nodo clave de la patología computacional."
 },
 "Insilico": {
  "founded": 2014,
  "employees": 500,
  "revenue_2025": "N/D privada (~$50-100M est.)",
  "geo_risk": "Sede dual Hong Kong/Nueva York con fuerte I+D en China continental; expuesta a restricciones EEUU-China sobre biotecnología e IA (BIOSECURE Act) y al escrutinio de capital estadounidense en biotech china.",
  "desc": "Pionera en descubrimiento de fármacos con IA generativa (plataforma Pharma.AI); llevó moléculas diseñadas por IA a ensayos clínicos de fase II. Importa como caso de uso insignia de la IA aplicada a salud y como puente (y punto de fricción) biotech entre EEUU y China."
 },
 "Adept": {
  "founded": 2022,
  "employees": 30,
  "revenue_2025": "pre-revenue",
  "geo_risk": "Sede en San Francisco; tras el acuerdo de 2024 en que Amazon contrató a sus fundadores y gran parte del equipo, quedó como empresa residual con licencia de su tecnología a Amazon.",
  "desc": "Startup de agentes de IA que buscaba automatizar flujos de trabajo en software empresarial (modelos que 'usan' el ordenador). Importa como precedente del patrón acqui-hire de las big tech: Amazon absorbió su talento en 2024 sin comprar la empresa."
 },
 "Inflection": {
  "founded": 2022,
  "employees": 100,
  "revenue_2025": "N/D privada (ingresos mínimos, pivote enterprise)",
  "geo_risk": "Sede en Palo Alto; tras la absorción de Mustafa Suleyman y la mayoría del equipo por Microsoft (2024) depende de licencias a Microsoft y de un pivote a IA empresarial, con vínculos de cómputo a Intel Gaudi.",
  "desc": "Creadora del chatbot Pi y de los modelos Inflection; llegó a valorarse en $4B con $1.3B levantados. Importa como el otro gran caso de vaciado por una big tech (Microsoft, 2024) y ejemplo de la consolidación del talento en labs frontera."
 },
 "Eutelsat": {
  "founded": 1977,
  "employees": 1700,
  "revenue_2025": "~$1.3B (~€1.2B)",
  "geo_risk": "Sede en París con constelación LEO OneWeb (Reino Unido/India como accionistas); es la apuesta soberana europea frente a Starlink, respaldada por el Estado francés, con exposición a decisiones políticas de la UE (IRIS²) y a lanzadores no propios.",
  "desc": "Operador satelital europeo que fusionó su flota GEO con la constelación LEO OneWeb (~650 satélites). Importa como única alternativa occidental operativa a Starlink en banda ancha LEO y pieza central de la conectividad soberana europea (Ucrania incluida)."
 },
 "SpireGlobal": {
  "founded": 2012,
  "employees": 400,
  "revenue_2025": "~$100M (tras vender el negocio marítimo a Kpler en 2025)",
  "geo_risk": "Sede en Virginia (EEUU) con operaciones en Escocia y Luxemburgo; depende de contratos gubernamentales (NOAA, defensa) y su salud financiera ha sido frágil (venta de activos para desapalancarse).",
  "desc": "Opera una constelación de nanosatélites (Lemur) que capta datos de radio-ocultación GNSS para clima, seguimiento de aviación y RF. Importa como proveedor de datos meteorológicos y de inteligencia espacial 'as a service' para gobiernos y agencias."
 },
 "HawkEye360": {
  "founded": 2015,
  "employees": 250,
  "revenue_2025": "N/D privada (~$50M est., mayoría contratos gob.)",
  "geo_risk": "Sede en Herndon, Virginia, junto al ecosistema de inteligencia de EEUU; ingresos concentrados en clientes de defensa/inteligencia de EEUU y aliados (Five Eyes, Ucrania), lo que la ata al ciclo presupuestario del Pentágono.",
  "desc": "Constelación de satélites que geolocaliza emisiones de radiofrecuencia (radares, GPS jamming, pesca ilegal, buques 'oscuros'). Importa porque el RF sensing comercial se volvió crítico para la inteligencia militar (Ucrania, mar de China Meridional)."
 },
 "Umbra": {
  "founded": 2015,
  "employees": 150,
  "revenue_2025": "N/D privada (decenas de $M, contratos NRO/DoD)",
  "geo_risk": "Sede en Santa Bárbara, California; fuerte dependencia de contratos de inteligencia/defensa de EEUU (NRO) y de licencias regulatorias NOAA para vender imágenes SAR de alta resolución.",
  "desc": "Fabrica y opera satélites SAR (radar de apertura sintética) con la resolución comercial más alta autorizada (~16 cm), vendiendo imágenes bajo modelo abierto. Importa porque el SAR ve de noche y a través de nubes: clave para vigilancia militar persistente."
 },
 "CapellaSpace": {
  "founded": 2016,
  "employees": 200,
  "revenue_2025": "N/D privada (adquirida por IonQ en 2025)",
  "geo_risk": "Sede en San Francisco; cliente-dependiente del gobierno de EEUU (SDA, NRO, Space Force) y desde 2025 integrada en IonQ para redes cuánticas espaciales, lo que la ata a la estrategia de esa empresa.",
  "desc": "Primer operador estadounidense de constelación SAR comercial (imágenes radar todo-tiempo bajo demanda). Importa por sus contratos de defensa/inteligencia y porque su compra por IonQ (2025) la convierte en plataforma para comunicaciones cuánticas por satélite."
 },
 "Lattice": {
  "founded": 1983,
  "employees": 1000,
  "revenue_2025": "~$550M",
  "geo_risk": "Sede en Hillsboro, Oregón, pero fabless: depende de fundiciones y ensamblaje en Taiwán/Asia (TSMC, UMC), con exposición directa a un conflicto en el estrecho de Taiwán; parte de sus FPGA van a defensa e industrial de EEUU.",
  "desc": "Líder en FPGAs de baja potencia y tamaño pequeño (familias Nexus, Avant) usadas en servidores de IA (gestión/seguridad de placa), automoción, industrial y defensa. Importa como el 'pegamento' programable de bajo consumo en casi todo servidor y sistema embebido."
 },
 "MaxLinear": {
  "founded": 2003,
  "employees": 1500,
  "revenue_2025": "~$400M (recuperándose del ciclo bajo 2023-24)",
  "geo_risk": "Sede en Carlsbad, California, fabless con manufactura en Taiwán/Asia; exposición a Taiwán y litigio arrastrado por la compra fallida de Silicon Motion (Taiwán) que China condicionó en 2023.",
  "desc": "Fabless de mixed-signal/RF: SoCs de banda ancha (cable, fibra PON), WiFi, backhaul inalámbrico y DSPs ópticos (Keystone) para interconexión de datacenters de IA de 800G. Importa por su apuesta en óptica para el cableado de clusters de IA."
 },
 "SiliconLabs": {
  "founded": 1996,
  "employees": 1700,
  "revenue_2025": "~$750M",
  "geo_risk": "Sede en Austin, Texas, fabless con dependencia de TSMC (Taiwán) para wafers y de OSATs asiáticos; mercado IoT muy expuesto a la demanda de consumo y a aranceles EEUU-China.",
  "desc": "Especialista en SoCs inalámbricos de bajo consumo para IoT (Zigbee, Thread/Matter, Bluetooth, sub-GHz) con las series EFR32. Importa como habilitador del edge conectado: hogares inteligentes, medidores, industrial — la periferia donde aterriza la IA embebida."
 },
 "Wolfspeed": {
  "founded": 1987,
  "employees": 4000,
  "revenue_2025": "~$750M (FY2025; salió de Chapter 11 en 2025)",
  "geo_risk": "Sede en Durham, Carolina del Norte, con fabs propias en EEUU (Mohawk Valley, Siler City) — baja exposición a Taiwán pero alta a la competencia china en SiC (precios) y a su propia crisis financiera: pasó por Chapter 11 en 2025 pese a fondos CHIPS Act.",
  "desc": "Mayor fabricante occidental de carburo de silicio (SiC): sustratos, wafers de 200 mm y dispositivos de potencia para vehículos eléctricos, energía y datacenters. Importa porque el SiC es el material clave de la electrónica de potencia y Wolfspeed es la apuesta de EEUU por no cederlo a China."
 },
 "EdgeImpulse": {
  "founded": 2019,
  "employees": 130,
  "revenue_2025": "N/D (adquirida por Qualcomm en marzo 2025)",
  "geo_risk": "Sede en San José, California; tras la adquisición por Qualcomm su destino queda atado a la estrategia edge-AI de Qualcomm y a las tensiones EEUU-China que afectan a su matriz.",
  "desc": "Plataforma de desarrollo de machine learning para dispositivos embebidos (TinyML): permite entrenar y desplegar modelos en MCUs y sensores sin ser experto. Importa como capa de software que democratiza la IA en el edge; Qualcomm la compró para su stack IoT/edge."
 },
 "MP_Materials": {
  "founded": 2017,
  "employees": 900,
  "revenue_2025": "~$250M (creciendo con imanes y acuerdo DoD)",
  "geo_risk": "Opera Mountain Pass (California), la única mina de tierras raras a escala de EEUU; históricamente dependía de refinado/clientes chinos (Shenghe), dependencia que rompe con el acuerdo DoD de 2025 (participación estatal, precio suelo de NdPr y fábrica de imanes 10X).",
  "desc": "Única cadena mina-a-imán de tierras raras integrada en EEUU: extrae NdPr en Mountain Pass y fabrica imanes en Texas (cliente ancla GM, y desde 2025 el Pentágono y Apple). Importa porque los imanes de neodimio son insumo crítico de motores de EVs, robots humanoides, drones y armamento, hoy dominado ~90% por China."
 },
 "Lynas": {
  "founded": 1983,
  "employees": 1200,
  "revenue_2025": "~$370M (~A$560M FY2025)",
  "geo_risk": "Minera australiana (Mt Weld) con su refinería principal en Malasia — mayor procesador de tierras raras FUERA de China; presión regulatoria malasia sobre residuos radiactivos y nueva planta de pesados en Texas financiada por el DoD de EEUU.",
  "desc": "Mayor productor de tierras raras separadas fuera de China (NdPr para imanes; en 2025 empezó a producir disprosio/terbio pesados fuera de China por primera vez). Importa como el contrapeso occidental clave al monopolio chino de refinado, con respaldo de Australia, Japón (JARE/Sojitz) y EEUU."
 },
 "EnergyFuels": {
  "founded": 1987,
  "employees": 500,
  "revenue_2025": "~$80-100M",
  "geo_risk": "Sede en Colorado con activos en Utah/Arizona; es la apuesta de EEUU para independizarse de China en tierras raras y de Rusia/Kazajistán en uranio, pero su escala es aún pequeña frente a los procesadores chinos.",
  "desc": "Productor estadounidense de uranio y única empresa de EEUU procesando tierras raras (NdPr) a escala comercial en su planta White Mesa (Utah). Importa por el renacimiento nuclear ligado a datacenters de IA y por la cadena de imanes fuera de China."
 },
 "Albemarle": {
  "founded": 1994,
  "employees": 7000,
  "revenue_2025": "~$5B",
  "geo_risk": "Sede en Charlotte (EEUU) pero depende de salmueras en Chile (Atacama, contrato con CORFO), minas en Australia y conversión parcial en China; muy expuesta al ciclo de precios del litio dominado por oferta china.",
  "desc": "Mayor productor occidental de litio (además de bromo y catalizadores), insumo clave de las baterías para EVs, almacenamiento de red y respaldo de datacenters. Su salud financiera marca el pulso de la cadena de materiales de baterías fuera de China."
 },
 "RocketLab": {
  "founded": 2006,
  "employees": 2600,
  "revenue_2025": "~$570M",
  "geo_risk": "HQ en Long Beach (California) con plataforma de lanzamiento principal en Nueva Zelanda; fuerte dependencia de contratos del gobierno/defensa de EEUU (Space Force, NRO) que a la vez le da colchón geopolítico.",
  "desc": "Lanzador líder de cohetes pequeños (Electron) y fabricante de componentes/satélites (Space Systems); desarrolla el cohete mediano reutilizable Neutron para competir con SpaceX. Es el segundo lanzador estadounidense por frecuencia de vuelos."
 },
 "ULA": {
  "founded": 2006,
  "employees": 2700,
  "revenue_2025": "~$2B (privada, JV Boeing/Lockheed)",
  "geo_risk": "Joint venture 50/50 de Boeing y Lockheed Martin en Colorado; casi todo su negocio depende de lanzamientos de seguridad nacional de EEUU y del contrato Kuiper de Amazon; ya no depende de motores rusos (RD-180) tras migrar a Vulcan con motores BE-4 de Blue Origin.",
  "desc": "Lanzador histórico de cargas de seguridad nacional de EEUU (Atlas V, Delta IV, ahora Vulcan Centaur). Importa como segunda vía de acceso al espacio del Pentágono frente a SpaceX y como lanzador principal de la constelación Kuiper de Amazon."
 },
 "RelativitySpace": {
  "founded": 2015,
  "employees": 1100,
  "revenue_2025": "pre-revenue",
  "geo_risk": "Sede en Long Beach (California); depende de capital privado (Eric Schmidt tomó el control como CEO/inversor principal en 2025) y de que Terran R vuele antes de quemar caja; riesgo de ejecución más que geopolítico.",
  "desc": "Startup de lanzadores que apuesta por impresión 3D masiva de cohetes; retiró el pequeño Terran 1 tras un solo vuelo (2023) para concentrarse en el cohete mediano reutilizable Terran R. Candidata a tercera opción de lanzamiento pesado-medio en EEUU."
 },
 "Allegro": {
  "founded": 1990,
  "employees": 4300,
  "revenue_2025": "~$750M (FY2025)",
  "geo_risk": "Sede en New Hampshire pero con ensamblaje/test concentrado en Filipinas y lazos históricos con la japonesa Sanken (aún accionista relevante); muy expuesta al ciclo automotriz global y a fabricación asiática.",
  "desc": "Fabless de sensores magnéticos (efecto Hall, TMR) y chips de potencia para automoción e industria: detección de corriente y posición en EVs, ADAS y robótica. Es proveedor clave del contenido creciente de semiconductores por vehículo."
 },
 "Ceva": {
  "founded": 2002,
  "employees": 450,
  "revenue_2025": "~$110M",
  "geo_risk": "Sede operativa e I+D principal en Israel (riesgo de conflicto regional), cotiza en EEUU; sus regalías dependen de volúmenes de clientes en China y Asia, sensibles a restricciones de exportación.",
  "desc": "Licenciante de IP de semiconductores: DSPs, NPUs de IA en el borde, Bluetooth, Wi-Fi y UWB que otros integran en sus SoCs. Importa porque sus núcleos están en miles de millones de dispositivos conectados, al estilo 'Arm de la conectividad y el edge AI'."
 },
 "Indie": {
  "founded": 2007,
  "employees": 1200,
  "revenue_2025": "~$230M",
  "geo_risk": "HQ en Aliso Viejo (California) con diseño distribuido en Europa/Asia y dependencia de foundries asiáticas (TSMC y otras); expuesta al ciclo de inventarios automotriz y a aranceles EEUU-China en autos.",
  "desc": "Fabless 'autotech' centrada en ADAS (radar, visión, lidar), ultrasonido y electrónica de experiencia de usuario para automóviles. Importa como apuesta pure-play al aumento de semiconductores por vehículo en la conducción asistida."
 },
 "PhysicalIntelligence": {
  "founded": 2024,
  "employees": 100,
  "revenue_2025": "pre-revenue",
  "geo_risk": "Startup de San Francisco financiada por Jeff Bezos, OpenAI, Thrive y Lux entre otros; su riesgo es de capital y talento más que geopolítico, aunque el hardware robótico donde corre su software depende de cadenas de suministro asiáticas.",
  "desc": "Laboratorio fundado por exinvestigadores de Google DeepMind y Stanford (Hausman, Levine, Finn) que construye modelos fundacionales para robots (familia π0), hardware-agnósticos. Es una de las apuestas centrales de la tesis 'IA física': el software cerebral para cualquier robot."
 },
 "Runway": {
  "founded": 2018,
  "employees": 250,
  "revenue_2025": "~$100M+ ARR (est., privada)",
  "geo_risk": "Sede en Nueva York; depende de cómputo de nube (GPUs NVIDIA) y enfrenta riesgo competitivo (Sora de OpenAI, Veo de Google) y legal por derechos de autor de datos de entrenamiento, más que riesgo geográfico.",
  "desc": "Pionera en generación de video por IA (modelos Gen-3/Gen-4) usada en cine, publicidad y creadores. Importa como demandante intensiva de GPUs y como referente de la capa de aplicaciones creativas sobre la infraestructura de IA."
 },
 "Perplexity": {
  "founded": 2022,
  "employees": 800,
  "revenue_2025": "~$150M ARR (est., privada)",
  "geo_risk": "Sede en San Francisco; depende de modelos y cómputo de terceros (NVIDIA es inversor) y desafía frontalmente a Google en búsqueda, con riesgo legal de editores por uso de contenido.",
  "desc": "Motor de búsqueda/respuestas con IA que compite con Google combinando LLMs y web en tiempo real; valorada en ~$14-18B en rondas de 2025. Importa como el retador más visible en la capa de búsqueda con IA y gran consumidor de inferencia."
 },
 "Glean": {
  "founded": 2019,
  "employees": 1000,
  "revenue_2025": "~$100-150M ARR (est., privada)",
  "geo_risk": "Sede en Palo Alto, fundada por exingenieros de Google; riesgo principal competitivo (Microsoft Copilot, OpenAI enterprise) más que geopolítico, con clientela concentrada en grandes empresas de EEUU.",
  "desc": "Plataforma de búsqueda y agentes de IA empresarial que indexa todas las apps internas de una compañía (RAG corporativo). Importa como caso de uso insignia de la IA generativa en la empresa; valorada en ~$7B en 2025."
 },
 "Cohere": {
  "founded": 2019,
  "employees": 450,
  "revenue_2025": "~$100M ARR (est., privada)",
  "geo_risk": "Sede realmente en Toronto (Canadá, no EEUU), con fuerte respaldo del gobierno canadiense y de NVIDIA/Oracle/Fujitsu; se posiciona como alternativa 'soberana' y desplegable on-premise frente a los labs estadounidenses.",
  "desc": "Laboratorio de LLMs enfocado en empresa y gobiernos (modelos Command, embeddings, plataforma North), cofundado por Aidan Gomez, coautor del paper 'Attention Is All You Need'. Importa como la gran apuesta de IA soberana de Canadá, valorada en ~$7B en 2025."
 },
 "Viasat": {
  "founded": 1986,
  "employees": 7000,
  "revenue_2025": "~$4.5B (FY2025)",
  "geo_risk": "Sede en Carlsbad (California) con huella global tras comprar la británica Inmarsat (2023); alta carga de deuda y presión competitiva directa de Starlink en banda ancha aérea, marítima y residencial.",
  "desc": "Operador de satélites GEO de banda ancha (ViaSat-3) y comunicaciones seguras para defensa y aviación. Importa como pilar de conectividad gubernamental/militar de EEUU y contrapeso GEO frente a las constelaciones LEO."
 },
 "Iridium": {
  "founded": 2001,
  "employees": 800,
  "revenue_2025": "~$860M",
  "geo_risk": "Sede en Virginia (EEUU) con cobertura global gracias a 66 satélites LEO de enlace cruzado; alta dependencia de clientes de defensa de EEUU y competencia creciente de direct-to-device (Starlink/Apple-Globalstar).",
  "desc": "Única constelación LEO con cobertura verdaderamente global (polos incluidos) para voz y datos vía satélite, crítica para el Pentágono, aviación y marítimo, y con negocio creciente de IoT y PNT alternativo al GPS."
 },
 "SiliconMotion": {
  "founded": 1995,
  "employees": 1600,
  "revenue_2025": "~$900M",
  "geo_risk": "Sede operativa en Taiwán (fabless, fabrica en TSMC): exposición directa al riesgo del estrecho de Taiwán y a controles de exportación EEUU-China, con parte relevante de clientes en China.",
  "desc": "Diseñador fabless líder mundial en controladores para memoria NAND flash y SSD, que vende a Samsung, SK hynix, Micron y fabricantes de módulos. Sus controladores son el 'cerebro' de gran parte del almacenamiento flash del mercado, pieza silenciosa pero crítica de la cadena."
 },
 "Ichor": {
  "founded": 1999,
  "employees": 2500,
  "revenue_2025": "~$900M",
  "geo_risk": "Sede en Fremont, California, con manufactura en EEUU, Singapur, Malasia y México; su suerte depende casi por completo del capex de Applied Materials y Lam Research (clientes que concentran la mayoría de sus ventas).",
  "desc": "Fabrica subsistemas de entrega de fluidos y gases ultrapuros para las herramientas de fabricación de chips (grabado, deposición). Es proveedor crítico de segundo nivel: sin sus módulos, los equipos de Lam y Applied no se ensamblan."
 },
 "Axcelis": {
  "founded": 1978,
  "employees": 1500,
  "revenue_2025": "~$800M",
  "geo_risk": "Sede en Massachusetts; alta exposición a China (que llegó a ser ~40-50% de ventas por fabs de nodos maduros), lo que la hace muy sensible a controles de exportación de EEUU.",
  "desc": "Uno de los dos grandes fabricantes mundiales de implantadores de iones (junto a Applied Materials), paso esencial para dopar silicio. Fuerte en carburo de silicio (SiC) y nodos maduros para potencia y automoción."
 },
 "Veeco": {
  "founded": 1945,
  "employees": 1200,
  "revenue_2025": "~$700M",
  "geo_risk": "Sede en Nueva York; ventas históricamente concentradas en Asia (China, Taiwán, Corea), por lo que los controles de exportación a China recortan parte de su mercado direccionable.",
  "desc": "Fabrica equipos de deposición y procesado especializados: recocido láser (laser annealing) para nodos avanzados, MOCVD para fotónica/LED y deposición por haz de iones para blancos EUV. Nicho pero crítico en varios pasos del proceso."
 },
 "AdvancedEnergy": {
  "founded": 1981,
  "employees": 9500,
  "revenue_2025": "~$1.7B",
  "geo_risk": "Sede en Denver, Colorado, con fuerte manufactura en Asia (Malasia, Filipinas, China, México); expuesta al ciclo de capex de semiconductores y a la relocalización de cadenas fuera de China.",
  "desc": "Líder en fuentes de potencia RF y DC de precisión que encienden y controlan los plasmas en grabado y deposición de chips, además de alimentación para data centers. Su electrónica de potencia está dentro de las herramientas de casi todos los grandes fabricantes de equipos."
 },
 "Azenta": {
  "founded": 1978,
  "employees": 3000,
  "revenue_2025": "~$650M",
  "geo_risk": "Sede en Massachusetts; en 2022 vendió su negocio de automatización de semiconductores a THL, así que hoy su exposición es más a ciencias de la vida que a la cadena de chips, con operaciones en EEUU, Europa y China.",
  "desc": "Antigua Brooks Automation: fue proveedor clave de robótica de vacío y automatización para fabs antes de pivotar a gestión de muestras biológicas y servicios genómicos para farma. Importa hoy más como legado/vecino de la cadena que como proveedor activo de semis."
 },
 "ExtremeNetworks": {
  "founded": 1996,
  "employees": 2800,
  "revenue_2025": "~$1.2B",
  "geo_risk": "Sede en EEUU (Morrisville, NC); depende de contract manufacturers en Asia para su hardware y compite contra Cisco/HPE-Juniper y Huawei en mercados globales.",
  "desc": "Proveedor de networking empresarial (switches, WiFi, gestión en la nube) de segundo escalón tras Cisco y HPE. Relevante en la capa de conectividad de campus y edge, cada vez más con gestión asistida por IA."
 },
 "Databricks": {
  "founded": 2013,
  "employees": 8000,
  "revenue_2025": "~$4B ARR (privada)",
  "geo_risk": "Sede en San Francisco; corre sobre los tres hyperscalers (AWS, Azure, GCP), de cuya capacidad de GPU depende, con riesgo regulatorio bajo pero exposición al ciclo de gasto en IA empresarial.",
  "desc": "Plataforma de datos e IA ('lakehouse') creada por los autores de Apache Spark; una de las startups privadas más valiosas del mundo (valoración >$100B en 2025). Es la capa donde miles de empresas preparan datos y entrenan/despliegan modelos, gran consumidora indirecta de GPUs."
 },
 "Confluent": {
  "founded": 2014,
  "employees": 3000,
  "revenue_2025": "~$1.1B",
  "geo_risk": "Sede en Mountain View, California; negocio de software global con baja exposición geopolítica directa, dependiente de los hyperscalers donde corre su nube.",
  "desc": "Empresa fundada por los creadores de Apache Kafka; su plataforma de streaming de datos en tiempo real es la 'tubería' por la que fluyen eventos hacia aplicaciones y modelos de IA. Pieza de infraestructura de datos crítica para casos de uso en tiempo real."
 },
 "HashiCorp": {
  "founded": 2012,
  "employees": 2400,
  "revenue_2025": "~$700M (dentro de IBM)",
  "geo_risk": "Sede en San Francisco, adquirida por IBM (~$6.4B, cerrado en 2025); su riesgo ya es el de integración corporativa dentro de IBM más que geopolítico.",
  "desc": "Creadora de Terraform y Vault, estándares de facto para provisionar infraestructura en la nube como código y gestionar secretos. Herramienta ubicua con la que se despliega gran parte de la infraestructura cloud que sostiene la IA."
 },
 "CharacterAI": {
  "founded": 2021,
  "employees": 200,
  "revenue_2025": "~$30-50M (privada)",
  "geo_risk": "Sede en Menlo Park, California; en 2024 Google licenció su tecnología y recontrató a sus fundadores (Noam Shazeer), dejando a la empresa con riesgo de dependencia estratégica de Google y escrutinio regulatorio por seguridad de menores.",
  "desc": "Startup de chatbots de compañía/entretenimiento fundada por coautores del paper de Transformers; llegó a ser una de las apps de IA de consumo con más uso. Importa como caso de demanda de inferencia masiva de consumo y como talento absorbido de vuelta por Google."
 },
 "BAESystems": {
  "founded": 1999,
  "employees": 107000,
  "revenue_2025": "~$38B",
  "geo_risk": "Sede en Reino Unido con enorme negocio en EEUU (via BAE Inc.); beneficiaria directa del rearme europeo y de la OTAN, con cartera de pedidos récord ligada a Ucrania y presupuestos de defensa crecientes.",
  "desc": "Mayor contratista de defensa de Europa: buques, submarinos nucleares (AUKUS), Eurofighter/F-35, municiones, guerra electrónica y una de las pocas fabs de chips rad-hard vía BAE en EEUU. Nodo central de la cadena de defensa occidental y de la electrónica militar."
 },
 "Rheinmetall": {
  "founded": 1889,
  "employees": 40000,
  "revenue_2025": "~$13B (≈€12B)",
  "geo_risk": "Sede en Düsseldorf, Alemania; el mayor beneficiario del rearme alemán/europeo (Zeitenwende) y del suministro a Ucrania, con expansión agresiva de plantas de municiones en Europa; expuesta a decisiones presupuestarias de Berlín y la UE.",
  "desc": "Fabricante alemán de municiones, blindados (Leopard 2, Panther), artillería y electrónica de defensa, en crecimiento explosivo desde 2022. Es la pieza industrial clave del rearme europeo y cada vez integra más IA/autonomía en sus sistemas."
 },
 "Innoviz": {
  "founded": 2016,
  "employees": 350,
  "revenue_2025": "~$40M",
  "geo_risk": "Sede en Israel (fundada por exmilitares de la unidad 81): exposición al riesgo de seguridad regional israelí y dependencia de programas de automoción de largo plazo (BMW, VW) con volúmenes aún inciertos.",
  "desc": "Fabricante israelí de LiDAR de estado sólido para conducción autónoma, con diseños ganados en BMW y el grupo VW/Mobileye. Importa como uno de los pocos proveedores de LiDAR automotriz-grade que sobrevivió a la consolidación del sector."
 },
 "Nuro": {
  "founded": 2016,
  "employees": 900,
  "revenue_2025": "pre-revenue (ingresos mínimos, privada)",
  "geo_risk": "Sede en Mountain View, California; opera solo en EEUU y depende de capital de riesgo (valorada ~$6B en 2025) y de regulación estatal de vehículos autónomos.",
  "desc": "Startup de vehículos autónomos fundada por exingenieros de Google/Waymo; empezó con robots de reparto y pivotó a licenciar su 'Nuro Driver' (stack de conducción autónoma con IA) a automotrices y flotas. Relevante como proveedor independiente de autonomía nivel 4 y consumidor de chips NVIDIA."
 },
 "Exscientia": {
  "founded": 2012,
  "employees": 400,
  "revenue_2025": "~$25-30M (colaboraciones; absorbida por Recursion en nov-2024)",
  "geo_risk": "Sede en Oxford (Reino Unido); tras fusionarse con Recursion (EEUU) su exposición pasa a depender del capital biotech estadounidense y de socios farma globales.",
  "desc": "Pionera británica en descubrimiento de fármacos con IA; fue la primera en llevar moléculas diseñadas por IA a ensayos clínicos. En 2024 se fusionó con Recursion Pharmaceuticals, consolidando el sector de IA aplicada a farma."
 },
 "BenevolentAI": {
  "founded": 2013,
  "employees": 120,
  "revenue_2025": "~£5-10M (colaboraciones, ej. AstraZeneca)",
  "geo_risk": "Sede en Londres, cotiza en Euronext Ámsterdam; muy dependiente del apetito europeo por biotech-IA, que se enfrió tras su SPAC, forzando recortes masivos.",
  "desc": "Plataforma británica de descubrimiento de fármacos con IA basada en grafos de conocimiento biomédico. Importa como caso de estudio del ciclo hype-corrección en IA-farma: tras salir por SPAC en 2022 recortó gran parte de plantilla y pivotó a licenciar su plataforma."
 },
 "VirtuFinancial": {
  "founded": 2008,
  "employees": 1900,
  "revenue_2025": "~$3B (ingresos totales de trading)",
  "geo_risk": "Sede en Nueva York; su riesgo es más regulatorio (SEC, reglas de market-making y PFOF) que geopolítico, con operaciones en mercados globales.",
  "desc": "Uno de los mayores creadores de mercado electrónicos del mundo, con trading de alta frecuencia impulsado por algoritmos y baja latencia. Importa como gran consumidor de infraestructura de cómputo y redes ultrarrápidas aplicadas a finanzas."
 },
 "LangChain": {
  "founded": 2022,
  "employees": 100,
  "revenue_2025": "N/D privada (~$12-16M ARR est.)",
  "geo_risk": "Sede en San Francisco; riesgo bajo geopolíticamente pero alto de plataforma: depende de que los LLMs de OpenAI/Anthropic/Google no absorban su capa de orquestación.",
  "desc": "Creadora del framework open-source más usado para construir aplicaciones y agentes sobre LLMs (LangChain, LangGraph, LangSmith). Es la capa de 'pegamento' estándar entre modelos, datos y herramientas en el stack de agentes de IA."
 },
 "Cloudflare": {
  "founded": 2009,
  "employees": 4500,
  "revenue_2025": "~$2.1B",
  "geo_risk": "Sede en San Francisco con red en 300+ ciudades; expuesta a fragmentación regulatoria de internet (soberanía de datos UE, bloqueos en China/Rusia) más que a una sola geografía.",
  "desc": "Red global de CDN, seguridad y edge computing que ahora despliega GPUs para inferencia de IA en el borde (Workers AI). Importa porque acerca la inferencia al usuario final y es infraestructura crítica de gran parte del tráfico web mundial."
 },
 "Akamai": {
  "founded": 1998,
  "employees": 10500,
  "revenue_2025": "~$4.1B",
  "geo_risk": "Sede en Cambridge, Massachusetts; red distribuida globalmente que diluye el riesgo país, con exposición regulatoria en mercados donde opera (UE, Asia).",
  "desc": "Veterana del CDN que pivota hacia seguridad cloud y cómputo distribuido (compró Linode), incluyendo inferencia de IA en el edge. Importa como una de las mayores redes de entrega de contenido y capa de defensa DDoS de internet."
 },
 "LambdaLabs": {
  "founded": 2012,
  "employees": 500,
  "revenue_2025": "~$500M-700M (est.)",
  "geo_risk": "Sede en San José, California; dependencia extrema del suministro de GPUs NVIDIA y de financiación apalancada en esos chips, sensible a controles de exportación de EEUU.",
  "desc": "Neocloud de GPUs (nube especializada en entrenamiento e inferencia de IA) y vendedor de estaciones/servidores con GPUs NVIDIA. Importa como uno de los principales challengers de los hyperscalers en cómputo de IA, junto a CoreWeave."
 },
 "Firefly": {
  "founded": 2014,
  "employees": 750,
  "revenue_2025": "~$100M (est.)",
  "geo_risk": "Sede en Cedar Park, Texas; cliente clave del gobierno de EEUU (NASA CLPS, Space Force), lo que la ata al presupuesto de defensa/espacio estadounidense; pasó por reestructuración por su antiguo inversor ucraniano por presión de CFIUS.",
  "desc": "Lanzadora espacial del cohete Alpha y del módulo lunar Blue Ghost, que logró el primer alunizaje comercial totalmente exitoso en marzo de 2025; salió a bolsa (NASDAQ: FLY) en agosto de 2025. Importa en el acceso responsivo al espacio y la economía lunar."
 },
 "StokSpace": {
  "founded": 2019,
  "employees": 350,
  "revenue_2025": "pre-revenue (contratos gubernamentales iniciales)",
  "geo_risk": "Sede en Kent, Washington; depende de contratos de la Space Force (seleccionada para NSSL Lane 1) y del capital riesgo espacial de EEUU.",
  "desc": "Desarrolla Nova, un cohete 100% reutilizable (ambas etapas) con segunda etapa de escudo térmico regenerativo, fundada por ex-Blue Origin. Importa porque la reutilización total bajaría radicalmente el costo de acceso a órbita."
 },
 "Agility": {
  "founded": 2015,
  "employees": 350,
  "revenue_2025": "N/D privada (ingresos iniciales por pilotos con GXO/Schaeffler)",
  "geo_risk": "Sede en Oregón con fábrica propia (RoboFab, ~10.000 unidades/año de capacidad); fabricación en EEUU la protege de aranceles pero compite contra humanoides chinos (Unitree) mucho más baratos.",
  "desc": "Creadora de Digit, el humanoide bípedo más avanzado en despliegue logístico real (almacenes de GXO, pruebas con Amazon). Importa como referente occidental de robótica física comercializada, no solo demos."
 },
 "Datadog": {
  "founded": 2010,
  "employees": 6000,
  "revenue_2025": "~$3.2B",
  "geo_risk": "Sede en Nueva York con fuerte ingeniería en París; ingresos diversificados globalmente, riesgo principal es competitivo (hyperscalers) y de concentración de clientes IA-nativos.",
  "desc": "Plataforma líder de observabilidad y monitoreo de infraestructura cloud, ahora con productos de monitoreo de LLMs (LLM Observability). Importa porque es el 'panel de control' de gran parte de las cargas de trabajo de IA en producción."
 },
 "Elastic": {
  "founded": 2012,
  "employees": 3300,
  "revenue_2025": "~$1.5B (FY2025)",
  "geo_risk": "Origen holandés (Ámsterdam) con operaciones dirigidas desde EEUU; distribuida y remota, su riesgo es de licenciamiento/competencia open-source (fork OpenSearch de AWS) más que geopolítico.",
  "desc": "Creadora de Elasticsearch, motor de búsqueda y analítica que se reposicionó como base de datos vectorial para RAG y búsqueda con IA. Importa como capa de recuperación (retrieval) en muchas pilas de IA generativa empresarial."
 },
 "MongoDB": {
  "founded": 2007,
  "employees": 5500,
  "revenue_2025": "~$2.0B (FY2025)",
  "geo_risk": "Sede en Nueva York; base de clientes global diversificada, con riesgo más competitivo (Postgres, DynamoDB) que geopolítico.",
  "desc": "Base de datos documental líder (Atlas en la nube) que añadió búsqueda vectorial nativa para aplicaciones de IA generativa. Importa como capa de datos operativa por defecto de muchas startups y apps que integran LLMs."
 },
 "OntoInnovation": {
  "founded": 2019,
  "employees": 1500,
  "revenue_2025": "~$1.0B",
  "geo_risk": "Sede en Wilmington, Massachusetts; alta exposición a Asia (TSMC, fabricantes de HBM en Corea) como clientes y a los controles de exportación de EEUU hacia China.",
  "desc": "Equipos de metrología e inspección de procesos para semiconductores, nacida de la fusión Nanometrics-Rudolph (2019); líder en inspección de empaquetado avanzado y HBM. Importa porque el packaging avanzado (CoWoS, HBM) es el cuello de botella de los chips de IA."
 },
 "AlibabaCloud": {
  "founded": 2009,
  "employees": 15000,
  "revenue_2025": "~$16B (segmento cloud de Alibaba, FY2025)",
  "geo_risk": "Sede en Hangzhou, China; bloqueada de las GPUs punteras de NVIDIA por los controles de exportación de EEUU, depende de chips propios (Hanguang/T-Head) y de Huawei; riesgo regulatorio doble (Pekín y sanciones occidentales).",
  "desc": "Mayor nube pública de China y brazo de IA de Alibaba, desarrolladora de la familia de modelos abiertos Qwen, referente mundial en open-source. Importa como el hyperscaler central del ecosistema de IA chino y su vía de autosuficiencia en cómputo."
 },
 "StabilityAI": {
  "founded": 2019,
  "employees": 200,
  "revenue_2025": "~$60M (est., privada)",
  "geo_risk": "Sede real en Londres (Reino Unido) pese a operar en EEUU; su riesgo principal es financiero y de dependencia de cómputo alquilado (AWS/CoreWeave, GPUs NVIDIA), no geopolítico.",
  "desc": "Laboratorio de IA generativa creador de Stable Diffusion (imagen open-source) y modelos de audio/video. Importa como pionero del ecosistema abierto de modelos de difusión, aunque quedó debilitado tras crisis de gestión y salida de Emad Mostaque en 2024."
 },
 "CommScopeHolding": {
  "founded": 1976,
  "employees": 20000,
  "revenue_2025": "~$5B",
  "geo_risk": "Sede en Carolina del Norte con fábricas en México, China y EEUU: expuesta a aranceles EEUU-China; tras vender OWN/DAS a Amphenol se concentra en conectividad de datacenters.",
  "desc": "Fabricante de infraestructura de conectividad: fibra, cableado estructurado y soluciones para datacenters y redes de banda ancha. Importa porque el boom de datacenters de IA dispara la demanda de su segmento de fibra/conectividad (CCS)."
 },
 "CMC_Materials": {
  "founded": 2000,
  "employees": 2000,
  "revenue_2025": "N/D (adquirida por Entegris en 2022; ~$1.2B antes de la compra)",
  "geo_risk": "Plantas en Illinois/Texas y presencia en Taiwán, Corea y Japón; su negocio depende de las fabs asiáticas de lógica y memoria. Nota: el ticker CMIT del grafo no corresponde — ya no cotiza sola, es parte de Entegris (ENTG).",
  "desc": "Líder en slurries y pads de CMP (pulido químico-mecánico de obleas), ex Cabot Microelectronics. Importa porque el CMP es un paso obligatorio en cada capa de un chip avanzado; hoy opera dentro de Entegris."
 },
 "DuPont_Electronics": {
  "founded": 1802,
  "employees": 12000,
  "revenue_2025": "~$4.5B (segmento electrónica)",
  "geo_risk": "La mayoría de sus ventas de electrónica van a fabs en Taiwán, Corea, China y Japón — alta exposición a Asia y a controles de exportación; el negocio se escindió como Qnity Electronics (NYSE: Q) el 1-nov-2025.",
  "desc": "Materiales electrónicos de DuPont: fotorresistentes, pastas CMP, laminados y químicos para fabricación de semiconductores y empaquetado avanzado. Importa como proveedor crítico de consumibles para casi todas las fabs; en 2025 se independizó como Qnity."
 },
 "TowerSemiconductor": {
  "founded": 1993,
  "employees": 6000,
  "revenue_2025": "~$1.6B",
  "geo_risk": "Sede y dos fabs en Israel (Migdal HaEmek), expuesta al conflicto regional; mitiga con fabs en EEUU (Texas, California), Japón (TPSCo) y capacidad en Italia (acuerdo con ST en Agrate.",
  "desc": "Foundry especializada en nodos analógicos: RF-SOI, sensores de imagen, gestión de potencia y fotónica de silicio (SiPho). Importa porque su fotónica de silicio alimenta los transceptores ópticos de los datacenters de IA; Intel intentó comprarla en 2022 (veto de China)."
 },
 "Inspur": {
  "founded": 1945,
  "employees": 35000,
  "revenue_2025": "~$20B+ (Inspur Information, 000977.SZ)",
  "geo_risk": "China (Shandong); en la Entity List de EEUU desde 2023, lo que restringe su acceso a GPUs NVIDIA y CPUs Intel/AMD — depende crecientemente de aceleradores domésticos (Huawei Ascend).",
  "desc": "Mayor fabricante chino de servidores y uno de los mayores del mundo en servidores de IA; arma la infraestructura de cómputo de los hyperscalers chinos (Alibaba, Tencent, ByteDance). Importa como pieza clave del stack de IA chino bajo sanciones."
 },
 "Ericsson": {
  "founded": 1876,
  "employees": 94000,
  "revenue_2025": "~$24B",
  "geo_risk": "Sede en Suecia; gran dependencia de Norteamérica (contrato AT&T), salida de Rusia consumada, y beneficiaria del veto occidental a Huawei — pero expuesta a un mercado 5G global estancado.",
  "desc": "Uno de los tres grandes proveedores mundiales de redes móviles (RAN 5G, core, transporte). Importa porque la conectividad 5G/6G y el AI-RAN son la capa de red sobre la que correrán los servicios de IA distribuida y el edge computing."
 },
 "Nokia": {
  "founded": 1865,
  "employees": 78000,
  "revenue_2025": "~$21B",
  "geo_risk": "Sede en Finlandia; favorecida por la exclusión de Huawei en Occidente y cada vez más anclada a EEUU: compró Infinera (óptica, 2025) y recibió una inversión de ~$1B de NVIDIA (oct-2025) para AI-RAN.",
  "desc": "Proveedor de redes móviles, fijas y ópticas; con Infinera se convirtió en actor fuerte de interconexión óptica para datacenters. Importa como puente entre telecom e infraestructura de IA (redes ópticas de datacenter y AI-RAN con NVIDIA)."
 },
 "AlephAlpha": {
  "founded": 2019,
  "employees": 150,
  "revenue_2025": "N/D privada (estimado decenas de M€)",
  "geo_risk": "Heidelberg, Alemania; es la apuesta de soberanía de IA europea/alemana (respaldo de Schwarz Group, SAP y Bosch, ronda de ~$500M en 2023), pero depende de GPUs NVIDIA y compite contra labs de EEUU con mucho más capital.",
  "desc": "Laboratorio alemán de IA que pivotó de competir en LLMs frontera a vender PhariaAI, un stack/sistema operativo de IA soberana para empresas y gobiernos europeos. Importa como el estandarte de la 'IA soberana' de la UE."
 },
 "01AI": {
  "founded": 2023,
  "employees": 250,
  "revenue_2025": "N/D privada (~decenas de M$)",
  "geo_risk": "Pekín, China; fundada por Kai-Fu Lee, entrenó sus modelos Yi con inventario de GPUs NVIDIA acumulado antes de los controles de exportación de EEUU; en 2025 pivotó a soluciones empresariales apoyándose en modelos DeepSeek.",
  "desc": "Laboratorio chino de IA creador de los modelos abiertos Yi (Yi-34B, Yi-Large), valorado en ~$1B en 2023. Importa como ejemplo del ecosistema chino de LLMs abiertos y de su consolidación tras el shock DeepSeek."
 },
 "Graphcore": {
  "founded": 2016,
  "employees": 500,
  "revenue_2025": "N/D (parte de SoftBank; históricamente <$30M/año)",
  "geo_risk": "Bristol, Reino Unido; adquirida por SoftBank (Japón) en jul-2024 por ~$600M tras quedarse sin caja — encajada en la estrategia de ASI de Masayoshi Son; los controles de exportación la forzaron a abandonar el mercado chino.",
  "desc": "Diseñador británico de IPUs (Intelligence Processing Units), la alternativa europea más ambiciosa a las GPU de NVIDIA que no logró tracción comercial. Importa como talento de diseño de aceleradores dentro del portafolio de IA de SoftBank (junto a Arm)."
 },
 "Rockwell_Automation": {
  "founded": 1903,
  "employees": 27000,
  "revenue_2025": "~$8.2B",
  "geo_risk": "Sede en Milwaukee, EEUU, con manufactura en México y EEUU expuesta a aranceles; es beneficiaria directa del reshoring industrial estadounidense (fabs, baterías, datacenters).",
  "desc": "Mayor empresa pura de automatización industrial de EEUU (PLCs Allen-Bradley, software FactoryTalk, alianza con NVIDIA para robótica/IA industrial). Importa porque automatiza las propias fábricas del reshoring, incluidas plantas de chips y energía."
 },
 "Samsara": {
  "founded": 2015,
  "employees": 3000,
  "revenue_2025": "~$1.5B",
  "geo_risk": "San Francisco, EEUU; su hardware IoT (cámaras, telemática) se fabrica en Asia — exposición a aranceles y a la cadena electrónica china/taiwanesa; maneja datos de flotas e infraestructura crítica.",
  "desc": "Plataforma de 'operaciones conectadas': telemática, cámaras con IA y sensores IoT para flotas, logística e infraestructura física. Importa como caso líder de IA aplicada al mundo físico (ticker IOT) con ~$1.5B de ingresos recurrentes."
 },
 "Leonardo_DRS": {
  "founded": 1969,
  "employees": 8000,
  "revenue_2025": "~$3.5B",
  "geo_risk": "EEUU (Virginia) pero controlada ~72% por Leonardo S.p.A. (Italia) bajo acuerdo de seguridad (proxy/SSA) con el DoD; demanda ligada al presupuesto de defensa de EEUU y a los sensores para Ucrania/Indo-Pacífico.",
  "desc": "Electrónica de defensa: sensores infrarrojos (con fab propia de detectores), computación naval nuclear-eléctrica y sistemas de contra-drones para el Pentágono. Importa como puente entre sensores avanzados de semiconductores y la defensa con IA."
 },
 "Zebra_Technologies": {
  "founded": 1969,
  "employees": 10000,
  "revenue_2025": "~$5.2B",
  "geo_risk": "Sede en Illinois con fabricación concentrada en Asia (China, y diversificación a México/Vietnam) — muy expuesta a aranceles EEUU-China en hardware de captura de datos.",
  "desc": "Líder en identificación automática y visión para logística: escáneres, impresoras de etiquetas, RFID, computadoras móviles y robots de almacén (compró Fetch Robotics). Importa como la capa de sensado/digitalización de almacenes y cadenas de suministro que la IA física necesita."
 },
 "Cognex": {
  "founded": 1981,
  "employees": 2400,
  "revenue_2025": "~$950M",
  "geo_risk": "Sede en Massachusetts pero fuerte exposición a la manufactura electrónica y de baterías EV en China, y al ciclo de capex de la cadena de Apple en Asia.",
  "desc": "Líder en visión artificial industrial (cámaras y software de inspección) usada en fábricas de semiconductores, electrónica y logística. Es el 'ojo' que automatiza el control de calidad en la manufactura avanzada."
 },
 "Keysight": {
  "founded": 2014,
  "employees": 15000,
  "revenue_2025": "~$5.4B",
  "geo_risk": "Sede en California (heredera de HP/Agilent); ~15% de ingresos de China, expuesta a controles de exportación de EEUU sobre equipos de prueba avanzados.",
  "desc": "Mayor fabricante de instrumentos de prueba y medición electrónica (osciloscopios, analizadores de red, emulación 5G/6G y de interconexiones para IA). Todo chip y sistema de red se valida con sus equipos antes de producirse."
 },
 "Mercury_Systems": {
  "founded": 1981,
  "employees": 2200,
  "revenue_2025": "~$900M",
  "geo_risk": "Casi 100% dependiente del presupuesto de defensa de EEUU; su valor es justamente ofrecer procesamiento 'trusted' fabricado y empaquetado en suelo estadounidense.",
  "desc": "Electrónica de defensa: módulos de procesamiento seguro, RF y subsistemas embebidos para radares, misiles y aviónica. Es el puente entre los chips comerciales (Intel, NVIDIA) y las plataformas militares de EEUU."
 },
 "Booz_Allen": {
  "founded": 1914,
  "employees": 34000,
  "revenue_2025": "~$12B",
  "geo_risk": "~98% de ingresos del gobierno de EEUU; muy expuesta a recortes de gasto federal civil (era DOGE), aunque defensa e inteligencia le dan colchón.",
  "desc": "Consultora tecnológica del gobierno de EEUU, mayor proveedor de servicios de IA para defensa e inteligencia (contratos con DoD, NSA). Canaliza la adopción de IA (incluida la de Anthropic/OpenAI vía acuerdos) hacia agencias federales."
 },
 "PixelWorks": {
  "founded": 1997,
  "employees": 230,
  "revenue_2025": "~$40M",
  "geo_risk": "Sede en EEUU pero la mayoría de operaciones e ingresos dependen de OEMs de smartphones chinos vía su filial Pixelworks Shanghai; fabricación en fundiciones asiáticas.",
  "desc": "Fabless de chips de procesamiento visual (mejora de video/display para móviles gaming y proyectores). Actor de nicho pequeño y en declive de ingresos; su relevancia en la cadena es marginal frente a los grandes fabless."
 },
 "Veeva": {
  "founded": 2007,
  "employees": 7000,
  "revenue_2025": "~$2.75B",
  "geo_risk": "Exposición geopolítica baja: SaaS con sede en California y clientes farmacéuticos globales; su riesgo es regulatorio (datos clínicos) más que de cadena de suministro física.",
  "desc": "Software cloud vertical para la industria farmacéutica (CRM, ensayos clínicos, calidad regulatoria), ahora integrando IA generativa en sus productos. Ejemplo de SaaS vertical que monetiza la capa de aplicación de la IA."
 },
 "Coherus_Bio": {
  "employees": 90,
  "revenue_2025": "pre-revenue (<$5M)",
  "geo_risk": "Sede real en Toronto (Canadá, no EEUU) y cotiza en NASDAQ; su manufactura depende de un JV con Sanan IC (China) y operaciones en Singapur — exposición directa a tensiones EEUU-China en fotónica.",
  "desc": "OJO: el id dice Coherus_Bio (biotecnológica) pero label/ticker/categoría corresponden a POET Technologies: interposers ópticos y motores fotónicos para interconexiones de datacenters de IA (800G/1.6T). Empresa pre-ingresos apostando a la óptica co-empaquetada."
 },
 "STMicroelectronics": {
  "founded": 1987,
  "employees": 50000,
  "revenue_2025": "~$11.8B",
  "geo_risk": "Campeón franco-italiano (Estados de Francia e Italia son accionistas); fabs en Francia, Italia, Singapur y Malta; muy expuesta al ciclo automotriz y a la competencia china en chips analógicos/potencia.",
  "desc": "IDM europeo (no fabless): microcontroladores, sensores, chips de potencia SiC/GaN para autos y electrónica industrial. Pilar de la soberanía semiconductora europea y proveedor clave de Tesla/automoción en carburo de silicio."
 },
 "First_Solar": {
  "founded": 1999,
  "employees": 8000,
  "revenue_2025": "~$5B",
  "geo_risk": "Campeón solar de EEUU (fabs en Ohio) beneficiado por el IRA y aranceles anti-China, pero con plantas en India, Malasia y Vietnam expuestas a la política arancelaria de EEUU.",
  "desc": "Mayor fabricante solar de EEUU con tecnología propia de capa fina CdTe (no depende del polisilicio chino). Clave para alimentar la demanda eléctrica de los datacenters de IA con generación desplegable rápido."
 },
 "SMA_Solar": {
  "founded": 1981,
  "employees": 3700,
  "revenue_2025": "~$1.6B",
  "geo_risk": "Sede en Alemania; sufre competencia feroz de inversores chinos (Huawei, Sungrow) y la debilidad del solar residencial europeo — ha recortado plantilla.",
  "desc": "Fabricante alemán de inversores solares (residencial, comercial y utility-scale). Uno de los pocos proveedores occidentales de electrónica de potencia solar, relevante para la seguridad energética europea."
 },
 "Kratos_Defense": {
  "founded": 1994,
  "employees": 4100,
  "revenue_2025": "~$1.3B",
  "geo_risk": "Dependencia casi total del presupuesto de defensa de EEUU; se beneficia del giro hacia drones baratos 'attritable', hipersónica y comunicaciones satelitales militares.",
  "desc": "Defensa de nueva generación: drones de combate económicos (XQ-58 Valkyrie), objetivos aéreos, motores de misiles y software de tierra satelital (OpenSpace). Apuesta por lo 'barato y masivo' frente a los primes tradicionales."
 },
 "SiTime": {
  "founded": 2005,
  "employees": 600,
  "revenue_2025": "~$285M",
  "geo_risk": "Fabless de Silicon Valley; sus MEMS se fabrican con Bosch (Alemania) y TSMC (Taiwán) con ensamblaje en Asia — exposición a Taiwán/Malasia, mitigada por doble fuente.",
  "desc": "Líder en timing MEMS (osciladores de silicio que reemplazan al cuarzo): la sincronización de precisión que necesitan los switches, ópticas y racks de GPU en datacenters de IA. Su segmento CommsEnterprise crece fuerte con la ola de IA. (Nota: el ticker real es SITM, no SITT.)"
 },
 "Globalstar": {
  "founded": 1991,
  "employees": 400,
  "revenue_2025": "~$275M",
  "geo_risk": "Riesgo de concentración extremo en un solo cliente: Apple (SOS satelital del iPhone) financia y consume la mayor parte de su capacidad; nuevos satélites construidos por MDA con lanzamientos SpaceX.",
  "desc": "Operador de constelación LEO de comunicaciones que da el servicio de emergencia satelital del iPhone y posee espectro terrestre (banda n53) valioso para redes privadas 5G/IoT. Ejemplo de 'direct-to-device' monetizado vía Apple."
 },
 "BlackSky": {
  "founded": 2014,
  "employees": 300,
  "revenue_2025": "~$115M",
  "geo_risk": "Dependiente de contratos de inteligencia de EEUU (NRO/EOCL) y ministerios de defensa aliados; lanza con Rocket Lab — riesgo de concentración gubernamental más que geográfico.",
  "desc": "Observación de la Tierra con constelación propia de alta revisita (Gen-3) y plataforma de análisis con IA (Spectra) que convierte imágenes en inteligencia en tiempo casi real. Actor puro de 'inteligencia geoespacial como servicio'."
 },
 "Hexcel": {
  "founded": 1946,
  "employees": 5700,
  "revenue_2025": "~$1.9B",
  "geo_risk": "Muy atada a los ritmos de producción de Boeing y Airbus (duopolio cliente); plantas en EEUU, Europa y Marruecos; insumo crítico (fibra de carbono/precursor PAN) con pocas fuentes globales.",
  "desc": "Fabricante de composites avanzados (fibra de carbono, honeycomb, prepregs) para aeroestructuras comerciales, defensa y espacio. Material estructural clave para aviones, cohetes y satélites — cuello de botella físico de la cadena aeroespacial."
 },
 "TorayIndustries": {
  "founded": 1926,
  "employees": 48000,
  "revenue_2025": "~$17B",
  "geo_risk": "Sede en Tokio con plantas en Japón, Corea, EE.UU. y Europa; líder mundial en fibra de carbono, expuesto a tensiones comerciales Japón-China y a la demanda aeroespacial occidental.",
  "desc": "Conglomerado químico japonés, mayor productor mundial de fibra de carbono (Torayca) usada en aviones (Boeing 787), cohetes, tanques de hidrógeno y palas eólicas. Material estructural crítico para aeroespacio y defensa."
 },
 "AlleghenyTech": {
  "founded": 1996,
  "employees": 7500,
  "revenue_2025": "~$4.5B",
  "geo_risk": "Sede en Pittsburgh (EE.UU.); depende de esponja de titanio importada (históricamente Rusia/Kazajistán, hoy Japón), pero se beneficia del rearme occidental y del reshoring de metales estratégicos.",
  "desc": "Productor estadounidense de metales especiales: titanio y superaleaciones de níquel para motores a reacción, fuselajes y defensa. Cuello de botella clave en la cadena aeroespacial tras la salida del titanio ruso (VSMPO)."
 },
 "CarpenterTech": {
  "founded": 1889,
  "employees": 5000,
  "revenue_2025": "~$2.9B",
  "geo_risk": "Producción concentrada en EE.UU. (Pensilvania, Alabama); baja exposición a China y alta alineación con la demanda de defensa/aeroespacio estadounidense.",
  "desc": "Fabricante de aleaciones especiales de alto rendimiento (aceros premium, titanio, aleaciones magnéticas blandas) para motores de avión, defensa, médico y actuadores eléctricos. Capacidad de fundición especializada escasa en Occidente."
 },
 "ParkerHannifin": {
  "founded": 1917,
  "employees": 60000,
  "revenue_2025": "~$20B",
  "geo_risk": "Sede en Ohio con huella manufacturera global diversificada; exposición moderada a ciclos industriales de China/Europa, y creciente peso del segmento aeroespacial (compra de Meggitt, Reino Unido).",
  "desc": "Gigante de sistemas de movimiento y control: hidráulica, neumática, sellos, filtración y actuación aeroespacial. Sus componentes están en casi todo avión, cohete y robot industrial occidental."
 },
 "Moog": {
  "founded": 1951,
  "employees": 13500,
  "revenue_2025": "~$3.7B",
  "geo_risk": "Sede en Nueva York (East Aurora); fuerte dependencia del presupuesto de defensa de EE.UU. y programas espaciales, con riesgo bajo de cadena china por ser proveedor ITAR.",
  "desc": "Especialista en actuadores y controles de precisión para aviones, misiles, satélites y lanzadores (controla superficies de vuelo y vectorización de empuje). Proveedor crítico y difícil de sustituir en defensa y espacio."
 },
 "Boeing": {
  "founded": 1916,
  "employees": 170000,
  "revenue_2025": "~$78B",
  "geo_risk": "Sede en EE.UU. (Arlington/Seattle); rehén de las tensiones EE.UU.-China (pedidos chinos usados como palanca comercial) y de una cadena de suministro propia frágil (Spirit AeroSystems, titanio).",
  "desc": "Uno de los dos grandes fabricantes de aviones comerciales del mundo y contratista principal de defensa/espacio (satélites, SLS, aviones militares). Ancla de demanda de toda la cadena aeroespacial occidental."
 },
 "Airbus": {
  "founded": 1970,
  "employees": 155000,
  "revenue_2025": "~$80B",
  "geo_risk": "Consorcio europeo (Francia/Alemania/España) con línea de ensamblaje en Tianjin, China: expuesto a la geopolítica UE-China-EE.UU. y a aranceles, pero también beneficiario de los problemas de Boeing.",
  "desc": "Mayor fabricante de aviones comerciales del mundo por entregas; también satélites, helicópteros y defensa europea. Su cartera récord de pedidos tensiona a toda la cadena de motores, titanio y fibra de carbono."
 },
 "Northrop": {
  "founded": 1939,
  "employees": 97000,
  "revenue_2025": "~$42B",
  "geo_risk": "Contratista puro de defensa de EE.UU.; dependencia casi total del presupuesto del Pentágono, con riesgo de programas (B-21, Sentinel) más que geográfico.",
  "desc": "Contratista de defensa estadounidense: bombardero furtivo B-21, misiles ICBM Sentinel, motores de cohete sólidos, satélites militares y sistemas espaciales (construyó el James Webb). Pilar de la disuasión nuclear y espacial de EE.UU."
 },
 "Aerojet": {
  "founded": 1942,
  "employees": 5000,
  "revenue_2025": "~$2.4B (segmento de L3Harris)",
  "geo_risk": "Absorbida por L3Harris en 2023; capacidad casi monopólica en EE.UU. de motores cohete líquidos (RL10, RS-25) y propulsión de misiles, lo que la hace cuello de botella del rearme estadounidense.",
  "desc": "Fabricante estadounidense de propulsión: motores de cohete para ULA/NASA y motores de misiles (Javelin, Stinger, THAAD). Su capacidad de producción limita el ritmo de reposición de arsenales occidentales."
 },
 "Stellantis": {
  "founded": 2021,
  "employees": 250000,
  "revenue_2025": "~$160B",
  "geo_risk": "Sede en Países Bajos con centros en Francia, Italia y EE.UU.; muy expuesta a aranceles EE.UU.-UE, a la competencia de EVs chinos y a la dependencia de baterías/semiconductores asiáticos.",
  "desc": "Cuarto grupo automotriz mundial (fusión Fiat-Chrysler + PSA: Jeep, Peugeot, Ram, Fiat). Gran comprador de chips automotrices y baterías; su electrificación y conducción asistida lo atan a la cadena de semiconductores."
 },
 "SpaceX": {
  "founded": 2002,
  "employees": 14000,
  "revenue_2025": "~$15B (privada, estimado)",
  "geo_risk": "Sede en EE.UU. (Texas/California); dominio casi monopólico del lanzamiento occidental y dependencia del gobierno de EE.UU. (NASA, Pentágono), con riesgo político ligado a la figura de Elon Musk.",
  "desc": "Empresa de Elon Musk que domina el acceso al espacio con Falcon 9/Starship y opera Starlink, la mayor constelación de satélites del mundo. Es la infraestructura de lanzamiento de la que depende gran parte de la economía espacial y militar (Starshield)."
 },
 "BlueOrigin": {
  "founded": 2000,
  "employees": 12000,
  "revenue_2025": "N/D privada (financiada por Bezos)",
  "geo_risk": "Sede en Kent, Washington (EE.UU.); riesgo bajo de cadena externa pero alta dependencia del capital de Jeff Bezos y de contratos NASA/Pentágono aún incipientes.",
  "desc": "Empresa espacial de Jeff Bezos: cohete pesado New Glenn (primer vuelo 2025), motores BE-4 que también propulsan el Vulcan de ULA, y módulo lunar para Artemis. Segunda alternativa creíble de EE.UU. frente a SpaceX."
 },
 "T_Mobile": {
  "founded": 1994,
  "employees": 70000,
  "revenue_2025": "~$86B",
  "geo_risk": "Opera solo en EE.UU. pero controlada por Deutsche Telekom (Alemania); su red 5G depende de equipos Ericsson/Nokia tras la exclusión de Huawei.",
  "desc": "Mayor operador 5G de EE.UU. por cobertura; socio de SpaceX/Starlink para conectividad directa satélite-a-móvil. Puente clave entre la infraestructura terrestre y la nueva capa de conectividad espacial."
 },
 "AST_SpaceMobile": {
  "founded": 2017,
  "employees": 1200,
  "revenue_2025": "~$50-100M (fase pre-comercial)",
  "geo_risk": "Sede en Midland, Texas; depende de lanzamientos de terceros (SpaceX, Blue Origin, ISRO) y de acuerdos con operadores (AT&T, Verizon, Vodafone), con espectro y regulación como riesgos clave.",
  "desc": "Construye la primera constelación de satélites que se conecta directamente a teléfonos móviles normales (BlueBird, con antenas gigantes en órbita). Si escala, convierte a los satélites en torres celulares espaciales, con interés también de defensa."
 },
 "PlanetLabs": {
  "founded": 2010,
  "employees": 1000,
  "revenue_2025": "~$250M",
  "geo_risk": "Sede en San Francisco con filial relevante en Alemania; ingresos crecientemente ligados a contratos de defensa/inteligencia de EE.UU. y aliados (Ucrania elevó la demanda de imágenes).",
  "desc": "Opera la mayor flota de satélites de observación terrestre (Doves, SkySat, Pelican) que fotografía toda la Tierra a diario. Sus datos alimentan inteligencia militar, agricultura y monitoreo climático, cada vez más analizados con IA."
 },
 "ICEYE": {
  "founded": 2014,
  "employees": 700,
  "revenue_2025": "~$150-200M (privada)",
  "geo_risk": "Sede en Espoo, Finlandia (frontera con Rusia); muy expuesta a demanda de defensa europea/OTAN y a Ucrania, su mayor caso de uso visible.",
  "desc": "Opera la mayor constelación comercial de satélites SAR (radar de apertura sintética), que ve a través de nubes y de noche. Clave para inteligencia de defensa, seguros y monitoreo de la cadena de suministro global."
 },
 "Anduril": {
  "founded": 2017,
  "employees": 5500,
  "revenue_2025": "~$1.5-2B (privada)",
  "geo_risk": "Sede en Costa Mesa, California; ingresos concentrados en contratos del Pentágono y aliados (AUKUS), con megafábrica Arsenal-1 en Ohio para escalar producción.",
  "desc": "Startup de defensa que integra IA (plataforma Lattice) con hardware autónomo: drones, interceptores, submarinos y el programa IVAS del ejército. Es el símbolo del nuevo complejo defensa-tecnología estadounidense."
 },
 "AuroraInnovation": {
  "founded": 2017,
  "employees": 1900,
  "revenue_2025": "~$10M (inicio comercial, aún quema caja)",
  "geo_risk": "Sede en Pittsburgh, EEUU; operación comercial concentrada en corredores de Texas (Dallas-Houston) y dependiente de regulación estatal/federal de camiones sin conductor.",
  "desc": "Desarrolla el Aurora Driver, sistema de conducción autónoma para camiones de carga; lanzó operación sin conductor en Texas en 2025 con socios como Volvo, PACCAR, Uber Freight y NVIDIA. Primer caso real de camiones autónomos comerciales en EEUU."
 },
 "ElevenLabs": {
  "founded": 2022,
  "employees": 400,
  "revenue_2025": "~$150-200M ARR (privada)",
  "geo_risk": "Fundada por polacos con sedes en Nueva York y Londres; riesgo más regulatorio (deepfakes de voz, UE AI Act) que geográfico, y depende de nubes/GPU de terceros.",
  "desc": "Líder en síntesis y clonación de voz con IA y agentes conversacionales de voz. Valorada en ~$6.6B (enero 2025); es la capa de voz de facto para productos de IA (incluida la voz Bixby de esta app)."
 },
 "ScaleAI": {
  "founded": 2016,
  "employees": 1400,
  "revenue_2025": "~$1.5-2B (privada)",
  "geo_risk": "Sede en San Francisco; tras la inversión de Meta (49%, $14.3B, jun 2025) perdió clientes como OpenAI y Google, y depende de mano de obra de etiquetado en Filipinas, Kenia y Venezuela.",
  "desc": "Proveedor dominante de datos etiquetados y RLHF para entrenar modelos frontera, más contratos de IA de defensa (Defense Llama, DoD). Su absorción parcial por Meta reconfiguró el mercado de datos para IA."
 },
 "FujitsuHPC": {
  "founded": 1935,
  "employees": 124000,
  "revenue_2025": "~$24B (grupo Fujitsu)",
  "geo_risk": "Sede en Tokio; campeón nacional japonés de HPC financiado por el estado (RIKEN), con fabricación de CPU dependiente de TSMC en Taiwán.",
  "desc": "Fujitsu construyó Fugaku, el supercomputador insignia de Japón, con sus CPU ARM A64FX, y prepara la CPU MONAKA de 2nm para Fugaku NEXT. Es la vía soberana japonesa hacia el HPC y la IA sin depender solo de NVIDIA."
 },
 "Qorvo": {
  "founded": 2015,
  "employees": 8500,
  "revenue_2025": "~$3.7B",
  "geo_risk": "Sede en Greensboro, EEUU; ~40-50% de ingresos ligados a Apple y exposición fuerte a China como mercado final, aunque sus fabs de GaAs/GaN en EEUU la hacen estratégica para defensa.",
  "desc": "Fabricante de chips de radiofrecuencia (filtros BAW, amplificadores GaAs/GaN) nacido de la fusión RFMD-TriQuint. Crítico para smartphones, radares de defensa y electrónica de potencia."
 },
 "Skyworks": {
  "founded": 2002,
  "employees": 9500,
  "revenue_2025": "~$4B",
  "geo_risk": "Sede en Irvine, California; dependencia extrema de Apple (~65-70% de ingresos), lo que la expone al ciclo del iPhone y al riesgo de insourcing de RF por parte de Apple.",
  "desc": "Diseña y fabrica front-ends de radiofrecuencia (amplificadores, filtros, módulos) para móviles e IoT. Junto con Qorvo y Broadcom forma el oligopolio RF que conecta todo dispositivo inalámbrico."
 },
 "Rohm": {
  "founded": 1958,
  "employees": 23000,
  "revenue_2025": "~$3.2B",
  "geo_risk": "Sede en Kioto, Japón; apostó fuerte por SiC con fabs en Japón (Miyazaki) justo cuando el mercado de vehículos eléctricos se enfrió, y compite contra capacidad china subsidiada.",
  "desc": "Fabricante japonés de semiconductores de potencia, pionero en carburo de silicio (SiC) para EVs e infraestructura energética. Pieza del bloque japonés de chips de potencia junto a Renesas y Toshiba."
 },
 "Navitas": {
  "founded": 2014,
  "employees": 300,
  "revenue_2025": "~$60-80M",
  "geo_risk": "Sede en Torrance, California, pero con fabricación externalizada en Asia (TSMC para GaN) y parte importante de ventas en cargadores/OEMs chinos.",
  "desc": "Especialista fabless en chips de potencia GaN y SiC; elegida por NVIDIA para la arquitectura de alimentación de 800V HVDC de los data centers de IA de próxima generación, lo que la convirtió en proxy bursátil de la energía para IA."
 },
 "Shinko_Electric": {
  "founded": 1946,
  "employees": 25000,
  "revenue_2025": "~$1.5B",
  "geo_risk": "Sede en Nagano, Japón; considerada activo estratégico nacional — el fondo estatal JIC la compró (saliendo Fujitsu) para mantener los sustratos avanzados en manos japonesas.",
  "desc": "Uno de los pocos fabricantes mundiales de sustratos FC-BGA para empaquetado avanzado de chips, junto a Ibiden y Unimicron. Sin estos sustratos no se ensamblan las GPU/CPU de IA: cuello de botella silencioso de la cadena."
 },
 "Modine": {
  "founded": 1916,
  "employees": 11500,
  "revenue_2025": "~$2.6B",
  "geo_risk": "Sede en Racine, Wisconsin, con plantas globales; su suerte está cada vez más atada al capex de data centers de IA en EEUU y Europa (marca Airedale).",
  "desc": "Fabricante centenario de gestión térmica que pivotó al enfriamiento de data centers (chillers, CDUs, líquido) vía Airedale. Beneficiario directo del boom de refrigeración para IA."
 },
 "Fanuc": {
  "founded": 1972,
  "employees": 8800,
  "revenue_2025": "~$5.3B",
  "geo_risk": "Producción hiperconcentrada en su campus del monte Fuji (Yamanashi, Japón) y ~30% de ventas expuestas a China, cuyo ciclo industrial marca sus resultados.",
  "desc": "Líder mundial en controles CNC y uno de los mayores fabricantes de robots industriales (los robots amarillos). Sus máquinas fabrican las fábricas: base de la automatización de autos, electrónica y semiconductores."
 },
 "Yaskawa": {
  "founded": 1915,
  "employees": 13000,
  "revenue_2025": "~$3.8B",
  "geo_risk": "Sede en Kitakyushu, Japón; fuerte exposición al ciclo de inversión industrial chino y competencia creciente de robótica china (Estun, Inovance) en su propio terreno.",
  "desc": "Fabricante japonés de robots Motoman, servomotores (líder mundial) y variadores de frecuencia. Sus servos son el componente de movimiento dentro de robots y máquinas-herramienta de media industria global, incluidos humanoides."
 },
 "ABB_Robotics": {
  "founded": 1988,
  "employees": 7000,
  "revenue_2025": "~$2.3B (división; grupo ABB ~$33B)",
  "geo_risk": "División con sede en Zúrich pero con su mayor fábrica de robots en Shanghái, lo que la expone de lleno a la rivalidad EEUU-China; ABB planea escindirla y sacarla a bolsa en 2026.",
  "desc": "Una de las 'cuatro grandes' de la robótica industrial (con Fanuc, Yaskawa y KUKA): brazos robóticos, cobots y software de automatización. Su spin-off previsto la convertirá en la mayor robótica cotizada de Occidente."
 },
 "Maxar": {
  "founded": 2017,
  "employees": 4600,
  "revenue_2025": "N/D privada (~$1.8-2B est.)",
  "geo_risk": "Sede en Colorado (EEUU); privatizada por Advent en 2023 y muy dependiente de contratos de defensa/inteligencia del gobierno estadounidense (NRO/EOCL).",
  "desc": "Operador líder de satélites de observación de la Tierra de muy alta resolución (constelación WorldView/Legion) y fabricante de buses satelitales. Sus imágenes alimentan inteligencia militar, mapas y modelos de IA geoespacial."
 },
 "AeroVironment": {
  "founded": 1971,
  "employees": 4000,
  "revenue_2025": "~$820M FY25 (~$2B run-rate tras absorber BlueHalo)",
  "geo_risk": "Sede en Virginia/California (EEUU); ingresos concentrados en el Pentágono y aliados (Ucrania fue gran catalizador), expuesta a ciclos presupuestarios de defensa de EEUU.",
  "desc": "Fabricante de drones tácticos pequeños (Raven, Puma) y municiones merodeadoras Switchblade, ampliado a espacio y láseres con la compra de BlueHalo en 2025. Referente de la guerra autónoma de bajo costo."
 },
 "Joby_Aviation": {
  "founded": 2009,
  "employees": 1800,
  "revenue_2025": "pre-revenue (certificación FAA en curso)",
  "geo_risk": "Sede en Santa Cruz, California; depende del ritmo de certificación de la FAA y del capital de Toyota (mayor accionista industrial), con planes de lanzamiento comercial en Dubái.",
  "desc": "Desarrollador de aerotaxis eléctricos eVTOL con respaldo de Toyota y contratos con la USAF (Agility Prime). Es el candidato más avanzado a certificar un eVTOL en EEUU, clave para la movilidad aérea urbana autónoma."
 },
 "Wayve": {
  "founded": 2017,
  "employees": 500,
  "revenue_2025": "pre-revenue (licencias iniciales a OEMs)",
  "geo_risk": "Sede en Londres (Reino Unido); financiada por SoftBank, NVIDIA y Microsoft, y dependiente de GPUs de NVIDIA y de acuerdos con OEMs globales (Nissan) para escalar.",
  "desc": "Startup británica de conducción autónoma end-to-end basada en IA aprendida (sin mapas HD), con la mayor ronda de IA europea (~$1.05B en 2024). Su enfoque 'embodied AI' compite con Tesla FSD y se licencia a fabricantes."
 },
 "Umicore": {
  "founded": 1805,
  "employees": 11500,
  "revenue_2025": "~€3.5B (ingresos excl. metales; facturación total mucho mayor)",
  "geo_risk": "Sede en Bruselas (Bélgica); expuesta a la sobrecapacidad china en cátodos, a precios de cobalto/litio y a plantas en Polonia, Corea y Canadá cuyo retorno depende de la demanda EV occidental.",
  "desc": "Grupo belga de materiales: cátodos para baterías EV, catalizadores y el mayor reciclador de metales preciosos/baterías de Europa (Hoboken). Pieza clave de la cadena de baterías no-china."
 },
 "Nanya": {
  "founded": 1995,
  "employees": 3800,
  "revenue_2025": "~$1.2B",
  "geo_risk": "Fabs 100% en Taiwán (New Taipei), máxima exposición al riesgo del estrecho; cuarto jugador DRAM mundial detrás de Samsung/SK hynix/Micron, parte del grupo Formosa Plastics.",
  "desc": "Fabricante taiwanés de DRAM de especialidad (consumo, industrial, automotriz) con tecnología propia de 10nm-class. Aporta oferta DRAM fuera del trío dominante, relevante cuando la memoria escasea por el boom de IA."
 },
 "Winbond": {
  "founded": 1987,
  "employees": 7500,
  "revenue_2025": "~$2.5-3B (consolidado con Nuvoton)",
  "geo_risk": "Fabs en Taiwán (Taichung, Kaohsiung), plena exposición al estrecho de Taiwán; su NOR flash es insumo crítico difícil de sustituir en automoción y electrónica industrial.",
  "desc": "Especialista taiwanés en memorias nicho: NOR flash, NAND de baja densidad y DRAM de especialidad (incl. CUBE para IA en el edge). Sus chips arrancan (boot) casi cualquier sistema electrónico moderno."
 },
 "Altium": {
  "founded": 1985,
  "employees": 900,
  "revenue_2025": "~$350M (ya dentro de Renesas)",
  "geo_risk": "Origen australiano con sede operativa en San Diego; adquirida por Renesas (Japón) en 2024 por $5.9B, por lo que su riesgo ahora se liga al grupo japonés.",
  "desc": "Editor del software Altium Designer, estándar de facto para diseño de PCBs entre ingenieros y startups de hardware. Renesas la compró para construir una plataforma 'system design' de silicio a placa."
 },
 "Photronics": {
  "founded": 1969,
  "employees": 5000,
  "revenue_2025": "~$870M",
  "geo_risk": "Sede en Connecticut pero con fábricas y joint ventures clave en Taiwán (PDMC) y China (PDMCX), quedando en medio de la tensión EEUU-China sobre semiconductores.",
  "desc": "Mayor fabricante independiente de fotomáscaras del mundo, el 'negativo fotográfico' con el que se imprimen los chips. Cuello de botella silencioso: sin máscaras no hay litografía para ningún nodo."
 },
 "Rambus": {
  "founded": 1990,
  "employees": 900,
  "revenue_2025": "~$650M",
  "geo_risk": "Sede en San José, California; fabless dependiente de foundries asiáticas y muy apalancada al ciclo de servidores/DDR5, con licencias a los tres grandes de DRAM.",
  "desc": "Diseñador de chips de interfaz de memoria (RCD/MRDIMM para DDR5), IP de seguridad e interconexión. Sus buffers están en la ruta crítica entre CPUs de servidor y la DRAM que alimenta a la IA."
 },
 "Achronix": {
  "founded": 2004,
  "employees": 250,
  "revenue_2025": "N/D privada (~$100M est.)",
  "geo_risk": "Sede en Santa Clara, California; fabless que fabrica en TSMC 7nm (Taiwán) y cuyo intento de SPAC se frustró en 2021, permaneciendo privada.",
  "desc": "Único fabless independiente de FPGAs de gama alta (Speedster7t) y de IP de eFPGA embebible, alternativa a AMD/Xilinx e Intel/Altera. Sus FPGAs se usan en aceleración de redes, 5G e inferencia de IA."
 },
 "NXP": {
  "founded": 2006,
  "employees": 34000,
  "revenue_2025": "~$12.5B",
  "geo_risk": "Sede en Eindhoven (Países Bajos) con ~30% de ingresos en China y fabs propias más dependencia de TSMC; escindida de Philips, muy sensible al ciclo automotriz global.",
  "desc": "Líder mundial en semiconductores para automóvil (microcontroladores, radar, procesadores S32), NFC y edge industrial. Sus chips son el sistema nervioso del coche definido por software."
 },
 "Renesas": {
  "founded": 2002,
  "employees": 21000,
  "revenue_2025": "~$9B (~¥1.3-1.4T)",
  "geo_risk": "Sede en Tokio (Japón); fabs propias en Japón (el incendio de Naka en 2021 paró la industria auto mundial) y fuerte exposición al ciclo automotriz e industrial chino.",
  "desc": "Gigante japonés de microcontroladores y SoCs automotrices (heredero de Hitachi, Mitsubishi y NEC), ampliado a analógico (IDT, Dialog) y diseño de placas (Altium). Uno de los tres pilares del silicio para autos junto a NXP e Infineon."
 },
 "Microchip_Tech": {
  "founded": 1989,
  "employees": 20000,
  "revenue_2025": "~$4.4B FY25 (tras corrección de inventarios; pico $8.4B FY23)",
  "geo_risk": "Sede en Chandler, Arizona, con fabs propias en EEUU (modelo IDM parcial) que la hacen menos dependiente de Taiwán, aunque sufre el ciclo de inventarios industrial/auto.",
  "desc": "Fabricante de microcontroladores PIC/AVR, FPGAs rad-hard (Microsemi) y analógico para industria, defensa y espacio. Sus MCUs baratos y omnipresentes son el 'arroz' de la electrónica embebida."
 },
 "InfiniteraNet": {
  "founded": 2000,
  "employees": 3200,
  "revenue_2025": "~$1.4B (absorbida por Nokia en feb 2025)",
  "geo_risk": "Sede en San José, California, con fab propia de fotónica de indio-fósforo en Sunnyvale y ensamblaje en Asia; su compra por Nokia (~$2.3B) la integra al bloque occidental frente a Huawei.",
  "desc": "Especialista en transporte óptico coherente y fotónica integrada (ICE/DSPs propios) para redes de larga distancia y datacenter interconnect. Crítica para mover el tráfico masivo que generan los clusters de IA."
 },
 "HuggingFace": {
  "founded": 2016,
  "employees": 500,
  "revenue_2025": "~$130M (ARR est., privada)",
  "geo_risk": "Sede en EEUU con raíces francesas; riesgo geopolítico bajo pero depende de nubes estadounidenses (AWS/Google) y del ecosistema open-source global.",
  "desc": "Plataforma central del ecosistema de IA open-source: hub de modelos, datasets y librerías (Transformers). Es la 'capa de distribución' de los modelos abiertos que corren sobre GPUs de toda la cadena."
 },
 "X_Fab": {
  "founded": 1992,
  "employees": 4400,
  "revenue_2025": "~$850M",
  "geo_risk": "Fabs en Alemania, Francia, Malasia (Kuching) y EEUU (Texas); diversificada pero con exposición operativa relevante a Malasia y al ciclo automotriz europeo.",
  "desc": "Foundry especializada europea en analógico/mixed-signal, MEMS y SiC para automotriz, médico e industrial. Importa como capacidad de fundición no-digital fuera de Asia oriental."
 },
 "Wistron": {
  "founded": 2001,
  "employees": 85000,
  "revenue_2025": "~$50B (fuerte salto por servidores IA)",
  "geo_risk": "Sede en Taiwán con manufactura en Taiwán, China, México, Vietnam y EEUU (Texas); muy expuesta a un conflicto en el estrecho y a aranceles EEUU-China.",
  "desc": "ODM taiwanés (spin-off de Acer) que ensambla servidores de IA, incluidas placas de cómputo GB200/GB300 para Nvidia y sus socios. Eslabón crítico entre los chips y los racks de los datacenters."
 },
 "Sensata": {
  "founded": 2006,
  "employees": 18000,
  "revenue_2025": "~$3.8B",
  "geo_risk": "Domiciliada en Reino Unido con HQ operativo en Massachusetts; manufactura concentrada en México, China y Bulgaria — expuesta al ciclo automotriz y a fricciones EEUU-China.",
  "desc": "Fabricante de sensores y controles (presión, temperatura, corriente) para automóviles, EVs e industria, heredera del negocio de sensores de Texas Instruments. Provee el 'sistema nervioso' sensorial de vehículos y equipos."
 },
 "Himax_Tech": {
  "founded": 2001,
  "employees": 2200,
  "revenue_2025": "~$950M",
  "geo_risk": "Fabless con sede en Tainan (Taiwán), depende de foundries taiwanesas (TSMC/UMC) y de clientes de paneles en China — doble exposición al estrecho y a la demanda china.",
  "desc": "Fabless taiwanesa líder en drivers de pantalla (DDIC) y timing controllers, con línea creciente en sensado 3D/ultra-low-power (WiseEye) para IA en el borde. Clave para displays de autos, TVs y móviles."
 },
 "Ultra_Clean": {
  "founded": 1991,
  "employees": 7000,
  "revenue_2025": "~$2.1B",
  "geo_risk": "Sede en California con plantas en EEUU, República Checa, Malasia y China; alta concentración de clientes (Lam Research y Applied Materials) y exposición a controles de exportación hacia China.",
  "desc": "Fabrica subsistemas críticos (entrega de gases y fluidos, módulos de vacío) y servicios de limpieza para los grandes fabricantes de equipos semiconductores. Proveedor 'invisible' pero esencial de Lam y AMAT."
 },
 "Aehr_Test": {
  "founded": 1977,
  "employees": 120,
  "revenue_2025": "~$60M",
  "geo_risk": "Sede en Fremont, California; riesgo principal no es geográfico sino de concentración de clientes y del ciclo de SiC/EV, con expansión reciente hacia burn-in de GaN y procesadores IA.",
  "desc": "Sistemas de test y burn-in a nivel de oblea (FOX-XP), críticos para calificar chips de carburo de silicio (SiC) para EVs y, más recientemente, procesadores de IA. Nicho pequeño pero estratégico en fiabilidad."
 },
 "ACM_Research": {
  "founded": 1998,
  "employees": 1900,
  "revenue_2025": "~$950M",
  "geo_risk": "Listada en EEUU pero opera vía ACM Shanghai y vende mayoritariamente a fabs chinas (SMIC, Hua Hong): exposición máxima a sanciones, entity lists y desacople EEUU-China.",
  "desc": "Equipos de limpieza de obleas y procesos húmedos (tecnología SAPS/TEBO) que compiten con Screen y Lam. Es uno de los pilares del esfuerzo chino por equipar sus fabs con herramientas propias."
 },
 "TataSemiconductor": {
  "founded": 2020,
  "employees": 5000,
  "revenue_2025": "pre-revenue (fab en construcción)",
  "geo_risk": "Apuesta soberana de India: mega-fab en Dholera (Gujarat, con tecnología de PSMC de Taiwán) y OSAT en Assam; depende de transferencia tecnológica taiwanesa y subsidios estatales indios.",
  "desc": "División de semiconductores del grupo Tata que construye la primera fab de escala de India (~$11B) y plantas de empaquetado. Importa como el intento más serio de India de entrar en la manufactura de chips."
 },
 "Etched": {
  "founded": 2022,
  "employees": 80,
  "revenue_2025": "pre-revenue",
  "geo_risk": "Startup californiana totalmente dependiente de TSMC para fabricar su chip en nodos avanzados — hereda el riesgo Taiwán completo sin diversificación.",
  "desc": "Startup que diseña 'Sohu', un ASIC especializado exclusivamente en transformers, prometiendo órdenes de magnitud más inferencia por dólar que las GPU. Apuesta extrema de silicio ultra-especializado contra Nvidia."
 },
 "SES": {
  "founded": 1985,
  "employees": 4000,
  "revenue_2025": "~$3B (consolida Intelsat desde jul-2025)",
  "geo_risk": "Sede en Luxemburgo con fuerte negocio gubernamental/militar en EEUU y Europa; su flota GEO/MEO compite con la presión de Starlink y depende de lanzadores estadounidenses.",
  "desc": "Operador satelital europeo (GEO + constelación MEO O3b mPOWER) que en 2025 completó la compra de Intelsat, creando un gigante de conectividad y comunicaciones gubernamentales. Contrapeso occidental no-Starlink en órbita."
 },
 "Together_AI": {
  "founded": 2022,
  "employees": 300,
  "revenue_2025": "~$100M+ (ARR est., privada)",
  "geo_risk": "Sede en San Francisco; su riesgo es de suministro más que geográfico — depende del acceso a GPUs Nvidia y a datacenters con energía disponible en Norteamérica.",
  "desc": "Nube de IA (AI cloud) para entrenamiento e inferencia de modelos abiertos, valorada ~$3.3B tras su Serie B de 2025. Parte de la capa 'neocloud' que revende cómputo GPU a desarrolladores."
 },
 "Prophesee": {
  "founded": 2014,
  "employees": 100,
  "revenue_2025": "~$15M (est.; pasó por reestructuración judicial 2024-25)",
  "geo_risk": "Sede en París; campeón europeo de visión neuromórfica pero financieramente frágil (concurso judicial en 2024) y dependiente de socios como Sony para fabricar sus sensores.",
  "desc": "Pionera francesa en sensores de visión basados en eventos (event-based, inspirados en la retina), con chips co-desarrollados con Sony. Relevante para visión de máquina ultrarrápida y de bajo consumo en robótica y móviles."
 },
 "Rain_Neuromorphics": {
  "founded": 2017,
  "employees": 90,
  "revenue_2025": "pre-revenue",
  "geo_risk": "Startup de San Francisco respaldada por Sam Altman (OpenAI firmó carta de intención de compra de chips); en 2024-25 tuvo dificultades para levantar capital y exploró su venta.",
  "desc": "Diseña chips de cómputo en memoria (analógico/digital) inspirados en el cerebro para inferencia de IA ultraeficiente, rebautizada Rain AI. Apuesta especulativa de hardware neuromórfico ligada al ecosistema OpenAI."
 },
 "Richtek": {
  "founded": 1998,
  "employees": 1800,
  "revenue_2025": "~$800M",
  "geo_risk": "Sede en Hsinchu (Taiwán) y filial de MediaTek; concentración total en el ecosistema taiwanés de foundries y en la demanda de electrónica de consumo asiática.",
  "desc": "Fabless taiwanesa de ICs de gestión de energía (PMICs, conversores DC-DC) adquirida por MediaTek. Sus chips de potencia acompañan a casi todo SoC en móviles, PCs y ahora placas de servidores."
 },
 "PDF_Solutions": {
  "founded": 1991,
  "employees": 550,
  "revenue_2025": "~$190M",
  "geo_risk": "Sede en Santa Clara (California); su plataforma de datos se usa en fabs de todo el mundo, con exposición a clientes en Taiwán, Corea y China sujeta a controles de exportación de EEUU.",
  "desc": "Software de análisis de rendimiento (yield) y datos de fabricación de semiconductores; su plataforma Exensio conecta datos de fab, test y ensamblaje. Importa porque mejora el yield de los fabs, un cuello de botella clave en nodos avanzados."
 },
 "FlexLogix": {
  "founded": 2014,
  "employees": 70,
  "revenue_2025": "N/D privada",
  "geo_risk": "Empresa de Mountain View (California) adquirida por Analog Devices a finales de 2024; fabless, dependiente de foundries externas (TSMC) para sus chips de prueba.",
  "desc": "Especialista en eFPGA embebido (IP reconfigurable dentro de otros chips) y aceleradores de inferencia InferX. Su IP permite actualizar hardware tras fabricación, relevante para defensa y edge AI; hoy integrada en Analog Devices."
 },
 "Oklo": {
  "founded": 2013,
  "employees": 250,
  "revenue_2025": "pre-revenue",
  "geo_risk": "Sede en Santa Clara (California); depende del licenciamiento de la NRC estadounidense y del suministro de combustible HALEU, hoy dominado históricamente por Rusia.",
  "desc": "Desarrolla microrreactores rápidos (Aurora) con modelo de venta de energía en vez de reactores, respaldada por Sam Altman y cotizando tras SPAC en 2024. Clave como fuente de energía dedicada para datacenters de IA (acuerdos con Switch y otros)."
 },
 "Xenergy": {
  "founded": 2009,
  "employees": 600,
  "revenue_2025": "pre-revenue",
  "geo_risk": "Sede en Rockville (Maryland); depende de financiación del DOE (programa ARDP) y de construir su propia cadena de combustible TRISO en EEUU para reducir dependencia de HALEU ruso.",
  "desc": "Desarrolla el SMR de alta temperatura Xe-100 y fabrica combustible TRISO-X; respaldada por Amazon (~$500M en 2024) para alimentar datacenters. Uno de los SMR más avanzados de EEUU con Dow como primer cliente industrial."
 },
 "TerraPower": {
  "founded": 2006,
  "employees": 800,
  "revenue_2025": "pre-revenue",
  "geo_risk": "Sede en Bellevue (Washington) con primera planta en Kemmerer (Wyoming); su diseño Natrium requiere HALEU, cuya cadena de suministro occidental aún es incipiente tras cortar el suministro ruso.",
  "desc": "Empresa nuclear fundada por Bill Gates que construye el reactor rápido refrigerado por sodio Natrium con almacenamiento térmico en sales. Primera construcción SMR avanzada iniciada en EEUU (2024), pieza clave de la energía firme para la demanda eléctrica de la IA."
 },
 "Cameco": {
  "founded": 1988,
  "employees": 3000,
  "revenue_2025": "~$2.5B",
  "geo_risk": "Sede en Saskatoon (Canadá) con minas clave en Saskatchewan y JV en Kazajistán (Inkai), expuesta a riesgo logístico/kazajo-ruso; su participación del 49% en Westinghouse la ancla al ecosistema nuclear occidental.",
  "desc": "Uno de los mayores productores de uranio del mundo (McArthur River, Cigar Lake) y copropietario de Westinghouse junto a Brookfield. Es el proveedor occidental de referencia de combustible nuclear, crítico para el renacimiento nuclear que impulsa la demanda energética de la IA."
 },
 "Redwire": {
  "founded": 2020,
  "employees": 1400,
  "revenue_2025": "~$550M",
  "geo_risk": "Sede en Jacksonville (Florida) con plantas en EEUU y Europa (Bélgica, Luxemburgo); fuerte dependencia de contratos gubernamentales de NASA y del Departamento de Defensa de EEUU.",
  "desc": "Proveedor de infraestructura espacial: paneles solares desplegables ROSA, aviónica, estructuras y manufactura en órbita; en 2025 sumó drones militares con la compra de Edge Autonomy. Suministrador transversal de componentes para casi cualquier misión espacial occidental."
 }
};
if (typeof NODE_META !== 'undefined') {
  for (var _kf in META_FILL) {
    NODE_META[_kf] = Object.assign({}, META_FILL[_kf], NODE_META[_kf] || {});
  }
}
window.META_FILL = META_FILL;
