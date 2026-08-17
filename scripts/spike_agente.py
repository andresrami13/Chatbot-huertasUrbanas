"""Spike del agente orquestador, contra la base y la API reales (ADR-0013).

    python -m scripts.spike_agente

**Escribe en la base y lo borra al terminar.** Crea dos usuarias
temporales —una que conversa y otra con huerta, para que el CU4 tenga qué
encontrar— y las borra en un `finally`. Los números empiezan por
`5700000007`, para que no choquen con uno real ni con los de los otros
spikes.

**No envía nada por WhatsApp.** Los dos envíos de `memoria` se sustituyen
por espías que capturan el texto, como se hizo para probar la
transcripción. Así se puede leer lo que la usuaria habría recibido sin
gastar mensajes del número de prueba, que solo admite cinco destinatarios
verificados.

**El enrutamiento no es determinista.** El agente corre a temperatura 0.7
(CLAUDE.md §8), así que el mismo mensaje puede tomar caminos distintos en
dos ejecuciones. Es la diferencia con los spikes anteriores y hay que
tenerla presente al leer un fallo: una vez no es una medida.

Comprueba lo que puede salir mal:

1. Que **enrute** cada mensaje a la herramienta que le toca.
2. Que **no aconseje por su cuenta**: una duda de cultivo tiene que
   terminar citando la fuente oficial, no en la respuesta del agente.
3. Que **no dé por guardado** lo que solo se propuso (CLAUDE.md §4.7).
4. Que un mensaje de **doble intención** produzca las dos cosas, y que los
   botones queden en el último mensaje.
5. Que **use la memoria**: que "en el regalo" se entienda como respuesta a
   la pregunta anterior.
6. Que pase la pregunta **con las palabras de la usuaria**, que es como se
   calibró el umbral del CU2 (ADR-0010).
"""

import asyncio
import logging
import re

from app import textos
from app.agent import agente
from app.core.basedatos import abrir_pool, cerrar_pool, obtener_pool
from app.core.identidad import calcular_telefono_hash
from app.services import memoria
from app.services.fragmento_comunitario import regenerar_fragmento
from app.services.repositorio import guardar_huerta, registrar_consentimiento

_PREFIJO = "5700000007"
_NUMERO_ANA = f"{_PREFIJO}01"
_NUMERO_VECINA = f"{_PREFIJO}02"

# Lo que el espía va capturando en el turno en curso.
_enviados: list[tuple[str, str]] = []

_resultados: list[tuple[bool, str]] = []

# Señales de que el agente se puso a aconsejar de su propia cosecha en vez
# de llamar a la herramienta respaldada por la guía oficial.
_CONSEJO_PROPIO = re.compile(
    r"\b(aplique|rocíe|rocie|mezcle|use jab[óo]n|agua con|riegue cada|"
    r"le recomiendo que|puede fumigar)\b",
    re.IGNORECASE,
)

# Señales de que dio por hecho un registro que solo se propuso.
_YA_GUARDADO = re.compile(
    r"\b(ya qued[óo] guardad|ya lo guard|ya lo anot[ée]|qued[óo] registrad|"
    r"ya registr)\w*", re.IGNORECASE,
)


async def _espia_texto(destino: str, texto: str) -> str | None:
    _enviados.append(("texto", texto))
    return None


async def _espia_botones(destino: str, cuerpo: str, botones) -> str | None:
    rotulos = " | ".join(rotulo for _, rotulo in botones)
    _enviados.append(("botones", f"{cuerpo}\n   [{rotulos}]"))
    return None


def _comprobar(condicion: bool, titulo: str, detalle: str = "") -> None:
    marca = "OK  " if condicion else "FALLA"
    print(f"    [{marca}] {titulo}" + (f" — {detalle}" if detalle else ""))
    _resultados.append((condicion, titulo))


async def _turno(numero: str, usuario_id, mensaje: str) -> list[tuple[str, str]]:
    """Un mensaje entrante completo, como lo hará el despachador en 4c.

    Registra lo entrante en la memoria **antes** de atenderlo, que es lo
    que deja la ventana terminando en la pregunta en curso (ADR-0012).
    """
    _enviados.clear()

    await memoria.recordar_usuaria(usuario_id, mensaje, "text", None)
    await agente.atender(numero, usuario_id, mensaje)

    print(f"\n  USUARIA: {mensaje}")
    for clase, texto in _enviados:
        marca = "BOT (botones)" if clase == "botones" else "BOT"
        sangrado = texto.replace("\n", "\n     ")
        print(f"  {marca}: {sangrado}")

    return list(_enviados)


def _todo(enviados) -> str:
    return "\n".join(texto for _, texto in enviados)


async def _borrar_temporales() -> None:
    hashes = [
        calcular_telefono_hash(numero)
        for numero in (_NUMERO_ANA, _NUMERO_VECINA)
    ]
    resultado = await obtener_pool().execute(
        "delete from usuario where telefono_hash = any($1::text[])", hashes
    )
    print(f"\nLimpieza: {resultado}")


async def main() -> None:
    # Con bitácora, para poder leer a qué función enrutó, si respetó las
    # palabras de la usuaria y si el CU2 tuvo que reintentar con el mensaje
    # completo. Nada de esto lleva contenido del mensaje (CLAUDE.md §11).
    logging.basicConfig(level=logging.INFO, format="      · %(name)s | %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google_genai").setLevel(logging.WARNING)

    await abrir_pool()

    # Espías: sustituyen los dos envíos que usa `memoria`. Se hace aquí y
    # no dentro del agente para no meter una bandera de prueba en el código
    # que va a producción.
    memoria.enviar_texto = _espia_texto
    memoria.enviar_botones = _espia_botones

    try:
        ana = await registrar_consentimiento(_NUMERO_ANA)
        vecina = await registrar_consentimiento(_NUMERO_VECINA)

        # Una huerta ajena, para que el CU4 tenga algo que contar.
        huerta_id = await guardar_huerta(
            usuario_id=vecina.id,
            barrio_codigo="holanda",
            nombre_huerta="La Esperanza",
            cultivos=[("fresa", None, True), ("acelga", None, True)],
        )
        await regenerar_fragmento(huerta_id)

        # Ana ya completó el onboarding: tiene huerta con barrio y nombre,
        # pero todavía sin cultivos. Desde el ADR-0016 esa fila es lo que
        # significa "completó el onboarding", y sin ella el CU3
        # conversacional no tiene dónde añadir lo que cuente.
        await guardar_huerta(
            usuario_id=ana.id,
            barrio_codigo="holanda",
            nombre_huerta="La Milagrosa",
            cultivos=[],
        )
        print("Preparado: una huerta vecina con fresa y acelga en Holanda.")
        print("Preparado: Ana con onboarding hecho y su huerta sin cultivos.")

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("1. Duda de cultivo -> consultar_orientacion")
        print("=" * 70)
        enviados = await _turno(
            _NUMERO_ANA, ana.id,
            "a mi mata de tomate le salieron unos bichitos verdes, que le echo",
        )
        texto = _todo(enviados)

        _comprobar(len(enviados) == 1, "responde con un solo mensaje")
        _comprobar(
            "Fuente:" in texto or textos.ORIENTACION_SIN_RESPALDO in texto,
            "la respuesta viene del CU2, no del agente",
            "cita la fuente oficial o reconoce que no la tiene",
        )
        _comprobar(
            not (_CONSEJO_PROPIO.search(texto) and "Fuente:" not in texto),
            "no aconseja de su propia cosecha",
        )

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("2. Qué siembran otras -> consultar_comunidad")
        print("=" * 70)
        enviados = await _turno(
            _NUMERO_ANA, ana.id, "que estan sembrando las otras huertas por aca"
        )
        texto = _todo(enviados)

        _comprobar(
            "Holanda" in texto or textos.COMUNIDAD_SIN_DATOS in texto,
            "atribuye la huerta vecina o reconoce que no hay datos",
        )
        _comprobar("Fuente:" not in texto, "no cita fuente oficial: es dato comunitario")
        _comprobar(
            "COMUNITARIO" not in texto,
            "no se le cuela la etiqueta de procedencia",
            "el 15/08 el modelo escribió 'la huerta COMUNITARIO – La Esperanza'",
        )

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("3. Cuenta de su huerta -> registrar_huerta (propone, no guarda)")
        print("=" * 70)
        enviados = await _turno(
            _NUMERO_ANA, ana.id, "sembre cilantro y cebolla larga en marzo"
        )
        texto = _todo(enviados)

        # Con el onboarding hecho, el barrio ya está: se ofrecen los botones
        # de una vez. Antes del ADR-0016 aquí se preguntaba el barrio en
        # lenguaje natural, porque la extracción podía no traerlo
        # (ADR-0008, decisión 5, ya retirada).
        _comprobar(
            any(clase == "botones" for clase, _ in enviados),
            "ofrece los botones de confirmación",
            "el barrio lo fijó el onboarding, así que no falta nada",
        )
        _comprobar(
            "La Milagrosa" in texto and "HOLANDA" in texto,
            "el resumen muestra la huerta y el barrio que ella confirmó",
            "salen de `huerta`, no de la extracción, y en mayúscula",
        )
        _comprobar(not _YA_GUARDADO.search(texto), "NO dice que ya quedó guardado")

        cultivos_de_ana = await obtener_pool().fetchval(
            """
            select count(*)
              from cultivo c
              join huerta h on h.id = c.huerta_id
             where h.usuario_id = $1
            """,
            ana.id,
        )
        _comprobar(
            cultivos_de_ana == 0,
            "no guardó ningún cultivo en la base",
            "es la comprobación que sostiene el §4.7",
        )

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("4. La memoria: 'también lechuga' solo se entiende con lo anterior")
        print("=" * 70)
        # Antes del ADR-0016 este caso era "en holanda", respondiendo a la
        # pregunta del barrio que hacía el CU3. Ese camino ya no existe: el
        # barrio lo fija el onboarding y la extracción ni lo mira. La
        # invariante que se comprueba es la misma —memoria y fusión del
        # borrador— con un mensaje que hoy tiene sentido.
        enviados = await _turno(_NUMERO_ANA, ana.id, "ah, y también sembré lechuga")
        texto = _todo(enviados)

        _comprobar(
            "lechuga" in texto.lower(),
            "recoge lo que acaba de decir",
        )
        _comprobar(
            "cilantro" in texto.lower(),
            "conserva el cilantro del mensaje anterior",
            "es la fusión del borrador del ADR-0008",
        )
        _comprobar(
            any(clase == "botones" for clase, _ in enviados),
            "vuelve a ofrecer los botones con la lista completa",
        )
        _comprobar(
            "cebolla larga" in texto.lower(),
            "conserva la especie literal en el resumen",
            "la extracción trabajó sobre el mensaje, no sobre una paráfrasis",
        )

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("5. Saludo -> mostrar_ayuda (texto fijo, sin pasar por el modelo)")
        print("=" * 70)
        enviados = await _turno(_NUMERO_ANA, ana.id, "hola")
        texto = _todo(enviados)

        _comprobar(
            textos.BIENVENIDA in texto,
            "manda la bienvenida palabra por palabra",
            "el modelo decide cuándo, no qué dice",
        )

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("6. Doble intención -> consulta y propuesta, en ese orden")
        print("=" * 70)
        enviados = await _turno(
            _NUMERO_ANA, ana.id,
            "a mi tomate le salieron bichos y de paso sembre lechuga el mes pasado",
        )
        texto = _todo(enviados)

        _comprobar(
            len(enviados) == 2,
            "produce dos mensajes, no uno",
            f"{len(enviados)} mensaje(s)",
        )
        if len(enviados) == 2:
            _comprobar(
                enviados[-1][0] == "botones",
                "los botones quedan en el ÚLTIMO mensaje",
                "si no, ella los pulsaría con otra respuesta encima",
            )
        _comprobar(not _YA_GUARDADO.search(texto), "sigue sin dar nada por guardado")

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("7. Cortesía -> ninguna función, texto propio y corto")
        print("=" * 70)
        enviados = await _turno(_NUMERO_ANA, ana.id, "muchas gracias, muy amable")
        texto = _todo(enviados)

        _comprobar(len(enviados) == 1, "un solo mensaje")
        _comprobar(
            len(texto.split()) <= 40,
            "no se enrolla",
            f"{len(texto.split())} palabras",
        )

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("8. Fuera de dominio -> se reconoce, no se inventa")
        print("=" * 70)
        enviados = await _turno(
            _NUMERO_ANA, ana.id, "cada cuanto le cambio el aceite al carro"
        )
        texto = _todo(enviados)

        _comprobar(
            "Fuente:" not in texto,
            "no cita la guía de huertas para hablar de carros",
        )

        # -----------------------------------------------------------------
        fallos = [titulo for ok, titulo in _resultados if not ok]
        print("\n" + "=" * 70)
        if fallos:
            print(f"{len(fallos)} COMPROBACIONES FALLIDAS de {len(_resultados)}:")
            for titulo in fallos:
                print(f"  - {titulo}")
            print("\nRecuerde: a temperatura 0.7 el enrutamiento varía.")
            print("Repita antes de dar por bueno un fallo aislado.")
        else:
            print(f"Las {len(_resultados)} comprobaciones pasaron.")
        print("=" * 70)
    finally:
        await _borrar_temporales()
        await cerrar_pool()


if __name__ == "__main__":
    asyncio.run(main())
