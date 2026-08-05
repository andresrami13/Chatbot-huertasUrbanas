"""Repositorio de datos (Fase 3, Tabla 2).

Único punto de acceso a Supabase. Aquí vive la **capa 1** del modelo de
seguridad —el filtrado por usuario_id—, que es la barrera de acceso real
del sistema, no el RLS (Fase 3, §5.1).

Sobre la identidad: las funciones reciben el número de teléfono en claro,
tal como llega de Meta, y calculan la huella internamente. Quien las
llama nunca manipula huellas ni ve datos cifrados. El número no se
almacena ni se registra en bitácora en ningún momento.

Estado actual: `usuario`, el catálogo `barrio`, la idempotencia del webhook,
el registro del CU3 (`huerta`, `cultivo` y su borrador) y la colección
oficial (`fuente`, `fragmento_oficial`). Falta `fragmento_comunitario` y
`mensaje`.
"""

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
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
class Fuente:
    """Un documento oficial curado (Fase 4, §5.1).

    Sus metadatos son los que se citan en la respuesta del CU2: la
    atribución `[OFICIAL – entidad, título]` sale de aquí, no del texto del
    fragmento.
    """

    id: UUID
    entidad: str
    titulo: str
    url: str | None


@dataclass(frozen=True)
class Usuaria:
    """Una usuaria ya identificada, con el nombre ya descifrado.

    Fuera de este módulo nadie trabaja con el texto cifrado.
    """

    id: UUID
    nombre: str | None
    consentimiento_en: datetime


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


# --- Borrador de registro (CU3, ADR-0008) -----------------------------
# Un borrador abandonado caduca. Un día es de sobra: si la usuaria no
# confirmó en 24 horas, lo más probable es que ya no recuerde qué iba a
# confirmar, y mostrarle luego un resumen viejo sería peor que olvidarlo.
_CADUCIDAD_BORRADOR_HORAS = 24


async def guardar_borrador(usuario_id: UUID, datos: dict) -> None:
    """Guarda o reemplaza el borrador pendiente de confirmación."""
    await obtener_pool().execute(
        """
        insert into registro_pendiente (usuario_id, datos)
             values ($1, $2::jsonb)
        on conflict (usuario_id) do update
                set datos = excluded.datos, creado_en = now()
        """,
        usuario_id,
        json.dumps(datos),
    )


async def obtener_borrador(usuario_id: UUID) -> dict | None:
    """Devuelve el borrador vigente, o None si no hay o ya caducó.

    Filtra por antigüedad en la propia consulta: un borrador caducado es
    como si no existiera, y así no hace falta acordarse de comprobarlo en
    cada sitio que lo lea.
    """
    fila = await obtener_pool().fetchrow(
        """
        select datos
          from registro_pendiente
         where usuario_id = $1
           and creado_en > now() - make_interval(hours => $2)
        """,
        usuario_id,
        _CADUCIDAD_BORRADOR_HORAS,
    )

    return json.loads(fila["datos"]) if fila else None


async def borrar_borrador(usuario_id: UUID) -> None:
    """Descarta el borrador, se haya guardado o no."""
    await obtener_pool().execute(
        "delete from registro_pendiente where usuario_id = $1", usuario_id
    )


async def limpiar_borradores() -> int:
    """Borra los borradores caducados. Se invoca al arrancar."""
    resultado = await obtener_pool().execute(
        """
        delete from registro_pendiente
         where creado_en < now() - make_interval(hours => $1)
        """,
        _CADUCIDAD_BORRADOR_HORAS,
    )

    borrados = int(resultado.rsplit(" ", 1)[-1]) if resultado else 0
    if borrados:
        logger.info("Borradores caducados borrados=%d", borrados)

    return borrados


# --- Huerta y cultivos (CU3) ------------------------------------------


async def guardar_huerta(
    usuario_id: UUID,
    barrio_codigo: str,
    nombre_huerta: str | None,
    cultivos: list[tuple[str, date | None, bool]],
) -> UUID:
    """Persiste el registro confirmado y devuelve el id de la huerta.

    Todo en una transacción: una huerta creada sin sus cultivos, o cultivos
    a medias, dejaría el dato peor que no haberlo guardado.

    **Reutiliza la huerta que ya tenga la usuaria** en lugar de crear otra
    (ADR-0008). El esquema admite varias por usuaria, pero el perfil real es
    una líder con una huerta: crear una nueva cada vez que menciona un
    cultivo le fragmentaría los datos y rompería la atribución del CU4, que
    es por huerta.

    `cultivos` son ternas (especie, fecha o None, fecha_imprecisa).
    """
    pool = obtener_pool()

    async with pool.acquire() as conexion:
        async with conexion.transaction():
            barrio_id = await conexion.fetchval(
                "select id from barrio where codigo = $1 and activo", barrio_codigo
            )
            if barrio_id is None:
                # El enum de la extracción sale de esta misma tabla, así que
                # esto solo puede pasar si el barrio se desactivó entre la
                # extracción y la confirmación.
                raise ValueError(f"Barrio desconocido o inactivo: {barrio_codigo!r}")

            # Capa 1 del modelo de seguridad: acotado por usuario_id.
            huerta_id = await conexion.fetchval(
                """
                select id from huerta
                 where usuario_id = $1
                 order by creado_en
                 limit 1
                """,
                usuario_id,
            )

            if huerta_id is None:
                huerta_id = await conexion.fetchval(
                    """
                    insert into huerta (usuario_id, barrio_id, nombre_huerta)
                         values ($1, $2, $3)
                      returning id
                    """,
                    usuario_id,
                    barrio_id,
                    nombre_huerta,
                )
                creada = True
            else:
                # coalesce: un dato nuevo completa el que faltara, pero un
                # null de esta extracción no borra lo que ya se sabía.
                await conexion.execute(
                    """
                    update huerta
                       set barrio_id     = $2,
                           nombre_huerta = coalesce($3, nombre_huerta)
                     where id = $1
                    """,
                    huerta_id,
                    barrio_id,
                    nombre_huerta,
                )
                creada = False

            for especie, fecha, imprecisa in cultivos:
                await conexion.execute(
                    """
                    insert into cultivo
                           (huerta_id, especie, fecha_siembra_aprox,
                            fecha_imprecisa)
                         values ($1, $2, $3, $4)
                    """,
                    huerta_id,
                    especie,
                    fecha,
                    imprecisa,
                )

    logger.info(
        "Registro guardado | usuario_id=%s | huerta_id=%s | nueva=%s | "
        "cultivos=%d",
        usuario_id,
        huerta_id,
        creada,
        len(cultivos),
    )

    # TODO (Fase 6, ADR-0004): regenerar el fragmento_comunitario de esta
    # huerta —texto y embedding— para que el CU4 la incluya.

    return huerta_id


# --- Colección oficial: fuente y sus fragmentos (Fase 4, §5.1) --------
#
# Quien las usa hoy es el script de ingesta (`scripts/ingesta_fuente.py`),
# que se ejecuta a mano y no forma parte del servicio. Viven aquí de todos
# modos porque este módulo es el único punto de acceso a Supabase: que el
# script leyera y escribiera por su cuenta duplicaría el conocimiento del
# esquema en dos sitios. Lo que sí se queda fuera de `app/` es `pypdf`.


def _a_literal_vector(vector: list[float]) -> str:
    """Formatea un embedding como literal de pgvector: `[0.1,0.2,...]`.

    asyncpg no conoce el tipo `vector`, que lo aporta la extensión, así que
    el valor viaja como texto y la consulta lo convierte con `::vector`.

    Se usa `repr` y no un formato de precisión fija porque `repr` de un
    float de Python va y vuelve sin perder un bit. Redondear aquí
    introduciría una diferencia entre el vector que se calculó y el que se
    almacena, invisible salvo como recuperación ligeramente peor.
    """
    return "[" + ",".join(repr(float(componente)) for componente in vector) + "]"


async def obtener_fuente_por_url(url: str) -> Fuente | None:
    """Busca una fuente ya ingerida por su URL.

    La URL es lo que identifica al documento en la práctica: el título y la
    entidad se pueden escribir de varias maneras. Sirve para que la ingesta
    detecte que ese PDF ya entró y no lo duplique.
    """
    fila = await obtener_pool().fetchrow(
        """
        select id, entidad, titulo, url
          from fuente
         where url = $1
        """,
        url,
    )

    if fila is None:
        return None

    return Fuente(
        id=fila["id"],
        entidad=fila["entidad"],
        titulo=fila["titulo"],
        url=fila["url"],
    )


async def crear_fuente(entidad: str, titulo: str, url: str | None) -> Fuente:
    """Registra un documento oficial y devuelve su fila."""
    fila = await obtener_pool().fetchrow(
        """
        insert into fuente (entidad, titulo, url)
             values ($1, $2, $3)
          returning id, entidad, titulo, url
        """,
        entidad,
        titulo,
        url,
    )

    logger.info("Fuente registrada | fuente_id=%s | entidad=%s", fila["id"], entidad)

    return Fuente(
        id=fila["id"],
        entidad=fila["entidad"],
        titulo=fila["titulo"],
        url=fila["url"],
    )


async def contar_fragmentos_oficiales(fuente_id: UUID) -> int:
    """Cuántos fragmentos tiene ya esa fuente."""
    return await obtener_pool().fetchval(
        "select count(*) from fragmento_oficial where fuente_id = $1",
        fuente_id,
    )


async def reemplazar_fragmentos_oficiales(
    fuente_id: UUID,
    fragmentos: list[tuple[int, str, list[float]]],
) -> int:
    """Sustituye por completo los fragmentos de una fuente.

    `fragmentos` son ternas (orden, contenido, embedding).

    Borrado e inserción van en **una transacción**. Si se hicieran por
    separado y la inserción fallara a mitad, la fuente quedaría sin
    fragmentos o con parte de ellos, y el CU2 respondería peor sin que nada
    lo indicara: el fallo del RAG no es una excepción, es una respuesta
    mediocre.

    Reemplazar entero, y no añadir, es lo que hace repetible la ingesta. Un
    segundo pase que insertara sin borrar duplicaría el corpus, y con top-k
    los duplicados se llevarían los cuatro puestos con el mismo texto.
    """
    pool = obtener_pool()

    async with pool.acquire() as conexion:
        async with conexion.transaction():
            await conexion.execute(
                "delete from fragmento_oficial where fuente_id = $1", fuente_id
            )

            await conexion.executemany(
                """
                insert into fragmento_oficial
                       (fuente_id, orden, contenido, embedding)
                     values ($1, $2, $3, $4::vector)
                """,
                [
                    (fuente_id, orden, contenido, _a_literal_vector(embedding))
                    for orden, contenido, embedding in fragmentos
                ],
            )

    logger.info(
        "Fragmentos oficiales escritos | fuente_id=%s | fragmentos=%d",
        fuente_id,
        len(fragmentos),
    )

    return len(fragmentos)


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
