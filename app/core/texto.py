"""Normalización de texto para comparar lo que escribe la usuaria.

Existe porque tres sitios necesitan la misma comparación indulgente y
hasta el 08/09/2026 había dos copias idénticas de la función, en
`consentimiento.py` y en `onboarding.py`. La tercera —el filtro por
especie del CU7— iba a ser la de la gota, así que se factorizó
(CLAUDE.md §12).

**No sirve para almacenar ni para mostrar, solo para comparar.** Lo que se
guarda y lo que se le enseña conserva siempre las tildes y la forma en que
ella lo escribió: «cebolla larga» se persiste tal cual (ADR-0013), y los
barrios van en mayúscula y sin recortar (ADR-0016).
"""

import unicodedata


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y sin signos, para comparar.

    Hace falta porque quien escribe desde un celular no pone tildes de
    forma fiable, y porque una nota de voz transcrita llega con la
    puntuación que el modelo decida. Comparar en crudo dejaría fuera «sí»
    frente a «si» y «Holanda,» frente a «Holanda».

    Los espacios repetidos se colapsan a uno, de modo que el resultado se
    puede comparar entero o por palabras.
    """
    sin_tildes = "".join(
        c
        for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(
        "".join(c for c in sin_tildes if c.isalnum() or c.isspace()).split()
    )
