"""Conexión a Supabase (PostgreSQL).

Se conecta directamente por el protocolo de PostgreSQL, no por la Data
API de Supabase. El motivo es la búsqueda por similitud del RAG: con
pgvector es SQL corriente, mientras que por la API habría que envolver
cada consulta en una función RPC. Además permite dejar la Data API
cerrada.

El backend usa la clave de *service role*, que omite el RLS por diseño.
La barrera de acceso real es el filtrado por usuario_id que aplica el
repositorio (Fase 3, §5.1).
"""

import logging

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def abrir_pool() -> None:
    """Crea el pool de conexiones al arrancar el servicio."""
    global _pool

    if _pool is not None:
        return

    _pool = await asyncpg.create_pool(
        dsn=settings.DATABASE_URL,
        min_size=settings.DB_POOL_MIN,
        max_size=settings.DB_POOL_MAX,
        # El plan gratuito de Supabase limita las conexiones simultáneas;
        # un pool pequeño evita agotarlas.
        command_timeout=30,
    )

    # Sin datos de la cadena de conexión: lleva la contraseña.
    logger.info(
        "Pool de base de datos abierto | min=%d | max=%d",
        settings.DB_POOL_MIN,
        settings.DB_POOL_MAX,
    )


async def cerrar_pool() -> None:
    """Cierra el pool al apagar el servicio."""
    global _pool

    if _pool is None:
        return

    await _pool.close()
    _pool = None
    logger.info("Pool de base de datos cerrado")


def obtener_pool() -> asyncpg.Pool:
    """Devuelve el pool activo.

    Falla de forma explícita si se llama antes de arrancar, en lugar de
    dar un error confuso de NoneType más adelante.
    """
    if _pool is None:
        raise RuntimeError(
            "El pool de base de datos no está abierto. "
            "abrir_pool() se invoca en el ciclo de vida de la aplicación."
        )
    return _pool


async def comprobar_conexion() -> bool:
    """Comprueba que la base responde. La usa el endpoint /health."""
    try:
        async with obtener_pool().acquire() as conexion:
            await conexion.fetchval("select 1")
        return True
    except Exception:
        logger.exception("La comprobación de conexión a la base falló")
        return False
