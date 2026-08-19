"""Ingesta de una fuente oficial a la colección vectorial (Fase 6, CU2).

**No forma parte del servicio.** Se ejecuta a mano, desde la raíz del
repositorio, y escribe en Supabase:

    python -m scripts.ingesta_fuente --listar
    python -m scripts.ingesta_fuente --fuente jbb_practicas_2022 --simular
    python -m scripts.ingesta_fuente --fuente jbb_practicas_2022
    python -m scripts.ingesta_fuente --fuente jbb_practicas_2022 --reingerir

Qué documento se ingiere y con qué parámetros lo dice
`scripts/catalogo_fuentes.py`. Hasta la Fase 6 había una sola fuente y sus
datos eran constantes de este módulo; con seis documentos eso obligaba a
editar el script para cambiar de documento, que es justo lo que impide
repetir una ingesta igual meses después.

Vive en `scripts/` y no en `app/` por una razón concreta: así `pypdf` se
queda en `requirements-scripts.txt` y no entra en el `requirements.txt` que
se despliega en Railway. El servicio no lee PDF nunca; solo consulta lo que
esto dejó escrito.

El acceso a la base lo hace `app/services/repositorio.py`, que sigue siendo
el punto único de acceso a Supabase (Fase 3, Tabla 2). Aquí solo vive lo
propio del documento: extraer, limpiar, trocear.

## Por qué la limpieza es la mitad del trabajo

El PDF está maquetado, y lo que `extract_text` devuelve son renglones de la
página, no frases. Sin reconstruir los párrafos, los fragmentos quedarían
cortados por la maquetación y no por el sentido, que es justo lo que
arruina una recuperación. Comprobado sobre el documento del Jardín Botánico
(128 páginas):

- El número de página aparece **de dos formas**: en renglón propio (47
  páginas) y pegado a la primera palabra (32 páginas, `"13medicinal"`).
- Las palabras cortadas al final de renglón vienen en **dos variantes**:
  `"enten-"` (325 veces) y `"inte -"`, con espacio antes del guión (55).
- **No hay párrafos separados por renglón en blanco.** El corte de párrafo
  hay que deducirlo de la puntuación y de la mayúscula siguiente.
- **No hay encabezado ni pie repetido**, lo que importa más de lo que
  parece: un texto fijo repetido en todos los fragmentos infla por igual la
  similitud de todos, que es el defecto medido en la colección comunitaria
  (ESTADO.md, spike del 29/07). La colección oficial se libra de él, y por
  eso tampoco se le añade aquí ninguna plantilla de atribución: la entidad
  y el título salen de la tabla `fuente` al responder, no del texto
  vectorizado.

Eso último **no vale para todos los documentos**. La cartilla de 2011 sí
lleva cabecera y pie en todas sus páginas, y por eso la detección de
plantilla no es un adorno: es lo que le impide contaminar el corpus.
"""

import argparse
import asyncio
import re
import statistics
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import httpx

from app.core.basedatos import abrir_pool, cerrar_pool
from app.services.embeddings import vectorizar_documentos
from app.services.repositorio import (
    contar_fragmentos_oficiales,
    crear_fuente,
    listar_contenidos_oficiales,
    obtener_fuente_por_url,
    reemplazar_fragmentos_oficiales,
)
from scripts.catalogo_fuentes import FuenteDocumento, describir, obtener

# --- Troceo (CLAUDE.md §8: 300–500 tokens, solape de 50) -----------------
#
# El tamaño se mide en caracteres y no llamando al contador de tokens en
# cada corte: serían ~100 llamadas de red para gobernar un punto de corte.
# Pero la ratio no se supone, se **mide**, y vive en el catálogo porque es
# propia de cada documento: la nomenclatura botánica tokeniza mucho más
# denso que la prosa (ADR-0009, decisión 4).

TOKENS_OBJETIVO = 500
TOKENS_SOLAPE = 50

# Tope duro por fragmento. `gemini-embedding-001` admite 2 048 tokens de
# entrada por texto y trunca en silencio lo que sobre: un fragmento
# demasiado largo se vectorizaría a medias sin dar error. Este límite deja
# margen de sobra sobre el objetivo de 500.
TOKENS_TOPE = 1500

# Textos por llamada de vectorización. La documentación de Gemini no
# publica un máximo de entradas por petición —solo el de 2 048 tokens por
# texto—, así que se lotea conservador en lugar de suponer un número.
LOTE_VECTORIZACION = 16

_VIÑETAS = "○⚫•▪-–—"
_FIN_DE_FRASE = ".:;?!»”)"

_PIE_DE_FIGURA = re.compile(r"^\s*(fig\.|figura|tabla|fuente:)\s", re.IGNORECASE)

# Renglón de índice o tabla de contenido: "Cilantro ........... 51". Los
# puntos de relleno son la señal, y no aparecen en prosa.
#
# Se descartan porque son veneno para la recuperación, y está medido: son
# 10 de 774 fragmentos (1.3 % del corpus) y salían entre los cuatro mejores
# en el 25 % de las consultas reales, como el MEJOR en el 10 %. Un índice
# es una lista de nombres de plantas, así que puntúa altísimo contra
# cualquier pregunta sobre plantas y no responde absolutamente nada.
#
# Ese es el modo de fallo que la usuaria notó en la prueba del 15/08, con
# un mensaje que decía "sino me estas respondiendo nada, porque citas
# información?". Ningún umbral lo arregla: un fragmento inútil que puntúa
# 0.7185 pasa cualquier umbral razonable.
_LINEA_DE_INDICE = re.compile(r"\.{4,}")


# =========================================================================
# Obtención del PDF
# =========================================================================


def _obtener_pdf(fuente: FuenteDocumento, ruta: Path | None) -> Path:
    """Devuelve la ruta al PDF, descargándolo si hace falta.

    Se cachea en `fuentes/`, que está fuera del control de versiones: son
    publicaciones de terceros y el repositorio es público.
    """
    destino = ruta or fuente.ruta

    if destino.exists():
        print(f"PDF local: {destino} ({destino.stat().st_size / 1e6:.1f} MB)")
        return destino

    if ruta is not None:
        raise SystemExit(f"No existe el archivo indicado: {ruta}")

    destino.parent.mkdir(parents=True, exist_ok=True)
    print(f"Descargando de {fuente.url}")

    # La resolución DNS del equipo de desarrollo falla de forma
    # intermitente (ESTADO.md): se reintenta antes de dar el fallo por
    # bueno.
    ultimo_error: Exception | None = None
    for intento in (1, 2, 3):
        try:
            with httpx.stream(
                "GET", fuente.url, timeout=120.0, follow_redirects=True
            ) as respuesta:
                respuesta.raise_for_status()
                with destino.open("wb") as archivo:
                    for trozo in respuesta.iter_bytes():
                        archivo.write(trozo)
            print(f"Descargado en {destino} ({destino.stat().st_size / 1e6:.1f} MB)")
            return destino
        except Exception as error:  # noqa: BLE001 — se reintenta y se informa
            ultimo_error = error
            print(f"  intento {intento} fallido: {type(error).__name__}")

    raise SystemExit(f"No se pudo descargar el PDF: {ultimo_error}")


# =========================================================================
# Extracción y limpieza
# =========================================================================


def _normalizar_texto(texto: str) -> str:
    """Unifica espacios raros y deshace las ligaduras tipográficas.

    Dos tratamientos distintos con el mismo fin: que la misma palabra se
    escriba igual venga del documento que venga.

    **Espacios.** El PDF trae espacio duro (U+00A0), espacio fino (U+2009)
    y espacio de anchura cero (U+200B), que no son separadores para
    `split()` y acabarían pegados dentro de las palabras. El de anchura
    cero hay que quitarlo a mano: la normalización de Unicode no lo toca.

    **Ligaduras.** Se normaliza con **NFKC y no con NFC**, que es lo que
    deshace `ﬁ` (U+FB01) en las dos letras `fi`. No es cosmético: medido el
    15/08/2026, la cartilla de 2022 trae 293 ligaduras —265 de `ﬁ` y 28 de
    `ﬂ`— dentro de palabras corrientes como «beneﬁcios», «especíﬁcas» o
    «ﬂoración». Vectorizadas así, esas palabras no son la misma palabra que
    escribe una usuaria en WhatsApp, y el fragmento que las contiene se
    recupera peor sin que nada lo delate.

    NFC no bastaba porque las ligaduras son equivalencia **de
    compatibilidad**, no canónica.

    El coste sobre lo ya ingerido es despreciable, y se comprobó antes de
    cambiarlo: el documento del Jardín Botánico no tiene ni una ligadura y
    NFKC solo le altera 9 caracteres de 130 719, sin mover ningún límite de
    fragmento. Sigue dando los mismos 81.
    """
    texto = texto.replace("​", "")
    return unicodedata.normalize("NFKC", texto)


def _quitar_numero_pagina(texto: str, folio: int, variable: bool = False) -> str:
    """Quita el folio de la página, en cualquiera de sus tres formas.

    `folio` es el número **impreso**, que no siempre coincide con el índice
    de la página dentro del PDF: si el archivo trae hojas de cortesía sin
    numerar, van desfasados. El desfase lo declara el catálogo y lo calcula
    `--detectar-folio`.

    Medidas sobre el documento del Jardín Botánico, entre las páginas 12 y
    121:

    - renglón propio, `"12\\nINTRODUCCIÓN"` — 39 páginas;
    - pegado a la palabra, `"13medicinal de algunas..."` — 30 páginas;
    - seguido de espacio, `"48 Nombre común..."` — 37 páginas.

    La tercera es fácil de pasar por alto y no es inocua: el folio se
    queda incrustado a mitad del texto ("...Verbenaceae x 48 Nombre
    común...") y acaba dentro de un fragmento vectorizado.

    Solo se quita **si coincide con el folio esperado**. Borrar cualquier
    dígito inicial se llevaría por delante un texto que empezara
    legítimamente con una cifra, y el resto que empieza por dígito se
    respeta por eso: en "1234 kg" el "12" de la página 12 no es folio.
    """
    texto = texto.lstrip()
    esperado = str(folio)

    # Con el desfase variable no se puede comparar contra un folio
    # esperado, porque no lo hay: se quita cualquier renglón que sea solo
    # un número. Ver `folio_desfase_variable` en el catálogo.
    if variable:
        return "\n".join(
            linea
            for linea in texto.split("\n")
            if not re.fullmatch(r"[-–—\s]*\d{1,3}[-–—\s]*", linea.strip())
        )

    if texto.startswith(esperado):
        resto = texto[len(esperado) :]
        if resto[:1].isspace() or resto[:1].isalpha():
            texto = resto.lstrip()

    # En renglón propio, con o sin adornos. La cartilla de 2011 lo imprime
    # como `- 16 -`, y con guiones no coincide con el número pelado: se
    # quedaba dentro del texto vectorizado. No basta con mirar el último
    # renglón, que es lo que hacía antes: ahí el folio va en el segundo,
    # justo debajo de la cabecera.
    solo_folio = re.compile(rf"^[-–—\s]*{esperado}[-–—\s]*$")

    return "\n".join(
        linea
        for linea in texto.split("\n")
        if not solo_folio.match(linea.strip())
    )


# --- Páginas de dos columnas --------------------------------------------
#
# Solo aplica al texto extraído en modo `layout`, que es el único que
# conserva la posición horizontal de cada palabra. Leído renglón a renglón,
# una página de dos columnas entreteje dos textos que no tienen nada que
# ver, frase a frase. Son 82 de las 260 páginas de Sembrando Biodiversidad.
#
# La calle se detecta por lo que es: una franja vertical en blanco en casi
# todos los renglones **que tienen texto a ambos lados**. Solo cuentan esos
# renglones, porque un título corto o un pie centrado no dicen nada sobre
# si la página tiene columnas.

# Mínimo de renglones que cruzan la calle. Con menos, dos renglones sueltos
# bastarían para partir en dos una página de texto corrido.
RENGLONES_QUE_CRUZAN = 6

# El mismo mínimo, dentro de un bloque suelto de la página. Se baja porque
# una lista de plagas a dos columnas rara vez pasa de cuatro o cinco
# renglones, y con seis se quedaba sin detectar.
RENGLONES_QUE_CRUZAN_EN_BLOQUE = 4

# Qué proporción de esos renglones debe estar en blanco en la franja.
PROPORCION_EN_BLANCO = 0.92

# Ancho mínimo de la calle, en caracteres. Una separación de una o dos
# columnas es el espaciado normal entre palabras.
ANCHO_MINIMO_CALLE = 4


def _detectar_calles(
    lineas: list[str], renglones_minimos: int = RENGLONES_QUE_CRUZAN
) -> list[tuple[int, int]]:
    """Franjas verticales en blanco que separan columnas de texto."""
    con_texto = [linea for linea in lineas if linea.strip()]
    if not con_texto:
        return []

    ancho = max(len(linea) for linea in con_texto)
    candidatas: list[int] = []

    for columna in range(1, ancho):
        cruzan = 0
        blancas = 0
        for linea in con_texto:
            if not linea[:columna].strip() or not linea[columna + 1 :].strip():
                continue
            cruzan += 1
            if columna >= len(linea) or linea[columna] == " ":
                blancas += 1

        if cruzan >= renglones_minimos and blancas / cruzan >= PROPORCION_EN_BLANCO:
            candidatas.append(columna)

    agrupadas: list[tuple[int, int]] = []
    for columna in candidatas:
        if agrupadas and columna == agrupadas[-1][1] + 1:
            agrupadas[-1] = (agrupadas[-1][0], columna)
        else:
            agrupadas.append((columna, columna))

    return [
        (inicio, fin)
        for inicio, fin in agrupadas
        if fin - inicio + 1 >= ANCHO_MINIMO_CALLE
    ]


def _partir_por_calle(lineas: list[str], calle: tuple[int, int]) -> list[str]:
    """Devuelve los renglones de la izquierda y luego los de la derecha.

    Un renglón que **invade** la calle —un título que cruza la página
    entera— se deja entero en el bloque izquierdo en lugar de partirlo por
    la mitad: la detección tolera hasta un 8 % de renglones así, y cortarlos
    destruiría el texto en vez de ordenarlo.
    """
    inicio, fin = calle
    izquierda: list[str] = []
    derecha: list[str] = []

    for linea in lineas:
        if linea[inicio : fin + 1].strip():
            izquierda.append(linea)
            continue

        parte_izquierda = linea[:inicio].rstrip()
        parte_derecha = linea[fin + 1 :].rstrip() if len(linea) > fin else ""

        if parte_izquierda:
            izquierda.append(parte_izquierda)
        if parte_derecha:
            derecha.append(parte_derecha)

    # El renglón en blanco entre los dos bloques cierra el párrafo: sin él,
    # la última frase de la columna izquierda se pegaría a la primera de la
    # derecha, que es justo lo que se está corrigiendo.
    return izquierda + [""] + derecha


def _separar_columnas(texto: str) -> tuple[str, bool]:
    """Reordena las columnas de una página para leerlas en orden.

    Se intenta primero con la página entera. Si no hay calle que la cruce
    de arriba abajo, se prueba **bloque a bloque**, separando por los
    renglones en blanco que la maquetación ya deja entre secciones.

    Los dos pasos hacen falta porque hay páginas mixtas, y son las que más
    daño hacían: la ficha de cada especie trae una sección de prosa de una
    sola columna y, debajo, la lista de plagas y enfermedades en dos. Con
    la detección solo por página, esa lista se quedaba entretejida —«Trips
    (Thrips tabaci Lind.): generan Trozador (Agriotes lineatus L.):
    manchas plateadas en las hojas conocido como gusano del alambre»—, y es
    justo el contenido que responde la consulta insignia del CU2.

    En un bloque se exigen menos renglones que en una página entera: una
    lista de plagas a dos columnas rara vez pasa de cuatro o cinco.
    """
    lineas = texto.split("\n")

    calles = _detectar_calles(lineas)
    if calles:
        mayor = max(calles, key=lambda calle: calle[1] - calle[0])
        return "\n".join(_partir_por_calle(lineas, mayor)), True

    bloques: list[list[str]] = [[]]
    for linea in lineas:
        if linea.strip():
            bloques[-1].append(linea)
        elif bloques[-1]:
            bloques.append([])

    resultado: list[str] = []
    se_partio = False

    for bloque in bloques:
        calles_bloque = _detectar_calles(bloque, RENGLONES_QUE_CRUZAN_EN_BLOQUE)
        if calles_bloque:
            mayor = max(calles_bloque, key=lambda calle: calle[1] - calle[0])
            resultado.extend(_partir_por_calle(bloque, mayor))
            se_partio = True
        else:
            resultado.extend(bloque)
        resultado.append("")

    return "\n".join(resultado), se_partio


def _detectar_desfase_folio(crudas: list[tuple[int, str]]) -> None:
    """Diagnóstico: en cuántas páginas encaja cada desfase posible.

    No se ejecuta durante la ingesta. Sirve para rellenar el catálogo con
    un número medido en lugar de uno mirado por encima, que es donde se
    cuela el error: en la cartilla de 2022 hay páginas sueltas con cifras
    que parecen folios y no lo son, y una sola muestra habría dado un
    desfase equivocado para todo el documento.
    """
    conteo: Counter[int] = Counter()

    for numero, texto in crudas:
        limpio = texto.strip()
        if not limpio:
            continue

        candidatos: set[int] = set()

        inicial = re.match(r"(\d{1,3})", limpio)
        if inicial:
            candidatos.add(int(inicial.group(1)))

        lineas = [linea.strip() for linea in limpio.split("\n") if linea.strip()]
        if lineas:
            final = re.search(r"(\d{1,3})\s*$", lineas[-1])
            if final:
                candidatos.add(int(final.group(1)))

        # En renglón propio y con adornos, que es como lo imprime la
        # cartilla de 2011: `- 16 -`, y además en el segundo renglón, no en
        # el último. El detector tiene que reconocer las mismas formas que
        # `_quitar_numero_pagina`, o declararía que el documento no lleva
        # folio y habría que fijarlo a ojo.
        for linea in lineas:
            adornado = re.fullmatch(r"[-–—\s]*(\d{1,3})[-–—\s]*", linea)
            if adornado:
                candidatos.add(int(adornado.group(1)))

        for candidato in candidatos:
            desfase = numero - candidato
            if 0 <= desfase <= 20:
                conteo[desfase] += 1

    total = sum(1 for _, texto in crudas if texto.strip())
    print(f"\nDesfase del folio, sobre {total} páginas con texto:")

    if not conteo:
        print("  No se encontró ningún folio. El documento puede no llevarlo.")
        return

    for desfase, veces in conteo.most_common(5):
        print(
            f"  desfase {desfase:2d}  encaja en {veces:3d} páginas "
            f"({100 * veces / total:.0f} %)"
        )

    # Varios desfases con peso repartido significan que el desfase no es
    # constante: el PDF trae páginas sin numerar intercaladas y cada una
    # corre la cuenta. Pasó en la cartilla de 2011, donde crece de 2 a 5, y
    # ahí ningún número único sirve. Sin este aviso, el más votado parecía
    # el bueno y dejaba el folio dentro del texto en la mitad del documento.
    repartidos = [
        desfase for desfase, veces in conteo.items() if veces >= total * 0.10
    ]
    if len(repartidos) > 1:
        print(
            f"\n  El desfase NO es constante: {sorted(repartidos)} tienen peso.\n"
            "  Suele ser por páginas sin numerar intercaladas. Ningún número\n"
            "  único sirve: use folio_desfase_variable=True en el catálogo."
        )
        return

    mejor, veces = conteo.most_common(1)[0]
    if veces < total * 0.4:
        print(
            "\n  Ninguno encaja en la mayoría de las páginas. Compruebe a "
            "mano antes de fiarse de este número."
        )
    else:
        print(f"\n  Sugerido para el catálogo: desfase_folio={mejor}")


def _detectar_plantilla(paginas: list[str], paginas_para_plantilla: int) -> set[str]:
    """Renglones que se repiten en tantas páginas que no son contenido.

    El umbral lo pone el catálogo por documento. En prosa corrida basta con
    10; en un documento organizado en fichas de especie hay que subirlo
    mucho, porque ahí un nombre de familia botánica se repite en decenas de
    páginas siendo contenido legítimo. Medido en el catálogo de plantas:
    `Compositae` sale en 12 páginas y `Lamiaceae` en 11, y con el umbral de
    10 se irían las dos.
    """
    apariciones: dict[str, int] = {}

    for texto in paginas:
        vistos = {linea.strip() for linea in texto.split("\n") if linea.strip()}
        for linea in vistos:
            if not linea.isdigit():
                apariciones[linea] = apariciones.get(linea, 0) + 1

    return {
        linea
        for linea, veces in apariciones.items()
        if veces >= paginas_para_plantilla
    }


def _es_titulo(linea: str) -> bool:
    """¿El renglón es un encabezado de sección?

    Interesa por dos motivos: un título nunca continúa el párrafo anterior,
    y marca un buen sitio por donde cortar un fragmento.
    """
    if len(linea) > 70 or linea.endswith((".", ",", ";")):
        return False

    letras = [caracter for caracter in linea if caracter.isalpha()]
    if not letras:
        return False

    mayusculas = sum(1 for caracter in letras if caracter.isupper())
    return mayusculas / len(letras) >= 0.6


def _empieza_parrafo(anterior: str, linea: str) -> bool:
    """Decide si `linea` abre un párrafo nuevo o continúa el anterior.

    En estos PDF no hay renglones en blanco entre párrafos, así que el
    corte se deduce: el renglón anterior cerró una frase y este empieza en
    mayúscula, o uno de los dos es un título, o este arranca con viñeta.
    """
    if not anterior:
        return True

    # Una palabra cortada nunca cierra un párrafo, pase lo que pase.
    if anterior.rstrip().endswith("-"):
        return False

    if linea[:1] in _VIÑETAS:
        return True

    if _es_titulo(linea) or _es_titulo(anterior):
        return True

    return anterior.rstrip().endswith(tuple(_FIN_DE_FRASE)) and (
        linea[:1].isupper() or linea[:1].isdigit()
    )


def _unir(anterior: str, linea: str) -> str:
    """Pega dos renglones del mismo párrafo, recomponiendo la palabra rota.

    Las dos variantes del documento: `"enten-"` y `"inte -"`. Solo se
    recompone si lo que sigue empieza en minúscula; si empieza en mayúscula
    el guión probablemente no era un corte de palabra, y unir destruiría el
    texto en lugar de arreglarlo.
    """
    limpio = anterior.rstrip()

    if limpio.endswith("-") and linea[:1].islower():
        return limpio[:-1].rstrip() + linea

    return f"{limpio} {linea}"


def _reconstruir_parrafos(paginas: list[str], plantilla: set[str]) -> list[str]:
    """Convierte renglones de página en párrafos.

    Las páginas se procesan **encadenadas, no una a una**: un párrafo que
    cruza el salto de página tiene que quedar entero. La página 13 del
    documento del Jardín Botánico empieza a mitad de la frase que abrió la
    12.
    """
    parrafos: list[str] = []
    actual = ""

    for texto in paginas:
        for cruda in texto.split("\n"):
            linea = " ".join(cruda.split())

            if (
                not linea
                or linea in plantilla
                or _PIE_DE_FIGURA.match(linea)
                or _LINEA_DE_INDICE.search(linea)
            ):
                # Un pie de figura remite a una imagen que la usuaria no va
                # a ver por WhatsApp: como fragmento recuperable no dice
                # nada. Cerrar el párrafo aquí, además, evita que el pie se
                # cuele en mitad de una frase.
                if actual:
                    parrafos.append(actual)
                    actual = ""
                continue

            if _empieza_parrafo(actual, linea):
                if actual:
                    parrafos.append(actual)
                actual = linea
            else:
                actual = _unir(actual, linea)

    if actual:
        parrafos.append(actual)

    return parrafos


# =========================================================================
# Tablas de especies
# =========================================================================
#
# El documento del Jardín Botánico trae cuatro tablas de especies aptas
# para el clima de Bogotá, con las columnas: nombre común, nombre
# científico, familia, exótica y nativa. Al extraer el PDF las columnas se
# colapsan en una fila corrida y las dos últimas quedan reducidas a una `x`
# suelta:
#
#     Nombre común Nombre científico Familia Exótica Nativa
#     Feijoa Acca sellowiana (O.Berg) Burret Myrtaceae x
#     Tomate Solanum lycopersicum L. Solanaceae x
#
# Ya no se puede saber a cuál de las dos columnas pertenece esa marca. El
# problema no es que falte el dato: es que el fragmento **invita a
# inventarlo**, y estos fragmentos entran como fuente OFICIAL, el nivel más
# alto de la jerarquía (CLAUDE.md §6), donde la respuesta se da por
# verificada.
#
# Se quita entonces exactamente lo que la extracción destruyó —las marcas y
# su encabezado— y se conserva lo que sobrevivió intacto: nombre común,
# nombre científico y familia. La lista de ~80 especies sigue sirviendo
# para responder qué se puede sembrar, y ya no se puede afirmar de ninguna
# que sea nativa o introducida.

_ENCABEZADO_COLUMNAS = re.compile(r"\s*Exótica\s+Nativa", re.IGNORECASE)

# La `x` de celda va seguida de la primera palabra de la fila siguiente, en
# mayúscula, o cierra el texto. Se exige eso para no tocar la `x` de los
# híbridos botánicos —"Fragaria x ananassa"—, donde lo que sigue es el
# epíteto en minúscula, ni las medidas del tipo "30 x 40 centímetros".
_MARCA_DE_CELDA = re.compile(r"\s+x(?=\s+[A-ZÁÉÍÓÚÑ])|\s+x\s*$")


def _parece_tabla_de_especies(parrafo: str) -> bool:
    """¿El párrafo es una de las tablas de especies?

    Se exige una señal fuerte para no pasear la limpieza por la prosa: o
    lleva el encabezado, o acumula nombres de familia botánica, que fuera
    de una tabla no aparecen en racimo.
    """
    if "Nombre científico" in parrafo:
        return True

    familias = len(re.findall(r"(?:aceae|Leguminosae)\b", parrafo))
    return familias >= 3


def _limpiar_tablas(parrafos: list[str]) -> tuple[list[str], int]:
    """Quita de las tablas las columnas que la extracción dejó ambiguas."""
    limpios: list[str] = []
    tocados = 0

    for parrafo in parrafos:
        if not _parece_tabla_de_especies(parrafo):
            limpios.append(parrafo)
            continue

        nuevo = _ENCABEZADO_COLUMNAS.sub("", parrafo)
        # Repetido: al quitar una marca, la siguiente pasa a cumplir la
        # condición de ir seguida de mayúscula. Una sola pasada dejaría la
        # mitad de las celdas puestas.
        while True:
            reducido = _MARCA_DE_CELDA.sub("", nuevo)
            if reducido == nuevo:
                break
            nuevo = reducido

        if nuevo != parrafo:
            tocados += 1
        limpios.append(nuevo)

    return limpios, tocados


# =========================================================================
# Troceo
# =========================================================================


def _partir_por_frases(texto: str, tope: int) -> list[str]:
    """Parte un párrafo demasiado largo, por frases y nunca a mitad."""
    frases = re.split(r"(?<=[.:;])\s+", texto)
    piezas: list[str] = []
    actual = ""

    for frase in frases:
        candidato = f"{actual} {frase}".strip() if actual else frase
        if actual and len(candidato) > tope:
            piezas.append(actual)
            actual = frase
        else:
            actual = candidato

    if actual:
        piezas.append(actual)

    return piezas


def _cola_para_solape(texto: str, caracteres: int) -> str:
    """Final del fragmento anterior que se arrastra al siguiente.

    Avanza hasta el primer espacio para no empezar el solape a mitad de una
    palabra.
    """
    if len(texto) <= caracteres:
        return texto

    trozo = texto[-caracteres:]
    espacio = trozo.find(" ")
    return trozo[espacio + 1 :] if espacio != -1 else trozo


# Un rótulo es corto y no lleva cifras. Lo segundo importa más de lo que
# parece: el párrafo anterior al rótulo suele ser la última fila de una
# tabla de resultados —"Canastillas 0,806 30"— y también es corto.
_LARGO_MAXIMO_ROTULO = 60


def _parece_rotulo_de_ficha(parrafo: str) -> bool:
    return len(parrafo) <= _LARGO_MAXIMO_ROTULO and not any(
        caracter.isdigit() for caracter in parrafo
    )


def _inicios_de_ficha(
    parrafos: list[str], marcador: str, rotulos: int
) -> set[int]:
    """Índices de párrafo por los que hay que abrir fragmento nuevo.

    `rotulos` es cuántos párrafos de encabezado van **delante** del
    marcador y tienen que quedar dentro del fragmento nuevo, porque son lo
    que identifica de qué planta habla el resto. Depende de cómo esté
    maquetada la ficha, así que lo declara el catálogo.
    """
    patron = re.compile(marcador)
    inicios: set[int] = set()

    for indice, parrafo in enumerate(parrafos):
        if not patron.match(parrafo):
            continue

        inicio = indice
        for _ in range(rotulos):
            if inicio > 0 and _parece_rotulo_de_ficha(parrafos[inicio - 1]):
                inicio -= 1
            else:
                break

        inicios.add(inicio)

    return inicios


def _trocear(
    parrafos: list[str],
    caracteres_por_token: float,
    inicios_de_ficha: set[int] | None = None,
) -> list[str]:
    """Agrupa párrafos en fragmentos de 300–500 tokens con solape.

    Se acumula por párrafos completos: el corte cae siempre en un límite de
    párrafo, nunca dentro de una frase.

    `inicios_de_ficha` fuerza además el corte donde empieza una ficha nueva,
    **y ahí no se arrastra solape**: el solape existe para no perder la
    continuidad de un texto seguido, y entre dos especies distintas no hay
    continuidad que preservar. Arrastrarlo reintroduciría justo la
    contaminación que este corte viene a quitar.
    """
    maximo = int(TOKENS_OBJETIVO * caracteres_por_token)
    solape = int(TOKENS_SOLAPE * caracteres_por_token)
    tope = int(TOKENS_TOPE * caracteres_por_token)
    inicios_de_ficha = inicios_de_ficha or set()

    unidades: list[tuple[str, bool]] = []
    for indice, parrafo in enumerate(parrafos):
        abre_ficha = indice in inicios_de_ficha
        if len(parrafo) <= maximo:
            unidades.append((parrafo, abre_ficha))
        else:
            piezas = _partir_por_frases(parrafo, maximo)
            unidades.extend(
                (pieza, abre_ficha and orden == 0)
                for orden, pieza in enumerate(piezas)
            )

    fragmentos: list[str] = []
    actual = ""

    for unidad, abre_ficha in unidades:
        if abre_ficha and actual:
            fragmentos.append(actual)
            actual = unidad
            continue

        candidato = f"{actual} {unidad}".strip() if actual else unidad

        if actual and len(candidato) > maximo:
            fragmentos.append(actual)
            cola = _cola_para_solape(actual, solape)
            actual = f"{cola} {unidad}".strip() if cola else unidad
        else:
            actual = candidato

    if actual:
        fragmentos.append(actual)

    # Red de seguridad frente al truncado silencioso del modelo.
    excedidos = [pieza for pieza in fragmentos if len(pieza) > tope]
    if excedidos:
        raise RuntimeError(
            f"{len(excedidos)} fragmentos superan el tope de {tope} caracteres."
        )

    return fragmentos


# =========================================================================
# Informe
# =========================================================================


def _informar(
    fragmentos: list[str], muestra: int, caracteres_por_token: float
) -> None:
    """Imprime la distribución de tamaños y unos cuantos fragmentos."""
    longitudes = [len(pieza) for pieza in fragmentos]

    print(f"\nFragmentos: {len(fragmentos)}")
    print(
        f"Caracteres  min={min(longitudes)}  mediana="
        f"{int(statistics.median(longitudes))}  max={max(longitudes)}"
    )
    print(
        f"Tokens estimados (a {caracteres_por_token} car./token)  "
        f"min={int(min(longitudes) / caracteres_por_token)}  "
        f"mediana={int(statistics.median(longitudes) / caracteres_por_token)}  "
        f"max={int(max(longitudes) / caracteres_por_token)}"
    )

    dentro = sum(
        1 for largo in longitudes if 300 <= largo / caracteres_por_token <= 500
    )
    print(
        f"Dentro del objetivo de 300–500 tokens: {dentro}/{len(fragmentos)} "
        f"({100 * dentro / len(fragmentos):.0f} %)"
    )

    for indice in range(min(muestra, len(fragmentos))):
        pieza = fragmentos[indice]
        print(f"\n--- fragmento {indice} ({len(pieza)} car.) ---")
        print(pieza)


async def _medir_tokens(fragmentos: list[str], caracteres_por_token: float) -> None:
    """Cuenta los tokens reales de **todos** los fragmentos.

    Se miden todos y no una muestra porque muestrear diez daba ratios
    entre 4.54 y 4.78 según cuáles tocaran, y esa oscilación es del mismo
    orden que la corrección que se pretende comprobar. Son ~70 llamadas a
    `count_tokens`, que es barato y se ejecuta a mano.

    Es una comprobación, no una dependencia del troceo, pero es la que
    permite declarar en el documento de grado el tamaño real de los
    fragmentos en lugar del estimado, y la que desbloquea `ratio_medida` en
    el catálogo.
    """
    from app.core.gemini import MODELO_EMBEDDING, obtener_cliente

    cliente = obtener_cliente()
    tokens: list[int] = []

    for pieza in fragmentos:
        try:
            respuesta = await cliente.aio.models.count_tokens(
                model=MODELO_EMBEDDING, contents=pieza
            )
        except Exception as error:  # noqa: BLE001
            print(f"\ncount_tokens no disponible para el modelo: {error}")
            return
        tokens.append(respuesta.total_tokens)

    caracteres = sum(len(pieza) for pieza in fragmentos)
    dentro = sum(1 for cuenta in tokens if 300 <= cuenta <= 500)

    print(
        f"\nTokens REALES sobre los {len(tokens)} fragmentos:  "
        f"min={min(tokens)}  mediana={int(statistics.median(tokens))}  "
        f"max={max(tokens)}"
    )
    print(
        f"Dentro de 300–500 tokens reales: {dentro}/{len(tokens)} "
        f"({100 * dentro / len(tokens):.0f} %)"
    )
    print(
        f"Ratio media del corpus: {caracteres / sum(tokens):.2f} car./token "
        f"(la usada para trocear es {caracteres_por_token})"
    )

    # La media no es lo que hay que poner en el catálogo. Se dimensiona por
    # el extremo denso, que es lo que mete el máximo dentro del intervalo
    # (ADR-0009, decisión 4).
    ratios = sorted(len(p) / t for p, t in zip(fragmentos, tokens))
    percentil_10 = ratios[max(0, int(0.10 * len(ratios)) - 1)]
    print(
        f"Extremo denso (percentil 10): {percentil_10:.2f} car./token "
        "— es el valor que se lleva al catálogo."
    )


# =========================================================================
# Programa
# =========================================================================


# =========================================================================
# Casi duplicados entre fuentes
# =========================================================================
#
# La decisión 5 del ADR-0009 previó los duplicados **dentro** de una
# fuente: reingerir añadiendo duplicaría el corpus y los duplicados
# coparían el top-k con el mismo texto. Con una sola fuente ahí se acababa
# el problema.
#
# Con seis no. La cartilla de 2022 comparte el 22 % de su texto, palabra
# por palabra, con el documento ya ingerido —medido el 15/08/2026 sobre
# secuencias de ocho palabras—: no son dos ediciones de la misma obra, pero
# hay pasajes que sí están repetidos. En una consulta que caiga sobre uno
# de ellos, el top-k=4 puede gastar dos de sus cuatro puestos en decir lo
# mismo dos veces, firmado por dos fuentes distintas.
#
# La comprobación es **textual y no vectorial**, a propósito. Lo que
# interesa aquí es si el pasaje está literalmente repetido, y para eso la
# coincidencia de palabras es más precisa que la similitud coseno: dos
# fragmentos distintos sobre el mismo tema pueden puntuar muy alto en
# coseno sin ser el mismo texto, y confundirlos llevaría a descartar
# material legítimo. Además no gasta embeddings.

# Ocho palabras seguidas no coinciden por azar entre dos textos del mismo
# dominio. Es la misma ventana con la que se midió el solape entre los dos
# documentos.
VENTANA_SOLAPE = 8

# A partir de aquí el fragmento se considera repetido: más de la mitad de
# sus secuencias ya están en el corpus.
SOLAPE_PARA_DUPLICADO = 0.50

_SIN_LETRAS = re.compile(r"[^a-z0-9ñ ]+")


def _huellas(texto: str) -> set[tuple[str, ...]]:
    """Secuencias de palabras del texto, sin tildes ni puntuación."""
    plano = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(caracter) != "Mn"
    )
    palabras = _SIN_LETRAS.sub(" ", plano).split()

    return {
        tuple(palabras[indice : indice + VENTANA_SOLAPE])
        for indice in range(len(palabras) - VENTANA_SOLAPE + 1)
    }


async def _comprobar_duplicados(
    fuente: FuenteDocumento, fragmentos: list[str]
) -> list[str]:
    """Compara los fragmentos nuevos contra el corpus ya ingerido.

    Devuelve los que hay que conservar: todos, salvo que la fuente pida
    `descartar_repetidos`, en cuyo caso se van los que superen el umbral.
    """
    await abrir_pool()
    try:
        fila = await obtener_fuente_por_url(fuente.url)
        existentes = await listar_contenidos_oficiales(
            excluir_fuente_id=fila.id if fila else None
        )
    finally:
        await cerrar_pool()

    if not existentes:
        print("\nNo hay otras fuentes en la base: nada contra lo que comparar.")
        return fragmentos

    print(
        f"\nComprobando {len(fragmentos)} fragmentos nuevos contra "
        f"{len(existentes)} ya ingeridos..."
    )

    # El corpus entero como un solo conjunto: lo que importa es si el
    # pasaje ya está, no en cuál de los documentos anteriores.
    corpus: set[tuple[str, ...]] = set()
    for _, contenido in existentes:
        corpus |= _huellas(contenido)

    solapes: list[tuple[float, int]] = []
    for indice, pieza in enumerate(fragmentos):
        huellas = _huellas(pieza)
        solapes.append(
            (len(huellas & corpus) / len(huellas) if huellas else 0.0, indice)
        )

    ordenados = sorted(solapes, reverse=True)
    repetidos = {
        indice for solape, indice in solapes if solape >= SOLAPE_PARA_DUPLICADO
    }

    medio = sum(solape for solape, _ in solapes) / len(solapes)
    print(f"Solape medio con el corpus: {100 * medio:.1f} %")
    print(
        f"Fragmentos con más del {100 * SOLAPE_PARA_DUPLICADO:.0f} % repetido: "
        f"{len(repetidos)}/{len(solapes)}"
    )

    for solape, indice in ordenados[:5]:
        print(f"\n  fragmento {indice}: {100 * solape:.0f} % ya está en el corpus")
        print(f"    {fragmentos[indice][:220]}...")

    if not repetidos:
        return fragmentos

    if not fuente.descartar_repetidos:
        print(
            f"\nESOS {len(repetidos)} FRAGMENTOS COMPETIRÁN CON EL CORPUS EN EL "
            "TOP-K.\nLa fuente no pide descartarlos (descartar_repetidos=False), "
            "así que entran.\nQueda medido y dicho."
        )
        return fragmentos

    conservados = [
        pieza for indice, pieza in enumerate(fragmentos) if indice not in repetidos
    ]
    print(
        f"\nDescartados {len(repetidos)} fragmentos por estar ya en el corpus "
        f"(descartar_repetidos=True).\nSe ingieren {len(conservados)} de "
        f"{len(fragmentos)}."
    )

    return conservados


async def _ingerir(
    fuente: FuenteDocumento, fragmentos: list[str], reingerir: bool
) -> None:
    """Escribe la fuente y sus fragmentos vectorizados en Supabase."""
    await abrir_pool()
    try:
        fila = await obtener_fuente_por_url(fuente.url)

        if fila is not None:
            existentes = await contar_fragmentos_oficiales(fila.id)
            if not reingerir:
                raise SystemExit(
                    f"Esa fuente ya está ingerida (fuente_id={fila.id}, "
                    f"{existentes} fragmentos). Repetir la ingesta "
                    "duplicaría el corpus y los duplicados coparían el "
                    "top-k con el mismo texto. Use --reingerir para "
                    "rehacerla."
                )
            print(
                f"Fuente ya registrada (fuente_id={fila.id}); se "
                f"reemplazan sus {existentes} fragmentos."
            )
        else:
            fila = await crear_fuente(fuente.entidad, fuente.titulo, fuente.url)
            print(f"Fuente registrada: fuente_id={fila.id}")

        print(f"Vectorizando {len(fragmentos)} fragmentos...")
        vectores: list[list[float]] = []
        for inicio in range(0, len(fragmentos), LOTE_VECTORIZACION):
            lote = fragmentos[inicio : inicio + LOTE_VECTORIZACION]
            vectores.extend(await vectorizar_documentos(lote))
            print(f"  {len(vectores)}/{len(fragmentos)}")

        escritos = await reemplazar_fragmentos_oficiales(
            fila.id,
            [
                (orden, contenido, vector)
                for orden, (contenido, vector) in enumerate(
                    zip(fragmentos, vectores)
                )
            ],
        )
        print(f"\nEscritos {escritos} fragmentos para fuente_id={fila.id}")
    finally:
        await cerrar_pool()


async def main() -> None:
    analizador = argparse.ArgumentParser(
        description="Ingesta de una fuente oficial al RAG (CU2)."
    )
    analizador.add_argument(
        "--fuente", help="Clave del documento en scripts/catalogo_fuentes.py."
    )
    analizador.add_argument(
        "--listar", action="store_true", help="Muestra el catálogo y termina."
    )
    analizador.add_argument(
        "--pdf", type=Path, help="Ruta local al PDF. Si falta, se descarga."
    )
    analizador.add_argument(
        "--desde-pagina",
        type=int,
        help="Primera página con contenido. Por defecto, la del catálogo.",
    )
    analizador.add_argument(
        "--hasta-pagina",
        type=int,
        help="Última página con contenido. Por defecto, la del catálogo.",
    )
    analizador.add_argument(
        "--simular",
        action="store_true",
        help="Trocea e informa, sin vectorizar ni escribir en la base.",
    )
    analizador.add_argument(
        "--reingerir",
        action="store_true",
        help="Reemplaza los fragmentos de una fuente ya ingerida.",
    )
    analizador.add_argument(
        "--muestra", type=int, default=3, help="Fragmentos a imprimir."
    )
    analizador.add_argument(
        "--medir-tokens",
        action="store_true",
        help="Contrasta la ratio caracteres/token contra la API.",
    )
    analizador.add_argument(
        "--comprobar-duplicados",
        action="store_true",
        help=(
            "Compara los fragmentos contra el corpus ya ingerido. Se hace "
            "sola antes de toda ingesta real."
        ),
    )
    analizador.add_argument(
        "--detectar-folio",
        action="store_true",
        help="Calcula el desfase del folio y termina, sin trocear.",
    )
    analizador.add_argument(
        "--ratio",
        type=float,
        help=(
            "Ratio caracteres/token solo para esta corrida, para probar "
            "valores antes de fijarlos. No habilita la ingesta real: eso "
            "exige escribirla en el catálogo."
        ),
    )
    argumentos = analizador.parse_args()

    if argumentos.listar:
        print("Fuentes declaradas:\n")
        print(describir())
        return

    if not argumentos.fuente:
        raise SystemExit(
            "Falta --fuente. Vea las disponibles con:\n"
            "    python -m scripts.ingesta_fuente --listar"
        )

    fuente = obtener(argumentos.fuente)

    try:
        from pypdf import PdfReader
    except ModuleNotFoundError:
        raise SystemExit(
            "Falta pypdf, que a propósito no está en requirements.txt para "
            "no desplegarlo en Railway. Instálelo con:\n"
            "    pip install -r requirements-scripts.txt"
        ) from None

    print(f"Fuente: {fuente.clave} — {fuente.titulo}")
    if fuente.nota:
        print(f"Nota del catálogo: {fuente.nota}")

    ruta = _obtener_pdf(fuente, argumentos.pdf)
    lector = PdfReader(str(ruta))
    total = len(lector.pages)

    primera = argumentos.desde_pagina or fuente.pagina_inicial
    ultima = min(argumentos.hasta_pagina or fuente.pagina_final, total)
    print(f"Páginas: {total}. Se ingieren de la {primera} a la {ultima}.")

    print(f"Modo de extracción: {fuente.modo_extraccion}")

    excluidas = {
        numero
        for desde, hasta in fuente.paginas_excluidas
        for numero in range(desde, hasta + 1)
    }
    if excluidas:
        print(
            f"Páginas excluidas del medio: {len(excluidas)} "
            f"{list(fuente.paginas_excluidas)}"
        )

    crudas: list[tuple[int, str]] = []
    for numero in range(primera, ultima + 1):
        if numero in excluidas:
            continue
        bruto = (
            lector.pages[numero - 1].extract_text(
                extraction_mode=fuente.modo_extraccion
            )
            or ""
        )
        for malo, bueno in fuente.sustituciones:
            bruto = bruto.replace(malo, bueno)
        crudas.append((numero, _normalizar_texto(bruto)))

    if argumentos.detectar_folio:
        _detectar_desfase_folio(crudas)
        return

    paginas: list[str] = []
    saltadas = 0
    partidas = 0

    for numero, texto in crudas:
        limpio = _quitar_numero_pagina(
            texto, numero - fuente.desfase_folio, fuente.folio_desfase_variable
        )

        if not limpio.strip():
            continue

        # Se decide con el texto ya sin folio y antes de partir columnas: la
        # marca está en el primer renglón de la página.
        primeros = [linea.strip() for linea in limpio.split("\n") if linea.strip()]
        if primeros and primeros[0].startswith(fuente.saltar_pagina_si_empieza_por or ()):
            saltadas += 1
            continue

        if fuente.separar_columnas:
            limpio, se_partio = _separar_columnas(limpio)
            partidas += se_partio

        paginas.append(limpio)

    print(f"Páginas con texto: {len(paginas)}")
    if saltadas:
        print(
            f"Páginas saltadas por empezar con "
            f"{list(fuente.saltar_pagina_si_empieza_por)}: {saltadas}"
        )
    if partidas:
        print(f"Páginas leídas por columnas: {partidas}")

    plantilla = _detectar_plantilla(paginas, fuente.paginas_para_plantilla)
    if plantilla:
        print(
            f"Renglones descartados por repetirse en {fuente.paginas_para_plantilla} "
            f"páginas o más: {len(plantilla)}"
        )
        for linea in sorted(plantilla):
            print(f"    {linea[:80]}")

    parrafos = _reconstruir_parrafos(paginas, plantilla)
    print(f"Párrafos reconstruidos: {len(parrafos)}")

    if fuente.limpiar_tablas_especies:
        parrafos, tablas = _limpiar_tablas(parrafos)
        if tablas:
            print(
                f"Tablas de especies saneadas: {tablas} "
                "(se retiran las columnas Exótica/Nativa, ilegibles tras la "
                "extracción)"
            )

    ratio = argumentos.ratio or fuente.caracteres_por_token
    if argumentos.ratio:
        print(f"Ratio de esta corrida: {ratio} (el catálogo dice {fuente.caracteres_por_token})")

    inicios = set()
    if fuente.marcador_de_ficha:
        inicios = _inicios_de_ficha(
            parrafos, fuente.marcador_de_ficha, fuente.rotulos_de_ficha
        )
        print(f"Fichas detectadas, y por las que se corta fragmento: {len(inicios)}")

    fragmentos = _trocear(parrafos, ratio, inicios)
    _informar(fragmentos, argumentos.muestra, ratio)

    if argumentos.medir_tokens:
        await _medir_tokens(fragmentos, ratio)

    if argumentos.comprobar_duplicados:
        fragmentos = await _comprobar_duplicados(fuente, fragmentos)

    if argumentos.simular:
        print("\n--simular: no se ha vectorizado ni escrito nada.")
        return

    # La URL es la clave por la que la ingesta reconoce lo ya ingerido, y
    # sin ella no hay forma de rehacer el corpus en la Fase 8: los PDF no se
    # versionan (ADR-0009). Se comprueba aquí porque el fallo sería
    # silencioso y destructivo: con dos fuentes marcadas `PENDIENTE`, la
    # segunda encontraría la fila de la primera y se creería ya ingerida.
    if not fuente.url.startswith("http"):
        raise SystemExit(
            f"\nLa fuente {fuente.clave!r} no tiene URL ({fuente.url!r}).\n"
            "Es la clave que identifica el documento y lo que permite "
            "volver a descargarlo:\nsin ella la ingesta no es reproducible. "
            "Escríbala en el catálogo."
        )

    # La ratio calibrada contra otro documento no vale: la nomenclatura
    # botánica tokeniza más denso que la prosa y los fragmentos se saldrían
    # del intervalo de la Fase 4 sin que nada lo indicara (ADR-0009,
    # decisión 4). Se bloquea aquí y no antes para que simular y medir
    # sigan funcionando, que es justo lo que hay que hacer para desbloquearlo.
    if not fuente.ratio_medida:
        raise SystemExit(
            f"\nLa fuente {fuente.clave!r} tiene ratio_medida=False: su "
            f"valor de {fuente.caracteres_por_token} car./token está "
            "heredado de otro documento y no se ha comprobado contra este.\n"
            "Mídalo y escríbalo en el catálogo antes de ingerir:\n"
            f"    python -m scripts.ingesta_fuente --fuente {fuente.clave} "
            "--simular --medir-tokens"
        )

    # Antes de escribir, siempre: mirar contra qué se está añadiendo. Es el
    # mismo criterio por el que existe `--simular`, llevado al caso que el
    # ADR-0009 no contemplaba porque solo había una fuente.
    if not argumentos.comprobar_duplicados:
        fragmentos = await _comprobar_duplicados(fuente, fragmentos)

    await _ingerir(fuente, fragmentos, argumentos.reingerir)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
