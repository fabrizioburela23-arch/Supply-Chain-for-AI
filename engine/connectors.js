/* engine/connectors.js — 🧩 CONECTORES (tus apps) en Khipus OS (2026-11-26, pedido de Fabrizio: «algo que se conecte
   a todo, sin un MCP por cada cosa»). Puerta única: Composio (servidor: core/connectors.py + core/connectors_api.py).

   · Ventana: tus apps (Gmail, Calendar, Sheets, Drive, Slack, Notion, Outlook, WhatsApp… o cualquiera por nombre),
     cuáles están conectadas y un botón «Conectar» que abre el inicio de sesión OFICIAL de esa app.
   · Confirmación: cuando le pides a Khipu algo que CAMBIA algo (enviar un correo, crear una fila…), el chat NO lo hace:
     queda pendiente y aquí aparece el diálogo con el contenido exacto → «Confirmar» pide tu PIN. Sin clic no se envía nada.
   API: window.KhipuConnectors = { open(), poll(), _state }
   ============================================================================ */
(function () {
  'use strict';
  var W = window, seen = {}, st = { enabled: null, pending: [] }, timer = null;
  var APP_NAMES = { gmail: 'Gmail', googlecalendar: 'Google Calendar', googlesheets: 'Google Sheets', googledrive: 'Google Drive',
    slack: 'Slack', notion: 'Notion', outlook: 'Outlook', whatsapp: 'WhatsApp' };
  var APP_ICONS = { gmail: '✉️', googlecalendar: '📅', googlesheets: '📊', googledrive: '📁', slack: '💬', notion: '📝', outlook: '📧', whatsapp: '🟢' };

  function L(es, en) { try { return (W.LANG === 'en' || localStorage.getItem('eco_lang') === 'en') ? en : es; } catch (e) { return es; } }
  function owner() { try { var k = localStorage.getItem('kh_owner_key'); return k && k.length >= 16 ? k : ''; } catch (e) { return ''; } }
  function base() { return W.BASE || ''; }
  function el(t, c, txt) { var n = document.createElement(t); if (c) n.className = c; if (txt != null) n.textContent = txt; return n; }
  function get(path) {
    return fetch(base() + path, { cache: 'no-store', headers: { Accept: 'application/json', 'X-Khipu-Owner': owner() } })
      .then(function (r) { return r.json(); });
  }
  function post(path, body, pin) {
    var opts = { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Khipu-Owner': owner() }, body: JSON.stringify(body || {}) };
    var p = (pin && W._tradeFetch) ? W._tradeFetch(base() + path, opts, true) : fetch(base() + path, opts);
    return p.then(function (r) { return r.json().then(function (d) { d._status = r.status; return d; }); });
  }
  function toast(kind, title, body) { try { if (W.KhipuToast) W.KhipuToast.show({ kind: kind, title: title, body: body }); } catch (e) {} }
  function appName(a) { return APP_NAMES[a] || (a ? a.charAt(0).toUpperCase() + a.slice(1) : '?'); }

  // ── confirmar una acción que ESCRIBE ──
  function confirmOne(p) {
    var T = W.KhipuToast;
    if (!T || !T.confirm) return;
    var args = String(p.arguments || '');
    T.confirm({
      title: L('¿Hacer esto en ', 'Do this in ') + appName(p.app) + '?',
      body: p.summary,
      note: L('Contenido exacto: ', 'Exact content: ') + args.slice(0, 600) + L(' · Nada se envía sin tu confirmación (PIN).', ' · Nothing is sent without your confirmation (PIN).'),
      confirmLabel: L('Confirmar', 'Confirm'), cancelLabel: L('No, descartar', 'No, discard')
    }).then(function (ok) {
      if (!ok) { post('/api/connectors/discard', { id: p.id }); toast('info', L('Descartado', 'Discarded'), p.summary); return; }
      post('/api/connectors/confirm', { id: p.id }, true).then(function (d) {
        if (d && d.ok) toast('success', L('Hecho en ', 'Done in ') + appName(p.app), p.summary);
        else toast('error', L('No se pudo', 'Could not do it'), (d && (d.error || d.code)) || ('HTTP ' + (d && d._status)));
        refreshWin();
      }).catch(function () { toast('error', L('No se pudo', 'Could not do it'), L('Sin conexión con el servidor', 'No connection to the server')); });
    });
  }

  function poll() {
    if (document.hidden || !owner()) return Promise.resolve(st);
    return get('/api/connectors/pending').then(function (d) {
      st.enabled = !!(d && d.enabled);
      st.pending = (d && d.pending) || [];
      st.pending.forEach(function (p) { if (!seen[p.id]) { seen[p.id] = 1; confirmOne(p); } });
      if (!st.enabled && timer) { clearInterval(timer); timer = null; }
      return st;
    }).catch(function () { return st; });
  }

  // ── ventana ──
  var ov = null;
  function close() { if (ov && ov.parentNode) ov.parentNode.removeChild(ov); ov = null; }
  function card(app, status) {
    var c = el('div', 'kcn-app'), on = status === 'ACTIVE';
    c.appendChild(el('span', 'kcn-ic', APP_ICONS[app] || '🧩'));
    var t = el('div', 'kcn-t'); t.appendChild(el('b', null, appName(app)));
    t.appendChild(el('small', null, on ? L('✅ Conectada', '✅ Connected') : status ? L('⏳ Pendiente', '⏳ Pending') : L('Sin conectar', 'Not connected')));
    c.appendChild(t);
    if (!on) {
      var b = el('button', 'kcn-btn', L('Conectar', 'Connect')); b.type = 'button';
      b.addEventListener('click', function () { connect(app, b); });
      c.appendChild(b);
    }
    return c;
  }
  function connect(app, btn) {
    if (btn) { btn.disabled = true; btn.textContent = '…'; }
    var win = null; try { win = W.open('about:blank', '_blank'); } catch (e) {}
    post('/api/connectors/link', { app: app }).then(function (d) {
      if (d && d.redirect_url && /^https:\/\//.test(d.redirect_url)) {
        if (win) win.location.href = d.redirect_url; else W.open(d.redirect_url, '_blank', 'noopener');
        toast('info', L('Inicia sesión en ', 'Sign in to ') + appName(app), L('Al terminar, vuelve aquí y toca «Actualizar».', 'When done, come back and tap “Refresh”.'));
      } else {
        if (win) try { win.close(); } catch (e) {}
        toast('error', L('No se pudo conectar ', 'Could not connect ') + appName(app), (d && d.error) || '');
      }
      if (btn) { btn.disabled = false; btn.textContent = L('Conectar', 'Connect'); }
    });
  }
  function refreshWin() {
    if (!ov) return;
    var body = ov.querySelector('.kcn-body');
    body.textContent = L('Cargando…', 'Loading…');
    get('/api/connectors/status').then(function (d) {
      body.textContent = '';
      if (!d || !d.enabled) {
        body.appendChild(el('p', 'kcn-note', L('Aún no está activado. Falta poner la clave COMPOSIO_API_KEY en Railway (Variables).',
          'Not enabled yet. COMPOSIO_API_KEY must be set in Railway (Variables).')));
        return;
      }
      if (d.error) body.appendChild(el('p', 'kcn-note', d.error));
      var conn = d.connected || {}, apps = (d.suggested || []).slice();
      Object.keys(conn).forEach(function (a) { if (apps.indexOf(a) < 0) apps.unshift(a); });
      var grid = el('div', 'kcn-grid');
      apps.forEach(function (a) { grid.appendChild(card(a, conn[a])); });
      body.appendChild(grid);
      var row = el('div', 'kcn-row'), inp = el('input', 'kcn-in'), go = el('button', 'kcn-btn', L('Conectar otra', 'Connect another'));
      inp.placeholder = L('Otra app (ej. hubspot, trello, github)', 'Another app (e.g. hubspot, trello, github)'); go.type = 'button';
      go.addEventListener('click', function () { var v = String(inp.value || '').trim().toLowerCase().replace(/[^a-z0-9_-]/g, ''); if (v) connect(v, go); });
      row.appendChild(inp); row.appendChild(go); body.appendChild(row);
      if ((d.pending || []).length) {
        body.appendChild(el('h4', null, L('Esperando tu confirmación', 'Waiting for your confirmation')));
        d.pending.forEach(function (p) {
          var r = el('div', 'kcn-pend'), b = el('button', 'kcn-btn', L('Revisar', 'Review')); b.type = 'button';
          r.appendChild(el('span', null, appName(p.app) + ' · ' + p.summary));
          b.addEventListener('click', function () { confirmOne(p); }); r.appendChild(b); body.appendChild(r);
        });
      }
      body.appendChild(el('p', 'kcn-note', L('Leer en tus apps es directo; enviar, crear o borrar siempre te pide confirmar con PIN. Khipus nunca ve tus contraseñas.',
        'Reading your apps is direct; sending, creating or deleting always asks you to confirm with PIN. Khipus never sees your passwords.')));
    }).catch(function () { body.textContent = L('Sin conexión con el servidor', 'No connection to the server'); });
  }
  function open() {
    css();
    close();
    ov = el('div', 'kcn-ov');
    var box = el('div', 'kcn-box kos-themed'), head = el('div', 'kcn-head');
    head.appendChild(el('b', null, '🧩 ' + L('Conectores · tus apps', 'Connectors · your apps')));
    var rf = el('button', 'kcn-x', L('Actualizar', 'Refresh')), x = el('button', 'kcn-x', '✕');
    rf.type = x.type = 'button'; rf.addEventListener('click', refreshWin); x.addEventListener('click', close);
    head.appendChild(rf); head.appendChild(x);
    box.appendChild(head); box.appendChild(el('div', 'kcn-body'));
    ov.appendChild(box);
    ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
    document.body.appendChild(ov);
    refreshWin();
  }

  var _css = false;
  function css() {
    if (_css) return; _css = true;
    var s = el('style');
    s.textContent = '.kcn-ov{position:fixed;inset:0;z-index:7700;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;padding:16px}' +
      '.kcn-box{width:min(560px,100%);max-height:86vh;overflow:auto;background:var(--os-surface,#16171c);color:var(--os-ink,#eee);border:1px solid var(--os-line,rgba(255,255,255,.12));border-radius:16px;padding:16px}' +
      '.kcn-head{display:flex;gap:8px;align-items:center;margin-bottom:12px}.kcn-head b{flex:1;font-size:16px}' +
      '.kcn-x,.kcn-btn{font:600 13px inherit;border-radius:999px;padding:6px 12px;border:1px solid var(--os-line,rgba(255,255,255,.2));background:transparent;color:inherit;cursor:pointer}' +
      '.kcn-btn{background:var(--os-accent,#2F6BEA);color:#fff;border-color:transparent}.kcn-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px}' +
      '.kcn-app{display:flex;gap:10px;align-items:center;padding:10px;border:1px solid var(--os-line,rgba(255,255,255,.12));border-radius:12px}' +
      '.kcn-ic{font-size:20px}.kcn-t{flex:1;display:flex;flex-direction:column}.kcn-t small{opacity:.7}' +
      '.kcn-row{display:flex;gap:8px;margin-top:12px}.kcn-in{flex:1;font:inherit;padding:6px 10px;border-radius:999px;border:1px solid var(--os-line,rgba(255,255,255,.2));background:transparent;color:inherit}' +
      '.kcn-pend{display:flex;gap:8px;align-items:center;justify-content:space-between;padding:6px 0}.kcn-note{opacity:.75;font-size:12.5px;margin-top:12px}';
    document.head.appendChild(s);
  }

  // aviso de confirmación: revisa pendientes cada 12 s con la pestaña visible (se apaga solo si Composio no está)
  function start() { if (timer) return; poll(); timer = setInterval(poll, 12000); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { setTimeout(start, 4000); });
  else setTimeout(start, 4000);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) poll(); });

  W.KhipuConnectors = { open: open, poll: poll, _state: st, _confirm: confirmOne };
})();
