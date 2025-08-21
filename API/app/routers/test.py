# routers/test.py (추가)

from typing import Any, Dict, List, Optional

import boto3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import asyncio
import logging
import os

from app.config import settings

# 1) OpenSearch 클라이언트 준비
#    - 프로젝트에 이미 공용 클라이언트가 있으면 그걸 import 하세요.
#      예: from app.search.os_client import os_client, OS_INDEX
#    - 없으면 아래 간이 클라이언트를 사용하세요.
try:
    # 공용 클라이언트가 있다면 여기로 교체
    from app.search.os_client import os_client, OS_INDEX  # type: ignore
except Exception:
    from opensearchpy import OpenSearch, AWSV4SignerAuth, RequestsHttpConnection  # pip install opensearch-py

    region = getattr(settings, "OPENSEARCH_REGION", os.getenv("OPENSEARCH_REGION", "us-east-1"))
    auth = AWSV4SignerAuth(boto3.Session().get_credentials(), region, "es")
    host = getattr(settings, "OPENSEARCH_HOST", os.getenv("OPENSEARCH_HOST"))
    port = int(getattr(settings, "OPENSEARCH_PORT", os.getenv("OPENSEARCH_PORT", "443")))
    os_client =  OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )
    OS_INDEX = getattr(settings, "OPENSEARCH_INDEX", None)

logger = logging.getLogger(__name__)
try:
    router  # type: ignore  # 기존 router가 있으면 재사용
except NameError:
    router = APIRouter()  # test.py에 router가 없으면 생성

# ---------- 요청/응답 모델 ----------

class PolicySearchIn(BaseModel):
    policy_id: str = Field(..., description="정확히 이 policy_id로만 필터링")
    query: Optional[str] = Field(None, description="내용 검색어 (없으면 전체에서 최신/기본 순)")
    limit: int = Field(10, ge=1, le=50, description="상위 문서 개수")

class DocOut(BaseModel):
    policy_id: Optional[str] = None
    product_code: Optional[str] = None
    version: Optional[str] = None
    insurer: Optional[str] = None
    filename: Optional[str] = None
    section_title: Optional[str] = None
    chunk_index: Optional[int] = None
    updated_at: Optional[str] = None
    score: Optional[float] = None
    preview: Optional[str] = None

class PolicySearchOut(BaseModel):
    policy_id: str
    query: Optional[str]
    limit: int
    count: int
    sources: List[str]
    sources_str: str
    docs: List[DocOut]

# ---------- 유틸 ----------

def _source_str(d: Dict[str, Any]) -> str:
    insurer = (d.get("insurer") or "").strip()
    version = (d.get("version") or "").strip()
    filename = (d.get("filename") or "").strip()
    policy_id = (d.get("policy_id") or "").strip()
    left = " ".join([s for s in [insurer, version, filename] if s])
    right = f"#{policy_id}" if policy_id else ""
    return " ".join([s for s in [left, right] if s]).strip()

def _pick_preview(d: Dict[str, Any], max_len: int = 400) -> str:
    raw = (d.get("content") or d.get("text") or d.get("embed_input") or "").strip()
    if len(raw) <= max_len:
        return raw
    return raw[: max_len - 3] + "..."

def _build_policy_scoped_body(*, policy_id: str, query: Optional[str], limit: int) -> Dict[str, Any]:
    """
    policy_id만 확실히 필터하고, 그 스코프 안에서 query가 있으면 내용 필드에 매칭.
    - policy_id와 policy_id.keyword 둘 다 should로 넣어 매핑 편차에 견고.
    - query가 없으면 match_all.
    """
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
                "operator": "or"
            }
        })
    else:
        must_block.append({"match_all": {}})

    body = {
        "size": max(1, min(limit, 50)),
        "query": {
            "bool": {
                "filter": filter_block,
                "must": must_block
            }
        },
        "_source": [
            "policy_id","product_code","version","insurer","filename",
            "section_title","chunk_index","updated_at","content","embed_input","text"
        ]
    }
    return body

# ---------- 엔드포인트 ----------

@router.post("/debug/policy-search", response_model=PolicySearchOut, tags=["debug"])
async def debug_policy_search(payload: PolicySearchIn):
    """
    OpenSearch로 **policy_id만 조건으로 고정** + (있다면) query로 내용 검색.
    retriever의 OS 검색 로직과 동일한 흐름이며, 전역(통) 검색은 하지 않음.
    """
    body = _build_policy_scoped_body(
        policy_id=payload.policy_id,
        query=payload.query,
        limit=payload.limit
    )
    try:
        # IO 블로킹을 thread로
        res = await asyncio.to_thread(os_client.search, index=OS_INDEX, body=body)
    except Exception as e:
        logger.exception("OpenSearch policy-scoped search failed")
        raise HTTPException(status_code=500, detail=f"OpenSearch 검색 실패: {e}")

    hits = (res or {}).get("hits", {}).get("hits", []) or []

    docs: List[DocOut] = []
    sources_list: List[str] = []
    seen = set()
    for h in hits:
        src = (h or {}).get("_source", {}) or {}
        score = (h or {}).get("_score", None)
        docs.append(DocOut(
            policy_id=src.get("policy_id"),
            product_code=src.get("product_code"),
            version=src.get("version"),
            insurer=src.get("insurer"),
            filename=src.get("filename"),
            section_title=src.get("section_title"),
            chunk_index=src.get("chunk_index"),
            updated_at=src.get("updated_at"),
            score=score if isinstance(score, (int, float)) else None,
            preview=_pick_preview(src),
        ))
        s = _source_str(src)
        if s and s not in seen:
            sources_list.append(s)
            seen.add(s)

    sources_str = " / ".join(sources_list)
    logger.info(
        "[DEBUG][policy-search] pid=%s | q='%s' | hits=%d | sources=%s",
        payload.policy_id,
        (payload.query or "")[:80],
        len(hits),
        sources_str,
    )

    return PolicySearchOut(
        policy_id=payload.policy_id,
        query=payload.query,
        limit=payload.limit,
        count=len(hits),
        sources=sources_list,
        sources_str=sources_str,
        docs=docs,
    )
