from __future__ import annotations
import json
import os
import asyncio
import logging
from typing import Any, Dict, List, Optional
from openai import OpenAI

CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "gpt-4o-mini")
ANSWERER_MODEL   = os.getenv("ANSWERER_MODEL",   "gpt-4o")

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
body_logger = logging.getLogger("debug.body")  # 전용 로거

def _to_transcript(chat_meta: Optional[Dict[str, Any]], user_text: str) -> str:
    """
    chat_meta(이전 대화)와 현재 user_text를 사람이 읽는 대화 로그 문자열로 직렬화.
    chat_meta가 dict/str/None 어떤 형태로 와도 최대한 안전하게 처리.
    """
    lines: List[str] = []
    if isinstance(chat_meta, dict):
        # 키를 정렬해 재현성 확보 (user0, assistant0, user1... 같은 형태를 기대)
        for k in sorted(chat_meta.keys(), key=lambda x: str(x)):
            role = "user" if "user" in str(k).lower() else ("assistant" if "assistant" in str(k).lower() else "note")
            lines.append(f"{role}: {chat_meta[k]}")
    elif isinstance(chat_meta, list):
        # ["user: ...", "assistant: ..."] 같은 경우
        for item in chat_meta:
            lines.append(str(item))
    elif isinstance(chat_meta, str):
        lines.append(chat_meta.strip())

    # 현재 사용자 입력을 마지막에 추가
    if user_text:
        lines.append(f"user: {user_text.strip()}")

    # 비어있으면 현재 입력만 반환
    if not lines:
        return f"user: {user_text.strip()}"
    return "\n".join(lines)


def run_classifier_llm(user_text: str, chat_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    모드 분류/엔터티 추출 전용 경량 호출 (JSON ONLY).
    이전 대화 + 현재 입력을 함께 고려하여 primary_flow를 결정하고,
    요약 텍스트는 `text` 필드에 넣어 반환.
    """
    # 강화된 시스템 프롬프트
    system_meta = (
        "당신은 보험 도메인 대화 라우터입니다. 오직 JSON만 출력하세요.\n"
        "다음 규칙으로 primary_flow를 결정합니다 (최근 사용자 발화를 우선하되 이전 맥락도 고려):\n"
        "- TERMS: 약관/보장/면책/청구 절차/특약/자필서명/약관 분석/해석 등의 문의\n"
        "- REFUND: 환불/해지/해지환급금/무해지환급/환급률/환급금 얼마 등의 문의\n"
        "- RECOMMEND: 추천/어떤 상품이 좋은지/맞춤/비교/견적/가입 권유 등의 문의\n"
        "- GENERAL: 위에 명확히 속하지 않는 일반 질의응답\n"
        "- FALLBACK: 사용자의 의도가 불명확하여 분류 불가\n"
        "질병코드가 존재하더라도, retrieval_suggestion은 항상 on으로 반환\n"
        "반드시 아래 스키마의 JSON 객체만 반환하세요.\n"
        "chat_meta{\n"
        "  \"primary_flow\":\"TERMS|REFUND|RECOMMEND|GENERAL|FALLBACK\",\n"
        "  \"confidence\":0.0,\n"
        "  \"entities\":{\n"
        "    \"insurer\":null, \"product\":null, \"version\":null,\n"
        "    \"topic\":null, \"icd10_candidate\":null,\n"
        "    \"product_type\":null, \"focus_topics\":[]\n"
        "  },\n"
        "  \"retrieval_suggestion\":\"on|off|auto\",\n"
        "  \"reasons\":\"최소한의 근거 요약\",\n"
        "  \"tags\":[\"키워드\"],\n"
        "  \"text\":\"이전 대화 + 현재 발화를 1~2문장으로 요약\"\n"
        "}\n"
        "JSON 이외의 텍스트는 절대 출력하지 마세요."
    )

    user_context = _to_transcript(chat_meta, user_text)

    messages = [
        {"role": "system", "content": system_meta},
        {"role": "user", "content": f"<<CONTEXT>>\n{user_context}\n<<END>>"}
    ]

    try:
        payload_str = json.dumps(
            messages.model_dump() if hasattr(messages, "model_dump") else messages.__dict__,
            ensure_ascii=False,
            default=str
        )
    except Exception:
        # 혹시라도 직렬화 실패 시 문자열 fallback
        payload_str = "\n############ [LLM DEBUG] ############\n" + str(messages)
    body_logger.info(payload_str)

    resp = _client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=messages,
        temperature=0.0,
        response_format={"type": "json_object"}  # JSON 모드
    )
    content = (resp.choices[0].message.content or "").strip()

    payload_str = "\n############ [LLM DEBUG2] ############\n" + str(content)
    body_logger.info(payload_str)

    try:
        return json.loads(content)
    except Exception:
        # 실패 시 안전한 기본값
        return {
            "primary_flow": "GENERAL",
            "confidence": 0.3,
            "entities": {
                "insurer": None,
                "product": None,
                "version": None,
                "topic": None,
                "icd10_candidate": None,
                "product_type": None,
                "focus_topics": [],
            },
            "retrieval_suggestion": "auto",
            "reasons": "parse_error",
            "tags": [],
            "text": user_text or ""
        }

# ================== 최종 Answerer LLM (chat.py 호환) ==================
def run_llm(messages: List[Dict[str, str]]) -> str:
    resp = _client.chat.completions.create(
        model=ANSWERER_MODEL,
        messages=messages,
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()

async def call_llm(messages: List[Dict[str, str]]) -> str:
    return await asyncio.to_thread(run_llm, messages)
