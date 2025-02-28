"""
초고정밀 멀티랭귀지 OCR 시스템
- PDF 및 이미지에서 텍스트 추출
- 다국어 지원
- LLM 기반 데이터 추출
"""

__version__ = '1.0.0'
__author__ = 'OCR Team'
__email__ = 'support@ocr-service.com'
__license__ = 'MIT'

# 버전 관리
VERSION_INFO = {
    'major': 1,
    'minor': 0,
    'patch': 0,
    'release': 'final',
    'build': 0
}

# 편의성을 위한 주요 모듈/클래스 임포트
from src.core.config import config
from src.document.pdf_processor import PDFProcessor
from src.ocr.ensemble import OCREngine
from src.extraction.llm_processor import LLMProcessor
from src.storage.manager import StorageManager

# 로깅 설정 초기화
import logging
import os

# 로그 디렉토리 생성
logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# 기본 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'ocr_service.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"초고정밀 OCR 시스템 초기화 (버전: {__version__})")
