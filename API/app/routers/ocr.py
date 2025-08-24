import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.services.ocr import extract_diagnosis_fields, ocr_file
from app.services.ingest import ingest_policy, preview_policy
from app.services.vector_db import add_document
from app.auth import deps
from app.schemas import userSchema

router = APIRouter(prefix="/ocr", tags=["ocr"], dependencies=[Depends(deps.get_current_user)])
logger = logging.getLogger(__name__)

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

@router.post("/preview")
async def preview_ocr(
    file: UploadFile = File(...),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    """PDF 문서를 청킹만 수행해 bulk 액션을 반환한다."""

    try:
        filename = (file.filename or "").lower()
        if not filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="PDF files only")

        text = await ocr_file(file)
        product_id = f"{current_user.user_id}-{file.filename}"
        meta = {
            "policy_id": product_id,
            "uploader_id": current_user.user_id,
            "filename": file.filename,
        }
        actions = await preview_policy(text, meta)
        logger.info("[OCR-Preview] generated %d actions for %s", len(actions), product_id)
        return {"result_code": "SUCCESS", "actions": actions}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[OCR] preview processing failed: %s", e)
        raise HTTPException(status_code=500, detail="OCR preview failed")