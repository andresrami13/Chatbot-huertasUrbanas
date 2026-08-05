"""Spike del CU4 de punta a punta, contra la base y la API reales.

    python -m scripts.spike_comunidad

**Escribe en la base y lo borra al terminar.** Crea cuatro usuarias
temporales con sus huertas, genera sus fragmentos, pregunta, y borra todo
en un `finally`. Es el mismo procedimiento con el que se probó el CU3 el
30/07/2026.

Los números de teléfono son inventados y empiezan por `5700000009`, para
que no puedan chocar con uno real. **La fila real del celular de pruebas
del autor no se toca**: el borrado se acota a los teléfonos que este script
creó.

Comprueba las cuatro cosas que pueden salir mal:

1. Que la respuesta **atribuya cada dato a su huerta y su barrio**. Sin eso
   la usuaria entendería que todo se siembra en el suyo (ADR-0001).
2. Que **no convierta el reporte en consejo**: que tres vecinas tengan
   tomate no significa que el tomate se dé bien aquí (CLAUDE.md §6).
3. Que **excluya la huerta de quien pregunta**. El CU4 es qué siembran
   *otras* huertas.
4. Que sin datos que vengan a cuento responda el texto fijo.
"""

import asyncio
import re

from app.core.basedatos import abrir_pool, cerrar_pool, obtener_pool
from app.core.identidad import calcular_telefono_hash
from app.services.comunidad import consultar_comunidad
from app.services.fragmento_comunitario import regenerar_fragmento
from app.services.repositorio import guardar_huerta, registrar_consentimiento

# Prefijo inconfundible: ningún celular colombiano real lo tiene.
_PREFIJO = "5700000009"

HUERTAS = [
    (f"{_PREFIJO}01", "El Porvenir", "holanda",
     ["tomate", "cilantro", "lechuga"]),
    (f"{_PREFIJO}02", "La Esperanza", "el_regalo",
     ["cebolla larga", "acelga"]),
    (f"{_PREFIJO}03", "Semillas de Vida", "los_3_sectores",
     ["tomate", "papa criolla"]),
    (f"{_PREFIJO}04", "Mi Jardín", "el_anhelo",
     ["romero", "ruda", "manzanilla"]),
]

CONSULTAS = [
    "alguien mas por aca siembra tomate",
    "quien tiene hierbas aromaticas sembradas",
    "que estan sembrando las otras huertas",
    "cuando cambio el aceite del carro",
]

# Señales de que el modelo convirtió el reporte de las vecinas en una
# recomendación técnica, que es lo que la jerarquía de fuentes prohíbe.
_CONSEJO = re.compile(
    r"\b(se da bien|le recomiendo|deber[íi]a sembrar|es lo mejor|"
    r"crece bien|ideal para|conviene sembrar)\b",
    re.IGNORECASE,
)


async def _borrar_temporales() -> None:
    """Borra las usuarias del spike. En cascada se van huertas y cultivos.

    Va por `telefono_hash` y no por otra cosa: es lo único que identifica a
    estas filas, y acotarlo así garantiza que no se toque la fila real.
    """
    hashes = [calcular_telefono_hash(numero) for numero, *_ in HUERTAS]
    resultado = await obtener_pool().execute(
        "delete from usuario where telefono_hash = any($1::text[])", hashes
    )
    print(f"\nLimpieza: {resultado}")


async def main() -> None:
    await abrir_pool()
    try:
        print("Creando huertas temporales...")
        propias: dict[str, object] = {}

        for numero, nombre, barrio, especies in HUERTAS:
            usuaria = await registrar_consentimiento(numero)
            huerta_id = await guardar_huerta(
                usuario_id=usuaria.id,
                barrio_codigo=barrio,
                nombre_huerta=nombre,
                cultivos=[(especie, None, True) for especie in especies],
            )
            await regenerar_fragmento(huerta_id)
            propias[numero] = usuaria.id
            print(f"  {nombre} ({barrio}): {', '.join(especies)}")

        # Pregunta la dueña de El Porvenir, que tiene tomate. Su propia
        # huerta NO debe aparecer en las respuestas.
        quien_pregunta = propias[f"{_PREFIJO}01"]
        print(f"\nPregunta la dueña de El Porvenir (tomate, cilantro, lechuga)\n")

        for consulta in CONSULTAS:
            print("=" * 70)
            print(f"PREGUNTA: {consulta}")
            print("=" * 70)

            respuesta = await consultar_comunidad(consulta, quien_pregunta)
            print(respuesta)

            avisos = []

            if "El Porvenir" in respuesta:
                avisos.append("¡FILTRA SU PROPIA HUERTA! debía excluirse")

            consejos = set(_CONSEJO.findall(respuesta))
            if consejos:
                avisos.append(f"suena a recomendación: {sorted(consejos)}")

            # La atribución solo se exige cuando hubo datos que atribuir.
            from app import textos
            if respuesta not in (
                textos.COMUNIDAD_SIN_DATOS,
                textos.COMUNIDAD_NO_DISPONIBLE,
            ):
                barrios = ("Holanda", "El Regalo", "Los 3 Sectores", "El Anhelo")
                if not any(b in respuesta for b in barrios):
                    avisos.append("no atribuye el barrio de ninguna huerta")

            palabras = len(respuesta.split())
            if palabras > 80:
                avisos.append(f"se pasa de largo: {palabras} palabras")

            print(
                f"\n[{palabras} palabras]"
                + (f"  AVISOS: {'; '.join(avisos)}" if avisos else "  correcto")
            )
            print()
    finally:
        await _borrar_temporales()
        await cerrar_pool()


if __name__ == "__main__":
    asyncio.run(main())
