from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
import os
import uuid
from datetime import datetime

from app.database import get_db, AsyncSessionLocal
from app.auth import deps
from app.schemas import userSchema
from app.models import policyModel
from app.models.assessmentModel import Assessment
from app.models.attachmentModel import AssessmentAttachment
from app.models.assessmentMessageModel import AssessmentMessage
from app.schemas import assessmentSchema
from app.services.assessment_ingest import (
    analyze_image_with_gpt4o,
    analyze_text_with_gpt4o,
    index_assessment_entries,
    search_combined_context,
)
from app.services.llm_gateway import call_llm

router = APIRouter(prefix="/assessments", tags=["assessments"])


def _uploads_base() -> str:
    # Base dir to store uploaded files; default inside repo under app/data/uploads
    base = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "data", "uploads"))
    return os.path.abspath(os.path.normpath(base))


async def _resolve_user_policy_by_id(db: AsyncSession, user_id: int, policy_db_id: int) -> policyModel.InsurancePolicy | None:
    stmt = select(policyModel.InsurancePolicy).where(
        (policyModel.InsurancePolicy.user_id == user_id)
        & (policyModel.InsurancePolicy.id == policy_db_id)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


@router.get("/", response_model=List[assessmentSchema.AssessmentRead])
async def list_assessments(
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    stmt = (
        select(Assessment)
        .where(Assessment.user_id == current_user.user_id)
        .order_by(Assessment.created_at.desc())
    )
    res = await db.execute(stmt)
    items = res.scalars().all()
    return items


@router.post("/", response_model=assessmentSchema.AssessmentRead)
async def create_assessment(
    payload: assessmentSchema.AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    # find user's policy
    policy = await _resolve_user_policy_by_id(db, current_user.user_id, payload.policy_instance_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found for user")

    assessment = Assessment(
        user_id=current_user.user_id,
        policy_id=policy.policy_id,
        title=payload.assessment_name,
        insurer=policy.insurer,
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return assessment


@router.get("/{assessment_id}", response_model=assessmentSchema.AssessmentRead)
async def get_assessment(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    stmt = select(Assessment).where((Assessment.id == assessment_id) & (Assessment.user_id == current_user.user_id))
    res = await db.execute(stmt)
    assessment = res.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


@router.get("/{assessment_id}/messages", response_model=List[assessmentSchema.MessageRead])
async def get_messages(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    # find assessment
    stmt = select(Assessment).where((Assessment.id == assessment_id) & (Assessment.user_id == current_user.user_id))
    res = await db.execute(stmt)
    assessment = res.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    msg_stmt = (
        select(AssessmentMessage)
        .where(AssessmentMessage.assessment_id == assessment.id)
        .order_by(AssessmentMessage.created_at.asc())
    )
    msgs_res = await db.execute(msg_stmt)
    msgs = msgs_res.scalars().all()

    out: List[assessmentSchema.MessageRead] = []
    for m in msgs:
        out.append(
            assessmentSchema.MessageRead(
                id=m.id,
                role=m.role,  # type: ignore
                content=m.content,
                timestamp=m.created_at,
                attachment=None,
            )
        )
    return out


@router.post("/{assessment_id}/messages", response_model=assessmentSchema.MessageRead)
async def post_message(
    assessment_id: int,
    payload: assessmentSchema.MessageCreate,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    # resolve assessment
    stmt = select(Assessment).where((Assessment.id == assessment_id) & (Assessment.user_id == current_user.user_id))
    res = await db.execute(stmt)
    assessment = res.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # create user message
    user_msg = AssessmentMessage(
        assessment_id=assessment.id,
        role="user",
        content=payload.content,
        state="commencing",
    )
    db.add(user_msg)
    await db.flush()

    # create placeholder assistant message in 'building' state
    bot_msg = AssessmentMessage(
        assessment_id=assessment.id,
        role="assistant",
        content="泥섎━ 以묒엯?덈떎...",
        state="building",
    )
    db.add(bot_msg)
    await db.commit()
    await db.refresh(user_msg)

    # simulate background processing to mark state done
    def _complete_message():
        import asyncio
        async def _run():
            # mark assistant message to done and update content
            async with AsyncSessionLocal() as session:
                # type: ignore
                stmt = (
                    select(AssessmentMessage)
                    .where((AssessmentMessage.assessment_id == assessment.id) & (AssessmentMessage.role == "assistant"))
                    .order_by(AssessmentMessage.created_at.desc())
                )
                r = await session.execute(stmt)
                msg = r.scalars().first()
                if msg:
                    msg.state = "done"
                    msg.content = "?붿껌?섏떊 ?댁슜??寃?좏뻽?듬땲??"
                    await session.commit()
        try:
            asyncio.run(_run())
        except RuntimeError:
            # if already running loop (unlikely in thread), skip
            pass

    background.add_task(_complete_message)

    return assessmentSchema.MessageRead(
        id=user_msg.id,
        role="user",
        content=user_msg.content,
        timestamp=user_msg.created_at,
    )


@router.get("/{assessment_id}/messageState", response_model=assessmentSchema.MessageStateRead)
async def get_message_state(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    # resolve assessment
    stmt = select(Assessment).where((Assessment.id == assessment_id) & (Assessment.user_id == current_user.user_id))
    res = await db.execute(stmt)
    assessment = res.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # last assistant message state (or default 'done')
    msg_stmt = (
        select(AssessmentMessage)
        .where(AssessmentMessage.assessment_id == assessment.id)
        .order_by(AssessmentMessage.created_at.desc())
    )
    msgs_res = await db.execute(msg_stmt)
    last = msgs_res.scalars().first()
    state = last.state if last and last.state else "done"
    return assessmentSchema.MessageStateRead(state=state)  # type: ignore


@router.get("/{assessment_id}/uploads", response_model=assessmentSchema.UploadList)
async def list_uploads(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    stmt = select(Assessment).where((Assessment.id == assessment_id) & (Assessment.user_id == current_user.user_id))
    res = await db.execute(stmt)
    assessment = res.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    stmt2 = (
        select(AssessmentAttachment)
        .where(AssessmentAttachment.assessment_id == assessment.id)
        .order_by(AssessmentAttachment.created_at.desc())
    )
    r2 = await db.execute(stmt2)
    atts = r2.scalars().all()
    items: List[assessmentSchema.UploadItem] = []
    for a in atts:
        items.append(
            assessmentSchema.UploadItem(
                upload_id=a.upload_id,
                filename=a.filename,
                file_type=a.content_type,
                file_size=a.file_size,
                upload_status=a.upload_status,
                ocr_status=a.ocr_status,
                created_at=a.created_at,
            )
        )
    return assessmentSchema.UploadList(uploads=items)


@router.post("/{assessment_id}/upload", response_model=assessmentSchema.UploadItem)
async def upload_assessment_file(
    assessment_id: int,
    file: UploadFile = File(...),
    background: BackgroundTasks = None,  # type: ignore
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    # verify assessment ownership
    stmt = select(Assessment).where((Assessment.id == assessment_id) & (Assessment.user_id == current_user.user_id))
    res = await db.execute(stmt)
    assessment = res.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # storage path
    base = _uploads_base()
    room_dir = os.path.join(base, "assessment", str(assessment.id))
    os.makedirs(room_dir, exist_ok=True)

    upload_id = uuid.uuid4().hex[:12]
    fname = file.filename or f"upload-{upload_id}"
    content_type = file.content_type or "application/octet-stream"
    target_path = os.path.join(room_dir, f"{upload_id}-{fname}")

    raw = await file.read()
    with open(target_path, "wb") as f:
        f.write(raw)

    att = AssessmentAttachment(
        assessment_id=assessment.id,
        upload_id=upload_id,
        filename=fname,
        content_type=content_type,
        file_size=len(raw),
        storage_path=target_path,
        upload_status="completed",
        ocr_status="pending",
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)

    def _bg_process():
        import asyncio

        async def _run():
            try:
                items: List[dict] = []
                ctype = (content_type or "").lower()
                if fname.lower().endswith(".png") or ctype.startswith("image/"):
                    items = analyze_image_with_gpt4o(raw, mime=ctype or "image/png")
                elif fname.lower().endswith(".txt") or ctype == "text/plain":
                    try:
                        txt = raw.decode("utf-8", errors="ignore")
                    except Exception:
                        txt = raw.decode("cp949", errors="ignore")
                    items = analyze_text_with_gpt4o(txt)
                else:
                    items = []

                meta = {
                    "user_id": current_user.user_id,
                    "assessment_id": assessment.id,
                    "insurer": assessment.insurer,
                    "policy_id": assessment.policy_id,
                    "filename": fname,
                    "upload_id": upload_id,
                }
                _ = index_assessment_entries(items, meta) if items else 0

                async with AsyncSessionLocal() as session:
                    stmt = select(AssessmentAttachment).where(AssessmentAttachment.upload_id == upload_id)
                    r = await session.execute(stmt)
                    row = r.scalar_one_or_none()
                    if row:
                        row.ocr_status = "completed"
                    await session.commit()
            except Exception:
                try:
                    async with AsyncSessionLocal() as session:
                        stmt = select(AssessmentAttachment).where(AssessmentAttachment.upload_id == upload_id)
                        r = await session.execute(stmt)
                        row = r.scalar_one_or_none()
                        if row:
                            row.ocr_status = "failed"
                        await session.commit()
                except Exception:
                    pass

        try:
            asyncio.run(_run())
        except RuntimeError:
            pass

    if background:
        background.add_task(_bg_process)

    return assessmentSchema.UploadItem(
        upload_id=att.upload_id,
        filename=att.filename,
        file_type=att.content_type,
        file_size=att.file_size,
        upload_status=att.upload_status,
        ocr_status=att.ocr_status,
        created_at=att.created_at,
    )


@router.delete("/{assessment_id}/uploads/{upload_id}")
async def delete_upload(
    assessment_id: int,
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    # ensure assessment ownership
    stmt = select(Assessment).where((Assessment.id == assessment_id) & (Assessment.user_id == current_user.user_id))
    res = await db.execute(stmt)
    assessment = res.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # find attachment
    a_stmt = select(AssessmentAttachment).where(
        (AssessmentAttachment.assessment_id == assessment.id) & (AssessmentAttachment.upload_id == upload_id)
    )
    a_res = await db.execute(a_stmt)
    att = a_res.scalar_one_or_none()
    if not att:
        raise HTTPException(status_code=404, detail="Upload not found")

    # remove file best-effort
    try:
        if att.storage_path and os.path.exists(att.storage_path):
            os.remove(att.storage_path)
    except Exception:
        pass

    await db.execute(delete(AssessmentAttachment).where(AssessmentAttachment.id == att.id))
    await db.commit()

    return {"ok": True}
@router.get("/", response_model=List[assessmentSchema.AssessmentRead])
async def list_assessments(
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    stmt = (
        select(Assessment)
        .where(Assessment.user_id == current_user.user_id)
        .order_by(Assessment.created_at.desc())
    )
    res = await db.execute(stmt)
    rows = res.scalars().all()
    return rows

