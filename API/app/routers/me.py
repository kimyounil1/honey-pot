from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.auth import deps
from app.schemas import userSchema
from app.models.policyModel import InsurancePolicy

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/policies")
async def get_my_policies(
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    stmt = select(InsurancePolicy.id, InsurancePolicy.policy_id, InsurancePolicy.insurer).where(
        InsurancePolicy.user_id == current_user.user_id
    )
    res = await db.execute(stmt)
    rows = res.all()
    return [
        {"id": r[0], "policy_id": r[1], "insurer": r[2]} for r in rows if r[1] is not None
    ]
