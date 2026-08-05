# ADR-0010. El umbral de similitud baja a 0.68, y sin respaldo no se responde

- **Estado:** Aceptada
- **Fecha:** 2026-08-04
- **Fase:** 6 (implementa la recuperación del CU2)
- **Depende de:** [ADR-0009](0009-ingesta-de-fuentes-oficiales.md)

## Contexto

La Fase 4, §7 fija un umbral de similitud coseno de **0.7**, declarado
valor inicial calibrable (CLAUDE.md §8). El spike del 29/07/2026 lo
respaldó con la primera evidencia: documento pertinente 0.797, mismo
dominio pero otro tema 0.607, ajeno al dominio 0.536. El umbral caía casi
centrado en el hueco.

Aquella evidencia tenía un defecto que solo se ve al compararla con un
corpus real: **los documentos de prueba estaban escritos a mano para el
spike**, con casi las mismas palabras de la consulta. El "documento
pertinente" decía *"el pulgón se reconoce por insectos verdes agrupados en
los brotes tiernos"* frente a la consulta *"a mi mata de tomate le salieron
unos bichitos verdes"*. Eso no mide la recuperación: mide el parecido de
dos frases escritas a la vez.

Con el corpus real ya ingerido (ADR-0009, 81 fragmentos), esa misma
consulta —la insignia del CU2— **no recuperaba nada**: su mejor fragmento
puntuaba 0.6911. Y los fragmentos que quedaban fuera sí trataban del manejo
de plagas.

## Decisión 1. El umbral baja a 0.68

Medido con [`scripts/calibrar_umbral.py`](../../scripts/calibrar_umbral.py)
sobre 12 consultas que el CU2 debe responder y 6 que no, todas escritas en
el registro de las usuarias reales —informales, sin tildes, sin vocabulario
técnico—:

| | mejor similitud |
|---|---|
| Positivas (12) | 0.6854 – 0.7673, mediana 0.7132 |
| Negativas (6) | 0.5318 – 0.6752, mediana 0.5736 |

| Umbral | Responde | Falsos positivos | Fragmentos/consulta |
|---|---|---|---|
| 0.65 | 12/12 | 1/6 | 3.9 |
| **0.68** | **12/12** | **0/6** | **3.1** |
| 0.70 | 8/12 | 0/6 | 1.5 |

**0.68 es el único valor que responde todas las consultas legítimas sin
dejar pasar ninguna ajena.** Con 0.70, cuatro de doce consultas del CU2 se
quedan sin respuesta.

Es un ajuste de dos centésimas sobre el valor de la Fase 4, no un cambio de
criterio: la separación entre lo pertinente y lo ajeno sigue existiendo y
sigue siendo amplia. Lo que cambia es dónde cae, unas siete centésimas más
abajo que con material sintético.

**El margen es estrecho y hay que declararlo:** entre la peor positiva
(0.6854) y la mejor negativa (0.6752) hay **una centésima**. Esa negativa
es el caso difícil que se incluyó a propósito —"dónde me inscribo para que
me regalen una compostera"—, que habla de algo que el corpus sí cubre pero
pide un trámite que no. Descartándola, la siguiente negativa está en
0.5947, muy lejos. El umbral es sólido frente a lo claramente ajeno y
justito frente a lo que roza el dominio.

### Configurable por entorno

`RAG_UMBRAL_SIMILITUD` y `RAG_TOP_K` son variables de entorno con valor por
defecto en [`app/config.py`](../../app/config.py), por el mismo criterio que
`GEMINI_GENERATIVE_MODEL` y por el contrario que el modelo de embeddings
(ADR-0007): **cambiarlas no invalida nada de lo almacenado**, y la Fase 4
las declara calibrables. Poder ajustarlas en Railway sin desplegar es justo
lo que la Fase 7 va a necesitar.

La configuración rechaza al arrancar un umbral fuera de [0, 1]. Sin esa
comprobación, escribir una distancia donde va una similitud no daría
error: el CU2 respondería con cualquier fragmento o con ninguno.

## Decisión 2. Sin respaldo oficial no se responde

Cuando nada supera el umbral, **no se le pregunta al modelo de todos
modos**. Se responde con un texto fijo que reconoce que no se sabe y ofrece
reformular.

Conviene ser preciso, porque matiza la jerarquía de CLAUDE.md §6. Esa
jerarquía admite un tercer nivel —conocimiento del modelo con advertencia
explícita de que no está verificado— y aquí se decide **no usarlo en el
CU2**:

- El propósito del prototipo es orientar con una guía oficial detrás. Una
  respuesta sin respaldo, aunque vaya advertida, no es el producto que se
  está evaluando.
- La advertencia protege al sistema, no a la usuaria. El perfil real
  —adultas mayores, apropiación tecnológica limitada— no discrimina bien
  entre un consejo respaldado y uno advertido dentro del mismo mensaje.
- Es la salvaguarda barata frente a la consulta que roza el dominio sin
  pertenecerle, que en la calibración se quedó a una centésima de colarse.
  Si algún día se cuela, cae en el texto fijo y no en una recomendación
  agronómica improvisada.

El tercer nivel de la jerarquía queda disponible para el agente, que puede
usarlo en conversación general. Lo que no puede es sostener una
recomendación técnica.

## Consecuencias

- El CU2 funciona de punta a punta. Probado con
  [`scripts/spike_orientacion.py`](../../scripts/spike_orientacion.py)
  contra la base y la API reales: las cuatro consultas legítimas reciben
  respuesta apoyada en el documento y con la fuente citada; las dos ajenas
  caen en el texto fijo.
- La atribución se exige en el prompt con formato fijo (`Fuente: entidad`).
  En la primera versión salía inconsistente, y la cita no es adorno: es lo
  que sostiene la jerarquía de fuentes.
- **Hay que revalidar el umbral en la Fase 7** con consultas reales de las
  usuarias, no con las que imaginó el autor. Un margen de una centésima no
  aguanta suposiciones sobre cómo pregunta la gente.
- Si se ingiere una segunda fuente oficial, el umbral debe remedirse: el
  corpus cambia y con él la distribución de similitudes.

## Pendiente de corrección documental

- **Fase 4, §7** — el umbral pasa de 0.7 a 0.68, y la evidencia que lo
  respaldaba se sustituye por la medida contra el corpus real.
- **Fase 2, CU2** — no contempla el caso de que no haya fuente que
  responda. Se resuelve con texto fijo, no con conocimiento del modelo.

## Alternativas descartadas

- **Mantener 0.7.** Deja sin respuesta un tercio de las consultas
  legítimas, incluida la que el propio proyecto usa de ejemplo desde la
  Fase 1. Un CU2 que calla ante "mi tomate tiene bichos" no cumple su
  propósito.
- **Bajar a 0.65 o menos.** Deja pasar la consulta de trámite, que
  recibiría una respuesta agronómica sin venir a cuento. Y con 0.60 el
  sistema recupera cuatro fragmentos para cualquier cosa, con lo que el
  umbral deja de filtrar y quien decide pasa a ser solo el top-k, que es
  exactamente el defecto ya diagnosticado en la colección comunitaria.
- **Umbral propio para cada colección.** El spike de la Fase 5 comprobó que
  no hace falta para la comunitaria. Se revisará al implementar el CU4, con
  fragmentos comunitarios reales y no imitados.
- **Responder con conocimiento del modelo advertido.** Descartada en la
  decisión 2.
