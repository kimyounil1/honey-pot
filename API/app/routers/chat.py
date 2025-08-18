# app/routers/chat.py
import logging
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

import json
from app.services.common import Mode
from app.services import stage
from app.services import llm_gateway
from app.schemas import userSchema, chatSchema

from app.crud import chatCRUD
from app.models import userModel
from app.auth import deps
from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(deps.get_current_user)])

class AskBody(BaseModel):
    # user_id: int
    role: str = "user"
    text: str
    attachment_ids: Optional[List[str]] = None  # 업로드된 file_id 배열
    chat_id: Optional[int] = None
    file: Optional[UploadFile] = None

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def as_form(
            cls,
            text: str = Form(...),
            attachment_ids: Optional[str] = Form(None),
            chat_id: Optional[str] = Form(None),
            file: Optional[UploadFile] = File(None)
    ) -> "AskBody":
        ids = json.loads(attachment_ids) if attachment_ids else None

        parsed_chat_id: Optional[int] = None
        if chat_id:
            try:
                parsed_chat_id = int(chat_id)
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid chat_id")
        valid_file = file if file and file.filename else None

        return cls(text=text, attachment_ids=ids, chat_id=parsed_chat_id, file=valid_file)

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
    form_data: AskBody = Depends(AskBody.as_form),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    body = form_data
    file = form_data.file
    try:
        # 1단계: Stage에서 준비(폴백→OCR→DB→RAG→메시지)
        prep = await stage.prepare_llm_request(
            user_id=current_user.user_id,
            text=body.text,
            attachment_ids=body.attachment_ids or [],
            file=file,  # - OCR은 stage에서 처리
        )

        mode = prep["mode"]
        mode_str = getattr(mode, "name", str(mode))   # Enum 대응
        attachments_used = prep.get("attachments_used", [])
        static_answer = prep.get("static_answer") or ""

        # 2-1단계: 채팅의 시작일 경우 create_chat 호출
        if not body.chat_id:
            newChat = await chatCRUD.create_chat(
                db,
                chatSchema.NewChat(
                    user_id = current_user.user_id,
                    title=body.text[:30],
                    type=mode  # 팀 스키마와 일치(필요시 .lower()로 통일)
                )
            )
            # 채팅의 시작일 경우 chat_id를 받아옴
            chat_id = newChat.id
        else:
            chat_id = body.chat_id

        # 2-2단계: 사용자 메세지는 항상 저장
        await chatCRUD.create_message(
            db,
            chatSchema.Message(
                chat_id = chat_id,
                role="user",
                content=body.text
            )
        )

        # 3단계: 폴백이면 정적 답 저장 후 즉시 반환
        if static_answer:
            answer = static_answer
            await chatCRUD.create_message(
                db,
                chatSchema.Message(
                    chat_id=chat_id,
                    role="assistant",
                    content=answer,
                ),
            )
            logger.info("[ROUTER] FALLBACK. mode=%s, used_attachments=%s", mode_str, attachments_used)
            return {
                "ok": True,
                "answer": answer,
                "mode": mode_str,
                "used_attachments": attachments_used,
                "chat_id": chat_id,
            }

        # 4-1단계: LLM 호출(폴백이 아닌 경우) 
        messages = prep["messages"]
        logger.info("[ROUTER] Calling LLM. mode=%s, messages_len=%d", mode_str, len(messages))
        answer = await llm_gateway.call_llm(messages)

        # 4-2단계: 어시스턴트 메세지 저장(폴백이 아닌 경우)
        await chatCRUD.create_message(
            db,
            chatSchema.Message(
                chat_id = chat_id,
                role="assistant",
                content=answer
            )
        )

        logger.info("[ROUTER] LLM done. mode=%s, used_attachments=%s", mode_str, attachments_used)
        return {
            "ok": True,
            "answer": answer,
            "mode": mode_str,
            "used_attachments": attachments_used,
            "chat_id": chat_id,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Server error in /chat/ask: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")