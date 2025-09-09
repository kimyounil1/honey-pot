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
import asyncio
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
# body_logger = logging.getLogger("debug.body")

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
        timeout=120,
        max_retries=2,
        retry_on_timeout=True,
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
    logger.info(out)
    # 검색 결과 요약 로그(상위 1개만 제목 찍기)
    logger.debug(
        "[RAG][OS_OK] index=%s total=%d k=%d top_title=%s query=%s",
        index, total, k, _trim(out[0].get("section_title")), _trim(query)
    )
    return out

def _search_user_knowledge(query: str, k: int, user_id: Optional[int | str]) -> List[Dict[str, Any]]:
    """Search user-specific knowledge (indexed from uploads) for the given user_id."""
    try:
        if not user_id:
            return []
        index = getattr(settings, "OPENSEARCH_INDEX", None)
        uid = int(user_id) if isinstance(user_id, (int, str)) and str(user_id).isdigit() else None
        if uid is None:
            return []
        body: Dict[str, Any] = {
            "size": max(1, min(k, 20)),
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"doc_type": "user_knowledge"}},
                        {"term": {"user_id": uid}},
                    ],
                    "must": [
                        {"multi_match": {"query": query, "fields": ["content^3", "section_title^2", "entry"], "type": "best_fields"}}
                    ],
                }
            },
            "_source": True,
        }
        resp = _os_client().search(index=index, body=body)
        hits = resp.get("hits", {}).get("hits", []) or []
        out: List[Dict[str, Any]] = []
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
        if not out:
            logger.debug("[RAG][UK_EMPTY] user_id=%s query=%s", uid, _trim(query))
        else:
            logger.debug("[RAG][UK_OK] user_id=%s top_title=%s", uid, _trim(out[0].get("section_title")))
        return out
    except Exception as e:
        logger.warning("[RAG][UK_ERROR] search failed: %s", e)
        return []

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

def _rag_prompt(user_query: str, context_block: str, history_summary: str = "") -> str:
    history_sec = f"[HISTORY]\n{history_summary}\n\n" if history_summary else ""
    # 최신 질문 맨 끝 + 우선순위 규칙 명시
    return (
        "당신은 제공된 컨텍스트만 근거로 답하는 보험 도메인 RAG 어시스턴트입니다.\n"
        "규칙:\n"
        "1) HISTORY/컨텍스트는 참고용이다. CURRENT_QUESTION과 충돌하면 CURRENT_QUESTION을 우선한다.\n"
        "2) 금액/한도/면책 수치는 반드시 인용 근거와 함께 제시.\n"
        "3) 컨텍스트가 부족하면 부족함을 명시.\n\n"
        f"{history_sec}"
        f"{context_block}\n\n"
        f"[CURRENT_QUESTION]\n{user_query}\n\n"
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
        # 1) (검색은 최신 질문만 사용) 스니펫 수집
        snippets: List[Dict[str, Any]] = []
        # 1-a) 사용자 업로드 지식 우선 병합 (있으면 상단에 위치)
        try:
            user_snips = _search_user_knowledge(query=query, k=max(1, min(limit, 8)), user_id=user_id)
        except Exception:
            user_snips = []
        if product_id:
            try:
                snippets = _search_snippets(query=query, k=limit, policy_id=product_id)
            except Exception as e:
                logger.error("[RAG][OS_ERROR] policy_id=%s search failed: %s", str(product_id), e)
                # 옵션: 글로벌로 폴백 시도
                if fallback_to_global:
                    try:
                        snippets = _search_snippets(query=query, k=limit)
                    except Exception:
                        snippets = []
                else:
                    snippets = []
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
                try:
                    snippets = _search_snippets(query=query, k=limit, policy_ids=policy_ids)
                except Exception as e:
                    logger.error("[RAG][OS_ERROR] user policies search failed: %s", e)
                    if fallback_to_global:
                        try:
                            snippets = _search_snippets(query=query, k=limit)
                        except Exception:
                            snippets = []
                    else:
                        snippets = []
            elif fallback_to_global:
                snippets = _search_snippets(query=query, k=limit)
        else:
            snippets = _search_snippets(query=query, k=limit)

        # 병합: 사용자 업로드 지식을 컨텍스트 상단에 배치하여 최신/개인 맥락을 우선
        if user_snips:
            snippets = user_snips + snippets

        # 2) watsonx 토큰 예산 내로 컨텍스트 패킹
        context_block, _ = _fit_snippets_to_limit(
            snippets=snippets,
            user_query=query,
        )

        # 3) 과거 대화 요약을 HISTORY로
        history_summary = await summarize_prev_chats_for_context(prev_chats)

        # 4) 프롬프트 구성: [HISTORY] → [RAG CONTEXT] → [CURRENT_QUESTION]
        #    (충돌 시 최신 질문 우선 규칙을 system에 이미 명시)
        prompt = _rag_prompt(
            user_query=query,
            context_block=context_block + (db_context or ""),
            history_summary=history_summary
        )

        logger.info("\n[RAG AUTO PROMPT END]\n" + str(prompt)[:500] + ("... (truncated)" if len(str(prompt)) > 500 else ""))

        # 5) 생성 (watsonx 호출에 타임아웃 가드)
        try:
            wx_timeout = int(os.getenv("WATSONX_TIMEOUT", "120"))  # seconds
        except Exception:
            wx_timeout = 120
        try:
            answer = await asyncio.wait_for(_wx_async(prompt), timeout=wx_timeout)
        except asyncio.TimeoutError:
            logger.error("[RAG][WX_TIMEOUT] generation exceeded %ss (user_id=%s)", wx_timeout, str(user_id))
            answer = ""
        logger.info("\n[RAG AUTO ANSWER END]\n%s", str(answer)[:500] + ("... (truncated)" if len(str(answer)) > 500 else ""))

        if (answer or "").strip():
            return "[RAG AUTO ANSWER]\n" + answer

        # watsonx 실패 시: 원문 컨텍스트라도 반환
        return context_block

    except Exception as e:
        logger.exception("retrieve failed: %s", e)
        return ""

from typing import Dict, Any

# 부정감지기
def _detect_excluded_types_ko(q: str) -> list[str]:
    q = (q or "")
    pairs = [
        ("실손", ["실손", "실비", "실손의료비"]),
        ("암보험", ["암보험", r"\b암\b"]),
        ("운전자", ["운전자"]),
        ("치아", ["치아"]),
        ("종신", ["종신"]),
        ("정기", ["정기"]),
        ("어린이", ["어린이"]),
        ("간병", ["간병"]),
    ]
    neg_trigs = ["아닌", "제외", "빼고", "말고", "말곤", "제외하고"]
    out = set()
    import re
    for norm, kws in pairs:
        hit = any(re.search(k, q) for k in kws)
        neg = any(t in q for t in neg_trigs)
        if hit and neg:
            out.add(norm)
        for k in kws:
            if re.search(fr"{k}.*(아닌|말고|제외|빼고)", q):
                out.add(norm)
            if re.search(fr"(아닌|말고|제외|빼고).*\b{k}\b", q):
                out.add(norm)
    return list(out)


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

                # 추천 후보 (user_id=1)
                res = await session.execute(
                    select(InsurancePolicy).where(InsurancePolicy.user_id == 1)
                )
                candidates = res.scalars().all()
                if not candidates:
                    return ""
                
                # (1) 1차 LLM이 넘긴 엔티티에서 제외 세트 확보
                excluded = set()
                if isinstance(entities, dict):
                    for x in (entities.get("exclude_product_types") or []):
                        if isinstance(x, str) and x.strip():
                            excluded.add(x.strip())

                # (2) 유저 문장으로도 보강(1차가 못 잡았더라도)
                excluded |= set(_detect_excluded_types_ko(user_text))

                # 사용자가 특정 유형을 요청하면 후보를 해당 유형으로 우선 제한
                # 1) LLM 분류 엔티티 우선
                target_type = (entities.get("product_type") or "").strip() if isinstance(entities, dict) else ""
                # 제외목록과 충돌시 target_type을 확정하지 않음
                if target_type and target_type in excluded:
                    target_type = ""

                # 2) 휴리스틱 보강: 사용자 문구에서 유형 키워드 감지
                if not target_type:
                    qtxt = (user_text or "")
                    if "실손" in qtxt or "실비" in qtxt or "실손의료비" in qtxt:
                        if "실손" not in excluded: target_type = "실손"
                    elif "암보험" in qtxt or ("암" in qtxt and "보험" in qtxt):
                        if "암보험" not in excluded: target_type = "암보험"
                    elif "운전자" in qtxt:
                        if "운전자" not in excluded: target_type = "운전자"
                    elif "치아" in qtxt:
                        if "치아" not in excluded: target_type = "치아"
                    elif "종신" in qtxt:
                        if "종신" not in excluded: target_type = "종신"
                    elif "정기" in qtxt:
                        if "정기" not in excluded: target_type = "정기"
                    elif "어린이" in qtxt:
                        if "어린이" not in excluded: target_type = "어린이"
                    elif "간병" in qtxt:
                        if "간병" not in excluded: target_type = "간병"

                def _ptype_val(v):
                    return (getattr(v, "value", v) or "")
                
                # 제외를 먼저 적용
                if excluded:
                    candidates = [c for c in candidates if _ptype_val(c.product_type) not in excluded]

                # 후보를 요청 유형으로 필터링(있을 때만 적용; 없으면 전체 유지)
                if target_type:
                    typed = [c for c in candidates if _ptype_val(c.product_type) == target_type]
                    if typed:
                        candidates = typed
                    else:
                        # 요청한 유형이 DB 후보에 아예 없는 경우: 명시적으로 빈 표식 반환
                        return "[DB RECOMMENDATION_EMPTY]\nproduct_type: " + target_type

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

                recs = []
                logger.info("\n[candidates]\n"+str(candidates))
                for cand in candidates:
                    # 적합도(Fit)
                    fit = 0.0
                    if target_type and _ptype_val(cand.product_type) == target_type:
                        # 요청 유형과 완전 일치 시 가산
                        fit = 1.0

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
                top = recs[:10]
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

                    detail = ", ".join([p for p in parts if p])

                    # source_ref는 문자열로 보관되므로 문자 단위 join을 하지 말 것
                    ref = f" [근거: {cov.source_ref}]" if cov.source_ref else ""

                    # coverage 항목명(name)을 함께 표기해 상충/중복을 쉽게 식별
                    prefix = f"- {pol_id}: "
                    if name and detail:
                        lines.append(f"{prefix}{name}, {detail}{ref}")
                    elif name:
                        lines.append(f"{prefix}{name}{ref}")
                    else:
                        lines.append(f"{prefix}{detail}{ref}")

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
    logger.info("\n[name_groups]"+str(name_groups))
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

async def summarize_prev_chats_for_context(prev_chats: Optional[List[str]], max_chars: int = 1200) -> str:
    """
    과거 대화를 1~2문장으로 요약해 HISTORY 블록에 넣는다.
    watsonx 호출 실패 시, 최근 몇 줄을 추출식으로 합쳐 짧게 자른다.
    """
    if not prev_chats:
        return ""
    raw = "\n".join(str(x).strip() for x in prev_chats if x).strip()
    raw = raw[:max_chars]

    prompt = (
        "다음 대화 로그를 1~2문장으로 요약하세요. 핵심 의도/주제만 간결히:\n"
        "<<LOG>>\n" + raw + "\n<<END>>\n"
        "출력: 한국어 1~2문장. 불릿/코드/머리글 금지."
    )
    try:
        try:
            wx_timeout = int(os.getenv("WATSONX_TIMEOUT", "120"))
        except Exception:
            wx_timeout = 120
        txt = await asyncio.wait_for(_wx_async(prompt), timeout=wx_timeout)
        out = (txt or "").strip()
        # 과도한 포맷 방지
        out = out.replace("\n", " ").strip()
        # 너무 길면 컷
        return out[:400]
    except Exception:
        # 폴백: 최근 3줄만 압축
        lines = [l for l in raw.splitlines() if l.strip()]
        tail = " ".join(lines[-3:]) if lines else ""
        return tail[:300]

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
    logger.info("\n[agg.values]\n"+str(agg.values()))
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
