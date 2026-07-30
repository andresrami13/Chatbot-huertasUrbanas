"""Servicio de identidad y cifrado (Fase 3, Tabla 2 y §5.2).

Resuelve los datos personales del sistema:

- El **teléfono** nunca se almacena. Se convierte en un HMAC-SHA256 con
  un pepper secreto y se guarda solo esa huella. Es determinista a
  propósito: el mismo número produce siempre la misma huella, lo que
  permite reconocer a la usuaria en cada mensaje con una consulta
  directa, sin haber guardado nunca el número. El número en claro existe
  únicamente en memoria durante la petición.

- El **nombre** se cifra con AES-GCM del lado de la aplicación, de modo
  que la base solo almacena texto cifrado y la clave nunca viaja a
  Supabase ni aparece en sus registros de consultas.

- El **`wamid`** no parece un dato personal, pero lo es: lleva dentro el
  número de teléfono en ASCII, recuperable con un `base64 -d`. Se
  comprobó sobre un `wamid` real el 30/07/2026. Por eso nunca se registra
  ni se almacena en claro, sino a través de `huella_wamid`.

La información agronómica NO pasa por aquí: va en claro porque alimenta
la búsqueda vectorial y cifrarla rompería la recuperación.

Límite declarado (Fase 3, §5.3): esto protege frente a una fuga del
volcado de la base, no es cifrado de conocimiento cero. El operador del
backend tiene las claves en tiempo de ejecución.
"""

import base64
import hashlib
import hmac
import os
import re
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

# AES-GCM exige un nonce único por cifrado. 12 bytes es el tamaño
# recomendado por la especificación.
_TAMANO_NONCE = 12

# Rango de la E.164: entre 8 y 15 dígitos contando el indicativo.
_MIN_DIGITOS = 8
_MAX_DIGITOS = 15

_SOLO_DIGITOS = re.compile(r"\D")


def normalizar_telefono(numero: str) -> str:
    """Deja el número en dígitos, sin signos ni espacios.

    Meta entrega el número ya en este formato —`wa_id` y `from` llegan
    como '573001234567', sin el '+'—, así que en la práctica esta función
    no cambia nada. Se aplica igualmente porque la huella es determinista:
    si el mismo número entrara alguna vez con otro formato, produciría una
    huella distinta y la usuaria dejaría de ser reconocida.

    Cambiar esta normalización más adelante tiene el mismo efecto que
    cambiar el pepper.
    """
    digitos = _SOLO_DIGITOS.sub("", numero or "")

    if not (_MIN_DIGITOS <= len(digitos) <= _MAX_DIGITOS):
        # Sin incluir el número en el mensaje: acabaría en los registros.
        raise ValueError(
            f"Número de teléfono no válido: se esperaban entre "
            f"{_MIN_DIGITOS} y {_MAX_DIGITOS} dígitos, se recibieron "
            f"{len(digitos)}"
        )

    return digitos


def calcular_telefono_hash(numero: str) -> str:
    """Devuelve el HMAC-SHA256 del número en hexadecimal (64 caracteres).

    Coincide con la restricción CHECK de `usuario.telefono_hash`.
    """
    normalizado = normalizar_telefono(numero)

    return hmac.new(
        key=settings.PHONE_HASH_PEPPER.encode("utf-8"),
        msg=normalizado.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


# Etiqueta de dominio del HMAC. Separa el espacio de los `wamid` del de
# los teléfonos aunque compartan el pepper: así ninguna huella de un
# espacio puede coincidir con la del otro.
_DOMINIO_WAMID = "wamid:"

# Longitud de la referencia que va a la bitácora. 16 caracteres hex bastan
# para no confundir dos mensajes y caben en una línea de registro.
_LONGITUD_REFERENCIA = 16


def huella_wamid(wamid: str) -> str:
    """HMAC-SHA256 del `wamid` en hexadecimal (64 caracteres).

    Es la forma en la que el `wamid` puede guardarse o compararse sin
    arrastrar el teléfono que lleva dentro. Determinista, que es lo que la
    idempotencia necesita: el mismo `wamid` da siempre la misma huella, así
    que un reintento de Meta se reconoce igual de bien que con el valor en
    claro.

    Depende del pepper, con la misma consecuencia que el teléfono: si el
    pepper cambia, las huellas viejas dejan de coincidir. Para la
    idempotencia eso solo significa olvidar qué mensajes ya se procesaron.
    """
    return hmac.new(
        key=settings.PHONE_HASH_PEPPER.encode("utf-8"),
        msg=(_DOMINIO_WAMID + wamid).encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def referencia_wamid(wamid: str) -> str:
    """Identificador corto del mensaje, apto para la bitácora.

    Es el prefijo de `huella_wamid`, no un recorte del `wamid`: recortar el
    valor original seguiría exponiendo el teléfono, que va al principio.
    Derivarlo de la huella tiene además la ventaja de que una línea de
    registro se puede cruzar con la fila de la tabla de idempotencia
    comparando el prefijo.

    Lo que se pierde es poder buscar el mensaje en el panel de Meta, que
    exige el `wamid` completo. Se compensa con la marca de tiempo.
    """
    return huella_wamid(wamid)[:_LONGITUD_REFERENCIA]


@lru_cache(maxsize=1)
def _cifrador() -> AESGCM:
    """Instancia única del cifrador. La clave ya fue validada al arrancar."""
    return AESGCM(base64.b64decode(settings.NAME_ENCRYPTION_KEY))


def cifrar_nombre(nombre: str | None) -> bytes | None:
    """Cifra el nombre para `usuario.nombre_usuario_cifrado`.

    El resultado es `nonce || texto cifrado || etiqueta`. El nonce se
    guarda junto al dato porque no es secreto; lo que no puede repetirse
    es su valor, y por eso se genera uno nuevo en cada llamada.

    Devuelve None si no hay nombre: la columna admite nulos mientras la
    usuaria no lo haya dado.
    """
    if not nombre:
        return None

    nonce = os.urandom(_TAMANO_NONCE)
    cifrado = _cifrador().encrypt(nonce, nombre.encode("utf-8"), None)
    return nonce + cifrado


def descifrar_nombre(dato: bytes | None) -> str | None:
    """Descifra lo que produjo `cifrar_nombre`.

    Lanza `cryptography.exceptions.InvalidTag` si el dato fue alterado o
    si la clave no es la que lo cifró. No se captura a propósito: un
    fallo aquí significa que la clave cambió, y conviene que se note.
    """
    if not dato:
        return None

    nonce, cifrado = dato[:_TAMANO_NONCE], dato[_TAMANO_NONCE:]
    return _cifrador().decrypt(nonce, cifrado, None).decode("utf-8")
