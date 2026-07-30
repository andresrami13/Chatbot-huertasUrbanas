"""Carga de los prompts versionados de `app/agent/prompts/`.

Los prompts viven en archivos y no en cadenas dentro del código porque el
versionamiento de prompts es una práctica declarada en la metodología
(CLAUDE.md §11): la comparación entre `extraccion_v1.md` y un futuro
`extraccion_v2.md` tiene que poder leerse en el historial de git y citarse
en el documento de grado.

Se leen del disco una sola vez y quedan en memoria: en Railway el
sistema de archivos no cambia entre reinicios, y volver a leer el archivo
en cada mensaje sería trabajo inútil.

**Cuidado al editar un prompt:** los huecos se rellenan con
`str.format`, así que una llave literal en el texto rompe la carga con un
`KeyError`. Si algún prompt necesita mostrar un ejemplo en JSON, hay que
duplicar las llaves (`{{` y `}}`) o cambiar el mecanismo de plantilla.
"""

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_DIRECTORIO = Path(__file__).parent / "prompts"


@lru_cache(maxsize=None)
def cargar_prompt(nombre: str) -> str:
    """Devuelve el contenido de un prompt por su nombre de archivo.

    Falla de forma explícita si no existe. Un prompt ausente no puede
    tratarse como cadena vacía: el modelo respondería cualquier cosa y el
    fallo aparecería como una extracción absurda, no como un error.
    """
    ruta = _DIRECTORIO / nombre

    if not ruta.is_file():
        disponibles = sorted(p.name for p in _DIRECTORIO.glob("*.md"))
        raise FileNotFoundError(
            f"No existe el prompt '{nombre}' en {_DIRECTORIO}. "
            f"Disponibles: {disponibles or 'ninguno'}"
        )

    contenido = ruta.read_text(encoding="utf-8")
    logger.info("Prompt cargado | nombre=%s | caracteres=%d", nombre, len(contenido))
    return contenido
