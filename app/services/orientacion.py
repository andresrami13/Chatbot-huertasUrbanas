"""Consulta de orientación agroecológica — CU2 (Fase 2, §5.3).

Une las dos mitades del RAG: `recuperacion.py` trae los fragmentos
pertinentes y aquí se redactan como respuesta para la usuaria.

Será la implementación de la herramienta `consultar_orientacion` cuando
llegue el agente con function calling. Hoy el despachador la invoca
directamente, de forma provisional, para que el CU2 se pueda probar antes
de que exista el agente.

## Lo que NO se hace aquí

**Cuando no se recupera nada, no se le pregunta al modelo de todos modos.**
La respuesta sale de un texto fijo. Es la consecuencia práctica de la
jerarquía de fuentes (CLAUDE.md §6): sin fuente oficial que respalde la
recomendación, el conocimiento del modelo solo puede ofrecerse con
advertencia explícita de que no está verificado, y para un prototipo cuyo
propósito es orientar a huerteras con una guía oficial detrás, una
respuesta sin respaldo vale menos que reconocer que no se sabe.

Es también la salvaguarda barata frente a la consulta que roza el dominio
sin pertenecerle —"dónde me inscribo para que me regalen una compostera"—,
que en la calibración del umbral se quedó a una centésima de colarse
(ADR-0010).
"""

import logging

from google.genai import types

from app.agent.plantillas import cargar_prompt
from app.core.gemini import MODELO_GENERATIVO, obtener_cliente
from app.services.recuperacion import componer_contexto, recuperar_orientacion

logger = logging.getLogger(__name__)

_PROMPT = "redaccion_rag_v1.md"

# Fase 4 / CLAUDE.md §8. Más baja que la del agente (0.7) a propósito: aquí
# no se conversa, se reformula lo que dice un documento, y la variabilidad
# solo puede alejar la respuesta de la fuente.
_TEMPERATURA = 0.4


async def consultar_orientacion(pregunta: str) -> str:
    """Responde una consulta agroecológica apoyada en las fuentes oficiales.

    Devuelve siempre un texto enviable. Nunca lanza: una consulta fallida
    no debe tumbar la conversación, y la usuaria tiene que recibir algo.
    """
    from app import textos

    fragmentos = await recuperar_orientacion(pregunta)

    if not fragmentos:
        logger.info("CU2 sin fragmentos por encima del umbral")
        return textos.ORIENTACION_SIN_RESPALDO

    prompt = cargar_prompt(_PROMPT).format(
        contexto=componer_contexto(fragmentos),
        pregunta=pregunta,
    )

    try:
        respuesta = await obtener_cliente().aio.models.generate_content(
            model=MODELO_GENERATIVO,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=_TEMPERATURA),
        )
    except Exception:
        logger.exception("Gemini falló al redactar la respuesta del CU2")
        return textos.ORIENTACION_NO_DISPONIBLE

    texto = (respuesta.text or "").strip()

    if not texto:
        # Puede pasar si el modelo corta por filtros de seguridad. Sin esto,
        # la usuaria recibiría un mensaje vacío.
        logger.error("La redacción del CU2 devolvió texto vacío")
        return textos.ORIENTACION_NO_DISPONIBLE

    # Nunca la pregunta ni la respuesta (CLAUDE.md §11).
    logger.info(
        "CU2 respondido | fragmentos=%d | longitud_respuesta=%d",
        len(fragmentos),
        len(texto),
    )

    return texto
