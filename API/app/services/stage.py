# app/services/stage.py
from typing import Sequence, TypedDict, List, Dict, Optional
from app.services.common import Mode
from app.services import startend, fallback
from app.rag.retriever import retrieve

class LLMRequest(TypedDict, total=False):
    mode: Mode
    messages: List[Dict[str, str]]
    attachments_used: List[str]
    static_answer: Dict[str, str]

async def prepare_llm_request(
    user_id: int,
    text: str,
    # first_message: bool = False,
    attachment_ids: Sequence[str] | None = None,
) -> LLMRequest:
    # print(f"[STAGE] prepare: user_id={user_id}, first={first_message}, attachments={list(attachment_ids or [])}")
    print(f"[STAGE] prepare: user_id={user_id}, attachments={list(attachment_ids or [])}")

    decision = startend.classify_with_llm(text, list(attachment_ids or []))
    mode = decision.flow

    # FALLBACK은 LLM 호출 없이 정적 응답 반환
    if mode == Mode.FALLBACK:
        static = fallback.static_answer(text)
        print(f"[STAGE] ready: mode=FALLBACK, ctx_len=0, messages_len=0 (static)")
        return {
            "mode": mode,
            "messages": [],
            "attachments_used": list(attachment_ids or []),
            "static_answer": static,
        }

    # RAG/TERMS/REFUND/RECO/GENERAL일 때 컨텍스트 수집
    context = await retrieve(
        mode, user_id=user_id, query=text,
        attachment_ids=list(attachment_ids or []), k=6
    )

    messages = startend.build_messages(
        # mode=mode, user_text=text, context=context, first_message=first_message
        mode=mode, user_text=text, context=context
    )

    print(f"[STAGE] ready: mode={mode}, ctx_len={len(context)}, messages_len={len(messages)})")
    return {
        "mode": mode,
        "messages": messages,
        "attachments_used": list(attachment_ids or []),
    }
