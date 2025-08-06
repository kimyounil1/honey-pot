from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from passlib.context import CryptContext

from app.database import get_db
from app import crud, schemas
from app.auth import token as token_service
from app.schemas import claimSchema, policySchema, tokenSchema, userSchema

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=userSchema.UserRead)
async def create_user(user_in: userSchema.UserCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_user(db, user_in)

@router.get("/{user_id}", response_model=userSchema.UserRead)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/login", response_model=tokenSchema.Token)
async def login_for_access_token(login_data: userSchema.UserLogin, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user_by_email(db, email=login_data.email)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    if not user or not pwd_context.verify(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="이메일 혹은 비밀번호가 틀립니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=token_service.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = token_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/by-email/{email}", response_model=userSchema.UserRead)
async def get_user_by_email(email: str, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
