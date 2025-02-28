"""
입력 검증 유틸리티 모듈
- 파일 및 입력 검증 함수
"""

import os
import logging
from typing import Dict, Any, List, Union, Optional, Set

# 로거 설정
logger = logging.getLogger(__name__)

# 지원하는 파일 형식
SUPPORTED_FILE_TYPES = {
    # 이미지 파일
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
    '.bmp': 'image/bmp',
    '.gif': 'image/gif',
    
    # PDF 파일
    '.pdf': 'application/pdf'
}

# 기본 최대 파일 크기 (20MB)
DEFAULT_MAX_FILE_SIZE = 20 * 1024 * 1024


def validate_file_type(filename: str, allowed_types: Optional[Set[str]] = None) -> bool:
    """
    파일 형식 검증
    
    Args:
        filename: 파일명
        allowed_types: 허용된 확장자 집합 (None이면 모든 지원 형식)
        
    Returns:
        유효 여부
    """
    # 파일 확장자 추출
    ext = os.path.splitext(filename)[1].lower()
    
    # 허용된 형식이 지정되지 않은 경우 기본 지원 형식 사용
    if allowed_types is None:
        allowed_types = set(SUPPORTED_FILE_TYPES.keys())
    
    # 확장자 검증
    return ext in allowed_types


def validate_file_size(file_size: int, max_size: Optional[int] = None) -> bool:
    """
    파일 크기 검증
    
    Args:
        file_size: 파일 크기 (바이트)
        max_size: 최대 허용 크기 (None이면 기본값 사용)
        
    Returns:
        유효 여부
    """
    # 최대 크기가 지정되지 않은 경우 기본값 사용
    if max_size is None:
        max_size = DEFAULT_MAX_FILE_SIZE
    
    return file_size <= max_size


def validate_options(options: Dict[str, Any], required_fields: Optional[List[str]] = None) -> bool:
    """
    옵션 딕셔너리 검증
    
    Args:
        options: 옵션 딕셔너리
        required_fields: 필수 필드 목록
        
    Returns:
        유효 여부
    """
    # 필수 필드가 지정되지 않은 경우 검증 통과
    if required_fields is None:
        return True
    
    # 필수 필드 확인
    for field in required_fields:
        if field not in options:
            logger.warning(f"필수 옵션 필드 누락: {field}")
            return False
    
    return True


def validate_language_code(lang: str) -> bool:
    """
    언어 코드 검증
    
    Args:
        lang: 언어 코드
        
    Returns:
        유효 여부
    """
    # 지원하는 언어 코드
    valid_codes = {
        # Tesseract 형식
        'jpn', 'eng', 'kor', 'chi_sim', 'chi_tra',
        
        # ISO 639-1
        'ja', 'en', 'ko', 'zh',
        
        # 국가 코드 포함
        'ja-jp', 'en-us', 'ko-kr', 'zh-cn', 'zh-tw',
        
        # 스크립트 포함
        'zh-hans', 'zh-hant'
    }
    
    return lang.lower() in valid_codes


def validate_extraction_field(field: Dict[str, Any]) -> bool:
    """
    추출 필드 검증
    
    Args:
        field: 필드 설정
        
    Returns:
        유효 여부
    """
    # 필수 키 확인
    if 'name' not in field:
        logger.warning("필드에 'name' 키가 없습니다.")
        return False
    
    # 필드 유형 확인
    if 'type' in field:
        valid_types = {'text', 'date', 'amount', 'company', 'person', 'address', 'phone', 'email', 'number'}
        if field['type'] not in valid_types:
            logger.warning(f"유효하지 않은 필드 유형: {field['type']}")
            return False
    
    return True


def validate_email(email: str) -> bool:
    """
    이메일 주소 검증
    
    Args:
        email: 이메일 주소
        
    Returns:
        유효 여부
    """
    import re
    
    # 간단한 이메일 형식 검증
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """
    URL 검증
    
    Args:
        url: URL 문자열
        
    Returns:
        유효 여부
    """
    import re
    
    # URL 형식 검증
    pattern = r'^(https?|ftp)://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def validate_json(json_str: str) -> bool:
    """
    JSON 문자열 검증
    
    Args:
        json_str: JSON 문자열
        
    Returns:
        유효 여부
    """
    import json
    
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False
