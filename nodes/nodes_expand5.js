// nodes/nodes_expand5.js — Informe de enriquecimiento 2026-07
// Generado por scripts/ingest_enrichment_md.py desde el informe de Fabrizio
// (148 nuevas + 82 enriquecidas). NO editar a mano: regenerar con el script.

var NODES_EXPAND5 = [
  {"id": "Vistra", "label": "Vistra", "ticker": "VST · NYSE", "cat": "power_ipp", "port": "", "role": "Mayor productor independiente de electricidad de mercado libre en EEUU (~39 GW), con flota mixta de gas, carbón, nuclear y baterías.", "supplies": "Electricidad baseload nuclear y de respaldo a hyperscalers de IA vía PPAs directos en sus propias plantas (Comanche Peak, Perry, Davis-Besse).", "moat": "Mayor cartera de generación desregulada de EEUU con activos nucleares baseload escasos muy codiciados por datacenters; riesgo: alta concentración en pocos clientes hyperscaler y ejecución de \"uprates\" nucleares.", "country": "EEUU", "growth": "🟢 Acción disparada 2025-2026 por demanda de datacenters de IA; PPAs ancla con Amazon y Meta.", "margin": 0.11, "mkt": "VST"},
  {"id": "TalenEnergy", "label": "Talen Energy", "ticker": "TLN · NASDAQ", "cat": "power_ipp", "port": "", "role": "IPP centrada en la planta nuclear Susquehanna (2.5 GW, Pensilvania) más generación a gas/carbón en PJM.", "supplies": "Electricidad nuclear \"front of the meter\" para el campus de datacenters de Amazon en Pensilvania.", "moat": "Primer mover del modelo IPP-nuclear-hyperscaler con contrato ancla de $18B; riesgo: alto apalancamiento post-bancarrota y dependencia de un solo activo nuclear/cliente.", "country": "EEUU", "growth": "🟢 Acción referencia del sector tras el mega-PPA con Amazon de junio 2025.", "margin": 0.2, "mkt": "TLN"},
  {"id": "NRGEnergy", "label": "NRG Energy", "ticker": "NRG · NYSE", "cat": "power_ipp", "port": "", "role": "Generador diversificado (gas, carbón, renovables) con fuerte foco en Texas, expandiendo capacidad de gas nueva para datacenters de IA.", "supplies": "Electricidad de sitios propios en Texas a datacenters bajo PPAs de largo plazo; desarrollo conjunto de plantas de gas con GE Vernova.", "moat": "Control de generación + retail en Texas y posicionamiento agresivo en gas nuevo; riesgo: gran parte de su pipeline de datacenters aún son cartas de intención sin PPA firme.", "country": "EEUU", "growth": "🟢 Re-rating fuerte 2025-2026 por narrativa de datacenters en Texas.", "margin": 0.09, "mkt": "NRG"},
  {"id": "Calpine", "label": "Calpine (Constellation Energy)", "ticker": "Privada (subsidiaria de Constellation Energy desde ene 2026)", "cat": "power_ipp", "port": "", "role": "Mayor flota de generación a gas natural y geotérmica de EEUU, adquirida por Constellation Energy para crear el mayor productor privado de electricidad del país.", "supplies": "Generación a gas complementaria a la flota nuclear de Constellation, incluyendo suministro directo a operadores de datacenters de IA en Texas.", "moat": "Escala de generación a gas flexible que complementa el baseload nuclear de Constellation; riesgo: complejidad regulatoria multi-estado de la mega-fusión ($16.4B).", "country": "EEUU", "growth": "🟢 Integración con Constellation refuerza posición dominante en mercado de energía para IA.", "margin": null, "mkt": "", "preipo": true},
  {"id": "PSEG", "label": "Public Service Enterprise Group (PSEG)", "ticker": "PEG · NYSE", "cat": "power_ipp", "port": "", "role": "Utility regulada de Nueva Jersey con generación nuclear propia (Hope Creek, participación en Salem y Peach Bottom).", "supplies": "Electricidad nuclear baseload en el mercado PJM; en negociación para monetizar capacidad hacia datacenters de IA.", "moat": "Activos nucleares baseload en mercado PJM de alta demanda; riesgo: va por detrás de competidores en firmar PPAs concretos con hyperscalers.", "country": "EEUU", "growth": "🟡 Pipeline de \"gran carga\" creció a 9.4 GW (90% datacenters) pero sin PPA firme aún anunciado.", "margin": 0.2, "mkt": "PEG"},
  {"id": "AEP", "label": "American Electric Power (AEP)", "ticker": "AEP · NASDAQ", "cat": "power_ipp", "port": "", "role": "Mayor red de transmisión de EEUU y generador multi-estado (nuclear, carbón, gas, eólica/solar) sirviendo a >5M clientes en 11 estados.", "supplies": "Transmisión y suministro eléctrico a datacenters de IA de Google, Amazon, Meta y Microsoft en Ohio, Indiana y Texas.", "moat": "Mayor huella de transmisión del país, clave para interconectar datacenters; riesgo: fricción regulatoria multi-estado sobre quién paga la infraestructura nueva.", "country": "EEUU", "growth": "🟢 Capacidad contratada escaló a ~63 GW (~90% ligada a datacenters); espera duplicar demanda total para 2030.", "margin": 0.17, "mkt": "AEP"},
  {"id": "DominionEnergy", "label": "Dominion Energy", "ticker": "D · NYSE", "cat": "power_ipp", "port": "", "role": "Utility de Virginia con la mayor concentración de datacenters de IA del mundo (\"Data Center Alley\"), generación nuclear, gas y renovables.", "supplies": "Electricidad a la mayor concentración mundial de datacenters de hyperscalers en el norte de Virginia; explora SMRs con Amazon.", "moat": "Ubicación geográfica única junto al mayor clúster de datacenters del planeta; riesgo: límites de interconexión y permisos ante crecimiento explosivo de demanda.", "country": "EEUU", "growth": "🟢 40 GW bajo contrato de datacenters, la utility más expuesta a IA de EEUU.", "margin": 0.2, "mkt": "D"},
  {"id": "DukeEnergy", "label": "Duke Energy", "ticker": "DUK · NYSE", "cat": "power_ipp", "port": "", "role": "Mayor flota nuclear regulada de EEUU, sirviendo Carolinas, Florida, Indiana, Ohio y Kentucky, con capex récord por demanda de IA.", "supplies": "Electricidad nuclear y de gas a datacenters de hyperscalers en sus territorios de servicio.", "moat": "Mayor base regulada de activos nucleares de EEUU con capex garantizado; riesgo: ejecución de un plan de capex histórico de $103B.", "country": "EEUU", "growth": "🟢 CapEx récord de $103B (abr 2026), ~14 GW de nueva demanda ligada a IA.", "margin": 0.2, "mkt": "DUK"},
  {"id": "SouthernCompany", "label": "Southern Company", "ticker": "SO · NYSE", "cat": "power_ipp", "port": "", "role": "Utility del sureste de EEUU (Georgia, Alabama), operadora de Plant Vogtle, los únicos reactores nucleares nuevos construidos en EEUU en décadas.", "supplies": "Electricidad nuclear de Plant Vogtle y gas/renovables a datacenters de IA en Georgia.", "moat": "Único operador de reactores nucleares AP1000 nuevos en EEUU (Vogtle 3 y 4); riesgo: margen operativo en descenso pese al crecimiento de ventas.", "country": "EEUU", "growth": "🟡 Ventas eléctricas industriales +42% i.a. por datacenters, pero margen operativo cayendo (19.6%→16.9%).", "margin": 0.17, "mkt": "SO"},
  {"id": "PPLCorp", "label": "PPL Corporation", "ticker": "PPL · NYSE", "cat": "power_ipp", "port": "", "role": "Utility de Pensilvania/Kentucky que desarrolla nueva generación a gas específicamente para datacenters de IA vía JV con Blackstone.", "supplies": "Electricidad de nueva generación a gas natural a datacenters de IA en Pensilvania.", "moat": "Territorio de transmisión clave en PJM (mismo mercado que Talen/Susquehanna); riesgo: pipeline aún mayormente en fase de solicitud, no contratado en firme.", "country": "EEUU", "growth": "🟢 Pipeline de 28.3 GW en solicitudes de gran carga, JV de hasta 6.75 GW con Blackstone (jul 2025).", "margin": 0.18, "mkt": "PPL"},
  {"id": "RollsRoyceSMR", "label": "Rolls-Royce SMR", "ticker": "Privada (subsidiaria de Rolls-Royce Holdings, LSE: RR.)", "cat": "nuclear_smr", "port": "", "role": "Diseña y fabrica reactores modulares pequeños (SMR) de ~470 MWe basados en tecnología de agua presurizada.", "supplies": "Reactores SMR a gobiernos y utilities europeas; aún sin contrato directo confirmado con un hyperscaler de IA.", "moat": "Respaldo industrial e ingeniería nuclear de Rolls-Royce (submarinos, aviación); riesgo: ningún SMR aún operativo, y compite con GE Hitachi, X-energy y NuScale por contratos de datacenter.", "country": "Reino Unido", "growth": "🟡 Contratos gubernamentales crecientes (Reino Unido abr 2026, ČEZ/Chequia abr 2026) pero sin PPA de IA aún.", "margin": null, "mkt": "", "preipo": true},
  {"id": "GEHitachiNuclear", "label": "GE Hitachi Nuclear Energy", "ticker": "No cotiza (JV GE Vernova / Hitachi)", "cat": "nuclear_smr", "port": "", "role": "Diseña el reactor modular pequeño BWRX-300 y reactores ABWR/ESBWR de gran escala.", "supplies": "Reactores BWRX-300 a utilities y ahora a desarrolladores de datacenters de IA (Google/Elementl Power en Ohio).", "moat": "~80% de componentes del BWRX-300 ya pre-aprobados por la NRC, ventaja de \"primero en construir\" (Darlington, Canadá); riesgo: sobrecostos severos (~8x) en su proyecto insignia de Darlington.", "country": "EEUU", "growth": "🟢 Hitachi vincula explícitamente su expansión de cadena nuclear a la demanda de datacenters de IA (oct 2025).", "margin": null, "mkt": ""},
  {"id": "WestinghouseElectric", "label": "Westinghouse Electric Company", "ticker": "Privada (Brookfield 51% / Cameco 49%)", "cat": "nuclear_smr", "port": "", "role": "Diseña y construye el reactor nuclear AP1000, con 12 unidades operativas y ~19 en desarrollo global.", "supplies": "Reactores AP1000 a gobiernos y, desde 2025, a proyectos de campus de datacenters de IA (Fermi America, Texas).", "moat": "Único proveedor occidental con AP1000 de historial comercial probado (Vogtle); riesgo: historial de sobrecostos masivos que llevó a la bancarrota de Toshiba en 2017.", "country": "EEUU", "growth": "🟢 Contrato de $80B con el gobierno de EEUU (oct 2025) para 10 nuevas plantas AP1000, explícitamente para alimentar expansión de datacenters de IA.", "margin": null, "mkt": "", "preipo": true},
  {"id": "Kazatomprom", "label": "Kazatomprom", "ticker": "KAP · LSE / AIX", "cat": "uranium", "port": "", "role": "Mayor productor mundial de uranio (~40% del suministro global) mediante extracción por lixiviación in situ (ISR).", "supplies": "Uranio natural a utilities nucleares occidentales y asiáticas, incluidos operadores de flotas nucleares en EEUU.", "moat": "Costos de producción ISR más bajos del mundo y reservas de mayor calidad; riesgo: ruta de exportación principal depende de infraestructura logística rusa.", "country": "Kazajistán", "growth": "🟢 Precio de contrato a largo plazo alcanzó $90/lb en Q1 2026, el más alto desde 2008, en un mercado con déficit estructural.", "margin": 0.3, "mkt": "KAP"},
  {"id": "NexGenEnergy", "label": "NexGen Energy", "ticker": "NXE · NYSE / TSX / ASX", "cat": "uranium", "port": "", "role": "Desarrolladora del proyecto Rook I (depósito Arrow) en la cuenca de Athabasca, Saskatchewan, el mayor depósito de uranio de alta ley no desarrollado del mundo.", "supplies": "Uranio de alta ley a utilities norteamericanas bajo contratos de offtake; producción proyectada hasta 30M lb U3O8/año (>20% del suministro mundial).", "moat": "Mayor depósito de alta ley no desarrollado del mundo en jurisdicción estable (Canadá); riesgo: financiamiento y ejecución de la construcción a 4 años recién iniciada.", "country": "Canadá", "growth": "🟢 Permiso final CNSC obtenido (5 mar 2026); market cap +47% i.a., conversaciones exploratorias con proveedores de datacenters para financiamiento.", "margin": null, "mkt": "NXE"},
  {"id": "DenisonMines", "label": "Denison Mines", "ticker": "DNN · TSX / NYSE American", "cat": "uranium", "port": "", "role": "Desarrolladora del proyecto Wheeler River (depósito Phoenix) en la cuenca de Athabasca, primer proyecto canadiense aprobado para minería por ISR.", "supplies": "Uranio a utilities norteamericanas; 22.5% de participación en el molino McClean Lake (24M lb/año de capacidad de procesamiento).", "moat": "Tecnología ISR de bajo capex sobre mineral de alta ley, con acceso a infraestructura de molino ya construida; riesgo: ejecución del cronograma de construcción hasta primera producción en 2028.", "country": "Canadá", "growth": "🟢 Licencia final CNSC (feb 2026) y decisión final de inversión (FID) tomada; acción +78.7% i.a.", "margin": null, "mkt": "DNN"},
  {"id": "PaladinEnergy", "label": "Paladin Energy", "ticker": "PDN · ASX / TSX", "cat": "uranium", "port": "", "role": "Opera la mina de uranio Langer Heinrich en Namibia (75% propiedad, 25% CNNC Overseas) mediante extracción a cielo abierto.", "supplies": "Uranio natural al mercado spot y contratos de largo plazo con utilities globales.", "moat": "Mina de escala mundial ya en operación con guía de 4.0-4.4M lb U3O8 para FY2026; riesgo: dependencia de un solo activo principal y de la regulación minera namibia.", "country": "Australia", "growth": "🟢 Acción +186% i.a. (jul 2026), narrativa explícita de \"supercycle nuclear\" ligado a demanda de datacenters de IA.", "margin": 0.15, "mkt": "PDN"},
  {"id": "UrEnergy", "label": "Ur-Energy", "ticker": "URG · NYSE American / TSX", "cat": "uranium", "port": "", "role": "Productor 100% estadounidense de uranio mediante ISR en Wyoming (Lost Creek, y Shirley Basin desde 2026).", "supplies": "Uranio doméstico a utilities estadounidenses bajo contratos legacy y de largo plazo.", "moat": "Único gran productor 100% doméstico de EEUU con tecnología ISR de bajo costo, estratégico ante políticas de \"seguridad de suministro nuclear\"; riesgo: contratos legacy a precios inferiores al spot actual.", "country": "EEUU", "growth": "🟢 Market cap ~$515M (+38.5%), posicionado como proveedor doméstico clave del \"supercycle\" nuclear-IA.", "margin": null, "mkt": "URG"},
  {"id": "GlobalAtomic", "label": "Global Atomic Corporation", "ticker": "GLO · TSX / GLATF · OTC", "cat": "uranium", "port": "", "role": "Desarrolla el proyecto de uranio Dasa en Níger (minería subterránea, ~73M lb U3O8 de reservas).", "supplies": "Uranio a utilities estadounidenses bajo contratos de offtake ya asegurados para el 90% de su producción inicial.", "moat": "Depósito de mayor ley de uranio en África, con contratos de venta ya asegurados; riesgo geopolítico severo por operar en Níger tras el golpe militar de 2023.", "country": "Canadá", "growth": "🟡 Producción retrasada a Q1 2027; parte del déficit estructural de suministro estadounidense (~45-46M lb/año) atribuido en parte a demanda de IA.", "margin": null, "mkt": "GLO"},
  {"id": "BossEnergy", "label": "Boss Energy", "ticker": "BOE · ASX / OTCQX", "cat": "uranium", "port": "", "role": "Productor de uranio ISR en Honeymoon (Australia, 100%) y Alta Mesa (Texas, 30%).", "supplies": "Uranio natural a utilities norteamericanas y asiáticas bajo contratos de largo plazo.", "moat": "Tecnología ISR de bajo costo, diversificación multi-activo en jurisdicciones estables (Australia y EEUU) y balance sin deuda; riesgo: recortes recientes de guía de producción por mayores costos.", "country": "Australia", "growth": "🟡 Guía FY2026 recortada a 1.40-1.45M lb por mayores costos de combustible, aunque contexto de precio spot proyectado en $100-135/lb.", "margin": null, "mkt": "BOE"},
  {"id": "GeneralFusion", "label": "General Fusion", "ticker": "Pre-IPO ~$1B (SPAC pendiente, Spring Valley Acquisition Corp III, NASDAQ ~\"GFUZ\")", "cat": "nuclear_fusion", "port": "", "role": "Desarrolla fusión nuclear por confinamiento magnetizado (MTF), comprimiendo litio líquido sin imanes superconductores ni láseres.", "supplies": "Aún sin contrato de suministro eléctrico comercial; en fase de demostración científica (máquina LM26).", "moat": "Enfoque tecnológico de bajo costo de capital (sin imanes superconductores/láseres); riesgo: aún no alcanza el criterio de Lawson ni breakeven científico, y casi se queda sin efectivo en 2025.", "country": "Canadá", "growth": "🟡 Hito jun 2026 (8.4M°C, 0.72 keV, 3x mejora) y salida a bolsa vía SPAC prevista para 2026, pero sin PPA de hyperscaler confirmado (a diferencia de Helion Energy-Microsoft).", "margin": null, "mkt": "", "preipo": true},
  {"id": "ZapEnergy", "label": "Zap Energy", "ticker": "Privada (~$330M levantados)", "cat": "nuclear_fusion", "port": "", "role": "Desarrolla fusión nuclear por Z-pinch estabilizado por flujo cortante, sin imanes externos; pivotó parcialmente a fisión SMR en 2026.", "supplies": "Sin suministro comercial aún; plataforma de demostración \"Century\" (100 kW).", "moat": "Diseño de reactor simplificado sin imanes externos, respaldado por Chevron Technology Ventures; riesgo: pivote a fisión SMR (diseño 4S de Toshiba) divide foco y capital, y añade exposición regulatoria NRC tradicional.", "country": "EEUU", "growth": "🟡 >100 disparos a 39 kW (oct 2025); CEO cita explícitamente la falta de energía para datacenters de IA como razón del pivote a fisión (abr 2026).", "margin": null, "mkt": "", "preipo": true},
  {"id": "CentrusEnergy", "label": "Centrus Energy", "ticker": "LEU · NYSE American", "cat": "uranium", "port": "", "role": "Único productor comercial de uranio enriquecido HALEU (uranio poco enriquecido de ensayo alto) en EEUU, insumo crítico para la nueva generación de reactores SMR avanzados.", "supplies": "HALEU a los desarrolladores de reactores avanzados que alimentan estrategias de datacenters de IA, bajo contratos del programa ARDP del DOE.", "moat": "Único enriquecedor comercial de HALEU en Occidente fuera de Rusia, posición geoestratégica clave; riesgo: capacidad de producción aún limitada y fuertemente dependiente de subsidios del DOE.", "country": "EEUU", "growth": "🟢 Demanda de HALEU disparada por el auge de SMRs orientados a datacenters de IA (TerraPower, X-energy, Kairos Power).", "margin": 0.15, "mkt": "LEU"},
  {"id": "Orano", "label": "Orano", "ticker": "ORAN · Euronext Paris (listado parcial 2024; mayoría estatal francesa)", "cat": "uranium", "port": "", "role": "Gigante estatal francés del ciclo de combustible nuclear completo: minería de uranio, conversión, enriquecimiento y reciclaje, competidor directo de Kazatomprom y Cameco.", "supplies": "Servicios de conversión y enriquecimiento de uranio a utilities occidentales que buscan diversificar su cadena de suministro fuera de Rusia.", "moat": "Única cadena de conversión/enriquecimiento comercial integrada verticalmente en Europa occidental; riesgo: pérdida forzada en 2025 de su mina histórica Somaïr en Níger tras la nacionalización.", "country": "Francia", "growth": "🟢 Demanda occidental de enriquecimiento no-ruso en máximos históricos por expansión nuclear ligada a IA.", "margin": 0.1, "mkt": "ORAN"},
  {"id": "china-northern-rare-earth", "label": "China Northern Rare Earth Group", "ticker": "600111 · SSE (Shanghái)", "cat": "rare_earth", "port": "", "role": "Mayor productor y procesador de tierras raras del mundo, controla el complejo minero-industrial de Bayan Obo en Mongolia Interior.", "supplies": "Óxidos y compuestos de tierras raras (NdPr, Dy, Tb) para fabricantes de imanes permanentes NdFeB usados en motores EV, turbinas eólicas y sistemas de defensa.", "moat": "Control cuasi-monopólico de refinación de tierras raras respaldado por cuotas estatales del gobierno chino; riesgo: dependencia total de la política de exportación de Beijing, usada como arma geopolítica en 2025-2026.", "country": "China", "growth": "🟢 ingresos +29,1% y beneficio neto +124,2% en 2025, impulsados por controles de exportación que elevaron precios globales", "margin": null, "mkt": "600111"},
  {"id": "iluka-resources", "label": "Iluka Resources", "ticker": "ILU · ASX", "cat": "rare_earth", "port": "", "role": "Productor australiano de minerales de mineral pesado (circonio, titanio) que construye la primera refinería de tierras raras totalmente integrada fuera de China.", "supplies": "Óxidos de NdPr desde la refinería Eneabba (57% construida en 2025) hacia fabricantes de imanes permanentes fuera de la cadena china.", "moat": "Respaldo financiero directo del gobierno australiano (préstamo A$1.650M); riesgo: aún en fase de construcción, sin ingresos de tierras raras confirmados.", "country": "Australia", "growth": "🟡 refinería Eneabba avanzando, primer contrato de offtake de magnéticas firmado jun-2026", "margin": null, "mkt": "ILU"},
  {"id": "ucore-rare-metals", "label": "Ucore Rare Metals", "ticker": "UCU · TSXV (UURAF · OTCQX)", "cat": "rare_earth", "port": "", "role": "Desarrolla la tecnología patentada RapidSX de separación de tierras raras y construye una planta comercial en Louisiana, EEUU.", "supplies": "Separación de los 6 elementos de tierras raras críticos bajo restricción china, financiada por el Departamento de Defensa de EEUU.", "moat": "Tecnología propietaria RapidSX más rápida y compacta que la extracción por solventes tradicional; riesgo: ejecución de la primera planta comercial a escala (2026-2028).", "country": "Canadá", "growth": "🟢 contrato DoD de USD 18,4M (mayo 2025), planta de Louisiana escalando de 2.000 a 7.500 tpa", "margin": null, "mkt": "UCU"},
  {"id": "arafura-resources", "label": "Arafura Resources", "ticker": "ARU · ASX", "cat": "rare_earth", "port": "", "role": "Desarrolla el proyecto Nolans, una mina y refinería integrada \"ore-to-oxide\" de óxido de NdPr en el Territorio del Norte australiano.", "supplies": "Óxido de NdPr para fabricantes de imanes permanentes fuera de China, cubriendo hasta 4-5% de la demanda mundial de tierras raras magnéticas.", "moat": "Financiamiento estatal multipaís (Australia, EEUU, Alemania) asegurando el desarrollo; riesgo: capex total de USD 1.900M y FID recién confirmada en mayo 2026.", "country": "Australia", "growth": "🟢 FID confirmada mayo 2026, compromiso de compra estatal australiano de A$1.200M", "margin": null, "mkt": "ARU"},
  {"id": "vital-metals", "label": "Vital Metals", "ticker": "VML · ASX (suspendida)", "cat": "rare_earth", "port": "", "role": "Minera de tierras raras en crisis financiera severa, propietaria del depósito Nechalacho (Tardiff) en Canadá.", "supplies": "Concentrado de tierras raras (histórico); operación de procesamiento colapsada tras quiebra de su subsidiaria canadiense en 2023.", "moat": "Sin ventaja competitiva clara actualmente; riesgo: caja de solo A$328.691, quiebra de subsidiaria de procesamiento y suspensión bursátil en ASX desde agosto 2025.", "country": "Australia", "growth": "🔴 acciones suspendidas ago-2025, perdió su rol de socio de procesamiento ante REalloys en Saskatchewan", "margin": null, "mkt": "VML"},
  {"id": "air-products", "label": "Air Products and Chemicals", "ticker": "APD · NYSE", "cat": "chemicals", "port": "", "role": "Proveedor global de gases industriales y electrónicos (nitrógeno, hidrógeno, gases especiales) para semiconductores y energía.", "supplies": "Gases industriales/electrónicos in-situ a fabricantes de semiconductores, incluyendo expansión en la planta de Samsung Electronics en Pyeongtaek y contratos en Taiwán.", "moat": "Escala global e infraestructura de producción junto a fabs de clientes; riesgo: grandes apuestas de capital en hidrógeno con retornos inciertos (canceló proyecto de USD 4.500M en Louisiana).", "country": "Estados Unidos", "growth": "🟡 ingresos FY2025 -1%, pero expansión de contratos de semiconductores en Corea/Taiwán en 2026", "margin": null, "mkt": "APD"},
  {"id": "resonac-holdings", "label": "Resonac Holdings", "ticker": "4004 · TSE", "cat": "materials", "port": "", "role": "Fabricante japonés de materiales avanzados para semiconductores (ex Showa Denko), líder mundial en films no conductores (NCF) para empaquetado HBM.", "supplies": "NCF y materiales de empaquetado avanzado a TSMC; participa en consorcio de empaquetado con Applied Materials, KLA y Tokyo Electron.", "moat": "~50% de cuota mundial en NCF para HBM impulsado por el boom de IA; riesgo: dependencia de materias primas chinas para ánodos de baterías, con márgenes de EV en caída.", "country": "Japón", "growth": "🟢 crecimiento récord en materiales de semiconductores/HBM en 1T FY2026, aunque ingresos totales -3,2% en FY2025", "margin": 0.043, "mkt": "4004"},
  {"id": "kanto-denka-kogyo", "label": "Kanto Denka Kogyo", "ticker": "4047 · TSE", "cat": "chemicals", "port": "", "role": "Química especializada japonesa, productor casi monopolístico doméstico de NF3 y WF6 críticos para fabricación de semiconductores.", "supplies": "NF3 (limpieza/etching) y WF6 (cableado metálico en nodos 3-7nm) a TSMC (Kumamoto), Samsung, SK Hynix, Micron, Kioxia, Sony y Rapidus (dependencia exclusiva).", "moat": "~90% de la producción japonesa de NF3, integración vertical hacia WF6; riesgo: concentración de producción en una sola planta (incendio en Shibukawa, ago-2025) y crisis de suministro de tungsteno chino.", "country": "Japón", "growth": "🔴 ingresos planos, crisis de tungsteno chino duplicando/triplicando el precio del WF6", "margin": 0.056, "mkt": "4047"},
  {"id": "nitto-denko", "label": "Nitto Denko", "ticker": "6988 · TSE", "cat": "materials", "port": "", "role": "Fabricante japonés de materiales avanzados de nicho global (cintas, films) para semiconductores, displays y automoción.", "supplies": "Cintas de dicing y films de back-grinding (ELEP MOUNT, ELEP HOLDER) para fabricantes de semiconductores, y polarizadores para paneles OLED.", "moat": "Posicionamiento estratégico \"Global Niche Top\" en adhesivos y coatings especializados; riesgo: contracción del segmento de films ópticos (-2,6%) y exposición cambiaria.", "country": "Japón", "growth": "🟡 ingresos +1,4% FY2026, Industrial Tape crece (+4,2%) pero Optronics se contrae", "margin": 0.178, "mkt": "6988"},
  {"id": "sumitomo-chemical", "label": "Sumitomo Chemical", "ticker": "4005 · TSE", "cat": "chemicals", "port": "", "role": "Conglomerado químico japonés diversificado, líder mundial en fotorresistentes (SUMIRESIST) para litografía de semiconductores incluyendo EUV.", "supplies": "Fotorresistentes ArF/EUV a fabricantes líderes de semiconductores en Taiwán, EEUU y Japón, con producción en Japón y Corea del Sur.", "moat": "Liderazgo mundial en fotorresistentes ArF con meta de 10% de ventas de semiconductores para FY2030; riesgo: competencia intensa de JSR, TOK y Shin-Etsu.", "country": "Japón", "growth": "🟢 core operating income +48,3%, adquisición de AUECC en Taiwán (nov-2025) expande presencia", "margin": 0.065, "mkt": "4005"},
  {"id": "mitsubishi-gas-chemical", "label": "Mitsubishi Gas Chemical", "ticker": "4182 · TSE", "cat": "chemicals", "port": "", "role": "Productor japonés de químicos especializados, líder mundial autodeclarado en peróxido de hidrógeno de grado electrónico para limpieza de obleas de semiconductores.", "supplies": "Peróxido de hidrógeno ultra-puro y materiales BT de empaquetado a fabricantes de semiconductores globales, con nueva planta en Texas (Killeen).", "moat": "Cuota #1 mundial autodeclarada en peróxido de hidrógeno electrónico; riesgo: pérdida neta 2025-2026 (¥40.300M) e impairment de ¥10.600M en Taiwán por retrasos de certificación de clientes.", "country": "Japón", "growth": "🔴 ingresos -4,6%, pérdida neta, impairment en planta de Taiwán", "margin": 0.061, "mkt": "4182"},
  {"id": "adeka-corporation", "label": "Adeka Corporation", "ticker": "4401 · TSE", "cat": "chemicals", "port": "", "role": "Fabricante japonés de precursores químicos ALD/CVD y materiales high-k para fabricación avanzada de semiconductores.", "supplies": "Precursores ALD/CVD (TEOS, TMB, TEB) y materiales high-k (Hf, Zr, Ta) a fabricantes de semiconductores en Corea, Taiwán y EEUU.", "moat": "Cartera especializada de precursores de alta pureza con meta de ¥500.000M en ventas de semiconductores para FY2030; riesgo: rentabilidad de semiconductores cayendo (-17,7%) pese a crecimiento de ventas, dificultades de certificación en Taiwán.", "country": "Japón", "growth": "🟡 ventas de semiconductores +5,8% pero beneficio operativo -17,7%", "margin": 0.1, "mkt": "4401"},
  {"id": "tosoh-corporation", "label": "Tosoh Corporation", "ticker": "4042 · TSE (ADR TOSCF · OTC)", "cat": "materials", "port": "", "role": "Química japonesa diversificada cuya filial Tosoh SMD fabrica metales/aleaciones de alta pureza para sputtering targets de semiconductores.", "supplies": "Metales de alta pureza para sputtering targets usados en la fabricación de obleas de semiconductores (150mm-450mm).", "moat": "Filial especializada Tosoh SMD con décadas de expertise en targets de alta pureza; riesgo: impairment de ¥19.300M en Tosoh SMD y márgenes de ingeniería expuestos a costos de nafta.", "country": "Japón", "growth": "🟡 ingresos -4,1% FY2026, impairment en negocio de sputtering targets", "margin": 0.094, "mkt": "4042"},
  {"id": "fujimi-incorporated", "label": "Fujimi Incorporated", "ticker": "5384 · TSE", "cat": "materials", "port": "", "role": "Fabricante japonés de abrasivos de precisión y slurries CMP (pulido químico-mecánico) para semiconductores.", "supplies": "Slurries CMP (GLANZOX, PLANERLITE) para pulido de obleas de silicio y cobre en fabricación avanzada de chips.", "moat": "Especialización de décadas en slurries de alta pureza con presencia manufacturera junto a clústeres de fabricación (Taiwán, Corea, China, EEUU); riesgo: alta dependencia del ciclo de capex de foundries/memoria.", "country": "Japón", "growth": "🟢 ingresos trimestrales crecientes (~¥17-18.000M por trimestre en 2025-2026)", "margin": null, "mkt": "5384"},
  {"id": "kyocera-corporation", "label": "Kyocera Corporation", "ticker": "6971 · TSE (ADR KYO · NYSE)", "cat": "materials", "port": "", "role": "Fabricante japonés de cerámica avanzada y sustratos/packages para componentes de semiconductores y electrónica.", "supplies": "Packages cerámicos y sustratos FCBGA para fabricantes de chips de IA y centros de datos.", "moat": "Expertise histórico de décadas en cerámica de precisión y diversificación industrial amplia; riesgo: pérdida de ¥27.800M en el segmento de semiconductores por caída de demanda FCBGA e impairment de packages orgánicos.", "country": "Japón", "growth": "🔴 margen operativo cayó de 6,8% a 3,2% en FY2025, pero nuevo sustrato cerámico para IA y expansión en EEUU (Carolina del Norte) en 2026", "margin": 0.032, "mkt": "6971"},
  {"id": "tokamak-energy", "label": "Tokamak Energy", "ticker": "Privada", "cat": "nuclear_fusion", "port": "", "role": "Desarrolla tokamaks esféricos compactos con imanes superconductores de alta temperatura (HTS) para energía de fusión.", "supplies": "Tecnología de imanes HTS (vía filial TE Magnetics) para centros de datos, aviación eléctrica y aplicaciones de levitación magnética.", "moat": "Récords técnicos en tokamaks esféricos y demostración de sistema de imanes a 11,8 Tesla (nov-2025); riesgo: financiación y valuación no reveladas públicamente, camino largo a comercialización.", "country": "Reino Unido", "growth": "🟢 récord de campo magnético nov-2025, programa LEAPS de USD 52M con el Department of Energy de EEUU", "margin": null, "mkt": "", "preipo": true},
  {"id": "type-one-energy", "label": "Type One Energy", "ticker": "Privada (Serie B en curso, pre-money ~USD 900M)", "cat": "nuclear_fusion", "port": "", "role": "Desarrolla reactores stellarator de fusión nuclear, con planta piloto comercial \"Infinity Two\" de 350 MWe planeada.", "supplies": "Licencia tecnología de cable superconductor HTS VIPER de Commonwealth Fusion Systems/MIT; despliega su planta piloto en colaboración con Tennessee Valley Authority y Oak Ridge National Laboratory.", "moat": "Financiación robusta (>USD 160M más nota convertible de USD 87M) e inversores de peso (Breakthrough Energy Ventures, TDK Ventures); riesgo: tecnología stellarator pre-comercial, competencia con Helion Energy y TAE Technologies.", "country": "Estados Unidos", "growth": "🟢 Serie B en curso (objetivo USD 250M), carta de intención de TVA (sep-2025) para desplegar en el sitio Bull Run", "margin": null, "mkt": "", "preipo": true},
  {"id": "pacific-fusion", "label": "Pacific Fusion", "ticker": "Privada (Serie A >USD 900M, valuación no revelada)", "cat": "nuclear_fusion", "port": "", "role": "Desarrolla fusión por confinamiento inercial pulsado (tipo MagLIF), fundada por Eric Lander y ex científicos de LLNL/Sandia.", "supplies": "n/a (pre-comercial); construye planta de demostración desde el verano de 2026.", "moat": "Tercera startup de fusión mejor financiada del mundo, con respaldo de Eric Schmidt y General Catalyst; riesgo: tecnología sin ignición a escala completa, meta comercial recién en 2040.", "country": "Estados Unidos", "growth": "🟢 hito técnico jun-2026 (440 GW de potencia pico), ronda con tramos adicionales desbloqueados por hitos técnicos", "margin": null, "mkt": "", "preipo": true},
  {"id": "nissan-chemical", "label": "Nissan Chemical Corporation", "ticker": "4021 · TSE", "cat": "chemicals", "port": "", "role": "Química diversificada japonesa, proveedor de recubrimientos antirreflectantes (ARC) y materiales multicapa para litografía EUV.", "supplies": "Recubrimientos BARC/ARC y materiales multicapa EUV para fabricación de semiconductores, con tecnología licenciada de Brewer Science (EEUU).", "moat": "Crecimiento fuerte y sostenido en materiales EUV/multicapa (+31% a +39% interanual); riesgo: dependencia de una licencia tecnológica externa (Brewer Science) y falta de diversificación hacia CMP.", "country": "Japón", "growth": "🟢 ARC +31%, Multilayer Materials +39%, EUV Materials +36% interanual; beneficio neto récord en FY marzo 2026", "margin": 0.226, "mkt": "4021"},
  {"id": "chang-chun-group", "label": "Chang Chun Group", "ticker": "Privada (filial cotizada Chang Chun Petrochemical · 1717 · TWSE)", "cat": "chemicals", "port": "", "role": "Conglomerado químico taiwanés, uno de los mayores productores mundiales de fotorresistentes, PVA y materiales electrónicos, pilar de la cadena de suministro local de TSMC.", "supplies": "Fotorresistentes, foil de cobre y materiales electrónicos especializados a fabricantes de semiconductores taiwaneses, principalmente TSMC.", "moat": "Integración vertical masiva en petroquímicos y materiales electrónicos dentro de Taiwán; riesgo: alta concentración geográfica en Taiwán, expuesta a riesgo geopolítico del estrecho.", "country": "Taiwán", "growth": "🟢 demanda sostenida por expansión de capacidad de TSMC y foundries taiwanesas", "margin": null, "mkt": "", "preipo": true},
  {"id": "stella-chemifa", "label": "Stella Chemifa", "ticker": "4109 · TSE", "cat": "chemicals", "port": "", "role": "Casi monopolista japonés de ácido fluorhídrico de alta pureza (HF), insumo crítico para grabado (etching) de semiconductores.", "supplies": "HF de grado electrónico a Samsung Electronics y SK Hynix, insumo central del conflicto comercial Japón-Corea de 2019 (controles de exportación japoneses).", "moat": "Cuota dominante japonesa en HF ultra-puro; riesgo: alta concentración de producción y exposición directa a decisiones de política comercial gubernamental (ya usado como arma en 2019).", "country": "Japón", "growth": "🟡 demanda estable ligada al ciclo de capex de memoria y lógica avanzada", "margin": null, "mkt": "4109"},
  {"id": "brewer-science", "label": "Brewer Science", "ticker": "Privada", "cat": "chemicals", "port": "", "role": "Fabricante estadounidense de materiales especializados de litografía (recubrimientos antirreflectantes, materiales de bonding temporal) para semiconductores avanzados.", "supplies": "Licencia tecnología de recubrimientos ARC a Nissan Chemical (acuerdo desde 1997, renovado hasta 2028); provee materiales de litografía a fabricantes de semiconductores en EEUU.", "moat": "Rara excepción estadounidense en un mercado de materiales de litografía dominado por Japón; riesgo: escala menor frente a competidores japoneses (JSR, TOK, Shin-Etsu, Sumitomo Chemical).", "country": "Estados Unidos", "growth": "🟢 beneficiada por inversión en fabs de EEUU (CHIPS Act) y demanda de empaquetado avanzado", "margin": null, "mkt": "", "preipo": true},
  {"id": "jcet", "label": "JCET Group", "ticker": "600584 · SSE", "cat": "osat", "port": "", "role": "Mayor proveedor OSAT (ensamblaje y test de semiconductores) de China continental, tercero a nivel mundial.", "supplies": "Empaquetado avanzado 2.5D/3D, SiP y test para diseñadores fabless chinos y globales, incluyendo chips lógicos, memoria e IA/HPC.", "moat": "Escala de \"campeón nacional\" chino en OSAT construida sobre la adquisición de STATS ChipPAC (2015) y capacidad de packaging avanzado chiplet; riesgo clave: objetivo directo de controles de exportación de EE.UU. y tensión tecnológica China-EEUU.", "country": "China", "growth": "🟡 ingresos casi planos (+0.7% TTM) pero el segmento de packaging avanzado/IA crece más rápido", "margin": 0.07, "mkt": "600584"},
  {"id": "pti", "label": "Powertech Technology (PTI)", "ticker": "6239 · TWSE", "cat": "osat", "port": "", "role": "OSAT taiwanés especializado en empaquetado y test de memoria (DRAM/NAND/MCP) y SiP lógico.", "supplies": "Empaqueta y testea memoria para fabricantes IDM globales, con creciente foco en HBM para IA.", "moat": "Especialista independiente líder en packaging de memoria con relaciones profundas con IDMs; riesgo clave: concentración en el ciclo cíclico de memoria y competencia de ASE/JCET.", "country": "Taiwán", "growth": "🟢 +25.2% YoY en 4T25 impulsado por demanda de HBM/IA", "margin": 0.1, "mkt": "6239"},
  {"id": "kyec", "label": "King Yuan Electronics (KYEC)", "ticker": "2449 · TWSE", "cat": "osat", "port": "", "role": "Casa de test de semiconductores pure-play líder en Taiwán, prueba de oblea y test final para chips lógicos/IA.", "supplies": "Servicios de test dedicados para clientes fabless del ecosistema de fundición taiwanés, ante alta demanda de capacidad de test de chips IA.", "moat": "Líder independiente en test IC en Taiwán con fuerte capex hacia AI; riesgo clave: expansión agresiva de capacidad (NT$50B) crea riesgo de ejecución si la demanda IA se enfría.", "country": "Taiwán", "growth": "🟢 ingresos récord, expansión a Singapur con producción masiva estimada para 2027", "margin": 0.12, "mkt": "2449"},
  {"id": "chipbond", "label": "Chipbond Technology", "ticker": "6147 · TPEx", "cat": "osat", "port": "", "role": "Mayor proveedor mundial de bumping y empaquetado COF/COG para drivers de pantalla (DDIC), diversificando hacia GaN/SiC.", "supplies": "Bumping de oblea y empaquetado para diseñadores DDIC y fabricantes de paneles; empaquetado de semiconductores de compuesto (GaN/SiC) para automotriz y potencia.", "moat": "Dominio de nicho en empaquetado DDIC a escala global; riesgo clave: dependencia del ciclo cíclico de la industria de paneles de pantalla.", "country": "Taiwán", "growth": "🟢 +5.5% YoY 2025, fuerte revalorización bursátil por narrativa IA/potencia", "margin": 0.1, "mkt": "6147"},
  {"id": "biren", "label": "Biren Technology", "ticker": "6082 · HKEX", "cat": "fabless", "port": "", "role": "Diseñador fabless chino de GPUs/GPGPU de IA, alternativa doméstica a Nvidia para entrenamiento e inferencia.", "supplies": "GPGPUs de las series BR100/BR104 para infraestructura de nube e IA estatal china.", "moat": "Uno de los diseños de GPU domésticos chinos más avanzados con fuerte respaldo estatal; riesgo clave: exclusión de TSMC tras su inclusión en la Entity List (2023), forzada a fabricar en nodos domésticos menos avanzados.", "country": "China", "growth": "🟢 IPO en Hong Kong con salto de ~76-82% en el debut (enero 2026), fuerte demanda pese a pérdidas", "margin": null, "mkt": "6082"},
  {"id": "moorethreads", "label": "Moore Threads", "ticker": "688795 · SSE (STAR Market)", "cat": "fabless", "port": "", "role": "Diseñador fabless chino de GPUs, pivotó de gaming a aceleradores de entrenamiento/inferencia IA, apodado el \"Nvidia de China\".", "supplies": "GPUs serie MTT S y aceleradores IA para clientes de nube/datacenter chinos.", "moat": "Talento profundo ex-Nvidia (fundador con 14 años en Nvidia); riesgo clave: en la Entity List de EE.UU., bloquea acceso a IP/herramientas/materiales estadounidenses, aún no rentable.", "country": "China", "growth": "🟢 IPO en STAR Market con +468% en el debut (2026); ingresos explosivos desde una base pequeña", "margin": null, "mkt": "688795"},
  {"id": "unisoc", "label": "UNISOC", "ticker": "Privada (IPO en preparación)", "cat": "fabless", "port": "", "role": "Diseñador fabless de SoCs móviles, IoT y chips automotrices de gama media/baja.", "supplies": "Chipsets para smartphones Android de gama económica en mercados emergentes.", "moat": "Experiencia en nodos maduros costo-competitivos, #4 proveedor global de procesadores de aplicación móvil; riesgo clave: confinado a segmento de bajo margen, compite en precio con MediaTek/Qualcomm.", "country": "China", "growth": "🟡 ~13% de cuota global de chips smartphone en 2024, estable", "margin": null, "mkt": "", "preipo": true},
  {"id": "starfive", "label": "StarFive Technology", "ticker": "Privada", "cat": "fabless", "port": "", "role": "Diseñador fabless de chips e IP RISC-V para edge, AIoT y, cada vez más, procesadores de centro de datos.", "supplies": "SoCs JH7100/JH7110, placas de desarrollo VisionFive y el chip \"Lion Rock\" para datacenter basado en RISC-V.", "moat": "Pionero y líder de facto del ecosistema RISC-V chino; riesgo clave: el ecosistema RISC-V aún es inmaduro frente a Arm/x86.", "country": "China", "growth": "🟡 expansión de nicho edge hacia datacenter (lanzamiento de Lion Rock en 2025)", "margin": null, "mkt": "", "preipo": true},
  {"id": "loongson", "label": "Loongson Technology", "ticker": "688047 · SSE (STAR Market)", "cat": "fabless", "port": "", "role": "Diseña CPUs con su propio set de instrucciones LoongArch para PCs, servidores y sistemas gubernamentales/embebidos.", "supplies": "CPUs de las series 3A/3B (desktop) y 3C (servidor) para agencias gubernamentales chinas y OEMs domésticos.", "moat": "Campeón estatal de autosuficiencia de CPU/ISA de China, controla su propio ISA evitando licencias de Arm/x86; riesgo clave: fuerte dependencia de compras gubernamentales, no rentable.", "country": "China", "growth": "🟡 +26% YoY 2025, pero margen neto muy negativo (-64.75%)", "margin": -0.65, "mkt": "688047"},
  {"id": "enflame", "label": "Enflame Technology", "ticker": "Privada (IPO STAR Market aprobada, aún no cotiza)", "cat": "fabless", "port": "", "role": "Diseñador fabless de chips aceleradores de entrenamiento/inferencia IA en la nube, uno de los \"cuatro dragones\" chinos de chips IA.", "supplies": "Tarjetas y sistemas aceleradores IA, vendidos casi en su totalidad a un cliente ancla (Tencent, ~84% de ingresos 2025).", "moat": "Respaldo de un inversor/cliente ancla dominante y cuatro generaciones de arquitectura propia; riesgo clave: concentración extrema en un solo cliente y pérdidas acumuladas grandes.", "country": "China", "growth": "🟢 ingresos +~37% YoY 2025, pero pérdidas crecientes", "margin": null, "mkt": "", "preipo": true},
  {"id": "nexperia", "label": "Nexperia", "ticker": "Privada (subsidiaria de Wingtech Technology, 600745 · SSE)", "cat": "materials", "port": "", "role": "Fabrica semiconductores discretos, ICs lógicos y MOSFETs de alto volumen para automotriz, industrial y consumo.", "supplies": "Diodos, transistores, MOSFETs y protección ESD para Tier-1 automotrices y OEMs de consumo.", "moat": "Escala masiva en discretos de nodo maduro con calificación automotriz profunda; riesgo clave: en octubre 2025 el gobierno holandés tomó control operativo (Ley de Disponibilidad de Bienes) por presión de EE.UU., y China respondió bloqueando la exportación de chips terminados, generando una crisis de suministro automotriz.", "country": "Países Bajos", "growth": "🔴 disrupción severa desde finales de 2025 por la disputa Países Bajos-China", "margin": null, "mkt": "", "preipo": true},
  {"id": "vishay", "label": "Vishay Intertechnology", "ticker": "VSH · NYSE", "cat": "materials", "port": "", "role": "Fabrica semiconductores discretos y componentes pasivos (resistencias, capacitores, inductores, MOSFETs) para industrial, automotriz y computación.", "supplies": "Componentes pasivos/discretos para OEMs automotrices, automatización industrial y fuentes de poder de datacenter.", "moat": "Catálogo diversificado y ciclos de diseño largos con clientes industriales/automotrices; riesgo clave: presión de precios commoditizada y demanda cíclica.", "country": "Estados Unidos", "growth": "🔴 débil en 2025, ingresos planos/en baja (~$800.9M en 4T25)", "margin": null, "mkt": "VSH"},
  {"id": "juniper", "label": "Juniper Networks", "ticker": "No cotiza — adquirida por HPE (HPE · NYSE), cierre julio 2025", "cat": "networking", "port": "", "role": "Fabricaba routers, switches y redes con IA (Mist AI) para empresas, proveedores de servicio y datacenters; ahora integrada en la unidad de networking de HPE.", "supplies": "Routers core/edge, switches de datacenter y networking de campus nativo en IA.", "moat": "Mist AI y fuerte base instalada de routers de proveedores de servicio; riesgo clave: integración post-adquisición y competencia creciente de Arista/Nvidia en networking IA de datacenter.", "country": "Estados Unidos", "growth": "🟢 crecimiento \"récord\" del segmento de networking de HPE tras la adquisición", "margin": null, "mkt": ""},
  {"id": "f5", "label": "F5 Inc", "ticker": "FFIV · NASDAQ", "cat": "networking", "port": "", "role": "Provee controladores de entrega de aplicaciones (ADC), balanceo de carga y seguridad de apps/APIs para datacenters empresariales y en la nube.", "supplies": "Appliances/software BIG-IP, NGINX y seguridad distribuida en la nube para empresas, bancos, telcos y proveedores cloud.", "moat": "Fuerte arraigo empresarial en entrega y seguridad de aplicaciones críticas; riesgo clave: migración de hardware hacia competidores cloud-native.", "country": "Estados Unidos", "growth": "🟢 ingresos FY25 $3.1B, +10% YoY", "margin": null, "mkt": "FFIV"},
  {"id": "americantower", "label": "American Tower", "ticker": "AMT · NYSE", "cat": "connectivity_infra", "port": "", "role": "REIT que posee y opera torres de comunicaciones inalámbricas y, cada vez más, datacenters (vía CoreSite) arrendados a operadoras y clientes digitales.", "supplies": "Espacio de torre/colocación y colocation de datacenter (CoreSite) principalmente a operadoras móviles y clientes cloud/interconexión.", "moat": "Huella inmobiliaria irremplazable con contratos de arrendamiento multi-inquilino de largo plazo; riesgo clave: ciclicidad del capex de operadoras y sensibilidad a tasas de interés como REIT.", "country": "Estados Unidos", "growth": "🟢 crecimiento estable en 2025, AFFO e ingresos por encima de estimaciones", "margin": null, "mkt": "AMT"},
  {"id": "crowncastle", "label": "Crown Castle", "ticker": "CCI · NYSE", "cat": "connectivity_infra", "port": "", "role": "REIT propietaria/operadora de infraestructura inalámbrica compartida (torres) arrendada a operadoras móviles en EE.UU.", "supplies": "Espacio de torre para T-Mobile, AT&T y Verizon (~90% de ingresos de renta de sitios).", "moat": "Ubicaciones físicas de torres irremplazables y altos costos de cambio para operadoras; riesgo clave: concentración de clientes (3 inquilinos = ~90% de ingresos) y consolidación de redes de operadoras.", "country": "Estados Unidos", "growth": "🟡 en repliegue hacia modelo pure-play de torres tras vender su negocio de fibra/small cells por $8.5B", "margin": null, "mkt": "CCI"},
  {"id": "gds", "label": "GDS Holdings", "ticker": "GDS · NASDAQ (también 9698 · HKEX)", "cat": "dc_reit", "port": "", "role": "Operador chino de datacenters de terceros (carrier-neutral), construye instalaciones hyperscale y de colocation, pivotando hacia datacenters listos para IA/GPU.", "supplies": "Espacio de datacenter y colocation para grandes proveedores cloud e internet chinos.", "moat": "Escala con permisos de terreno/energía en metrópolis chinas tier-1 e interconexión carrier-neutral; riesgo clave: exposición regulatoria/geopolítica (controles de datos de China, estructura VIE), alto apalancamiento y base de clientes concentrada.", "country": "China", "growth": "🟢 volvió a rentabilidad en 2025 tras pérdida neta en 2024; comprometió hasta RMB 50B para expansión de capacidad de IA", "margin": null, "mkt": "GDS"},
  {"id": "adva", "label": "ADVA Optical Networking (Adtran Networks)", "ticker": "ADV · XETRA (mayoría propiedad de Adtran Holdings, ADTN · NASDAQ)", "cat": "networking", "port": "", "role": "Diseña equipos de networking óptico y de acceso —transporte de fibra, acceso de banda ancha y sincronización de red— para operadoras telco y empresas.", "supplies": "Equipos de transporte óptico y acceso para operadoras europeas, posicionada como alternativa \"de confianza\" a Huawei/ZTE.", "moat": "Fuerte arraigo con operadoras europeas y políticas de \"des-risking\" alejándose de proveedores chinos; riesgo clave: competencia intensa de precios de Huawei/Nokia/Ciena/Infinera.", "country": "Alemania", "growth": "🟢 recuperación, ingresos FY25 +17.5% YoY, margen no-GAAP volvió a positivo (+4.8%)", "margin": null, "mkt": "ADV"},
  {"id": "fabrinet", "label": "Fabrinet", "ticker": "FN · NYSE", "cat": "optics", "port": "", "role": "Manufactura de precisión óptica y electromecánica subcontratada para transceptores ópticos, automotriz, médico e industrial.", "supplies": "Fabrica transceptores ópticos 800G/1.6T bajo contrato para OEMs de networking y datacom.", "moat": "Escala y certificaciones de manufactura de precisión con relaciones OEM multi-año difíciles de resustituir; riesgo clave: concentración de clientes y dependencia del ciclo de capex de IA/datacenter.", "country": "Tailandia (incorporada en Islas Caimán)", "growth": "🟢 ingresos récord FY25 $3.4B, +19% YoY, impulsado por demanda de transceptores ópticos de IA", "margin": null, "mkt": "FN"},
  {"id": "colt", "label": "Colt Technology Services", "ticker": "Privada (propiedad de Fidelity Investments)", "cat": "connectivity_infra", "port": "", "role": "Proveedor de conectividad de red empresarial —construye y opera redes de fibra, transmisión de datos/voz e infraestructura de baja latencia para datos de mercado.", "supplies": "Conectividad de fibra y baja latencia a grandes empresas, instituciones financieras (vía MarketPrizm) y operadoras en Europa, EE.UU. y Asia.", "moat": "Red de fibra paneuropea/asiática con nicho fuerte en conectividad de servicios financieros; riesgo clave: buildout de red intensivo en capital y competencia de BT/Deutsche Telekom/Lumen.", "country": "Reino Unido", "growth": "🟢 fuerte, ingresos del grupo +32% a €2.2B en 2024 (impulsado por adquisición de Lumen EMEA)", "margin": null, "mkt": "", "preipo": true},
  {"id": "wingtech", "label": "Wingtech Technology", "ticker": "600745 · SSE", "cat": "servers", "port": "", "role": "Conglomerado chino de manufactura electrónica (ODM) y matriz de Nexperia, con exposición directa a la disputa de control de chips entre Países Bajos y China en 2025.", "supplies": "Servicios ODM de diseño/manufactura de smartphones y electrónica de consumo; controla la propiedad de Nexperia (semiconductores discretos).", "moat": "Verticalización ODM combinada con control accionario de Nexperia; riesgo clave: sancionado por EE.UU. (Entity List 2023) y en el centro de la disputa de control corporativo de Nexperia con el gobierno holandés.", "country": "China", "growth": "🔴 disrupción por la crisis de Nexperia y controles de exportación", "margin": null, "mkt": "600745"},
  {"id": "sba", "label": "SBA Communications", "ticker": "SBAC · NASDAQ", "cat": "connectivity_infra", "port": "", "role": "REIT propietaria/operadora de torres inalámbricas, tercer mayor operador de torres de EE.UU. tras American Tower y Crown Castle.", "supplies": "Espacio de torre arrendado a operadoras móviles en América, principalmente en EE.UU. y Latinoamérica.", "moat": "Cartera de torres bien ubicada en mercados de EE.UU. y Latinoamérica de alto crecimiento; riesgo clave: concentración de clientes en pocas operadoras grandes.", "country": "Estados Unidos", "growth": "🟡 crecimiento estable, moderado por consolidación de operadoras", "margin": null, "mkt": "SBAC"},
  {"id": "chindata", "label": "Chindata Group", "ticker": "Privada (ex-NASDAQ:CD, deslistada tras adquisición por Bain Capital 2023)", "cat": "dc_reit", "port": "", "role": "Operador de datacenters hyperscale en China y Asia emergente (India, Malasia, tras fusión con Bridge Data Centres).", "supplies": "Provee espacio, energía y colocation hyperscale a Alibaba Cloud, Bytedance y otros clientes cloud chinos; expande a mercados del sudeste asiático.", "moat": "Dominio del mercado de datacenters de nivel hyperscale en China continental con permisos y terreno difíciles de replicar; riesgo de controles de capital/exportación de chips avanzados a China y tensión regulatoria EE.UU.-China.", "country": "China / Singapur (holding, operaciones pan-asiáticas)", "growth": "🟢 fusión con Bridge Data Centres crea plataforma pan-asiática de ~$4B+ tras salida de Bain Capital", "margin": null, "mkt": "", "preipo": true},
  {"id": "vantage-dc", "label": "Vantage Data Centers", "ticker": "Privada", "cat": "dc_reit", "port": "", "role": "Desarrollador y operador global de campus de datacenters hyperscale para nube y entrenamiento de IA a gran escala.", "supplies": "Provee capacidad de datacenter (colocation y \"shell\" a medida) a Microsoft, Amazon, Meta y otros hyperscalers, incluyendo el megacampus \"Frontier\" de $25.000M en Texas.", "moat": "Acceso a capital masivo (DigitalBridge/Silver Lake, $9.200M en equity) y bancos de terreno/energía preadquiridos en mercados clave; riesgo de sobreoferta y cuellos de botella en interconexión eléctrica.", "country": "Estados Unidos (HQ Denver, CO)", "growth": "🟢 expansión agresiva multi-billonaria (campus Frontier 2.5GW en Texas)", "margin": null, "mkt": "", "preipo": true},
  {"id": "stack-infra", "label": "STACK Infrastructure", "ticker": "Privada", "cat": "dc_reit", "port": "", "role": "Operador global de datacenters hyperscale y de colocation en América, EMEA y APAC.", "supplies": "Provee capacidad de datacenter a hyperscalers y clientes cloud; Blue Owl evalúa venta de su portafolio asiático por más de $30.000M.", "moat": "Escala global multi-región respaldada por capital institucional de Blue Owl; riesgo de concentración de capital y exposición a ciclo de tasas de interés que encarece financiamiento de nueva capacidad.", "country": "Estados Unidos (HQ Denver/Kansas City) — propiedad de Blue Owl Capital", "growth": "🟢 evaluando venta de portafolio APAC por $30B+, señal de demanda desbordante", "margin": null, "mkt": "", "preipo": true},
  {"id": "crusoe-energy", "label": "Crusoe Energy", "ticker": "Pre-IPO ~$30B", "cat": "hpc_super", "port": "", "role": "\"Fábrica de IA\" verticalmente integrada: construye y opera datacenters de GPU alimentados por energía propia (gas asociado, nuclear, renovables) para entrenamiento de IA a gran escala.", "supplies": "Provee cómputo GPU y datacenters \"energy-first\" a OpenAI (proyecto Stargate Abilene), y capacidad de nube de IA a otros clientes enterprise.", "moat": "Integración única energía-cómputo (usa gas de venteo/asociado y contratos de energía dedicados) que reduce tiempos de conexión a red; riesgo de apalancamiento alto por financiamiento de deuda para comprar GPUs Nvidia.", "country": "Estados Unidos (HQ Denver, CO)", "growth": "🟢 valuación triplicada a ~$30B en 2026, ronda de $3.000M en curso", "margin": null, "mkt": "", "preipo": true},
  {"id": "voltage-park", "label": "Voltage Park", "ticker": "Privada", "cat": "hpc_super", "port": "", "role": "Nube de GPU independiente (neocloud) fundada con donación filantrópica de Navigation Fund; ahora rebautizada como Lightning AI tras pivote de producto.", "supplies": "Renta clústeres de GPU Nvidia H100/H200 bajo demanda a laboratorios de IA y empresas para entrenamiento e inferencia.", "moat": "Origen de capital no tradicional (financiada por donación filantrópica en criptoactivos) le dio ventaja de costo temprana; riesgo de comoditización frente a neoclouds mejor capitalizados y de repricing de GPUs H100 obsoletas.", "country": "Estados Unidos (HQ San Francisco, CA)", "growth": "🟡 pivote de marca a \"Lightning AI\" en 2026 sugiere reposicionamiento estratégico", "margin": null, "mkt": "", "preipo": true},
  {"id": "fluidstack", "label": "FluidStack", "ticker": "Pre-IPO ~$18B", "cat": "hpc_super", "port": "", "role": "Neocloud de GPU que construye y opera supercomputadores de IA a gran escala (incluyendo el proyecto de 1GW en Francia) para laboratorios frontera.", "supplies": "Provee cómputo GPU masivo a Anthropic (acuerdo histórico de $50.000M) y Google, además de infraestructura para clientes enterprise de IA.", "moat": "Contratos ancla de largo plazo con Anthropic y Google que garantizan demanda multi-año; riesgo de ejecución en construir 1GW+ de capacidad nueva y de concentración de clientes.", "country": "Reino Unido / Estados Unidos", "growth": "🟢 valuación de $18.000M en 2026 tras ronda de $1.000M+, ancla Anthropic de $50.000M", "margin": null, "mkt": "", "preipo": true},
  {"id": "nscale", "label": "Nscale", "ticker": "Pre-IPO ~$14.6B", "cat": "hpc_super", "port": "", "role": "Neocloud europeo de GPU construyendo datacenters de IA soberana en el Reino Unido, Noruega y Europa continental.", "supplies": "Provee cómputo GPU Nvidia a Microsoft (partner de capacidad para Azure) y a clientes europeos de IA soberana.", "moat": "Posicionamiento como \"campeón de IA soberana europea\" con respaldo de Nvidia y contratos con Microsoft; riesgo de competencia de hyperscalers con más capital y de dependencia energética europea.", "country": "Reino Unido / Noruega", "growth": "🟢 Serie C de $2.000M en 2026 (mayor ronda europea en la historia), valuación $14.600M", "margin": null, "mkt": "", "preipo": true},
  {"id": "tensorwave", "label": "TensorWave", "ticker": "Privada", "cat": "hpc_super", "port": "", "role": "Neocloud de GPU especializado en infraestructura AMD Instinct (MI300/MI325), alternativa a los neoclouds basados en Nvidia.", "supplies": "Provee cómputo GPU AMD a startups y empresas de IA que buscan diversificar fuera del ecosistema Nvidia/CUDA.", "moat": "Único neocloud puro-AMD de escala, con inversión estratégica directa de AMD; riesgo de ecosistema de software (ROCm) menos maduro que CUDA y dependencia de un solo proveedor de silicio.", "country": "Estados Unidos (HQ Las Vegas, NV)", "growth": "🟢 Serie B de $350M liderada por AMD y Magnetar en 2026, valuación $1.550M", "margin": null, "mkt": "", "preipo": true},
  {"id": "northern-data", "label": "Northern Data Group", "ticker": "NB2 · Frankfurt (Scale/Prime Standard)", "cat": "hpc_super", "port": "", "role": "Ex-minero de Bitcoin reconvertido en proveedor europeo de infraestructura de IA/HPC (unidad Taiga Cloud) tras vender su negocio de minería.", "supplies": "Provee cómputo GPU Nvidia en la nube (Taiga Cloud) a clientes de entrenamiento de IA en Europa; antes ancla de minería a pools de Bitcoin.", "moat": "Reconversión temprana de infraestructura energética de minería cripto a datacenters de IA; riesgo financiero alto por historial de dificultades de liquidez, litigios (Tether) y estructura de capital compleja.", "country": "Alemania", "growth": "🟡 pivote completo a IA/HPC tras vender unidad de minería Bitcoin en 2025-2026, pero con historial financiero volátil", "margin": null, "mkt": "NB2"},
  {"id": "yotta-data-services", "label": "Yotta Data Services", "ticker": "Privada", "cat": "hpc_super", "port": "", "role": "Proveedor indio de datacenters e infraestructura de \"IA soberana\" (Shakti Cloud), parte del grupo Hiranandani.", "supplies": "Provee cómputo GPU Nvidia (Shakti Cloud) a startups, gobierno y empresas indias bajo la iniciativa de IA soberana del país.", "moat": "Posicionamiento como socio preferente del gobierno indio para IA soberana con respaldo de Nvidia y del grupo inmobiliario Hiranandani; riesgo de competencia de hyperscalers globales entrando a India y de escasez de energía local.", "country": "India", "growth": "🟢 reconocida \"Compañía India del Año 2026\" por Frost & Sullivan en IA soberana, expansión agresiva de capacidad Shakti Cloud", "margin": null, "mkt": "", "preipo": true},
  {"id": "zayo-group", "label": "Zayo Group", "ticker": "Privada (ex-NYSE:ZAYO, deslistada 2020)", "cat": "connectivity_infra", "port": "", "role": "Operador de red de fibra óptica de largo recorrido y \"middle mile\" que conecta datacenters, hyperscalers y operadores de telecomunicaciones en Norteamérica y Europa.", "supplies": "Provee capacidad de fibra oscura y ancho de banda mayorista a hyperscalers y operadores de datacenter para interconectar clústeres de entrenamiento de IA distribuidos.", "moat": "Red de fibra de largo recorrido difícil de replicar (derechos de vía histórico); riesgo de apalancamiento alto tras compra apalancada por EQT/Digital Colony ($14.300M).", "country": "Estados Unidos (HQ Boulder, CO)", "growth": "🟢 demanda de fibra de alta capacidad dispara por interconexión de datacenters de IA distribuidos", "margin": null, "mkt": "", "preipo": true},
  {"id": "cologix", "label": "Cologix", "ticker": "Privada", "cat": "dc_reit", "port": "", "role": "Operador de datacenters de colocation e interconexión \"edge\", con expansión reciente a capacidad \"AI-ready\" a gran escala.", "supplies": "Provee colocation, interconexión y capacidad edge densa a operadores de red, nubes y clientes empresariales en Norteamérica.", "moat": "Red de 40+ datacenters edge en mercados secundarios de Norteamérica, densamente interconectados; riesgo de competir contra jugadores hyperscale de mayor escala en capacidad de IA pura.", "country": "Estados Unidos (HQ Denver, CO)", "growth": "🟢 levantó $1.500M en 2024-2026 para campus AI-ready, plan de $5.000-7.000M en Ashburn", "margin": null, "mkt": "", "preipo": true},
  {"id": "ntt-gdc", "label": "NTT Global Data Centers", "ticker": "9432 · Tokyo (matriz NTT Corporation)", "cat": "dc_reit", "port": "", "role": "División global de datacenters de NTT, uno de los mayores operadores hyperscale del mundo con presencia en más de 20 países.", "supplies": "Provee capacidad de datacenter e infraestructura de red a hyperscalers, empresas y gobiernos globalmente; planea duplicar capacidad ante demanda de IA.", "moat": "Escala global respaldada por el balance de NTT Corporation (una de las telcos más grandes del mundo) y relaciones profundas con hyperscalers; riesgo de competencia de precios en mercado de datacenters saturado.", "country": "Japón", "growth": "🟢 plan de duplicar capacidad global anunciado en 2026 ante demanda de IA", "margin": null, "mkt": "9432"},
  {"id": "princeton-digital-group", "label": "Princeton Digital Group", "ticker": "Privada", "cat": "dc_reit", "port": "", "role": "Desarrollador y operador de datacenters hyperscale en Asia emergente (China, India, Indonesia, Corea del Sur, Japón), respaldado por Warburg Pincus.", "supplies": "Provee capacidad de datacenter a hyperscalers y clientes cloud en mercados asiáticos de alto crecimiento, incluyendo un proyecto de $700M en Corea del Sur.", "moat": "Presencia temprana y diversificada en mercados asiáticos fragmentados y de difícil entrada regulatoria; riesgo de financiamiento vía deuda masiva ($5.000M planeados) en entorno de tasas altas.", "country": "Singapur (operaciones pan-asiáticas)", "growth": "🟢 plan de levantar hasta $5.000M en deuda para expansión de datacenters de IA en Asia", "margin": null, "mkt": "", "preipo": true},
  {"id": "edgeconnex", "label": "EdgeConneX", "ticker": "Privada — propiedad de EQT", "cat": "dc_reit", "port": "", "role": "Desarrollador global de datacenters \"edge\" e hyperscale, ahora eje de la nueva estrategia de infraestructura de IA de EQT.", "supplies": "Provee campus de datacenter dedicados a clientes de IA como Lambda (fábrica de IA en Chicago) y capacidad edge/hyperscale en mercados secundarios globales.", "moat": "Plataforma ancla de la estrategia de inversión en IA de EQT, con compromiso de capital de $2.400M de CPP Investments; riesgo de ejecución en escalar decenas de campus simultáneamente.", "country": "Estados Unidos (HQ Herndon, VA)", "growth": "🟢 ancla de la nueva estrategia \"AI Infrastructure\" de EQT con $2.400M de CPP Investments", "margin": null, "mkt": "", "preipo": true},
  {"id": "lightning-ai", "label": "Lightning AI", "ticker": "Privada", "cat": "hpc_super", "port": "", "role": "Plataforma de desarrollo e infraestructura de IA (ex-Voltage Park bajo nuevo posicionamiento de marca) que combina PyTorch Lightning con nube de GPU.", "supplies": "Provee entorno de desarrollo y cómputo GPU para entrenamiento/fine-tuning a desarrolladores de IA e investigadores.", "moat": "Base instalada de PyTorch Lightning (framework open-source ampliamente usado) como canal de adquisición de clientes; riesgo de competir contra neoclouds mejor financiados en el segmento puro de infraestructura.", "country": "Estados Unidos (HQ San Francisco, CA)", "growth": "🟡 reposicionamiento estratégico en 2026 tras absorber activos de Voltage Park", "margin": null, "mkt": "", "preipo": true},
  {"id": "fourier-intelligence", "label": "Fourier Intelligence", "ticker": "Privada", "cat": "robotics_physical", "port": "", "role": "Diseña y fabrica robots humanoides de propósito general (línea GR-1/GR-2) y exoesqueletos/robots de rehabilitación médica.", "supplies": "Robots humanoides y sistemas de rehabilitación a hospitales, centros de investigación y fabricantes que licencian su plataforma GR para integración industrial.", "moat": "Pionero chino en humanoides con enfoque dual médico+industrial y ventas ya a clientes de investigación globales; riesgo: mercado saturado de humanoides chinos (UBTech, AgiBot, Unitree) con guerra de precios y controles de exportación de EEUU sobre chips avanzados.", "country": "China", "growth": "🟢 Serie E de $109M (ene-2025), parte de la ola de posibles IPOs de robótica china.", "margin": null, "mkt": "", "preipo": true},
  {"id": "sanctuary-ai", "label": "Sanctuary AI", "ticker": "Privada", "cat": "robotics_physical", "port": "", "role": "Desarrolla robots humanoides de propósito general (Phoenix) controlados por su sistema de IA Carbon para tareas industriales y de manufactura.", "supplies": "Robots humanoides piloto desplegados en plantas de manufactura de clientes automotrices (p. ej. Magna International).", "moat": "Uno de los pioneros de humanoides \"control-first\" con manos altamente destras; riesgo: crisis financiera severa, ronda de apenas $10M en notas convertibles (ene-2025), cambio forzado de CEO y despidos (nov-2024).", "country": "Canadá", "growth": "🔴 Señales claras de estrés financiero y reestructuración de liderazgo.", "margin": null, "mkt": "", "preipo": true},
  {"id": "skild-ai", "label": "Skild AI", "ticker": "Pre-IPO ~$14B", "cat": "robotics_physical", "port": "", "role": "Construye un \"modelo fundacional\" de IA general para robots (cualquier hardware), y desde 2026 también fabrica robots propios tras adquirir el negocio robótico de Zebra Technologies.", "supplies": "Software de percepción y control tipo \"brain\" para robots humanoides y móviles de múltiples fabricantes; plataformas físicas para logística tras la adquisición de Zebra Robotics.", "moat": "Modelo fundacional agnóstico de hardware entrenado con datos masivos multi-robot, respaldado por el mayor pool de capital del sector; riesgo: pivote reciente a fabricación de hardware diluye el enfoque \"software puro\" y añade complejidad operativa.", "country": "Estados Unidos", "growth": "🟢 Serie C de $1.4B (ene-2026) liderada por SoftBank, valuación >$14B; adquisición de Zebra Robotics (abr-2026).", "margin": null, "mkt": "", "preipo": true},
  {"id": "berkshire-grey", "label": "Berkshire Grey", "ticker": "No cotiza (ex-Nasdaq: BGRY, deslistada)", "cat": "robotics_physical", "port": "", "role": "Fabrica sistemas de automatización robótica con IA para picking, clasificación y empaque en almacenes de e-commerce y logística.", "supplies": "Sistemas robóticos de fulfillment a operadores logísticos y retailers, ahora integrados en el portafolio de robótica industrial de SoftBank.", "moat": "Tecnología de picking robótico madura y probada a escala; riesgo: fue adquirida por SoftBank en 2023 con un descuento del 86% frente a su debut en bolsa vía SPAC, evidenciando fallas de ejecución comercial y quema de capital.", "country": "Estados Unidos", "growth": "🔴 Absorbida por SoftBank tras colapso de valuación pública; ahora integrada en su unidad de robótica junto a ABB Robotics.", "margin": null, "mkt": ""},
  {"id": "covariant", "label": "Covariant", "ticker": "Privada", "cat": "robotics_physical", "port": "", "role": "Desarrolla IA de percepción y manipulación (RFM-1) para robots de picking en almacenes; tras 2024 quedó reducida a una cáscara operativa tras el \"reverse acquihire\" de Amazon.", "supplies": "Licenció (no exclusivamente) su tecnología de IA de picking a Amazon; anteriormente desplegaba robots de picking en almacenes de terceros.", "moat": "Pionera en modelos fundacionales de manipulación robótica (\"RFM-1\"); riesgo: Amazon contrató a los tres fundadores y ~25% del equipo en agosto 2024 (~$380M+$20M diferidos), dejando a la empresa con solo ~20 empleados y prácticamente inoperante en 2026.", "country": "Estados Unidos", "growth": "🔴 Efectivamente desmantelada; caso de estudio de \"acquihire regulatorio\" bajo investigación por denuncia de whistleblower.", "margin": null, "mkt": "", "preipo": true},
  {"id": "dexterity", "label": "Dexterity Inc", "ticker": "Privada", "cat": "robotics_physical", "port": "", "role": "Construye brazos robóticos móviles duales (\"Physical AI\") para carga/descarga de camiones y contenedores en logística.", "supplies": "Sistemas robóticos DexR para carga/descarga de camiones a FedEx, UPS, Maersk, GXO Logistics y VF Corporation; JV con Sumitomo para 1,500 robots en Japón.", "moat": "Percepción + razonamiento + control de fuerza aplicado a tareas físicas altamente variables (carga de camiones), validado con clientes logísticos Fortune 500; riesgo: sector \"physical AI\" saturado con competencia de Dexterity, RightHand Robotics y Ambi Robotics por los mismos casos de uso.", "country": "Estados Unidos", "growth": "🟢 Ronda de $95M (mar-2025) a valuación $1.65B; expansión a Japón vía JV con Sumitomo y alianza con Kawasaki (jun-2026).", "margin": null, "mkt": "", "preipo": true},
  {"id": "righthand-robotics", "label": "RightHand Robotics", "ticker": "Privada", "cat": "robotics_physical", "port": "", "role": "Desarrolla el sistema RightPick para picking robótico de artículos individuales (each-picking) en fulfillment de e-commerce.", "supplies": "Sistemas de picking robótico y gestión de flotas a operadores de fulfillment de e-commerce.", "moat": "Tecnología de agarre adaptable de origen académico (Harvard/Yale/MIT) con más de una década de operación; riesgo: sin ronda de financiamiento confirmada desde 2022, señal de posible estancamiento frente a competidores mejor capitalizados (Dexterity, Ambi Robotics).", "country": "Estados Unidos", "growth": "🟡 Sin ronda nueva desde Serie C 2022; crecimiento no confirmado en 2025-2026.", "margin": null, "mkt": "", "preipo": true},
  {"id": "symbotic", "label": "Symbotic", "ticker": "SYM · Nasdaq", "cat": "robotics_physical", "port": "", "role": "Automatiza almacenes de gran escala con robots de IA para manejo de pallets, cajas y unidades individuales.", "supplies": "Sistemas de automatización de almacenes a Walmart (>84% de ingresos FY2025), Medline y otros; JV \"GreenBox\" (Warehouse-as-a-Service) con SoftBank, con C&S Wholesale Grocers como primer cliente.", "moat": "Backlog de $22.5B y contrato ancla con Walmart que garantiza volumen a largo plazo; riesgo: concentración extrema en un solo cliente (Walmart >84% de ingresos), pérdidas operativas GAAP persistentes, y conflicto de interés señalado (CEO Rick Cohen también preside C&S Wholesale Grocers, cliente de la JV GreenBox).", "country": "Estados Unidos", "growth": "🟡 Ingresos +26% interanual (FY2025: $2.25B) pero con pérdida operativa GAAP de $115M; alta dependencia de un solo cliente.", "margin": null, "mkt": "SYM"},
  {"id": "locus-robotics", "label": "Locus Robotics", "ticker": "Privada", "cat": "robotics_physical", "port": "", "role": "Fabrica robots móviles autónomos (AMR) para picking en almacenes bajo modelo Robotics-as-a-Service.", "supplies": "Robots AMR (Origin, Vector) y plataforma LocusONE a DHL Supply Chain (cliente ancla, expansión a 5,000 robots), GEODIS, Ryder, CEVA y Carhartt.", "moat": "Mayor flota desplegada del sector (17,000+ robots, 360+ sitios) y modelo RaaS agnóstico de cliente; riesgo: competencia intensa (Geek+, 6 River Systems/Ocado, Fetch/Zebra) y sin ronda nueva confirmada desde 2022 pese a rumores de IPO desde entonces.", "country": "Estados Unidos", "growth": "🟢 ARR de $165M (fin 2025) a $180M (jun 2026); adquisición de Nexera Robotics (may-2026) y lanzamiento de Array.", "margin": null, "mkt": "", "preipo": true},
  {"id": "vicarious-surgical", "label": "Vicarious Surgical", "ticker": "RBOT · OTCQB (ex-NYSE, deslistada mar-2026)", "cat": "robotics_physical", "port": "", "role": "Desarrolla un robot quirúrgico de un solo puerto con visión 3D estereoscópica y brazos articulados tipo humano, aún en fase preclínica.", "supplies": "Sin producto comercializado; en desarrollo para cirugía de hernia ventral, con meta de \"design freeze\" a fines de 2026 y presentación FDA De Novo reprogramada para 2026.", "moat": "Diseño único de brazos miniaturizados tipo humano con control por VR y designación FDA Breakthrough Device (2019); riesgo: liquidez crítica (~$3.68M en caja líquida, marzo 2026), deslistada de NYSE por bajo market cap, sin ingresos y compitiendo contra Intuitive Surgical, líder consolidado y rentable.", "country": "Estados Unidos", "growth": "🔴 Crisis de liquidez severa, deslistada de NYSE en marzo 2026, alto riesgo de dilución masiva.", "margin": null, "mkt": "RBOT"},
  {"id": "ambi-robotics", "label": "Ambi Robotics", "ticker": "Privada", "cat": "robotics_physical", "port": "", "role": "Fabrica robots con IA para picking, clasificación (AmbiSort) y apilamiento (AmbiStack) en centros logísticos, con plataforma agnóstica de hardware AmbiOS.", "supplies": "Sistemas de clasificación y apilamiento a Pitney Bowes (4 sistemas, +3M paquetes clasificados) y UPS (+400% productividad reportada).", "moat": "Modelo fundacional propio (PRIME-1) entrenado con 250,000+ horas y 150M+ paquetes, tecnología Sim2Real de origen UC Berkeley; riesgo: sin ronda de financiamiento nueva desde octubre 2022 pese a fuerte demanda comercial (AmbiStack \"agotado\" para todo 2025).", "country": "Estados Unidos", "growth": "🟡 Fuerte tracción comercial (premio RBR50 2026) pero sin ronda de capital nueva desde 2022.", "margin": null, "mkt": "", "preipo": true},
  {"id": "diligent-robotics", "label": "Diligent Robotics", "ticker": "Privada (subsidiaria de Serve Robotics, Nasdaq: SERV, desde ene-2026)", "cat": "robotics_physical", "port": "", "role": "Fabrica el robot móvil manipulador Moxi para transporte autónomo de suministros, muestras de laboratorio y medicamentos en hospitales.", "supplies": "Robots Moxi desplegados en Northwestern Medicine, ChristianaCare y Rochester General Hospital (100+ robots en 25+ hospitales, 1.25M+ entregas acumuladas).", "moat": "Mayor flota de robots móviles manipuladores de IA en hospitales de EEUU; riesgo: no logró escalar como empresa independiente y fue adquirida por Serve Robotics en enero 2026 por ~$25.7-29M en acciones, muy por debajo de su capital levantado.", "country": "Estados Unidos", "growth": "🟡 Adquisición por Serve Robotics (ene-2026) marca el fin de su vida independiente, aunque la tecnología Moxi continúa desplegándose.", "margin": null, "mkt": "", "preipo": true},
  {"id": "chef-robotics", "label": "Chef Robotics", "ticker": "Privada", "cat": "robotics_physical", "port": "", "role": "Fabrica brazos robóticos con IA (software propietario ChefOS) para ensamblaje de comidas en plantas de producción de alimentos.", "supplies": "Sistemas robóticos de ensamblaje de comidas bajo modelo Robotics-as-a-Service a Amy's Kitchen, Sunbasket, Cafe Spice y Project Open Hand.", "moat": "Datos de producción real a gran escala (+70M porciones producidas) que retroalimentan mejoras de IA; riesgo: modelo intensivo en capital/deuda de equipos, dependiente de un sector de food-service de alta rotación y márgenes ajustados.", "country": "Estados Unidos", "growth": "🟢 Serie A de $43.1M (abr-2025) y lanzamiento de Chef+ (dic-2025) con doble capacidad.", "margin": null, "mkt": "", "preipo": true},
  {"id": "realtime-robotics", "label": "Realtime Robotics", "ticker": "Privada", "cat": "robotics_physical", "port": "", "role": "Desarrolla software de planificación de movimiento en tiempo real (RapidPlan, Resolver) para evitar colisiones entre múltiples robots industriales.", "supplies": "Software de motion planning a BMW, Mercedes-Benz, Daimler Truck, Volkswagen Commercial Vehicles, KUKA y Schaeffler Group.", "moat": "Planificación de trayectorias en microsegundos con respaldo de fabricantes industriales líderes (Mitsubishi Electric, Siemens Next47, Toyota AI Ventures); riesgo: ARR estimado bajo (~$5.7M en 2025) frente a $67-107M levantados, sugiere quema de caja elevada.", "country": "Estados Unidos", "growth": "🟡 Financiamiento sostenido por corporativos industriales pero ARR aparentemente desproporcionado frente al capital levantado.", "margin": null, "mkt": "", "preipo": true},
  {"id": "formic", "label": "Formic", "ticker": "Privada", "cat": "robotics_physical", "port": "", "role": "Ofrece robots industriales bajo modelo Robotics-as-a-Service (cero CapEx) para manufactura mid-market: paletizado, empaque y machine tending.", "supplies": "Robots gestionados por precio fijo mensual a Bacardi, Cameron's Coffee, Fastenal, Trident Seafoods y Land O'Frost (25+ clientes, 60+ instalaciones).", "moat": "Software propietario (Cortex/Core) con datos de millones de ciclos y 97% de tasa de renovación de clientes; riesgo: modelo intensivo en capital (deben poseer/financiar los robots), sensible a tasas de interés.", "country": "Estados Unidos", "growth": "🟢 Nueva sede de 53,000 sq ft (jun-2026) y más de 650,000 horas de producción acumuladas.", "margin": null, "mkt": "", "preipo": true},
  {"id": "zipline", "label": "Zipline", "ticker": "Pre-IPO ~$7.6B", "cat": "robotics_physical", "port": "", "role": "Opera una red de entrega logística autónoma mediante drones de ala fija (Platform 1, salud) y drones VTOL (Platform 2, retail/comida).", "supplies": "Entregas autónomas de sangre y medicinas a más de 5,000 hospitales/centros de salud (incluido el sistema nacional de salud de Ruanda) y entregas de retail/comida a Walmart y más de una docena de marcas de restaurantes en EEUU.", "moat": "Pionera con red logística probada en salud africana durante una década y diversificación a retail comercial en EEUU; riesgo: regulación FAA sobre vuelos BVLOS y competencia directa de Wing (Alphabet) y Amazon Prime Air.", "country": "Estados Unidos", "growth": "🟢 Valuación disparada a $7.6B (ene-2026, +$200M adicionales mar-2026); superó 2 millones de entregas comerciales acumuladas.", "margin": null, "mkt": "", "preipo": true},
  {"id": "wing-alphabet", "label": "Wing (Alphabet)", "ticker": "No cotiza (subsidiaria de Alphabet, GOOGL · Nasdaq)", "cat": "robotics_physical", "port": "", "role": "Opera un servicio de entrega de paquetes pequeños mediante drones VTOL, subsidiaria 100% de Alphabet desde 2018.", "supplies": "Entregas de última milla a clientes de Walmart (expansión a 270+ ubicaciones para 2027) y Papa John's, cubriendo múltiples ciudades de EEUU (Dallas-Fort Worth, Atlanta, y expansión a Los Ángeles, Houston, Miami, entre otras).", "moat": "Respaldo financiero y regulatorio ilimitado de Alphabet y tecnología VTOL madura desde 2012; riesgo: depende de las prioridades estratégicas de \"Other Bets\" de Alphabet, con historial de proyectos cerrados si no alcanzan rentabilidad.", "country": "Estados Unidos", "growth": "🟢 Entregas crecieron 3x entre jul-dic 2025 vs ene-jun 2025; expansión agresiva con Walmart.", "margin": null, "mkt": ""},
  {"id": "skydio", "label": "Skydio", "ticker": "Pre-IPO ~$4.4B", "cat": "robotics_physical", "port": "", "role": "Fabrica drones autónomos para defensa, seguridad pública y empresas (utilities, inspección), tras discontinuar su línea de consumo en 2023.", "supplies": "Sistemas de vigilancia autónoma \"dock-based\" a más de 1,200 agencias de seguridad pública, todas las ramas militares de EEUU y 450+ compañías de servicios públicos; contrato AFCENT de $9M (abr-2026).", "moat": "Único fabricante de drones 100% de origen EEUU a gran escala, certificado NDAA-compliant y Blue UAS-listed, beneficiario directo del vacío dejado por el ban de DJI; riesgo: pese al ban, EEUU depende de China para el 90% de imanes de tierras raras y 99% de baterías de drones, generando riesgo de cadena de suministro incluso para fabricantes \"domésticos\".", "country": "Estados Unidos", "growth": "🟢 Serie F de $110M (abr-2026) a valuación $4.4B; inversión de $3.5B en 5 años (\"SkyForge\") para manufactura doméstica.", "margin": null, "mkt": "", "preipo": true},
  {"id": "waabi", "label": "Waabi", "ticker": "Pre-IPO ~$3B", "cat": "robotics_physical", "port": "", "role": "Desarrolla camiones de carga totalmente autónomos (Nivel 4) mediante un enfoque \"AI-first\" basado en simulación (Waabi World) en vez de flotas masivas de prueba en carretera.", "supplies": "Tecnología de conducción autónoma para camiones \"purpose-built\" desarrollados con Volvo Trucks/Volvo Autonomous Solutions; despliegue de robotaxis y camiones autónomos vía la plataforma de Uber (25,000+ robotaxis planeados, más Uber Freight).", "moat": "Enfoque de simulación generativa (Waabi World) que reduce dependencia de millones de millas de prueba física, respaldado por Nvidia y un OEM de camiones (Volvo) para hardware purpose-built; riesgo: modelo aún no probado a escala comercial completa, alta dependencia de ejecución de partnerships sin cronograma público confirmado.", "country": "Canadá", "growth": "🟢 Serie C de $750M + compromiso de $250M de Uber (ene-2026), sumando ~$1B en la ronda; expansión a robotaxis.", "margin": null, "mkt": "", "preipo": true},
  {"id": "ubtech-robotics", "label": "UBTech Robotics", "ticker": "9880 · HKEX", "cat": "robotics_physical", "port": "", "role": "Fabricante chino de robots humanoides industriales (línea Walker S) y de consumo/compañía (línea UWORLD U1), primer fabricante de robótica listado en la Bolsa de Hong Kong.", "supplies": "Robots humanoides industriales para manufactura y robots de consumo orientados a personas mayores y hogares en China; meta de producción de 10,000+ unidades U1 en 2026 y capacidad de 50,000 en 2027.", "moat": "Pionero listado en bolsa con acceso a capital público chino y escala de manufactura consolidada (+101% en su acción durante 2025); riesgo: alta exposición a controles de exportación de tierras raras chinos y a restricciones de acceso a mercados occidentales por la guerra comercial EEUU-China en IA/robótica.", "country": "China", "growth": "🟢 Ingresos creciendo fuerte, humanoides proyectados a representar >80% de ingresos totales en 2026; 13,361+ pedidos del U1 en su día de lanzamiento.", "margin": null, "mkt": "9880"},
  {"id": "agibot-zhiyuan", "label": "AgiBot (Zhiyuan Robotics)", "ticker": "Pre-IPO ~$6.4B", "cat": "robotics_physical", "port": "", "role": "Desarrolla humanoides bípedos y con ruedas, cuadrúpedos y brazos robóticos para manufactura, servicios y hogar, con venta masiva vía ecommerce propio y JD.com.", "supplies": "Robots humanoides y con ruedas a clientes industriales (ej. Fulin Precision, ~100 unidades A2-W) y colaboraciones de marca (PepsiCo \"Fizzbot\"); casi 1,000 humanoides fabricados a inicios de 2025.", "moat": "Velocidad de ejecución e iteración de producto respaldada por gigantes tecnológicos chinos (Baidu, JD.com, BYD) y estrategia de distribución masiva de bajo costo (productos desde ~$2,000 hasta ~$60,000); riesgo: fuerte dependencia del liderazgo de su fundador, competencia intensa de Unitree, UBTech, Tesla y Figure AI, y mismo riesgo geopolítico de tierras raras/controles de exportación que otras humanoides chinas.", "country": "China", "growth": "🟢 Ocho rondas de financiamiento en dos años, valuación >$1B (unicornio) en tiempo récord; fuertes rumores de IPO sin confirmar.", "margin": null, "mkt": "", "preipo": true},
  {"id": "neura-robotics", "label": "Neura Robotics", "ticker": "Pre-IPO ~$7B", "cat": "robotics_physical", "port": "", "role": "Desarrolla \"robots cognitivos\" (humanoide 4NE-1) diseñados para percibir, razonar y actuar en entornos humanos no estructurados, más allá de tareas fabriles repetitivas.", "supplies": "Plataforma de robots cognitivos a Kawasaki (desarrollo de cobots), Bosch (escalado de humanoides en producción industrial, ene-2026) y Schaeffler (partnership tecnológico); meta de escalar a fabricación de millones de unidades para 2030.", "moat": "Único jugador europeo de escala relevante en humanoides con partnerships industriales profundos (Bosch, Schaeffler, Kawasaki) y respaldo de semiconductoras (Nvidia, Qualcomm) fuera de los ecosistemas chino y estadounidense puro; riesgo: valuación de $7B cuestionada por analistas dado su ARR relativamente bajo, y ejecución de manufactura a escala de millones de unidades aún no probada.", "country": "Alemania", "growth": "🟢 Serie C de hasta $1.4B (jun-2026) liderada por Tether, la mayor ronda jamás registrada en robótica full-stack; valuación saltó de ~€4B a $7B en meses.", "margin": null, "mkt": "", "preipo": true},
  {"id": "vast-space", "label": "Vast Space", "ticker": "Privada", "cat": "space_infra", "port": "", "role": "Desarrolla estaciones espaciales comerciales privadas, empezando por el módulo habitable Haven-1, como sucesoras de la ISS.", "supplies": "Provee acceso a hábitat orbital y experimentos en microgravedad a agencias espaciales, investigadores y turistas; depende de SpaceX para lanzamiento y transporte de tripulación (Falcon 9/Dragon).", "moat": "Financiamiento personal ilimitado del fundador (Jed McCaleb) le da independencia de rondas de capital, pero enfrenta riesgo de ejecución técnica y calendario ajustado frente a la desorbitación de la ISS (~2030).", "country": "Estados Unidos", "growth": "🟢 Lanzamiento de Haven-1 previsto 2026, contratos crecientes con NASA", "margin": null, "mkt": "", "preipo": true},
  {"id": "ispace", "label": "ispace", "ticker": "9348 · Tokyo Stock Exchange", "cat": "space_infra", "port": "", "role": "Diseña y opera módulos de alunizaje comerciales para transportar cargas científicas y comerciales a la superficie lunar.", "supplies": "Provee servicios de transporte lunar tipo CLPS a agencias y empresas; su filial ispace-U.S. desarrolla el lander APEX 1.0 con Draper para NASA.", "moat": "Pionero japonés cotizado en alunizaje comercial con marca reconocida, pero dos intentos de alunizaje (2023 y 2025) terminaron en pérdida de la nave, dañando credibilidad técnica.", "country": "Japón", "growth": "🟡 Misión 3 (APEX 1.0) en desarrollo tras dos fallos consecutivos", "margin": null, "mkt": "9348"},
  {"id": "astroscale", "label": "Astroscale", "ticker": "5034 · Tokyo Stock Exchange", "cat": "space_infra", "port": "", "role": "Ofrece servicios de sostenibilidad orbital: remoción de basura espacial, extensión de vida útil de satélites e inspección en órbita.", "supplies": "Provee misiones de rendezvous y captura de desechos a operadores de satélites y agencias (JAXA, ESA, UK Space Agency).", "moat": "Primer movimiento regulatorio y técnico en \"debris removal as a service\" con contratos multi-país, pero tecnología de captura aún de bajo TRL comercial y ciclos de venta gubernamentales largos.", "country": "Japón", "growth": "🟢 Contratos crecientes con JAXA, ESA, UK Space Agency y programas de defensa", "margin": null, "mkt": "5034"},
  {"id": "d-orbit", "label": "D-Orbit", "ticker": "Privada", "cat": "space_infra", "port": "", "role": "Provee vehículos de transporte y \"última milla\" orbital (ION Satellite Carrier) que despliegan y posicionan satélites tras el lanzamiento.", "supplies": "Provee transporte orbital compartido a operadores de constelaciones pequeñas, integrándose como payload en misiones rideshare de SpaceX.", "moat": "Track record con más de 20 misiones ION exitosas y presencia logística europea, pero compite con actores de EE.UU. mejor capitalizados por el mismo nicho.", "country": "Italia", "growth": "🟢 Expansión a manufactura en microgravedad y contratos de defensa europeos", "margin": null, "mkt": "", "preipo": true},
  {"id": "momentus", "label": "Momentus", "ticker": "MNTS · Nasdaq", "cat": "space_infra", "port": "", "role": "Fabrica vehículos de transferencia orbital (Vigoride) que transportan y posicionan satélites de clientes tras el lanzamiento compartido.", "supplies": "Provee servicios de \"última milla\" orbital y hosting de payloads a operadores de smallsats en misiones rideshare.", "moat": "Uno de los pocos operadores de vehículos de transferencia orbital cotizados en bolsa, pero atraviesa crisis financiera severa tras fallos técnicos en primeras misiones Vigoride.", "country": "Estados Unidos", "growth": "🔴 Ingresos mínimos, reestructuración financiera y riesgo de continuidad", "margin": null, "mkt": "MNTS"},
  {"id": "loft-orbital", "label": "Loft Orbital", "ticker": "Privada", "cat": "space_infra", "port": "", "role": "Opera \"infraestructura espacial como servicio\": satélites multi-payload (línea YAM) que alquila a clientes gubernamentales y comerciales.", "supplies": "Provee capacidad de carga útil en órbita (potencia, datos, apuntamiento) a agencias y empresas que necesitan volar sensores sin operar su propia plataforma satelital.", "moat": "Modelo \"rideshare para payloads\" reduce el tiempo de acceso al espacio de años a meses, con contratos recurrentes de Space Force y NRO; depende de terceros para manufactura de buses y lanzamiento.", "country": "Estados Unidos", "growth": "🟢 Contratos crecientes con Space Force, NRO y clientes comerciales", "margin": null, "mkt": "", "preipo": true},
  {"id": "terran-orbital", "label": "Terran Orbital", "ticker": "Privada (subsidiaria de Lockheed Martin, adquirida en 2024)", "cat": "satellite", "port": "", "role": "Fabrica buses y plataformas satelitales completas (pequeños a medianos) para clientes de defensa, gobierno y comerciales.", "supplies": "Provee buses satelitales integrados y fabricación en gran volumen a programas de defensa (incluida la capa de rastreo de la Space Development Agency) y clientes comerciales.", "moat": "Escala de manufactura vertical (Irvine, CA) única en el segmento de buses medianos, ahora respaldada por el balance de Lockheed Martin tras su adquisición (2024); riesgo de pérdida de neutralidad frente a otros integradores tras quedar bajo un solo contratista primario.", "country": "Estados Unidos", "growth": "🟡 Estabilizada tras la adquisición por Lockheed Martin luego de años de pérdidas como empresa pública", "margin": null, "mkt": "", "preipo": true},
  {"id": "abl-space-systems", "label": "ABL Space Systems", "ticker": "Privada", "cat": "space_infra", "port": "", "role": "Originalmente desarrollador del cohete orbital RS1; tras retirar el programa en 2024, pivotó a propulsión e interceptores para defensa antimisiles y sistemas hipersónicos.", "supplies": "Provee tecnología de propulsión e interceptores de misiles a la Fuerza Espacial y la Agencia de Defensa Antimisiles de EE.UU. (incluido el programa Golden Dome).", "moat": "Herencia de ingeniería de propulsión de bajo costo aplicada ahora a interceptores, con contratos de defensa nacional emergentes; riesgo de ejecución tras el fracaso comercial de su programa de lanzamiento original.", "country": "Estados Unidos", "growth": "🟡 Reestructuración exitosa hacia defensa tras cancelar RS1, contratos crecientes de interceptores", "margin": null, "mkt": "", "preipo": true},
  {"id": "sierra-nevada-corporation", "label": "Sierra Nevada Corporation", "ticker": "Privada", "cat": "space_infra", "port": "", "role": "Conglomerado aeroespacial y de defensa privado (propiedad familiar Ozawa) que provee aviones ISR, guerra electrónica y tecnología espacial de seguridad nacional; escindió su negocio comercial de estaciones espaciales/Dream Chaser en Sierra Space (2021).", "supplies": "Provee aeronaves de vigilancia/inteligencia, integración C4ISR y cargas útiles espaciales clasificadas al Pentágono, la Fuerza Espacial y agencias de inteligencia de EE.UU.", "moat": "Décadas de relaciones contractuales clasificadas con el gobierno de EE.UU. y diversificación entre aviación, espacio y cibernética; riesgo de concentración en contratos de defensa sujetos a ciclos presupuestarios.", "country": "Estados Unidos", "growth": "🟢 Crecimiento sostenido en contratos clasificados de defensa y espacio nacional", "margin": null, "mkt": "", "preipo": true},
  {"id": "voyager-technologies", "label": "Voyager Technologies", "ticker": "VOYG · NYSE", "cat": "space_infra", "port": "", "role": "Holding espacial diversificado que desarrolla la estación espacial comercial Starlab (sucesora de la ISS) y opera negocios de defensa y exploración espacial (Nanoracks).", "supplies": "Provee capacidad de investigación en microgravedad y hardware de misión (vía Nanoracks) a NASA y clientes comerciales; construye Starlab junto a Airbus.", "moat": "Cartera diversificada (espacio comercial + defensa + biotech orbital) reduce dependencia de un solo contrato, respaldada por su IPO en NYSE (junio 2025); enfrenta fuerte competencia de Axiom Space y Vast por los contratos CLD de NASA.", "country": "Estados Unidos", "growth": "🟢 IPO exitosa 2025, contrato NASA Commercial LEO Destinations para Starlab", "margin": null, "mkt": "VOYG"},
  {"id": "sidus-space", "label": "Sidus Space", "ticker": "SIDU · Nasdaq", "cat": "satellite", "port": "", "role": "Micro-cap que fabrica piezas aeroespaciales impresas en 3D y opera la constelación de satélites de datos LizzieSat.", "supplies": "Provee componentes manufacturados (impresión 3D, mecanizado) a SpaceX, Blue Origin y NASA, y datos de observación terrestre vía LizzieSat.", "moat": "Modelo dual (manufactura + datos satelitales) le da ingresos recurrentes tempranos, pero es una micro-cap con capitalización muy reducida y alta dilución para financiar la constelación.", "country": "Estados Unidos", "growth": "🟡 Ingresos de manufactura estables, constelación LizzieSat aún en fase temprana", "margin": null, "mkt": "SIDU"},
  {"id": "nanoavionics", "label": "NanoAvionics", "ticker": "Privada (subsidiaria de Kongsberg)", "cat": "satellite", "port": "", "role": "Diseña y fabrica plataformas y buses de nanosatélites/smallsats modulares para clientes comerciales, gubernamentales y de defensa.", "supplies": "Provee buses satelitales estandarizados (línea MP) y servicios de integración de misión a operadores de constelaciones y agencias gubernamentales europeas.", "moat": "Buses modulares de bajo costo con producción en Lituania y EE.UU., ahora respaldados por el balance y canal de defensa de Kongsberg tras su adquisición mayoritaria; riesgo de comoditización del segmento de buses pequeños.", "country": "Lituania", "growth": "🟢 Integración con la división de defensa espacial de Kongsberg impulsa contratos militares europeos", "margin": null, "mkt": "", "preipo": true},
  {"id": "exolaunch", "label": "Exolaunch", "ticker": "Privada (subsidiaria de Isar Aerospace)", "cat": "space_launch", "port": "", "role": "Ofrece servicios de integración de lanzamiento y despliegue (\"rideshare\") para satélites pequeños: separadores, dispensadores y gestión de misión.", "supplies": "Provee integración y despliegue en órbita de smallsats a decenas de operadores por misión, principalmente en las misiones Transporter de SpaceX.", "moat": "Mayor integrador de rideshare del mundo por número de satélites desplegados, con relación estrecha con SpaceX; ahora integrado en Isar Aerospace, lo que podría generar conflicto de interés con otros proveedores de lanzamiento.", "country": "Alemania", "growth": "🟢 Cientos de satélites desplegados anualmente, integrado en la cadena de lanzamiento propia de Isar Aerospace", "margin": null, "mkt": "", "preipo": true},
  {"id": "karman-space-defense", "label": "Karman Space & Defense", "ticker": "KRMN · NYSE", "cat": "space_infra", "port": "", "role": "Fabrica estructuras, motores de cohete sólido, energéticos y componentes críticos para sistemas hipersónicos, defensa antimisiles y vehículos de lanzamiento.", "supplies": "Provee cofres de motor, aeroestructuras y componentes energéticos a contratistas primarios de defensa e industria de lanzamiento (RTX, Northrop Grumman, agencias de defensa de EE.UU.).", "moat": "Posición dominante como proveedor \"pick and shovel\" en la cadena de suministro de hipersónicos e interceptores de misiles, con barreras de certificación altas; alta concentración de ingresos en contratos gubernamentales.", "country": "Estados Unidos", "growth": "🟢 Fuerte demanda por programas hipersónicos y defensa antimisiles (Golden Dome)", "margin": null, "mkt": "KRMN"},
  {"id": "true-anomaly", "label": "True Anomaly", "ticker": "Privada", "cat": "space_infra", "port": "", "role": "Desarrolla vehículos autónomos de vigilancia y seguridad orbital (Jackal) y software de dominio espacial para detectar y responder a amenazas satelitales.", "supplies": "Provee vehículos de inspección/interceptación orbital y software de mando y control (Mosaic) a la Fuerza Espacial de EE.UU. y aliados.", "moat": "Pionero en \"space security\" con contratos tempranos de la Fuerza Espacial y valoración creciente (>$1000M), pero opera en un nicho de defensa nuevo con reglas de enfrentamiento aún poco definidas.", "country": "Estados Unidos", "growth": "🟢 Contratos crecientes de Space Force y ronda Serie C a valoración >$1000M (2024-2025)", "margin": null, "mkt": "", "preipo": true},
  {"id": "impulse-space", "label": "Impulse Space", "ticker": "Privada", "cat": "space_infra", "port": "", "role": "Fabrica vehículos de transferencia orbital (Mira) y etapas de empuje de alta energía (Helios) para mover satélites entre órbitas tras el lanzamiento.", "supplies": "Provee servicios de \"última milla\" y transferencia a órbitas altas (GEO, cislunares) a operadores de satélites comerciales y gubernamentales que lanzan en cohetes de terceros.", "moat": "Fundada por Tom Mueller (ex vicepresidente de propulsión de SpaceX), con ventaja técnica en propulsión; compite en un mercado aún pequeño con Momentus y D-Orbit por los mismos clientes.", "country": "Estados Unidos", "growth": "🟢 Ronda Serie C 2025 a valoración multibillonaria, contrato de la Fuerza Espacial para Helios", "margin": null, "mkt": "", "preipo": true},
  {"id": "varda-space-industries", "label": "Varda Space Industries", "ticker": "Privada", "cat": "space_infra", "port": "", "role": "Fabrica productos farmacéuticos y materiales avanzados en microgravedad usando cápsulas orbitales reutilizables que regresan a la Tierra.", "supplies": "Provee capacidad de manufactura orbital (cristalización de fármacos, materiales) a empresas farmacéuticas y de materiales, con cápsulas W-series que reingresan y aterrizan en EE.UU.", "moat": "Primer actor en demostrar manufactura farmacéutica en microgravedad con reingreso exitoso repetido (W-1, W-2, W-3); el mercado de manufactura orbital comercial aún es incipiente y depende de aprobación regulatoria FAA/farmacéutica.", "country": "Estados Unidos", "growth": "🟢 Múltiples misiones W-series exitosas, ronda Serie C 2025 a valoración ~$1800M", "margin": null, "mkt": "", "preipo": true},
  {"id": "orbit-fab", "label": "Orbit Fab", "ticker": "Privada", "cat": "space_infra", "port": "", "role": "Desarrolla infraestructura de reabastecimiento de combustible en órbita (\"gasolineras espaciales\"), incluyendo puertos de acoplamiento estándar RAFTI y depósitos de propelente.", "supplies": "Provee puertos de reabastecimiento y transferencia de propelente en órbita a operadores de satélites gubernamentales y comerciales que buscan extender la vida útil de sus activos.", "moat": "Estándar de puerto de reabastecimiento (RAFTI) adoptado por la Fuerza Espacial y varios fabricantes, con efecto de red a su favor; el mercado de reabastecimiento en órbita aún no tiene demanda comercial masiva.", "country": "Estados Unidos", "growth": "🟡 Contratos piloto con Space Force (Tetra-5) y adopción creciente del estándar RAFTI", "margin": null, "mkt": "", "preipo": true},
  {"id": "starfish-space", "label": "Starfish Space", "ticker": "Privada", "cat": "space_infra", "port": "", "role": "Desarrolla vehículos autónomos de servicio orbital (Otter) para extender la vida útil, reubicar y desorbitar satélites al final de su misión.", "supplies": "Provee servicios de acoplamiento autónomo y remolque orbital a operadores de constelaciones y agencias que necesitan extender vida útil o desorbitar satélites responsablemente.", "moat": "Software propietario de acoplamiento autónomo de bajo costo (validado en la misión Otter Pup, 2023) le da ventaja en el nicho de \"servicing\" para smallsats, frente a rivales más grandes como Astroscale enfocados en misiones gubernamentales.", "country": "Estados Unidos", "growth": "🟡 Escalando tras validación técnica, primeros contratos comerciales de extensión de vida", "margin": null, "mkt": "", "preipo": true},
  {"id": "space-forge", "label": "Space Forge", "ticker": "Privada", "cat": "space_infra", "port": "", "role": "Fabrica semiconductores y aleaciones avanzadas en microgravedad usando satélites reutilizables (ForgeStar) que regresan a la Tierra para reciclar la plataforma.", "supplies": "Provee capacidad de manufactura orbital de semiconductores compuestos y materiales avanzados a fabricantes de chips y materiales que buscan propiedades imposibles de lograr en gravedad terrestre.", "moat": "Primer actor europeo enfocado en semiconductores fabricados en el espacio, con respaldo del gobierno del Reino Unido; tecnología de reingreso y reutilización de plataforma aún no demostrada a escala comercial repetible.", "country": "Reino Unido", "growth": "🟡 Primeras misiones ForgeStar en curso, fuerte respaldo gubernamental británico", "margin": null, "mkt": "", "preipo": true},
  {"id": "helsing", "label": "Helsing", "ticker": "Pre-IPO ~€12B", "cat": "ai_defense", "port": "", "role": "Startup alemana que desarrolla software de IA para sistemas de defensa (fusión de sensores, autonomía, guerra electrónica) integrado en plataformas existentes.", "supplies": "Software de IA de misión (HX-2 municiones merodeadoras, Centaur - copiloto de IA para Eurofighter, Altra - guerra electrónica, drones submarinos con Saab); provee a los ejércitos de Alemania, Ucrania, Reino Unido y Francia.", "moat": "Pionera del \"AI-native defense stack\" con acceso privilegiado a gobiernos europeos post-invasión de Ucrania; riesgo: depende de contratos gubernamentales concentrados y de la competencia creciente de Anduril y primes tradicionales entrando en IA.", "country": "Alemania", "growth": "🟢 Ronda Serie D 2025 (~€600M) valoró la empresa en ~€12B, cuadruplicando su valuación en 12 meses", "margin": null, "mkt": "", "preipo": true},
  {"id": "elbit-systems", "label": "Elbit Systems", "ticker": "ESLT · NASDAQ/TASE", "cat": "defense_prime", "port": "", "role": "Conglomerado israelí de electrónica de defensa que diseña y fabrica sistemas aeroespaciales, terrestres, navales y C4ISR.", "supplies": "Sistemas ISTAR, municiones guiadas de precisión, guerra electrónica, drones (familia Hermes), aviónica, sistemas C4I; provee a las FDI israelíes, OTAN y más de 100 países.", "moat": "Integración vertical y cartera diversificada con backlog récord >$20-23B; riesgo: dependencia del gasto militar israelí y exposición a restricciones de exportación en algunos mercados europeos.", "country": "Israel", "growth": "🟢 Backlog récord y crecimiento de doble dígito impulsado por demanda global post-2023", "margin": 0.09, "mkt": "ESLT"},
  {"id": "iai-israel-aerospace", "label": "Israel Aerospace Industries", "ticker": "No cotiza (empresa estatal)", "cat": "defense_prime", "port": "", "role": "Empresa aeroespacial y de defensa propiedad del Estado israelí, líder en satélites, misiles, drones y radares avanzados.", "supplies": "Defensa antimisiles (Arrow), satélites de observación y comunicación, drones (familia Heron), radares vía su subsidiaria ELTA Systems; cliente principal el Ministerio de Defensa de Israel, con exportaciones a India, EE.UU. y Europa.", "moat": "Cuasi-monopolio estatal en programas estratégicos israelíes (satélites, defensa antimisiles); riesgo: la gobernanza estatal limita agilidad frente a competidores privados.", "country": "Israel", "growth": "🟢 Backlog en máximos históricos (~$20B+) por defensa antimisiles y exportaciones", "margin": null, "mkt": ""},
  {"id": "rafael-advanced-defense", "label": "Rafael Advanced Defense Systems", "ticker": "No cotiza (empresa estatal)", "cat": "defense_prime", "port": "", "role": "Empresa estatal israelí especializada en defensa antimisiles, misiles guiados de precisión y protección activa para blindados.", "supplies": "Iron Dome (coproducido con RTX en EE.UU.), David's Sling, misiles Spike, sistema de protección activa Trophy (usado en tanques Abrams de EE.UU.); cliente principal FDI, con exportaciones a EE.UU. y Alemania.", "moat": "Único proveedor de Iron Dome/David's Sling para Israel con demanda disparada tras octubre de 2023; riesgo: capacidad de producción limitada frente a la demanda global.", "country": "Israel", "growth": "🟢 Ingresos y backlog en máximos históricos por demanda de Iron Dome/Trophy", "margin": null, "mkt": ""},
  {"id": "general-dynamics", "label": "General Dynamics", "ticker": "GD · NYSE", "cat": "defense_prime", "port": "", "role": "Conglomerado de defensa diversificado que fabrica submarinos nucleares, tanques de combate, jets de negocios y servicios de TI/IA de misión al gobierno de EE.UU.", "supplies": "Submarinos clase Columbia y Virginia (Electric Boat) a la Marina, tanques Abrams y Stryker al Ejército, jets Gulfstream, y servicios de TI/ciberseguridad/IA (GDIT) al DoD e IC.", "moat": "Único astillero (junto con HII) capaz de producir submarinos nucleares, con contratos plurianuales; riesgo: retrasos crónicos en producción de submarinos y dependencia del presupuesto federal.", "country": "Estados Unidos", "growth": "🟢 Backlog récord impulsado por submarinos, IT gubernamental y Gulfstream", "margin": 0.11, "mkt": "GD"},
  {"id": "lockheed-martin", "label": "Lockheed Martin", "ticker": "LMT · NYSE", "cat": "defense_prime", "port": "", "role": "Mayor contratista de defensa del mundo por ingresos, líder en aviones de combate, misiles y sistemas espaciales militares.", "supplies": "Cazas F-35 y F-16 a EE.UU. y aliados OTAN, misiles (PAC-3), satélites militares y sistemas de mando/control con IA (AEGIS).", "moat": "Monopolio de facto en cazas furtivos occidentales de 5ª generación (F-35) con ecosistema logístico global; riesgo: sobrecostos históricos y dependencia de un solo programa para gran parte del backlog.", "country": "Estados Unidos", "growth": "🟢 Backlog >$170B, demanda europea/asiática de F-35", "margin": 0.11, "mkt": "LMT"},
  {"id": "textron-systems", "label": "Textron Systems", "ticker": "Privada (división de Textron Inc, TXT · NYSE)", "cat": "defense_prime", "port": "", "role": "División de defensa de Textron especializada en sistemas no tripulados aéreos y terrestres, municiones y simulación militar.", "supplies": "Drones tácticos (Shadow, Aerosonde), vehículos terrestres no tripulados (Ripsaw), municiones guiadas y sistemas de entrenamiento para el Ejército de EE.UU. y aliados.", "moat": "Posición consolidada como proveedor histórico de UAS tácticos del Ejército (programa Shadow); riesgo: competencia creciente de startups de autonomía con ciclos de desarrollo más rápidos.", "country": "Estados Unidos", "growth": "🟡 Crecimiento moderado, presionado por nuevos entrantes en drones de bajo costo", "margin": null, "mkt": "", "preipo": true},
  {"id": "hanwha-aerospace", "label": "Hanwha Aerospace", "ticker": "012450 · KRX", "cat": "defense_prime", "port": "", "role": "Principal fabricante surcoreano de defensa terrestre y motores aeroespaciales, con expansión agresiva en exportación de artillería y naval.", "supplies": "Obuses K9 Thunder y lanzacohetes Chunmoo a Polonia, Australia y Medio Oriente; motores de aviación bajo licencia (GE); vehículos blindados Redback y construcción naval vía Hanwha Ocean.", "moat": "Bajo costo de producción y velocidad de entrega frente a rivales occidentales; riesgo: dependencia de licencias tecnológicas extranjeras (motores GE) y tensiones con Corea del Norte.", "country": "Corea del Sur", "growth": "🟢 Explosión de exportaciones (Polonia, Medio Oriente) la posicionan como potencia emergente de defensa", "margin": 0.12, "mkt": "012450"},
  {"id": "babcock-international", "label": "Babcock International", "ticker": "BAB · LSE", "cat": "defense_prime", "port": "", "role": "Proveedor de servicios de ingeniería, mantenimiento y soporte de ciclo de vida para plataformas navales, nucleares y de defensa, incluyendo submarinos nucleares.", "supplies": "Mantenimiento y soporte de submarinos nucleares (clase Vanguard/Astute) y portaaviones para el MoD británico; gestión de instalaciones nucleares navales (Devonport, Rosyth, Faslane).", "moat": "Contratos de décadas ligados a infraestructura crítica nacional insustituible; riesgo: alta dependencia del gasto UK y sobrecostos históricos.", "country": "Reino Unido", "growth": "🟢 Rearme europeo y renovación de disuasión nuclear (AUKUS, Dreadnought) impulsan la cartera de pedidos", "margin": 0.08, "mkt": "BAB"},
  {"id": "qinetiq", "label": "QinetiQ", "ticker": "QQ. · LSE", "cat": "defense_prime", "port": "", "role": "Empresa de tecnología de defensa y seguridad especializada en ensayo/evaluación, robótica, sistemas no tripulados y ciberdefensa para gobiernos aliados.", "supplies": "Servicios de ensayo y evaluación (T&E) para el MoD británico; sistemas robóticos no tripulados (filial Pratt Miller en EE.UU.) y guerra electrónica para OTAN.", "moat": "Operador exclusivo de infraestructuras de ensayo estratégicas del gobierno UK bajo contratos de largo plazo; riesgo: exposición a ciclos de adquisición gubernamental y competencia en no tripulados.", "country": "Reino Unido", "growth": "🟢 Expansión en EE.UU. (Pratt Miller, robótica militar) y crecimiento en presupuestos de defensa OTAN", "margin": 0.12, "mkt": "QQ."},
  {"id": "xanadu-quantum", "label": "Xanadu", "ticker": "Privada", "cat": "quantum_hw", "port": "", "role": "Desarrolla computadoras cuánticas fotónicas y el framework open-source PennyLane para computación cuántica y machine learning cuántico.", "supplies": "Acceso en la nube a procesadores cuánticos fotónicos (Aurora, Borealis) para I+D; software PennyLane usado ampliamente en investigación cuántica.", "moat": "Qubits fotónicos que operan a temperatura ambiente, nativamente compatibles con fibra óptica; riesgo: tecnología fotónica aún no demuestra corrección de errores a escala frente a superconductores/iones atrapados.", "country": "Canadá", "growth": "🟡 Avances técnicos notables (Aurora) pero camino a ventaja cuántica comercial incierto", "margin": null, "mkt": "", "preipo": true},
  {"id": "iqm-quantum", "label": "IQM Quantum Computers", "ticker": "Privada", "cat": "quantum_hw", "port": "", "role": "Fabricante europeo de computadoras cuánticas superconductoras de pila completa (hardware y control), on-premise y en la nube.", "supplies": "Sistemas cuánticos superconductores completos a centros de supercomputación nacionales en Alemania, Polonia, España y Finlandia; coprocesadores cuánticos integrados en HPC.", "moat": "Único proveedor europeo de hardware cuántico superconductor de pila completa con fábrica de chips propia en Finlandia; riesgo: escalar qubits manteniendo bajas tasas de error frente a IBM/Google.", "country": "Finlandia", "growth": "🟢 Fuerte impulso de financiamiento soberano europeo por autonomía tecnológica cuántica", "margin": null, "mkt": "", "preipo": true},
  {"id": "alice-bob-quantum", "label": "Alice & Bob", "ticker": "Privada", "cat": "quantum_hw", "port": "", "role": "Desarrolla computadoras cuánticas basadas en \"cat qubits\", un enfoque que busca reducir drásticamente la sobrecarga de corrección de errores cuánticos.", "supplies": "Procesadores experimentales de cat qubits y licencias de propiedad intelectual a socios de investigación; prototipos para gobiernos y laboratorios europeos (France 2030).", "moat": "Cat qubits que suprimen nativamente errores de bit-flip, reduciendo qubits físicos necesarios por qubit lógico; riesgo: tecnología en etapa muy temprana, sin validación a escala comercial.", "country": "Francia", "growth": "🟡 Reducción teórica prometedora de overhead de corrección de errores, validación experimental a gran escala pendiente", "margin": null, "mkt": "", "preipo": true},
  {"id": "seeqc-quantum", "label": "SEEQC", "ticker": "Privada", "cat": "quantum_hw", "port": "", "role": "Desarrolla computación cuántica digital superconductora con electrónica de control criogénica integrada (SFQ), resolviendo el cuello de botella de \"wiring\" al escalar qubits.", "supplies": "Chips de control clásico criogénico integrados junto a qubits superconductores para fabricantes/laboratorios de hardware cuántico; sistemas para casos de uso industriales como detección de fraude financiero.", "moat": "Arquitectura híbrida única con electrónica de control dentro del mismo criostato que los qubits, clave para escalar a millones de qubits; riesgo: nicho técnico especializado con adopción de mercado aún limitada.", "country": "Estados Unidos", "growth": "🟡 Tecnología vista como habilitadora crítica para escalado, comercialización todavía incipiente", "margin": null, "mkt": "", "preipo": true},
  {"id": "atom-computing", "label": "Atom Computing", "ticker": "Privada", "cat": "quantum_hw", "port": "", "role": "Diseña y construye computadoras cuánticas basadas en arreglos de átomos neutros atrapados ópticamente (tweezers ópticos), enfocada en escalar qubits lógicos tolerantes a fallos.", "supplies": "Acceso a hardware cuántico de átomos neutros (sistema \"Phenom\", 1000+ qubits físicos) vía cloud y colaboración de I+D a Microsoft Azure Quantum y clientes gubernamentales/científicos de EE.UU.", "moat": "Arquitectura de átomos neutros que escala qubits con alta conectividad sin criogenia extrema; riesgo: competencia de IonQ, QuEra y Pasqal en la misma modalidad.", "country": "Estados Unidos", "growth": "🟢 Anunció junto a Microsoft 24 qubits lógicos con corrección de errores, hito clave del sector", "margin": null, "mkt": "", "preipo": true},
  {"id": "infleqtion", "label": "Infleqtion", "ticker": "Privada", "cat": "quantum_hw", "port": "", "role": "Desarrolla tecnología cuántica basada en átomos fríos para computación, sensores de precisión y relojes atómicos (antes ColdQuanta).", "supplies": "Computadoras cuánticas (plataforma \"Albert\"), relojes atómicos de precisión y sensores cuánticos a DARPA, AFRL, NASA y socios comerciales.", "moat": "Tecnología de átomos fríos con doble aplicación (cómputo y sensado/timing), diversificando ingresos; riesgo: dependencia de contratos gubernamentales/defensa y competencia de QuEra/Pasqal.", "country": "Estados Unidos", "growth": "🟡 Crecimiento constante en contratos gubernamentales, cómputo cuántico comercial aún inmaduro", "margin": null, "mkt": "", "preipo": true},
  {"id": "world-labs", "label": "World Labs", "ticker": "Pre-IPO ~$1B", "cat": "ailab", "port": "", "role": "Laboratorio de IA fundado por Fei-Fei Li enfocado en \"spatial intelligence\": modelos de mundo que permiten a la IA percibir, generar e interactuar con entornos 3D.", "supplies": "Modelos generativos de mundos 3D (producto \"Marble\") a desarrolladores de juegos, simulación, robótica y contenido inmersivo.", "moat": "Liderazgo científico de Fei-Fei Li (pionera de ImageNet) y equipo con expertise único en visión 3D/NeRF; riesgo: competencia de OpenAI, Google DeepMind y Runway en modelos de mundo generativos.", "country": "Estados Unidos", "growth": "🟢 Lanzó su primer producto comercial \"Marble\" (generación de mundos 3D) a fines de 2025", "margin": null, "mkt": "", "preipo": true},
  {"id": "sakana-ai", "label": "Sakana AI", "ticker": "Privada", "cat": "ailab", "port": "", "role": "Laboratorio de IA japonés que desarrolla modelos y algoritmos inspirados en la naturaleza (evolución, inteligencia colectiva) como alternativa a la escala pura de LLMs.", "supplies": "Modelos fundacionales y técnicas de \"model merging\" evolutivo a empresas japonesas y globales; colabora con el gobierno japonés en soberanía de IA.", "moat": "Equipo fundador de clase mundial (David Ha, ex-Google Brain, y Llion Jones, coautor de \"Attention Is All You Need\"); riesgo: competir con gigantes de EE.UU./China con recursos comparativamente limitados.", "country": "Japón", "growth": "🟢 Alcanzó estatus de unicornio en 2024 y continuó levantando capital en 2025", "margin": null, "mkt": "", "preipo": true},
  {"id": "reflection-ai", "label": "Reflection AI", "ticker": "Pre-IPO ~$8B", "cat": "ailab", "port": "", "role": "Laboratorio de IA \"agentic\" que construye modelos fundacionales open-weight para agentes autónomos de programación, fundado por ex-investigadores de DeepMind.", "supplies": "Modelos de lenguaje open-weight orientados a agentes de codificación autónomos, como alternativa abierta a DeepSeek y modelos cerrados de OpenAI/Anthropic.", "moat": "Equipo fundador con experiencia en AlphaGo/Gemini (Misha Laskin e Ioannis Antonoglou); riesgo: alta intensidad de capital para entrenar modelos de frontera compitiendo con labs mejor financiados.", "country": "Estados Unidos", "growth": "🟢 Pasó de ~$555M de valuación (marzo 2025) a una ronda mucho mayor a fines de 2025, con inversión de Nvidia", "margin": null, "mkt": "", "preipo": true},
  {"id": "poolside-ai", "label": "Poolside AI", "ticker": "Pre-IPO ~$3B", "cat": "ailab", "port": "", "role": "Laboratorio de IA enfocado en modelos fundacionales para generación de código, entrenados con aprendizaje por refuerzo sobre datos sintéticos de programación.", "supplies": "Modelos de IA para asistencia y automatización de desarrollo de software a empresas; opera infraestructura de cómputo dedicada para entrenamiento propio.", "moat": "Fundadores de primer nivel (Jason Warner, ex-CTO de GitHub, y Eiso Kant) apostando por datos sintéticos de código propios; riesgo: altísimo costo de cómputo y competencia de GitHub Copilot, Cursor y grandes labs.", "country": "Estados Unidos / Francia", "growth": "🟢 Series B grande en 2024-2025 y clúster de GPUs dedicado en Texas para escalar entrenamiento", "margin": null, "mkt": "", "preipo": true},
  {"id": "naval-group", "label": "Naval Group", "ticker": "Privada (95,5% Estado francés)", "cat": "defense_prime", "port": "", "role": "Constructor naval militar estatal francés; diseña y construye submarinos (convencionales y de propulsión nuclear) y fragatas para la Marine Nationale y clientes de exportación.", "supplies": "Submarinos clase Barracuda y Scorpène, fragatas FDI/FREMM, sistemas de combate naval y mantenimiento (MRO) para Francia, Brasil, India, Indonesia y Países Bajos.", "moat": "Único constructor de submarinos nucleares de Francia (barrera tecnológica altísima); riesgo: dependencia de contratos estatales plurianuales y exposición a cancelaciones geopolíticas (caso AUKUS 2021).", "country": "Francia", "growth": "🟢 Cartera de pedidos en máximos por reposición de flota francesa y exportaciones a India/Indonesia", "margin": null, "mkt": "", "preipo": true},
  {"id": "dassault-aviation", "label": "Dassault Aviation", "ticker": "AM · Euronext Paris", "cat": "defense_prime", "port": "", "role": "Fabricante francés de aviones de combate (caza Rafale) y jets ejecutivos Falcon, con integración vertical en diseño y producción aeroespacial.", "supplies": "Cazas Rafale a la Fuerza Aérea francesa y exportación (India, Egipto, Qatar, Grecia, Croacia, Indonesia, EAU); jets de negocios Falcon; participación en el programa europeo SCAF/FCAS junto a Airbus.", "moat": "Uno de los pocos fabricantes mundiales de cazas de generación 4.5 con control total del diseño; riesgo: dependencia de exportaciones de Rafale (ciclos de venta largos) y tensiones con Airbus por liderazgo en SCAF.", "country": "Francia", "growth": "🟢 Fuerte demanda de exportación de Rafale post-2022 (Indonesia, EAU) impulsa cartera de pedidos plurianual", "margin": 0.09, "mkt": "AM"},
];
window.NODES_EXPAND5 = NODES_EXPAND5;

// [source, target, weight, rel, type] — canónico: source PROVEE a target
var LINKS_EXPAND5 = [
  ["Vistra", "Amazon", 5.0, "PPA a 20 años (+20 opcional), 1,200 MW en la planta nuclear Comanche Peak (TX), firmado 2024, energización 2027-2032", "ppa"],
  ["Vistra", "Meta", 5.0, "PPAs a 20 años por 2,600+ MW en plantas nucleares Perry y Davis-Besse (Ohio), anunciados 2024-2025", "ppa"],
  ["TalenEnergy", "Amazon", 5.0, "Ampliación de PPA (jun 2025) a 1,920 MW en Susquehanna, contrato de ~$18B vigente hasta 2042", "ppa"],
  ["TalenEnergy", "Constellation", 1.0, "Comparable/competidor directo en el modelo IPP nuclear-para-datacenter dentro del mercado PJM", "partner"],
  ["NRGEnergy", "Nvidia", 2.0, "Colaboración anunciada en GTC 2025 (con GE Vernova) para optimizar el diseño de nuevas plantas de gas mediante herramientas de IA de Nvidia", "partner"],
  ["NRGEnergy", "CoreWeave", 1.0, "Pipeline de ~4 GW en cartas de intención con hyperscalers de IA no revelados públicamente (2025-2026)", "ppa"],
  ["Constellation", "Calpine", 3.0, "Adquirida por Constellation Energy en enero 2026 ($16.4B), formando el mayor productor privado de electricidad de EEUU", "partner"],
  ["Calpine", "CyrusOne", 3.0, "Acuerdo de suministro eléctrico a datacenters de IA/nube de CyrusOne en Texas, post-fusión con Constellation (2026)", "supply"],
  ["PSEG", "Constellation", 1.0, "Comparable de mercado PJM; ambas exploran monetizar activos nucleares (Hope Creek, Salem) para datacenters de IA citando el acuerdo Talen-Amazon como modelo", "partner"],
  ["PSEG", "Alphabet", 1.0, "En conversaciones para contratos de energía nuclear de largo plazo con operadores de datacenters; pipeline de 9.4 GW (90% datacenters) reportado en 2026", "ppa"],
  ["AEP", "Alphabet", 4.0, "Clean Capacity Arrangement (jul 2025) vía Indiana Michigan Power: Google cede capacidad limpia a cambio de suministro/respuesta a demanda en su datacenter de Fort Wayne ($2B)", "ppa"],
  ["AEP", "Amazon", 2.0, "Parte del pipeline de ~63 GW de gran carga contratada (~90% ligada a datacenters) en Ohio y Texas", "ppa"],
  ["AEP", "Meta", 1.0, "Involucrada junto a Google, Amazon y Microsoft en disputa regulatoria sobre tarifas especiales para datacenters de IA (2025)", "partner"],
  ["DominionEnergy", "Amazon", 4.0, "Acuerdo (oct 2024) para explorar reactores modulares pequeños (SMR) cerca de la planta nuclear North Anna, Virginia", "ppa"],
  ["DominionEnergy", "Meta", 3.0, "Cliente clave de datacenters en 'Data Center Alley' (norte de Virginia), ~40 GW bajo contrato total del territorio", "ppa"],
  ["DominionEnergy", "Microsoft", 3.0, "Cliente clave de datacenters en 'Data Center Alley' (norte de Virginia)", "ppa"],
  ["DominionEnergy", "Alphabet", 2.0, "Cliente de datacenters en el territorio de servicio de Dominion en Virginia", "ppa"],
  ["DukeEnergy", "Meta", 2.0, "Cliente de datacenters de IA en el territorio de servicio de Duke en Carolina del Norte", "ppa"],
  ["DukeEnergy", "Amazon", 2.0, "Parte del pipeline de ~14 GW de nueva demanda ligada a datacenters de IA anunciado en el plan de capex 2026", "ppa"],
  ["DukeEnergy", "Microsoft", 1.0, "Cliente de datacenters de IA dentro del territorio regulado de Duke", "ppa"],
  ["SouthernCompany", "Meta", 3.0, "Sirve creciente demanda de datacenters de IA de Meta en Georgia; ventas eléctricas industriales +42% i.a. ligadas en parte a hyperscalers", "ppa"],
  ["SouthernCompany", "Microsoft", 2.0, "Cliente de datacenters de IA en el territorio de servicio de Georgia Power (Southern Company)", "ppa"],
  ["PPLCorp", "Amazon", 2.0, "JV con Blackstone (jul 2025) para desarrollar hasta 6.75 GW de generación a gas en Pensilvania destinada a datacenters de IA", "ppa"],
  ["PPLCorp", "Microsoft", 1.0, "Parte del pipeline de 28.3 GW de solicitudes de gran carga de datacenters en el territorio de PPL", "ppa"],
  ["RollsRoyceSMR", "SiemensEnergy", 1.0, "Relación típica de la industria SMR europea para turbinas/equipos de balance de planta; sin contrato específico públicamente confirmado", "partner"],
  ["GEHitachiNuclear", "Alphabet", 3.0, "Acuerdo early-works con Google/Elementl Power (Ohio) por hasta 1.5 GW de reactores BWRX-300, operación estimada ~2034", "deploy"],
  ["Cameco", "WestinghouseElectric", 3.0, "Cameco posee el 49% de Westinghouse desde la adquisición conjunta con Brookfield en 2023; codesarrollan estrategia de suministro de combustible y reactores", "partner"],
  ["Kazatomprom", "Cameco", 4.0, "Co-propietarios de la joint venture de producción de uranio Inkai en Kazajistán (Cameco 40%, Kazatomprom 60%)", "partner"],
  ["NexGenEnergy", "Constellation", 1.0, "En conversaciones exploratorias con utilities/proveedores de datacenters de EEUU (no confirmado por nombre) para offtake de uranio ligado a demanda de IA (feb 2026)", "supply"],
  ["DenisonMines", "Constellation", 1.0, "Compromisos de venta de uranio (parcialmente en firme) con utilities norteamericanas de cara a primera producción en 2028", "supply"],
  ["PaladinEnergy", "Constellation", 1.0, "Suministrador del mercado spot/contratos de largo plazo a utilities nucleares occidentales (relación de mercado, sin contrato bilateral específico confirmado)", "supply"],
  ["UrEnergy", "Constellation", 1.0, "Proveedor doméstico estratégico de uranio para la flota nuclear estadounidense bajo contratos de largo plazo (relación de mercado sectorial)", "supply"],
  ["GlobalAtomic", "Constellation", 1.0, "90% de la producción inicial de Dasa ya pre-contratada con utilities de EEUU (nombres específicos no revelados públicamente)", "supply"],
  ["BossEnergy", "Constellation", 1.0, "Proveedor de uranio de mercado a utilities norteamericanas bajo contratos de largo plazo (relación sectorial)", "supply"],
  ["GeneralFusion", "Helion", 1.0, "Competidor directo en la carrera de fusión nuclear comercial para datacenters de IA; Helion ya tiene PPA con Microsoft mientras General Fusion aún no", "partner"],
  ["ZapEnergy", "Helion", 1.0, "Competidor en el sector de fusión nuclear orientado a resolver la demanda energética de datacenters de IA", "partner"],
  ["CentrusEnergy", "TerraPower", 4.0, "Principal candidato para suministrar combustible HALEU al reactor Natrium de TerraPower (Kemmerer, Wyoming) bajo contratos del DOE", "supply"],
  ["CentrusEnergy", "Xenergy", 4.0, "Designado por el DOE como proveedor de HALEU para el reactor Xe-100 de X-energy bajo el programa ARDP", "supply"],
  ["CentrusEnergy", "KairosPower", 3.0, "Suministro de HALEU contemplado para el reactor de demostración Hermes de Kairos Power bajo programas del DOE", "supply"],
  ["Orano", "Cameco", 2.0, "Co-participan en la diversificación de cadenas de suministro occidentales de conversión/enriquecimiento de uranio fuera de Rusia", "partner"],
  ["Orano", "Constellation", 1.0, "Proveedor de servicios de conversión/enriquecimiento a utilities nucleares occidentales bajo contratos de mercado", "supply"],
  ["china-northern-rare-earth", "Tesla", 1.0, "óxidos NdPr para imanes de motores EV", "supply"],
  ["china-northern-rare-earth", "GEVernova", 1.0, "compuestos de tierras raras para generadores eólicos", "supply"],
  ["china-northern-rare-earth", "BMW", 1.0, "tierras raras para motores eléctricos", "supply"],
  ["iluka-resources", "GEVernova", 0.4, "futuro suministro de NdPr para imanes de turbinas eólicas (planeado)", "supply"],
  ["iluka-resources", "BMW", 0.4, "contrato de offtake de tierras raras magnéticas (jun-2026, cliente no identificado públicamente)", "supply"],
  ["ucore-rare-metals", "sumitomo-chemical", 0.3, "colaboración anunciada jun-2026 (alcance no confirmado)", "partner"],
  ["ucore-rare-metals", "Raytheon", 0.4, "elementos de tierras raras críticos para cadena de suministro de defensa de EEUU", "supply"],
  ["arafura-resources", "GEVernova", 0.4, "futuro suministro de NdPr para imanes de turbinas (planeado, post-FID)", "supply"],
  ["arafura-resources", "BMW", 0.4, "potencial cliente de óxido de NdPr para motores EV", "supply"],
  ["vital-metals", "EnergyFuels", 0.3, "actores paralelos en diversificación de minerales críticos en Norteamérica (sin acuerdo comercial confirmado)", "partner"],
  ["air-products", "Samsung", 1.0, "expansión de suministro de gases industriales a la fábrica de Pyeongtaek (anuncio abril 2026)", "supply"],
  ["air-products", "TSMC", 0.6, "contrato de USD 900M para mercado de semiconductores taiwanés (cliente no revelado, TSMC es el actor dominante)", "supply"],
  ["resonac-holdings", "TSMC", 1.0, "films no conductores (NCF) para empaquetado avanzado; premio TSMC 2025", "supply"],
  ["resonac-holdings", "AMAT", 0.3, "consorcio US-JOINT de empaquetado avanzado", "partner"],
  ["resonac-holdings", "KLA", 0.3, "consorcio US-JOINT de empaquetado avanzado", "partner"],
  ["resonac-holdings", "TEL", 0.3, "consorcio US-JOINT de empaquetado avanzado", "partner"],
  ["kanto-denka-kogyo", "TSMC", 1.0, "NF3/WF6 para planta de Kumamoto", "supply"],
  ["kanto-denka-kogyo", "Samsung", 1.0, "NF3/WF6 para fabricación de semiconductores", "supply"],
  ["kanto-denka-kogyo", "SKHynix", 1.0, "gases especiales para memoria", "supply"],
  ["kanto-denka-kogyo", "Micron", 1.0, "gases especiales para memoria", "supply"],
  ["kanto-denka-kogyo", "Rapidus", 1.0, "dependencia exclusiva de NF3", "supply"],
  ["nitto-denko", "TSMC", 0.6, "cintas de dicing y films de back-grinding (relación típica del sector, no confirmada por nombre)", "supply"],
  ["nitto-denko", "Samsung", 0.6, "polarizadores para paneles OLED", "supply"],
  ["sumitomo-chemical", "TSMC", 1.0, "fotorresistentes ArF/EUV (cliente típico taiwanés líder del sector)", "supply"],
  ["sumitomo-chemical", "Samsung", 0.6, "fotorresistentes para litografía", "supply"],
  ["mitsubishi-gas-chemical", "TSMC", 0.5, "peróxido de hidrógeno electrónico (planta Taiwán con retrasos de certificación, cliente no confirmado por nombre)", "supply"],
  ["mitsubishi-gas-chemical", "TataSemiconductor", 0.4, "materiales de empaquetado BT para nueva capacidad en EEUU/Asia", "supply"],
  ["adeka-corporation", "Samsung", 0.7, "precursores ALD/CVD para expansión de Hwaseong", "supply"],
  ["adeka-corporation", "SKHynix", 0.6, "materiales high-k para memoria avanzada", "supply"],
  ["tosoh-corporation", "TSMC", 0.6, "sputtering targets de alta pureza (relación típica del sector)", "supply"],
  ["tosoh-corporation", "Samsung", 0.6, "sputtering targets para fabricación de obleas", "supply"],
  ["fujimi-incorporated", "Entegris", 0.3, "colaboración CMP heredada del acuerdo con Cabot Microelectronics (2018)", "partner"],
  ["fujimi-incorporated", "TSMC", 0.6, "slurries CMP para pulido de obleas (cliente típico del sector)", "supply"],
  ["fujimi-incorporated", "Samsung", 0.6, "slurries CMP para pulido de cobre", "supply"],
  ["kyocera-corporation", "Nvidia", 0.4, "sustratos cerámicos para empaquetado de chips de IA (relación típica del sector, no confirmada por nombre)", "supply"],
  ["kyocera-corporation", "Samsung", 0.4, "componentes cerámicos para electrónica avanzada", "supply"],
  ["tokamak-energy", "CommonwealthFusion", 0.3, "actores paralelos en el ecosistema occidental de fusión por confinamiento magnético", "partner"],
  ["tokamak-energy", "TAETechnologies", 0.3, "colaboración de industria en desarrollo de fusión (contexto sectorial, no confirmado como acuerdo formal)", "partner"],
  ["CommonwealthFusion", "type-one-energy", 0.8, "licencia exclusiva del cable superconductor HTS VIPER (feb-2025)", "license"],
  ["type-one-energy", "GEVernova", 0.3, "ecosistema de infraestructura energética en el despliegue de la planta piloto TVA (contexto, no confirmado como acuerdo directo)", "partner"],
  ["pacific-fusion", "CommonwealthFusion", 0.3, "competidor/comparable en el ecosistema de startups de fusión mejor financiadas", "partner"],
  ["pacific-fusion", "TAETechnologies", 0.3, "competidor/comparable en financiación de fusión privada", "partner"],
  ["nissan-chemical", "TSMC", 0.6, "recubrimientos BARC/ARC para litografía EUV (relación típica del sector, no confirmada por nombre)", "supply"],
  ["nissan-chemical", "Samsung", 0.6, "materiales multicapa para litografía avanzada", "supply"],
  ["chang-chun-group", "TSMC", 1.0, "fotorresistentes y materiales electrónicos especializados", "supply"],
  ["chang-chun-group", "ASE", 0.6, "materiales para empaquetado y ensamblaje", "supply"],
  ["stella-chemifa", "Samsung", 1.0, "ácido fluorhídrico de alta pureza para grabado de obleas", "supply"],
  ["stella-chemifa", "SKHynix", 1.0, "ácido fluorhídrico de alta pureza para fabricación de memoria", "supply"],
  ["brewer-science", "nissan-chemical", 0.8, "licencia de tecnología de recubrimientos antirreflectantes desde 1997 (renovada hasta 2028)", "license"],
  ["brewer-science", "Intel", 0.4, "materiales de litografía para fabs estadounidenses (relación típica del sector)", "supply"],
  ["jcet", "Cambricon", 1.0, "empaquetado y test avanzado para chips IA de Cambricon", "supply"],
  ["jcet", "HiSilicon", 1.0, "packaging avanzado 2.5D/3D para chips Ascend de Huawei", "supply"],
  ["jcet", "SMIC", 0.3, "colaboración fab-OSAT dentro de la cadena de suministro doméstica china", "partner"],
  ["pti", "Micron", 1.0, "empaquetado y test de DRAM/NAND para Micron", "supply"],
  ["pti", "SKHynix", 1.0, "servicios de test/empaquetado de memoria HBM", "supply"],
  ["pti", "Nanya", 1.0, "empaquetado de DRAM para Nanya", "supply"],
  ["kyec", "TSMC", 0.3, "test dedicado para clientes fabless del ecosistema de fundición TSMC", "partner"],
  ["kyec", "ASE", 0.3, "par y competidor en el ecosistema OSAT/test de Taiwán", "partner"],
  ["chipbond", "Himax_Tech", 1.0, "bumping y empaquetado COF para drivers de pantalla de Himax", "supply"],
  ["chipbond", "Navitas", 1.0, "empaquetado de semiconductores GaN de potencia", "supply"],
  ["chipbond", "Wolfspeed", 0.3, "colaboración en empaquetado de dispositivos SiC", "partner"],
  ["biren", "AlibabaCloud", 1.0, "suministra GPGPUs BR100/BR104 para infraestructura de nube IA china", "supply"],
  ["SMIC", "biren", 0.3, "depende de SMIC como fundición doméstica sustituta tras perder acceso a TSMC", "partner"],
  ["biren", "Cambricon", 0.3, "par en el ecosistema chino de chips IA domésticos frente a Nvidia", "partner"],
  ["DeepSeek", "moorethreads", 0.3, "Liang Wenfeng, fundador de DeepSeek, fue inversor institucional temprano", "partner"],
  ["SMIC", "moorethreads", 0.3, "depende de fundición doméstica para la fabricación de sus GPUs", "partner"],
  ["moorethreads", "AlibabaCloud", 1.0, "suministra GPUs MTT para infraestructura de nube IA china", "supply"],
  ["SMIC", "unisoc", 0.3, "fabrica en nodos maduros domésticos de SMIC", "partner"],
  ["unisoc", "Xiaomi", 1.0, "suministra SoCs para smartphones de gama económica", "supply"],
  ["SMIC", "starfive", 0.3, "fabrica sus SoCs RISC-V en fundiciones domésticas chinas", "partner"],
  ["starfive", "ARM", 0.3, "arquitectura RISC-V rival que compite por reducir la dependencia china del ecosistema Arm", "partner"],
  ["SMIC", "loongson", 0.3, "fabrica sus CPUs en fundiciones domésticas de nodo maduro para reducir dependencia de TSMC/Samsung", "partner"],
  ["loongson", "Lenovo", 1.0, "suministra CPUs LoongArch para PCs/servidores domésticos", "supply"],
  ["SMIC", "enflame", 0.3, "depende de fundiciones domésticas para la fabricación de sus aceleradores IA", "partner"],
  ["enflame", "Cambricon", 0.3, "par competidor dentro del ecosistema chino de chips IA domésticos", "partner"],
  ["nexperia", "NXP", 0.3, "escindida de NXP en 2017, mantiene lazos tecnológicos y de producto", "partner"],
  ["nexperia", "BMW", 1.0, "suministra MOSFETs y discretos para electrónica automotriz", "supply"],
  ["nexperia", "Stellantis", 1.0, "proveedor de semiconductores discretos para vehículos", "supply"],
  ["vishay", "BMW", 1.0, "suministra componentes pasivos y discretos para electrónica automotriz", "supply"],
  ["vishay", "Vertiv", 1.0, "provee componentes de potencia para infraestructura de datacenter", "supply"],
  ["vishay", "Rockwell_Automation", 1.0, "suministra componentes discretos/pasivos para automatización industrial", "supply"],
  ["HPE", "juniper", 0.3, "adquirida por HPE en julio 2025 por $14B; HPE es ahora su matriz", "partner"],
  ["juniper", "Cisco", 0.3, "competidor histórico en routers y switches empresariales", "partner"],
  ["juniper", "Arista", 0.3, "competencia directa en networking IA de datacenter", "partner"],
  ["f5", "T_Mobile", 1.0, "provee soluciones de entrega de aplicaciones y seguridad de red a operadoras telco", "supply"],
  ["f5", "CrowdStrike", 0.3, "integración de seguridad de aplicaciones/API en ecosistemas empresariales", "partner"],
  ["f5", "Cloudflare", 0.3, "competidor y complemento en seguridad de aplicaciones y APIs en la nube", "partner"],
  ["americantower", "T_Mobile", 1.0, "arrienda espacio de torre a T-Mobile como inquilino principal", "supply"],
  ["americantower", "Equinix", 0.3, "competencia/complemento en colocation de datacenter vía CoreSite", "partner"],
  ["americantower", "DigitalRealty", 0.3, "competidor en infraestructura de datacenter para clientes cloud", "partner"],
  ["crowncastle", "T_Mobile", 1.0, "arrienda espacio de torre, uno de los tres inquilinos principales (~90% de ingresos)", "supply"],
  ["crowncastle", "americantower", 0.3, "competidor directo en el mercado de REIT de torres inalámbricas de EE.UU.", "partner"],
  ["gds", "AlibabaCloud", 1.0, "provee espacio de datacenter carrier-neutral para infraestructura de nube de Alibaba", "supply"],
  ["Vertiv", "gds", 0.3, "despliega infraestructura de energía/enfriamiento de Vertiv en sus datacenters IA", "partner"],
  ["adva", "Nokia", 0.3, "competidor y par en el desplazamiento de proveedores chinos en redes europeas", "partner"],
  ["adva", "Ciena", 0.3, "competidor directo en equipos de transporte óptico", "partner"],
  ["fabrinet", "Nvidia", 1.0, "fabrica transceptores ópticos 800G/1.6T para redes de IA de Nvidia", "supply"],
  ["fabrinet", "Ciena", 1.0, "manufactura contratada de módulos ópticos para Ciena", "supply"],
  ["fabrinet", "Lumentum", 1.0, "fabrica componentes ópticos de precisión para Lumentum", "supply"],
  ["fabrinet", "Cisco", 1.0, "produce transceptores ópticos bajo contrato para equipos de networking de Cisco", "supply"],
  ["colt", "Lumen", 0.3, "adquirió el negocio EMEA de Lumen en 2022 por $1.8B", "partner"],
  ["colt", "CBOE", 1.0, "provee infraestructura de baja latencia vía MarketPrizm para datos de mercado financiero", "supply"],
  ["colt", "VirtuFinancial", 1.0, "conectividad de baja latencia para trading de alta frecuencia", "supply"],
  ["wingtech", "nexperia", 0.6, "matriz y accionista mayoritario de Nexperia desde 2019", "owns"],
  ["wingtech", "Xiaomi", 1.0, "fabricación ODM de smartphones para Xiaomi", "supply"],
  ["sba", "T_Mobile", 1.0, "arrienda espacio de torre a operadoras móviles como T-Mobile", "supply"],
  ["sba", "americantower", 0.3, "competidor directo en el mercado de REIT de torres de EE.UU.", "partner"],
  ["chindata", "AlibabaCloud", 1.0, "provee colocation hyperscale a Alibaba Cloud", "supply"],
  ["chindata", "Huawei", 0.3, "cliente/socio de infraestructura en China", "partner"],
  ["vantage-dc", "Microsoft", 1.0, "provee campus hyperscale a Azure", "supply"],
  ["vantage-dc", "Meta", 1.0, "construye capacidad dedicada para Meta", "supply"],
  ["Vertiv", "vantage-dc", 0.3, "usa infraestructura de energía/enfriamiento Vertiv", "supply"],
  ["stack-infra", "Amazon", 1.0, "provee capacidad de datacenter a AWS", "supply"],
  ["Vertiv", "stack-infra", 0.3, "infraestructura crítica de energía/refrigeración", "supply"],
  ["Nvidia", "crusoe-energy", 1.0, "opera flotas masivas de GPU Nvidia H100/B200", "supply"],
  ["crusoe-energy", "OpenAI", 0.9, "provee cómputo dedicado para el proyecto Stargate", "cloud"],
  ["crusoe-energy", "Constellation", 0.3, "acuerdos de suministro de energía para datacenters", "partner"],
  ["Nvidia", "voltage-park", 1.0, "opera flotas de GPU H100/H200 alquiladas", "supply"],
  ["voltage-park", "CoreWeave", 0.3, "competidor/comparable directo en el mercado neocloud", "partner"],
  ["fluidstack", "Anthropic", 0.9, "acuerdo de infraestructura de $50.000M", "cloud"],
  ["Alphabet", "fluidstack", 0.25, "inversor y ancla de capacidad", "invest"],
  ["Nvidia", "fluidstack", 1.0, "opera flotas masivas de GPU Nvidia", "supply"],
  ["Nvidia", "nscale", 1.0, "opera GPUs Nvidia bajo asignación directa e inversión estratégica", "supply"],
  ["nscale", "Microsoft", 0.9, "socio de capacidad de cómputo para Azure en Europa", "cloud"],
  ["AMD", "tensorwave", 1.0, "opera flotas de GPU AMD Instinct MI300/MI325 e recibe inversión directa de AMD", "supply"],
  ["Nvidia", "northern-data", 1.0, "opera clústeres de GPU Nvidia para Taiga Cloud", "supply"],
  ["Nvidia", "yotta-data-services", 1.0, "opera GPUs Nvidia para Shakti Cloud, caso de estudio oficial de Nvidia", "supply"],
  ["zayo-group", "vantage-dc", 0.3, "interconecta campus de datacenters hyperscale", "partner"],
  ["zayo-group", "Equinix", 0.3, "interconexión de fibra entre nodos de colocation", "partner"],
  ["cologix", "Equinix", 0.3, "competidor/comparable en interconexión de colocation", "partner"],
  ["Nvidia", "ntt-gdc", 0.5, "despliega GPUs Nvidia en sus datacenters para clientes de IA", "supply"],
  ["ntt-gdc", "Microsoft", 0.6, "provee capacidad de datacenter a hyperscalers globales", "supply"],
  ["princeton-digital-group", "AlibabaCloud", 0.6, "provee capacidad de datacenter a clientes cloud regionales", "supply"],
  ["edgeconnex", "LambdaLabs", 0.3, "construye conjuntamente fábrica de IA de alta densidad en Chicago", "partner"],
  ["Vertiv", "edgeconnex", 0.3, "infraestructura de energía/enfriamiento de alta densidad", "supply"],
  ["Nvidia", "lightning-ai", 1.0, "opera GPUs Nvidia para entrenamiento/fine-tuning", "supply"],
  ["Nvidia", "fourier-intelligence", 1.0, "Nvidia provee GPUs/plataforma Isaac para cómputo de IA embebida en los robots GR", "supply"],
  ["Microsoft", "sanctuary-ai", 0.25, "Microsoft ha invertido/colaborado con Sanctuary AI en cómputo en la nube para su IA Carbon", "invest"],
  ["SoftBank", "skild-ai", 0.25, "SoftBank lideró la Serie C de $1.4B en enero 2026", "invest"],
  ["Nvidia", "skild-ai", 0.25, "Nvidia es inversionista estratégico y proveedor de cómputo GPU para entrenamiento del modelo fundacional", "invest"],
  ["Samsung", "skild-ai", 0.25, "Samsung participó como inversionista estratégico", "invest"],
  ["skild-ai", "Zebra_Technologies", 0.3, "Skild AI adquirió el negocio robótico de Zebra Technologies en abril 2026", "partner"],
  ["SoftBank", "berkshire-grey", 0.6, "SoftBank adquirió Berkshire Grey en 2023 y la integró en su división de robótica", "owns"],
  ["berkshire-grey", "ABB_Robotics", 0.3, "Ambas son parte del portafolio de robótica industrial de SoftBank tras la compra de ABB Robotics en 2025", "partner"],
  ["covariant", "Amazon", 0.8, "Covariant licenció su tecnología de IA de picking a Amazon en agosto 2024 (reverse acquihire de fundadores)", "license"],
  ["Nvidia", "covariant", 0.25, "Nvidia fue inversionista en rondas previas de Covariant", "invest"],
  ["Microsoft", "covariant", 0.25, "Microsoft participó como inversionista estratégico", "invest"],
  ["Nvidia", "dexterity", 1.0, "Nvidia provee cómputo GPU/plataforma Isaac para la percepción y control del DexR", "supply"],
  ["Rockwell_Automation", "righthand-robotics", 0.25, "Rockwell Automation es inversionista estratégico de RightHand Robotics", "invest"],
  ["Nvidia", "righthand-robotics", 1.0, "Uso probable de cómputo Nvidia para el sistema de visión y agarre RightPick (práctica estándar del sector)", "supply"],
  ["SoftBank", "symbotic", 0.25, "SoftBank invirtió ~$100M en la JV GreenBox (Warehouse-as-a-Service) con Symbotic", "invest"],
  ["Nvidia", "locus-robotics", 1.0, "Cómputo embebido para navegación autónoma de los robots Origin/Vector (práctica estándar del sector AMR)", "supply"],
  ["Amazon", "locus-robotics", 0.9, "Infraestructura cloud probable para la plataforma analítica LocusONE", "cloud"],
  ["Nvidia", "vicarious-surgical", 1.0, "Cómputo probable para el procesamiento de visión estereoscópica 3D del sistema quirúrgico", "supply"],
  ["Nvidia", "ambi-robotics", 1.0, "GPUs RTX A6000/Quadro RTX 4000 para el modelo de IA de percepción PRIME-1", "supply"],
  ["ambi-robotics", "Yaskawa", 0.3, "Yaskawa Motoman es socio de integración de hardware para los sistemas AmbiSort/AmbiStack", "partner"],
  ["Nvidia", "diligent-robotics", 1.0, "Moxi 2.0 usa el procesador Nvidia IGX Thor (Blackwell) para cómputo embebido", "supply"],
  ["Nvidia", "chef-robotics", 1.0, "Cómputo de visión para el sistema de 3 cámaras del brazo Chef+ (práctica estándar del sector)", "supply"],
  ["realtime-robotics", "BMW", 0.4, "BMW utiliza RapidPlan de Realtime Robotics para planificación de movimiento en sus fábricas", "deploy"],
  ["SiemensEDA", "realtime-robotics", 0.25, "Siemens (vía su brazo de venture capital Next47) es inversionista de Realtime Robotics", "invest"],
  ["NEC", "formic", 0.25, "NEC es inversionista de Formic", "invest"],
  ["Amazon", "zipline", 0.9, "Infraestructura cloud probable para la coordinación logística de la red de drones (práctica estándar del sector)", "cloud"],
  ["Qualcomm", "zipline", 1.0, "Módulos de conectividad/cómputo embebido probables para los drones Platform 2 (práctica estándar del sector)", "supply"],
  ["Alphabet", "wing-alphabet", 0.6, "Wing es subsidiaria 100% de Alphabet dentro de su portafolio de Other Bets", "owns"],
  ["Qualcomm", "wing-alphabet", 1.0, "Chips de conectividad/cómputo embebido probables para los drones VTOL (práctica estándar del sector)", "supply"],
  ["Nvidia", "skydio", 1.0, "Uso histórico de cómputo Nvidia Jetson para autonomía embebida en generaciones anteriores de drones", "supply"],
  ["Qualcomm", "skydio", 1.0, "Chips Snapdragon Flight utilizados en generaciones de drones Skydio para cómputo/conectividad", "supply"],
  ["Nvidia", "waabi", 0.25, "NVentures (brazo de VC de Nvidia) invirtió en la Serie C de Waabi", "invest"],
  ["Nvidia", "waabi", 1.0, "Waabi usa la plataforma de cómputo vehicular de Nvidia para sus camiones autónomos", "supply"],
  ["Lynas", "ubtech-robotics", 1.0, "Proveedor potencial de imanes de tierras raras para actuadores de humanoides (riesgo de cadena de suministro fuera de China)", "supply"],
  ["ubtech-robotics", "Foxconn", 0.3, "Foxconn y UBTech firmaron cooperación estratégica en IA+robótica para manufactura", "partner"],
  ["Huawei", "agibot-zhiyuan", 1.0, "Chips de cómputo Huawei Ascend probables para robots destinados al mercado doméstico chino (alternativa a Nvidia por controles de exportación)", "supply"],
  ["AlibabaCloud", "agibot-zhiyuan", 0.9, "Infraestructura cloud china probable para entrenamiento de modelos de IA a escala (práctica estándar del sector chino)", "cloud"],
  ["Qualcomm", "neura-robotics", 0.25, "Qualcomm es inversionista estratégico en la Serie C de $1.4B", "invest"],
  ["Nvidia", "neura-robotics", 0.25, "Nvidia es inversionista estratégico y miembro del Humanoid Robot Developer Program desde 2024", "invest"],
  ["Amazon", "neura-robotics", 0.25, "Amazon es inversionista estratégico en la Serie C de $1.4B", "invest"],
  ["SpaceX", "vast-space", 0.3, "Lanzamiento en Falcon 9 y transporte de tripulación en Dragon", "partner"],
  ["vast-space", "AxiomSpace", 0.3, "Competidor directo en estaciones espaciales comerciales LEO", "partner"],
  ["vast-space", "Redwire", 0.3, "Colaboración en payloads e investigación en microgravedad", "partner"],
  ["SpaceX", "ispace", 0.3, "Lanzamiento de misiones lunares en Falcon 9", "partner"],
  ["ispace", "IntuitiveMachines", 0.3, "Par y competidor en aterrizajes lunares comerciales tipo CLPS", "partner"],
  ["ispace", "Airbus", 0.3, "Colaboración europea en misiones de exploración lunar", "partner"],
  ["RocketLab", "astroscale", 0.3, "Lanzamiento de misiones de demostración de captura de basura", "partner"],
  ["astroscale", "Maxar", 0.3, "Colaboración en servicing y extensión de vida de satélites", "partner"],
  ["astroscale", "BAESystems", 0.3, "Programas conjuntos de conciencia situacional espacial en Reino Unido", "partner"],
  ["SpaceX", "d-orbit", 0.3, "Lanzamiento de ION Satellite Carrier en misiones rideshare Transporter", "partner"],
  ["d-orbit", "PlanetLabs", 0.3, "Despliegue de satélites de observación terrestre", "partner"],
  ["d-orbit", "Airbus", 0.3, "Colaboración en misiones de defensa y logística espacial europea", "partner"],
  ["SpaceX", "momentus", 0.3, "Lanzamiento de Vigoride en misiones rideshare Transporter", "partner"],
  ["momentus", "Redwire", 0.3, "Competidor y potencial colaborador en infraestructura orbital", "partner"],
  ["SpaceX", "loft-orbital", 0.3, "Lanzamiento de satélites YAM en misiones rideshare", "partner"],
  ["loft-orbital", "Eutelsat", 0.3, "Hosting de payloads de comunicaciones", "partner"],
  ["loft-orbital", "L3Harris", 0.3, "Integración de sensores de defensa en plataformas hosted", "partner"],
  ["SpaceX", "terran-orbital", 0.3, "Lanzamiento de buses satelitales en misiones dedicadas y rideshare", "partner"],
  ["RocketLab", "terran-orbital", 0.3, "Lanzamientos dedicados de misiones de defensa", "partner"],
  ["terran-orbital", "Northrop", 0.3, "Par y colaborador en programas de buses para la capa de rastreo de la Space Development Agency", "partner"],
  ["abl-space-systems", "Raytheon", 0.3, "Competencia y colaboración en interceptores de misiles para defensa antimisiles", "partner"],
  ["abl-space-systems", "Northrop", 0.3, "Colaboración en motores de cohete sólido para programas de defensa de misiles", "partner"],
  ["sierra-nevada-corporation", "SierraSpace", 0.6, "Empresa matriz que escindió la unidad comercial de espacio en 2021", "owns"],
  ["sierra-nevada-corporation", "Raytheon", 0.3, "Integración de sistemas de guerra electrónica y aviónica", "partner"],
  ["sierra-nevada-corporation", "L3Harris", 0.3, "Colaboración en sistemas ISR y comunicaciones tácticas", "partner"],
  ["voyager-technologies", "Airbus", 0.3, "Socio de ingeniería y manufactura para la estación espacial Starlab", "partner"],
  ["voyager-technologies", "AxiomSpace", 0.3, "Competidor directo por contratos de estaciones comerciales sucesoras de la ISS", "partner"],
  ["voyager-technologies", "vast-space", 0.3, "Competidor en el mercado de estaciones espaciales comerciales LEO", "partner"],
  ["voyager-technologies", "SpaceX", 0.3, "Lanzamiento de módulos y misiones de reabastecimiento", "partner"],
  ["sidus-space", "SpaceX", 1.0, "Fabricación de componentes de precisión para vehículos de lanzamiento", "supply"],
  ["sidus-space", "BlueOrigin", 1.0, "Manufactura de piezas aeroespaciales", "supply"],
  ["sidus-space", "PlanetLabs", 0.3, "Competidor en datos de observación terrestre como servicio", "partner"],
  ["nanoavionics", "SpaceX", 0.3, "Lanzamiento de buses de clientes en misiones rideshare", "partner"],
  ["nanoavionics", "RocketLab", 0.3, "Competidor y ocasional integrador de lanzamientos dedicados", "partner"],
  ["nanoavionics", "Saab_AB", 0.3, "Colaboración en programas de defensa espacial europea vía Kongsberg", "partner"],
  ["exolaunch", "SpaceX", 0.3, "Principal integrador de payloads en misiones rideshare Transporter", "partner"],
  ["exolaunch", "PlanetLabs", 0.3, "Integración y despliegue de satélites de observación terrestre", "partner"],
  ["exolaunch", "nanoavionics", 0.3, "Integración de buses de nanosatélites en misiones compartidas", "partner"],
  ["karman-space-defense", "Raytheon", 1.0, "Suministro de componentes estructurales para sistemas interceptores de misiles", "supply"],
  ["karman-space-defense", "Northrop", 1.0, "Suministro de motores de cohete sólido y estructuras hipersónicas", "supply"],
  ["karman-space-defense", "L3Harris", 0.3, "Colaboración en programas de defensa antimisiles", "partner"],
  ["true-anomaly", "Anduril", 0.3, "Colaboración en autonomía y sistemas de defensa de próxima generación", "partner"],
  ["true-anomaly", "SpaceX", 0.3, "Lanzamiento de vehículos Jackal en misiones rideshare", "partner"],
  ["true-anomaly", "Kratos_Defense", 0.3, "Integración de sistemas de comando y control de dominio espacial", "partner"],
  ["impulse-space", "SpaceX", 0.3, "Lanzamiento de vehículos Mira y Helios en misiones rideshare Transporter", "partner"],
  ["impulse-space", "Anduril", 0.3, "Misión conjunta de demostración de transferencia orbital para el Departamento de Defensa", "partner"],
  ["impulse-space", "varda-space-industries", 0.3, "Provee la etapa de transferencia orbital Mira para misiones de manufactura en microgravedad", "partner"],
  ["RocketLab", "varda-space-industries", 1.0, "Provee el bus satelital Photon que aloja la cápsula de manufactura de Varda", "supply"],
  ["varda-space-industries", "SpaceX", 0.3, "Lanzamiento de misiones W-series en rideshare Transporter", "partner"],
  ["varda-space-industries", "impulse-space", 0.3, "Exploración conjunta de vehículos de transferencia orbital para futuras misiones", "partner"],
  ["orbit-fab", "true-anomaly", 0.3, "Colaboración en infraestructura de seguridad y servicio orbital para Space Force", "partner"],
  ["orbit-fab", "Northrop", 0.3, "Integración de puertos de reabastecimiento en programas de extensión de vida satelital", "partner"],
  ["orbit-fab", "SpaceX", 0.3, "Lanzamiento de misiones de demostración de reabastecimiento", "partner"],
  ["starfish-space", "astroscale", 0.3, "Competidor directo en el mercado de servicing y extensión de vida orbital", "partner"],
  ["starfish-space", "SpaceX", 0.3, "Lanzamiento de vehículos Otter en misiones rideshare", "partner"],
  ["starfish-space", "PlanetLabs", 0.3, "Cliente potencial para extensión de vida de constelaciones de observación terrestre", "partner"],
  ["space-forge", "RocketLab", 0.3, "Lanzamiento de misiones ForgeStar", "partner"],
  ["space-forge", "varda-space-industries", 0.3, "Competidor y par en manufactura orbital reutilizable", "partner"],
  ["space-forge", "Infineon", 0.3, "Exploración conjunta de aplicaciones de semiconductores fabricados en órbita", "partner"],
  ["helsing", "Saab_AB", 0.3, "Coopera en drones submarinos autónomos", "partner"],
  ["helsing", "Anduril", 0.3, "Par/competidor en ecosistema de defensa con IA-nativa", "partner"],
  ["Mistral", "helsing", 0.8, "Colaboración en modelos de IA para aplicaciones militares", "license"],
  ["helsing", "Rheinmetall", 0.3, "Integración potencial de software IA en plataformas terrestres alemanas", "partner"],
  ["Microsoft", "helsing", 0.9, "Infraestructura cloud para entrenamiento de modelos", "cloud"],
  ["elbit-systems", "Raytheon", 0.3, "Alianzas en programas conjuntos de defensa aérea", "partner"],
  ["elbit-systems", "L3Harris", 0.3, "Competencia/colaboración en sistemas C4ISR para EE.UU.", "partner"],
  ["elbit-systems", "Booz_Allen", 0.3, "Consultoría/integración en programas gubernamentales de EE.UU.", "partner"],
  ["elbit-systems", "Kratos_Defense", 1.0, "Provisión de componentes/subsistemas de drones tácticos", "supply"],
  ["iai-israel-aerospace", "Boeing", 0.3, "Colaboración en el programa de defensa antimisiles Arrow", "partner"],
  ["iai-israel-aerospace", "Raytheon", 0.3, "Programas conjuntos EE.UU.-Israel de defensa antimisiles", "partner"],
  ["iai-israel-aerospace", "Northrop", 0.3, "Cooperación en tecnología satelital y espacial", "partner"],
  ["rafael-advanced-defense", "Raytheon", 0.8, "Coproducción bajo licencia de Iron Dome para EE.UU.", "license"],
  ["rafael-advanced-defense", "Rheinmetall", 0.3, "Colaboración en el sistema Trophy para blindados europeos", "partner"],
  ["rafael-advanced-defense", "BAESystems", 0.3, "Integración de Trophy en vehículos blindados de socios OTAN", "partner"],
  ["rafael-advanced-defense", "Leonardo_DRS", 1.0, "Suministro de componentes electrónicos/sensores", "supply"],
  ["Microsoft", "general-dynamics", 0.9, "GDIT despliega Azure Government para cargas de trabajo del DoD", "cloud"],
  ["general-dynamics", "Palantir", 0.3, "Integración de plataformas de datos/IA para mando y control", "partner"],
  ["GE_Aerospace", "general-dynamics", 1.0, "Motores para jets Gulfstream", "supply"],
  ["general-dynamics", "L3Harris", 0.3, "Colaboración en sistemas de misión y comunicaciones", "partner"],
  ["general-dynamics", "Boeing", 0.3, "Programas conjuntos de defensa/espacio", "partner"],
  ["Nvidia", "lockheed-martin", 1.0, "GPUs para simulación de vuelo, entrenamiento de IA y autonomía", "supply"],
  ["Microsoft", "lockheed-martin", 0.9, "Uso de Azure Government para plataformas de datos de misión", "cloud"],
  ["lockheed-martin", "Palantir", 0.3, "Integración de IA/análisis de datos en sistemas de combate conjunto", "partner"],
  ["lockheed-martin", "Raytheon", 0.3, "Joint venture en misiles Javelin y defensa antimisiles", "partner"],
  ["Northrop", "lockheed-martin", 1.0, "Fabricación del fuselaje central del F-35 como subcontratista", "supply"],
  ["textron-systems", "ShieldAI", 0.3, "Integración de software de autonomía en plataformas no tripuladas", "partner"],
  ["L3Harris", "textron-systems", 1.0, "Suministro de sensores y comunicaciones para sistemas UAS", "supply"],
  ["textron-systems", "Kratos_Defense", 0.3, "Coexistencia en el mercado de drones tácticos y blanco", "partner"],
  ["textron-systems", "Anduril", 0.3, "Competencia y colaboración en autonomía para el Ejército de EE.UU.", "partner"],
  ["textron-systems", "general-dynamics", 0.3, "Programas conjuntos de vehículos terrestres", "partner"],
  ["GE_Aerospace", "hanwha-aerospace", 0.8, "Producción bajo licencia de motores F404/F414", "license"],
  ["hanwha-aerospace", "lockheed-martin", 0.3, "Colaboración en el caza KF-21 y defensa antimisiles", "partner"],
  ["hanwha-aerospace", "Rheinmetall", 0.3, "Competencia/colaboración en artillería autopropulsada en Europa", "partner"],
  ["hanwha-aerospace", "Leonardo_DRS", 0.3, "Alianzas para expansión de capacidad naval en EE.UU.", "partner"],
  ["hanwha-aerospace", "Northrop", 0.3, "Cooperación en misiles y defensa aérea integrada", "partner"],
  ["babcock-international", "BAESystems", 0.3, "Colaboración en programas navales y de submarinos nucleares UK", "partner"],
  ["babcock-international", "Rheinmetall", 0.3, "Cooperación en vehículos blindados y municiones en Europa", "partner"],
  ["babcock-international", "Airbus", 1.0, "Mantenimiento y soporte de flotas de helicópteros y aviones militares", "supply"],
  ["babcock-international", "Booz_Allen", 0.3, "Colaboración en consultoría de defensa y ciberseguridad", "partner"],
  ["babcock-international", "Thales", 0.3, "Cooperación en sistemas navales y de comunicaciones", "partner"],
  ["qinetiq", "BAESystems", 0.3, "Colaboración en defensa electrónica y ensayo de sistemas UK", "partner"],
  ["qinetiq", "Raytheon", 0.3, "Cooperación en guerra electrónica y sensores", "partner"],
  ["qinetiq", "Booz_Allen", 0.3, "Competencia/colaboración en consultoría de defensa e inteligencia en EE.UU.", "partner"],
  ["qinetiq", "Thales", 0.3, "Colaboración en sistemas de defensa electrónica europeos", "partner"],
  ["Alphabet", "xanadu-quantum", 0.9, "Distribución de acceso a procesadores cuánticos vía Google Cloud Marketplace", "cloud"],
  ["Amazon", "xanadu-quantum", 0.9, "Disponibilidad de hardware fotónico en Amazon Braket", "cloud"],
  ["xanadu-quantum", "IBMQuantum", 0.3, "Colaboración en estándares de software cuántico", "partner"],
  ["xanadu-quantum", "PsiQuantum", 0.3, "Competencia/coordinación en computación cuántica fotónica", "partner"],
  ["Bluefors", "iqm-quantum", 1.0, "Sistemas de refrigeración criogénica finlandeses para procesadores superconductores", "supply"],
  ["OxfordInstruments", "iqm-quantum", 1.0, "Componentes criogénicos y de control cuántico", "supply"],
  ["iqm-quantum", "QuantumMachines", 0.3, "Integración de electrónica de control cuántico", "partner"],
  ["Microsoft", "iqm-quantum", 0.9, "Distribución de acceso a hardware cuántico vía Azure Quantum", "cloud"],
  ["iqm-quantum", "IBMQuantum", 0.3, "Competencia/coordinación en estándares de computación cuántica superconductora", "partner"],
  ["alice-bob-quantum", "Thales", 0.3, "Colaboración en investigación cuántica para defensa y comunicaciones seguras francesas", "partner"],
  ["alice-bob-quantum", "QuantumMachines", 0.3, "Integración de sistemas de control y electrónica cuántica", "partner"],
  ["alice-bob-quantum", "Pasqal", 0.3, "Coordinación dentro del ecosistema de soberanía cuántica francesa", "partner"],
  ["alice-bob-quantum", "IBMQuantum", 0.3, "Comparación tecnológica y colaboración en estándares de corrección de errores", "partner"],
  ["seeqc-quantum", "IBMQuantum", 0.3, "Colaboración técnica en arquitecturas de control cuántico superconductor", "partner"],
  ["seeqc-quantum", "Rigetti", 0.3, "Coordinación en el ecosistema de hardware cuántico superconductor de EE.UU.", "partner"],
  ["Bluefors", "seeqc-quantum", 1.0, "Sistemas de refrigeración criogénica para chips de control SFQ", "supply"],
  ["seeqc-quantum", "QuantumMachines", 0.3, "Competencia/coordinación en electrónica de control cuántico", "partner"],
  ["atom-computing", "Microsoft", 0.3, "Colaboración de I+D en corrección de errores cuánticos, acceso vía Azure Quantum", "partner"],
  ["atom-computing", "IonQ", 0.3, "Competidor directo en hardware cuántico comercial de EE.UU.", "partner"],
  ["atom-computing", "Rigetti", 0.3, "Par del ecosistema de startups cuánticas estadounidenses", "partner"],
  ["atom-computing", "Nvidia", 0.3, "Integración con CUDA-Q para simulación híbrida cuántico-clásica", "partner"],
  ["infleqtion", "Quantinuum", 0.3, "Par competidor en hardware cuántico empresarial de EE.UU./UK", "partner"],
  ["infleqtion", "DWave", 0.3, "Otro actor del ecosistema cuántico comercial estadounidense", "partner"],
  ["infleqtion", "Nvidia", 0.3, "Integración de software cuántico-clásico híbrido", "partner"],
  ["Bluefors", "infleqtion", 1.0, "Infraestructura de vacío/óptica de precisión", "supply"],
  ["Nvidia", "world-labs", 1.0, "Dependencia de GPUs para entrenamiento de modelos de mundo 3D", "supply"],
  ["Alphabet", "world-labs", 0.9, "Infraestructura cloud para entrenamiento e inferencia", "cloud"],
  ["CoreWeave", "world-labs", 0.9, "Proveedor de cómputo GPU especializado en IA", "cloud"],
  ["world-labs", "OpenAI", 0.3, "Competidor/par en la carrera por modelos de mundo generativos", "partner"],
  ["Nvidia", "sakana-ai", 0.25, "Inversor y proveedor de GPUs para entrenamiento", "invest"],
  ["Alphabet", "sakana-ai", 0.9, "Infraestructura cloud para cómputo de IA", "cloud"],
  ["Microsoft", "sakana-ai", 0.9, "Acceso a cómputo Azure para modelos fundacionales", "cloud"],
  ["sakana-ai", "FujitsuHPC", 0.3, "Colaboración con el gobierno japonés usando la supercomputadora Fugaku", "partner"],
  ["sakana-ai", "OpenAI", 0.3, "Par competidor en el ecosistema global de laboratorios de IA", "partner"],
  ["Nvidia", "reflection-ai", 0.25, "Inversor y proveedor de GPUs para entrenamiento de modelos de frontera", "invest"],
  ["CoreWeave", "reflection-ai", 0.9, "Cómputo GPU especializado en la nube para entrenamiento", "cloud"],
  ["Microsoft", "reflection-ai", 0.9, "Acceso a infraestructura Azure para cómputo a escala", "cloud"],
  ["reflection-ai", "Anthropic", 0.3, "Competidor/par en laboratorios de IA para codificación", "partner"],
  ["Nvidia", "poolside-ai", 1.0, "Dependencia crítica de GPUs para su clúster de entrenamiento dedicado", "supply"],
  ["CoreWeave", "poolside-ai", 0.9, "Posible socio de infraestructura GPU en la nube", "cloud"],
  ["Amazon", "poolside-ai", 0.9, "Infraestructura cloud complementaria", "cloud"],
  ["poolside-ai", "OpenAI", 0.3, "Competidor directo en IA para generación de código", "partner"],
  ["Thales", "naval-group", 0.3, "Accionista minoritario y proveedor de sistemas de combate/sonar", "partner"],
  ["naval-group", "Airbus", 0.3, "Colaboración en programas de defensa europeos", "partner"],
  ["naval-group", "BAESystems", 0.3, "Coordinación en programas navales europeos", "partner"],
  ["naval-group", "Raytheon", 0.3, "Cooperación puntual en sistemas de misiles navales", "partner"],
  ["Thales", "dassault-aviation", 1.0, "Aviónica, radar y sistemas de misión para el Rafale", "supply"],
  ["dassault-aviation", "Airbus", 0.3, "Socio (y rival de liderazgo) en el caza de sexta generación SCAF/FCAS", "partner"],
  ["dassault-aviation", "BAESystems", 0.3, "Competencia europea en programas de aviación militar de próxima generación", "partner"],
  ["dassault-aviation", "Raytheon", 0.3, "Competencia en el mercado global de cazas y sistemas de misión", "partner"],
  ["Anthropic", "Cognition", 0.8, "Devin utiliza modelos Claude de Anthropic como uno de sus motores de razonamiento de agente", "license"],
  ["Microsoft", "Cognition", 0.9, "Windsurf (adquirida por Cognition) dependía de infraestructura Azure OpenAI Service para inferencia", "cloud"],
  ["Nvidia", "Cognition", 1.0, "Entrenamiento e inferencia de agentes de codificación corren sobre GPUs Nvidia en la nube", "supply"],
  ["Cognition", "Salesforce", 0.3, "Integraciones piloto de agentes de codificación con flujos empresariales tipo Agentforce", "partner"],
  ["Nvidia", "Imbue", 0.25, "Nvidia participó como inversor en la ronda de $200M de 2023, valorando a Imbue en más de $1B", "invest"],
  ["Microsoft", "Imbue", 0.9, "Cómputo de entrenamiento de modelos propietarios corre en infraestructura cloud alquilada tipo Azure/AWS", "cloud"],
  ["Imbue", "Cognition", 0.3, "Ambas startups compiten y colaboran en el ecosistema de agentes de codificación autónomos, compartiendo inversores", "partner"],
  ["OpenAI", "Voiceflow", 0.8, "Voiceflow integra modelos GPT de OpenAI como motor de generación de diálogo en sus agentes", "license"],
  ["Anthropic", "Voiceflow", 0.8, "Ofrece integración nativa con modelos Claude para construcción de agentes conversacionales", "license"],
  ["Amazon", "Voiceflow", 0.9, "Plataforma SaaS alojada en infraestructura AWS", "cloud"],
  ["Voiceflow", "Salesforce", 0.3, "Conectores para desplegar agentes de Voiceflow dentro de flujos de atención al cliente tipo Salesforce Service Cloud", "partner"],
  ["OpenAI", "AlphaSenseFin", 0.8, "AlphaSense Generative Search usa modelos GPT de OpenAI para resúmenes y respuestas basadas en documentos financieros", "license"],
  ["Amazon", "AlphaSenseFin", 0.9, "Infraestructura de búsqueda y almacenamiento documental corre sobre AWS", "cloud"],
  ["AlphaSenseFin", "Microsoft", 0.3, "Integración empresarial con Microsoft 365/Teams para distribución de insights", "partner"],
  ["Amazon", "Kensho", 0.9, "Kensho documentó públicamente su infraestructura de ML entrenada y desplegada sobre AWS", "cloud"],
  ["Kensho", "NASDAQ", 0.3, "Kensho colabora con proveedores de datos de mercado del sector, incluyendo integraciones de feeds bursátiles", "partner"],
  ["Kensho", "FactSet", 0.3, "Competencia/coopetencia en el mercado de analítica financiera con solapamiento de clientes institucionales", "partner"],
  ["Amazon", "Kavout", 0.9, "Infraestructura de scoring cuantitativo y almacenamiento de datos de mercado corre sobre AWS", "cloud"],
  ["NASDAQ", "Kavout", 0.3, "Consume feeds de datos de mercado de Nasdaq para generar sus señales de inversión", "partner"],
  ["Microsoft", "Kavout", 0.3, "Programas de aceleración/soporte técnico para startups fintech de IA sobre Azure", "partner"],
  ["Amazon", "Addepar", 0.9, "Plataforma de agregación de datos financieros alojada en infraestructura AWS", "cloud"],
  ["MSCI", "Addepar", 0.3, "Integra datos de riesgo y benchmarks de MSCI para análisis de carteras multi-activo", "partner"],
  ["Morningstar", "Addepar", 0.3, "Incorpora datos de research y ratings de Morningstar en sus reportes de inversión", "partner"],
  ["Microsoft", "FactSet", 0.9, "FactSet migró infraestructura y servicios de IA a Microsoft Azure como parte de su transformación cloud", "cloud"],
  ["OpenAI", "FactSet", 0.8, "FactSet Mercury (asistente de IA generativa) usa modelos GPT de OpenAI", "license"],
  ["NASDAQ", "FactSet", 0.3, "Distribuye y consume feeds de datos de mercado de Nasdaq dentro de su plataforma de analítica", "partner"],
  ["Amazon", "Morningstar", 0.9, "Infraestructura de datos y analítica de Morningstar corre principalmente sobre AWS", "cloud"],
  ["Morningstar", "MSCI", 0.3, "Competencia y coopetencia en datos ESG/riesgo con solapamiento de clientes institucionales", "partner"],
  ["Morningstar", "NASDAQ", 0.3, "Distribución de datos de fondos e índices vinculados a productos listados en Nasdaq", "partner"],
  ["Amazon", "NASDAQ", 0.9, "Nasdaq anunció en 2021 un acuerdo estratégico plurianual para migrar su tecnología de mercados a AWS Cloud", "cloud"],
  ["NASDAQ", "FactSet", 0.3, "Provee feeds de datos de mercado consumidos por la plataforma de FactSet", "partner"],
  ["NASDAQ", "CBOE", 0.3, "Ambas bolsas colaboran en estándares de datos de mercado e infraestructura regulatoria compartida en EE.UU.", "partner"],
  ["Alphabet", "CBOE", 0.9, "Cboe anunció una alianza estratégica con Google Cloud para migrar su infraestructura de mercado de datos y trading", "cloud"],
  ["CBOE", "NASDAQ", 0.3, "Coordinación de infraestructura regulatoria y estándares de datos de mercado entre bolsas de EE.UU.", "partner"],
  ["VirtuFinancial", "CBOE", 0.3, "Virtu es uno de los principales market makers/proveedores de liquidez en los mercados operados por Cboe", "partner"],
  ["AlphaSense", "Databricks", 0.3, "Integración de datos de research vía marketplace/pipelines de datos tipo Databricks para clientes empresariales", "partner"],
  ["AlphaSense", "Snowflake", 0.3, "Distribución de contenido de research a través del marketplace de datos de Snowflake", "partner"],
  ["Amazon", "AlphaSense", 0.9, "Infraestructura de búsqueda semántica y almacenamiento documental corre sobre AWS", "cloud"],
  ["AlphaSense", "Databricks", 0.3, "Integración de datos de research vía pipelines de datos empresariales tipo Databricks", "partner"],
  ["Amazon", "AlphaSense", 0.9, "Infraestructura de búsqueda semántica y almacenamiento documental corre sobre AWS", "cloud"],
  ["AlphaSense", "Microsoft", 0.3, "Integración con Microsoft 365/Teams para distribución de insights financieros", "partner"],
  ["Microsoft", "MSCI", 0.9, "MSCI y Microsoft anunciaron una alianza estratégica para llevar datos privados/ESG de MSCI a Azure", "cloud"],
  ["MSCI", "Morningstar", 0.3, "Coopetencia en datos de riesgo y ESG con solapamiento de clientes de gestión de activos", "partner"],
  ["MSCI", "Addepar", 0.3, "Datos de riesgo/benchmarks de MSCI se integran en plataformas de gestión patrimonial como Addepar", "partner"],
  ["Nvidia", "Crane_NXT", 1.0, "Sistemas de visión por computadora para autenticación de billetes usan aceleradores GPU Nvidia", "supply"],
  ["Microsoft", "Crane_NXT", 0.9, "Servicios de analítica de datos de sus sistemas de validación de efectivo corren sobre infraestructura cloud Azure", "cloud"],
  ["Crane_NXT", "Zebra_Technologies", 0.3, "Colaboración en soluciones de captura de datos e identificación para sistemas de pago/retail", "partner"],
  ["CoreWeave", "Suno", 0.9, "Entrenamiento e inferencia de modelos generativos de audio se apoya en cómputo GPU alquilado tipo CoreWeave", "cloud"],
  ["Nvidia", "Suno", 1.0, "Modelos de generación musical entrenados sobre clústeres de GPUs Nvidia", "supply"],
  ["Microsoft", "Suno", 0.3, "Programas de startups de IA generativa con créditos y soporte técnico en Azure", "partner"],
  ["Amazon", "GenDigital", 0.9, "Infraestructura de análisis de amenazas y telemetría de seguridad corre sobre AWS", "cloud"],
  ["GenDigital", "CrowdStrike", 0.3, "Intercambio de inteligencia de amenazas dentro del ecosistema de ciberseguridad del consumidor y empresarial", "partner"],
  ["GenDigital", "Zscaler", 0.3, "Integraciones de seguridad en la nube y protección de endpoints con proveedores de seguridad complementarios", "partner"],
  ["Microsoft", "Trimble_Inc", 0.9, "Trimble y Microsoft anunciaron una alianza estratégica para su plataforma Trimble Connect/Construction sobre Azure", "cloud"],
  ["Trimble_Inc", "Boeing", 1.0, "Sistemas de posicionamiento de precisión de Trimble se usan en manufactura y ensamblaje aeroespacial", "supply"],
  ["Microsoft", "Trimble_Inc", 0.9, "Trimble y Microsoft anunciaron una alianza estratégica para su plataforma Trimble Connect/Construction sobre Azure", "cloud"],
  ["Trimble_Inc", "Boeing", 1.0, "Sistemas de posicionamiento de precisión GNSS de Trimble se usan en manufactura y ensamblaje aeroespacial", "supply"],
  ["Trimble_Inc", "Rockwell_Automation", 0.3, "Colaboración en soluciones de automatización y guiado de precisión para maquinaria industrial", "partner"],
  ["Amazon", "Verint", 0.9, "La plataforma Verint Da Vinci de IA corre sobre infraestructura AWS", "cloud"],
  ["Verint", "Salesforce", 0.3, "Integraciones de analítica de interacciones de Verint con Salesforce Service Cloud", "partner"],
  ["OpenAI", "Verint", 0.8, "Verint incorpora modelos de lenguaje de OpenAI en sus bots de IA generativa para centros de contacto", "license"],
  ["Amazon", "Salesforce", 0.9, "Salesforce amplió su alianza con AWS en 2024 para ejecutar Data Cloud e IA generativa sobre infraestructura AWS", "cloud"],
  ["Alphabet", "Salesforce", 0.9, "Alianza estratégica Salesforce-Google Cloud (2022) para IA generativa e infraestructura de datos", "cloud"],
  ["Salesforce", "Anthropic", 0.25, "Salesforce Ventures participó en rondas de financiamiento de Anthropic como parte de su estrategia de IA generativa", "invest"],
  ["Salesforce", "HuggingFace", 0.25, "Salesforce Ventures invirtió en Hugging Face como parte de su portafolio de infraestructura de IA abierta", "invest"],
  ["Raytheon", "Boeing", 1.0, "Pratt & Whitney/Collins Aerospace suministra motores y aviónica a Boeing (777, KC-46)", "supply"],
  ["Raytheon", "Airbus", 1.0, "Motores Pratt & Whitney GTF equipan el Airbus A320neo y A220", "supply"],
  ["Microsoft", "Raytheon", 0.9, "Alianza RTX-Microsoft (2023) para usar Azure OpenAI Service en ingeniería digital", "cloud"],
  ["Raytheon", "Palantir", 0.3, "Colaboración anunciada para IA en cadenas de mando y control (kill chain)", "partner"],
  ["Leidos", "Nvidia", 0.3, "Alianza de ciberseguridad con IA anunciada en 2025 (con VAST Data)", "partner"],
  ["Leidos", "Palantir", 0.3, "Colaboración en plataformas de datos/IA para clientes gubernamentales", "partner"],
  ["Amazon", "Leidos", 0.9, "Amplio uso de AWS GovCloud para cargas de trabajo federales clasificadas", "cloud"],
  ["Microsoft", "Leidos", 0.9, "Servicios en la nube Azure Government para contratos de defensa", "cloud"],
  ["Parsons", "Leidos", 0.3, "Co-adjudicatarios del contrato MDA SHIELD de defensa antimisiles (2025)", "partner"],
  ["Parsons", "Raytheon", 0.3, "Colaboración en programas de defensa antimisiles (MDA SHIELD)", "partner"],
  ["Parsons", "L3Harris", 0.3, "Teaming en contratos de defensa espacial y de misiles", "partner"],
  ["Microsoft", "AxonEnterprise", 0.9, "Draft One, su herramienta de IA para redactar reportes policiales, corre sobre Azure OpenAI Service", "cloud"],
  ["Amazon", "AxonEnterprise", 0.9, "Plataforma Evidence.com alojada en infraestructura de AWS", "cloud"],
  ["AxonEnterprise", "Palantir", 0.3, "Integración de datos para agencias de seguridad pública", "partner"],
  ["Alphabet", "Thales", 0.9, "Joint venture S3NS con Google Cloud para nube soberana en Francia (2023-2025)", "cloud"],
  ["Thales", "Imperva", 0.6, "Thales adquirió Imperva (ciberseguridad) en 2023", "owns"],
  ["STMicroelectronics", "Thales", 1.0, "Proveedor de semiconductores para sistemas de radar y aviónica de Thales", "supply"],
  ["Thales", "Rheinmetall", 0.3, "Colaboración europea en programas de defensa terrestre y municiones", "partner"],
  ["PaloAltoNetworks", "Nvidia", 0.3, "Colaboración en blueprints de seguridad para infraestructuras de IA", "partner"],
  ["Amazon", "PaloAltoNetworks", 0.9, "Prisma Cloud protege e integra con cargas de trabajo de AWS", "cloud"],
  ["Microsoft", "PaloAltoNetworks", 0.9, "Integración de Cortex XSIAM con Microsoft Azure", "cloud"],
  ["Teledyne_Flir", "Raytheon", 1.0, "Proveedor de sensores térmicos para sistemas guiados y misiles de RTX", "supply"],
  ["Teledyne_Flir", "Anduril", 1.0, "Sensores térmicos/infrarrojos integrados en plataformas de Anduril", "supply"],
  ["Teledyne_Flir", "L3Harris", 0.3, "Integración de sensores en plataformas ISR conjuntas", "partner"],
  ["Raytheon", "Saab_AB", 1.0, "El radar AESA ES-05 Raven del Gripen E utiliza tecnología de Raytheon (RTX)", "supply"],
  ["Saab_AB", "Rheinmetall", 0.3, "Colaboración europea en municiones y defensa terrestre", "partner"],
  ["Microsoft", "Saab_AB", 0.9, "Adopción de Azure para plataformas de datos de defensa", "cloud"],
  ["ShieldAI", "L3Harris", 0.3, "Integración del sistema de autonomía Hivemind en plataformas de L3Harris", "partner"],
  ["ShieldAI", "Kratos_Defense", 0.3, "Colaboración en programas de aeronaves no tripuladas (CCA)", "partner"],
  ["ShieldAI", "Palantir", 0.3, "Integración de datos e IA para operaciones de defensa", "partner"],
  ["Hailo", "Renesas", 0.3, "Alianza (2024) para integrar aceleradores Hailo con microcontroladores Renesas en IA automotriz", "partner"],
  ["Hailo", "Foxconn", 0.3, "Colaboración para dispositivos de IA de borde/PC con el chip Hailo-10", "partner"],
  ["Hailo", "onsemi", 0.3, "Integración de sensores de imagen con aceleradores de IA de borde", "partner"],
  ["TSMC", "Untether_AI", 1.0, "Fabricaba sus chips speedAI en procesos TSMC (12nm)", "fab"],
  ["GF", "Untether_AI", 1.0, "Generación anterior de chips (tsunami) fabricada en procesos GlobalFoundries de 22nm", "fab"],
  ["Untether_AI", "Kratos_Defense", 0.3, "Participación en programas de IA de borde vinculados a contratos de defensa de EE.UU.", "partner"],
  ["Synopsys", "AnsysEDA", 0.6, "Synopsys completó la adquisición de Ansys en julio de 2025 (~$35.000M)", "owns"],
  ["AnsysEDA", "Nvidia", 0.3, "Simulación acelerada por GPU en colaboración con Nvidia Omniverse", "partner"],
  ["Microsoft", "AnsysEDA", 0.9, "Ansys Cloud se ejecuta sobre infraestructura de Microsoft Azure", "cloud"],
  ["Foxconn", "Kneron", 0.25, "Foxconn invirtió en Kneron y colabora en soluciones de IA de borde", "invest"],
  ["Qualcomm", "Kneron", 0.25, "Qualcomm Ventures invirtió en Kneron en ronda Serie B", "invest"],
  ["TSMC", "Kneron", 1.0, "Fabricación de sus chips KL en procesos TSMC", "fab"],
  ["GF", "Mythic", 1.0, "Fabrica sus chips analógicos de cómputo en memoria en procesos GlobalFoundries", "fab"],
  ["Mythic", "Raytheon", 0.3, "Participación en programas de IA de borde de bajo consumo vinculados a I+D de defensa", "partner"],
  ["TSMC", "GreenWaves", 1.0, "El chip GAP9 se fabrica en proceso TSMC de 22nm de ultra bajo consumo", "fab"],
  ["GreenWaves", "STMicroelectronics", 0.3, "Colaboración dentro del ecosistema europeo de IoT/RISC-V", "partner"],
  ["TSMC", "SiMa", 1.0, "El MLSoC se fabrica en proceso TSMC de 16nm", "fab"],
  ["ARM", "SiMa", 0.8, "Integra núcleos de CPU ARM Cortex bajo licencia en su SoC", "license"],
  ["SiMa", "Renesas", 0.3, "Alianza para plataformas de IA de borde en automoción", "partner"],
  ["Amazon", "Syntiant", 0.25, "El Alexa Fund de Amazon invirtió en Syntiant y sus chips se usan en dispositivos con Alexa", "invest"],
  ["Microsoft", "Syntiant", 0.25, "El fondo M12 de Microsoft es inversor de Syntiant", "invest"],
  ["AMAT", "Syntiant", 0.25, "Applied Ventures es inversor estratégico de Syntiant", "invest"],
  ["Infineon", "Syntiant", 0.3, "Infineon Ventures participó como inversor/socio estratégico", "partner"],
  ["Semtech", "Nvidia", 1.0, "Suministra chips de interconexión de cobre activo (CopperEdge) para servidores de IA de Nvidia", "supply"],
  ["TSMC", "Semtech", 1.0, "Fabricación de sus chips analógicos en procesos TSMC", "fab"],
  ["Semtech", "Amphenol", 0.3, "Colaboración en cables de cobre activo para centros de datos de IA", "partner"],
  ["MACOM", "Raytheon", 1.0, "Proveedor de componentes RF/microondas para sistemas de radar y misiles", "supply"],
  ["MACOM", "Nvidia", 1.0, "Suministra componentes ópticos de alta velocidad (800G) para infraestructura de IA", "supply"],
  ["MACOM", "L3Harris", 1.0, "Componentes de RF para sistemas de comunicación de defensa", "supply"],
  ["TSMC", "PowerIntegrations", 1.0, "Fabricación de sus chips de potencia en procesos TSMC", "fab"],
  ["PowerIntegrations", "DeltaElectronics", 0.3, "Colaboración en fuentes de alimentación de alta eficiencia", "partner"],
  ["PowerIntegrations", "Vertiv", 1.0, "Suministro de componentes de conversión de energía para infraestructura de centros de datos de IA", "supply"],
  ["TSMC", "Diodes", 1.0, "Subcontrata parte de su producción a fundiciones externas como TSMC", "fab"],
  ["Diodes", "Dell", 1.0, "Suministro de componentes discretos para servidores", "supply"],
  ["Diodes", "BMW", 1.0, "Proveedor de semiconductores automotrices para BMW", "supply"],
  ["Cirrus_Logic", "Apple", 1.0, "Proveedor dominante de chips de audio y gestión de energía para iPhone (>80% de sus ingresos)", "supply"],
  ["TSMC", "Cirrus_Logic", 1.0, "Fabricación de sus chips de señal mixta en procesos TSMC", "fab"],
  ["Cirrus_Logic", "Samsung", 1.0, "Proveedor de componentes de audio para dispositivos Samsung", "supply"],
  ["GF", "Innatera", 1.0, "Fabricación del chip neuromórfico Pulsar en proceso GF 22FDX", "fab"],
  ["ARM", "Innatera", 0.8, "Licencia de núcleo de control Cortex-M integrado junto al motor spiking en el SoC", "license"],
  ["Innatera", "STMicroelectronics", 0.3, "Colaboración en kits de referencia de IA de borde de bajo consumo", "partner"],
  ["Naver", "GrAI_Matter", 0.25, "NAVER D2SF (fondo corporativo de Naver) participó como inversor estratégico", "invest"],
  ["Samsung", "GrAI_Matter", 0.25, "Samsung Catalyst Fund invirtió en rondas tempranas de la compañía", "invest"],
  ["GrAI_Matter", "STMicroelectronics", 0.3, "Colaboración explorada para visión neuromórfica en aplicaciones automotrices", "partner"],
  ["GF", "Lightelligence", 1.0, "Fabricación de chips de fotónica de silicio en proceso de GlobalFoundries", "fab"],
  ["Lightelligence", "AlibabaCloud", 0.3, "Pilotos de aceleración óptica de IA con proveedores de nube chinos", "partner"],
  ["RockleyPhotonics", "Apple", 1.0, "Suministro y desarrollo de sensores ópticos para dispositivos wearables (Apple Watch)", "supply"],
  ["GF", "RockleyPhotonics", 1.0, "Fabricación de chips fotónicos de silicio en planta de GlobalFoundries", "fab"],
  ["RockleyPhotonics", "STMicroelectronics", 0.3, "Colaboración en empaquetado de componentes optoelectrónicos (VCSEL/fotodetectores)", "partner"],
  ["Amazon", "QuEra", 0.9, "Sistemas cuánticos de QuEra disponibles y ampliados en Amazon Braket, meta de tolerancia a fallos para 2028", "cloud"],
  ["Alphabet", "QuEra", 0.25, "Participación de Google en ronda de financiamiento de $230M", "invest"],
  ["SoftBank", "QuEra", 0.25, "Inversor en rondas de expansión de capital de QuEra", "invest"],
  ["Livent", "BMW", 1.0, "Acuerdo de suministro de largo plazo de hidróxido de litio para baterías EV de BMW", "supply"],
  ["Livent", "SQM", 0.3, "Coordinación de mercado dentro del triángulo del litio (Chile/Argentina)", "partner"],
  ["PiedmontLithium", "Tesla", 1.0, "Acuerdo de venta de concentrado de espodumeno/litio a Tesla desde 2020, ampliado en 2023", "supply"],
  ["PiedmontLithium", "Albemarle", 0.3, "Coordinación dentro de iniciativas de cadena de suministro de litio de EE.UU.", "partner"],
  ["SigmaLithium", "Tesla", 0.7, "Interés de suministro/adquisición reportado por Tesla sobre la producción de litio de Sigma", "supply"],
  ["SigmaLithium", "SQM", 0.3, "Referencia de mercado y potencial coordinación de oferta en el sector de litio sudamericano", "partner"],
  ["ArcadiumLithium", "BMW", 1.0, "Continuación del contrato heredado de Livent para suministro de hidróxido de litio a BMW", "supply"],
  ["ArcadiumLithium", "SQM", 0.3, "Coexistencia y coordinación de oferta en el triángulo del litio andino", "partner"],
  ["SQM", "Tesla", 1.0, "Acuerdo de suministro de carbonato de litio a Tesla para baterías EV", "supply"],
  ["SQM", "BMW", 1.0, "Suministro de compuestos de litio para cadena de baterías de BMW", "supply"],
  ["Nvidia", "CommonwealthFusion", 0.25, "Nvidia participó en la ronda Serie B2 de $863M (agosto 2025)", "invest"],
  ["Alphabet", "CommonwealthFusion", 0.25, "Google es inversor estratégico recurrente desde rondas previas", "invest"],
  ["Helion", "Microsoft", 0.7, "Primer acuerdo mundial de compra de energía de fusión (PPA), entrega objetivo 2028", "ppa"],
  ["Helion", "Constellation", 0.7, "Constellation gestiona la interconexión a la red del PPA de fusión Helion-Microsoft", "ppa"],
  ["Alphabet", "TAETechnologies", 0.25, "Google ha invertido de forma recurrente desde 2015, incluida nueva ronda en 2025", "invest"],
  ["TAETechnologies", "Constellation", 0.3, "Exploración conjunta de integración de energía de fusión avanzada a la red eléctrica de EE.UU.", "partner"],
  ["NuScale", "Constellation", 0.3, "Ambas exploran despliegue de energía nuclear avanzada para demanda de centros de datos de IA en EE.UU.", "partner"],
  ["Raytheon", "NuScale", 0.25, "Vínculo histórico de inversión temprana ligado a United Technologies/RTX en el desarrollo de la tecnología SMR", "invest"],
  ["KairosPower", "Alphabet", 0.7, "Primer PPA de energía nuclear Gen IV de EE.UU., junto con TVA, para alimentar centros de datos de Google", "ppa"],
  ["KairosPower", "Constellation", 0.3, "Colaboración de sector en despliegue de energía nuclear avanzada en el sureste de EE.UU.", "partner"],
  ["NioCorp", "GE_Aerospace", 1.0, "El niobio es insumo crítico de superaleaciones (tipo Inconel 718) usadas en turbinas de motores a reacción", "supply"],
  ["NioCorp", "Raytheon", 1.0, "Superaleaciones con niobio destinadas a motores Pratt & Whitney", "supply"],
  ["NioCorp", "Northrop", 0.7, "Programa financiado por el Pentágono para tecnología de defensa basada en escandio", "supply"],
  ["UraniumEnergy", "Constellation", 1.0, "Suministro de concentrado de uranio (U3O8) a utilities operadoras de plantas nucleares en EE.UU.", "supply"],
  ["UraniumEnergy", "Oklo", 0.7, "Posicionamiento como proveedor de combustible para reactores avanzados de próxima generación", "supply"],
  ["UraniumEnergy", "Xenergy", 0.7, "Cadena de suministro de uranio orientada a futuros reactores SMR de EE.UU.", "supply"],
  ["Danaher", "TSMC", 1.0, "Pall Corporation (Danaher) suministra sistemas de filtración ultrapura para fabricación de chips", "supply"],
  ["Danaher", "Intel", 1.0, "Suministro de tecnología de purificación de agua/gases para fabs de Intel", "supply"],
  ["Danaher", "Samsung", 1.0, "Sistemas de filtración crítica para líneas de producción de semiconductores de Samsung", "supply"],
  ["Cohu", "TexasInstruments", 1.0, "Cliente histórico más grande de equipos de prueba/manejo de semiconductores de Cohu", "supply"],
  ["Cohu", "STMicroelectronics", 1.0, "Suministro de handlers de prueba para líneas de producción de chips analógicos/potencia", "supply"],
  ["Cohu", "onsemi", 1.0, "Equipos de prueba utilizados en manufactura de semiconductores de potencia de onsemi", "supply"],
  ["Zeiss", "ASML", 1.0, "Proveedor exclusivo de la óptica EUV/DUV integrada en las máquinas de litografía de ASML", "supply"],
  ["Zeiss", "TSMC", 1.0, "Servicios de metrología e inspección/reparación de fotomáscaras para líneas de producción avanzadas", "supply"],
  ["Zeiss", "Samsung", 1.0, "Equipos de metrología óptica de precisión para fabs de semiconductores", "supply"],
  ["Trumpf", "ASML", 1.0, "Suministro del láser de CO2 de alta potencia que genera la luz EUV en las máquinas de litografía de ASML", "supply"],
  ["Trumpf", "BMW", 1.0, "Sistemas láser de corte y soldadura utilizados en líneas de producción automotriz de BMW", "supply"],
  ["Trumpf", "Airbus", 1.0, "Tecnología láser para manufactura de componentes aeroespaciales de Airbus", "supply"],
  ["Satellogic", "Rheinmetall", 0.3, "Joint venture para fabricación y operación de satélites de reconocimiento para defensa europea", "partner"],
  ["Satellogic", "Palantir", 0.3, "Integración de imágenes satelitales de Satellogic en la plataforma de análisis geoespacial de Palantir", "partner"],
  ["SpaceX", "Satellogic", 0.4, "Lanzamiento de satélites de la constelación mediante misiones rideshare de Falcon 9", "deploy"],
  ["Maxar", "HughesNetwork", 1.0, "Maxar fabricó el satélite Jupiter-3/EchoStar XXIV, pieza central de la red de banda ancha de Hughes", "supply"],
  ["Eutelsat", "HughesNetwork", 0.3, "Hughes distribuye y revende capacidad LEO de OneWeb para banda ancha empresarial y gubernamental", "partner"],
  ["Iridium", "HughesNetwork", 0.3, "Hughes integra conectividad de respaldo Iridium en soluciones IoT y retail (HughesON)", "partner"],
  ["SpaceX", "Orbcomm", 0.3, "Orbcomm lanzó su constelación OG2 en misiones dedicadas de Falcon 9 de SpaceX", "partner"],
  ["Orbcomm", "Iridium", 0.3, "Competidor/aliado ocasional en roaming de IoT satelital de doble red", "partner"],
  ["Orbcomm", "Trimble_Inc", 0.3, "Integración de datos de rastreo de flotas entre plataformas de telemática de Orbcomm y Trimble", "partner"],
  ["SpaceX", "IntuitiveMachines", 0.3, "SpaceX lanza las misiones lunares Nova-C de Intuitive Machines (IM-1, IM-2, IM-4) en Falcon 9", "partner"],
  ["IntuitiveMachines", "Boeing", 0.3, "Colaboración en el desarrollo de comunicaciones y soporte a Artemis para NASA", "partner"],
  ["IntuitiveMachines", "AxiomSpace", 0.3, "Ambas son contratistas comerciales clave del programa Artemis de NASA, colaborando en infraestructura lunar", "partner"],
  ["SierraSpace", "BlueOrigin", 0.3, "Codesarrollan la estación espacial comercial Orbital Reef", "partner"],
  ["SierraSpace", "Boeing", 0.3, "Boeing es socio en el consorcio de la estación espacial comercial Orbital Reef", "partner"],
  ["ULA", "SierraSpace", 0.3, "El Dream Chaser se lanza sobre cohetes Vulcan Centaur de ULA bajo contrato de reabastecimiento de la ISS para NASA", "partner"],
  ["SpaceX", "AxiomSpace", 0.3, "SpaceX transporta a las tripulaciones de las misiones privadas Axiom (Ax-1 a Ax-4) a la ISS en Crew Dragon", "partner"],
  ["Thales", "AxiomSpace", 1.0, "Thales Alenia Space (participada por Thales) construye la estructura primaria de los módulos de la estación Axiom", "supply"],
  ["AxiomSpace", "IntuitiveMachines", 0.3, "Colaboración como contratistas comerciales del ecosistema Artemis/CLPS de NASA", "partner"],
  ["PowerchipSemi", "TataSemiconductor", 0.8, "PSMC transfiere tecnología de fabricación para construir la primera fab de semiconductores de India (Dholera, Tata Electronics)", "license"],
  ["PowerchipSemi", "Vedanta_Semi", 0.3, "PSMC fue socio tecnológico original propuesto para el proyecto de fab de Vedanta-Foxconn en India antes de su reestructuración", "partner"],
  ["PowerchipSemi", "Rapidus", 0.3, "Colaboración regional asiática en transferencia de know-how de fabricación de semiconductores", "partner"],
  ["Vedanta_Semi", "Foxconn", 0.3, "Foxconn (Hon Hai) fue el socio original de la JV antes de retirarse en 2023", "partner"],
  ["Vedanta_Semi", "PowerchipSemi", 0.3, "PSMC fue evaluada como socio tecnológico alternativo tras la salida de Foxconn", "partner"],
  ["Vedanta_Semi", "TataSemiconductor", 0.3, "Compite directamente con Tata Electronics por el liderazgo del ecosistema de fabricación de chips en India", "partner"],
  ["Seagate", "Amazon", 1.0, "AWS es uno de los mayores compradores de discos HAMR de alta capacidad de Seagate para almacenamiento en nube", "supply"],
  ["Seagate", "Microsoft", 1.0, "Azure despliega discos duros Seagate Exos/Mozaic en su infraestructura de almacenamiento masivo", "supply"],
  ["Seagate", "Alphabet", 1.0, "Google Cloud es cliente hiperescala de unidades HAMR de Seagate para almacenamiento de IA", "supply"],
  ["IronMountain", "Microsoft", 0.9, "Microsoft es cliente ancla de colocación en varios data centers de Iron Mountain", "cloud"],
  ["IronMountain", "DigitalRealty", 0.3, "Compiten y colaboran en interconexión dentro del mismo ecosistema de REITs de data centers en EE.UU.", "partner"],
  ["IronMountain", "Equinix", 0.3, "Ambos REITs comparten mercados de colocación e interconexión de nube híbrida", "partner"],
  ["CyrusOne", "Microsoft", 0.9, "Microsoft arrienda capacidad significativa en campus de CyrusOne para cargas de IA", "cloud"],
  ["CyrusOne", "Meta", 0.9, "Meta es cliente de colocación de gran escala en instalaciones de CyrusOne", "cloud"],
  ["CyrusOne", "Oracle", 0.9, "Oracle Cloud Infrastructure ha arrendado capacidad de centros de datos de CyrusOne para expansión de IA", "cloud"],
  ["TSMC", "Cerebras", 1.0, "TSMC fabrica el Wafer Scale Engine (WSE-3) de Cerebras en su proceso de 5nm", "fab"],
  ["Cerebras", "OpenAI", 1.0, "Cerebras firmó un acuerdo de cómputo de inferencia con OpenAI valorado hasta US$10.000M", "supply"],
  ["Cerebras", "Mistral", 0.9, "Mistral AI utiliza la infraestructura de inferencia ultrarrápida de Cerebras para servir sus modelos", "cloud"],
  ["Cerebras", "Cloudflare", 0.3, "Cloudflare integró la inferencia de Cerebras en su red edge de IA", "partner"],
  ["Penguin_Solutions", "CoreWeave", 1.0, "Penguin Solutions integra y despliega clústeres de servidores GPU para CoreWeave", "supply"],
  ["Micron", "Penguin_Solutions", 1.0, "SMART Modular (Penguin Solutions) utiliza chips de memoria de Micron en sus módulos especializados", "supply"],
  ["Penguin_Solutions", "Nvidia", 0.3, "Penguin Solutions es integrador certificado de referencia (NPN) de arquitecturas de servidores Nvidia", "partner"],
  ["Sycamore", "Ciena", 0.3, "Competidor histórico directo en equipos de transporte óptico durante los 2000; ex-clientes de telecomunicaciones se trasladaron a Ciena", "partner"],
  ["Sycamore", "Nokia", 0.3, "El negocio óptico vendido por Sycamore (vía Coriant) fue posteriormente adquirido por activos hoy consolidados en la cartera de Nokia", "partner"],
  ["Sycamore", "InfiniteraNet", 0.3, "Comparte legado tecnológico y clientes de telecomunicaciones ópticas de Norteamérica de la era 2000-2010", "partner"],
  ["Silicom", "PaloAltoNetworks", 1.0, "Silicom fabrica SmartNICs/appliances OEM integrados en plataformas de seguridad de red de Palo Alto Networks", "supply"],
  ["Silicom", "Cisco", 0.3, "Provee tarjetas de conectividad especializadas compatibles con equipos de red Cisco", "partner"],
  ["Silicom", "Intel", 0.3, "Miembro del programa de socios Intel Network Builders, usando FPGAs y chips Intel en sus adaptadores", "partner"],
  ["Calix", "T_Mobile", 0.3, "Colabora con operadores de banda ancha fija inalámbrica que usan infraestructura de acceso de Calix", "partner"],
  ["Calix", "Nokia", 0.3, "Competidor y a la vez interoperador de estándares de acceso de fibra (GPON/XGS-PON) con Nokia", "partner"],
  ["Calix", "Ciena", 0.3, "Integración de equipos de transporte óptico de Ciena en redes de operadores clientes de Calix", "partner"],
  ["Calix_Net", "Amazon", 0.3, "NetScout provee visibilidad de red y detección de amenazas para entornos de nube híbrida que incluyen cargas en AWS", "partner"],
  ["Calix_Net", "Ericsson", 0.3, "Integración de monitoreo de red NetScout en infraestructuras 5G desplegadas con equipos Ericsson", "partner"],
  ["Calix_Net", "Cisco", 0.3, "Interoperabilidad y coexistencia con equipos de red Cisco en despliegues de monitoreo empresarial", "partner"],
  ["Lightsource_BP", "Microsoft", 0.7, "Lightsource bp firmó un PPA corporativo con Microsoft para suministrar energía solar a sus operaciones en Polonia y otros mercados", "ppa"],
  ["First_Solar", "Lightsource_BP", 1.0, "Lightsource bp compra paneles solares de fabricación estadounidense de First Solar para sus proyectos con contenido doméstico", "supply"],
  ["NexTracker", "Lightsource_BP", 1.0, "Utiliza seguidores solares de Nextracker en múltiples proyectos utility-scale", "supply"],
  ["NexTracker", "First_Solar", 0.3, "Coordina despliegues conjuntos en proyectos utility-scale que combinan paneles First Solar con seguidores Nextracker", "partner"],
  ["NexTracker", "Lightsource_BP", 1.0, "Provee sistemas de seguimiento solar a proyectos desarrollados por Lightsource bp", "supply"],
  ["NexTracker", "Array_Technologies", 0.3, "Principal competidor directo en el mercado de trackers solares utility-scale de EE.UU.", "partner"],
  ["Array_Technologies", "First_Solar", 0.3, "Sus seguidores solares se despliegan habitualmente junto a paneles First Solar en proyectos utility-scale en EE.UU.", "partner"],
  ["Array_Technologies", "NexTracker", 0.3, "Principal rival en el mercado de trackers solares; ambos compiten por los mismos contratos de desarrolladores", "partner"],
  ["Array_Technologies", "Lightsource_BP", 1.0, "Provee estructuras de seguimiento solar a proyectos desarrollados por Lightsource bp", "supply"],
  ["SiemensEnergy", "WiTricity", 0.25, "Siemens realizó una inversión estratégica en WiTricity para avanzar la carga inalámbrica de vehículos eléctricos", "invest"],
  ["WiTricity", "BMW", 0.8, "BMW ha explorado e integrado tecnología de carga inalámbrica basada en patentes de WiTricity en programas piloto de vehículos eléctricos", "license"],
  ["WiTricity", "Hyundai", 0.8, "Hyundai colabora con licenciatarios de WiTricity para sistemas de carga inalámbrica en sus plataformas EV", "license"],
  ["GE_Aerospace", "Boeing", 1.0, "GE Aerospace suministra motores GEnx y GE9X para las familias 787 y 777X de Boeing", "supply"],
  ["GE_Aerospace", "Raytheon", 0.3, "Compite y coopera en programas de defensa de propulsión con RTX/Pratt & Whitney", "partner"],
  ["GE_Aerospace", "Leonardo_DRS", 0.3, "Colaboración en programas de defensa y componentes aeroespaciales militares de EE.UU.", "partner"],
  ["Pegatron", "Apple", 1.0, "Pegatron es uno de los principales ensambladores de iPhones y otros dispositivos de Apple", "supply"],
  ["Nvidia", "Pegatron", 1.0, "Pegatron ensambla servidores y racks de infraestructura de IA basados en plataformas Nvidia", "supply"],
  ["Pegatron", "Microsoft", 1.0, "Fabrica servidores de infraestructura de nube/IA para despliegues de Microsoft Azure", "supply"],
  ["Pegatron", "Foxconn", 0.3, "Principal rival directo en el sector de manufactura electrónica por contrato (EMS) en Taiwán", "partner"],
];
window.LINKS_EXPAND5 = LINKS_EXPAND5;

// meta (founded/employees/revenue/geo_risk/desc) de nodos nuevos y enriquecidos
var META_EXPAND5 = {
 "Vistra": {
  "founded": 2016,
  "employees": 6850,
  "revenue_2025": "~$17.7B",
  "geo_risk": "Exposición a mercados desregulados de Texas (ERCOT) y PJM, y a aprobaciones NRC para ampliar capacidad nuclear.",
  "desc": "Emergida en 2016 del Chapter 11 de Energy Future Holdings, Vistra se convirtió en el mayor IPP de EEUU. Desde 2024 firmó los primeros grandes PPAs nucleares \"detrás/enfrente del contador\" con hyperscalers de IA, posicionándose como referencia del nuevo modelo negocio \"nuclear-para-datacenter\"."
 },
 "TalenEnergy": {
  "founded": 2015,
  "employees": 1900,
  "revenue_2025": "~$2.8B",
  "geo_risk": "Concentración de negocio en un único activo nuclear (Susquehanna) y en el mercado regulatorio PJM/Pensilvania.",
  "desc": "Spinoff de PPL en 2015, salió de Chapter 11 en 2023 y se reinventó como el caso de referencia del boom nuclear-IA al ampliar en junio 2025 su acuerdo con Amazon a 1,920 MW valorados en ~$18B hasta 2042."
 },
 "NRGEnergy": {
  "founded": 1989,
  "employees": 15673,
  "revenue_2025": "~$28B",
  "geo_risk": "Alta exposición a precios de gas natural y al mercado desregulado ERCOT de Texas.",
  "desc": "IPP texana que pasó de vender activos de carbón a anunciar 5.4 GW de nueva generación a gas junto a GE Vernova y Nvidia (feb 2025) específicamente para el mercado de datacenters de IA, con 4 GW en cartas de intención adicionales."
 },
 "Calpine": {
  "founded": 1984,
  "employees": 2400,
  "revenue_2025": "N/D (adquisición cerrada por $16.4B en efectivo+acciones, ~$26.6B con deuda)",
  "geo_risk": "Riesgo de integración regulatoria en múltiples estados de EEUU tras el cierre de la adquisición en enero 2026.",
  "desc": "Fundada en 1984, Calpine fue el mayor operador de gas natural y geotérmico de EEUU antes de ser adquirida por Constellation Energy (anuncio ene 2025, cierre ene 2026), formando el mayor productor de electricidad privado del mundo, combinando la mayor flota nuclear de EEUU con la mayor flota de gas."
 },
 "PSEG": {
  "founded": 1985,
  "employees": 12945,
  "revenue_2025": "~$10.5B",
  "geo_risk": "Regulación estatal de Nueva Jersey (BPU) y riesgo político sobre tarifas especiales para datacenters.",
  "desc": "Utility regulada con la mayor concentración de clientes de datacenter de Nueva Jersey; su CEO ha confirmado conversaciones para vender energía nuclear de Hope Creek y Salem a operadores de IA citando el modelo Talen-Amazon, tras la expiración en 2025 de certificados \"zero-emission\" que ataban esa energía al mercado minorista estatal."
 },
 "AEP": {
  "founded": 1906,
  "employees": 16330,
  "revenue_2025": "~$20B",
  "geo_risk": "Litigios activos sobre tarifas especiales para datacenters y aprobaciones regulatorias en 11 jurisdicciones estatales distintas.",
  "desc": "Mayor operador de transmisión de EEUU, con un acuerdo pionero de \"Clean Capacity Arrangement\" con Google (jul 2025) donde el hyperscaler cede derechos de capacidad limpia a cambio de suministro firme y respuesta a demanda en su datacenter de Fort Wayne ($2B), mientras litiga con Amazon, Google, Meta y Microsoft sobre tarifas especiales para grandes cargas."
 },
 "DominionEnergy": {
  "founded": 1983,
  "employees": 16900,
  "revenue_2025": "~$16.5B",
  "geo_risk": "Saturación de interconexión en el corredor de Data Center Alley (Virginia) y riesgo de permisos NRC para SMRs.",
  "desc": "Con más del 70% de todo el tráfico global de internet pasando por su territorio de servicio en Virginia, Dominion es la utility con mayor exposición directa a la demanda de datacenters de IA en el mundo, y firmó en octubre de 2024 un acuerdo con Amazon para explorar reactores modulares pequeños cerca de la planta North Anna."
 },
 "DukeEnergy": {
  "founded": 1904,
  "employees": 27600,
  "revenue_2025": "~$31.8B",
  "geo_risk": "Aprobaciones regulatorias estatales múltiples y riesgo de ejecución del mayor plan de inversión de su historia.",
  "desc": "Con la mayor flota nuclear regulada de EEUU, Duke Energy anunció en abril de 2026 un plan de capex récord de $103.000 millones, impulsado en gran parte por ~14 GW de nueva demanda vinculada a datacenters de IA en sus territorios de las Carolinas, Indiana y Florida."
 },
 "SouthernCompany": {
  "founded": 1945,
  "employees": 28000,
  "revenue_2025": "~$27B",
  "geo_risk": "Riesgo de sobrecostos regulatorios recurrentes (histórico en Vogtle) y presión tarifaria por crecimiento de demanda industrial.",
  "desc": "Southern Company completó en 2023-2024 los primeros reactores nucleares nuevos construidos en EEUU en una generación (Vogtle 3 y 4, AP1000), y ahora ve sus ventas eléctricas industriales dispararse 42% interanual por la demanda de datacenters de IA en Georgia, respaldada por un préstamo del DOE de $26.5B."
 },
 "PPLCorp": {
  "founded": 1920,
  "employees": 7000,
  "revenue_2025": "~$8.6B",
  "geo_risk": "Congestión de interconexión en PJM y dependencia de aprobaciones regulatorias de Pensilvania.",
  "desc": "Ex-matriz de Talen Energy, PPL formó en julio de 2025 una joint venture con Blackstone para desarrollar hasta 6.75 GW de generación a gas natural en Pensilvania destinada explícitamente a datacenters de IA, dentro de un pipeline total de 28.3 GW de solicitudes de gran carga."
 },
 "RollsRoyceSMR": {
  "founded": 2021,
  "employees": 1200,
  "revenue_2025": "N/D (financiamiento gubernamental UK ~£490M + contratos recientes)",
  "geo_risk": "Dependencia de subsidios y aprobaciones regulatorias del Reino Unido y la UE; competencia directa de proveedores estadounidenses respaldados por hyperscalers.",
  "desc": "Spin-off de Rolls-Royce Holdings dedicado a SMRs, seleccionado por el gobierno británico como su diseño SMR preferente y con acuerdo reciente con la checa ČEZ (abr 2026); a diferencia de competidores como X-energy o Kairos Power, aún no ha anunciado un contrato directo con un hyperscaler de IA."
 },
 "GEHitachiNuclear": {
  "founded": 2007,
  "employees": 3000,
  "revenue_2025": "N/D (no desglosado de GE Vernova)",
  "geo_risk": "Riesgo de ejecución \"primero de su tipo\" (ningún BWRX-300 aún operativo) y competencia de Rosatom en mercados emergentes.",
  "desc": "Joint venture GE Vernova/Hitachi que desarrolla el BWRX-300, el SMR con más pedidos en construcción del mundo (Ontario Power Generation, TVA), y que en 2025 firmó su primer acuerdo \"early works\" directamente ligado a IA con Google y Elementl Power en Ohio, por hasta 1.5 GW."
 },
 "WestinghouseElectric": {
  "founded": 1999,
  "employees": 13000,
  "revenue_2025": "~$5B (est.) · valuación referencia $7.9B (adquisición 2023)",
  "geo_risk": "Dependencia de aprobaciones NRC/DOE y de financiamiento gubernamental; reemplaza suministro nuclear ruso en Europa del Este.",
  "desc": "Propiedad de Brookfield y Cameco desde 2023, Westinghouse relanzó su reactor AP1000 como pieza central de la estrategia nuclear de EEUU, incluyendo un acuerdo de $80.000 millones con el gobierno (oct 2025) y un contrato para 4 AP1000 en el campus \"HyperGrid AI\" de Fermi America en Amarillo, Texas (hasta 11 GW)."
 },
 "Kazatomprom": {
  "founded": 1997,
  "employees": 20000,
  "revenue_2025": "~$2.8B",
  "geo_risk": "Dependencia crítica de la ruta de exportación vía San Petersburgo (Rusia) y de servicios de conversión ligados a Rosatom, bajo riesgo creciente de sanciones.",
  "desc": "Estatal kazajo (75% Samruk-Kazyna) que domina el mercado global de uranio; recortó su guía de producción 2026 en 10% priorizando \"valor sobre volumen\" mientras firma nuevos contratos con India (+$4.000M, feb 2026), China, Japón y República Checa para diversificar clientes ante el déficit global agravado por la demanda eléctrica de datacenters de IA."
 },
 "NexGenEnergy": {
  "founded": 2011,
  "employees": 142,
  "revenue_2025": "Pérdida neta ~CAD 309.7M · market cap ~$6.26B",
  "geo_risk": "Bajo riesgo geopolítico (Canadá), contraste favorable frente a productores en Kazajistán/Níger.",
  "desc": "Tras obtener en marzo de 2026 el último permiso regulatorio pendiente (CNSC), NexGen inicia la construcción de Rook I, el mayor depósito de uranio de alta ley no desarrollado del mundo; ha mantenido conversaciones exploratorias con \"proveedores de datacenters\" de IA para financiar directamente la construcción, en línea con la narrativa de \"big tech busca uranio\"."
 },
 "DenisonMines": {
  "founded": 1960,
  "employees": 68,
  "revenue_2025": "~$4.9M",
  "geo_risk": "Bajo riesgo geopolítico (Saskatchewan, Canadá), aunque expuesto a riesgo climático (inundaciones).",
  "desc": "Primer gran proyecto de uranio canadiense aprobado para construcción en más de 20 años; tras el FID de febrero de 2026 (capex ~$600M), Denison tiene ya comprometidas ~16M lb de venta de U3O8 (mitad en firme con utilities norteamericanas) para cuando inicie producción en 2028."
 },
 "PaladinEnergy": {
  "founded": 1993,
  "employees": 500,
  "revenue_2025": "~$270M (anualizado sobre H1 FY2025)",
  "geo_risk": "Dependencia de Namibia (cuotas de propiedad local, Tratado de Pelindaba) y fuerte presencia de mineras estatales chinas en el sector namibio.",
  "desc": "Operador de Langer Heinrich, una de las mayores minas de uranio de Namibia, que diversificó recientemente vía la adquisición de Fission Uranium en Canadá; su acción ha sido una de las más beneficiadas del \"supercycle\" de uranio atribuido en parte a la demanda energética de datacenters de IA."
 },
 "UrEnergy": {
  "founded": 2004,
  "employees": 157,
  "revenue_2025": "~$27.2M",
  "geo_risk": "Bajo (100% EEUU), con exposición a riesgo regulatorio ambiental (EPA/permisos estatales).",
  "desc": "Con Lost Creek en producción desde 2013 y Shirley Basin arrancando en 2026, Ur-Energy es uno de los pocos productores de uranio 100% estadounidenses, un activo estratégico en un contexto de políticas de EEUU orientadas a reducir dependencia de uranio ruso/kazajo para su flota nuclear (incluida la que alimenta datacenters de IA)."
 },
 "GlobalAtomic": {
  "founded": 2004,
  "employees": 700,
  "revenue_2025": "Pre-producción (inversión total ~$250M)",
  "geo_risk": "Riesgo severo de nacionalización en Níger — el gobierno ya nacionalizó en 2025 la mina Somaïr de su competidor Orano y la eléctrica Nigelec, aunque Global Atomic reporta apoyo gubernamental continuo y un nuevo código minero (2027) que reduce regalías del 12% al 7%.",
  "desc": "Desarrolladora del proyecto Dasa, uno de los depósitos de uranio de mayor ley de África, con 90% de su producción inicial ya contratada con utilities de EEUU; opera bajo el riesgo geopolítico más alto de este lote tras el golpe de estado nigerino de 2023 y la nacionalización en 2025 de activos de su competidor francés Orano en el mismo país."
 },
 "BossEnergy": {
  "founded": 2005,
  "employees": 125,
  "revenue_2025": "~AUD $75.6M (~$50M)",
  "geo_risk": "Bajo (Australia y EEUU, jurisdicciones estables); riesgo principal es de costos operativos, no geopolítico.",
  "desc": "Operador de la mina ISR Honeymoon en Australia y del 30% de Alta Mesa en Texas, con balance sin deuda y caja de AUD $224M; sus inversionistas citan explícitamente la demanda de datacenters de IA como factor material en la planificación de nueva capacidad nuclear."
 },
 "GeneralFusion": {
  "founded": 2002,
  "employees": 100,
  "revenue_2025": "N/D (~$366-400M levantados históricamente; hasta $335M vía SPAC 2026)",
  "geo_risk": "Dependencia de subvenciones gubernamentales canadienses y mercados de capital volátiles para financiar I+D de fusión.",
  "desc": "Pionera canadiense de fusión por confinamiento magnetizado, respaldada por Jeff Bezos y Temasek entre otros, que recortó plantilla 25% en 2025 por presión de caja antes de asegurar financiamiento vía SPAC; a diferencia de Helion Energy (que ya tiene PPA con Microsoft), aún no ha firmado un contrato de suministro con un hyperscaler de IA."
 },
 "ZapEnergy": {
  "founded": 2017,
  "employees": 150,
  "revenue_2025": "N/D (Serie D $130M oct 2024, ~$330M total levantado)",
  "geo_risk": "Bajo geopolíticamente (EEUU), pero alto riesgo de ejecución técnica y regulatoria por el pivote a fisión.",
  "desc": "Startup de fusión por Z-pinch respaldada por Chevron Technology Ventures, Lowercarbon Capital y Breakthrough Energy Ventures (Bill Gates), que en abril de 2026 anunció un pivote parcial hacia un SMR de fisión basado en el diseño 4S de Toshiba, citando explícitamente la escasez de energía para datacenters de IA como motivo estratégico."
 },
 "CentrusEnergy": {
  "founded": 1998,
  "employees": 1100,
  "revenue_2025": "~$350M",
  "geo_risk": "Cuello de botella crítico de la cadena de suministro nuclear occidental: hasta 2028 EEUU depende parcialmente de Rusia (Rosatom/TENEX) para HALEU comercial, bajo sanciones y restricciones crecientes.",
  "desc": "Sucesora de USEC, Centrus opera la única cascada de enriquecimiento de HALEU con licencia comercial en EEUU (planta de Piketon, Ohio), posicionándose como el eslabón crítico —y hoy escaso— de la cadena de suministro para todos los reactores avanzados que buscan alimentar datacenters de IA con energía libre de carbono."
 },
 "Orano": {
  "founded": 2018,
  "employees": 17000,
  "revenue_2025": "~€4.6B",
  "geo_risk": "Nacionalización en junio de 2025 de su joint venture Somaïr y de la eléctrica Nigelec en Níger, dejando su filial \"al borde de la bancarrota\" según reportes; alto riesgo de repetición en otras jurisdicciones africanas.",
  "desc": "Spin-off en 2018 de la antigua Areva, Orano concentra la mayor parte de la capacidad occidental de conversión y enriquecimiento de uranio fuera de EEUU, un eslabón crítico para reducir la dependencia europea de servicios rusos justo cuando la demanda de combustible nuclear se dispara por la expansión de reactores para datacenters de IA; sufrió en 2025 la pérdida de control de su histórica mina en Níger."
 },
 "china-northern-rare-earth": {
  "founded": 1997,
  "employees": 20000,
  "revenue_2025": "RMB 42.560M (~USD 5.900M)",
  "geo_risk": "Instrumento central de los controles de exportación chinos (abril y octubre 2025); tregua Trump-Xi frágil con enforcement renovado en 2026.",
  "desc": "Filial cotizada del grupo estatal Baotou Iron and Steel, procesa el mayor depósito de tierras raras del planeta. Es el actor cuyo comportamiento de exportación mueve los mercados globales de imanes permanentes y motiva las inversiones occidentales alternativas (Lynas, MP Materials, Iluka, Arafura)."
 },
 "iluka-resources": {
  "founded": 1998,
  "employees": 1000,
  "revenue_2025": "~A$700-800M (negocio de mineral de arenas pesadas; tierras raras aún sin ingresos)",
  "geo_risk": "Pieza clave de la estrategia Australia-EEUU para diversificar fuera de la dependencia china de tierras raras.",
  "desc": "Productor histórico de circonio y titanio que pivota hacia tierras raras magnéticas con apoyo estatal directo, posicionándose como alternativa occidental de suministro crítico."
 },
 "ucore-rare-metals": {
  "founded": 2007,
  "employees": 170,
  "revenue_2025": "pre-ingresos; market cap ~CAD 660M",
  "geo_risk": "Apoyo directo del gobierno de EEUU (DoD) para romper la dependencia de refinación china de tierras raras.",
  "desc": "Startup canadiense-estadounidense que apuesta por una tecnología de separación más ágil que la extracción por solventes convencional, con el respaldo del Pentágono como ancla de demanda."
 },
 "arafura-resources": {
  "founded": 1998,
  "employees": 100,
  "revenue_2025": "pre-ingresos",
  "geo_risk": "Proyecto insignia de la estrategia occidental para reducir dependencia de tierras raras chinas, con financiamiento de Export Finance Australia y marco Australia-EEUU.",
  "desc": "Uno de los proyectos de tierras raras más avanzados fuera de China, con vida de mina de 38 años y compromiso de compra estatal que reduce el riesgo comercial de arranque."
 },
 "vital-metals": {
  "founded": 2003,
  "employees": 50,
  "revenue_2025": "A$854.551 en ventas de mineral (FY2025)",
  "geo_risk": "Ejemplo cautelar de cómo la falta de financiamiento occidental deja huecos que la oferta china puede seguir explotando.",
  "desc": "Caso de estudio de los riesgos de ejecución en la cadena de suministro occidental de tierras raras: proyecto con recursos geológicos reales pero fracaso financiero y operativo reiterado."
 },
 "air-products": {
  "founded": 1940,
  "employees": 21300,
  "revenue_2025": "USD 12.000M",
  "geo_risk": "Expansión concentrada en Taiwán/Corea/China la expone a tensiones de la cadena de suministro de semiconductores.",
  "desc": "Uno de los mayores proveedores mundiales de gases industriales, con modelo de plantas dedicadas junto a fabs; recientemente reorientó capital fuera del hidrógeno hacia semiconductores."
 },
 "resonac-holdings": {
  "founded": 1939,
  "employees": 21525,
  "revenue_2025": "~USD 8.900M",
  "geo_risk": "Dependencia de materias primas chinas para grafito/ánodos; cerró plantas en China y Malasia en 2025 por presión de márgenes.",
  "desc": "Uno de los mayores beneficiarios japoneses del boom de HBM/IA gracias a su dominio en films no conductores de empaquetado, recibió el \"TSMC Excellent Performance Award\" en 2025."
 },
 "kanto-denka-kogyo": {
  "founded": 1938,
  "employees": 802,
  "revenue_2025": "~USD 400M (proyección anualizada)",
  "geo_risk": "Dependencia crítica de tungsteno chino (>60% del costo del WF6) y concentración geográfica de producción en Japón; competidores como Mitsui Chemicals ya cesaron producción de NF3 por la crisis.",
  "desc": "Nodo de riesgo de cadena de suministro extremadamente concentrado: Rapidus depende exclusivamente de esta empresa para NF3, y el incendio de 2025 más la crisis de tungsteno chino ilustran la fragilidad de los insumos críticos de litografía."
 },
 "nitto-denko": {
  "founded": 1918,
  "employees": 28006,
  "revenue_2025": "~USD 6.900M",
  "geo_risk": "Extensa huella manufacturera en China (~16 plantas/filiales) y nueva planta en Taiwán (Kaohsiung, 2026) expuesta a tensiones regionales.",
  "desc": "Proveedor de materiales de \"nicho global top\" cuya cinta de dicing y films de back-grinding son insumos críticos poco visibles pero esenciales en el proceso de fabricación de obleas."
 },
 "sumitomo-chemical": {
  "founded": 1913,
  "employees": 29279,
  "revenue_2025": "~USD 15.500M",
  "geo_risk": "No figura en las listas de restricción Japón-China de 2025-2026, pero su nueva planta en Taiwán la expone a tensiones regionales.",
  "desc": "Conglomerado histórico japonés que reestructuró su cartera (salida de petroquímicos) para enfocarse en materiales de alto valor como fotorresistentes de última generación para EUV."
 },
 "mitsubishi-gas-chemical": {
  "founded": 1918,
  "employees": 8319,
  "revenue_2025": "~USD 4.900M",
  "geo_risk": "Tensión Japón-China (nov-dic 2025) generó controles chinos sobre ~40 empresas japonesas; expansión en EEUU busca diversificar geografía.",
  "desc": "Proveedor crítico y poco visible del insumo de limpieza más usado en fabricación de obleas, con dificultades recientes de certificación en Taiwán que sugieren fricción con fabricantes líderes."
 },
 "adeka-corporation": {
  "founded": 1917,
  "employees": 5453,
  "revenue_2025": "~USD 2.800M",
  "geo_risk": "Expansión en Corea (Hwaseong x7), Taiwán y costa oeste de EEUU busca diversificar fuera de la dependencia japonesa-china.",
  "desc": "Proveedor especializado de precursores de deposición atómica cuya rentabilidad se ve presionada por costos de certificación y competencia, pese a fuerte demanda estructural de IA."
 },
 "tosoh-corporation": {
  "founded": 1935,
  "employees": 14813,
  "revenue_2025": "~USD 6.800M",
  "geo_risk": "Retiró su guía FY2027 por incertidumbre de Medio Oriente en costos de nafta; competencia de Materion, Honeywell y JX Advanced Metals.",
  "desc": "Conglomerado químico diversificado cuya filial estadounidense Tosoh SMD es un proveedor clave y poco visible de targets de sputtering, insumo esencial en deposición de películas metálicas."
 },
 "fujimi-incorporated": {
  "founded": 1950,
  "employees": 830,
  "revenue_2025": "~USD 450M (anualizado)",
  "geo_risk": "Competencia directa de Entegris/CMC Materials; expuesta al ciclo global de capex de semiconductores.",
  "desc": "Pionero japonés de slurries CMP desde 1967 (serie GLANZOX), con colaboración histórica de desarrollo conjunto con Cabot Microelectronics (hoy parte de Entegris)."
 },
 "kyocera-corporation": {
  "founded": 1959,
  "employees": 80000,
  "revenue_2025": "~USD 13.400M",
  "geo_risk": "Expansión en Hendersonville, NC (EEUU) sugiere diversificación geográfica ante riesgo arancelario/geopolítico.",
  "desc": "Conglomerado industrial japonés cuyo segmento de componentes de semiconductores atraviesa pérdidas por la caída de demanda de FCBGA para centros de datos, aunque lanza nuevos sustratos multicapa orientados a IA."
 },
 "tokamak-energy": {
  "founded": 2009,
  "employees": 350,
  "revenue_2025": "no cotiza; financiación no revelada públicamente",
  "geo_risk": "Colaboración gubernamental UK-EEUU (LEAPS) refleja la competencia occidental en fusión frente a los programas estatales chinos.",
  "desc": "Pionero británico en tokamaks esféricos, con spin-off comercial (TE Magnetics) que vende su tecnología de imanes HTS fuera del sector de fusión, diversificando ingresos mientras persigue energía comercial."
 },
 "type-one-energy": {
  "founded": 2019,
  "employees": 190,
  "revenue_2025": "financiación acumulada >USD 160M (sin Serie B); valuación pre-money de Serie B ~USD 900M",
  "geo_risk": "Proyecto financiado por capital privado de EEUU, alineado con independencia energética; sin exposición directa a cadenas chinas.",
  "desc": "Spin-off de investigación stellarator de la Universidad de Wisconsin-Madison, hoy con sede en Tennessee y respaldo de inversores destacados como Bill Gates (vía Breakthrough Energy Ventures) y John Arnold."
 },
 "pacific-fusion": {
  "founded": 2024,
  "revenue_2025": "sin ingresos; financiación comprometida >USD 1.000M",
  "geo_risk": "Proyecto estadounidense sin exposición directa a cadenas chinas; compite por talento y capital con Commonwealth Fusion Systems y TAE Technologies.",
  "desc": "Startup de fusión inercial impulsada eléctricamente (inspirada en el Z Machine de Sandia y el NIF de LLNL), con un consejo de inversores de alto perfil (Eric Schmidt, Reid Hoffman, Ken Griffin) y objetivo declarado de electricidad comercial hacia 2040."
 },
 "nissan-chemical": {
  "founded": 1887,
  "employees": 2800,
  "revenue_2025": "~USD 1.900M",
  "geo_risk": "La empresa cita riesgo de abastecimiento de materia prima específica y desastres naturales en Japón, sin mencionar explícitamente riesgo geopolítico EEUU-China.",
  "desc": "Proveedor especializado de recubrimientos antirreflectantes que capitaliza plenamente el boom de litografía EUV, con crecimiento porcentual de doble dígito alto en sus segmentos ligados a semiconductores avanzados."
 },
 "chang-chun-group": {
  "founded": 1949,
  "employees": 20000,
  "revenue_2025": ">USD 10.000M (grupo, estimado)",
  "geo_risk": "Cubre un hueco crítico: la cadena de suministro química de TSMC depende en gran parte de proveedores domésticos taiwaneses como Chang Chun, vulnerables a un conflicto en el estrecho de Taiwán.",
  "desc": "Gigante químico familiar taiwanés poco conocido fuera de la industria, pero esencial: fabrica buena parte de los fotorresistentes y materiales electrónicos que sostienen la industria de semiconductores de la isla."
 },
 "stella-chemifa": {
  "founded": 1916,
  "employees": 700,
  "revenue_2025": "~USD 300-400M (estimado)",
  "geo_risk": "Es el ejemplo histórico de referencia de cómo un insumo químico aparentemente menor (HF) puede convertirse en arma geopolítica: Japón restringió sus exportaciones a Corea del Sur en 2019, afectando directamente a Samsung y SK Hynix.",
  "desc": "Proveedor poco visible pero estratégicamente central: el ácido fluorhídrico de alta pureza que fabrica es indispensable para el grabado de obleas, y su restricción de exportación en 2019 demostró la fragilidad de la cadena de suministro de semiconductores ante decisiones políticas bilaterales."
 },
 "brewer-science": {
  "founded": 1981,
  "employees": 700,
  "revenue_2025": "no cotiza (estimado cientos de millones USD)",
  "geo_risk": "Cubre un hueco relevante: casi todos los proveedores de materiales de litografía del grafo son japoneses; Brewer Science es de las pocas alternativas estadounidenses, relevante para la política de \"onshoring\" de materiales críticos de EEUU.",
  "desc": "Proveedor estadounidense de nicho en materiales de litografía que licencia su tecnología central a fabricantes japoneses como Nissan Chemical, ilustrando la interdependencia tecnológica bidireccional EEUU-Japón en la cadena de suministro de semiconductores."
 },
 "jcet": {
  "founded": 1972,
  "employees": 22000,
  "revenue_2025": "~$5.4B (RMB 38.7B TTM)",
  "geo_risk": "Objetivo directo de controles de exportación de EE.UU. por ser el \"campeón nacional\" OSAT de China.",
  "desc": "JCET es el mayor OSAT de China continental, construido sobre la adquisición en 2015 de la singapurense STATS ChipPAC. Ofrece desde ensamblaje básico hasta empaquetado chiplet 2.5D/3D avanzado para clientes de IA/HPC, posicionándose como el contrapeso chino a ASE (Taiwán) y Amkor (EE.UU.)."
 },
 "pti": {
  "founded": 1997,
  "employees": 15000,
  "revenue_2025": "~$2.4-2.6B (NT$75-80B est.)",
  "geo_risk": "Sede en Taiwán, expuesta a tensión del Estrecho de Taiwán y a shocks arancelarios de EE.UU.",
  "desc": "PTI es el mayor OSAT independiente de memoria de Taiwán, empaquetando y testeando DRAM/NAND para los principales fabricantes IDM del mundo. Su desempeño sigue de cerca el ciclo de memoria y se ha beneficiado del auge de HBM impulsado por IA."
 },
 "kyec": {
  "founded": 1987,
  "employees": 8000,
  "revenue_2025": "~$1.2B (NT$37.8B TTM)",
  "geo_risk": "Riesgo del Estrecho de Taiwán y dependencia del ciclo de chips IA ligado a demanda de EE.UU.",
  "desc": "KYEC es el principal proveedor independiente de test de chips de Taiwán, tradicionalmente enfocado en test final y sondeo de oblea para ICs lógicos y de señal mixta. El auge de IA lo ha llevado a una expansión agresiva, incluida su primera planta fuera de Taiwán (Singapur)."
 },
 "chipbond": {
  "founded": 1997,
  "employees": 3757,
  "revenue_2025": "~$680M (NT$21.45B)",
  "geo_risk": "Sede en Taiwán, menor exposición directa a controles de exportación que OSATs lógicos, pero expuesta al riesgo geopolítico del Estrecho.",
  "desc": "Chipbond es el proveedor dominante a nivel global de bumping y empaquetado COF/COG para drivers de pantalla, un eslabón clave pero poco visible entre diseñadores DDIC y fabricantes de paneles. Se ha diversificado hacia empaquetado de semiconductores de compuesto (GaN/SiC) para capturar demanda automotriz y de electrónica de potencia."
 },
 "biren": {
  "founded": 2019,
  "revenue_2025": "valoración ~$6B (HK$46.9B market cap en IPO)",
  "geo_risk": "Añadida a la Entity List de EE.UU. en 2023, cortada del acceso a TSMC, dependiente de fundición doméstica menos avanzada.",
  "desc": "Biren es el startup de GPU IA más prominente de China, fundado en 2019 para construir alternativas domésticas a las GPUs de centro de datos de Nvidia. Los controles de exportación de EE.UU. la cortaron de TSMC, forzándola a fundiciones domésticas menos avanzadas, pero su IPO en Hong Kong (enero 2026) atrajo fuerte demanda como apuesta por la autosuficiencia china en chips IA."
 },
 "moorethreads": {
  "founded": 2020,
  "revenue_2025": "IPO recaudó ~$1.1B (¥8B); ingresos aún pequeños escalando rápido",
  "geo_risk": "En la Entity List de EE.UU.; depende de fundiciones y herramientas no estadounidenses.",
  "desc": "Fundada en 2020 por exejecutivos de Nvidia China, Moore Threads se convirtió en el símbolo del impulso chino hacia la autosuficiencia en GPU, debutando en el STAR Market de Shanghái en 2026 con un salto bursátil de ~468%. Liang Wenfeng, fundador de DeepSeek, fue inversor institucional temprano."
 },
 "unisoc": {
  "founded": 2001,
  "employees": 5000,
  "revenue_2025": "valoración ~$9.1B (ronda 2024)",
  "geo_risk": "Matriz Tsinghua Unigroup reestructurada por quiebra estatal; enfoque en nodos maduros reduce exposición a controles de exportación avanzados.",
  "desc": "UNISOC sobrevive enfocándose en nodos de proceso maduros no alcanzados por los controles de exportación más estrictos, dándole resiliencia pese a la presión de sanciones sobre firmas chinas de chips. Es mayoritariamente propiedad de un reestructurado Tsinghua Unigroup y prepara una posible salida a bolsa."
 },
 "starfive": {
  "founded": 2018,
  "revenue_2025": "no revelado; inversión estratégica de Hong Kong Investment Corporation (marzo 2025)",
  "geo_risk": "RISC-V favorecido por Beijing como alternativa resistente a sanciones frente a Arm/x86.",
  "desc": "StarFive es central en la estrategia china de adoptar RISC-V como arquitectura abierta y libre de licencias para reducir la dependencia de IP occidental. Ha evolucionado de placas de desarrollo (VisionFive) hacia silicio de clase datacenter."
 },
 "loongson": {
  "founded": 2010,
  "employees": 977,
  "revenue_2025": "¥635.3M (~$88M); market cap ~¥54.5B (~$7.6B)",
  "geo_risk": "Jugada de autosuficiencia \"a prueba de sanciones\" (ISA propio), pero depende de listas de adquisición estatal \"seguras y controlables\".",
  "desc": "Loongson es el fabricante insignia chino de CPUs con ISA indígena, originado en un instituto de investigación estatal y aún mayoritariamente vinculado al Estado. Pese al fuerte crecimiento de ingresos, sigue profundamente en pérdidas, sostenido por una colocación privada reciente y demanda continua del gobierno."
 },
 "enflame": {
  "founded": 2018,
  "revenue_2025": "~¥990M (~$137M); objetivo de IPO ¥6B (~$827M)",
  "geo_risk": "Probable futura exposición a controles de exportación de EE.UU. como sus pares (Biren, Moore Threads).",
  "desc": "Enflame es el último de los \"cuatro dragones\" chinos de chips IA en buscar una salida a bolsa en el STAR Market, con fuerte crecimiento de ingresos pero pérdidas considerables y dependencia casi total de un cliente/inversor ancla. Los fondos de la IPO se destinarán mayormente a I+D de próximas generaciones de chips."
 },
 "nexperia": {
  "founded": 2017,
  "employees": 15000,
  "revenue_2025": "~€2.0-2.2B (estimado)",
  "geo_risk": "Epicentro directo de la guerra de chips EE.UU.-China-Países Bajos; control operativo tomado por el gobierno holandés y exportaciones bloqueadas por China.",
  "desc": "Nexperia es una fabricante de semiconductores discretos con sede en Países Bajos pero propiedad china (Wingtech), escindida de NXP en 2017. En octubre de 2025 el gobierno holandés invocó poderes de emergencia para tomar control de la empresa por razones de seguridad nacional, lo que provocó que China bloqueara la exportación de sus chips terminados, disruptando cadenas de suministro automotrices globales."
 },
 "vishay": {
  "founded": 1962,
  "employees": 22000,
  "revenue_2025": "~$3.0-3.2B (estimado)",
  "geo_risk": "Exposición a cambios arancelarios/manufactura en China y tensiones comerciales de semiconductores.",
  "desc": "Vishay es uno de los mayores fabricantes mundiales de semiconductores discretos y componentes pasivos, sirviendo a OEMs automotrices, industriales y de computación. Ha enfrentado una desaceleración cíclica de demanda a lo largo de 2025, reflejada en resultados trimestrales débiles."
 },
 "juniper": {
  "founded": 1996,
  "employees": 10000,
  "revenue_2025": "~$5.0-5.6B (últimas cifras standalone)",
  "geo_risk": "Equipos de networking bajo creciente escrutinio comercial/seguridad EE.UU.-China; la fusión con HPE enfrentó revisión antimonopolio del DOJ.",
  "desc": "Juniper Networks fue un vendedor independiente clave de networking, conocido por routers de proveedores de servicio y networking de campus/wireless con IA (Mist). HPE completó su adquisición de $14B en julio de 2025 tras una larga revisión antimonopolio del DOJ, combinando el networking nativo en IA de Juniper con el portafolio de cómputo/datacenter de HPE."
 },
 "f5": {
  "founded": 1996,
  "employees": 6500,
  "revenue_2025": "$3.1B (confirmado FY2025)",
  "geo_risk": "Exposición moderada; software de seguridad empresarial bajo escrutinio de control de exportación en ciertos países.",
  "desc": "F5 es una compañía con sede en Seattle de entrega y seguridad de aplicaciones cuyos productos BIG-IP y de nube distribuida están en el centro de la gestión de tráfico de aplicaciones en empresas y datacenters cloud. Sus ingresos FY2025 alcanzaron $3.1B (+10% YoY), reflejando demanda ligada al crecimiento de tráfico de aplicaciones impulsado por IA."
 },
 "americantower": {
  "founded": 1995,
  "employees": 5000,
  "revenue_2025": "~$10.5-11B (estimado)",
  "geo_risk": "Operaciones internacionales (India, África, Latam) con riesgo cambiario/regulatorio; unidad CoreSite la vincula al boom de IA/nube.",
  "desc": "American Tower es uno de los mayores REITs globales, propietario de torres y datacenters arrendados a operadoras inalámbricas y clientes cloud/interconexión. Su unidad de datacenter CoreSite la vincula cada vez más a la demanda de colocation e interconexión impulsada por IA."
 },
 "crowncastle": {
  "founded": 1994,
  "employees": 4000,
  "revenue_2025": "no reportado de forma consolidada limpia (negocio de fibra discontinuado); >40,000 torres",
  "geo_risk": "Bajo riesgo geopolítico directo (activos domésticos EE.UU.), pero expuesta a ciclos de capex de operadoras y sensibilidad a tasas de interés.",
  "desc": "Crown Castle posee y opera el mayor portafolio independiente de infraestructura inalámbrica compartida de EE.UU., arrendando espacio de torre a las principales operadoras bajo contratos de largo plazo. En 2025-2026 atraviesa un giro estratégico mayor —desinvirtiendo su negocio de fibra y small cells para convertirse en un REIT puro de torres— tras sostenida presión de inversionistas activistas."
 },
 "gds": {
  "founded": 2001,
  "employees": 2434,
  "revenue_2025": "RMB 11,432.3M (~$1,634.8M), +10.8% YoY",
  "geo_risk": "Alto — tensiones tecnológicas EE.UU.-China, controles de exportación de GPU/chips afectando la demanda de datacenters IA, riesgo de deslistado ADR/VIE.",
  "desc": "GDS es el mayor operador independiente de datacenters de China, construyendo y operando instalaciones hyperscale para gigantes domésticos de nube e internet. Aprovecha la expansión de infraestructura de IA de China (668,283 m² en servicio, 75.5% de utilización), pero conlleva riesgo geopolítico y de apalancamiento significativo por su estructura de empresa china cotizada en EE.UU."
 },
 "adva": {
  "founded": 1994,
  "employees": 2000,
  "revenue_2025": "matriz Adtran Holdings consolidada $1,083.8M",
  "geo_risk": "Beneficiada por la política de \"red limpia\" de la UE frente a proveedores chinos, pero expuesta a la volatilidad de capex telco europeo.",
  "desc": "Adtran Networks (la antigua ADVA) es una fabricante alemana de equipos de networking óptico/acceso, ahora mayoritariamente propiedad de la estadounidense Adtran Holdings. Se beneficia de las políticas europeas de \"proveedor de confianza\" que desplazan a los proveedores chinos, y 2025 mostró un retorno al crecimiento tras un 2024 con pérdidas."
 },
 "fabrinet": {
  "founded": 2000,
  "employees": 20000,
  "revenue_2025": "$3.42B (FY2025, terminado en junio 2025)",
  "geo_risk": "Base de manufactura en Tailandia ofrece cobertura ante fricción arancelaria EE.UU.-China, pero expuesta a política arancelaria de EE.UU. sobre importaciones del sudeste asiático.",
  "desc": "Fabrinet es el mayor fabricante subcontratado de componentes ópticos y transceptores de alta precisión del mundo, con base en Tailandia, sirviendo a OEMs de networking, datacom e industrial. Se ha convertido en beneficiario directo del boom de IA/datacenter, ya que hyperscalers y vendedores de networking necesitan transceptores ópticos 800G/1.6T a escala."
 },
 "colt": {
  "founded": 1992,
  "employees": 6000,
  "revenue_2025": "~€2.2B+ (2024 confirmado, 2025 no confirmado)",
  "geo_risk": "Moderado —exposición de cable submarino paneuropeo a riesgo físico/geopolítico (rutas del Báltico), estructura de propiedad privada limita transparencia.",
  "desc": "Colt es un operador privado (propiedad de Fidelity Investments desde 2015) de redes empresariales que provee conectividad de fibra e infraestructura de baja latencia en Europa, América y Asia. Su adquisición en 2022 del negocio EMEA de Lumen expandió significativamente su huella, y mantiene un fuerte nicho en conectividad de servicios financieros vía MarketPrizm."
 },
 "wingtech": {
  "founded": 2006,
  "employees": 30000,
  "revenue_2025": "no confirmado (~$8-9B est. incluyendo Nexperia)",
  "geo_risk": "Añadida a la Entity List de EE.UU.; en el centro de la disputa Países Bajos-China por el control de Nexperia.",
  "desc": "Wingtech es un conglomerado chino de manufactura electrónica (ODM) que se convirtió en el foco de la crisis de chips de 2025 al ser la matriz de Nexperia, cuando el gobierno holandés tomó control operativo de esta última por razones de seguridad nacional. La disputa resultante disruptó cadenas de suministro automotrices globales."
 },
 "sba": {
  "founded": 1989,
  "employees": 1500,
  "revenue_2025": "~$2.7B (estimado)",
  "geo_risk": "Exposición cambiaria/regulatoria en mercados latinoamericanos.",
  "desc": "SBA Communications completa el trío de grandes REITs de torres inalámbricas de EE.UU. junto a American Tower y Crown Castle, con un portafolio con fuerte presencia en EE.UU. y Latinoamérica que se beneficia del despliegue continuo de redes 5G y densificación de operadoras."
 },
 "chindata": {
  "founded": 2015,
  "employees": 1500,
  "revenue_2025": "~$800M-1B estimado (última cifra pública ~$500M antes de deslistado)",
  "geo_risk": "Alta exposición a controles de exportación de semiconductores EE.UU.-China y riesgo regulatorio de datos transfronterizos.",
  "desc": "Chindata construyó la mayor red de datacenters hyperscale de China, con clientes ancla como Bytedance y Alibaba. Bain Capital la adquirió y deslistó en 2023, fusionándola después con Bridge Data Centres para crear una plataforma de datacenters pan-asiática valorada en más de $4.000M."
 },
 "vantage-dc": {
  "founded": 2010,
  "employees": 1200,
  "revenue_2025": "~$1.500M estimado",
  "geo_risk": "Riesgo de restricciones de suministro eléctrico y permisos locales en EE.UU./Europa/APAC ante demanda explosiva de IA.",
  "desc": "Vantage es uno de los mayores desarrolladores privados de datacenters hyperscale del mundo, respaldado por DigitalBridge y Silver Lake con más de $9.000M de capital. Construye campus multi-gigavatio para los principales hyperscalers, incluyendo el proyecto Frontier de $25.000M en Texas."
 },
 "stack-infra": {
  "founded": 2017,
  "employees": 800,
  "revenue_2025": "~$1.000M estimado",
  "geo_risk": "Exposición a mercados APAC (incluyendo posibles restricciones regulatorias en Asia) y dependencia de financiamiento de deuda privada.",
  "desc": "STACK Infrastructure, controlada por Blue Owl Capital tras adquirir IPI Partners por ~$1.000M, opera datacenters hyperscale en tres continentes. Su portafolio asiático está en proceso de venta por más de $30.000M, reflejando la demanda récord de capacidad para IA."
 },
 "crusoe-energy": {
  "founded": 2018,
  "employees": 1200,
  "revenue_2025": "~$1.400M estimado (ARR)",
  "geo_risk": "Dependencia de contratos energéticos de gas natural en EE.UU. y de suministro de GPUs Nvidia sujeto a cuellos de botella de la cadena de suministro.",
  "desc": "Crusoe nació como startup de captura de gas de venteo para minería de Bitcoin y pivotó a construir \"fábricas de IA\" integrando generación de energía propia con datacenters de GPU. Es socio de infraestructura clave del proyecto Stargate de OpenAI en Abilene, Texas, y levanta capital a una valuación de ~$30.000M en 2026."
 },
 "voltage-park": {
  "founded": 2023,
  "employees": 100,
  "revenue_2025": "~$100-150M estimado",
  "geo_risk": "Bajo, opera principalmente en EE.UU.; riesgo de obsolescencia tecnológica frente a GPUs de última generación.",
  "desc": "Voltage Park es una neocloud de GPU lanzada en 2023 con financiamiento filantrópico atípico (Navigation Fund), que compró miles de GPUs Nvidia H100 para ofrecer cómputo bajo demanda. En 2026 se reposicionó bajo la marca Lightning AI."
 },
 "fluidstack": {
  "founded": 2017,
  "employees": 250,
  "revenue_2025": "~$700M-1.000M estimado (ARR)",
  "geo_risk": "Exposición a permisos de construcción y suministro eléctrico en Francia/Europa para el proyecto de 1GW; dependencia de disponibilidad de GPUs Nvidia.",
  "desc": "FluidStack pasó de ser un bróker de GPU a convertirse en un neocloud de gigavatios, firmando un acuerdo histórico de $50.000M con Anthropic para infraestructura dedicada y liderando un supercomputador de IA de 1GW en Francia. Google y Anthropic anclan su ronda de $750M a valuación de $7.000-18.000M en 2026."
 },
 "nscale": {
  "founded": 2024,
  "employees": 300,
  "revenue_2025": "~$400-600M estimado (ARR)",
  "geo_risk": "Dependencia de disponibilidad energética en el Reino Unido/Noruega y de suministro de GPUs Nvidia asignadas bajo cuota.",
  "desc": "Nscale es el neocloud europeo de más rápido crecimiento, construyendo datacenters de GPU en el Reino Unido y los países nórdicos para ofrecer \"IA soberana\" a clientes europeos. Levantó la mayor Serie C europea de la historia ($2.000M) con participación de Nvidia, alcanzando $14.600M de valuación en 2026."
 },
 "tensorwave": {
  "founded": 2023,
  "employees": 150,
  "revenue_2025": "~$150-250M estimado (ARR)",
  "geo_risk": "Bajo geopolíticamente, pero riesgo de concentración en la hoja de ruta de un solo fabricante de chips (AMD).",
  "desc": "TensorWave es el mayor neocloud construido exclusivamente sobre GPUs AMD Instinct, posicionado como alternativa directa a los neoclouds basados en Nvidia. AMD y Magnetar Capital lideraron su Serie B de $350M en 2026, validando la tesis de una cadena de suministro de cómputo de IA no dependiente de Nvidia."
 },
 "northern-data": {
  "founded": 2019,
  "employees": 400,
  "revenue_2025": "~$250-350M estimado",
  "geo_risk": "Historial de inestabilidad financiera y disputas legales con acreedores (incl. Tether); dependencia de asignación de GPUs Nvidia y energía europea.",
  "desc": "Northern Data Group se originó como uno de los mayores mineros de Bitcoin de Europa y pivotó agresivamente hacia infraestructura de IA bajo su marca Taiga Cloud, vendiendo activos de minería para financiar GPUs Nvidia. Ha enfrentado tensiones financieras significativas, incluyendo disputas con su principal acreedor Tether."
 },
 "yotta-data-services": {
  "founded": 2016,
  "employees": 600,
  "revenue_2025": "~$150-250M estimado",
  "geo_risk": "Dependencia de asignación de GPUs Nvidia bajo cuotas de exportación de EE.UU. hacia India y de infraestructura eléctrica local.",
  "desc": "Yotta, respaldada por el grupo Hiranandani, opera el mayor campus de datacenters de la India y lanzó Shakti Cloud, la primera nube de IA soberana a gran escala del país basada en GPUs Nvidia. Es pieza central de la estrategia de India para reducir su dependencia de cómputo de IA extranjero."
 },
 "zayo-group": {
  "founded": 2007,
  "employees": 2200,
  "revenue_2025": "~$1.800M estimado",
  "geo_risk": "Exposición a permisos de derecho de vía en EE.UU./Europa y a refinanciamiento de deuda LBO en entorno de tasas altas.",
  "desc": "Zayo es uno de los mayores operadores de fibra óptica de largo recorrido de Norteamérica, adquirido en 2020 por EQT y Digital Colony (ahora DigitalBridge) por $14.300M. Su red es infraestructura crítica para interconectar datacenters de IA geográficamente dispersos."
 },
 "cologix": {
  "founded": 2010,
  "employees": 500,
  "revenue_2025": "~$400-500M estimado",
  "geo_risk": "Bajo, concentrado en EE.UU./Canadá; riesgo de disponibilidad eléctrica en mercados clave como Ashburn (Virginia).",
  "desc": "Cologix opera una red de datacenters de interconexión \"edge\" en mercados secundarios de Norteamérica y ha pivotado hacia campus de gran escala \"AI-ready\", incluyendo un plan de hasta $7.000M en Ashburn, Virginia, el mayor hub de datacenters del mundo."
 },
 "ntt-gdc": {
  "founded": 1988,
  "employees": 5000,
  "revenue_2025": "~$5.000-6.000M (división datacenters)",
  "geo_risk": "Bajo por diversificación geográfica, pero expuesto a tensiones de suministro eléctrico en mercados de alta demanda (EE.UU., APAC).",
  "desc": "NTT Global Data Centers es la división de infraestructura de datacenters de NTT Corporation, uno de los operadores más grandes y diversificados geográficamente del mundo. En 2026 anunció planes para duplicar su capacidad global ante la demanda explosiva de cómputo de IA."
 },
 "princeton-digital-group": {
  "founded": 2017,
  "employees": 400,
  "revenue_2025": "~$300-400M estimado",
  "geo_risk": "Alta fragmentación regulatoria entre mercados asiáticos (China, India, Corea) y riesgo de controles de exportación de chips que afectan disponibilidad de GPUs en la región.",
  "desc": "Princeton Digital Group, respaldado por Warburg Pincus, construye datacenters hyperscale en mercados de rápido crecimiento en Asia como China, India, Indonesia y Corea del Sur. Planea levantar hasta $5.000M en deuda para financiar su expansión de capacidad orientada a IA."
 },
 "edgeconnex": {
  "founded": 2009,
  "employees": 600,
  "revenue_2025": "~$600-800M estimado",
  "geo_risk": "Bajo-medio, diversificado globalmente; riesgo de disponibilidad eléctrica en mercados de expansión (Suecia, EE.UU.).",
  "desc": "EdgeConneX pasó de construir datacenters \"edge\" cerca de usuarios finales a convertirse en plataforma ancla de la nueva estrategia de infraestructura de IA de EQT, que movilizó miles de millones (incluyendo $2.400M de CPP Investments) para construir \"fábricas de IA\" a gran escala, como su proyecto conjunto con Lambda en Chicago."
 },
 "lightning-ai": {
  "founded": 2019,
  "employees": 150,
  "revenue_2025": "~$50-100M estimado",
  "geo_risk": "Bajo, opera principalmente en EE.UU.",
  "desc": "Lightning AI combina el popular framework open-source PyTorch Lightning con infraestructura de nube de GPU, absorbiendo la capacidad de Voltage Park en 2026 para ofrecer una plataforma integrada de desarrollo y despliegue de modelos de IA."
 },
 "fourier-intelligence": {
  "founded": 2015,
  "employees": 800,
  "revenue_2025": "Financiamiento acumulado estimado >$180M; ingresos no públicos",
  "geo_risk": "Como fabricante chino, expuesto a controles de exportación de semiconductores avanzados de EEUU y a posibles aranceles/restricciones de acceso a mercados occidentales.",
  "desc": "Fourier Intelligence nació de la robótica de rehabilitación médica y giró hacia humanoides de propósito general con su serie GR, vendida tanto a hospitales como a integradores industriales y de investigación. Es una de las startups chinas de humanoides mejor financiadas y candidata a una eventual salida a bolsa en Hong Kong o Shanghái."
 },
 "sanctuary-ai": {
  "founded": 2018,
  "employees": 120,
  "revenue_2025": "Financiamiento acumulado ~$180M; ronda 2025 de solo $10M en notas convertibles",
  "geo_risk": "Bajo riesgo geopolítico directo (Canadá/EEUU), pero alto riesgo de insolvencia o adquisición forzada dado el deterioro de caja.",
  "desc": "Sanctuary AI fue de las primeras en mostrar manos robóticas humanoides de alta destreza, pero entró en 2025-2026 en una fase crítica de escasez de capital, con despidos y cambio de CEO. Su futuro depende de encontrar un comprador estratégico o cerrar una ronda mayor."
 },
 "skild-ai": {
  "founded": 2023,
  "employees": 350,
  "revenue_2025": "Financiamiento acumulado >$2B; valuación ~$14-17B",
  "geo_risk": "Bajo riesgo geopolítico directo, pero depende de acceso continuo a GPUs Nvidia de alta gama para entrenamiento a gran escala.",
  "desc": "Fundada por investigadores de Carnegie Mellon (Deepak Pathak, Abhinav Gupta), Skild AI apuesta por un modelo de IA \"general purpose\" para robots físicos, análogo a los LLM. Su ronda de $1.4B en 2026 la convirtió en una de las startups de robótica mejor capitalizadas del mundo, y su adquisición del negocio robótico de Zebra marca un giro hacia integración vertical."
 },
 "berkshire-grey": {
  "founded": 2013,
  "employees": 400,
  "revenue_2025": "Adquirida por SoftBank en 2023 por ~$375M (vs. valuación pública de $2.7B en 2021)",
  "geo_risk": "Bajo riesgo geopolítico directo; riesgo de reestructuración interna dentro del portafolio robótico de SoftBank.",
  "desc": "Berkshire Grey fue una de las primeras empresas de robótica de almacenes en salir a bolsa vía SPAC (2021, valuación $2.7B), pero su desempeño comercial decepcionó y fue adquirida por SoftBank en 2023 con un 86% de descuento. SoftBank la integró en su ofensiva de robótica industrial junto con la compra de ABB Robotics en 2025."
 },
 "covariant": {
  "founded": 2017,
  "employees": 20,
  "revenue_2025": "Financiamiento acumulado previo ~$300M+; ingresos residuales por licencia a Amazon",
  "geo_risk": "Bajo riesgo geopolítico; riesgo regulatorio antitrust en EEUU por la estructura de \"licencia no exclusiva\" usada para evadir escrutinio de adquisición.",
  "desc": "Covariant fue pionera en modelos fundacionales de manipulación robótica para picking en almacenes, pero en agosto de 2024 Amazon contrató a sus tres fundadores y una cuarta parte del equipo mediante una licencia tecnológica no exclusiva, un mecanismo señalado por reguladores como forma de evadir revisión antitrust. La empresa remanente opera con apenas ~20 personas."
 },
 "dexterity": {
  "founded": 2017,
  "employees": 300,
  "revenue_2025": "Financiamiento acumulado ~$290-300M; valuación $1.65B (mar-2025)",
  "geo_risk": "Bajo riesgo geopolítico directo; expansión a Japón la expone a dinámicas de escasez de mano de obra logística local, su principal tesis de mercado.",
  "desc": "Dexterity fabrica el DexR, un robot dual móvil capaz de cargar y descargar camiones y contenedores a alta velocidad, un problema no resuelto por la robótica industrial tradicional. Su ronda de $95M en 2025 y la joint venture con Sumitomo para desplegar 1,500 robots en Japón la posicionan como líder en automatización de la última milla logística."
 },
 "righthand-robotics": {
  "founded": 2015,
  "employees": 80,
  "revenue_2025": "Financiamiento acumulado ~$66M+ (Serie C 2022); cifras 2025-2026 no públicas",
  "geo_risk": "Bajo riesgo geopolítico directo; dependiente de la salud del sector e-commerce/fulfillment en EEUU.",
  "desc": "RightHand Robotics, originada en laboratorios de robótica de Harvard, Yale y MIT, desarrolló uno de los primeros sistemas comerciales de \"each-picking\" para almacenes. Rockwell Automation es inversionista estratégico, pero la falta de rondas recientes genera dudas sobre su capacidad de competir con rivales más financiados."
 },
 "symbotic": {
  "founded": 2007,
  "employees": 2000,
  "revenue_2025": "$2,247M (FY2025), backlog $22.5B, market cap ~$26B (jul-2026)",
  "geo_risk": "Bajo riesgo geopolítico directo; riesgo de gobierno corporativo por conflictos de interés y antecedentes de investigación SEC sobre reconocimiento de ingresos.",
  "desc": "Symbotic es el líder en automatización robótica de almacenes de gran escala, con Walmart como cliente ancla y accionista. Su joint venture GreenBox con SoftBank busca expandir el modelo a otros retailers, pero la empresa arrastra pérdidas GAAP, un historial de restatement contable (2024) y señales de gobierno corporativo cuestionable."
 },
 "locus-robotics": {
  "founded": 2014,
  "employees": 400,
  "revenue_2025": "ARR ~$165-180M; financiamiento acumulado ~$432.8M (Serie F 2022, valuación ~$2B)",
  "geo_risk": "Bajo riesgo geopolítico directo; dependiente de la salud del sector logístico/e-commerce global.",
  "desc": "Locus Robotics es uno de los mayores operadores de robots móviles autónomos para picking en almacenes bajo un modelo Robotics-as-a-Service, con DHL como su cliente insignia. Ha mantenido crecimiento de ARR de doble dígito sin necesitar una ronda de financiamiento nueva desde 2022, aunque rumores de IPO persisten sin concretarse."
 },
 "vicarious-surgical": {
  "founded": 2014,
  "employees": 48,
  "revenue_2025": "$0 ingresos; déficit acumulado $253.4M; gasto operativo 2025 ~$50M",
  "geo_risk": "Bajo riesgo geopolítico directo; riesgo financiero extremo domina el perfil de la empresa.",
  "desc": "Vicarious Surgical desarrolla un robot quirúrgico de un solo puerto con brazos articulados y visión estereoscópica, respaldado en sus inicios por inversionistas de alto perfil (Bill Gates, Eric Schmidt). Tras años sin ingresos, en marzo 2026 fue deslistada de NYSE por bajo market cap y pasó a cotizar en OTCQB, con apenas meses de runway y sin haber completado ensayos en humanos."
 },
 "ambi-robotics": {
  "founded": 2019,
  "employees": 120,
  "revenue_2025": "Financiamiento acumulado ~$65-67M; demanda comercial fuerte, ingresos no públicos",
  "geo_risk": "Bajo riesgo geopolítico directo; dependiente de la salud del sector logístico/paquetería en EEUU.",
  "desc": "Ambi Robotics, fundada por investigadores de UC Berkeley, desarrolló un modelo fundacional propio (PRIME-1) para picking y clasificación de paquetes, con Pitney Bowes y UPS como clientes de referencia. Pese a tener su AmbiStack agotado para todo 2025, no ha anunciado una ronda de financiamiento desde 2022."
 },
 "diligent-robotics": {
  "founded": 2017,
  "employees": 217,
  "revenue_2025": "Financiamiento acumulado ~$70-100M; adquirida por ~$25.7-29M en acciones + earn-out hasta $5.3M (ene-2026)",
  "geo_risk": "Bajo riesgo geopolítico directo; riesgo regulatorio sanitario (FDA/hospitalario) para expansión de funciones.",
  "desc": "Diligent Robotics desarrolló Moxi, el robot móvil manipulador con IA más desplegado en hospitales de EEUU para tareas logísticas internas. En enero 2026 fue adquirida por Serve Robotics (Nasdaq: SERV), consolidando su tecnología dentro de un actor de robótica de entrega más amplio en vez de continuar como startup independiente."
 },
 "chef-robotics": {
  "founded": 2019,
  "employees": 80,
  "revenue_2025": "Financiamiento acumulado ~$65.6M (a abr-2025); ingresos no públicos",
  "geo_risk": "Bajo riesgo geopolítico directo; expuesta a costos de componentes (actuadores, sensores) sujetos a aranceles.",
  "desc": "Chef Robotics automatiza el ensamblaje de comidas (bowls, meal-kits, congelados) con brazos robóticos que aprenden de datos de producción real, sirviendo a marcas como Amy's Kitchen y Sunbasket. Su Serie A de 2025 combinó equity y financiamiento de equipos, reflejando el modelo intensivo en capital típico del Robotics-as-a-Service."
 },
 "realtime-robotics": {
  "founded": 2016,
  "employees": 52,
  "revenue_2025": "ARR estimado ~$5.7M; financiamiento acumulado ~$67-107M",
  "geo_risk": "Bajo riesgo geopolítico directo; dependiente de la salud del sector automotriz global (clientes concentrados en OEMs europeos).",
  "desc": "Realtime Robotics resuelve un problema crítico de la automatización industrial: coordinar múltiples robots sin colisiones en tiempo real. Su Serie B liderada por Mitsubishi Electric y clientes como BMW y Mercedes-Benz reflejan validación industrial profunda, aunque su escala de ingresos parece modesta frente al capital acumulado."
 },
 "formic": {
  "founded": 2018,
  "employees": 180,
  "revenue_2025": "Financiamiento acumulado ~$52M+ (extensión Serie A, jun-2024); ingresos no públicos",
  "geo_risk": "Bajo riesgo geopolítico directo; expuesta a costos de componentes (servos, brazos robóticos) sujetos a aranceles sobre manufactura industrial.",
  "desc": "Formic ofrece robots industriales sin inversión inicial (RaaS) a fabricantes medianos que no pueden justificar CapEx tradicional, con una tasa de renovación del 97% entre sus 25+ clientes. Su expansión de instalaciones en 2026 refleja demanda sostenida en un segmento de mercado desatendido por integradores tradicionales."
 },
 "zipline": {
  "founded": 2014,
  "employees": 375,
  "revenue_2025": "Serie H de $600-800M (ene-2026) + $200M adicionales (mar-2026); valuación $7.6B",
  "geo_risk": "Expuesta a regulación aérea diferenciada por país (FAA en EEUU, autoridades africanas); dependencia de componentes electrónicos/baterías con cadena de suministro global.",
  "desc": "Zipline es pionera mundial en entrega logística por drones, con una red consolidada de salud en África (Ruanda, Ghana) que ahora escala hacia retail comercial en EEUU junto a Walmart. Su ronda de 2026 la valora en $7.6B, superando ampliamente a competidores directos como Wing."
 },
 "wing-alphabet": {
  "founded": 2012,
  "employees": 500,
  "revenue_2025": "Financiada internamente por Alphabet; sin cifras públicas separadas",
  "geo_risk": "Bajo riesgo geopolítico directo; expuesta a regulación FAA sobre vuelos de drones en EEUU.",
  "desc": "Wing es el proyecto de entrega por drones de Alphabet, operando de forma independiente desde X Development desde 2018. Su alianza con Walmart la posiciona como una de las redes de entrega por drones de mayor cobertura en EEUU, compitiendo directamente con Zipline y Amazon Prime Air."
 },
 "skydio": {
  "founded": 2014,
  "employees": 900,
  "revenue_2025": "Ingresos >$100M (declarado por CEO); financiamiento acumulado ~$842M+; valuación $4.4B",
  "geo_risk": "Beneficiaria directa del ban de la FCC sobre drones chinos (dic-2025, litigio de DJI en curso), pero con exposición residual a componentes críticos (imanes de tierras raras, baterías) controlados por China.",
  "desc": "Skydio pivotó de drones de consumo a defensa y seguridad pública, capitalizando el vacío dejado por la prohibición estadounidense a DJI. Su inversión de $3.5B en manufactura doméstica (\"SkyForge\") busca reducir la dependencia de componentes críticos chinos, aunque esa dependencia persiste en imanes y baterías."
 },
 "waabi": {
  "founded": 2021,
  "employees": 250,
  "revenue_2025": "Ronda 2026 ~$1B; financiamiento acumulado ~$1.28B; valuación ~$3B",
  "geo_risk": "Bajo riesgo geopolítico directo (Canadá/EEUU); dependiente de regulación de vehículos autónomos en múltiples jurisdicciones norteamericanas.",
  "desc": "Waabi, fundada por la ex-jefa de IA de Uber ATG Raquel Urtasun, apuesta por un enfoque de simulación generativa para acelerar el desarrollo de camiones autónomos sin depender de flotas masivas de prueba física. Su ronda de 2026, con Volvo y Uber como socios estratégicos, la posiciona como un competidor serio frente a Aurora Innovation y Kodiak en transporte de carga autónomo."
 },
 "ubtech-robotics": {
  "founded": 2012,
  "employees": 3000,
  "revenue_2025": "Colocación de acciones HK$3.11B (~$400M) nov-2025; precio de acción +101.3% en 2025",
  "geo_risk": "Alto — como fabricante chino de humanoides, depende de imanes de tierras raras sujetos a controles de exportación de Beijing, mientras enfrenta restricciones de EEUU sobre semiconductores avanzados y posible exclusión de mercados occidentales/aliados.",
  "desc": "UBTech es el mayor fabricante chino de robots humanoides listado en bolsa, con una estrategia dual entre automatización industrial (Walker S) y robots de consumo para el mercado de personas mayores en China (U1). Su rápido crecimiento de ingresos y su posición pionera en HKEX la convierten en un proxy clave para apostar por el sector de humanoides chino, aunque con alto riesgo geopolítico de cadena de suministro y acceso a mercado."
 },
 "agibot-zhiyuan": {
  "founded": 2023,
  "employees": 1000,
  "revenue_2025": "ARR estimado ~$10.8M; valuación estimada ~$6.4B",
  "geo_risk": "Alto — empresa china de humanoides con ambiciones de exportación global, expuesta a controles de exportación de tierras raras y semiconductores, y a posibles restricciones de acceso a mercados occidentales.",
  "desc": "AgiBot (Zhiyuan Robotics), fundada por el ex-ingeniero de Huawei HiSilicon Peng Zhihui, es uno de los casos de crecimiento más rápidos del sector de humanoides chino, alcanzando estatus de unicornio en apenas dos años con respaldo de Sequoia China, Baidu, JD.com y BYD. Opera la instalación \"AgiBot World\" para recolección continua de datos de entrenamiento a escala."
 },
 "neura-robotics": {
  "founded": 2019,
  "employees": 400,
  "revenue_2025": "Serie C hasta $1.4B (jun-2026); valuación $7B; backlog/pipeline >$1B",
  "geo_risk": "Bajo riesgo geopolítico directo (Alemania/UE); comparte exposición a la cadena de suministro global de imanes de tierras raras y semiconductores avanzados.",
  "desc": "Neura Robotics es la apuesta europea más financiada en robótica humanoide, con su \"robot cognitivo\" 4NE-1 y partnerships industriales profundos con Bosch, Schaeffler y Kawasaki. Su Serie C de hasta $1.4B, liderada por el emisor de stablecoins Tether y con participación de Nvidia, Qualcomm y Amazon, es la mayor ronda jamás registrada en el sector, aunque analistas cuestionan si su valuación de $7B está respaldada por ingresos reales."
 },
 "vast-space": {
  "founded": 2021,
  "employees": 1000,
  "revenue_2025": "Financiamiento acumulado >$300M (capital propio del fundador)",
  "geo_risk": "Depende casi exclusivamente de SpaceX como único proveedor de lanzamiento y transporte tripulado.",
  "desc": "Vast fue fundada por Jed McCaleb (cofundador de Ripple/Stellar) para operar la primera estación espacial comercial con gravedad artificial. Haven-1 competirá con Axiom Space y Voyager/Starlab por los contratos de reemplazo de la ISS de NASA (Commercial LEO Destinations)."
 },
 "ispace": {
  "founded": 2010,
  "employees": 330,
  "revenue_2025": "~$20-25M, con pérdidas netas significativas",
  "geo_risk": "Dependencia de lanzadores extranjeros (SpaceX); exposición regulatoria dual Japón/EE.UU. vía ispace-U.S.",
  "desc": "ispace busca crear una \"economía cislunar\" transportando cargas para gobiernos y empresas privadas. Tras el fallo de Hakuto-R Mission 1 (2023) y Mission 2 \"Resilience\" (2025), se apoya en contratos institucionales para financiar Mission 3."
 },
 "astroscale": {
  "founded": 2013,
  "employees": 550,
  "revenue_2025": "~$40-45M",
  "geo_risk": "Opera en Japón, Reino Unido, EE.UU. e Israel, exponiéndose a controles de exportación cruzados en tecnología de doble uso.",
  "desc": "Astroscale fue pionera en definir el mercado de \"servicing\" orbital, con misiones como ELSA-d y ADRAS-J (inspección de basura para JAXA). Cotiza en Tokio desde 2023 y expande operaciones para capturar contratos de defensa espacial."
 },
 "d-orbit": {
  "founded": 2011,
  "employees": 300,
  "revenue_2025": "~€40-50M estimados; +€100M levantados en financiamiento acumulado",
  "geo_risk": "Dependencia de lanzadores estadounidenses (SpaceX Transporter) y exposición a políticas de exportación dual italiana/UE.",
  "desc": "D-Orbit es líder europeo en logística orbital \"última milla\", con su plataforma ION. También explora manufactura en microgravedad y misiones de defensa para el Ministerio de Defensa italiano y la ESA."
 },
 "momentus": {
  "founded": 2017,
  "employees": 90,
  "revenue_2025": "<$5M, con pérdidas operativas superiores a $50M anuales",
  "geo_risk": "Historial de escrutinio CFIUS por vínculos de fundación con capital chino, que forzó desinversión y reestructuración de gobernanza.",
  "desc": "Momentus fue pionera en vehículos de transferencia orbital con su línea Vigoride, pero enfrentó fallos técnicos, una demanda de la SEC (resuelta) y problemas severos de liquidez. Reduce personal y reenfoca su modelo hacia hosting de payloads y contratos gubernamentales."
 },
 "loft-orbital": {
  "founded": 2017,
  "employees": 220,
  "revenue_2025": "Financiamiento acumulado >$180M (Series B liderada por Tikehau Capital, 2023)",
  "geo_risk": "Alta dependencia de contratos de defensa de EE.UU. (Space Force/NRO), expuesta a cambios presupuestarios del Pentágono.",
  "desc": "Loft Orbital democratiza el acceso al espacio ofreciendo sus satélites YAM como plataforma multi-misión donde los clientes alquilan capacidad en vez de construir satélites propios. Trabaja con Space Force, NRO y operadores comerciales para desplegar sensores rápidamente."
 },
 "terran-orbital": {
  "founded": 2013,
  "employees": 1200,
  "revenue_2025": "~$250-300M estimados (como subsidiaria)",
  "geo_risk": "Manufactura concentrada en EE.UU.; ahora atada estratégicamente a las prioridades de Lockheed Martin en defensa y seguridad nacional.",
  "desc": "Terran Orbital escaló rápidamente como fabricante de buses satelitales para programas de defensa (incluyendo la Tranche 0/1 de la Space Development Agency), pero sus pérdidas como empresa pública en Nasdaq la llevaron a ser adquirida por completo por Lockheed Martin en noviembre de 2024."
 },
 "abl-space-systems": {
  "founded": 2017,
  "employees": 200,
  "revenue_2025": "Financiamiento acumulado >$500M",
  "geo_risk": "Alta concentración en contratos clasificados de defensa de EE.UU.; bajo riesgo geopolítico externo.",
  "desc": "ABL Space Systems intentó competir como lanzador orbital de bajo costo con su cohete RS1, pero tras fallos de lanzamiento canceló el programa en 2024 y redirigió su ingeniería de propulsión hacia interceptores de misiles e hipersónicos para el Pentágono."
 },
 "sierra-nevada-corporation": {
  "founded": 1963,
  "employees": 5000,
  "revenue_2025": "~$2000-2500M estimados (grupo completo)",
  "geo_risk": "Fuerte concentración en contratos clasificados de EE.UU.; expuesta a recortes o cambios de prioridad del Departamento de Defensa.",
  "desc": "Sierra Nevada Corporation es una de las mayores empresas de defensa privadas de EE.UU., especializada en aeronaves de misión especial e ISR. En 2021 escindió su unidad comercial de espacio (estación orbital, Dream Chaser) como Sierra Space, reteniendo programas espaciales de seguridad nacional clasificados."
 },
 "voyager-technologies": {
  "founded": 2019,
  "employees": 1000,
  "revenue_2025": "~$150-200M (segmento defensa/Nanoracks)",
  "geo_risk": "Depende de coordinación internacional con Airbus (socio en Starlab) y de que NASA mantenga el financiamiento del programa Commercial LEO Destinations.",
  "desc": "Voyager Technologies (ex-Voyager Space) salió a bolsa en NYSE en junio de 2025 tras integrar Nanoracks y asociarse con Airbus para construir la estación espacial comercial Starlab, uno de los finalistas del programa de NASA para reemplazar la ISS."
 },
 "sidus-space": {
  "founded": 2010,
  "employees": 60,
  "revenue_2025": "~$5-8M",
  "geo_risk": "Alta dependencia de contratos concentrados con SpaceX y NASA como clientes de manufactura; vulnerabilidad financiera de micro-cap.",
  "desc": "Sidus Space combina un negocio establecido de manufactura de precisión para la cadena de suministro espacial (piezas para SpaceX, Blue Origin, NASA) con el despliegue incipiente de su constelación LizzieSat, enfocada en agricultura, incendios forestales y seguridad marítima."
 },
 "nanoavionics": {
  "founded": 2014,
  "employees": 400,
  "revenue_2025": "~€60-80M estimados",
  "geo_risk": "Sede en Lituania, cerca de Bielorrusia/Rusia, con riesgo de seguridad regional pese al respaldo de Kongsberg (Noruega/OTAN).",
  "desc": "Nacida como spin-off de la Universidad de Vilnius, NanoAvionics es uno de los mayores fabricantes de buses de nanosatélites del mundo. En 2024-2025 Kongsberg Defence & Aerospace tomó control mayoritario, integrándola en su estrategia de defensa espacial europea."
 },
 "exolaunch": {
  "founded": 2011,
  "employees": 150,
  "revenue_2025": "~$40-60M estimados",
  "geo_risk": "Integración reciente en Isar Aerospace podría limitar su neutralidad frente a otros proveedores de lanzamiento no alemanes.",
  "desc": "Exolaunch se convirtió en el bróker e integrador de rideshare líder mundial, coordinando el despliegue de cientos de smallsats en misiones compartidas de SpaceX. En 2024 fue adquirida por Isar Aerospace para asegurar capacidades de integración de misión propias."
 },
 "karman-space-defense": {
  "founded": 1958,
  "employees": 1400,
  "revenue_2025": "~$400-450M",
  "geo_risk": "Cadena de suministro de materiales energéticos y aleaciones especiales concentrada en EE.UU.; alta sensibilidad a recortes de presupuesto de defensa.",
  "desc": "Karman Space & Defense salió a bolsa vía SPAC en diciembre de 2024 y se posiciona como proveedor crítico de \"pick-and-shovel\" para la carrera de armamento hipersónico y defensa antimisiles de EE.UU., suministrando estructuras y motores a los principales contratistas de defensa."
 },
 "true-anomaly": {
  "founded": 2022,
  "employees": 200,
  "revenue_2025": "Financiamiento acumulado >$260M",
  "geo_risk": "Negocio centrado en seguridad nacional de EE.UU.; alta sensibilidad a cambios de doctrina y presupuesto de la Fuerza Espacial.",
  "desc": "True Anomaly construye los vehículos Jackal, satélites autónomos diseñados para inspeccionar, rastrear y neutralizar amenazas de otros países en órbita, posicionándose en el naciente sector de \"seguridad espacial\" impulsado por la rivalidad EE.UU.-China-Rusia."
 },
 "impulse-space": {
  "founded": 2021,
  "employees": 300,
  "revenue_2025": "Financiamiento acumulado >$600M (Serie C 2025, valoración ~$3000M)",
  "geo_risk": "Depende de lanzadores de terceros (principalmente SpaceX) para llegar a órbita; bajo riesgo geopolítico directo.",
  "desc": "Impulse Space, fundada por el histórico ingeniero de propulsión de SpaceX Tom Mueller, desarrolla remolcadores orbitales (Mira) y una etapa de alta energía (Helios) para transferir satélites a órbitas geoestacionarias o cislunares en una sola misión de rideshare."
 },
 "varda-space-industries": {
  "founded": 2020,
  "employees": 150,
  "revenue_2025": "Financiamiento acumulado ~$450M (Serie C 2025)",
  "geo_risk": "Depende del bus satelital de Rocket Lab (Photon) y lanzamiento de SpaceX; cápsulas de reingreso requieren coordinación con la FAA y zonas de aterrizaje en EE.UU.",
  "desc": "Varda combina un bus satelital (Photon de Rocket Lab) con una cápsula de reingreso propia para fabricar en microgravedad cristales farmacéuticos de mayor pureza y devolverlos a la Tierra en semanas. Sus misiones W-1 a W-3 (2023-2025) demostraron el ciclo completo fabricación-reingreso-recuperación."
 },
 "orbit-fab": {
  "founded": 2018,
  "employees": 80,
  "revenue_2025": "Financiamiento acumulado >$100M",
  "geo_risk": "Fuerte dependencia de contratos de la Fuerza Espacial de EE.UU.; bajo riesgo geopolítico directo pero alta dependencia presupuestaria militar.",
  "desc": "Orbit Fab busca crear la infraestructura básica de \"gasolineras espaciales\" para reabastecer satélites en órbita, extendiendo su vida útil. Su estándar de puerto RAFTI ha sido adoptado como referencia por la Fuerza Espacial de EE.UU. para futuras misiones de servicio."
 },
 "starfish-space": {
  "founded": 2019,
  "employees": 50,
  "revenue_2025": "Financiamiento acumulado ~$45M",
  "geo_risk": "Bajo riesgo geopolítico directo; opera únicamente en EE.UU.",
  "desc": "Starfish Space, con ingenieros provenientes de Kepler Communications y Blue Origin, desarrolla el vehículo de servicio Otter para acoplarse de forma autónoma a satélites no cooperativos y extender su vida útil o desorbitarlos, apuntando a constelaciones comerciales más pequeñas que las que atiende Astroscale."
 },
 "space-forge": {
  "founded": 2021,
  "employees": 90,
  "revenue_2025": "Financiamiento acumulado ~$30-40M",
  "geo_risk": "Dependencia de spaceports emergentes del Reino Unido (aún sin cohete nacional operativo) y de lanzadores extranjeros.",
  "desc": "Space Forge es la apuesta británica por la manufactura orbital de semiconductores, usando satélites reutilizables ForgeStar que aprovechan la microgravedad y el vacío espacial para crear materiales de mayor pureza que en la Tierra, reingresando para reutilizar la plataforma en misiones sucesivas."
 },
 "helsing": {
  "founded": 2021,
  "employees": 750,
  "revenue_2025": "Valuación ~€12,000M (2025); financiamiento acumulado >€1,000M",
  "geo_risk": "Alta dependencia del gasto en defensa europeo post-Ucrania; exposición a cambios políticos sobre exportación de armas con IA.",
  "desc": "Fundada por Torsten Reil, Gundbert Scherf y Niklas Köhler, Helsing se posiciona como la \"Palantir europea de defensa\", vendiendo software de IA en vez de hardware. Colabora con Saab en drones submarinos y con Mistral AI en modelos militares."
 },
 "elbit-systems": {
  "founded": 1966,
  "employees": 20000,
  "revenue_2025": "~$7,500-8,000M",
  "geo_risk": "Exposición directa a conflictos en Medio Oriente y riesgo de sanciones/exclusiones ligadas a Gaza.",
  "desc": "Elbit es uno de los mayores contratistas de defensa de Israel, con presencia global vía Elbit Systems of America. Su cartera abarca desde drones tácticos hasta municiones de precisión, con fuerte crecimiento de backlog tras Gaza y Ucrania."
 },
 "iai-israel-aerospace": {
  "founded": 1953,
  "employees": 16000,
  "revenue_2025": "~$6,000-6,500M",
  "geo_risk": "Alta concentración geopolítica en el conflicto israelí-palestino y tensiones con Irán.",
  "desc": "IAI es el mayor fabricante aeroespacial de Israel, con rol central en el escudo antimisiles nacional (Arrow) y programas satelitales (Ofek, Amos). Su subsidiaria ELTA Systems es líder mundial en radares y sistemas EW."
 },
 "rafael-advanced-defense": {
  "founded": 1948,
  "employees": 10000,
  "revenue_2025": "~$5,000-5,500M",
  "geo_risk": "Alta exposición al conflicto israelí-palestino; capacidad productiva limitada ante demanda internacional creciente.",
  "desc": "Rafael desarrolló Iron Dome, coproducido con RTX para EE.UU., y el sistema Trophy adoptado en los tanques M1 Abrams. Tras octubre de 2023 aceleró producción de interceptores para cubrir demanda israelí y de aliados."
 },
 "general-dynamics": {
  "founded": 1952,
  "employees": 117000,
  "revenue_2025": "~$50,000M",
  "geo_risk": "Cuellos de botella en cadena de suministro de submarinos (mano de obra, componentes nucleares) que afectan compromisos AUKUS.",
  "desc": "Opera en cuatro segmentos (Aerospace, Marine Systems, Combat Systems, Technologies), uno de los cinco grandes contratistas de defensa de EE.UU. GDIT es proveedor clave de infraestructura cloud/IA para agencias de defensa e inteligencia."
 },
 "lockheed-martin": {
  "founded": 1995,
  "employees": 122000,
  "revenue_2025": "~$74,000M",
  "geo_risk": "Alta exposición a decisiones de exportación de armas (ITAR) y a cadenas de suministro de semiconductores/tierras raras.",
  "desc": "Domina el mercado de cazas furtivos con el F-35 (mayor programa de armas del mundo) y es líder en defensa antimisiles e infraestructura espacial militar. Invierte fuertemente en IA de misión y autonomía."
 },
 "textron-systems": {
  "founded": 1923,
  "employees": 4000,
  "revenue_2025": "~$1,200M (segmento Systems de Textron)",
  "geo_risk": "Dependencia de contratos plurianuales del Ejército de EE.UU. y exposición a cambios de prioridad hacia sistemas autónomos más baratos.",
  "desc": "Agrupa las capacidades de defensa no tripulada y de municiones de Textron, heredadas de adquisiciones como AAI Corporation. Compite en un mercado de UAS tácticos cada vez más disputado por firmas emergentes de autonomía."
 },
 "hanwha-aerospace": {
  "founded": 1977,
  "employees": 16000,
  "revenue_2025": "~$9,000-10,000M",
  "geo_risk": "Alta dependencia de tensiones en la península coreana y de tecnología de motores/semiconductores occidentales.",
  "desc": "Antes Samsung Techwin/Hanwha Techwin, se convirtió en uno de los mayores exportadores de armamento terrestre del mundo tras el megacontrato con Polonia. Controla Hanwha Ocean (naval/submarinos) y busca expandirse en EE.UU. adquiriendo astilleros."
 },
 "babcock-international": {
  "founded": 1891,
  "employees": 35000,
  "revenue_2025": "~£4,800M (~$6,100M)",
  "geo_risk": "Fuerte concentración en contratos del gobierno británico y sensibilidad a recortes o retrasos en AUKUS.",
  "desc": "Uno de los mayores contratistas de defensa del Reino Unido, especializado en el ciclo de vida completo de activos navales complejos, incluida la flota de submarinos nucleares británica. Actor clave del programa AUKUS."
 },
 "qinetiq": {
  "founded": 2001,
  "employees": 9500,
  "revenue_2025": "~£2,000M (~$2,550M)",
  "geo_risk": "Dependencia del gasto de defensa UK/EE.UU./Australia y riesgo regulatorio ITAR al expandirse en EE.UU.",
  "desc": "Nació como escisión del laboratorio de defensa gubernamental DERA y se especializa en ensayo y desarrollo de tecnologías avanzadas de defensa. Ha crecido agresivamente en EE.UU. vía adquisiciones para captar contratos del Pentágono."
 },
 "xanadu-quantum": {
  "founded": 2016,
  "employees": 300,
  "revenue_2025": "Financiamiento acumulado ~$300M+",
  "geo_risk": "Dependencia de capital de riesgo/inversión pública canadiense y riesgo de controles de exportación de tecnología cuántica.",
  "desc": "Pionera en computación cuántica fotónica, apostando por qubits basados en luz que operan a temperaturas más altas que los enfoques superconductores. PennyLane es un estándar de facto en machine learning cuántico."
 },
 "iqm-quantum": {
  "founded": 2018,
  "employees": 340,
  "revenue_2025": "Financiamiento acumulado >$200M; valuación estimada ~$1,000M+",
  "geo_risk": "Beneficiaria de estrategias de soberanía tecnológica UE, con riesgo de dependencia de subsidios estatales.",
  "desc": "Principal fabricante europeo de computadoras cuánticas superconductoras, con fabricación de chips propia en Espoo. Provee sistemas llave en mano a centros de supercómputo europeos como parte de la soberanía cuántica de la UE."
 },
 "alice-bob-quantum": {
  "founded": 2020,
  "employees": 150,
  "revenue_2025": "Financiamiento acumulado ~$130M+",
  "geo_risk": "Fuerte respaldo del estado francés por soberanía cuántica europea, con riesgo de fuga de talento hacia EE.UU. si no escala financiamiento.",
  "desc": "Una de las startups cuánticas más prometedoras de Europa, con arquitectura de cat qubits que promete reducir drásticamente los qubits físicos necesarios para tolerancia a fallos. Colabora con agencias de defensa francesas en su procesador Boson."
 },
 "seeqc-quantum": {
  "founded": 2019,
  "employees": 80,
  "revenue_2025": "Financiamiento acumulado ~$100M+",
  "geo_risk": "Cadena de suministro de chips superconductores dependiente de fundiciones especializadas; riesgo de controles de exportación de EE.UU.",
  "desc": "Empresa estadounidense (raíces en Hypres) especializada en electrónica de control digital criogénica para computación cuántica superconductora, componente clave para superar el cableado como cuello de botella al escalar sistemas."
 },
 "atom-computing": {
  "founded": 2018,
  "employees": 150,
  "revenue_2025": "~$180M financiamiento acumulado (incluye Series C ~$100M)",
  "geo_risk": "Depende de cadena de suministro de láseres/óptica de precisión y talento científico de EE.UU.; expuesta a controles de exportación.",
  "desc": "Fundada por Ben Bloom y Jonathan King, líder en computación cuántica de átomos neutros. Su colaboración con Microsoft Azure Quantum (24 qubits lógicos, 2024) fue uno de los primeros hitos públicos de corrección de errores a escala relevante."
 },
 "infleqtion": {
  "founded": 2007,
  "employees": 200,
  "revenue_2025": "~$150M+ financiamiento acumulado (Series B $110M en 2022)",
  "geo_risk": "Fuerte dependencia de contratos con el gobierno de EE.UU., expuesta a cambios presupuestarios y controles de exportación dual-use.",
  "desc": "Pionera en átomos fríos aplicados a computación cuántica y sensores de precisión/sincronización temporal. Adquirió Super.tech en 2022 para reforzar su stack de software. Mantiene fuertes vínculos con el ecosistema de defensa e investigación de EE.UU."
 },
 "world-labs": {
  "founded": 2024,
  "employees": 40,
  "revenue_2025": "~$230M levantados en ronda semilla (2024) a valuación ~$1,000M",
  "geo_risk": "Alta dependencia de acceso a GPUs Nvidia de última generación y de cómputo en la nube.",
  "desc": "Fundada en 2024 por Fei-Fei Li junto a Justin Johnson, Christoph Lassner y Ben Mildenhall, con respaldo de a16z, NEA, Radical Ventures, AMD Ventures e Intel Capital. Su tesis: la próxima frontera de la IA es la \"inteligencia espacial\" 3D."
 },
 "sakana-ai": {
  "founded": 2023,
  "employees": 40,
  "revenue_2025": "Valuación ~$1,500-2,600M; financiamiento acumulado >$300M",
  "geo_risk": "Depende del acceso a cómputo GPU global (Nvidia) y de la cooperación tecnológica Japón-EE.UU.",
  "desc": "Fundada en Tokio en 2023 por David Ha y Llion Jones, aplica principios de la naturaleza a la IA en vez de depender únicamente del escalado masivo. Respaldada por Nvidia, NEA, Lux Capital y conglomerados japoneses; colabora con el gobierno japonés usando la supercomputadora Fugaku."
 },
 "reflection-ai": {
  "founded": 2024,
  "employees": 100,
  "revenue_2025": "Financiamiento acumulado >$2,000M; valuación estimada $5,000-8,000M",
  "geo_risk": "Alta dependencia de cómputo GPU (Nvidia) y talento de IA de EE.UU.; su estrategia de modelos abiertos la sitúa en debates geopolíticos EE.UU.-China.",
  "desc": "Fundada en 2024 por Misha Laskin e Ioannis Antonoglou, ambos ex-Google DeepMind con roles clave en AlphaGo y Gemini. Su misión: construir \"el DeepSeek de Estados Unidos\", modelos de frontera abiertos especializados en agentes de codificación."
 },
 "poolside-ai": {
  "founded": 2023,
  "employees": 80,
  "revenue_2025": "Financiamiento acumulado >$600M (Series B ~$500M a valuación ~$3,000M)",
  "geo_risk": "Dependencia crítica de GPUs Nvidia y energía para su clúster dedicado en EE.UU.; operación dual EE.UU.-Francia expuesta a diferencias regulatorias UE/EE.UU.",
  "desc": "Fundada en 2023 por Jason Warner y Eiso Kant, desarrolla modelos fundacionales especializados en generación de código con RL y datos sintéticos a gran escala. Con equipos en San Francisco y París, invirtió en infraestructura de cómputo propia para reducir dependencia de proveedores cloud."
 },
 "naval-group": {
  "founded": 1631,
  "employees": 18000,
  "revenue_2025": "~$4,500M",
  "geo_risk": "Alta dependencia del gasto de defensa francés y sensibilidad a crisis diplomáticas en exportación (precedente AUKUS).",
  "desc": "Astillero de defensa estatal de Francia, pilar de la disuasión nuclear naval del país. Thales participa en su capital y en sistemas embarcados."
 },
 "dassault-aviation": {
  "founded": 1929,
  "employees": 13000,
  "revenue_2025": "~$6,500M",
  "geo_risk": "Exposición a decisiones geopolíticas de compradores de Rafale (Medio Oriente, India) y fricciones franco-alemanas en SCAF/FCAS.",
  "desc": "Fabricante insignia de aviación militar francesa, responsable del caza Rafale y motor de la autonomía estratégica aérea de Francia. Thales es socio industrial clave en aviónica."
 },
 "Cognition": {
  "founded": 2023,
  "employees": 150,
  "revenue_2025": "valuación ~$10.2B (sep 2025) tras compra de Windsurf; luego ronda de $1B a $25-26B pre-money (mayo 2026)",
  "geo_risk": "Concentración en EE.UU. (SF); dependencia crítica de proveedores de modelos LLM externos y de GPU cloud, sin redundancia geográfica de datacenters propia.",
  "desc": "Cognition AI es la creadora de Devin, un \"ingeniero de software autónomo\" basado en agentes de IA que escribe, prueba y despliega código. En 2025 adquirió Windsurf (ex-Codeium) tras el colapso de su venta a OpenAI, consolidándose como líder en codificación agéntica empresarial."
 },
 "Imbue": {
  "founded": 2021,
  "employees": 40,
  "revenue_2025": "valuación >$1B tras ronda de $200M (2023), liderada por Astera Institute",
  "geo_risk": "Laboratorio pequeño en EE.UU. muy dependiente de un único gran inversor de cómputo (Nvidia), lo que la hace vulnerable a cambios de asignación de GPUs.",
  "desc": "Imbue es un laboratorio de investigación en IA enfocado en construir agentes que \"razonan de forma robusta\" y pueden operar código y tareas complejas con supervisión mínima. Pivotó de investigación fundamental de IA general a agentes prácticos de productividad."
 },
 "Voiceflow": {
  "founded": 2019,
  "employees": 90,
  "revenue_2025": "~$9.9M ARR reportado (2025), tras ronda de $15M",
  "geo_risk": "Startup canadiense (Toronto) de tamaño medio, dependiente de APIs de LLM de terceros para su núcleo de producto.",
  "desc": "Voiceflow es una plataforma colaborativa para diseñar y desplegar agentes conversacionales de IA (voz y chat) usada por equipos de producto y CX. Permite prototipar, probar y lanzar asistentes virtuales conectados a modelos de lenguaje de terceros."
 },
 "AlphaSenseFin": {
  "founded": 2011,
  "employees": 1800,
  "revenue_2025": ">$600M ARR; ronda de $350M a valuación de $7.5B (2025/2026)",
  "geo_risk": "Fuerte concentración de ingresos en clientes de servicios financieros de EE.UU./Europa; dependencia de proveedores de LLM externos para su función de búsqueda generativa.",
  "desc": "AlphaSense es una plataforma de búsqueda e inteligencia de mercado impulsada por IA que agrega informes de research, transcripciones de earnings calls y documentos regulatorios para profesionales de inversión y corporativos. Adquirió Tegus en 2024, ampliando su cobertura de transcripciones de expertos."
 },
 "Kensho": {
  "founded": 2013,
  "employees": 200,
  "revenue_2025": "N/A pública (parte de S&P Global, adquirida por $550M en 2018)",
  "geo_risk": "Dependencia total de la estrategia y presupuesto de I+A de su matriz S&P Global; riesgo de reasignación de recursos ante cambios corporativos.",
  "desc": "Kensho es la división de inteligencia artificial de S&P Global, especializada en NLP, extracción de entidades y reconocimiento de voz (Scribe) para datos financieros. Sus modelos alimentan productos de S&P Capital IQ y Market Intelligence."
 },
 "Kavout": {
  "founded": 2015,
  "employees": 20,
  "revenue_2025": "no divulgada (privada, fintech de nicho)",
  "geo_risk": "Startup pequeña con sede en Seattle/Asia, alta dependencia de proveedores de datos de mercado y cómputo cloud de terceros, vulnerable a consolidación del sector fintech-AI.",
  "desc": "Kavout es una plataforma de inteligencia de inversión basada en IA (Kai Score) que genera señales cuantitativas y de ranking de acciones combinando datos alternativos, fundamentales y de sentimiento de mercado para gestores de activos y traders minoristas."
 },
 "Addepar": {
  "founded": 2009,
  "employees": 900,
  "revenue_2025": "valuación estimada >$3.25B (última ronda conocida ~2021, con levantamientos adicionales posteriores)",
  "geo_risk": "Alta concentración en clientes de wealth management de EE.UU.; dependencia de infraestructura cloud de un único proveedor principal para datos financieros sensibles.",
  "desc": "Addepar es una plataforma de gestión de patrimonio e inversiones que agrega y analiza datos financieros complejos (multi-activo) para family offices, RIAs y bancos privados. Es ampliamente usada por gestores de grandes fortunas en EE.UU."
 },
 "FactSet": {
  "founded": 1978,
  "employees": 12000,
  "revenue_2025": "~$2.3B ingresos anuales (FY2025)",
  "geo_risk": "Dependencia de la estabilidad regulatoria del sector de datos financieros y de acuerdos de distribución de datos con exchanges globales.",
  "desc": "FactSet es un proveedor global de datos financieros, analítica y software de flujo de trabajo para gestores de inversión, banca y corporativos. Compite con Bloomberg y S&P Capital IQ, e integra capacidades de IA generativa en su plataforma \"FactSet Mercury\"."
 },
 "Morningstar": {
  "founded": 1984,
  "employees": 13000,
  "revenue_2025": "~$2.4B ingresos anuales (FY2025)",
  "geo_risk": "Ingresos diversificados globalmente pero con exposición a la volatilidad de flujos de fondos de inversión que afecta su negocio de ratings/licencias de datos.",
  "desc": "Morningstar es un proveedor líder de investigación de inversión independiente, ratings de fondos y datos ESG (Sustainalytics) para inversores institucionales y minoristas a nivel global."
 },
 "NASDAQ": {
  "founded": 1971,
  "employees": 8700,
  "revenue_2025": "~$7.8B ingresos anuales (FY2025 estimado)",
  "geo_risk": "Infraestructura crítica de mercado financiero de EE.UU.; alta exposición regulatoria y a riesgo de ciberseguridad como operador de bolsa sistémico.",
  "desc": "Nasdaq Inc. opera la segunda bolsa de valores más grande del mundo y provee tecnología de mercado, datos financieros y soluciones antifraude/RegTech impulsadas por IA a otras bolsas y bancos globalmente."
 },
 "CBOE": {
  "founded": 1973,
  "employees": 1700,
  "revenue_2025": "~$2.2B ingresos anuales (FY2025 estimado)",
  "geo_risk": "Concentración de negocio en derivados/opciones de EE.UU., con expansión reciente a cripto y mercados globales que aumenta exposición regulatoria.",
  "desc": "Cboe Global Markets opera mercados de opciones, futuros, acciones y divisas, siendo el mayor mercado de opciones de EE.UU. Ha impulsado su transformación digital migrando infraestructura de trading a la nube."
 },
 "AlphaSense": {
  "founded": 2011,
  "employees": 1800,
  "revenue_2025": ">$600M ARR; valuación $7.5B tras ronda de $350M",
  "geo_risk": "Ver entrada AlphaSense (Finance AI); misma entidad corporativa, riesgo concentrado en clientes institucionales de EE.UU./Europa.",
  "desc": "(Ver descripción de AlphaSense (Finance AI): plataforma de búsqueda e inteligencia de mercado con IA generativa para profesionales financieros y corporativos.)"
 },
 "MSCI": {
  "founded": 1969,
  "employees": 5600,
  "revenue_2025": "~$2.9B ingresos anuales (FY2025 estimado)",
  "geo_risk": "Alta dependencia de licencias de índices para productos financieros pasivos globales; expuesto a riesgo regulatorio ESG en distintas jurisdicciones.",
  "desc": "MSCI es un proveedor global líder de índices bursátiles, herramientas de análisis de riesgo de carteras y datos ESG/climáticos usados por gestores de activos institucionales en todo el mundo."
 },
 "Crane_NXT": {
  "founded": 2023,
  "employees": 4000,
  "revenue_2025": "~$1.3B ingresos anuales (FY2025 estimado)",
  "geo_risk": "Negocio de autenticación de moneda y pagos con exposición a cambios en políticas de efectivo/digitalización de bancos centrales globales.",
  "desc": "Crane NXT es una empresa de tecnología especializada en autenticación de billetes, seguridad de marca y sistemas de validación de pagos en efectivo, usada por bancos centrales, casinos y sistemas de transporte."
 },
 "Suno": {
  "founded": 2022,
  "employees": 60,
  "revenue_2025": "valuación estimada ~$2.45B (ronda Series C 2025)",
  "geo_risk": "Alto riesgo legal por demandas de las principales discográficas (Universal, Warner, Sony) por entrenamiento de modelos con material protegido por derechos de autor.",
  "desc": "Suno AI es una startup que desarrolla modelos generativos de IA para creación de música a partir de texto, permitiendo a usuarios generar canciones completas con letra, voz e instrumentación. Alcanzó acuerdos de licencia con discográficas tras litigios en 2025."
 },
 "GenDigital": {
  "founded": 1982,
  "employees": 10000,
  "revenue_2025": "~$3.9B ingresos anuales (FY2025)",
  "geo_risk": "Exposición a regulación de privacidad de datos de consumidores en múltiples jurisdicciones (UE/GDPR) tras la fusión con Avast (República Checa).",
  "desc": "Gen Digital es la matriz de marcas de ciberseguridad para consumidores como Norton, Avast, LifeLock, Avira y CCleaner, ofreciendo protección antivirus, VPN y de identidad impulsada por IA de detección de amenazas."
 },
 "Trimble_Inc": {
  "founded": 1978,
  "employees": 11000,
  "revenue_2025": "~$3.6B ingresos anuales (FY2025 estimado)",
  "geo_risk": "Negocio de posicionamiento/geoespacial dependiente de constelaciones satelitales GNSS y de la disponibilidad de espectro; exposición a tensiones geopolíticas en cadenas de suministro de hardware GPS.",
  "desc": "Trimble es un proveedor global de tecnología de posicionamiento, geoespacial y software para construcción, agricultura y transporte, combinando hardware GNSS con plataformas de software en la nube potenciadas por IA."
 },
 "Verint": {
  "founded": 1994,
  "employees": 3300,
  "revenue_2025": "~$900M ingresos anuales (FY2025 estimado)",
  "geo_risk": "Negocio de analítica de experiencia del cliente con exposición regulatoria a privacidad de datos de consumidores (grabación/análisis de interacciones) en múltiples países.",
  "desc": "Verint es un proveedor de software de experiencia del cliente (CX) e IA conversacional, con soluciones de analítica de voz, chatbots y automatización de centros de contacto usadas por grandes bancos y aseguradoras."
 },
 "Salesforce": {
  "founded": 1999,
  "employees": 76000,
  "revenue_2025": "~$38B ingresos anuales (FY2025)",
  "geo_risk": "Como gigante SaaS global, expuesto a regulaciones de soberanía de datos en múltiples jurisdicciones y a la concentración de infraestructura en pocos hyperscalers.",
  "desc": "Salesforce es la plataforma de CRM líder mundial, que ha expandido agresivamente su oferta de IA agéntica (Agentforce) e invierte activamente en startups de IA a través de Salesforce Ventures."
 },
 "Raytheon": {
  "founded": 1922,
  "employees": 187000,
  "revenue_2025": "~$85.000M (ingresos anuales, tendencia de crecimiento desde $80.700M en 2024)",
  "geo_risk": "Alta dependencia del presupuesto de defensa de EE.UU. y exposición de su cadena de suministro de microelectrónica a fundiciones en Taiwán/Asia.",
  "desc": "RTX (ex Raytheon Technologies) es un conglomerado aeroespacial y de defensa que agrupa a Collins Aerospace, Pratt & Whitney y Raytheon (misiles, radares y sensores). Es uno de los mayores proveedores de motores de aviación y sistemas de defensa antimisiles del mundo, y ha comenzado a integrar IA generativa en ingeniería digital."
 },
 "Leidos": {
  "founded": 2013,
  "employees": 47000,
  "revenue_2025": "$17.200M (cierre de año fiscal 2025, según reporte oficial)",
  "geo_risk": "Fuerte dependencia de contratos federales de EE.UU.; vulnerable a shutdowns gubernamentales y resoluciones de continuidad presupuestaria.",
  "desc": "Leidos es uno de los mayores integradores de TI y servicios de defensa/inteligencia de EE.UU., con contratos en NGA, DoD, NASA y salud. En 2025 anunció una alianza de ciberseguridad con IA junto a Nvidia y VAST Data."
 },
 "Parsons": {
  "founded": 1944,
  "employees": 20000,
  "revenue_2025": "$6.400M (año fiscal 2025, récord)",
  "geo_risk": "Alta exposición a contratos de infraestructura en Medio Oriente y a riesgo de cierre/recorte presupuestario federal de EE.UU.",
  "desc": "Parsons ofrece ingeniería de defensa, ciberseguridad e infraestructura crítica al gobierno de EE.UU. y a clientes de Medio Oriente. En diciembre de 2025 fue seleccionada para el contrato multiadjudicatario de defensa antimisiles MDA SHIELD, valorado en $151.000M."
 },
 "AxonEnterprise": {
  "founded": 1993,
  "employees": 4500,
  "revenue_2025": "~$2.700M (estimado; 2024 fue $2.100M con 33% de crecimiento interanual)",
  "geo_risk": "Dependencia de presupuestos de policía/seguridad pública en EE.UU. y creciente escrutinio regulatorio sobre drones armados e IA.",
  "desc": "Axon fabrica TASER, cámaras corporales y software de evidencia (Evidence.com), y ha expandido su ecosistema con IA generativa (Draft One) y sistemas de drones para primera respuesta."
 },
 "Thales": {
  "founded": 2000,
  "employees": 81000,
  "revenue_2025": "~€21.000M (estimado, en línea con crecimiento desde €20.600M en 2024)",
  "geo_risk": "Exposición a presupuestos de defensa franceses/europeos y a controles de exportación de tecnología dual-use hacia Medio Oriente.",
  "desc": "Thales Group es un grupo francés que suministra electrónica de defensa, aviónica, radares y ciberseguridad, con creciente presencia en computación cuántica, espacio e IA para identificación segura."
 },
 "PaloAltoNetworks": {
  "founded": 2005,
  "employees": 15000,
  "revenue_2025": "~$9.200M (año fiscal 2025)",
  "geo_risk": "Exposición a un panorama de amenazas cibernéticas geopolíticamente impulsado y a competencia intensa (CrowdStrike) en un mercado de talento escaso.",
  "desc": "Palo Alto Networks es líder en ciberseguridad basada en IA (firewalls de próxima generación, Cortex XSIAM). En 2025 completó adquisiciones como Protect AI y CyberArk, ampliando su enfoque hacia la seguridad de agentes de IA."
 },
 "Teledyne_Flir": {
  "founded": 1978,
  "employees": 8000,
  "revenue_2025": "Incluido en Teledyne Technologies (~$5.700M totales 2024); segmento aeroespacial/defensa (incl. FLIR) ~$1.900M",
  "geo_risk": "Controles ITAR sobre tecnología de imagen térmica y exposición a componentes de la cadena de suministro china.",
  "desc": "Teledyne FLIR es proveedor líder de sensores térmicos e imágenes infrarrojas para defensa, drones y seguridad fronteriza, integrado en Teledyne Technologies desde 2021."
 },
 "Saab_AB": {
  "founded": 1937,
  "employees": 24000,
  "revenue_2025": "~SEK 68.000M (~$6.500M, estimado)",
  "geo_risk": "Exposición a tensiones en el Báltico/OTAN y a controles de exportación sobre el caza Gripen.",
  "desc": "Saab AB es un fabricante sueco de sistemas de defensa (caza Gripen, radares AESA, submarinos), en fuerte expansión desde el ingreso de Suecia a la OTAN en 2024."
 },
 "ShieldAI": {
  "founded": 2015,
  "employees": 750,
  "revenue_2025": "Valoración de $12.700M tras contrato de la Fuerza Aérea de EE.UU. (CCA), ingresos no divulgados públicamente",
  "geo_risk": "Dependencia de contratos del DoD de EE.UU. y de Ucrania; riesgo de controles de exportación sobre software de autonomía.",
  "desc": "Shield AI desarrolla el sistema de autonomía Hivemind para aeronaves no tripuladas, usado en el dron V-BAT y en el programa de Cazas Colaborativos de Combate (CCA) de EE.UU."
 },
 "Hailo": {
  "founded": 2017,
  "employees": 250,
  "revenue_2025": "Valoración >$1.000M tras ronda Serie D 2024 (~$120M levantados)",
  "geo_risk": "Sede en Israel, expuesta a inestabilidad regional y a controles de exportación sobre chips de IA de doble uso.",
  "desc": "Hailo desarrolla procesadores de IA de borde (Hailo-8/Hailo-10) para visión por computadora en automoción, cámaras inteligentes y aplicaciones de defensa."
 },
 "Untether_AI": {
  "founded": 2018,
  "employees": 2024,
  "revenue_2025": "No aplicable — la empresa detuvo sus operaciones comerciales en 2024",
  "geo_risk": "Riesgo de cierre total; activos e IP potencialmente en venta tras la crisis de financiamiento de 2024.",
  "desc": "Untether AI desarrollaba chips de inferencia con cómputo en memoria (speedAI) para aplicaciones de borde y defensa. A mediados de 2024 cesó sus operaciones comerciales tras no asegurar nuevo financiamiento, despidiendo a la mayor parte de su plantilla."
 },
 "AnsysEDA": {
  "founded": 1970,
  "employees": 6000,
  "revenue_2025": "~$2.700M (último año como entidad independiente antes del cierre de la adquisición)",
  "geo_risk": "Ahora parte de Synopsys, expuesta a restricciones de exportación de EDA hacia China.",
  "desc": "Ansys es líder en software de simulación de ingeniería (CFD, estructural, electromagnética). En julio de 2025 Synopsys completó su adquisición por ~$35.000M para integrar simulación de sistemas con diseño de chips."
 },
 "Kneron": {
  "founded": 2015,
  "employees": 200,
  "revenue_2025": "Valoración >$1.000M (unicornio desde ronda respaldada por Foxconn/Qualcomm)",
  "geo_risk": "Manufactura y ecosistema concentrados en Taiwán, expuestos a tensión en el estrecho de Taiwán.",
  "desc": "Kneron diseña procesadores de IA de borde (NPU) de bajo consumo para dispositivos, cámaras y automoción, con inversión estratégica de Foxconn y Qualcomm."
 },
 "Mythic": {
  "founded": 2012,
  "employees": 80,
  "revenue_2025": "No divulgado; principalmente pre-ingresos, sostenida por financiamiento puente tras casi cerrar en 2023",
  "geo_risk": "Riesgo elevado de continuidad financiera tras crisis de 2023; depende de nuevas rondas de capital.",
  "desc": "Mythic desarrolla chips de IA analógicos de cómputo en memoria para inferencia de borde de bajo consumo. Sobrevivió a una crisis de financiamiento en 2023 que casi la lleva al cierre."
 },
 "GreenWaves": {
  "founded": 2014,
  "employees": 45,
  "revenue_2025": "No divulgado; startup de nicho con financiamiento total acumulado <$30M",
  "geo_risk": "Startup europea pequeña, altamente dependiente de rondas de financiamiento adicionales.",
  "desc": "GreenWaves Technologies diseña procesadores RISC-V ultra eficientes (familia GAP9) para IA de borde en audio y sensores wearables, originada como spinoff del instituto francés CEA-Leti."
 },
 "SiMa": {
  "founded": 2018,
  "employees": 200,
  "revenue_2025": "Valoración >$1.000M (ronda 2024 a ~$800M, con crecimiento posterior)",
  "geo_risk": "Depende de financiamiento continuo frente a competencia de Nvidia Jetson y Qualcomm en IA de borde.",
  "desc": "SiMa.ai diseña SoCs de IA de borde de bajo consumo (MLSoC) para visión por computadora en automoción, robótica y aplicaciones de defensa."
 },
 "Syntiant": {
  "founded": 2017,
  "employees": 100,
  "revenue_2025": "No divulgado; financiamiento total acumulado >$150M",
  "geo_risk": "Startup dependiente de clientes de electrónica de consumo (auriculares/wearables) y de rondas de capital adicionales.",
  "desc": "Syntiant diseña procesadores NDP de IA ultra eficiente para reconocimiento de voz \"always-on\" en auriculares y wearables, respaldada por inversión estratégica de gigantes tecnológicos."
 },
 "Semtech": {
  "founded": 1960,
  "employees": 1800,
  "revenue_2025": "~$900M (estimado, tras la integración de Sierra Wireless en 2023)",
  "geo_risk": "Exposición a manufactura y pruebas en China, y a ciclicidad del mercado de telecomunicaciones/IoT.",
  "desc": "Semtech es proveedor de semiconductores analógicos y de señal mixta, conocido por su tecnología LoRa para IoT y por sus productos de interconexión de alta velocidad (CopperEdge) para centros de datos de IA."
 },
 "MACOM": {
  "founded": 1950,
  "employees": 2300,
  "revenue_2025": "~$1.020M (superó $1.000M por primera vez en año fiscal 2025)",
  "geo_risk": "Exposición a demanda de telecomunicaciones en China y a controles de exportación de tecnología GaN/GaAs de uso dual.",
  "desc": "MACOM diseña semiconductores de RF, microondas y fotónica para aplicaciones de defensa, centros de datos ópticos de IA y redes 5G."
 },
 "PowerIntegrations": {
  "founded": 1988,
  "employees": 800,
  "revenue_2025": "~$430M (estimado, en línea con 2024)",
  "geo_risk": "Alta exposición a manufactura de electrónica de consumo y electrodomésticos en China.",
  "desc": "Power Integrations diseña circuitos integrados de conversión de energía de alta eficiencia (tecnología PowiGaN), usados en cargadores, fuentes de alimentación de centros de datos y automoción."
 },
 "Diodes": {
  "founded": 1959,
  "employees": 8000,
  "revenue_2025": "~$1.250M (estimado)",
  "geo_risk": "Manufactura propia significativa en Shanghái y Chengdu, expuesta a tensión comercial EE.UU.-China.",
  "desc": "Diodes Incorporated fabrica semiconductores discretos, de señal mixta y de gestión de energía para automoción, informática e IA, con fábricas propias en China y EE.UU."
 },
 "Cirrus_Logic": {
  "founded": 1984,
  "employees": 1700,
  "revenue_2025": "~$1.900M (año fiscal cerrado en marzo 2025)",
  "geo_risk": "Concentración extrema de clientes (Apple representa más del 80% de sus ingresos) y exposición a fundiciones en Taiwán.",
  "desc": "Cirrus Logic diseña circuitos integrados de audio y gestión de energía de señal mixta, con Apple como su cliente dominante desde hace más de una década."
 },
 "Innatera": {
  "founded": 2018,
  "employees": 60,
  "revenue_2025": "pre-ingresos; ronda Serie A de $21M (2024) más ampliaciones (~€5M adicionales), total levantado ~€35-40M",
  "geo_risk": "Startup europea de deep-tech dependiente de acceso a foundries asiáticas/americanas (GlobalFoundries) y de financiamiento de VC europeo, vulnerable a controles de exportación de IP de semiconductores.",
  "desc": "Fabricante holandés de procesadores neuromórficos de ultra bajo consumo (chip Pulsar) para sensado e IA en el borde (wearables, IoT industrial, audio). Combina un núcleo de red neuronal de impulsos (spiking) con un core de control convencional para inferencia con microwatts de consumo."
 },
 "GrAI_Matter": {
  "founded": 2016,
  "employees": 30,
  "revenue_2025": "pre-ingresos significativos; total levantado histórico ~$40M",
  "geo_risk": "Startup en dificultades financieras con operaciones prácticamente detenidas, alto riesgo de cierre definitivo o venta de activos de IP.",
  "desc": "Diseñador franco-singapurense de procesadores neuromórficos de eventos (event-based) para visión por computador de bajo consumo, dirigido a automoción y edge AI. Enfrentó fuertes recortes y pausa operativa tras no cerrar rondas posteriores."
 },
 "Lightelligence": {
  "founded": 2017,
  "employees": 150,
  "revenue_2025": "ronda Serie C de ~$210M (liderada por inversores chinos incl. China Mobile), pre-ingresos comerciales masivos",
  "geo_risk": "Empresa dual EE.UU.-China en computación fotónica, expuesta a controles de exportación de EE.UU. sobre tecnología de IA avanzada y a tensiones de desacoplamiento tecnológico.",
  "desc": "Desarrolladora de chips de computación óptica/fotónica híbrida para acelerar cargas de trabajo de IA con menor consumo energético que GPUs convencionales. Ha girado buena parte de su financiamiento e infraestructura de fabricación hacia el ecosistema chino."
 },
 "RockleyPhotonics": {
  "founded": 2013,
  "employees": 100,
  "revenue_2025": "ingresos reducidos (~decenas de millones USD), compañía privada tras salir de bancarrota, respaldada por inversión de Medtronic",
  "geo_risk": "Historial de bancarrota (Chapter 11, 2023) y dependencia de pocos clientes ancla (Apple, Medtronic), alto riesgo de liquidez.",
  "desc": "Fabricante de sensores fotónicos de silicio para biomarcadores en dispositivos wearables (\"clinic-on-the-wrist\"). Trabajó como proveedor/socio de I+D de Apple para sensores del Apple Watch y ahora se enfoca en biomarcadores clínicos con Medtronic."
 },
 "QuEra": {
  "founded": 2018,
  "employees": 150,
  "revenue_2025": "ronda ampliada de $230M (2024-25); valuación reportada >$1B",
  "geo_risk": "Dependencia de contratos gubernamentales de EE.UU. (DARPA, DOE) y de la disponibilidad continua en la nube de AWS Braket para monetización comercial.",
  "desc": "Compañía líder en computación cuántica de átomos neutros, con hoja de ruta hacia sistemas tolerantes a fallos (Libra). Su tecnología se comercializa principalmente a través de Amazon Braket y colaboraciones de investigación con universidades y gobierno."
 },
 "Livent": {
  "founded": 2018,
  "employees": 1600,
  "revenue_2025": "entidad fusionada con Allkem en 2024 (deal ~$10.6B); adquirida por Rio Tinto en marzo 2025 por US$6.7B",
  "geo_risk": "Nodo ahora integrado dentro de Rio Tinto (no listado en el grafo), con operaciones críticas de litio en Argentina/China expuestas a nacionalización y controles de exportación.",
  "desc": "Productor histórico de hidróxido de litio de alta pureza para baterías EV, con contrato emblemático de largo plazo con BMW. Su fusión con Allkem (2024) creó Arcadium Lithium, adquirida luego por el gigante minero Rio Tinto."
 },
 "PiedmontLithium": {
  "founded": 2016,
  "employees": 100,
  "revenue_2025": "compañía en etapa de desarrollo, sin ingresos comerciales masivos aún; capitalización de mercado fluctuante ~US$200-400M",
  "geo_risk": "Proyectos clave dependen de permisos ambientales en EE.UU. (Carolina del Norte) y de la joint venture North American Lithium en Quebec, expuestos a retrasos regulatorios.",
  "desc": "Minera y procesadora de litio (espodumeno) enfocada en asegurar cadena de suministro norteamericana para baterías EV. Mantiene un acuerdo de venta clave con Tesla, ampliado y modificado varias veces desde 2020."
 },
 "SigmaLithium": {
  "founded": 2012,
  "employees": 500,
  "revenue_2025": "US$146M en dos acuerdos de offtake firmados en 2025; flujo de caja 4T25 de US$31M con margen de caja del 47%",
  "geo_risk": "Producción concentrada en Brasil (Vale do Jequitinhonha), expuesta a volatilidad regulatoria minera brasileña y a rumores de adquisición no concretados (Tesla).",
  "desc": "Productora brasileña de \"litio verde\" (concentrado de espodumeno de bajo carbono) que ha firmado múltiples acuerdos de offtake plurianuales. Ha sido mencionada reiteradamente como posible objetivo de adquisición por parte de Tesla."
 },
 "ArcadiumLithium": {
  "founded": 2024,
  "employees": 3000,
  "revenue_2025": "adquisición completada por Rio Tinto por US$6.7B (marzo 2025); ya no cotiza de forma independiente",
  "geo_risk": "Activos clave en Argentina (Olaroz, Fénix) y Australia bajo control de Rio Tinto (no listado en el grafo), sujeto a riesgo de nacionalización de litio en Sudamérica.",
  "desc": "Entidad resultante de la fusión Livent-Allkem, uno de los mayores productores integrados de litio del mundo (roca dura en Australia, salmuera en Argentina, procesamiento en China/EE.UU.). Absorbida por Rio Tinto para consolidar su nueva unidad de litio."
 },
 "SQM": {
  "founded": 1968,
  "employees": 7000,
  "revenue_2025": "ingresos anuales del orden de US$4-5B (negocio combinado de litio y químicos especializados)",
  "geo_risk": "Operaciones en el Salar de Atacama sujetas a la nueva Estrategia Nacional del Litio de Chile y a su joint venture con la estatal Codelco (control estatal creciente).",
  "desc": "Mayor productor de litio de Chile y uno de los mayores del mundo, con operaciones de extracción de salmuera en el Salar de Atacama. En 2025 formalizó una joint venture con Codelco (Novandino Litio) para ampliar capacidad hacia 2030."
 },
 "CommonwealthFusion": {
  "founded": 2018,
  "employees": 1300,
  "revenue_2025": "ronda Serie B2 de US$863M (agosto 2025) con Nvidia, Google y Bill Gates; financiamiento acumulado >US$3B",
  "geo_risk": "Riesgo tecnológico de primero-en-su-clase (reactor SPARC aún no ha alcanzado ganancia neta de energía), concentrado en un único sitio de demostración en Massachusetts.",
  "desc": "Desarrolladora líder de fusión nuclear por confinamiento magnético (tokamak con imanes superconductores de alta temperatura), spinout del MIT. Construye el reactor de demostración SPARC y planea la planta comercial ARC, con fuerte respaldo de gigantes tecnológicos de IA."
 },
 "Helion": {
  "founded": 2013,
  "employees": 300,
  "revenue_2025": "Serie G de US$465M a valuación de US$15.5B; ronda previa Serie F de US$425M",
  "geo_risk": "Tecnología de fusión por confinamiento magnetoinercial aún no demostrada a escala comercial; dependiente de un único cliente ancla de PPA (Microsoft).",
  "desc": "Startup de fusión nuclear (respaldada por Sam Altman) que persigue generación directa de electricidad sin turbina de vapor. Firmó el primer acuerdo de compra de energía de fusión del mundo con Microsoft, con meta de entrega en 2028, y construye su planta Orion en Washington."
 },
 "TAETechnologies": {
  "founded": 1998,
  "employees": 300,
  "revenue_2025": "ronda adicional de US$150M (2025); financiamiento acumulado histórico >US$1.2B; explorando salida a mercados públicos",
  "geo_risk": "Enfoque técnico de fusión aneutrónica (hidrógeno-boro) de muy alto riesgo científico, aún sin reactor de demostración comercial.",
  "desc": "Pionera en fusión nuclear con combustible avanzado hidrógeno-boro (aneutrónico), evitando materiales radiactivos. Google ha sido inversor recurrente desde 2015, reforzando su apuesta en 2025 junto a Commonwealth Fusion."
 },
 "NuScale": {
  "founded": 2007,
  "employees": 600,
  "revenue_2025": "compañía pública (NYSE: SMR), ingresos aún limitados por etapa precomercial de sus reactores modulares pequeños (SMR)",
  "geo_risk": "Dependencia de aprobaciones regulatorias de la NRC y de contratos de despliegue aún no comprometidos en firme; alta volatilidad bursátil.",
  "desc": "Diseñadora del primer reactor modular pequeño (SMR) certificado por la NRC en EE.UU. (VOYGR). Explora activamente contratos para alimentar centros de datos de IA junto con actores de energía avanzada."
 },
 "KairosPower": {
  "founded": 2016,
  "employees": 400,
  "revenue_2025": "ronda Serie C de ~US$629M (2024-25); respaldo de fondos de riesgo y capital estratégico",
  "geo_risk": "Tecnología de reactor refrigerado por sal fundida (Fluoride salt-cooled High-temperature Reactor) aún en fase de demostración (Hermes) en Tennessee.",
  "desc": "Desarrolladora de reactores nucleares avanzados refrigerados por sal fundida, con planta de demostración Hermes en Oak Ridge, Tennessee. Protagonizó en 2025 el primer PPA de energía nuclear Gen IV de EE.UU. junto a Google y TVA."
 },
 "NioCorp": {
  "founded": 2010,
  "employees": 50,
  "revenue_2025": "pre-ingresos (etapa de desarrollo/construcción); financiamiento respaldado por potencial préstamo del DOE/EXIM >US$800M",
  "geo_risk": "Proyecto único (Elk Creek, Nebraska) altamente dependiente de financiamiento gubernamental de EE.UU. para minerales críticos y de la escasez de refinación fuera de China.",
  "desc": "Desarrolladora del único proyecto de niobio permitido en Norteamérica, que también producirá escandio y tierras raras. Recibió fondos del Pentágono junto a contratistas de defensa para tecnología de escandio, clave en aleaciones aeroespaciales de alta resistencia."
 },
 "UraniumEnergy": {
  "founded": 2003,
  "employees": 150,
  "revenue_2025": "ingresos crecientes por ventas de U3O8 (decenas de millones USD); capitalización de mercado ~US$2-3B",
  "geo_risk": "Producción concentrada en EE.UU. (Wyoming, Texas) con exposición a precios volátiles del uranio y a la política de reservas estratégicas de EE.UU.",
  "desc": "Mayor productor de uranio con sede en EE.UU., con operaciones de extracción in-situ (ISR) y reservas físicas de uranio. Se beneficia de la política estadounidense de reducir dependencia de uranio ruso/kazajo y del renovado interés nuclear ligado a IA."
 },
 "Danaher": {
  "founded": 1969,
  "employees": 62000,
  "revenue_2025": "ingresos anuales aprox. US$23-24B (ciencias de la vida, diagnóstico y tecnología de filtración/purificación)",
  "geo_risk": "Alta exposición a gasto de capital cíclico en semiconductores y ciencias de la vida, y a controles de exportación de tecnología de purificación de alta pureza.",
  "desc": "Conglomerado industrial-científico de EE.UU. dueño de Pall Corporation, proveedor crítico de sistemas de filtración de agua ultrapura y gases para fabricación de semiconductores. También abarca ciencias de la vida (Cepheid, Beckman Coulter)."
 },
 "Cohu": {
  "founded": 1947,
  "employees": 1700,
  "revenue_2025": "ingresos anuales aprox. US$350-450M (equipo semicap cíclico)",
  "geo_risk": "Alta dependencia de gasto cíclico de prueba de semiconductores y concentración de ingresos en pocos clientes grandes (Texas Instruments históricamente el mayor).",
  "desc": "Fabricante de equipos de prueba y manejo (handlers) de semiconductores, esencial en la etapa de back-end de fabricación de chips. Sus sistemas se usan ampliamente en pruebas de chips analógicos y de potencia."
 },
 "Zeiss": {
  "founded": 2001,
  "employees": 4000,
  "revenue_2025": "división no reportada por separado; Grupo Zeiss total ~€11B en ingresos anuales",
  "geo_risk": "Proveedor único (monopolio de facto) de óptica EUV para ASML, lo que la convierte en un punto único de falla crítico para toda la industria de litografía avanzada.",
  "desc": "División de Carl Zeiss y proveedor exclusivo de los sistemas ópticos (espejos de precisión atómica) para las máquinas de litografía EUV y DUV de ASML. También ofrece servicios de metrología e inspección/reparación de fotomáscaras a los principales fabricantes de chips."
 },
 "Trumpf": {
  "founded": 1923,
  "employees": 16500,
  "revenue_2025": "ingresos anuales aprox. €5.6-5.9B (año fiscal 2024/25)",
  "geo_risk": "Empresa familiar alemana con fuerte exposición a la industria automotriz europea en desaceleración y a la cadena crítica de litografía EUV, sensible a controles de exportación.",
  "desc": "Fabricante alemán líder de máquinas láser y herramientas de manufactura, proveedor clave del láser de CO2 de alta potencia (\"drive laser\") que genera la luz EUV en los sistemas de litografía de ASML. También suministra sistemas láser de corte/soldadura a industria automotriz y aeroespacial."
 },
 "Satellogic": {
  "founded": 2010,
  "employees": 300,
  "revenue_2025": "ingresos anuales aprox. US$30-40M, en fase de escalado de constelación",
  "geo_risk": "Dependencia de lanzamientos de terceros (SpaceX) y de contratos gubernamentales/defensa, con exposición a tensiones geopolíticas por su alianza de defensa europea con Rheinmetall.",
  "desc": "Operadora de una constelación de satélites de observación terrestre de alta frecuencia, con modelo verticalmente integrado (diseño, fabricación y operación propia de satélites). Se ha expandido hacia aplicaciones de defensa mediante una joint venture con Rheinmetall en Alemania."
 },
 "HughesNetwork": {
  "founded": 1971,
  "employees": 2500,
  "revenue_2025": "~US$1.4-1.5B (segmento Hughes dentro de EchoStar, ingresos por banda ancha en descenso frente a competencia LEO)",
  "geo_risk": "Alta dependencia de un puñado de satélites geoestacionarios de alto valor (single point of failure) y exposición a disputas regulatorias de espectro con operadores LEO como Starlink.",
  "desc": "Hughes Network Systems, subsidiaria de EchoStar, es proveedor líder de banda ancha satelital geoestacionaria (VSAT) para consumidores, empresas, aviación y gobiernos. Opera la flota de satélites Jupiter y enfrenta presión competitiva creciente de constelaciones de órbita baja."
 },
 "Orbcomm": {
  "founded": 1993,
  "employees": 700,
  "revenue_2025": "~US$300M (privada tras adquisición por Bain Capital/GI Partners en 2021)",
  "geo_risk": "Concentración en un pequeño número de satélites propios y dependencia de terceros para lanzamiento; riesgo de interferencia de espectro en bandas IoT compartidas.",
  "desc": "ORBCOMM es proveedor líder de soluciones IoT industrial satelital y celular para rastreo de activos en transporte, marítimo, agrícola y maquinaria pesada. Opera constelaciones propias (OG2/OGx) además de asociarse con redes celulares terrestres."
 },
 "IntuitiveMachines": {
  "founded": 2013,
  "employees": 350,
  "revenue_2025": "~US$228M (ingresos reportados FY2025, contratos NASA CLPS)",
  "geo_risk": "Dependencia crítica de contratos NASA (CLPS) y de un único proveedor de lanzamiento; riesgo técnico alto de misiones lunares (2 de 3 alunizajes con anomalías).",
  "desc": "Intuitive Machines es una empresa de servicios lunares que desarrolla el módulo de alunizaje Nova-C bajo el programa NASA CLPS (Commercial Lunar Payload Services). También construye satélites de relevo de datos lunares y sistemas de soporte vital para futuras misiones Artemis."
 },
 "SierraSpace": {
  "founded": 2021,
  "employees": 1900,
  "revenue_2025": "Valoración ~US$5.3B tras ronda Serie B 2024 (ingresos no públicos, privada)",
  "geo_risk": "Riesgo de retraso técnico en el primer vuelo orbital del Dream Chaser y dependencia de un único vehículo de lanzamiento certificado.",
  "desc": "Sierra Space desarrolla el vehículo espacial reutilizable Dream Chaser para reabastecer la ISS y la futura estación comercial Orbital Reef. Es una de las empresas mejor capitalizadas del \"New Space\" tras levantar más de US$1.7B en capital privado."
 },
 "AxiomSpace": {
  "founded": 2016,
  "employees": 900,
  "revenue_2025": "Valoración ~US$2.5-3.4B (ronda de US$350M en 2026, privada)",
  "geo_risk": "Dependencia total de SpaceX para acceso tripulado a la ISS y riesgo de cronograma en el desarrollo de su propia estación espacial comercial.",
  "desc": "Axiom Space construye módulos de estación espacial comercial que se acoplarán a la ISS y opera misiones privadas tripuladas (Ax-1 a Ax-4) en colaboración con NASA. Busca convertirse en sucesora comercial de la ISS antes de su retiro."
 },
 "PowerchipSemi": {
  "founded": 1994,
  "employees": 6000,
  "revenue_2025": "~US$1.2-1.5B (foundry, Taiwán)",
  "geo_risk": "Alta exposición geopolítica en el estrecho de Taiwán y competencia intensa de fundiciones chinas subvencionadas en nodos maduros.",
  "desc": "Powerchip Semiconductor Manufacturing Corporation (PSMC) es una fundición taiwanesa especializada en nodos maduros (DRAM legacy, memoria NOR, chips de potencia). Ha expandido su modelo de transferencia tecnológica a India y Japón como socio de fabricación."
 },
 "Vedanta_Semi": {
  "founded": 2022,
  "revenue_2025": "N/D (sin fab operativa aún; el proyecto original de US$19.5B fue abandonado por Foxconn)",
  "geo_risk": "Muy alto: el socio tecnológico y de capital original (Foxconn) se retiró en 2023, dejando el proyecto de fab india sin planta operativa confirmada.",
  "desc": "Vedanta-Foxconn Semi fue una joint venture anunciada en 2022 para construir la primera fábrica de semiconductores de India en Gujarat. Foxconn abandonó el proyecto en julio de 2023 citando falta de avance, y Vedanta ha buscado desde entonces nuevos socios tecnológicos."
 },
 "Seagate": {
  "founded": 1978,
  "employees": 40000,
  "revenue_2025": "~US$9.6B (año fiscal 2025, impulsado por discos HAMR para IA)",
  "geo_risk": "Concentración de manufactura en el sudeste asiático (Tailandia, Singapur, China) expuesta a disrupciones de cadena de suministro y aranceles.",
  "desc": "Seagate Technology es uno de los dos mayores fabricantes mundiales de discos duros (HDD), con fuerte crecimiento reciente gracias a su tecnología HAMR de alta densidad para almacenamiento masivo en centros de datos de IA. Sus clientes hiperescala representan una porción creciente de sus ingresos."
 },
 "IronMountain": {
  "founded": 1951,
  "employees": 28000,
  "revenue_2025": "~US$6.4B (REIT, incluyendo negocio creciente de data centers)",
  "geo_risk": "Transición desde almacenamiento físico de documentos hacia data centers intensivos en capital, con riesgo de ejecución y competencia de REITs especializados como Equinix/Digital Realty.",
  "desc": "Iron Mountain es un REIT global históricamente enfocado en gestión de información física, que ha diversificado agresivamente hacia centros de datos de colocación para clientes hiperescala e IA. Su segmento de data centers crece de forma acelerada desde 2023."
 },
 "CyrusOne": {
  "founded": 2001,
  "employees": 1400,
  "revenue_2025": "privada tras compra por KKR/GIP en 2022 (~US$15B); ingresos anuales estimados ~US$1B+",
  "geo_risk": "Alta dependencia de un número reducido de clientes hiperescala y necesidad intensiva de capital para expansión ligada a IA, con riesgo de suministro eléctrico en mercados saturados (Virginia del Norte).",
  "desc": "CyrusOne es un operador global de centros de datos de colocación e hyperscale, propiedad de KKR y Global Infrastructure Partners desde 2022. Sus instalaciones alojan cargas de trabajo de nube y entrenamiento de IA para los mayores operadores tecnológicos del mundo."
 },
 "Cerebras": {
  "founded": 2016,
  "employees": 500,
  "revenue_2025": "~US$580M ARR estimado (con IPO presentada en 2026, valoración objetivo ~US$8B)",
  "geo_risk": "Dependencia crítica de un único proveedor de fabricación (TSMC) para su chip wafer-scale gigante, y concentración de ingresos en pocos clientes (G42, OpenAI).",
  "desc": "Cerebras Systems fabrica el chip de IA más grande del mundo (Wafer Scale Engine) y ofrece servicios de inferencia y entrenamiento en la nube como alternativa a Nvidia. Firmó un acuerdo histórico de cómputo con OpenAI valorado en hasta US$10.000 millones."
 },
 "Penguin_Solutions": {
  "founded": 1998,
  "employees": 1500,
  "revenue_2025": "~US$400M anuales (fiscal 2025)",
  "geo_risk": "Concentración de ingresos en pocos clientes de infraestructura de IA (CoreWeave y similares) y dependencia de memoria/componentes de Micron.",
  "desc": "Penguin Solutions diseña e integra clústeres de cómputo de alto rendimiento (HPC) y servidores de IA a medida (ODM), además de fabricar módulos de memoria especializados a través de su unidad SMART Modular. Es proveedor clave de infraestructura para neoclouds de IA."
 },
 "Sycamore": {
  "founded": 1998,
  "employees": 10,
  "revenue_2025": "N/D — negocio óptico vendido a Marlin Equity Partners/Coriant en 2013; entidad remanente sin operaciones comerciales activas",
  "geo_risk": "Empresa efectivamente disuelta operativamente: todo el riesgo reside en litigios residuales y liquidación de activos, no en operaciones activas.",
  "desc": "Sycamore Networks fue pionera de equipos de conmutación óptica durante el boom de internet, alcanzando una capitalización de mercado de más de US$40.000 millones en 2000. Vendió su negocio de networking óptico a Marlin Equity Partners en 2013 y cesó operaciones comerciales activas poco después."
 },
 "Silicom": {
  "founded": 1987,
  "employees": 250,
  "revenue_2025": "~US$85-95M (ingresos anuales estimados, Q3 2025 reportado)",
  "geo_risk": "Alta concentración de ingresos en pocos clientes OEM de ciberseguridad y networking; sede y desarrollo en Israel expuestos a riesgo geopolítico regional.",
  "desc": "Silicom Ltd. diseña adaptadores de red, SmartNICs y appliances de conectividad para proveedores de ciberseguridad, telecomunicaciones y edge computing. Vende principalmente como fabricante OEM integrado en las plataformas de sus clientes."
 },
 "Calix": {
  "founded": 1999,
  "employees": 1500,
  "revenue_2025": "~US$800M (ingresos anuales estimados FY2025)",
  "geo_risk": "Dependencia de gasto de capital de operadores de banda ancha regionales pequeños/rurales en EE.UU., sensible a ciclos de subsidios gubernamentales (BEAD).",
  "desc": "Calix provee plataformas de software y hardware de acceso de banda ancha (fibra, cable) a operadores de telecomunicaciones regionales y rurales, con una plataforma \"Calix One\" que incorpora funciones de IA para gestión de red."
 },
 "Calix_Net": {
  "founded": 1984,
  "employees": 2300,
  "revenue_2025": "~US$850-900M (ingresos anuales)",
  "geo_risk": "Dependencia de gasto en ciberseguridad/observabilidad de grandes operadores de telecomunicaciones y nube, sensible a recortes de presupuesto TI.",
  "desc": "NetScout Systems provee soluciones de visibilidad, monitoreo de rendimiento de red y ciberseguridad (DDoS) para operadores de telecomunicaciones, empresas y proveedores de nube. Su tecnología de inspección profunda de paquetes es usada para asegurar infraestructuras 5G y de data centers de IA."
 },
 "Lightsource_BP": {
  "founded": 2010,
  "employees": 1400,
  "revenue_2025": "~US$1.2-1.5B (desarrollador de proyectos, cifra de ingresos por ventas de energía y desarrollo estimada)",
  "geo_risk": "Exposición a cambios regulatorios de incentivos solares y a cadenas de suministro de paneles solares afectadas por aranceles y controles de origen (Xinjiang).",
  "desc": "Lightsource bp es uno de los mayores desarrolladores de energía solar a escala de servicios públicos del mundo, con más de 25GW en desarrollo. Firma contratos corporativos de compra de energía (PPA) directamente con grandes consumidores tecnológicos para descarbonizar sus operaciones de centros de datos."
 },
 "NexTracker": {
  "founded": 2013,
  "employees": 3000,
  "revenue_2025": "~US$2.1-2.2B (año fiscal 2025)",
  "geo_risk": "Exposición a aranceles sobre componentes solares importados y a la volatilidad de la política de créditos fiscales (IRA) en EE.UU.",
  "desc": "Nextracker es el mayor fabricante mundial de sistemas de seguimiento solar (trackers) para plantas fotovoltaicas de gran escala, con fuerte enfoque reciente en contenido 100% doméstico estadounidense para calificar a incentivos fiscales."
 },
 "Array_Technologies": {
  "founded": 1989,
  "employees": 1100,
  "revenue_2025": "~US$1.3-1.4B (ingresos anuales estimados 2025)",
  "geo_risk": "Exposición similar a Nextracker: dependencia de créditos fiscales de contenido doméstico y cadenas de suministro de acero/paneles solares.",
  "desc": "Array Technologies es el segundo mayor fabricante de sistemas de seguimiento solar de EE.UU., superando los 100GW en entregas acumuladas. Compite directamente con Nextracker por contratos de proyectos solares utility-scale de gran escala."
 },
 "WiTricity": {
  "founded": 2007,
  "employees": 150,
  "revenue_2025": "privada, valoración estimada >US$1B tras rondas con Siemens y otros inversores estratégicos",
  "geo_risk": "Dependencia de licenciamiento de propiedad intelectual a terceros fabricantes para generar ingresos, con riesgo de adopción lenta de la carga inalámbrica en el mercado automotriz masivo.",
  "desc": "WiTricity desarrolla y licencia tecnología de transferencia de energía inalámbrica basada en resonancia magnética, utilizada en carga de vehículos eléctricos. Licencia su propiedad intelectual a fabricantes de componentes automotrices e industriales en lugar de fabricar directamente."
 },
 "GE_Aerospace": {
  "founded": 1917,
  "employees": 52000,
  "revenue_2025": "~US$40.000M (ingresos anuales FY2025)",
  "geo_risk": "Cuellos de botella persistentes en la cadena de suministro de componentes de motores (fundición, forja) que limitan la producción y afectan la relación con Boeing y Airbus.",
  "desc": "GE Aerospace es uno de los mayores fabricantes de motores de aviación del mundo, proveedor clave de Boeing y Airbus a través de su joint venture CFM International con Safran. Tras separarse de General Electric en 2024, se enfoca exclusivamente en propulsión aeroespacial y defensa."
 },
 "Pegatron": {
  "founded": 2008,
  "employees": 90000,
  "revenue_2025": "~US$40.000-45.000M (ingresos anuales estimados 2025)",
  "geo_risk": "Alta concentración de ingresos en un único cliente (Apple, ~50% de ventas) y exposición a diversificación de manufactura fuera de China por tensiones comerciales EE.UU.-China.",
  "desc": "Pegatron es uno de los mayores fabricantes por contrato (ODM/EMS) del mundo, ensamblador clave de iPhones para Apple. Ha diversificado hacia el ensamblaje de servidores de IA y componentes de redes, expandiendo capacidad en Vietnam, India y México."
 }
};
if (typeof NODE_META !== 'undefined') { for (var _k5 in META_EXPAND5) {
  NODE_META[_k5] = Object.assign({}, NODE_META[_k5] || {}, META_EXPAND5[_k5]); } }
window.META_EXPAND5 = META_EXPAND5;

// categorías nuevas de primera clase (el resto de la cola larga mapea a canónicas)
if (typeof CATS_NEW !== 'undefined') Object.assign(CATS_NEW, {"power_ipp": {"label": "Energía IPP / PPA", "en": "Power IPP / PPA", "cssVar": "--c-power_ipp", "x": 0.06}, "osat": {"label": "Empaquetado / OSAT", "en": "Packaging / OSAT", "cssVar": "--c-osat", "x": 0.12}, "defense_prime": {"label": "Defensa Prime", "en": "Defense Primes", "cssVar": "--c-defense_prime", "x": 0.58}});
if (typeof CAT_TO_SECTOR !== 'undefined') Object.assign(CAT_TO_SECTOR, {"power_ipp": "energia", "osat": "fabricacion", "defense_prime": "defensa"});
if (typeof document !== 'undefined') { var _cc5 = {"--c-power_ipp": "#B8E356", "--c-osat": "#FFA94D", "--c-defense_prime": "#FF6B8A"};
  for (var _v5 in _cc5) document.documentElement.style.setProperty(_v5, _cc5[_v5]); }
