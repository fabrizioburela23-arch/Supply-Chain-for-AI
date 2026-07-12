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
    nrs: {
      es: {
        t: '¿Qué es el NRS?',
        b: '<b>NRS (Nexus Risk Score)</b> es la nota de riesgo de cada empresa, de <b>0 (muy segura)</b> a <b>100 (muy frágil)</b>.' +
           '<br><br>Se calcula sumando 4 ingredientes:' +
           '<ul style="margin:10px 0;padding-left:20px;line-height:1.7">' +
           '<li><b>Geopolítica (hasta 30 pts)</b> — dónde opera: Taiwán o China suman más riesgo que EEUU o Europa.</li>' +
           '<li><b>Concentración de cadena (hasta 25 pts)</b> — de cuántos proveedores/clientes depende: si todo pasa por una sola empresa, el riesgo sube.</li>' +
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
           '<li><b>Supply-chain concentration (up to 25 pts)</b> — how many suppliers/customers it depends on: if everything flows through one company, risk goes up.</li>' +
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

  // botoncito "?" reutilizable — pegarlo junto a cualquier métrica
  window.explainChip = function (key) {
    var tip = lang() === 'en' ? 'What is this?' : '¿Qué es esto?';
    return '<span onclick="event.stopPropagation();window.explainMetric(\'' + key + '\')" title="' + tip + '" ' +
      'style="display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;border-radius:50%;' +
      'border:1px solid rgba(0,224,255,.45);color:#00E0FF;font-size:10px;font-weight:700;cursor:pointer;' +
      'margin-left:5px;vertical-align:middle;user-select:none">?</span>';
  };
})();
