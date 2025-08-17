# app/services/ingest.py
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import boto3
from opensearchpy import (
    AWSV4SignerAuth,
    OpenSearch,
    RequestsHttpConnection,
    helpers,
)

from app.config import settings

logger = logging.getLogger(__name__)


def _split_text(text: str, max_chars: int) -> List[Tuple[str, str]]:
    if "\f" in text:
        parts = text.split("\f")
    else:
        parts = text.split("\n\n")

    results: List[Tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        lines = part.splitlines()
        if len(lines) > 1:
            section_title = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
        else:
            section_title = ""
            body = part

        for start in range(0, len(body), max_chars):
            snippet = body[start:start + max_chars]
            results.append((section_title, snippet))

    return results


async def ingest_policy(text: str, meta: Dict[str, Any]) -> int:
    if not text:
        logger.warning("ingest_policy called with empty text")
        return 0

    max_chars = settings.OPENSEARCH_MAX_CHARS
    chunks = _split_text(text, max_chars)
    host = settings.OPENSEARCH_HOST
    port = getattr(settings, "OPENSEARCH_PORT", 443)
    region = getattr(settings, "OPENSEARCH_REGION", "us-east-1")
    index = settings.OPENSEARCH_INDEX
    pipeline = settings.OPENSEARCH_PIPELINE
    timeout = getattr(settings, "OPENSEARCH_TIMEOUT", 40)

    auth = AWSV4SignerAuth(boto3.Session().get_credentials(), region, "es")
    client = OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )

    actions = []
    for i, (section_title, chunk) in enumerate(chunks):
        doc = {**meta, "chunk_index": i, "section_title": section_title, "content": chunk}
        actions.append({"_index": index, "_source": doc})

    try:
        bulk_kwargs = {"pipeline": pipeline} if pipeline else {}
        helpers.bulk(client, actions, request_timeout=timeout, **bulk_kwargs)
    except Exception as exc:
        logger.exception("Policy ingest failed: %s", exc)
        raise

    logger.info("Indexed %s documents for policy %s", len(actions), meta.get("policy_id"))
    return len(actions)
