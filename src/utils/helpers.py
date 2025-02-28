"""
유틸리티 헬퍼 함수 모듈
- 일반적인 유틸리티 함수 제공
"""

import os
import uuid
import re
import time
import datetime
from typing import Optional, Union, List, Dict, Any


def generate_id(prefix: str = '') -> str:
    """
    고유 ID 생성
    
    Args:
        prefix: ID 접두사
    
    Returns:
        고유 ID 문자열
    """
    uid = str(uuid.uuid4())
    if prefix:
        return f"{prefix}_{uid}"
    return uid


def format_timestamp(timestamp: Union[int, float, datetime.datetime] = None,
                    format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    타임스탬프 포맷팅
    
    Args:
        timestamp: 유닉스 타임스탬프 또는 datetime 객체
        format_str: 포맷 문자열
    
    Returns:
        포맷팅된 날짜/시간 문자열
    """
    if timestamp is None:
        # 현재 시간 사용
        dt = datetime.datetime.now()
    elif isinstance(timestamp, (int, float)):
        # 유닉스 타임스탬프
        dt = datetime.datetime.fromtimestamp(timestamp)
    else:
        # datetime 객체
        dt = timestamp
    
    return dt.strftime(format_str)


def sanitize_filename(filename: str) -> str:
    """
    파일명 정제 (안전한 파일명으로 변환)
    
    Args:
        filename: 원본 파일명
    
    Returns:
        정제된 파일명
    """
    # 파일 확장자 분리
    name, ext = os.path.splitext(filename)
    
    # 비허용 문자 제거 (경로 구분자 및 특수문자)
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    
    # 공백을 언더스코어로 변환
    name = re.sub(r'\s+', '_', name)
    
    # 다중 언더스코어 정리
    name = re.sub(r'_+', '_', name)
    
    # 파일명 길이 제한 (확장자 제외 최대 128자)
    if len(name) > 128:
        name = name[:128]
    
    # 파일명이 비어있으면 타임스탬프 사용
    if not name:
        name = f"file_{int(time.time())}"
    
    return name + ext


def get_file_extension(filename: str) -> str:
    """
    파일 확장자 추출
    
    Args:
        filename: 파일명
    
    Returns:
        파일 확장자 (점 포함)
    """
    return os.path.splitext(filename)[1].lower()


def format_file_size(size_bytes: int) -> str:
    """
    파일 크기 포맷팅
    
    Args:
        size_bytes: 바이트 단위 파일 크기
    
    Returns:
        포맷팅된 파일 크기 문자열
    """
    # 2^10 = 1024
    power = 2**10
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    
    while size_bytes > power and n < 4:
        size_bytes /= power
        n += 1
    
    return f"{size_bytes:.2f} {power_labels[n]}"


def parse_language_code(lang_code: str) -> str:
    """
    언어 코드 파싱
    
    Args:
        lang_code: 언어 코드 (ISO 639-1, ISO 639-2, 또는 Tesseract 형식)
    
    Returns:
        Tesseract 형식 언어 코드
    """
    # 언어 코드 정규화 매핑
    lang_map = {
        # ISO 639-1 코드를 Tesseract 언어 코드로 매핑
        'ja': 'jpn',
        'en': 'eng',
        'ko': 'kor',
        'zh': 'chi_sim',
        'zh-cn': 'chi_sim',
        'zh-hans': 'chi_sim',
        'zh-tw': 'chi_tra',
        'zh-hant': 'chi_tra',
        
        # Cloud API 언어 코드를 Tesseract 언어 코드로 매핑
        'ja-jp': 'jpn',
        'en-us': 'eng',
        'ko-kr': 'kor',
        
        # 이미 정규화된 코드는 그대로 유지
        'jpn': 'jpn',
        'eng': 'eng',
        'kor': 'kor',
        'chi_sim': 'chi_sim',
        'chi_tra': 'chi_tra'
    }
    
    # 소문자로 변환 후 매핑
    norm_code = lang_map.get(lang_code.lower(), 'eng')  # 기본값은 영어
    
    return norm_code


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    텍스트를 청크로 분할
    
    Args:
        text: 원본 텍스트
        chunk_size: 청크 크기 (문자 단위)
        overlap: 청크 간 중복 문자 수
    
    Returns:
        텍스트 청크 목록
    """
    if not text:
        return []
    
    # 청크 크기가 텍스트 길이보다 크면 그대로 반환
    if chunk_size >= len(text):
        return [text]
    
    chunks = []
    pos = 0
    
    while pos < len(text):
        # 청크 끝 위치 계산
        end = min(pos + chunk_size, len(text))
        
        # 청크 추출
        chunk = text[pos:end]
        chunks.append(chunk)
        
        # 다음 시작 위치 계산 (중복 고려)
        pos = end - overlap if end < len(text) else len(text)
    
    return chunks


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    두 딕셔너리 병합 (중첩 딕셔너리 지원)
    
    Args:
        dict1: 기본 딕셔너리
        dict2: 덮어쓸 딕셔너리
    
    Returns:
        병합된 딕셔너리
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if (
            key in result and 
            isinstance(result[key], dict) and 
            isinstance(value, dict)
        ):
            # 중첩 딕셔너리는 재귀적으로 병합
            result[key] = merge_dicts(result[key], value)
        else:
            # 그 외에는 덮어쓰기
            result[key] = value
    
    return result
