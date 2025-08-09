from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import policyCRUD
from app.schemas import policySchema

router = APIRouter(prefix="/policies", tags=["insurance policies"])

@router.post("/", response_model=policySchema.InsurancePolicyRead)
async def create_policy(policy_in: policySchema.InsurancePolicyCreate, db: AsyncSession = Depends(get_db)):
    return await policyCRUD.create_policy(db, policy_in)

@router.get("/{policy_id}", response_model=policySchema.InsurancePolicyRead)
async def get_policy(policy_id: int, db: AsyncSession = Depends(get_db)):
    policy = await policyCRUD.get_policy(db, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy
