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
import re
from uuid import UUID

from app.config import settings
from app.services.embeddings import vectorizar_consulta
from app.services.repositorio import (
    FragmentoComunitario,
    FragmentoOficial,
    buscar_fragmentos_comunitarios,
    buscar_fragmentos_oficiales,
)

logger = logging.getLogger(__name__)


# --- Retirada de las etiquetas que se cuelan en la respuesta -----------
#
# Las etiquetas viven aquí, así que la limpieza también: este es el único
# módulo que sabe qué forma tienen.
#
# Hace falta porque el modelo a veces copia el rótulo en la respuesta. Visto
# el 15/08/2026 en el spike del despachador: "En la huerta COMUNITARIO – La
# Esperanza, del barrio El Regalo...". La etiqueta es un andamio para el
# modelo y para la usuaria no significa nada.
#
# Los prompts se lo prohíben, que es la defensa principal. Esto es la red:
# se comprobó que ocurre de forma intermitente, y una regla de prompt a
# temperatura 0.4 no es una garantía.

# Con corchetes: se conserva lo de dentro, que es la atribución de verdad.
_ETIQUETA_ENTERA = re.compile(r"\[\s*(?:OFICIAL|COMUNITARIO)\s*[–—-]\s*([^\]]*)\]")

# Sin corchetes, que es como se coló en la prueba.
_ETIQUETA_SUELTA = re.compile(r"\b(?:OFICIAL|COMUNITARIO)\s*[–—-]\s*")

_ESPACIOS = re.compile(r"[ \t]{2,}")


def limpiar_etiquetas(respuesta: str) -> str:
    """Quita de la respuesta los rótulos de procedencia que se hayan colado.

    No toca la atribución: de `[COMUNITARIO – La Esperanza, Holanda]` deja
    `La Esperanza, Holanda`. Lo que se retira es la palabra clave y los
    corchetes, que son andamiaje del prompt.
    """
    limpia = _ETIQUETA_ENTERA.sub(r"\1", respuesta)
    limpia = _ETIQUETA_SUELTA.sub("", limpia)
    limpia = _ESPACIOS.sub(" ", limpia)

    if limpia != respuesta:
        # Interesa para la Fase 7: cuenta cuántas veces la regla del prompt
        # no bastó. Sin el contenido de la respuesta (CLAUDE.md §11).
        logger.info("Se retiró una etiqueta de procedencia de la respuesta")

    return limpia.strip()


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


def _etiquetar_comunitario(fragmento: FragmentoComunitario) -> str:
    """Antepone la etiqueta `[COMUNITARIO – huerta, barrio]` (Fase 4, §5).

    Es la etiqueta imprescindible. El spike de la Fase 5 lo dejó medido: al
    preguntar por los cultivos de un barrio se recuperan huertas de los
    tres, porque el barrio no filtra (ADR-0001). Sin decir de dónde sale
    cada dato, la usuaria entendería que todo eso se siembra en el suyo.

    Una huerta sin nombre se identifica por su barrio, que es lo único que
    se puede decir de ella sin inventar.
    """
    if fragmento.nombre_huerta:
        atribucion = f"{fragmento.nombre_huerta}, {fragmento.barrio}"
    else:
        atribucion = f"una huerta del barrio {fragmento.barrio}"

    return f"[COMUNITARIO – {atribucion}]\n{fragmento.contenido}"


def componer_contexto_comunitario(fragmentos: list[FragmentoComunitario]) -> str:
    """Arma el bloque de contexto del CU4, cada huerta con su atribución."""
    return "\n\n---\n\n".join(
        _etiquetar_comunitario(fragmento) for fragmento in fragmentos
    )


async def buscar_en_comunidad(
    pregunta: str,
    usuario_id: UUID | None = None,
) -> list[FragmentoComunitario]:
    """Busca qué huertas ajenas tienen sembrado lo que ella preguntó (CU7).

    `usuario_id` se excluye de los resultados: devolverle su propia huerta
    como dato comunitario sería repetirle lo que ella misma registró.

    Umbral propio, distinto del de la colección oficial (ADR-0011): estos
    fragmentos son listas de tres o cuatro palabras, no prosa de 400
    tokens, y sus similitudes viven en otro rango.

    ## Ya no lleva respaldo por listado, y eso es el ADR-0021

    Hasta el 08/09/2026 esta función hacía dos cosas: buscaba por similitud
    y, si nada pasaba el umbral, devolvía las huertas actualizadas más
    recientemente. Ese respaldo existía porque el CU4 recibía dos clases de
    pregunta por el mismo camino y solo una era una búsqueda (ADR-0011).

    El respaldo tenía un modo de fallo que solo se ve cuando las dos clases
    se separan: si ella pregunta por un cultivo que **nadie** tiene, la
    similitud no devuelve nada, el respaldo se dispara y recibe un listado
    de huertas que no tienen lo que preguntó. Con el listado ya bien
    formateado eso queda peor, no mejor.

    Hoy el listado es su propio caso de uso, lo compone el código y no pasa
    por aquí. Lo que queda aquí es solo la búsqueda, y cuando no encuentra
    **devuelve la lista vacía**, que es una respuesta y no un fallo: quien
    llama tiene que decir que ninguna huerta tiene eso anotado.

    Advertencia que vale también para el documento de grado: **aquí el
    umbral no hace todo el trabajo**. Con 5 a 7 huertas y top-k=4, casi
    cualquier consulta recupera medio corpus, y por eso `comunidad.py`
    filtra después por la especie. Lo que aporta rigor es esa comprobación
    y la atribución, no el filtro por similitud.
    """
    vector = await vectorizar_consulta(pregunta)

    fragmentos = await buscar_fragmentos_comunitarios(
        vector,
        top_k=settings.RAG_TOP_K,
        umbral=settings.RAG_UMBRAL_COMUNITARIO,
        excluir_usuario=usuario_id,
    )

    logger.info(
        "Búsqueda comunitaria | fragmentos=%d | umbral=%.2f | mejor=%s",
        len(fragmentos),
        settings.RAG_UMBRAL_COMUNITARIO,
        f"{fragmentos[0].similitud:.4f}" if fragmentos else "-",
    )

    return fragmentos


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
