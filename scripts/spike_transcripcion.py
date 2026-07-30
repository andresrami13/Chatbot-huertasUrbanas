"""Spike de transcripción: prueba el camino completo con un audio real.

No forma parte del servicio. Comprueba lo único que no se puede resolver
leyendo documentación: **si Gemini acepta el formato exacto en el que
WhatsApp manda las notas de voz.**

El asunto es que WhatsApp envía `audio/ogg; codecs=opus`, mientras que la
documentación de Gemini enumera `audio/ogg` describiéndolo como "OGG
Vorbis". Opus y Vorbis son códecs distintos dentro del mismo contenedor, así
que la compatibilidad no se puede dar por supuesta: hay que medirla.

Cómo usarlo:

1. Mande una nota de voz al número de pruebas desde un celular verificado.
2. Busque en la bitácora de Railway la línea `Audio recibido | media_id=...`
   y copie ese identificador.
3. Ejecútelo desde la raíz del repositorio, antes de 7 días (el `media_id`
   caduca):

       python -m scripts.spike_transcripcion <media_id>

Se imprime la transcripción en pantalla porque es una prueba manual que
usted ejecuta con su propia voz. El servicio **nunca** registra el
contenido de un mensaje (CLAUDE.md §11); este script no es el servicio.
"""

import asyncio
import sys

from app.core.gemini import MODELO_GENERATIVO
from app.services.media import descargar_audio
from app.services.normalizacion import transcribir_bytes


async def main(media_id: str) -> int:
    print(f"media_id: {media_id}")
    print(f"Modelo generativo: {MODELO_GENERATIVO}\n")

    # --- 1. Descarga. Las dos peticiones autenticadas de la Media API.
    print("[1/2] Descargando de la Media API de Meta...")
    descarga = await descargar_audio(media_id)

    if descarga is None:
        print(
            "  FALLO. Revise la bitácora de arriba. Causas habituales:\n"
            "    - el media_id ya caducó (7 días);\n"
            "    - META_ACCESS_TOKEN vencido;\n"
            "    - el media_id pertenece a otro número de teléfono."
        )
        return 1

    audio, mime_type = descarga
    print(f"  OK. {len(audio)} bytes, mime_type={mime_type}")
    if "opus" in mime_type:
        print("  Nota: el mime_type conserva el códec; deberia venir sin él.")

    # --- 2. Transcripción, sobre los bytes ya descargados. Así, si falla,
    # el culpable es Gemini y no la red de Meta.
    print("\n[2/2] Transcribiendo con Gemini...")
    texto = await transcribir_bytes(audio, mime_type, media_id=media_id)

    if texto is None:
        print(
            "  FALLO. Si la descarga funcionó, lo más probable es que Gemini\n"
            "  haya rechazado el formato. En ese caso hay que convertir el\n"
            "  audio antes de mandarlo (ffmpeg a audio/mp3 o audio/wav), lo\n"
            "  que añade una dependencia del sistema al despliegue."
        )
        return 1

    print(f"  OK. {len(texto)} caracteres.\n")
    print("-" * 60)
    print(texto)
    print("-" * 60)
    print(
        "\nCompruebe a mano: ¿dice lo que usted dijo? Importa sobre todo que\n"
        "acierte los nombres de cultivos y de barrios, que es lo que la\n"
        "extracción de entidades tiene que sacar después."
    )
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)

    sys.exit(asyncio.run(main(sys.argv[1])))
