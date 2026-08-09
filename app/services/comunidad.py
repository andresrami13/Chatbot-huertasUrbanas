"""Consulta de lo que siembran otras huertas — CU4 (Fase 2, §5.4).

Hermano de `orientacion.py`: `recuperacion.py` trae los fragmentos y aquí
se redactan. Es la implementación de la herramienta `consultar_comunidad`
del agente (ADR-0013), y lo que devuelve se envía tal cual.

**Es el agente quien lo enruta**, y por eso estuvo construido y sin
conectar desde el 04/08/2026: decidir que un mensaje es una consulta a la
comunidad con palabras clave sería el clasificador aparte que CLAUDE.md
§4.9 excluye. Importa más de lo que parece, porque el respaldo por listado
del ADR-0011 no filtra por intención: si algo llega hasta aquí, recibe
huertas.

## En qué se diferencia del CU2, y no es un detalle

El CU2 responde con una **fuente oficial curada**, que es autoridad. El CU4
responde con **dato comunitario**, que según la jerarquía de CLAUDE.md §6
va siempre atribuido y **nunca como instrucción técnica**. Que tres huertas
tengan tomate no significa que el tomate se dé bien aquí; significa que
tres vecinas sembraron tomate.

Por eso el prompt es propio y no el del CU2: la mitad de sus reglas
existen para impedir que el modelo convierta un reporte en una
recomendación.

La atribución `[COMUNITARIO – huerta, barrio]` la pone `recuperacion.py` y
el prompt obliga a repetirla en la respuesta. No es adorno: el barrio no
filtra la búsqueda (ADR-0001), así que se recuperan huertas de barrios
distintos al de quien pregunta.

## Precondición

El CU4 exige consentimiento **y datos existentes** (Fase 2). Lo segundo no
está garantizado: con el prototipo recién desplegado puede no haber
ninguna otra huerta registrada, y ese caso se responde con texto fijo.
"""

import logging
from uuid import UUID

from google.genai import types

from app.agent.plantillas import cargar_prompt
from app.core.gemini import MODELO_GENERATIVO, obtener_cliente
from app.services.recuperacion import (
    componer_contexto_comunitario,
    limpiar_etiquetas,
    recuperar_comunidad,
)

logger = logging.getLogger(__name__)

_PROMPT = "redaccion_comunidad_v1.md"

# La misma que la redacción del RAG (CLAUDE.md §8). Aquí importa incluso
# más: lo que se reformula es una lista de especies ajenas, y la
# creatividad solo puede añadir lo que nadie sembró.
_TEMPERATURA = 0.4


async def consultar_comunidad(pregunta: str, usuario_id: UUID) -> str:
    """Cuenta qué siembran otras huertas de la zona.

    `usuario_id` es obligatorio, y no por simetría con el resto: es lo que
    excluye la huerta de quien pregunta de sus propios resultados.

    Devuelve siempre un texto enviable. Nunca lanza.
    """
    from app import textos

    fragmentos = await recuperar_comunidad(pregunta, usuario_id=usuario_id)

    if not fragmentos:
        # Dos causas distintas con el mismo remedio: todavía no hay otras
        # huertas registradas, o las que hay no vienen a cuento. No se
        # distinguen en la respuesta porque a la usuaria le da igual el
        # motivo, y explicarle que "no superaron el umbral" no es lenguaje.
        logger.info("CU4 sin fragmentos | usuario_id=%s", usuario_id)
        return textos.COMUNIDAD_SIN_DATOS

    prompt = cargar_prompt(_PROMPT).format(
        contexto=componer_contexto_comunitario(fragmentos),
        pregunta=pregunta,
    )

    try:
        respuesta = await obtener_cliente().aio.models.generate_content(
            model=MODELO_GENERATIVO,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=_TEMPERATURA),
        )
    except Exception:
        logger.exception("Gemini falló al redactar la respuesta del CU4")
        return textos.COMUNIDAD_NO_DISPONIBLE

    # La etiqueta de procedencia es andamiaje del prompt: si el modelo la
    # copió, se retira antes de que la usuaria la lea.
    texto = limpiar_etiquetas(respuesta.text or "")

    if not texto:
        logger.error("La redacción del CU4 devolvió texto vacío")
        return textos.COMUNIDAD_NO_DISPONIBLE

    logger.info(
        "CU4 respondido | huertas=%d | longitud_respuesta=%d",
        len(fragmentos),
        len(texto),
    )

    return texto
