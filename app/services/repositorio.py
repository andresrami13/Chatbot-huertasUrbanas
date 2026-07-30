"""Repositorio de datos (Fase 3, Tabla 2).

Único punto de acceso a Supabase. Aquí vive la **capa 1** del modelo de
seguridad —el filtrado por usuario_id—, que es la barrera de acceso real
del sistema, no el RLS (Fase 3, §5.1).

Sobre la identidad: las funciones reciben el número de teléfono en claro,
tal como llega de Meta, y calculan la huella internamente. Quien las
llama nunca manipula huellas ni ve datos cifrados. El número no se
almacena ni se registra en bitácora en ningún momento.

Estado actual: `usuario` y el catálogo `barrio`. Las funciones de huerta y
cultivo llegan con el flujo de registro (CU3).
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.core.basedatos import obtener_pool
from app.core.identidad import (
    calcular_telefono_hash,
    cifrar_nombre,
    descifrar_nombre,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Barrio:
    """Una fila del catálogo de barrios (ADR-0002)."""

    id: int
    codigo: str
    nombre: str


@dataclass(frozen=True)
class Usuaria:
    """Una usuaria ya identificada, con el nombre ya descifrado.

    Fuera de este módulo nadie trabaja con el texto cifrado.
    """

    id: UUID
    nombre: str | None
    consentimiento_en: datetime


async def listar_barrios() -> list[Barrio]:
    """Devuelve los barrios activos del catálogo, en orden alfabético.

    Es la fuente del enum de la extracción: el prompt y el esquema de la
    salida estructurada se generan leyendo esta tabla, nunca con la lista
    escrita a mano (ADR-0002). Añadir un barrio es un INSERT y el extractor
    lo recoge sin tocar código.

    No lleva filtro por usuario_id porque el catálogo no es de nadie: es la
    única tabla del sistema sin dueño.
    """
    filas = await obtener_pool().fetch(
        """
        select id, codigo, nombre
          from barrio
         where activo
         order by nombre
        """
    )

    return [
        Barrio(id=fila["id"], codigo=fila["codigo"], nombre=fila["nombre"])
        for fila in filas
    ]


async def buscar_usuaria(telefono: str) -> Usuaria | None:
    """Busca a la usuaria por su número.

    Devuelve None si no está registrada, que en este sistema equivale a
    que **no ha dado su consentimiento**: la fila solo existe si autorizó
    (CU1). La compuerta de consentimiento se apoya en esto.
    """
    huella = calcular_telefono_hash(telefono)

    fila = await obtener_pool().fetchrow(
        """
        select id, nombre_usuario_cifrado, consentimiento_en
          from usuario
         where telefono_hash = $1
        """,
        huella,
    )

    if fila is None:
        return None

    return Usuaria(
        id=fila["id"],
        nombre=descifrar_nombre(fila["nombre_usuario_cifrado"]),
        consentimiento_en=fila["consentimiento_en"],
    )


async def registrar_consentimiento(
    telefono: str,
    nombre: str | None = None,
) -> Usuaria:
    """Crea la fila de la usuaria, que ES el registro de su consentimiento.

    Deliberadamente NO existe un `buscar_o_crear`: crear la fila equivale
    a registrar la autorización, y eso solo puede ocurrir cuando la
    usuaria pulsa [Acepto]. Un método que creara la fila de paso, al
    buscarla, saltaría la compuerta del CU1 sin que se notara.

    Es idempotente: si ya existe, no duplica ni pisa la fecha original de
    consentimiento, que es la constancia legal (Ley 1581). Un nombre
    nuevo sí completa el que faltara.
    """
    huella = calcular_telefono_hash(telefono)
    cifrado = cifrar_nombre(nombre)

    fila = await obtener_pool().fetchrow(
        """
        insert into usuario (telefono_hash, nombre_usuario_cifrado)
             values ($1, $2)
        on conflict (telefono_hash) do update
                set nombre_usuario_cifrado = coalesce(
                        excluded.nombre_usuario_cifrado,
                        usuario.nombre_usuario_cifrado)
          returning id, nombre_usuario_cifrado, consentimiento_en
        """,
        huella,
        cifrado,
    )

    # El usuario_id es un UUID sin relación con el número: puede
    # registrarse sin exponer datos personales.
    logger.info("Consentimiento registrado | usuario_id=%s", fila["id"])

    return Usuaria(
        id=fila["id"],
        nombre=descifrar_nombre(fila["nombre_usuario_cifrado"]),
        consentimiento_en=fila["consentimiento_en"],
    )
