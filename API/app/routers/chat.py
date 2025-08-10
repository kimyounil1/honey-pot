# app/routers/chat.py
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.config import settings
from app.service.llm_service import ask_llm

router = APIRouter(prefix="/chat", tags=["chat"])

class AskBody(BaseModel):
    user_id: Optional[int] = None
    text: str
    first_message: bool = False   # ✅ 추가

@router.post("/ask")
async def ask(body: AskBody, db: AsyncSession = Depends(get_db)):
    answer = await ask_llm(body.text, first_message=body.first_message)  # ✅ 변경
    # TODO: 필요하면 여기서 대화 로그 DB에 저장
    return {"ok": True, "answer": answer}

@router.post("/webhook")
async def webhook(
    body: AskBody,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: Optional[str] = Header(None),
):
    if settings.WEBHOOK_SECRET and (x_webhook_signature or "") != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    answer = await ask_llm(body.text, first_message=body.first_message)  # ✅ 변경
    return {"answer": answer}
