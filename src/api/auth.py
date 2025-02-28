"""
API 인증 및 권한 관리 모듈
- API 키 검증
- 권한 확인
"""

import os
import time
import hashlib
import hmac
import secrets
import logging
from typing import Dict, Any, Optional, List
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader

from src.core.config import config
from src.utils.security import verify_token

# 로거 설정
logger = logging.getLogger(__name__)

# API 키 헤더 설정
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# API 키 캐시 (메모리 캐시)
API_KEY_CACHE = {}

# API 키 활성화 여부
API_KEY_ENABLED = config.get('api.key_required', False)


def get_api_key(api_key_header: str = Security(API_KEY_HEADER)) -> Optional[str]:
    """
    API 키 가져오기
    
    Args:
        api_key_header: API 키 헤더 값
    
    Returns:
        API 키 또는 None
    """
    # API 키가 필요 없는 경우
    if not API_KEY_ENABLED:
        return None
    
    # API 키 헤더 확인
    if not api_key_header:
        raise HTTPException(
            status_code=401,
            detail="API 키가 필요합니다",
            headers={"WWW-Authenticate": "APIKey"},
        )
    
    return api_key_header


def verify_api_key(api_key: str = Depends(get_api_key)) -> Dict[str, Any]:
    """
    API 키 검증
    
    Args:
        api_key: API 키
    
    Returns:
        API 키 메타데이터
    
    Raises:
        HTTPException: API 키가 유효하지 않음
    """
    # API 키가 필요 없는 경우
    if not API_KEY_ENABLED:
        return {"valid": True, "user_id": "anonymous", "role": "anonymous"}
    
    # API 키 캐시 확인
    if api_key in API_KEY_CACHE:
        cached_data = API_KEY_CACHE[api_key]
        
        # 캐시 만료 확인
        if cached_data.get('expiry', 0) > time.time():
            return cached_data
        
        # 만료된 캐시 삭제
        del API_KEY_CACHE[api_key]
    
    # 환경 변수에서 API 키 확인 (개발용)
    dev_api_key = os.environ.get('DEV_API_KEY')
    if dev_api_key and api_key == dev_api_key:
        result = {
            "valid": True,
            "user_id": "dev",
            "role": "admin",
            "expiry": time.time() + 3600  # 1시간 캐시
        }
        API_KEY_CACHE[api_key] = result
        return result
    
    # 토큰 형식 API 키 검증
    token_data = verify_token(api_key)
    if token_data:
        result = {
            "valid": True,
            "user_id": token_data['user_id'],
            "role": "user",  # 기본 역할
            "expiry": token_data['expiry']
        }
        API_KEY_CACHE[api_key] = result
        return result
    
    # TODO: 실제 API 키 검증 로직 (데이터베이스 조회 등)
    # 여기에 구현
    
    # 기본적으로 인증 실패
    raise HTTPException(
        status_code=401,
        detail="유효하지 않은 API 키",
        headers={"WWW-Authenticate": "APIKey"},
    )


def check_permissions(api_key_data: Dict[str, Any] = Depends(verify_api_key), 
                     required_roles: List[str] = None) -> Dict[str, Any]:
    """
    권한 확인
    
    Args:
        api_key_data: API 키 메타데이터
        required_roles: 필요한 역할 목록
    
    Returns:
        API 키 메타데이터
    
    Raises:
        HTTPException: 권한 없음
    """
    # 역할이 지정되지 않은 경우 모든 인증된 사용자 허용
    if not required_roles:
        return api_key_data
    
    # 사용자 역할 확인
    user_role = api_key_data.get('role')
    
    # 관리자는 모든 접근 허용
    if user_role == 'admin':
        return api_key_data
    
    # 역할 확인
    if user_role not in required_roles:
        raise HTTPException(
            status_code=403,
            detail="이 작업을 수행할 권한이 없습니다",
        )
    
    return api_key_data


def generate_api_key(user_id: str, role: str = "user", expiry: int = 30 * 86400) -> str:
    """
    API 키 생성
    
    Args:
        user_id: 사용자 ID
        role: 사용자 역할
        expiry: 만료 시간 (초, 기본 30일)
    
    Returns:
        생성된 API 키
    """
    from src.utils.security import generate_token
    
    # 토큰 기반 API 키 생성
    api_key = generate_token(user_id, expiry)
    
    # 메타데이터를 캐시에 저장
    API_KEY_CACHE[api_key] = {
        "valid": True,
        "user_id": user_id,
        "role": role,
        "expiry": time.time() + expiry
    }
    
    return api_key


def revoke_api_key(api_key: str) -> bool:
    """
    API 키 취소
    
    Args:
        api_key: 취소할 API 키
    
    Returns:
        성공 여부
    """
    # 캐시에서 삭제
    if api_key in API_KEY_CACHE:
        del API_KEY_CACHE[api_key]
    
    # TODO: 실제 API 키 취소 로직 (데이터베이스 업데이트 등)
    # 여기에 구현
    
    return True


def cleanup_expired_keys() -> int:
    """
    만료된 API 키 정리
    
    Returns:
        정리된 키 수
    """
    current_time = time.time()
    expired_keys = [
        key for key, data in API_KEY_CACHE.items()
        if data.get('expiry', 0) < current_time
    ]
    
    # 만료된 키 삭제
    for key in expired_keys:
        del API_KEY_CACHE[key]
    
    return len(expired_keys)


def get_rate_limit(api_key_data: Dict[str, Any]) -> int:
    """
    API 키에 따른 비율 제한 가져오기
    
    Args:
        api_key_data: API 키 메타데이터
    
    Returns:
        분당 최대 요청 수
    """
    # 역할별 비율 제한
    rate_limits = {
        'admin': 1000,   # 관리자
        'user': 100,     # 일반 사용자
        'anonymous': 10  # 익명 사용자
    }
    
    role = api_key_data.get('role', 'anonymous')
    return rate_limits.get(role, 10)  # 기본 10 요청/분
