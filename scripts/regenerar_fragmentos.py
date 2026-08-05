"""Regenera el fragmento comunitario de todas las huertas.

    python -m scripts.regenerar_fragmentos --simular   # dice qué haría
    python -m scripts.regenerar_fragmentos

Cumple dos funciones distintas, y conviene no confundirlas:

1. **Puesta al día, una sola vez.** La generación del fragmento se
   implementó en la Fase 6, y se dispara al confirmar un registro. Las
   huertas guardadas **antes** de eso no la dispararon nunca, así que
   estarían en la base con sus cultivos correctos y a la vez invisibles
   para el CU4: la búsqueda por similitud no tendría contra qué
   compararlas. Este script las incorpora.

2. **Reparación, cuantas veces haga falta.** Al confirmar un registro, un
   fallo de red o del modelo de embeddings deja la huerta guardada y sin
   fragmento; es deliberado, porque el fragmento es un derivado y no debe
   tumbar el CU3 (ADR-0004). El fallo queda en la bitácora y se repara
   ejecutando esto.

También es lo que hay que ejecutar si algún día cambia el formato del
texto del fragmento: los fragmentos viejos y los nuevos no serían
comparables entre sí, igual que no lo serían embeddings de modelos
distintos.

Es idempotente: regenerar una huerta que ya está al día produce el mismo
texto y el mismo vector.
"""

import argparse
import asyncio

from app.core.basedatos import abrir_pool, cerrar_pool
from app.services.fragmento_comunitario import componer_texto, regenerar_fragmento
from app.services.repositorio import (
    listar_cultivos_de_huerta,
    listar_huertas_para_regenerar,
)


async def main() -> None:
    analizador = argparse.ArgumentParser(
        description="Regenera los fragmentos comunitarios (CU4)."
    )
    analizador.add_argument(
        "--simular",
        action="store_true",
        help="Muestra qué se generaría, sin vectorizar ni escribir.",
    )
    argumentos = analizador.parse_args()

    await abrir_pool()
    try:
        huertas = await listar_huertas_para_regenerar()
        print(f"Huertas en la base: {len(huertas)}")

        if not huertas:
            print(
                "\nNo hay ninguna huerta registrada, así que no hay nada que\n"
                "regenerar. No es un error: significa que ninguna quedó fuera\n"
                "del CU4."
            )
            return

        generados = vacias = fallidos = 0

        for huerta_id in huertas:
            especies = await listar_cultivos_de_huerta(huerta_id)

            if not especies:
                vacias += 1
                print(f"  {huerta_id}  sin cultivos, se omite")
                continue

            if argumentos.simular:
                print(f"  {huerta_id}  -> {componer_texto(especies)!r}")
                generados += 1
                continue

            if await regenerar_fragmento(huerta_id):
                generados += 1
                print(f"  {huerta_id}  regenerado ({len(especies)} especies)")
            else:
                fallidos += 1
                print(f"  {huerta_id}  FALLÓ, ver la bitácora")

        verbo = "se generarían" if argumentos.simular else "generados"
        print(f"\n{verbo}: {generados} | sin cultivos: {vacias} | fallidos: {fallidos}")

        if argumentos.simular:
            print("--simular: no se ha vectorizado ni escrito nada.")
    finally:
        await cerrar_pool()


if __name__ == "__main__":
    asyncio.run(main())
