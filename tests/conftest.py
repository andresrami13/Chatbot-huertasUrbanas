"""Entorno de prueba: variables falsas, puestas antes de importar `app`.

`app/config.py` valida al importarse y el servicio se niega a arrancar con
un `.env` incompleto. Eso es deliberado y no se toca, así que probar exige
un entorno completo —y **falso**—.

Que sean falsas no es un detalle de higiene: si las pruebas leyeran el
`.env` real, la huella de una identidad dependería del pepper de
producción y el resultado cambiaría de una máquina a otra. Aquí se fijan
en el entorno del proceso, que en pydantic-settings **gana** al archivo
`.env`, de modo que la prueba da lo mismo en el equipo del autor que en
integración continua.

Ninguna prueba de este directorio abre la base de datos, llama a Meta ni
llama a Gemini. Lo que necesita red o base vive en `scripts/`.
"""

import base64
import hashlib
import hmac
import os

import pytest

# 64 caracteres: el validador exige al menos 32. Valor constante a
# propósito, para que las huellas de las pruebas sean reproducibles.
_PEPPER_DE_PRUEBA = "pepper-de-prueba-no-usar-en-produccion-0123456789"

# 32 bytes exactos, que es lo que pide AES-256.
_CLAVE_DE_PRUEBA = base64.b64encode(bytes(range(32))).decode()

os.environ.update(
    {
        "META_VERIFY_TOKEN": "token-de-verificacion-de-prueba",
        "META_APP_SECRET": "secreto-de-aplicacion-de-prueba",
        "META_ACCESS_TOKEN": "token-de-acceso-de-prueba",
        "META_PHONE_NUMBER_ID": "000000000000000",
        "PHONE_HASH_PEPPER": _PEPPER_DE_PRUEBA,
        "NAME_ENCRYPTION_KEY": _CLAVE_DE_PRUEBA,
        "GEMINI_API_KEY": "clave-de-gemini-de-prueba",
        "DATABASE_URL": "postgresql://prueba:prueba@localhost:5432/prueba",
    }
)


@pytest.fixture
def firmar():
    """Firma un cuerpo como lo firmaría Meta, con el secreto de prueba.

    Vive aquí porque la necesitan dos archivos —el de la firma y el del
    contrato del webhook— y estaba copiada en los dos. Se importa **dentro**
    y no arriba: `app.config` se valida al importarse, y arriba correría
    antes de que este mismo archivo ponga las variables de entorno falsas.
    """
    from app.config import settings

    def _firmar(cuerpo: bytes) -> str:
        digest = hmac.new(
            key=settings.META_APP_SECRET.encode("utf-8"),
            msg=cuerpo,
            digestmod=hashlib.sha256,
        ).hexdigest()
        return f"sha256={digest}"

    return _firmar
