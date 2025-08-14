# app/routers/chat.py
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional

import json
from app.services.common import Mode
from app.services.ocr import ocr_file
from app.services.stage import prepare_llm_request
from app.services.llm_gateway import call_llm

from app.schemas import userSchema, chatSchema
# from app.schemas.chatSchema import NewChat, Message

from app.crud import chatCRUD
from app.models import userModel
from app.auth import deps
from app.database import get_db

router = APIRouter(prefix="/chat", tags=["chat"])

class AskBody(BaseModel):
    # user_id: int
    role: str = "user"
    text: str
    first_message: bool = False
    attachment_ids: Optional[List[str]] = None  # 업로드된 file_id 배열
    chat_id: Optional[int] = None

    @classmethod
    def as_form(
            cls,
            text: str = Form(...),
            first_message: bool = Form(False),
            attachment_ids: Optional[str] = Form(None),
            chat_id: Optional[str] = Form(None)
    ) -> "AskBody":
        ids = json.loads(attachment_ids) if attachment_ids else None
        parsed_chat_id: Optional[int] = None
        if chat_id:
            try:
                parsed_chat_id = int(chat_id)
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid chat_id")
        return cls(text=text, first_message=first_message, attachment_ids=ids, chat_id=parsed_chat_id)

@router.get("/{chat_id}/messages", response_model=List[chatSchema.Message])
async def read_chat_messages(
    chat_id: int, 
    db: AsyncSession = Depends(get_db), 
    current_user: userModel.User = Depends(deps.get_current_user)
):
    messages = await chatCRUD.get_messages(db=db, chat_id=chat_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Chat not found or no messages")
    return messages

@router.post("/ask")
async def ask(
    body: AskBody = Depends(AskBody.as_form),
    file: UploadFile | None = File(None),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # print(f"[ROUTER] /chat/ask user_id={body.user_id} first={body.first_message} text='{body.text[:80]}'")
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
    if file and llm_req["mode"] in (Mode.TERMS, Mode.REFUND):
        ocr_text = await ocr_file(file)
        print(f"[ROUTER] OCR extracted {len(ocr_text)} chars")
        # TODO: OpenSearch ingest pipeline integration

    # 3단계: LLM 호출
    answer = await call_llm(llm_req["messages"])
    mode = llm_req["mode"]
    attachments_used = llm_req["attachments_used"]  

    # 채팅의 시작일 경우 create_chat 호출
    if body.first_message:
        newChat = await chatCRUD.create_chat(
            db,
            chatSchema.NewChat(
                user_id = current_user.user_id,
                title=body.text[:30],
                type=mode
            )
        )
        # 채팅의 시작일 경우 chat_id를 받아옴
        chat_id = newChat.id
    else:
        if not body.chat_id:
        # 기존 대화인데 chat_id가 없는 경우, 클라이언트 오류이므로 예외 처리
            raise HTTPException(status_code=400, detail="기존 대화에는 chat_id가 반드시 필요합니다.")
        chat_id = body.chat_id

    await chatCRUD.create_message(
        db,
        chatSchema.Message(
            chat_id = chat_id,
            role="user",
            content=body.text
        )
    )
    await chatCRUD.create_message(
        db,
        chatSchema.Message(
            chat_id = chat_id,
            role="assistant",
            content=answer
        )
    )

    # 완료 로그
    print(f"[ROUTER] LLM done. mode={mode}, used_attachments={attachments_used}")

    return {
        "answer": answer,
        "mode": mode,
        "used_attachments": attachments_used,
        "chat_id": chat_id
    }
