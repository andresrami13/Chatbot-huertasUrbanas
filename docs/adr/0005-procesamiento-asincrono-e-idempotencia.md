# ADR-0005. Procesamiento asíncrono del webhook e idempotencia por `wamid`

- **Estado:** Aceptada, con puntos abiertos
- **Fecha:** 2026-07-25
- **Fase:** 5

## Contexto

El diagrama C4 de la Fase 3 y la Tabla 2 de componentes no contemplan
ningún procesamiento en segundo plano: el webhook aparece como si
resolviera la petición de forma síncrona. Esa omisión no es viable:

- Meta reintenta la entrega de un webhook si no recibe respuesta con
  rapidez.
- El pipeline completo —transcripción, function calling, RAG, envío—
  excede ese margen con holgura.
- Sin control de duplicados, cada reintento produce una respuesta repetida
  a la usuaria o un registro de huerta duplicado.

Es la única decisión estructural del proyecto **sin respaldo en los
documentos de las fases cerradas**, por lo que se registra aquí para darle
trazabilidad.

## Decisión

1. El controlador de webhook valida la firma, responde **200 de inmediato**
   y delega el trabajo a segundo plano.
2. Todo mensaje se descarta si su `wamid` ya fue procesado
   (**idempotencia por `wamid`**).

## Estado de la implementación

Implementado en [`app/api/webhook.py`](../../app/api/webhook.py) y
[`app/services/dispatcher.py`](../../app/services/dispatcher.py), con
`BackgroundTasks` de FastAPI y un conjunto en memoria para los `wamid`.

El control en memoria es **provisional**: se pierde en cada reinicio y
asume un único worker (coherente con el `Procfile` actual, que no usa
`--workers`).

## Puntos abiertos

Ninguno bloquea la Fase 5 mientras el despachador solo escriba en bitácora.
**Todos deben resolverse antes de implementar el flujo del CU3**, porque a
partir de ahí un mensaje perdido es un registro de huerta perdido.

1. **Conflicto con la compuerta de consentimiento.** ~~Persistir el `wamid`
   al recibirlo es tratamiento de datos de alguien que quizá no ha
   autorizado, y el CU1 lo prohíbe.~~ **Resuelto el 30/07/2026.**

   La propuesta que figuraba aquí —almacenar el `wamid` "desacoplado de todo
   identificador de remitente, de modo que la tabla no permita reconstruir
   quién escribió"— **era inviable, y por un motivo que no se había
   advertido: el `wamid` contiene el número de teléfono del remitente**, en
   ASCII, recuperable con un `base64 -d`. Es él mismo un identificador de
   remitente, así que desacoplarlo de otros no servía de nada: una tabla de
   `wamid` en claro es una tabla de teléfonos.

   La solución adoptada es guardar un **HMAC-SHA256 del `wamid`** con el
   pepper que ya existe (`huella_wamid`, en
   [`app/core/identidad.py`](../../app/core/identidad.py)). La comparación
   exacta que la idempotencia necesita funciona igual sobre la huella, la
   tabla deja de ser reconstruible, y el conflicto con la compuerta
   desaparece: lo que se persiste ya no es un dato personal.

   Aplicado también a la bitácora, que registraba el `wamid` completo, y al
   conjunto en memoria. Queda por hacer solo la tabla.
2. **El `wamid` se marca antes de procesarlo.** Si el procesamiento falla a
   mitad, el reintento de Meta se descarta como duplicado y el mensaje se
   pierde en silencio. Debe pasar a dos estados: `recibido` al entrar,
   `procesado` solo al terminar correctamente.
3. **El conjunto en memoria se vacía por completo al llegar al límite**, lo
   que olvida también los `wamid` vistos hace segundos. La tabla definitiva
   debe descartar por antigüedad o TTL.
4. **`BackgroundTasks` muere con el proceso.** Un redeploy de Railway pierde
   las tareas en vuelo. Combinado con el punto 2, el mensaje no se recupera.

## Consecuencias

- La Fase 3 debe actualizarse: el despachador asíncrono es un componente
  que no figura en la Tabla 2, y el C4 no refleja el procesamiento en
  segundo plano.
- La idempotencia deja de ser un detalle de implementación y pasa a ser
  requisito de corrección funcional del CU3.

## Alternativas descartadas

- **Procesar dentro de la petición.** Produce reintentos de Meta y
  respuestas duplicadas. Es el problema que este ADR existe para evitar.
- **Cola externa (Redis, broker).** Innecesaria al volumen del prototipo y
  añade un servicio de pago al presupuesto, ya ajustado por el coste de
  Railway Hobby.
