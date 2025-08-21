# /API/app/routers/chat.py
import logging
from fastapi import APIRouter, Depends, Form, HTTPException, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

import json
import asyncio
from datetime import datetime
from app.services.common import Mode
from app.services import stage
from app.services import llm_gateway
from app.schemas import userSchema, chatSchema

from app.crud import chatCRUD
from app.auth import deps
from app.database import get_db, AsyncSessionLocal
from app.services.state_update import process_assistant_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(deps.get_current_user)])

class AskBody(BaseModel):
    # user_id: int
    role: str = "user"
    text: str
    attachment_ids: Optional[List[str]] = None  # 업로드된 file_id 배열
    chat_id: Optional[int] = None
    disease_code: Optional[str] = None
    product_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def as_form(
            cls,
            text: str = Form(...),
            attachment_ids: Optional[str] = Form(None),
            chat_id: Optional[str] = Form(None),
            disease_code: Optional[str] = Form(None),
            product_id: Optional[str] = Form(None),
    ) -> "AskBody":
        ids = json.loads(attachment_ids) if attachment_ids else None

        parsed_chat_id: Optional[int] = None
        if chat_id:
            try:
                parsed_chat_id = int(chat_id)
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid chat_id")

        return cls(
            text=text,
            attachment_ids=ids,
            chat_id=parsed_chat_id,
            disease_code=disease_code,
            product_id=product_id,
        )

###### 되도록 지우지 말아주세요 ######
@router.get("/chats", response_model=List[chatSchema.Chat])
async def read_user_chats(
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get user_id from the token to fetch chats for the current user
    user_chats = await chatCRUD.get_chat_list(db=db, user_id=current_user.user_id)
    
    if not user_chats:
        # Return an empty list if the user has no chats, instead of a 404 error
        return []
    return user_chats

@router.get("/{chat_id}/messages", response_model=List[chatSchema.Message])
async def read_chat_messages(
    chat_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    chat = await chatCRUD.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="no chat")
    elif (chat.user_id != current_user.user_id and current_user.user_id != 1):
        raise HTTPException(status_code=403, detail="You do not have permission to access this chat.")
    messages = await chatCRUD.get_messages(db, chat_id)
    return messages

TIMEOUT_SECONDS = 1.0
@router.get("/{chat_id}/messageState", response_model=chatSchema.MessageStateResponse)
async def read_message_state(chat_id: int, current_user: userSchema.UserRead = Depends(deps.get_current_user)):
    try:
        # ✅ 별도 세션(짧게 열고 빨리 닫기). 기존 db 세션 대신 사용.
        async with AsyncSessionLocal() as s:
            # Postgres 기준: 읽기 전용 + 1s 쿼리 타임아웃

            await s.execute(text("SET LOCAL statement_timeout = 1000"))
            await s.execute(text("SET TRANSACTION READ ONLY"))

            print("########### get_char 호출시작 ###########")
            chat = await asyncio.wait_for(chatCRUD.get_chat(s, chat_id), timeout=TIMEOUT_SECONDS)
            print("########### get_char 호출종료 ###########")
            if not chat:
                raise HTTPException(status_code=404, detail="no chat")
            if (chat.user_id != current_user.user_id and current_user.user_id != 1):
                raise HTTPException(status_code=403, detail="You do not have permission to access this chat.")

            print("########### get_last_message 호출시작 ###########")
            last_message = await asyncio.wait_for(chatCRUD.get_last_message(s, chat_id), timeout=TIMEOUT_SECONDS)
            print("########### get_last_message 호출종료 ###########")

        return chatSchema.MessageStateResponse(state=last_message.state)

    except asyncio.TimeoutError:
        # 폴링이므로 504로 빠르게 실패 → 클라가 0.3s 후 재시도
        raise HTTPException(status_code=504, detail="messageState timed out (>1s)")
    
@router.get("/{chat_id}/messageState/complete")
async def update_message_state(chat_id: int, db: AsyncSession = Depends(get_db)):
    try:
        # ✅ 별도 세션(짧게 열고 빨리 닫기). 기존 db 세션 대신 사용.
            await chatCRUD.update_message_state(db, chat_id, "complete")
            await db.commit()
    except Exception as e:
        pass
    return chatSchema.MessageStateResponse(state="complete")


@router.post("/ask")
async def ask(
    background_tasks: BackgroundTasks,
    form_data: AskBody = Depends(AskBody.as_form),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    body = form_data
    try:
        # 1) 채팅 시작 시 create_chat
        if not body.chat_id:
            newChat = await chatCRUD.create_chat(
                db,
                chatSchema.NewChat(
                    user_id=current_user.user_id,
                    title=body.text[:30],
                ),
            )
            chat_id = newChat.id
        else:
            chat_id = body.chat_id

        # 2) user 메시지 즉시 저장
        await chatCRUD.create_message(
            db,
            chatSchema.Message(
                chat_id=chat_id,
                role="user",
                content=body.text,
                type="general",
                state="done",
            ),
        )

        # 3) 비어있는 assistant 메시지(commencing) 저장
        await chatCRUD.create_message(
            db,
            chatSchema.Message(
                chat_id=chat_id,
                role="assistant",
                content="",
                type="",
                state="commencing",
            )
        )
        await db.commit()

        # 4) 백그라운드 태스크로 LLM 처리 예약
        background_tasks.add_task(
            process_assistant_message,
            chat_id,
            current_user.user_id,
            body.text,
            body.attachment_ids,
            body.disease_code,
            body.product_id,
        )
        # 5) 즉시 응답 반환
        return {
            "ok": True,
            "chat_id": chat_id,
            "message": "Assistant message processing started"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Server error in /chat/ask: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")