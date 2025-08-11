from typing import List, Dict
from app.services.common import Mode, GREETING, TERMS_KEYS, REFUND_KEYS, RECO_KEYS
from app.services import terms_analysis, refund_calc, recommend, fallback

SYSTEM_PROMPT = (
    "[모드: STARTEND]\n"
    "역할: 사용자의 발화와 첨부 컨텍스트를 고려해 적절한 하위 어시스턴트로 연결한다.\n"
    "우선순위: 약관분석 > 환급금찾기 > 보험추천, 그 외는 예외질문(fallback).\n"
)

def classify(user_text: str) -> Mode:
    lt = user_text.lower()
    if any(k in lt for k in TERMS_KEYS):  return Mode.TERMS
    if any(k in lt for k in REFUND_KEYS): return Mode.REFUND
    if any(k in lt for k in RECO_KEYS):   return Mode.RECO
    return Mode.FALLBACK

def build_messages(user_text: str, context: str = "", first_message: bool = False) -> List[Dict[str, str]]:
    mode = classify(user_text)
    if mode == Mode.TERMS:
        msgs = terms_analysis.build_messages(user_text, context)
    elif mode == Mode.REFUND:
        msgs = refund_calc.build_messages(user_text, context)
    elif mode == Mode.RECO:
        msgs = recommend.build_messages(user_text, context)
    else:
        msgs = fallback.build_messages(user_text, context)

    if first_message:
        for m in msgs:
            if m["role"] == "user":
                m["content"] = GREETING + m["content"]
                break
    return msgs
