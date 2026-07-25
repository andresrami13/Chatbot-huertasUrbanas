"""Controlador de webhook (Fase 3, Tabla 2).

Dos responsabilidades y nada más:
  GET  -> responder el reto de verificación de Meta al registrar la URL.
  POST -> validar la firma, responder 200 de inmediato y delegar el
          procesamiento al despachador asíncrono.

El 200 inmediato no es un detalle de rendimiento: Meta reintenta la entrega
si no recibe respuesta con rapidez, y el pipeline completo (transcripción,
function calling, RAG) tarda bastante más que ese margen. Procesar dentro
del request produciría mensajes duplicados al usuario.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Request, Response
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.core.signature import firma_valida
from app.services.dispatcher import procesar_evento

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("")
async def verificar_webhook(request: Request) -> PlainTextResponse:
    """Reto de verificación que Meta envía al registrar la URL."""
    parametros = request.query_params
    modo = parametros.get("hub.mode")
    token = parametros.get("hub.verify_token")
    reto = parametros.get("hub.challenge")

    if modo == "subscribe" and token == settings.META_VERIFY_TOKEN:
        logger.info("Webhook verificado correctamente por Meta")
        # Debe devolverse como texto plano. Si se envuelve en JSON,
        # Meta rechaza la verificación.
        return PlainTextResponse(content=reto or "", status_code=200)

    logger.warning("Verificación de webhook rechazada: token no coincide")
    return PlainTextResponse(content="Forbidden", status_code=403)


@router.post("")
async def recibir_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Response:
    """Recibe los eventos de WhatsApp y los encola para procesamiento."""
    cuerpo_crudo = await request.body()
    cabecera_firma = request.headers.get("X-Hub-Signature-256")

    if not firma_valida(cuerpo_crudo, cabecera_firma):
        logger.warning("Petición descartada: firma inválida o ausente")
        return Response(status_code=403)

    try:
        payload = await request.json()
    except ValueError:
        logger.exception("El cuerpo recibido no es JSON válido")
        # 200 a propósito: el cuerpo es inválido y reintentarlo no cambia
        # nada. Devolver error solo provocaría reintentos indefinidos.
        return Response(status_code=200)

    background_tasks.add_task(procesar_evento, payload)
    return Response(status_code=200)
