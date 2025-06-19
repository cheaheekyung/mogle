from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """사용자 기본 스키마"""

    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """회원가입용 스키마"""

    password: str


class UserLogin(BaseModel):
    """로그인용 스키마"""

    email: EmailStr
    password: str


class Token(BaseModel):
    """토큰 응답 스키마"""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """토큰 데이터 스키마"""

    email: Optional[str] = None


class UserResponse(UserBase):
    """사용자 응답 스키마"""

    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
