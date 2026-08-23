# Estado del proyecto

Última actualización: 2026-08-19. **La Fase 6 se cerró el 15/08/2026 con la
prueba en un celular real, y el trabajo está en la Fase 7 (calibración y
pruebas).** Los cinco casos de uso están construidos y desplegados, y la
conversación ya se probó desde un celular real. El CU4 es el único que
sigue sin ejercitarse de verdad, y no por un fallo: excluye la huerta de
quien pregunta y solo hay una registrada.

De la Fase 7 van hechas siete cosas, las dos primeras nacidas de esa prueba:

- **El corpus oficial pasó de 81 a 765 fragmentos en nueve fuentes**
  (ADR-0014), y dos de ellas ya no son del Jardín Botánico. Fueron 774
  hasta el 19/08, cuando se quitaron diez fragmentos que eran índices.
- **El CU2 responde aunque ninguna fuente supere el umbral**, con el
  conocimiento del modelo y sin citar a nadie, y toda respuesta que hable
  de salud lleva advertencia (ADR-0015).
- **El CU3 empieza con un onboarding de tres preguntas cerradas**
  (ADR-0016, 17/08/2026), y el catálogo de barrios pasó de 8 a 313.
  **Probado desde un celular real el 17/08/2026, y funcionó.**
- **El corpus se limpió de índices y el umbral bajó a 0.66**, medido
  contra 81 consultas reales de las dos pruebas con celular (19/08/2026).
- **El modelo generativo pasó a `gemini-3.5-flash-lite`** en Railway: los
  de la familia flash completa daban 503 por sobrecarga y tardaban entre
  10 y 138 segundos.
- **La nota de voz se acusa en el acto**, para que ella sepa que llegó. Se
  envía y no se recuerda (ADR-0017). El aviso equivalente para el camino
  con RAG se puso y **se retiró el mismo día**: anunciar la espera la hacía
  sentir más larga.
- **La fecha de siembra salió del CU3 entero** —del prompt, del resumen y de
  la tabla `cultivo`— por ser un dato de solo escritura (ADR-0018).

Falta lo principal: **revalidar el umbral**, que hoy no lo respalda ninguna
medición.

Este documento existe para retomar el trabajo sin releer toda la historia.
Léalo junto con `CLAUDE.md` (instrucciones del proyecto) y `docs/adr/`
(dieciocho decisiones tomadas durante la implementación).

**Si retoma en una conversación nueva, vaya directo a
[Por dónde seguir](#por-dónde-seguir).** Lo de más abajo es historia.

---

## Resumen en una línea

El bot recibe mensajes escritos y hablados, aplica la compuerta de
consentimiento, transcribe las notas de voz y **un agente con function
calling decide qué hacer**: responder con la guía oficial (CU2), contar qué
siembran otras huertas (CU4), ofrecer guardar lo que le contaron (CU3) o
mostrar la ayuda (CU5). Recuerda los últimos diez mensajes. **Los cinco
casos de uso están construidos y desplegados, y la conversación se probó
desde un celular real.** Lo que queda es medirlo y calibrarlo.

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
| Repositorio de datos | `app/services/repositorio.py` | Cubre el esquema entero |
| Cliente de WhatsApp | `app/services/whatsapp.py` | Texto y botones |
| Compuerta de consentimiento (CU1) | `app/services/consentimiento.py` | **Probado de punta a punta** |
| Textos fijos (CU5) | `app/textos.py` | Sin pasar por el modelo |
| Cliente de Gemini | `app/core/gemini.py` | En uso por agente, extracción, RAG y transcripción |
| Vectorización | `app/services/embeddings.py` | Probado contra la API real |
| Descarga de multimedia | `app/services/media.py` | Probado en producción |
| Transcripción | `app/services/normalizacion.py` | Probado en producción |
| Extracción de entidades | `app/services/extraccion.py` | Conectada al flujo |
| Registro de la huerta (CU3) | `app/services/registro.py`, `db/005_*.sql` | Probado de punta a punta |
| Prompts versionados | `app/agent/prompts/`, `plantillas.py` | Seis: `agente_v1`, `extraccion_v3`, `barrio_v1`, `redaccion_rag_v1`, `redaccion_comunidad_v1`, `respuesta_general_v1` |
| Catálogo de fuentes oficiales | `scripts/catalogo_fuentes.py` | Nueve fuentes declaradas, con sus parámetros medidos (ADR-0014) |
| Ingesta de fuentes oficiales | `scripts/ingesta_fuente.py` | **765 fragmentos de nueve fuentes en Supabase**; descarta los renglones de índice |
| Recuperación por similitud | `app/services/recuperacion.py` | Probada contra el corpus real |
| Orientación agroecológica (CU2) | `app/services/orientacion.py` | **Probado en producción** |
| Respuesta sin respaldo oficial | `respuesta_general_v1.md`, `CU2_RESPALDO_MODELO` | Activo desde el 15/08; se apaga en Railway sin desplegar |
| Advertencia de contenido médico | `app/textos.py`, `orientacion.py` | La pone el backend, no el prompt (ADR-0015) |
| Fragmento comunitario | `app/services/fragmento_comunitario.py` | Se genera al confirmar el CU3 |
| Qué siembran otras huertas (CU4) | `app/services/comunidad.py` | Enrutado por el agente desde el 15/08 |
| Memoria de conversación | `app/services/memoria.py`, `db/006_*.sql` | **Probada en producción**; es de donde sale el material de la Fase 7 |
| Agente orquestador | `app/agent/agente.py`, `agente_v1.md` | **Probado en producción desde el celular** |
| Onboarding de tres preguntas | `app/services/onboarding.py`, `db/007_*.sql`, `barrio_v1.md` | **Probado desde un celular real el 17/08/2026** (ADR-0016) |
| Acuse de la nota de voz | `app/services/espera.py` | Se manda al recibir el audio, sin umbral (ADR-0017, revisado) |
| CU3 sin fecha de siembra | `extraccion_v3.md`, `db/008_*.sql` | Código listo; **la migración `008` está sin correr** (ADR-0018) |
| Catálogo de barrios de Bosa | `db/003_catalogo_barrios_bosa.sql` | **313 filas en Supabase** desde el 17/08/2026 |

Flujo comprobado en un celular real: `"Hola"` → bienvenida + botones
[Acepto]/[No acepto] → al aceptar, se crea la fila y se confirma. En la base
quedó el `telefono_hash`, nunca el número. Lo que la prueba completa del
15/08 encontró está más abajo, en
[la prueba con celular](#fase-6-paso-5-la-prueba-con-celular-real-15082026).

## Infraestructura operativa

- **Railway:** desplegado en `https://web-production-1390a.up.railway.app`.
  Arranque por `Procfile`, comprobación de salud en `/health`, que verifica
  Supabase y **dice qué commit está corriendo** desde el 15/08/2026. Sale de
  `RAILWAY_GIT_COMMIT_SHA`, que Railway rellena sola en los despliegues
  desde GitHub; no hay que definirla. En local informa `local`. Con eso,
  confirmar un despliegue ya no exige gastar un mensaje del número de
  prueba. Plan Hobby, USD 5/mes.
- **Supabase:** PostgreSQL 17.6, esquema aplicado, RLS activo sin políticas.
  Conexión por **session pooler, puerto 5432** — la directa es solo IPv6 y el
  equipo de desarrollo no tiene IPv6; el puerto 6543 rompe `asyncpg`.
  **765 fragmentos oficiales de nueve fuentes** desde el 19/08/2026, y
  **313 barrios** desde el 17/08. Escribir ahí cambia lo que responde el
  bot **en el acto**, con o sin despliegue: Railway lee esta misma base.
  **`usuario`, `mensaje`, `huerta`, `cultivo` y `fragmento_comunitario`
  están en cero filas** desde el 18/08/2026: se borró a propósito la fila
  real del autor para volver a recorrer el camino completo. Con eso
  desapareció también la conversación de la prueba del 15/08, que solo
  sobrevive exportada en `fuentes/conversacion_prueba_real.json` —fuera del
  repositorio, que es público—. **`scripts/revisar_prueba_real.py` ya no
  tiene qué reconstruir** hasta que haya una prueba nueva.
- **Meta:** app `Chatbot Huertas Urbanas` (id `4332318797098432`), número de
  prueba `+1 555-136-8057`. Webhook registrado, app suscrita al WABA y campo
  `messages` suscrito. **Los tres pasos son independientes**; que el webhook
  verifique no implica que lleguen mensajes.
- **GitHub:** repositorio **público**. `origin/main` al día en `c0d2303`.
  **Antes de dar por probado nada, compruebe con `/health` qué commit está
  corriendo:** desde el 15/08 lo dice, y el corpus vive en Supabase, así que
  el bot puede estar respondiendo con fragmentos nuevos y código viejo.

## Lo que NO funciona todavía (esperado)

- **El umbral está en 0.66 desde el 19/08/2026**, medido contra 81
  consultas reales y el corpus ya limpio. **No es una calibración
  cerrada:** falta etiquetar leyendo el fragmento recuperado de cada
  consulta, y falta resolver la desviación de `jbb_practicas_2022`. Ver
  [Por dónde seguir](#por-dónde-seguir).
- **`jbb_practicas_2022` no se puede reproducir.** En la base hay 62
  fragmentos y el código produce 83, comprobado el 19/08 revirtiendo a
  `b159cd2`, así que no lo causó la limpieza de índices. Mientras siga
  así, el corpus entero no es reproducible y toda calibración hereda esa
  debilidad.
- **El defecto por defecto del modelo generativo está desalineado.**
  `app/config.py` dice `gemini-3.6-flash` y Railway corre
  `gemini-3.5-flash-lite`. El propio comentario de ese archivo dice que el
  valor por defecto existe para dejar constancia de con qué se probó, así
  que hay que decidirlo: o se baja el defecto, o se documenta por qué no.
- **El `flash-lite` responde peor.** Observado por el autor al cambiarlo:
  mucho más rápido —3 s frente a 10-19 s— pero de menor calidad en la
  redacción del CU2. Está sin medir; es material de la Fase 7.
- **El corpus tiene huecos que el umbral no arregla.** La prueba real dejó
  un tercer grupo de consultas —del dominio, pero fuera de lo que tratan
  las fuentes— que bajar el umbral no salva: solo consigue que se respondan
  con el fragmento equivocado. Lo que piden es más corpus, no menos umbral.
  Están enumeradas como `DESCUBIERTA` en `scripts/calibrar_umbral_real.py`,
  y varias ya dejaron de serlo con las nueve fuentes.
- **Un mensaje que mezcle consulta y dato sigue ofreciendo guardar el
  cultivo por el que se preguntó.** El ADR-0008 daba esto por "cosa del
  agente" y no lo era: el agente enruta bien las dos intenciones, pero la
  extracción corre sobre el mensaje entero. La confirmación la protege;
  queda para calibrar en la Fase 7 (ADR-0013).
- **Quedan dos defectos de extracción declarados en *Sembrando
  Biodiversidad*** (ADR-0014, «Lo que este ADR no resuelve»): los rótulos al
  margen que se cuelan dentro de la frase en unas 17 páginas, y cinco
  páginas con texto rotado que `pypdf` no extrae. **Y uno más, encontrado
  el 19/08 en el catálogo de plantas:** un fragmento contiene la cadena
  `ENREDADERA KJBNVBJNBHJ BHJ Gulupa`, basura de la extracción del PDF.

---

## Por dónde seguir

### 1. Cerrar la calibración del umbral del CU2

**Ya no está en cero, pero tampoco cerrada.** El 19/08/2026 se midieron
**81 consultas reales** —las 63 de la usuaria de la prueba del 15/08 más
las 32 de las pruebas del 18 y el 19— contra el corpus ya limpio, y de ahí
salió el **0.66** que está puesto hoy. Lo que falta son dos cosas
concretas.

**Falta 1: la desviación de `jbb_practicas_2022`.** En la base hay 62
fragmentos de esa fuente y el código produce **83**, comprobado revirtiendo
el árbol a `b159cd2`, así que no lo causó la limpieza de índices. Mientras
siga así, **el corpus entero no es reproducible** y cualquier calibración
hereda esa debilidad. Es lo primero que hay que resolver, y hay que
decidirlo con cuidado: reingerir esa fuente cambia el corpus otra vez y
obliga a remedir.

**Falta 2: etiquetar leyendo el fragmento.** La frontera que importa no es
«del dominio o no», es «el fragmento recuperado responde de verdad o no».
Eso exige leer los 81 textos recuperados uno por uno. Es criterio del
autor, no automatizable, y sin ello el 0.66 es un número razonable pero no
demostrado.

Lo que sí quedó medido y no hay que repetir:

- **Ningún umbral separa la intención.** Los rangos se solapan: «Que
  conocimiento en agricultura sabes» (no es CU2) puntúa **0.6779** y «Qué
  puedo hacer si mis plantas no dan frutos» (sí lo es) puntúa **0.6775**.
  Quien filtra la intención es el agente (ADR-0013), no esto.
- **Los mensajes del CU3 y del CU4 puntúan entre los mejores.** «Y que
  están sembrando las otras huertas» da **0.7194**. Subir el umbral no
  protegería de ellos.
- **Lo verdaderamente ajeno se separa solo:** «Que carro está barato hoy en
  día» **0.5782**, los barrios entre 0.587 y 0.612, y el mensaje de
  emergencia familiar **0.5687**.
- **El umbral decide citar o no citar**, no responder o callar
  (`CU2_RESPALDO_MODELO`). El modo de fallo de citar sin contenido se
  observó en producción el 17/08 con el 0.68 puesto, en una consulta de
  **0.7232**, así que no aparecía solo al bajar el umbral.

**Las etiquetas de `scripts/calibrar_umbral_real.py` siguen desfasadas** y
el script se quedó corto: mide 21 consultas escritas a mano contra las 81
reales que ya existen. Conviene rehacerlo leyendo de `mensaje` y del
export, que es lo que hizo la medición del 19/08.

### 2. El resto de la Fase 7

Lo que ya está identificado y esperando datos de las pruebas por WhatsApp:

- **Los trece segundos del camino con RAG siguen sin resolverse**
  (ADR-0017, revisión). El aviso de texto se probó y se retiró: no añadía
  tiempo, pero anunciar la espera la hacía sentir más larga. Si se quiere
  atacar, la vía es el **indicador de «escribiendo…» de la Cloud API**, que
  no manda ningún mensaje —y que hay que verificar antes contra la
  documentación vigente, porque no se ha hecho—.
  Para repetir cualquier prueba del onboarding basta con **borrar su fila
  de `huerta`**: el siguiente mensaje lo relanza solo, sin repetir el
  consentimiento. Borrar `usuario` también sirve, pero se lleva por
  cascada la conversación de `mensaje`, que es el material de esta fase.
- **Remedir el umbral comunitario** con 5–7 huertas de verdad (ADR-0011).
  Sigue sin tocar desde el 04/08, y no se puede tocar antes: el CU4 excluye
  la huerta de quien pregunta y solo hay una registrada.
- **Cuántas veces responde el CU2 sin respaldo oficial.** Cada vez queda
  contado en la bitácora, y es la señal honesta de dónde le falta corpus
  —que el respaldo del modelo volvió invisible para la usuaria—.
- **Si el vocabulario de la advertencia médica acierta** con consultas
  reales (ADR-0015). Tira a ancho a propósito: advertir de más cuesta dos
  renglones. **Ya hay un caso observado:** se disparó con una consulta de
  plagas —«bichitos verdes»—, que no es de salud. Puede ser el
  comportamiento buscado o puede ser demasiado ancho; hace falta medirlo,
  no decidirlo de memoria.
- **La mezcla consulta + dato**, que sigue ofreciendo guardar el cultivo por
  el que se preguntó (ver arriba, y ADR-0013).
- **Cuántas veces se cuela la etiqueta de procedencia.** La bitácora lo
  registra cada vez que `limpiar_etiquetas` actúa.
- **Cuántas veces el recorte del agente se queda corto.** La bitácora trae
  `literal=True/False` y avisa cuando el CU2 recuperó con el mensaje
  completo tras fallar el recorte (ADR-0013).
- **Ampliar las listas de saludos** con los que las usuarias usen de verdad
  y el sistema no reconozca (ADR-0006).
- **Calibrar** temperaturas, top-k y la ventana de memoria. Todo por
  variables de entorno menos la extracción, que es fija a propósito.

Para diagnosticar una sesión hecha desde el celular, `python -m
scripts.revisar_prueba_real` reconstruye la conversación desde `mensaje` y
remide cada consulta. Hace falta porque la bitácora dice `fragmentos=0`
pero no a qué pregunta (CLAUDE.md §11). **Su salida no va al repositorio,
que es público.**

### 3. Acciones suyas, que no puede hacer la IA

- **Purgar los registros viejos de Railway.** Lo más urgente: los anteriores
  al 30/07/2026 contienen su número de teléfono.
- **Migrar a número propio con SIM nueva antes de la Fase 8.** El
  `PHONE_NUMBER_ID` cambia; nunca escribirlo en el código.
- **Pasar al documento de grado los quince ADR y las veinte correcciones**
  de [`docs/adr/README.md`](adr/README.md). Los ADR-0014 y 0015 todavía no
  han aportado las suyas a esa lista consolidada.
- **Revisar el DNS del equipo.** El resolutor configurado rechaza el host de
  Supabase de forma intermitente (ver más abajo). No rompe nada en
  producción, pero cuesta tiempo en cada sesión de desarrollo.

### Scripts, para no buscarlos

Todos se ejecutan con `python -m scripts.<nombre>` desde la raíz, con el
`.venv` activo. **Los que escriben en la base crean datos temporales y los
borran en un `finally`**, acotados a teléfonos que empiezan por `57000000`;
la fila real del autor no se toca.

| Script | Qué hace |
|---|---|
| `spike_despachador` | La rama completa, entrando por `procesar_evento`. **El más útil para comprobar que nada se rompió.** |
| `spike_agente` | El agente y sus cuatro herramientas, con espías en vez de envíos |
| `spike_memoria` | La ventana, la deduplicación y el aislamiento entre usuarias |
| `spike_comunidad`, `spike_orientacion` | El CU4 y el CU2 por separado |
| `spike_extraccion`, `spike_transcripcion`, `spike_embeddings` | Piezas de la Fase 5 |
| `calibrar_umbral`, `calibrar_fragmento_comunitario` | Las mediciones de los ADR-0010 y 0011, con consultas imaginadas por el autor |
| `calibrar_umbral_real` | **La revalidación de la Fase 7**, con las consultas de la prueba real |
| `revisar_prueba_real` | Reconstruye una sesión hecha desde el celular y remide cada consulta. Solo lee |
| `ingesta_fuente` | La ingesta oficial. `--listar`, `--fuente`, `--detectar-folio`, `--medir-tokens`, `--simular`, `--reingerir` |
| `catalogo_fuentes` | No se ejecuta: es la declaración de las nueve fuentes y sus parámetros medidos |
| `regenerar_fragmentos` | Rehace los fragmentos comunitarios |
| `generar_catalogo_barrios` | Escribe `db/003_catalogo_barrios_bosa.sql` desde el listado oficial. No toca la base |

---

## Historia de la implementación, paso a paso

Lo que sigue es el registro de cómo se llegó hasta aquí, con las medidas
que respaldan cada decisión. Es material para el documento de grado, no
tareas pendientes.

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
     la Fase 8. El valor por defecto de `app/config.py` es
     `gemini-3.6-flash`, **pero Railway corre `gemini-3.5-flash-lite`**
     desde el 19/08: ver la sección del 19/08 más abajo.
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

### Fase 6, paso 1: ingesta hecha el 04/08/2026

**81 fragmentos** del documento del Jardín Botánico en `fragmento_oficial`,
`fuente_id` `5afa2267-bcc6-4773-b5a2-c87593fa32cf`, 768 dimensiones, sin
duplicados. Decisiones en
[ADR-0009](adr/0009-ingesta-de-fuentes-oficiales.md).

Desde el 15/08/2026 el script recibe la fuente del catálogo y estas órdenes
llevan `--fuente` (ADR-0014):

    python -m scripts.ingesta_fuente --listar
    python -m scripts.ingesta_fuente --fuente jbb_pasos_basicos --simular
    python -m scripts.ingesta_fuente --fuente jbb_pasos_basicos --reingerir

- `pypdf` está en **`requirements-scripts.txt`**, aparte, para que no se
  despliegue en Railway. El servicio no abre un PDF nunca.
- Los PDF **no se versionan** (`fuentes/` en el `.gitignore`): el script los
  descarga de la URL registrada en `fuente`.
- **Se ingiere de la página 12 a la 121.** Había que cortar también la cola,
  cosa que este documento no advertía: de la 122 a la 128 van la
  bibliografía, el colofón de imprenta y la contracubierta. El glosario
  (120–121) sí se conserva.
- **El folio aparece en tres formas**, no dos: renglón propio (39 páginas),
  pegado a la palabra (30) y **seguido de espacio** —`"48 Nombre común"`—
  (37). La tercera es la traicionera: deja el número incrustado a mitad del
  texto.
- **El tamaño del fragmento se calibró midiendo tokens de verdad.** La
  aproximación de 4 caracteres por token dejaba los fragmentos cortos, y
  medir sobre una muestra de diez oscilaba entre 4.54 y 4.78 según cuáles
  tocaran. Hay que **dimensionar por el extremo denso del corpus, no por la
  media**: con la media (4.49) la mitad de los fragmentos se salía del
  intervalo, con máximos de 625 tokens. Con 3.9 quedan 229–516, mediana
  392, el 90 % dentro de 300–500. `--medir-tokens` cuenta ahora todos los
  fragmentos. **La constante está calibrada contra ESTE documento**: con
  otra fuente hay que remedir.
- **Las tablas de especies se sanean.** Al extraer, las columnas
  Exótica/Nativa se colapsan en una `x` de la que ya no se sabe a cuál
  pertenece. Se retiran esa marca y su encabezado y se conserva nombre
  común, científico y familia. Se conserva la `x` de los híbridos
  botánicos (`Fragaria x ananassa`), que es otra cosa.

### Fase 6, paso 2: recuperación y CU2, hecho el 04/08/2026

**El CU2 responde, y está probado en producción** el 04/08/2026 con un
celular real: una consulta agroecológica recibe respuesta corta con la
fuente citada, y una consulta ajena al dominio recibe el texto fijo sin
improvisar. Antes se probó de punta a punta contra la base y la API reales
con `python -m scripts.spike_orientacion`. Decisiones en
[ADR-0010](adr/0010-umbral-de-similitud-recalibrado.md).

Es el primer caso de uso que responde con contenido generado: hasta ahora
todo lo que el bot decía era texto fijo o un resumen compuesto por el
código.

Piezas: `app/services/recuperacion.py` (búsqueda y atribución),
`app/services/orientacion.py` (CU2: recupera y redacta),
`app/agent/prompts/redaccion_rag_v1.md`,
`repositorio.buscar_fragmentos_oficiales`, y la rama del despachador que
antes callaba.

**El umbral bajó de 0.70 a 0.68**, y es el hallazgo con más recorrido para
la tesis. Calibrado con `python -m scripts.calibrar_umbral` sobre 12
consultas que el CU2 debe responder y 6 que no:

| Umbral | Responde | Falsos positivos |
|---|---|---|
| 0.65 | 12/12 | 1/6 |
| **0.68** | **12/12** | **0/6** |
| 0.70 | 8/12 | 0/6 |

El 0.70 de la Fase 4 se respaldó en el spike del 29/07 contra documentos
**escritos a mano para la prueba**, con casi las palabras de la consulta
(0.797). Eso no medía la recuperación, medía el parecido de dos frases
escritas a la vez. Contra el corpus real, el mismo tipo de acierto da
0.69–0.77, y con 0.70 se quedaban sin respuesta 4 de 12 consultas
legítimas, incluida la insignia del proyecto desde la Fase 1.

- **El margen es de una centésima**: peor positiva 0.6854, mejor negativa
  0.6752. Esa negativa es el caso difícil metido a propósito —"dónde me
  inscribo para que me regalen una compostera"—, que roza el dominio pero
  pide un trámite. Sin ella, la siguiente está en 0.5947. **Hay que
  revalidarlo en la Fase 7 con consultas reales de las usuarias**, no con
  las que imaginó el autor.
- `RAG_UMBRAL_SIMILITUD` y `RAG_TOP_K` son **variables de entorno** con
  valor por defecto en `config.py`, para poder calibrarlas en Railway sin
  desplegar. Cambiarlas no invalida nada guardado, al contrario que el
  modelo de embeddings (ADR-0007). La configuración rechaza al arrancar un
  umbral fuera de [0, 1]: escribir una distancia donde va una similitud no
  daría error, solo respuestas absurdas.
- **Sin respaldo oficial no se responde.** Si nada supera el umbral se
  contesta con texto fijo y **no** se le pregunta al modelo de todos modos.
  Matiza la jerarquía de CLAUDE.md §6, que admite un tercer nivel de
  conocimiento del modelo advertido: se decide no usarlo en el CU2, porque
  el perfil de usuaria no discrimina bien entre un consejo respaldado y uno
  advertido dentro del mismo mensaje. Queda disponible para el agente en
  conversación general.
- **Cuidado con el operador.** `<=>` de pgvector devuelve *distancia*, no
  similitud. La conversión ocurre una sola vez, dentro del repositorio;
  fuera se habla siempre en similitud. Confundirlo invierte el filtro sin
  dar ningún error.
- Al prompt hubo que meterle dos avisos que salieron de la ingesta: los
  fragmentos pueden empezar o terminar cortados, y el documento remite a
  figuras que la usuaria no puede ver por WhatsApp.

Para la tesis: un spike validado contra material sintético sobreestima la
similitud. La cifra solo vale remedida contra el corpus real.

### Fase 6, paso 3: fragmento comunitario y CU4, hecho el 04/08/2026

**El CU4 funciona, pero no está conectado al despachador** — enrutarlo sin
agente sería un clasificador aparte (CLAUDE.md §4.9). Probado de punta a
punta con `python -m scripts.spike_comunidad`, que crea cuatro huertas
temporales y las borra al terminar. Decisiones en
[ADR-0011](adr/0011-fragmento-comunitario-solo-especies.md), que
**sustituye la composición del texto que proponía el ADR-0004**.

Piezas: `app/services/fragmento_comunitario.py` (generación),
`app/services/comunidad.py` (CU4),
`app/agent/prompts/redaccion_comunidad_v1.md`, la recuperación comunitaria
en `recuperacion.py` y `scripts/regenerar_fragmentos.py`.

**El texto del fragmento son solo las especies**: `"tomate, cilantro,
lechuga"`. Ni nombre de huerta, ni barrio, ni fechas — todo eso llega por
la clave foránea al componer la respuesta. Comparados cuatro formatos
contra consultas reales del CU4, la separación media entre la huerta
pertinente y la que no lo es:

| Formato | Separación |
|---|---|
| plantilla del ADR-0004 | 0,0585 |
| prosa con nombre y barrio | 0,0608 |
| solo cultivos con fecha | 0,0735 |
| **solo especies** | **0,1166** |

- **No es la plantilla como forma, es el contenido repetido.** Redactarla
  como prosa natural no mejora nada: da igual cómo se escriba el nombre y
  el barrio, lo que estorba es que estén.
- **Las fechas también son relleno compartido**, y eso no estaba previsto:
  conservarlas cuesta un tercio de la separación. "marzo de 2026" sale en
  todos los fragmentos y actúa igual que la plantilla, solo que más
  disimulado.
- `RAG_UMBRAL_COMUNITARIO = 0.65`, propio y distinto del oficial —0.68 en
  aquel momento, 0.66 desde el 19/08—: un
  fragmento comunitario es una lista de tres palabras y uno oficial prosa
  de 400 tokens. El hueco medido es de **+0,0437**, cuatro veces más
  holgado que el del CU2.
- **Respaldo por listado.** "¿Qué están sembrando las otras huertas?" no es
  una búsqueda sino un listado, y una lista de especies se parece poco a
  esa frase: se queda en 0,63 y el CU4 callaba teniendo tres huertas que
  enseñar. Si la similitud no devuelve nada, se listan las más recientes.
  **Ese respaldo no filtra por intención**, y por eso importa que el CU4 lo
  enrute el agente.
- **Un error de método que conviene contar en la tesis:** la calibración
  midió el máximo sobre *todas* las huertas, pero en producción se excluye
  la de quien pregunta. En la primera prueba real la excluida era justo la
  que puntuaba más alto, y la consulta general falló pese a que la
  calibración la daba por buena. Mismo tipo de error que el del umbral del
  CU2: medir sobre un montaje que no reproduce las condiciones reales.
- Generar el fragmento **no puede tumbar el registro**: va fuera de la
  transacción y, si falla, el CU3 responde igual. El precio es que esa
  huerta queda invisible al CU4 hasta que se regenere, y por eso el fallo
  queda en la bitácora.
- `scripts/regenerar_fragmentos.py` sirve para tres cosas: poner al día las
  huertas anteriores a la Fase 6, reparar los fallos de generación, y
  rehacerlo todo si algún día cambia el formato del texto.

### Fase 6, paso 4a: memoria de conversación, hecho el 15/08/2026

**`mensaje` se llena y `mensaje.wamid` ya no existe.** Decisiones en
[ADR-0012](adr/0012-memoria-de-conversacion.md). Piezas:
`db/006_memoria_mensaje.sql`, `app/services/memoria.py`,
`repositorio.registrar_mensaje` y `ultimos_mensajes`, y los flujos que
antes enviaban sin recordar.

- **Cierra el resto del hallazgo del 30/07/2026**: no queda ninguna columna
  `wamid` en el esquema.
- **El `unique` de esa columna obligaba a un segundo cambio.** La escritura
  lleva `on conflict do nothing`, porque la garantía es *al menos una vez*:
  sin esa cláusula, el reintento de Meta chocaría con el índice y tumbaría
  justo la rama que el ADR-0005 existe para proteger.
- **La memoria empieza donde termina la compuerta.** La única forma de
  escribir exige `usuario_id`, y ese identificador solo existe si hubo
  consentimiento. Ni la solicitud, ni el rechazo, ni la bienvenida previa
  entran.
- **Enviar y recordar van juntos** (`memoria.responder`). Es una
  invariante: un envío sin registrar deja un hueco que el agente **no puede
  detectar** —una pregunta suya sin respuesta parece sin contestar— y le
  hace repetirse.
- **El contenido va en claro**, decidido a propósito y con el límite
  declarado: `mensaje.contenido` es el primer sitio donde el texto libre de
  la usuaria queda guardado de forma permanente, y ella puede contar ahí lo
  que quiera. Para la tesis: la minimización de la Fase 3 gobierna lo que
  el sistema **pide**, no lo que la usuaria decide escribir.
- **La ventana son diez mensajes, no diez turnos**, y el último es el que
  ella acaba de mandar: el mensaje entrante se registra antes de atenderlo,
  así que la ventana ya tiene la forma con la que se le habla al modelo.
  `MEMORIA_VENTANA_MENSAJES` es opcional, con valor por defecto en código.
- **`mensaje` no se limpia por antigüedad**, al contrario que las otras dos
  tablas efímeras: la ventana lee diez filas y la Fase 7 necesita el
  historial.

**Migración aplicada y probado contra la base real** el 15/08/2026 con
`python -m scripts.spike_memoria`, que crea dos usuarias temporales, las
hace conversar y las borra en un `finally`. Las 17 comprobaciones pasaron:
orden cronológico, corte en 10 conservando los recientes, el reproceso que
no duplica, los nulos que conviven, el aislamiento entre usuarias, la
huella de 64 hex donde antes iba el `wamid` y el tipo que distingue la voz
de lo escrito.

La prueba con celular llegó en el paso 5, junto con la del agente: la
memoria no cambia por sí sola nada de lo que la usuaria ve. Lo que sí
cambió es su papel — **`mensaje` es hoy la única fuente de la que se puede
reconstruir una prueba real**, porque la bitácora no guarda ni la pregunta
ni la respuesta (`scripts/revisar_prueba_real.py`).

### Fase 6, paso 4b: el agente orquestador, hecho el 15/08/2026

**El agente decide y enruta.** Decisiones en
[ADR-0013](adr/0013-agente-orquestador.md). Piezas: `app/agent/agente.py`,
`app/agent/prompts/agente_v1.md`, el respaldo de `orientacion.py` y
`scripts/spike_agente.py`. **Todavía no está conectado al despachador**:
eso es el paso 4c.

Probado con `python -m scripts.spike_agente`, que crea dos usuarias
temporales, sustituye los envíos por espías —no gasta mensajes del número
de prueba— y las borra al terminar. Las 20 comprobaciones pasaron.

- **El agente enruta, no relata.** La salida de cada herramienta se envía
  tal cual, sin volver a pasar por el modelo. Si volviera, una segunda
  pasada a 0.7 podría reescribir una recomendación atada a la guía oficial
  o perder la cita, **y nada delataría que ocurrió**.
- **De ahí que no haya bucle de llamadas**, contra lo que el plan preveía:
  una sola pasada, se ejecuta lo pedido y se manda lo que devuelve.
- **AFC desactivado**, verificado en `google-genai 2.14.0`. Sin eso el SDK
  ejecuta las funciones solo y `registrar_huerta` se salta los botones.
- **Son cuatro herramientas, no tres.** `mostrar_ayuda` existe porque el
  saludo posterior al consentimiento no cabía en las otras tres sin
  incumplir la Fase 2: el modelo decide cuándo, el backend decide qué.
- **`registrar_huerta` no lleva parámetros.** La extracción sigue a 0.1
  sobre el mensaje literal; si los datos vinieran del modelo, "cebolla
  larga" volvería como "cebolla".

**El hallazgo del paso, y solo pudo aparecer con el agente delante.** Ante
"a mi tomate le salieron bichos y de paso sembré lechuga el mes pasado" el
modelo separa la duda del dato —que es lo correcto— y la recuperación
falla:

| Formulación | Mejor similitud | ¿Pasa 0.68? |
|---|---|---|
| mensaje mixto completo | 0.6840 | sí |
| **el recorte del agente** | **0.6796** | **no** |
| "...bichos, que le echo" | 0.6990 | sí |

Cuatro diezmilésimas. El umbral se calibró sobre mensajes **completos**, y
su margen de una centésima no sobrevive a que el agente recorte. Por eso el
CU2 reintenta con el mensaje literal si el recorte no recupera nada. Es la
lección del proyecto al revés: antes era medir reproduciendo producción;
ahora es **que producción conserve las condiciones de la medición**.

Dos cosas que conviene no exagerar en la tesis:

- **El respaldo evita el silencio, no mejora el corpus.** Rescató un solo
  fragmento a 0.6840, y la respuesta empieza reconociendo que no tiene
  información específica. El caso simple recupera tres.
- **El agente NO arregla lo que el ADR-0008 esperaba.** Ese ADR daba la
  mezcla consulta/dato por "cosa del agente". El agente enruta bien las dos
  intenciones, pero la extracción corre sobre el mensaje entero y saca
  `tomate` de la parte que era pregunta, así que el resumen ofrece
  guardarlo. La confirmación la protege; queda para calibrar en la Fase 7.

### Fase 6, paso 4c: el agente conectado, hecho el 15/08/2026

**El despachador ya no decide intenciones.** Se retiraron las dos ramas
provisionales —el saludo por palabras clave después de la compuerta y
tratar cualquier mensaje libre como posible registro— y en su lugar queda
una sola llamada al agente. **Con esto el CU4 queda enrutado**, que era lo
que faltaba desde el 04/08.

Cuidado con lo que NO se retiró: `es_saludo_o_ayuda` sigue vivo **dentro de
la compuerta**, donde el ADR-0006 lo declara camino permanente. Solo sobraba
su uso posterior.

Probado con `python -m scripts.spike_despachador`, que entra por
`procesar_evento` con cargas útiles con la forma real de las de Meta y
espía los tres módulos que envían. Las 15 comprobaciones pasaron, incluidas
las que importan cuando se reemplaza código que funcionaba: la compuerta
sigue cerrada y sin persistir nada de quien no autoriza, el saludo previo
al consentimiento sigue respondiéndose sin modelo, los botones se resuelven
sin pasar por el agente, y el reintento de Meta se sigue descartando.

**Un defecto que solo apareció al cablear:** el modelo copió la etiqueta
interna en la respuesta —"en la huerta COMUNITARIO – La Esperanza"—. Es
intermitente, y por eso los spikes anteriores no lo vieron. Corregido en
los prompts y con una red en `recuperacion.limpiar_etiquetas`, que retira
el rótulo conservando la atribución. Los dos spikes llevan ya una
comprobación que lo atrapa.

### Fase 6, paso 5: la prueba con celular real, 15/08/2026

**Con esto cierra la Fase 6.** Se hizo desde el celular de pruebas del
autor, contra el servicio desplegado, y lo que encontró cambió una decisión
tomada y abrió el trabajo de la Fase 7 entera. Conviene contarlo así en el
documento de grado: la prueba no confirmó lo construido, lo corrigió.

**El hallazgo: seis de diez consultas terminaron en «no le puedo
responder».** Varias eran del dominio. El criterio de éxito del proyecto es
un SUS ≥ 68 con usuarias de la comunidad, y un asistente que se bloquea seis
veces en una sesión no llega a esa cifra.

De ahí salieron dos correcciones, y ninguna de las dos era el ajuste obvio
—bajar el umbral—:

1. **El CU2 responde con el conocimiento del modelo cuando nada supera el
   umbral**, sin citar a nadie. Revierte la decisión 2 del
   [ADR-0010](adr/0010-umbral-de-similitud-recalibrado.md) usando el tercer
   nivel de la jerarquía de CLAUDE.md §6, que siempre estuvo contemplado.
   La objeción de aquel ADR sigue en pie —la usuaria no distingue un consejo
   respaldado de uno advertido **dentro del mismo mensaje**—, y por eso el
   diseño es **o se cita toda la respuesta, o no se cita absolutamente
   nada**, y el camino lo elige el código mirando si la recuperación trajo
   algo. `CU2_RESPALDO_MODELO=false` en Railway devuelve el comportamiento
   anterior sin desplegar.
2. **El corpus era el problema, no el umbral.** Lo cual llevó a la
   ampliación del ADR-0014, que es la Fase 7.

**El umbral se queda en 0.68 pero ya no significa lo mismo**: antes decidía
responder o callar, ahora decide **citar o no citar**. Se probó bajarlo a
0.65 y apareció un modo de fallo que a 0.68 no existe —consultas que pasan
el filtro, no encuentran nada útil y responden «no tengo la información»
con `Fuente: Jardín Botánico` al pie—. Una cita al pie de una frase vacía
es peor que no responder.

Dos mediciones que contradicen al ADR-0010 aunque el número no cambie, y
que están anotadas en `app/config.py` para que no se pierdan:

- **La frontera que aquel ADR midió ya no existe.** Con consultas reales, la
  peor legítima puntúa 0.6584 y el mejor mensaje que **no** es del CU2,
  0.6977. Los rangos se solapan y ningún umbral los separa. Quien filtra la
  intención hoy es el agente (ADR-0013).
- **Su control negativo difícil** —«dónde me inscribo para que me regalen
  una compostera», 0.6752— **puntúa más alto que una consulta legítima de la
  prueba real** —«qué recomendaciones me das para sembrar papa», 0.6729—.

**Y las consultas no se parten en dos grupos sino en tres**, que es el
hallazgo con más recorrido: `CUBIERTA` (del dominio y el documento la
responde), `DESCUBIERTA` (del dominio y el corpus no la trata) y `NO_ES_CU2`
(saludo, ayuda, registro, comunidad, botón; hoy las atrapa el agente antes).
**Bajar el umbral no salva a las `DESCUBIERTA`**: solo consigue que se
respondan con el fragmento equivocado y la fuente citada al pie. Esas piden
corpus.

Dos herramientas nuevas, las dos de la Fase 7:
[`scripts/revisar_prueba_real.py`](../scripts/revisar_prueba_real.py), que
reconstruye la sesión desde `mensaje` y remide cada consulta —hacía falta
porque la bitácora dice `fragmentos=0` sin decir a qué pregunta—, y
[`scripts/calibrar_umbral_real.py`](../scripts/calibrar_umbral_real.py),
el compañero de `calibrar_umbral.py` con las consultas que escribió una
persona sin saber qué había en el corpus.

**Del repositorio quedan fuera la conversación y los mensajes que nombran
el barrio**, además de uno de emergencia familiar: el repositorio es
público. Sus similitudes van de 0.5618 a 0.5917, muy por debajo de
cualquier umbral candidato, así que no cambian ninguna conclusión.

### Fase 7, en curso: el corpus pasó de 81 a 774 fragmentos

Hecho el 15/08/2026 en tres tandas, con el catálogo del
[ADR-0014](adr/0014-catalogo-de-fuentes-oficiales.md). Nueve fuentes, y
**dos ya no son del Jardín Botánico**: es la primera vez que pasa, y la
línea que lee la usuaria dirá «FAO» o «Universidad Nacional Abierta y a
Distancia» porque sale de la tabla `fuente` por la clave foránea.

| Fragmentos | Fuente | Entidad |
|---|---|---|
| 220 | Sembrando biodiversidad Vol. 1 | Jardín Botánico |
| 125 | Catálogo de plantas usadas en agricultura urbana | Jardín Botánico |
| 92 | Producción agroecológica urbana y periurbana | UNAD |
| 81 | Pasos básicos para establecer y manejar tu huerta | Jardín Botánico |
| 68 | Manual de compostaje del agricultor | FAO |
| 62 | Prácticas para establecer y manejar tu huerta | Jardín Botánico |
| 46 | Cartilla 1. Agricultura urbana | Jardín Botánico |
| 46 | Protocolo de espacio público, Decreto 315/2024 | Jardín Botánico |
| 34 | Manejo integrado de fertilización y plagas | Jardín Botánico |
| **774** | **nueve fuentes** | |

**Esos nueve números son la prueba de regresión.** Cualquier cambio en la
tubería de ingesta tiene que seguir dándolos, porque ese corpus es el que
sostiene lo que se mida a partir de ahora.

Lo medido al ampliar, que no sustituye a la revalidación:

| Consulta | 81 fragmentos | 774 |
|---|---|---|
| «a mi mata de tomate le salieron unos bichitos verdes» | 0.6911 | **0.7231** |
| «puedo sembrar en el parque de mi barrio» | sin respuesta | **4 de 4 del Protocolo** |
| «cuándo cambio el aceite del carro» | descarta | descarta |

Las siete consultas cubiertas de la prueba real pasan hoy el umbral; antes
la peor se quedaba en 0.6584.

**El criterio de recorte, acordado el 15/08/2026:** entra lo que le dice a
una líder de huerta **cómo** hacer algo en Bogotá; sale lo que describe
dónde más se hace, la política nacional o tecnología que ella no va a usar.
Ante la duda, se recorta. Por eso del libro de la UNAD entró un capítulo de
cinco y de la FAO se quitaron las experiencias en otros países.

Lo que la ampliación enseñó, y está detallado en el ADR-0014: que un buen
indicador puede estar midiendo lo que no es —con la extracción desordenada,
el troceo daba el 99 % dentro del intervalo mientras el contenido estaba
revuelto—; que para buscar defectos en un texto extraído hay que
**inventariar y no buscar sospechosos**; y que la regla del extremo denso
del ADR-0009 no vale para todos los documentos.

**En medio de esto apareció el ADR-0015.** Las fuentes traen usos
medicinales y toxicidad, y la respuesta terminaba en `Fuente: Jardín
Botánico`, que es el sello del nivel verificado de la jerarquía. La
advertencia la pone el backend como texto fijo, no una regla de prompt
—a 0.4 las reglas de prompt se incumplen de forma intermitente, y está
medido aquí mismo con la etiqueta `[OFICIAL – ...]`—, y **se mira el texto
que sale, no el fragmento que entra**, porque el camino sin respaldo no
tiene ningún fragmento que marcar. Comprobado 7 de 7. No filtra el
contenido: lo que corrige es el sello, no lo que la guía dice.

### Fase 7: el onboarding de tres preguntas, 17/08/2026

**El CU3 capturaba mal la información, y la causa no era la extracción.**
Al aceptar el consentimiento, el bot mandaba un solo mensaje libre pidiendo
tres cosas a la vez —nombre de huerta, barrio y qué tenía sembrado— y de
una respuesta parcial a tres preguntas no sale una extracción buena. Lo
corrige el [ADR-0016](adr/0016-onboarding-de-preguntas-cerradas.md).

Piezas: `app/services/onboarding.py`, `db/007_onboarding_pendiente.sql`,
`app/agent/prompts/barrio_v1.md`, `extraccion_v2.md`, el cambio de firma de
`memoria.responder`, y `db/003_catalogo_barrios_bosa.sql` con
`scripts/generar_catalogo_barrios.py`.

- **Tres preguntas cerradas, una por mensaje**, con el eco de la anterior
  dentro de la siguiente. La única confirmación explícita es la del final,
  con los botones que ya existían del CU3.
- **`huerta` cambió de significado**, y es lo que más hay que tener
  presente: existir en esa tabla ya no es «registró algo» sino «completó el
  onboarding». Una huerta sin cultivos es hoy lo normal.
- **El barrio se desambigua con lista numerada de texto, no con botones.**
  La medición lo decidió: el rótulo de un botón admite 20 caracteres,
  **76 de los 312 barrios de Bosa (24 %) pasan de ahí** —máximo 38— y
  `whatsapp.enviar_botones` **lanza `ValueError`**, no degrada. Recortar
  tampoco vale: a 20 caracteres seis grupos quedan con el rótulo idéntico,
  y los cuatro `SAN BERNARDINO SECTOR …` colapsan en el mismo texto.
  **Consecuencia buena: no hubo que enmendar el §4.3 de CLAUDE.md.** El
  diseño con botones sí lo exigía.
- **Los candidatos los busca el modelo, no `pg_trgm`.** El catálogo trae
  variantes que comparten el arranque —`HOLANDA`, `HOLANDA I SECTOR`,
  `HOLANDA SECTOR CAMINITO`— y la similitud de cadenas no distingue el
  barrio base; el modelo sí. Comprobado en el spike: ante «Holanda»
  devolvió `HOLANDA`, `HOLANDA I SECTOR`, `HOLANDA II SECTOR`, en ese
  orden. Y se ahorra un umbral que calibrar en una fase que ya arrastra
  la revalidación del 0.68.
- **El número se lee sin modelo, y acepta la palabra.** `3` y `tres`, nada
  más. La palabra no es una concesión: `normalizacion.py` transcribe
  literalmente a 0.0, así que una nota de voz diciendo «tres» llega en
  letras y nunca como dígito. Con un lector de solo dígitos, quien responde
  por voz **no podría terminar el onboarding jamás**, y el barrio es
  obligatorio.
- **La quinta opción aparece al tercer «Ninguno»**, no antes: ofrecer la
  salida de entrada degradaría el dato del barrio, que sostiene la
  atribución del CU4. Y el contador es el de «Ninguno», no el de respuestas
  ininteligibles: si no consigue escribir `3`, tampoco escribirá `5`.
- **El saludo personalizado se antepone al enviar y no se recuerda.** Es el
  motivo del cambio de firma de `memoria.responder`: el nombre va cifrado
  en `usuario` y `mensaje.contenido` va en claro (ADR-0012), así que meter
  el saludo en la memoria anularía el cifrado. Primera vez que se usa
  `nombre_usuario_cifrado`.

**El catálogo pasó de 8 a 313 barrios** (312 de Bosa más `otro`), en
mayúscula y sin recortar. `Los 3 Sectores` **no entró**: no está en el
listado oficial, lo que corrige el ADR-0002 en sentido contrario —era el
§7.1 del anteproyecto el que acertaba al omitirlo, no el §5.3.1—.

Antes de sembrar se vaciaron `huerta`, `cultivo`, `fragmento_comunitario`,
`registro_pendiente`, `idempotencia_webhook` y `barrio`. **No se tocaron
`usuario`, `mensaje`, `fuente` ni `fragmento_oficial`**: contienen la fila
real del autor, los 126 mensajes de la prueba con celular y los 774
fragmentos que sostienen la calibración. Un borrado general se los habría
llevado sin ninguna necesidad, porque ninguna de esas cuatro tablas tiene
relación con `barrio`.

Probado con `spike_despachador` (25 comprobaciones), `spike_agente` (21) y
`spike_extraccion`, los tres contra la base y la API reales, y **desde un
celular real el 17/08/2026, donde funcionó de punta a punta**. La salvedad
que dejó esa prueba: se recorrió con una usuaria que lee lo que le llega y
contesta a lo que se le pregunta. Que el onboarding aguante a quien no lo
hace es lo que la evaluación con 5–7 usuarias tiene que decir.

Lo que quedó declarado como pendiente de medir, en el propio ADR: si tres
candidatos bastan, si tres rondas antes de ofrecer `otro` son demasiadas, y
si `EL BOSQUE DE BOSA` es el mismo barrio que el `El Bosque` del
anteproyecto.

### Fase 7: el aviso de espera y la salida de la fecha, 18/08/2026

Dos cambios del mismo día, ninguno de los dos nacido de un fallo.

**El aviso de espera** ([ADR-0017](adr/0017-aviso-de-espera.md)), del que
**solo sobrevivió el acuse de la nota de voz**. Se probó desde el celular
el mismo día y el aviso del camino con RAG se retiró: no añadía tiempo de
reloj —sale en una tarea aparte— pero anunciar la espera la volvía algo que
se mide, y trece segundos anunciados se hacen más largos que trece sin
anunciar. Con él salieron el umbral, el `ContextVar` y las diez frases del
RAG. Lo que queda es un acuse que confirma que el audio llegó, que es otra
cosa: no pide paciencia, da una información que ella no tiene por ningún
otro medio.

- **Se envía y no se recuerda.** Es la única excepción al CLAUDE.md §11, y
  está razonada: el acuse no dice nada que el agente necesite después, pero
  recordarlo gastaría uno de los diez huecos de la ventana en cada nota de
  voz.
- **Sin umbral y sin bloquear.** Sale en cuanto el webhook dice que el
  mensaje es un audio, en una tarea aparte, así que la transcripción no lo
  espera. Para un acuse que confirma la recepción, retrasarlo es lo
  contrario de lo que se busca.
- **Seis frases repartidas barajadas.** La primera versión repetía al
  cambiar de tanda, y salió probando.

**Lo que se retiró el mismo día**, tras la prueba con celular: el aviso del
camino con RAG, el umbral `ESPERA_AVISO_SEGUNDOS`, el `ContextVar` que
cruzaba el estado entre el despachador y el agente, y las diez frases de
`ESPERA_RAG`. La revisión del ADR-0017 detalla qué decisión cae y cuál
queda en pie.

**La fecha de siembra salió del CU3**
([ADR-0018](adr/0018-sin-fecha-de-siembra.md)). Era un dato de solo
escritura: la escribían dos `INSERT` y no la leía ningún caso de uso. El
CU4 ya la excluía a propósito y **con medición** —el ADR-0011 comparó cuatro
formatos y «solo especies» separaba 0.1166 frente a 0.0735 de «cultivos con
fecha»—, así que esto extiende al CU3 lo que el CU4 concluyó el 04/08.

- Fuera del prompt (`extraccion_v3.md`, de 2620 a **1783 caracteres**), del
  esquema de salida, del resumen de confirmación y de la tabla `cultivo`.
- El modelo queda con **un solo campo que acertar** por cultivo.
- El resumen que ella aprueba pasa de `- tomate, marzo de 2026 (más o
  menos)` a `- tomate`.
- El ejemplo de la bienvenida cambió: enseñaba `"sembré cilantro en marzo"`,
  una fecha que el sistema iba a ignorar.
- `_deserializar` tolera los borradores de los dos formatos anteriores, para
  que uno escrito antes del despliegue y confirmado después no se pierda.

**La migración `db/008_sin_fecha_de_siembra.sql` está escrita y sin correr,
a propósito.** El orden importa: primero se despliega el código que deja de
escribir esas columnas y solo después se borran. Al revés, cada
confirmación del CU3 falla mientras dure la ventana, porque Railway lee esta
misma base.

### Fase 7: corpus limpio, umbral a 0.66 y cambio de modelo, 19/08/2026

Tres cosas del mismo día, y la primera nació de una pregunta suya: por qué
tardaba tanto.

**El modelo generativo pasó a `gemini-3.5-flash-lite`, en Railway.**
Cronometrando cada etapa por separado, el RAG y la base resultaron ser
ruido —embedding 0.33 s, Supabase 0.30 s, recuperación completa 0.83 s— y
todo el tiempo se lo llevaba el modelo. Con `gemini-3.6-flash` un prompt
trivial tardó 18 s, 31 s y 1.95 s, y la causa era **503 UNAVAILABLE por
sobrecarga** más los reintentos del SDK. Midiendo siete modelos sin
reintentos y con tope de 20 s:

| Modelo | 3 intentos (s) | Pensamiento | Éxito |
|---|---|---|---|
| `gemini-3.5-flash-lite` | 3.3 · 3.4 · 3.0 | 0 | **3/3** |
| `gemini-3.5-flash` | 13.6 · 9.1 · 17.0 | 996 | 2/3 |
| `gemini-3.6-flash` | 10.9 · 19.2 · 19.3 | 965 | 1/3 |
| `gemini-3.7-flash` | 19.2 · 1.7 · 20.0 | — | 0/3 |
| `gemini-2.5-flash` | 10.1 · 19.6 · 19.6 | 976 | 1/3 |

No era problema del `3.6`: fallaban todos los de la familia flash
completa. Los *lite* **no piensan** —cero tokens de pensamiento— y parecen
estar en otra cola de capacidad. Se comprobó antes de recomendarlo que
`3.5-flash-lite` **acepta function calling y entrada de audio**, que son
obligatorios aquí.

**Ojo con esto:** el cambio está solo en Railway. `app/config.py` sigue
diciendo `gemini-3.6-flash`, y eso contradice la propia nota de ese
archivo, que dice que el valor por defecto existe para que el repositorio
deje constancia de con qué se probó. **Hay que decidir si se baja el
defecto a `flash-lite`.** El autor observó además que responde peor que el
flash completo, así que la decisión no es obvia.

**El corpus perdió diez fragmentos que eran índices.** Midiendo las 81
consultas reales contra los 774 fragmentos, resultó que los índices
—«Cilantro ........... 51»— salían entre los cuatro mejores en el 25 % de
las consultas y como el **mejor** en el 10 %. Un índice es una lista de
nombres de plantas: puntúa altísimo contra cualquier pregunta sobre
plantas y no responde nada. Era la causa principal del «no tengo esa
información» firmado con `Fuente: Jardín Botánico`, que la usuaria notó en
la prueba del 15/08 con un mensaje que decía literalmente *«sino me estas
respondiendo nada, porque citas información?»*.

El filtro va en `_reconstruir_parrafos`, donde ya se descartan la plantilla
y los pies de figura. Reingeridas las dos fuentes afectadas: catálogo de
plantas 125 → 120 y cartilla de fertilización 34 → 30. **Corpus en 765**, y
la polución de índices en esas mismas 81 consultas bajó a 0 %.

**Matiz importante que se descubrió al revisarlo:** ese 25 % medía
consultas cuya recuperación cambió, no respuestas que la usuaria vaya a
notar mejores. La mayoría eran barrios, saludos y mensajes del CU3 y CU4,
que **nunca llegan al CU2**. Filtrando a consultas reales del CU2, el
mejor fragmento era un índice en **2** casos y estaba en tercera o cuarta
posición en unos 7 más. La mejora es real pero modesta; lo que sí
desaparece es la causa principal del modo de fallo de la cita vacía.

**El umbral bajó de 0.68 a 0.66.** Quitar los índices **bajó** las
similitudes de las consultas que los recuperaban —lo que ganaba era el
índice— y varias legítimas quedaron rozando el 0.68:

    Cuánto se demora en dar cosecha la papa    0.6883 -> 0.6865
    pero que plantas me sirven para interior   0.6755 -> 0.6643
    Que recomendaciones das para sembrar papa  0.7282 -> 0.7044

Con 0.66 pasan a citar cuatro consultas legítimas más. El razonamiento
completo, con las mediciones que contradicen al ADR-0010, está en el
comentario de `RAG_UMBRAL_SIMILITUD` en `app/config.py`.

**Y se corrigieron dos restos de la fecha de siembra** que el ADR-0018 no
había alcanzado, porque hablaban de la fecha en prosa y no con los nombres
de código que se rastrearon: `REGISTRO_NADA_QUE_ANOTAR`, que le preguntaba
«¿por ahí cuándo lo sembró?», y el prompt del agente, que describía
`registrar_huerta` con la fecha, el nombre de la huerta y el barrio —los
tres retirados ya, por el ADR-0018 y el ADR-0016—. El segundo era el más
serio: el prompt decide el enrutamiento, así que describir la herramienta
con campos muertos invita a llamarla cuando no toca.

**Falta el ADR de todo esto.** Sería el **ADR-0019** y hoy solo vive en los
mensajes de commit `00133ef`, `9102b50` y `d6cac90`.

### Primera fuente oficial, ya verificada

| Campo de `fuente` | Valor |
|---|---|
| `entidad` | Jardín Botánico de Bogotá José Celestino Mutis |
| `titulo` | Pasos básicos para establecer y manejar tu huerta. Una guía práctica para agricultores urbanos |
| `url` | https://jbb.gov.co/documentos/cientifica/publicaciones/Pasos_basicos_para_establecer_y_manejar_tu_huerta.pdf |

Comprobado el 30/07/2026: 128 páginas, **PDF de texto, no escaneado**
(Adobe InDesign, 27 fuentes incrustadas), 146 874 caracteres extraíbles y
solo 5 páginas casi vacías. Vocabulario del dominio bien representado
—plaga 42, semilla 62, sustrato 56, cosecha 46—. Da para unos 80–110
fragmentos con el troceado de la Fase 4. Autores: Edgar Germán Herrera
Guzmán y Edgar Hernán Lara García, 2020, ISBN digital 978-958-8576-49-7.

Al ingerirlo, dos limpiezas: **descartar las ~10 primeras páginas**
(créditos, ISBN, tabla de contenido), que solo meterían ruido en el RAG, y
despegar el número de página de la primera palabra (`"65Para la
propagación"`).

**La ingesta debería ser un script local, no parte del servicio**: se
ejecuta una vez y escribe en Supabase. Así `pypdf` no entra en el
`requirements.txt` que se despliega en Railway.

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

**El resto que quedaba se cerró el 15/08/2026.** La tabla `mensaje` de
`db/001_esquema.sql` declaraba `wamid text unique`, en claro, con un
comentario que además decía que la idempotencia "sigue en memoria por
ahora". Las dos cosas eran anteriores a la corrección del 30/07/2026, y
eran inocuas mientras nada escribiera en `mensaje`.

`db/006_memoria_mensaje.sql` la pasa a `huella_wamid` y corrige los
comentarios (ADR-0012). **Ya no queda ninguna columna `wamid` en el
esquema**, y la memoria del agente se pudo encender sin volver a meter el
teléfono en la base.

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
  **Diagnosticado el 15/08/2026:** el culpable es el resolutor configurado
  en el equipo, no la red ni Supabase. `Resolve-DnsName <host>` devuelve
  "operación DNS rechazada" mientras que `Resolve-DnsName <host> -Server
  8.8.8.8` resuelve al momento. Si vuelve a pasar, esa pareja de comandos
  lo confirma en diez segundos.
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
- **`CU2_RESPALDO_MODELO` es un interruptor a propósito.** En `false`
  devuelve el comportamiento del ADR-0010 —el CU2 calla si nada supera el
  umbral— sin desplegar y sin tocar código. Es lo que hay que hacer si la
  evaluación con usuarias dice que un consejo sin respaldo confunde más de
  lo que ayuda.
- **El corpus vive en Supabase, no en el despliegue.** Ingerir una fuente
  cambia lo que responde el bot en el acto, con o sin despliegue, y por eso
  una respuesta rara puede venir de código viejo con corpus nuevo. `/health`
  dice qué commit corre.
- **Ninguna fuente oficial se ingiere a mano.** Se declara en
  `scripts/catalogo_fuentes.py` y se ingiere con `--fuente <clave>`. Los
  parámetros del catálogo son mediciones: `ratio_medida=False` bloquea la
  ingesta real hasta que se mida.
- **El modelo de embeddings NO es una variable de entorno**, y es
  deliberado ([ADR-0007](adr/0007-modelo-de-embeddings-fijo-en-codigo.md)):
  cambiarlo invalida todos los vectores guardados **sin dar ningún error**,
  solo con peor recuperación. Vive en `app/core/gemini.py` para que
  cambiarlo exija un commit y re-vectorizar.

## Correcciones pendientes en los `.docx`

Consolidadas en [`docs/adr/README.md`](adr/README.md). Son veinte, e
incluyen la contradicción sobre el RLS entre las Fases 2 y 3, el modelo de
embeddings dado de baja, la entrada por voz, el presupuesto de Railway y lo
que la Fase 3 no dice sobre la conversación almacenada.

**Los ADR-0014 y 0015 aún no han aportado las suyas a esa lista**, y son
al menos cuatro: que el corpus oficial son nueve documentos y no uno, que
dos no son del Jardín Botánico, la desviación declarada del intervalo de
300–500 tokens en el catálogo de plantas, y que ninguna fase previó que una
fuente de agricultura urbana atribuyera usos medicinales.
