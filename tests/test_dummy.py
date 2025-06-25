from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.main import app


# 테스트용 데이터베이스 설정
@pytest.fixture(scope="function")
def test_db():
    """테스트용 SQLite 인메모리 데이터베이스"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # 테이블 생성
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(test_db):
    """테스트용 FastAPI 클라이언트"""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """테스트용 사용자 데이터"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
        "full_name": "테스트 사용자",
    }


@pytest.fixture
def unique_user_data():
    """각 테스트마다 고유한 사용자 데이터"""
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    return {
        "email": f"test{unique_id}@example.com",
        "username": f"testuser{unique_id}",
        "password": "testpassword123",
        "full_name": f"테스트 사용자 {unique_id}",
    }


class TestSecurity:
    """보안 관련 함수 테스트"""

    def test_password_hashing(self):
        """비밀번호 해싱 테스트"""
        password = "mypassword123"
        hashed = get_password_hash(password)

        # 해시된 비밀번호는 원본과 다름
        assert hashed != password
        # 검증은 성공
        assert verify_password(password, hashed) is True
        # 잘못된 비밀번호는 실패
        assert verify_password("wrongpassword", hashed) is False

    def test_create_access_token(self):
        """JWT 토큰 생성 테스트"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 50  # JWT 토큰은 충분히 길어야 함

    def test_create_access_token_with_expiry(self):
        """만료 시간이 있는 JWT 토큰 생성 테스트"""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta)

        assert isinstance(token, str)
        assert len(token) > 50
