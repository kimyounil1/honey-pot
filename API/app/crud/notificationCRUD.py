# app/crud/notificationCRUD.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from app.models import notificationModel
from app.models.claimTimelineModel import ClaimTimeline
from app.schemas import notificationSchema

async def upsert(db: AsyncSession, payload: notificationSchema.NotificationCreate):
    # 간단 upsert: 같은 timeline_id+send_on 있으면 갱신, 없으면 생성
    q = select(notificationModel.Notification).where(
        notificationModel.Notification.timeline_id == payload.timeline_id,
        notificationModel.Notification.send_on == payload.send_on,
    )
    r = await db.execute(q)
    obj = r.scalars().first()
    if obj:
        for k, v in payload.dict().items():
            setattr(obj, k, v)
    else:
        obj = notificationModel.Notification(**payload.dict())
        db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def list_for_user_on_or_before(db: AsyncSession, user_id: int, day: date):
    """
    ✅ 읽음 여부(is_read)는 무시하고,
    ✅ 해당 타임라인이 mute(is_muted) 된 경우만 제외하여 반환.
    """
    q = (
        select(notificationModel.Notification)
        .join(ClaimTimeline, ClaimTimeline.id == notificationModel.Notification.timeline_id)
        .where(
            notificationModel.Notification.user_id == user_id,
            notificationModel.Notification.send_on <= day,
            ClaimTimeline.is_muted == False,  # 다시보지않기만 팝업 차단
        )
        .order_by(notificationModel.Notification.send_on.asc())
    )
    r = await db.execute(q)
    return r.scalars().all()

async def mark_read(db: AsyncSession, notif_id: int):
    q = select(notificationModel.Notification).where(
        notificationModel.Notification.id == notif_id
    )
    r = await db.execute(q)
    obj = r.scalars().first()
    if not obj:
        return None
    obj.is_read = True
    await db.commit()
    await db.refresh(obj)
    return obj

# (테스트/운영 편의) 읽음 해제도 유지
async def mark_unread(db: AsyncSession, notif_id: int):
    q = select(notificationModel.Notification).where(
        notificationModel.Notification.id == notif_id
    )
    r = await db.execute(q)
    obj = r.scalars().first()
    if not obj:
        return None
    obj.is_read = False
    await db.commit()
    await db.refresh(obj)
    return obj
