// engine/guide.js — pestaña "❓ Guía": explica la app en lenguaje simple.
// Sin jerga técnica. Expone window.initGuiaTab (mismo patrón que initTKGTab).
// Actualizada 2026-07-12 (pedido de Fabrizio: "la guía está desactualizada").

(function () {
  'use strict';
  let _built = false;

  const SEC = (title, html) => `
    <div style="margin-bottom:34px">
      <h3 style="font-family:'Fraunces',serif;font-size:18px;font-weight:700;margin:0 0 10px;color:var(--ink-1)">${title}</h3>
      ${html}
    </div>`;

  const TAB_ROWS = [
    ['🗺️ Mapa', 'El universo de las 555 empresas. Sub-modos: ⬡ Cadena (el grafo), 🌐 Geopolítica, 🚀 Espacio, ◈ Grafo Temporal, 🧬 Simulación y 🪐 3D. También puedes entrar al 3D con el botón 🪐 junto al zoom.'],
    ['📈 Mercado', 'Precios en tiempo real y tu portafolio. Sub-modo ₿ Cripto: el mercado cripto explicado — vista Mapa por categorías (qué es cada familia de monedas, en simple), top 100 en vivo, y el Expediente Bixby de las 50 grandes: qué es, cómo funciona, riesgos y catalizadores de cada una, con advertencias ⚠ en las monedas delicadas.'],
    ['🖥️ Terminal', 'Vista estilo Bloomberg: hasta 4 gráficos lado a lado + el panel 📋 Datos a la derecha (ficha, valuación, analistas, fundamentales anuales y cadena de cada empresa). Sub-modos: Terminal, Análisis y Canvas IA.'],
    ['❓ Guía', 'Esta página.'],
  ];

  const WOW_ROWS = [
    ['🎙 Cabina de Bixby', 'Toca el botón Bixby (o Ctrl+K): pantalla completa con botones para TODO — Grafo, Terminal, X-Ray, Simular, Comparar, Oportunidades, Investigar y Gráficos. Escribe o habla en español normal.'],
    ['🔬 X-Ray', 'En la ficha de cualquier empresa: la "desarma" por completo — por qué tiene ese riesgo, todos sus hilos (de quién depende y a quién provee), y la onda de impacto si cae (quién sufre y quién GANA).'],
    ['📊 Dossier financiero', 'En la Terminal, cada empresa tiene un botón 📊 DOSSIER: 8 mini-gráficos con crecimiento de ingresos, dilución, free cash flow, acción, valuación, deuda, márgenes y ROE.'],
    ['◉ Simulación en vivo', 'En el mapa, botón "◉ En vivo": elige un tipo de golpe (corte, auge, precio, sanción) y un objetivo (empresa, sector o país entero) — el mapa se tiñe en tiempo real y ves ganadores y perdedores.'],
    ['🪐 Universo', 'Las 555 empresas flotando en el espacio con estrellas y nebulosas: izquierda→derecha = posición en la cadena, arriba→abajo = riesgo. Clic en una empresa y su cadena se ilumina (verde = le provee, naranja = le compra); doble clic abre su ficha. Funciona en cualquier equipo, sin depender de la tarjeta gráfica.'],
    ['🧠 Investigación profunda', 'Dile a Bixby "investiga la energía nuclear para datacenters" (o cualquier pregunta grande): planifica, reúne el contexto, simula en las matrices y te escribe una tesis con números reales. Tarda ~1 minuto.'],
    ['📡 Radar en vivo', 'La app se mantiene al día SOLA: cada ~10 minutos los agentes leen noticias, recalculan riesgos y hasta incorporan empresas nuevas al grafo (todo auditado y reversible). Verás "● EN VIVO" en el pie.'],
    ['✦ Gráficos al instante', 'Pide "top 10 por riesgo", "márgenes de Nvidia y TSMC", "proveedores de ASML" o "precio de AMD" — salen al instante, sin esperar a la IA (etiqueta "local ⚡").'],
  ];

  const KHIPU_ROWS = [
    ['TSMC XRAY', 'desarma TSMC (el X-Ray completo)'],
    ['SHOCK NVDA', 'simula qué pasa si Nvidia cae'],
    ['COMPARE NVDA AMD', 'compara dos empresas lado a lado'],
    ['INSIGHTS', 'abre el panel de oportunidades y riesgo'],
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
        <h2 style="font-family:'Fraunces',serif;font-size:27px;font-weight:700;margin:0 0 8px">¿Qué es Bixby Finance?</h2>
        <p style="font-size:14px;line-height:1.6;color:var(--ink-2);margin:0 0 36px;max-width:70ch">
          Un terminal financiero para invertir en la cadena de suministro de la IA — <b>555 empresas</b> de
          semiconductores, inteligencia artificial, espacio, energía nuclear, robótica y defensa, conectadas por sus
          <b>1.600+ relaciones reales</b> (quién fabrica, quién abastece, quién depende de quién). Precios en vivo,
          simulaciones de crisis, radiografías de empresas, y un asistente (Bixby) que lo ejecuta todo por ti.
        </p>

        ${SEC('Las 4 pestañas', `
          <div style="display:flex;flex-direction:column;gap:10px">
            ${TAB_ROWS.map(([name, desc]) => `
              <div style="display:flex;gap:14px;align-items:baseline;padding:9px 0;border-bottom:1px solid var(--line)">
                <div style="flex:0 0 150px;font-size:13px;font-weight:700;color:var(--ink-1)">${esc(name)}</div>
                <div style="flex:1;font-size:12.5px;color:var(--ink-3);line-height:1.5">${esc(desc)}</div>
              </div>`).join('')}
          </div>`)}

        ${SEC('Los superpoderes', `
          <div style="display:flex;flex-direction:column;gap:10px">
            ${WOW_ROWS.map(([name, desc]) => `
              <div style="display:flex;gap:14px;align-items:baseline;padding:9px 0;border-bottom:1px solid var(--line)">
                <div style="flex:0 0 190px;font-size:13px;font-weight:700;color:var(--ink-1)">${esc(name)}</div>
                <div style="flex:1;font-size:12.5px;color:var(--ink-3);line-height:1.5">${esc(desc)}</div>
              </div>`).join('')}
          </div>`)}

        ${SEC('Bixby: pídeselo y lo hace', `
          <p style="font-size:13px;line-height:1.6;color:var(--ink-2);margin:0 0 8px">
            Toca <b>Bixby</b> (arriba a la derecha) o presiona <b>Ctrl+K</b>: se abre su pantalla completa.
            Escríbele o háblale en español normal — <i>"desármame Nvidia"</i>, <i>"¿qué pasa si cae TSMC?"</i>,
            <i>"compara Nvidia y AMD"</i>, <i>"dossier de Apple"</i>, <i>"precio de AMD"</i>,
            <i>"investiga la energía nuclear para datacenters"</i>, <i>"muéstrame la terminal"</i>.
            Bixby lo ejecuta y te muestra el resultado en su propio escenario.
          </p>
          <p style="font-size:13px;line-height:1.6;color:var(--ink-2);margin:0">
            Por voz sabe también los datos de cada empresa (empleados, ingresos, fundación, riesgo…) —
            pregúntale lo que quieras mientras miras el mapa.
          </p>`)}

        ${SEC('◈ Grafo Temporal — la máquina del tiempo', `
          <p style="font-size:13px;line-height:1.6;color:var(--ink-2);margin:0 0 10px">
            Cada relación entre empresas tiene fecha de inicio (y a veces de fin). Mueve la línea de tiempo y verás
            cómo la cadena cambió con los años — sanciones, escaseces, nuevos acuerdos. Dentro de la ficha de cada
            empresa, <b>＋ Acción</b> te deja crear tesis, marcar riesgos o anotar — con fecha y tu nombre, para siempre.
          </p>`)}

        ${SEC('Comandos rápidos (opcional)', `
          <p style="font-size:12.5px;color:var(--ink-3);margin:0 0 12px">Escríbelos en la Cabina de Bixby — responden al instante, sin esperar a la IA.</p>
          <div style="border:1px solid var(--line);border-radius:10px;overflow:hidden">
            ${KHIPU_ROWS.map(([cmd, desc], i) => `
              <div style="display:flex;gap:14px;align-items:center;padding:9px 14px;${i % 2 ? 'background:var(--surface-2)' : ''}">
                <code style="flex:0 0 220px;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--violet);font-weight:700">${esc(cmd)}</code>
                <span style="font-size:12.5px;color:var(--ink-2)">${esc(desc)}</span>
              </div>`).join('')}
          </div>`)}

        ${SEC('Preguntas frecuentes', `
          <div style="display:flex;flex-direction:column;gap:14px">
            <div><div style="font-size:13px;font-weight:700;color:var(--ink-1);margin-bottom:3px">¿Qué es el NRS?</div>
              <div style="font-size:12.5px;color:var(--ink-3);line-height:1.5">La nota de riesgo de cada empresa, de 0 (segura) a 100 (frágil). Suma geopolítica, dependencia de la cadena, salud del negocio y sector. Donde veas NRS hay un botoncito <b style="color:#00E0FF">?</b> que te lo explica con ejemplos — igual que el peso de las conexiones, el VaR y la dilución.</div></div>
            <div><div style="font-size:13px;font-weight:700;color:var(--ink-1);margin-bottom:3px">¿Se pierden mis datos si cierro el navegador?</div>
              <div style="font-size:12.5px;color:var(--ink-3);line-height:1.5">Tu portafolio (compras/ventas) vive en este navegador. Tus tesis, anotaciones y decisiones (＋ Acción) se guardan en el servidor — sobreviven aunque cambies de computadora.</div></div>
            <div><div style="font-size:13px;font-weight:700;color:var(--ink-1);margin-bottom:3px">¿La app se actualiza sola?</div>
              <div style="font-size:12.5px;color:var(--ink-3);line-height:1.5">Sí. Cuando hay versión nueva, si acabas de abrirla se actualiza sola; si estás trabajando, aparece un avisito "⬆ Nueva versión" abajo a la derecha — la tocas cuando quieras.</div></div>
            <div><div style="font-size:13px;font-weight:700;color:var(--ink-1);margin-bottom:3px">¿El Universo 🪐 funciona en cualquier equipo?</div>
              <div style="font-size:12.5px;color:var(--ink-3);line-height:1.5">Sí. Desde julio 2026 el Universo se dibuja con una técnica que no depende de la tarjeta gráfica ni de configuraciones del navegador — si la app carga, el Universo se ve. Si alguna vez ves una pantalla vacía, es señal de que tu navegador guardó una copia vieja: borra los datos del sitio (candado junto a la dirección → Datos del sitio → Borrar) y recarga.</div></div>
            <div><div style="font-size:13px;font-weight:700;color:var(--ink-1);margin-bottom:3px">¿Qué hago si algo no responde?</div>
              <div style="font-size:12.5px;color:var(--ink-3);line-height:1.5">Abre 🩺 Sistema (arriba) — te dice en vivo qué servicio falló y por qué, sin mostrar ninguna clave.</div></div>
          </div>`)}
      </div>`;
  };
})();
