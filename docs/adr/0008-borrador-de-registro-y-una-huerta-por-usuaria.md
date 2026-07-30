# ADR-0008. Borrador de registro en la base, y una huerta por usuaria

- **Estado:** Aceptada
- **Fecha:** 2026-07-30
- **Fase:** 5 (implementa el CU3)
- **Depende de:** [ADR-0004](0004-cultivo-y-fragmento-comunitario.md)

## Contexto

El CU3 exige mostrar lo extraído y persistir **solo tras la confirmación**
de la usuaria (CLAUDE.md §4.7). Al implementarlo aparecieron cuatro
cuestiones que ninguna fase resuelve.

La primera es la que fuerza las demás: **entre el resumen y el botón hay dos
mensajes de WhatsApp distintos**, y la respuesta de un botón solo trae su
identificador. No hay manera de que traiga los datos de vuelta, así que lo
extraído tiene que esperar en algún sitio entre un mensaje y el siguiente.

## Decisión 1. El borrador espera en la base, no en memoria

Tabla `registro_pendiente`
([`db/005_registro_pendiente.sql`](../../db/005_registro_pendiente.sql)),
con `usuario_id` como clave primaria —un borrador por usuaria— y la
extracción en `jsonb`.

**Por qué no en memoria.** Un redeploy de Railway borraría el borrador y la
usuaria pulsaría "Sí, guardar" para que no ocurriera nada. Es el mismo
defecto que el [ADR-0005](0005-procesamiento-asincrono-e-idempotencia.md)
acaba de retirar de la idempotencia, y aquí sería peor: allí el fallo lo veía
el operador en la bitácora; aquí lo ve ella.

**Por qué no contradice "confirmar antes de guardar".** El borrador no es el
registro:

- no aparece en el CU4 ni se comparte con nadie;
- no entra al RAG;
- caduca a las 24 horas y se limpia al arrancar el servicio;
- solo contiene información agronómica, que va sin cifrar como el resto
  (Fase 3, §5.2), y ningún dato personal.

Lo que la usuaria autoriza al confirmar es la creación de su fila en
`huerta`, y eso sigue ocurriendo únicamente entonces. Conviene enunciarlo
con precisión en el documento de grado: **el dato extraído se persiste antes
de la confirmación; el registro de la huerta, no.**

**Por qué `jsonb` y no columnas.** La forma de lo extraído la fija el prompt
y cambiará durante la calibración de la Fase 7. Una migración de esquema por
cada ajuste del extractor no se sostiene, y el dato es efímero.

## Decisión 2. Una huerta por usuaria: se reutiliza, no se crea otra

El esquema admite varias huertas por usuaria (`huerta.usuario_id` es 1:N),
pero `guardar_huerta` **reutiliza la que ya tenga** y solo crea una si no
hay ninguna.

Motivos:

- El perfil real es una líder con una huerta. Crear otra cada vez que
  menciona un cultivo le fragmentaría los datos.
- La unidad de atribución del CU4 es la huerta
  (`[COMUNITARIO – huerta, barrio]`, ADR-0001), y el ADR-0004 impone **un
  fragmento comunitario por huerta** con un `UNIQUE`. Varias huertas por
  usuaria multiplicarían fragmentos casi idénticos y empeorarían una
  recuperación que ya discrimina poco en la colección comunitaria.

Al reutilizar, un dato nuevo completa el que faltara pero **un valor ausente
no borra lo que ya se sabía** (`coalesce` sobre `nombre_huerta`).

No se cambia el esquema a 1:1: dejar la puerta abierta no cuesta nada y
cerrarla exigiría una migración si en la Fase 8 aparece una usuaria con dos
parcelas.

## Decisión 3. Los cultivos se acumulan al fusionar

La conversación llega a trozos: "sembré lechuga" y después, cuando se le
pregunta el barrio, "en El Regalo". Sin fusionar, la segunda frase perdería
la lechuga.

- El dato nuevo gana; el que falta en el nuevo se conserva del anterior.
- Los **cultivos se acumulan**, sin repetir especie. Corresponde a cómo se
  habla: "también sembré lechuga" añade, no sustituye.

El riesgo es acumular algo que ella no quería. Queda cubierto porque el
resumen muestra la lista completa antes de guardar y puede descartar el
registro entero.

## Decisión 4. El resumen lo compone el código, no el modelo

El texto que se le muestra antes de los botones se arma en
[`app/services/registro.py`](../../app/services/registro.py) a partir de los
datos, **sin pasar por Gemini**.

Es una cuestión de validez del consentimiento, no de coste: ella confirma lo
que va a quedar guardado, así que el texto debe reflejarlo con exactitud. Un
resumen redactado por un modelo podría suavizar, omitir o añadir, y estaría
autorizando algo distinto de lo que vio. Es el mismo criterio por el que la
bienvenida no pasa por el modelo (Fase 2, §4).

La marca de imprecisión de la Fase 4, Tabla 3, **se le muestra** —"marzo de
2026 (más o menos)"— en lugar de esconderse: es la ocasión de corregir una
fecha que el modelo estimó.

## Decisión 5. Sin barrio no hay botones, y se pregunta sin menú

`huerta.barrio_id` es obligatoria, así que sin barrio no se puede crear la
fila. Cuando la extracción no lo trae, el flujo **no ofrece la
confirmación**: pregunta el barrio en lenguaje natural y deja el borrador
esperando.

No se le presenta la lista de ocho barrios como botones ni como menú, aunque
sea un campo cerrado: WhatsApp admite tres botones por mensaje y un menú de
navegación es justo la barrera que el diseño elimina (Fase 2, §1). El enum
lo aplica la salida estructurada del extractor, no la interfaz.

## Consecuencias

- El CU3 queda completo y la Fase 5 cerrada.
- `registro_pendiente` es la segunda tabla que se limpia al arrancar, junto
  con `idempotencia_webhook`.
- **Pendiente para la Fase 6 (ADR-0004):** al confirmar hay que regenerar el
  `fragmento_comunitario` de esa huerta, texto y embedding, o el CU4 no la
  incluirá. Está señalado con un TODO en `guardar_huerta`.
- Mientras no exista el agente, el despachador trata **cualquier** mensaje
  libre como posible registro. Es provisional: en la Fase 6 el function
  calling decide entre registrar, consultar orientación o consultar a la
  comunidad. Hoy una consulta agronómica que no mencione cultivos no
  produce registro, pero una que los mencione —"a mi tomate le salieron
  bichos"— puede ofrecer guardar el tomate. La extracción distingue bien la
  pregunta pura; la mezcla es cosa del agente.

## Alternativas descartadas

- **Guardar el borrador en memoria.** Descartada arriba.
- **Codificar los datos en el identificador del botón.** WhatsApp lo limita
  a 256 caracteres, no cabe una lista de cultivos, y pondría los datos a
  viajar en el propio mensaje.
- **Reextraer del historial al confirmar.** Exigiría una segunda llamada al
  modelo que podría dar un resultado distinto del que ella vio y aprobó, lo
  que rompe el sentido de la confirmación.
- **Crear una huerta nueva en cada registro.** Fragmenta los datos y choca
  con el `UNIQUE` de `fragmento_comunitario` del ADR-0004.
- **Sustituir los cultivos en lugar de acumularlos.** Perdería lo dicho en
  el mensaje anterior, que es justo el caso que la fusión existe para
  cubrir.
