# Especificación de pruebas

| | |
|---|---|
| **Identificador** | `ESP-CHU-001`, versión 1.7 |
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
| 05/10/2026 | 1.3 | MP-25, la limpieza del corpus (INC-019 e INC-010): 28 casos. MP-16 gana 11 casos por INC-024. Total 270 | A. Ramírez |
| 10/10/2026 | 1.4 | **Depuración de los casos**: de 271 a 198. Se retira MP-21 y 74 casos que repetían una partición, probaban valores sin ser límite, repetían otra afirmación, no podían fallar o no probaban código. Se rehacen dos casos que no comprobaban lo que decían (INC-028, INC-029) y se añaden tres que faltaban. Ver «Depuración del 10/10/2026» | A. Ramírez |
| 10/10/2026 | 1.5 | **Trazabilidad hacia los requisitos** de las Tablas 5 y 6 del documento de grado, en las dos direcciones. Hasta esta versión los modelos se trazaban a riesgos, ADR y casos de uso, pero a ningún requisito | A. Ramírez |
| 10/10/2026 | 1.6 | **MP-26, MP-27 y MP-28**, para los tres requisitos que quedaron sin cobertura: RNF-07, RNF-08 y RF-19. 33 casos, cada regla comprobada con una mutación. Total 231 | A. Ramírez |
| 12/10/2026 | 1.7 | Aceptación de CU4, CU7 y CU8 en producción (INC-027 cerrada): RF-16, RF-21 y RF-22 pasan a cubiertos. **De 24 requisitos, 17 cubiertos** | A. Ramírez |

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

Veintisiete modelos vigentes, de MP-01 a MP-28: MP-21 se retiró el
10/10/2026 y conserva su número para que las referencias de otros
documentos sigan siendo válidas. Cada uno lleva su objetivo, su
prioridad —heredada del riesgo que mitiga—, el extracto de estrategia que
le aplica, el modelo en sí y su trazabilidad.

La **prioridad** sale de la exposición del riesgo asociado en el
[plan](plan-de-pruebas.md) §5, y determina la profundidad según la regla
del §6.4 de ese mismo plan.

## MP-01 — Qué es un teléfono y qué es un BSUID

- **Objetivo**: que el sistema distinga los dos espacios de identificadores.
- **Prioridad**: 1 (riesgo P-02, exposición 20).
- **Estrategia**: particiones de equivalencia sobre la forma del identificador. Cobertura completa.
- **Modelo**: dos particiones válidas —cadena de dígitos, con y sin puntuación E.164; cadena que empieza por dos letras y un punto— y tres inválidas —vacía, nula, texto libre—. Un caso por partición. La partición frontera es el **BSUID corto** (`CO.12345678`), que contando solo dígitos pasaría por teléfono: es el caso que motivó el filtro de forma del ADR-0023.
- **Traza**: ADR-0023 · `identidad.es_telefono` · riesgo P-02.

## MP-02 — Longitud admisible del teléfono

- **Objetivo**: que solo se acepten números con forma de E.164.
- **Prioridad**: 2 (riesgo P-02).
- **Estrategia**: análisis de valores límite de dos valores sobre el intervalo cerrado [8, 15].
- **Modelo**: 7 inválido, 8 válido, 15 válido, 16 inválido. El mensaje de error no lleva el número. Modelo adicional de **invariancia**: un mismo número escrito con `+`, con espacios o con paréntesis debe producir una sola huella, porque cambiar la normalización equivale a cambiar el pepper.
- **Traza**: Fase 3 §5.2 · `identidad.normalizar_telefono` · riesgo P-02.

## MP-03 — Los dominios del HMAC separan los espacios de identificadores

- **Objetivo**: que la huella de un BSUID no pueda coincidir con la de un teléfono aunque compartan pepper y columna.
- **Prioridad**: 1 (riesgos P-02 y P-07).
- **Estrategia**: basada en especificación, comparando contra el HMAC calculado a mano.
- **Modelo**: dos casos, uno por dominio de identidad —`""` para el teléfono y `bsuid:`—; el de `wamid:` es MP-04. Comparar contra el HMAC exacto ya implica el determinismo, y comparar dos huellas de identificadores distintos no probaría la etiqueta: darían distinto con ella o sin ella. El dominio vacío del teléfono es **intocable**: ponerle etiqueta ahora dejaría sin reconocer a quien quedara identificada por número.
- **Traza**: ADR-0023 · `identidad.calcular_identidad_hash` · riesgos P-02, P-07.

## MP-04 — El `wamid` nunca en claro

- **Objetivo**: que ni la bitácora ni la base reciban el `wamid`, que lleva el teléfono dentro en base64.
- **Prioridad**: 1 (riesgo P-07, **defecto ya materializado** el 30/07/2026).
- **Estrategia**: conjetura de errores sobre el defecto conocido, más propiedades de la huella.
- **Modelo**: la referencia **no** puede ser un recorte del valor original —el teléfono va al principio—, debe ser prefijo de la huella para poder cruzar bitácora y tabla de idempotencia, y mide 16 hexadecimales. El determinismo y que dos `wamid` den huellas distintas son propiedades de HMAC, no del código, y no llevan caso.
- **Traza**: ADR-0012 · migración `006` · `identidad.referencia_wamid` · riesgo P-07.

## MP-05 — Cifrado del nombre

- **Objetivo**: que la base solo almacene texto cifrado y que el nonce no se repita.
- **Prioridad**: 2 (riesgo P-07).
- **Estrategia**: ciclo cifrar–descifrar más propiedades.
- **Modelo**: ida y vuelta; dos cifrados del mismo nombre difieren —lo que además descarta que el cifrado devuelva el nombre a la vista—; sin nombre no hay cifrado, porque la columna admite nulos mientras ella no lo haya dado.
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
- **Modelo**: si el destino es teléfono → `to`; si no → `recipient`. Regla añadida: exactamente una clave, que la cubren las dos comparaciones exactas sin caso propio. Mandar las dos taparía para siempre un error en el BSUID, porque Meta usaría el número y el envío saldría bien.
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
- **Estrategia**: particiones de equivalencia.
- **Modelo**: pertenencia exacta a un conjunto cerrado de saludos y peticiones. La partición que importa es «saludo con consulta detrás»: `hola, mi tomate tiene bichos` **no** es un saludo, porque tratarlo como tal la dejaría sin respuesta a lo que preguntó. **El tope de cuatro palabras no lleva caso** porque no tiene efecto observable: la frase más larga del conjunto mide tres, así que ninguna entrada de cuatro puede dar verdadero (INC-030).
- **Traza**: ADR-0006 · Fase 2 §4 · `consentimiento.es_saludo_o_ayuda`.

## MP-11 — Leer la respuesta a la lista numerada

- **Objetivo**: interpretar la elección del barrio sin modelo.
- **Prioridad**: 2 (riesgo P-16).
- **Estrategia**: particiones más valores límite sobre [1, máximo].
- **Modelo**: dígito, palabra (`tres`) y emoji de teclado son válidos; 0 y máximo+1 no —los dígitos los cubren los cuatro valores límite, sin casos aparte—; texto libre no, tampoco con un dígito dentro. La **palabra es un requisito, no una concesión**: la transcripción de voz es literal, así que una nota diciendo «tres» llega en letras, y sin ella quien responde por voz no podría terminar el onboarding.
- **Traza**: ADR-0016 · `onboarding.leer_numero` · riesgo P-16.

## MP-12 — Componer la lista numerada y el resumen

- **Objetivo**: que la lista y su lector estén de acuerdo sobre cuál es el máximo, y que el resumen del cierre muestre lo que se va a guardar.
- **Prioridad**: 2 (riesgo P-16).
- **Estrategia**: basada en especificación, más una prueba de **coherencia entre dos modelos** (MP-11 y MP-12).
- **Modelo**: `n` candidatos más «ninguno» —y opcionalmente «mi barrio no está»— dan `n+1` o `n+2` opciones. Los nombres van completos: el cuerpo admite 1024 caracteres, que es lo que permitió descartar los botones, cuyo rótulo admite 20. El resumen lleva nombre, barrio y huerta, y sin nombre no inventa la línea. Esos dos casos existían sin modelo hasta el 10/10/2026.
- **Traza**: ADR-0016 · CLAUDE.md §4.7 · `onboarding.componer_opciones` · `onboarding.componer_resumen` · riesgo P-16.

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
- **Estrategia**: **inventario exhaustivo** de los seis prompts vigentes, tomados de la constante de cada módulo para que la prueba siga al que de verdad se carga.
- **Modelo**: los huecos de cada prompt son **exactamente** los que le rellena su `.format()`; el del agente **no lleva ninguno**, a propósito; un prompt inexistente falla de forma explícita y no como cadena vacía. Que el texto se deje analizar no basta: `parse` acepta `{"clave": 1}` como un hueco más (INC-028). Los históricos no llevan caso: no los carga nadie, y su conservación la garantiza git.
- **Traza**: CLAUDE.md §11 · `plantillas.cargar_prompt` · riesgo P-09.

## MP-16 — La advertencia médica

- **Objetivo**: que toda respuesta del CU2 que hable de salud la lleve, la ponga el camino que la ponga.
- **Prioridad**: 1 (riesgo P-01: la única consecuencia de nivel 5 con daño físico posible).
- **Estrategia**: particiones sobre el vocabulario, más posición en el texto.
- **Modelo**: particiones de vocabulario —uso medicinal, toxicidad, preparación, contraindicación, efecto terapéutico— frente a texto agronómico puro. Una raíz por cada entrada que INC-024 dejó pasar, y una por cada exclusión agronómica de `salud`. `cicatrice`, con c, lleva su caso: es el único que cubre el subjuntivo. La advertencia va **al final**, después de la línea de la fuente, para no romper la atribución. **No se exige idempotencia**, y se explica por qué en el código (incidencia INC-003).
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
- **Modelo**: `papa` **no** puede dar por buena una huerta que sembró `papaya` —un caso cubre la partición «subcadena de otra palabra»—; `cebolla` **sí** encuentra `cebolla larga`, porque quien pregunta nombra la especie más corta de como está registrada. Hace falta porque el umbral no basta: con 5 a 7 huertas y top-k=4 la similitud recupera medio corpus.
- **Traza**: ADR-0011 · ADR-0021 · `comunidad._tiene_la_especie` · riesgo P-08.

## MP-19 — Fusión del borrador de registro

- **Objetivo**: que la conversación a trozos no pierda lo que ella ya contó.
- **Prioridad**: 2 (CU3).
- **Estrategia**: particiones sobre la acumulación y la deduplicación.
- **Modelo**: «también sembré lechuga» **añade**, no sustituye; la misma especie no se repite, ni cambiando mayúsculas —un solo caso, porque si se detecta con mayúsculas distintas se detecta con las mismas—; lo último dicho va primero; fusionar con un borrador vacío no pierde nada.
- **Traza**: ADR-0008 · `registro.fusionar`.

## MP-20 — Normalización L2 del vector

- **Objetivo**: que los vectores truncados a 768 dimensiones queden de longitud 1.
- **Prioridad**: 3.
- **Estrategia**: propiedades matemáticas más el caso límite.
- **Modelo**: norma resultante 1, con el triángulo 3-4-5 para tener el resultado exacto; un vector ya normalizado no cambia; el **vector nulo es un error** y no se tolera, porque no tiene dirección y la similitud coseno queda indefinida.
- **Traza**: ADR-0007 · corrección §9.1 · `embeddings._normalizar_l2`.

## MP-21 — El texto que se vectoriza · **retirado el 10/10/2026**

- **Por qué se retira**: `componer_texto` es `", ".join(especies)` y solo recibe la lista de especies. Lo que el modelo decía probar —sin fecha, sin barrio, sin nombre— no lo puede violar la función: lo garantiza su firma. Sus dos casos eran tautologías.
- **Lo que no se pierde**: la decisión sigue trazada en el ADR-0011 y el ADR-0018, y un cambio de firma que metiera esos datos se vería en la revisión del código, no en esta prueba.

## MP-22 — El servicio se niega a arrancar mal configurado

- **Objetivo**: que un fallo de configuración aparezca al arrancar y no al registrar a la primera usuaria.
- **Prioridad**: 2 (riesgo P-12).
- **Estrategia**: valores límite sobre cada validador.
- **Modelo**: pepper de 31 caracteres frente a 32; clave de cifrado de 16, 31, 32 y 33 bytes —16 por ser el error realista de generar una clave AES-128—; umbral en −0.1, 0, 1 y 1.1; top-k y los dos tamaños del listado en 0 y 1, los tres; ventana de memoria en 1 y 2; puerto 6543 frente a 5432; esquema que no es PostgreSQL; identificador de embeddings puesto donde va el generativo. Se declara además **lo que la validación del umbral no puede atrapar**: escribir la distancia en lugar de la similitud.
- **Traza**: ADR-0007 · CLAUDE.md §8 · `config.py` · riesgo P-12.

## MP-23 — Contrato del webhook con Meta

- **Objetivo**: que el webhook responda lo que Meta espera y delegue sin esperar.
- **Prioridad**: 1 (procesamiento asíncrono e idempotencia; corrección §9.2).
- **Estrategia**: tabla de decisión sobre método, firma y forma del cuerpo. Nivel de integración.
- **Modelo**: `GET` con token correcto devuelve el reto **en texto plano** —envuelto en JSON, Meta rechaza la verificación—; `GET` con token incorrecto o incompleto, 403. `POST` firmado, 200 y encolado; sin firma o con firma de otro cuerpo, 403 y **nada encolado**; cuerpo no-JSON con firma válida, **200 a propósito**, porque reintentarlo no cambia nada. Y el 200 **no espera** al procesamiento: si el despachador falla, la respuesta ya se había devuelto. Ese caso corre con `raise_server_exceptions=False`; sin eso pasaba igual con el procesamiento en línea (INC-029).
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

## MP-25 — La limpieza del corpus

- **Objetivo**: que la limpieza quite lo que tiene que quitar **y no toque lo que estaba bien**. Una regla ancha estropea un texto correcto, y se aplica con una escritura en la base de producción.
- **Prioridad**: 2 (CU2). Riesgo P-14.
- **Estrategia**: particiones de equivalencia entre lo que se quita y lo que se conserva, más propiedades —idempotencia, y que un fragmento limpio se devuelva idéntico— y conjetura de errores sobre las frases reales que ya fallaron.
- **Modelo**: las viñetas de fuente simbólica, el marcador de objeto y el acento huérfano se quitan; los apellidos de las bibliografías y los nombres científicos **no**. Los rótulos del margen se quitan solo si están sueltos —ni letras ni números pegados—, y solo en la fuente que los declara; el nombre de una empresa en mayúscula no es un rótulo; dos rótulos seguidos se quitan los dos; limpiar dos veces es limpiar una. Cada caso de rótulo compara la salida exacta, y con eso cubre también que no queden espacios dobles. Qué fuentes declaran rótulos es un dato del catálogo, no un comportamiento, y no lleva caso.
- **Traza**: INC-019 · INC-010 · `ingesta_fuente.limpiar_fragmento` · `catalogo_fuentes.rotulos_del_margen`.

## MP-26 — El filtrado por `usuario_id`

- **Objetivo**: que ninguna consulta lea ni escriba el dato de una persona sin acotarlo a ella. Es la capa 1 del modelo de seguridad y su barrera principal: el RLS solo la respalda, porque el backend usa service role.
- **Prioridad**: 1 (RNF-07, riesgo P-08).
- **Estrategia**: **inventario exhaustivo** de las funciones públicas de `repositorio`, que es el único punto de acceso a Supabase, más una tabla de decisión por clase. Se ejecuta cada función contra un pool espía que anota el SQL y sus argumentos: no se abre la base.
- **Modelo**: cada función cae en una de cinco clases, y una función nueva sin clasificar hace fallar el inventario. **De una persona** —quince—: cada sentencia sobre una tabla personal usa el `usuario_id` recibido en una comparación o en su columna del insert, o el `id` de la huerta que devolvió una consulta ya acotada; se prueban las dos ramas de las que crean o reutilizan la huerta. **Por identidad** —dos—: acotadas por la huella de la identidad. **Comunitarias** —tres—: dejan fuera a quien pregunta con `usuario_id <> $n`. **Por huerta** y **sin dueño**: declaradas, con su razón, sin más exigencia.
- **Límite declarado**: comprueba el SQL que se manda, no lo que la base hace con él. Un `join` mal escrito que sí filtrara por `usuario_id` pasaría. Lo que no puede pasar es una sentencia que no use el identificador, que es el defecto que importa.
- **Traza**: Fase 3 §5.1, capa 1 · RNF-07 · riesgo P-08 · `services/repositorio`.

## MP-27 — Solo columnas compartibles en lo comunitario

- **Objetivo**: que el CU4 y el CU7 no lean ni devuelvan nada que identifique a otra persona.
- **Prioridad**: 1 (RNF-08, riesgo P-08).
- **Estrategia**: basada en especificación, sobre el SQL de las tres consultas comunitarias y sobre la forma de lo que devuelven.
- **Modelo**: ninguna de las tres nombra el nombre cifrado, la huella de identidad ni el teléfono, ni lee las tablas `usuario` o `mensaje`, ni saca el `usuario_id` en la selección. Y los objetos que devuelven tienen **exactamente** los campos compartibles: un campo nuevo es un dato nuevo que ve otra vecina, y la prueba obliga a decidirlo a conciencia.
- **Traza**: Fase 3 §5, capa 4 · RNF-08 · riesgo P-08 · `repositorio.FragmentoComunitario` · `repositorio.HuertaDeLaComunidad`. El plan ya declaraba «componente sobre las columnas compartibles» como mitigación de P-08; hasta este modelo, ese caso no existía.

## MP-28 — El acuse de la nota de voz

- **Objetivo**: que la nota de voz se acuse en el acto y que el acuse no entre en la memoria.
- **Prioridad**: 2 (RF-19).
- **Estrategia**: basada en especificación, por el camino real del despachador (`_atender_mensaje`) con espías solo en los bordes: lo que sale hacia Meta, la transcripción y la memoria.
- **Modelo**: el acuse llega a quien escribió con una frase del repertorio; la única escritura en la memoria es lo que ella dijo, transcrito y anotado como audio; el acuse llega antes de que termine la transcripción; si el acuse falla, la nota se atiende igual; y sin consentimiento no hay ni acuse ni transcripción. El espía de la transcripción **cede el turno** como lo hace la real al descargar el audio: sin eso mediría un orden que en producción no se da.
- **Traza**: ADR-0017 · CLAUDE.md §11, la excepción declarada a «enviar y recordar van juntos» · RF-19 · `services/espera`.

## Matriz de trazabilidad

| Modelos | Archivo de casos | Casos | Riesgo principal |
|---|---|---|---|
| MP-01 a MP-06 | `tests/test_identidad_y_firma.py` | 29 | P-02, P-07 |
| MP-07, MP-08 | `tests/test_destino.py` | 7 | **P-02 (exposición 20)** |
| MP-09 a MP-13 | `tests/test_conversacion.py` | 39 | P-16, P-06 |
| MP-14 a MP-17, MP-24 | `tests/test_agente_y_respuesta.py` | 47 | P-01, **P-03**, P-09, P-08 |
| MP-18 a MP-20 | `tests/test_datos.py` | 15 | P-08 |
| MP-22 | `tests/test_config.py` | 29 | P-12 |
| MP-23 | `tests/test_webhook.py` | 9 | Seguridad, ADR-0005 |
| MP-25 | `tests/test_corpus.py` | 23 | P-14 |
| MP-26, MP-27 | `tests/test_capa_de_datos.py` | 28 | P-08 |
| MP-28 | `tests/test_acuse_de_voz.py` | 5 | RF-19 |
| **Total** | | **231** | |

## Depuración del 10/10/2026

Hasta la versión 1.3 la suite había crecido por acumulación: cada
incidencia añadía casos y ninguno se retiraba. El 10/10/2026 se revisaron
los 271 casos —la matriz decía 270; el de más era `agente_v2.md`, que
pasó a histórico con el `agente_v3.md`— contra los modelos de la parte 1,
y se retiraron **74 casos y un modelo** con cinco criterios:

| Criterio | Ejemplo | Casos |
|---|---|---|
| **Misma partición** que otro caso | `HOLA` y `Hola` en MP-10, cuando las mayúsculas son de MP-09 | 21 |
| **Valor que no es límite** en un análisis de valores límite | 9 y 14 en MP-02; 0.66 y 2.0 en MP-22 | 10 |
| **Repite la afirmación** de otro caso | «el BSUID gana aunque venga el teléfono» repetía el primer caso de MP-08 | 26 |
| **No puede fallar**, o prueba la librería y no el código | dos huellas de identificadores distintos difieren con etiqueta de dominio o sin ella | 7 |
| **No prueba código**: existencia de archivos, datos del catálogo, lo que la función no hace | los seis prompts históricos «siguen en el repositorio» | 10 |

Y se **rehicieron** dos casos que no comprobaban lo que decían, los dos
registrados como defectos del caso de prueba: el de las llaves de los
prompts (INC-028) y el del 200 que no espera al despachador (INC-029). Los
dos se comprobaron con una mutación: introducido el defecto que dicen
atrapar, ahora fallan; antes pasaban. Se **añadieron** tres casos que el
modelo MP-22 pedía y no tenía —top-k y tamaños del listado en 1—. Las
otras dos bajas no entran en la tabla: el caso «el prompt del agente no
lleva huecos» pasó a ser una fila más del de MP-15, y el del tope de
cuatro palabras de MP-10 se retiró porque no se podía reescribir: ese
tope no tiene efecto observable (INC-030). En cuentas: 271 − 74 − 2 + 3
= 198.

La regla que queda para lo que venga: **un caso nuevo tiene que poder
decir qué partición, límite o regla del modelo cubre que no cubra ya otro
caso.** Si no puede, no entra.

## Trazabilidad hacia los requisitos

La base de prueba son los requisitos de las Tablas 5 y 6 del documento de
grado. Hasta la versión 1.5 ningún modelo se trazaba a ellos, y al
cruzarlos aparecieron dos requisitos desactualizados —RNF-03 y RNF-04
seguían hablando del número de celular, que el ADR-0023 dejó de guardar—
y tres casos de uso sin requisito —CU6, CU7 y CU8—. Los dos se
reescribieron y los tres recibieron RF-20, RF-21 y RF-22 en el documento
de grado el 10/10/2026.

**De modelo a requisito.**

| Modelo | Requisitos | Modelo | Requisitos |
|---|---|---|---|
| MP-01 | RNF-03 | MP-13 | RF-20 |
| MP-02 | RNF-04 | MP-14 | RF-04, RF-17 |
| MP-03 | RNF-04 | MP-15 | RF-04, RF-06, RF-07 |
| MP-04 | — (riesgo P-07) | MP-16 | RNF-09 |
| MP-05 | RNF-05 | MP-17 | RF-14, RF-16 |
| MP-06 | — (capa 5 de seguridad) | MP-18 | RF-21 |
| MP-07 | RNF-03 | MP-19 | RF-06 |
| MP-08 | RNF-03 | MP-20 | RF-07 |
| MP-09 | RF-05 | MP-22 | RF-15, RF-18 |
| MP-10 | RF-03 | MP-23 | RF-01, RNF-12 |
| MP-11 | RF-05, RF-20 | MP-24 | RF-14, RF-15 |
| MP-12 | RF-05, RF-20 | MP-25 | RF-07 |
| MP-26 | RNF-07 | MP-27 | RNF-08 |
| MP-28 | RF-19 | | |

MP-04 y MP-06 no tienen requisito y se conservan: protegen de la fuga del
teléfono dentro del `wamid` y de la inyección de mensajes falsos, y los
justifican el riesgo y el modelo de seguridad de la Fase 3. Que la
Tabla 6 no los recoja es un hueco de la Tabla 6, no de la prueba.

**De requisito a prueba**, en todos los niveles.

| Requisito | Componente | Sistema y aceptación | Cobertura |
|---|---|---|---|
| RF-01 Texto y nota de voz | MP-23 | Aceptación: 9 notas de voz | **Parcial**: nada prueba el camino del audio |
| RF-02 Bloqueo sin consentimiento | — | `spike_despachador` 1 | Cubierto en sistema |
| RF-03 Saludo sin modelo | MP-10 | `spike_despachador` 2 | Cubierto |
| RF-04 Intención por function calling | MP-14, MP-15 | `spike_despachador` 3; enrutamiento 76 de 76 | Cubierto |
| RF-05 Barrio en catálogo cerrado | MP-09, MP-11, MP-12 | Evaluación formativa | **Parcial**: las variantes de escritura las resuelve el modelo, sin caso |
| RF-06 Extracción de especies | MP-15, MP-19 | `spike_despachador` 4; formativa 12 de 14 | **Parcial**: la extracción en sí no tiene modelo |
| RF-07 Jerarquía de fuentes | MP-15, MP-20, MP-25 | Banco de 40 preguntas | Cubierto |
| RF-14 Atribución | MP-17, MP-24 | Banco de 40 preguntas | Cubierto |
| RF-15 Sin cita bajo el umbral | MP-22, MP-24 | Preguntas de control del banco | **Parcial**: la rama por debajo del umbral no tiene modelo |
| RF-16 Qué siembran otras huertas | MP-17, MP-27 | `spike_despachador` 6; aceptación 12/10 | Cubierto |
| RF-17 Bienvenida | MP-10, MP-14 | `spike_despachador` 2 | Cubierto |
| RF-18 Ventana de diez mensajes | MP-22 | — | **Parcial**: solo se valida la configuración |
| RF-19 Acuse de la nota de voz | MP-28 | — | Cubierto |
| RF-20 Onboarding | MP-11, MP-12, MP-13 | Formativa: 14 de 16 | Cubierto |
| RF-21 Buscar un cultivo | MP-18 | Aceptación 12/10 | Cubierto |
| RF-22 Mi huerta | — | `spike_despachador` 7; aceptación 12/10 | Cubierto en sistema |
| RNF-01 Solo WhatsApp | — | Inspección | Verificado por inspección |
| RNF-03 Identidad por BSUID | MP-01, MP-07, MP-08 | `spike_despachador` 8 y 9 | Cubierto |
| RNF-04 Huella HMAC | MP-02, MP-03 | — | Cubierto |
| RNF-05 Nombre cifrado | MP-05 | — | Cubierto, **con la salvedad de INC-026**: el nombre queda también en claro en `mensaje` |
| RNF-07 Filtrado por usuario | MP-26 | — | Cubierto en componente: el SQL, no la base |
| RNF-08 Solo datos compartibles | MP-27 | — | Cubierto |
| RNF-09 Advertencia médica | MP-16 | Banco de 40 preguntas | Cubierto |
| RNF-12 Asíncrono | MP-23 | — | **Parcial**: el reintento ante la base caída (ADR-0019) no se prueba |

**Resultado, al 12/10/2026: de 24 requisitos, 17 cubiertos, 6 parciales
y 1 verificado por inspección. Ninguno queda sin cobertura.** RF-16 y
RF-21 dejaron de ser parciales al ejercerse en producción el CU4 y el CU7
(INC-027). Los tres que
lo estaban en la versión 1.5 —RNF-07, RNF-08 y RF-19— recibieron MP-26,
MP-27 y MP-28. RNF-07 queda cubierto **en componente**: se comprueba el
SQL que se manda, no lo que la base hace con él. Una comprobación de
sistema —una persona no ve la huerta de otra, contra la base real— lo
completaría, y queda como mejora, no como hueco.

## Trazabilidad hacia los casos de uso

| Caso de uso | Modelos que lo cubren en este nivel | Sistema | Aceptación |
|---|---|---|---|
| CU1 Consentimiento | MP-10 | `spike_despachador`, comprob. 1 y 2 | Sí, 17 participantes |
| CU2 Orientación | MP-15, MP-16, MP-17, MP-24 | Banco de 40 preguntas | Sí, 9 participantes |
| CU3 Registro | MP-19 | `spike_despachador`, comprob. 4 | Sí, 11 participantes |
| CU4 Comunidad | MP-17, MP-26, MP-27 | `spike_despachador`, comprob. 6 | Sí, 1 participante, el 12/10 |
| CU5 Ayuda | MP-10, MP-14 | `spike_despachador`, comprob. 2 | Sí, 1 participante |
| CU6 Onboarding | MP-11, MP-12, MP-13 | — | Sí, 15 de 17 lo completaron |
| CU7 Búsqueda por cultivo | MP-18, MP-27 | — | Sí, 1 participante, el 12/10 |
| CU8 Mi huerta | MP-14 | `spike_despachador`, comprob. 7 | Sí, 1 participante, el 12/10 |

**Los ocho casos de uso tienen aceptación con evidencia** desde el
12/10/2026, según el [registro de aceptación](registro-de-aceptacion.md),
reconstruido desde `mensaje` sin contenido de nadie. Hasta el 25/09 este
documento decía «los ocho» apoyado en la declaración del autor; al
reconstruirlo, ninguna participante había usado el CU4, el CU7 ni el CU8
(INC-027). El 12/10 los ejerció el autor desde su celular: **es evidencia
mínima**, que prueba que funcionan en producción, no que alguien los
encuentre por su cuenta.

Queda además una deuda de *tipo*, no de nivel: la aceptación demuestra que
los casos de uso **funcionan**, no que el CU2 **acierte**. Eso lo mide el
[banco de 40 preguntas](banco-de-preguntas.md).

---

# Parte 3 — Procedimientos de prueba (§8.4)

## PR-01 — Componente e integración

- **Objetivo**: ejecutar los 231 casos de los 27 modelos vigentes, de MP-01 a MP-28.
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
