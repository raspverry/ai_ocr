"""
문서 처리 모듈
- PDF 처리 및 변환
- 페이지 방향 감지 및 보정
- 이미지 정규화
"""

import logging
from typing import Dict, Any, List

# 모듈 메타데이터
__module_name__ = 'document'
__version__ = '1.0.0'

# 로거 설정
logger = logging.getLogger(__name__)

# 문서 처리 상수
PDF_DEFAULT_DPI = 300
IMAGE_DEFAULT_MAX_SIZE = 4000
MAX_PAGE_COUNT = 100

# 방향 유형
ORIENTATION_TYPES = {
    0: '정상',
    90: '시계방향 90도 회전',
    180: '180도 회전',
    270: '반시계방향 90도 회전'
}

# 지원하는 파일 형식
SUPPORTED_EXTENSIONS = {
    # PDF 파일
    '.pdf': 'application/pdf',
    
    # 이미지 파일
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
    '.bmp': 'image/bmp',
    '.gif': 'image/gif'
}

# 문서 처리 상태
PROCESS_STATUS = {
    'pending': '대기 중',
    'processing': '처리 중',
    'completed': '완료됨',
    'failed': '실패'
}

# 에러 코드
ERROR_CODES = {
    'invalid_file_format': 'E001',
    'empty_file': 'E002',
    'too_many_pages': 'E003',
    'conversion_error': 'E004',
    'orientation_detection_error': 'E005'
}

# 편의성을 위한 주요 모듈/클래스 임포트
from src.document.pdf_processor import PDFProcessor
from src.document.orientation import (
    detect_orientation,
    correct_orientation,
    detect_skew_angle,
    correct_skew,
    detect_document_bounds,
    crop_and_correct_document
)

# 도우미 함수
def get_file_extension(filename: str) -> str:
    """파일 확장자 추출"""
    import os
    return os.path.splitext(filename)[1].lower()

def is_supported_extension(filename: str) -> bool:
    """지원하는 파일 형식인지 확인"""
    ext = get_file_extension(filename)
    return ext in SUPPORTED_EXTENSIONS

def get_mime_type(filename: str) -> str:
    """파일 MIME 타입 반환"""
    ext = get_file_extension(filename)
    return SUPPORTED_EXTENSIONS.get(ext, 'application/octet-stream')

# 모듈 초기화 로그
logger.info(f"문서 처리 모듈 초기화 완료")
