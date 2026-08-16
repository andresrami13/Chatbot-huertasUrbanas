"""Catálogo de las fuentes oficiales que alimentan el RAG del CU2.

Cada documento se declara aquí con los parámetros que **le son propios**, y
`scripts/ingesta_fuente.py` los recibe en lugar de tenerlos como constantes
de módulo. Hasta la Fase 6 había una sola fuente y sus parámetros vivían
dentro del script; con seis documentos eso ya no se sostiene.

## Por qué un catálogo y no un script por documento

Los parámetros de abajo no son configuración de gusto: son **mediciones**.
El rango de páginas se obtuvo mirando dónde acaba la presentación
institucional y dónde empieza la bibliografía; el desfase del folio,
contando en cuántas páginas el número impreso coincide con el índice del
PDF; la ratio de caracteres por token, llamando a `count_tokens`.

Tenerlos versionados en un archivo es lo que hace **reproducible** la
ingesta, que es la exigencia del ADR-0009: los PDF no se versionan
—`fuentes/` está en el `.gitignore` porque son publicaciones de terceros y
el repositorio es público—, así que lo único que permite rehacer el mismo
corpus en la Fase 8 es la URL más estos números.

## La ratio no se hereda

`caracteres_por_token` está calibrada contra un documento concreto y no
transfiere a otro: la nomenclatura botánica tokeniza mucho más denso que la
prosa. Por eso existe `ratio_medida`. Mientras esté en `False`, la ingesta
real se niega a correr y solo se permite simular y medir. Es la decisión 4
del ADR-0009 convertida en algo que el programa comprueba, en vez de una
advertencia en un comentario que nadie relee.
"""

from dataclasses import dataclass
from pathlib import Path

CARPETA_FUENTES = Path("fuentes")


@dataclass(frozen=True)
class FuenteDocumento:
    """Un documento oficial y todo lo que hace falta para ingerirlo."""

    clave: str
    entidad: str
    titulo: str
    url: str
    archivo: str

    # Primera y última página con contenido aprovechable, contando desde 1
    # y ambas inclusive. Fuera quedan portada, créditos, tabla de
    # contenido, presentación institucional y bibliografía: una lista de
    # URL entraría al nivel más alto de la jerarquía de fuentes
    # (CLAUDE.md §6) sin responder nada.
    pagina_inicial: int
    pagina_final: int

    # Caracteres por token, medidos con `--medir-tokens` sobre el corpus
    # entero del documento. Se dimensiona por el extremo denso observado,
    # no por la media (ADR-0009, decisión 4).
    caracteres_por_token: float

    # Cuánto hay que restarle al índice de página del PDF para obtener el
    # folio impreso. Si el PDF trae tres hojas de cortesía sin numerar, la
    # página 20 del archivo lleva impreso un 17 y el desfase es 3. Importa
    # porque el folio se retira comparándolo con el número esperado: con el
    # desfase mal puesto no se retira nada y el número acaba incrustado a
    # mitad del texto vectorizado.
    desfase_folio: int = 0

    # Un renglón repetido en esta cantidad de páginas se descarta por ser
    # maquetación. El valor por defecto sirve para prosa corrida; los
    # documentos organizados en fichas necesitan más, porque en ellos un
    # nombre de familia botánica se repite legítimamente en muchas.
    paginas_para_plantilla: int = 10

    # Retira de las tablas de especies las columnas Exótica/Nativa, que la
    # extracción deja reducidas a una `x` de la que ya no se sabe a cuál
    # pertenece (ADR-0009, decisión 3). Solo aplica a los documentos que
    # traen esas tablas.
    limpiar_tablas_especies: bool = False

    # Cómo lee el texto `pypdf`. `"plain"` devuelve los renglones en el
    # orden del flujo interno del PDF, que en un documento de prosa
    # corrida coincide con el orden de lectura. En uno maquetado por cajas
    # **no coincide**: en Sembrando Biodiversidad el nombre de la especie y
    # los rótulos de sección salían en mitad del texto, detrás del
    # contenido que encabezan, y los rótulos de las cajas —TALLO, HOJAS,
    # SEMILLAS— aparecían amontonados y separados de lo que rotulan.
    #
    # `"layout"` reconstruye la posición en la página y devuelve el orden
    # de lectura correcto. No se pone por defecto porque cambiaría la
    # extracción del documento ya ingerido, cuyo corpus sostiene la
    # calibración del umbral.
    modo_extraccion: str = "plain"

    # Lee las páginas de dos columnas columna por columna, en vez de
    # renglón por renglón. Solo tiene sentido con `modo_extraccion`
    # `"layout"`, que es el único que conserva la posición horizontal.
    #
    # Sin esto, una página de dos columnas entreteje dos textos ajenos
    # frase a frase: «Condiciones o requerimientos especiales: Semillas la
    # especie requiere suelos con un pH entre Reportadas: se usa una dosis
    # de semilla...». Son 82 de las 260 páginas de Sembrando Biodiversidad,
    # un tercio del documento.
    separar_columnas: bool = False

    # Páginas enteras que se descartan por cómo empiezan. Pensado para el
    # material que se recorta por la cabecera y la cola en un libro lineal
    # pero que en uno por fichas aparece repartido por el medio: Sembrando
    # Biodiversidad lleva una bibliografía propia por especie, 18 en total,
    # cada una en su página. Una lista de autores y URLs no responde nada y
    # ocuparía puestos del top-k.
    saltar_pagina_si_empieza_por: tuple[str, ...] = ()

    # `True` cuando `caracteres_por_token` se midió contra este documento.
    # Con `False`, la ingesta real se bloquea.
    ratio_medida: bool = False

    nota: str = ""

    @property
    def ruta(self) -> Path:
        return CARPETA_FUENTES / self.archivo


# =========================================================================
# Los documentos
# =========================================================================

CATALOGO: dict[str, FuenteDocumento] = {
    # --- Ya ingerida el 04/08/2026: 81 fragmentos ------------------------
    #
    # fuente_id 5afa2267-bcc6-4773-b5a2-c87593fa32cf. Sus parámetros son
    # los que estaban en el script y los conserva tal cual: reingerirla con
    # otros números cambiaría el corpus contra el que se calibró el umbral
    # de 0.68 (ADR-0010).
    "jbb_pasos_basicos": FuenteDocumento(
        clave="jbb_pasos_basicos",
        entidad="Jardín Botánico de Bogotá José Celestino Mutis",
        titulo=(
            "Pasos básicos para establecer y manejar tu huerta. "
            "Una guía práctica para agricultores urbanos"
        ),
        url=(
            "https://jbb.gov.co/documentos/cientifica/publicaciones/"
            "Pasos_basicos_para_establecer_y_manejar_tu_huerta.pdf"
        ),
        archivo="jbb_pasos_basicos.pdf",
        # Del 1 al 7 van portada, créditos, ISBN y tabla de contenido; del
        # 8 al 10, presentación institucional y agradecimientos; la 11 está
        # en blanco. De la 122 a la 126 van las referencias, la 127 el
        # colofón y la 128 la contracubierta. Sí se conserva el glosario de
        # las páginas 120 y 121.
        pagina_inicial=12,
        pagina_final=121,
        caracteres_por_token=3.9,
        limpiar_tablas_especies=True,
        ratio_medida=True,
        nota="Primera fuente ingerida. 81 fragmentos, 90 % dentro de 300–500 tokens reales.",
    ),
    # --- Los dos primeros de la ampliación de la Fase 7 -------------------
    "jbb_practicas_2022": FuenteDocumento(
        clave="jbb_practicas_2022",
        entidad="Jardín Botánico de Bogotá José Celestino Mutis",
        titulo=(
            "Prácticas para establecer y manejar tu huerta. Una guía para "
            "agricultoras y agricultores urbanos y periurbanos"
        ),
        # Alojado por la OEI, que coedita. Comprobado el 15/08/2026: los
        # bytes de esta URL son idénticos al PDF local.
        url=(
            "https://oei.int/wp-content/uploads/2023/03/"
            "cartilla-bogota-es-mi-huertav15-ber-web-2.pdf"
        ),
        archivo="cartilla-bogota-es-mi-huertav15-ber-web-2 (1).pdf",
        # 1 portada, 2 y 3 en blanco, 4 créditos, 5 citación e ISBN, 6 y 7
        # tabla de contenido, 8 y 9 presentación, 10 agradecimientos. La 11
        # abre la introducción, que es el mismo criterio con el que se
        # incluyó la página 12 del documento anterior. Al final, de la 114
        # a la 117 van referencias y bibliografía relacionada, y de la 118 a
        # la 120 páginas en blanco.
        pagina_inicial=11,
        pagina_final=113,
        # Medida el 15/08/2026 sobre los 89 fragmentos: media 4.60, extremo
        # denso 4.18. Su prosa tokeniza MENOS denso que la del documento
        # anterior, así que con el 3.9 heredado los fragmentos salían
        # cortos: mediana de 386 tokens reales y mínimo de 169.
        caracteres_por_token=4.18,
        ratio_medida=True,
        nota=(
            "Comparte el 22 % de su texto, palabra por palabra, con "
            "jbb_pasos_basicos (medido el 15/08/2026 sobre secuencias de 8 "
            "palabras). No es otra edición —el 78 % es material nuevo— pero "
            "hay que vigilar que el top-k no se llene con el mismo pasaje "
            "firmado por dos fuentes."
        ),
    ),
    "jbb_sembrando_2023": FuenteDocumento(
        clave="jbb_sembrando_2023",
        entidad="Jardín Botánico de Bogotá José Celestino Mutis",
        titulo=(
            "Sembrando biodiversidad. Protocolos para la propagación, "
            "cultivo y aprovechamiento de especies para huertas urbanas "
            "en Bogotá D.C. Volumen 1"
        ),
        url=(
            "https://jbb.gov.co/documentos/publicaciones/"
            "Sembrando_Biodivesridad_Vol1-2023.pdf"
        ),
        archivo="Sembrando_Biodivesridad_Vol1-2023.pdf",
        # 1 portada, 2 créditos, 3 tabla de contenido, 4 presentación, 5
        # agradecimientos, 6 y 7 la guía de uso, que explica cómo está
        # organizado el libro y no responde nada sobre una huerta. La 8 abre
        # la primera ficha de especie. De la 268 a la 270 van las
        # referencias.
        pagina_inicial=8,
        pagina_final=267,
        # Medida el 15/08/2026 sobre los 187 fragmentos: media 3.76,
        # extremo denso 3.40. Es el caso que anticipaba el ADR-0009: va
        # cargado de nomenclatura botánica y tokeniza MÁS denso, así que
        # con el 3.9 heredado el máximo real llegaba a 620 tokens, por
        # encima del techo de 500 de la Fase 4, y solo el 60 % de los
        # fragmentos caía dentro del intervalo.
        caracteres_por_token=3.40,
        # No es prosa corrida: son fichas de especie con la misma plantilla
        # de ocho secciones, así que los rótulos se repiten legítimamente
        # en decenas de páginas.
        paginas_para_plantilla=40,
        # Maquetado en cajas: sin esto, el nombre de la especie sale detrás
        # de su propio contenido.
        modo_extraccion="layout",
        separar_columnas=True,
        # Las 18 bibliografías de ficha, una por especie. Comprobado el
        # 15/08/2026: ocupan la página entera y empiezan por ese renglón.
        saltar_pagina_si_empieza_por=("Bibliografía",),
        ratio_medida=True,
        nota=(
            "El más trabajado de los tres. 18 bibliografías de ficha fuera y "
            "95 páginas leídas por columnas. Queda un residuo conocido: en "
            "las páginas de descripción botánica los rótulos del margen "
            "izquierdo (TALLO, HOJAS, SEMILLAS) se inyectan dentro de la "
            "frase, porque ahí no hay dos columnas de texto sino una "
            "etiqueta al margen. Cinco páginas avisan además de texto "
            "rotado que pypdf no extrae."
        ),
    ),
}


# =========================================================================
# Pendientes
# =========================================================================
#
# Los tres que faltan de la carpeta `fuentes/`, con lo que le falta a cada
# uno para poder entrar. No se declaran a medias a propósito: una entrada
# en el catálogo es ejecutable, y media entrada invita a ingerir con
# parámetros que nadie midió.
#
# - Cartilla_agricultura_urbana_final.pdf (2011, manejo integrado de la
#   fertilización, las plagas y las enfermedades). **Falta la URL.** La
#   candidata `cartilla_tecnica_agricultura_urbana.pdf` se descargó y se
#   descartó el 15/08/2026: es otro documento, de 62 páginas y de la
#   administración Garzón. Sin URL no se puede registrar la fuente, porque
#   es la clave por la que la ingesta reconoce lo ya ingerido. Trae además
#   cabecera y pie repetidos en 23 y 25 páginas, y el folio desfasado en 4.
#
# - catalog-plantas-usadas-agricultura-urb.pdf. Necesita subir
#   `paginas_para_plantilla` —`Compositae` sale en 12 páginas y `Lamiaceae`
#   en 11, y son contenido, no maquetación— y tiene el folio desfasado en
#   10. Su capa de texto arrastra `KJBNVBJNBHJBHJ` en 110 de sus 127
#   páginas.
#
# - Cartilla_1_Agricultura_urbana2010.pdf. La más sencilla de las tres:
#   folio sin desfase y sin plantilla repetida. Sus páginas 52 a 54 son
#   divulgación institucional —programa de radio, curso virtual— y van
#   fuera.
#
# Fuera de alcance por decisión del 15/08/2026:
# `Anexo_9_del_Protocolo_Listado_de_Especies.pdf` son 63 páginas de lista
# numerada de nombre común y nombre científico, sin una línea de
# orientación. Como fuente oficial competiría en el top-k contra los
# fragmentos que sí explican algo.


def obtener(clave: str) -> FuenteDocumento:
    """Devuelve la fuente del catálogo o falla diciendo cuáles hay."""
    if clave not in CATALOGO:
        disponibles = "\n".join(f"    {c}" for c in CATALOGO)
        raise SystemExit(
            f"No hay ninguna fuente con la clave {clave!r}.\n"
            f"Las declaradas son:\n{disponibles}"
        )
    return CATALOGO[clave]


def describir() -> str:
    """Listado legible del catálogo, para `--listar`."""
    lineas = []
    for fuente in CATALOGO.values():
        estado = "ratio medida" if fuente.ratio_medida else "RATIO SIN MEDIR"
        lineas.append(
            f"  {fuente.clave}\n"
            f"      {fuente.titulo}\n"
            f"      páginas {fuente.pagina_inicial}–{fuente.pagina_final} | "
            f"{fuente.caracteres_por_token} car./token ({estado})"
        )
    return "\n".join(lineas)
