"""Consulta de orientación agroecológica — CU2 (Fase 2, §5.3).

Une las dos mitades del RAG: `recuperacion.py` trae los fragmentos
pertinentes y aquí se redactan como respuesta para la usuaria.

Es la implementación de la herramienta `consultar_orientacion` del agente
(ADR-0013). Lo que devuelve **se le envía a la usuaria tal cual**, sin
volver a pasar por el modelo: las reglas de abajo son las que sostienen la
jerarquía de fuentes, y una segunda redacción a temperatura 0.7 las
anularía sin dejar rastro.

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
from app.services.recuperacion import (
    componer_contexto,
    limpiar_etiquetas,
    recuperar_orientacion,
)

logger = logging.getLogger(__name__)

_PROMPT = "redaccion_rag_v1.md"

# Fase 4 / CLAUDE.md §8. Más baja que la del agente (0.7) a propósito: aquí
# no se conversa, se reformula lo que dice un documento, y la variabilidad
# solo puede alejar la respuesta de la fuente.
_TEMPERATURA = 0.4


async def _recuperar_con_respaldo(
    pregunta: str,
    respaldo: str | None,
) -> tuple[list, str]:
    """Recupera con la pregunta y, si no sale nada, con el mensaje entero.

    Existe por una medición del 08/08/2026 que solo pudo aparecer con el
    agente delante. Cuando un mensaje trae dos intenciones —"a mi tomate le
    salieron bichos y de paso sembré lechuga el mes pasado"— el agente
    separa la duda del dato, que es lo correcto, y le pasa aquí solo la
    duda. Medido contra el corpus real:

        mensaje completo .................. 0.6840  recupera
        solo la duda, que es lo que pasa .. 0.6796  NO recupera

    Cuatro diezmilésimas. **El umbral de 0.68 se calibró sobre mensajes
    completos** (ADR-0010, 12 consultas), y su margen de una centésima no
    sobrevive a que el agente recorte la consulta: un recorte más corto
    pierde señal, y "que le echo" al final vale casi dos centésimas.

    Por eso el mensaje completo conserva siempre su oportunidad: es la
    formulación sobre la que existe la calibración. El recorte se intenta
    primero porque suele ser mejor —quita el saludo y el ruido—, pero no
    puede quitarle a la usuaria una respuesta que el sistema medido sí le
    daba.

    El coste es una vectorización más, y solo cuando la primera falla.

    Devuelve los fragmentos y la formulación que los encontró, porque es
    esa la que se le pasa al redactor.
    """
    fragmentos = await recuperar_orientacion(pregunta)

    if fragmentos or not respaldo or respaldo == pregunta:
        return fragmentos, pregunta

    fragmentos = await recuperar_orientacion(respaldo)

    if fragmentos:
        # Interesa para la Fase 7: dice cuántas veces el recorte del agente
        # se quedó corto y el mensaje completo salvó la respuesta.
        logger.info("CU2 recuperado con el mensaje completo tras fallar el recorte")

    return fragmentos, respaldo


async def consultar_orientacion(pregunta: str, respaldo: str | None = None) -> str:
    """Responde una consulta agroecológica apoyada en las fuentes oficiales.

    `respaldo` es el mensaje tal como lo escribió la usuaria, cuando quien
    llama recortó la pregunta. Se reintenta con él si el recorte no
    recupera nada. Ver `_recuperar_con_respaldo`.

    Devuelve siempre un texto enviable. Nunca lanza: una consulta fallida
    no debe tumbar la conversación, y la usuaria tiene que recibir algo.
    """
    from app import textos

    fragmentos, pregunta = await _recuperar_con_respaldo(pregunta, respaldo)

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

    # Igual que en el CU4: la etiqueta `[OFICIAL – ...]` es andamiaje del
    # prompt y no puede llegarle a la usuaria.
    texto = limpiar_etiquetas(respuesta.text or "")

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
