"""Comprobación de humo tras un despliegue. Procedimiento PR-03.

    python -m scripts.humo_despliegue
    python -m scripts.humo_despliegue --url https://otro.up.railway.app
    python -m scripts.humo_despliegue --commit a1b2c3d --modelo gemini-3.6-flash

Es la **prueba de instalabilidad** del plan: no comprueba que el sistema
funcione, comprueba que **el que está corriendo es el que usted cree**.

Existe porque esa confusión ya costó una medición. El 08/09/2026 había
tres valores del modelo generativo y ninguno acertaba: los documentos
daban por corriendo `gemini-3.5-flash-lite`, `config.py` declaraba
`gemini-3.6-flash` y Railway corría `gemini-2.5-flash`. Con eso se midió
el enrutamiento del agente contra dos modelos que no eran producción, y
la medición no valía (riesgo P-12).

Comprueba tres cosas y ninguna más:

1. Que el servicio responde y **llega a Supabase**. `/health` devuelve 503
   si no llega, porque un servicio vivo que no alcanza la base no puede
   atender a nadie.
2. Que el **commit desplegado** es el que se acaba de subir.
3. Que el **modelo generativo** que corre es el que el repositorio declara
   por defecto en `app/config.py`.

No escribe nada, no manda ningún WhatsApp y no llama a Gemini. Se puede
correr tantas veces como haga falta.

Devuelve 0 si todo cuadra y 1 si algo no, para poder encadenarlo.
"""

import argparse
import subprocess
import sys

import httpx

# La URL del despliegue. No es un secreto —el repositorio es público y
# `/health` no expone ninguna variable sensible—, pero se puede cambiar
# por argumento para probar contra otro entorno.
_URL_POR_DEFECTO = "https://web-production-1390a.up.railway.app"

_TIEMPO_ESPERA = 20.0

# Longitud del commit corto, la misma que informa `/health`.
_LONGITUD_COMMIT = 7

_resultados: list[tuple[bool, str]] = []


def _comprobar(condicion: bool, titulo: str, detalle: str = "") -> None:
    marca = "OK  " if condicion else "FALLA"
    print(f"  [{marca}] {titulo}" + (f" — {detalle}" if detalle else ""))
    _resultados.append((condicion, titulo))


def _commit_local() -> str | None:
    """El commit del árbol actual, que es contra el que se compara.

    Devuelve None si no se puede saber —sin git, o fuera de un
    repositorio—, y entonces la comprobación del commit se omite en vez de
    fallar: no tener git no es un defecto del despliegue.
    """
    try:
        salida = subprocess.run(
            ["git", "rev-parse", f"--short={_LONGITUD_COMMIT}", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    return salida.stdout.strip() or None


def _modelo_declarado() -> str | None:
    """El modelo que el repositorio declara por defecto en `app/config.py`.

    Se lee del **campo de la clase**, no de la instancia: la instancia
    aplicaría el `.env` del equipo, y entonces se estaría comparando
    Railway contra la máquina del autor en lugar de contra el
    repositorio, que es el punto de la comprobación.

    Devuelve None si `app.config` no se puede importar —típicamente
    porque falta el `.env`—; en ese caso conviene pasar `--modelo`.
    """
    try:
        from app.config import Settings
    except Exception:
        return None

    return Settings.model_fields["GEMINI_GENERATIVE_MODEL"].default


def _consultar(url: str) -> tuple[int, dict]:
    respuesta = httpx.get(f"{url.rstrip('/')}/health", timeout=_TIEMPO_ESPERA)
    return respuesta.status_code, respuesta.json()


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--url", default=_URL_POR_DEFECTO)
    analizador.add_argument(
        "--commit",
        help="Commit esperado. Por defecto, el HEAD del árbol actual.",
    )
    analizador.add_argument(
        "--modelo",
        help="Modelo esperado. Por defecto, el que declara app/config.py.",
    )
    argumentos = analizador.parse_args()

    print(f"\nComprobación de humo contra {argumentos.url}\n")

    try:
        codigo, cuerpo = _consultar(argumentos.url)
    except Exception as fallo:
        print(f"  [FALLA] No se pudo consultar /health — {fallo}\n")
        return 1

    # 1. El servicio responde y llega a la base.
    _comprobar(codigo == 200, "El servicio responde 200", f"código={codigo}")
    _comprobar(
        cuerpo.get("status") == "ok",
        "El estado es 'ok'",
        f"base_de_datos={cuerpo.get('base_de_datos')}",
    )

    # 2. El commit desplegado es el esperado.
    version = cuerpo.get("version") or {}
    desplegado = version.get("commit")
    esperado = argumentos.commit or _commit_local()

    if esperado is None:
        print("  [ ?  ] No se pudo determinar el commit esperado; se omite")
    else:
        _comprobar(
            desplegado == esperado,
            "El commit desplegado es el esperado",
            f"desplegado={desplegado} esperado={esperado}",
        )

    # 3. El modelo generativo que corre es el que el repositorio declara.
    corriendo = cuerpo.get("modelo_generativo")
    declarado = argumentos.modelo or _modelo_declarado()

    if declarado is None:
        print(
            "  [ ?  ] No se pudo leer el modelo declarado "
            "(¿falta el .env?); pase --modelo"
        )
    else:
        _comprobar(
            corriendo == declarado,
            "El modelo generativo es el declarado",
            f"corriendo={corriendo} declarado={declarado}",
        )

    fallos = [titulo for correcto, titulo in _resultados if not correcto]

    print()
    if fallos:
        print(f"  {len(fallos)} comprobación(es) no pasaron:")
        for titulo in fallos:
            print(f"    - {titulo}")
        print(
            "\n  Mientras esto no cuadre, cualquier medición que se haga "
            "contra este despliegue es sospechosa.\n"
        )
        return 1

    print(f"  Las {len(_resultados)} comprobaciones pasaron.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
