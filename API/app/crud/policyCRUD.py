from . import AsyncSession, select, policyModel, policySchema

async def create_policy(db: AsyncSession, policy_in: policySchema.InsurancePolicyCreate):
    policy = policyModel.InsurancePolicy(**policy_in.dict())
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy

async def get_policy(db: AsyncSession, policy_id: int):
    result = await db.execute(select(policyModel.InsurancePolicy).where(InsurancePolicy.policy_id == policy_id))
    return result.scalars().first()