# 🔎 Qué investigar de CADA empresa

Lista para llenar la ficha de una empresa (`company.schema.json`). Sirve igual para las ~4.000 nuevas y para
completar las 937 que ya están.

## 🧭 Empieza aquí: no hace falta todo de una vez

| Nivel | Qué incluye | Cuándo |
|---|---|---|
| **A** (entra al grafo) | lo 🔴 de las secciones 1, 2, 3, 4 y 14 + **1 vínculo** con fuente | primero, para las 4.000 |
| **B** (ficha completa) | A + el resto de lo 🔴 (puesto en su mercado, rondas, listas restringidas) + lo 🟡 + 3-10 vínculos | las importantes (P1) |
| **C** (profunda) | B + plantas con capacidad, % de dependencia, segmentos, 🟢 | las críticas (chips, baterías, energía) |

## 📏 La regla de oro (vale para TODO)

- 🔗 **Cada dato lleva su enlace** (la página o el PDF exacto, no "Google"). Primero documentos oficiales; después
  prensa seria (Reuters, Bloomberg, Nikkei, FT, prensa del sector).
- 📅 **Cada dato lleva su fecha**: el día en que ese dato es verdad (`as_of`). Si solo sabes el mes o el año, pon solo
  eso. **Nunca inventes el día.**
- 🎯 **Cada dato lleva tu confianza** de 0 a 1: 0,9 = lo dice un documento oficial; 0,6 = lo dice la prensa; 0,3 = rumor.
- 💬 **Copia una frase textual** de la fuente cuando el dato es un número o un vínculo.
- 🌎 **Textos en español E inglés.**
- 🚫 **Si lo buscaste y NO existe**, anótalo en `not_found`. "No hay" no es lo mismo que "no lo busqué".
- 💵 **Montos en la moneda original y en unidades** (no en millones). Khipus convierte a dólares solo.
- % siempre de **0 a 100** (los márgenes sí pueden ser negativos).

**Leyenda**: 🔴 imprescindible · 🟡 importante · 🟢 deseable · 🐢 cambia lento (revisar cada trimestre o año)

---

## ⛔ NO investigar: llega EN VIVO solo

Khipus lo trae del mercado. Si lo escribes a mano, la ficha se **rechaza**.

- ⛔ Precio de la acción
- ⛔ Capitalización de mercado (se calcula: precio × acciones × tipo de cambio)
- ⛔ Volumen negociado
- ⛔ Tipo de cambio
- ⛔ Múltiplos (P/E, EV/EBITDA…) y valor de empresa (EV)
- ⛔ Acciones en circulación de las que cotizan (Khipus las trae)
- ⛔ Valuación "en negociación" de una privada (Khipus vigila los titulares)
- ⛔ NRS, impacto, grado: los calcula Khipus

👉 Lo que SÍ necesita Khipus para traerlos: los **identificadores** de la sección 1. Sin ellos no hay precio en vivo.

---

## 1️⃣ 🪪 Identidad (sin esto la empresa no puede entrar)

- [ ] 🔴 **Nombre legal exacto**: informe anual, registro de la empresa
- [ ] 🔴 **Nombre corto** que verá el usuario (ej. "CATL")
- [ ] 🔴 **Otros nombres**: siglas, nombre en su idioma (chino, japonés, coreano…), nombres anteriores con fecha.
  Sirve para que la voz y el chat la encuentren
- [ ] 🔴 **Estado**: cotiza / privada / filial / estatal / adquirida / quebrada
- [ ] 🔴 **País de la sede** (código de 2 letras: CN, US, TW…) y **ciudad**
- [ ] 🔴 **Web oficial**
- [ ] 🔴 **Al menos UN identificador fuerte** (cuantos más, mejor):
  - [ ] LEI (20 caracteres) → search.gleif.org (gratis)
  - [ ] ISIN (12 caracteres) → web de la bolsa o GLEIF
  - [ ] CIK (solo si reporta en EE.UU.) → sec.gov/edgar
  - [ ] Wikidata (Q + número) → wikidata.org
  - [ ] FIGI → openfigi.com
- [ ] 🟡 **País donde está constituida** (puede ser Cayman, Países Bajos…): GLEIF
- [ ] 🟡 **Año de fundación**: web "historia", informe anual
- [ ] 🟢 **Coordenadas de la sede**: mapa (marca si es exacta o solo la ciudad)
- [ ] 🟢 **Número en el registro mercantil del país**

## 2️⃣ 📈 Dónde cotiza (si cotiza)

Una fila por cada bolsa. Ejemplo: TSMC cotiza en Taiwán (principal) y como ADR en Nueva York.

- [ ] 🔴 **Ticker** y **bolsa** (código MIC de 4 letras, ej. XNAS, XSHE, XHKG): web de la bolsa
- [ ] 🔴 **Símbolo en Yahoo Finance** con su sufijo (ej. `.SZ`, `.HK`, `.TW`). **Es la llave del precio en vivo**
- [ ] 🔴 **Cuál es la cotización PRINCIPAL**
- [ ] 🔴 **Moneda** de cada cotización
- [ ] 🟡 **Tipo**: acción común, A, H, ADR, OTC, preferente
- [ ] 🟡 **ADR**: cuántas acciones normales vale 1 ADR (TSM = 5): web del banco depositario o 20-F
- [ ] 🟢 Fecha de salida a bolsa

## 3️⃣ 🗂 Dónde encaja en Khipus

- [ ] 🔴 **Categoría** del catálogo (una de las 108; lista en `PROMPT_INVESTIGACION.md`)
- [ ] 🟡 Si ninguna sirve: **proponer una categoría nueva** (ej. "Celdas de batería")
- [ ] 🟡 **Capas de la cadena** donde opera (materia prima, componentes, energía, centro de datos…)
- [ ] 🟢 Código NAICS / industria GICS

## 4️⃣ 📝 Qué hace (textos en ES + EN)

- [ ] 🔴 **Resumen** en 1-2 frases simples
- [ ] 🔴 **Qué vende y a quién**
- [ ] 🟡 **Ventaja difícil de copiar + su riesgo principal**
- [ ] 🟡 **Riesgo geográfico/político**
- [ ] 🟡 **Tendencia reciente con fecha** 🐢 (sin precio ni capitalización)
- [ ] 🟡 **Tecnologías clave** (ej. LFP, sodio-ión, EUV, HBM)
- [ ] 🟢 **Productos principales** y su % de ingresos si lo publica
- [ ] 🟢 Descripción larga (3-6 frases)
- [ ] 🟢 Estrategia declarada
- [ ] 🟡 **Empleados**, en personas (no en miles) 🐢: informe anual
- [ ] 🟡 **Personas clave**: CEO, CFO, fundadores, presidente del directorio, con fecha de inicio 🐢

## 5️⃣ 🏆 Tamaño en su mercado (lo que el chat no pudo contestar)

- [ ] 🔴 **Puesto mundial (1.º, 2.º…) y/o cuota %** en su mercado principal 🐢 (al menos uno de los dos)
  - Dónde buscar: firmas que miden mercados (baterías: SNE Research; chips: TrendForce, Gartner, IDC; minerales:
    USGS; energía: IEA, BNEF) o el informe anual
  - Di con qué se mide (ingresos, unidades, GWh, capacidad), qué región y qué año
- [ ] 🟡 Lo mismo para sus **otros mercados** importantes

## 6️⃣ 🔗 Proveedores y clientes (el corazón del grafo)

Por CADA vínculo:

- [ ] 🔴 **Con quién** (nombre + identificador si lo tienes)
- [ ] 🔴 **Tipo**: provee · fabrica para · da nube · licencia · da energía · despliega · posee · invierte · socio
- [ ] 🔴 **Papel de esta empresa**: ¿es la que provee o la que compra? (Khipus pone la flecha solo)
- [ ] 🔴 **Qué producto**
- [ ] 🔴 **Estado**: activo / terminado / anunciado / planeado / rumor
- [ ] 🔴 **Importancia del 1 al 6** (ver regla abajo)
- [ ] 🔴 **Fuente con frase textual**
- [ ] 🟡 **Fecha de inicio** (y de fin si terminó)
- [ ] 🟡 **¿Proveedor único?** sí/no
- [ ] 🟡 **% de ingresos** que viene de ese cliente: 10-K "clientes principales" / nota de concentración
- [ ] 🟢 % de las compras del cliente que cubre este proveedor
- [ ] 🟢 Valor del contrato y meses que tardaría en reemplazarlo

**Regla del 1 al 6**: 6 = único proveedor, sin reemplazo en menos de 1 año · 5 = más de la mitad del insumo · 4 =
proveedor principal con 1-2 alternativas · 3 = uno de pocos · 2 = uno de varios · 1 = menor.

👉 Meta: **3 a 10 vínculos** por empresa. Rumores y vínculos con confianza menor a 0,5 entran como **propuesta** (tú
los confirmas en 🩺 → Propuestas).

## 7️⃣ 🏛 Dueños y estructura

- [ ] 🟡 **Matriz** directa y última, con % 🐢: GLEIF (relaciones), 10-K "Exhibit 21", 20-F
- [ ] 🟡 **Accionistas principales** (≥5 %, fundadores, Estado) con % 🐢: informe anual, 13D/13G (EE.UU.),
  "disclosure of interests" (Hong Kong)
- [ ] 🟡 **% en manos del Estado** 🐢
- [ ] 🟢 **Filiales importantes** con %

## 8️⃣ 🏭 Plantas, minas, fábricas, centros de datos

Solo sitios físicos importantes:

- [ ] 🟡 **Nombre, tipo, país, ciudad** 🐢
- [ ] 🟡 **Capacidad con unidad** (GWh/año, obleas/mes, MW, toneladas/año) 🐢
- [ ] 🟡 **Estado**: operando / arrancando / en obra / planeada / cerrada, con fecha
- [ ] 🟢 Coordenadas · % si es una empresa conjunta
- Dónde buscar: informe anual, web de la empresa ("nuestras plantas"), comunicados, prensa del sector

## 9️⃣ 💰 Números del negocio 🐢 (cada trimestre o año)

**Si COTIZA**: solo lo que las fuentes automáticas no traen (Khipus ya trae ingresos, márgenes y utilidad):

- [ ] 🟡 **Ingresos por segmento** (por producto o negocio): nota de segmentos del informe anual
- [ ] 🟡 **Ingresos por país o región**: nota geográfica del informe anual
- [ ] 🟡 **Concentración de clientes** (% del mayor cliente; % de los 5 mayores)
- [ ] 🟡 **Cartera de pedidos** (backlog): informe trimestral
- [ ] 🟡 **Capex guiado** para el próximo año: presentación de resultados
- [ ] 🟡 **Capacidad total** (ej. GWh/año)

**Si es PRIVADA**: todo lo que encuentres, con fuente:

- [ ] 🟡 Ingresos, margen, utilidad, capex, I+D por año
- [ ] 🔴 **Rondas de inversión CERRADAS**: fecha, monto, valuación post, líderes, otros inversores. Comunicado oficial o
  prensa seria (no "en conversaciones": eso lo vigila Khipus)

## 🔟 ⚖️ Leyes, sanciones y subsidios

- [ ] 🔴 **¿Está en alguna lista restringida?** (Entity List de EE.UU., OFAC, lista 1260H, sanciones UE/Reino Unido,
  listas de China) con **fecha de entrada**: Consolidated Screening List (trade.gov), Federal Register. Tú das la
  historia con fecha; lo nuevo lo vigilará Khipus cada hora (paso E4.10 del plan)
- [ ] 🟡 **Controles de exportación** que la afectan
- [ ] 🟡 **Subsidios importantes** (CHIPS Act, IRA, fondos estatales) con monto y fecha
- [ ] 🟢 **Juicios** relevantes (antimonopolio, patentes, comercio)

## 1️⃣1️⃣ ⚠️ Riesgos

- [ ] 🟡 **3 a 5 riesgos** en palabras simples (ES + EN): geopolítico, concentración, tecnología, regulatorio,
  financiero, suministro
- [ ] 🟢 Si encaja con un Factor sistémico de Khipus (ej. turbinas de gas, Taiwán), anótalo

## 1️⃣2️⃣ 📅 Línea de tiempo

- [ ] 🟡 **Hechos con fecha**: fundación, salida a bolsa, compras, fusiones, plantas abiertas, contratos grandes,
  sanciones, cambio de CEO. Alimentan el Grafo Temporal (⏱ del mapa)

## 1️⃣3️⃣ 🧪 Innovación y ESG 🐢 (una vez al año)

- [ ] 🟢 Familias de patentes: Google Patents
- [ ] 🟢 Personas en I+D
- [ ] 🟢 Emisiones (alcance 1 y 2), energía, agua y % renovable: informe de sostenibilidad / CDP
- [ ] 🟢 Controversias

## 1️⃣4️⃣ 📡 Para que Khipus la siga en vivo

- [ ] 🔴 **Palabras clave para noticias** (nombre corto, en su idioma, marcas)
- [ ] 🟡 **Página de inversores**
- [ ] 🟡 **Dónde publica sus documentos oficiales**: EDGAR (EE.UU.), HKEXnews (Hong Kong), CNINFO (China), DART
  (Corea), EDINET/TDnet (Japón), MOPS (Taiwán)
- [ ] 🟡 **¿Es privada?** → marcar "vigilar valuación" (Khipus avisa cuando un titular hable de una ronda nueva)
