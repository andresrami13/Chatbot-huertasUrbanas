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

    # Cuando el desfase **no es constante**, porque el PDF trae páginas sin
    # numerar intercaladas y cada una corre la cuenta. En la cartilla de
    # 2011 el desfase crece de 2 a 5 a lo largo del documento, por las
    # páginas de imagen 13, 18 y 27: ningún número único sirve.
    #
    # Con esto, se retira cualquier renglón que sea **solo** un número, con
    # o sin adornos, sin compararlo con el folio esperado. Es más agresivo y
    # por eso no es el comportamiento por defecto: un renglón que contenga
    # únicamente una cifra podría ser una celda de tabla. Pero el caso
    # peligroso que el modo normal evita —quitarle el número a un texto que
    # empieza legítimamente por una cifra— aquí no se da, porque se exige
    # que el renglón entero no tenga nada más.
    folio_desfase_variable: bool = False

    # Sustituciones de carácter a aplicar nada más extraer, para PDF cuya
    # capa de texto viene con la codificación rota.
    #
    # El Protocolo de Espacio Público sale de Ghostscript con un mapa de
    # fuente equivocado: unos 600 caracteres mal en 30 páginas.
    #
    # **La tabla se saca de un inventario completo de caracteres, no
    # buscando los sospechosos.** Buscándolos aparecieron tres; el
    # inventario destapó cinco más. Con los tres primeros el texto ya
    # *parecía* correcto de un vistazo y seguía diciendo «a travØs» y
    # «MAR˝A CLAUDIA GARC˝A D`VILA».
    #
    # Se declara por documento y no como limpieza general a propósito. Una
    # tabla de sustituciones aplicada a ciegas a todo el corpus es una
    # forma excelente de estropear un texto que estaba bien.
    sustituciones: tuple[tuple[str, str], ...] = ()

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

    # Descarta los fragmentos cuyo texto ya esté en el corpus ingerido.
    #
    # Se declara como regla y no como lista de números de fragmento para
    # que la ingesta se vuelva a derivar sola. Pero conviene tener presente
    # su límite: **el resultado depende del corpus que haya en la base en
    # ese momento**. Reingerir esta fuente con otro corpus delante puede
    # descartar un conjunto distinto. Es reproducible dado el mismo estado
    # de la base, no en abstracto.
    descartar_repetidos: bool = False

    # Expresión regular que reconoce el primer párrafo de una ficha. Donde
    # encaja, el troceo cierra el fragmento anterior y abre uno nuevo, sin
    # arrastrar solape.
    #
    # Hace falta en los documentos organizados por fichas de especie: sin
    # esto, un fragmento contiene el final de una planta y el principio de
    # la siguiente, y el modelo puede atribuirle a una los datos de la otra.
    # Medido en el corpus del 15/08/2026, un fragmento que se recupera al
    # preguntar por la limonaria terminaba con «el mejor contenedor para el
    # hinojo son los baldes» dentro.
    marcador_de_ficha: str = ""

    # Cuántos párrafos de rótulo van DELANTE del marcador y hay que
    # arrastrar al fragmento nuevo. En Sembrando Biodiversidad son dos
    # —nombre común y nombre científico, antes de `1. Generalidades`—. En el
    # catálogo de plantas es cero: allí el marcador es el hábito de la
    # planta, que ya es el primer párrafo de la ficha.
    rotulos_de_ficha: int = 2

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
        # Decidido el 15/08/2026. De sus 83 fragmentos, 21 repiten más de
        # la mitad de su texto de lo que ya está ingerido, y el peor un
        # 85 %: en una consulta que caiga sobre uno de esos pasajes, el
        # top-k gastaría dos de sus cuatro puestos diciendo lo mismo.
        descartar_repetidos=True,
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
        # Dos cortes por regla, ambos comprobados el 15/08/2026: ocupan la
        # página entera y empiezan por ese renglón.
        #
        # `Bibliografía` — las 18 bibliografías de ficha, una por especie.
        #
        # `PREPARACIÓN` — las 15 páginas de preparación del recetario. Se
        # maquetan en TRES columnas y la extracción las deja inservibles:
        # «1. Cocinar el haba al 2. Una vez cocinada 3. Pasar por un vapor
        # o con poca agua, dejar enfriar y colar. procesador o licuadora».
        # La separación de columnas no las salva porque parte por una sola
        # calle y ahí hay dos. Una receta revuelta entrando como fuente
        # oficial es peor que no tenerla: invita al modelo a componer una
        # preparación que el documento no dice, que es el mismo motivo por
        # el que el ADR-0009 recortó las columnas ilegibles de las tablas
        # de especies. Se conservan las páginas de valor nutricional y las
        # de cultivo del recetario, que son de una columna y salen bien.
        saltar_pagina_si_empieza_por=("Bibliografía", "PREPARACIÓN"),
        # Cada ficha abre con `1. Generalidades`, precedido del nombre común
        # en mayúsculas y del nombre científico. Comprobado el 15/08/2026:
        # aparece 18 veces, siempre al principio de párrafo, una por especie.
        marcador_de_ficha=r"^1\.\s*Generalidades",
        ratio_medida=True,
        nota=(
            "El más trabajado de los tres. 33 páginas cortadas por regla y "
            "81 leídas por columnas. No solapa con el corpus ya ingerido: "
            "0 de 211 fragmentos por encima del 50 %. Queda un residuo "
            "conocido: en las páginas de descripción botánica los rótulos "
            "del margen izquierdo (TALLO, HOJAS, SEMILLAS) se inyectan "
            "dentro de la frase, porque ahí no hay dos columnas de texto "
            "sino una etiqueta al margen. Cinco páginas avisan además de "
            "texto rotado que pypdf no extrae."
        ),
    ),
    # --- El resto de la carpeta, declarados el 15/08/2026 ----------------
    "jbb_manejo_integrado_2011": FuenteDocumento(
        clave="jbb_manejo_integrado_2011",
        entidad="Jardín Botánico de Bogotá José Celestino Mutis",
        titulo=(
            "Cartilla para el manejo integrado de la fertilización, las "
            "plagas y las enfermedades en las Unidades Integrales de "
            "Agricultura Urbana en Bogotá D.C."
        ),
        # Comprobado el 15/08/2026: los bytes de esta URL son idénticos al
        # PDF local. La candidata anterior, `cartilla_tecnica_agricultura_
        # urbana.pdf`, se descargó y se descartó: era otro documento, de 62
        # páginas y de otra administración.
        url=(
            "https://jbb.gov.co/documentos/tecnica/2018/"
            "Cartilla_agricultura_urbana_final.pdf"
        ),
        archivo="Cartilla_agricultura_urbana_final.pdf",
        # 1 y 3 portadas, 5 créditos y autoras. La 7 abre la introducción.
        # La 54 es la literatura citada y la 55 la contracubierta.
        pagina_inicial=7,
        pagina_final=53,
        # Medida sobre sus fragmentos: media 4.61, extremo denso 3.56.
        caracteres_por_token=3.56,
        # El folio va impreso como `- 16 -` en el segundo renglón, debajo
        # de la cabecera, y su desfase **crece de 2 a 5** a lo largo del
        # documento: las páginas 13, 18 y 27 son imágenes sin numerar y
        # cada una corre la cuenta. Medido página a página el 15/08/2026.
        folio_desfase_variable=True,
        ratio_medida=True,
        nota=(
            "El de plagas y enfermedades, que es la consulta insignia del "
            "CU2. Lleva cabecera y pie repetidos en 23 y 25 páginas, que "
            "los quita la detección de plantilla. Su maquetación en "
            "versalitas deja 63 palabras con mayúscula intercalada "
            "(«agriCUltUra»), casi todas en esa cabecera y en títulos; la "
            "prosa sale limpia."
        ),
    ),
    "jbb_cartilla_1_2010": FuenteDocumento(
        clave="jbb_cartilla_1_2010",
        entidad="Jardín Botánico de Bogotá José Celestino Mutis",
        titulo="Cartilla 1. Agricultura urbana",
        url=(
            "https://jbb.gov.co/documentos/agricultura/2022/protocolo/"
            "Cartilla_1_Agricultura_urbana2010.pdf"
        ),
        archivo="Cartilla_1_Agricultura_urbana2010.pdf",
        # 1 portada, 3 y 4 junta directiva y comité editorial, 5 tabla de
        # contenido. La 7 abre la presentación. De la 52 a la 54 va
        # divulgación institucional —programa de radio, curso virtual,
        # directorio— y la 55 es la bibliografía.
        pagina_inicial=7,
        pagina_final=51,
        # Medida sobre sus fragmentos: media 4.53, extremo denso 3.81.
        caracteres_por_token=3.81,
        ratio_medida=True,
        nota="El más sencillo de los cinco: folio sin desfase y sin plantilla repetida.",
    ),
    "jbb_catalogo_plantas": FuenteDocumento(
        clave="jbb_catalogo_plantas",
        entidad="Jardín Botánico de Bogotá José Celestino Mutis",
        titulo="Catálogo de plantas usadas en agricultura urbana",
        url=(
            "https://jbb.gov.co/documentos/agricultura/2022/protocolo/"
            "catalog-plantas-usadas-agricultura-urb.pdf"
        ),
        archivo="catalog-plantas-usadas-agricultura-urb.pdf",
        # 1 portada, 2 a 4 tabla de contenido. La 5 abre la introducción.
        # De la 125 a la 127 van las referencias.
        pagina_inicial=5,
        pagina_final=124,
        # El más denso de los seis: media 3.74 y extremo denso 2.97. Son
        # fichas cortas cargadas de nomenclatura botánica y de nombres de
        # principios activos. Con el 3.9 heredado, el máximo real llegaba a
        # 722 tokens y solo el 52 % caía dentro del intervalo.
        caracteres_por_token=2.97,
        desfase_folio=10,
        # Sube desde 10 porque es un documento por fichas: `Compositae`
        # sale en 12 páginas y `Lamiaceae` en 11, y son familias botánicas,
        # no maquetación.
        #
        # El valor no es libre, lo fija el propio documento. Con 20 se caía
        # `HIERBA` (61 páginas) pero sobrevivían `ENREDADERA` (15), `ÁRBOL`
        # (12) y `ARBUSTO` (11): unas fichas conservaban el hábito de la
        # planta y otras lo perdían, que es peor que cualquiera de los dos
        # extremos. Con 70 sobreviven los cuatro y se van solo los dos
        # renglones que sí son ruido uniforme: `USOS` (102 páginas) y
        # `KJBNVBJNBHJBHJ` (110), un resto de maquetación.
        paginas_para_plantilla=70,
        # Cada ficha abre con el hábito de la planta, que ya es el primer
        # párrafo: no hay rótulo que arrastrar hacia atrás. Son 104 fichas
        # en 56 fragmentos, o sea dos especies por fragmento, y en el
        # documento del contenido medicinal esa mezcla es la más dañina de
        # todas: atribuiría a una planta el uso medicinal de otra.
        # El límite de palabra no sobra: sin él, `ÁRBOL` encajaría
        # también en `ÁRBOLES`, que es el título de la sección y no una
        # ficha de especie.
        marcador_de_ficha=r"^(ÁRBOL|ARBUSTO|SUBARBUSTO|HIERBA|ENREDADERA)\b",
        rotulos_de_ficha=0,
        ratio_medida=True,
        nota=(
            "El del contenido medicinal: atribuye a la papayuela uso «como "
            "tratamiento de diabetes, enfermedades hepáticas». Entra con la "
            "advertencia del ADR-0015 ya puesta. DESVIACIÓN DECLARADA: sus "
            "fragmentos miden unos 183 tokens, por debajo del intervalo de "
            "300-500 de la Fase 4, y solo el 10 % cae dentro. Es "
            "deliberado: una ficha de especie mide eso, y respetar el "
            "intervalo exigiría meter dos plantas en cada fragmento. En un "
            "documento que atribuye usos medicinales, esa mezcla es el peor "
            "fallo posible. El intervalo es un medio para que el fragmento "
            "sea una unidad con sentido; aquí la unidad con sentido es más "
            "corta que el intervalo."
        ),
    ),
    # --- Tercera tanda, del 15/08/2026 -----------------------------------
    #
    # Las dos primeras NO son del Jardín Botánico, y es la primera vez que
    # pasa. La línea de la fuente que lee la usuaria dirá «FAO» y
    # «Universidad Nacional Abierta y a Distancia», que es lo correcto: sale
    # de la tabla `fuente` por la clave foránea, no del texto vectorizado
    # (ADR-0009, decisión 6).
    "fao_compostaje_2013": FuenteDocumento(
        clave="fao_compostaje_2013",
        entidad=(
            "Organización de las Naciones Unidas para la Alimentación y la "
            "Agricultura (FAO)"
        ),
        titulo=(
            "Manual de compostaje del agricultor. Experiencias en América "
            "Latina"
        ),
        url="PENDIENTE",
        archivo="Manual de compostaje del agricultor.pdf",
        # 1 portada, 3 portadilla, 4 avisos legales, 5 equipo técnico, 6
        # presentación, 7 resumen ejecutivo, 8 y 9 índice y lista de
        # figuras. La 15 abre el capítulo 1 (folio impreso 13). De la 103 a
        # la 108 va la bibliografía y la 109 son anotaciones en blanco.
        pagina_inicial=15,
        pagina_final=101,
        # Medida sobre sus fragmentos: media 4.11, extremo denso 3.32.
        caracteres_por_token=3.32,
        # Constante y comprobado en las 100 páginas que llevan folio.
        desfase_folio=2,
        ratio_medida=False,
        nota=(
            "Primera fuente que no es del Jardín Botánico. Su alcance es "
            "América Latina, no Bogotá: el compostaje es de los temas que "
            "peor y mejor viajan, porque el proceso es universal pero los "
            "tiempos dependen del clima, y Bogotá está a 2.600 m."
        ),
    ),
    "unad_agroecologica_2021": FuenteDocumento(
        clave="unad_agroecologica_2021",
        entidad="Universidad Nacional Abierta y a Distancia (UNAD)",
        titulo=(
            "Producción agroecológica urbana - periurbana y su contribución "
            "en la seguridad alimentaria de Colombia"
        ),
        url="PENDIENTE",
        archivo="Producción+agroecológica+(Digital).pdf",
        # De la 1 a la 14 van portada, autores, créditos, ficha catalográfica,
        # reseñas, contenido y listas de tablas y figuras. La 15 es la
        # presentación, prosa institucional; la 16 abre la introducción, que
        # es el mismo criterio con el que entraron los otros. De la 204 en
        # adelante van las referencias.
        pagina_inicial=16,
        pagina_final=203,
        # Elegida COMPARANDO, no por la regla del extremo denso, y es el
        # primer documento en que esa regla no sirve. Medido sobre sus
        # fragmentos: media 4.16, extremo denso 3.18. Pero con 3.18 solo el
        # 58 % cae en el intervalo, con 3.6 el 69 % y con 3.9 el 73 %.
        #
        # El motivo es la mecánica del troceo: cuando un párrafo largo llega
        # detrás de uno corto, el corto se cierra tal cual y sale un
        # fragmento pequeño. Este libro alterna prosa con pies de figura, así
        # que eso pasa a menudo, y cuanto menor es la ratio —y por tanto el
        # tamaño máximo— más veces ocurre. La regla del ADR-0009 dimensiona
        # para que el máximo entre en el intervalo; aquí lo que domina es el
        # mínimo.
        caracteres_por_token=3.9,
        # El desfase se reparte entre -1, -2, -3 y -4: hay páginas sin
        # numerar intercaladas, como en la cartilla de 2011.
        folio_desfase_variable=True,
        ratio_medida=False,
        nota=(
            "Libro académico. Lleva cabecera repetida en 92 páginas y "
            "encabezados de capítulo en otras tantas, que los quita la "
            "detección de plantilla. PENDIENTE DE DECIDIR: su capítulo 4, "
            "«Agricultura digital urbana», ocupa de la 142 a la 171 y trata "
            "de plantas agro-voltaicas y análisis de palabras clave; no "
            "responde nada que una usuaria vaya a preguntar y competiría en "
            "el top-k."
        ),
    ),
    "jbb_protocolo_espacio_publico_2024": FuenteDocumento(
        clave="jbb_protocolo_espacio_publico_2024",
        entidad="Jardín Botánico de Bogotá José Celestino Mutis",
        titulo=(
            "Protocolo de agricultura urbana y periurbana agroecológica en "
            "espacio público, en el marco del Decreto 315 de 2024"
        ),
        url="PENDIENTE",
        archivo=(
            "Protocolo_de_Agricultura_Urbana_y_Periurbana_Agroecologica_"
            "en_Espacio_Publico.pdf"
        ),
        # La 1 es la tabla de contenido; la 2 abre la introducción. No tiene
        # bibliografía que recortar al final.
        pagina_inicial=2,
        pagina_final=31,
        # Medida sobre sus fragmentos: media 4.53, extremo denso 3.87.
        caracteres_por_token=3.87,
        # Su capa de texto viene de Ghostscript con el mapa de fuente
        # equivocado. Cada correspondencia se lee sola en su contexto
        # —«prÆcticas», «pœblico», «a travØs», «diseæo», «BOGOT`»,
        # «MAR˝A»— y todas son seguras porque esas letras no existen en
        # español.
        #
        # La tabla se sacó de un **inventario completo de caracteres**, no
        # buscando los sospechosos de uno en uno. Buscándolos aparecieron
        # tres; el inventario destapó seis más. Con los tres primeros el
        # texto ya *parecía* correcto de un vistazo y seguía diciendo
        # «a travØs» y «JosØ Celestino Mutis».
        #
        # `<` y `=` son las comillas de apertura y cierre con que el
        # documento entrecomilla los títulos de los decretos. El `@` en
        # cambio se deja: son correos institucionales del Jardín Botánico,
        # no un carácter roto.
        sustituciones=(
            ("Æ", "á"),
            ("œ", "ú"),
            ("Ø", "é"),
            ("æ", "ñ"),
            ("`", "Á"),
            ("˝", "Í"),
            ("<", '"'),
            ("=", '"'),
        ),
        ratio_medida=False,
        nota=(
            "El único de los tres que es normativo y no agronómico: fija "
            "quién autoriza una huerta en espacio público, qué se puede "
            "sembrar y de qué no responden las entidades. Es el más pegado "
            "al Programa 25 del Plan de Desarrollo Local de Bosa. Repite el "
            "título entero como cabecera en 29 de sus 30 páginas."
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
