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
    META_GRAPH_VERSION: str = "v26.0"

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
    # **Baja de 0.68 a 0.66 el 19/08/2026**, después de limpiar el corpus.
    #
    # Lo primero, porque importa más que el número: el umbral **ya no
    # significa lo mismo**. Hasta el ADR-0010 decidía responder o callar;
    # con el respaldo del modelo activo (`CU2_RESPALDO_MODELO`, aquí
    # debajo) decide **citar o no citar**. Por encima se responde con la
    # guía oficial y su atribución; por debajo responde el modelo, sin
    # fuente ninguna.
    #
    # Por qué baja. Quitar los renglones de índice del corpus **bajó las
    # similitudes** de las consultas que los recuperaban, porque lo que
    # ganaba era el índice. Medido sobre las 81 consultas de las dos
    # pruebas con celular:
    #
    #     Cuánto se demora en dar cosecha la papa   0.6883 -> 0.6865
    #     pero que plantas me sirven para interior  0.6755 -> 0.6643
    #     Que recomendaciones das para sembrar papa 0.7282 -> 0.7044
    #
    # Consultas legítimas quedaron rozando el 0.68 o por debajo, así que
    # mantenerlo dejaría sin citar cosas que el corpus sí responde.
    #
    # Y bajar es menos arriesgado que antes. El motivo por el que 0.65 se
    # descartó en su día era un modo de fallo concreto —consultas que pasan
    # el filtro, no encuentran nada útil y responden "no tengo la
    # información sobre eso" con `Fuente: Jardín Botánico` al pie—. Su
    # causa principal eran justo esos índices: un fragmento que puntúa alto
    # contra cualquier pregunta sobre plantas y no dice nada. Con ellos
    # fuera, el riesgo de bajar es menor.
    #
    # Tres mediciones que conviene no perder, porque contradicen al
    # ADR-0010:
    #
    # - La frontera que ese ADR midió no existe. Con 81 consultas reales,
    #   los rangos de legítimas y ajenas se solapan y **ningún umbral los
    #   separa**: "Que conocimiento en agricultura sabes" (no es CU2)
    #   puntúa 0.6779 y "Qué puedo hacer si mis plantas no dan frutos"
    #   (sí lo es) puntúa 0.6775. Quien filtra la intención hoy es el
    #   agente (ADR-0013), no esto.
    # - Los mensajes del CU3 y del CU4 puntúan **entre los mejores** —"Y
    #   que están sembrando las otras huertas" da 0.7194—. Subir el umbral
    #   no protegería de ellos; solo el enrutamiento lo hace.
    # - Lo que sí separa solo es lo verdaderamente ajeno: "Que carro está
    #   barato hoy en día" 0.5782, y los barrios entre 0.587 y 0.612.
    #
    # **Esto sigue sin ser una calibración cerrada.** Falta etiquetar
    # leyendo el fragmento recuperado de cada consulta, y queda pendiente
    # la desviación de `jbb_practicas_2022` (CLAUDE.md §11), que impide
    # reproducir el corpus entero.
    RAG_UMBRAL_SIMILITUD: float = 0.66
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

    # --- Presentación del listado del CU4 (ADR-0021) ----------------------
    #
    # Cuántas huertas por mensaje y cuántos cultivos por huerta. Son
    # decisiones de PRESENTACIÓN, no de recuperación, y por eso no reusan
    # `RAG_TOP_K`: aquella gobierna cuántos fragmentos entran al prompt del
    # CU2, y subirla para enseñar más huertas le cambiaría al CU2 el
    # tamaño de su contexto en mitad de una calibración que sigue abierta
    # (CLAUDE.md §8). Una perilla, una cosa.
    #
    # Tres y cinco los fijó el autor el 08/09/2026. Tres deja el mensaje
    # en siete renglones contando encabezado y cola, dentro de los 6-8 que
    # manda el CLAUDE.md §11; el resto de huertas se ofrecen en la tanda
    # siguiente, que es lo que sostiene la tabla `listado_comunitario_
    # pendiente`. Cinco cultivos evitan que una huerta con quince especies
    # se lleve el mensaje entero.
    #
    # Calibrables en la Fase 7 desde Railway, como los umbrales: cambiarlos
    # no invalida nada guardado, solo cuánto se enseña de una vez.
    CU4_HUERTAS_POR_TANDA: int = 3
    CU4_CULTIVOS_POR_HUERTA: int = 5

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

    @field_validator("CU4_HUERTAS_POR_TANDA", "CU4_CULTIVOS_POR_HUERTA")
    @classmethod
    def _validar_tamano_listado(cls, valor: int) -> int:
        # Cero huertas por tanda daría un listado vacío con su cola
        # diciendo cuántas hay, y cero cultivos, huertas sin nada al lado.
        # Las dos cosas fallarían en silencio, que es lo que aquí se evita.
        if valor < 1:
            raise ValueError(
                f"Los tamaños del listado del CU4 deben ser al menos 1; "
                f"llegó {valor}."
            )
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
