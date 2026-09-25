"""Arnés común de los scripts que hacen pasar mensajes por el despachador.

No es un script: no se ejecuta, lo importan `spike_despachador` y
`ejecutar_banco`. Vive aquí y no en `app/` porque **nada de esto forma
parte del servicio**; es andamio de prueba, y el servicio no debe poder
importarlo por descuido.

Reúne las tres cosas que los dos necesitan para entrar por
`dispatcher.procesar_evento` como si el mensaje viniera de Meta:

1. **Silenciar los envíos**, para que la prueba no le escriba a nadie.
2. **Armar la carga útil** con la forma anidada que manda Meta.
3. **Borrar lo que se escribió en la base** al terminar.

Estaba duplicado en los dos scripts hasta el 24/09/2026, y la copia no era
inocua: `spike_despachador` no sustituía `marcar_escribiendo`, así que cada
ejecución **sí llamaba a la API de Meta** para pintar los tres puntitos, con
un `wamid` inventado que Meta rechazaba con un 400. Se descubrió al escribir
el segundo script y tropezar con el mismo error.
"""

from app.core.identidad import calcular_identidad_hash, huella_wamid
from app.services import consentimiento, dispatcher, memoria


class Envios:
    """Lo que el bot habría mandado por WhatsApp, sin mandarlo.

    Cada mensaje queda como `(clase, texto)`, donde la clase es `"texto"` o
    `"botones"`. Los destinos van aparte porque hay pruebas que solo miran
    hacia dónde salió el mensaje —el ADR-0023 dejó ocho sin respuesta por
    resolver mal el destino— y no qué decía.
    """

    def __init__(self) -> None:
        self.mensajes: list[tuple[str, str]] = []
        self.destinos: list[str] = []

    def limpiar(self) -> None:
        self.mensajes.clear()
        self.destinos.clear()

    def todo(self) -> str:
        """Todo lo enviado como un solo texto, para buscar dentro."""
        return texto_de(self.mensajes)


def texto_de(mensajes: list[tuple[str, str]]) -> str:
    """Une los mensajes de un turno en un solo texto.

    Existe aparte de `Envios.todo` porque quien compara un turno con el
    siguiente trabaja sobre **copias**: `Envios` se vacía en cada turno.
    """
    return "\n".join(texto for _, texto in mensajes)


def silenciar_envios() -> Envios:
    """Sustituye por espías los cuatro puntos por los que se sale a Meta.

    Son cuatro y no tres: además de los tres módulos que envían mensajes,
    está `marcar_escribiendo`, que llama a la API aunque no mande nada.

    `consentimiento` y `dispatcher` llaman al cliente directamente porque
    sus mensajes no son memoria (ADR-0012); `memoria` es por donde sale
    todo lo demás.
    """
    envios = Envios()

    async def espia_texto(destino: str, texto: str) -> None:
        envios.mensajes.append(("texto", texto))
        envios.destinos.append(destino)

    async def espia_botones(destino: str, cuerpo: str, botones) -> None:
        rotulos = " | ".join(rotulo for _, rotulo in botones)
        envios.mensajes.append(("botones", f"{cuerpo}\n   [{rotulos}]"))
        envios.destinos.append(destino)

    async def espia_escribiendo(wamid: str) -> None:
        return None

    memoria.enviar_texto = espia_texto
    memoria.enviar_botones = espia_botones
    consentimiento.enviar_texto = espia_texto
    consentimiento.enviar_botones = espia_botones
    dispatcher.enviar_texto = espia_texto
    dispatcher.marcar_escribiendo = espia_escribiendo

    return envios


def evento(bsuid: str, wamid: str, telefono: str | None = None, **cuerpo) -> dict:
    """Envuelve un mensaje en la estructura anidada que manda Meta.

    Con la forma comprobada contra producción el 17/09/2026: el BSUID va en
    el mensaje **y** en `contacts[]`, y el teléfono puede no venir —es lo
    que pasa desde que ella tiene nombre de usuario de WhatsApp (ADR-0023)—.
    """
    mensaje = {"from_user_id": bsuid, "id": wamid, **cuerpo}
    contacto: dict = {"profile": {"name": "-"}, "user_id": bsuid}

    if telefono:
        mensaje["from"] = telefono
        contacto["wa_id"] = telefono

    return {
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [contacto],
                            "messages": [mensaje],
                        },
                    }
                ]
            }
        ]
    }


def evento_texto(
    bsuid: str, wamid: str, cuerpo: str, telefono: str | None = None
) -> dict:
    return evento(bsuid, wamid, telefono, type="text", text={"body": cuerpo})


def evento_boton(bsuid: str, wamid: str, boton_id: str) -> dict:
    return evento(
        bsuid,
        wamid,
        None,
        type="interactive",
        interactive={"button_reply": {"id": boton_id, "title": "-"}},
    )


async def borrar_temporales(pool, identidades, wamids) -> str:
    """Borra las filas que dejó la ejecución. Va en un `finally`.

    La idempotencia no cuelga de ninguna usuaria —se escribe **antes** de
    la compuerta, así que no puede llevar `usuario_id` ni ningún dato
    personal (ADR-0005)—, de modo que hay que borrarla aparte, por su
    huella.

    Devuelve las dos cuentas para imprimirlas: si alguna no es la esperada,
    quedó basura en la base de la Fase 7.
    """
    usuarias = await pool.execute(
        "delete from usuario where identidad_hash = any($1::text[])",
        [calcular_identidad_hash(identificador) for identificador in identidades],
    )
    idempotencia = await pool.execute(
        "delete from idempotencia_webhook where wamid_huella = any($1::text[])",
        [huella_wamid(w) for w in wamids],
    )
    return f"{usuarias} | {idempotencia}"
