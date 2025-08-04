from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=schemas.UserRead)
async def create_user(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_user(db, user_in)

@router.get("/{user_id}", response_model=schemas.UserRead)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
