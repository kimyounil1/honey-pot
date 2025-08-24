# app/rag/retriever.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import os
import logging
import boto3

from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from app.services.common import Mode
from app.config import settings
import json
from typing import List, Dict, Any
from starlette.concurrency import run_in_threadpool

# watsonx.ai (pip install ibm-watsonx-ai)
try:
    from ibm_watsonx_ai import Credentials, APIClient
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
    from ibm_watsonx_ai.foundation_models import ModelInference
except Exception:
    Credentials = None
    APIClient = None
    ModelInference = None

logger = logging.getLogger(__name__)
COVERAGE_SYS = """너는 한국 보험 약관/요약서 텍스트에서 보장 항목을 구조화하는 전문가야.
반드시 내가 제공한 coverage_item 이름 목록 중에서만 name을 선택해.
정확히 일치하지 않으면 가장 가까운 항목 1개를 선택하고 notes에 "fuzzy: <원문표현>"을 남겨.
segment는 ['입원','외래','처방','응급'] 중 선택, benefit_type은 ['급여','비급여','선택'] 중 선택.
숫자는 KRW 기준 정수(원) 또는 소수점 2자리. 범위/~ 표기는 단일 수치로 정규화.
JSON 배열만 출력:
[
  {
    "name": "<coverage_item.name 중 하나>",
    "segment": "입원|외래|처방|응급",
    "benefit_type": "급여|비급여|선택",
    "coinsurance_pct": 0.20,
    "deductible_min": 10000,
    "per_visit_limit": 200000,
    "annual_limit": 50000000,
    "combined_cap_group": "코드 or null",
    "combined_cap_amount": 3500000,
    "frequency_limit": 50,
    "frequency_period": "year|contract|null",
    "coverage_order": 10,
    "notes": "설명/주석",
    "source_ref": "근거 구절/페이지"
  }
]
"""

PREMIUM_SYS = """너는 한국 보험 약관/요약서에서 보험료(월보험료) 표를 구조화한다.
문서에 숫자 금액이 명시된 경우만 monthly_premium 채운다(없으면 null).
tier는 문서의 플랜 명칭을 그대로 사용하되 없으면 "standard".
gender는 'M','F','A' 중 하나. 연령대는 표의 구간을 그대로 [age_min, age_max].
JSON 배열만 출력:
[
  {
    "age_min": 20,
    "age_max": 29,
    "gender": "M",
    "smoker": null,
    "tier": "기본형",
    "monthly_premium": 12340.00,
    "currency": "KRW",
    "meta": { "근거": "표 페이지/구절", "비고": "갱신형/산출근거 등" }
  }
]
"""
# ============================= OpenSearch =============================

def _os_client() -> OpenSearch:
    region = getattr(settings, "OPENSEARCH_REGION", os.getenv("OPENSEARCH_REGION", "us-east-1"))
    auth = AWSV4SignerAuth(boto3.Session().get_credentials(), region, "es")
    host = getattr(settings, "OPENSEARCH_HOST", os.getenv("OPENSEARCH_HOST"))
    port = int(getattr(settings, "OPENSEARCH_PORT", os.getenv("OPENSEARCH_PORT", "443")))
    return OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )

def _trim(s: str, n: int = 120) -> str:
    s = (s or "").replace("\n", " ").strip()
    return (s[:n] + "…") if len(s) > n else s

def _search_snippets(query: str, k: int = 8, policy_id: Optional[str] = None) -> List[Dict[str, Any]]:
    index = getattr(settings, "OPENSEARCH_INDEX", None)

    if policy_id:
        filter_block = [{
            "bool": {
                "should": [
                    {"term": {"policy_id": policy_id}}
                ]
            }
        }]

        must_block: List[Dict[str, Any]] = []
        if (query or "").strip():
            must_block.append({
                "multi_match": {
                    "query": query,
                    "fields": ["content^2", "section_title", "embed_input", "text"],
                    "type": "best_fields",
                    "operator": "or",
                }
            })
        else:
            must_block.append({"match_all": {}})

        body: Dict[str, Any] = {
            "size": max(1, min(k, 20)),
            "query": {
                "bool": {
                    "filter": filter_block,
                    "must": must_block,
                }
            },
            "_source": True,
        }
    else:
        body = {
            "size": max(1, min(k, 20)),
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["section_title^2", "content"],
                    "type": "best_fields",
                    "tie_breaker": 0.2
                }
            },
            "_source": True,
        }

    resp = _os_client().search(index=index, body=body)

    # total 파싱(버전에 따라 dict/int 혼재)
    raw_total = (resp.get("hits", {}).get("total", {}) or {})
    if isinstance(raw_total, dict):
        total = int(raw_total.get("value", 0))
    else:
        total = int(raw_total or 0)

    hits = resp.get("hits", {}).get("hits", []) or []

    if not hits:
        # ✅ 검색 0건 로그
        logger.info(
            "[RAG][OS_EMPTY] index=%s total=%d k=%d query=%s",
            index, total, k, _trim(query)
        )
        return []

    out = []
    for h in hits:
        s = h.get("_source", {}) or {}
        out.append({
            "score": h.get("_score", 0.0),
            "section_title": s.get("section_title", "") or "",
            "content": s.get("content", "") or "",
            "filename": s.get("filename", ""),
            "insurer": s.get("insurer", ""),
            "version": s.get("version", ""),
            "policy_id": s.get("policy_id", "") or s.get("policy", ""),
            "effective_date": s.get("effective_date", ""),
        })

    # 검색 결과 요약 로그(상위 1개만 제목 찍기)
    logger.debug(
        "[RAG][OS_OK] index=%s total=%d k=%d top_title=%s query=%s",
        index, total, k, _trim(out[0].get("section_title")), _trim(query)
    )
    return out

# ============================= Token Utils =============================

def _rough_tokens(text: str) -> int:
    """보수 근사(한글 포함): ~1토큰=3문자."""
    if not text:
        return 0
    return max(1, len(text) // 3)

def _wx_model() -> Optional[ModelInference]:
    if ModelInference is None:
        logger.warning("ibm-watsonx-ai SDK not installed.")
        return None

    creds = Credentials(api_key=settings.WATSONX_API_KEY, url=settings.WATSONX_URL)
    _ = APIClient(creds)  # 내부 토크나이저 호출에 필요

    return ModelInference(
        model_id=settings.WATSONX_MODEL_ID,
        credentials=creds,
        space_id=settings.WATSONX_SPACE_ID,
    )

def _wx_token_count(model: Optional[ModelInference], text: str) -> int:
    if not model:
        return _rough_tokens(text)
    try:
        t = model.tokenize(prompt=text, return_tokens=True)
        return len(t.get("result", []))
    except Exception:
        return _rough_tokens(text)

def _fit_snippets_to_limit(
    snippets: List[Dict[str, Any]],
    user_query: str,
    token_limit: int = 30000,
    system_overhead_tokens: int = 600,
    per_snippet_header_tokens: int = 12,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    watsonx 호출 전, RAG 컨텍스트(원문 스니펫) 블록을 10,000 토큰 이내로 구성.
    watsonx 토크나이저 없이 보수 근사 사용.
    """
    header = "[RAG CONTEXT]\n"
    used = _rough_tokens(header) + _rough_tokens(user_query) + system_overhead_tokens
    chosen: List[Dict[str, Any]] = []
    lines: List[str] = [header]

    for s in snippets:
        title = s.get("section_title") or "snippet"
        body = (s.get("content") or "").strip()
        if not body:
            continue
        block = f"- ({title}) {body}"
        need = per_snippet_header_tokens + _rough_tokens(block)

        if used + need > token_limit:
            remain = token_limit - used - per_snippet_header_tokens
            if remain <= 0:
                break
            approx_chars = max(0, remain * 3)
            block = f"- ({title}) {body[:approx_chars]}…"
            need = per_snippet_header_tokens + _rough_tokens(block)
            if used + need > token_limit:
                break

        lines.append(block)
        used += need
        chosen.append(s)

    # 간단 출처
    if chosen:
        labels = []
        for s in chosen:
            parts = []
            if s.get("insurer"): parts.append(str(s["insurer"]))
            if s.get("version"): parts.append(str(s["version"]))
            if s.get("filename"): parts.append(str(s["filename"]))
            if s.get("policy_id"): parts.append(f"#{s['policy_id']}")
            lab = " ".join([p for p in parts if p])
            if lab and lab not in labels:
                labels.append(lab)
        if labels:
            lines.append("🔎 출처: " + " / ".join(labels))

    return "\n".join(lines), chosen

# ============================= watsonx Generator =============================

def _rag_prompt(user_query: str, context_block: str) -> str:
    return (
        "당신은 제공된 컨텍스트만 근거로 답하는 보험 도메인 RAG 어시스턴트입니다.\n"
        "규칙:\n"
        "1) 컨텍스트 밖 지식 사용 금지.\n"
        "2) 금액/한도/면책 등 수치는 인용 근거와 함께 제시.\n"
        "3) 컨텍스트가 부족하면 그 사실을 명시.\n\n"
        f"{context_block}\n\n"
        f"[사용자 질문]\n{user_query}\n\n"
        "출력 형식: 요약 → 근거(글머리표) → 유의사항 → 출처"
    )

def _wx_generate_answer(prompt: str) -> str:
    model = _wx_model()
    if model is None:
        return ""
    try:
        gen_params = {
            GenParams.TEMPERATURE: 0.2,
            GenParams.DECODING_METHOD: "greedy",
            GenParams.REPETITION_PENALTY: 1.05,
            GenParams.STOP_SEQUENCES: [],
        }
        resp = model.generate_text(prompt=prompt, params=gen_params)

        return (resp or "").strip()
    except Exception as e:
        logger.exception("watsonx.ai generation failed: %s", e)
        return ""

# ============================= Public API =============================
def retrieve(
    *,
    mode,
    user_id: str,
    query: str,
    attachment_ids: List[str] | None = None,
    product_id: Optional[str] = None,
    limit: int = 5,
    fallback_to_global: bool = False,
) -> str:
    try:
        if product_id:
            snippets = _search_snippets(query=query, k=limit, policy_id=product_id)
        else:
            snippets = _search_snippets(query=query, k=limit)
        context_block, _ = _fit_snippets_to_limit(
            snippets=snippets,
            user_query=query,
        )
        prompt = _rag_prompt(user_query=query, context_block=context_block)
        print("[RAG AUTO PROMPT END]\n" + prompt)
        answer = _wx_generate_answer(prompt)
        print("[RAG AUTO ANSWER END]\n" + answer)
        if (answer or "").strip():
            # 외부(OpenAI) 폴리싱이 컨텍스트로 사용할 수 있게 명확한 헤더 부여
            return "[RAG AUTO ANSWER]\n" + answer

        # watsonx 실패 시: 원문 컨텍스트라도 반환
        return context_block

    except Exception as e:
        logger.exception("retrieve failed: %s", e)
        return ""
#
from typing import Dict, Any

async def policy_db_lookup(*, mode: Mode, entities: Dict[str, Any], user_text: str) -> str:
    """
    TODO: 실제 약관 DB 직조회 로직으로 교체.
    현재는 빈 문자열을 반환하여 stage에서 RAG 보조를 시도하게 둡니다.
    """
    try:
        return ""
    except Exception as e:
        logger.warning("policy_db_lookup failed: %s", e)
        return ""

# app/rag/retriever.py (하단에 추가)
from typing import List, Dict, Any, Tuple, Optional
import math, json
from starlette.concurrency import run_in_threadpool

MODEL_LIMIT = 20_000           # llama-4 maverick 17B 입력 총 한도
OUTPUT_RESERVE = 8_096          # 출력 토큰 예약 (상황에 따라 조절)
PROMPT_OVERHEAD = 2_000         # 시스템/지시/메타 오버헤드 가정
CONTEXT_BUDGET = MODEL_LIMIT - OUTPUT_RESERVE - PROMPT_OVERHEAD

def _tok_count(s: str) -> int:
    # watson 토크나이저 있으면 정확, 없으면 러프
    m = _wx_model()
    try:
        return _wx_token_count(m, s)
    except Exception:
        return _rough_tokens(s)

def _chunk_to_text(c: Dict[str, Any]) -> str:
    title = (c.get("section_title") or "").strip()
    body  = (c.get("content") or c.get("embed_input") or c.get("text") or "").strip()
    if not body:
        return ""
    return f"### {title}\n{body}" if title else body

def _pack_batches_by_tokens(chunks: List[Dict[str, Any]], budget_tokens: int = CONTEXT_BUDGET) -> List[List[Dict[str, Any]]]:
    """
    조각 리스트를 토큰 예산에 맞춰 여러 배치로 나눕니다.
    """
    batches: List[List[Dict[str, Any]]] = []
    cur: List[Dict[str, Any]] = []
    used = 0
    for c in chunks:
        print("청크를 토큰 예산에서 맞춰서 다시 재배치로 분할")
        t = _chunk_to_text(c)
        if not t:
            continue
        cost = _tok_count(t) + 24  # 헤더 여유치
        if cost > budget_tokens * 0.9:
            # 개별 조각이 너무 큰 경우: 과감히 잘라서 줄이기
            short = t[: max(1, (budget_tokens // 3) * 3)]
            c = dict(c)
            c["content"] = short
            cost = _tok_count(_chunk_to_text(c)) + 24

        if used + cost > budget_tokens and cur:
            batches.append(cur); cur = []; used = 0
        cur.append(c); used += cost

    if cur:
        batches.append(cur)
    return batches

async def _wx_async(prompt: str) -> str:
    return await run_in_threadpool(_wx_generate_answer, prompt)

def extract_json_array(text: str) -> List[Any]:
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, list) else []
    except Exception:
        i, j = text.find("["), text.rfind("]")
        if i >= 0 and j >= i:
            try:
                return json.loads(text[i:j+1])
            except Exception:
                return []
        return []

# ----------------------- MAP (Watson 호출) -----------------------

async def extract_coverage_batched(base_names: List[str], chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    batches = _pack_batches_by_tokens(chunks)
    out: List[Dict[str, Any]] = []
    for b in batches:
        print("========WATSON BATCH 호출==========")
        prompt = _coverage_prompt(base_names, b)   # ← 프롬프트는 문자열
        txt = await _wx_async(prompt)
        arr = extract_json_array(txt)
        # JSON 타입 방어 (숫자 문자열 -> 숫자)
        for it in arr:
            if isinstance(it, dict):
                for k in ("coinsurance_pct","deductible_min","per_visit_limit","annual_limit","combined_cap_amount","frequency_limit","coverage_order"):
                    if k in it and isinstance(it[k], str):
                        try:
                            it[k] = float(it[k]) if "." in it[k] else int(it[k])
                        except Exception:
                            pass
        out.extend([x for x in arr if isinstance(x, dict)])
    return out

async def extract_premiums_batched(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    batches = _pack_batches_by_tokens(chunks)
    out: List[Dict[str, Any]] = []
    for b in batches:
        prompt = _premium_prompt(b)
        txt = await _wx_async(prompt)
        arr = extract_json_array(txt)
        for it in arr:
            if isinstance(it, dict):
                for k in ("age_min","age_max"):
                    if k in it and isinstance(it[k], str):
                        try: it[k] = int(it[k])
                        except: pass
                if "monthly_premium" in it and isinstance(it["monthly_premium"], str):
                    try: it["monthly_premium"] = float(it["monthly_premium"])
                    except: pass
        out.extend([x for x in arr if isinstance(x, dict)])
    return out

# ----------------------- REDUCE (서버 병합) -----------------------

def _merge_num(a, b, mode: str):
    to_num = lambda x: None if x in (None, "", "null") else x
    a, b = to_num(a), to_num(b)
    if a is None: return b
    if b is None: return a
    if mode == "min": return a if a <= b else b
    if mode == "max": return a if a >= b else b
    return a  # default keep

def _concat_notes(*vals: Optional[str]) -> str:
    parts = [v for v in vals if isinstance(v, str) and v.strip()]
    # 중복/길이 방지
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            out.append(p); seen.add(p)
    return " | ".join(out)[:2000]

def reduce_coverage(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    (name, segment, benefit_type, combined_cap_group)로 그룹핑하고
    한도류는 max, 공제/본인부담은 min을 취함. 충돌은 notes에 기록.
    """
    key = lambda d: (
        d.get("name"),
        d.get("segment"),
        d.get("benefit_type"),
        d.get("combined_cap_group"),
    )
    agg: Dict[Tuple, Dict[str, Any]] = {}
    for it in items:
        k = key(it)
        if k not in agg:
            agg[k] = dict(it)
            continue
        cur = agg[k]
        # 규칙 병합
        cur["coinsurance_pct"] = _merge_num(cur.get("coinsurance_pct"), it.get("coinsurance_pct"), "min")
        cur["deductible_min"]  = _merge_num(cur.get("deductible_min"),  it.get("deductible_min"),  "min")
        cur["per_visit_limit"] = _merge_num(cur.get("per_visit_limit"), it.get("per_visit_limit"), "max")
        cur["annual_limit"]    = _merge_num(cur.get("annual_limit"),    it.get("annual_limit"),    "max")
        cur["combined_cap_amount"] = _merge_num(cur.get("combined_cap_amount"), it.get("combined_cap_amount"), "max")
        cur["frequency_limit"] = _merge_num(cur.get("frequency_limit"), it.get("frequency_limit"), "max")

        # coverage_order는 가장 작은(우선순위 높은) 값 유지
        cur["coverage_order"]  = _merge_num(cur.get("coverage_order"), it.get("coverage_order"), "min")

        # source_ref, notes는 합치기
        cur["source_ref"] = _concat_notes(cur.get("source_ref"), it.get("source_ref"))
        cur["notes"]      = _concat_notes(cur.get("notes"), it.get("notes"))

        # currency/period 등 누락 보완
        for f in ("frequency_period", "combined_cap_group"):
            if not cur.get(f) and it.get(f):
                cur[f] = it[f]
    # 리스트 반환(정렬은 coverage_order → name)
    return sorted(agg.values(), key=lambda d: (d.get("coverage_order") or 9999, str(d.get("name") or "")))

def reduce_premiums(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    (age_min, age_max, gender, smoker, tier)로 그룹핑, 월보험료는 값 다르면 평균/최솟값 중 택1.
    여기서는 문서 상 단일표 기준으로 min을 유지(보수적).
    """
    key = lambda d: (d.get("age_min"), d.get("age_max"), d.get("gender"), d.get("smoker"), d.get("tier") or "standard")
    agg: Dict[Tuple, Dict[str, Any]] = {}
    for it in items:
        k = key(it)
        if k not in agg:
            agg[k] = dict(it)
            continue
        cur = agg[k]
        # 금액 충돌 시 더 작은 값 유지(보수적)
        if it.get("monthly_premium") is not None:
            if cur.get("monthly_premium") is None:
                cur["monthly_premium"] = it["monthly_premium"]
            else:
                cur["monthly_premium"] = min(cur["monthly_premium"], it["monthly_premium"])
        # 근거/비고 합치기
        meta = cur.get("meta") or {}
        meta2 = it.get("meta") or {}
        note = _concat_notes(
            (meta.get("비고") if isinstance(meta.get("비고"), str) else None),
            (meta2.get("비고") if isinstance(meta2.get("비고"), str) else None),
        )
        base = _concat_notes(
            (meta.get("근거") if isinstance(meta.get("근거"), str) else None),
            (meta2.get("근거") if isinstance(meta2.get("근거"), str) else None),
        )
        cur["meta"] = {"근거": base, "비고": note}
        # currency 기본값
        if not cur.get("currency"):
            cur["currency"] = it.get("currency") or "KRW"

    return sorted(agg.values(), key=lambda d: (d.get("tier") or "standard", d.get("gender") or "A", d.get("age_min") or 0))

def _chunks_to_context(chunks: List[Dict[str, Any]], max_chars: int = 500_000) -> str:
    """section_title, content/embed_input/text 순으로 문맥 합치기 (중복 제거 포함)."""
    parts: List[str] = []
    for c in chunks:
        title = (c.get("section_title") or "").strip()
        body = (c.get("content") or c.get("embed_input") or c.get("text") or "").strip()
        if not body:
            continue
        if title:
            parts.append(f"### {title}\n{body}")
        else:
            parts.append(body)
    # 중복 제거
    seen, uniq = set(), []
    for p in parts:
        if p not in seen:
            uniq.append(p); seen.add(p)
    ctx = "\n\n".join(uniq)
    return ctx[:max_chars]

def _coverage_prompt(base_names: List[str], chunks: List[Dict[str, Any]]) -> str:
    names_json = json.dumps(base_names, ensure_ascii=False)
    context = _chunks_to_context(chunks)
    return (
        f"{COVERAGE_SYS}\n\n"
        f"[coverage_item.name 목록]\n{names_json}\n\n"
        f"[문서 컨텍스트]\n{context}\n\n"
        "[지시사항]\n"
        "- JSON 배열만 출력. 주석/설명/라벨 금지.\n"
        "- 수치는 KRW 단위. 범위/‘~’ 표기는 단일 수치로 정규화.\n"
        "- 각 항목에 source_ref로 근거 구절/페이지를 남겨."
    )

def _premium_prompt(chunks: List[Dict[str, Any]]) -> str:
    context = _chunks_to_context(chunks)
    return (
        f"{PREMIUM_SYS}\n\n"
        f"[문서 컨텍스트]\n{context}\n\n"
        "[지시사항]\n"
        "- JSON 배열만 출력. 주석/설명/라벨 금지.\n"
        "- 문서에 실제 금액 있을 때만 monthly_premium 채움."
    )
