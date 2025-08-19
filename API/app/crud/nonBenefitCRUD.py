# app/crud/nonBenefitCRUD.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Dict, Optional
from app.models.nonBenefitModel import NonBenefitItem

async def replace_all(db: AsyncSession, items: List[Dict]) -> int:
    await db.execute(delete(NonBenefitItem))
    for it in items:
        db.add(NonBenefitItem(**it))
    await db.commit()
    # rowcount가 아닌 실제 insert 수 반환
    return len(items)

async def upsert_by_code(db: AsyncSession, items: List[Dict]) -> int:
    cnt = 0
    for it in items:
        code = (it.get("code") or "").strip()
        if not code:
            continue
        res = await db.execute(select(NonBenefitItem).where(NonBenefitItem.code == code))
        obj: Optional[NonBenefitItem] = res.scalar_one_or_none()
        if obj:
            for k, v in it.items():
                setattr(obj, k, v)
        else:
            db.add(NonBenefitItem(**it))
        cnt += 1
    await db.commit()
    return cnt

async def get_by_code(db: AsyncSession, code: str) -> Optional[NonBenefitItem]:
    res = await db.execute(select(NonBenefitItem).where(NonBenefitItem.code == code))
    return res.scalar_one_or_none()

async def list_items(db: AsyncSession, limit: int = 50, offset: int = 0) -> list[NonBenefitItem]:
    res = await db.execute(
        select(NonBenefitItem).order_by(NonBenefitItem.id).limit(limit).offset(offset)
    )
    return list(res.scalars().all())
