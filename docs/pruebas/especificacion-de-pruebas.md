# Especificación de pruebas

| | |
|---|---|
| **Identificador** | `ESP-CHU-001`, versión 1.2 |
| **Emite** | Andrés Ramírez — autor del trabajo de grado |
| **Aprueba** | A. Ramírez — autor. **Única autoridad de aprobación** (desviación D-9) |
| **Estado** | Borrador para revisión |
| **Fecha** | 23/09/2026 |

## Historial de cambios

| Fecha | Versión | Cambio | Autor |
|---|---|---|---|
| 23/09/2026 | 1.0 | Versión inicial: 23 modelos de prueba y 217 casos ejecutables | A. Ramírez |
| 24/09/2026 | 1.1 | MP-24, de la corrección de INC-020 (ADR-0025): 14 casos más. PR-05, el banco de preguntas | A. Ramírez |
| 25/09/2026 | 1.2 | Cobertura de aceptación corregida con el registro de A-14: CU4, CU7 y CU8 sin evidencia | A. Ramírez |

## Introducción

Reúne los tres ítems de información del diseño dinámico de
ISO/IEC/IEEE 29119-3:2021: la **especificación de modelos de prueba**
(§8.2), la de **casos de prueba** (§8.3) y la de **procedimientos** (§8.4).

Van en un solo documento, y **no es una desviación**: el §3.23 define la
especificación de prueba como la documentación completa del diseño, los
casos y los procedimientos de un ítem, y su nota 1 admite que se detalle
«en un documento, en un conjunto de documentos, o de otras formas».

**Los casos viven en el código, no aquí.** Este documento especifica los
modelos y la trazabilidad; los casos son las funciones de `tests/`, y la
norma lo permite (§4.1.1: la documentación puede ser electrónica, en
herramientas). Duplicarlos en prosa garantizaría que las dos copias se
separen.

## Alcance

Cubre los niveles de **componente** e **integración**. El nivel de
sistema lo especifica `scripts/spike_despachador.py`, cuyo encabezado
enumera los nueve caminos que comprueba. Los niveles de instalabilidad y
aceptación se especifican en la parte 3 de este documento.

## Referencias

- [Política y prácticas de prueba](politica-y-practicas-de-prueba.md)
- [Plan de pruebas](plan-de-pruebas.md)
- [Registro de incidencias](incidencias.md)
- `tests/`, `scripts/spike_despachador.py`, `scripts/ejecutar_banco.py`
- `scripts/arnes.py` — el arnés que comparten los dos scripts anteriores

## Glosario

El de la política y prácticas de prueba.

---

# Parte 1 — Modelos de prueba (§8.2)

Veintitrés modelos. Cada uno lleva su objetivo, su prioridad —heredada del
riesgo que mitiga—, el extracto de estrategia que le aplica, el modelo en
sí y su trazabilidad.

La **prioridad** sale de la exposición del riesgo asociado en el
[plan](plan-de-pruebas.md) §5, y determina la profundidad según la regla
del §6.4 de ese mismo plan.

## MP-01 — Qué es un teléfono y qué es un BSUID

- **Objetivo**: que el sistema distinga los dos espacios de identificadores.
- **Prioridad**: 1 (riesgo P-02, exposición 20).
- **Estrategia**: particiones de equivalencia sobre la forma del identificador. Cobertura completa.
- **Modelo**: dos particiones válidas —cadena de dígitos con puntuación E.164; cadena que empieza por dos letras y un punto— y tres inválidas —vacía, nula, texto libre—. La partición frontera es el **BSUID corto** (`CO.12345678`), que contando solo dígitos pasaría por teléfono: es el caso que motivó el filtro de forma del ADR-0023.
- **Traza**: ADR-0023 · `identidad.es_telefono` · riesgo P-02.

## MP-02 — Longitud admisible del teléfono

- **Objetivo**: que solo se acepten números con forma de E.164.
- **Prioridad**: 2 (riesgo P-02).
- **Estrategia**: análisis de valores límite sobre el intervalo cerrado [8, 15]. Los cuatro límites y dos valores exteriores.
- **Modelo**: 7 inválido, 8 válido, 15 válido, 16 inválido. Modelo adicional de **invariancia**: un mismo número escrito con `+`, con espacios o con paréntesis debe producir una sola huella, porque cambiar la normalización equivale a cambiar el pepper.
- **Traza**: Fase 3 §5.2 · `identidad.normalizar_telefono` · riesgo P-02.

## MP-03 — Los dominios del HMAC separan los espacios de identificadores

- **Objetivo**: que la huella de un BSUID no pueda coincidir con la de un teléfono aunque compartan pepper y columna.
- **Prioridad**: 1 (riesgos P-02 y P-07).
- **Estrategia**: basada en especificación, comparando contra el HMAC calculado a mano.
- **Modelo**: tres dominios —`""` para el teléfono, `bsuid:` y `wamid:`— y la propiedad de determinismo. El dominio vacío del teléfono es **intocable**: ponerle etiqueta ahora dejaría sin reconocer a quien quedara identificada por número.
- **Traza**: ADR-0023 · `identidad.calcular_identidad_hash` · riesgos P-02, P-07.

## MP-04 — El `wamid` nunca en claro

- **Objetivo**: que ni la bitácora ni la base reciban el `wamid`, que lleva el teléfono dentro en base64.
- **Prioridad**: 1 (riesgo P-07, **defecto ya materializado** el 30/07/2026).
- **Estrategia**: conjetura de errores sobre el defecto conocido, más propiedades de la huella.
- **Modelo**: la referencia **no** puede ser un recorte del valor original —el teléfono va al principio—, debe ser prefijo de la huella para poder cruzar bitácora y tabla de idempotencia, y debe ser determinista para que el reintento de Meta se reconozca.
- **Traza**: ADR-0012 · migración `006` · `identidad.referencia_wamid` · riesgo P-07.

## MP-05 — Cifrado del nombre

- **Objetivo**: que la base solo almacene texto cifrado y que el nonce no se repita.
- **Prioridad**: 2 (riesgo P-07).
- **Estrategia**: ciclo cifrar–descifrar más propiedades.
- **Modelo**: ida y vuelta; dos cifrados del mismo nombre difieren; el nombre no aparece en el cifrado; sin nombre no hay cifrado, porque la columna admite nulos mientras ella no lo haya dado.
- **Traza**: Fase 3 §5.2 · `identidad.cifrar_nombre` · riesgo P-07.

## MP-06 — Firma de las peticiones de Meta

- **Objetivo**: capa 5 del modelo de seguridad. Que nadie que conozca la URL pública pueda inyectar mensajes.
- **Prioridad**: 1 (seguridad).
- **Estrategia**: particiones más conjetura de errores sobre la cabecera.
- **Modelo**: firma correcta; cuerpo alterado en un byte; cabecera ausente, vacía, sin prefijo `sha256=`, con otro algoritmo, y bien formada pero falsa.
- **Traza**: Fase 3 Tabla 3, capa 5 · `signature.firma_valida`.

## MP-07 — En qué campo viaja el destinatario

- **Objetivo**: que la respuesta salga por `recipient` al BSUID y por `to` al teléfono, y **nunca por los dos**.
- **Prioridad**: 1 (riesgo P-02, exposición 20).
- **Estrategia**: tabla de decisión de una condición. Cobertura completa.
- **Modelo**: si el destino es teléfono → `to`; si no → `recipient`. Regla añadida: exactamente una clave. Mandar las dos taparía para siempre un error en el BSUID, porque Meta usaría el número y el envío saldría bien.
- **Traza**: ADR-0023 · `whatsapp._campo_destino` · riesgo P-02.

## MP-08 — La escalera de identidad del despachador

- **Objetivo**: con qué se reconoce a la usuaria, y en qué orden.
- **Prioridad**: 1 (riesgo P-02).
- **Estrategia**: tabla de decisión de tres peldaños. Cobertura completa, más la **cadena** con MP-07.
- **Modelo**: BSUID del mensaje → BSUID del contacto → teléfono → descartar. El caso encadenado —mensaje sin teléfono, identificado por BSUID, respondido por `recipient`— es exactamente la cadena que falló el 15/09/2026.
- **Traza**: ADR-0023 · `dispatcher._resolver_identidad` · riesgo P-02.

## MP-09 — Normalización de texto para comparar

- **Objetivo**: que la comparación sea indulgente con tildes, mayúsculas, signos y espacios.
- **Prioridad**: 2.
- **Estrategia**: particiones de equivalencia sobre cada transformación.
- **Modelo**: minúsculas, sin tildes, sin signos, espacios colapsados. Caso especial: el **emoji de teclado** (`3️⃣`) debe quedar en su dígito, porque ella puede copiar la opción de la lista. Y se declara lo que la función **no** hace: no sirve para almacenar ni para mostrar.
- **Traza**: ADR-0016 · `texto.normalizar`.

## MP-10 — Saludo y ayuda sin modelo

- **Objetivo**: reconocer saludo y petición de ayuda **sin llamar a Gemini**, porque antes de la compuerta hacerlo ya sería tratamiento de datos.
- **Prioridad**: 1 (CU1, riesgo P-06).
- **Estrategia**: particiones más valor límite sobre la longitud.
- **Modelo**: conjunto cerrado de saludos y peticiones, con tope de cuatro palabras. La partición que importa es «saludo con consulta detrás»: `hola, mi tomate tiene bichos` **no** es un saludo, porque tratarlo como tal la dejaría sin respuesta a lo que preguntó.
- **Traza**: ADR-0006 · Fase 2 §4 · `consentimiento.es_saludo_o_ayuda`.

## MP-11 — Leer la respuesta a la lista numerada

- **Objetivo**: interpretar la elección del barrio sin modelo.
- **Prioridad**: 2 (riesgo P-16).
- **Estrategia**: particiones más valores límite sobre [1, máximo].
- **Modelo**: dígito, palabra (`tres`) y emoji de teclado son válidos; 0 y máximo+1 no; texto libre no. La **palabra es un requisito, no una concesión**: la transcripción de voz es literal, así que una nota diciendo «tres» llega en letras, y sin ella quien responde por voz no podría terminar el onboarding.
- **Traza**: ADR-0016 · `onboarding.leer_numero` · riesgo P-16.

## MP-12 — Componer la lista numerada

- **Objetivo**: que la lista y su lector estén de acuerdo sobre cuál es el máximo.
- **Prioridad**: 2 (riesgo P-16).
- **Estrategia**: basada en especificación, más una prueba de **coherencia entre dos modelos** (MP-11 y MP-12).
- **Modelo**: `n` candidatos más «ninguno» —y opcionalmente «mi barrio no está»— dan `n+1` o `n+2` opciones. Los nombres van completos: el cuerpo admite 1024 caracteres, que es lo que permitió descartar los botones, cuyo rótulo admite 20.
- **Traza**: ADR-0016 · `onboarding.componer_opciones` · riesgo P-16.

## MP-13 — Qué es una respuesta aprovechable

- **Objetivo**: descartar lo que claramente no es un nombre, sin pretender validar que lo sea.
- **Prioridad**: 3.
- **Estrategia**: particiones más valor límite sobre el número de palabras.
- **Modelo**: vacío, solo espacios, pregunta, o más de cuatro palabras → no útil. Lo que se cuele lo corrige ella en la confirmación final.
- **Traza**: ADR-0016 · `onboarding._es_respuesta_util`.

## MP-14 — Selección y orden de las llamadas del agente

- **Objetivo**: que el orden lo imponga el código y no el modelo.
- **Prioridad**: 1 (Fase 2 §4, decisión no negociable).
- **Estrategia**: tabla de decisión de tres reglas. Cobertura completa.
- **Modelo**: sin repetidas; la ayuda cede si hay algo más; el registro **siempre el último**, porque lleva botones y tienen que quedar en el último mensaje de la pantalla. Más el tope de llamadas por turno, que evita la ráfaga de mensajes.
- **Traza**: ADR-0013 · ADR-0022 · CLAUDE.md §5 · `agente._seleccionar`.

## MP-15 — Los prompts versionados cargan

- **Objetivo**: que una llave literal no rompa la carga con `KeyError` a mitad del turno.
- **Prioridad**: 2 (riesgo P-09).
- **Estrategia**: **inventario exhaustivo**, no muestreo: los seis vigentes y los cuatro históricos, uno por uno.
- **Modelo**: cada prompt vigente carga y su texto es analizable por `str.format`; el del agente **no lleva huecos**, a propósito; los cuatro históricos siguen en el repositorio como evidencia citable; un prompt inexistente falla de forma explícita y no como cadena vacía.
- **Traza**: CLAUDE.md §11 · `plantillas.cargar_prompt` · riesgo P-09.

## MP-16 — La advertencia médica

- **Objetivo**: que toda respuesta del CU2 que hable de salud la lleve, la ponga el camino que la ponga.
- **Prioridad**: 1 (riesgo P-01: la única consecuencia de nivel 5 con daño físico posible).
- **Estrategia**: particiones sobre el vocabulario, más posición en el texto.
- **Modelo**: particiones de vocabulario —uso medicinal, toxicidad, preparación, contraindicación, efecto terapéutico— frente a texto agronómico puro. La advertencia va **al final**, después de la línea de la fuente, para no romper la atribución. **No se exige idempotencia**, y se explica por qué en el código (incidencia INC-003).
- **Traza**: ADR-0015 · `orientacion._con_advertencia_medica` · riesgo P-01.

## MP-17 — Las etiquetas de procedencia no se cuelan

- **Objetivo**: que el andamiaje del prompt no llegue a la usuaria, y que la atribución sí.
- **Prioridad**: 2 (riesgo P-08).
- **Estrategia**: particiones sobre las dos formas observadas de la etiqueta.
- **Modelo**: etiqueta entera con corchetes —se conserva lo de dentro—; etiqueta suelta sin corchetes, que es como se coló de verdad en la prueba con celular; texto ya limpio, que no se toca; espacios dobles que se colapsan. Modelo asociado: una huerta **sin nombre** se identifica por su barrio, que es lo único que se puede decir de ella sin inventar.
- **Traza**: ADR-0001 · Fase 4 §5 · `recuperacion.limpiar_etiquetas` · riesgo P-08.

## MP-18 — La especie está de verdad en esa huerta

- **Objetivo**: no atribuirle a una huerta un cultivo que no sembró.
- **Prioridad**: 1 (riesgo P-08; el peor fallo posible en el dato comunitario).
- **Estrategia**: particiones sobre la comparación por palabra completa.
- **Modelo**: `papa` **no** puede dar por buena una huerta que sembró `papaya`; `cebolla` **sí** encuentra `cebolla larga`, porque quien pregunta nombra la especie más corta de como está registrada. Hace falta porque el umbral no basta: con 5 a 7 huertas y top-k=4 la similitud recupera medio corpus.
- **Traza**: ADR-0011 · ADR-0021 · `comunidad._tiene_la_especie` · riesgo P-08.

## MP-19 — Fusión del borrador de registro

- **Objetivo**: que la conversación a trozos no pierda lo que ella ya contó.
- **Prioridad**: 2 (CU3).
- **Estrategia**: particiones sobre la acumulación y la deduplicación.
- **Modelo**: «también sembré lechuga» **añade**, no sustituye; la misma especie no se repite, ni cambiando mayúsculas; lo último dicho va primero; fusionar con un borrador vacío no pierde nada.
- **Traza**: ADR-0008 · `registro.fusionar`.

## MP-20 — Normalización L2 del vector

- **Objetivo**: que los vectores truncados a 768 dimensiones queden de longitud 1.
- **Prioridad**: 3.
- **Estrategia**: propiedades matemáticas más el caso límite.
- **Modelo**: norma resultante 1; un vector ya normalizado no cambia; el **vector nulo es un error** y no se tolera, porque no tiene dirección y la similitud coseno queda indefinida.
- **Traza**: ADR-0007 · corrección §9.1 · `embeddings._normalizar_l2`.

## MP-21 — El texto que se vectoriza

- **Objetivo**: que el fragmento comunitario lleve las especies y nada más.
- **Prioridad**: 2.
- **Estrategia**: basada en especificación.
- **Modelo**: especies separadas por comas; sin fecha, sin barrio, sin nombre. La fecha dentro del fragmento empeoraba la separación —0.0735 frente a 0.1166— y además no la leía ningún caso de uso. Una huerta sin cultivos da texto vacío, que es lo normal desde el onboarding.
- **Traza**: ADR-0011 · ADR-0018 · `fragmento_comunitario.componer_texto`.

## MP-22 — El servicio se niega a arrancar mal configurado

- **Objetivo**: que un fallo de configuración aparezca al arrancar y no al registrar a la primera usuaria.
- **Prioridad**: 2 (riesgo P-12).
- **Estrategia**: valores límite sobre cada validador.
- **Modelo**: pepper de 31 caracteres frente a 32; clave de cifrado de 16, 31, 32 y 33 bytes; umbral en −0.1, 0, 1 y 1.1; top-k y tamaños del listado en 0 y 1; ventana de memoria en 1 y 2; puerto 6543 frente a 5432; esquema que no es PostgreSQL; identificador de embeddings puesto donde va el generativo. Se declara además **lo que la validación del umbral no puede atrapar**: escribir la distancia en lugar de la similitud.
- **Traza**: ADR-0007 · CLAUDE.md §8 · `config.py` · riesgo P-12.

## MP-23 — Contrato del webhook con Meta

- **Objetivo**: que el webhook responda lo que Meta espera y delegue sin esperar.
- **Prioridad**: 1 (procesamiento asíncrono e idempotencia; corrección §9.2).
- **Estrategia**: tabla de decisión sobre método, firma y forma del cuerpo. Nivel de integración.
- **Modelo**: `GET` con token correcto devuelve el reto **en texto plano** —envuelto en JSON, Meta rechaza la verificación—; `GET` con token incorrecto o incompleto, 403. `POST` firmado, 200 y encolado; sin firma o con firma de otro cuerpo, 403 y **nada encolado**; cuerpo no-JSON con firma válida, **200 a propósito**, porque reintentarlo no cambia nada. Y el 200 **no espera** al procesamiento: si el despachador falla, la respuesta ya se había devuelto.
- **Traza**: ADR-0005 · corrección §9.2 · `api/webhook.py`.

---

# Parte 2 — Casos de prueba (§8.3)

Los ítems de cobertura derivados de los modelos y sus casos **son las
funciones de `tests/`**. Cada función lleva en su nombre el modelo del que
sale (`test_mp07_...`) y en su docstring la razón por la que existe.

## MP-24 — La línea de la fuente la pone el backend

- **Objetivo**: que una respuesta que declina no lleve cita, y que la cita que lleve la ponga el backend con la entidad de la tabla `fuente`.
- **Prioridad**: 1 (CU2). Sale de una incidencia de severidad 2 medida en producción: 6 de 20.
- **Estrategia**: tabla de decisión sobre dos condiciones —el modelo puso la marca, el modelo escribió una línea de fuente— y conjetura de errores sobre cómo puede escribir la marca.
- **Modelo**: sin marca se cita; con marca no se cita; la marca se reconoce con corchetes, sin ellos y en minúscula; la frase corriente «sin respaldo» **no** es la marca; la fuente que escriba el modelo se retira siempre; la entidad es la que recibe la función, no la que diga el texto; no quedan renglones vacíos de más; la advertencia médica va después de la cita.
- **Traza**: ADR-0025 · INC-020 · `orientacion._con_cita` · `prompts/redaccion_rag_v2.md`.

## Matriz de trazabilidad

| Modelos | Archivo de casos | Casos | Riesgo principal |
|---|---|---|---|
| MP-01 a MP-06 | `tests/test_identidad_y_firma.py` | 43 | P-02, P-07 |
| MP-07, MP-08 | `tests/test_destino.py` | 11 | **P-02 (exposición 20)** |
| MP-09 a MP-13 | `tests/test_conversacion.py` | 56 | P-16, P-06 |
| MP-14 a MP-17, MP-24 | `tests/test_agente_y_respuesta.py` | **54** | P-01, **P-03**, P-09, P-08 |
| MP-18 a MP-21 | `tests/test_datos.py` | 23 | P-08 |
| MP-22 | `tests/test_config.py` | 34 | P-12 |
| MP-23 | `tests/test_webhook.py` | 10 | Seguridad, ADR-0005 |
| **Total** | | **231** | |

## Trazabilidad hacia los casos de uso

| Caso de uso | Modelos que lo cubren en este nivel | Sistema | Aceptación |
|---|---|---|---|
| CU1 Consentimiento | MP-10 | `spike_despachador`, comprob. 1 y 2 | Sí, 12 participantes |
| CU2 Orientación | MP-15, MP-16, MP-17, MP-24 | Banco de 20 preguntas | Sí, 7 participantes |
| CU3 Registro | MP-19 | `spike_despachador`, comprob. 4 | Sí, 6 participantes |
| CU4 Comunidad | MP-17 | `spike_despachador`, comprob. 6 | **Sin evidencia** (INC-027) |
| CU5 Ayuda | MP-10, MP-14 | `spike_despachador`, comprob. 2 | Sí, 1 participante |
| CU6 Onboarding | MP-11, MP-12, MP-13 | — | Sí, 10 de 12 lo completaron |
| CU7 Búsqueda por cultivo | MP-18 | — | **Sin evidencia** (INC-027) |
| CU8 Mi huerta | MP-14 | `spike_despachador`, comprob. 7 | **Sin evidencia** (INC-027) |

**Cinco de los ocho casos de uso tienen aceptación con evidencia**, según
el [registro de aceptación](registro-de-aceptacion.md) (A-14, 25/09/2026), reconstruido desde `mensaje` sin contenido de
nadie. Hasta ese día este documento decía «los ocho», apoyado en la
declaración del autor; al reconstruirlo, **ninguna de las doce
participantes usó nunca el CU4, el CU7 ni el CU8** (INC-027).

Queda además una deuda de *tipo*, no de nivel: la aceptación demuestra que
los casos de uso **funcionan**, no que el CU2 **acierte**. Eso lo mide el
[banco de 20 preguntas](banco-de-preguntas.md).

---

# Parte 3 — Procedimientos de prueba (§8.4)

## PR-01 — Componente e integración

- **Objetivo**: ejecutar los 231 casos de los modelos MP-01 a MP-24.
- **Prioridad**: 1.
- **Preparación**: `pip install -r requirements.txt -r requirements-dev.txt`. No hace falta `.env`: `tests/conftest.py` pone un entorno falso y completo, que gana al archivo del equipo.
- **Ejecución**: `python -m pytest`
- **Relación con otros**: ninguna. Es el primero de la cadena.
- **Cierre**: ninguno. **Ninguna de estas pruebas abre la base de datos, llama a Meta ni llama a Gemini**, así que no deja nada que limpiar.

## PR-02 — Sistema

- **Objetivo**: comprobar los nueve caminos de la rama completa.
- **Prioridad**: 1.
- **Preparación**: `.env` completo y acceso a Supabase.
- **Ejecución**: `python -m scripts.spike_despachador`
- **Relación con otros**: después de PR-01.
- **Cierre**: el script borra en un `finally` las filas temporales que creó, identificadas por `57000000`. **Comprobar que no quedó ninguna** antes de dar por terminado.
- **Aislamiento**: `scripts/arnes.py` sustituye por espías los **cuatro** puntos por los que se sale a Meta, incluido el indicador de escritura. Hasta el 24/09/2026 eran tres y el cuarto sí llamaba a la API (INC-023).
- **Repeticiones**: el enrutamiento del agente corre a temperatura 0.7 y **no es determinista**. Un fallo aislado no es un defecto: repetir antes de levantar incidencia.

## PR-03 — Instalabilidad

- **Objetivo**: confirmar qué está corriendo de verdad tras un despliegue.
- **Prioridad**: 1 (riesgo P-12).
- **Preparación**: despliegue promovido en Railway.
- **Ejecución**: consultar `/health` y comprobar tres cosas: `status` en `ok`, `version.commit` igual al `HEAD` que se subió, y `modelo_generativo` igual al esperado.
- **Relación con otros**: después de PR-02 y antes de PR-04.
- **Cierre**: ninguno.

## PR-04 — Aceptación

- **Objetivo**: la conversación completa desde un celular real.
- **Prioridad**: 1.
- **Preparación**: PR-03 en verde y migraciones aplicadas. Para repetir el onboarding basta con **borrar la fila de `huerta`** de esa usuaria; borrar `usuario` también sirve, pero se lleva por cascada la conversación, que es el material de la Fase 7.
- **Ejecución**: saludo, consentimiento, onboarding de tres preguntas, una consulta del CU2, un registro de cultivo, una consulta comunitaria, una nota de voz.
- **Relación con otros**: el último.
- **Cierre**: `python -m scripts.registro_aceptacion` produce el resultado por caso de uso y la bitácora, **sin contenido de nadie**, y su salida va al [registro de aceptación](registro-de-aceptacion.md). Para diagnosticar una consulta concreta, `python -m scripts.revisar_prueba_real`, cuya salida lleva la conversación en claro y **no va al repositorio, que es público**.

## PR-05 — Banco de veinte preguntas

- **Objetivo**: calificar la **calidad** de la respuesta del CU2, que es lo único que ni PR-01 ni PR-02 miran.
- **Prioridad**: 1 (riesgos P-01 y P-03). Es el criterio de terminación 5.
- **Preparación**: `.env` completo, acceso a Supabase y a Gemini. Corpus en el estado que se quiera medir.
- **Ejecución**: `python -m scripts.ejecutar_banco`, y calificar leyendo las respuestas contra los fragmentos.
- **Relación con otros**: **antes y después** de cualquier cambio en el corpus o en los prompts del CU2. Su valor está en comparar dos salidas.
- **Cierre**: el script borra en un `finally` la identidad temporal `CO.570000000605` y sus filas de idempotencia.
