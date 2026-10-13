---
tipo: "modulo"
capa: "Infraestructura"
ruta: "scripts/build_vault.py"
lenguaje: "python"
lineas: 3483
aliases: ["scripts/build_vault.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# scripts/build_vault.py

> Módulo · capa [[Capa Infraestructura]] · 3.483 líneas · `scripts/build_vault.py`

## Para qué sirve

BÓVEDA DE OBSIDIAN + GRAFO DE CONOCIMIENTO del repo (2026-10-11).

## API pública

- `capa_de(path)` _(línea 230)_
- `safe_name(s, limit=…)` — Nombre de archivo válido en Windows/macOS/Linux y como [ [enlace] ] de Obsidian. _(línea 240)_
- `prose(s)` — Texto tomado de las fuentes → Markdown seguro (sin enlaces, etiquetas ni HTML accidentales). _(línea 254)_
- `cell(s)` _(línea 268)_
- `code(s)` _(línea 272)_
- `tcode(s)` — código dentro de una tabla _(línea 277)_
- `link(name)` _(línea 282)_
- `first_paragraph(text, limit=…)` _(línea 286)_
- `strip_self_path(p, path)` — Quita el prefijo «ruta — » con el que empiezan casi todos los docstrings/cabeceras. _(línea 295)_
- `fm(d)` — Front matter YAML (cadenas en JSON, que es YAML válido). _(línea 306)_
- `miles(n)` _(línea 322)_
- clase `JSScan` — code = fuente sin comentarios (con cadenas); code_ns = además sin el TEXTO de las cadenas (quedan comillas vacías; el código dentro de \${…} … _(línea 347)_
- `js_identifiers(code_text, skip_keys=…)` — (identificadores sueltos, identificadores leídos como window.X). skip_keys: sin las claves de objetos. _(línea 487)_
- `js_local_decls(code_text)` _(línea 509)_
- `js_header(text)` — Primer comentario del archivo (cabecera) → texto plano. _(línea 521)_
- `analyze_py(path, text)` _(línea 615)_
- `dyn_module_refs(root, strings=…)` — Textos que nombran un módulo para importarlo en tiempo de ejecución (importación «dinámica»). _(línea 814)_
- `inventory()` _(línea 872)_
- clase `Model` _(línea 926)_
- `endpoint_ref(s)` — Literal que parece una ruta HTTP de Khipus → forma normalizada, o None. _(línea 957)_
- `match_routes(ref, routes_by_path, prefix=…)` — Rutas que un literal puede estar llamando. Exacto; o (prefix=True) prefijo si el literal termina en '/' (se concatena algo) o es una base … _(línea 988)_
- `build_model()` _(línea 1013)_
- `js_concat_chains(code)` — Concatenaciones que arman una ruta RELATIVA: '/clients/' + id + '/audit' → '/clients/◊/audit' y API + '/status' → '◊/status'. Un texto en … _(línea 1373)_
- `relative_refs(chains)` — Rutas relativas limpias ('/clients/◊/audit') a partir de las cadenas armadas. _(línea 1444)_
- `parse_claude_env_block(text)` _(línea 1530)_
- `env_documented(M, name)` _(línea 1559)_
- `env_is_read(M, name)` — ¿Alguien la lee? (directo, por patrón f'PREFIJO_{x}' o en despliegue) _(línea 1569)_
- `parse_sessions(text)` _(línea 1663)_
- `api_group_layer(M, g, rs)` _(línea 1800)_
- `api_group(path)` _(línea 1810)_
- `route_is_external(path)` _(línea 1821)_
- `derive(M)` _(línea 1827)_
- `capa_link(key)` _(línea 1894)_
- `capa_note_name(key)` _(línea 1898)_
- `env_note(nm)` _(línea 1902)_
- `tags_for(layer, tipo)` _(línea 1906)_
- `note_module(M, p)` _(línea 1928)_
- `note_api_group(M, g)` _(línea 2212)_
- `note_mcp_tools(M)` _(línea 2231)_
- `note_api_index(M)` _(línea 2249)_
- `note_env(M, nm)` _(línea 2262)_
- `note_env_index(M)` _(línea 2300)_
- `note_session(M, s, prev, nxt)` _(línea 2312)_
- `note_session_index(M)` _(línea 2336)_
- `note_test_index(M)` _(línea 2347)_
- `note_layer(M, key)` _(línea 2362)_
- `note_home(M)` _(línea 2405)_
- `note_howto(M)` _(línea 2449)_
- `note_report(M, R)` _(línea 2517)_
- `report_data(M)` _(línea 2618)_
- `note_sw(M, R)` _(línea 2735)_
- `note_path(M, p)` _(línea 2754)_
- `graph_data(M)` _(línea 2759)_
- `graph_json_text(G)` _(línea 2789)_
- `map_html(M, G)` _(línea 2803)_
- `obsidian_files()` _(línea 2827)_
- `merge_obsidian_config(rel, old_text, new_text)` — Configuración de Obsidian que YA existe → lo que hay que escribir (None = no tocar). _(línea 2863)_
- `build_vault()` — → dict {ruta relativa dentro de vault/: texto} _(línea 2897)_
- `existing_owned(vault_dir)` _(línea 2952)_
- `diff_vault(out, vault_dir)` — Diferencias entre lo generado y vault/. La configuración de Obsidian solo tiene que EXISTIR: Obsidian la reescribe cuando la persona mueve … _(línea 2968)_
- `write_vault(out, vault_dir)` _(línea 2988)_
- `main(argv=…)` _(línea 3021)_

**Internas** (empiezan con `_`): `_read`, `_lines`, `_is_object_key`, `_const_str`, `_render_str`, `_call_name`, `_sig`, `_loop_names`, `_assign_names`, `_module_names`, `_resolve_import`, `_segs`, `_seg_ok`, `_window_aliases`, `_analyze_js`, `_str_uses`, `_analyze_html`, `_md_purpose`, `_mcp_tools`, `_mentions`, `_build_edges`, `_flink`, `_route_line`, `_callers_cell`, `_api_sections`, `_dep_sections`, `_endpoint_sections`, `_env_sections`, `_data_sections`, `_page_sections`, `_doc_sections`, `_test_sections`, `_dump_cfg`, `_managed_group`, `_owned`

## Depende de

_Nada interno._

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Pruebas que lo cubren

- [[tests.test_vault.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
