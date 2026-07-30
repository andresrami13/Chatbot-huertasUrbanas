"""Vectorización de texto para la búsqueda por similitud (Fase 4, §7).

Dos entradas, una por lado de la recuperación:

- `vectorizar_documentos`, para la ingesta (fuentes oficiales y fragmentos
  comunitarios).
- `vectorizar_consulta`, para lo que pregunta la usuaria.

La diferencia no es cosmética: `gemini-embedding-001` admite `task_type`, y
vectorizar un documento y una consulta con el mismo valor degrada la
recuperación. Los dos vectores tienen que estar en el mismo espacio, pero
generados para el papel que cumplen.

**Ningún dato personal se vectoriza.** Solo entra lo agronómico
—nombre de huerta, barrio, cultivos—, que es lo compartible según la capa 4
del modelo de seguridad (Fase 3, Tabla 3) y el ADR-0004.
"""

import logging
import math

from google.genai import types

from app.core.gemini import (
    DIMENSIONES_EMBEDDING,
    MODELO_EMBEDDING,
    obtener_cliente,
)

logger = logging.getLogger(__name__)


def _normalizar_l2(vector: list[float]) -> list[float]:
    """Lleva el vector a longitud 1.

    Hace falta porque `gemini-embedding-001` solo devuelve normalizados los
    vectores de 3072 dimensiones; los truncados a 768 llegan con norma
    distinta de 1 y Google indica normalizarlos a mano.

    Matiz que conviene no confundir: para la distancia coseno de pgvector
    (`<=>`) la norma es irrelevante, porque el propio operador divide por
    ella. Normalizar sirve para otras dos cosas: permite usar el producto
    interno (`<#>`), más barato, como equivalente del coseno, y evita que la
    misma columna acabe mezclando vectores normalizados y sin normalizar, que
    sí rompería cualquier comparación posterior.
    """
    norma = math.sqrt(math.fsum(componente * componente for componente in vector))

    if norma == 0.0:
        # Un vector nulo no tiene dirección: la similitud coseno queda
        # indefinida. Es señal de un fallo del modelo, no un caso a tolerar.
        raise ValueError("El modelo devolvió un vector nulo; no se puede normalizar.")

    return [componente / norma for componente in vector]


async def _vectorizar(textos: list[str], tarea: str) -> list[list[float]]:
    """Llama al modelo y devuelve un vector normalizado por cada texto."""
    if not textos:
        return []

    respuesta = await obtener_cliente().aio.models.embed_content(
        model=MODELO_EMBEDDING,
        contents=textos,
        config=types.EmbedContentConfig(
            task_type=tarea,
            output_dimensionality=DIMENSIONES_EMBEDDING,
        ),
    )

    embeddings = respuesta.embeddings or []

    # El SDK devuelve un embedding por entrada. Si no coinciden, alinear
    # vectores con textos por posición sería adivinar.
    if len(embeddings) != len(textos):
        raise RuntimeError(
            f"Se pidieron {len(textos)} embeddings y llegaron "
            f"{len(embeddings)}."
        )

    vectores: list[list[float]] = []
    for embedding in embeddings:
        valores = embedding.values
        if valores is None:
            raise RuntimeError("Un embedding llegó sin valores.")

        # Si esto cambiara sin avisar, los vectores entrarían a una columna
        # vector(768) y el fallo aparecería en la base, no aquí.
        if len(valores) != DIMENSIONES_EMBEDDING:
            raise RuntimeError(
                f"El modelo devolvió {len(valores)} dimensiones y se "
                f"esperaban {DIMENSIONES_EMBEDDING}."
            )

        vectores.append(_normalizar_l2(list(valores)))

    # Nunca el contenido de los textos (CLAUDE.md §11): solo metadatos.
    logger.info(
        "Vectorización | tarea=%s | textos=%d | dimensiones=%d",
        tarea,
        len(textos),
        DIMENSIONES_EMBEDDING,
    )

    return vectores


async def vectorizar_documentos(textos: list[str]) -> list[list[float]]:
    """Vectoriza texto que se va a almacenar y recuperar (ingesta)."""
    return await _vectorizar(textos, "RETRIEVAL_DOCUMENT")


async def vectorizar_consulta(texto: str) -> list[float]:
    """Vectoriza la pregunta de la usuaria."""
    vectores = await _vectorizar([texto], "RETRIEVAL_QUERY")
    return vectores[0]
