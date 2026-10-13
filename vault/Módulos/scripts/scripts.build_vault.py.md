---
tipo: "modulo"
capa: "Infraestructura"
ruta: "scripts/build_vault.py"
lenguaje: "python"
lineas: 3479
aliases: ["scripts/build_vault.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# scripts/build_vault.py

> Módulo · capa [[Capa Infraestructura]] · 3.479 líneas · `scripts/build_vault.py`

## Para qué sirve

BÓVEDA DE OBSIDIAN + GRAFO DE CONOCIMIENTO del repo (2026-10-11).

## API pública

- `capa_de(path)` _(línea 229)_
- `safe_name(s, limit=…)` — Nombre de archivo válido en Windows/macOS/Linux y como [ [enlace] ] de Obsidian. _(línea 239)_
- `prose(s)` — Texto tomado de las fuentes → Markdown seguro (sin enlaces, etiquetas ni HTML accidentales). _(línea 253)_
- `cell(s)` _(línea 267)_
- `code(s)` _(línea 271)_
- `tcode(s)` — código dentro de una tabla _(línea 276)_
- `link(name)` _(línea 281)_
- `first_paragraph(text, limit=…)` _(línea 285)_
- `strip_self_path(p, path)` — Quita el prefijo «ruta — » con el que empiezan casi todos los docstrings/cabeceras. _(línea 294)_
- `fm(d)` — Front matter YAML (cadenas en JSON, que es YAML válido). _(línea 305)_
- `miles(n)` _(línea 321)_
- clase `JSScan` — code = fuente sin comentarios (con cadenas); code_ns = además sin el TEXTO de las cadenas (quedan comillas vacías; el código dentro de \${…} … _(línea 346)_
- `js_identifiers(code_text, skip_keys=…)` — (identificadores sueltos, identificadores leídos como window.X). skip_keys: sin las claves de objetos. _(línea 486)_
- `js_local_decls(code_text)` _(línea 508)_
- `js_header(text)` — Primer comentario del archivo (cabecera) → texto plano. _(línea 520)_
- `analyze_py(path, text)` _(línea 614)_
- `dyn_module_refs(root, strings=…)` — Textos que nombran un módulo para importarlo en tiempo de ejecución (importación «dinámica»). _(línea 813)_
- `inventory()` _(línea 871)_
- clase `Model` _(línea 925)_
- `endpoint_ref(s)` — Literal que parece una ruta HTTP de Khipus → forma normalizada, o None. _(línea 956)_
- `match_routes(ref, routes_by_path, prefix=…)` — Rutas que un literal puede estar llamando. Exacto; o (prefix=True) prefijo si el literal termina en '/' (se concatena algo) o es una base … _(línea 987)_
- `build_model()` _(línea 1012)_
- `js_concat_chains(code)` — Concatenaciones que arman una ruta RELATIVA: '/clients/' + id + '/audit' → '/clients/◊/audit' y API + '/status' → '◊/status'. Un texto en … _(línea 1370)_
- `relative_refs(chains)` — Rutas relativas limpias ('/clients/◊/audit') a partir de las cadenas armadas. _(línea 1441)_
- `parse_claude_env_block(text)` _(línea 1527)_
- `env_documented(M, name)` _(línea 1556)_
- `env_is_read(M, name)` — ¿Alguien la lee? (directo, por patrón f'PREFIJO_{x}' o en despliegue) _(línea 1566)_
- `parse_sessions(text)` _(línea 1660)_
- `api_group_layer(M, g, rs)` _(línea 1797)_
- `api_group(path)` _(línea 1807)_
- `route_is_external(path)` _(línea 1818)_
- `derive(M)` _(línea 1824)_
- `capa_link(key)` _(línea 1891)_
- `capa_note_name(key)` _(línea 1895)_
- `env_note(nm)` _(línea 1899)_
- `tags_for(layer, tipo)` _(línea 1903)_
- `note_module(M, p)` _(línea 1925)_
- `note_api_group(M, g)` _(línea 2209)_
- `note_mcp_tools(M)` _(línea 2228)_
- `note_api_index(M)` _(línea 2245)_
- `note_env(M, nm)` _(línea 2258)_
- `note_env_index(M)` _(línea 2296)_
- `note_session(M, s, prev, nxt)` _(línea 2308)_
- `note_session_index(M)` _(línea 2332)_
- `note_test_index(M)` _(línea 2343)_
- `note_layer(M, key)` _(línea 2358)_
- `note_home(M)` _(línea 2401)_
- `note_howto(M)` _(línea 2445)_
- `note_report(M, R)` _(línea 2513)_
- `report_data(M)` _(línea 2614)_
- `note_sw(M, R)` _(línea 2731)_
- `note_path(M, p)` _(línea 2750)_
- `graph_data(M)` _(línea 2755)_
- `graph_json_text(G)` _(línea 2785)_
- `map_html(M, G)` _(línea 2799)_
- `obsidian_files()` _(línea 2823)_
- `merge_obsidian_config(rel, old_text, new_text)` — Configuración de Obsidian que YA existe → lo que hay que escribir (None = no tocar). _(línea 2859)_
- `build_vault()` — → dict {ruta relativa dentro de vault/: texto} _(línea 2893)_
- `existing_owned(vault_dir)` _(línea 2948)_
- `diff_vault(out, vault_dir)` — Diferencias entre lo generado y vault/. La configuración de Obsidian solo tiene que EXISTIR: Obsidian la reescribe cuando la persona mueve … _(línea 2964)_
- `write_vault(out, vault_dir)` _(línea 2984)_
- `main(argv=…)` _(línea 3017)_

**Internas** (empiezan con `_`): `_read`, `_lines`, `_is_object_key`, `_const_str`, `_render_str`, `_call_name`, `_sig`, `_loop_names`, `_assign_names`, `_module_names`, `_resolve_import`, `_segs`, `_seg_ok`, `_window_aliases`, `_analyze_js`, `_str_uses`, `_analyze_html`, `_md_purpose`, `_mcp_tools`, `_mentions`, `_build_edges`, `_flink`, `_route_line`, `_callers_cell`, `_api_sections`, `_dep_sections`, `_endpoint_sections`, `_env_sections`, `_data_sections`, `_page_sections`, `_doc_sections`, `_test_sections`, `_dump_cfg`, `_managed_group`, `_owned`

## Depende de

_Nada interno._

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Pruebas que lo cubren

- [[tests.test_vault.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
