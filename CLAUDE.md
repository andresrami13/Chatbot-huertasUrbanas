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

**Fase actual: 5 — Configuración de infraestructura y procesamiento base.**

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

**Herramientas del agente:** `registrar_huerta`, `consultar_orientacion`,
`consultar_comunidad`.

**Multi-intención:** un mensaje puede disparar varias funciones. Regla de
orquestación: (i) responder primero la necesidad urgente; (ii) ofrecer el
registro como confirmación, sin persistir; (iii) tratar fechas vagas como
aproximadas y afinarlas en la confirmación.

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

| Tarea | Parámetro | Valor inicial |
|---|---|---|
| Conversación (agente) | Temperatura | 0.7 |
| Extracción de entidades | Temperatura | 0.1 (fijo, formato estricto) |
| Redacción RAG | Temperatura | 0.4 |
| Recuperación | Umbral de similitud (coseno) | 0.7 |
| Recuperación | top-k | 4 por colección |
| Memoria | Ventana de mensajes | 10 |
| Ingesta | Fragmento / solape | 300–500 / 50 tokens |

Salvo la extracción, todos son calibrables durante las pruebas (Fase 7).

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

---

## 10. Estado de la infraestructura

- **Meta:** app creada, número de prueba operativo, token permanente de usuario
  del sistema generado. Restricción de portfolio apelada; **la revisión sigue
  abierta**, así que el acceso puede considerarse provisional.
- **Número de prueba:** admite un máximo de **5 destinatarios verificados**.
  Está previsto migrar a un número propio con SIM nueva para la Fase 8. El
  `PHONE_NUMBER_ID` cambia al migrar — **nunca lo escribas en el código**.
- **Supabase:** pendiente.
- **Railway:** pendiente.

---

## 11. Convenciones de código

- **Español** en nombres de funciones, comentarios, mensajes de log y docstrings.
- Los mensajes al usuario van en español colombiano, trato de **usted**, frases
  cortas, sin tecnicismos, máximo 6–8 líneas por mensaje.
- **Nunca registres en logs** el número de teléfono en claro ni el contenido de
  los mensajes. Registra metadatos: tipo, `wamid`, longitudes.
- Secretos solo por variables de entorno. `.env` nunca se versiona.
- Los prompts viven en `app/agent/prompts/` como archivos versionados
  (`agente_v1.md`, `extraccion_v1.md`, `redaccion_rag_v1.md`), conforme a la
  práctica de versionamiento declarada en la metodología.
- Un componente, una responsabilidad — según la Tabla 2 de la Fase 3.

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
