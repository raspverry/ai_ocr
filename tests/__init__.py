"""
테스트 모듈
- 시스템 기능 테스트
- 단위 및 통합 테스트
"""

import logging
import os
import sys
from pathlib import Path

# 상위 디렉토리를 시스템 경로에 추가 (테스트 실행을 위함)
sys.path.insert(0, str(Path(__file__).parent.parent))

# 테스트 데이터 디렉토리
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# 테스트 시 사용할 샘플 파일
SAMPLE_FILES = {
    'pdf': os.path.join(TEST_DATA_DIR, 'sample.pdf'),
    'image': os.path.join(TEST_DATA_DIR, 'sample.jpg'),
    'jpn_invoice': os.path.join(TEST_DATA_DIR, 'jpn_invoice.pdf'),
    'kor_document': os.path.join(TEST_DATA_DIR, 'kor_document.pdf'),
    'eng_form': os.path.join(TEST_DATA_DIR, 'eng_form.pdf'),
    'receipt': os.path.join(TEST_DATA_DIR, 'receipt.jpg'),
    'handwritten': os.path.join(TEST_DATA_DIR, 'handwritten.jpg')
}

# 테스트 설정
TEST_CONFIG = {
    'debug': True,
    'storage_type': 'local',
    'storage_path': os.path.join(TEST_DATA_DIR, 'storage'),
    'use_tesseract': True,
    'use_custom_model': False,
    'use_google_vision': False,
    'use_azure_form': False
}

# 테스트 데이터 디렉토리 생성
os.makedirs(TEST_DATA_DIR, exist_ok=True)
os.makedirs(TEST_CONFIG['storage_path'], exist_ok=True)
