from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postuser:postuser@db:5432/users"
    SECRET_KEY: str = os.getenv("SECRET_KEY")

settings = Settings()