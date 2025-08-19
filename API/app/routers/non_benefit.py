# app/routers/non_benefit.py
from fastapi import APIRouter, UploadFile, File, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal, List
from app.database import get_db
from app.auth import deps
from app.schemas.nonBenefitSchema import NonBenefitItemRead
from app.crud import nonBenefitCRUD as crud
from app.services.non_benefit_import import read_excel_to_records

router = APIRouter(prefix="/non-benefit", tags=["non-benefit"], dependencies=[Depends(deps.get_current_user)])

@router.post("/import")
async def import_non_benefit(
    file: UploadFile = File(..., description="Excel (.xlsx/.xls)"),
    mode: Literal["replace", "upsert"] = Query("replace"),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Excel file required (.xlsx/.xls)")

    content = await file.read()
    try:
        records = read_excel_to_records(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse Excel: {e}")

    n = await (crud.replace_all(db, records) if mode == "replace" else crud.upsert_by_code(db, records))
    return {"ok": True, "mode": mode, "rows": n}

@router.get("/{code}", response_model=NonBenefitItemRead)
async def get_item_by_code(code: str, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_by_code(db, code)
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    return obj

@router.get("/", response_model=List[NonBenefitItemRead])
async def list_items(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    return await crud.list_items(db, limit=limit, offset=offset)

@router.get("/check/{code}")
async def check_is_benefit(code: str, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_by_code(db, code)
    is_non_benefit = obj is not None
    return {
        "code": code,
        "is_non_benefit": is_non_benefit,
        "is_benefit": not is_non_benefit
    }
