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
from app.models.user import User
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


class TestUserModel:
    """User 모델 테스트"""

    def test_user_model_creation(self, test_db):
        """User 모델 직접 생성 테스트"""
        import uuid

        unique_id = str(uuid.uuid4())[:8]

        user = User(
            email=f"model{unique_id}@example.com",
            username=f"modeluser{unique_id}",
            hashed_password=get_password_hash("password"),
            full_name="모델 테스트",
            is_active=True,
        )

        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        assert user.id is not None
        assert user.email == f"model{unique_id}@example.com"
        assert user.username == f"modeluser{unique_id}"
        assert user.is_active is True
        assert user.is_verified is False  # 기본값
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_model_defaults(self, test_db):
        """User 모델 기본값 테스트"""
        import uuid

        unique_id = str(uuid.uuid4())[:8]

        user = User(
            email=f"defaults{unique_id}@example.com",
            username=f"defaultuser{unique_id}",
            hashed_password=get_password_hash("password"),
        )

        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        # 기본값 확인
        assert user.is_active is True
        assert user.is_verified is False
        assert user.full_name is None


class TestAPI:
    """API 엔드포인트 테스트"""

    def test_root_endpoint(self, client):
        """루트 엔드포인트 테스트"""
        response = client.get("/")

        assert response.status_code == 200
        assert "message" in response.json()
        assert "Mogle API" in response.json()["message"]

    def test_join_success(self, client, unique_user_data):
        """회원가입 성공 테스트"""
        response = client.post("/api/v1/auth/join", json=unique_user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == unique_user_data["email"]
        assert data["username"] == unique_user_data["username"]
        assert data["full_name"] == unique_user_data["full_name"]
        assert data["is_active"] is True
        assert data["is_verified"] is False  # 기본값
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        # 비밀번호는 응답에 포함되지 않음
        assert "password" not in data
        assert "hashed_password" not in data

    def test_join_duplicate_email(self, client, unique_user_data):
        """이메일 중복 회원가입 테스트"""
        # 첫 번째 회원가입 성공
        response1 = client.post("/api/v1/auth/join", json=unique_user_data)
        assert response1.status_code == 201

        # 같은 이메일로 재가입 시도
        duplicate_data = unique_user_data.copy()
        duplicate_data["username"] = f"different{unique_user_data['username']}"
        response2 = client.post("/api/v1/auth/join", json=duplicate_data)

        assert response2.status_code == 400
        assert "이미 등록된 이메일" in response2.json()["detail"]

    def test_join_duplicate_username(self, client, unique_user_data):
        """사용자명 중복 회원가입 테스트"""
        # 첫 번째 회원가입 성공
        response1 = client.post("/api/v1/auth/join", json=unique_user_data)
        assert response1.status_code == 201

        # 같은 사용자명으로 재가입 시도
        duplicate_data = unique_user_data.copy()
        duplicate_data["email"] = f"different{unique_user_data['email']}"
        response2 = client.post("/api/v1/auth/join", json=duplicate_data)

        assert response2.status_code == 400
        assert "이미 사용 중인 사용자명" in response2.json()["detail"]

    def test_login_success(self, client, unique_user_data):
        """로그인 성공 테스트"""
        # 먼저 회원가입
        client.post("/api/v1/auth/join", json=unique_user_data)

        # 로그인 시도
        login_data = {
            "username": unique_user_data["email"],  # OAuth2는 username 필드 사용
            "password": unique_user_data["password"],
        }
        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 50  # JWT 토큰은 충분히 길어야 함

    def test_login_invalid_credentials(self, client, unique_user_data):
        """잘못된 인증 정보로 로그인 테스트"""
        # 먼저 회원가입
        client.post("/api/v1/auth/join", json=unique_user_data)

        # 잘못된 비밀번호로 로그인 시도
        login_data = {"username": unique_user_data["email"], "password": "wrongpassword"}
        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401
        assert "이메일 또는 비밀번호가 올바르지 않습니다" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """존재하지 않는 사용자 로그인 테스트"""
        login_data = {"username": "nonexistent@example.com", "password": "somepassword"}
        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401
        assert "이메일 또는 비밀번호가 올바르지 않습니다" in response.json()["detail"]


class TestIntegration:
    """통합 테스트"""

    def test_complete_user_flow(self, client, unique_user_data):
        """완전한 사용자 플로우 테스트 (회원가입 → 로그인)"""
        # 1. 회원가입
        join_response = client.post("/api/v1/auth/join", json=unique_user_data)
        assert join_response.status_code == 201
        user_data = join_response.json()

        # 2. 로그인
        login_data = {"username": unique_user_data["email"], "password": unique_user_data["password"]}
        login_response = client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200
        token_data = login_response.json()

        # 3. 토큰 검증
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"

        # 사용자 정보가 일치하는지 확인
        assert user_data["email"] == unique_user_data["email"]
        assert user_data["username"] == unique_user_data["username"]
        # 새로 추가된 필드들 확인
        assert user_data["is_verified"] is False
        assert "updated_at" in user_data
