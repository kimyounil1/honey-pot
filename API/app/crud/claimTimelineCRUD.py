# app/crud/claimTimelineCRUD.py
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claimTimelineModel import ClaimTimeline
from app.schemas import claimTimelineSchema


# ========== 기존 ==========
async def get_by_chat(db: AsyncSession, chat_id: int):
    r = await db.execute(
        select(ClaimTimeline).where(ClaimTimeline.chat_id == chat_id)
    )
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


async def get_by_id(db: AsyncSession, timeline_id: int):
    r = await db.execute(select(ClaimTimeline).where(ClaimTimeline.id == timeline_id))
    return r.scalars().first()

async def set_mute(db: AsyncSession, timeline_id: int, flag: bool):
    r = await db.execute(select(ClaimTimeline).where(ClaimTimeline.id == timeline_id))
    obj = r.scalars().first()
    if not obj:
        return None
    obj.is_muted = flag
    await db.commit()
    await db.refresh(obj)
    return obj


# ========== 추가(중복판정 키 강화): user_id + policy_id + disease_code + base_date ==========
async def get_by_unique(
    db: AsyncSession,
    *,
    user_id: int,
    policy_id: str,
    disease_code: Optional[str],
    base_date: date,
):
    """
    타임라인 고유 키(중복 판정): user_id + policy_id + disease_code + base_date
    disease_code가 NULL 허용이면 is_(None)으로 비교합니다.
    """
    conds = [
        ClaimTimeline.user_id == user_id,
        ClaimTimeline.policy_id == policy_id,
        ClaimTimeline.base_date == base_date,
    ]
    if disease_code is None:
        conds.append(ClaimTimeline.disease_code.is_(None))
    else:
        conds.append(ClaimTimeline.disease_code == disease_code)

    r = await db.execute(
        select(ClaimTimeline)
        .where(*conds)
        .order_by(ClaimTimeline.id.desc())
    )
    return r.scalars().first()


async def upsert(
    db: AsyncSession,
    payload: claimTimelineSchema.ClaimTimelineCreate,
):
    """
    user_id + policy_id + disease_code + base_date 로 기존 레코드가 있으면 업데이트,
    없으면 생성합니다. (기존 create는 그대로 두고, 서비스에서 이 함수를 호출)
    """
    existing = await get_by_unique(
        db,
        user_id=payload.user_id,
        policy_id=payload.policy_id,
        disease_code=payload.disease_code,
        base_date=payload.base_date,
    )

    if existing:
        updated = False

        # 필요한 필드만 보수적으로 갱신
        if payload.expected_amount is not None and existing.expected_amount != payload.expected_amount:
            existing.expected_amount = payload.expected_amount
            updated = True

        # chat_id가 새로 들어왔고 기존이 비어있으면 연결
        if getattr(payload, "chat_id", None) and not existing.chat_id:
            existing.chat_id = payload.chat_id
            updated = True

        # deadline_date가 계산/수정된 경우 반영
        if getattr(payload, "deadline_date", None) and existing.deadline_date != payload.deadline_date:
            existing.deadline_date = payload.deadline_date
            updated = True

        # (원하면 disease_name, policy_name 등도 여기서 보수적으로 갱신)

        if updated:
            await db.commit()
            await db.refresh(existing)
        return existing

    # 없으면 신규 생성
    return await create(db, payload)
