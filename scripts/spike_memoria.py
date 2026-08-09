"""Spike de la memoria de conversación, contra la base real (ADR-0012).

    python -m scripts.spike_memoria

**Escribe en la base y lo borra al terminar.** Crea dos usuarias
temporales, conversa con ellas y borra todo en un `finally`, igual que los
spikes del CU3 y del CU4.

Los números empiezan por `5700000008`, para que no puedan chocar con uno
real ni con los del spike del CU4. **La fila real del celular de pruebas
del autor no se toca**: el borrado se acota a los teléfonos que este script
creó.

No llama a Gemini ni envía nada por WhatsApp: la memoria es persistencia,
no conversación. Comprueba las siete cosas que pueden salir mal:

1. Que la ventana salga **en orden cronológico** y termine en lo último que
   dijo la usuaria, que es la forma con la que se le habla al modelo.
2. Que **corte en N** y conserve los más recientes, no los primeros.
3. Que el **reproceso no duplique** la pregunta. Es el *al menos una vez*
   del ADR-0005: sin `on conflict do nothing` el reintento reventaría.
4. Que **varias filas sin wamid convivan**, que es lo que permite registrar
   una respuesta cuyo envío falló.
5. Que **la conversación de una usuaria no aparezca en la de otra** (capa 1
   del modelo de seguridad).
6. Que en la base **no quede ningún wamid en claro**, que es lo que el
   30/07/2026 costó descubrir.
7. Que un **contenido vacío no genere fila**.
"""

import asyncio
import re

from app.config import settings
from app.core.basedatos import abrir_pool, cerrar_pool, obtener_pool
from app.core.identidad import calcular_telefono_hash, huella_wamid
from app.services.memoria import recordar_asistente, recordar_usuaria, ventana
from app.services.repositorio import registrar_consentimiento

# Prefijo inconfundible: ningún celular colombiano real lo tiene.
_PREFIJO = "5700000008"

_NUMERO_ANA = f"{_PREFIJO}01"
_NUMERO_ROSA = f"{_PREFIJO}02"

# Un wamid con la forma real de los de Meta. El teléfono va dentro, en
# base64, que es justo el motivo de que nunca se guarde en claro.
_WAMID = "wamid.HBgMNTcwMDAwMDAwODAxFQIAEhggQUJDREVGMDEyMzQ1Njc4OQA="

_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# El resultado de cada comprobación, para el resumen final.
_resultados: list[tuple[bool, str]] = []


def _comprobar(condicion: bool, titulo: str, detalle: str = "") -> None:
    marca = "OK  " if condicion else "FALLA"
    print(f"  [{marca}] {titulo}" + (f" — {detalle}" if detalle else ""))
    _resultados.append((condicion, titulo))


async def _contar_filas(usuario_id) -> int:
    return await obtener_pool().fetchval(
        "select count(*) from mensaje where usuario_id = $1", usuario_id
    )


async def _borrar_temporales() -> None:
    """Borra las usuarias del spike. En cascada se van sus mensajes."""
    hashes = [
        calcular_telefono_hash(numero)
        for numero in (_NUMERO_ANA, _NUMERO_ROSA)
    ]
    resultado = await obtener_pool().execute(
        "delete from usuario where telefono_hash = any($1::text[])", hashes
    )
    print(f"\nLimpieza: {resultado}")


async def main() -> None:
    await abrir_pool()
    try:
        ana = await registrar_consentimiento(_NUMERO_ANA)
        rosa = await registrar_consentimiento(_NUMERO_ROSA)
        print(f"Usuarias temporales creadas.\n")

        # -----------------------------------------------------------------
        print("1. Orden cronológico y forma de la ventana")
        # -----------------------------------------------------------------
        await recordar_usuaria(ana.id, "buenas, tengo una duda", "text", None)
        await recordar_asistente(ana.id, "Claro, cuénteme.", None)
        await recordar_usuaria(ana.id, "sembre tomate en marzo", "audio", None)
        await recordar_asistente(ana.id, "¿En qué barrio queda su huerta?", None)
        await recordar_usuaria(ana.id, "en el regalo", "text", None)

        turnos = await ventana(ana.id)

        _comprobar(
            len(turnos) == 5,
            "están los cinco mensajes",
            f"{len(turnos)} filas",
        )
        _comprobar(
            [t.rol for t in turnos]
            == ["usuaria", "asistente", "usuaria", "asistente", "usuaria"],
            "alterna usuaria/asistente sin invertirse",
        )
        _comprobar(
            turnos[0].contenido == "buenas, tengo una duda",
            "el primero es el más antiguo",
        )
        _comprobar(
            turnos[-1].rol == "usuaria" and turnos[-1].contenido == "en el regalo",
            "termina en lo último que dijo la usuaria",
            "es lo que el agente entrega como turno en curso",
        )

        print("\n  Ventana tal como la leerá el agente:")
        for turno in turnos:
            print(f"    {turno.rol:>9}: {turno.contenido}")

        # -----------------------------------------------------------------
        print(f"\n2. Corte en {settings.MEMORIA_VENTANA_MENSAJES} mensajes")
        # -----------------------------------------------------------------
        # Ya hay 5; se añaden 10 más para pasarse holgadamente.
        for i in range(10):
            await recordar_usuaria(ana.id, f"mensaje numero {i}", "text", None)

        turnos = await ventana(ana.id)
        total = await _contar_filas(ana.id)

        _comprobar(
            len(turnos) == settings.MEMORIA_VENTANA_MENSAJES,
            f"devuelve {settings.MEMORIA_VENTANA_MENSAJES}, no más",
            f"{len(turnos)} de {total} filas guardadas",
        )
        _comprobar(
            turnos[-1].contenido == "mensaje numero 9",
            "conserva los más recientes, no los primeros",
        )
        _comprobar(
            all("tengo una duda" not in t.contenido for t in turnos),
            "lo viejo se queda fuera de la ventana pero sigue en la tabla",
            f"la tabla conserva {total}, para la Fase 7",
        )

        # -----------------------------------------------------------------
        print("\n3. Reproceso: el mismo wamid no duplica la pregunta")
        # -----------------------------------------------------------------
        antes = await _contar_filas(rosa.id)
        await recordar_usuaria(rosa.id, "mi tomate tiene bichos", "text", _WAMID)
        tras_primera = await _contar_filas(rosa.id)

        # Meta reintrega el mismo mensaje: el proceso murió antes de
        # marcarlo como procesado (ADR-0005).
        await recordar_usuaria(rosa.id, "mi tomate tiene bichos", "text", _WAMID)
        tras_reproceso = await _contar_filas(rosa.id)

        _comprobar(
            tras_primera == antes + 1,
            "la primera entrega se guarda",
        )
        _comprobar(
            tras_reproceso == tras_primera,
            "la segunda entrega NO duplica",
            "on conflict do nothing; sin él el reintento reventaría",
        )

        # -----------------------------------------------------------------
        print("\n4. Respuestas sin wamid: varios nulos conviven")
        # -----------------------------------------------------------------
        antes = await _contar_filas(rosa.id)
        await recordar_asistente(rosa.id, "Le cuento lo del pulgón.", None)
        await recordar_asistente(rosa.id, "Le cuento lo del pulgón.", None)
        despues = await _contar_filas(rosa.id)

        _comprobar(
            despues == antes + 2,
            "dos respuestas sin wamid dan dos filas",
            "si el envío falla no hay wamid, y la fila tiene que entrar igual",
        )

        # -----------------------------------------------------------------
        print("\n5. Aislamiento entre usuarias (capa 1)")
        # -----------------------------------------------------------------
        turnos_rosa = await ventana(rosa.id)
        turnos_ana = await ventana(ana.id)

        _comprobar(
            all("tomate tiene bichos" not in t.contenido for t in turnos_ana),
            "lo de Rosa no aparece en la ventana de Ana",
        )
        _comprobar(
            all("mensaje numero" not in t.contenido for t in turnos_rosa),
            "lo de Ana no aparece en la ventana de Rosa",
        )

        # -----------------------------------------------------------------
        print("\n6. En la base no queda ningún wamid en claro")
        # -----------------------------------------------------------------
        filas = await obtener_pool().fetch(
            """
            select huella_wamid, tipo
              from mensaje
             where usuario_id = any($1::uuid[])
               and huella_wamid is not null
            """,
            [ana.id, rosa.id],
        )
        huellas = [fila["huella_wamid"] for fila in filas]

        _comprobar(
            bool(huellas) and all(_HEX64.match(h) for h in huellas),
            "lo guardado son huellas de 64 hex",
            f"{len(huellas)} fila(s) con huella",
        )
        _comprobar(
            all(_WAMID not in h for h in huellas),
            "el wamid no aparece en la columna",
        )
        _comprobar(
            huellas and huellas[0] == huella_wamid(_WAMID),
            "la huella es la que produce huella_wamid()",
            "determinista, que es lo que la deduplicación necesita",
        )

        tipos = await obtener_pool().fetch(
            "select distinct tipo from mensaje where usuario_id = $1", ana.id
        )
        _comprobar(
            {t["tipo"] for t in tipos} == {"text", "audio"},
            "el tipo conserva cómo llegó el mensaje",
            "la nota de voz se guardó transcrita pero anotada como 'audio'",
        )

        # -----------------------------------------------------------------
        print("\n7. Contenido vacío no genera fila")
        # -----------------------------------------------------------------
        antes = await _contar_filas(rosa.id)
        await recordar_usuaria(rosa.id, "", "interactive", None)
        despues = await _contar_filas(rosa.id)

        _comprobar(
            despues == antes,
            "un botón desconocido no ensucia la memoria",
        )

        # -----------------------------------------------------------------
        fallos = [titulo for ok, titulo in _resultados if not ok]
        print("\n" + "=" * 70)
        if fallos:
            print(f"{len(fallos)} COMPROBACIONES FALLIDAS de {len(_resultados)}:")
            for titulo in fallos:
                print(f"  - {titulo}")
        else:
            print(f"Las {len(_resultados)} comprobaciones pasaron.")
        print("=" * 70)
    finally:
        await _borrar_temporales()
        await cerrar_pool()


if __name__ == "__main__":
    asyncio.run(main())
