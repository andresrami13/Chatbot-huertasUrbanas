"""Calibra el umbral de similitud contra el corpus oficial ya ingerido.

No forma parte del servicio. Se ejecuta a mano y **no escribe nada**:

    python -m scripts.calibrar_umbral

## Por qué hace falta

El umbral de 0.7 de la Fase 4 se respaldó en el spike del 29/07/2026, pero
aquella evidencia se obtuvo contra **documentos escritos a mano para la
prueba**, redactados casi con las palabras de la consulta. El documento
pertinente puntuó 0.797.

Con el corpus real ingerido (ADR-0009) ese mismo tipo de acierto puntúa
bastante menos, hasta el punto de que la consulta insignia del CU2 —"a mi
mata de tomate le salieron unos bichitos verdes"— no recupera nada. Este
script mide dónde cae de verdad la separación.

## Cómo están escritas las consultas

En el registro de las usuarias reales: informales, sin tildes muchas veces
—como salen de una nota de voz transcrita—, y sin vocabulario técnico. Una
consulta de prueba escrita como la escribiría un ingeniero ("manejo
integrado de plagas en solanáceas") mediría lo que el sistema hace bien, no
lo que va a recibir.

Los controles negativos son igual de importantes que los positivos: un
umbral que lo recupera todo no es un umbral. El de la fiebre está a
propósito —el bot **no** puede responder una consulta médica— y el de la
compostera es el caso difícil: habla de algo que sí está en el corpus, pero
pregunta por un trámite que no.
"""

import asyncio
import statistics

from app.core.basedatos import abrir_pool, cerrar_pool, obtener_pool
from app.services.embeddings import vectorizar_consulta

# Consultas que el CU2 SÍ debe responder. Cubren los temas del documento:
# adecuación, sustrato, riego, siembra, plagas, abonos, cosecha.
POSITIVAS = [
    "a mi mata de tomate le salieron unos bichitos verdes, que le echo",
    "cada cuanto tengo que regar la huerta",
    "como hago compost con lo que sobra de la cocina",
    "que tierra le pongo a las materas",
    "cuando se cosecha la lechuga",
    "se me estan poniendo amarillas las hojas de las plantas",
    "puedo sembrar si mi patio es de cemento",
    "que hortalizas se dan bien en Bogota",
    "como preparo un purin para las plagas",
    "cada cuanto hay que abonar la tierra",
    "mis plantas no crecen, que les hara falta",
    "como siembro las semillas de cilantro",
]

# Lo que el CU2 NO debe responder. Si el umbral las deja pasar, el bot
# contesta con orientación agronómica a quien preguntó otra cosa.
NEGATIVAS = [
    "cuando cambio el aceite del carro",
    "a que hora abre el banco",
    "mi hijo tiene fiebre, que le puedo dar",
    "cuanto cuesta el pasaje para Medellin",
    "donde saco la cita para la eps",
    # El difícil: menciona la huerta pero pide un trámite que el documento
    # no trata. Un umbral demasiado bajo lo dejará pasar.
    "donde me inscribo para que me regalen una compostera",
]

UMBRALES = [0.60, 0.62, 0.64, 0.65, 0.66, 0.68, 0.70]
TOP_K = 4


async def _mejores(pool, vector: list[float]) -> list[float]:
    """Similitudes de los `TOP_K` fragmentos más cercanos."""
    filas = await pool.fetch(
        """
        select 1 - (embedding <=> $1::vector) as similitud
          from fragmento_oficial
         order by embedding <=> $1::vector
         limit $2
        """,
        "[" + ",".join(repr(componente) for componente in vector) + "]",
        TOP_K,
    )
    return [fila["similitud"] for fila in filas]


async def main() -> None:
    await abrir_pool()
    try:
        pool = obtener_pool()
        total = await pool.fetchval("select count(*) from fragmento_oficial")
        print(f"Corpus oficial: {total} fragmentos\n")

        resultados: dict[str, list[tuple[str, list[float]]]] = {}

        for etiqueta, consultas in (("positiva", POSITIVAS), ("negativa", NEGATIVAS)):
            print(f"--- Consultas que {'SÍ' if etiqueta == 'positiva' else 'NO'} "
                  f"debe responder ---")
            medidas = []
            for consulta in consultas:
                similitudes = await _mejores(pool, await vectorizar_consulta(consulta))
                medidas.append((consulta, similitudes))
                print(
                    f"  {similitudes[0]:.4f}  "
                    f"(4.ª: {similitudes[-1]:.4f})  {consulta}"
                )
            resultados[etiqueta] = medidas
            print()

        mejores_pos = [maximos[0] for _, maximos in resultados["positiva"]]
        mejores_neg = [maximos[0] for _, maximos in resultados["negativa"]]

        print("--- Separación ---")
        print(
            f"  positivas: min={min(mejores_pos):.4f}  "
            f"mediana={statistics.median(mejores_pos):.4f}  "
            f"max={max(mejores_pos):.4f}"
        )
        print(
            f"  negativas: min={min(mejores_neg):.4f}  "
            f"mediana={statistics.median(mejores_neg):.4f}  "
            f"max={max(mejores_neg):.4f}"
        )
        hueco = min(mejores_pos) - max(mejores_neg)
        print(
            f"  hueco entre la peor positiva y la mejor negativa: {hueco:+.4f}"
        )

        print("\n--- Qué haría cada umbral ---")
        print(f"  {'umbral':>7}  {'responde':>9}  {'falsos +':>9}  {'frag./consulta':>15}")
        for umbral in UMBRALES:
            responden = sum(1 for maximos in mejores_pos if maximos >= umbral)
            falsos = sum(1 for maximos in mejores_neg if maximos >= umbral)
            recuperados = [
                sum(1 for similitud in similitudes if similitud >= umbral)
                for _, similitudes in resultados["positiva"]
            ]
            print(
                f"  {umbral:>7.2f}  {responden:>4}/{len(mejores_pos):<4}  "
                f"{falsos:>4}/{len(mejores_neg):<4}  "
                f"{statistics.mean(recuperados):>15.1f}"
            )

        print(
            "\nLectura: interesa el umbral más alto que responda todas las "
            "positivas\nsin dejar pasar ninguna negativa. Si no existe, la "
            "separación no da\ny hay que decidir cuál de los dos errores se "
            "prefiere."
        )
    finally:
        await cerrar_pool()


if __name__ == "__main__":
    asyncio.run(main())
