"""Extracción de entidades de la huerta (Fase 4, Tabla 3).

Convierte lo que la usuaria escribió —o dictó— en los datos estructurados
del CU3: nombre de la huerta, barrio y cultivos con su fecha aproximada.

Tres decisiones que vienen de las fases y no deben cambiarse aquí:

- **Temperatura 0.1, fija** (CLAUDE.md §8). Es la única de la tabla que no
  se calibra: el formato es estricto y la variabilidad solo puede
  estropearlo.
- **El enum de barrios se genera leyendo la tabla `barrio`**, nunca escrito
  a mano (ADR-0002). Añadir un barrio es un INSERT.
- **Nada se persiste aquí.** Esta función solo lee y devuelve; el CU3 tiene
  que mostrar el resultado y esperar la confirmación de la usuaria antes de
  guardar (CLAUDE.md §4.7).

Sobre la salida estructurada: el esquema obliga al modelo a devolver un
código de barrio válido, así que no hace falta validar contra el catálogo
después. Lo que el esquema no puede garantizar es que el mes esté entre 1 y
12 ni que el año sea razonable, y eso sí se comprueba abajo.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import date

from google.genai import types

from app.agent.plantillas import cargar_prompt
from app.core.gemini import MODELO_GENERATIVO, obtener_cliente
from app.services.repositorio import Barrio, listar_barrios

logger = logging.getLogger(__name__)

_PROMPT = "extraccion_v1.md"

# Fija por decisión documentada, no calibrable (CLAUDE.md §8).
_TEMPERATURA = 0.1

# Margen de cordura para el año. Una huerta sembrada antes de esto, o en el
# futuro, es un error de extracción, no un dato.
_ANIO_MINIMO = 2015


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
    """Lo extraído de un mensaje. Ningún campo es obligatorio.

    Que todo pueda venir vacío es lo correcto: el mensaje pudo no hablar de
    la huerta en absoluto. `tiene_datos` distingue ese caso.
    """

    nombre_huerta: str | None = None
    barrio_codigo: str | None = None
    cultivos: list[CultivoExtraido] = field(default_factory=list)

    @property
    def tiene_datos(self) -> bool:
        return bool(self.nombre_huerta or self.barrio_codigo or self.cultivos)


def _construir_esquema(barrios: list[Barrio]) -> types.Schema:
    """Arma el esquema de salida con el enum del catálogo."""
    return types.Schema(
        type=types.Type.OBJECT,
        properties={
            "nombre_huerta": types.Schema(
                type=types.Type.STRING,
                nullable=True,
                description="Cómo llama la usuaria a su huerta. null si no lo dice.",
            ),
            "barrio": types.Schema(
                type=types.Type.STRING,
                enum=[barrio.codigo for barrio in barrios],
                nullable=True,
                description="Código del barrio. null si no lo menciona.",
            ),
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
        required=["nombre_huerta", "barrio", "cultivos"],
    )


def _texto_barrios(barrios: list[Barrio]) -> str:
    """La lista para el prompt: código y nombre, uno por línea."""
    return "\n".join(f"- `{barrio.codigo}` — {barrio.nombre}" for barrio in barrios)


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
    """Extrae los datos de la huerta que haya en el mensaje.

    Devuelve una `HuertaExtraida` vacía si el mensaje no habla de la huerta
    o si el modelo falla. Nunca lanza: quien llama sigue el flujo del CU3, y
    un fallo de extracción no debe tumbar la conversación.

    `hoy` es inyectable para poder probar las fechas relativas.
    """
    hoy = hoy or date.today()
    barrios = await listar_barrios()

    if not barrios:
        # Sin catálogo no hay enum, y sin enum el modelo devolvería barrios
        # inventados. Es un fallo de instalación: falta ejecutar 002.
        logger.error("El catálogo de barrios está vacío; no se puede extraer")
        return HuertaExtraida()

    prompt = cargar_prompt(_PROMPT).format(
        barrios=_texto_barrios(barrios),
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
                response_schema=_construir_esquema(barrios),
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

    nombre = (datos.get("nombre_huerta") or "").strip() or None

    cultivos = []
    for bruto in datos.get("cultivos") or []:
        if isinstance(bruto, dict):
            cultivo = _limpiar_cultivo(bruto, hoy)
            if cultivo is not None:
                cultivos.append(cultivo)

    extraida = HuertaExtraida(
        nombre_huerta=nombre,
        barrio_codigo=datos.get("barrio") or None,
        cultivos=cultivos,
    )

    # Nunca el contenido (CLAUDE.md §11): se registra la forma de lo
    # extraído, no lo extraído. El barrio sí, que es un código del catálogo
    # y no identifica a nadie por sí solo.
    logger.info(
        "Extracción | nombre=%s | barrio=%s | cultivos=%d | sin_fecha=%d",
        extraida.nombre_huerta is not None,
        extraida.barrio_codigo,
        len(extraida.cultivos),
        sum(1 for c in extraida.cultivos if c.fecha_siembra() is None),
    )

    return extraida
