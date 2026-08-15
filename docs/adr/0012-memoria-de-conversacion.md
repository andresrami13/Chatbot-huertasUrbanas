# ADR-0012. La memoria de conversación empieza después de la compuerta, y el `wamid` sale de `mensaje`

- **Estado:** Aceptada
- **Fecha:** 2026-08-15
- **Fase:** 6 (prepara el agente orquestador)
- **Depende de:** [ADR-0005](0005-procesamiento-asincrono-e-idempotencia.md),
  [ADR-0006](0006-saludo-y-ayuda-sin-modelo.md)

## Contexto

La Fase 3 declara la tabla `mensaje` y la Fase 4 §6 fija una ventana de
diez mensajes, pero ningún documento dice **qué mensajes entran, quién los
escribe ni qué pasa con lo que ya se sabe del `wamid`**. Hasta ahora daba
igual: la tabla existía desde `001` y nada escribía en ella. El agente la
enciende.

Al ir a encenderla aparecen tres cuestiones que las fases no resuelven, y
una deuda que llevaba abierta desde el 30/07/2026.

## Decisión 1. `mensaje.wamid` pasa a `huella_wamid`

`db/001_esquema.sql` declaraba `wamid text unique`, en claro. Es anterior
al hallazgo del 30/07/2026: **el `wamid` contiene el número de teléfono del
remitente** en ASCII, recuperable con un `base64 -d`. Una columna de
`wamid` es una columna de teléfonos.

En la bitácora y en la idempotencia eso se corrigió entonces. Aquí no,
porque era inocuo: nadie escribía en la tabla. Deja de serlo ahora, y sería
la peor de las tres versiones del mismo fallo —permanente y una fila por
mensaje—.

[`db/006_memoria_mensaje.sql`](../../db/006_memoria_mensaje.sql) la
sustituye por la huella, con la misma forma que
`idempotencia_webhook.wamid_huella`. **Con esto no queda ninguna columna
`wamid` en el esquema.**

### El `unique` obligaba a un segundo cambio

La restricción no es decorativa, pero tal cual estaba habría introducido un
fallo nuevo. La garantía del [ADR-0005](0005-procesamiento-asincrono-e-idempotencia.md)
es **al menos una vez**: si el proceso muere entre el final del trabajo y
`marcar_procesado`, Meta reintenta y el mismo mensaje se procesa dos veces.
Un `insert` a secas chocaría entonces con el índice único y tumbaría el
reintento entero —justo la rama que el ADR-0005 existe para proteger—. La
escritura lleva por tanto `on conflict do nothing`.

De ahí se sigue que la fila de la asistente **no puede llevar la misma
huella** que la de la usuaria. Lleva la del `wamid` **saliente**, que el
cliente de WhatsApp ya devolvía y se descartaba, y nulo si el envío falló.
Consecuencia deliberada: si hay reproceso, la memoria muestra una pregunta
y dos respuestas, que es exactamente lo que la usuaria vio en su teléfono.

## Decisión 2. El contenido se guarda sin cifrar

`mensaje.contenido` va en claro, como la información agronómica y al
contrario que `nombre_usuario` (Fase 3, §5.2).

Motivos:

1. **Es lo que la Fase 3 establece.** Solo obliga a cifrar el nombre y el
   teléfono. Cifrar aquí sería añadir una protección que ningún documento
   pide.
2. **La Fase 7 necesita leerlo.** Medir qué preguntan las usuarias, cuánta
   voz usan y qué no supo responder el bot se hace con consultas sobre esta
   tabla. Cifrado, cada análisis exigiría un script que descifre.
3. **Se descifraría en cada turno de todos modos**, diez filas por mensaje,
   y la clave está en el mismo proceso: la protección real que añadiría es
   frente a un volcado de la base, no frente a nada más.

**El límite hay que declararlo, porque es nuevo.** Ninguna fase lo
anticipó: `mensaje.contenido` es el primer y único sitio donde el texto
libre de la usuaria queda guardado de forma permanente. Ella puede contar
ahí lo que quiera —un nombre, una dolencia, dónde vive— sin que el sistema
se lo haya pedido, y eso queda en claro en la base. La minimización de la
Fase 3 §5.6 (sin cédula, sin dirección) se refiere a lo que el sistema
**pide**; no puede gobernar lo que la usuaria decide escribir.

No cambia lo que ya declara el sistema —el operador tiene las claves en
tiempo de ejecución y los mensajes viajan en claro por los servidores de
Meta (CLAUDE.md §7)—, pero conviene que el documento de grado lo diga con
estas palabras y no se apoye solo en «los datos personales van cifrados».

## Decisión 3. La memoria empieza después de la compuerta

Se registra a partir del punto en el que la compuerta devuelve una usuaria.
No entra nada de antes:

- **La solicitud de consentimiento y la bienvenida previa no son memoria.**
  En ese momento no hay `usuario_id`, y no lo hay porque no hay
  consentimiento (CU1).
- **Del rechazo no queda rastro**, conforme al
  [ADR-0003](0003-consentimiento-sin-insistencia.md).
- **El texto de aceptación tampoco entra.** Podría —la fila ya existe—,
  pero abriría la conversación con un turno del asistente sin pregunta
  delante. La memoria empieza en la primera cosa que ella dice ya
  autorizada.

Que la única forma de escribir sea una función que exige `usuario_id` no es
casualidad: hace que saltarse la compuerta requiera inventarse un
identificador que no existe.

**Y va después de la transcripción**, no antes: el audio se guarda ya
convertido en texto. Es la misma normalización única de CLAUDE.md §4.4, y
evita que el agente tenga que distinguir entre lo escrito y lo hablado. La
columna `tipo` conserva de todos modos cómo llegó, que es el dato que la
Fase 7 necesita.

Si la transcripción falla no se registra nada, ni la disculpa: una
respuesta sin la pregunta que la provocó confunde más de lo que aporta.

## Decisión 4. Enviar y recordar van juntos

[`app/services/memoria.py`](../../app/services/memoria.py) expone
`responder`, que envía y registra en una sola llamada, y los flujos
posteriores a la compuerta la usan en lugar de `enviar_texto`.

Es una invariante, no una comodidad: si cada flujo enviara por su cuenta y
recordara aparte, tarde o temprano alguno enviaría sin recordar. El agente
vería entonces una conversación con huecos **que no puede detectar** —una
pregunta suya sin respuesta parece una pregunta sin contestar— y repetiría
lo que ya dijo. Antes de la compuerta se sigue usando `enviar_texto`
directamente, y es correcto: allí no hay nada que recordar.

Un fallo al escribir en la memoria **no propaga**. Cuando ocurre, el
mensaje ya se envió; propagarlo dejaría la fila de idempotencia en
`recibido`, Meta reintentaría y la usuaria recibiría la misma respuesta dos
veces. Perder una línea de memoria es más barato, y queda en la bitácora.

## Decisión 5. La ventana son diez mensajes, y el último es el de ahora

`MEMORIA_VENTANA_MENSAJES = 10` en [`app/config.py`](../../app/config.py),
variable de entorno con valor por defecto en código por el mismo criterio
que los umbrales del RAG ([ADR-0010](0010-umbral-de-similitud-recalibrado.md)):
la Fase 4 lo declara calibrable y cambiarlo no invalida nada de lo
guardado, solo cuánto se lee.

**Se cuentan mensajes, no turnos** —diez son unos cinco intercambios—, y el
mensaje entrante se registra **antes** de atenderlo. Así la ventana termina
siempre en lo que la usuaria acaba de decir, que es exactamente la forma en
la que se le entrega la conversación al modelo: no hay que sacar el mensaje
en curso de la lista ni pasarlo aparte.

## Consecuencias

- Queda cerrado el último resto del hallazgo del 30/07/2026. Ninguna tabla
  ni ninguna línea de bitácora contiene ya un `wamid`.
- `mensaje` es la sexta tabla del esquema que se escribe, y la primera cuyo
  contenido es texto libre de la usuaria.
- **No se limpia por antigüedad**, al contrario que `idempotencia_webhook`
  y `registro_pendiente`. La ventana lee solo diez filas, así que crecer no
  la degrada, y la Fase 7 necesita el historial completo. Si tras la Fase 8
  el histórico dejara de hacer falta, el descarte por antigüedad es el sitio
  evidente.
- El agente de la Fase 6 recibe la memoria ya construida: solo tiene que
  leer la ventana.

## Alternativas descartadas

- **Cifrar `contenido` con AES-GCM.** Coherente con que el texto libre
  puede traer datos personales, pero descifraría diez filas en cada turno y
  dejaría el análisis de la Fase 7 sin poder hacerse con una consulta. La
  protección que añade es solo frente al volcado de la base.
- **Registrar la memoria dentro del cliente de WhatsApp.** Cerraría el
  hueco de la decisión 4 sin tocar los flujos, pero el cliente no sabe de
  quién es la conversación —ni debe— y mezclaría el canal con la
  persistencia.
- **Leer la ventana antes de registrar el mensaje entrante.** Obligaría a
  pasar el mensaje en curso por separado en todas partes, para el mismo
  resultado.
- **Guardar también los mensajes previos al consentimiento sin
  `usuario_id`.** Sería una tabla de mensajes de gente que no ha
  autorizado, que es lo que el CU1 prohíbe.
- **Conservar `wamid` en claro «solo para trazabilidad».** Es el
  razonamiento que el ADR-0005 ya intentó y que el hallazgo del 30/07
  desmontó: el `wamid` es él mismo un identificador del remitente.
