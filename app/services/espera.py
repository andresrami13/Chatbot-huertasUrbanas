"""Aviso de espera mientras el modelo trabaja (Fase 7).

El camino con RAG tarda unos 13 segundos medidos, y una nota de voz más
todavía. Ese silencio es la peor parte de la conversación para alguien que
no sabe si su mensaje llegó, así que se le manda un "deme un momentico"
antes de la respuesta de verdad.

Cuatro cosas que conviene tener claras antes de tocar este módulo:

- **El aviso no entra en la memoria.** Es la única excepción a "enviar y
  recordar van juntos" (CLAUDE.md §11), y por eso aquí se llama a
  `whatsapp.enviar_texto` y no a `memoria.responder`. El motivo está en
  `textos.ESPERA_RAG`.
- **Solo se avisa en los caminos lentos.** El de la ayuda y los pasos del
  onboarding tardan dos o tres segundos: ahí un aviso llegaría pegado a la
  respuesta y se leería como que el bot se trabó, no como atención.
- **Los dos caminos se saben en momentos distintos.** Que sea audio viene
  en el propio webhook; que vaya al RAG lo decide el agente después. De ahí
  que haya dos disparadores y no uno.
- **Un aviso por mensaje.** Un audio que además va al RAG manda solo el de
  la voz, que es el que ya salió.

El estado viaja en un `ContextVar` y no en las firmas. Es lo que asyncio
tiene para esto —estado por petición, propagado solo dentro de la tarea que
atiende ese mensaje— y evita pasar un objeto de mano en mano por
`dispatcher -> agente -> orientacion`, que son tres módulos que no tienen
nada que ver con esto.
"""

import asyncio
import contextvars
import logging
import random
import time
from dataclasses import dataclass, field

from app import textos
from app.config import settings
from app.services.whatsapp import enviar_texto

logger = logging.getLogger(__name__)

AUDIO = "audio"
RAG = "rag"

_FRASES = {AUDIO: textos.ESPERA_AUDIO, RAG: textos.ESPERA_RAG}


class _Baraja:
    """Reparte las frases barajadas y no repite hasta agotarlas.

    Con un sorteo simple, una de cada diez veces le llegaría dos veces
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


_BARAJAS = {tipo: _Baraja(frases) for tipo, frases in _FRASES.items()}


@dataclass
class _Aviso:
    """Lo que hace falta saber para avisar, durante un solo mensaje."""

    numero: str
    recibido_en: float = field(default_factory=time.monotonic)
    tarea: asyncio.Task | None = None
    enviado: bool = False


_actual: contextvars.ContextVar[_Aviso | None] = contextvars.ContextVar(
    "aviso_de_espera", default=None
)


def iniciar_aviso(numero: str) -> None:
    """Marca el comienzo del mensaje. Todavía no programa nada.

    Se llama al empezar a atender, para que el retraso se cuente desde que
    el mensaje entró y no desde que se supo que iba a tardar.
    """
    _actual.set(_Aviso(numero=numero))


async def _avisar(aviso: _Aviso, tipo: str) -> None:
    """Espera lo que falte para el umbral y manda una frase."""
    restante = settings.ESPERA_AVISO_SEGUNDOS - (time.monotonic() - aviso.recibido_en)
    if restante > 0:
        await asyncio.sleep(restante)

    # Antes del envío: si algo falla en la red, el aviso se da por gastado
    # igual. Reintentarlo llegaría después de la respuesta de verdad.
    aviso.enviado = True

    try:
        await enviar_texto(aviso.numero, _BARAJAS[tipo].siguiente())
        logger.info("Aviso de espera enviado | tipo=%s", tipo)
    except Exception:
        # Que no salga el aviso no puede tumbar la respuesta: es un
        # acompañamiento, no el contenido.
        logger.exception("Falló el aviso de espera | tipo=%s", tipo)


def programar_aviso(tipo: str) -> None:
    """Programa el aviso del camino `tipo`, si procede.

    No bloquea: deja una tarea corriendo en paralelo al trabajo de verdad.
    Se ignora en silencio si ya hay un aviso en marcha o ya salió uno, que
    es lo que hace que un audio con RAG mande uno solo.
    """
    aviso = _actual.get()

    if aviso is None or aviso.enviado or aviso.tarea is not None:
        return

    # La referencia se guarda en el propio aviso, que vive en el
    # ContextVar: sin ella el recolector podría llevarse la tarea antes de
    # que llegue a mandar nada.
    aviso.tarea = asyncio.create_task(_avisar(aviso, tipo))


def cancelar_aviso() -> None:
    """Cierra el aviso del mensaje en curso.

    Se llama cuando ya se respondió. Si la tarea seguía esperando el
    umbral, se cancela y la usuaria no ve nada: el trabajo terminó antes de
    lo que se temía y el aviso ya no tiene sentido.

    Queda una rendija de milisegundos: si la respuesta sale justo mientras
    el aviso está viajando, pueden cruzarse y ella lee "deme un momentico"
    después de la respuesta. Es raro y no rompe nada.
    """
    aviso = _actual.get()

    if aviso is None or aviso.tarea is None:
        return

    aviso.tarea.cancel()
    aviso.tarea = None
