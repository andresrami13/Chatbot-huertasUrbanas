"""Genera `db/003_catalogo_barrios_bosa.sql` desde el listado oficial.

    python -m scripts.generar_catalogo_barrios

Lee `fuentes/barrios_localidad.json` —el listado de barrios de Bogotá por
localidad— y escribe el script de siembra con los de Bosa. **No toca la
base**: solo produce el `.sql`, que se ejecuta aparte.

Ninguna fuente se siembra a mano (CLAUDE.md §11). Este generador existe
para que el catálogo sea reproducible y para que se vea de dónde salió cada
fila, igual que `scripts/catalogo_fuentes.py` hace con los PDF.

El JSON vive en `fuentes/`, que está en el `.gitignore`, así que no viaja
en el repositorio. El `.sql` generado sí, y es el que manda.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

# Localidad 7 del listado oficial.
LOCALIDAD_BOSA = 7

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "fuentes" / "barrios_localidad.json"
DESTINO = RAIZ / "db" / "003_catalogo_barrios_bosa.sql"

CABECERA = """\
-- =====================================================================
-- 003 — Catálogo de barrios de Bosa (ADR-0016)
--
-- GENERADO por `python -m scripts.generar_catalogo_barrios` desde el
-- listado oficial de barrios de Bogotá por localidad. No se edita a mano.
--
-- Sustituye a los siete barrios de la UPZ 84 que sembraba `002`, que se
-- calibraron contra el anteproyecto §5.3.1. Dos correcciones respecto de
-- aquel:
--
--  - `Los 3 Sectores` NO entra: no aparece en el listado oficial, ni
--    exacta ni parcialmente. El ADR-0002 lo había sembrado resolviendo a
--    favor del §5.3.1 frente al §7.1, que lo omitía; el listado indica
--    que era el §7.1 el que acertaba, y que §5.3.1 recogía un nombre de
--    uso comunitario y no un barrio oficial.
--  - El alcance pasa de la UPZ 84 Bosa Occidental a la localidad entera.
--    Es deliberado: tener de más un barrio cuesta una fila, y que falte
--    cuesta una usuaria que no puede completar el onboarding.
--
-- Los nombres van en MAYÚSCULA y sin recortar, tal como vienen del
-- listado oficial. No hay límite de longitud que obligue a acortarlos: la
-- desambiguación se presenta como lista numerada en el cuerpo de un
-- mensaje —1024 caracteres— y no como botones, cuyo rótulo se queda en 20
-- (ADR-0016, decisión 4).
--
-- `otro` se conserva. Es la salida cuando ninguno de los candidatos es su
-- barrio, y sin él la pregunta del barrio no tendría fin, porque es
-- obligatoria (ADR-0002 y ADR-0016, decisión 6).
--
-- Idempotente: puede reejecutarse sin duplicar filas. El `do update`
-- —y no `do nothing`, que es lo que hacía 002— es necesario porque un
-- código que ya exista tiene que quedar con el nombre y el `activo` de
-- este listado; con `do nothing` la fila vieja sobreviviría intacta.
-- =====================================================================

insert into public.barrio (codigo, nombre) values
"""

PIE = """\
on conflict (codigo) do update
        set nombre = excluded.nombre,
            activo = true;
"""


def codigo_de(nombre: str) -> str:
    """Convierte el nombre oficial en un código estable y sin acentos.

    El código es lo que consume el catálogo y lo que devuelve el modelo al
    desambiguar; el nombre es lo que lee la usuaria. Se separan para que
    corregir una tilde del nombre no invalide las huertas que ya apuntan a
    esa fila.
    """
    sin_tildes = (
        unicodedata.normalize("NFD", nombre).encode("ascii", "ignore").decode()
    )
    limpio = re.sub(r"[^a-z0-9]+", "_", sin_tildes.lower())
    return re.sub(r"_+", "_", limpio).strip("_")


def main() -> int:
    if not ORIGEN.exists():
        print(f"No se encuentra {ORIGEN}", file=sys.stderr)
        return 1

    registros = json.loads(ORIGEN.read_text(encoding="utf-8"))
    nombres = sorted(
        {
            r["barrio"].strip()
            for r in registros
            if r.get("localidad_numero") == LOCALIDAD_BOSA and r.get("barrio")
        }
    )

    filas: dict[str, str] = {}
    for nombre in nombres:
        codigo = codigo_de(nombre)
        if not codigo:
            print(f"  aviso: nombre sin código utilizable: {nombre!r}")
            continue
        if codigo in filas:
            # No debería ocurrir con el listado actual, y si ocurriera hay
            # que verlo: dos barrios distintos con el mismo código dejarían
            # uno de los dos fuera del catálogo sin avisar.
            print(f"  AVISO: código repetido {codigo!r}: {filas[codigo]!r} y {nombre!r}")
            continue
        filas[codigo] = nombre

    # `otro` va el último y aparte, porque no sale del listado: es la
    # salida del ADR-0002 para el barrio no previsto.
    lineas = [
        f"    ('{codigo}', '{nombre.replace(chr(39), chr(39) * 2)}')"
        for codigo, nombre in filas.items()
    ]
    lineas.append("    ('otro', 'Otro')")

    DESTINO.write_text(CABECERA + ",\n".join(lineas) + "\n" + PIE, encoding="utf-8")

    print(f"Escrito {DESTINO.relative_to(RAIZ)}")
    print(f"  barrios de Bosa: {len(filas)}")
    print(f"  filas totales:   {len(lineas)} (con 'otro')")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
