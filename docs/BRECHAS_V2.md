# BRECHAS v2 — qué falta para que Khipus esté bien en código y en matemática

*Auditoría del 2026-10-12 contra `docs/ARQUITECTURA_V2.md`. Cinco lentes independientes (motores de simulación,
matemática financiera, datos y tiempo, contexto de la IA/MCP, estructura del código) leyeron y EJECUTARON el código
real; cada hallazgo lo intentó refutar un segundo revisor que volvió a medir. Resultado: **99 hallazgos** (4 críticos,
27 altos, 41 medios, 27 bajos) — **0 refutados**, 28 con la gravedad o las cifras ajustadas por el verificador, 16
encontrados por los verificadores. Las secciones A-E tienen cada hallazgo con evidencia (archivo:línea y números) y
su arreglo; los campos técnicos de algunos lentes están en inglés.*

---

## 1. En simple (para Fabrizio)

**Lo que ya está bien (medido, no supuesto):** la matemática de base es correcta — Black-Scholes y sus griegas
(paridad put-call exacta), VaR paramétrico e histórico, prueba de Kupiec, paridad de riesgo (las contribuciones suman
exactamente la volatilidad), radio espectral y convergencia del motor, impacto que crece con la severidad, motor denso
= disperso, UNA fórmula NRS, quórum del comité, calendario de la bolsa de Nueva York. La suite completa pasa (1.942
pruebas con base de datos) y ninguna prueba usa la red.

**Lo que falta, agrupado en 5 problemas de fondo:**

1. **La misma pregunta da números distintos según la pantalla.** Un choque en TSMC afecta a 164, 217, 246, 263, 273,
   293 o 315 empresas según qué botón uses: hay **siete** cálculos de contagio con reglas distintas (el del servidor,
   el instantáneo de la Cabina/X-Ray, el del banner de estrés, el tensor, la sala de guerra, el de escenarios y el de
   la simulación por agentes, donde los % los escribe la IA). Además, al "disparar" una crisis el golpe sale al 160 %
   (la severidad de los factores está en escala 0-10 y la fórmula divide por 5). → **Un solo motor** (A).
2. **El guardián de cifras deja pasar números falsos.** No reconoce precios escritos como "233,95 USD" o "233.95
   dólares" (el formato que el propio chat usa), acepta cualquier cifra a ±15 % de algún número del contexto (si el
   precio real es 180,20, "$205" pasa) y solo revisa dinero: porcentajes, múltiplos y crecimientos inventados no se
   controlan. → Es lo más urgente para el inversionista (D: L4-02, L4-M1; B: L2-04).
3. **Khipus no tiene memoria de los números.** No se guarda la historia de precios, tipos de cambio, posiciones ni
   métricas. Consecuencias medidas: se aplica el tipo de cambio de HOY a toda la historia (el riesgo cambiario de un
   inversor en dólares desaparece), no hay correlaciones ni factores, no se pueden calibrar los escenarios a pérdidas
   en dinero, y "¿cómo cambió mi exposición?" no tiene respuesta. → Fase 1 #1-3 (C: L3-01, L3-14; B: L2-01, L2-12).
4. **Los datos del grafo tienen errores que la matemática amplifica.** Dos escalas de peso mezcladas (0-1 y 1-6:
   400 vínculos cuentan la importancia del tipo DOS veces), 97 % de los vínculos sin fecha real (el "viaje en el
   tiempo" devuelve el grafo de hoy), direcciones invertidas que la auditoría no detecta ("X usa Y"), 27 vínculos con
   fecha que entran como "suministro" aunque son inversiones o contratos de energía, y empresa = acción (TSMC tiene
   2330.TW y el ADR TSM, pero Khipus guarda uno solo). → Revisión contigo (C: L3-02, L3-11, L3-12, L3-13).
5. **El dinero y el despliegue tienen caminos sin los mismos controles.** Hay tres caminos que mandan órdenes a la
   MISMA cuenta de Alpaca con controles distintos: `/api/trade/order` y `/api/trade/close` no pasan por los límites de
   riesgo del bróker de clientes; y ningún test corre antes de desplegar (cada push a `main` sale a producción sin
   pasar la suite). → E: G5-01, M-code-03, G5-02.

Además (menos urgente): el motor de contexto de la IA sigue repartido en 9 armadores sin presupuesto (D: L4-01), el
MCP devuelve hasta 112 mil caracteres por consulta y le faltan 7 de las 11 operaciones (L4-08, L4-09), no hay caché
de prompt (L4-06), y los archivos gigantes (`app.html` 12.665 líneas, `server.py` 5.977, `cockpit.js` 4.991) hacen
lento y riesgoso cada cambio (E: G5-05/06/07).

---

## 2. Lo que necesito de ti (decisiones, revisiones, cuentas)

Nada de esto lo decido yo: son decisiones de negocio, de dinero o de datos que solo tú puedes marcar.

| # | Qué | Por qué | Hallazgos |
|---|---|---|---|
| 1 | **Límites de tu cuenta de bróker**: tope diario en USD, % máximo por empresa y por sector (sugerido 30-40 %), y si tu cuenta puede operar con dinero real | sin esto no puedo poner el mismo control de riesgo en todos los caminos de órdenes | G5-01, M-code-03, L2-M3 |
| 2 | **Railway → activar "Wait for CI"** (o desplegar desde una rama protegida) y **confirmar que `SECRET_KEY` existe** y es larga y aleatoria | para que nada llegue a producción sin pasar las pruebas | G5-02, G5-18 |
| 3 | **OK para guardar 5 años de precios** en el Postgres actual (~720 mil filas, ~100 MB en 10 años; descarga gratuita de Yahoo, unas horas) | es la base de todo lo que dependa del tiempo | L3-01, L2-12 |
| 4 | **¿Socios y accionistas transmiten daño en una caída?** (recomendación: NO por defecto; se muestran aparte como "relacionadas") | hoy unos motores sí y otros no | PROP-07, L4-03, M-code-01 |
| 5 | **Escala de severidad de los factores = 0-10** (como en el documento multicapa) | para corregir el golpe al 160 % | PROP-05 |
| 6 | **¿Dar de baja Neo4j Aura** y borrar `NEO4J_URI/USER/PASSWORD`? (nadie lo lee) | una copia menos del grafo y una factura menos | L3-10, G5-12 |
| 7 | **¿Postgres de producción manda sobre el catálogo?** (recomendado) y revisar una vez el plan de reconciliación | hoy hay tres copias vivas del grafo | L3-09 |
| 8 | **Revisar listas que yo preparo** (tú solo marcas ✔/✘): 27 vínculos con fecha (tipo y dirección), 9-15 direcciones sospechosas, la conversión de pesos (sobre todo 462 vínculos con peso 1), el significado de "controla / alberga / domina" | nada del grafo se cambia sin tu marca | L3-02, L3-03, L3-11, L3-12, PROP-14 |
| 9 | **Precio de referencia** de 16 empresas con varios listados y 28 con certificado OTC (acción local o ADR en dólares) | empresa ≠ instrumento | L3-13 |
| 10 | **Fechas**: aprobar las fechas propuestas (con fuente) para los ~200 vínculos más pesados y fundación/salida a bolsa de las empresas principales | sin fechas el grafo temporal responde "no sé" | L3-04, DT-M2 |
| 11 | **Episodios históricos para calibrar** escenarios → dinero (p. ej. escasez de chips 2021, controles de exportación oct-2022, terremoto de Taiwán abr-2024) | para traducir "TSMC cae" a "tu cartera pierde X ± Y" | L2-13 |
| 12 | **API de pago `/v1/risk/portfolio`**: OK para que cambien sus NÚMEROS (no su formato) al usar el cálculo correcto | hoy calcula el VaR con pesos al costo y series sin alinear | L2-02 |
| 13 | **Historial de predicciones**: ¿recalificar con un método v2 en paralelo (sin borrar el viejo)? | la banda fija de ±2 % y el Brier sobre algo que no es probabilidad | L2-07 |
| 14 | **Agente de trading tras un despliegue**: ¿se reanuda solo (solo en papel) o queda apagado con aviso? | hoy se apaga en silencio y pierde su configuración | G5-10 |
| 15 | **Orden de las operaciones MCP que faltan** (sugerido: run_scenario, get_subgraph, get_exposure primero) | 7 de 11 no existen | L4-09 |

---

## 3. El orden en que lo haría

Cada bloque = commits pequeños, cada uno con su prueba que fallaba antes (como en la misión de reparación).

| Bloque | Qué | Necesita de ti | Hallazgos principales |
|---|---|---|---|
| **0. Cifras y despliegue seguros** (1-2 días) | guardián de cifras: formatos "233,95 USD"/"dólares", tolerancia por TIPO de cifra con fuente cercana (no todo el prompt), también %, múltiplos y crecimientos; prueba automática en GitHub antes de desplegar; quitar el "55 %" inventado del X-Ray; la simulación por agentes toma los % del motor, no de la IA; la reducción a la mitad del tamaño "no validado" se aplica siempre | #2 (solo el interruptor de Railway) | L4-02, L4-M1, L2-04, G5-02, PROP-04, L4-04, PROP-10, L2-05 |
| **1. Un solo motor de contagio** | `matrix/engine.propagate` como única matemática; el navegador lo consulta o lo replica con prueba de paridad sobre los 937 choques; borrar `computeDownstream`, la BFS de escenarios y el respaldo de la sala de guerra; misma regla de socios en todos | #4, #5 | PROP-01..03, 05..07, 09, 11, 13, 17..20, G5-03/04, M-code-01/02, L4-03, L4-M2 |
| **2. Memoria de los números** (Fase 1 #1-3) | tabla de precios EOD + relleno de 5 años + ingesta diaria; tipos de cambio diarios; fotos diarias de métricas y posiciones; instrumentos (empresa ≠ acción); todo el riesgo y los técnicos leen de ahí (cierres ajustados, RSI de Wilder) | #3, #9 | L3-01, L2-12, L3-14, L2-01, L3-13, L2-03, L2-11, L2-M1 |
| **3. Un solo camino de órdenes** | los tres caminos a Alpaca pasan por los mismos controles (límites, client_order_id, auditoría); `/api/trade/close` también | #1, #14 | G5-01, M-code-03, G5-08, G5-10 |
| **4. Un solo motor de contexto + MCP + caché** (Fase 1 #5-7) | `core/context_engine.py` con relevancia y presupuesto; contrato MCP con `detail`/`max_chars`; las operaciones que faltan; caché de prompt con costos de caché separados; sin respuestas escritas dos veces | #15 | L4-01, L4-05..L4-11 |
| **5. Calidad de datos del grafo** (Fase 1 #8, con tu revisión) | escala única de pesos [0,1], detector de dirección por texto, mapear verbos en español, reconciliación con Postgres como verdad, retirar Neo4j | #6, #7, #8, #10 | L3-02, L3-03, L3-09..L3-12, PROP-14 |
| **Fase 2+** | grafo bitemporal G(t, κ), historia de propiedades, Δθ en el diff, disparador append-only; factores, EWMA, Ledoit-Wolf, CVaR multi-día; escenario → P&L con κ calibrado; dividir los archivos gigantes | #11, #12, #13 | L3-04..L3-08, L2-07, L2-13..L2-16, G5-05..G5-07 |

**Mi recomendación**: empezar YA por el bloque 0 (no necesita decisiones tuyas salvo el interruptor de Railway) y
el bloque 1 (necesita solo tus respuestas a #4 y #5). Los bloques 2 y 3 arrancan apenas tengas las respuestas #1 y #3.

---

## 4. Detalle verificado por área

### A. Motores de simulación (kernel de propagación) — 20 hallazgos

**PROP-01 · CRÍTICO · both · Fase 1 · esfuerzo M** — Seven engines give seven different answers for the same TSMC collapse  
- *En simple:* Hoy la misma pregunta («¿qué pasa si cae TSMC?») da entre 164 y 315 empresas afectadas según la pantalla que mires. Un inversionista no puede confiar en un número que cambia según el botón.
- *Hoy:* TSMC collapse at severity 100 reaches a different number of companies (impact of 1% or more) depending on the screen. Server propagate (matrix/engine.py:427) with production latent factors: 315. Server without factors: 293. livesim with latent factors (engine/livesim.js:155): 263. Tensor Ψ (matrix/tensor.py:166): 246. War Room fallback (app.html:8823): 273, of which 208 are shown at 2% or more. Cockpit stageSim and …
- *Debe ser:* v2 §7 ('Un solo kernel') and §20.1 #4: one kernel. The client either calls the server or replicates it, with a parity test over all 937 shocks. scenario_engine only seeds the shock and then uses the same kernel.
- *Evidencia:* /tmp/audit_propagation/{server_kernel.py,client.js,compare.py,factors.py,client_lat.js} on data/grafo_v0.json (937 nodes / 2510 links) and data/multicapa_factors_seats.json (69 factors at latent 1.0). Output: server 293 (top5 Nvidia 61.09, Apple 60, Groq 60, Tesla 55, AMD 50); latent 315; Ψ 246; client 217 (top5 Nvidia 60, Apple 60, AMD 50, MediaTek 50, Bro…
- *Arreglo:* Make matrix.engine.propagate the only math. The client asks /api/matrix/impact, or ports the kernel with the same params, factors and cap. Add a test that runs all 937 single-node shocks in node and in python and requires max|Δ| < 1e-6. Delete or redirect the other paths (PROP-02/03/09/11).
- *Verificación:* confirmed

**PROP-02 · ALTO · both · Fase 1 · esfuerzo M** — statematrix.js (cockpit, X-Ray, livesim) uses different math from the server kernel  
- *En simple:* La simulación instantánea de la Cabina y del X-Ray calcula distinto que el servidor: a algunas empresas les marca la mitad del golpe (40 % contra 20 %). Hay que dejar una sola cuenta.
- *Hoy:* engine/statematrix.js has six differences from the server. (1) It combines incoming edges with MAX, 'eslabón más débil' (line 132), where the server SUMS them (Tᵀx at matrix/engine.py:459). (2) It has no 1% threshold; the server has one at engine.py:463. (3) It has no FRAGILITY_CAP (line 105). (4) It runs 8 iterations, not 6 hops. (5) The shocked node keeps re-emitting every iteration (line 126); on the server it is…
- *Debe ser:* v2 §20.1 #4: the client uses the server kernel (sum, 6 hops, threshold, fragility cap) or replicates it with a parity test over 937 shocks.
- *Evidencia:* compare.py: of the 211 nodes both engines reach for TSMC, max diff 20 pp, mean 2.25 pp, 15 differ by more than 10 pp (Esperanto 40 vs 20, MPWR 50 vs 30, SiliconLabs 40 vs 20, Groq 60 vs 40). Over all 937 shocks (allnodes.py): Spearman 0.868 for reach, top-10 chokepoint overlap 8/10, mean reach 6.59 server vs 10.01 client. 6 nodes reached only by the client …
- *Arreglo:* Port propagate exactly: sum aggregation, threshold 0.01, cap 2.5, 6 hops, non-persistent x0, partner symmetric, and REL_W/SOLE_LINK_FLOOR read from /api/vocabulary or generated from vocabulary.json. Or replace the instant call with /api/matrix/impact plus a cache. If the server kernel gets a 'direction' parameter (row-normalized customers matrix), the 'up' …
- *Verificación:* adjusted — Real, and high severity is correct, but two of the six listed differences have no numeric effect and one root cause is missing. (4) Iteration count does not matter: the client stabilizes at iteration 4 (frames 1,79,195,216,218,218…), and 6, 8 and 20 iterations give identical output. REL_W (statemat…

**PROP-03 · ALTO · both · Fase 1 · esfuerzo S** — computeDownstream: a separate binary cascade still drives the stress banner, brief, insights and X-Ray fallback  
- *En simple:* El banner de «prueba de estrés» del mapa y el brief matinal usan una regla vieja de sí/no que casi no coincide con el motor real (solo 1 de las 10 empresas más críticas coincide).
- *Hoy:* app.html:3702-3734 is an on/off failure model. A company fails if it loses at least 50% of its incoming weight, or if it has a fab/supply link with w≥5. It only looks at supply/fab/license/cloud and ignores conf, criticality and damping. Callers: activateStress (app.html:3748), the StressAI prompt (7127), engine/brief.js:164, engine/insights.js:155, engine/secondbrain.js:201 and engine/xray.js:597.
- *Debe ser:* v2 §7/§20.1 #4: a single kernel. Cascade counts must come from the same propagate.
- *Evidencia:* client.js + allnodes.py over 937 shocks: Spearman between server reach and computeDownstream = 0.393. Top-10 overlap = 1/10: its top-10 is ASML, Ajinomoto, EvergreenMarine, HMM, NipponElectricGlass, SKHynix, TSMC, WanHai, YangMing, Zeiss. 82 companies have 0 local cascade but 10 or more affected in the server kernel. TSMC: 164 vs 293.
- *Arreglo:* Replace computeDownstream with the unified kernel (count of impacts ≥ threshold, plus magnitude) and delete it. brief.js and insights.js should read /api/matrix/metrics, or the ported kernel when there is no DB.
- *Verificación:* adjusted — The math divergence is real; I reproduced Spearman 0.393, top-10 overlap 1/10, 82 nodes with 0 local cascade but ≥10 on the server, and TSMC 164. The scope claim is overstated. engine/brief.js:207 uses computeDownstream only when /api/matrix/metrics fails, and engine/insights.js:281-283 drops the c…

**PROP-05 · ALTO · math · Fase 1 · esfuerzo S** — Factor severity scale is 0-10 in the data but the math divides by 5; fired shocks exceed 100%  
- *En simple:* Al «disparar» una crisis (por ejemplo Taiwán), el sistema golpea con 160 % de fuerza en vez de un máximo de 100 %, y muestra muchas más empresas dañadas de las que corresponde (137 en promedio en vez de 87).
- *Hoy:* data/multicapa_factors_seats.json crisis severities run 4-10 (20×7, 18×6, 14×8, 7×9, 7×5, 2×4, 1×10). scripts/migrate_v0_to_ontology.py:428 even warns 'el documento usa 0-10, no 0-5'. Yet fragility() uses severity/5 (matrix/engine.py:379). /factor/fire sets crisis from severity_crisis, or min(5, 2·sev) when missing (matrix/api.py:880), and then base_mag = crisis/5 (api.py:889), so x0 > 1. Each member's coefficient i…
- *Debe ser:* Impacts and shocks must be fractions in [0,1], with one severity scale shared by data, fragility, fire and actions. The initial vector should be x0_m = mag·coef_m.
- *Evidencia:* fire.py: 60 of 69 factors fire with base_mag between 1.2 and 2.0. Mean reach under the current rule is 137.3 nodes, versus 87.4 with x0 = min(1, mag)·coef. Worst cases: FACTOR_Nexperia 250 vs 60, FACTOR_RareEarth 201 vs 35. server_kernel/factors.py: TSMC at magnitude 1.6 moves Apple from 60.0 to 96.0 and reach from 293 to 318.
- *Arreglo:* Pick one scale. Either divide by 10 everywhere, or rescale severity_crisis to 0-5 through events. Clamp magnitude to ≤1 in /impact and /fire, build x0 per member as mag·coef, and validate ActivarFactor against that scale. Add a test: no propagate input above 1.
- *Necesita de Fabrizio:* Confirmar que la severidad de crisis de los factores está en escala 0-10 (como en el documento multicapa) para fijar una sola escala.
- *Verificación:* confirmed

**PROP-04 · MEDIO · code · Fase 1 · esfuerzo S** — X-Ray shows a made-up constant 55% and mixes three engines on one screen  
- *En simple:* Cuando falla el cálculo, la ficha X-Ray muestra «55 %» para todas las afectadas, un número inventado. Además, la misma ficha mezcla tres cálculos distintos.
- *Hoy:* When the instant and server results are empty, engine/xray.js:601 sets impacts[aid] = 55 for every company computeDownstream returns. The same X-Ray paints the client engine first (217 for TSMC), replaces it with the server's (293), and its 'Estructura' block uses Ψ (246, flow-only, no factors) via /api/tensor/node (xray.js:550).
- *Debe ser:* CLAUDE.md 'NUNCA inventar cifras' and v2 §7: one quantitative layer.
- *Evidencia:* grep: engine/xray.js:601 `list.forEach(function (aid) { impacts[aid] = 55; });`. Reach numbers from PROP-01: 217 / 293 / 246 for the same company on the same screen.
- *Arreglo:* Remove the 55% fallback. If no engine is available, say so. Use one engine (the server kernel with factors) for both the impact list and the structure tiles. If Ψ stays, compute it with the same relation set and fragility.
- *Verificación:* adjusted — Both parts exist in the code, but the 55% fallback is much rarer than implied. xray.js:601 does set impacts[aid]=55. finish(), though, returns early when the instant client result was shown (xray.js:592 'if (shown) return;'). Over all 937 nodes, there are 0 cases where computeDownstream is non-empt…

**PROP-06 · MEDIO · math · Fase 1 · esfuerzo S** — Chokepoint ranking counts companies hit at 1% or more, ignoring how hard they are hit  
- *En simple:* La lista de «empresas cuello de botella» premia a quien toca a muchas empresas un poquito (como PDF Solutions o el banco central de Taiwán) por encima de quien golpea fuerte (como ASML).
- *Hoy:* compute_metrics uses cascade_size = number of impacts with v ≥ 1.0 (matrix/engine.py:651) and chokepoint_rank sorts by that count. A shock that hits 144 companies at 1-10% outranks one that hits 66 companies at up to 40%.
- *Debe ser:* A systemic-importance metric sensitive to magnitude: Σ impacts (expected loss) or cap-weighted Ψᵀc (tensor down_cap already computes it). Count can stay as a secondary field.
- *Evidencia:* choke.py (937 shocks). By count: TSMC 293, Nvidia 205, ARM 201, PDF_Solutions 144 (max impact 10%, 1 node ≥10%), Synopsys 117, Microsoft 113, Amazon 110, Palantir 94, AESCorp 90, CBCTaiwan 85 (max 6%, 0 nodes ≥10%). ASML (max 40%) is not in that top-10. By Σ impacts: TSMC 36.9, Nvidia 19.8, Amazon 14.5, Microsoft 7.6, ARM 5.6, Intel 4.6, Palantir 4.6, Space…
- *Arreglo:* Rank by Σ impacts or by cap-weighted downstream (Ψᵀc). Report the count of nodes ≥10% next to the count ≥1%. Update insights/brief to match.
- *Verificación:* confirmed

**PROP-07 · MEDIO · both · Fase 1 · esfuerzo S** — Partner and investor links transmit damage in the server kernel but not in Ψ (G4 rule)  
- *En simple:* Hoy una alianza o una inversión cuenta como si fuera un proveedor que te deja sin piezas, y eso infla el número de afectadas (47 de 293 en el caso de TSMC).
- *Hoy:* matrix/engine.py builds T from every structural relation (vocabulary.json): partner (weight 0.3, symmetric) and invest (0.25) included. matrix/tensor.py:141 uses flow-only relations, following G4 ('socios e inversores NO transmiten daño de suministro'). The MCP and the NRS degree also treat partner/invest as non-flow.
- *Debe ser:* One relation set for damage propagation, consistent with G4 and v2 §7, used by both the kernel and Ψ.
- *Evidencia:* compare.py: the server kernel without partner and invest reaches exactly 246 nodes for TSMC, the same as Ψ. All 47 extra nodes (293 − 246) come from partner/invest. ρ: 0.8928 with all structural relations vs 0.7505 flow-only. CBCTaiwan (Taiwan's central bank) is the #10 chokepoint only through 'partner' to TSMC (w=5) and Foxconn.
- *Arreglo:* Use flow relations only for damage, or give partner a small non-symmetric weight if Fabrizio wants it. Apply the same set in build_matrices for /impact and /metrics and in Ψ, and re-measure ρ.
- *Necesita de Fabrizio:* Decidir si los socios (partner) y los inversores (invest) deben transmitir daño en una simulación de caída, o solo las relaciones de suministro/fabricación/nube/licencia/energía.
- *Verificación:* confirmed

**PROP-09 · MEDIO · math · Fase 1 · esfuerzo S** — scenario_engine has its own BFS with a non-monotone weight map and no relation types  
- *En simple:* El simulador de escenarios trata un vínculo débil (peso 1) como si fuera crítico y le da el mismo golpe a Nvidia, Apple y AMD. Debe usar el mismo motor que el resto.
- *Hoy:* core/scenario_engine.py:208 maps weights with `max(0.1, min(1.0, w/5 if w>1 else w))`. It propagates over ALL out-links (partner, invest and about included) with no type criticality and no conf. It uses fixed multipliers of 0.7 (hop 1) and 0.45 (hop 2), keeps the top 12 edges and top 10 frontier, cuts at sev<0.08, stops at 2 hops, and adds suppliers at 0.3·w (lines 296-317).
- *Debe ser:* v2 §20.1 #4: scenario_engine only seeds the shock (hit, benefit, sign) and the unified kernel propagates it.
- *Evidencia:* _w: 0.3→0.3, 0.9→0.9, 1→1.0, 2→0.4, 3→0.6, 5→1.0, 6→1.0. The 462 links with w=1 count as critical as w=5. For TSMC, 42 downstream and 8 upstream nodes; Nvidia, Broadcom, Apple, AMD and MediaTek all tie at −0.70 (the server gives 61/43/60/50/50).
- *Arreglo:* Keep detect(), seeds and sign. Call matrix.engine.propagate (snapshot matrices when there is no DB) for the magnitudes, and use 'up' propagation for supplier effects. Remove _w.
- *Verificación:* confirmed

**PROP-10 · MEDIO · both · Fase 1 · esfuerzo M** — Agent simulation: the final % impacts are written by the AI, not computed  
- *En simple:* En la simulación por agentes, los porcentajes de subida o bajada los inventa la IA (con un tope). Deberían salir de una fórmula, y la IA solo debería explicarlos.
- *Hoy:* core/sim_agents.py run loop (ROUNDS=2, line 45) stores state[nid]['pct'] = what the LLM returns, clamped by _clamp_pct to _BOUNDS mega 12 / mid 20 / small 35 % (lines 52 and 259). The structural fallback turns sev into % with fixed bounds (_struct_pct, line 378). Neither is calibrated or comes from the kernel.
- *Debe ser:* v2 §0.5/§13 ('la IA nunca suma ni multiplica'), §20.3 (scenario → calibrated return κ → P&L with bands).
- *Evidencia:* Code: `state[nid] = {'pct': imp.get('pct', prev.get('pct', 0)), ...}` in _run_impl, then `p = _clamp_pct(v['pct'], a['size'])`. No eod_prices or prices_store exists in the repo (grep returns nothing), so κ cannot be calibrated today.
- *Arreglo:* Compute impacts with the unified kernel. Convert impact to % move with an explicit, versioned κ (constant now, calibrated once EOD history exists). The AI only narrates and quotes agents.
- *Verificación:* confirmed

**PROP-11 · MEDIO · code · Fase 1 · esfuerzo S** — War Room fallback calls the client engine with different parameters and claims it is the server math  
- *En simple:* La «sala de guerra» de simulación, cuando no hay IA, usa una versión más agresiva del cálculo y dice que es la misma. Hay que alinearla.
- *Hoy:* app.html:8823 calls KhipuState.simulate(shocks salud 0.2, null, 4 iterations, damping 0.85), keeps impacts of 2 or more and shows the top 60. The comment at app.html:8790 says 'la MISMA matemática que matrix/engine.py'.
- *Debe ser:* Same kernel, same damping 0.6, hops, factors and threshold as the server.
- *Evidencia:* client.js: war room TSMC reaches 273 companies at 1% or more, 208 at 2% or more. Nvidia 68 (server 61.09), Apple 68 (60), AMD 57 (50).
- *Arreglo:* Use the unified kernel with default params, magnitude = scenario severity, and pass the active factors.
- *Verificación:* confirmed

**PROP-14 · MEDIO · data · Fase 1 · esfuerzo M** — Mixed weight scales: 400 links carry the type criticality as their weight, so it is applied twice  
- *En simple:* Unos 400 vínculos tienen el peso anotado en otra escala, así que el sistema los trata como mucho más débiles de lo que son (por ejemplo, la nube de Google para una empresa).
- *Hoy:* Kernel, client and Ψ read w on the 1-6 scale (matrix/engine.py:_eff_weight, statematrix.js:61), but 400 of 2510 links have w<1, equal to the type criticality (cloud 0.9 ×44, license 0.8 ×17, ppa 0.7 ×2, owns 0.6 ×6, deploy 0.4 ×2, partner 0.3 ×263, invest 0.25 ×34, plus supply 0.3-0.7 ×32). Criticality is then multiplied a second time in _dependency_matrix. Another 462 links have w=1, which is ambiguous between the …
- *Debe ser:* v2 §18 / §20.1 #8: one weight scale, with a review list.
- *Evidencia:* Snapshot weight histogram per type (python over data/grafo_v0.json). Example: a cloud link with w=0.9 transmits 0.9/6·0.9 = 0.135, while a cloud link with w=2 transmits 0.3.
- *Arreglo:* Add the scale check to scripts/audit_graph.py and produce a review list. After Fabrizio marks it, rewrite weights through events. Add a ratchet test against the baseline.
- *Necesita de Fabrizio:* Revisar la lista de vínculos con peso menor a 1 o igual a 1 y confirmar su importancia real en la escala 1-6.
- *Verificación:* confirmed

**PROP-17 · MEDIO · math · Fase 1 · esfuerzo S** — Client 'up' propagation (demand, boom) has no SOLE_LINK_FLOOR, so one weak link passes the whole boom upstream  
- *En simple:* En la simulación de «auge de demanda», un proveedor con un solo cliente pequeño recibe el 60 % del auge aunque el vínculo sea débil (por ejemplo, Tesla por OpenAI). Exagera a los ganadores.
- *Hoy:* engine/statematrix.js:84 builds customers[i] with w = e.w / rowSum[e.i] · crit, normalized per type over the supplier's out-weight with no floor, and the kernel takes the MAX. A supplier whose only supply customer is linked at w=1 gets 0.6·1·crit = 60% of that customer's boom, while the downstream path applies the floor of 6 and gives a few percent in the other direction. Cockpit stageSim (cockpit.js:2533, direction…
- *Debe ser:* Floor and normalization rules that match in both directions, or a server kernel with a direction parameter (v2 §7: one kernel).
- *Evidencia:* /tmp/audit_kernel/up.js: 200 suppliers have exactly one supply customer, 152 of them with w≤2. A boom on OpenAI sends Tesla to 60 (link w=1); a collapse of Tesla hits OpenAI by 4. MSCI←AlphaSense is 60 up vs 10 down; NexGenEnergy←Constellation is 60 up vs 2 down.
- *Arreglo:* Apply max(rowSum, SOLE_LINK_FLOOR) to customers. Better, add direction='up' to matrix.engine.propagate using row-normalized Aᵀ with the same floor, and have the client call or port it. Add a parity test.
- *Verificación:* hallado por el verificador

**PROP-18 · MEDIO · both · Fase 1 · esfuerzo M** — Engines read different graphs: /api/matrix uses Postgres, while Ψ, scenario_engine and the client use the 937-node catalog  
- *En simple:* Aunque se unifique la fórmula, unas pantallas calculan sobre la base de datos de producción (1.294 objetos) y otras sobre el catálogo (937). La misma pregunta puede seguir dando números distintos.
- *Hoy:* matrix/engine.py build_matrices (:267-290) reads live LinkRecord rows from Postgres; in production that is 1,294 objects, about 216 of which the repo cannot rebuild. matrix/tensor.py:60/:257 builds Ψ from data/grafo_v0.json. scenario_engine uses semantic._load_snapshot(). The client uses window.LINKS from the catalog merge. Even after the math is unified (PROP-01/02), the same shock will give different numbers on sc…
- *Debe ser:* v2 §7/§20.1 #4: one kernel over one graph. Either every engine reads the same source (server, DB) or a recurring check reports reach and impact Δ between the snapshot and DB for a fixed set of shocks.
- *Evidencia:* matrix/tensor.py:60 `SNAPSHOT = os.path.join(_ROOT, 'data', 'grafo_v0.json')`; tensor.py:257 `Model(snap or _load_snapshot(), …)`; matrix/engine.py:277 `select(LinkRecord).where(LinkRecord.valid_to.is_(None))`; CLAUDE.md: production base 1,294 objects vs 937 catalog nodes. I could not measure the production Δ (no production access).
- *Arreglo:* Build Ψ and scenario magnitudes from build_matrices when DATABASE_URL is set, falling back to the snapshot only without a DB, and label which one was used. Add a daily ops check (core/ops_check) that runs ~20 reference shocks on both sources and stores reach and Σ impact deltas.
- *Verificación:* hallado por el verificador

**PROP-08 · BAJO · math · Fase 1 · esfuerzo M** — Kernel is not monotone: adding a supply edge FROM the failed company can lower other companies' impact  
- *En simple:* En casos raros, agregar que TSMC le vende a otra empresa hace que el sistema muestre a alguien menos dañado si TSMC cae, lo cual no tiene lógica.
- *Hoy:* propagate applies x_k = clamp(α·diag(f)·Tᵀ·x_{k-1}) with x0 present only at hop 0, then takes impact = max over hops (matrix/engine.py:459-472). A new edge raises the column sum and dilutes the other suppliers, which lowers hop-2+ values, while the source does not re-emit.
- *Debe ser:* Exposure to a failed company should never reduce anyone's computed impact. Fragility, severity and edges from impacted nodes should all act monotonically.
- *Evidencia:* mono_edge.py, 300 random added supply edges (w=2) under a TSMC shock. Edge from TSMC: 5 of 85 cases lowered some node, by up to 3.8 pp. Edge from an impacted node: 11 of 99. Edge from an unaffected node: 12 of 100 (this one is intended diversification). Severity monotonicity holds: magnitude 0.1→1.0 reach 143→293, no node decreases (also true in the client).
- *Arreglo:* Use a persistent-source operator, x_k = min(1, x0 + α·diag(f)·Tᵀ·x_{k-1}), iterated to a fixed point. It is monotone and bounded, and converges because αρ<1 at base. Or document dilution as intended and add a property test for edges from shocked or impacted nodes. Re-check the 6-hop equivalence after the change.
- *Verificación:* adjusted — Reproduced (mono_edge.py: 5/85 trials from the shocked node, 11/99 from an impacted node, max drop 3.8 pp). The mechanism is real: x0 is not persistent (engine.py:449-472), and the new edge raises the column sum above the floor of 6. The effect is small and rare, though, and the 12/100 drops for ed…

**PROP-12 · BAJO · math · Fase 1 · esfuerzo S** — No fragility cap in the client, and the server cap of 2.5 sits right at the critical edge  
- *En simple:* Si se encienden muchas crisis a la vez, el cálculo del navegador se «desboca» y marca todo al 100 %. El del servidor queda justo al borde. Falta fijar el tope con una regla clara.
- *Hoy:* matrix/engine.py:fragility caps f at FRAGILITY_CAP=2.5. engine/statematrix.js:105 sums f with no cap. Nothing ties the cap value to the stability condition α·ρ(diag(f)Tᵀ)<1.
- *Debe ser:* v2 §7: an explicit stability criterion (αρ<1, or an explicit 'saturated regime' flag) and the same cap everywhere.
- *Evidencia:* factors.py with 69 factors from multicapa. Latent (sev 1.0): ρ=1.1716, αρ=0.703, 275 nodes with f>1. All at crisis, cap 2.5: ρ=1.6603, αρ=0.996, 76 nodes capped, max raw f 8.72. FRAGILITY_CAP=100 (no cap): ρ=2.7215, αρ=1.633, supercritical. The client with all at crisis has max f 9.79; TSMC reaches 280 with 10 nodes at 100%.
- *Arreglo:* Apply the cap in the client from the same constant (served via /api/vocabulary or a test). Choose the cap so that α·ρ stays below about 0.9 with every factor at crisis, or report 'régimen saturado' when αρ≥1. Add a test on ρ.
- *Verificación:* adjusted — The client cap is genuinely missing: statematrix.js:98-104 has no cap, with max f 9.79 when all factors are at crisis. That is one item of PROP-02. 'The server cap sits right at the critical edge' is true only for the deliberately unrealistic everything-at-crisis case (αρ=0.996 < 1, as the cap was …

**PROP-13 · BAJO · code · Fase 1 · esfuerzo S** — Cockpit and X-Ray ignore the active factors; livesim and the server apply them  
- *En simple:* La Cabina y la simulación en vivo del mapa dan resultados distintos porque una toma en cuenta los riesgos de fondo (factores) y la otra no.
- *Hoy:* engine/cockpit.js:2533 and :4252, and engine/xray.js:540, call KhipuState.simulate(shock, [] …). engine/livesim.js:155 passes the factors from /api/matrix/factors. The server always applies fragility(active_factors).
- *Debe ser:* The same factors in every simulation path.
- *Evidencia:* client_lat.js: TSMC 217 without factors (cockpit, X-Ray) vs 263 with latent factors (livesim). The server gives 293 without and 315 with.
- *Arreglo:* Keep one cached factor list (/api/matrix/factors) and pass it on every simulate call. This disappears if the client calls the server kernel.
- *Verificación:* confirmed

**PROP-15 · BAJO · math · Fase 1 · esfuerzo S** — The 'nonlinear' (severe stress) option lowers impacts instead of raising them  
- *En simple:* La opción de «estrés severo» en realidad hace el golpe más suave. Es un detalle de nombre y fórmula que conviene corregir antes de usarla.
- *Hoy:* matrix/engine.py:460-461 applies cur = 1 − exp(−cur) after the linear step. Since 1−e^{−x} ≤ x, it always attenuates, yet the docstring and /impact describe it as 'escenario estrés severo'.
- *Debe ser:* A severe-stress flag should amplify, or at least not attenuate, the transmitted distress.
- *Evidencia:* TSMC linear: reach 293, Nvidia 61.09. nonlinear=True: reach 290, Nvidia 45.72. No node is higher (any higher = False).
- *Arreglo:* Rename it as a saturating or attenuating option, or replace it with a real amplifying nonlinearity, e.g. a DebtRank-style threshold function. Document it in explain.js.
- *Verificación:* confirmed

**PROP-16 · BAJO · data · Fase 4 · esfuerzo L** — The kernel's hand-set parameters are uncalibrated (no price history to fit them)  
- *En simple:* Los números del motor (cuánto se contagia de una empresa a otra) se pusieron a mano. Para ajustarlos con la realidad hace falta guardar la historia de precios.
- *Hoy:* damping 0.6, REL weights (vocabulary.json), SOLE_LINK_FLOOR 6, threshold 0.01, FRAGILITY_CAP 2.5, max_hops 6 and the factor coefficients are all set by hand. No price history is stored, so they cannot be backtested.
- *Debe ser:* v2 §10 / §20.4: fit the ~12 kernel parameters on real episodes once EOD series exist (§20.1 #1).
- *Evidencia:* grep -rl 'eod_prices|prices_store' --include=*.py returns nothing.
- *Arreglo:* Phase 1 #1 stores EOD series. Phase 4 fits the parameters on 2021+ episodes, versioned, with out-of-sample checks.
- *Verificación:* confirmed

**PROP-19 · BAJO · code · Fase 1 · esfuerzo S** — The kernel's own docstring states the wrong aggregation rule, and the client copied it  
- *En simple:* La explicación escrita del motor dice una cosa y el código hace otra, y por eso la versión del navegador se programó distinta. Hay que dejar la regla por escrito y probarla.
- *Hoy:* matrix/engine.py:432-435 says the total impact is 'el MÁXIMO alcanzado por cualquier ruta (no la suma — evita doble conteo en diamantes)'. The code at :459 computes damping·(DT @ cur), which sums all in-edges within each hop and then takes the max only across hop-lengths. Diamonds of equal length are therefore summed. statematrix.js:118-120 cites matrix/engine.py as 'idéntica' and implements a per-edge MAX. That one…
- *Debe ser:* An explicit written spec of the kernel (aggregation across in-edges, across hops, threshold, cap, x0 persistence) that both implementations and a parity test cite.
- *Evidencia:* /tmp/audit_kernel/maxagg.py: server with SUM reach 293; the same kernel with per-node MAX 245; client 217. Mean |Δ| vs client on common nodes: 2.28 pp (SUM) → 1.66 pp (MAX).
- *Arreglo:* Correct the docstring to 'suma sobre proveedores dentro de un salto, máximo entre saltos'. Write the spec into docs/ARQUITECTURA_V2 §7, and have the parity test from PROP-01 assert it.
- *Verificación:* hallado por el verificador

**PROP-20 · BAJO · code · Fase 1 · esfuerzo S** — Edge cases in factor inputs: severity 0 becomes 5 in the client, and coefficient 0 becomes 1 on the server  
- *En simple:* Si alguien crea un factor de riesgo con fuerza 0, el navegador lo trata como uno fuerte. Hoy no pasa con los datos actuales, pero es una trampa.
- *Hoy:* engine/statematrix.js:101 computes `var sev = (fac.severity || 5) / 5;`, so a factor with severity 0 (allowed by CrearFactorInput ge=0, ontology/actions.py:154) gets full severity 5 in the client and 0 on the server. matrix/engine.py:304 has `'weight': float(l.weight or 1)` for 'affects' links, so a member coefficient of 0 becomes 1 (+100% sensitivity). The server's default when the severity property is missing is a…
- *Debe ser:* Missing and zero values handled the same way in client and server, with severity 0 meaning no effect.
- *Evidencia:* Code lines cited. The current data has no zero coefficients (range 0.05-1.0 over 505 members), so there is no production impact today; it is a latent trap for CrearFactor and ActivarFactor.
- *Arreglo:* Use `fac.severity != null ? fac.severity : 1` in the client and `l.weight if l.weight is not None else 1` on the server, and align the missing-severity default with FACTOR_LATENT_SEVERITY. Add a unit test.
- *Verificación:* hallado por el verificador

<details><summary>Lo que este lente midió y está BIEN (10)</summary>

- ✔ Server kernel, TSMC collapse (no factors): 293 nodes ≥1%; top5 Nvidia 61.09, Apple 60, Groq 60, Tesla 55, AMD 50; max first-reach hop 3; aggregation sum over in-edges, max over hops; threshold 0.01; cap…
- ✔ Server kernel, TSMC with production latent factors (69 factors, sev 1.0): 315 nodes ≥1%, max hop 4
- ✔ ya arreglado Dense == sparse: max |Δ| = 0.0, identical key sets, ρ identical
- ✔ ya arreglado Speed of 937 shocks with dependency_transpose: 0.35 s (sparse default, Tᵀ built once)
- ✔ Determinism: server: identical output on repeat; client: identical Map
- ✔ Monotone in severity: server reach 143/200/256/286/293 for magnitude 0.1/0.25/0.5/0.75/1.0, no node decreases; client 171→217, monotone
- ✔ Spectral radius, base (all structural): ρ=0.892761, αρ=0.5357 (flow-only ρ=0.7505, αρ=0.4503)
- ✔ Spectral radius with latent factors: ρ=1.1716, αρ=0.703 (275 nodes with f>1)
- ✔ Hop cap 6 justification: 6 vs 12 hops: 0/937 shocks change (base and latent factors); 20/937 change with all factors at crisis (mean reach 21.91→21.96)
- ✔ ||αTᵀ||∞ and in-flow saturation: ||0.6Tᵀ||∞=2.65; 94 nodes with Tᵀ row sum >1 and 29 above 1/0.6 (saturate at the clamp)

</details>


### B. Matemática financiera y estadística — 22 hallazgos

**L2-01 · ALTO · both · Fase 1 · esfuerzo M** — El tipo de cambio de HOY se aplica a toda la historia: el riesgo cambiario desaparece para el inversor en dólares  
- *En simple:* Si tienes acciones de Japón, Taiwán o Europa, la app hoy no cuenta cuánto puedes ganar o perder por el cambio de moneda; tu riesgo real en dólares puede ser mucho mayor que el que ves.
- *Hoy:* core/risk_report.py:159-177: `fx` es un escalar por símbolo ({sym: moneda→USD}, spot de core/quotes._fx_to_usd:86-105, 5d meta.regularMarketPrice) y los retornos se calculan en moneda LOCAL (_returns, línea 84/175). Lo mismo en core/portfolio_ai.py:633-635/697 (vol de exclusión y ERC en moneda local), core/portfolio_report.py:95-96 (value_at(d) usa fx[s] de hoy para cualquier fecha) y research/outcomes.py:305-311 (e…
- *Debe ser:* v2 §9.1: r^USD_t,i = r^local_t,i + r^FX_t,i con la serie histórica {CUR}USD=X alineada por fecha (hoy se aplica el FX de HOY a toda la historia: error para el inversor en dólares).
- *Evidencia:* /tmp/audit_lens2/fx_check.py: acción en JPY plana en yenes, JPY con 0,8 % de vol diaria. build_report reporta vol anual 0.15 % y VaR95 1d 0.016 %; la serie real en USD da vol 11.73 % y VaR95 1d 1.172 % (73x subestimado).
- *Arreglo:* Bajar la serie diaria {CUR}USD=X (misma caché/ventana que fetch_history), multiplicar precio local × FX por fecha ANTES de calcular retornos (o sumar r_FX), y usar esa serie USD en risk_report.compute, portfolio_ai, portfolio_report.value_at y outcomes.score_checkpoint (no-EE.UU.). Test sintético: activo plano + FX con vol conocida → vol reportada = vol del…
- *Verificación:* adjusted — Real, and I reproduced it. fx in core/risk_report.compute (lines 159-177) is one spot scalar per symbol, so returns stay in local currency. portfolio_report.value_at (lines 95-96) uses today's fx for any date. outcomes.score_checkpoint (lines 418-427) subtracts SPY in USD from a local-currency retu…

**L2-02 · ALTO · both · Fase 1 · esfuerzo S** — _portfolio_risk_impl calcula VaR con pesos al costo, series sin alinear por fecha y posiciones sin datos que diluyen el riesgo  
- *En simple:* Hay dos calculadoras de riesgo en la app que dan números distintos, y la vieja (que también se vende por la API pública) puede decirte que casi no tienes riesgo cuando le falta un dato.
- *Hoy:* server.py:4757-4810 (_portfolio_risk_impl), llamado por /api/portfolio-risk (botón var-calc-btn en app.html:9669-9690) y /v1/risk/portfolio (server.py:4983-4993). Pesos = shares×buy_price (costo, línea 4782/4787) no valor actual; las series semanales de cada ticker se suman por POSICIÓN en la lista, no por fecha (min_len, 4792); un ticker sin datos queda en pv pero no en los retornos (pesos no renormalizados); np.st…
- *Debe ser:* Un solo motor de riesgo (core/risk_report) para todo consumidor; pesos a valor de mercado; retornos alineados por fecha; v2 §9.2 VaR/CVaR.
- *Evidencia:* /tmp/audit_lens2/legacy_var.py (server importado, _safe_get simulado): cartera AAA sola → VaR95 6.88 %; añadiendo un ticker SIN datos que es el 99 % del costo → VaR95 0.07 % (100x menos).
- *Arreglo:* Hacer que /api/portfolio-risk y el botón de app.html usen core.risk_report.build_report; para /v1 mantener la FORMA de la respuesta pero calcular con risk_report (excluir y reportar posiciones sin historia, pesos a valor actual, alineación por fecha, ddof=1, Sharpe con ^IRX). Test de paridad entre ambos endpoints.
- *Necesita de Fabrizio:* Aprobar que /v1/risk/portfolio (API de pago, contrato 'intocable') cambie sus NÚMEROS (no su formato) para usar el motor correcto, y avisar a clientes de la API si los hay.
- *Verificación:* confirmed

**L2-04 · ALTO · code · Fase 1 · esfuerzo M** — El guardián solo verifica DINERO: porcentajes, múltiplos, RSI y crecimientos inventados por la IA pasan sin control  
- *En simple:* La IA no puede inventar montos en dólares, pero sí puede inventar porcentajes (márgenes, crecimiento, volatilidad) y la app no lo detecta.
- *Hoy:* core/numbers.py:84-95 borra porcentajes y múltiplos de la evidencia (_RATIO_RX) y check_numbers/unsupported_in:125-160 solo revisan money_mentions. research (claims), core/ai._ai_complete (portfolio_ai:864,1157; portfolio_advisor:343; portfolio_report:199) y el presidente del comité (committee.py:1561) pueden escribir márgenes, P/E, volatilidades o crecimientos que no están en los datos.
- *Debe ser:* Ninguna cifra que la IA presente como dato puede salir de la IA (CLAUDE.md 'GUARDIÁN DE CIFRAS', v2 §13 hechos [F#]): los números los calcula el código y la IA solo los cita.
- *Evidencia:* /tmp/audit_lens2/guard2.py: fuente 'margen bruto 75 %; RSI(14) 55; volatilidad 48 %'. Texto 'El margen bruto es 95 % y el RSI 82, P/E 300x, crece 400 %' → unsupported_in = [] (pasa). 'Ingresos de $500B' → ['$500B'] (sí se detecta).
- *Arreglo:* Añadir un segundo conjunto de valores de evidencia para ratios (%, x, puntos) y una función unsupported_ratios con tolerancia absoluta (±1 punto o ±10 %); aplicarla en check_numbers (rechazo) y en _ai_complete (marca '⚠'). Excluir porcentajes triviales (0 %, 100 %).
- *Verificación:* confirmed

**L2-05 · ALTO · math · Fase 1 · esfuerzo S** — La reducción a la mitad por historial no validado NO ocurre cuando el tope por posición ya limita el tamaño  
- *En simple:* Cuando los analistas todavía no tienen historial comprobado, la app promete invertir solo la mitad, pero en acciones poco volátiles igual propone la cantidad completa.
- *Hoy:* research/committee.py:316-337: validated=False multiplica risk_budget × 0.5 ANTES del tope; target_weight (307-313) = min(rb/vol, max_position). Con el mandato por defecto (rb 2 %, tope 10 %, vol mínima 10 %) cualquier acción con vol < 20 % queda topada en 10 % tanto validada como no.
- *Debe ser:* CLAUDE.md C6: 'sin ≥MIN_N calificaciones por analista → tamaño a la MITAD'; el docstring dice 'el peso objetivo cae a la mitad'.
- *Evidencia:* /tmp/audit_lens2/pf_check.py, compute_sizing('BUY', vol, mandate_from({})): vol 10 % → 10.0 vs 10.0 (ratio 1.0); vol 12 % → 10.0 vs 8.333 (0.833); vol 15 % → 0.667; vol 20 % y 40 % → 0.5.
- *Arreglo:* Aplicar UNVALIDATED_FACTOR al peso objetivo DESPUÉS del tope (tw = min(rb/vol, max_pos) × 0.5) o reducir también max_position; test con vol 10 % que exija ratio 0.5.
- *Verificación:* confirmed

**L2-M1 · ALTO · math · Fase 1 · esfuerzo S** — Beta y correlaciones de acciones asiáticas contra el S&P 500 se calculan con el mismo día calendario aunque Asia cierra ANTES que Nueva York: beta ~0 y VaR subestimado  
- *En simple:* Si tienes acciones de Taiwán, Corea o Japón (como TSMC o Samsung), la app cree que casi no se mueven con Wall Street porque esas bolsas cierran antes; por eso tu riesgo real es mayor que el que muestra.
- *Hoy:* core/risk_report.py:216-229 empareja el retorno de la cartera del día d con el de SPY del día d. Los cálculos de cov/corr/contrib (198-204) también usan la fecha de la bolsa local (gmtoffset, líneas 58-66, D1). Para .TW/.KS/.T/.HK/.SS la reacción a la sesión de EE.UU. llega al día SIGUIENTE. No hay beta de Dimson (rezago) ni retornos de varios días para pares asíncronos.
- *Debe ser:* Beta Dimson (Σ β con rezagos −1,0,+1) o retornos de 2-5 días para covarianzas entre bolsas no sincronizadas (v2 §9.1-9.2: covarianza correcta antes de VaR).
- *Evidencia:* /tmp/audit_finance/async_beta.py usa core.risk_report.compute real con datos sintéticos. Acción asiática con beta verdadero 1.0 respecto a SPY con un día de rezago → beta_spy reportado −0.037 (EE.UU., mismo modelo: 1.077). Corr Asia–EE.UU. reportada −0.042 (verdadera ~0.5). Vol anual de una cartera 50/50 reportada 17.78 % vs 21.92 % medida con retornos de 1…
- *Arreglo:* En compute: beta Dimson con rezagos −1/0/+1 cuando la cartera o el símbolo no es de EE.UU. Para covarianza/VaR de carteras mixtas, usar retornos de 5 días superpuestos (o el ajuste de Newey-West de la covarianza) y reportar 'nonsync_adjusted'. Test sintético con rezago conocido que exija beta ≈ 1.
- *Verificación:* hallado por el verificador

**L2-06 · MEDIO · math · Fase 1 · esfuerzo S** — La convicción cuenta CLAIMS, no analistas: un solo agente con varias conclusiones pesa como el comité entero  
- *En simple:* Si un solo analista escribe muchas conclusiones parecidas, el comité puede recomendar comprar como si todos estuvieran de acuerdo.
- *Hoy:* research/committee.py:146-189 suma w·signo por claim sin agrupar por agent_type; las claims del mismo agente (misma evidencia, correladas) se tratan como independientes. El global (180-188) se renormaliza solo sobre los horizontes presentes.
- *Debe ser:* Independencia de fuentes (conf-v2, v2 §14 'un solo mundo, roles distintos'): primero una postura por agente y horizonte, luego el promedio entre agentes.
- *Evidencia:* /tmp/audit_lens2/research_check.py: 4 claims positivas conf 0.6 del MISMO agente fundamental → convicción 70.6; 4 claims de 4 agentes distintos → 70.6 (idéntico). 2 claims de un agente solo en SHORT_TERM → global 54.5 ≥ BUY_T 35 (el quórum de 3 agentes lo frena solo si faltan agentes, no si sobran claims de uno).
- *Arreglo:* Agrupar por (horizonte, agente): peso del agente = media (o máx) de sus pesos, postura = media ponderada de signos; sumar entre agentes con W0. Opcional: exigir ≥2 agentes coincidentes en el horizonte dominante para BUY.
- *Verificación:* adjusted — The math holds: conviction_by_horizon (lines 146-189) accumulates per claim with no grouping by agent_type, and re-running gives 70.6 = 70.6. The auditor's second example (2 claims from one agent → 54.5) cannot reach a BUY, though, because quorum_check requires fundamental plus 3 of 4 analysts. The…

**L2-07 · MEDIO · math · Fase 2 · esfuerzo M** — Banda fija de ±2 % para todo horizonte, exceso sin ajustar por beta y Brier sobre una 'confianza' que no es probabilidad  
- *En simple:* La forma de medir si los analistas acertaron es injusta con las predicciones 'neutrales' y favorece a las acciones muy movidas, así que el historial de cada analista puede verse mejor o peor de lo que es.
- *Hoy:* research/outcomes.py:366-373 judge() con band fija (band_default 0.02) para checkpoints de 5 días hábiles a 365 días; exceso = r − r_SPY (score_checkpoint:418-420) sin beta; stats():672-684 calcula Brier tratando conf-v2 (calidad de evidencia, research/confidence.py) como P(acierto) y mezcla posturas neutral/positiva/negativa en los mismos tramos que luego alimentan calibrated_confidence y los pesos del comité.
- *Debe ser:* Una tasa de acierto comparable entre posturas y horizontes: banda ∝ σ_idio·√h (o z-score), retorno anormal de modelo de mercado r − (α+β r_m), y calibración separada por postura.
- *Evidencia:* Cálculo en /tmp/audit_lens2/research_check.py con vol idiosincrática 35 %/año y sin habilidad: P(acierto|neutral) = 0.161 (20b), 0.093 (60b), 0.064 (180d), 0.046 (365d) vs P(acierto|positiva) = 0.420, 0.453, 0.468, 0.477. Un analista que dice 'neutral' queda castigado estructuralmente y su fiabilidad baja aunque acierte lo esperable.
- *Arreglo:* band_h = k·σ̂_idio·√(días/252) guardado en la foto de partida; exceso = r − β̂·r_SPY con β̂ de 1 año; tramos de calibración por postura; reportar Brier skill vs tasa base.
- *Necesita de Fabrizio:* Decidir si se recalifica el historial ya guardado (append-only: sería un método outcome-v2 nuevo en paralelo, no se borra el viejo).
- *Verificación:* confirmed

**L2-08 · MEDIO · math · Fase 1 · esfuerzo S** — Dos endpoints de Yahoo cuentan como dos fuentes independientes y 'www.reuters.com' ≠ 'reuters.com'  
- *En simple:* La app cree que una conclusión está respaldada por tres fuentes distintas cuando en realidad todas vienen de Yahoo, y le da más confianza de la que merece.
- *Hoy:* research/confidence.py:64-74 _key = source_type + ':' + host; financials (yahoo .../financials) y market (yahoo .../quote) dan 'financials:finance.yahoo.com' y 'market:finance.yahoo.com' → distintos. No se normaliza 'www.'. research/context.py:303-338 y 387 referencian Yahoo con distintos source_type.
- *Debe ser:* CLAUDE.md C9 / conf-v2: 'computed y khipus:* no son fuentes independientes'; misma regla para un mismo proveedor externo.
- *Evidencia:* /tmp/audit_lens2/research_check.py: soporte = Yahoo financials + Yahoo perfil + catálogo Khipus → distinct_sources 3, independence 1.0, confianza 0.88 (sin ninguna fuente fuera de Yahoo). Dos noticias de www.reuters.com y reuters.com → distinct 2.
- *Arreglo:* _key = proveedor registrable (strip 'www.', mapear finance.yahoo.com/query*.finance.yahoo.com → 'yahoo', finnhub:* → 'finnhub') sin source_type; test: Yahoo×2 + khipus → distinct 2, indep 0.67.
- *Verificación:* confirmed

**L2-10 · MEDIO · both · Fase 2 · esfuerzo M** — Totales de delta y gamma suman acciones de subyacentes distintos; opciones fuera de USD se rotulan USD; sin dividendos ni solucionador de IV  
- *En simple:* En el reporte de opciones, el total de 'acciones equivalentes' mezcla acciones de empresas distintas y las opciones europeas se muestran como si fueran en dólares.
- *Hoy:* core/options.py:195-209 suma delta_sh y gamma de TODOS los subyacentes; value_usd/vega_usd (190-191) no convierten la moneda de la cadena (row['currency']); bs() usa q=0 (modelo europeo sin dividendos, línea 6/28-54) y la IV viene de Yahoo (177-179) con respaldo de vol histórica: no hay solucionador de IV propio (grep newton/brentq: 0).
- *Debe ser:* Agregados con sentido: delta en dólares (Σ Δ·S·mult), gamma en dólares (½Γ S²·1 %), todo convertido a USD; BSM con rendimiento de dividendo q; IV invertida desde el mid cuando Yahoo no la publica.
- *Evidencia:* /tmp/audit_lens2/bs_check.py: BS correcto (call 10.4506, put 5.5735, paridad error 0.0; Δ, Γ, vega, ρ = diferencias finitas a 1e-7; θ ≈ FD a 1e-5). /tmp/audit_lens2/opt_check.py: NVDA + BRK-A + ASML.AS → totals.delta_shares 885.15 (mezcla acciones de 3 empresas), gamma 12.22; ASML en EUR rotulado value_usd 27993.17.
- *Arreglo:* Reemplazar delta_shares/gamma totales por dollar_delta y dollar_gamma; convertir con _fx_to_usd(currency); añadir q (dividendYield del perfil) a bs(); bisección/Newton sobre el mid para IV con test de ida y vuelta.
- *Verificación:* confirmed

**L2-11 · MEDIO · math · Fase 1 · esfuerzo S** — RSI con promedio simple (Cutler) en vez del suavizado de Wilder que usa el mercado  
- *En simple:* El indicador RSI que leen los analistas no es el que muestran las plataformas de bolsa; en 1 de cada 7 casos dice 'sobrecompra' o 'sobreventa' cuando el estándar no lo dice.
- *Hoy:* research/analytics.py:145-156 _rsi: media simple de las últimas 14 variaciones.
- *Debe ser:* v2 §9.3.4: RSI de Wilder; cambiarlo junto con la tabla de precios y anotarlo.
- *Evidencia:* /tmp/audit_lens2/research_check.py, 500 caminatas aleatorias de 252 días (σ 2.5 %): |Cutler − Wilder| media 6.40 puntos, p95 15.72, máx 25.82; la zona (sobrecompra/sobreventa/neutral) cambia en 73/500 casos.
- *Arreglo:* Implementar Wilder (semilla = media de 14, luego (prev·13 + x)/14) con test contra valores de referencia; anotar en el texto de evidencia 'RSI(14, Wilder)'.
- *Verificación:* confirmed

**L2-12 · MEDIO · data · Fase 1 · esfuerzo M** — No existe tabla eod_prices: cada módulo baja 1 año de Yahoo por su cuenta, sin volumen ni historia de 5 años  
- *En simple:* La app no guarda su propia historia de precios; cada pantalla la pide por separado, sin volumen y solo de un año, y eso impide cálculos más serios.
- *Hoy:* ls core | grep price → nada; grep eod_prices → 0. Cinco lectores distintos del chart de Yahoo: core/risk_report.py:46 (adjclose, 1y, caché 6 h en memoria), research/context.py:119 (close), core/screener.py:70 (close, 3mo), core/company_data.py:1087 (close), core/quotes.py:125. El volumen se descarta en todos.
- *Debe ser:* v2 §20.1 #1: core/prices_store.py + tabla eod_prices con ≥5 años de adjclose/volumen, ingesta diaria por el scheduler y lectura única para riesgo, screener y técnicos (§9.1, prerrequisito de κ, EWMA, liquidez y FHS).
- *Evidencia:* grep -rn "eod_prices" --include=*.py → 0 resultados; grep "'volume'" en risk_report/analytics → 0; fetch_history máx '5y' solo en outcomes.default_price_fn.
- *Arreglo:* Crear eod_prices (símbolo, fecha, adjclose, close, volumen, moneda, fuente) en _COLUMNAS_TARDIAS, relleno inicial 5 años, tarea diaria en core/scheduler, y hacer que fetch_history lea de ahí con respaldo a Yahoo.
- *Necesita de Fabrizio:* Confirmar que se puede usar espacio en el Postgres de Railway (~568 símbolos × 5 años ≈ 720 mil filas) y el posible costo extra del plan.
- *Verificación:* confirmed

**L2-13 · MEDIO · both · Fase 2 · esfuerzo M** — Los choques del grafo no se traducen a pérdidas/ganancias de la cartera (no existe κ calibrado)  
- *En simple:* Hoy la app dice 'si TSMC cae, 293 empresas se afectan', pero no te dice cuántos dólares perdería TU cartera.
- *Hoy:* grep -rln 'kappa|κ' en *.py → 0; grep pnl en matrix/ y core/scenario_engine.py → 0. matrix/engine.propagate devuelve impacto en % por nodo pero nada lo multiplica por pesos ni valor de la cartera.
- *Debe ser:* v2 §9.3.2: ΔP&L_p = Σ w_i V_p r^esc_i, r^esc_i = −κ·impacto_i, κ por regresión sobre episodios (escasez 2021, controles oct-2022, terremoto Taiwán abr-2024) con intervalo de confianza.
- *Evidencia:* Comandos grep anteriores: 0 resultados para kappa/κ/pnl en matrix, core/scenario_engine.py, core/sim_agents.py.
- *Arreglo:* core/scenario_pnl.py: con eod_prices, regresión de retornos anormales por episodio sobre el impacto del kernel → κ̂ e IC; endpoint que recibe posiciones + choque y devuelve P&L con bandas.
- *Necesita de Fabrizio:* Revisar y aprobar la lista de episodios históricos (fechas exactas) que se usarán para calibrar.
- *Verificación:* confirmed

**L2-14 · MEDIO · math · Fase 2 · esfuerzo S** — Una sola posición con poca historia recorta la ventana de TODA la cartera y, con 60 posiciones, la covarianza queda singular  
- *En simple:* Si en tu cartera hay una acción que salió a bolsa hace poco, todo el cálculo de riesgo usa solo esos pocos días, y con muchas acciones los números se vuelven poco confiables.
- *Hoy:* core/risk_report.py:166-168 usa la intersección de fechas y acepta ≥60 días; core/portfolio_advisor.py:57/119 pasa max_positions=60. No hay contracción (Ledoit-Wolf) ni modelo factorial en ningún módulo (grep linalg/ledoit/ewma → 0).
- *Debe ser:* v2 §9.3.1: con n > T la covarianza muestral es singular → contracción o factores obligatorios; ventana mínima ≥ 2n o excluir/rellenar la posición corta.
- *Evidencia:* /tmp/audit_lens2/trunc.py: 59 acciones con 252 días + 1 con 61 días → compute usa days 60 para todas; matriz de covarianza 60×60 con rango 59 (singular).
- *Arreglo:* Excluir (y avisar) posiciones con historia < max(120, 2n) o calcular la cartera con la ventana larga y la posición corta por proxy de sector; aplicar Ledoit-Wolf a S cuando n > T/3.
- *Verificación:* adjusted — The truncation is real: compute() intersects all dates and accepts ≥60 (risk_report.py:166-168), and portfolio_advisor passes MAX_POSITIONS (line 119). trunc.py re-run gives 60 days and rank 59. The singularity has no numerical consequence today, though. risk_report never inverts Σ (w'Σw and Euler …

**L2-M2 · MEDIO · math · Fase 2 · esfuerzo S** — Sesgo de supervivencia: si una empresa se deslista o suspende, su predicción queda 'n/a' en vez de acierto/fallo  
- *En simple:* Si un analista apostó a favor de una empresa que después quebró o dejó de cotizar, ese error no se cuenta, así que el historial de aciertos puede verse mejor de lo que es.
- *Hoy:* research/outcomes.py:401-408: sin cierre después del vencimiento por más de GIVE_UP_DAYS=20 → _na('¿suspendida o deslistada?'), y un hueco en la serie → n/a. track_record/stats (línea 587) excluye los n/a del denominador. Una postura positiva sobre una empresa que quebró nunca cuenta como fallo, ni una negativa como acierto.
- *Debe ser:* Ganar o perder se califica con el último precio negociable (o el valor de liquidación/compra si fue adquirida), no se descarta. La tasa de aciertos y la calibración (que alimentan el peso de cada analista en el comité) no deben excluir justo los eventos extre…
- *Evidencia:* outcomes.py:66 GIVE_UP_DAYS = 20. Las líneas 401-404 devuelven _na para 'no hay cierre después del vencimiento'. Las líneas 406-408 devuelven _na para un hueco en la serie. counts['n/a'] se reporta aparte (líneas 497 y 540) y no entra en hits/n_scored.
- *Arreglo:* Si la serie termina antes del vencimiento, calificar con el último cierre disponible y marcar 'terminal_price'. Si hubo compra (listing_status.js tiene IPOs/compras/quiebras), usar el precio de la operación. Mantener n/a solo cuando no hay ningún precio después de la fecha de partida.
- *Verificación:* hallado por el verificador

**L2-M3 · MEDIO · math · Fase 2 · esfuerzo M** — Cada compra se dimensiona sola por su volatilidad: no se mira la correlación con lo que ya tienes ni la concentración por sector antes de enviar la orden  
- *En simple:* El comité puede recomendarte comprar varias acciones de chips una tras otra, cada una 'con tamaño prudente', y terminar con casi todo tu dinero apostado a lo mismo sin que nada lo frene.
- *Hoy:* research/committee.compute_sizing (línea 316) recibe solo vol_ann_pct de la acción (risk_report de un solo símbolo, línea 1075) y el mandato. No recibe covarianza ni posiciones existentes. Los controles de brokerage/risk.run_checks (líneas 185-434) son: kill_switch, mode, account, symbol, restricted, order_size, daily_limit, buying_power, position_limit (por nombre), drawdown_stop, holdings, duplicate y limit_price.…
- *Debe ser:* v2 §9.2: tamaño por contribución marginal al riesgo de la cartera (o al menos un tope por sector/factor) y un control previo de concentración (HHI/sector) antes de la cola de aprobación.
- *Evidencia:* Firma de compute_sizing(decision, vol_ann_pct, mandate, equity, current_value, …) sin parámetros de cartera. grep 'sector|concentr|corr' en brokerage/risk.py → 0 coincidencias en los nombres de los controles. Con el mandato por defecto (tope 10 % por nombre), 10 BUY consecutivos sobre semiconductores con ρ≈0.8 pasan todos y dejan ~100 % en un solo factor.
- *Arreglo:* Añadir a run_checks un control 'sector_limit' (peso del sector tras la orden ≤ mandato.max_sector) y, en compute_sizing, un factor de ajuste por la correlación media con las posiciones actuales (o la vol marginal w'Σ de risk_report). Test: cartera con 3 semis al 10 % → 4.º semi limitado.
- *Necesita de Fabrizio:* Decidir el tope por sector del mandato por defecto (por ejemplo 30-40 %) para cuentas de clientes.
- *Verificación:* hallado por el verificador

**L2-03 · BAJO · both · Fase 1 · esfuerzo S** — Cierres SIN ajustar por splits/dividendos en el análisis técnico que leen los agentes y en el screener  
- *En simple:* Cuando una empresa divide sus acciones (como hizo NVIDIA), los agentes pueden creer que la acción se desplomó 75 % y escribir conclusiones equivocadas.
- *Hoy:* research/context.py:116-126 (_fetch_candles) toma indicators.quote.close (sin ajustar) y lo pasa a research/analytics.technical_indicators (context.py:381-387); core/screener.py:70-88 igual (range 3mo, quote.close). core/risk_report.fetch_history:54-57 SÍ usa adjclose.
- *Debe ser:* v2 §9.3.3: todo lee adjclose (tabla de precios propia, Fase 1 #1).
- *Evidencia:* /tmp/audit_lens2/research_check.py: serie con split 4:1 en el día 200 → max_drawdown_1y_pct −14.2 → −77.2; ret_3m_pct −1.3 → −75.3; pct_from_52w_high −8.6 → −76.6; sma200 109.58 → 86.99 (todo falso).
- *Arreglo:* Que _fetch_candles y el screener lean adjclose (o core.risk_report.fetch_history) y, cuando exista, la tabla eod_prices; test con split sintético → drawdown sin salto.
- *Verificación:* adjusted — The code fact holds: research/context.py:116-126 and core/screener.py:70-88 read indicators.quote.close, not adjclose. The synthetic −75 % split scenario does not match the data source, though. Yahoo's chart 'close' is already split-adjusted; only 'adjclose' adds the dividend adjustment. I could no…

**L2-09 · BAJO · math · Fase 2 · esfuerzo M** — Los topes por nombre/sector rompen la paridad de riesgo pero la cartera se sigue rotulando 'risk_parity'  
- *En simple:* La cartera de 'baja volatilidad' dice repartir el riesgo por igual, pero después de aplicar los límites algunas acciones aportan el doble de riesgo que otras.
- *Hoy:* core/portfolio_ai.py:700-707: risk_parity() (ERC correcto) y LUEGO apply_caps (445-497) redistribuye proporcionalmente; method='risk_parity' se mantiene. No se reporta HHI ni número efectivo de nombres.
- *Debe ser:* v2 §9.2 Optimización 'paridad de riesgo (✔)' y Concentración HHI ✔: ERC bajo restricciones (o rotular honestamente) + HHI = Σw² y RC_i = w_i(Σw)_i/σ_p.
- *Evidencia:* /tmp/audit_lens2/pf_check.py (10 activos, vol 15-70 %, ρ 0.3/0.8): ERC sin topes → Σ RC = σ_p = 0.011684, max/min RC = 1.0000000006 (correcto). Con tope 12 % por nombre y 55 % por sector: contribuciones 5.06 %…13.12 % del riesgo (objetivo 10 %). HHI 0.1033 / n_eff 9.68 calculados a mano; grep 'hhi' en core/portfolio_*.py: 0 resultados.
- *Arreglo:* ERC con restricciones de caja (iteración de Spinu o ciclo ERC→caps→ERC sobre los nombres libres hasta convergencia) y añadir a metrics: hhi, n_eff = 1/HHI, rc_dispersion; si no converge, rotular 'paridad de riesgo aproximada'.
- *Verificación:* adjusted — pf_check.py re-run confirms ERC is exact without caps and that after apply_caps the risk shares spread from 5.06 % to 13.12 % while method stays 'risk_parity'. However, caps that bind are a deliberate profile constraint. Each position's risk_contrib_pct IS reported (portfolio_ai.py:725, taken from …

**L2-15 · BAJO · math · Fase 2 · esfuerzo S** — CVaR y VaR paramétrico solo a 1 día; a N días solo el histórico × √N (sin Cornish-Fisher)  
- *En simple:* La pérdida esperada en un mal escenario solo se muestra para un día, no para las próximas dos semanas.
- *Hoy:* core/risk_report.py:183-194 var_block: claves hist_1d, param_1d, hist_nd, cvar_1d; no hay param_nd ni cvar_nd; escala √h pura sobre el cuantil histórico.
- *Debe ser:* v2 §9.2: CVaR al horizonte y Cornish-Fisher para colas; luego FHS (Monte Carlo histórico filtrado).
- *Evidencia:* /tmp/audit_lens2/risk_check.py: claves var99 = ['conf','cvar_1d_pct','cvar_1d_usd','hist_1d_pct','hist_1d_usd','hist_nd_pct','hist_nd_usd','param_1d_pct','param_1d_usd']. Lo que sí está bien: param99 4.662 % vs teoría 4.653 %; CVaR99 5.026 % vs teoría 5.33 % (muestra de 2000); Kupiec p(6/100)=0.655997 = scipy 0.656015.
- *Arreglo:* Añadir param_nd (μh − zσ√h), cvar_nd (histórico con retornos de h días superpuestos o √h documentado) y VaR Cornish-Fisher con asimetría/curtosis de la muestra.
- *Verificación:* confirmed

**L2-16 · BAJO · math · Fase 3 · esfuerzo M** — Faltan EWMA, Ledoit-Wolf, factores multifactor, liquidez (ADV) y FHS  
- *En simple:* La volatilidad que usa la app reacciona lento a los cambios del mercado y no considera si una acción es fácil o difícil de vender.
- *Hoy:* Toda la volatilidad es muestral de 1 año con igual peso (risk_report._std, portfolio_ai._std, options.hist_vol:136-142); analytics.vol_20d (185) usa RMS sin restar media, inconsistente con el resto. grep -rn 'ewma|ledoit|linalg' → 0.
- *Debe ser:* v2 §9.2: EWMA λ=0.94, Ledoit-Wolf, B multifactor, días para liquidar, FHS — todos derivados de eod_prices, sin tensores guardados (§19).
- *Evidencia:* grep -rn "linalg\.(inv|solve)|np\.cov|ledoit|ewma|0\.94" en core research matrix mcp_server server.py → 0 resultados.
- *Arreglo:* Tras L2-12: módulo core/risk_models.py con ewma_vol, ledoit_wolf(S), y adv/días-para-liquidar; usar EWMA en el VaR paramétrico y en el sizing del comité.
- *Verificación:* confirmed

**L2-17 · BAJO · code · Fase 1 · esfuerzo S** — Compara contribución al riesgo (sobre lo invertido) con peso (sobre total con efectivo)  
- *En simple:* Si tienes mucho dinero en efectivo, el comité puede pedirte reducir una acción que en realidad no está tomando demasiado riesgo.
- *Hoy:* core/portfolio_advisor.py:128-133 recalcula weight_pct = value/(invertido + efectivo) pero risk_contrib_pct viene de risk_report sobre lo invertido; la regla 181 'risk_contrib > 2·weight' mezcla denominadores.
- *Debe ser:* Mismo denominador en ambos lados (o RC escalado por la fracción invertida).
- *Evidencia:* Con 50 % en efectivo, una posición del 20 % de lo invertido muestra weight_pct 10 % y, si aporta 25 % del riesgo invertido, dispara 'reducir' (25 > 2×10) aunque frente a lo invertido (25 vs 20) no lo haría.
- *Arreglo:* Usar el peso sobre lo invertido para la regla de riesgo, o multiplicar risk_contrib por invertido/total.
- *Verificación:* confirmed

**L2-18 · BAJO · math · Fase 2 · esfuerzo S** — Sharpe con retorno GEOMÉTRICO (no el estándar aritmético) y ^IRX en base de descuento  
- *En simple:* El Sharpe que muestra la app sale un poco más bajo que el que calcularía un banco para acciones muy movidas.
- *Hoy:* core/risk_report.py:241-245: sharpe = (ret_geom − rf)/vol; rf = último ^IRX/100 (339) que es tasa de descuento bancario, no rendimiento equivalente.
- *Debe ser:* Sharpe estándar = (media aritmética de exceso diario × 252) / (σ·√252); rf convertido a rendimiento equivalente.
- *Evidencia:* /tmp/audit_lens2/risk_check.py (σ 2 % diario): geométrico −22.15 %, aritmético −20.14 %, Sharpe reportado −0.71 vs aritmético −0.64 (diferencia ≈ σ²/2; para vol 50 % ≈ 0.25 de Sharpe).
- *Arreglo:* Publicar el Sharpe aritmético como principal (y el geométrico como 'retorno compuesto'); convertir ^IRX con y = 365·d/(360 − 91·d).
- *Verificación:* adjusted — The geometric Sharpe is a deliberate, labelled choice (D2: sharpe_method states it), not a bug. The ~σ²/2 gap is real for high-vol names. The ^IRX discount-to-yield point is immaterial: at 4 % discount the bond-equivalent yield is about 4.08 %, under 0.01 of Sharpe. The fix should be to show both S…

**L2-19 · BAJO · code · Fase 1 · esfuerzo S** — Se adivina si un ratio viene en fracción o en % por su tamaño  
- *En simple:* En casos extremos (empresas que crecen más del 200 %), la app puede mostrar el crecimiento 100 veces más chico.
- *Hoy:* research/analytics.py:122 (ROE/ROIC: ×100 si |v|<5) y 228-230 _as_pct (×100 si |v|≤2).
- *Debe ser:* Unidades declaradas por la fuente (company_data documenta roe/roic como FRACCIÓN, línea 106).
- *Evidencia:* _as_pct(2.5) → 2.5 (un crecimiento de ingresos de 250 % en fracción se muestra como 2.5 %); un ROE de 6.0 (600 %) se muestra como 6.0 %.
- *Arreglo:* Convertir siempre fracción→% según el contrato de company_data/get_live_profile, sin umbrales.
- *Verificación:* confirmed

<details><summary>Lo que este lente midió y está BIEN (15)</summary>

- ✔ Black-Scholes precio y paridad put-call: call 10.4506, put 5.5735 (S=K=100,T=1,r=5 %,σ=20 %); error de paridad 0.0
- ✔ Griegas BS vs diferencias finitas: Δ, Γ, vega, ρ coinciden a ~1e-7; θ por día ≈ FD a 1e-5
- ✔ VaR paramétrico 99 % con retornos normales: 4.662 % vs teoría 4.653 % (σ 2 %, T 2000)
- ✔ CVaR histórico 99 %: 5.026 % vs teoría normal 5.33 % (error muestral)
- ✔ Prueba de Kupiec: LR(6/100)=0.1984, p=0.655997 vs scipy 0.656015; LR(0/250)=25.65
- ✔ ya arreglado Backtest VaR fuera de muestra (D3): ventana móvil max(60,min(125,n/2)) + Kupiec; en-muestra solo de referencia
- ✔ ya arreglado Sharpe con ^IRX (D2): rf = T-bill 13 semanas en vivo; Sharpe geométrico −0.71 vs aritmético −0.64 en sintético
- ✔ Precios ajustados en el reporte de riesgo: adjclose con aviso de símbolos sin ajustar (unadjusted_symbols)
- ✔ ya arreglado Máxima caída de 1 año en técnicos (bug de ventana): pico arranca dentro de la ventana de 250 días
- ✔ Retornos simples agregados entre activos: risk_report y portfolio_ai usan retornos simples para w·r (correcto según v2 §9.1)
- ✔ ERC: contribuciones suman σ_p e iguales: Σ RC = σ_p = 0.011684; max/min RC = 1.0000000006
- ✔ Máxima caída del motor viejo (orden invertido de la serie): 30.0 % = 30.0 % cronológico (la máx. caída no depende del orden de los segmentos)
- ✔ Quórum del comité (C7): fundamental obligatorio + 3 de 4 analistas; sin quórum → HOLD 'DATOS INSUFICIENTES'
- ✔ Calendario NYSE y checkpoints hábiles (C10): feriados por reglas + Pascua; business_days_after
- ✔ ya arreglado Fórmula NRS única (cliente=servidor): fuera de este lente; según el encargo ya unificada (app.html _nrsTerms = core/world.client_nrs)

</details>


### C. Datos, historia y tiempo — 19 hallazgos

**L3-01 · CRÍTICO · both · Fase 1 · esfuerzo M** — No existe ninguna tabla de historia: eod_prices, entity_daily, positions_eod, instruments, fills (PriceObserved sin escritores)  
- *En simple:* Khipus no guarda precios, riesgos ni posiciones de días pasados, así que no puede responder '¿cómo cambió mi cartera en 12 meses?' ni calcular correlaciones serias. Cada día sin guardar es historia que se pierde para siempre.
- *Hoy:* ontology/models.py:33 define PriceObserved, pero ontology/service.py:402 lo ignora ('pass') y nada lo escribe. Las 30 tablas de la base (listado \dt sobre una migración nueva) no incluyen series. El scheduler (server.py:483-504) solo registra research_recover_orphans, research_resume_deferred, research_outcomes_daily, world_prewarm, live_fundamentals y ops_daily_check: no hay ingesta EOD. Las posiciones del usuario …
- *Debe ser:* v2 §9.1, §17.3 (eod_prices, entity_daily, positions_eod, instruments), §20.1 #1-#2: relleno inicial >=5 años de adjclose/volumen + ingesta diaria de los 568 símbolos + foto diaria de NRS/capitalización/posiciones.
- *Evidencia:* grep -rn 'PriceObserved' --include=*.py → solo models.py:34, service.py:402 (pass), matrix/engine.py:678 y ontology/timeline.py (lectura). grep 'eod_prices|entity_daily|positions_eod|nrs_history|price_history' en *.py → 0 archivos. pg_trigger/\dt en base migrada: 30 tablas, ninguna serie.
- *Arreglo:* core/prices_store.py con tabla eod_prices(instrument_id,date,o,h,l,c,adjclose,volume,src) particionada por mes + columna en _COLUMNAS_TARDIAS; tarea diaria en core/scheduler (lotes de 100, idempotente por (instrumento,fecha)); core/daily_snapshots.py para entity_daily y positions_eod. No usar eventos PriceObserved para precios (inflan el registro): borrar e…
- *Necesita de Fabrizio:* Aprobar el relleno inicial de 5 años (unas horas de descargas gratuitas de Yahoo) y confirmar que se use el Postgres actual de Railway (~100 MB en 10 años).
- *Verificación:* confirmed

**DT-M1 · ALTO · code · Fase 1 · esfuerzo S** — Nothing turns a catalog 'since' date (or the date of a real fact) into valid_from: both the migration and the reconcile write GENESIS, and reconcile excludes rows that already have a date  
- *En simple:* Aunque se agreguen fechas reales a las relaciones en el catálogo, hoy no llegarían a la base: el sistema las sigue guardando como 'desde el año 2000'. Hay que arreglar ese paso antes de empezar a fechar.
- *Hoy:* scripts/migrate_v0_to_ontology.py:383-387 copies l['since'] only into properties and calls apply_event(..., valid_from=GENESIS). ontology/reconcile.py writes valid_from=GENESIS in every LinkCreated (lines 613, 626, 635), and _row_scope (reconcile.py:143-145) returns 'fecha_real' (out of scope) for any row whose valid_from is not GENESIS. grep 'since' ontology/reconcile.py → 0 hits.
- *Debe ser:* v2 §8.2 P2 / §19.11: date the ~200 heaviest links; the catalog field since ({conf, verified, since} in nodes/merge_graph.js:162-197) is the intended carrier.
- *Evidencia:* sed -n 355,387p scripts/migrate_v0_to_ontology.py; grep -n 'valid_from\|GENESIS' ontology/reconcile.py → 53, 127, 144, 285, 613, 626, 635; grep -n since ontology/reconcile.py → none.
- *Arreglo:* In the migration, use valid_from = since when it is present (keep valid_from_known logic). Teach reconcile to emit a directed retraction plus LinkCreated with valid_from=since when catalog since ≠ DB valid_from (a new 'date' category, reviewed by Fabrizio). Keep dated rows in scope for weight and direction drift instead of skipping them.
- *Verificación:* hallado por el verificador

**DT-M3 · ALTO · code · Fase 1 · esfuerzo M** — Two incompatible time-travels: the map slider (client) hides links by pair date and by 'founded', while the server keeps every link and adds parallel dated rows  
- *En simple:* El mapa con la línea de tiempo y el motor del servidor muestran 'la cadena en 2020' de dos formas distintas, así que un mismo análisis puede dar resultados diferentes según dónde se mire.
- *Hoy:* engine/maptime.js:87-148 dates a catalog PAIR (undirected pairKey, any rel type) with the earliest TEMPORAL_SEED_FACTS valid_from, and hides links and nodes before 'founded'. Server _links_active_at (ontology/service.py:452-529) keeps every catalog link (GENESIS) and adds the dated facts as separate links (L3-02). 'GRAPH ASOF' on the map and /api/ontology/graph?as_of= (and /api/matrix?as_of=) therefore return differ…
- *Debe ser:* v2 §17.8 / §18 fila 1: a single materializer of G_t used by every surface.
- *Evidencia:* /tmp/audit_data_time inline script reproducing the maptime rules over data/grafo_v0.json: the client hides 43 / 33 / 17 of 2,510 catalog links at 2018-01-01 / 2020-01-01 / 2024-01-01. The server keeps all 2,510 (GENESIS) at every date, and the audit's migrated base had 2,986 links at 2020-01-01.
- *Arreglo:* Make the client time slider read the server as_of graph when DATABASE_URL exists (it already exists in /api/ontology/graph?as_of=). Without a base, apply ONE shared rule (dated twin = valid_from of the existing edge, as DT-M1/L3-02 propose) implemented once and exported in the snapshot. Add a parity test of link counts per date for client and server.
- *Verificación:* hallado por el verificador

**L3-02 · ALTO · both · Fase 1 · esfuerzo S** — 27 vínculos FECHADOS entran al motor como 'supply' por defecto aunque son inversiones, PPAs o van al revés  
- *En simple:* Hoy el motor cree, por ejemplo, que si OpenAI cae arrastra un 18 % a Oracle, cuando la relación real es la inversa. Son 27 relaciones con fecha que están mal clasificadas y deforman los choques.
- *Hoy:* scripts/migrate_v0_to_ontology.py:400 usa {'rel_type': f.get('rel') or 'supply'} sin peso; 28 de los 86 hechos-arista de temporal_facts no traen 'rel' (p. ej. 'invirtió ~$13B en', 'PPA 1.2 GW con', 'proyecto Stargate con', 'Colossus: 100k+ GPUs de'). En la base quedan como supply con weight NULL → _eff_weight(None)=2 (matrix/engine.py:131).
- *Debe ser:* v2 §3.3 (cada arista con tipo y dirección correctos; invest/ppa/fab distintos de supply) y §20.1 #8 (puerta de calidad).
- *Evidencia:* Migración real a una base local (/tmp/audit_l3): links con valid_from≠2000-01-01 y rel_type='supply': 27, todos con weight NULL. Radio espectral con esas filas 0.923779 vs 0.892761 sin ellas. Choque OpenAI → impacto en Oracle 18.0 % (con ellas) vs 1.72 % (sin ellas); Meta→ScaleAI 25.5 vs 7.5; SoftBank→OpenAI 6.58 vs 1.63. Mal tipados: 6 inversiones (Microso…
- *Arreglo:* Agregar 'rel' explícito (y 'w') a los 28 hechos en nodes/temporal_seed_facts*.js con un test que falle si un hecho-arista no trae rel del vocabulario; en la migración, rechazar (no suponer 'supply') un hecho sin rel. En producción: RetractarVinculo de esas 27 filas + LinkCreated con el tipo/dirección correctos y la misma fecha (canal reconcile).
- *Necesita de Fabrizio:* Revisar la lista de 27 relaciones (tipo y dirección propuestos) y marcarlas como correctas antes de aplicarlas en producción con PIN.
- *Verificación:* adjusted — The numbers reproduce exactly without Postgres. I fed build_matrices_from_triples the snapshot links plus the temporal edges, using the same filter as the migration. Result: 30 extra rows, 27 of them defaulting to 'supply'. ρ = 0.892761 → 0.923779. An OpenAI shock moves Oracle from 1.72 to 18.0 (no…

**L3-04 · ALTO · data · Fase 2 · esfuerzo L** — El time-travel al pasado devuelve el grafo de hoy: 97 % de los vínculos tienen la fecha centinela 2000-01-01  
- *En simple:* Si preguntas '¿cómo era la cadena en 2018?', Khipus te muestra la de hoy, con empresas que ni existían. Hace falta poner fecha real a las relaciones más importantes.
- *Hoy:* Catálogo: 0 de 2.510 vínculos traen 'since' (el 6.º elemento existe en merge_graph.js pero nadie lo usa). Toda la migración usa valid_from=GENESIS (scripts/migrate_v0_to_ontology.py:360-387, 467-485), también los 447 'affects' de los 69 factores.
- *Debe ser:* v2 §8.2 P2 y §19.11: 'la tarea prioritaria es fechar los ~200 vínculos más pesados'; §17.8 G(t_v, t_k).
- *Evidencia:* Base migrada: 81 de 3.042 links con valid_from≠2000-01-01 (2,7 %). as_of_graph('2005-01-01') → 2.967 links y 995 nodos, e incluye OpenAI (2015), Anthropic, xAI (2023), CoreWeave, ScaleAI, DeepSeek. active_factors(as_of='2005-01-01') → 69 factores y 447 miembros, igual que hoy. _links_active_at('2020-01-01') = 2.986 vs 3.041 hoy.
- *Arreglo:* Fechar primero los ~200 vínculos de flujo de mayor peso con fuente (agente de investigación propone, Fabrizio confirma) usando el campo since del catálogo y la acción de reconciliación; marcar en la UI/MCP la proporción fechada de cada respuesta temporal; las fechas de factores salen de sus fuentes (aranceles 2025, Entity List 2019…).
- *Necesita de Fabrizio:* Revisar y aprobar las fechas propuestas para los ~200 vínculos más importantes (o aceptar que el agente de investigación las proponga con fuente para su visto bueno).
- *Verificación:* confirmed

**L3-05 · ALTO · code · Fase 2 · esfuerzo M** — No existe G(t, κ) ('qué creíamos en t'): ninguna consulta filtra por recorded_at  
- *En simple:* Hoy no se puede auditar con qué información decidió el comité un día concreto, porque las correcciones posteriores se mezclan con el pasado. Es la base para rendir cuentas de una recomendación.
- *Hoy:* ontology/service.py:452 _links_active_at(session, as_of_dt), :531 as_of_graph(session, as_of_dt=None) y :548 diff_graph(session, from_dt, to_dt) solo filtran por valid_from; recorded_at se usa solo para desempates internos (_killed). Los memos del comité (research/models.py:273-308) guardan inputs pero no la época del grafo usada.
- *Debe ser:* v2 §3.1 (dos tiempos t_v y t_k), §8.1 fórmula G(t,κ), §17.8 'auditoría = G(t,t) ✚'.
- *Evidencia:* inspect.signature: as_of_graph (session, as_of_dt=None); diff_graph (session, from_dt, to_dt); _links_active_at (session, as_of_dt). grep 'known_at|recorded_before|knowledge_time' en ontology/matrix/core/mcp_server/research → 0 resultados. grep graph_epoch en research/core/mcp_server → 0.
- *Arreglo:* Parámetro known_at (κ) en _links_active_at/as_of_graph/diff_graph/build_matrices: filtrar Event.recorded_at <= κ en creaciones Y remociones/retracciones (como en la fórmula §8.1); exponerlo en /api/ontology/graph?as_of=&known_at= y en MCP; guardar graph_epoch y as_of en committee_memos.inputs e insight_snapshots.
- *Verificación:* adjusted — The core claim holds. _links_active_at / as_of_graph / diff_graph (ontology/service.py:452, 531, 548) only filter on valid_from. recorded_at is used only inside _killed for tie-breaking, so there is no G(t,κ). One part of the fix is already done: InsightSnapshot already stores graph_epoch (= MAX(re…

**L3-09 · ALTO · code · Fase 1 · esfuerzo M** — Tres copias vivas del grafo que dan resultados distintos (catálogo JS, snapshot, Postgres) + Neo4j  
- *En simple:* Las IAs externas (MCP) y el motor de la app miran versiones distintas del mapa, por eso pueden dar respuestas distintas a la misma pregunta. Hay que dejar una sola versión de la verdad.
- *Hoy:* Cliente: window.LINKS desde nodes/*.js. Snapshot data/grafo_v0.json lo leen 7 módulos: matrix/tensor.py:60, core/world.py:56, core/entities.py:32, core/screener.py:49, core/semantic.py:32, core/sim_agents.py:83, mcp_server/tools.py:37. Postgres lo leen matrix/engine.py:266-289 (kernel del servidor) y ontology/*. Paso catálogo→Postgres solo manual (reconcile con PIN).
- *Debe ser:* v2 §18 fila 1 y §17.3: Postgres = verdad; snapshot GENERADO; un solo Γ que materializa G_t.
- *Evidencia:* Snapshot vs catálogo: buildSnapshot() en memoria → 0 diferencias (ok). Migración del MISMO repo a Postgres: 3.042 links (2.510 + 85 fechados + 447 affects) y ρ=0.923779 vs ρ=0.892761 de la vista sin fechados; choque OpenAI alcanza 56 nodos (Postgres) vs 48 (sin fechados). Producción tiene 1.294 objetos vs 969 migrables (CLAUDE.md). MCP/tensor Ψ usan el snap…
- *Arreglo:* Un solo materializador: un módulo core/graph_view.py que entregue (nodos, links, época) desde Postgres cuando DATABASE_URL existe y desde el snapshot si no; mcp_server/tools.py, matrix/tensor.py, core/world.py y core/entities.py lo consumen; test de paridad snapshot↔Postgres (conteos por tipo y ρ) en CI con base local; plan de reconcile diario solo-lectura …
- *Necesita de Fabrizio:* Decidir si Postgres de producción manda sobre el catálogo (recomendado) y revisar una vez el plan de reconciliación que muestre las diferencias actuales.
- *Verificación:* adjusted — The copies are real. Snapshot readers: matrix/tensor.py, core/world.py, core/entities.py, core/screener.py, core/semantic.py, core/sim_agents.py, core/khipu_chat.py and mcp_server/tools.py (8, not 7). Postgres readers: matrix/engine and ontology/*. The MCP itself mixes both: get_supply_chain uses t…

**L3-11 · ALTO · both · Fase 1 · esfuerzo M** — Pesos mezclados en dos escalas (0-1 y 1-6) que el kernel normaliza como si todo fuera 1-6  
- *En simple:* Algunas relaciones se cargaron con una escala de 0 a 1 y otras de 1 a 6; el motor trata a las primeras como casi irrelevantes aunque sean el único proveedor. Hay 41 casos así.
- *Hoy:* matrix/engine.py:401 SOLE_LINK_FLOOR=6 y :421 col = max(colsum, 6): un proveedor único con w=0,9 transmite 0,9/6 = 15 % en vez de ~90 %. Mismo piso en engine/statematrix.js:30 y en matrix/tensor.py (usa E._dependency_matrix).
- *Debe ser:* v2 §3.3 'Unificación de escalas': una escala w∈[0,1] = fracción del insumo del cliente que depende del proveedor; §20.1 #8.
- *Evidencia:* data/grafo_v0.json: w<1: 400 (0.3×266, 0.25×34, 0.9×44, 0.6×20, 0.8×17, 0.4×11, 0.7×6, 0.5×2); w=1.0: 462 (ambiguo entre escalas); w>1: 1.648. En FLUJO: 103 vínculos con w<1 (cloud 44, supply 32, license 17, owns 6, ppa 2, deploy 2); 41 de ellos son el ÚNICO proveedor de su tipo para el cliente y transmiten como máximo 0,15.
- *Arreglo:* Script que proponga la conversión a [0,1] por tipo (1-6 → w/6; 0-1 se queda; w=1.0 se decide por fuente/archivo de origen) → lista de revisión; migrar por eventos (LinkRemoved dirigido + LinkCreated) y cambiar el piso a 1.0 en engine.py, statematrix.js y tensor a la vez con test de paridad.
- *Necesita de Fabrizio:* Revisar la propuesta de conversión de pesos, sobre todo los 462 vínculos con peso 1 (no se sabe en qué escala se escribieron).
- *Verificación:* confirmed

**L3-12 · ALTO · data · Fase 1 · esfuerzo S** — La auditoría de direcciones no detecta vínculos invertidos por texto ('X usa Y'); al menos 9 claros fuera de los 32 marcados  
- *En simple:* Hay relaciones al revés: por ejemplo, el mapa dice que OpenAI le provee a Nvidia, cuando es al revés. Eso hace que un problema en OpenAI parezca dañar a Nvidia.
- *Hoy:* scripts/audit_graph.py solo marca 'service_source' (4 traders) y 'bidirectional_same_type' (28); data/graph_audit_baseline.json: suspicious_directions=32. No mira el sujeto del verbo en el texto del vínculo.
- *Debe ser:* v2 §18 fila 'Direcciones dudosas' y §20.1 #8: detector de dirección por texto ('usa', 'uses', 'co-fundó…') + lista de revisión.
- *Evidencia:* Detector en /tmp/audit_l3 sobre 1.558 vínculos de flujo: 50 textos con usa/utiliza/compra/cliente de/compite/co-fundó; claros invertidos o mal tipados NO incluidos en los 32: OpenAI→Nvidia supply w4 'ChatGPT usa clusters de H100', Snowflake→Nvidia 'Snowflake Cortex AI usa GPUs Nvidia', Qwen→Nvidia 'Alibaba usa clusters H800', BostonDynamics→OpenAI 'Boston D…
- *Arreglo:* Agregar a audit_graph.py la regla 'sujeto del verbo de consumo = source' (alias/etiquetas de nodos) y 'texto de competencia/fundación en relación de flujo' como categorías con trinquete; salida = lista para Fabrizio; corrección por RetractarVinculo + LinkCreated invertido.
- *Necesita de Fabrizio:* Revisar la lista de ~9-15 vínculos sospechosos y marcar cuáles invertir, cambiar de tipo o borrar.
- *Verificación:* confirmed

**L3-13 · ALTO · both · Fase 1 · esfuerzo M** — Empresa = acción: un solo campo mkt por empresa, sin bolsa, moneda ni multi-listado  
- *En simple:* Para Khipus una empresa y su acción son lo mismo, y para Samsung o Tokyo Electron se usa un certificado poco negociado en EE.UU. en vez de la acción principal. Eso da precios y riesgos menos fiables.
- *Hoy:* Cada nodo tiene un único mkt (string). Los listados múltiples viven solo en el texto 'ticker'. 28 empresas cotizan vía ADR/OTC proxy (Samsung mkt=SSNLF aunque el texto dice '005930 · KRX'; TEL→TOELY, ShinEtsu→SHECY, Foxconn→HNHPF). No hay tabla instruments.
- *Debe ser:* v2 §3.2 (tipo Instrumento con subtipo equity/adr…, listed_on, denominated_in), §19.2, §17.3 instruments, §20.1 #3.
- *Evidencia:* data/grafo_v0.json: 568 nodos con mkt, 369 sin; sufijos: 365 EE.UU./sin sufijo, 203 extranjeros (.T 38, .HK 25, .AX 20, .SS 15, .TW 14, .DE 14, .L 12…); 16 con dos listados declarados solo en texto (Baidu 'BIDU · NASDAQ / 9888 · HKEX', Tencent '0700 · HKEX / TCEHY · OTC', KEPCO, POSCO, CNOOC, HuaHong…); 28 con proxy OTC/ADR (regex [A-Z]{4}[FY] u 'OTC').
- *Arreglo:* core/instruments.py + tabla instruments(id, company_id, symbol, venue, currency, kind, ratio_adr, primary) generada desde mkt + parseo del texto 'ticker'; ADR/multi-bolsa marcados para revisión; quotes/risk/eod leen por instrument_id; el nodo empresa queda sin precio propio.
- *Necesita de Fabrizio:* Elegir, para las 16 empresas con varios listados y las 28 con certificado OTC, cuál es el precio de referencia (acción local o ADR en dólares).
- *Verificación:* confirmed

**L3-14 · ALTO · math · Fase 1 · esfuerzo S** — Sin historia de tipo de cambio: se aplica el FX de HOY a toda la serie de precios  
- *En simple:* Para acciones de Japón, Europa o Asia, el riesgo calculado en dólares ignora cuánto se movió la moneda en el pasado, así que puede subestimar pérdidas reales del inversor en dólares.
- *Hoy:* core/risk_report.py:349-367 obtiene rate = fx_fn(cur) una vez y hace px_usd = h[d] * fx[s] para todas las fechas; igual core/portfolio_report.py:73-96 y 116-118. core/quotes.py:86-101 _fx_to_usd cachea solo la tasa spot ({CUR}USD=X) 1 h.
- *Debe ser:* v2 §9.1: r^USD = r^local + r^FX con FX histórico; FX como serie en eod (tabla de pares).
- *Evidencia:* Lectura de código citada; 203 de 568 tickers del catálogo tienen sufijo de bolsa extranjera → su VaR/volatilidad/P&L histórico en USD omite el componente cambiario (p. ej. JPY ±10 %/año).
- *Arreglo:* Guardar series diarias de FX (mismos 30-40 pares) en eod_prices como instrumentos kind='fx'; build_report/portfolio_report convierten fecha a fecha; test sintético: activo plano en moneda local con FX que cae 10 % → retorno USD −10 %.
- *Verificación:* confirmed

**DT-M2 · MEDIO · both · Fase 2 · esfuerzo M** — The set of nodes has no time: node_index ignores as_of, all objects are born at GENESIS, and retired objects stay as rows  
- *En simple:* Al viajar al pasado, Khipus sigue contando empresas que todavía no existían o que ya se fusionaron, lo que distorsiona los cálculos de riesgo de esas fechas.
- *Hoy:* matrix/engine.py:186-218 node_index(session, as_of) uses as_of only in the cache key and selects every ObjectRecord whose type is economic, whatever its creation date or retired flag. The migration creates every object with valid_from=GENESIS (scripts/migrate_v0_to_ontology.py:358-363). Only 40 of 937 catalog nodes have 'founded' (OpenAI, Anthropic, xAI, CoreWeave and DeepSeek have none). as_of_graph derives nodes o…
- *Debe ser:* v2 §8.1 G(t): V(t) = entities whose validity interval contains t; retirement and merges (FusionarEntidad) end the interval.
- *Evidencia:* sed -n 186,218p matrix/engine.py (no valid_from / retired filter); python: nodes with 'founded' = 40/937; actions.py:415 and :564 set retired via ObjectUpdated properties (no validity interval).
- *Arreglo:* Give every object an existence interval: ObjectCreated.valid_from = founded/IPO/first-dated fact when it is known, and retirement as a dated event. In node_index(as_of), filter to objects whose interval contains as_of and drop retired/merged aliases. Add a test that as_of='2005-01-01' excludes OpenAI and xAI.
- *Necesita de Fabrizio:* Aprobar que se usen fechas de fundación/salida a bolsa con fuente para las empresas más importantes (hoy solo 40 de 937 tienen año de fundación).
- *Verificación:* hallado por el verificador

**L3-03 · MEDIO · data · Fase 1 · esfuerzo S** — 58 vínculos fechados usan verbos en español fuera del vocabulario y el motor los ignora  
- *En simple:* La mayoría de las relaciones que sí tienen fecha real están escritas con palabras que el motor no entiende, así que no cuentan para nada en los cálculos.
- *Hoy:* La migración guarda rel_type 'fabrica' (20), 'usa' (7), 'restringe' (6), 'controla' (6), 'alberga' (5), 'energiza' (3), 'invierte' (3), 'depende' (3), 'compite' (3), 'sanciona' (1), 'domina' (1). build_matrices_from_triples (matrix/engine.py:236-238) descarta cualquier rel que no esté en REL_TYPES = vocab.relation_types() (9 tipos). Resultado: casi todos los hechos con fecha real no llegan al kernel ni al time-trave…
- *Debe ser:* v2 §3.2-3.3 (meta-grafo cerrado de relaciones) y §1 ('58 de esas 85 con relaciones en español fuera del vocabulario').
- *Evidencia:* python sobre data/grafo_v0.json: temporal_facts=105, hechos-arista=86, rel fuera del vocabulario=58, rel=None=28. Migración local: el log imprime 11 'rel_type desconocido … se excluye'; SELECT rel_type,count(*) FROM links muestra fabrica 20, usa 7, etc., todas con weight NULL.
- *Arreglo:* Tabla de mapeo verbo→relación del vocabulario (fabrica→fab, energiza→ppa, invierte→invest, usa→supply con dirección invertida, controla→owns) y relaciones NO-flujo para restringe/sanciona/compite/domina/alberga (Factor/affects o 'about'); aplicar en temporal_seed_facts*.js con test de vocabulario y migrar por eventos.
- *Necesita de Fabrizio:* Confirmar qué significa en el negocio 'controla', 'alberga' y 'domina' (¿propiedad, ubicación, cuota de mercado?) para mapearlas bien.
- *Verificación:* adjusted — The counts are right: 58 edge-facts with a Spanish rel outside the 9-type vocabulary, plus 28 with no rel at all. But 55 of the 58 involve ONT_* concept objects: technologies (ONT_EUV, ONT_HBM3e, ONT_CUDA), countries (ONT_Taiwan, ONT_China), policies (ONT_BIS, ONT_CHIPSAct, ONT_DUVBan), materials a…

**L3-06 · MEDIO · code · Fase 2 · esfuerzo M** — Las propiedades de los objetos no tienen historia: ObjectUpdated pisa el valor y el pasado lee el de hoy  
- *En simple:* Si hoy se sube la gravedad de un riesgo, Khipus la aplica también a fechas pasadas, así que las simulaciones 'como en 2022' salen infladas.
- *Hoy:* ontology/service.py:329-345 hace merged.update(new_props) sobre objects; no hay object_versions ni replay. matrix/engine.py:318-330 (active_factors con as_of) lee o.properties actuales para severity.
- *Debe ser:* v2 §8.1: 'Falta el replay de propiedades (o tabla object_versions)'.
- *Evidencia:* Prueba en base local: factor FACTOR_EUChipsAct2 severity 1.0 → ObjectUpdated severity 9.9 con valid_from 2026-10-12 → active_factors(as_of='2020-01-01') devuelve severity 9.9.
- *Arreglo:* Función props_at(object_id, t, κ) que pliega ObjectCreated/ObjectUpdated con valid_from<=t (y recorded_at<=κ) y usarla en active_factors/as_of_graph cuando hay as_of; o tabla object_versions(object_id, valid_from, valid_to, recorded_at, properties) materializada por _materialize. Test: severidad en 2020 ≠ severidad de hoy.
- *Verificación:* confirmed

**L3-07 · MEDIO · code · Fase 2 · esfuerzo S** — diff_graph no ve cambios de peso (Δθ): solo altas y bajas  
- *En simple:* Si una relación se vuelve más o menos crítica, el comparador de fechas no lo muestra; solo ve relaciones que aparecen o desaparecen.
- *Hoy:* ontology/service.py:548-567 compara conjuntos de claves (source,target,rel_type) sin peso ni confianza.
- *Debe ser:* v2 §8.2 P2: Δθ = {e ∈ E(t1)∩E(t2): |θe(t2)−θe(t1)| > ε}.
- *Evidencia:* Prueba local: LinkRemoved+LinkCreated TSMC→Nvidia fab con peso 6→2 el 2025-03-01; _links_active_at da pesos [6] en enero y [2.0] en junio, pero diff_graph('2025-01-01','2025-06-01') devuelve counts {'added':3,'removed':0} (los 3 son hechos fechados ajenos) y no reporta el cambio de peso.
- *Arreglo:* Indexar por (s,t,rel) → (peso, conf) y devolver 'changed': [{source,target,rel,w_from,w_to,conf_from,conf_to}] con umbral ε; exponerlo en GRAPH DIFF y en el feed.
- *Verificación:* confirmed

**L3-08 · MEDIO · code · Fase 2 · esfuerzo S** — La tabla events es append-only solo por convención: no hay disparador que impida UPDATE/DELETE  
- *En simple:* Hoy alguien con acceso a la base podría borrar o cambiar historia sin dejar rastro. Un candado en la base lo impide, igual que ya se hace con la auditoría del bróker.
- *Hoy:* ontology/models.py:39-40 lo dice en un docstring; el único disparador real es el de broker_audit (brokerage/models.py:144-166).
- *Debe ser:* v2 §8.1 y §17.3: 'append-only (disparador, Fase 2)'.
- *Evidencia:* SELECT tgname, relname FROM pg_trigger … NOT tgisinternal en base migrada → solo broker_audit_no_truncate y broker_audit_no_modify; ninguno sobre events.
- *Arreglo:* Copiar el patrón de broker_audit (función + BEFORE UPDATE OR DELETE + BEFORE TRUNCATE) para events, creado en init_schema; el --reset de migrate_v0 (base local) debe desactivarlo explícitamente con confirmación, nunca en producción.
- *Verificación:* confirmed

**L3-15 · MEDIO · code · Fase 2 · esfuerzo M** — Órdenes mutables y sin tabla de ejecuciones (fills); posiciones del usuario sin historia  
- *En simple:* Khipus no puede reconstruir qué tenías en cartera un día pasado; solo sabe lo que tienes ahora. Hay que guardar cada ejecución y una foto diaria.
- *Hoy:* brokerage/models.py:72-112 broker_orders guarda filled_qty/filled_avg_price/status/updated_at que se sobrescriben (onupdate), sin fecha de ejecución ni fills parciales; las posiciones manuales (eco_pos) se sincronizan a user_state 'último que escribe gana' (engine/sync.js:17, research/models.py:393-401).
- *Debe ser:* v2 §3.4 (posiciones como función del libro: q(t)=Σ Δq de fills) y §17.3 'fills ✚', positions_eod.
- *Evidencia:* Columnas de BrokerOrder listadas (filled_qty, filled_avg_price, updated_at con onupdate); grep 'fills' en *.py → sin tabla; user_state con PK (owner_hash,key).
- *Arreglo:* Tabla append-only broker_fills(order_id, filled_at, qty, price, alpaca_activity_id) poblada desde las actividades de Alpaca; positions_eod diaria para cuentas manuales (desde user_state) y de bróker (desde fills).
- *Verificación:* confirmed

**L3-10 · BAJO · code · Fase 1 · esfuerzo S** — Neo4j sigue recibiendo escrituras pero nadie lo lee  
- *En simple:* Se está pagando o manteniendo una base de datos (Neo4j) a la que se le envían datos que nadie usa. Se puede apagar sin perder nada.
- *Hoy:* server.py:3943-3964 POST /api/grafo/seed escribe con _neo4j_add_fact (server.py:4018-4035, MERGE Cypher); engine/temporal-graph.js:1403-1462 siembra hasta 1.000 hechos al detectar Neo4j. No existe ninguna ruta que consulte Neo4j (solo verify_connectivity en /api/grafo/estado y el 🩺).
- *Debe ser:* v2 §0.4 y §20.1 'NO: más Neo4j (se retira)'; §18 fila 1.
- *Evidencia:* grep -n 'MATCH |s.run(' server.py → solo las 2 constraints y el _FACT_CYPHER de escritura; grep neo4j en engine/*.js → solo temporal-graph.js (badge + seed).
- *Arreglo:* Quitar /api/grafo/seed, _get_neo4j_driver, _neo4j_add_fact, la tarjeta del 🩺 y el seed de temporal-graph.js; borrar el driver de requirements/constraints; regenerar la bóveda y bump de sw.js.
- *Necesita de Fabrizio:* Confirmar que se puede dar de baja la cuenta de Neo4j Aura y borrar NEO4J_URI/USER/PASSWORD en Railway.
- *Verificación:* confirmed

**L3-16 · BAJO · data · Fase 1 · esfuerzo S** — Tabla de precios de IA sin fecha de vigencia: el 1-ene-2027 el costo de Gemini 3.8 quedará subestimado 2×  
- *En simple:* Desde enero de 2027 el panel de gasto de IA mostraría la mitad de lo que realmente se paga si nadie cambia el número a mano.
- *Hoy:* core/ai_usage.py:42-43 fija 'gemini:gemini-3.8-flash': (0.75, 3.75) con un comentario 'hasta el 31-dic-2026; desde el 1-ene-2027 sube a (1.5, 7.5) → actualizar aquí'.
- *Debe ser:* v2 §2.2 regla 2 (valor = f(entidad, t)): un precio vigente por fecha, no un número pisado.
- *Evidencia:* sed -n 35,50p core/ai_usage.py (comentario y valor citados).
- *Arreglo:* PRICES con entradas {desde: fecha, in, out} y elegir por fecha de la llamada; test con reloj en 2027-01-02.
- *Verificación:* confirmed

<details><summary>Lo que este lente midió y está BIEN (7)</summary>

- ✔ Snapshot vs catálogo: 0 diferencias (937 nodos / 2.510 links idénticos)
- ✔ G(t, hoy) — as_of_graph: existe; replay 0,08-0,12 s con 4.108 eventos (sin puntos de control, suficiente hoy)
- ✔ ya arreglado Motor disperso por defecto: sí: MATRIX_ENGINE por defecto 'sparse' (matrix/engine.py:69-75) + dependency_transpose (engine.py:480)
- ✔ ya arreglado Una sola fórmula NRS: tests/test_cleanup_nrs_parity.py incluido en la suite verde
- ✔ ya arreglado test_world_feeds dependiente del reloj: corregido: monkeypatch de W._now a 2026-10-06 (tests/test_world_feeds.py:33-36)
- ✔ Tests que vencen con el calendario (sin base): 0 fallos con el reloj adelantado +90, +365 y +800 días (1.662 aprobados, 299 saltados cada vez)
- ✔ Tests con base y reloj adelantado: 13 (+90 d) y 16 (+365 d) fallos, atribuibles al método: now() de Postgres no se desplaza (p. ej. oauth 'state_expired', feed sin filas); no son bombas de tiemp…

</details>


### D. Contexto de la IA, agentes, MCP y costo — 14 hallazgos

**L4-02 · CRÍTICO · code · Fase 1 · esfuerzo S** — El guardián NO detecta precios en el formato que el propio chat exige («233,95 USD») ni '… dólares' sin unidad; tampoco porcentajes  
- *En simple:* El 'vigilante' que impide que la IA invente precios no reconoce justo la forma en que el chat escribe los precios (por ejemplo «233,95 USD»). Un precio inventado podría mostrarse como si fuera real.
- *Hoy:* core/khipu_chat.py:932 ordena al modelo escribir cifras así: «233,95 USD (Yahoo, hoy)». core/numbers.py:29 _MONEY_SUFFIX exige una unidad (B/M/mil millones) ANTES de 'USD/dólares', y _MONEY_PREFIX:27 solo atrapa '$'/'US$'/'USD ' delante. Resultado: un precio inventado en el formato pedido pasa sin marca. Los % (caídas, impactos, VaR) nunca se verifican (_RATIO_RX:35 solo se usa para excluir). research.check_numbers …
- *Debe ser:* §14/§19.12: 'corrección de los números' es prioridad 2; toda cifra de precio que llegue al usuario debe estar respaldada por el input (NUMBERS_RULE). El formato canónico del chat debe ser verificable.
- *Evidencia:* python (unsupported_in con fuente 'Nvidia price 180 USD'): 'cotiza a 233,95 USD (Yahoo, hoy)' → [] (no detectado); '233,95 dólares' → []; 'el precio es 912 USD' → []; 'Nvidia cayó 37 % hoy' → []; 'su NRS es 88' → []. En cambio 'cotiza a $233.95' → ['$233.95'] y 'US$ 233,95' → ['US$ 233,95'].
- *Arreglo:* Añadir a core/numbers.py un patrón de número + (USD|US\$|dólares|dollars|EUR…) SIN unidad obligatoria (precio unitario) y, opcional con bandera, porcentajes con signo cuando el texto habla de precio/cambio ('cayó', 'subió', 'change'). Test: el ejemplo literal de build_system ('233,95 USD') debe marcarse si no está en la fuente. Mismo arreglo vale para resea…
- *Verificación:* confirmed

**L4-M1 · CRÍTICO · math · Fase 1 · esfuerzo S** — El guardián acepta como 'respaldada' la mayoría de las cifras inventadas: la fuente es TODO el system+prompt, con ±15 % y escalas ×1000/÷1000  
- *En simple:* El 'vigilante' de cifras compara contra cualquier número que aparezca en el mensaje y con mucho margen, así que más de la mitad de los precios inventados pasarían como si fueran reales. Hay que hacerlo comparar precio con precio y con poco margen.
- *Hoy:* core/ai.py:945 source = system + prompt; unsupported_in → evidence_numbers toma CUALQUIER número del texto (pesos, NRS, grados, conteos, el ejemplo «233,95» del propio system); _supported (numbers.py:113-119) acepta si |a−c|/max ≤ 0.15 contra cualquiera de ellos, y para cifras en B también contra c×1000 y c/1000. Con ~40 números distintos en el prompt, las bandas de ±15 % cubren gran parte del rango de precios.
- *Debe ser:* §14/§19.12: una cifra de precio/capitalización solo se acepta si coincide (redondeo ~1-2 %) con un HECHO tipado de la misma entidad y la misma magnitud (precio↔precio, cap↔cap) en la tabla de hechos [F#], nunca con un peso de arista o un número del system pro…
- *Evidencia:* /tmp/audit_ctxv/hay.py sobre el prompt real del chat '¿Cómo va Nvidia?' (22.506 car., 39 números distintos, SIN datos en vivo): precios inventados uniformes $50-500 → 53,4 % pasan como respaldados; $1-1000 → 69,9 %; capitalizaciones $100B-5.000B → 81,3 %. Solo con el system prompt (números 1,2,3,5,6,7,15,20,24,25,95,100,233.95,949,950): 25,3 % de precios $5…
- *Arreglo:* Fuente = solo el bloque de datos (excluir system/NUMBERS_RULE y ejemplos), tolerancia 2 % para precios unitarios, y emparejar por TIPO: precios contra precios (quotes/live_facts), capitalizaciones contra capitalizaciones; sin escalas ×1000 salvo que la unidad lo justifique. A medio plazo: cotejar contra la tabla de hechos [F#] del motor de contexto (L4-01).…
- *Verificación:* hallado por el verificador

**L4-01 · ALTO · both · Fase 1 · esfuerzo M** — No existe un motor de contexto único con relevancia R(v|Q) y presupuesto; hay ≥9 armadores de contexto y 3 detectores de entidades que no coinciden  
- *En simple:* Hoy cada parte de la app arma por su cuenta lo que le cuenta a la IA y hasta detectan empresas distintas en la misma pregunta. Un solo 'seleccionador' haría que la IA reciba solo lo importante, con menos gasto y respuestas más coherentes.
- *Hoy:* core/context_engine.py no existe. Contexto para LLM armado por separado en: core/khipu_chat.py build_prompt:1022 + bucle de herramientas + _compact_for_chat:963; core/live_facts.py live_facts_block; core/semantic.py build_context:105; research/context.py ContextBuilder.build:240 (+subgraph:197 que recorre los 2.510 vínculos por profundidad y ordena por w×conf); research/agent_skills.py skill_packet; research/debate.…
- *Debe ser:* §13.2-13.4: un solo core/context_engine.py: resolución determinista → vecindario de FLUJO por intención → R(v|Q)=π_Q·frescura·(ε+I_v)·(1+λU_v) con π_Q = PPR o Ψ[v,S_Q] → empaquetado voraz de cobertura ponderada bajo presupuesto B → tabla de hechos [F#] + resu…
- *Evidencia:* grep -rniE 'pagerank|personalized|token_budget|submodular|\[F#' core research mcp_server → solo core/screener.py (ranking de PageRank para el screener), nada de contexto. /tmp/audit_lens4/ent.py sobre 15 preguntas: core.semantic.extract_companies vs core.live_facts.detect_entities discrepan en 6/15 (p. ej. 'meta capex' → semantic=['Meta'], live_facts=[]; 'r…
- *Arreglo:* Crear core/context_engine.py (sin IA, sin embeddings en Fase 1): entidades vía core.entities.resolve (un solo detector; borrar extract_companies/detect_entities duplicados o hacerlos delegar), π_Q con PPR sobre la matriz de flujo dispersa ya existente (matrix/engine) o Ψ[:,S_Q] para preguntas de impacto, R(v|Q) multiplicativo, empaquetado voraz ΔF/tok vs me…
- *Verificación:* confirmed

**L4-03 · ALTO · both · Fase 1 · esfuerzo S** — scenario_exposure y la simulación por agentes propagan golpes por aristas partner/invest/about y las etiquetan como 'cliente'/'proveedor'  
- *En simple:* En los '¿qué pasa si…?', 1 de cada 8 empresas 'afectadas' aparece solo porque es socia o inversora, no porque compre o venda algo; el informe las llama 'clientes' por error.
- *Hoy:* core/scenario_engine.py:300-319 recorre snap['out'] / snap['in'] (core/semantic._load_snapshot, TODOS los tipos) sin filtrar por flow_relation_types: clientes a 2 saltos (top 12 por peso) y proveedores (top 8). Lo usan el chat (core/khipu_chat.py x_scenario_exposure:418) y core/sim_agents.py:558. MCP, core/semantic.build_context, research/context (línea 469) y matrix/tensor SÍ filtran flujo (ok).
- *Debe ser:* §13.2 paso 2 y §20.1 #5: 'solo FLUJO salvo que se pida'; prueba 'cero aristas partner como proveedor'. Regla G4a de CLAUDE.md.
- *Evidencia:* /tmp/audit_lens4/scen_leak2.py: 11 escenarios, 161 impactos de cadena (customer/second_order/supplier); 20 (12,4 %) solo existen por aristas no-flujo. Ejemplos: 'Taiwan blockade' → HMM 'customer' vía 'Yang Ming → HMM (Premier Alliance desde feb-2025)'; 'US export ban on Nvidia chips to China' → TSMC 'customer' vía 'Synopsys → TSMC (Reference flow N3/N2…)' y…
- *Arreglo:* En analyze() usar snap filtrado a flow_relation_types (o pasar kinds), igual que t_get_supply_chain; mantener partner/invest solo como 'relacionados' con include_partners explícito. Test: ninguna ruta de impacto usa una arista no-flujo. A medio plazo, que scenario_engine solo SIEMBRE el choque y propague con el kernel único (matrix/engine.propagate).
- *Necesita de Fabrizio:* Confirmar que las alianzas/sociedades (p. ej. alianzas navieras) NO deben transmitir golpes por defecto (se podrían mostrar aparte como 'relacionadas').
- *Verificación:* confirmed

**L4-04 · ALTO · both · Fase 1 · esfuerzo M** — En la simulación por agentes la IA decide los % de impacto por empresa (números), no el kernel  
- *En simple:* En la sala de guerra, los porcentajes de cuánto 'cae' cada empresa los inventa la IA dentro de unos topes. Deberían salir de la fórmula del grafo, y la IA solo explicarlos.
- *Hoy:* core/sim_agents.py:587-640: en cada ronda el LLM (tier deep) devuelve impacts[{id, pct}] y esos % se muestran tal cual tras _clamp_pct:259 (topes ±12 mega / ±20 mid / ±35 small, _BOUNDS:52). El guardián no revisa % (ver L4-02). El análisis estructural (scenario_engine) solo aporta caminos.
- *Debe ser:* §14: 'la IA argumenta, la matemática decide los números'; §15 run_scenario = impacto por el kernel ÚNICO + P&L con bandas; §20.1 #4 scenario_engine siembra y propaga con el kernel único.
- *Evidencia:* /tmp/audit_lens4/sim.py con proveedor simulado: SA.run('Taiwan blockade',['TSMC']) → 2 llamadas deep de 1.793+10.177 y 1.793+10.202 caracteres (≈5.991 tokens) y la salida impacts = [('TSMC', -11.0), ('Nvidia', -9.0)], exactamente los números que inventó el stub del modelo.
- *Arreglo:* Calcular los % con matrix/engine.propagate (Ψ, choque sembrado por scenario_engine) y pasarlos al LLM como datos fijos; el LLM solo narra/argumenta y cita. Validar que cada pct de la salida coincide con el del kernel (rechazo si no). Etiquetar 'estimación estructural, no precio'.
- *Verificación:* confirmed

**L4-05 · ALTO · code · Fase 1 · esfuerzo S** — Resultados de herramientas duplicados en el prompt: la ficha pre-consultada se vuelve a pegar entera cuando el modelo la pide  
- *En simple:* Para una pregunta simple como '¿cómo va Nvidia?', la IA recibe la misma ficha dos veces: casi la mitad del texto es repetido y se paga dos veces.
- *Hoy:* run_chat pre-consulta get_company (línea 2489-2508, scratch.append) y la receta del sistema pide 'get_company + get_news' para '¿cómo va X?'. En el bucle (2596-2625) un resultado servido desde la caché se agrega OTRA VEZ a scratch (2625) — además la clave de caché distingue 'Nvidia' de 'nvidia'.
- *Debe ser:* §13.5: no repetir pasos; contexto de herramientas de ~6-7k a ~1,5-2k tokens.
- *Evidencia:* /tmp/audit_lens4/chat_tokens.py: 2.º prompt de '¿Cómo va Nvidia?' = 14.440 caracteres, de los cuales [1] get_company 7.032 y [2] get_company 7.054 (misma ficha dos veces, ≈49 %). /tmp/audit_lens4/dup.py con la clave EXACTA ('Nvidia'): 'get_company entries in last prompt: 2'.
- *Arreglo:* Clave de caché con el id canónico (resolver antes) y no volver a anexar a scratch un resultado ya presente (anexar solo '[n] ya consultado arriba'). Test: una pregunta '¿cómo va X?' no contiene la ficha dos veces.
- *Verificación:* confirmed

**L4-08 · ALTO · code · Fase 1 · esfuerzo S** — Sin 'detail'/'max_chars' ni contrato común: get_supply_chain de Nvidia a profundidad 2 = 112k caracteres (×2 con structuredContent)  
- *En simple:* Cuando otra IA (Claude, ChatGPT) consulta Khipus, recibe respuestas enormes: la cadena de Nvidia a dos niveles pesa como un libro. Con un modo 'resumen' sería unas 20 veces más liviana.
- *Hoy:* mcp_server/tools.py no tiene parámetros detail ni max_chars; mcp_server/protocol.py:_tool_result (≈97-112) repite el JSON en content[0].text y structuredContent; único tope MAX_RESULT_CHARS=240_000 (protocol.py:35). Campos del contrato v2: 'uncertainty', 'valid_at', 'known_at', 'tokens_estimate', 'detail' = 0 apariciones; 'sources' solo en get_company.
- *Debe ser:* §15: toda respuesta {data, as_of, valid_at, known_at, sources[], method, uncertainty, detail, truncated, tokens_estimate}; detail∈{brief,full}; max_chars; brief de get_entity ≈1,5k.
- *Evidencia:* /tmp/audit_lens4/mcp_sizes.py (principal falso, sin red): get_company(nvidia, include_live=false) 11.043 caracteres (22.086 con la copia ≈5.5k tokens); get_supply_chain nvidia depth=1 32.195 (64.390); depth=2 112.354 (224.708 ≈56k tokens); depth=2 limit=60 160.366 (320.732); tsmc depth=2 limit=60 109.074. Catálogo MCP: 23 herramientas, 20.905 caracteres.
- *Arreglo:* Añadir detail (brief por defecto: identidad + NRS + top-5 proveedores/clientes por R/peso + conteos; full = actual) y max_chars a todas las operaciones de lectura; envoltorio común con as_of/sources/method/truncated/tokens_estimate; recorte ordenado (no por posición) con resumen de la cola. Test: brief de get_company ≤ 1.500 caracteres; depth 2 brief ≤ 8k.
- *Verificación:* adjusted — Raw sizes re-measured and match (get_company 11,043; supply_chain depth1 32,195; depth2 112,354; depth2 limit60 160,366). Contract fields detail/max_chars/uncertainty/valid_at/known_at/tokens_estimate = 0 occurrences. The token figures are inflated, though. The MCP 2025-06-18 spec RECOMMENDS repeat…

**L4-09 · ALTO · code · Fase 1 · esfuerzo L** — De las 11 operaciones de v2 §15 solo 2 existen, 2 parcialmente y 7 faltan; los escenarios solo existen dentro del chat  
- *En simple:* Las IAs externas no pueden pedirle a Khipus cosas clave como '¿qué pasa si…?', 'empresas parecidas' o 'mi exposición'; algunas de esas cosas solo existen dentro del chat de la app.
- *Hoy:* MCP expone 23 herramientas (mcp_server/tools.py): search_companies, get_company, get_supply_chain, get_ontology_object, get_research, get_claim_evidence, get_research_job, get_risk_report, get_option_greeks, get_world_events, get_committee_memo, get_conclusions_board, get_research_health, get_track_record, run_research, run_committee + 7 de trading. Chat: 17 herramientas (10 de MCP + 7 propias: get_news, ask_agent, …
- *Debe ser:* §15: get_entity, get_relationships, get_subgraph(presupuesto), get_history, get_exposure, calculate_risk, calculate_correlation, run_scenario, find_similar_entities, find_anomalies, project_portfolio; un solo catálogo para chat y MCP.
- *Evidencia:* Mapeo: get_entity≈get_company ✔(sin brief); calculate_risk≈get_risk_report ✔; get_relationships≈get_supply_chain(depth1) ◐; get_history≈get_ontology_object (eventos, sin series de precios) ◐; get_subgraph, get_exposure, calculate_correlation, run_scenario, find_similar_entities (matrix/tensor peers solo como 'peers' top-3 en get_company.structure), find_ano…
- *Arreglo:* Fase 1: get_subgraph sobre el motor de contexto (L4-01), run_scenario sobre el kernel único (sacar scenario_exposure del chat a mcp_server/tools), get_exposure (asesor+tensor), find_similar_entities (tensor.peers con puntaje por espacio), calculate_correlation (extraer de risk_report). Un registro único de herramientas que use el chat. get_history con serie…
- *Necesita de Fabrizio:* Elegir el orden de prioridad de las operaciones que faltan (sugerido: run_scenario, get_subgraph, get_exposure primero).
- *Verificación:* confirmed

**L4-06 · MEDIO · code · Fase 1 · esfuerzo S** — Sin caché de prompt en ningún proveedor y ai_usage mezcla lecturas/escrituras de caché en un solo número  
- *En simple:* Cada pregunta reenvía el mismo manual de instrucciones a la IA y se paga completo. Guardarlo en caché abarata las preguntas largas, y hoy ni siquiera podemos medir cuánto se ahorraría.
- *Hoy:* core/ai.py:523 manda system como texto plano (sin cache_control). core/ai.py:509-510 suma cache_creation_input_tokens ×1,0 (Anthropic cobra 1,25×) y cache_read ×0,1 dentro de tokens_in; core/ai_usage.record:364 solo tiene tokens_in/tokens_out (sin columnas de caché). Gemini (core/ai.py:760) concatena system+prompt en 'contents' y record (:793) ignora cachedContentTokenCount. Prefijo estable del chat: build_system = …
- *Debe ser:* §20.1 #7: caché donde el modelo lo permita (nivel profundo, prefijo ≥ mínimo) + ai_usage con cache_read / cache_write separados; costo medido antes/después.
- *Evidencia:* grep -rn 'cache_control\|cache_read' --include=*.py . (sin tests) → solo core/ai.py:510 (contabilidad). Chat medido: system de 8.063 caracteres reenviado en CADA llamada (2-3 por pregunta).
- *Arreglo:* 1) ai_usage: columnas tokens_cache_read/tokens_cache_write (vía ontology/db._COLUMNAS_TARDIAS) y precio 1,25×/0,1× en cost_of; leer cachedContentTokenCount de Gemini. 2) core/ai: system como bloque con cache_control solo en el nivel profundo y solo si el prefijo estable (sistema + catálogo) supera el mínimo del modelo; para Gemini usar systemInstruction sep…
- *Verificación:* adjusted — Accounting part confirmed. core/ai.py:509-510 folds cache_creation at 1.0× (Anthropic charges 1.25×) and cache_read at 0.1× into one tokens_in. Gemini :793 records promptTokenCount and ignores cachedContentTokenCount. No cache_control appears anywhere (grep). But 'sin caché en ningún proveedor' is …

**L4-07 · MEDIO · code · Fase 1 · esfuerzo S** — En preguntas de análisis la respuesta final se escribe dos veces (rápido y luego profundo): 3 llamadas  
- *En simple:* En las preguntas 'difíciles' se paga una respuesta completa que después se tira y se reescribe con el modelo caro.
- *Hoy:* core/khipu_chat.py:2577-2588: con deep_final el modelo rápido ya entrega su 'final' completo y luego _deep_final:2211 vuelve a mandar todo el contexto al modelo profundo.
- *Debe ser:* §13.5 / §20.1 #7: 'el modelo profundo escribe una sola vez' (−1 llamada completa ≈ −5k tokens).
- *Evidencia:* /tmp/audit_lens4/chat_deep.py (Jev → needs_deep_reasoning): 3 llamadas IA, 39.624 caracteres ≈ 9.906 tokens: [fast] 8.063+330, [fast] 8.063+7.516 (respuesta descartada), [deep] 8.063+7.589.
- *Arreglo:* Cuando la ruta es needs_deep_reasoning, pedir al modelo rápido solo herramientas (forzar 'tool'/'calls' o detener al primer 'final' sin pedir redacción) y que el profundo escriba la única respuesta; el rápido solo como respaldo si el profundo falla.
- *Verificación:* confirmed

**L4-10 · MEDIO · both · Fase 1 · esfuerzo S** — La compactación del chat recorta por posición sin relevancia ni resumen de la cola: a profundidad 2 sobreviven 12 de 282 aristas (todas de 1 salto)  
- *En simple:* Cuando se pregunta por la cadena completa de una empresa, la IA ve solo las primeras 12 relaciones y nada del segundo nivel, sin saber qué se dejó afuera.
- *Hoy:* core/khipu_chat.py:_fmt_result:998 / _compact_for_chat:963 con MAX_TOOL_RESULT_CHARS=7000 (línea 59): baja niveles (_CHAT_LEVELS:946 → listas de 25 y luego 12) y deja '…+N'. MAX_SCRATCH_CHARS=26000 recorta lo más viejo por caracteres. En investigación, la evidencia del grafo se corta a 700 caracteres (research/context.py add max_chars=700) aunque se armen 15 líneas.
- *Debe ser:* §13.4: empaquetado bajo presupuesto por R(f|Q) con cobertura ponderada y resumen de la cola con estadísticos suficientes (conteo, peso total, máximo, países).
- *Evidencia:* /tmp/audit_lens4/compact.py: get_supply_chain nvidia depth1 → 50 aristas/46 nodos → chat 6.038 caracteres, 12 aristas y 12 nodos; depth2 → 282 aristas/184 nodos (113.419 caracteres) → 6.042 caracteres, 12 aristas, hops [1×12], marca '…+270' sin estadísticos. Investigación supply_chain de Nvidia: subgrafo 12 aristas, excerpt 700 caracteres con 9 visibles.
- *Arreglo:* Reemplazar el recorte por el empaquetador del motor de contexto (L4-01): ordenar aristas por R(e|Q)=√(R(u)R(v))·w̃·c, incluir los 2 saltos según la intención y cerrar con una línea de cola ('otros 270 vínculos: X % del peso, países…'). En investigación, quitar el tope de 700 para la evidencia de grafo o usar la tabla compacta.
- *Verificación:* adjusted — The cut is not purely by position. MCP _edges sorts each node's list by -w (tools.py:468), and _balance_edges (khipu_chat.py:952) interleaves suppliers and customers, so the 12 survivors are the heaviest 1-hop edges on each side. That is a weight proxy for relevance. The real defects: (1) _balance_…

**L4-11 · MEDIO · code · Fase 1 · esfuerzo S** — Sin pool de evidencia compartido: cada analista vuelve a traer las mismas noticias de la misma empresa  
- *En simple:* Cuando el equipo de analistas investiga una empresa, cada uno vuelve a pedir las mismas noticias por separado: más lento, más gasto y más riesgo de que las fuentes nos bloqueen.
- *Hoy:* research/runner.py:486 crea un ContextBuilder por analista (fetchers=None en producción); research/context._fetch_news:73 (GDELT) y _fetch_company_news:87 (Finnhub) no tienen caché; las 8 entradas de AGENT_NEEDS (context.py:24-35) incluyen 'news'. El sistema de cada analista (schema JSON + reglas) ≈3,4-4,1k caracteres se reenvía por analista y por reintento (max_attempts=3, base.py:105).
- *Debe ser:* §13.5: 'pool de evidencia compartido por (entidad, fuente, día) para los 4 analistas — noticias y perfil se traen 1 vez, no 4'.
- *Evidencia:* /tmp/audit_lens4/research_tokens2.py (fetchers simulados que cuentan llamadas, 1 job con los 8 analistas, STANDARD): fetch calls {'news(gdelt)': 8, 'company_news(finnhub)': 8, 'profile': 12, 'sec_filings': 3, 'financials': 2, 'candles': 2}; prompt por analista 2.773-3.281 tokens (solo noticias de relleno; sin estados financieros ni SEC) ≈24.279 tokens el jo…
- *Arreglo:* Caché por (entidad, fuente, día) dentro del job (memo compartido entre hilos en runner._execute_job, pasando fetchers memoizados) y caché TTL corto para GDELT/Finnhub; el sistema estable de los analistas candidato a caché de prompt (L4-06).
- *Verificación:* adjusted — Only the news part holds. Profile and financials are already memoized process-wide in core/company_data.py (_LIVE_CACHE / _FIN_CACHE, _cache_get at :663, get_annual_financials use_cache at :723). The 12 'profile' fetches the auditor counted came from simulated fetchers that bypass that cache. resea…

**L4-M2 · MEDIO · both · Fase 1 · esfuerzo S** — scenario_engine elige productores y ordena impactos con el grado TOTAL (incluye partner/invest/about), contra la regla G4d  
- *En simple:* Al decidir qué empresas 'importan' en un escenario, la app cuenta también socios e inversores, así que empresas como SoftBank o Anthropic parecen más centrales en la cadena de lo que son.
- *Hoy:* core/semantic.py:43-46 calcula snap['deg'] sobre TODOS los vínculos (además de flow_deg). scenario_engine lo usa para elegir 'empresas clave' de un país (:230, :276), desempatar text_search (:197) y ordenar impactos 'magnitud × relevancia' (:344 rel = 0.45 + min(deg,30)/30 …). khipu_chat.py:502 muestra ese mismo grado total en rank_companies (aunque el NRS usa flow_deg).
- *Debe ser:* CLAUDE.md G4d: el grado es ESTRUCTURAL (pares distintos de flujo) en cliente, servidor y catálogo; §13.2 'solo FLUJO salvo que se pida'.
- *Evidencia:* python sobre core.semantic._load_snapshot(): 626 de 914 nodos tienen deg > flow_deg; Nvidia 196 vs 138, TSMC 175 vs 151, SpaceX 51 vs 27, Anthropic 31 vs 9, SoftBank 19 vs 2; solapamiento top-30 por grado total vs flujo = 26/30.
- *Arreglo:* Usar snap['flow_deg'] en scenario_engine (:197, :230, :276, :344) y en rank_companies (:502); borrar snap['deg'] si no queda otro uso. Test: ningún ranking de escenario usa grado no estructural.
- *Verificación:* hallado por el verificador

**L4-12 · BAJO · code · Fase 2 · esfuerzo M** — La voz repite cifras con su propio modelo sin guardián; la confirmación de órdenes aún depende de que el modelo vuelva a llamar la herramienta  
- *En simple:* Lo que Khipu dice en voz alta lo resume otra IA y nadie revisa que repita bien los números; en pantalla sí están verificados.
- *Hoy:* engine/voice.js _toolBrain:1340 devuelve al agente de ElevenLabs la respuesta del chat (hasta 2.500 caracteres, ya verificada) y el agente la RESUME con su LLM; server.py:4094 pide decir los % de la simulación. Nada verifica lo que se dice en voz. Órdenes: voice.js:1900-1925 exige confirmed=true + resumen previo de ≤3 min (VOICE_ORDER_PREVIEW_MS:46) y la tarjeta en pantalla permite confirmar con clic — seguro, pero …
- *Debe ser:* §14 (la IA narra, los números son del sistema) y guardián de cifras en toda ruta que llegue al usuario.
- *Evidencia:* server.py:4094-4210 (reglas: 'Never quote a price… from memory', 'USING THE % THE SIMULATION RETURNED' — solo instrucciones, sin verificación). voice.js:1129-1135 (pending:true tras el tope), 1909-1923 (resumen obligatorio).
- *Arreglo:* Pasar a la voz una línea 'speak' ya redactada y verificada por el servidor (resumen corto con las cifras del chat) e instruir a decirla literal, como el recorrido; opcional: verificar la transcripción del agente (evento agent_response) contra las cifras de la respuesta y marcar en pantalla si difiere.
- *Verificación:* confirmed

<details><summary>Lo que este lente midió y está BIEN (7)</summary>

- ✔ Tokens @cadena Nvidia (ask_agent, sin red ni BD): 1 llamada deep, 1.995 + 2.873 car. ≈ 1.217 tokens (cota inferior: sin paquete en vivo)
- ✔ Fuga partner/invest como proveedor — MCP, core/semantic, research/context, matrix/tensor: 0: todos filtran flow_relation_types (get_company counts Nvidia: 45 proveedores / 97 clientes / 54 relacionados aparte)
- ✔ Guardián de cifras — cobertura de rutas: chat, portafolio, reportes, sim, ontología, insights pasan por _ai_complete (23 llamadas); investigación/debate/presidente usan check_numbers/_money_check; sol…
- ✔ Agentes deterministas (Risk/Compliance/Trading): riesgo = core/risk_report (fórmulas); cumplimiento = brokerage/risk.py límites por perfil + aprobación con PIN; trading preview→confirm; IA solo narra en portf…
- ✔ ya arreglado Fórmula NRS única (texto de la voz coincide): core/world.client_nrs: geo 0-30 + cadena min(25, 2,5·grado de flujo) + margen 0-20 + fundamentales 0-15 + concentración 4/10 — igual a lo descrito en BIXBY_SYS…
- ✔ ya arreglado Recorrido de voz dependiente de que el LLM encadene 'next': ya no: voice.js marca el ritmo con [TOUR n/N] (máx. 2 envíos por paso) y respaldo local
- ✔ Órdenes por voz sin resumen previo: bloqueadas en el cliente: confirmed=true sin resumen de ≤3 min vuelve a ser resumen; tarjeta en pantalla

</details>


### E. Estructura del código, dinero y despliegue — 24 hallazgos

**G5-01 · ALTO · code · Fase 1 · esfuerzo M** — Tres caminos de órdenes a la MISMA cuenta Alpaca con controles distintos; /api/trade/order se salta los controles de riesgo y el interruptor de dinero real del corretaje  
- *En simple:* Hoy tu propia cuenta se puede operar por una puerta que no revisa el límite diario ni pide el permiso extra para dinero real. Hay que pasar todas las compras y ventas por la misma revisión de seguridad.
- *Hoy:* La cuenta de la casa (ALPACA_KEY) recibe órdenes por 3 caminos: brokerage/alpaca.py:179 (vía preview_order/confirm_order, con brokerage/risk.run_checks = 34 controles: % por posición, tope diario USD, drawdown, mandato, ventana de duplicados, desvío del límite, y exige BROKERAGE_LIVE_ENABLED=on + client.live_enabled para dinero real), server.py:2722 (/api/trade/order, que usan el panel de app.html:11236, engine/cryp…
- *Debe ser:* CLAUDE.md 'DINERO — regla de oro': toda orden pasa por brokerage.service.preview_order → confirm_order; 'Nunca crear otro camino que envíe órdenes a Alpaca'. v2 §19.9: Risk/Trading deben ser servicios deterministas únicos.
- *Evidencia:* grep -rn 'v2/orders' --include=*.py → brokerage/alpaca.py:179, server.py:2722, server.py:5446. grep -c "_c('" brokerage/risk.py → 34. grep 'BROKERAGE_LIVE_ENABLED\|live_env_enabled' server.py → 0 resultados. grep MAX_ORDER_USD → server.py:2214 y brokerage/risk.py:40 (HARD_MAX_ORDER_USD, comentario 'igual que /api/trade/order').
- *Arreglo:* Hacer que /api/trade/order y _agent_submit llamen brokerage.service.preview_order(HOUSE_ID,…) + confirm_order (el humano ya confirmó en la UI) en vez de requests.post directo; borrar el código de validación duplicado en server.py; el agente usa la misma ruta con actor='agente-trading'. Mantener la respuesta JSON actual para no romper la UI.
- *Necesita de Fabrizio:* Decidir los límites de TU cuenta (tope diario en USD, % máximo por empresa) y si tu cuenta puede operar con dinero real (BROKERAGE_LIVE_ENABLED).
- *Verificación:* adjusted — Real, but the gap is wider than described for /api/trade and narrower for the agent. (1) /api/trade/order confirmed. It only checks format, MAX_ORDER_USD=100000 (server.py:2214, 2679, 2706) and the kill switch _house_trading_enabled (server.py:2711), then POSTs straight to Alpaca (server.py:2722). …

**G5-02 · ALTO · code · Fase 1 · esfuerzo S** — Ninguna prueba corre antes de desplegar: push a main despliega sin CI  
- *En simple:* Hoy un cambio con error puede llegar a la app en 2 minutos sin que nadie lo revise. Con esto, las 1.942 pruebas se corren solas antes de publicar y frenan lo roto.
- *Hoy:* El único workflow es .github/workflows/smoke-mcp.yml (instala requests y hace humo del MCP después del deploy). No hay job que corra pytest. railway.toml despliega con cada push a main. 299 de 1.961 pruebas (15 %) solo corren con DATABASE_URL (la PC de Fabrizio).
- *Debe ser:* Regla de despliegue 4 de CLAUDE.md (pytest antes de commit) hecha cumplir por máquina; v2 Fase 1: cada entregable 'con prueba que lo fija'.
- *Evidencia:* ls .github/workflows → smoke-mcp.yml solamente. pytest tests/ (sin BD) → 1662 passed, 299 skipped en 304 s; con DATABASE_URL=…khipus_test → 1942 passed, 19 deselected en 327 s (0 fallos). Es decir, la suite está verde y es barata: solo falta que corra sola.
- *Arreglo:* Workflow de GitHub Actions con servicio postgres:16 + node 22 + playwright: pytest tests/ -q en cada push/PR; en Railway activar 'Wait for CI' (o desplegar solo desde una rama que exige check verde).
- *Necesita de Fabrizio:* Activar en Railway la opción 'Wait for CI' (o aceptar desplegar desde una rama protegida); GitHub Actions es gratis para este uso.
- *Verificación:* confirmed

**G5-03 · ALTO · both · Fase 1 · esfuerzo M** — El simulador del navegador (statematrix.js) NO usa el mismo kernel que el servidor aunque su comentario dice 'idéntica'  
- *En simple:* Si simulas una crisis en TSMC, el mapa dice que afecta a 218 empresas y el servidor dice 294. La app da dos respuestas distintas a la misma pregunta; hay que dejar una sola.
- *Hoy:* engine/statematrix.js:118-128 combina por MÁXIMO entre proveedores ('eslabón más débil'), 8 iteraciones, sin umbral 1 % y sin FRAGILITY_CAP; matrix/engine.py:427-478 (propagate) SUMA por fila (DT @ cur), 6 saltos, umbral 0,01 y tope de fragilidad 2,5 (engine.py:355). El comentario de statematrix.js:116 dice 'idéntica a matrix/engine.py'.
- *Debe ser:* v2 §20.1 #4: kernel único (suma, 6 saltos, umbral, tope de fragilidad) o réplica con prueba de paridad sobre 937 choques; §18 '4 kernels → 1'.
- *Evidencia:* /tmp/audit_lens5/kern_srv.py + kern_cli.js sobre data/grafo_v0.json, mismos pesos y confianzas, sin factores: TSMC servidor 294 nodos vs cliente 218 (136 nodos difieren >1 punto, máx 20,0 pts); Nvidia 206 vs 133 (101 nodos, máx 17,9); ASML 67 vs 65 (38 nodos, máx 7,7).
- *Arreglo:* Opción A (preferida): livesim/xray piden POST /api/matrix/impact y el cliente solo anima los saltos que devuelve. Opción B: reescribir simulate() como suma+6 saltos+umbral+tope y añadir test de paridad cliente↔servidor sobre los 937 choques (como test_cleanup_nrs_parity). Corregir el comentario.
- *Verificación:* confirmed

**G5-05 · MEDIO · code · Fase 2 · esfuerzo L** — server.py mezcla 12+ responsabilidades (trading y su agente, voz, salud, Neo4j, API pública /v1, proxies) en 5.977 líneas  
- *En simple:* El archivo principal del servidor hace de todo a la vez; cada cambio toca un archivo gigante y es fácil romper otra cosa. Separarlo por temas hace la app más segura de modificar.
- *Hoy:* server.py: 5.977 líneas, 89 rutas, 190 funciones de primer nivel, 135 'except Exception' (20 seguidos de pass). Líneas aproximadas por dominio: voz ~790 (rutas /api/voice/* + prompt + audio del recorrido, 4228-4810 y 283-430) aunque existe core/voice_agent.py; trading ~570 (2200-2770) + agente de trading ~755 (5190-5945); salud/diagnóstico ~780; Neo4j /api/grafo/* ~500; /v1 monetizada (4883-4999); cripto, espacio, c…
- *Debe ser:* v2 §17.13 ficha por componente; un módulo por responsabilidad para poder evolucionar (§20.1 #1-#8 añaden tablas y servicios nuevos).
- *Evidencia:* wc -l server.py → 5977; grep -c '@app.route' → 89; script de spans por grupo → voice 788, health 622, supply-chain 558, trade 535, grafo 507 líneas; grep broad except → 135.
- *Arreglo:* Mover a blueprints sin cambiar rutas: brokerage/house_api.py (/api/trade/* + agente, ver G5-01), core/voice_api.py (/api/voice/*), public_api.py (/v1/*), core/diag_api.py (/api/health,/api/diagnostics), y retirar /api/grafo/* con Neo4j (G5-12). Un blueprint por PR con la suite verde.
- *Verificación:* adjusted — The sizes hold: 5977 lines, 89 @app.route, 190 top-level defs. I count 136 'except Exception' (the audit says 135). The Neo4j/grafo share is overstated, though. Only 2 routes exist (/api/grafo/estado at 3895, /api/grafo/seed at 3943). The Neo4j block runs from 3889 to 4092 (about 200 lines), plus a…

**G5-06 · MEDIO · code · Fase 2 · esfuerzo L** — app.html: 12.665 líneas con 9.737 de JavaScript en línea, 293 variables globales y 82 scripts sin sistema de módulos  
- *En simple:* Toda la pantalla vive en un solo archivo enorme. Eso hace lento y riesgoso cada arreglo y no deja activar protecciones de seguridad más fuertes.
- *Hoy:* app.html 762 KB: 10 bloques <script> en línea (325, 4816, 118, 51, 15, 2693, 607, 142, 689, 281 líneas), 1.847 líneas de CSS en línea, 314 funciones, 159 window.* propias; en todo el front 293 globales window.* distintas; 82 <script src> síncronos (78 locales + 4 CDN) cuyo orden es el contrato; 245 manejadores on*= en línea (lo que obliga a 'unsafe-inline' en la CSP).
- *Debe ser:* v2 §17 arquitectura por capas; condición para endurecer la CSP (G5-09) y para probar la UI por partes.
- *Evidencia:* python sobre app.html → inline blocks 10 [325, 4816, …], style lines [1425,106,188,128], function decls 314; cat app.html engine/*.js nodes/*.js sim/*.js | grep window.X= | sort -u → 293; grep -c '<script[^>]*src=(engine|nodes|sim)' → 78; on*= → 245.
- *Arreglo:* Sacar progresivamente cada bloque en línea a engine/<tema>.js (mapa, mercado, trading, sistema), empezando por el de 4.816 líneas; agrupar globales bajo window.Khipu.*; reemplazar on*= por addEventListener en los archivos que se extraen.
- *Verificación:* confirmed

**G5-07 · MEDIO · code · Fase 2 · esfuerzo M** — engine/cockpit.js (4.991 líneas, ~25 responsabilidades incluida la pantalla del bróker) y engine/voice.js (3.024)  
- *En simple:* La pantalla principal de Khipus OS también es un solo archivo gigante que mezcla el chat, la voz y el bróker. Separarla evita que arreglar una ventana rompa otra.
- *Hoy:* cockpit.js reúne: barra superior, menús, paleta ⌘K, columna de chat, micrófono, adopción de paneles, registro de pantallas, cripto, terminal, capa proactiva de inicio, selector de empresa, comparar fundamentales, screener, insights del hipergrafo, STAGE BRÓKER (dinero), informe de portafolio y modo demostración (banners en el archivo). voice.js 3.024 líneas incluye su propio envío de órdenes (2915-2990).
- *Debe ser:* KHIPUS_OS: 'una sola puerta' y ventanas nativas registradas (oswindows.js registerKind) — cada escena debería ser un módulo.
- *Evidencia:* wc -l engine/cockpit.js engine/voice.js → 4991, 3024; grep de banners '/* ══' y '// ──' en cockpit.js → ~30 secciones; 265 funciones con nombre en cockpit.js.
- *Arreglo:* Extraer cada escena a engine/scenes/<kind>.js registrada con BixbyCockpit.registerKind (empezar por broker, screener, compare, demo); cockpit.js queda como cáscara.
- *Verificación:* confirmed

**G5-08 · MEDIO · code · Fase 1 · esfuerzo S** — Tres copias del código que envía órdenes desde el navegador  
- *En simple:* Comprar desde el panel, desde cripto o por voz usa tres programas distintos. Si se corrige un error en uno, los otros dos siguen con el error.
- *Hoy:* app.html:11236 (panel de trading), engine/crypto.js:607-650 y engine/voice.js:2958-2990 re-implementan cada uno: armar el cuerpo, client_order_id (_tradeOrderId), detección de duplicado, notificación KhipuToast y manejo de error.
- *Debe ser:* CLAUDE.md: toda compra/venta debe confirmar y notificar por KhipuToast; una sola ruta de dinero.
- *Evidencia:* grep 'api/trade/order' app.html engine/*.js → app.html:11236, engine/crypto.js:627, engine/voice.js:2968; grep _tradeOrderId → crypto.js:610, voice.js:2962 además de app.html.
- *Arreglo:* Una sola función window.KhipuOrder.submit(order) en engine/toast.js o app.html (confirmOrder → _tradeFetch → settle/dup → notificación) usada por los tres; test de node que la ejercita.
- *Verificación:* adjusted — A shared function already exists, so the fix should reuse it, not create KhipuOrder. window._executeTradeOrder (confirm → client_order_id → _tradeFetch → dup → KhipuToast) is defined in engine/voice.js:2918. cockpit.js (2945, 3298) and voice.js (1928) use it. The remaining copies are the app.html p…

**G5-09 · MEDIO · code · Fase 2 · esfuerzo M** — CSP débil ('unsafe-inline' + 'unsafe-eval' + connect-src a cualquier https) con el PIN de trading en localStorage  
- *En simple:* Las defensas del navegador están muy abiertas y el PIN de tu cuenta se guarda donde un código malicioso podría leerlo. Hay pasos sencillos para cerrar la mayor parte del riesgo.
- *Hoy:* server.py:625-639: script-src 'self' 'unsafe-inline' 'unsafe-eval'; connect-src 'self' https: wss:; img-src https:. El comentario justifica connect-src por el 'modo standalone' que ya se borró. El PIN vive en localStorage (app.html:1554 khipu_trade_pin), legible por cualquier script inyectado. 574 asignaciones a innerHTML; 30 copias de esc(), 10 de ellas sin escapar ' (engine/termdata.js:78, matrixview.js:28, compar…
- *Debe ser:* Endurecimiento 2026-09-30 de CLAUDE.md ('esc() escapa '''); dinero real detrás del PIN.
- *Evidencia:* grep eval(|new Function( en app.html/engine/nodes/sim → 0 (unsafe-eval no se necesita); grep innerHTML= → 574; script sobre esc() → 30 definiciones, 10 sin comilla simple; grep integrity en app.html → 0.
- *Arreglo:* (1) Quitar 'unsafe-eval' (probar 1 semana con CSP_REPORT_ONLY=true). (2) connect-src a los hosts reales (finnhub ws, elevenlabs, self). (3) Un único esc() compartido. (4) Hash sha384 fijo en _VENDOR_MAP y verificarlo antes de servir. (5) A medio plazo, tras G5-06, nonces y quitar 'unsafe-inline'.
- *Verificación:* confirmed

**G5-10 · MEDIO · code · Fase 2 · esfuerzo S** — El agente de trading se apaga en silencio y pierde su configuración en cada despliegue  
- *En simple:* Si dejas el agente de trading encendido, cada actualización de la app lo apaga sin avisarte y olvida tus ajustes.
- *Hoy:* _AGENT (server.py:5195-5212: running, mode, universo, límites, daily_pnl_pct) vive solo en memoria; agent_start (5699) lo enciende y nada lo guarda ni lo restaura al arrancar (grep persistencia/restore → 0). Cada push a main reinicia el proceso (~2 min). Igual: sesiones MCP (mcp_server/api.py:64), progreso del comité (research/committee.py:911) y contadores de bloqueo del PIN (core/pin.py:65-67) se reinician.
- *Debe ser:* Dockerfile:18-21 fija 1 worker justamente por este estado; v2 §17.3 Postgres como única memoria duradera.
- *Evidencia:* grep -n '_AGENT\[.running.\] = True' server.py → solo 5699; no hay lectura de config del agente desde BD; módulo-nivel mutables fuera de tests: 56 (script grep).
- *Arreglo:* Guardar config + 'debería estar corriendo' del agente en Postgres (tabla de estado de usuario o broker_*); al arrancar, si estaba corriendo y es papel, reanudar; si es real, dejarlo detenido y crear una alerta 'detenido por actualización'. Persistir también el bloqueo del PIN.
- *Necesita de Fabrizio:* Decidir si el agente debe reanudarse solo tras una actualización (solo en papel) o quedar apagado con aviso.
- *Verificación:* confirmed

**G5-11 · MEDIO · code · Fase 1 · esfuerzo M** — Tres mecanismos de migración distintos y sin versión; ninguno de los 4 módulos de datos de la Fase 1 existe  
- *En simple:* La base de datos se actualiza con tres recetas distintas y la memoria de precios e historial que pide la arquitectura nueva todavía no empezó. Conviene ordenar primero cómo se agregan tablas.
- *Hoy:* ontology/db.py:128 _COLUMNAS_TARDIAS (5), brokerage/models.py:146 _LATE_COLUMNS (2) y mcp_server/models.py:101 LATE_COLUMNS (2), cada uno con su propio ALTER … IF NOT EXISTS; sin tabla de versión de esquema. CLAUDE.md dice 'Columnas nuevas van en ontology/db._COLUMNAS_TARDIAS', pero brokerage y mcp tienen las suyas. core/prices_store.py, core/daily_snapshots.py, core/instruments.py, core/context_engine.py: no existe…
- *Debe ser:* v2 §20.1 #1-#3 y #5: tablas eod_prices, entity_daily, positions_eod, instruments + motor de contexto.
- *Evidencia:* grep 'ALTER TABLE' → brokerage/models.py, mcp_server/auth.py, ontology/db.py (x2); ls core/prices_store.py core/daily_snapshots.py core/instruments.py core/context_engine.py → 'No such file' x4.
- *Arreglo:* Un solo módulo core/schema.py con tabla schema_version y pasos numerados idempotentes (incluye los 3 listados actuales); crear ahí las tablas de la Fase 1 antes de escribir los módulos.
- *Verificación:* confirmed

**G5-12 · MEDIO · code · Fase 2 · esfuerzo M** — Neo4j sigue cableado y la interfaz nunca lee el grafo de Postgres  
- *En simple:* La app guarda el mapa de empresas en varios lugares y lo que ves no sale de la base 'oficial'. Quitar la base extra (Neo4j) simplifica y ahorra.
- *Hoy:* v2 §18 retira Neo4j, pero server.py tiene 56 referencias y ~500 líneas en /api/grafo/* (3895-3990), engine/temporal-graph.js:1443 _seedBackend envía hechos a Neo4j, requirements/constraints lo instalan. Ninguna pantalla consume GET /api/ontology/graph?as_of= (solo aparece en un texto de tooltip, temporal-graph.js:1435; el comentario 1419-1424 dice que es 'verificación cruzada'): la UI dibuja el catálogo JS (25 archi…
- *Debe ser:* v2 §18: Postgres = verdad, snapshot generado, Neo4j retirado.
- *Evidencia:* grep -c neo4j server.py → 56; grep 'api/ontology/graph' engine/ app.html → solo khipu_lang.js:328 (/diff) y dos comentarios; du -cb nodes/*.js → 2.182.420 bytes.
- *Arreglo:* Retirar Neo4j (rutas, seed y dependencia) tras confirmar que nadie lo usa; luego que el cliente cargue nodos/vínculos desde /api/ontology/graph (o un snapshot generado desde Postgres) en vez de nodes/*.js.
- *Necesita de Fabrizio:* Confirmar que se puede apagar Neo4j Aura (y cancelar la cuenta si tiene costo).
- *Verificación:* adjusted — Direction confirmed, sizes off. The UI never fetches /api/ontology/graph; only /graph/diff is used (khipu_lang.js:328). engine/temporal-graph.js:1399/1455 still calls /api/grafo/estado and /seed. Neo4j stays in requirements.txt:24 and constraints.txt:28. Corrections: the Neo4j code is about 260 lin…

**M-code-01 · MEDIO · both · Fase 1 · esfuerzo S** — El tensor Ψ (X-Ray, capitalización en riesgo, sugerencias de vínculos) dice usar 'la misma semántica que propagate' pero usa otro conjunto de relaciones y da otros números  
- *En simple:* La ficha de una empresa dice que una caída de TSMC afecta a 246 empresas y la simulación dice 293. Son dos cálculos que deberían ser el mismo.
- *Hoy:* matrix/tensor.py:141 limita las relaciones a vocab.flow_relation_types() (7 tipos: supply, cloud, fab, license, deploy, owns, ppa). matrix/engine.propagate usa REL_TYPES (9 tipos, incluye partner 0.3 e invest 0.25). El comentario de tensor.py:16 y :162 dice 'misma semántica que engine.propagate'. Ψ tampoco aplica fragilidad.
- *Debe ser:* v2 §18/§20.1 #4: un solo kernel. Si se excluye partner/invest a propósito, hacerlo en propagate también, o documentarlo y probarlo.
- *Evidencia:* /tmp/audit_code/psi.py (columna Ψ[:,s] de matrix.tensor.Model(snapshot) vs matrix.engine.propagate sobre data/grafo_v0.json, sin contar el nodo del choque): TSMC Ψ 246 nodos vs propagate 293 (55 difieren más de 1 pt, máx 12,9); Nvidia 142 vs 205 (75, máx 18,0); ASML 49 vs 66 (37, máx 7,7).
- *Arreglo:* Decidir una sola regla de relaciones para la transmisión del daño (probablemente solo FLUJO, coherente con el NRS G4d). Aplicarla en _dependency_matrix para que propagate y Ψ la compartan. Añadir un test de paridad entre Ψ[:,s] y propagate([s]) para una muestra de nodos.
- *Necesita de Fabrizio:* Decidir si los socios (partner) y los inversionistas (invest) deben transmitir daño en una crisis o no.
- *Verificación:* hallado por el verificador

**M-code-02 · MEDIO · both · Fase 1 · esfuerzo M** — Hay al menos 5 variantes del cálculo de contagio con constantes distintas, no 2  
- *En simple:* La app calcula 'a quién le pega una crisis' de cinco maneras distintas según la pantalla. Una sola fórmula hace que todas las pantallas digan lo mismo.
- *Hoy:* (1) matrix/engine.propagate: suma por salto, 6 saltos, damping 0,6, umbral 1 %, tope de fragilidad 2,5, 9 tipos. (2) matrix/tensor Ψ: igual pero solo 7 tipos de flujo y sin fragilidad. (3) engine/statematrix.js simulate: máximo por proveedor, 8 iteraciones, 0,6, fragilidad sin tope (livesim.js:155, xray.js:538, cockpit.js:2533 y 4252, voice.js:1567). (4) app.html:8823: simulate(shocks, null, 4, 0.85), con 4 iteracio…
- *Debe ser:* v2 §18 '4 kernels → 1' y §20.1 #4.
- *Evidencia:* grep -n 'simulate(' engine/*.js app.html → 7 llamadas con 2 juegos de parámetros (8/0,6 y 4/0,85). sed -n 200,206p y 280-320p de core/scenario_engine.py. Las mediciones de M-code-01 y G5-03 cuantifican 3 de las variantes.
- *Arreglo:* Una función de transmisión en el servidor: _dependency_matrix + propagate con parámetros con nombre. Que scenario_engine use propagate (con dirección y signo) en vez de su BFS. Que el cliente solo anime los saltos que devuelve /api/matrix/impact, o una réplica de propagate con test de paridad. Borrar la llamada 4/0,85 de app.html:8823.
- *Verificación:* hallado por el verificador

**M-code-03 · MEDIO · code · Fase 1 · esfuerzo S** — /api/trade/close liquida posiciones completas por un camino directo sin controles de riesgo  
- *En simple:* El botón de 'cerrar posición' vende todo lo que tienes de una empresa sin pasar por la revisión de seguridad que sí tienen las demás órdenes.
- *Hoy:* server.py:2552-2598 (/api/trade/close) llama requests.delete(f'{ALPACA_BASE}/v2/positions/{path_sym}') (server.py:2580). Solo valida el símbolo, el PIN y el interruptor general (2574). Cerrar una posición completa es una orden de mercado que no pasa por brokerage.service ni por brokerage/risk, y G5-01 no lo menciona.
- *Debe ser:* CLAUDE.md 'DINERO — regla de oro': toda orden pasa por preview_order → confirm_order.
- *Evidencia:* grep -n 'requests\.' entre las líneas 2552 y 2598 de server.py → una sola llamada, requests.delete(.../v2/positions/...) en la línea 2580; no hay ninguna llamada a brokerage.service.
- *Arreglo:* Incluirlo en el mismo cambio de G5-01: cerrar posición = preview_order(HOUSE_ID, side=sell, qty=posición) + confirm_order, con el mismo registro de auditoría.
- *Verificación:* hallado por el verificador

**G5-04 · BAJO · code · Fase 1 · esfuerzo S** — Pesos por tipo de relación, piso de proveedor único y lista de relaciones de FLUJO copiados a mano en el cliente sin prueba que los compare  
- *En simple:* Hay números importantes escritos dos veces (en el servidor y en el navegador). Si alguien cambia uno y olvida el otro, la app calcula distinto en cada lado sin avisar.
- *Hoy:* REL_W en engine/statematrix.js:23 (copia de ontology/vocabulary.json relation_weights), SOLE_LINK_FLOOR en statematrix.js:30 (copia de matrix/engine.py), NRS_FLOW_TYPES en app.html:2780 (copia de vocabulary flow:true), MAX_ORDER_USD server.py:2214 vs HARD_MAX_ORDER_USD brokerage/risk.py:40. Hoy coinciden, pero ningún test los compara (grep 'REL_W' tests/*.py → 0; SOLE_LINK_FLOOR solo en un comentario de test_repair_…
- *Debe ser:* CLAUDE.md: 'Nunca re-escribir la fórmula en otro archivo'; 'cambiar los dos juntos' (SOLE_LINK_FLOOR) hoy depende de memoria humana.
- *Evidencia:* /tmp/audit_lens5/relw.py: vocab {'supply':1.0,'cloud':0.9,'fab':1.0,'license':0.5,'partner':0.3,'invest':0.25,'deploy':0.4,'owns':0.6,'ppa':0.7} vs statematrix REL_W → diff {} (iguales hoy); flow types iguales; SOLE 6.0 en ambos. Ningún test los fija.
- *Arreglo:* Exportar relation_weights, flow types y SOLE_LINK_FLOOR en data/grafo_v0.json (export_graph_v0.js) y leerlos en el cliente; mientras tanto, un test que parsea statematrix.js/app.html y compara con ontology.vocabulary y matrix.engine.
- *Verificación:* adjusted — Partly wrong. NRS_FLOW_TYPES IS pinned against vocabulary.json (tests/test_cleanup_server.py:42-43). The client's SOLE_LINK_FLOOR is pinned indirectly: tests/test_repair_graph.py:374-393 runs statematrix.js and asserts weights 1/6 and 2/6. It is never compared with matrix.engine.SOLE_LINK_FLOOR, so…

**G5-13 · BAJO · code · Fase 2 · esfuerzo M** — El mapa por defecto y otros módulos grandes no tienen pruebas de comportamiento  
- *En simple:* Partes que se usan todo el tiempo, como el mapa principal, no tienen pruebas automáticas; un error ahí solo se ve cuando alguien abre la app.
- *Hoy:* engine/universe2d.js (1.048 líneas, el renderizador del mapa por defecto) y engine/maptime.js (389): 0 menciones en tests; worldmonitor.js (1.326) y spacemonitor.js (1.324) solo aparecen en un test de colores (tests/test_cleanup_modules_theme_i18n.py:38); core/decide_api.py y core/country_geo.py: 0; research/contradictions.detect_for (usado por research/runner.py:26): 0 tests que lo llamen.
- *Debe ser:* v2 Fase 1: 'prueba que lo fija' por entregable; reporte de la bóveda: 23 módulos sin pruebas.
- *Evidencia:* grep -rl <módulo> tests/*.py → universe2d 0, maptime 0, decide_api 0, country_geo 0; grep detect_for|detect_semantic tests → 0.
- *Arreglo:* Arneses de node (como los de statematrix/khipu_chat) para universe2d (posiciones estables, filtro por fecha de maptime) y un test unitario de contradictions.detect_for.
- *Verificación:* adjusted — universe2d, maptime, decide_api and country_geo: 0 test mentions (confirmed). The contradictions claim is wrong. research.runner.execute_job calls detect_for for every claim (runner.py:601), and DB tests drive it end to end (tests/test_research.py:213-223, 344-354, 396-418 asserting ClaimRelation r…

**G5-14 · BAJO · code · Fase 1 · esfuerzo S** — 63 variables de entorno sin documentar (incluidas de seguridad y gasto) y un alias leído solo en algunos lugares  
- *En simple:* Hay ajustes que cambian la seguridad o cuánto puedes gastar en IA y no están anotados en ningún lado; si alguien los toca en Railway, nadie sabría qué hacen.
- *Hoy:* Según vault/01 Reporte del grafo.md, 63 variables se leen pero faltan en CLAUDE.md; verificadas: MCP_STATIC_TOKEN (da acceso MCP sin base, mcp_server/auth.py:368), CSP_ENABLED/CSP_REPORT_ONLY (pueden apagar la CSP, server.py:615-616), AI_DAILY_LIMIT_USD/AI_MONTHLY_LIMIT_USD (topes 10/150 USD, core/ai_usage.py:227-228), MATRIX_ENGINE (matrix/engine.py:75), REDIS_URL. Alias: ALPHA_VANTAGE_KEY se acepta en server.py:57…
- *Debe ser:* CLAUDE.md sección 'Variables de entorno' como lista completa; config centralizada en core/config.py.
- *Evidencia:* vault report: 'Variables leídas en el código que faltan en CLAUDE.md (63)'; grep confirma lectura de las 6 citadas y 0 menciones en CLAUDE.md; 143 lecturas os.getenv repartidas en 42 archivos.
- *Arreglo:* Documentar las 63 (agrupadas) y mover las de dinero/seguridad a core/config.py con un test que compare la lista con CLAUDE.md; research/context.py debe usar core.company_data.AV_KEY.
- *Verificación:* confirmed

**G5-15 · BAJO · code · Fase 2 · esfuerzo S** — Globales y rutas sin uso, alias de módulos ya borrados  
- *En simple:* Quedan piezas que ya nadie usa. No rompen nada, pero confunden al que lee el código.
- *Hoy:* Verificadas con 1 sola mención (la definición): window.APP_NAME, ASSISTANT_NAME, _initGeoGlobe (app.html:10380), togglePortfolio (5165), closeDiagnostics (5921), closeRegistro, _cvRows, _pfPendingAdd, _refreshLiveData, _layersApply, KhipuOSWin_memoLine; alias KhipuGeoGlobe/Planetarium (engine/globe.js:1013-1024) de módulos borrados. Rutas con 0 llamadas en código: /api/trade/diag, /api/tensor/status, /api/tensor/eva…
- *Debe ser:* Limpieza 'sin cosas sueltas' 2026-10-11.
- *Evidencia:* bucle grep -rnw por global → conteo 1 para las 11 citadas; grep de rutas → code_refs=0 para las 6 citadas (vault: 40 globales y 9 rutas sin uso).
- *Arreglo:* Borrar globales con 'se usa dentro: no' y los alias de globe.js; borrar o documentar como API de diagnóstico las 6 rutas; regenerar la bóveda.
- *Verificación:* confirmed

**G5-16 · BAJO · code · Fase 3 · esfuerzo S** — 37 archivos del front reimplementan su propio selector de idioma  
- *En simple:* Cada pantalla decide el idioma a su manera; a veces una queda en español y otra en inglés.
- *Hoy:* 19 copias de function L(es,en), 11 de isEn(), 9 de lang(), 3 de _lang() en engine/*.js; 55 lecturas directas de localStorage 'eco_lang' con defaults distintos (algunas comparan 'en', otras slice(0,2)).
- *Debe ser:* REGLA BILINGÜE de CLAUDE.md con un solo punto de verdad (window.LANG getter).
- *Evidencia:* grep -lE 'function (L|t|tr|_t|_L|lang|isEn|_en)\(' engine/*.js → 37 archivos; grep eco_lang getItem → 55.
- *Arreglo:* Exponer window.khL(es,en)/window.khIsEn() una vez (app.html primer bloque o toast.js) y reemplazar las copias al tocar cada archivo.
- *Verificación:* confirmed

**G5-17 · BAJO · code · Fase 2 · esfuerzo S** — Precio de Gemini con fecha de vencimiento escrita a mano: desde 2027 el gasto se registra a la mitad  
- *En simple:* A partir de enero de 2027 la app creería que gastas la mitad de lo que realmente gastas en Gemini y tus topes de gasto dejarían de proteger bien.
- *Hoy:* core/ai_usage.py:42 fija (0.75, 3.75) 'hasta el 31-dic-2026; desde el 1-ene-2027 sube a (1.5, 7.5) → actualizar aquí'; el código no mira la fecha y tests/test_ai_gemini_fast.py:99 fija 0.75. Los topes AI_DAILY_LIMIT_USD/MONTHLY se calculan con ese precio.
- *Debe ser:* Una sola tabla de precios (core/ai_usage.PRICES) correcta en el tiempo.
- *Evidencia:* grep '2026-12\|2027' core/ai_usage.py → línea 42 (comentario); ninguna rama por fecha.
- *Arreglo:* Precio con fecha de vigencia [(desde, in, out)] elegido por la fecha de la llamada; test con fecha simulada 2027-01-02.
- *Verificación:* adjusted — Real: core/ai_usage.py:42 is a comment and no code branches on the date. An existing env override (AI_PRICES_JSON, read by ai_usage) lets prices be fixed without code. That lowers urgency, but nothing reminds anyone to use it. Keep low.

**G5-18 · BAJO · code · Fase 1 · esfuerzo S** — El servidor arranca con la SECRET_KEY pública por defecto y /api/trade/status expone el modo de la cuenta sin PIN  
- *En simple:* Si en Railway faltara la clave secreta, alguien podría crearse acceso gratis a la API de pago. Conviene que la app se niegue en vez de solo avisar.
- *Hoy:* server.py:578 usa 'khipu-dev-secret-change-me' si falta SECRET_KEY y solo registra un error (606-609); las llaves /v1 se firman/validan con ella (server.py:4890, 4897) → con la clave por defecto cualquiera fabrica una llave de nivel enterprise. /api/trade/status (server.py:2398) no pide PIN y devuelve paper/live, pin_set y trading_enabled, contra la regla 'TODAS las rutas /api/trade/* exigen X-Trade-Pin'.
- *Debe ser:* CLAUDE.md namespaces (/v1 monetizada) y regla de PIN de trading.
- *Evidencia:* sed -n 578,610p server.py; script de decoradores: /api/trade/status ['@rate_limit'] sin _trade_auth (las otras 13 /api/trade/* lo tienen).
- *Arreglo:* En producción (RAILWAY_ENVIRONMENT presente) con SECRET_KEY por defecto: /v1/auth/key y la validación JWT responden 503; /api/trade/status devuelve solo ok/hint sin paper ni pin_set.
- *Necesita de Fabrizio:* Confirmar en Railway → Variables que SECRET_KEY existe y es un texto largo y aleatorio.
- *Verificación:* adjusted — The SECRET_KEY default is confirmed (server.py:578). /v1 JWTs are signed and validated with it (generate_khipu_key and validate_khipu_key around 4888-4897). The risk only applies if Railway lacks SECRET_KEY, and in that case a loud error is logged (600-607). /api/trade/status without PIN is a delib…

**G5-19 · BAJO · code · Fase 2 · esfuerzo S** — El servidor no entiende los alias de voz que sí entiende el navegador  
- *En simple:* Si dices 'en vidia' por voz, el navegador entiende Nvidia pero el cerebro del servidor no. Hay que darles a ambos la misma lista de apodos.
- *Hoy:* engine/resolve.js:60 VOICE_ALIAS ('en vidia','open ai','taiwan semi'…) no existe en core/entities.py; el chat central (server) recibe el texto hablado.
- *Debe ser:* CLAUDE.md: KhipuResolve y core/entities = el mismo resolvedor (legal_names vía snapshot).
- *Evidencia:* /tmp/audit_lens5/resolve_parity.js vs core.entities.resolve sobre 1.520 consultas (todas las etiquetas y tickers + 15 alias): 1.515 coinciden, 5 difieren: 'en vidia','envidia','taiwan semi','open ai' (navegador sí, servidor None) y 'samsung electronics co' (servidor sí, navegador None).
- *Arreglo:* Mover VOICE_ALIAS a nodes/legal_names.js (ya exportado al snapshot) para que ambos lo usen; test de paridad con esas 1.520 consultas.
- *Verificación:* adjusted — Confirmed with core.entities.resolve: 'en vidia', 'envidia', 'taiwan semi' and 'open ai' → None, while VOICE_ALIAS (engine/resolve.js:60) maps them. The proposed fix is risky as written. VOICE_ALIAS includes broad aliases meant for dictated names, such as 'video'→Nvidia, 'applied'→AMAT, 'lam', 'tel…

**G5-20 · BAJO · code · Fase 3 · esfuerzo S** — Dos pruebas de navegador tardan 30 s cada una con temporizadores reales  
- *En simple:* Un minuto de las pruebas se va en esperar que el recorrido de voz avance de verdad; se puede simular el reloj.
- *Hoy:* tests/test_voice_tour_drive.py::test_navegador_recorrido_entero_sin_que_el_agente_encadene[es|en] 30,4 s + 30,1 s; test_voice_tour_client 15,4 s; test_world_feeds::test_geopolitica_en_vivo_por_empresa_para_el_comite 13,0 s. Suite completa 304 s sin BD / 327 s con BD.
- *Debe ser:* Suite rápida para que la CI (G5-02) sea práctica.
- *Evidencia:* pytest tests/ --durations=30 → valores citados; con red bloqueada (plugin /tmp/audit_lens5/plug/nonet.py) 1643 passed y 0 intentos de red desde Python.
- *Arreglo:* Acelerar el reloj en los arneses de Playwright (page.clock.install / fastForward) en vez de esperar el ritmo real del recorrido.
- *Verificación:* confirmed

**M-code-04 · BAJO · code · Fase 1 · esfuerzo S** — La función compartida de órdenes del navegador vive dentro del módulo de voz  
- *En simple:* El código que hace las compras está guardado dentro del archivo de la voz; si la voz falla, comprar desde la pantalla principal también falla.
- *Hoy:* window._executeTradeOrder (confirmación → client_order_id → _tradeFetch → detección de duplicado → avisos de KhipuToast) está definida en engine/voice.js:2918. La bolsa del bróker de la Cabina depende de ella (cockpit.js:2930 muestra 'Trading no cargado' si falta; también cockpit.js:2945 y 3298). Si voice.js falla o se carga de forma perezosa, comprar desde la Cabina deja de funcionar.
- *Debe ser:* KHIPUS OS: una sola puerta por responsabilidad; dinero separado de la voz.
- *Evidencia:* grep -n '_executeTradeOrder' app.html engine/*.js → definida solo en engine/voice.js:2918; usada en cockpit.js:2930, 2945, 3298, voice.js:1928 y en el contrato de toast.js:644.
- *Arreglo:* Mover _executeTradeOrder a app.html, junto a _tradeOrderId y _tradeFetch (o a toast.js). Que el panel de app.html:11236 y crypto.js:627 la usen (eso cierra G5-08). Añadir un test de node.
- *Verificación:* hallado por el verificador

<details><summary>Lo que este lente midió y está BIEN (12)</summary>

- ✔ Suite de pruebas sin base: 1662 passed, 299 skipped, 0 failed en 304 s (1.961 recogidas; CLAUDE.md dice ~1.800)
- ✔ Suite de pruebas con Postgres de prueba: 1942 passed, 19 deselected, 0 failed en 327 s
- ✔ Pruebas que usan la red: 0 intentos de conexión/DNS no locales desde Python en 1.643 pruebas
- ✔ Pruebas que leen el reloj real: 17 archivos de test llaman datetime.now/date.today/time.time; 14 congelan o parchean el tiempo; hoy todas pasan
- ✔ ya arreglado Fórmula NRS única: 1 fórmula (app.html _nrsTerms = core/world.client_nrs) con test de paridad sobre todo el catálogo
- ✔ ya arreglado Motor disperso por defecto: MATRIX_ENGINE por defecto 'sparse' (matrix/engine.py:69-75); denso solo como respaldo
- ✔ Coordenadas país cliente vs servidor: 122/122 iguales, con test de paridad (tests/test_world.py)
- ✔ Bóveda Obsidian al día: 686 archivos, al día
- ✔ Llamadas a /api/trade/* sin _tradeFetch: 0 (solo app.html:1627 pone X-Trade-Pin, dentro de _tradeFetch)
- ✔ Llamadas a proveedores de IA fuera de core/: 0 (solo core/ai.py, core/ai_usage.py informe de costos, core/decide.py, core/voice_agent.py)
- ✔ Colisiones de clave de rate limit: 0 entre 156 manejadores con @rate_limit
- ✔ except amplios en caminos de dinero: brokerage/service.py 13 (3 con pass, todos en respaldos de precio/reloj); server.py 135 (20 con pass); ninguno oculta el resultado de una orden (timeout → 'unk…

</details>

