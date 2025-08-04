import uvicorn
from fastapi import FastAPI
from app.database import Base, engine
from app.routers import user, policy, claim
from contextlib import asynccontextmanager

app = FastAPI(title="InsuranceApp")

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# 라우터 등록
app.include_router(user.router)
app.include_router(policy.router)
app.include_router(claim.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
