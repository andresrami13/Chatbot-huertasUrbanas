# El informe vive en `docs/`

El informe de la prueba formativa de usabilidad es
**[`docs/prueba_formativa.md`](../../docs/prueba_formativa.md)**
(`EVF-CHU-001`), junto a los demás documentos de prueba del proyecto.

Este archivo queda como puntero y no repite ningún número: dos documentos
con las mismas cifras se desincronizan a la primera, y el §12 de
`CLAUDE.md` no admite contenido duplicado.

Lo que vive en esta carpeta son las salidas de
`python -m scripts.evaluacion_formativa`:

| Archivo | Contenido | Versionado |
|---|---|---|
| `mapeo_esquema.md` | Punto de control de la Fase 1: tabla o columna → concepto, secuencias mínimas por tarea y mensajes de error del bot | Sí |
| `parametros.json` | Instantánea de los datos, cuenta excluida y parámetros | Sí |
| `categorias_propuestas.json` | La clasificación de los 50 mensajes libres que propuso la IA, congelada para poder auditarla | Sí |
| `rubrica_respuestas.json` | La calificación de las 20 consultas agroecológicas | Sí |
| `embudo_onboarding.csv` | El embudo del onboarding, paso a paso | Sí |
| `clasificacion_mensajes_libres.csv` | Los 50 mensajes libres, con lo que quería cada persona | **No** |
| `rubrica_T3.csv` | Las 20 consultas con su pregunta, su respuesta y su calificación | **No** |
| `intentos_tareas.csv` | Una fila por intento, con su unidad de medida | **No** |
| `tiempos_respuesta_sistema.csv` | Un par por mensaje entrante | **No** |
| `asistencia.csv` | Asistencia recibida, por participante | **No** |
| `candidatas_sus.csv` | Las candidatas al SUS, solo seudónimos | **No** |

Los seis últimos llevan texto literal de la conversación o la huella de
identidad abreviada, así que `.gitignore` los deja fuera: las participantes
autorizaron el tratamiento de sus datos, no su publicación, y este
repositorio es público.
