"""Reconstruye una prueba hecha desde el celular y la remide (Fase 7).

    python -m scripts.revisar_prueba_real

**No escribe nada.** Solo lee, así que no necesita el borrado en `finally`
de los demás scripts: no crea ninguna fila temporal.

## Por qué hace falta

La bitácora de Railway no registra ni la pregunta ni la respuesta, y es
deliberado (CLAUDE.md §11). Eso deja bien protegida a la usuaria y sin
material al que quiera diagnosticar por qué el CU2 no respondió: la
bitácora dice `fragmentos=0 | mejor=-`, pero no a qué pregunta.

Lo que sí queda es `mensaje.contenido`, sin cifrar y por decisión declarada
(ADR-0012). Con eso se puede reconstruir la conversación tal como ocurrió y
**remedir cada consulta contra el corpus real**, que es la única forma de
separar las tres causas por las que el CU2 puede haber callado:

1. el umbral está demasiado alto para cómo pregunta la usuaria de verdad,
2. el corpus no cubre el tema, por mucho que se baje el umbral,
3. el agente no enrutó a `consultar_orientacion` y el CU2 ni corrió.

Las tres se ven distintas en la salida: (1) deja similitudes justo por
debajo del umbral, (2) las deja muy por debajo y con fragmentos del tema
equivocado, y (3) no deja ni rastro —la respuesta del asistente no es la
del CU2—.

Es la revalidación del umbral que pide la Fase 7 (ADR-0010), pero con las
consultas que la usuaria escribió de verdad en lugar de las doce que
imaginó el autor en `scripts/calibrar_umbral.py`.

## Aviso

Imprime la conversación en claro por la terminal, que es lo que se está
diagnosticando. **Esa salida no va a un archivo del repositorio ni a un
issue**: es texto libre de una persona, y el repositorio es público.
"""

import argparse
import asyncio
from uuid import UUID

from app.config import settings
from app.core.basedatos import abrir_pool, cerrar_pool, obtener_pool
from app.services.embeddings import vectorizar_consulta

# Cuántos fragmentos se miran al remedir. El mismo top-k de producción, para
# que la comparación con el umbral signifique lo mismo que en el servicio.
TOP_K = settings.RAG_TOP_K

# Recorte del fragmento recuperado. Lo justo para reconocer de qué habla:
# si el tema no tiene nada que ver con la pregunta, el problema es el corpus
# y no el umbral, y eso solo se ve leyendo.
_MUESTRA = 110


async def _usuarias_con_conversacion() -> list[tuple[UUID, int]]:
    """Las usuarias que tienen mensajes, de la más habladora a la que menos.

    No hay forma de reconocer aquí a la usuaria por su número —la columna es
    el HMAC, que no se puede invertir—, así que se listan todas. En la base
    hay una sola fila real, la del celular de pruebas del autor.
    """
    filas = await obtener_pool().fetch(
        """
        select usuario_id, count(*) as cuantos
          from mensaje
         group by usuario_id
         order by cuantos desc
        """
    )
    return [(fila["usuario_id"], fila["cuantos"]) for fila in filas]


async def _conversacion(usuario_id: UUID) -> list[dict]:
    """Todo lo hablado con esa usuaria, del primer mensaje al último.

    Sin recortar a la ventana de diez: aquí interesa la prueba entera, no lo
    que el agente alcanzaba a ver en cada turno.
    """
    filas = await obtener_pool().fetch(
        """
        select rol, tipo, contenido, creado_en
          from mensaje
         where usuario_id = $1
         order by creado_en asc, rol asc
        """,
        usuario_id,
    )
    return [dict(fila) for fila in filas]


async def _huerta(usuario_id: UUID) -> dict | None:
    """La huerta registrada y sus cultivos, para contrastar con el CU3.

    Es lo que permite decir si lo que se guardó coincide con lo que ella
    escribió: el resumen que confirmó lo compuso el código a partir de la
    extracción, y el error puede estar en cualquiera de los dos sitios.
    """
    fila = await obtener_pool().fetchrow(
        """
        select h.id,
               h.nombre_huerta,
               b.nombre as barrio,
               h.comentarios,
               h.creado_en,
               h.actualizado_en,
               (select count(*) from fragmento_comunitario f
                 where f.huerta_id = h.id) as tiene_fragmento
          from huerta h
          join barrio b on b.id = h.barrio_id
         where h.usuario_id = $1
        """,
        usuario_id,
    )

    if fila is None:
        return None

    cultivos = await obtener_pool().fetch(
        """
        select especie, fecha_siembra_aprox, fecha_imprecisa, creado_en
          from cultivo
         where huerta_id = $1
         order by creado_en asc
        """,
        fila["id"],
    )

    return {"huerta": dict(fila), "cultivos": [dict(c) for c in cultivos]}


async def _remedir(consulta: str) -> list[dict]:
    """Similitud de los `TOP_K` fragmentos más cercanos a esa consulta.

    Misma cuenta que hace el repositorio en producción —`1 - (a <=> b)`, de
    distancia a similitud— y sin filtrar por umbral: interesa justamente ver
    lo que se quedó fuera y por cuánto.
    """
    vector = await vectorizar_consulta(consulta)
    literal = "[" + ",".join(repr(componente) for componente in vector) + "]"

    filas = await obtener_pool().fetch(
        """
        select 1 - (fo.embedding <=> $1::vector) as similitud,
               fo.contenido,
               f.entidad
          from fragmento_oficial fo
          join fuente f on f.id = fo.fuente_id
         order by fo.embedding <=> $1::vector
         limit $2
        """,
        literal,
        TOP_K,
    )
    return [dict(fila) for fila in filas]


def _una_linea(texto: str, ancho: int) -> str:
    """El texto en una sola línea y recortado, para que la tabla se lea."""
    plano = " ".join(texto.split())
    if len(plano) <= ancho:
        return plano
    return plano[: ancho - 1] + "…"


async def main() -> None:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument(
        "--usuaria",
        help="UUID de la usuaria. Por defecto, la que más mensajes tenga.",
    )
    analizador.add_argument(
        "--sin-remedir",
        action="store_true",
        help="Solo vuelca la conversación y la huerta, sin llamar a Gemini.",
    )
    argumentos = analizador.parse_args()

    await abrir_pool()
    try:
        pool = obtener_pool()

        # --- Con qué se está midiendo -----------------------------------
        #
        # Va primero porque una medición sin las condiciones en las que se
        # tomó no vale para nada, que es la lección repetida del proyecto.
        fragmentos = await pool.fetchval("select count(*) from fragmento_oficial")
        fuentes = await pool.fetchval(
            "select count(*) from fuente where exists "
            "(select 1 from fragmento_oficial where fuente_id = fuente.id)"
        )
        print("=== Condiciones de la medida ===")
        print(f"  corpus oficial ....... {fragmentos} fragmentos de {fuentes} fuente(s)")
        print(f"  umbral oficial ....... {settings.RAG_UMBRAL_SIMILITUD}")
        print(f"  umbral comunitario ... {settings.RAG_UMBRAL_COMUNITARIO}")
        print(f"  top-k ................ {settings.RAG_TOP_K}")
        print(f"  modelo generativo .... {settings.GEMINI_GENERATIVE_MODEL}")
        print(
            "\n  CUIDADO: estos son los valores del .env local. Si Railway "
            "define otros,\n  la prueba corrió con los suyos y hay que "
            "mirarlos en el panel.\n"
        )

        # --- De quién es la conversación --------------------------------
        if argumentos.usuaria:
            usuario_id = UUID(argumentos.usuaria)
        else:
            usuarias = await _usuarias_con_conversacion()
            if not usuarias:
                print("No hay ningún mensaje registrado todavía.")
                return
            if len(usuarias) > 1:
                print("Hay varias usuarias con conversación:")
                for identificador, cuantos in usuarias:
                    print(f"  {identificador}  {cuantos} mensajes")
                print("Se toma la primera. Use --usuaria para elegir otra.\n")
            usuario_id = usuarias[0][0]

        # --- La conversación --------------------------------------------
        turnos = await _conversacion(usuario_id)
        print(f"=== Conversación ({len(turnos)} mensajes) ===\n")
        for turno in turnos:
            marca = turno["creado_en"].strftime("%d/%m %H:%M:%S")
            quien = "USUARIA " if turno["rol"] == "usuaria" else "bot     "
            voz = " (voz)" if turno["tipo"] != "text" else ""
            print(f"  [{marca}] {quien}{voz}")
            for linea in turno["contenido"].splitlines() or [""]:
                print(f"      {linea}")
            print()

        # --- Lo que quedó guardado (CU3) --------------------------------
        print("=== Lo que se guardó (CU3) ===")
        registro = await _huerta(usuario_id)
        if registro is None:
            print("  No hay ninguna huerta registrada para esta usuaria.\n")
        else:
            huerta = registro["huerta"]
            print(f"  nombre ......... {huerta['nombre_huerta'] or '(sin nombre)'}")
            print(f"  barrio ......... {huerta['barrio']}")
            print(f"  comentarios .... {huerta['comentarios'] or '(ninguno)'}")
            print(f"  creada ......... {huerta['creado_en']:%d/%m/%Y %H:%M}")
            print(f"  actualizada .... {huerta['actualizado_en']:%d/%m/%Y %H:%M}")
            # Sin fragmento, esa huerta es invisible al CU4 de las demás:
            # la generación va fuera de la transacción del registro y puede
            # haber fallado sin tumbarlo (ADR-0011).
            print(
                f"  fragmento CU4 .. "
                f"{'sí' if huerta['tiene_fragmento'] else 'NO — invisible al CU4'}"
            )
            print(f"  cultivos ....... {len(registro['cultivos'])}")
            for cultivo in registro["cultivos"]:
                if cultivo["fecha_siembra_aprox"]:
                    fecha = f"{cultivo['fecha_siembra_aprox']:%d/%m/%Y}"
                    if cultivo["fecha_imprecisa"]:
                        fecha += " (aprox.)"
                else:
                    fecha = "sin fecha"
                print(f"      - {cultivo['especie']:<24} {fecha}")
            print()

        if argumentos.sin_remedir:
            return

        # --- Remedida de cada consulta contra el corpus real ------------
        #
        # Sobre el mensaje **entero**, que es la formulación sobre la que
        # existe la calibración (ADR-0013). Si el agente recortó, su recorte
        # puntúa por debajo de esto, no por encima: lo que se ve aquí es el
        # techo de lo que el CU2 podía recuperar.
        consultas = [t["contenido"] for t in turnos if t["rol"] == "usuaria"]
        umbral = settings.RAG_UMBRAL_SIMILITUD

        print("=== Cada mensaje suyo, remedido contra el corpus ===")
        print("(el mensaje entero: es el techo de lo que el CU2 podía recuperar)\n")

        for consulta in consultas:
            mejores = await _remedir(consulta)
            if not mejores:
                print(f"  (corpus vacío)  {_una_linea(consulta, 60)}")
                continue

            mejor = mejores[0]["similitud"]
            pasan = sum(1 for m in mejores if m["similitud"] >= umbral)
            veredicto = f"{pasan}/{TOP_K} pasan" if pasan else "NADA pasa"
            distancia = "" if pasan else f"  (le faltan {umbral - mejor:.4f})"

            print(f"  {mejor:.4f}  {veredicto:<11}{distancia}")
            print(f"          «{_una_linea(consulta, 70)}»")
            print(f"          mejor fragmento: {_una_linea(mejores[0]['contenido'], _MUESTRA)}")
            print()

        print(
            "Lectura:\n"
            "  - similitudes rozando el umbral por debajo  -> es el umbral, y se\n"
            "    baja en Railway sin desplegar (RAG_UMBRAL_SIMILITUD).\n"
            "  - similitudes bajas y fragmentos de otro tema -> es el corpus, y\n"
            "    bajar el umbral solo dejaría entrar respuestas equivocadas.\n"
            "  - un mensaje que sí pasa pero al que el bot no respondió con el\n"
            "    CU2 -> el agente no enrutó ahí; el problema está en el agente."
        )
    finally:
        await cerrar_pool()


if __name__ == "__main__":
    asyncio.run(main())
