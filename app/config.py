"""Configuración del backend.

Todas las credenciales se leen de variables de entorno. En local se toman
del archivo .env (que NO se versiona); en Railway, de las variables del
servicio. Ningún secreto se escribe en el código.
"""

import base64
import binascii

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Meta / WhatsApp Cloud API ---
    META_VERIFY_TOKEN: str
    META_APP_SECRET: str
    META_ACCESS_TOKEN: str
    META_PHONE_NUMBER_ID: str
    META_WABA_ID: str = ""
    META_GRAPH_VERSION: str = "v25.0"

    # --- Identidad y cifrado (Fase 3, §5.2) ---
    # Ambos son críticos e irrecuperables. Si el pepper cambia, las
    # usuarias registradas dejan de ser reconocidas; si se pierde la
    # clave, los nombres cifrados no se pueden descifrar.
    PHONE_HASH_PEPPER: str
    NAME_ENCRYPTION_KEY: str

    # --- Gemini ---
    GEMINI_API_KEY: str

    # Modelo generativo: agente, extracción de entidades y redacción del
    # RAG. Configurable a propósito, para poder cambiarlo en Railway sin
    # desplegar —los modelos de Gemini se retiran con calendario— y para
    # comparar modelos durante la calibración de la Fase 7.
    #
    # El valor de aquí es el que vale si Railway no define nada, así que el
    # repositorio siempre deja constancia de con qué se probó.
    #
    # NO existe una variable equivalente para el modelo de embeddings, y es
    # deliberado: ver app/core/gemini.py y el ADR-0007.
    GEMINI_GENERATIVE_MODEL: str = "gemini-3.6-flash"

    # --- Recuperación (RAG) ---
    # Configurables por el mismo criterio que GEMINI_GENERATIVE_MODEL y por
    # el contrario que el modelo de embeddings (ADR-0007): cambiarlos no
    # invalida nada de lo almacenado, y la Fase 4 los declara calibrables
    # durante las pruebas (CLAUDE.md §8). Poder ajustarlos en Railway sin
    # desplegar es justo lo que la Fase 7 necesita.
    #
    # El valor por defecto vive aquí, no solo en Railway, para que el
    # repositorio deje constancia de con qué se probó.
    #
    # Se queda en 0.68 (ADR-0010), pero **ya no significa lo mismo**, y eso
    # importa más que el número.
    #
    # Hasta ahora el umbral decidía responder o callar. Con el respaldo del
    # modelo activo (`CU2_RESPALDO_MODELO`, aquí debajo) decide otra cosa:
    # **citar o no citar**. Por encima se responde con la guía oficial y su
    # atribución; por debajo responde el modelo, sin fuente ninguna.
    #
    # Y para ese oficio 0.68 es mejor que bajarlo. Medido con
    # `scripts/calibrar_umbral_real.py` sobre las consultas de la primera
    # prueba con celular, y comprobado con el CU2 corriendo de verdad: al
    # bajar a 0.65 aparecía un modo de fallo que a 0.68 no existe —consultas
    # que pasan el filtro, no encuentran nada útil y terminan respondiendo
    # "no tengo la información sobre eso" con `Fuente: Jardín Botánico` al
    # pie—. Una cita al pie de una frase vacía es peor que no responder.
    #
    # Dos mediciones que conviene no perder, porque contradicen al ADR-0010
    # aunque el número no cambie:
    #
    # - La frontera que ese ADR midió ya no existe. Con consultas reales, la
    #   peor consulta legítima puntúa 0.6584 y el mejor mensaje que NO es
    #   del CU2, 0.6977: los rangos se solapan y ningún umbral los separa.
    #   Quien filtra la intención hoy es el agente (ADR-0013), no esto.
    # - Su control negativo difícil —"dónde me inscribo para que me regalen
    #   una compostera", 0.6752— puntúa MÁS ALTO que una consulta legítima
    #   de la prueba real —"qué recomendaciones me das para sembrar papa",
    #   0.6729—. No hay umbral que admita una y rechace la otra.
    RAG_UMBRAL_SIMILITUD: float = 0.68
    RAG_TOP_K: int = 4

    # La colección comunitaria lleva umbral propio, y no por capricho de
    # simetría: sus fragmentos son listas de tres o cuatro palabras
    # ("tomate, cilantro, lechuga"), no prosa de 400 tokens, así que sus
    # similitudes viven en otro rango. El de arriba se calibró contra la
    # colección oficial y aplicado aquí dejaría sin responder la consulta
    # más típica del CU4 (ADR-0011).
    #
    # 0.65 cae centrado en el hueco medido: peor consulta legítima 0.6765,
    # mejor consulta ajena 0.6327 —la de la fiebre, que importa que quede
    # fuera—.
    RAG_UMBRAL_COMUNITARIO: float = 0.65

    # --- Respaldo del CU2 con conocimiento del modelo ---------------------
    #
    # Cuando ninguna fuente oficial supera el umbral, el CU2 responde con el
    # conocimiento del modelo, sin citar nada y solo dentro del dominio.
    # Es el tercer nivel de la jerarquía de CLAUDE.md §6, que siempre estuvo
    # contemplado y que el ADR-0010 había decidido no usar aquí.
    #
    # Se revierte esa decisión por evidencia de campo: en la primera prueba
    # con celular, seis de diez consultas terminaron en el texto fijo de "no
    # le puedo responder". El criterio de éxito del proyecto es un SUS >= 68
    # con usuarias de la comunidad, y un asistente que se bloquea seis veces
    # en una sesión no llega a esa cifra.
    #
    # ES UN INTERRUPTOR A PROPÓSITO. Ponerlo en `false` en Railway devuelve
    # el comportamiento del ADR-0010 sin desplegar y sin tocar código, que es
    # lo que hace falta si la evaluación con usuarias dice que un consejo sin
    # respaldo confunde más de lo que ayuda.
    #
    # Lo que sostiene la jerarquía del §6 cuando esto está activo no es el
    # umbral, son dos cosas: que los dos caminos **nunca se mezclen en un
    # mismo mensaje** —o cita entero, o no cita nada— y que la respuesta sin
    # respaldo se abra reconociéndolo. Ver `app/services/orientacion.py`.
    CU2_RESPALDO_MODELO: bool = True

    # --- Memoria de conversación (CLAUDE.md §8) ---
    # Cuántos mensajes ve el agente de lo ya hablado. Se cuentan mensajes,
    # no turnos: 10 son unos cinco intercambios, y el último es el que la
    # usuaria acaba de escribir.
    #
    # Configurable por el mismo criterio que los umbrales del RAG
    # (ADR-0010): la Fase 4 lo declara calibrable y cambiarlo no invalida
    # nada de lo guardado, solo cuánto de ello se lee.
    MEMORIA_VENTANA_MENSAJES: int = 10

    # --- Identificación del despliegue ---
    # Las rellena Railway sola en cada despliegue desde GitHub
    # (comprobado en su documentación el 15/08/2026). No hay que definirlas
    # a mano, y en local quedan vacías, que es lo correcto: en local no hay
    # despliegue que identificar.
    #
    # Existen porque `/health` no decía qué versión estaba corriendo, y
    # confirmar un despliegue obligaba a mandar un WhatsApp de prueba.
    RAILWAY_GIT_COMMIT_SHA: str = ""
    RAILWAY_GIT_BRANCH: str = ""

    # --- Supabase / PostgreSQL ---
    # Cadena del *session pooler* (puerto 5432). Ver la validación de
    # más abajo para el motivo.
    DATABASE_URL: str
    DB_POOL_MIN: int = 1
    DB_POOL_MAX: int = 5

    LOG_LEVEL: str = "INFO"

    @field_validator("META_VERIFY_TOKEN")
    @classmethod
    def _validar_verify_token(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError(
                "META_VERIFY_TOKEN no puede estar vacío. Es una cadena que "
                "usted inventa y registra igual en el panel de Meta. "
                'Genérela con: python -c "import secrets; '
                'print(secrets.token_urlsafe(32))"'
            )
        return valor

    # Las dos validaciones siguientes se ejecutan al arrancar. Es
    # deliberado que el servicio no levante con una clave mal formada:
    # el fallo alternativo aparecería al registrar a la primera usuaria,
    # mucho más tarde y mucho más difícil de diagnosticar.

    @field_validator("PHONE_HASH_PEPPER")
    @classmethod
    def _validar_pepper(cls, valor: str) -> str:
        if len(valor) < 32:
            raise ValueError(
                "PHONE_HASH_PEPPER debe tener al menos 32 caracteres. "
                'Genérelo con: python -c "import secrets; '
                'print(secrets.token_hex(32))"'
            )
        return valor

    @field_validator("NAME_ENCRYPTION_KEY")
    @classmethod
    def _validar_clave_cifrado(cls, valor: str) -> str:
        try:
            bruta = base64.b64decode(valor, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(
                "NAME_ENCRYPTION_KEY debe venir codificada en base64."
            ) from exc

        if len(bruta) != 32:
            raise ValueError(
                f"NAME_ENCRYPTION_KEY debe ser de 32 bytes (AES-256); "
                f"la recibida tiene {len(bruta)}. Genérela con: "
                'python -c "import base64,os; '
                'print(base64.b64encode(os.urandom(32)).decode())"'
            )
        return valor

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def _validar_clave_gemini(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError(
                "GEMINI_API_KEY no puede estar vacía. Genere una en "
                "https://aistudio.google.com/apikey"
            )
        return valor

    @field_validator("GEMINI_GENERATIVE_MODEL")
    @classmethod
    def _validar_modelo_generativo(cls, valor: str) -> str:
        limpio = valor.strip()
        if not limpio:
            raise ValueError(
                "GEMINI_GENERATIVE_MODEL no puede estar vacío. Déjelo sin "
                "definir para usar el valor por defecto."
            )
        # Un identificador de embeddings aquí no fallaría al arrancar: el
        # error saldría en la primera conversación, como una respuesta vacía
        # difícil de relacionar con la causa.
        if "embedding" in limpio:
            raise ValueError(
                f"GEMINI_GENERATIVE_MODEL apunta a '{limpio}', que es un "
                "modelo de embeddings, no generativo. El modelo de "
                "embeddings no se configura por variable de entorno "
                "(ADR-0007)."
            )
        return limpio

    @field_validator("RAG_UMBRAL_SIMILITUD", "RAG_UMBRAL_COMUNITARIO")
    @classmethod
    def _validar_umbral(cls, valor: float) -> float:
        # Un umbral fuera de [0, 1] no tiene sentido como similitud coseno
        # y aquí no arrancaría el servicio.
        #
        # Lo que esta comprobación NO puede atrapar, y conviene no
        # atribuirle: escribir por error la *distancia* en lugar de la
        # similitud. La distancia equivalente a 0.68 es 0.32, que está en
        # rango y pasaría, dejando el CU2 respondiendo justamente con los
        # fragmentos que no vienen a cuento y sin dar ningún error. Contra
        # eso solo protege leer el aviso del `.env.example`.
        if not 0.0 <= valor <= 1.0:
            raise ValueError(
                f"RAG_UMBRAL_SIMILITUD debe estar entre 0 y 1; llegó {valor}. "
                "Es una SIMILITUD coseno, no una distancia."
            )
        return valor

    @field_validator("RAG_TOP_K")
    @classmethod
    def _validar_top_k(cls, valor: int) -> int:
        if valor < 1:
            raise ValueError(f"RAG_TOP_K debe ser al menos 1; llegó {valor}.")
        return valor

    @field_validator("MEMORIA_VENTANA_MENSAJES")
    @classmethod
    def _validar_ventana(cls, valor: int) -> int:
        # Al menos dos: con uno solo el agente vería la pregunta en curso y
        # nada de lo anterior, que es no tener memoria con el coste de
        # tenerla.
        if valor < 2:
            raise ValueError(
                f"MEMORIA_VENTANA_MENSAJES debe ser al menos 2; llegó {valor}."
            )
        return valor

    @field_validator("DATABASE_URL")
    @classmethod
    def _validar_cadena_conexion(cls, valor: str) -> str:
        # El transaction pooler de Supabase no admite prepared statements,
        # y asyncpg los usa por defecto. El fallo aparecería en tiempo de
        # ejecución con un mensaje difícil de relacionar con la causa, así
        # que se corta aquí.
        if ":6543" in valor:
            raise ValueError(
                "DATABASE_URL apunta al puerto 6543 (transaction pooler), "
                "que no admite prepared statements y rompe asyncpg. Use el "
                "session pooler: Supabase -> Connect -> Session pooler "
                "(pooler.supabase.com:5432)."
            )
        if not valor.startswith(("postgresql://", "postgres://")):
            raise ValueError(
                "DATABASE_URL debe ser una cadena de conexión de "
                "PostgreSQL (postgresql://...)."
            )
        return valor


settings = Settings()
