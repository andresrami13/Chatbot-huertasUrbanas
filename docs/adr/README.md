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

## Documentos pendientes de corrección

Consolidado de lo que estos ADR obligan a ajustar en los `.docx`:

- **Fase 2, CU2, paso 1** — dice "datos comunitarios del barrio"; el barrio
  no filtra (ADR-0001).
- **Fase 2, CU1, flujo alternativo 3a** — dice que el ciclo se repite hasta
  que el usuario acepte (ADR-0003).
- **Fase 2, CU3 y §5.4** — atribuyen al RLS la protección de los datos
  personales; la Fase 3 §5.1 lo desmiente.
- **Fase 3, §2 (C4) y Tabla 2** — no contemplan el procesamiento asíncrono
  ni el despachador (ADR-0005).
- **Fase 2, CU1 y CU5** — no resuelven cómo se detecta el saludo o la ayuda
  de alguien que aún no ha autorizado, siendo el CU5 el único caso de uso
  sin precondición (ADR-0006).
- **Fase 3, §3 y Fase 4, §7** — citan `text-embedding-004`, dado de baja;
  se sustituye por `gemini-embedding-001` truncado a 768 (ADR-0007).
- **Fase 4, Tabla 3** — su justificación del valor cerrado queda anulada
  por ADR-0001 y sustituida por ADR-0002.
- **Anteproyecto, §7.1** — lista seis barrios; omite Los 3 Sectores
  (ADR-0002).
- **Anteproyecto, §7.2 y §8** — excluyen la entrada por voz, ya incorporada
  al alcance por la Fase 2.
- **Anteproyecto, §7.2 y §10.2** — dan Railway por gratuito.
- **Fase 4, §7** — el troceo de 300–500 tokens no dice cómo se cuentan. La
  aproximación estándar de 4 caracteres por token desvía el resultado lo
  bastante para sacar la mitad del corpus del intervalo (ADR-0009).
- **Fase 4, §7** — el umbral pasa de 0.7 a **0.68**. El valor original se
  respaldó con material sintético; contra el corpus real dejaba sin
  responder 4 de 12 consultas legítimas del CU2 (ADR-0010).
- **Fase 2, CU2** — no contempla qué hacer cuando ninguna fuente responde.
  Se resuelve con texto fijo y no con conocimiento del modelo (ADR-0010).
- **Fase 3 / ADR-0004** — el texto del fragmento comunitario ya no incluye
  el nombre de la huerta, el barrio ni las fechas: solo las especies
  (ADR-0011).
- **Fase 4, §7** — la colección comunitaria lleva **umbral propio** (0.65).
  El spike de la Fase 5 concluyó que no hacía falta, pero lo midió sobre el
  formato con plantilla (ADR-0011).
- **Fase 3, §3** — la tabla `mensaje` no guarda el `wamid`, sino su huella.
  El `wamid` contiene el teléfono del remitente (ADR-0012).
- **Fase 4, §6** — la ventana de diez no precisa si son mensajes o turnos,
  ni qué entra en ella. Son mensajes, el último es el de la usuaria, y nada
  anterior al consentimiento se registra (ADR-0012).
- **Fase 3, §5.2** — el modelo de seguridad no contempla que la
  conversación quede almacenada. `mensaje.contenido` es texto libre en
  claro, y la minimización solo gobierna lo que el sistema pide, no lo que
  la usuaria decide contar (ADR-0012).
- **Fase 2, §4** — las herramientas del agente son **cuatro**, no tres. El
  saludo posterior al consentimiento no cabía en ninguna de las tres sin
  incumplir la propia Fase 2 (ADR-0013).
- **Fase 4, §7** — el umbral se calibró sobre mensajes completos, y el
  agente puede recortar la consulta. El recorte de un mensaje de doble
  intención cayó a 0.6796, cuatro diezmilésimas por debajo (ADR-0013).
- **Fase 2, CU3** — describe un único flujo conversacional. El registro
  empieza ahora con un onboarding de tres preguntas cerradas, una por
  mensaje; el flujo conversacional atiende lo que ella cuente después
  (ADR-0016).
- **Anteproyecto, §5.3.1** — lista `Los 3 Sectores`, que no aparece en el
  listado oficial de barrios de Bosa. Corrige en sentido contrario al
  ADR-0002: era el §7.1 el que acertaba al omitirlo (ADR-0016).
- **Anteproyecto, §7.1** — acota el alcance a la UPZ 84 Bosa Occidental; el
  catálogo de barrios pasa a cubrir la localidad de Bosa entera, 312
  barrios (ADR-0016).
- **Fase 3, §2 (C4)** — el procesamiento asíncrono se describe desde el lado
  del webhook, para que Meta no reintente, y no desde el lado de quien
  espera: nada dice qué ve la usuaria durante los trece segundos que tarda
  el camino con RAG (ADR-0017).
- **Fase 4, Tabla 3** — la extracción ya no devuelve la fecha de siembra ni
  la marca de imprecisión. Era un dato de solo escritura, y el ADR-0011 ya
  había medido que empeoraba la recuperación (ADR-0018).
- **Fase 3, §3** — `cultivo` pierde `fecha_siembra_aprox` y
  `fecha_imprecisa` en la migración `008` (ADR-0018).
- **Fase 2, CU3** — el resumen de confirmación ya no muestra la fecha de
  cada cultivo, solo el nombre de la planta (ADR-0018).
- **Fase 3, §5.2 y Fase 4, Tabla 3** — no contemplan que el nombre de la
  usuaria se muestre en la conversación. El saludo personalizado se
  antepone al enviar y **no** se registra en `mensaje`, o el nombre cifrado
  quedaría en claro allí (ADR-0016).
