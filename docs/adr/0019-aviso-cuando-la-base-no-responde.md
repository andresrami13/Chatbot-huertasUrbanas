# ADR-0019. Cuando la base no responde, se reintenta y se le avisa a la usuaria

- **Estado:** Aceptada. La decisión 5 se escribió y se retiró el mismo
  día; ver la revisión al final
- **Fecha:** 2026-09-08
- **Fase:** 7
- **Origen:** sin respaldo documental

## Contexto

Trazando los caminos de fallo del sistema apareció un caso que ninguna fase
contempla y que el código no atendía: **qué ve la usuaria cuando la
infraestructura no está.**

Hay dos escenarios y conviene separarlos, porque no son el mismo problema.

### El backend caído

Meta hace `POST /webhook` y no hay nadie. No recibe `200`, así que reintenta
la entrega. La usuaria ve su mensaje con doble chulo —lo puso el servidor de
Meta al recibirlo, no nuestro backend— y después silencio. Si el servicio
vuelve dentro de la ventana de reintentos, el mensaje se procesa tarde: la
respuesta le llega sobre una conversación que ya abandonó.

**Este ADR no se ocupa de ese caso.** Sin proceso vivo no hay nada que
programar.

### Supabase caída con el backend vivo — el caso «B2»

Es el más probable de los dos: el session pooler corta, se agotan las
conexiones, Supabase tiene una incidencia. Y es el que sí se puede atender,
porque el proceso está corriendo.

1. Llega el POST. La validación de firma es HMAC puro y no toca la base,
   así que pasa.
2. El webhook devuelve **`200`** y encola `procesar_evento`.
3. En segundo plano, `reclamar_wamid` es la **primera** consulta a Supabase
   de todo el turno, y lanza.
4. La excepción sube hasta el `except` de `procesar_evento`, se registra y
   `return`.

Resultado hasta el 08/09/2026: **silencio absoluto.** Ni respuesta, ni
disculpa, ni siquiera los puntitos de «escribiendo», porque
`marcar_escribiendo` está después del reclamo.

Y algo peor que el silencio: **el mensaje se pierde para siempre.** Meta ya
recibió su `200` en el paso 2, así que no reentrega. Como fue el propio
reclamo el que falló, tampoco queda fila en `idempotencia_webhook`, de modo
que `contar_mensajes_atascados` ni siquiera lo cuenta al arrancar. Todo
rastro es una línea de bitácora.

### Lo que el sistema sí sabía hacer, y por qué no bastaba

`app/textos.py` tiene disculpas para todo lo que falla **dentro** del
turno: `ORIENTACION_NO_DISPONIBLE`, `COMUNIDAD_NO_DISPONIBLE`,
`REGISTRO_FALLO`, `ONBOARDING_FALLO`, `AGENTE_NO_DISPONIBLE`. Todas cubren
fallos de Gemini o escrituras concretas.

**Y todas siguen llegando con la base caída**, cosa que conviene dejar
escrita porque no es evidente: se envían con `memoria.responder`, y sus
tres pasos toleran que Supabase no esté. `_con_saludo` captura su propio
fallo y devuelve el texto sin saludo, `enviar_texto` es solo httpx, y
`_recordar` se traga la excepción por decisión del ADR-0012. El mensaje
sale; lo único que se pierde es la línea de memoria.

El problema no era, por tanto, que esos textos no pudieran enviarse. Era
que **el turno no llega hasta ellos**: con Supabase caída, la primera
consulta del turno es `reclamar_wamid` y ahí se acaba todo, antes de que
exista una usuaria identificada a la que responderle.

El criterio de éxito del proyecto es un SUS ≥ 68 con usuarias de la
comunidad. Con este perfil —adultas mayores, apropiación tecnológica
limitada al uso básico del celular— el silencio es el peor resultado
posible: ella no sabe si el bot la ignoró, si escribió mal, o si el aparato
se dañó.

## Decisión 1. Se reintenta el reclamo antes de rendirse

Tres intentos: el primero sin esperar, y dos más tras **1 y 3 segundos**
(`_ESPERAS_RECLAMO` en `dispatcher.py`).

Aquí sobra el tiempo, y ese es el punto: Meta ya recibió su `200`
(ADR-0005), nadie está esperando esta tarea y el reloj no aprieta. Un corte
del pooler de Supabase suele durar segundos, así que **la mayoría de las
caídas se resuelven sin que la usuaria se entere**, que vale más que
cualquier disculpa bien redactada.

El coste en una caída real es de unos 4 segundos por mensaje antes de
disculparse. Con 5 a 7 usuarias, irrelevante.

## Decisión 2. Agotados los intentos, se le avisa con un texto propio

`SERVICIO_NO_DISPONIBLE`, nuevo en `app/textos.py`. Se rechazó reutilizar
`AGENTE_NO_DISPONIBLE` por el mismo motivo que llevó a separar los otros
cuatro: confundir las causas en la bitácora le quita a la Fase 7 el dato de
cuántos turnos se perdieron por infraestructura.

Sin tecnicismos (CLAUDE.md §11). «Base de datos» no significa nada para
ella. El texto dice las tres cosas que necesita saber: que no fue culpa
suya, que no se perdió lo que ya tenía guardado, y que vuelva a escribir.

Se envía con `whatsapp.enviar_texto`, que es **solo httpx** y no toca la
base — condición sin la cual nada de esto sería posible.

## Decisión 3. El aviso se envía y no se recuerda

Segunda **excepción declarada** al CLAUDE.md §11 después del acuse de voz
(ADR-0017, decisión 1).

Y aquí ni siquiera incomoda. La regla existe porque un envío sin registrar
deja un hueco asimétrico que el agente no puede detectar (ADR-0012): el
asistente dijo algo, ella responde a eso, y el agente lee una respuesta sin
la pregunta que la provocó. **Ese riesgo aquí no existe**, porque el fallo
ocurre en `reclamar_wamid`, que va **antes** de `recordar_usuaria`: no se
guardó el mensaje de ella ni el nuestro. La ventana se salta el turno
entero y queda coherente, que es justo lo que el ADR-0012 protege.

## Decisión 4. Va antes de la compuerta de consentimiento

El aviso se manda sin saber si ella autorizó. Es el mismo argumento con el
que el indicador de «escribiendo» ya está antes de la compuerta (ADR-0017,
revisión del 23/08, decisión B): **es un texto fijo devuelto al número que
acaba de escribir.** No lee su mensaje, no lo transcribe, no llama al
modelo y no persiste nada suyo.

No incumple el ADR-0006 ni el CLAUDE.md §4.2, que prohíben **procesar** el
mensaje de quien no ha autorizado. Queda escrito porque a primera vista
parece que choca.

## Decisión 5. Se avisa siempre, sin freno y sin estado

Cada mensaje que llegue con la base caída recibe su disculpa. El
despachador no lleva cuenta de a quién avisó ni cuándo.

**Esta decisión sustituye a la que llevaba este número**, que puso un
freno de cinco minutos por número y se retiró el mismo día. El porqué está
en la revisión del final, y merece leerse: es el defecto más instructivo
de este ADR.

El coste asumido es que una caída larga le repite la misma disculpa. Se
acepta: repetida es molesta, pero es **inequívoca**. Ella sabe que el bot
está vivo y que le dice lo mismo. El silencio, en cambio, es ambiguo, y la
ambigüedad es lo que este perfil de usuaria no puede resolver.

## La rendija que abre el reintento, y por qué se deja abierta

Es la parte que obligó a pensar y no a escribir tres líneas.

`reclamar_wamid` es una sola sentencia `insert ... on conflict do update
... where recibido_en < now() - 300s`, diseñada así para que dos entregas
del mismo mensaje no se reclamen las dos (ADR-0005). Si un intento **llega
a escribir la fila** en Supabase pero la conexión se rompe antes de que
leamos la respuesta, el intento siguiente encuentra su propia fila en
`recibido` y recién puesta. El `where` exige que hayan pasado 300 segundos
para volver a tomarla, así que no devuelve nada, y el mensaje se descarta
**como si fuera un duplicado**.

Es decir: un reintento ingenuo puede convertir un tropiezo transitorio en
una pérdida silenciosa, que es exactamente lo que este ADR viene a
arreglar.

Se acepta de todos modos, por dos razones:

1. **En ese escenario el mensaje se perdía igual antes de este ADR.** No
   empeora el resultado, solo lo deja de mejorar.
2. **Resolverlo puede salir peor.** Habría que leer la fila y decidir si es
   nuestra o de una entrega concurrente de Meta. Equivocarse ahí **le manda
   la respuesta dos veces**, y eso es peor que perder el mensaje: uno se
   puede volver a escribir, el otro ya lo leyó.

Lo que sí se hace es **no dejarlo disfrazado**: un rechazo tras un reintento
se registra con un `warning` distinto del duplicado normal, para que en la
bitácora se pueda ver la diferencia.

## Consecuencias

- La usuaria deja de quedarse en silencio cuando Supabase no responde.
- Las caídas cortas —las más frecuentes— pasan a ser invisibles para ella.
- Ningún mensaje suyo se queda sin respuesta mientras el proceso viva.
- Aparece una segunda excepción a «enviar y recordar van juntos» que hay
  que conocer antes de tocar `memoria.py`.
- La Fase 7 gana un dato que no tenía: la bitácora distingue ahora el fallo
  de infraestructura del fallo del modelo, y cuenta los reintentos que
  salvaron un turno.
- Un texto nuevo, dos funciones privadas en el despachador y cuatro líneas
  cambiadas en `_procesar_mensaje`.

## Lo que este ADR NO resuelve

- **El mensaje se sigue perdiendo.** Ella sabrá que vuelva a escribir, que
  es mucho más que antes, pero **quien reintenta es ella, no el sistema.**
  Cerrar eso exige tocar el contrato con Meta —devolver algo distinto de
  `200` cuando la base no responde, o encolar el trabajo fuera del proceso—
  y es una decisión de otro tamaño.
- **La afirmación del ADR-0005 sobre la recuperación queda matizada.** El
  despachador dice que si el trabajo falla «la fila se deja en `recibido` y
  al vencer el plazo el reintento de Meta lo vuelve a tomar». Eso **solo
  ocurre si Meta no recibió el `200`**, y el webhook lo devuelve siempre en
  cuanto la firma es válida y el cuerpo parsea. Ningún fallo de
  procesamiento provoca reentrega, así que esas filas se quedan en
  `recibido` sin que nadie las vuelva a tomar. Queda anotado en el
  docstring de `_procesar_mensaje` y **sin resolver**.
- **Solo se cubre `reclamar_wamid`.** Si la base se cae más adelante —en la
  compuerta, en el onboarding, al confirmar un registro— vuelve el silencio.
  Se dejó fuera a propósito: una red alrededor de `_atender_mensaje` entero
  arriesga el **mensaje doble**, porque para entonces el flujo pudo haberle
  enviado ya una respuesta, y haría falta llevar cuenta de si se envió algo
  en el turno.
- **Las esperas de 1 y 3 segundos no están medidas.** Salen de que un
  corte de pooler dura segundos, no de una observación de los cortes
  reales de Supabase. A diferencia del resto de lo calibrable (CLAUDE.md
  §8) todavía no son variables de entorno, porque no hay ninguna medición
  que ajustar.
- **Una caída larga le repite la misma disculpa** por cada mensaje. Es la
  consecuencia aceptada de la decisión 5, no un descuido.
- **Si el texto suena bien de verdad.** Está en registro bogotano y con
  trato de usted, pero eso lo confirma una usuaria, no el autor.

## Alternativas descartadas

- **Comprobar la base antes de empezar** con `comprobar_conexion()`. Mete un
  `select 1` a cada mensaje para cubrir un fallo raro, y es intrínsecamente
  condenada a la carrera: puede pasar y la base caerse un milisegundo
  después. No elimina la necesidad del `try`, así que paga un coste
  permanente sin cerrar el hueco.
- **Una red alrededor de `_atender_mensaje`.** Cubriría todos los fallos y
  no solo los de la base, pero arriesga contradecir una respuesta ya
  enviada. Es la extensión natural de este ADR cuando haga falta, y
  entonces habrá que resolver antes lo del mensaje doble.
- **Distinguir la causa por tipo de excepción** —infraestructura frente a
  error de programación— para no decirle «vuelva a intentarlo» ante un
  fallo que reintentar no arregla. Correcto en principio y prematuro hoy:
  el único fallo posible en `reclamar_wamid` es de infraestructura, porque
  es una sentencia SQL sin lógica. Empieza a hacer falta con la alternativa
  anterior.
- **Mover `marcar_escribiendo` antes del reclamo**, para que al menos vea
  los puntitos. No informa del fallo, y una reentrega de Meta los mostraría
  dos veces. Serviría de complemento, no de sustituto.

## Cómo se comprobó

Sin tocar Supabase ni Meta: `reclamar_wamid` y `enviar_texto` sustituidos
por dobles dentro del módulo, y credenciales ficticias para que ni por
accidente pudiera autenticarse contra nada. Siete escenarios, todos
pasando:

| Escenario | Esperado | Medido |
|---|---|---|
| La base responde | 1 reclamo, 0 avisos | ✔ |
| Duplicado real | 1 reclamo, 0 avisos | ✔ |
| Falla 1 vez y se recupera | 2 reclamos, **0 avisos**, ~1 s | ✔ 1,01 s |
| B2: fallan los tres | 3 reclamos, 1 aviso, ~4 s | ✔ 4,02 s |
| Vuelve a escribir enseguida | **aviso, nunca silencio** | ✔ |
| Insiste una tercera vez | aviso otra vez | ✔ |
| Estado guardado del aviso | ninguno | ✔ |

**Falta la comprobación que de verdad cuenta**, y es la de siempre en este
proyecto (CLAUDE.md §12): reproducir las condiciones de producción. Esto se
midió contra dobles, no contra una Supabase caída de verdad ni desde un
celular. La forma de hacerlo es apuntar `DATABASE_URL` a un puerto muerto y
mandar un WhatsApp.

---

## Revisión del 08/09/2026: el freno se retira el mismo día

La decisión 5 original ponía un **freno de cinco minutos por número**: se
avisaba una vez y los mensajes siguientes dentro de esa ventana no recibían
nada. Duró lo que tardó en leerse en voz alta.

### El defecto

El texto que enviamos **le pide que vuelva a escribir**. La usuaria que
obedece cae dentro de la ventana y recibe **silencio por hacer lo que le
pedimos**. Es decir: el freno reintroducía exactamente el silencio que este
ADR existe para quitar, y lo reintroducía en el caso más probable de todos.

Y la deja peor que si nunca le hubiéramos hablado. El primer silencio era
ambiguo —quizá no llegó el mensaje—; el segundo, después de una instrucción
explícita, solo se puede leer como que el bot se dañó de verdad.

### Por qué se coló

El freno se diseñó pensando en **la usuaria que insiste enfadada**, a la
que cinco párrafos idénticos le confirman que el bot se rompió. No se pensó
en **la usuaria que obedece**, que es la que el texto está fabricando.

### Por qué el problema que atajaba no existía

Lo señaló el autor al revisarlo: **pasadas dos veces sin respuesta útil, la
usuaria deja de escribirle al bot.** Las cinco disculpas seguidas eran un
escenario de laboratorio. El freno pagaba un daño real y frecuente —el
silencio a quien obedece— para evitar un daño hipotético.

### Qué queda

Se avisa siempre. Fuera `_ULTIMO_AVISO`, `_SILENCIO_AVISO_SEGUNDOS`, la
poda del diccionario y los imports de `time` y `calcular_telefono_hash`,
que dejaron de usarse. El despachador no guarda ningún estado del aviso.

Se estudió una tercera vía —**variar el texto** en lugar de callar, como
hacen las seis frases barajadas del acuse de voz (ADR-0017, decisión 6)— y
se descartó por innecesaria una vez visto que el escenario que la
justificaba no ocurre. Queda anotada por si la primera prueba con celular
dice otra cosa.

### Lo que vale como lección, más allá de este ADR

**Un mecanismo de protección puede reintroducir el daño del que protege.**
El freno se escribió tres párrafos después del texto que lo contradice, en
la misma sesión y por la misma persona, y ninguno de los dos se leyó junto
al otro. Cuando el sistema le pide algo a la usuaria, hay que comprobar que
el sistema esté preparado para que ella lo haga.
