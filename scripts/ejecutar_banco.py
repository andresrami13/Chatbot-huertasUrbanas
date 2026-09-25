"""Ejecuta el banco de veinte preguntas agroecológicas (BPA-CHU-001).

    python -m scripts.ejecutar_banco            # las veinte y las de control
    python -m scripts.ejecutar_banco --solo R   # solo las reales
    python -m scripts.ejecutar_banco --solo C   # solo las de control

Es la forma ejecutable del **criterio de terminación 5** de la política de
pruebas: el banco no se califica leyendo el corpus, se califica leyendo lo
que la usuaria recibiría. Por eso no llama a `consultar_orientacion`: entra
por `procesar_evento` con cargas útiles con la forma real de las de Meta,
igual que `spike_despachador`, y así pasan por el camino el enrutamiento
del agente, la retirada de etiquetas y la advertencia médica del ADR-0015.

**Escribe en la base y lo borra al terminar.** La identidad lleva
`5700000006` dentro, con forma de BSUID (ADR-0023).

**No envía nada por WhatsApp**: los módulos que envían se sustituyen por
espías.

**Cada pregunta entra en conversación limpia.** Entre una y otra se borran
los mensajes de la identidad temporal, para que la ventana de memoria no
arrastre la pregunta anterior: se mide cada pregunta por sí sola, que es
como está definido el banco.

La similitud que imprime se mide aparte, con las funciones de producción, y
es informativa: sirve para saber si la respuesta salió con respaldo oficial
o por el camino sin respaldo (`CU2_RESPALDO_MODELO`).

Se vuelve a ejecutar **cada vez que cambie el corpus**, y se comparan las
dos salidas: es la línea base contra la que se comprueba que una limpieza o
una ingesta no empeoraron las respuestas.
"""

import argparse
import asyncio
import logging

from app import textos
from app.config import settings
from app.core.basedatos import abrir_pool, cerrar_pool, obtener_pool
from app.services.dispatcher import procesar_evento
from app.services.embeddings import vectorizar_consulta
from app.services.repositorio import (
    buscar_fragmentos_oficiales,
    guardar_huerta,
    registrar_consentimiento,
)
from scripts.arnes import borrar_temporales, evento_texto, silenciar_envios

_BSUID = "CO.570000000605"

# Las veinte del banco, más cuatro de control fuera del corpus.
#
# R — reales, transcritas literalmente de la tabla `mensaje`. No se limpian
#     las muletillas ni los errores: así habla la gente por nota de voz y
#     la transcripción es literal.
# D — derivadas del corpus, con respuesta en un fragmento concreto.
# C — de control, deliberadamente FUERA del corpus: miden el camino sin
#     respaldo, que es el más expuesto porque ahí la respuesta no está
#     atada a ningún documento.
PREGUNTAS: list[tuple[str, str]] = [
    ("R-01", "A que cosas es vulnerable la acelga?"),
    ("R-02", "Como cuido mi acelga, para que no tenga bichos."),
    ("R-03", "Puedo usar un espacio público, zona verde, para hacer una paca "
             "Compostera y sembrar luego. Debo obtener alguna autorización?"),
    ("R-04", "Bueno, si tengo un repollo y empiezan a poner las mariposas... "
             "bueno, e- evidenc- evidenciado que el repollo tiene unos huevitos "
             "amarillitos por debajo de las hojas, ¿qué es?"),
    ("R-05", "Cómo hacer un atrapador de rocío casero para regar la huerta"),
    ("R-06", "Que tipo de suelo necesito para mis Granadilla"),
    ("R-07", "O, el agua del lavado de la ropa, se puede filtrar o purificar "
             "para el riego de la huerta?"),
    ("R-08", "Quiero saber cómo aumento la mariposa blanca para que no ponga "
             "huevos y se transforman en gusanos negros que se comen la mata "
             "de granadillas?"),
    ("R-09", "¿En qué momento debe uno aporcar las matas y cómo hace uno para "
             "saber cuando la remolacha ya está? Tengo... quisiera saber cómo."),
    ("R-10", "Yo misma puedo quemar la cascarilla y como hacerlo?"),
    ("D-01", "¿De qué tamaño mínimo tiene que ser la pila para hacer compost?"),
    ("D-02", "¿Qué plantas recomienda el Jardín Botánico para una huerta "
             "familiar en Bogotá?"),
    ("D-03", "¿Para qué sirve el romero?"),
    ("D-04", "¿Qué pasa si le echo a la tierra compost que todavía no está "
             "maduro?"),
    ("D-05", "¿Cómo se prepara el caldo sulfocálcico y en qué dosis se aplica?"),
    ("D-06", "¿Cuándo debo trasplantar las plántulas del semillero?"),
    ("D-07", "¿De qué capacidad necesito un tanque para recoger agua lluvia?"),
    ("D-08", "¿Qué usos tiene el canelón?"),
    ("D-09", "¿Qué le puedo echar a la mosca blanca?"),
    ("D-10", "¿Puedo tapar un desagüe para aprovechar esa agua en la huerta?"),
    ("C-01", "¿Cuánto cuesta el arriendo de un lote en Bosa para hacer huerta?"),
    ("C-02", "¿Qué variedad de quinua se da mejor en el Amazonas?"),
    ("C-03", "¿Me puede dar el teléfono del veterinario del Jardín Botánico?"),
    ("C-04", "¿Cuántos grados va a hacer mañana en Bogotá?"),
]

_wamids: list[str] = []


def _pregunta(numero: int, cuerpo: str) -> dict:
    """La pregunta con la forma de un mensaje de Meta, y su wamid anotado."""
    wamid = f"wamid.BANCO{numero:02d}"
    _wamids.append(wamid)
    return evento_texto(_BSUID, wamid, cuerpo)


async def _similitud(pregunta: str) -> tuple[float, str]:
    """Mejor similitud y título de su fuente, con las funciones de producción."""
    vector = await vectorizar_consulta(pregunta)
    hallados = await buscar_fragmentos_oficiales(vector, settings.RAG_TOP_K, 0.0)
    if not hallados:
        return 0.0, "—"
    return hallados[0].similitud, hallados[0].titulo


async def _limpiar_memoria(usuario_id) -> None:
    await obtener_pool().execute(
        "delete from mensaje where usuario_id = $1", usuario_id
    )


async def _limpiar() -> None:
    cuentas = await borrar_temporales(obtener_pool(), (_BSUID,), _wamids)
    print(f"\nLimpieza: {cuentas}")


async def main() -> None:
    analizador = argparse.ArgumentParser(
        description="Ejecuta el banco de veinte preguntas agroecológicas."
    )
    analizador.add_argument(
        "--solo",
        default="",
        help="Prefijo a ejecutar: R, D o C. Vacío, todas.",
    )
    argumentos = analizador.parse_args()

    logging.basicConfig(level=logging.WARNING)

    envios = silenciar_envios()

    seleccion = [
        (clave, texto)
        for clave, texto in PREGUNTAS
        if clave.startswith(argumentos.solo)
    ]

    await abrir_pool()
    try:
        usuaria = await registrar_consentimiento(_BSUID)
        # Sin huerta, el despachador arranca el onboarding y la pregunta
        # nunca llega al CU2 (ADR-0016): existir en `huerta` significa
        # «completó el onboarding». Se crea sin cultivos, que es lo normal,
        # y sin fragmento comunitario, para no tocar esa colección.
        await guardar_huerta(
            usuario_id=usuaria.id,
            barrio_codigo="el_regalo",
            nombre_huerta="Huerta de prueba del banco",
            especies=[],
        )
        print(f"Modelo generativo: {settings.GEMINI_GENERATIVE_MODEL}")
        print(f"Umbral del CU2:    {settings.RAG_UMBRAL_SIMILITUD}")
        print(f"Preguntas:         {len(seleccion)}\n")

        for numero, (clave, pregunta) in enumerate(seleccion, start=1):
            await _limpiar_memoria(usuaria.id)
            similitud, titulo = await _similitud(pregunta)

            envios.limpiar()
            await procesar_evento(_pregunta(numero, pregunta))
            respuesta = envios.todo() or "(nada)"

            con_respaldo = similitud >= settings.RAG_UMBRAL_SIMILITUD
            print("=" * 72)
            print(
                f"{clave}  sim={similitud:.4f}  "
                f"{'CON respaldo' if con_respaldo else 'SIN respaldo'}  "
                f"[{titulo[:44]}]"
            )
            print(f"ELLA: {pregunta}")
            print(f"BOT : {respuesta}")

            marcas = []
            if textos.ADVERTENCIA_MEDICA.splitlines()[0] in respuesta:
                marcas.append("advertencia médica")
            if "Fuente:" in respuesta:
                marcas.append("cita la fuente")
            if "[OFICIAL" in respuesta or "[COMUNITARIO" in respuesta:
                marcas.append("¡ETIQUETA COLADA!")
            print(f"      -> {', '.join(marcas) or 'sin marcas'}\n")
    finally:
        await _limpiar()
        await cerrar_pool()


if __name__ == "__main__":
    asyncio.run(main())
