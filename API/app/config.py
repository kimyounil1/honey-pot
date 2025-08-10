from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
<<<<<<< HEAD
    DATABASE_URL: str
    SECRET_KEY: str
    OPENAI_API_KEY: str
    WEBHOOK_SECRET: str = ""

    class Config:
        env_file = ".env"
=======
    DATABASE_URL: str = "postgresql+asyncpg://postuser:postuser@db:5432/users"
    SECRET_KEY: str = os.getenv("SECRET_KEY")
>>>>>>> 1d7fcad4234dd5cb90a81edb12019c3838911dc8

settings = Settings()
