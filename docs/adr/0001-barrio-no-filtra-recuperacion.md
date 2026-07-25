# ADR-0001. El barrio no filtra la recuperación comunitaria

- **Estado:** Aceptada
- **Fecha:** 2026-07-25
- **Fase:** 5 (resuelve una contradicción entre las Fases 2 y 4)

## Contexto

Los documentos se contradicen sobre el papel del barrio en la recuperación:

- La **Fase 4, §5** dice que la búsqueda comunitaria se ejecuta sobre todas
  las huertas registradas y que "el barrio no filtra la búsqueda, sino que
  se informa como parte de la atribución".
- La **Fase 2, CU2, paso 1** dice que el sistema recupera "los datos
  comunitarios **del barrio**".
- La **Fase 4, Tabla 3** justifica el valor cerrado del campo porque las
  variantes de escritura "romperían el **filtro por barrio** del RAG",
  dando por supuesto que ese filtro existe.

Sin resolverlo no se puede decidir si `barrio` necesita ser una columna
filtrable e indexada en `fragmento_comunitario` o basta como metadato.

## Decisión

**El barrio no participa como criterio de filtrado en ninguna
recuperación.** Prevalece la Fase 4, §5.

La búsqueda por similitud se ejecuta sobre todas las huertas registradas,
sin restricción geográfica. El barrio se usa exclusivamente como metadato
de atribución en la respuesta, con la etiqueta
`[COMUNITARIO – huerta, barrio]` definida en la Fase 4, §5.

## Consecuencias

- `fragmento_comunitario` no requiere índice sobre el barrio para el RAG.
  El único índice necesario es el vectorial.
- El CU4 se resuelve con una sola consulta de similitud, sin predicado
  previo de barrio.
- Una usuaria puede recibir como contexto lo que reporta una huerta de otro
  barrio de la UPZ. Es coherente con el propósito del CU4 —convertir el
  conocimiento disperso en un activo consultable— y la atribución explícita
  deja claro de dónde viene cada dato.
- **Anula la justificación de la Fase 4, Tabla 3** para el valor cerrado del
  barrio. La decisión de mantenerlo controlado se sostiene ahora en otros
  motivos, recogidos en [ADR-0002](0002-catalogo-de-barrios.md).

## Pendiente de corrección documental

Fase 2, CU2, paso 1: eliminar la restricción "del barrio".

## Alternativas descartadas

**Filtrar por barrio con respaldo a búsqueda global si no hay resultados.**
Descartada: añade una segunda consulta y una regla de respaldo al pipeline
para un beneficio nulo con el volumen del prototipo (5–7 huertas
registradas en la Fase 8). La atribución ya da a la usuaria el contexto
geográfico que necesita para juzgar la pertinencia del dato.
