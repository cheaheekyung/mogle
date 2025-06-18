from typing import Optional

from pydantic import BaseModel, EmailStr


class AccountBase(BaseModel):
    """사용자 기본 스키마"""

    email: EmailStr
    username: str
    full_name: Optional[str] = None
