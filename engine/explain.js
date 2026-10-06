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
      'border:1px solid rgba(0,224,255,.45);color:#00E0FF;font-size:10px;font-weight:700;cursor:pointer;' +
      'margin-left:5px;vertical-align:middle;user-select:none">?</span>';
  };
})();
