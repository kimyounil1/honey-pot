from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.policy_sync import sync_policies_from_opensearch
from app.auth import deps  # 인증 재사용(원하면 제거 가능)

router = APIRouter(prefix="/sync", tags=["sync"])

@router.post("/policies/from-opensearch")
async def sync_policies(
    dry_run: bool = Query(False, description="실제 저장 없이 통계만 보기"),
    db: AsyncSession = Depends(get_db),
):
    try:
        stats = await sync_policies_from_opensearch(db, dry_run=dry_run)
        return {"ok": True, **stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
