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

logger = logging.getLogger(__name__)

# Límites de la Cloud API. Se comprueban aquí para fallar con un mensaje
# entendible en vez de recibir un 400 opaco de Meta.
_MAX_BOTONES = 3
_MAX_TITULO_BOTON = 20
_MAX_CUERPO = 1024

_TIEMPO_ESPERA = 20.0


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
    logger.info("Mensaje enviado | wamid=%s", wamid)
    return wamid


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
