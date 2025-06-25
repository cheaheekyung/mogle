from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.database import Base, engine

# 데이터베이스 테이블 생성 (개발 환경용)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mogle API", description="회원가입 및 인증 시스템", version="1.0.0")

# API 라우터 등록
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Mogle API에 오신 것을 환영합니다!"}
