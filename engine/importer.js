/* engine/importer.js — EXPANSION_5K E2.7 · 🩺 Sistema → Diagnóstico → «📥 Importar empresas».
   Panel de la tubería de importación (ontology/company_import.py, rutas /api/ontology/import/*):
     · lista los PAQUETES del repositorio (GET /import/packages: «Lote 2 — 386 empresas completas»);
     · «Ver plan» SIN PIN (GET /import/packages/plan: lectura pura) en palabras simples: se crean / se fusionan /
       vínculos vivos · propuestos · pendientes / categorías / ¿qué cambia? (ρ y TSMC antes → después) / avisos;
     · «Aplicar» = confirmación + copia de seguridad + nombre EXACTO de la base + PIN (window._tradeFetch) y manda
       expect.plan_sha (la huella del plan que la persona vio); el servidor recalcula y, si cambió → 409 explicado;
     · «Deshacer» la corrida más nueva (POST /import/rollback con PIN); «Subir un archivo propio» (trozos con PIN).
   Reglas: bilingüe ES/EN (T.es / T.en con las MISMAS claves), tokens --os-* de Khipus OS, «?» en cada cifra nueva
   (engine/explain.js), DOM seguro (textContent; nunca HTML armado con datos), diálogos SOLO por KhipuToast (nunca
   window.confirm/prompt), PIN SOLO por window._tradeFetch. Se carga PEREZOSO desde engine/app_main.js al abrir 🩺.
   API: window.KhipuImporter.mount(parentId) · .reload() · ._T (diccionario) y ._sha256 (huella en JS puro), para las pruebas. */
(function () {
  'use strict';
  var W = window;
  if (W.KhipuImporter && W.KhipuImporter.__v) return;

  function base() { return (typeof W.BASE !== 'undefined' && W.BASE) ? W.BASE : ''; }
  function en() {
    try { return String(W.LANG || W.localStorage.getItem('eco_lang') || 'es').slice(0, 2) === 'en'; }
    catch (e) { return false; }
  }

  /* ══ textos ES/EN (mismas claves en los dos; {x} = valor) ══ */
  var T = {
    es: {
      title: 'Importar empresas', what: '¿Qué es esto?', loading: 'Cargando…',
      sub: 'Paquetes de empresas investigadas, listos para entrar al grafo. Ver el plan no cambia nada; aplicar pide tu PIN.',
      no_db: 'Sin base de datos (DATABASE_URL): no hay dónde importar.',
      no_pkgs: 'No hay paquetes en el servidor todavía (data/import/lotes/<fecha>/bundle_*.json.gz).',
      st_applied: 'aplicado', st_new: 'sin aplicar', st_undone: 'deshecho',
      pkg_meta: '{date} · {links} vínculos investigados',
      pkg_excluded: '{n} fichas no entran (incompletas)', pkg_broken: 'Paquete que no se pudo leer: {name} ({err})',
      see_plan: 'Ver plan', hide_plan: 'Ocultar plan', apply: 'Aplicar…', retry: 'Reintentar',
      plan_loading: 'Calculando el plan sobre el grafo de hoy… (no cambia nada)',
      sec_enter: 'Qué entra', sec_change: '¿Qué cambia en el grafo?', sec_merge: 'Se fusionan con una que ya existe',
      sec_review: 'Para revisar', sec_why: '¿Por qué no todos los vínculos quedan vivos?', sec_types: 'Vínculos por tipo',
      sec_fix: 'Reparado solo el FORMATO', sec_runs: 'Corridas', sec_upload: '¿Tienes otro archivo?',
      k_create: 'Se crean', k_merge: 'Se fusionan', k_live: 'Vínculos vivos', k_proposed: 'Propuestos',
      k_pending: 'Pendientes', k_cats: 'Categorías por aprobar', k_events: 'Eventos', k_skip: 'Se omiten',
      k_invalid: 'Fichas inválidas', k_update: 'Se actualizan', route_live: 'vivos', route_proposed: 'propuestos', route_pending: 'pendientes',
      ch_nodes: 'Puntos del grafo (empresas y factores): {a} → {b}', ch_links: 'Vínculos nuevos que mueven números: +{n}',
      ch_rho: 'Fuerza de contagio (ρ): {a} → {b}', ch_tsmc: 'Si TSMC falla, golpea a: {a} → {b} empresas',
      ch_top: 'Top-20 cuellos de botella: entran {in} · salen {out}', ch_none: 'ninguno', ch_same: 'El grafo no cambia: no entran vínculos vivos.',
      ch_na: '«¿Qué cambia?» no disponible: {r}', ch_stale: 'Después de importar, la cifra en DINERO de los escenarios puede salir sin monto hasta que se recalibre (lo hace Claude con un script; tú no tienes que hacer nada). Los porcentajes de impacto sí salen.',
      merge_row: '{name} → {id} ({how})', review_dup: '¿Duplicada? {name} se parece a {other} (puntaje {score}): se crea aparte; si es la misma, fusionar después.',
      review_sub: '{name}: NO se fusiona con {other} (la ficha la nombra como otra empresa).',
      review_hint: '{name}: la pista apunta a {other}; manda el identificador fuerte.', review_other: '{name}: {kind} ({other})',
      warn_line: 'Avisos: {list}', conf_line: 'Conflictos: {list}',
      fix_line: '{rep} datos reparados en {rec} fichas · {drop} quitados (sin inventar) · {rej} fichas rechazadas',
      fix_none: 'No hizo falta reparar nada.', excl_line: '{n} fichas de la entrega NO entran (no están completas).',
      fp_label: 'Huella del plan:', fp_graph: 'grafo versión {gv}', fp_snap: 'catálogo (sin versión)',
      invalid_line: '{rid}: {msg}', cats_line: '{id} ({n} empresas)',
      runs_none: 'Todavía no hay corridas.', run_row: '{date} · {batch} · {n} empresas nuevas',
      run_undone: 'deshecha', run_applied: 'aplicada', undo: 'Deshacer', pending_links: 'Vínculos esperando a su otra empresa: {n}',
      upload_btn: 'Subir archivo (.json, .jsonl, .gz)…', upload_hint: 'Fichas khipus.company/1. Subir y ver su plan pide tu PIN; el formato se repara solo (nunca los números).',
      up_reading: 'Leyendo el archivo…', up_sending: 'Subiendo… trozo {i} de {n}', up_done: 'Archivo subido: {name} ({n} fichas).',
      up_too_big: 'El archivo es demasiado grande (máximo 64 MB sin comprimir).', up_no_gz: 'Este navegador no puede abrir .gz: descomprímelo primero.',
      file_title: 'Archivo {name}',
      apply_q: '¿Importar «{title}»?', apply_sub: 'Esto escribe en la base de datos real del grafo.',
      apply_note: 'Todo entra como eventos nuevos en UNA decisión del libro, con tu PIN. Nada se borra y se puede deshacer.',
      backup_check: 'Hice una copia de seguridad de la base (Railway → Postgres → Backups → Create backup).',
      apply_go: 'Aplicar', db_title: 'Nombre exacto de la base de datos',
      db_body: 'Es un seguro para no escribir en la base equivocada. Lo encuentras en Railway → tu servicio Postgres → pestaña Variables → PGDATABASE (casi siempre «railway»). Si no coincide, no se cambia nada.',
      db_label: 'Nombre de la base', db_needed: 'Hace falta el nombre de la base: no se cambió nada.',
      db_retry_body: 'El servidor dice que esta base se llama «{name}». Si es la que quieres cambiar, acepta para seguir.',
      no_dialog: 'Falta el diálogo de confirmación de Khipus (engine/toast.js): no se hizo nada.',
      prog_apply: 'Aplicando en el servidor…', prog_undo: 'Deshaciendo en el servidor…', prog_upload: 'Subiendo el archivo…',
      prog_note: 'Recalcula el plan, escribe todo en UNA transacción y reconstruye las vistas. Suele tardar entre 10 y 60 s: no cierres esta ventana.',
      prog_secs: '{s} s',
      ok_apply: 'Importado.', ok_apply_detail: '{created} empresas nuevas · {merged} completadas · {links} vínculos escritos · {events} eventos · {secs} s',
      id_run: 'Corrida', id_dec: 'decisión', ok_undo_hint: 'Para deshacer: botón «Deshacer» en Corridas.',
      reload_hint: 'Recarga la página (F5) para ver el cambio en el mapa y en la búsqueda.', reload_btn: '↻ Recargar',
      dw_line: 'Vivos con un peso POR DEFECTO (no investigado): dueño {owns} (peso 3-5 según el % declarado) · socio o inversor {nonflow} (peso 1)',
      undo_q: '¿Deshacer la corrida {run}?', undo_note: 'Se revierte con eventos NUEVOS: las empresas creadas quedan retiradas y los vínculos retractados. La historia queda.',
      undo_go: 'Deshacer', ok_undo: 'Deshecho.', ok_undo_detail: '{links} vínculos retractados · {retired} empresas retiradas · {restored} empresas vuelven a como estaban',
      e_plan_changed: 'El plan cambió desde que lo miraste (otra huella). Lo volvimos a calcular: revísalo y vuelve a aplicar.',
      e_graph_changed: 'El grafo cambió mientras tanto (otra escritura). Vuelve a ver el plan antes de aplicar.',
      e_graph_stale: 'La vista del grafo todavía se está poniendo al día. Espera unos segundos y reintenta.',
      e_busy: 'Ya hay otra importación o reconciliación en curso. Espera un minuto y reintenta.',
      e_confirm_db: 'El nombre de la base no coincide: no se cambió nada.',
      e_pin: 'Hace falta el PIN de operador (TRADE_PIN de Railway): no se cambió nada.',
      e_ledger: 'No se pudo registrar la decisión en el libro: NO se aplicó nada. Reintenta en un momento.',
      e_gate: 'Una regla de calidad (puerta) frenó la importación: no se aplicó nada.',
      e_pkg: 'Ese paquete ya no está en el servidor (¿se desplegó otra versión?). Actualiza la lista.',
      e_rate: 'Demasiados intentos seguidos. Espera unos minutos.',
      e_later: 'Primero hay que deshacer las corridas más nuevas (de la más nueva a la más vieja).',
      e_already: 'Esa corrida ya estaba deshecha.', e_graph_na: 'El grafo no está disponible en el servidor ahora mismo.',
      e_network: 'No llegó la respuesta del servidor. Puede que SÍ se haya hecho: mira «Corridas» antes de reintentar.',
      e_generic: 'El servidor no pudo hacerlo.', e_server_says: 'El servidor dice: {m}',
      x_panel_t: '¿Qué es «Importar empresas»?',
      x_panel_b: 'Aquí entran al grafo empresas nuevas que ya fueron investigadas (cada una con su ficha y sus fuentes).<br><br>' +
        '1) <b>Ver plan</b> no cambia nada: dice qué empresas se crean, cuáles ya existían (se completan) y cómo cambia el riesgo.<br>' +
        '2) <b>Aplicar</b> pide tu PIN y el nombre exacto de la base. Todo queda en el libro de decisiones con tu nombre.<br>' +
        '3) <b>Deshacer</b> revierte con eventos nuevos: nada se borra.',
      x_links_t: 'Vínculos vivos, propuestos y pendientes',
      x_links_b: '<b>Vivos</b>: relaciones con buena fuente; desde ya mueven los números (riesgo, simulaciones).<br>' +
        '<b>Propuestos</b>: fuente débil o rumor; quedan guardados pero NO mueven números hasta que una persona los confirme.<br>' +
        '<b>Pendientes</b>: la otra empresa aún no está en Khipus; se conectan cuando llegue su ficha, con las MISMAS reglas (vivo o propuesto).<br>' +
        '<b>Fusionar</b>: la empresa ya existía; se completa sin pisar lo curado (país, categoría, textos…).',
      x_change_t: '¿Qué cambia en el grafo?',
      x_change_b: 'Antes de escribir, Khipus corre el MISMO motor de contagio sobre una copia del grafo con las empresas nuevas.<br><br>' +
        '<b>ρ (fuerza de contagio)</b>: cuánto se amplifica un golpe al recorrer la cadena; más alto = los golpes se propagan más.<br>' +
        '<b>TSMC golpea a</b>: cuántas empresas sufrirían al menos un 1 % si TSMC fallara.<br>' +
        '<b>Top-20</b>: las empresas cuyo fallo dañaría a más empresas (cuellos de botella).',
      x_fp_t: '¿Qué es la huella del plan?',
      x_fp_b: 'Un código único de EXACTAMENTE lo que viste. Al aplicar se manda esa huella: si el plan cambió (otro grafo, otro archivo), el servidor no aplica nada y te pide volver a mirarlo.',
      x_dw_t: '¿Qué es un peso por defecto?',
      x_dw_b: 'Cada vínculo tiene un peso (1 a 6): cuánto depende una empresa de la otra. Casi siempre lo da la investigación. Cuando la ficha no lo trae, Khipus usa una tabla fija y pública (policy.import): un dueño pesa 3, 4 o 5 según el % que declara la ficha; un socio o inversor pesa 1.<br><br>' +
        'Se marcan (criticality_source) y se pueden corregir después; un dueño sin % de control nunca entra vivo.',
      x_cal_t: '¿Por qué la cifra en dinero puede salir sin monto?',
      x_cal_b: 'Los escenarios («¿qué pasa si TSMC falla?») dan primero un % de impacto y, aparte, una cifra en dinero para tu cartera. Esa cifra usa una calibración medida con el grafo de ANTES.<br><br>' +
        'Cuando entran vínculos nuevos, la calibración queda vieja: mientras tanto Khipus prefiere no mostrar el monto antes que mostrar uno equivocado. Claude la vuelve a medir con un script; tú no tienes que hacer nada.',
      x_fix_t: '¿Qué se reparó?',
      x_fix_b: 'Solo el FORMATO: enlaces con espacios, años escritos como texto, tickers con espacio, datos que salen de otro dato de la misma ficha. Ningún número se cambia y nada se inventa: lo que no se pudo reparar se quitó (solo ese dato) y queda en el registro sanitize_log.json.',
      rel_supply: 'provee', rel_fab: 'fabrica', rel_cloud: 'nube', rel_license: 'licencia', rel_ppa: 'energía (PPA)',
      rel_deploy: 'despliega', rel_owns: 'es dueño', rel_invest: 'invierte', rel_partner: 'socio',
      how_yahoo_symbol: 'mismo símbolo de Yahoo', how_khipus_id: 'id que dio la investigación', how_hint: 'id que dio la investigación',
      how_lei: 'mismo LEI', how_isin: 'mismo ISIN', how_cik: 'mismo CIK', how_qid: 'mismo Wikidata', how_figi: 'mismo FIGI',
      how_ticker_mic: 'mismo ticker y bolsa', how_name: 'mismo nombre', how_other: 'identificador',
      cf_curated_differs: 'dato curado distinto (no se pisa)', cf_possible_duplicate: '¿duplicada?', cf_value_differs: 'valor distinto (no se pisa)',
      cf_name_target_is_counterparty: 'el nombre apuntaba a su filial', cf_listing_differs: 'cotización distinta a la curada',
      cf_hint_mismatch: 'la pista apunta a otra empresa', cf_hint_contradicted: 'la pista choca con cotización o sede',
      cf_name_differs_from_hint: 'el nombre apuntaba a otra', cf_id_differs: 'identificador distinto (no se pisa)',
      w_confidence_defaulted: 'datos de ESG/línea de tiempo sin confianza (se usa 0,4, marcada)',
      w_listing_added_secondary: 'cotización que entra como secundaria', w_primary_is_depositary: 'la principal era un certificado (ADR/GDR)',
      w_fiscal_year_label_start: 'año fiscal rotulado con el año en que EMPIEZA (no se cambia)',
      r_counterparty_unknown: 'la otra empresa aún no está en Khipus', r_pending: 'participación con una empresa que aún no está',
      r_source_trust_low: 'fuente de poca confianza (prensa o agregador)', r_proposed: 'participación con fuente débil',
      r_owns_without_control_pct: 'dueño sin % de control declarado', r_holding_without_pct: 'participación sin %',
      r_low_confidence: 'confianza baja', r_status_rumored: 'es un rumor', r_status_disputed: 'está en disputa',
      r_counterparty_by_name_only: 'la otra empresa se encontró solo por nombre', r_self_link: 'apunta a sí misma',
      r_flow_supplier_type: 'un país o una política no puede ser proveedor',
    },
    en: {
      title: 'Import companies', what: 'What is this?', loading: 'Loading…',
      sub: 'Packages of researched companies, ready to enter the graph. Viewing the plan changes nothing; applying asks for your PIN.',
      no_db: 'No database (DATABASE_URL): nowhere to import.',
      no_pkgs: 'No packages on the server yet (data/import/lotes/<date>/bundle_*.json.gz).',
      st_applied: 'applied', st_new: 'not applied', st_undone: 'undone',
      pkg_meta: '{date} · {links} researched links',
      pkg_excluded: '{n} records do not enter (incomplete)', pkg_broken: 'Package that could not be read: {name} ({err})',
      see_plan: 'See plan', hide_plan: 'Hide plan', apply: 'Apply…', retry: 'Retry',
      plan_loading: 'Computing the plan on today\'s graph… (changes nothing)',
      sec_enter: 'What enters', sec_change: 'What changes in the graph?', sec_merge: 'Merged into one that already exists',
      sec_review: 'To review', sec_why: 'Why are not all links live?', sec_types: 'Links by type',
      sec_fix: 'Only the FORMAT was repaired', sec_runs: 'Runs', sec_upload: 'Have another file?',
      k_create: 'Created', k_merge: 'Merged', k_live: 'Live links', k_proposed: 'Proposed',
      k_pending: 'Pending', k_cats: 'Categories to approve', k_events: 'Events', k_skip: 'Skipped',
      k_invalid: 'Invalid records', k_update: 'Updated', route_live: 'live', route_proposed: 'proposed', route_pending: 'pending',
      ch_nodes: 'Graph nodes (companies and factors): {a} → {b}', ch_links: 'New links that move numbers: +{n}',
      ch_rho: 'Contagion strength (ρ): {a} → {b}', ch_tsmc: 'If TSMC fails, it hits: {a} → {b} companies',
      ch_top: 'Top-20 chokepoints: in {in} · out {out}', ch_none: 'none', ch_same: 'The graph does not change: no live links enter.',
      ch_na: '"What changes?" unavailable: {r}', ch_stale: 'After importing, the MONEY figure of scenarios may show no amount until it is recalibrated (Claude does it with a script; you do not need to do anything). Impact percentages still show.',
      merge_row: '{name} → {id} ({how})', review_dup: 'Duplicate? {name} looks like {other} (score {score}): created separately; if it is the same, merge later.',
      review_sub: '{name}: NOT merged into {other} (the record names it as another company).',
      review_hint: '{name}: the hint points to {other}; the strong identifier wins.', review_other: '{name}: {kind} ({other})',
      warn_line: 'Warnings: {list}', conf_line: 'Conflicts: {list}',
      fix_line: '{rep} values repaired in {rec} records · {drop} dropped (nothing invented) · {rej} records rejected',
      fix_none: 'Nothing needed repairing.', excl_line: '{n} records of the delivery do NOT enter (not complete).',
      fp_label: 'Plan fingerprint:', fp_graph: 'graph version {gv}', fp_snap: 'catalog (no version)',
      invalid_line: '{rid}: {msg}', cats_line: '{id} ({n} companies)',
      runs_none: 'No runs yet.', run_row: '{date} · {batch} · {n} new companies',
      run_undone: 'undone', run_applied: 'applied', undo: 'Undo', pending_links: 'Links waiting for their other company: {n}',
      upload_btn: 'Upload file (.json, .jsonl, .gz)…', upload_hint: 'khipus.company/1 records. Uploading and seeing its plan asks for your PIN; the format is repaired automatically (never the numbers).',
      up_reading: 'Reading the file…', up_sending: 'Uploading… chunk {i} of {n}', up_done: 'File uploaded: {name} ({n} records).',
      up_too_big: 'The file is too large (64 MB maximum uncompressed).', up_no_gz: 'This browser cannot open .gz: decompress it first.',
      file_title: 'File {name}',
      apply_q: 'Import "{title}"?', apply_sub: 'This writes to the real graph database.',
      apply_note: 'Everything enters as new events in ONE ledger decision, with your PIN. Nothing is deleted and it can be undone.',
      backup_check: 'I made a database backup (Railway → Postgres → Backups → Create backup).',
      apply_go: 'Apply', db_title: 'Exact database name',
      db_body: 'A safety check so the wrong database is never written. Find it in Railway → your Postgres service → Variables tab → PGDATABASE (almost always "railway"). If it does not match, nothing changes.',
      db_label: 'Database name', db_needed: 'The database name is needed: nothing was changed.',
      db_retry_body: 'The server says this database is called "{name}". If it is the one you want to change, accept to continue.',
      no_dialog: 'The Khipus confirmation dialog (engine/toast.js) is missing: nothing was done.',
      prog_apply: 'Applying on the server…', prog_undo: 'Undoing on the server…', prog_upload: 'Uploading the file…',
      prog_note: 'It recomputes the plan, writes everything in ONE transaction and rebuilds the views. It usually takes 10 to 60 s: do not close this window.',
      prog_secs: '{s} s',
      ok_apply: 'Imported.', ok_apply_detail: '{created} new companies · {merged} completed · {links} links written · {events} events · {secs} s',
      id_run: 'Run', id_dec: 'decision', ok_undo_hint: 'To undo: the "Undo" button in Runs.',
      reload_hint: 'Reload the page (F5) to see the change on the map and in search.', reload_btn: '↻ Reload',
      dw_line: 'Live with a DEFAULT weight (not researched): owner {owns} (weight 3-5 by the declared %) · partner or investor {nonflow} (weight 1)',
      undo_q: 'Undo run {run}?', undo_note: 'It is reverted with NEW events: created companies are retired and links retracted. The history stays.',
      undo_go: 'Undo', ok_undo: 'Undone.', ok_undo_detail: '{links} links retracted · {retired} companies retired · {restored} companies back to how they were',
      e_plan_changed: 'The plan changed since you looked at it (different fingerprint). It was recomputed: review it and apply again.',
      e_graph_changed: 'The graph changed meanwhile (another write). Review the plan again before applying.',
      e_graph_stale: 'The graph view is still catching up. Wait a few seconds and retry.',
      e_busy: 'Another import or reconciliation is running. Wait a minute and retry.',
      e_confirm_db: 'The database name does not match: nothing was changed.',
      e_pin: 'The operator PIN (Railway TRADE_PIN) is needed: nothing was changed.',
      e_ledger: 'The decision could not be recorded in the ledger: NOTHING was applied. Retry shortly.',
      e_gate: 'A quality rule (gate) stopped the import: nothing was applied.',
      e_pkg: 'That package is no longer on the server (was another version deployed?). Refresh the list.',
      e_rate: 'Too many attempts in a row. Wait a few minutes.',
      e_later: 'The newer runs must be undone first (newest to oldest).',
      e_already: 'That run was already undone.', e_graph_na: 'The graph is not available on the server right now.',
      e_network: 'No answer from the server. It MAY have been done: check "Runs" before retrying.',
      e_generic: 'The server could not do it.', e_server_says: 'The server says: {m}',
      x_panel_t: 'What is "Import companies"?',
      x_panel_b: 'This is where new, already researched companies enter the graph (each with its record and sources).<br><br>' +
        '1) <b>See plan</b> changes nothing: it says which companies are created, which already existed (they are completed) and how risk changes.<br>' +
        '2) <b>Apply</b> asks for your PIN and the exact database name. Everything goes into the decision ledger under your name.<br>' +
        '3) <b>Undo</b> reverts with new events: nothing is deleted.',
      x_links_t: 'Live, proposed and pending links',
      x_links_b: '<b>Live</b>: relationships with a good source; they move the numbers right away (risk, simulations).<br>' +
        '<b>Proposed</b>: weak source or rumor; stored but they do NOT move numbers until a person confirms them.<br>' +
        '<b>Pending</b>: the other company is not in Khipus yet; they connect when its record arrives, with the SAME rules (live or proposed).<br>' +
        '<b>Merge</b>: the company already existed; it is completed without overwriting curated data (country, category, texts…).',
      x_change_t: 'What changes in the graph?',
      x_change_b: 'Before writing, Khipus runs the SAME contagion engine on a copy of the graph with the new companies.<br><br>' +
        '<b>ρ (contagion strength)</b>: how much a shock is amplified along the chain; higher = shocks spread further.<br>' +
        '<b>TSMC hits</b>: how many companies would suffer at least 1 % if TSMC failed.<br>' +
        '<b>Top-20</b>: the companies whose failure would hurt the most companies (chokepoints).',
      x_fp_t: 'What is the plan fingerprint?',
      x_fp_b: 'A unique code of EXACTLY what you saw. Applying sends that fingerprint: if the plan changed (another graph, another file), the server applies nothing and asks you to review it again.',
      x_dw_t: 'What is a default weight?',
      x_dw_b: 'Each link has a weight (1 to 6): how much one company depends on the other. The research almost always gives it. When the record does not, Khipus uses a fixed, public table (policy.import): an owner weighs 3, 4 or 5 by the % the record declares; a partner or investor weighs 1.<br><br>' +
        'They are flagged (criticality_source) and can be corrected later; an owner without a control % never enters live.',
      x_cal_t: 'Why may the money figure show no amount?',
      x_cal_b: 'Scenarios ("what if TSMC fails?") first give an impact % and, separately, a money figure for your portfolio. That figure uses a calibration measured on the graph from BEFORE.<br><br>' +
        'When new links enter, the calibration becomes stale: meanwhile Khipus prefers to show no amount rather than a wrong one. Claude measures it again with a script; you do not need to do anything.',
      x_fix_t: 'What was repaired?',
      x_fix_b: 'Only the FORMAT: links with spaces, years written as text, tickers with a space, values that follow from another value of the same record. No number is changed and nothing is invented: what could not be repaired was dropped (only that value) and is kept in sanitize_log.json.',
      rel_supply: 'supplies', rel_fab: 'manufactures', rel_cloud: 'cloud', rel_license: 'license', rel_ppa: 'power (PPA)',
      rel_deploy: 'deploys', rel_owns: 'owns', rel_invest: 'invests', rel_partner: 'partner',
      how_yahoo_symbol: 'same Yahoo symbol', how_khipus_id: 'id given by the research', how_hint: 'id given by the research',
      how_lei: 'same LEI', how_isin: 'same ISIN', how_cik: 'same CIK', how_qid: 'same Wikidata', how_figi: 'same FIGI',
      how_ticker_mic: 'same ticker and exchange', how_name: 'same name', how_other: 'identifier',
      cf_curated_differs: 'curated value differs (not overwritten)', cf_possible_duplicate: 'duplicate?', cf_value_differs: 'value differs (not overwritten)',
      cf_name_target_is_counterparty: 'the name pointed to its subsidiary', cf_listing_differs: 'listing differs from the curated one',
      cf_hint_mismatch: 'the hint points to another company', cf_hint_contradicted: 'the hint clashes with listing or HQ',
      cf_name_differs_from_hint: 'the name pointed to another one', cf_id_differs: 'identifier differs (not overwritten)',
      w_confidence_defaulted: 'ESG/timeline facts without confidence (0.4 used, flagged)',
      w_listing_added_secondary: 'listing that enters as secondary', w_primary_is_depositary: 'the primary was a certificate (ADR/GDR)',
      w_fiscal_year_label_start: 'fiscal year labelled with the year it STARTS (not changed)',
      r_counterparty_unknown: 'the other company is not in Khipus yet', r_pending: 'holding with a company that is not there yet',
      r_source_trust_low: 'low-trust source (press or aggregator)', r_proposed: 'holding with a weak source',
      r_owns_without_control_pct: 'owner without a declared control %', r_holding_without_pct: 'holding without %',
      r_low_confidence: 'low confidence', r_status_rumored: 'it is a rumor', r_status_disputed: 'it is disputed',
      r_counterparty_by_name_only: 'the other company was found by name only', r_self_link: 'points to itself',
      r_flow_supplier_type: 'a country or a policy cannot be a supplier',
    },
  };
  function t(k, v) {
    var d = T[en() ? 'en' : 'es'];
    var s = d[k] != null ? d[k] : (T.es[k] != null ? T.es[k] : k);
    if (v) s = s.replace(/\{(\w+)\}/g, function (m, x) { return v[x] != null ? String(v[x]) : m; });
    return s;
  }
  function tc(prefix, code) { var k = prefix + code; return T.es[k] != null ? t(k) : String(code); }

  if (W.explainRegister) {
    [['import_panel', 'x_panel'], ['import_links', 'x_links'], ['import_change', 'x_change'],
      ['import_fingerprint', 'x_fp'], ['import_sanitize', 'x_fix'], ['import_calibration', 'x_cal'], ['import_default_weight', 'x_dw']].forEach(function (p) {
      W.explainRegister(p[0], { es: { t: T.es[p[1] + '_t'], b: T.es[p[1] + '_b'] }, en: { t: T.en[p[1] + '_t'], b: T.en[p[1] + '_b'] } });
    });
  }

  /* ══ números (es: 1.234 · 1,21 / en: 1,234 · 1.21) ══ */
  function fmtInt(n) {
    n = Math.round(+n);
    if (!isFinite(n)) return '—';
    var s = String(Math.abs(n)).replace(/\B(?=(\d{3})+(?!\d))/g, en() ? ',' : '.');
    return (n < 0 ? '−' : '') + s;
  }
  function fmtDec(x, d) {
    if (x == null || x === '' || !isFinite(+x)) return '—';
    var s = (+x).toFixed(d);
    return en() ? s : s.replace('.', ',');
  }
  function fmtWhen(iso) {
    var s = String(iso || '');
    return s ? s.slice(0, 16).replace('T', ' ') + ' UTC' : '—';
  }

  /* ══ DOM seguro: todo dato va como TEXTO ══ */
  function add(el, kids) {
    if (kids == null || kids === false) return el;
    if (!Array.isArray(kids)) kids = [kids];
    kids.forEach(function (c) {
      if (c == null || c === false || c === '') return;
      el.appendChild(typeof c === 'object' ? c : document.createTextNode(String(c)));
    });
    return el;
  }
  function h(tag, a, kids) {
    var el = document.createElement(tag);
    if (a) Object.keys(a).forEach(function (k) {
      var v = a[k];
      if (v == null || v === false) return;
      if (k === 'class') el.className = v;
      else if (k.slice(0, 2) === 'on' && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : String(v));
    });
    return add(el, kids);
  }
  function clear(el) { while (el && el.firstChild) el.removeChild(el.firstChild); }
  function q(key) {          // el «?» (engine/explain.js) como BOTÓN: teclado y lector de pantalla
    return h('button', { type: 'button', class: 'kim-q', title: t('what'), 'aria-label': t('what'),
      onclick: function (e) { e.stopPropagation(); if (W.explainMetric) W.explainMetric(key); } }, '?');
  }
  function btn(label, onclick, cls, extra) {
    var a = { type: 'button', class: 'kim-btn' + (cls ? ' ' + cls : ''), onclick: onclick };
    if (extra) Object.keys(extra).forEach(function (k) { a[k] = extra[k]; });
    return h('button', a, label);
  }
  function code(x) { return h('code', null, x); }

  /* ══ estilos (tokens --os-* de Khipus OS; el valor tras la coma = respaldo oscuro) ══ */
  function ensureStyles() {
    if (document.getElementById('kim-styles')) return;
    var st = document.createElement('style'); st.id = 'kim-styles';
    st.textContent =
      '.kim-root{color:var(--os-ink,#F2F2F5);font-family:var(--os-font,\'Nunito\',\'Geist\',system-ui,-apple-system,\'Segoe UI\',sans-serif);-webkit-font-smoothing:antialiased}' +
      '.kim-root *{box-sizing:border-box}.kim-root button{font-family:inherit}' +
      '.kim-root .kim-card{border-radius:var(--os-r,18px);padding:14px 16px;margin:6px 0 12px;background:var(--os-surface,#17181F);' +
        'box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35));min-width:0}' +
      '.kim-root .kim-hd{display:flex;align-items:center;gap:8px;margin-bottom:4px}' +
      '.kim-root .kim-hd b{font-size:14px;font-weight:800;letter-spacing:-.005em;flex:1;min-width:0}' +
      '.kim-root .kim-ic{width:28px;height:28px;flex:none;border-radius:9px;display:inline-flex;align-items:center;justify-content:center;font-size:14px;' +
        'background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-accent,#4C8DF6) 13%,transparent)}' +
      '.kim-root .kim-in{padding-left:36px}' +
      '.kim-root .kim-mut{font-size:12px;color:var(--os-ink-2,#A6A8B5);line-height:1.5;margin:2px 0 6px;overflow-wrap:anywhere}' +
      '.kim-root code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:11.5px;padding:1px 6px;border-radius:6px;' +
        'background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5);overflow-wrap:anywhere}' +
      '.kim-root .kim-pkg{border-radius:var(--os-r-sm,12px);background:var(--os-surface-2,#1F2029);padding:10px 12px;margin:8px 0}' +
      '.kim-root .kim-pkg-hd{display:flex;align-items:center;gap:8px;flex-wrap:wrap}' +
      '.kim-root .kim-pkg-hd b{font-size:13px;font-weight:800;flex:1;min-width:160px}' +
      '.kim-root .kim-chip{display:inline-flex;align-items:center;font-size:10.5px;font-weight:800;border-radius:999px;padding:2px 9px;white-space:nowrap;' +
        'background:var(--os-surface-3,#2A2B36);color:var(--os-ink-2,#A6A8B5)}' +
      '.kim-root .kim-chip.ok{color:var(--os-good-ink,#2fbf5b);background:color-mix(in srgb,var(--os-good,#2fbf5b) 14%,transparent)}' +
      '.kim-root .kim-chip.warn{color:var(--os-warn-ink,#F2C46D);background:color-mix(in srgb,var(--os-warn,#F2C46D) 16%,transparent)}' +
      '.kim-root .kim-tiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:8px 0}' +
      '.kim-root .kim-tile{border-radius:12px;background:var(--os-surface,#17181F);padding:8px 10px;min-width:0}' +
      '.kim-root .kim-tile .n{display:block;font-size:19px;font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-.01em;line-height:1.2}' +
      '.kim-root .kim-tile .l{display:block;font-size:11px;color:var(--os-ink-2,#A6A8B5);line-height:1.3;overflow-wrap:anywhere}' +
      '.kim-root .kim-sec{margin:10px 0 4px;font-size:12px;font-weight:800;display:flex;align-items:center;gap:4px}' +
      '.kim-root ul.kim-ul{margin:4px 0 6px;padding-left:18px;font-size:12px;line-height:1.55}' +
      '.kim-root ul.kim-ul li{overflow-wrap:anywhere}' +
      '.kim-root details{margin:6px 0;font-size:12px}.kim-root summary{cursor:pointer;font-weight:700;padding:3px 0}' +
      '.kim-root summary:focus-visible{outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px;border-radius:6px}' +
      '.kim-root .kim-acts{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;align-items:center}' +
      '.kim-root .kim-btn{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px;min-height:34px;' +
        'padding:0 14px;border-radius:999px;background:var(--os-surface-3,#2A2B36);color:var(--os-ink,#F2F2F5);font-size:12.5px;font-weight:700;white-space:nowrap;' +
        'transition:opacity .15s,background-color .15s,transform .1s}' +
      '.kim-root .kim-btn:hover:not([disabled]){opacity:.88}.kim-root .kim-btn:active{transform:scale(.98)}' +
      '.kim-root .kim-btn.pri{background:var(--os-btn,#F2F2F5);color:var(--os-btn-ink,#111216)}' +
      '.kim-root .kim-btn.bad{color:var(--os-bad-ink,#F47C7C)}' +
      '.kim-root .kim-btn[disabled]{opacity:.45;cursor:default;transform:none}' +
      '.kim-root .kim-btn:focus-visible,.kim-root .kim-q:focus-visible{outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px}' +
      '.kim-root .kim-q{appearance:none;border:1px solid color-mix(in srgb,var(--os-accent,#4C8DF6) 45%,transparent);background:none;color:var(--os-accent,#4C8DF6);' +
        'width:18px;height:18px;min-width:18px;border-radius:50%;font-size:10.5px;font-weight:800;line-height:1;padding:0;cursor:pointer;margin-left:4px;vertical-align:middle}' +
      '.kim-root .kim-line{font-size:12.5px;line-height:1.55;margin:2px 0;overflow-wrap:anywhere}' +
      '.kim-root .kim-warn{color:var(--os-warn-ink,#F2C46D)}.kim-root .kim-good{color:var(--os-good-ink,#2fbf5b)}.kim-root .kim-bad{color:var(--os-bad-ink,#F47C7C)}' +
      '.kim-root .kim-msg{border-radius:12px;padding:10px 12px;margin-top:10px;font-size:12.5px;line-height:1.5;background:var(--os-surface-2,#1F2029);overflow-wrap:anywhere}' +
      '.kim-root .kim-msg.ok{box-shadow:inset 3px 0 0 var(--os-good-ink,#2fbf5b)}.kim-root .kim-msg.err{box-shadow:inset 3px 0 0 var(--os-bad-ink,#F47C7C)}' +
      '.kim-root .kim-msg.warn{box-shadow:inset 3px 0 0 var(--os-warn-ink,#F2C46D)}' +
      '.kim-root .kim-bar{height:4px;border-radius:2px;background:var(--os-surface-3,#2A2B36);overflow:hidden;margin:8px 0 4px}' +
      '.kim-root .kim-bar>i{display:block;height:100%;width:35%;border-radius:2px;background:var(--os-accent,#4C8DF6);animation:kim-slide 1.3s ease-in-out infinite}' +
      '@keyframes kim-slide{0%{transform:translateX(-100%)}100%{transform:translateX(300%)}}' +
      '.kim-root .kim-run{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:6px 0;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07));font-size:12px}' +
      '.kim-root .kim-run:last-child{border-bottom:0}.kim-root .kim-run span.t{flex:1;min-width:180px;overflow-wrap:anywhere}' +
      '@media(prefers-reduced-motion:reduce){.kim-root .kim-btn{transition:none}.kim-root .kim-bar>i{animation:none;width:100%;opacity:.55}}' +
      '@media(max-width:480px){.kim-root .kim-in{padding-left:0}.kim-root .kim-tiles{grid-template-columns:repeat(2,minmax(0,1fr))}.kim-root .kim-card{padding:12px}}';
    document.head.appendChild(st);
  }

  /* ══ estado ══ */
  var S = {
    box: null, packages: null, pkgErr: null, plans: {}, open: null, runs: null, pending: null, policy: null,
    busy: false, msg: null, progress: null, timer: null, files: {}, details: {},
  };
  function keyOf(src) { return src.kind === 'package' ? 'p:' + src.name : 'f:' + src.sha; }
  function srcTitle(src) {
    if (src.kind === 'package') {
      var m = (S.packages || []).filter(function (p) { return p.name === src.name; })[0];
      return m ? (en() ? m.title_en : m.title_es) : src.name;
    }
    return t('file_title', { name: (S.files[src.sha] || {}).name || src.sha.slice(0, 12) });
  }

  /* ══ red ══ */
  async function getJSON(url) {
    try {
      var r = await fetch(base() + url, { cache: 'no-store' });
      var d = await r.json().catch(function () { return {}; });
      return { ok: r.ok, status: r.status, d: d || {} };
    } catch (e) { return { ok: false, status: 0, d: {}, net: true }; }
  }
  async function pinPost(url, body, timeout) {
    var f = W._tradeFetch;
    if (typeof f !== 'function') return { ok: false, status: 0, d: { code: 'no_trade_fetch' } };
    try {
      var r = await f(base() + url, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body), timeout: timeout || 120000, channel: 'ui' }, true);
      var d = await r.json().catch(function () { return {}; });
      return { ok: r.ok, status: r.status, d: d || {} };
    } catch (e) { return { ok: false, status: 0, d: {}, net: true }; }
  }
  function serverText(d) {
    d = d || {};
    var m = en() ? (d.error_en || d.error) : (d.error || d.error_es || d.error_en);
    return m ? String(m) : '';
  }
  function errLine(res) {
    var d = res.d || {}, c = d.code || '';
    if (res.net) return t('e_network');
    var map = { plan_changed: 'e_plan_changed', graph_changed: 'e_graph_changed', graph_stale: 'e_graph_stale', busy: 'e_busy',
      confirm_db: 'e_confirm_db', pin_required: 'e_pin', invalid_pin: 'e_pin', ledger_unavailable: 'e_ledger',
      package_not_found: 'e_pkg', later_runs: 'e_later', already_rolled_back: 'e_already', graph_unavailable: 'e_graph_na' };
    if (map[c]) return t(map[c]);
    if (res.status === 401 || res.status === 403) return t('e_pin');
    if (res.status === 422) return t('e_gate');
    if (res.status === 429) return t('e_rate');
    return t('e_generic');
  }

  /* ══ carga ══ */
  async function loadPackages() {
    var res = await getJSON('/api/ontology/import/packages');
    if (!res.ok) { S.packages = []; S.pkgErr = res.status === 503 ? t('no_db') : (serverText(res.d) || errLine(res)); }
    else { S.packages = res.d.packages || []; S.pkgErr = null; S.pkgBroken = res.d.errors || []; }
  }
  async function loadRuns() {
    var res = await getJSON('/api/ontology/import/runs?limit=20');
    if (res.ok) { S.runs = res.d.runs || []; S.pending = res.d.pending_links; S.policy = res.d.policy || null; }
  }
  async function load() {
    render();
    await Promise.all([loadPackages(), loadRuns()]);
    render();
  }
  async function loadPlan(src) {
    var k = keyOf(src);
    S.plans[k] = { loading: true };
    render();
    var res;
    if (src.kind === 'package') res = await getJSON('/api/ontology/import/packages/plan?package=' + encodeURIComponent(src.name));
    else res = await pinPost('/api/ontology/import/plan', { file_sha: src.sha, view: 'panel', sanitize: 1 }, 120000);
    S.plans[k] = res.ok ? { data: res.d } : { err: res };
    render();
  }
  function togglePlan(src) {
    var k = keyOf(src);
    if (S.open === k) { S.open = null; render(); return; }
    S.open = k;
    if (!S.plans[k] || S.plans[k].err) loadPlan(src); else render();
  }

  /* ══ mensajes y progreso ══ */
  function setMsg(kind, lines) { S.msg = { kind: kind, lines: Array.isArray(lines) ? lines : [lines] }; render(); }
  function startProgress(kindKey) {
    S.progress = { label: t(kindKey), t0: Date.now(), key: kindKey };
    S.msg = null;
    if (S.timer) clearInterval(S.timer);
    S.timer = setInterval(function () {
      var el = S.box && S.box.querySelector('[data-kim="secs"]');
      if (el && S.progress) el.textContent = t('prog_secs', { s: Math.round((Date.now() - S.progress.t0) / 1000) });
    }, 1000);
    render();
  }
  function stopProgress() { S.progress = null; if (S.timer) clearInterval(S.timer); S.timer = null; }

  /* ══ diálogos (SOLO KhipuToast) ══ */
  function lastDb() { try { return W.localStorage.getItem('kh_import_db') || ''; } catch (e) { return ''; } }
  function saveDb(v) { try { W.localStorage.setItem('kh_import_db', v); } catch (e) {} }
  async function askDb(prefill, body) {
    var KT = W.KhipuToast;
    var v = await KT.prompt({ title: t('db_title'), body: body || t('db_body'), label: t('db_label'),
      value: prefill || '', maxLength: 120, okText: t('apply_go') });
    return String(v == null ? '' : v).trim();
  }
  function expectedDb(d) {
    var m = /\((['"])([^'"]{1,120})\1\)/.exec(String((d && (d.error || d.error_en)) || ''));
    return m ? m[2] : '';
  }
  async function actor() {
    if (typeof W.khipuActor !== 'function') return '';
    try { var a = await W.khipuActor({ ask: true }); return typeof a === 'string' ? a.slice(0, 80) : ''; } catch (e) { return ''; }
  }
  // confirma con el nombre de la base; si el servidor (tras el PIN) dice otro nombre, lo ofrece UNA vez
  async function withDb(send) {
    var db = await askDb(lastDb());
    if (!db) { setMsg('warn', t('db_needed')); return null; }
    var res = await send(db);
    if (!res.ok && res.d && res.d.code === 'confirm_db') {
      var exp = expectedDb(res.d);
      stopProgress(); render();
      if (exp) {
        var db2 = await askDb(exp, t('db_retry_body', { name: exp }));
        if (!db2) { setMsg('warn', t('db_needed')); return null; }
        db = db2;
        res = await send(db);
      }
    }
    if (res.ok) saveDb(db);
    return res;
  }

  /* ══ aplicar / deshacer ══ */
  async function apply(src) {
    var pl = S.plans[keyOf(src)];
    if (S.busy || !pl || !pl.data) return;
    var KT = W.KhipuToast;
    if (!KT || typeof KT.confirm !== 'function' || typeof KT.prompt !== 'function') { setMsg('err', t('no_dialog')); return; }
    var P = pl.data.plan, c = P.counts || {}, lk = c.links || {};
    var ok = await KT.confirm({
      title: t('apply_q', { title: srcTitle(src) }), subtitle: t('apply_sub'),
      rows: [[t('k_create'), fmtInt(c.create)], [t('k_merge'), fmtInt(c.merge)], [t('k_live'), fmtInt(lk.live)],
        [t('k_proposed'), fmtInt(lk.proposed)], [t('k_pending'), fmtInt(lk.pending)], [t('k_events'), fmtInt(c.events_estimated)]],
      note: t('apply_note'), requireCheck: t('backup_check'), confirmLabel: t('apply_go'),
    });
    if (!ok) return;
    var who = await actor();
    S.busy = true;
    var res = await withDb(function (db) {
      var body = { expect: { plan_sha: P.plan_sha }, confirm_db: db };
      if (who) body.actor = who;
      if (src.kind === 'package') body.package = src.name; else { body.file_sha = src.sha; body.sanitize = 1; }
      startProgress('prog_apply');
      return pinPost('/api/ontology/import/apply', body, 300000);
    });
    stopProgress();
    S.busy = false;
    if (!res) { render(); return; }
    if (res.ok) {
      var r = res.d;
      delete S.plans[keyOf(src)];
      S.open = null;
      S.details.runs = true;          // «Corridas» abierta: el botón «Deshacer» queda a la vista
      await Promise.all([loadPackages(), loadRuns()]);
      var pc = r.plan_counts || c;     // EMPRESAS del plan aplicado (objects_created suma también las fuentes nuevas)
      setMsg('ok', [t('ok_apply'), t('ok_apply_detail', { created: fmtInt(pc.create), merged: fmtInt(pc.merge),
        links: fmtInt(r.links_created), events: fmtInt(r.events), secs: fmtDec((+r.elapsed_ms || 0) / 1000, 1) }),
        { ids: [r.run_id, r.decision_id] }, t('ok_undo_hint'), { reload: true }]);
      return;
    }
    var code = (res.d || {}).code;
    if (code === 'plan_changed' || code === 'graph_changed') loadPlan(src);
    if (res.net) loadRuns();
    setMsg(res.net ? 'warn' : 'err', [errLine(res), serverText(res.d) ? t('e_server_says', { m: serverText(res.d) }) : null]);
  }

  async function undo(run) {
    if (S.busy || !run) return;
    var KT = W.KhipuToast;
    if (!KT || typeof KT.confirm !== 'function' || typeof KT.prompt !== 'function') { setMsg('err', t('no_dialog')); return; }
    var ok = await KT.confirm({ title: t('undo_q', { run: run.run_id }), note: t('undo_note'), confirmLabel: t('undo_go'), danger: true });
    if (!ok) return;
    var who = await actor();
    S.busy = true;
    var res = await withDb(function (db) {
      var body = { run_id: run.run_id, confirm_db: db };
      if (who) body.actor = who;
      startProgress('prog_undo');
      return pinPost('/api/ontology/import/rollback', body, 300000);
    });
    stopProgress();
    S.busy = false;
    if (!res) { render(); return; }
    S.plans = {};
    S.open = null;
    await Promise.all([loadPackages(), loadRuns()]);
    if (res.ok) {
      var r = res.d;
      setMsg('ok', [t('ok_undo'), t('ok_undo_detail', { links: fmtInt(r.links_retracted), retired: fmtInt(r.objects_retired),
        restored: fmtInt(r.objects_restored) }), { ids: [r.run_id, r.decision_id] }, { reload: true }]);
    } else {
      setMsg(res.net ? 'warn' : 'err', [errLine(res), serverText(res.d) ? t('e_server_says', { m: serverText(res.d) }) : null]);
    }
  }

  /* ══ subir un archivo propio (trozos ≤ policy.import.upload_chunk_max_bytes; PIN) ══ */
  function hex(buf) {
    return Array.prototype.map.call(new Uint8Array(buf), function (x) { return (x + 0x100).toString(16).slice(1); }).join('');
  }
  // SHA-256 en JS puro: crypto.subtle solo existe en contextos seguros (https/localhost); sin él la huella sale igual
  var K256 = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98,
    0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6,
    0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3,
    0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e,
    0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
    0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814,
    0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2];
  function sha256js(bytes) {
    var H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
    var n = bytes.length, blocks = (n + 72) >> 6, pad = new Uint8Array(blocks * 64), w = new Int32Array(64);
    pad.set(bytes); pad[n] = 0x80;
    var dv = new DataView(pad.buffer), bits = n * 8;
    dv.setUint32(pad.length - 8, Math.floor(bits / 4294967296)); dv.setUint32(pad.length - 4, bits >>> 0);
    for (var b = 0; b < blocks; b++) {
      var i, x, y;
      for (i = 0; i < 16; i++) w[i] = dv.getInt32(b * 64 + i * 4);
      for (i = 16; i < 64; i++) {
        x = w[i - 15]; y = w[i - 2];
        w[i] = (w[i - 16] + (((x >>> 7) | (x << 25)) ^ ((x >>> 18) | (x << 14)) ^ (x >>> 3)) + w[i - 7] +
          (((y >>> 17) | (y << 15)) ^ ((y >>> 19) | (y << 13)) ^ (y >>> 10))) | 0;
      }
      var A = H[0], B = H[1], C = H[2], D = H[3], E = H[4], F = H[5], G = H[6], HH = H[7];
      for (i = 0; i < 64; i++) {
        var t1 = (HH + (((E >>> 6) | (E << 26)) ^ ((E >>> 11) | (E << 21)) ^ ((E >>> 25) | (E << 7))) + ((E & F) ^ (~E & G)) +
          K256[i] + w[i]) | 0;
        var t2 = ((((A >>> 2) | (A << 30)) ^ ((A >>> 13) | (A << 19)) ^ ((A >>> 22) | (A << 10))) + ((A & B) ^ (A & C) ^ (B & C))) | 0;
        HH = G; G = F; F = E; E = (D + t1) | 0; D = C; C = B; B = A; A = (t1 + t2) | 0;
      }
      H[0] = (H[0] + A) | 0; H[1] = (H[1] + B) | 0; H[2] = (H[2] + C) | 0; H[3] = (H[3] + D) | 0;
      H[4] = (H[4] + E) | 0; H[5] = (H[5] + F) | 0; H[6] = (H[6] + G) | 0; H[7] = (H[7] + HH) | 0;
    }
    return H.map(function (v) { return ('0000000' + (v >>> 0).toString(16)).slice(-8); }).join('');
  }
  async function sha256Hex(bytes) {
    if (W.crypto && W.crypto.subtle && W.isSecureContext !== false) {
      try { return hex(await W.crypto.subtle.digest('SHA-256', bytes)); } catch (e) { /* cae al cálculo en JS */ }
    }
    return sha256js(bytes);
  }
  function b64(bytes) {
    var s = '', step = 0x8000;
    for (var i = 0; i < bytes.length; i += step) s += String.fromCharCode.apply(null, bytes.subarray(i, i + step));
    return W.btoa(s);
  }
  async function streamBytes(bytes, Ctor, fmt) {
    var stream = new Blob([bytes]).stream().pipeThrough(new Ctor(fmt));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }
  async function upload(file) {
    if (S.busy || !file) return;
    var name = String(file.name || 'import.json').slice(0, 180);
    S.busy = true;
    startProgress('prog_upload');
    try {
      var bytes = new Uint8Array(await file.arrayBuffer());
      if (/\.gz$/i.test(name)) {
        if (typeof W.DecompressionStream !== 'function') throw { user: t('up_no_gz') };
        bytes = await streamBytes(bytes, W.DecompressionStream, 'gzip');
        name = name.replace(/\.gz$/i, '');
      }
      if (bytes.length > 64 * 1024 * 1024) throw { user: t('up_too_big') };
      var sha = await sha256Hex(bytes);
      var zl = typeof W.CompressionStream === 'function';
      var cap = +((S.policy || {}).upload_chunk_max_bytes) || 921600;
      var size = zl ? Math.max(4096, cap - 4096) : Math.min(cap, 700000);   // sin zlib: base64 cabe en 1 MB
      var n = Math.max(1, Math.ceil(bytes.length / size)), last = null;
      for (var i = 0; i < n; i++) {
        var part = bytes.subarray(i * size, Math.min(bytes.length, (i + 1) * size));
        var data = zl ? await streamBytes(part, W.CompressionStream, 'deflate') : part;
        S.progress.label = t('up_sending', { i: i + 1, n: n });
        render();
        last = await pinPost('/api/ontology/import/files', { name: name, sha256: sha, chunk: i, chunks: n, data: b64(data),
          encoding: zl ? 'zlib' : 'none', actor: (typeof W.khipuActor === 'function' ? W.khipuActor() : '') || undefined }, 120000);
        if (!last.ok) break;
      }
      stopProgress();
      S.busy = false;
      if (!last || !last.ok) {
        setMsg('err', [errLine(last || {}), serverText((last || {}).d) ? t('e_server_says', { m: serverText(last.d) }) : null]);
        return;
      }
      S.files[sha] = { name: name, n: last.d.n_records };
      setMsg('ok', t('up_done', { name: name, n: fmtInt(last.d.n_records) }));
      var src = { kind: 'file', sha: sha };
      S.open = keyOf(src);
      loadPlan(src);
    } catch (e) {
      stopProgress();
      S.busy = false;
      setMsg('err', (e && e.user) || String((e && e.message) || e));
    }
  }

  /* ══ pintar ══ */
  function tile(n, label) { return h('div', { class: 'kim-tile' }, [h('span', { class: 'n' }, n), h('span', { class: 'l' }, label)]); }
  function sec(label, xkey) { return h('div', { class: 'kim-sec' }, [label, xkey ? q(xkey) : null]); }
  function det(key, summary, kids) {
    var d = h('details', S.details[key] ? { open: true } : null, [h('summary', null, summary)].concat(kids));
    d.addEventListener('toggle', function () { S.details[key] = d.open; });
    return d;
  }
  function counterList(obj, prefix) {
    return Object.keys(obj || {}).sort(function (a, b) { return (obj[b] - obj[a]) || (a < b ? -1 : 1); })
      .map(function (k) { return tc(prefix, k) + ' ' + fmtInt(obj[k]); }).join(' · ');
  }
  function howLabel(m) {
    m = String(m || '');
    if (m.indexOf('name') === 0) return t('how_name');
    return T.es['how_' + m] != null ? t('how_' + m) : (m || t('how_other'));
  }

  function renderPlan(src, pkg) {
    var k = keyOf(src), st = S.plans[k] || {};
    var wrap = h('div', { class: 'kim-plan' });
    if (st.loading) { add(wrap, [h('div', { class: 'kim-bar' }, h('i')), h('div', { class: 'kim-mut', role: 'status' }, t('plan_loading'))]); return wrap; }
    if (st.err) {
      add(wrap, h('div', { class: 'kim-msg err', role: 'alert' }, [errLine(st.err),
        serverText(st.err.d) ? h('div', { class: 'kim-mut' }, t('e_server_says', { m: serverText(st.err.d) })) : null,
        h('div', { class: 'kim-acts' }, btn('↻ ' + t('retry'), function () { loadPlan(src); }))]));
      return wrap;
    }
    if (!st.data) return wrap;
    var P = st.data.plan, c = P.counts || {}, lk = c.links || {}, wc = P.what_changes || {};
    add(wrap, [
      sec(t('sec_enter'), 'import_links'),
      h('div', { class: 'kim-tiles' }, [
        tile(fmtInt(c.create), t('k_create')), tile(fmtInt(c.merge), t('k_merge')), tile(fmtInt(lk.live), t('k_live')),
        tile(fmtInt(lk.proposed), t('k_proposed')), tile(fmtInt(lk.pending), t('k_pending')),
        tile(fmtInt(c.categories_to_approve), t('k_cats'))]),
    ]);
    // vivos con un peso que NO salió de la investigación (tabla de policy.import): se ven antes de aplicar
    var dw = (c.links_default_weight || {}).live || {};
    if (dw.default_owns || dw.default_nonflow) {
      add(wrap, h('div', { class: 'kim-line' }, [t('dw_line', { owns: fmtInt(dw.default_owns || 0),
        nonflow: fmtInt(dw.default_nonflow || 0) }), ' ', q('import_default_weight')]));
    }
    var extra = [];
    if (c.update) extra.push(t('k_update') + ' ' + fmtInt(c.update));
    if (c.skip) extra.push(t('k_skip') + ' ' + fmtInt(c.skip));
    if (c.invalid) extra.push(t('k_invalid') + ' ' + fmtInt(c.invalid));
    if (extra.length) add(wrap, h('div', { class: 'kim-line kim-warn' }, extra.join(' · ')));
    // ¿qué cambia?
    add(wrap, sec(t('sec_change'), 'import_change'));
    if (wc.available) {
      var b = wc.before || {}, a = wc.after || {};
      if (wc.identical) add(wrap, h('div', { class: 'kim-line' }, t('ch_same')));
      add(wrap, [
        h('div', { class: 'kim-line' }, t('ch_nodes', { a: fmtInt(b.nodes), b: fmtInt(a.nodes) })),
        // lo exacto y simple: los vínculos vivos que entran al kernel (before/after.links = entradas de las matrices)
        h('div', { class: 'kim-line' }, t('ch_links', { n: fmtInt(wc.added_links || 0) })),
        h('div', { class: 'kim-line' }, t('ch_rho', { a: fmtDec(b.rho, 4), b: fmtDec(a.rho, 4) })),
        h('div', { class: 'kim-line' }, t('ch_tsmc', { a: fmtInt(b.tsmc_hit), b: fmtInt(a.tsmc_hit) })),
        h('div', { class: 'kim-line' }, t('ch_top', { in: (wc.top_in || []).join(', ') || t('ch_none'),
          out: (wc.top_out || []).join(', ') || t('ch_none') })),
        wc.calibration_stale ? h('div', { class: 'kim-line kim-warn' }, ['⚠ ' + t('ch_stale'), ' ', q('import_calibration')]) : null,
      ]);
    } else {
      add(wrap, h('div', { class: 'kim-line kim-warn' }, t('ch_na', { r: wc.reason || '?' })));
    }
    // fusiones
    var merges = P.merges || [];
    if (merges.length) add(wrap, det(k + ':m', '🔗 ' + t('sec_merge') + ' (' + fmtInt(merges.length) + ')', h('ul', { class: 'kim-ul' },
      merges.map(function (m) { return h('li', null, t('merge_row', { name: m.name || m.record_id, id: m.id, how: howLabel(m.method) })); }))));
    // para revisar
    var rv = P.review || [];
    if (rv.length) add(wrap, det(k + ':r', '🔎 ' + t('sec_review') + ' (' + fmtInt(rv.length) + ')', h('ul', { class: 'kim-ul' },
      rv.map(function (x) {
        var v = { name: x.name || x.record_id, other: x.other || '?', score: x.score == null ? '—' : x.score, kind: tc('cf_', x.kind) };
        var key = x.kind === 'possible_duplicate' ? 'review_dup' : (x.kind === 'name_target_is_counterparty' ? 'review_sub'
          : (x.kind === 'hint_mismatch' ? 'review_hint' : 'review_other'));
        return h('li', null, t(key, v));
      }))));
    // vínculos: por qué no vivos + por tipo
    var why = P.not_live_reasons || {};
    if (Object.keys(why).length) add(wrap, det(k + ':w', t('sec_why'), h('ul', { class: 'kim-ul' },
      Object.keys(why).sort(function (x, y) { return why[y] - why[x]; }).map(function (r) { return h('li', null, tc('r_', r) + ': ' + fmtInt(why[r])); }))));
    var lbt = P.links_by_type || {};
    if (Object.keys(lbt).length) add(wrap, det(k + ':t', t('sec_types'), h('ul', { class: 'kim-ul' },
      Object.keys(lbt).sort().map(function (rt) {
        var r = lbt[rt];
        return h('li', null, rt + ' (' + tc('rel_', rt) + '): ' + t('route_live') + ' ' + fmtInt(r.live || 0) + ' · ' +
          t('route_proposed') + ' ' + fmtInt(r.proposed || 0) + ' · ' + t('route_pending') + ' ' + fmtInt(r.pending || 0));
      }))));
    // avisos / conflictos / inválidas / categorías
    if (P.warnings && Object.keys(P.warnings).length) add(wrap, h('div', { class: 'kim-line' }, t('warn_line', { list: counterList(P.warnings, 'w_') })));
    if (P.conflicts && Object.keys(P.conflicts).length) add(wrap, h('div', { class: 'kim-line' }, t('conf_line', { list: counterList(P.conflicts, 'cf_') })));
    if ((P.invalid || []).length) add(wrap, det(k + ':i', t('k_invalid') + ' (' + fmtInt(c.invalid) + ')', h('ul', { class: 'kim-ul' },
      P.invalid.map(function (x) { return h('li', null, t('invalid_line', { rid: x.record_id || '?', msg: (en() ? x.msg_en : x.msg_es) || '' })); }))));
    if ((P.categories_to_approve || []).length) add(wrap, det(k + ':c', t('k_cats') + ' (' + fmtInt(P.categories_to_approve.length) + ')', h('ul', { class: 'kim-ul' },
      P.categories_to_approve.map(function (x) { return h('li', null, t('cats_line', { id: (en() ? x.label_en : x.label_es) || x.id, n: fmtInt(x.n) })); }))));
    // reparado (formato) — del paquete o del plan (archivo subido)
    var san = pkg && pkg.sanitize ? pkg.sanitize : (P.sanitize || null);
    if (san) {
      var rep = san.fields_repaired, drop = san.fields_dropped, rec = san.records_changed;
      var rej = typeof san.rejected === 'number' ? san.rejected : (san.rejected || []).length;
      add(wrap, [sec('🧹 ' + t('sec_fix'), 'import_sanitize'),
        h('div', { class: 'kim-line' }, (rep || drop || rej) ? t('fix_line', { rep: fmtInt(rep), rec: fmtInt(rec), drop: fmtInt(drop), rej: fmtInt(rej) }) : t('fix_none'))]);
    }
    if (pkg && pkg.origin && pkg.origin.excluded) add(wrap, h('div', { class: 'kim-line' }, '⛔ ' + t('excl_line', { n: fmtInt(pkg.origin.excluded) })));
    // huella + acciones
    add(wrap, [h('div', { class: 'kim-mut' }, [t('fp_label'), ' ', h('code', { title: P.plan_sha }, String(P.plan_sha || '').slice(0, 12) + '…'),
      ' · ', P.graph_source === 'pg' && P.graph_version != null ? t('fp_graph', { gv: P.graph_version }) : t('fp_snap'), q('import_fingerprint')]),
    h('div', { class: 'kim-acts' }, [
      btn('✓ ' + t('apply'), function () { apply(src); }, 'pri', { disabled: S.busy || c.valid === 0 ? true : null, 'data-kim-f': 'apply:' + k }),
      btn(t('hide_plan'), function () { togglePlan(src); }, '', { 'data-kim-f': 'hide:' + k }),
    ])]);
    return wrap;
  }

  function renderPackages(card) {
    if (S.packages == null) { add(card, h('div', { class: 'kim-mut kim-in' }, t('loading'))); return; }
    if (S.pkgErr) { add(card, h('div', { class: 'kim-mut kim-in' }, S.pkgErr)); return; }
    if (!S.packages.length) add(card, h('div', { class: 'kim-mut kim-in' }, t('no_pkgs')));
    (S.pkgBroken || []).forEach(function (e) {
      add(card, h('div', { class: 'kim-line kim-warn kim-in' }, '⚠ ' + t('pkg_broken', { name: e.name, err: (en() ? e.error_en : e.error) || '?' })));
    });
    S.packages.forEach(function (p) {
      var src = { kind: 'package', name: p.name }, open = S.open === keyOf(src);
      var undone = (p.runs || []).length && !p.applied;
      var chip = p.applied ? h('span', { class: 'kim-chip ok' }, '✓ ' + t('st_applied'))
        : h('span', { class: 'kim-chip' + (undone ? ' warn' : '') }, undone ? t('st_undone') : t('st_new'));
      var row = h('div', { class: 'kim-pkg', 'data-pkg': p.name }, [
        h('div', { class: 'kim-pkg-hd' }, [h('b', null, en() ? p.title_en : p.title_es), chip,
          btn(open ? t('hide_plan') : t('see_plan'), function () { togglePlan(src); }, open ? '' : 'pri',
            { 'aria-expanded': open ? 'true' : 'false', 'data-kim-f': 'toggle:' + keyOf(src) })]),
        h('div', { class: 'kim-mut' }, [t('pkg_meta', { date: p.date, links: fmtInt(p.n_relations) }),
          p.origin && p.origin.excluded ? ' · ' + t('pkg_excluded', { n: fmtInt(p.origin.excluded) }) : '',
          p.plan_doc ? ' · ' : '', p.plan_doc ? code(p.plan_doc) : null]),
      ]);
      if (open) add(row, renderPlan(src, p));
      add(card, h('div', { class: 'kim-in' }, row));
    });
    // archivos subidos en esta sesión
    Object.keys(S.files).forEach(function (sha) {
      var src = { kind: 'file', sha: sha }, open = S.open === keyOf(src), f = S.files[sha];
      var row = h('div', { class: 'kim-pkg', 'data-file': sha }, [
        h('div', { class: 'kim-pkg-hd' }, [h('b', null, t('file_title', { name: f.name })), h('span', { class: 'kim-chip' }, fmtInt(f.n)),
          btn(open ? t('hide_plan') : t('see_plan'), function () { togglePlan(src); }, open ? '' : 'pri',
            { 'aria-expanded': open ? 'true' : 'false', 'data-kim-f': 'toggle:' + keyOf(src) })]),
      ]);
      if (open) add(row, renderPlan(src, null));
      add(card, h('div', { class: 'kim-in' }, row));
    });
  }

  function renderRuns(card) {
    var runs = S.runs || [];
    var undone = {};
    runs.forEach(function (r) { if (r.kind === 'rollback' && r.rolled_back_run) undone[r.rolled_back_run] = 1; });
    var applies = runs.filter(function (r) { return r.kind === 'apply'; });
    var newest = applies.filter(function (r) { return !undone[r.id]; })[0];
    var kids = [];
    if (!applies.length) kids.push(h('div', { class: 'kim-mut' }, t('runs_none')));
    applies.slice(0, 8).forEach(function (r) {
      var isUndone = !!undone[r.id], s = r.summary || {};
      kids.push(h('div', { class: 'kim-run' }, [
        h('span', { class: 't' }, [t('run_row', { date: fmtWhen(r.created_at), batch: r.batch || '—', n: fmtInt((s.counts || {}).create || 0) }), ' ', code(r.run_id)]),
        h('span', { class: 'kim-chip' + (isUndone ? '' : ' ok') }, isUndone ? t('run_undone') : t('run_applied')),
        newest && newest.id === r.id ? btn('↶ ' + t('undo'), function () { undo(r); }, 'bad', { disabled: S.busy ? true : null, 'data-kim-f': 'undo' }) : null,
      ]));
    });
    if (S.pending != null) kids.push(h('div', { class: 'kim-mut' }, [t('pending_links', { n: fmtInt(S.pending) }), q('import_links')]));
    add(card, h('div', { class: 'kim-in' }, det('runs', '🧾 ' + t('sec_runs') + ' (' + fmtInt(applies.length) + ')', kids)));
  }

  function renderUpload(card) {
    var input = h('input', { type: 'file', accept: '.json,.jsonl,.gz,application/json', class: 'kim-file', hidden: true,
      'aria-hidden': 'true', tabindex: '-1' });
    input.addEventListener('change', function () { var f = input.files && input.files[0]; input.value = ''; if (f) upload(f); });
    add(card, h('div', { class: 'kim-in' }, det('upload', '📤 ' + t('sec_upload'), [
      h('div', { class: 'kim-mut' }, t('upload_hint')),
      h('div', { class: 'kim-acts' }, [btn(t('upload_btn'), function () { input.click(); }, '', { disabled: S.busy ? true : null }), input]),
    ])));
  }

  function renderMsg(card) {
    if (S.progress) {
      add(card, h('div', { class: 'kim-msg kim-in', role: 'status', 'aria-live': 'polite' }, [
        h('div', null, ['⏳ ', h('b', null, S.progress.label), ' · ',
          h('span', { 'data-kim': 'secs' }, t('prog_secs', { s: Math.round((Date.now() - S.progress.t0) / 1000) }))]),
        h('div', { class: 'kim-bar' }, h('i')),
        S.progress.key !== 'prog_upload' ? h('div', { class: 'kim-mut' }, t('prog_note')) : null]));
      return;
    }
    if (!S.msg) return;
    var icon = S.msg.kind === 'ok' ? '✅ ' : (S.msg.kind === 'warn' ? '⚠ ' : '❌ ');
    var box = h('div', { class: 'kim-msg kim-in ' + S.msg.kind, role: S.msg.kind === 'ok' ? 'status' : 'alert' });
    S.msg.lines.forEach(function (ln, i) {
      if (ln == null) return;
      if (typeof ln === 'object' && ln.reload) {    // el mapa y la búsqueda se arman al cargar la página (catalog_sync)
        add(box, h('div', { class: 'kim-acts' }, [h('span', { class: 'kim-mut' }, t('reload_hint')),
          btn(t('reload_btn'), function () { try { W.location.reload(); } catch (e) {} })]));
        return;
      }
      if (typeof ln === 'object' && ln.ids) {
        add(box, h('div', { class: 'kim-mut' }, [t('id_run'), ' ', code(ln.ids[0] || '—'), ' · ', t('id_dec'), ' ', code(ln.ids[1] || '—')]));
        return;
      }
      add(box, h('div', i === 0 ? null : { class: 'kim-mut' }, i === 0 ? [icon, h('b', null, ln)] : ln));
    });
    add(card, box);
  }

  function render() {
    var box = S.box;
    if (!box) return;
    _lastLang = en();
    ensureStyles();
    if (box.classList) { box.classList.add('kos-themed'); box.classList.add('kim-root'); }
    var focusKey = document.activeElement && box.contains(document.activeElement) ? document.activeElement.getAttribute('data-kim-f') : null;
    clear(box);
    var card = h('div', { class: 'kim-card' }, [
      h('div', { class: 'kim-hd' }, [h('span', { class: 'kim-ic', 'aria-hidden': 'true' }, '📥'), h('b', null, t('title')), q('import_panel')]),
      h('div', { class: 'kim-mut kim-in' }, t('sub')),
    ]);
    renderPackages(card);
    if (!S.pkgErr) { renderUpload(card); renderRuns(card); }
    renderMsg(card);
    box.appendChild(card);
    if (focusKey) {
      var all = box.querySelectorAll('[data-kim-f]');
      for (var i = 0; i < all.length; i++) if (all[i].getAttribute('data-kim-f') === focusKey) { all[i].focus(); break; }
    }
  }

  // ES/EN: se repinta con el idioma nuevo (como layers.js/oswindows.js: <html lang> que pone applyLang() y 'khipu:lang')
  var _lastLang = null;
  function onLang() {
    var now = en();
    if (now === _lastLang) return;
    _lastLang = now;
    if (S.box && document.contains(S.box) && !S.progress) render();
  }
  if (W.addEventListener) W.addEventListener('khipu:lang', onLang);
  try { new MutationObserver(onLang).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] }); } catch (e) {}

  W.KhipuImporter = {
    __v: 1,
    mount: function (parentId) {
      var parent = document.getElementById(parentId || 'sistema-diag');
      if (!parent) return;
      var box = document.getElementById('import-box');
      if (!box) {
        box = document.createElement('div');
        box.id = 'import-box';
        var after = document.getElementById('prices-box');
        if (after && after.parentNode === parent) parent.insertBefore(box, after.nextSibling); else parent.appendChild(box);
      }
      S.box = box;
      if (S.busy) { render(); return; }
      load();
    },
    reload: function () { return load(); },
    _T: T,
    _sha256: sha256js,
  };
})();
