/* ============================================================================
   engine/explain.js — EXPLICADOR DE MÉTRICAS para no expertos (2026-07-12).
   Feedback real: un inversionista preguntó "¿qué es el NRS y cómo se calcula?"
   y la app no se lo decía. Regla nueva: toda métrica tiene su "?" que la
   explica en lenguaje simple — en ESPAÑOL e INGLÉS (regla bilingüe).

   API:  window.explainMetric('nrs')  →  abre el modal explicativo
         window.explainChip('nrs')    →  devuelve el HTML del botoncito "?"
   ============================================================================ */
(function () {
  'use strict';

  function lang() {
    try { return (window.LANG || localStorage.getItem('eco_lang') || 'es'); } catch (e) { return 'es'; }
  }

  var EXPLAIN = {
    tensor_struct: {
      es: { t: '¿Qué es la "Estructura" de una empresa?',
        b: 'Khipus convierte toda la cadena de suministro en una tabla matemática (un <b>tensor</b>): quién le vende a quién, ' +
           'por qué tipo de relación y con qué peso. Con eso calcula, para cada empresa:' +
           '<ul style="margin:10px 0;padding-left:20px;line-height:1.7">' +
           '<li><b>Concentración de proveedores</b> — si depende de muchos proveedores o de uno solo. Alta = si ese proveedor falla, ella sufre mucho.</li>' +
           '<li><b>Países de sus proveedores</b> — de dónde viene lo que compra (riesgo geopolítico real, no solo su sede).</li>' +
           '<li><b>Valor arrastrado si cae</b> — cuánta capitalización de mercado de sus clientes (y clientes de sus clientes) quedaría expuesta. Es su importancia para el sistema, en dólares.</li>' +
           '<li><b>De dónde le llega el riesgo</b> — las empresas cuyo problema más la golpearía, aunque no sean proveedoras directas.</li>' +
           '<li><b>Comparables</b> — empresas con proveedores y clientes parecidos (más útil que "mismo sector").</li></ul>' +
           'Solo cuentan relaciones de suministro reales (no socios ni accionistas). Las capitalizaciones son en vivo o valuaciones verificadas. ' +
           '<b>No es una recomendación</b> de compra ni de venta.' },
      en: { t: 'What is a company\'s "Structure"?',
        b: 'Khipus turns the whole supply chain into a mathematical table (a <b>tensor</b>): who sells to whom, through which kind of ' +
           'relationship and with what weight. From it, for every company it computes:' +
           '<ul style="margin:10px 0;padding-left:20px;line-height:1.7">' +
           '<li><b>Supplier concentration</b> — whether it relies on many suppliers or a single one. High = if that supplier fails, it suffers a lot.</li>' +
           '<li><b>Supplier countries</b> — where what it buys comes from (real geopolitical risk, not just its HQ).</li>' +
           '<li><b>Value dragged down if it fails</b> — how much market cap of its customers (and their customers) would be exposed. Its importance to the system, in dollars.</li>' +
           '<li><b>Where its risk comes from</b> — the companies whose trouble would hit it hardest, even if they are not direct suppliers.</li>' +
           '<li><b>Peers</b> — companies with similar suppliers and customers (more useful than "same sector").</li></ul>' +
           'Only real supply relationships count (not partners or shareholders). Market caps are live or verified valuations. ' +
           '<b>Not a buy or sell recommendation.</b>' } },
    claim_conf: {
      es: { t: '¿Qué es la confianza de una conclusión?',
        b: 'Es qué tan bien <b>respaldada</b> está una conclusión de un agente de IA, de 0 a 100%. <b>No</b> es lo que "dice" la IA: ' +
           'la calcula Khipus combinando seis cosas, y guarda cada una para auditar:' +
           '<ul style="margin:10px 0;padding-left:20px;line-height:1.7">' +
           '<li><b>Calidad de las fuentes</b> (30%) — un estado financiero vale más que un blog.</li>' +
           '<li><b>Fuentes independientes</b> (20%) — tres fuentes distintas valen más que una.</li>' +
           '<li><b>Qué tan recientes</b> (15%) — una noticia de hace un año pesa menos.</li>' +
           '<li><b>Evidencia en contra</b> (15%) — si hay datos que la contradicen, baja.</li>' +
           '<li><b>Seguridad del agente</b> (10%) — lo que declara la IA, con poco peso a propósito.</li>' +
           '<li><b>Datos completos</b> (10%) — si faltaron datos que el agente necesitaba, baja.</li></ul>' +
           'Con una sola fuente nunca pasa de 60%. <b>No es una recomendación</b> de compra ni de venta.' },
      en: { t: 'What is a conclusion\'s confidence?',
        b: 'How well <b>supported</b> an AI agent\'s conclusion is, from 0 to 100%. It is <b>not</b> what the AI "says": ' +
           'Khipus computes it from six factors and stores each one for auditing:' +
           '<ul style="margin:10px 0;padding-left:20px;line-height:1.7">' +
           '<li><b>Source quality</b> (30%) — a financial statement beats a blog.</li>' +
           '<li><b>Independent sources</b> (20%) — three different sources beat one.</li>' +
           '<li><b>Recency</b> (15%) — year-old news weighs less.</li>' +
           '<li><b>Counter-evidence</b> (15%) — data against it lowers it.</li>' +
           '<li><b>Agent certainty</b> (10%) — what the AI declares, deliberately low weight.</li>' +
           '<li><b>Data completeness</b> (10%) — missing data the agent needed lowers it.</li></ul>' +
           'With a single source it never exceeds 60%. <b>It is not</b> a buy or sell recommendation.' },
    },
    horizon: {
      es: { t: '¿Qué es el horizonte?',
        b: 'El plazo en el que aplica una conclusión: <b>Intradía</b> (horas), <b>Corto plazo</b> (días a ~3 meses), ' +
           '<b>Mediano</b> (3-12 meses), <b>Largo</b> (1-5 años) y <b>Estructural</b> (más de 5 años).<br><br>' +
           'Dos agentes pueden "discrepar" sin contradecirse: el técnico puede ver caída a <b>corto</b> plazo y el ' +
           'fundamental crecimiento a <b>largo</b>. La app muestra ambas y no las mezcla.' },
      en: { t: 'What is the horizon?',
        b: 'The time frame a conclusion applies to: <b>Intraday</b> (hours), <b>Short term</b> (days to ~3 months), ' +
           '<b>Medium</b> (3-12 months), <b>Long</b> (1-5 years) and <b>Structural</b> (5+ years).<br><br>' +
           'Two agents can "disagree" without contradicting each other: technical may see a <b>short-term</b> drop while ' +
           'fundamental sees <b>long-term</b> growth. The app shows both and never mixes them.' },
    },
    nrs: {
      es: {
        t: '¿Qué es el NRS?',
        b: '<b>NRS (Nexus Risk Score)</b> es la nota de riesgo de cada empresa, de <b>0 (muy segura)</b> a <b>100 (muy frágil)</b>.' +
           '<br><br>Se calcula sumando 4 ingredientes:' +
           '<ul style="margin:10px 0;padding-left:20px;line-height:1.7">' +
           '<li><b>Geopolítica (hasta 30 pts)</b> — dónde opera: Taiwán o China suman más riesgo que EEUU o Europa.</li>' +
           '<li><b>Concentración de cadena (hasta 25 pts)</b> — cuántos proveedores y clientes <b>de suministro</b> distintos tiene (2,5 pts por cada uno, hasta 10). Solo cuentan relaciones de flujo: suministro, fabricación, nube, licencia, energía, propiedad y despliegue; <b>socios e inversionistas no cuentan</b> y una misma pareja de empresas cuenta una sola vez.</li>' +
           '<li><b>Fundamentales (hasta 25 pts)</b> — la salud del negocio: margen, tamaño, si ya genera ingresos.</li>' +
           '<li><b>Sector (hasta 20 pts)</b> — hay sectores estructuralmente más volátiles (cuántica pre-ingresos) que otros (equipos consolidados).</li>' +
           '</ul>' +
           'Ejemplo: TSMC tiene NRS alto (~60-80) <b>no porque sea mal negocio</b>, sino porque medio mundo depende de sus fábricas en Taiwán — si algo le pasa, arrastra a cientos de empresas.' +
           '<br><br><b>Cómo usarlo:</b> verde (&lt;35) = tranquilo · amarillo (35-60) = vigilar · rojo (&gt;60) = frágil o crítico para la cadena.',
      },
      en: {
        t: 'What is NRS?',
        b: '<b>NRS (Nexus Risk Score)</b> is each company’s risk grade, from <b>0 (very safe)</b> to <b>100 (very fragile)</b>.' +
           '<br><br>It adds up 4 ingredients:' +
           '<ul style="margin:10px 0;padding-left:20px;line-height:1.7">' +
           '<li><b>Geopolitics (up to 30 pts)</b> — where it operates: Taiwan or China add more risk than the US or Europe.</li>' +
           '<li><b>Supply-chain concentration (up to 25 pts)</b> — how many distinct <b>supply</b> suppliers and customers it has (2.5 pts each, up to 10). Only flow relations count: supply, fab, cloud, license, power, ownership and deployment; <b>partners and investors do not count</b> and the same pair of companies counts once.</li>' +
           '<li><b>Fundamentals (up to 25 pts)</b> — business health: margins, size, whether it has real revenue yet.</li>' +
           '<li><b>Sector (up to 20 pts)</b> — some sectors are structurally more volatile (pre-revenue quantum) than others (established equipment makers).</li>' +
           '</ul>' +
           'Example: TSMC has a high NRS (~60-80) <b>not because it’s a bad business</b> — but because half the world depends on its Taiwan fabs; if anything happens to it, hundreds of companies get dragged down.' +
           '<br><br><b>How to read it:</b> green (&lt;35) = calm · yellow (35-60) = watch · red (&gt;60) = fragile or chain-critical.',
      },
    },
    w: {
      es: { t: '¿Qué es el peso (w)?', b: 'Cada conexión entre dos empresas tiene un <b>peso de 1 a 5</b> que mide qué tan crítica es esa relación.<br><br><b>w5</b> = vital (ej. Apple no puede fabricar sin TSMC) · <b>w3</b> = importante · <b>w1</b> = menor o sustituible.<br><br>Las simulaciones usan estos pesos: cuando una empresa cae, el golpe viaja más fuerte por las conexiones de mayor peso.' },
      en: { t: 'What is weight (w)?', b: 'Every connection between two companies has a <b>weight from 1 to 5</b> measuring how critical that relationship is.<br><br><b>w5</b> = vital (e.g. Apple cannot manufacture without TSMC) · <b>w3</b> = important · <b>w1</b> = minor or replaceable.<br><br>Simulations use these weights: when a company falls, the shock travels harder through higher-weight connections.' },
    },
    chokepoint: {
      es: { t: '¿Qué es un chokepoint?', b: 'Un <b>chokepoint</b> (cuello de botella) es una empresa por la que pasa tanta cadena de suministro que, si falla, <b>arrastra a decenas o cientos de empresas</b>.<br><br>Ejemplos reales: <b>ASML</b> (única fabricante de las máquinas EUV sin las que no hay chips avanzados) o <b>TSMC</b> (fabrica los chips de Apple, Nvidia, AMD y Qualcomm).<br><br>Para un inversionista: los chokepoints suelen tener ventajas competitivas enormes (por eso todos dependen de ellos), pero concentran el riesgo sistémico de todo el sector.' },
      en: { t: 'What is a chokepoint?', b: 'A <b>chokepoint</b> is a company that so much of the supply chain flows through that, if it fails, it <b>drags down dozens or hundreds of companies</b>.<br><br>Real examples: <b>ASML</b> (sole maker of the EUV machines without which no advanced chip exists) or <b>TSMC</b> (manufactures the chips of Apple, Nvidia, AMD and Qualcomm).<br><br>For an investor: chokepoints usually enjoy huge competitive moats (that’s why everyone depends on them), but they concentrate the systemic risk of the whole sector.' },
    },
    impact_sum: {
      es: { t: '¿Qué son "afectadas ≥1 %" y "Σ impacto"?', b: 'Cuando simulamos la caída de una empresa, el <b>motor único del servidor</b> (el mismo para el X-Ray, la Cabina, la voz, el mapa y los Insights) calcula cuánto del golpe le llega a cada empresa de la cadena, de 0 a 100 %.<br><br><b>Afectadas ≥1 %</b> = cuántas reciben al menos un 1 % del golpe. <b>≥10 %</b> = las golpeadas fuerte.<br><b>Σ impacto</b> = la suma de todos los golpes, en "empresas equivalentes": 3,5 significa tanto daño como si 3 empresas y media cayeran por completo.<br><br>Ordenamos los cuellos de botella por Σ impacto (no por el conteo) porque una cascada larga de golpes pequeños no es tan grave como pocos golpes fuertes.<br><br>El sello pequeño (p. ej. <b>g18 · base · hace 3 s</b>) dice de qué versión del grafo sale la cifra y hace cuánto se calculó.' },
      en: { t: 'What are "affected ≥1%" and "Σ impact"?', b: 'When we simulate a company failing, the <b>single server engine</b> (the same one for the X-Ray, the Cockpit, voice, the map and Insights) computes how much of the hit reaches each company in the chain, from 0 to 100%.<br><br><b>Affected ≥1%</b> = how many receive at least 1% of the hit. <b>≥10%</b> = the hard-hit ones.<br><b>Σ impact</b> = the sum of all hits, in "company-equivalents": 3.5 means as much damage as three and a half companies failing completely.<br><br>We rank chokepoints by Σ impact (not by the count) because a long cascade of small hits is not as serious as a few strong ones.<br><br>The small stamp (e.g. <b>g18 · database · 3 s ago</b>) tells which version of the graph the figure comes from and how long ago it was computed.' },
    },
    var: {
      es: { t: '¿Qué es el VaR?', b: '<b>VaR (Value at Risk)</b> responde: "en un día malo, ¿cuánto podría perder mi portafolio?"<br><br>Un VaR de $500 al 95% significa: <b>en 19 de cada 20 días, no perderás más de $500</b>. El día 20 (el 5% peor) podrías perder más.<br><br>El <b>CVaR</b> mide justamente eso: cuánto pierdes en promedio en esos días extremos.' },
      en: { t: 'What is VaR?', b: '<b>VaR (Value at Risk)</b> answers: "on a bad day, how much could my portfolio lose?"<br><br>A $500 VaR at 95% means: <b>on 19 out of 20 days you won’t lose more than $500</b>. On day 20 (the worst 5%) you could lose more.<br><br><b>CVaR</b> measures exactly that: your average loss on those extreme days.' },
    },
    vol_ann: {
      es: { t: "¿Qué es la volatilidad?", b: "Cuánto <b>se mueve</b> tu cartera, en promedio, en un año (desviación estándar de los retornos diarios × √252).<br><br>Una volatilidad de 25% quiere decir que en un año típico el valor puede alejarse <b>±25%</b> de su camino normal. Más volatilidad = más sube y baja; no dice si va a subir o bajar." },
      en: { t: "What is volatility?", b: "How much your portfolio <b>moves</b>, on average, over a year (standard deviation of daily returns × √252).<br><br>A 25% volatility means that in a typical year the value can stray <b>±25%</b> from its normal path. More volatility = bigger swings; it does not say whether it will rise or fall." },
    },
    cvar: {
      es: { t: "¿Qué es el CVaR?", b: "El <b>CVaR</b> (o <i>Expected Shortfall</i>) responde: \"<b>cuando</b> me toca uno de esos días malos (el 5% peor), ¿cuánto pierdo <b>en promedio</b>?\".<br><br>Siempre es mayor que el VaR, y por eso los bancos lo prefieren hoy: mira la cola de las pérdidas, no solo su borde." },
      en: { t: "What is CVaR?", b: "<b>CVaR</b> (or <i>Expected Shortfall</i>) answers: \"<b>when</b> one of those bad days hits (the worst 5%), how much do I lose <b>on average</b>?\".<br><br>It is always larger than VaR, which is why banks prefer it today: it looks at the whole tail of losses, not just its edge." },
    },
    var_method: {
      es: { t: "VaR histórico vs paramétrico", b: "<b>Histórico</b>: toma los retornos REALES del último año y mira el 5% peor. No supone nada, pero depende de lo que pasó ese año.<br><br><b>Paramétrico</b>: supone que los retornos siguen una curva normal (campana) con la volatilidad medida. Es suave pero <b>subestima</b> las caídas extremas si el mercado tiene \"colas gordas\".<br><br>Si ambos se parecen, el número es robusto. A <b>N días</b> se escala por √N (regla estándar de Basilea)." },
      en: { t: "Historical vs parametric VaR", b: "<b>Historical</b>: takes the REAL returns of the last year and looks at the worst 5%. It assumes nothing, but depends on what happened that year.<br><br><b>Parametric</b>: assumes returns follow a normal (bell) curve with the measured volatility. It is smooth but <b>underestimates</b> extreme drops when markets have \"fat tails\".<br><br>If both are close, the number is robust. For <b>N days</b> it scales by √N (standard Basel rule)." },
    },
    beta: {
      es: { t: "¿Qué es la beta?", b: "Cuánto se mueve tu cartera cuando se mueve el mercado (S&amp;P 500).<br><br><b>Beta 1</b> = igual que el mercado. <b>1,5</b> = si el mercado cae 10%, tu cartera tiende a caer ~15%. <b>0,5</b> = la mitad. La <b>correlación</b> dice qué tan \"pegada\" va al mercado (1 = totalmente)." },
      en: { t: "What is beta?", b: "How much your portfolio moves when the market (S&amp;P 500) moves.<br><br><b>Beta 1</b> = same as the market. <b>1.5</b> = if the market drops 10%, your portfolio tends to drop ~15%. <b>0.5</b> = half. <b>Correlation</b> says how tightly it tracks the market (1 = fully)." },
    },
    drawdown: {
      es: { t: "¿Qué es la máxima caída?", b: "La peor caída desde un máximo hasta un mínimo en el período: \"si hubieras comprado en el peor momento, ¿cuánto llegaste a perder antes de recuperarte?\". Mide el <b>dolor real</b> que habría que aguantar." },
      en: { t: "What is max drawdown?", b: "The worst fall from a peak to a trough in the period: \"had you bought at the worst moment, how much would you have been down before recovering?\". It measures the <b>real pain</b> you would have had to endure." },
    },
    sharpe: {
      es: { t: "¿Qué es el Sharpe?", b: "Retorno por unidad de riesgo: (retorno anual <b>compuesto</b> − tasa libre de riesgo) ÷ volatilidad anual. La tasa libre de riesgo es la del T-bill de EE.UU. a 13 semanas (^IRX), en vivo; si no se pudo bajar, se usa 0 y se dice.<br><br>Más de <b>1</b> es bueno; más de <b>2</b>, muy bueno. Es una foto del pasado, no garantiza el futuro." },
      en: { t: "What is Sharpe?", b: "Return per unit of risk: (<b>compounded</b> annual return − risk-free rate) ÷ annual volatility. The risk-free rate is the live US 13-week T-bill (^IRX); if it could not be fetched, 0 is used and the report says so.<br><br>Above <b>1</b> is good; above <b>2</b>, very good. It is a snapshot of the past, not a guarantee." },
    },
    risk_contrib: {
      es: { t: "¿Qué es la contribución al riesgo?", b: "Qué parte de la volatilidad total la <b>pone cada acción</b>. Suma 100%.<br><br>Si una acción pesa 20% de tu dinero pero aporta 45% del riesgo, es la que más mueve tu cartera: está <b>concentrando el riesgo</b>. Tiene en cuenta cuánto se mueven juntas (correlaciones)." },
      en: { t: "What is risk contribution?", b: "Which share of total volatility <b>each stock contributes</b>. It sums to 100%.<br><br>If a stock is 20% of your money but contributes 45% of the risk, it is what moves your portfolio most: it is <b>concentrating the risk</b>. It accounts for how stocks move together (correlations)." },
    },
    correlation: {
      es: { t: "¿Qué es la correlación?", b: "Qué tan parecido se mueven dos acciones, de −1 a 1. <b>Cerca de 1</b>: suben y bajan juntas (no diversifican). <b>Cerca de 0</b>: independientes. <b>Negativa</b>: una tiende a subir cuando la otra baja (cubren).<br><br>El <b>ratio de diversificación</b> dice cuánto riesgo te ahorras por combinarlas: 1 = nada; más alto = mejor." },
      en: { t: "What is correlation?", b: "How similarly two stocks move, from −1 to 1. <b>Near 1</b>: they rise and fall together (no diversification). <b>Near 0</b>: independent. <b>Negative</b>: one tends to rise when the other falls (a hedge).<br><br>The <b>diversification ratio</b> says how much risk you save by combining them: 1 = none; higher = better." },
    },
    backtest: {
      es: { t: "¿Qué es el backtest del VaR?", b: "Comprueba si el VaR fue honesto <b>fuera de muestra</b>: cada día se calcula el VaR 95% solo con los ~125 días anteriores y se cuenta si la pérdida real de ese día lo <b>superó</b>. Lo esperado es ~5% de los días. La <b>prueba de Kupiec</b> dice si la diferencia es casualidad (p alto) o no (p &lt; 0,05).<br><br>Muchas más veces y p bajo = el VaR está <b>subestimando</b> el riesgo. (El viejo conteo dentro de la misma muestra siempre daba ≈5% por construcción: no medía nada.)" },
      en: { t: "What is the VaR backtest?", b: "It checks whether the VaR was honest <b>out of sample</b>: each day the 95% VaR is computed only from the previous ~125 days and we count whether that day's real loss <b>exceeded</b> it. About 5% of days are expected. The <b>Kupiec test</b> says whether the difference is chance (high p) or not (p &lt; 0.05).<br><br>Many more breaches with a low p = the VaR is <b>underestimating</b> risk. (The old in-sample count always gave ≈5% by construction: it measured nothing.)" },
    },
    vega: {
      es: { t: "¿Qué es la Vega (o Kappa)?", b: "La <b>Vega</b> mide la <b>sensibilidad</b> de una posición ante los cambios en la <b>volatilidad</b> del mercado: cuánto cambia el valor de tus <b>opciones</b> si la <b>volatilidad</b> del mercado sube o baja <b>1 punto</b> (por ejemplo de 30% a 31%). En algunos bancos, como Morgan Stanley, se le llama <b>Kappa</b>.<br><br>Vega de <b>+$500</b> = si la volatilidad sube 1 punto, ganas ~$500; si baja 1 punto, pierdes ~$500. Comprar opciones da Vega positiva; venderlas, negativa.<br><br>Las <b>acciones tienen Vega 0</b>: su valor no depende directamente de la volatilidad." },
      en: { t: "What is Vega (or Kappa)?", b: "<b>Vega</b> measures how much the value of your <b>options</b> changes if market <b>volatility</b> rises or falls by <b>1 point</b> (e.g. from 30% to 31%). At some banks, like Morgan Stanley, it is called <b>Kappa</b>.<br><br>Vega of <b>+$500</b> = if volatility rises 1 point you gain ~$500; if it falls 1 point you lose ~$500. Buying options gives positive Vega; selling them, negative.<br><br><b>Stocks have zero Vega</b>: their value does not depend directly on volatility." },
    },
    iv: {
      es: { t: "¿Qué es la volatilidad implícita?", b: "Es la volatilidad que el <b>mercado</b> está \"cobrando\" en el precio de una opción: lo que los operadores esperan que se mueva la acción hasta el vencimiento.<br><br>Aquí se usa la publicada para ese contrato exacto. Si no está publicada, se usa la volatilidad <b>histórica</b> del último año, y se avisa." },
      en: { t: "What is implied volatility?", b: "It is the volatility the <b>market</b> is \"charging\" in an option's price: how much traders expect the stock to move until expiry.<br><br>Here we use the one published for that exact contract. If it isn't published, the stock's <b>historical</b> volatility of the last year is used, and we say so." },
    },
    greeks: {
      es: { t: "Delta, Gamma y Theta", b: "<b>Delta</b>: a cuántas acciones equivale tu posición en opciones (si la acción sube $1, ganas ~Delta dólares).<br><b>Gamma</b>: cuánto cambia la Delta cuando la acción se mueve.<br><b>Theta</b>: cuánto valor pierden tus opciones por cada día que pasa, aunque nada más cambie (el \"costo del tiempo\")." },
      en: { t: "Delta, Gamma and Theta", b: "<b>Delta</b>: how many shares your option position is equivalent to (if the stock rises $1, you gain ~Delta dollars).<br><b>Gamma</b>: how much Delta changes when the stock moves.<br><b>Theta</b>: how much value your options lose each day that passes, even if nothing else changes (the \"cost of time\")." },
    },
    delta: {
      es: { t: "¿Qué es la Delta?", b: "La <b>Delta</b> describe la relación <b>lineal</b> de tu posición con la acción (el activo subyacente): si la acción sube <b>$1</b>, tu posición gana aproximadamente <b>Delta</b> dólares.<br><br>Aquí se muestra en \"acciones equivalentes\": una Delta de +150 se comporta como tener 150 acciones. Una acción tiene Delta 1; un call, entre 0 y 1; un put, entre −1 y 0." },
      en: { t: "What is Delta?", b: "<b>Delta</b> describes the <b>linear</b> relationship between your position and the stock (the underlying asset): if the stock rises <b>$1</b>, your position gains about <b>Delta</b> dollars.<br><br>Shown here as \"equivalent shares\": a Delta of +150 behaves like holding 150 shares. A share has Delta 1; a call, between 0 and 1; a put, between −1 and 0." },
    },
    gamma: {
      es: { t: "¿Qué es la Gamma?", b: "La <b>Gamma</b> es la <b>segunda derivada</b> respecto al precio de la acción: cuánto cambia la Delta cuando la acción se mueve $1. Añade la <b>curvatura (convexidad)</b> al riesgo.<br><br>Gamma alta = tu exposición cambia rápido cuando el precio se mueve (la Delta sola se queda corta). Comprar opciones da Gamma positiva; venderlas, negativa." },
      en: { t: "What is Gamma?", b: "<b>Gamma</b> is the <b>second derivative</b> with respect to the stock price: how much Delta changes when the stock moves $1. It adds <b>curvature (convexity)</b> to the risk.<br><br>High Gamma = your exposure changes fast when the price moves (Delta alone falls short). Buying options gives positive Gamma; selling them, negative." },
    },
    theta: {
      es: { t: "¿Qué es la Theta?", b: "La <b>Theta</b> mide cómo cambia el valor de tu cartera <b>a medida que pasa el tiempo</b>, suponiendo que nada más cambia en el mercado.<br><br>Theta de <b>−$20</b> = cada día que pasa tus opciones valen ~$20 menos (el \"costo del tiempo\"). Quien compra opciones suele tener Theta negativa; quien las vende, positiva." },
      en: { t: "What is Theta?", b: "<b>Theta</b> measures how your portfolio's value changes <b>as time passes</b>, assuming nothing else in the market changes.<br><br>Theta of <b>−$20</b> = each day that passes your options are worth ~$20 less (the \"cost of time\"). Option buyers usually have negative Theta; sellers, positive." },
    },
    // batch I2 (riesgo robusto, BRECHAS L2-09/10/14/15/16/18): cada métrica nueva con su "?"
    vol_ewma: {
      es: { t: "¿Qué es la volatilidad EWMA?", b: "Es la volatilidad que da <b>más peso a los días recientes</b> (método RiskMetrics de J.P. Morgan, λ = 0,94: el día de ayer pesa ~6 %, hace un mes ~1 %).<br><br>Si está <b>por encima</b> de la volatilidad de todo el año, el mercado se puso más nervioso últimamente; si está por debajo, se calmó. No predice: solo reacciona más rápido." },
      en: { t: "What is EWMA volatility?", b: "Volatility that gives <b>more weight to recent days</b> (J.P. Morgan RiskMetrics, λ = 0.94: yesterday weighs ~6%, a month ago ~1%).<br><br>If it is <b>above</b> the full-year volatility, the market got more nervous lately; below, it calmed down. It does not predict: it just reacts faster." },
    },
    shrinkage: {
      es: { t: "¿Qué es la contracción de Ledoit-Wolf?", b: "Con muchas acciones y pocos días, la tabla de \"cuánto se mueven juntas\" (covarianza) sale <b>ruidosa</b> y hasta inservible para cálculos. Ledoit-Wolf la <b>acerca un poco</b> a una tabla simple y estable; cuánto, lo decide la propia muestra (0 = nada, 1 = todo).<br><br>Así el riesgo de una cartera grande (por ejemplo 60 posiciones) nunca sale roto." },
      en: { t: "What is Ledoit-Wolf shrinkage?", b: "With many stocks and few days, the table of \"how they move together\" (covariance) comes out <b>noisy</b>, even unusable for calculations. Ledoit-Wolf <b>pulls it a little</b> toward a simple, stable table; how much is decided by the sample itself (0 = none, 1 = all).<br><br>So the risk of a large portfolio (say 60 positions) never comes out broken." },
    },
    var_nd: {
      es: { t: "VaR y CVaR a varios días", b: "La pérdida de un mal escenario a <b>N días</b> (por ejemplo 10), calculada de tres formas:<ul style=\"margin:8px 0;padding-left:20px;line-height:1.6\"><li><b>Histórico</b>: los retornos REALES de N días seguidos (ventanas que se superponen). El CVaR es el promedio del peor 5%.</li><li><b>Normal</b>: con la volatilidad medida × √N.</li><li><b>Cornish-Fisher</b>: la normal corregida por la <b>asimetría</b> y las <b>colas gordas</b> de tus retornos (si tu cartera tiene caídas bruscas, sale más alto).</li></ul>Las ventanas superpuestas no son independientes: con un año hay pocas ventanas \"de verdad\" distintas." },
      en: { t: "Multi-day VaR and CVaR", b: "The loss in a bad scenario over <b>N days</b> (e.g. 10), computed three ways:<ul style=\"margin:8px 0;padding-left:20px;line-height:1.6\"><li><b>Historical</b>: REAL N-day returns (overlapping windows). CVaR is the average of the worst 5%.</li><li><b>Normal</b>: the measured volatility × √N.</li><li><b>Cornish-Fisher</b>: the normal corrected for the <b>skew</b> and <b>fat tails</b> of your returns (if your portfolio has sharp drops, it comes out higher).</li></ul>Overlapping windows are not independent: one year holds few truly distinct windows." },
    },
    sharpe_arith: {
      es: { t: "Sharpe aritmético (el estándar)", b: "(Retorno <b>promedio</b> diario − tasa libre de riesgo) × 252 ÷ volatilidad anual. Es como lo calculan bancos y fondos. La tasa del T-bill (^IRX) se publica como <b>tasa de descuento</b>; aquí se convierte a <b>rendimiento equivalente</b> (365·d / (360 − 91·d)).<br><br>Suele salir un poco más alto que el Sharpe con retorno compuesto en acciones muy movidas." },
      en: { t: "Arithmetic Sharpe (the standard)", b: "(<b>Average</b> daily return − risk-free rate) × 252 ÷ annual volatility. It is how banks and funds compute it. The T-bill rate (^IRX) is quoted as a <b>discount rate</b>; here it is converted to an <b>equivalent yield</b> (365·d / (360 − 91·d)).<br><br>It usually comes out a bit higher than the compounded-return Sharpe for very volatile stocks." },
    },
    liquidity: {
      es: { t: "¿Qué es la liquidez (días para vender)?", b: "Cuántos días tardarías en vender la posición <b>sin mover el precio</b>, vendiendo como máximo el 20% del volumen que se negocia en un día normal (promedio de 20 días, volumen REAL del proveedor).<br><br>Más de <b>5 días</b> se marca: en una caída fuerte podrías no salir a tiempo. Sin dato de volumen no se calcula (nunca se inventa)." },
      en: { t: "What is liquidity (days to sell)?", b: "How many days it would take to sell the position <b>without moving the price</b>, selling at most 20% of a normal day's traded volume (20-day average, REAL provider volume).<br><br>More than <b>5 days</b> is flagged: in a sharp drop you might not get out in time. Without volume data it is not computed (never invented)." },
    },
    dollar_delta: {
      es: { t: "¿Qué es la Delta en dólares?", b: "La Delta en acciones no se puede sumar entre empresas distintas (100 acciones de NVIDIA no son 100 de ASML). La <b>Delta en dólares</b> (Delta × precio × acciones, en USD) sí: dice cuántos dólares ganas o pierdes si <b>todas</b> las acciones suben 1%… multiplicado por 100.<br><br>Por eso el total en acciones y la Gamma solo se muestran <b>por empresa</b>." },
      en: { t: "What is dollar Delta?", b: "Delta in shares cannot be added across different companies (100 NVIDIA shares are not 100 ASML shares). <b>Dollar Delta</b> (Delta × price × shares, in USD) can: it says how many dollars you gain or lose if <b>every</b> stock rises 1%… times 100.<br><br>That is why the share total and Gamma are only shown <b>per company</b>." },
    },
    rp_capped: {
      es: { t: "Paridad de riesgo con topes", b: "La <b>paridad de riesgo</b> reparte el dinero para que cada empresa aporte el <b>mismo riesgo</b>. Después se aplican tus topes (por empresa, sector y país) y eso <b>rompe un poco</b> el reparto igual.<br><br>Por eso se rotula «con topes» y se muestra cuánto aporta la que menos y la que más (lo ideal sería que todas aporten lo mismo)." },
      en: { t: "Capped risk parity", b: "<b>Risk parity</b> splits the money so every company brings the <b>same risk</b>. Then your caps (per company, sector and country) are applied, and that <b>bends</b> the equal split a little.<br><br>That is why it is labelled «capped» and shows how much the lowest and highest contributor bring (ideally all would bring the same)." },
    },
    // paso 12 (INFRA_OPERATIVA): gobernanza de las reglas y el motor de contagio versionado
    gov_release: {
      es: { t: '¿Qué es el "release" y por qué se activa con tu PIN?',
        b: 'Las reglas y los números de Khipus (cómo se contagia una crisis, la fórmula del riesgo NRS, los límites del corretaje…) ' +
           'son <b>versiones guardadas con huella digital</b>. El conjunto vigente se llama <b>release</b>.<br><br>' +
           'Una versión nueva llega con un despliegue pero <b>no manda</b> hasta que tú la activas con tu PIN. Antes puedes ver ' +
           '<b>«¿Qué cambia?»</b>: Khipus recalcula todas las simulaciones con la versión nueva SIN tocar la vigente y te muestra las diferencias.<br><br>' +
           'Cada activación queda registrada con tu nombre y la hora, y nunca se borra. <b>Deshacer</b> es activar la versión anterior (también queda registrado).' },
      en: { t: 'What is the "release" and why is it activated with your PIN?',
        b: 'Khipus\' rules and numbers (how a crisis spreads, the NRS risk formula, brokerage limits…) are <b>versions saved with a ' +
           'digital fingerprint</b>. The set in force is called the <b>release</b>.<br><br>' +
           'A new version arrives with a deploy but <b>does not rule</b> until you activate it with your PIN. Before that you can see ' +
           '<b>"What changes?"</b>: Khipus recomputes every simulation with the new version WITHOUT touching the current one and shows you the differences.<br><br>' +
           'Every activation is recorded with your name and the time, and is never deleted. <b>Undo</b> means activating the previous version (also recorded).' } },
    kernel_v2: {
      es: { t: '¿Qué cambia con el motor de contagio 2.0.0?',
        b: '<ul style="margin:6px 0;padding-left:20px;line-height:1.7">' +
           '<li><b>Solo contagian las relaciones de suministro</b> (fabricación, nube, licencias, energía, propiedad, despliegue). Una alianza o una inversión ya no ' +
           'cuenta como si te dejaran sin piezas; se muestran aparte como «relacionadas».</li>' +
           '<li><b>La gravedad de las crisis usa su escala real 0-10</b>: al disparar una crisis nadie arranca por encima del 100 %.</li>' +
           '<li><b>Los auges de demanda</b> se calculan con el mismo motor: un vínculo débil ya no le pasa todo el auge a un proveedor.</li>' +
           '<li><b>«Estrés severo»</b> ahora agrava el golpe (antes, por un error de fórmula, lo suavizaba).</li>' +
           '<li><b>Los cuellos de botella</b> se ordenan por la fuerza total del golpe, no por cuántas empresas toca un poquito.</li>' +
           '<li><b>Simulación por agentes</b>: los % salen del motor; la IA solo explica.</li></ul>' +
           'El NRS no cambia. Son estimaciones estructurales, <b>no precios</b> ni recomendaciones.' },
      en: { t: 'What changes with contagion engine 2.0.0?',
        b: '<ul style="margin:6px 0;padding-left:20px;line-height:1.7">' +
           '<li><b>Only supply relationships spread damage</b> (manufacturing, cloud, licenses, power, ownership, deployment). An alliance or an investment no longer ' +
           'counts as if it left you without parts; they are shown separately as "related".</li>' +
           '<li><b>Crisis severity uses its real 0-10 scale</b>: when a crisis fires nobody starts above 100%.</li>' +
           '<li><b>Demand booms</b> are computed with the same engine: a weak link no longer passes the whole boom to a supplier.</li>' +
           '<li><b>"Severe stress"</b> now worsens the hit (before, due to a formula error, it softened it).</li>' +
           '<li><b>Chokepoints</b> are ranked by the total strength of the hit, not by how many companies they touch slightly.</li>' +
           '<li><b>Agent simulation</b>: the % come from the engine; the AI only explains.</li></ul>' +
           'The NRS does not change. These are structural estimates, <b>not prices</b> or recommendations.' } },
    // pasos 11, 22 y 26 (INFRA_OPERATIVA): Puertas en bloqueo, guardia «sin decisión no hay cambio», retención
    gov_gates_7d: {
      es: { t: '¿Qué son las «Puertas» y el resumen de 7 días?',
        b: 'Las puertas son <b>reglas que revisan cada cambio del grafo</b> antes de guardarlo (por ejemplo: un vínculo de una empresa consigo misma, un peso fuera de 1-6, un campo que no existe). ' +
           'Hoy están en <b>sombra</b>: solo avisan y queda registrado, no rechazan nada.<br><br>' +
           'El resumen cuenta los avisos de los últimos 7 días por regla y <b>cuántas escrituras se habrían rechazado</b> con la versión 2.0.0 (bloqueo). ' +
           'Si ese número es 0 o lo que sale está mal de verdad, puedes activar el bloqueo con tu PIN en Gobernanza; se deshace volviendo a la versión anterior. Las órdenes de dinero no cambian.' },
      en: { t: 'What are the "Gates" and the 7-day summary?',
        b: 'Gates are <b>rules that check every graph change</b> before it is saved (for example: a link from a company to itself, a weight outside 1-6, a field that does not exist). ' +
           'Today they are in <b>shadow</b>: they only warn and it is recorded, nothing is rejected.<br><br>' +
           'The summary counts the warnings of the last 7 days per rule and <b>how many writes would have been rejected</b> with version 2.0.0 (blocking). ' +
           'If that number is 0, or what shows up is really wrong, you can activate blocking with your PIN in Governance; undo by going back to the previous version. Money orders do not change.' } },
    gov_guard: {
      es: { t: '¿Qué es la «guardia sin decisión no hay cambio»?',
        b: 'Khipus anota en un libro que nadie puede borrar <b>cada decisión</b> (quién, qué, con qué datos). La guardia es una regla de la base de datos que mira las tablas importantes ' +
           '(órdenes, clientes, memos del comité, conclusiones, propuestas, alertas, ajustes de IA) y <b>cuenta cada cambio que llegó sin su decisión en el libro</b>.<br><br>' +
           'Hoy solo <b>cuenta</b> (modo aviso). Cuando el contador lleve una semana en 0, puedes pasarla a <b>bloquear</b> con tu PIN (versión 2.0.0): desde ahí, un cambio sin decisión no se guarda.' },
      en: { t: 'What is the "no decision, no change" guard?',
        b: 'Khipus writes <b>every decision</b> (who, what, with which data) to a ledger nobody can erase. The guard is a database rule that watches the important tables ' +
           '(orders, clients, committee memos, conclusions, proposals, alerts, AI settings) and <b>counts every change that arrived without its decision in the ledger</b>.<br><br>' +
           'Today it only <b>counts</b> (warn mode). Once the counter has been at 0 for a week, you can switch it to <b>block</b> with your PIN (version 2.0.0): from then on, a change without a decision is not saved.' } },
    gov_retention: {
      es: { t: '¿Qué es la «retención»?',
        b: 'Lo que tiene que ver con <b>dinero, el grafo, el comité y las reglas se guarda para siempre</b>. Las preguntas del chat y las simulaciones «qué pasaría si» se guardan <b>90 días</b>.<br><br>' +
           'Pasado ese plazo, una tarea diaria vacía su contenido pero <b>conserva su huella</b> (un código único): así se puede seguir demostrando que el libro no fue alterado. Cada vaciado queda registrado como una decisión.' },
      en: { t: 'What is "retention"?',
        b: 'Everything about <b>money, the graph, the committee and the rules is kept forever</b>. Chat questions and "what if" simulations are kept <b>90 days</b>.<br><br>' +
           'After that, a daily task empties their content but <b>keeps their fingerprint</b> (a unique code): so it can still be proven that the ledger was not altered. Every purge is recorded as a decision.' } },
    // paso 25 (INFRA_OPERATIVA): flujo de gobernanza completo — proponer, regresión, programar, ¿qué cambia para mí?
    gov_propose: {
      es: { t: '¿Qué es «Proponer cambio»?',
        b: 'Puedes pedir que un número de las reglas cambie (por ejemplo, cuánto se debilita una crisis en cada paso de la cadena, o el umbral del comité para sugerir comprar). ' +
           'Solo se pueden mover los números que Khipus marca como ajustables y <b>dentro de su rango</b>; lo demás se cambia con una actualización del código.<br><br>' +
           'Proponer <b>no cambia nada todavía</b>: queda guardado con tu PIN como una versión nueva, Khipus calcula qué cambiaría y tú decides si activarla. ' +
           'Si el cambio altera números, es un cambio <b>mayor</b> (por ahora solo tú lo apruebas).' },
      en: { t: 'What is "Propose a change"?',
        b: 'You can ask for a number in the rules to change (for example, how much a crisis weakens at each step of the chain, or the committee threshold to suggest buying). ' +
           'Only the numbers Khipus marks as adjustable can move, and <b>within their range</b>; everything else changes with a code update.<br><br>' +
           'Proposing <b>changes nothing yet</b>: it is saved with your PIN as a new version, Khipus computes what would change and you decide whether to activate it. ' +
           'If the change alters numbers it is a <b>major</b> change (for now only you approve it).' } },
    gov_regression: {
      es: { t: '¿Qué es la «regresión contrafactual»?',
        b: 'Antes de activar una versión, Khipus <b>vuelve a calcular con ella</b> lo que ya pasó, sin tocar lo vigente: las simulaciones «qué pasaría si» que hiciste en los últimos 30 días, ' +
           'la caída de cada empresa del grafo, los memos del comité, los controles de monto de las órdenes recientes y el NRS.<br><br>' +
           'Te dice <b>cuántos resultados cambiarían</b>. Si una versión dice ser «menor» pero cambia resultados, te avisa. Queda registrado y no se borra.' },
      en: { t: 'What is the "counterfactual regression"?',
        b: 'Before activating a version, Khipus <b>recomputes with it</b> what already happened, without touching what is in force: the what-if simulations you ran in the last 30 days, ' +
           'the fall of every company in the graph, the committee memos, the amount checks of recent orders and the NRS.<br><br>' +
           'It tells you <b>how many results would change</b>. If a version claims to be "minor" but changes results, it warns you. It is recorded and never deleted.' } },
    gov_schedule: {
      es: { t: '¿Qué es «Programar» un cambio?',
        b: 'En vez de activar ya, eliges <b>cuándo</b> entra en vigor (por ejemplo, después del cierre de la bolsa). Hasta esa hora nada cambia y puedes <b>cancelarlo</b>.<br><br>' +
           'Los límites del corretaje se aplican por defecto después del cierre de Nueva York, para no cambiar las reglas a mitad de una sesión. Mientras haya un cambio programado no se activa otro (para que uno no pise al otro).' },
      en: { t: 'What is "Schedule" a change?',
        b: 'Instead of activating now, you choose <b>when</b> it takes effect (for example, after the market close). Until then nothing changes and you can <b>cancel it</b>.<br><br>' +
           'Brokerage limits apply by default after the New York close, so rules do not change in the middle of a session. While a change is scheduled no other one is activated (so one does not overwrite the other).' } },
    gov_for_me: {
      es: { t: '¿Cómo se calcula «¿Qué cambia para mí?»?',
        b: 'Para cada empresa de <b>tus posiciones</b> (si no tienes, las 10 más críticas del grafo) Khipus compara, con la versión vigente y con la nueva: ' +
           'el <b>peor golpe</b> que puede recibir si cae cualquier otra empresa, y <b>a cuántas arrastra</b> si cae ella.<br><br>' +
           'Para reglas que no son del motor (comité, corretaje…) te muestra los números que cambian, con su nombre. Son estimaciones estructurales, <b>no precios</b>.' },
      en: { t: 'How is "What changes for me?" computed?',
        b: 'For each company in <b>your positions</b> (if you have none, the 10 most critical in the graph) Khipus compares, with the version in force and with the new one: ' +
           'the <b>worst hit</b> it can take if any other company fails, and <b>how many it drags</b> if it fails.<br><br>' +
           'For rules outside the engine (committee, brokerage…) it shows you the numbers that change, by name. These are structural estimates, <b>not prices</b>.' } },
    audit_replay: {
      es: { t: '¿Qué es «Repetir» una decisión?',
        b: 'Khipus vuelve a hacer el <b>mismo cálculo</b> con lo que el sistema <b>sabía en ese momento</b>: los datos que guardó, el grafo ' +
           'tal como estaba (su versión), las <b>reglas y números aprobados</b> que regían entonces (aunque hoy rijan otros) y el mismo código.<br><br>' +
           'Si sale igual, la decisión es <b>auditable</b>: cualquiera puede comprobar que se tomó con esos datos. Cada noche se repiten solas ' +
           '50 decisiones al azar y todas las de dinero. Lo que escribió una IA <b>no se vuelve a pedir</b> (sería otra respuesta): solo se ' +
           'comprueba que su texto y sus cifras son los guardados.' },
      en: { t: 'What does "Replay" a decision mean?',
        b: 'Khipus redoes the <b>same computation</b> with what the system <b>knew at that moment</b>: the data it stored, the graph ' +
           'as it was (its version), the <b>approved rules and numbers</b> in force then (even if others rule today) and the same code.<br><br>' +
           'If it comes out the same, the decision is <b>auditable</b>: anyone can check it was taken with that data. Every night 50 random ' +
           'decisions and all money ones are replayed automatically. Text written by an AI is <b>never asked again</b> (it would be a different ' +
           'answer): only its stored text and figures are checked.' } },
    audit_verdict: {
      es: { t: '¿Qué significan «idéntica», «distinta» y «no repetible»?',
        b: '<b>✓ Idéntica</b>: al repetirla sale exactamente lo mismo (todas las cifras, sin redondeos).<br>' +
           '<b>≠ Distinta</b>: algo no coincide; se muestra qué campo y los dos valores. Pasa si cambió el código que la calcula o si algo del registro ' +
           'no cuadra: el 🩺 se pone en rojo para que lo revises.<br>' +
           '<b>— No repetible</b>: no tiene un cálculo que repetir, y se dice por qué: es texto de IA, sus datos se vaciaron a los 90 días (queda la huella), ' +
           'usó precios en vivo que no se guardaron completos, o es anterior a este registro. <b>Nunca se inventa</b> lo que falta.<br>' +
           '<b>aproximada</b> (etiqueta amarilla): se repitió, pero con una salvedad que se explica debajo del veredicto.' },
      en: { t: 'What do "identical", "different" and "not replayable" mean?',
        b: '<b>✓ Identical</b>: replaying it gives exactly the same (every figure, no rounding).<br>' +
           '<b>≠ Different</b>: something does not match; the field and both values are shown. It happens if the code that computes it changed or ' +
           'something in the record does not add up: the 🩺 turns red so you review it.<br>' +
           '<b>— Not replayable</b>: there is no computation to repeat, and it says why: it is AI text, its data was emptied after 90 days (the ' +
           'fingerprint stays), it used live prices that were not fully stored, or it predates this record. What is missing is <b>never invented</b>.<br>' +
           '<b>approximate</b> (yellow tag): it was replayed, but with a caveat explained under the verdict.' } },
    audit_approx: {
      es: { t: '¿Qué significa «aproximada»?',
        b: 'El cálculo se repitió y se comparó, pero <b>algo de lo que se usó para repetirlo no es exactamente lo de entonces</b>, y Khipus te dice qué: ' +
           'por ejemplo, la versión del grafo salió del sello de la ficha y no de la vista que se leyó, fue un viaje a una fecha pasada, la base de datos ' +
           'se restauró, o un memo viejo se repitió con el paquete guardado del comité.<br><br>' +
           '«✓ Idéntica» + «aproximada» = <b>mismo resultado</b>, con esa salvedad escrita debajo. «≠ Distinta» + «aproximada» = revisa primero esa ' +
           'salvedad: puede explicar la diferencia.' },
      en: { t: 'What does "approximate" mean?',
        b: 'The computation was repeated and compared, but <b>something used to repeat it is not exactly what was used then</b>, and Khipus tells you what: ' +
           'for example, the graph version came from the record stamp rather than from the view that was read, it was a trip to a past date, the database ' +
           'was restored, or an old memo was replayed from the stored committee package.<br><br>' +
           '"✓ Identical" + "approximate" = <b>same result</b>, with that caveat written below. "≠ Different" + "approximate" = check that caveat first: ' +
           'it may explain the difference.' } },
    audit_why: {
      es: { t: '¿Qué muestra «¿Por qué?»?',
        b: 'La ficha de la decisión en lenguaje simple: <b>qué</b> se decidió y cómo terminó, <b>quién</b> (una persona con PIN, un agente, una tarea ' +
           'automática o una IA externa), <b>cuándo</b>, <b>con qué conocimiento</b> (versión del grafo y versión de cada regla), cuánta <b>evidencia</b> citó, ' +
           'qué <b>puertas de validación</b> avisaron y los resultados posteriores. Sin tu PIN no se muestran nombres de personas ni datos de clientes.' },
      en: { t: 'What does "Why?" show?',
        b: 'The decision record in plain language: <b>what</b> was decided and how it ended, <b>who</b> (a person with PIN, an agent, an automatic ' +
           'task or an external AI), <b>when</b>, <b>with what knowledge</b> (graph version and version of every rule), how much <b>evidence</b> it cited, ' +
           'which <b>validation gates</b> warned and later outcomes. Without your PIN, people names and client data are not shown.' } },
    choke_sum: {
      es: { t: '¿Qué es el «impacto total» de un cuello de botella?',
        b: 'Si esa empresa cae, sumamos cuánto pierde cada empresa golpeada (100 % = una empresa entera). Un impacto total de 40 equivale a ' +
           '<b>40 empresas completas</b> sin suministro. Ordenar por esto premia a quien golpea <b>fuerte</b>, no a quien toca a muchas un poquito. ' +
           'Junto se muestra cuántas reciben ≥1 % y ≥10 %.' },
      en: { t: 'What is a chokepoint\'s "total impact"?',
        b: 'If that company fails, we add up how much every hit company loses (100% = one whole company). A total impact of 40 equals ' +
           '<b>40 whole companies</b> without supply. Ranking by it rewards whoever hits <b>hard</b>, not whoever touches many slightly. ' +
           'Next to it we show how many get ≥1% and ≥10%.' } },
    dilucion: {
      es: { t: '¿Qué es la dilución?', b: 'Cuando una empresa <b>emite acciones nuevas</b>, tu porción del pastel se achica: eso es <b>dilución</b>.<br><br>Dilución positiva (+%) = imprimieron acciones (malo para ti, salvo que el dinero se invierta muy bien). Dilución negativa (−%) = la empresa <b>recompró</b> acciones: tu porción crece sin que hagas nada (Nvidia y Apple lo hacen).' },
      en: { t: 'What is dilution?', b: 'When a company <b>issues new shares</b>, your slice of the pie shrinks: that’s <b>dilution</b>.<br><br>Positive dilution (+%) = they printed shares (bad for you unless the money is invested brilliantly). Negative dilution (−%) = the company <b>bought back</b> shares: your slice grows while you do nothing (Nvidia and Apple do this).' },
    },
  };

  function ensureModal() {
    if (document.getElementById('xpl-ov')) return;
    var ov = document.createElement('div');
    ov.id = 'xpl-ov';
    ov.style.cssText = 'position:fixed;inset:0;z-index:11000;display:none;align-items:center;justify-content:center;' +
      'background:rgba(3,6,12,.72);backdrop-filter:blur(4px);font-family:Inter,system-ui,sans-serif';
    ov.innerHTML = '<div id="xpl" style="width:min(560px,92vw);max-height:84vh;overflow-y:auto;border-radius:16px;' +
      'background:radial-gradient(700px 400px at 50% -10%,#0B1222 0%,#06090F 60%);border:1px solid rgba(122,158,255,.22);' +
      'box-shadow:0 24px 70px rgba(0,0,0,.6);padding:22px 24px;color:#E8EDFB">' +
      '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">' +
        '<span style="font-size:20px">💡</span><h3 id="xpl-t" style="margin:0;font-size:18px;font-weight:750;flex:1"></h3>' +
        '<button onclick="document.getElementById(\'xpl-ov\').style.display=\'none\'" ' +
          'style="width:30px;height:30px;border-radius:8px;cursor:pointer;border:1px solid rgba(122,158,255,.2);' +
          'background:rgba(21,28,45,.7);color:#7C87A3;font-size:15px">✕</button></div>' +
      '<div id="xpl-b" style="font-size:13.5px;line-height:1.65;color:#C9D4EC"></div></div>';
    ov.addEventListener('click', function (e) { if (e.target === ov) ov.style.display = 'none'; });
    document.body.appendChild(ov);
  }

  window.explainMetric = function (key) {
    var entry = EXPLAIN[key];
    if (!entry) return;
    var L = entry[lang()] || entry.es;
    ensureModal();
    document.getElementById('xpl-t').innerHTML = L.t;
    document.getElementById('xpl-b').innerHTML = L.b;
    document.getElementById('xpl-ov').style.display = 'flex';
  };

  // Registro desde otros módulos (sin editar este archivo):
  //   window.explainRegister('mi_metrica', { es: {t, b}, en: {t, b} })
  window.explainRegister = function (key, entry) {
    if (key && entry && (entry.es || entry.en)) EXPLAIN[key] = entry;
  };

  // botoncito "?" reutilizable — pegarlo junto a cualquier métrica
  window.explainChip = function (key) {
    var tip = lang() === 'en' ? 'What is this?' : '¿Qué es esto?';
    return '<span onclick="event.stopPropagation();window.explainMetric(\'' + key + '\')" title="' + tip + '" ' +
      'style="display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;border-radius:50%;' +
      // tokens de Khipus OS (claro/oscuro); fuera del OS, el cian de siempre
      'border:1px solid color-mix(in srgb,var(--os-accent,#00E0FF) 45%,transparent);color:var(--os-accent,#00E0FF);font-size:10px;font-weight:700;cursor:pointer;' +
      'margin-left:5px;vertical-align:middle;user-select:none">?</span>';
  };
})();
