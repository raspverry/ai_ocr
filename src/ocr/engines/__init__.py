"""
OCR 엔진 모듈
- 다양한 OCR 엔진 구현
- 기본 인터페이스 제공
"""

import logging
from typing import Dict, Any, List, Type

# 로거 설정
logger = logging.getLogger(__name__)

# 엔진 정보
ENGINE_INFO = {
    'custom_model': {
        'name': 'TrOCR 모델',
        'description': '딥러닝 기반 OCR 모델',
        'languages': ['jpn', 'eng', 'kor', 'chi_sim', 'chi_tra'],
        'local': True
    },
    'tesseract': {
        'name': 'Tesseract OCR',
        'description': '오픈소스 OCR 엔진',
        'languages': ['jpn', 'eng', 'kor', 'chi_sim', 'chi_tra'],
        'local': True
    },
    'google_vision': {
        'name': 'Google Cloud Vision',
        'description': 'Google Cloud OCR API',
        'languages': ['jpn', 'eng', 'kor', 'chi_sim', 'chi_tra'],
        'local': False
    },
    'azure_form': {
        'name': 'Azure Form Recognizer',
        'description': 'Microsoft Azure OCR API',
        'languages': ['jpn', 'eng', 'kor', 'chi_sim', 'chi_tra'],
        'local': False
    }
}

# 편의성을 위한 주요 모듈/클래스 임포트
from src.ocr.engines.base import BaseOCREngine
from src.ocr.engines.custom_model import CustomModelEngine
from src.ocr.engines.tesseract import TesseractEngine
from src.ocr.engines.google_vision import GoogleVisionEngine
from src.ocr.engines.azure_form import AzureFormEngine

# 엔진 클래스 매핑
ENGINE_CLASSES = {
    'custom_model': CustomModelEngine,
    'tesseract': TesseractEngine,
    'google_vision': GoogleVisionEngine,
    'azure_form': AzureFormEngine
}

def get_engine(engine_name: str) -> BaseOCREngine:
    """
    엔진 이름으로 OCR 엔진 인스턴스 가져오기
    
    Args:
        engine_name: 엔진 이름
    
    Returns:
        OCR 엔진 인스턴스
    
    Raises:
        ValueError: 지원하지 않는 엔진 이름
    """
    if engine_name not in ENGINE_CLASSES:
        raise ValueError(f"지원하지 않는 OCR 엔진: {engine_name}")
    
    return ENGINE_CLASSES[engine_name]()

# 모듈 초기화 로그
logger.info(f"OCR 엔진 모듈 초기화 완료")
