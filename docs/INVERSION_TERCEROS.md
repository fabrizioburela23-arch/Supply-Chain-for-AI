# Invertir el dinero de otras personas desde Khipus — memo para Fabrizio

**Fecha:** 30 de septiembre de 2026 · **Preparado por:** Claude (asistente de programación) ·
**Para:** Fabrizio (y para mostrar a Diego si ayuda)

> **IMPORTANTE — esto NO es asesoría legal ni tributaria.** Es una investigación
> ordenada para que llegues preparado a un abogado peruano de mercado de valores.
> Nada de aquí reemplaza su opinión. Antes de mover un solo sol de otra persona
> con dinero real, un abogado tiene que decir "sí" por escrito.

**Cómo se hizo este memo y qué NO se pudo verificar.** Investigué con un
buscador web el 30-sep-2026. La red de este entorno **bloqueó abrir** las páginas
de Alpaca, Interactive Brokers, la SMV, gob.pe, LP Derecho e Infobae, así que lo
que cito viene de los extractos que el buscador muestra de esas páginas oficiales
(con su enlace), no de haber leído el documento completo. Todo lo marcado con
**(verificar)** debe confirmarse abriendo el enlace o preguntando directamente.

---

## 1. Respuesta corta

1. **No uses TU cuenta de Alpaca para invertir el dinero de otros.** Es la opción
   más peligrosa de todas, por tres motivos:
   - **El contrato de Alpaca lo prohíbe en la práctica**: dice que nadie, salvo el
     titular, tiene interés en la cuenta; que no puedes dejar que otra persona opere
     tu cuenta sin una autorización aprobada por Alpaca; y el dinero debe venir de
     cuentas bancarias a tu nombre (los depósitos de terceros solo se revisan "por
     excepción" y con carta de autorización).
   - **En Perú, recibir dinero de terceros de forma habitual e invertirlo** es
     "captación" y está prohibido sin autorización de la SBS (Ley 26702, art. 11).
     En su forma grave es **delito** (Código Penal, art. 246: 3 a 6 años de cárcel).
   - **Administrar la cartera de otros** (decidir tú qué comprar y vender con su
     dinero) en Perú es una actividad de **entidades autorizadas por la SMV**
     (sociedades agentes de bolsa y sociedades administradoras de fondos).
2. **Lo que SÍ puedes hacer la próxima semana, con riesgo bajo:**
   - Demos con **dinero simulado (paper trading)** para todos los interesados.
   - Que cada amigo o familiar abra **SU PROPIA cuenta, a SU nombre, con SU dinero**,
     y que **él apruebe cada orden**. Khipus es la herramienta; tú nunca tocas el dinero.
   - **Sin cobrar nada** (ni comisión ni % de ganancias) hasta que el abogado lo apruebe,
     y con un **acuerdo escrito** sencillo que deje claro todo esto.
3. **Alpaca sigue siendo una buena elección técnica**, pero por el camino correcto:
   cada inversionista con su propia cuenta y Khipus conectado por **OAuth
   ("Alpaca Connect")**, que requiere que Alpaca **apruebe tu app** para operar en
   dinero real de otros. Para crecer en serio: **Broker API** con una estructura
   regulada, o **aliarte con una entidad autorizada por la SMV**.
4. **Alternativa a considerar**: Interactive Brokers tiene cuentas de
   **"asesor no profesional" (Friends & Family)**: cada cliente tiene su propia cuenta
   y tú operas desde un panel. Tiene condiciones fuertes (máx. ~15 clientes, estar
   exento de registro, reglas sobre cobrar) y **igual necesita el visto bueno del
   abogado en Perú**.

---

## 2. Tabla de opciones

| Opción | Cómo funciona | ¿Quién tiene el dinero? | ¿Qué necesitas legalmente? | Tiempo para lanzar | Costo | ¿Sirve la próxima semana? |
|---|---|---|---|---|---|---|
| **A. Tu cuenta Alpaca con el dinero de todos ("pozo")** | Te transfieren a ti y tú inviertes todo junto | Tú (mezclado con lo tuyo) | Choca con el contrato de Alpaca; en Perú riesgo de captación ilegal (art. 11 Ley 26702, art. 246 CP) y de administrar cartera sin autorización | — | — | **NO. Descartar.** |
| **B. Demos con dinero simulado (paper)** | Cada persona ve en Khipus cómo operaría, sin dinero real | Nadie (es simulado) | Nada especial; dejar claro que es simulación | Ya | $0 | **Sí** |
| **C. Cada uno con su cuenta, opera él mismo** | Abre su cuenta (Alpaca, Hapi, etc.) y decide solo, usando Khipus como fuente de información | El bróker, a nombre del inversionista | Bajo; cuidado con dar recomendaciones personalizadas (ver sección 3) | Días (lo que tarde abrir la cuenta) | $0 de comisión en acciones/ETF de EE.UU. en Alpaca para cuentas autodirigidas | **Sí** |
| **D. Cada uno con su cuenta Alpaca + Khipus conectado por OAuth** | El inversionista autoriza a Khipus desde Alpaca; Khipus propone la orden y **él la aprueba** | Alpaca, a nombre del inversionista | Alpaca debe **aprobar tu app** para dinero real de otros (y aprobar por escrito si la app es comercial). Abogado para el rol que tú juegas | Paper: inmediato. Dinero real: depende de la revisión de Alpaca (plazo no publicado) | App: sin costo publicado (verificar) | **Paper sí; dinero real solo cuando Alpaca apruebe** |
| **E. El inversionista te da sus claves API** | Guardas su clave y Khipus opera su cuenta | Alpaca, a nombre del inversionista | El contrato pide que Alpaca apruebe a quien opere una cuenta ajena; OAuth es el camino "oficial". Preguntar a Alpaca | Técnicamente inmediato | $0 | **Solo para paper** (o su propia cuenta) hasta que Alpaca confirme |
| **F. Interactive Brokers "Non-Professional Advisor" / Friends & Family** | Cada cliente tiene cuenta propia; tú, desde una cuenta maestra, pones órdenes y las repartes | IBKR, a nombre de cada cliente | Estar **exento de registro** como asesor; máx. ~15 clientes; reglas de cobro; en Perú, visto bueno del abogado | Semanas (verificar) | Comisiones de IBKR (no verificadas) | **No** (tarda y necesita abogado) |
| **G. Alpaca Broker API (modelo fintech)** | Khipus abre cuentas a nombre de cada cliente dentro de su propia plataforma | Alpaca, a nombre de cada cliente | Empresa, KYC/KYB, aprobación "Full Live" de Alpaca; según el modelo: licencia de bróker local, o asesor registrado (RIA), o programa propio de KYC/antilavado | Meses (estimación mía) | Costo de configuración + depósito de garantía (montos no publicados); algunos planes cobran extra (p. ej. US$1.000/mes por opciones) | **No** — es el camino para escalar |
| **H. Aliarte con una entidad peruana autorizada (SAB o SAF) o sacar licencia propia** | La entidad autorizada tiene la licencia; Khipus pone la tecnología (como tyba con Credicorp Capital SAF) | La entidad autorizada / su custodio | Contrato con la entidad; o autorización SMV propia (capital, personal certificado, etc.) | Meses a más de un año (estimación mía) | Alto | **No** — es el camino "grande" |

---

## 3. Qué dice la ley (en simple)

### Perú — dos reguladores distintos

- **SBS (dinero del público):** la **Ley General del Sistema Financiero (Ley 26702),
  art. 11**, prohíbe a quien no tenga autorización **captar o recibir dinero de
  terceros de forma habitual** (en depósito, préstamo "o cualquier otra forma") y
  **colocarlo en inversiones**. El **Código Penal, art. 246** castiga a quien se
  dedique habitualmente a captar fondos del público sin permiso con **3 a 6 años de
  cárcel** y multa (180 a 365 días-multa). Los jueces lo tratan como delito de
  "peligro abstracto": **no hace falta que nadie pierda dinero** para que exista.
  Las palabras clave son "habitual" y "público": pocos familiares no es lo mismo
  que anunciarlo a desconocidos, pero **esa línea la tiene que trazar un abogado,
  no nosotros**.
- **SMV (valores):** administrar carteras de otros la hacen los **agentes de
  intermediación (sociedades agentes de bolsa)** y las **sociedades administradoras
  de fondos (SAFM/SAFI)**. La **Resolución SMV N.° 011-2026-SMV/01** (publicada en
  El Peruano el **17-ago-2026**, vigente desde el 18-ago) ordenó las reglas de
  **perfil de riesgo, asesoría de inversión y administración de cartera** para esas
  entidades: una recomendación personalizada debe apoyarse en un **perfil de riesgo
  documentado** (situación financiera, objetivos y capacidad de asumir pérdidas).
  En el proyecto de esa norma (nov-2025) se habló de exigir a los administradores
  de cartera una **certificación y al menos 3 años de experiencia** (verificar el
  texto final).
- **Asesores independientes y "fininfluencers":** el 27-sep-2026 la SMV anunció que
  meterá en su **agenda regulatoria 2027** la asesoría independiente (evalúa un
  registro o exámenes obligatorios). Traducción: **hoy la asesoría de una persona
  natural no autorizada es una zona gris, y se va a endurecer**. No construyas el
  negocio sobre ese hueco.
- **Que el dinero esté en un bróker de EE.UU. no te saca de la ley peruana** si tú y
  tus inversionistas están en Perú (verificar con el abogado).

### Estados Unidos

- **Quién es "asesor de inversiones"** (Investment Advisers Act, sección 202(a)(11)):
  quien, **a cambio de una compensación**, se dedica a aconsejar a otros sobre
  valores. Sin cobrar, en principio no encajas en la definición (pero eso **no**
  resuelve el tema en Perú).
- **Si no tienes oficina en EE.UU. ni clientes residentes en EE.UU.**, la guía de
  Interactive Brokers resume que **no necesitas registrarte ante la SEC**, sin
  importar cuánto manejes; la SEC aplica un enfoque territorial (cartas "Unibanco").
- **Si algún día tienes clientes que viven en EE.UU.:** la vieja excepción de
  "menos de 15 clientes" **se eliminó en 2011** (ley Dodd-Frank). Existe la excepción
  de "asesor privado extranjero" (sin oficina en EE.UU., **menos de 15** clientes e
  inversionistas en EE.UU., **menos de US$25 millones** de ellos, y sin
  promocionarte al público de EE.UU.), y los estados no pueden exigirte registro si
  no tienes oficina allí y tuviste **menos de 6 clientes** de ese estado en 12 meses.
  Recomendación: **por ahora, cero clientes residentes en EE.UU.**

### "Discrecional" vs. "cada cliente aprueba cada orden"

| Modo | Qué significa | Riesgo regulatorio |
|---|---|---|
| **Discrecional** | Tú decides y ejecutas sin preguntar | **El más alto**: es administración de cartera (en Perú, para entidades autorizadas) |
| **No discrecional** | Khipus propone, **el dueño de la cuenta aprueba cada orden** | Menor, pero si la propuesta es personalizada puede ser "asesoría" |
| **Solo herramienta** | Khipus muestra datos e investigación; el inversionista decide solo | **El más bajo** |

Khipus debe funcionar por defecto en los dos últimos modos.

---

## 4. Camino recomendado

### Para la PRÓXIMA SEMANA (legal y de bajo riesgo)

**Las 8 reglas:**

1. **Ni un sol pasa por tus manos.** Nada de transferencias, Yape o Plin a ti para "invertir".
2. **Cada persona, su propia cuenta, a su nombre** (Alpaca si su país está aceptado; si no, otro bróker; Hapi es un ejemplo, no una recomendación).
3. **Cada orden la aprueba el dueño de la cuenta** (un clic o un "sí"). Nada automático.
4. **No cobras nada** — ni comisión ni % de ganancias — hasta que el abogado lo apruebe.
5. **No prometes rentabilidad.** Las "ganancias garantizadas" son la primera señal de fraude que busca la SMV.
6. **Documento firmado** por cada persona: que Khipus es una herramienta, que tú no guardas su dinero, que puede perder todo lo invertido, y su perfil de riesgo básico.
7. **Empieza chico**: pocas personas cercanas y montos que puedan perder sin problema.
8. **Primero 1–2 semanas en paper** (simulado) antes de dinero real, y **sin anunciarlo en redes sociales**.

**Semáforo:**
- **Verde (ya):** demos en paper; cada uno opera su cuenta con información de Khipus; tú no cobras.
- **Amarillo (solo con OK del abogado):** darle a alguien recomendaciones personalizadas; que Khipus envíe órdenes a cuentas de otros en dinero real vía OAuth; cobrar cualquier cosa.
- **Rojo (no hacer):** recibir dinero en tu cuenta; juntar el dinero de varios; operar sin que el dueño apruebe; prometer ganancias; captar gente por redes; clientes que viven en EE.UU.

### Para crecer (de 1 a 12 meses)

1. **Mes 1:** abogado + consultas a Alpaca (sección 5). Registrar Khipus como app de
   "Alpaca Connect" y pedir la revisión para dinero real. Todos en paper.
2. **Meses 1–3:** con la app aprobada por Alpaca y el OK del abogado: cuentas propias
   conectadas por OAuth, modo **no discrecional**, perfil de riesgo documentado,
   términos de uso y política de privacidad.
3. **Meses 3–12:** una de dos rutas reguladas:
   - **Aliarte** con una sociedad agente de bolsa o una SAF autorizada por la SMV
     (ellos ponen la licencia; Khipus pone la tecnología). Precedente: **tyba** operaba en
     Perú y Colombia con la Broker API de Alpaca (según Alpaca, a fines de 2024), y sus
     fondos mutuos en Perú los administra **Credicorp Capital S.A. SAF**.
   - **Broker API de Alpaca** con una empresa y la estructura que el abogado apruebe
     (o licencia propia en el futuro).

**Ojo:** crear una empresa y abrir una "cuenta de empresa" **no** resuelve el problema.
Si la empresa recibe dinero de inversionistas para invertirlo junto, eso es un
**fondo**, y en Perú los fondos los administran SAF autorizadas. (Además, la cuenta de
empresa de Alpaca está en beta, pide un mínimo de US$30.000 y está pensada para
invertir el dinero propio de la empresa, no para construir apps.)

---

## 5. Próximos pasos concretos

### a) Llamar a un abogado peruano de mercado de valores (esta semana)

Busca un estudio con práctica de **mercado de capitales / regulación financiera**
(por ejemplo Rodrigo, Elías & Medrano; Miranda & Amado; Payet, Rey, Cauvi, Pérez;
Estudio Echecopar; Cuatrecasas Perú — son ejemplos conocidos, **no** una recomendación).

**Preguntas para el abogado:**
1. Si 5–10 amigos/familiares abren **su propia cuenta** en un bróker de EE.UU. y
   **aprueban cada orden** que les propone mi app, ¿estoy haciendo algo que requiera
   autorización de la SMV o la SBS?
2. ¿Dónde está la línea entre "herramienta de información" y "asesoría de inversión"
   tras la **Res. SMV 011-2026-SMV/01**? ¿Qué cambia con la agenda 2027 para asesores
   independientes?
3. ¿Puedo cobrar algo (suscripción a la app, comisión, % de ganancias)? ¿Qué forma es la más segura?
4. ¿Qué **no** debo hacer nunca para no caer en el art. 11 de la Ley 26702 ni en el
   art. 246 del Código Penal?
5. ¿Qué debe decir el **contrato/declaración** que firme cada inversionista?
6. ¿Me conviene más aliarme con una SAB/SAF o pedir una autorización propia? ¿Costos y plazos?
7. Si uso Interactive Brokers "Friends & Family", ¿estoy exento de registro en Perú?
8. Impuestos: ¿cómo declara cada inversionista sus ganancias en el extranjero ante
   SUNAT, y qué tengo que declarar yo? (o que te derive a un contador)

### b) Escribirle a Alpaca (support@alpaca.markets; para Broker API, a su equipo comercial)

Borrador para copiar y pegar:

> Hello Alpaca team. I am based in Peru and I am building Khipus Finance AI, an
> investment research app. (1) Can Peruvian residents open individual live Trading
> API accounts? (2) I want each of my users to keep **their own** Alpaca account
> and connect my app through OAuth (Alpaca Connect) so the app can propose orders
> that **the user approves one by one**. What does the review for live trading on
> behalf of other users require, and how long does it take? My app may be
> commercial in the future — what do you need from me for written approval?
> (3) Is it allowed for a user to share their API keys with a third-party app, or
> is OAuth the only permitted way? (4) For the Broker API, as a Peruvian company
> without a broker-dealer license, which setup could I use (fully disclosed,
> omnibus, Alpaca KYC), and what are the setup cost and clearing deposit?
> Thank you.

### c) Interactive Brokers (opcional)

Preguntarles si un **residente en Perú**, sin clientes en EE.UU. y sin cobrar, puede
abrir una cuenta **Non-Professional Advisor / Friends & Family**, y qué documentos piden.

### d) Para la reunión con Diego (mañana)

- "No vamos a juntar el dinero de nadie: cada inversionista tiene su propia cuenta a
  su nombre, y aprueba cada operación."
- "Empezamos en simulado; dinero real solo con el OK del abogado y de Alpaca."
- "El camino para escalar es regulado: app aprobada por Alpaca y/o una alianza con
  una entidad autorizada por la SMV."

---

## 6. Cómo se está construyendo Khipus para hacer esto de forma segura

Esto es lo que se está construyendo en la app (**en construcción esta semana**; el
estado final quedará en `docs/ESTADO.md`):

- **Cada cliente con su propia cuenta**, nunca una cuenta común: conexión por
  **OAuth de Alpaca** (el camino recomendado) o, solo para paper/pruebas, claves por
  cliente guardadas **únicamente en el servidor** y nunca en el navegador.
- **Simulado por defecto.** Pasar a dinero real exige una activación explícita, y la
  pantalla siempre muestra si es **SIMULADO** o **DINERO REAL**.
- **Aprobación humana de cada orden:** primero un resumen, luego un "sí" explícito
  (clic o voz), y solo entonces se envía. Las IAs y agentes que se conecten por el
  **servidor MCP** pueden leer la ontología y **proponer** órdenes, pero **no
  ejecutarlas** sin esa aprobación humana.
- **Límites**: monto máximo por orden y por día, y lista de activos permitidos.
- **Botón de apagado** ("kill switch") que detiene todo el envío de órdenes.
- **Registro de auditoría**: quién propuso, quién aprobó, qué se envió, cuándo y qué
  respondió el bróker.
- **PIN de trading** (`X-Trade-Pin`) en todas las rutas que mueven dinero.
- **Lo que la app NO hace:** no guarda dinero, no junta cuentas, no opera sola, no
  promete rentabilidad.

---

## 7. Fuentes (consultadas el 30-sep-2026)

**Alpaca**
- Contrato de cliente (nadie más tiene interés en la cuenta; autorización de trading
  aprobada por Alpaca; cuenta autodirigida; acceso de terceros bajo riesgo del
  cliente): https://files.alpaca.markets/disclosures/library/AcctAppMarginAndCustAgmt.pdf
  (versión vista vía buscador; no se pudo abrir el PDF completo)
- Comisiones de cuentas individuales (tarifario):
  https://files.alpaca.markets/disclosures/library/BrokFeeSched.pdf
- Depósitos: la cuenta bancaria debe estar a tu nombre; transferencias de terceros
  solo por excepción y con carta de autorización:
  https://alpaca.markets/support/wire-deposit · https://docs.alpaca.markets/us/docs/funding-accounts
- OAuth / Alpaca Connect (alcances `account:write`, `trading`, `data`; la app necesita
  aprobación para dinero real de otros usuarios; apps comerciales requieren aprobación
  escrita; el desarrollador puede operar su propia cuenta real sin aprobación):
  https://docs.alpaca.markets/us/docs/using-oauth2-and-trading-api ·
  https://docs.alpaca.markets/us/docs/registering-your-app ·
  https://docs.alpaca.markets/us/docs/about-connect-api ·
  https://alpaca.markets/support/oauth-applications ·
  https://github.com/alpacahq/alpaca-docs/blob/master/content/api-references/oauth-api/_index.md
  (repositorio archivado en abril de 2025)
- Países (dice atender 195+ países; **no se pudo confirmar si Perú está incluido**):
  https://alpaca.markets/support/countries-alpaca-is-available ·
  https://alpaca.markets/learn/live-trading-account-non-us
- Broker API (onboarding, KYC/KYB, "Full Live"; modelos fully-disclosed/omnibus/RIA;
  costos): https://alpaca.markets/broker ·
  https://alpaca.markets/broker-resources/guide/getting-started-with-broker-api-guide-to-onboarding-process ·
  https://docs.alpaca.markets/us/docs/getting-started-with-broker-api ·
  https://docs.alpaca.markets/us/docs/omnisub · https://alpaca.markets/support/support-for-ria ·
  cuentas de empresa para socios de Broker API (18-ago-2026):
  https://alpaca.markets/blog/alpaca-launches-business-accounts-for-broker-partners/
- Cuenta de empresa (beta, mínimo US$30.000): https://alpaca.markets/support/non-us-business
- Caso tyba (Colombia y Perú, Broker API; 10.000+ clientes y US$7 M en activos al
  4T-2024): https://alpaca.markets/blog/tyba-creating-investment-access-in-latin-america/ ·
  fondos de tyba en Perú administrados por Credicorp Capital S.A. SAF:
  https://tyba.pe/preguntas-frecuentes/que-es-un-fondo-mutuo/

**Otras plataformas**
- Hapi (bróker en EE.UU. para latinos; custodia Apex Clearing): https://hapi.trade/es/blog/que-es-hapi
- Interactive Brokers, asesor no profesional / Friends & Family (exento de registro;
  generalmente 15 clientes o menos; cuenta maestra para asignar órdenes y cobrar):
  https://www.interactivebrokers.com/en/accounts/non-professional-advisor.php ·
  https://www.interactivebrokers.com/en/accounts/family-advisor.php ·
  https://ibkrcampus.com/campus/glossary-terms/friends-and-family-group-account/ ·
  registro de asesores (no-EE.UU. sin oficina ni clientes en EE.UU. no se registran
  ante la SEC): https://www.interactivebrokers.com/en/accounts/advisor-registration.php ·
  países aceptados (**Perú no confirmado**):
  https://www.interactivebrokers.com/en/accounts/open-account-country-list.php

**Perú**
- Ley 26702, art. 11 (texto concordado SBS):
  https://www.sbs.gob.pe/Portals/0/jer/LEY_GENERAL_SISTEMA_FINANCIERO/2023/Ley%20N%C2%B0%2026702%20(01012023).pdf
- Código Penal, art. 246 (pena 3–6 años): https://lpderecho.pe/articulo-246-codigo-penal-instituciones-financieras-ilegales/ ·
  Casación 923-2020: https://juris.pe/blog/delito-instituciones-financieras-ilegales-articulo-246-codigo-penal-casacion-923-2020-lambayeque/
- Res. SMV N.° 011-2026-SMV/01 (El Peruano, 17-ago-2026):
  https://www.gob.pe/institucion/smv/normas-legales/8492182-011-2026-smv-01 ·
  https://www.gob.pe/institucion/smv/noticias/1434034-smv-modifica-los-reglamentos-de-agentes-de-intermediacion-de-fondos-mutuos-y-de-fondos-de-inversion ·
  https://lpderecho.pe/smv-modifica-reglamentos-de-agentes-de-intermediacion-de-fondos-mutuos-de-inversion-en-valores-y-de-fondos-de-inversion-res-smv-011-2026-smv-01/
- Proyecto SMV sobre administración de cartera (nov-2025):
  https://www.infobae.com/peru/2025/11/10/smv-permitira-que-sociedades-administradoras-de-fondos-gestionen-carteras-igual-que-agentes-de-intermediacion/
- SMV y asesoría independiente / fininfluencers, agenda 2027 (27-sep-2026):
  https://www.infobae.com/peru/2026/09/27/a-ti-tambien-te-quisieron-dar-asesoria-financiera-por-tiktok-o-instagram-smv-obligara-a-fininfluencers-a-tomar-examenes/
- Ley del Mercado de Valores: https://www.smv.gob.pe/uploads/PeruLeyMercadoValores_002.pdf ·
  sociedades agentes de bolsa (SMV): https://www.smv.gob.pe/uploads/SociedadesAgentesdeBolsas.pdf

**Estados Unidos**
- Definición de asesor de inversiones, 15 U.S.C. § 80b-2(a)(11):
  https://www.law.cornell.edu/uscode/text/15/80b-2
- Fin de la excepción de "menos de 15 clientes" (SEC, 2011):
  https://www.sec.gov/newsroom/press-releases/2011-133-sec-adopts-dodd-frank-act-amendments-investment-advisers-act
- Asesor privado extranjero (menos de 15 clientes en EE.UU., menos de US$25 M):
  https://www.kelleydrye.com/viewpoints/client-advisories/foreign-private-advisers-under-dodd-frank
- Mínimo estatal (menos de 6 clientes por estado, sección 222):
  https://katten.com/Summary-and-Analysis-of-Dodd-Frank-Rules-for-Investment-Advisers
- Enfoque territorial de la SEC (cartas Unibanco):
  https://www.ropesgray.com/en/insights/alerts/2017/03/secs-information-update-for-advisers-relying-on-the-unibanco-no-action-letters

**No verificado / pendiente:** si Alpaca e IBKR aceptan residentes en Perú; cuánto
tarda Alpaca en aprobar una app OAuth para dinero real; los costos exactos de la
Broker API; las comisiones de IBKR para asesores; el texto final completo de la
Res. SMV 011-2026-SMV/01 (requisitos de certificación y experiencia). Los plazos
marcados como "estimación mía" no vienen de ninguna fuente.
