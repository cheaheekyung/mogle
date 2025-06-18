from typing import Optional

from pydantic import BaseModel, EmailStr


class AccountBase(BaseModel):
    """사용자 기본 스키마"""

    email: EmailStr
    username: str
    full_name: Optional[str] = None


class AccounCreate(AccountBase):
    """회원가입용 스키마"""

    password: str


class AccountLogin(BaseModel):
    """로그인용 스키마"""

    email: EmailStr
    password: str
