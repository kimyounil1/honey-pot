from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth, helpers
import boto3

from app.config import settings

logger = logging.getLogger(__name__)


_oa_client = OpenAI()


def _os_client() -> OpenSearch:
    region = getattr(settings, "OPENSEARCH_REGION", "us-east-1")
    host = settings.OPENSEARCH_HOST
    # Prefer AWS SigV4 if credentials available, else basic auth
    creds = boto3.Session().get_credentials()
    if creds is not None:
        auth = AWSV4SignerAuth(creds, region, "es")
    else:
        auth = (settings.OPENSEARCH_USERNAME, settings.OPENSEARCH_PASSWORD)

    return OpenSearch(
        hosts=[{"host": host, "port": int(getattr(settings, "OPENSEARCH_PORT", 443))}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=int(getattr(settings, "OPENSEARCH_CLIENT_TIMEOUT", 120)),
        max_retries=int(getattr(settings, "OPENSEARCH_MAX_RETRIES", 3)),
        retry_on_timeout=True,
        http_compress=True,
    )


KNOWLEDGE_SYS = (
    "당신은 보험 청구/심사 내역을 구조화하는 전문가입니다.\n"
    "첨부된 문서(이미지 또는 텍스트)에서 상담과 판단에 유용한 '엔트리'를 추출하세요.\n"
    "각 엔트리는 다음 키를 포함하는 JSON 객체입니다.\n"
    "{\n"
    "  \"entry_kind\": \"claim|assessment|communication|eob|other\",\n"
    "  \"title\": \"짧은 요약 제목\",\n"
    "  \"summary\": \"핵심 요약(1~2문장)\",\n"
    "  \"key_points\": [\"핵심 포인트\"],\n"
    "  \"amounts\": {\"claimed\": null, \"approved\": null, \"deductible\": null},\n"
    "  \"codes\": [\"진단/수가/내부코드 등\"],\n"
    "  \"dates\": {\"service_date\": null, \"decision_date\": null},\n"
    "  \"decision\": \"approved|partial|denied|pending|null\",\n"
    "  \"reason\": \"승인/부지급 사유 요약(있으면)\",\n"
    "  \"errors\": [\"명백한 오류/누락 의심\"],\n"
    "  \"suggestions\": [\"추가 청구/보완 제안\"]\n"
    "}\n"
    "반드시 JSON 배열(list)만 출력하세요. 주석, 라벨, 코드블록 금지. 숫자는 KRW 기준 정수로, 없으면 null."
)


def _json_array_or_empty(text: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(text)
        if isinstance(data, list):
            # only keep dict items
            return [d for d in data if isinstance(d, dict)]
        if isinstance(data, dict):
            return [data]
    except Exception:
        pass
    return []


def analyze_text_with_gpt4o(text: str) -> List[Dict[str, Any]]:
    if not (text or "").strip():
        return []
    prompt = (
        f"[문서]\n{text[:120000]}\n\n"
        "위 문서만으로 엔트리 JSON 배열을 생성하세요."
    )
    resp = _oa_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": KNOWLEDGE_SYS},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        response_format={"type": "json_object"} if "gpt-4o" in "gpt-4o" else None,
    )
    raw = (resp.choices[0].message.content or "").strip()
    # If response_format is json_object, model may return an object with a key. Try to unwrap common patterns.
    items = _json_array_or_empty(raw)
    if items:
        return items
    # Try to extract JSON array inside text
    try:
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1 and end > start:
            return _json_array_or_empty(raw[start:end+1])
    except Exception:
        pass
    return []


def analyze_image_with_gpt4o(img_bytes: bytes, mime: str = "image/png") -> List[Dict[str, Any]]:
    if not img_bytes:
        return []
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    data_url = f"data:{mime};base64,{b64}"
    messages = [
        {"role": "system", "content": KNOWLEDGE_SYS},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "이미지에서 엔트리 JSON 배열을 생성하세요."},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        },
    ]
    resp = _oa_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.0,
    )
    raw = (resp.choices[0].message.content or "").strip()
    items = _json_array_or_empty(raw)
    if items:
        return items
    try:
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1 and end > start:
            return _json_array_or_empty(raw[start:end+1])
    except Exception:
        pass
    return []


def index_assessment_entries(entries: List[Dict[str, Any]], meta: Dict[str, Any]) -> int:
    if not entries:
        return 0

    client = _os_client()
    index = settings.OPENSEARCH_INDEX
    pipeline = getattr(settings, "OPENSEARCH_PIPELINE", None)

    actions: List[Dict[str, Any]] = []
    for i, e in enumerate(entries):
        title = (e.get("title") or "").strip() or "Entry"
        summary = (e.get("summary") or "").strip()
        # Assemble a searchable content block
        key_points = ", ".join([str(x) for x in (e.get("key_points") or [])])
        content = "\n".join([p for p in [summary, key_points] if p])
        doc = {
            **meta,
            "doc_type": "user_knowledge",
            "section_title": title,
            "content": content,
            "entry": e,
            "chunk_index": i,
        }
        actions.append({"_index": index, "_source": doc})

    bulk_kwargs: Dict[str, Any] = {}
    if pipeline:
        bulk_kwargs["pipeline"] = pipeline

    success, errors = helpers.bulk(
        client,
        actions,
        request_timeout=int(getattr(settings, "OPENSEARCH_REQUEST_TIMEOUT", 120)),
        chunk_size=int(getattr(settings, "OPENSEARCH_CHUNK_SIZE", 100)),
        max_retries=int(getattr(settings, "OPENSEARCH_MAX_RETRIES", 3)),
        raise_on_error=False,
        **bulk_kwargs,
    )
    if errors:
        logger.error("[assessment_ingest] OpenSearch bulk errors (first 3): %s", errors[:3])
    return int(success)


def search_combined_context(query: str, *, assessment_id: int, user_id: int, insurer: Optional[str] = None, product_id: Optional[str] = None, size: int = 10) -> Dict[str, Any]:
    client = _os_client()
    index = settings.OPENSEARCH_INDEX

    should: List[Dict[str, Any]] = []
    # Clause 1: user knowledge for this assessment
    should.append({
        "bool": {
            "filter": [
                {"term": {"doc_type": "user_knowledge"}},
                {"term": {"assessment_id": assessment_id}},
                {"term": {"user_id": user_id}},
            ],
            "must": [
                {"multi_match": {"query": query, "fields": ["content^3", "section_title^2", "entry"], "type": "best_fields"}}
            ],
        }
    })
    # Clause 2: general insurer/product documents (catalog/policy)
    must_general: List[Dict[str, Any]] = [
        {"multi_match": {"query": query, "fields": ["content^2", "section_title", "text", "embed_input"]}}
    ]
    filter_general: List[Dict[str, Any]] = []
    if product_id:
        filter_general.append({"term": {"policy_id": str(product_id)}})
    if insurer:
        filter_general.append({"term": {"insurer": insurer}})
    should.append({"bool": {"filter": filter_general, "must": must_general}})

    body = {
        "size": size,
        "query": {"bool": {"should": should}},
        "_source": True,
    }
    resp = client.search(index=index, body=body)
    hits = resp.get("hits", {}).get("hits", []) or []
    return {
        "hits": [h.get("_source", {}) for h in hits],
    }

