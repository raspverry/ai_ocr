"""
작업자 모듈
- 백그라운드 작업 처리
- 작업 큐 관리
"""

import logging
from typing import Dict, Any, List

# 모듈 메타데이터
__module_name__ = 'worker'
__version__ = '1.0.0'

# 로거 설정
logger = logging.getLogger(__name__)

# 작업 상태
JOB_STATUS = {
    'queued': '대기 중',
    'processing': '처리 중',
    'completed': '완료',
    'failed': '실패',
    'cancelled': '취소됨'
}

# 작업 유형
JOB_TYPES = {
    'ocr': 'OCR 처리',
    'extraction': '데이터 추출',
    'export': '내보내기',
    'pdf_report': 'PDF 보고서 생성'
}

# 작업 우선순위
JOB_PRIORITIES = {
    'high': '높음',
    'normal': '보통',
    'low': '낮음'
}

# 기본 작업자 수
DEFAULT_WORKERS = 4

# 편의성을 위한 주요 모듈/클래스 임포트
from src.worker.tasks import (
    process_document,
    extract_data_from_document,
    export_data_to_csv,
    generate_pdf_report
)

# 모듈 초기화 로그
logger.info(f"작업자 모듈 초기화 완료")
