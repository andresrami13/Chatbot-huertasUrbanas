"""Onboarding de tres preguntas cerradas (CU3, ADR-0016).

Nombre de pila, barrio y nombre de la huerta, **una pregunta por mensaje**.
Hasta el 17/08/2026 las tres se pedían juntas en un solo mensaje libre, y de
ahí salía una extracción pobre: era la causa raíz del CU3.

Cuatro cosas que conviene tener claras antes de tocar este módulo:

- **La confirmación es implícita.** El eco de lo que ella contestó va dentro
  de la pregunta siguiente, sin pedir un "sí" aparte. La única confirmación
  explícita es la del final, con los botones que ya existen del CU3.
- **"guardé" y "anoté" no son sinónimos.** El nombre se persiste en el acto,
  porque su fila de `usuario` existe desde el consentimiento; el barrio y el
  nombre de la huerta esperan al botón. Decirle "guardé" de esos dos sería
  falso en ese instante.
- **Al terminar se crea la fila de `huerta`**, aunque no haya contado ningún
  cultivo. Desde el ADR-0016 esa fila significa "completó el onboarding", no
  "registró algo": es el indicador que evita repetirle las preguntas.
- **El barrio se desambigua con una lista numerada de texto, no con
  botones.** WhatsApp limita el rótulo de un botón a 20 caracteres y el 24 %
  de los barrios de Bosa pasa de ahí; recortarlos deja seis grupos con el
  mismo rótulo. Como no hay botones, no hace falta enmendar el §4.3 de
  CLAUDE.md: siguen apareciendo solo en el consentimiento y en la
  confirmación.

El CU5 no tiene precondición: si escribe "ayuda" a mitad del onboarding se
le da el texto fijo y **se repite la pregunta pendiente**, sin gastar un
intento (ADR-0006).
"""

import json
import logging
import unicodedata
from uuid import UUID

from google.genai import types

from app import textos
from app.agent.plantillas import cargar_prompt
from app.core.gemini import MODELO_GENERATIVO, obtener_cliente
from app.services.consentimiento import es_saludo_o_ayuda
from app.services.memoria import responder, responder_con_botones
from app.services.repositorio import (
    Barrio,
    borrar_onboarding,
    guardar_huerta,
    guardar_onboarding,
    listar_barrios,
    obtener_huerta_de_usuaria,
    obtener_onboarding,
    registrar_consentimiento,
)

logger = logging.getLogger(__name__)

_PROMPT_BARRIO = "barrio_v1.md"

# Misma temperatura que la extracción de entidades y por el mismo motivo:
# el formato es estricto y la variabilidad solo puede estropearlo. A los 0.7
# del agente aplicaría el aviso de CLAUDE.md §12 sobre no fiarse del primer
# resultado; con esquema cerrado y 0.1, no.
_TEMPERATURA_BARRIO = 0.1

# Tres candidatos más la salida. Con botones solo cabían dos, porque
# WhatsApp admite tres botones en total; en texto el techo lo pone la
# legibilidad, no la API.
_MAXIMO_CANDIDATOS = 3

# Cuántas veces tiene que decir "Ninguno de estos" antes de que aparezca la
# quinta opción. Ofrecerla desde el principio degradaría el dato del barrio,
# que es el que sostiene la atribución del CU4 (ADR-0001): sería el camino
# corto. Tres rondas son evidencia razonable de que su barrio no está.
_NINGUNO_PARA_OFRECER_OTRO = 3

# Código del catálogo que absorbe el barrio no previsto (ADR-0002).
_CODIGO_OTRO = "otro"

PASO_NOMBRE = "nombre"
PASO_BARRIO = "barrio"
PASO_BARRIO_OPCIONES = "barrio_opciones"
PASO_HUERTA = "huerta"
PASO_CONFIRMACION = "confirmacion"

# Salidas que se le ofrecen al segundo intento fallido. No son un reproche:
# son una puerta para quien no quiera dar el dato.
_SALIDA_NOMBRE = {"vecina", "vecino"}

_PALABRAS_NUMERO = {"uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5}

_ESQUEMA_BARRIO = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "codigos": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
        ),
    },
    required=["codigos"],
)


def _normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y sin signos, para comparar."""
    sin_tildes = "".join(
        c
        for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(
        "".join(c for c in sin_tildes if c.isalnum() or c.isspace()).split()
    )


# Emoji de teclado para numerar las opciones. Se ven como un número
# metido en una tecla, y a simple vista dicen "aquí toca escribir un
# número" mejor que un "1." al principio del renglón.
#
# Ella sigue escribiendo el dígito normal de su teclado, y eso es lo que
# le pide `ONBOARDING_NUMERO_NO_ENTENDIDO`. Pero si copia el emoji de la
# lista y lo manda, también vale: `_normalizar` le quita el envolvente
# (categoría Me) y el selector de variación (Mn) y deja el dígito solo.
# Comprobado: "3", "tres" y "3️⃣" dan los tres 3.
_DIGITOS_EMOJI = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
                  "6️⃣", "7️⃣", "8️⃣", "9️⃣")


def _vineta(indice: int) -> str:
    """El número de una opción, como emoji de teclado.

    Por encima de nueve no hay emoji y se cae al texto de siempre. Hoy no
    puede ocurrir —tres candidatos más las dos salidas son cinco—, pero
    subir el número de candidatos es justo de lo que la Fase 7 tiene que
    decidir, y no vale que reviente por eso.
    """
    return _DIGITOS_EMOJI[indice - 1] if 1 <= indice <= 9 else f"{indice}."


def leer_numero(texto: str | None, maximo: int) -> int | None:
    """Interpreta la respuesta a una lista numerada. None si no es un número.

    Acepta el dígito y la palabra —`3` y `tres`— y nada más. La palabra no es
    una concesión sino un requisito de la entrada por voz: la transcripción
    es literal (`normalizacion.py`), así que una nota de voz diciendo "tres"
    llega como `tres` en letras y nunca como dígito. Con un lector de solo
    dígitos, quien responde por voz recibiría "No entendí" para siempre y
    —como el barrio es obligatorio— no podría terminar el onboarding.

    Se descarta todo lo demás: "la de arriba", "Holanda sector 3", un saludo.
    Sin modelo y sin temperatura, igual que `es_saludo_o_ayuda` (ADR-0006).
    """
    if not texto:
        return None

    normalizado = _normalizar(texto)

    if normalizado.isdigit():
        numero = int(normalizado)
    elif normalizado in _PALABRAS_NUMERO:
        numero = _PALABRAS_NUMERO[normalizado]
    else:
        return None

    return numero if 1 <= numero <= maximo else None


def _es_respuesta_util(texto: str | None, maximo_palabras: int) -> bool:
    """Filtro determinista para el nombre y el nombre de la huerta.

    No valida que sea un nombre de verdad —eso no se puede—, solo descarta
    lo que claramente no lo es: vacío, una pregunta, o una frase larga. Que
    se cuele algo raro lo corrige ella en la confirmación final, que muestra
    los tres datos antes de guardar.
    """
    if not texto or "?" in texto or "¿" in texto:
        return False

    normalizado = _normalizar(texto)
    if not normalizado:
        return False

    return len(normalizado.split()) <= maximo_palabras


async def _buscar_candidatos(texto: str) -> list[Barrio]:
    """Los barrios del catálogo que más se parecen a lo que ella escribió.

    Lo resuelve el modelo y no una búsqueda por trigramas (`pg_trgm`), por
    dos motivos medidos: el catálogo trae variantes que comparten el
    arranque del nombre —`HOLANDA`, `HOLANDA I SECTOR`, `HOLANDA SECTOR
    CAMINITO`— y la similitud de cadenas no distingue el barrio base de sus
    variantes, mientras que el modelo sí; y `pg_trgm` traía un umbral nuevo
    que calibrar en la Fase 7, que ya arrastra la revalidación del 0.68.

    El coste del catálogo entero en el prompt se paga **una vez por
    usuaria**, no en cada mensaje como ocurriría en la extracción.

    Nunca lanza: si el modelo falla se devuelve la lista vacía y quien llama
    le pide que lo escriba otra vez.
    """
    barrios = await listar_barrios()
    if not barrios:
        logger.error("El catálogo de barrios está vacío; falta ejecutar 003")
        return []

    por_codigo = {barrio.codigo: barrio for barrio in barrios}

    prompt = cargar_prompt(_PROMPT_BARRIO).format(
        maximo=_MAXIMO_CANDIDATOS,
        barrios="\n".join(f"- `{b.codigo}` — {b.nombre}" for b in barrios),
        mensaje=texto,
    )

    try:
        respuesta = await obtener_cliente().aio.models.generate_content(
            model=MODELO_GENERATIVO,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=_TEMPERATURA_BARRIO,
                response_mime_type="application/json",
                response_schema=_ESQUEMA_BARRIO,
            ),
        )
        datos = json.loads(respuesta.text or "{}")
    except Exception:
        logger.exception("Falló la búsqueda de candidatos de barrio")
        return []

    # El esquema no puede llevar el enum de 300 códigos sin inflar cada
    # llamada, así que se valida aquí: un código inventado se descarta en
    # vez de acabar en un botón que no lleva a ninguna parte.
    candidatos: list[Barrio] = []
    for codigo in datos.get("codigos") or []:
        barrio = por_codigo.get(codigo)
        if barrio is not None and barrio not in candidatos:
            candidatos.append(barrio)

    logger.info("Candidatos de barrio | encontrados=%d", len(candidatos))
    return candidatos[:_MAXIMO_CANDIDATOS]


def componer_opciones(
    candidatos: list[tuple[str, str]],
    ofrecer_otro: bool,
) -> tuple[str, int]:
    """El mensaje con la lista numerada y cuántas opciones tiene.

    `candidatos` son pares (código, nombre). Devuelve el texto y el número
    más alto válido, que es lo que `leer_numero` necesita para acotar.

    Los nombres van completos: el cuerpo de un mensaje admite 1024
    caracteres, así que no hay que recortar nombres oficiales ni arriesgarse
    a que dos opciones queden con el mismo texto.
    """
    lineas = [textos.ONBOARDING_BARRIO_ENCABEZADO, ""]

    for indice, (_, nombre) in enumerate(candidatos, 1):
        lineas.append(f"{_vineta(indice)} {nombre}")

    total = len(candidatos) + 1
    lineas.append(f"{_vineta(total)} {textos.ONBOARDING_OPCION_NINGUNO}")

    if ofrecer_otro:
        total += 1
        lineas.append(f"{_vineta(total)} {textos.ONBOARDING_OPCION_OTRO}")

    return "\n".join(lineas), total


def componer_resumen(nombre: str | None, barrio: str, huerta: str) -> str:
    """El texto que se le muestra antes de los botones del cierre.

    Lo compone el código y no el modelo, por el mismo criterio de la
    decisión 4 del ADR-0008: ella confirma lo que va a quedar guardado, así
    que el texto tiene que reflejarlo con exactitud.
    """
    lineas = ["Esto es lo que voy a guardar:", ""]

    if nombre:
        lineas.append(f"Nombre: {nombre}")
    lineas.append(f"Barrio: {barrio}")
    lineas.append(f"Huerta: {huerta}")

    lineas.append("")
    lineas.append("¿Lo guardo así?")

    return "\n".join(lineas)


async def _preguntar(
    numero: str,
    usuario_id: UUID,
    paso: str,
    datos: dict,
    texto: str,
) -> None:
    """Guarda el estado y hace la pregunta correspondiente."""
    await guardar_onboarding(usuario_id, paso, datos)
    await responder(numero, usuario_id, texto)


async def iniciar_onboarding(numero: str, usuario_id: UUID) -> None:
    """Arranca el onboarding por la primera pregunta.

    Se llama justo después de que ella acepte, y también cuando vuelve
    pasadas 24 horas sin haberlo terminado: en ese caso se repiten las tres
    preguntas y lo que conteste sobrescribe lo que hubiera, que es más
    simple que llevar la cuenta de qué había contestado.
    """
    logger.info("Onboarding iniciado | usuario_id=%s", usuario_id)
    await _preguntar(
        numero,
        usuario_id,
        PASO_NOMBRE,
        {"fallos": 0},
        textos.ONBOARDING_PREGUNTA_NOMBRE,
    )


async def atender_onboarding(
    numero: str,
    usuario_id: UUID,
    texto: str | None,
    boton_id: str | None,
) -> bool:
    """Atiende el mensaje si el onboarding está en curso.

    Devuelve True si lo atendió, y entonces el despachador no sigue: mientras
    no complete las tres preguntas no hay huerta donde registrar nada, y el
    agente no tiene nada que enrutar.

    Devuelve False si no hay onboarding que atender, es decir, si ya lo
    completó.
    """
    estado = await obtener_onboarding(usuario_id)

    if estado is None:
        # Sin estado hay dos casos: ya completó el onboarding (tiene huerta)
        # o lo abandonó y caducó. En el segundo se vuelve a empezar.
        if await obtener_huerta_de_usuaria(usuario_id) is not None:
            return False

        await iniciar_onboarding(numero, usuario_id)
        return True

    # El CU5 no tiene precondición: se atiende la ayuda y se repite la
    # pregunta pendiente, sin gastar un intento (ADR-0006). Va antes que
    # nada porque "ayuda" es una respuesta válida a cualquier paso.
    if es_saludo_o_ayuda(texto):
        logger.info("Ayuda dentro del onboarding | paso=%s", estado.paso)
        await responder(numero, usuario_id, textos.BIENVENIDA)
        await _repetir_pregunta(numero, usuario_id, estado.paso, estado.datos)
        return True

    if estado.paso == PASO_NOMBRE:
        await _atender_nombre(numero, usuario_id, texto, estado.datos)
    elif estado.paso == PASO_BARRIO:
        await _atender_barrio(numero, usuario_id, texto, estado.datos)
    elif estado.paso == PASO_BARRIO_OPCIONES:
        await _atender_opcion_barrio(numero, usuario_id, texto, estado.datos)
    elif estado.paso == PASO_HUERTA:
        await _atender_huerta(numero, usuario_id, texto, estado.datos)
    elif estado.paso == PASO_CONFIRMACION:
        await _atender_confirmacion(numero, usuario_id, boton_id, estado.datos)
    else:
        # Paso desconocido: el estado quedó de una versión anterior. Se
        # reinicia en lugar de dejarla atascada.
        logger.warning("Paso de onboarding desconocido | paso=%s", estado.paso)
        await iniciar_onboarding(numero, usuario_id)

    return True


async def _repetir_pregunta(
    numero: str,
    usuario_id: UUID,
    paso: str,
    datos: dict,
) -> None:
    """Vuelve a hacer la pregunta del paso en curso, sin contar el intento."""
    if paso == PASO_BARRIO_OPCIONES:
        candidatos = [tuple(c) for c in datos.get("candidatos") or []]
        mensaje, _ = componer_opciones(
            candidatos,
            datos.get("intentos_ninguno", 0) >= _NINGUNO_PARA_OFRECER_OTRO,
        )
    elif paso == PASO_BARRIO:
        mensaje = textos.ONBOARDING_PREGUNTA_BARRIO
    elif paso == PASO_HUERTA:
        mensaje = textos.ONBOARDING_PREGUNTA_HUERTA
    elif paso == PASO_CONFIRMACION:
        # Lleva botones, así que se rehace entero por el camino que los pone.
        await _proponer_cierre(numero, usuario_id, datos)
        return
    else:
        mensaje = textos.ONBOARDING_PREGUNTA_NOMBRE

    await responder(numero, usuario_id, mensaje)


async def _atender_nombre(
    numero: str,
    usuario_id: UUID,
    texto: str | None,
    datos: dict,
) -> None:
    """Primera pregunta: el nombre de pila, sin apellido."""
    fallos = datos.get("fallos", 0)

    if not _es_respuesta_util(texto, maximo_palabras=4):
        fallos += 1
        datos["fallos"] = fallos
        # Al segundo fallo se le ofrece la salida; al primero solo se
        # repite la pregunta.
        mensaje = (
            textos.ONBOARDING_NOMBRE_REINTENTO
            if fallos >= 2
            else textos.ONBOARDING_PREGUNTA_NOMBRE
        )
        await _preguntar(numero, usuario_id, PASO_NOMBRE, datos, mensaje)
        return

    nombre = (texto or "").strip()

    # El nombre se persiste YA, cifrado, porque su fila de `usuario` existe
    # desde el consentimiento. `registrar_consentimiento` es idempotente y
    # hace coalesce sobre el nombre, así que sirve para completarlo sin una
    # función nueva. Por eso el eco dice "guardé" y no "anoté".
    await registrar_consentimiento(numero, nombre)

    logger.info("Onboarding: nombre guardado | usuario_id=%s", usuario_id)

    await _preguntar(
        numero,
        usuario_id,
        PASO_BARRIO,
        {"fallos": 0, "nombre": nombre},
        textos.ONBOARDING_ECO_NOMBRE.format(nombre=nombre)
        + "\n\n"
        + textos.ONBOARDING_PREGUNTA_BARRIO,
    )


async def _atender_barrio(
    numero: str,
    usuario_id: UUID,
    texto: str | None,
    datos: dict,
) -> None:
    """Segunda pregunta: el barrio, en lenguaje natural."""
    if not _es_respuesta_util(texto, maximo_palabras=8):
        await _preguntar(
            numero,
            usuario_id,
            PASO_BARRIO,
            datos,
            textos.ONBOARDING_BARRIO_REINTENTO,
        )
        return

    candidatos = await _buscar_candidatos(texto or "")

    if not candidatos:
        await _preguntar(
            numero,
            usuario_id,
            PASO_BARRIO,
            datos,
            textos.ONBOARDING_BARRIO_SIN_CANDIDATOS,
        )
        return

    datos["candidatos"] = [[b.codigo, b.nombre] for b in candidatos]
    mensaje, _ = componer_opciones(
        [(b.codigo, b.nombre) for b in candidatos],
        datos.get("intentos_ninguno", 0) >= _NINGUNO_PARA_OFRECER_OTRO,
    )

    await _preguntar(numero, usuario_id, PASO_BARRIO_OPCIONES, datos, mensaje)


async def _atender_opcion_barrio(
    numero: str,
    usuario_id: UUID,
    texto: str | None,
    datos: dict,
) -> None:
    """La respuesta numérica a la lista de candidatos."""
    candidatos = [tuple(c) for c in datos.get("candidatos") or []]
    intentos = datos.get("intentos_ninguno", 0)
    ofrecer_otro = intentos >= _NINGUNO_PARA_OFRECER_OTRO

    _, maximo = componer_opciones(candidatos, ofrecer_otro)
    eleccion = leer_numero(texto, maximo)

    if eleccion is None:
        # No es un número. Una quinta opción no arregla esto: si no consigue
        # escribir "3", tampoco escribirá "5". Se repite y ya.
        await responder(numero, usuario_id, textos.ONBOARDING_NUMERO_NO_ENTENDIDO)
        return

    # La última opción, cuando está ofrecida, es "mi barrio no está".
    if ofrecer_otro and eleccion == maximo:
        logger.info("Onboarding: barrio 'otro' por descarte | usuario_id=%s", usuario_id)
        await _pasar_a_huerta(numero, usuario_id, datos, _CODIGO_OTRO, None)
        return

    # "Ninguno de estos": se repregunta el barrio y se cuenta el intento.
    if eleccion == len(candidatos) + 1:
        datos["intentos_ninguno"] = intentos + 1
        datos.pop("candidatos", None)
        logger.info(
            "Onboarding: ninguno de los candidatos | usuario_id=%s | intentos=%d",
            usuario_id,
            intentos + 1,
        )
        await _preguntar(
            numero,
            usuario_id,
            PASO_BARRIO,
            datos,
            textos.ONBOARDING_PREGUNTA_BARRIO,
        )
        return

    codigo, nombre = candidatos[eleccion - 1]
    await _pasar_a_huerta(numero, usuario_id, datos, codigo, nombre)


async def _pasar_a_huerta(
    numero: str,
    usuario_id: UUID,
    datos: dict,
    codigo: str,
    nombre: str | None,
) -> None:
    """Fija el barrio en el borrador y pasa a la tercera pregunta.

    El eco dice "anoté" y no "guardé": el barrio espera en el borrador hasta
    el botón del final, así que decirle que está guardado sería falso.
    """
    datos["barrio_codigo"] = codigo
    datos["barrio_nombre"] = nombre
    datos["fallos"] = 0
    datos.pop("candidatos", None)

    if nombre:
        cabecera = textos.ONBOARDING_ECO_BARRIO.format(barrio=nombre) + "\n\n"
    else:
        # Cayó en `otro`: no hay nombre de barrio que devolverle, y repetirle
        # "anoté el barrio Otro" no le dice nada.
        cabecera = ""

    await _preguntar(
        numero,
        usuario_id,
        PASO_HUERTA,
        datos,
        cabecera + textos.ONBOARDING_PREGUNTA_HUERTA,
    )


async def _atender_huerta(
    numero: str,
    usuario_id: UUID,
    texto: str | None,
    datos: dict,
) -> None:
    """Tercera pregunta: el nombre de la huerta."""
    fallos = datos.get("fallos", 0)

    if not _es_respuesta_util(texto, maximo_palabras=6):
        fallos += 1
        datos["fallos"] = fallos
        mensaje = (
            textos.ONBOARDING_HUERTA_REINTENTO
            if fallos >= 2
            else textos.ONBOARDING_PREGUNTA_HUERTA
        )
        await _preguntar(numero, usuario_id, PASO_HUERTA, datos, mensaje)
        return

    datos["nombre_huerta"] = (texto or "").strip()
    await _proponer_cierre(numero, usuario_id, datos)


async def _proponer_cierre(numero: str, usuario_id: UUID, datos: dict) -> None:
    """Muestra los tres datos y pide la confirmación con botones.

    Es el único momento con botones del onboarding, y reutiliza los del CU3
    —mismo mecanismo del ADR-0008—, no unos nuevos.
    """
    await guardar_onboarding(usuario_id, PASO_CONFIRMACION, datos)

    resumen = componer_resumen(
        datos.get("nombre"),
        datos.get("barrio_nombre") or "Otro",
        datos.get("nombre_huerta") or "",
    )

    await responder_con_botones(
        numero,
        usuario_id,
        resumen,
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


async def _atender_confirmacion(
    numero: str,
    usuario_id: UUID,
    boton_id: str | None,
    datos: dict,
) -> None:
    """El botón del cierre. Aquí es donde se crea la fila de `huerta`."""
    if boton_id == textos.BOTON_REGISTRO_DESCARTO:
        logger.info("Onboarding descartado por la usuaria | usuario_id=%s", usuario_id)
        await responder(numero, usuario_id, textos.ONBOARDING_DESCARTADO)
        await iniciar_onboarding(numero, usuario_id)
        return

    if boton_id != textos.BOTON_REGISTRO_CONFIRMO:
        # Escribió en vez de pulsar. Se le vuelve a mostrar el resumen con
        # los botones en lugar de interpretar el texto: lo que falta es su
        # confirmación, no otro dato.
        await _proponer_cierre(numero, usuario_id, datos)
        return

    barrio_codigo = datos.get("barrio_codigo")
    if not barrio_codigo:
        # No debería ocurrir: no se llega a la confirmación sin barrio.
        logger.warning("Confirmación de onboarding sin barrio | usuario_id=%s", usuario_id)
        await iniciar_onboarding(numero, usuario_id)
        return

    try:
        huerta_id = await guardar_huerta(
            usuario_id=usuario_id,
            barrio_codigo=barrio_codigo,
            nombre_huerta=datos.get("nombre_huerta"),
            # Sin cultivos: el onboarding no los pregunta. Los va contando
            # ella después y los atiende el CU3 conversacional.
            especies=[],
        )
    except Exception:
        # El estado NO se borra: así puede reintentar el botón sin volver a
        # contestar las tres preguntas.
        logger.exception("Falló el cierre del onboarding | usuario_id=%s", usuario_id)
        await responder(numero, usuario_id, textos.ONBOARDING_FALLO)
        return

    # No se genera el fragmento comunitario: sin cultivos no hay especies
    # que vectorizar, y el fragmento son solo las especies (ADR-0011). Lo
    # genera el CU3 conversacional cuando ella cuente qué sembró.
    await borrar_onboarding(usuario_id)

    logger.info(
        "Onboarding completado | usuario_id=%s | huerta_id=%s", usuario_id, huerta_id
    )
    await responder(numero, usuario_id, textos.ONBOARDING_GUARDADO)
