"""Despachador asíncrono de eventos de WhatsApp.

Recorre la estructura anidada del payload de Meta, descarta duplicados por
wamid y deriva cada mensaje al flujo correspondiente.

Orden del flujo general (Fase 2, §5.1): primero la compuerta de
consentimiento y solo después el resto. Centralizarlo aquí evita
duplicarlo en cada flujo y cierra la posibilidad de procesar datos de
alguien que no ha autorizado.

Pendiente de conectar: la normalización de la entrada (transcripción del
audio) y el agente orquestador.
"""

import logging

from app import textos
from app.services.consentimiento import compuerta, es_saludo_o_ayuda
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

    if tipo == "text":
        texto = mensaje.get("text", {}).get("body", "")
        logger.info("Texto recibido | longitud=%d", len(texto))

    elif tipo == "interactive":
        interactivo = mensaje.get("interactive", {})
        boton_id = interactivo.get("button_reply", {}).get("id")
        logger.info("Botón pulsado | id=%s", boton_id)

    elif tipo == "audio":
        media_id = mensaje.get("audio", {}).get("id")
        logger.info("Audio recibido | media_id=%s", media_id)
        # TODO: normalización de la entrada. Hasta que esté, el audio
        # llega a la compuerta sin texto, así que una usuaria sin
        # autorizar recibirá la solicitud de permiso —correcto— y una ya
        # autorizada no obtendrá respuesta todavía.

    else:
        logger.info("Tipo de mensaje no soportado aún | tipo=%s", tipo)

    # Compuerta de consentimiento. Si devuelve None, ya atendió el
    # mensaje: pidió autorización, la registró o respondió la ayuda.
    usuaria = await compuerta(numero, texto, boton_id)
    if usuaria is None:
        return

    # A partir de aquí la usuaria ya autorizó.

    # Provisional: mientras no exista el agente, el saludo y la ayuda se
    # resuelven por palabras clave. Cuando entre el agente, esta decisión
    # pasa a ser suya por function calling (Fase 2, §4).
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
