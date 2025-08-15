import logging
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from app.services.ocr import ocr_file
from app.services.ingest import ingest_policy
from app.auth import deps
from app.schemas import userSchema

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)

@router.post("/")
async def upload_document(
    file: UploadFile = File(...),
    policy_id: str = Form(...),
    insurer: str = Form(...),
    product_code: str = Form(...),
    version: str = Form(...),
    effective_date: str = Form(...),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    try:
        ocr_text = await ocr_file(file)
        logger.info("[ROUTER] OCR extracted %s chars", len(ocr_text))

        meta = {
            "policy_id": policy_id,
            "insurer": insurer,
            "product_code": product_code,
            "version": version,
            "effective_date": effective_date,
            "uploader_id": current_user.user_id,
            "filename": file.filename,
        }

        indexed = await ingest_policy(ocr_text, meta)
        logger.info("[ROUTER] OpenSearch indexed %s docs policy_id=%s", indexed, policy_id)
        return {"indexed": indexed, "policy_id": policy_id}
    except Exception as exc:
        logger.exception("[ROUTER] Ingest failed: %s", exc)
        raise HTTPException(status_code=500, detail="Ingestion failed") from exc