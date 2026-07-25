"""Despachador asíncrono de eventos de WhatsApp.

Recorre la estructura anidada del payload de Meta, descarta duplicados por
wamid y deriva cada mensaje al flujo correspondiente.

Estado actual: solo registra en bitácora. La compuerta de consentimiento,
la normalización de la entrada y el agente se conectan aquí en los pasos
siguientes.
"""

import logging

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

    # Minimización de datos (Fase 3, capa 6): no se registra el número del
    # remitente ni el contenido del mensaje en la bitácora.
    logger.info("Mensaje entrante | tipo=%s | wamid=%s", tipo, wamid)

    if tipo == "text":
        texto = mensaje.get("text", {}).get("body", "")
        logger.info("Texto recibido | longitud=%d", len(texto))
    elif tipo == "audio":
        media_id = mensaje.get("audio", {}).get("id")
        logger.info("Audio recibido | media_id=%s", media_id)
    elif tipo == "interactive":
        logger.info("Respuesta interactiva recibida (botón)")
    else:
        logger.info("Tipo de mensaje no soportado aún | tipo=%s", tipo)

    # TODO (paso siguiente): compuerta de consentimiento -> normalización
    # de la entrada -> agente orquestador -> respuesta por WhatsApp.
