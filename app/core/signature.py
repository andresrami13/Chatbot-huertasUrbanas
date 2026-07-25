"""Validación de la firma de las peticiones entrantes de Meta.

Meta firma el cuerpo de cada webhook con HMAC-SHA256 usando el App Secret.
Sin esta validación, cualquiera que conozca la URL pública podría inyectar
mensajes falsos en el sistema.

Corresponde a la capa 5 del modelo de seguridad (Fase 3, Tabla 3).
"""

import hashlib
import hmac

from app.config import settings


def firma_valida(cuerpo_crudo: bytes, cabecera_firma: str | None) -> bool:
    """Compara la firma recibida contra el HMAC calculado localmente.

    IMPORTANTE: el HMAC se calcula sobre los bytes crudos del cuerpo, no
    sobre el JSON reserializado. Reserializar cambia espacios y orden de
    claves, y la firma deja de coincidir.
    """
    if not cabecera_firma or not cabecera_firma.startswith("sha256="):
        return False

    firma_recibida = cabecera_firma.removeprefix("sha256=")
    firma_esperada = hmac.new(
        key=settings.META_APP_SECRET.encode("utf-8"),
        msg=cuerpo_crudo,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # compare_digest evita ataques de temporización.
    return hmac.compare_digest(firma_recibida, firma_esperada)
