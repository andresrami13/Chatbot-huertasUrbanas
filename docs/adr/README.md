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
| [0005](0005-procesamiento-asincrono-e-idempotencia.md) | Procesamiento asíncrono del webhook e idempotencia por `wamid` | Aceptada, con puntos abiertos | Sin respaldo documental |

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
- **Fase 3, §3 y Fase 4, §7** — citan `text-embedding-004`, dado de baja.
- **Fase 4, Tabla 3** — su justificación del valor cerrado queda anulada
  por ADR-0001 y sustituida por ADR-0002.
- **Anteproyecto, §7.1** — lista seis barrios; omite Los 3 Sectores
  (ADR-0002).
- **Anteproyecto, §7.2 y §8** — excluyen la entrada por voz, ya incorporada
  al alcance por la Fase 2.
- **Anteproyecto, §7.2 y §10.2** — dan Railway por gratuito.
