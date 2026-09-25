"""Repara los fragmentos oficiales que traen basura de extracción.

    python -m scripts.limpiar_corpus --simular   # dice qué cambiaría
    python -m scripts.limpiar_corpus

Corrige la incidencia INC-019: viñetas de fuente simbólica que `pypdf`
devolvió sin traducir, un marcador de objeto incrustado, un acento
combinante huérfano y un rótulo con basura pegada. Al 24/09/2026 son **36
fragmentos de 765**, repartidos en cinco de las nueve fuentes.

## Por qué esto existe y no se reingiere

Reingerir una fuente la borra y la vuelve a escribir entera, y eso cambia
el corpus más de lo pedido: son 765 vectores nuevos, un rato largo de API y
una calibración que habría que rehacer. Aquí solo se tocan los fragmentos
que de verdad cambian.

**La regla de limpieza es una sola y vive en un solo sitio**:
`ingesta_fuente.limpiar_fragmento`. La ingesta la aplica a cada fragmento
recién troceado y esto la aplica a los ya guardados, así que un documento
reingerido mañana y uno reparado hoy quedan con el mismo texto.

## Texto y vector van juntos

Un fragmento cuyo texto se corrige y conserva el vector viejo es una fila
que miente: el vector representa un texto que ya no está. Por eso cada
fragmento que cambia **se vuelve a vectorizar**, y las dos columnas se
escriben en la misma sentencia.

Eso mueve la similitud de esos fragmentos, poco pero la mueve. **Antes y
después hay que ejecutar `scripts/ejecutar_banco.py`** y comparar: es la
línea base que dice si la limpieza mejoró o empeoró lo que la usuaria
recibe.
"""

import argparse
import asyncio

from app.core.basedatos import abrir_pool, cerrar_pool, obtener_pool
from app.services.embeddings import vectorizar_documentos
from scripts.ingesta_fuente import limpiar_fragmento

# Cuántos fragmentos se vectorizan por llamada. La ingesta usa el mismo
# criterio: lotes pequeños, para que un fallo de red no tire el trabajo.
_TANDA = 20


def _diferencias(viejo: str, nuevo: str) -> list[str]:
    """Los trozos que cambian, con contexto, para poder leerlos."""
    muestras = []
    i = j = 0
    while i < len(viejo) and j < len(nuevo):
        if viejo[i] == nuevo[j]:
            i += 1
            j += 1
            continue
        muestras.append(f"{viejo[max(0, i - 35):i + 35]!r}")
        # Resincronizar por el siguiente trozo común de 12 caracteres.
        ancla = nuevo[j + 1 : j + 13]
        siguiente = viejo.find(ancla, i) if ancla else -1
        if siguiente < 0:
            break
        i, j = siguiente, j + 1
    return muestras[:3]


async def main() -> None:
    analizador = argparse.ArgumentParser(
        description="Limpia la basura de extracción del corpus oficial."
    )
    analizador.add_argument(
        "--simular",
        action="store_true",
        help="Muestra qué cambiaría, sin vectorizar ni escribir.",
    )
    argumentos = analizador.parse_args()

    await abrir_pool()
    try:
        pool = obtener_pool()
        filas = await pool.fetch(
            """
            select f.id, f.orden, f.contenido, fu.titulo
              from fragmento_oficial f
              join fuente fu on fu.id = f.fuente_id
             order by fu.titulo, f.orden
            """
        )
        print(f"Fragmentos en la base: {len(filas)}")

        cambios = []
        for fila in filas:
            limpio = limpiar_fragmento(fila["contenido"])
            if limpio != fila["contenido"]:
                cambios.append((fila["id"], fila["titulo"], fila["contenido"], limpio))

        if not cambios:
            print("\nNinguno trae basura. No hay nada que hacer.")
            return

        print(f"Fragmentos que cambian: {len(cambios)}\n")

        por_fuente: dict[str, int] = {}
        for _, titulo, viejo, nuevo in cambios:
            por_fuente[titulo] = por_fuente.get(titulo, 0) + 1
        for titulo, cuantos in sorted(por_fuente.items(), key=lambda x: -x[1]):
            print(f"  {cuantos:3d}  {titulo[:66]}")

        print("\nMuestra de lo que se quita:")
        for _, titulo, viejo, nuevo in cambios[:6]:
            for trozo in _diferencias(viejo, nuevo):
                print(f"  [{titulo[:26]}] {trozo}")

        if argumentos.simular:
            print("\n--simular: no se ha vectorizado ni escrito nada.")
            return

        print(f"\nVectorizando los {len(cambios)} fragmentos corregidos...")
        vectores: list[list[float]] = []
        for inicio in range(0, len(cambios), _TANDA):
            tanda = cambios[inicio : inicio + _TANDA]
            vectores.extend(await vectorizar_documentos([n for _, _, _, n in tanda]))
            print(f"  {min(inicio + _TANDA, len(cambios))} de {len(cambios)}")

        # Una sola transacción: o queda el corpus entero corregido o no
        # queda nada a medias, que es lo peor que le puede pasar a una
        # colección vectorial.
        async with pool.acquire() as conexion:
            async with conexion.transaction():
                for (identificador, _, _, nuevo), vector in zip(cambios, vectores):
                    await conexion.execute(
                        """
                        update fragmento_oficial
                           set contenido = $2, embedding = $3::vector
                         where id = $1
                        """,
                        identificador,
                        nuevo,
                        str(vector),
                    )

        print(f"\nCorregidos y revectorizados: {len(cambios)}")
        print("Ejecute ahora `python -m scripts.ejecutar_banco` y compare.")
    finally:
        await cerrar_pool()


if __name__ == "__main__":
    asyncio.run(main())
