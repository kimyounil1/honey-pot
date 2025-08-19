from pydantic_settings import BaseSettings
from typing import Optional, Literal
from pydantic import Field

class Settings(BaseSettings):
    # Pydantic-settings will automatically load these from environment variables.
    # The `env_file` in docker-compose.yaml makes the variables from .env available.
    DATABASE_URL: str
    SECRET_KEY: str
    OPENAI_API_KEY: str
    WEBHOOK_SECRET: str = ""

    # OpenSearch settings
    OPENSEARCH_HOST: str
    OPENSEARCH_USERNAME: str
    OPENSEARCH_PASSWORD: str
    OPENSEARCH_INDEX: str
    OPENSEARCH_PIPELINE: str # optional ingest pipeline for embeddings
    OPENSEARCH_MAX_CHARS: int # Titan v2 ~8k tokens ≈50k chars per chunk
    OPENSEARCH_REGION: str
    OPENSEARCH_TIMEOUT: int = 40

    #왓슨 Setting값
    WATSONX_API_KEY: str
    WATSONX_URL: str
    WATSONX_PROJECT_ID: str
    WATSONX_MODEL_ID: str

    NON_BENEFIT_EXCEL_PATH: Optional[str] = Field(
        default="./app/data/비급여_리스트.xlsx"
    )
    NON_BENEFIT_IMPORT_MODE: Literal["replace", "upsert"] = Field(default="replace")
    NON_BENEFIT_SKIP_IF_EXISTS: bool = Field(default=True)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
