"""El dato agronómico y su vector — modelos MP-18 a MP-21.

Riesgo P-08: atribuirle a una huerta un cultivo que no sembró. Es el peor
fallo posible en el dato comunitario, porque la usuaria no tiene forma de
detectarlo —no conoce las otras huertas— y porque el ADR-0011 ya midió que
con 5 a 7 huertas y top-k=4 la similitud recupera medio corpus.
"""

import math

import pytest

from app.services.comunidad import _tiene_la_especie
from app.services.embeddings import _normalizar_l2
from app.services.extraccion import CultivoExtraido, HuertaExtraida
from app.services.fragmento_comunitario import componer_texto
from app.services.registro import fusionar


# --- MP-18: la especie está de verdad en esa huerta ------------------
# Particiones sobre la comparación por palabra completa.


@pytest.mark.parametrize(
    ("contenido", "especie"),
    [
        ("tomate, lechuga", "tomate"),
        ("Tomate, Lechuga", "tomate"),
        ("tomate, lechuga", "TOMATE"),
        # La dirección útil: quien pregunta nombra la especie más corta de
        # como está registrada.
        ("cebolla larga, tomate", "cebolla"),
        ("maíz, frijol", "maiz"),
    ],
)
def test_mp18_la_especie_presente_se_encuentra(contenido, especie):
    assert _tiene_la_especie(contenido, especie) is True


@pytest.mark.parametrize(
    ("contenido", "especie"),
    [
        # El caso que justifica comparar por palabra completa: «papa» no
        # puede dar por buena una huerta que sembró «papaya».
        ("papaya, lechuga", "papa"),
        ("tomate, lechuga", "cilantro"),
        ("", "tomate"),
        ("tomate", ""),
        ("tomate", "   "),
    ],
)
def test_mp18_la_especie_ausente_no_se_inventa(contenido, especie):
    assert _tiene_la_especie(contenido, especie) is False


def test_mp18_no_basta_con_que_aparezca_como_subcadena():
    """`tomatera` no es `tomate`, aunque lo contenga."""
    assert _tiene_la_especie("tomatera", "tomate") is False


# --- MP-19: fusión del borrador de registro --------------------------


def _huerta(*especies: str) -> HuertaExtraida:
    return HuertaExtraida(cultivos=[CultivoExtraido(especie=e) for e in especies])


def _especies(huerta: HuertaExtraida) -> list[str]:
    return [c.especie for c in huerta.cultivos]


def test_mp19_los_cultivos_se_acumulan():
    """«También sembré lechuga» añade, no sustituye.

    Sin fusionar, la segunda frase perdería el tomate de la primera.
    """
    fusionada = fusionar(_huerta("tomate"), _huerta("lechuga"))
    assert sorted(_especies(fusionada)) == ["lechuga", "tomate"]


def test_mp19_no_se_repite_la_misma_especie():
    fusionada = fusionar(_huerta("tomate"), _huerta("tomate"))
    assert _especies(fusionada) == ["tomate"]


def test_mp19_la_repeticion_se_detecta_sin_importar_las_mayusculas():
    fusionada = fusionar(_huerta("Tomate"), _huerta("tomate"))
    assert len(fusionada.cultivos) == 1


def test_mp19_lo_ultimo_que_dijo_va_primero():
    fusionada = fusionar(_huerta("tomate", "cebolla"), _huerta("lechuga"))
    assert _especies(fusionada)[0] == "lechuga"


def test_mp19_fusionar_con_un_borrador_vacio_no_pierde_nada():
    fusionada = fusionar(_huerta(), _huerta("tomate"))
    assert _especies(fusionada) == ["tomate"]

    fusionada = fusionar(_huerta("tomate"), _huerta())
    assert _especies(fusionada) == ["tomate"]


def test_mp19_una_extraccion_vacia_no_tiene_datos():
    """Es lo que decide si hay algo que ofrecer guardar."""
    assert _huerta().tiene_datos is False
    assert _huerta("tomate").tiene_datos is True


# --- MP-20: normalización L2 del vector ------------------------------


def test_mp20_el_vector_queda_de_longitud_uno():
    """`gemini-embedding-001` no normaliza los truncados a 768 dimensiones."""
    normalizado = _normalizar_l2([3.0, 4.0])
    assert normalizado == pytest.approx([0.6, 0.8])


def test_mp20_la_norma_resultante_es_uno():
    normalizado = _normalizar_l2([1.0, 2.0, 3.0, 4.0])
    norma = math.sqrt(sum(c * c for c in normalizado))
    assert norma == pytest.approx(1.0)


def test_mp20_un_vector_ya_normalizado_no_cambia():
    assert _normalizar_l2([1.0, 0.0]) == pytest.approx([1.0, 0.0])


def test_mp20_el_vector_nulo_es_un_error_y_no_se_tolera():
    """Un vector nulo no tiene dirección: la similitud coseno queda indefinida.

    Es señal de un fallo del modelo. Devolver ceros dejaría el fragmento
    en la base sin que nada lo delatara.
    """
    with pytest.raises(ValueError):
        _normalizar_l2([0.0, 0.0, 0.0])


# --- MP-21: el texto que se vectoriza --------------------------------


def test_mp21_el_fragmento_lleva_las_especies_y_nada_mas():
    """Ni fecha ni barrio ni nombre: solo especies (ADR-0011 y ADR-0018).

    La fecha dentro del fragmento empeoraba la recuperación —0.0735 de
    separación frente a 0.1166— y además era un dato de solo escritura.
    """
    assert componer_texto(["tomate", "lechuga", "cebolla"]) == "tomate, lechuga, cebolla"


def test_mp21_una_huerta_sin_cultivos_da_texto_vacio():
    """Una huerta sin cultivos es lo normal desde el onboarding del ADR-0016."""
    assert componer_texto([]) == ""
