# ADR-0002. Catálogo de barrios como tabla, no como tipo ENUM

- **Estado:** Aceptada
- **Fecha:** 2026-07-25
- **Fase:** 5
- **Depende de:** [ADR-0001](0001-barrio-no-filtra-recuperacion.md)

## Contexto

La Fase 4, Tabla 3, define `barrio` como enumeración de valores cerrados
—Holanda, Los 3 Sectores, El Regalo, El Anhelo, La Cabaña, El Bosque, Santa
Fe y `otro`— justificándolo en que las variantes de escritura romperían el
filtro por barrio del RAG.

El [ADR-0001](0001-barrio-no-filtra-recuperacion.md) elimina ese filtro, y
con él la única justificación documentada del valor cerrado. Se evaluó
entonces abrir el campo y dejar que la lista se poblara con los valores que
fueran entrando.

El dato relevante para decidir es **quién puebla el campo**: no es la
usuaria escribiendo en un formulario, es Gemini extrayendo entidades de un
texto que muchas veces viene de audio transcrito.

## Decisión

Se mantiene la lista controlada, pero **como tabla de catálogo, no como
tipo `ENUM` de PostgreSQL ni como campo de texto libre**.

- Tabla `barrio`, sembrada con los siete barrios de la UPZ 84 Bosa
  Occidental más el valor `otro`.
- `huerta.barrio_id` como clave foránea al catálogo.
- El prompt de extracción **se genera leyendo la tabla**, no lleva la lista
  escrita a mano. La salida estructurada de Gemini restringe la respuesta a
  esos valores.

## Justificación

La del documento original ya no aplica. Los motivos vigentes son otros
tres:

1. **Fiabilidad de la extracción.** La salida estructurada admite `enum` en
   el esquema, lo que obliga al modelo a devolver un valor válido. Sin esa
   restricción, un extractor que trabaja sobre audio transcrito produce
   "Holanda", "Barrio Holanda", "holanda" y "Holanda, Bosa" para el mismo
   sitio. Una lista poblada así no es un catálogo, es ruido acumulado.
2. **Integridad del alcance y del entregable.** El anteproyecto §8 promete
   "una primera base estructurada de información sobre las huertas de los
   barrios seleccionados". Con campo libre entrarían barrios ajenos a la
   UPZ 84, fuera del alcance declarado en §7.1, y el dato dejaría de ser
   estructurado.
3. **Consistencia de la atribución.** Tras el ADR-0001, el barrio se
   muestra a la usuaria en cada dato comunitario atribuido. Las variantes
   ortográficas se verían en las respuestas.

El caso que motivaba abrir la lista —una huerta cuyo barrio no esté
previsto— ya lo cubre el valor `otro`, definido en la Fase 4. No se pierde
ningún registro.

## Consecuencias

- Añadir un barrio es un `INSERT`, sin migración de esquema.
- Resuelve el desajuste entre el anteproyecto §5.3.1, que lista siete
  barrios, y el §7.1, que lista seis omitiendo Los 3 Sectores: **se siembran
  los siete**.
- El generador del prompt de extracción depende del catálogo. Si se añade
  un barrio, el prompt lo recoge sin cambios de código.
- Un valor `otro` frecuente es señal de que al catálogo le falta un barrio;
  conviene revisarlo tras la Fase 8.

## Alternativas descartadas

- **Tipo `ENUM` de PostgreSQL.** Semánticamente equivalente, pero crecer la
  lista exige `ALTER TYPE` y una migración. Rígido sin necesidad.
- **Campo de texto libre poblado por uso.** Descartada por los tres motivos
  de arriba. La diferencia decisiva frente a un catálogo emergente clásico
  es que aquí el poblador es un modelo de lenguaje, no una persona.
