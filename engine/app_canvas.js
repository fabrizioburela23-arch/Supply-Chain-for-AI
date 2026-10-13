
(function(){
'use strict';

/* ── palette & helpers ── */
/* 2026-10-06 (Canvas nivel Power BI): paleta categórica VALIDADA (validate_palette.js: banda de luminosidad,
   croma, separación para daltonismo ΔE≥8 entre vecinos, ΔE≥15 con vista normal, contraste ≥3:1) — la anterior
   fallaba 3 de 5 en el tema claro. Orden FIJO, nunca cíclico: la serie 9+ va en gris neutro ("otros"). */
const CV_PAL_D = ['#3987e5','#d95926','#199e70','#c98500','#d55181','#008300','#9085e9','#e66767'];
const CV_PAL_L = ['#2a78d6','#eb6834','#1baf7a','#eda100','#e87ba4','#008300','#4a3aa7','#e34948'];
const CV_OTHER = '#8a8577';
// las tarjetas usan var(--surface-2) del tema del <body> (.dark = predeterminado) → misma regla para los colores
function cvDark(){ return !document.body || document.body.classList.contains('dark'); }
function cvCol(i){ const p=cvDark()?CV_PAL_D:CV_PAL_L; return i<p.length?p[i]:CV_OTHER; }
window.cvCol = cvCol;
// rampa secuencial de UN tono (claro→oscuro) para mapas de calor; rojo si "más alto = peor"
const CV_SEQ = { blue:['#cfe1f7','#86b6ef','#5598e7','#256abf','#104281'], red:['#f7d0cf','#ee9b9a','#e34948','#b8302f','#7e1d1d'] };
function cvSeq(t,hue){ const r=CV_SEQ[hue]||CV_SEQ.blue, k=r.length-1, x=Math.max(0,Math.min(1,t))*k, i=Math.min(Math.floor(x),k-1), f=x-i;
  const a=r[i], b=r[i+1], h=c=>[1,3,5].map(j=>parseInt(c.slice(j,j+2),16)), A=h(a), B=h(b);
  return 'rgb('+A.map((v,j)=>Math.round(v+(B[j]-v)*f)).join(',')+')'; }
function cvEsc(s){ return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }
function cvFmt(v){
  if(v==null) return '—';
  if(typeof v==='boolean') return v?'Sí':'No';
  if(typeof v!=='number') return String(v);
  if(Math.abs(v)>=1e9) return (v/1e9).toFixed(1)+'B';
  if(Math.abs(v)>=1e6) return (v/1e6).toFixed(1)+'M';
  if(Math.abs(v)>=1e3) return (v/1e3).toFixed(1)+'K';
  return v % 1===0 ? String(v) : v.toFixed(2);
}

/* ── empty state (bilingüe; ejemplos que el router responde bien) ── */
const CV_W = {
  es:{sub:'Pregunta en lenguaje natural y el Canvas dibuja el gráfico adecuado: los pedidos que se pueden responder con precisión salen al instante sin IA (⚡); el resto los arma la IA (✦).',
      ph:'Pregunta al Canvas… «compara márgenes de Nvidia y AMD», «precio de TSMC 6 meses»',
      gen:'✦ Generar', busy:'⟳ Generando…', wait:'Generando visualización…',
      busySrv:'El servidor está reiniciándose (¿despliegue en curso?). Reintenta en ~1 min.', badResp:'Respuesta inesperada del servidor (HTTP {s}).',
      ex:['Compara márgenes de Nvidia y AMD','Precio de TSMC 6 meses','Riesgo por sector','Top 10 por capitalización','Relación entre riesgo y margen','Radar Nvidia vs TSMC vs ASML','Proveedores de TSMC','Heatmap riesgo por país y sector']},
  en:{sub:'Ask in plain language and the Canvas draws the right chart: requests that can be answered precisely appear instantly without AI (⚡); the rest are built by AI (✦).',
      ph:'Ask the Canvas… “compare margins of Nvidia and AMD”, “TSMC price 6 months”',
      gen:'✦ Generate', busy:'⟳ Generating…', wait:'Generating visualization…',
      busySrv:'The server is restarting (deploy in progress?). Try again in ~1 min.', badResp:'Unexpected server response (HTTP {s}).',
      ex:['Compare margins of Nvidia and AMD','TSMC price 6 months','Risk by sector','Top 10 by market cap','Risk vs margin','Radar Nvidia vs TSMC vs ASML','Suppliers of TSMC','Heatmap risk by country and sector']}
};
function cvW(k){ const l=(String(window.LANG||'es').slice(0,2)==='en')?'en':'es'; return CV_W[l][k]; }
function _cvShowWelcome(){
  const el=document.getElementById('canvas-cards');
  const qi=document.getElementById('canvas-query'); if(qi) qi.placeholder=cvW('ph');
  const bt=document.getElementById('canvas-send-txt'); if(bt&&!_cvBusy) bt.textContent=cvW('gen');
  if(!el||el.children.length) return;
  el.innerHTML=`<div data-cv-empty style="width:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:320px;gap:16px;padding:32px 16px;text-align:center">
    <div style="font-size:48px;opacity:.35">✦</div>
    <div style="font-size:20px;font-weight:700;color:var(--ink)">Canvas IA</div>
    <div style="font-size:13px;color:var(--ink-3);max-width:480px;line-height:1.65">${cvEsc(cvW('sub'))}</div>
    <div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;max-width:560px">
      ${cvW('ex').map(q=>`<span class="cv-ex" data-q="${cvEsc(q)}" style="font-size:11.5px;padding:6px 12px;background:var(--surface-2);border:1px solid var(--line);border-radius:20px;cursor:pointer;color:var(--ink-2)">${cvEsc(q)}</span>`).join('')}
    </div>
  </div>`;
  el.querySelectorAll('.cv-ex').forEach(s=>s.addEventListener('click',()=>{ const i=document.getElementById('canvas-query'); if(i){ i.value=s.getAttribute('data-q'); window.canvasGenerate(); } }));
}

window.initCanvasTab = function(){
  _cvShowWelcome();
};

/* ── main generator ──
   Flujo (router 2026-10-02, engine/localcharts.js):
   1) KhipuLocalCharts.try → spec local SOLO si la confianza es alta (todas las
      empresas resueltas, métrica que sí tenemos, intención que sabemos dibujar).
   2) tryAsync → lo mismo con datos del servidor (velas, estados anuales, cripto).
   3) IA (/api/canvas/generate): el interceptor de localcharts añade `hints`
      (intención/entidades/métricas) y el server valida el tipo de gráfico.
   4) Sin IA → KhipuLocalCharts.honest: "no puedo con precisión sin IA" + la
      respuesta parcial correcta más cercana (nunca un gráfico sin relación). */
let _cvBusy=false;
window.canvasGenerate = async function(){
  if(_cvBusy) return;
  const input=document.getElementById('canvas-query');
  const query=(input.value||'').trim();
  if(!query){ input.focus(); return; }

  _cvBusy=true;
  const btn=document.getElementById('canvas-send');
  const btnTxt=document.getElementById('canvas-send-txt');
  btnTxt.textContent=cvW('busy');
  btn.disabled=true;
  const done=()=>{ _cvBusy=false; btnTxt.textContent=cvW('gen'); btn.disabled=false; };

  /* create placeholder card */
  const cardId='cv-'+Date.now();
  const cardsEl=document.getElementById('canvas-cards');
  const emptyEl=cardsEl.querySelector('[data-cv-empty]');
  if(emptyEl) emptyEl.remove();

  cardsEl.insertAdjacentHTML('afterbegin',`
    <div id="${cardId}" class="cv-card">
      <div class="cv-card-hdr">
        <div><div class="cv-card-title">${cvEsc(query)}</div><div class="cv-card-sub">${cvEsc(cvW('wait'))}</div></div>
        <button class="cv-card-close" onclick="document.getElementById('${cardId}').remove()">✕</button>
      </div>
      <div style="height:180px;display:flex;align-items:center;justify-content:center"><div class="cv-spinner"></div></div>
    </div>`);
  cardsEl.scrollTop=0;

  const LC=window.KhipuLocalCharts;
  /* 1º: local confiable (0 ms, sin IA) */
  const _localSpec = LC && LC.try(query);
  if (_localSpec) {
    _cvRenderCard(cardId, query, _localSpec, 'local');
    input.value=''; done();
    return;
  }
  /* 2º: local con datos del servidor (precio histórico, estados anuales, cripto) */
  if (LC && LC.tryAsync) {
    const _localA = await LC.tryAsync(query);
    if (_localA) {
      _cvRenderCard(cardId, query, _localA, 'local');
      input.value=''; done();
      return;
    }
  }

  /* build compact context (localcharts añade datos de ficha y los hints) */
  const nodeCtx=(window.NODES||[]).slice(0,600).map(n=>{
    /* compacto: omitir campos nulos para no inflar el body (límite del servidor) */
    const o={id:n.id, label:n.label, cat:n.cat};
    if(n.mkt) o.mkt=n.mkt;
    if(n.margin!=null) o.margin=n.margin;
    if(n.growth!=null) o.growth=n.growth;
    if(n.port) o.port=n.port;
    if(n.country) o.country=n.country;
    if(n.preipo!=null) o.preipo=n.preipo;
    if(typeof computeNRS==='function'){ const s=computeNRS(n.id); if(s!=null) o.nrs=s; }
    return o;
  });
  const quotesCtx={};
  for(const [t,q] of Object.entries((window.MKT||{}).quotes||{})){
    if(q) quotesCtx[t]={close:q.close,prev:q.prev};
  }

  try{
    /* enriquecer con precios en vivo si la consulta menciona empresas */
    let live=null;
    if(window.canvasEnrichData){ try{ const en=await window.canvasEnrichData(query); live=(en&&en.live)||null; }catch(e){} }
    const r=await fetch('/api/canvas/generate',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({query,context:{nodes:nodeCtx,quotes:quotesCtx,live,selected_id:window._selectedNode||null}})});
    const ct=r.headers.get('content-type')||'';
    if(!ct.includes('application/json')){
      throw new Error(r.status>=500 ? cvW('busySrv') : cvW('badResp').replace('{s}',r.status));
    }
    const d=await r.json();
    if(d.error||!d.spec) throw new Error(d.error||'no spec');
    _cvRenderCard(cardId,query,d.spec,d.model);
    input.value='';
  } catch(e){
    /* sin IA: respuesta honesta + la parcial correcta más cercana */
    let shown=false;
    try{
      const hs = LC && LC.honest ? await LC.honest(query, e.message) : null;
      if(hs){ _cvRenderCard(cardId,query,hs,'local'); shown=true; }
    }catch(e2){}
    if(!shown){
      const card=document.getElementById(cardId);
      if(card) card.innerHTML=`
        <div class="cv-card-hdr">
          <div class="cv-card-title">${cvEsc(query)}</div>
          <button class="cv-card-close" onclick="document.getElementById('${cardId}').remove()">✕</button>
        </div>
        <div style="padding:20px;text-align:center;color:#f87171;font-size:13px">⚠ ${cvEsc(e.message)}</div>`;
    }
  } finally{
    done();
  }
};

/* ── card renderer ──
   Rediseño 2026-10-02 (feedback Fabrizio: "afinar en estética y resultado"):
   título legible (2 líneas, sin cortar), formato de cifras por unidad ($B→$T,
   %, NRS, años), barras con su valor, pie de "cómo se calculó" (fuente +
   ⚡ local sin IA / ✦ IA), tipos nuevos: grouped · kpi · donut · histogram ·
   notice (respuesta honesta sin IA + parcial). Responsivo a 375 px y con las
   variables de tema (claro/oscuro). API intacta:
   window._cvRenderCard(cardId, query, spec, modelLabel). */
const CV_T = {
  es:{bar:'Barras',line:'Línea',bubble:'Burbujas',treemap:'Treemap',heatmap:'Mapa de calor',radar:'Radar',scatter:'Dispersión',
      table:'Tabla',grouped:'Barras agrupadas',kpi:'Dato clave',donut:'Composición',histogram:'Distribución',notice:'Aviso',
      noData:'Sin datos', local:'⚡ local · sin IA', ai:'✦ IA', aiSrc:'calculado por IA con datos del catálogo y precios en vivo — verifica las cifras clave',
      cached:'caché', total:'Total', renderErr:'No se pudo dibujar', other:'Otros',
      asTable:'Ver como tabla', asChart:'Ver gráfico', csv:'Descargar CSV', period:'Periodo', series:'Serie', metric:'Métrica', value:'Valor', name:'Nombre'},
  en:{bar:'Bars',line:'Line',bubble:'Bubbles',treemap:'Treemap',heatmap:'Heatmap',radar:'Radar',scatter:'Scatter',
      table:'Table',grouped:'Grouped bars',kpi:'Key figure',donut:'Composition',histogram:'Distribution',notice:'Notice',
      noData:'No data', local:'⚡ local · no AI', ai:'✦ AI', aiSrc:'computed by AI from catalog data and live prices — double-check key figures',
      cached:'cache', total:'Total', renderErr:'Could not draw', other:'Others',
      asTable:'View as table', asChart:'View chart', csv:'Download CSV', period:'Period', series:'Series', metric:'Metric', value:'Value', name:'Name'}
};
function cvT(k){ const l=(String(window.LANG||'es').slice(0,2)==='en')?'en':'es'; return (CV_T[l][k]!=null?CV_T[l][k]:CV_T.es[k]); }
function cvEmpty(el){ el.innerHTML=`<div class="cv-empty">${cvT('noData')}</div>`; }

/* cifras por unidad: '$B' → $3.20T / $130B / $12.4B · '%' · 'NRS' · '$' · 'x' · 'year' · 'w' */
function cvFmtU(v,unit){
  if(v==null||v==='') return '—';
  if(typeof v!=='number'){ const n=Number(v); if(!isFinite(n)||String(v).trim()==='') return String(v); v=n; }
  if(!isFinite(v)) return '—';
  const u=String(unit||'').trim(), neg=v<0, a=Math.abs(v), s=neg?'−':'';
  const trim=x=>x.replace(/\.0+$/,'').replace(/(\.\d*?)0+$/,'$1');
  const comp=x=> x>=1e12?trim((x/1e12).toFixed(2))+'T':x>=1e9?trim((x/1e9).toFixed(1))+'B':x>=1e6?trim((x/1e6).toFixed(1))+'M':x>=1e4?trim((x/1e3).toFixed(1))+'k':(x%1===0?x.toLocaleString('en-US'):trim(x.toFixed(x<10?2:1)));
  switch(u){
    case '$B': case 'B$': case 'USD B': case 'B USD':
      return s+(a>=1000?'$'+trim((a/1000).toFixed(2))+'T':a>=100?'$'+Math.round(a)+'B':a>=1?'$'+trim(a.toFixed(1))+'B':'$'+Math.round(a*1000)+'M');
    case '$M': return s+(a>=1000?'$'+trim((a/1000).toFixed(1))+'B':'$'+trim(a.toFixed(a<10?1:0))+'M');
    case '$': case 'USD': return s+'$'+(a>=1e6?comp(a):a>=1000?Math.round(a).toLocaleString('en-US'):a.toFixed(2));
    case '%': return s+(a>=100?Math.round(a):trim(a.toFixed(1)))+'%';
    case 'NRS': return s+Math.round(a);
    case 'x': return s+trim(a.toFixed(1))+'x';
    case 'year': return String(Math.round(v));
    case 'w': return s+trim(a.toFixed(1));
    case '': return s+comp(a);
    default: return s+comp(a)+' '+u;
  }
}
function cvTimeLike(labels){
  return labels.length>=2 && labels.every(l=>/^(?:19|20)\d{2}(?:[-\/ ]?(?:Q[1-4]|\d{1,2}))?$|^(?:Q[1-4]|T[1-4])\s?(?:19|20)\d{2}$|^\d{1,2}\s\w{3,5}\.?\s\d{2}$/i.test(String(l).trim()));
}
function cvLocal(spec,model){ return (spec&&spec.engine==='local') || /local|sin ia|no ai/i.test(String(model||'')); }
function cvFoot(spec,model){
  const local=cvLocal(spec,model);
  const src=spec.source||(spec.config&&spec.config.source)||'';
  const m=String(model||'').replace(/^⚡\s*/,'');
  const eng= local ? cvT('local') : cvT('ai')+(m?' · '+m.slice(0,32):'')+(/^⚡/.test(String(model||''))?' · '+cvT('cached'):'');
  return `<div class="cv-foot"><span class="cv-eng ${local?'loc':'ai'}">${cvEsc(eng)}</span><span>${cvEsc(src || (local?'':cvT('aiSrc')))}</span></div>`;
}
function cvBody(el,spec){
  const fn={bar:_cvBar,line:_cvLine,treemap:_cvTreemap,heatmap:_cvHeatmap,radar:_cvRadar,scatter:_cvScatter,
            bubble:_cvBubble,table:_cvTable,grouped:_cvGrouped,kpi:_cvKpi,donut:_cvDonut,pie:_cvDonut,
            histogram:_cvHistogram}[spec.type] || _cvBar;   // tipo desconocido → barras, nunca JSON crudo
  fn(el,spec);
  // Los gráficos SVG/canvas se dibujan con el ancho medido; si la tarjeta aún no tenía su tamaño final
  // (recién insertada, ventana que cambia) el texto quedaba diminuto. Se redibuja al cambiar el ancho real.
  if(/^(line|scatter|bubble|radar|treemap)$/.test(spec.type) && window.ResizeObserver && !el._cvRO){
    let lastW=el.clientWidth, t=null;
    el._cvRO=new ResizeObserver(()=>{ const w=el.clientWidth; if(!w||Math.abs(w-lastW)<24) return; lastW=w;
      clearTimeout(t); t=setTimeout(()=>{ if(el.isConnected && !el.querySelector('.cv-tbl')) try{ fn(el,spec); }catch(e){} },120); });
    el._cvRO.observe(el);
  }
}

function _cvRenderCard(cardId,query,spec,model){
  const card=document.getElementById(cardId);
  if(!card||!spec) return;
  card.classList.add('cv-card');
  const isNotice=spec.type==='notice';
  card.innerHTML=`
    <div class="cv-card-hdr">
      <div style="min-width:0;flex:1">
        <div class="cv-chiprow"><span class="cv-chip ${isNotice?'warn':''}">${cvEsc(cvT(spec.type)||spec.type)}</span><span class="cv-q" title="${cvEsc(query)}">${cvEsc(query)}</span></div>
        <div class="cv-card-title cv-ttl">${cvEsc(spec.title||query)}</div>
        ${spec.subtitle?`<div class="cv-card-sub">${cvEsc(spec.subtitle)}</div>`:''}
      </div>
      <div class="cv-tools">${isNotice||spec.type==='table'?'':`<button class="cv-tool" data-cvact="table" title="${cvEsc(cvT('asTable'))}" aria-label="${cvEsc(cvT('asTable'))}">▦</button>`}${isNotice?'':`<button class="cv-tool" data-cvact="csv" title="${cvEsc(cvT('csv'))}" aria-label="${cvEsc(cvT('csv'))}">⤓</button>`}
      <button class="cv-card-close" aria-label="close" onclick="document.getElementById('${cardId}').remove()">✕</button></div>
    </div>
    <div id="${cardId}-body" class="cv-body"></div>
    ${spec.note?`<div class="cv-note">${cvEsc(spec.note)}</div>`:''}
    ${isNotice&&!spec.partial?'':cvFoot(isNotice?(spec.partial||spec):spec,model)}`;
  const body=document.getElementById(cardId+'-body');
  try{
    if(isNotice) _cvNotice(body,spec,cardId);
    else cvBody(body,spec);
  } catch(e){ body.innerHTML=`<div class="cv-empty" style="color:#f87171">${cvT('renderErr')}: ${cvEsc(e.message)}</div>`; }
  let asTable=false;
  card.querySelectorAll('[data-cvact]').forEach(b=>b.addEventListener('click',()=>{
    const act=b.getAttribute('data-cvact');
    if(act==='csv') return cvDownloadCSV(spec);
    asTable=!asTable;
    b.textContent=asTable?'◔':'▦';
    b.title=b.ariaLabel=cvT(asTable?'asChart':'asTable');
    try{ if(asTable) _cvTable(body,cvAsTable(spec)); else cvBody(body,spec); }catch(e){}
  }));
}

/* ── datos del gráfico como filas (vista de tabla + CSV): mismo origen, sin recalcular ── */
function cvRows(spec){
  const cfg=spec.config||{}, d=(spec.data||[]).filter(Boolean), unit=cfg.unit||'';
  const raw=[];   // filas con números crudos (CSV) — cols[i] ↔ fila[i]
  let cols;
  if(spec.type==='table'){ cols=cfg.columns||Object.keys(d[0]||{}); d.forEach(r=>raw.push(cols.map(c=>r[c]))); }
  else if(spec.type==='heatmap'){
    const rows=cfg.rows||[...new Set(d.map(x=>x.row))], cs=cfg.cols||[...new Set(d.map(x=>x.col))];
    const m=Object.fromEntries(d.map(x=>[x.row+'||'+x.col,x.value]));
    cols=[''].concat(cs); rows.forEach(r=>raw.push([r].concat(cs.map(c=>m[r+'||'+c]??null))));
  } else if(spec.type==='scatter'||spec.type==='bubble'){
    cols=['', cfg.x_label||'X', cfg.y_label||'Y'].concat(spec.type==='bubble'?[cfg.r_label||'r']:[]);
    d.forEach(x=>raw.push([x.label, +x.x, +x.y].concat(spec.type==='bubble'?[+x.r]:[])));
  } else if(spec.type==='radar'){
    cols=[cvT('series')].concat(cfg.axes||[]); d.forEach(x=>raw.push([x.label].concat(x.values||[])));
  } else if(spec.type==='grouped'){
    cols=[cvT('metric')].concat(cfg.series_labels||[]); d.forEach(g=>raw.push([g.label].concat(g.values||[])));
  } else if(d[0]&&Array.isArray(d[0].values)){
    const sl=cfg.series_labels||d.map(x=>x.label), n=Math.max(...d.map(x=>(x.values||[]).length));
    cols=[cvT('period')].concat(sl);
    for(let i=0;i<n;i++) raw.push([(cfg.labels||[])[i]??String(i+1)].concat(d.map(x=>(x.values||[])[i]??null)));
  } else {
    cols=['', cvT('value')+(unit?' ('+unit+')':'')].concat(d.some(x=>x.sub)?['']:[]);
    d.forEach(x=>raw.push([x.label, x.value!=null&&isFinite(+x.value)?+x.value:x.value].concat(d.some(y=>y.sub)?[x.sub||'']:[])));
  }
  return {cols, raw, unit};
}
function cvAsTable(spec){
  const {cols,raw,unit}=cvRows(spec), uniq=cols.map((c,i)=>c||(i===0?cvT('name'):'·'+i));
  return {type:'table', config:{columns:uniq, unit}, data:raw.map(r=>Object.fromEntries(uniq.map((c,i)=>{
    const v=r[i]; return [c, typeof v==='number'&&i>0&&spec.type!=='table'?cvFmtU(v,(spec.data||[])[0]&&(spec.data||[])[0].unit!=null?spec.data[0].unit:unit):v];
  })))};
}
function cvDownloadCSV(spec){
  const {cols,raw}=cvRows(spec);
  const q=v=>{ if(v==null) return ''; const t=String(v); return /[",\n;]/.test(t)?'"'+t.replace(/"/g,'""')+'"':t; };
  const csv='\ufeff'+[cols].concat(raw).map(r=>r.map(q).join(',')).join('\n');
  const name=(String(spec.title||'khipus-grafico').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^\w]+/g,'-').replace(/^-|-$/g,'').slice(0,60)||'khipus')+'.csv';
  const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})); a.download=name;
  document.body.appendChild(a); a.click(); setTimeout(()=>{ URL.revokeObjectURL(a.href); a.remove(); },500);
}

/* ── TOOLTIP compartido: todo elemento con data-tip dentro de un gráfico muestra su valor al pasar el mouse ── */
const cvTip=(function(){
  let el=null;
  function node(){ if(!el){ el=document.createElement('div'); el.className='cv-tip'; el.setAttribute('role','tooltip'); document.body.appendChild(el); } return el; }
  function show(html,x,y){ const t=node(); t.innerHTML=html; t.style.display='block';
    const w=t.offsetWidth, h=t.offsetHeight, vw=window.innerWidth, vh=window.innerHeight;
    t.style.left=Math.max(6,Math.min(vw-w-6,x+14))+'px'; t.style.top=Math.max(6,(y+h+18>vh?y-h-12:y+14))+'px'; }
  function hide(){ if(el) el.style.display='none'; }
  document.addEventListener('mouseover',e=>{ const m=e.target.closest&&e.target.closest('.cv-body [data-tip]'); if(m) show(cvEsc(m.getAttribute('data-tip')).replace(/\n/g,'<br>'),e.clientX,e.clientY); });
  document.addEventListener('mousemove',e=>{ if(el&&el.style.display==='block'&&e.target.closest&&e.target.closest('.cv-body [data-tip]')) show(el.innerHTML,e.clientX,e.clientY); });
  document.addEventListener('mouseout',e=>{ if(e.target.closest&&e.target.closest('.cv-body [data-tip]')) hide(); });
  document.addEventListener('scroll',hide,true);
  return {show,hide};
})();

/* ── NOTICE: "no puedo con precisión sin IA" + la parcial correcta más cercana ── */
function _cvNotice(el,spec,cardId){
  const c=spec.config||{};
  const p=spec.partial;
  el.innerHTML=`<div class="cv-notice ${c.tone==='info'?'info':''}">${cvEsc(c.message||'')}</div>
    ${p?`<div class="cv-partial-lbl">${cvEsc(c.partial_label||'')}</div>
      <div class="cv-partial"><div class="cv-card-title" style="font-size:13px">${cvEsc(p.title||'')}</div>
      ${p.subtitle?`<div class="cv-card-sub">${cvEsc(p.subtitle)}</div>`:''}
      <div id="${cardId}-pbody" class="cv-body"></div>${p.note?`<div class="cv-note">${cvEsc(p.note)}</div>`:''}</div>`
      :(c.partial_label?`<div class="cv-partial-lbl">${cvEsc(c.partial_label)}</div>`:'')}`;
  if(p){ const pb=document.getElementById(cardId+'-pbody'); try{ cvBody(pb,p); }catch(e){ pb.innerHTML=''; } }
}

/* ── BAR (horizontal, con valor y unidad; negativos divergen desde 0) ── */
function _cvBar(el,spec){
  let data=(spec.data||[]).filter(d=>d&&d.value!=null&&isFinite(+d.value)).map(d=>Object.assign({},d,{value:+d.value}));
  if(!data.length) return cvEmpty(el);
  const cfg=spec.config||{}, unit=cfg.unit||'';
  const labels=data.map(d=>String(d.label??''));
  const keep= cfg.sort==='none' || cfg.time || cvTimeLike(labels) || spec.engine==='local';
  if(!keep) data.sort((a,b)=>b.value-a.value);
  data=data.slice(0,20);
  const maxPos=Math.max(0,...data.map(d=>d.value)), maxNeg=Math.max(0,...data.map(d=>-d.value));
  const scaleMax= unit==='NRS' ? Math.max(100,maxPos) : (cfg.max||0);
  const span=(scaleMax?Math.max(scaleMax,maxPos):maxPos)+maxNeg || 1;
  const zero=maxNeg/span*100;
  const longLbl=Math.max(...labels.map(l=>l.length))>26;
  el.innerHTML=`<div class="cv-bars ${longLbl?'stack':''}">`+data.map((d,i)=>{
    const col=d.color||cvCol(0), v=d.value, own=d.max?(Math.abs(v)/d.max*100):null;
    const w=own!=null?Math.min(100,own):Math.abs(v)/span*100;
    const left=own!=null?0:(v<0?zero-w:zero);
    return `<div class="cv-bar-row" data-tip="${cvEsc(d.label)}: ${cvEsc(cvFmtU(v,unit))}${d.sub?' · '+cvEsc(d.sub):''}">
      <div class="cv-bar-label">${cvEsc(d.label)}</div>
      <div class="cv-bar-line"><div class="cv-bar-track">${maxNeg&&own==null?`<div class="cv-bar-zero" style="left:${zero.toFixed(2)}%"></div>`:''}<div class="cv-bar-fill" style="left:${left.toFixed(2)}%;width:${Math.max(.6,w).toFixed(2)}%;background:${v<0&&!d.color?'#f87171':col}"></div></div>
      <div class="cv-bar-val">${cvEsc(cvFmtU(v,unit))}${d.max?`<span class="cv-dim">/${d.max}</span>`:''}</div></div>
    </div>`;
  }).join('')+'</div>';
}

/* ── GROUPED: un bloque por métrica, una barra por serie (empresa) ── */
function _cvGrouped(el,spec){
  const data=(spec.data||[]).filter(g=>g&&Array.isArray(g.values));
  const cfg=spec.config||{};
  const series=cfg.series_labels||[];
  if(!data.length||!series.length) return cvEmpty(el);
  const colors=series.map((_,i)=>(cfg.colors&&cfg.colors[i])||cvCol(i));
  el.innerHTML=`<div class="cv-legend">${series.map((s,i)=>`<span><i style="background:${colors[i]}"></i>${cvEsc(s)}</span>`).join('')}</div>
    <div class="cv-groups">${data.map(g=>{
      const unit=g.unit!=null?g.unit:(cfg.unit||'');
      const vals=g.values.map(v=>v==null||!isFinite(+v)?null:+v);
      const mx=Math.max(...vals.map(v=>v==null?0:Math.abs(v)))||1;
      const scale=unit==='NRS'?Math.max(100,mx):mx;
      return `<div class="cv-group"><div class="cv-group-h">${cvEsc(g.label)}</div>${series.map((s,i)=>{
        const v=vals[i];
        return `<div class="cv-bar-row compact" data-tip="${cvEsc(s)} · ${cvEsc(g.label)}: ${cvEsc(cvFmtU(v,unit))}"><div class="cv-bar-label">${cvEsc(s)}</div>
          <div class="cv-bar-line"><div class="cv-bar-track">${v==null?'':`<div class="cv-bar-fill" style="left:0;width:${Math.max(.6,Math.abs(v)/scale*100).toFixed(2)}%;background:${v<0?'#f87171':colors[i]}"></div>`}</div>
          <div class="cv-bar-val">${v==null?'<span class="cv-dim">—</span>':cvEsc(cvFmtU(v,unit))}</div></div></div>`;
      }).join('')}</div>`;
    }).join('')}</div>`;
}

/* ── KPI: 1-6 tarjetas con la cifra grande ── */
function _cvKpi(el,spec){
  const data=(spec.data||[]).filter(d=>d&&d.value!=null);
  if(!data.length) return cvEmpty(el);
  const big=data.length===1;
  el.innerHTML=`<div class="cv-kpis ${big?'one':''}">${data.slice(0,8).map((d,i)=>`
    <div class="cv-kpi" style="border-left-color:${d.color||cvCol(i)}">
      <div class="cv-kpi-l">${cvEsc(d.label||'')}</div>
      <div class="cv-kpi-v" style="${d.color?'color:'+d.color:''}">${cvEsc(cvFmtU(d.value,d.unit!=null?d.unit:(spec.config&&spec.config.unit)||''))}</div>
      ${d.sub?`<div class="cv-kpi-s">${cvEsc(d.sub)}</div>`:''}
    </div>`).join('')}</div>`;
}

/* ── DONUT (≤6 porciones; más → treemap) ── */
function _cvDonut(el,spec){
  const data=(spec.data||[]).filter(d=>d&&isFinite(+d.value)&&+d.value>0).map(d=>Object.assign({},d,{value:+d.value}));
  if(!data.length) return cvEmpty(el);
  if(data.length>6) return _cvTreemap(el,spec);
  data.sort((a,b)=>b.value-a.value);
  const unit=(spec.config||{}).unit||'';
  const tot=data.reduce((s,d)=>s+d.value,0)||1;
  const R=62, C=2*Math.PI*R; let off=0;
  const arcs=data.map((d,i)=>{ const f=d.value/tot, len=f*C;
    const gap=data.length>1?Math.min(1.5,len/3):0;
    const a=`<circle r="${R}" cx="80" cy="80" fill="none" stroke="${d.color||cvCol(i)}" stroke-width="26" stroke-dasharray="${(len-gap).toFixed(2)} ${(C-len+gap).toFixed(2)}" stroke-dashoffset="${(-off).toFixed(2)}" transform="rotate(-90 80 80)" data-tip="${cvEsc(d.label)}: ${cvEsc(cvFmtU(d.value,unit))} (${(f*100).toFixed(1)}%)" style="cursor:default"></circle>`;
    off+=len; return a; }).join('');
  el.innerHTML=`<div class="cv-donut">
    <svg viewBox="0 0 160 160" class="cv-donut-svg">${arcs}
      <text x="80" y="76" text-anchor="middle" style="fill:var(--ink-3);font-size:10px">${cvT('total')}</text>
      <text x="80" y="94" text-anchor="middle" style="fill:var(--ink);font-size:15px;font-weight:700">${cvEsc(cvFmtU(tot,unit))}</text></svg>
    <div class="cv-donut-leg">${data.map((d,i)=>`<div><i style="background:${d.color||cvCol(i)}"></i><span class="n">${cvEsc(d.label)}</span><span class="v">${(d.value/tot*100).toFixed(1)}%</span><span class="cv-dim">${cvEsc(cvFmtU(d.value,unit))}</span></div>`).join('')}</div>
  </div>`;
}

/* ── HISTOGRAM (columnas: cuántos caen en cada rango) ── */
function _cvHistogram(el,spec){
  const data=(spec.data||[]).filter(d=>d&&isFinite(+d.value));
  if(!data.length) return cvEmpty(el);
  const mx=Math.max(...data.map(d=>+d.value))||1;
  const cfg=spec.config||{};
  el.innerHTML=`<div class="cv-hist">${data.map((d,i)=>`<div class="cv-hcol" data-tip="${cvEsc(d.label)}: ${cvEsc(d.value)} ${cvEsc(cfg.unit||'')}">
      <div class="cv-hval">${cvEsc(cvFmtU(+d.value,''))}</div>
      <div class="cv-hbar-wrap"><div class="cv-hbar" style="height:${Math.max(1.5,(+d.value)/mx*100).toFixed(1)}%;background:${d.color||cvCol(0)}"></div></div>
      <div class="cv-hlbl">${cvEsc(d.label)}</div></div>`).join('')}</div>
    ${cfg.x_label?`<div class="cv-axis-lbl">${cvEsc(cfg.x_label)}${cfg.unit?' · '+cvEsc(cfg.unit):''}</div>`:''}`;
}

/* ── LINE (series [{label,values}] o puntos [{label,value}]; huecos = null) ── */
function _cvLine(el,spec){
  let data=spec.data||[];
  if(!data.length) return cvEmpty(el);
  const cfg=spec.config||{}, unit=cfg.unit||'';
  let labels;
  if(data[0] && Array.isArray(data[0].values)){
    labels=(data[0].values||[]).map((_,i)=> (cfg.labels||[])[i] ?? String(i+1));
  } else {
    labels=data.map(d=> String(d.label!=null?d.label:''));
    data=[{ label:(cfg.series_labels&&cfg.series_labels[0])||spec.title||'', values:data.map(d=> d.value==null?null:+d.value), color:(data[0]||{}).color }];
  }
  const seriesLabels=cfg.series_labels||data.map((d,i)=> d.label || `Serie ${i+1}`);
  const allVals=data.flatMap(d=>(d.values||[]).filter(v=>v!=null&&isFinite(v)));
  if(!allVals.length) return cvEmpty(el);
  let minV=Math.min(...allVals), maxV=Math.max(...allVals);
  const pad=(maxV-minV)*0.08||Math.abs(maxV)*0.05||1; minV-=pad; maxV+=pad;
  if(Math.min(...allVals)>=0 && minV<0) minV=0;
  // ancho real del contenedor → el texto conserva ~10-11 px también a 375 px
  const W=Math.max(300,Math.min(760,el.clientWidth||600)), H=W<480?210:230, PAD={t:12,r:58,b:28,l:54};
  const cw=W-PAD.l-PAD.r, ch=H-PAD.t-PAD.b;
  const n=Math.max(...data.map(d=>(d.values||[]).length));
  const xS=i=>PAD.l+i/(Math.max(n-1,1))*cw;
  const yS=v=>PAD.t+ch-(v-minV)/(maxV-minV||1)*ch;
  const paths=data.map((d,si)=>{
    const col=d.color||cvCol(si); let p='', on=false;
    (d.values||[]).forEach((v,i)=>{ if(v==null||!isFinite(v)){ on=false; return; } p+=(on?' L':' M')+xS(i).toFixed(1)+','+yS(v).toFixed(1); on=true; });
    const area= data.length===1 && p ? `<path d="${p} L${xS((d.values||[]).length-1).toFixed(1)},${(PAD.t+ch).toFixed(1)} L${PAD.l},${(PAD.t+ch).toFixed(1)} Z" fill="${col}" opacity=".08"/>` : '';
    return area+`<path d="${p}" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
  });
  const ends=data.map((d,si)=>{ const vs=d.values||[]; let li=vs.length-1; while(li>=0&&(vs[li]==null||!isFinite(vs[li]))) li--; if(li<0) return '';
    const col=d.color||cvCol(si);
    return `<circle cx="${xS(li).toFixed(1)}" cy="${yS(vs[li]).toFixed(1)}" r="3.6" fill="${col}"/><text x="${(xS(li)+6).toFixed(1)}" y="${(yS(vs[li])+4).toFixed(1)}" style="fill:${col};font-size:11px;font-weight:700">${cvEsc(cvFmtU(vs[li],unit))}</text>`; }).join('');
  const step=Math.max(1,Math.ceil(labels.length/(W<480?4:6)));
  const ticks=[0,0.25,0.5,0.75,1].map(t=>{const v=minV+(maxV-minV)*t; return `<line x1="${PAD.l}" x2="${W-PAD.r}" y1="${yS(v).toFixed(1)}" y2="${yS(v).toFixed(1)}" stroke="currentColor" stroke-opacity=".12"/><text x="${PAD.l-6}" y="${(yS(v)+4).toFixed(1)}" text-anchor="end" style="fill:var(--ink-3);font-size:10px">${cvEsc(cvFmtU(v,unit))}</text>`;}).join('');
  el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" class="cv-svg" role="img">
    ${ticks}
    ${labels.map((lb,i)=> (i%step===0||i===labels.length-1)&&(i===labels.length-1||labels.length-1-i>=step/2) ? `<text x="${xS(i).toFixed(1)}" y="${H-8}" text-anchor="middle" style="fill:var(--ink-3);font-size:10px">${cvEsc(lb)}</text>` : '').join('')}
    ${paths.join('')}${ends}
    <g class="cv-xh" style="display:none;pointer-events:none"><line y1="${PAD.t}" y2="${PAD.t+ch}" stroke="currentColor" stroke-opacity=".45" stroke-dasharray="3 3"/>
      ${data.map((d,si)=>`<circle r="4.5" fill="${d.color||cvCol(si)}" stroke="var(--surface-2)" stroke-width="2"/>`).join('')}</g>
    <rect class="cv-hit" x="${PAD.l}" y="${PAD.t}" width="${cw}" height="${ch}" fill="transparent" style="cursor:crosshair"/>
  </svg>
  ${data.length>1?`<div class="cv-legend">${data.map((d,si)=>`<span><i style="background:${d.color||cvCol(si)}"></i>${cvEsc(seriesLabels[si]||d.label||'')}</span>`).join('')}</div>`:''}`;
  // CRUZ + TOOLTIP: el periodo bajo el mouse y el valor de cada serie (como Power BI)
  const svg=el.querySelector('svg'), hit=svg&&svg.querySelector('.cv-hit'), xh=svg&&svg.querySelector('.cv-xh');
  if(!hit||!xh) return;
  const ln=xh.querySelector('line'), dots=xh.querySelectorAll('circle');
  function at(e){
    const r=svg.getBoundingClientRect(), x=(e.clientX-r.left)*W/(r.width||W);
    const i=Math.max(0,Math.min(n-1,Math.round((x-PAD.l)/(cw||1)*(n-1)))), X=xS(i).toFixed(1);
    ln.setAttribute('x1',X); ln.setAttribute('x2',X); xh.style.display='';
    const rows=[];
    data.forEach((d,si)=>{ const v=(d.values||[])[i], ok=v!=null&&isFinite(v);
      dots[si].style.display=ok?'':'none'; if(ok){ dots[si].setAttribute('cx',X); dots[si].setAttribute('cy',yS(v).toFixed(1)); }
      rows.push(`<div class="cv-tip-r"><i style="background:${d.color||cvCol(si)}"></i><span>${cvEsc(seriesLabels[si]||d.label||'')}</span><b>${ok?cvEsc(cvFmtU(v,unit)):'—'}</b></div>`); });
    cvTip.show(`<div class="cv-tip-h">${cvEsc(labels[i]||'')}</div>`+rows.join(''),e.clientX,e.clientY);
  }
  hit.addEventListener('mousemove',at);
  hit.addEventListener('mouseleave',()=>{ xh.style.display='none'; cvTip.hide(); });
}

/* ── TREEMAP (squarified; tamaño = peso en el total) ── */
function _cvTreemap(el,spec){
  const raw=(spec.data||[]).filter(d=>d&&isFinite(+d.value)&&+d.value>0).map(d=>Object.assign({},d,{value:+d.value}));
  if(!raw.length) return cvEmpty(el);
  const unit=(spec.config||{}).unit||'';
  const items=raw.sort((a,b)=>b.value-a.value).slice(0,30);
  const tot=items.reduce((s,d)=>s+d.value,0)||1;
  const W=Math.max(260,el.clientWidth||560), H=W<420?300:270;
  const rects=[];
  // algoritmo squarified (Bruls et al.) — compacto
  (function sq(list,x,y,w,h){
    if(!list.length) return;
    const sum=list.reduce((s,d)=>s+d.value,0);
    const area=list.map(d=>d.value/sum*w*h);
    const short=Math.min(w,h); let row=[], best=Infinity, i=0;
    const worst=(r)=>{ const s=r.reduce((a,b)=>a+b,0), mx=Math.max(...r), mn=Math.min(...r); return Math.max(short*short*mx/(s*s), (s*s)/(short*short*mn)); };
    while(i<list.length){ const nr=row.concat(area[i]); const wv=worst(nr); if(wv<=best){ row=nr; best=wv; i++; } else break; }
    const rs=row.reduce((a,b)=>a+b,0);
    if(w>=h){ const cwid=rs/h; let yy=y; row.forEach((a,k)=>{ const hh=a/cwid; rects.push([list[k],x,yy,cwid,hh]); yy+=hh; }); sq(list.slice(row.length),x+cwid,y,w-cwid,h); }
    else { const rh=rs/w; let xx=x; row.forEach((a,k)=>{ const ww=a/rh; rects.push([list[k],xx,y,ww,rh]); xx+=ww; }); sq(list.slice(row.length),x,y+rh,w,h-rh); }
  })(items,0,0,W,H);
  el.innerHTML=`<div class="cv-tm" style="height:${H}px">${rects.map(([d,x,y,w,h],i)=>{
    const pct=d.value/tot*100, show=w>54&&h>30;
    return `<div class="cv-tm-cell" title="${cvEsc(d.label)}: ${cvEsc(cvFmtU(d.value,unit))} (${pct.toFixed(1)}%)" style="left:${(x/W*100).toFixed(3)}%;top:${y.toFixed(1)}px;width:${(w/W*100).toFixed(3)}%;height:${h.toFixed(1)}px;background:${d.color||cvCol(i)}">
      ${show?`<div class="n">${cvEsc(d.label)}</div><div class="v">${cvEsc(cvFmtU(d.value,unit))} · ${pct.toFixed(pct<10?1:0)}%</div>`:''}</div>`;
  }).join('')}</div>`;
}

/* ── HEATMAP (SVG; el texto usa style= porque los atributos SVG no resuelven var()) ── */
function _cvHeatmap(el,spec){
  const data=(spec.data||[]).filter(d=>d&&d.row!=null&&d.col!=null);
  const cfg=spec.config||{};
  const rows=cfg.rows||[...new Set(data.map(d=>d.row))];
  const cols=cfg.cols||[...new Set(data.map(d=>d.col))];
  const unit=cfg.unit||'';
  if(!rows.length||!cols.length||!data.length) return cvEmpty(el);
  const vals=data.map(d=>+d.value).filter(isFinite);
  const minV=Math.min(...vals), maxV=Math.max(...vals);
  const CELL=46, LPAD=96, THEAD=78;
  const W=LPAD+cols.length*CELL, H=THEAD+rows.length*CELL;
  const heat=Object.fromEntries(data.map(d=>[`${d.row}||${d.col}`,+d.value]));
  const hue=cfg.higher_is_worse?'red':'blue';
  function lerp(t){ return cvSeq(t,hue); }
  const cells=rows.flatMap((r,ri)=>cols.map((c,ci)=>{
    const v=heat[`${r}||${c}`];
    const has=v!=null&&isFinite(v), t=has?(v-minV)/(maxV-minV||1):0;
    return `<rect x="${LPAD+ci*CELL}" y="${THEAD+ri*CELL}" width="${CELL-3}" height="${CELL-3}" rx="4" fill="${has?lerp(t):'rgba(120,130,150,.08)'}" data-tip="${cvEsc(r)} × ${cvEsc(c)}: ${has?cvEsc(cvFmtU(v,unit)):'—'}"></rect>
      ${has?`<text x="${LPAD+ci*CELL+CELL/2-1.5}" y="${THEAD+ri*CELL+CELL/2+3}" text-anchor="middle" style="fill:${t>0.55?'#ffffff':'#14110c'};font-size:11px;font-weight:700;pointer-events:none">${cvEsc(cvFmtU(v,unit))}</text>`:''}`;
  }));
  el.innerHTML=`<div class="cv-scroll"><svg viewBox="0 0 ${W} ${H}" style="width:100%;min-width:${Math.min(W,560)}px;display:block">
    ${cols.map((c,ci)=>`<text x="${LPAD+ci*CELL+CELL/2-1}" y="${THEAD-8}" text-anchor="start" transform="rotate(-38 ${LPAD+ci*CELL+CELL/2-1} ${THEAD-8})" style="fill:var(--ink-3);font-size:10px">${cvEsc(String(c).length>16?String(c).slice(0,15)+'…':String(c))}<title>${cvEsc(c)}</title></text>`).join('')}
    ${rows.map((r,ri)=>`<text x="${LPAD-8}" y="${THEAD+ri*CELL+CELL/2+3}" text-anchor="end" style="fill:var(--ink-2);font-size:11px">${cvEsc(String(r).slice(0,15))}</text>`).join('')}
    ${cells.join('')}
  </svg></div>`;
}

/* ── RADAR (Canvas 2D polar; tamaño según el ancho disponible) ── */
function _cvRadar(el,spec){
  const data=(spec.data||[]).filter(d=>d&&Array.isArray(d.values));
  const axes=(spec.config||{}).axes||[];
  if(!data.length||axes.length<3) return cvEmpty(el);
  const SZ=Math.max(200,Math.min(290,(el.clientWidth||300)-90)), WR=SZ+90, CX=WR/2, CY=SZ/2, R=SZ*0.34;
  const N=axes.length, step=2*Math.PI/N;
  const id='cv-radar-'+Math.random().toString(36).slice(2,7);
  el.innerHTML=`<div class="cv-radar"><canvas id="${id}" width="${WR}" height="${SZ}" style="width:${WR}px;height:${SZ}px;max-width:100%"></canvas>
    <div class="cv-legend col">${data.map((s,si)=>`<span><i style="background:${s.color||cvCol(si)}"></i>${cvEsc(s.label||'')}</span>`).join('')}</div></div>`;
  requestAnimationFrame(()=>{
    const cv=document.getElementById(id); if(!cv) return;
    const ink=getComputedStyle(el).color||'#9aa';
    const ctx=cv.getContext('2d'), dpr=window.devicePixelRatio||1;
    cv.width=WR*dpr; cv.height=SZ*dpr; ctx.scale(dpr,dpr);
    for(let r=1;r<=4;r++){ ctx.beginPath();
      for(let i=0;i<N;i++){ const a=i*step-Math.PI/2, x=CX+Math.cos(a)*R*(r/4), y=CY+Math.sin(a)*R*(r/4); i===0?ctx.moveTo(x,y):ctx.lineTo(x,y); }
      ctx.closePath(); ctx.strokeStyle='rgba(128,140,170,.22)'; ctx.lineWidth=1; ctx.stroke(); }
    for(let i=0;i<N;i++){ const a=i*step-Math.PI/2;
      ctx.beginPath(); ctx.moveTo(CX,CY); ctx.lineTo(CX+Math.cos(a)*R,CY+Math.sin(a)*R); ctx.strokeStyle='rgba(128,140,170,.25)'; ctx.stroke();
      const lx=CX+Math.cos(a)*(R+14), ly=CY+Math.sin(a)*(R+14);
      ctx.font='600 11px system-ui,sans-serif'; ctx.fillStyle=ink; ctx.globalAlpha=.85;
      ctx.textAlign=Math.abs(lx-CX)<10?'center':lx>CX?'left':'right'; ctx.textBaseline='middle';
      String(axes[i]||'').split(' ').forEach((w,wi)=>ctx.fillText(w,lx,ly+wi*12)); ctx.globalAlpha=1; }
    data.forEach((s,si)=>{
      const col=s.color||cvCol(si), vals=s.values||[];
      ctx.beginPath();
      for(let i=0;i<N;i++){ const v=Math.max(0,Math.min(100,+vals[i]||0))/100, a=i*step-Math.PI/2; const x=CX+Math.cos(a)*R*v, y=CY+Math.sin(a)*R*v; i===0?ctx.moveTo(x,y):ctx.lineTo(x,y); }
      ctx.closePath(); ctx.strokeStyle=col; ctx.lineWidth=2; ctx.stroke(); ctx.globalAlpha=.13; ctx.fillStyle=col; ctx.fill(); ctx.globalAlpha=1;
      for(let i=0;i<N;i++){ const v=Math.max(0,Math.min(100,+vals[i]||0))/100, a=i*step-Math.PI/2;
        ctx.beginPath(); ctx.arc(CX+Math.cos(a)*R*v,CY+Math.sin(a)*R*v,3.2,0,2*Math.PI); ctx.fillStyle=col; ctx.fill(); }
    });
  });
}

/* ── SCATTER / BUBBLE (Canvas 2D; ancho del contenedor; etiqueta los extremos) ── */
function _cvScatter(el,spec){ _cvScatterBase(el,spec,false); }
function _cvBubble(el,spec){ _cvScatterBase(el,spec,true); }
function _cvScatterBase(el,spec,isBubble){
  const data=(spec.data||[]).filter(d=>d&&isFinite(+d.x)&&isFinite(+d.y));
  if(!data.length) return cvEmpty(el);
  const cfg=spec.config||{};
  const W=Math.max(260,Math.min(680,el.clientWidth||560)), H=W<420?240:270, PAD={t:14,r:16,b:34,l:52};
  const xs=data.map(d=>+d.x), ys=data.map(d=>+d.y), rs=isBubble?data.map(d=>+d.r||1):null;
  // dominio robusto: un atípico (p.ej. margen −131 %) no debe aplastar al resto;
  // se dibuja en el borde, hueco, con su valor real en la etiqueta
  const fence=a=>{ const s=[...a].sort((p,q)=>p-q), q=f=>s[Math.min(s.length-1,Math.max(0,Math.round(f*(s.length-1))))];
    const q1=q(.25), q3=q(.75), k=3*((q3-q1)||Math.abs(q3)||1); return [Math.min(...s.filter(v=>v>=q1-k)), Math.max(...s.filter(v=>v<=q3+k))]; };
  let [minX,maxX]=data.length>=8?fence(xs):[Math.min(...xs),Math.max(...xs)];
  let [minY,maxY]=data.length>=8?fence(ys):[Math.min(...ys),Math.max(...ys)];
  const isOut=d=>+d.x<minX||+d.x>maxX||+d.y<minY||+d.y>maxY;
  const px=(maxX-minX)*.06||1, py=(maxY-minY)*.08||1; minX-=px; maxX+=px; minY-=py; maxY+=py;
  const maxR=isBubble?(Math.max(...rs)||1):1;
  let Wd=W; const sx=v=>PAD.l+(v-minX)/(maxX-minX||1)*(Wd-PAD.l-PAD.r);
  const sy=v=>PAD.t+(1-(v-minY)/(maxY-minY||1))*(H-PAD.t-PAD.b);
  const id='cv-sc-'+Math.random().toString(36).slice(2,7);
  const xl=cfg.x_label||'X', yl=cfg.y_label||'Y';
  el.innerHTML=`<canvas id="${id}" style="width:100%;height:${H}px;display:block"></canvas>
    <div class="cv-axis-lbl">→ ${cvEsc(xl)} &nbsp;·&nbsp; ↑ ${cvEsc(yl)}</div>`;
  requestAnimationFrame(()=>{
    const cv=document.getElementById(id); if(!cv) return;
    const ink=getComputedStyle(el).color||'#9aa';
    Wd=cv.clientWidth||W; const ctx=cv.getContext('2d'), dpr=window.devicePixelRatio||1;
    cv.width=Wd*dpr; cv.height=H*dpr; ctx.scale(dpr,dpr);
    ctx.font='10px system-ui'; ctx.fillStyle=ink; ctx.globalAlpha=.7;
    for(let t=0;t<=4;t++){ const v=minY+(maxY-minY)*t/4, y=sy(v);
      ctx.strokeStyle='rgba(128,140,170,.18)'; ctx.setLineDash([3,4]); ctx.beginPath(); ctx.moveTo(PAD.l,y); ctx.lineTo(Wd-PAD.r,y); ctx.stroke(); ctx.setLineDash([]);
      ctx.textAlign='right'; ctx.textBaseline='middle'; ctx.fillText(cvFmtU(v,cfg.y_unit||''),PAD.l-5,y); }
    ctx.textAlign='center'; ctx.textBaseline='top';
    for(let t=0;t<=4;t++){ const v=minX+(maxX-minX)*t/4; ctx.fillText(cvFmtU(v,cfg.x_unit||''),sx(v),H-PAD.b+6); }
    ctx.globalAlpha=1;
    // etiquetas: los 8 puntos más extremos (lejos del centro) — legible, sin amontonar
    const cxm=(minX+maxX)/2, cym=(minY+maxY)/2;
    const clampX=v=>Math.max(minX,Math.min(maxX,v)), clampY=v=>Math.max(minY,Math.min(maxY,v));
    const order=data.map((d,i)=>[i,isOut(d)?9:Math.hypot((clampX(+d.x)-cxm)/(maxX-minX||1),(clampY(+d.y)-cym)/(maxY-minY||1))]).sort((a,b)=>b[1]-a[1]).map(a=>a[0]);
    const boxes=[], pts=[];
    data.forEach((d,i)=>{
      const out=isOut(d), x=sx(clampX(+d.x)), y=sy(clampY(+d.y)), r=isBubble?Math.max(4,Math.min(26,((+d.r||1)/maxR)*26)):4.5, col=d.color||cvCol(0);
      pts.push([x,y,Math.max(r,7),d]);
      ctx.beginPath(); ctx.arc(x,y,r,0,2*Math.PI);
      if(!out){ ctx.globalAlpha=.55; ctx.fillStyle=col; ctx.fill(); ctx.globalAlpha=1; }
      ctx.strokeStyle=col; ctx.lineWidth=out?2:1.3; ctx.stroke();
    });
    // etiquetas: extremos primero, sin solaparse (máx. 10)
    ctx.font='600 10px system-ui'; ctx.textBaseline='middle';
    let nlab=0;
    for(const i of order){
      if(nlab>=10) break;
      const d=data[i], out=isOut(d), x=sx(clampX(+d.x)), y=sy(clampY(+d.y));
      const txt=String(d.label||'').slice(0,16)+(out?' ('+cvFmtU(+d.x,cfg.x_unit||'')+', '+cvFmtU(+d.y,cfg.y_unit||'')+')':'');
      const w=ctx.measureText(txt).width, right=x>Wd-w-20, lx=right?x-7-w:x+7, box=[lx-2,y-7,lx+w+2,y+7];
      if(boxes.some(b=>!(box[2]<b[0]||box[0]>b[2]||box[3]<b[1]||box[1]>b[3]))) continue;
      boxes.push(box); nlab++;
      ctx.fillStyle=ink; ctx.textAlign='left'; ctx.fillText(txt,lx,y);
    }
    // tooltip del punto más cercano (radio de captura ≥ 7 px, más grande que la marca)
    cv.addEventListener('mousemove',e=>{
      const rc=cv.getBoundingClientRect(), mx=e.clientX-rc.left, my=e.clientY-rc.top;
      let best=null, bd=1e9; pts.forEach(p=>{ const dd=Math.hypot(p[0]-mx,p[1]-my); if(dd<=p[2]+4&&dd<bd){ bd=dd; best=p[3]; } });
      if(!best){ cvTip.hide(); cv.style.cursor=''; return; }
      cv.style.cursor='pointer';
      cvTip.show(`<div class="cv-tip-h">${cvEsc(best.label||'')}</div><div class="cv-tip-r"><span>${cvEsc(xl)}</span><b>${cvEsc(cvFmtU(+best.x,cfg.x_unit||''))}</b></div>`+
        `<div class="cv-tip-r"><span>${cvEsc(yl)}</span><b>${cvEsc(cvFmtU(+best.y,cfg.y_unit||''))}</b></div>`+
        (isBubble?`<div class="cv-tip-r"><span>${cvEsc(cfg.r_label||'r')}</span><b>${cvEsc(cvFmtU(+best.r,cfg.r_unit||''))}</b></div>`:''),e.clientX,e.clientY);
    });
    cv.addEventListener('mouseleave',()=>cvTip.hide());
  });
}

/* ── TABLE ── */
function _cvTable(el,spec){
  const data=(spec.data||[]).filter(r=>r&&typeof r==='object');
  const cols=(spec.config||{}).columns||Object.keys(data[0]||{});
  if(!data.length||!cols.length) return cvEmpty(el);
  const num=c=>data.every(r=>r[c]==null||r[c]==='—'||typeof r[c]==='number');
  el.innerHTML=`<div class="cv-scroll" style="max-height:340px;overflow-y:auto">
    <table class="cv-tbl"><thead><tr>${cols.map(c=>`<th${num(c)?' class="r"':''}>${cvEsc(c)}</th>`).join('')}</tr></thead>
      <tbody>${data.slice(0,15).map(row=>`<tr>${cols.map(c=>`<td${num(c)?' class="r"':''}>${cvEsc(typeof row[c]==='number'?cvFmtU(row[c],/fund|found|año|year/i.test(c)?'year':''):cvFmt(row[c]))}</td>`).join('')}</tr>`).join('')}</tbody>
    </table></div>`;
}

/* ── expose to global (used by inline onclick + Khipu command center) ── */
window._cvRenderCard = _cvRenderCard;   // permite a Khipu renderizar gráficos inline

})();
