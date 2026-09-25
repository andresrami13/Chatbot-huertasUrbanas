"""A quién se le responde y por dónde — modelos MP-07 y MP-08.

Es el riesgo **P-02**, el de mayor exposición del registro (20) y el único
que ya dejó a usuarias sin recibir nada: ocho mensajes de unos setenta el
15/09/2026. Son dos tablas de decisión pequeñas y es donde equivocarse no
produce un error visible, sino silencio.
"""

import pytest

from app.services.dispatcher import _resolver_identidad
from app.services.whatsapp import _campo_destino

_BSUID = "CO.570000000601"
_TELEFONO = "573001234567"
_REF = "0123456789abcdef"


# --- MP-07: en qué campo viaja el destinatario -----------------------
# Tabla de decisión de una sola condición: ¿el destino es un teléfono?


def test_mp07_al_bsuid_se_le_responde_por_recipient():
    """Desde el ADR-0023 es el camino normal: por aquí salen todas las respuestas."""
    assert _campo_destino(_BSUID) == {"recipient": _BSUID}


def test_mp07_al_telefono_se_le_responde_por_to():
    """Rama de respaldo, la que actúa si un mensaje llegara sin BSUID."""
    assert _campo_destino(_TELEFONO) == {"to": _TELEFONO}


@pytest.mark.parametrize("destino", [_BSUID, _TELEFONO])
def test_mp07_nunca_se_mandan_los_dos_campos(destino):
    """Meta admite los dos y entonces usa el teléfono.

    Mandar ambos taparía para siempre un error en el BSUID: el envío
    saldría bien por el número y el sistema estaría diciendo que funciona
    algo que no se ha probado.
    """
    assert len(_campo_destino(destino)) == 1


# --- MP-08: la escalera de identidad del despachador -----------------
# Tabla de decisión de tres peldaños, en orden de preferencia.


def test_mp08_el_bsuid_del_mensaje_manda():
    mensaje = {"from_user_id": _BSUID, "from": _TELEFONO}
    assert _resolver_identidad(mensaje, _BSUID, _REF) == _BSUID


def test_mp08_el_contacto_es_el_segundo_peldano():
    """No es lo esperado: significa que la forma del webhook cambió."""
    assert _resolver_identidad({"from": _TELEFONO}, _BSUID, _REF) == _BSUID


def test_mp08_el_telefono_es_la_red_de_seguridad():
    assert _resolver_identidad({"from": _TELEFONO}, None, _REF) == _TELEFONO


def test_mp08_sin_nada_con_que_identificar_se_descarta():
    """Sin identidad no hay a quién responder ni bajo qué fila guardar."""
    assert _resolver_identidad({}, None, _REF) is None


def test_mp08_el_bsuid_gana_aunque_venga_el_telefono():
    """Si ganara el teléfono, la misma persona quedaría con dos huellas."""
    mensaje = {"from_user_id": _BSUID, "from": _TELEFONO}
    assert _resolver_identidad(mensaje, None, _REF) != _TELEFONO


def test_mp08_la_identidad_resuelta_sirve_como_destino():
    """Las dos decisiones tienen que encajar: lo que identifica es lo que recibe.

    Un mensaje sin teléfono —lo que llega desde que ella activa su nombre
    de usuario de WhatsApp— se identifica por BSUID y **debe** salir por
    `recipient`. Esta es la cadena que falló en septiembre.
    """
    identidad = _resolver_identidad({"from_user_id": _BSUID}, None, _REF)
    assert _campo_destino(identidad) == {"recipient": _BSUID}


def test_mp08_el_respaldo_por_telefono_sale_por_to():
    identidad = _resolver_identidad({"from": _TELEFONO}, None, _REF)
    assert _campo_destino(identidad) == {"to": _TELEFONO}
