"""A quién se le responde y por dónde — modelos MP-07 y MP-08.

Es el riesgo **P-02**, el de mayor exposición del registro (20) y el único
que ya dejó a usuarias sin recibir nada: ocho mensajes de unos setenta el
15/09/2026. Son dos tablas de decisión pequeñas y es donde equivocarse no
produce un error visible, sino silencio.
"""

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


# Las dos comparaciones anteriores son exactas, y con eso cubren también
# la regla de una sola clave: Meta admite las dos y entonces usa el
# teléfono, lo que taparía para siempre un error en el BSUID.


# --- MP-08: la escalera de identidad del despachador -----------------
# Tabla de decisión de tres peldaños, en orden de preferencia.


def test_mp08_el_bsuid_del_mensaje_manda():
    """Aunque venga también el teléfono: si ganara este, la misma persona
    quedaría con dos huellas. Sin contacto, para que no sea él quien gane.
    """
    mensaje = {"from_user_id": _BSUID, "from": _TELEFONO}
    assert _resolver_identidad(mensaje, None, _REF) == _BSUID


def test_mp08_el_contacto_es_el_segundo_peldano():
    """No es lo esperado: significa que la forma del webhook cambió."""
    assert _resolver_identidad({"from": _TELEFONO}, _BSUID, _REF) == _BSUID


def test_mp08_el_telefono_es_la_red_de_seguridad():
    assert _resolver_identidad({"from": _TELEFONO}, None, _REF) == _TELEFONO


def test_mp08_sin_nada_con_que_identificar_se_descarta():
    """Sin identidad no hay a quién responder ni bajo qué fila guardar."""
    assert _resolver_identidad({}, None, _REF) is None


def test_mp08_la_identidad_resuelta_sirve_como_destino():
    """Las dos decisiones tienen que encajar: lo que identifica es lo que recibe.

    Un mensaje sin teléfono —lo que llega desde que ella activa su nombre
    de usuario de WhatsApp— se identifica por BSUID y **debe** salir por
    `recipient`. Esta es la cadena que falló en septiembre.
    """
    identidad = _resolver_identidad({"from_user_id": _BSUID}, None, _REF)
    assert _campo_destino(identidad) == {"recipient": _BSUID}
