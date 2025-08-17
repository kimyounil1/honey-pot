import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import deps
from app.schemas import userSchema
from app.services import llm_gateway
from app.services import stage

from app.database import get_db
from app.crud import chatCRUD
from app.schemas import chatSchema

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


# --- 요청 바디(JSON/FORM 공통) ---
class AskBody(BaseModel):
    text: str
    first_message: Optional[bool] = False
    attachment_ids: Optional[List[str]] = None
    chat_id: Optional[int] = None  # 새 채팅이면 None


def _coerce_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in ("1", "true", "on", "yes")


@router.post("/ask")
async def ask(
    request: Request,
    file: UploadFile | None = File(None),  # 파일은 multipart/form-data로 올 때만 존재
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    """
    - JSON이면 request.json()에서 파싱, multipart/form이면 form 파싱 + file 주입
    - stage.prepare_llm_request()가 FALLBACK/OCR/DB/RAG/메시지 빌드를 전부 준비
    - 여기서는 저장 + (폴백이면 즉시 반환) or (LLM 호출 후 저장) 만 담당
    """
    try:
        # --- 1) 입력 파싱 ---
        content_type = (request.headers.get("content-type") or "").lower()
        if content_type.startswith("application/json"):
            payload = await request.json()
            body = AskBody(**payload)
        else:
            # multipart/form-data 또는 x-www-form-urlencoded
            form = await request.form()
            text = (form.get("text") or "").strip()
            first_message = _coerce_bool(form.get("first_message"))
            raw_ids = form.get("attachment_ids")
            if isinstance(raw_ids, list):
                attachment_ids = raw_ids
            elif isinstance(raw_ids, str) and raw_ids.strip():
                attachment_ids = [s.strip() for s in raw_ids.split(",")]
            else:
                attachment_ids = None
            chat_id = form.get("chat_id")
            if chat_id is not None:
                try:
                    chat_id = int(chat_id)
                except Exception:
                    chat_id = None
            body = AskBody(
                text=text,
                first_message=first_message,
                attachment_ids=attachment_ids,
                chat_id=chat_id,
            )

        # --- 2) Stage에서 준비(폴백→OCR→DB→RAG→메시지) ---
        prep = await stage.prepare_llm_request(
            user_id=current_user.user_id,
            text=body.text,
            attachment_ids=body.attachment_ids or [],
            file=file,                    # ⬅ OCR은 stage에서 처리
            current_user=current_user,
        )

        mode = prep["mode"]
        mode_str = getattr(mode, "name", str(mode))   # Enum 대응
        attachments_used = prep.get("attachments_used", [])
        static_answer = prep.get("static_answer") or ""

        # --- 3) chat_id 확정(없으면 생성) ---
        if not body.chat_id:
            new_chat = await chatCRUD.create_chat(
                db,
                chatSchema.NewChat(
                    user_id=current_user.user_id,
                    title=body.text[:30],
                    type=mode_str,  # Enum -> str로 저장
                ),
            )
            chat_id = new_chat.id
        else:
            chat_id = body.chat_id

        # --- 4) 사용자 메시지 저장(항상) ---
        await chatCRUD.create_message(
            db,
            chatSchema.Message(
                chat_id=chat_id,
                role="user",
                content=body.text,
            ),
        )

        # --- 5) 폴백이면 정적 답 저장 후 즉시 반환 ---
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

        # --- 6) LLM 호출(폴백이 아닌 경우) ---
        messages = prep["messages"]
        logger.info("[ROUTER] Calling LLM. mode=%s, messages_len=%d", mode_str, len(messages))
        answer = await llm_gateway.call_llm(messages)

        # --- 7) 어시스턴트 메시지 저장 ---
        await chatCRUD.create_message(
            db,
            chatSchema.Message(
                chat_id=chat_id,
                role="assistant",
                content=answer,
            ),
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
