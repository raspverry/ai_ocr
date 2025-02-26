#!/usr/bin/env python3
"""
초고정밀 OCR 시스템 애플리케이션 진입점
- FastAPI 웹 애플리케이션 시작
- API 라우트 등록
"""

import os
import sys
import logging
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ocr_service")

# 설정 로드
from src.core.config import config

# API 라우트 로드
from src.api.routes import router as api_router

# 웹 UI 라우트 로드
# from src.web.routes import router as web_router

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="초고정밀 멀티랭귀지 OCR API",
    description="PDF 및 이미지에서 고정밀 텍스트 추출 API",
    version="1.0.0"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우트 등록
app.include_router(api_router)

# 웹 UI 라우트 등록
# app.include_router(web_router)

# 정적 파일 마운트 (웹 UI용)
try:
    static_dir = os.path.join(os.path.dirname(__file__), "src", "web", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        
        # 템플릿 설정
        templates_dir = os.path.join(os.path.dirname(__file__), "src", "web", "templates")
        if os.path.exists(templates_dir):
            templates = Jinja2Templates(directory=templates_dir)
            
            # 루트 경로 핸들러 (웹 UI 리다이렉트)
            @app.get("/")
            async def read_root(request: Request):
                return templates.TemplateResponse("index.html", {"request": request})
except Exception as e:
    logger.warning(f"웹 UI 설정 오류: {e}")

# 전역 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"전역 예외 발생: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "내부 서버 오류", "detail": str(exc)}
    )

# 애플리케이션 시작
if __name__ == "__main__":
    host = config.get('app.api_host', '0.0.0.0')
    port = config.get('app.api_port', 8000)
    
    logger.info(f"OCR 서비스 시작 (호스트: {host}, 포트: {port})")
    uvicorn.run(app, host=host, port=port)
