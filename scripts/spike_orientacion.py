"""Spike del CU2: recupera y redacta, contra la base y la API reales.

No escribe nada. Se ejecuta a mano desde la raíz:

    python -m scripts.spike_orientacion

Comprueba las cuatro cosas que pueden salir mal y que no se ven mirando
solo la similitud:

1. Que una consulta legítima reciba una respuesta apoyada en el documento.
2. Que la respuesta **cite la fuente**, sin la cual el CU2 incumple la
   jerarquía de CLAUDE.md §6.
3. Que una consulta ajena al dominio caiga en el texto fijo y **no** reciba
   una respuesta improvisada.
4. Que se respete la forma: trato de usted, frases cortas, sin mencionar
   figuras ni tablas que la usuaria no puede ver.
"""

import asyncio
import re

from app import textos
from app.core.basedatos import abrir_pool, cerrar_pool
from app.services.orientacion import consultar_orientacion

CONSULTAS = [
    # La insignia: con el umbral de 0.70 no recuperaba nada.
    "a mi mata de tomate le salieron unos bichitos verdes, que le echo",
    "cada cuanto tengo que regar la huerta",
    "que tierra le pongo a las materas",
    "como preparo un purin para las plagas",
    # Debe caer en el texto fijo, sin improvisar.
    "cuando cambio el aceite del carro",
    # El caso difícil de la calibración: roza el dominio pero pide trámite.
    "donde me inscribo para que me regalen una compostera",
]

# Lo que el prompt prohíbe expresamente.
PROHIBIDO = re.compile(
    r"\b(figura|tabla|capítulo|fragmento|contexto|documento|base de datos)\b",
    re.IGNORECASE,
)


async def main() -> None:
    await abrir_pool()
    try:
        for consulta in CONSULTAS:
            print("=" * 70)
            print(f"PREGUNTA: {consulta}")
            print("=" * 70)

            respuesta = await consultar_orientacion(consulta)
            print(respuesta)

            lineas = [l for l in respuesta.split("\n") if l.strip()]
            avisos = []

            # Se cuentan palabras y no renglones: el modelo escribe un solo
            # párrafo largo, así que contar "\n" siempre daría 2 y no
            # mediría nada. En la pantalla de un celular, 80 palabras ya
            # son media pantalla.
            palabras = len(respuesta.split())
            if palabras > 90:
                avisos.append(f"se pasa de largo: {palabras} palabras")

            # Los textos fijos no citan fuente, y es correcto: no hay
            # ninguna que citar. Se comparan contra el texto real y no
            # contra una subcadena inventada.
            es_texto_fijo = respuesta in (
                textos.ORIENTACION_SIN_RESPALDO,
                textos.ORIENTACION_NO_DISPONIBLE,
            )
            if not es_texto_fijo and "Fuente:" not in respuesta:
                avisos.append("no cita la fuente con el formato pedido")

            if re.search(r"\bt[uú]\b|\btienes\b|\bpuedes\b", respuesta, re.IGNORECASE):
                avisos.append("tutea; debe tratarla de usted")

            prohibidas = set(PROHIBIDO.findall(respuesta))
            if prohibidas:
                avisos.append(f"menciona {sorted(prohibidas)}")

            print(
                f"\n[{len(lineas)} líneas, {len(respuesta)} caracteres]"
                + (f"  AVISOS: {'; '.join(avisos)}" if avisos else "  forma correcta")
            )
            print()
    finally:
        await cerrar_pool()


if __name__ == "__main__":
    asyncio.run(main())
