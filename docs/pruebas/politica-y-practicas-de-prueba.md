# Política y prácticas de prueba

| | |
|---|---|
| **Identificador** | `PPP-CHU-001`, versión 1.0 |
| **Emite** | Andrés Ramírez — autor del trabajo de grado |
| **Aprueba** | A. Ramírez — autor. **Única autoridad de aprobación** (desviación D-9) |
| **Estado** | Borrador para revisión |
| **Fecha** | 23/09/2026 |

## Historial de cambios

| Fecha | Versión | Cambio | Autor |
|---|---|---|---|
| 23/09/2026 | 1.0 | Versión inicial. Formaliza como proceso de prueba lo que el proyecto venía haciendo sin declararlo | A. Ramírez |

## Introducción

Este documento cumple **dos** de los ítems de información de
ISO/IEC/IEEE 29119-3:2021: la **política de prueba** (§6.2) y las
**prácticas organizacionales de prueba** (§6.3). Van fusionados, y la
propia norma lo permite: el §6.3.1 admite que las prácticas incorporen el
contenido de la política cuando no existe una política separada. La razón
aquí es que la «organización» es una sola persona.

Es el documento de nivel organizacional del que cuelgan el
[plan de pruebas](plan-de-pruebas.md) y todo lo que venga después.

## Alcance

Aplica a **todas** las actividades de prueba del prototipo de chatbot de
huertas urbanas de Bosa: estáticas y dinámicas, funcionales y no
funcionales, manuales y automatizadas, guionadas y no guionadas. No
gobierna el diseño metodológico de la evaluación de usabilidad con
usuarias —eso lo fija el anteproyecto—, pero **sí** la incorpora como un
tipo de prueba dentro de esta misma estrategia (§4.9).

## Referencias

**Externas**

- ISO/IEC/IEEE 29119-1:2013, *Software testing — Part 1: Concepts and definitions*
- ISO/IEC/IEEE 29119-2:2013, *Software testing — Part 2: Test processes*
- ISO/IEC/IEEE 29119-3:2021, *Software testing — Part 3: Test documentation*
- ISO/IEC/IEEE 29119-4, *Software testing — Part 4: Test techniques*
- ISO/IEC 25010, *System and software quality models*
- Ley 1581 de 2012 (Colombia), protección de datos personales

**Internas**

- Anteproyecto del trabajo de grado, §6.1.7 y Fase 7
- Fases de diseño 2 (funcional), 3 (técnico) y 4 (IA)
- [`CLAUDE.md`](../../CLAUDE.md) — decisiones no negociables y convenciones
- [`docs/adr/`](../adr/) — veinticuatro decisiones de implementación
- [`docs/ESTADO.md`](../ESTADO.md) — estado del trabajo
- [`docs/correcciones-a-los-documentos.md`](../correcciones-a-los-documentos.md)

## Glosario

Se usan los términos de ISO/IEC/IEEE 29119-1 §4 y 29119-3 §3. Tres
precisiones propias del proyecto:

- **Ítem de prueba**: el prototipo desplegado en Railway, los módulos de
  `app/`, los `scripts/` de ingesta y calibración, el esquema de `db/` y
  los documentos de fase.
- **Base de prueba**: los `.docx` de fase, los ADR —que **prevalecen**
  sobre los `.docx` cuando discrepan— y `CLAUDE.md`.
- **Consulta insignia**: la consulta del CU2 usada como referencia en las
  mediciones del umbral desde el 15/08/2026.

---

# 1. Declaración de conformidad

Se declara **conformidad adaptada** (*tailored conformance*) con
ISO/IEC/IEEE 29119-2:2013 §2.1.2 y ISO/IEC/IEEE 29119-3:2021 §4.1.3.

No se declara conformidad con 29119-1, que es **informativa** y no la
admite (§2 de esa parte); se cita solo como fuente de conceptos y
vocabulario.

## 1.1 Advertencia de ediciones

Las partes disponibles son **29119-2 de 2013** y **29119-3 de 2021**, y no
usan el mismo vocabulario de diseño de pruebas:

- La parte 2:2013 deriva **condiciones de prueba** en un proceso de seis
  actividades (TD1–TD6).
- La parte 3:2021 sustituyó las condiciones de prueba por **modelos de
  prueba** y redujo el proceso a cuatro actividades. La razón está en su
  Anexo T: los usuarios encontraban «confusas» las condiciones de prueba.

**Este proyecto adopta el vocabulario de 2021 —modelos de prueba— y toma
de la parte 2:2013 los procesos de gestión y de ejecución.** Se declara
aquí para que ningún documento posterior mezcle los dos.

## 1.2 Subconjunto al que se declara conformidad

| Proceso (29119-2) | ¿Se implementa? | Cómo |
|---|---|---|
| §6 Proceso organizacional de prueba | Sí | Este documento |
| §7.2 Planificación | Sí | [Plan de pruebas](plan-de-pruebas.md) |
| §7.3 Seguimiento y control | Adaptado | [`docs/ESTADO.md`](../ESTADO.md) y la bitácora de Railway (ver D-2) |
| §7.4 Cierre | Sí | Informe de cierre, al terminar la Fase 7 |
| §8.2 Diseño e implementación | Sí | Especificaciones de modelo, caso y procedimiento |
| §8.3 Entorno y datos | Sí | Requisitos e informes de preparación |
| §8.4 Ejecución | Sí | Resultados reales, resultado y bitácora |
| §8.5 Informe de incidencias | Sí | Registro de incidencias |

## 1.3 Desviaciones registradas, con su justificación

La norma exige que cada desviación lleve justificación y que se consideren
los riesgos asociados (29119-2 §2.1.2). Estas son todas.

| # | Desviación | Justificación | Riesgo asumido |
|---|---|---|---|
| **D-1** | La política de prueba y las prácticas organizacionales van en **un solo documento** | 29119-3 §6.3.1 lo permite explícitamente. La «organización» es un autor | Ninguno apreciable |
| **D-2** | El **informe de estado de prueba** no es un documento periódico con sus nueve secciones: lo cumplen `docs/ESTADO.md` y la bitácora | 29119-3 §7.3.1 NOTA admite que en entrega ágil el estado no se registre como documento, y lo cataloga como conformidad adaptada | Menor visibilidad del avance para terceros. Se acepta: no hay interesado externo que lo consuma antes del informe de cierre |
| **D-3** | **No hay entorno de prueba separado**: se usa la misma instancia de Supabase que produce | Presupuesto y alcance de prototipo. Una segunda instancia exigiría duplicar el corpus de 765 fragmentos y los 313 barrios, y volver a medir el umbral sobre ella | **Alto y declarado.** Ver el riesgo J-03 del plan y el informe de preparación del entorno |
| **D-4** | No se realizan pruebas de **rendimiento, carga, estrés, penetración ni recuperación ante desastre** | Exposición de riesgo baja: prototipo académico, 5 a 7 usuarias, sin transacción económica ni diagnóstico médico | Se desconoce el comportamiento con concurrencia. Aceptado y declarado como límite |
| **D-5** | **Independencia de nivel a)** — el autor prueba su propio producto (29119-1 Anexo E.3) | Trabajo de grado individual | **Alto y declarado.** Mitigado en §4.4 |
| **D-6** | Las pruebas de componente **no son repetibles bit a bit** en el sentido de la gestión de configuración: dependen de claves generadas en el momento | 29119-1 §5.3.3.3 admite excluir la prueba unitaria del requisito de repetibilidad si la excepción se declara | Ninguno: se prueban propiedades, no valores |
| **D-7** | Las mediciones que involucran al modelo generativo **no son deterministas**, y su criterio de aprobación es estadístico y no un `assert` | El agente corre a temperatura 0.7. Repetir es la única forma de medir (CLAUDE.md §12) | Un fallo aislado no prueba un defecto, ni un acierto aislado prueba la corrección |
| **D-8** | No se usa herramienta comercial de gestión de pruebas ni Postman | El anteproyecto §6.1.7 pide QA «sin recurrir a frameworks de evaluación automatizados que excedan el alcance del prototipo». Se sustituye por `pytest` y `TestClient`, versionados en el repositorio | Ninguno: la sustitución es más reproducible que la prevista |
| **D-9** | **No hay autoridad de aprobación distinta del autor**: el mismo que prueba aprueba el plan, las desviaciones y el cierre | Decisión del autor del 24/09/2026. El trabajo de grado es individual y no hay un segundo interesado que ejerza el rol | **Alto y declarado.** Un criterio de terminación puede acomodarse al resultado sin que nadie lo note. Se contrapesa escribiendo y fechando los criterios **antes** de ejecutar (§4.4), que reduce el riesgo pero no lo elimina |

**Las decisiones de adaptación las acuerdan los interesados pertinentes**
(29119-2 §2.1.2). Aquí el interesado pertinente es uno solo —el autor—, y
el acuerdo es esta tabla: queda **registrado y fechado**, que es lo que la
norma pide. La ausencia de un segundo par de ojos es ella misma una
desviación, la D-9, y no se disimula.

---

# 2. Política de prueba

## 2.1 Objetivos de la prueba

Probar aquí sirve a tres fines, en este orden:

1. **Proteger a la usuaria.** El perfil es de líderes de huerta,
   mayoritariamente adultas mayores, con apropiación tecnológica limitada.
   Un error no le cuesta dinero: le cuesta una cosecha, o —en el peor
   caso— la salud, porque las fuentes oficiales traen usos medicinales y
   toxicidad.
2. **Proteger su dato personal.** Ley 1581 de 2012, y el consentimiento
   como compuerta previa a todo procesamiento.
3. **Sostener las mediciones del trabajo de grado.** Un umbral, un
   enrutamiento o un corpus que no se puedan reproducir no valen como
   resultado.

## 2.2 Proceso de prueba

El de ISO/IEC/IEEE 29119-2:2013, en el subconjunto del §1.2. Las pruebas
estáticas siguen además ISO/IEC 20246 en lo aplicable.

## 2.3 Estructura de la organización de prueba

Un autor, que ejerce los cuatro roles: estratega, gestor y ejecutor de
prueba del Anexo E.1 de 29119-1, y además la autoridad de aprobación.
**No existe organización de prueba independiente del desarrollo ni
revisión externa**, y las dos cosas se declaran (D-5 y D-9).

## 2.4 Formación

El autor es estudiante de la Especialización en Ingeniería de Software de
la Universidad Distrital Francisco José de Caldas. No se exige
certificación adicional.

## 2.5 Ética

Rige el principio de **no atribuir al sistema garantías que no tiene**. En
concreto: no presentarlo como consejo médico, no presentarlo como cifrado
de conocimiento cero, y no reportar como medido lo que se observó una vez
(CLAUDE.md §12).

## 2.6 Normas aplicables

ISO/IEC/IEEE 29119 partes 2, 3 y 4 en conformidad adaptada; ISO/IEC 25010
para las características de calidad; ISO/IEC 20246 para revisiones.

## 2.7 Otras políticas que condicionan la prueba

Las **nueve decisiones no negociables** de `CLAUDE.md` §4 y las reglas de
seguridad del §7. Ninguna prueba puede proponer levantarlas: si una prueba
las contradice, se corrige la prueba.

## 2.8 Medición del valor de la prueba

Se mide por **defectos encontrados antes de que los encontrara una
usuaria**, no por número de casos. El proyecto tiene ya el contraejemplo:
los ocho mensajes sin respuesta del 15/09/2026 los encontró la producción,
no una prueba.

## 2.9 Archivado y reutilización de activos de prueba

Todo activo de prueba vive en el repositorio, que es **público**. De ahí se
siguen dos reglas:

- Las conversaciones reales, los mensajes que nombran un barrio y
  cualquier salida de `revisar_prueba_real` **no se versionan**.
- El historial de git es el archivo: borrar un script es barato porque el
  historial lo conserva, y de ahí salen los anexos del documento de grado.

## 2.10 Mejora del proceso

Cada hallazgo que cambie cómo se prueba se registra como ADR en
[`docs/adr/`](../adr/). Los cuatro aprendizajes ya recogidos en
`CLAUDE.md` §12 —medir reproduciendo producción, desconfiar del buen
indicador, inventariar en vez de buscar sospechosos, y no dar por bueno un
resultado del agente a la primera— son el punto de partida, no un anexo.

---

# 3. Prácticas de prueba — nivel organizacional

## 3.1 Enfoque de gestión del riesgo

**El riesgo decide qué se prueba y en qué orden.** Se identifican riesgos
de producto y de proyecto, se les asigna probabilidad y consecuencia en
escala 1–5, y la exposición (P × C) ordena el trabajo. El registro vive en
el [plan de pruebas](plan-de-pruebas.md) §5 y se revisa cada vez que se
cierra un ADR.

## 3.2 Selección y priorización

Los casos de prueba heredan la prioridad del riesgo que mitigan. Un
procedimiento que agrupa casos de distinta prioridad toma la más alta. Con
todo, **ningún conjunto de funcionalidades queda sin prueba alguna**: los
ocho casos de uso tienen cobertura, aunque sea mínima.

## 3.3 Documentación e informes

Los ítems del §1.2, en Markdown dentro de `docs/pruebas/`. La norma lo
admite: 29119-3 §4.1.1 acepta documentación en formato electrónico y
permite combinar, añadir o retitular secciones.

## 3.4 Automatización y herramientas

| Herramienta | Uso |
|---|---|
| `pytest` | Pruebas de componente y de integración. Versionadas en el repositorio |
| `TestClient` de FastAPI | Contrato del webhook, sin red |
| `scripts/spike_despachador.py` | Prueba de sistema de extremo a extremo |
| `scripts/calibrar_umbral_real.py` | Recuperación del CU2 contra consultas reales |
| `scripts/calibrar_enrutamiento.py` | Enrutamiento del agente, con repeticiones |
| `scripts/revisar_prueba_real.py` | Reconstrucción de una sesión hecha desde el celular |
| `/health` | Prueba de instalabilidad tras cada despliegue |
| Celular real y WhatsApp | Prueba de aceptación |

**No se usa herramienta comercial de gestión de pruebas** (D-8).

## 3.5 Gestión de configuración de los productos de prueba

Git. Los parámetros calibrables viven en variables de entorno de Railway
con valor por defecto en [`app/config.py`](../../app/config.py), y **el
defecto del repositorio debe coincidir con el valor de Railway**: el
08/09/2026 había tres valores del modelo generativo y ninguno acertaba, y
con eso se llegó a medir el enrutamiento contra dos modelos que no eran
producción.

## 3.6 Gestión de incidencias

Toda incidencia se registra en [`incidencias.md`](incidencias.md) con los
ocho campos obligatorios de 29119-3 §8.11. Severidad y prioridad usan
cuatro niveles. Una incidencia que cambie una decisión de arquitectura
genera además un ADR.

## 3.7 Niveles de prueba

Componente, integración, sistema, instalabilidad y aceptación. Se detallan
en §4.

## 3.8 Tipos de prueba

Funcional, **seguridad**, **usabilidad** y **de procedimiento** (29119-1
§4.29: si las instrucciones para interactuar con el sistema sirven al
propósito de uso — aquí, si la conversación se entiende). Excluidos:
rendimiento, carga, estrés, penetración y recuperación (D-4).

## 3.9 Reglas para desviarse de estas prácticas

Cualquier desviación se registra en la tabla del §1.3 con su
justificación y su fecha. Las nueve decisiones no negociables de
`CLAUDE.md` §4 **no** admiten desviación por esta vía.

---

# 4. Prácticas por nivel y por tipo

## 4.1 Criterios de entrada y de salida

| Nivel | Entrada | Salida |
|---|---|---|
| Estático | El artefacto existe en borrador | Hallazgos registrados; los que cambian una decisión, con su ADR |
| Componente | La función está escrita y su modelo de prueba declarado | 100 % de los ítems de cobertura del modelo, ejecutados y en verde |
| Integración | Componentes en verde; contrato del webhook especificado | Los seis casos del contrato en verde |
| Sistema | Integración en verde; base y corpus disponibles | `spike_despachador` sin ningún FALLA |
| Instalabilidad | Despliegue promovido en Railway | `/health` responde 200 con el commit y el modelo esperados |
| Aceptación | Todos los anteriores en verde y migraciones aplicadas | La conversación completa desde un celular real, sin incidencia de severidad 1 o 2 |

## 4.2 Criterios de terminación

1. **100 %** de los ítems de cobertura derivados de los modelos de prueba
   declarados para los CU1 a CU8.
2. **Cero** incidencias de severidad 1 o 2 abiertas. Las de severidad 3 y
   4 que queden, listadas y aceptadas por escrito.
3. **Regresión de la tubería de ingesta**: las nueve fuentes, simuladas
   **en el mismo orden** con `--simular --comprobar-duplicados`, vuelven a
   dar 81, 62, 220, 30, 46, 120, 68, 92 y 46 fragmentos. El orden importa
   porque el descarte de duplicados compara contra el corpus que hubiera
   en ese momento. Sirve para que un cambio en el troceo no pase
   inadvertido.
4. **Decisión del autor, 24/09/2026: los umbrales se mantienen** en sus
   valores vigentes y no se recalibran en esta fase.

   | Umbral | Variable | Valor | Qué gobierna |
   |---|---|---|---|
   | CU2, recuperación oficial | `RAG_UMBRAL_SIMILITUD` | **0.66** | Citar o no citar una fuente oficial |
   | CU7, recuperación comunitaria | `RAG_UMBRAL_COMUNITARIO` | **0.65** | Qué huertas entran en la búsqueda por cultivo |

   Son **dos perillas distintas** y conviene no confundirlas al escribir
   el documento de grado.

   **Sustento, medido el 24/09/2026:** de las 19 consultas agroecológicas
   reales recibidas entre el 09 y el 23/09, **15 superan el 0.66**. Las
   cuatro restantes son afirmaciones y no preguntas —«Hay problema con la
   sequia»—, y bajar el umbral no las arreglaría. Ver el
   [banco de preguntas](banco-de-preguntas.md) §3.

   **Consecuencia que hay que declarar:** el 0.66 queda **sostenido por
   evidencia de uso, no cerrado por calibración**. La revalidación que
   exigía leer el fragmento recuperado de cada una de las 81 consultas
   **no se hizo**. El documento de grado debe decir «se mantuvo el valor
   medido el 19/08/2026 y se comprobó contra 19 consultas reales», nunca
   «se calibró el umbral».
5. El banco de 20 preguntas ejecutado y calificado con su rúbrica.

   **Ejecutado el 24/09/2026, tres veces.** Tras corregir INC-020 con el
   ADR-0025: precisión **20/20**, coherencia **20/20** y advertencia médica
   **100 %** cumplen; pertinencia **13/20** contra un umbral de 16 **no**.

   El criterio queda **incumplido por la pertinencia, y por una causa que
   ningún cambio de código arregla**: cinco de las diez preguntas reales
   piden algo que el corpus no cubre. Es un hueco de corpus, no un defecto
   del sistema, y así hay que declararlo en el documento de grado.

Obsérvese que **no hay objetivo de cobertura de código**, y es deliberado:
la norma exige criterios de terminación, no un porcentaje de líneas.

## 4.3 Documentación e informes por nivel

La del §3.3. El nivel de aceptación añade el registro de la sesión con
celular, que **no se versiona** por contener conversación real.

## 4.4 Grado de independencia

**Nivel a) del Anexo E.3 de 29119-1: el autor prueba su propio producto.**
Es el nivel más bajo que la norma contempla. Se mitiga con tres medidas, y
ninguna lo compensa del todo:

1. Las pruebas de componente e integración son **deterministas y
   automatizadas**: una vez escritas, su resultado no depende de quien las
   corre.
2. La **aceptación la ejecutan las usuarias**, no el autor. La evaluación
   con 5 a 7 líderes de huerta introduce la única independencia real del
   proyecto.
3. Las desviaciones y los criterios de terminación quedan **escritos y
   fechados** antes de ejecutar, no después, para que el criterio no se
   acomode al resultado. Es lo único que sustituye a una revisión externa,
   y no la sustituye del todo.

## 4.5 Técnicas de diseño de prueba

Se usan las de ISO/IEC/IEEE 29119-4, asignadas por modelo de prueba:

| Modelo | Técnica |
|---|---|
| Rango de 8 a 15 dígitos de `normalizar_telefono` | Valores límite (7, 8, 15, 16) |
| Forma de un identificador en `es_telefono` | Particiones de equivalencia |
| Onboarding de tres preguntas | Transición de estados, **incluidas las transiciones nulas** |
| Compuerta de consentimiento | Transición de estados |
| Reglas de `_seleccionar` del agente | Tabla de decisión |
| Escalera de identidad del despachador | Tabla de decisión |
| Firma HMAC del webhook | Especificación más conjetura de errores |
| Defectos ya vividos (`wamid`, BSUID, modelo) | **Conjetura de errores** (29119-1 §4.14) |
| Corpus extraído de PDF | Inventario exhaustivo, no búsqueda de sospechosos |
| Conversación completa | Escenarios y casos de uso |
| Calidad de respuesta del CU2 | Basada en experiencia, con rúbrica |

## 4.6 Datos de prueba

- Los datos temporales llevan `57000000` dentro, con forma de BSUID
  (`CO.570000000601`), y **se borran en un `finally`**.
- **Las nueve filas reales de `usuario` no se tocan**: son el material de
  la Fase 7.
- El dato personal está protegido en origen —huella HMAC del BSUID y
  nombre cifrado con AES-GCM—, de modo que no hace falta ofuscar nada
  adicional para probar.
- Reiniciar el onboarding de una usuaria se hace **borrando su fila de
  `huerta`**, nunca la de `usuario`, que se llevaría por cascada la
  conversación.

## 4.7 Entorno de prueba

Tres entornos, y **uno de ellos es producción**:

| Entorno | Qué es | Diferencia con producción |
|---|---|---|
| Local | `uvicorn` en el equipo del autor | `/health` informa `local`; sin `RAILWAY_GIT_COMMIT_SHA` |
| Railway | El despliegue | Ninguna: **es** producción |
| Supabase | Base y corpus | **Ninguna: es la misma instancia** (D-3) |

29119-2 §8.3.4.1 c) obliga a declarar las diferencias conocidas entre el
entorno de prueba y el operativo. Aquí lo notable es que **no hay
diferencia**, y eso es el riesgo, no la garantía.

## 4.8 Métricas a recoger

| Métrica | Fuente |
|---|---|
| Casos ejecutados sobre planificados | `pytest`, `spike_despachador` |
| Incidencias abiertas y cerradas por severidad | Registro de incidencias |
| Riesgo residual: mitigados sobre identificados | Registro de riesgos |
| Consultas del CU2 resueltas **sin respaldo oficial** | Bitácora |
| Turnos con `literal=False` (recorte del agente) | Bitácora |
| Veces que `limpiar_etiquetas` actúa | Bitácora |
| Aciertos de enrutamiento sobre 76 repeticiones | `calibrar_enrutamiento` |
| Fragmentos por fuente frente a la línea base | `ingesta_fuente --simular` |

## 4.9 Prueba de usabilidad

La evaluación con usuarias **es un tipo de prueba** bajo esta política, no
una actividad aparte: mide la característica *Usability* de ISO/IEC 25010
mediante la Escala de Usabilidad del Sistema. Su diseño metodológico
—número de rondas, instrumento, muestra— lo fija el anteproyecto y su
discusión sigue abierta (ver `docs/ESTADO.md`, «La evaluación con
usuarias»). Lo que esta política determina es que sus hallazgos entran al
mismo registro de incidencias que los demás.

## 4.10 Reejecución

Todo caso que detecte un defecto se vuelve a ejecutar tras la corrección.
Si el defecto estaba en el caso y no en el producto, se corrige el caso y
se anota en el registro de incidencias.

## 4.11 Regresión

Se reejecuta la suite completa de componente e integración —es de
segundos— más `spike_despachador` antes de cada despliegue.

**Y hay una regresión propia de este proyecto que no es de código:** el
corpus vive en Supabase, así que cualquier cambio en la tubería de ingesta
debe seguir produciendo los mismos fragmentos en las fuentes ya ingeridas.
Ese corpus es el que sostiene la calibración del umbral.
