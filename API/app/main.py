import os
import uvicorn
from datetime import date
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging_conf import setup_logging
from app.database import Base, engine, AsyncSessionLocal
from app.services.non_benefit_seed import maybe_seed_on_start
from app.routers import user, policy, claim, chat, document, test, non_benefit, ocr, sync
from app.crud import userCRUD
from app.schemas import userSchema
from contextlib import asynccontextmanager
from app.models.enums import product_type_enum, renewal_type_enum

# 로그 디렉토리 준비
LOG_DIR = os.getenv("APP_LOG_DIR", "/src/app/log")
os.makedirs(LOG_DIR, exist_ok=True)

setup_logging(LOG_DIR)

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(product_type_enum.create, checkfirst=True)
        await conn.run_sync(renewal_type_enum.create, checkfirst=True)
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
        test_email = os.getenv("TEST_USER_EMAIL")
        test_passwd = os.getenv("TEST_USER_PW")
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
        
        if test_email and test_passwd:
            user_in_db = await userCRUD.get_user_by_email(db, email=test_email)
            if not user_in_db:
                print(f"test user '{test_email}' not found, creating one...")
                test_user_in = userSchema.UserCreate(
                    name="테스트",
                    email=test_email,
                    password=test_passwd,
                    birth_date=date(2000, 1, 1)
                )
                await userCRUD.create_user(db, user_in=test_user_in)
                print("Test user created.")
            else:
                print(f"Test user '{test_email}' already exists.")
        else:
            print("TEST_USER_EMAIL or TEST_USER_PW environment variables not set. Skipping test user creation.")
        
        try:
            inserted = await maybe_seed_on_start(db)
            if inserted:
                print(f"[non-benefit] seeded {inserted} rows on startup")
            else:
                print("[non-benefit] seeding skipped (no path or data exists).")
        except Exception as e:
            (
                print(f"[non-benefit] seeding failed: {e}"))
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
app.include_router(non_benefit.router)
app.include_router(ocr.router)
app.include_router(sync.router)  # include 추가

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
