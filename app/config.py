"""Configuración del backend.

Todas las credenciales se leen de variables de entorno. En local se toman
del archivo .env (que NO se versiona); en Railway, de las variables del
servicio. Ningún secreto se escribe en el código.
"""

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

    LOG_LEVEL: str = "INFO"


settings = Settings()
