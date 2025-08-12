# app/services/startend.py
from typing import List, Dict, Optional
from app.services.common import Mode, decide_flow_with_llm
from app.services import terms_analysis, refund_calc, recommend, general_question, fallback

def classify_with_llm(user_text: str, attachment_ids: Optional[List[str]] = None):
    decision = decide_flow_with_llm(user_text, attachment_ids or [])
    print(f"[STARTEND] classify -> {decision.flow} | text='{user_text[:80]}'")
    return decision

def build_messages(mode: Mode, user_text: str, context: str = "", first_message: bool = False) -> List[Dict[str, str]]:
    if mode == Mode.TERMS:
        msgs = terms_analysis.build_messages(user_text, context)
    elif mode == Mode.REFUND:
        msgs = refund_calc.build_messages(user_text, context)
    elif mode == Mode.RECO:
        msgs = recommend.build_messages(user_text, context)
    elif mode == Mode.GENERAL:
        msgs = general_question.build_messages(user_text, context)
    else:
        msgs = fallback.build_messages(user_text, context)

    print(f"[STARTEND] built messages for mode={mode} (context_len={len(context)}, messages_len={len(msgs)})")
    return msgs
