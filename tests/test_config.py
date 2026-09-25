"""Que el servicio se niegue a arrancar mal configurado — modelo MP-22.

Estas validaciones existen para que un fallo de configuración aparezca al
arrancar y no al registrar a la primera usuaria, que es mucho más tarde y
mucho más difícil de diagnosticar. Probarlas es probar ese adelanto.

Riesgo P-12: el modelo generativo desalineado, que el 08/09/2026 invalidó
una medición del enrutamiento.
"""

import base64

import pytest
from pydantic import ValidationError

from app.config import Settings, settings


def test_mp22_la_configuracion_de_prueba_es_valida():
    """Punto de partida: sin esto, cualquier otro fallo sería ambiguo."""
    assert Settings().PHONE_HASH_PEPPER


# --- Claves críticas e irrecuperables --------------------------------


@pytest.mark.parametrize("pepper", ["", "corto", "a" * 31])
def test_mp22_un_pepper_debil_no_arranca(pepper):
    """Valor límite: 31 caracteres no, 32 sí.

    Si el pepper cambia, las usuarias registradas dejan de ser
    reconocidas. Es irreversible, así que se valida al arrancar.
    """
    with pytest.raises(ValidationError):
        Settings(PHONE_HASH_PEPPER=pepper)


def test_mp22_treinta_y_dos_caracteres_bastan():
    assert Settings(PHONE_HASH_PEPPER="a" * 32).PHONE_HASH_PEPPER


@pytest.mark.parametrize(
    "clave",
    [
        "no-es-base64-!!",
        # 16 bytes: válido en base64, pero no es AES-256.
        base64.b64encode(bytes(16)).decode(),
        base64.b64encode(bytes(31)).decode(),
        base64.b64encode(bytes(33)).decode(),
    ],
)
def test_mp22_una_clave_de_cifrado_mal_formada_no_arranca(clave):
    with pytest.raises(ValidationError):
        Settings(NAME_ENCRYPTION_KEY=clave)


def test_mp22_treinta_y_dos_bytes_son_la_clave_correcta():
    assert Settings(NAME_ENCRYPTION_KEY=base64.b64encode(bytes(32)).decode())


@pytest.mark.parametrize("campo", ["META_VERIFY_TOKEN", "GEMINI_API_KEY"])
def test_mp22_las_credenciales_vacias_no_arrancan(campo):
    with pytest.raises(ValidationError):
        Settings(**{campo: "   "})


# --- El modelo generativo --------------------------------------------


def test_mp22_un_modelo_de_embeddings_no_sirve_como_generativo():
    """El error saldría en la primera conversación como una respuesta vacía.

    El modelo de embeddings no se configura por variable de entorno, y es
    deliberado (ADR-0007): cambiarlo invalidaría todos los vectores
    guardados sin dar ningún error, solo con peor recuperación.
    """
    with pytest.raises(ValidationError):
        Settings(GEMINI_GENERATIVE_MODEL="gemini-embedding-001")


def test_mp22_el_modelo_generativo_no_puede_ir_vacio():
    with pytest.raises(ValidationError):
        Settings(GEMINI_GENERATIVE_MODEL="  ")


def test_mp22_el_defecto_del_repositorio_es_un_modelo_generativo():
    """El defecto existe para dejar constancia de con qué se está corriendo.

    No se comprueba aquí *cuál* es —eso lo manda la variable de Railway y
    lo informa `/health`—, sino que sea utilizable.
    """
    assert settings.GEMINI_GENERATIVE_MODEL.strip()
    assert "embedding" not in settings.GEMINI_GENERATIVE_MODEL


# --- Parámetros calibrables ------------------------------------------


@pytest.mark.parametrize("umbral", [-0.1, 1.1, 2.0])
def test_mp22_un_umbral_fuera_de_rango_no_arranca(umbral):
    with pytest.raises(ValidationError):
        Settings(RAG_UMBRAL_SIMILITUD=umbral)


@pytest.mark.parametrize("umbral", [0.0, 0.66, 1.0])
def test_mp22_los_umbrales_en_rango_se_aceptan(umbral):
    """Valores límite del intervalo cerrado [0, 1]."""
    assert Settings(RAG_UMBRAL_SIMILITUD=umbral).RAG_UMBRAL_SIMILITUD == umbral


def test_mp22_la_validacion_del_umbral_no_atrapa_una_distancia():
    """Se declara lo que esta comprobación NO puede hacer.

    La distancia equivalente a 0.66 es 0.34, que está en rango y pasaría,
    dejando el CU2 respondiendo con los fragmentos que no vienen a cuento
    y sin dar ningún error. Contra eso solo protege leer el aviso del
    `.env.example`.
    """
    assert Settings(RAG_UMBRAL_SIMILITUD=0.34).RAG_UMBRAL_SIMILITUD == 0.34


@pytest.mark.parametrize("top_k", [0, -1])
def test_mp22_un_top_k_sin_sentido_no_arranca(top_k):
    with pytest.raises(ValidationError):
        Settings(RAG_TOP_K=top_k)


@pytest.mark.parametrize("campo", ["CU4_HUERTAS_POR_TANDA", "CU4_CULTIVOS_POR_HUERTA"])
def test_mp22_un_listado_de_cero_no_arranca(campo):
    """Cero fallaría en silencio: un listado vacío con su cola contando huertas."""
    with pytest.raises(ValidationError):
        Settings(**{campo: 0})


@pytest.mark.parametrize("ventana", [0, 1])
def test_mp22_una_ventana_de_memoria_inutil_no_arranca(ventana):
    """Con uno solo, el agente vería la pregunta en curso y nada de lo anterior."""
    with pytest.raises(ValidationError):
        Settings(MEMORIA_VENTANA_MENSAJES=ventana)


def test_mp22_dos_mensajes_es_el_minimo_admitido():
    assert Settings(MEMORIA_VENTANA_MENSAJES=2).MEMORIA_VENTANA_MENSAJES == 2


# --- La cadena de conexión -------------------------------------------


def test_mp22_el_transaction_pooler_no_arranca():
    """El puerto 6543 no admite prepared statements y rompe asyncpg.

    El fallo aparecería en ejecución con un mensaje difícil de relacionar
    con la causa, así que se corta al arrancar.
    """
    with pytest.raises(ValidationError):
        Settings(DATABASE_URL="postgresql://u:p@host.pooler.supabase.com:6543/db")


def test_mp22_el_session_pooler_se_acepta():
    assert Settings(DATABASE_URL="postgresql://u:p@host.pooler.supabase.com:5432/db")


@pytest.mark.parametrize("cadena", ["mysql://u:p@host/db", "host:5432", ""])
def test_mp22_lo_que_no_es_postgres_no_arranca(cadena):
    with pytest.raises(ValidationError):
        Settings(DATABASE_URL=cadena)
