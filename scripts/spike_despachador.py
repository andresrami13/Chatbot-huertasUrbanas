"""Spike del despachador ya con el agente conectado (ADR-0013).

    python -m scripts.spike_despachador

Es el paso siguiente al `spike_agente`: allí se probaba el agente suelto,
aquí se prueba **la rama por la que pasa todo mensaje**, entrando por
`procesar_evento` con cargas útiles con la forma real de las de Meta.

**Escribe en la base y lo borra al terminar**, incluidas las filas de
idempotencia que crea. Los números empiezan por `5700000006`.

**No envía nada por WhatsApp**: los tres módulos que envían se sustituyen
por espías.

Comprueba lo que el cambio de 4c pudo romper, que es lo que importa cuando
se reemplaza código que funcionaba:

1. Que la **compuerta siga cerrada**. Quien no ha autorizado recibe la
   solicitud y **no queda ni una fila suya** en ninguna tabla.
2. Que un **saludo de quien no autorizó** siga recibiendo bienvenida y
   solicitud, por palabras clave y sin tocar el modelo (ADR-0006). Es el
   camino permanente que 4c NO debía retirar.
3. Que un mensaje de quien sí autorizó **llegue al agente**.
4. Que los **botones del registro** sigan resolviéndose sin pasar por el
   agente: una pulsación no es un mensaje que haya que interpretar.
5. Que la **idempotencia** siga descartando el reintento de Meta.
6. Que el **CU4 quede enrutado**, que era lo que faltaba desde el
   04/08/2026.
"""

import asyncio
import logging

from app import textos
from app.core.basedatos import abrir_pool, cerrar_pool, obtener_pool
from app.core.identidad import calcular_telefono_hash, huella_wamid
from app.services import consentimiento, dispatcher, memoria
from app.services.dispatcher import procesar_evento
from app.services.fragmento_comunitario import regenerar_fragmento
from app.services.repositorio import guardar_huerta, registrar_consentimiento

_PREFIJO = "5700000006"
_NUMERO_ANA = f"{_PREFIJO}01"      # autoriza
_NUMERO_DESCONOCIDA = f"{_PREFIJO}02"  # nunca autoriza
_NUMERO_VECINA = f"{_PREFIJO}03"   # tiene huerta, para el CU4

_enviados: list[tuple[str, str]] = []
_resultados: list[tuple[bool, str]] = []
_wamids: list[str] = []


async def _espia_texto(destino: str, texto: str) -> str | None:
    _enviados.append(("texto", texto))
    return None


async def _espia_botones(destino: str, cuerpo: str, botones) -> str | None:
    rotulos = " | ".join(rotulo for _, rotulo in botones)
    _enviados.append(("botones", f"{cuerpo}\n   [{rotulos}]"))
    return None


def _comprobar(condicion: bool, titulo: str, detalle: str = "") -> None:
    marca = "OK  " if condicion else "FALLA"
    print(f"    [{marca}] {titulo}" + (f" — {detalle}" if detalle else ""))
    _resultados.append((condicion, titulo))


def _wamid(sufijo: str) -> str:
    """Un wamid con la forma de los de Meta, para poder borrarlo después."""
    valor = f"wamid.SPIKE{sufijo}"
    if valor not in _wamids:
        _wamids.append(valor)
    return valor


def _evento(numero: str, wamid: str, **cuerpo) -> dict:
    """Envuelve un mensaje en la estructura anidada que manda Meta."""
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {"from": numero, "id": wamid, **cuerpo}
                            ],
                        }
                    }
                ]
            }
        ]
    }


def _texto(numero: str, wamid: str, cuerpo: str) -> dict:
    return _evento(numero, wamid, type="text", text={"body": cuerpo})


def _boton(numero: str, wamid: str, boton_id: str) -> dict:
    return _evento(
        numero,
        wamid,
        type="interactive",
        interactive={"button_reply": {"id": boton_id, "title": "-"}},
    )


async def _entra(payload: dict, rotulo: str) -> list[tuple[str, str]]:
    _enviados.clear()
    await procesar_evento(payload)

    print(f"\n  ENTRA: {rotulo}")
    for clase, texto in _enviados:
        marca = "BOT (botones)" if clase == "botones" else "BOT"
        print(f"  {marca}: {texto.replace(chr(10), chr(10) + '     ')}")
    if not _enviados:
        print("  BOT: (nada)")

    return list(_enviados)


def _todo(enviados) -> str:
    return "\n".join(texto for _, texto in enviados)


async def _borrar_temporales() -> None:
    pool = obtener_pool()

    hashes = [
        calcular_telefono_hash(n)
        for n in (_NUMERO_ANA, _NUMERO_DESCONOCIDA, _NUMERO_VECINA)
    ]
    usuarias = await pool.execute(
        "delete from usuario where telefono_hash = any($1::text[])", hashes
    )

    # La idempotencia no cuelga de ninguna usuaria —se escribe antes de la
    # compuerta— así que hay que borrarla aparte, por su huella.
    huellas = [huella_wamid(w) for w in _wamids]
    idempotencia = await pool.execute(
        "delete from idempotencia_webhook where wamid_huella = any($1::text[])",
        huellas,
    )

    print(f"\nLimpieza: {usuarias} | {idempotencia}")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="      · %(name)s | %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google_genai").setLevel(logging.WARNING)

    await abrir_pool()

    # Los tres módulos que envían. `consentimiento` y `dispatcher` llaman al
    # cliente directamente porque sus mensajes no son memoria (ADR-0012).
    memoria.enviar_texto = _espia_texto
    memoria.enviar_botones = _espia_botones
    consentimiento.enviar_texto = _espia_texto
    consentimiento.enviar_botones = _espia_botones
    dispatcher.enviar_texto = _espia_texto

    try:
        vecina = await registrar_consentimiento(_NUMERO_VECINA)
        huerta_id = await guardar_huerta(
            usuario_id=vecina.id,
            barrio_codigo="el_regalo",
            nombre_huerta="La Esperanza",
            cultivos=[("fresa", None, True), ("uchuva", None, True)],
        )
        await regenerar_fragmento(huerta_id)
        print("Preparado: huerta vecina con fresa y uchuva en El Regalo.")

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("1. La compuerta sigue cerrada")
        print("=" * 70)
        enviados = await _entra(
            _texto(_NUMERO_DESCONOCIDA, _wamid("01"), "mi tomate tiene bichos"),
            "consulta de alguien que NO ha autorizado",
        )
        texto = _todo(enviados)

        _comprobar(
            textos.SOLICITUD_CONSENTIMIENTO in texto,
            "recibe la solicitud de autorización",
        )
        _comprobar(
            "Fuente:" not in texto,
            "NO recibe respuesta agronómica",
            "su consulta no se procesó",
        )

        huella_desconocida = calcular_telefono_hash(_NUMERO_DESCONOCIDA)
        existe = await obtener_pool().fetchval(
            "select count(*) from usuario where telefono_hash = $1",
            huella_desconocida,
        )
        _comprobar(
            existe == 0,
            "no queda ninguna fila suya en la base",
            "ni siquiera el hecho de haber escrito (CU1, ADR-0003)",
        )

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("2. El saludo previo al consentimiento (camino permanente)")
        print("=" * 70)
        enviados = await _entra(
            _texto(_NUMERO_DESCONOCIDA, _wamid("02"), "hola"),
            "saludo de alguien que NO ha autorizado",
        )
        texto = _todo(enviados)

        _comprobar(
            textos.BIENVENIDA in texto,
            "recibe la bienvenida",
            "es_saludo_o_ayuda sigue vivo dentro de la compuerta",
        )
        _comprobar(
            textos.SOLICITUD_CONSENTIMIENTO in texto,
            "y después la solicitud de autorización",
        )

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("3. Autoriza y consulta: el mensaje llega al agente")
        print("=" * 70)
        await _entra(
            _boton(_NUMERO_ANA, _wamid("03"), textos.BOTON_ACEPTO),
            "pulsa [Acepto]",
        )

        ana_id = await obtener_pool().fetchval(
            "select id from usuario where telefono_hash = $1",
            calcular_telefono_hash(_NUMERO_ANA),
        )
        _comprobar(ana_id is not None, "queda registrado su consentimiento")

        enviados = await _entra(
            _texto(
                _NUMERO_ANA, _wamid("04"),
                "a mi mata de tomate le salieron unos bichitos verdes, que le echo",
            ),
            "consulta agroecológica",
        )
        texto = _todo(enviados)

        _comprobar(
            "Fuente:" in texto or textos.ORIENTACION_SIN_RESPALDO in texto,
            "el agente la enrutó al CU2",
        )

        en_memoria = await obtener_pool().fetchval(
            "select count(*) from mensaje where usuario_id = $1", ana_id
        )
        _comprobar(
            en_memoria >= 2,
            "la conversación quedó en la memoria",
            f"{en_memoria} filas: su pregunta y la respuesta",
        )

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("4. El CU4, que llevaba desde el 04/08 sin enrutar")
        print("=" * 70)
        enviados = await _entra(
            _texto(_NUMERO_ANA, _wamid("05"), "que estan sembrando las otras huertas"),
            "consulta a la comunidad",
        )
        texto = _todo(enviados)

        _comprobar(
            "El Regalo" in texto or textos.COMUNIDAD_SIN_DATOS in texto,
            "el agente la enrutó al CU4",
            "antes de 4c esta rama no existía",
        )
        # El 15/08/2026 el modelo escribió "la huerta COMUNITARIO – La
        # Esperanza". La etiqueta es andamiaje del prompt y para ella no
        # significa nada.
        _comprobar(
            "COMUNITARIO" not in texto and "OFICIAL" not in texto,
            "no se le cuela la etiqueta de procedencia",
        )

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("5. Registro y botones, sin pasar por el agente")
        print("=" * 70)
        enviados = await _entra(
            _texto(_NUMERO_ANA, _wamid("06"), "sembre cilantro en marzo, en holanda"),
            "cuenta de su huerta",
        )

        _comprobar(
            any(clase == "botones" for clase, _ in enviados),
            "le propone el registro con botones",
        )

        huertas = await obtener_pool().fetchval(
            "select count(*) from huerta where usuario_id = $1", ana_id
        )
        _comprobar(huertas == 0, "todavía NO hay huerta: solo se propuso")

        enviados = await _entra(
            _boton(_NUMERO_ANA, _wamid("07"), textos.BOTON_REGISTRO_CONFIRMO),
            "pulsa [Sí, guardar]",
        )
        texto = _todo(enviados)

        _comprobar(
            textos.REGISTRO_GUARDADO in texto,
            "ahora sí confirma que quedó guardado",
        )

        huertas = await obtener_pool().fetchval(
            "select count(*) from huerta where usuario_id = $1", ana_id
        )
        _comprobar(huertas == 1, "la huerta existe solo después del botón")

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("6. Idempotencia: el reintento de Meta se descarta")
        print("=" * 70)
        enviados = await _entra(
            _texto(_NUMERO_ANA, _wamid("05"), "que estan sembrando las otras huertas"),
            "el mismo wamid del caso 4, reenviado",
        )

        _comprobar(
            not enviados,
            "no se le responde dos veces",
            "el wamid ya estaba procesado",
        )

        # -----------------------------------------------------------------
        fallos = [titulo for ok, titulo in _resultados if not ok]
        print("\n" + "=" * 70)
        if fallos:
            print(f"{len(fallos)} COMPROBACIONES FALLIDAS de {len(_resultados)}:")
            for titulo in fallos:
                print(f"  - {titulo}")
            print("\nRecuerde: a temperatura 0.7 el enrutamiento varía.")
        else:
            print(f"Las {len(_resultados)} comprobaciones pasaron.")
        print("=" * 70)
    finally:
        await _borrar_temporales()
        await cerrar_pool()


if __name__ == "__main__":
    asyncio.run(main())
