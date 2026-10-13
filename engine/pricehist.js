/* engine/pricehist.js — 🩺 Sistema → «Historia de precios» (BRECHAS bloque 2: la memoria de los números).
   Muestra cuánta historia guarda Khipus (cierres diarios ajustados, tipo de cambio diario, fotos diarias de
   métricas y posiciones) y el progreso del relleno de 5 años. El relleno NUNCA es automático (decisión #3 sin
   responder): «Descargar 5 años (PIN)» lo arranca el operador por window._tradeFetch, con KhipuToast.confirm
   (nunca window.confirm); «Detener (PIN)» lo pausa (es reanudable). Textos ES/EN.
   API: window.KhipuPriceHistory.mount(containerId)
*/
(function () {
  'use strict';
  var BASE = (typeof window.BASE !== 'undefined') ? window.BASE : '';
  function en() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = 'es'; } } return l === 'en'; }
  function L(es, e) { return en() ? e : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function chip(k) { return window.explainChip ? window.explainChip(k) : ''; }
  function num(n) { return (n == null) ? '—' : Number(n).toLocaleString(en() ? 'en-US' : 'es-ES'); }

  if (window.explainRegister) {
    window.explainRegister('eod_history', {
      es: { t: '¿Qué es la «Historia de precios»?',
        b: 'Khipus guarda cada día el <b>precio de cierre</b> de todas las empresas que cotizan (ajustado por divisiones de ' +
           'acciones y dividendos), el <b>tipo de cambio</b> de cada moneda y una <b>foto</b> del riesgo NRS y de tus posiciones. ' +
           'Con esa memoria, el riesgo y los análisis técnicos usan precios guardados y fechados, y el riesgo en dólares de una ' +
           'acción japonesa o europea incluye lo que se mueve su moneda.<br><br>' +
           'La <b>descarga de 5 años</b> llena el pasado de una vez (unas horas, descargas gratuitas de Yahoo, ~100 MB). ' +
           'Solo empieza si tú la pides con tu PIN; si la detienes, la próxima vez sigue donde quedó.' },
      en: { t: 'What is the "Price history"?',
        b: 'Every day Khipus stores the <b>closing price</b> of every listed company (adjusted for stock splits and dividends), ' +
           'the <b>exchange rate</b> of each currency and a <b>snapshot</b> of the NRS risk and of your positions. With that ' +
           'memory, risk and technical analysis use stored, dated prices, and the dollar risk of a Japanese or European stock ' +
           'includes how much its currency moves.<br><br>' +
           'The <b>5-year download</b> fills the past in one go (a few hours, free Yahoo downloads, ~100 MB). It only starts if ' +
           'you ask for it with your PIN; if you stop it, next time it resumes where it left off.' } });
  }

  var _box = null, _st = null, _bf = null, _busy = false, _msg = '', _timer = null;

  function ensureStyles() {
    if (document.getElementById('kph-styles')) return;
    var st = document.createElement('style'); st.id = 'kph-styles';
    st.textContent =
      '.kph-root{color:var(--os-ink,#F2F2F5);font-family:var(--os-font,\'Nunito\',system-ui,sans-serif)}' +
      '.kph-root .kph-card{border-radius:var(--os-r,18px);padding:14px 16px;margin:6px 0 12px;background:var(--os-surface,#17181F);' +
        'box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35));min-width:0}' +
      '.kph-root .kph-hd{display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap}' +
      '.kph-root .kph-hd b{font-size:14px;font-weight:800;flex:1;min-width:0}' +
      '.kph-root .kph-mut{font-size:12px;color:var(--os-ink-2,#A6A8B5);line-height:1.5;overflow-wrap:anywhere}' +
      '.kph-root .kph-acts{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}' +
      '.kph-root .kph-btn{appearance:none;border:0;cursor:pointer;height:32px;padding:0 13px;border-radius:999px;font-size:12.5px;font-weight:700;' +
        'background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5)}' +
      '.kph-root .kph-btn.pri{background:var(--os-btn,#F2F2F5);color:var(--os-btn-ink,#111216)}' +
      '.kph-root .kph-btn[disabled]{opacity:.45;cursor:default}' +
      '.kph-root .kph-btn:focus-visible{outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px}' +
      '.kph-root .kph-bar{height:8px;border-radius:999px;background:var(--os-surface-2,#1F2029);overflow:hidden;margin:6px 0}' +
      '.kph-root .kph-bar i{display:block;height:100%;background:var(--os-accent,#4C8DF6)}' +
      '.kph-root .kph-warn{color:var(--os-warn-ink,#F2C46D)}';
    document.head.appendChild(st);
  }

  function errMsg(d, status) {
    if (d && (d.error || d.error_en)) return en() ? (d.error_en || d.error) : (d.error || d.error_en);
    return 'HTTP ' + status;
  }

  async function load() {
    try {
      var r = await fetch(BASE + '/api/prices/status');
      _st = r.ok ? await r.json() : null;
      _bf = _st ? _st.backfill : null;
    } catch (e) { _st = null; }
    render();
    schedule();
  }

  function schedule() {
    if (_timer) { clearTimeout(_timer); _timer = null; }
    if (_bf && _bf.running && _box && document.body.contains(_box)) {
      _timer = setTimeout(async function () {
        try { var r = await fetch(BASE + '/api/prices/backfill'); if (r.ok) _bf = await r.json(); } catch (e) { /* reintenta */ }
        render();
        if (_bf && !_bf.running) { load(); return; }
        schedule();
      }, 4000);
    }
  }

  function render() {
    if (!_box) return;
    ensureStyles();
    var s = _st, b = _bf || {};
    var h = '<div class="kph-root kos-themed"><div class="kph-card"><div class="kph-hd"><b>📈 ' +
      esc(L('Historia de precios', 'Price history')) + ' ' + chip('eod_history') + '</b></div>';
    if (!s) {
      h += '<div class="kph-mut">' + esc(L('Cargando…', 'Loading…')) + '</div>';
    } else if (!s.db) {
      h += '<div class="kph-mut">' + esc(L('Sin base de datos no se guarda historia: el riesgo y los técnicos siguen usando la descarga en vivo.',
        'Without a database no history is stored: risk and technicals keep using the live download.')) + '</div>';
    } else {
      h += '<div class="kph-mut">' + esc(L('Cierres guardados: ', 'Stored closes: ')) + '<b>' + esc(num(s.rows)) + '</b> · ' +
        esc(num(s.instruments_with_prices)) + esc(L(' instrumentos', ' instruments')) +
        (s.first_date ? ' · ' + esc(s.first_date) + ' → ' + esc(s.last_date) : '') + '</div>';
      h += '<div class="kph-mut">' + esc(L('Tipo de cambio diario: ', 'Daily exchange rates: ')) + esc(num(s.fx_pairs)) +
        esc(L(' monedas', ' currencies')) + (s.fx_last ? ' · ' + esc(s.fx_last) : '') + ' · ' +
        esc(L('foto diaria de NRS y posiciones: ', 'daily NRS and positions snapshot: ')) + esc(s.metrics_last || L('aún no', 'not yet')) + '</div>';
      var d = s.daily || {};
      h += '<div class="kph-mut">' + esc(L('Carga diaria (días hábiles, después de las 22:00 UTC): ', 'Daily load (business days, after 22:00 UTC): ')) +
        esc(d.running ? L('corriendo…', 'running…') : (d.last_day || L('todavía no corrió', 'has not run yet'))) +
        (s.daily_enabled ? '' : ' · <span class="kph-warn">' + esc(L('apagada (PRICES_EOD=off)', 'off (PRICES_EOD=off)')) + '</span>') + '</div>';
      if (s.instruments_review) {
        h += '<div class="kph-mut">' + esc(L('Empresas para que elijas su precio de referencia: ', 'Companies for you to choose their reference price: ')) +
          '<b>' + esc(s.instruments_review) + '</b> (docs/REVISION_INSTRUMENTOS.md)</div>';
      }
      if (b.running || b.started_at) {
        var pct = Math.max(0, Math.min(100, Number(b.pct) || 0));
        h += '<div class="kph-mut">' + esc(b.running ? L('Descarga de historia en curso: ', 'History download running: ') : L('Última descarga de historia: ', 'Last history download: ')) +
          esc(num(b.done)) + ' / ' + esc(num(b.total)) + ' · ' + esc(num(b.rows)) + esc(L(' filas nuevas', ' new rows')) +
          (b.skipped ? ' · ' + esc(num(b.skipped)) + esc(L(' ya estaban', ' already there')) : '') +
          (b.failed ? ' · <span class="kph-warn">' + esc(num(b.failed)) + esc(L(' sin datos', ' without data')) + '</span>' : '') +
          (b.running && b.eta_s != null ? ' · ' + esc(L('faltan ~', '~')) + esc(Math.ceil(b.eta_s / 60)) + esc(L(' min', ' min left')) : '') +
          (b.stopped_reason ? ' · <span class="kph-warn">' + esc(b.stopped_reason === 'source_down' ? L('la fuente no respondió: vuelve a intentarlo más tarde', 'the source did not answer: try again later')
            : b.stopped_reason === 'stopped_by_operator' ? L('detenida (se puede reanudar)', 'stopped (can be resumed)') : b.stopped_reason) + '</span>' : '') +
          '</div><div class="kph-bar"><i style="width:' + pct + '%"></i></div>';
      }
      h += '<div class="kph-acts">' + (b.running
        ? '<button class="kph-btn" data-act="stop"' + (_busy ? ' disabled' : '') + '>' + esc(L('Detener (PIN)', 'Stop (PIN)')) + '</button>'
        : '<button class="kph-btn pri" data-act="start"' + (_busy ? ' disabled' : '') + '>' + esc(L('Descargar 5 años (PIN)', 'Download 5 years (PIN)')) + '</button>') + '</div>';
    }
    if (_msg) h += '<div class="kph-mut" style="margin-top:6px">' + _msg + '</div>';
    h += '</div></div>';
    _box.innerHTML = h;
    var bs = _box.querySelectorAll('[data-act]');
    for (var i = 0; i < bs.length; i++) {
      bs[i].addEventListener('click', function (ev) {
        var a = ev.currentTarget.getAttribute('data-act');
        if (a === 'start') start(); else if (a === 'stop') stop();
      });
    }
  }

  async function post(url, body) {
    var f = window._tradeFetch || fetch;
    var r = await f(BASE + url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}), timeout: 30000 }, true);
    var d = await r.json().catch(function () { return {}; });
    return { ok: r.ok, status: r.status, d: d };
  }

  async function start() {
    if (_busy) return;
    var ok = window.KhipuToast && window.KhipuToast.confirm ? await window.KhipuToast.confirm({
      title: L('¿Descargar 5 años de historia de precios?', 'Download 5 years of price history?'),
      note: L('Baja de Yahoo (gratis) los cierres diarios de ~570 empresas y ~20 monedas, despacio para no saturar la fuente: ' +
              'unas horas y ~100 MB en tu base. La app sigue funcionando normal. Queda registrado con tu PIN y se puede detener.',
              'Downloads (free, from Yahoo) the daily closes of ~570 companies and ~20 currencies, slowly so as not to overload ' +
              'the source: a few hours and ~100 MB in your database. The app keeps working normally. It is recorded with your PIN and can be stopped.'),
      confirmLabel: L('Descargar', 'Download'),
    }) : false;   // sin engine/toast.js no hay confirmación posible → no arranca
    if (!ok) return;
    _busy = true; _msg = '⏳ ' + esc(L('Arrancando…', 'Starting…')); render();
    var res = await post('/api/prices/backfill', { years: 5 });
    _busy = false;
    _msg = res.ok ? '✅ ' + esc(L('Descarga en marcha.', 'Download started.')) : '❌ ' + esc(errMsg(res.d, res.status));
    await load();
  }

  async function stop() {
    if (_busy) return;
    var ok = window.KhipuToast && window.KhipuToast.confirm ? await window.KhipuToast.confirm({
      title: L('¿Detener la descarga de historia?', 'Stop the history download?'),
      note: L('Lo ya bajado queda guardado; la próxima vez sigue donde quedó.', 'What was downloaded stays stored; next time it resumes where it left off.'),
      confirmLabel: L('Detener', 'Stop'),
    }) : false;
    if (!ok) return;
    _busy = true; render();
    var res = await post('/api/prices/backfill/stop', {});
    _busy = false;
    _msg = res.ok ? '⏸ ' + esc(L('Se detendrá al terminar el instrumento en curso.', 'It will stop after the current instrument.')) : '❌ ' + esc(errMsg(res.d, res.status));
    await load();
  }

  window.KhipuPriceHistory = {
    mount: function (id) {
      _box = document.getElementById(id);
      if (!_box) return;
      _msg = '';
      render();
      if (!_busy) load();
    },
    reload: function () { return load(); },
  };
})();
