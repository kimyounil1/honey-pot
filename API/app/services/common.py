# app/services/common.py
from __future__ import annotations
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ================== 모드 정의 (RAG는 '스위치'로만 운용) ==================
class Mode(str, Enum):
    TERMS = "TERMS"          # 약관/특약/증권 분석
    REFUND = "REFUND"        # 환급금 추정/안내
    RECOMMEND = "RECOMMEND"  # 담보/플랜 추천
    GENERAL = "GENERAL"      # 보험 일반질문(절차/서류 등)
    FALLBACK = "FALLBACK"    # 도메인 외/모호

class RetrievalSuggestion(str, Enum):
    ON = "on"
    OFF = "off"
    AUTO = "auto"

# ================== 결정 구조체 ==================
@dataclass
class FlowDecision:
    flow: Mode
    confidence: float = 0.0
    reasons: str = ""
    tags: List[str] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    retrieval_suggestion: RetrievalSuggestion = RetrievalSuggestion.AUTO
    use_retrieval: bool = False

# ================== RAG 스위치 정책 ==================
_FORCE_OFF = ["근거 없이", "출처 없이", "인용 빼고", "대략만", "대충만"]
_HINT_RAG  = ["근거", "조항", "출처", "면책", "원문", "링크", "증빙", "첨부", "파일"]

def decide_use_retrieval(
    user_text: str,
    n_attachments: int,
    mode: Mode,
    suggestion: RetrievalSuggestion
) -> bool:
    """
    최종 RAG 스위치 결정.
    - GENERAL은 항상 False
    - 강제 OFF 문구가 있으면 False
    - 첨부가 있거나 근거/조항/출처 요구가 있으면 (TERMS/REFUND/RECOMMEND 한정) True
    - 분류 LLM 제안(suggestion)은 보조 신호
    """
    if mode == Mode.GENERAL:
        return False

    txt = (user_text or "").strip()

    if any(k in txt for k in _FORCE_OFF):
        return False

    if n_attachments > 0:
        return mode in (Mode.TERMS, Mode.REFUND, Mode.RECOMMEND)

    if any(k in txt for k in _HINT_RAG):
        return mode in (Mode.TERMS, Mode.REFUND, Mode.RECOMMEND)

    if suggestion == RetrievalSuggestion.ON and mode in (Mode.TERMS, Mode.REFUND):
        return True

    return False

# ================== 분류 + 스위치 ==================
def _map_mode(s: str) -> Mode:
    """
    분류 LLM 산출을 안전 매핑:
    - "RECO" → RECOMMEND
    - "RECOMMEND" → RECOMMEND
    - "RAG" → TERMS (RAG는 모드가 아니므로 약관해석으로 귀속)
    - 그 외 실패 → GENERAL
    """
    if not s:
        return Mode.GENERAL
    u = s.upper()
    if u in ("RECO", "RECOMMEND"):
        return Mode.RECOMMEND
    if u == "RAG":
        return Mode.TERMS
    try:
        return Mode(u)
    except Exception:
        return Mode.GENERAL

def _map_suggestion(s: str) -> RetrievalSuggestion:
    try:
        return RetrievalSuggestion((s or "auto").lower())
    except Exception:
        return RetrievalSuggestion.AUTO

def decide_flow_with_llm(user_text: str, attachment_ids: List[str]) -> FlowDecision:
    """
    내부에서 경량 분류 LLM을 호출하고 서버 정책으로 RAG 스위치를 최종 결정.
    """
    # 지연 임포트로 순환 참조 방지
    from .llm_gateway import run_classifier_llm

    meta = {"count": len(attachment_ids or [])}
    try:
        raw = run_classifier_llm(user_text=user_text, attachments_meta=meta)
    except Exception:
        return FlowDecision(
            flow=Mode.GENERAL, confidence=0.0, reasons="classifier_error",
            tags=[], entities={}, retrieval_suggestion=RetrievalSuggestion.AUTO, use_retrieval=False
        )

    mode  = _map_mode(raw.get("primary_flow", "GENERAL"))
    conf  = float(raw.get("confidence", 0.0))
    ents  = raw.get("entities", {}) or {}
    sug   = _map_suggestion(raw.get("retrieval_suggestion", "auto"))
    rsn   = (raw.get("reasons") or "")[:500]
    tags  = raw.get("tags", []) or []

    use_ret = decide_use_retrieval(
        user_text=user_text,
        n_attachments=meta["count"],
        mode=mode,
        suggestion=sug
    )

    return FlowDecision(
        flow=mode, confidence=conf, reasons=rsn, tags=tags,
        entities=ents, retrieval_suggestion=sug, use_retrieval=use_ret
    )
