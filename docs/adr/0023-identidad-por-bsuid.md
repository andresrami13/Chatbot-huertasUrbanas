# ADR-0023. La identidad de la usuaria es el BSUID, no su teléfono

- **Estado:** Aceptada
- **Fecha:** 2026-09-17
- **Fase:** 7
- **Origen:** sin respaldo documental — corrige la Fase 3, §5 y el
  «identidad por número de celular» que el CLAUDE.md §4.8 daba por
  decidido

## Contexto

**Personas nuevas le escribían al bot y no recibían absolutamente nada.**
En la bitácora de Railway quedaba una sola línea:

    Mensaje sin remitente; se descarta

Eran **8 de unos 69 mensajes (12 %)**, todos de tipo texto, **ninguno
anterior al 15/09/2026**, y con el mismo despliegue corriendo desde el
10/09. Ningún cambio de código lo provocó: cambió lo que manda Meta.

La causa es que **Meta dejó de mandar `from` —el teléfono— y manda
`from_user_id`**, que es un **Business-Scoped User ID (BSUID)**: un
identificador de la usuaria propio de este portafolio de negocio. Llega
con los nombres de usuario de WhatsApp, y en cuanto ella activa el suyo,
su número desaparece del webhook.

El despachador identificaba a la usuaria por `mensaje["from"]` y, sin él,
descartaba el mensaje antes de la compuerta. Para ella eso no era un
error: era silencio.

### Lo que dice la documentación oficial

De [Business-scoped user IDs][doc]:

> BSUIDs will be **prefixed with the user's ISO 3166 alpha-2 two-letter
> country code and a period, followed up to 128 alphanumeric characters**
> (for example, `US.13491208655302741918`).

> BSUID will be assigned to the `user_id` parameter and appear in **all
> messages webhooks, regardless of whether or not the user has enabled
> the username feature**.

> BSUIDs will be **regenerated if a user changes their phone number**
> (which triggers a system messages webhook).

Y para responderle:

> set `recipient` to the user's BSUID or parent BSUID — omit the `to`
> property

[doc]: https://developers.facebook.com/documentation/business-messaging/whatsapp/business-scoped-user-ids/

### Lo que está comprobado contra producción, no supuesto

Medido el 17/09/2026 con el commit `55e5a4d` desplegado, que registraba
los **nombres** de los campos del webhook —nunca sus valores—:

- `from_user_id` llega **junto a** `from`, no en su lugar:
  `campos=['from', 'from_user_id', 'id', 'text', 'timestamp', 'type']`
- El mismo BSUID llega además en el bloque de contactos:
  `campos_contacto=['profile', 'user_id', 'wa_id']`
- Cuando falta el teléfono, el mensaje llega así:
  `campos=['from_user_id', 'id', 'text', 'timestamp', 'type']`
- El campo `messages` del webhook está en **v26.0** desde el 17/09. La
  variable `META_GRAPH_VERSION` de Railway ya valía v26.0 y **no hay que
  tocarla**: solo arma las URL de salida.
- De los diez campos suscritos —`messages`, `calls`, los dos de
  plantilla, los cuatro de cuenta y número, y `security`—, **ninguno
  salvo `messages` envía `messages[]`**.

**Salvedad honesta, y es la que explica media decisión:** son **dos**
mensajes medidos. Confirman la **forma** del webhook, no que el BSUID
venga siempre. Por eso la resolución de identidad lleva respaldo y se
cuenta en la bitácora.

## Decisión

### 1. La identidad es el BSUID, para todas

Tengan nombre de usuario o no. **El teléfono no se guarda nunca más, ni
hasheado.**

No es solo arreglar el 12 %: es una mejora de la minimización de la
Fase 3, §5. El sistema pasa a no conservar ninguna forma —ni siquiera
irreversible— del dato personal más identificable que manejaba. Y el
BSUID es mejor identidad que el número para lo que el sistema hace: es
estable aunque ella cambie de nombre de usuario, y **solo sirve dentro de
este portafolio**, así que no identifica a nadie fuera de aquí.

Contradice el CLAUDE.md §4.8 —«identidad por número de celular»—, que era
una decisión de minimización con la información de entonces. La Ley 1581
no pide un número: pide minimizar, y esto minimiza más.

### 2. Se responde con `recipient`, y nunca con los dos campos

La identidad **es** el destino. Un solo valor recorre el sistema: el
despachador lo resuelve, la compuerta identifica con él y los demás
módulos solo le responden —de ahí que allí se llame `destino`—.

`whatsapp._campo_destino` decide en qué campo viaja: `to` si es un
teléfono, `recipient` si no. Lo decide **el mismo predicado** que elige el
dominio del HMAC (`identidad.es_telefono`), para que las dos cosas no
puedan discrepar.

Meta admite mandar `to` y `recipient` a la vez, y entonces manda el
teléfono. **Aquí se manda uno solo**, y a propósito: con los dos, un error
en el camino del BSUID no se notaría nunca —el envío saldría bien por el
número— y el sistema estaría dando por bueno algo que no se ha probado.

**El predicado no se apoya solo en `normalizar_telefono`.** Esa función
**quita** todo lo que no sea dígito, así que un BSUID corto como
`CO.12345678` quedaría en ocho dígitos y pasaría por teléfono. Lleva
delante un filtro de forma —solo dígitos y su puntuación— que ningún
BSUID cumple, porque todos empiezan por dos letras y un punto.

### 3. Escalera de identidad con precedencia, y cada peldaño se cuenta

1. `mensaje["from_user_id"]` — el BSUID. `info`.
2. si falta, `contacts[0]["user_id"]`, **solo si hay exactamente un
   mensaje y un contacto**. Emparejarlos por su posición en la lista
   sería adivinar, y equivocarse ahí es atribuirle a una usuaria lo que
   dijo otra. `warning`.
3. si falta, `mensaje["from"]` — el teléfono. `warning` explícito: es una
   red de seguridad, no funcionamiento normal.
4. si falta todo, se descarta, como hasta ahora.

La cuenta en la bitácora **es la medición permanente** de si el supuesto
de los dos mensajes sigue siendo cierto. El día que aparezca
`origen=contacto`, la forma del webhook cambió.

El peldaño 3 tiene un precio declarado: quien entre por ahí queda
identificada por su número y **se duplicará** cuando vuelva a llegar su
BSUID. Son dos huellas distintas y el sistema no puede saber que son la
misma persona.

### 4. A las que ya están se les cambia la llave, no se las borra

**Esta decisión cambió al medirla.** El plan era un corte limpio: crear de
nuevo a «las cuatro usuarias registradas», avisarlas, y que volvieran a
pasar por consentimiento y onboarding. Al exportar las conversaciones
antes de tocar nada —lo primero que se hizo—, la base decía otra cosa:

| | Lo que decían los documentos (08/09) | Lo que había el 17/09 |
|---|---|---|
| usuarias | 4 | **9** |
| huertas | 4 | **7** |
| cultivos | 13 | **56** |
| mensajes | — | **204** |

El número de producción llevaba ocho días abierto. El corte no eran cuatro
personas: eran **nueve, con siete huertas y 56 cultivos**, y 204 mensajes
que son el material de la Fase 7. Y el CU4 y el CU7 volverían a quedarse
sin nada que enseñar, que es justo lo que el README lleva meses señalando
como su bloqueo.

Así que **`repositorio.rellavear_identidad`**: cuando el mensaje trae las
dos cosas —BSUID y teléfono, que es lo que llega hoy en la mayoría—, y
existe una fila con la huella del número pero ninguna con la del BSUID, se
le cambia la llave. Nadie se entera. No se crea ninguna fila, no se toca
`consentimiento_en` —que es la constancia legal— y no se pierde ninguna
huerta, ningún cultivo ni ninguna conversación.

Es **transitorio y se borra**: deja de tener sentido en cuanto todas hayan
escrito una vez con el código nuevo. Mientras siga, cada línea
`Identidad re-llaveada` de la bitácora es una usuaria menos por migrar.

A quien ya escribe sin teléfono no se la puede migrar, y no hace falta:
esas son precisamente las personas nuevas que nunca recibieron respuesta,
y no tienen datos que conservar.

### 5. La columna se llama `identidad_hash` (migración `010`)

`usuario.telefono_hash` guardaría la huella de algo que no es un teléfono.
El nombre viejo mentiría, y una columna que miente es una trampa para
quien lea el esquema dentro de seis meses.

Cada espacio de identificadores lleva **su propia etiqueta de dominio** en
el HMAC —`bsuid:`, como ya se hacía con `wamid:`—, de modo que la huella
de un BSUID no pueda coincidir con la de un teléfono aunque compartan
pepper y columna.

El `PHONE_HASH_PEPPER` **no se toca** aunque el nombre quede impreciso:
cambiarlo es irreversible —las usuarias registradas dejarían de ser
reconocidas— y no aporta nada.

### 6. El nombre de pila lo guarda `guardar_nombre`

Efecto lateral, pero conviene dejarlo escrito. El onboarding completaba el
nombre llamando a `registrar_consentimiento`, aprovechando que era
idempotente. Eso obligaba a arrastrar la **identidad** hasta el onboarding,
que ya no identifica a nadie: solo responde. Ahora escribe por
`usuario_id`, que es lo que tiene a mano, y `registrar_consentimiento`
pierde un parámetro que ya no usaba nadie.

## Consecuencias

**El teléfono deja de circular por el sistema.** Solo se lee en dos
sitios: el peldaño 3 de la escalera y el re-llaveo transitorio. Cuando ese
segundo se borre, quedará uno.

**`spike_despachador` gana dos bloques** —el mensaje sin teléfono y el
re-llaveo— y, de paso, **todas sus cargas útiles pasaron a la forma
nueva**: llevan `from_user_id` y `contacts[]`, y solo una lleva `from`.

**La migración `010` y el despliegue van juntos**, y esta vez al revés que
la `008`: el código desplegado lee `telefono_hash` y el nuevo lee
`identidad_hash`, así que entre uno y otro cada mensaje falla. Es cosa de
un minuto, no se pierde nada —la fila de idempotencia queda en
'recibido'—, pero conviene hacerlo a una hora tranquila.

## Lo que este ADR no resuelve

**`recipient` no está probado en vivo.** Es el único punto donde
equivocarse deja a alguien sin respuesta, y ahora es el camino de
**todos**, no de una minoría. Está comprobado contra la documentación y
con las comprobaciones del spike, que no llegan a Meta. **Hay que
escribirle al bot desde un celular antes de darlo por bueno**; si falla,
se ve en la bitácora (`WhatsApp rechazó el envío`) y se revierte con un
commit.

**El BSUID se regenera si la usuaria cambia de número de teléfono.**
Entonces es, para el sistema, otra persona: pierde su huerta y vuelve a
empezar. Aceptado. Meta manda un webhook de sistema cuando ocurre, así que
tiene arreglo si alguna vez pasa de ser hipotético.

**Los ocho mensajes que ya se perdieron no se recuperan solos.** Se
marcaron `procesado` al descartarse, así que ni un reintento de Meta los
traería de vuelta.

**`calls` sigue suscrito y sin atender.** Si alguien llama al número en
vez de escribir, no pasa nada: ni respuesta ni rastro en la bitácora. Lo
destapó esta misma revisión y no se toca aquí.
