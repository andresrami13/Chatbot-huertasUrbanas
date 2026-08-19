"""Extracción de los cultivos de la huerta (Fase 4, Tabla 3).

Convierte lo que la usuaria escribió —o dictó— en los cultivos del CU3.

Cuatro decisiones que vienen de las fases y no deben cambiarse aquí:

- **Temperatura 0.1, fija** (CLAUDE.md §8). Es la única de la tabla que no
  se calibra: el formato es estricto y la variabilidad solo puede
  estropearlo.
- **Ni el barrio ni el nombre de la huerta se extraen aquí** (ADR-0016).
  Los dos se preguntan en el onboarding, una pregunta por mensaje, y ya
  están guardados cuando este extractor entra en juego. Antes sí se
  extraían, por la decisión 5 del ADR-0008: `huerta.barrio_id` es NOT NULL
  y no había otro momento donde preguntarlo.
- **La fecha de siembra tampoco se extrae** (ADR-0018). Era un dato de
  solo escritura: nadie lo leía, y el ADR-0011 ya había medido que metido
  en el fragmento comunitario empeoraba la recuperación. Las columnas
  salieron de `cultivo` en la migración 008.
- **Nada se persiste aquí.** Esta función solo lee y devuelve; el CU3 tiene
  que mostrar el resultado y esperar la confirmación de la usuaria antes de
  guardar (CLAUDE.md §4.7).

Que el barrio saliera de aquí tiene además un motivo de coste: el catálogo
pasó de 8 a 313 barrios (ADR-0016), y su enum viajaba en **cada** llamada de
extracción, que ocurre en cada mensaje. La desambiguación del barrio lo
paga una sola vez, en el onboarding.

Con la fecha fuera, el modelo tiene un solo campo que acertar por cultivo y
el prompt se quedó en la mitad. Es el mismo efecto que buscaba el ADR-0016
al sacarle el barrio: cada campo que se le quita es un campo menos que
puede equivocar.
"""

import json
import logging
from dataclasses import dataclass, field

from google.genai import types

from app.agent.plantillas import cargar_prompt
from app.core.gemini import MODELO_GENERATIVO, obtener_cliente

logger = logging.getLogger(__name__)

_PROMPT = "extraccion_v3.md"

# Fija por decisión documentada, no calibrable (CLAUDE.md §8).
_TEMPERATURA = 0.1

_ESQUEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "cultivos": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "especie": types.Schema(type=types.Type.STRING),
                },
                required=["especie"],
            ),
        ),
    },
    required=["cultivos"],
)


@dataclass(frozen=True)
class CultivoExtraido:
    """Un cultivo tal como lo entendió el modelo, todavía sin confirmar."""

    especie: str


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


def _limpiar_cultivo(bruto: dict) -> CultivoExtraido | None:
    """Valida un cultivo del modelo. Devuelve None si no es aprovechable."""
    especie = (bruto.get("especie") or "").strip()
    if not especie:
        # Sin especie no hay cultivo que guardar.
        return None

    return CultivoExtraido(especie=especie)


async def extraer_huerta(mensaje: str) -> HuertaExtraida:
    """Extrae los cultivos que haya en el mensaje.

    Devuelve una `HuertaExtraida` vacía si el mensaje no habla de cultivos
    o si el modelo falla. Nunca lanza: quien llama sigue el flujo del CU3, y
    un fallo de extracción no debe tumbar la conversación.

    Ya no recibe `hoy`: se inyectaba para poder probar las fechas
    relativas, y no hay fechas que resolver (ADR-0018).
    """
    prompt = cargar_prompt(_PROMPT).format(mensaje=mensaje)

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
            cultivo = _limpiar_cultivo(bruto)
            if cultivo is not None:
                cultivos.append(cultivo)

    extraida = HuertaExtraida(cultivos=cultivos)

    # Nunca el contenido (CLAUDE.md §11): se registra la forma de lo
    # extraído, no lo extraído.
    logger.info("Extracción | cultivos=%d", len(extraida.cultivos))

    return extraida
