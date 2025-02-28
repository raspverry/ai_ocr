"""
OCR 모듈
- 다양한 OCR 엔진 통합
- 텍스트 인식 및 처리
- 이미지 전처리 및 후처리
"""

import logging
from typing import Dict, Any, List

# 모듈 메타데이터
__module_name__ = 'ocr'
__version__ = '1.0.0'

# 로거 설정
logger = logging.getLogger(__name__)

# 지원 언어
SUPPORTED_LANGUAGES = {
    'jpn': '일본어',
    'eng': '영어',
    'kor': '한국어',
    'chi_sim': '중국어 간체',
    'chi_tra': '중국어 번체'
}

# 지원 OCR 엔진
OCR_ENGINES = [
    'custom_model',  # TrOCR 모델 기반
    'tesseract',     # Tesseract OCR
    'google_vision', # Google Cloud Vision API
    'azure_form'     # Azure Form Recognizer
]

# 특수 항목 감지 유형
SPECIAL_ITEM_TYPES = {
    'stamps': '도장',
    'handwriting': '손글씨',
    'strikethrough': '취소선',
    'tables': '표'
}

# 편의성을 위한 주요 모듈/클래스 임포트
from src.ocr.ensemble import OCREngine
from src.ocr.preprocessor import Preprocessor, DocumentPreprocessor
from src.ocr.postprocessor import PostProcessor
from src.ocr.special_handlers import SpecialItemDetector

# 모듈 초기화 로그
logger.info(f"OCR 모듈 초기화 완료")
