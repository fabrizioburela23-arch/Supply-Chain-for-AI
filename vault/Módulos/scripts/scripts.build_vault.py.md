---
tipo: "modulo"
capa: "Infraestructura"
ruta: "scripts/build_vault.py"
lenguaje: "python"
lineas: 3492
aliases: ["scripts/build_vault.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# scripts/build_vault.py

> Módulo · capa [[Capa Infraestructura]] · 3.492 líneas · `scripts/build_vault.py`

## Para qué sirve

BÓVEDA DE OBSIDIAN + GRAFO DE CONOCIMIENTO del repo (2026-10-11).

## API pública

- `capa_de(path)` _(línea 239)_
- `safe_name(s, limit=…)` — Nombre de archivo válido en Windows/macOS/Linux y como [ [enlace] ] de Obsidian. _(línea 249)_
- `prose(s)` — Texto tomado de las fuentes → Markdown seguro (sin enlaces, etiquetas ni HTML accidentales). _(línea 263)_
- `cell(s)` _(línea 277)_
- `code(s)` _(línea 281)_
- `tcode(s)` — código dentro de una tabla _(línea 286)_
- `link(name)` _(línea 291)_
- `first_paragraph(text, limit=…)` _(línea 295)_
- `strip_self_path(p, path)` — Quita el prefijo «ruta — » con el que empiezan casi todos los docstrings/cabeceras. _(línea 304)_
- `fm(d)` — Front matter YAML (cadenas en JSON, que es YAML válido). _(línea 315)_
- `miles(n)` _(línea 331)_
- clase `JSScan` — code = fuente sin comentarios (con cadenas); code_ns = además sin el TEXTO de las cadenas (quedan comillas vacías; el código dentro de \${…} … _(línea 356)_
- `js_identifiers(code_text, skip_keys=…)` — (identificadores sueltos, identificadores leídos como window.X). skip_keys: sin las claves de objetos. _(línea 496)_
- `js_local_decls(code_text)` _(línea 518)_
- `js_header(text)` — Primer comentario del archivo (cabecera) → texto plano. _(línea 530)_
- `analyze_py(path, text)` _(línea 624)_
- `dyn_module_refs(root, strings=…)` — Textos que nombran un módulo para importarlo en tiempo de ejecución (importación «dinámica»). _(línea 823)_
- `inventory()` _(línea 881)_
- clase `Model` _(línea 935)_
- `endpoint_ref(s)` — Literal que parece una ruta HTTP de Khipus → forma normalizada, o None. _(línea 966)_
- `match_routes(ref, routes_by_path, prefix=…)` — Rutas que un literal puede estar llamando. Exacto; o (prefix=True) prefijo si el literal termina en '/' (se concatena algo) o es una base … _(línea 997)_
- `build_model()` _(línea 1022)_
- `js_concat_chains(code)` — Concatenaciones que arman una ruta RELATIVA: '/clients/' + id + '/audit' → '/clients/◊/audit' y API + '/status' → '◊/status'. Un texto en … _(línea 1382)_
- `relative_refs(chains)` — Rutas relativas limpias ('/clients/◊/audit') a partir de las cadenas armadas. _(línea 1453)_
- `parse_claude_env_block(text)` _(línea 1539)_
- `env_documented(M, name)` _(línea 1568)_
- `env_is_read(M, name)` — ¿Alguien la lee? (directo, por patrón f'PREFIJO_{x}' o en despliegue) _(línea 1578)_
- `parse_sessions(text)` _(línea 1672)_
- `api_group_layer(M, g, rs)` _(línea 1809)_
- `api_group(path)` _(línea 1819)_
- `route_is_external(path)` _(línea 1830)_
- `derive(M)` _(línea 1836)_
- `capa_link(key)` _(línea 1903)_
- `capa_note_name(key)` _(línea 1907)_
- `env_note(nm)` _(línea 1911)_
- `tags_for(layer, tipo)` _(línea 1915)_
- `note_module(M, p)` _(línea 1937)_
- `note_api_group(M, g)` _(línea 2221)_
- `note_mcp_tools(M)` _(línea 2240)_
- `note_api_index(M)` _(línea 2258)_
- `note_env(M, nm)` _(línea 2271)_
- `note_env_index(M)` _(línea 2309)_
- `note_session(M, s, prev, nxt)` _(línea 2321)_
- `note_session_index(M)` _(línea 2345)_
- `note_test_index(M)` _(línea 2356)_
- `note_layer(M, key)` _(línea 2371)_
- `note_home(M)` _(línea 2414)_
- `note_howto(M)` _(línea 2458)_
- `note_report(M, R)` _(línea 2526)_
- `report_data(M)` _(línea 2627)_
- `note_sw(M, R)` _(línea 2744)_
- `note_path(M, p)` _(línea 2763)_
- `graph_data(M)` _(línea 2768)_
- `graph_json_text(G)` _(línea 2798)_
- `map_html(M, G)` _(línea 2812)_
- `obsidian_files()` _(línea 2836)_
- `merge_obsidian_config(rel, old_text, new_text)` — Configuración de Obsidian que YA existe → lo que hay que escribir (None = no tocar). _(línea 2872)_
- `build_vault()` — → dict {ruta relativa dentro de vault/: texto} _(línea 2906)_
- `existing_owned(vault_dir)` _(línea 2961)_
- `diff_vault(out, vault_dir)` — Diferencias entre lo generado y vault/. La configuración de Obsidian solo tiene que EXISTIR: Obsidian la reescribe cuando la persona mueve … _(línea 2977)_
- `write_vault(out, vault_dir)` _(línea 2997)_
- `main(argv=…)` _(línea 3030)_

**Internas** (empiezan con `_`): `_read`, `_lines`, `_is_object_key`, `_const_str`, `_render_str`, `_call_name`, `_sig`, `_loop_names`, `_assign_names`, `_module_names`, `_resolve_import`, `_segs`, `_seg_ok`, `_window_aliases`, `_analyze_js`, `_str_uses`, `_analyze_html`, `_md_purpose`, `_mcp_tools`, `_mentions`, `_build_edges`, `_flink`, `_route_line`, `_callers_cell`, `_api_sections`, `_dep_sections`, `_endpoint_sections`, `_env_sections`, `_data_sections`, `_page_sections`, `_doc_sections`, `_test_sections`, `_dump_cfg`, `_managed_group`, `_owned`

## Depende de

_Nada interno._

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Pruebas que lo cubren

- [[tests.test_vault.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
