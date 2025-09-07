from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
import os
import uuid
from datetime import datetime
import logging

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
logger = logging.getLogger(__name__)


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
    try:
        # resolve assessment
        stmt = select(Assessment).where((Assessment.id == assessment_id) & (Assessment.user_id == current_user.user_id))
        res = await db.execute(stmt)
        assessment = res.scalar_one_or_none()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        content = (payload.content or "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="Message content is required")

        logger.info("[message] create user message: assessment_id=%s user_id=%s", assessment.id, current_user.user_id)
        # create user message
        user_msg = AssessmentMessage(
            assessment_id=assessment.id,
            role="user",
            content=content,
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

        logger.info("[message] user_msg_id=%s, bot_msg_id=%s", user_msg.id, bot_msg.id)

        # background: build assistant message using retrieval + LLM
        import asyncio
        loop = asyncio.get_running_loop()
        async def _finish():
            try:
                # 1) Retrieve context (OpenSearch) off main loop
                ctx = await asyncio.to_thread(
                    search_combined_context,
                    content,
                    assessment_id=assessment.id,
                    user_id=current_user.user_id,
                    insurer=assessment.insurer,
                    product_id=assessment.policy_id,
                    size=8,
                )
                hits = (ctx or {}).get("hits", [])
                parts: list[str] = []
                for h in hits[:6]:
                    title = str(h.get("section_title") or h.get("title") or "컨텍스트")
                    snippet = str(h.get("content") or h.get("text") or "").strip().replace("\n", " ")
                    if snippet:
                        snippet = (snippet[:400] + "…") if len(snippet) > 400 else snippet
                    parts.append(f"- {title}: {snippet}")
                ctx_text = "\n".join(parts) if parts else "(관련 컨텍스트가 충분하지 않습니다.)"

                # 2) Call LLM to compose answer
                system_prompt = (
                    "당신은 보험 청구/약관/보상 분석 보조자입니다. 한국어로 간결하고 정확히 답하세요.\n"
                    "가능하면 아래 컨텍스트를 우선 참고하되, 불충분하면 일반적 원칙 수준에서 안내하세요.\n"
                    "숫자/금액 추정은 추정임을 명시하고, 절차/서류는 단계적으로 제시하세요."
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "assistant", "content": f"[CONTEXT]\n{ctx_text}"},
                    {"role": "user", "content": content},
                ]
                answer = await call_llm(messages)

                # 3) Update latest assistant message
                async with AsyncSessionLocal() as session:
                    stmt = (
                        select(AssessmentMessage)
                        .where((AssessmentMessage.assessment_id == assessment.id) & (AssessmentMessage.role == "assistant"))
                        .order_by(AssessmentMessage.created_at.desc())
                    )
                    r = await session.execute(stmt)
                    msg = r.scalars().first()
                    if msg:
                        msg.state = "done"
                        msg.content = answer or "분석 결과를 생성하지 못했습니다."
                        await session.commit()
                        logger.info("[message-bg] completed assistant message id=%s", msg.id)
            except Exception as e:
                logger.exception("[message-bg] error completing assistant message: %s", e)
                try:
                    async with AsyncSessionLocal() as session:
                        stmt = (
                            select(AssessmentMessage)
                            .where((AssessmentMessage.assessment_id == assessment.id) & (AssessmentMessage.role == "assistant"))
                            .order_by(AssessmentMessage.created_at.desc())
                        )
                        r = await session.execute(stmt)
                        msg = r.scalars().first()
                        if msg:
                            msg.state = "failed"
                            msg.content = "메시지 처리 중 오류가 발생했습니다."
                            await session.commit()
                except Exception:
                    pass
        def _complete_message():
            try:
                asyncio.run_coroutine_threadsafe(_finish(), loop)
                logger.info("[message-bg] scheduled on main loop")
            except Exception as run_e:
                logger.exception("[message-bg] scheduler error: %s", run_e)

        background.add_task(_complete_message)

        return assessmentSchema.MessageRead(
            id=user_msg.id,
            role="user",
            content=user_msg.content,
            timestamp=user_msg.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[message] failed to post message: %s", e)
        raise HTTPException(status_code=500, detail="Failed to post message")


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
    import asyncio, logging
    lg = logging.getLogger(__name__)

    # verify assessment ownership
    lg.info("[upload] start: assessment_id=%s user_id=%s filename=%s ctype=%s",
            assessment_id, getattr(current_user, 'user_id', None), getattr(file, 'filename', None), getattr(file, 'content_type', None))
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
    lg.info("[upload] saved: path=%s size=%sB", target_path, len(raw))

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
    lg.info("[upload] db row created: upload_id=%s ocr_status=%s", upload_id, att.ocr_status)

    import asyncio
    loop = asyncio.get_running_loop()

    async def _run():
        try:
            lg.info("[upload-bg] begin: upload_id=%s filename=%s ctype=%s", upload_id, fname, content_type)
            items: List[dict] = []
            ctype = (content_type or "").lower()
            if fname.lower().endswith(".png") or ctype.startswith("image/"):
                # run blocking OCR in thread
                items = await asyncio.to_thread(analyze_image_with_gpt4o, raw, ctype or "image/png")
            elif fname.lower().endswith(".txt") or ctype == "text/plain":
                try:
                    txt = raw.decode("utf-8", errors="ignore")
                except Exception:
                    txt = raw.decode("cp949", errors="ignore")
                items = await asyncio.to_thread(analyze_text_with_gpt4o, txt)
            else:
                items = []
            lg.info("[upload-bg] analysis entries: %s", len(items))

            meta = {
                "user_id": current_user.user_id,
                "assessment_id": assessment.id,
                "insurer": assessment.insurer,
                "policy_id": assessment.policy_id,
                "filename": fname,
                "upload_id": upload_id,
            }
            indexed = await asyncio.to_thread(index_assessment_entries, items, meta) if items else 0
            lg.info("[upload-bg] indexed: %s", indexed)

            async with AsyncSessionLocal() as session:
                stmt = select(AssessmentAttachment).where(AssessmentAttachment.upload_id == upload_id)
                r = await session.execute(stmt)
                row = r.scalar_one_or_none()
                if row:
                    row.ocr_status = "completed"
                    lg.info("[upload-bg] status->completed upload_id=%s", upload_id)
                await session.commit()
        except Exception as e:
            lg.exception("[upload-bg] error upload_id=%s: %s", upload_id, e)
            try:
                async with AsyncSessionLocal() as session:
                    stmt = select(AssessmentAttachment).where(AssessmentAttachment.upload_id == upload_id)
                    r = await session.execute(stmt)
                    row = r.scalar_one_or_none()
                    if row:
                        row.ocr_status = "failed"
                        lg.warning("[upload-bg] status->failed upload_id=%s", upload_id)
                    await session.commit()
            except Exception as e2:
                lg.exception("[upload-bg] fail to set failed status upload_id=%s: %s", upload_id, e2)

    def _bg_process():
        # BackgroundTasks runs this in a thread; schedule coroutine onto main loop
        try:
            loop.call_soon_threadsafe(lambda: asyncio.create_task(_run()))
            lg.info("[upload-bg] scheduled on main loop upload_id=%s", upload_id)
        except Exception as run_e:
            lg.exception("[upload-bg] scheduler error upload_id=%s: %s", upload_id, run_e)

    if background:
        lg.info("[upload] schedule background task upload_id=%s", upload_id)
        background.add_task(_bg_process)
    else:
        # Fallback for cases where BackgroundTasks isn't available (tests, etc.)
        try:
            loop.create_task(_run())
            lg.info("[upload] fired background task via create_task upload_id=%s", upload_id)
        except Exception as e:
            lg.exception("[upload] failed to schedule task upload_id=%s: %s", upload_id, e)

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
