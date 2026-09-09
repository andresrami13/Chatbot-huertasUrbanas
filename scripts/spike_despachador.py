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
7. Que el **CU8 le cuente lo que ella tiene sembrado**, y que no se
   confunda con un registro (ADR-0022).
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
            # Solo los nombres: la fecha de siembra salió de `cultivo` en
            # la migración 008 (ADR-0018), y este spike se quedó llamando
            # con el formato viejo hasta el 08/09/2026.
            especies=["fresa", "uchuva"],
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

        # Al aceptar arranca el onboarding (ADR-0016): tres preguntas
        # cerradas, una por mensaje. Mientras no las conteste, el agente no
        # ve nada — es lo que se comprueba de paso al final del bloque.
        enviados = await _entra(
            _texto(_NUMERO_ANA, _wamid("03a"), "Carmen"),
            "contesta el nombre",
        )
        _comprobar(
            textos.ONBOARDING_PREGUNTA_BARRIO in _todo(enviados),
            "el eco del nombre va dentro de la pregunta del barrio",
            "confirmación implícita: no se le pide un 'sí' aparte",
        )
        _comprobar(
            "guardé" in _todo(enviados),
            "del nombre dice 'guardé', que es verdad",
            "su fila de usuario existe desde el consentimiento",
        )

        enviados = await _entra(
            _texto(_NUMERO_ANA, _wamid("03b"), "Holanda"),
            "contesta el barrio",
        )
        texto = _todo(enviados)
        _comprobar(
            textos.ONBOARDING_OPCION_NINGUNO in texto,
            "ofrece los candidatos como lista numerada de texto",
            "sin botones: el 24 % de los barrios no cabe en un rótulo",
        )
        _comprobar(
            not any(clase == "botones" for clase, _ in enviados),
            "la desambiguación NO usa botones",
            "por eso no hay que enmendar el §4.3 de CLAUDE.md",
        )
        _comprobar(
            textos.ONBOARDING_OPCION_OTRO not in texto,
            "la salida 'mi barrio no está' todavía NO aparece",
            "solo al tercer 'Ninguno', para no ofrecer el camino corto",
        )

        enviados = await _entra(
            _texto(_NUMERO_ANA, _wamid("03c"), "1"),
            "elige la opción 1",
        )
        _comprobar(
            textos.ONBOARDING_PREGUNTA_HUERTA in _todo(enviados),
            "pasa a la tercera pregunta",
        )
        _comprobar(
            "anoté" in _todo(enviados),
            "del barrio dice 'anoté', no 'guardé'",
            "todavía espera al botón: decir 'guardé' sería falso",
        )

        enviados = await _entra(
            _texto(_NUMERO_ANA, _wamid("03d"), "La Milagrosa"),
            "contesta el nombre de la huerta",
        )
        _comprobar(
            any(clase == "botones" for clase, _ in enviados),
            "cierra con el resumen y los botones del CU3",
            "el único momento con botones del onboarding, y son los de siempre",
        )

        huertas = await obtener_pool().fetchval(
            "select count(*) from huerta where usuario_id = $1", ana_id
        )
        _comprobar(huertas == 0, "todavía NO hay huerta: solo se propuso")

        enviados = await _entra(
            _boton(_NUMERO_ANA, _wamid("03e"), textos.BOTON_REGISTRO_CONFIRMO),
            "pulsa [Sí, guardar] del onboarding",
        )

        huertas = await obtener_pool().fetchval(
            "select count(*) from huerta where usuario_id = $1", ana_id
        )
        _comprobar(
            huertas == 1,
            "la huerta existe solo después del botón",
            "y desde el ADR-0016 significa 'completó el onboarding'",
        )

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
            "regalo" in texto.lower() or textos.COMUNIDAD_SIN_HUERTAS in texto,
            "el agente la enrutó al CU4",
            "antes de 4c esta rama no existía",
        )
        # Desde el ADR-0021 el listado lo compone el código, así que su
        # forma es comprobable y no depende de lo que redacte el modelo.
        # Si hay huertas que enseñar, el encabezado está.
        _comprobar(
            textos.COMUNIDAD_SIN_HUERTAS in texto
            or textos.COMUNIDAD_LISTADO_ENCABEZADO in texto,
            "el listado del CU4 lo compuso el código",
            "encabezado fijo, no un párrafo del modelo",
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

        cultivos = await obtener_pool().fetchval(
            """
            select count(*) from cultivo c
              join huerta h on h.id = c.huerta_id
             where h.usuario_id = $1
            """,
            ana_id,
        )
        _comprobar(cultivos == 0, "todavía NO hay cultivos: solo se propuso")

        enviados = await _entra(
            _boton(_NUMERO_ANA, _wamid("07"), textos.BOTON_REGISTRO_CONFIRMO),
            "pulsa [Sí, guardar]",
        )
        texto = _todo(enviados)

        _comprobar(
            textos.REGISTRO_GUARDADO in texto,
            "ahora sí confirma que quedó guardado",
        )

        cultivos = await obtener_pool().fetchval(
            """
            select count(*) from cultivo c
              join huerta h on h.id = c.huerta_id
             where h.usuario_id = $1
            """,
            ana_id,
        )
        _comprobar(cultivos >= 1, "el cultivo existe solo después del botón")

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("6. El CU8: qué tengo yo sembrado")
        print("=" * 70)
        enviados = await _entra(
            _texto(_NUMERO_ANA, _wamid("08"), "que tengo sembrado"),
            "pregunta por su propia huerta",
        )
        texto = _todo(enviados)

        # Hasta el ADR-0022 no había herramienta para esto y el agente
        # respondía de la ventana de memoria, nombrando solo el último
        # cultivo. El encabezado fijo delata que lo compuso el código.
        _comprobar(
            "Su huerta" in texto,
            "el agente la enrutó al CU8",
            "y el texto lo compuso el código, no el modelo",
        )
        _comprobar(
            "cilantro" in texto.lower(),
            "le nombra el cultivo que acaba de registrar",
        )
        _comprobar(
            textos.REGISTRO_NADA_QUE_ANOTAR not in texto,
            "no lo confundió con un registro",
            "la pregunta no nombra ninguna planta",
        )

        # -----------------------------------------------------------------
        print("\n" + "=" * 70)
        print("7. Idempotencia: el reintento de Meta se descarta")
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
