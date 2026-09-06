# Correcciones a los documentos de fases

Lo que los `.docx` de `docs/` dan por cerrado y el sistema implementado hace
de otra manera. Cada entrada dice **qué afirma el documento**, **qué hace el
código** y **qué decisión lo justifica**.

Es el consolidado que antes vivía en `docs/adr/README.md`. Se movió aquí para
que haya un solo sitio que mantener, y porque incorpora además lo que se
decidió después de escribir aquel listado.

- **Corte:** 2026-08-23
- **Estado del código:** commit `d3c7c01`
- **Regla:** cuando un ADR corrige un documento de fase, **prevalece el ADR**.

Los valores de la tabla de parámetros se leyeron del código, no de la
documentación.

---

## Parámetros vigentes

| Parámetro | Valor | Frente al documento |
|---|---|---|
| Modelo de embeddings | `gemini-embedding-001`, 768 dim | La Fase 3 §3 y la Fase 4 §7 citan `text-embedding-004`, dado de baja. Truncado a 768 porque pgvector solo indexa hasta 2000 (ADR-0007). Fijo en código a propósito |
| Modelo generativo | `gemini-3.5-flash-lite` | No existía al escribir la Fase 4. **Desalineado:** `config.py` declara `gemini-3.6-flash` y Railway corre el *lite* |
| Umbral oficial (coseno) | **0.66** | La Fase 4 §7 dice 0.7. Bajó a 0.68 (ADR-0010) y a 0.66 el 19/08/2026 |
| Umbral comunitario | 0.65 | La Fase 4 no contempla un umbral propio (ADR-0011) |
| top-k por colección | 4 | Conforme |
| Ventana de memoria | 10 mensajes | La Fase 4 §6 no precisa si son mensajes o turnos (ADR-0012) |
| Temperatura · agente | 0.7 | Conforme |
| Temperatura · extracción | 0.1 | Conforme. Única no calibrable |
| Temperatura · barrio | 0.1 | Paso que la Fase 4 no contempla (ADR-0016) |
| Temperatura · redacción | 0.4 | Conforme |
| Temperatura · transcripción | 0.0 | No está en la Fase 4: es anterior a que la voz entrara al alcance |
| Troceo / solape | 300–500 / 50 tokens | La Fase 4 §7 no dice cómo se cuentan (ADR-0009) |
| Corpus oficial | 765 fragmentos, 9 fuentes | La Fase 4 supone una sola entidad; dos no son del Jardín Botánico |
| Catálogo de barrios | 313 | 312 de Bosa más `otro`. El anteproyecto acotaba a la UPZ 84 (ADR-0016) |

---

## Fase 2 — Diseño funcional

Casos de uso y orquestación. La mayoría son cosas que el documento no podía
prever porque solo aparecen al ponerlo a hablar con una persona.

### CU2, paso 1 — el barrio no filtra

- **Dice:** recupera «datos comunitarios del barrio».
- **Hace:** el barrio **no filtra** la recuperación comunitaria. Filtrar por
  barrio deja fuera respuestas útiles de barrios vecinos con el mismo clima
  y suelo.
- **Justifica:** [ADR-0001](adr/0001-barrio-no-filtra-recuperacion.md)

### CU1, flujo alternativo 3a — no se insiste

- **Dice:** el ciclo se repite hasta que el usuario acepte.
- **Hace:** se pide **una sola vez**. Ante el rechazo no se insiste: la
  puerta queda abierta pero la iniciativa es suya. Insistir sobre una
  negativa es lo contrario de un consentimiento informado.
- **Justifica:** [ADR-0003](adr/0003-consentimiento-sin-insistencia.md), Ley
  1581 de 2012

### CU3 y §5.4 — el RLS no es la barrera

- **Dice:** el RLS de Supabase protege los datos personales.
- **Hace:** la barrera real es el **filtrado por `usuario_id`** en cada
  consulta. El RLS está activo pero es defensa en profundidad: el backend
  usa *service role*, que lo omite.
- **Justifica:** contradicción interna — la propia Fase 3 §5.1 lo desmiente.

### CU1 y CU5 — cómo se atiende a quien no ha autorizado

- **Dice:** el CU5 es el único caso de uso sin precondición, pero no dice
  cómo se atiende a quien todavía no ha autorizado.
- **Hace:** el saludo y la ayuda se detectan **sin pasar por el modelo**, con
  listas de palabras dentro de la compuerta. Mandar el mensaje a Gemini
  sería procesarlo antes de tener permiso.
- **Justifica:** [ADR-0006](adr/0006-saludo-y-ayuda-sin-modelo.md)

### CU2 — qué hacer sin respaldo oficial

- **Dice:** nada sobre qué hacer cuando ninguna fuente supera el umbral.
- **Hace:** responde con el **conocimiento del modelo y sin citar a nadie**.
  La ausencia de atribución es lo que le permite a la usuaria distinguir un
  dato verificado de uno que no lo está.
- **Justifica:** [ADR-0010](adr/0010-umbral-de-similitud-recalibrado.md),
  revertido por `CU2_RESPALDO_MODELO`

### §4 — las herramientas del agente son cuatro

- **Dice:** el agente tiene tres herramientas.
- **Hace:** son **cuatro**. Se añadió `mostrar_ayuda` porque el saludo
  posterior al consentimiento no cabía en las otras tres sin incumplir la
  propia Fase 2. El modelo decide *cuándo*, el backend decide *qué*.
- **Justifica:** [ADR-0013](adr/0013-agente-orquestador.md)

### CU3 — el registro empieza con preguntas cerradas

- **Dice:** un único flujo conversacional en lenguaje natural.
- **Hace:** arranca con un **onboarding de tres preguntas cerradas**
  —nombre, barrio, nombre de huerta— una por mensaje. El flujo
  conversacional atiende después solo los cultivos. De una respuesta parcial
  a tres preguntas juntas no salía una extracción buena.
- **Justifica:** [ADR-0016](adr/0016-onboarding-de-preguntas-cerradas.md)

### CU3, confirmación — sin fecha

- **Dice:** el resumen previo a los botones incluye la fecha de siembra.
- **Hace:** muestra **solo el nombre de la planta**. Pasó de
  `- tomate, marzo de 2026 (más o menos)` a `- tomate`.
- **Justifica:** [ADR-0018](adr/0018-sin-fecha-de-siembra.md)

---

## Fase 3 — Diseño técnico

Arquitectura, esquema y modelo de seguridad. Aquí están las dos correcciones
con más peso legal del proyecto.

### §2 (C4) y Tabla 2 — falta el procesamiento asíncrono

- **Dice:** el diagrama de contenedores no contempla procesamiento asíncrono
  ni un despachador.
- **Hace:** es **obligatorio**. El webhook responde `200` de inmediato y
  delega a segundo plano. Meta reintenta si tardas, y el pipeline completo
  excede ese margen. Sin esto hay respuestas y registros duplicados. Va
  acompañado de idempotencia por `wamid`.
- **Justifica:** [ADR-0005](adr/0005-procesamiento-asincrono-e-idempotencia.md)

### §2 (C4) — qué ve la usuaria mientras espera

- **Dice:** el asíncrono se describe desde el lado del webhook, para que Meta
  no reintente.
- **Hace:** nada dice qué ve **la usuaria** durante los ~13 segundos del
  camino con RAG, que es quien de verdad espera. Se probó un aviso de texto y
  **se retiró**: anunciar la espera la hacía sentir más larga. Desde el
  23/08/2026 lo cubre el **indicador de «escribiendo» de la Cloud API**, que
  no manda ningún mensaje y por tanto no marca el comienzo de la espera. Trae
  incluido el acuse de lectura: aparecen los dos chulos azules.
- **Justifica:** [ADR-0017](adr/0017-aviso-de-espera.md) y su revisión

### §3 — el modelo de embeddings

- **Dice:** `text-embedding-004`, 768 dimensiones.
- **Hace:** `gemini-embedding-001` con `output_dimensionality=768`. El modelo
  citado fue dado de baja. El truncado no es capricho: pgvector solo indexa
  hasta 2000 dimensiones con el tipo `vector` y el modelo devuelve 3072.
- **Justifica:** [ADR-0007](adr/0007-modelo-de-embeddings-fijo-en-codigo.md)

### §3, tabla `mensaje` — el `wamid` no se guarda

- **Dice:** se almacena el `wamid` del mensaje.
- **Hace:** se almacena su **huella HMAC**, nunca el valor. El `wamid`
  contiene el teléfono del remitente en ASCII, recuperable con un
  `base64 -d` —comprobado el 30/07/2026—. Tampoco va a la bitácora.
- **Justifica:** [ADR-0012](adr/0012-memoria-de-conversacion.md), migración
  `006`

### §3, tabla `cultivo` — sin fecha de siembra

- **Dice:** columnas `fecha_siembra_aprox` y `fecha_imprecisa`.
- **Hace:** **ya no existen**. Era un dato de solo escritura: lo escribían
  dos `INSERT` y no lo leía ningún caso de uso. El ADR-0011 ya había medido
  que dentro del fragmento comunitario empeoraba la recuperación —0.0735
  frente a 0.1166 de separación—.
- **Justifica:** [ADR-0018](adr/0018-sin-fecha-de-siembra.md), migración
  `008`

### §5.2 — la conversación queda almacenada

- **Dice:** el modelo de seguridad cubre el nombre cifrado y el teléfono con
  hash.
- **Hace:** no contempla que **la conversación entera quede almacenada**.
  `mensaje.contenido` es texto libre en claro, y es el único sitio donde lo
  que ella escribe queda guardado de forma permanente. Límite declarado: la
  minimización gobierna lo que el sistema *pide*, no lo que ella decide
  contar.
- **Justifica:** [ADR-0012](adr/0012-memoria-de-conversacion.md)

### §5.2 y Fase 4 Tabla 3 — el nombre se muestra en la conversación

- **Dice:** el nombre de la usuaria va cifrado en `usuario`.
- **Hace:** sigue cifrado, pero no se contemplaba que además **se le muestre
  en la conversación**. El saludo personalizado se antepone al enviar y **no**
  se registra en `mensaje`; registrarlo dejaría el nombre en claro allí y
  anularía el cifrado.
- **Justifica:** [ADR-0016](adr/0016-onboarding-de-preguntas-cerradas.md),
  decisión 8

### Fragmento comunitario — solo especies

- **Dice:** el texto vectorizado incluye nombre de huerta, barrio y fechas.
- **Hace:** **solo las especies** — `"tomate, cilantro, lechuga"`. Lo que se
  repite en todos los fragmentos infla por igual la similitud de todos y
  destruye la capacidad de distinguirlos. El nombre y el barrio se recuperan
  por la clave foránea. Medido sobre cuatro formatos:

      plantilla del spike        0.0585
      prosa con nombre y barrio  0.0608
      solo cultivos con fecha    0.0735
      solo especies              0.1166   <- el que quedó

- **Justifica:** [ADR-0011](adr/0011-fragmento-comunitario-solo-especies.md),
  sustituye al [ADR-0004](adr/0004-cultivo-y-fragmento-comunitario.md)

### Tabla 2 — componentes que no están listados

- **Dice:** un componente, una responsabilidad, con el inventario cerrado.
- **Hace:** el principio se respeta, pero aparecieron módulos que la tabla no
  lista: `dispatcher`, `onboarding`, `memoria`, `espera` y el agente
  orquestador.
- **Justifica:** ADR-0005, 0012, 0013, 0016, 0017

---

## Fase 4 — Diseño de IA

Es la fase con más desviaciones, y casi todas por el mismo motivo: **sus
números se fijaron antes de que existiera el corpus real**.

### §7 — el umbral de similitud

- **Dice:** 0.7, respaldado con documentos de prueba escritos a mano.
- **Hace:** **0.66**. Contra el corpus real, 0.7 dejaba sin responder 4 de 12
  consultas legítimas. Bajó a 0.68 (ADR-0010) y a 0.66 el 19/08/2026, medido
  contra **81 consultas reales** de dos pruebas con celular.
- **Justifica:** [ADR-0010](adr/0010-umbral-de-similitud-recalibrado.md) y la
  recalibración del 19/08/2026

### §7 — el umbral no separa la intención

- **Dice:** el umbral separa las consultas del CU2 de las que no lo son.
- **Hace:** **ningún umbral las separa.** Los rangos se solapan: «Que
  conocimiento en agricultura sabes» (no es CU2) puntúa 0.6779 y «Qué puedo
  hacer si mis plantas no dan frutos» (sí lo es) puntúa 0.6775. Quien filtra
  la intención es el agente. El umbral hoy decide **citar o no citar**, no
  responder o callar.
- **Justifica:** medición del 19/08/2026,
  [ADR-0013](adr/0013-agente-orquestador.md)

### §7 — umbral propio para la colección comunitaria

- **Dice:** un solo umbral para toda la recuperación.
- **Hace:** la colección comunitaria lleva **umbral propio, 0.65**. Sus
  fragmentos son listas de tres o cuatro palabras, no prosa de 400 tokens,
  así que sus similitudes viven en otro rango.
- **Justifica:** [ADR-0011](adr/0011-fragmento-comunitario-solo-especies.md)

### §7 — el agente puede recortar la consulta

- **Dice:** nada sobre qué texto se usa para consultar.
- **Hace:** el umbral se calibró sobre **mensajes completos**, pero el agente
  puede recortar la consulta. El recorte de un mensaje de doble intención
  cayó a 0.6796, cuatro diezmilésimas por debajo. El CU2 reintenta con el
  mensaje entero si el recorte no recupera nada.
- **Justifica:** [ADR-0013](adr/0013-agente-orquestador.md)

### §7 — cómo se cuentan los tokens del troceo

- **Dice:** fragmentos de 300–500 tokens con 50 de solape.
- **Hace:** se respeta, pero **no dice cómo se cuentan**. La aproximación
  estándar de 4 caracteres por token desvía lo bastante para sacar la mitad
  del corpus del intervalo. La ratio se mide **por documento** y vive en el
  catálogo de fuentes.
- **Justifica:** [ADR-0009](adr/0009-ingesta-de-fuentes-oficiales.md),
  [ADR-0014](adr/0014-catalogo-de-fuentes-oficiales.md)

### §7 — la ingesta descarta los índices

- **Dice:** nada sobre qué partes del documento deben descartarse.
- **Hace:** la ingesta **descarta los renglones de índice** —«Cilantro
  ....... 51»—. Eran 10 de 774 fragmentos y salían entre los cuatro mejores
  en el 25 % de las consultas reales. Un índice es una lista de nombres de
  plantas: puntúa altísimo contra cualquier pregunta sobre plantas y no
  responde nada.
- **Justifica:** 19/08/2026, commit `00133ef`. **Pendiente de ADR-0019.**

### §7 — desviación declarada del intervalo

- **Dice:** el intervalo de 300–500 tokens aplica a todo el corpus.
- **Hace:** el catálogo de plantas tiene **desviación declarada**: sus
  fragmentos miden ~183 tokens. Una ficha de especie mide eso, y respetar el
  intervalo exigiría meter dos plantas en el mismo fragmento. En un documento
  que atribuye usos medicinales, esa mezcla es el peor fallo posible.
- **Justifica:** [ADR-0014](adr/0014-catalogo-de-fuentes-oficiales.md)

### Tabla 3 — la extracción devuelve un solo campo

- **Dice:** la extracción devuelve especie, fecha de siembra, marca de
  imprecisión, barrio y nombre de huerta.
- **Hace:** **devuelve solo la especie**. El barrio y el nombre de huerta los
  fija el onboarding, y volver a extraerlos arriesgaría pisar lo que ella
  confirmó; la fecha era un dato de solo escritura. El prompt pasó de 2620 a
  1783 caracteres y el modelo quedó con un campo que acertar.
- **Justifica:** [ADR-0016](adr/0016-onboarding-de-preguntas-cerradas.md),
  [ADR-0018](adr/0018-sin-fecha-de-siembra.md)

### Tabla 3 — la justificación del valor cerrado

- **Dice:** el barrio es un valor cerrado, justificado por el filtrado de la
  recuperación.
- **Hace:** sigue siendo cerrado, pero **por otro motivo**: la justificación
  original queda anulada por el ADR-0001 —el barrio no filtra— y sustituida
  por la atribución del CU4. Se implementa como **tabla**, no como tipo
  `ENUM`: 313 valores que cambian no caben en un `ALTER TYPE`.
- **Justifica:** [ADR-0001](adr/0001-barrio-no-filtra-recuperacion.md),
  [ADR-0002](adr/0002-catalogo-de-barrios.md)

### §6 — la ventana de memoria

- **Dice:** ventana de diez.
- **Hace:** diez **mensajes**, no diez turnos, y el último es siempre el de
  ella. Nada anterior al consentimiento entra. Tampoco entra el acuse de la
  nota de voz, que se envía y no se recuerda.
- **Justifica:** [ADR-0012](adr/0012-memoria-de-conversacion.md),
  [ADR-0017](adr/0017-aviso-de-espera.md)

### Tabla 3 — faltan dos temperaturas

- **Dice:** temperaturas para agente, extracción y redacción.
- **Hace:** faltan dos filas: **transcripción a 0.0** —anterior a que la voz
  entrara al alcance— y **desambiguación de barrio a 0.1**, un paso que la
  Fase 4 no contempla.
- **Justifica:** [ADR-0016](adr/0016-onboarding-de-preguntas-cerradas.md)

---

## Anteproyecto

### §5.3.1 y §7.1 — el catálogo de barrios

- **Dice:** el §5.3.1 lista `Los 3 Sectores`; el §7.1 lista seis barrios y lo
  omite; ambos acotan el alcance a la UPZ 84 Bosa Occidental.
- **Hace:** el catálogo cubre **los 312 barrios de la localidad de Bosa** más
  `otro`, en mayúscula y sin recortar, tomados del listado oficial.
  `Los 3 Sectores` **no existe** en ese listado: acertaba el §7.1 al
  omitirlo, no el §5.3.1.
- **Justifica:** [ADR-0016](adr/0016-onboarding-de-preguntas-cerradas.md),
  corrige en sentido contrario al
  [ADR-0002](adr/0002-catalogo-de-barrios.md)

### §7.2 y §8 — la entrada por voz

- **Dice:** excluye la entrada por voz del alcance y la lista como trabajo
  futuro.
- **Hace:** está **dentro del alcance** desde la Fase 2 y funciona en
  producción. La **respuesta** por voz y la búsqueda en internet siguen
  fuera.

### §7.2 y §10.2 — el presupuesto

- **Dice:** dan Railway por gratuito.
- **Hace:** Railway no tiene plan gratuito real para un servicio permanente.
  Hay que contar **Hobby, USD 5/mes** durante la ejecución.

---

## Sin respaldo documental

No corrigen el documento: **lo amplían**. Son problemas que ninguna fase
previó y que hubo que resolver para que el sistema funcionara. Son las que
más falta hacen en el documento de grado, porque no tienen de dónde
deducirse.

| ADR | Qué añade |
|---|---|
| [0005](adr/0005-procesamiento-asincrono-e-idempotencia.md) | Procesamiento asíncrono e idempotencia por `wamid`, con dos estados en base: `recibido` permite recuperar un intento muerto, `procesado` es lo único que hace de un reintento un duplicado |
| [0006](adr/0006-saludo-y-ayuda-sin-modelo.md) | El saludo y la ayuda se detectan sin el modelo. Es lo que permite atender el CU5 —único sin precondición— sin procesar el mensaje de quien no ha autorizado |
| [0015](adr/0015-advertencia-de-contenido-medico.md) | Advertencia médica en toda respuesta del CU2 que hable de salud. Las fuentes oficiales traen usos medicinales, y la usuaria es mayoritariamente adulta mayor y puede estar medicada. La pone el backend, no el prompt |
| [0017](adr/0017-aviso-de-espera.md) | El acuse de la nota de voz se envía y no se recuerda. Única excepción a «enviar y recordar van juntos» |

---

## Lo que sigue abierto

Antes de dar la Fase 7 por cerrada.

**El corpus no es del todo reproducible.** `jbb_practicas_2022` tiene 62
fragmentos en la base y el código produce 83, comprobado revirtiendo el árbol
a `b159cd2`. No lo causó la limpieza de índices. Mientras siga así, toda
calibración hereda esa debilidad, porque el corpus sobre el que se midió no se
puede rehacer.

**La calibración del umbral no está cerrada.** El 0.66 está medido contra 81
consultas reales, pero falta etiquetar leyendo el fragmento recuperado de cada
una. La frontera que importa no es «del dominio o no», es «el fragmento
responde de verdad o no», y eso es criterio del autor.

**El modelo generativo está desalineado entre código y despliegue.**
`app/config.py` declara `gemini-3.6-flash` y Railway corre
`gemini-3.5-flash-lite`. El propio comentario de ese archivo dice que el valor
por defecto existe para dejar constancia de con qué se probó, así que hoy se
contradice. El *lite* responde más rápido —3 s frente a 10-19 s— pero, según
observación del autor, con peor calidad.

**Falta el ADR-0019.** La limpieza de índices del corpus y la bajada del
umbral a 0.66 son la decisión con más recorrido del 19/08 y hoy solo viven en
mensajes de commit y en un comentario de `config.py`.
