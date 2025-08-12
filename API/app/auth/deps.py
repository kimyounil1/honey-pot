from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from app.models import userModel
from app.database import get_db
from app.schemas.tokenSchema import Token


from app.auth.token import SECRET_KEY, ALGORITHM

async def get_current_user(token: str = Depends(Token), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token.access_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        # exp 체크는 jose가 자동으로 해줌 (만료되면 JWTError 발생)
    except JWTError:
        raise credentials_exception

    # DB에서 유저 확인
    result = await db.execute(select(userModel.User).where(userModel.User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user
