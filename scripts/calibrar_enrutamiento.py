"""Mide a qué herramienta enruta el agente, sin ejecutar ninguna.

    python -m scripts.calibrar_enrutamiento
    python -m scripts.calibrar_enrutamiento --repeticiones 6
    python -m scripts.calibrar_enrutamiento --modelos gemini-3.6-flash,gemini-3.5-flash-lite
    python -m scripts.calibrar_enrutamiento --grupo comunidad

**No escribe nada, no manda WhatsApp y no llama a ninguna herramienta.**
Monta la misma llamada que hace `agente.atender` —mismo prompt de sistema,
mismas herramientas, misma temperatura, AFC desactivado— y solo lee qué
función pidió el modelo.

## Por qué existe

Porque tres veces en dos días hubo que decidir algo del enrutamiento y las
tres hizo falta medirlo:

- **08/09/2026, el CU4.** La hipótesis era que faltaban frases en el
  prompt. Medido, el enrutamiento acertaba 100 % en dos modelos y 66 % en
  el que corría en Railway, y **los 26 fallos eran «no llamó a ninguna
  herramienta»**, ni uno a la herramienta equivocada. No era el prompt: era
  el modelo (ADR-0020, sección del 08/09 en `docs/ESTADO.md`).
- **08/09/2026, los ejemplos del cierre del CU3.** Había que comprobar que
  las tres preguntas de ejemplo fueran al CU2 y no al registro.
- **09/09/2026, el CU8.** El riesgo de añadir `consultar_mi_huerta` era
  confundir «qué tengo sembrado» con «tengo cilantro sembrado». Medido con
  catorce frases sin signos de interrogación: 56/56 (ADR-0022).

## Tres cosas que una prueba suelta no da

1. **Repite.** A temperatura 0.7 el enrutamiento **no es determinista**
   (CLAUDE.md §12), así que un acierto suelto no es una medida. Por eso la
   salida dice «CU4×2, (sin herramienta)×2» y no un sí o un no.
2. **Compara modelos.** Es lo que destapó que el problema del CU4 no
   estaba en el prompt.
3. **Lleva controles.** Frases que **no** deben ir a donde se está
   calibrando, para que subir el acierto de una intención no se pague
   bajando el de otra.

## Lo que NO mide

Si la respuesta es buena. Solo a dónde enruta. Para lo primero están
`spike_despachador` y leer la respuesta con los ojos.

## Sobre el modelo

Por defecto usa el de `settings.GEMINI_GENERATIVE_MODEL`, que copia la
variable de Railway. **Medir contra otro modelo no dice nada de
producción**, y eso ya costó una medición inválida el 08/09/2026: se
comparó `3.5-flash-lite` con `3.6-flash` mientras Railway corría
`gemini-2.5-flash`.
"""

import argparse
import asyncio
import sys
from collections import Counter

from google.genai import types

from app.agent.agente import _HERRAMIENTAS, _PROMPT, _TEMPERATURA
from app.agent.plantillas import cargar_prompt
from app.config import settings
from app.core.gemini import obtener_cliente

# Lo que el bot acaba de mandar, para los mensajes de seguimiento. Sin esto
# «y las demás?» no significa nada.
_LISTADO_CU4 = (
    "🌱 Esto es lo que tienen sembrado otras huertas:\n\n"
    "• Tierra verde (HOLANDA III SECTOR): fresa, tomate, uchuvas\n"
    "• El placer (LAURELES LA ESTACION): acelga, auyama, Cebolla\n"
    "• huertica (EL PORVENIR): cebolla, lechuga, tomate\n\n"
    "Hay una huerta más. Si quiere le cuento de ellas, dígame."
)

_TRAS_REGISTRAR = [
    ("usuaria", "tengo tomate y lechuga sembrado"),
    ("modelo", "Esto es lo que entendí: - tomate - lechuga  ¿Lo guardo así?"),
    ("usuaria", "Sí, guardar"),
    ("modelo", "✅ Listo, ya quedó guardado."),
]

_TRAS_LISTADO = [
    ("usuaria", "que siembran las otras huertas"),
    ("modelo", _LISTADO_CU4),
]

# Los nombres esperados son los de las funciones, salvo `consultar_comunidad`,
# que se desglosa en CU4 y CU7 según venga o no el parámetro `especie`
# (ADR-0021).
_GRUPOS: dict[str, list[tuple[str, list, str]]] = {
    "comunidad": [
        ("que estan sembrando las otras huertas", [], "CU4"),
        ("que siembran las demas", [], "CU4"),
        ("que tienen sembrado las otras señoras", [], "CU4"),
        ("quiero saber que cultivan los demas", [], "CU4"),
        ("cuenteme de las otras huertas", [], "CU4"),
        ("que hay en las huertas del barrio", [], "CU4"),
        ("quienes mas tienen huerta por aqui", [], "CU4"),
        ("que estan cultivando mis vecinas", [], "CU4"),
        ("hay mas huertas por aca?", [], "CU4"),
        ("y las demas?", _TRAS_LISTADO, "CU4"),
        ("cuenteme mas", _TRAS_LISTADO, "CU4"),
        ("si, muestreme las otras", _TRAS_LISTADO, "CU4"),
        ("alguien mas siembra tomate?", [], "CU7"),
        ("quien tiene fresas", [], "CU7"),
        ("hay alguien que tenga cilantro sembrado", [], "CU7"),
    ],
    # El par que introdujo el CU8, y el riesgo de añadirlo (ADR-0022).
    # NINGUNA lleva signo de interrogación: lo que separa las dos cosas es
    # si nombra una planta o no, no la puntuación.
    "mi_huerta": [
        ("que tengo sembrado", _TRAS_REGISTRAR, "consultar_mi_huerta"),
        ("que tengo en mi huerta", _TRAS_REGISTRAR, "consultar_mi_huerta"),
        ("cuales son mis cultivos", _TRAS_REGISTRAR, "consultar_mi_huerta"),
        ("recuerdeme que sembre", _TRAS_REGISTRAR, "consultar_mi_huerta"),
        ("digame que tengo anotado", _TRAS_REGISTRAR, "consultar_mi_huerta"),
        ("como se llama mi huerta", _TRAS_REGISTRAR, "consultar_mi_huerta"),
        ("en que barrio quede registrada", _TRAS_REGISTRAR, "consultar_mi_huerta"),
        ("no me acuerdo que sembre", _TRAS_REGISTRAR, "consultar_mi_huerta"),
        ("sembre cilantro", _TRAS_REGISTRAR, "registrar_huerta"),
        ("tengo cilantro sembrado", _TRAS_REGISTRAR, "registrar_huerta"),
        ("puse unas maticas de sabila", _TRAS_REGISTRAR, "registrar_huerta"),
        ("ayer sembre papa criolla", _TRAS_REGISTRAR, "registrar_huerta"),
    ],
    # Los ejemplos que el cierre del CU3 le enseña. Si uno de estos no fuera
    # al CU2, la invitación estaría enseñándole a fallar.
    "ejemplos": [
        ("puedo sembrar en materas o tarros", _TRAS_REGISTRAR, "consultar_orientacion"),
        ("cada cuánto hay que regar la huerta", _TRAS_REGISTRAR, "consultar_orientacion"),
        ("cómo hago compost en la casa", _TRAS_REGISTRAR, "consultar_orientacion"),
    ],
    # Controles. No calibran nada: comprueban que lo que ya funcionaba
    # sigue funcionando.
    "controles": [
        ("como siembro tomate", [], "consultar_orientacion"),
        ("mi tomate tiene bichos, que le echo", [], "consultar_orientacion"),
        ("sembre lechuga la semana pasada", [], "registrar_huerta"),
        ("hola", [], "mostrar_ayuda"),
        ("que puede hacer usted", [], "mostrar_ayuda"),
    ],
}

# Reintentos ante el 503 UNAVAILABLE, que la familia flash completa da por
# sobrecarga (medido el 19/08 y visto otra vez el 09/09/2026). Sin esto un
# corte de la API se contaría como fallo de enrutamiento, que es una
# conclusión falsa.
_ESPERAS = (2.0, 4.0, 8.0)


def _contenidos(historial: list, mensaje: str) -> list[types.Content]:
    partes = [
        types.Content(
            role="user" if rol == "usuaria" else "model",
            parts=[types.Part(text=texto)],
        )
        for rol, texto in historial
    ]
    partes.append(types.Content(role="user", parts=[types.Part(text=mensaje)]))
    return partes


async def _enrutar(modelo: str, historial: list, mensaje: str) -> str:
    """Qué herramienta pediría el modelo. Nunca lanza."""
    for intento in range(len(_ESPERAS) + 1):
        try:
            respuesta = await obtener_cliente().aio.models.generate_content(
                model=modelo,
                contents=_contenidos(historial, mensaje),
                config=types.GenerateContentConfig(
                    temperature=_TEMPERATURA,
                    system_instruction=cargar_prompt(_PROMPT),
                    tools=[_HERRAMIENTAS],
                    automatic_function_calling=(
                        types.AutomaticFunctionCallingConfig(disable=True)
                    ),
                ),
            )
            break
        except Exception as error:  # noqa: BLE001 — aquí se mide, no se atiende
            if "503" not in str(error) or intento == len(_ESPERAS):
                return f"ERROR:{type(error).__name__}"
            await asyncio.sleep(_ESPERAS[intento])

    llamadas = respuesta.function_calls or []
    if not llamadas:
        # No es un detalle: cuando pasa, `agente.py` manda el texto que
        # escribió el modelo y se salta el caso de uso entero.
        return "(sin herramienta)"

    nombres = []
    for llamada in llamadas:
        if llamada.name == "consultar_comunidad":
            especie = str((llamada.args or {}).get("especie") or "").strip()
            nombres.append("CU7" if especie else "CU4")
        else:
            nombres.append(llamada.name)
    return "+".join(nombres)


async def _medir(modelo: str, casos: list, repeticiones: int) -> tuple[int, int]:
    print("\n" + "=" * 78)
    print(f"MODELO: {modelo}   ({repeticiones} repeticiones por mensaje)")
    print("=" * 78)

    aciertos = 0
    for mensaje, historial, esperado in casos:
        # En serie y no en paralelo: cuatro llamadas simultáneas disparan el
        # 503 de la familia flash con mucha más frecuencia.
        resultados = [
            await _enrutar(modelo, historial, mensaje) for _ in range(repeticiones)
        ]
        vistos = Counter(resultados)
        bien = vistos.get(esperado, 0)
        aciertos += bien

        marca = "OK  " if bien == repeticiones else ("~   " if bien else "FALLA")
        seguimiento = " [con historial]" if historial else ""
        detalle = ", ".join(f"{k}×{v}" for k, v in vistos.most_common())
        print(f"  [{marca}] {mensaje!r}{seguimiento}")
        print(f"          esperado {esperado} -> {detalle}")

    total = len(casos) * repeticiones
    print(f"\n  {aciertos}/{total} enrutamientos correctos "
          f"({100 * aciertos / total:.0f} %)")
    return aciertos, total


async def principal(modelos: list[str], grupos: list[str], repeticiones: int) -> None:
    casos = [caso for grupo in grupos for caso in _GRUPOS[grupo]]
    print(f"Grupos: {', '.join(grupos)} | {len(casos)} mensajes")

    resumen = []
    for modelo in modelos:
        resumen.append((modelo, *await _medir(modelo, casos, repeticiones)))

    if len(resumen) > 1:
        print("\n" + "=" * 78)
        print("RESUMEN")
        print("=" * 78)
        for modelo, aciertos, total in resumen:
            print(f"  {modelo:28} {aciertos:3d}/{total:3d}  "
                  f"({100 * aciertos / total:3.0f} %)")


def main() -> None:
    analizador = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analizador.add_argument(
        "--modelos",
        default=settings.GEMINI_GENERATIVE_MODEL,
        help="Separados por coma. Por defecto, el desplegado.",
    )
    analizador.add_argument(
        "--grupo",
        action="append",
        choices=sorted(_GRUPOS),
        help="Repetible. Por defecto, todos.",
    )
    analizador.add_argument("--repeticiones", type=int, default=4)
    argumentos = analizador.parse_args()

    if argumentos.repeticiones < 1:
        sys.exit("Las repeticiones tienen que ser al menos 1.")

    asyncio.run(
        principal(
            [m.strip() for m in argumentos.modelos.split(",") if m.strip()],
            argumentos.grupo or sorted(_GRUPOS),
            argumentos.repeticiones,
        )
    )


if __name__ == "__main__":
    main()
