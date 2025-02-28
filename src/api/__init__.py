"""
API 모듈
- RESTful API 엔드포인트
- API 요청/응답 모델
- 인증 및 권한 관리
"""

from fastapi import APIRouter
from typing import Dict, Any

# API 라우터 정의
router = APIRouter(prefix="/api/v1")

# API 상태 정보
API_INFO: Dict[str, Any] = {
    'version': '1.0.0',
    'endpoints': {
        'ocr': '/api/v1/ocr',
        'extraction': '/api/v1/extraction',
        'fields': '/api/v1/fields',
        'health': '/api/v1/health',
        'languages': '/api/v1/languages'
    },
    'docs': '/docs'
}

# API 인증 및 보안 설정
from src.core.config import config

API_SECURITY_ENABLED = config.get('api.security_enabled', False)
API_KEY_REQUIRED = config.get('api.key_required', False)

# API 버전 관리
API_VERSION = '1.0.0'
API_DEPRECATED_VERSIONS = []

# API 제한 설정
API_RATE_LIMIT = config.get('api.rate_limit', 100)  # 분당 요청 수
API_MAX_UPLOAD_SIZE = config.get('api.max_upload_size', 20 * 1024 * 1024)  # 20MB
API_ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif']

# 편의성을 위한 주요 모듈/클래스 임포트
from src.api.routes import router as api_router
from src.api.models import (
    OCRRequest, OCRResponse, OCRResult, 
    ExtractionRequest, ExtractionResult
)

# 로깅 설정
import logging
logger = logging.getLogger(__name__)
logger.info(f"API 모듈 초기화 (버전: {API_VERSION})")
