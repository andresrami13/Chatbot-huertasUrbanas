# ADR-0004. Se conserva `cultivo`; un fragmento comunitario por huerta

- **Estado:** Aceptada (la parte de generación queda propuesta para la Fase 6)
- **Fecha:** 2026-07-25
- **Fase:** 5

## Contexto

El modelo de la Fase 3 guarda la información agronómica dos veces: como
filas en `cultivo` (relacional, 1:N con `huerta`) y, vectorizada, en
`fragmento_comunitario` (N:1 con `huerta`). Es duplicación deliberada
—cada forma sirve a un acceso distinto— pero ningún documento define quién
compone el texto que se vectoriza ni cuándo se regenera si una huerta
cambia sus cultivos.

Sin resolverlo, el riesgo es que el fragmento quede desincronizado respecto
a las filas de `cultivo` y que el CU4 responda con datos obsoletos.

## Decisión

**Se conserva `cultivo` como tabla relacional.** Es la fuente de verdad del
dato agronómico; `fragmento_comunitario` es un derivado.

Para la generación del fragmento se adopta:

- **Un fragmento por huerta**, no uno por cultivo. La unidad de atribución
  del CU4 es la huerta (`[COMUNITARIO – huerta, barrio]`), y fragmentar por
  cultivo produciría trozos sin contexto suficiente.
- El texto se compone de `nombre_huerta` + barrio + la lista de cultivos
  con sus fechas aproximadas.
- **Se regenera por completo** —texto y embedding— cada vez que se confirma
  un registro o una actualización de esa huerta. No hay actualización
  incremental.

## Consecuencias

- `cultivo` y `fragmento_comunitario` no pueden divergir: el segundo se
  reconstruye entero desde el primero.
- Evita fragmentos huérfanos y la lógica de reconciliación que exigiría una
  actualización parcial.
- Cuesta un `embedding` completo por huerta en cada cambio. Con el volumen
  del prototipo (5–7 huertas en la Fase 8) es irrelevante.
- Ningún campo personal entra en el texto del fragmento: solo
  `nombre_huerta`, barrio y cultivos, que son los campos compartibles según
  la capa 4 del modelo de seguridad (Fase 3, Tabla 3).

## Alcance en la Fase 5

Para el esquema basta con **crear la tabla**. La composición del texto y su
regeneración se implementan en la Fase 6, junto con el resto del RAG, y la
parte de generación de este ADR debe confirmarse entonces.

## Alternativas descartadas

- **Un fragmento por cultivo.** Trozos demasiado pequeños y sin contexto;
  además multiplica las llamadas de vectorización.
- **Actualización incremental del fragmento.** Complejidad de
  reconciliación sin beneficio a este volumen.
- **Eliminar `cultivo` y dejar solo el fragmento vectorial.** Impediría
  cualquier consulta estructurada sobre los cultivos y degradaría el
  entregable de datos comprometido en el anteproyecto §8.
