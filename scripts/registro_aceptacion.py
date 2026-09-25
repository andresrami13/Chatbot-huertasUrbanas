"""Reconstruye el registro de la prueba de aceptación desde `mensaje`.

    python -m scripts.registro_aceptacion

Es la actividad A-14 del plan de pruebas: la aceptación la ejecutaron
usuarias reales desde sus celulares, y lo único que queda de ella es la
conversación guardada. Esto la convierte en los dos productos que pide
ISO/IEC/IEEE 29119-3: **resultados por caso de uso** (§8.9) y **bitácora de
ejecución** (§8.10).

**No escribe nada.** Solo lee.

## Por qué su salida sí puede ir al repositorio

`revisar_prueba_real` imprime la conversación en claro y su salida no sale
de la terminal. Esto es lo contrario **por construcción**: no imprime una
sola palabra de lo que escribió nadie. Solo fechas, conteos y seudónimos
(`P-01`, `P-02`…, por orden de consentimiento), que no se pueden cruzar
con nada fuera de la base. Ni barrio, ni nombre de huerta, ni cultivos.

## Cómo sabe qué caso de uso se atendió

`mensaje` no guarda qué herramienta respondió. Se deduce de las **marcas
de los textos que compone el código**, que son estables aunque la
redacción haya cambiado de un ADR a otro. Lo que redacta el modelo sin
marca fija queda como «respuesta libre del agente», sin atribuirle un caso
de uso que no se puede demostrar.

Dos casos de uso no dejan rastro aquí **por diseño**, y se cuentan de otra
fuente: el consentimiento (CU1) se atiende antes de la compuerta y no se
recuerda (ADR-0012), así que su evidencia es la fila de `usuario`; y el
onboarding (CU6) se da por completado cuando existe la fila de `huerta`.

## «Sin respuesta registrada» no es «sin respuesta»

Tres envíos se hacen sin recordarse, a propósito: el acuse de la nota de
voz (ADR-0017), el saludo personalizado (ADR-0016) y el aviso de base caída
(ADR-0019). Un mensaje de ella seguido de otro suyo sin nada en medio puede
ser cualquiera de esos. Se cuenta, y se lee con esa reserva.
"""

import asyncio
import re
from collections import defaultdict

from app.core.basedatos import abrir_pool, cerrar_pool, obtener_pool

# Marcas de los textos compuestos por el código, por caso de uso. Se buscan
# fragmentos estables y no el texto entero, porque varios textos cambiaron
# de redacción (ADR-0016, ADR-0021, ADR-0024) y los mensajes viejos guardan
# la versión de su día.
_MARCAS: dict[str, str] = {
    "CU2 con cita": r"^Fuente:",
    "CU2 sin respaldo": r"De eso no le puedo responder con seguridad|no se lo puedo asegurar",
    "CU3 propuesta": r"^Esto es lo que entendí:",
    "CU3 guardado": r"ya quedó guardado\.",
    "CU3 descartado": r"no guardé nada\.\s+Si quiere lo intentamos",
    "CU3 sin borrador": r"ya no tengo a la mano lo que iba a guardar",
    "CU4 listado": r"tienen sembrado otras huertas|Le repito desde el principio|Todavía no tengo otras huertas",
    "CU5 bienvenida": r"asistente virtual de huertas urbanas|asistente de huertas urbanas",
    "CU6 pregunta": r"¿cómo se llama usted|¿En qué barrio de Bosa|¿Cuál de estos es su barrio|¿Cómo se llama su huerta",
    "CU6 reintento": r"No encontré ese barrio|^No entendí\.|no le entendí el (nombre|barrio)",
    "CU6 descartado": r"no guardé nada\.\s+Volvamos a empezar",
    "CU7 sin ese cultivo": r"De las huertas que conozco, ninguna tiene",
    "CU8 mi huerta": r"Esto es lo que tiene anotado|Todavía no tengo ninguna planta anotada|Todavía no tengo registrada su huerta|^🌱 Su huerta",
    "Promesa de reportar": r"equipo.{0,80}(registrad|en cuenta)|(registrad|reportad).{0,80}equipo",
}

# Qué marcas cuentan como evidencia de que el caso de uso se ejerció.
_EVIDENCIA_POR_CU: dict[str, tuple[str, ...]] = {
    "CU2": ("CU2 con cita", "CU2 sin respaldo"),
    "CU3": ("CU3 propuesta", "CU3 guardado"),
    "CU4": ("CU4 listado",),
    "CU5": ("CU5 bienvenida",),
    "CU7": ("CU7 sin ese cultivo",),
    "CU8": ("CU8 mi huerta",),
}


def _clasificar(texto: str) -> list[str]:
    return [clave for clave, patron in _MARCAS.items() if re.search(patron, texto, re.M)]


async def main() -> None:
    await abrir_pool()
    try:
        pool = obtener_pool()
        usuarias = await pool.fetch(
            "select id, consentimiento_en from usuario order by consentimiento_en"
        )
        con_huerta = {
            fila["usuario_id"]
            for fila in await pool.fetch("select usuario_id from huerta")
        }
        cultivos = {
            fila["usuario_id"]: fila["n"]
            for fila in await pool.fetch(
                """
                select h.usuario_id, count(c.id) as n
                  from huerta h left join cultivo c on c.huerta_id = h.id
                 group by h.usuario_id
                """
            )
        }
        mensajes = await pool.fetch(
            "select usuario_id, rol, tipo, contenido, creado_en "
            "from mensaje order by usuario_id, creado_en"
        )
    finally:
        await cerrar_pool()

    seudonimo = {fila["id"]: f"P-{n:02d}" for n, fila in enumerate(usuarias, start=1)}
    por_usuaria: dict = defaultdict(list)
    for fila in mensajes:
        por_usuaria[fila["usuario_id"]].append(fila)

    total: dict[str, int] = defaultdict(int)
    quien: dict[str, set] = defaultdict(set)
    dias: dict[str, set] = defaultdict(set)

    print("## Bitácora por participante\n")
    print("| Participante | Consintió | Onboarding | Días con actividad | Mensajes de ella | De ellos, voz | CU2 con cita | CU2 sin respaldo | CU3 guardados | Cultivos | Sin respuesta registrada |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")

    for fila in usuarias:
        uid = fila["id"]
        propios = por_usuaria.get(uid, [])
        cuenta: dict[str, int] = defaultdict(int)
        sin_respuesta = 0

        for i, m in enumerate(propios):
            if m["rol"] == "asistente":
                for clave in _clasificar(m["contenido"]):
                    cuenta[clave] += 1
                    total[clave] += 1
                    quien[clave].add(seudonimo[uid])
                    dias[clave].add(m["creado_en"].date())
            else:
                siguiente = propios[i + 1] if i + 1 < len(propios) else None
                if siguiente is None or siguiente["rol"] == "usuaria":
                    sin_respuesta += 1

        de_ella = [m for m in propios if m["rol"] == "usuaria"]
        activos = sorted({m["creado_en"].date() for m in propios})
        print(
            f"| {seudonimo[uid]} | {fila['consentimiento_en']:%d/%m} "
            f"| {'completo' if uid in con_huerta else 'sin completar'} "
            f"| {len(activos)} "
            f"| {len(de_ella)} "
            f"| {sum(1 for m in de_ella if m['tipo'] == 'audio')} "
            f"| {cuenta['CU2 con cita']} "
            f"| {cuenta['CU2 sin respaldo']} "
            f"| {cuenta['CU3 guardado']} "
            f"| {cultivos.get(uid, 0)} "
            f"| {sin_respuesta} |"
        )
        total["sin respuesta"] += sin_respuesta

    print("\n## Evidencia por caso de uso\n")
    print("| CU | Participantes con evidencia | Respuestas | Primera | Última |")
    print("|---|---|---|---|---|")
    print(
        f"| CU1 | {len(usuarias)} | filas de `usuario` "
        f"| {usuarias[0]['consentimiento_en']:%d/%m} "
        f"| {usuarias[-1]['consentimiento_en']:%d/%m} |"
    )
    for cu, claves in _EVIDENCIA_POR_CU.items():
        participantes = set().union(*(quien[c] for c in claves))
        fechas = sorted(set().union(*(dias[c] for c in claves)))
        n = sum(total[c] for c in claves)
        rango = f"{fechas[0]:%d/%m} | {fechas[-1]:%d/%m}" if fechas else "— | —"
        print(f"| {cu} | {len(participantes)} | {n} | {rango} |")
        if cu == "CU5":
            print(
                f"| CU6 | {len(con_huerta)} | filas de `huerta` "
                f"| — | — |"
            )

    print("\n## Marcas contadas\n")
    for clave in _MARCAS:
        print(f"- {clave}: {total[clave]}")
    print(f"- mensajes de ella sin respuesta registrada: {total['sin respuesta']}")

    # Las fechas importan en esta marca: el ADR-0024 le prohibió al agente,
    # el 19/09/2026, prometer nada que no haga. Antes de esa fecha era el
    # defecto; después, es que la regla no basta.
    promesas = sorted(dias["Promesa de reportar"])
    if promesas:
        print(f"  fechas de las promesas: {', '.join(f'{d:%d/%m}' for d in promesas)}")

    fechas = [m["creado_en"] for m in mensajes]
    print(
        f"\nMensajes: {len(mensajes)}, del "
        f"{min(fechas):%d/%m/%Y} al {max(fechas):%d/%m/%Y}."
    )


if __name__ == "__main__":
    asyncio.run(main())
