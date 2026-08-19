"""Acuse de la nota de voz (Fase 7, ADR-0017 revisado el 18/08/2026).

Cuando llega un audio se le dice en el acto que la nota de voz se está
oyendo. Es lo único que queda del aviso de espera: **el del camino con RAG
se retiró el mismo día que se puso**, porque en la prueba con celular la
conversación se sintió más lenta con él que sin él.

Tres cosas que conviene tener claras antes de tocar este módulo:

- **El acuse no entra en la memoria.** Es la excepción declarada a "enviar
  y recordar van juntos" (CLAUDE.md §11): aquí se llama a
  `whatsapp.enviar_texto` y no a `memoria.responder`. El motivo de esa
  regla —que un envío sin registrar deja un hueco que el agente no puede
  detectar— no aplica, porque el acuse no dice nada que el agente vaya a
  necesitar. Recordarlo sí haría daño: gastaría un hueco de los diez de la
  ventana en cada nota de voz.
- **No bloquea.** Sale en una tarea aparte, así que la transcripción
  arranca sin esperar a que Meta conteste.
- **Sin umbral.** Se manda en cuanto se sabe que el mensaje es un audio,
  que es lo que viene en el propio webhook. El retraso configurable que
  tenía se fue con el aviso del RAG: para un acuse que confirma la
  recepción, esperar es justo lo contrario de lo que se busca.
"""

import asyncio
import logging
import random

from app import textos
from app.services.whatsapp import enviar_texto

logger = logging.getLogger(__name__)


class _Baraja:
    """Reparte las frases barajadas y no repite hasta agotarlas.

    Con un sorteo simple, una de cada seis veces le llegaría dos veces
    seguida la misma frase, que es justo lo que delata a una máquina.

    El estado es del proceso, no de la usuaria: en Railway corre una sola
    instancia y dos usuarias distintas compartirían la baraja. Da igual
    —ninguna ve lo que le llega a la otra— y evita una tabla para esto.
    """

    def __init__(self, frases: tuple[str, ...]) -> None:
        self._frases = frases
        self._pendientes: list[str] = []
        self._ultima: str | None = None

    def siguiente(self) -> str:
        if not self._pendientes:
            self._pendientes = random.sample(self._frases, len(self._frases))

            # Al barajar de nuevo, la primera de la tanda puede coincidir
            # con la última de la anterior, y entonces la repetición ocurre
            # igual. Se manda al fondo, que es donde menos estorba. Se saca
            # por el final, así que el fondo es la posición 0.
            if len(self._pendientes) > 1 and self._pendientes[-1] == self._ultima:
                self._pendientes.insert(0, self._pendientes.pop())

        self._ultima = self._pendientes.pop()
        return self._ultima


_BARAJA_AUDIO = _Baraja(textos.ESPERA_AUDIO)

# Sin esto el recolector puede llevarse una tarea antes de que llegue a
# mandar nada: `create_task` no guarda una referencia fuerte.
_EN_VUELO: set[asyncio.Task] = set()


async def _enviar_acuse(numero: str) -> None:
    try:
        await enviar_texto(numero, _BARAJA_AUDIO.siguiente())
        logger.info("Acuse de nota de voz enviado")
    except Exception:
        # Que no salga el acuse no puede tumbar la respuesta: es un
        # acompañamiento, no el contenido.
        logger.exception("Falló el acuse de la nota de voz")


def acusar_audio(numero: str) -> None:
    """Le confirma que la nota de voz llegó. No bloquea."""
    tarea = asyncio.create_task(_enviar_acuse(numero))
    _EN_VUELO.add(tarea)
    tarea.add_done_callback(_EN_VUELO.discard)
