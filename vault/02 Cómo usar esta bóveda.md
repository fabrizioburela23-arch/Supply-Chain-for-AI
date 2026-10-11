---
tipo: "guia"
tags: ["tipo/guia"]
---

# 02 Cómo usar esta bóveda

Una **bóveda** es simplemente una carpeta de notas que el programa gratuito **Obsidian** sabe mostrar como un mapa. Esta carpeta (`vault`) la genera Claude a partir del código de Khipus, así puedes ver de un vistazo cómo se conecta todo.

## 1. Instalar Obsidian (una sola vez)

1. Entra a **https://obsidian.md** y haz clic en **Download** (Descargar) → elige Windows.
2. Abre el instalador descargado y sigue los pasos (siguiente, siguiente, finalizar). Es gratis.

## 2. Abrir la bóveda

1. Asegúrate de tener el proyecto actualizado en tu PC (GitHub Desktop → **Fetch origin** → **Pull origin**).
2. Abre Obsidian → **Open folder as vault** (Abrir carpeta como bóveda).
3. Busca la carpeta del proyecto (`Supply-Chain-for-AI`), entra y elige la carpeta **`vault`** → **Abrir**.
4. Abre la nota [[00 Mapa de Khipus]]: es la portada.

## 3. Ver el grafo (el mapa de conexiones)

- Haz clic en el ícono de **puntos conectados** en la barra de la izquierda, o pulsa **Ctrl + G**.
- Cada punto es una nota; las líneas son conexiones reales del código. Ya viene **coloreado por capa**:

| Color | Capa |
|---|---|
| azul | [[Capa Interfaz (Khipus OS)]] |
| naranja | [[Capa Chat y agentes]] |
| verde agua | [[Capa Investigación]] |
| amarillo | [[Capa Comité]] |
| rosa | [[Capa Ontología y grafo temporal]] |
| verde lima | [[Capa Cuantitativo (matrices, tensores, riesgo)]] |
| violeta | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] |
| rojo | [[Capa Dinero (carteras, trading, corretaje)]] |
| celeste | [[Capa MCP y API]] |
| morado | [[Capa Voz]] |
| gris oscuro | [[Capa Infraestructura]] |
| marrón | [[Capa Datos del catálogo]] |
| gris | [[Capa Pruebas]] |
| gris claro | [[Capa Documentación]] |
| gris medio | [[Capa Otros]] |
| lila | sesiones de trabajo |
| arena | variables de entorno |

- Si quieres **tus propios colores** (por ejemplo resaltar una nota), agrégalos en el panel **Groups** del grafo con otra búsqueda: se respetan y ganan a los de capa. Los colores de las capas los repone el generador.

- **Filtrar**: en el grafo abre el panel **Filters** (arriba a la derecha) y escribe en la caja de búsqueda:
  - `path:Módulos` → solo el código
  - `-path:Sesiones -path:Pruebas` → esconde sesiones y pruebas
  - `tag:#capa/dinero` → solo una capa (las etiquetas están en cada nota)
- Pasa el mouse sobre un punto para ver su nombre; haz clic para abrir la nota.
- **Grafo local**: con una nota abierta, menú ⋯ → **Open local graph** muestra solo sus vecinos.

## 4. Buscar

- **Ctrl + O**: abrir una nota por nombre (escribe por ejemplo `cockpit` o `khipu_chat`).
- **Ctrl + Shift + F**: buscar una palabra en todas las notas (por ejemplo `PIN` o `/api/trade`).
- Cada nota de código dice: para qué sirve, qué funciones ofrece, de quién depende, quién la usa, qué rutas define o llama, qué variables lee, qué pruebas la cubren y en qué sesiones se mencionó.

## 5. El mapa interactivo (sin Obsidian)

Dentro de `vault/_grafo/` está **`mapa.html`**: ábrelo con doble clic y se abre en el navegador (necesita internet cada vez que lo abres, para cargar la librería de dibujo; sin conexión muestra un aviso). Tiene buscador, filtros por capa y al tocar un punto muestra sus conexiones. Funciona también en el teléfono.

## 6. Cómo se actualiza

**Lo actualiza Claude en cada cambio**: antes de guardar cambios en el código corre `python scripts/build_vault.py`, y una prueba automática avisa si la bóveda quedó vieja. Tú no tienes que hacer nada más que **Pull** en GitHub Desktop para ver la versión nueva.

- No edites las notas generadas: se reescriben solas.
- **Tus notas personales** van en la carpeta **`Mis notas`** (el generador nunca la toca).

## Glosario rápido

- **Módulo**: un archivo de código (por ejemplo `core/ai.py`).
- **Ruta / endpoint**: una dirección del servidor que la pantalla llama (por ejemplo `/api/khipu/chat`).
- **Variable de entorno**: un ajuste secreto o de configuración que vive en Railway (aquí solo aparece el nombre).
- **Prueba**: un chequeo automático que confirma que algo sigue funcionando.
- **Capa**: un grupo de archivos que hacen un mismo tipo de trabajo (interfaz, dinero, voz…).

## Qué hacer ahora

1. Instala Obsidian y abre la carpeta `vault` como bóveda.
2. Abre [[00 Mapa de Khipus]] y luego el grafo con **Ctrl + G**.
3. Mira [[01 Reporte del grafo]]: ahí están las cosas sueltas que conviene revisar.
