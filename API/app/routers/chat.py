# app/routers/chat.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
# from sqlalchemy.ext.asyncio import AysncSession

from app.services.stage import prepare_llm_request
from app.services.llm_gateway import call_llm

# from app.crud import chatCRUD 
from app.models.userModel import User
# from app.database import get_db

from app.auth import deps

# from app.schemas.chatSchema import ChatBase
from app.schemas.userSchema import UserRead

router = APIRouter(prefix="/chat", tags=["chat"])

class AskBody(BaseModel):
    # user_id: str
    text: str
    first_message: bool = False
    attachment_ids: Optional[List[str]] = None  # 업로드된 file_id 배열

@router.post("/ask")
async def ask(
    body: AskBody,
    current_user: UserRead = Depends(deps.get_current_user),
    # db: AsyncSession = Depends(get_db)
):
    print(f"[ROUTER] /chat/ask user_id={body.user_id} first={body.first_message} text='{body.text[:80]}'")
    # 2단계: messages 준비
    llm_req = await prepare_llm_request(
        user_id=current_user.user_id,
        text=body.text,
        first_message=body.first_message,
        attachment_ids=body.attachment_ids
    )

    # 폴백이면 LLM 호출하지 않고 정적 응답 바로 반환
    if "static_answer" in llm_req and llm_req["static_answer"]:
        print(f"[ROUTER] LLM skipped (FALLBACK). mode={llm_req['mode']}, used_attachments={llm_req['attachments_used']}")
        return {
            "answer": llm_req["static_answer"]["answer"],
            "mode": llm_req["mode"],
            "used_attachments": llm_req["attachments_used"],
        }

    # 3단계: LLM 호출
    answer = await call_llm(llm_req["messages"])

    # 완료 로그
    print(f"[ROUTER] LLM done. mode={llm_req['mode']}, used_attachments={llm_req['attachments_used']}")

    return {
        "answer": answer,
        "mode": llm_req["mode"],
        "used_attachments": llm_req["attachments_used"],
    }
