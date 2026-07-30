"""Spike de extracción de entidades: prueba el CU3 sin persistir nada.

No forma parte del servicio. Se ejecuta desde la raíz del repositorio:

    python -m scripts.spike_extraccion

Necesita el `.env` completo: lee el catálogo de barrios de Supabase y llama
a Gemini. **No escribe nada en la base.**

Los mensajes de prueba están elegidos para tensar los puntos donde la
extracción se puede equivocar de forma que la usuaria lo note:

- un mensaje completo y bien dicho, que es el caso fácil;
- una fecha vaga, que debe marcarse como imprecisa y no inventarse;
- una pregunta, que NO es un registro y no debe producir cultivos;
- un barrio de fuera de la UPZ, que debe caer en `otro`;
- nombres locales de plantas, que no deben "corregirse";
- una transcripción con titubeos, como las que llegan de verdad por voz.
"""

import asyncio
from datetime import date

from app.core.basedatos import abrir_pool, cerrar_pool
from app.services.extraccion import extraer_huerta
from app.services.repositorio import listar_barrios

CASOS = [
    (
        "mensaje completo",
        "buenas, mi huerta se llama El Porvenir, queda en Holanda y sembré "
        "tomate y cilantro en marzo",
        "nombre, barrio holanda, 2 cultivos con fecha precisa",
    ),
    (
        "fecha vaga",
        "tengo unas maticas de cebolla larga desde hace rato",
        "1 cultivo 'cebolla larga', fecha_imprecisa=True",
    ),
    (
        "pregunta, no registro",
        "y al tomate qué le echo para los bichos",
        "todo vacío: es una consulta",
    ),
    (
        "barrio de fuera",
        "yo vivo en Kennedy y tengo lechuga sembrada",
        "barrio 'otro', 1 cultivo",
    ),
    (
        "nombres locales",
        "sembré cebolla larga y papa criolla el mes pasado",
        "especies literales, sin recortar a 'cebolla' ni 'papa'",
    ),
    (
        "voz con titubeos",
        "eh... buenas... pues yo tengo, tengo tomate, sembré en abril me "
        "parece, alla en el barrio los tres sectores",
        "barrio los_3_sectores, 1 cultivo en abril",
    ),
    (
        "sin nada de huerta",
        "muchas gracias, muy amable",
        "todo vacío",
    ),
]


async def main() -> None:
    await abrir_pool()
    try:
        barrios = await listar_barrios()
        print(f"Catálogo leído de la base: {len(barrios)} barrios activos")
        print("  " + ", ".join(b.codigo for b in barrios))
        print(f"\nFecha de referencia: {date.today().isoformat()}")
        print("=" * 70)

        for etiqueta, mensaje, esperado in CASOS:
            print(f"\n[{etiqueta}]")
            print(f"  mensaje:  {mensaje}")
            print(f"  esperado: {esperado}")

            extraida = await extraer_huerta(mensaje)

            print(f"  huerta:   {extraida.nombre_huerta!r}")
            print(f"  barrio:   {extraida.barrio_codigo!r}")
            if not extraida.cultivos:
                print("  cultivos: (ninguno)")
            for cultivo in extraida.cultivos:
                fecha = cultivo.fecha_siembra()
                marca = "aproximada" if cultivo.fecha_imprecisa else "precisa"
                print(
                    f"  cultivo:  {cultivo.especie!r} | "
                    f"fecha={fecha} ({marca})"
                )
            print(f"  tiene_datos: {extraida.tiene_datos}")

        print("\n" + "=" * 70)
        print(
            "Revise a mano: que no haya inventado nada, que las especies estén\n"
            "literales y que 'pregunta, no registro' y 'sin nada de huerta'\n"
            "hayan salido vacíos. Un cultivo inventado se le mostraría a la\n"
            "usuaria como si lo hubiera dicho ella."
        )
    finally:
        await cerrar_pool()


if __name__ == "__main__":
    asyncio.run(main())
