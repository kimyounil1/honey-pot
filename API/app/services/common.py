# app/services/common.py
from __future__ import annotations
import os
import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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
    text: str = ""
    # 분류 단계에서 생성된 보조 컨텍스트(히스토리 요약 등)를 문자열로 전달
    ctx: str = ""

# ================== RAG 스위치 정책 ==================
_FORCE_OFF = ["근거 없이", "출처 없이", "인용 빼고", "대략만", "대충만"]
_HINT_RAG  = ["근거", "조항", "출처", "면책", "원문", "링크", "증빙", "첨부", "파일"]

def decide_use_retrieval(
    text: str,
    # n_attachments: int,
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

    txt = (text or "").strip()

    if any(k in txt for k in _FORCE_OFF):
        return False

    # if n_attachments > 0:
    #     return mode in (Mode.TERMS, Mode.REFUND, Mode.RECOMMEND)

    if any(k in txt for k in _HINT_RAG):
        return mode in (Mode.TERMS, Mode.REFUND, Mode.RECOMMEND)

    if suggestion == RetrievalSuggestion.ON and mode in (Mode.TERMS, Mode.REFUND):
        return True

    return False

# ================== 엔티티 힌트 빌더 ==================
def _build_entity_hints(prev_chats: List[str], max_lookback: int = 10) -> Dict[str, List[str]]:
    texts = [str(x) for x in (prev_chats or [])][-max_lookback:]

    insurers: set[str] = set()
    products: set[str] = set()

    INSURER_PAT = r"(롯데|한화|삼성|현대|KB|메리츠|흥국|DB|교보|라이나|농협|동양|우체국)"
    for t in texts:
        for m in re.findall(INSURER_PAT, t):
            insurers.add(m)

        # ‘보험/실손/무배당/간편…’ 포함 라인을 후보 상품으로 수집
        for line in t.splitlines():
            if ("보험" in line) or ("실손" in line):
                s = line.strip()
                if 3 <= len(s) <= 80:
                    products.add(s)

    return {
        "insurers": sorted(insurers),
        "products": sorted(products),
    }

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

def decide_flow_with_llm(user_text: str, prev_chats: List[str]) -> FlowDecision:
    from .llm_gateway import run_classifier_llm

    meta = dict()
    for i in range(len(prev_chats)):
        role = "user" + str(i%2) if i % 2 == 0 else "assistant" + str((i-1)%2)
        meta[role] = prev_chats[i]

    # (신규) 힌트 생성
    entity_hints = _build_entity_hints(prev_chats, max_lookback=10)

    try:
        raw = run_classifier_llm(
            user_text=user_text,
            chat_meta=meta,
            entity_hints=entity_hints,
        )
    except Exception:
        return FlowDecision(
            flow=Mode.GENERAL, confidence=0.0, reasons="classifier_error",
            tags=[], entities={}, retrieval_suggestion=RetrievalSuggestion.AUTO, use_retrieval=False
        )

    # 이하 기존 로직 동일...
    mode  = _map_mode(raw.get("primary_flow", "GENERAL"))
    conf  = float(raw.get("confidence", 0.0))
    ents  = raw.get("entities", {}) or {}
    sug   = _map_suggestion(raw.get("retrieval_suggestion", "auto"))
    rsn   = (raw.get("reasons") or "")[:500]
    tags  = raw.get("tags", []) or []
    text  = raw.get("text", "")
    # 분류 보조 컨텍스트 가공(문자열로 안전 변환)
    try:
        import json
        _ctx = raw.get("__ctx") or {}
        if isinstance(_ctx, dict):
            hist = (_ctx.get("history_summary") or "").strip()
            # probe = _ctx.get("current_entities_probed") or {}
            compact = _ctx.get("decision_compact") or {}

            parts = []
            if hist:
                parts.append("[HISTORY]\n" + hist)
            # if probe:
            #     parts.append("[ENTITIES PROBED]\n" + json.dumps(probe, ensure_ascii=False))
            if compact:
                parts.append("[DECISION]\n" + json.dumps(compact, ensure_ascii=False))
            ctx = "\n\n".join(parts)
        else:
            ctx = str(_ctx)
    except Exception:
        ctx = ""

    use_ret = decide_use_retrieval(text=text, mode=mode, suggestion=sug)

    return FlowDecision(
        flow=mode, confidence=conf, reasons=rsn, tags=tags,
        entities=ents, retrieval_suggestion=sug, use_retrieval=use_ret, text=text, ctx=ctx,
    )
