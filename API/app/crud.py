from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app import models
from app.schemas import claimSchema, policySchema, tokenSchema, userSchema
from app.auth import hash

########
### USER
########
async def create_user(db: AsyncSession, user_in: userSchema.UserCreate) -> models.User:
    user = models.User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hash.get_password_hash(user_in.password), # 유저 생성시 해싱된 패스워드 저장
        birth_date=user_in.birth_date,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.User).where(models.User.user_id == user_id))
    return result.scalars().first()

# 이메일로 사용자 조회
async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.User).filter(models.User.email == email))
    return result.scalars().first()

########################
### INSURANCE_POLICY
########################
async def create_policy(db: AsyncSession, policy_in: policySchema.InsurancePolicyCreate):
    policy = models.InsurancePolicy(**policy_in.dict())
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy

async def get_policy(db: AsyncSession, policy_id: int):
    result = await db.execute(select(models.InsurancePolicy).where(models.InsurancePolicy.policy_id == policy_id))
    return result.scalars().first()


################
### CLAIM
################
async def create_claim(db: AsyncSession, claim_in: claimSchema.ClaimCreate):
    claim = models.Claim(**claim_in.dict())
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return claim

async def get_claim(db: AsyncSession, claim_id: int):
    result = await db.execute(select(models.Claim).where(models.Claim.claim_id == claim_id))
    return result.scalars().first()
