# app/services/vector_db.py
from __future__ import annotations

import uuid
from difflib import SequenceMatcher
from typing import Any, Dict, List

_store: List[Dict[str, Any]] = []


def add_document(text: str, meta: Dict[str, Any]) -> str:
    """Store a document with associated metadata."""
    doc_id = meta.get("policy_id") or str(uuid.uuid4())
    _store.append({"id": doc_id, "text": text, "meta": meta})
    return doc_id


def search_documents(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Naive search over stored documents.

    This is a placeholder for a real vector database search.
    """
    results: List[Dict[str, Any]] = []
    for doc in _store:
        score = SequenceMatcher(None, doc["text"], query).ratio()
        results.append({"id": doc["id"], "score": score, "meta": doc["meta"]})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]