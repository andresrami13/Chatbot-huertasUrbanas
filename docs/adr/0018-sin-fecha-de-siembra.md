# ADR-0018. La fecha de siembra sale del CU3

- **Estado:** Aceptada; extiende al CU3 lo que el
  [ADR-0011](0011-fragmento-comunitario-solo-especies.md) concluyó para el CU4
- **Fecha:** 2026-08-18
- **Fase:** 7
- **Origen:** Fase 4, Tabla 3 (extracción de entidades) / Fase 3 (esquema)

## Contexto

La Fase 4, Tabla 3, define la extracción del CU3 con tres campos por
cultivo: la especie, la fecha aproximada de siembra y una **marca de
imprecisión** que distingue lo que la usuaria precisó de lo que el modelo
estimó. El esquema de la Fase 3 lo refleja en `cultivo` con
`fecha_siembra_aprox` y `fecha_imprecisa`.

Al revisar el CU3 con el registro ya funcionando, la fecha resultó ser un
**dato de solo escritura**. Se inventaría quién la toca:

| | |
|---|---|
| La escriben | `repositorio.guardar_huerta` y `repositorio.agregar_cultivos` |
| La lee un caso de uso | **ninguno** |
| La lee algo | `scripts/revisar_prueba_real.py`, que la imprime para diagnosticar |

El CU2 no toca `cultivo`. El agente tampoco. Y el CU4 la excluye **a
propósito y con medición**: al calibrar el fragmento comunitario
(ADR-0011) se compararon cuatro formatos contra consultas reales, y la
separación media fue

    plantilla del spike        0.0585
    prosa con nombre y barrio  0.0608
    solo cultivos con fecha    0.0735
    solo especies              0.1166   <- el que quedó

La fecha **empeoraba la recuperación**. Ese hallazgo ya estaba en el
proyecto desde el 04/08/2026, aplicado solo al texto vectorizado.

A eso se suma lo que la fecha cuesta en el otro extremo, el de la usuaria.
Aparecía en el mensaje de confirmación —`- tomate, marzo de 2026 (más o
menos)`— y era el campo más largo de cada renglón, en un mensaje que ella
tiene que leer y aprobar. La decisión 4 del
[ADR-0008](0008-borrador-de-registro-y-una-huerta-por-usuaria.md) defendía
mostrar la marca de imprecisión en lugar de esconderla, para darle ocasión
de corregir. El argumento era bueno mientras el dato sirviera para algo.

## Decisión 1. La fecha sale del extractor, no solo del resumen

Podría haberse dejado de mostrar y seguido extrayendo. Se descarta: un dato
que nadie lee ni muestra no debe pedirse.

`extraccion_v3.md` sustituye a `extraccion_v2.md` y el prompt pasa de 2620 a
1783 caracteres. Desaparecen el bloque de fechas relativas, la resolución de
«hace dos meses» contra la fecha de hoy y la explicación de la marca de
imprecisión. Con ellos desaparece el hueco `{hoy}`, y `extraer_huerta` deja
de recibir el parámetro que existía para poder probar las fechas relativas.

**El modelo queda con un solo campo que acertar por cultivo.** Es el mismo
efecto que buscaba la decisión 9 del
[ADR-0016](0016-onboarding-de-preguntas-cerradas.md) al sacarle el barrio:
cada campo que se le quita es un campo menos que puede equivocar.

La usuaria puede seguir diciendo «sembré cilantro en marzo». De ahí solo
sale «cilantro», y el prompt lo dice con ese ejemplo.

## Decisión 2. Las columnas se borran, no se dejan muertas

Migración `db/008_sin_fecha_de_siembra.sql`: `alter table public.cultivo
drop column` sobre las dos.

La alternativa era dejarlas nulas y sin escribir. Se descarta porque una
columna que nadie llena es una trampa para quien lea el esquema —o el
documento de grado— y suponga que ahí hay fechas de siembra. El proyecto ya
tiene bastante distancia entre los `.docx` y el código como para añadir una
que no se ve.

Se ejecuta con `cultivo` en cero filas, así que no se pierde ningún dato de
ninguna usuaria. Ese es el momento barato de hacerlo, y no vuelve.

**El orden importa y es la parte operativa de esta decisión:** primero se
despliega el código que deja de escribir las columnas, y solo después se
corre la migración. Al revés, cada confirmación del CU3 falla durante la
ventana, porque Railway lee esta misma base y el efecto es inmediato
(CLAUDE.md §10).

## Decisión 3. El borrador tolera los dos formatos anteriores

`registro._deserializar` ignora las claves que ya no existen. Eran
`nombre_huerta` y `barrio_codigo` desde el ADR-0016; ahora también `anio`,
`mes` y `fecha_imprecisa`.

Sin esa tolerancia, un borrador escrito antes del despliegue y confirmado
después perdería lo que la usuaria ya contó. Los borradores caducan a las 24
horas, así que la ventana en la que puede ocurrir es exactamente la del
despliegue.

## Consecuencias

- El mensaje de confirmación del CU3 queda en una lista de nombres de
  plantas. Es más corto y más fácil de aprobar de un vistazo, que es lo que
  el §4.7 necesita que ella haga de verdad.
- La regla (iii) de la orquestación multi-intención del CLAUDE.md §5
  —«tratar fechas vagas como aproximadas y afinarlas en la confirmación»—
  deja de existir. Se retira del CLAUDE.md.
- La Fase 4, Tabla 3, y el esquema de la Fase 3 quedan pendientes de
  corrección en los `.docx`.
- El ejemplo de la bienvenida cambia. Decía `"sembré cilantro en marzo"` y
  estaba enseñándole a decir una fecha que el sistema iba a ignorar.
- En `scripts/spike_extraccion.py` dos casos cambian de expectativa: el de
  «fecha vaga» ahora comprueba que el «desde hace rato» **se ignore**.
  `scripts/revisar_prueba_real.py` deja de imprimir la fecha.

## Lo que este ADR no resuelve

- **Si alguna usuaria echa de menos la fecha.** Nadie la ha pedido, pero
  tampoco se ha preguntado. La evaluación con 5–7 usuarias de la Fase 7 es
  donde se vería.
- **Qué pasa si ella dice la fecha igual.** El sistema la ignora en
  silencio, sin decirle que no la guardó. Es lo mismo que ya ocurre con el
  barrio y el nombre de la huerta desde el ADR-0016, así que no introduce
  un comportamiento nuevo, pero sigue sin medirse si desconcierta.

## Alternativas descartadas

- **Dejar de mostrarla y seguir guardándola.** Es lo mínimo que resolvía la
  queja, y deja el peor resultado: se le sigue pidiendo al modelo un campo
  que nadie va a ver ni a leer.
- **Dejar las columnas vacías por si la Fase 8 las pide.** Solo compensaría
  con un caso de uso concreto en mente —recordatorios de cosecha, por
  ejemplo— y la Fase 2 no define ninguno. Si aparece, vuelven con otra
  migración y con datos desde cero igual, porque hoy la tabla está vacía.
- **Guardar la fecha en `cultivo` pero fuera del fragmento comunitario.**
  Es exactamente el estado del que se viene: el ADR-0011 ya la había sacado
  del texto vectorizado y la había dejado en la tabla. Un año de datos
  después seguiría sin leerla nadie.
