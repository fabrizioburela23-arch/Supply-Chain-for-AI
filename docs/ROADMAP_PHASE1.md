# ROADMAP — Phase 1: Live Investment Graph V1

Milestones derivados de la auditoría en `docs/ARCHITECTURE.md`. Cada uno es
**aditivo**, tiene tests, y deja la app desplegable al terminar.

Estado global: **M1 y M2 (núcleo) completos**. M3-M6 planificados.

---

## M1 — Capa de procedencia ✅ COMPLETO

> Spec §5 (*"NINGÚN hecho importante debe existir sin poder conocer su
> origen"*) y §14 (calidad de dato). Va primero porque **todo lo demás la
> referencia**: sin procedencia, los agentes de Fase 2 no pueden razonar sobre
> calidad de evidencia, y la ingesta automática llenaría el grafo de hechos
> sin origen.

- [x] `Source` como entidad de primera clase — el tipo **ya estaba declarado**
      en `vocabulary.json` sin ningún código detrás; M1 le pone el motor.
- [x] `ontology/provenance.py`: `register_source()` con deduplicación estable
      por URL (`src_<sha1[:12]>`), `source_trust()` leyendo el `source_kinds`
      del vocabulario, `provenance_for_object()`.
- [x] `Event.source_id` + `Event.confidence` (columnas aditivas, con ALTER
      idempotente porque `create_all` **no** añade columnas a tablas que ya
      existen).
- [x] `apply_event()` acepta `source_id`/`confidence` sin romper llamadores.
- [x] `crear_tesis` registra cada `FuenteCitada` como entidad `Source`, la
      enlaza (`evidenced_by`) y **mete los ids de fuente en el evento
      `ActionExecuted`** — antes la evidencia no llegaba al rastro auditable.
- [x] Nuevo `rel_type` `evidenced_by` en el vocabulario.
- [x] API: `GET /api/ontology/sources`,
      `GET /api/ontology/objects/<id>/provenance`.
- [x] **Bug corregido**: los campos `fuente` de varias Acciones admitían 200
      caracteres y se volcaban a `Event.source`, que es `String(60)` →
      truncamiento/error de escritura.

## M2 — Identidad de entidad ✅ NÚCLEO COMPLETO

> Spec §8. Va segundo porque la ingesta automática (M4) necesita saber a qué
> entidad pegar un hecho sin duplicar.

- [x] **`NODE_ID_ALIAS` ya cruza la frontera cliente→servidor.** Era el defecto
      raíz: el exportador la usaba como ENTRADA del merge pero no la incluía en
      `data/grafo_v0.json`, así que ni la migración ni el servidor la veían.
      Ahora se exporta (81 alias) y el snapshot sigue dando 949 nodos / 2.526
      links, idénticos.
- [x] **Un solo resolvedor server-side** (`core/entities.py`) que reemplaza a
      los tres divergentes. Escalera auditable: id 100 · ticker 98 · label 95 ·
      alias 92 · sufijo societario 88-90 · prefijo único 70 · subcadena única 60.
      Un prefijo/subcadena **ambiguo no resuelve**: dos candidatos = ninguno.
- [x] **Devuelve CÓMO resolvió**, no solo qué: `{id, score, method, matched}`.
      Sin el método no se puede auditar por qué un texto acabó en una entidad.
- [x] **Dos umbrales distintos a propósito**: `UMBRAL_ESCRITURA=85` (solo
      exacto/ticker/alias) y `UMBRAL_BUSQUEDA=60`. Un match flojo al escribir
      en la ontología la corrompe en silencio; al buscar solo molesta.
- [x] **`ontology/agents.py:_resolve` usa el resolvedor único.** Es el camino
      que consume nombres GENERADOS POR UN LLM: antes solo probaba slug y label
      exacto, así que "NVIDIA Corporation", "NVDA" o "AWS" fallaban en silencio
      y el hecho se perdía. Confirma contra la base antes de devolver.
- [x] `external_ids` estructurado: `parse_ticker()` separa el campo sucio del
      catálogo (`'RGTI · Nasdaq'`) en `{ticker, exchange}`.

Pendiente de M2 (no bloquea a M3/M4):

- [ ] Persistir `aliases[]` y `external_ids{}` en las propiedades de cada
      objeto durante la migración (hoy el resolvedor los lee del snapshot).
- [ ] CIK/ISIN/LEI: hoy CIK se resuelve ad-hoc contra SEC y se descarta;
      ISIN y LEI no existen.
- [ ] Persistir la decisión de resolución (método+score) cuando un agente
      escribe, para poder medir falsos positivos.
- [ ] Enriquecer alias con nombres legales completos: "Taiwan Semiconductor"
      no resuelve porque el catálogo llama a esa empresa solo "TSMC", y el
      resolvedor —correctamente— prefiere no adivinar.
- [ ] Matches de baja confianza → cola `ProposedAction` (el patrón ya existe).

## M3 — Interfaces de proveedor

> Spec §7. `core/providers/__init__.py` ya describe este patrón y cita un
> `base.py` **que no existe**; solo CoinGecko pasa por ahí.

- [ ] `core/providers/base.py`: `MarketDataProvider` (`get_quote`,
      `get_history`, `subscribe_quotes`) y `NewsProvider` (`get_latest`,
      `search`, `subscribe`) + esquemas unificados.
- [ ] Adapters de equities (Finnhub, FMP, Yahoo) detrás de la interfaz; el
      resto del sistema deja de conocer al proveedor.
- [ ] Cada respuesta lleva `as_of` — hoy los quotes no exponen su frescura.
- [ ] Modo "configuración pendiente" explícito cuando falta una key: nunca
      datos simulados presentados como reales.

## M4 — Ingesta de eventos al grafo

> Spec §6 y §10. Depende de M1 (procedencia) y M2 (identidad).

- [ ] GDELT y SEC dejan de ser passthrough: las noticias se normalizan a
      `NewsItem` (tipo ya declarado en el vocabulario) con su `Source`, y se
      enlazan (`reports_on`, ya en el vocabulario) a las entidades que
      mencionan.
- [ ] `CorporateEvent` N-ario (earnings, M&A) sobre la abstracción de
      hiperaristas que **ya existe** (`Factor` + `affects`), sin esquema nuevo.
- [ ] Bus de eventos interno con suscriptores, preparado para streaming.
      Hoy la ingesta es por corrida manual (`/api/ontology/agents/run`) —
      decisión deliberada: gunicorn con 1 worker no admite scheduler interno.

## M5 — Completar la Graph API

> Spec §11. Lo que falta sobre lo que ya existe.

- [ ] `GET /api/ontology/search` server-side (hoy la búsqueda es solo cliente).
- [ ] `GET /api/ontology/events/<id>`.
- [ ] `GET /api/ontology/objects/<id>/timeline` — fusión de eventos del grafo +
      noticias + movimientos de precio en una sola línea de tiempo.
- [ ] Filtros temporales uniformes (`as_of`) en todo lo anterior.

## M6 — UI del grafo vivo

> Spec §12 y los criterios de éxito.

- [ ] Panel de procedencia en la ficha de entidad: de qué fuente salió cada
      dato, con enlace a la evidencia original. Hoy la evidencia solo es
      clicable mientras la propuesta está pendiente y **se pierde al aprobarla**.
- [ ] Feed de eventos en vivo.
- [ ] Línea de tiempo por entidad.
- [ ] Mostrar frescura por dato (hoy solo el precio tiene el linaje ⓘ).

---

## Fuera de alcance de Phase 1 (spec §20)

Broker execution, trading automático, recomendaciones de inversión,
optimización de cartera, MCP, enjambre de agentes.

**Nota:** el trading **en papel** (Alpaca + PIN obligatorio + confirmación
explícita) **ya existía** antes de esta fase. No se amplía ni se conecta a
nada nuevo aquí.

---

## Deuda conocida que Phase 1 NO resuelve

- `apply_event()` no valida `type`/`rel_type` contra el vocabulario: cualquier
  tipo entra por la puerta principal. `justified_by` ya está persistido en la
  base sin estar en el vocabulario. *(Candidato a M2.)*
- Rework de escala del cliente antes de superar ~2.500 nodos
  (`docs/ESTADO.md`).
- La fórmula NRS del cliente no acota el término de margen; la réplica
  server-side sí. Divergencia documentada.
- `app.html` sigue siendo un archivo de ~10.000 líneas.
