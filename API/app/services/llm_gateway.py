# app/services/llm_gateway.py
from __future__ import annotations
import json
import os
import asyncio
from typing import Any, Dict, List, Optional

from openai import OpenAI

# 환경 변수(없으면 기본값)
CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "gpt-4o-mini")
ANSWERER_MODEL   = os.getenv("ANSWERER_MODEL",   "gpt-4o")

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ================== 분류용 LLM ==================
def run_classifier_llm(user_text: str, attachments_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    모드 분류/엔터티 추출 전용 경량 호출 (JSON ONLY).
    """
    system = (
        "당신은 보험 도메인 대화 라우터입니다. 사용자 질문과 첨부 정보를 분석하여 JSON만 출력하세요.\n"
        "{"
        "\"primary_flow\":\"TERMS|REFUND|RECOMMEND|GENERAL|FALLBACK\","
        "\"confidence\":0.0,"
        "\"entities\":{"
        "  \"insurer\":null,\"product\":null,\"version\":null,"
        "  \"topic\":null,\"icd10_candidates\":[]"
        "},"
        "\"retrieval_suggestion\":\"on|off|auto\","
        "\"reasons\":\"...\","
        "\"tags\":[\"...\"]"
        "}\n"
        "JSON 이외의 텍스트는 출력하지 마세요."
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": (user_text or "")},
    ]
    if attachments_meta:
        try:
            meta_str = json.dumps(attachments_meta)[:2000]
        except Exception:
            meta_str = str(attachments_meta)[:2000]
        messages.append({"role": "system", "content": f"[attachments-meta]\n{meta_str}"})

    resp = _client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=messages,
        temperature=0.1,
    )
    content = (resp.choices[0].message.content or "").strip()

    try:
        return json.loads(content)
    except Exception:
        return {
            "primary_flow": "GENERAL",
            "confidence": 0.3,
            "entities": {},
            "retrieval_suggestion": "auto",
            "reasons": "parse_error",
            "tags": []
        }

# ================== 최종 Answerer LLM (chat.py 호환) ==================
def run_llm(messages: List[Dict[str, str]]) -> str:
    resp = _client.chat.completions.create(
        model=ANSWERER_MODEL,
        messages=messages,
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()

# chat.py는 async call_llm(...)을 호출하므로 간단 래퍼 제공
async def call_llm(messages: List[Dict[str, str]]) -> str:
    """Run the blocking LLM call in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(run_llm, messages)
