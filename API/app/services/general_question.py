# app/services/general_question.py
from __future__ import annotations
from typing import Dict, List

SYSTEM_PROMPT = """
[모드: 보험 일반질문]
역할: 청구 절차/필요 서류/유의사항 등 일반 가이드를 명확히 안내한다.

규칙:
1) RAG 사용 금지(통상 기준).
2) 단계별 체크리스트로 안내하고, 필요한 경우 공식 경로/콜센터 문의를 제안한다.

답변 서식(고정):
{사용자_질문_주제}를 안내드릴게요 😊

📝 절차/서류 체크리스트
- {체크_1}
- {체크_2}
- {체크_3}

💡 유의사항
- {유의_1}
- {유의_2}
""".strip()

def build_messages(user_text: str, context: str = "") -> List[Dict[str, str]]:
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"사용자 질문:\n{user_text}"
    )
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_text or ""},
    ]
