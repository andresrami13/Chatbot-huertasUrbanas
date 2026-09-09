"""Agente orquestador con function calling (Fase 2, §4; ADR-0013).

Decide qué necesita la usuaria y llama a la pieza que corresponde. **No
añade capacidades**: el CU2, el CU4 y el CU3 ya estaban construidos y
probados; lo que faltaba era quién elige entre ellos. Es también la única
forma de enrutar el CU4 sin un clasificador aparte (CLAUDE.md §4.9).

## Enruta, no relata

Las herramientas ya producen el texto que la usuaria va a leer, y ese
texto **se envía tal cual**. No vuelve al modelo para que lo redacte de
nuevo.

No es una simplificación, es lo que sostiene la jerarquía de fuentes
(CLAUDE.md §6). La respuesta del CU2 está atada a la guía oficial por su
propio prompt y su temperatura de 0.4: cita la entidad, no añade
conocimiento y no pasa de 80 palabras. Una segunda pasada a 0.7 podría
reescribirla, perder la cita o completar lo que el documento no dice, y
nada en la respuesta delataría que eso pasó. Lo mismo con la atribución
`[COMUNITARIO – huerta, barrio]` del CU4, sin la cual la usuaria creería
que todo se siembra en su barrio (ADR-0001).

De ahí que **no haya bucle de llamadas**: una sola pasada por el modelo,
se ejecuta lo que pidió y se manda lo que devuelve. No hay nada que
realimentar cuando el resultado ya está listo para enviarse. Si en la Fase
7 apareciera un caso donde el agente sí deba comentar un resultado, este
es el punto de extensión.

## AFC desactivado

El SDK trae *automatic function calling* activado por defecto: ejecutaría
las funciones por su cuenta en un bucle interno. Aquí eso rompería el
§4.7, porque el modelo llamaría a `registrar_huerta` y daría el registro
por hecho sin pasar por los botones de confirmación. Se desactiva y las
llamadas se orquestan a mano.

## Lo que el modelo no decide

- **No extrae datos.** `registrar_huerta` no lleva parámetros: la
  extracción sigue donde estaba, a temperatura 0.1 fija y con el enum del
  catálogo (CLAUDE.md §8, ADR-0002), y trabaja sobre el mensaje literal.
  Si los datos vinieran del modelo, "cebolla larga" volvería como
  "cebolla".
- **No escribe la bienvenida.** `mostrar_ayuda` devuelve el texto fijo de
  `textos.py`, sin pasar por el modelo (Fase 2, §4). El modelo decide
  cuándo, no qué dice.
- **No sabe quién pregunta.** El `usuario_id` y el número salen del
  contexto de la conversación, nunca de una respuesta del modelo.
"""

import logging
from uuid import UUID

from google.genai import types

from app import textos
from app.agent.plantillas import cargar_prompt
from app.core.gemini import MODELO_GENERATIVO, obtener_cliente
from app.services.comunidad import consultar_comunidad
from app.services.extraccion import extraer_huerta
from app.services.memoria import responder, ventana
from app.services.orientacion import consultar_orientacion
from app.services.registro import proponer_registro

logger = logging.getLogger(__name__)

# Sin huecos de `str.format`: se carga tal cual. Es deliberado, porque un
# prompt largo lleno de ejemplos es justo donde una llave literal rompería
# la carga (CLAUDE.md §11).
_PROMPT = "agente_v1.md"

# Fase 4 / CLAUDE.md §8. Más alta que la redacción del RAG (0.4) porque
# aquí sí se conversa. Consecuencia que conviene tener presente al probar:
# el enrutamiento **deja de ser determinista**, y el mismo mensaje puede
# tomar caminos distintos en dos intentos.
_TEMPERATURA = 0.7

# Tope de funciones que se ejecutan en un turno. Con cuatro herramientas y
# sin repetidas no debería llegar a tres nunca; está para que un modelo que
# se desboque no produzca una ráfaga de mensajes en el celular de la
# usuaria.
_MAX_LLAMADAS = 3

_ORIENTACION = "consultar_orientacion"
_COMUNIDAD = "consultar_comunidad"
_REGISTRO = "registrar_huerta"
_AYUDA = "mostrar_ayuda"

# El registro va siempre el último, y no en el orden que decida el modelo:
# es el que lleva botones, y los botones tienen que quedar en el último
# mensaje de la pantalla o ella los pulsaría con la respuesta de otra cosa
# encima. Es además la regla de orquestación del CLAUDE.md §5: primero la
# necesidad urgente, después ofrecer el registro.
_ORDEN_EJECUCION = {_ORIENTACION: 0, _COMUNIDAD: 0, _AYUDA: 0, _REGISTRO: 1}


def _esquema_pregunta(descripcion: str) -> types.Schema:
    return types.Schema(
        type=types.Type.OBJECT,
        properties={
            "pregunta": types.Schema(type=types.Type.STRING, description=descripcion)
        },
        required=["pregunta"],
    )


# Las descripciones son parte del prompt, aunque no vivan en el archivo:
# son lo que el modelo lee para elegir. Se mantienen cortas porque
# `agente_v1.md` ya explica los matices.
_HERRAMIENTAS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name=_ORIENTACION,
            description=(
                "Responde una duda sobre cómo cultivar: plagas, riego, abonos, "
                "compost, siembra, cosecha, tierra o semillas. Se apoya en una "
                "guía oficial. Úsela siempre para este tipo de dudas."
            ),
            parameters=_esquema_pregunta(
                "La duda con las palabras de la usuaria, sin el saludo. No la "
                "reescriba ni la traduzca a lenguaje técnico."
            ),
        ),
        types.FunctionDeclaration(
            name=_COMUNIDAD,
            description=(
                "Cuenta qué siembran OTRAS huertas de la zona. Solo para saber "
                "qué hacen los demás, no para resolver dudas de cultivo. "
                "Sirve para dos cosas: enseñarle la lista de las otras huertas "
                "y sus cultivos, y buscar si alguna tiene sembrada una planta "
                "en concreto. Úsela también cuando pida ver más huertas."
            ),
            # `especie` es la bandera que separa el CU4 del CU7 (ADR-0021).
            # Tiene que decidirse ANTES de recuperar: si se dedujera después,
            # mirando si la búsqueda encontró algo, una pregunta por un
            # cultivo que nadie tiene acabaría contestada con un listado de
            # huertas que no lo tienen.
            #
            # El backend la usa solo para elegir la vía y filtrar el
            # resultado. La búsqueda por similitud sigue corriendo sobre la
            # pregunta completa, que es la formulación sobre la que existe la
            # calibración del umbral (ADR-0011) y la que no sufre el recorte
            # que midió el ADR-0013.
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "pregunta": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "La pregunta con las palabras de la usuaria, sin "
                            "el saludo."
                        ),
                    ),
                    "especie": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "SOLO si preguntó por una planta concreta: el "
                            "nombre de esa planta tal como ella lo escribió, "
                            "sin recortarlo ('cebolla larga', no 'cebolla'). "
                            "Déjelo vacío si preguntó en general qué siembran "
                            "las otras huertas o si pidió ver más."
                        ),
                    ),
                },
                required=["pregunta"],
            ),
        ),
        types.FunctionDeclaration(
            name=_REGISTRO,
            description=(
                "Avisa de que la usuaria contó algo de SU PROPIA huerta y hay "
                "que ofrecerle guardarlo: qué sembró, cuándo, cómo se llama su "
                "huerta o en qué barrio queda. NO guarda nada: prepara un "
                "resumen que ella tiene que confirmar con un botón. No lleva "
                "datos; el sistema los saca del mensaje."
            ),
        ),
        types.FunctionDeclaration(
            name=_AYUDA,
            description=(
                "Muestra el mensaje de bienvenida con lo que el asistente sabe "
                "hacer. Para un saludo sin petición, para cuando pregunta qué "
                "puede hacer, o cuando no se entiende qué necesita."
            ),
        ),
    ]
)


def _historial(turnos, mensaje: str) -> list[types.Content]:
    """Convierte la ventana de memoria en el formato de Gemini.

    El último elemento tiene que ser el mensaje en curso. Normalmente ya lo
    es —el despachador registra lo entrante antes de atenderlo (ADR-0012)—,
    pero se comprueba y se añade si falta: si quien llama olvidara
    registrarlo, el modelo vería una conversación que termina en su propia
    respuesta y contestaría a la pregunta anterior.
    """
    contenidos = [
        types.Content(
            role="user" if turno.rol == "usuaria" else "model",
            parts=[types.Part(text=turno.contenido)],
        )
        for turno in turnos
    ]

    ultimo = contenidos[-1] if contenidos else None
    if (
        ultimo is None
        or ultimo.role != "user"
        or ultimo.parts[0].text != mensaje
    ):
        contenidos.append(
            types.Content(role="user", parts=[types.Part(text=mensaje)])
        )

    return contenidos


def _seleccionar(llamadas) -> list:
    """Deja las llamadas que se van a ejecutar, en su orden definitivo.

    Tres reglas, todas para proteger a la usuaria de una ráfaga de
    mensajes:

    - **Sin repetidas.** Dos llamadas a la misma función darían dos veces
      la misma respuesta.
    - **La ayuda cede.** Si el modelo pidió la bienvenida junto con algo
      más, se descarta la bienvenida: existe para cuando no hay nada que
      hacer, y acompañando a una respuesta real sobra.
    - **El registro, al final.**
    """
    vistas: dict[str, object] = {}
    for llamada in llamadas:
        if llamada.name in _ORDEN_EJECUCION and llamada.name not in vistas:
            vistas[llamada.name] = llamada

    if len(vistas) > 1:
        vistas.pop(_AYUDA, None)

    seleccionadas = sorted(vistas.values(), key=lambda l: _ORDEN_EJECUCION[l.name])
    return seleccionadas[:_MAX_LLAMADAS]


def _pregunta_de(llamada, mensaje: str) -> str:
    """El argumento `pregunta`, con el mensaje original como respaldo.

    Si el modelo no lo manda —o manda algo vacío— se usa el mensaje tal
    como llegó. Es preferible a no consultar: el mensaje literal es
    exactamente lo que la calibración del umbral midió (ADR-0010).
    """
    argumentos = llamada.args or {}
    pregunta = str(argumentos.get("pregunta") or "").strip()

    if not pregunta:
        logger.warning("La llamada a %s vino sin pregunta; se usa el mensaje", llamada.name)
        return mensaje

    return pregunta


async def _ejecutar(
    llamada,
    numero: str,
    usuario_id: UUID,
    mensaje: str,
) -> bool:
    """Corre una función y responde con lo que devuelva.

    Devuelve si le mandó algo a la usuaria, para saber al final si el turno
    se quedó mudo.
    """
    nombre = llamada.name

    if nombre == _ORIENTACION:
        pregunta = _pregunta_de(llamada, mensaje)
        # Se registra si el modelo respetó las palabras de la usuaria. Es
        # el dato que hace falta para la Fase 7: el umbral se calibró con
        # la forma en que habla la gente, no con paráfrasis del modelo.
        logger.info(
            "Herramienta %s | literal=%s | longitud=%d",
            nombre,
            pregunta == mensaje,
            len(pregunta),
        )
        # El mensaje entero va de respaldo: si el recorte del modelo no
        # recupera nada, el CU2 reintenta con lo que ella escribió, que es
        # la formulación sobre la que existe la calibración del umbral.
        await responder(
            numero, usuario_id, await consultar_orientacion(pregunta, mensaje)
        )
        return True

    if nombre == _COMUNIDAD:
        pregunta = _pregunta_de(llamada, mensaje)

        # Vacío o ausente significa "el listado" (ADR-0021). Se normaliza
        # aquí y no en el servicio para que este sea el único sitio que
        # sabe qué forma tienen los argumentos del modelo.
        especie = str((llamada.args or {}).get("especie") or "").strip()

        # Sin la especie en la bitácora, que es dato agronómico de una
        # conversación (CLAUDE.md §11): interesa qué vía se tomó, no qué
        # planta preguntó. En la Fase 7 dice cuánto se usa cada caso de uso
        # y si el modelo rellena la bandera cuando toca.
        logger.info(
            "Herramienta %s | literal=%s | via=%s | usuario_id=%s",
            nombre,
            pregunta == mensaje,
            "CU7" if especie else "CU4",
            usuario_id,
        )
        await responder(
            numero,
            usuario_id,
            await consultar_comunidad(pregunta, usuario_id, especie or None),
        )
        return True

    if nombre == _AYUDA:
        # Texto fijo, sin pasar por el modelo (Fase 2, §4). El modelo
        # decidió cuándo; el qué no es suyo.
        logger.info("Herramienta %s", nombre)
        await responder(numero, usuario_id, textos.BIENVENIDA)
        return True

    if nombre == _REGISTRO:
        # La extracción trabaja sobre el mensaje literal, no sobre nada que
        # haya escrito el modelo.
        extraida = await extraer_huerta(mensaje)

        if not extraida.tiene_datos:
            # El modelo creyó ver un registro donde no hay datos que
            # extraer ("sembré algo el otro día"). Se le pregunta en lugar
            # de proponerle guardar un borrador vacío.
            logger.info("Herramienta %s sin datos que extraer", nombre)
            await responder(numero, usuario_id, textos.REGISTRO_NADA_QUE_ANOTAR)
            return True

        logger.info("Herramienta %s | cultivos=%d", nombre, len(extraida.cultivos))

        # Envía por su cuenta: el resumen lleva botones y lo compone el
        # código, no el modelo (ADR-0008). El barrio y el nombre de la
        # huerta los lee del registro, no del catálogo: los fijó el
        # onboarding (ADR-0016).
        await proponer_registro(numero, usuario_id, extraida)
        return True

    logger.warning("El modelo pidió una función que no existe | nombre=%s", nombre)
    return False


def _texto_de(respuesta) -> str:
    """Junta las partes de texto de la respuesta.

    Se recorren las partes a mano en vez de usar `respuesta.text` porque
    una respuesta con llamadas a función mezcla partes de tipos distintos.
    """
    candidatos = respuesta.candidates or []
    if not candidatos or candidatos[0].content is None:
        return ""

    partes = candidatos[0].content.parts or []
    return "".join(parte.text for parte in partes if parte.text).strip()


async def atender(numero: str, usuario_id: UUID, mensaje: str) -> None:
    """Atiende un mensaje ya normalizado de una usuaria con consentimiento.

    Responde por WhatsApp y deja constancia en la memoria. No devuelve
    nada: hay turnos que producen dos mensajes —una respuesta y una
    propuesta de registro— y uno solo no cabría en un valor de retorno.

    Nunca lanza. Si el modelo falla, la usuaria recibe un texto fijo: es
    preferible a que el mensaje quede sin respuesta y a que el reintento de
    Meta lo repita.
    """
    turnos = await ventana(usuario_id)

    try:
        respuesta = await obtener_cliente().aio.models.generate_content(
            model=MODELO_GENERATIVO,
            contents=_historial(turnos, mensaje),
            config=types.GenerateContentConfig(
                temperature=_TEMPERATURA,
                system_instruction=cargar_prompt(_PROMPT),
                tools=[_HERRAMIENTAS],
                # Sin esto el SDK ejecutaría las funciones por su cuenta y
                # `registrar_huerta` se saltaría los botones (CLAUDE.md §4.7).
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )
    except Exception:
        logger.exception("Gemini falló al decidir qué hacer con el mensaje")
        await responder(numero, usuario_id, textos.AGENTE_NO_DISPONIBLE)
        return

    llamadas = _seleccionar(respuesta.function_calls or [])

    # Nunca el contenido del mensaje (CLAUDE.md §11): qué decidió el
    # modelo, no qué se le dijo.
    logger.info(
        "Agente | turnos_memoria=%d | funciones=%s",
        len(turnos),
        [l.name for l in llamadas] or "ninguna",
    )

    respondido = False
    for llamada in llamadas:
        try:
            respondido |= await _ejecutar(llamada, numero, usuario_id, mensaje)
        except Exception:
            # Una herramienta que falle no debe impedir que se ejecute la
            # otra: en un mensaje de doble intención, que falle la consulta
            # no es motivo para perder también el registro.
            logger.exception("Falló la herramienta | nombre=%s", llamada.name)

    if respondido:
        return

    # El modelo no llamó a nada, o lo que llamó no produjo mensaje: se
    # envía lo que haya escrito.
    texto = _texto_de(respuesta)

    if texto:
        await responder(numero, usuario_id, texto)
        return

    # Ni funciones ni texto. Pasa si el modelo corta por filtros de
    # seguridad. Sin esto la usuaria se quedaría sin respuesta y creería
    # que el bot está caído.
    logger.error("El agente no produjo ni función ni texto")
    await responder(numero, usuario_id, textos.BIENVENIDA)
