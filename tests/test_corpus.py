"""La limpieza del corpus — modelo MP-25.

Riesgo P-14: texto defectuoso extraído del PDF llega a la usuaria. Las dos
incidencias que lo materializaron son INC-019 (restos de extracción) e
INC-010 (rótulos del margen metidos en la frase).

Estas pruebas existen por lo que cuesta equivocarse aquí: una regla de
limpieza demasiado ancha **estropea un texto que estaba bien**, y se
aplica con una escritura en la base de datos de producción. Cada caso
fija o lo que la regla debe quitar, o —igual de importante— lo que no
debe tocar.

No abren la base de datos ni la red: `limpiar_fragmento` es texto.
"""

import pytest

from scripts.catalogo_fuentes import CATALOGO
from scripts.ingesta_fuente import limpiar_fragmento

_SEMBRANDO = CATALOGO["jbb_sembrando_2023"].rotulos_del_margen


# --- MP-25a: restos de extracción (INC-019) --------------------------


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        # Las dos viñetas de Wingdings que `pypdf` devolvió sin traducir.
        ("\x93y Caneca de 20 litros", "• Caneca de 20 litros"),
        ("\x93\x93 Canecas de 20 litros", "• Canecas de 20 litros"),
        # La viñeta de la zona de uso privado.
        (" Ajenjo", "• Ajenjo"),
        # El marcador de objeto incrustado, con su espacio.
        ("Anexo 5. ￼ https://x", "Anexo 5. https://x"),
        # La basura pegada al rótulo del catálogo de plantas.
        ("ENREDADERA KJBNVBJNBHJ BHJ Ahuyama", "ENREDADERA Ahuyama"),
    ],
)
def test_mp25_los_restos_de_extraccion_se_quitan(entrada, esperado):
    assert limpiar_fragmento(entrada) == esperado


def test_mp25_el_acento_huerfano_se_quita_donde_iba_una_letra_griega():
    """`α-pineno` salió como ` ́-pineno`: no se sabe qué letra era."""
    assert limpiar_fragmento("tuyona, ́-pineno y") == "tuyona, -pineno y"


def test_mp25_las_tildes_descompuestas_legitimas_no_se_tocan():
    """`a` + U+0301 es una `á` de verdad, y borrarle el acento la rompe."""
    import unicodedata

    descompuesto = unicodedata.normalize("NFD", "La producción está aquí")

    assert unicodedata.normalize("NFC", limpiar_fragmento(descompuesto)) == (
        "La producción está aquí"
    )


@pytest.mark.parametrize(
    "legitimo",
    [
        "Produção Spångberg Lazarević",   # apellidos de las bibliografías
        "Symphytum Dysphania Phyllosticta Cryptosporidium",   # nombres científicos
    ],
)
def test_mp25_lo_que_parece_raro_y_es_legitimo_no_se_toca(legitimo):
    """El inventario lo miró uno por uno: buscar sospechosos lo habría roto."""
    assert limpiar_fragmento(legitimo) == legitimo


# --- MP-25b: rótulos del margen (INC-010) ----------------------------
#
# Los casos son frases reales del corpus, tal como las dejó la extracción.


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        # Un rótulo pegado a otro.
        (
            "el tallo presenta un diámetro de entre 13 mm y TALLOTALL 13,95 mm",
            "el tallo presenta un diámetro de entre 13 mm y 13,95 mm",
        ),
        (
            "Descripción botánica RAÍZ presenta una raíz principal, con TALL ramificaciones",
            "Descripción botánica presenta una raíz principal, con ramificaciones",
        ),
        # `TALLO` partido en dos: la `O` suelta es parte del rótulo.
        (
            "Foliolos delgados TALL O capítulos o cabezuelas",
            "Foliolos delgados capítulos o cabezuelas",
        ),
        # Dos rótulos seguidos: el segundo solo aparece al quitar el primero.
        (
            "a un paraguas. TALL TALLOO tallo delgado y ramificado",
            "a un paraguas. tallo delgado y ramificado",
        ),
        # El rótulo era de dos palabras y salió separado.
        (
            "un área foliar en FOLIAR condiciones optimas",
            "un área foliar en condiciones optimas",
        ),
        # Pegado a un signo, el espacio se conserva o las palabras se juntan.
        (
            "Achillea laxiflora Pollard &TALL Cockerell, Achillea",
            "Achillea laxiflora Pollard & Cockerell, Achillea",
        ),
    ],
)
def test_mp25_los_rotulos_del_margen_se_quitan(entrada, esperado):
    assert limpiar_fragmento(entrada, _SEMBRANDO) == esperado


@pytest.mark.parametrize(
    "legitimo",
    [
        # El nombre de una empresa en mayúscula no es un rótulo.
        "semillas obtenidas de la casa comercial SEMILLAS FERCON. El análisis",
        # Las mismas palabras en minúscula son el texto.
        "las hojas y los tallos de la planta, su fruto y sus semillas son comestibles",
        # Una palabra que contiene un rótulo no es el rótulo.
        "una HOJASECA gruesa cubre el suelo",
        "las HOJAS2 del mapa",
    ],
)
def test_mp25_lo_que_no_es_un_rotulo_no_se_toca(legitimo):
    assert limpiar_fragmento(legitimo, _SEMBRANDO) == legitimo


def test_mp25_sin_lista_de_rotulos_no_se_quita_ninguno():
    """Es por fuente: `HOJAS` en mayúscula puede ser un encabezado legítimo."""
    texto = "el tallo mide 13 mm y TALLOTALL 13,95 mm"

    assert limpiar_fragmento(texto) == texto
    assert limpiar_fragmento(texto, ()) == texto


# --- MP-25c: propiedades de las dos limpiezas ------------------------


@pytest.mark.parametrize(
    "texto",
    [
        "a un paraguas. TALL TALLOO tallo delgado y TALL O capítulos",
        "\x93y Caneca de 20 litros KJBNVBJNBHJ BHJ y HOJAS verdes",
    ],
)
def test_mp25_limpiar_dos_veces_es_limpiar_una(texto):
    """Idempotente: es lo que permite reparar y reingerir sin que difieran."""
    una_vez = limpiar_fragmento(texto, _SEMBRANDO)

    assert limpiar_fragmento(una_vez, _SEMBRANDO) == una_vez


def test_mp25_un_fragmento_limpio_se_devuelve_identico():
    """Ni siquiera se le recortan los espacios: no había nada que arreglar."""
    texto = "  Riegue temprano.\n\nSin   nada que quitar.  "

    assert limpiar_fragmento(texto, _SEMBRANDO) == texto
