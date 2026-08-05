# ADR-0011. El fragmento comunitario lleva solo las especies

- **Estado:** Aceptada
- **Fecha:** 2026-08-04
- **Fase:** 6 (implementa el CU4)
- **Sustituye:** la composición del texto propuesta en
  [ADR-0004](0004-cultivo-y-fragmento-comunitario.md)

## Contexto

El [ADR-0004](0004-cultivo-y-fragmento-comunitario.md) fijó que el texto
del fragmento se compondría de `nombre_huerta` + barrio + la lista de
cultivos con sus fechas, y dejó dicho que **la parte de generación quedaba
propuesta y debía confirmarse en la Fase 6**. Este es ese momento, y la
confirmación es negativa.

El motivo estaba anotado desde el spike del 29/07/2026: en la colección
comunitaria el umbral casi no discriminaba —todo caía entre 0.66 y 0.80—
porque todos los fragmentos comparten la plantilla `"Huerta X. Barrio Y.
Cultivos: ..."` y ese texto fijo infla por igual la similitud de todos.

El [ADR-0009](0009-ingesta-de-fuentes-oficiales.md) dio después la
contrapartida: en la colección oficial **no se metió ninguna plantilla**
—la atribución sale de `fuente` por la clave foránea— y la separación entre
lo pertinente y lo ajeno resultó de catorce centésimas.

## Decisión 1. El texto vectorizado son solo las especies

```
tomate, cilantro, lechuga
```

Ni nombre de huerta, ni barrio, ni fechas. **No se pierde ninguna
información:** el nombre y el barrio llegan por la clave foránea a
`huerta`, y las fechas siguen en `cultivo`. Todo se recupera al componer la
respuesta, igual que la entidad y el título del CU2 salen de `fuente`.

Medido con
[`scripts/calibrar_fragmento_comunitario.py`](../../scripts/calibrar_fragmento_comunitario.py)
sobre seis huertas y cinco consultas del CU4, la separación media entre la
huerta más pertinente y la menos pertinente:

| Formato | Separación | Orden correcto |
|---|---|---|
| A. plantilla del ADR-0004 | 0.0585 | 3/3 |
| B. prosa con nombre y barrio | 0.0608 | 3/3 |
| C. solo cultivos con fecha | 0.0735 | 3/3 |
| **D. solo especies** | **0.1166** | 3/3 |

Tres lecturas que conviene llevar al documento de grado:

1. **Quitar el dato compartido dobla la discriminación.** El caso más
   claro: "alguna huerta tiene fresas o uchuvas" separa 0.084 con la
   plantilla y **0.213** sin ella.
2. **No es la plantilla como forma, es el contenido repetido.** Redactarla
   como prosa natural (B) no mejora nada. Da igual cómo se escriba el
   nombre y el barrio; lo que estorba es que estén.
3. **Las fechas también son relleno compartido.** El formato C las conserva
   y pierde un tercio de la separación frente a D. "marzo de 2026" aparece
   en todos los fragmentos y actúa como la plantilla, solo que más
   disimulado. Es la mitad del efecto y no estaba previsto.

Con seis huertas los cuatro formatos aciertan el orden, así que ese
indicador no distingue todavía. Lo que distingue es el margen, y con 5 a 7
huertas en la Fase 8 el margen será lo único que separe una recuperación
fiable de una casualidad.

## Decisión 2. Umbral propio para la colección comunitaria

`RAG_UMBRAL_COMUNITARIO = 0.65`, frente al 0.68 de la colección oficial
([ADR-0010](0010-umbral-de-similitud-recalibrado.md)).

No es simetría: son magnitudes distintas. Un fragmento oficial es prosa de
unos 400 tokens y uno comunitario es una lista de tres palabras, así que
sus similitudes viven en otro rango. Aplicarles el mismo umbral dejaba sin
responder la consulta más típica del CU4.

Medido sobre 9 consultas legítimas y 5 ajenas, el hueco es de **+0.0437**
—peor legítima 0.6765, mejor ajena 0.6327, que es la consulta médica y
por tanto la que más importa dejar fuera—. Cuatro veces más holgado que el
del CU2. El 0.65 cae centrado.

## Decisión 3. Respaldo por listado para la pregunta general

Si la búsqueda por similitud no devuelve nada, se listan las huertas
actualizadas más recientemente.

El CU4 recibe dos clases de pregunta que no se resuelven igual:

- **"¿alguien más siembra tomate?"** es una búsqueda, y la similitud la
  resuelve con precisión.
- **"¿qué están sembrando las otras huertas?"** es un **listado**. Una
  lista de especies se parece poco a esa frase por mucho que sea la
  respuesta correcta: se queda en 0.63 y el CU4 callaba teniendo tres
  huertas que enseñar.

Bajar el umbral para que pasara la segunda estropea la primera: con 0.60
entran las cuatro huertas cuando preguntan por fresas y solo una las tiene.

**Este respaldo no filtra por intención**, y hay que declararlo: una
pregunta ajena al dominio que llegue hasta aquí recibirá el listado igual.
Quien decide si un mensaje es una consulta a la comunidad es el function
calling (Fase 2, §4). Mientras el agente no exista, el CU4 **no está
conectado al despachador**.

### Un error de método que conviene registrar

La calibración inicial midió la similitud máxima sobre **todas** las
huertas, pero en producción se excluye la de quien pregunta —el CU4 es qué
siembran *otras* huertas—. En la primera prueba de punta a punta la huerta
excluida era justo la que puntuaba más alto, y la consulta general falló
pese a que la calibración la daba por buena.

Es el mismo tipo de error que el del umbral del CU2 (ADR-0010): medir sobre
un montaje que no reproduce las condiciones reales. Aquí lo destapó la
prueba con datos en la base, no la calibración.

## Decisión 4. Generar no puede tumbar el registro

El fragmento se regenera al confirmar un registro, **fuera de la
transacción** y después de que el guardado haya cerrado: exige una llamada
de red al modelo de embeddings, y meterla dentro tendría la base bloqueada
esperando a un tercero.

Si falla, el CU3 responde igual "listo, ya quedó guardado". El fragmento es
un derivado y se puede rehacer (ADR-0004); la huerta no. El precio hay que
enunciarlo: **entre el fallo y la reparación esa huerta es invisible para
el CU4**, y por eso el fallo queda en la bitácora y existe
[`scripts/regenerar_fragmentos.py`](../../scripts/regenerar_fragmentos.py).

Ese script cumple tres funciones: la puesta al día de las huertas
anteriores a la Fase 6, la reparación de los fallos, y la re-generación
completa si algún día cambia el formato del texto —porque fragmentos de
formatos distintos no son comparables entre sí, igual que no lo serían
embeddings de modelos distintos—.

## Consecuencias

- El CU4 funciona. Probado de punta a punta con
  [`scripts/spike_comunidad.py`](../../scripts/spike_comunidad.py), que crea
  cuatro huertas temporales y las borra al terminar: la consulta específica
  devuelve solo la huerta pertinente, la general las lista todas con su
  barrio, la huerta de quien pregunta queda excluida siempre y ninguna
  respuesta presenta el dato como recomendación.
- **`fragmento_comunitario` no contiene ningún dato personal**: solo
  nombres de especies vegetales. Menos aún que antes, cuando llevaba el
  nombre de la huerta.
- El prompt del CU4 es propio y no el del CU2. La mitad de sus reglas
  existen para impedir que el modelo convierta un reporte en un consejo:
  que tres vecinas tengan tomate no significa que el tomate se dé bien
  aquí (CLAUDE.md §6).
- **Al ingerir una segunda fuente o cambiar el formato, hay que remedir.**
  Ninguno de estos números sobrevive a un cambio de corpus.

## Pendiente de corrección documental

- **Fase 3 / ADR-0004** — el texto del fragmento ya no incluye
  `nombre_huerta`, barrio ni fechas.
- **Fase 4, §7** — la colección comunitaria lleva umbral propio (0.65). El
  spike de la Fase 5 concluyó que no hacía falta, pero midió sobre el
  formato con plantilla.

## Alternativas descartadas

- **Conservar el formato del ADR-0004.** Menos de la mitad de discriminación
  por un dato que no se pierde: está en la clave foránea.
- **Formato C, especies con fecha.** Punto intermedio, pero paga un tercio
  de la separación por unas fechas que igual se recuperan de `cultivo` para
  la respuesta.
- **Bajar el umbral en vez del respaldo por listado.** Estropea la consulta
  específica, que es donde la similitud sí aporta.
- **Detectar si la pregunta es general o específica.** Sería un clasificador
  de intención aparte, que es justo lo que CLAUDE.md §4.9 excluye. El
  respaldo consigue lo mismo sin decidir nada: intenta buscar y, si no hay
  nada, lista.
