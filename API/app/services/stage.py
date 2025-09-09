import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import fallback, vector_db
from app.services.startend import Mode, classify_with_llm, build_messages
from app.rag.retriever import retrieve, policy_db_lookup as _policy_db_lookup
from app.crud import chatCRUD, nonBenefitCRUD

logger = logging.getLogger(__name__)


async def _classify(user_text: str, prev_chats: Optional[List[str]], disease_code: Optional[str], product_id: Optional[str]) -> Tuple[Mode, Dict[str, Any], bool, str, str]:
    # decision = classify_with_llm(user_text, attachment_ids or [])
    """Run the classification LLM in a thread so it doesn't block the event loop."""
    decision = await asyncio.to_thread(classify_with_llm, user_text, prev_chats or [], disease_code, product_id)
    mode: Mode = decision.flow
    entities: Dict[str, Any] = decision.entities or {}
    use_retrieval: bool = bool(getattr(decision, "use_retrieval", False))
    text = decision.text
    ctx = decision.ctx
    return mode, entities, use_retrieval, text, ctx


async def prepare_llm_request(
    *,
    db: AsyncSession,
    user_id: int | str,
    text: str,
    prev_chats: Optional[List[str]] = None,
    chat_id: int,
    disease_code: str | None = None,
    product_id: str | None = None,
) -> Dict[str, Any]:
    pre_chat = list(prev_chats or [])

    # 1) 분류 (동기 classify_with_llm에 맞춰 래퍼 사용)
    # 메세지 state 갱신 (classifying)
    try:
        await chatCRUD.update_message_state(db, chat_id, "classifying")
    except Exception as e:
        await chatCRUD.update_message_state(db, chat_id, "failed")
        raise
    mode, entities, use_retrieval, text, ctx = await _classify(text, pre_chat, disease_code, product_id)
    logger.info(
        "[STAGE] classify -> mode=%s | text='%s'",
        getattr(mode, "name", str(mode)),
        text[:80],
    )
    code_for_check = (disease_code or entities.get("icd10_candidate") or "").strip().upper()

    # 2) FALLBACK은 정적 응답
    if mode == Mode.FALLBACK:
        static = fallback.static_answer(text)
        logger.info("[STAGE] ready: mode=FALLBACK, ctx_len=0, messages_len=0 (static)")
        return {
            "mode": mode,
            "messages": [],
            "attachments_used": pre_chat,
            "static_answer": static,
        }

    # 3) DB-우선 조회
    # 메세지 state 갱신 (searching)
    try:
        await chatCRUD.update_message_state(db, chat_id, "searching")
    except Exception as e:
        await chatCRUD.update_message_state(db, chat_id, "failed")
        raise
    db_block = ""
    if mode in (Mode.REFUND, Mode.RECOMMEND):
        db_block = await _policy_db_lookup(
            mode=mode, entities=entities, user_text=text, user_id=user_id
        )
    # 4) (필요 시) RAG 보조
    rag_parts: List[str] = []
    # REFUND은 항상 RAG를 수행(개인 업로드/약관을 광범위하게 활용)
    # TERMS는 분류기 제안(use_retrieval)이 on일 때만 수행
    run_retrieval = (mode == Mode.REFUND) or (use_retrieval and mode == Mode.TERMS)
    if run_retrieval:
        os_block = await retrieve(
            mode=mode,
            user_id=str(user_id),
            query=text,
            prev_chats=pre_chat,
            product_id=product_id,
            limit=20,
            fallback_to_global=True,
            db_context=db_block,
        )
        if os_block:
            rag_parts.append(os_block)
    rag_block = "\n\n".join([s for s in rag_parts if s])

    benefit_ctx = ""
    if mode == Mode.REFUND:
        if not code_for_check:
            m = re.search(r"\b([A-Za-z][0-9]{2,3}[A-Za-z0-9]*)\b", text or "")
            if m:
                code_for_check = m.group(1).upper()
        if code_for_check:
            # 기본 줄은 항상 넣어 코드 존재를 LLM이 확실히 인지하도록 함
            benefit_lines = [f"[ICD-10]", f"{code_for_check}"]
            try:
                item = await nonBenefitCRUD.get_by_code(db, code_for_check)
                if item is not None:
                    # DB에 있으면 급여/비급여 힌트 추가
                    if item:
                        benefit_lines.append(" (비급여)")
                    else:
                        benefit_lines.append(" (급여)")
            except Exception as e:
                logger.warning("[STAGE] nonBenefit lookup failed: %s", e)
            benefit_ctx = "\n".join([benefit_lines[0], "".join(benefit_lines[1:])])

    # 5) 메시지 빌드 (context 하나로 합치기)
    # 메세지 state 갱신 (building)
    try:
        await chatCRUD.update_message_state(db, chat_id, "building")
    except Exception as e:
        await chatCRUD.update_message_state(db, chat_id, "failed")
        raise
    context = "\n\n".join([s for s in [db_block, rag_block, benefit_ctx, ctx] if s]).strip()

    # 첨부 힌트 주입: 이미지 업로드로 질병코드가 전달된 경우(제품 PDF 아님)
    try:
        attach_image_hint = (mode == Mode.REFUND) and (disease_code is not None) and not product_id
    except Exception:
        attach_image_hint = False
    if attach_image_hint:
        # refund_calc.build_messages가 이를 감지하여 [ATTACHMENT] 메타를 정확히 세팅할 수 있도록 컨텍스트에 힌트를 추가
        attach_block = "[ATTACHMENT]\nimage_uploaded: true"
        context = attach_block + ("\n\n" + context if context else "")
    messages = build_messages(mode=mode, user_text=text, context=context)

    logger.info(
        "[STAGE] ready: mode=%s, ctx_len=%d, messages_len=%d",
        getattr(mode, "name", str(mode)),
        len(context),
        len(messages),
    )
    return {
        "mode": mode,
        "messages": messages,
        "prev_chats": pre_chat,
        "static_answer": "",
    }
