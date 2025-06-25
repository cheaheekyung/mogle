from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.crud import user as user_crud
from app.main import app
from app.schemas.user import UserCreate


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


class TestUserCrud:
    """사용자 CRUD 함수 테스트"""

    def test_create_user(self, test_db, unique_user_data):
        """사용자 생성 테스트"""
        user_create = UserCreate(**unique_user_data)
        user = user_crud.create_user(test_db, user_create)

        assert user.email == unique_user_data["email"]
        assert user.username == unique_user_data["username"]
        assert user.full_name == unique_user_data["full_name"]
        assert user.is_active is True
        assert user.is_verified is False  # 기본값
        assert user.id is not None
        assert user.created_at is not None
        assert user.updated_at is not None
        # 비밀번호는 해시되어 저장됨
        assert user.hashed_password != unique_user_data["password"]

    def test_get_user_by_email(self, test_db, unique_user_data):
        """이메일로 사용자 조회 테스트"""
        # 사용자 생성
        user_create = UserCreate(**unique_user_data)
        created_user = user_crud.create_user(test_db, user_create)

        # 이메일로 조회
        found_user = user_crud.get_user_by_email(test_db, unique_user_data["email"])

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == unique_user_data["email"]

    def test_get_user_by_username(self, test_db, unique_user_data):
        """사용자명으로 사용자 조회 테스트"""
        # 사용자 생성
        user_create = UserCreate(**unique_user_data)
        created_user = user_crud.create_user(test_db, user_create)

        # 사용자명으로 조회
        found_user = user_crud.get_user_by_username(test_db, unique_user_data["username"])

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.username == unique_user_data["username"]

    def test_authenticate_user(self, test_db, unique_user_data):
        """사용자 인증 테스트"""
        # 사용자 생성
        user_create = UserCreate(**unique_user_data)
        user_crud.create_user(test_db, user_create)

        # 올바른 인증
        authenticated_user = user_crud.authenticate_user(
            test_db, unique_user_data["email"], unique_user_data["password"]
        )
        assert authenticated_user is not None
        assert authenticated_user.email == unique_user_data["email"]

        # 잘못된 비밀번호
        failed_auth = user_crud.authenticate_user(test_db, unique_user_data["email"], "wrongpassword")
        assert failed_auth is None

        # 존재하지 않는 이메일
        failed_auth = user_crud.authenticate_user(test_db, "nonexistent@example.com", unique_user_data["password"])
        assert failed_auth is None
