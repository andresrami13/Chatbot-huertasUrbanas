"""Lo que el agente elige y lo que la usuaria acaba leyendo — MP-14 a MP-17.

Aquí no se prueba el modelo, que no es determinista: se prueba el código
que rodea al modelo y que sí lo es. La diferencia importa, porque es
justo ese código el que sostiene la jerarquía de fuentes (CLAUDE.md §6) y
la advertencia médica del ADR-0015.

Riesgos P-01 (una respuesta de salud sin advertencia), P-09 (un prompt que
no carga) y el rastro del ADR-0001 en la atribución comunitaria.
"""

import string
from types import SimpleNamespace

import pytest

from app import textos
from app.agent.agente import _seleccionar
from app.agent.plantillas import cargar_prompt
from app.services.orientacion import _con_advertencia_medica, _con_cita
from app.services.recuperacion import _etiquetar_comunitario, limpiar_etiquetas

_PROMPTS_VIGENTES = [
    "agente_v2.md",
    "extraccion_v3.md",
    "barrio_v1.md",
    "redaccion_rag_v2.md",
    "redaccion_comunidad_v2.md",
    "respuesta_general_v1.md",
]

# Se conservan a propósito como historial citable (CLAUDE.md §11). No los
# carga nadie, pero borrarlos rompería la trazabilidad del documento.
_PROMPTS_HISTORICOS = [
    "agente_v1.md",
    "extraccion_v1.md",
    "extraccion_v2.md",
    "redaccion_comunidad_v1.md",
    "redaccion_rag_v1.md",
]


def _llamada(nombre: str):
    """Una llamada de función con la forma mínima que `_seleccionar` mira."""
    return SimpleNamespace(name=nombre, args={"pregunta": "lo que sea"})


# --- MP-14: selección y orden de las llamadas ------------------------
# Tabla de decisión de tres reglas: sin repetidas, la ayuda cede, el
# registro al final.


def test_mp14_el_registro_va_siempre_el_ultimo():
    """Lleva botones, y los botones tienen que quedar en el último mensaje.

    Si no, ella los pulsaría con la respuesta de otra cosa encima.
    """
    elegidas = _seleccionar([_llamada("registrar_huerta"), _llamada("consultar_orientacion")])
    assert [l.name for l in elegidas] == ["consultar_orientacion", "registrar_huerta"]


def test_mp14_no_se_ejecuta_dos_veces_la_misma():
    """Dos llamadas iguales darían dos veces la misma respuesta."""
    elegidas = _seleccionar([_llamada("consultar_orientacion")] * 3)
    assert len(elegidas) == 1


def test_mp14_la_ayuda_cede_ante_una_respuesta_real():
    """La bienvenida existe para cuando no hay nada que hacer."""
    elegidas = _seleccionar([_llamada("mostrar_ayuda"), _llamada("consultar_orientacion")])
    assert [l.name for l in elegidas] == ["consultar_orientacion"]


def test_mp14_la_ayuda_sola_se_queda():
    elegidas = _seleccionar([_llamada("mostrar_ayuda")])
    assert [l.name for l in elegidas] == ["mostrar_ayuda"]


def test_mp14_una_herramienta_desconocida_se_ignora():
    elegidas = _seleccionar([_llamada("hacer_cualquier_cosa"), _llamada("mostrar_ayuda")])
    assert [l.name for l in elegidas] == ["mostrar_ayuda"]


def test_mp14_no_se_manda_una_rafaga_de_mensajes():
    """Tope de llamadas por turno: la usuaria no puede recibir cinco mensajes."""
    elegidas = _seleccionar(
        [
            _llamada("consultar_orientacion"),
            _llamada("consultar_comunidad"),
            _llamada("consultar_mi_huerta"),
            _llamada("registrar_huerta"),
        ]
    )
    assert len(elegidas) <= 3


def test_mp14_sin_llamadas_no_se_elige_nada():
    assert _seleccionar([]) == []


# --- MP-15: los prompts versionados cargan ---------------------------


@pytest.mark.parametrize("nombre", _PROMPTS_VIGENTES)
def test_mp15_los_prompts_vigentes_cargan(nombre):
    assert cargar_prompt(nombre).strip()


@pytest.mark.parametrize("nombre", _PROMPTS_VIGENTES)
def test_mp15_ningun_prompt_tiene_una_llave_suelta(nombre):
    """Los huecos se rellenan con `str.format`: una llave literal rompe la carga.

    El fallo aparecería en producción como un `KeyError` a mitad del turno,
    no al desplegar. Esto lo adelanta al momento de escribir el prompt.
    """
    list(string.Formatter().parse(cargar_prompt(nombre)))


def test_mp15_el_prompt_del_agente_no_lleva_huecos():
    """Se carga tal cual, a propósito: no se le aplica `format`."""
    campos = [
        campo
        for _, campo, _, _ in string.Formatter().parse(cargar_prompt("agente_v2.md"))
        if campo is not None
    ]
    assert campos == []


@pytest.mark.parametrize("nombre", _PROMPTS_HISTORICOS)
def test_mp15_los_prompts_historicos_siguen_en_el_repositorio(nombre):
    """No los carga nadie, y aun así tienen que estar: son evidencia citable."""
    assert cargar_prompt(nombre).strip()


def test_mp15_un_prompt_inexistente_falla_de_forma_explicita():
    """Tratarlo como cadena vacía haría que el modelo respondiera cualquier cosa."""
    with pytest.raises(FileNotFoundError):
        cargar_prompt("prompt_que_no_existe_v9.md")


# --- MP-16: la advertencia médica ------------------------------------


@pytest.mark.parametrize(
    "respuesta",
    [
        "La caléndula tiene propiedades medicinales conocidas.",
        "Esta planta es tóxica si se consume.",
        "Se usa en infusión para la tos.",
        "No se recomienda durante el embarazo.",
        "Tiene efecto antiinflamatorio.",
    ],
)
def test_mp16_lo_que_habla_de_salud_lleva_advertencia(respuesta):
    """La pone el backend, no el prompt: así cubre los dos caminos del CU2."""
    assert textos.ADVERTENCIA_MEDICA in _con_advertencia_medica(respuesta)


@pytest.mark.parametrize(
    "respuesta",
    [
        "Siembre el tomate a 20 centímetros de distancia.",
        "El compost necesita voltearse cada semana.",
        "Riegue por la mañana temprano.",
    ],
)
def test_mp16_lo_que_no_habla_de_salud_no_la_lleva(respuesta):
    assert _con_advertencia_medica(respuesta) == respuesta


def test_mp16_la_advertencia_va_al_final():
    """Después de la línea de la fuente, para no romper la atribución."""
    respuesta = "Es medicinal.\n\nFuente: Jardín Botánico de Bogotá"
    resultado = _con_advertencia_medica(respuesta)

    assert resultado.startswith(respuesta)
    assert resultado.endswith(textos.ADVERTENCIA_MEDICA)


# No se exige que la advertencia sea idempotente, y conviene dejarlo
# escrito para que nadie vuelva a añadir esa prueba (incidencia INC-003).
# Aplicarla dos veces sí apila el texto, pero eso no ocurre: los dos
# puntos de llamada de `orientacion.py` están en ramas mutuamente
# excluyentes —el camino con RAG y el camino sin respaldo— y el propio
# ADR-0015 la sitúa sobre el texto que se va a enviar. Exigir idempotencia
# sería probar una propiedad que el sistema no necesita.


# --- MP-17: las etiquetas de procedencia no se cuelan ----------------


def test_mp17_la_etiqueta_entera_se_quita_y_la_atribucion_se_queda():
    """De `[COMUNITARIO – La Esperanza, Holanda]` queda `La Esperanza, Holanda`.

    Lo que se retira es andamiaje del prompt; la atribución es lo que la
    usuaria necesita para saber que ese dato no es de su barrio (ADR-0001).
    """
    limpia = limpiar_etiquetas("[COMUNITARIO – La Esperanza, Holanda] siembra tomate")

    assert "COMUNITARIO" not in limpia
    assert "[" not in limpia and "]" not in limpia
    assert "La Esperanza, Holanda" in limpia


def test_mp17_la_etiqueta_suelta_tambien_se_quita():
    """Sin corchetes es como se coló de verdad en la prueba con celular."""
    limpia = limpiar_etiquetas("OFICIAL – Jardín Botánico: riegue por la mañana")

    assert "OFICIAL" not in limpia
    assert "Jardín Botánico" in limpia


def test_mp17_una_respuesta_limpia_no_se_toca():
    respuesta = "Riegue por la mañana temprano."
    assert limpiar_etiquetas(respuesta) == respuesta


def test_mp17_los_espacios_dobles_se_colapsan():
    assert "  " not in limpiar_etiquetas("[OFICIAL – JBB]  riegue  temprano")


def test_mp17_la_huerta_sin_nombre_se_identifica_por_su_barrio():
    """Es lo único que se puede decir de ella sin inventar."""
    fragmento = SimpleNamespace(nombre_huerta=None, barrio="HOLANDA", contenido="tomate")
    assert "una huerta del barrio HOLANDA" in _etiquetar_comunitario(fragmento)


def test_mp17_la_huerta_con_nombre_lo_lleva_junto_al_barrio():
    fragmento = SimpleNamespace(
        nombre_huerta="La Esperanza", barrio="HOLANDA", contenido="tomate"
    )
    etiquetado = _etiquetar_comunitario(fragmento)

    assert "[COMUNITARIO – La Esperanza, HOLANDA]" in etiquetado
    assert etiquetado.endswith("tomate")


# --- MP-24: la línea de la fuente la pone el backend (ADR-0025) -------
#
# Es el defecto INC-020: 6 de 20 respuestas del banco decían «no tengo esa
# información» y llevaban `Fuente: Jardín Botánico` al pie. Estos casos son
# lo que impide que vuelva a pasar sin que nadie se entere.

_ENTIDAD = "Jardín Botánico de Bogotá José Celestino Mutis"


def test_mp24_una_respuesta_normal_lleva_la_cita_del_backend():
    resultado = _con_cita("Riegue temprano en la mañana.", _ENTIDAD)

    assert resultado == f"Riegue temprano en la mañana.\n\nFuente: {_ENTIDAD}"


def test_mp24_con_la_marca_no_se_cita():
    """El caso de INC-020: si el modelo declinó, no se le atribuye a nadie."""
    resultado = _con_cita(
        "No tengo esa información. Pregúnteme de otra manera.\n\n[[SIN_RESPALDO]]",
        _ENTIDAD,
    )

    assert "Fuente" not in resultado
    assert "SIN_RESPALDO" not in resultado
    assert resultado == "No tengo esa información. Pregúnteme de otra manera."


@pytest.mark.parametrize(
    "marca",
    [
        "[[SIN_RESPALDO]]",
        "[SIN_RESPALDO]",
        "SIN_RESPALDO",
        "sin_respaldo",
        "[[ SIN_RESPALDO ]]",
    ],
)
def test_mp24_la_marca_se_reconoce_como_la_escriba(marca):
    """No se puede depender de que la copie exacta: sale a temperatura 0.4."""
    assert "Fuente" not in _con_cita(f"No lo sé.\n{marca}", _ENTIDAD)


def test_mp24_la_frase_corriente_sin_respaldo_no_es_la_marca():
    """Sin el guion bajo no es marca, o se perdería la cita sin motivo."""
    resultado = _con_cita("Se lo digo sin respaldo de otra guía.", _ENTIDAD)

    assert f"Fuente: {_ENTIDAD}" in resultado


def test_mp24_la_fuente_que_escriba_el_modelo_se_retira():
    """El prompt se lo prohíbe; esto es la red, como con las etiquetas."""
    resultado = _con_cita("Riegue temprano.\n\nFuente: Otra entidad que no es\n", _ENTIDAD)

    assert resultado.count("Fuente:") == 1
    assert resultado.endswith(f"Fuente: {_ENTIDAD}")


def test_mp24_la_fuente_del_modelo_se_retira_tambien_si_declino():
    """Los dos defectos a la vez: declina, cita, y la cita es suya."""
    resultado = _con_cita(
        "No tengo esa información.\n\nFuente: Jardín Botánico\n[[SIN_RESPALDO]]",
        _ENTIDAD,
    )

    assert "Fuente" not in resultado


def test_mp24_la_entidad_es_la_que_recibe_y_no_la_que_diga_el_modelo():
    """Sale de la tabla `fuente` por la clave foránea, no del texto."""
    assert _con_cita("Voltee la pila cada semana.", "FAO").endswith("Fuente: FAO")


def test_mp24_no_quedan_renglones_vacios_de_mas():
    """Quitar la marca y la fuente deja huecos, y la usuaria los ve."""
    resultado = _con_cita("Riegue temprano.\n\n\n\n[[SIN_RESPALDO]]", _ENTIDAD)

    assert "\n\n\n" not in resultado
    assert resultado == "Riegue temprano."


def test_mp24_la_advertencia_medica_va_despues_de_la_cita():
    """El orden importa: la advertencia cierra el mensaje, siempre."""
    citado = _con_cita("El romero es medicinal para el dolor de cabeza.", _ENTIDAD)
    resultado = _con_advertencia_medica(citado)

    assert resultado.index("Fuente:") < resultado.index(textos.ADVERTENCIA_MEDICA)
