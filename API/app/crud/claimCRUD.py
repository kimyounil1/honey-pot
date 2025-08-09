from . import AsyncSession, select, claimModel, claimSchema

async def create_claim(db: AsyncSession, claim_in: claimSchema.ClaimCreate):
    claim = claimModel.Claim(**claim_in.dict())
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return claim

async def get_claim(db: AsyncSession, claim_id: int):
    result = await db.execute(select(claimModel.Claim).where(claimModel.Claim.claim_id == claim_id))
    return result.scalars().first()
