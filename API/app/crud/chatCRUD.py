# from sqlalchemy.future import select
# from sqlalchemy import func
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.models.chatModel import ChatHistory

# async def get_next_chat_session_idx(db: AsyncSession, user_id: int):
#     result = await db.execute(
#         select(func.max(ChatHistory.user_chat_idx)).where(ChatHistory.user_id == user_id)
#     )
#     max_idx = result.scalar()
#     return (max_idx or 0) + 1

# async def get_next_chat_idx(db: AsyncSession, user_id: int, user_chat_idx: int):
#     result = await db.execute(
#         select(func.max(ChatHistory.idx)).where(
#             ChatHistory.user_id == user_id,
#             ChatHistory.user_chat_idx == user_chat_idx
#         )
#     )
#     max_idx = result.scalar()
#     return (max_idx or 0) + 1

# async def create_chat_history(db: AsyncSession, user_id: int, user_chat_idx: int, chat_idx: int, body: str)-> ChatHistory :
#     new_chat = ChatHistory(
#         user_id=user_id,
#         user_chat_idx=user_chat_idx,
#         idx=chat_idx,
#         body=body
#     )
#     db.add(new_chat)
#     await db.commit()
#     await db.refresh(new_chat)
#     return new_chat
