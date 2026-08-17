"""Extracción de los cultivos de la huerta (Fase 4, Tabla 3).

Convierte lo que la usuaria escribió —o dictó— en los cultivos del CU3, con
su fecha aproximada de siembra.

Tres decisiones que vienen de las fases y no deben cambiarse aquí:

- **Temperatura 0.1, fija** (CLAUDE.md §8). Es la única de la tabla que no
  se calibra: el formato es estricto y la variabilidad solo puede
  estropearlo.
- **Ni el barrio ni el nombre de la huerta se extraen aquí** (ADR-0016).
  Los dos se preguntan en el onboarding, una pregunta por mensaje, y ya
  están guardados cuando este extractor entra en juego. Antes sí se
  extraían, por la decisión 5 del ADR-0008: `huerta.barrio_id` es NOT NULL
  y no había otro momento donde preguntarlo.
- **Nada se persiste aquí.** Esta función solo lee y devuelve; el CU3 tiene
  que mostrar el resultado y esperar la confirmación de la usuaria antes de
  guardar (CLAUDE.md §4.7).

Que el barrio saliera de aquí tiene además un motivo de coste: el catálogo
pasó de 8 a 313 barrios (ADR-0016), y su enum viajaba en **cada** llamada de
extracción, que ocurre en cada mensaje. La desambiguación del barrio lo
paga una sola vez, en el onboarding.

Sobre la salida estructurada: el esquema garantiza el tipo, no el rango. Que
el mes esté entre 1 y 12 y que el año sea razonable se comprueba abajo.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import date

from google.genai import types

from app.agent.plantillas import cargar_prompt
from app.core.gemini import MODELO_GENERATIVO, obtener_cliente

logger = logging.getLogger(__name__)

_PROMPT = "extraccion_v2.md"

# Fija por decisión documentada, no calibrable (CLAUDE.md §8).
_TEMPERATURA = 0.1

# Margen de cordura para el año. Una huerta sembrada antes de esto, o en el
# futuro, es un error de extracción, no un dato.
_ANIO_MINIMO = 2015

_ESQUEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "cultivos": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "especie": types.Schema(type=types.Type.STRING),
                    "anio": types.Schema(type=types.Type.INTEGER, nullable=True),
                    "mes": types.Schema(
                        type=types.Type.INTEGER,
                        nullable=True,
                        description="Mes de siembra, de 1 a 12.",
                    ),
                    "fecha_imprecisa": types.Schema(type=types.Type.BOOLEAN),
                },
                required=["especie", "anio", "mes", "fecha_imprecisa"],
            ),
        ),
    },
    required=["cultivos"],
)


@dataclass(frozen=True)
class CultivoExtraido:
    """Un cultivo tal como lo entendió el modelo, todavía sin confirmar."""

    especie: str
    anio: int | None
    mes: int | None
    # "Marca de imprecisión" de la Fase 4, Tabla 3: distingue lo que la
    # usuaria precisó de lo que el modelo aproximó. Se usa para afinar la
    # fecha en la confirmación del CU3.
    fecha_imprecisa: bool

    def fecha_siembra(self) -> date | None:
        """La fecha como la espera `cultivo.fecha_siembra_aprox`.

        La Fase 4 normaliza a mes y año, así que se guarda el día 1.
        """
        if self.anio is None or self.mes is None:
            return None
        return date(self.anio, self.mes, 1)


@dataclass(frozen=True)
class HuertaExtraida:
    """Lo extraído de un mensaje. Puede venir vacío.

    Que pueda venir vacío es lo correcto: el mensaje pudo no hablar de la
    huerta en absoluto. `tiene_datos` distingue ese caso.

    Desde el ADR-0016 solo lleva cultivos. El nombre de la huerta y el
    barrio los fija el onboarding y se leen de `huerta`, no de aquí.
    """

    cultivos: list[CultivoExtraido] = field(default_factory=list)

    @property
    def tiene_datos(self) -> bool:
        return bool(self.cultivos)


def _limpiar_cultivo(bruto: dict, hoy: date) -> CultivoExtraido | None:
    """Valida un cultivo del modelo. Devuelve None si no es aprovechable."""
    especie = (bruto.get("especie") or "").strip()
    if not especie:
        # Sin especie no hay cultivo que guardar.
        return None

    anio = bruto.get("anio")
    mes = bruto.get("mes")
    imprecisa = bool(bruto.get("fecha_imprecisa", True))

    # El esquema garantiza el tipo, no el rango. Una fecha fuera de rango se
    # descarta y el cultivo se conserva sin fecha: perder la especie porque
    # el mes vino mal sería peor.
    if mes is not None and not 1 <= mes <= 12:
        logger.warning("Mes fuera de rango en la extracción | mes=%s", mes)
        anio, mes, imprecisa = None, None, True

    if anio is not None and not _ANIO_MINIMO <= anio <= hoy.year:
        logger.warning("Año fuera de rango en la extracción | anio=%s", anio)
        anio, mes, imprecisa = None, None, True

    # Un mes sin año, o al contrario, no forma una fecha utilizable.
    if (anio is None) != (mes is None):
        anio, mes, imprecisa = None, None, True

    return CultivoExtraido(
        especie=especie, anio=anio, mes=mes, fecha_imprecisa=imprecisa
    )


async def extraer_huerta(mensaje: str, hoy: date | None = None) -> HuertaExtraida:
    """Extrae los cultivos que haya en el mensaje.

    Devuelve una `HuertaExtraida` vacía si el mensaje no habla de cultivos
    o si el modelo falla. Nunca lanza: quien llama sigue el flujo del CU3, y
    un fallo de extracción no debe tumbar la conversación.

    `hoy` es inyectable para poder probar las fechas relativas.
    """
    hoy = hoy or date.today()

    prompt = cargar_prompt(_PROMPT).format(
        hoy=hoy.isoformat(),
        mensaje=mensaje,
    )

    try:
        respuesta = await obtener_cliente().aio.models.generate_content(
            model=MODELO_GENERATIVO,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=_TEMPERATURA,
                response_mime_type="application/json",
                response_schema=_ESQUEMA,
            ),
        )
    except Exception:
        logger.exception("Gemini falló al extraer las entidades")
        return HuertaExtraida()

    try:
        datos = json.loads(respuesta.text or "{}")
    except json.JSONDecodeError:
        # Con salida estructurada no debería ocurrir. Si ocurre, es un
        # cambio de comportamiento del modelo y conviene que se vea.
        logger.error("La extracción no devolvió JSON válido")
        return HuertaExtraida()

    cultivos = []
    for bruto in datos.get("cultivos") or []:
        if isinstance(bruto, dict):
            cultivo = _limpiar_cultivo(bruto, hoy)
            if cultivo is not None:
                cultivos.append(cultivo)

    extraida = HuertaExtraida(cultivos=cultivos)

    # Nunca el contenido (CLAUDE.md §11): se registra la forma de lo
    # extraído, no lo extraído.
    logger.info(
        "Extracción | cultivos=%d | sin_fecha=%d",
        len(extraida.cultivos),
        sum(1 for c in extraida.cultivos if c.fecha_siembra() is None),
    )

    return extraida
