# ADR-0027. El agente busca antes de decir que no tiene un dato

- **Estado:** Aceptada
- **Fecha:** 2026-10-06
- **Fase:** 7
- **Origen:** incidencia INC-025

## Contexto

El 25/09/2026, al medir el top-k (ADR-0026), se vio que la consulta real
«Cual es la dirección de enlace al JBB para obtener el formulario» **no
llegaba a la guía**: el agente contestaba por su cuenta que no tenía el
enlace. El Protocolo de espacio público sí lo trae, y trae además el
correo de renovación, el correo de cada localidad y los pasos de la
solicitud.

Medido el 06/10/2026 con `calibrar_enrutamiento --grupo tramites`, cinco
repeticiones, el defecto **no es de una pregunta sino de una clase**: las
que piden un **dato concreto** —un enlace, un correo— no van a la guía, y
las que piden un **procedimiento** —«cómo pido permiso para sembrar en un
espacio público»— sí.

| Pregunta | `agente_v2` |
|---|---|
| El mensaje real del formulario, literal | 1 de 5 a la guía |
| A qué correo escribir para renovar la autorización | 0 de 5 |
| A qué correo del Jardín Botánico escribir desde Bosa | 0 de 5 |
| Dónde se consigue el formulario para una huerta en un parque | 5 de 5 |
| Cómo pedir permiso para sembrar en un espacio público | 5 de 5 |

Dos cosas del `v2` empujan al modelo a contestar «no lo tengo» sin
buscar. La lista de `consultar_orientacion` solo habla de cultivar
—plagas, riego, abonos—, y un correo no es nada de eso. Y la regla 6 y el
cierre del prompt le enseñan a reconocer con franqueza lo que no puede
hacer, que es correcto para un trámite que el sistema no ejecuta y
equivocado para un dato que el sistema sí tiene.

**Lo que no cuadra, y queda declarado.** La conversación guardada
muestra que el 18/09/2026, día en que la persona hizo esa pregunta, el
asistente **sí** consultó la guía: su respuesta parafrasea el Protocolo.
El `v2` entró al día siguiente. Es compatible con que el `v2` causara el
defecto, pero **no se comprobó** midiendo el `v1`, y una sola respuesta
no es una medida.

## Decisión

**`agente_v3.md`** sustituye al `v2`, con tres cambios:

1. La descripción de `consultar_orientacion` añade los **trámites y datos
   de contacto** de la agricultura urbana: permisos para sembrar en
   espacio público, formularios, correos, entidades.
2. Una regla nueva, la 6: **nunca decir que no se tiene un dato sin
   haberlo buscado**. Si piden un enlace, un correo, una dirección o un
   formulario, se llama a la guía antes de decir nada. Si la guía no lo
   trae, el CU2 ya lo dice.
3. La regla de no prometer pasa a ser la 7, sin cambios de texto.

De paso, la frase que describía a las personas usuarias como «mujeres
adultas mayores» pasa a «personas adultas mayores» (CLAUDE.md §1).

**No se toca la descripción de la función en `agente.py`.** Es código y
no está versionada con el prompt: cambiarla habría movido también el
`v2`, y la comparación dejaría de ser en las mismas condiciones.

## Por qué no abre la puerta a inventar un correo

Mandar más preguntas a la guía tiene un riesgo evidente: si la guía no
trae el dato, el CU2 responde con el modelo sin respaldo, y un modelo sin
respaldo es justo quien inventaría un correo. **Ese camino ya está
cerrado**: `respuesta_general_v1.md` trata los trámites como fuera de
tema y su regla 2 le prohíbe dar direcciones, teléfonos, oficinas o
requisitos. Un trámite sin fragmento termina en «no lo sé», no en un dato
supuesto.

## Lo que se midió

**El grupo de trámites, `v2` frente a `v3`**, cinco repeticiones:
**26/40 frente a 40/40**. Los tres controles del grupo —pedir que se
reporte una pregunta, pedir que se guarde para después y dar las
gracias— siguen sin herramienta en los dos: la regla de no prometer no
se resiente.

**La regresión sobre los otros cuatro grupos**, cuatro repeticiones:
**140/140 con el `v2` y 140/140 con el `v3`**: comunidad (CU4 y CU7), mi huerta
frente a registro (CU8 y CU3), los ejemplos del cierre del CU3 y los
controles, saludo incluido. Ningún fallo y ningún error de la API.

**De punta a punta**, con el `v3`, por `procesar_evento` y dos
repeticiones de las tres preguntas que fallaban: cinco respuestas dan el
dato y la sexta fue un corte de la API de Gemini, no del enrutamiento. El
enlace que da para Bosa (`forms.office.com/r/GnBmMa7yNW`) y el correo de
la localidad (`riobogotasur@jbb.gov.co`) están literalmente en el
Protocolo, y en su maquetación cada grupo de localidades precede a su
enlace y a su correo: el modelo los asignó bien.

## Consecuencias

- La persona recibe el enlace o el correo que la guía trae, con la cita.
- **El ADR-0026 pierde su caso de origen como argumento**: la pregunta del
  formulario ya llega a la recuperación. Medir si con top-k 4 el
  fragmento quedaría fuera es una pregunta nueva, que no se ha hecho.
- Lo que no se arregla: el agente sigue sin saber qué contiene la guía.
  La regla funciona para la clase que se nombra —enlaces, correos,
  formularios—; otra clase de dato concreto podría repetir el patrón.
