"""
웹 인터페이스 모듈
- 웹 UI 제공
- 사용자 인터페이스 및 상호작용
"""

import logging
from typing import Dict, Any, List

# 모듈 메타데이터
__module_name__ = 'web'
__version__ = '1.0.0'

# 로거 설정
logger = logging.getLogger(__name__)

# 페이지 정보
PAGES = {
    'home': '홈',
    'upload': '업로드',
    'documents': '문서 목록',
    'view': '문서 보기',
    'settings': '설정',
    'extraction': '데이터 추출',
    'exports': '내보내기',
    'account': '계정'
}

# 사용자 역할
USER_ROLES = {
    'admin': '관리자',
    'user': '일반 사용자',
    'guest': '게스트'
}

# 페이지당 항목 수
DEFAULT_ITEMS_PER_PAGE = 20

# 편의성을 위한 주요 모듈/클래스 임포트
from src.web.app import create_app
from src.web.forms import (
    LoginForm,
    UploadForm,
    SettingsForm,
    ExtractionForm
)

# 모듈 초기화 로그
logger.info(f"웹 인터페이스 모듈 초기화 완료")
