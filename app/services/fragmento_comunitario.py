"""Generación del fragmento comunitario que alimenta el CU4.

`cultivo` es la fuente de verdad del dato agronómico; este fragmento es un
**derivado** que se reconstruye entero cada vez que la huerta cambia
(ADR-0004). No hay actualización incremental.

## Qué entra en el texto, y por qué tan poco

Solo las especies: `"tomate, cilantro, lechuga"`. Ni el nombre de la
huerta, ni el barrio, ni las fechas.

Parece que se pierde información y no se pierde ninguna: el nombre y el
barrio viajan por la clave foránea a `huerta`, y las fechas siguen en
`cultivo`. Todo eso se recupera al componer la respuesta, igual que la
entidad y el título de la colección oficial salen de `fuente` (ADR-0009).

El motivo de sacarlo del texto **está medido** (ADR-0011). Lo que se repite
en todos los fragmentos —una plantilla, un barrio, un "de 2026"— infla por
igual la similitud de todos y destruye la capacidad de distinguir unos de
otros. Comparados cuatro formatos contra consultas reales del CU4, la
separación media fue:

    plantilla del spike        0.0585
    prosa con nombre y barrio  0.0608
    solo cultivos con fecha    0.0735
    solo especies              0.1166   <- este

Y no es cosa de la forma: redactar la plantilla como prosa natural no
mejoró nada. Lo que estorba es que el dato compartido esté, se escriba como
se escriba.

## Ningún dato personal

Solo especies vegetales. Es la capa 4 del modelo de seguridad (Fase 3,
Tabla 3): lo agronómico es compartible, lo personal no entra al RAG.
"""

import logging
from uuid import UUID

from app.services.embeddings import vectorizar_documentos
from app.services.repositorio import (
    guardar_fragmento_comunitario,
    listar_cultivos_de_huerta,
)

logger = logging.getLogger(__name__)


def componer_texto(especies: list[str]) -> str:
    """El texto que se vectoriza: las especies y nada más (ADR-0011)."""
    return ", ".join(especies)


async def regenerar_fragmento(huerta_id: UUID) -> bool:
    """Rehace el fragmento de una huerta desde sus filas de `cultivo`.

    Devuelve True si quedó escrito, False si no había nada que compartir.

    **No lanza excepciones hacia arriba por decisión de diseño.** Quien la
    llama es la confirmación del CU3, y el fragmento es un derivado: si la
    vectorización falla, la huerta ya está guardada y la usuaria debe
    recibir su "listo, ya quedó guardado". Lo que no puede es fallar en
    silencio, así que el fallo queda en la bitácora y el script
    `scripts.regenerar_fragmentos` lo repara después.

    El precio de esa decisión hay que enunciarlo: entre el fallo y la
    reparación, esa huerta es invisible para el CU4.
    """
    try:
        especies = await listar_cultivos_de_huerta(huerta_id)

        if not especies:
            # Una huerta registrada con nombre y barrio pero sin cultivos no
            # tiene nada que aportar al CU4. Vectorizar la cadena vacía no
            # daría un vector útil, solo ruido en la colección.
            logger.info(
                "Huerta sin cultivos; no se genera fragmento | huerta_id=%s",
                huerta_id,
            )
            return False

        texto = componer_texto(especies)
        vectores = await vectorizar_documentos([texto])
        await guardar_fragmento_comunitario(huerta_id, texto, vectores[0])

        # El contenido son especies vegetales, no dato personal, pero se
        # registra el número y no la lista: la bitácora no necesita saber
        # qué siembra nadie (CLAUDE.md §11).
        logger.info(
            "Fragmento comunitario regenerado | huerta_id=%s | especies=%d",
            huerta_id,
            len(especies),
        )
        return True

    except Exception:
        logger.exception(
            "Falló la generación del fragmento comunitario; la huerta queda "
            "invisible para el CU4 hasta que se regenere | huerta_id=%s",
            huerta_id,
        )
        return False
