"""Evaluación formativa de usabilidad a partir de los registros del sistema.

    python -m scripts.evaluacion_formativa

Calcula las medidas de eficacia y eficiencia de ISO/IEC 25022:2016 y el
tiempo de respuesta de ISO/IEC 25023 sobre la conversación real guardada en
`mensaje`, y deja las salidas en `analisis/salidas/`.

**No escribe nada en la base. Solo lee.**

## Qué contrasta

La hipótesis del documento de grado, textual: que las participantes
«completen sin asistencia al menos el 80 % de las tareas de registro inicial
(onboarding), registro de cultivos y consulta agroecológica». Son las tres
tareas, y la regla de decisión —fijada antes de conocer los resultados— es
**Ef-1-G global = ΣA ÷ ΣB ≥ 0,80**, sumando los intentos de las tres.

## Las tres tareas y su unidad de medida

| Tarea | Qué es | Unidad |
|---|---|---|
| T1 | Autorización y onboarding (CU1 + CU6) | Participante |
| T2 | Registro de cultivos (CU3) | **Intento** |
| T3 | Consulta agroecológica (CU2) | **Consulta** |

T2 y T3 se miden por intento y por consulta, y no por participante, porque
medirlas por participante las volvía **circulares**: el intento se detectaba
con la misma evidencia que la completitud, y la proporción no podía bajar
del 100 %. Es la corrección C-4 del informe.

## Por qué hace falta clasificación humana

`mensaje` no guarda qué herramienta respondió, y el camino que el sistema
eligió **no dice qué quería la participante**: cuando el agente no llama a
ninguna herramienta, manda el texto del modelo sin dejar marca (INC-025). Un
mensaje así puede ser una consulta agroecológica perfectamente atendida o
una charla cualquiera, y eso no lo decide el código.

Por eso el script exporta `clasificacion_mensajes_libres.csv` con **todos**
los mensajes libres posteriores al onboarding, para que una persona marque
qué era cada uno. Mientras esa hoja esté vacía, T2 y T3 se reportan como
**pendientes de clasificación**, nunca con un número que parezca definitivo.

**La hoja no se sobrescribe:** si ya tiene columnas humanas llenas, se
conservan y solo se añaden los mensajes nuevos.

## Privacidad de las salidas

Los CSV llevan texto literal de la conversación, así que `.gitignore` los
deja fuera: las participantes autorizaron el tratamiento de sus datos, y lo
que la autorización dice exactamente está transcrito en el anexo 12.3 del
informe. El repositorio es público.
"""

import asyncio
import csv
import json
import re
import statistics
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.basedatos import abrir_pool, cerrar_pool, obtener_pool

RAIZ = Path(__file__).resolve().parent.parent
SALIDAS = RAIZ / "analisis" / "salidas"
HOJA = SALIDAS / "clasificacion_mensajes_libres.csv"
PROPUESTAS = SALIDAS / "categorias_propuestas.json"
# Las dos hojas cortas que llena una persona, una pregunta por columna.
RUBRICA = SALIDAS / "rubrica_T3.csv"
ASISTENCIA = SALIDAS / "asistencia.csv"
RESPUESTAS = SALIDAS / "rubrica_respuestas.json"

# Bogotá no tiene horario de verano: el desplazamiento es fijo.
BOGOTA = timezone(timedelta(hours=-5))

# `categoria_propuesta` la rellena la IA y NO se edita: queda como registro
# de procedencia. `categoria_humana` arranca con esa misma propuesta y es la
# que el autor corrige; la clasificación declarada es siempre la suya.
COLUMNAS_HUMANAS = [
    "categoria_humana", "es_agroecologica",
    "pertinente_eval1", "correcta_eval1",
    "pertinente_eval2", "correcta_eval2", "asistencia",
]


# ---------------------------------------------------------------------
# Marcas de los textos que compone el backend
# ---------------------------------------------------------------------
#
# Una marca por texto de `app/textos.py`, más las dos que componen
# `onboarding.componer_resumen` y `registro.componer_resumen`. Son
# fragmentos estables y no el texto entero, porque varios textos cambiaron
# de redacción de un ADR a otro y **los mensajes viejos guardan la versión
# de su día**: ver la corrección C-1 del informe.

_MARCAS: dict[str, str] = {
    # --- T1, onboarding (CU6) ---
    "T1 pregunta nombre": r"¿cómo se llama usted",
    "T1 reintento nombre": r"no le entendí el nombre\.",
    "T1 eco nombre": r"Entendido, guardé ",
    "T1 pregunta barrio": r"¿En qué barrio de Bosa",
    "T1 reintento barrio": r"no le entendí el barrio",
    "T1 barrio sin candidatos": r"No encontré ese barrio en mi lista",
    "T1 lista de barrios": r"¿Cuál de estos es su barrio",
    "T1 numero no entendido": r"^No entendí\.",
    "T1 eco barrio": r"Entendido, anoté el barrio",
    "T1 pregunta huerta": r"¿Cómo se llama su huerta",
    "T1 reintento huerta": r"no le entendí el nombre de la huerta",
    "T1 resumen": r"^Esto es lo que voy a guardar:",
    "T1 guardado": r"ya quedó guardada su huerta",
    "T1 descartado": r"no guardé nada\.\s+Volvamos a empezar",
    "T1 fallo": r"no pude guardar la información en este momento",
    # --- T2, registro de cultivos (CU3) ---
    "T2 propuesta": r"^Esto es lo que entendí:",
    "T2 guardado": r"ya quedó guardado\.",
    "T2 descartado": r"no guardé nada\.\s+Si quiere lo intentamos",
    "T2 sin borrador": r"ya no tengo a la mano lo que iba a guardar",
    "T2 nada que anotar": r"no le entendí bien qué sembró",
    "T2 sin huerta": r"Antes de anotar lo que sembró necesito unos datos",
    # --- T3, orientación agroecológica (CU2) ---
    "T3 con cita": r"^Fuente:",
    "T3 sin respaldo": r"De eso no le puedo responder con seguridad"
    r"|no se lo puedo asegurar",
    "T3 no disponible": r"no pude consultar la información",
    "T3 advertencia medica": r"no es un consejo médico",
    # --- Otros casos de uso ---
    "CU4 listado": r"tienen sembrado otras huertas|Le repito desde el principio"
    r"|Todavía no tengo otras huertas",
    "CU5 bienvenida": r"asistente virtual de huertas urbanas"
    r"|asistente de huertas urbanas",
    "CU7 sin ese cultivo": r"De las huertas que conozco, ninguna tiene",
    "CU8 mi huerta": r"Esto es lo que tiene anotado"
    r"|Todavía no tengo ninguna planta anotada"
    r"|Todavía no tengo registrada su huerta"
    r"|^🌱 Su huerta",
    # --- Fallos del sistema ---
    "fallo comunidad": r"no pude consultar lo de las otras huertas",
    "fallo mi huerta": r"no pude consultar lo de su huerta",
    "fallo agente": r"en este momento no le puedo responder",
}

_COMPILADAS = {clave: re.compile(patron, re.M) for clave, patron in _MARCAS.items()}

# Ef-3-G: el bot declara no haber entendido. Son error de la tarea.
_ERRORES = {
    "T1 reintento nombre", "T1 reintento barrio", "T1 barrio sin candidatos",
    "T1 numero no entendido", "T1 reintento huerta",
    "T2 nada que anotar", "T2 sin huerta", "T2 sin borrador",
}
# La participante deshizo lo que ya había contestado.
_CORRECCIONES = {"T1 descartado", "T2 descartado"}
# Falló el sistema. No es error de usabilidad: columna aparte.
_FALLOS = {"T1 fallo", "T3 no disponible", "fallo comunidad", "fallo mi huerta",
           "fallo agente"}
_SIN_RESPALDO = {"T3 sin respaldo"}

# Las tres categorías de la hoja de clasificación, escritas una sola vez.
CONSULTA = "consulta agroecológica"
REGISTRO = "registro de cultivos"
OTRA = "otra"

# Lo que cuenta como «sí» en las casillas que llena una persona a mano.
_SI = {"si", "sí", "s", "x", "1", "true", "verdadero"}

_ABRE_T2 = {"T2 propuesta", "T2 nada que anotar", "T2 sin huerta"}
_CIERRA_T2 = {"T2 guardado", "T2 descartado", "T2 sin borrador"}
_MARCAS_T2 = _ABRE_T2 | _CIERRA_T2
_MARCAS_T3 = {"T3 con cita", "T3 sin respaldo", "T3 no disponible"}
# Una respuesta de otra tarea cierra el episodio de registro.
_OTRAS_TAREAS = _MARCAS_T3 | {"CU4 listado", "CU5 bienvenida",
                              "CU7 sin ese cultivo", "CU8 mi huerta"}

_MINIMOS = {"T1": 5, "T2": 2, "T3": 1}


def _marcas(texto: str) -> set[str]:
    return {clave for clave, patron in _COMPILADAS.items() if patron.search(texto)}


def _camino(respuesta: dict | None) -> str:
    """Por dónde lo llevó el sistema. No dice qué quería la participante."""
    if respuesta is None:
        return "sin respuesta registrada"
    m = respuesta["_marcas"]
    if m & _MARCAS_T3:
        return "CU2"
    if m & _MARCAS_T2:
        return "CU3"
    if "CU4 listado" in m:
        return "CU4"
    if "CU7 sin ese cultivo" in m:
        return "CU7"
    if "CU8 mi huerta" in m:
        return "CU8"
    if "CU5 bienvenida" in m:
        return "CU5"
    if m & _FALLOS:
        return "fallo"
    if not m:
        return "texto libre"
    return "otro"


# ---------------------------------------------------------------------
# Anonimización de los textos exportados
# ---------------------------------------------------------------------
#
# **Nada se descifra.** El nombre de pila, el barrio y el nombre de la
# huerta se recogen de lo que la propia participante escribió en el
# onboarding, que queda en claro en `mensaje` (INC-026), y se tapan allí
# donde vuelvan a aparecer. No se tocan las claves ni la columna cifrada.

_TRAS_PREGUNTA = {
    "nombre": {"T1 pregunta nombre", "T1 reintento nombre"},
    "barrio": {"T1 pregunta barrio", "T1 reintento barrio",
               "T1 barrio sin candidatos"},
    "huerta": {"T1 pregunta huerta", "T1 reintento huerta"},
}
# Respuestas que no identifican a nadie: el propio backend las sugiere.
_NO_TAPAR = {"vecina", "mi huerta", "ninguno", "otro", "no", "si", "sí"}

_DIRECCION = re.compile(
    r"\b(calle|cll|carrera|cra|kra|kr|diagonal|diag|transversal|trans|tv|"
    r"avenida|av|manzana|mz)\.?\s*\d+[\w\s#\-]{0,12}",
    re.I,
)
_DIGITOS = re.compile(r"\b\d{7,}\b")

# El modelo se dirige a la participante por su nombre, y no siempre con
# el que ella tecleó: P-01 escribió tres palabras y el bot usaba dos.
# Esta regla tapa el nombre que siga a un tratamiento de cortesía, venga
# de donde venga.
_CORTESIA = re.compile(
    r"\b(doña|dona|don|señora|senora|señor|senor|sra|sr)\.?\s+"
    r"[A-ZÁÉÍÓÚÑ][\wáéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][\wáéíóúñ]+)?",
    re.U,
)


def _datos_propios(propios: list[dict]) -> set[str]:
    """Lo que la participante contestó a las tres preguntas del onboarding."""
    valores: set[str] = set()
    for i, m in enumerate(propios):
        if m["rol"] != "asistente":
            continue
        for marcas in _TRAS_PREGUNTA.values():
            if not (m["_marcas"] & marcas):
                continue
            siguiente = next(
                (s for s in propios[i + 1:] if s["rol"] == "usuaria"), None
            )
            if siguiente is None:
                continue
            valor = siguiente["contenido"].strip()
            if len(valor) >= 4 and valor.lower() not in _NO_TAPAR:
                valores.add(valor)
    return valores


def _plegado(texto: str) -> str:
    """Minúsculas y sin tildes, **conservando una letra por letra**.

    Hace falta para comparar sin tildes sin perder la correspondencia de
    posiciones con el original, que es lo que permite tapar el fragmento
    exacto. Un `normalize("NFD")` a secas cambia la longitud.
    """
    salida = []
    for c in texto:
        descompuesto = unicodedata.normalize("NFD", c)
        salida.append(descompuesto[0] if descompuesto else c)
    return "".join(salida).lower()


def _variantes(valores: set[str]) -> set[str]:
    """El valor entero y sus subcadenas de dos palabras o más.

    Un nombre de tres palabras se repite muchas veces con solo dos, así que
    buscar la cadena completa no basta. Las palabras sueltas se dejan
    aparte a propósito: tapar una sola palabra borraría especies como
    «rosa» o «flor» y estropearía la clasificación.
    """
    salida: set[str] = set()
    for valor in valores:
        salida.add(valor)
        palabras = valor.split()
        for n in range(len(palabras), 1, -1):
            for i in range(len(palabras) - n + 1):
                salida.add(" ".join(palabras[i:i + n]))
    return {v for v in salida if len(v) >= 4}


def _tapar(texto: str, propios: set[str]) -> str:
    """Sustituye por `[DATO_PERSONAL]` lo que identifique a la participante.

    La comparación **ignora tildes y mayúsculas**: ella escribió su nombre
    sin tilde y el modelo lo repitió con ella, así que una comparación
    literal lo dejaba en claro. Comprobado con un nombre real que se coló
    en la primera exportación.
    """
    salida = texto
    for valor in sorted(_variantes(propios), key=len, reverse=True):
        patron = re.compile(re.escape(_plegado(valor)))
        while True:
            m = patron.search(_plegado(salida))
            if m is None:
                break
            salida = salida[:m.start()] + "[DATO_PERSONAL]" + salida[m.end():]
    salida = _CORTESIA.sub(
        lambda m: f"{m.group(1)} [DATO_PERSONAL]", salida
    )
    salida = _DIRECCION.sub("[DATO_PERSONAL]", salida)
    salida = _DIGITOS.sub("[DATO_PERSONAL]", salida)
    return salida


# ---------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------


async def _leer(corte: datetime) -> dict[str, Any]:
    pool = obtener_pool()

    usuarias = await pool.fetch(
        """
        select u.id,
               left(u.identidad_hash, 8)              as hash8,
               u.identidad_hash,
               u.consentimiento_en,
               (u.nombre_usuario_cifrado is not null) as dio_su_nombre,
               (h.id is not null)                     as tiene_huerta,
               h.nombre_huerta,
               b.nombre                               as barrio,
               coalesce(c.n, 0)                       as cultivos
          from usuario u
          left join huerta h on h.usuario_id = u.id
          left join barrio b on b.id = h.barrio_id
          left join (select h.usuario_id, count(c.id) as n
                       from huerta h
                       join cultivo c on c.huerta_id = h.id
                      group by h.usuario_id) c on c.usuario_id = u.id
         order by u.consentimiento_en
        """
    )

    mensajes = await pool.fetch(
        """
        select usuario_id, rol, tipo, contenido, creado_en
          from mensaje
         where creado_en <= $1
         order by usuario_id, creado_en
        """,
        corte,
    )

    # El instante de cada cultivo, para saber si se guardó DENTRO del
    # intento que se está midiendo y no en otro anterior.
    cultivos = await pool.fetch(
        """
        select h.usuario_id, c.creado_en
          from cultivo c join huerta h on h.id = c.huerta_id
         where c.creado_en <= $1
         order by h.usuario_id, c.creado_en
        """,
        corte,
    )

    return {"usuarias": usuarias, "mensajes": mensajes, "cultivos": cultivos}


# ---------------------------------------------------------------------
# Segmentación de los intentos de registro (T2)
# ---------------------------------------------------------------------


def _contar(tramo: list[dict], conjunto: set[str]) -> int:
    """Cuántas marcas del conjunto aparecen en las respuestas del tramo."""
    return sum(len(m["_marcas"] & conjunto) for m in tramo
               if m["rol"] == "asistente")


def _pausa_maxima(tramo: list[dict]) -> float:
    if len(tramo) < 2:
        return 0.0
    return max(
        (tramo[i + 1]["creado_en"] - tramo[i]["creado_en"]).total_seconds()
        for i in range(len(tramo) - 1)
    )


def _repeticiones(tramo: list[dict], ventana_min: int) -> int:
    """Mensajes de la participante repetidos literalmente en la ventana.

    Los reintentos que manda Meta no llegan aquí: la idempotencia por huella
    del `wamid` los descarta antes de escribir en `mensaje` (ADR-0005). Así
    que esto mide que **ella** repitió, no que el canal reintentó.
    """
    previos: list[tuple[str, datetime]] = []
    repetidos = 0
    for m in tramo:
        if m["rol"] != "usuaria":
            continue
        texto = m["contenido"].strip().lower()
        if not texto:
            continue
        limite = m["creado_en"] - timedelta(minutes=ventana_min)
        if any(t == texto and c >= limite for t, c in previos):
            repetidos += 1
        previos.append((texto, m["creado_en"]))
    return repetidos


def episodios_t2(propios: list[dict], umbral_pausa_min: int) -> list[dict]:
    """Parte la conversación en intentos de registro.

    **Abre** el mensaje de la participante que el sistema llevó al CU3, es
    decir, aquel cuya respuesta trae una de las tres salidas de
    `registrar_huerta`: la propuesta, «no le entendí qué sembró» o «necesito
    unos datos de su huerta».

    **Cierra** en el primero de estos cuatro:

    1. confirmación de guardado;
    2. descarte, o confirmación sin borrador que confirmar;
    3. pausa mayor que el umbral entre dos mensajes consecutivos;
    4. cambio de tarea: una respuesta de otro caso de uso.

    Un reintento tras un «no le entendí qué sembró» **pertenece al mismo
    intento** mientras no ocurra ninguno de los cuatro cierres, y sus
    errores se cuentan en él.
    """
    episodios: list[dict] = []
    i = 0
    while i < len(propios):
        m = propios[i]
        if m["rol"] != "usuaria":
            i += 1
            continue

        respuesta = next((s for s in propios[i + 1:] if s["rol"] == "asistente"), None)
        if respuesta is None or not (respuesta["_marcas"] & _ABRE_T2):
            i += 1
            continue

        tramo = [m]
        cierre = None
        motivo = "sin cerrar"
        j = i + 1
        while j < len(propios):
            actual = propios[j]
            pausa = (actual["creado_en"] - tramo[-1]["creado_en"]).total_seconds()
            if pausa > umbral_pausa_min * 60:
                motivo = "pausa"
                break
            if actual["rol"] == "asistente":
                if actual["_marcas"] & _OTRAS_TAREAS:
                    motivo = "cambio de tarea"
                    break
                tramo.append(actual)
                if "T2 guardado" in actual["_marcas"]:
                    cierre = actual["creado_en"]
                    motivo = "guardado"
                    j += 1
                    break
                if actual["_marcas"] & {"T2 descartado", "T2 sin borrador"}:
                    motivo = "descartado"
                    j += 1
                    break
            else:
                tramo.append(actual)
            j += 1

        episodios.append({
            "tramo": tramo,
            "inicio": tramo[0]["creado_en"],
            "cierre": cierre,
            "motivo": motivo,
        })
        i = max(j, i + 1)

    return episodios


# ---------------------------------------------------------------------
# Salidas
# ---------------------------------------------------------------------


_BLOQUEADAS: list[str] = []


def _escribir_csv(ruta: Path, columnas: list[str], filas: list[dict]) -> None:
    """Escribe la hoja, y avisa en vez de caerse si está abierta en Excel.

    Pasa a menudo: el autor deja el CSV abierto mientras lo llena y Windows
    bloquea el archivo. Perder toda la ejecución por eso sería absurdo,
    porque lo que ya hay en disco sigue siendo válido.
    """
    try:
        with ruta.open("w", encoding="utf-8-sig", newline="") as f:
            escritor = csv.DictWriter(f, fieldnames=columnas,
                                      extrasaction="ignore")
            escritor.writeheader()
            escritor.writerows(filas)
    except PermissionError:
        _BLOQUEADAS.append(ruta.name)


def _leer_csv(ruta: Path, llave: str) -> dict[str, dict]:
    """Lo que ya esté lleno en una hoja, indexado por su llave.

    Se relee antes de reescribir para no pisar lo que el autor haya puesto:
    las tres hojas se regeneran en cada ejecución.
    """
    if not ruta.exists():
        return {}
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        return {fila[llave]: fila for fila in csv.DictReader(f)}


def _mediana(valores: list[float]) -> float | None:
    return round(statistics.median(valores), 1) if valores else None


def _percentil(valores: list[float], p: float) -> float | None:
    if not valores:
        return None
    o = sorted(valores)
    k = (len(o) - 1) * p
    b = int(k)
    a = min(b + 1, len(o) - 1)
    return round(o[b] + (o[a] - o[b]) * (k - b), 1)


async def main() -> None:
    parametros = json.loads((SALIDAS / "parametros.json").read_text(encoding="utf-8"))
    corte = datetime.fromisoformat(parametros["FECHA_EXTRACCION"])
    excluidos = {h.lower() for h in parametros["HASHES_EXCLUIDOS"]}
    umbral_pausa = parametros["UMBRAL_PAUSA_MIN"]
    repeticion = parametros["REPETICION_MIN"]
    esperado = parametros.get("N_ESPERADO")
    validada = parametros.get("CLASIFICACION_VALIDADA", False)

    await abrir_pool()
    try:
        datos = await _leer(corte)
    finally:
        await cerrar_pool()

    por_usuaria: dict[Any, list[dict]] = defaultdict(list)
    for fila in datos["mensajes"]:
        m = dict(fila)
        m["_marcas"] = _marcas(m["contenido"]) if m["rol"] == "asistente" else set()
        por_usuaria[m["usuario_id"]].append(m)

    cultivos_de: dict[Any, list[datetime]] = defaultdict(list)
    for fila in datos["cultivos"]:
        cultivos_de[fila["usuario_id"]].append(fila["creado_en"])

    # Los seudónimos se asignan sobre TODAS las filas y por orden de
    # consentimiento, antes de excluir a nadie: así siguen coincidiendo con
    # los del registro de aceptación. La excluida deja un hueco.
    todas = [dict(u) for u in datos["usuarias"]]
    seudonimo = {u["id"]: f"P-{n:02d}" for n, u in enumerate(todas, start=1)}
    huecos = [
        seudonimo[u["id"]] for u in todas
        if u["identidad_hash"].lower() in excluidos
        or u["hash8"].lower() in excluidos
    ]
    usuarias = [
        u for u in todas
        if u["identidad_hash"].lower() not in excluidos
        and u["hash8"].lower() not in excluidos
    ]

    print(f"Participantes en la base: {len(todas)}")
    print(f"Excluidas: {len(huecos)} {huecos or ''}")
    print(f"Elegibles: {len(usuarias)}")
    if esperado is not None and len(usuarias) != esperado:
        print(
            f"\n  AVISO: quedan {len(usuarias)} elegibles y se esperaban "
            f"{esperado}. No se calcula nada más hasta resolverlo."
        )
        if not excluidos:
            print("  Falta `HASHES_EXCLUIDOS` en parametros.json: lo entrega el autor.")
    print(f"Instantánea: {corte.astimezone(BOGOTA):%Y-%m-%d %H:%M} (Bogotá)\n")

    previa = _leer_csv(HOJA, "id_mensaje")
    propuestas = (
        json.loads(PROPUESTAS.read_text(encoding="utf-8"))["categorias"]
        if PROPUESTAS.exists() else {}
    )
    filas_hoja: list[dict] = []
    filas_tiempos: list[dict] = []
    resumen: list[dict] = []

    for usuaria in usuarias:
        uid = usuaria["id"]
        pseudo = seudonimo[uid]
        propios = por_usuaria.get(uid, [])
        propios_ordenados = sorted(propios, key=lambda m: m["creado_en"])
        tapar = _datos_propios(propios_ordenados)
        # El barrio y el nombre de la huerta, tal como los guarda la base:
        # el backend los repite normalizados en el resumen del CU3, así que
        # taparlos solo con lo que ella tecleó dejaba «Barrio: VILLA DE
        # SUAITA» en claro. La regla 4 del encargo prohíbe que un nombre de
        # barrio o de huerta aparezca en ninguna salida.
        for campo in ("nombre_huerta", "barrio"):
            valor = (usuaria.get(campo) or "").strip()
            if len(valor) >= 4:
                tapar.add(valor)

        cierre_t1 = next(
            (m["creado_en"] for m in propios_ordenados
             if m["rol"] == "asistente" and "T1 guardado" in m["_marcas"]),
            None,
        )

        # --- Mensajes libres posteriores al onboarding ---
        libres: list[dict] = []
        if cierre_t1 is not None:
            n = 0
            for i, m in enumerate(propios_ordenados):
                if (m["rol"] != "usuaria" or m["tipo"] == "interactive"
                        or m["creado_en"] <= cierre_t1):
                    continue
                n += 1
                respuesta = next(
                    (s for s in propios_ordenados[i + 1:] if s["rol"] == "asistente"),
                    None,
                )
                idm = f"{pseudo}-{n:03d}"
                fila = {
                    "id_mensaje": idm,
                    "seudonimo": pseudo,
                    "timestamp": m["creado_en"].astimezone(BOGOTA).isoformat(),
                    "tipo_entrada": m["tipo"],
                    "texto_usuario": _tapar(m["contenido"], tapar),
                    "respuesta_bot": _tapar(respuesta["contenido"], tapar)
                    if respuesta else "",
                    "camino": _camino(respuesta),
                }
                anterior = previa.get(idm, {})
                propuesta = propuestas.get(idm, "")
                fila["categoria_propuesta"] = propuesta
                for col in COLUMNAS_HUMANAS:
                    # La propuesta solo siembra la casilla la primera vez:
                    # si el autor ya escribió algo, manda lo suyo.
                    defecto = propuesta if col == "categoria_humana" else ""
                    fila[col] = anterior.get(col) or defecto
                filas_hoja.append(fila)
                libres.append({"mensaje": m, "respuesta": respuesta, "id": idm})

        episodios = episodios_t2(propios_ordenados, umbral_pausa)

        # T1 conserva la unidad «participante». Su tramo va del
        # consentimiento al «ya quedó guardada su huerta»; quien no lo
        # completó se quedó en el onboarding, porque el despachador no deja
        # llegar nada al agente hasta que termine.
        tramo_t1 = (
            [m for m in propios_ordenados if m["creado_en"] <= cierre_t1]
            if cierre_t1 is not None else propios_ordenados
        )
        resumen.append({
            "seudonimo": pseudo,
            "libres": libres,
            "episodios_t2": len(episodios),
            "completo_t1": bool(usuaria["tiene_huerta"]),
            "cultivos": usuaria["cultivos"],
            "cultivos_en": cultivos_de.get(uid, []),
            "episodios": episodios,
            "errores_t1": (
                _contar(tramo_t1, _ERRORES) + _contar(tramo_t1, _CORRECCIONES)
                + _repeticiones(tramo_t1, repeticion)
            ),
            "fallos_t1": _contar(tramo_t1, _FALLOS),
            "segundos_t1": round(
                (cierre_t1 - usuaria["consentimiento_en"]).total_seconds(), 1
            ) if cierre_t1 is not None else None,
            "interrumpido_t1": _pausa_maxima(tramo_t1) > umbral_pausa * 60,
            "mensajes_t1": sum(1 for m in tramo_t1 if m["rol"] == "usuaria"),
            "dias": len({m["creado_en"].astimezone(BOGOTA).date()
                         for m in propios_ordenados}),
            "consintio": usuaria["consentimiento_en"].astimezone(BOGOTA)
            .strftime("%d/%m/%Y %H:%M"),
            "mensajes_suyos": sum(1 for m in propios_ordenados
                                  if m["rol"] == "usuaria"),
            # Pasos del embudo que solo se ven en las marcas del texto: la
            # fila de `huerta` se crea entera al final y
            # `onboarding_pendiente` se borra al completar, así que de
            # quien abandonó no queda estado.
            "marcas_suyas": {m for x in propios_ordenados for m in x["_marcas"]},
            "dio_su_nombre": bool(usuaria["dio_su_nombre"]),
        })

        # PTb-1-G: cada mensaje suyo con el siguiente del asistente.
        for i, m in enumerate(propios_ordenados):
            if m["rol"] != "usuaria":
                continue
            respuesta = next(
                (s for s in propios_ordenados[i + 1:] if s["rol"] == "asistente"),
                None,
            )
            if respuesta is None:
                continue
            filas_tiempos.append({
                "seudonimo": pseudo,
                "timestamp_entrante": m["creado_en"].astimezone(BOGOTA).isoformat(),
                "tipo_entrante": m["tipo"],
                "segundos": round(
                    (respuesta["creado_en"] - m["creado_en"]).total_seconds(), 1
                ),
                "marcas_de_la_respuesta": "|".join(sorted(respuesta["_marcas"])),
            })

    SALIDAS.mkdir(parents=True, exist_ok=True)
    _escribir_csv(
        HOJA,
        ["id_mensaje", "seudonimo", "timestamp", "tipo_entrada", "texto_usuario",
         "respuesta_bot", "camino", "categoria_propuesta"] + COLUMNAS_HUMANAS,
        filas_hoja,
    )

    # --- Estado de la clasificación ---
    sin_clasificar = sum(1 for f in filas_hoja if not f["categoria_humana"].strip())
    print(f"Mensajes libres posteriores al onboarding: {len(filas_hoja)}")
    print(f"  sin clasificar: {sin_clasificar} de {len(filas_hoja)}")
    caminos: dict[str, int] = defaultdict(int)
    for f in filas_hoja:
        caminos[f["camino"]] += 1
    print("  por camino que eligió el sistema:")
    for c, n in sorted(caminos.items(), key=lambda kv: -kv[1]):
        print(f"    {c:24} {n:3}")

    print(f"\nIntentos de registro (T2) segmentados: "
          f"{sum(r['episodios_t2'] for r in resumen)}")
    motivos: dict[str, int] = defaultdict(int)
    for r in resumen:
        for e in r["episodios"]:
            motivos[e["motivo"]] += 1
    for m, n in sorted(motivos.items(), key=lambda kv: -kv[1]):
        print(f"  cierre por {m:18} {n:3}")

    cruce: dict[tuple[str, str], int] = defaultdict(int)
    for f in filas_hoja:
        cruce[(f["categoria_humana"] or "sin clasificar", f["camino"])] += 1
    categorias = sorted({c for c, _ in cruce})
    caminos_orden = sorted({c for _, c in cruce})
    print()
    print("¿Qué quería la participante (filas) contra a dónde fue (columnas)?")
    print("| categoría | " + " | ".join(caminos_orden) + " | total |")
    print("|---" * (len(caminos_orden) + 2) + "|")
    for cat in categorias:
        fila_n = [cruce.get((cat, cam), 0) for cam in caminos_orden]
        print(f"| {cat} | " + " | ".join(str(n) for n in fila_n)
              + f" | {sum(fila_n)} |")

    cambiadas = sum(
        1 for f in filas_hoja
        if f["categoria_propuesta"] and f["categoria_humana"]
        and f["categoria_propuesta"] != f["categoria_humana"]
    )
    print()
    print(f"Filas donde el autor corrigió la propuesta: {cambiadas} de "
          f"{len(filas_hoja)}")

    if not validada:
        print()
        print("La clasificación está PROPUESTA POR LA IA y SIN VALIDAR.")
        print("No es la clasificación declarada mientras `CLASIFICACION_VALIDADA`")
        print("sea false en parametros.json: revise las 50 filas y corrija")
        print("`categoria_humana` donde no esté de acuerdo.")

    if sin_clasificar:
        print(
            f"\nT2 y T3 quedan PENDIENTES DE CLASIFICACIÓN: no se calcula "
            f"Ef-1-G mientras\nhaya {sin_clasificar} mensajes sin marcar en "
            f"{HOJA.relative_to(RAIZ)}."
        )

    # =================================================================
    # Las medidas, con las unidades nuevas
    # =================================================================
    #
    # T1 se mide por participante; T2 por intento de registro y T3 por
    # consulta. Medir las dos últimas por participante las volvía
    # circulares: el intento se detectaba con la misma evidencia que la
    # completitud y la proporción no podía bajar del 100 %.

    clasificado = {f["id_mensaje"]: f for f in filas_hoja}
    rubrica = _leer_csv(RUBRICA, "id_consulta")
    # Lo que el autor haya escrito en el CSV manda; el JSON solo siembra lo
    # que esté vacío, para no pisar una corrección suya.
    if RESPUESTAS.exists():
        dadas = json.loads(RESPUESTAS.read_text(encoding="utf-8"))["respuestas"]
        for idc, valores in dadas.items():
            fila = rubrica.setdefault(idc, {"id_consulta": idc})
            for campo, valor in valores.items():
                if not fila.get(campo, "").strip():
                    fila[campo] = valor
    hay_rubrica = any(
        v.get("lo_que_dice_es_cierto", "").strip() for v in rubrica.values()
    )
    ayuda = {
        s: v.get("recibio_ayuda", "").strip().lower()
        for s, v in _leer_csv(ASISTENCIA, "seudonimo").items()
    }
    hay_asistencia = any(ayuda.values())

    intentos: list[dict] = []
    for r in resumen:
        pseudo = r["seudonimo"]

        intentos.append({
            "tarea": "T1", "unidad": "participante", "seudonimo": pseudo,
            "id": pseudo, "completo": r["completo_t1"],
            "errores": r["errores_t1"], "fallos": r["fallos_t1"],
            "segundos": r["segundos_t1"], "interrumpido": r["interrumpido_t1"],
            "mensajes": r["mensajes_t1"], "minimo": _MINIMOS["T1"],
            "camino": "", "sin_respaldo": 0,
            "asistencia": ayuda.get(pseudo, ""), "grupo": "",
        })

        for n, e in enumerate(r["episodios"], start=1):
            fin = e["cierre"] or e["tramo"][-1]["creado_en"]
            guardados = [c for c in r["cultivos_en"] if e["inicio"] <= c <= fin]
            intentos.append({
                "tarea": "T2", "unidad": "intento", "seudonimo": pseudo,
                "id": f"{pseudo}-R{n}",
                "completo": e["motivo"] == "guardado" and bool(guardados),
                "errores": (_contar(e["tramo"], _ERRORES)
                            + _contar(e["tramo"], _CORRECCIONES)
                            + _repeticiones(e["tramo"], repeticion)),
                "fallos": _contar(e["tramo"], _FALLOS),
                "segundos": round((fin - e["inicio"]).total_seconds(), 1),
                "interrumpido": _pausa_maxima(e["tramo"]) > umbral_pausa * 60,
                "mensajes": sum(1 for m in e["tramo"] if m["rol"] == "usuaria"),
                "minimo": _MINIMOS["T2"], "camino": "CU3",
                "cultivos_guardados": len(guardados), "motivo": e["motivo"],
                "sin_respaldo": 0, "asistencia": ayuda.get(pseudo, ""),
                "grupo": "",
            })

        for f in r["libres"]:
            ficha = clasificado.get(f["id"], {})
            if ficha.get("categoria_humana") != CONSULTA:
                continue
            notas = rubrica.get(f["id"], {})
            calificada = notas.get("lo_que_dice_es_cierto", "").strip() != ""
            # Completada = le contestó lo que preguntó Y lo que dice es
            # cierto. Las dos, no una.
            aprobada = (
                notas.get("contesto_lo_que_pregunto", "").strip().lower() in _SI
                and notas.get("lo_que_dice_es_cierto", "").strip().lower() in _SI
            )
            respuesta = f["respuesta"]
            intentos.append({
                "tarea": "T3", "unidad": "consulta", "seudonimo": pseudo,
                "id": f["id"],
                # Sin rúbrica no se decide: la completitud de una consulta
                # es que la respuesta le sirviera, y eso lo dice una persona.
                "completo": aprobada if calificada else None,
                "errores": 0,
                "fallos": 1 if respuesta and respuesta["_marcas"] & _FALLOS else 0,
                "segundos": round(
                    (respuesta["creado_en"] - f["mensaje"]["creado_en"]).total_seconds(), 1
                ) if respuesta else None,
                "interrumpido": False, "mensajes": 1, "minimo": _MINIMOS["T3"],
                "camino": ficha.get("camino", ""),
                "sin_respaldo": 1 if respuesta
                and "T3 sin respaldo" in respuesta["_marcas"] else 0,
                "asistencia": ayuda.get(pseudo, ""), "grupo": "",
            })

    _escribir_csv(
        SALIDAS / "intentos_tareas.csv",
        ["tarea", "unidad", "seudonimo", "id", "completo", "errores", "fallos",
         "segundos", "interrumpido", "mensajes", "minimo", "camino",
         "cultivos_guardados", "motivo", "sin_respaldo", "asistencia", "grupo"],
        intentos,
    )

    # --- Las dos hojas que llena una persona ---------------------------
    #
    # Van aparte de la hoja grande a propósito: lo que falta son dos
    # preguntas concretas, y pedirlas dentro de una tabla de quince
    # columnas y cincuenta filas las volvía difíciles de ver.

    filas_rubrica = []
    for x in intentos:
        if x["tarea"] != "T3":
            continue
        ficha = clasificado.get(x["id"], {})
        anterior = rubrica.get(x["id"], {})
        filas_rubrica.append({
            "id_consulta": x["id"],
            "pregunta": ficha.get("texto_usuario", ""),
            "respuesta_del_bot": ficha.get("respuesta_bot", ""),
            "contesto_lo_que_pregunto": anterior.get("contesto_lo_que_pregunto", ""),
            "lo_que_dice_es_cierto": anterior.get("lo_que_dice_es_cierto", ""),
            "observacion": anterior.get("observacion", ""),
        })
    _escribir_csv(
        RUBRICA,
        ["id_consulta", "pregunta", "respuesta_del_bot",
         "contesto_lo_que_pregunto", "lo_que_dice_es_cierto", "observacion"],
        filas_rubrica,
    )

    previa_asist = _leer_csv(ASISTENCIA, "seudonimo")
    _escribir_csv(
        ASISTENCIA,
        ["seudonimo", "consintio", "mensajes_suyos", "recibio_ayuda", "grupo"],
        [
            {
                "seudonimo": r["seudonimo"],
                "consintio": r["consintio"],
                "mensajes_suyos": r["mensajes_suyos"],
                "recibio_ayuda": previa_asist.get(r["seudonimo"], {}).get(
                    "recibio_ayuda", ""),
                "grupo": previa_asist.get(r["seudonimo"], {}).get("grupo", ""),
            }
            for r in resumen
        ],
    )

    # El estado del dato de asistencia: ninguna, parte, o todas.
    con_dato = sum(1 for r in resumen if ayuda.get(r["seudonimo"], ""))
    estado = ("sin verificar asistencia" if con_dato == 0
              else "asistencia verificada" if con_dato == len(resumen)
              else f"asistencia parcial ({con_dato}/{len(resumen)})")
    print()
    print(f"Ef-1-G por tarea — completitud {estado}")
    print("| Tarea | Unidad | B | A | Proporción | Estado |")
    print("|---|---|---|---|---|---|")
    suma_a = suma_b = 0
    t3_pendientes: list[dict] = []
    for tarea, unidad in (("T1", "participantes"), ("T2", "intentos"),
                          ("T3", "consultas")):
        f = [x for x in intentos if x["tarea"] == tarea]
        b = len(f)
        suma_b += b
        if tarea == "T3" and not hay_rubrica:
            t3_pendientes = f
            print(f"| T3 | consultas | {b} | — | — | pendiente de rúbrica |")
            continue
        # «Sin asistencia» es parte de la definición: quien recibió ayuda
        # no cuenta en A, aunque completara la tarea.
        a = sum(1 for x in f
                if x["completo"] and x["asistencia"] not in _SI)
        suma_a += a
        print(f"| {tarea} | {unidad} | {b} | {a} | {a}/{b} | {estado} |")
    if hay_rubrica:
        print(f"| Global | mixta | {suma_b} | {suma_a} | "
              f"{suma_a}/{suma_b} = {suma_a / suma_b:.2f} | sin asistencia |")
    else:
        # Dar un global ahora sería contar como fallidas las consultas que
        # solo están *sin calificar*. Se da la cota: el resultado depende
        # entero de la rúbrica.
        sin_t3 = suma_b - len(t3_pendientes)
        peor = suma_a / suma_b
        mejor = (suma_a + len(t3_pendientes)) / suma_b
        print(f"| Global | mixta | {suma_b} | {suma_a} + T3 | "
              f"entre {peor:.2f} y {mejor:.2f} | SIN CONTRASTAR |")
        print(f"  Sin T3, lo medible va {suma_a}/{sin_t3} = "
              f"{suma_a / sin_t3:.2f}.")
        print(f"  Las {len(t3_pendientes)} consultas no están fallidas: están sin")
        print("  calificar. Si la rúbrica aprueba todas, el global sube a "
              f"{mejor:.2f}; si no")
        print(f"  aprueba ninguna, baja a {peor:.2f}. El contraste de la hipótesis")
        print("  depende entero de esa rúbrica y del dato de asistencia.")

    print()
    print("Ef-3-G, Ef-4-G y Ef-5-G")
    print("| Tarea | Unidad | Intentos | Errores | Ef-4-G | Ef-5-G | Fallos |")
    print("|---|---|---|---|---|---|---|")
    for tarea, unidad in (("T1", "participante"), ("T2", "intento"),
                          ("T3", "consulta")):
        f = [x for x in intentos if x["tarea"] == tarea]
        if not f:
            continue
        con_error = [x for x in f if x["errores"] > 0]
        quienes = {x["seudonimo"] for x in f}
        con_error_q = {x["seudonimo"] for x in con_error}
        print(f"| {tarea} | {unidad} | {len(f)} | "
              f"{sum(x['errores'] for x in f)} | {len(con_error)}/{len(f)} | "
              f"{len(con_error_q)}/{len(quienes)} | "
              f"{sum(x['fallos'] for x in f)} |")
    print("  En T1 la unidad ES la participante, así que Ef-4-G y Ef-5-G")
    print("  coinciden por construcción. Solo se separan en T2 y T3.")

    print()
    print("Ey-1-G, tiempo de la tarea (s)")
    print("| Tarea | Unidad | n | Mediana | Mín | Máx | Sin interrumpidos |")
    print("|---|---|---|---|---|---|---|")
    for tarea, unidad in (("T1", "participante"), ("T2", "intento"),
                          ("T3", "consulta")):
        v = [x["segundos"] for x in intentos
             if x["tarea"] == tarea and x["segundos"] is not None]
        ni = [x["segundos"] for x in intentos
              if x["tarea"] == tarea and x["segundos"] is not None
              and not x["interrumpido"]]
        if v:
            print(f"| {tarea} | {unidad} | {len(v)} | {_mediana(v)} | {min(v)} "
                  f"| {max(v)} | n={len(ni)}, mediana {_mediana(ni)} |")

    t3 = [x for x in intentos if x["tarea"] == "T3"]
    print()
    print(f"Las {len(t3)} consultas agroecológicas")
    por_camino: dict[str, int] = defaultdict(int)
    for x in t3:
        por_camino[x["camino"]] += 1
    for c, n in sorted(por_camino.items(), key=lambda kv: -kv[1]):
        print(f"  por el camino {c:14} {n}/{len(t3)}")
    print(f"  sin respaldo oficial: {sum(x['sin_respaldo'] for x in t3)}/{len(t3)}")
    print(f"  participantes que consultaron: "
          f"{len({x['seudonimo'] for x in t3})}/{len(usuarias)}")

    completas: dict[str, set] = defaultdict(set)
    for x in intentos:
        if x["completo"]:
            completas[x["seudonimo"]].add(x["tarea"])
    if not hay_rubrica:
        # Sin rúbrica, T3 se da por «consultó y recibió respuesta», y la
        # lista queda marcada como provisional.
        for x in t3:
            if x["segundos"] is not None:
                completas[x["seudonimo"]].add("T3")
    candidatas = sorted(p for p, t in completas.items() if {"T1", "T2", "T3"} <= t)
    _escribir_csv(SALIDAS / "candidatas_sus.csv", ["seudonimo"],
                  [{"seudonimo": p} for p in candidatas])
    print()
    print(f"Candidatas al SUS, con las tres tareas completadas: "
          f"{len(candidatas)} de {len(usuarias)}"
          + ("  (T3 provisional, sin rúbrica)" if not hay_rubrica else ""))

    varios = [r["seudonimo"] for r in resumen if r["dias"] > 1]
    print(f"Con actividad en más de un día: {len(varios)} de {len(usuarias)} "
          f"{varios}")

    # --- PTb-1-G ------------------------------------------------------
    _escribir_csv(
        SALIDAS / "tiempos_respuesta_sistema.csv",
        ["seudonimo", "timestamp_entrante", "tipo_entrante", "segundos",
         "marcas_de_la_respuesta"],
        filas_tiempos,
    )
    seg = [f["segundos"] for f in filas_tiempos]
    print()
    print(f"PTb-1-G, tiempo de respuesta ({len(seg)} pares): "
          f"media {statistics.mean(seg):.1f} s | mediana {_mediana(seg)} s | "
          f"p90 {_percentil(seg, 0.9)} s | máx {max(seg)} s")
    # El agregado esconde dos poblaciones: el onboarding no llama al modelo
    # y el CU2 recupera y redacta. Juntas dan una mediana que no describe
    # ninguna de las dos.
    grupos: dict[str, list[float]] = defaultdict(list)
    for f in filas_tiempos:
        marcas = set(f["marcas_de_la_respuesta"].split("|")) - {""}
        if marcas & _MARCAS_T3:
            g = "CU2 (recupera y redacta)"
        elif any(m.startswith("T1 ") for m in marcas):
            g = "onboarding (sin modelo)"
        elif any(m.startswith("T2 ") for m in marcas):
            g = "CU3 registro (extrae)"
        elif not marcas:
            g = "texto libre del modelo"
        else:
            g = "otros textos del backend"
        grupos[g].append(f["segundos"])
    for g, v in sorted(grupos.items(), key=lambda kv: -len(kv[1])):
        print(f"  {g:26} n={len(v):3} mediana={_mediana(v):6} "
              f"p90={_percentil(v, 0.9):6} máx={max(v):6}")

    # --- Ey-5-S -------------------------------------------------------
    print()
    print("Ey-5-S, razón de mensajes (solo intentos completados)")
    print("| Tarea | Mínimo | n | Mediana | Máx |")
    print("|---|---|---|---|---|")
    for tarea in ("T1", "T2", "T3"):
        razones = [x["mensajes"] / x["minimo"] for x in intentos
                   if x["tarea"] == tarea and x["completo"]]
        if razones:
            print(f"| {tarea} | {_MINIMOS[tarea]} | {len(razones)} | "
                  f"{_mediana(razones)} | {max(razones):.2f} |")
    exacto = [x["seudonimo"] for x in intentos
              if x["tarea"] == "T1" and x["completo"]
              and x["mensajes"] == x["minimo"]]
    print(f"  T1 en el mínimo exacto: {len(exacto)} de "
          f"{sum(1 for x in intentos if x['tarea'] == 'T1' and x['completo'])}")

    # --- Embudo del onboarding ----------------------------------------
    pasos = [
        ("1 recibió la bienvenida", None),
        ("2 aceptó la autorización", lambda r: True),
        ("3 dio su nombre", lambda r: r["dio_su_nombre"]),
        ("4 llegó al barrio",
         lambda r: bool({"T1 lista de barrios", "T1 eco barrio"} & r["marcas_suyas"])),
        ("5 llegó al nombre de la huerta",
         lambda r: "T1 pregunta huerta" in r["marcas_suyas"]),
        ("6 vio el resumen", lambda r: "T1 resumen" in r["marcas_suyas"]),
        ("7 onboarding completo", lambda r: r["completo_t1"]),
    ]
    filas_embudo = []
    print()
    print("Embudo del onboarding")
    for nombre, prueba in pasos:
        if prueba is None:
            filas_embudo.append({
                "paso": nombre, "participantes": "", "de": len(resumen),
                "porcentaje": "",
                "nota": "No medible: se envía antes de la compuerta y no se "
                        "recuerda (ADR-0012)",
            })
            print(f"  {nombre}: no medible")
            continue
        n = sum(1 for r in resumen if prueba(r))
        filas_embudo.append({
            "paso": nombre, "participantes": n, "de": len(resumen),
            "porcentaje": round(100 * n / len(resumen), 1), "nota": "",
        })
        print(f"  {nombre}: {n} de {len(resumen)}")
    _escribir_csv(
        SALIDAS / "embudo_onboarding.csv",
        ["paso", "participantes", "de", "porcentaje", "nota"],
        filas_embudo,
    )

    print(f"\nSalidas en {SALIDAS}")


if __name__ == "__main__":
    asyncio.run(main())
