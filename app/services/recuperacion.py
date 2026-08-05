"""Recuperación por similitud y armado del contexto atribuido (Fase 4, §5).

Un componente, una responsabilidad (Fase 3, Tabla 2): aquí se recupera y se
etiqueta, **no se redacta**. Quien convierte esto en una respuesta para la
usuaria es `app/services/orientacion.py`.

## La atribución no es decorativa

Cada fragmento entra al contexto con su etiqueta de procedencia —
`[OFICIAL – entidad, título]` en la Fase 4, §5— y esa etiqueta es lo que
sostiene la jerarquía de fuentes de CLAUDE.md §6: fuente oficial curada por
encima del dato comunitario, y este siempre atribuido y nunca presentado
como instrucción técnica.

El spike de la Fase 5 lo dejó claro para el CU4: al preguntar por los
cultivos de un barrio se recuperaron los tres barrios, porque el barrio no
filtra (ADR-0001). Sin la etiqueta, la usuaria creería que todo eso se
siembra en el suyo.

## Sobre el umbral

Se habla siempre en **similitud**, no en distancia. La conversión al
operador de pgvector ocurre una sola vez, dentro del repositorio.

El valor por defecto es 0.68 y no el 0.70 de la Fase 4 (ADR-0010): medido
contra el corpus real, 0.70 dejaba sin responder 4 de 12 consultas
legítimas del CU2. Es configurable por entorno para poder calibrarlo en la
Fase 7 sin desplegar.
"""

import logging

from app.config import settings
from app.services.embeddings import vectorizar_consulta
from app.services.repositorio import FragmentoOficial, buscar_fragmentos_oficiales

logger = logging.getLogger(__name__)


def _etiquetar(fragmento: FragmentoOficial) -> str:
    """Antepone al fragmento su etiqueta de procedencia (Fase 4, §5)."""
    return f"[OFICIAL – {fragmento.entidad}, {fragmento.titulo}]\n{fragmento.contenido}"


def componer_contexto(fragmentos: list[FragmentoOficial]) -> str:
    """Arma el bloque de contexto que se le pasa al modelo.

    Van en orden de pertinencia y separados, para que el modelo pueda
    distinguir dónde acaba uno y empieza otro: fragmentos consecutivos del
    mismo documento tratan temas distintos, y pegarlos sin separación
    invita a construir una frase que ninguno de los dos dice.
    """
    return "\n\n---\n\n".join(_etiquetar(fragmento) for fragmento in fragmentos)


async def recuperar_orientacion(pregunta: str) -> list[FragmentoOficial]:
    """Recupera de la colección oficial lo pertinente a la pregunta.

    Devuelve la lista vacía si nada supera el umbral, y eso **es una
    respuesta válida**, no un fallo: significa que el corpus no cubre lo
    que se preguntó. Quien llama tiene que distinguir ese caso y decirlo,
    en lugar de dejar que el modelo improvise (CLAUDE.md §6).
    """
    vector = await vectorizar_consulta(pregunta)

    fragmentos = await buscar_fragmentos_oficiales(
        vector,
        top_k=settings.RAG_TOP_K,
        umbral=settings.RAG_UMBRAL_SIMILITUD,
    )

    # Nunca la pregunta ni el contenido (CLAUDE.md §11): solo cuántos y con
    # qué similitud, que es lo que hace falta para calibrar en la Fase 7.
    logger.info(
        "Recuperación oficial | fragmentos=%d | umbral=%.2f | mejor=%s",
        len(fragmentos),
        settings.RAG_UMBRAL_SIMILITUD,
        f"{fragmentos[0].similitud:.4f}" if fragmentos else "-",
    )

    return fragmentos
