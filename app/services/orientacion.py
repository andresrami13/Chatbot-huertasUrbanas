"""Consulta de orientación agroecológica — CU2 (Fase 2, §5.3).

Une las dos mitades del RAG: `recuperacion.py` trae los fragmentos
pertinentes y aquí se redactan como respuesta para la usuaria.

Es la implementación de la herramienta `consultar_orientacion` del agente
(ADR-0013). Lo que devuelve **se le envía a la usuaria tal cual**, sin
volver a pasar por el modelo: las reglas de abajo son las que sostienen la
jerarquía de fuentes, y una segunda redacción a temperatura 0.7 las
anularía sin dejar rastro.

## Dos caminos que nunca se mezclan

Cuando ninguna fuente oficial supera el umbral, **responde el modelo con lo
que sabe, sin citar nada**. Es el tercer nivel de la jerarquía de fuentes
(CLAUDE.md §6), que siempre estuvo contemplado y que el ADR-0010 había
decidido no usar en el CU2.

Esa decisión se revierte por evidencia de campo: en la primera prueba con
celular, seis de diez consultas acabaron en el texto fijo de "no le puedo
responder", incluidas varias del dominio. El criterio de éxito es un SUS
>= 68 con usuarias de la comunidad, y un asistente que se bloquea seis
veces en una sesión no llega ahí.

**La objeción del ADR-0010 sigue siendo cierta y por eso el diseño es
este.** Aquel decía que la usuaria no distingue un consejo respaldado de
uno advertido *dentro del mismo mensaje*, y tiene razón. Lo que sí
distingue es un mensaje entero de otro, porque el sistema ya se lo enseñó:
las respuestas respaldadas terminan en `Fuente: ...`. Así que:

- o se responde con la guía y se cita **toda** la respuesta,
- o responde el modelo y **no se cita absolutamente nada**,
- nunca medio mensaje de cada, y **el camino lo elige el código**, no el
  modelo: se mira si la recuperación trajo algo.

La consulta que roza el dominio sin pertenecerle —"dónde me inscribo para
que me regalen una compostera"— pasa ahora al modelo. Lo que impide que se
invente una oficina no es el umbral, es la regla 2 de
`prompts/respuesta_general_v1.md`; el umbral nunca supo hacer eso, y con
consultas reales resultó puntuar más alto que una consulta legítima.

## Reversible a propósito

`CU2_RESPALDO_MODELO=false` en Railway devuelve el comportamiento del
ADR-0010 sin desplegar y sin tocar código.

## Lo que este camino NO arregla

Hace que el bot siempre responda; no hace que responda mejor. Un consejo
del modelo no está respaldado por nada, y **vuelve invisible el hueco del
corpus**: hasta hoy, el texto fijo era la señal honesta de que el corpus es
flaco, y es lo que permitió diagnosticarlo. Por eso cada vez que este
camino se toma queda en la bitácora: la Fase 7 tiene que poder decir qué
porcentaje de las respuestas del CU2 fue respaldado. Si sale bajo, la
respuesta es más corpus, no más modelo.
"""

import logging
import re

from google.genai import types

from app.agent.plantillas import cargar_prompt
from app.config import settings
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


# --- Respaldo con conocimiento del modelo ------------------------------

_PROMPT_GENERAL = "respuesta_general_v1.md"

# Más baja todavía que la redacción del RAG, y por el mismo razonamiento
# llevado un paso más allá: allí la variabilidad podía alejar la respuesta
# de la fuente; aquí, donde no hay fuente ninguna, solo puede inventar.
# Calibrable en la Fase 7.
_TEMPERATURA_GENERAL = 0.3

# Lo que el prompt manda responder cuando la pregunta no es del dominio.
# Es una segunda red: el agente ya filtra la intención, pero corre a 0.7 y
# en la prueba real se le midió un error de enrutamiento.
_FUERA_DE_TEMA = "FUERA_DE_TEMA"

# Una línea final de atribución, que es como el modelo la escribe cuando se
# le contagia el formato del otro camino.
_LINEA_FUENTE = re.compile(r"^[ \t]*fuente\s*:.*$", re.IGNORECASE | re.MULTILINE)

# Una atribución metida dentro de la frase. Esta no se puede recortar sin
# reescribir, así que se descarta la respuesta entera: una recomendación que
# se cuelga de una guía oficial que no la respalda es exactamente el daño
# que la jerarquía del §6 existe para impedir.
#
# Solo atrapa la atribución AFIRMATIVA. Es deliberado: "esto no está en la
# guía" es lo contrario de una cita falsa —es la advertencia funcionando— y
# descartar esa respuesta castigaría justo el comportamiento correcto. Al
# nombre de la entidad no se le pide afirmación: el prompt prohíbe
# mencionarla de cualquier forma, y aquí no hay ninguna razón legítima para
# que aparezca.
_ATRIBUCION_INVENTADA = re.compile(
    r"jard[íi]n bot[áa]nico"
    r"|seg[úu]n (la|el|una|un) (gu[íi]a|documento|fuente|manual|cartilla)"
    r"|(la |una )?(gu[íi]a|fuente|informaci[óo]n) oficial\s+"
    r"(dice|indica|se[ñn]ala|recomienda|explica|establece)"
    r"|(el|un) documento (dice|indica|se[ñn]ala|recomienda)",
    re.IGNORECASE,
)


# --- Advertencia sobre contenido de salud -------------------------------
#
# Las fuentes oficiales del corpus traen usos medicinales y toxicidad.
# Medido el 15/08/2026 contra el corpus real: «para qué sirve la limonaria»
# recupera un fragmento que la llama «anticonceptiva» y «antiulceroso», y
# «qué mata es buena para el dolor de estómago» recupera usos tradicionales
# para fiebre y dolor de cabeza. Se responde citando al Jardín Botánico, o
# sea con el sello de fuente verificada del §6.
#
# El documento oficial avala la botánica, no un consejo de salud para una
# persona concreta.
#
# ## Por qué se mira el texto que sale, y no el fragmento que entra
#
# Marcar el fragmento en la ingesta era la otra opción, y cubre menos: no
# alcanza al camino sin respaldo, donde el modelo responde de su propio
# conocimiento y **no hay ningún fragmento que marcar**. Ese camino es
# además el más expuesto, porque ahí la respuesta ni siquiera está atada a
# un documento. Mirando el texto que se va a enviar quedan cubiertos los
# dos caminos y cualquiera que se añada después.
#
# El vocabulario tira a ancho a propósito. Advertir de más cuesta dos
# renglones; advertir de menos falla justo en el mensaje en que importaba.
_HABLA_DE_SALUD = re.compile(
    r"medicinal|medicina|remedio|curativ|terapéutic|terapeutic"
    r"|anticonceptiv|abortiv|emenagog|afrodisíac|afrodisiac"
    r"|antiinflamatori|antibiótic|antibiotic|antiséptic|antiseptic"
    r"|analgésic|analgesic|expectorante|diurétic|diuretic|laxante"
    r"|digestiv|estomáquic|estomaquic|carminativ|antiulceros|antiespasmódic"
    r"|sedante|calmante|cicatrizante|desinflamat|purgante|vermífug"
    r"|t[óo]xic|venenos|intoxicaci[óo]n|contraindicaci"
    r"|\btos\b|\bfiebre\b|\bgripa\b|\bgripe\b|dolor de|dolencia|malestar"
    r"|infusi[óo]n|aromática para|agua de panela para"
    r"|embarazo|lactancia|diabetes|hipertensi[óo]n|presi[óo]n alta"
    r"|colesterol|gastritis|[úu]lcera|insomnio|ansiedad"
    r"|para (la|el) salud|propiedades? (medicinal|curativ|terap)",
    re.IGNORECASE,
)


def _con_advertencia_medica(texto: str) -> str:
    """Añade la advertencia si la respuesta habla de salud.

    Va al final, después de la línea de la fuente, para no romper el
    formato de atribución que exige la regla 4 del prompt del CU2.
    """
    from app import textos

    if not _HABLA_DE_SALUD.search(texto):
        return texto

    # Sin el contenido de la respuesta (CLAUDE.md §11). El contador dice
    # qué proporción del CU2 toca salud, que es dato para la Fase 7 y para
    # el documento de grado.
    logger.info("CU2: se añadió la advertencia médica a la respuesta")

    return f"{texto}\n\n{textos.ADVERTENCIA_MEDICA}"


async def _recuperar_con_respaldo(
    pregunta: str,
    respaldo: str | None,
) -> tuple[list, str]:
    """Recupera con la pregunta y, si no sale nada, con el mensaje entero.

    Existe por una medición del 15/08/2026 que solo pudo aparecer con el
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


async def _responder_sin_respaldo(pregunta: str) -> str:
    """Responde con el conocimiento del modelo, sin citar nada.

    Solo se llega aquí cuando ninguna fuente oficial superó el umbral. La
    respuesta que devuelve **no lleva atribución y no puede llevarla**: es
    lo único que le permite a la usuaria distinguirla de una respaldada.

    Devuelve el texto fijo, y no una disculpa distinta, en tres casos que
    valen lo mismo para ella: que el modelo diga que la pregunta no es del
    dominio, que la llamada falle, y que la respuesta venga con una
    atribución inventada. Los tres se distinguen en la bitácora.
    """
    from app import textos

    prompt = cargar_prompt(_PROMPT_GENERAL).format(pregunta=pregunta)

    try:
        respuesta = await obtener_cliente().aio.models.generate_content(
            model=MODELO_GENERATIVO,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=_TEMPERATURA_GENERAL),
        )
    except Exception:
        logger.exception("Gemini falló al redactar la respuesta sin respaldo")
        return textos.ORIENTACION_NO_DISPONIBLE

    texto = (respuesta.text or "").strip()

    if not texto:
        logger.error("La respuesta sin respaldo del CU2 vino vacía")
        return textos.ORIENTACION_NO_DISPONIBLE

    # El modelo juzgó que la pregunta no es de cultivar. Se le devuelve el
    # texto fijo, que ya está redactado para eso.
    if _FUERA_DE_TEMA in texto:
        logger.info("CU2 sin respaldo: el modelo la dio por ajena al dominio")
        return textos.ORIENTACION_SIN_RESPALDO

    # Una línea de fuente al final es contagio del otro camino y se puede
    # quitar sin tocar el consejo.
    limpio = _LINEA_FUENTE.sub("", texto).strip()
    if limpio != texto:
        # Interesa para la Fase 7: cuenta cuántas veces la regla 1 del
        # prompt no bastó.
        logger.warning("Se retiró una línea de fuente de la respuesta sin respaldo")

    # Una atribución dentro de la frase no se puede recortar sin reescribir
    # el consejo, y dejarla pasar sería peor que callar: la usuaria leería
    # una recomendación avalada por una guía que no la avala.
    if _ATRIBUCION_INVENTADA.search(limpio):
        logger.error(
            "La respuesta sin respaldo del CU2 se atribuyó a una fuente; se descarta"
        )
        return textos.ORIENTACION_SIN_RESPALDO

    # Sin la pregunta ni la respuesta (CLAUDE.md §11). El contador es lo que
    # la Fase 7 necesita para saber qué porcentaje del CU2 fue respaldado.
    logger.info(
        "CU2 respondido SIN respaldo oficial | longitud_respuesta=%d", len(limpio)
    )

    # Este camino es el más expuesto de los dos: la respuesta no está atada
    # a ningún documento, así que si habla de salud lo hace solo con el
    # conocimiento del modelo.
    return _con_advertencia_medica(limpio)


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

        # La bifurcación de los dos caminos, y la decide el código. Al
        # respaldo se le pasa `pregunta`, que a estas alturas ya es el
        # mensaje completo si el recorte del agente no recuperó nada
        # (ver `_recuperar_con_respaldo`): con menos contexto que el otro
        # camino, conviene darle el que hay.
        if settings.CU2_RESPALDO_MODELO:
            return await _responder_sin_respaldo(pregunta)

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

    return _con_advertencia_medica(texto)
