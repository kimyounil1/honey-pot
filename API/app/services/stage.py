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

# --- DB 우선 조회 훅 (실제 연결 시 내부 구현만 교체) ---
async def _policy_db_lookup(mode: Mode, entities: Dict[str, str], user_text: str) -> str:
    """
    약관전문/사내DB에서 정합 블록을 만들어 반환. 없으면 "".
    포맷 예:
    [DB]
    보험사: {insurer} / 상품: {product}({version})
    - 보장대상: ...
    - 한도/공제: ...
    - 면책/제외: ...
    - 청구요건: ...
    🔎 출처: {clause_id} / {page_ref}
    """
    # TODO: 실제 DB 연동
    return ""

async def prepare_llm_request(
    user_id: int,
    text: str,
    # first_message: bool = False,
    attachment_ids: Sequence[str] | None = None,
) -> LLMRequest:
    print(f"[STAGE] prepare: user_id={user_id}, attachments={list(attachment_ids or [])}")

    # 1) LLM 분류 + 서버 정책(스위치) 반영
    decision = startend.classify_with_llm(text, list(attachment_ids or []))
    mode = decision.flow
    use_retrieval: bool = bool(getattr(decision, "use_retrieval", False))
    entities: Dict[str, str] = getattr(decision, "entities", {}) or {}

    # 2) FALLBACK은 정적 응답
    if mode == Mode.FALLBACK:
        static = fallback.static_answer(text)
        print(f"[STAGE] ready: mode=FALLBACK, ctx_len=0, messages_len=0 (static)")
        return {
            "mode": mode,
            "messages": [],
            "attachments_used": list(attachment_ids or []),
            "static_answer": static,
        }

    # 3) DB-우선 조회
    db_block = await _policy_db_lookup(mode=mode, entities=entities, user_text=text)
    db_hit = bool((db_block or "").strip())

    # 4) (필요 시) RAG 보조 — GENERAL은 금지, RECOMMEND는 요청 시 허용
    rag_block = ""
    rag_hit = False
    if use_retrieval and not db_hit and mode in (Mode.TERMS, Mode.REFUND, Mode.RECOMMEND):
        rag_block = await retrieve(
            mode, user_id=user_id, query=text,
            attachment_ids=list(attachment_ids or []), k=6
        )
        rag_hit = bool((rag_block or "").strip())

    # 5) 컨텍스트 합성
    context = "\n\n".join([blk for blk in [db_block, rag_block] if (blk or "").strip()])

    # 6) 모드별 템플릿 메시지
    messages = startend.build_messages(
        # mode=mode, user_text=text, context=context, first_message=first_message
        mode=mode, user_text=text, context=context
    )

    print(f"[STAGE] ready: mode={mode}, db_hit={db_hit}, rag_hit={rag_hit}, ctx_len={len(context)}, messages_len={len(messages)})")
    return {
        "mode": mode,
        "messages": messages,
        "attachments_used": list(attachment_ids or []),
    }
