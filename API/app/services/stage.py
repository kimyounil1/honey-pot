import logging
from typing import Any, Dict, List, Optional, Tuple

from fastapi import UploadFile

from app.services import fallback
from app.services.startend import Mode, classify_with_llm, build_messages
from app.rag.retriever import retrieve, policy_db_lookup as _policy_db_lookup
from app.services.ocr import ocr_file
from app.services.ingest import ingest_policy
from app.schemas import userSchema

logger = logging.getLogger(__name__)


async def _classify(user_text: str, attachment_ids: Optional[List[str]]) -> Tuple[Mode, Dict[str, Any], bool]:
    decision = classify_with_llm(user_text, attachment_ids or [])
    mode: Mode = decision.flow
    entities: Dict[str, Any] = decision.entities or {}
    use_retrieval: bool = bool(getattr(decision, "use_retrieval", False))
    return mode, entities, use_retrieval


async def prepare_llm_request(
    *,
    user_id: int | str,
    text: str,
    attachment_ids: Optional[List[str]] = None,
    file: UploadFile | None = None,
    current_user: userSchema.UserRead | None = None,
) -> Dict[str, Any]:
    att_ids = list(attachment_ids or [])

    # 1) 분류 (동기 classify_with_llm에 맞춰 래퍼 사용)
    mode, entities, use_retrieval = await _classify(text, att_ids)
    logger.info("[STAGE] classify -> mode=%s | text='%s'", getattr(mode, "name", str(mode)), text[:80])

    # 2) FALLBACK은 정적 응답
    if mode == Mode.FALLBACK:
        static = fallback.static_answer(text)
        logger.info("[STAGE] ready: mode=FALLBACK, ctx_len=0, messages_len=0 (static)")
        return {
            "mode": mode,
            "messages": [],
            "attachments_used": att_ids,
            "static_answer": static,
        }

    # 3) OCR (TERMS/REFUND + 파일)
    if file and mode in (Mode.TERMS, Mode.REFUND):
        try:
            ocr_text = await ocr_file(file)
            logger.info("[STAGE] OCR extracted %s chars", len(ocr_text))
            meta = {
                "policy_id": f"{(current_user.user_id if current_user else user_id)}-{file.filename}",
                "uploader_id": current_user.user_id if current_user else user_id,
                "filename": file.filename,
            }
            try:
                indexed = await ingest_policy(ocr_text, meta)
                logger.info("[STAGE] OpenSearch indexed %s docs policy_id=%s", indexed, meta["policy_id"])
            except Exception as ingest_err:
                logger.warning("[STAGE] Ingest failed: %s", ingest_err)
        except Exception as e:
            logger.warning("[STAGE] OCR failed: %s", e)

    # 4) DB-우선 조회
    db_block = await _policy_db_lookup(mode=mode, entities=entities, user_text=text)
    db_hit = bool((db_block or "").strip())

    # 5) (필요 시) RAG 보조
    rag_block = ""
    if use_retrieval and not db_hit and mode in (Mode.TERMS, Mode.REFUND, Mode.RECOMMEND):
        rag_block = await retrieve(mode=mode, user_id=str(user_id), query=text, attachment_ids=att_ids)

    # 6) 메시지 빌드 (context 하나로 합치기)
    context = "\n\n".join([s for s in [db_block, rag_block] if s]).strip()
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
        "attachments_used": att_ids,
        "static_answer": "",
    }