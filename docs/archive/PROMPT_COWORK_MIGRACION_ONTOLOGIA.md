# Prompt para Claude Cowork — correr la migración de la Ontología

Copia TODO lo que está dentro del bloque de abajo y pégalo en Claude Cowork.

---

> Estoy trabajando en el repo **Supply-Chain-for-AI** (Khipus AI Finance
> Intelligence), una app Flask desplegada en Railway. Otro asistente (Claude
> Code) acaba de construir la **Fase 1 de una ontología** (Postgres,
> registro de eventos bitemporal) y ya está desplegada y funcionando en
> producción — el panel de diagnóstico 🩺 de la app muestra "Ontología:
> OPERATIVO" (Postgres conectado). Todo el código ya existe en el repo, en
> la carpeta `ontology/` y en `scripts/migrate_v0_to_ontology.py`.
>
> **Lo único que falta es UN PASO: correr la migración una sola vez** para
> cargar los datos (463 empresas + 32 objetos de ontología + ~1163
> relaciones + 105 hechos temporales) a esa base Postgres, que ahora mismo
> está conectada pero vacía.
>
> **NO edites código.** Esto es solo ejecutar un script ya construido y
> probado. Si algo falla, dime el error exacto en vez de intentar arreglarlo
> tú mismo modificando archivos — prefiero que me consultes primero.
>
> Necesito que:
>
> 1. Clones o uses tu copia de trabajo del repo `Supply-Chain-for-AI` (rama
>    `main`, ya tiene todo lo necesario).
> 2. Me preguntes por el valor de `DATABASE_URL` — está en Railway → el
>    servicio de **Postgres** (no el principal) → pestaña **Variables** →
>    copio el valor de `DATABASE_URL` y te lo paso.
> 3. Instales las dependencias necesarias:
>    ```
>    pip install sqlalchemy psycopg2-binary
>    ```
>    (o `pip install -r requirements.txt` si prefieres, ya las incluye)
> 4. Corras exactamente este comando, con la variable de entorno seteada:
>    ```
>    export DATABASE_URL="<lo que te pase>"
>    python scripts/migrate_v0_to_ontology.py --reset
>    ```
> 5. Me muestres la salida completa del comando. Debería terminar con algo
>    parecido a:
>    ```
>    ✅ 495 objetos creados
>    ✅ 1163 links base creados (0 saltados)
>    ✅ 86 hechos temporales con fecha real creados (0 saltados)
>    🎉 Migración completa
>    ```
> 6. Si el número de "saltados" es mayor que 0 en cualquier paso, o si el
>    script lanza un error, muéstrame el mensaje completo — no lo intentes
>    arreglar solo, pregúntame primero.
> 7. Al final, verifica que funcionó abriendo en el navegador (o con curl)
>    la URL: `https://<mi-app>.railway.app/api/ontology/status` — debería
>    devolver JSON con `"configured": true, "ok": true` y contadores de
>    objects/links/events mayores a 0.
>
> **Importante:** este script (`--reset`) borra y recrea las tablas de la
> ontología antes de cargar los datos — es seguro correrlo ahora porque la
> base está recién creada y vacía, pero avísame antes si detectas que ya
> tiene datos (no debería, pero confírmalo).

---

## Notas para ti (no es parte del prompt)

- Este paso es **de una sola vez**. Si en el futuro necesitas recargar los
  datos (por ejemplo si actualizas el catálogo de empresas), se vuelve a
  correr el mismo comando.
- Cuando Cowork te confirme que terminó, vuelve a `🩺 diagnóstico` en tu app
  y la fila "Ontología" debería mostrar los números reales (495 objetos,
  ~1249 vínculos, ~1744 eventos) en vez de solo "conectado".
