"""Despachador asíncrono de eventos de WhatsApp.

Recorre la estructura anidada del payload de Meta, descarta duplicados por
huella del wamid y deriva cada mensaje al flujo correspondiente.

La idempotencia vive ya en Supabase, con dos estados, y no en memoria
(ADR-0005). Aquí solo se reclama y se cierra; la mecánica está en
`repositorio.reclamar_wamid`.

Orden del flujo general (Fase 2, §5.1): primero la compuerta de
consentimiento y solo después el resto. Centralizarlo aquí evita
duplicarlo en cada flujo y cierra la posibilidad de procesar datos de
alguien que no ha autorizado.

Orden interno, y el orden importa: identificar el mensaje -> compuerta de
consentimiento -> normalización de la entrada -> memoria -> intención. La
transcripción va **después** de la compuerta a propósito (ADR-0006), y la
memoria después de la transcripción, para que el audio quede guardado ya
convertido en texto (ADR-0012).

Pendiente de conectar: el agente orquestador. Hasta que exista, la
intención se resuelve de forma provisional —saludo y ayuda por palabras
clave, y cualquier otro mensaje como posible registro de huerta—. En la
Fase 6 esa decisión pasa al function calling (Fase 2, §4).
"""

import logging

from app import textos
from app.core.identidad import huella_wamid, referencia_wamid
from app.services.consentimiento import compuerta, es_saludo_o_ayuda
from app.services.extraccion import extraer_huerta
from app.services.memoria import recordar_usuaria, responder
from app.services.normalizacion import transcribir_audio
from app.services.orientacion import consultar_orientacion
from app.services.registro import (
    confirmar_registro,
    descartar_registro,
    proponer_registro,
)
from app.services.repositorio import (
    listar_barrios,
    marcar_procesado,
    reclamar_wamid,
)
from app.services.whatsapp import enviar_texto

logger = logging.getLogger(__name__)

async def procesar_evento(payload: dict) -> None:
    """Punto de entrada del procesamiento en segundo plano."""
    try:
        for entrada in payload.get("entry", []):
            for cambio in entrada.get("changes", []):
                valor = cambio.get("value", {})

                # Acuses de entrega y lectura. No requieren acción, pero
                # sirven para diagnosticar problemas de envío.
                for estado in valor.get("statuses", []):
                    identificador = estado.get("id")
                    logger.info(
                        "Acuse | ref=%s | estado=%s",
                        referencia_wamid(identificador) if identificador else "-",
                        estado.get("status"),
                    )

                for mensaje in valor.get("messages", []):
                    await _procesar_mensaje(mensaje)

    except Exception:
        # El despachador corre fuera del ciclo de la petición: si estalla
        # aquí, la excepción se pierde en silencio. Registrarla es la
        # única forma de enterarse.
        logger.exception("Error no controlado procesando el evento")


async def _procesar_mensaje(mensaje: dict) -> None:
    """Reclama el mensaje, lo atiende y solo entonces lo cierra.

    El orden es el que exige el ADR-0005: `procesado` se marca **al
    terminar bien**, nunca al empezar. Si el trabajo falla, la fila se deja
    en `recibido` y al vencer el plazo el reintento de Meta lo vuelve a
    tomar, en lugar de descartarlo como duplicado y perderlo en silencio.
    """
    wamid = mensaje.get("id")
    if not wamid:
        logger.warning("Mensaje sin wamid; se descarta")
        return

    # Todo lo que salga a la bitácora usa la referencia, nunca el wamid.
    ref = referencia_wamid(wamid)
    huella = huella_wamid(wamid)

    if not await reclamar_wamid(huella):
        logger.info("Duplicado o ya en curso; se descarta | ref=%s", ref)
        return

    try:
        await _atender_mensaje(mensaje, ref)
    except Exception:
        # Se deja a propósito en 'recibido': es lo que permite recuperarlo.
        logger.exception("Fallo atendiendo el mensaje | ref=%s", ref)
        return

    await marcar_procesado(huella)


async def _atender_mensaje(mensaje: dict, ref: str) -> None:
    """El trabajo en sí. Que lance una excepción es aceptable: quien llama
    la captura y deja el mensaje disponible para el reintento."""
    tipo = mensaje.get("type")
    numero = mensaje.get("from")

    # Minimización de datos (Fase 3, capa 6): no se registra el número del
    # remitente ni el contenido del mensaje en la bitácora. Tampoco el
    # wamid, que contiene el número (ver `huella_wamid`).
    logger.info("Mensaje entrante | tipo=%s | ref=%s", tipo, ref)

    if not numero:
        logger.warning("Mensaje sin remitente; se descarta | ref=%s", ref)
        return

    texto: str | None = None
    boton_id: str | None = None
    media_id_audio: str | None = None

    if tipo == "text":
        texto = mensaje.get("text", {}).get("body", "")
        logger.info("Texto recibido | longitud=%d", len(texto))

    elif tipo == "interactive":
        interactivo = mensaje.get("interactive", {})
        boton_id = interactivo.get("button_reply", {}).get("id")
        logger.info("Botón pulsado | id=%s", boton_id)

    elif tipo == "audio":
        media_id_audio = mensaje.get("audio", {}).get("id")
        logger.info("Audio recibido | media_id=%s", media_id_audio)
        # Solo se guarda el identificador. NO se transcribe aquí: hacerlo
        # antes de la compuerta sería mandar a Gemini el audio de alguien
        # que quizá no ha autorizado, que es exactamente lo que el
        # ADR-0006 impide. La transcripción va más abajo.

    else:
        logger.info("Tipo de mensaje no soportado aún | tipo=%s", tipo)

    # Compuerta de consentimiento. Si devuelve None, ya atendió el
    # mensaje: pidió autorización, la registró o respondió la ayuda.
    #
    # El audio llega aquí sin texto, y es correcto: quien no ha autorizado
    # recibe la solicitud de permiso, sin que su voz salga del backend.
    usuaria = await compuerta(numero, texto, boton_id)
    if usuaria is None:
        return

    # A partir de aquí la usuaria ya autorizó.

    # Normalización de la entrada (CLAUDE.md §4.4). Una sola vez, en un
    # único sitio y antes de interpretar la intención: de aquí en adelante
    # da igual si el mensaje llegó escrito o hablado.
    if media_id_audio is not None:
        texto = await transcribir_audio(media_id_audio)
        if texto is None:
            # No se registra nada en la memoria: no hay contenido que
            # guardar, y anotar solo la disculpa dejaría una respuesta sin
            # la pregunta que la provocó (ADR-0012).
            await enviar_texto(numero, textos.AUDIO_NO_ENTENDIDO)
            return

    # Memoria de la conversación (ADR-0012). Aquí y no antes: después de la
    # compuerta, así que nunca entra un mensaje de quien no ha autorizado, y
    # después de transcribir, así que el audio queda guardado ya en texto.
    #
    # Se registra el mensaje entrante ANTES de atenderlo. Es lo que hace
    # que la ventana termine siempre en lo que la usuaria acaba de decir,
    # que es la forma en la que el agente la va a necesitar.
    await recordar_usuaria(
        usuaria.id,
        _contenido_recordable(texto, boton_id),
        _tipo_entrante(media_id_audio, boton_id),
        mensaje.get("id"),
    )

    # Botones del registro (CU3). Van antes de cualquier interpretación:
    # una pulsación no es un mensaje que haya que entender, es una respuesta
    # a algo que ya se le preguntó.
    if boton_id == textos.BOTON_REGISTRO_CONFIRMO:
        await confirmar_registro(numero, usuaria.id)
        return

    if boton_id == textos.BOTON_REGISTRO_DESCARTO:
        await descartar_registro(numero, usuaria.id)
        return

    # Provisional: mientras no exista el agente, el saludo y la ayuda se
    # resuelven por palabras clave. Cuando entre el agente, esta decisión
    # pasa a ser suya por function calling (Fase 2, §4).
    #
    # Ahora también alcanza a las notas de voz: un "hola" hablado llega
    # aquí ya como texto.
    if es_saludo_o_ayuda(texto):
        await responder(numero, usuaria.id, textos.BIENVENIDA)
        return

    if not texto:
        logger.info("Mensaje sin texto que interpretar | ref=%s", ref)
        return

    # Registro de la huerta (CU3). Provisional en un punto: mientras no
    # exista el agente, todo mensaje libre se trata como un posible registro.
    # Cuando entre el function calling será él quien decida entre registrar,
    # consultar orientación o consultar a la comunidad (Fase 2, §4).
    extraida = await extraer_huerta(texto)

    if extraida.tiene_datos:
        barrios = await listar_barrios()
        await proponer_registro(
            numero,
            usuaria.id,
            extraida,
            {barrio.codigo: barrio.nombre for barrio in barrios},
        )
        return

    # No había nada que registrar y no es un saludo: se trata como consulta
    # de orientación agroecológica (CU2).
    #
    # Provisional en el mismo sentido que las ramas de arriba: quien debe
    # decidir que esto es una consulta y no otra cosa es el function
    # calling (Fase 2, §4). Mientras tanto es la rama por defecto, que era
    # la que hasta ahora callaba.
    logger.info("Consulta de orientación | usuario_id=%s | ref=%s", usuaria.id, ref)
    await responder(numero, usuaria.id, await consultar_orientacion(texto))


def _tipo_entrante(media_id_audio: str | None, boton_id: str | None) -> str:
    """Cómo llegó el mensaje, antes de normalizarlo.

    No es lo mismo que el contenido que se guarda: una nota de voz se
    almacena transcrita pero se anota como 'audio', que es lo que la Fase 7
    necesita para medir cuánto se usa la voz frente a la escritura.
    """
    if boton_id is not None:
        return "interactive"
    if media_id_audio is not None:
        return "audio"
    return "text"


def _contenido_recordable(texto: str | None, boton_id: str | None) -> str:
    """El texto que se guarda en la memoria, o cadena vacía si no hay.

    De una pulsación se guarda el rótulo que la usuaria leyó en el botón,
    no su identificador interno: "Sí, guardar" se entiende leyendo la
    conversación, `registro_confirmo` no.

    Los botones del consentimiento no llegan hasta aquí —la compuerta los
    atiende y corta—, así que solo hay que contemplar los del CU3. Un
    identificador desconocido no se anota: sería una fila de basura en la
    memoria del agente.
    """
    if boton_id is not None:
        return textos.ROTULOS_BOTONES_REGISTRO.get(boton_id, "")

    return texto or ""
