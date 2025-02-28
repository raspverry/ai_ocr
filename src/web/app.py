"""
웹 애플리케이션 초기화 및 설정 모듈
- FastAPI 웹 애플리케이션 생성
- 미들웨어 및 라우터 설정
- 세션 및 인증 관리
"""

import os
import logging
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.sessions import SessionMiddleware

from src.core.config import config

# 로거 설정
logger = logging.getLogger(__name__)

# 기본 디렉토리 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def create_app() -> FastAPI:
    """
    FastAPI 애플리케이션 생성 및 설정
    
    Returns:
        설정된 FastAPI 애플리케이션
    """
    # 앱 생성
    app = FastAPI(
        title="초고정밀 멀티랭귀지 OCR 시스템",
        description="PDF 및 이미지에서 텍스트 추출 및 데이터 추출",
        version="1.0.0"
    )
    
    # 템플릿 설정
    templates = Jinja2Templates(directory=TEMPLATE_DIR)
    app.state.templates = templates
    
    # 정적 파일 설정
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    
    # 미들웨어 설정
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.get('app.secret_key', 'change-this-to-a-secure-secret'),
        session_cookie="ocr_session",
        max_age=config.get('web.session_lifetime', 86400)  # 기본 1일
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 라우터 설정
    from src.web.routes import router as web_router
    app.include_router(web_router)
    
    # 인증 설정
    security = HTTPBasic()
    
    # 인증 의존성
    async def get_current_user(
        request: Request,
        credentials: Optional[HTTPBasicCredentials] = Depends(security)
    ):
        """
        현재 사용자 가져오기 (인증 의존성)
        
        Args:
            request: FastAPI 요청 객체
            credentials: 기본 인증 정보
            
        Returns:
            인증된 사용자 정보
            
        Raises:
            HTTPException: 인증 실패
        """
        # 세션에서 사용자 정보 확인
        if "user" in request.session:
            return request.session["user"]
        
        # 인증 활성화 여부 확인
        auth_enabled = config.get('web.auth_enabled', True)
        if not auth_enabled:
            # 인증 비활성화 시 게스트 사용자 반환
            return {"username": "guest", "role": "guest"}
        
        # 기본 인증 확인 (HTTP Basic Auth)
        if credentials:
            # 기본 사용자 정보 (실제 구현에서는 데이터베이스 조회 필요)
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            admin_password = os.getenv("ADMIN_PASSWORD", "admin")
            
            if credentials.username == admin_username and credentials.password == admin_password:
                user_info = {"username": admin_username, "role": "admin"}
                request.session["user"] = user_info
                return user_info
        
        # 인증 실패
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다.",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # 의존성 앱에 저장
    app.dependency_overrides[get_current_user] = get_current_user
    
    # 앱 시작/종료 이벤트 설정
    @app.on_event("startup")
    async def startup_event():
        """앱 시작 시 실행할 이벤트"""
        logger.info("웹 애플리케이션 시작")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """앱 종료 시 실행할 이벤트"""
        logger.info("웹 애플리케이션 종료")
    
    return app
