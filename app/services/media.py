"""Descarga de archivos multimedia de la Meta Cloud API.

El webhook no trae el audio: trae un identificador. Recuperar los bytes
son **dos peticiones, las dos autenticadas**, y ningún documento del
proyecto describe el paso (la Fase 2 incorporó la entrada por voz al
alcance, pero no detalló cómo se obtiene el archivo).

1. `GET /{media_id}` devuelve una URL temporal, el `mime_type` y el tamaño.
2. `GET` a esa URL devuelve los bytes.

Dos detalles que no son evidentes y que rompen la descarga si se omiten:

- **La segunda petición también necesita el token.** La URL no es pública,
  aunque lo parezca.
- **Hay que mandar un `User-Agent`.** El servidor de descarga de Meta
  rechaza las peticiones sin él o con uno que le parezca de robot. No está
  en la documentación oficial; se descubre por el 400 que devuelve.

La URL caduca a los **5 minutos**, así que las dos peticiones van seguidas
y no se guarda la URL en ninguna parte. El `media_id` dura 7 días, pero eso
no ayuda: el procesamiento es inmediato.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TIEMPO_ESPERA = 30.0

# WhatsApp no acepta audios de más de 16 MB, así que este límite no debería
# alcanzarse nunca. Está para que un archivo inesperado no se cargue entero
# en memoria: el servicio corre en Railway Hobby, con memoria acotada.
# De paso queda por debajo del máximo de 20 MB por petición de Gemini, que
# es lo que permite mandar el audio en línea sin usar la Files API.
_MAX_BYTES = 16 * 1024 * 1024

# Un valor fijo y con pinta de cliente HTTP corriente. Ver la nota de
# arriba sobre el rechazo de Meta.
_USER_AGENT = "curl/8.5.0"


async def descargar_audio(media_id: str) -> tuple[bytes, str] | None:
    """Devuelve (bytes, mime_type) del audio, o None si no se pudo.

    No lanza excepción: corre en segundo plano y que una nota de voz no se
    pueda descargar no debe tumbar el procesamiento de los demás mensajes.
    """
    cabeceras = {
        "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
        "User-Agent": _USER_AGENT,
    }

    try:
        # follow_redirects: la URL de descarga de Meta redirige a su CDN.
        # Sin esto httpx devolvería el 302 y la descarga saldría vacía.
        async with httpx.AsyncClient(
            timeout=_TIEMPO_ESPERA, follow_redirects=True
        ) as cliente:
            metadatos = await _pedir_metadatos(cliente, media_id, cabeceras)
            if metadatos is None:
                return None

            url, mime_type, tamano = metadatos

            if tamano > _MAX_BYTES:
                logger.error(
                    "Audio demasiado grande | media_id=%s | bytes=%d | max=%d",
                    media_id,
                    tamano,
                    _MAX_BYTES,
                )
                return None

            respuesta = await cliente.get(url, headers=cabeceras)

    except httpx.HTTPError as exc:
        logger.error(
            "Fallo de red descargando el audio | media_id=%s | %s",
            media_id,
            type(exc).__name__,
        )
        return None

    if respuesta.status_code != 200:
        logger.error(
            "La descarga del audio falló | media_id=%s | http=%d",
            media_id,
            respuesta.status_code,
        )
        return None

    contenido = respuesta.content

    # El tamaño declarado y el descargado deberían coincidir. Si no lo
    # hacen, el archivo llegó truncado y transcribirlo daría un resultado
    # parcial que parecería válido.
    if len(contenido) > _MAX_BYTES:
        logger.error(
            "El audio descargado supera el límite | media_id=%s | bytes=%d",
            media_id,
            len(contenido),
        )
        return None

    logger.info(
        "Audio descargado | media_id=%s | bytes=%d | mime=%s",
        media_id,
        len(contenido),
        mime_type,
    )
    return contenido, mime_type


async def _pedir_metadatos(
    cliente: httpx.AsyncClient,
    media_id: str,
    cabeceras: dict[str, str],
) -> tuple[str, str, int] | None:
    """Primera petición: URL temporal, mime_type y tamaño."""
    url_metadatos = (
        f"https://graph.facebook.com/{settings.META_GRAPH_VERSION}/{media_id}"
    )

    respuesta = await cliente.get(
        url_metadatos,
        headers=cabeceras,
        params={"phone_number_id": settings.META_PHONE_NUMBER_ID},
    )

    if respuesta.status_code != 200:
        logger.error(
            "Meta no devolvió los metadatos del audio | media_id=%s | "
            "http=%d | %s",
            media_id,
            respuesta.status_code,
            respuesta.text[:300],
        )
        return None

    datos = respuesta.json()
    url = datos.get("url")
    if not url:
        logger.error("Los metadatos llegaron sin url | media_id=%s", media_id)
        return None

    # Las notas de voz de WhatsApp llegan como "audio/ogg; codecs=opus".
    # Gemini espera el tipo base, así que se quita el parámetro.
    mime_completo = datos.get("mime_type", "")
    mime_type = mime_completo.split(";")[0].strip() or "audio/ogg"

    return url, mime_type, int(datos.get("file_size") or 0)
