"""La capa de datos no cruza a una persona con otra — modelos MP-26 y MP-27.

RNF-07: el filtrado por `usuario_id` es la barrera principal del modelo de
seguridad (Fase 3, §5.1), y el RLS solo la respalda porque el backend usa
service role. RNF-08: la consulta comunitaria lee únicamente columnas
compartibles (capa 4).

Ninguna prueba abre la base. Todo el acceso a Supabase pasa por
`repositorio`, así que basta con sustituir el pool por un espía que anota
cada sentencia y sus argumentos: lo que se comprueba es qué SQL se manda y
con qué identificador, que es justo donde vive la barrera.
"""

import asyncio
import inspect
import re
from dataclasses import fields
from uuid import UUID

import pytest

from app.core.identidad import calcular_identidad_hash
from app.services import repositorio

_ELLA = UUID("00000000-0000-0000-0000-570000000601")
_SU_HUERTA = UUID("00000000-0000-0000-0000-570000000602")
_IDENTIDAD = "CO.570000000601"

# Tablas con dato de una persona concreta. `cultivo` no está: es dato
# agronómico compartible, y se acota por la huerta (ver `_comprobar`).
_TABLAS_PERSONALES = (
    "usuario", "huerta", "mensaje", "registro_pendiente",
    "onboarding_pendiente", "listado_comunitario_pendiente",
)


class _PoolEspia:
    """Anota cada sentencia. Devuelve lo mínimo para que la función siga.

    `select id from huerta` devuelve la huerta de ella, como haría la base
    con la consulta acotada; el resto de lecturas no encuentra nada.
    """

    def __init__(self, huerta_existente: bool = True) -> None:
        self.sentencias: list[tuple[str, tuple]] = []
        self._huerta_existente = huerta_existente

    def _anotar(self, sql: str, args: tuple) -> None:
        self.sentencias.append((" ".join(sql.split()), args))

    async def fetchval(self, sql, *args):
        self._anotar(sql, args)
        if "from barrio" in sql:
            return 1
        if "insert into huerta" in sql:
            return _SU_HUERTA
        if "from huerta" in sql:
            return _SU_HUERTA if self._huerta_existente else None
        return None

    async def fetchrow(self, sql, *args):
        self._anotar(sql, args)
        if "returning" in sql:
            return {"id": _ELLA, "nombre_usuario_cifrado": None, "consentimiento_en": None}
        return None

    async def fetch(self, sql, *args):
        self._anotar(sql, args)
        return []

    async def execute(self, sql, *args):
        self._anotar(sql, args)
        return "OK"

    def acquire(self):
        return _Contexto(self)

    def transaction(self):
        return _Contexto(self)


class _Contexto:
    def __init__(self, valor):
        self._valor = valor

    async def __aenter__(self):
        return self._valor

    async def __aexit__(self, *excepcion):
        return False


def _ejecutar(monkeypatch, llamada, pool=None):
    pool = pool or _PoolEspia()
    monkeypatch.setattr(repositorio, "obtener_pool", lambda: pool)
    asyncio.run(llamada())
    assert pool.sentencias, "La función no mandó ninguna sentencia"
    return pool.sentencias


def _columnas_del_insert(sql: str) -> list[str] | None:
    hallado = re.search(r"insert into \w+ \(([^)]*)\) values \(([^)]*)\)", sql)
    if not hallado:
        return None
    return [c.strip() for c in hallado.group(1).split(",")], [
        re.search(r"\$\d+", v).group(0) for v in hallado.group(2).split(",")
    ]


def _acotada(sql: str, args: tuple, valor, columna: str) -> bool:
    """`valor` llega como argumento y el SQL lo usa en `columna`, ya sea en
    una comparación o en el lugar de esa columna dentro de un insert."""
    if valor not in args:
        return False
    marcador = f"${args.index(valor) + 1}"
    if re.search(rf"\b{columna}\s*=\s*\{marcador}\b", sql):
        return True
    insert = _columnas_del_insert(sql)
    if insert:
        columnas, valores = insert
        return columna in columnas and valores[columnas.index(columna)] == marcador
    return False


def _comprobar(sentencias) -> None:
    """Toda sentencia sobre una tabla personal va acotada a ella.

    O por su `usuario_id`, o por el `id` de la huerta que devolvió una
    consulta ya acotada. Lo segundo cubre también `cultivo`: escribir en
    una huerta cuyo id no salió de ahí sería escribir en la de otra.
    """
    for sql, args in sentencias:
        tablas = set(re.findall(r"(?:from|into|update|join) (\w+)", sql))
        if "barrio" in tablas and len(tablas) == 1:
            continue
        por_ella = _acotada(sql, args, _ELLA, "usuario_id") or _acotada(sql, args, _ELLA, "id")
        por_su_huerta = (
            _acotada(sql, args, _SU_HUERTA, "id")
            or _acotada(sql, args, _SU_HUERTA, "huerta_id")
        )
        assert por_ella or por_su_huerta, f"Sentencia sin acotar: {sql}"


# --- MP-26: el filtrado por usuario_id (RNF-07) -----------------------
# Inventario exhaustivo: cada función pública del repositorio cae en una
# clase, y la clase decide qué se le exige.

# Leen o escriben el dato de una persona: acotadas por su usuario_id.
_DE_UNA_PERSONA = {
    "guardar_borrador": lambda: repositorio.guardar_borrador(_ELLA, {}),
    "obtener_borrador": lambda: repositorio.obtener_borrador(_ELLA),
    "borrar_borrador": lambda: repositorio.borrar_borrador(_ELLA),
    "nombre_para_saludo": lambda: repositorio.nombre_para_saludo(_ELLA),
    "guardar_onboarding": lambda: repositorio.guardar_onboarding(_ELLA, "nombre", {}),
    "obtener_onboarding": lambda: repositorio.obtener_onboarding(_ELLA),
    "borrar_onboarding": lambda: repositorio.borrar_onboarding(_ELLA),
    "obtener_desplazamiento_listado": lambda: repositorio.obtener_desplazamiento_listado(_ELLA),
    "guardar_desplazamiento_listado": lambda: repositorio.guardar_desplazamiento_listado(_ELLA, 3),
    "guardar_huerta": lambda: repositorio.guardar_huerta(_ELLA, "C1", None, ["tomate"]),
    "obtener_huerta_de_usuaria": lambda: repositorio.obtener_huerta_de_usuaria(_ELLA),
    "agregar_cultivos": lambda: repositorio.agregar_cultivos(_ELLA, ["tomate"]),
    "registrar_mensaje": lambda: repositorio.registrar_mensaje(_ELLA, "usuaria", "hola"),
    "ultimos_mensajes": lambda: repositorio.ultimos_mensajes(_ELLA, 10),
    "guardar_nombre": lambda: repositorio.guardar_nombre(_ELLA, "Ana"),
}

# Llegan a una persona por la huella de su identidad, que es lo único que
# se tiene antes de saber su usuario_id.
_POR_IDENTIDAD = {
    "buscar_usuaria": lambda: repositorio.buscar_usuaria(_IDENTIDAD),
    "registrar_consentimiento": lambda: repositorio.registrar_consentimiento(_IDENTIDAD),
}

# Leen lo de las demás y dejan fuera a quien pregunta (ADR-0011).
_COMUNITARIAS = {
    "buscar_fragmentos_comunitarios": lambda: repositorio.buscar_fragmentos_comunitarios(
        [0.1] * 768, 5, 0.65, excluir_usuario=_ELLA
    ),
    "listar_huertas_con_cultivos": lambda: repositorio.listar_huertas_con_cultivos(
        3, excluir_usuario=_ELLA
    ),
    "contar_huertas_con_cultivos": lambda: repositorio.contar_huertas_con_cultivos(
        excluir_usuario=_ELLA
    ),
}

# Acotadas por una huerta que quien llama obtuvo antes con una consulta
# acotada: `mi_huerta` y `fragmento_comunitario`.
_POR_HUERTA = {"listar_cultivos_de_huerta", "guardar_fragmento_comunitario"}

# Sin dueño, y a propósito: el catálogo, la idempotencia —que se escribe
# antes de la compuerta—, las limpiezas periódicas, la colección oficial,
# el re-llaveo transitorio del ADR-0023 y el script de regeneración.
_SIN_DUENO = {
    "reclamar_wamid", "marcar_procesado", "limpiar_idempotencia",
    "contar_mensajes_atascados", "listar_barrios", "limpiar_borradores",
    "limpiar_onboardings", "limpiar_listados_comunitarios",
    "obtener_fuente_por_url", "crear_fuente", "contar_fragmentos_oficiales",
    "reemplazar_fragmentos_oficiales", "listar_contenidos_oficiales",
    "buscar_fragmentos_oficiales", "listar_huertas_para_regenerar",
    "rellavear_identidad",
}


def test_mp26_toda_funcion_del_repositorio_esta_clasificada():
    """Una función nueva que no se clasifique hace fallar esta prueba.

    Es lo que convierte el inventario en exhaustivo: quien añada una
    consulta tiene que decidir a cuál clase pertenece, y con eso qué se le
    exige.
    """
    publicas = {
        nombre
        for nombre, funcion in inspect.getmembers(repositorio, inspect.iscoroutinefunction)
        if funcion.__module__ == repositorio.__name__ and not nombre.startswith("_")
    }
    clasificadas = [
        *_DE_UNA_PERSONA, *_POR_IDENTIDAD, *_COMUNITARIAS, *_POR_HUERTA, *_SIN_DUENO
    ]

    assert len(clasificadas) == len(set(clasificadas)), "Una función está en dos clases"
    assert publicas == set(clasificadas)


@pytest.mark.parametrize("nombre", sorted(_DE_UNA_PERSONA))
def test_mp26_lo_de_una_persona_va_acotado_por_su_usuario_id(monkeypatch, nombre):
    _comprobar(_ejecutar(monkeypatch, _DE_UNA_PERSONA[nombre]))


@pytest.mark.parametrize("nombre", ["guardar_huerta", "agregar_cultivos"])
def test_mp26_sin_huerta_previa_tampoco_se_cruza(monkeypatch, nombre):
    """La otra rama: `guardar_huerta` la crea y `agregar_cultivos` no hace nada."""
    _comprobar(_ejecutar(monkeypatch, _DE_UNA_PERSONA[nombre], _PoolEspia(huerta_existente=False)))


@pytest.mark.parametrize("nombre", sorted(_POR_IDENTIDAD))
def test_mp26_por_identidad_se_llega_solo_a_su_fila(monkeypatch, nombre):
    huella = calcular_identidad_hash(_IDENTIDAD)
    for sql, args in _ejecutar(monkeypatch, _POR_IDENTIDAD[nombre]):
        assert _acotada(sql, args, huella, "identidad_hash"), sql


@pytest.mark.parametrize("nombre", sorted(_COMUNITARIAS))
def test_mp26_lo_comunitario_deja_fuera_a_quien_pregunta(monkeypatch, nombre):
    """El CU4 es «qué siembran **otras** huertas» (ADR-0011)."""
    (sql, args), = _ejecutar(monkeypatch, _COMUNITARIAS[nombre])
    marcador = f"${args.index(_ELLA) + 1}"

    assert re.search(rf"usuario_id\s*<>\s*\{marcador}\b", sql), sql


# --- MP-27: solo columnas compartibles (RNF-08) -----------------------

# Lo que identifica o retrata a una persona. Ninguna consulta comunitaria
# puede nombrarlo, ni tocar las tablas donde vive.
_PERSONAL = ("nombre_usuario", "identidad_hash", "telefono", "contenido_mensaje")


@pytest.mark.parametrize("nombre", sorted(_COMUNITARIAS))
def test_mp27_la_consulta_comunitaria_no_lee_nada_personal(monkeypatch, nombre):
    (sql, _), = _ejecutar(monkeypatch, _COMUNITARIAS[nombre])
    seleccion = sql.split(" from ", 1)[0]
    tablas = set(re.findall(r"(?:from|join) (\w+)", sql))

    assert not any(dato in sql for dato in _PERSONAL), sql
    assert "usuario_id" not in seleccion, "El identificador saldría con el resultado"
    assert not tablas & {"usuario", "mensaje"}, tablas


@pytest.mark.parametrize(
    ("clase", "campos"),
    [
        (repositorio.FragmentoComunitario, {"contenido", "similitud", "nombre_huerta", "barrio"}),
        (repositorio.HuertaDeLaComunidad, {"nombre_huerta", "barrio", "cultivos"}),
    ],
)
def test_mp27_lo_que_devuelve_solo_tiene_campos_compartibles(clase, campos):
    """Un campo nuevo en estas clases es un dato nuevo que ve otra vecina.

    Si se añade, esta prueba obliga a decidir a conciencia si es
    compartible, en lugar de que llegue al CU4 y al CU7 sin que nadie lo
    note.
    """
    assert {campo.name for campo in fields(clase)} == campos
