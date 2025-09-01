# app/routers/notifications.py
from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import deps
from app.schemas import userSchema, notificationSchema
from app.crud import notificationCRUD

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=List[notificationSchema.NotificationRead])
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    # ✅ 읽지 않은 + mute 아닌 타임라인의 알림만 반환
    rows = await notificationCRUD.list_for_user_on_or_before(
        db, current_user.user_id, date.today()
    )
    return rows


@router.post("/{notif_id}/read")
async def mark_read(
    notif_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    obj = await notificationCRUD.mark_read(db, notif_id)
    if not obj or obj.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True}
