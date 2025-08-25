from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.crud import policyCRUD
from app.schemas import policySchema, userSchema
from app.auth import deps

router = APIRouter(prefix="/policies", tags=["insurance policies"])

@router.post("/", response_model=policySchema.InsurancePolicyRead)
async def create_policy(policy_in: policySchema.InsurancePolicyCreate, db: AsyncSession = Depends(get_db)):
    return await policyCRUD.create_policy(db, policy_in)

class PolicyPayload(BaseModel):
    policy_id: str
@router.post("/submit", response_model=policySchema.InsurancePolicyRead)
async def add_policy(
    payload: PolicyPayload, 
    db: AsyncSession = Depends(get_db), 
    current_user: userSchema.UserRead = Depends(deps.get_current_user)
):
    policy_id = payload.policy_id
    template = await policyCRUD.get_policy(db, policy_id)
    if not template:
        raise HTTPException(status_code=404, detail="Policy not found")
    user_id = current_user.user_id
    existing = await policyCRUD.get_policy_with_user(db, user_id, policy_id)
    if existing:
        return existing
    
    create_in = policySchema.InsurancePolicyCreate(
        user_id=current_user.user_id,
        policy_id=template.policy_id,
        insurer=template.insurer,
        product_code=template.product_code,
        version=template.version,
        effective_date=template.effective_date,
        policy_type=template.policy_type,
        coverage_summary=template.coverage_summary,
        start_date=template.start_date,
        end_date=template.end_date,
        coverage_item_names=list(getattr(template, "coverage_item_names", []) or []),
    )
    
    result = await policyCRUD.create_policy(db, create_in) 
    return result

@router.get("/insurers", response_model=policySchema.InsurancePolicyInsurers)
async def get_insurers(db: AsyncSession = Depends(get_db)):
    insurers = await policyCRUD.get_insurers(db)
    return {"insurers": insurers}

@router.get("/{insurer}/list", response_model=policySchema.InsurancePolicyList)
async def get_policies_by_insurer(insurer: str, db: AsyncSession = Depends(get_db)):
    policy_list = await policyCRUD.get_policies_by_insurer(db, insurer)
    return {"insurer": insurer, "policies": policy_list}

@router.get("/{policy_id}", response_model=policySchema.InsurancePolicyRead)
async def get_policy(policy_id: str, db: AsyncSession = Depends(get_db)):
    policy = await policyCRUD.get_policy(db, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy
