# app/crud/notificationCRUD.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from app.models import notificationModel
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
    q = select(notificationModel.Notification).where(
        notificationModel.Notification.user_id == user_id,
        notificationModel.Notification.send_on <= day,
    ).order_by(notificationModel.Notification.send_on.asc())
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
