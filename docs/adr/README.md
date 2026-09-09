# Registro de decisiones de arquitectura (ADR)

Cada archivo recoge una decisión que no está resuelta —o que quedó
contradictoria— en los documentos de las fases cerradas. Existen para que
toda decisión de implementación pueda rastrearse hasta una fase
documentada y para poder incorporarlas al documento de grado.

Cuando un ADR corrige un documento de `docs/`, **prevalece el ADR** y el
documento queda marcado como pendiente de corrección.

| ADR | Título | Estado | Fase de origen |
|---|---|---|---|
| [0001](0001-barrio-no-filtra-recuperacion.md) | El barrio no filtra la recuperación comunitaria | Aceptada | Fase 2 / Fase 4 |
| [0002](0002-catalogo-de-barrios.md) | Catálogo de barrios como tabla, no como tipo ENUM | Aceptada | Fase 3 / Fase 4 |
| [0003](0003-consentimiento-sin-insistencia.md) | Consentimiento sin insistencia ante el rechazo | Aceptada | Fase 2 (CU1) |
| [0004](0004-cultivo-y-fragmento-comunitario.md) | Se conserva `cultivo`; un fragmento comunitario por huerta | Aceptada (parcial) | Fase 3 |
| [0005](0005-procesamiento-asincrono-e-idempotencia.md) | Procesamiento asíncrono del webhook e idempotencia por `wamid` | Aceptada, sin puntos abiertos | Sin respaldo documental |
| [0006](0006-saludo-y-ayuda-sin-modelo.md) | El saludo y la ayuda se detectan sin el modelo | Aceptada | Sin respaldo documental |
| [0007](0007-modelo-de-embeddings-fijo-en-codigo.md) | Se mantiene `gemini-embedding-001`, fijo en código | Aceptada | Fase 3 / Fase 4 |
| [0008](0008-borrador-de-registro-y-una-huerta-por-usuaria.md) | Borrador de registro en la base, y una huerta por usuaria | Aceptada | Fase 2 (CU3) |
| [0009](0009-ingesta-de-fuentes-oficiales.md) | La ingesta de fuentes oficiales es un script local y repetible | Aceptada | Fase 4 (§7) |
| [0010](0010-umbral-de-similitud-recalibrado.md) | El umbral baja a 0.68, y sin respaldo oficial no se responde | Aceptada | Fase 4 (§7) / Fase 2 (CU2) |
| [0011](0011-fragmento-comunitario-solo-especies.md) | El fragmento comunitario lleva solo las especies | Aceptada; sustituye la composición del [0004](0004-cultivo-y-fragmento-comunitario.md) | Fase 3 / Fase 2 (CU4) |
| [0012](0012-memoria-de-conversacion.md) | La memoria empieza tras la compuerta, y el `wamid` sale de `mensaje` | Aceptada | Fase 3 / Fase 4 (§6) |
| [0013](0013-agente-orquestador.md) | El agente enruta y no relata; el mensaje completo conserva su oportunidad | Aceptada | Fase 2 (§4) |
| [0014](0014-catalogo-de-fuentes-oficiales.md) | Las fuentes oficiales se declaran en un catálogo, y sus parámetros son mediciones | Aceptada; amplía el [0009](0009-ingesta-de-fuentes-oficiales.md) | Fase 4 (§7) |
| [0015](0015-advertencia-de-contenido-medico.md) | Toda respuesta del CU2 que hable de salud lleva advertencia, puesta por el backend | Aceptada | Sin respaldo documental |
| [0016](0016-onboarding-de-preguntas-cerradas.md) | El registro empieza con un onboarding de preguntas cerradas | Aceptada | Fase 2 (CU3) |
| [0017](0017-aviso-de-espera.md) | El aviso de espera se envía y no se recuerda | Aceptada solo para la nota de voz; el del RAG se retiró el mismo día | Sin respaldo documental |
| [0018](0018-sin-fecha-de-siembra.md) | La fecha de siembra sale del CU3 | Aceptada; extiende el [0011](0011-fragmento-comunitario-solo-especies.md) al CU3 | Fase 4 (Tabla 3) / Fase 3 |
| [0019](0019-aviso-cuando-la-base-no-responde.md) | Cuando la base no responde, se reintenta y se le avisa a la usuaria | Aceptada; el freno de la decision 5 se retiro el mismo dia | Sin respaldo documental |
| [0020](0020-indices-fuera-del-corpus-y-umbral-a-066.md) | Los renglones de índice salen del corpus, y el umbral baja a 0.66 | Aceptada; **la calibración no está cerrada**. Obsoleta la medición del [0010](0010-umbral-de-similitud-recalibrado.md) | Fase 4 (§7) / ADR-0010 |
| [0021](0021-listado-de-la-comunidad-y-busqueda-por-cultivo.md) | El listado de la comunidad lo compone el código, y la búsqueda por cultivo se separa como CU7 | Aceptada; retira el respaldo por listado del [0011](0011-fragmento-comunitario-solo-especies.md) | Fase 2 (CU4) / ADR-0011 |

## Documentos pendientes de corrección

El consolidado de lo que estos ADR obligan a ajustar en los `.docx` vive en
**[`docs/correcciones-a-los-documentos.md`](../correcciones-a-los-documentos.md)**,
organizado por fase y sección.

Estaba aquí hasta el 23/08/2026 y se movió para que haya **un solo sitio que
mantener**: el listado se estaba quedando viejo cada vez que un ADR nuevo
cambiaba un número, y este proyecto ya arrastra bastantes cifras duplicadas.

Al añadir un ADR que corrija un documento de fase, la entrada va allí.
