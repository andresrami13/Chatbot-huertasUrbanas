# Banco de veinte preguntas agroecológicas

| | |
|---|---|
| **Identificador** | `BPA-CHU-001`, versión 3.0 |
| **Emite** | Andrés Ramírez — autor del trabajo de grado |
| **Aprueba** | A. Ramírez — autor. **Única autoridad de aprobación** (desviación D-9) |
| **Estado** | **Ejecutado el 24/09/2026, tres veces.** Tras el ADR-0025 pasan tres de los cuatro criterios; falta la pertinencia. Ver el §7 |
| **Fecha** | 24/09/2026 |

## Historial de cambios

| Fecha | Versión | Cambio | Autor |
|---|---|---|---|
| 24/09/2026 | 1.0 | Versión inicial: 10 preguntas reales y 10 derivadas del corpus, todas medidas | A. Ramírez |
| 24/09/2026 | 2.0 | **Ejecución completa y calificación.** Cuatro preguntas de control añadidas, transcripción literal corregida en R-04 y R-09, y corrección del §3.1, que afirmaba algo falso sobre el corpus | A. Ramírez |
| 24/09/2026 | 2.1 | Segunda ejecución tras limpiar el corpus (INC-019) y comparación de las dos (§6) | A. Ramírez |
| 24/09/2026 | 3.0 | Tercera ejecución, tras corregir INC-020 e INC-021 con el ADR-0025. Nueva calificación (§7) | A. Ramírez |

## Introducción

Es el **banco de veinte preguntas predefinidas sobre temáticas
agroecológicas** que el anteproyecto compromete en su §6.1.7 y en la
descripción de la Fase 7, valorando «criterios de precisión, pertinencia y
coherencia». Es el **criterio de terminación 5** del
[plan de pruebas](plan-de-pruebas.md) §6.6.

Mide una cosa que la aceptación **no** mide: la aceptación demostró que
los ocho casos de uso funcionan; esto mide si el CU2 **acierta**.

## Alcance

Solo el CU2, orientación agroecológica. No cubre el resto de casos de uso
ni la usabilidad.

## Referencias

- [Plan de pruebas](plan-de-pruebas.md), criterio de terminación 5
- [Especificación de pruebas](especificacion-de-pruebas.md), modelos MP-15 a MP-17
- [Registro de incidencias](incidencias.md), INC-018, INC-020 e INC-021
- `scripts/ejecutar_banco.py` — la ejecución
- Tabla `mensaje` de Supabase, 09 al 23/09/2026

---

# 1. Cómo se construyó

## 1.1 Las diez reales

Se leyeron los **123 mensajes de usuaria** registrados entre el 09 y el
23/09/2026. De ellos, **19 son consultas agroecológicas**; el resto son
onboarding, confirmaciones, saludos y listas de cultivos.

Las 19 se midieron contra el corpus **con las funciones de producción**
—`vectorizar_consulta` y `buscar_fragmentos_oficiales`, mismo modelo de
embeddings, mismo top-k—: **15 superan el umbral de 0.66 y 4 no.** De las
15 se eligieron 10, descartando las ambiguas fuera de contexto
(«como hago para que sea mejor»).

**Van transcritas literalmente, con sus muletillas y sus errores.** No se
limpian, y es deliberado: así habla la gente por nota de voz, la
transcripción es literal, y la similitud medida corresponde a ese texto
exacto. Limpiarlas cambiaría la consulta y anularía la medición. El texto
vive en `scripts/ejecutar_banco.py` y no en esta tabla, para que lo que se
ejecuta y lo que se documenta no puedan separarse.

> **Esto ya falló una vez, dentro de esta misma prueba.** En la versión 1.0
> las preguntas se transcribieron **recortadas**: a R-04 le faltaba el
> «¿qué es?» final y a R-09 el «Tengo... quisiera saber cómo.». El recorte
> movió la similitud de R-09 de **0.6682 a 0.6396**, es decir, la cruzó por
> debajo del umbral y la mandó por otro camino del código. Está corregido y
> queda anotado: **una consulta recortada no es la misma consulta**, que es
> lo que el ADR-0013 ya advertía del recorte que hace el agente.

Se revisó una por una que **ninguna contenga dato personal**: ni nombres,
ni barrios, ni referencias identificables. Por eso pueden vivir en este
repositorio, que es público.

## 1.2 Las diez derivadas del corpus

Se muestrearon fragmentos de las nueve fuentes y se redactaron preguntas
**cuya respuesta está en un fragmento concreto**, cubriendo las fuentes
que las preguntas reales no tocan: el manual de la FAO, el libro de la
UNAD, la cartilla de fertilización, el catálogo de plantas, el protocolo
de espacio público y la cartilla 1.

Dos de ellas —romero y canelón— se eligieron **a propósito para disparar
la advertencia médica**: el catálogo atribuye usos medicinales, y esa es
la vía del riesgo P-01.

## 1.3 Las cuatro de control

Las veinte están cubiertas por el corpus, que es lo que pide el
anteproyecto. Con solo eso quedaría sin probar el camino que se activa
cuando **nada** supera el umbral (`CU2_RESPALDO_MODELO`), que es el más
expuesto: ahí la respuesta no está atada a ningún documento.

Se añadieron cuatro preguntas **deliberadamente fuera del corpus**. No
cuentan para la calificación de las veinte; se califican con otro criterio:
**que no cite fuente, que no invente el dato y que diga que no lo tiene.**

---

# 2. Cómo se ejecuta

    python -m scripts.ejecutar_banco

**No se llama a `consultar_orientacion`.** El script entra por
`procesar_evento` con cargas útiles con la forma real de las de Meta, igual
que `spike_despachador`, de modo que por el camino pasan el enrutamiento
del agente, la retirada de etiquetas de procedencia y la advertencia médica
del ADR-0015. Lo que se califica es **lo que la usuaria recibiría**, no lo
que devuelve una función.

Escribe en la base con una identidad temporal con forma de BSUID
(`CO.570000000605`) y la borra en un `finally`. No envía nada por WhatsApp:
los módulos que envían se sustituyen por espías, **incluido el indicador de
«escribiendo»**, que sí sale a la API de Meta.

**Cada pregunta entra en conversación limpia**: entre una y otra se borran
los mensajes de la identidad temporal, para que la ventana de memoria no
arrastre la anterior.

Se vuelve a ejecutar **cada vez que cambie el corpus**. Esa es su segunda
función: es la línea base contra la que se comprueba que una limpieza o una
ingesta no empeoraron las respuestas.

---

# 3. Resultado de la ejecución del 24/09/2026

Modelo `gemini-3.6-flash`, umbral 0.66, top-k 4, corpus de 765 fragmentos.

Se ejecutó **dos veces el mismo día**, antes y después de limpiar los 36
fragmentos con basura de extracción (INC-019). Las similitudes de la tabla
son las de **después**, que es el corpus vigente; el §6 compara las dos.

## 3.1 Preguntas reales de usuarias

| # | Tema | Sim. | Camino | Resultado |
|---|---|---|---|---|
| R-01 | A qué es vulnerable la acelga | 0.7637 | con respaldo | **Responde.** Sequía, gusano gris, caracoles, babosas, mosca minadora, virus y hongos |
| R-02 | Cómo cuidar la acelga de los bichos | 0.7389 | con respaldo | **Responde.** Riego matinal, ventilación, purines de ajo o cebolla, ceniza de ajenjo |
| R-03 | Paca compostera en espacio público | 0.7222 | con respaldo | **Responde.** Sí hace falta autorización; describe el trámite y admite que no cubre las pacas |
| R-04 | Huevitos amarillos bajo la hoja del repollo | 0.7016 | con respaldo | **Responde.** Los identifica como gusano de la col |
| R-05 | Atrapador de rocío casero | 0.7001 | con respaldo | **Declina y cita** |
| R-06 | Tipo de suelo para la granadilla | 0.6826 | con respaldo | **Declina y cita** |
| R-07 | Reusar el agua del lavado de la ropa | 0.6822 | con respaldo | **Declina y cita** |
| R-08 | Mariposa blanca en la granadilla | 0.6722 | con respaldo | **Responde.** Y **entiende bien el «aumento»**, que ella dijo por «controlo» |
| R-09 | Cuándo aporcar y cuándo está la remolacha | 0.6682 | con respaldo | **Declina y cita** |
| R-10 | Quemar la cascarilla | 0.6633 | con respaldo | **Declina y cita** |

## 3.2 Preguntas derivadas del corpus

| # | Tema | Sim. | Resultado |
|---|---|---|---|
| D-01 | Tamaño mínimo de la pila de compost | 0.7902 | **Responde.** 1 m³, 250 kg, 1,5–2 m de alto. Cita a la FAO |
| D-02 | Plantas para huerta familiar | 0.7726 | **Responde.** Pero le pone **advertencia médica sin hablar de salud** (INC-018) |
| D-03 | Para qué sirve el romero | 0.7696 | **Responde con advertencia médica.** Correcto |
| D-04 | Compost sin madurar | 0.7539 | **Responde.** Nitrógeno, oxígeno radicular, olores, patógenos |
| D-05 | Caldo sulfocálcico | 0.7514 | **Responde.** Preparación y dosis de 40 a 80 c.c. Cita a la UNAD |
| D-06 | Cuándo trasplantar del semillero | 0.7449 | **Responde, y una cifra no está en ninguna fuente** (INC-021) |
| D-07 | Capacidad del tanque de agua lluvia | 0.7205 | **Responde.** 250, 500, 1.000 L; y la advertencia del peso |
| D-08 | Usos del canelón | 0.7185 | **Responde con advertencia médica.** Correcto |
| D-09 | Qué echarle a la mosca blanca | 0.7140 | **Responde.** Diatomeas, neem, ajo-ají, ortiga, trampas amarillas |
| D-10 | Tapar un desagüe (pregunta trampa) | 0.7016 | **No da la respuesta correcta.** Ver el §4.2 |

## 3.3 Preguntas de control, fuera del corpus

| # | Tema | Sim. | Resultado |
|---|---|---|---|
| C-01 | Precio del arriendo de un lote | 0.6905 | **Correcto.** Dice que no lo tiene, **no cita** y no inventa |
| C-02 | Variedad de quinua para el Amazonas | 0.6707 | Dice que no lo tiene y no inventa, **pero cita** |
| C-03 | Teléfono del veterinario del JBB | 0.6514 | **Correcto.** Sin respaldo, sin cita, sin invención |
| C-04 | Clima de mañana | 0.6355 | **Correcto.** Sin respaldo, sin cita, sin invención |

**Las cuatro de control pasan en lo que importa: ninguna inventó un dato.**
El camino sin respaldo se comporta como debe.

---

# 4. Calificación

| Criterio | Umbral | Obtenido | |
|---|---|---|---|
| **Precisión** — ninguna afirmación agronómica falsa ni que contradiga el fragmento citado | 20 de 20 | **19 de 20** | **No pasa** |
| **Pertinencia** — la respuesta atiende lo que se preguntó, no un tema vecino | ≥ 16 de 20 | **14 de 20** | **No pasa** |
| **Coherencia** — sin contradicción interna, con la cita presente y sin etiqueta de procedencia colada | ≥ 18 de 20 | **14 de 20** | **No pasa** |
| **Advertencia médica** — presente en D-03 y D-08, y en toda respuesta que hable de salud | 100 % | **100 %** | **Pasa** |
| **Etiqueta de procedencia colada** — `[OFICIAL – …]` en el texto de la usuaria | 0 de 24 | **0 de 24** | **Pasa** |

La precisión se exige al 20 de 20 porque el daño no es simétrico: una
recomendación agronómica falsa le cuesta una cosecha a quien la siga, y en
las respuestas con contenido medicinal puede costar más.

**El banco no se supera, y casi todo lo explica un solo defecto.**

## 4.1 El defecto dominante: declina y cita (INC-020)

Seis de las veinte respuestas dicen a la usuaria que **no tienen esa
información** y a continuación le ponen **`Fuente: Jardín Botánico de
Bogotá José Celestino Mutis`**. Son R-05, R-06, R-07, R-09, R-10 y, entre
las de control, C-02.

Es contradictorio en el propio mensaje: o la guía lo dice o no lo dice. Y
no es cosmético, porque la cita es lo que sostiene la jerarquía de fuentes
de `CLAUDE.md` §6: **atribuir a una fuente oficial una no-respuesta es
atribuirle algo que no dijo.** Una usuaria que lea eso puede concluir que
el Jardín Botánico desaconseja quemar la cascarilla, cuando lo único cierto
es que el corpus no habla de eso.

Las seis tienen la misma forma: la similitud **supera** el umbral —entre
0.6633 y 0.7001—, así que el código entra por el camino con respaldo; pero
el fragmento recuperado **no responde la pregunta**, y el modelo, bien
instruido, lo dice.

**La cita la escribe el modelo**, no el código. El prompt
`redaccion_rag_v1.md` tiene dos reglas que aquí se contradicen: la 2 —«si
el contexto no alcanza para responder, dígalo con naturalidad»— y la 4
—«termine **siempre** citando la fuente… la cita no es opcional ni
adorno»—. El modelo obedece las dos a la vez, que es lo único que puede
hacer con esas instrucciones.

Esto vuelve a decir lo que ya decía el §5 de la versión anterior de este
documento, ahora con la respuesta delante y no solo con la similitud:
**superar el umbral no es tener la respuesta.**

## 4.2 Las dos preguntas cuya respuesta sí está en el corpus y no llega

**D-10, tapar un desagüe.** Es la pregunta trampa: la respuesta correcta es
que **no se puede**. El corpus lo dice con todas las letras, en el
Protocolo de espacio público: «Está prohibido la conexión de puntos de
servicios públicos, así como el taponamiento de drenajes, desagües y demás
elementos del sistema de acueducto…». Ese fragmento sale en el **puesto 32
con 0.6430**, por debajo del umbral, mientras el primero —sobre recoger
agua lluvia, 0.7016— se lleva la respuesta. La usuaria recibe consejos de
recolección de agua y **nadie le dice que eso está prohibido**.

**La dirección del formulario del JBB.** Es una consulta real, de las 19, y
puntúa **0.7261**. El corpus **sí tiene** las direcciones —ocho enlaces
`forms.office.com` en el Protocolo—, pero el fragmento que las contiene
sale en el **puesto 5 con 0.6811**: supera el umbral y **queda fuera del
top-k, que es 4**.

> **Corrección a la versión 1.0 de este documento.** Aquel §3.1 afirmaba
> que «el corpus no contiene ninguna URL de formulario» y que por eso era
> imposible responder. **Era falso**, y se descubrió inventariando el
> corpus carácter por carácter para otra cosa. El diagnóstico correcto es
> el contrario y es mejor noticia: la respuesta **está**, y lo que falla es
> la recuperación.

Las dos juntas dicen algo que ninguna calibración del umbral arregla: el
umbral decide **citar o no citar**, pero **`RAG_TOP_K` decide qué se lee**,
y hoy vale 4. Subirlo es barato y no toca ninguna medición del umbral, pero
**alarga el contexto y no está medido**: queda anotado, no hecho.

## 4.3 La cifra que no está en ninguna fuente (INC-021)

D-06 responde que hay que trasplantar con «de **2 a 4** hojas verdaderas».
El corpus dice «de **3 a 5** hojas verdaderas» en dos fuentes y «**dos o
tres** hojas verdaderas» en otra. **El «2 a 4» no está en ninguna**: parece
una mezcla de las dos.

Todo lo demás de esa respuesta sí se comprobó en el corpus, incluidas las
horas —«antes de las 9:00 am o pasadas las 4:00 pm»— y el «5 a 20 cm en un
plazo de 4 a 5 semanas», que estaban textuales.

Es el fallo más caro de detectar de todos: la respuesta es correcta en lo
demás, va citada y suena bien. **Solo se ve leyendo el fragmento.**

## 4.4 La advertencia médica

Está en las dos que debía —D-03 romero y D-08 canelón— y en ninguna de
esas dos faltó. Es el riesgo P-01, y en esta ejecución no se materializó.

Apareció además en **D-02**, que pregunta qué plantas sembrar en una huerta
familiar y no habla de salud. Confirma INC-018: **la advertencia es
demasiado ancha**. Se prefiere ancha a estrecha, pero conviene medirlo, y
esto es la medida.

## 4.5 Un resultado que conviene no perder

R-09 se ejecutó por casualidad dos veces, con el texto recortado y con el
literal:

| Texto | Sim. | Camino | Respuesta |
|---|---|---|---|
| Recortado | 0.6396 | **sin respaldo** | Explica qué es aporcar y cómo se nota que la remolacha está lista. **Útil**, sin cita y con el aviso de cautela |
| Literal | 0.6682 | **con respaldo** | «No cuento con esa información», más el dato suelto de que la remolacha mide hasta 50 cm. **Inútil**, y citando |

**La misma pregunta se responde mejor por el camino sin respaldo que por el
camino con respaldo.** Veintiséis milésimas de similitud separan una cosa
de la otra. No es un argumento para subir el umbral —el corpus sigue siendo
mejor fuente que el modelo cuando de verdad cubre el tema—, pero sí para
dejar de tratar el camino sin respaldo como el peligroso: aquí fue el
bueno.

---

# 5. Qué hacer con esto

Ninguna de las tres cosas que fallan es un problema de corpus ni de umbral,
y por eso ninguna se arregla ingiriendo más ni moviendo el 0.66:

1. **INC-020, declina y cita.** Es el 90 % de lo que baja la nota. La cita
   se adjunta por el número y no por el contenido; hay que decidir si el
   código puede saber que el modelo declinó, o si la cita debe pedírsele al
   propio prompt de redacción. Es una decisión de diseño y va a ADR.
2. **`RAG_TOP_K` = 4** deja fuera respuestas que están y superan el umbral.
   Medir con 6 y con 8 antes de tocarlo.
3. **INC-021**, la cifra mezclada. Una sola, en veinte, pero es justo la
   clase de fallo para la que se exigía 20 de 20.

Y una del propio banco: **el script no registra qué fragmentos entraron de
verdad en cada respuesta**. Se calificó reconstruyéndolos a mano, que es
lento y no queda como evidencia. Registrar el contexto recuperado junto a
la respuesta es lo que convierte esta calificación en repetible.

## 5.1 Una usuaria pidió explícitamente que se reportara la falta

Dos de sus mensajes son: *«Puedes reportar a tu fuente que tienes una
pregunta para la cual no tienes respuesta?»* y *«Reporta esa pregunta
también.»* Esa persona **detectó sola** que el bot no tenía con qué
responderle. Es la señal de campo más valiosa del periodo y merece citarse
en el documento: dice, sin encuesta, dónde falta corpus.

## 5.2 La forma de preguntar decide más que el tema

De las 19 consultas reales, las 4 que no superan el umbral **son
afirmaciones, no preguntas**. La misma usuaria, sobre el mismo problema:

| Formulación | Sim. | ¿Pasa? |
|---|---|---|
| «Hay problema con la sequia» | 0.6531 | No |
| «Por ahora solo requiero opciones para obtención de agua del ambiente, ya que no hay lluvias» | 0.7147 | Sí |

El corpus **sí** tiene material sobre agua y sequía. Lo que falla es que un
comentario corto no se parece a un texto técnico. Apunta a algo que no está
en la lista de pendientes y debería: **al sistema le falta pedir precisión
cuando la entrada es un comentario y no una pregunta.**


---

# 6. La limpieza del corpus, medida contra este banco

El 24/09/2026, entre las dos ejecuciones, se corrigieron **36 fragmentos de
765** con basura de extracción (INC-019) y se revectorizaron solo esos, con
`scripts/limpiar_corpus.py`. Este banco es lo que dice si eso mejoró o
empeoró las respuestas, y es la primera vez en el proyecto que un cambio de
corpus se mide así en vez de a ojo.

**De las 24 preguntas, 21 dan exactamente la misma similitud.** Se movieron
tres:

| # | Antes | Después | |
|---|---|---|---|
| R-04 | 0.7114 | **0.7016** | Baja 0.0098. Su fragmento era de los limpiados |
| D-06 | 0.7420 | **0.7449** | Sube 0.0029. Su fragmento era de los limpiados |
| C-01 | 0.6906 | 0.6905 | Una diezmilésima |

**Ninguna cruzó el umbral en ningún sentido**, así que ninguna cambió de
camino. El riesgo que INC-019 declaraba —que limpiar moviera las
similitudes y dejara vieja la calibración— **no se materializó**, y ahora
está medido en vez de supuesto.

## 6.1 Lo que sí cambió, y no es la similitud

La basura no era decorativa. La viñeta simbólica de la cartilla de
fertilización se guardaba como la letra `y`, así que el modelo leía las
listas de esa cartilla como una frase corrida:

> «…a lo largo del ciclo vegetativo. **y** Hidratar el sustrato donde se
> sembrarán las plántulas **y** Abrir un hueco de aproximadamente 5 cm
> **y** Por cada plántula, adicionar 5 gramos de micorrizas…»

Son 95 casos. Ahora dicen `•`. Eso no mueve casi la similitud —lo acabamos
de medir— pero cambia lo que el modelo tiene delante al redactar.

## 6.2 Una advertencia sobre leer esta comparación

R-04, cuyo fragmento se limpió, **respondió peor** en la segunda
ejecución: en la primera identificó los huevos como gusano de la col sin
reservas y en la segunda pidió que le preguntaran de otra manera. **No se
puede atribuir a la limpieza.** El agente corre a temperatura 0.7 y una
sola repetición no es una medida (`CLAUDE.md` §12). Queda anotado como lo
que es: un caso que hay que repetir antes de diagnosticar.


---

# 7. Tercera ejecución: después del ADR-0025

El mismo día, tras corregir INC-020 —declinar y citar igual— con el
ADR-0025: la línea de la fuente la pone ahora el backend y el modelo solo
declara, con una marca interna, que el contexto no le alcanzó.

## 7.1 Calificación

| Criterio | Umbral | Antes | Después | |
|---|---|---|---|---|
| **Precisión** | 20 de 20 | 19 | **20 de 20** | **Pasa** |
| **Pertinencia** | ≥ 16 de 20 | 14 | 13 de 20 | **No pasa** |
| **Coherencia** | ≥ 18 de 20 | 14 | **20 de 20** | **Pasa** |
| **Advertencia médica** | 100 % | 100 % | 100 % | **Pasa** |
| **Etiqueta colada** | 0 de 24 | 0 | 0 de 24 | **Pasa** |

## 7.2 Lo que se arregló

**INC-020, de 6 de 20 a 0 de 20.** Ninguna respuesta declina y cita. Las
seis que antes lo hacían —R-05, R-06, R-07, R-09, R-10 y C-02— ahora dicen
que no tienen la información y **no atribuyen nada a nadie**.

Siguen citando dos respuestas que contienen una frase negativa, y **es
correcto**: R-03 y R-08 responden con el contexto y avisan de lo que les
falta, que es justo la regla 3 del prompt. La cita las respalda de verdad.

**INC-021, la cifra que no estaba en ninguna fuente.** La regla 9 del
`redaccion_rag_v2.md` le prohíbe promediar o fundir cifras de fragmentos
distintos. D-06 pasó de

> «entre **2 y 4** hojas verdaderas y una altura de 5 a 20 centímetros…
> esto sucede entre 30 y 35 días»

a

> «**El tiempo varía según la planta.** …entre 30 y 55 días desde la
> germinación, o cuando midan entre 5 y 20 centímetros. Otra señal es que
> tengan entre **3 y 4** hojas verdaderas»

El «3 a 4» es textual de la cartilla de fertilización, y el «varía según la
planta» es la respuesta honesta cuando dos documentos dan cifras distintas.

## 7.3 Lo que no se arregló, y no se arregla con código

**La pertinencia sigue por debajo del umbral**, y las cinco preguntas
reales que fallan son las mismas de siempre: cómo hacer un atrapador de
rocío, qué suelo quiere la granadilla, si se puede reusar el agua de lavar
la ropa, cuándo aporcar, y cómo quemar la cascarilla. **El corpus no las
cubre.**

Lo que cambió es que ahora el bot lo dice sin colgarle la falta al Jardín
Botánico. Eso no es responder: es fallar bien. **Se arregla con corpus, no
con código**, y es lo que hay que declarar en el documento de grado.

A eso se suma D-10, la pregunta trampa, que sigue sin decir que taponar un
desagüe está prohibido: su fragmento sale en el **puesto 32 con 0.6430**,
por debajo del umbral, así que ni subir el top-k lo alcanza.

## 7.4 Advertencia sobre estos números

La pertinencia bajó de 14 a 13, y **no hay que leerlo como una regresión**.
Lo que cambió fue D-05, el caldo sulfocálcico: en la segunda ejecución dio
la preparación **y la dosis**, y en la tercera solo la preparación. El
agente corre a temperatura 0.7 y la redacción a 0.4; una repetición no es
una medida (`CLAUDE.md` §12).

Lo que sí se puede afirmar de una sola ejecución es lo que cambió de forma
**categórica y en el sentido previsto**: seis citas indebidas a cero, y una
cifra inventada a la cifra de la fuente. Eso no es variación.

## 7.5 Lo que este banco sigue sin poder ver

El backend sabe si el modelo declinó, pero no si **acertó** al declinar. Una
respuesta que el contexto sí sostenía y el modelo no supo redactar sale
ahora sin cita, y no la detecta nada. Está declarado como riesgo residual en
el ADR-0025 y es la razón de que P-03 baje a probabilidad 2 y no a 1.
