from pydantic_settings import BaseSettings

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
    WATSONX_API_KEY: str = ""
    WATSONX_URL: str = ""
    WATSONX_PROJECT_ID: str = ""
    WATSONX_MODEL_ID: str = ""

settings = Settings()
