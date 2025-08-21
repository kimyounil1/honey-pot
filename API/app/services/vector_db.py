# app/services/vector_db.py
from __future__ import annotations

import uuid
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

_store: List[Dict[str, Any]] = []


def add_document(text: str, meta: Dict[str, Any]) -> str:
    """Store a document with associated metadata."""
    doc_id = meta.get("policy_id") or str(uuid.uuid4())
    _store.append({"id": doc_id, "text": text, "meta": meta})
    return doc_id


def get_document(doc_id: str) -> Dict[str, Any] | None:
    for doc in _store:
        if doc.get("id") == doc_id:
            return doc
    return None


def search_documents(
    query: str,
    *,
    product_id: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Naive search over stored documents.

    Optionally filter documents by ``product_id`` before computing
    similarity scores. The returned results include the original
    text so callers can build a RAG context from the matches.

    This is a placeholder for a real vector database search.
    """
    results: List[Dict[str, Any]] = []
    for doc in _store:
        if product_id and doc.get("meta", {}).get("product_id") != product_id:
            continue
        score = SequenceMatcher(None, doc["text"], query).ratio()
        results.append(
            {
                "id": doc["id"],
                "score": score,
                "meta": doc["meta"],
                "text": doc["text"],
            }
        )
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
