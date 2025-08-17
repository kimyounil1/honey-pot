import os
import uvicorn
from datetime import date
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, AsyncSessionLocal
from app.routers import user, policy, claim, chat, document, test
from app.crud import userCRUD
from app.schemas import userSchema
from contextlib import asynccontextmanager


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    # 1. 데이터베이스 테이블 생성
    await create_db_and_tables()
    print("Database tables created or already exist.")

    # 2. 기본 관리자 계정 확인 및 생성
    async with AsyncSessionLocal() as db:
        admin_email = os.getenv("ADMIN_EMAIL")
        admin_passwd = os.getenv("ADMIN_PW")
        if admin_email and admin_passwd:
            user_in_db = await userCRUD.get_user_by_email(db, email=admin_email)
            if not user_in_db:
                print(f"Admin user '{admin_email}' not found, creating one...")
                admin_user_in = userSchema.UserCreate(
                    name="관리자",
                    email=admin_email,
                    password=admin_passwd,
                    birth_date=date(2000, 1, 1)
                )
                await userCRUD.create_user(db, user_in=admin_user_in)
                print("Admin user created.")
            else:
                print(f"Admin user '{admin_email}' already exists.")
        else:
            print("ADMIN_EMAIL or ADMIN_PW environment variables not set. Skipping admin creation.")
    yield
    print("Shutting down...")


app = FastAPI(lifespan=lifespan, title="InsuranceApp")

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://0.0.0.0:3000", ],  # Next.js 개발 서버 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(user.router)
app.include_router(policy.router)
app.include_router(claim.router)
app.include_router(chat.router)
app.include_router(document.router)
app.include_router(test.router)
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
