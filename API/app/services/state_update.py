# /API/app/services/state_update.py
import logging
from typing import Optional, List
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import stage, llm_gateway
from app.schemas import chatSchema
from app.crud import chatCRUD
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

async def process_assistant_message(
    chat_id: int,
    user_id: int,
    text: str,
    attachment_ids: Optional[List[str]],
    file: Optional[UploadFile],
):
    """
    백그라운드에서 실행되는 어시스턴트 메시지 처리 파이프라인
    """
    async with AsyncSessionLocal() as db:
        try:
            # Stage 준비 (classifying → analyzing → searching → building)
            prep = await stage.prepare_llm_request(
                db=db,
                user_id=user_id,
                text=text,
                attachment_ids=attachment_ids or [],
                file=file,
                chat_id=chat_id,
            )
            await db.commit()

            mode = prep["mode"]
            mode_str = getattr(mode, "name", str(mode))
            attachments_used = prep.get("attachments_used", [])
            static_answer = prep.get("static_answer") or ""

            # type 업데이트
            await chatCRUD.update_message_type(db, chat_id, mode_str)

            # Fallback (정적 응답)
            if static_answer:
                answer = static_answer.get("answer") if isinstance(static_answer, dict) else static_answer
                await chatCRUD.create_message(
                    db,
                    chatSchema.Message(
                        chat_id=chat_id,
                        role="assistant",
                        content=answer,
                        type=mode_str,
                        state="done",
                    ),
                )
                await db.commit()
                logger.info("[BG] FALLBACK complete: chat=%s mode=%s", chat_id, mode_str)
                return

            # LLM 호출
            messages = prep["messages"]
            logger.info("[BG] Calling LLM. mode=%s, messages_len=%d", mode_str, len(messages))
            answer = await llm_gateway.call_llm(messages)

            # content/state 업데이트
            await chatCRUD.update_message_content(db, chat_id, answer)
            await chatCRUD.update_message_state(db, chat_id, "done")
            await db.commit()

            logger.info("[BG] LLM done: chat=%s mode=%s", chat_id, mode_str)

        except Exception as e:
            logger.exception("[BG] Error in assistant message processing: %s", e)
            try:
                await chatCRUD.update_message_state(db, chat_id, "failed")
                await db.commit()
            except Exception:
                pass
