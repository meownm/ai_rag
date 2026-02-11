from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "embeddings-service"
    app_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8200
    default_model_id: str = "BAAI/bge-small-en-v1.5"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
