"""Spike de embeddings: comprueba el modelo antes de construir el RAG.

No forma parte del servicio. Se ejecuta a mano, desde la raíz del
repositorio:

    python -m scripts.spike_embeddings

Responde cuatro preguntas que no se pueden dar por supuestas:

1. ¿`output_dimensionality=768` funciona con `gemini-embedding-001`?
2. ¿El vector truncado llega sin normalizar? (la documentación dice que sí,
   pero conviene medirlo antes de apoyar el RAG en ello)
3. ¿El umbral de similitud de 0.7 de la Fase 4 separa de verdad lo
   pertinente de lo que no lo es, con texto agronómico en español?
4. ¿Ese mismo umbral sirve para la colección comunitaria, cuyos fragmentos
   no son prosa sino listas generadas (ADR-0004)?

Las dos últimas son las importantes. El umbral está fijado en los
documentos como valor inicial calibrable (CLAUDE.md §8) y este spike da la
primera evidencia para sostenerlo o cambiarlo.
"""

import asyncio
import math

from google.genai import types

from app.core.gemini import (
    DIMENSIONES_EMBEDDING,
    MODELO_EMBEDDING,
    obtener_cliente,
)
from app.services.embeddings import vectorizar_consulta, vectorizar_documentos

CONSULTA = "a mi mata de tomate le salieron unos bichitos verdes, que le echo"

DOCUMENTOS = [
    (
        "muy relacionado",
        "Manejo de plagas en tomate. El pulgon se reconoce por insectos "
        "verdes agrupados en los brotes tiernos. Se controla con jabon "
        "potasico diluido, aplicado sobre el reverso de las hojas al "
        "atardecer.",
    ),
    (
        "mismo dominio, otro tema",
        "Preparacion de compost casero. Se alternan capas de residuos "
        "verdes de cocina con hojas secas, se mantiene humedo y se voltea "
        "cada dos semanas.",
    ),
    (
        "ajeno al dominio",
        "Tramite de inscripcion en el registro de comerciantes de Bogota. "
        "Se requiere formulario diligenciado y pago de la matricula "
        "mercantil.",
    ),
]


# --- Colección comunitaria (CU4) -----------------------------------------
# Estos fragmentos imitan la forma REAL que tendrán: no los escribe una
# persona, los compone el backend a partir de las filas de `cultivo`
# (ADR-0004). Son listas, no prosa, y ahí está el riesgo: la pregunta de la
# usuaria sí es prosa.
FRAGMENTOS_COMUNITARIOS = [
    (
        "tomate, Holanda",
        "Huerta El Porvenir. Barrio Holanda. Cultivos: tomate (marzo de "
        "2026), cilantro (abril de 2026), lechuga (abril de 2026).",
    ),
    (
        "sin tomate, El Regalo",
        "Huerta La Esperanza. Barrio El Regalo. Cultivos: cebolla larga "
        "(febrero de 2026), acelga (marzo de 2026).",
    ),
    (
        "tomate, Los 3 Sectores",
        "Huerta Semillas de Vida. Barrio Los 3 Sectores. Cultivos: tomate "
        "(mayo de 2026), papa criolla (mayo de 2026).",
    ),
]

CONSULTAS_CU4 = [
    "que estan sembrando las otras huertas",
    "alguien mas por aca siembra tomate",
    "que cultivos hay en el barrio Holanda",
]


def coseno(a: list[float], b: list[float]) -> float:
    """Similitud coseno. Con vectores normalizados es el producto interno."""
    return math.fsum(x * y for x, y in zip(a, b))


async def main() -> None:
    print(f"Modelo: {MODELO_EMBEDDING}")
    print(f"Dimensiones solicitadas: {DIMENSIONES_EMBEDDING}\n")

    # --- 1 y 2. Llamada cruda, sin pasar por el servicio, para poder medir
    # la norma ANTES de normalizar. El servicio normaliza siempre, así que
    # desde fuera de él la pregunta 2 no se puede observar.
    respuesta = await obtener_cliente().aio.models.embed_content(
        model=MODELO_EMBEDDING,
        contents=[CONSULTA],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=DIMENSIONES_EMBEDDING,
        ),
    )
    crudo = list(respuesta.embeddings[0].values)
    norma = math.sqrt(math.fsum(v * v for v in crudo))

    print(f"Dimensiones devueltas: {len(crudo)}")
    print(f"Norma L2 del vector crudo: {norma:.6f}")
    if abs(norma - 1.0) < 1e-4:
        print("  -> Llega normalizado. La normalizacion del servicio es un no-op.")
    else:
        print("  -> Llega SIN normalizar, como indica la documentacion.")
        print("     app/services/embeddings.py lo corrige con L2.")

    # --- 3. Umbral. Consulta y documentos con sus task_type respectivos.
    print(f"\nUmbral de la Fase 4: 0.7\nConsulta: {CONSULTA!r}\n")

    vector_consulta = await vectorizar_consulta(CONSULTA)
    vectores_documentos = await vectorizar_documentos(
        [texto for _, texto in DOCUMENTOS]
    )

    for (etiqueta, _), vector in zip(DOCUMENTOS, vectores_documentos):
        similitud = coseno(vector_consulta, vector)
        veredicto = "RECUPERA" if similitud >= 0.7 else "descarta"
        print(f"  {similitud:.4f}  {veredicto:9s}  {etiqueta}")

    print(
        "\nLectura: el umbral sirve si 'muy relacionado' queda por encima y "
        "'ajeno al dominio' por debajo. Si el primero no llega a 0.7, el "
        "umbral esta demasiado alto para este modelo y hay que bajarlo en la "
        "Fase 7."
    )

    # --- 4. El mismo umbral, contra fragmentos comunitarios en forma de
    # lista. Es el caso del CU4 y no tiene por que comportarse igual.
    print("\n" + "=" * 70)
    print("Colección comunitaria (CU4): pregunta en prosa contra lista generada")
    print("=" * 70 + "\n")

    vectores_comunitarios = await vectorizar_documentos(
        [texto for _, texto in FRAGMENTOS_COMUNITARIOS]
    )

    etiquetas = [etiqueta for etiqueta, _ in FRAGMENTOS_COMUNITARIOS]
    print(f"{'consulta':38s}" + "".join(f"{e:>24s}" for e in etiquetas))

    maximos = []
    for consulta in CONSULTAS_CU4:
        vector_consulta_cu4 = await vectorizar_consulta(consulta)
        similitudes = [
            coseno(vector_consulta_cu4, vector) for vector in vectores_comunitarios
        ]
        maximos.append(max(similitudes))
        celdas = "".join(
            f"{s:>18.4f} {'ok' if s >= 0.7 else '--':>4s}" for s in similitudes
        )
        print(f"{consulta[:37]:38s}" + celdas)

    mejor = max(maximos)
    peor = min(maximos)
    print(
        f"\nMejor coincidencia de cada consulta: entre {peor:.4f} y {mejor:.4f}."
    )
    if mejor < 0.7:
        print(
            "  -> NINGUNA consulta del CU4 alcanza 0.7. Con el umbral unico de\n"
            "     la Fase 4 el CU4 no devolveria nada NUNCA, y sin dar error.\n"
            "     La coleccion comunitaria necesita su propio umbral."
        )
    elif peor < 0.7:
        print(
            "  -> Algunas consultas del CU4 no alcanzan 0.7. El umbral unico\n"
            "     deja fuera parte de los casos legitimos: conviene un umbral\n"
            "     propio para la coleccion comunitaria."
        )
    else:
        print(
            "  -> Todas las consultas del CU4 superan 0.7. El umbral unico\n"
            "     sirve para las dos colecciones."
        )


if __name__ == "__main__":
    asyncio.run(main())
