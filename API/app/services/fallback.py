# app/services/fallback.py
from __future__ import annotations
from typing import Dict, List

SYSTEM_PROMPT = """
[모드: FALLBACK]
역할: 보험 도메인과 무관하거나 모호한 질문에 대해, 가능한 범위에서 방향을 제시하고 구체화를 유도한다.

규칙:
1) 민감/법률/의료 판단은 제공하지 말고 공식 채널을 안내한다.
2) 다음 질문 예시(선택지)를 2~3개 제시해 사용자가 쉽게 구체화하도록 돕는다.

답변 서식(고정):
{사용자_질문_주제}를 안내드릴게요 😊

가능한 다음 질문 예시
- {예시질문_1}
- {예시질문_2}
- {예시질문_3}
""".strip()

def build_messages(user_text: str, context: str = "") -> List[Dict[str, str]]:
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"사용자 메시지:\n{user_text}\n"
        f"→ 위 메시지가 보험 관련이 맞는지 애매하면, 가능한 관련 주제를 추정해 '선택지' 형태로 재질문을 제안하세요."
    )
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_text or ""},
    ]

def static_answer(user_text: str) -> dict:
    msg = (
        "보험 주제인지 애매해요. 아래 중 하나로 알려주시면 정확히 도와드릴게요 😊\n"
        "- 가입한 보험사/상품명을 알려주세요.\n"
        "- 어떤 치료/행위(예: 도수치료, MRI)인지 말씀해 주세요.\n"
        "- 환급/청구 문의면 상황을 한 줄로 적어주세요."
    )
    return {"answer": msg}
