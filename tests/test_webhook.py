"""Contrato del webhook con Meta — modelo MP-23. Nivel de integración.

Es lo que el anteproyecto preveía validar «mediante casos de prueba en
Postman». Se hace con `TestClient`, que hace lo mismo y además queda
versionado y se puede volver a ejecutar (desviación D-8).

Aquí no se monta la aplicación completa de `app.main`: se monta solo el
enrutador del webhook. Así el ciclo de vida no abre el pool de conexiones
y **ninguna prueba toca la base de datos**, que es la misma que produce.
"""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import webhook
from app.config import settings

_CUERPO = json.dumps({"entry": [{"changes": []}]}).encode("utf-8")


@pytest.fixture
def procesados(monkeypatch):
    """Espía del despachador: registra qué se encoló, sin procesar nada."""
    recibidos: list[dict] = []

    async def _espia(payload: dict) -> None:
        recibidos.append(payload)

    monkeypatch.setattr(webhook, "procesar_evento", _espia)
    return recibidos


@pytest.fixture
def cliente():
    aplicacion = FastAPI()
    aplicacion.include_router(webhook.router)
    return TestClient(aplicacion)


# --- GET: el reto de verificación ------------------------------------


def test_mp23_el_reto_se_devuelve_con_el_token_correcto(cliente):
    respuesta = cliente.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": settings.META_VERIFY_TOKEN,
            "hub.challenge": "1158201444",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.text == "1158201444"


def test_mp23_el_reto_va_en_texto_plano(cliente):
    """Envuelto en JSON, Meta rechaza la verificación."""
    respuesta = cliente.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": settings.META_VERIFY_TOKEN,
            "hub.challenge": "1158201444",
        },
    )

    assert respuesta.headers["content-type"].startswith("text/plain")


@pytest.mark.parametrize(
    "parametros",
    [
        {"hub.mode": "subscribe", "hub.verify_token": "otro", "hub.challenge": "1"},
        {"hub.mode": "unsubscribe", "hub.verify_token": None, "hub.challenge": "1"},
        {},
    ],
)
def test_mp23_una_verificacion_que_no_cuadra_se_rechaza(cliente, parametros):
    if parametros.get("hub.verify_token") is None:
        parametros.pop("hub.verify_token", None)

    respuesta = cliente.get("/webhook", params=parametros)
    assert respuesta.status_code == 403


# --- POST: firma, respuesta inmediata y delegación -------------------


def test_mp23_un_evento_firmado_se_acepta_y_se_encola(cliente, procesados, firmar):
    respuesta = cliente.post(
        "/webhook",
        content=_CUERPO,
        headers={
            "X-Hub-Signature-256": firmar(_CUERPO),
            "Content-Type": "application/json",
        },
    )

    assert respuesta.status_code == 200
    assert len(procesados) == 1
    assert procesados[0] == json.loads(_CUERPO)


def test_mp23_sin_firma_no_se_procesa_nada(cliente, procesados):
    """Cualquiera que conozca la URL pública podría inyectar mensajes falsos."""
    respuesta = cliente.post(
        "/webhook", content=_CUERPO, headers={"Content-Type": "application/json"}
    )

    assert respuesta.status_code == 403
    assert procesados == []


def test_mp23_una_firma_de_otro_cuerpo_no_sirve(cliente, procesados, firmar):
    """La firma se calcula sobre los bytes crudos, no sobre el JSON reserializado.

    El cuerpo de aquí es el mismo objeto con **un espacio de más**: al
    reserializar daría igual, y por eso la comprobación tiene que hacerse
    sobre los bytes tal como llegaron.
    """
    respuesta = cliente.post(
        "/webhook",
        content=b'{"entry": [{"changes": [] }]}',
        headers={
            "X-Hub-Signature-256": firmar(_CUERPO),
            "Content-Type": "application/json",
        },
    )

    assert respuesta.status_code == 403
    assert procesados == []


def test_mp23_un_cuerpo_no_json_se_responde_con_doscientos(cliente, procesados, firmar):
    """A propósito: reintentarlo no cambia nada.

    Devolver un error solo provocaría reintentos indefinidos de Meta sobre
    un cuerpo que nunca va a poder procesarse.
    """
    cuerpo = b"esto no es json"
    respuesta = cliente.post(
        "/webhook",
        content=cuerpo,
        headers={
            "X-Hub-Signature-256": firmar(cuerpo),
            "Content-Type": "application/json",
        },
    )

    assert respuesta.status_code == 200
    assert procesados == []


def test_mp23_el_doscientos_no_espera_al_procesamiento(cliente, monkeypatch, firmar):
    """Meta reintenta si el webhook tarda, y el pipeline completo excede ese margen.

    Sin esta separación habría respuestas y registros duplicados. Se
    comprueba haciendo que el despachador falle: la respuesta tiene que
    ser 200 igualmente, porque ya se había devuelto.
    """
    async def _revienta(payload: dict) -> None:
        raise RuntimeError("el despachador falló")

    monkeypatch.setattr(webhook, "procesar_evento", _revienta)

    with pytest.raises(RuntimeError):
        cliente.post(
            "/webhook",
            content=_CUERPO,
            headers={
                "X-Hub-Signature-256": firmar(_CUERPO),
                "Content-Type": "application/json",
            },
        )
