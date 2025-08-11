from typing import List, Dict

SYSTEM_PROMPT = (
    "[모드: 예외질문]\n"
    "역할: 보험 외 질문은 답변하지 않고, 본 서비스의 3가지 기능으로만 유도한다.\n"
    "\n"
    "출력 섹션(헤더 고정, 순서 고정):\n"
    "1) 안내\n"
    "2) 다음 중 하나로 질문해 주세요\n"
    "\n"
    "규칙:\n"
    "- 보험 외 주제에는 내용을 제공하지 말고 정중히 안내만 한다.\n"
    "- 본 서비스 기능: (1) 약관분석, (2) 환급금 찾기, (3) 보험추천\n"
    "- 각 기능별 구체적 예시 2개씩 제공.\n"
    "- 답변은 한국어.\n"
)


def build_messages(user_text: str, context: str = "") -> List[Dict[str, str]]:
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"컨텍스트(있으면 사용):\n{context}\n\n"
        f"사용자 질문:\n{user_text}"
    )
    return [
        {"role": "system", "content": "너는 한국 사용자에게 보험을 쉽게 설명하는 보조자다."},
        {"role": "user", "content": prompt},
    ]
