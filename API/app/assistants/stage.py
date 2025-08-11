from typing import Sequence, TypedDict, List, Dict
from app.assistants.common import Mode
from app.assistants import startend
from app.rag.retriever import retrieve

class LLMRequest(TypedDict):
    mode: Mode
    messages: List[Dict[str, str]]
    attachments_used: List[str]

async def prepare_llm_request(
    user_id: str,
    text: str,
    first_message: bool = False,
    attachment_ids: Sequence[str] | None = None,
) -> LLMRequest:
    mode = startend.classify(text)
    context = await retrieve(
        mode, user_id=user_id, query=text,
        attachment_ids=list(attachment_ids or []), k=6
    )
    messages = startend.build_messages(
        user_text=text, context=context, first_message=first_message
    )
    return {
        "mode": mode,
        "messages": messages,
        "attachments_used": list(attachment_ids or []),
    }
