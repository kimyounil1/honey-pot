from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import claimCRUD
from app.schemas import claimSchema

router = APIRouter(prefix="/claims", tags=["claims"])

@router.post("/", response_model=claimSchema.ClaimRead)
async def create_claim(claim_in: claimSchema.ClaimCreate, db: AsyncSession = Depends(get_db)):
    return await claimCRUD.create_claim(db, claim_in)

@router.get("/{claim_id}", response_model=claimSchema.ClaimRead)
async def get_claim(claim_id: int, db: AsyncSession = Depends(get_db)):
    claim = await claimCRUD.get_claim(db, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim
