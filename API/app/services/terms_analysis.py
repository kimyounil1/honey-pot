# app/services/terms_analysis.py
from typing import List, Dict

# 청구 의도 감지 키워드(필요시 추가)
CLAIM_KEYWORDS = {
    "청구", "서류", "접수", "제출", "필요서류",
    "지급", "보상", "신청", "영수증", "심사", "청구방법", "청구기간", "claim"
}

def _has_claim_intent(text: str) -> bool:
    """사용자 질문에서 청구 관련 의도를 간단히 감지"""
    t = (text or "").replace(" ", "")
    return any(k in t for k in CLAIM_KEYWORDS)

# 공통 베이스 프롬프트(청구 섹션은 {CLAIM_BLOCK} 자리로 분기 주입)
SYSTEM_PROMPT_BASE = (
    "[모드: 보험약관분석]\n"
    "역할: 약관/특약/증권 내용을 이해하기 쉽게 풀어서 안내하고, 약관 여부에 따라 추가 질문을 덧붙인다.\n"
    "\n"
    "답변 형식(고정):\n"
    "실손보험에서 {사용자_질문_주제}를 안내드릴게요 😊\n"
    "\n"
    "📋 보장 내용 안내\n"
    "\n"
    "보장대상: {보장대상_요약}  \n"
    "한도/공제: {한도공제_요약}  \n"
    "면책/제외: {면책제외_요약}\n"
    "\n"
    "{CLAIM_BLOCK}"
    "📚 참고 자료\n"
    "\n"
    "현재 제공된 약관이 없어, 일반적인 보험 가이드를 기준으로 안내드렸습니다.\n"
    "\n"
    "📌 요약\n"
    "\n"
    "{핵심_요약_1줄}\n"
    "\n"
    "- 사용자가 보험사명, 보험상품명 또는 진단서를 이미 제공한 경우 아래 문구는 생략.\n"
    "- 제공하지 않았다면 항상 마지막에 추가:\n"
    "  '혹시 가입하신 보험사와 상품명을 알려주시겠어요?'\n"
    "  '진단서를 업로드해 주시면 더 정확하게 안내드릴 수 있습니다 !🍯'\n"
    "\n"
    "작성 규칙:\n"
    "- 답변은 한국어.\n"
    "- 각 제목 후 반드시 줄바꿈.\n"
    "- 표 대신 문장과 줄바꿈 위주로 구성.\n"
    "- 친근한 상담 톤 유지.\n"
    "- 숫자/조건은 컨텍스트에 있을 때만 명시(임의 추정 금지). 컨텍스트 없으면 원칙 위주로 설명.\n"
    "- 질문 주제와 무관한 예시(예: 도수치료 등)를 하드코딩하지 말 것.\n"
)

# 청구 섹션 블록(의도 있을 때만 삽입)
CLAIM_BLOCK = (
    "💵 청구 안내\n"
    "\n"
    "필요한 서류: {청구_서류_요약}  \n"
    "청구 절차: {청구_절차_요약}  \n"
    "청구 가능 기간: {청구_기간_요약}\n"
    "\n"
)

def _build_system_prompt(include_claim: bool) -> str:
    """청구 섹션 포함 여부에 따라 SYSTEM_PROMPT 완성"""
    claim_text = CLAIM_BLOCK if include_claim else ""
    return SYSTEM_PROMPT_BASE.replace("{CLAIM_BLOCK}", claim_text)

def build_messages(user_text: str, context: str = "") -> List[Dict[str, str]]:
    include_claim = _has_claim_intent(user_text)
    SYSTEM_PROMPT = _build_system_prompt(include_claim)

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"컨텍스트(검색결과가 있으면 반영):\n{context}\n\n"
        f"사용자 질문:\n{user_text}"
    )
    return [
        {
            "role": "system",
            "content": (
                "너는 한국 사용자에게 보험을 쉽게, 친근한 상담 톤으로 안내하는 보조자다. "
                "표 대신 줄바꿈과 한 줄 설명으로 작성한다."
            ),
        },
        {"role": "user", "content": prompt},
    ]
