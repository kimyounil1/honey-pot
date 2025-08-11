from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Pydantic-settings will automatically load these from environment variables.
    # The `env_file` in docker-compose.yaml makes the variables from .env available.
    DATABASE_URL: str
    SECRET_KEY: str
    OPENAI_API_KEY: str
    WEBHOOK_SECRET: str = ""

    # By removing the inner Config class and os.getenv, we rely solely on environment
    # variables, which is the standard practice for Docker.

settings = Settings()
