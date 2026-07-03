// engine/guide.js — pestaña "❓ Guía": explica la app en lenguaje simple.
// Sin jerga técnica. Expone window.initGuiaTab (mismo patrón que initTKGTab).

(function () {
  'use strict';
  let _built = false;

  const SEC = (title, html) => `
    <div style="margin-bottom:34px">
      <h3 style="font-family:'Fraunces',serif;font-size:18px;font-weight:700;margin:0 0 10px;color:var(--ink-1)">${title}</h3>
      ${html}
    </div>`;

  const TAB_ROWS = [
    ['🗺 Mapa de la Cadena', 'El grafo 3D de las 463 empresas. Arrastra, haz zoom, y clic en cualquier empresa para ver su ficha.'],
    ['📈 Mercado en Vivo', 'Precios en tiempo real y tu portafolio (lo que compras/vendes se guarda en este navegador).'],
    ['📊 Análisis de Red', 'Rankings: quién es más crítico, quién concentra más riesgo.'],
    ['🌍 Geopolítica', 'El mismo mapa, pero coloreado por país y tensiones comerciales.'],
    ['🧬 Simulación', 'Corre escenarios completos (ej. "conflicto en Taiwán") y mide el impacto en toda la cadena.'],
    ['🚀 Espacio', 'Satélites reales en órbita y las empresas que los operan.'],
    ['⌨ Terminal', 'Vista estilo Bloomberg — cotizaciones y gráficos lado a lado.'],
    ['🎨 Canvas IA', 'Pide un gráfico en lenguaje natural ("compara márgenes de Nvidia y AMD") y la IA lo dibuja.'],
    ['◈ Grafo Temporal', 'La novedad: una "máquina del tiempo" de la cadena de suministro. Ver sección de abajo.'],
  ];

  const KHIPU_ROWS = [
    ['TSMC DES', 'abre la ficha de TSMC'],
    ['NVDA RISK', 'muestra el riesgo de Nvidia'],
    ['TSMC SUP', 'quién le abastece a TSMC'],
    ['TSMC SIM', 'simula qué pasa si TSMC cae'],
    ['NVDA THESIS me gusta por su moat', 'guarda esa idea como tesis'],
    ['PORT VAR', 'el riesgo (VaR) de tu portafolio'],
    ['GRAPH ASOF 2020-01-01', 'ver la cadena como era en esa fecha'],
    ['ALERT NVDA PX > 150', 'avisarte si Nvidia sube de $150'],
  ];

  window.initGuiaTab = function () {
    const panel = document.getElementById('guia-panel');
    if (!panel) return;
    if (_built) return;
    _built = true;

    const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    panel.innerHTML = `
      <div style="max-width:820px;margin:0 auto;padding:26px 24px 60px">
        <div style="margin-bottom:8px;font-family:'JetBrains Mono',monospace;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--violet)">Guía rápida</div>
        <h2 style="font-family:'Fraunces',serif;font-size:27px;font-weight:700;margin:0 0 8px">¿Qué es Khipus AI Finance Intelligence?</h2>
        <p style="font-size:14px;line-height:1.6;color:var(--ink-2);margin:0 0 36px;max-width:70ch">
          Un terminal financiero para invertir en la cadena de suministro de semiconductores, IA y espacio —
          463 empresas conectadas por sus relaciones reales (quién fabrica, quién abastece, quién depende de quién).
          Puedes ver precios en vivo, simular crisis geopolíticas, y ahora también <b>registrar tus decisiones de inversión</b>
          con fecha y motivo, para no olvidar por qué compraste o vendiste algo.
        </p>

        ${SEC('Tus 9 pestañas', `
          <div style="display:flex;flex-direction:column;gap:10px">
            ${TAB_ROWS.map(([name, desc]) => `
              <div style="display:flex;gap:14px;align-items:baseline;padding:9px 0;border-bottom:1px solid var(--line)">
                <div style="flex:0 0 190px;font-size:13px;font-weight:700;color:var(--ink-1)">${esc(name)}</div>
                <div style="flex:1;font-size:12.5px;color:var(--ink-3);line-height:1.5">${esc(desc)}</div>
              </div>`).join('')}
          </div>`)}

        ${SEC('Bixby, tu asistente', `
          <p style="font-size:13px;line-height:1.6;color:var(--ink-2);margin:0 0 8px">
            El botón <b>Bixby</b> (arriba a la derecha) abre un cuadro donde puedes <b>escribir o hablar</b> en español normal.
            Ejemplos: <i>"muéstrame el riesgo de TSMC"</i>, <i>"simula qué pasa si China corta las tierras raras"</i>,
            <i>"grafica los márgenes de los 5 fabricantes más grandes"</i>.
          </p>
          <p style="font-size:13px;line-height:1.6;color:var(--ink-2);margin:0">
            Bixby entiende lenguaje natural Y comandos cortos (ver la tabla de "Comandos rápidos" más abajo) —
            los comandos cortos responden al instante, sin esperar a la IA.
          </p>`)}

        ${SEC('◈ Grafo Temporal — la novedad', `
          <p style="font-size:13px;line-height:1.6;color:var(--ink-2);margin:0 0 10px">
            Es un mapa que además <b>recuerda el tiempo</b>: cada relación entre empresas tiene una fecha en que empezó
            (y a veces una fecha en que terminó). Mueve la línea de tiempo y verás cómo la cadena de suministro
            cambió con los años — sanciones, escaseces, nuevos acuerdos.
          </p>
          <div style="display:flex;flex-direction:column;gap:8px;margin-top:12px">
            <div style="font-size:12.5px;color:var(--ink-2)"><b style="color:var(--ink-1)">⚡ Simular caída</b> — clic en una empresa y ves qué otras empresas se ven arrastradas si esa cae (por ejemplo, cuánto arrastra ASML si le pasa algo).</div>
            <div style="font-size:12.5px;color:var(--ink-2)"><b style="color:var(--ink-1)">🏛 Chokepoints</b> — el ranking de qué empresas son más peligrosas de perder (más arrastran si caen).</div>
            <div style="font-size:12.5px;color:var(--ink-2)"><b style="color:var(--ink-1)">🎯 Mi exposición</b> — si tienes posiciones, te dice a qué riesgos ocultos estás expuesto sin saberlo.</div>
            <div style="font-size:12.5px;color:var(--ink-2)"><b style="color:var(--ink-1)">＋ Acción</b> (dentro de la ficha de cada empresa) — crea una tesis de inversión, marca un riesgo, o simplemente anota algo. Queda guardado con fecha y tu nombre.</div>
          </div>`)}

        ${SEC('Guardar tus decisiones', `
          <p style="font-size:13px;line-height:1.6;color:var(--ink-2);margin:0 0 8px">
            <b>📋 Registro</b> (arriba) muestra todo lo que has anotado o decidido — como un diario de inversión.
            <b>🔔 Propuestas</b> muestra sugerencias automáticas (ej. "esta empresa subió de riesgo") que tú apruebas o rechazas —
            nada se guarda sin que tú lo confirmes.
          </p>`)}

        ${SEC('Comandos rápidos (opcional)', `
          <p style="font-size:12.5px;color:var(--ink-3);margin:0 0 12px">Escríbelos en el cuadro de Bixby — no hace falta usarlos, pero son más rápidos que escribir una pregunta completa.</p>
          <div style="border:1px solid var(--line);border-radius:10px;overflow:hidden">
            ${KHIPU_ROWS.map(([cmd, desc], i) => `
              <div style="display:flex;gap:14px;align-items:center;padding:9px 14px;${i % 2 ? 'background:var(--surface-2)' : ''}">
                <code style="flex:0 0 220px;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--violet);font-weight:700">${esc(cmd)}</code>
                <span style="font-size:12.5px;color:var(--ink-2)">${esc(desc)}</span>
              </div>`).join('')}
          </div>`)}

        ${SEC('Preguntas frecuentes', `
          <div style="display:flex;flex-direction:column;gap:14px">
            <div><div style="font-size:13px;font-weight:700;color:var(--ink-1);margin-bottom:3px">¿Se pierden mis datos si cierro el navegador?</div>
              <div style="font-size:12.5px;color:var(--ink-3);line-height:1.5">Tu portafolio (compras/ventas) vive en este navegador. Tus tesis, anotaciones y decisiones (＋ Acción) se guardan en el servidor — sobreviven aunque cambies de computadora.</div></div>
            <div><div style="font-size:13px;font-weight:700;color:var(--ink-1);margin-bottom:3px">¿Necesito usar el Grafo Temporal o los comandos?</div>
              <div style="font-size:12.5px;color:var(--ink-3);line-height:1.5">No — son opcionales. La app funciona perfecto solo con el Mapa, Mercado y Bixby.</div></div>
            <div><div style="font-size:13px;font-weight:700;color:var(--ink-1);margin-bottom:3px">¿Qué hago si algo no responde?</div>
              <div style="font-size:12.5px;color:var(--ink-3);line-height:1.5">Abre 🩺 (arriba) — te dice en vivo qué servicio falló y por qué, sin mostrar ninguna clave.</div></div>
          </div>`)}
      </div>`;
  };
})();
