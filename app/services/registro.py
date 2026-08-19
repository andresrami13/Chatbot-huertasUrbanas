"""Flujo de registro de la huerta (CU3).

Extraer -> mostrar -> confirmar con botones -> persistir. Los cuatro pasos,
en ese orden, y **nada se guarda antes del botón** (CLAUDE.md §4.7).

El resumen que se le muestra lo compone este módulo con los datos
extraídos, **sin pasar por el modelo**. Es deliberado: la usuaria confirma
lo que va a quedar guardado, así que el texto tiene que reflejarlo con
exactitud. Un resumen redactado por un modelo podría suavizar, omitir o
añadir, y ella estaría autorizando algo distinto de lo que vio.

Entre el resumen y el botón hay dos mensajes de WhatsApp, y la respuesta de
un botón solo trae su identificador. Lo extraído espera en
`registro_pendiente`, no en memoria (ADR-0008).

**Desde el ADR-0018 el borrador lleva solo especies.** La fecha de siembra
salió del CU3 entero —del prompt, del esquema, del resumen y de la tabla
`cultivo`, en la migración 008—, así que el resumen nombra las plantas y
nada más.

**Este es el CU3 conversacional**, el que atiende lo que ella cuente sobre
la marcha. La entrada al sistema la lleva el onboarding (ADR-0016), que ya
fijó el barrio y el nombre de la huerta; aquí solo se añaden cultivos. Por
eso el borrador guarda únicamente cultivos y desapareció la rama de "sin
barrio no hay botones" de la decisión 5 del ADR-0008: con el onboarding
cumplido, el barrio siempre está.
"""

import logging
from uuid import UUID

from app import textos
from app.services.extraccion import CultivoExtraido, HuertaExtraida
from app.services.fragmento_comunitario import regenerar_fragmento
from app.services.memoria import responder, responder_con_botones
from app.services.repositorio import (
    HuertaDeUsuaria,
    agregar_cultivos,
    borrar_borrador,
    guardar_borrador,
    obtener_borrador,
    obtener_huerta_de_usuaria,
)

logger = logging.getLogger(__name__)


def _serializar(extraida: HuertaExtraida) -> dict:
    """Convierte la extracción en el jsonb del borrador."""
    return {"cultivos": [{"especie": c.especie} for c in extraida.cultivos]}


def _deserializar(datos: dict) -> HuertaExtraida:
    """Reconstruye la extracción desde el jsonb del borrador.

    Tolera los borradores de los dos formatos anteriores: el de antes del
    ADR-0016, que llevaba además `nombre_huerta` y `barrio_codigo`, y el de
    antes del ADR-0018, que llevaba `anio`, `mes` y `fecha_imprecisa`. Se
    ignoran esas claves y se conservan los cultivos.

    Sin esa tolerancia, un borrador escrito antes del cambio y confirmado
    después perdería lo que la usuaria ya contó. Duran 24 horas, así que la
    ventana en la que puede pasar es justo la del despliegue.
    """
    return HuertaExtraida(
        cultivos=[
            CultivoExtraido(especie=c["especie"])
            for c in datos.get("cultivos") or []
            if c.get("especie")
        ],
    )


def fusionar(previa: HuertaExtraida, nueva: HuertaExtraida) -> HuertaExtraida:
    """Combina un borrador anterior con lo que la usuaria acaba de decir.

    Hace falta porque la conversación llega a trozos: "sembré tomate" y,
    en el mensaje siguiente, "ah, y también lechuga". Sin fusionar, la
    segunda frase perdería el tomate.

    Los cultivos **se acumulan**, evitando repetir la misma especie. Es lo
    que corresponde a cómo se habla: "también sembré lechuga" añade, no
    sustituye. Y si se colara algo indeseado, ella lo ve en el resumen y
    puede descartar el registro completo.
    """
    especies_nuevas = {c.especie.lower() for c in nueva.cultivos}
    cultivos = list(nueva.cultivos) + [
        c for c in previa.cultivos if c.especie.lower() not in especies_nuevas
    ]

    return HuertaExtraida(cultivos=cultivos)


def componer_resumen(extraida: HuertaExtraida, huerta: HuertaDeUsuaria) -> str:
    """El texto que se le muestra antes de los botones.

    Frases cortas y trato de usted (CLAUDE.md §11). Se cierra con una
    pregunta para que quede claro que hace falta su respuesta.

    El nombre de la huerta y el barrio salen de `huerta`, que es lo que ella
    confirmó en el onboarding, y se muestran para que sepa dónde va a quedar
    lo que se anote. No se le vuelven a pedir.
    """
    lineas = ["Esto es lo que entendí:", ""]

    if huerta.nombre_huerta:
        lineas.append(f"Huerta: {huerta.nombre_huerta}")
    lineas.append(f"Barrio: {huerta.barrio_nombre}")

    if extraida.cultivos:
        lineas.append("")
        lineas.append("Sembrado:")
        for cultivo in extraida.cultivos:
            lineas.append(f"- {cultivo.especie}")

    lineas.append("")
    lineas.append("¿Lo guardo así?")

    return "\n".join(lineas)


async def proponer_registro(
    numero: str,
    usuario_id: UUID,
    extraida: HuertaExtraida,
) -> None:
    """Guarda el borrador y le pide confirmación a la usuaria."""
    huerta = await obtener_huerta_de_usuaria(usuario_id)

    if huerta is None:
        # No completó el onboarding. No debería ocurrir: el despachador lo
        # atiende antes de llamar al agente. Se responde de todos modos,
        # porque callar dejaría en la memoria un hueco que el agente no
        # puede detectar (ADR-0012).
        logger.warning("Registro propuesto sin huerta | usuario_id=%s", usuario_id)
        await responder(numero, usuario_id, textos.REGISTRO_SIN_HUERTA)
        return

    previa = await obtener_borrador(usuario_id)
    if previa is not None:
        extraida = fusionar(_deserializar(previa), extraida)

    await guardar_borrador(usuario_id, _serializar(extraida))

    logger.info(
        "Registro propuesto | usuario_id=%s | cultivos=%d",
        usuario_id,
        len(extraida.cultivos),
    )

    await responder_con_botones(
        numero,
        usuario_id,
        componer_resumen(extraida, huerta),
        [
            (
                textos.BOTON_REGISTRO_CONFIRMO,
                textos.ROTULOS_BOTONES_REGISTRO[textos.BOTON_REGISTRO_CONFIRMO],
            ),
            (
                textos.BOTON_REGISTRO_DESCARTO,
                textos.ROTULOS_BOTONES_REGISTRO[textos.BOTON_REGISTRO_DESCARTO],
            ),
        ],
    )


async def confirmar_registro(numero: str, usuario_id: UUID) -> None:
    """Persiste el borrador. Es el único punto que escribe en `cultivo`."""
    datos = await obtener_borrador(usuario_id)

    if datos is None:
        # Caducó, o pulsó el botón de un mensaje viejo ya resuelto.
        logger.info("Confirmación sin borrador vigente | usuario_id=%s", usuario_id)
        await responder(numero, usuario_id, textos.REGISTRO_SIN_BORRADOR)
        return

    extraida = _deserializar(datos)

    especies = [c.especie for c in extraida.cultivos]

    try:
        huerta_id = await agregar_cultivos(usuario_id=usuario_id, especies=especies)
    except Exception:
        # El borrador NO se borra: así puede reintentar sin volver a
        # contarlo todo.
        logger.exception("Falló el guardado del registro | usuario_id=%s", usuario_id)
        await responder(numero, usuario_id, textos.REGISTRO_FALLO)
        return

    if huerta_id is None:
        # La huerta desapareció entre la propuesta y la confirmación. El
        # borrador se conserva por si vuelve a haberla.
        logger.warning("Confirmación sin huerta | usuario_id=%s", usuario_id)
        await responder(numero, usuario_id, textos.REGISTRO_SIN_HUERTA)
        return

    # Fuera de la transacción y después de confirmar el guardado, a
    # propósito. Regenerar implica una llamada de red al modelo de
    # embeddings, y meterla dentro de la transacción tendría la base
    # bloqueada esperando a un tercero.
    #
    # Que falle no interrumpe el CU3 ni cambia lo que se le responde: los
    # cultivos ya están guardados y el fragmento es un derivado que se puede
    # rehacer (ADR-0004). Lo único que se pierde entretanto es que esa
    # huerta aparezca en el CU4, y `regenerar_fragmento` deja constancia en
    # la bitácora para poder repararlo.
    await regenerar_fragmento(huerta_id)

    await borrar_borrador(usuario_id)
    await responder(numero, usuario_id, textos.REGISTRO_GUARDADO)


async def descartar_registro(numero: str, usuario_id: UUID) -> None:
    """Tira el borrador sin guardar nada."""
    await borrar_borrador(usuario_id)
    logger.info("Registro descartado por la usuaria | usuario_id=%s", usuario_id)
    await responder(numero, usuario_id, textos.REGISTRO_DESCARTADO)
