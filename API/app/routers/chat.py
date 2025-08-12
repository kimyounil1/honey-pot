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

    # 2단계: messages 준비
    llm_req = await prepare_llm_request(
        user_id=current_user.user_id,
        text=body.text,
        first_message=body.first_message,
        attachment_ids=body.attachment_ids
    )
    # 3단계: LLM 호출
    answer = await call_llm(llm_req["messages"])
    return {
        "answer": answer,
        "mode": llm_req["mode"],
        "used_attachments": llm_req["attachments_used"],
    }
