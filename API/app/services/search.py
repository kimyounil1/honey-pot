from __future__ import annotations

import logging
from typing import Any, Dict, List

import boto3
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection

from app.config import settings

logger = logging.getLogger(__name__)


def search_policies(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search ingested policy documents in OpenSearch."""
    host = settings.OPENSEARCH_HOST
    port = getattr(settings, "OPENSEARCH_PORT", 443)
    region = getattr(settings, "OPENSEARCH_REGION", "us-east-1")
    index = settings.OPENSEARCH_INDEX

    auth = AWSV4SignerAuth(boto3.Session().get_credentials(), region, "es")
    client = OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )

    try:
        response = client.search(
            index=index,
            body={
                "size": limit,
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "content",
                            "section_title",
                            "policy_id",
                            "insurer",
                            "product_code",
                        ],
                    }
                },
            },
        )
    except Exception as exc:
        logger.exception("OpenSearch query failed: %s", exc)
        raise

    hits = response.get("hits", {}).get("hits", [])
    results: List[Dict[str, Any]] = []
    for hit in hits:
        src = hit.get("_source", {})
        results.append(
            {
                "score": hit.get("_score", 0.0),
                "content": src.get("content", ""),
                "section_title": src.get("section_title", ""),
                "policy_id": src.get("policy_id"),
                "insurer": src.get("insurer"),
                "product_code": src.get("product_code"),
                "version": src.get("version"),
                "effective_date": src.get("effective_date"),
            }
        )
    return results