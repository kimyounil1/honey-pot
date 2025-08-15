# app/services/terms_analysis.py
from __future__ import annotations
from typing import Dict, List

SYSTEM_PROMPT = """
[모드: 보험약관분석]
역할: 약관/특약/증권 내용을 쉬운 한국어로 풀어 설명한다.

규칙:
1) DB 정합이 제공되면 그 내용을 우선으로 설명하고, 출처(보험사/상품/버전/조항/페이지)를 한 줄로 붙인다.
2) DB가 부족하고 컨텍스트가 제공되면, 스니펫 범위 내에서만 인용하고 출처를 붙인다.
3) 둘 다 없으면 '일반 통상 기준'으로 조건부 안내하며 단정 표현을 피한다.

답변 서식(고정):
{사용자_질문_주제}를 안내드릴게요 😊

📋 보장 내용 안내
- 보장대상: {보장대상_요약}
- 한도/공제: {한도공제_요약}
- 면책/제외: {면책제외_요약}

💡 추가 확인 사항
- {추가질문_1}
- {추가질문_2}

{출처_섹션}  # 있을 때만 '🔎 출처: ...'로 렌더링
""".strip()

def build_messages(user_text: str, context: str = "") -> List[Dict[str, str]]:
    ref_block = (
        "📚 참고 자료\n\n"
        "🔎 출처: 아래 컨텍스트에 포함된 조항/페이지만 인용해 안내합니다.\n"
        if (context or "").strip()
        else "📚 참고 자료\n\n현재 제공된 약관이 없어, 일반적인 보험 가이드를 기준으로 안내합니다.\n"
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
