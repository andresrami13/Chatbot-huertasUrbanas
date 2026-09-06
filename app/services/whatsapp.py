"""Cliente de WhatsApp (Fase 3, Tabla 2).

Envía las respuestas a través de la Meta Cloud API. Es la única salida
del sistema hacia la usuaria.

Solo dos tipos de mensaje, y es deliberado (Fase 2, §1): texto libre como
vía principal, y botones únicamente en los dos momentos binarios del
diseño —el consentimiento y la confirmación de un registro—. No hay menús
de navegación: reintroducirían la barrera que el proyecto busca eliminar.
"""

import logging

import httpx

from app.config import settings
from app.core.identidad import referencia_wamid

logger = logging.getLogger(__name__)

# Límites de la Cloud API. Se comprueban aquí para fallar con un mensaje
# entendible en vez de recibir un 400 opaco de Meta.
_MAX_BOTONES = 3
_MAX_TITULO_BOTON = 20
_MAX_CUERPO = 1024

_TIEMPO_ESPERA = 20.0

# El indicador de "escribiendo" va ESPERADO, en el camino crítico del turno
# (ver `marcar_escribiendo`), así que no puede heredar los 20 segundos de un
# envío normal: una Meta lenta retrasaría la respuesta de verdad. Cinco
# segundos bastan de sobra para un cambio de estado, y si no llega, el turno
# sigue sin los puntitos.
_TIEMPO_ESPERA_INDICADOR = 5.0


def _url() -> str:
    return (
        f"https://graph.facebook.com/{settings.META_GRAPH_VERSION}"
        f"/{settings.META_PHONE_NUMBER_ID}/messages"
    )


async def _enviar(carga: dict) -> str | None:
    """Hace la petición y devuelve el wamid del mensaje enviado.

    Devuelve None si falla. No lanza excepción a propósito: esto corre en
    segundo plano, y que no se pueda responder a una usuaria no debe
    tumbar el procesamiento de las demás.
    """
    cabeceras = {
        "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIEMPO_ESPERA) as cliente:
            respuesta = await cliente.post(_url(), json=carga, headers=cabeceras)
    except httpx.HTTPError as exc:
        logger.error("Fallo de red al enviar por WhatsApp | %s", type(exc).__name__)
        return None

    if respuesta.status_code != 200:
        # El cuerpo del error de Meta no lleva datos de la usuaria, pero
        # sí el motivo del rechazo, que es lo que hace falta para
        # diagnosticar (token vencido, destinatario no verificado...).
        logger.error(
            "WhatsApp rechazó el envío | http=%d | %s",
            respuesta.status_code,
            respuesta.text[:300],
        )
        return None

    datos = respuesta.json()
    wamid = (datos.get("messages") or [{}])[0].get("id")

    # El wamid del mensaje enviado lleva dentro el número del destinatario,
    # igual que el de los entrantes, así que a la bitácora va la referencia.
    # El valor completo sí se devuelve: quien llama puede necesitarlo.
    logger.info(
        "Mensaje enviado | ref=%s", referencia_wamid(wamid) if wamid else "-"
    )
    return wamid


async def marcar_escribiendo(wamid: str) -> None:
    """Muestra los tres puntitos de "escribiendo" en el chat de la usuaria.

    Verificado en la documentación de Meta el 23/08/2026: se pide con un
    POST al mismo endpoint de mensajes, con `status: "read"` y el
    `message_id` del mensaje entrante. Dura **hasta 25 segundos** y se
    quita al responder, lo que ocurra primero. Los 25 cubren de sobra los
    ~13 del camino con RAG.

    ## Por qué el wamid aquí no incumple el §11

    La regla dice que el `wamid` nunca va a la bitácora ni a la base **en
    claro**, porque lleva dentro el teléfono del remitente. Aquí no se
    registra ni se almacena: se le devuelve a Meta un identificador que
    Meta mismo generó y ya tiene. A la bitácora sigue yendo la referencia.

    ## Por qué se espera en vez de lanzarlo en segundo plano

    Si la petición del indicador llegara **después** de la respuesta, Meta
    ya no tendría qué descartar y los puntitos se quedarían puestos los 25
    segundos, con nada detrás. Esperar cuesta un viaje de ida y vuelta y
    garantiza el orden.

    ## Efecto que no es opcional

    El cuerpo lleva `status: "read"`, así que además **marca el mensaje
    como leído**: aparecen los dos chulos azules. No se puede pedir lo uno
    sin lo otro.

    No lanza: que no salgan los puntitos no puede tumbar el turno.
    """
    carga = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": wamid,
        "typing_indicator": {"type": "text"},
    }
    cabeceras = {
        "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIEMPO_ESPERA_INDICADOR) as cliente:
            respuesta = await cliente.post(_url(), json=carga, headers=cabeceras)
    except httpx.HTTPError as exc:
        logger.warning("No se pudo marcar escribiendo | %s", type(exc).__name__)
        return

    if respuesta.status_code != 200:
        logger.warning(
            "Meta rechazó el indicador de escritura | http=%d | %s",
            respuesta.status_code,
            respuesta.text[:200],
        )


async def enviar_texto(destino: str, texto: str) -> str | None:
    """Envía un mensaje de texto simple."""
    if len(texto) > _MAX_CUERPO:
        logger.warning(
            "Texto recortado a %d caracteres | longitud=%d", _MAX_CUERPO, len(texto)
        )
        texto = texto[:_MAX_CUERPO]

    return await _enviar(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": destino,
            "type": "text",
            # preview_url en false: los enlaces no generan vista previa,
            # que en pantallas pequeñas ocupa espacio y distrae.
            "text": {"preview_url": False, "body": texto},
        }
    )


async def enviar_botones(
    destino: str,
    cuerpo: str,
    botones: list[tuple[str, str]],
) -> str | None:
    """Envía un mensaje con botones de respuesta rápida.

    `botones` es una lista de pares (identificador, rótulo). El
    identificador es el que vuelve en el webhook cuando la usuaria pulsa.
    """
    if not 1 <= len(botones) <= _MAX_BOTONES:
        raise ValueError(
            f"WhatsApp admite entre 1 y {_MAX_BOTONES} botones; "
            f"se pasaron {len(botones)}"
        )

    for _, rotulo in botones:
        if len(rotulo) > _MAX_TITULO_BOTON:
            raise ValueError(
                f"El rótulo '{rotulo}' supera los {_MAX_TITULO_BOTON} "
                f"caracteres que admite WhatsApp"
            )

    if len(cuerpo) > _MAX_CUERPO:
        raise ValueError(
            f"El cuerpo supera los {_MAX_CUERPO} caracteres "
            f"(tiene {len(cuerpo)})"
        )

    return await _enviar(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": destino,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": cuerpo},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": identificador, "title": rotulo},
                        }
                        for identificador, rotulo in botones
                    ]
                },
            },
        }
    )
