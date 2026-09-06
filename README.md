# Chatbot de huertas urbanas — Bosa

Prototipo de agente conversacional sobre WhatsApp para el apoyo a la
creación y gestión de huertas urbanas, en el marco del Programa 25 del
Plan de Desarrollo Local de Bosa 2024-2028, que fija la meta de 500
huertas en la localidad.

Trabajo de grado — Especialización en Ingeniería de Software,
Universidad Distrital Francisco José de Caldas.

**Las usuarias son líderes y propietarias de huerta, mayoritariamente
adultas mayores y de mediana edad, con apropiación tecnológica limitada al
uso básico del celular.** Ese perfil condiciona todas las decisiones de
diseño: WhatsApp como único canal, lenguaje natural en lugar de menús, y
botones solo en los dos momentos binarios del flujo. El criterio de éxito
es una puntuación SUS igual o superior a 68 en la evaluación con 5 a 7
usuarias de la comunidad.

## Estado

**Fase 7 — calibración y pruebas.** Los cinco casos de uso están
construidos, desplegados y probados desde un celular real. Lo que queda es
medirlos y calibrarlos.

Lo que **no** está cerrado, y conviene saberlo antes de leer cualquier
número de este repositorio:

- **El umbral de similitud del CU2 (0.66) no es una calibración cerrada.**
  Está medido contra 81 consultas reales, pero falta etiquetarlas leyendo
  el fragmento recuperado de cada una.
- **El corpus no es del todo reproducible.** La fuente
  `jbb_practicas_2022` tiene 62 fragmentos en la base y el código produce
  83. Mientras siga así, toda calibración hereda esa debilidad.
- **El CU4 no se ha ejercitado de verdad**, y no por un fallo: excluye a
  propósito la huerta de quien pregunta, y hasta ahora nunca ha habido más
  de una registrada. Necesita las 5–7 huertas de la evaluación.

El detalle, con las mediciones que respaldan cada decisión, está en
[`docs/ESTADO.md`](docs/ESTADO.md).

## Qué hace

| ID | Caso de uso | Precondición |
|---|---|---|
| CU1 | Iniciar y autorizar el tratamiento de datos | Primer contacto |
| CU2 | Consultar orientación agroecológica sobre fuentes oficiales | Consentimiento |
| CU3 | Registrar la información de su huerta | Consentimiento |
| CU4 | Consultar qué siembran otras huertas | Consentimiento + datos existentes |
| CU5 | Pedir ayuda | Ninguna |

Acepta mensajes escritos y notas de voz. La respuesta es siempre escrita:
la salida por voz y la búsqueda en internet están fuera del alcance.

## Cómo se atiende un mensaje

El orden importa y está fijado en
[`app/services/dispatcher.py`](app/services/dispatcher.py):

1. **El webhook valida la firma de Meta y responde `200` de inmediato**,
   delegando el trabajo a segundo plano. El pipeline completo excede el
   margen de reintento de Meta; procesarlo dentro de la petición produce
   respuestas y registros duplicados.
2. **Idempotencia por huella del `wamid`**, con dos estados en base.
   `procesado` se marca solo al terminar bien: si el trabajo falla, la
   fila queda en `recibido` y el reintento de Meta lo recupera.
3. **Compuerta de consentimiento (CU1).** Sin autorización solo se
   atienden el saludo y la ayuda, detectados por palabras clave **sin
   pasar por el modelo** — mandar el mensaje a Gemini ya sería tratamiento
   de datos. Mientras no autorice no se persiste nada, tampoco el rechazo.
4. **Normalización de la entrada.** Si es una nota de voz se le acusa
   recibo y se transcribe **una sola vez**, antes de interpretar nada. De
   aquí en adelante da igual cómo llegó el mensaje.
5. **Memoria.** El mensaje entrante se registra antes de atenderlo, así
   que la ventana de diez mensajes termina siempre en lo que ella acaba de
   decir.
6. **Onboarding, botones del registro, o el agente.** El onboarding de
   tres preguntas cerradas va antes que todo lo demás; las pulsaciones de
   botón se resuelven sin modelo, porque son respuesta a algo que ya se
   preguntó; el resto lo decide el agente.

### El agente

Un modelo con **function calling** elige entre cuatro herramientas
—`consultar_orientacion`, `consultar_comunidad`, `registrar_huerta` y
`mostrar_ayuda`— y el backend ejecuta lo que pidió.

- **Enruta, no relata.** Lo que devuelve cada herramienta se envía tal
  cual, sin volver a pasar por el modelo. Una segunda pasada a temperatura
  0.7 podría reescribir una recomendación atada a la guía oficial o perder
  la cita, y nada delataría que ocurrió. De ahí que no haya bucle de
  llamadas: una sola pasada.
- **El *automatic function calling* del SDK está desactivado a
  propósito.** Con él, el modelo ejecutaría `registrar_huerta` por su
  cuenta y se saltaría los botones de confirmación.
- **No extrae datos.** `registrar_huerta` no lleva parámetros: la
  extracción corre aparte, a temperatura 0.1 y sobre el mensaje literal.
  Si los datos vinieran del modelo, «cebolla larga» volvería como
  «cebolla».
- **Multi-intención:** un mensaje puede disparar varias funciones. El
  orden lo impone el código, no el modelo — el registro va siempre el
  último, porque lleva botones.

### Jerarquía de fuentes

Fuente oficial curada > dato comunitario, siempre atribuido > conocimiento
del modelo, **sin atribución ninguna**. La ausencia de cita es justamente
lo que le permite a la usuaria distinguir un dato verificado de uno que no
lo está, así que los dos caminos nunca se mezclan en un mismo mensaje: o
se cita toda la respuesta, o no se cita absolutamente nada, y quien elige
el camino es el código mirando si la recuperación trajo algo.

El umbral de similitud **decide citar o no citar**, no responder o callar.
Y toda respuesta del CU2 que hable de salud lleva advertencia, la ponga el
camino que la ponga: las fuentes oficiales traen usos medicinales y
toxicidad, y avalan la botánica, no un consejo médico para una persona
concreta.

## Arquitectura

Python + FastAPI sobre Railway, PostgreSQL con pgvector en Supabase, API
de Gemini para el modelo de lenguaje y los embeddings, y la Meta Cloud API
como canal.

**Sin framework de orquestación.** Las fases de diseño preveían LangChain,
y no se usa: no está en `requirements.txt` ni se importa en ninguna parte.
El agente son unas 390 líneas sobre el SDK `google-genai` con las llamadas
a función orquestadas a mano, y esa decisión no fue de estilo: el
*automatic function calling* del SDK hay que desactivarlo para no saltarse
los botones de confirmación, y el orden de ejecución —el registro siempre
el último— lo impone el código. Un framework por encima habría que
desmontarlo justo en los puntos donde se toman las decisiones. Es una
desviación declarada respecto de la Fase 3.

    app/
      main.py                       FastAPI y /health
      config.py                     Variables de entorno y sus validaciones
      textos.py                     Todo lo que el backend dice sin modelo
      api/webhook.py                GET de verificación + POST firmado
      core/
        signature.py                Firma X-Hub-Signature-256 de Meta
        identidad.py                HMAC del teléfono y cifrado del nombre
        basedatos.py                Pool de asyncpg contra Supabase
        gemini.py                   Cliente único; modelo de embeddings fijo
      services/
        dispatcher.py               Orden del flujo e idempotencia
        consentimiento.py           CU1 — la compuerta
        onboarding.py               Las tres preguntas cerradas del CU3
        registro.py                 CU3 — borrador, botones y persistencia
        extraccion.py               Los cultivos, a temperatura 0.1
        orientacion.py              CU2 — RAG y respaldo del modelo
        comunidad.py                CU4 — qué siembran otras huertas
        recuperacion.py             Búsqueda por similitud y atribución
        embeddings.py               Vectorización y normalización L2
        fragmento_comunitario.py    El derivado que alimenta el CU4
        memoria.py                  Ventana de conversación; enviar y recordar
        normalizacion.py            Transcripción de la nota de voz
        media.py                    Descarga del audio desde Meta
        espera.py                   Acuse de la nota de voz
        whatsapp.py                 Única salida hacia la usuaria
        repositorio.py              Único acceso a la base; filtra por usuario
      agent/
        agente.py                   Function calling y orquestación
        plantillas.py               Carga de los prompts
        prompts/                    Prompts versionados, uno por archivo

Los prompts viven en archivos y no en cadenas dentro del código, porque el
versionamiento de prompts es una práctica declarada en la metodología: la
comparación entre dos versiones tiene que poder leerse en el historial de
git. Se rellenan con `str.format`, así que **una llave literal rompe la
carga con un `KeyError`**.

## Datos

Once tablas. Las siete entidades de la Fase 3 —`usuario`, `huerta`,
`cultivo`, `mensaje`, `fuente`, `fragmento_oficial`,
`fragmento_comunitario`—, el catálogo `barrio`, y tres tablas de estado
efímero: idempotencia del webhook, borrador del registro y onboarding en
curso.

**Dos colecciones vectoriales separadas**, no una sola con discriminador:
`fragmento_oficial` cuelga de `fuente` y `fragmento_comunitario` de
`huerta`.

- **Corpus oficial: 765 fragmentos de nueve fuentes.** Siete son del
  Jardín Botánico de Bogotá, una de la FAO y una de la UNAD. La entidad
  que lee la usuaria sale de la tabla `fuente` por la clave foránea, no
  del texto vectorizado.
- **Fragmento comunitario: solo las especies** —`"tomate, cilantro,
  lechuga"`—. Ni nombre de huerta, ni barrio, ni fechas: lo que se repite
  en todos los fragmentos infla por igual la similitud de todos y destruye
  la capacidad de distinguirlos. El nombre y el barrio llegan por la clave
  foránea al componer la respuesta.
- **Catálogo de barrios: 313** — los 312 de la localidad de Bosa según el
  listado oficial, más `otro`, en mayúscula y sin recortar. No se siembra
  a mano: lo genera `scripts/generar_catalogo_barrios.py`.

El barrio **no filtra** la recuperación comunitaria; solo atribuye.

## Seguridad, y sus límites

| Capa | Mecanismo |
|---|---|
| 1 | Filtrado por `usuario_id` en cada consulta — **la barrera real** |
| 2 | RLS activo en Supabase, sin políticas — defensa en profundidad |
| 3 | `telefono_hash` con HMAC-SHA256 + pepper; nombre cifrado con AES-GCM |
| 4 | El CU4 selecciona solo columnas compartibles |
| 5 | Secretos en variables de entorno; verify token y firma de Meta |
| 6 | Minimización: identidad por celular, sin cédula ni dirección |

El backend usa la clave de *service role*, que omite el RLS por diseño:
por eso la barrera primaria es la capa 1 y no la 2.

**La información agronómica no se cifra**, a propósito: alimenta la
búsqueda vectorial y cifrarla rompería la recuperación.

**El `wamid` nunca se guarda ni se registra en claro.** Contiene el
teléfono del remitente en ASCII, recuperable con un `base64 -d`. Para la
bitácora se usa `referencia_wamid`; para almacenar y comparar,
`huella_wamid`.

Tres límites que conviene declarar y no maquillar:

- **Esto no es cifrado de conocimiento cero.** El operador del backend
  tiene las claves en tiempo de ejecución, y los mensajes viajan en claro
  por los servidores de Meta.
- **`mensaje.contenido` guarda la conversación sin cifrar.** Es el único
  sitio donde el texto libre de la usuaria queda almacenado de forma
  permanente. La minimización gobierna lo que el sistema *pide*, no lo que
  ella decide contar.
- **`PHONE_HASH_PEPPER` y `NAME_ENCRYPTION_KEY` son irrecuperables.** Si
  el pepper cambia, las usuarias registradas dejan de ser reconocidas.

## Ejecución local

    python -m venv .venv
    .venv\Scripts\activate           # Linux/macOS: source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env             # y completar los valores
    uvicorn app.main:app --reload

Comprobación: <http://localhost:8000/health>, que verifica también la
conexión a Supabase y dice qué commit está corriendo.

**El `.env` debe estar completo o el servicio se niega a arrancar**, y es
deliberado: una clave mal formada fallaría si no al registrar a la primera
usuaria, mucho más tarde y mucho más difícil de diagnosticar. Los valores
y sus avisos están en [`.env.example`](.env.example).

Las dependencias de los scripts van aparte, en
[`requirements-scripts.txt`](requirements-scripts.txt), para que `pypdf`
no se despliegue en Railway: el servicio no abre un PDF nunca.

    pip install -r requirements.txt -r requirements-scripts.txt

Las versiones son **fijas**, no rangos: el prototipo debe comportarse en
la evaluación con usuarias igual que hoy.

## Base de datos

Los archivos de [`db/`](db/) se aplican **en orden** en el editor SQL de
Supabase, y son idempotentes: reejecutarlos no duplica nada.

| Archivo | Contenido |
|---|---|
| `001_esquema.sql` | `pgvector`, las ocho tablas del modelo, índices y disparadores |
| `002_catalogo_barrios.sql` | Siembra inicial de los barrios de la UPZ 84. **Superado por el `003` de Bosa** |
| `003_rls.sql` | Activación de RLS y retirada de privilegios públicos |
| `003_catalogo_barrios_bosa.sql` | Los 312 barrios de Bosa más `otro`. Generado, no escrito a mano (ADR-0016) |
| `004_idempotencia.sql` | Idempotencia del webhook, con dos estados (ADR-0005) |
| `005_registro_pendiente.sql` | Borrador del CU3 a la espera de confirmación (ADR-0008) |
| `006_memoria_mensaje.sql` | El `wamid` sale de `mensaje` y entra la huella (ADR-0012) |
| `007_onboarding_pendiente.sql` | Onboarding en curso (ADR-0016) |
| `008_sin_fecha_de_siembra.sql` | Retira la fecha de siembra de `cultivo` (ADR-0018) |

Dos avisos: **hay dos archivos con el prefijo `003`** —el de RLS y el
catálogo de barrios, que llegó después—, y el `002` quedó superado por ese
catálogo. Y [`db/README.md`](db/README.md) **está desactualizado**: describe
el esquema tal como estaba en la migración `005`.

## Scripts

Todos se ejecutan con `python -m scripts.<nombre>` desde la raíz.
**Los que escriben en la base crean datos temporales y los borran en un
`finally`**, con teléfonos que empiezan por `57000000`.

| Script | Qué hace |
|---|---|
| `ingesta_fuente` | Ingesta de una fuente oficial. `--listar`, `--fuente`, `--detectar-folio`, `--medir-tokens`, `--simular`, `--reingerir` |
| `catalogo_fuentes` | No se ejecuta: es la declaración de las nueve fuentes y sus parámetros medidos |
| `generar_catalogo_barrios` | Escribe `db/003_catalogo_barrios_bosa.sql`. No toca la base |
| `regenerar_fragmentos` | Rehace los fragmentos comunitarios |
| `calibrar_umbral`, `calibrar_fragmento_comunitario` | Las mediciones de los ADR-0010 y 0011 |
| `calibrar_umbral_real` | La revalidación de la Fase 7, con consultas de la prueba real |
| `revisar_prueba_real` | Reconstruye una sesión hecha desde el celular y remide cada consulta. Solo lee |
| `spike_despachador` | La rama completa, entrando por `procesar_evento`. El más útil para comprobar que nada se rompió |
| `spike_agente`, `spike_memoria` | El agente con espías en vez de envíos, y la ventana de memoria |
| `spike_orientacion`, `spike_comunidad` | El CU2 y el CU4 por separado |
| `spike_extraccion`, `spike_transcripcion`, `spike_embeddings` | Piezas sueltas de la Fase 5 |

**Ninguna fuente oficial se ingiere a mano.** Se declara en
`scripts/catalogo_fuentes.py` con sus parámetros, que son mediciones y no
gustos: la ratio caracteres/token de un documento no transfiere a otro, y
`ratio_medida=False` bloquea la ingesta real hasta que se mida. Los PDF no
se versionan; el script los descarga de la URL registrada en `fuente`.

**El corpus vive en Supabase, no en el despliegue.** Ingerir una fuente
cambia lo que responde el bot en el acto, con o sin despliegue, así que
una respuesta rara puede venir de código viejo con corpus nuevo.

## Despliegue

Railway, con el arranque definido en el [`Procfile`](Procfile). Las
credenciales se configuran como variables del servicio y nunca se
versionan. `/health` informa del commit desplegado, así que confirmar un
despliegue no obliga a gastar un mensaje del número de prueba.

Los umbrales, el top-k, la ventana de memoria, el modelo generativo y el
interruptor del respaldo del CU2 son variables de entorno con valor por
defecto en `app/config.py`: se pueden ajustar sin desplegar, que es lo que
la calibración necesita. **El modelo de embeddings no**, y es deliberado:
cambiarlo invalidaría todos los vectores guardados sin dar ningún error,
solo con peor recuperación.

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/ESTADO.md`](docs/ESTADO.md) | Dónde está el trabajo, qué falta y las mediciones que respaldan cada paso |
| [`docs/adr/`](docs/adr/) | Dieciocho decisiones tomadas durante la implementación. Prevalecen sobre los `.docx` |
| [`docs/correcciones-a-los-documentos.md`](docs/correcciones-a-los-documentos.md) | Qué dice cada documento de fase y qué hace el sistema, por fase y sección |
| [`CLAUDE.md`](CLAUDE.md) | Instrucciones de trabajo y decisiones no negociables |
| `docs/*.docx` | Anteproyecto y fases de diseño 2, 3 y 4 |

Los `.docx` son la especificación del sistema, pero tienen puntos
superados por la implementación. Cuando un ADR corrige un documento de
fase, **prevalece el ADR**.

## Sobre este repositorio

Es **público**, y el `.gitignore` está escrito para que siga siéndolo sin
riesgo: deja fuera el `.env`, los PDF de las fuentes oficiales —son
publicaciones de terceros y se descargan de la URL registrada en `fuente`—
y el borrador del documento de grado. Las conversaciones de las pruebas y
los mensajes que nombran un barrio tampoco se versionan.

No lleva archivo de licencia. Es material de un trabajo de grado en curso.
