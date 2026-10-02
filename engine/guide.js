// engine/guide.js — pestaña "❓ Guía": explica la app en lenguaje simple.
// Sin jerga técnica. Expone window.initGuiaTab (mismo patrón que initTKGTab).
// Actualizada 2026-07-12 (pedido de Fabrizio: "la guía está desactualizada").
// 2026-09-28: BILINGÜE (regla del proyecto) y al día — 949 empresas, ⏱ en el
// mapa, 📡 feed, actualizaciones silenciosas (ya no hay aviso "Nueva versión").
// 2026-09-28 (tarde): toda empresa tiene 📊 Dossier y qué parte es EN VIVO.
// Se reconstruye si cambia el idioma.

(function () {
  'use strict';
  let _builtLang = null;

  function lang() {
    let l = window.LANG;
    if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } }
    return l === 'en' ? 'en' : 'es';
  }

  const SEC = (title, html) => `
    <div style="margin-bottom:34px">
      <h3 style="font-family:'Fraunces',serif;font-size:18px;font-weight:700;margin:0 0 10px;color:var(--ink-1)">${title}</h3>
      ${html}
    </div>`;

  const T = {
    es: {
      kicker: 'Guía rápida',
      title: '¿Qué es Khipus Finance AI?',
      intro: `Un terminal financiero para invertir en la cadena de suministro de la IA — <b>949 empresas</b> en
        13 sectores: semiconductores, IA, espacio, nuclear, robótica, defensa, energía, materiales,
        macro/crédito, inmobiliario y logística, conectadas por sus <b>2.500+ relaciones reales</b>
        (quién fabrica, quién abastece, quién depende de quién). Precios en vivo de las bolsas del mundo,
        simulaciones de crisis, radiografías de empresas, y un asistente (Khipu) que lo ejecuta todo por ti.`,
      tabs_h: 'Las 4 pestañas',
      tabs: [
        ['🗺️ Mapa', 'El universo de las 949 empresas. Sub-modos: ⬡ Cadena (el grafo), 🌐 Geopolítica, 🚀 Espacio, 🧬 Simulación y 🪐 Universo. Los botones de la izquierda (+ − ⤢ 🪐 ⏱) son el zoom, el Universo y la máquina del tiempo. Sin ninguna empresa elegida, el panel derecho muestra 📡 lo último que entró al grafo.'],
        ['📈 Mercado', 'Precios en tiempo real y tu portafolio. Sub-modo ₿ Cripto: el mercado cripto explicado — vista Mapa por categorías, top 100 en vivo, y el Expediente Khipu de las 50 grandes: qué es, cómo funciona, riesgos y catalizadores de cada una, con advertencias ⚠ en las monedas delicadas.'],
        ['🖥️ Terminal', 'Vista estilo Bloomberg: gráficos lado a lado + el panel 📋 Datos (ficha, valuación, analistas, fundamentales y cadena de cada empresa). Toca una empresa de la lista para abrir su gráfico. Sub-modos: Terminal, Análisis y Canvas IA.'],
        ['❓ Guía', 'Esta página.'],
      ],
      wow_h: 'Los superpoderes',
      wow: [
        ['🎙 Cabina de Khipu', 'Toca el botón Khipu (o Ctrl+K): pantalla completa con botones para TODO — Grafo, Terminal, X-Ray, Simular, Comparar, Oportunidades, Investigar y Gráficos. Escribe o habla normal.'],
        ['🔬 X-Ray', 'En la ficha de cualquier empresa: la "desarma" por completo — por qué tiene ese riesgo, todos sus hilos (de quién depende y a quién provee), y la onda de impacto si cae (quién sufre y quién GANA).'],
        ['🔬 Investigación IA', 'En el X-Ray o la ficha de una empresa: botón 🔬 Investigar. Varios analistas IA (fundamentales, noticias, técnico, cadena de suministro…) leen SOLO datos reales con fuente y escriben conclusiones cortas: cada una dice si es a favor, en contra o neutral, para qué plazo (hoy, semanas, meses, años), qué tan confiable es (y por qué) y qué la desmentiría. Toca "¿Por qué? →" para ver la evidencia a favor y en contra con su fuente original (incluidos los reportes oficiales a la SEC: 10-K, 10-Q, 8-K). Si dos analistas no están de acuerdo, se muestra el choque — no se esconde. Nunca dice compra/vende.'],
        ['🌐 World Monitor (Geopolítica)', 'La pestaña Geopolítica es un solo globo 3D con lo que pasa en el mundo EN VIVO: conflictos y protestas (GDELT), sismos (USGS), incendios, tormentas y volcanes (NASA), estrechos marítimos con su puntaje de riesgo e inestabilidad por país. Toca cualquier punto: te dice qué pasó, dónde, cuándo, la fuente, y QUÉ EMPRESAS DE TU CADENA están cerca (con su riesgo) — y puedes simular el impacto sobre la cadena. Las capas de referencia (rutas marítimas, cables, fabs) dicen "no en vivo". Si una fuente no responde, lo dice.'],
        ['💬 Pregúntale a Khipu', 'En la Cabina (botón Khipu o Ctrl+K) escribe cualquier pregunta como a un analista: "¿qué riesgos tiene TSMC?", "¿qué pasó hoy con Nvidia?", "¿cuáles son las empresas más críticas?". Antes de responder CONSULTA la app (fichas, cadena, precios en vivo, investigación de los agentes, eventos, comité) y te dice de dónde sacó cada dato. Recuerda la conversación y puede abrirte el X-Ray, el mapa o una simulación. Por VOZ (🎙) usa el mismo cerebro.'],
        ['🚀 Space Monitor (Espacio)', 'La pestaña Espacio es un globo 3D con los satélites reales (CelesTrak) y los PRÓXIMOS LANZAMIENTOS: las plataformas brillan, los cohetes dibujan su arco de ascenso, arriba ves la cuenta regresiva del próximo y abajo una línea de tiempo que puedes arrastrar o tocar. Cada lanzamiento dice cohete, misión, órbita, ventana, webcast y qué empresas de tu cadena participan.'],
        ['💼 Asistente de carteras', 'Carteras → 🤖 Asistente: pregúntale lo que quieras ("¿Nvidia y AMD se mueven juntas?", "¿qué es diversificar?") o pulsa Proponme una cartera: eliges objetivo, plazo, riesgo, monto y temas, y te da 2–3 carteras armadas con precios reales, su riesgo y por qué. Con un clic la creas como cartera SIMULADA. Es educativo: no ejecuta nada.'],
        ['🏛 Comité de inversión', 'Mercado → 🏛 Comité (o en el X-Ray, o el comando NVDA COMITE). Reúne a todos los analistas IA, su historial REAL de aciertos, el riesgo medido y los datos en vivo, y propone una decisión (comprar, aumentar, mantener, reducir, vender o evitar) con su tamaño calculado por volatilidad. Muestra quién no está de acuerdo y qué la desmentiría. NADA se ejecuta sin tu aprobación con PIN; es una propuesta, no asesoría personalizada.'],
        ['🎯 ¿Aciertan los analistas?', 'Cada conclusión de un analista IA guarda el precio del día en que se hizo. Cuando vence su plazo, Khipus compara contra el S&amp;P 500 y marca acierto o fallo. Con eso calcula el historial de cada analista y ajusta su "confianza calibrada". Lo ves en 🏛 Comité → Historial. Al principio hay pocos datos: se llena solo con las semanas.'],
        ['👥 Clientes e inversión', 'Mercado → 👥 Clientes. Cada cliente usa SU PROPIA cuenta de Alpaca (nunca se mezcla dinero). Por defecto todo es en PAPEL (simulado); el dinero real exige dos interruptores. Cada orden pasa controles (límites por orden, por día, % máximo por empresa, poder de compra) y las propuestas del Comité o de IAs externas quedan en <b>Aprobaciones</b> hasta que tú las apruebes con tu PIN. Todo queda registrado. Antes de manejar dinero de otras personas, lee docs/INVERSION_TERCEROS.md y habla con un abogado.'],
        ['🤖 Conectar IAs (MCP)', '🩺 → 🤖 Conectar IAs. Crea una conexión para que Claude, ChatGPT o tus propios agentes usen Khipus desde su ventana: buscar empresas, ver la cadena, leer la investigación, calcular riesgo y, si les das permiso, PROPONER órdenes para un cliente — que siempre esperan tu aprobación. Puedes revocar la conexión cuando quieras y ver todo lo que hizo.'],
        ['📉 Reporte de riesgo (VaR y Vega)', 'En Mercado → <b>📉 Reporte de riesgo</b> (o en tus Carteras → 📉 Riesgo, o el comando <b>PORT VAR</b>). Con precios diarios REALES del último año te dice: cuánto se mueve tu cartera (volatilidad), cuánto podrías perder en un día malo (VaR y CVaR al 95% y 99%), qué acción pone más riesgo, qué tan pegada va al S&amp;P 500 (beta) y cuánto se mueven juntas tus acciones (correlaciones). La pestaña <b>Vega / Kappa</b> (comando <b>PORT VEGA</b>) es para opciones: registras tus calls y puts y ves su Delta, Gamma, Theta y Vega con la volatilidad implícita en vivo, y cuánto ganas o pierdes si la volatilidad sube o baja. Botón 🖨 para guardarlo en PDF.'],
        ['🛡 Cifras verificadas', 'Ninguna IA de la app puede darte cifras de memoria: toda cifra de dinero (valuación, precio, ingresos) debe salir de un dato real que se le entregó, y a cada pregunta se le agregan la capitalización y el precio EN VIVO de las empresas mencionadas. Si aun así una cifra no se puede comprobar, aparece marcada <b>(⚠ cifra no verificada)</b> — no la tomes como dato.'],
        ['📊 Dossier de cada empresa', 'TODAS las empresas tienen Dossier: botón 📊 Dossier en la ficha del mapa, en el X-Ray y en la Terminal. Si cotiza en bolsa, arriba va una franja EN VIVO (precio y % del día, capitalización, empleados, ingresos de los últimos 12 meses, márgenes, rango del año y precio objetivo — se refresca sola cada minuto) y debajo 8 mini-gráficos anuales (ingresos, dilución, free cash flow, acción, valuación, deuda, márgenes y ROE) con su fuente. Si es privada o filial: su ficha, la cotización del dueño cuando la hay ("cotiza a través de…") y noticias recientes en vivo. Si una fuente no publica un dato, se dice — nunca se inventan números.'],
        ['◉ Simulación en vivo', 'En el mapa, botón "◉ En vivo": elige un tipo de golpe (corte, auge, precio, sanción) y un objetivo (empresa, sector o país entero) — el mapa se tiñe en tiempo real y ves ganadores y perdedores.'],
        ['🪐 Universo', 'Las 949 empresas flotando en el espacio: izquierda→derecha = posición en la cadena, arriba→abajo = riesgo. Clic en una empresa y su cadena se ilumina (verde = le provee, naranja = le compra); doble clic abre su ficha. Funciona en cualquier equipo.'],
        ['🧠 Investigación profunda', 'Dile a Khipu "investiga la energía nuclear para datacenters" (o cualquier pregunta grande): planifica, reúne el contexto, simula en las matrices y te escribe una tesis con números reales. Tarda ~1 minuto.'],
        ['📡 Radar en vivo', 'La app se mantiene al día SOLA: los agentes leen noticias, recalculan riesgos y hasta proponen empresas nuevas (todo auditado y reversible). Lo último aparece en "📡 Lo último en el grafo".'],
        ['✦ Gráficos al instante', 'Pide "top 10 por riesgo", "márgenes de Nvidia y TSMC", "proveedores de ASML" o "precio de AMD" — salen al instante, sin esperar a la IA (etiqueta "local ⚡").'],
      ],
      khipu_h: 'Khipu: pídeselo y lo hace',
      khipu_p1: `Toca <b>Khipu</b> (arriba a la derecha) o presiona <b>Ctrl+K</b>: se abre su pantalla completa.
        Escríbele o háblale normal — <i>"desármame Nvidia"</i>, <i>"¿qué pasa si cae TSMC?"</i>,
        <i>"compara Nvidia y AMD"</i>, <i>"dossier de Apple"</i>, <i>"precio de AMD"</i>,
        <i>"investiga la energía nuclear para datacenters"</i>, <i>"muéstrame la terminal"</i>.
        Khipu lo ejecuta y te muestra el resultado en su propio escenario.`,
      khipu_p2: `Por voz sabe también los datos de cada empresa (empleados, ingresos, fundación, riesgo…) —
        pregúntale lo que quieras mientras miras el mapa. Entiende nombres completos o legales
        ("Taiwan Semiconductor", "Google", "Hon Hai").`,
      time_h: '⏱ Tiempo — el mapa como máquina del tiempo',
      time_p: `En el mapa, toca <b>⏱</b> (junto al zoom). Aparece una línea de tiempo abajo: muévela
        (o dale ▶) y verás la cadena como era en esa fecha — lo que aún no existía se apaga. <b>⚡ Eventos</b>
        dibuja los hechos con fecha: línea punteada entre dos empresas, o anillo punteado alrededor de una
        empresa cuando el hecho es con un tema (EUV, Ley CHIPS, China…). Pasa el mouse para leerlos.
        <b>☰ Hechos</b> abre la lista completa y <b>⬗ 3D</b> la vista donde la profundidad es el tiempo.
        Dentro de la ficha de cada empresa, <b>＋ Acción</b> te deja crear tesis, marcar riesgos o anotar —
        con fecha y tu nombre, para siempre. La sección <b>Historia</b> de la ficha dice de dónde sale cada dato.`,
      cmd_h: 'Comandos rápidos (opcional)',
      cmd_p: 'Escríbelos en la Cabina de Khipu — responden al instante, sin esperar a la IA.',
      cmds: [
        ['TSMC XRAY', 'desarma TSMC (el X-Ray completo)'],
        ['NVDA RESEARCH', 'pone a los analistas IA a investigar Nvidia'],
        ['SHOCK NVDA', 'simula qué pasa si Nvidia cae'],
        ['COMPARE NVDA AMD', 'compara dos empresas lado a lado'],
        ['INSIGHTS', 'abre el panel de oportunidades y riesgo'],
        ['NVDA THESIS me gusta por su moat', 'guarda esa idea como tesis'],
        ['PORT VAR', 'el reporte de riesgo de tu portafolio (VaR, volatilidad, beta)'],
        ['PORT VEGA', 'griegas de tus opciones (Delta, Gamma, Theta, Vega)'],
        ['NVDA COMITE', 'el comité de inversión propone una decisión sobre Nvidia'],
        ['CLIENTES', 'clientes, órdenes y aprobaciones'],
        ['MUNDO', 'el World Monitor (globo con eventos en vivo)'],
        ['GRAPH ASOF 2020-01-01', 'ver la cadena como era en esa fecha'],
        ['FEED', 'lo último que entró al grafo: noticias, relaciones nuevas, tesis'],
        ['ALERT NVDA PX > 150', 'avisarte si Nvidia sube de $150'],
        ['FACTOR LIST', 'los ~70 riesgos sistémicos latentes (aranceles, tasas, cuellos de botella)'],
        ['FACTOR taiwan FIRE', 'qué pasaría si esa crisis se dispara: contagio y nivel sistémico'],
      ],
      faq_h: 'Preguntas frecuentes',
      faq: [
        ['¿Qué es el NRS?', 'La nota de riesgo de cada empresa, de 0 (segura) a 100 (frágil). Suma geopolítica, dependencia de la cadena, salud del negocio y sector. Donde veas NRS hay un botoncito <b style="color:#00E0FF">?</b> que te lo explica con ejemplos — igual que el peso de las conexiones, el VaR y la dilución.'],
        ['¿Se pierden mis datos si cierro el navegador?', 'Tu portafolio (compras/ventas) vive en este navegador. Tus tesis, anotaciones y decisiones (＋ Acción) se guardan en el servidor — sobreviven aunque cambies de computadora.'],
        ['¿Qué datos se actualizan en vivo?', 'En las empresas que cotizan: el precio y su % del día, la capitalización (en dólares), los empleados y los ingresos de los últimos 12 meses — en la ficha del mapa, en el X-Ray y en el 📊 Dossier. Un dato en vivo lleva un <b style="color:#2BE38B">●</b> punto verde: pasa el mouse o tócalo (en el teléfono) para ver <i>en vivo · fuente · hora</i>. El precio del X-Ray y la franja del Dossier se revisan cada minuto mientras están abiertos; con la bolsa cerrada verás el último precio y su fecha, marcado como tal. Las noticias también llegan en vivo. Los gráficos anuales vienen de los estados financieros publicados (cambian una vez al año). La capitalización de TODAS las empresas cotizadas (unas 580) se consulta en vivo cada 15 minutos y reemplaza a la del catálogo en toda la app (comparador, simulación, portafolio, terminal). Si no hay dato en vivo, ves el del catálogo, como siempre.'],
        ['¿Los % del War Room son reales?', 'No: el War Room simula un escenario HIPOTÉTICO. Arriba lo dice con el aviso 🧪 SIMULACIÓN. Si la IA está disponible, los % son estimaciones de los agentes (cada empresa con su razón); si no, el motor del grafo calcula la severidad del golpe de 0 a 100 (no es % de precio). Nunca son precios reales ni recomendaciones.'],
        ['¿La app se actualiza sola?', 'Sí, en silencio: al abrirla (o al volver a la pestaña) ya tienes la última versión, sin avisos. Si alguna vez no ves un cambio, recarga con Ctrl+Shift+R.'],
        ['¿Se puede usar desde el teléfono?', 'Sí. En pantallas chicas las pestañas se deslizan con el dedo, los botones del mapa van a la derecha y en la Terminal basta con tocar una empresa.'],
        ['¿Qué hago si algo no responde?', 'Abre 🩺 Sistema (arriba) — te dice en vivo qué servicio falló y por qué, sin mostrar ninguna clave.'],
      ],
    },
    en: {
      kicker: 'Quick guide',
      title: 'What is Khipus Finance AI?',
      intro: `A financial terminal for investing in the AI supply chain — <b>949 companies</b> across
        13 sectors: semiconductors, AI, space, nuclear, robotics, defense, energy, materials,
        macro/credit, real estate and logistics, connected by <b>2,500+ real relationships</b>
        (who makes what, who supplies whom, who depends on whom). Live prices from exchanges worldwide,
        crisis simulations, company X-rays, and an assistant (Khipu) that runs it all for you.`,
      tabs_h: 'The 4 tabs',
      tabs: [
        ['🗺️ Map', 'The universe of 949 companies. Sub-modes: ⬡ Chain (the graph), 🌐 Geopolitics, 🚀 Space, 🧬 Simulation and 🪐 Universe. The buttons on the side (+ − ⤢ 🪐 ⏱) are zoom, the Universe and the time machine. With no company selected, the right panel shows 📡 the latest additions to the graph.'],
        ['📈 Market', 'Real-time prices and your portfolio. ₿ Crypto sub-mode: the crypto market explained — a Map view by category, live top 100, and the Khipu Dossier on the top 50: what each one is, how it works, risks and catalysts, with ⚠ warnings on the delicate ones.'],
        ['🖥️ Terminal', 'Bloomberg-style view: charts side by side + the 📋 Data panel (profile, valuation, analysts, fundamentals and supply chain for each company). Tap a company in the list to open its chart. Sub-modes: Terminal, Analysis and AI Canvas.'],
        ['❓ Guide', 'This page.'],
      ],
      wow_h: 'The superpowers',
      wow: [
        ['🎙 Khipu Cockpit', 'Tap the Khipu button (or Ctrl+K): a full screen with buttons for EVERYTHING — Graph, Terminal, X-Ray, Simulate, Compare, Opportunities, Research and Charts. Type or talk normally.'],
        ['🔬 X-Ray', 'From any company card: takes it apart completely — why it carries that risk, all its threads (who it depends on and who it supplies), and the impact wave if it fails (who suffers and who WINS).'],
        ['🔬 AI Research', 'In the X-Ray or a company card: the 🔬 Research button. Several AI analysts (fundamentals, news, technical, supply chain…) read ONLY real, sourced data and write short conclusions: each says whether it is positive, negative or neutral, for which horizon (today, weeks, months, years), how reliable it is (and why) and what would prove it wrong. Tap "Why? →" to see the evidence for and against with its original source. When two analysts disagree the clash is shown, not hidden. It never says buy/sell. Evidence includes official SEC filings (10-K, 10-Q, 8-K).'],
        ['🌐 World Monitor (Geopolitics)', 'The Geopolitics tab is a single 3D globe with what is happening in the world LIVE: conflicts and protests (GDELT), earthquakes (USGS), wildfires, storms and volcanoes (NASA), maritime chokepoints with their risk score and instability by country. Tap any point: it tells you what happened, where, when, the source, and WHICH COMPANIES OF YOUR CHAIN are nearby (with their risk) — and you can simulate the impact on the chain. Reference layers (shipping lanes, cables, fabs) say "not live". If a source does not respond, it says so.'],
        ['💬 Ask Khipu', 'In the Cockpit (Khipu button or Ctrl+K) type any question like you would to an analyst: "what are TSMC\'s risks?", "what happened with Nvidia today?", "which companies are most critical?". Before answering it LOOKS THINGS UP in the app (profiles, chain, live prices, agents\' research, events, committee) and tells you where each fact comes from. It remembers the conversation and can open the X-Ray, the map or a simulation. By VOICE (🎙) it uses the same brain.'],
        ['🚀 Space Monitor (Space)', 'The Space tab is a 3D globe with real satellites (CelesTrak) and UPCOMING LAUNCHES: pads glow, rockets draw their ascent arc, the top shows the next countdown and the bottom a timeline you can drag or tap. Each launch shows rocket, mission, orbit, window, webcast and which companies of your chain are involved.'],
        ['💼 Portfolio assistant', 'Portfolios → 🤖 Assistant: ask anything ("do Nvidia and AMD move together?", "what is diversifying?") or press Propose a portfolio: pick goal, horizon, risk, amount and themes, and get 2–3 portfolios built with real prices, their risk and why. One click creates it as a SIMULATED portfolio. Educational: nothing executes.'],
        ['🏛 Investment committee', 'Market → 🏛 Committee (or in the X-Ray, or the NVDA COMMITTEE command). It brings together all AI analysts, their REAL track record, measured risk and live data, and proposes a decision (buy, add, hold, trim, sell or avoid) with a volatility-based size. It shows who disagrees and what would prove it wrong. NOTHING executes without your PIN approval; it is a proposal, not personalized advice.'],
        ['🎯 Are the analysts right?', 'Every AI analyst conclusion stores the price on the day it was made. When its horizon ends, Khipus compares against the S&amp;P 500 and marks a hit or a miss. From that it computes each analyst\'s track record and adjusts its "calibrated confidence". See it in 🏛 Committee → Track record. There is little data at first: it fills in over the weeks.'],
        ['👥 Clients and investing', 'Market → 👥 Clients. Each client uses THEIR OWN Alpaca account (money is never pooled). Everything is PAPER (simulated) by default; real money needs two switches. Every order passes checks (per-order and daily limits, max % per company, buying power) and proposals from the Committee or external AIs wait in <b>Approvals</b> until you approve them with your PIN. Everything is logged. Before handling other people\'s money, read docs/INVERSION_TERCEROS.md and talk to a lawyer.'],
        ['🤖 Connect AIs (MCP)', '🩺 → 🤖 Connect AIs. Create a connection so Claude, ChatGPT or your own agents can use Khipus from their own window: search companies, see the chain, read the research, compute risk and, if you allow it, PROPOSE orders for a client — which always wait for your approval. You can revoke the connection anytime and see everything it did.'],
        ['📉 Risk report (VaR and Vega)', 'In Market → <b>📉 Risk report</b> (or in your Portfolios → 📉 Risk, or the <b>PORT VAR</b> command). Using REAL daily prices from the last year it tells you: how much your portfolio moves (volatility), how much you could lose on a bad day (VaR and CVaR at 95% and 99%), which stock brings the most risk, how closely it tracks the S&amp;P 500 (beta) and how much your stocks move together (correlations). The <b>Vega / Kappa</b> tab (<b>PORT VEGA</b> command) is for options: register your calls and puts and see their Delta, Gamma, Theta and Vega with live implied volatility, and how much you gain or lose if volatility rises or falls. 🖨 button to save it as PDF.'],
        ['🛡 Verified figures', 'No AI in the app can give you figures from memory: every money figure (valuation, price, revenue) must come from real data it was given, and every question gets the LIVE market cap and price of the companies mentioned. If a figure still cannot be checked, it is marked <b>(⚠ unverified figure)</b> — do not treat it as data.'],
        ['📊 Every company has a Dossier', 'EVERY company has a Dossier: the 📊 Dossier button on the map card, in the X-Ray and in the Terminal. If it is publicly traded, the top shows a LIVE strip (price and daily %, market cap, employees, trailing-12-month revenue, margins, 52-week range and price target — it refreshes itself every minute) and below it 8 yearly mini-charts (revenue, dilution, free cash flow, stock, valuation, debt, margins and ROE) with their source. If it is private or a subsidiary: its profile, the owner\'s live quote when there is one ("traded through…") and live recent news. When a source does not publish a figure, we say so — numbers are never made up.'],
        ['◉ Live simulation', 'On the map, the "◉ Live" button: pick a type of shock (cut, boom, price, sanction) and a target (company, sector or whole country) — the map colors in real time and you see winners and losers.'],
        ['🪐 Universe', 'The 949 companies floating in space: left→right = position in the chain, top→bottom = risk. Click a company and its chain lights up (green = supplies it, orange = buys from it); double-click opens its card. Works on any device.'],
        ['🧠 Deep research', 'Tell Khipu "research nuclear energy for datacenters" (or any big question): it plans, gathers context, simulates on the matrices and writes you a thesis with real numbers. Takes ~1 minute.'],
        ['📡 Live radar', 'The app keeps itself up to date: agents read news, recompute risks and even propose new companies (all audited and reversible). The latest shows up in "📡 Latest in the graph".'],
        ['✦ Instant charts', 'Ask for "top 10 by risk", "Nvidia and TSMC margins", "ASML suppliers" or "AMD price" — they appear instantly, without waiting for the AI ("local ⚡" tag).'],
      ],
      khipu_h: 'Khipu: ask and it does it',
      khipu_p1: `Tap <b>Khipu</b> (top right) or press <b>Ctrl+K</b>: its full screen opens.
        Type or talk normally — <i>"break down Nvidia"</i>, <i>"what if TSMC fails?"</i>,
        <i>"compare Nvidia and AMD"</i>, <i>"Apple dossier"</i>, <i>"AMD price"</i>,
        <i>"research nuclear energy for datacenters"</i>, <i>"show me the terminal"</i>.
        Khipu runs it and shows you the result on its own stage.`,
      khipu_p2: `By voice it also knows each company's data (employees, revenue, founding year, risk…) —
        ask whatever you want while looking at the map. It understands full and legal names
        ("Taiwan Semiconductor", "Google", "Hon Hai").`,
      time_h: '⏱ Time — the map as a time machine',
      time_p: `On the map, tap <b>⏱</b> (next to zoom). A timeline appears at the bottom: drag it
        (or press ▶) and you see the chain as it was on that date — what did not exist yet is dimmed. <b>⚡ Events</b>
        draws dated facts: a dashed line between two companies, or a dashed ring around a company when the
        fact is about a topic (EUV, CHIPS Act, China…). Hover to read them.
        <b>☰ Facts</b> opens the full list and <b>⬗ 3D</b> the view where depth is time.
        Inside each company card, <b>＋ Action</b> lets you create theses, flag risks or take notes —
        dated and signed, forever. The card's <b>History</b> section shows where each fact comes from.`,
      cmd_h: 'Quick commands (optional)',
      cmd_p: 'Type them in the Khipu Cockpit — they answer instantly, without waiting for the AI.',
      cmds: [
        ['TSMC XRAY', 'take TSMC apart (the full X-Ray)'],
        ['NVDA RESEARCH', 'put the AI analysts to research Nvidia'],
        ['SHOCK NVDA', 'simulate what happens if Nvidia fails'],
        ['COMPARE NVDA AMD', 'compare two companies side by side'],
        ['INSIGHTS', 'open the opportunities and risk panel'],
        ['NVDA THESIS I like its moat', 'save that idea as a thesis'],
        ['PORT VAR', 'your portfolio risk report (VaR, volatility, beta)'],
        ['PORT VEGA', 'your options Greeks (Delta, Gamma, Theta, Vega)'],
        ['NVDA COMMITTEE', 'the investment committee proposes a decision on Nvidia'],
        ['CLIENTS', 'clients, orders and approvals'],
        ['WORLD', 'the World Monitor (globe with live events)'],
        ['GRAPH ASOF 2020-01-01', 'see the chain as it was on that date'],
        ['FEED', 'the latest in the graph: news, new relationships, theses'],
        ['ALERT NVDA PX > 150', 'alert you if Nvidia goes above $150'],
        ['FACTOR LIST', 'the ~70 latent systemic risks (tariffs, rates, bottlenecks)'],
        ['FACTOR taiwan FIRE', 'what if that crisis fires: contagion and systemic level'],
      ],
      faq_h: 'FAQ',
      faq: [
        ['What is the NRS?', 'Each company\'s risk score, from 0 (safe) to 100 (fragile). It adds up geopolitics, supply-chain dependence, business health and sector. Wherever you see NRS there is a small <b style="color:#00E0FF">?</b> button that explains it with examples — same for link weight, VaR and dilution.'],
        ['Do I lose my data if I close the browser?', 'Your portfolio (buys/sells) lives in this browser. Your theses, notes and decisions (＋ Action) are saved on the server — they survive even if you switch computers.'],
        ['Which data updates live?', 'For listed companies: the price and its daily %, market cap (in dollars), employees and trailing-12-month revenue — on the map card, in the X-Ray and in the 📊 Dossier. A live figure carries a green <b style="color:#2BE38B">●</b> dot: hover it or tap it (on a phone) to see <i>live · source · time</i>. The X-Ray price and the Dossier strip are checked every minute while they are open; when the exchange is closed you see the last price and its date, labeled as such. News also arrives live. The yearly charts come from published financial statements (they change once a year). The market cap of ALL listed companies (about 580) is fetched live every 15 minutes and replaces the catalog one across the app (compare, simulation, portfolio, terminal). With no live figure, you see the catalog one, as always.'],
        ['Are the War Room % real?', 'No: the War Room simulates a HYPOTHETICAL scenario, and the 🧪 SIMULATION notice at the top says so. When AI is available, the % are the agents\' estimates (each company with its rationale); otherwise the graph engine computes the hit severity from 0 to 100 (not % price). They are never real prices nor recommendations.'],
        ['Does the app update itself?', 'Yes, silently: when you open it (or come back to the tab) you already have the latest version, with no prompts. If you ever miss a change, reload with Ctrl+Shift+R.'],
        ['Can I use it from my phone?', 'Yes. On small screens the tabs swipe sideways, the map buttons move to the right, and in the Terminal you just tap a company.'],
        ['What if something does not respond?', 'Open 🩺 System (top) — it tells you live which service failed and why, without showing any key.'],
      ],
    },
  };

  window.initGuiaTab = function () {
    const panel = document.getElementById('guia-panel');
    if (!panel) return;
    const lg = lang();
    if (_builtLang === lg) return;   // se reconstruye si cambió el idioma
    _builtLang = lg;
    const C = T[lg];

    const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const rows = (list, w) => `
          <div style="display:flex;flex-direction:column;gap:10px">
            ${list.map(([name, desc]) => `
              <div style="display:flex;gap:14px;align-items:baseline;padding:9px 0;border-bottom:1px solid var(--line);flex-wrap:wrap">
                <div style="flex:0 0 ${w}px;font-size:13px;font-weight:700;color:var(--ink-1)">${esc(name)}</div>
                <div style="flex:1;min-width:200px;font-size:12.5px;color:var(--ink-3);line-height:1.5">${esc(desc)}</div>
              </div>`).join('')}
          </div>`;

    panel.innerHTML = `
      <div style="max-width:820px;margin:0 auto;padding:26px 18px 60px">
        <div style="margin-bottom:8px;font-family:'JetBrains Mono',monospace;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--violet)">${C.kicker}</div>
        <h2 style="font-family:'Fraunces',serif;font-size:27px;font-weight:700;margin:0 0 8px">${C.title}</h2>
        <p style="font-size:14px;line-height:1.6;color:var(--ink-2);margin:0 0 36px;max-width:70ch">${C.intro}</p>

        ${SEC(C.tabs_h, rows(C.tabs, 150))}
        ${SEC(C.wow_h, rows(C.wow, 190))}

        ${SEC(C.khipu_h, `
          <p style="font-size:13px;line-height:1.6;color:var(--ink-2);margin:0 0 8px">${C.khipu_p1}</p>
          <p style="font-size:13px;line-height:1.6;color:var(--ink-2);margin:0">${C.khipu_p2}</p>`)}

        ${SEC(C.time_h, `
          <p style="font-size:13px;line-height:1.6;color:var(--ink-2);margin:0 0 10px">${C.time_p}</p>`)}

        ${SEC(C.cmd_h, `
          <p style="font-size:12.5px;color:var(--ink-3);margin:0 0 12px">${C.cmd_p}</p>
          <div style="border:1px solid var(--line);border-radius:10px;overflow:hidden">
            ${C.cmds.map(([cmd, desc], i) => `
              <div style="display:flex;gap:6px 14px;align-items:center;padding:9px 14px;flex-wrap:wrap;${i % 2 ? 'background:var(--surface-2)' : ''}">
                <code style="flex:0 0 220px;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--violet);font-weight:700">${esc(cmd)}</code>
                <span style="font-size:12.5px;color:var(--ink-2)">${esc(desc)}</span>
              </div>`).join('')}
          </div>`)}

        ${SEC(C.faq_h, `
          <div style="display:flex;flex-direction:column;gap:14px">
            ${C.faq.map(([q, a]) => `
            <div><div style="font-size:13px;font-weight:700;color:var(--ink-1);margin-bottom:3px">${q}</div>
              <div style="font-size:12.5px;color:var(--ink-3);line-height:1.5">${a}</div></div>`).join('')}
          </div>`)}
      </div>`;
  };
})();
