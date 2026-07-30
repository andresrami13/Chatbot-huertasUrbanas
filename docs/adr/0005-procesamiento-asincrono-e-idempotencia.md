# ADR-0005. Procesamiento asíncrono del webhook e idempotencia por `wamid`

- **Estado:** Aceptada; puntos abiertos resueltos el 30/07/2026
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
`BackgroundTasks` de FastAPI.

La idempotencia vive en la tabla `idempotencia_webhook`
([`db/004_idempotencia.sql`](../../db/004_idempotencia.sql)), con dos
estados y descarte por antigüedad. El conjunto en memoria que había antes
quedó retirado el 30/07/2026.

## Puntos abiertos

**Los cuatro quedaron resueltos el 30/07/2026**, antes de implementar el
flujo del CU3 como exigía este apartado. Se conserva el enunciado original
de cada uno porque el recorrido interesa al documento de grado: dos de
ellos se resolvieron de forma distinta a la prevista.

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

   Aplicado a la bitácora, que registraba el `wamid` completo, y a la tabla.

2. **El `wamid` se marca antes de procesarlo.** ~~Si el procesamiento falla
   a mitad, el reintento de Meta se descarta como duplicado y el mensaje se
   pierde en silencio.~~ **Resuelto.** Dos estados, como se pedía:

   - `recibido` al tomar el mensaje;
   - `procesado` **solo al terminar bien**.

   El reclamo es **una sola sentencia** `INSERT ... ON CONFLICT DO UPDATE
   ... WHERE`, no una consulta seguida de una escritura: separarlas abriría
   una carrera en la que dos entregas del mismo mensaje se reclamarían las
   dos. Resuelve cuatro casos: mensaje nuevo (se toma), ya `procesado`
   (duplicado real, se descarta), `recibido` reciente (en curso, se
   descarta) y `recibido` vencido (el intento anterior murió, **se vuelve a
   tomar**).

   El plazo del reclamo es de 5 minutos, holgadamente por encima de los
   4,3 s que tardó el pipeline medido en producción.

   Si el trabajo lanza una excepción, la fila se deja a propósito en
   `recibido`: al vencer el plazo, el reintento de Meta lo recupera.

3. **El conjunto en memoria se vacía por completo al llegar al límite.**
   ~~Olvida también los `wamid` vistos hace segundos.~~ **Resuelto.** La
   tabla descarta **por antigüedad** —siete días—, nunca en bloque. La
   limpieza corre al arrancar el servicio. Con 5 a 7 usuarias la tabla no
   crece lo bastante para necesitar una tarea periódica; si algún día lo
   hiciera, el sitio está señalado en `limpiar_idempotencia`.

4. **`BackgroundTasks` muere con el proceso.** Un redeploy de Railway pierde
   las tareas en vuelo. **Mitigado, no eliminado**, y conviene ser preciso
   al describirlo en el documento de grado:

   - Lo que se arregló es la consecuencia grave. Con el punto 2 resuelto, un
     mensaje interrumpido queda en `recibido` y el reintento de Meta lo
     recupera. Antes quedaba marcado como visto y se perdía.
   - Lo que queda es la pérdida **si Meta ya agotó sus reintentos**. Pero
     **deja de ser silenciosa**: la fila permanece en `recibido` y
     `contar_mensajes_atascados` la encuentra. El servicio avisa en la
     bitácora al arrancar si hay alguna.
   - Eliminarlo del todo exigiría una cola externa, descartada en este mismo
     ADR por presupuesto.

   La garantía real del sistema es **al menos una vez**, no exactamente una:
   si el proceso muere entre el final del trabajo y el marcado, el mensaje se
   reprocesa. Con las respuestas del bot eso significa un mensaje repetido,
   preferible a un registro de huerta perdido.

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
