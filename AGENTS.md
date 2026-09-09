# AGENTS.md

Instrucciones de proyecto para Codex. Léelas al inicio de cada sesión.

---

## 1. Qué es este proyecto

Prototipo funcional de un **chatbot de WhatsApp con inteligencia artificial**
para apoyar la creación y gestión de huertas urbanas en barrios seleccionados
de la **UPZ 84 Bosa Occidental** (Bogotá, Colombia).

Es el trabajo de grado de la Especialización en Ingeniería de Software de la
**Universidad Distrital Francisco José de Caldas**. Se enmarca en el Programa 25
del Plan de Desarrollo Local de Bosa 2024-2028, que fija la meta de 500 huertas
urbanas en la localidad.

**Usuarias reales:** líderes y propietarias de huerta, mayoritariamente adultas
mayores y de mediana edad, con apropiación tecnológica limitada al uso básico
del celular. Este perfil condiciona **todas** las decisiones de diseño. No es un
detalle de contexto: es la restricción principal.

**Criterio de éxito:** puntuación SUS igual o superior a 68 en la evaluación
sumativa con 5 a 7 usuarias de la comunidad.

---

## 2. Documentación de referencia — léela antes de proponer cambios

En `docs/` están los documentos de las fases ya cerradas. **Son la
especificación del sistema.** Si algo que vas a implementar contradice lo que
dicen, no lo implementes: dilo y espera decisión.

| Documento | Contenido |
|---|---|
| Anteproyecto | Problema, objetivos, metodología, alcance, marco legal |
| Fases de diseño | Fase 2 (funcional), Fase 3 (técnico), Fase 4 (IA) |
| `docs/ESTADO.md` | **Léelo al empezar.** Dónde está el trabajo y por dónde seguir |
| `docs/adr/` | Veintidós decisiones tomadas al implementar. Prevalecen sobre los `.docx` |
| `docs/correcciones-a-los-documentos.md` | **Qué dice cada `.docx` y qué hace el sistema**, por fase y sección. Consolidado de las desviaciones |

**Fase actual: 7 (calibración y pruebas).** La Fase 6 se cerró el
15/08/2026 con la prueba en un celular real. De la 7 van hechas cuatro
cosas: la ampliación del corpus —de 81 a **765 fragmentos en nueve
fuentes**—, el **onboarding de tres preguntas cerradas** que corrige la
captura del CU3 (ADR-0016), la **limpieza de los índices** del corpus y la
bajada del **umbral a 0.66**, medido contra 81 consultas reales
(19/08/2026).

**La calibración sigue sin cerrarse, y ahora se sabe por qué:** falta
etiquetar leyendo el fragmento recuperado de cada consulta, y
`jbb_practicas_2022` no se puede reproducir —62 fragmentos en la base
contra 83 que produce el código—. El detalle está en `docs/ESTADO.md`,
sección «Por dónde seguir».

---

## 3. Stack

| Capa | Tecnología |
|---|---|
| Backend | Python + FastAPI |
| Despliegue | Railway |
| Base de datos | Supabase (PostgreSQL + pgvector) |
| Modelo de lenguaje | API de Gemini |
| Orquestación | LangChain (librería dentro del backend, **no** un contenedor) |
| Canal | Meta Cloud API (WhatsApp) |

---

## 4. Decisiones no negociables

Provienen de las fases ya documentadas y de los hallazgos de campo de la
encuesta (Fase 1, n=11). No las revises ni las "mejores" por tu cuenta.

1. **WhatsApp es el único canal.** 11/11 encuestadas lo usan a diario, 9/11 lo
   prefieren. No propongas web, app móvil ni Telegram.
2. **El consentimiento es una compuerta previa a todo procesamiento.** Sin
   autorización solo se atienden el saludo y la ayuda (CU5). Cualquier consulta
   o registro queda bloqueado, y no se persiste ningún dato — tampoco el hecho
   del rechazo.
3. **Lenguaje natural como vía principal.** Botones de WhatsApp únicamente en
   dos momentos binarios: consentimiento y confirmación de registro. **Nunca**
   un menú de navegación permanente: reintroduce la barrera que el diseño
   quiere eliminar.
   Se estudió un tercer momento —botones para desambiguar el barrio— y se
   **descartó** (ADR-0016): el rótulo de un botón admite 20 caracteres y el
   24 % de los barrios de Bosa pasa de ahí. La desambiguación se resuelve
   con una **lista numerada dentro del cuerpo del mensaje**, que admite
   1024, así que esta regla sigue intacta.
4. **Normalización única de la entrada.** Si el mensaje es audio, se transcribe
   una sola vez antes de interpretar la intención. No dupliques transcripción
   por flujo.
5. **Separación de datos.** Lo agronómico (barrio, cultivos, nombre de huerta)
   es compartible y alimenta el RAG. Lo personal (teléfono, nombre) nunca se
   expone a otras usuarias ni entra al RAG.
6. **Jerarquía de fuentes:** fuente oficial curada > dato comunitario (siempre
   atribuido, nunca como instrucción técnica) > conocimiento del modelo (sin
   atribución ninguna, que es lo que le permite a ella distinguirlo).
   Búsqueda en internet fuera de alcance.
   **El tercer nivel está activo desde el 15/08/2026:** si nada supera el
   umbral, el CU2 responde con el modelo y sin citar a nadie
   (`CU2_RESPALDO_MODELO`). Eso revierte la decisión del ADR-0010 de callar
   sin respaldo. El umbral dejó entonces de decidir *responder o callar* y
   pasa a decidir **citar o no citar**.
   Y **toda respuesta del CU2 que hable de salud lleva advertencia**, la
   ponga el camino que la ponga (ADR-0015): las fuentes oficiales traen usos
   medicinales y toxicidad, y el documento avala la botánica, no un consejo
   médico para una persona concreta.
7. **Confirmar antes de guardar.** Toda extracción de entidades se muestra a la
   usuaria y se persiste solo tras su confirmación.
8. **Identidad por número de celular.** Sin cédula, sin dirección
   (minimización, Ley 1581 de 2012).
9. **Las intenciones se resuelven con function calling**, no con un
   clasificador aparte.

---

## 5. Casos de uso

| ID | Nombre | Precondición |
|---|---|---|
| CU1 | Iniciar y autorizar datos | Primer contacto |
| CU2 | Consultar orientación agroecológica | Consentimiento (CU1) |
| CU3 | Registrar información de la huerta | Consentimiento (CU1) |

**El CU3 tiene dos entradas desde el ADR-0016.** Al aceptar el
consentimiento arranca un **onboarding de tres preguntas cerradas** —nombre
de pila, barrio y nombre de la huerta, una por mensaje— que cierra con los
botones del registro y **crea la fila de `huerta`**. Después, lo que ella
vaya contando lo atiende el CU3 conversacional de siempre, que ya solo
añade cultivos. Consecuencia que hay que tener presente: **existir en
`huerta` significa ahora «completó el onboarding»**, no «registró algo», y
una huerta sin cultivos es lo normal.
| CU4 | Consultar qué siembran otras huertas | Consentimiento (CU1) + datos existentes |
| CU5 | Pedir ayuda | Ninguna (contenido estático) |
| CU6 | Onboarding | Consentimiento (CU1) |
| CU7 | Buscar un cultivo concreto en otras huertas | Consentimiento (CU1) + datos existentes |
| CU8 | Consultar mi propia huerta | Consentimiento (CU1) + onboarding (CU6) |

**Son ocho, no cinco, y tres son posteriores a la Fase 2.** El **CU6
(Onboarding)** lo especifica el documento de grado en su §3.6; aquí es lo
que el ADR-0016 llama «la segunda entrada del CU3». El **CU7** se separó
del CU4 el 08/09/2026 (ADR-0021), y el **CU8** se añadió el 09/09/2026
(ADR-0022) porque ninguna fase previó que ella quisiera consultar sus
propios datos: al preguntar «qué tengo sembrado» el agente no llamaba a
nada y respondía de la memoria, nombrando **solo el último cultivo**.

**El CU4 y el CU7 son la misma herramienta y caminos distintos.** El CU4 es
un **listado** —«¿qué están sembrando las otras huertas?»— que compone el
**código**, sale de tres en tres y no consulta la colección vectorial. El
CU7 es una **búsqueda** —«¿alguien más siembra tomate?»— que sí usa la
similitud, comprueba después que la especie esté de verdad en la huerta y
redacta con el modelo. Los separa el parámetro `especie`, que rellena el
agente **antes** de recuperar: deducirlo después —mirando si la búsqueda
encontró algo— hacía que preguntar por un cultivo que nadie tiene se
respondiera con un listado de huertas que no lo tienen.

**Herramientas del agente — son cinco, no tres** (ADR-0013, ADR-0022):
`registrar_huerta`, `consultar_orientacion`, `consultar_comunidad`,
`mostrar_ayuda` y `consultar_mi_huerta`. La cuarta se añadió porque el saludo posterior al
consentimiento no cabía en las otras tres sin incumplir la Fase 2: el
modelo decide **cuándo**, el backend decide **qué** y manda el texto fijo.

**El agente enruta, no relata.** Lo que devuelve cada herramienta se envía
tal cual, sin volver a pasar por el modelo. La jerarquía de fuentes del §6
no vive en el agente, vive en los prompts del CU2 y del CU4: una segunda
pasada a 0.7 podría reescribir una recomendación atada a la guía oficial o
perder la cita, y nada delataría que ocurrió. De ahí que **no haya bucle de
llamadas**: una sola pasada por el modelo.

**Multi-intención:** un mensaje puede disparar varias funciones. Regla de
orquestación: (i) responder primero la necesidad urgente; (ii) ofrecer el
registro como confirmación, sin persistir. El orden lo impone el código,
no el modelo: el registro va siempre el último, porque lleva botones.

**Bienvenida:** el disparador es la intención, no que la usuaria sea nueva. Se
muestra solo ante un saludo o un mensaje sin petición accionable. Es texto fijo
enviado por el backend, **sin pasar por el modelo**.

---

## 6. Modelo de datos

Entidades: `usuario`, `huerta`, `cultivo`, `mensaje`, `fuente`,
`fragmento_oficial`, `fragmento_comunitario`.

Dos colecciones vectoriales **separadas** (no una sola con discriminador):
`fragmento_oficial` (vinculada a `fuente`) y `fragmento_comunitario` (vinculada
a `huerta`).

**Barrios — enumeración cerrada, y desde el 17/08/2026 son 313.** El
catálogo pasó de los siete de la UPZ 84 a **los 312 barrios de la
localidad de Bosa** del listado oficial, más `otro` (ADR-0016). Los
nombres van **en MAYÚSCULA y sin recortar**, tal como vienen del listado.

`Los 3 Sectores` **ya no está**: no aparece en el listado oficial. El
ADR-0002 lo había sembrado dando la razón al anteproyecto §5.3.1 frente
al §7.1; el listado indica que acertaba el §7.1.

No se siembra a mano: `python -m scripts.generar_catalogo_barrios` produce
`db/003_catalogo_barrios_bosa.sql` desde `fuentes/barrios_localidad.json`,
que no se versiona.

---

## 7. Seguridad (Fase 3, §5)

| Capa | Mecanismo |
|---|---|
| 1 | Filtrado por `usuario_id` en cada consulta — **barrera principal** |
| 2 | RLS en Supabase — defensa en profundidad, no barrera primaria (el backend usa service role, que omite RLS) |
| 3 | `telefono_hash` con HMAC-SHA256 + pepper; `nombre_usuario` cifrado con AES-GCM del lado de la aplicación |
| 4 | El flujo del CU4 selecciona solo columnas compartibles |
| 5 | Secretos en variables de entorno; verify token y firma de Meta |
| 6 | Minimización: sin cédula ni dirección |

**No cifres la información agronómica.** Alimenta la búsqueda vectorial y
cifrarla rompe la recuperación.

**`PHONE_HASH_PEPPER` y `NAME_ENCRYPTION_KEY` son críticos.** Si el pepper
cambia, los números entrantes dejan de coincidir con los hashes guardados y las
usuarias registradas dejan de ser reconocidas.

**Límite declarado:** esto no es cifrado de conocimiento cero. El operador del
backend tiene las claves en tiempo de ejecución, y los mensajes viajan en claro
por los servidores de Meta. No atribuyas al sistema garantías que no tiene.

---

## 8. Parámetros del modelo

**Valores vigentes**, que no todos son los de la Fase 4. Los que cambiaron
llevan el ADR que lo justifica.

| Tarea | Parámetro | Valor |
|---|---|---|
| **Todas** | **Modelo generativo** | **`gemini-3.6-flash`**, y lo manda `GEMINI_GENERATIVE_MODEL` de Railway. El defecto de `config.py` la copia |
| Conversación (agente) | Temperatura | 0.7 |
| Extracción de entidades | Temperatura | 0.1 (fijo, formato estricto) |
| Desambiguación de barrio | Temperatura | 0.1 (ADR-0016, mismo criterio) |
| Redacción RAG y comunidad | Temperatura | 0.4 |
| Transcripción de voz | Temperatura | 0.0 — **no está en la Fase 4**, es anterior a la entrada por voz |
| Recuperación oficial | Umbral de similitud (coseno) | **0.66** desde el 19/08/2026; fue 0.7 y luego 0.68 (ADR-0010) |
| Recuperación comunitaria | Umbral propio | **0.65** (ADR-0011) |
| Recuperación | top-k | 4 por colección |
| Listado del CU4 | Huertas por tanda / cultivos por huerta | **3 / 5** (ADR-0021). Perillas propias: **no** reusan el top-k, que gobierna el contexto del CU2 |
| Memoria | Ventana de mensajes | 10 mensajes, no turnos; el último es el de ella |
| Ingesta | Fragmento / solape | 300–500 / 50 tokens, midiendo tokens de verdad (ADR-0009). La ratio car./token es **por documento** y vive en el catálogo (ADR-0014) |

Salvo la extracción, todos son calibrables durante las pruebas (Fase 7).
Los umbrales, el top-k, la ventana y el modelo generativo son variables de
entorno con valor por defecto en `app/config.py`: se pueden ajustar en
Railway sin desplegar. **El modelo de embeddings no**, y es deliberado
(ADR-0007).

**El modelo generativo lo manda `GEMINI_GENERATIVE_MODEL` de Railway, y
todo lo demás la copia.** Hoy vale **`gemini-3.6-flash`**, y el defecto de
`app/config.py` dice lo mismo a propósito. **Al cambiarlo en Railway,
cámbialo también** en `config.py`, en `CLAUDE.md` (§8 y §10), en este
archivo y en `docs/ESTADO.md`.

No es burocracia. El 08/09/2026 había **tres valores y ninguno acertaba**:
los documentos daban por corriendo `gemini-3.5-flash-lite` desde el 19/08,
`config.py` declaraba `gemini-3.6-flash` y Railway corría
`gemini-2.5-flash`. Con eso se midió el enrutamiento contra dos modelos que
no eran producción, y la medición no valía.

**El modelo decide cuánto acierta el enrutamiento**, y está medido. Mismas
19 frases, 4 repeticiones, mismo prompt:

| Modelo | Enrutamientos correctos |
|---|---|
| `gemini-2.5-flash` | **50/76 (66 %)** |
| `gemini-3.5-flash-lite` | 76/76 (100 %) |
| `gemini-3.6-flash` | 76/76 (100 %) |

Los 26 fallos del 2.5 son **todos** «no llamó a ninguna herramienta» —ni
uno fue a la herramienta equivocada—, incluido `"hola"` 4 de 4. Y ahí
`agente.py` manda el texto que escribió el modelo, **saltándose el CU2
entero**: sin RAG, sin cita y sin la advertencia médica del ADR-0015.

**Los dos umbrales están medidos contra el corpus real y no sobreviven a un
cambio de corpus.** El del CU2 tenía un margen de **una centésima**, y el
ADR-0013 añadió que ese margen no aguanta que el agente recorte la
consulta.

**El umbral bajó a 0.66 el 19/08/2026**, tras medir las 81 consultas
reales de las dos pruebas con celular contra el corpus ya limpio de
índices. Baja porque quitar los índices bajó las similitudes de las
consultas que los recuperaban, y varias legítimas quedaron rozando el
0.68. **Sigue sin ser una calibración cerrada:** falta etiquetar leyendo
el fragmento de cada consulta, y `jbb_practicas_2022` está desviada. Lo que sí se midió al ampliar es que
la consulta insignia del CU2 subió de 0.6911 a 0.7231 y que las siete
consultas cubiertas de la prueba real pasan el umbral, cuando antes la peor
se quedaba en 0.6584. **Revalidarlo es lo primero que falta de la Fase 7**,
con `scripts/calibrar_umbral_real.py`, cuyas etiquetas
`CUBIERTA`/`DESCUBIERTA` también quedaron viejas: varias consultas que el
corpus no cubría ahora sí las cubre.

---

## 9. Correcciones vigentes sobre los documentos

Los `.docx` de `docs/` tienen puntos superados. **Prevalece lo que sigue.**

1. **Modelo de embeddings.** Los documentos citan `text-embedding-004` con 768
   dimensiones. Ese modelo fue dado de baja. Usa **`gemini-embedding-001` con
   `output_dimensionality=768`**. Motivo del truncado: pgvector solo indexa
   hasta 2000 dimensiones con el tipo `vector`, y el modelo devuelve 3072 por
   defecto. No mezcles embeddings de modelos distintos: los espacios
   vectoriales son incompatibles y habría que re-vectorizar todo.
2. **Procesamiento asíncrono.** El diagrama C4 de la Fase 3 no lo contempla,
   pero es obligatorio: el webhook responde `200` de inmediato y delega el
   trabajo a segundo plano. Meta reintenta si tardas, y el pipeline completo
   (transcripción + function calling + RAG) excede ese margen. Sin esto hay
   respuestas y registros duplicados. Se acompaña de **idempotencia por
   `wamid`**.
3. **Entrada por voz.** El anteproyecto la excluía (§7.2) y la listaba como
   trabajo futuro (§8). La Fase 2 la incorporó al alcance. La **respuesta** por
   voz y la búsqueda en internet siguen fuera.
4. **Presupuesto.** Railway no tiene plan gratuito real para un servicio
   permanente; hay que contar Hobby (USD 5/mes) durante la ejecución.
5. **El SDK trae *automatic function calling* activado.** Hay que
   desactivarlo con `types.AutomaticFunctionCallingConfig(disable=True)`
   —verificado en `google-genai 2.14.0`— y orquestar las llamadas a mano.
   Sin eso el modelo ejecuta `registrar_huerta` por su cuenta y se salta
   los botones, rompiendo el §4.7. Ya está hecho en `app/agent/agente.py`;
   **no lo quites** (ADR-0013).
6. **El `wamid` nunca en claro, tampoco en la base.** Cerrado del todo el
   15/08/2026 con la migración `006`: ya no queda ninguna columna `wamid`
   en el esquema. Ver el §11 y el ADR-0012.
7. **`mensaje.contenido` guarda la conversación sin cifrar**, siguiendo la
   Fase 3 §5.2, que solo obliga a cifrar el nombre. Es el primer y único
   sitio donde el texto libre de la usuaria queda guardado de forma
   permanente. Límite declarado en el ADR-0012: la minimización gobierna lo
   que el sistema **pide**, no lo que ella decide contar.
8. **`gemini-2.5-flash` se retira el 16/10/2026**, antes de la Fase 8. El
   modelo generativo debe ser de la serie 3.
9. **El corpus oficial ya no es un documento, son nueve** (ADR-0014), y
   **dos no son del Jardín Botánico**: el manual de compostaje de la FAO y
   un libro de la UNAD. Las fases dan por supuesto una sola entidad; la
   línea que lee la usuaria dirá «Fuente: FAO» cuando toque, y sale de la
   tabla `fuente` por la clave foránea, no del texto vectorizado.
10. **Criterio de recorte al ingerir, fijado el 15/08/2026:** entra lo que
    le dice a una líder de huerta **cómo** hacer algo en Bogotá; sale lo
    que describe dónde más se hace, la política nacional o tecnología que
    ella no va a usar. **Ante la duda, se recorta.** Por eso del libro de
    la UNAD entró solo un capítulo de cinco, y del manual de la FAO se
    quitaron las experiencias en otros países.
11. **El extractor devuelve solo especies** (`extraccion_v3.md`). Perdió
    el barrio y el nombre de la huerta con el ADR-0016 —los fija el
    onboarding, y volver a extraerlos del texto libre solo arriesgaría
    pisar lo que ella confirmó—, y perdió **la fecha de siembra** con el
    ADR-0018. La Fase 4, Tabla 3, incluye las tres cosas. Por lo primero
    ya no lee el catálogo de barrios, cuyo enum de 313 valores viajaba en
    cada mensaje.
    **La fecha salió porque era un dato de solo escritura:** no la leía
    ningún caso de uso, y el ADR-0011 ya había medido que dentro del
    fragmento comunitario empeoraba la recuperación (0.0735 frente a
    0.1166 de separación). Las columnas `fecha_siembra_aprox` y
    `fecha_imprecisa` salieron de `cultivo` en la migración `008`.
12. **El intervalo de 300–500 tokens de la Fase 4 tiene una desviación
    declarada.** Los fragmentos del catálogo de plantas miden unos 183,
    porque una ficha de especie mide eso y respetar el intervalo exigiría
    meter dos plantas en el mismo fragmento. En un documento que atribuye
    usos medicinales, esa mezcla es el peor fallo posible. El intervalo es
    un medio para que el fragmento sea una unidad con sentido; ahí la
    unidad con sentido es más corta.

---

## 10. Estado de la infraestructura

- **Meta:** app creada, número de prueba operativo, token permanente de usuario
  del sistema generado. Restricción de portfolio apelada; **la revisión sigue
  abierta**, así que el acceso puede considerarse provisional.
- **Número de prueba:** admite un máximo de **5 destinatarios verificados**.
  Está previsto migrar a un número propio con SIM nueva para la Fase 8. El
  `PHONE_NUMBER_ID` cambia al migrar — **nunca lo escribas en el código**.
- **Supabase:** operativo. PostgreSQL 17.6, RLS activo sin políticas.
  Conexión por **session pooler, puerto 5432**. **765 fragmentos oficiales
  en nueve fuentes** desde el 19/08/2026. Escribir ahí cambia lo que
  responde el bot **en el acto**, con o sin despliegue: Railway lee esta
  misma base. Al 08/09/2026 hay **4 usuarias, 4 huertas con 13 cultivos** y
  sus fragmentos comunitarios.
- **Migraciones aplicadas: hasta la `008`.** Comprobado el 08/09/2026
  contra `information_schema` —la columna `fecha_siembra_aprox` ya no
  existe—, lo que cierra la duda que este archivo arrastraba. **La `009`
  está sin correr**, y el listado del CU4 la necesita en cuanto haya más
  huertas que `CU4_HUERTAS_POR_TANDA`.
- **Railway:** desplegado y con el servicio en marcha. `/health` dice qué
  commit está corriendo, así que confirmar un despliegue no exige mandar un
  WhatsApp. **`/health` dice también qué modelo generativo corre**, desde
  el 08/09/2026: es la forma de comprobarlo sin preguntar. Hoy vale
  `gemini-3.6-flash`, igual que el defecto del repositorio (§8).
- **Pendiente del autor, y urgente:** purgar los registros de Railway
  anteriores al 30/07/2026, que contienen su número de teléfono.

---

## 11. Convenciones de código

- **Español** en nombres de funciones, comentarios, mensajes de log y docstrings.
- Los mensajes al usuario van en español colombiano, trato de **usted**, frases
  cortas, sin tecnicismos, máximo 6–8 líneas por mensaje.
- **Nunca registres en logs** el número de teléfono en claro ni el contenido de
  los mensajes. Registra metadatos: tipo, longitudes y la **referencia** del
  mensaje (`referencia_wamid`).
- **El `wamid` no va nunca a la bitácora ni a la base en claro.** Contiene el
  teléfono del remitente en ASCII, recuperable con un `base64 -d`
  (comprobado el 30/07/2026). Para registrar usa `referencia_wamid`; para
  almacenar o comparar, `huella_wamid`. Aplica igual al `wamid` de los
  mensajes que envías, que lleva el número del destinatario.
- Secretos solo por variables de entorno. `.env` nunca se versiona.
- Los prompts viven en `app/agent/prompts/` como archivos versionados
  (`agente_v1.md`, `extraccion_v2.md`, `barrio_v1.md`,
  `redaccion_rag_v1.md`, `redaccion_comunidad_v2.md`,
  `respuesta_general_v1.md`), conforme a la
  práctica de versionamiento
  declarada en la metodología. **Se rellenan con `str.format`: una llave
  literal rompe la carga con un `KeyError`.** El del agente no lleva huecos
  y se carga tal cual, a propósito.
- Un componente, una responsabilidad — según la Tabla 2 de la Fase 3.
- **Enviar y recordar van juntos.** Después de la compuerta se responde con
  `memoria.responder`, no con `whatsapp.enviar_texto`: un envío sin
  registrar deja en la memoria un hueco que el agente no puede detectar
  (ADR-0012). Antes de la compuerta sí se envía directo, porque ahí no hay
  nada que recordar.
- **Los scripts de `scripts/` que escriben en la base crean datos
  temporales y los borran en un `finally`**, con teléfonos que empiezan por
  `57000000`. Hay **una fila real** en `usuario`, la del celular de pruebas
  del autor: no la toques.
- **Ninguna fuente oficial se ingiere a mano.** Se declara en
  `scripts/catalogo_fuentes.py` y se ingiere con
  `python -m scripts.ingesta_fuente --fuente <clave>` (ADR-0014). Los PDF
  no se versionan: `fuentes/` está en el `.gitignore` y el script los
  vuelve a descargar de la URL registrada. **Sin URL no se ingiere**, y el
  script lo comprueba.
- **Los parámetros del catálogo son mediciones, no gustos.** Antes de
  ingerir algo nuevo: `--detectar-folio`, `--simular` y `--medir-tokens`.
  La ratio caracteres/token de un documento **no transfiere a otro**, y
  `ratio_medida=False` bloquea la ingesta real hasta que se mida.
- **Reingerir siempre con `--reingerir`,** que reemplaza en una sola
  transacción. Y comprueba la regresión: cualquier cambio en la tubería de
  ingesta tiene que seguir dando los mismos fragmentos en las fuentes ya
  ingeridas —81, 62, 220, 30, 46, 120, 68, 92, 46— porque ese corpus es el
  que sostiene la calibración.
  **`jbb_practicas_2022` está desviada y no es culpa de nadie de hoy:** en
  la base hay 62 fragmentos y el código actual produce 83, comprobado el
  19/08/2026 revirtiendo el árbol a `b159cd2`. No se ha reingerido para no
  cambiar el corpus más de lo pedido, pero **ese 62 no se puede reproducir**
  y hay que resolverlo antes de dar la calibración por buena.

---

## 12. Cómo trabajar conmigo

- **Un paso a la vez.** No adelantes fases ni implementes de más.
- **Explica antes de codificar** cuando la decisión sea arquitectónica.
- **Sé crítico.** Si una instrucción mía tiene un fallo lógico o técnico,
  dímelo antes de ejecutarla. No me des la razón por defecto.
- **No inventes.** Si no sabes si una API o un parámetro existe en la versión
  vigente, dilo y verifícalo en la documentación oficial en lugar de suponer.
- **Trazabilidad.** Cada decisión de implementación debe poder rastrearse hasta
  una fase documentada. Si introduces algo nuevo, déjalo anotado en
  `docs/adr/` para poder incorporarlo al documento de grado.
- **Refactoriza al terminar, siempre.** Antes de dar algo por hecho, vuelve
  sobre lo que escribiste y quítale lo que sobra. **Toda función, script y
  archivo tiene que servir para algo; lo que no sirve se borra.** Ni código
  duplicado, ni restos «por si acaso», ni cosas que se quedan porque cuesta
  decidir.
  Borrar aquí es barato, y por eso no hay excusa para no hacerlo: **el
  historial de git lo conserva todo**, y de ahí salen los anexos del
  documento de grado. El 08/09/2026 se fueron así nueve scripts y 1.798
  líneas, tres de los cuales llevaban meses rotos sin que nadie lo supiera.
  «Servir para algo» incluye dos casos que no se ejecutan a diario y sí
  sirven: la herramienta que es lo único que comprueba una cadena entera
  —`scripts/spike_despachador.py`— y los prompts versionados del §11,
  porque el versionamiento es una práctica declarada en la metodología. La
  prueba es sencilla: **di en una frase para qué sirve.** Si no te sale la
  frase, bórralo.
- **Mide reproduciendo las condiciones de producción.** Es el error que más
  caro ha salido, y ya van tres veces: el umbral de 0.7 se validó contra
  documentos escritos a mano y se cayó contra el corpus real (ADR-0010); el
  del CU4 se midió sobre todas las huertas cuando en producción se excluye
  la de quien pregunta (ADR-0011); y el de 0.68 se calibró sobre mensajes
  completos, pero el agente puede recortar la consulta (ADR-0013). **Un
  número medido sobre un montaje que no es producción no vale.** Y su
  recíproco: si ya existe una medición, producción tiene que conservar las
  condiciones en las que se hizo. **Van cuatro:** el 15/08/2026 la ingesta
  del ADR-0014 multiplicó el corpus por nueve y dejó vieja la calibración
  del umbral que se acababa de medir con consultas reales.
- **Un buen indicador puede estar midiendo lo que no es.** Con la
  extracción de *Sembrando Biodiversidad* desordenada, el troceo daba 232
  fragmentos y **99 % dentro del intervalo objetivo** —la mejor
  distribución de todo el corpus— mientras el nombre de la especie salía
  detrás de su propio contenido. Antes de celebrar un número, mira el
  texto.
  **Van dos, y la segunda se presentó como resultado antes de
  desglosarla:** el 19/08 la limpieza de índices se anunció con un «25 %
  de las consultas mejoran», y ese 25 % contaba consultas cuya
  *recuperación* cambió, no respuestas que la usuaria fuera a notar
  mejores. Al desglosarlo, la mayoría eran barrios, saludos y mensajes del
  CU3 y CU4, **que nunca llegan al CU2**; consultas reales del CU2 con el
  índice como mejor fragmento había **dos**. Antes de dar un porcentaje,
  comprueba que el denominador sea lo que le importa a la usuaria.
- **Para buscar defectos en un texto extraído, inventaría; no busques
  sospechosos.** En el Protocolo de espacio público, buscar caracteres
  raros encontró tres de ocho. Arreglados esos tres el texto ya *parecía*
  correcto y seguía diciendo «a travØs». Solo el inventario completo de
  caracteres destapó el resto.
- **No des por bueno un resultado del agente a la primera.** Corre a
  temperatura 0.7 y el enrutamiento no es determinista. Un fallo aislado en
  un spike no es una medida; repite antes de diagnosticar.
