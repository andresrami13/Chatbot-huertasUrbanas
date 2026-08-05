"""Compara formatos del fragmento comunitario antes de fijar uno (CU4).

No escribe nada ni toca la base. Se ejecuta a mano:

    python -m scripts.calibrar_fragmento_comunitario

## Por qué hace falta

El spike del 29/07/2026 comprobó que la colección comunitaria supera el
umbral, pero dejó un aviso que nunca se resolvió: **el umbral casi no
discrimina ahí**. Todas las similitudes caían entre 0.66 y 0.80, porque
todos los fragmentos comparten la plantilla —"Huerta X. Barrio Y.
Cultivos: ..."— y ese texto fijo infla por igual la similitud de todos.
Consecuencia: quien limita el CU4 es el top-k, no el umbral.

El ADR-0009 encontró después la contrapartida en la colección oficial:
allí **no se metió ninguna plantilla** —la atribución sale de la tabla
`fuente` por la clave foránea— y la separación entre lo pertinente y lo
ajeno resultó ser de catorce centésimas.

Esa es la hipótesis que este script mide: **si la plantilla es el problema,
sacarla del texto vectorizado debería devolver la discriminación**. El
nombre de la huerta y el barrio no se pierden: viajan por la clave foránea
a `huerta`, exactamente igual que la entidad y el título en el CU2.

## Qué se mide

No la similitud absoluta, que es la trampa en la que cayó el spike, sino
dos cosas:

1. **Discriminación**: cuánto separa una consulta a las huertas que sí
   vienen a cuento de las que no. Es la diferencia entre la mejor y la peor
   similitud de la misma consulta.
2. **Acierto del orden**: si al preguntar por un cultivo concreto, las
   huertas que lo tienen quedan por encima de las que no. Es lo que de
   verdad determina si el CU4 responde bien, porque con top-k=4 y 5–7
   huertas en la Fase 8 casi todas entran igual.

Los datos de huerta son inventados, pero eso aquí **no es el defecto que
tuvo el spike del umbral**: el fragmento comunitario no lo escribe una
persona, lo compone el backend a partir de las filas de `cultivo`, así que
un fragmento generado por este script tiene la forma exacta que tendrá el
real. Lo que sí hay que cuidar es que las consultas suenen a usuaria, y no
a quien escribió el código.
"""

import asyncio
import statistics

from app.services.embeddings import vectorizar_consulta, vectorizar_documentos

# Huertas verosímiles: barrios del catálogo y especies de la guía del
# Jardín Botánico. Los cultivos se reparten a propósito para que las
# consultas por especie tengan respuesta correcta y respuesta incorrecta.
HUERTAS = [
    {
        "nombre": "El Porvenir",
        "barrio": "Holanda",
        "cultivos": [("tomate", "marzo de 2026"), ("cilantro", "abril de 2026"),
                     ("lechuga", "abril de 2026")],
    },
    {
        "nombre": "La Esperanza",
        "barrio": "El Regalo",
        "cultivos": [("cebolla larga", "febrero de 2026"),
                     ("acelga", "marzo de 2026")],
    },
    {
        "nombre": "Semillas de Vida",
        "barrio": "Los 3 Sectores",
        "cultivos": [("tomate", "mayo de 2026"), ("papa criolla", "mayo de 2026")],
    },
    {
        "nombre": "Mi Jardín",
        "barrio": "El Anhelo",
        "cultivos": [("romero", "enero de 2026"), ("ruda", "enero de 2026"),
                     ("manzanilla", "marzo de 2026")],
    },
    {
        "nombre": "Las Palmas",
        "barrio": "La Cabaña",
        "cultivos": [("fresa", "abril de 2026"), ("uchuva", "mayo de 2026")],
    },
    {
        "nombre": "El Edén",
        "barrio": "Santa Fe",
        "cultivos": [("espinaca", "marzo de 2026"), ("rábano", "abril de 2026"),
                     ("zanahoria", "abril de 2026")],
    },
]


def _lista_con_fecha(huerta: dict) -> str:
    return ", ".join(f"{especie} ({fecha})" for especie, fecha in huerta["cultivos"])


def _lista_simple(huerta: dict) -> str:
    return ", ".join(especie for especie, _ in huerta["cultivos"])


# --- Los formatos que se comparan ---------------------------------------
FORMATOS = {
    # El del spike. Es el que hay que batir.
    "A. plantilla del spike": lambda h: (
        f"Huerta {h['nombre']}. Barrio {h['barrio']}. "
        f"Cultivos: {_lista_con_fecha(h)}."
    ),
    # Misma información, redactada como prosa. Comprueba si el problema es
    # la plantilla o simplemente que el nombre y el barrio estén dentro.
    "B. prosa con nombre y barrio": lambda h: (
        f"En la huerta {h['nombre']}, del barrio {h['barrio']}, "
        f"siembran {_lista_con_fecha(h)}."
    ),
    # Sin nombre ni barrio: la atribución sale de la clave foránea, como en
    # la colección oficial (ADR-0009). Conserva las fechas.
    "C. solo cultivos con fecha": lambda h: (
        f"{_lista_con_fecha(h)}."
    ),
    # Lo mínimo: las especies y nada más.
    "D. solo especies": lambda h: _lista_simple(h),
}

# Consultas del CU4 en el registro de las usuarias. Las tres primeras
# apuntan a un cultivo concreto y por eso tienen respuesta correcta
# comprobable; las dos últimas son generales.
CONSULTAS = [
    ("alguien mas por aca siembra tomate", {"El Porvenir", "Semillas de Vida"}),
    ("quien tiene hierbas aromaticas sembradas", {"Mi Jardín"}),
    ("alguna huerta tiene fresas o uchuvas", {"Las Palmas"}),
    ("que estan sembrando las otras huertas", set()),
    ("que siembran por mi barrio", set()),
]

# Para calibrar el umbral propio de la colección comunitaria hacen falta
# más consultas legítimas y, sobre todo, consultas que NO deba responder.
POSITIVAS_CU4 = [consulta for consulta, _ in CONSULTAS] + [
    "que mas esta sembrando la gente",
    "alguien tiene lechuga o espinaca",
    "que hortalizas tienen las vecinas",
    "hay alguien con papa sembrada",
]

NEGATIVAS_CU4 = [
    "cuando cambio el aceite del carro",
    "a que hora abre el banco",
    "mi hijo tiene fiebre, que le puedo dar",
    "cuanto cuesta el pasaje para Medellin",
    "donde saco la cita para la eps",
]

UMBRALES_CU4 = [0.55, 0.58, 0.60, 0.62, 0.64, 0.66, 0.68]

# El formato que se calibra: el elegido tras la comparación de arriba.
FORMATO_ELEGIDO = "D. solo especies"


async def main() -> None:
    nombres = [huerta["nombre"] for huerta in HUERTAS]

    print(f"{len(HUERTAS)} huertas, {len(FORMATOS)} formatos, "
          f"{len(CONSULTAS)} consultas\n")

    resumen = {}

    for etiqueta,componer in FORMATOS.items():
        textos = [componer(huerta) for huerta in HUERTAS]
        vectores = await vectorizar_documentos(textos)

        print("=" * 72)
        print(etiqueta)
        print("=" * 72)
        print(f"  ejemplo: {textos[0]}")
        print(f"  longitud media: {statistics.mean(len(t) for t in textos):.0f} car.\n")

        discriminaciones = []
        aciertos = 0
        con_respuesta = 0

        for consulta, esperadas in CONSULTAS:
            vector = await vectorizar_consulta(consulta)
            similitudes = {
                nombre: sum(a * b for a, b in zip(vector, vectores[i]))
                for i, nombre in enumerate(nombres)
            }
            ordenadas = sorted(similitudes.items(), key=lambda p: -p[1])

            mejor, peor = ordenadas[0][1], ordenadas[-1][1]
            discriminaciones.append(mejor - peor)

            marca = ""
            if esperadas:
                con_respuesta += 1
                # ¿Las que sí tienen ese cultivo quedaron arriba del todo?
                arriba = {nombre for nombre, _ in ordenadas[: len(esperadas)]}
                if arriba == esperadas:
                    aciertos += 1
                    marca = "orden correcto"
                else:
                    marca = f"ORDEN MAL (arriba: {', '.join(sorted(arriba))})"

            print(f"  {consulta}")
            print(
                "    "
                + "  ".join(f"{n.split()[0][:11]}:{s:.3f}" for n, s in ordenadas)
            )
            print(f"    rango {peor:.3f}–{mejor:.3f}  (separa {mejor - peor:.3f})"
                  + (f"  {marca}" if marca else ""))

        resumen[etiqueta] = (
            statistics.mean(discriminaciones),
            aciertos,
            con_respuesta,
        )
        print()

    print("=" * 72)
    print("RESUMEN")
    print("=" * 72)
    print(f"  {'formato':<32}{'separación media':>18}{'orden correcto':>18}")
    for etiqueta, (discriminacion, aciertos, total) in resumen.items():
        print(f"  {etiqueta:<32}{discriminacion:>18.4f}{f'{aciertos}/{total}':>18}")

    print(
        "\nLectura: gana el formato que más separa y que más veces pone "
        "arriba a la\nhuerta que sí tiene el cultivo. La similitud absoluta "
        "no dice nada por sí\nsola: fue lo que engañó al spike del umbral."
    )

    # --- Umbral propio de la colección comunitaria -----------------------
    # Hace falta calibrarlo aparte porque quitar el relleno compartido baja
    # las similitudes absolutas: el umbral de 0.68 del CU2 (ADR-0010) se
    # calibró contra fragmentos de prosa larga, no contra listas de tres
    # palabras.
    print("\n" + "=" * 72)
    print(f"UMBRAL PROPIO PARA LA COLECCIÓN COMUNITARIA ({FORMATO_ELEGIDO})")
    print("=" * 72)

    vectores = await vectorizar_documentos(
        [FORMATOS[FORMATO_ELEGIDO](huerta) for huerta in HUERTAS]
    )

    async def mejor_similitud(consulta: str) -> float:
        vector = await vectorizar_consulta(consulta)
        return max(
            sum(a * b for a, b in zip(vector, vectores[i]))
            for i in range(len(HUERTAS))
        )

    print("\n  consultas que SÍ debe responder:")
    mejores_positivas = []
    for consulta in POSITIVAS_CU4:
        similitud = await mejor_similitud(consulta)
        mejores_positivas.append(similitud)
        print(f"    {similitud:.4f}  {consulta}")

    print("\n  consultas que NO debe responder:")
    mejores_negativas = []
    for consulta in NEGATIVAS_CU4:
        similitud = await mejor_similitud(consulta)
        mejores_negativas.append(similitud)
        print(f"    {similitud:.4f}  {consulta}")

    hueco = min(mejores_positivas) - max(mejores_negativas)
    print(
        f"\n  positivas: {min(mejores_positivas):.4f}–{max(mejores_positivas):.4f}"
        f"   negativas: {min(mejores_negativas):.4f}–{max(mejores_negativas):.4f}"
        f"\n  hueco: {hueco:+.4f}"
    )

    print(f"\n  {'umbral':>7}{'responde':>12}{'falsos +':>12}")
    for umbral in UMBRALES_CU4:
        responden = sum(1 for s in mejores_positivas if s >= umbral)
        falsos = sum(1 for s in mejores_negativas if s >= umbral)
        print(
            f"  {umbral:>7.2f}"
            f"{f'{responden}/{len(mejores_positivas)}':>12}"
            f"{f'{falsos}/{len(mejores_negativas)}':>12}"
        )

    print(
        "\nOjo al interpretarlo: aunque salga un umbral que separe, en el CU4\n"
        "el umbral NO hace el trabajo. Con 5–7 huertas y top-k=4, casi "
        "cualquier\nconsulta legítima recupera medio corpus. Lo que aporta "
        "rigor es el orden\ny la atribución, no el filtro. El umbral solo "
        "evita responder a quien\npreguntó por otra cosa."
    )


if __name__ == "__main__":
    asyncio.run(main())
