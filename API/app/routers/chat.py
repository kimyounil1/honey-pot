# app/routers/chat.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.assistants.stage import prepare_llm_request
from app.assistants.llm_gateway import call_llm

router = APIRouter(prefix="/chat", tags=["chat"])

class AskBody(BaseModel):
    user_id: str
    text: str
    first_message: bool = False
    attachment_ids: Optional[List[str]] = None  # 업로드된 file_id 배열

@router.post("/ask")
async def ask(body: AskBody):
    # 2단계: messages 준비
    llm_req = await prepare_llm_request(
        user_id=body.user_id,
        text=body.text,
        first_message=body.first_message,
        attachment_ids=body.attachment_ids,
    )
    # 3단계: LLM 호출
    answer = await call_llm(llm_req["messages"])
    return {
        "answer": answer,
        "mode": llm_req["mode"],
        "used_attachments": llm_req["attachments_used"],
    }
