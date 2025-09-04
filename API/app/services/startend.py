# app/services/startend.py
from __future__ import annotations
from typing import List, Dict, Optional

from app.services.common import Mode, decide_flow_with_llm
from app.services import terms_analysis, refund_calc, recommend, general_question, fallback

def classify_with_llm(user_text: str, prev_chats: Optional[List[str]], disease_code: Optional[str], product_id: Optional[str]):
    decision = decide_flow_with_llm(user_text, prev_chats or [], disease_code, product_id)
    print(f"[STARTEND] classify -> {decision.flow} | text='{(user_text or '')[:80]}'")
    return decision

# def build_messages(mode: Mode, user_text: str, context: str = "", first_message: bool = False) -> List[Dict[str, str]]:
def build_messages(mode: Mode, user_text: str, context: str = "") -> List[Dict[str, str]]:
    if mode == Mode.TERMS:
        msgs = terms_analysis.build_messages(user_text, context)
    elif mode == Mode.REFUND:
        msgs = refund_calc.build_messages(user_text, context)
    elif mode == Mode.RECOMMEND:
        msgs = recommend.build_messages(user_text, context)
    elif mode == Mode.GENERAL:
        msgs = general_question.build_messages(user_text, context)
    else:
        msgs = fallback.build_messages(user_text, context)
    print(f"[STARTEND] built messages for mode={mode} (context_len={len(context)}, messages_len={len(msgs)})")
    return msgs
