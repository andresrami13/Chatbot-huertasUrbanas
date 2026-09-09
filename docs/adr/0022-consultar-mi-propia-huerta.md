# ADR-0022. Consultar la propia huerta es el CU8, y son cinco herramientas

- **Estado:** Aceptada
- **Fecha:** 2026-09-09
- **Fase:** 7
- **Origen:** sin respaldo documental — ninguna fase previó esta pregunta

## Contexto

El autor observó que al preguntarle **«qué tengo sembrado»** el bot
respondía **solo con el último cultivo**, no con todo lo que ella tiene.

La causa no estaba en el CU3, ni en la base, ni en el modelo. Es que
**ninguna fase previó que ella quisiera consultar sus propios datos.** Los
cinco casos de uso originales cubren autorizar (CU1), preguntar a la guía
(CU2), registrar (CU3), preguntar por las otras huertas (CU4) y pedir ayuda
(CU5). Leer lo suyo no está.

Y las herramientas del agente reflejaban eso: cuatro, ninguna capaz de
contarle lo que ella tiene registrado.

## Lo que pasaba, medido

**El agente nunca llamaba a nada.** Con la memoria real detrás y cuatro
repeticiones por frase:

    'que tengo sembrado'          -> (sin herramienta) ×4
    'que tengo en mi huerta'      -> (sin herramienta) ×4
    'cuales son mis cultivos'     -> (sin herramienta) ×4
    'que plantas tengo anotadas'  -> (sin herramienta) ×4
    'recuerdame que sembre'       -> (sin herramienta) ×4

    0/20

Y cuando el modelo no llama a ninguna función, `agente.py` **envía el texto
que el modelo haya escrito**. Ese texto sale de la ventana de memoria, que
son diez mensajes (ADR-0012).

De ahí el «solo el último cultivo»: los anteriores ya se habían salido de
la ventana. Reproducido con una usuaria que registró tomate, cebolla y
lechuga, hizo tres preguntas y luego registró cilantro —los cuatro en la
base—:

> «Usted tiene registrado que sembró cilantro. Si tiene más plantas en su
> huerta, me puede contar y las agregamos.»

**El fallo no es que faltara información: es que afirmaba algo falso sobre
los datos de ella**, con el tono del asistente y sin nada que lo delatara.
Es la misma clase de error que atribuirle cultivos a la huerta equivocada
en el CU4, y el mismo que el ADR-0021 acaba de cerrar allá.

**No dependía del modelo.** Se midió con `gemini-3.6-flash`, el desplegado.
Ninguno puede acertar: el dato no está en la conversación, está en la base.

## Decisión

### 1. Consultar la propia huerta es el CU8

Casos de uso: CU1 a CU5 de la Fase 2, CU6 (onboarding) del documento de
grado, CU7 (buscar un cultivo en otras huertas) del ADR-0021, y ahora
**CU8: consultar mi huerta**. Precondición: consentimiento (CU1) y
onboarding completado (CU6).

No cabía en el CU3, que la Fase 2 define como **registrar**. Leer no es
registrar, y meterlo ahí habría dado un caso de uso con dos garantías
contradictorias —uno persiste tras confirmación, el otro no persiste nada—.

### 2. Son cinco herramientas, no cuatro

`consultar_mi_huerta` **sin parámetros**, como `registrar_huerta` y
`mostrar_ayuda`. Lo que hay que contarle sale de la base por su
`usuario_id`, no de nada que escriba el modelo.

Esto enmienda el «son cuatro, no tres» del [ADR-0013](0013-agente-orquestador.md),
que sigue siendo correcto en lo que decía: el modelo decide **cuándo**, el
backend decide **qué**.

### 3. El texto lo compone el código

Como el resumen del CU3 (ADR-0008) y el listado del CU4 (ADR-0021). Aquí el
motivo es el más fuerte de los tres: **son sus datos, y este caso de uso
existe precisamente porque el modelo los estaba contando mal.** Un modelo
que los reformule puede perder un cultivo, y perder un cultivo es el fallo
que esto corrige.

### 4. La lista de cultivos no se recorta

Al contrario que la del CU4, que enseña cinco por huerta. Allá son huertas
ajenas y caben muchas en un mensaje; aquí son sus plantas, y **esconder
parte de ellas sería volver al fallo**. El tope real es el cuerpo de
WhatsApp, 1024 caracteres, que da para más de cien especies.

## La distinción entre preguntar y contar, que es el riesgo real

Añadir esta herramienta mete un par que el agente tiene que separar:
«tengo cilantro sembrado» (registro) contra «qué tengo sembrado» (consulta).
Se diferencian en una palabra.

**No se resuelve con el signo de interrogación**, y era la duda del autor al
aprobarlo: este perfil de usuaria muchas veces no lo escribe. Lo que las
separa es **si nombra una planta o no**, y eso sobrevive a la falta de
puntuación. El prompt lo dice con esas palabras.

Medido con **catorce frases y ninguna con signos de interrogación**, cuatro
repeticiones cada una: **56/56**. Incluye el par difícil —«que tengo
sembrado» contra «tengo cilantro sembrado»— y cinco afirmaciones que deben
seguir yendo al registro.

**Y si el modelo se equivoca, hay una red determinista que ya existía.**
`registrar_huerta` no lleva parámetros: el backend corre el extractor sobre
el mensaje literal a 0.1. Una consulta enrutada por error al registro no
encuentra especies, así que ella recibe el «no le entendí qué sembró» y
**no se guarda nada**. El error molesta pero no corrompe.

El error inverso —una afirmación tratada como consulta— sí perdería el
registro, y por eso las cinco afirmaciones se midieron aparte. Además ella
lo vería: recibiría su lista sin la planta que acaba de contar.

Si dice las dos cosas en el mismo mensaje, el agente llama a las dos y
`_seleccionar` ya deja el registro al final, porque es el que lleva botones
(ADR-0013).

## Consecuencias

**Cubre además preguntas que hoy fallaban por lo mismo:** «¿cómo se llama
mi huerta?» y «¿en qué barrio quedé registrada?». Salen del mismo sitio.

**El CLAUDE.md §5 y el AGENTS.md cambian de número**: las herramientas del
agente pasan a ser cinco, y los casos de uso a ocho.

**`spike_despachador` gana tres comprobaciones** y pasa de 26 a 29. Una de
ellas es que la pregunta **no** se confunda con un registro, que es el
riesgo que este ADR introduce.

**Una huerta sin cultivos responde sin tratarlo como error.** Desde el
ADR-0016 existir en `huerta` significa «completó el onboarding», así que
una huerta sin plantas es lo normal y el texto lo dice como tal.

## Lo que este ADR no resuelve

**Cuántas veces se equivoca el modelo en el par pregunta/afirmación con
usuarias reales.** 56/56 es con catorce frases que escribió quien conoce el
sistema. La bitácora ya lo permite contar: cada llamada registra la
herramienta.

**Si a una usuaria con veinte cultivos el renglón se le hace ilegible.** No
se recorta a propósito, pero no se ha visto en un teléfono. Hoy la huerta
más grande de la base tiene seis.

**Nada de esto está probado desde un celular.** Sí contra la base real —las
cuatro huertas devuelven su lista completa, incluida la de seis cultivos
que era el caso que fallaba— y con las 29 comprobaciones del spike.
