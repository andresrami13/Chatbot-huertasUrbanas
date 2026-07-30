"""Despachador asíncrono de eventos de WhatsApp.

Recorre la estructura anidada del payload de Meta, descarta duplicados por
wamid y deriva cada mensaje al flujo correspondiente.

Orden del flujo general (Fase 2, §5.1): primero la compuerta de
consentimiento y solo después el resto. Centralizarlo aquí evita
duplicarlo en cada flujo y cierra la posibilidad de procesar datos de
alguien que no ha autorizado.

Orden interno, y el orden importa: identificar el mensaje -> compuerta de
consentimiento -> normalización de la entrada -> intención. La
transcripción va **después** de la compuerta a propósito (ADR-0006).

Pendiente de conectar: el agente orquestador.
"""

import logging

from app import textos
from app.services.consentimiento import compuerta, es_saludo_o_ayuda
from app.services.normalizacion import transcribir_audio
from app.services.whatsapp import enviar_texto

logger = logging.getLogger(__name__)

# --- Idempotencia -----------------------------------------------------
# Meta reintenta la entrega de un webhook si no recibe 200 a tiempo, así
# que el mismo mensaje puede llegar más de una vez. Sin este control, un
# reintento produciría una respuesta duplicada o un registro de huerta
# duplicado.
#
# PROVISIONAL: en memoria. Se pierde en cada reinicio del servicio y no
# sirve si hubiera más de una instancia. Debe migrar a una tabla en
# Supabase cuando se implemente la persistencia.
_wamids_procesados: set[str] = set()
_LIMITE_EN_MEMORIA = 5_000


async def procesar_evento(payload: dict) -> None:
    """Punto de entrada del procesamiento en segundo plano."""
    try:
        for entrada in payload.get("entry", []):
            for cambio in entrada.get("changes", []):
                valor = cambio.get("value", {})

                # Acuses de entrega y lectura. No requieren acción, pero
                # sirven para diagnosticar problemas de envío.
                for estado in valor.get("statuses", []):
                    logger.info(
                        "Acuse | wamid=%s | estado=%s",
                        estado.get("id"),
                        estado.get("status"),
                    )

                for mensaje in valor.get("messages", []):
                    await _procesar_mensaje(mensaje)

    except Exception:
        # El despachador corre fuera del ciclo de la petición: si estalla
        # aquí, la excepción se pierde en silencio. Registrarla es la
        # única forma de enterarse.
        logger.exception("Error no controlado procesando el evento")


async def _procesar_mensaje(mensaje: dict) -> None:
    wamid = mensaje.get("id")
    if not wamid:
        logger.warning("Mensaje sin wamid; se descarta")
        return

    if wamid in _wamids_procesados:
        logger.info("Duplicado descartado | wamid=%s", wamid)
        return

    if len(_wamids_procesados) >= _LIMITE_EN_MEMORIA:
        _wamids_procesados.clear()
    _wamids_procesados.add(wamid)

    tipo = mensaje.get("type")
    numero = mensaje.get("from")

    # Minimización de datos (Fase 3, capa 6): no se registra el número del
    # remitente ni el contenido del mensaje en la bitácora.
    logger.info("Mensaje entrante | tipo=%s | wamid=%s", tipo, wamid)

    if not numero:
        logger.warning("Mensaje sin remitente; se descarta | wamid=%s", wamid)
        return

    texto: str | None = None
    boton_id: str | None = None
    media_id_audio: str | None = None

    if tipo == "text":
        texto = mensaje.get("text", {}).get("body", "")
        logger.info("Texto recibido | longitud=%d", len(texto))

    elif tipo == "interactive":
        interactivo = mensaje.get("interactive", {})
        boton_id = interactivo.get("button_reply", {}).get("id")
        logger.info("Botón pulsado | id=%s", boton_id)

    elif tipo == "audio":
        media_id_audio = mensaje.get("audio", {}).get("id")
        logger.info("Audio recibido | media_id=%s", media_id_audio)
        # Solo se guarda el identificador. NO se transcribe aquí: hacerlo
        # antes de la compuerta sería mandar a Gemini el audio de alguien
        # que quizá no ha autorizado, que es exactamente lo que el
        # ADR-0006 impide. La transcripción va más abajo.

    else:
        logger.info("Tipo de mensaje no soportado aún | tipo=%s", tipo)

    # Compuerta de consentimiento. Si devuelve None, ya atendió el
    # mensaje: pidió autorización, la registró o respondió la ayuda.
    #
    # El audio llega aquí sin texto, y es correcto: quien no ha autorizado
    # recibe la solicitud de permiso, sin que su voz salga del backend.
    usuaria = await compuerta(numero, texto, boton_id)
    if usuaria is None:
        return

    # A partir de aquí la usuaria ya autorizó.

    # Normalización de la entrada (CLAUDE.md §4.4). Una sola vez, en un
    # único sitio y antes de interpretar la intención: de aquí en adelante
    # da igual si el mensaje llegó escrito o hablado.
    if media_id_audio is not None:
        texto = await transcribir_audio(media_id_audio)
        if texto is None:
            await enviar_texto(numero, textos.AUDIO_NO_ENTENDIDO)
            return

    # Provisional: mientras no exista el agente, el saludo y la ayuda se
    # resuelven por palabras clave. Cuando entre el agente, esta decisión
    # pasa a ser suya por function calling (Fase 2, §4).
    #
    # Ahora también alcanza a las notas de voz: un "hola" hablado llega
    # aquí ya como texto.
    if es_saludo_o_ayuda(texto):
        await enviar_texto(numero, textos.BIENVENIDA)
        return

    logger.info(
        "Mensaje de usuaria autorizada, a la espera del agente | "
        "usuario_id=%s | wamid=%s",
        usuaria.id,
        wamid,
    )

    # TODO (pasos siguientes): normalización de la entrada -> agente
    # orquestador (function calling) -> respuesta por WhatsApp.
