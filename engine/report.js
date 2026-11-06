/* engine/report.js — 📄 INFORME de cualquier respuesta del chat (2026-11-06, pedido de Fabrizio: «que Khipus pueda
   hacer informes como ese de forma nativa»).

   La respuesta YA está pintada (texto + bloques kblocks/1 con sus gráficos SVG, cifras con fuente y hora). El informe
   la copia tal cual a una página de PAPEL (tema claro de Khipus OS, A4) con membrete, la pregunta como título, la
   fecha y el aviso «información, no recomendación», y abre el diálogo de impresión → «Guardar como PDF».
   Sin IA, sin servidor y sin cifras nuevas: lo que se imprime es exactamente lo que el usuario vio.

   API: window.KhipuReport.open(replyEl, question) · .html(replyEl, question) (lo usa la prueba) */
(function () {
  'use strict';
  var W = window;
  function L(es, en) { return (W.LANG === 'en' || (function () { try { return localStorage.getItem('eco_lang') === 'en'; } catch (e) { return false; } })()) ? en : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  // papel = tema CLARO de Khipus OS (mismos tokens que engine/pfreports.js) + los que usan los bloques
  var TOKENS = ':root{--os-surface:#FFFFFF;--os-surface-2:#F4F4F8;--os-surface-3:#E9E9F0;--os-ink:#111216;--os-ink-2:#4A4D59;' +
    '--os-ink-3:#7D8090;--os-line:rgba(17,18,22,.13);--os-mute:#C9CAD6;--os-accent:#2F6BEA;--os-good:#0ca30c;--os-bad:#d03b3b;' +
    '--os-good-ink:#15803D;--os-bad-ink:#B42318;--os-warn:#b7791f;--os-warn-ink:#8A5A00;--os-neg:#d03b3b;--os-pos:#0ca30c;' +
    '--os-ai:#6236C9;--os-shadow:none;--os-font:\'Inter\',\'Geist\',system-ui,-apple-system,\'Segoe UI\',sans-serif;color-scheme:light}';
  var PAGE = '@page{size:A4;margin:14mm 14mm 16mm}' +
    'html,body{background:#fff}body{margin:0;font-family:var(--os-font);color:var(--os-ink);-webkit-print-color-adjust:exact;print-color-adjust:exact}' +
    '.khr{max-width:760px;margin:0 auto;padding:28px 28px 40px}' +
    '.khr-mast{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid var(--os-ink);padding-bottom:7px;' +
    'font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--os-ink-2)}.khr-mast b{color:var(--os-ink);letter-spacing:.16em}' +
    '.khr-title{font-family:Georgia,\'Charter\',\'Times New Roman\',serif;font-weight:400;font-size:30px;line-height:1.15;margin:20px 0 6px;letter-spacing:-.01em}' +
    '.khr-date{font-size:11px;color:var(--os-ink-3);margin-bottom:18px}' +
    '.khr-body .kc-body,.khr-body .kg-text{font-size:13.5px;line-height:1.6}' +
    '.khr-body [data-kg-id],.khr-body .kc-contrib,.khr-body .kc-chart{break-inside:avoid;page-break-inside:avoid}' +
    '.khr-body button,.khr-body .kc-acts,.khr-body .kg-acts,.khr-body .kc-meta,.khr-body .kc-av,.khr-body input,.khr-body select,' +
    '.khr-body [role=menu],.khr-body .kc-retry{display:none!important}' +
    '.khr-body a{color:var(--os-accent);text-decoration:none}' +
    // papel compacto: 3 cifras por fila, sin la fila de pasos ni animaciones; cada bloque entero en su página
    '.khr-body .kc-think,.khr-body .kc-contrib,.khr-body .kc-who{display:none!important}' +
    '.khr-body .kg-tiles{grid-template-columns:repeat(3,minmax(0,1fr))!important}' +
    '.khr-body *{animation:none!important;transition:none!important}' +
    '.khr-foot{margin-top:26px;border-top:1px solid var(--os-line);padding-top:8px;font-size:10px;color:var(--os-ink-3);display:flex;justify-content:space-between;gap:12px}' +
    '.khr-bar{position:sticky;top:0;display:flex;gap:8px;justify-content:flex-end;padding:10px 16px;background:#F4F4F8;border-bottom:1px solid var(--os-line)}' +
    '.khr-bar button{font:600 13px var(--os-font);border:0;border-radius:999px;padding:8px 16px;cursor:pointer;background:#111216;color:#fff}' +
    '.khr-bar button+button{background:#E9E9F0;color:#111216}' +
    '@media print{.khr-bar{display:none}.khr{padding:0}}';

  // el CSS de los bloques y del chat (lo inyectan genui.js / khipu_chat.js en <style>): se copia tal cual
  function blockCSS() {
    var out = [];
    Array.prototype.forEach.call(W.document.querySelectorAll('style'), function (s) {
      var t = s.textContent || '';
      if (t.indexOf('.kg-') >= 0 || t.indexOf('.kc-') >= 0) out.push(t);
    });
    return out.join('\n');
  }

  function today() {
    try { return new Date().toLocaleString(L('es-PE', 'en-US'), { dateStyle: 'long', timeStyle: 'short' }); } catch (e) { return new Date().toISOString().slice(0, 16).replace('T', ' '); }
  }

  function html(replyEl, question) {
    var main = (replyEl && (replyEl.querySelector('.kc-main') || replyEl)) || W.document.createElement('div');
    var c = main.cloneNode(true);
    Array.prototype.forEach.call(c.querySelectorAll('script,button,.kc-acts,.kg-acts,.kc-meta,.kc-av,.kc-think,input,select,[role=menu]'),
      function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
    var q = String(question || '').trim() || L('Informe de Khipus', 'Khipus report');
    return '<!doctype html><html lang="' + L('es', 'en') + '"><head><meta charset="utf-8"><title>' + esc(q.slice(0, 120)) + '</title>' +
      '<style>' + TOKENS + blockCSS() + PAGE + '</style></head><body>' +
      '<div class="khr-bar"><button type="button" id="khr-print">🖨 ' + esc(L('Imprimir / Guardar PDF', 'Print / Save PDF')) + '</button>' +
      '<button type="button" id="khr-close">' + esc(L('Cerrar', 'Close')) + '</button></div>' +
      '<div class="khr"><div class="khr-mast"><b>Khipus Finance Intelligence</b><span>' + esc(L('Informe', 'Report')) + '</span></div>' +
      '<h1 class="khr-title">' + esc(q) + '</h1><div class="khr-date">' + esc(today()) + '</div>' +
      '<div class="khr-body">' + c.innerHTML + '</div>' +
      '<div class="khr-foot"><span>' + esc(L('Elaborado con Khipus Finance Intelligence · cifras con su fuente y hora. Información, no recomendación de inversión.',
        'Made with Khipus Finance Intelligence · every figure with its source and time. Information, not investment advice.')) +
      '</span><span>khipus</span></div></div></body></html>';
  }

  function open(replyEl, question) {
    var w = null;
    try { w = W.open('', '_blank'); } catch (e) { w = null; }
    if (!w) {
      if (W.KhipuToast && W.KhipuToast.show) W.KhipuToast.show({ kind: 'warn', title: L('No pude abrir el informe', 'Could not open the report'),
        body: L('Tu navegador bloqueó la ventana nueva: permite ventanas emergentes para Khipus y vuelve a intentar.',
          'Your browser blocked the new window: allow pop-ups for Khipus and try again.') });
      return null;
    }
    w.document.open(); w.document.write(html(replyEl, question)); w.document.close();
    var d = w.document;
    var pr = d.getElementById('khr-print'), cl = d.getElementById('khr-close');
    if (pr) pr.addEventListener('click', function () { try { w.print(); } catch (e) {} });
    if (cl) cl.addEventListener('click', function () { try { w.close(); } catch (e) {} });
    setTimeout(function () { try { w.focus(); w.print(); } catch (e) {} }, 450);
    return w;
  }

  // el botón «📄 Informe PDF» de cada respuesta con contenido (lo pide engine/khipu_chat.js fillReply)
  function button(el, d, gui, question) {
    d = d || {};
    if (d.error || !(gui || (d.ai && String(d.answer || '').length > 160))) return null;
    var b = W.document.createElement('button'); b.className = 'kc-act kc-report'; b.type = 'button';
    b.textContent = '📄 ' + L('Informe PDF', 'PDF report');
    b.addEventListener('click', function () { open(el, question); });
    return b;
  }

  W.KhipuReport = { open: open, html: html, button: button };
})();
