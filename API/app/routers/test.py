# app/rag/test.py
from fastapi import FastAPI,APIRouter
from pydantic import BaseModel
import asyncio, time
from app.rag.retriever import retrieve
from app.services.common import Mode

router = APIRouter(prefix="/test", tags=["test"])

class RAGReq(BaseModel):
    query: str
    k: int = 6
    mode: str = "TERMS"  # "TERMS" | "REFUND" | "RECOMMEND"

class RAGResp(BaseModel):
    ok: bool
    elapsed_ms: int
    rag_block: str

@router.post("/rag", response_model=RAGResp)
async def rag(req: RAGReq):
    t0 = time.time()
    mode = getattr(Mode, req.mode, Mode.TERMS)
    # rag_block = await retrieve(
    #     mode=mode, user_id="rag-mini",
    #     query=req.query, attachment_ids=[], k=req.k
    # )
    rag_block = await asyncio.to_thread(
        retrieve,
        mode=mode,
        user_id="rag-mini",
        query=req.query,
        attachment_ids=[],
        k=req.k,
    )
    return RAGResp(
        ok=bool((rag_block or "").strip()),
        elapsed_ms=int((time.time()-t0)*1000),
        rag_block=rag_block or ""
    )