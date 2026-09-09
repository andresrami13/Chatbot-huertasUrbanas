"""Lo que siembran otras huertas — CU4 y CU7 (Fase 2, §5.4; ADR-0021).

Es la implementación de la herramienta `consultar_comunidad` del agente
(ADR-0013), y lo que devuelve se envía tal cual.

**Es el agente quien lo enruta**, y por eso estuvo construido y sin
conectar desde el 04/08/2026: decidir que un mensaje es una consulta a la
comunidad con palabras clave sería el clasificador aparte que CLAUDE.md
§4.9 excluye.

## Dos casos de uso por el mismo camino, y hay que separarlos

El ADR-0011 ya había medido que aquí llegan dos clases de pregunta que no
se resuelven igual, pero las atendía la misma tubería:

- **CU4, «¿qué están sembrando las otras huertas?»** es un **listado**. Una
  lista de especies —"cebolla larga, acelga"— se parece poco a esa frase
  por muy correcta que sea la respuesta: medido, se queda en 0.63.
- **CU7, «¿alguien más siembra tomate?»** es una **búsqueda**. La
  similitud la resuelve bien: la huerta con fresas salía a 0.819 y las
  demás por debajo de 0.653.

Mientras las dos compartieron camino, el listado era el respaldo de la
búsqueda: si nada superaba el umbral, se listaba lo más reciente. Eso
escondía un fallo que solo se ve al separarlas — **si ella pregunta por un
cultivo que nadie tiene, la búsqueda no encuentra nada y el respaldo le
contesta con huertas que no lo tienen**.

Hoy la vía la elige el agente antes de recuperar, con el parámetro
`especie`, y cada una puede decir lo que de verdad pasó: que no hay otras
huertas, o que ninguna tiene lo que preguntó.

## El listado lo compone el código (ADR-0021)

Por el mismo motivo que el resumen del CU3 (ADR-0008): un listado es un
reporte de datos y el modelo solo puede restarle. A 0.4 se le caían huertas
para caber en las 70 palabras del prompt —de ahí que respondiera hablando
de una sola teniendo cuatro— y la atribución obligatoria de huerta y barrio
quedaba encomendada a una regla de prompt que ya está medido que se
incumple (`limpiar_etiquetas` existe por eso).

La búsqueda del CU7 sí pasa por el modelo, porque ahí no hay un formato
fijo que componer: responde a lo que ella preguntó.

## En qué se diferencia del CU2, y no es un detalle

El CU2 responde con una **fuente oficial curada**, que es autoridad. Esto
responde con **dato comunitario**, que según la jerarquía de CLAUDE.md §6
va siempre atribuido y **nunca como instrucción técnica**. Que tres huertas
tengan tomate no significa que el tomate se dé bien aquí; significa que
tres vecinas sembraron tomate.

La atribución no es adorno: el barrio no filtra la búsqueda (ADR-0001), así
que se recuperan huertas de barrios distintos al de quien pregunta.

## Precondición

Las dos exigen consentimiento **y datos existentes** (Fase 2). Lo segundo
no está garantizado: con el prototipo recién desplegado puede no haber
ninguna otra huerta registrada, y ese caso se responde con texto fijo.
"""

import logging
from uuid import UUID

from google.genai import types

from app.agent.plantillas import cargar_prompt
from app.config import settings
from app.core.gemini import MODELO_GENERATIVO, obtener_cliente
from app.core.texto import normalizar
from app.services.recuperacion import (
    buscar_en_comunidad,
    componer_contexto_comunitario,
    limpiar_etiquetas,
)
from app.services.repositorio import (
    HuertaDeLaComunidad,
    contar_huertas_con_cultivos,
    guardar_desplazamiento_listado,
    listar_huertas_con_cultivos,
    obtener_desplazamiento_listado,
)

logger = logging.getLogger(__name__)

_PROMPT = "redaccion_comunidad_v2.md"

# La misma que la redacción del RAG (CLAUDE.md §8). Aquí importa incluso
# más: lo que se reformula es una lista de especies ajenas, y la
# creatividad solo puede añadir lo que nadie sembró.
_TEMPERATURA = 0.4


async def consultar_comunidad(
    pregunta: str,
    usuario_id: UUID,
    especie: str | None = None,
) -> str:
    """Cuenta qué siembran otras huertas de la zona.

    `usuario_id` es obligatorio, y no por simetría con el resto: es lo que
    excluye la huerta de quien pregunta de sus propios resultados.

    `especie` es la bandera que separa los dos casos de uso. La rellena el
    agente cuando ella preguntó por un cultivo concreto (CU7); vacía, esto
    es el listado del CU4.

    Devuelve siempre un texto enviable. Nunca lanza.
    """
    if especie:
        return await _buscar_cultivo(pregunta, especie, usuario_id)

    return await _listar_huertas(usuario_id)


# --- CU4: el listado, compuesto por el código -------------------------


def _renglon(huerta: HuertaDeLaComunidad) -> str:
    """Una huerta y sus cultivos en un renglón, con su atribución.

    El tope de cultivos evita que una huerta con quince especies se lleve
    el mensaje entero. Lo que se recorta se dice —"y 3 más"— en lugar de
    desaparecer: callarlo le haría creer que esa huerta tiene solo cinco.
    """
    from app import textos

    tope = settings.CU4_CULTIVOS_POR_HUERTA
    mostrados = huerta.cultivos[:tope]
    faltan = len(huerta.cultivos) - len(mostrados)

    cultivos = ", ".join(mostrados)
    if faltan:
        cultivos += " " + textos.COMUNIDAD_MAS_CULTIVOS.format(faltan=faltan)

    return textos.COMUNIDAD_LISTADO_RENGLON.format(
        huerta=huerta.nombre_huerta or textos.COMUNIDAD_HUERTA_SIN_NOMBRE,
        barrio=huerta.barrio,
        cultivos=cultivos,
    )


async def _listar_huertas(usuario_id: UUID) -> str:
    """Las siguientes huertas del recorrido, con su cola (CU4).

    ## Cómo avanza la paginación, sin detectar «más» en lenguaje natural

    Cada vez que se toma esta vía, el recorrido avanza. Así, volver a
    preguntar lo general —«y las otras?», «cuénteme más»— trae la tanda
    siguiente sin que nadie tenga que interpretar esas palabras: el agente
    ya decidió que esto es una consulta a la comunidad, y eso basta.

    Al llegar al final se vuelve a empezar y **se le avisa**: recibir otra
    vez las tres primeras sin explicación parecería que el bot se trabó.

    Si todas caben en una tanda no se guarda recorrido ninguno. Con dos
    huertas registradas, preguntar dos veces da lo mismo las dos veces, que
    es lo que ella espera.
    """
    from app import textos

    try:
        total = await contar_huertas_con_cultivos(excluir_usuario=usuario_id)

        if not total:
            logger.info("CU4 sin otras huertas | usuario_id=%s", usuario_id)
            return textos.COMUNIDAD_SIN_HUERTAS

        por_tanda = settings.CU4_HUERTAS_POR_TANDA
        pagina = total > por_tanda

        desde = await obtener_desplazamiento_listado(usuario_id) if pagina else 0
        reinicio = desde >= total
        if reinicio:
            desde = 0

        huertas = await listar_huertas_con_cultivos(
            limite=por_tanda, desde=desde, excluir_usuario=usuario_id
        )

        if not huertas:
            # El total encogió entre las dos consultas: alguien borró una
            # huerta justo aquí. Se vuelve al principio en lugar de
            # devolver un listado vacío con su cola.
            logger.warning(
                "El recorrido del listado quedó fuera de rango; se reinicia "
                "| usuario_id=%s | desde=%d | total=%d",
                usuario_id,
                desde,
                total,
            )
            desde, reinicio = 0, True
            huertas = await listar_huertas_con_cultivos(
                limite=por_tanda, desde=0, excluir_usuario=usuario_id
            )

            if not huertas:
                return textos.COMUNIDAD_SIN_HUERTAS

        if pagina:
            await guardar_desplazamiento_listado(usuario_id, desde + len(huertas))

    except Exception:
        logger.exception("Falló el listado de otras huertas del CU4")
        return textos.COMUNIDAD_NO_DISPONIBLE

    faltan = total - (desde + len(huertas))

    lineas = [
        textos.COMUNIDAD_LISTADO_REINICIO
        if reinicio
        else textos.COMUNIDAD_LISTADO_ENCABEZADO,
        "",
    ]
    lineas.extend(_renglon(huerta) for huerta in huertas)

    if faltan > 0:
        cola = (
            textos.COMUNIDAD_LISTADO_COLA_UNA
            if faltan == 1
            else textos.COMUNIDAD_LISTADO_COLA.format(faltan=faltan)
        )
        lineas.extend(["", cola])

    # Ni los nombres de las huertas ni sus cultivos (CLAUDE.md §11): la
    # bitácora no necesita saber qué siembra nadie. Lo que sí hace falta
    # para la Fase 7 es si la paginación se está usando y hasta dónde.
    logger.info(
        "CU4 listado | huertas=%d de %d | desde=%d | reinicio=%s",
        len(huertas),
        total,
        desde,
        reinicio,
    )

    return "\n".join(lineas)


# --- CU7: la búsqueda de un cultivo concreto --------------------------


def _tiene_la_especie(contenido: str, especie: str) -> bool:
    """Si el fragmento de una huerta incluye de verdad esa especie.

    El fragmento comunitario es literalmente la lista de sus especies
    separadas por comas (ADR-0011), así que esto se puede comprobar sin
    modelo y sin margen de error.

    Hace falta porque **el umbral no basta**: con 5 a 7 huertas y top-k=4
    casi cualquier consulta recupera medio corpus (ADR-0011), así que la
    similitud trae huertas que no tienen lo que ella preguntó. Sin esta
    comprobación se le atribuirían cultivos a quien no los sembró, que es
    el peor fallo posible en el dato comunitario.

    Se compara por palabras completas, no por subcadena: «papa» no puede
    dar por buena una huerta que sembró «papaya». Y en la dirección útil sí
    coincide —«cebolla» encuentra «cebolla larga»—, porque quien pregunta
    suele nombrar la especie más corta de lo que está registrada.
    """
    buscada = normalizar(especie)
    if not buscada:
        return False

    return any(
        f" {normalizar(registrada)} ".find(f" {buscada} ") >= 0
        for registrada in contenido.split(",")
    )


async def _buscar_cultivo(pregunta: str, especie: str, usuario_id: UUID) -> str:
    """Qué huertas tienen sembrado el cultivo por el que preguntó (CU7).

    La similitud corre sobre la **pregunta completa**, no sobre `especie`.
    Es deliberado y por dos motivos ya medidos: el umbral comunitario está
    calibrado sobre la forma en que ella escribe (ADR-0011), y el ADR-0013
    dejó dicho lo que pasa cuando el dato lo pone el modelo —«cebolla
    larga» vuelve como «cebolla»—. `especie` decide la vía y filtra el
    resultado; no es la consulta.
    """
    from app import textos

    try:
        fragmentos = await buscar_en_comunidad(pregunta, usuario_id=usuario_id)
        coincidencias = [
            fragmento
            for fragmento in fragmentos
            if _tiene_la_especie(fragmento.contenido, especie)
        ]

        if not coincidencias:
            # Los dos silencios son distintos y hasta el ADR-0021 se
            # respondían igual, porque el código no los distinguía.
            total = await contar_huertas_con_cultivos(excluir_usuario=usuario_id)

            logger.info(
                "CU7 sin coincidencias | usuario_id=%s | recuperados=%d | "
                "otras_huertas=%d",
                usuario_id,
                len(fragmentos),
                total,
            )

            if not total:
                return textos.COMUNIDAD_SIN_HUERTAS

            return textos.COMUNIDAD_SIN_ESE_CULTIVO.format(cultivo=especie)

    except Exception:
        logger.exception("Falló la búsqueda de un cultivo en la comunidad")
        return textos.COMUNIDAD_NO_DISPONIBLE

    prompt = cargar_prompt(_PROMPT).format(
        contexto=componer_contexto_comunitario(coincidencias),
        pregunta=pregunta,
    )

    try:
        respuesta = await obtener_cliente().aio.models.generate_content(
            model=MODELO_GENERATIVO,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=_TEMPERATURA),
        )
    except Exception:
        logger.exception("Gemini falló al redactar la respuesta del CU7")
        return textos.COMUNIDAD_NO_DISPONIBLE

    # La etiqueta de procedencia es andamiaje del prompt: si el modelo la
    # copió, se retira antes de que la usuaria la lea.
    texto = limpiar_etiquetas(respuesta.text or "")

    if not texto:
        logger.error("La redacción del CU7 devolvió texto vacío")
        return textos.COMUNIDAD_NO_DISPONIBLE

    logger.info(
        "CU7 respondido | huertas=%d de %d recuperadas | longitud_respuesta=%d",
        len(coincidencias),
        len(fragmentos),
        len(texto),
    )

    return texto
