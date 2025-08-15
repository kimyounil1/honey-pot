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
from app.services.ingest import ingest_policy
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

    # 2단계: messages 준비 (분류→가드룰→DB우선→조건부RAG)
    llm_req = await prepare_llm_request(
        user_id=current_user.user_id,
        text=body.text,
        # first_message=body.first_message,
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

    # 파일 업로드가 있고, 약관/환급 모드면 OCR 인제스트(로그용)
    if file and llm_req["mode"] in (Mode.TERMS, Mode.REFUND):
        try:
            ocr_text = await ocr_file(file)
            print(f"[ROUTER] OCR extracted {len(ocr_text)} chars")
            meta = {
                "policy_id": f"{current_user.user_id}-{file.filename}",
                "uploader_id": current_user.user_id,
                "filename": file.filename,
            }
            try:
                indexed = await ingest_policy(ocr_text, meta)
                print(f"[ROUTER] OpenSearch indexed {indexed} docs policy_id={meta['policy_id']}")
            except Exception as ingest_err:
                print(f"[ROUTER] Ingest failed: {ingest_err}")

        except Exception as e:
            print(f"[ROUTER] OCR failed: {e}")

    # 3단계: LLM 호출(최종 Answerer)
    answer = await call_llm(llm_req["messages"])
    mode = llm_req["mode"]
    attachments_used = llm_req["attachments_used"]  

    # 채팅의 시작일 경우 create_chat 호출
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
