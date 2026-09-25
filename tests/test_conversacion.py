"""La capa determinista de la conversación — modelos MP-09 a MP-13.

Todo lo de aquí se resuelve **sin el modelo**, y esa es justamente la
razón de probarlo: son las piezas que deciden antes de que haya
consentimiento (ADR-0006) o que sostienen el onboarding (ADR-0016), donde
un fallo deja a la usuaria atascada sin salida. Riesgo P-16.
"""

import pytest

from app.core.texto import normalizar
from app.services.consentimiento import es_saludo_o_ayuda
from app.services.onboarding import (
    _es_respuesta_util,
    componer_opciones,
    componer_resumen,
    leer_numero,
)


# --- MP-09: normalización para comparar ------------------------------
# Particiones: mayúsculas, tildes, signos, espacios repetidos.


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("HOLA", "hola"),
        ("Sí", "si"),
        ("Holanda,", "holanda"),
        ("¿Qué más?", "que mas"),
        ("  dos   espacios  ", "dos espacios"),
        ("El Regalo", "el regalo"),
        ("", ""),
        ("!!!", ""),
    ],
)
def test_mp09_normalizacion(entrada, esperado):
    assert normalizar(entrada) == esperado


def test_mp09_el_emoji_de_teclado_queda_en_su_digito():
    """Si ella copia la opción de la lista en vez de escribir el número.

    El envolvente y el selector de variación caen, y queda el dígito.
    """
    assert normalizar("3️⃣") == "3"


def test_mp09_normalizar_no_sirve_para_mostrar():
    """Se declara aquí lo que la función NO hace, para que no se use mal.

    Lo que se guarda y lo que se le enseña conserva sus tildes: los
    barrios van en mayúscula y sin recortar (ADR-0016).
    """
    assert normalizar("BOSA CENTRAL") != "BOSA CENTRAL"


# --- MP-10: saludo y ayuda sin modelo --------------------------------


@pytest.mark.parametrize(
    "texto",
    ["hola", "Hola", "HOLA", "buenos dias", "Buenos días", "ayuda", "qué hace"],
)
def test_mp10_los_saludos_y_peticiones_de_ayuda_se_reconocen(texto):
    assert es_saludo_o_ayuda(texto) is True


@pytest.mark.parametrize(
    "texto",
    [
        # El caso que importa: un saludo con una consulta detrás. Tratarlo
        # como saludo la dejaría sin respuesta a lo que preguntó.
        "hola, mi tomate tiene bichos",
        "mi tomate tiene bichos",
        "",
        None,
        "buenas, una pregunta sobre el compost",
    ],
)
def test_mp10_una_consulta_no_es_un_saludo(texto):
    assert es_saludo_o_ayuda(texto) is False


def test_mp10_el_limite_es_de_cuatro_palabras():
    """Valor límite del filtro de longitud."""
    assert es_saludo_o_ayuda("hola") is True
    assert es_saludo_o_ayuda("hola hola hola hola hola") is False


# --- MP-11: leer la respuesta a la lista numerada --------------------
# Particiones más valores límite sobre el rango [1, máximo].


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("1", 1),
        ("3", 3),
        ("tres", 3),
        ("TRES", 3),
        # Por voz la transcripción es literal: "tres" nunca llega como dígito.
        ("cinco", 5),
        ("3️⃣", 3),
        # La puntuación cae en la normalización, así que «1.» y «-1» se
        # leen como 1. No es una concesión buscada, es consecuencia de
        # `normalizar`, y conviene dejarla fijada: mucha gente numera así.
        ("1.", 1),
        ("-1", 1),
    ],
)
def test_mp11_lo_que_es_un_numero_se_lee(texto, esperado):
    assert leer_numero(texto, 5) == esperado


@pytest.mark.parametrize("texto", ["0", "6", "la de arriba", "Holanda sector 3", "", None])
def test_mp11_lo_que_no_es_un_numero_valido_se_descarta(texto):
    assert leer_numero(texto, 5) is None


@pytest.mark.parametrize(("numero", "valido"), [(0, False), (1, True), (5, True), (6, False)])
def test_mp11_los_limites_del_rango(numero, valido):
    resultado = leer_numero(str(numero), 5)
    assert (resultado is not None) is valido


# --- MP-12: componer la lista numerada -------------------------------


def _candidatos(cuantos: int) -> list[tuple[str, str]]:
    return [(f"C{i}", f"BARRIO NUMERO {i}") for i in range(1, cuantos + 1)]


def test_mp12_el_total_cuenta_las_salidas():
    """Tres candidatos más «ninguno» son cuatro opciones."""
    _, total = componer_opciones(_candidatos(3), ofrecer_otro=False)
    assert total == 4


def test_mp12_con_la_opcion_otro_hay_una_mas():
    _, total = componer_opciones(_candidatos(3), ofrecer_otro=True)
    assert total == 5


def test_mp12_los_nombres_no_se_recortan():
    """El cuerpo admite 1024 caracteres: no hay por qué recortar un nombre oficial.

    Es lo que permitió descartar los botones para desambiguar el barrio
    (ADR-0016), cuyo rótulo solo admite 20 caracteres.
    """
    nombre = "SAN BERNARDINO XXV SECTOR URBANIZACION LA ESPERANZA"
    texto, _ = componer_opciones([("C1", nombre)], ofrecer_otro=False)
    assert nombre in texto


def test_mp12_la_lista_y_el_lector_encajan():
    """Las dos piezas tienen que estar de acuerdo sobre cuál es el máximo.

    Si no, la última opción de la lista sería ilegible para `leer_numero`
    y ella quedaría atascada eligiendo algo que el sistema rechaza.
    """
    texto, total = componer_opciones(_candidatos(3), ofrecer_otro=True)

    assert leer_numero(str(total), total) == total
    assert leer_numero(str(total + 1), total) is None
    for indice in range(1, total + 1):
        assert leer_numero(str(indice), total) == indice
    assert texto.count("\n") >= total


# --- MP-13: qué es una respuesta aprovechable ------------------------


@pytest.mark.parametrize("texto", ["María", "La Esperanza", "la huerta de casa"])
def test_mp13_un_nombre_razonable_se_acepta(texto):
    assert _es_respuesta_util(texto, 4) is True


@pytest.mark.parametrize(
    "texto",
    [
        None,
        "",
        "   ",
        "¿por qué me pregunta eso?",
        "esto son seis palabras y sobra",
    ],
)
def test_mp13_lo_que_claramente_no_es_un_nombre_se_descarta(texto):
    assert _es_respuesta_util(texto, 4) is False


def test_mp13_el_limite_es_de_cuatro_palabras():
    """Valor límite del filtro. Cinco palabras ya no pasan."""
    assert _es_respuesta_util("una dos tres cuatro", 4) is True
    assert _es_respuesta_util("una dos tres cuatro cinco", 4) is False


# --- El resumen del cierre del onboarding ----------------------------


def test_mp13_el_resumen_muestra_lo_que_se_va_a_guardar():
    """Lo compone el código, no el modelo: ella confirma lo que quedará guardado."""
    resumen = componer_resumen("María", "HOLANDA", "La Esperanza")

    assert "María" in resumen
    assert "HOLANDA" in resumen
    assert "La Esperanza" in resumen
    assert resumen.rstrip().endswith("¿Lo guardo así?")


def test_mp13_sin_nombre_no_se_inventa_la_linea():
    resumen = componer_resumen(None, "HOLANDA", "La Esperanza")
    assert "Nombre:" not in resumen
    assert "HOLANDA" in resumen
