---
tipo: "api"
capa: "Infraestructura"
rutas: 8
tags: ["capa/infraestructura", "tipo/api"]
---

# API páginas y archivos estáticos

> 8 rutas · definidas en [[server.py]] · prefijo `/`, `/engine/<path:filename>`, `/icon.svg`, `/manifest.webmanifest`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/` | `index` | [[server.py]] | — |
| `GET` | `/engine/<path:filename>` | `serve_engine` | [[server.py]] | — |
| `GET` | `/icon.svg` | `icon` | [[server.py]] | — |
| `GET` | `/manifest.webmanifest` | `manifest` | [[server.py]] | — |
| `GET` | `/nodes/<path:filename>` | `serve_nodes` | [[server.py]] | — |
| `GET` | `/sim/<path:filename>` | `serve_sim` | [[server.py]] | — |
| `GET` | `/sw.js` | `service_worker` | [[server.py]] | — |
| `GET` | `/vendor/<path:name>` | `vendor` | [[server.py]] | — |
