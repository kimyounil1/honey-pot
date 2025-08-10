from . import AsyncSession, select, userModel, userSchema, hash

async def create_user(db: AsyncSession, user_in: userSchema.UserCreate) -> userModel.User:
    user = userModel.User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hash.get_password_hash(user_in.password), # 유저 생성시 해싱된 패스워드 저장
        birth_date=user_in.birth_date,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(userModel.User).where(userModel.User.user_id == user_id))
    return result.scalars().first()

# 이메일로 사용자 조회
async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(userModel.User).filter(userModel.User.email == email))
    return result.scalars().first()