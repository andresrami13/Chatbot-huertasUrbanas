"""Backend API del chatbot de huertas urbanas de la UPZ 84 Bosa Occidental.

Punto de entrada de la aplicación FastAPI.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.webhook import router as webhook_router
from app.config import settings
from app.core.basedatos import abrir_pool, cerrar_pool, comprobar_conexion
from app.services.repositorio import (
    contar_mensajes_atascados,
    limpiar_borradores,
    limpiar_idempotencia,
    limpiar_onboardings,
)

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

# Longitud del commit corto, que es como se lee en el historial de git.
_LONGITUD_COMMIT = 7


def _version_desplegada() -> dict[str, str]:
    """Qué commit está corriendo, para poder confirmar un despliegue.

    Railway rellena estas variables sola en cada despliegue desde GitHub.
    En local quedan vacías y se informa "local", que es lo correcto: no hay
    despliegue que identificar.

    Existe porque hasta ahora `/health` decía que el servicio estaba vivo
    pero no cuál era, así que comprobar si un cambio ya estaba arriba
    obligaba a mandar un WhatsApp de prueba.
    """
    commit = settings.RAILWAY_GIT_COMMIT_SHA

    return {
        "commit": commit[:_LONGITUD_COMMIT] if commit else "local",
        "rama": settings.RAILWAY_GIT_BRANCH or "local",
    }


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    """Abre el pool de conexiones al arrancar y lo cierra al apagar."""
    version = _version_desplegada()
    logger.info(
        "Arrancando | commit=%s | rama=%s", version["commit"], version["rama"]
    )

    await abrir_pool()

    # Mantenimiento de la idempotencia (ADR-0005). Va aquí y no en el
    # despachador porque no tiene nada que ver con atender un mensaje.
    try:
        await limpiar_idempotencia()
        await limpiar_borradores()
        await limpiar_onboardings()

        # Los mensajes que se tomaron y nunca terminaron delatan un
        # procesamiento interrumpido, casi siempre un redeploy a mitad de
        # camino. Antes esa pérdida era invisible.
        atascados = await contar_mensajes_atascados()
        if atascados:
            logger.warning(
                "Mensajes tomados y sin terminar | cantidad=%d | "
                "se reprocesarán si Meta los reintenta",
                atascados,
            )
    except Exception:
        # El mantenimiento no debe impedir que el servicio arranque: sin él
        # el bot sigue atendiendo, solo se acumulan filas viejas.
        logger.exception("Falló el mantenimiento de la idempotencia")

    try:
        yield
    finally:
        await cerrar_pool()


app = FastAPI(
    title="Chatbot Huertas Urbanas UPZ 84",
    description=(
        "Prototipo de agente conversacional sobre WhatsApp para el apoyo a "
        "la creación y gestión de huertas urbanas en Bosa Occidental."
    ),
    version="0.1.0",
    lifespan=ciclo_de_vida,
)

app.include_router(webhook_router)


@app.get("/health", tags=["infraestructura"])
async def health() -> JSONResponse:
    """Comprobación de vida, para Railway y para diagnóstico.

    Incluye la base de datos: un servicio que responde pero no llega a
    Supabase no puede atender a nadie, y conviene que eso se vea.

    E incluye **qué versión está corriendo**, para poder confirmar un
    despliegue sin gastar un mensaje del número de prueba, que solo admite
    cinco destinatarios verificados.

    No expone nada sensible: el commit es público —el repositorio lo es— y
    no hay aquí ninguna variable de entorno con secretos.
    """
    base_ok = await comprobar_conexion()

    return JSONResponse(
        status_code=200 if base_ok else 503,
        content={
            "status": "ok" if base_ok else "degradado",
            "base_de_datos": "ok" if base_ok else "sin conexión",
            "version": _version_desplegada(),
        },
    )
