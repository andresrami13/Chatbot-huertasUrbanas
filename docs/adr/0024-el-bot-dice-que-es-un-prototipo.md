# ADR-0024. El bot dice que es un prototipo, y el alcance es Bosa entera

- **Estado:** Aceptada
- **Fecha:** 2026-09-19
- **Fase:** 7
- **Origen:** sin respaldo documental — corrige la presentación del
  asistente que fijan la Fase 2 (CU5) y la Fase 4, y el alcance «UPZ 84
  Bosa Occidental» del anteproyecto

## Contexto

El bot está en un número de producción desde el 09/09/2026 y **se repartió
sin decir en ninguna parte que es un prototipo académico**. En diez días
escribieron **once personas**, siete de ellas con consultas agroecológicas
reales, y nada en la conversación les dice que lo que están usando es un
trabajo de grado en pruebas.

La trazabilidad de `mensaje` del 19/09/2026 —268 mensajes— muestra que no
es una precaución teórica:

- **De 17 respuestas del CU2 que citan una fuente oficial, 12 dicen «no
  tengo esa información»** y firman igual con `Fuente: Jardín Botánico de
  Bogotá`. La usuaria recibe una no-respuesta con sello de fuente
  verificada.
- **El bot prometió dos veces algo que no existe.** A la pregunta «¿puedes
  reportar a tu fuente que tienes una pregunta para la cual no tienes
  respuesta?» respondió: *«Las preguntas para las que aún no tengo
  respuesta quedan registradas para que el equipo pueda revisar y mejorar
  la guía.»* **No hay ningún registro de preguntas sin respuesta.** Es el
  modo de fallo del CLAUDE.md §8 —el agente no llamó a ninguna herramienta
  y se envió el texto libre del modelo— ocurriendo con `gemini-3.6-flash`,
  que en `calibrar_enrutamiento` daba 76/76.
- **Una usuaria abandonó el onboarding** tras recibir tres veces «No
  encontré ese barrio en mi lista» por escribir *Bosa recreo* y *Bosa
  despensa*. Ninguno de los dos está en las 313 filas del catálogo.

Arreglar cada uno de esos defectos es trabajo de la Fase 7 y no cabe
ahora. Lo que sí cabe, y no puede esperar, es **dejar de presentarlo como
algo terminado**.

## Decisión

### 1. El asistente declara que está en pruebas, en cuatro sitios y no más

El criterio es **decirlo completo una vez, corto al reincidir, y otra vez
en el punto donde algo falla**. Nunca en medio de una respuesta buena.

| Sitio | Qué dice | A quién alcanza |
|---|---|---|
| `SOLICITUD_CONSENTIMIENTO` | El marco completo, con la Universidad Distrital | Solo quien llegue de ahora en adelante |
| `SALUDO_PERSONALIZADO` | Un renglón, una vez cada 24 h | **Las que ya están registradas** |
| `BIENVENIDA` (CU5) | Media línea en el renglón que ya existía | Todo el mundo, incluso sin autorizar |
| `ONBOARDING_BARRIO_SIN_CANDIDATOS` | Que la lista de barrios está incompleta | Quien tropiece con el hueco |

**Los dos primeros no son intercambiables, y esa es la razón de que sean
dos.** El texto del consentimiento no se repite nunca: las once personas
que ya pasaron la compuerta no volverían a verlo. Y la bienvenida tampoco
las alcanza: tres de las siete que han consultado entraron preguntando
directo, sin saludar, y no la han visto desde el primer día. El saludo de
las 24 horas es el único canal que llega a quien ya está dentro.

En el consentimiento va **primero, antes de pedir el dato**: saber que el
asistente está en pruebas es parte de lo que ella autoriza. Nombrar a la
Universidad Distrital juega además a favor de la Ley 1581 de 2012, que
pide identificar al responsable del tratamiento.

### 2. El agente no puede prometer nada

Regla 6 de `agente_v2.md`, entre las que no puede romper:

> **Nunca prometa algo que usted no hace.** Usted no reporta preguntas, no
> le avisa a nadie, no pasa razones a ningún equipo, no abre quejas ni deja
> nada pendiente para después. Tampoco aprende de lo que ella le cuenta.

Y en «Cuando sí escribe usted», la contraria: si le preguntan si se
equivoca, si está terminado o quién lo hizo, **que lo diga**.

Esta regla es la que hace honesto el resto. Sin ella, invitar a la usuaria
a contar lo que salga mal terminaría en una segunda promesa falsa.

### 3. El alcance que el bot declara es la localidad de Bosa

Desaparece **«UPZ 84 Bosa Occidental»** de todo lo que la usuaria lee y de
los prompts vigentes. Queda «la localidad de Bosa».

No es una ampliación de alcance: es **poner al día lo que el sistema ya
hacía**. El catálogo de barrios son los 312 de la localidad entera desde el
ADR-0016 (17/08/2026), y las usuarias reales están en PIAMONTE I ETAPA,
VILLA DE SUAITA, CHICO SUR y LA PAZ. Decir «Bosa Occidental» describía un
alcance que el sistema había dejado de tener un mes antes.

## Consecuencias

- **Hay que declararlo en el documento de grado.** La Fase 2 (CU5) y la
  Fase 4 fijan cómo se presenta el asistente y no dicen «prototipo» en
  ninguna parte; el anteproyecto acota el alcance a la UPZ 84. Van las dos
  cosas a `docs/correcciones-a-los-documentos.md`.
- **Ayuda a la evaluación en vez de estorbarla.** La ronda SUS todavía está
  sin decidir, así que poniéndolo ahora **todas** las personas evaluadas
  habrán visto el mismo encuadre. Hacerlo a mitad de la evaluación habría
  dejado una mitad de respuestas de gente que creía usar un servicio
  terminado y otra mitad que no, y el ≥68 dejaría de ser comparable
  consigo mismo.
- **El prompt del agente pasa a `agente_v2.md`.** El `v1` se queda en el
  repositorio como historial citable, igual que `extraccion_v1/v2` y
  `redaccion_comunidad_v1`, y por eso conserva el «UPZ 84 Bosa Occidental»
  original: el historial no se reescribe.
- **Se acepta una redundancia conocida.** Si una usuaria registrada saluda,
  el saludo de las 24 h se antepone a la bienvenida y las dos dicen que
  está en pruebas. Pasa una vez al día y solo a quien salude en vez de
  preguntar. Evitarlo exigiría que `mostrar_ayuda` se saltara el saludo,
  que es código y no texto.
- **El texto del barrio no ofrece salida, a propósito.** Decirle «si no
  aparece, seguimos sin barrio» sería prometer algo que hoy no existe: la
  única escapatoria es la opción «Mi barrio no está en la lista», que solo
  sale cuando hay candidatos que listar.

## Lo que este ADR no resuelve

- **Los doce «no tengo esa información» firmados por el Jardín Botánico.**
  El aviso de prototipo los hace más llevaderos, no los arregla. La causa
  está en `orientacion.py`: en cuanto un fragmento pasa el 0.66 el camino
  queda fijado, y el respaldo del modelo —que solo corre con cero
  fragmentos— no llega a intentarlo. **Es el arreglo de más valor que
  queda pendiente del CU2.**
- **`ONBOARDING_NUMERO_NO_ENTENDIDO`,** que salió 6 veces y cuatro
  seguidas a la misma persona, incluida una nota de voz que traía las tres
  respuestas del onboarding correctas. Cambiarle el texto tapa el síntoma.
  El arreglo real es que **cada respuesta del onboarding se pueda
  confirmar o rechazar en su momento**, en vez de esperar a los botones
  del final y obligarla a repetir las tres. Queda anotado y sin hacer.
- **El hueco del catálogo de barrios.** EL RECREO y LA DESPENSA no están
  entre las 313 filas. El texto ahora lo declara; el catálogo sigue igual.
