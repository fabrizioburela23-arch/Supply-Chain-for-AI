# Prompt para Claude Cowork — terminar la configuración de Khipus AI Finance

Copia TODO lo que está dentro del bloque de abajo y pégalo en Claude Cowork.

---

> Soy el dueño de **Khipus AI Finance Intelligence**, un terminal financiero
> tipo Bloomberg (semiconductores, IA, espacio, nuclear) desplegado en
> **Railway**. Es una app Flask de un solo archivo (`server.py`) + `app.html`,
> con **microservicios opcionales** en el mismo repo. Otro asistente (Claude
> Code) está trabajando ACTIVAMENTE el código de la app; por eso necesito que
> **TÚ te enfoques SOLO en la configuración/despliegue en Railway y en guiarme
> con clics**, y que **NO edites** `server.py`, `app.html` ni `engine/*`
> (evitamos conflictos de git). Si algún cambio de código fuera imprescindible,
> hazlo SOLO dentro de la carpeta `rag/` y en una rama nueva, y avísame primero.
>
> Ayúdame a dejar en verde estas 3 cosas pendientes (verifícalas al final con el
> panel 🩺 de diagnóstico de la app). Hazme preguntas cuando necesites un dato
> mío (llaves, nombres de servicio) en vez de inventarlos.
>
> ## 1) Second Brain (RAG) — DESPLEGAR como servicio nuevo en Railway
> El microservicio ya existe y está listo en la carpeta `rag/` (tiene su propio
> `Dockerfile`, `railway.toml`, `requirements.txt`, `rag_server.py`, `indexer.py`).
> Corre ChromaDB + Flask y expone `/stats`, `/index/company`, `/query/ai`.
> El servidor principal lo llama por la variable `RAG_URL` (hoy apunta a
> `localhost:5051`, por eso el diagnóstico marca “RAG no responde”).
> Guíame paso a paso para:
> 1. En Railway, dentro del MISMO proyecto, crear un **nuevo servicio** desde el
>    mismo repo de GitHub, con **Root Directory = `rag/`** (para que use el
>    Dockerfile de esa carpeta). Ponle de nombre `rag`.
> 2. Añadir un **Volume** a ese servicio montado en `/data` (ChromaDB persiste en
>    `CHROMA_PATH=/data/chroma`), para que el índice no se pierda en cada deploy.
> 3. Poner en el servicio `rag` la variable `ANTHROPIC_KEY` (la misma que uso en
>    el servicio principal).
> 4. En el **servicio principal**, setear `RAG_URL` al dominio privado interno
>    del servicio rag: `RAG_URL=http://${{rag.RAILWAY_PRIVATE_DOMAIN}}:8080`
>    (o el puerto que Railway asigne; ayúdame a confirmarlo).
> 5. Tras el deploy, **indexar las empresas** en el Second Brain (el servidor
>    principal tiene un endpoint de indexación que llama a `/index/company`, o se
>    puede usar `rag/indexer.py`). Dime exactamente cómo dispararlo.
> 6. Verificar que 🩺 → “Second Brain (RAG)” pase a **OPERATIVO** y que Bixby
>    pueda responder con contexto del Second Brain.
>
> ## 2) Neo4j (Grafo Temporal) — arreglar credenciales
> El diagnóstico da `Neo.ClientError.Security.Unauthorized` (auth incorrecta).
> Guíame para: resetear la contraseña en Neo4j Aura (console.neo4j.io →
> Instances → “…” → Reset password), copiar la nueva, y actualizar en Railway
> (servicio principal) `NEO4J_PASSWORD`, confirmando que `NEO4J_USER=neo4j` y que
> `NEO4J_URI` empiece con `neo4j+s://`. El código de persistencia ya está listo;
> es solo config. Verifica que 🩺 → “Grafo Temporal” pase a OPERATIVO / badge
> “neo4j 🟢”.
>
> ## 3) Finnhub — llave inválida
> El diagnóstico da `Finnhub HTTP 429 — key inválida o rate-limited`. Los precios
> ya funcionan con las fuentes de respaldo (FMP/MarketStack/AlphaVantage), así que
> esto es baja prioridad. Guíame para revisar/regenerar la `FINNHUB_KEY` en
> finnhub.io y actualizarla en Railway, y verificar en 🩺.
>
> ## Cómo verificar todo
> La app tiene un panel de diagnóstico en vivo (icono 🩺 / “Diagnóstico”). Ábrelo
> tras cada cambio: cada servicio muestra OPERATIVO (verde) o FALLA (rojo) con el
> motivo. El objetivo es dejar en verde: Voz (Bixby), MiroFish, Second Brain,
> Grafo Temporal y Fuentes de respaldo. Finnhub puede quedar en rojo sin problema.
>
> Empecemos por el punto 1 (Second Brain), que es el que requiere más pasos.
> Hazme las preguntas que necesites.

---

## Notas para ti (el dueño) — NO es parte del prompt
- **Reparto de trabajo:** Claude Code (esta otra ventana) sigue puliendo el
  código de la app; Cowork solo hace la config de Railway/Neo4j/Finnhub. Así no
  chocan.
- El Second Brain es **opcional**: la app funciona sin él. Si tu reunión es
  pronto, prioriza Neo4j (punto 2, más rápido) y deja el RAG para después.
- Cuando termines, dime aquí cómo quedó el diagnóstico y cierro cualquier detalle.
