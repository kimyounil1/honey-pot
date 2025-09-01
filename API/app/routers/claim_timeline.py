# app/routers/claim_timeline.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.auth import deps
from app.schemas import claimTimelineSchema, userSchema
from app.crud import claimTimelineCRUD
from app.services.scheduler import scan_and_build_timeline
from app.models.claimTimelineModel import ClaimTimeline  # ✅ mute 토글에 사용

router = APIRouter(prefix="/claim-timeline", tags=["claim_timeline"])


@router.get("/", response_model=List[claimTimelineSchema.ClaimTimelineRead])
async def list_my_timeline(
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    rows = await claimTimelineCRUD.list_by_user(db, current_user.user_id)
    return rows


@router.post("/scan")
async def manual_scan(
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    # 관리자가 아니어도 자기 채팅 위주로 스캔되는 현재 로직 특성상 전체 스캔 허용(내부 서비스 용도)
    await scan_and_build_timeline()
    return {"ok": True}


# ✅ 새로 추가: 타임라인 "다시 보지 않기" 토글(mute)
@router.post("/{timeline_id}/mute")
async def mute_timeline(
    timeline_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    row = await claimTimelineCRUD.get_by_id(db, timeline_id)
    if not row or row.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="not found")
    await claimTimelineCRUD.set_mute(db, timeline_id, True)
    return {"ok": True}

@router.post("/{timeline_id}/unmute")
async def unmute_timeline(
    timeline_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    row = await claimTimelineCRUD.get_by_id(db, timeline_id)
    if not row or row.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="not found")
    await claimTimelineCRUD.set_mute(db, timeline_id, False)
    return {"ok": True}
