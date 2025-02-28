"""
보안 관련 유틸리티 모듈
- 비밀번호 해싱 및 검증
- 토큰 생성 및 검증
"""

import os
import time
import hashlib
import hmac
import base64
import secrets
import logging
from typing import Dict, Any, Optional, Tuple, Union

# 로거 설정
logger = logging.getLogger(__name__)

# 비밀번호 해싱 설정
HASH_ALGORITHM = 'sha256'
HASH_ITERATIONS = 100000
SALT_SIZE = 32
KEY_LENGTH = 64

# 토큰 설정
TOKEN_BYTES = 32
TOKEN_EXPIRY = 86400  # 1일 (초 단위)
TOKEN_SECRET = os.environ.get('TOKEN_SECRET', 'change-this-to-a-secure-secret')


def generate_salt(size: int = SALT_SIZE) -> bytes:
    """
    무작위 솔트 생성
    
    Args:
        size: 솔트 크기 (바이트)
    
    Returns:
        무작위 솔트 바이트
    """
    return os.urandom(size)


def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    비밀번호 해싱
    
    Args:
        password: 평문 비밀번호
        salt: 솔트 (None이면 생성)
    
    Returns:
        (해시, 솔트) 튜플
    """
    if salt is None:
        salt = generate_salt()
    
    # 비밀번호를 바이트로 인코딩
    password_bytes = password.encode('utf-8')
    
    # PBKDF2 해싱
    hash_bytes = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password_bytes,
        salt,
        HASH_ITERATIONS,
        KEY_LENGTH
    )
    
    return hash_bytes, salt


def verify_password(password: str, hash_bytes: bytes, salt: bytes) -> bool:
    """
    비밀번호 검증
    
    Args:
        password: 평문 비밀번호
        hash_bytes: 저장된 해시
        salt: 저장된 솔트
    
    Returns:
        비밀번호 일치 여부
    """
    # 비밀번호 해싱
    test_hash, _ = hash_password(password, salt)
    
    # 상수 시간 비교 (타이밍 공격 방지)
    return hmac.compare_digest(test_hash, hash_bytes)


def format_hash_for_storage(hash_bytes: bytes, salt: bytes) -> str:
    """
    해시와 솔트를 저장 형식으로 변환
    
    Args:
        hash_bytes: 해시 바이트
        salt: 솔트 바이트
    
    Returns:
        저장용 문자열 (Base64 인코딩)
    """
    # Base64 인코딩
    hash_b64 = base64.b64encode(hash_bytes).decode('utf-8')
    salt_b64 = base64.b64encode(salt).decode('utf-8')
    
    # 형식: algorithm$iterations$salt$hash
    return f"{HASH_ALGORITHM}${HASH_ITERATIONS}${salt_b64}${hash_b64}"


def parse_hash_from_storage(hash_str: str) -> Tuple[bytes, bytes, str, int]:
    """
    저장된 해시 문자열 파싱
    
    Args:
        hash_str: 저장된 해시 문자열
    
    Returns:
        (해시, 솔트, 알고리즘, 반복 횟수) 튜플
    
    Raises:
        ValueError: 잘못된 해시 형식
    """
    # 형식: algorithm$iterations$salt$hash
    parts = hash_str.split('$')
    
    if len(parts) != 4:
        raise ValueError("잘못된 해시 형식")
    
    algorithm = parts[0]
    iterations = int(parts[1])
    salt = base64.b64decode(parts[2])
    hash_bytes = base64.b64decode(parts[3])
    
    return hash_bytes, salt, algorithm, iterations


def generate_token(user_id: Union[str, int], expiry: Optional[int] = None) -> str:
    """
    인증 토큰 생성
    
    Args:
        user_id: 사용자 ID
        expiry: 만료 시간 (초 단위, None이면 기본값 사용)
    
    Returns:
        생성된 토큰
    """
    # 토큰 바이트 생성
    token_bytes = secrets.token_bytes(TOKEN_BYTES)
    token_b64 = base64.urlsafe_b64encode(token_bytes).decode('utf-8').rstrip('=')
    
    # 만료 시간 계산
    if expiry is None:
        expiry = int(time.time()) + TOKEN_EXPIRY
    else:
        expiry = int(time.time()) + expiry
    
    # 서명 생성
    data = f"{token_b64}.{user_id}.{expiry}"
    signature = hmac.new(
        TOKEN_SECRET.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')
    
    # 토큰 형식: token.user_id.expiry.signature
    return f"{token_b64}.{user_id}.{expiry}.{signature_b64}"


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    인증 토큰 검증
    
    Args:
        token: 검증할 토큰
    
    Returns:
        검증 결과 (None이면 검증 실패)
    """
    try:
        # 토큰 파싱
        parts = token.split('.')
        if len(parts) != 4:
            logger.warning("잘못된 토큰 형식")
            return None
        
        token_b64, user_id, expiry_str, signature_b64 = parts
        
        # 만료 시간 확인
        expiry = int(expiry_str)
        if expiry < time.time():
            logger.warning("만료된 토큰")
            return None
        
        # 서명 검증
        data = f"{token_b64}.{user_id}.{expiry}"
        expected_signature = hmac.new(
            TOKEN_SECRET.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).digest()
        expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode('utf-8').rstrip('=')
        
        # 상수 시간 비교 (타이밍 공격 방지)
        if not hmac.compare_digest(signature_b64, expected_signature_b64):
            logger.warning("잘못된 토큰 서명")
            return None
        
        # 토큰 복원
        token_bytes = base64.urlsafe_b64decode(token_b64 + '=' * (4 - len(token_b64) % 4))
        
        # 검증 성공
        return {
            'token': token_b64,
            'user_id': user_id,
            'expiry': expiry,
            'token_bytes': token_bytes
        }
    
    except Exception as e:
        logger.error(f"토큰 검증 오류: {e}")
        return None


def sanitize_html(html: str) -> str:
    """
    HTML 삭제 및 특수문자 이스케이프
    
    Args:
        html: HTML 문자열
    
    Returns:
        정제된 문자열
    """
    import re
    
    # HTML 태그 제거
    text = re.sub(r'<[^>]*>', '', html)
    
    # 특수문자 이스케이프
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#39;')
    
    return text
