from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
import os
import uuid
from datetime import datetime

from app.database import get_db
from app.auth import deps
from app.schemas import userSchema
from app.models import policyModel
from app.models.assessmentModel import Assessment
from app.models.attachmentModel import AssessmentAttachment
from app.models.assessmentMessageModel import AssessmentMessage
from app.schemas import assessmentSchema

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
        content="처리 중입니다...",
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
            async with get_db() as s:  # type: ignore
                session: AsyncSession = s  # type: ignore
                stmt = (
                    select(AssessmentMessage)
                    .where((AssessmentMessage.assessment_id == assessment.id) & (AssessmentMessage.role == "assistant"))
                    .order_by(AssessmentMessage.created_at.desc())
                )
                r = await session.execute(stmt)
                msg = r.scalars().first()
                if msg:
                    msg.state = "done"
                    msg.content = "요청하신 내용을 검토했습니다."
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

    a_stmt = (
        select(AssessmentAttachment)
        .where(AssessmentAttachment.assessment_id == assessment.id)
        .order_by(AssessmentAttachment.created_at.desc())
    )
    a_res = await db.execute(a_stmt)
    items = a_res.scalars().all()
    return {
        "uploads": [
            assessmentSchema.UploadItem(
                upload_id=i.upload_id,
                filename=i.filename,
                file_type=i.content_type,
                file_size=i.file_size,
                upload_status=i.upload_status,
                ocr_status=i.ocr_status,
                created_at=i.created_at,
            )
            for i in items
        ]
    }


@router.post("/{assessment_id}/uploads", response_model=assessmentSchema.UploadList)
async def upload_files(
    assessment_id: int,
    background: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: userSchema.UserRead = Depends(deps.get_current_user),
):
    # resolve assessment
    stmt = select(Assessment).where((Assessment.id == assessment_id) & (Assessment.user_id == current_user.user_id))
    res = await db.execute(stmt)
    assessment = res.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    base_dir = _uploads_base()
    target_dir = os.path.join(base_dir, str(assessment.id))
    os.makedirs(target_dir, exist_ok=True)

    created: list[AssessmentAttachment] = []
    for f in files:
        data = await f.read()
        ext = os.path.splitext(f.filename or "")[1]
        uid = f"upl_{uuid.uuid4().hex[:12]}"
        stored_name = f"{uid}{ext}"
        stored_path = os.path.join(target_dir, stored_name)
        with open(stored_path, "wb") as out:
            out.write(data)

        att = AssessmentAttachment(
            assessment_id=assessment.id,
            upload_id=uid,
            filename=f.filename or stored_name,
            content_type=f.content_type,
            file_size=len(data),
            storage_path=stored_path,
            upload_status="completed",
            ocr_status="pending",
        )
        db.add(att)
        created.append(att)

    await db.commit()

    # background OCR + index stub
    def _ocr_and_index(paths: list[str]):
        # TODO: integrate with paddle OCR service and OpenSearch index
        # For now, mark records as completed.
        import asyncio
        async def _run():
            async with get_db() as s:  # type: ignore
                session: AsyncSession = s  # type: ignore
                for att in created:
                    stmt = (
                        select(AssessmentAttachment)
                        .where(AssessmentAttachment.upload_id == att.upload_id)
                    )
                    r = await session.execute(stmt)
                    row = r.scalar_one_or_none()
                    if row:
                        row.ocr_status = "completed"
                await session.commit()

        try:
            asyncio.run(_run())
        except RuntimeError:
            pass

    background.add_task(_ocr_and_index, [a.storage_path for a in created])

    return {
        "uploads": [
            assessmentSchema.UploadItem(
                upload_id=a.upload_id,
                filename=a.filename,
                file_type=a.content_type,
                file_size=a.file_size,
                upload_status=a.upload_status,
                ocr_status=a.ocr_status,
                created_at=a.created_at,
            )
            for a in created
        ]
    }


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
