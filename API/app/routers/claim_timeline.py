# app/routers/claim_timeline.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import deps
from app.schemas import claimTimelineSchema, userSchema
from app.crud import claimTimelineCRUD
from app.services.scheduler import scan_and_build_timeline

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
