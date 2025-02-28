"""
스토리지 관리 모듈
- 파일 저장 및 관리
- 다양한 스토리지 백엔드 지원 (로컬, S3, GCS)
"""

import logging
from typing import Dict, Any, List

# 모듈 메타데이터
__module_name__ = 'storage'
__version__ = '1.0.0'

# 로거 설정
logger = logging.getLogger(__name__)

# 지원하는 스토리지 유형
STORAGE_TYPES = {
    'local': '로컬 파일 시스템',
    's3': 'Amazon S3',
    'gcs': 'Google Cloud Storage'
}

# 스토리지 폴더 구조
FOLDER_STRUCTURE = {
    'uploads': '업로드된 원본 파일',
    'processed': '처리된 파일',
    'temp': '임시 파일',
    'results': '결과 파일',
    'exports': '내보내기 파일'
}

# 편의성을 위한 주요 모듈/클래스 임포트
from src.storage.manager import StorageManager

# 모듈 초기화 로그
logger.info(f"스토리지 관리 모듈 초기화 완료")
