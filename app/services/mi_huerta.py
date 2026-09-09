"""Consulta de la propia huerta — CU8 (ADR-0022).

Le dice a la usuaria qué tiene ella registrado: su huerta, su barrio y sus
cultivos. Es la implementación de la herramienta `consultar_mi_huerta` del
agente, y lo que devuelve se envía tal cual.

## Por qué hizo falta, que es lo interesante

Hasta el 09/09/2026 no había ninguna herramienta para esto, y el agente
**contestaba igual**: al no llamar a ninguna función, `agente.py` envía el
texto que el modelo haya escrito, y ese texto sale de la ventana de memoria
—diez mensajes (ADR-0012)—.

Con lo cual respondía **solo el último cultivo**, porque los anteriores ya
se habían salido de la ventana. Reproducido: una usuaria con tomate,
cebolla, lechuga y cilantro en la base recibía *«usted tiene registrado que
sembró cilantro»*.

**El fallo no era que faltara información: era que afirmaba algo falso
sobre los datos de ella**, con el tono del asistente. Es la misma clase de
error que atribuirle cultivos a la huerta equivocada en el CU4.

Y no dependía del modelo. Ninguno puede acertar aquí, porque el dato no
está en la conversación: está en la base.

## El texto lo compone el código

Como el resumen del CU3 (ADR-0008) y como el listado del CU4 (ADR-0021), y
por el mismo motivo: es un reporte de **sus** datos y tiene que reflejarlos
con exactitud. Un modelo que los reformule puede perder un cultivo, y aquí
perder un cultivo es exactamente el fallo que este caso de uso corrige.

## Sin recortes

A diferencia del listado del CU4, aquí **no se recorta la lista de
cultivos**. Allá se enseñan cinco por huerta porque son huertas ajenas y
caben muchas en un mensaje; aquí es su huerta y son sus plantas, y esconder
parte de ellas sería volver al fallo que esto arregla. El tope real es el
del cuerpo de WhatsApp, 1024 caracteres, que da para más de cien especies.

## Precondición

Consentimiento (CU1) y onboarding completado (CU6): sin fila en `huerta` no
hay nada que contar. En la práctica no se llega aquí sin ella, porque el
despachador arranca el onboarding antes (ADR-0016), pero el caso se atiende
igual en vez de dar por hecho que no pasa.
"""

import logging
from uuid import UUID

from app.services.repositorio import (
    listar_cultivos_de_huerta,
    obtener_huerta_de_usuaria,
)

logger = logging.getLogger(__name__)


async def consultar_mi_huerta(usuario_id: UUID) -> str:
    """Le cuenta a la usuaria qué tiene registrado.

    `usuario_id` no es un parámetro más: es la capa 1 del modelo de
    seguridad (Fase 3, §5). Las dos consultas están acotadas por él, así
    que no hay forma de que esto devuelva la huerta de otra persona.

    Devuelve siempre un texto enviable. Nunca lanza.
    """
    from app import textos

    try:
        huerta = await obtener_huerta_de_usuaria(usuario_id)

        if huerta is None:
            # No debería llegar aquí: el despachador arranca el onboarding
            # antes de dejar hablar al agente (ADR-0016). Se atiende de
            # todas formas, porque responder "no tiene huerta" es mejor que
            # una excepción.
            logger.info("CU8 sin huerta | usuario_id=%s", usuario_id)
            return textos.MI_HUERTA_SIN_REGISTRO

        cultivos = await listar_cultivos_de_huerta(huerta.id)

    except Exception:
        logger.exception("Falló la consulta de la propia huerta (CU8)")
        return textos.MI_HUERTA_NO_DISPONIBLE

    # El nombre de la huerta es opcional en el esquema, así que hay dos
    # encabezados y no uno con un hueco que a veces queda vacío.
    if huerta.nombre_huerta:
        encabezado = textos.MI_HUERTA_ENCABEZADO.format(
            huerta=huerta.nombre_huerta, barrio=huerta.barrio_nombre
        )
    else:
        encabezado = textos.MI_HUERTA_ENCABEZADO_SIN_NOMBRE.format(
            barrio=huerta.barrio_nombre
        )

    if not cultivos:
        # Desde el ADR-0016 una huerta sin cultivos es lo normal: existir en
        # `huerta` significa "completó el onboarding", no "registró algo".
        cuerpo = textos.MI_HUERTA_SIN_CULTIVOS
    else:
        cuerpo = textos.MI_HUERTA_CULTIVOS.format(cultivos=", ".join(cultivos))

    # Ni el nombre de la huerta ni las especies (CLAUDE.md §11): cuántas,
    # que es lo que hace falta para saber si el caso de uso se usa.
    logger.info(
        "CU8 respondido | usuario_id=%s | cultivos=%d", usuario_id, len(cultivos)
    )

    return f"{encabezado}\n\n{cuerpo}"
