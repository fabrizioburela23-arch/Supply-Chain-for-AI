// nodes/links_connect.js — Conexiones de cadena de suministro para nodos huérfanos
// Conecta los ~82 nodos que se habían añadido (expand2/expand3) sin enlaces,
// con relaciones reales verificadas. Formato: {s, t, w, rel, type}
// Convención (igual que links_expand.js): s = empresa, t = aquello de lo que depende
//   (proveedor/fab/cloud/licencia aguas arriba) o su cliente (deploy/customer).
// type ∈ supply | fab | license | cloud | invest | deploy | partner | owns

var LINKS_CONNECT = [

  // ── FABLESS (diseñadores de chips: fab en TSMC/Samsung, EDA, clientes) ──────
  {s:"Achronix",        t:"TSMC",          w:3, rel:"Fabrica sus FPGA en TSMC",                       type:"fab"},
  {s:"Achronix",        t:"Synopsys",      w:2, rel:"Diseña con herramientas EDA de Synopsys",        type:"license"},
  {s:"Microsoft",       t:"Achronix",      w:2, rel:"FPGAs para aceleración en data center",          type:"supply"},

  {s:"Apple",           t:"Arm_Holdings",  w:5, rel:"Licencia la ISA ARM para sus chips A/M",         type:"license"},
  {s:"Qualcomm",        t:"Arm_Holdings",  w:5, rel:"Licencia núcleos ARM para Snapdragon",           type:"license"},
  {s:"Nvidia",          t:"Arm_Holdings",  w:4, rel:"CPU Grace basada en ARM",                        type:"license"},
  {s:"Samsung",         t:"Arm_Holdings",  w:4, rel:"Exynos sobre arquitectura ARM",                  type:"license"},
  {s:"MediaTek",        t:"Arm_Holdings",  w:4, rel:"Dimensity sobre núcleos ARM",                    type:"license"},

  {s:"Qualcomm",        t:"CEVA",          w:2, rel:"Licencia DSP IP de CEVA",                         type:"license"},
  {s:"MediaTek",        t:"CEVA",          w:2, rel:"IP de conectividad y DSP",                        type:"license"},
  {s:"Samsung",         t:"Ceva",          w:2, rel:"Licencia IP de DSP/Bluetooth",                    type:"license"},

  {s:"FlexLogix",       t:"TSMC",          w:2, rel:"eFPGA embebida fabricada en TSMC",                type:"fab"},
  {s:"Boeing",          t:"FlexLogix",     w:2, rel:"FPGA reconfigurable para aeroespacial",           type:"supply"},

  {s:"Himax_Tech",      t:"TSMC",          w:3, rel:"Fabrica drivers de display en TSMC",             type:"fab"},
  {s:"Himax_Tech",      t:"Samsung",       w:2, rel:"Capacidad de foundry adicional",                 type:"fab"},

  {s:"Indie",           t:"TSMC",          w:2, rel:"Chips automotrices fabricados en TSMC",          type:"fab"},
  {s:"BMW",             t:"Indie",         w:2, rel:"Semiconductores para ADAS",                      type:"supply"},
  {s:"Indie_Semi",      t:"TSMC",          w:2, rel:"SoC automotriz fabricado en TSMC",               type:"fab"},
  {s:"Stellantis",      t:"Indie_Semi",    w:2, rel:"Chips para sistemas del vehículo",               type:"supply"},

  {s:"Lattice",         t:"Samsung",       w:3, rel:"FPGA de bajo consumo en Samsung Foundry",        type:"fab"},
  {s:"Lattice",         t:"TSMC",          w:2, rel:"Capacidad de foundry adicional",                 type:"fab"},
  {s:"Microsoft",       t:"Lattice",       w:2, rel:"FPGA para seguridad de servidores",              type:"supply"},

  {s:"Microchip_Tech",  t:"TSMC",          w:3, rel:"Complementa fabs propias con TSMC",              type:"fab"},
  {s:"BMW",             t:"Microchip_Tech",w:2, rel:"Microcontroladores automotrices",                type:"supply"},

  {s:"NXP",             t:"TSMC",          w:4, rel:"Procesadores automotrices en TSMC",              type:"fab"},
  {s:"NXP",             t:"GlobalFoundries",w:3,rel:"Capacidad de nodos maduros",                     type:"fab"},
  {s:"BMW",             t:"NXP",           w:3, rel:"Chips para powertrain y ADAS",                   type:"supply"},
  {s:"Tesla",           t:"NXP",           w:3, rel:"Microcontroladores del vehículo",                type:"supply"},

  {s:"Micron",          t:"Rambus",        w:2, rel:"Licencia IP de interfaz de memoria",             type:"license"},
  {s:"SKHynix",         t:"Rambus",        w:2, rel:"IP de memoria de alto ancho de banda",           type:"license"},
  {s:"Samsung",         t:"Rambus",        w:2, rel:"Licencia de IP de memoria",                      type:"license"},

  {s:"Renesas",         t:"TSMC",          w:3, rel:"Complementa fabs propias con TSMC",              type:"fab"},
  {s:"BMW",             t:"Renesas",       w:3, rel:"Microcontroladores automotrices",                type:"supply"},
  {s:"Hyundai",         t:"Renesas",       w:2, rel:"Chips para el vehículo",                         type:"supply"},

  {s:"STMicro",         t:"TSMC",          w:2, rel:"Capacidad de foundry adicional",                 type:"fab"},
  {s:"Apple",           t:"STMicro",       w:2, rel:"Sensores y chips de potencia",                   type:"supply"},
  {s:"Tesla",           t:"STMicro",       w:3, rel:"SiC para inversores de potencia",                type:"supply"},

  {s:"Tesla",           t:"Sensata",       w:2, rel:"Sensores para el vehículo eléctrico",            type:"supply"},
  {s:"BMW",             t:"Sensata",       w:2, rel:"Sensores de presión y temperatura",              type:"supply"},

  {s:"Silicon_Labs",    t:"TSMC",          w:2, rel:"Chips IoT fabricados en TSMC",                   type:"fab"},
  {s:"Amazon",          t:"Silicon_Labs",  w:2, rel:"SoC inalámbricos para dispositivos IoT",         type:"supply"},

  // ── FOUNDRY (dependen de equipos ASML/AMAT/Lam/TEL; sirven a fabless) ───────
  {s:"TataSemiconductor",t:"ASML",         w:3, rel:"Litografía para su nueva fab en India",          type:"supply"},
  {s:"TataSemiconductor",t:"AMAT",         w:2, rel:"Equipos de deposición y grabado",                type:"supply"},
  {s:"TowerSemi",       t:"AMAT",          w:2, rel:"Equipos para nodos analógicos",                  type:"supply"},
  {s:"Broadcom",        t:"TowerSemi",     w:2, rel:"Foundry para chips analógicos/RF",               type:"fab"},
  {s:"Vedanta_Semi",    t:"ASML",          w:2, rel:"Litografía para fab India (Foxconn JV)",         type:"supply"},
  {s:"X_Fab",           t:"AMAT",          w:2, rel:"Equipos para foundry de SiC",                    type:"supply"},
  {s:"Tesla",           t:"X_Fab",         w:2, rel:"Foundry para chips de potencia",                 type:"fab"},

  // ── EQUIP (proveen equipos a TSMC/Samsung/Intel) ───────────────────────────
  {s:"Samsung",         t:"ACM_Research",  w:2, rel:"Equipos de limpieza de obleas",                  type:"supply"},
  {s:"TSMC",            t:"ACM_Research",  w:2, rel:"Limpieza húmeda de obleas",                      type:"supply"},
  {s:"TSMC",            t:"Aehr_Test",     w:2, rel:"Sistemas de burn-in y test",                     type:"supply"},
  {s:"Intel",           t:"Aehr_Test",    w:2, rel:"Test de fiabilidad de chips",                    type:"supply"},
  {s:"Samsung",         t:"Cohu",          w:2, rel:"Equipos de handling y test",                     type:"supply"},
  {s:"TSMC",            t:"Onto_Innovation",w:2,rel:"Metrología e inspección óptica",                 type:"supply"},
  {s:"Samsung",         t:"Onto_Innovation",w:2,rel:"Inspección de packaging avanzado",              type:"supply"},
  {s:"AMAT",            t:"Ultra_Clean",   w:3, rel:"Subsistemas y módulos críticos",                 type:"supply"},
  {s:"Lam",             t:"Ultra_Clean",   w:3, rel:"Componentes para equipos de grabado",            type:"supply"},

  // ── POWER (analógico/RF/potencia: fab TSMC, clientes Apple/auto/DC) ─────────
  {s:"Allegro_Micro",   t:"TSMC",          w:2, rel:"Sensores de corriente en TSMC",                  type:"fab"},
  {s:"Tesla",           t:"Allegro_Micro", w:2, rel:"Sensores Hall para motores",                     type:"supply"},
  {s:"Monolithic_Power",t:"TSMC",          w:3, rel:"PMIC fabricados en TSMC",                        type:"fab"},
  {s:"Nvidia",          t:"Monolithic_Power",w:3,rel:"Gestión de energía para GPU/servidores",        type:"supply"},
  {s:"Navitas",         t:"TSMC",          w:2, rel:"GaN/SiC fabricado en TSMC",                      type:"fab"},
  {s:"Tesla",           t:"Navitas",       w:2, rel:"Semiconductores GaN para carga",                 type:"supply"},
  {s:"Qorvo",           t:"TSMC",          w:3, rel:"Front-end RF fabricado en TSMC",                 type:"fab"},
  {s:"Apple",           t:"Qorvo",         w:4, rel:"Módulos RF para iPhone",                         type:"supply"},
  {s:"Samsung",         t:"Qorvo",         w:2, rel:"RF para Galaxy",                                 type:"supply"},
  {s:"Richtek",         t:"TSMC",          w:2, rel:"PMIC fabricados en TSMC",                        type:"fab"},
  {s:"MediaTek",        t:"Richtek",       w:2, rel:"Gestión de energía para SoC",                    type:"supply"},
  {s:"BMW",             t:"Rohm",          w:2, rel:"SiC para inversores EV",                         type:"supply"},
  {s:"Hyundai",         t:"Rohm",          w:2, rel:"Semiconductores de potencia",                    type:"supply"},
  {s:"Skyworks",        t:"TSMC",          w:3, rel:"Front-end RF fabricado en TSMC",                 type:"fab"},
  {s:"Apple",           t:"Skyworks",      w:4, rel:"Amplificadores RF para iPhone",                  type:"supply"},

  // ── MEMORY ─────────────────────────────────────────────────────────────────
  {s:"Nanya",           t:"AMAT",          w:2, rel:"Equipos para DRAM",                              type:"supply"},
  {s:"Foxconn",         t:"Nanya",         w:2, rel:"DRAM para ensamblaje",                           type:"supply"},
  {s:"MediaTek",        t:"Winbond",       w:2, rel:"Memoria especializada para SoC",                 type:"supply"},
  {s:"Winbond",         t:"TSMC",          w:2, rel:"Capacidad de foundry adicional",                 type:"fab"},

  // ── NEUROMORPHIC ───────────────────────────────────────────────────────────
  {s:"GrAI_Matter",     t:"TSMC",          w:2, rel:"Chips neuromórficos en TSMC",                    type:"fab"},
  {s:"Prophesee",       t:"TSMC",          w:2, rel:"Sensores de visión por eventos",                 type:"fab"},
  {s:"Qualcomm",        t:"Prophesee",     w:2, rel:"Sensado por eventos para móvil",                 type:"partner"},
  {s:"Rain_Neuromorphics",t:"TSMC",        w:2, rel:"Chips analógicos in-memory en TSMC",             type:"fab"},
  {s:"OpenAI",          t:"Rain_Neuromorphics",w:2,rel:"Inversión en hardware neuromórfico",          type:"invest"},

  // ── ASIC CUSTOM ────────────────────────────────────────────────────────────
  {s:"BroadcomASIC",    t:"TSMC",          w:5, rel:"ASIC de IA fabricados en TSMC",                  type:"fab"},
  {s:"Alphabet",        t:"BroadcomASIC",  w:5, rel:"Co-diseño de los TPU de Google",                 type:"supply"},
  {s:"Meta",            t:"BroadcomASIC",  w:4, rel:"ASIC MTIA para inferencia",                      type:"supply"},
  {s:"Etched",          t:"TSMC",          w:3, rel:"ASIC de transformers (Sohu) en TSMC",            type:"fab"},
  {s:"Anthropic",       t:"Etched",        w:2, rel:"Aceleradores de inferencia de transformers",     type:"supply"},
  {s:"Graphcore",       t:"TSMC",          w:3, rel:"IPU fabricadas en TSMC",                         type:"fab"},
  {s:"Graphcore",       t:"SoftBank",      w:3, rel:"Adquirida por SoftBank (2024)",                  type:"owns"},

  // ── EDGE AI ────────────────────────────────────────────────────────────────
  {s:"Esperanto_Tech",  t:"TSMC",          w:2, rel:"Chips RISC-V para IA en TSMC",                   type:"fab"},

  // ── PHOTONICS ──────────────────────────────────────────────────────────────
  {s:"Coherus_Bio",     t:"TSMC",          w:2, rel:"Fotónica de silicio en TSMC",                    type:"fab"},
  {s:"Nvidia",          t:"Coherus_Bio",   w:2, rel:"Óptica co-empaquetada para switches",            type:"supply"},
  {s:"InfiniteraNet",   t:"TSMC",          w:2, rel:"DSP ópticos coherentes en TSMC",                 type:"fab"},
  {s:"Amazon",          t:"InfiniteraNet", w:2, rel:"Transporte óptico para data centers",            type:"supply"},

  // ── EDA / máscaras ─────────────────────────────────────────────────────────
  {s:"Nvidia",          t:"Altium",        w:2, rel:"Diseño de PCB para placas",                      type:"license"},
  {s:"Apple",           t:"Altium",        w:2, rel:"Herramientas de diseño de PCB",                  type:"license"},
  {s:"TSMC",            t:"PDF_Solutions", w:2, rel:"Analítica de rendimiento de fab",                type:"license"},
  {s:"Samsung",         t:"PDF_Solutions", w:2, rel:"Optimización de yield",                         type:"license"},
  {s:"TSMC",            t:"Photronics",    w:3, rel:"Fotomáscaras para litografía",                   type:"supply"},
  {s:"Samsung",         t:"Photronics",    w:2, rel:"Máscaras para procesos avanzados",               type:"supply"},

  // ── SUBSTRATES / CHEMICALS ─────────────────────────────────────────────────
  {s:"Intel",           t:"Shinko_Electric",w:3,rel:"Sustratos de packaging avanzado",               type:"supply"},
  {s:"TSMC",            t:"Shinko_Electric",w:2,rel:"Sustratos para CoWoS",                          type:"supply"},
  {s:"TSMC",            t:"Cabot_Micro",   w:3, rel:"Slurry de CMP para pulido",                      type:"supply"},
  {s:"Samsung",         t:"Cabot_Micro",   w:2, rel:"Consumibles de CMP",                            type:"supply"},
  {s:"Intel",           t:"Cabot_Micro",   w:2, rel:"Materiales de pulido CMP",                       type:"supply"},

  // ── HPC / SUPERCOMPUTING ───────────────────────────────────────────────────
  {s:"FujitsuHPC",      t:"Arm_Holdings",  w:3, rel:"CPU A64FX (Fugaku) basada en ARM",               type:"license"},
  {s:"FujitsuHPC",      t:"TSMC",          w:2, rel:"Fabrica sus CPU HPC en TSMC",                    type:"fab"},
  {s:"Penguin_Solutions",t:"Nvidia",       w:3, rel:"Integra clusters de GPU Nvidia",                 type:"supply"},
  {s:"Together_AI",     t:"Nvidia",        w:3, rel:"Cloud de GPU para entrenamiento",                type:"supply"},
  {s:"Together_AI",     t:"Amazon",        w:2, rel:"Infraestructura cloud complementaria",           type:"cloud"},

  // ── SERVERS / ODM ──────────────────────────────────────────────────────────
  {s:"Nvidia",          t:"Modine",        w:2, rel:"Refrigeración térmica para racks GPU",           type:"supply"},
  {s:"Microsoft",       t:"Modine",        w:2, rel:"Soluciones de enfriamiento de DC",               type:"supply"},
  {s:"Apple",           t:"Pegatron",      w:3, rel:"Ensamblaje de productos",                        type:"supply"},
  {s:"Nvidia",          t:"Quanta_Computer",w:4,rel:"ODM de servidores DGX/HGX",                      type:"supply"},
  {s:"Amazon",          t:"Quanta_Computer",w:3,rel:"Servidores para AWS",                            type:"supply"},
  {s:"Nvidia",          t:"Supermicro_Liquid",w:3,rel:"Servidores con refrigeración líquida",         type:"supply"},
  {s:"Microsoft",       t:"Supermicro_Liquid",w:2,rel:"Racks GPU para Azure",                         type:"supply"},
  {s:"Nvidia",          t:"Wistron",       w:3, rel:"ODM de placas y servidores GPU",                 type:"supply"},
  {s:"Apple",           t:"Wistron",       w:2, rel:"Ensamblaje de dispositivos",                     type:"supply"},

  // ── ROBOTICS / INDUSTRIAL ──────────────────────────────────────────────────
  {s:"BMW",             t:"ABB_Robotics",  w:3, rel:"Robots de línea de ensamblaje",                  type:"supply"},
  {s:"ABB_Robotics",    t:"Nvidia",        w:2, rel:"Isaac para IA de robots",                        type:"partner"},
  {s:"Fanuc",           t:"Nvidia",        w:2, rel:"IA para automatización industrial",              type:"partner"},
  {s:"Tesla",           t:"Fanuc",         w:3, rel:"Robots para Gigafactory",                        type:"supply"},
  {s:"Foxconn",         t:"Fanuc",         w:3, rel:"Robots de ensamblaje",                           type:"supply"},
  {s:"Yaskawa",         t:"Nvidia",        w:2, rel:"IA para robótica colaborativa",                  type:"partner"},
  {s:"BMW",             t:"Yaskawa",       w:2, rel:"Servomotores y robots",                          type:"supply"},

  // ── AI AUTO ────────────────────────────────────────────────────────────────
  {s:"Joby_Aviation",   t:"Nvidia",        w:2, rel:"Cómputo para autonomía eVTOL",                   type:"supply"},
  {s:"Joby_Aviation",   t:"Qualcomm",      w:2, rel:"Conectividad y cómputo embebido",                type:"partner"},
  {s:"Wayve",           t:"Nvidia",        w:3, rel:"GPU para conducción autónoma E2E",               type:"supply"},
  {s:"Wayve",           t:"SoftBank",      w:3, rel:"Inversión líder Serie C",                        type:"invest"},
  {s:"Wayve",           t:"Microsoft",     w:2, rel:"Azure para entrenamiento",                       type:"cloud"},

  // ── AI DEFENSE ─────────────────────────────────────────────────────────────
  {s:"AeroVironment",   t:"Nvidia",        w:2, rel:"Cómputo de IA para drones",                      type:"supply"},
  {s:"AeroVironment",   t:"Palantir",      w:2, rel:"Software de misión",                             type:"partner"},
  {s:"BoozAllen",       t:"Palantir",      w:3, rel:"Integrador de plataformas Palantir",             type:"partner"},
  {s:"BoozAllen",       t:"Amazon",        w:2, rel:"Cloud gubernamental (AWS GovCloud)",             type:"cloud"},
  {s:"Kratos",          t:"Nvidia",        w:2, rel:"Cómputo para sistemas autónomos",                type:"supply"},
  {s:"Kratos",          t:"Boeing",        w:2, rel:"Drones colaborativos de combate",               type:"partner"},

  // ── AI FINANCE / HEALTH / LAB / SOFT ───────────────────────────────────────
  {s:"Crane_NXT",       t:"Microsoft",     w:2, rel:"Cloud para soluciones fintech",                  type:"cloud"},
  {s:"TempusAI",        t:"Alphabet",      w:3, rel:"Google Cloud para genómica",                     type:"cloud"},
  {s:"TempusAI",        t:"Nvidia",        w:2, rel:"GPU para modelos clínicos",                      type:"supply"},
  {s:"Cohere_AI",       t:"Nvidia",        w:3, rel:"GPU para entrenar LLM empresariales",            type:"supply"},
  {s:"Cohere_AI",       t:"Alphabet",      w:2, rel:"Google Cloud como infraestructura",              type:"cloud"},
  {s:"HuggingFace",     t:"Amazon",        w:3, rel:"AWS como socio de despliegue",                   type:"cloud"},
  {s:"HuggingFace",     t:"Nvidia",        w:3, rel:"GPU para el hub de modelos",                     type:"supply"},
  {s:"Scale_AI",        t:"Meta",          w:3, rel:"Etiquetado de datos; Meta invirtió (2025)",      type:"invest"},
  {s:"OpenAI",          t:"Scale_AI",      w:3, rel:"Datos de entrenamiento etiquetados",             type:"supply"},

  // ── EARTH OBS / SATELLITE / SPACE ──────────────────────────────────────────
  {s:"Maxar",           t:"SpaceX",        w:3, rel:"Lanza sus satélites con SpaceX",                 type:"supply"},
  {s:"Maxar",           t:"Palantir",      w:2, rel:"Imágenes para análisis geoespacial",             type:"partner"},
  {s:"Spire_Global",    t:"SpaceX",        w:3, rel:"Lanzamiento de nanosatélites",                   type:"supply"},
  {s:"EutelsatOneWeb",  t:"SpaceX",        w:3, rel:"Parte de la constelación lanzada por SpaceX",    type:"supply"},
  {s:"EutelsatOneWeb",  t:"Airbus",        w:3, rel:"Airbus fabrica los satélites OneWeb",            type:"supply"},
  {s:"HughesNetwork",   t:"SpaceX",        w:2, rel:"Capacidad complementaria de banda",              type:"partner"},
  {s:"Orbcomm",         t:"SpaceX",        w:2, rel:"Lanzamiento de satélites IoT",                   type:"supply"},
  {s:"SES",             t:"SpaceX",        w:3, rel:"Lanza su constelación O3b mPOWER",               type:"supply"},
  {s:"SES",             t:"Boeing",        w:2, rel:"Boeing fabrica satélites GEO",                   type:"supply"},
  {s:"Amazon",          t:"BlueOrigin",    w:3, rel:"Lanza satélites Kuiper en New Glenn",            type:"deploy"},
  {s:"BlueOrigin",      t:"Boeing",        w:2, rel:"Socios en ULA (motores BE-4)",                   type:"partner"},

  // ── BATTERY / RARE EARTH ───────────────────────────────────────────────────
  {s:"Tesla",           t:"PiedmontLithium",w:3,rel:"Litio para baterías",                            type:"supply"},
  {s:"BMW",             t:"Umicore",       w:3, rel:"Materiales catódicos para baterías",             type:"supply"},
  {s:"Hyundai",         t:"Umicore",       w:2, rel:"Cátodos para vehículos eléctricos",              type:"supply"},
  {s:"Tesla",           t:"Energy_Fuels",  w:2, rel:"Tierras raras para imanes de motor",             type:"supply"},
  {s:"Boeing",          t:"Energy_Fuels",  w:2, rel:"Tierras raras para defensa/aero",                type:"supply"},

  // ── QUANTUM INFRA ──────────────────────────────────────────────────────────
  {s:"IBMQuantum",      t:"Oxford_Instruments",w:3,rel:"Criostatos de dilución para qubits",          type:"supply"},
  {s:"Rigetti",         t:"Oxford_Instruments",w:2,rel:"Refrigeración criogénica",                    type:"supply"},
  {s:"IonQ",            t:"Oxford_Instruments",w:2,rel:"Instrumentación criogénica",                  type:"supply"},

  // ── CONNECTIVITY INFRA ─────────────────────────────────────────────────────
  {s:"CommScopeHolding",t:"Ericsson",      w:2, rel:"Infraestructura RAN y antenas",                  type:"partner"},
  {s:"CommScopeHolding",t:"Nokia",         w:2, rel:"Conectividad de red fija/móvil",                 type:"partner"},
  {s:"Qualcomm_Infra",  t:"TSMC",          w:3, rel:"Chips de infraestructura 5G en TSMC",            type:"fab"},
  {s:"Qualcomm_Infra",  t:"Ericsson",      w:2, rel:"Soluciones RAN 5G",                              type:"partner"},

];

if (typeof window !== 'undefined') window.LINKS_CONNECT = LINKS_CONNECT;
