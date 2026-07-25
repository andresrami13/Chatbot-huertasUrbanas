"""Backend API del chatbot de huertas urbanas de la UPZ 84 Bosa Occidental.

Punto de entrada de la aplicación FastAPI.
"""

import logging

from fastapi import FastAPI

from app.api.webhook import router as webhook_router
from app.config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(
    title="Chatbot Huertas Urbanas UPZ 84",
    description=(
        "Prototipo de agente conversacional sobre WhatsApp para el apoyo a "
        "la creación y gestión de huertas urbanas en Bosa Occidental."
    ),
    version="0.1.0",
)

app.include_router(webhook_router)


@app.get("/health", tags=["infraestructura"])
async def health() -> dict[str, str]:
    """Comprobación de vida del servicio, para Railway y para diagnóstico."""
    return {"status": "ok"}
