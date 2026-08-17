# ADR-0016. El registro empieza con un onboarding de preguntas cerradas

- **Estado:** Aceptada
- **Fecha:** 2026-08-17
- **Fase:** 7 (corrige el CU3 construido en la Fase 5)
- **Depende de:** [ADR-0002](0002-catalogo-de-barrios.md),
  [ADR-0008](0008-borrador-de-registro-y-una-huerta-por-usuaria.md),
  [ADR-0012](0012-memoria-de-conversacion.md)

## Contexto

El CU3 captura mal la información, y la causa está identificada: al aceptar
el consentimiento, el bot envía **un solo mensaje libre pidiendo tres cosas
a la vez** —nombre de la huerta, barrio y qué tiene sembrado—. La usuaria
responde a una, a dos o a ninguna, y la extracción trabaja sobre una
respuesta parcial que no sabe a qué pregunta contesta.

Ninguna fase lo previó porque las tres fases de diseño describen el CU3 como
un flujo conversacional único: ella cuenta algo, el sistema extrae, muestra
y confirma. Eso funciona para lo que va contando sobre la marcha —«sembré
lechuga el mes pasado»—, y es lo que el
[ADR-0008](0008-borrador-de-registro-y-una-huerta-por-usuaria.md)
implementó. Lo que no funciona es usar el mismo mecanismo para **arrancar**,
cuando el sistema no sabe nada de ella y necesita tres datos concretos.

El perfil de usuaria agrava el fallo. Un mensaje que pide tres cosas a la
vez exige sostener tres respuestas en la cabeza y redactarlas juntas; es
justo la carga que el diseño quiere evitar (CLAUDE.md §1).

Este ADR **no sustituye** el CU3 conversacional: lo antepone. Después del
onboarding, cuando ella cuente qué va sembrando, el flujo del ADR-0008 sigue
siendo el que atiende.

## Decisión 1. Tres preguntas cerradas, una por una, sin salto

Al aceptar el consentimiento se abre un onboarding de **tres preguntas
obligatorias**, en este orden y una por mensaje:

1. **Nombre de pila.** Sin apellido.
2. **Barrio.**
3. **Nombre de la huerta.**

No se puede saltar ninguna. Si la respuesta no sirve —una pregunta ajena, un
saludo, una frase sin el dato— **se repite la pregunta**. Al segundo intento
fallido se ofrece una salida explícita:

- para el nombre, escribir `vecina` o `vecino`;
- para el nombre de la huerta, escribir `Mi huerta`.

**Solo el nombre de pila, y es una decisión de minimización.** El apellido
no se usa en ninguna parte del sistema: no identifica —la identidad es el
número de celular (CLAUDE.md §4.8)—, no se muestra a otras usuarias y no
entra al RAG. Pedirlo sería recoger un dato personal sin finalidad, contra
la Ley 1581 de 2012 y contra la Fase 3 §5.

**El CU5 sigue sin precondición.** Si escribe «ayuda» en mitad del
onboarding se le da el texto fijo de ayuda —por `es_saludo_o_ayuda`, sin
modelo, camino permanente del
[ADR-0006](0006-saludo-y-ayuda-sin-modelo.md)— y **después se repite la
pregunta pendiente**. Atender la ayuda no consume un intento.

**Si abandona y vuelve pasadas 24 horas, se repiten las tres preguntas** y
lo que conteste sobrescribe lo anterior. Se descartó llevar la cuenta de qué
había contestado: el estado parcial multiplica los casos por tres y el coste
de repetir tres preguntas cortas es menor que el de razonar sobre un
onboarding a medias.

## Decisión 2. Confirmación implícita, con una sola confirmación explícita al final

El eco de lo que escribió **va dentro de la siguiente pregunta**, sin pedir
un «sí» aparte:

> Entendido, guardé Carmen.
> ¿En qué barrio está su huerta?

Tres confirmaciones explícitas seguidas convertirían un onboarding de tres
preguntas en uno de seis mensajes. El cierre sí es explícito: un resumen de
los tres datos y los botones **[Sí, guardar] / [No]**, reutilizando el
mecanismo y los textos que ya existen del CU3
(`textos.BOTON_REGISTRO_CONFIRMO` / `BOTON_REGISTRO_DESCARTO`, rótulos en
`textos.ROTULOS_BOTONES_REGISTRO`). No se crean botones nuevos.

**`guardé` y `anoté` no son sinónimos aquí, y la distinción es deliberada.**

| Dato | Verbo | Por qué |
|---|---|---|
| Nombre de pila | «guardé» | Es verdad: la fila de `usuario` existe desde el consentimiento, así que el nombre se persiste en el acto |
| Barrio, nombre de huerta | «anoté» | Esperan en el borrador hasta el botón final; decirle «guardé» sería falso en ese instante |

El nombre se persiste llamando otra vez a `registrar_consentimiento`
(`repositorio.py:892`), que ya acepta `nombre` opcional y hace `coalesce`:
es idempotente y no hace falta función nueva.

Es el mismo criterio de la decisión 4 del ADR-0008 —el resumen lo compone el
código para que refleje con exactitud lo que se va a guardar—, aplicado
ahora al verbo. «Guardado» queda reservado para después del botón.

## Decisión 3. `huerta` pasa a significar «completó el onboarding»

**Es el cambio de semántica más importante de este ADR y hay que enunciarlo
así en el documento de grado.**

Se necesita saber si una usuaria ya hizo el onboarding para no repetírselo.
El indicador es **la existencia de su fila en `huerta`**, lo que obliga a
crear esa fila al terminar el onboarding, no cuando ella cuente qué sembró.

| | Antes (ADR-0008) | Ahora |
|---|---|---|
| Existe fila en `huerta` | Registró algún dato agronómico | Completó el onboarding, con cultivos o sin ellos |

Consecuencias sobre lo ya decidido:

- **ADR-0008, decisión 2** («se reutiliza la huerta que ya tenga») se
  refuerza: ahora la huerta existe desde el principio, así que el flujo
  conversacional siempre reutiliza y nunca crea.
- **ADR-0011 / CU4** no se rompe: el CU4 ya se salta las huertas sin
  cultivos. Pero ahora habrá huertas sin cultivos de forma **normal** y no
  excepcional, y conviene no leer su número como un fallo.
- `huerta.nombre_huerta` es `nullable` en el esquema y el onboarding lo hace
  obligatorio **en la aplicación, no en la columna**. No se cambia el
  esquema: la salida `Mi huerta` cubre el caso y una restricción `NOT NULL`
  obligaría a migrar por una regla de flujo que puede cambiar en la Fase 8.
- `huerta.barrio_id` es `NOT NULL` y deja de ser un problema: con el barrio
  obligatorio, siempre hay valor. Desaparece el caso «sin barrio no hay
  botones» de la decisión 5 del ADR-0008.

## Decisión 4. El barrio se desambigua con el modelo, y se presenta como texto numerado

Ella escribe el barrio en lenguaje natural. El sistema busca los **tres
candidatos más parecidos** del catálogo y se los presenta numerados **en el
cuerpo de un mensaje de texto**, no como botones:

```
¿Cuál de estos es su barrio? Escriba solo el número.

1. SAN BERNARDINO SECTOR POTRERITO
2. SAN BERNARDINO SECTOR PROTRERITO
3. SAN BERNARDINO SECTOR VILLA EMMA
4. Ninguno de estos
```

**Por qué texto y no botones.** Es la decisión que más se estudió, y la
medición la resolvió sola. WhatsApp limita el rótulo de un botón a **20
caracteres**, y `app/services/whatsapp.py:117` **lanza `ValueError`** al
superarlo: un nombre largo no se ve mal, rompe el flujo. **76 de los 312
barrios de Bosa (24 %) pasan de 20 caracteres**, con máximo de 38. Recortar
no es salida: los nombres son oficiales, y además al recortar a 20 quedan
**seis grupos con el rótulo idéntico** —los cuatro `SAN BERNARDINO SECTOR
…` colapsan en el mismo texto—, con lo que ella vería dos opciones iguales
sin forma de elegir.

El cuerpo de un mensaje admite 1024 caracteres, así que los nombres
oficiales viajan íntegros. Y como el techo de tres botones desaparece, caben
**tres candidatos más la salida**, cuando con botones solo cabían dos.

**Esto evita enmendar el §4.3 de CLAUDE.md.** Una versión anterior de este
diseño usaba botones de desambiguación, lo que introducía un tercer momento
con botones y contradecía tanto el §4.3 como la decisión 5 del ADR-0008. Al
resolverlo con texto numerado, **no hace falta enmendar ninguna de las
dos**: los botones siguen apareciendo únicamente en el consentimiento y en
la confirmación de registro. Queda anotado que se consideró y por qué se
descartó.

**Por qué el modelo y no `pg_trgm`.** Se evaluó buscar por trigramas con la
extensión nativa de PostgreSQL. Se descartó por dos motivos:

1. **La fragmentación del catálogo derrota a los trigramas.** El listado
   oficial trae `HOLANDA`, `HOLANDA I SECTOR`, `HOLANDA II SECTOR`,
   `HOLANDA III SECTOR` y `HOLANDA SECTOR CAMINITO`. Ante «Holanda», la
   similitud de cadenas no distingue el barrio base de sus variantes; el
   modelo sí interpreta que una respuesta escueta apunta al base.
2. **Ahorra un umbral que calibrar.** `pg_trgm` traía un parámetro nuevo a
   medir en la Fase 7, que ya arrastra la revalidación del 0.68.

La llamada usa **salida estructurada con `enum` de códigos y temperatura
0.1**, el mismo patrón que la extracción de entidades, no los 0.7 del
agente. Así el modelo solo puede devolver códigos válidos del catálogo y no
hace falta validar después. A 0.7 aplicaría el aviso de CLAUDE.md §12 sobre
no fiarse del primer resultado; a 0.1 con esquema cerrado, no.

**El coste del enum grande se paga una vez.** Los 312 barrios ocupan unos
2 500 tokens de prompt. El onboarding corre **una vez por usuaria**; la
extracción corre en **cada mensaje**. Por eso el orden de trabajo de la
decisión 7 importa: el enum no desaparece, se muda de un sitio que corre
siempre a uno que corre una vez.

## Decisión 5. La respuesta numérica se lee sin el modelo

Un botón devolvía un identificador inequívoco; un «3» hay que interpretarlo.
Lo hace un lector determinista, sin modelo y sin temperatura, del mismo tipo
que `es_saludo_o_ayuda`.

**Acepta el dígito y la palabra:** `1 2 3 4` y `uno dos tres cuatro`.

La palabra no es una concesión, es un requisito de la entrada por voz.
`app/services/normalizacion.py` instruye «**Transcriba el audio
literalmente**» a temperatura 0.0, así que una nota de voz diciendo «tres»
llega como `tres` en letras, nunca como dígito. Con un lector de solo
dígitos, una usuaria que responde por voz recibiría «No entendí»
indefinidamente y —como el barrio es obligatorio— **no podría terminar el
onboarding ni usar el bot**. La voz entró en el alcance en la Fase 2 por
este perfil de usuaria; sería el peor sitio donde cerrarle la puerta.

Se descarta todo lo demás: `Holanda sector 3`, `la de arriba`, un saludo o
cualquier respuesta ambigua. Ante eso:

> No entendí. Por favor escriba solo el número de su opción, por ejemplo: 2

Redactado en **usted**, como todo mensaje al usuario (CLAUDE.md §11).

**Hay que persistir qué se le ofreció.** Un «3» no significa nada sin saber
qué tres candidatos vio, y la respuesta llega en un mensaje distinto. Es el
mismo problema que la decisión 1 del ADR-0008 resolvió para el borrador, así
que se resuelve igual: el mapa número → código se guarda con el borrador del
onboarding, en la base y no en memoria.

## Decisión 6. La quinta opción aparece al tercer «Ninguno», no antes

Si pulsa **«Ninguno de estos»** tres veces, la lista pasa a ofrecer una
salida más:

```
5. Mi barrio no está en la lista
```

que asigna el valor `otro` del catálogo y deja seguir el onboarding.

**Por qué no desde el principio.** Ofrecer la salida fácil de entrada
degradaría el dato del barrio, que es el que sostiene la atribución del CU4
(`[COMUNITARIO – huerta, barrio]`, ADR-0001). Tres rondas de candidatos son
evidencia razonable de que su barrio no está en el catálogo; un `otro`
ofrecido en el primer intento sería solo el camino corto.

**El contador es el de «Ninguno», no el de respuestas ininteligibles.** Son
dos fallos distintos y solo uno se arregla con una opción más: si ella no
consigue escribir `3`, tampoco escribirá `5`, y añadir la opción solo alarga
el mensaje. Para ese caso la respuesta sigue siendo repetir la pregunta.

**Las etiquetas 4 y 5 se redactan por lo que hacen**, no por lo que
significan. «Ninguno» y «Otro» son casi sinónimos en español y la usuaria no
sabría cuál tocar; `Ninguno de estos` vuelve a preguntar el barrio y `Mi
barrio no está en la lista` cierra con `otro`.

Un `otro` frecuente sigue siendo la señal que anticipó el ADR-0002: al
catálogo le falta un barrio.

## Decisión 7. El catálogo pasa a los 312 barrios de Bosa, en mayúscula

El catálogo de siete barrios de la UPZ 84 se sustituye por **los 312 barrios
de la localidad de Bosa** del listado oficial (`localidad_numero = 7`), más
el valor `otro`.

- **Los nombres se guardan y se muestran en MAYÚSCULA**, tal como vienen del
  listado oficial. No se recortan ni se reescriben: son nombres oficiales, y
  la decisión 4 elimina la razón técnica que obligaba a acortarlos.
- **Se siembra con un script SQL idempotente**, `db/003_catalogo_barrios_bosa.sql`,
  siguiendo el patrón de `db/002_catalogo_barrios.sql`
  (`on conflict (codigo) do nothing`), con la referencia a este ADR en el
  comentario de cabecera.
- **`Los 3 Sectores` no entra.** No aparece en el listado oficial de Bosa,
  ni exacta ni parcialmente. El ADR-0002 lo había sembrado resolviendo a
  favor del anteproyecto §5.3.1 frente al §7.1, que lo omitía; el listado
  oficial indica que **el §7.1 tenía razón** y que §5.3.1 recogía un nombre
  de uso comunitario, no un barrio oficial. Se corrige en sentido contrario
  al ADR-0002.
- **El listado no se versiona.** Vive en `fuentes/`, que está en el
  `.gitignore`, igual que los PDF de las fuentes oficiales.

**Amplía el alcance declarado.** El anteproyecto §7.1 acota el trabajo a la
UPZ 84 Bosa Occidental; el catálogo pasa a cubrir la localidad entera. Es
deliberado: el coste de tener de más un barrio es una fila, y el de que
falte es una usuaria que no puede completar el onboarding. Queda como
corrección pendiente del anteproyecto.

**Preparación ya ejecutada (17/08/2026).** Se vaciaron `huerta`,
`registro_pendiente`, `idempotencia_webhook` y `barrio` en una sola
transacción, para que el catálogo pudiera reemplazarse sin choques de código
ni violaciones de clave foránea —la única que entra a `barrio` es
`huerta.barrio_id`—. **No se tocaron `usuario`, `mensaje`, `fuente` ni
`fragmento_oficial`**: contienen la fila real del autor, los 126 mensajes de
la prueba con celular que son el material de la Fase 7, y los 774 fragmentos
de las nueve fuentes que sostienen la calibración.

**`barrio` está vacía desde entonces**, y eso degrada el CU3 hasta que se
siembre: `extraccion.py:171` registra un error y devuelve una extracción
vacía, así que no se ofrece guardar nada.

## Decisión 8. El saludo personalizado se antepone al enviar y no se recuerda

Una vez cada 24 horas —medidas en horas desde su último mensaje, no por día
calendario— la respuesta se antepone con su nombre de pila:

> Hola Carmen, ...

**El saludo no se registra en `mensaje`.** El nombre vive cifrado con
AES-GCM en `usuario.nombre_usuario_cifrado`, y `mensaje.contenido` va en
claro por decisión del [ADR-0012](0012-memoria-de-conversacion.md). Si el
saludo completo se guardara en `mensaje`, el nombre quedaría expuesto en
claro allí y **el cifrado dejaría de proteger nada**: bastaría leer la
conversación para recuperarlo.

Esto obliga a **separar el texto que se envía del texto que se recuerda** en
`memoria.responder` (`app/services/memoria.py`). El cambio va ahí y no en
cada flujo porque es el punto único por el que pasa todo envío posterior a
la compuerta —invariante del ADR-0012—, y repartirlo abriría la puerta a que
un flujo nuevo se saltara la regla.

**El agente no se entera de si ya saludó hoy.** Es cosmética de entrega, no
información de la conversación: si entrara en la ventana de memoria, el
modelo podría imitarlo y saludar por su cuenta.

Es además la **primera vez que se usa `nombre_usuario_cifrado`**. La columna
y sus funciones (`cifrar_nombre` / `descifrar_nombre` en
`app/core/identidad.py`) existen desde la Fase 5 pero ningún flujo las
escribía ni las leía.

## Decisión 9. El barrio sale del extractor antes de ampliar el catálogo

El orden importa y no es intercambiable:

1. **Primero**, `app/services/extraccion.py` pasa a `extraccion_v2`:
   **solo cultivos y fechas**. El barrio deja de extraerse de la
   conversación libre.
2. **Después**, se siembra el catálogo de 312.

El barrio estaba en el extractor por herencia de las decisiones 3 y 5 del
ADR-0008: `huerta.barrio_id` es `NOT NULL` y no había ningún otro momento
donde preguntarlo, así que había que pescarlo del texto libre y fusionarlo
en el borrador. El onboarding elimina esa necesidad de raíz.

Si se invirtiera el orden, el enum de 312 barrios y su listado en texto
viajarían **en cada llamada de extracción del CU3 conversacional**
(`extraccion.py:169-181`), que corre en cada mensaje. Y ocurriría **sin
desplegar nada**: el catálogo vive en Supabase y Railway lee esa misma base.

## Consecuencias

- El CU3 gana un flujo de entrada; el conversacional del ADR-0008 se
  conserva para lo que ella cuente después.
- **`huerta` cambia de significado** (decisión 3). Afecta a cómo se leen el
  ADR-0004, el ADR-0008 y el ADR-0011.
- Se usa por primera vez `usuario.nombre_usuario_cifrado`.
- `memoria.responder` cambia de firma. Es el punto por el que pasa todo
  envío posterior a la compuerta, así que el cambio toca todos los flujos
  aunque la lógica viva en un solo sitio.
- Aparece un **borrador de onboarding** con el mapa número → código. Puede
  apoyarse en `registro_pendiente` o ser una tabla paralela; se decide al
  implementar.
- El catálogo pasa de 8 a 313 filas.
- **Nada de esto está implementado.** Lo único ejecutado es el vaciado de
  las cuatro tablas de la decisión 7.

## Lo que este ADR no resuelve

- **`EL BOSQUE DE BOSA` y `El Bosque`.** El anteproyecto lista `El Bosque`;
  el listado oficial solo trae `EL BOSQUE DE BOSA`. Probablemente sean el
  mismo barrio, pero no está verificado y no se decide aquí.
- **Cuántos candidatos acierta el modelo.** Que tres basten es una
  estimación, no una medida. Hay que comprobarlo en la Fase 7 con nombres
  de barrio dichos por usuarias reales, y muy en particular con los grupos
  fragmentados (`SAN BERNARDINO SECTOR …`, `HOLANDA …`).
- **Si tres rondas antes de ofrecer `otro` son demasiadas.** El número sale
  de un razonamiento sobre calidad del dato, no de una medición. Si en la
  evaluación las usuarias abandonan antes de la tercera, hay que bajarlo.
- **La mezcla consulta + dato** del ADR-0013 sigue igual: el onboarding no
  la toca.

## Alternativas descartadas

- **Seguir con el mensaje único de tres preguntas.** Es la causa del
  problema.
- **Botones para desambiguar el barrio.** El límite de 20 caracteres del
  rótulo lo hace inviable en el 24 % de los barrios, y `enviar_botones`
  lanza `ValueError` en vez de degradar. Exigía además enmendar el §4.3 de
  CLAUDE.md y la decisión 5 del ADR-0008.
- **Recortar los nombres de barrio.** Son nombres oficiales, y al recortar a
  20 caracteres seis grupos quedan con el rótulo idéntico.
- **Un mensaje de lista de WhatsApp.** Admitiría más opciones y nombres
  largos, pero es exactamente la forma de un menú de navegación, que el
  §4.3 prohíbe por reintroducir la barrera que el diseño elimina.
- **`pg_trgm` para los candidatos.** Descartada en la decisión 4.
- **Interpretar el número con el modelo.** Añade latencia y no
  determinismo a algo que resuelven cuatro cadenas fijas.
- **Llevar la cuenta del onboarding incompleto.** Triplica los casos para
  ahorrar dos preguntas cortas.
- **Pedir el apellido.** Sin finalidad en el sistema; contra la
  minimización.
- **Poner `NOT NULL` a `nombre_huerta`.** Una regla de flujo no justifica
  una migración de esquema.
