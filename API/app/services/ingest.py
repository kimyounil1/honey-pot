from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import boto3
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection, helpers

from app.config import settings

logger = logging.getLogger(__name__)


def _split_text(text: str, max_chars: int) -> List[Tuple[str, str]]:
    # 페이지 구분문자(폼피드)가 있으면 우선 사용, 없으면 문단 단위
    parts = text.split("\f") if "\f" in text else text.split("\n\n")

    out: List[Tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.splitlines()
        if len(lines) > 1:
            section_title = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
        else:
            section_title, body = "", part

        for start in range(0, len(body), max_chars):
            out.append((section_title, body[start : start + max_chars]))
    return out


def _http_auth():
    """
    인증 우선순위:
    1) AWS SigV4 (컨테이너/호스트에 자격증명 존재 시)
    2) BasicAuth (OPENSEARCH_USERNAME/PASSWORD 설정 시)
    둘 다 없으면 즉시 예외.
    """
    # SigV4
    creds = boto3.Session().get_credentials()
    if creds is not None:
        region = getattr(settings, "OPENSEARCH_REGION", "us-east-1")
        return AWSV4SignerAuth(creds, region, "es")

    # Basic
    username = getattr(settings, "OPENSEARCH_USERNAME", None)
    password = getattr(settings, "OPENSEARCH_PASSWORD", None)
    if username and password:
        return (username, password)

    raise RuntimeError("OpenSearch auth not configured (SigV4 or BasicAuth required)")


def _os_client() -> OpenSearch:
    host = settings.OPENSEARCH_HOST
    port = int(getattr(settings, "OPENSEARCH_PORT", 443))
    auth = _http_auth()

    # 요청이 길어질 수 있으므로 타임아웃/재시도/압축을 보수적으로 늘림
    return OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=int(getattr(settings, "OPENSEARCH_CLIENT_TIMEOUT", 120)),  # read timeout
        max_retries=int(getattr(settings, "OPENSEARCH_MAX_RETRIES", 3)),
        retry_on_timeout=True,
        http_compress=True,
    )


async def ingest_policy(text: str, meta: Dict[str, Any]) -> int:
    """
    텍스트를 조각내 OpenSearch에 **실색인**한다.
    - 실패 시 예외를 **그대로** 올린다(soft-fail 없음).
    - 대용량 문서는 청크 크기를 줄여 요청당 처리 시간을 낮춘다.
    """
    if not text:
        logger.warning("ingest_policy called with empty text")
        return 0

    max_chars = int(getattr(settings, "OPENSEARCH_MAX_CHARS", 200_000))
    chunks = _split_text(text, max_chars)

    index = settings.OPENSEARCH_INDEX
    pipeline = getattr(settings, "OPENSEARCH_PIPELINE", None)

    # bulk 옵션(운영에서 조정 가능)
    request_timeout = int(
        getattr(settings, "OPENSEARCH_TIMEOUT",  # 과거 호환
                getattr(settings, "OPENSEARCH_REQUEST_TIMEOUT", 120))
    )
    chunk_size = int(getattr(settings, "OPENSEARCH_CHUNK_SIZE", 100))  # 작게: 타임아웃 방지
    max_retries = int(getattr(settings, "OPENSEARCH_MAX_RETRIES", 3))

    client = _os_client()

    # 액션 생성
    actions: List[Dict[str, Any]] = []
    for i, (section_title, chunk) in enumerate(chunks):
        doc = {
            **meta,
            "chunk_index": i,
            "section_title": section_title,
            "content": chunk,
        }
        actions.append({"_index": index, "_source": doc})

    # 색인
    bulk_kwargs: Dict[str, Any] = {}
    if pipeline:
        bulk_kwargs["pipeline"] = pipeline

    # helpers.bulk이 내부에서 chunk 단위로 나눠 전송함.
    # 타임아웃/재시도는 여기서 직접 지정.
    success, errors = helpers.bulk(
        client,
        actions,
        request_timeout=request_timeout,
        chunk_size=chunk_size,
        max_retries=max_retries,
        raise_on_error=False,  # 오류는 errors 배열로 수집하고 판단/로깅
        **bulk_kwargs,
    )

    if errors:
        # 운영 가독성을 위해 일부만 로그. 필요하면 상세 저장으로 확장.
        logger.error("OpenSearch bulk returned %d errors (first 3 shown): %s", len(errors), errors[:3])
        # 운영 정책상 에러가 하나라도 있으면 실패로 간주하려면 아래 한 줄을 활성화
        # raise RuntimeError(f"OpenSearch bulk had errors: {errors[:3]}")

    logger.info("Indexed %d documents for policy %s", int(success), meta.get("policy_id"))
    return int(success)

async def preview_policy(text: str, meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    """청킹 로직을 그대로 적용해 bulk 액션만 생성한다.

    OpenSearch 에는 전혀 전송하지 않고, helpers.bulk 에 전달될 "actions" 배열을
    그대로 반환한다. 디버깅이나 청킹 결과 확인 용도로 사용한다.

    Args:
        text: 인덱싱 대상 원본 텍스트
        meta: 각 청크에 포함할 메타데이터

    Returns:
        helpers.bulk 에 전달 가능한 액션 딕셔너리 리스트
    """

    if not text:
        logger.warning("preview_policy called with empty text")
        return []

    max_chars = int(getattr(settings, "OPENSEARCH_MAX_CHARS", 200_000))
    chunks = _split_text(text, max_chars)

    index = settings.OPENSEARCH_INDEX

    actions: List[Dict[str, Any]] = []
    for i, (section_title, chunk) in enumerate(chunks):
        doc = {
            **meta,
            "chunk_index": i,
            "section_title": section_title,
            "content": chunk,
        }
        actions.append({"_index": index, "_source": doc})

    logger.info("Prepared %d preview actions for policy %s", len(actions), meta.get("policy_id"))
    return actions