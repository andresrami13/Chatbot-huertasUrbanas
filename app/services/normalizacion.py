"""Normalización de la entrada (CLAUDE.md §4.4).

Convierte una nota de voz en texto **una sola vez**, antes de que nada
interprete la intención. Que la transcripción viva aquí y no dentro de cada
flujo es lo que garantiza esa unicidad: a partir de este punto, el resto del
sistema trabaja siempre con texto y no le importa cómo llegó el mensaje.

**Cuándo se invoca importa tanto como qué hace.** Solo después de la
compuerta de consentimiento. Mandar el audio a Gemini es tratamiento de
datos —y transferencia a un tercero fuera del país—, justo lo que la
compuerta impide para quien no ha autorizado (ADR-0006). El despachador es
responsable de ese orden.

La instrucción de transcripción se queda como constante de este módulo y no
va a `app/agent/prompts/`: transcribir es normalización de la entrada
(Fase 5), no una tarea del agente (Fase 6). Los tres prompts versionados que
define CLAUDE.md §11 son los del agente, la extracción y la redacción del
RAG.
"""

import logging

from google.genai import types

from app.core.gemini import MODELO_GENERATIVO, obtener_cliente
from app.services.media import descargar_audio

logger = logging.getLogger(__name__)

# Temperatura 0: transcribir no es una tarea creativa y no interesa que dos
# ejecuciones del mismo audio den resultados distintos. CLAUDE.md §8 no
# recoge este parámetro porque la tabla se escribió antes de que la entrada
# por voz entrara al alcance; queda anotado para incorporarlo.
_TEMPERATURA = 0.0

# Marca que devuelve el modelo cuando no hay nada que transcribir. Hace
# falta un valor explícito: sin él, un audio en blanco devolvería una cadena
# vacía o una disculpa en prosa, y habría que adivinar cuál de las dos.
_SIN_VOZ = "SIN_VOZ"

_INSTRUCCION = f"""Transcriba el audio literalmente.

Contexto: es español de Colombia. Quien habla es una persona de un barrio de
Bogotá que cuenta cosas de su huerta urbana: cultivos, siembras, plagas,
riego. Puede usar nombres locales de plantas.

Reglas:
- Devuelva únicamente la transcripción, sin comentarios ni introducción.
- No traduzca, no corrija la gramática, no resuma y no añada nada.
- Conserve las palabras tal como se dicen.
- Si el audio no tiene voz o no se entiende nada, devuelva exactamente
  {_SIN_VOZ} y nada más."""


async def transcribir_audio(media_id: str) -> str | None:
    """Descarga la nota de voz y devuelve su transcripción.

    Devuelve None si el audio no se pudo descargar, no se pudo transcribir
    o no traía voz. Quien llama decide qué responderle a la usuaria.
    """
    descarga = await descargar_audio(media_id)
    if descarga is None:
        return None

    audio, mime_type = descarga
    return await transcribir_bytes(audio, mime_type, media_id=media_id)


async def transcribir_bytes(
    audio: bytes,
    mime_type: str,
    media_id: str = "-",
) -> str | None:
    """Transcribe un audio ya descargado.

    Separado de la descarga para que un fallo se pueda atribuir a una de
    las dos mitades: la red de Meta o el modelo. `media_id` solo se usa
    para la bitácora.
    """
    try:
        respuesta = await obtener_cliente().aio.models.generate_content(
            model=MODELO_GENERATIVO,
            contents=[
                types.Part.from_bytes(data=audio, mime_type=mime_type),
                _INSTRUCCION,
            ],
            config=types.GenerateContentConfig(temperature=_TEMPERATURA),
        )
    except Exception:
        # Cualquier fallo del modelo (cuota, formato no admitido, filtro de
        # seguridad) termina igual para la usuaria: se le pide que repita.
        logger.exception("Gemini falló al transcribir | media_id=%s", media_id)
        return None

    texto = (respuesta.text or "").strip()

    # Nunca el contenido (CLAUDE.md §11): solo la longitud.
    if not texto or texto == _SIN_VOZ:
        logger.info(
            "El audio no traía voz reconocible | media_id=%s | vacio=%s",
            media_id,
            not texto,
        )
        return None

    logger.info(
        "Audio transcrito | media_id=%s | longitud=%d", media_id, len(texto)
    )
    return texto
