/* ============================================================================
   engine/brief.js — BRIEF MATINAL (te recibe con la inteligencia del día)
   Al abrir la app (una vez al día, descartable), un overlay NEXUS resume:
   el mayor chokepoint, la empresa de mayor riesgo, factores externos activos
   y una oportunidad. Reutiliza el motor de matrices (o topología cliente) y,
   opcional, una línea narrada por IA (gasto moderado). No molesta: 1×/día,
   fácil de cerrar, y un botón ❓ para reabrirlo.
   KHIPUS OS (2026-10-06): NO se abre solo encima de Khipus OS (la app arranca en el
   OS salvo "Vista clásica"); queda a pedido (window._briefOpen, paleta ⌘K). Así el
   arranque no gasta CPU (cadena de caída de 949 empresas) ni una llamada de IA que
   compite con la primera pregunta del usuario. Al abrirse: primero el motor de
   matrices; el cálculo local solo si el servidor no lo tiene, y en porciones.
   ============================================================================ */
(function () {
  'use strict';

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function isEn() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } } return l === 'en'; }
  function L(es, en) { return isEn() ? en : es; }
  function nm(id) { var n = window.NODE_BY_ID && window.NODE_BY_ID[id]; return n ? n.label : id; }
  function secColor(id) {
    var n = window.NODE_BY_ID && window.NODE_BY_ID[id];
    if (!n || !window.SECTORS9) return '#00E0FF';
    var s = window.SECTORS9[(window.CAT_TO_SECTOR || {})[n.cat] || 'cloud_ia'];
    return s ? s.color : '#00E0FF';
  }
  function todayKey() {
    var d = new Date();
    return d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
  }
  function fechaLarga() {
    try { return new Date().toLocaleDateString(isEn() ? 'en' : 'es', { weekday: 'long', day: 'numeric', month: 'long' }); }
    catch (e) { return ''; }
  }

  function ensureStyles() {
    if (document.getElementById('brief-styles')) return;
    var css = ''
      + '#brief-ov{position:fixed;inset:0;z-index:7600;display:none;align-items:center;justify-content:center;'
      + 'background:rgba(3,6,12,.72);backdrop-filter:blur(4px);font-family:Inter,system-ui,sans-serif}'
      + '#brief-ov.show{display:flex;animation:brFade .2s ease}'
      + '@keyframes brFade{from{opacity:0}to{opacity:1}}'
      + '#brief{width:min(560px,94vw);max-height:88vh;overflow-y:auto;color:#E8EDFB;border-radius:18px;'
      + 'background:radial-gradient(680px 380px at 65% -8%,#0e1626,#06090F);border:1px solid rgba(122,158,255,.22);'
      + 'box-shadow:0 30px 80px rgba(0,0,0,.6);padding:24px 26px 20px}'
      + '#brief .eb{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:#00E0FF}'
      + '#brief h2{margin:6px 0 3px;font-size:22px;font-weight:650;text-transform:capitalize}'
      + '#brief .sub{color:#8791AC;font-size:12.5px;margin:0 0 6px}'
      + '#brief .lead{color:#c8d0e0;font-size:13px;line-height:1.55;margin:12px 0 4px;min-height:18px}'
      + '#brief .cards{display:flex;flex-direction:column;gap:9px;margin:16px 0 6px}'
      + '.brc{border:1px solid rgba(122,158,255,.14);border-radius:12px;padding:12px 14px;background:rgba(21,28,45,.5);'
      + 'display:flex;gap:12px;align-items:flex-start;cursor:pointer;transition:border-color .12s}'
      + '.brc:hover{border-color:rgba(0,224,255,.4)}'
      + '.brc .ic{width:30px;height:30px;border-radius:9px;flex:none;display:flex;align-items:center;justify-content:center;font-size:15px}'
      + '.brc .bd{flex:1;min-width:0}'
      + '.brc .tag{font-family:"JetBrains Mono",monospace;font-size:9px;letter-spacing:.1em;text-transform:uppercase;font-weight:700}'
      + '.brc .tx{font-size:12.5px;line-height:1.45;color:#E8EDFB;margin-top:3px}'
      + '.brc .tx b{color:#fff}'
      + '#brief .src{font-size:10.5px;color:#7C87A3;margin-top:8px;line-height:1.4}'
      + '#brief .foot{display:flex;justify-content:space-between;align-items:center;margin-top:16px;gap:10px}'
      + '#brief .dismiss{font-size:11px;color:#7C87A3;display:flex;align-items:center;gap:6px;cursor:pointer}'
      + '#brief .ok{padding:9px 20px;border-radius:9px;cursor:pointer;font-family:inherit;font-size:12.5px;font-weight:600;'
      + 'background:#00E0FF;color:#03141C;border:1px solid #00E0FF;box-shadow:0 0 16px rgba(0,224,255,.4)}'
      + '#brief-fab{position:fixed;right:16px;bottom:70px;z-index:40;width:38px;height:38px;border-radius:50%;cursor:pointer;'
      + 'display:none;align-items:center;justify-content:center;font-size:16px;background:rgba(15,21,34,.9);'
      + 'border:1px solid rgba(0,224,255,.35);color:#00E0FF;backdrop-filter:blur(6px)}'
      + '#brief-fab.show{display:flex}#brief-fab:hover{border-color:#00E0FF}';
    var st = document.createElement('style'); st.id = 'brief-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  var KIND = {
    shock:  { ic: '⚡', bg: 'rgba(255,77,106,.15)', col: '#FF4D6A', tag: 'CHOKEPOINT' },
    risk:   { ic: '△', bg: 'rgba(255,179,0,.15)',  col: '#FFB300', tag: 'RIESGO', tag_en: 'RISK' },
    factor: { ic: '◈', bg: 'rgba(157,107,255,.15)', col: '#9D6BFF', tag: 'FACTOR ACTIVO', tag_en: 'ACTIVE FACTOR' },
    oport:  { ic: '↑', bg: 'rgba(43,227,139,.15)', col: '#2BE38B', tag: 'OPORTUNIDAD', tag_en: 'OPPORTUNITY' },
    concl:  { ic: '🏛', bg: 'rgba(0,224,255,.12)', col: '#00E0FF', tag: 'CONCLUSIONES', tag_en: 'CONCLUSIONS' },
  };

  function card(c) {
    var k = KIND[c.kind] || KIND.shock;
    var click = c.committee ? 'onclick="window._briefCommittee(\'' + esc(c.committee) + '\')"'
      : c.node ? 'onclick="window._briefJump(\'' + esc(c.node) + '\')"' : '';
    return '<div class="brc" ' + click + '>' +
      '<div class="ic" style="background:' + k.bg + ';color:' + k.col + '">' + k.ic + '</div>' +
      '<div class="bd"><div class="tag" style="color:' + k.col + '">' + (isEn() && k.tag_en ? k.tag_en : k.tag) + '</div>' +
      '<div class="tx">' + c.text + '</div></div></div>';
  }

  window._briefCommittee = function (id) {
    close();
    if (window.KhipuCommittee) window.KhipuCommittee.open(id === '__board' ? undefined : id);
  };

  // ── lo que concluyeron los analistas (pizarra del comité; sin IA) ──
  function conclusionsCard() {
    return fetch('/api/committee/board?limit=60').then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; })
      .then(function (d) {
        var it = (d && d.items) || [];
        if (!it.length) return null;
        var best = it[0], worst = it[it.length - 1];
        var parts = [];
        if (best.overall_conviction >= 20) {
          var bf = best.best_for ? (isEn() ? best.best_for.text_en : best.best_for.text_es) : '';
          parts.push(L('Los analistas ven más favorable a ', 'The analysts see the most favorable case for ') + '<b>' + esc(best.label) + '</b> (' +
            L('convicción', 'conviction') + ' <b>+' + Math.round(best.overall_conviction) + '</b>)' + (bf ? ': ' + esc(String(bf).slice(0, 180)) : '.'));
        }
        if (worst !== best && worst.overall_conviction <= -20) {
          parts.push(L('La más desfavorable: ', 'The most unfavorable: ') + '<b>' + esc(worst.label) + '</b> (<b>' + Math.round(worst.overall_conviction) + '</b>).');
        }
        if (!parts.length) parts.push(L('Los analistas investigaron ', 'The analysts researched ') + '<b>' + it.length + '</b> ' +
          L('empresa(s), sin una convicción fuerte en ninguna dirección.', 'company(ies), with no strong conviction either way.'));
        parts.push('<span style="color:#00E0FF">' + L('Ver la pizarra →', 'See the board →') + '</span>');
        return { kind: 'concl', committee: '__board', text: parts.join(' ') };
      });
  }

  window._briefJump = function (id) {
    close();
    if (window.switchTab) window.switchTab('map');
    setTimeout(function () { if (window.jumpTo) window.jumpTo(id); }, 100);
  };

  // ── el mayor punto único de fallo, calculado EN TU NAVEGADOR (respaldo sin servidor) ──
  // computeDownstream recorre todos los vínculos por cada empresa (~949 × 2.500): va en porciones
  // de ~12 ms para no congelar la pantalla (antes era UNA tarea larga de ~0,3 s; >1 s en un móvil).
  function clientChokepoint() {
    return new Promise(function (resolve) {
      var NODES = window.NODES || [];
      if (typeof window.computeDownstream !== 'function' || !NODES.length) { resolve(null); return; }
      var best = null, i = 0;
      (function step() {
        var t0 = Date.now();
        for (; i < NODES.length && Date.now() - t0 < 12; i++) {
          var a = 0;
          try { var r = window.computeDownstream(NODES[i].id); a = (r instanceof Set ? r.size : (r || []).length); } catch (e) {}
          if (!best || a > best.a) best = { id: NODES[i].id, a: a };
        }
        if (i < NODES.length) setTimeout(step, 0);
        else resolve(best && best.a > 0 ? best : null);
      })();
    });
  }

  // riesgo alto (cartera o universo) — NRS memoizado, barato
  function riskCard() {
    if (typeof window.computeNRS !== 'function') return null;
    var NODES = window.NODES || [];
    var pos = (window.MKT && window.MKT.pos) || {};
    var mine = Object.keys(pos).length > 0;
    var pool = mine ? Object.keys(pos) : NODES.map(function (n) { return n.id; });
    var risky = pool.map(function (id) { return { id: id, nrs: window.computeNRS(id) }; })
      .sort(function (a, b) { return b.nrs - a.nrs; })[0];
    if (!risky || !(risky.nrs >= 60)) return null;
    return { kind: 'risk', node: risky.id,
      text: (mine ? L('En tu cartera, ', 'In your portfolio, ') : '') + '<b>' + esc(nm(risky.id)) + '</b> ' +
        L('es la de mayor riesgo', 'carries the highest risk') + ' (NRS <b>' + risky.nrs + '/100</b>). ' +
        L('Vigílala.', 'Keep an eye on it.') };
  }

  function hhmm() {
    try { return new Date().toLocaleTimeString(isEn() ? 'en' : 'es', { hour: '2-digit', minute: '2-digit' }); } catch (e) { return ''; }
  }

  // ── construir las tarjetas: motor de matrices primero (servidor); si no está, el cálculo
  //    local (en porciones). La pizarra del comité va EN PARALELO. → {cards, src} ──
  function build() {
    var metricsP = fetch('/api/matrix/metrics').then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
    var boardP = conclusionsCard().catch(function () { return null; });
    var risk = null;
    try { risk = riskCard(); } catch (e) { risk = null; }
    return metricsP.then(function (m) {
      var top = m && m.chokepoints_top25 && m.chokepoints_top25[0];
      var shockP = top
        ? Promise.resolve({ kind: 'shock', node: top.id,
            text: L('Chokepoint de la red (motor de matrices): <b>', 'Network chokepoint (matrix engine): <b>') + esc(nm(top.id)) +
              L('</b> concentra el riesgo estructural — arrastra a <b>', '</b> concentrates the structural risk — it drags down <b>') +
              esc(top.cascade_size) + L('</b> empresas.', '</b> companies.') })
        : clientChokepoint().then(function (best) {
            return best ? { kind: 'shock', node: best.id,
              text: L('El mayor punto único de fallo hoy es <b>', "Today's biggest single point of failure is <b>") + esc(nm(best.id)) +
                L('</b>: su caída arrastraría a <b>', '</b>: its fall would drag down <b>') + best.a + L(' empresas</b>.', ' companies</b>.') } : null;
          });
      return shockP.then(function (shock) {
        var cards = [];
        if (shock) cards.push(shock);
        if (risk) cards.push(risk);
        if (m && m.factors_active && m.factors_active.length) {
          cards.push({ kind: 'factor',
            text: '<b>' + m.factors_active.length + '</b> ' + L('factor(es) externo(s) modulando la red: ', 'external factor(s) shaping the network: ') +
              esc(m.factors_active.slice(0, 2).join(', ')) + '.' });
        }
        // Fuente y hora SIEMPRE a la vista (ninguna cifra sin procedencia)
        var src = top
          ? L('Fuente: motor de matrices de Khipus (ontología)', 'Source: Khipus matrix engine (ontology)') +
            (m.stale ? L(' · última lectura guardada', ' · last saved reading') : ' · ' + hhmm())
          : L('Fuente: grafo de Khipus, calculado en tu navegador', 'Source: Khipus graph, computed in your browser') + ' · ' + hhmm();
        return boardP.then(function (cc) {
          cards = cards.slice(0, 4);
          if (cc) cards.splice(1, 0, cc);
          return { cards: cards.slice(0, 5), src: src };
        });
      });
    });
  }

  function open(force) {
    ensureStyles();
    var ov = document.getElementById('brief-ov');
    if (!ov) {
      ov = document.createElement('div'); ov.id = 'brief-ov';
      ov.innerHTML = '<div id="brief"></div>';
      ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
      document.body.appendChild(ov);
    }
    var seen = localStorage.getItem('khipu_brief_day');
    document.getElementById('brief').innerHTML =
      '<div class="eb">' + L('Brief matinal', 'Morning brief') + '</div>' +
      '<h2>' + esc(fechaLarga()) + '</h2>' +
      '<div class="sub">' + L('Tu resumen de inteligencia de la cadena de IA', 'Your AI supply-chain intelligence summary') + '</div>' +
      '<div class="lead" id="brief-lead">' + L('Leyendo la red…', 'Reading the network…') + '</div>' +
      '<div class="cards" id="brief-cards"></div>' +
      '<div class="src" id="brief-src"></div>' +
      '<div class="foot"><label class="dismiss"><input type="checkbox" id="brief-mute" ' + (seen === 'muted' ? 'checked' : '') + '> ' + L('no mostrar automáticamente', 'do not show automatically') + '</label>' +
      '<button class="ok" onclick="window._briefClose()">' + L('Entendido', 'Got it') + '</button></div>';
    document.getElementById('brief-mute').onchange = function (e) {
      localStorage.setItem('khipu_brief_day', e.target.checked ? 'muted' : todayKey());
    };
    ov.classList.add('show');
    build().then(function (res) {
      var cards = (res && res.cards) || [];
      var el = document.getElementById('brief-cards'); if (el) el.innerHTML = cards.map(card).join('');
      var se = document.getElementById('brief-src'); if (se) se.textContent = (res && res.src) || '';
      narrate(cards);
    }).catch(function () {
      var lead = document.getElementById('brief-lead');
      if (lead) lead.textContent = L('No se pudo leer la red ahora. Reintenta en un momento.', 'Could not read the network right now. Try again in a moment.');
    });
    var fab = document.getElementById('brief-fab'); if (fab) fab.classList.add('show');
  }

  // línea narrada por IA (opcional, gasto moderado; degrada a una determinista)
  function narrate(cards) {
    var lead = document.getElementById('brief-lead'); if (!lead) return;
    var plain = cards.map(function (c) { return c.text.replace(/<[^>]+>/g, ''); }).join(' ');
    var en = (window.LANG || '') === 'en';
    lead.textContent = cards.length ? (en ? 'Today stands out: ' : 'Hoy destaca: ') + cards[0].text.replace(/<[^>]+>/g, '') : (en ? 'Stable network, no major alerts.' : 'Red estable, sin alertas mayores.');
    if (!cards.length) return;
    fetch('/api/ai/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ system: 'Eres un analista de investigación. En 1 frase en ' + (en ? 'inglés' : 'español') + ', resume la señal más importante del día y por qué importa. NO recomiendes comprar, vender ni mantener. Sin saludos.',
        prompt: 'Señales de hoy en la cadena de IA/semiconductores: ' + plain + '\nResumen en 1 frase:', max_tokens: 90 }),
    }).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      if (d && d.result && lead) lead.textContent = '💡 ' + d.result.trim();
    }).catch(function () {});
  }

  function close() {
    var ov = document.getElementById('brief-ov'); if (ov) ov.classList.remove('show');
    if (localStorage.getItem('khipu_brief_day') !== 'muted') localStorage.setItem('khipu_brief_day', todayKey());
  }
  window._briefClose = close;
  window._briefOpen = function () { open(true); };

  // Khipus OS manda la pantalla: está abierto, o se abrirá al arrancar (siempre, salvo que el
  // usuario eligió "Vista clásica" en esta sesión: sessionStorage kh_os_classic='1').
  function osOwnsScreen() {
    var ck = window.BixbyCockpit;
    if (!ck) return false;
    if (typeof ck.isOpen === 'function' && ck.isOpen()) return true;
    var classic = false;
    try { classic = sessionStorage.getItem('kh_os_classic') === '1'; } catch (e) {}
    return !classic;
  }
  window._briefAutoAllowed = function () { return !osOwnsScreen(); };

  function maybeAutoOpen() {
    if (!document.querySelector('.graph-wrap')) { setTimeout(maybeAutoOpen, 800); return; }
    ensureStyles();
    // botón flotante ❓ para reabrir siempre (vista clásica; Khipus OS lo ofrece en su paleta)
    if (!document.getElementById('brief-fab')) {
      var fab = document.createElement('div'); fab.id = 'brief-fab'; fab.innerHTML = '❓';
      fab.title = L('Brief matinal', 'Morning brief'); fab.className = 'show';
      fab.onclick = function () { open(true); };
      document.body.appendChild(fab);
    }
    var seen = null;
    try { seen = localStorage.getItem('khipu_brief_day'); } catch (e) {}
    if (seen === 'muted' || seen === todayKey()) return;   // ya visto hoy o silenciado
    if (osOwnsScreen()) return;                             // Khipus OS: a pedido, nunca encima
    setTimeout(function () { if (!osOwnsScreen()) open(false); }, 1400);   // deja cargar el grafo primero
  }
  if (document.readyState === 'complete') maybeAutoOpen();
  else window.addEventListener('load', maybeAutoOpen);
})();
