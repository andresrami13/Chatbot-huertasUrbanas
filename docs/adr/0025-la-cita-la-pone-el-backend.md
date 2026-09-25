# ADR-0025. La línea de la fuente la pone el backend, no el modelo

- **Estado:** Aceptada
- **Fecha:** 2026-09-24
- **Fase:** 7
- **Origen:** incidencia INC-020, de la ejecución del banco de 20 preguntas

## Contexto

Al ejecutar el banco de veinte preguntas agroecológicas (`BPA-CHU-001`),
**seis de veinte respuestas** le dicen a la usuaria que no tienen esa
información y a continuación le adjuntan la línea

    Fuente: Jardín Botánico de Bogotá José Celestino Mutis

Son R-05, R-06, R-07, R-09 y R-10 del banco, más C-02 de las de control.
Es lo que hace que el banco no se supere: explica los seis fallos de
pertinencia y los seis de coherencia.

### Por qué ocurre

**La cita la escribe el modelo**, obedeciendo el prompt. El
`redaccion_rag_v1.md` tiene dos reglas que en estos casos se contradicen:

> **2.** Si el contexto no alcanza para responder, dígalo con naturalidad y
> sugiera que le pregunte de otra manera. Es preferible a inventar.
>
> **4.** Termine **siempre** citando la fuente… La cita no es opcional ni
> adorno.

El modelo cumple las dos a la vez, que es lo único que puede hacer con esas
instrucciones. **No está fallando: está obedeciendo.**

### Es la violación de un principio que ya estaba escrito

El encabezado de `app/services/orientacion.py` lo dice desde el ADR-0015:

> o se responde con la guía y se cita **toda** la respuesta, o responde el
> modelo y **no se cita absolutamente nada**, nunca medio mensaje de cada,
> y **el camino lo elige el código**, no el modelo: se mira si la
> recuperación trajo algo.

Aquí el código eligió «con respaldo» **mirando la similitud**, y el modelo
produjo de hecho una respuesta sin respaldo. Los dos creen estar en caminos
distintos, y el mensaje que sale es justo el «medio mensaje de cada» que el
diseño prohíbe.

La similitud es una medida de parecido, no de que el fragmento responda.
**Quien sabe si el contexto sirvió es el que lo leyó**, y ese es el modelo.

### Estaba anunciado y se dio por resuelto

El comentario de `RAG_UMBRAL_SIMILITUD` en `app/config.py` describe este
modo de fallo con estas palabras: «consultas que pasan el filtro, no
encuentran nada útil y responden "no tengo la información sobre eso" con
`Fuente: Jardín Botánico` al pie». Se atribuyó a los índices del corpus y
se dio por mitigado al quitarlos el 19/08/2026. **No lo estaba**: sigue en
6 de 20, ya sin índices.

## Decisión

**El modelo declara si pudo responder con el contexto. El backend decide
qué texto sale.** Es el mismo reparto que el ADR-0015 fijó para la
advertencia médica.

Tres partes:

1. **El prompt deja de mandar citar.** `redaccion_rag_v2.md` retira el
   «termine siempre citando la fuente» y le prohíbe escribir la palabra
   *Fuente*. En su lugar: si el contexto no alcanzaba, que termine con la
   marca `[[SIN_RESPALDO]]` en un renglón aparte.
2. **El backend pone la línea.** Si no hay marca, `orientacion.py` añade
   `Fuente: <entidad>`; si la hay, no añade nada. En los dos casos retira
   la marca y **también cualquier línea `Fuente:` que el modelo haya
   escrito de su cuenta**, para que el resultado no dependa de que obedezca.
3. **La entidad sale de la tabla `fuente`**, por la clave foránea del
   fragmento mejor puntuado, y no de lo que el modelo transcriba de la
   etiqueta `[OFICIAL – …]`. Es para lo que el ADR-0009 la dejó fuera del
   texto vectorizado.

### La marca es negativa, y es deliberado

Se marca **no haber podido responder**, y no lo contrario. Marcar el uso
del contexto parece más natural y es peor, y la razón es qué pasa cuando el
modelo se salta la marca:

| Marca | Si el modelo la olvida | Consecuencia |
|---|---|---|
| «usé el contexto» | No se cita | Se pierde la atribución en respuestas **buenas**, que son la mayoría |
| «no pude responder» | Se cita | Se vuelve al comportamiento de hoy, **solo en ese caso** |

Es decir: con la marca negativa, **un fallo del modelo degrada al
comportamiento actual en vez de introducir uno nuevo**, y solo en las
respuestas que iban a ser malas de todos modos. Con la positiva, el fallo
estropea las que ya funcionaban.

## Alternativa descartada

**Arreglarlo solo en el prompt**, haciendo condicional la regla 4. Cuesta
un archivo y ningún código.

Se descarta porque este proyecto ya midió dos veces que una regla de prompt
sola no basta a temperatura 0.4:

- Los dos prompts prohíben copiar la etiqueta `[OFICIAL – …]` y **se cuela
  igual**. Por eso existe `limpiar_etiquetas`, cuyo propio comentario dice:
  «los prompts se lo prohíben, que es la defensa principal. Esto es la red».
- El ADR-0015 sacó la advertencia médica del prompt al backend por lo
  mismo: «una advertencia que falte una vez de cada diez es peor que no
  tenerla, porque falta justo cuando hace falta».

Una cita que sobre una de cada diez veces tiene el mismo problema. **El
cambio de prompt no es la alternativa: es la primera de las tres partes de
esta decisión.** Lo que se descarta es quedarse solo con ella.

## Consecuencias

- **La línea de la fuente es ahora determinista.** Su presencia, su forma y
  el nombre de la entidad no dependen del modelo.
- **Un prompt nuevo, `redaccion_rag_v2.md`.** El `v1` se queda en el
  repositorio como historial citable y no lo carga nadie (`CLAUDE.md` §11).
- **Se puede medir.** El banco de 20 preguntas da el número a batir: 6 de
  20 citas indebidas. Es la primera decisión del proyecto que nace con su
  medición previa ya hecha.
- **Queda un residuo declarado.** El backend sabe si el modelo declinó,
  pero no sabe si el modelo *acertó* al declinar. Una respuesta que el
  contexto sí sostenía y el modelo no supo redactar sale ahora sin cita, y
  eso no lo detecta nada. Es menos grave que el problema que resuelve.
- **No toca el umbral ni el top-k.** `RAG_UMBRAL_SIMILITUD` sigue decidiendo
  por qué camino entra la consulta; lo que cambia es que el camino con
  respaldo ya puede terminar sin cita.
