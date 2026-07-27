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

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    """Abre el pool de conexiones al arrancar y lo cierra al apagar."""
    await abrir_pool()
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
    """
    base_ok = await comprobar_conexion()

    return JSONResponse(
        status_code=200 if base_ok else 503,
        content={
            "status": "ok" if base_ok else "degradado",
            "base_de_datos": "ok" if base_ok else "sin conexión",
        },
    )
