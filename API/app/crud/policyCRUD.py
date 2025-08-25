from . import AsyncSession, select, policyModel, policySchema

async def create_policy(db: AsyncSession, policy_in: policySchema.InsurancePolicyCreate):
    policy = policyModel.InsurancePolicy(**policy_in.dict())
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy

async def get_policy(db: AsyncSession, policy_id: str):
    result = await db.execute(select(policyModel.InsurancePolicy).where(policyModel.InsurancePolicy.policy_id == policy_id))
    return result.scalars().first()

async def get_policies_by_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(policyModel.InsurancePolicy).where(policyModel.InsurancePolicy.user_id == user_id))
    return result.scalars().all()

async def get_policy_with_user(db: AsyncSession, user_id: int, policy_id: str):
    result = await db.execute(select(policyModel.InsurancePolicy).where(policyModel.InsurancePolicy.user_id == user_id, policyModel.InsurancePolicy.policy_id == policy_id))
    return result.scalars().first()

async def get_insurers(db: AsyncSession):
    result = await db.execute(select(policyModel.InsurancePolicy.insurer).distinct())
    return result.scalars().all()

async def get_policies_by_insurer(db:AsyncSession, insurer: str):
    result = await db.execute(select(policyModel.InsurancePolicy.policy_id).where(policyModel.InsurancePolicy.insurer == insurer))
    return result.scalars().all()