from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    """이메일로 사용자 조회"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    """사용자명으로 사용자 조회"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """ID로 사용자 조회"""
    return db.query(User).filter(User.id == user_id).first()
