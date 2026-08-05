"""Ingesta de una fuente oficial a la colección vectorial (Fase 6, CU2).

**No forma parte del servicio.** Se ejecuta a mano, desde la raíz del
repositorio, y escribe en Supabase:

    python -m scripts.ingesta_fuente --simular      # no escribe ni vectoriza
    python -m scripts.ingesta_fuente                # ingesta real
    python -m scripts.ingesta_fuente --reingerir    # rehace una ya ingerida

Vive en `scripts/` y no en `app/` por una razón concreta: así `pypdf` se
queda en `requirements-scripts.txt` y no entra en el `requirements.txt` que
se despliega en Railway. El servicio no lee PDF nunca; solo consulta lo que
esto dejó escrito.

El acceso a la base lo hace `app/services/repositorio.py`, que sigue siendo
el punto único de acceso a Supabase (Fase 3, Tabla 2). Aquí solo vive lo
propio del documento: extraer, limpiar, trocear.

## Por qué la limpieza es la mitad del trabajo

El PDF está maquetado en InDesign, y lo que `extract_text` devuelve son
renglones de la página, no frases. Sin reconstruir los párrafos, los
fragmentos quedarían cortados por la maquetación y no por el sentido, que
es justo lo que arruina una recuperación. Comprobado sobre el documento del
Jardín Botánico (128 páginas):

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
"""

import argparse
import asyncio
import re
import statistics
import sys
import unicodedata
from pathlib import Path

import httpx

from app.core.basedatos import abrir_pool, cerrar_pool
from app.services.embeddings import vectorizar_documentos
from app.services.repositorio import (
    contar_fragmentos_oficiales,
    crear_fuente,
    obtener_fuente_por_url,
    reemplazar_fragmentos_oficiales,
)

# --- La fuente, verificada el 30/07/2026 (ESTADO.md) ---------------------
ENTIDAD = "Jardín Botánico de Bogotá José Celestino Mutis"
TITULO = (
    "Pasos básicos para establecer y manejar tu huerta. "
    "Una guía práctica para agricultores urbanos"
)
URL = (
    "https://jbb.gov.co/documentos/cientifica/publicaciones/"
    "Pasos_basicos_para_establecer_y_manejar_tu_huerta.pdf"
)

RUTA_POR_DEFECTO = Path("fuentes/jbb_pasos_basicos.pdf")

# Primera página con contenido aprovechable, en numeración de 1.
#
# ESTADO.md decía "las ~10 primeras"; contadas una a una son 11. Del 1 al 7
# van portada, créditos, ISBN y tabla de contenido; del 8 al 10, la
# presentación institucional y los agradecimientos, que son prosa de la
# entidad y no orientación agronómica. La página 11 está en blanco y en la
# 12 empieza la introducción.
PAGINA_INICIAL = 12

# Última página aprovechable, también en numeración de 1.
#
# ESTADO.md solo advertía de la cabecera, pero la cola hay que cortarla
# igual: de la 122 a la 126 van las referencias bibliográficas, la 127 es
# el colofón de imprenta y la 128 la contracubierta. Una lista de URL y el
# gramaje del papel no responden nada, y como fuente OFICIAL entrarían al
# nivel más alto de la jerarquía (CLAUDE.md §6).
#
# Se conserva en cambio el glosario de las páginas 120 y 121: define
# alelopatía, nivel freático o patógeno, que es justo el tipo de término
# que una usuaria puede preguntar.
PAGINA_FINAL = 121

# --- Troceo (CLAUDE.md §8: 300–500 tokens, solape de 50) -----------------
#
# El tamaño se mide en caracteres y no llamando al contador de tokens en
# cada corte: serían ~100 llamadas de red para gobernar un punto de corte.
# Pero la ratio no se supone, se **midió**.
#
# El valor NO es la ratio media del corpus, y la diferencia importa.
#
# Medida con `count_tokens` del propio `gemini-embedding-001` sobre los
# fragmentos completos, la media del documento es **4.49** car./token. Pero
# dimensionar con la media deja fuera de intervalo a la mitad del corpus:
# la ratio varía mucho de un fragmento a otro —los que cargan nomenclatura
# botánica ("Amaranthaceae", "Vasconcellea pubescens") tokenizan mucho más
# denso— y con 4.49 los fragmentos salían con mediana 482 y **máximo 625**
# tokens reales, por encima del techo de 500 de la Fase 4 (CLAUDE.md §8).
#
# Se dimensiona entonces por el extremo denso observado, no por la media,
# que es lo que hace que el máximo real caiga dentro del intervalo.
#
# Advertencia para la siguiente fuente que se ingiera: esta constante está
# calibrada contra ESTE documento. Con otro vocabulario hay que volver a
# medir con `--medir-tokens`, que cuenta los tokens reales de todos los
# fragmentos, antes de dar el troceo por bueno.
CARACTERES_POR_TOKEN = 3.9

CARACTERES_MAXIMO = int(500 * CARACTERES_POR_TOKEN)
CARACTERES_SOLAPE = int(50 * CARACTERES_POR_TOKEN)

# Tope duro por fragmento. `gemini-embedding-001` admite 2 048 tokens de
# entrada por texto y trunca en silencio lo que sobre: un fragmento
# demasiado largo se vectorizaría a medias sin dar error. Este límite deja
# margen de sobra sobre el objetivo de 500.
CARACTERES_TOPE = int(1500 * CARACTERES_POR_TOKEN)

# Textos por llamada de vectorización. La documentación de Gemini no
# publica un máximo de entradas por petición —solo el de 2 048 tokens por
# texto—, así que se lotea conservador en lugar de suponer un número.
LOTE_VECTORIZACION = 16

# Un renglón que aparece en esta cantidad de páginas distintas es plantilla
# de maquetación, no contenido. El umbral es alto a propósito: en este
# documento hay tablas de especies donde "Cebolla" o "Tomate" salen en 5
# páginas, y descartar contenido legítimo es peor que dejar pasar una línea
# de ruido. Lo que se descarte se imprime, para que nunca sea silencioso.
PAGINAS_PARA_PLANTILLA = 10

_VIÑETAS = "○⚫•▪-–—"
_FIN_DE_FRASE = ".:;?!»”)"

_PIE_DE_FIGURA = re.compile(r"^\s*(fig\.|figura|tabla|fuente:)\s", re.IGNORECASE)


# =========================================================================
# Obtención del PDF
# =========================================================================


def _obtener_pdf(ruta: Path | None) -> Path:
    """Devuelve la ruta al PDF, descargándolo si hace falta.

    Se cachea en `fuentes/`, que está fuera del control de versiones: es una
    publicación de terceros y el repositorio es público.
    """
    destino = ruta or RUTA_POR_DEFECTO

    if destino.exists():
        print(f"PDF local: {destino} ({destino.stat().st_size / 1e6:.1f} MB)")
        return destino

    if ruta is not None:
        raise SystemExit(f"No existe el archivo indicado: {ruta}")

    destino.parent.mkdir(parents=True, exist_ok=True)
    print(f"Descargando de {URL}")

    # La resolución DNS del equipo de desarrollo falla de forma
    # intermitente (ESTADO.md): se reintenta antes de dar el fallo por
    # bueno.
    ultimo_error: Exception | None = None
    for intento in (1, 2, 3):
        try:
            with httpx.stream(
                "GET", URL, timeout=120.0, follow_redirects=True
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


def _normalizar_espacios(texto: str) -> str:
    """Unifica los espacios raros de la maquetación.

    El PDF trae espacio duro (U+00A0) y espacio fino (U+2009), que no son
    separadores para `split()` y acabarían pegados dentro de las palabras.
    """
    texto = texto.replace("\xa0", " ").replace(" ", " ").replace("​", "")
    return unicodedata.normalize("NFC", texto)


def _quitar_numero_pagina(texto: str, numero: int) -> str:
    """Quita el folio de la página, en cualquiera de sus tres formas.

    Medidas sobre este documento, entre las páginas 12 y 121:

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
    folio = str(numero)

    if texto.startswith(folio):
        resto = texto[len(folio) :]
        if resto[:1].isspace() or resto[:1].isalpha():
            texto = resto.lstrip()

    # Algunas páginas lo repiten al final, también en renglón propio.
    lineas = texto.rstrip().split("\n")
    if lineas and lineas[-1].strip() == folio:
        texto = "\n".join(lineas[:-1])

    return texto


def _detectar_plantilla(paginas: list[str]) -> set[str]:
    """Renglones que se repiten en tantas páginas que no son contenido."""
    apariciones: dict[str, int] = {}

    for texto in paginas:
        vistos = {linea.strip() for linea in texto.split("\n") if linea.strip()}
        for linea in vistos:
            if not linea.isdigit():
                apariciones[linea] = apariciones.get(linea, 0) + 1

    return {
        linea
        for linea, veces in apariciones.items()
        if veces >= PAGINAS_PARA_PLANTILLA
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

    En este PDF no hay renglones en blanco entre párrafos, así que el corte
    se deduce: el renglón anterior cerró una frase y este empieza en
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
    cruza el salto de página tiene que quedar entero. La página 13 de este
    documento empieza a mitad de la frase que abrió la 12.
    """
    parrafos: list[str] = []
    actual = ""

    for texto in paginas:
        for cruda in texto.split("\n"):
            linea = " ".join(cruda.split())

            if not linea or linea in plantilla or _PIE_DE_FIGURA.match(linea):
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
# El documento trae cuatro tablas de especies aptas para el clima de
# Bogotá, con las columnas: nombre común, nombre científico, familia,
# exótica y nativa. Al extraer el PDF las columnas se colapsan en una fila
# corrida y las dos últimas quedan reducidas a una `x` suelta:
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


def _trocear(parrafos: list[str]) -> list[str]:
    """Agrupa párrafos en fragmentos de 300–500 tokens con solape.

    Se acumula por párrafos completos: el corte cae siempre en un límite de
    párrafo, nunca dentro de una frase.
    """
    unidades: list[str] = []
    for parrafo in parrafos:
        if len(parrafo) <= CARACTERES_MAXIMO:
            unidades.append(parrafo)
        else:
            unidades.extend(_partir_por_frases(parrafo, CARACTERES_MAXIMO))

    fragmentos: list[str] = []
    actual = ""

    for unidad in unidades:
        candidato = f"{actual} {unidad}".strip() if actual else unidad

        if actual and len(candidato) > CARACTERES_MAXIMO:
            fragmentos.append(actual)
            cola = _cola_para_solape(actual, CARACTERES_SOLAPE)
            actual = f"{cola} {unidad}".strip() if cola else unidad
        else:
            actual = candidato

    if actual:
        fragmentos.append(actual)

    # Red de seguridad frente al truncado silencioso del modelo.
    excedidos = [pieza for pieza in fragmentos if len(pieza) > CARACTERES_TOPE]
    if excedidos:
        raise RuntimeError(
            f"{len(excedidos)} fragmentos superan el tope de "
            f"{CARACTERES_TOPE} caracteres."
        )

    return fragmentos


# =========================================================================
# Informe
# =========================================================================


def _informar(fragmentos: list[str], muestra: int) -> None:
    """Imprime la distribución de tamaños y unos cuantos fragmentos."""
    longitudes = [len(pieza) for pieza in fragmentos]

    print(f"\nFragmentos: {len(fragmentos)}")
    print(
        f"Caracteres  min={min(longitudes)}  mediana="
        f"{int(statistics.median(longitudes))}  max={max(longitudes)}"
    )
    print(
        f"Tokens estimados (a {CARACTERES_POR_TOKEN} car./token)  "
        f"min={int(min(longitudes) / CARACTERES_POR_TOKEN)}  "
        f"mediana={int(statistics.median(longitudes) / CARACTERES_POR_TOKEN)}  "
        f"max={int(max(longitudes) / CARACTERES_POR_TOKEN)}"
    )

    dentro = sum(
        1 for largo in longitudes if 300 <= largo / CARACTERES_POR_TOKEN <= 500
    )
    print(
        f"Dentro del objetivo de 300–500 tokens: {dentro}/{len(fragmentos)} "
        f"({100 * dentro / len(fragmentos):.0f} %)"
    )

    for indice in range(min(muestra, len(fragmentos))):
        pieza = fragmentos[indice]
        print(f"\n--- fragmento {indice} ({len(pieza)} car.) ---")
        print(pieza)


async def _medir_tokens(fragmentos: list[str]) -> None:
    """Cuenta los tokens reales de **todos** los fragmentos.

    Se miden todos y no una muestra porque muestrear diez daba ratios
    entre 4.54 y 4.78 según cuáles tocaran, y esa oscilación es del mismo
    orden que la corrección que se pretende comprobar. Son ~70 llamadas a
    `count_tokens`, que es barato y se ejecuta a mano.

    Es una comprobación, no una dependencia del troceo, pero es la que
    permite declarar en el documento de grado el tamaño real de los
    fragmentos en lugar del estimado.
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
        f"Ratio real del corpus: {caracteres / sum(tokens):.2f} car./token "
        f"(la usada para trocear es {CARACTERES_POR_TOKEN})"
    )


# =========================================================================
# Programa
# =========================================================================


async def _ingerir(fragmentos: list[str], reingerir: bool) -> None:
    """Escribe la fuente y sus fragmentos vectorizados en Supabase."""
    await abrir_pool()
    try:
        fuente = await obtener_fuente_por_url(URL)

        if fuente is not None:
            existentes = await contar_fragmentos_oficiales(fuente.id)
            if not reingerir:
                raise SystemExit(
                    f"Esa fuente ya está ingerida (fuente_id={fuente.id}, "
                    f"{existentes} fragmentos). Repetir la ingesta "
                    "duplicaría el corpus y los duplicados coparían el "
                    "top-k con el mismo texto. Use --reingerir para "
                    "rehacerla."
                )
            print(
                f"Fuente ya registrada (fuente_id={fuente.id}); se "
                f"reemplazan sus {existentes} fragmentos."
            )
        else:
            fuente = await crear_fuente(ENTIDAD, TITULO, URL)
            print(f"Fuente registrada: fuente_id={fuente.id}")

        print(f"Vectorizando {len(fragmentos)} fragmentos...")
        vectores: list[list[float]] = []
        for inicio in range(0, len(fragmentos), LOTE_VECTORIZACION):
            lote = fragmentos[inicio : inicio + LOTE_VECTORIZACION]
            vectores.extend(await vectorizar_documentos(lote))
            print(f"  {len(vectores)}/{len(fragmentos)}")

        escritos = await reemplazar_fragmentos_oficiales(
            fuente.id,
            [
                (orden, contenido, vector)
                for orden, (contenido, vector) in enumerate(
                    zip(fragmentos, vectores)
                )
            ],
        )
        print(f"\nEscritos {escritos} fragmentos para fuente_id={fuente.id}")
    finally:
        await cerrar_pool()


async def main() -> None:
    analizador = argparse.ArgumentParser(
        description="Ingesta de una fuente oficial al RAG (CU2)."
    )
    analizador.add_argument(
        "--pdf", type=Path, help="Ruta local al PDF. Si falta, se descarga."
    )
    analizador.add_argument(
        "--desde-pagina",
        type=int,
        default=PAGINA_INICIAL,
        help=f"Primera página con contenido, contando desde 1 "
        f"(por defecto {PAGINA_INICIAL}).",
    )
    analizador.add_argument(
        "--hasta-pagina",
        type=int,
        default=PAGINA_FINAL,
        help=f"Última página con contenido, inclusive "
        f"(por defecto {PAGINA_FINAL}).",
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
    argumentos = analizador.parse_args()

    try:
        from pypdf import PdfReader
    except ModuleNotFoundError:
        raise SystemExit(
            "Falta pypdf, que a propósito no está en requirements.txt para "
            "no desplegarlo en Railway. Instálelo con:\n"
            "    pip install -r requirements-scripts.txt"
        ) from None

    ruta = _obtener_pdf(argumentos.pdf)
    lector = PdfReader(str(ruta))
    total = len(lector.pages)
    ultima = min(argumentos.hasta_pagina, total)
    print(
        f"Páginas: {total}. Se ingieren de la {argumentos.desde_pagina} "
        f"a la {ultima}."
    )

    paginas: list[str] = []
    for numero in range(argumentos.desde_pagina, ultima + 1):
        crudo = lector.pages[numero - 1].extract_text() or ""
        limpio = _quitar_numero_pagina(_normalizar_espacios(crudo), numero)
        if limpio.strip():
            paginas.append(limpio)

    print(f"Páginas con texto: {len(paginas)}")

    plantilla = _detectar_plantilla(paginas)
    if plantilla:
        print(f"Renglones descartados por repetirse en muchas páginas: {len(plantilla)}")
        for linea in sorted(plantilla):
            print(f"    {linea[:80]}")

    parrafos = _reconstruir_parrafos(paginas, plantilla)
    print(f"Párrafos reconstruidos: {len(parrafos)}")

    parrafos, tablas = _limpiar_tablas(parrafos)
    if tablas:
        print(
            f"Tablas de especies saneadas: {tablas} "
            "(se retiran las columnas Exótica/Nativa, ilegibles tras la "
            "extracción)"
        )

    fragmentos = _trocear(parrafos)
    _informar(fragmentos, argumentos.muestra)

    if argumentos.medir_tokens:
        await _medir_tokens(fragmentos)

    if argumentos.simular:
        print("\n--simular: no se ha vectorizado ni escrito nada.")
        return

    await _ingerir(fragmentos, argumentos.reingerir)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
