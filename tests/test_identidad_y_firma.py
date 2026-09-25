"""Identidad, huellas y firma — modelos MP-01 a MP-06.

Cubre los riesgos P-02 (la usuaria no recibe nada porque la identidad se
resolvió mal) y P-07 (un dato personal acaba en la bitácora o en la base
en claro). Son las dos filas de mayor consecuencia del registro de
riesgos, y P-07 ya se materializó el 30/07/2026.
"""

import hashlib
import hmac
import re

import pytest

from app.config import settings
from app.core.identidad import (
    calcular_identidad_hash,
    cifrar_nombre,
    descifrar_nombre,
    es_telefono,
    huella_wamid,
    normalizar_telefono,
    referencia_wamid,
)
from app.core.signature import firma_valida

# Un wamid con la forma de los de Meta. El de verdad lleva el teléfono
# dentro en base64 (comprobado el 30/07/2026); este lleva un número
# inventado con la marca `57000000` de los datos temporales.
_WAMID = "wamid.HBgMNTcwMDAwMDAwNjAxFQIAERgSMEE5QjhDN0Q2RTVGNEEzQjJDAA=="
_TELEFONO = "573001234567"
_BSUID = "CO.570000000601"


# --- MP-01: qué es un teléfono y qué es un BSUID ---------------------
# Particiones de equivalencia sobre la forma del identificador.


@pytest.mark.parametrize(
    "identidad",
    [
        _TELEFONO,
        "+57 300 123 4567",
        "(57) 300-123-4567",
        "57300123456",
    ],
)
def test_mp01_los_telefonos_se_reconocen(identidad):
    assert es_telefono(identidad) is True


@pytest.mark.parametrize(
    "identidad",
    [
        _BSUID,
        "US.13491208655302741918",
        # El caso que motivó el filtro de forma del ADR-0023: un BSUID
        # corto que, si solo se contaran dígitos, pasaría por teléfono.
        "CO.12345678",
        "",
        None,
        "no soy un identificador",
    ],
)
def test_mp01_lo_que_no_es_telefono_no_lo_parece(identidad):
    assert es_telefono(identidad) is False


# --- MP-02: longitud del teléfono ------------------------------------
# Valores límite sobre el rango [8, 15] de la E.164.


@pytest.mark.parametrize("digitos", [8, 9, 14, 15])
def test_mp02_las_longitudes_validas_se_aceptan(digitos):
    numero = "5" * digitos
    assert normalizar_telefono(numero) == numero


@pytest.mark.parametrize("digitos", [0, 1, 7, 16, 20])
def test_mp02_las_longitudes_invalidas_se_rechazan(digitos):
    with pytest.raises(ValueError):
        normalizar_telefono("5" * digitos)


def test_mp02_el_mensaje_de_error_no_lleva_el_numero():
    """El error se registra; el número no puede viajar dentro (CLAUDE.md §11)."""
    numero = "5" * 7
    with pytest.raises(ValueError) as fallo:
        normalizar_telefono(numero)

    assert numero not in str(fallo.value)


def test_mp02_la_puntuacion_no_cambia_la_identidad():
    """Un mismo número escrito de tres formas da una sola huella.

    Si no fuera así, la usuaria dejaría de ser reconocida en cuanto el
    formato cambiara, con el mismo efecto que cambiar el pepper.
    """
    huellas = {
        calcular_identidad_hash(escrito)
        for escrito in ("573001234567", "+573001234567", "+57 300 123 4567")
    }
    assert len(huellas) == 1


# --- MP-03: los dominios del HMAC separan los espacios ---------------


def test_mp03_la_huella_es_determinista():
    assert calcular_identidad_hash(_BSUID) == calcular_identidad_hash(_BSUID)


def test_mp03_el_bsuid_y_el_telefono_no_pueden_coincidir():
    """Dos espacios de identificadores, dos huellas, aunque compartan pepper.

    Es lo que garantiza la etiqueta de dominio del ADR-0023.
    """
    assert calcular_identidad_hash(_BSUID) != calcular_identidad_hash(_TELEFONO)


def test_mp03_el_telefono_no_lleva_etiqueta_de_dominio():
    """El teléfono se calcula sin prefijo, y eso no se puede cambiar.

    Cambiarlo equivaldría a cambiar el pepper: las usuarias que quedaran
    identificadas por número dejarían de ser reconocidas.
    """
    esperada = hmac.new(
        key=settings.PHONE_HASH_PEPPER.encode("utf-8"),
        msg=_TELEFONO.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    assert calcular_identidad_hash(_TELEFONO) == esperada


def test_mp03_el_bsuid_lleva_su_etiqueta():
    esperada = hmac.new(
        key=settings.PHONE_HASH_PEPPER.encode("utf-8"),
        msg=f"bsuid:{_BSUID}".encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    assert calcular_identidad_hash(_BSUID) == esperada


def test_mp03_la_huella_cabe_en_la_columna():
    """64 caracteres hexadecimales, que es la restricción CHECK del esquema."""
    huella = calcular_identidad_hash(_BSUID)
    assert re.fullmatch(r"[0-9a-f]{64}", huella)


# --- MP-04: el wamid nunca en claro ----------------------------------


def test_mp04_la_referencia_no_contiene_el_wamid():
    """Recortar el wamid seguiría exponiendo el teléfono, que va al principio.

    Esta prueba fija el defecto corregido el 30/07/2026 para que no pueda
    volver por descuido.
    """
    referencia = referencia_wamid(_WAMID)

    assert referencia not in _WAMID
    assert _WAMID[:16] not in referencia


def test_mp04_la_referencia_es_prefijo_de_la_huella():
    """Así una línea de bitácora se puede cruzar con la fila de idempotencia."""
    assert huella_wamid(_WAMID).startswith(referencia_wamid(_WAMID))


def test_mp04_la_referencia_mide_dieciseis_hexadecimales():
    assert re.fullmatch(r"[0-9a-f]{16}", referencia_wamid(_WAMID))


def test_mp04_la_huella_del_wamid_es_determinista():
    """La idempotencia depende de ello: el reintento de Meta trae el mismo wamid."""
    assert huella_wamid(_WAMID) == huella_wamid(_WAMID)


def test_mp04_dos_wamid_distintos_dan_huellas_distintas():
    assert huella_wamid(_WAMID) != huella_wamid(_WAMID.replace("HBgM", "HBgN"))


# --- MP-05: cifrado del nombre ---------------------------------------


def test_mp05_el_nombre_va_y_vuelve():
    assert descifrar_nombre(cifrar_nombre("María José")) == "María José"


def test_mp05_dos_cifrados_del_mismo_nombre_son_distintos():
    """El nonce es nuevo en cada llamada; si no, el cifrado sería reconocible."""
    assert cifrar_nombre("Ana") != cifrar_nombre("Ana")


def test_mp05_el_cifrado_no_deja_el_nombre_a_la_vista():
    assert b"Ana" not in cifrar_nombre("Ana")


@pytest.mark.parametrize("vacio", [None, ""])
def test_mp05_sin_nombre_no_hay_cifrado(vacio):
    """La columna admite nulos mientras la usuaria no haya dado su nombre."""
    assert cifrar_nombre(vacio) is None
    assert descifrar_nombre(None) is None


# --- MP-06: firma de Meta --------------------------------------------


def test_mp06_la_firma_correcta_se_acepta(firmar):
    cuerpo = b'{"entry":[]}'
    assert firma_valida(cuerpo, firmar(cuerpo)) is True


def test_mp06_el_cuerpo_alterado_se_rechaza(firmar):
    """Un solo byte distinto basta: es de lo que protege la capa 5."""
    cuerpo = b'{"entry":[]}'
    assert firma_valida(b'{"entry":[ ]}', firmar(cuerpo)) is False


@pytest.mark.parametrize(
    "cabecera",
    [
        None,
        "",
        # Sin el prefijo del algoritmo.
        "a" * 64,
        # Con otro algoritmo.
        "sha1=" + "a" * 40,
        # Bien formada pero falsa.
        "sha256=" + "0" * 64,
    ],
)
def test_mp06_las_cabeceras_invalidas_o_ausentes_se_rechazan(cabecera):
    assert firma_valida(b'{"entry":[]}', cabecera) is False
