"""
OCR 엔진 기본 인터페이스
- 모든 OCR 엔진이 구현해야 하는 기본 인터페이스 정의
- OCR 엔진 공통 유틸리티 제공
"""

import abc
import logging
from typing import Dict, Any, Optional, Union
from PIL import Image
import numpy as np

# 로거 설정
logger = logging.getLogger(__name__)


class BaseOCREngine(abc.ABC):
    """OCR 엔진 기본 인터페이스"""
    
    def __init__(self):
        """초기화"""
        self.name = self.__class__.__name__
    
    @abc.abstractmethod
    async def recognize(self, image: Union[Image.Image, np.ndarray], lang: Optional[str] = None) -> Dict[str, Any]:
        """
        이미지에서 텍스트 인식 (모든 OCR 엔진이 구현해야 함)
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
            lang: 언어 코드 (None이면 자동 감지)
        
        Returns:
            인식 결과 딕셔너리 (최소한 'text', 'language', 'confidence' 키 포함)
        """
        pass
    
    def preprocess_image(self, image: Union[Image.Image, np.ndarray]) -> Image.Image:
        """
        이미지 전처리 (필요에 따라 오버라이드)
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
        
        Returns:
            전처리된 PIL 이미지
        """
        # NumPy 배열을 PIL 이미지로 변환
        if isinstance(image, np.ndarray):
            # 3채널 RGB 이미지인지 확인
            if len(image.shape) == 3 and image.shape[2] == 3:
                return Image.fromarray(image)
            # 1채널 그레이스케일 이미지
            elif len(image.shape) == 2:
                return Image.fromarray(image).convert('RGB')
            # 알파 채널 포함 이미지
            elif len(image.shape) == 3 and image.shape[2] == 4:
                return Image.fromarray(image).convert('RGB')
            else:
                logger.warning(f"알 수 없는 이미지 형식: {image.shape}")
                return Image.fromarray(image)
        
        # 이미 PIL 이미지인 경우
        return image
    
    def ensure_rgb_image(self, image: Image.Image) -> Image.Image:
        """
        이미지가 RGB 모드인지 확인하고 아니면 변환
        
        Args:
            image: PIL 이미지
            
        Returns:
            RGB 모드의 PIL 이미지
        """
        if image.mode != 'RGB':
            return image.convert('RGB')
        return image
    
    def normalize_language_code(self, lang: Optional[str] = None, default_lang: str = 'jpn') -> str:
        """
        언어 코드 정규화
        
        Args:
            lang: 입력 언어 코드
            default_lang: 기본 언어 코드
            
        Returns:
            정규화된 언어 코드
        """
        if not lang:
            return default_lang
        
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
        normalized = lang_map.get(lang.lower(), default_lang)
        return normalized
    
    def format_result(self, 
                     text: str, 
                     language: str, 
                     confidence: float, 
                     extra_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        표준 형식의 OCR 결과 생성
        
        Args:
            text: 인식된 텍스트
            language: 언어 코드
            confidence: 신뢰도 (0.0-1.0)
            extra_data: 추가 데이터
            
        Returns:
            표준 형식의 OCR 결과 딕셔너리
        """
        result = {
            'text': text,
            'language': self.normalize_language_code(language),
            'confidence': min(1.0, max(0.0, confidence)),  # 0.0-1.0 범위로 제한
            'engine': self.name
        }
        
        # 추가 데이터가 있으면 병합
        if extra_data:
            result.update(extra_data)
        
        return result
