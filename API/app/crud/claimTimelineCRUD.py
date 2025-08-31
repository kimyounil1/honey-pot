from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.claimTimelineModel import ClaimTimeline
from app.schemas import claimTimelineSchema

async def get_by_chat(db: AsyncSession, chat_id: int):
    r = await db.execute(select(ClaimTimeline).where(ClaimTimeline.chat_id == chat_id))
    return r.scalars().first()

async def create(db: AsyncSession, payload: claimTimelineSchema.ClaimTimelineCreate):
    obj = ClaimTimeline(**payload.dict())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def list_by_user(db: AsyncSession, user_id: int):
    r = await db.execute(
        select(ClaimTimeline)
        .where(ClaimTimeline.user_id == user_id)
        .order_by(ClaimTimeline.deadline_date.asc())
    )
    return r.scalars().all()
