# ADR-0017. El aviso de espera se envía y no se recuerda

- **Estado:** Aceptada **solo para la nota de voz**. El aviso del camino
  con RAG se puso y se retiró el mismo día; ver la revisión al final
- **Fecha:** 2026-08-18
- **Fase:** 7
- **Origen:** sin respaldo documental

## Contexto

El camino con RAG tarda unos **13 segundos**, medidos desde la prueba con
celular real. Son tres llamadas encadenadas: el agente decide la ruta, la
recuperación busca en las nueve fuentes, y una segunda pasada por el modelo
redacta la respuesta. Con nota de voz hay una cuarta por delante, la
transcripción.

Trece segundos de silencio no son un detalle de rendimiento con este perfil
de usuaria. Ella no sabe si el mensaje salió, si llegó, o si el bot se dañó,
y la reacción natural en WhatsApp es volver a escribir. Cada reenvío es un
`wamid` nuevo, así que la idempotencia del
[ADR-0005](0005-procesamiento-asincrono-e-idempotencia.md) no lo evita: son
mensajes distintos y se atienden los dos.

Ninguna fase documentada contempla el caso. La Fase 3 §2 describe el
procesamiento asíncrono desde el lado del webhook —responder `200` rápido
para que Meta no reintente— y no desde el lado de la usuaria, que es quien
espera de verdad.

## Decisión 1. El aviso se envía con `whatsapp.enviar_texto`, no con `memoria.responder`

Es una **excepción declarada** al CLAUDE.md §11, que obliga a que después de
la compuerta enviar y recordar vayan juntos.

Esa regla existe porque un envío sin registrar deja en la memoria un hueco
que el agente no puede detectar
([ADR-0012](0012-memoria-de-conversacion.md)): el asistente dijo algo, la
usuaria responde a eso, y el agente lee una respuesta sin la pregunta que la
provocó. **Ese riesgo aquí no existe**, porque el aviso no dice nada a lo
que ella pueda responder ni que el agente vaya a necesitar después.

Recordarlo, en cambio, sí haría daño y es medible. La ventana son diez
mensajes, no diez turnos. Un intercambio normal gasta dos —la pregunta de
ella y la respuesta— y con el aviso gastaría tres. La memoria útil pasaría
de cinco intercambios a poco más de tres, y un tercio de lo que el agente
lee sería «deme un momentico».

## Decisión 2. Solo se avisa en los caminos lentos

No todos los caminos llaman al modelo, y de los que lo llaman no todos
tardan:

| Camino | Tiempo | ¿Avisa? |
|---|---|---|
| Agente → CU2 o CU4, con recuperación | ~13 s | **Sí** |
| Audio → transcripción → agente → … | más | **Sí** |
| Agente → `mostrar_ayuda`, texto fijo | ~2-3 s | No |
| Onboarding, paso del barrio | ~2-3 s | No |
| Compuerta, botones del CU3 | sin modelo | No |

Un aviso en un camino rápido llega pegado a la respuesta, y dos mensajes
seguidos en un segundo no se leen como atención sino como que el bot se
trabó. El aviso solo compensa cuando hay silencio que llenar.

## Decisión 3. Dos disparadores, porque los dos caminos se saben en momentos distintos

Es la parte que obligó a un diseño y no a una línea:

- **Que el mensaje sea audio** viene en el propio webhook. Se sabe en el
  primer instante, y la transcripción tarda por sí sola.
- **Que el mensaje vaya al RAG lo decide el agente**, y su llamada al modelo
  gasta justamente esos dos o tres segundos. En el segundo 2 todavía no se
  sabe.

De ahí que `dispatcher` arme el aviso de audio antes de transcribir, y que
`agente` arme el del RAG al enrutar a `consultar_orientacion` o
`consultar_comunidad`. **Un aviso por mensaje:** un audio que además va al
RAG manda solo el de la voz, que es el que ya salió.

## Decisión 4. El umbral se cuenta desde que entró el mensaje

`ESPERA_AVISO_SEGUNDOS`, por defecto **2.0**, medido desde que el mensaje
entra por el webhook y no desde que se supo que iba a tardar. Variable de
entorno, como el resto de lo calibrable (CLAUDE.md §8).

El umbral hace dos cosas, y la segunda no es obvia: además de retrasar el
aviso, lo **suprime** cuando el turno entero termina antes. Un turno de 1.9
segundos no avisa nunca, aunque alguien lo hubiera programado. Eso apareció
probando, en un escenario que se dio por fallido hasta mirar los tiempos.

## Decisión 5. El estado viaja en un `ContextVar`

El aviso lo arma el despachador y lo dispara el agente, dos módulos
separados por una cadena de llamadas que no tiene nada que ver con esto.
Pasar un objeto de mano en mano por `dispatcher → agente → orientacion`
habría ensuciado tres firmas.

`contextvars` es lo que asyncio tiene para exactamente este caso: estado por
petición, propagado dentro de la tarea que atiende ese mensaje y aislado
entre mensajes concurrentes.

## Decisión 6. Las frases se reparten barajadas, no sorteadas

Diez frases para el camino con RAG y seis para el de audio, en
`app/textos.py`. Con un sorteo simple, una de cada diez veces le llegaría
dos veces seguidas la misma frase, que es justo lo que delata a una máquina.

Se reparten barajadas y sin repetir hasta agotar la tanda. **Con la primera
versión eso no bastaba:** al barajar de nuevo, la primera de la tanda podía
coincidir con la última de la anterior, y la repetición ocurría igual. Salió
en la prueba, sobre tres frases. Ahora esa coincidencia se manda al fondo.

El estado de la baraja es del proceso y no de la usuaria. En Railway corre
una sola instancia y dos usuarias comparten la baraja, lo que da igual
—ninguna ve lo que le llega a la otra— y evita una tabla para esto.

El emoji sí es siempre el mismo: ⏳ en las diez del RAG. Es lo que hace
reconocer el aviso de un vistazo sin leerlo. Las de audio llevan 🎤 y no ⏳
a propósito: lo que más tranquiliza ahí no es «espere», es saber que la nota
de voz sí llegó.

## Consecuencias

- La usuaria deja de esperar en silencio en los dos caminos largos.
- La memoria del agente no se entera de que el aviso existió.
- Aparece una excepción al CLAUDE.md §11 que hay que conocer antes de tocar
  `memoria.py`: no toda respuesta se recuerda.
- Un módulo nuevo, `app/services/espera.py`, y tres líneas repartidas entre
  el despachador y el agente.
- La Fase 7 gana un dato: la bitácora registra cada aviso enviado y con qué
  camino, que es una medida indirecta de cuánto tarda cada uno.

## Lo que este ADR no resuelve

- **La rendija de la cancelación.** Si la respuesta sale justo mientras el
  aviso está viajando, pueden cruzarse y ella lee «deme un momentico»
  después de la respuesta. Es cuestión de milisegundos y no rompe nada, pero
  existe.
- **Si dos segundos son los correctos.** El número sale de que el agente
  tarda eso en decidir, no de una medición sobre usuarias. Queda para
  calibrar en la Fase 7, y por eso es variable de entorno.
- **Si las frases suenan bien de verdad.** Están escritas en registro
  bogotano popular y con trato de usted, pero eso lo confirma una usuaria,
  no el autor.

## Alternativas descartadas

- **El indicador de «escribiendo…» de la Cloud API.** Sería lo natural: sin
  mensaje extra, sin memoria y sin doble notificación. **No se verificó
  contra la documentación vigente**, así que no se da por existente. Y
  aunque exista, los tres puntitos son sutiles para una usuaria que no está
  pendiente de la pantalla; serviría de complemento, no de reemplazo.
- **Avisar siempre, sin umbral.** Cinco líneas en vez de un módulo, pero
  manda un mensaje de más en los caminos de dos segundos.
- **Un solo disparador al recibir el mensaje.** Es lo que se pidió primero.
  No se puede: en el segundo 2 aún no se sabe si el mensaje va al RAG,
  porque quien lo decide es el agente.
- **Guardar el aviso en la memoria y filtrarlo al leerla.** Deja la decisión
  repartida en dos sitios, y la ventana de diez seguiría contándolo salvo
  que también se filtre en la consulta. Más piezas para el mismo efecto.

## Revisión del 18/08/2026: el aviso del RAG se retira

Probado desde el celular el mismo día, **la conversación se sintió más
lenta con el aviso que sin él** y se quitó. Queda solo el acuse de la nota
de voz.

**El aviso no añadía tiempo de reloj.** Sale en una tarea aparte
(`asyncio.create_task`), así que la respuesta no lo espera. Lo que cambió
no fue la duración sino la percepción: un mensaje que dice «deme un
momentico» **marca el comienzo de la espera** y la vuelve algo que se
mide, cuando antes era un rato indefinido en el que ella podía estar
haciendo otra cosa. Trece segundos anunciados se hacen más largos que
trece segundos sin anunciar.

Eso vale como hallazgo de la Fase 7 y no como fracaso de la implementación,
porque es justo lo que no se podía saber sin un teléfono. La decisión 2
—avisar solo en los caminos lentos— resulta ser más restrictiva de lo que
se creyó: **el camino con RAG tampoco lo quería.**

Qué queda en pie y qué no:

| | |
|---|---|
| Decisión 1, enviar sin recordar | **Vigente**, ahora para el acuse de voz |
| Decisión 2, solo caminos lentos | **Vigente y más estrecha**: solo el audio |
| Decisión 3, dos disparadores | **Retirada.** Queda uno, y se sabe en el webhook |
| Decisión 4, umbral de 2 s | **Retirada.** `ESPERA_AVISO_SEGUNDOS` sale de `config.py`: para un acuse que confirma la recepción, esperar es lo contrario de lo que se busca |
| Decisión 5, `ContextVar` | **Retirada.** Sin dos disparadores no hay estado que cruzar entre módulos |
| Decisión 6, frases barajadas | **Vigente** para las seis de voz; las diez del RAG salen de `textos.py` |

El acuse de la nota de voz se conserva porque **hace otra cosa**: no pide
paciencia, confirma que el audio llegó. Ahí el mensaje aporta información
que ella no tiene por ningún otro medio, y por eso se manda ya sin esperar
ningún umbral.

**Lo que este ADR deja abierto sigue abierto**, menos lo de los dos
segundos, que dejó de tener sentido. En particular, el indicador de
«escribiendo…» de la Cloud API vuelve a ser la alternativa que habría que
verificar si el silencio del camino con RAG se quiere resolver: no manda
ningún mensaje, así que no marca el comienzo de la espera como lo hacía
este.
