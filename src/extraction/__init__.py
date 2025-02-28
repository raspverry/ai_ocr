"""
데이터 추출 모듈
- OCR 결과에서 구조화된 데이터 추출
- LLM 기반 필드 추출
- 추출 데이터 내보내기 
"""

import logging
from typing import Dict, Any, List

# 모듈 메타데이터
__module_name__ = 'extraction'
__version__ = '1.0.0'

# 로거 설정
logger = logging.getLogger(__name__)

# 추출 필드 유형
FIELD_TYPES = {
    'text': '텍스트',
    'date': '날짜',
    'amount': '금액',
    'company': '회사명',
    'person': '인명',
    'address': '주소',
    'phone': '전화번호',
    'email': '이메일',
    'number': '숫자'
}

# 필드 컨텍스트 구분자
CONTEXT_DELIMITER = '|'

# 편의성을 위한 주요 모듈/클래스 임포트
from src.extraction.field_config import FieldConfig
from src.extraction.llm_processor import LLMProcessor
from src.extraction.csv_exporter import CSVExporter

# 모듈 초기화 로그
logger.info(f"데이터 추출 모듈 초기화 완료")
