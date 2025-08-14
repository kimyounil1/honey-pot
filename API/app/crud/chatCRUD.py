from fastapi import Depends
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
import datetime

from app.models import chatModel, userModel

from app.schemas import userSchema, chatSchema

from app.auth import deps

# 새 메세지 전송시
async def create_message(db: AsyncSession, message_in: chatSchema.Message) -> chatModel.Message:
    message = chatModel.Message(
        chat_id = message_in.chat_id,
        role = message_in.role,
        content = message_in.content,
        created_at = datetime.datetime.now()
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
        type = chat_in.type,
        created_at = datetime.datetime.now(),
        updated_at = datetime.datetime.now()
    )
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat

# 특정 user_id에 대해 채팅방 목록 불러오기
# SELECT id, title, type, updated_at FROM chats WHERE user_id = 'CURRENT_USER_ID' ORDER BY updated_at DESC;
async def get_chat_list(db: AsyncSession, user_id: int):
    result = await db.execute(select(chatModel.Chat).where(userModel.User.user_id == user_id).order_by(chatModel.Chat.updated_at.desc()))
    return result.scalars().all()

# 특정 채팅방 선택시 메세지 불러오기
# SELECT id, role, content, created_at FROM messages WHERE chat_id = '123' ORDER BY created_at ASC;
async def get_messages(db:AsyncSession, chat_id: int):
    result = await db.execute(select(chatModel.Message).where(chatModel.Message.chat_id == chat_id).order_by(chatModel.Message.created_at.asc()))
    return result.scalars().all()