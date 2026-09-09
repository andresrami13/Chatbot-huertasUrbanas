"""Recalibra el umbral del CU2 con las consultas de la prueba real (Fase 7).

    python -m scripts.calibrar_umbral_real

No escribe nada. Fue el compañero de `scripts/calibrar_umbral.py`, que se
**borró el 08/09/2026** y vive en el historial de git. Lo que cambiaba
entre los dos es de dónde salen las consultas:

- `calibrar_umbral.py` las imaginó el autor. Doce positivas y seis
  negativas, escritas en el vocabulario del documento. Dieron el 0.68 del
  ADR-0010, con un margen de una centésima.
- **este** las escribió una persona hablándole al bot por WhatsApp, sin
  saber qué había dentro del corpus.

## Qué se descubrió al medirlas

Dos cosas que la calibración original no podía ver.

**1. El umbral dejó de ser el filtro de intención.** El ADR-0010 lo calibró
contra seis controles negativos —"a qué hora abre el banco", "cuándo cambio
el aceite del carro"— porque entonces cualquier mensaje libre llegaba al
CU2. Desde el paso 4c de la Fase 6 eso ya no ocurre: el agente decide la
intención y esos mensajes ni entran. En la prueba real, "que carro está
barato hoy en día" lo atajó el agente antes de llegar aquí.

Consecuencia: **el umbral ya no protege de una intención ajena, solo de una
respuesta mala**, y seguía puesto a la altura de la protección que ya no le
toca.

**2. Las consultas no se parten en dos grupos, sino en tres.** La
clasificación de abajo es el hallazgo, y es lo que impide bajar el umbral
todo lo que uno querría:

- `CUBIERTA` — es del dominio y el documento la responde. El umbral tiene
  que dejarla pasar.
- `DESCUBIERTA` — es del dominio, pero el corpus no la trata: ornamentales
  que no son huerta, o una especie que solo aparece dentro de una lista.
  **Bajar el umbral no las salva**; lo único que consigue es que se
  respondan con el fragmento equivocado y la fuente citada al pie, que es
  peor que callar. Estas son las que piden más corpus.
- `NO_ES_CU2` — saludo, ayuda, registro, comunidad, botón. Hoy las atrapa
  el agente antes de llegar aquí.

Así que el umbral se elige donde mejor separa `CUBIERTA` de `DESCUBIERTA`,
que es una frontera distinta de la que se midió en el ADR-0010.

## Sobre lo que este archivo NO contiene

El repositorio es público. De la conversación real solo se traen aquí las
consultas agronómicas y los mensajes de pura forma, que no dicen nada de
quien escribe. Quedan fuera los que nombran el barrio y uno de emergencia
familiar; sus similitudes van de 0.5618 a 0.5917, muy por debajo de
cualquier umbral candidato, así que no cambian ninguna conclusión.

La conversación completa se recupera cuando haga falta con
`python -m scripts.revisar_prueba_real`, que la lee de la base y no la
versiona.
"""

import asyncio
import statistics

from app.config import settings
from app.core.basedatos import abrir_pool, cerrar_pool, obtener_pool
from app.services.embeddings import vectorizar_consulta

# Del dominio, y el documento del Jardín Botánico las responde. Son las que
# el umbral tiene que dejar pasar.
CUBIERTAS = [
    "Necesito saber que plantas son las más comunes que se pueden sembrar "
    "en Bogotá, para yo sembrar en mi huerta?",
    "¿Qué hierbas podría sembrar yo?",
    "Que tipo de plantas me recomiendas que son más aptas para donde yo vivo",
    "A mí mata de tomate le salieron unos bichitos verdes, que le echo",
    "Cuál es la planta más común para sembrar?",
    "Que recomendaciones me das para sembrar papa?",
    "Cómo puedo sembrar limonaria?",
]

# Del dominio pero fuera del corpus. Dos son plantas de adorno, que no son
# huerta; la tercera pide los cuidados de una especie que el documento solo
# menciona dentro de una lista de nombres. Ningún umbral las arregla.
DESCUBIERTAS = [
    "Tengo un bonsai que le salieron unos bichitos blancos que dejan la "
    "planta pegajosa",
    "Dime qué cuidados debería tener con la mata de limonaria",
    "Si quiero que mi planta millonaria crezca más que podría hacer?",
]

# No son consultas al CU2: saludo, ayuda, registro de la propia huerta,
# pregunta por la comunidad y respuesta de botón. Hoy las enruta el agente
# a otra parte y no llegan aquí, pero se miden porque dicen cuánto margen
# queda si alguna vez se equivoca — y ya se le midió un error de
# enrutamiento en esta misma prueba.
NO_ES_CU2 = [
    "Que he sembrado yo al momento?",
    "Dame un resumen de lo que tengo sembrado",
    "Tienes información de otras huertas cercanas?",
    "Que conocimiento en agricultura sabes, para así yo poder preguntarte?",
    "Mira que sembré una mata de cilantro en marzo",
    "Yo he sembrado papa el año pasado, y hasta ahorita he podido ver qué "
    "si tengo una que otra papa pequeñita",
    "Sí, guardar",
    "Necesito ayuda",
    "Dime qué cosas puntuales sabes que te puedo preguntar",
    "Que carro está barato hoy en día?",
    "Hola",
]

GRUPOS = [
    ("CUBIERTA", CUBIERTAS, "debe pasar"),
    ("DESCUBIERTA", DESCUBIERTAS, "no la salva el umbral"),
    ("NO_ES_CU2", NO_ES_CU2, "no debe pasar"),
]

UMBRALES = [0.62, 0.63, 0.64, 0.65, 0.66, 0.67, 0.68, 0.70]


async def _mejores(pool, vector: list[float], top_k: int) -> list[float]:
    """Similitudes de los `top_k` fragmentos más cercanos.

    Misma cuenta que el repositorio en producción: `1 - (a <=> b)`, de
    distancia a similitud. Sin filtrar por umbral, que es justo lo que se
    está eligiendo.
    """
    filas = await pool.fetch(
        """
        select 1 - (embedding <=> $1::vector) as similitud
          from fragmento_oficial
         order by embedding <=> $1::vector
         limit $2
        """,
        "[" + ",".join(repr(componente) for componente in vector) + "]",
        top_k,
    )
    return [fila["similitud"] for fila in filas]


async def main() -> None:
    await abrir_pool()
    try:
        pool = obtener_pool()
        top_k = settings.RAG_TOP_K
        total = await pool.fetchval("select count(*) from fragmento_oficial")

        print(f"Corpus oficial: {total} fragmentos | top-k {top_k} | "
              f"umbral vigente {settings.RAG_UMBRAL_SIMILITUD}\n")

        medidas: dict[str, list[tuple[str, list[float]]]] = {}

        for etiqueta, consultas, nota in GRUPOS:
            print(f"--- {etiqueta} ({nota}) ---")
            grupo = []
            for consulta in consultas:
                similitudes = await _mejores(
                    pool, await vectorizar_consulta(consulta), top_k
                )
                grupo.append((consulta, similitudes))
                recorte = consulta if len(consulta) <= 62 else consulta[:61] + "…"
                print(f"  {similitudes[0]:.4f}  (4.ª: {similitudes[-1]:.4f})  {recorte}")
            medidas[etiqueta] = sorted(grupo, key=lambda par: -par[1][0])
            print()

        cubiertas = [s[0] for _, s in medidas["CUBIERTA"]]
        descubiertas = [s[0] for _, s in medidas["DESCUBIERTA"]]
        no_cu2 = [s[0] for _, s in medidas["NO_ES_CU2"]]

        # --- Dónde cae la frontera que ahora importa ---------------------
        #
        # La del ADR-0010 era CUBIERTA contra NO_ES_CU2, y hoy la vigila el
        # agente. La que le queda al umbral es CUBIERTA contra DESCUBIERTA:
        # decidir a partir de qué similitud el documento tiene de verdad
        # algo que decir.
        print("--- La frontera que le queda al umbral ---")
        peor_cubierta = min(cubiertas)
        mejor_descubierta = max(descubiertas)
        print(f"  peor CUBIERTA ........ {peor_cubierta:.4f}")
        print(f"  mejor DESCUBIERTA .... {mejor_descubierta:.4f}")
        print(f"  hueco ................ {peor_cubierta - mejor_descubierta:+.4f}")
        if peor_cubierta > mejor_descubierta:
            centro = (peor_cubierta + mejor_descubierta) / 2
            print(f"  centro del hueco ..... {centro:.4f}")
        print()

        print("--- La frontera que el ADR-0010 midió, y que ya no vigila el umbral ---")
        mejor_no_cu2 = max(no_cu2)
        print(f"  peor CUBIERTA ........ {peor_cubierta:.4f}")
        print(f"  mejor NO_ES_CU2 ...... {mejor_no_cu2:.4f}")
        print(f"  hueco ................ {peor_cubierta - mejor_no_cu2:+.4f}")
        print(
            "  Negativo: los rangos se solapan y NINGÚN umbral separa los dos\n"
            "  grupos. Quien los separa hoy es el agente (function calling),\n"
            "  no el umbral. Ver el ADR-0013.\n"
        )

        # --- Qué haría cada candidato ------------------------------------
        print("--- Qué haría cada umbral ---")
        print(f"  {'umbral':>7}  {'responde':>10}  {'sin corpus':>11}  "
              f"{'no es CU2':>10}  {'frag./consulta':>15}")
        for umbral in UMBRALES:
            pasan_cub = sum(1 for m in cubiertas if m >= umbral)
            pasan_des = sum(1 for m in descubiertas if m >= umbral)
            pasan_no = sum(1 for m in no_cu2 if m >= umbral)
            recuperados = [
                sum(1 for s in similitudes if s >= umbral)
                for _, similitudes in medidas["CUBIERTA"]
            ]
            marca = " <-- vigente" if abs(umbral - settings.RAG_UMBRAL_SIMILITUD) < 1e-9 else ""
            print(
                f"  {umbral:>7.2f}  {pasan_cub:>4}/{len(cubiertas):<5}  "
                f"{pasan_des:>4}/{len(descubiertas):<6}  "
                f"{pasan_no:>4}/{len(no_cu2):<5}  "
                f"{statistics.mean(recuperados):>15.1f}{marca}"
            )

        print(
            "\nLectura:\n"
            "  - 'responde' es lo que se gana: consultas legítimas que el\n"
            "    documento cubre y hoy se quedan sin contestar.\n"
            "  - 'sin corpus' es lo que se pierde: respuestas construidas con\n"
            "    el fragmento equivocado, y encima citando la fuente.\n"
            "  - 'no es CU2' no es un coste hoy, porque el agente las desvía\n"
            "    antes; es el margen que queda si el agente se equivoca."
        )
    finally:
        await cerrar_pool()


if __name__ == "__main__":
    asyncio.run(main())
