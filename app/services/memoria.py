"""Memoria de conversación del agente (CLAUDE.md §8, ADR-0012).

Guarda lo que se ha dicho y lo devuelve como ventana de los últimos N
mensajes. Es lo que permite que "y en El Regalo" se entienda como
respuesta a la pregunta anterior y no como una frase suelta.

**Empieza después de la compuerta.** Aquí no entra nada de quien no ha
autorizado: toda función exige `usuario_id`, y ese identificador solo
existe cuando hay consentimiento (CU1). Del rechazo tampoco queda rastro,
conforme al ADR-0003.

Enviar y recordar van juntos, por eso existe `responder`: si cada flujo
enviara por su cuenta y recordara aparte, tarde o temprano alguno enviaría
sin recordar y el agente vería una conversación con huecos que no puede
detectar.
"""

import logging
from uuid import UUID

from app.config import settings
from app.core.identidad import huella_wamid
from app.services.repositorio import (
    Turno,
    registrar_mensaje,
    ultimos_mensajes,
)
from app.services.whatsapp import enviar_botones, enviar_texto

logger = logging.getLogger(__name__)

_ROL_USUARIA = "usuaria"
_ROL_ASISTENTE = "asistente"


async def ventana(usuario_id: UUID) -> list[Turno]:
    """Lo ya hablado, del mensaje más antiguo al más reciente.

    Se lee **después** de registrar el mensaje entrante, no antes: así el
    último elemento de la lista es la pregunta en curso, que es
    exactamente la forma en la que se le entrega la conversación al modelo.
    La ventana la ocupan por tanto 10 mensajes contando ese.

    Si la consulta falla se devuelve una lista vacía en lugar de propagar.
    Un agente sin memoria responde peor —tratará la conversación como si
    empezara ahora—, pero responde; propagar dejaría a la usuaria sin nada.
    """
    try:
        return await ultimos_mensajes(usuario_id, settings.MEMORIA_VENTANA_MENSAJES)
    except Exception:
        logger.exception("No se pudo leer la memoria | usuario_id=%s", usuario_id)
        return []


async def _recordar(
    usuario_id: UUID,
    rol: str,
    contenido: str,
    tipo: str,
    wamid: str | None,
) -> None:
    """Escribe una fila de memoria sin dejar que un fallo tumbe el turno.

    Se traga la excepción a propósito, y conviene entender por qué: cuando
    esto se llama, el mensaje ya se envió o ya se atendió. Propagar el
    fallo dejaría la fila de idempotencia en 'recibido', Meta reintentaría
    y la usuaria recibiría la misma respuesta por segunda vez. Perder una
    línea de memoria es mucho más barato que eso.

    El wamid se convierte en huella aquí. Fuera de este módulo nadie
    manipula huellas, igual que nadie manipula el teléfono cifrado fuera
    del repositorio.
    """
    if not contenido:
        return

    try:
        await registrar_mensaje(
            usuario_id=usuario_id,
            rol=rol,
            contenido=contenido,
            tipo=tipo,
            huella=huella_wamid(wamid) if wamid else None,
        )
    except Exception:
        # Sin el contenido del mensaje en la bitácora (CLAUDE.md §11): solo
        # de quién es la conversación y qué se perdió.
        logger.exception(
            "No se pudo guardar en la memoria | usuario_id=%s | rol=%s",
            usuario_id,
            rol,
        )


async def recordar_usuaria(
    usuario_id: UUID,
    contenido: str,
    tipo: str,
    wamid: str | None,
) -> None:
    """Registra lo que dijo la usuaria, ya normalizado.

    El audio entra transcrito, no como audio: la normalización ocurre una
    sola vez y antes de esto (CLAUDE.md §4.4). `tipo` conserva de todos
    modos cómo llegó, que es el dato que la Fase 7 necesita para medir
    cuánto se usa la voz.
    """
    await _recordar(usuario_id, _ROL_USUARIA, contenido, tipo, wamid)


async def recordar_asistente(
    usuario_id: UUID,
    contenido: str,
    wamid: str | None,
) -> None:
    """Registra lo que respondió el bot.

    El `tipo` es siempre 'text': la columna describe cómo entró el mensaje,
    y las respuestas del bot son texto aunque lleven botones. La respuesta
    por voz está fuera de alcance (CLAUDE.md §9.3).
    """
    await _recordar(usuario_id, _ROL_ASISTENTE, contenido, "text", wamid)


async def responder(numero: str, usuario_id: UUID, texto: str) -> None:
    """Envía un texto a la usuaria y lo deja en la memoria.

    Es la forma normal de responder a alguien que ya autorizó. Antes de la
    compuerta no sirve —no hay `usuario_id`— y allí se usa `enviar_texto`
    directamente, que es lo correcto: esos mensajes no son memoria.
    """
    wamid = await enviar_texto(numero, texto)
    await recordar_asistente(usuario_id, texto, wamid)


async def responder_con_botones(
    numero: str,
    usuario_id: UUID,
    cuerpo: str,
    botones: list[tuple[str, str]],
) -> None:
    """Igual que `responder`, para los dos momentos binarios del diseño.

    Lo que se guarda es el cuerpo del mensaje, no los rótulos: es el texto
    que ella leyó. Cuál pulsó se registra por separado, cuando la pulsación
    vuelve por el webhook.
    """
    wamid = await enviar_botones(numero, cuerpo, botones)
    await recordar_asistente(usuario_id, cuerpo, wamid)
