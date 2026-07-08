/* ============================================================================
   engine/brief.js — BRIEF MATINAL (te recibe con la inteligencia del día)
   Al abrir la app (una vez al día, descartable), un overlay NEXUS resume:
   el mayor chokepoint, la empresa de mayor riesgo, factores externos activos
   y una oportunidad. Reutiliza el motor de matrices (o topología cliente) y,
   opcional, una línea narrada por IA (gasto moderado). No molesta: 1×/día,
   fácil de cerrar, y un botón ❓ para reabrirlo.
   ============================================================================ */
(function () {
  'use strict';

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
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
    try { return new Date().toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'long' }); }
    catch (e) { return ''; }
  }

  function ensureStyles() {
    if (document.getElementById('brief-styles')) return;
    var css = ''
      + '#brief-ov{position:fixed;inset:0;z-index:6200;display:none;align-items:center;justify-content:center;'
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
    risk:   { ic: '△', bg: 'rgba(255,179,0,.15)',  col: '#FFB300', tag: 'RIESGO' },
    factor: { ic: '◈', bg: 'rgba(157,107,255,.15)', col: '#9D6BFF', tag: 'FACTOR ACTIVO' },
    oport:  { ic: '↑', bg: 'rgba(43,227,139,.15)', col: '#2BE38B', tag: 'OPORTUNIDAD' },
  };

  function card(c) {
    var k = KIND[c.kind] || KIND.shock;
    return '<div class="brc" ' + (c.node ? 'onclick="window._briefJump(\'' + esc(c.node) + '\')"' : '') + '>' +
      '<div class="ic" style="background:' + k.bg + ';color:' + k.col + '">' + k.ic + '</div>' +
      '<div class="bd"><div class="tag" style="color:' + k.col + '">' + k.tag + '</div>' +
      '<div class="tx">' + c.text + '</div></div></div>';
  }

  window._briefJump = function (id) {
    close();
    if (window.switchTab) window.switchTab('map');
    setTimeout(function () { if (window.jumpTo) window.jumpTo(id); }, 100);
  };

  // ── construir las tarjetas del brief (cliente + matriz si hay) ──
  function build() {
    return Promise.resolve().then(function () {
      var cards = [];
      var NODES = window.NODES || [];
      // chokepoint principal (cliente)
      if (typeof window.computeDownstream === 'function' && NODES.length) {
        var best = null;
        NODES.forEach(function (n) {
          var a = 0; try { var r = window.computeDownstream(n.id); a = (r instanceof Set ? r.size : (r || []).length); } catch (e) {}
          if (!best || a > best.a) best = { id: n.id, a: a };
        });
        if (best && best.a > 0) cards.push({ kind: 'shock', node: best.id,
          text: 'El mayor punto único de fallo hoy es <b>' + esc(nm(best.id)) + '</b>: su caída arrastraría a <b>' + best.a + ' empresas</b>.' });
      }
      // riesgo alto (cartera o universo)
      if (typeof window.computeNRS === 'function') {
        var pos = (window.MKT && window.MKT.pos) || {};
        var pool = Object.keys(pos).length ? Object.keys(pos) : NODES.map(function (n) { return n.id; });
        var risky = pool.map(function (id) { return { id: id, nrs: window.computeNRS(id) }; })
          .sort(function (a, b) { return b.nrs - a.nrs; })[0];
        if (risky && risky.nrs >= 60) cards.push({ kind: 'risk', node: risky.id,
          text: (Object.keys(pos).length ? 'En tu cartera, ' : '') + '<b>' + esc(nm(risky.id)) + '</b> es la de mayor riesgo (NRS <b>' + risky.nrs + '/100</b>). Vigílala.' });
      }
      // enriquecer con matriz (chokepoint ponderado + factores)
      return fetch('/api/matrix/metrics').then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; })
        .then(function (m) {
          if (m && m.chokepoints_top25 && m.chokepoints_top25.length) {
            cards[0] = { kind: 'shock', node: m.chokepoints_top25[0].id,
              text: 'Chokepoint de la red (motor de matrices): <b>' + esc(nm(m.chokepoints_top25[0].id)) +
                '</b> concentra el riesgo estructural — arrastra a <b>' + m.chokepoints_top25[0].cascade_size + '</b> empresas.' };
          }
          if (m && m.factors_active && m.factors_active.length) {
            cards.push({ kind: 'factor',
              text: '<b>' + m.factors_active.length + '</b> factor(es) externo(s) modulando la red: ' + esc(m.factors_active.slice(0, 2).join(', ')) + '.' });
          }
          return cards.slice(0, 4);
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
      '<div class="eb">Brief matinal</div>' +
      '<h2>' + esc(fechaLarga()) + '</h2>' +
      '<div class="sub">Tu resumen de inteligencia de la cadena de IA</div>' +
      '<div class="lead" id="brief-lead">Leyendo la red…</div>' +
      '<div class="cards" id="brief-cards"></div>' +
      '<div class="foot"><label class="dismiss"><input type="checkbox" id="brief-mute" ' + (seen === 'muted' ? 'checked' : '') + '> no mostrar automáticamente</label>' +
      '<button class="ok" onclick="window._briefClose()">Entendido</button></div>';
    document.getElementById('brief-mute').onchange = function (e) {
      localStorage.setItem('khipu_brief_day', e.target.checked ? 'muted' : todayKey());
    };
    ov.classList.add('show');
    build().then(function (cards) {
      var el = document.getElementById('brief-cards'); if (el) el.innerHTML = cards.map(card).join('');
      narrate(cards);
    });
    var fab = document.getElementById('brief-fab'); if (fab) fab.classList.add('show');
  }

  // línea narrada por IA (opcional, gasto moderado; degrada a una determinista)
  function narrate(cards) {
    var lead = document.getElementById('brief-lead'); if (!lead) return;
    var plain = cards.map(function (c) { return c.text.replace(/<[^>]+>/g, ''); }).join(' ');
    lead.textContent = cards.length ? 'Hoy destaca: ' + cards[0].text.replace(/<[^>]+>/g, '') : 'Red estable, sin alertas mayores.';
    if (!cards.length) return;
    fetch('/api/ai/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ system: 'Eres un analista de inversión. En 1 frase en español, da la conclusión accionable del día. Sin saludos.',
        prompt: 'Señales de hoy en la cadena de IA/semiconductores: ' + plain + '\nConclusión en 1 frase:', max_tokens: 90 }),
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

  function maybeAutoOpen() {
    if (!document.querySelector('.graph-wrap')) { setTimeout(maybeAutoOpen, 800); return; }
    ensureStyles();
    // botón flotante ❓ para reabrir siempre
    if (!document.getElementById('brief-fab')) {
      var fab = document.createElement('div'); fab.id = 'brief-fab'; fab.innerHTML = '❓';
      fab.title = 'Brief matinal'; fab.className = 'show';
      fab.onclick = function () { open(true); };
      document.body.appendChild(fab);
    }
    var seen = localStorage.getItem('khipu_brief_day');
    if (seen === 'muted' || seen === todayKey()) return;   // ya visto hoy o silenciado
    setTimeout(function () { open(false); }, 1400);         // deja cargar el grafo primero
  }
  if (document.readyState === 'complete') maybeAutoOpen();
  else window.addEventListener('load', maybeAutoOpen);
})();
