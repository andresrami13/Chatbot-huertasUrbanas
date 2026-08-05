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
