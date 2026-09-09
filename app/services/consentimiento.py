"""Servicio de consentimiento (Fase 3, Tabla 2).

La compuerta previa a todo procesamiento. Sin autorización solo se
atienden el saludo y la ayuda (CU5, contenido estático); cualquier
consulta o registro queda bloqueado, porque todo mensaje libre constituye
tratamiento de datos (Fase 2, §5.1).

Mientras no autorice **no se persiste absolutamente nada**, tampoco el
hecho del rechazo (CU1, flujo alternativo 3a, con la corrección del
ADR-0003).
"""

import logging

from app import textos
from app.core.texto import normalizar
from app.services.repositorio import (
    Usuaria,
    buscar_usuaria,
    registrar_consentimiento,
)
from app.services.whatsapp import enviar_botones, enviar_texto

logger = logging.getLogger(__name__)


# Detección de saludo y ayuda por palabras clave, no con el modelo.
#
# No es una simplificación: para una usuaria que todavía no ha autorizado,
# mandar su mensaje a Gemini YA SERÍA tratamiento de datos, justo lo que
# la compuerta impide. La comparación tiene que resolverse aquí, sin salir
# del backend.
#
# Una vez hay consentimiento, quien decide la intención es el agente por
# function calling (Fase 2, §4).
_SALUDOS = {
    "hola", "holis", "buenas", "buenos dias", "buenas tardes",
    "buenas noches", "buen dia", "que mas", "quiubo", "alo", "hey",
}
_PETICIONES_AYUDA = {
    "ayuda", "ayudame", "menu", "opciones", "info", "informacion",
    "que hace", "que puede hacer", "que haces", "que puedes hacer",
    "como funciona", "para que sirve",
}


def es_saludo_o_ayuda(texto: str | None) -> bool:
    """Indica si el mensaje es un saludo o una petición de ayuda.

    Solo reconoce mensajes cortos: "hola" es un saludo, pero "hola, mi
    tomate tiene bichos" es una consulta con un saludo delante, y tratarla
    como saludo dejaría a la usuaria sin respuesta a lo que preguntó
    (Fase 2, §4).
    """
    if not texto:
        return False

    normalizado = normalizar(texto)
    if not normalizado or len(normalizado.split()) > 4:
        return False

    return normalizado in _SALUDOS or normalizado in _PETICIONES_AYUDA


async def compuerta(
    numero: str,
    texto: str | None,
    boton_id: str | None,
) -> Usuaria | None:
    """Aplica la compuerta a un mensaje entrante.

    Devuelve la usuaria si el mensaje puede seguir al agente, o None si la
    compuerta ya lo atendió (pidió autorización, la registró, o respondió
    la ayuda).
    """
    # 1. La usuaria acepta. Es el único punto del sistema donde se crea
    #    una fila a partir de un mensaje entrante.
    #
    #    Devuelve la usuaria, no None: quien llama tiene que arrancar el
    #    onboarding a continuación (ADR-0016). No se arranca aquí para no
    #    importar `onboarding`, que a su vez necesita `es_saludo_o_ayuda`
    #    de este módulo y formaría un ciclo.
    if boton_id == textos.BOTON_ACEPTO:
        usuaria = await registrar_consentimiento(numero)
        await enviar_texto(numero, textos.CONSENTIMIENTO_ACEPTADO)
        return usuaria

    # 2. La usuaria rechaza. Se responde una sola vez y no se insiste
    #    (ADR-0003). No se guarda nada: el sistema no recuerda el rechazo.
    if boton_id == textos.BOTON_NO_ACEPTO:
        logger.info("Autorización rechazada; no se persiste nada")
        await enviar_texto(numero, textos.CONSENTIMIENTO_RECHAZADO)
        return None

    usuaria = await buscar_usuaria(numero)

    # 3. Ya autorizó: el mensaje sigue su camino.
    if usuaria is not None:
        return usuaria

    # 4. No ha autorizado. Solo la bienvenida y la ayuda están
    #    disponibles; todo lo demás termina en la solicitud de permiso.
    if es_saludo_o_ayuda(texto):
        await enviar_texto(numero, textos.BIENVENIDA)

    await enviar_botones(
        numero,
        textos.SOLICITUD_CONSENTIMIENTO,
        [
            (textos.BOTON_ACEPTO, "Acepto"),
            (textos.BOTON_NO_ACEPTO, "No acepto"),
        ],
    )
    return None
