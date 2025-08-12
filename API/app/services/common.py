from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
import logging
import os

from pydantic import BaseModel, Field
from openai import OpenAI  # openai>=1.x

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class Mode(str, Enum):
    TERMS = "TERMS"      # 약관분석
    REFUND = "REFUND"    # 환급금찾기
    RECO = "RECO"        # 보험추천
    GENERAL = "GENERAL"  # 보험 일반 질문
    RAG = "RAG"          # 첨부 기반 약관/근거 인용
    FALLBACK = "FALLBACK"

# ===== 키워드 힌트(보조 규칙) =====
TERMS_TRIGGERS  = {"약관", "조항", "면책", "보장 범위", "지급 기준", "보장한도", "보상 제외", "특약"}
REFUND_TRIGGERS = {"환급", "해지환급금", "만기환급금", "해지", "환급률", "적립", "무해지", "청구", "환불", "돌려"}
RECO_TRIGGERS   = {"추천", "설계", "담보", "보장갭", "갭", "권장", "보험사 비교", "특약 추천"}
GENERAL_TRIGGERS= {"서류", "절차", "증빙", "필요서류", "접수", "방법", "준비물", "문의", "일반"}
RAG_HINTS       = {"첨부", "파일", "PDF", "문서", "원문", "근거 찾아줘", "조항 인용", "붙인 약관", "컨텍스트"}

class ClassifierOut(BaseModel):
    primary_flow: Mode = Field(..., description="TERMS|REFUND|RECO|GENERAL|RAG|FALLBACK")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasons: str
    tags: List[str] = []

@dataclass
class FlowDecision:
    flow: Mode
    confidence: float
    reasons: str
    tags: List[str]

CLASSIFIER_SYSTEM = """당신은 보험 도메인 대화 라우터입니다.
사용자 입력과 첨부 존재 여부를 보고 다음 중 하나의 primary_flow를 고르세요:
- RAG: 첨부 문서를 근거로 조항/근거 인용이 필요한 경우
- TERMS: 약관/특약/보장범위/면책/지급기준 등의 '약관 해석'이 핵심 (첨부 없어도 됨)
- REFUND: 해지환급금/만기환급금/무해지 등 환급 관련 질의
- RECO: 사용자 상황 기반 보장갭 진단/담보/한도 추천
- GENERAL: 청구서류/절차/실무 가이드 등 일반 질의
- FALLBACK: 보험 도메인과 무관하거나 모호함

주의:
- 키워드만 보지 말고 문맥을 보세요.
- 첨부가 있어도 인용/근거 요구가 약하면 RAG가 아닐 수 있습니다.
- 반드시 JSON만 출력하세요.
"""

CLASSIFIER_USER_TMPL = """[사용자 입력]
{text}

[메타]
- 첨부 개수: {n_attachments}

[출력 포맷(JSON)]
{{
  "primary_flow": "RAG|TERMS|REFUND|RECO|GENERAL|FALLBACK",
  "confidence": 0.0~1.0,
  "reasons": "간단한 근거",
  "tags": ["연관 키워드", "..."]
}}
"""

def _call_llm_classifier(text: str, n_attachments: int) -> ClassifierOut:
    user = CLASSIFIER_USER_TMPL.format(text=text, n_attachments=n_attachments)
    resp = client.chat.completions.create(
        model=os.getenv("ROUTER_MODEL", "gpt-4o-mini"),
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": CLASSIFIER_SYSTEM},
            {"role": "user", "content": user},
        ],
    )
    content = resp.choices[0].message.content
    return ClassifierOut.model_validate_json(content)

def _has_any(text: str, needles: set) -> bool:
    return any(k in text for k in needles)

def _apply_priority_rules(
    text: str,
    n_attachments: int,
    primary_flow: Mode,
    confidence: float,
    tags: List[str]
) -> Mode:
    t = text.strip()

    wants_terms   = _has_any(t, TERMS_TRIGGERS)
    wants_refund  = _has_any(t, REFUND_TRIGGERS)
    wants_reco    = _has_any(t, RECO_TRIGGERS)
    wants_general = _has_any(t, GENERAL_TRIGGERS)
    hints_rag     = _has_any(t, RAG_HINTS)

    # 우선순위: RAG > TERMS > REFUND > RECO > GENERAL > FALLBACK
    # 1) 첨부 + (약관/근거/인용) 의도 → RAG
    if n_attachments > 0 and (wants_terms or hints_rag):
        return Mode.RAG

    # 2) 약관 해석 중심
    if wants_terms:
        return Mode.TERMS

    # 3) 환급
    if wants_refund:
        return Mode.REFUND

    # 4) 추천
    if wants_reco:
        return Mode.RECO

    # 5) 일반
    if wants_general:
        return Mode.GENERAL

    # 6) LLM 판단 반영(신뢰 충분)
    if confidence >= 0.55 and primary_flow in (Mode.RAG, Mode.TERMS, Mode.REFUND, Mode.RECO, Mode.GENERAL):
        return primary_flow

    # 7) 나머지
    return Mode.FALLBACK

def decide_flow_with_llm(user_text: str, attachment_ids: Optional[List[str]]) -> FlowDecision:
    n_attachments = len(attachment_ids or [])
    try:
        out = _call_llm_classifier(user_text, n_attachments)
        final_flow = _apply_priority_rules(
            text=user_text,
            n_attachments=n_attachments,
            primary_flow=out.primary_flow,
            confidence=out.confidence,
            tags=out.tags,
        )
        logger.info(f"[CLASSIFIER] primary={out.primary_flow}, final={final_flow}, conf={out.confidence}, tags={out.tags}")
        return FlowDecision(flow=final_flow, confidence=out.confidence, reasons=out.reasons, tags=out.tags)
    except Exception:
        logger.exception("Classifier failed, falling back.")
        return FlowDecision(flow=Mode.FALLBACK, confidence=0.0, reasons="classifier_error", tags=[])
