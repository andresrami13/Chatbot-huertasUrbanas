# Plan de pruebas del proyecto

| | |
|---|---|
| **Identificador** | `PLP-CHU-001`, versión 1.0 |
| **Emite** | Andrés Ramírez — autor del trabajo de grado |
| **Aprueba** | A. Ramírez — autor. **Única autoridad de aprobación** (desviación D-9) |
| **Estado** | Borrador para revisión |
| **Fecha** | 23/09/2026 |

## Historial de cambios

| Fecha | Versión | Cambio | Autor |
|---|---|---|---|
| 23/09/2026 | 1.0 | Versión inicial | A. Ramírez |

## Introducción

Plan de pruebas del proyecto conforme a ISO/IEC/IEEE 29119-3:2021 §7.2, en
la **conformidad adaptada** declarada en la
[política y prácticas de prueba](politica-y-practicas-de-prueba.md) §1.

Es un **plan de proyecto**, no de nivel: cubre todos los niveles y tipos de
prueba del prototipo. No se producen planes separados por nivel, porque la
escala no lo justifica.

**Estado de lo planificado, al cierre del 23/09/2026.** Ejecutados: la
prueba estática, la de componente (231 casos), la de integración, la de
sistema (`spike_despachador`), la de instalabilidad (`humo_despliegue`) y
**la de aceptación, con usuarias reales desde celulares reales en los ocho
casos de uso**. El **banco de 20 preguntas se ejecutó y calificó el
24/09/2026** y **se repitió el 25/09**. INC-020 quedó corregida con el
ADR-0025; INC-021 se dio por corregida con una sola corrida y **se reabrió**
al repetir, y la repetición destapó INC-024 —advertencia médica ausente— e
INC-025 —una pregunta que el agente no enruta—. Solo la coherencia pasa de
forma estable.

Este plan describe lo que se va a hacer; **el informe de cierre dirá lo
que se hizo**, y las diferencias entre uno y otro se registran ahí.

## Alcance de este documento

Cubre la Fase 7 (pruebas y validaciones) y la parte de la Fase 8
(socialización con la comunidad) que constituye prueba de aceptación y de
usabilidad. No cubre la metodología de la evaluación SUS, que fija el
anteproyecto.

## Referencias

Las de la [política y prácticas de prueba](politica-y-practicas-de-prueba.md),
más:

- [`docs/ESTADO.md`](../ESTADO.md), sección «Por dónde seguir»
- [`app/config.py`](../../app/config.py), parámetros calibrables
- [`scripts/catalogo_fuentes.py`](../../scripts/catalogo_fuentes.py), las nueve fuentes y sus parámetros medidos

## Glosario

El de la política y prácticas de prueba.

---

# 1. Contexto de la prueba

## 1.1 Proyecto, niveles y tipos

Prototipo funcional de chatbot de WhatsApp con inteligencia artificial para
el apoyo a huertas urbanas en la localidad de Bosa, Bogotá. Trabajo de
grado de la Especialización en Ingeniería de Software de la Universidad
Distrital Francisco José de Caldas.

- **Niveles**: estático, componente, integración, sistema, instalabilidad
  y aceptación.
- **Tipos**: funcional, seguridad, usabilidad y de procedimiento.

## 1.2 Elementos de prueba

| Elemento | Versión |
|---|---|
| Backend FastAPI desplegado en Railway | El commit que informe `/health` en el momento de la ejecución |
| Módulos de [`app/`](../../app/) | La del repositorio |
| Esquema de [`db/`](../../db/) | Archivos `001` a `010`, **todas aplicadas**. Comprobado el 23/09/2026 contra `information_schema`: existe `usuario.identidad_hash` y existe la tabla `listado_comunitario_pendiente` (incidencia INC-004) |
| Prompts versionados de `app/agent/prompts/` | Los seis vigentes: `agente_v2`, `extraccion_v3`, `barrio_v1`, `redaccion_rag_v1`, `redaccion_comunidad_v2`, `respuesta_general_v1` |
| Corpus oficial en Supabase | 765 fragmentos en nueve fuentes |
| Catálogo de barrios | 313 filas |
| Scripts de [`scripts/`](../../scripts/) | La del repositorio |
| Documentos de fase y ADR | Los de `docs/` |

La versión de cada elemento se registra al ejecutar, tomándola de `/health`
y de `git`.

## 1.3 Alcance de la prueba

**Se prueba**

- Los ocho casos de uso: CU1 consentimiento, CU2 orientación, CU3
  registro, CU4 listado de la comunidad, CU5 ayuda, CU6 onboarding, CU7
  búsqueda por cultivo, CU8 consultar la propia huerta.
- Las seis capas del modelo de seguridad de la Fase 3.
- La entrada por texto y por nota de voz.
- La calidad de la respuesta agroecológica del CU2.
- La usabilidad con usuarias de la comunidad.
- La regresión de la tubería de ingesta y de los parámetros calibrados.

**No se prueba, y por qué**

| Excluido | Razón |
|---|---|
| Rendimiento, carga, estrés, resistencia | Exposición baja: prototipo con 5 a 7 usuarias, sin transacción económica. Desviación D-4 |
| Penetración y recuperación ante desastre | Igual que arriba. El límite de seguridad ya está declarado: esto no es cifrado de conocimiento cero y el operador tiene las claves |
| La API de Meta y la API de Gemini en sí mismas | Son servicios de terceros. Se prueba la **integración**, no el proveedor |
| La respuesta por voz y la búsqueda en internet | Fuera del alcance del anteproyecto y de la Fase 2 |
| El modelo de embeddings | Fijo en código a propósito (ADR-0007). Cambiarlo invalidaría todos los vectores guardados |
| Compatibilidad entre dispositivos y versiones de WhatsApp | El canal lo normaliza Meta. Se observará durante la aceptación, sin diseño de prueba propio |

## 1.4 Base de prueba

En este orden de precedencia:

1. Los **ADR** de [`docs/adr/`](../adr/) — veinticuatro decisiones. Cuando
   un ADR corrige un documento de fase, **prevalece el ADR**.
2. [`CLAUDE.md`](../../CLAUDE.md), decisiones no negociables (§4),
   seguridad (§7) y parámetros (§8).
3. Los `.docx` de fase: anteproyecto, Fase 2 funcional, Fase 3 técnico,
   Fase 4 IA.
4. [`docs/correcciones-a-los-documentos.md`](../correcciones-a-los-documentos.md),
   que consolida las desviaciones ya declaradas.

Que la base de prueba tenga **conflictos internos declarados** es un hecho
del proyecto, no un descuido: los `.docx` de fase quedaron superados en
varios puntos y el orden de precedencia es la forma de resolverlo.

---

# 2. Supuestos y restricciones

| # | Supuesto o restricción |
|---|---|
| S-1 | El autor es la única persona que diseña, implementa y ejecuta las pruebas, salvo la aceptación |
| S-2 | **No existe entorno de prueba separado**: Supabase es la misma instancia que sirve a producción (desviación D-3) |
| S-3 | Ejecutar pruebas contra el modelo de Gemini tiene costo monetario; las repeticiones se acotan |
| S-4 | La restricción de portfolio de Meta sigue en revisión: el acceso al canal puede considerarse provisional |
| S-5 | El presupuesto de infraestructura es Railway Hobby, USD 5 al mes |
| S-6 | El calendario es el del anteproyecto: cuatro meses y medio del segundo semestre de 2026 |
| S-7 | La evaluación con usuarias exige reclutar entre 5 y 7 líderes de huerta, y su diseño está en discusión |
| S-8 | Las **11 filas reales** de `usuario` y sus **258 mensajes** (al 23/09/2026) son material irreemplazable de la Fase 7 |

---

# 3. Interesados

| Interesado | Relevancia |
|---|---|
| Líderes y propietarias de huerta de Bosa | Usuarias finales. Ejecutan la prueba de aceptación y responden el SUS |
| Jurados de la Universidad Distrital | Destinatarios del informe de cierre |
| Autor | Estratega, gestor y ejecutor de pruebas, y **autoridad de aprobación** |
| Alcaldía Local de Bosa (Programa 25 del PDL) | Interesado institucional del resultado, sin participación en la prueba |

---

# 4. Comunicación de la prueba

- El estado se registra en [`docs/ESTADO.md`](../ESTADO.md) (desviación D-2).
- Las incidencias, en [`incidencias.md`](incidencias.md).
- Las decisiones que cambien la arquitectura o una medición, en
  [`docs/adr/`](../adr/).
- Con las usuarias, únicamente por WhatsApp y —en la evaluación— por nota
  de voz o llamada. **Ninguna evaluación la pide el propio bot**: sesgaría
  la respuesta.

---

# 5. Registro de riesgos

Escalas de 1 a 5. **E = P × C.** La exposición ordena el trabajo de prueba:
las filas de mayor exposición se prueban primero y con más profundidad.

## 5.1 Riesgos de producto

| # | Riesgo | P | C | E | Mitigación por prueba |
|---|---|---|---|---|---|
| **P-02** | La usuaria escribe y **no recibe nada** por identidad o destino mal resueltos | 1 | 5 | **5** | **Reevaluado el 23/09/2026.** Ocurrió el 15/09 —8 mensajes de unos 70—, y desde entonces: corrección desplegada (`7b136e7`), migración `010` corrida, 11 casos de componente sobre `_campo_destino` y `_resolver_identidad`, y **aceptación ejecutada en celulares reales con usuarias reales**. La base registra 135 respuestas del asistente y actividad hasta hoy |
| **P-03** | El CU2 **cita una fuente que no sustenta** lo que dice, o calla la cita cuando debía darla | 2 | 4 | **8** | **Materializado, medido y corregido el 24/09/2026.** Ocurría en 6 de 20 (INC-020); con el ADR-0025 la cita la pone el backend y ocurre en 0 de 20. Baja a probabilidad 2 y no a 1: queda el caso contrario —que el modelo declare no haber podido cuando el contexto sí le servía—, que **no lo detecta nada** |
| **P-12** | El **modelo generativo desalineado** entre Railway, `config.py` y los documentos invalida una medición | 3 | 4 | **12** | Instalabilidad: `/health` informa el modelo. Ya ocurrió el 08/09/2026 con tres valores distintos |
| **P-14** | **Texto defectuoso extraído del PDF** llega a la usuaria | 2 | 3 | **6** | **Reevaluado el 24/09/2026.** El inventario exhaustivo se hizo y la limpieza también: 36 fragmentos corregidos, cero apariciones después, y la regla vive en `ingesta_fuente.limpiar_fragmento`, así que una reingesta no la deshace. Queda INC-010, de otra clase: rótulos incrustados y cinco páginas rotadas que `pypdf` no extrae |
| **P-01** | Una respuesta del CU2 que habla de **salud sale sin advertencia médica** | 3 | 5 | **15** | **Materializado el 25/09/2026 (INC-024)**: el romero, 1 de 7 corridas. Sube de probabilidad 2 a 3 |
| **P-05** | El agente **no llama a ninguna herramienta** y responde de memoria, saltándose el CU2: sin RAG, sin cita y sin advertencia | 2 | 5 | **10** | `calibrar_enrutamiento` con repeticiones. Con `gemini-2.5-flash` fallaba 26 de 76; con el modelo actual, 0 de 76 |
| **P-07** | Un **dato personal** aparece en la bitácora o en la base en claro | 2 | 5 | **10** | Componente sobre `referencia_wamid`, `huella_wamid` y el cifrado del nombre; revisión estática de los registros. Ya ocurrió el 30/07/2026 |
| **P-13** | `gemini-2.5-flash` **se retira el 16/10/2026** | 5 | 2 | **10** | Ya no está en uso; `/health` lo confirma en cada despliegue |
| **P-16** | El **onboarding no reconoce el barrio** y la usuaria se atasca | 3 | 3 | **9** | Componente por transición de estados sobre las tres preguntas y la desambiguación; aceptación |
| **P-17** | La usuaria cree que habla con una **persona o con una autoridad técnica** | 3 | 3 | **9** | Aceptación y SUS. Mitigado por diseño en el ADR-0024 |
| **P-09** | Un prompt **no carga por una llave literal** y el turno se cae con `KeyError` | 2 | 4 | **8** | Componente parametrizado sobre los seis prompts vigentes |
| **P-11** | Un mensaje **se pierde en silencio** cuando la base no responde, después de que el webhook ya devolvió 200 | 2 | 4 | **8** | Sistema. Mitigado por diseño en el ADR-0019 |
| **P-15** | Un mensaje que **mezcla consulta y dato** ofrece guardar el cultivo por el que se preguntó | 4 | 2 | **8** | Sistema y aceptación. La confirmación previa a guardar lo contiene |
| **P-10** | **Respuesta o registro duplicados** por un reintento de Meta | 2 | 3 | **6** | Sistema: idempotencia por huella del `wamid` |
| **P-06** | Se **persiste un dato antes del consentimiento** | 1 | 5 | **5** | Componente y sistema: el spike comprueba que no queda **ni una fila** de quien no autorizó |
| **P-08** | El CU4 o el CU7 **exponen un dato personal** de otra usuaria | 1 | 5 | **5** | Componente sobre las columnas compartibles; sistema |
| **P-18** | La **advertencia médica se dispara donde no toca** y termina cansando | 4 | 1 | **4** | **Medido el 24/09/2026**: 1 de 20 respuestas sin tema de salud la lleva, y no faltó en ninguna de las 2 que sí. Es ancha, como se diseñó |

## 5.2 Riesgos de proyecto

| # | Riesgo | P | C | E | Mitigación |
|---|---|---|---|---|---|
| **J-01** | **No hay independencia de prueba ni revisión externa**: el autor prueba, aprueba y cierra su propio producto | 5 | 3 | **15** | Automatizar lo determinista, para que el resultado no dependa de quien lo corre; **la aceptación la ejecutan las usuarias**, que es la única independencia real del proyecto (política §4.4). No queda mitigado del todo, y se declara |
| **J-02** | **Probar daña los datos reales** de la Fase 7, porque no hay entorno separado | 3 | 5 | **15** | Marca `57000000` en toda identidad temporal y borrado en `finally`; nunca borrar filas de `usuario`; exportar antes de cualquier operación destructiva |
| **J-07** | Los **registros de Railway anteriores al 30/07/2026 contienen el teléfono del autor** en claro y siguen sin purgar | 5 | 3 | **15** | Acción pendiente del autor. Es lo más urgente de la lista |
| **J-05** | El **calendario** no alcanza: la Fase 8 depende de reclutar 5 a 7 usuarias | 3 | 4 | **12** | Página de registro de una sola pantalla con alternativa por nota de voz; el bot ya está en número de producción |
| **J-03** | Los **datos reales no se pueden regenerar**. Ya se perdió la conversación de la prueba del 15/08 al vaciar las tablas el 18/08 | 2 | 5 | **10** | Exportar siempre antes; el export de las nueve conversaciones del 17/09 vive fuera del repositorio, que es público |
| **J-04** | La **revisión de portfolio de Meta** sigue abierta y el acceso puede revocarse | 2 | 5 | **10** | Ninguna mitigación técnica. Se declara como límite del prototipo |
| **J-06** | **Costo de la API de Gemini** en ejecuciones repetidas de calibración | 3 | 2 | **6** | Acotar las repeticiones; ninguna llamada al modelo en integración continua |
| **J-08** | El **resolutor DNS** del equipo rechaza el host de Supabase de forma intermitente | 4 | 1 | **4** | Acción pendiente del autor. No afecta a producción |

## 5.3 Consecuencia para el orden de trabajo

De las exposiciones se sigue el orden: **identidad y envío** y
**calidad de la respuesta del CU2** antes que ninguna otra cosa.

**Actualización del 23/09/2026.** La identidad por BSUID resultó **ya
desplegada y migrada** (INC-004): se creía pendiente por leer
`docs/ESTADO.md` en vez de consultar el sistema. Queda arriba, sola, la
**calidad de la respuesta agroecológica** (A-10).

---

# 6. Estrategia de prueba

## 6.1 Niveles

| Nivel | Ítem de prueba | Ejecuta | Automatizado |
|---|---|---|---|
| Estático | Documentos, ADR, corpus extraído, código | Autor | No |
| Componente | Funciones de `app/` | Autor | Sí (`pytest`) |
| Integración | Contrato del webhook con Meta | Autor | Sí (`pytest` + `TestClient`) |
| Sistema | La rama completa desde `procesar_evento` | Autor | Sí (`spike_despachador`) |
| Instalabilidad | El despliegue en Railway | Autor | Parcial (`/health`) |
| Aceptación | La conversación real por WhatsApp | **Usuarias** | No |

## 6.2 Tipos

Funcional, seguridad, usabilidad y de procedimiento. Los tipos no son un
nivel aparte: se ejecutan **dentro** de los niveles. La prueba de
seguridad, por ejemplo, vive sobre todo en el nivel de componente —firma
HMAC, dominios del HMAC de identidad, cifrado del nombre— y en parte en el
de sistema —la compuerta de consentimiento—.

## 6.3 Entregables de prueba

| Entregable (29119-3) | Documento | Estado |
|---|---|---|
| Política de prueba y prácticas organizacionales | `PPP-CHU-001` | **Hecho** |
| Plan de pruebas | `PLP-CHU-001` | **Hecho** |
| Especificación de modelos de prueba | `ESP-CHU-001` §MP | **Hecho**: 24 modelos |
| Especificación de casos de prueba | `ESP-CHU-001`, matriz | **Hecho**: 231 casos, en `tests/` |
| Especificación de procedimientos de prueba | `ESP-CHU-001` §PR | **Hecho**: PR-01 a PR-05 |
| Registro de incidencias | `INC-CHU-001` | **Hecho**: 21 incidencias |
| Banco de 20 preguntas y su rúbrica | `BPA-CHU-001` | **Hecho**, ejecutado y calificado |
| Informe de estado de prueba | `docs/ESTADO.md` | **Hecho** por la vía de la desviación D-2 |
| Requisitos de datos y de entorno de prueba | — | **Pendiente.** Es lo que falta por escribir |
| Informes de preparación de datos y de entorno | — | **Pendiente**, y depende del anterior |
| Resultados reales, resultado y bitácora de ejecución | — | **Parcial.** Existen los de `spike_despachador`, el banco y el humo; falta el de la **aceptación** (actividad A-14) |
| Informe de cierre | — | **Pendiente** (actividad A-13). Es el último |

**Tres de doce siguen abiertos, y dos son el mismo trabajo.** Los
requisitos de datos y de entorno son un documento corto: la desviación D-3
ya dice que no hay entorno separado y que Supabase **es** producción, y los
datos de prueba son las identidades con `57000000` que los scripts crean y
borran. Escribirlo es recoger lo que ya está decidido y disperso.

## 6.4 Técnicas de diseño

Las de la [política](politica-y-practicas-de-prueba.md) §4.5, asignadas
por modelo de prueba. Regla de profundidad, derivada del riesgo:

- Exposición **≥ 12**: cobertura completa del modelo, incluidas las
  transiciones nulas y los valores límite por ambos lados.
- Exposición **entre 6 y 11**: un representante por partición válida y uno
  por partición inválida.
- Exposición **≤ 5**: un caso positivo.

## 6.5 Criterios de entrada y de salida

Los de la política §4.1.

## 6.6 Criterios de terminación

Los de la política §4.2. El **quinto** es el banco de 20 preguntas, cuya
rúbrica fija el autor (§4 del [banco](banco-de-preguntas.md)):

| Criterio | Umbral | Antes del ADR-0025 | Después | |
|---|---|---|---|---|
| Precisión: ninguna afirmación agronómica falsa | **20 de 20** | 19 de 20 | 20 en una corrida; D-06 falla 5 de 6 al repetir (INC-021) | **No pasa** |
| Pertinencia: la respuesta atiende lo que se preguntó | **≥ 16 de 20** | 14 de 20 | 13 de 20 | **No pasa** |
| Coherencia: sin contradicción interna ni cita rota | **≥ 18 de 20** | 14 de 20 | **20 de 20** | **Pasa** |
| Advertencia médica presente cuando corresponde | **100 %** | 100 % | un falso negativo al repetir (INC-024) | **No pasa** |

**Falta la pertinencia, y no por un defecto del sistema.** Las cinco
preguntas reales que fallan piden algo que el corpus no cubre —cómo hacer
un atrapador de rocío, qué suelo quiere la granadilla, reusar el agua de
lavar ropa, cuándo aporcar, cómo quemar la cascarilla—. Ahora el bot lo
dice sin citar a nadie, que es lo correcto, pero sigue sin responderlas.
**Se arregla con corpus, no con código.**

## 6.7 Grado de independencia

Nivel a) del Anexo E.3 de 29119-1, declarado en la desviación D-5.

## 6.8 Métricas

Las de la política §4.8.

## 6.9 Requisitos de datos de prueba

Se detallan en un documento aparte. En resumen:

| Dato | Origen | Restablecer | Al terminar |
|---|---|---|---|
| Identidades temporales `CO.5700000006xx` | Los scripts las crean | No aplica | **Borrar en `finally`** |
| 765 fragmentos oficiales, nueve fuentes | Supabase, ya ingeridos | Reingesta con `--reingerir` | Conservar |
| 313 barrios | `db/003_catalogo_barrios_bosa.sql` | Reejecutar el script | Conservar |
| **11 usuarias reales, 9 huertas, 61 cultivos, 258 mensajes** (123 de ellas, 135 del asistente), del 09 al 23/09/2026 | Producción | **Nunca** | **No tocar** |
| 81 consultas reales para el umbral | Tabla `mensaje` y el export del 17/09 | No aplica | No versionar |
| 19 frases de enrutamiento × 4 repeticiones | `calibrar_enrutamiento` | No aplica | Conservar la salida |

## 6.10 Requisitos de entorno de prueba

Se detallan en un documento aparte. El punto que la norma obliga a
declarar (29119-2 §8.3.4.1 c): **el entorno de prueba y el operativo son el
mismo en lo que respecta a la base de datos y al corpus**. Escribir en
Supabase cambia lo que responde el bot en el acto, con o sin despliegue.
De ahí salen las mitigaciones del riesgo J-02.

## 6.11 Reejecución

La de la política §4.10.

## 6.12 Regresión

La de la política §4.11, que incluye la regresión **del corpus**, no solo
la del código.

## 6.13 Criterios de suspensión y de reanudación

| Se suspende cuando | Se reanuda cuando |
|---|---|
| El código desplegado y el esquema de la base no coinciden (por ejemplo, entre desplegar y correr la migración `010`) | Ambos coinciden, comprobado con `/health` y contra `information_schema` |
| Meta suspende o restringe el acceso al canal | El acceso se restablece |
| Una prueba pone en peligro dato real de la Fase 7 | Existe copia exportada fuera del repositorio |
| La familia de modelos devuelve `503 UNAVAILABLE` de forma sostenida | El servicio se estabiliza |

La autoridad para suspender y reanudar es el autor. Al reanudar tras el
primer caso, se **repite la prueba de instalabilidad completa**.

## 6.14 Desviaciones respecto de las prácticas organizacionales

Ninguna adicional a las ocho de la política §1.3.

---

# 7. Actividades y estimación

| # | Actividad | Estimación | Depende de |
|---|---|---|---|
| A-1 | Registro de riesgos y este plan | 1 jornada | — |
| A-2 | Especificar modelos de prueba (estados del onboarding y del consentimiento, tablas de decisión, particiones) | 1 jornada | A-1 |
| A-3 | Derivar ítems de cobertura y casos; implementarlos en `pytest` | 1,5 jornadas | A-2 |
| A-4 | Contrato del webhook con `TestClient` | 0,5 jornada | A-3 |
| A-5 | Prueba de instalabilidad automatizada contra `/health` | 0,5 jornada | — |
| A-6 | Integración continua que ejecute A-3 y A-4 | 0,5 jornada | A-4 |
| A-7 | Retro-documentar incidencias y pruebas estáticas ya realizadas | 1 jornada | A-1 |
| A-10 | ~~Construir y ejecutar el banco de 20 preguntas con su rúbrica~~ **Hecha el 24/09/2026**, con `scripts/ejecutar_banco.py`. No superado | — | — |
| A-16 | ~~Corregir INC-020~~ **Hecha el 24/09/2026**: ADR-0025, prompt `redaccion_rag_v2.md`, `_con_cita` y 14 casos nuevos. De 6 de 20 a 0 de 20 | — | — |
| A-17 | ~~Medir `RAG_TOP_K`~~ **Hecha el 25/09/2026**, con 4 y 5 y tres repeticiones. Sin beneficio ni daño medido; el autor fijó 5 (ADR-0026) | — | — |
| A-18 | ~~Limpiar los 36 fragmentos de INC-019 y revectorizar solo esos, remidiendo el banco antes y después~~ **Hecha el 24/09/2026** con `scripts/limpiar_corpus.py`. Ninguna similitud cruzó el umbral | — | — |
| A-11 | ~~Probar en celular el envío por `recipient`~~ **Hecha.** Despliegue, migración `010` y aceptación en celulares reales | — | — |
| A-12 | Remedir el umbral comunitario del CU7, ahora con 9 huertas y 6 fragmentos comunitarios | 0,5 jornada | — |
| A-13 | Informe de cierre | 1 jornada | Todas |
| **A-14** | **Reconstruir el registro de la aceptación**: resultados reales, resultado y bitácora de ejecución, desde `mensaje` con `revisar_prueba_real`. La ejecución existe; el registro normalizado que exige la conformidad declarada, no | 1 jornada | — |
| A-15 | Regresión de la tubería de ingesta en las fuentes que faltan. **Aplazada por decisión del autor el 25/09/2026**: no es prioritaria. Van 6 de 9 comprobadas | — | — |

**Total estimado: 12,5 jornadas.** No incluye la Fase 8.

La estimación es del autor por juicio experto, sin datos históricos de
proyectos comparables; conviene leerla como orden de magnitud.

---

# 8. Personal

## 8.1 Roles y responsabilidades

| Rol | Quién | Responsabilidad |
|---|---|---|
| Estratega de prueba | Autor | Política y prácticas |
| Gestor de prueba | Autor | Este plan, seguimiento, control y cierre |
| Ejecutor de prueba | Autor | Diseño, implementación y ejecución de los niveles estático a instalabilidad |
| Ejecutor de aceptación | **Usuarias de la comunidad** | Uso real por WhatsApp y respuesta al SUS |
| Autoridad de aprobación | Autor | Aprueba el plan, las desviaciones y los criterios de terminación (D-9) |

## 8.2 Necesidades de contratación

Ninguna. El trabajo de grado es individual y el presupuesto de
infraestructura es de USD 5 al mes.

## 8.3 Necesidades de formación

Ninguna adicional. Dos carencias conscientes: el autor no tiene
certificación en pruebas, y no hay experiencia previa en `pytest` dentro
del proyecto. Se cubre con la documentación oficial y no se estima riesgo
apreciable.

---

# 9. Cronograma

Anclado a las fases del anteproyecto, no a fechas de calendario, porque la
Fase 8 depende del reclutamiento.

| Hito | Actividades | Momento |
|---|---|---|
| H-1 Proceso de prueba declarado | A-1 | **Hecho** el 23/09/2026 |
| H-2 Red de seguridad automatizada | A-2 a A-6 | **Hecho** el 23/09/2026: 231 casos tras el ADR-0025, humo de despliegue e integración continua |
| H-3 Historia de prueba recuperada | A-7 | **Hecho** el 23/09/2026: 18 incidencias y nueve pruebas estáticas registradas |
| H-4 Identidad por BSUID comprobada en vivo | A-11 | **Hecho** |
| H-5 Regresión de la ingesta | A-15 | **Aplazado** por decisión del autor. 6 de 9 fuentes comprobadas |
| H-6 Umbrales decididos | — | **Cerrado el 24/09/2026 por decisión del autor**: se mantienen 0.66 y 0.65, sostenidos por la medición de 19 consultas reales y **declarados como no recalibrados** |
| H-7 Umbral comunitario remedido | A-12 | Pendiente |
| H-8 Calidad de respuesta evaluada | A-10 | **Hecho** el 24/09/2026. Tres de los cuatro criterios pasan; falta la pertinencia, por hueco de corpus |
| H-9 Defectos del banco corregidos | A-16, A-17, A-18 | Las tres hechas. **Pero la repetición abrió INC-021, INC-024 e INC-025**, que siguen sin corregir |
| H-10 Corrección del CU2 desplegada | — | **Pendiente.** El ADR-0025 está escrito y probado, y **sin desplegar**: producción sigue corriendo `7b136e7`, con el prompt `v1` y la cita del modelo |
| H-11 Registro de la aceptación | A-14 | Pendiente. La ejecución existe; el registro, no |
| H-12 Fase 7 cerrada | A-13 | Al cumplirse los cinco criterios de terminación del §6.6 |
| H-13 Usabilidad | Fase 8 | Según reclutamiento |

**La aceptación dejó de ser un hito futuro.** Los ocho casos de uso se han
ejercitado con usuarias reales desde celulares reales entre el 09 y el
23/09/2026, y la base lo respalda: 11 usuarias, 9 huertas, 61 cultivos y
258 mensajes. Lo que queda de ese frente no es ejecutar, es **registrar**
(A-14): la conformidad declarada exige resultados reales, resultado y
bitácora de ejecución, y eso se reconstruye desde `mensaje`.
