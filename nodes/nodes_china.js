// nodes/nodes_china.js — Ola CHINA 2026-07 (pedido de Fabrizio tras la OPI de
// CXMT: "estamos desperdiciando el mercado chino").
// 13 empresas + 21 links curados a mano con datos verificados a jul-2026.
// CXMT: OPI en el STAR Market de Shanghái el 27-jul-2026 — la mayor de Asia en
// 2026 (~US$8.600M recaudados, debut ~+470%, 4º fabricante mundial de DRAM).
// Convención de links: source PROVEE a target (igual que todo el catálogo).

var NODES_CHINA = [
  {"id": "CXMT", "label": "CXMT (ChangXin Memory)", "ticker": "SSE STAR (OPI 27-jul-2026)", "cat": "memory", "port": "", "role": "Mayor fabricante chino de DRAM y 4º del mundo; campeón nacional de la autosuficiencia de memoria. OPI récord en Shanghái: ~US$8.600M, la mayor de Asia en 2026, debut ~+470%.", "supplies": "DRAM (DDR4/DDR5, LPDDR) y HBM en rampa para servidores de IA y móviles del ecosistema chino (Huawei, Xiaomi, Lenovo).", "moat": "Único productor chino de DRAM a escala con respaldo estatal masivo; brecha tecnológica frente a Samsung/SK Hynix/Micron pero acceso cautivo al mercado doméstico. Riesgo: controles de exportación de equipos y sobrevaloración post-OPI.", "loc": "Hefei, China", "country": "China", "growth": "🟢 OPI +470% en el debut (jul 2026); capacidad DRAM en expansión agresiva", "margin": null, "mkt": ""},
  {"id": "Baidu", "label": "Baidu", "ticker": "BIDU · NASDAQ / 9888 · HKEX", "cat": "cloud", "port": "", "role": "Buscador líder de China y pionero de su IA: LLM Ernie, nube AI Cloud, conducción autónoma Apollo Go y chips propios Kunlun.", "supplies": "Nube de IA y APIs de Ernie al mercado chino; robotaxis Apollo Go en varias ciudades.", "moat": "Distribución masiva (búsqueda + apps) y stack propio de IA (chip Kunlun → framework PaddlePaddle → LLM Ernie). Riesgo: competencia feroz de Alibaba/ByteDance/DeepSeek y monetización lenta.", "loc": "Pekín, China", "country": "China", "growth": "🟡 Nube de IA crece; núcleo publicitario presionado", "margin": 0.15, "mkt": "BIDU"},
  {"id": "Tencent", "label": "Tencent", "ticker": "0700 · HKEX / TCEHY · OTC", "cat": "cloud", "port": "", "role": "Gigante de plataformas (WeChat, gaming #1 mundial) con nube propia y LLM Hunyuan; uno de los mayores compradores chinos de GPUs.", "supplies": "Nube, pagos y distribución vía WeChat al ecosistema chino; inversor prolífico en startups de IA.", "moat": "WeChat como sistema operativo social de China (1.300M+ usuarios) y caja enorme para capex de IA. Riesgo: regulación doméstica y acceso restringido a GPUs de frontera.", "loc": "Shenzhen, China", "country": "China", "growth": "🟢 Hunyuan + gaming sólido; capex de IA en aumento", "margin": 0.26, "mkt": "TCEHY"},
  {"id": "ByteDance", "label": "ByteDance", "ticker": "Privada (pre-OPI)", "cat": "ailab", "port": "", "role": "Dueña de TikTok/Douyin y del LLM Doubao (el chatbot más usado de China); mayor comprador chino de GPUs de Nvidia y nube propia Volcano Engine.", "supplies": "Modelos Doubao/Seed y nube Volcano Engine al mercado chino; demanda gigante de cómputo que arrastra a toda la cadena.", "moat": "El motor de recomendación más valioso del mundo + escala de datos de TikTok/Douyin. Riesgo: presión geopolítica sobre TikTok y acceso a chips.", "loc": "Pekín, China", "country": "China", "growth": "🟢 Doubao líder en uso; capex de IA récord", "margin": null, "mkt": "", "preipo": true},
  {"id": "HuaHong", "label": "Hua Hong Semiconductor", "ticker": "1347 · HKEX / 688347 · STAR", "cat": "foundry", "port": "", "role": "Segunda fundición de China tras SMIC, especializada en nodos maduros (55-90nm+): power, MCU, NOR flash y análogos.", "supplies": "Fundición de especialidad para diseñadores chinos (GigaDevice y otros) en power discretes, IGBT, eNVM.", "moat": "Capacidad doméstica protegida en nodos maduros con demanda de autos/industria; riesgo: guerra de precios en nodos legacy y sanciones a equipos.", "loc": "Shanghái, China", "country": "China", "growth": "🟡 Utilización recuperándose; presión de precios en legacy", "margin": 0.08, "mkt": ""},
  {"id": "GigaDevice", "label": "GigaDevice", "ticker": "603986 · SSE", "cat": "memory", "port": "", "role": "Líder chino (top-3 mundial) en memoria NOR flash y MCUs RISC-V/ARM; fabless.", "supplies": "NOR flash para autos, IoT y wearables; MCUs de propósito general al ecosistema chino.", "moat": "Top-3 mundial en NOR con costos competitivos y sustitución doméstica a favor. Riesgo: ciclo de memoria y competencia de Winbond/Macronix.", "loc": "Pekín, China", "country": "China", "growth": "🟢 Sustitución doméstica + autos empujan NOR/MCU", "margin": 0.18, "mkt": ""},
  {"id": "WillSemi", "label": "Will Semiconductor (OmniVision)", "ticker": "603501 · SSE", "cat": "fabless", "port": "", "role": "Dueña de OmniVision, top-3 mundial en sensores de imagen CMOS (CIS) para smartphones y automóvil.", "supplies": "Sensores de imagen para cámaras de smartphones chinos (Xiaomi, Honor) y sistemas de conducción asistida.", "moat": "Portafolio CIS de gama alta que compite con Sony/Samsung y viento de cola de sustitución doméstica. Riesgo: ciclo de smartphones.", "loc": "Shanghái, China", "country": "China", "growth": "🟢 Recuperación de smartphones + auto CIS en expansión", "margin": 0.14, "mkt": ""},
  {"id": "Montage", "label": "Montage Technology", "ticker": "688008 · STAR", "cat": "fabless", "port": "", "role": "Líder mundial en chips de interfaz de memoria (RCD/MDB para DDR5) — el 'peaje' entre la CPU y los módulos DRAM de servidores.", "supplies": "Chips de interfaz DDR5 a los módulos de memoria de Samsung, SK Hynix y Micron; CXL en desarrollo.", "moat": "Uno de ~3 jugadores del duopolio/triopolio mundial de RCD (con Renesas y Rambus); se beneficia de CADA servidor de IA sin importar quién gane. Riesgo: concentración en un nicho.", "loc": "Shanghái, China", "country": "China", "growth": "🟢 DDR5/servidores de IA disparan la demanda de RCD", "margin": 0.4, "mkt": ""},
  {"id": "Hygon", "label": "Hygon Information", "ticker": "688041 · STAR", "cat": "asic_custom", "port": "", "role": "CPUs x86 domésticas (herencia de la JV con AMD de 2016) y aceleradores DCU para los centros de datos estatales chinos.", "supplies": "CPUs x86 compatibles y aceleradores a servidores de Inspur/Lenovo para gobierno y banca china.", "moat": "Única x86 'de confianza' doméstica para el sector estatal chino. Riesgo: base tecnológica congelada por controles de exportación de 2019; depende de iteración propia.", "loc": "Tianjín, China", "country": "China", "growth": "🟢 Sustitución doméstica estatal acelera pedidos", "margin": 0.3, "mkt": ""},
  {"id": "HorizonRobotics", "label": "Horizon Robotics", "ticker": "9660 · HKEX", "cat": "ai_auto", "port": "", "role": "Líder chino en chips de conducción asistida/autónoma (serie Journey), el 'Mobileye chino'; OPI en Hong Kong 2024.", "supplies": "SoCs Journey y stack de software ADAS a la mayoría de las marcas de autos chinas (BYD, Li Auto, y JV con Volkswagen/CARIAD).", "moat": "Mayor cuota de ADAS doméstico en el mercado de autos más grande del mundo + alianza Volkswagen (~US$2.400M). Riesgo: guerra de precios de los autos eléctricos chinos.", "loc": "Pekín, China", "country": "China", "growth": "🟢 Penetración ADAS en autos chinos en plena curva", "margin": null, "mkt": ""},
  {"id": "Empyrean", "label": "Empyrean Technology", "ticker": "301269 · SZSE", "cat": "eda", "port": "", "role": "El principal EDA doméstico de China (el 'Cadence chino'), pieza crítica de la autosuficiencia: sin EDA no hay diseño de chips.", "supplies": "Herramientas de diseño analógico/mixto y flujos parciales digitales a SMIC, HiSilicon y diseñadores chinos.", "moat": "Campeón nacional protegido con demanda cautiva por las sanciones a Synopsys/Cadence. Riesgo: brecha grande en digital avanzado frente a los líderes.", "loc": "Pekín, China", "country": "China", "growth": "🟢 Sanciones EDA de EE.UU. le regalan el mercado doméstico", "margin": 0.25, "mkt": ""},
  {"id": "SMEE", "label": "SMEE (Shanghai Micro Electronics)", "ticker": "Estatal (no cotiza)", "cat": "equip", "port": "", "role": "La apuesta china de litografía: escáneres DUV domésticos para nodos maduros; el eslabón MÁS débil (y más estratégico) de la autosuficiencia china.", "supplies": "Litografía DUV de 90nm (28nm en desarrollo) a fabs chinas de nodos maduros.", "moat": "Monopolio doméstico por mandato estatal en el único hueco que ASML no puede llenar por sanciones. Riesgo: décadas de brecha tecnológica frente a ASML/Nikon/Canon.", "loc": "Shanghái, China", "country": "China", "growth": "🟡 Progreso lento pero prioridad nacional absoluta", "margin": null, "mkt": "", "preipo": true},
  {"id": "ZhipuAI", "label": "Zhipu AI (GLM)", "ticker": "Privada (pre-OPI, proceso iniciado)", "cat": "ailab", "port": "", "role": "Uno de los 'tigres de la IA' chinos: laboratorio de los modelos GLM, spin-off de Tsinghua, respaldado por Alibaba, Tencent y fondos estatales.", "supplies": "Modelos GLM (chat, código, visión) vía API y despliegues empresariales/gubernamentales en China.", "moat": "Pedigrí Tsinghua + respaldo simultáneo de los dos gigantes (Alibaba y Tencent) y del Estado. Riesgo: DeepSeek redefinió el costo de frontera y compite gratis.", "loc": "Pekín, China", "country": "China", "growth": "🟢 En proceso hacia OPI; adopción estatal creciente", "margin": null, "mkt": "", "preipo": true}
];

// source PROVEE a target · [s, t, w, descripción, tipo]
var LINKS_CHINA = [
  // CXMT — cadena de equipos doméstica y clientes
  ['AMEC', 'CXMT', 3, 'Equipos de grabado (etch) para las fabs DRAM de CXMT', 'supply'],
  ['Naura', 'CXMT', 3, 'Equipos de depósito y grabado para DRAM doméstica', 'supply'],
  ['ACM_Research', 'CXMT', 2, 'Equipos de limpieza de obleas para DRAM', 'supply'],
  ['CXMT', 'Huawei', 3, 'DRAM y HBM doméstica para servidores Ascend', 'supply'],
  ['CXMT', 'Xiaomi', 2, 'LPDDR para smartphones', 'supply'],
  ['CXMT', 'Lenovo', 2, 'DRAM para PCs y servidores', 'supply'],
  // fundiciones domésticas
  ['HuaHong', 'GigaDevice', 3, 'Fundición de NOR flash y MCUs', 'fab'],
  ['SMIC', 'WillSemi', 2, 'Fundición de sensores de imagen CIS', 'fab'],
  ['SMIC', 'Cambricon', 2, 'Fundición doméstica de aceleradores de IA', 'fab'],
  ['TSMC', 'HorizonRobotics', 3, 'Fabricación de los SoC Journey de conducción', 'fab'],
  // Montage: el peaje del DDR5
  ['Montage', 'Samsung', 2, 'Chips de interfaz RCD para módulos DDR5', 'supply'],
  ['Montage', 'SKHynix', 2, 'Chips de interfaz RCD para DIMMs DDR5', 'supply'],
  ['Montage', 'Micron', 2, 'Chips de interfaz de memoria para módulos', 'supply'],
  // EDA y litografía domésticas
  ['Empyrean', 'SMIC', 2, 'Herramientas EDA domésticas', 'license'],
  ['Empyrean', 'HiSilicon', 2, 'EDA doméstica para diseño de chips', 'license'],
  ['SMEE', 'SMIC', 2, 'Litografía DUV doméstica para nodos maduros', 'supply'],
  // GPUs hacia las plataformas chinas
  ['Nvidia', 'Baidu', 2, 'GPUs para entrenamiento (H20 bajo licencia)', 'supply'],
  ['Nvidia', 'Tencent', 2, 'GPUs H20 para la nube de Tencent', 'supply'],
  ['Nvidia', 'ByteDance', 3, 'Mayor comprador chino de GPUs H20', 'supply'],
  // CPUs domésticas en servidores
  ['Hygon', 'Inspur', 2, 'CPUs x86 domésticas para servidores estatales', 'supply'],
  // inversiones en los laboratorios
  ['AlibabaCloud', 'ZhipuAI', 2, 'Inversión estratégica del grupo Alibaba en GLM', 'invest'],
  ['Tencent', 'ZhipuAI', 2, 'Inversión en las rondas de Zhipu', 'invest'],
];

// Meta para el Grafo Temporal (founded) y las fichas
var META_CHINA = {
  "CXMT": { "founded": 2016, "employees": 20000, "revenue_2025": "~US$3.000-4.000M (est.; no auditado público pre-OPI)", "geo_risk": "Controles de exportación de equipos EUV/DUV avanzados de EE.UU./P. Bajos/Japón limitan su hoja de ruta; sobrevaloración post-debut (~US$480.000M) muy por encima de comparables.", "desc": "ChangXin Memory Technologies (CXMT), fundada en 2016 en Hefei, es el mayor fabricante de DRAM de China y el 4º del mundo. Su OPI del 27 de julio de 2026 en el STAR Market recaudó ~US$8.600M (la mayor de Asia en 2026) y debutó con una subida de ~470%." },
  "Baidu": { "founded": 2000, "employees": 41000, "revenue_2025": "~US$18.500M", "desc": "Pionero de la IA china: buscador dominante, LLM Ernie, nube de IA, robotaxis Apollo Go y chips propios Kunlun." },
  "Tencent": { "founded": 1998, "employees": 105000, "revenue_2025": "~US$92.000M", "desc": "El gigante de WeChat y el gaming; nube propia, LLM Hunyuan y uno de los mayores capex de IA de China." },
  "ByteDance": { "founded": 2012, "employees": 150000, "revenue_2025": "~US$155.000M (est.)", "desc": "TikTok/Douyin + Doubao, el chatbot más usado de China; mayor comprador chino de GPUs y nube Volcano Engine." },
  "HuaHong": { "founded": 1996, "employees": 10000, "revenue_2025": "~US$2.300M", "desc": "Segunda fundición china, especialista en nodos maduros: power, MCU, NOR y análogos." },
  "GigaDevice": { "founded": 2005, "employees": 3000, "revenue_2025": "~US$1.100M", "desc": "Top-3 mundial en NOR flash y líder chino en MCUs; fabless con fundición en Hua Hong y SMIC." },
  "WillSemi": { "founded": 2007, "employees": 5600, "revenue_2025": "~US$3.600M", "desc": "Dueña de OmniVision, top-3 mundial en sensores de imagen CMOS para móviles y automóvil." },
  "Montage": { "founded": 2004, "employees": 700, "revenue_2025": "~US$500M", "desc": "Líder mundial en chips de interfaz de memoria DDR5 (RCD): cobra peaje en cada servidor de IA." },
  "Hygon": { "founded": 2014, "employees": 2500, "revenue_2025": "~US$1.300M", "desc": "CPUs x86 domésticas (herencia JV AMD 2016) y aceleradores DCU para el sector estatal chino." },
  "HorizonRobotics": { "founded": 2015, "employees": 2400, "revenue_2025": "~US$400M", "desc": "El 'Mobileye chino': SoCs Journey de conducción asistida con JV de ~US$2.400M con Volkswagen; OPI HK 2024." },
  "Empyrean": { "founded": 2009, "employees": 1200, "revenue_2025": "~US$180M", "desc": "El principal EDA doméstico de China; beneficiario directo de las sanciones a Synopsys/Cadence." },
  "SMEE": { "founded": 2002, "employees": 1000, "desc": "La apuesta estatal china de litografía: DUV doméstico de 90nm con 28nm en desarrollo; el eslabón más estratégico de la autosuficiencia." },
  "ZhipuAI": { "founded": 2019, "employees": 800, "desc": "Laboratorio de los modelos GLM (spin-off de Tsinghua), respaldado por Alibaba, Tencent y fondos estatales; en camino a la OPI." }
};

if (typeof NODE_META !== 'undefined') { for (var _kc in META_CHINA) {
  NODE_META[_kc] = Object.assign({}, NODE_META[_kc] || {}, META_CHINA[_kc]); } }
if (typeof window !== 'undefined') {
  window.NODES_CHINA = NODES_CHINA;
  window.LINKS_CHINA = LINKS_CHINA;
  window.META_CHINA = META_CHINA;
}
