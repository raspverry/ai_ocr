"""
코어 모듈
- 시스템 설정 관리
- 로깅 설정
- 공통 상수 및 유틸리티
"""

import os
import logging
from typing import Dict, Any

# 모듈 메타데이터
__module_name__ = 'core'
__version__ = '1.0.0'

# 공통 상수
APP_NAME = "초고정밀 OCR 시스템"
DEFAULT_ENCODING = "utf-8"
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

# 환경 설정
ENV = os.getenv("OCR_ENV", "development")
DEBUG = os.getenv("OCR_DEBUG", "False").lower() in ("true", "1", "yes")

# 설정 로드
from src.core.config import config

# 로깅 설정
LOG_LEVELS = {
    "development": logging.DEBUG,
    "testing": logging.INFO,
    "staging": logging.INFO,
    "production": logging.WARNING
}

LOG_LEVEL = LOG_LEVELS.get(ENV, logging.INFO)
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# 지원 언어
SUPPORTED_LANGUAGES = {
    'jpn': '일본어',
    'eng': '영어',
    'kor': '한국어',
    'chi_sim': '중국어 간체',
    'chi_tra': '중국어 번체'
}

# 문서 유형
DOCUMENT_TYPES = {
    'general': '일반 문서',
    'invoice': '청구서',
    'receipt': '영수증',
    'form': '양식',
    'contract': '계약서',
    'id_card': '신분증',
    'handwritten': '손글씨 문서'
}

# 초기화 함수
def initialize_core():
    """코어 모듈 초기화"""
    # 로깅 설정 초기화
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # 로거 설정
    logger = logging.getLogger('ocr_service')
    logger.setLevel(LOG_LEVEL)
    
    # 파일 핸들러
    file_handler = logging.FileHandler(os.path.join(logs_dir, 'ocr_service.log'))
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)
    
    logger.info(f"코어 모듈 초기화 완료 (환경: {ENV}, 디버그: {DEBUG})")
    return logger

# 모듈 로거
logger = initialize_core()

# 편의성을 위한 주요 모듈/클래스 임포트
from src.core.config import Config
