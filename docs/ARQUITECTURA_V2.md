# ARQUITECTURA v2 — Khipus como infraestructura de información y decisión

*Diseño del 2026-10-11. Responde al pedido de Fabrizio "diseña una arquitectura extremadamente avanzada… basada en
grafos, álgebra lineal, espacios vectoriales, tensores, embeddings, estructuras temporales y sistemas de inferencia".
Se apoya en cifras MEDIDAS sobre el código real (inventario del mismo día + limpieza "sin cosas sueltas", sw v254).
Las fórmulas usan notación LaTeX (`$…$`): GitHub y Obsidian las dibujan.*

---

## 0. Resumen para Fabrizio (en simple)

1. **Tu idea central es correcta y la mantengo**: el **grafo** guarda QUIÉN es quién y cómo se relaciona (la
   estructura del conocimiento); los **vectores** describen el ESTADO de cada cosa en un momento (sus números); los
   **tensores** son una herramienta de CÁLCULO que se arma un momento para una operación y se tira. Nada se guarda
   "como tensor".
2. **Lo más valioso no es matemática nueva, es tener UNA sola versión de cada cosa.** Hoy (medido) había 6 fórmulas
   de riesgo NRS, 4 motores de propagación que dan resultados distintos (un choque en TSMC alcanza 293, 246 o 217
   empresas según cuál uses), 4 copias del grafo y 4 armadores de contexto para la IA. La limpieza de hoy ya dejó
   UNA fórmula NRS, UN registro de agentes y el motor de matrices rápido; el resto está en la Fase 1.
3. **El mayor hueco no es técnico, es de DATOS**: Khipus no guarda la historia de precios, de posiciones ni de
   métricas. Sin historia no hay correlaciones, ni "¿cómo cambió mi exposición en 12 meses?", ni detección de
   anomalías, ni Monte Carlo serio. Guardar un precio de cierre diario de 568 acciones cuesta casi nada (≈100 MB en
   10 años) y destraba todo.
4. **Base de datos: se queda Postgres** (lo que ya pagas en Railway) + la extensión `pgvector` cuando haga falta.
   Nada de base de grafos aparte ni base vectorial aparte: con ~1.000 empresas y ~3.000 relaciones todo cabe en
   memoria y se recorre en microsegundos. **Neo4j sobra** (hoy solo recibe datos y nadie lo lee).
5. **Para la IA: menos tokens, mejor contexto.** El sistema elige del grafo solo lo relevante a la pregunta
   (fórmula $R(v\mid Q)$ de la sección 13), calcula los números ANTES (la IA nunca suma ni multiplica) y le pasa una
   tabla compacta con fuente y fecha. Meta: de ~10.000 tokens por pregunta a ~3.000, con mejores respuestas.
6. **Embeddings (vectores de texto): sí, pero solo para TEXTO** (noticias, conclusiones, descripciones), en la
   Fase 2. Redes neuronales de grafos (GNN, GAT, transformers de grafos): **no todavía** — con 937 empresas y pocos
   datos etiquetados aprenderían ruido. Lo que sí conviene (Fase 4) es AJUSTAR los ~10 números que hoy están
   puestos a mano en el motor de propagación usando eventos reales.
7. **Agentes**: de los 9 que propones, solo 4 necesitan IA para razonar (Investigación, Mercado, Macro y Reporte
   como narrador). Riesgo, Cartera, Cumplimiento y Datos deben ser **servicios deterministas** (reglas y fórmulas
   auditables) con la IA solo explicando. El de Trading nunca decide solo (regla de oro del dinero).
8. **Lo que critico de tu propuesta** (sección 19): guardar correlaciones como relaciones del grafo, hacer nodos de
   cada transacción u orden, el tensor de 5 dimensiones activo×sector×país×tiempo×métrica (es redundante: el
   sector y el país se deducen del activo), sumar embeddings de texto con variables financieras, y la fórmula
   $K:(D,G,X,T,Q)\to C$ (los tensores no son una entrada: se calculan desde el grafo y los datos).
9. **Fases**: 1) cimientos baratos (historia de precios, un solo motor de contexto, las 11 operaciones MCP que
   pediste) → 2) grafo temporal de verdad + embeddings de texto + modelo de factores → 3) tensores y escenarios con
   P&L → 4) ajustar el motor con datos reales → 5) sistema completo (cumplimiento, multiusuario, analítica pesada).
10. **Qué hacer ahora**: leer las secciones 0, 17, 19 y 20. Si estás de acuerdo con la Fase 1, se implementa en el orden
    de la sección 20.1 (cada paso con su prueba, como en la misión de reparación).

---

## 1. Punto de partida medido (no supuesto)

| Hecho | Valor medido (2026-10-11) | Consecuencia |
|---|---|---|
| Catálogo | 937 empresas, 2.510 vínculos (supply 1.001 · partner 756 · cloud 307 · invest 192 · fab 83 · license 63 · owns 51 · ppa 34 · deploy 19 · about 4) | El grafo es **pequeño**: $N\approx10^3$, $\lvert E\rvert\approx3\cdot10^3$ |
| Vínculos de FLUJO | 1.558 filas, 1.526 pares distintos, densidad 0,18 % | La matriz es **muy dispersa** |
| Base de producción | 1.294 objetos (≈216 que el repo no puede reconstruir) | Postgres es la fuente de verdad histórica |
| Fechas reales en vínculos | 85 de 2.595 (el resto: centinela 2000-01-01); 58 de esas 85 con relaciones en español fuera del vocabulario | El "grafo temporal" es casi atemporal: **faltan datos**, no código |
| Historia guardada | Precios, capitalización, fundamentales, NRS, posiciones: **ninguna** (solo en memoria; `PriceObserved` existe pero nada lo escribe) | No se puede responder nada "a lo largo del tiempo" salvo el grafo |
| Radio espectral del grafo | $\rho(T)=0{,}893$ (todas las relaciones estructurales), $0{,}750$ (solo flujo); amortiguación $\alpha=0{,}6$ | $\alpha\rho=0{,}536<1$ → la propagación converge |
| Motores de propagación | 4 (servidor, tensor Ψ, cliente statematrix, scenario_engine); choque en TSMC: 293 / 246 / 217 nodos | Respuestas distintas a la misma pregunta |
| Velocidad (tras la limpieza) | 937 choques: 47 s (denso, matriz rehecha por choque) → **0,3 s** (disperso, matriz una vez) | El cálculo NO es el cuello de botella |
| Tokens por acción | Chat ≈ 10k de entrada por pregunta (≈15,5k si va al modelo profundo); investigación STANDARD ≈ 14k por analista; comité ≈ 25-30k | Sin caché de prompt; el contexto crece en cada ronda |
| MCP | `get_supply_chain` de Nvidia a profundidad 2 = 102k caracteres (y la especificación MCP pide repetirlo como texto además de `structuredContent`) | Las IAs externas reciben demasiado: hay que achicar el resultado, no quitar la copia |
| Embeddings | Ninguno (lo "semántico" es léxico) | Hueco real para búsqueda de texto |
| Auto-conexión de empresas (tensor) | Hit@10 = 0,42 vs 0,23 de la línea base de popularidad | Lo estructural simple ya funciona |

**Lectura**: Khipus no necesita "más potencia" de cálculo; necesita (a) una sola representación del mundo,
(b) memoria temporal de los datos que ya consulta, y (c) un selector de contexto con criterio matemático.

---

## 2. Principio fundamental (formalización)

### 2.1 El mundo de Khipus como tres objetos de naturaleza distinta

Sea $\mathcal{L}$ el **registro de eventos** (inmutable, bitemporal). Todo lo demás es una función de $\mathcal{L}$:

$$
G_t=\Gamma(\mathcal{L},t),\qquad X_t=\Xi(\mathcal{L},t),\qquad \mathcal{T}_t=\Phi(G_t,X_t).
$$

- **Grafo** $G_t=(V_t,E_t,\phi,\psi)$: identidad y relación. $\phi:V\to\mathcal{T}_V$ tipa nodos,
  $\psi:E\to\mathcal{R}$ tipa aristas. Vive en el grafo **lo que tiene identidad propia y persiste**.
- **Vectores** $x_v(t)\in\mathbb{R}^{d_{\phi(v)}}$: el **estado medible** de una entidad en $t$. No tiene identidad
  propia: es una función $v\mapsto x_v(t)$.
- **Tensores** $\mathcal{T}\in\mathbb{R}^{d_1\times\cdots\times d_k}$: **objetos de cálculo**, derivados
  ($\mathcal{T}=\Phi(G,X)$), que existen mientras dura una operación o en una caché con versión. Nunca fuente de
  verdad.

### 2.2 Regla de decisión: ¿nodo, atributo, arista, vector o cálculo?

Para un dato $d$:

1. **Nodo** si y solo si tiene identidad estable (un id que no depende de otros datos), ciclo de vida propio
   (nace, cambia, muere) y participa en ≥ 2 tipos de relación o lo nombran agentes/usuarios. *Ejemplos: empresa,
   instrumento, país, sector, cartera, noticia, fuente, factor sistémico, agente.*
2. **Atributo / componente de vector** si es función de UNA entidad en el tiempo: $d=f(v,t)$. *Margen, precio,
   volatilidad, NRS.*
3. **Arista** si es función de un PAR ordenado (o de una tupla, que entonces se "reifica" como nodo) y además
   **se afirma** (tiene fuente y confianza propias, no se puede recalcular): $d=\theta_{uv}(t)$ afirmado.
   *Suministro, propiedad accionaria, licencia.*
4. **Cálculo (no se guarda)** si es reproducible desde lo guardado y
   $c_{\text{recalcular}}\cdot q < c_{\text{guardar}}+c_{\text{invalidar}}$, donde $q$ es la frecuencia de
   consulta. *Correlación, exposición de una cartera, impacto de un choque, similitud.*
5. **Registro de libro mayor (no nodo)** si es un hecho atómico de alta frecuencia sin valor de recorrido:
   *transacciones, órdenes, fills.* Van en tablas append-only, no en el grafo.

### 2.3 Las cuatro capas que NO deben confundirse

| Capa | Pregunta que responde | En Khipus |
|---|---|---|
| **Representación matemática** | ¿Qué objeto es? | $G$, $x_v(t)$, $A_r$, $\Sigma_t$, $\Psi$ |
| **Almacenamiento físico** | ¿Dónde vive, en qué formato? | Postgres (eventos, objetos, series), JSON del catálogo |
| **Índice de consulta** | ¿Cómo se encuentra rápido? | B-tree por id/fecha, GiST por intervalos, `pgvector` HNSW (Fase 2), lista de adyacencia en memoria |
| **Estructura de cálculo** | ¿En qué forma se opera? | CSR (`scipy.sparse`), arrays numpy, tensores transitorios |

Ejemplo: la relación "TSMC fabrica para Nvidia" es *matemáticamente* $A_{\text{fab}}[i,j]=w$, *se almacena* como un
evento `LinkCreated` + una fila en `links`, *se indexa* por `(source_id, target_id)`, y *se computa* como una entrada
de una matriz CSR que vive 300 ms.

---

## 3. El grafo heterogéneo y temporal

### 3.1 Definición

$$
G=(V,E,\phi,\psi),\quad e=(u,r,v,\theta,[t^{v}_{0},t^{v}_{1}),t^{k},s,c)
$$

Respecto a tu propuesta $e=(u,r,v,\theta,t)$ hacen falta **tres agregados** (y no son detalles):

- **Dos tiempos, no uno** (modelo bitemporal): $[t^{v}_{0},t^{v}_{1})$ = cuándo fue VERDAD en el mundo;
  $t^{k}$ = cuándo LO SUPIMOS (se registró). Sin $t^{k}$ no se puede auditar "¿qué creía el sistema el 3 de marzo
  cuando recomendó X?" — requisito de trazabilidad para decisiones de inversión.
- **Fuente** $s$ (un nodo `Source`, ya existe).
- **Confianza** $c\in[0,1]$: probabilidad de que la arista exista. Ya existe (`conf`, `verified`).

### 3.2 Esquema (meta-grafo)

Los tipos válidos forman un meta-grafo $S=(\mathcal{T}_V,\mathcal{R})$ con firmas $r:\tau_u\to\tau_v$. Ejemplo de
firmas (✔ = ya existe, ◐ = parcial, ✚ = a crear):

| Tipo de nodo | Estado | Nota de diseño |
|---|---|---|
| Empresa (`Company`) | ✔ 937 | Hoy además hace de "acción" (campo `mkt`) — ver Instrumento |
| **Instrumento** | ✚ | UN solo tipo con subtipo `equity / adr / bond / etf / crypto / fx / option`. Reemplaza a "activo", "acción", "bono", "ETF", "criptomoneda" como tipos separados (ver crítica 19.2) |
| Bolsa / mercado | ✚ | `listed_on` (TSMC: 2330.TW y TSM ADR) |
| Moneda | ✚ | `denominated_in`; FX como serie |
| Sector | ◐ atributo (13 + 108 categorías) | Pasar a nodo con arista ponderada `in_sector` (participación de ingresos) |
| País | ◐ 6 objetos + texto libre (136 grafías) | Nodo + arista `located_in` / `operates_in` (con peso) |
| Inversor / fondo | ◐ como `Company` con categoría | Tipo propio `Investor` (gestoras, soberanos, pensiones) |
| Usuario | ✗ (`owner_hash`) | Identidad de acceso, NO nodo económico; se enlaza a sus Carteras |
| Cuenta de bróker | ◐ tabla `broker_clients` | Queda relacional; nodo solo como ancla `Account` |
| Cartera | ◐ JSON | Nodo `Portfolio`; la composición es una SERIE (no aristas) |
| Posición, orden, transacción | ◐ tablas / JSON | **Libro mayor, no nodos** (sección 3.4) |
| Noticia (`NewsItem`) | ✔ parcial | `reports_on` con relevancia |
| Evento del mundo | ◐ hechos temporales + memoria | Nodo `WorldEvent` (conflicto, sanción, desastre) con `affects` |
| Indicador macro | ✗ | Nodo `MacroSeries` (metadatos) + tabla de serie |
| Factor / riesgo sistémico | ✔ 69 `Factor` | Hiperarista reificada (miembros con coeficiente) |
| Estrategia / tesis | ◐ `Thesis`, memos | Nodo; enlaza conclusiones |
| Modelo | ✗ (texto) | Nodo `Model` (nombre, versión, precio) → `produced_by` |
| Agente | ◐ `agent_runs` | Nodo `Agent` (los puestos del registro único) |
| Fuente (`Source`) | ✔ | Con `trust` 0-3 |

### 3.3 Tipos de arista: dirigidas, ponderadas, probabilísticas, temporales

| Relación | Dirigida | Peso $w$ (significado) | Probabilística | Temporal | ¿Se guarda? |
|---|---|---|---|---|---|
| `supply`, `fab`, `cloud`, `license`, `ppa`, `deploy` | sí (proveedor → cliente) | criticidad $\in[0,1]$ tras normalizar; hoy 0,25-6 mezclado | sí ($c$) | sí (contrato) | **sí** (afirmada) |
| `owns` | sí (dueño → filial) | fracción de propiedad $\in[0,1]$ | casi determinista (filings) | sí | sí |
| `invest` | sí | participación o monto | sí | sí | sí |
| `partner` | **no** (simétrica) | baja | sí | sí | sí |
| `in_sector`, `located_in`, `operates_in` | sí | participación $\in[0,1]$, $\sum=1$ | no | lenta | sí |
| `issued_by`, `listed_on`, `denominated_in` | sí | — | no | sí | sí |
| `affects` (Factor → entidad) | sí | coeficiente | no | sí | sí |
| `reports_on` (Noticia → entidad) | sí | relevancia | sí | instante | sí |
| `evidenced_by`, `produced_by` | sí | — | no | instante | sí |
| `competes_with` | no | similitud | sí | lenta | **derivada** (de sectores y clientes comunes) |
| `correlated_with` | no | $\rho_{ij}$ | — | ventana | **NUNCA guardada** (sección 4) |
| `holds` (Cartera → Instrumento) | sí | cantidad | no | continua | **serie**, no arista |

**Unificación de escalas (hallazgo medido)**: 400 vínculos (16 %) usan escala 0-1 junto a 2.110 en escala 1-6. Con
el piso `SOLE_LINK_FLOOR=6`, un proveedor único de nube con $w=0{,}9$ transmite
$0{,}9\cdot0{,}9/6\approx13{,}5\,\%$ cuando con $w=6$ transmitiría ≈90 %. Hay que llevar todo a una escala única
$w\in[0,1]$ = "fracción del insumo del cliente que depende de este proveedor" (Fase 1, migración por eventos con
revisión de Fabrizio).

**Aristas probabilísticas**: la existencia de $e$ es Bernoulli($c_e$). Para operadores **lineales**
$\mathbb{E}[f(A)]=f(\mathbb{E}[A])=f(C\odot W)$ — por eso multiplicar peso × confianza (lo que ya se hace) es
correcto *solo* en el régimen lineal. El kernel real tiene $\min(1,\cdot)$ y umbral (no lineal): para escenarios de
decisión se debe muestrear la existencia de aristas (Monte Carlo sobre $c_e$; extensión de `propagate_bands`).

### 3.4 Lo que NO es nodo: el libro mayor

Transacciones, órdenes y posiciones son hechos de alta frecuencia sin valor de recorrido de grafo: una cartera con
200 operaciones/año en 10 años serían 2.000 nodos que solo se consultan agregados. Se modelan como **tablas
append-only** y las posiciones como **función** del libro:

$$
q_{p,i}(t)=\sum_{\tau\in\text{fills}(p,i),\ t_\tau\le t}\Delta q_\tau,\qquad
w_{p,i}(t)=\frac{q_{p,i}(t)\,P_i(t)\,\text{FX}_i(t)}{\sum_j q_{p,j}(t)\,P_j(t)\,\text{FX}_j(t)}.
$$

El grafo solo guarda el ancla `Portfolio` y su dueño.

---

## 4. Valores de las relaciones: $u\xrightarrow{\theta(t)}v$

Forma general: $e_{ij}(t)=f\big(x_i(t),x_j(t),z_{ij}(t)\big)$, con $z_{ij}(t)$ = la parte del par que **no** se
deduce de los nodos. Tres clases, con política distinta:

| Clase | Definición | Ejemplo | Política |
|---|---|---|---|
| **Afirmada** | $f$ depende esencialmente de $z_{ij}$ (no reproducible) | propiedad 15 %, contrato de suministro, licencia | **Se guarda** como evento con fuente, confianza y validez |
| **Derivada** | $f$ depende solo de $x_i,x_j$ (y de parámetros de ventana) | correlación, beta, similitud, competencia | **Se calcula** bajo demanda; caché con clave (ventana, estimador, `as_of`) |
| **Modelada** | $f$ es la predicción de un modelo | sugerencia de vínculo, probabilidad de disrupción | Se guarda **solo como propuesta** con versión de modelo (como hoy `IncorporarEmpresa` con confianza 0) |

**Por qué la correlación NO es una arista** (crítica a tu ejemplo $Asset_i\xrightarrow{0{,}73}Asset_j$):

1. No es propiedad del par sino del par **y** de una ventana $W$ y un estimador: $\hat\rho_{ij}(t;W,\text{método})$.
2. Es densa: 568 tickers → $\binom{568}{2}=161.028$ pares *por ventana y por día*.
3. Es ruidosa: el error estándar aproximado de $\hat\rho$ es $(1-\rho^2)/\sqrt{T}$; con $T=252$ días y $\rho=0{,}73$
   da $\approx0{,}029$ — dos "aristas" de 0,73 y 0,70 son estadísticamente iguales.
4. Se comprime muchísimo con un modelo de factores (sección 9): $\Sigma=BFB^\top+D$ guarda $nk+k^2+n$ números en
   vez de $n^2$ (con $n=568,\ k=10$: ≈6.400 vs 322.624, **50× menos**) y de ahí sale cualquier $\rho_{ij}$ en $O(k)$.

**Regla de costo para guardar un θ derivado**: guardar si
$q\cdot c_f > s\cdot|E_\theta| + u\cdot c_{\text{inv}}$ ($q$ consultas/día, $c_f$ costo de calcular, $s$ costo de
almacenamiento, $u$ actualizaciones/día). Para correlaciones de cartera ($c_f\approx$ ms) nunca conviene; para
$\Psi$ (choques de todos contra todos, 0,3 s) conviene en caché por época del grafo — que es lo que ya se hace.

---

## 5. Vectores: espacios separados, combinados con criterio

### 5.1 Familias de vectores (una por significado, nunca mezcladas sin transformación)

| Vector | Dimensiones (propuesta) | Fuente | Estado hoy |
|---|---|---|---|
| $x^{\text{fin}}_i(t)\in\mathbb{R}^{\sim14}$ | log capitalización, crecimiento de ingresos, margen operativo, margen FCF, deuda neta/EBITDA, P/E, beta 1a, vol 60d, momentum 1/3/6/12m, ADV (liquidez) | precios EOD + estados | ◐ se calcula al vuelo, no se guarda |
| $x^{\text{struct}}_i\in\mathbb{R}^{\sim8}$ | grado de flujo in/out, HHI de proveedores, exposición aguas arriba (max fila de Ψ), capitalización aguas abajo en riesgo, PageRank, intermediación, contribución a $\rho$ | grafo | ✔ casi todo en `matrix/tensor.py` ($X\in\mathbb{R}^{N\times6}$) |
| $x^{\text{risk}}_i\in\mathbb{R}^{5+K+\lvert C\rvert }$ | términos del NRS (5), cargas factoriales $\beta_i\in\mathbb{R}^K$, participación por país (simplex disperso) | fórmula única + modelo de factores | ◐ NRS sí; factores no |
| $x^{\text{exp}}_p$ (cartera) | exposición sectorial $S^\top w_p$, por país $C^\top w_p$, factorial $B^\top w_p$, por país de PROVEEDORES $(\Psi^\top\!\odot\ldots)$, por moneda | **lineal en $w_p$** | ✗ — se CALCULA, nunca se guarda |
| $x^{\text{sem}}_i\in\mathbb{R}^{384..1024}$ | embedding de TEXTO (descripción, noticias, conclusiones) | modelo de texto | ✗ (Fase 2) |
| $x^{\text{temp}}_i(t)$ | NO un embedding: estadísticas de la serie (tendencia, régimen de volatilidad, días desde el último evento) | series | ✗ |
| Vector de "estado" del cliente (`statematrix`: salud, riesgo, momentum, valor, crecimiento) | 5 | coeficientes puestos a mano | ✔ pero **sin estimar** — reemplazar por cantidades medidas de arriba |

### 5.2 ¿Cómo se combinan? (la fórmula $x_i=\sum_k W_kx^k_i$ y sus límites)

1. **Identidad clave**: $\sum_k W_kx^k_i=[W_1\,\cdots\,W_K]\,[x^1_i;\ldots;x^K_i]$. La suma lineal ponderada es
   **un caso particular** de "concatenar y aplicar una capa lineal", con la restricción de que la salida tenga una
   sola dimensión $d$. Si $d<\sum_k d_k$ se **pierde información** (proyección). Sin datos para *aprender* los $W_k$,
   cualquier elección a mano es arbitraria.
2. **Problema de escalas**: un embedding de texto normalizado tiene $\lVert x^{\text{sem}}\rVert=1$ repartido en 768
   dimensiones (≈0,036 por componente); un z-score financiero tiene componentes de orden 1. Sumados, el texto
   desaparece; concatenados sin cuidado, el texto domina la distancia por número de dimensiones.
3. **Recomendación para Khipus: fusión TARDÍA en el puntaje, no en el vector.** Para similitud:
   $$s(i,j)=\sum_k\alpha_k\,s_k(i,j),\qquad s_k=\cos\!\big(\tilde x^k_i,\tilde x^k_j\big),\quad \tilde x^k=\text{estandarizado por bloque}$$
   con $\alpha$ visible y explicable ("se parecen 60 % por su cadena, 30 % por sus números, 10 % por cómo se
   describen"). `matrix/tensor.peers` ya hace exactamente esto ($0{,}6\cos(\text{perfil})+0{,}25e^{-\lVert\Delta x\rVert/2}+0{,}15[\text{misma categoría}]$).
4. **Cuándo concatenar**: como entrada de un modelo supervisado (Fase 4), con estandarización por bloque y escala
   $1/\sqrt{d_k}$ para que cada bloque pese lo mismo en la distancia euclídea.
5. **Cuándo atención / compuertas**: cuando el bloque relevante depende de la pregunta:
   $\alpha_k=\text{softmax}(q^\top u_k)$ — "competidores" → semántico + estructural; "gemelos de riesgo" → financiero. En Khipus la pregunta ya se
   clasifica (Jev / intención), así que basta una tabla $\alpha(\text{intención})$; aprenderla requiere
   retroalimentación (Fase 4).
6. **Producto tensorial** $x^{\text{sem}}\otimes x^{\text{fin}}$: $768\times14=10.752$ dimensiones para modelar
   interacciones bilineales. **No vale la pena**: sin miles de ejemplos etiquetados es sobreajuste seguro.

---

## 6. Tensores: cuáles sirven de verdad

### 6.1 Inventario de tensores útiles

| Tensor | Forma | Qué es | Densidad | Política |
|---|---|---|---|---|
| $\mathcal{A}$ | $R\times N\times N$ | adyacencia multi-relacional | 1.526 nnz / $9\cdot937^2$ (0,02 %) | ✔ CSR por relación, derivado del grafo |
| $\mathcal{X}$ | $T\times N\times d$ | panel de características (tiempo × empresa × rasgo) | denso | Fase 3; se arma desde las series |
| $\mathcal{E}$ | $P\times n\times K$ | exposición cartera × activo × factor | **rango 1 por factor** | NUNCA se guarda: $\mathcal{E}_{p,i,k}=W_{p,i}B_{i,k}$ |
| $\mathcal{S}$ | $S\times N\times H$ | escenario × nodo × salto/horizonte | disperso | Fase 3: biblioteca de escenarios con versión |
| $\mathcal{P}$ | $M\times H\times n$ | trayectorias Monte Carlo | denso, transitorio | en memoria (10.000×20×30 = 48 MB) |
| $\mathcal{A}(t)$ | $T\times R\times N\times N$ | grafo dinámico | — | **nunca denso** (3,5 GB POR relación para 500 días); se reconstruye desde eventos |

### 6.2 Crítica a $T_{\text{asset},\text{sector},\text{country},\text{time},\text{metric}}$

El sector y el país son **funciones** del activo: existen matrices indicadoras $S\in\{0,1\}^{n\times s}$ y
$C\in\{0,1\}^{n\times c}$ con una sola fila activa (o pesos que suman 1). El tensor de 5 modos tiene entonces
$\text{nnz}=n\cdot T\cdot M$ de $n\cdot s\cdot c\cdot T\cdot M$ celdas: con $s=13,\ c=136$ es **1.768 veces más
grande de lo necesario y 99,94 % vacío**. Todo lo que ofrece se obtiene del tensor de 3 modos
$\mathcal{X}\in\mathbb{R}^{n\times T\times M}$ por **contracción** con la indicadora:

$$
\mathcal{X}^{\text{sector}}=\mathcal{X}\times_1 S^\top\in\mathbb{R}^{s\times T\times M}
\qquad(\text{"agrupar por sector" = producto modo-1}).
$$

Lo mismo con $T_{\text{investor},\text{asset},\text{time},\text{riskfactor}}$: es
$W_{\text{inv},\text{asset},t}\cdot B_{\text{asset},\text{factor},t}$; se guardan $W$ (posiciones) y $B$ (cargas) y
la exposición es la contracción sobre el activo:
$\mathcal{E}_{\text{inv},t,k}=\sum_i W_{\text{inv},i,t}B_{i,k,t}$.

**Regla**: un modo que es función de otro modo no es un modo; es una matriz de agregación.

### 6.3 Descomposiciones: para qué sirve cada una en Khipus

| Técnica | Forma | Uso posible en Khipus | Costo | Veredicto |
|---|---|---|---|---|
| **Bajo rango matricial** (PCA/SVD) sobre retornos $R\in\mathbb{R}^{T\times n}$ | $R\approx U_k\Sigma_kV_k^\top$ | modelo de factores estadístico, covarianza estable, "absorption ratio" | $O(Tnk)$ con SVD aleatorizada: ms | **Fase 2 — es lo que más vale** |
| **CP** (PARAFAC) | $\mathcal{X}\approx\sum_r a_r\circ b_r\circ c_r$ | patrones conjuntos tiempo × empresa × rasgo ("en 2022 las empresas de memoria cambiaron margen y momentum juntas") | ALS $O(\text{nnz}\cdot R)$ por iteración; $\mathcal{X}$ de 500×600×14 = 4,2M celdas: segundos | Fase 3, exploratorio |
| **Tucker** | $\mathcal{X}\approx\mathcal{G}\times_1A\times_2B\times_3C$ | compresión del panel con rangos distintos por modo; regímenes | HOSVD $O(\sum_m I_m\prod I)$ | Fase 3, solo si CP no alcanza |
| **Tensor-train** | cadena de núcleos 3-modo | tensores de orden ≥ 5 (escenario × horizonte × nodo × factor × severidad) | lineal en el orden | **No**: ningún tensor útil de Khipus tiene orden ≥ 5 tras quitar modos redundantes |
| **RESCAL / DistMult / ComplEx** sobre $\mathcal{A}$ | $A_r\approx ER_rE^\top$ | predicción de vínculos (= embeddings de grafo de conocimiento) | $O(\text{nnz}\cdot d^2)$ | Fase 4, **solo** si supera a `suggest_links` (Hit@10 0,42) en ≥ 10 puntos |
| **Factor de covarianza** $\Sigma=BFB^\top+D$ | bajo rango + diagonal | VaR de cartera, optimización, correlaciones | inversión por Woodbury $O(nk^2)$ | **Fase 2** |

**Aceleración**: $\Psi$ (choques de todos contra todos) tiene 0,48 % de no-ceros → mantenerlo **disperso** es
mejor que aproximarlo por bajo rango (un $\Psi$ de rango $k$ denso tendría $2Nk$ números y perdería la estructura
local exacta que justifica cada número ante el usuario).

---

## 7. Grafo ↔ Matriz ↔ Tensor

1. **Grafo → matriz**: $A_{ij}=w_{ij}$. $(A^k)_{ij}$ suma los caminos de largo $k$.
2. **Propagación de choques como serie de Neumann**: con la matriz de transmisión normalizada
   $T=\sum_r\alpha_rA_rD_r^{-1}$ ($D_r=\text{diag}(\max(\mathbf{1}^\top A_r,6))$), la versión lineal del kernel es
   $$x=\sum_{k\ge1}\big(\alpha T^\top\big)^kx_0=(I-\alpha T^\top)^{-1}x_0-x_0,$$
   convergente porque $\alpha\rho(T)=0{,}6\cdot0{,}893=0{,}536<1$. El kernel real corta en 6 saltos: la masa
   lineal omitida es $(0{,}536)^7\approx1{,}3\,\%$ → **`max_hops=6` está justificado**; 8 saltos (cliente) no aporta.
3. **Matriz → tensor multi-relacional**: $T=\mathcal{A}'\times_1\alpha$ (contracción del modo de relación con el
   vector de criticidad $\alpha\in\mathbb{R}^R$, donde $\mathcal{A}'$ ya normalizó cada relación). Es decir: **el
   motor actual YA es álgebra tensorial**, solo que bien implementada como suma de matrices dispersas.
4. **Grafo dinámico**: $A^{(t)}$ = rebanada del tensor $\mathcal{A}(t)$; se materializa desde el registro de eventos
   para el $t$ pedido (hoy: `_links_active_at`, ≈0,1 s con 4.108 eventos; lineal en el tamaño del registro →
   Fase 2: puntos de control cada $m$ eventos para costo $O(m)$).
5. **$T_{ijtk}$ (relación × tiempo × métrica)**: solo para métricas DERIVADAS, p. ej. correlación rodante
   $\mathcal{C}\in\mathbb{R}^{T\times n\times n}$: 252 ventanas × 568² × 8 B ≈ 650 MB. **No se guarda**; se guardan los
   parámetros del modelo de factores por día ($nk+k^2+n\approx6{,}3$ mil números) y se reconstruye cualquier
   rebanada en $O(n^2k)$ o un par en $O(k)$.

**¿Es sólida la separación "grafo = capa semántica, tensor = capa cuantitativa asociada"?** Sí, con tres
condiciones que la hacen correcta y no solo bonita:

- **Funcionalidad**: el tensor es una función pura del grafo y de las series: $\mathcal{T}=\Phi(G_t,X_t;\pi)$ con
  parámetros $\pi$ explícitos. Una sola función constructora (hoy `build_matrices_from_triples`).
- **Versionado**: toda caché lleva la clave $(\text{época del grafo},\ \text{as\_of},\ \pi)$; al cambiar el grafo se
  invalida sola (ya existe la "época" = máximo `recorded_at` estructural).
- **Un solo kernel**: los 4 motores de propagación medidos dan 293/246/217 nodos para el mismo choque. La
  separación capa semántica/capa cuantitativa NO sirve si hay cuatro capas cuantitativas.

---

## 8. Grafo temporal: preservar la evolución sin sobrescribir

### 8.1 Modelo

Un **hecho** $f=(\text{sujeto},\text{predicado},\text{objeto},\theta,[t^{v}_{0},t^{v}_{1}),t^{k},s,c)$. El registro
$\mathcal{L}$ es append-only (ya lo es por convención en `events`; la Fase 2 lo blinda con un disparador como
`broker_audit`). El grafo en un instante de validez $t$ visto con el conocimiento disponible en $\kappa$:

$$
G(t,\kappa)=\Big\{f\in\mathcal{L}:\ t^{v}_{0}(f)\le t<t^{v}_{1}(f),\ \ t^{k}(f)\le\kappa,\ \ \nexists\,g\in\mathcal{L}:\ g\ \text{retracta}\ f,\ t^{k}(g)\le\kappa\Big\}.
$$

- $G(t,\text{hoy})$ = "¿cómo era el mundo en $t$ según lo que sabemos HOY?" — **existe** (`as_of_graph`).
- $G(t,t)$ = "¿qué creíamos en $t$?" — **falta** (no hay consulta por $t^{k}$). Es la base de la auditoría de
  decisiones: el comité recomendó X el día $t$ con $G(t,t)$, no con $G(t,\text{hoy})$.
- Propiedades de nodos en el tiempo: los `ObjectUpdated` se guardan pero no se reproducen → la severidad de un
  factor "en 2022" sale con el valor de hoy. **Falta** el replay de propiedades (o tabla `object_versions`).

### 8.2 Las tres preguntas que pediste, formalizadas

**P1. "¿Cómo cambió la exposición de este inversor al sector tecnológico en los últimos 12 meses?"**

$$
E_{\text{tech}}(t)=\sum_i w_{p,i}(t)\,s_{i,\text{tech}}(t),\qquad t\in\{t_0,\ldots,t_0+252\}
$$

con $w_{p,i}(t)$ del libro mayor (sección 3.4) y $s_{i,\text{tech}}(t)$ de la arista `in_sector` vigente en $t$.
Costo: $O(252\cdot n_p)$ — trivial. **Falta el dato**: hoy las posiciones no tienen historia (último valor en
`user_state`). Requisito Fase 1: foto diaria de posiciones.

**P2. "¿Qué relaciones existían en marzo pero desaparecieron en septiembre?"**

$$
\Delta^-=E(t_{\text{mar}})\setminus E(t_{\text{sep}}),\qquad \Delta^+=E(t_{\text{sep}})\setminus E(t_{\text{mar}}),\qquad
\Delta^\theta=\{e\in E(t_{\text{mar}})\cap E(t_{\text{sep}}):\ |\theta_e(t_{\text{sep}})-\theta_e(t_{\text{mar}})|>\epsilon\}.
$$

**Existe** `diff_graph` para $\Delta^\pm$; falta $\Delta^\theta$ (cambios de peso son invisibles hoy). Y el valor
real depende de tener fechas: hoy 85 de 2.595 vínculos tienen fecha real → **la tarea prioritaria es fechar los
~200 vínculos más pesados**, no más infraestructura.

**P3. "¿Qué activos empezaron a moverse conjuntamente antes de una caída?"**

Con retornos diarios $r_t\in\mathbb{R}^n$ y ventana $W$:
1. Matriz de correlación rodante $\hat C(t)$ (o su versión factorial).
2. **Absorption ratio** (Kritzman et al., 2011): $AR(t)=\sum_{k\le K}\lambda_k(t)/\sum_k\lambda_k(t)$ — sube cuando
   el mercado se mueve "en bloque", y históricamente antecede a caídas.
3. Pares que se acoplaron: $\{(i,j):\ \hat\rho_{ij}(t)-\hat\rho_{ij}(t-h)>z_{0.99}\cdot\text{SE}\}$, con
   $\text{SE}\approx\sqrt{2}(1-\rho^2)/\sqrt{W}$.
4. Restringido al grafo: ¿el acople ocurre entre vecinos de cadena ($\Psi_{ij}>0$)? Eso distingue "contagio por
   la cadena" de "pánico general" — **una señal que solo Khipus puede dar** porque solo Khipus tiene el grafo.

Costo por día: $O(nkW)$ con SVD aleatorizada ($n=568,\ k=10,\ W=60$): < 50 ms. **Falta el dato**: historia de
precios (Fase 1).

### 8.3 Grafos temporales y grafos de eventos: qué estructura usar

| Estructura | Idea | Para Khipus |
|---|---|---|
| Secuencia de instantáneas $\{G_{t_1},\ldots\}$ | una foto por fecha | Solo como **puntos de control** (cada $m$ eventos) para acelerar `as_of` |
| Grafo con intervalos (TVG) | aristas con $[t_0,t_1)$ | ✔ es lo que hay (`links.valid_from/valid_to`) |
| Grafo de eventos (event graph) | los eventos son nodos, enlazados por causalidad/tiempo | ✔ parcial: `WorldEvent`/`NewsItem` → `affects`/`reports_on`. Útil para "¿qué evento explica este movimiento?" |
| Redes temporales continuas (TGN, etc.) | embeddings que evolucionan con cada evento | **No** (Fase 4 como mucho): requiere millones de eventos |

---

## 9. Capa financiera: matemática, representación y dónde vive

### 9.1 Datos base (lo único que se guarda)

Precios de cierre ajustados $P\in\mathbb{R}^{T\times n}$ (+ máximo, mínimo, volumen), FX, tasa libre de riesgo,
posiciones (libro mayor). **Todo lo demás se calcula.** Retornos: $r_{t,i}=\ln(P_{t,i}/P_{t-1,i})$ (log para sumar en
el tiempo) o simples (para agregar entre activos: $r_{p,t}=w^\top r_t$ solo vale con retornos simples). Moneda:
$r^{\text{USD}}_{t,i}=r^{\text{local}}_{t,i}+r^{\text{FX}}_{t,i}$ (hoy se aplica el FX de HOY a toda la historia: error
para el inversor en dólares).

### 9.2 Las magnitudes

| Magnitud | Fórmula | Forma | Estado hoy |
|---|---|---|---|
| Volatilidad | muestral $\hat\sigma$; **EWMA** $\sigma^2_t=\lambda\sigma^2_{t-1}+(1-\lambda)r^2_{t-1}$, $\lambda=0{,}94$ | vector $\mathbb{R}^n$ | muestral ✔; EWMA ✗ |
| Covarianza | $S=\frac1{T-1}\tilde R^\top\tilde R$; **Ledoit-Wolf** $\hat\Sigma=\delta F+(1-\delta)S$; **factorial** $\Sigma=BFB^\top+D$ | $\mathbb{R}^{n\times n}$ (o $nk$) | muestral por cartera ✔ |
| Correlación | $C=D^{-1/2}\Sigma D^{-1/2}$ | $\mathbb{R}^{n\times n}$ | por cartera ✔ |
| Beta | $\beta_i=\text{Cov}(r_i,r_m)/\text{Var}(r_m)$; multifactor $r=\alpha+Bf+\varepsilon$ | $\mathbb{R}^n$ / $\mathbb{R}^{n\times k}$ | vs SPY ✔; multifactor ✗ |
| Exposición | $e=B^\top w$ (factores), $S^\top w$ (sector), $C^\top w$ (país), **$\Psi^\top$-ponderada** (cadena) | $\mathbb{R}^k$ | sector/país en asesor ✔; factor ✗; cadena ◐ |
| Drawdown | $DD_t=P_t/\max_{s\le t}P_s-1$ | serie | ✔ (bug de ventana corregido hoy) |
| VaR / CVaR | $\text{VaR}_\alpha=-q_\alpha(r_p)$; $\text{CVaR}_\alpha=-\mathbb{E}[r_p\mid r_p\le-\text{VaR}_\alpha]$; Cornish-Fisher para colas | escalares | VaR hist/param ✔, CVaR solo 1 día |
| Factores | estadísticos (PCA de $R$), fundamentales (sector, país, tamaño, valor, momentum) y **de cadena** (exposición a nodos críticos vía $\Psi$) | $B\in\mathbb{R}^{n\times k}$ | ✗ (los 69 "factores" de hoy son hiperaristas cualitativas, otro concepto) |
| Optimización | mínima varianza, paridad de riesgo (✔), **media-CVaR** (Rockafellar-Uryasev, programa lineal), con costos y rotación | $w^\star\in\Delta^n$ | inv-vol y ERC ✔ |
| Concentración | HHI $=\sum w_i^2$; contribución al riesgo $RC_i=w_i(\Sigma w)_i/\sigma_p$ (Euler) | — | ✔ |
| Liquidez | ADV, días para liquidar $=\lvert q_i\rvert /(\beta\,\text{ADV}_i)$, spread de Corwin-Schultz (máx/mín) | $\mathbb{R}^n$ | ✗ (las velas tiran el volumen) |
| Sensibilidad | $\partial\sigma_p/\partial w=\Sigma w/\sigma_p$; $\partial\,\text{P\&L}/\partial f=B^\top w$; griegas | — | griegas ✔ |
| Escenarios | choque estructural → retorno: $r^{\text{esc}}_i=-\kappa\cdot\text{impacto}_i$ con $\kappa$ CALIBRADO en eventos históricos | $\mathbb{R}^n$ | grafo ✔, **traducción a P&L ✗** |
| Monte Carlo | **simulación histórica filtrada** (FHS): $r^{(m)}_{t+h}=\sigma_{t+h}\,z^{(m)}$, $z$ remuestreado de residuos estandarizados | $\mathcal{P}\in\mathbb{R}^{M\times H\times n}$ | solo bandas del kernel ✔ |

### 9.3 Advertencias matemáticas que deciden el diseño

1. **Con $n>T$ la covarianza muestral es singular.** 568 activos con 252 días: $\text{rango}(S)\le251$ → la
   optimización de mínima varianza "encuentra" carteras de varianza cero falsas. Por eso un modelo de **factores** o
   **contracción** (Ledoit-Wolf) no es un lujo: es obligatorio a nivel universo. Dentro de una cartera de 30 activos
   con 252 días, la muestral es aceptable (ya se usa así).
2. **Los escenarios del grafo hoy no se traducen a dinero.** "TSMC cae: 293 empresas afectadas" no dice cuánto
   pierde TU cartera. Puente propuesto: $\Delta\text{P\&L}_p=\sum_i w_{p,i}\,V_p\,r^{\text{esc}}_i$ con
   $r^{\text{esc}}_i=-\kappa\,\text{impacto}_i/100$ y $\kappa$ estimado por regresión sobre episodios reales (escasez
   de chips 2021, controles de exportación oct-2022, terremoto de Taiwán abr-2024) — con su intervalo de confianza
   mostrado al usuario.
3. **Cierres sin ajustar** en el screener y en los indicadores técnicos de investigación producen saltos falsos
   por splits y dividendos. Con la tabla de precios propia, todo lee `adjclose`.
4. **RSI**: hoy usa promedio simple (Cutler); el estándar de mercado es el suavizado de Wilder. Cambiarlo altera
   valores que los agentes ya citan → hacerlo junto con la tabla de precios y anotarlo.

### 9.4 ¿Cuándo pasar de matriz a tensor en finanzas?

Solo cuando se agrega un modo que **varía independientemente**: horizonte ($\mathbb{R}^{T\times n\times H}$),
escenario ($\mathbb{R}^{S\times n}$ por fecha) o trayectoria Monte Carlo ($\mathbb{R}^{M\times H\times n}$). Una pila
de covarianzas $\Sigma_t$ ($T\times n\times n$) **no** se guarda: se guardan los parámetros factoriales por día.

---

## 10. Grafo + embeddings: técnica por técnica (sin IA "porque se puede")

Contexto que decide todo: $N=937$, $\approx1.500$ aristas de flujo (1,6 por nodo y relación), **muy pocas
etiquetas** (claims calificados por resultado: decenas). Los métodos profundos necesitan $10^4$-$10^6$ ejemplos.

| Técnica | Problema que resuelve | Datos que necesita | Costo | Ventaja real para Khipus | ¿Debe existir? |
|---|---|---|---|---|---|
| **node2vec / DeepWalk** | similitud estructural no supervisada | solo el grafo | $O(N\cdot r\cdot L\cdot d)$: segundos | poca: el perfil de proveedores/clientes + $\Psi$ ya da similitud estructural explicable (Hit@10 0,42) | **No** (como mucho, línea de comparación en Fase 4) |
| **GraphSAGE** | embeddings INDUCTIVOS (nodos nuevos) agregando vecinos | rasgos de nodo + una tarea supervisada | $O(L\,\lvert E\rvert \,d^2)$ | ubicar una empresa nueva sin re-entrenar | Fase 4, **solo** si supera a `suggest_links` |
| **GAT** | pesos de atención por vecino ("qué proveedor importa") | etiquetas abundantes | como GraphSAGE + atención | interpretabilidad atractiva… con datos que no hay | **No** |
| **KG embeddings** (TransE, RotatE, ComplEx, RESCAL) | predicción de vínculos multi-relacional | tripletas (2.510) | $O(\lvert E\rvert \,d)$ por época | completar el grafo | Fase 4 como experimento: adoptar si +10 pts de Hit@10 sobre lo actual |
| **Graph transformers** | atención global con codificación posicional | grafos grandes y muchas etiquetas | $O(N^2)$ | ninguna a esta escala | **No** |
| **Embeddings de TEXTO** (no de grafo) | búsqueda semántica, deduplicar noticias y conclusiones, enlazar noticias a entidades | texto (noticias, claims, descripciones) | modelo local pequeño en CPU o API barata | **alta**: hoy "semántico" es comparar letras | **Sí — Fase 2**, con `pgvector` |
| **GNN de propagación "aprendida"** | ajustar el kernel de choques | episodios históricos de choque + reacción de precios | ~10 parámetros | **alta**: el kernel actual YA es una GNN lineal con pesos a mano | **Sí — Fase 4**, pero como CALIBRACIÓN, no como red profunda |

**La observación clave**: el motor de propagación $x^{(k+1)}=\min\big(1,\ \alpha\,\text{diag}(f)\,T^\top x^{(k)}\big)$ es
**una capa de red neuronal de grafos** con función de activación $\min(1,\cdot)$ y pesos fijados a mano: criticidad
por relación $\alpha_r$ (9), amortiguación (1), piso de proveedor único (1), escala de fragilidad (1). En vez de una
GNN profunda (miles de parámetros, sin datos), la Graph-ML correcta para Khipus es **estimar esos ~12 parámetros por
máxima verosimilitud** sobre episodios reales:

$$
\hat\pi=\arg\min_\pi\sum_{\text{episodios }e}\sum_i\Big(r^{\text{obs}}_{e,i}-\big(-\kappa\cdot\text{impacto}_i(\pi;\text{choque}_e)\big)\Big)^2+\lambda\lVert\pi-\pi_0\rVert^2,
$$

con regularización hacia los valores actuales $\pi_0$. Doce parámetros con decenas de episodios es estadísticamente
razonable; doce mil no.

---

## 11. Almacenamiento: comparación A-E

**Tamaño real a 10 años** (lo que decide): grafo ≈ 10³ nodos, 10⁴ aristas, 10⁵-10⁶ eventos (< 1 GB); precios EOD de
600 instrumentos × 2.520 días ≈ 1,5 M filas (≈ 100-150 MB); embeddings de texto: 100 noticias/día × 384 floats ×
4 B ≈ 55 MB/año; registros de IA y research: decenas de MB/año. **Todo Khipus cabe en una sola instancia de
Postgres con holgura durante años.**

| Criterio | A. Grafo + vectorial + analítica | B. Grafo + columnar + índice vectorial | **C. Postgres + extensiones** | D. Lakehouse + capa de grafo + índice | E. Híbrida |
|---|---|---|---|---|---|
| Costo | alto (3 servicios) | alto | **bajo (ya pagado)** | medio (almacenamiento barato, cómputo aparte) | según mezcla |
| Simplicidad inicial | baja | baja | **alta** | media-baja | media |
| Escalabilidad | alta | alta | media-alta (hasta ~10⁸ filas sin drama) | muy alta | alta |
| Dependencia de proveedor | alta (Neo4j/Pinecone) | media-alta | **mínima (Postgres es estándar)** | baja (Parquet abierto) | baja si se elige bien |
| Ejecutar agentes | bien | bien | **bien (todo en un lugar, transacciones)** | regular (latencia) | bien |
| Consultas rápidas | grafo profundo excelente | analítica excelente | **buenas a esta escala** (recorridos en memoria) | analítica excelente, puntuales lentas | buenas |
| Series financieras | vía analítica | **excelente** | buena (particiones + BRIN; Timescale si hay) | excelente | excelente |
| Bitemporalidad | difícil en grafo | difícil | **natural (rangos + GiST)** | posible (versionado de tablas) | — |
| MCP/API | 3 conectores | 3 | **1** | 2 | 2-3 |

**Recorridos de grafo sin base de grafos**: dos saltos desde Nvidia (grado 196, mediana 3) tocan ~10³ aristas; en
una lista de adyacencia en memoria es del orden de microsegundos. Una consulta recursiva (`WITH RECURSIVE`) en
Postgres sobre 10⁴ aristas indexadas tarda milisegundos. Una base de grafos (Neo4j, AGE) gana cuando los recorridos
son profundos y el grafo tiene 10⁷+ aristas. Khipus está 3-4 órdenes de magnitud por debajo.

**Decisión**:

- **Primera etapa (Fases 1-3): C.** Postgres = registro de eventos (fuente de verdad) + estado materializado +
  series particionadas por mes + `pgvector` (Fase 2, índice HNSW). El cálculo numérico vive en el proceso
  (numpy/scipy), con cachés versionadas. Exportación nocturna a **Parquet** para análisis pesados y backtests con
  **DuckDB** dentro del mismo proceso (sin servidor nuevo). **Retirar Neo4j**: hoy es un espejo que solo recibe
  escrituras del navegador, nadie lo lee y deriva de Postgres.
- **Objetivo largo plazo: E (híbrida mínima)** = Postgres (transaccional + eventos + vectores) + lago Parquet/DuckDB
  (analítica, backtests, Monte Carlo masivo) + un **trabajador de cálculo separado** del servidor web (hoy hay 1
  worker de gunicorn: un cálculo pesado bloquea la app). Motores especializados (vectorial dedicado, grafo) **solo
  si se cruzan umbrales medibles**: > 10⁷ vectores o p95 de búsqueda > 100 ms; > 10⁷ aristas o recorridos > 4 saltos
  en línea.

---

## 12. Almacenamiento ≠ cálculo: el pipeline

Los datos se guardan en la forma que mejor preserva verdad y trazabilidad (eventos, filas, series) y se
**transforman temporalmente** en la forma que mejor sirve a la operación:

```
 ALMACENADO (fuente de verdad)        DERIVADO con versión (caché)            TRANSITORIO (vive en una operación)
 ─────────────────────────────        ─────────────────────────────           ───────────────────────────────────
 L1 registro de eventos  ───┐
    (bitemporal, append)    │  Γ(L,t)   L3 G_t: lista de adyacencia ──┐
 L1 series EOD (precios,    ├────────►     tipada + índices            │ consulta    L4  subgrafo S(Q)
    FX, posiciones, NRS)    │           L3 A_r CSR, T, Ψ (época,as_of) ├──────────►      matriz de rasgos F ∈ R^{|S|×d}
 L1 textos (noticias,       │  Ξ(L,t)   L3 X_t: vectores por tipo      │                tensor  (si hace falta)
    claims) + embeddings    ┘           L3 modelo de factores B,F,D    │                     │
                                        L3 embeddings (pgvector)  ─────┘                     ▼
 L2 estado actual                                                                  L4  núcleo matemático
    (objects, links,                                                                   (propagar, VaR, ρ, MC, PPR)
     último precio)                                                                         │
                                                                                            ▼
                                                                                   L5  compresión → hechos tipados
                                                                                            │
                                                                                            ▼
                                                                                   L6  LLM / agente → decisión
                                                                                            │
                                         ◄──────── resultado + decisión se REGISTRAN en L1 (evento) ─┘
```

Reglas del pipeline (verificables con pruebas):

1. **Todo L3 es recalculable desde L1** de forma determinista, y lleva su clave de versión
   $(\text{época},\ \text{as\_of},\ \pi)$.
2. **Nada en L3-L5 es fuente de verdad**: si se borra, se reconstruye.
3. **Los números los calcula L4, nunca el LLM.** El LLM recibe resultados con unidad, fecha y fuente (ya existe el
   "guardián de cifras" que lo exige).
4. **Una sola función por transformación**: un constructor de matrices, un kernel, una fórmula NRS, un armador de
   contexto. Ese es el aprendizaje principal de la limpieza.

Ejemplo concreto — "Data → Graph Query → Feature Matrix → Tensor → Model → Prediction" para *¿qué empresas se
parecen a ASML en riesgo?*: eventos → $G_t$ → vecinos 2 saltos + mismo sector ($|S|\approx60$) → $F\in\mathbb{R}^{60\times(8+14)}$
(estructural + financiero, estandarizado por bloque) → (sin tensor: no hay un tercer modo) → similitud por bloques
$s=\sum\alpha_ks_k$ → top-5 con explicación por bloque. Si la pregunta fuera *"…y cómo evolucionó ese parecido en
3 años"*, aparece un modo temporal y se arma $\mathcal{F}\in\mathbb{R}^{36\times60\times22}$ (meses × empresas × rasgos)
por 1 segundo.

---

## 13. Motor de contexto para agentes y compresión $R(v,e\mid Q)$

### 13.1 El problema medido

Hoy hay **4 armadores de contexto** independientes (investigación `ContextBuilder`, `core/semantic`, paquetes de
habilidad, prompt del chat), cada uno con su detección de entidades y su subgrafo. Costo típico: ≈10k tokens de
entrada por pregunta del chat, ≈14k por analista de investigación, sin caché de prompt, con el contexto creciendo en
cada ronda (crecimiento cuadrático del total) y la respuesta reescrita dos veces cuando va al modelo profundo.

### 13.2 El pipeline (un solo motor, `core/context_engine.py`)

```
 Q (pregunta + usuario + presupuesto B + tiempo t)
   │
   ├─1─► Resolución determinista: entidades (core.entities / KhipuResolve), intención (Jev o reglas),
   │     horizonte, ventana temporal (t_v, t_k)                                  [sin IA, < 5 ms]
   │
   ├─2─► Selección en el grafo: semillas S_Q → candidatos C = vecindario tipado por intención
   │     (aguas arriba / abajo / cartera / sector), solo FLUJO salvo que se pida              [O(Σ grado)]
   │
   ├─3─► Filtro temporal: G(t_v, t_k), series en la ventana                                  [índices]
   │
   ├─4─► Extracción de rasgos: x_v para v ∈ C (estructural, financiero, riesgo)              [caché L3]
   │
   ├─5─► Cálculo: lo que la intención pida — Ψ_S (impacto), VaR, exposición, correlación,
   │     anomalías, similitud. NÚMEROS LISTOS, con unidad, fecha y fuente                    [L4]
   │
   ├─6─► Puntaje R(v|Q), R(e|Q) y empaquetado bajo presupuesto B (13.3-13.4)
   │
   ├─7─► Render compacto: tabla de hechos tipados + resumen estadístico de la "cola"
   │     descartada ("otros 37 proveedores: 12 % del peso, ninguno crítico")
   │
   └─8─► LLM (prompt de sistema CACHEADO) → respuesta con citas [F#] → se registra (L1)
```

### 13.3 La función de relevancia

Para un nodo candidato $v$ y una consulta $Q$ con semillas $S_Q$:

$$
R(v\mid Q)=\underbrace{\pi_Q(v)}_{\text{alcance}}\cdot\underbrace{\big(1+\lambda_s\,\text{sem}(v,Q)\big)}_{\text{tema}}\cdot\underbrace{e^{-\Delta t_v/\tau_{\phi(v)}}}_{\text{frescura}}\cdot\underbrace{\big(\epsilon+I_v\big)}_{\text{impacto}}\cdot\underbrace{\big(1+\lambda_u\,U_v\big)}_{\text{incertidumbre}}
$$

**Por qué un producto y no una suma**: los factores son *compuertas* — un nodo inalcanzable desde la pregunta
($\pi_Q=0$) no debe entrar por ser muy "impactante" en abstracto; un dato viejo sobre algo cercano debe pesar menos.
En una suma ponderada, un término grande compensa a otro nulo; aquí no.

Cada factor, con su justificación:

| Factor | Definición | Por qué así |
|---|---|---|
| **Alcance / distancia / dependencia / causalidad** $\pi_Q(v)$ | PageRank personalizado desde $S_Q$ sobre el grafo de FLUJO orientado según la intención: $\pi=(1-\beta)e_{S_Q}+\beta P^\top\pi$; para "¿quién sufre si cae X?", directamente $\Psi[S_Q,v]$ (impacto propagado, ya calculado) | Une distancia, dirección causal (proveedor→cliente) y dependencia en un solo número con significado ("si X cae, v pierde 18 %"). Una distancia en saltos sola ignora que 1 salto débil importa menos que 2 fuertes |
| **Tema** $\text{sem}(v,Q)$ | coseno entre el embedding de la pregunta y el texto de $v$ (Fase 2); en Fase 1, 0 | Distingue "Nvidia + memoria" de "Nvidia + energía" |
| **Frescura** | $\tau$ por tipo: noticias 3 días, filings 90 días, estructura $\infty$ | La estructura no envejece; las noticias sí |
| **Impacto financiero** $I_v$ | en preguntas de cartera: $\lvert w_v\rvert \sigma_v$ (contribución al riesgo); en preguntas de empresa: capitalización en riesgo $(\Psi^\top c)_v$ normalizada | Lo que mueve dinero primero |
| **Incertidumbre** $U_v$ | $1-c$ (confianza) o desacuerdo entre fuentes/claims | Lo incierto que importa debe MOSTRARSE (marcado), no esconderse; $\lambda_u$ pequeño |
| **Centralidad** | entra vía $\pi_Q$ (PPR ya favorece nodos centrales alcanzables) | Evita contarla dos veces |

Para aristas: $R(e=(u,v)\mid Q)=\sqrt{R(u\mid Q)\,R(v\mid Q)}\cdot\tilde w_e\cdot c_e$ (importa si sus dos extremos
importan, si es fuerte y si es confiable).

### 13.4 Empaquetado bajo presupuesto (el "compresor")

Idea: elegir el conjunto de hechos $F\subseteq\mathcal{F}$ que maximiza

$$
\max_F\ \sum_{f\in F}R(f\mid Q)\;-\;\mu\!\!\sum_{f,g\in F}\!\!\text{sim}(f,g)\quad\text{s.a.}\quad\sum_{f\in F}\text{tok}(f)\le B.
$$

La penalización por pares hace la función submodular pero **no monótona** (agregar un hecho redundante puede
bajarla), y la restricción de tokens es de tipo mochila: ahí el voraz "simple" no tiene garantía constante. Por eso
se usa la forma **monótona** equivalente en espíritu, de cobertura ponderada ("ubicación de instalaciones"):
$$
F(S)=\sum_{g\in\mathcal{F}}R(g\mid Q)\,\max_{f\in S}\text{sim}(f,g),
$$
(cada hecho candidato $g$ queda "cubierto" por el elemento más parecido elegido: un segundo hecho casi igual no suma).
Para monótona submodular con mochila, **el mejor entre el voraz por cociente $\Delta F/\text{tok}$ y el mejor
elemento individual** garantiza $\ge\tfrac12(1-1/e)\approx31{,}6\,\%$ del óptimo (Leskovec et al., 2007; con
enumeración parcial se llega a $1-1/e$, Sviridenko 2004), en $O(|\mathcal{F}|^2)$ con evaluación perezosa — en la
práctica, a centésimas del óptimo con $|\mathcal{F}|\approx10^2$. Lo descartado no desaparece: se resume con
**estadísticos suficientes** (conteo, peso total, máximo, distribución por país) — compresión con pérdida
controlada.

**Formato del contexto**: hechos tipados en tabla (`id | hecho | valor | unidad | fecha | fuente | conf`), ≈40 %
menos tokens que el JSON equivalente, con referencias `[F#]` que la respuesta debe citar (mismo mecanismo que E# de
la investigación).

### 13.5 Ahorro esperado (estimación con las cifras medidas)

| Medida | Ahorro |
|---|---|
| Caché de prompt de Anthropic en el sistema + catálogo de herramientas (≈2,1k tokens fijos por paso) | el bloque cacheado se cobra ≈10 % → −1,9k tokens efectivos por paso |
| Números precalculados + tabla de hechos en vez de volcados JSON de herramientas (scratch de hasta 26k caracteres) | contexto de herramientas de ~6-7k a ~1,5-2k tokens |
| Paso profundo que reescribe la respuesta → que solo el modelo profundo escriba, con el contexto ya armado | −1 llamada completa (≈ −5k tokens) en la ruta profunda |
| Pool de evidencia compartido por (entidad, fuente, día) para los 4 analistas | noticias y perfil se traen 1 vez, no 4 |
| MCP: `detail` = brief / full, y `max_chars` (la copia en texto que pide la especificación se achica con el resultado) | hasta 20× menos en `brief` |

Meta realista: **chat de ~10k a ~3k tokens por pregunta** con igual o mejor calidad (más números verificados, menos
texto crudo).

---

## 14. Capa de agentes: un solo mundo, roles distintos

**Principio**: un agente = (rol, subconjunto PERMITIDO de operaciones MCP, política, presupuesto). Ningún agente
tiene base de conocimiento propia: todos leen el mismo $G_t$, las mismas series y el mismo motor de contexto, y
escriben sus conclusiones en el mismo "pizarrón" (tabla de claims con evidencia, ya existe).

| Agente pedido | ¿Necesita IA para RAZONAR? | Qué es en Khipus | Mascota |
|---|---|---|---|
| **Research** | **sí** | el enjambre de investigación (claims con evidencia E#, confianza calculada, falsadores) | Analista / Radar / Cadena / Técnico |
| **Market** | sí (interpretar movimientos y noticias) | anomalías + noticias + movimientos del día | Técnico / Radar |
| **Macro** | sí | macro + World Monitor + GPR | Analista (macro) / Radar |
| **Reporting** | solo para NARRAR | informes de cartera y brief (números deterministas, prosa con guardián de cifras) | Khipu |
| **Portfolio** | no (cálculo) + IA para explicar | asesor de cartera: reglas sobre riesgo/exposición (ya existe) | Comité |
| **Risk** | **no** | servicio de riesgo: VaR/CVaR/exposición/escenarios — fórmulas auditables | Técnico |
| **Compliance** | **no — debe ser determinista** | motor de reglas: mandato, límites, listas, aprobación humana, auditoría append-only. Una IA no puede ser la que dice "esto cumple" | (nuevo, sin mascota: es un control) |
| **Data** | **no** | ingesta, calidad, auditoría del grafo, verificación de cotización, reconciliación (ya existen piezas) | (servicio) |
| **Trading** | **no decide nunca** | `preview → confirm` con PIN; solo ejecuta lo aprobado (regla de oro) | (servicio) |

**Crítica**: 9 agentes con LLM serían 9 lugares donde la IA puede inventar, 9 costos y 9 superficies de ataque. De
los 9, **5 son servicios deterministas** con, a lo sumo, una IA narradora. Eso es más barato, más auditable y más
correcto. La coordinación ya existe: el comité arma la sala con los puestos y el presidente decide con un núcleo
cuantitativo determinista (Q1) — el patrón a mantener es **"la IA argumenta, la matemática decide los números, el
humano aprueba el dinero"**.

```
                 ┌──────────────── Representación común del mundo ────────────────┐
                 │  L1 eventos · series EOD · libro mayor · textos   (Postgres)    │
                 │  L3 G_t · A_r/Ψ · X_t · factores · embeddings   (cachés)        │
                 └───────────────▲───────────────────────────────▲─────────────────┘
                                 │ operaciones MCP tipadas       │ claims / decisiones (append)
        ┌────────────────────────┼───────────────────────────────┼──────────────────────┐
        │  Motor de contexto (UNO)    R(v|Q) · presupuesto B · hechos [F#]               │
        └───▲──────────▲──────────▲──────────▲──────────▲──────────▲──────────▲─────────┘
            │          │          │          │          │          │          │
        Research    Market     Macro    Reporting  Portfolio    Risk     Compliance/Data/Trading
        (IA)        (IA)       (IA)     (IA narra) (reglas+IA)  (cálculo) (deterministas, sin IA)
```

---

## 15. Interfaz MCP / API: las 11 operaciones

Contrato común de TODA respuesta:
`{data, as_of, valid_at, known_at, sources[], method, uncertainty, detail, truncated, tokens_estimate}`.
Parámetros comunes: `as_of` (validez), `known_at` (conocimiento, Fase 2), `detail ∈ {brief, full}`, `max_chars`.
Nada en la interfaz revela cómo se almacena (el agente nunca ve tablas, CSR ni Parquet).

| Operación | Entrada | Devuelve | Implementación (hoy → propuesta) |
|---|---|---|---|
| `get_entity` | id/nombre/ticker, campos | identidad, alias, identificadores por bolsa, atributos con fecha y fuente, resumen de vectores (estructural/financiero/riesgo), NRS con sus 5 términos | `get_company` (10k caracteres en Nvidia) → versión `brief` ≈1,5k |
| `get_relationships` | id, tipos/clase, dirección, `min_conf`, límite | aristas con θ, validez, confianza, fuente; socios/inversores aparte | `get_supply_chain` profundidad 1 |
| `get_subgraph` | semillas, pregunta opcional, profundidad ≤ 3, **presupuesto** | nodos y aristas ordenados por $R(v\mid Q)$ + resumen de la cola omitida | ✚ (motor de contexto) |
| `get_history` | id, métricas, ventana, frecuencia | series (precio, capitalización, NRS, rasgos) + eventos del grafo con $t^v$/$t^k$ | rutas de historia y línea de tiempo de `/api/ontology/*` + ✚ series EOD |
| `get_exposure` | cartera o entidad, dimensiones (sector, país, factor, país de proveedores, moneda) | vector de exposición por dimensión, top contribuyentes, exposición INDIRECTA vía $\Psi$ | ◐ partes en asesor y tensor → ✚ unificado |
| `calculate_risk` | cartera, horizonte, método (hist/param/FHS), $\alpha$ | vol, VaR, CVaR, beta, contribución al riesgo, drawdown, backtest (Kupiec) | `get_risk_report` ✔ (+CVaR multi-día, FHS) |
| `calculate_correlation` | ids, ventana, método (pearson/spearman/EWMA/contraído) | matriz + error estándar + cambios de régimen | ◐ dentro de risk_report → ✚ |
| `run_scenario` | choque (entidad/factor/país/sector, tipo, severidad), horizonte, cartera opcional | impacto estructural por nodo (kernel ÚNICO) + **P&L estimado con bandas** + ganadores/perdedores | 3 motores distintos → ✚ uno |
| `find_similar_entities` | id, espacio (estructural/financiero/semántico/combinado), k | vecinos con puntaje POR ESPACIO (explicable) | `tensor.peers` interno → ✚ |
| `find_anomalies` | alcance (cartera/sector/universo), ventana, tipos (precio z, volumen, quiebre de correlación, cambio estructural, ráfaga de noticias) | anomalías ordenadas con su z y su línea base | ◐ umbral fijo 8 % → ✚ estadístico |
| `project_portfolio` | cartera, horizonte, método (FHS/bootstrap), escenarios | cuantiles, probabilidad de pérdida > x, abanico de trayectorias; **"no es un pronóstico"** explícito | ✗ → ✚ |

Mejoras al servidor MCP actual: la especificación (2025-06-18) pide que un resultado con `structuredContent`
repita el JSON como texto por compatibilidad — está bien hacerlo, pero entonces el tamaño importa el doble:
`get_supply_chain` de profundidad 2 llega a 102k caracteres → `detail`/`max_chars` en TODAS las operaciones; y un
solo catálogo de herramientas para el chat y el MCP.

---

## 16. La abstracción $K:(D,G,X,T,Q)\to C$: correcciones

Tu formulación capta lo esencial (el valor está en producir un contexto $C$ relevante), pero tiene cinco defectos:

1. **$T$ no es una entrada**: los tensores son funciones de $G$ y $X$ ($T=\Phi(G,X)$). Ponerlos como entrada
   independiente permite que $T$ y $G$ se contradigan — exactamente lo que pasó con los 4 motores.
2. **$D$, $G$, $X$ tampoco son independientes**: los tres derivan del registro de eventos. La única entrada de
   estado es $\mathcal{L}$.
3. **Falta el tiempo explícito** (doble): la consulta debe fijar $(t^v,t^k)$.
4. **Faltan el presupuesto $B$ y los permisos $U$**: qué puede ver este agente/usuario y cuánto cabe.
5. **Falta el lazo de aprendizaje**: $C\to\text{IA}\to\text{Decisión}$ termina ahí; pero las decisiones tienen
   resultados (Khipus ya los mide: calificación de claims contra el S&P 500), y esos resultados deben ajustar el
   sistema (confiabilidad por analista, calibración, parámetros del kernel).

**Versión propuesta**:

$$
K_\vartheta(\mathcal{L},Q,U,B)=\operatorname*{arg\,max}_{F\subseteq\mathcal{F}(G_{t},X_{t},Q)\cap\text{Perm}(U)}\Big[\sum_{f\in F}R_\vartheta(f\mid Q)-\mu\,\text{Red}(F)\Big]\ \ \text{s.a.}\ \ \text{tok}(F)\le B,
$$

$$
G_t=\Gamma(\mathcal{L},t^v,t^k),\quad X_t=\Xi(\mathcal{L},t^v,t^k),\quad \mathcal{F}=\text{Analyze}\circ\text{Extract}\circ\text{Select}_Q(G_t,X_t),
$$

$$
D=\pi(C,\text{LLM}),\qquad O=\text{resultado}(D,\ t+h),\qquad \vartheta_{t+1}=\text{update}(\vartheta_t,\ O).
$$

Es decir, Khipus es una **composición de funciones** (materializar → seleccionar → extraer → analizar →
comprimir) con un **parámetro aprendible $\vartheta$** (pesos de relevancia, confiabilidades, parámetros del kernel)
que se actualiza con resultados reales. Sin el lazo, el sistema no mejora; con él, cada decisión registrada es un
dato de entrenamiento.

---

## 17. Arquitectura final

### 17.1 Conceptual

```
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║  FUENTES   Yahoo/Finnhub · FMP · SEC · GDELT/USGS/EONET · OFAC/BIS · noticias · Alpaca ·  ║
║            catálogo curado (nodes/*.js) · decisiones de Fabrizio y de los agentes        ║
╚═══════════════════════════════════════╤══════════════════════════════════════════════════╝
                                        │ ingesta (Data: determinista, con procedencia)
╔═══════════════════════════════════════▼══════════════════════════════════════════════════╗
║  MEMORIA (fuente de verdad, append-only, bitemporal)                     Postgres          ║
║    registro de eventos 𝓛  │  series EOD  │  libro mayor  │  textos (+ embeddings)          ║
╚═══════════════════════════════════════╤══════════════════════════════════════════════════╝
                                        │ Γ, Ξ (materializar en t_v, t_k)
╔═══════════════════════════════════════▼══════════════════════════════════════════════════╗
║  REPRESENTACIÓN DEL MUNDO (derivada, versionada por época/as_of)                           ║
║    GRAFO G_t (identidad, relaciones)   VECTORES X_t (estado)   ESTRUCTURAS DE CÁLCULO      ║
║                                                                (A_r CSR, Ψ, factores, ℰ…)  ║
╚═══════════════════════════════════════╤══════════════════════════════════════════════════╝
                                        │ núcleos matemáticos ÚNICOS (propagar, riesgo, ρ, MC…)
╔═══════════════════════════════════════▼══════════════════════════════════════════════════╗
║  MOTOR DE CONTEXTO   Q → selección (π_Q, Ψ) → cálculo → R(v|Q) → empaquetado bajo B → [F#]  ║
╚═══════════════════════════════════════╤══════════════════════════════════════════════════╝
                                        │ 11 operaciones MCP/API (contrato común)
╔═══════════════════════════════════════▼══════════════════════════════════════════════════╗
║  AGENTES  IA: Research · Market · Macro · Reporting   |   deterministas: Risk · Portfolio ·║
║           Compliance · Data · Trading   |   IAs externas vía MCP   |   Khipus OS (UI)      ║
╚═══════════════════════════════════════╤══════════════════════════════════════════════════╝
                                        │ decisión → aprobación HUMANA (dinero) → ejecución
                                        ▼
                         resultados medidos → calibración ϑ (lazo de aprendizaje)
```

### 17.2 Matemática (los objetos y sus relaciones)

```
 𝓛 ──Γ──► G_t=(V_t,E_t,φ,ψ)  ──build──►  {A_r ∈ R^{N×N}}_r (CSR) ──normalizar──► T = Σ_r α_r A_r D_r⁻¹
 │                                                                                   │
 │                                                     Ψ = max_k min(1,(αTᵀ)^k ⊙ f)  ◄┘  (6 saltos; αρ=0,54)
 │
 └──Ξ──► X_t:  x_v^struct ∈ R^8 · x_v^fin ∈ R^14 · x_v^risk · x_v^sem ∈ R^384 (Fase 2)
          P ∈ R^{T×n} ──► R (retornos) ──► Σ = BFBᵀ + D (k≈10)  ──► VaR, CVaR, RC, ρ_ij en O(k)
          w_p(t) (libro) ──► exposición e = Bᵀw, Sᵀw, Cᵀw, "cadena" = f(Ψ, w)
          escenario: choque s ──► impacto = propagar(T, s) ──► r^esc = −κ·impacto ──► ΔP&L = wᵀ r^esc
```

### 17.3 Datos (esquema lógico)

```
 entidades ─────────── objects(id, type, label, properties)           ← materializado de events
 relaciones ────────── links(source, target, rel, w, conf, valid_from, valid_to, event_id)
 historia ──────────── events(id, type, object_id, target_id, payload, valid_from, valid_to,
                              recorded_at, source_id, confidence)      ← append-only (disparador, Fase 2)
 instrumentos ✚ ────── instruments(id, company_id, symbol, venue, currency, kind)
 series ✚ ──────────── eod_prices(instrument_id, date, open, high, low, close, adjclose, volume, src)
                       entity_daily(entity_id, date, features jsonb)   ← NRS, capitalización, fundamentales
                       positions_eod(owner, portfolio, instrument_id, date, qty)
 libro mayor ───────── broker_orders, broker_audit (✔), fills ✚
 conocimiento ──────── research_claims, research_evidence, claim_outcomes, calibration_snapshots (✔)
 textos ✚ ──────────── documents(id, kind, entity_ids, published_at, text, embedding vector(384))
```

### 17.4 Almacenamiento físico

```
 Postgres (Railway)                     │ proceso Khipus (1 worker web)    │ trabajador de cálculo (Fase 5)
 ───────────────────────────────────────┼──────────────────────────────────┼──────────────────────────────
 eventos, objetos, vínculos (B-tree,    │ G_t en listas de adyacencia      │ Monte Carlo grande, backtests,
   GiST por intervalo en Fase 2)        │ A_r/Ψ CSR, factores, cachés      │ calibración del kernel
 series particionadas por mes + BRIN    │   por (época, as_of, π)          │ lee Parquet con DuckDB
 pgvector HNSW (Fase 2)                 │ numpy / scipy.sparse             │
 claims, memos, auditoría               │                                  │
 ── export nocturno ─► Parquet (lago barato, Fase 3) ◄──────────────────────────────────────────┘
```

### 17.5 Cálculo (cuándo corre cada cosa)

| Cómputo | Disparador | Costo medido / estimado | Vive en |
|---|---|---|---|
| $G_t$, $A_r$, $T$ | cambio de época del grafo | 0,2 s | caché L3 |
| $\Psi$ (todos los choques) | época o capitalizaciones (15 min) | 0,3 s disperso | caché L3 |
| Métricas de red (cascada, PageRank, ρ) | época | < 1 s (antes 30-50 s) | caché L3 |
| Precios EOD | 1×/día tras el cierre (scheduler) | 568 símbolos en lotes: ~1 min | L1 |
| Rasgos diarios (entity_daily) | 1×/día | segundos | L1 |
| Modelo de factores | 1×/día | SVD aleatorizada: ms | L3 (+ parámetros diarios en L1) |
| Embeddings de texto | al ingerir cada documento | ~ms por texto (modelo pequeño) | L1 (pgvector) |
| Riesgo / exposición / escenario de UNA cartera | bajo demanda | ms - 1 s | transitorio |
| Monte Carlo FHS (10k × 20 días × 30 activos) | bajo demanda | ~1 s en numpy | transitorio |
| Calibración del kernel ($\hat\pi$) | mensual | minutos | trabajador |

### 17.6 Agentes — ver sección 14. 17.7 MCP/API — ver sección 15.

### 17.8 Modelo temporal

```
 tiempo de VALIDEZ  t_v ──►  ¿cuándo fue verdad en el mundo?        (valid_from / valid_to)
 tiempo de CONOCIMIENTO t_k ►  ¿cuándo lo supo Khipus?               (recorded_at)
 consulta G(t_v, t_k):  "el mundo en t_v, según lo que sabíamos en t_k"
   • as_of (hoy)        = G(t_v, ahora)      ✔ existe
   • auditoría          = G(t, t)            ✚ Fase 2
   • corrección         = evento nuevo que retracta (retracts_event_id), nunca UPDATE
 series: un valor por (entidad, fecha); se corrigen con una fila nueva marcada, nunca se pisan
```

### 17.9 Estrategia de embeddings

- **Solo texto** (noticias, claims, descripciones, filings resumidos), un modelo pequeño y fijo (≈384
  dimensiones), versionado en la columna. Usos: búsqueda semántica en `get_subgraph`/chat, deduplicar noticias y
  claims, enlazar noticias a entidades, factor "tema" de $R(v\mid Q)$.
- **Estructura y finanzas: vectores INTERPRETABLES** (sección 5), no embeddings aprendidos.
- Embeddings de grafo aprendidos: solo como experimento comparado (Fase 4).

### 17.10 Estrategia tensorial

- Tensores **solo transitorios o en caché versionada**: $\mathcal{A}$ (CSR), $\mathcal{X}$ (panel, Fase 3),
  $\mathcal{S}$ (escenarios), $\mathcal{P}$ (Monte Carlo).
- Nunca un modo que sea función de otro (sector, país → matrices de agregación).
- Descomposiciones: bajo rango de covarianza (Fase 2), CP/Tucker del panel (Fase 3, exploratorio), RESCAL/ComplEx
  (Fase 4, solo si supera lo actual).

### 17.11 Estrategia de compresión de contexto — ver sección 13 ($R(v\mid Q)$ + empaquetado submodular + cola
resumida + caché de prompt).

### 17.12 Flujo completo: "¿Qué está pasando con mi cartera?"

```
 1  Resolución (sin IA, < 5 ms): usuario → cartera p; intención = "estado de cartera"; ventana = 1 semana
 2  Selección: semillas = posiciones de p (30); candidatos = proveedores críticos (Ψ) + noticias 7 días
    + eventos del World Monitor que tocan sus países          → ~150 candidatos
 3  Temporal: G(hoy, hoy), series de 1 año para riesgo, 5 días para movimiento
 4  Rasgos: x^fin, x^risk de las 30; exposición sector/país/cadena
 5  Cálculo (L4, ~1 s): P&L de la semana vs SPY; VaR/CVaR; contribución al riesgo; anomalías (z de cada
    posición contra su propia vol); impacto en p de los 3 eventos más relevantes (escenario → P&L)
 6  R(v|Q): impacto = |w|σ; alcance = Ψ desde los eventos; frescura 3 días para noticias
 7  Empaquetado B = 1.500 tokens: 12 hechos [F1..F12] + cola resumida ("las otras 24 posiciones: −0,4 %,
    ninguna anomalía")
 8  LLM (sistema cacheado): 3 párrafos con citas [F#]; el guardián de cifras verifica cada número
 9  Registro: la respuesta y sus F# quedan en el registro → auditables y evaluables
 Total ≈ 3k tokens de entrada (hoy ≈10k+), números 100 % calculados por Khipus
```

### 17.13 Ficha por componente

| Componente | Problema que resuelve | Estructura | Consume | Produce | Complejidad | Cuándo | Dónde | ¿Bajo demanda? | Con el grafo | Con los agentes |
|---|---|---|---|---|---|---|---|---|---|---|
| Registro de eventos $\mathcal{L}$ | verdad + historia sin pisar | log bitemporal | ingestas, acciones | eventos | $O(1)$ por evento | siempre | Postgres | — | lo genera | sus decisiones se registran aquí |
| Materializador $\Gamma$ | grafo en un instante | listas de adyacencia + CSR | $\mathcal{L}$ | $G_t$, $A_r$ | $O(\lvert E\rvert )$ (con puntos de control: $O(m)$) | por época / as_of | caché | sí (con caché) | ES el grafo | vía operaciones |
| Kernel de propagación (único) | contagio de choques | serie de Neumann truncada no lineal | $T$, fragilidad | impactos, $\Psi$ | $O(H\cdot\text{nnz})$ por choque | por época / pedido | caché L3 | sí | lee $A_r$ | `run_scenario`, Cadena |
| NRS (único) | riesgo de red legible | 5 términos | nodo + grado de flujo | 0-100 + desglose | $O(1)$ | al pedir | cálculo | sí | grado de flujo | todos |
| Series EOD | historia de mercado | tabla (instrumento, fecha) | Yahoo/Finnhub | precios ajustados | lineal | 1×/día | Postgres particionado | no (ingesta) | por `instrument→company` | Risk, Market, Portfolio |
| Modelo de factores | covarianza estable, exposiciones | $\Sigma=BFB^\top+D$ | retornos | $B,F,D$ diarios | $O(Tnk)$ | 1×/día | L1 (parámetros) | no | factores de cadena desde $\Psi$ | Risk, Portfolio |
| Motor de riesgo | VaR/CVaR/RC/drawdown | vectores y matrices | posiciones, series | métricas + backtest | $O(Tn^2)$ cartera | por pedido | transitorio | sí | exposición indirecta | Risk, Portfolio, Reporting |
| Motor de contexto | contexto mínimo y relevante | PPR/Ψ + submodular | pregunta, $G_t$, $X_t$ | hechos [F#] | $O(\lvert C\rvert ^2)$ perezoso, $\lvert C\rvert \approx10^2$ | cada pregunta | transitorio | sí | selección | TODOS |
| Embeddings de texto | búsqueda por significado | $\mathbb{R}^{384}$ + HNSW | textos | vectores | $O(\log n)$ búsqueda | al ingerir | pgvector | no | enlaza texto→entidad | Research, Market, chat |
| Similitud | pares comparables | fusión tardía por bloques | $X_t$, perfiles | vecinos explicados | $O(N\,d)$ | por pedido | transitorio | sí | perfiles de cadena | `find_similar_entities` |
| Anomalías | qué se salió de lo normal | z-scores, AR, cambios de régimen | series, grafo | lista ordenada | $O(nW)$ | 1×/día + pedido | L1 (alertas) | ambos | contagio por vecinos | Market, alertas |
| Proyección MC | rango de resultados futuros | $\mathcal{P}\in\mathbb{R}^{M\times H\times n}$ | series, posiciones | cuantiles | $O(MHn)$ | por pedido | transitorio | sí | escenarios de cadena (Fase 3) | Portfolio, Reporting |
| Calibración $\vartheta$ | que el sistema aprenda | MLE regularizado | resultados de claims/episodios | pesos | minutos | mensual | L1 | no | ajusta $\alpha_r$ | confiabilidades del comité |
| Compliance | límites y mandato | reglas | órdenes, mandato | sí/no + motivo | $O(1)$ | antes de cada orden | auditoría | sí | — | Trading (obligatorio) |

---

## 18. Qué dice esta arquitectura del Khipus actual (mapa de cambios)

| Hoy | Arquitectura v2 | Esfuerzo |
|---|---|---|
| 4 copias del grafo (catálogo JS, snapshot, Postgres, Neo4j) | Postgres = verdad; catálogo → eventos por reconciliación; snapshot GENERADO; Neo4j retirado | M |
| 4 kernels de propagación | 1 kernel (servidor) + el cliente lo consulta o replica con prueba de paridad | M |
| 6 fórmulas NRS | **1 (hecho hoy)** | ✔ |
| 4 armadores de contexto | 1 motor de contexto | M |
| Sin historia de precios / posiciones / métricas | series EOD + fotos diarias | S-M |
| Empresa = acción (`mkt`) | Instrumento como tipo (ADR, multi-bolsa, cripto) | M |
| Escalas de peso mezcladas (0-1 y 1-6) | escala única [0,1] con revisión | M (datos) |
| Direcciones de vínculos dudosas (32 marcadas + otras no detectadas, p. ej. OpenAI→Nvidia "usa clusters de H100") | puerta de calidad: detector de dirección por texto + lista de revisión | S |
| Escenarios sin P&L | escenario → retorno calibrado ($\kappa$) → P&L con bandas | M |
| MCP con payloads duplicados y enormes | contrato común + `detail` | S |
| Sin caché de prompt | caché en sistema + catálogo | S |
| Motor denso por defecto | **disperso (hecho hoy)** | ✔ |

---

## 19. Crítica de las ideas de partida (lo que NO haría y por qué)

1. **"Cada cosa un nodo"** (usuario, transacción, orden, posición como nodos). Las transacciones no se recorren:
   se agregan. Como nodos inflan $V$ sin aportar caminos útiles y vuelven lentas las consultas temporales.
   → Libro mayor + posiciones como función (3.4).
2. **"Activo, instrumento, acción, bono, ETF, criptomoneda" como seis tipos.** Son UN tipo (instrumento) con
   subtipo; separarlos multiplica las firmas del esquema por seis sin ganar nada. Y **empresa ≠ instrumento**:
   hoy Khipus las confunde (TSMC tiene 2330.TW y el ADR TSM).
3. **Correlación como arista guardada.** Es una propiedad de (par, ventana, estimador), densa ($O(n^2)$) y ruidosa.
   → Modelo de factores + cálculo bajo demanda (sección 4).
4. **El tensor activo × sector × país × tiempo × métrica.** El sector y el país son funciones del activo: el tensor
   es 99,9 % vacío y 1.768× más grande de lo necesario; "agrupar por sector" es una contracción con una
   indicadora (6.2).
5. **$x_i=\sum_k W_kx^k_i$ sin datos para aprender $W$.** Mezcla espacios con escalas y significados distintos
   (justo lo que temías). → Fusión tardía por puntaje, explicable (5.2).
6. **GNN, GAT, graph transformers "para la inferencia".** Con 937 nodos, ~1.500 aristas de flujo y decenas de
   resultados calificados, aprenden ruido. La Graph-ML que sí conviene es calibrar los ~12 parámetros del kernel
   actual (sección 10).
7. **Opción A de almacenamiento (base de grafos + vectorial + analítica).** Tres sistemas, tres facturas y tres
   puntos de falla para menos de 1 GB de datos. → Postgres (C) y crecer a E solo al cruzar umbrales medidos.
8. **$K:(D,G,X,T,Q)\to C$.** $T$ no es entrada; faltan tiempo doble, presupuesto, permisos y el lazo de aprendizaje
   (sección 16).
9. **Nueve agentes de IA.** Cinco deben ser servicios deterministas (Risk, Portfolio, Compliance, Data, Trading).
   Un agente de cumplimiento con LLM es un riesgo, no un control.
10. **"Minimizar tokens" como meta principal.** El mayor ahorro no viene de comprimir más, sino de (a) cachear lo
    fijo, (b) no hacer que la IA calcule y (c) no repetir pasos. Comprimir de más pierde matices; la meta correcta
    es **máxima información relevante por token**, con el presupuesto como restricción.
11. **"Grafo temporal" con infraestructura antes que datos.** Con 85 de 2.595 vínculos fechados, el mejor motor
    temporal del mundo respondería "no sé". Primero fechar los vínculos importantes y guardar series.
12. **Densidad informacional como objetivo #1.** Las 10 metas que listas compiten entre sí (más densidad ↔ menos
    trazabilidad; más velocidad ↔ más memoria). El orden que propongo para Khipus, por ser una herramienta de
    decisión con dinero: **1. trazabilidad, 2. corrección de los números, 3. compresión, 4. velocidad, 5. el resto.**

---

## 20. Fases

### 20.1 Fase 1 — MVP matemáticamente sólido y barato (orden de implementación)

| # | Entregable | Archivos | Prueba que lo fija |
|---|---|---|---|
| 1 | **Series EOD**: tabla `eod_prices` + ingesta diaria (scheduler) de los 568 símbolos con `adjclose`, volumen y fuente; lectura única para riesgo, screener y técnicos | `core/prices_store.py`, `ontology/db._COLUMNAS_TARDIAS` | ingesta idempotente; split ajustado; sin red en tests |
| 2 | **Fotos diarias**: `entity_daily` (NRS por términos, capitalización, fundamentales) y `positions_eod` | `core/daily_snapshots.py` | una fila por (entidad, día) |
| 3 | **Instrumentos**: tabla + migración desde `mkt` (ADR y multi-bolsa marcados para revisión) | `core/instruments.py` | cada empresa cotizada → ≥ 1 instrumento |
| 4 | **Kernel único**: el cliente (`statematrix.js`) usa el kernel del servidor (suma, no máximo; 6 saltos; umbral; tope de fragilidad) o lo replica con prueba de paridad; `scenario_engine` siembra choques y propaga con el kernel único | `engine/statematrix.js`, `core/scenario_engine.py` | paridad cliente↔servidor sobre 937 choques |
| 5 | **Motor de contexto v1**: selección por $\Psi$/PPR (solo flujo), $R(v\mid Q)$ sin término semántico, empaquetado voraz con redundancia, tabla de hechos [F#]; lo usan chat, @agente, investigación (parte de grafo) y MCP | `core/context_engine.py` | presupuesto respetado; cero aristas partner como "proveedor" |
| 6 | **11 operaciones MCP** con contrato común, `detail` y `max_chars` | `mcp_server/tools.py`, `protocol.py` | tamaño `brief` acotado; esquema validado |
| 7 | **Caché de prompt** (Anthropic) en sistema + catálogo; un catálogo de herramientas para chat y MCP; el modelo profundo escribe una sola vez | `core/ai.py`, `core/khipu_chat.py` | tokens medidos antes/después en `ai_usage` |
| 8 | **Puerta de calidad de datos**: detector de dirección por texto ("usa", "uses", "co-fundó…") + escala de pesos única → lista de revisión para Fabrizio (nada se cambia sin su marca) | `scripts/audit_graph.py` | trinquete de la línea base |

**NO en la Fase 1**: base de grafos o vectorial, embeddings, descomposiciones tensoriales, GNN, datos intradía,
correlaciones guardadas, más Neo4j (se retira). *Por qué*: nada de eso mejora una respuesta mientras falten la
historia de precios, un solo kernel y un solo contexto.

### 20.2 Fase 2 — Grafo temporal + embeddings de texto + analítica

Consultas $G(t^v,t^k)$ (auditoría), replay de propiedades, disparador append-only en `events`, puntos de control
para `as_of`, $\Delta^\theta$ en el diff; fechar los ~200 vínculos más pesados (con fuente); mapear las 12 relaciones
en español al vocabulario; `pgvector` + embeddings de texto (búsqueda, deduplicación, enlace noticia→entidad, término
"tema" de $R$); modelo de factores diario (PCA + sector/país + exposición de cadena), EWMA, Ledoit-Wolf, absorption
ratio y quiebres de correlación; CVaR multi-día.
**NO**: GNN, descomposiciones tensoriales, streaming en tiempo real. *Por qué*: primero hay que acumular historia
para tener algo que modelar.

### 20.3 Fase 3 — Tensores y operaciones avanzadas

Panel $\mathcal{X}$ (tiempo × empresa × rasgo) con CP/Tucker exploratorio (regímenes); biblioteca de escenarios
$\mathcal{S}$ versionada; **escenario → P&L** con $\kappa$ calibrado en episodios reales y bandas; Monte Carlo FHS con
choques de cadena; optimizador media-CVaR con costos y rotación; modelo de liquidez (ADV, días para liquidar);
lago Parquet + DuckDB para backtests.
**NO**: guardar tensores, tensor-train, optimización con pronósticos de retorno de la IA. *Por qué*: los tensores
son de cálculo; y un optimizador alimentado con retornos esperados inventados amplifica el error (error de
estimación de $\mu$).

### 20.4 Fase 4 — Graph ML / modelos especializados

Calibración por máxima verosimilitud de los ~12 parámetros del kernel (sección 10); experimento KG-embeddings vs
`suggest_links` (adoptar solo con +10 pts de Hit@10); GraphSAGE para empresas nuevas solo si supera; pesos de
$R(v\mid Q)$ aprendidos de la retroalimentación del usuario (aprendizaje de ranking).
**NO**: graph transformers, modelos profundos de punta a punta. *Por qué*: las etiquetas disponibles se cuentan en
cientos, no en millones.

### 20.5 Fase 5 — Sistema completo de inteligencia financiera

Motor de cumplimiento determinista (mandatos, listas, límites, aprobaciones, auditoría); usuarios y cuentas reales
(no solo `owner_hash`); trabajador de cálculo separado del web; linaje de datos visible en la UI ("¿de dónde salió
este número?" en un clic); motores especializados SOLO si se cruzan umbrales medidos (>10⁷ vectores, >10⁷ aristas,
p95 > 100 ms).
**NO**: microservicios por moda, Kubernetes, multi-región. *Por qué*: con un solo equipo y < 1 GB de estado, la
complejidad operativa cuesta más que cualquier ganancia.

---

## 21. Glosario mínimo (para leer este documento sin ser matemático)

- **Grafo**: puntos (empresas, países…) unidos por flechas (quién provee a quién).
- **Vector**: una lista de números que describe algo en un momento (margen, deuda, volatilidad…).
- **Matriz**: una tabla de números; la del grafo dice cuánto depende cada empresa de cada otra.
- **Tensor**: una tabla de más de dos dimensiones (por ejemplo empresa × rasgo × mes). Solo se arma para calcular.
- **Disperso**: casi todo cero; se guarda solo lo que no es cero (por eso el motor ahora es 10× más rápido).
- **Bitemporal**: guardar cuándo algo fue verdad Y cuándo lo supimos.
- **Embedding**: convertir un texto en un vector para buscar por significado y no por letras.
- **Modelo de factores**: explicar los movimientos de 568 acciones con ~10 fuerzas comunes; ahorra memoria y da
  correlaciones más estables.
- **VaR / CVaR**: cuánto podrías perder en un mal día (VaR) y cuánto en promedio en los peores días (CVaR).
- **Monte Carlo**: simular miles de futuros posibles para ver el rango de resultados.
- **Submodular / voraz**: forma de elegir la información más útil sin repetirla, con garantía matemática de no
  quedar lejos de lo óptimo.
- **PageRank personalizado**: medir qué tan "alcanzable" e importante es cada empresa desde las que pregunta el usuario.
