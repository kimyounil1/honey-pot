# app/rag/retriever.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import os
import logging
import boto3
import json, re
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from app.services.common import Mode
from app.config import settings
from typing import List, Dict, Any
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models import (
    InsurancePolicy,
    PolicyCoverage,
    CoverageItemWeight,
    PolicyPremium,
    ComplementarityRules,
    CoverageItem,
)
from typing import List, Optional
from sqlalchemy import MetaData, Table, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
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
coverage_order는 int형(정수)로 문서의 UI/설명을 표시하는 순서.
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
    "coverage_order": 1,
    "notes": "설명/주석",
    "source_ref": "근거 구절/페이지"
  }
]
"""

PREMIUM_SYS = """너는 한국 보험 약관/요약서에서 보험료(월보험료) 표를 구조화한다.
문서에 숫자 금액이 명시된 경우만 monthly_premium 채운다(없으면 null).
tier는 문서의 플랜 명칭을 그대로 사용하되 없으면 "standard".
smoker는 BOOLEAN값으로 리턴 TRUE,FALSE
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

POLICY_META_SYS = """너는 한국 보험 약관/요약서에서 상품 메타데이터를 구조화하는 전문가야.
'출력은 오직 JSON 배열 하나. 키는 정확히 다음만 사용(대소문자 포함, 추가/누락/다른 케이스 금지): '
'["product_type","renewal_type","waiting_period_days","age_min","age_max","gender_allowed","is_catalog","attrs"]'
JSON 배열 하나만 출력하고, 객체는 다음 키를 포함해야 해:
{
  "product_type": "암보험|실손|운전자|종신|정기|치아|어린이|간병|기타",
  "renewal_type": "비갱신|연만기갱신|3년갱신|5년갱신|기타",
  "waiting_period_days": 90,
  "age_min": 0,
  "age_max": 100,
  "gender_allowed": "M|F|A",
  "is_catalog": false,
  "attrs": {"키": "값"}
}
값이 없으면 null로 남겨.
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
        timeout=30,
    )

def _trim(s: str, n: int = 120) -> str:
    s = (s or "").replace("\n", " ").strip()
    return (s[:n] + "…") if len(s) > n else s

def _search_snippets(query: str, k: int = 8, policy_id: Optional[str] = None, policy_ids: Optional[List[str]] = None,) -> List[Dict[str, Any]]:
    index = getattr(settings, "OPENSEARCH_INDEX", None)

    must_block: List[Dict[str, Any]] = []
    if (query or "").strip():
        must_block.append(
            {
                "multi_match": {
                    "query": query,
                    "fields": ["content^2", "embed_input", "text"],
                    "type": "best_fields",
                    "operator": "or",
                }
            }
        )
    else:
        must_block.append({"match_all": {}})

    filter_block = []
    if policy_id:
        filter_block.append({"term": {"policy_id": policy_id}})
    elif policy_ids:
        filter_block.append({"terms": {"policy_id": policy_ids}})

    if policy_id or policy_ids:
        body: Dict[str, Any] = {
            "size": max(1, min(k, 20)),
            "query": {"bool": {"filter": filter_block, "must": must_block}},
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
                    "tie_breaker": 0.2,
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
    print(out)
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
        "당신은 제공된 컨텍스트만 근거로 답하는 보험 도메인 RAG 어시스턴트입니다. 단계별 설명은 생략하고 출력 형식의 내용을 자세하게 적어줘\n"
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
            GenParams.MAX_NEW_TOKENS: 8000,
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
async def retrieve(
    *,
    mode,
    user_id: str,
    query: str,
    prev_chats: List[str] | None = None,
    product_id: Optional[str] = None,
    limit: int = 20,
    fallback_to_global: bool = False,
    db_context: str | None = None,
) -> str:
    try:
        snippets: List[Dict[str, Any]] = []
        if product_id:
            snippets = _search_snippets(query=query, k=limit, policy_id=product_id)
        elif user_id:
            user_id_int = int(user_id) if user_id and user_id.isdigit() else 0
            policy_ids: List[str] = []
            if user_id_int:
                async with AsyncSessionLocal() as session:
                    res = await session.execute(
                        select(InsurancePolicy.policy_id).where(
                            InsurancePolicy.user_id == user_id_int
                        )
                    )
                    policy_ids = [pid for pid in res.scalars().all() if pid]

            if policy_ids:
                snippets = _search_snippets(
                    query=query, k=limit, policy_ids=policy_ids
                )
            elif fallback_to_global:
                snippets = _search_snippets(query=query, k=limit)
        else:
            snippets = _search_snippets(query=query, k=limit)

        context_block, _ = _fit_snippets_to_limit(
            snippets=snippets,
            user_query=query,
        )
        prompt = _rag_prompt(
            user_query=query, context_block=context_block + (db_context or "")
        )
        print("[RAG AUTO PROMPT END]\n" + prompt)
        answer = await _wx_async(prompt)
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

async def policy_db_lookup(*, mode: Mode, entities: Dict[str, Any], user_text: str, user_id: int) -> str:
    """DB lookups for recommendation or refund modes."""
    try:
        async with AsyncSessionLocal() as session:
            if mode == Mode.RECOMMEND:
                # 보유 보험 조회
                res = await session.execute(
                    select(InsurancePolicy).where(InsurancePolicy.user_id == user_id)
                )
                user_pols = res.scalars().all()
                if not user_pols:
                    return ""

                # 추천 후보 (user_id=1)
                res = await session.execute(
                    select(InsurancePolicy).where(InsurancePolicy.user_id == 1)
                )
                candidates = res.scalars().all()
                if not candidates:
                    return ""

                # 후보 보험료 평균 계산
                prem_res = await session.execute(
                    select(
                        PolicyPremium.policy_id,
                        func.avg(PolicyPremium.monthly_premium).label("avg_prem"),
                    )
                    .where(PolicyPremium.policy_id.in_([p.id for p in candidates]))
                    .group_by(PolicyPremium.policy_id)
                )
                avg_prem = {pid: float(v) for pid, v in prem_res}
                min_prem = min(avg_prem.values()) if avg_prem else 0.0
                max_prem = max(avg_prem.values()) if avg_prem else 0.0

                target_type = entities.get("product_type")
                recs = []
                print(candidates)
                for cand in candidates:
                    # 적합도(Fit)
                    fit = 0.0
                    if target_type and cand.product_type == target_type:
                        fit = 0.6

                    # 보장(Coverage)
                    cov_res = await session.execute(
                        select(CoverageItemWeight.weight).join(
                            PolicyCoverage,
                            CoverageItemWeight.coverage_item_id
                            == PolicyCoverage.coverage_item_id,
                        ).where(
                            PolicyCoverage.policy_id == cand.id,
                            CoverageItemWeight.product_type == cand.product_type,
                        )
                    )
                    weights = [float(w) for (w,) in cov_res]
                    coverage = sum(weights) / len(weights) if weights else 0.0

                    # 가격(Price)
                    p = avg_prem.get(cand.id)
                    if p is not None and max_prem > min_prem:
                        price = (max_prem - p) / (max_prem - min_prem)
                    else:
                        price = 0.5

                    # TODO : 추후에 보험 신용도/인지도 점수  추가해서 가중치 적용 현재 0.5 고정
                    trust = 0.5  # 고정값

                    # 보완성(Complementarity)
                    comps: List[float] = []
                    for up in user_pols:
                        c_res = await session.execute(
                            select(ComplementarityRules.effect).where(
                                ComplementarityRules.src_product_type == up.product_type,
                                ComplementarityRules.dst_product_type == cand.product_type,
                            )
                        )
                        eff = c_res.scalar()
                        if eff is not None:
                            comps.append(float(eff))
                    comp_raw = sum(comps) / len(comps) if comps else 0.0
                    complementarity = (comp_raw + 1) / 2

                    score = (fit + coverage + price + trust + complementarity) / 5
                    recs.append(
                        {
                            "policy": cand,
                            "score": score,
                            "fit": fit,
                            "coverage": coverage,
                            "price": price,
                            "trust": trust,
                            "complementarity": complementarity,
                        }
                    )

                recs.sort(key=lambda r: r["score"], reverse=True)
                top = recs[:3]
                lines = ["[DB RECOMMENDATION]"]
                for idx, r in enumerate(top, 1):
                    pol = r["policy"]
                    ptype = getattr(pol.product_type, "value", pol.product_type) or ""
                    lines.append(
                        f"{idx}. {ptype} ({pol.policy_id or ''}) score {r['score']:.2f} - "
                        f"Fit {r['fit']:.2f}, Coverage {r['coverage']:.2f}, Price {r['price']:.2f}, "
                        f"Trust {r['trust']:.2f}, Complementarity {r['complementarity']:.2f}"
                    )
                return "\n".join(lines)
            elif mode == Mode.REFUND:
                res = await session.execute(
                    select(InsurancePolicy.policy_id).where(InsurancePolicy.user_id == user_id)
                )
                pol_id = res.scalar()
                if pol_id is None:
                    return ""
                res = await session.execute(
                    select(InsurancePolicy.id).where(InsurancePolicy.policy_id == pol_id).order_by(InsurancePolicy.id)
                )
                policy_id = res.scalar()
                if policy_id is None:
                    return ""

                res = await session.execute(
                    select(PolicyCoverage)
                    .options(selectinload(PolicyCoverage.coverage_item))
                    .where(PolicyCoverage.policy_id == policy_id)  # pol.id를 조건으로 사용
                    .order_by(PolicyCoverage.coverage_order)
                )
                covs = res.scalars().all()
                if not covs:
                    return ""
                lines = ["[DB COVERAGE]"]
                for cov in covs:
                    name = getattr(cov.coverage_item, "name", "") or ""
                    parts: List[str] = []
                    if cov.segment:
                        parts.append(cov.segment)
                    if cov.benefit_type:
                        parts.append(cov.benefit_type)
                    if cov.coinsurance_pct is not None:
                        parts.append(f"자기부담 {float(cov.coinsurance_pct) * 100:.0f}%")
                    if cov.deductible_min is not None:
                        parts.append(f"공제 {int(cov.deductible_min):,}원")
                    if cov.per_visit_limit is not None:
                        parts.append(f"1회 {int(cov.per_visit_limit):,}원")
                    if cov.annual_limit is not None:
                        parts.append(f"연간 {int(cov.annual_limit):,}원")
                    if cov.frequency_limit is not None:
                        period = "연" if cov.frequency_period == "year" else "계약"
                        parts.append(f"횟수 {cov.frequency_limit}회/{period}")

                    detail = ", ".join(parts)

                    ref = f" [근거: {', '.join(cov.source_ref)}]" if cov.source_ref else ""

                    lines.append(f"- {pol_id}: {detail}{ref}")

                return "\n".join(lines)
            else:
                return ""
    except Exception as e:
        logger.warning("policy_db_lookup failed: %s", e)
        return ""

# app/rag/retriever.py (하단에 추가)
from typing import List, Dict, Any, Tuple, Optional
import math, json
from starlette.concurrency import run_in_threadpool

MODEL_LIMIT = 91_072           # llama-4 maverick 17B 총 입력 한도
OUTPUT_RESERVE = 8_096          # 출력 토큰 예약 (상황에 따라 조절)
PROMPT_OVERHEAD = 2_000         # 시스템/지시/메타 오버헤드 가정
CONTEXT_BUDGET = 20_000         # 문맥 청크에 허용할 토큰 수
NAME_BUDGET = MODEL_LIMIT - OUTPUT_RESERVE - PROMPT_OVERHEAD - CONTEXT_BUDGET

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

def _materialize_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """각 청크에 _text, _approx_tok 필드를 부여"""
    out: List[Dict[str, Any]] = []
    for c in chunks:
        t = _chunk_to_text(c)
        if not t:
            continue
        m = dict(c)  # 얕은 복사
        m["_text"] = t
        m["_approx_tok"] = max(1, len(t) // 3)  # 로컬 근사치
        out.append(m)
    return out

def _shrink_text_by_chars(text: str, target_tokens: int) -> str:
    # 근사치: 1토큰≈3문자 → 여유를 두고 2.8로 나눔
    max_chars = int(target_tokens * 2.8)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…"

def _pack_batches_by_tokens(chunks: List[Dict[str, Any]], budget_tokens: int = CONTEXT_BUDGET) -> List[List[Dict[str, Any]]]:
    """네트워크 토크나이저 호출 없이, 근사 토큰으로만 배치 구성"""
    mats = _materialize_chunks(chunks)  # _text, _approx_tok 포함
    batches: List[List[Dict[str, Any]]] = []
    cur: List[Dict[str, Any]] = []
    used = 0

    for m in mats:
        cost = m["_approx_tok"] + 24  # 헤더 여유치
        # 개별 청크가 과도하게 크면 잘라서 삽입
        if cost > int(budget_tokens * 0.9):
            short = _shrink_text_by_chars(m["_text"], int(budget_tokens * 0.9))
            m = dict(m)
            m["_text"] = short
            m["_approx_tok"] = max(1, len(short) // 3)
            cost = m["_approx_tok"] + 24

        if used + cost > budget_tokens and cur:
            batches.append(cur); cur = []; used = 0
        cur.append(m); used += cost

    if cur:
        batches.append(cur)
    return batches

def _pack_name_groups(names: List[str], budget_tokens: int = NAME_BUDGET) -> List[List[str]]:
    groups, cur, used = [], [], 0
    for n in names:
        # json.dumps 대신 길이 기반 근사 (문자/3 + 쉼표 여유치)
        t = max(1, len(n) // 3) + 1
        if used + t > budget_tokens and cur:
            groups.append(cur); cur, used = [], 0
        cur.append(n); used += t
    if cur:
        groups.append(cur)
    return groups

async def _wx_async(prompt: str) -> str:
    return await run_in_threadpool(_wx_generate_answer, prompt)

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

def _sanitize_json_like(s: str) -> str:
    # 흔한 오류: trailing comma 제거
    s = re.sub(r",\s*(\]|\})", r"\1", s)
    # 제어문자 제거(가끔 들어오는 0-width 등)
    s = "".join(ch for ch in s if ch.isprintable() or ch in "\n\r\t")
    return s.strip()

def _match_json_array(s: str, start: int) -> Optional[str]:
    """start가 가리키는 '['에서 시작해 문자열/이스케이프를 고려해
    균형이 맞는 첫 배열만 잘라 반환. 없으면 None."""
    depth = 0
    i = start
    in_str = False
    esc = False
    while i < len(s):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    return s[start:i+1]
        i += 1
    return None

def _first_json_array_anywhere(s: str) -> Optional[List[Any]]:
    idx = s.find('[')
    while idx != -1:
        cand = _match_json_array(s, idx)
        if cand:
            txt = _sanitize_json_like(cand)
            try:
                obj = json.loads(txt)
                if isinstance(obj, list):
                    return obj
            except Exception:
                pass
        idx = s.find('[', idx + 1)
    return None

def extract_json_array(text: str) -> List[Any]:
    """모델이 앞에 설명을 붙이거나 fenced code block을 쓰는 경우도 안전하게 배열만 추출"""
    if not isinstance(text, str):
        return []

    # 1) 코드 펜스 우선 (```json ... ``` 또는 ``` ... ```)
    for m in _CODE_FENCE_RE.finditer(text):
        block = _sanitize_json_like(m.group(1))
        # 블록 자체가 배열이면 바로
        try:
            obj = json.loads(block)
            if isinstance(obj, list):
                return obj
        except Exception:
            # 블록 안에 여러 내용이 섞였으면 배열만 다시 찾기
            arr = _first_json_array_anywhere(block)
            if arr is not None:
                return arr

    # 2) 문서 전체에서 첫 완결 배열만 추출
    arr = _first_json_array_anywhere(text)
    if arr is not None:
        return arr

    # 3) 마지막 시도: 앞뒤 토막 제거 후 재시도
    i, j = text.find('['), text.rfind(']')
    if i >= 0 and j >= i:
        try:
            return json.loads(_sanitize_json_like(text[i:j+1])) or []
        except Exception:
            return []

    return []

# ----------------------- MAP (Watson 호출) -----------------------

async def extract_coverage_batched(base_names: List[str], chunks: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    name_groups = _pack_name_groups(base_names)
    print(name_groups)
    out: List[Dict[str, Any]] = []
    for names in name_groups:
        for b in chunks:
            prompt = _coverage_prompt(names, b)
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

async def extract_premiums_batched(chunks: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    batches = chunks
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
    # print(lambda d: (d.get("coverage_order") or 9999, str(d.get("name") or "")))
    print(agg.values())
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

def _chunks_to_context(chunks: List[Dict[str, Any]], max_chars: int = 100_000) -> str:
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

async def extract_policy_meta(chunks: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
    flat = [c for b in chunks for c in b]
    prompt = _policy_meta_prompt(flat)
    txt = await _wx_async(prompt)
    arr = extract_json_array(txt)
    for it in arr:
        if isinstance(it, dict):
            for k in ("waiting_period_days", "age_min", "age_max"):
                if k in it and isinstance(it[k], str):
                    try: it[k] = int(it[k])
                    except: it[k] = None
            if "is_catalog" in it and isinstance(it["is_catalog"], str):
                it["is_catalog"] = it["is_catalog"].lower() in {"true", "1", "yes"}
            return it
    return {}

def _policy_meta_prompt(chunks: List[Dict[str, Any]]) -> str:
    context = _chunks_to_context(chunks)
    return (
        f"{POLICY_META_SYS}\n\n"
        f"[문서 컨텍스트]\n{context}\n\n"
        "[지시사항]\n"
        "- JSON 배열만 출력. 주석/설명/라벨 금지."
    )
