# ====== [ADD] policy_id 기반 preview → LLM 추출 → DB 적재 ======
import os, json, logging
from typing import Any, Dict, List, Optional
from fastapi import Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db

from app.rag.retriever import (
    extract_coverage_batched, reduce_coverage,
    extract_premiums_batched, reduce_premiums, _pack_batches_by_tokens,
)

# DB models
from app.models.coverageModel import CoverageItem
from app.models.policyCoverageModel import PolicyCoverage
from app.models.policyPremiumModel import PolicyPremium
from app.models.policyModel import InsurancePolicy

# LLM
from app.services.llm_gateway import call_llm

# OpenSearch (ingest의 헬퍼 재사용)
from app.services.ingest import _os_client
from app.config import settings

try:
    from rapidfuzz import process, fuzz
    HAS_RAPIDFUZZ = True
except Exception:
    HAS_RAPIDFUZZ = False
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.services.ocr import extract_diagnosis_fields, ocr_file
from app.services.ingest import ingest_policy, preview_policy
from app.services.vector_db import add_document
from app.auth import deps
from app.schemas import userSchema

router = APIRouter(prefix="/ocr", tags=["ocr"], dependencies=[Depends(deps.get_current_user)])
logger = logging.getLogger(__name__)

SEGMENTS = {"입원","외래","처방","응급"}
BENEFITS = {"급여","비급여","선택"}
FUZZY_CUTOFF = int(os.getenv("COVERAGE_MATCH_CUTOFF", "88"))
logger = logging.getLogger(__name__)

def _to_num(x) -> Optional[float]:
    if x is None: return None
    if isinstance(x, (int, float)): return float(x)
    s = str(x).replace(",","").replace("원","").strip()
    if not s: return None
    try: return float(s)
    except: return None

def _norm_seg(v: Optional[str]) -> Optional[str]:
    if not v: return None
    v = v.strip()
    return v if v in SEGMENTS else None

def _norm_benefit(v: Optional[str]) -> Optional[str]:
    if not v: return None
    v = v.strip()
    return v if v in BENEFITS else None

def _match_name(name: str, base_names: List[str], cutoff: int = FUZZY_CUTOFF) -> Optional[str]:
    if not name: return None
    if name in base_names: return name
    if HAS_RAPIDFUZZ and base_names:
        cand = process.extractOne(name, base_names, scorer=fuzz.WRatio)
        if cand and cand[1] >= cutoff:
            return cand[0]
        return None
    # 폴백(간단 포함 매칭)
    n = name.replace(" ","")
    for b in base_names:
        if n in b.replace(" ","") or b.replace(" ","") in n:
            return b
    return None

def _ensure_json_array(text: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(text)
        if isinstance(data, list): return data
        if isinstance(data, dict): return [data]
    except Exception:
        pass
    return []

def _fetch_policy_chunks(policy_id: str, limit: int = 3000) -> List[Dict[str, Any]]:
    client = _os_client()
    index = settings.OPENSEARCH_INDEX
    body = {
        "size": limit,
        "query": { "term": { "policy_id": str(policy_id) } },
        "_source": {"excludes": ["embedding"]},
        "sort": [ {"chunk_index": {"order": "asc"}} ]
    }
    resp = client.search(index=index, body=body)
    hits = resp.get("hits",{}).get("hits",[])
    return [h.get("_source", {}) for h in hits]

@router.post("/preview")
async def preview_from_policy(
    policy_id:int,
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    입력: { "policy_id": 9 }
    1) policy 존재 확인
    2) OpenSearch에서 policy_id로 청크 로드
    3) coverage_item 베이스 로드
    4) LLM으로 coverage/premium 추출
    5) policy_coverage upsert / policy_premium replace
    """
    policy_id = 78
    if not isinstance(policy_id, int):
        raise HTTPException(status_code=400, detail="policy_id(int) required")

    # (1) policy 확인
    res = await db.execute(select(InsurancePolicy).where(InsurancePolicy.id == policy_id))
    pol = res.scalars().first()
    if not pol:
        raise HTTPException(status_code=404, detail="policy not found")

    # (2) OpenSearch 청크 로드
    try:
        chunks_src = _fetch_policy_chunks(pol.policy_id)
    except Exception as e:
        logger.exception("OpenSearch fetch failed: %s", e)
        raise HTTPException(status_code=500, detail="OpenSearch fetch failed")
    chunks_src = chunks_src
    if not chunks_src:
        raise HTTPException(status_code=400, detail="no chunks for this policy")

    # (3) coverage_item 베이스 로드
    res = await db.execute(select(CoverageItem))
    base_items = list(res.scalars().all())
    base_names = [c.name for c in base_items]
    id_by_name = {c.name: c.id for c in base_items}
    # (4) LLM 추출
    chunk_batches = _pack_batches_by_tokens(chunks_src)
    cov_raw = await extract_coverage_batched(base_names, chunk_batches)
    prem_raw = await extract_premiums_batched(chunk_batches)
    # 3) REDUCE: 서버 쪽 결정적 병합
    cov_rows = reduce_coverage(cov_raw)
    prem_rows = reduce_premiums(prem_raw)
    # 정규화
    def _norm_cov(rows):
        out=[]
        for r in rows or []:
            r=dict(r)
            r["segment"]=_norm_seg(r.get("segment"))
            r["benefit_type"]=_norm_benefit(r.get("benefit_type"))
            r["coinsurance_pct"]=_to_num(r.get("coinsurance_pct"))
            r["deductible_min"]=_to_num(r.get("deductible_min"))
            r["per_visit_limit"]=_to_num(r.get("per_visit_limit"))
            r["annual_limit"]=_to_num(r.get("annual_limit"))
            r["combined_cap_amount"]=_to_num(r.get("combined_cap_amount"))
            # ints
            try:
                if r.get("frequency_limit") is not None:
                    r["frequency_limit"]=int(float(r["frequency_limit"]))
            except: r["frequency_limit"]=None
            try:
                if r.get("coverage_order") is not None:
                    r["coverage_order"]=int(float(r["coverage_order"]))
            except: r["coverage_order"]=None
            out.append(r)
        return out

    def _norm_prem(rows):
        out=[]
        for r in rows or []:
            r=dict(r)
            try:
                r["age_min"]=int(r.get("age_min")) if r.get("age_min") is not None else None
                r["age_max"]=int(r.get("age_max")) if r.get("age_max") is not None else None
            except: r["age_min"], r["age_max"]=None, None
            g=(r.get("gender") or "").upper()
            r["gender"]= g if g in {"M","F","A"} else "A"
            r["monthly_premium"]=_to_num(r.get("monthly_premium"))
            cur=(r.get("currency") or "KRW").upper()
            r["currency"]=cur[:3]
            if not isinstance(r.get("meta"), dict):
                r["meta"]={}
            out.append(r)
        return out

    cov_rows = _norm_cov(cov_rows)
    prem_rows = _norm_prem(prem_rows)

    # (5) DB write
    # 5-1) policy_coverage upsert (중복 방지)
    inserted_cov = 0
    for r in cov_rows:
        name = (r.get("name") or "").strip()
        if not name: continue
        match = _match_name(name, base_names, cutoff=FUZZY_CUTOFF)
        if not match: continue
        cov_id = id_by_name[match]
        ex = await db.execute(select(PolicyCoverage.id).where(
            PolicyCoverage.policy_id==policy_id,
            PolicyCoverage.coverage_item_id==cov_id
        ))
        if ex.scalar() is not None:
            continue
        db.add(PolicyCoverage(
            policy_id=policy_id,
            coverage_item_id=cov_id,
            policy_score=None,
            limit_amount=None,
            notes=r.get("notes"),
            segment=r.get("segment"),
            benefit_type=r.get("benefit_type"),
            coinsurance_pct=r.get("coinsurance_pct"),
            deductible_min=r.get("deductible_min"),
            per_visit_limit=r.get("per_visit_limit"),
            annual_limit=r.get("annual_limit"),
            combined_cap_group=r.get("combined_cap_group"),
            combined_cap_amount=r.get("combined_cap_amount"),
            frequency_limit=r.get("frequency_limit"),
            frequency_period=r.get("frequency_period"),
            coverage_order=r.get("coverage_order"),
            source_ref=r.get("source_ref"),
        ))
        inserted_cov += 1

    # 5-2) policy_premium replace (금액 없는 행은 스킵)
    await db.execute(delete(PolicyPremium).where(PolicyPremium.policy_id==policy_id))
    inserted_prem = 0
    for r in prem_rows:
        if r.get("age_min") is None or r.get("age_max") is None or r.get("monthly_premium") is None:
            continue
        db.add(PolicyPremium(
            policy_id=policy_id,
            age_min=r["age_min"],
            age_max=r["age_max"],
            gender=r["gender"],
            smoker=r.get("smoker"),
            tier=r.get("tier"),
            monthly_premium=r["monthly_premium"],
            currency=r.get("currency","KRW"),
            meta=r.get("meta") or {},
        ))
        inserted_prem += 1

    await db.commit()

    return {
        "policy_id": policy_id,
        "coverage_candidates": len(cov_rows),
        "coverage_inserted": inserted_cov,
        "premium_candidates": len(prem_rows),
        "premium_inserted": inserted_prem,
    }

@router.post("/")
async def handle_ocr(
    file: UploadFile = File(...),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    try:
        filename = (file.filename or "").lower()
        if filename.endswith(".pdf"):
            text = await ocr_file(file)
            product_id = f"{current_user.user_id}-{file.filename}"
            meta = {
                "policy_id": product_id,
                "uploader_id": current_user.user_id,
                "filename": file.filename,
            }
            try:
                await ingest_policy(text, meta)
            except Exception as e:
                logger.warning("[OCR] ingest failed: %s", e)
            add_document(text, meta)
            return {"result_code": "SUCCESS", "product_id": product_id}
        fields = await extract_diagnosis_fields(file)
        return {"result_code": "SUCCESS", "disease_code": fields.get("icd10_code")}
    except Exception as e:
        logger.exception("[OCR] processing failed: %s", e)
        raise HTTPException(status_code=500, detail="OCR processing failed")

