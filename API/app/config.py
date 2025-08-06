from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postuser:postuser@db:5432/users"
    SECRET_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()