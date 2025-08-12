from typing import List, Dict

SYSTEM_PROMPT = (
    "[모드: 보험일반질문]\n"
    "역할: 보험 관련 일반적인 질문에 대해 명확하고 근거 있는 답변을 제공한다.\n"
    "\n"
    "출력 섹션(헤더 고정, 순서 고정):\n"
    "1) 요약(2~3줄)\n"
    "2) 상세 설명\n"
    "3) 유의사항\n"
    "4) 근거\n"
    "\n"
    "작성 규칙:\n"
    "- 답변은 한국어.\n"
    "- 불확실한 경우 근거와 함께 추정 여부를 명시.\n"
    "- 가능한 경우 표를 사용하여 가독성을 높인다.\n"
    "- 근거 표기 필수.\n"
)

def build_messages(user_text: str, context: str = "") -> List[Dict[str, str]]:
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"컨텍스트:\n{context}\n\n"
        f"사용자 질문:\n{user_text}"
    )
    return [
        {"role": "system", "content": "너는 한국 사용자에게 보험을 쉽게 설명하는 보조자다. 항상 근거를 표기한다."},
        {"role": "user", "content": prompt},
    ]
