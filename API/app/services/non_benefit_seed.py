# app/services/non_benefit_seed.py
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.non_benefit_import import read_excel_to_records
from app.crud import nonBenefitCRUD as crud
from app.models.nonBenefitModel import NonBenefitItem

async def seed_from_excel(
    db: AsyncSession,
    path: str,
    mode: str = "replace",
    skip_if_exists: bool = True,
) -> int:
    if skip_if_exists:
        count = await db.scalar(select(func.count(NonBenefitItem.id)))
        if count and count > 0:
            return 0

    content = Path(path).read_bytes()
    records = read_excel_to_records(content)
    if mode == "replace":
        return await crud.replace_all(db, records)
    else:
        return await crud.upsert_by_code(db, records)

async def maybe_seed_on_start(db: AsyncSession) -> int:
    """
    Settings 기반 시더 실행:
    - settings.NON_BENEFIT_EXCEL_PATH
    - settings.NON_BENEFIT_IMPORT_MODE
    - settings.NON_BENEFIT_SKIP_IF_EXISTS
    """
    path = settings.NON_BENEFIT_EXCEL_PATH
    if not path:
        return 0

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"NON_BENEFIT_EXCEL_PATH not found: {p}")

    return await seed_from_excel(
        db,
        path=str(p),
        mode=settings.NON_BENEFIT_IMPORT_MODE,
        skip_if_exists=settings.NON_BENEFIT_SKIP_IF_EXISTS,
    )
