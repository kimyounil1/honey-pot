# app/rag/retriever.py
from __future__ import annotations
from typing import Sequence, List, Dict, Any, Optional, Tuple
import os
import logging
import boto3

from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from app.services.common import Mode
from app.config import settings

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

def _search_snippets(query: str, k: int = 6) -> List[Dict[str, Any]]:
    index = getattr(settings, "OPENSEARCH_INDEX", None)

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
    token_limit: int = 8_000,
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
            GenParams.MAX_NEW_TOKENS: 4000,
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
    mode: Mode,
    user_id: str,
    query: str,
    attachment_ids: Sequence[str] | None,
    k: int = 6,
) -> str:
    """
    Auto-RAG 컨텍스트 생성기:
    - OpenSearch에서 스니펫 검색 → 10,000 토큰 한도로 컨텍스트 구성
    - watsonx가 해당 컨텍스트만으로 초안 답변 생성
    - 생성된 초안 답변을 '[RAG AUTO ANSWER]' 블록으로 반환
    - watsonx 미설치/오류 시, 컨텍스트 블록만 반환(파이프라인 유지)
    """
    try:
        snippets = _search_snippets(query=query, k=k)
        context_block, _ = _fit_snippets_to_limit(
            snippets=snippets,
            user_query=query,
            token_limit=4_000,
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
