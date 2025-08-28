from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import datetime
import logging

from app.models import chatModel, userModel
from app.schemas import userSchema, chatSchema

logger = logging.getLogger(__name__)

# ========================================
# ================ CREATE ================
# ========================================
# 새 메세지 전송시
async def create_message(db: AsyncSession, message_in: chatSchema.Message) -> chatModel.Message:
    message = chatModel.Message(
        chat_id = message_in.chat_id,
        role = message_in.role,
        content = message_in.content,
        type = message_in.type,
        state = message_in.state,
        created_at = datetime.datetime.now(),
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message

# 새 채팅 시작시
async def create_chat(db: AsyncSession, chat_in: chatSchema.NewChat) -> chatModel.Chat :
    chat = chatModel.Chat(
        user_id = chat_in.user_id,
        title = chat_in.title,
        type = [],
        created_at = datetime.datetime.now(),
        updated_at = datetime.datetime.now(),
    )
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat

# ==========================================
# ================ RETREIVE ================
# ==========================================
# 특정 user_id에 대해 채팅방 목록 불러오기
# SELECT id, title, type, updated_at FROM chats WHERE user_id = 'CURRENT_USER_ID' ORDER BY updated_at DESC;
async def get_chat_list(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(chatModel.Chat)
        .where(chatModel.Chat.user_id == user_id)
        .order_by(chatModel.Chat.updated_at.desc())
    )
    return result.scalars().all()

# 특정 chat_id 선택시 메세지 불러오기
# SELECT id, role, content, created_at FROM messages WHERE chat_id = '123' ORDER BY created_at ASC;
async def get_messages(db:AsyncSession, chat_id: int):
    result = await db.execute(
        select(chatModel.Message).where(chatModel.Message.chat_id == chat_id).order_by(chatModel.Message.created_at.asc())
    )
    return result.scalars().all()

# 특정 chat_id에 대해 가장 마지막 어시스턴트 메세지 불러오기
async def get_last_message(db: AsyncSession, chat_id: int):
    result = await db.execute(
        select(chatModel.Message).where(chatModel.Message.chat_id == chat_id, chatModel.Message.role == "assistant").order_by(chatModel.Message.created_at.desc())
    )
    return result.scalars().first()

# 특정 chat_id에 대해 가장 마지막 어시스턴트 메세지 불러오기
async def get_last_user_message(db: AsyncSession, chat_id: int):
    result = await db.execute(
        select(chatModel.Message).where(chatModel.Message.chat_id == chat_id, chatModel.Message.role == "user").order_by(chatModel.Message.created_at.desc())
    )
    return result.scalars().first()

# 특정 chat_id로 채팅방 정보 불러오기
async def get_chat(db: AsyncSession, chat_id: int) -> chatModel.Chat | None:
    result = await db.execute(
        select(chatModel.Chat).where(chatModel.Chat.id == chat_id)
    )
    return result.scalars().first()

# ========================================
# ================ UPDATE ================
# ========================================
# 특정 chat_id에 type 추가
async def update_chat_type(db: AsyncSession, chat_id: int, new_type: str):
    chat = await get_chat(db, chat_id)
    if chat and new_type not in chat.type:
        chat.type.append(new_type)
        await db.commit()
        await db.refresh(chat)
    return chat

# 어시스턴트의 최신 메세지에 타입을 추가하고, 채팅방의 타입 목록도 갱신
async def update_message_type(db: AsyncSession, chat_id:int, message_type: str):
    message = await get_last_message(db, chat_id)
    user_message = await get_last_user_message(db, chat_id)
    if not message:
        return None
    chat = await get_chat(db, chat_id)

    # 메세지 타입 갱신
    message.type = message_type
    user_message.type = message_type

    # 채팅방 타입 목록 갱신
    if chat and message_type and message_type not in chat.type:
        chat.type.append(message_type)
    await db.commit()
    await db.refresh(message)
    return message

# 응답 대기중인 어시스턴트 메세지에 상태를 갱신
async def update_message_state(db: AsyncSession, chat_id:int, message_state: str):
    message = await get_last_message(db, chat_id)
    if message:
        message.state = message_state
        await db.commit()
        await db.refresh(message)
    logger.info("[STATE] chat=%s -> %s", chat_id, message_state)
    return message

# LLM 응답 갱신
async def update_message_content(db: AsyncSession, chat_id:int, message_content: str):
    message = await get_last_message(db, chat_id)
    if message:
        message.content = message_content
        await db.commit()
        await db.refresh(message)
    return message


# ========================================
# ================ DELETE ================
# ========================================
