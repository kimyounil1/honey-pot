# app/services/terms_analysis.py
from __future__ import annotations
from typing import Dict, List

SYSTEM_PROMPT = """
[모드: 보험약관분석]
역할: 보험 약관/특약/증권 내용을 사용자가 이해하기 쉽게, 상담원이 설명하듯 친근하게 풀어준다.

원칙:
1) 우선 일반적인 지식과 이해를 바탕으로 자연스럽게 설명한다.
2) 불확실하거나 세부 조건이 필요한 경우에만 컨텍스트(DB/문서)를 인용하고,
   인용 시 출처(보험사/상품/버전/조항/페이지)를 간단히 붙인다.
3) 답변 형식은 고정하지 않는다. 질문 주제에 맞게 섹션을 선택하고,
   불릿/숫자 예시 등을 활용해 직관적으로 설명한다.
4) 톤은 딱딱한 법률 문체가 아니라, 고객 상담 톤으로 짧고 쉬운 문장을 쓴다.
5) 필요한 경우 계산 예시나 비유를 들어 이해를 돕는다.

출력 예시:
- 상황 요약
- 핵심 설명 (예: "실손보험은 실제 낸 병원비까지만 보상돼요.")
- 숫자 예시나 그림 같은 설명
- 추가 확인이 필요한 사항 (약관/특약 조항, 청구 서류 등)
""".strip()


def build_messages(user_text: str, context: str = "") -> List[Dict[str, str]]:
    ref_block = (
        f"📚 참고 자료 (필요 시만 사용)\n\n{context}"
        if context.strip()
        else "📚 참고 자료 없음\n"
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
