# ADR-0006. El saludo y la ayuda se detectan sin el modelo

- **Estado:** Aceptada
- **Fecha:** 2026-07-29
- **Fase:** 5
- **Depende de:** [ADR-0003](0003-consentimiento-sin-insistencia.md)

## Contexto

El CU5 (pedir ayuda) es el único caso de uso **sin precondición de
consentimiento**, y la bienvenida se dispara "ante un saludo o un mensaje sin
petición accionable" (Fase 2, §4). Ambos deben funcionar, por tanto, para
alguien que todavía no ha autorizado el tratamiento de sus datos.

Al mismo tiempo, la Fase 2 §5.1 establece la compuerta: sin autorización,
ninguna consulta ni registro se procesa. Y la Fase 2 §4 establece que las
intenciones se resuelven con function calling, es decir, **con el modelo**.

Las dos reglas chocan justo en el primer mensaje de la conversación. Para
decidir si un "hola" es un saludo hay que interpretar el mensaje; si esa
interpretación la hace Gemini, el sistema ya procesó el mensaje de alguien a
quien todavía no le ha preguntado si puede. La compuerta se habría aplicado
después del hecho que pretende impedir.

Ningún documento de las fases cerradas resuelve este orden.

## Decisión

**La detección de saludo y de petición de ayuda se resuelve dentro del
backend, por comparación con listas de palabras clave, sin invocar al
modelo.** Implementada en
[`app/services/consentimiento.py`](../../app/services/consentimiento.py)
(`es_saludo_o_ayuda`).

La comparación normaliza el texto —minúsculas, sin tildes, sin signos— y
solo considera mensajes de **hasta cuatro palabras**. "Hola" es un saludo;
"hola, mi tomate tiene bichos" no lo es, es una consulta con un saludo
delante, y responderla con la bienvenida dejaría sin atender lo que la
usuaria preguntó.

Una vez existe consentimiento, la intención la decide el agente por function
calling, conforme a la Fase 2 §4.

## Justificación

1. **Es la única forma de cumplir el CU5 sin romper la compuerta.** Enviar el
   mensaje a Gemini para clasificarlo es tratamiento de datos, y además
   tratamiento por un tercero fuera del país. La Ley 1581 de 2012 sujeta esa
   transferencia a la autorización del titular (art. 26), que es exactamente
   lo que en ese instante no se tiene. El orden correcto no admite
   alternativa: primero se pregunta, después se procesa.
2. **Coherencia con la bienvenida.** La Fase 2 §4 ya define la bienvenida
   como texto fijo enviado por el backend **sin pasar por el modelo**. Sería
   incongruente que el texto no pase por el modelo pero la decisión de
   enviarlo sí.
3. **El CU5 es contenido estático.** No hay nada que generar: la respuesta
   está en `app/textos.py`. Un modelo no aporta calidad a una decisión cuyo
   resultado es una constante.
4. **Robustez del primer contacto.** El saludo es el primer mensaje que
   recibe toda usuaria nueva. Resolverlo sin dependencias externas lo hace
   inmune a una caída de la API, a la latencia y al gasto por invocación.

## Consecuencias

- La función queda **en el camino permanente** del sistema para el tramo
  previo al consentimiento. No es andamio provisional.
- En cambio, su uso **después** del consentimiento —hoy en
  [`app/services/dispatcher.py`](../../app/services/dispatcher.py)— sí es
  provisional: existe solo mientras no haya agente, y desaparece cuando el
  function calling asuma esa decisión en la Fase 6. El mismo código cumple
  dos papeles con vigencia distinta, y conviene no confundirlos al retirar el
  provisional.
- **Falsos negativos benignos.** Un saludo con una variante no prevista
  ("¿qué hubo pues?") no se reconoce y la usuaria recibe la solicitud de
  consentimiento en vez de la bienvenida. No pierde acceso a nada: el camino
  para autorizar sigue abierto y el mensaje no se procesa. Es el modo de
  fallo correcto para una compuerta.
- **El audio previo al consentimiento no se puede clasificar.** Transcribirlo
  exigiría enviarlo al modelo, es decir, lo que este ADR impide. Una nota de
  voz de alguien sin autorizar cae por tanto en la solicitud de
  consentimiento, que es el destino adecuado.
- Las listas de palabras clave son un artefacto que hay que mantener. La
  Fase 8 dará el material para ampliarlas: conviene revisar qué saludos
  reales de las usuarias no reconoció.

## Alternativas descartadas

- **Clasificar con el modelo antes de la compuerta.** Es el planteamiento que
  este ADR descarta. Invierte el orden que exige la Fase 2 §5.1.
- **Pedir consentimiento a todo el mundo antes de cualquier respuesta,
  incluida la ayuda.** Cumpliría la compuerta, pero incumple el CU5, que no
  tiene precondición, y abre la conversación con una solicitud de permisos
  sin haber explicado antes qué hace el bot. Con 8 de 11 encuestadas
  desconfiando de que se guarden sus datos (Fase 1), es el peor primer
  contacto posible y perjudica el criterio SUS ≥ 68.
- **Un clasificador de intención propio, entrenado o basado en reglas más
  ricas.** Desproporcionado: solo hay que distinguir dos intenciones de
  respuesta fija, y la Fase 2 §4 reserva la clasificación de intenciones al
  function calling. Añadir un clasificador aparte contradiría además la
  decisión de no tener clasificador separado (CLAUDE.md §4.9).
- **Responder la bienvenida a todo mensaje de quien no ha autorizado.**
  Convierte cualquier consulta en un texto genérico que no responde nada, y
  oculta que lo que falta es la autorización.

## Sin respaldo documental

Como el [ADR-0005](0005-procesamiento-asincrono-e-idempotencia.md), esta
decisión no se apoya en ninguna fase cerrada: resuelve un choque entre dos
reglas de la Fase 2 que los documentos no anticiparon. Debe incorporarse al
documento de grado como precisión del CU1 y del CU5.
