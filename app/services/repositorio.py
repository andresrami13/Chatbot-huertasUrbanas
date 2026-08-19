"""Repositorio de datos (Fase 3, Tabla 2).

Único punto de acceso a Supabase. Aquí vive la **capa 1** del modelo de
seguridad —el filtrado por usuario_id—, que es la barrera de acceso real
del sistema, no el RLS (Fase 3, §5.1).

Sobre la identidad: las funciones reciben el número de teléfono en claro,
tal como llega de Meta, y calculan la huella internamente. Quien las
llama nunca manipula huellas ni ve datos cifrados. El número no se
almacena ni se registra en bitácora en ningún momento.

Estado actual: `usuario`, el catálogo `barrio`, la idempotencia del webhook,
el registro del CU3 (`huerta`, `cultivo` y su borrador), las dos colecciones
vectoriales (`fuente`, `fragmento_oficial`, `fragmento_comunitario`) y la
memoria de conversación (`mensaje`). El esquema queda cubierto entero.
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


# --- Saludo personalizado (ADR-0016) ----------------------------------
# Cada cuánto se le antepone el nombre a la respuesta. Se mide en horas
# desde el último movimiento de la conversación, no por día calendario:
# quien escribe a las 23:50 y vuelve a las 00:10 no está empezando una
# conversación nueva.
_HORAS_ENTRE_SALUDOS = 24


async def nombre_para_saludo(usuario_id: UUID) -> str | None:
    """El nombre de pila si toca saludarla, o None si no toca.

    La condición es que el mensaje entrante **sea el único** de las últimas
    24 horas. Se cuentan los de los dos roles a propósito: en cuanto se le
    responde una vez queda una fila del asistente, así que dos respuestas
    seguidas dentro del mismo turno no la saludan dos veces. Y como el
    mensaje entrante se registra antes de atenderlo (ADR-0012), en el turno
    de vuelta el conteo vale exactamente 1.

    Devuelve None si no tiene nombre, que es lo que ocurre mientras no
    conteste la primera pregunta del onboarding.

    El nombre sale descifrado, como en el resto del módulo: fuera de aquí
    nadie ve el texto cifrado.
    """
    fila = await obtener_pool().fetchrow(
        """
        select u.nombre_usuario_cifrado,
               (select count(*)
                  from mensaje m
                 where m.usuario_id = u.id
                   and m.creado_en > now() - make_interval(hours => $2)
               ) as recientes
          from usuario u
         where u.id = $1
        """,
        usuario_id,
        _HORAS_ENTRE_SALUDOS,
    )

    if fila is None or fila["recientes"] != 1:
        return None

    return descifrar_nombre(fila["nombre_usuario_cifrado"])


# --- Onboarding en curso (ADR-0016) -----------------------------------
# Caduca con el mismo criterio que el borrador del CU3, y con una
# consecuencia distinta: al volver pasadas 24 horas se repiten las tres
# preguntas y lo que conteste sobrescribe lo que hubiera. Es más simple
# que llevar la cuenta de qué había contestado, y el coste son dos
# preguntas cortas.
_CADUCIDAD_ONBOARDING_HORAS = 24


@dataclass(frozen=True)
class OnboardingEnCurso:
    """El punto en el que va el onboarding de una usuaria."""

    paso: str
    datos: dict


async def guardar_onboarding(usuario_id: UUID, paso: str, datos: dict) -> None:
    """Crea o actualiza el estado del onboarding.

    `creado_en` no se toca al actualizar: la caducidad se mide sobre
    `actualizado_en`, que es lo que refleja cuándo habló ella por última
    vez dentro del onboarding.
    """
    await obtener_pool().execute(
        """
        insert into onboarding_pendiente (usuario_id, paso, datos)
             values ($1, $2, $3::jsonb)
        on conflict (usuario_id) do update
                set paso           = excluded.paso,
                    datos          = excluded.datos,
                    actualizado_en = now()
        """,
        usuario_id,
        paso,
        json.dumps(datos),
    )


async def obtener_onboarding(usuario_id: UUID) -> OnboardingEnCurso | None:
    """El onboarding vigente, o None si no hay o ya caducó.

    Filtra por antigüedad en la propia consulta, igual que el borrador del
    CU3: uno caducado es como si no existiera, y así no hay que acordarse
    de comprobarlo en cada sitio que lo lea.
    """
    fila = await obtener_pool().fetchrow(
        """
        select paso, datos
          from onboarding_pendiente
         where usuario_id = $1
           and actualizado_en > now() - make_interval(hours => $2)
        """,
        usuario_id,
        _CADUCIDAD_ONBOARDING_HORAS,
    )

    if fila is None:
        return None

    return OnboardingEnCurso(paso=fila["paso"], datos=json.loads(fila["datos"]))


async def borrar_onboarding(usuario_id: UUID) -> None:
    """Cierra el onboarding, se haya completado o no."""
    await obtener_pool().execute(
        "delete from onboarding_pendiente where usuario_id = $1", usuario_id
    )


async def limpiar_onboardings() -> int:
    """Borra los onboarding caducados. Se invoca al arrancar."""
    resultado = await obtener_pool().execute(
        """
        delete from onboarding_pendiente
         where actualizado_en < now() - make_interval(hours => $1)
        """,
        _CADUCIDAD_ONBOARDING_HORAS,
    )

    borrados = int(resultado.rsplit(" ", 1)[-1]) if resultado else 0
    if borrados:
        logger.info("Onboarding caducados borrados=%d", borrados)

    return borrados


# --- Huerta y cultivos (CU3) ------------------------------------------


async def guardar_huerta(
    usuario_id: UUID,
    barrio_codigo: str,
    nombre_huerta: str | None,
    especies: list[str],
) -> UUID:
    """Persiste el registro confirmado y devuelve el id de la huerta.

    Todo en una transacción: una huerta creada sin sus cultivos, o cultivos
    a medias, dejaría el dato peor que no haberlo guardado.

    **Reutiliza la huerta que ya tenga la usuaria** en lugar de crear otra
    (ADR-0008). El esquema admite varias por usuaria, pero el perfil real es
    una líder con una huerta: crear una nueva cada vez que menciona un
    cultivo le fragmentaría los datos y rompería la atribución del CU4, que
    es por huerta.

    `especies` son los nombres de las plantas, y nada más: la fecha de
    siembra salió de `cultivo` en la migración 008 (ADR-0018).
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

            for especie in especies:
                await conexion.execute(
                    "insert into cultivo (huerta_id, especie) values ($1, $2)",
                    huerta_id,
                    especie,
                )

    logger.info(
        "Registro guardado | usuario_id=%s | huerta_id=%s | nueva=%s | "
        "cultivos=%d",
        usuario_id,
        huerta_id,
        creada,
        len(cultivos),
    )

    # El fragmento comunitario lo regenera quien llama, después de que esta
    # transacción cierre (ADR-0004). No se hace aquí a propósito: exige una
    # llamada de red al modelo de embeddings, y dejarla dentro tendría la
    # base bloqueada esperando a un tercero.
    return huerta_id


@dataclass(frozen=True)
class HuertaDeUsuaria:
    """La huerta de una usuaria, con su barrio ya resuelto.

    Desde el ADR-0016 la existencia de esta fila significa que **completó el
    onboarding**, no que haya registrado algún cultivo. Antes significaba lo
    segundo, y el matiz importa: hoy una huerta sin cultivos es lo normal
    justo después del onboarding, no una anomalía.
    """

    id: UUID
    nombre_huerta: str | None
    barrio_codigo: str
    barrio_nombre: str


async def obtener_huerta_de_usuaria(usuario_id: UUID) -> HuertaDeUsuaria | None:
    """La huerta de la usuaria, o None si todavía no completó el onboarding.

    Es el indicador de onboarding completado (ADR-0016, decisión 3), y por
    eso lo consultan tanto el despachador —para decidir si arranca el
    onboarding— como el CU3 conversacional, que necesita el barrio y el
    nombre para componer el resumen sin volver a preguntarlos.

    Capa 1 del modelo de seguridad: acotado por `usuario_id`.
    """
    fila = await obtener_pool().fetchrow(
        """
        select h.id,
               h.nombre_huerta,
               b.codigo as barrio_codigo,
               b.nombre as barrio_nombre
          from huerta h
          join barrio b on b.id = h.barrio_id
         where h.usuario_id = $1
         order by h.creado_en
         limit 1
        """,
        usuario_id,
    )

    if fila is None:
        return None

    return HuertaDeUsuaria(
        id=fila["id"],
        nombre_huerta=fila["nombre_huerta"],
        barrio_codigo=fila["barrio_codigo"],
        barrio_nombre=fila["barrio_nombre"],
    )


async def agregar_cultivos(
    usuario_id: UUID,
    especies: list[str],
) -> UUID | None:
    """Añade cultivos a la huerta que ya existe. Devuelve su id.

    Es lo que persiste el CU3 conversacional desde el ADR-0016: el barrio y
    el nombre de la huerta los fijó el onboarding, así que aquí solo entran
    cultivos y no hace falta tocar la fila de `huerta`.

    Devuelve `None` si la usuaria no tiene huerta, es decir, si no completó
    el onboarding. No la crea: crear una huerta sin barrio confirmado por
    ella sería saltarse el §4.7.

    `especies` son los nombres de las plantas (ADR-0018).
    """
    pool = obtener_pool()

    async with pool.acquire() as conexion:
        async with conexion.transaction():
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
                return None

            for especie in especies:
                await conexion.execute(
                    "insert into cultivo (huerta_id, especie) values ($1, $2)",
                    huerta_id,
                    especie,
                )

            # La huerta cambió aunque su fila no: el CU4 ordena por esta
            # marca (`listar_fragmentos_comunitarios_recientes`), y sin
            # tocarla una huerta que acaba de sumar cultivos se hundiría en
            # el listado.
            await conexion.execute(
                "update huerta set actualizado_en = now() where id = $1",
                huerta_id,
            )

    logger.info(
        "Cultivos añadidos | usuario_id=%s | huerta_id=%s | cultivos=%d",
        usuario_id,
        huerta_id,
        len(cultivos),
    )

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


async def listar_contenidos_oficiales(
    excluir_fuente_id: UUID | None = None,
) -> list[tuple[str, str]]:
    """Devuelve el texto de los fragmentos oficiales ya ingeridos.

    Pares (título de la fuente, contenido). **Sin el embedding**, que aquí
    no hace falta y son 768 flotantes por fila.

    Lo usa la comprobación de casi duplicados de la ingesta, que compara un
    documento nuevo contra el corpus antes de escribirlo. `excluir_fuente_id`
    deja fuera la propia fuente cuando se está reingiriendo: si no, cada
    fragmento se encontraría a sí mismo.

    No la usa el servicio en producción: recuperar es cosa de
    `buscar_fragmentos_oficiales`, que filtra por similitud. Esta trae el
    corpus entero y solo tiene sentido ejecutándose a mano.
    """
    filas = await obtener_pool().fetch(
        """
        select f.titulo, o.contenido
          from fragmento_oficial o
          join fuente f on f.id = o.fuente_id
         where $1::uuid is null or o.fuente_id <> $1
         order by o.fuente_id, o.orden
        """,
        excluir_fuente_id,
    )

    return [(fila["titulo"], fila["contenido"]) for fila in filas]


@dataclass(frozen=True)
class FragmentoOficial:
    """Un fragmento recuperado, con la fuente que lo respalda.

    La entidad y el título viajan con el fragmento porque la respuesta del
    CU2 tiene que citarlos (Fase 2, §5.3). No están en el texto vectorizado
    a propósito (ADR-0009): se recuperan por la clave foránea.
    """

    contenido: str
    similitud: float
    entidad: str
    titulo: str


async def buscar_fragmentos_oficiales(
    consulta: list[float],
    top_k: int,
    umbral: float,
) -> list[FragmentoOficial]:
    """Recupera los fragmentos oficiales más parecidos a la consulta.

    **Cuidado con el operador:** `<=>` de pgvector devuelve *distancia*
    coseno, no similitud. Una similitud de 0.68 es una distancia de 0.32, y
    confundirlo invierte el filtro sin dar ningún error: devolvería
    justamente los fragmentos que no vienen a cuento. Por eso el umbral se
    convierte una sola vez, aquí, y de puertas afuera del repositorio todo
    se habla en similitud, que es como lo enuncian la Fase 4 y CLAUDE.md §8.

    El orden es por distancia ascendente, es decir, por similitud
    descendente: el primero es el más pertinente.

    No lleva filtro por `usuario_id` y es correcto: la colección oficial no
    es de nadie, como el catálogo de barrios. La capa 1 del modelo de
    seguridad aplica a los datos de las usuarias, y aquí no hay ninguno.
    """
    literal = _a_literal_vector(consulta)

    filas = await obtener_pool().fetch(
        """
        select f.contenido,
               1 - (f.embedding <=> $1::vector) as similitud,
               s.entidad,
               s.titulo
          from fragmento_oficial f
          join fuente s on s.id = f.fuente_id
         where f.embedding <=> $1::vector <= $2
         order by f.embedding <=> $1::vector
         limit $3
        """,
        literal,
        1 - umbral,
        top_k,
    )

    return [
        FragmentoOficial(
            contenido=fila["contenido"],
            similitud=fila["similitud"],
            entidad=fila["entidad"],
            titulo=fila["titulo"],
        )
        for fila in filas
    ]



# --- Colección comunitaria: el dato de las huertas (ADR-0004, ADR-0011) ---


@dataclass(frozen=True)
class FragmentoComunitario:
    """Un fragmento comunitario recuperado, con su huerta y su barrio.

    El nombre y el barrio **no están en el texto vectorizado** (ADR-0011):
    llegan por la clave foránea, igual que la entidad y el título en la
    colección oficial. Son los que forman la etiqueta
    `[COMUNITARIO – huerta, barrio]`, sin la cual la usuaria creería que
    todo lo recuperado se siembra en su propio barrio (ADR-0001).

    Solo campos compartibles. Ningún dato personal sale de aquí.
    """

    contenido: str
    similitud: float
    nombre_huerta: str | None
    barrio: str


async def listar_cultivos_de_huerta(huerta_id: UUID) -> list[str]:
    """Especies sembradas en una huerta, sin repetir y en orden de siembra.

    Es la fuente del texto del fragmento comunitario. Se lee de `cultivo`,
    que es la fuente de verdad del dato agronómico (ADR-0004); el fragmento
    es un derivado que se reconstruye entero desde aquí.
    """
    filas = await obtener_pool().fetch(
        """
        select distinct on (lower(especie)) especie
          from cultivo
         where huerta_id = $1
         order by lower(especie), creado_en
        """,
        huerta_id,
    )

    return [fila["especie"] for fila in filas]


async def guardar_fragmento_comunitario(
    huerta_id: UUID,
    contenido: str,
    embedding: list[float],
) -> None:
    """Crea o reemplaza el fragmento de una huerta.

    Un fragmento por huerta, garantizado por el `unique` de la columna
    (ADR-0004). El `on conflict` lo reemplaza entero, texto y vector: no hay
    actualización incremental, porque el fragmento se reconstruye desde
    `cultivo` cada vez que la huerta cambia.
    """
    await obtener_pool().execute(
        """
        insert into fragmento_comunitario (huerta_id, contenido, embedding)
             values ($1, $2, $3::vector)
        on conflict (huerta_id) do update
                set contenido = excluded.contenido,
                    embedding = excluded.embedding
        """,
        huerta_id,
        contenido,
        _a_literal_vector(embedding),
    )

    logger.info("Fragmento comunitario guardado | huerta_id=%s", huerta_id)


async def buscar_fragmentos_comunitarios(
    consulta: list[float],
    top_k: int,
    umbral: float,
    excluir_usuario: UUID | None = None,
) -> list[FragmentoComunitario]:
    """Recupera lo que siembran otras huertas.

    `excluir_usuario` deja fuera la huerta de quien pregunta. No es un
    detalle cosmético: el CU4 es "qué siembran **otras** huertas", y
    devolverle la suya propia como dato comunitario sería contarle lo que
    ella misma registró.

    **Sin filtro por barrio**, deliberadamente (ADR-0001): la búsqueda
    recorre todas las huertas y el barrio solo se informa en la atribución.

    Aquí no hay dato personal: se seleccionan únicamente las columnas
    compartibles, que es la capa 4 del modelo de seguridad (Fase 3, §5).
    """
    filas = await obtener_pool().fetch(
        """
        select f.contenido,
               1 - (f.embedding <=> $1::vector) as similitud,
               h.nombre_huerta,
               b.nombre as barrio
          from fragmento_comunitario f
          join huerta h on h.id = f.huerta_id
          join barrio b on b.id = h.barrio_id
         where f.embedding <=> $1::vector <= $2
           and ($4::uuid is null or h.usuario_id <> $4)
         order by f.embedding <=> $1::vector
         limit $3
        """,
        _a_literal_vector(consulta),
        1 - umbral,
        top_k,
        excluir_usuario,
    )

    return [
        FragmentoComunitario(
            contenido=fila["contenido"],
            similitud=fila["similitud"],
            nombre_huerta=fila["nombre_huerta"],
            barrio=fila["barrio"],
        )
        for fila in filas
    ]


async def listar_fragmentos_comunitarios_recientes(
    top_k: int,
    excluir_usuario: UUID | None = None,
) -> list[FragmentoComunitario]:
    """Las huertas actualizadas más recientemente, sin buscar por similitud.

    Es el respaldo del CU4 para la pregunta general —"qué están sembrando
    las otras huertas"—, que **no es una búsqueda sino un listado**: una
    lista de especies se parece poco a esa frase, por muy pertinente que
    sea la respuesta. Ver `recuperacion.recuperar_comunidad`.

    Se ordena por fecha de actualización y no al azar para que dos
    preguntas seguidas den la misma respuesta, y para que lo que se muestre
    sea lo último que alguien contó.
    """
    filas = await obtener_pool().fetch(
        """
        select f.contenido,
               h.nombre_huerta,
               b.nombre as barrio
          from fragmento_comunitario f
          join huerta h on h.id = f.huerta_id
          join barrio b on b.id = h.barrio_id
         where ($2::uuid is null or h.usuario_id <> $2)
         order by f.actualizado_en desc
         limit $1
        """,
        top_k,
        excluir_usuario,
    )

    return [
        FragmentoComunitario(
            contenido=fila["contenido"],
            # No hay similitud que informar: no se buscó por parecido.
            # Ponerle un número inventado haría que la bitácora de
            # calibración mezclara medidas con relleno.
            similitud=float("nan"),
            nombre_huerta=fila["nombre_huerta"],
            barrio=fila["barrio"],
        )
        for fila in filas
    ]


async def listar_huertas_para_regenerar() -> list[UUID]:
    """Ids de todas las huertas, para el script de regeneración."""
    filas = await obtener_pool().fetch("select id from huerta order by creado_en")
    return [fila["id"] for fila in filas]


# --- Memoria de conversación (Fase 3, Tabla 1; ADR-0012) --------------


@dataclass(frozen=True)
class Turno:
    """Un mensaje de la conversación, tal como lo lee el agente.

    Solo el rol y el contenido: es lo único que entra en el prompt. El
    `tipo` y la marca de tiempo se guardan en la tabla, pero para el
    análisis de la Fase 7 —cuánto se usa la voz—, no para el modelo.
    """

    rol: str
    contenido: str


async def registrar_mensaje(
    usuario_id: UUID,
    rol: str,
    contenido: str,
    tipo: str = "text",
    huella: str | None = None,
) -> None:
    """Añade un mensaje a la memoria de la usuaria.

    `on conflict do nothing` y no un insert a secas: la garantía del
    ADR-0005 es **al menos una vez**. Si el proceso muere entre el final
    del trabajo y `marcar_procesado`, Meta reintenta y el mismo mensaje se
    procesa dos veces; sin esa cláusula el segundo insert chocaría con el
    índice único y tumbaría el reintento entero, que es justo la rama que
    el ADR-0005 existe para proteger.

    La huella puede faltar: si el envío a WhatsApp falla no hay wamid que
    guardar, y la columna admite nulos porque en PostgreSQL varios nulos no
    chocan entre sí bajo un índice único.

    Solo se llama después de la compuerta —siempre hay `usuario_id`—, así
    que ninguna fila de esta tabla pertenece a quien no ha autorizado.
    """
    await obtener_pool().execute(
        """
        insert into mensaje (usuario_id, rol, tipo, contenido, huella_wamid)
             values ($1, $2, $3, $4, $5)
        on conflict (huella_wamid) do nothing
        """,
        usuario_id,
        rol,
        tipo,
        contenido,
        huella,
    )


async def ultimos_mensajes(usuario_id: UUID, limite: int) -> list[Turno]:
    """La ventana de memoria, del más antiguo al más reciente.

    En orden cronológico porque es como se le entrega al modelo, y el
    último de la lista es el mensaje que la usuaria acaba de mandar.

    Capa 1 del modelo de seguridad: acotado por `usuario_id`. Es lo que
    impide que la conversación de una usuaria aparezca en la de otra.

    El desempate por `rol` importa poco pero es gratis: si la pregunta y la
    respuesta cayeran en la misma marca de tiempo, sin él podrían salir en
    orden invertido y el agente leería que se contestó antes de preguntar.
    Ascendente porque 'asistente' va antes que 'usuaria' en el alfabeto, y
    esta consulta se lee al revés.
    """
    filas = await obtener_pool().fetch(
        """
        select rol, contenido
          from mensaje
         where usuario_id = $1
         order by creado_en desc, rol asc
         limit $2
        """,
        usuario_id,
        limite,
    )

    return [
        Turno(rol=fila["rol"], contenido=fila["contenido"])
        for fila in reversed(filas)
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
