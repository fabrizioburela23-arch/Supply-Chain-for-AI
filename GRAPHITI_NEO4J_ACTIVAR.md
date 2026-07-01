# Activar Neo4j + Graphiti (Grafo Temporal persistente)

## ⚠️ Antes de nada — lo que TÚ tienes que hacer (no Cowork)

Graphiti **no se deploya** (es una librería Python que ya corre dentro de tu Flask).
Neo4j **sí** necesita estar hosteado. Hazlo así, es gratis:

### 1. Crear Neo4j Aura (10 min, gratis)
1. Entra a https://neo4j.com/cloud/aura-free/ → **Start Free**.
2. Crea una instancia **AuraDB Free**.
3. Al crearla te muestra UNA VEZ un archivo con:
   - `NEO4J_URI` (algo como `neo4j+s://xxxxx.databases.neo4j.io`)
   - `NEO4J_USERNAME` (normalmente `neo4j`)
   - `NEO4J_PASSWORD` (una clave larga generada) → **GUÁRDALA, no se vuelve a mostrar**.

### 2. Pegar las 3 variables en Railway
En Railway → tu servicio principal → **Variables** → añade:
```
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<la clave que guardaste>
```
(Asegúrate que `ANTHROPIC_KEY` también esté puesta — Graphiti la usa para extraer entidades.)

### 3. Pásale a Cowork el prompt de abajo (agrega la librería + verifica)

---

## PROMPT PARA CLAUDE COWORK

> Estoy trabajando en el repo **Supply-Chain-for-AI** (Khipus AI Finance), un
> Flask de un solo archivo (`server.py`) desplegado en Railway. Ya existe el
> andamiaje del Grafo de Conocimiento Temporal y quiero **activar la
> persistencia con Graphiti + Neo4j**. NO reconstruyas nada: el scaffolding ya
> está. Haz solo lo necesario para encender el modo `neo4j`.
>
> **Contexto que ya existe (no lo dupliques):**
> - `server.py` ya tiene: `NEO4J_URI/USER/PASSWORD` (env vars),
>   `_graphiti_available()`, `_temporal_mode()` (devuelve `'neo4j'` si hay
>   credenciales + librería, si no `'native'`), y los endpoints
>   `/api/grafo/estado`, `/api/grafo/episodios` (POST), `/api/grafo/facts`,
>   y `_graphiti_add_episode(fact)` (envuelve una llamada async con
>   `asyncio.run`). El front (`engine/temporal-graph.js`) ya consume
>   `/api/grafo/estado` y muestra el badge de "memoria: neo4j 🟢".
> - Graphiti es una **librería** que corre dentro de este mismo Flask; NO es un
>   servicio aparte, NO agregues un nuevo servicio ni Dockerfile.
>
> **Tareas concretas:**
> 1. Agrega `graphiti-core[anthropic]` a `requirements.txt` (revisa que no rompa
>    versiones: el proyecto usa Flask sync + gunicorn). Fija una versión estable
>    reciente y comprueba que sus deps (incluye el driver `neo4j`) sean
>    compatibles con el resto de `requirements.txt`.
> 2. Revisa `_graphiti_add_episode(fact)` en `server.py`: confirma que llama a
>    `Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)`, hace
>    `await graphiti.build_indices_and_constraints()` **una sola vez** (idempotente,
>    cachea que ya se hizo), y luego `add_episode(...)` con el `fact` como
>    `EpisodeType.text` o `.json`. Que sea robusto: si Neo4j no conecta, cae a
>    modo nativo sin tumbar el request (log del error, no 500).
> 3. Envolver `asyncio.run(...)` en Flask sync está bien, pero verifica que no se
>    llame dentro de un event loop ya activo. Si hace falta, usa un
>    `asyncio.new_event_loop()` dedicado o `nest_asyncio`.
> 4. Al arrancar (o en el primer `/api/grafo/estado`), si el modo es `neo4j`,
>    **ingesta los 24 hechos semilla** de `nodes/temporal_seed_facts.js` a Neo4j
>    una sola vez (chequea un marcador para no duplicar en cada reinicio).
>    Como es un `.js`, extrae los datos con un pequeño parse o mantén una copia
>    de los hechos semilla en Python — lo que sea más limpio.
> 5. Prueba local con un Neo4j de prueba (o mockea el driver) y confirma que
>    `/api/grafo/estado` devuelve `{"store":"neo4j","neo4j_connected":true}`
>    cuando las credenciales existen, y `"native"` cuando no.
> 6. **Hazme preguntas antes de tocar** cualquier cosa fuera de `requirements.txt`
>    y la función `_graphiti_add_episode` / la ingesta semilla. No cambies el
>    front salvo que sea imprescindible. Desarrolla en una rama, commitea con
>    mensajes claros, y NO abras PR salvo que te lo pida.
>
> **Criterio de éxito:** tras poner las 3 env vars en Railway y desplegar, el
> badge del Grafo Temporal muestra "memoria: neo4j 🟢", los hechos persisten
> entre reinicios, y si Neo4j se cae la app sigue funcionando en modo nativo.

---

## Qué NO necesitas
- ❌ Deployear Graphiti como servicio → es una librería, va dentro del Flask.
- ❌ Un segundo contenedor / Dockerfile nuevo.
- ❌ Migrar datos manualmente → los hechos semilla se ingestan solos.

## Cómo sabrás que funcionó
Abre la pestaña **◈ Grafo Temporal** → el badge arriba a la derecha pasa de
"memoria: nativa" a **"memoria: neo4j 🟢"**.
