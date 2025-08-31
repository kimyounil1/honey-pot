# /API/app/services/state_update.py
import logging
from typing import Optional, List

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
    disease_code: Optional[str] = None,
    product_id: Optional[str] = None,
):
    """
    백그라운드에서 실행되는 어시스턴트 메시지 처리 파이프라인
    (기존 로직은 유지하면서, 아래 두 가지만 보강)
      1) 분류 결과(mode)를 사용자 마지막 메시지에도 type으로 반영
      2) REFUND일 때 타임라인/알림 생성을 즉시 트리거(선택)
    """
    async with AsyncSessionLocal() as db:
        try:
            # Stage 준비 (classifying → analyzing → searching → building)
            kwargs = dict(
                db=db,
                user_id=user_id,
                text=text,
                attachment_ids=attachment_ids or [],
                chat_id=chat_id,
                product_id=product_id,
            )
            if disease_code:
                kwargs["disease_code"] = disease_code

            prep = await stage.prepare_llm_request(**kwargs)
            await db.commit()

            mode = prep["mode"]
            mode_str = getattr(mode, "name", str(mode))  # e.g. "REFUND"
            attachments_used = prep.get("attachments_used", [])
            static_answer = prep.get("static_answer") or ""

            # -------------------------------
            # (A) type 업데이트(기존): 어시스턴트 placeholder 메시지에 type 세팅
            # -------------------------------
            await chatCRUD.update_message_type(db, chat_id, mode_str)

            # -------------------------------
            # (B) ✅ 추가: 사용자 마지막 메시지에도 같은 type 반영
            #     → 스캐너가 user 메시지를 집계할 수 있게 됨
            # -------------------------------
            try:
                await chatCRUD.update_last_user_message_type(db, chat_id, mode_str)
                # 필요시 빠른 반영
                await db.commit()
                logger.info("[BG] Tagged last user message with type=%s (chat=%s)", mode_str, chat_id)
            except Exception:
                logger.exception("[BG] failed to tag last user message type (chat=%s)", chat_id)

            # -------------------------------
            # (C) 옵션: REFUND이면 타임라인 즉시 스캔 트리거
            #     스케줄러를 기다리지 않고 팝업을 바로 띄우고 싶을 때 유용
            #     scan_and_build_timeline_for_chat 이 없으면 조용히 패스
            # -------------------------------
            try:
                if str(mode_str).upper() == "REFUND":
                    try:
                        from app.services.scheduler import scan_and_build_timeline_for_chat  # type: ignore
                        await scan_and_build_timeline_for_chat(chat_id=chat_id, user_id=user_id)
                        logger.info("[BG] timeline scan triggered for chat=%s user=%s", chat_id, user_id)
                    except Exception:
                        # helper가 없거나 에러면 전체 스캔으로 폴백(무거우면 주석 처리 가능)
                        try:
                            from app.services.scheduler import scan_and_build_timeline  # type: ignore
                            await scan_and_build_timeline()
                            logger.info("[BG] full timeline scan fallback executed")
                        except Exception:
                            logger.exception("[BG] timeline build trigger failed (chat=%s)", chat_id)
            except Exception:
                # 어떤 이유로든 트리거 실패해도 본 파이프라인은 진행
                logger.exception("[BG] timeline trigger outer failed")

            # Fallback (정적 응답)
            if static_answer:
                answer = static_answer.get("answer") if isinstance(static_answer, dict) else static_answer
                await chatCRUD.update_message_state(db, chat_id, "done")
                await chatCRUD.update_message_content(db, chat_id, answer)
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
