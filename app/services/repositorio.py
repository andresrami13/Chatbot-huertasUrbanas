"""Repositorio de datos (Fase 3, Tabla 2).

Único punto de acceso a Supabase. Aquí vive la **capa 1** del modelo de
seguridad —el filtrado por usuario_id—, que es la barrera de acceso real
del sistema, no el RLS (Fase 3, §5.1).

Sobre la identidad: las funciones reciben el número de teléfono en claro,
tal como llega de Meta, y calculan la huella internamente. Quien las
llama nunca manipula huellas ni ve datos cifrados. El número no se
almacena ni se registra en bitácora en ningún momento.

Estado actual: `usuario`, el catálogo `barrio` y la idempotencia del
webhook. Las funciones de huerta y cultivo llegan con el flujo de registro
(CU3).
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


# --- Idempotencia del webhook (ADR-0005) ------------------------------
# Plazo del reclamo. Si un mensaje sigue en 'recibido' pasado este tiempo,
# se da por muerto el intento anterior y se vuelve a tomar.
#
# Tiene que ser holgadamente mayor que el procesamiento completo. El
# pipeline con transcripción medido en producción tardó 4,3 s; con agente y
# RAG será más. Cinco minutos deja margen de sobra y sigue permitiendo
# recuperar el mensaje dentro de la ventana de reintentos de Meta.
_PLAZO_RECLAMO_SEGUNDOS = 300

# Cuánto se conserva una fila. Los reintentos de Meta duran mucho menos,
# pero siete días es barato y coincide con la vida de un media_id.
_RETENCION_DIAS = 7


async def reclamar_wamid(huella: str) -> bool:
    """Intenta tomar un mensaje para procesarlo.

    Devuelve True si hay que procesarlo y False si debe descartarse.

    Es una sola sentencia a propósito: separar la consulta de la escritura
    abriría una carrera en la que dos entregas del mismo mensaje se
    reclamarían las dos. Los cuatro casos que resuelve:

    - No existe la fila: se inserta y se procesa.
    - Existe como 'procesado': es un duplicado real, se descarta.
    - Existe como 'recibido' y reciente: se está procesando ahora mismo (o
      Meta reintentó antes de que termináramos), se descarta.
    - Existe como 'recibido' y vencida: el intento anterior murió a mitad,
      se vuelve a tomar. **Es lo que evita la pérdida silenciosa.**
    """
    fila = await obtener_pool().fetchrow(
        """
        insert into idempotencia_webhook (wamid_huella, estado)
             values ($1, 'recibido')
        on conflict (wamid_huella) do update
                set recibido_en = now()
              where idempotencia_webhook.estado = 'recibido'
                and idempotencia_webhook.recibido_en
                    < now() - make_interval(secs => $2)
          returning wamid_huella
        """,
        huella,
        _PLAZO_RECLAMO_SEGUNDOS,
    )

    return fila is not None


async def marcar_procesado(huella: str) -> None:
    """Cierra el mensaje como terminado correctamente.

    Solo a partir de aquí un reintento de Meta cuenta como duplicado. Si el
    proceso muere entre el final del trabajo y esta llamada, el mensaje se
    reprocesará: la garantía es *al menos una vez*, no exactamente una.
    """
    await obtener_pool().execute(
        """
        update idempotencia_webhook
           set estado = 'procesado', procesado_en = now()
         where wamid_huella = $1
        """,
        huella,
    )


async def limpiar_idempotencia() -> int:
    """Borra las filas viejas y devuelve cuántas.

    Descarte por antigüedad, nunca vaciado completo: el conjunto en memoria
    que esta tabla sustituye se borraba entero al llegar a su límite y
    olvidaba también los mensajes vistos hacía segundos (ADR-0005, punto
    abierto 3).

    Se invoca al arrancar el servicio. Con el volumen del prototipo —5 a 7
    usuarias— la tabla no crece lo suficiente para necesitar más; si algún
    día lo hiciera, el sitio de una tarea periódica es este.
    """
    resultado = await obtener_pool().execute(
        """
        delete from idempotencia_webhook
         where recibido_en < now() - make_interval(days => $1)
        """,
        _RETENCION_DIAS,
    )

    # asyncpg devuelve la etiqueta de estado, del tipo "DELETE 12".
    borradas = int(resultado.rsplit(" ", 1)[-1]) if resultado else 0

    if borradas:
        logger.info("Idempotencia | filas caducadas borradas=%d", borradas)

    return borradas


async def contar_mensajes_atascados(minutos: int = 10) -> int:
    """Cuenta los mensajes tomados que nunca terminaron.

    Sirve de diagnóstico para el punto abierto 4 del ADR-0005: un redeploy
    de Railway a mitad de procesamiento mata la tarea en segundo plano. No
    se puede evitar sin una cola externa, descartada por presupuesto, pero
    con esto **deja de ser una pérdida silenciosa**: la fila queda en
    'recibido' y aquí se ve.
    """
    return await obtener_pool().fetchval(
        """
        select count(*)
          from idempotencia_webhook
         where estado = 'recibido'
           and recibido_en < now() - make_interval(mins => $1)
        """,
        minutos,
    )


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
