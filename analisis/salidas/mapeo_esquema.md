# Mapeo del esquema para la evaluación formativa

| | |
|---|---|
| **Fase** | 1 de la evaluación formativa de usabilidad (punto de control) |
| **Fecha** | 28/09/2026 |
| **Estado** | **Esperando aprobación del autor.** No se ha calculado ninguna medida |
| **Instantánea** | `FECHA_EXTRACCION = 2026-09-29T02:27:05Z` (28/09/2026 21:27 en Bogotá) |
| **Consultas** | [`analisis/sql/f1_esquema.sql`](../sql/f1_esquema.sql), [`analisis/sql/f1_universo.sql`](../sql/f1_universo.sql) |

Este documento es el punto de control que pide la Fase 1: qué tabla o
columna representa cada concepto, la secuencia mínima de cada tarea, los
mensajes de error del bot, y **las seis decisiones que el autor tiene que
aprobar antes de calcular nada**.

Todo lo que sigue se comprobó contra la base, no contra la documentación.
Importa decirlo porque los dos puntos de partida estaban equivocados:
`docs/ESTADO.md` decía 12 usuarias al 25/09/2026 y el prompt de la
evaluación esperaba 16 elegibles.

---

## 1. Universo medido

**17 usuarias, 15 huertas, 77 cultivos, 356 mensajes** (169 de ellas, 187
del asistente), del **09/09/2026 al 28/09/2026**. Cinco consintieron el
27/09, lo que explica la diferencia con lo que decían los documentos.

Las 17 filas de `usuario` **autorizaron el tratamiento**: la existencia de
la fila *es* el consentimiento (CU1, ADR-0003). Ninguna rechazó de forma
registrable, porque el rechazo no se persiste.

**Las 17 tienen al menos un mensaje entrante**, así que el filtro del
prompt —«usuarios con al menos un mensaje entrante»— no descarta a nadie y
el universo coincide con «todas las que autorizaron», que es lo que el
autor pidió.

| Seudónimo | Consintió | Dio su nombre | Completó onboarding | Cultivos | Mensajes de ella | Del asistente | Días con actividad |
|---|---|---|---|---|---|---|---|
| P-01 | 09/09 | sí | sí | 0 | 8 | 9 | 1 |
| P-02 | 09/09 | sí | sí | 1 | 13 | 14 | **3** |
| P-03 | 09/09 | sí | sí | 26 | 19 | 20 | 1 |
| P-04 | 09/09 | sí | sí | 0 | 11 | 12 | 1 |
| P-05 | 10/09 | sí | **no** | 0 | 1 | 2 | 1 |
| P-06 | 15/09 | sí | **no** | 0 | 4 | 5 | 1 |
| P-07 | 15/09 | sí | sí | 15 | 24 | 26 | 1 |
| P-08 | 15/09 | sí | sí | 14 | 9 | 10 | 1 |
| P-09 | 17/09 | sí | sí | 1 | 11 | 12 | 1 |
| P-10 | 18/09 | sí | sí | 4 | 17 | 18 | 1 |
| P-11 | 23/09 | sí | sí | 0 | 6 | 7 | 1 |
| P-12 | 25/09 | sí | sí | 0 | 7 | 8 | 1 |
| P-13 | 27/09 | sí | sí | 6 | 7 | 8 | 1 |
| P-14 | 27/09 | sí | sí | 2 | 9 | 10 | 1 |
| P-15 | 27/09 | sí | sí | 3 | 10 | 11 | 1 |
| P-16 | 27/09 | sí | sí | 5 | 8 | 9 | 1 |
| P-17 | 27/09 | sí | sí | 0 | 5 | 6 | **2** |

Los seudónimos van por orden de consentimiento, igual que en
[`registro-de-aceptacion.md`](../../docs/pruebas/registro-de-aceptacion.md),
así que **P-01 a P-12 son las mismas personas** que allí. La
correspondencia con `identidad_hash` vive solo en los CSV, que no se
versionan.

**Quince de diecisiete volvieron un solo día.** P-02 escribió en tres días
distintos y P-17 en dos. Es el indicio más fuerte que hay en la base para
hablar de adopción, y va al informe.

---

## 2. Tabla o columna → concepto

| Concepto | Dónde vive | Reserva |
|---|---|---|
| Identidad de la usuaria | `usuario.identidad_hash` | HMAC-SHA256 del **BSUID de Meta** con pepper y etiqueta `bsuid:`. **No es `telefono_hash`**: la migración `010` lo renombró el 17/09/2026 y el teléfono no se guarda en ninguna forma (ADR-0023) |
| Consentimiento otorgado | La **existencia** de la fila en `usuario`; instante en `consentimiento_en` | No hay columna booleana ni registro del rechazo |
| Nombre de la usuaria | `usuario.nombre_usuario_cifrado` (AES-GCM) | **No prueba que el onboarding se completara**: se persiste en la *primera* de las tres preguntas. Ver la decisión D-2 |
| Perfil de la huerta | `huerta.barrio_id` → `barrio.nombre`, `huerta.nombre_huerta` | La fila se crea **solo al pulsar el botón del cierre**, con las tres respuestas juntas |
| Onboarding completo | La **existencia** de la fila en `huerta` | Es la definición del proyecto (`CLAUDE.md` §5) |
| Cultivos registrados | `cultivo.especie`, `cultivo.huerta_id` | Sin fecha de siembra desde la migración `008` (ADR-0018) |
| Conversación | `mensaje.rol` (`usuaria`/`asistente`), `mensaje.contenido`, `mensaje.creado_en` | `contenido` **sin cifrar**, y lleva dentro el nombre de pila de ella (INC-026) |
| Cómo llegó el mensaje | `mensaje.tipo`: `text`, `audio`, `interactive` | Es el tipo **antes** de normalizar: `audio` significa nota de voz ya transcrita. `interactive` es una pulsación de botón |
| Trazabilidad del mensaje de Meta | `mensaje.huella_wamid` | HMAC, no el `wamid`. Nulo si el envío falló |
| Duplicados del webhook | `idempotencia_webhook.wamid_huella`, `estado` | **Sin `usuario_id` a propósito**: se escribe antes de la compuerta. No se puede atribuir un duplicado a nadie |
| Estado del onboarding en curso | `onboarding_pendiente.paso` | **Vacía (0 filas).** Se borra al completar y caduca a las 24 h: no sirve para reconstruir dónde se atascó nadie |
| Borrador del registro | `registro_pendiente.datos` | **Vacía (0 filas)**, por lo mismo |

**No existe ninguna columna de intención, de herramienta ni de caso de
uso.** `mensaje` no guarda qué respondió. Todo lo que sigue se deduce de
las **marcas de los textos que compone el backend**, que es el método que
ya usa `scripts/registro_aceptacion.py`.

### 2.1 Idempotencia y Ef-3-G

`idempotencia_webhook` tiene **70 filas y ninguna sin procesar**. Descarta
un reintento de Meta solo cuando el estado es `procesado`, así que **los
duplicados de Meta no llegan a `mensaje`**: no inflan el conteo de
mensajes repetidos. El «mensaje del usuario repetido textualmente en menos
de 2 minutos» de Ef-3-G queda entonces midiendo lo que debe medir —que
**ella** repitió— y no un reintento del canal.

Hay 356 filas en `mensaje` frente a 70 de idempotencia porque la tabla se
purga y `mensaje` no.

---

## 3. Lo que la base no puede dar, y por qué

Cuatro huecos. Ninguno es un defecto: son consecuencia de decisiones
documentadas.

1. **El primer mensaje de ella no existe.** Todo lo anterior a la
   compuerta se envía con `whatsapp.enviar_texto` y **no se recuerda**
   (ADR-0012): su «hola», la bienvenida, la solicitud de permiso y la
   pulsación de «Acepto». La primera fila de `mensaje` de cualquiera es la
   **primera pregunta del onboarding**, que sí la manda `memoria.responder`.
   → El arranque de Ey-1-G de T1 que pide el prompt **no está**. Ver D-5.
2. **Los pasos intermedios del embudo no son columnas.** `huerta` se crea
   entera al final, y `onboarding_pendiente` está vacía. «Barrio» y
   «nombre de huerta» solo se ven en las **marcas de los textos** del
   asistente en `mensaje`. El paso «bienvenida» no se ve de ninguna forma.
3. **Cinco envíos no se recuerdan**, así que un hueco en `mensaje` no
   prueba silencio: el acuse de la nota de voz (ADR-0017), el saludo
   personalizado (ADR-0016), el aviso de base caída (ADR-0019), la
   disculpa de la nota de voz que no se entendió, y todo lo de antes de la
   compuerta.
4. **El texto guardado no es exactamente el que ella vio.**
   `memoria.responder` antepone el saludo personalizado a lo que **envía**
   y guarda el cuerpo **sin** él. La diferencia es una línea con su nombre.

---

## 4. Secuencia mínima por tarea

Derivada del código, no estimada. Es el denominador de Ey-5-S.

### T1 — autorización y onboarding (CU1 + CU6)

**6 mensajes de ella; 5 quedan en `mensaje`.**

| # | Mensaje de ella | Respuesta del backend | ¿Queda registrado? |
|---|---|---|---|
| 1 | Botón **Acepto** | `CONSENTIMIENTO_ACEPTADO` + primera pregunta | La pulsación **no**; la pregunta **sí** |
| 2 | Su nombre de pila | Eco + `¿En qué barrio de Bosa…?` | Sí |
| 3 | El barrio, en lenguaje natural | **Lista numerada** de candidatos | Sí |
| 4 | El **número** de la lista | Eco del barrio + `¿Cómo se llama su huerta?` | Sí |
| 5 | El nombre de la huerta | Resumen + los dos botones | Sí |
| 6 | Botón **Sí, guarde** | `ONBOARDING_GUARDADO`; se crea la fila de `huerta` | Sí (`interactive`) |

**El paso 4 es obligatorio siempre.** `onboarding._atender_barrio` pasa a
`PASO_BARRIO_OPCIONES` en cuanto encuentra candidatos, incluso si hay uno
solo: nunca da el barrio por resuelto sin que ella elija el número. Quien
midiera la secuencia mínima en 4 mensajes contaría como error un paso que
el diseño impone.

### T2 — registro de cultivos (CU3 conversacional)

**2 mensajes de ella.** Uno contando qué sembró → el bot propone
`Esto es lo que entendí:` con los dos botones → botón **Sí, guarde** →
`REGISTRO_GUARDADO`. Precondición: tener huerta; si no, responde
`REGISTRO_SIN_HUERTA`.

### T3 — consulta agroecológica (CU2)

**1 mensaje de ella.** La pregunta; el bot responde en la misma pasada.

---

## 5. Mensajes de error del bot

Los tres grupos **no se pueden sumar**: el prompt pide contar «mensajes de
fallback o error» en Ef-3-G, y mezclarlos mediría tres cosas distintas.

### 5.1 No entendió a la usuaria — sí son error (Ef-3-G)

| Constante | Marca en el texto | Tarea |
|---|---|---|
| `ONBOARDING_NOMBRE_REINTENTO` | `no le entendí el nombre` | T1 |
| `ONBOARDING_BARRIO_REINTENTO` | `no le entendí el barrio` | T1 |
| `ONBOARDING_BARRIO_SIN_CANDIDATOS` | `No encontré ese barrio en mi lista` | T1 |
| `ONBOARDING_NUMERO_NO_ENTENDIDO` | `No entendí.` | T1 |
| `ONBOARDING_HUERTA_REINTENTO` | `no le entendí el nombre de la huerta` | T1 |
| `REGISTRO_NADA_QUE_ANOTAR` | `no le entendí bien qué sembró` | T2 |
| `REGISTRO_SIN_BORRADOR` | `ya no tengo a la mano lo que iba a guardar` | T2 |
| `REGISTRO_SIN_HUERTA` | `Antes de anotar lo que sembró necesito unos datos` | T2 |
| `AUDIO_NO_ENTENDIDO` | `no logré entender la nota de voz` | **Invisible**: se envía sin recordarse |

La repetición de la pregunta sin disculpa también es un reintento: al
**primer** fallo del nombre o de la huerta el backend repite la pregunta
tal cual, y solo al segundo pide perdón. Se detecta por dos preguntas
iguales seguidas del asistente.

### 5.2 Falló el sistema — no son error de ella

`ORIENTACION_NO_DISPONIBLE`, `MI_HUERTA_NO_DISPONIBLE`,
`COMUNIDAD_NO_DISPONIBLE`, `REGISTRO_FALLO`, `ONBOARDING_FALLO`,
`AGENTE_NO_DISPONIBLE` y `SERVICIO_NO_DISPONIBLE` (este último tampoco se
recuerda). Van en una columna aparte: cuentan contra el sistema, no contra
la usabilidad de la tarea.

### 5.3 Respondió bien que no tiene el dato — no son error

`ORIENTACION_SIN_RESPALDO` es el **tercer nivel de la jerarquía de
fuentes** (`CLAUDE.md` §6), no un fallback de comprensión: el bot
responde, y sin citar a nadie. Igual `COMUNIDAD_SIN_ESE_CULTIVO`,
`COMUNIDAD_SIN_HUERTAS`, `MI_HUERTA_SIN_CULTIVOS` y
`MI_HUERTA_SIN_REGISTRO`. Contarlos como error castigaría al sistema por
hacer lo correcto. Se reportan aparte, como cobertura del corpus.

---

## 6. Cómo se distingue una consulta agroecológica (T3)

Por las marcas de la respuesta, en este orden:

| Marca en la respuesta del asistente | Vía |
|---|---|
| Empieza un párrafo por `Fuente:` | CU2 **con cita**: la pone el backend, y solo si el modelo dice haber usado el contexto (ADR-0025) |
| `De eso no le puedo responder con seguridad` / `no se lo puedo asegurar` | CU2 **sin respaldo oficial** |
| Cualquiera de las marcas del CU3, CU4, CU5, CU6, CU7 o CU8 | **No** es T3 |

**Y aquí está el hueco serio de toda la medición.** Cuando el agente no
llama a ninguna herramienta, `agente.atender` envía el texto que escribió
el modelo **sin marca ninguna**, saltándose el CU2 entero: sin RAG, sin
cita y sin advertencia médica. Está registrado como **INC-025** y es el
riesgo **P-05** del plan de pruebas. Esas consultas son indistinguibles,
por texto, de cualquier otra charla.

Propuesta en D-3.

---

## 7. Decisiones que necesitan su aprobación

No las resuelvo yo: la regla 2 del prompt dice que si una definición no se
puede aplicar con el esquema real, hay que detenerse y reportarlo.

| # | Asunto | Qué propongo |
|---|---|---|
| **D-1** | **Cuál de las 17 es su fila.** La base no tiene marca que lo diga. El prompt quería excluir al desarrollador | Dígame el seudónimo. Mientras no lo diga, calculo sobre 17 y el informe da **los dos denominadores** |
| **D-2** | **T1 completo.** El prompt pide la conjunción de nombre + barrio + nombre de huerta. Pero el nombre se guarda en la **primera** pregunta, y el barrio y la huerta se crean **juntos** al final: la conjunción se reduce a «existe la fila de `huerta`» | Definir `completo_T1` = existe fila en `huerta`. Son **15 de 17**. `nombre_usuario_cifrado` pasa a ser el paso «nombre» del embudo, que es donde sirve |
| **D-3** | **Intento de T3.** Por marcas se cuenta de menos, por INC-025 | Dos columnas: `T3_confirmada` (con marca del CU2) y `T3_candidata` (mensaje de ella cuya respuesta no lleva ninguna marca conocida, y que no es un paso del onboarding ni un botón). La segunda la revisa usted leyendo el CSV: son pocas decenas de mensajes |
| **D-4** | **Qué cuenta como error en Ef-3-G**, dados los tres grupos del §5 | Contar solo el §5.1. El §5.2 en `fallos_sistema` y el §5.3 en `sin_respaldo`, columnas aparte |
| **D-5** | **Arranque de Ey-1-G en T1.** El primer mensaje de ella no existe | Arrancar en `usuario.consentimiento_en`, que es el instante en que pulsó «Acepto», y declararlo. Mide el onboarding, no la autorización |
| **D-6** | **Ef-4-G y Ef-5-G.** El prompt las pide en el informe (§7.5) y **no las define** en ninguna parte | O me da la definición, o las omito y lo digo en el informe. No las invento |

### 7.1 Una nota sobre la hipótesis

La hipótesis del documento, textual, dice:

> «…completen sin asistencia al menos el 80 % de las tareas de **consulta
> agroecológica y registro de su huerta**.»

Son **T3 y T2**. El prompt del análisis habla de «T1, T2 y T3». Voy a
calcular las tres, pero el **Ef-1-G global que contrasta la hipótesis se
reportará sobre T2 y T3**, y T1 aparte como contexto del embudo. Si quería
que T1 también entrara en la hipótesis, hay que cambiar la redacción del
documento, no la del informe.

### 7.2 La asistencia

Usted dijo que la gran mayoría lo hizo sola y que unas dos personas
pidieron ayuda, y que eso lo resuelve con la otra parte de la encuesta.
La columna `asistencia` queda vacía en el CSV para que la llene por
seudónimo. **Sin ella, Ef-1-G no es «sin asistencia»** y la hipótesis no
queda contrastada: el informe lo dirá en esos términos hasta que las dos
o tres celdas estén puestas.

---

## 8. Privacidad de las salidas

Las conversaciones se analizan completas, sin anonimizar de más: las
usuarias autorizaron el tratamiento. Lo que **no** autorizaron es la
publicación, y este repositorio es público, así que:

| Archivo | Destino | Por qué |
|---|---|---|
| `analisis/sql/*.sql`, `mapeo_esquema.md`, `informe_preliminar.md`, `embudo_onboarding.csv`, `parametros.json` | **Versionados** | Solo conteos, fechas y seudónimos. Mismo criterio que `scripts/registro_aceptacion.py` |
| `intentos_tareas.csv`, `consultas_T3.csv`, `tiempos_respuesta_sistema.csv` | **`.gitignore`** | Llevan el `identidad_hash` o texto literal de la conversación, con su nombre de pila dentro (INC-026) |

---

## 9. Anomalías encontradas en la Fase 1

| Observación | Cantidad | Lectura |
|---|---|---|
| Usuarias que dieron su nombre y no completaron el onboarding | 2 (P-05, P-06) | P-06 coincide en fecha con la usuaria que abandonó porque su barrio no estaba en la lista (ADR-0024). Sin comprobar que sea ella |
| Usuarias con huerta y **cero** cultivos | 6 de 15 | Es lo normal desde el ADR-0016: el onboarding crea la huerta sin cultivos |
| Filas de idempotencia sin procesar | 0 | Ningún mensaje quedó a medias |
| `onboarding_pendiente` y `registro_pendiente` vacías | — | Nadie tiene un flujo abierto; y no queda rastro de dónde se atascaron P-05 y P-06 |
| Mensajes sin timestamp, o usuarias duplicadas | 0 | `creado_en` es `NOT NULL` y `identidad_hash` es único |
| Zonas horarias | Coherentes | Todo es `timestamptz`; se convierte a `America/Bogota` solo al reportar |

Ninguna se corrigió: la regla 6 del prompt pide reportarlas.

---

## 10. Qué sigue

Con D-1 a D-6 resueltas: un único script reproducible
(`python -m scripts.evaluacion_formativa`, para respetar la convención del
proyecto en lugar de `analisis/run.py`) que regenera desde cero las seis
salidas del §6 del prompt y deja cada consulta en `analisis/sql/`.
