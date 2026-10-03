# Prueba formativa de usabilidad

| | |
|---|---|
| **Identificador** | `EVF-CHU-001`, versión 1.1 |
| **Emite** | Andrés Ramírez — autor del trabajo de grado |
| **Aprueba** | A. Ramírez — autor. **Única autoridad de aprobación** (desviación D-9 de la [política de pruebas](pruebas/politica-y-practicas-de-prueba.md)) |
| **Estado** | Vigente. Medición cerrada |
| **Fecha** | 02/10/2026 |
| **Instantánea de los datos** | 28/09/2026 21:27 (Bogotá) = `2026-09-29T02:27:05Z` |
| **Se regenera con** | `python -m scripts.evaluacion_formativa` |

## Historial de cambios

| Fecha | Versión | Cambio | Autor |
|---|---|---|---|
| 28/09/2026 | 1.0 | Versión inicial, con 17 participantes | A. Ramírez |
| 02/10/2026 | 1.1 | Cinco correcciones de una revisión metodológica: **(1)** se excluye la cuenta del autor y el universo pasa a 16; **(2)** la hipótesis cubre las tres tareas y se fija la regla de decisión antes de ver los resultados; **(3)** el diseño se declara como **una sola** ronda, formativa, con el SUS dentro de ella; **(4)** T2 y T3 dejan de medirse por participante —eran circulares— y pasan a medirse por intento y por consulta, con clasificación humana de lo que cada persona quería; **(5)** se calculan Ef-4-G y Ef-5-G, se reescribe H-8 sin juicios de valor, se transcribe el texto real de autorización en un anexo y se adopta lenguaje neutro de género | A. Ramírez |

---

# 1. Introducción

Este documento presenta la **prueba formativa de usabilidad** del prototipo
de chatbot de huertas urbanas: su diseño, sus medidas, sus resultados y los
problemas de usabilidad que los datos sugieren.

Responde al **cuarto objetivo específico** del trabajo de grado —«evaluar la
usabilidad del prototipo mediante una prueba formativa con usuarios de la
comunidad, midiendo eficacia, eficiencia y satisfacción (SUS) conforme a la
ISO/IEC 25022»— y aporta la evidencia con la que se contrasta la
**hipótesis**:

> El prototipo de agente conversacional basado en inteligencia artificial en
> WhatsApp permite que los líderes de huertas urbanas de la UPZ 84 Bosa
> Occidental participantes en la evaluación formativa completen sin
> asistencia al menos el 80 % de las tareas de registro inicial
> (onboarding), registro de cultivos y consulta agroecológica.

Cubre **la eficacia y la eficiencia**, que es lo que los registros del
sistema pueden medir. La **satisfacción** se mide dentro de esta misma
evaluación con el cuestionario SUS, por llamada, y se integrará en una
versión posterior de este documento. La **corrección agronómica** de las
respuestas la calificó una persona con una rúbrica, y el §7 explica cómo.

Es **formativo**: su propósito es identificar qué ajustar. Por eso el §9
enumera hallazgos como indicios y no como conclusiones.

**No hay una segunda ronda sumativa.** El diseño es de una sola evaluación.

## 1.1 Relación con los demás documentos

| Documento | Qué aporta |
|---|---|
| [`docs/pruebas/`](pruebas/) | El proceso de prueba conforme a ISO/IEC/IEEE 29119. La aceptación (`RAC-CHU-001`) mide **si cada caso de uso se ejerció**; esta prueba mide **con qué eficacia y eficiencia** |
| [`docs/pruebas/banco-de-preguntas.md`](pruebas/banco-de-preguntas.md) | La calidad de la respuesta del CU2 sobre un banco de 40 preguntas escritas para probar. Aquí las preguntas son las **reales** de quienes usaron el prototipo |
| [`docs/adr/`](adr/) | Las veintiséis decisiones de implementación que explican por qué los datos son como son |
| [`analisis/salidas/mapeo_esquema.md`](../analisis/salidas/mapeo_esquema.md) | El punto de control de la Fase 1: qué columna representa cada concepto y qué no se puede medir |

---

# 2. Marco normativo

| Norma | Uso en esta prueba |
|---|---|
| **ISO/IEC 25022:2016** | Medidas de calidad en uso: Ef-1-G (completitud), Ef-3-G (errores), Ef-4-G e Ef-5-G (frecuencia de error) y Ey-1-G (tiempo de la tarea) |
| **ISO/IEC 25010** | Características de calidad en uso a las que se adscribe cada medida: eficacia y eficiencia |
| **ISO/IEC 25020:2019** | Marco de medición: cada medida se documenta con su función de medición, sus elementos de medida (QME), su método y su fuente de datos (§6) |
| **ISO/IEC 25023** | PTb-1-G, tiempo de respuesta del sistema |

## 2.1 Adaptaciones declaradas

**AD-1. No hay tareas asignadas ni sesiones observadas.** ISO/IEC 25022
supone que se le pide a la persona participante ejecutar una tarea y se la
observa. Aquí las dieciséis participantes le escribieron por su cuenta al
número de producción desde sus celulares, sin protocolo y sin nadie
presente. La consecuencia es que el denominador de Ef-1-G **no es «cuántas
veces se le pidió que lo hiciera» sino «cuántas veces decidió hacerlo»**.

Se acepta a propósito, por la razón que el §3 de
[`docs/ESTADO.md`](ESTADO.md) ya había argumentado: los registros del
sistema no dependen de que la persona recuerde ni de su cortesía con quien
le construyó la herramienta. Y es coherente con el perfil de la comunidad,
que una sesión de laboratorio observada distorsionaría.

**AD-2. La guía de observación del anteproyecto se sustituye por el análisis
de los registros del sistema.** Es observación de lo que pasó, no de lo que
el autor creyó ver estando presente. Hay que declararlo en
[`docs/correcciones-a-los-documentos.md`](correcciones-a-los-documentos.md).

**AD-3. Dos juicios de esta medición los emitió el autor, no un instrumento.**
La clasificación de lo que cada persona quería (§7, C-4) y el dato de
asistencia (§8.1) no salen de la base: los declaró el autor. Ambos están
fechados y con su procedencia escrita, porque el resultado global queda
exactamente sobre el umbral de la hipótesis y cualquiera de los dos lo
mueve.

---

# 3. Diseño de la evaluación

## 3.1 Las tres tareas

| Tarea | Qué hace la persona participante | Casos de uso | Unidad de medida |
|---|---|---|---|
| **T1** | Autoriza el tratamiento de sus datos y da su nombre, su barrio y el nombre de su huerta | CU1 + CU6 | **Participante** |
| **T2** | Registra qué tiene sembrado | CU3 | **Intento de registro** |
| **T3** | Pregunta algo de agroecología y recibe respuesta | CU2 | **Consulta** |

**La hipótesis cubre las tres.** La regla de decisión quedó fijada **antes
de conocer los resultados**: la hipótesis se sostiene *en la muestra* si
**Ef-1-G global ≥ 0,80**, donde el global es ΣA ÷ ΣB sumando los intentos de
las tres tareas y contando en A solo lo completado **sin asistencia**. El
resultado se reporta además por tarea, para que una con muchos intentos no
oculte a otra.

**T2 y T3 no se miden por participante, y esa es la corrección de fondo de
esta versión.** Medirlas así las volvía circulares; el §7, C-4 lo explica.

### Secuencia mínima de cada tarea

Derivada del código, no estimada. Es el denominador de Ey-5-S.

| Tarea | Mínimo de mensajes | Detalle |
|---|---|---|
| T1 | **6**, de los que quedan registrados **5** | Botón «Acepto» · nombre · barrio · número de la lista de barrios · nombre de la huerta · botón «Sí, guarde» |
| T2 | **2** | Un mensaje contando qué sembró · botón «Sí, guarde» |
| T3 | **1** | La pregunta |

El cuarto paso de T1 —elegir el número de una lista— **es obligatorio
siempre**: `onboarding._atender_barrio` muestra la lista en cuanto encuentra
candidatos, incluso si hay uno solo. Quien contara la secuencia mínima en
cuatro mensajes reportaría como error un paso que el diseño impone.

La pulsación de «Acepto» no queda registrada, porque se atiende antes de la
compuerta de consentimiento y no se recuerda (ADR-0012). Numerador y
denominador se comparan sobre lo que sí queda: cinco.

## 3.2 Participantes

**Dieciséis personas** que autorizaron el tratamiento de sus datos entre el
09 y el 27/09/2026, escribiéndole al número de producción desde sus propios
celulares. Son la población completa que usó el prototipo, no una muestra:
no se aplicó ningún criterio de selección.

**Se excluye una fila, la cuenta del autor**, identificada por su
`identidad_hash`, que el autor calculó con su propia clave y entregó. Es
**P-12**, y la exclusión se aplica antes de calcular cualquier medida. **Los
seudónimos no se reasignaron**: P-12 deja un hueco en la numeración para que
sigan coincidiendo con los del [registro de
aceptación](pruebas/registro-de-aceptacion.md), donde `P-01` a `P-11` son
las mismas personas.

**Son dieciséis y no las cinco a siete que preveía el anteproyecto.** El
número de producción está abierto desde el 09/09/2026 y le puede escribir
cualquiera.

**No todas las personas participantes son mujeres.** La documentación del proyecto
habla de «las usuarias» como supuesto, y los datos lo desmienten: entre las
dieciséis hay al menos un hombre. Este documento usa «participante» y
«persona participante» en todas partes, y la corrección debería bajar
también a `CLAUDE.md` y al documento de grado.

## 3.3 Recolección de datos

Los registros del propio sistema, en las tablas `usuario`, `huerta`,
`cultivo` y `mensaje` de la base de producción. **No se instrumentó nada
para esta evaluación**: se analiza lo que el prototipo ya guardaba para
funcionar, que es la memoria de conversación del agente (ADR-0012).

**Ninguna evaluación la pide el propio bot.** Preguntar dentro de la
herramienta que se evalúa sesgaría la respuesta.

Los datos se congelaron en una **instantánea**: solo se consideran los
mensajes anteriores al instante registrado en
`analisis/salidas/parametros.json`. La instantánea **no filtra
participantes**: entran las dieciséis.

## 3.4 Lo que esta prueba no mide, y quién lo mide

| Fuera de alcance de este documento | Dónde se mide |
|---|---|
| Satisfacción | Cuestionario SUS por llamada, dentro de esta misma evaluación formativa |
| Utilidad percibida y adopción declarada | Fuera del alcance de la ISO/IEC 25022 |

## 3.5 Datos personales

Las personas participantes autorizaron el tratamiento de sus datos, y la
existencia
de su fila en `usuario` *es* esa autorización (CU1, ADR-0003). **El texto
exacto que vieron está transcrito en el anexo 12.3**, con la advertencia de
que no fue el mismo para todas y de qué finalidades menciona y cuáles no.

La autorización no cubre la publicación. El repositorio del proyecto es
público, así que las salidas se separan:

| Salida | Versionada | Por qué |
|---|---|---|
| Este documento, `mapeo_esquema.md`, `embudo_onboarding.csv`, `parametros.json`, `categorias_propuestas.json`, `rubrica_respuestas.json`, las consultas SQL | **Sí** | Solo conteos, fechas, seudónimos `P-01`…`P-17` e identificadores |
| `clasificacion_mensajes_libres.csv`, `rubrica_T3.csv`, `intentos_tareas.csv`, `tiempos_respuesta_sistema.csv`, `asistencia.csv`, `candidatas_sus.csv` | **No** (`.gitignore`) | Llevan texto literal de la conversación o la huella de identidad abreviada. `mensaje.contenido` va sin cifrar y contiene el nombre de pila (INC-026) |

Es el mismo criterio que separa `scripts/registro_aceptacion.py`, cuya
salida sí puede ir al repositorio, de `scripts/revisar_prueba_real.py`, cuya
salida no sale de la terminal.

### Anonimización de los textos exportados

Los textos que salen a los CSV llevan tapado, con `[DATO_PERSONAL]`: el
nombre de pila, el barrio y el nombre de la huerta —estos dos últimos
tomados del catálogo y de la base, no de lo que la persona tecleó, porque el
backend los repite normalizados—, las direcciones y las secuencias de siete
dígitos o más. **Nada se descifra**: el nombre se recoge de lo que la propia
persona escribió en el onboarding, que queda en claro en `mensaje`
(INC-026).

Dos reglas se añadieron tras encontrar fugas reales, y quedan declaradas
porque describen el límite del método: se tapan también las **subcadenas de
dos palabras o más** del nombre —el modelo se dirige a una participante con
dos de las tres palabras que esa persona escribió— y **cualquier nombre que siga a
un tratamiento de cortesía** («doña», «don», «señora»). Las palabras sueltas
no se tapan a propósito: borrar una sola palabra eliminaría especies como
«rosa» y estropearía la clasificación.

---

# 4. Instrumentación y trazabilidad

| Activo | Qué es |
|---|---|
| [`scripts/evaluacion_formativa.py`](../scripts/evaluacion_formativa.py) | Script único que regenera todas las salidas desde cero. **Solo lee**: no ejecuta ninguna escritura contra la base |
| [`analisis/sql/`](../analisis/sql/) | Las cuatro consultas, una por archivo, con la medida que alimenta cada una |
| [`analisis/salidas/`](../analisis/salidas/) | Las salidas: el mapeo, las hojas de clasificación y rúbrica, los intentos, los tiempos, el embudo y los parámetros |

Todo número de este documento se puede rastrear hasta una de esas consultas,
hasta el catálogo de marcas del script, o hasta una de las dos hojas que
llenó una persona. La instantánea y los parámetros viven en un archivo
aparte para que dos ejecuciones den el mismo resultado.

## 4.1 Cómo se sabe qué tarea se atendió

**`mensaje` no guarda qué herramienta respondió**, y no existe ninguna
columna de intención, de caso de uso ni de clasificación. El camino que el
sistema tomó se deduce de las **marcas de los textos que compone el
backend**, que es el mismo método de `scripts/registro_aceptacion.py`.

Las marcas son fragmentos estables y no el texto entero, porque varios
textos cambiaron de redacción de un ADR a otro y **los mensajes viejos
guardan la versión de su día**. El §7 recoge lo que costó pasar por alto
eso.

**Pero el camino que el sistema eligió no dice qué quería la persona**, y
esa distinción es la que obliga a la clasificación humana del §7, C-4.

---

# 5. Lo que los registros no pueden dar

Cuatro huecos, todos consecuencia de decisiones documentadas. Se declaran
antes de los resultados porque condicionan cómo se leen.

1. **El primer mensaje de cada participante no existe.** Todo lo anterior a
   la compuerta de consentimiento se envía sin recordarse (ADR-0012): el
   saludo, la bienvenida, la solicitud de permiso y la pulsación de
   «Acepto». La primera fila de `mensaje` de cualquiera es la primera
   pregunta del onboarding. Por eso **el tiempo de T1 arranca en
   `usuario.consentimiento_en`** y el primer paso del embudo no se mide.
2. **Los pasos intermedios del onboarding no son columnas.** La fila de
   `huerta` se crea entera al pulsar el botón final, y
   `onboarding_pendiente` se borra al completar y caduca a las 24 horas: de
   quienes abandonaron **no queda estado**, solo sus mensajes. El embudo se
   reconstruye por marcas de texto.
3. **Cinco envíos no se recuerdan** a propósito: el acuse de la nota de voz
   (ADR-0017), el saludo personalizado (ADR-0016), el aviso de base caída
   (ADR-0019), la disculpa cuando no se entiende un audio, y todo lo
   anterior a la compuerta. Un hueco en `mensaje` **no prueba silencio**.
4. **El texto guardado no es exactamente el que la persona vio.**
   `memoria.responder` antepone el saludo personalizado a lo que envía y
   guarda el cuerpo sin él. La diferencia es una línea con su nombre.

---

# 6. Definiciones operativas de las medidas

## Ef-1-G — Completitud de la tarea

| | |
|---|---|
| **Característica** | Eficacia en uso (ISO/IEC 25010) |
| **Norma de origen** | ISO/IEC 25022:2016 |
| **Función de medición** | X = A / B |
| **QME** | A = intentos completados sin asistencia · B = intentos |
| **Método** | Indirecto, sobre los registros del sistema, con clasificación y rúbrica humanas |
| **Fuente** | `usuario`, `huerta`, `cultivo`, `mensaje`, más `clasificacion_mensajes_libres.csv`, `rubrica_T3.csv` y `asistencia.csv` |
| **Adaptación** | AD-1 y AD-3 del §2.1 |

**Intento (B) y completitud (A), por tarea:**

| Tarea | Unidad | Intento | Completado |
|---|---|---|---|
| T1 | Participante | Envió al menos un mensaje | Existe su fila en `huerta` |
| T2 | Intento de registro | Un episodio de registro, segmentado según el §6.1 | El episodio cerró con «ya quedó guardado» **y** se persistió al menos un cultivo **dentro de ese intento** |
| T3 | Consulta | Un mensaje libre posterior al onboarding que una persona clasificó como consulta agroecológica, **sin importar a qué camino lo llevó el sistema** | La rúbrica aprobó la respuesta: **contestó lo que se preguntó** y **lo que dice es cierto** |

En las tres, un intento **no cuenta en A si la persona recibió asistencia**.

**T1 completado es la fila de `huerta`, y no la conjunción de tres campos.**
El nombre se persiste cifrado en la *primera* de las tres preguntas
(`onboarding._atender_nombre`), así que `nombre_usuario_cifrado` no prueba
que el onboarding terminara; el barrio y el nombre de la huerta se escriben
**juntos** al pulsar el botón del cierre. El nombre pasa a ser un paso del
embudo, que es donde informa.

**En T3 lo que se mide es si la persona consiguió lo que buscaba, no por
dónde pasó la respuesta.** Una respuesta redactada por el modelo sin
recuperación cuenta como completada si la rúbrica la aprueba. El camino se
registra aparte y se reporta como hallazgo del sistema.

## 6.1 Segmentación de los intentos de registro (T2)

Un intento **abre** con el mensaje de la persona cuya respuesta trae una de
las tres salidas de `registrar_huerta`: la propuesta de registro, «no le
entendí qué sembró» o «necesito unos datos de su huerta».

**Cierra** en el primero de estos cuatro: confirmación de guardado;
descarte, o confirmación sin borrador que confirmar; pausa mayor que
`UMBRAL_PAUSA_MIN`; o cambio de tarea, es decir, una respuesta de otro caso
de uso.

Un reintento tras un «no le entendí qué sembró» **pertenece al mismo
intento** mientras no ocurra ninguno de los cuatro cierres, y sus errores se
cuentan en él.

**Una decisión declarada:** hay una «confirmación sin borrador» huérfana
—alguien pulsó el botón de un mensaje viejo, cuyo borrador ya había
caducado— que **no abre intento**, porque no hay mensaje de la persona que
lo abra. El autor decidió el 02/10/2026 **no contarla**, antes de conocer el
resultado global. Conviene saber que esa decisión sostiene el número: si se
contara como intento fallido, el global sería 40/51 = 0,78 en vez de 0,80.
Se deja escrito para que se vea que no se eligió el criterio conveniente.

## Ef-3-G — Errores en la tarea

| | |
|---|---|
| **Característica** | Eficacia en uso |
| **Norma de origen** | ISO/IEC 25022:2016 |
| **Función de medición** | Conteo por intento |
| **QME** | Mensajes en que el bot declara no haber entendido · correcciones de un dato ya dado · mensajes repetidos literalmente en menos de dos minutos |
| **Método** | Indirecto, por marcas de texto |
| **Fuente** | `mensaje` |

Los textos del backend se reparten en **tres grupos que no se pueden
sumar**, y solo el primero cuenta como error:

| Grupo | Ejemplos | ¿Es error? |
|---|---|---|
| No entendió | «no le entendí el barrio», «no encontré ese barrio en mi lista», «no le entendí bien qué sembró» | **Sí** |
| Falló el sistema | «no pude consultar la información», «no pude guardar la información» | No: cuenta contra el sistema, en columna aparte |
| Respondió bien que no tiene el dato | «de eso no le puedo responder con seguridad» | No: es el tercer nivel de la jerarquía de fuentes (`CLAUDE.md` §6). Contarlo castigaría al sistema por hacer lo correcto |

Los duplicados que reintenta Meta **no llegan a `mensaje`**: la idempotencia
por huella del `wamid` los descarta antes (ADR-0005), comprobado en la
instantánea con cero filas sin procesar. Así que «mensaje repetido» mide que
**la persona** repitió, no que el canal reintentó.

## Ef-4-G — Intentos con error

| | |
|---|---|
| **Característica** | Eficacia en uso |
| **Norma de origen** | ISO/IEC 25022:2016 |
| **Función de medición** | X = intentos con al menos un error ÷ intentos |
| **QME** | Los errores de Ef-3-G |
| **Método** | Indirecto, por marcas de texto |

## Ef-5-G — Participantes con error

| | |
|---|---|
| **Característica** | Eficacia en uso |
| **Norma de origen** | ISO/IEC 25022:2016 |
| **Función de medición** | X = participantes con al menos un error ÷ participantes que intentaron la tarea |
| **QME** | Los errores de Ef-3-G, agrupados por persona |
| **Método** | Indirecto, por marcas de texto |

**En T1 la unidad de medida ES la participante**, así que Ef-4-G y Ef-5-G
coinciden por construcción. Solo se separan en T2 y T3.

## Ey-1-G — Tiempo de la tarea

| | |
|---|---|
| **Característica** | Eficiencia en uso |
| **Norma de origen** | ISO/IEC 25022:2016 |
| **Función de medición** | Instante final − instante inicial |
| **QME** | T1: `usuario.consentimiento_en` → «ya quedó guardada su huerta». T2: el mensaje que abre el intento → su cierre. T3: la pregunta → la respuesta |
| **Método** | Directo, sobre `mensaje.creado_en` |
| **Interrumpido** | Alguna pausa de más de 10 minutos entre dos mensajes consecutivos del intento |

## PTb-1-G — Tiempo de respuesta del sistema

| | |
|---|---|
| **Característica** | Eficiencia de desempeño — comportamiento temporal |
| **Norma de origen** | ISO/IEC 25023 |
| **Función de medición** | Instante del saliente − instante del entrante |
| **QME** | Un par por cada mensaje de la persona participante |
| **Método** | Directo |
| **Reserva** | El entrante se registra **antes** de atenderlo y el saliente **después** de enviarlo (`memoria.responder`), así que la medida incluye una escritura en base: es una **cota superior** del tiempo percibido |

## Ey-5-S — Razón de mensajes

Mensajes de la persona en el intento ÷ mínimo necesario según el §3.1. Se
calcula solo sobre los intentos completados.

---

# 7. Correcciones de medición

Se registran porque dos de ellas estuvieron a punto de entrar al documento
de grado como resultados, y porque son el tipo de error que el §12 de
`CLAUDE.md` obliga a no dar por bueno a la primera.

**C-1. Una marca de texto desactualizada dio cero donde hay cuatro.** La
primera corrida reportó **0 respuestas del CU2 sin respaldo oficial**,
cuando las hay. El texto `ORIENTACION_SIN_RESPALDO` cambió de redacción y
los mensajes de septiembre guardan la versión de su día: faltaba la
alternativa «no se lo puedo asegurar». Se detectó **porque contradecía otro
documento del proyecto**, no porque el número pareciera raro.

**C-2. Los errores de T2 se contaban en un solo intento.** Daban cero
mientras el registro de aceptación contaba un registro descartado y una
confirmación sin borrador, que caían en intentos posteriores.

**C-3. En T3 se confundían «cuántas consultas hizo» con «cuántos mensajes
por intento».** Inflaba Ey-5-S a 2,00 cuando por construcción vale 1,00.

**C-4. T2 y T3 se medían por participante, y eso las volvía circulares.** Es
la corrección de fondo de la versión 1.1. En la 1.0, el intento de T3 se
detectaba **por la respuesta del CU2** y «completada» era que el bot hubiera
respondido: la misma evidencia en el numerador y en el denominador, así que
la proporción no podía bajar del 100 % y daba 9/9. T2 era casi igual, y daba
10/10. Ninguno de los dos números significaba nada.

La corrección tiene tres partes:

- **La unidad cambia**: T2 se mide por intento de registro y T3 por
  consulta, no por persona.
- **El denominador deja de depender del sistema**: una consulta es un
  mensaje que **una persona clasificó** como consulta agroecológica,
  cualquiera que fuera el camino que el sistema eligió.
- **El numerador deja de ser «respondió»**: una consulta se completa si la
  rúbrica aprueba la respuesta.

Con eso T2 pasó de 10/10 a **12/14 intentos** y T3 de 9/9 a **14/20
consultas**.

**Procedencia de la clasificación, que hay que declarar:** la propuso la IA
sobre los 50 mensajes libres y la validó el autor el 02/10/2026, revisando y
aprobando las cinco filas que la IA marcó como dudosas y aceptando las 45
restantes sin objeción. **No es una clasificación hecha desde cero por una
persona**, y presentarla como tal sería falso. La propuesta quedó congelada
en `categorias_propuestas.json` y la calificación de la rúbrica en
`rubrica_respuestas.json`, las dos versionadas, para que la comparación sea
auditable.

**C-5. Se excluye la cuenta del autor.** Las 17 filas de `usuario` incluían
una del propio autor, que en la versión 1.0 no se pudo identificar —la base
no tiene marca que lo diga— y por eso se midió sobre las 17, declarándolo
como limitación. En la 1.1 el autor entregó su `identidad_hash`, calculado
con su propia clave; resultó ser **P-12**, justamente la fila que el
registro de aceptación ya señalaba como sospechosa por coincidir con la
verificación del ADR-0025. El universo queda en 16 y los seudónimos no se
reasignan.

**Dos cifras redactadas de memoria** no resistieron la comprobación contra
los CSV y se corrigieron antes de publicar la versión 1.0: nueve de quince
completaron el onboarding en el mínimo exacto —no once—, y las consultas sin
clasificar se repartían en seis participantes —no ocho—.

---

# 8. Resultados

## 8.1 Universo

| | |
|---|---|
| Filas en `usuario` | 17 |
| **Excluidas** | **1 — P-12, cuenta del autor** |
| **Participantes** | **16** |
| Rechazos de la autorización | **0 registrables.** El ADR-0003 prohíbe persistir el rechazo: no es que nadie rechazara, es que no queda constancia |
| Rango de los mensajes | 09/09/2026 10:41 a 28/09/2026 07:28 (Bogotá) |
| Mensajes | 356 en la base; 162 pares pregunta-respuesta de las 16 |
| Notas de voz | 9, de 2 participantes |
| Mensajes libres tras el onboarding | **50** |
| Huertas / cultivos | 15 / 77 en la base |

**Asistencia recibida: ninguna.** El autor declaró el 02/10/2026 que las 16
usaron el prototipo por su cuenta. Una estimación previa de ese mismo día
hablaba de unas dos personas; se registra el cambio porque el resultado
global queda exactamente sobre el umbral y este dato lo mueve. Verificado
en 16 de 16 filas de `asistencia.csv`.

## 8.2 Ef-1-G

| Tarea | Unidad | B | A | Proporción | Estado |
|---|---|---|---|---|---|
| T1 autorización y onboarding | participantes | 16 | 14 | **14/16** | asistencia verificada |
| T2 registro de cultivos | intentos | 14 | 12 | **12/14** | asistencia verificada |
| T3 consulta agroecológica | consultas | 20 | 14 | **14/20** | asistencia verificada, con rúbrica |
| **Global** | mixta | **50** | **40** | **40/50 = 0,80** | **contrastado** |

**La hipótesis se sostiene en la muestra, exactamente en el umbral y sin
margen.** La regla de decisión pedía ≥ 0,80 y el resultado es 0,80: **un
intento en cualquier dirección la cambia**.

Esa fragilidad es, en sí misma, un resultado. Con 50 intentos y un umbral
del 80 %, la diferencia entre sostener la hipótesis y no sostenerla cabe en
un intento, y el §10 recoge las tres decisiones de medición que la mueven.
Dice más sobre el tamaño de la muestra que sobre el prototipo.

### Qué quería cada persona y a dónde la llevó el sistema

De los **50 mensajes libres** posteriores al onboarding:

| Qué quería | → CU2 | → CU3 | → ayuda | → texto libre del modelo | Total |
|---|---|---|---|---|---|
| Consulta agroecológica | **20** | 0 | 0 | **0** | 20 |
| Registro de cultivos | 0 | **16** | 0 | 0 | 16 |
| Otra cosa | 2 | 0 | 2 | **10** | 14 |

**El enrutamiento no falló ni una vez** en los 36 mensajes que pedían algo.

## 8.3 Ef-3-G, Ef-4-G y Ef-5-G

| Tarea | Unidad | Intentos | Errores | Ef-4-G | Ef-5-G | Fallos del sistema |
|---|---|---|---|---|---|---|
| T1 | participante | 16 | **19** | 6/16 | 6/16 | 0 |
| T2 | intento | 14 | 2 | 2/14 | 2/10 | 0 |
| T3 | consulta | 20 | 0 | 0/20 | 0/8 | 0 |

Los 19 errores de T1 se concentran en 6 participantes: nueve en una sola,
cuatro en otra, tres en quien abandonó, y uno en cada una de las otras tres.
Las diez restantes no tuvieron ninguno.

Los 2 errores de T2 son los dos intentos que cerraron en descarte. En T3 no
hay errores por construcción: la tarea es un solo mensaje y el bot nunca
declaró no entenderla.

**Cero fallos del sistema** en los tres casos.

## 8.4 Ey-1-G, tiempo de la tarea

En segundos.

| Tarea | Unidad | n | Mediana | Mín | Máx | Sin intentos interrumpidos |
|---|---|---|---|---|---|---|
| T1 | participante | 14 | 175,5 | 69,0 | 51 566,6 | n=12 · mediana 151,7 |
| T2 | intento | 14 | 14,7 | 8,9 | 278,4 | n=14, sin cambio |
| T3 | consulta | 20 | 13,8 | 11,4 | 15,8 | n=20, sin cambio |

**Dos intentos interrumpidos, los dos en T1.** Uno duró 14,3 horas —empezó
una noche y terminó a la mañana siguiente— y otro 18,5 minutos. Sin ellos,
el onboarding completo se resuelve en una mediana de **2 min 32 s**.

El máximo de T2, 278 s, es el intento de varios turnos descrito en el §9,
H-5.

## 8.5 PTb-1-G, tiempo de respuesta del sistema

**162 pares.** Media 4,1 s · mediana 1,4 s · percentil 90 12,7 s · máximo
**16,7 s**.

El agregado esconde poblaciones muy distintas; por separado sí describen
algo:

| Lo que respondió el sistema | n | Mediana | p90 | Máx |
|---|---|---|---|---|
| Onboarding (texto fijo, sin modelo) | 97 | 0,9 s | 5,0 s | 15,2 s |
| CU3 registro (extrae a temperatura 0.1) | 31 | 4,0 s | 8,7 s | 16,7 s |
| **CU2 (recupera y redacta)** | 22 | **13,3 s** | 15,2 s | 15,8 s |
| Texto libre del modelo | 10 | 3,0 s | 5,5 s | 5,6 s |
| Otros textos del backend | 2 | 3,8 s | 5,2 s | 5,6 s |

## 8.6 Ey-5-S, razón de mensajes

| Tarea | Mínimo | n | Mediana | Máx |
|---|---|---|---|---|
| T1 | 5 | 14 | **1,00** | 3,40 |
| T2 | 2 | 12 | 1,00 | 1,00 |
| T3 | 1 | 14 | 1,00 | 1,00 |

**Ocho de las catorce** completaron el onboarding en exactamente los cinco
mensajes mínimos. El máximo de 3,40 son diecisiete mensajes para cinco
necesarios.

En T2 y T3 la razón vale **1,00 por construcción** —el mínimo coincide con
lo que el flujo permite— y por eso no informa de nada.

## 8.7 Embudo del onboarding

| Paso | Participantes | De |
|---|---|---|
| 1. Recibió la bienvenida | **no medible** | 16 |
| 2. Aceptó la autorización | 16 | 16 |
| 3. Dio su nombre | 16 | 16 |
| 4. Llegó al barrio | 14 | 16 |
| 5. Llegó al nombre de la huerta | 14 | 16 |
| 6. Vio el resumen | 14 | 16 |
| 7. Onboarding completo | 14 | 16 |

**Todo el abandono está en un solo escalón: el barrio.** Las dieciséis
aceptaron y las dieciséis dieron su nombre; dos no pasaron de ahí, y de las
catorce que llegaron al barrio **ninguna se cayó después**.

## 8.8 Uso posterior

| | |
|---|---|
| No completaron el onboarding | **2 de 16** |
| Lo completaron y **no hicieron nada más** | **4 de 16** |
| Lo completaron y usaron el prototipo | 10 de 16 |
| Con actividad en más de un día calendario | **2 de 16** |
| Hicieron al menos una consulta agroecológica | 8 de 16 |
| Usaron el CU4, el CU7 o el CU8 | **0 de 16** |
| Entraron alguna vez por nota de voz | 2 de 16 |

## 8.9 Las 20 consultas agroecológicas

| | |
|---|---|
| Consultas | **20**, de 8 participantes |
| Pasaron por el CU2 | **20 de 20** |
| Sin respaldo oficial: responde el modelo y no cita | **4 de 20** |
| Entraron por voz | 3 de 20 |
| **Lo que dice es cierto** | **20 de 20** |
| **Contestó lo que se preguntó** | **14 de 20** |

**Ni una sola afirmación agronómica falsa en las respuestas reales.** Las
seis que no contestaron lo que se preguntó son todas del mismo tipo: cómo
hacer un atrapador de rocío, cómo condensar agua del ambiente, cuándo
aporcar y cómo saber que la remolacha está lista, cómo quemar la cascarilla,
y una mariposa que ataca la granadilla. **Son huecos de corpus, no fallos
del sistema**, y coinciden con lo que el banco de 40 preguntas ya había
medido.

## 8.10 Candidatas al SUS

**7 de 16 participantes** completaron las tres tareas según las definiciones
del §6. La lista, solo con seudónimos, está en
`analisis/salidas/candidatas_sus.csv`.

---

# 9. Hallazgos formativos

Son **indicios**, no conclusiones: dieciséis personas, ninguna sesión
observada. Cada uno dice en cuántas se observó.

**H-1. El catálogo de barrios es el único punto donde se pierde gente, y hay
evidencia directa.** Observado en 2 de 16. Las dos que abandonaron lo
hicieron en ese paso, y ninguna de las catorce que lo superó se cayó
después. **El último mensaje de una de ellas es el nombre de su barrio**, y
ese barrio no está entre las 313 filas del catálogo: es uno de los dos que
el ADR-0024 nombra como ausentes. No es una inferencia sobre por qué se fue;
es lo último que escribió. El hueco del catálogo le costó un participante al
proyecto.

**H-2. El enrutamiento no falló, y la versión 1.0 de este informe decía lo
contrario.** Observado en 36 de 36 mensajes con una petición: las 20
consultas agroecológicas fueron al CU2 y los 16 mensajes de registro al CU3.
Los 10 mensajes que el modelo contestó por su cuenta, sin pasar por ningún
caso de uso, son **agradecimientos, confirmaciones y dos peticiones al bot
sobre sí mismo** — ninguno es una consulta agroecológica.

La versión 1.0 presentó esos mensajes como la incidencia INC-025
materializándose en producción, es decir, como consultas respondidas sin
recuperación, sin cita y sin advertencia médica. **El hecho era cierto y la
lectura era falsa.** Es el error que el §12 de `CLAUDE.md` describe: un
indicador que mide lo que no es. Lo corrigió la clasificación humana, que es
exactamente para lo que hacía falta.

**H-3. Tres funciones construidas y desplegadas que nadie ha usado jamás.**
Observado en 16 de 16: **cero** mensajes enrutados al CU4, al CU7 o al CU8.
Confirma INC-027. El dato no dice que fallen; dice que **nadie descubre que
existen**, y eso sí es un hallazgo de usabilidad: las únicas vías de
descubrimiento son el texto de la bienvenida y el del cierre del registro, y
ninguno de los dos las menciona.

**H-4. Seis de dieciséis se registraron y nunca usaron la herramienta.** Dos
no completaron el onboarding y **cuatro lo completaron y no hicieron nada
más**: ni una consulta, ni un cultivo. Y de las diez que sí la usaron, solo
**dos volvieron otro día**.

Es el hallazgo más duro del informe, y conviene leerlo junto al 0,80 del
§8.2 sin que uno tape al otro: **el 0,80 dice que quien lo intenta lo
logra; este dice que más de un tercio no llega a intentarlo.** Las dos cosas
son ciertas a la vez, y presentar solo la primera daría una impresión falsa
de cómo le fue al prototipo.

**H-5. El flujo de registro funciona, y su único tropiezo es de otro tipo.**
Observado en 14 intentos: 12 terminaron guardando y 2 en descarte. **No hubo
ni un solo caso de «no le entendí qué sembró»**: la extracción nunca falló
en producción. El intento más largo —278 s, cuatro mensajes— es alguien que
dictó por voz una lista larga, añadió especies en dos mensajes más y al
final descartó el registro completo; después registró en dos intentos más,
con 18 y 8 cultivos. El descarte no fue un fallo: fue una corrección.

**H-6. Cuatro de veinte respuestas del CU2 salieron sin respaldo oficial, y
seis no contestaron lo que se preguntó.** Es la señal honesta de dónde falta
corpus. **Lo que falla no es el umbral, es la cobertura**, y coincide con lo
que el banco de 40 preguntas ya había medido.

**H-7. Ninguna respuesta del CU2 llevó advertencia médica.** 0 de 20. No es
un fallo —ninguna consulta real tocó salud—, pero deja sin comprobar en
producción el vocabulario del ADR-0015, que seguía pendiente de medir.

**H-8. Los tiempos de respuesta, sin juicio de valor.** No existe un umbral
de tiempo aceptable definido para este prototipo, así que aquí solo se
reportan los valores. Mediana de 1,4 s y máximo de 16,7 s sobre 162 pares.
**El camino del CU2 es el más lento**, con mediana de 13,3 s frente a 0,9 s
del onboarding. Definir qué tiempo es aceptable para una conversación por
WhatsApp con este perfil de usuario queda como pendiente (§11).

**H-9. El sistema no falló ni una vez.** Cero fallos de base de datos, de
modelo o de envío en los tres grupos de intentos.

---

# 10. Amenazas a la validez y limitaciones

| # | Limitación | Efecto |
|---|---|---|
| L-1 | **No es un estudio de tareas asignadas** (AD-1) | B es «cuántas decidió intentar», no «cuántas se le pidieron» |
| L-2 | **El resultado global queda exactamente sobre el umbral** | Tres decisiones de medición lo mueven: no contar la confirmación huérfana (§6.1), la clasificación de los mensajes dudosos (§7, C-4) y el dato de asistencia (§8.1). Las tres están fechadas y declaradas, y las dos primeras se tomaron antes de conocer el resultado |
| L-3 | **La clasificación la propuso la IA y la validó el autor** (§7, C-4) | No es una clasificación humana desde cero. Quedan versionados la propuesta y el criterio para que se pueda auditar |
| L-4 | **Un solo evaluador en la rúbrica** | Las columnas de un segundo evaluador quedaron sin llenar, así que no hay acuerdo entre evaluadores que reportar |
| L-5 | **El primer mensaje de cada participante no existe** | El tiempo de T1 arranca en el consentimiento y el primer paso del embudo no se mide |
| L-6 | **Cinco envíos no se recuerdan** a propósito | Un hueco en `mensaje` no prueba silencio |
| L-7 | **`onboarding_pendiente` está vacía** | De quienes abandonaron no queda estado, solo mensajes |
| L-8 | **El texto guardado no es exactamente el que la persona vio** | Diferencia de una línea con su nombre |
| L-9 | **El texto de autorización no fue el mismo para todas** | Diez vieron una versión y seis otra. Ver el anexo 12.3 |
| L-10 | **PTb-1-G incluye una escritura en base** | Es una cota superior del tiempo percibido |
| L-11 | **Muestras pequeñas**: 14, 20 y 16 según la tarea | Ningún porcentaje se reporta sin su conteo y su unidad al lado |
| L-12 | **El autor diseña, ejecuta y aprueba su propia evaluación** | Es el riesgo J-01 del plan de pruebas. No queda mitigado, y se declara |
| L-13 | Mensajes sin marca de tiempo, participantes duplicadas, zonas horarias incoherentes | **Ninguno.** `creado_en` es `NOT NULL`, `identidad_hash` es único y todo es `timestamptz` |

---

# 11. Pendientes

1. **Aplicar el SUS** por llamada a las 7 candidatas del §8.10 e integrar la
   satisfacción en este documento.
2. **Un segundo evaluador** para la rúbrica de las 20 consultas, y reportar
   el acuerdo entre ambos (L-4).
3. **Definir el umbral de tiempo de respuesta aceptable** para este canal y
   este perfil de usuario, sin el cual H-8 solo puede describir (§9, H-8).
4. **Decidir si H-2 cambia algo.** El enrutamiento no falló en producción,
   así que INC-025 no se materializó aquí; pero el riesgo P-05 sigue
   declarado y la decisión de corregirlo o no es del autor.
5. **Llevar al catálogo de barrios los dos que faltan** y medir si el
   abandono de H-1 desaparece.
6. **Hacer descubribles el CU4, el CU7 y el CU8** (§9, H-3), o declararlos
   fuera del alcance del prototipo.
7. **Declarar AD-2 en
   [`docs/correcciones-a-los-documentos.md`](correcciones-a-los-documentos.md)**:
   la guía de observación de la ronda formativa se sustituye por el análisis
   de los registros del sistema.
8. **Bajar a `CLAUDE.md` y al documento de grado el lenguaje neutro de
   género** (§3.2).

---

# 12. Anexos

## 12.1 Consultas

| Archivo | Qué calcula |
|---|---|
| [`f1_esquema.sql`](../analisis/sql/f1_esquema.sql) | Comprobación de columnas contra `information_schema`. Base del §5 |
| [`f1_universo.sql`](../analisis/sql/f1_universo.sql) | Conteos de control, ventana temporal y una fila por participante. Base del §8.1 |
| [`f2_usuarias.sql`](../analisis/sql/f2_usuarias.sql) | Universo y banderas de tabla. Alimenta Ef-1-G y el embudo |
| [`f2_conversacion.sql`](../analisis/sql/f2_conversacion.sql) | La conversación hasta la instantánea. Alimenta Ef-3-G, Ef-4-G, Ef-5-G, Ey-1-G, Ey-5-S, PTb-1-G, el embudo y las hojas |

Lo que se deriva de las marcas de texto vive en
[`scripts/evaluacion_formativa.py`](../scripts/evaluacion_formativa.py),
porque `mensaje` no guarda qué herramienta respondió y ninguna consulta SQL
puede deducirlo sola.

## 12.2 Salidas

| Archivo | Contenido | Versionado |
|---|---|---|
| `mapeo_esquema.md` | Punto de control de la Fase 1 | Sí |
| `parametros.json` | Instantánea, exclusiones y parámetros | Sí |
| `categorias_propuestas.json` | La clasificación que propuso la IA, congelada | Sí |
| `rubrica_respuestas.json` | La calificación de las 20 consultas | Sí |
| `embudo_onboarding.csv` | El embudo del §8.7 | Sí |
| `clasificacion_mensajes_libres.csv` | Los 50 mensajes libres con su categoría | No |
| `rubrica_T3.csv` | Las 20 consultas con su calificación | No |
| `intentos_tareas.csv` | Una fila por intento, con su unidad | No |
| `tiempos_respuesta_sistema.csv` | Un par por mensaje entrante | No |
| `asistencia.csv` | Asistencia recibida, por participante | No |
| `candidatas_sus.csv` | Las 7 candidatas, solo seudónimos | No |

## 12.3 El texto de autorización que vieron las personas participantes

Lo pide la revisión metodológica: el §3.5 no puede afirmar que la
autorización cubre este análisis sin mostrar qué decía. **No fue el mismo
texto para todas.** Cambió con el ADR-0024, en el commit `ea9bdb5` del
19/09/2026, y quien ya había pasado la compuerta no vuelve a verlo nunca.

**Versión vigente hasta el 19/09/2026.** Lo vieron las **diez** personas que
consintieron entre el 09 y el 18/09:

> Antes de empezar necesito su permiso.
>
> Para poder ayudarle guardo el nombre de su huerta, el barrio y lo que
> tiene sembrado. Eso se comparte con las demás huertas, para que aprendan
> unas de otras.
>
> Su número de celular y su nombre no se le muestran a nadie.
>
> ¿Me da su autorización?

**Versión vigente desde el 19/09/2026.** Lo vieron las **seis** personas que
consintieron el 23 y el 27/09:

> Antes de empezar le cuento qué soy: un asistente en pruebas, hecho como
> trabajo de grado de la Universidad Distrital. Todavía me equivoco y hay
> cosas que no sé.
>
> Para ayudarle guardo el nombre de su huerta, el barrio y lo que tiene
> sembrado, y eso se comparte con las demás huertas para que aprendan unas
> de otras.
>
> Su número de celular y su nombre no se le muestran a nadie.
>
> ¿Me da su autorización?

**Qué menciona cada una, sin interpretarlo jurídicamente:**

| | Hasta el 19/09 | Desde el 19/09 |
|---|---|---|
| Finalidad declarada | Ayudarle y compartir el dato agronómico con otras huertas | La misma |
| Fin académico o de investigación | **No lo menciona** | Dice que es un **trabajo de grado de la Universidad Distrital** |
| Análisis de las conversaciones | **No lo menciona** | **No lo menciona** |
| Mejora del servicio | **No lo menciona** | **No lo menciona** |
| Responsable del tratamiento | No lo identifica | Identifica a la Universidad Distrital |
| Que es un prototipo en pruebas | No lo dice | Lo dice |

**Ninguna de las dos versiones menciona que las conversaciones se vayan a
analizar.** La segunda sí identifica el contexto académico y al responsable.
La fecha del cambio y quién vio cada versión se derivan del historial de
git y de la fecha de consentimiento de cada fila; la fecha de despliegue
exacta del commit no se puede reconstruir a posteriori, así que el reparto
10/6 supone que se desplegó antes del 23/09.
