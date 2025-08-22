# app/services/policy_sync.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from datetime import date, datetime
import asyncio, json, logging
import boto3

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

from app.config import settings
from app.models.policyModel import InsurancePolicy

logger = logging.getLogger(__name__)
# app/services/policy_sync.py (발췌)
from sqlalchemy import select
from app.models.userModel import User  # ← 추가
# app/services/policy_sync.py
from sqlalchemy import select
from app.models.userModel import User

async def _resolve_owner_id(db: AsyncSession, src: dict, default_owner_env: int | None) -> int:
    # 0) 무조건 1을 우선 사용하려면 바로 반환해도 됩니다.
    # return 1
    default_owner_env =1
    # 1) 문서 메타에 uploader_id/user_id/owner_id가 있으면 그걸 시도
    for key in ("uploader_id", "user_id", "owner_id"):
        if key in src and src[key] not in (None, "", "null"):
            try:
                uid = int(src[key])
                exists = await db.execute(select(User.user_id).where(User.user_id == uid))
                if exists.scalar_one_or_none() is not None:
                    return uid
            except Exception:
                pass

    # 2) 환경변수 기본값(없으면 1)
    uid = default_owner_env if default_owner_env is not None else 1
    exists = await db.execute(select(User.user_id).where(User.user_id == uid))
    return uid

# -------------------------
# 타입 보정 유틸
# -------------------------
def _coerce_date(v: Any) -> Optional[date]:
    """OpenSearch에서 온 날짜 값을 date로 정규화"""
    if v is None or v == "" or v == "null":
        return None
    if isinstance(v, date):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, (int, float)):
        try:
            # epoch(ms) 방어
            ts = float(v)
            if ts > 1e12:
                ts = ts / 1000.0
            return datetime.utcfromtimestamp(ts).date()
        except Exception:
            return None
    if isinstance(v, str):
        s = v.strip()
        # 1) ISO 우선
        try:
            return date.fromisoformat(s)
        except Exception:
            pass
        # 2) dateutil fallback
        try:
            from dateutil import parser as dparser
            return dparser.parse(s, dayfirst=False, yearfirst=True).date()
        except Exception:
            return None
    return None

def _coerce_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    return str(v)

def _coerce_list_of_str(v: Any) -> List[str]:
    """JSONB 칼럼용: list[str]로 강제"""
    if v is None:
        return []
    if isinstance(v, list):
        if not v:
            return []
        # dict가 섞여 있으면 name 키를 우선
        if isinstance(v[0], dict):
            out: List[str] = []
            for item in v:
                if isinstance(item, dict):
                    if "name" in item:
                        out.append(str(item["name"]))
                    else:
                        # dict 전체를 문자열화(최후방어)
                        out.append(json.dumps(item, ensure_ascii=False))
                else:
                    out.append(str(item))
            return out
        # 원시값 리스트
        return [str(x) for x in v]
    if isinstance(v, str):
        s = v.strip()
        # JSON 문자열이면 파싱
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("{") and s.endswith("}")):
            try:
                parsed = json.loads(s)
                return _coerce_list_of_str(parsed)
            except Exception:
                # 콤마 분리 백업
                return [p.strip() for p in s.split(",") if p.strip()]
        # 콤마 분리 백업
        return [p.strip() for p in s.split(",") if p.strip()]
    # 그 외 타입 방어
    return [str(v)]

# -------------------------
# OpenSearch 클라이언트
# -------------------------
def _os_client() -> OpenSearch:
    region = getattr(settings, "OPENSEARCH_REGION", "us-east-1")
    auth = AWSV4SignerAuth(boto3.Session().get_credentials(), region, "es")
    host = settings.OPENSEARCH_HOST
    port = int(getattr(settings, "OPENSEARCH_PORT", 443))
    return OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=int(getattr(settings, "OPENSEARCH_TIMEOUT", 120)),
        max_retries=int(getattr(settings, "OPENSEARCH_MAX_RETRIES", 5)),
        retry_on_timeout=True,
        pool_maxsize=int(getattr(settings, "OPENSEARCH_POOL_MAXSIZE", 25)),
    )

async def _list_policy_ids(client: OpenSearch, index: str, page_size: int = 500) -> List[str]:
    after_key: Optional[Dict[str, Any]] = None
    out: List[str] = []
    while True:
        agg_body: Dict[str, Any] = {
            "size": 0,
            "aggs": {
                "pids": {
                    "composite": {
                        "size": page_size,
                        "sources": [{"pid": {"terms": {"field": "policy_id"}}}]
                    }
                }
            }
        }
        if after_key:
            agg_body["aggs"]["pids"]["composite"]["after"] = after_key  # type: ignore

        resp = await asyncio.to_thread(
            client.search, index=index, body=agg_body, request_timeout=180
        )
        buckets = resp.get("aggregations", {}).get("pids", {}).get("buckets", []) or []
        for b in buckets:
            v = (b.get("key") or {}).get("pid")
            if v:
                out.append(str(v))
        after_key = resp.get("aggregations", {}).get("pids", {}).get("after_key")
        if not after_key:
            break
    return out

async def _fetch_one_meta(client: OpenSearch, index: str, policy_id: str) -> Dict[str, Any]:
    body = {
        "size": 1,
        "query": {"bool": {"filter": [{"term": {"policy_id": policy_id}}]}},
        "_source": True,
        "sort": [{"updated_at": {"order": "desc"}}],
    }
    resp = await asyncio.to_thread(
        client.search, index=index, body=body, request_timeout=180
    )
    hits = resp.get("hits", {}).get("hits", []) or []
    if not hits:
        return {"policy_id": policy_id}
    return hits[0].get("_source", {}) or {}

# -------------------------
# 동기화 엔트리
# -------------------------
async def sync_policies_from_opensearch(db: AsyncSession, *, dry_run: bool = False) -> Dict[str, Any]:
    client = _os_client()
    index = settings.OPENSEARCH_INDEX

    pids = await _list_policy_ids(client, index)
    created = updated = skipped = 0

    # ❗ user_id 정책: 없으면 시스템 소유자 ID로(환경변수), 그마저 없으면 None
    default_owner: Optional[int] = None
    try:
        v = getattr(settings, "DEFAULT_POLICY_OWNER_USER_ID", None)
        if v is not None:
            default_owner = int(v)
    except Exception:
        default_owner = None

    for pid in pids:
        src = await _fetch_one_meta(client, index, pid)
        owner_id = await _resolve_owner_id(db, src, 1)
        insurer         = _coerce_str(src.get("insurer") or src.get("insurance_company") or "") or None
        product_code    = _coerce_str(src.get("product_code") or "") or None
        version         = _coerce_str(src.get("version") or "") or None
        effective_date  = _coerce_date(src.get("effective_date"))
        cov_names       = _coerce_list_of_str(src.get("coverage_item_names"))

        # policy_id(문자열 유니크) 기준 upsert
        res = await db.execute(select(InsurancePolicy).where(InsurancePolicy.policy_id == str(pid)))
        row = res.scalar_one_or_none()

        if dry_run:
            skipped += 1
            continue

        if row is None:
            row = InsurancePolicy(
                user_id=owner_id,        # FK 제약 주의: 존재하는 유저 ID여야 함(아니면 nullable 로 바꾸세요)
                policy_id=str(pid),
                insurer=insurer,
                product_code=product_code,
                version=version,
                effective_date=effective_date,
                coverage_item_names=cov_names,   # ✅ 리스트로 넣기
            )
            db.add(row)
            created += 1
        else:
            if not row.user_id:
                row.user_id = owner_id
            if insurer:       row.insurer = insurer
            if product_code:  row.product_code = product_code
            if version:       row.version = version
            if effective_date: row.effective_date = effective_date
            if cov_names:     row.coverage_item_names = cov_names
            updated += 1

    if not dry_run:
        await db.commit()

    return {"found": len(pids), "created": created, "updated": updated, "skipped": skipped}
