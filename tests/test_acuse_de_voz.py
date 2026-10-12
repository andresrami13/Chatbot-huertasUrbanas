"""El acuse de la nota de voz — modelo MP-28 (RF-19, ADR-0017).

Es la única excepción declarada a «enviar y recordar van juntos»
(CLAUDE.md §11): el acuse se envía y **no** entra en la memoria, porque no
dice nada que el agente necesite y gastaría uno de los diez huecos de la
ventana en cada nota de voz.

Se prueba por el camino real, `dispatcher._atender_mensaje`, con espías
solo en los bordes: lo que sale hacia Meta, la transcripción y la memoria.
Así se comprueban a la vez la regla del acuse y su sitio en la rama.
"""

import asyncio
from types import SimpleNamespace
from uuid import UUID

import pytest

from app import textos
from app.services import dispatcher, espera, memoria

_BSUID = "CO.570000000601"
_ELLA = SimpleNamespace(id=UUID("00000000-0000-0000-0000-570000000601"))
_TRANSCRIPCION = "mi tomate tiene bichos"
_AUDIO = {"id": "wamid.prueba", "type": "audio", "audio": {"id": "media-1"}}


@pytest.fixture
def rama(monkeypatch):
    """La rama del despachador con los bordes sustituidos. Anota en orden."""
    sucesos: list[tuple] = []

    async def _nada(*_):
        return None

    async def _compuerta(identidad, texto, boton_id):
        return _ELLA

    async def _enviar(destino, texto):
        sucesos.append(("enviado", destino, texto))

    async def _transcribir(media_id):
        # La de verdad descarga el audio de Meta antes de nada, así que
        # cede el turno en su primera espera de red. El espía lo imita:
        # sin eso mediría un orden que en producción no se da.
        await asyncio.sleep(0)
        sucesos.append(("transcrito", media_id))
        return _TRANSCRIPCION

    async def _recordar_usuaria(usuario_id, contenido, tipo, wamid):
        sucesos.append(("recordado", contenido, tipo))

    async def _registrar(usuario_id, rol, contenido, *_):
        sucesos.append(("registrado", rol, contenido))

    async def _onboarding_termina_aqui(*_):
        return True

    monkeypatch.setattr(dispatcher, "marcar_escribiendo", _nada)
    monkeypatch.setattr(dispatcher, "compuerta", _compuerta)
    monkeypatch.setattr(dispatcher, "transcribir_audio", _transcribir)
    monkeypatch.setattr(dispatcher, "recordar_usuaria", _recordar_usuaria)
    monkeypatch.setattr(dispatcher, "atender_onboarding", _onboarding_termina_aqui)
    monkeypatch.setattr(espera, "enviar_texto", _enviar)
    # Si algo intentara guardar el acuse por la memoria, quedaría anotado.
    monkeypatch.setattr(memoria, "registrar_mensaje", _registrar)
    return sucesos


def _atender(mensaje: dict) -> None:
    async def _turno():
        await dispatcher._atender_mensaje(mensaje, _BSUID, "ref")
        # El acuse sale en una tarea aparte: se espera a que termine.
        await asyncio.gather(*espera._EN_VUELO)

    asyncio.run(_turno())


def test_mp28_el_acuse_le_llega_a_ella_con_una_frase_del_repertorio(rama):
    _atender(_AUDIO)

    enviados = [s for s in rama if s[0] == "enviado"]
    assert len(enviados) == 1
    _, destino, texto = enviados[0]
    assert destino == _BSUID
    assert texto in textos.ESPERA_AUDIO


def test_mp28_el_acuse_no_entra_en_la_memoria(rama):
    """Lo único que se recuerda es lo que ella dijo, ya transcrito y anotado
    como audio. El acuse no aparece en ninguna escritura de la memoria."""
    _atender(_AUDIO)

    escrituras = [s for s in rama if s[0] in ("recordado", "registrado")]
    assert escrituras == [("recordado", _TRANSCRIPCION, "audio")]


def test_mp28_el_acuse_llega_antes_de_que_termine_la_transcripcion(rama):
    """Transcribir es lo más lento del turno: el acuse está para cubrirlo.

    Se lanza antes y no la espera, así que llega en cuanto la
    transcripción cede el turno. Si se lanzara después, o se esperara
    dentro, llegaría con la respuesta encima.
    """
    _atender(_AUDIO)

    orden = [s[0] for s in rama]
    assert orden.index("enviado") < orden.index("transcrito")


def test_mp28_si_el_acuse_falla_la_nota_se_atiende_igual(rama, monkeypatch):
    """Es un acompañamiento, no el contenido: su fallo no tumba el turno."""
    async def _falla(destino, texto):
        raise RuntimeError("Meta no respondió")

    monkeypatch.setattr(espera, "enviar_texto", _falla)
    _atender(_AUDIO)

    assert ("recordado", _TRANSCRIPCION, "audio") in rama


def test_mp28_sin_consentimiento_no_hay_acuse_ni_transcripcion(rama, monkeypatch):
    """Transcribir antes de la compuerta sería mandar a Gemini la voz de
    alguien que no ha autorizado (ADR-0006), y el acuse va con ella."""
    async def _sin_autorizar(identidad, texto, boton_id):
        return None

    monkeypatch.setattr(dispatcher, "compuerta", _sin_autorizar)
    _atender(_AUDIO)

    assert rama == []
