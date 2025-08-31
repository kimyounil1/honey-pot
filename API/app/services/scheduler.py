# app/services/scheduler.py
import os
from datetime import date, timedelta
from typing import List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import AsyncSessionLocal
from app.models.chatModel import Chat, Message
from app.crud import claimTimelineCRUD, notificationCRUD
from app.schemas import claimTimelineSchema, notificationSchema
from app.services.extractor import extract_core_info, compute_deadline, looks_like_refund_answer

# 알림 오프셋(일): D-90, D-30, D-14 기본값
NOTIF_OFFSETS = [90, 30, 14]

async def _scan_and_build_timeline_once():
    async with AsyncSessionLocal() as db:  # type: AsyncSession
        # 1) REFUND 후보 대화 찾기: 최근 assistant 메시지에 '환급/청구' 단어 포함
        q = (
            select(Chat.id, Chat.user_id, Chat.created_at)
            .order_by(Chat.id.desc())
        )
        chats = (await db.execute(q)).all()

        for chat_id, user_id, chat_created_at in chats:
            # 이미 타임라인 있으면 skip
            exists = await claimTimelineCRUD.get_by_chat(db, chat_id)
            if exists:
                continue

            # 최신 assistant 메시지 찾아서 환급 답변인지 판별
            mq = (
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.id.desc())
                .limit(5)
            )
            msgs = (await db.execute(mq)).scalars().all()
            if not msgs:
                continue

            combined = "\n".join([m.content or "" for m in msgs if m.content])
            if not combined or not looks_like_refund_answer(combined):
                continue

            base_date, disease_name, disease_code, policy_id, amount = extract_core_info(
                chat_created_at.date(), combined
            )
            deadline = compute_deadline(base_date, years=3)

            payload = claimTimelineSchema.ClaimTimelineCreate(
                user_id=user_id,
                chat_id=chat_id,
                policy_pk=None,
                policy_id=policy_id,
                insurer=None,
                product_code=None,
                disease_name=disease_name,
                disease_code=disease_code,
                base_date=base_date,
                deadline_date=deadline,
                expected_amount=amount,
                currency="KRW",
                source_message_id=msgs[0].id if msgs else None,
                notes=None,
            )
            tl = await claimTimelineCRUD.create(db, payload)

            # 2) 알림 예약(오프셋 별)
            for d in NOTIF_OFFSETS:
                send_on = deadline - timedelta(days=d)
                if send_on < date.today():
                    continue
                title = f"보험 청구 마감 D-{d}"
                total = f"{int(amount):,}원" if amount else "금액 추정 필요"
                message = f"마감일 {deadline.isoformat()} 전 D-{d}. 환급 예상액: {total}."
                notif = notificationSchema.NotificationCreate(
                    user_id=user_id,
                    timeline_id=tl.id,
                    send_on=send_on,
                    deadline_date=deadline,
                    title=title,
                    message=message,
                    is_sent=False,
                    is_read=False,
                    priority=5,
                )
                await notificationCRUD.upsert(db, notif)

async def scan_and_build_timeline():
    await _scan_and_build_timeline_once()

_scheduler: AsyncIOScheduler | None = None

async def setup_scheduler(app=None):
    if os.getenv("CLAIM_SCHEDULER", "1") != "1":
        return
    global _scheduler
    if _scheduler:
        return
    tz = timezone("Asia/Seoul")
    _scheduler = AsyncIOScheduler(timezone=tz)
    # 매일 09:00에 실행
    _scheduler.add_job(scan_and_build_timeline, "cron", hour=9, minute=0, id="scan_claim_timeline")
    _scheduler.start()
