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

# def _to_transcript(chat_meta: Optional[Dict[str, Any]], user_text: str) -> str:
#     """
#     chat_meta(이전 대화)와 현재 user_text를 사람이 읽는 대화 로그 문자열로 직렬화.
#     chat_meta가 dict/str/None 어떤 형태로 와도 최대한 안전하게 처리.
#     """
#     lines: List[str] = []
#     if isinstance(chat_meta, dict):
#         # 키를 정렬해 재현성 확보 (user0, assistant0, user1... 같은 형태를 기대)
#         for k in sorted(chat_meta.keys(), key=lambda x: str(x)):
#             role = "user" if "user" in str(k).lower() else ("assistant" if "assistant" in str(k).lower() else "note")
#             lines.append(f"{role}: {chat_meta[k]}")
#     elif isinstance(chat_meta, list):
#         # ["user: ...", "assistant: ..."] 같은 경우
#         for item in chat_meta:
#             lines.append(str(item))
#     elif isinstance(chat_meta, str):
#         lines.append(chat_meta.strip())

#     # 현재 사용자 입력을 마지막에 추가
#     if user_text:
#         lines.append(f"user: {user_text.strip()}")

#     # 비어있으면 현재 입력만 반환
#     if not lines:
#         return f"user: {user_text.strip()}"
#     return "\n".join(lines)

# 1) 간단 요약기 (mini 모델로 1~2문장 요약)
def summarize_history_for_context(chat_meta: Optional[Dict[str, Any] | List[str] | str], max_chars: int = 1200) -> str:
    """
    과거 대화를 1~2문장으로 요약. 실패 시 빈 문자열 반환.
    매우 저비용/저온도 호출을 가정. (원하면 동기/비동기 분리)
    """
    # 원자료 문자열화(길면 컷)
    raw = ""
    if isinstance(chat_meta, dict):
        # 키 정렬은 기존 로직 유지
        lines = []
        for k in sorted(chat_meta.keys(), key=lambda x: str(x)):
            role = "user" if "user" in str(k).lower() else ("assistant" if "assistant" in str(k).lower() else "note")
            lines.append(f"{role}: {chat_meta[k]}")
        raw = "\n".join(lines)
    elif isinstance(chat_meta, list):
        raw = "\n".join(str(x) for x in chat_meta)
    elif isinstance(chat_meta, str):
        raw = chat_meta.strip()
    raw = (raw or "").strip()[:max_chars]

    if not raw:
        return ""

    prompt = (
        "다음 대화 로그를 1~2문장으로 요약하세요. 핵심 의도/주제만 보존하고 사족은 제거하세요.\n"
        "출력은 한국어 1~2문장, 메타/불릿/코드블록 금지.\n\n"
        f"<<LOG>>\n{raw}\n<<END>>"
    )
    try:
        resp = _client.chat.completions.create(
            model=CLASSIFIER_MODEL,  # mini 사용
            messages=[
                {"role": "system", "content": "대화 요약가. 반드시 1~2문장으로만."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return ""
    
def extract_sticky_entities(chat_meta: Optional[Dict[str, Any] | List[str] | str],
                            entity_hints: Optional[Dict[str, List[str]]] = None,
                            max_lookback: int = 8) -> Dict[str, Optional[str]]:
    """
    최근 대화(최대 max_lookback 메시지 범위)에서 보험사/상품 단일 후보를 뽑아 Sticky로 사용.
    - entity_hints: {"insurers": [...], "products": [...]} 주면 정확도↑ (선택)
    - 충돌(후보가 2개 이상)이면 None 반환 → 상속 중단(보수적)
    """
    texts: List[str] = []
    if isinstance(chat_meta, dict):
        # 키 정렬 후 최근 메시지 몇 개만
        pairs = [(str(k), str(v)) for k, v in chat_meta.items()]
        pairs.sort(key=lambda kv: kv[0])
        texts = [v for _, v in pairs][-max_lookback:]
    elif isinstance(chat_meta, list):
        texts = [str(x) for x in chat_meta][-max_lookback:]
    elif isinstance(chat_meta, str):
        texts = [chat_meta.strip()]

    blob = "\n".join(texts).strip()
    if not blob:
        return {"insurer": None, "product": None}

    insurers = set()
    products = set()

    # 힌트 사전에 기반한 정합 추출 (정확·결정적)
    if entity_hints:
        for name in (entity_hints.get("insurers") or []):
            if name and name.lower() in blob.lower():
                insurers.add(name)
        for name in (entity_hints.get("products") or []):
            if name and name.lower() in blob.lower():
                products.add(name)

    # 힌트가 없거나 못찾은 경우: 간단한 휴리스틱(괄호/보험/실손 등 패턴)
    import re
    if not insurers:
        # 예: 롯데, 한화, 삼성, 현대 등 고유명사 패턴을 추가로 넣을 수 있음
        m = re.findall(r"(롯데|한화|삼성|현대|KB|메리츠|흥국|DB|교보|라이나|농협|동양|우체국)", blob)
        insurers.update(m)
    if not products:
        # 예: '보험', '실손', '무배당', '간편', '의료비' 등 포함된 상품명 라인 추출
        for line in blob.splitlines():
            if ("보험" in line) or ("실손" in line):
                # 너무 긴 줄은 제외
                cand = line.strip()
                if 3 <= len(cand) <= 80:
                    products.add(cand)

    # 충돌 시 보수적으로 배제
    insurer = list(insurers)[0] if len(insurers) == 1 else None
    product = list(products)[0] if len(products) == 1 else None
    return {"insurer": insurer, "product": product}


# 2) 분류기 호출: 메시지 구성 방식 변경
def run_classifier_llm(user_text: str,
                       chat_meta: Optional[Dict[str, Any]] = None,
                       entity_hints: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
    """
    최신 발화 우선 + Sticky 엔티티 상속.
    """
    SYSTEM_RULES = (
        "당신은 보험 도메인 대화 라우터입니다. 오직 JSON만 출력하세요.\n"
        "원칙:\n"
        "1) HISTORY는 참고용입니다. CURRENT_QUESTION과 충돌하면 CURRENT_QUESTION을 우선합니다.\n"
        "2) primary_flow/엔터티/의도는 최신 발화를 최우선으로 추정합니다.\n"
        "3) 환급금 관련 질문은 다음과 같이 분류합니다:\n"
        "   - 사용자가 받을 '환급금의 액수'를 직접 묻는 질문(숫자/계산/금액 범위 요청 포함)만 REFUND\n"
        "   - 그 외 환급금 절차/조건/서류/가능 여부/약관 조항 등은 TERMS\n"
        "4) CURRENT_QUESTION에 특정 보험사/상품명이 언급되면, entities.insurer/entities.product를 반드시 채우고,\n"
        "   primary_flow가 TERMS일 때 retrieval_suggestion은 반드시 'on'으로 설정합니다.\n"
        "5) CURRENT_QUESTION에 보험사/상품명이 없더라도, [STICKY_ENTITIES]에 단일 후보로 제공된 값이 있으면 해당 값을 상속하여 채웁니다.\n"
        "   단, 후보가 다수/모호하면 상속하지 마세요.\n"
        "6) 엔티티는 NULL을 남발하지 말고, CURRENT_QUESTION 또는 STICKY에서 추출 가능한 것은 반드시 채웁니다.\n"
        "스키마:\n"
        "{"
        "\"primary_flow\":\"TERMS|REFUND|RECOMMEND|GENERAL|FALLBACK\","
        "\"confidence\":0.0,"
        "\"entities\":{"
        "  \"insurer\":null,\"product\":null,\"version\":null,"
        "  \"topic\":null,\"icd10_candidate\":null,"
        "  \"product_type\":null,\"focus_topics\":[]"
        "},"
        "\"retrieval_suggestion\":\"on|off|auto\","
        "\"reasons\":\"최소 근거\","
        "\"tags\":[\"키워드\"],"
        "\"text\":\"HISTORY와 CURRENT_QUESTION을 합쳐 1~2문장 요약(보험사/상품이 있으면 반드시 포함)\""
        "}\n"
        "반드시 유효한 JSON만 출력하고 여분 텍스트/코드블록을 금지합니다.\n"
    )

    # 기존 요약 유지
    hist_summary = summarize_history_for_context(chat_meta)
    history_block = f"[HISTORY]\n{hist_summary}" if hist_summary else "[HISTORY]\n(없음)"

    # 🔧 NEW: Sticky 엔티티 추출
    sticky = extract_sticky_entities(chat_meta, entity_hints=entity_hints, max_lookback=8)
    sticky_block = "[STICKY_ENTITIES]\n" \
                   f"insurer: {sticky.get('insurer') or '(없음)'}\n" \
                   f"product: {sticky.get('product') or '(없음)'}"

    current = f"[CURRENT_QUESTION]\n{(user_text or '').strip()}"

    messages = [
        {"role": "system", "content": SYSTEM_RULES},
        {"role": "assistant", "content": history_block},     # 참고용
        {"role": "assistant", "content": sticky_block},      # 🔧 상속용 구조화 컨텍스트
        {"role": "user", "content": current},                # 최신 질문(최우선)
    ]

    # (로깅은 기존 body_logger 로직 재사용)
    try:
        payload_str = "\n############ [LLM DEBUG] ############\n"
        payload_str += json.dumps(messages, ensure_ascii=False, default=str)
    except Exception:
        payload_str = "\n############ [LLM DEBUG] ############\n" + str(messages)
    body_logger.info(payload_str)

    resp = _client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=messages,
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    content = (resp.choices[0].message.content or "").strip()
    body_logger.info("\n############ [LLM DEBUG2] ############\n" + content)

    try:
        result = json.loads(content)
    except Exception:
        # 실패 시 안전값
        return {
            "primary_flow": "GENERAL",
            "confidence": 0.3,
            "entities": {
                "insurer": None, "product": None, "version": None,
                "topic": None, "icd10_candidate": None,
                "product_type": None, "focus_topics": [],
            },
            "retrieval_suggestion": "auto",
            "reasons": "parse_error",
            "tags": [],
            "text": user_text or ""
        }

    # ===== 환급금 관련내용 보정 시작 =====
    entities = result.get("entities", {}) or {}
    insurer = (entities.get("insurer") or "").strip() or None
    product = (entities.get("product") or "").strip() or None
    topic   = (entities.get("topic") or "").strip() or None

    if (not insurer or not product) and sticky:
        s_ins = sticky.get("insurer")
        s_prod = sticky.get("product")
    # 현재가 비어있고 sticky에 단일 후보가 있으면 상속
    if not insurer and s_ins:
        entities["insurer"] = s_ins
        insurer = s_ins
    if not product and s_prod:
        entities["product"] = s_prod
        product = s_prod
    result["entities"] = entities

    # (A) 금액 질문 판별(정규식/키워드)
    ask_amount_like = False
    q = (user_text or "").lower()
    # 금액/계산/얼마/원/만원/비율/산출 등 간단 키워드와 숫자 패턴
    if any(k in q for k in ["얼마", "금액", "환급률", "계산", "산출", "비율", "얼마나 나오", "예상 환급"]):
        ask_amount_like = True
    # 숫자/통화 패턴도 힌트
    import re
    if re.search(r"\b\d+(\,\d{3})*(원|만원|,?\s?won)\b", q):
        ask_amount_like = True

    # (B) 1차 분류 보정: 금액 질문만 REFUND
    if ask_amount_like:
        result["primary_flow"] = "REFUND"
    else:
        # 환급금 관련인데 금액을 직언하지 않으면 TERMS 쪽으로
        if "환급" in q or "환불" in q or "해지환급" in q:
            result["primary_flow"] = "TERMS"

    # (C) 엔티티가 존재하면 TERMS에서 retrieval_suggestion 강제 ON
    if result.get("primary_flow") == "TERMS" and (insurer or product):
        result["retrieval_suggestion"] = "on"

    # (D) 요약 text에 엔티티가 빠지면 보완(프롬프트가 보장해도 가끔 빠짐)
    summary = (result.get("text") or "").strip()
    if (insurer or product) and summary:
        if insurer and insurer not in summary:
            summary = f"{insurer} " + summary
        if product and product not in summary:
            summary = f"{summary} (상품: {product})"
        result["text"] = summary

    # (E) 태그 보강
    tags = result.get("tags") or []
    if "환급금" not in tags and ("환급" in q or "해지환급" in q):
        tags.append("환급금")
    if (insurer or product) and "약관" not in tags and result.get("primary_flow") == "TERMS":
        tags.append("약관")
    result["tags"] = list(dict.fromkeys(tags))  # 중복 제거
    # ===== 보정 끝 =====

    return result

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
