# CLAUDE.md

Instrucciones de proyecto para Claude Code. Léelas al inicio de cada sesión.

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
| `docs/adr/` | Trece decisiones tomadas al implementar. Prevalecen sobre los `.docx` |

**Fase actual: 6 terminada de construir y desplegada; falta probarla con un
celular real. Después empieza la Fase 7 (calibración y pruebas).** El
detalle está en `docs/ESTADO.md`, sección «Por dónde seguir».

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
4. **Normalización única de la entrada.** Si el mensaje es audio, se transcribe
   una sola vez antes de interpretar la intención. No dupliques transcripción
   por flujo.
5. **Separación de datos.** Lo agronómico (barrio, cultivos, nombre de huerta)
   es compartible y alimenta el RAG. Lo personal (teléfono, nombre) nunca se
   expone a otras usuarias ni entra al RAG.
6. **Jerarquía de fuentes:** fuente oficial curada > dato comunitario (siempre
   atribuido, nunca como instrucción técnica) > conocimiento del modelo (con
   advertencia explícita de que no está verificado). Búsqueda en internet fuera
   de alcance.
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
| CU4 | Consultar qué siembran otras huertas | Consentimiento (CU1) + datos existentes |
| CU5 | Pedir ayuda | Ninguna (contenido estático) |

**Herramientas del agente — son cuatro, no tres** (ADR-0013):
`registrar_huerta`, `consultar_orientacion`, `consultar_comunidad` y
`mostrar_ayuda`. La cuarta se añadió porque el saludo posterior al
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
registro como confirmación, sin persistir; (iii) tratar fechas vagas como
aproximadas y afinarlas en la confirmación. El orden lo impone el código,
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

**Barrios — enumeración cerrada.** Valor abierto rompe el filtro del RAG:

```
Holanda | Los 3 Sectores | El Regalo | El Anhelo | La Cabaña | El Bosque | Santa Fe | otro
```

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
| Conversación (agente) | Temperatura | 0.7 |
| Extracción de entidades | Temperatura | 0.1 (fijo, formato estricto) |
| Redacción RAG y comunidad | Temperatura | 0.4 |
| Transcripción de voz | Temperatura | 0.0 — **no está en la Fase 4**, es anterior a la entrada por voz |
| Recuperación oficial | Umbral de similitud (coseno) | **0.68**, no 0.7 (ADR-0010) |
| Recuperación comunitaria | Umbral propio | **0.65** (ADR-0011) |
| Recuperación | top-k | 4 por colección |
| Memoria | Ventana de mensajes | 10 mensajes, no turnos; el último es el de ella |
| Ingesta | Fragmento / solape | 300–500 / 50 tokens, midiendo tokens de verdad (ADR-0009) |

Salvo la extracción, todos son calibrables durante las pruebas (Fase 7).
Los umbrales, el top-k, la ventana y el modelo generativo son variables de
entorno con valor por defecto en `app/config.py`: se pueden ajustar en
Railway sin desplegar. **El modelo de embeddings no**, y es deliberado
(ADR-0007).

**Los dos umbrales están medidos contra el corpus real y no sobreviven a un
cambio de corpus.** El del CU2 tiene un margen de **una centésima**, y el
ADR-0013 añadió que ese margen no aguanta que el agente recorte la
consulta. Hay que revalidarlos en la Fase 7 con consultas reales.

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
   08/08/2026 con la migración `006`: ya no queda ninguna columna `wamid`
   en el esquema. Ver el §11 y el ADR-0012.
7. **`mensaje.contenido` guarda la conversación sin cifrar**, siguiendo la
   Fase 3 §5.2, que solo obliga a cifrar el nombre. Es el primer y único
   sitio donde el texto libre de la usuaria queda guardado de forma
   permanente. Límite declarado en el ADR-0012: la minimización gobierna lo
   que el sistema **pide**, no lo que ella decide contar.
8. **`gemini-2.5-flash` se retira el 16/10/2026**, antes de la Fase 8. El
   modelo generativo debe ser de la serie 3.

---

## 10. Estado de la infraestructura

- **Meta:** app creada, número de prueba operativo, token permanente de usuario
  del sistema generado. Restricción de portfolio apelada; **la revisión sigue
  abierta**, así que el acceso puede considerarse provisional.
- **Número de prueba:** admite un máximo de **5 destinatarios verificados**.
  Está previsto migrar a un número propio con SIM nueva para la Fase 8. El
  `PHONE_NUMBER_ID` cambia al migrar — **nunca lo escribas en el código**.
- **Supabase:** operativo. PostgreSQL 17.6, seis migraciones aplicadas, RLS
  activo sin políticas. Conexión por **session pooler, puerto 5432**.
- **Railway:** desplegado y con el servicio en marcha. `/health` dice qué
  commit está corriendo, así que confirmar un despliegue no exige mandar un
  WhatsApp.
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
  (`agente_v1.md`, `extraccion_v1.md`, `redaccion_rag_v1.md`,
  `redaccion_comunidad_v1.md`), conforme a la práctica de versionamiento
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
- **Mide reproduciendo las condiciones de producción.** Es el error que más
  caro ha salido, y ya van tres veces: el umbral de 0.7 se validó contra
  documentos escritos a mano y se cayó contra el corpus real (ADR-0010); el
  del CU4 se midió sobre todas las huertas cuando en producción se excluye
  la de quien pregunta (ADR-0011); y el de 0.68 se calibró sobre mensajes
  completos, pero el agente puede recortar la consulta (ADR-0013). **Un
  número medido sobre un montaje que no es producción no vale.** Y su
  recíproco: si ya existe una medición, producción tiene que conservar las
  condiciones en las que se hizo.
- **No des por bueno un resultado del agente a la primera.** Corre a
  temperatura 0.7 y el enrutamiento no es determinista. Un fallo aislado en
  un spike no es una medida; repite antes de diagnosticar.
