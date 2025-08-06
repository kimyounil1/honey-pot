from . import BaseModel, EmailStr, date, Optional

class UserBase(BaseModel):
    name: str
    email: EmailStr
    birth_date: Optional[date] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    user_id: int
    class Config:
        orm_mode = True