from __future__ import annotations
import json
import os
import asyncio
import logging
from typing import Any, Dict, List, Optional
from openai import OpenAI

# ===== Models (env configurable) =====
SUMMARIZER_MODEL = os.getenv("SUMMARIZER_MODEL", "gpt-4o-mini")
CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "gpt-4o-mini")
ANSWERER_MODEL   = os.getenv("ANSWERER_MODEL",   "gpt-4o")

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
body_logger = logging.getLogger("debug.body")  # 전용 로거

# ========== Helpers ==========
def _supports_json_object(model_name: str) -> bool:
    """
    일부 모델은 response_format={'type':'json_object'}가 불안정/미지원일 수 있어 가드.
    운영 중 검증된 모델명 키워드 기준(필요 시 업데이트/환경변수 플래그로 제어).
    """
    model_name = (model_name or "").lower()
    # 알려진 계열: gpt-5, gpt-4o, o3
    return any(k in model_name for k in ["gpt-5", "gpt-4o", "o3"])


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
        "다음 대화 로그를 2~3문장으로 요약하세요. 핵심 의도/주제만 보존하고 사족은 제거하세요.\n"
        "출력은 한국어 2~3문장, 메타/불릿/코드블록 금지.\n\n"
        f"<<LOG>>\n{raw}\n<<END>>"
    )
    try:
        resp = _client.chat.completions.create(
            model=SUMMARIZER_MODEL,
            messages=[
                {"role": "system", "content": "대화 요약가. 반드시 2~3문장으로만."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        body_logger.info("\n############ [SUMMARY ERROR] ############\n" + repr(e))
        return ""



def _extract_current_entities(user_text: str,
                              entity_hints: Optional[Dict[str, List[str]]] = None) -> Dict[str, Optional[str]]:
    """최신 질문에서의 명시 후보(단일이면 확정). 다수면 None."""
    import re
    txt = (user_text or "").strip()
    if not txt:
        return {"insurer": None, "product": None}

    ins = set()
    prod = set()

    # 힌트가 있으면 먼저 결정적 매칭
    if entity_hints:
        for name in (entity_hints.get("insurers") or []):
            if name and name.lower() in txt.lower():
                ins.add(name)
        for name in (entity_hints.get("products") or []):
            if name and name.lower() in txt.lower():
                prod.add(name)

    # 보조 휴리스틱
    if not ins:
        for m in re.findall(r"(롯데|한화|삼성|현대|KB|메리츠|흥국|DB|교보|라이나|농협|동양|우체국)", txt):
            ins.add(m)
    if not prod:
        for line in txt.splitlines():
            if ("보험" in line) or ("실손" in line):
                s = line.strip()
                if 3 <= len(s) <= 80:
                    prod.add(s)

    return {
        "insurer": list(ins)[0] if len(ins) == 1 else None,
        "product": list(prod)[0] if len(prod) == 1 else None,
    }

# 2) 분류기 호출: 메시지 구성 방식
def run_classifier_llm(user_text: str,
                       chat_meta: Optional[Dict[str, Any]] = None,
                       entity_hints: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
    """
    최신 발화 우선. Sticky 엔티티 로직은 제거됨.
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
        "5) 엔티티는 NULL을 남발하지 말고, CURRENT_QUESTION에서 추출 가능한 것은 반드시 채웁니다.\n"
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
        "\"text\":\"CURRENT_QUESTION을 1~2문장으로 요약(사용자가 질의한 보험사/상품이 있으면 반드시 포함)\""
        "}\n"
        "반드시 유효한 JSON만 출력하고 여분 텍스트/코드블록을 금지합니다.\n"
    )

    # 기존 요약 유지
    hist_summary = summarize_history_for_context(chat_meta)
    # current에서도 단일 후보를 사전 추출 → LLM이 판단하기 쉽게 노출
    # current_entities = _extract_current_entities(user_text, entity_hints=entity_hints)

    history_block = f"[HISTORY]\n{hist_summary}" if hist_summary else "[HISTORY]\n(없음)"
    # hints_block   = "[HINTS]\n" \
    #                 f"insurers: {', '.join(entity_hints.get('insurers', [])) if entity_hints else '(없음)'}\n" \
    #                 f"products: {', '.join(entity_hints.get('products', [])) if entity_hints else '(없음)'}"
    current_block = "[CURRENT_QUESTION]\n" + (user_text or "").strip()
    # current_probe = "[CURRENT_ENTITIES_PROBED]\n" \
    #                 f"insurer: {current_entities.get('insurer') or '(없음)'}\n" \
    #                 f"product: {current_entities.get('product') or '(없음)'}"

    messages = [
        {"role": "system",    "content": SYSTEM_RULES},
        {"role": "assistant", "content": history_block},
        # {"role": "assistant", "content": hints_block},       # << HINTS 주입
        # {"role": "assistant", "content": current_probe},     # << CURRENT 엔티티 힌트
        {"role": "user",      "content": current_block},
    ]

    # (로깅) 요청 페이로드
    try:
        payload_str = "\n############ [LLM DEBUG] ############\n"
        payload_str += json.dumps(messages, ensure_ascii=False, default=str, indent=2)
    except Exception:
        payload_str = "\n############ [LLM DEBUG] ############\n" + str(messages)
    body_logger.info(payload_str)

    # OpenAI 호출 (예외 가드 + response_format 옵션화)
    try:
        kwargs = {
            "model": CLASSIFIER_MODEL,
            "messages": messages,
            "temperature": 0.0,
        }
        if _supports_json_object(CLASSIFIER_MODEL):
            kwargs["response_format"] = {"type": "json_object"}

        if "gpt-5-mini" not in CLASSIFIER_MODEL.lower():
            kwargs["temperature"] = 0.0

        resp = _client.chat.completions.create(**kwargs)
        content = (resp.choices[0].message.content or "").strip()
        # 파싱, 보정 전 1차 LLM 답변 로깅
        try:
            raw_for_log = content

            # ```json ... ``` 같은 코드펜스 제거 (여기서도 파싱 전에 전처리)
            if raw_for_log.startswith("```"):
                import re as _re
                m = _re.search(r"\{.*\}", raw_for_log, _re.S)
                raw_for_log = m.group(0) if m else raw_for_log

            try:
                parsed = json.loads(raw_for_log)          # 문자열 → 파이썬 객체
                pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
            except Exception:
                # JSON이 아니면 원문 그대로
                pretty = raw_for_log
            body_logger.info("############ [LLM DEBUG 2] ############\n%s", pretty)
        except Exception as e:
            body_logger.info("############ [LLM DEBUG 2 ERROR] ############\n%s", repr(e))

    except Exception as e:
        body_logger.info("\n############ [LLM ERROR] ############\n" + repr(e))
        return {
            "primary_flow": "GENERAL",
            "confidence": 0.2,
            "entities": {
                "insurer": None, "product": None, "version": None,
                "topic": None, "icd10_candidate": None,
                "product_type": None, "focus_topics": [],
            },
            "retrieval_suggestion": "auto",
            "reasons": "openai_error",
            "tags": [],
            "text": user_text or ""
        }

    # JSON 파싱 (방어적)
    raw = content
    if raw.startswith("```"):
        import re as _re
        m = _re.search(r"\{.*\}", raw, _re.S)
        raw = m.group(0) if m else raw

    try:
        result = json.loads(raw)
    except Exception:
        body_logger.info("\n############ [LLM PARSE ERROR] ############\n" + raw)
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

    # # 1) 현재 단일 후보 우선
    # if not insurer and current_entities.get("insurer"):
    #     entities["insurer"] = current_entities["insurer"]
    #     insurer = entities["insurer"]
    # if not product and current_entities.get("product"):
    #     entities["product"]  = current_entities["product"]
    #     product = entities["product"]

    # 3) 힌트에 후보가 1개뿐이라면 최후 보정(드물게)
    if entity_hints:
        hins = entity_hints.get("insurers") or []
        hpro = entity_hints.get("products") or []
        if not insurer and len(hins) == 1:
            entities["insurer"] = hins[0]; insurer = hins[0]
        if not product and len(hpro) == 1:
            entities["product"] = hpro[0]; product = hpro[0]

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

    # (D) 요약 text에 엔티티가 빠지면 보완
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

    result["__ctx"] = {
        "history_summary": hist_summary,          # str | ""
        # "current_entities_probed": current_entities,
        "decision_compact": {                     # Answerer가 한눈에 보도록 요약
            "primary_flow": result.get("primary_flow"),
            "entities": result.get("entities", {}),
            "retrieval_suggestion": result.get("retrieval_suggestion", "auto"),
        },
    }

    # 최종 결과 로그
    try:
        body_logger.info(
            "############ [CLASSIFIER RESULT] ############\n%s",
            json.dumps(result, ensure_ascii=False, default=str, indent=2),
        )
    except Exception as e:
        body_logger.info("############ [CLASSIFIER RESULT LOG ERROR] ############\n%s", repr(e))

    return result

# ================== 최종 Answerer LLM (chat.py 호환) ==================
def run_llm(messages: List[Dict[str, str]]) -> str:
    resp = _client.chat.completions.create(
        model=ANSWERER_MODEL,
        messages=messages,
        # 원래 0.2였는데, 이걸 조정해야되나?
        temperature=0.3,
    )
    return (resp.choices[0].message.content or "").strip()


async def call_llm(messages: List[Dict[str, str]]) -> str:
    return await asyncio.to_thread(run_llm, messages)
