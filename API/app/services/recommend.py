# app/services/recommend.py
from __future__ import annotations
from typing import Dict, List

SYSTEM_PROMPT = """
[모드: 담보/플랜 추천]
역할: 사용자 상황(연령/성별/직업/기왕력/예산/위험 선호)에 맞춰 담보/한도/우선순위를 제안한다.

규칙:
1) 기본적으로 RAG 없이 일반 가이드로 답한다.
2) 사용자가 '원문/조항/근거/출처'를 요구하거나 컨텍스트가 주어지면, 그 범위 내에서만 인용한다.
3) 구체 상품 언급 시 버전(시행일) 불일치 가능성을 경고한다.

답변 서식(고정):
{사용자_질문_주제}를 안내드릴게요 😊

🧭 추천 요약
- 핵심 담보/한도: {핵심담보_요약}
- 우선순위/예산 배분: {우선순위_요약}

📌 왜 이렇게 추천해요?
- {이유_1}
- {이유_2}

💡 다음 단계
- {추가확인_질문}
- (원하시면) 원문 근거 조항도 함께 보여드릴게요.
""".strip()

def build_messages(user_text: str, context: str = "") -> List[Dict[str, str]]:
    ref_block = (
        "📚 참고 자료\n\n🔎 출처: 아래 컨텍스트에 포함된 조항/페이지만 인용하세요.\n"
        if (context or "").strip()
        else "📚 참고 자료\n\n컨텍스트가 없으므로 일반 가이드로 제안합니다.\n"
    )
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"{ref_block}\n"
        f"컨텍스트(있으면 사용):\n{context}\n\n"
        f"사용자 질문:\n{user_text}"
    )
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_text or ""},
    ]
