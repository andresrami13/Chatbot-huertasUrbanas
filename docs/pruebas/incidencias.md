# Registro de incidencias

| | |
|---|---|
| **Identificador** | `INC-CHU-001`, versión 1.7 |
| **Emite** | Andrés Ramírez — autor del trabajo de grado |
| **Aprueba** | A. Ramírez — autor. **Única autoridad de aprobación** (desviación D-9) |
| **Estado** | Abierto, en actualización continua |
| **Fecha** | 23/09/2026 |

## Historial de cambios

| Fecha | Versión | Cambio | Autor |
|---|---|---|---|
| 23/09/2026 | 1.0 | Versión inicial con las tres incidencias del diseño de pruebas | A. Ramírez |
| 23/09/2026 | 1.1 | INC-004 tras la primera ejecución del humo de despliegue. Traslado de las catorce incidencias históricas (actividad A-7) y registro de las pruebas estáticas ya realizadas | A. Ramírez |
| 24/09/2026 | 1.2 | INC-019 del barrido del corpus, e INC-020 e INC-021 de la ejecución del banco de preguntas. Retirada de INC-011, que no era una incidencia | A. Ramírez |
| 24/09/2026 | 1.3 | INC-022 e INC-023, de refactorizar los scripts de prueba sobre un arnés común | A. Ramírez |
| 25/09/2026 | 1.4 | **Cerrada INC-004**: corregidas en `docs/ESTADO.md` las tres afirmaciones que desmentía, con el commit y los contadores verificados de nuevo contra el sistema. **Cero incidencias de severidad 1 o 2 abiertas** | A. Ramírez |
| 25/09/2026 | 1.5 | Repetición con top-k 4 y 5: **se reabre INC-021**, cerrada con una sola corrida, y nacen INC-024 —el romero sin advertencia— e INC-025 —el formulario que el agente no enruta—. Vuelve a haber dos de severidad 2 abiertas | A. Ramírez |
| 25/09/2026 | 1.6 | INC-026 e INC-027, de reconstruir el registro de aceptación (A-14) | A. Ramírez |
| 26/09/2026 | 1.7 | INC-026 reclasificada a severidad 3 y aceptada por escrito por el autor. Banco de 40 preguntas en las medidas | A. Ramírez |

## Introducción

Registro de incidencias conforme a ISO/IEC/IEEE 29119-3:2021 §8.11. Una
incidencia por cada hecho anómalo que requiera investigación, con los ocho
campos obligatorios.

Sustituye al seguimiento en GitHub Projects que preveía el anteproyecto
(desviación D-8 de la [política](politica-y-practicas-de-prueba.md)).

**Las incidencias no se levantan solo contra el producto.** El §8.11.5 de
la norma admite levantarlas también contra los procedimientos de prueba,
la base de prueba o el entorno. En este registro las hay de los tres
tipos, y conviene no confundirlas al contar.

## Alcance

Cubre desde el 30/07/2026 —la primera incidencia documentada del
proyecto— hasta hoy. Las anteriores al 23/09/2026 **se detectaron antes
de que existiera este proceso de prueba** y estaban documentadas en
`docs/adr/` y en `docs/ESTADO.md`; aquí se trasladan a formato normalizado
sin reescribir la historia: la fecha y la causa son las que quedaron
registradas entonces.

## Referencias

- [Política y prácticas de prueba](politica-y-practicas-de-prueba.md)
- [Plan de pruebas](plan-de-pruebas.md) — registro de riesgos
- [Especificación de pruebas](especificacion-de-pruebas.md)
- [`docs/adr/`](../adr/) y [`docs/ESTADO.md`](../ESTADO.md)

## Glosario

**Severidad**: impacto si ocurre. **Prioridad**: urgencia de la corrección.
Cuatro niveles cada una, 1 el más grave.

| Severidad | Significado en este proyecto |
|---|---|
| 1 | La usuaria no recibe respuesta, recibe un dato falso sobre salud, o se filtra un dato personal |
| 2 | Un caso de uso queda inservible, o una medición del trabajo de grado queda invalidada |
| 3 | Molestia para la usuaria, o pérdida de calidad sin daño |
| 4 | Cosmético, o interno sin efecto visible |

---

# 1. Incidencias abiertas

Son ocho. Las de severidad 1 y 2 tienen que quedar resueltas o aceptadas
por escrito antes de dar la Fase 7 por cerrada (criterio de terminación 2
del [plan](plan-de-pruebas.md) §6.6).

## INC-010 — Dos defectos de extracción en *Sembrando Biodiversidad*

| Campo | Contenido |
|---|---|
| **Detectada** | 15/08/2026 |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: el corpus oficial. Fuente `jbb_sembrando_2023`. Prueba estática de inventario |
| **Descripción** | Los **rótulos al margen se cuelan dentro de la frase** en unas 17 páginas, y **cinco páginas con texto rotado** que `pypdf` no extrae. Documentado en el ADR-0014, sección «Lo que este ADR no resuelve» |
| **Severidad** | 3 |
| **Prioridad** | 3 |
| **Riesgo** | Un fragmento con el rótulo incrustado puede recuperarse y llegar a la usuaria con una frase rota. Las cinco páginas perdidas son corpus que no está |
| **Estado** | **Abierta.** Aceptada conscientemente al ingerir |

## INC-017 — Un mensaje que mezcla consulta y dato ofrece guardar lo consultado

| Campo | Contenido |
|---|---|
| **Detectada** | 15/08/2026, en la prueba con celular |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: `app/services/extraccion.py` y el despachador. Nivel de sistema |
| **Descripción** | El agente enruta bien las dos intenciones, pero **la extracción corre sobre el mensaje entero**, así que «mi tomate tiene bichos» acaba ofreciendo guardar tomate. El ADR-0008 lo daba por «cosa del agente» y no lo era |
| **Severidad** | 3 |
| **Prioridad** | 3 |
| **Riesgo** | La confirmación previa a guardar lo contiene: ella ve el resumen y puede descartar. Queda como molestia, no como dato falso |
| **Estado** | **Abierta y aplazada por decisión del autor el 24/09/2026.** Se corrige más adelante. Al ser de severidad 3 no bloquea el criterio de terminación 2, y esta línea **es** la aceptación por escrito que ese criterio exige |

## INC-018 — La advertencia médica se dispara donde no toca

| Campo | Contenido |
|---|---|
| **Detectada** | 17/08/2026, observada en producción |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: `orientacion._con_advertencia_medica`. Modelo MP-16 |
| **Descripción** | Se disparó con una consulta de plagas —«bichitos verdes»—, que no es de salud. El vocabulario tira a ancho a propósito (ADR-0015) |
| **Severidad** | 4 |
| **Prioridad** | 4 |
| **Riesgo** | Advertir de más cuesta dos renglones y cansa; advertir de menos falla justo en el mensaje en que importaba. **Puede ser el comportamiento buscado o puede ser demasiado ancho: hace falta medirlo, no decidirlo de memoria.** Es una de las salidas del banco de 20 preguntas |
| **Estado** | **Abierta** |

## INC-021 — Una cifra agronómica que no está en ninguna fuente

| Campo | Contenido |
|---|---|
| **Detectada** | 24/09/2026, al calificar D-06 del banco leyendo los fragmentos |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: redacción del CU2 con respaldo. Criterio de **precisión** |
| **Descripción** | La respuesta sobre cuándo trasplantar dice «de **2 a 4** hojas verdaderas». El fragmento del que sale dice «de **3 a 4**»; otros dicen «de **3 a 5**» y «**dos o tres**»; **el «2 a 4» no está en ninguna**. Todo lo demás de esa respuesta sí se comprobó textual, incluidas las horas y el «5 a 20 cm en un plazo de 4 a 5 semanas» |
| **Severidad** | **2** |
| **Prioridad** | 2 |
| **Riesgo** | Es el fallo más difícil de ver: la respuesta es correcta en lo demás, va citada y suena bien. Una cifra inventada **bajo una cita oficial** es exactamente lo que la jerarquía de fuentes promete que no pasa. Una sola en veinte, y el umbral de precisión se fijó en 20 de 20 justo por esto |
| **Estado** | **Reabierta el 25/09/2026.** Se había cerrado el 24/09 con la regla 9 del `redaccion_rag_v2.md` —no fundir cifras de fragmentos distintos— **y una sola corrida**, la afortunada. Repitiendo tres veces con top-k 4 y tres con 5, D-06 vuelve a decir «2 a 4» en **5 de 6**. La regla de prompt no basta |

## INC-024 — El romero respondió usos medicinales sin advertencia médica

| Campo | Contenido |
|---|---|
| **Detectada** | 25/09/2026, en el banco completo con top-k 5 |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: `orientacion._HABLA_DE_SALUD`. Modelo MP-16. Riesgo P-01 |
| **Descripción** | D-03, «¿Para qué sirve el romero?», respondió *«En la salud, sus aceites relajan los músculos y alivian dolores de cabeza, dolores articulares […] cicatrizar heridas, tratar problemas del estómago y aliviar males respiratorios como asma, bronquitis»* **sin la advertencia**. El vocabulario busca `dolor de` y no `dolores de`, `cicatrizante` y no `cicatrizar`, `para la salud` y no `en la salud`, y no tiene `asma`, `bronquitis` ni `respiratori`. La misma pregunta llevó advertencia en las otras 6 corridas: depende de cómo redacte el modelo |
| **Severidad** | **2** |
| **Prioridad** | 1 |
| **Riesgo** | Viola una decisión no negociable, el `CLAUDE.md` §4.6: toda respuesta del CU2 que hable de salud lleva advertencia. Y la viola justo en la pregunta elegida para comprobarla. El vocabulario se amplió «a lo ancho» a propósito (ADR-0015) y aun así tiene huecos: la lista mira palabras, y el modelo conjuga |
| **Estado** | **Abierta.** Corregirlo es ampliar el vocabulario —formas conjugadas y dolencias respiratorias—, con el coste conocido de INC-018: más falsos positivos |

## INC-025 — El agente contesta sin consultar la guía una pregunta que la guía responde

| Campo | Contenido |
|---|---|
| **Detectada** | 25/09/2026, al medir el top-k (ADR-0026) |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: enrutamiento del agente, `agente_v2.md` (ADR-0013) |
| **Descripción** | La consulta real «Cual es la dirección de enlace al JBB para obtener el formulario» tiene respuesta en el corpus —los enlaces del Protocolo de espacio público—, y el agente **no llama al CU2**: contesta por su cuenta «No tengo el enlace ni los formularios del Jardín Botánico». Comprobado envolviendo `agente.consultar_orientacion`, que no se invoca en ninguna de las corridas |
| **Severidad** | 3 |
| **Prioridad** | 3 |
| **Riesgo** | Ella se queda sin un dato que el sistema tiene. Y **nada lo delata**: la respuesta es plausible y educada. Además invalida una forma de medir: el fragmento se había medido en el puesto 5 con la consulta suelta, fuera del agente, y de ahí salió la idea de subir el top-k |
| **Estado** | **Abierta** |

## INC-026 — El nombre de pila queda en claro en `mensaje`

| Campo | Contenido |
|---|---|
| **Detectada** | 25/09/2026, al reconstruir el registro de aceptación (A-14) |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: `dispatcher.procesar_evento` y `onboarding`. Fase 3 §5, capa 3. ADR-0012 y ADR-0016 |
| **Descripción** | El despachador guarda cada mensaje de ella **antes** de pasarlo al onboarding (`recordar_usuaria`). Su respuesta a «¿cómo se llama usted?» queda así en `mensaje.contenido` **en claro**, mientras en `usuario.nombre_usuario_cifrado` va cifrada con AES-GCM. El agente la lee de la ventana de memoria y la repite en respuestas que también se guardan: se observó al menos una |
| **Severidad** | 3 —era 2 hasta el 26/09/2026— |
| **Prioridad** | 4 |
| **Riesgo** | Anula la capa 3 del modelo de seguridad para el nombre: quien lea la base lo tiene, cifrado o no. No se expone a otras usuarias —`mensaje` se filtra por `usuario_id` y el CU4 no lo lee—, pero **el ADR-0016 dejó el saludo personalizado fuera de la memoria justo para que el nombre no estuviera en `mensaje`**, y la premisa no se cumple. El ADR-0012 dice que la minimización gobierna lo que el sistema pide; aquí **el sistema lo pide** |
| **Estado** | **Abierta y aceptada por escrito por el autor el 26/09/2026**, que la reclasifica de severidad 2 a 3. Motivo: las usuarias autorizaron el tratamiento de su nombre al dar el consentimiento (Ley 1581 de 2012), así que conocerlo y guardarlo tiene base legal, y no se expone a otras usuarias. **Riesgo que se asume**: el cifrado del nombre en `usuario` no lo protege frente a quien lea la base, y el documento de grado no puede presentar la capa 3 como si lo hiciera. La corrección —no recordar la respuesta del paso del nombre— queda para después |

## INC-027 — CU4, CU7 y CU8 no tienen evidencia de aceptación

| Campo | Contenido |
|---|---|
| **Detectada** | 25/09/2026, al reconstruir el registro de aceptación (A-14) |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: **la base de prueba**. La especificación, el plan y `ESTADO.md` afirmaban «los ocho casos de uso han pasado por aceptación» |
| **Descripción** | En `mensaje` —273 mensajes de 12 participantes, del 09 al 25/09— no hay ninguna respuesta del listado del CU4, de la búsqueda del CU7 ni de «mi huerta» del CU8, **ni ninguna pregunta de ellas con esa intención**. La afirmación se apoyaba en la declaración del autor, no en la base. Si se probaron desde una fila después borrada, la evidencia se perdió por cascada |
| **Severidad** | **2** |
| **Prioridad** | 2 |
| **Riesgo** | Invalida una medición del trabajo de grado: la cobertura de la aceptación. Y el CU7 queda sin prueba de punta a punta de ninguna clase: solo tiene casos de componente |
| **Estado** | **Abierta.** Se cierra con tres preguntas desde un celular real y regenerando el registro |

---

# 2. Incidencias cerradas

## INC-004 — `docs/ESTADO.md` describe un estado de despliegue que no es el real

| Campo | Contenido |
|---|---|
| **Detectada** | 23/09/2026, durante la primera ejecución de `PR-03`. **Cerrada el 25/09/2026** |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: **la base de prueba**. `docs/ESTADO.md`, secciones «Infraestructura operativa» y «Por dónde seguir». Nivel de instalabilidad |
| **Descripción** | El documento afirmaba tres cosas que la comprobación desmentía: que **la migración `009` estaba sin correr** —existe la tabla `listado_comunitario_pendiente`—, que **la `010` tampoco** —existe la columna `usuario.identidad_hash`— y que `origin/main` estaba al día en un commit viejo. Comprobado contra `/health` y contra `information_schema` |
| **Severidad** | 2 |
| **Prioridad** | 2 |
| **Riesgo** | Alto y ya materializado dentro del propio proceso de prueba: el [plan](plan-de-pruebas.md) se redactó el 23/09/2026 apoyándose en este documento y **heredó los tres errores**, incluida la afirmación de que «hoy hay gente que escribe y no recibe nada». Hubo que corregirlo |
| **Estado** | **Cerrada el 25/09/2026.** Las tres afirmaciones se corrigieron en `docs/ESTADO.md`, con los contadores de infraestructura y el commit desplegado (`e7a5ec9`) verificados de nuevo contra el sistema, no copiados a mano |

**Lo que esto obliga a cambiar en el proceso, y ya quedó dicho ahí.** Antes
de planificar sobre el estado del despliegue hay que **consultarlo**, no
leerlo. Para eso está `python -m scripts.humo_despliegue`, que responde en
dos segundos y sin gastar un mensaje de WhatsApp. El propio `ESTADO.md`
ahora se lo recuerda a quien vuelva a editarlo a mano.

## Del trabajo del 24/09/2026

## INC-009 — Basura de extracción en el catálogo de plantas

| Campo | Contenido |
|---|---|
| **Detectada** | 19/08/2026 |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: el corpus oficial. Fuente `jbb_catalogo_plantas` |
| **Descripción** | Un fragmento contiene la cadena `ENREDADERA KJBNVBJNBHJ BHJ Gulupa`, basura de la extracción del PDF |
| **Severidad** | 3 |
| **Prioridad** | 3 |
| **Riesgo** | El fragmento es recuperable y puede llegar a la usuaria. Limitado a una ficha |
| **Estado** | **Cerrada el 24/09/2026** junto con INC-019, que la absorbe: eran 15 apariciones y no una |

## INC-019 — Caracteres de extracción defectuosa repartidos por el corpus

| Campo | Contenido |
|---|---|
| **Detectada** | 24/09/2026, en el barrido de inventario sobre los 765 fragmentos |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: el corpus oficial en Supabase. Prueba estática de inventario exhaustivo |
| **Descripción** | Inventario completo de caracteres fuera de lo corriente del español sobre los 765 fragmentos. **Basura real: `U+0093` × 101** —viñeta de fuente simbólica mal decodificada, aparece como `U+0093U+0093 ` o `U+0093y ` delante de cada ítem de lista—, **`U+F0B7` × 19** —otra viñeta simbólica, zona de uso privado—, **`KJBNVBJNBHJ` × 15** en el catálogo de plantas —no una vez, como estaba registrado—, **acento combinante suelto × 5** —donde iba una letra griega: `́-pineno` por `α-pineno`— y **`U+FFFC` × 1**. En total **36 fragmentos afectados de 765**: catálogo de plantas 17, cartilla de fertilización 15, *Sembrando biodiversidad* 2, manual de la FAO 1 y protocolo de espacio público 1 |
| **Comprobado y legítimo** | Lo que el inventario descartó, y por qué importa que se mirara: las 74 rachas de consonantes son nombres científicos —*Symphytum*, *Dysphania*, *Phyllosticta*, *Cryptosporidium*—; las 514 viñetas tipográficas (`•`, `○`, `⚫`, `∙`) son viñetas de verdad; y `ã ç å ä ö õ ć` son apellidos de las bibliografías —Ação, Produção, Spångberg, Länger, Jönsson, Lazarević—. **Ninguno es defecto** |
| **Severidad** | 3 |
| **Prioridad** | 2 |
| **Riesgo** | Un fragmento con basura puede recuperarse y llegar a la usuaria. Los 101 `U+0093` no se ven como error evidente pero ensucian el texto que lee el modelo. **Limpiarlos obliga a revectorizar el fragmento**, porque texto y vector tienen que corresponder, y eso mueve su similitud: hay que remedir contra la línea base del [banco de preguntas](banco-de-preguntas.md) antes y después. **Solo hay que tocar 36 fragmentos, no los 765** |
| **Estado** | **Cerrada el 24/09/2026.** Corregida con `scripts/limpiar_corpus.py`: 36 fragmentos reparados y revectorizados, en una transacción. Inventario posterior: **cero apariciones**. El banco de preguntas se ejecutó antes y después y **21 de 24 similitudes son idénticas**; las tres que se movieron lo hicieron como mucho una centésima y **ninguna cruzó el umbral**. El riesgo que esta incidencia declaraba no se materializó, y ahora está medido |

## INC-016 — El evento `calls` está suscrito y nadie lo atiende

| Campo | Contenido |
|---|---|
| **Detectada** | 16/09/2026, en la revisión del webhook (prueba estática) |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: `app/api/webhook.py` y la configuración de la app en Meta |
| **Descripción** | El campo `calls` está suscrito en el WABA y el código no atiende ese evento. Si alguien **llama** al número en vez de escribir, no pasa nada: ni respuesta ni rastro en la bitácora |
| **Severidad** | 3 |
| **Prioridad** | 3 |
| **Riesgo** | Una usuaria que llame se queda sin nada y sin saber por qué. El perfil del proyecto —adultas mayores acostumbradas a llamar— hace esto más probable de lo que parece |
| **Estado** | **Cerrada el 24/09/2026**, declarado corregido por el autor. **Pendiente de comprobación**: no hay prueba registrada que lo confirme, y la corrección es de configuración en Meta, así que no deja rastro en el repositorio. Basta con llamar al número una vez y anotar el resultado |

## INC-020 — El CU2 dice que no tiene la información y cita la fuente igual

| Campo | Contenido |
|---|---|
| **Detectada** | 24/09/2026, en la ejecución del [banco de veinte preguntas](banco-de-preguntas.md) |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: `app/services/orientacion.py`, camino con respaldo. Modelos MP-15 y MP-16 |
| **Descripción** | **Seis de veinte respuestas** dicen a la usuaria que no tienen esa información y a continuación le adjuntan `Fuente: Jardín Botánico de Bogotá José Celestino Mutis`. Son R-05, R-06, R-07, R-09 y R-10 del banco, más C-02 de las de control. Las seis superan el umbral —entre 0.6633 y 0.7001—, así que el código entra por el camino con respaldo y pone la cita; pero el fragmento recuperado no responde la pregunta y el modelo, bien instruido, lo dice. **La cita la escribe el modelo**, obedeciendo la regla 4 de `redaccion_rag_v1.md` —«termine siempre citando la fuente»—, que choca con la regla 2 del mismo prompt —«si el contexto no alcanza, dígalo»—. El modelo cumple las dos a la vez y sale la contradicción |
| **Severidad** | **2** |
| **Prioridad** | 1 |
| **Riesgo** | Atribuir a una fuente oficial una no-respuesta es atribuirle algo que no dijo, y eso ataca la jerarquía de fuentes de `CLAUDE.md` §6, que es la base de que ella pueda distinguir de dónde viene cada cosa. Una usuaria puede concluir que el Jardín Botánico **desaconseja** lo que preguntó, cuando lo cierto es que el corpus no habla de eso |
| **Estado** | **Cerrada el 24/09/2026** con el ADR-0025: la línea de la fuente la pone ahora el backend y el modelo solo declara que no pudo responder. **Medido con el banco: de 6 de 20 a 0 de 20.** Las dos respuestas que declinan algo y siguen citando —R-03 y R-08— son parciales de la regla 3: responden con el contexto y avisan de lo que les falta, así que la cita es correcta |

**Es una violación de un principio que el diseño ya tenía escrito.** El
encabezado de `orientacion.py` dice: «o se responde con la guía y se cita
**toda** la respuesta, o responde el modelo y **no se cita absolutamente
nada**, nunca medio mensaje de cada, y **el camino lo elige el código**».
Aquí el código eligió «con respaldo» mirando la similitud, y el modelo
produjo de hecho una respuesta sin respaldo. Los dos creen estar en caminos
distintos.

**Y estaba anunciado.** El comentario de `RAG_UMBRAL_SIMILITUD` en
`app/config.py` describe este modo de fallo con estas palabras: «consultas
que pasan el filtro, no encuentran nada útil y responden "no tengo la
información sobre eso" con `Fuente: Jardín Botánico` al pie». Se dio por
mitigado al quitar los índices del corpus. **No lo estaba**: sigue en 6 de
20.

**Resuelta el mismo día con el ADR-0025.** El modelo declara con una marca
interna que no pudo responder, y la línea de la fuente la pone el backend
con la entidad sacada de la tabla `fuente` por la clave foránea. Es el mismo
reparto del ADR-0015 con la advertencia médica: el modelo decide cuándo, el
backend decide qué texto sale.

## INC-022 — La comprobación del enrutamiento al CU2 usaba la cita como prueba

| Campo | Contenido |
|---|---|
| **Detectada** | 24/09/2026, al correr `spike_despachador` después del ADR-0025 |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: **el caso de prueba**, no el producto. `scripts/spike_despachador.py`, comprobación «el agente la enrutó al CU2» |
| **Descripción** | La comprobación afirmaba el **enrutamiento** y lo verificaba buscando `Fuente:` en la respuesta, que hasta el ADR-0025 salía en toda respuesta con respaldo. Al dejar de citarse las respuestas que declinan, empezó a **fallar con el producto correcto**: el agente sí había enrutado al CU2 y la respuesta no llevaba cita porque el fragmento no respondía |
| **Severidad** | 3 |
| **Prioridad** | 2 |
| **Riesgo** | Un falso fallo cansa y se acaba ignorando, y entonces deja de avisar cuando el fallo es de verdad. El indicador medía un efecto lateral en vez de lo que decía medir |
| **Estado** | **Cerrada el 24/09/2026.** Ahora se envuelve `agente.consultar_orientacion` y se anota la llamada: se comprueba el enrutamiento mirando el enrutamiento. Con eso, 34 de 34 |

**La lección ya estaba en `CLAUDE.md` §12** —«un buen indicador puede estar
midiendo lo que no es»— y esta vez le tocó a una prueba, no a una medición.

## INC-023 — El spike llamaba a la API de Meta en cada ejecución

| Campo | Contenido |
|---|---|
| **Detectada** | 24/09/2026, al escribir `ejecutar_banco` y tropezar con el mismo error 400 |
| **Origen** | A. Ramírez, autor |
| **Contexto** | Ítem: **el entorno de prueba**. `scripts/spike_despachador.py` |
| **Descripción** | El spike decía en su encabezado «no envía nada por WhatsApp» y sustituía por espías los **tres** módulos que envían mensajes. Pero son cuatro los puntos por los que se sale a Meta: `whatsapp.marcar_escribiendo`, el de los tres puntitos, **no estaba sustituido**, así que cada ejecución llamaba de verdad a la API con un `wamid` inventado que Meta rechazaba con `(#131009) Parameter value is not valid` |
| **Severidad** | 3 |
| **Prioridad** | 3 |
| **Riesgo** | Ninguna usuaria recibió nada —el indicador de escritura no es un mensaje—, pero **el encabezado del script afirmaba algo falso**, y una prueba que toca un servicio externo sin decirlo no es repetible: depende de que el token valga y de que Meta responda |
| **Estado** | **Cerrada el 24/09/2026.** Los cuatro puntos se sustituyen ahora en `scripts/arnes.py`, que es el sitio único |


## Del diseño de pruebas, 23/09/2026

Las tres se detectaron en la primera ejecución de `PR-01` y **ninguna era
del producto**: eran defectos de los casos de prueba.

| ID | Contexto | Descripción | Sev | Pri | Riesgo | Estado |
|---|---|---|---|---|---|---|
| **INC-001** | Caso de prueba. `tests/test_conversacion.py`, MP-11 | El caso esperaba que `leer_numero("-1", 5)` diera `None`. Da `1`: la normalización quita la puntuación antes de leer el dígito, y **es el comportamiento correcto**, además de conveniente porque mucha gente numera escribiendo «1.» | 4 | 3 | Ninguno nuevo. De haberse aceptado como fallo del producto, se habría «corregido» una función que funciona bien | Cerrada: se corrigió el caso y el comportamiento quedó fijado |
| **INC-002** | Caso de prueba. `tests/test_conversacion.py`, MP-13 | El caso usaba un nombre de **cinco** palabras contra un máximo de cuatro. Error al elegir el dato de prueba | 4 | 3 | Ninguno | Cerrada: se cambió el dato y se añadió un caso de valor límite |
| **INC-003** | Caso de prueba. `tests/test_agente_y_respuesta.py`, MP-16 | El caso exigía idempotencia a `_con_advertencia_medica`. No la tiene, y **no la necesita**: los dos puntos de llamada están en ramas mutuamente excluyentes, verificado en el código | 4 | 4 | Bajo, pero anotado: si se añadiera un tercer camino al CU2, la advertencia se apilaría. El comentario dejado en el código es el aviso | Cerrada: se retiró el caso y se dejó la constancia |

## Históricas, trasladadas desde los ADR y `docs/ESTADO.md`

| ID | Fecha | Contexto | Descripción | Sev | Pri | Riesgo | Estado |
|---|---|---|---|---|---|---|---|
| **INC-005** | 30/07/2026 | Producto. Bitácora y esquema | El **`wamid` lleva el teléfono dentro** en ASCII, recuperable con un `base64 -d`, y se estaba registrando y almacenando en claro | **1** | 1 | Fuga de dato personal. Ley 1581 de 2012 | **Cerrada** del todo el 15/08/2026 con la migración `006`: no queda ninguna columna `wamid` en el esquema (ADR-0012) |
| **INC-006** | 17/08/2026 | Producto. CU2, en producción | El CU2 **citó una fuente sin contenido que la sustentara**, con el umbral en 0.68 y una similitud de 0.7232. El modo de fallo no aparecía solo al bajar el umbral | 2 | 2 | Atribuirle a una fuente oficial algo que no dice | **Cerrada**: el umbral pasó a decidir citar o no citar, no responder o callar (ADR-0015, ADR-0020) |
| **INC-007** | 17/08/2026 | Producto. Desambiguación del barrio | El **rótulo de un botón de WhatsApp admite 20 caracteres** y el **24 %** de los barrios de Bosa pasa de ahí | 2 | 2 | Con 313 barrios, una de cada cuatro opciones habría salido cortada o ambigua | **Cerrada**: se descartaron los botones y se pasó a una lista numerada dentro del cuerpo, que admite 1024 (ADR-0016) |
| **INC-008** | 19/08/2026 | Producto. Corpus oficial | **Diez renglones de índice** contaminaban el corpus y desplazaban fragmentos útiles en la recuperación | 2 | 2 | Respuestas del CU2 apoyadas en un índice en vez de en contenido | **Cerrada**: se limpiaron y el umbral bajó a 0.66 (ADR-0020). Quedó una lección: el «25 % de consultas mejoran» con que se anunció contaba consultas cuya recuperación cambió, no respuestas mejores |
| **INC-012** | 08/09/2026 | Base de prueba y configuración | **Tres valores distintos del modelo generativo**: los documentos decían `gemini-3.5-flash-lite`, `config.py` decía `gemini-3.6-flash` y Railway corría `gemini-2.5-flash` | 2 | 1 | Se midió el enrutamiento del agente **contra dos modelos que no eran producción**, y la medición no valía | **Cerrada**: manda la variable de Railway, todo lo demás la copia, y `/health` informa el modelo desde ese día |
| **INC-013** | 08/09/2026 | Producto. Agente | `gemini-2.5-flash` **no llamaba a ninguna herramienta** en 26 de 76 casos —`"hola"` incluido, 4 de 4—, y entonces se enviaba el texto del modelo **saltándose el CU2 entero**: sin RAG, sin cita y sin advertencia médica | **1** | 1 | Es la vía por la que una respuesta sobre salud podía salir sin advertencia | **Cerrada**: con el modelo actual, 76 de 76 correctos |
| **INC-014** | 09/09/2026 | Producto. CU8 | Al preguntar «qué tengo sembrado», el agente **no llamaba a nada** y respondía de memoria, nombrando **solo el último cultivo** | 2 | 2 | Dato falso sobre su propia huerta, y de los que ella sí puede detectar | **Cerrada**: se añadió el CU8 y la quinta herramienta (ADR-0022) |
| **INC-015** | 15/09/2026 | Producto. Identidad | **Ocho mensajes de unos setenta sin respuesta ninguna**: Meta deja de mandar el número en cuanto la usuaria activa su nombre de usuario de WhatsApp, y el sistema identificaba por teléfono | **1** | 1 | Riesgo P-02. Los ocho mensajes quedaron marcados `procesado`, así que **ni un reintento de Meta los recuperaría**: no vuelven | **Cerrada del todo el 23/09/2026.** Identidad por BSUID desplegada en `7b136e7`, migración `010` corrida, 11 casos de componente y **aceptación en celulares reales**. La base registra 135 respuestas del asistente y actividad continua hasta el 23/09 |

---

# 3. Pruebas estáticas realizadas

Las pruebas estáticas de este proyecto son anteriores al proceso
formalizado y no estaban registradas como pruebas. Se dejan aquí porque
son, con diferencia, las que más defectos han encontrado.

| Fecha | Ítem examinado | Técnica | Hallazgo |
|---|---|---|---|
| Continuo | Documentos de fase frente a la implementación | Revisión técnica | **Veinte correcciones declaradas** en `docs/correcciones-a-los-documentos.md` y veinticuatro ADR |
| 30/07/2026 | Un `wamid` real | Inspección | El teléfono dentro, en base64 (INC-005) |
| 15/08/2026 | *Sembrando Biodiversidad*, texto extraído | Inventario | Rótulos al margen y páginas rotadas (INC-010) |
| 19/08/2026 | Catálogo de plantas, texto extraído | Inventario | `ENREDADERA KJBNVBJNBHJ` (INC-009) |
| 19/08/2026 | Corpus completo | Inspección | Diez renglones de índice (INC-008) |
| Sin fecha | Protocolo de espacio público, texto extraído | **Inventario exhaustivo de caracteres** | Buscar caracteres raros encontró **tres de ocho**; arreglados esos tres el texto ya *parecía* correcto y seguía diciendo «a travØs». Solo el inventario completo destapó el resto |
| 08/09/2026 | `scripts/`, uso real | Revisión | Nueve scripts sin uso, 1.798 líneas, **tres de ellos rotos desde hacía meses** sin que nadie lo supiera |
| 16/09/2026 | `app/api/webhook.py` y la suscripción en Meta | Revisión | El evento `calls` sin atender (INC-016) |
| 23/09/2026 | `docs/ESTADO.md` frente al despliegue | Revisión contra `/health` e `information_schema` | Tres afirmaciones falsas (INC-004) |

**La lección del Protocolo de espacio público merece quedar como práctica
y ya está en la política §4.5:** para buscar defectos en un texto
extraído, **inventaríe; no busque sospechosos**. Un texto que «parece
correcto» después de arreglar lo que se encontró buscando es exactamente
el estado en el que quedan los defectos que no se buscaron.

---

# 4. Medidas

| Métrica | Valor al 26/09/2026 |
|---|---|
| Incidencias registradas | 26 —de INC-001 a INC-027; la INC-011 se retiró porque no era una incidencia— |
| Abiertas | 8 |
| **Abiertas de severidad 1 o 2** | **3** (INC-021, INC-024, INC-027) |
| Cerradas | 18 |
| Contra el producto | 18 |
| Contra los casos de prueba | 4 (INC-001 a INC-003, INC-022) |
| **Contra la base de prueba** | **3** (INC-004, INC-012, INC-027) |
| Contra el entorno de prueba | 1 (INC-023) |
| Casos de componente e integración ejecutados | **231 de 231**, todos en verde |
| Comprobaciones de instalabilidad | 4 de 4 |
| Casos de uso con aceptación con evidencia | **5 de 8** —declarados 8 por el autor— (INC-027) |
| Casos de uso con aceptación **registrada** conforme a §8.9 y §8.10 | **8 de 8** registrados, 5 con resultado «pasa» ([registro](registro-de-aceptacion.md)) |
| Banco de preguntas | **40 preguntas, dos rondas: 29 y 30 de 40, el 74 %**. Estable en 37 de 40 |
| Fuentes del corpus con regresión comprobada | **6 de 9**: `jbb_practicas_2022` el 23/09 y las cinco tocadas por la limpieza el 24/09, todas con su recuento de origen |
| **Defectos de severidad 1 encontrados por una prueba** | **0** |
| **Defectos de severidad 1 encontrados por el uso** | **3** (INC-005, INC-013, INC-015) |

## Lectura honesta de estos números

Las dos últimas filas son el dato que de verdad mide el valor de la prueba
en este proyecto (política §2.8), y dicen algo incómodo: **los tres
defectos más graves los encontró el uso, no la prueba.** El `wamid` con el
teléfono dentro lo destapó una inspección casual; que el modelo dejara de
llamar a las herramientas se supo al medir el enrutamiento por otra razón;
y los ocho mensajes perdidos los descubrió el silencio de ocho personas.

Que los 231 casos escritos hoy pasen todos **no significa que el producto
esté bien**: significa que cubren código que ya llevaba meses
ejercitándose con nueve usuarias reales. La red de seguridad sirve para lo
que venga, no para validar lo que ya pasó, y así conviene presentarla en
el documento de grado.

Lo segundo que dicen estos números es que **las pruebas estáticas son las
que más han rendido** en este proyecto, y son las que el plan original ni
siquiera mencionaba.
