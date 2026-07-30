# Estado del proyecto

Última actualización: 2026-07-30. **Fase 5 terminada.** Siguiente: Fase 6 —
agente orquestador con function calling, ingesta y RAG.

Este documento existe para retomar el trabajo sin releer toda la historia.
Léalo junto con `CLAUDE.md` (instrucciones del proyecto) y `docs/adr/`
(decisiones tomadas durante la implementación).

---

## Resumen en una línea

El bot recibe mensajes escritos y hablados, aplica la compuerta de
consentimiento, transcribe las notas de voz, extrae los datos de la huerta y
los guarda tras confirmación. **La Fase 5 está terminada: CU1, CU3 y CU5
funcionando.** Falta el agente con function calling y el RAG (CU2 y CU4),
que son la Fase 6.

---

## Qué está hecho y verificado

| Pieza | Archivo | Estado |
|---|---|---|
| Webhook con verificación de firma HMAC | `app/api/webhook.py`, `app/core/signature.py` | Funcionando |
| Despachador asíncrono | `app/services/dispatcher.py` | Funcionando |
| Idempotencia con dos estados | `db/004_idempotencia.sql`, `repositorio.py` | En Supabase, probada |
| Esquema de base de datos | `db/*.sql` | Aplicado en Supabase |
| Identidad (HMAC) y cifrado (AES-GCM) | `app/core/identidad.py` | Probado |
| Conexión a PostgreSQL | `app/core/basedatos.py` | Pool con `asyncpg` |
| Repositorio de datos | `app/services/repositorio.py` | Solo tabla `usuario` |
| Cliente de WhatsApp | `app/services/whatsapp.py` | Texto y botones |
| Compuerta de consentimiento (CU1) | `app/services/consentimiento.py` | **Probado de punta a punta** |
| Textos fijos (CU5) | `app/textos.py` | Sin pasar por el modelo |
| Cliente de Gemini | `app/core/gemini.py` | Creado; sin llamada real todavía |
| Vectorización | `app/services/embeddings.py` | Probado contra la API real |
| Descarga de multimedia | `app/services/media.py` | Probado en producción |
| Transcripción | `app/services/normalizacion.py` | Probado en producción |
| Extracción de entidades | `app/services/extraccion.py` | Conectada al flujo |
| Registro de la huerta (CU3) | `app/services/registro.py`, `db/005_*.sql` | Probado de punta a punta |
| Prompts versionados | `app/agent/prompts/`, `plantillas.py` | Solo `extraccion_v1.md` |

Flujo comprobado en un celular real: `"Hola"` → bienvenida + botones
[Acepto]/[No acepto] → al aceptar, se crea la fila y se confirma. En la base
quedó el `telefono_hash`, nunca el número.

## Infraestructura operativa

- **Railway:** desplegado en `https://web-production-1390a.up.railway.app`.
  Arranque por `Procfile`, comprobación de salud en `/health` (que también
  verifica Supabase). Plan Hobby, USD 5/mes.
- **Supabase:** PostgreSQL 17.6, esquema aplicado, RLS activo sin políticas.
  Conexión por **session pooler, puerto 5432** — la directa es solo IPv6 y el
  equipo de desarrollo no tiene IPv6; el puerto 6543 rompe `asyncpg`.
- **Meta:** app `Chatbot Huertas Urbanas` (id `4332318797098432`), número de
  prueba `+1 555-136-8057`. Webhook registrado, app suscrita al WABA y campo
  `messages` suscrito. **Los tres pasos son independientes**; que el webhook
  verifique no implica que lleguen mensajes.
- **GitHub:** repositorio **público**. Último commit `237d4d9`. Árbol limpio.

## Lo que NO funciona todavía (esperado)

- **Una consulta agroecológica no recibe respuesta** ("¿qué le echo al tomate
  para los bichos?"). Es el CU2 y necesita el RAG de la Fase 6. El
  despachador lo anota en bitácora y calla.
- **El CU4 no existe**: no se puede preguntar qué siembran otras huertas.
- **No hay agente.** La intención se resuelve de forma provisional: saludo y
  ayuda por palabras clave, y cualquier otro mensaje se trata como posible
  registro de huerta. En la Fase 6 esa decisión pasa al function calling.
  Consecuencia visible hoy: un mensaje que mezcle consulta y dato —"a mi
  tomate le salieron bichos"— puede ofrecer guardar el tomate en vez de
  responder la duda.
- **El fragmento comunitario no se genera** al confirmar un registro
  (ADR-0004). Hasta que se haga, en la Fase 6, una huerta guardada no
  aparecerá en el CU4. Hay un TODO en `guardar_huerta`.
- No se guarda el historial de conversación en `mensaje`: es la memoria del
  agente, Fase 6.

---

## Siguientes pasos, en orden

1. ~~**ADR pendiente.**~~ Hecho:
   [ADR-0006](adr/0006-saludo-y-ayuda-sin-modelo.md) documenta por qué la
   detección de saludo/ayuda va por palabras clave y no por el modelo.
2. **Cliente de Gemini y spike de embeddings.** Hecho y **ejecutado contra
   la API real** el 29/07/2026 (`python -m scripts.spike_embeddings`):
   - `output_dimensionality` existe y admite 768; `task_type` también.
   - El vector truncado a 768 llega **sin normalizar**: norma medida
     **0.594**, no 1. Con `gemini-embedding-001` hay que normalizarlo a
     mano y ya lo hace `embeddings.py`. Matiz: para el operador `<=>` de
     pgvector la norma es indiferente, así que **no afecta al coseno**;
     importa para poder usar `<#>` y para no mezclar vectores de normas
     distintas en la columna.
   - **El umbral de 0.7 de la Fase 4 queda respaldado** por la primera
     evidencia. Con la consulta "a mi mata de tomate le salieron unos
     bichitos verdes, qué le echo": documento pertinente **0.797**, mismo
     dominio pero otro tema (compost) **0.607**, ajeno al dominio
     **0.536**. El umbral cae casi centrado en el hueco, con ~0.09 de
     margen a cada lado. **No hay que cambiarlo por ahora.**
   - **La colección comunitaria también supera 0.7**, contra lo que se
     temía: se comprobó que una pregunta en prosa contra un fragmento en
     forma de lista generada (ADR-0004) no pierde similitud. Tres consultas
     del CU4 contra tres fragmentos imitando la forma real dieron mejores
     coincidencias entre 0.731 y 0.795. **No hace falta un umbral propio.**
   - **Pero el umbral casi no discrimina en la colección comunitaria.**
     Todos los valores caen entre 0.66 y 0.80, porque los fragmentos
     comparten la plantilla ("Huerta X. Barrio Y. Cultivos: ...") y ese
     texto fijo infla la similitud de todos por igual. Consecuencias:
     - Quien limita de verdad el CU4 es **top-k=4**, no el umbral. Con 5–7
       huertas en la Fase 8, casi cualquier pregunta recupera medio corpus.
     - "Qué cultivos hay en el barrio Holanda" recuperó los tres barrios
       (0.795 / 0.741 / 0.738). Es correcto según el ADR-0001 —el barrio no
       filtra— pero confirma que **la etiqueta de atribución
       `[COMUNITARIO – huerta, barrio]` es imprescindible**, no decorativa:
       sin ella la usuaria creería que todo eso se siembra en Holanda.
     - Al redactar la tesis, no atribuir al RAG comunitario una precisión de
       filtrado que no tiene. Recupera de forma amplia; lo que aporta rigor
       es la atribución.
   - Se **mantiene** `gemini-embedding-001` y no se pasa a
     `gemini-embedding-2` (GA el 22/04/2026): el nuevo no admite `task_type`
     y devuelve un solo embedding agregado para varias entradas. Retiro de
     `001` previsto para el 14/05/2028, muy posterior a la Fase 8. Recogido
     en [ADR-0007](adr/0007-modelo-de-embeddings-fijo-en-codigo.md).
   - **`gemini-2.5-flash` se retira el 16/10/2026**, probablemente antes de
     la Fase 8. El modelo generativo por defecto es `gemini-3.6-flash`, de
     la serie 3.
3. **Servicio de normalización.** Hecho y **probado en producción** el
   30/07/2026 con una nota de voz real desde un celular: descarga, mime
   `audio/ogg`, 15 515 bytes, transcripción de 69 caracteres y entrega al
   punto donde espera el agente. El camino completo funciona.
   - **Riesgo del códec Opus: cerrado.** Gemini **aceptó** el audio de
     WhatsApp tal cual, sin conversión. No hace falta ffmpeg ni ninguna
     dependencia del sistema en Railway. Era el riesgo abierto del paso 3.
   - El `mime_type` llegó ya normalizado a `audio/ogg`: quitar el
     `; codecs=opus` funcionó.
   - El `User-Agent` de la descarga funcionó: `lookaside.fbsbx.com`
     respondió 200.
   - **Tiempos medidos, que respaldan el ADR-0005:** el webhook devolvió
     200 de inmediato y el pipeline tardó **4,3 s** (1,7 s de descarga,
     2,5 s de Gemini). Confirma que procesar dentro de la petición
     provocaría reintentos de Meta. Es evidencia citable en la tesis, y sin
     agente todavía: con function calling y RAG será bastante más.
   - Para leer la transcripción literal, `python -m
     scripts.spike_transcripcion <media_id>` (el `media_id` dura 7 días).
   - La descarga son **dos peticiones y las dos llevan el token**. La URL
     que devuelve la primera caduca a los **5 minutos**; el `media_id`, a
     los 7 días.
   - El servidor de descarga de Meta **exige `User-Agent`**. Sin él
     responde 400. No está en la documentación oficial.
   - **Riesgo abierto:** WhatsApp manda `audio/ogg; codecs=opus` y la
     documentación de Gemini enumera `audio/ogg` como "OGG Vorbis". Son
     códecs distintos. Si Gemini lo rechaza hay que convertir con ffmpeg,
     lo que añade una dependencia del sistema al despliegue de Railway.
     **Es lo que el spike resuelve.**
   - La transcripción va **después** de la compuerta, no antes (ADR-0006).
     Comprobado con espías: el audio de quien no ha autorizado no llega a
     Gemini, el de quien sí se transcribe una sola vez, y si la
     transcripción falla se le avisa.
   - Temperatura 0.0 para transcribir. **CLAUDE.md §8 no recoge este
     parámetro** porque la tabla es anterior a la entrada por voz; hay que
     añadirlo al documento de grado.
4. **Extracción de entidades.** Hecha y **probada contra la base y la API
   reales** el 30/07/2026 (`python -m scripts.spike_extraccion`, que no
   escribe nada).
   - `app/agent/prompts/extraccion_v1.md`, cargado por
     `app/agent/plantillas.py`. **Al editar un prompt, cuidado con las
     llaves literales:** los huecos se rellenan con `str.format` y una `{`
     sin duplicar rompe la carga.
   - Salida estructurada con `response_schema`, temperatura 0.1 fija.
   - El enum de barrios se genera con `listar_barrios()` leyendo la tabla
     (ADR-0002). El esquema obliga al modelo a devolver un código válido,
     así que no hace falta validar contra el catálogo después.
   - **La fecha de hoy se inyecta en el prompt.** Sin ella el modelo no
     puede resolver "en marzo" ni "hace dos meses", y acertaría el año por
     casualidad. Ninguna fase lo contemplaba.
   - Los siete casos de prueba salieron bien, incluidos los tres que
     importan: una pregunta ("¿al tomate qué le echo?") **no** produce
     cultivos; "cebolla larga" y "papa criolla" se conservan literales sin
     recortarse a "cebolla" y "papa"; y "los tres sectores" dictado por voz
     cae en el código `los_3_sectores`.
   - **Nada se persiste**: la función solo devuelve. El guardado es del
     paso 5, tras la confirmación (CLAUDE.md §4.7).
   - Punto menor para calibrar en la Fase 7: "sembré en abril **me
     parece**" se marca como fecha precisa, porque el prompt manda mirar si
     nombra un mes. El titubeo de la usuaria podría justificar marcarla
     imprecisa. Es de bajo riesgo, porque la confirmación del CU3 le
     muestra la fecha de todos modos.
5. **Flujo de registro de huerta (CU3).** Hecho y **probado de punta a punta**
   el 30/07/2026 contra la base y la API reales, con una usuaria temporal que
   se borró después. **Con esto cierra la Fase 5.**
   `app/services/registro.py`, `db/005_registro_pendiente.sql`, decisiones en
   [ADR-0008](adr/0008-borrador-de-registro-y-una-huerta-por-usuaria.md).
   - **El borrador espera en la base**, no en memoria: un redeploy la dejaría
     pulsando "Sí, guardar" sin efecto. Caduca a las 24 horas.
   - Matiz que hay que enunciar con precisión en la tesis: **el dato extraído
     se persiste antes de la confirmación; el registro de la huerta, no.** El
     borrador no se comparte, no entra al RAG y caduca.
   - **El resumen lo compone el código, no el modelo.** Ella confirma lo que
     se va a guardar, así que el texto tiene que reflejarlo con exactitud.
   - **Se reutiliza la huerta que ya tenga** en lugar de crear otra.
   - **Los cultivos se acumulan al fusionar**, que es lo que permite "sembré
     lechuga" + "en El Regalo" en dos mensajes sin perder la lechuga.
   - **Sin barrio no hay botones**: la columna es obligatoria, así que se
     pregunta en lenguaje natural y el borrador espera. Sin menú de barrios.
   - La marca de imprecisión se le muestra: "marzo de 2026 (más o menos)".
   - Probado: resumen sin guardar nada, confirmación que persiste, falta de
     barrio, fusión, descarte, y botón pulsado sobre un borrador ya caducado.
6. ~~**Antes del punto 5**, resolver los puntos abiertos del ADR-0005.~~
   **Hecho el 30/07/2026: los cuatro cerrados.**
   [ADR-0005](adr/0005-procesamiento-asincrono-e-idempotencia.md) ya no
   tiene puntos abiertos.
   - Tabla `idempotencia_webhook` (`db/004_idempotencia.sql`), **aplicada en
     Supabase**. Sin `usuario_id` y con el HMAC del `wamid`, no el `wamid`:
     se escribe antes de la compuerta, así que no puede llevar dato
     personal.
   - Dos estados. `procesado` se marca **solo al terminar bien**; si el
     trabajo falla, la fila se queda en `recibido` y el reintento de Meta lo
     recupera al vencer el plazo de 5 minutos.
   - El reclamo es **una sola sentencia** `INSERT ... ON CONFLICT DO UPDATE
     ... WHERE`. Separar consulta y escritura abriría una carrera entre dos
     entregas del mismo mensaje.
   - Descarte **por antigüedad** (7 días), nunca en bloque. Limpieza al
     arrancar.
   - Los cuatro casos probados contra la base real: mensaje nuevo, duplicado
     real, entrega mientras se procesa, e intento anterior muerto (que **se
     vuelve a tomar**). Más la limpieza y el diagnóstico de atascados.
   - **Límite que queda, y hay que declararlo así en la tesis:** la garantía
     es *al menos una vez*, no exactamente una. Si el proceso muere entre el
     final del trabajo y el marcado, el mensaje se reprocesa y la usuaria
     recibe una respuesta repetida. Es preferible a perder un registro de
     huerta. Y si Meta agota sus reintentos el mensaje se pierde, pero **ya
     no en silencio**: queda la fila en `recibido` y el servicio avisa al
     arrancar.

Después de la Fase 5 viene la **Fase 6**: agente orquestador con function
calling, ingesta de fuentes oficiales y RAG (CU2 y CU4).

**Aviso para la Fase 6, visto en la bitácora:** el SDK registra `AFC is
enabled with max remote calls: 10`. AFC es *automatic function calling*, y
viene activado por defecto: en cuanto el agente tenga herramientas, el SDK
**ejecutará las funciones por su cuenta** en un bucle. Eso choca de frente
con la decisión de confirmar antes de guardar (CLAUDE.md §4.7): el modelo
llamaría a `registrar_huerta` sin pasar por los botones de confirmación.
Habrá que desactivarlo (`AutomaticFunctionCallingConfig(disable=True)`) y
orquestar las llamadas a mano. Hoy es inocuo porque la transcripción no
declara herramientas.

---

## El `wamid` lleva el teléfono dentro — corregido el 30/07/2026

**Hallazgo.** El `wamid` contiene el número de teléfono del remitente, en
ASCII, recuperable con un solo `base64 -d`. Comprobado sobre un `wamid` real
de la bitácora: dentro aparecen los 12 dígitos del celular y, aparte, el
identificador hexadecimal del mensaje. Vale igual para el `wamid` de los
mensajes que envía el bot, que lleva el número del destinatario.

Durante unas horas la bitácora de Railway guardó el número de quien
escribiera. **Los registros anteriores al 30/07/2026 siguen conteniéndolo**;
si Railway permite purgarlos, conviene hacerlo.

**Corregido así:**

- `huella_wamid` (HMAC-SHA256 con el pepper) para almacenar y comparar.
- `referencia_wamid`, prefijo de 16 caracteres de esa huella, para la
  bitácora. Es prefijo de la huella y **no** un recorte del `wamid`:
  recortar el valor original seguiría exponiendo el número, que va al
  principio. Como es prefijo, una línea de bitácora se podrá cruzar con la
  fila de la tabla de idempotencia.
- La idempotencia en memoria guarda ya huellas, no `wamid`. Importa porque
  el duplicado se descarta **antes** de la compuerta, así que ese conjunto
  incluye a quien no ha autorizado.
- CLAUDE.md §11 corregido: decía que se registrara el `wamid`.
- Comprobado con la bitácora capturada: no aparece el número, ni en claro ni
  en base64, ni el `wamid` completo, ni el contenido del mensaje.

**Lo que se pierde:** buscar un mensaje en el panel de Meta, que exige el
`wamid` completo. Se compensa con la marca de tiempo.

**Resuelve el punto abierto 1 del [ADR-0005](adr/0005-procesamiento-asincrono-e-idempotencia.md).**
Su propuesta —guardar el `wamid` "desacoplado de todo identificador de
remitente"— era inviable: el `wamid` **es** un identificador del remitente, y
una tabla de `wamid` en claro sería una tabla de teléfonos. La huella sí lo
consigue.

## Cosas que conviene no olvidar

- **`PHONE_HASH_PEPPER` y `NAME_ENCRYPTION_KEY` son irrecuperables.** Están en
  el `.env` local y en las variables de Railway, y deben ser **idénticos** en
  ambos: los dos entornos apuntan a la misma base. Si el pepper cambia, todas
  las usuarias registradas dejan de ser reconocidas.
- **El repositorio es público.** El `.gitignore` cubre `.env`; no lo
  desactive.
- Hay **una fila real** en `usuario`, la del celular de pruebas del autor. No
  es de prueba: borrarla obliga a repetir el consentimiento.
- La resolución DNS del equipo de desarrollo falla de forma intermitente. Si
  algo "no conecta", reintentar antes de tocar configuración.
- `requirements.txt` tiene versiones **fijas**, a propósito: el prototipo debe
  comportarse igual en la Fase 8 que hoy.
- Para probar en local: `.venv`, `uvicorn app.main:app --reload`. El `.env`
  debe tener las 9 variables o el servicio se niega a arrancar, que es
  deliberado.
- **`GEMINI_API_KEY` es ahora obligatoria.** Hay que añadirla a las
  variables de Railway **antes** del siguiente despliegue: sin ella el
  servicio no arranca y el webhook deja de responder. No es irrecuperable
  como el pepper —se puede generar otra en
  https://aistudio.google.com/apikey—, pero tumba el servicio si falta.
- **`GEMINI_GENERATIVE_MODEL` es opcional** y se puede cambiar en Railway
  sin desplegar. Si no se define, vale el valor por defecto de
  `app/config.py`. Para el agente, la extracción y la redacción del RAG.
- **El modelo de embeddings NO es una variable de entorno**, y es
  deliberado ([ADR-0007](adr/0007-modelo-de-embeddings-fijo-en-codigo.md)):
  cambiarlo invalida todos los vectores guardados **sin dar ningún error**,
  solo con peor recuperación. Vive en `app/core/gemini.py` para que
  cambiarlo exija un commit y re-vectorizar.

## Correcciones pendientes en los `.docx`

Consolidadas en [`docs/adr/README.md`](adr/README.md). Son diez, e incluyen
la contradicción sobre el RLS entre las Fases 2 y 3, el modelo de embeddings
dado de baja, la entrada por voz y el presupuesto de Railway.
