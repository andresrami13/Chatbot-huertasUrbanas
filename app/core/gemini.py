"""Cliente de la API de Gemini.

Un único cliente compartido por todo el backend, análogo al pool de
`basedatos.py`: crearlo por llamada desperdiciaría la reutilización de
conexiones HTTP del SDK.

Se usa `google-genai`, el SDK vigente. El anterior
(`google-generativeai`) es el legado y no recibe los modelos nuevos.

Este módulo solo construye el cliente y declara qué modelos se usan. Quien
vectoriza es `app/services/embeddings.py`; el agente llegará en la Fase 6
(un componente, una responsabilidad — Fase 3, Tabla 2).
"""

import logging

from google import genai

from app.config import settings

logger = logging.getLogger(__name__)

# --- Modelo generativo ----------------------------------------------------
# Sí es configurable, por variable de entorno: se puede cambiar en Railway
# sin desplegar. Ningún dato almacenado depende de él, así que cambiarlo no
# invalida nada. Lo usarán el agente, la extracción de entidades y la
# redacción del RAG, cada uno con su temperatura (CLAUDE.md §8).
MODELO_GENERATIVO = settings.GEMINI_GENERATIVE_MODEL

# --- Modelo de embeddings (CLAUDE.md §9.1) --------------------------------
# Este, en cambio, NO es configurable, y la asimetría es deliberada
# (ADR-0007): los embeddings de dos modelos distintos viven en espacios
# vectoriales incompatibles. Cambiarlo por variable de entorno dejaría las
# consultas nuevas comparándose contra vectores viejos —sin error, solo con
# recuperación degradada— y obliga a re-vectorizar todo el corpus.
#
# Que exija un commit es la garantía de que no se cambie por accidente.
# Los documentos de las Fases 3 y 4 citan text-embedding-004, que Google
# retiró el 14 de enero de 2026.
#
# Se mantiene gemini-embedding-001 y no se pasa a gemini-embedding-2, pese
# a que este último es el reemplazo que recomienda Google, por dos motivos
# comprobados en la documentación:
#
#   1. gemini-embedding-2 no admite task_type. La asimetría entre
#      RETRIEVAL_DOCUMENT (ingesta) y RETRIEVAL_QUERY (consulta) es una
#      palanca de calidad del RAG que se perdería, sustituida por
#      instrucciones dentro del texto.
#   2. gemini-embedding-2 devuelve UN embedding agregado para varias
#      entradas, no uno por entrada. La ingesta por lotes de fragmentos
#      exigiría una llamada por fragmento.
#
# La fecha de retiro de gemini-embedding-001 es el 14 de mayo de 2028, muy
# por detrás de la Fase 8, así que no hay urgencia de migración.
MODELO_EMBEDDING = "gemini-embedding-001"

# 768 y no las 3072 por defecto: pgvector solo indexa hasta 2000
# dimensiones con el tipo `vector`. El truncado es Matryoshka, previsto por
# el modelo, no un recorte arbitrario.
#
# Consecuencia que obliga a normalizar: con gemini-embedding-001 el vector
# truncado llega SIN normalizar. Lo hace `embeddings.py`.
DIMENSIONES_EMBEDDING = 768

_cliente: genai.Client | None = None


def obtener_cliente() -> genai.Client:
    """Devuelve el cliente compartido, creándolo la primera vez."""
    global _cliente

    if _cliente is None:
        _cliente = genai.Client(api_key=settings.GEMINI_API_KEY)
        # Sin la clave, evidentemente. Los modelos sí se registran: si
        # alguien cambia la variable en Railway, la bitácora dice con qué
        # quedó arrancando el servicio.
        logger.info(
            "Cliente de Gemini creado | generativo=%s | embedding=%s",
            MODELO_GENERATIVO,
            MODELO_EMBEDDING,
        )

    return _cliente
