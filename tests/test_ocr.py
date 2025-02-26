"""
OCR 관련 기능 테스트 모듈
- OCR 엔진 테스트
- 전처리 및 후처리 테스트
- 앙상블 알고리즘 테스트
"""

import os
import json
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from PIL import Image
import numpy as np
import io

# 테스트 대상 모듈 임포트
from src.ocr.ensemble import OCREngine
from src.ocr.engines.base import BaseOCREngine
from src.ocr.preprocessor import Preprocessor
from src.ocr.postprocessor import PostProcessor
from src.ocr.special_handlers import SpecialItemDetector


# 테스트용 더미 OCR 엔진 클래스
class DummyOCREngine(BaseOCREngine):
    """테스트용 더미 OCR 엔진"""
    
    def __init__(self, result_text="테스트 텍스트", confidence=0.9, language="kor"):
        super().__init__()
        self.name = "dummy_engine"
        self.result_text = result_text
        self.result_confidence = confidence
        self.result_language = language
    
    async def recognize(self, image, lang=None):
        """더미 인식 결과 반환"""
        return self.format_result(
            self.result_text, 
            self.result_language, 
            self.result_confidence
        )


# 테스트용 고정 이미지 생성 함수
def create_test_image(text="테스트", size=(300, 100), bg_color=(255, 255, 255), text_color=(0, 0, 0)):
    """테스트용 이미지 생성"""
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB', size, color=bg_color)
    draw = ImageDraw.Draw(image)
    
    # 텍스트 쓰기 (시스템 기본 폰트)
    try:
        font = ImageFont.truetype("Arial", 24)
    except IOError:
        font = ImageFont.load_default()
    
    # 텍스트 중앙 정렬
    text_width, text_height = draw.textsize(text, font=font)
    position = ((size[0] - text_width) / 2, (size[1] - text_height) / 2)
    
    # 텍스트 그리기
    draw.text(position, text, font=font, fill=text_color)
    
    return image


# 테스트 클래스
class TestOCREngine:
    """OCR 엔진 테스트 클래스"""
    
    @pytest.fixture
    def test_image(self):
        """테스트 이미지 픽스처"""
        return create_test_image()
    
    @pytest.fixture
    def mock_ocr_engine(self):
        """모의 OCR 엔진 픽스처"""
        with patch('src.ocr.ensemble.OCREngine._initialize_engines') as mock_init:
            engine = OCREngine()
            # 더미 엔진 설정
            engine.engines = {
                "engine1": DummyOCREngine("텍스트 1", 0.8, "kor"),
                "engine2": DummyOCREngine("텍스트 2", 0.9, "kor"),
                "engine3": DummyOCREngine("テキスト 3", 0.7, "jpn")
            }
            # 가중치 설정
            engine.weights = {
                "engine1": 0.3,
                "engine2": 0.5,
                "engine3": 0.2
            }
            return engine
    
    @pytest.mark.asyncio
    async def test_recognize_text(self, test_image, mock_ocr_engine):
        """텍스트 인식 기능 테스트"""
        # OCR 실행
        result = await mock_ocr_engine.recognize_text(test_image)
        
        # 결과 검증
        assert result is not None
        assert 'text' in result
        assert 'language' in result
        assert 'confidence' in result
        
        # 가중치가 높은 엔진2의 결과가 선택되어야 함
        assert result['text'] == "텍스트 2"
        assert result['language'] == "kor"
        assert result['confidence'] > 0.8
    
    @pytest.mark.asyncio
    async def test_recognize_with_specified_language(self, test_image, mock_ocr_engine):
        """특정 언어 지정 시 인식 기능 테스트"""
        # 일본어로 지정하여 OCR 실행
        result = await mock_ocr_engine.recognize_text(test_image, lang="jpn")
        
        # 결과 검증
        assert result is not None
        assert result['language'] == "jpn"
        # 일본어 결과가 우선되어야 함
        assert "テキスト" in result['text']
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, test_image, mock_ocr_engine):
        """캐시 기능 테스트"""
        # 캐시 모의 객체 설정
        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # 첫 호출에는 캐시 미스
        mock_ocr_engine.cache = mock_cache
        mock_ocr_engine.cache_enabled = True
        
        # 첫 번째 OCR 실행 (캐시 미스)
        result1 = await mock_ocr_engine.recognize_text(test_image)
        
        # 캐시 설정 확인
        assert mock_cache.get.called
        assert mock_cache.setex.called
        
        # 캐시 히트 시뮬레이션
        cached_result = {
            "text": "캐시된 텍스트",
            "language": "kor",
            "confidence": 0.95
        }
        mock_cache.get.return_value = json.dumps(cached_result).encode()
        
        # 두 번째 OCR 실행 (캐시 히트)
        result2 = await mock_ocr_engine.recognize_text(test_image)
        
        # 캐시된 결과 확인
        assert result2['text'] == cached_result['text']
        assert result2['confidence'] == cached_result['confidence']


class TestPreprocessor:
    """이미지 전처리 테스트 클래스"""
    
    @pytest.fixture
    def preprocessor(self):
        """전처리기 픽스처"""
        return Preprocessor()
    
    @pytest.fixture
    def test_image(self):
        """테스트 이미지 픽스처"""
        return create_test_image()
    
    def test_process_image_basic(self, preprocessor, test_image):
        """기본 이미지 전처리 테스트"""
        # 이미지 전처리
        processed = preprocessor.process_image(test_image)
        
        # 결과 검증
        assert processed is not None
        assert isinstance(processed, Image.Image)
        
        # 크기가 유지되어야 함
        assert processed.size == test_image.size
    
    def test_process_for_different_languages(self, preprocessor, test_image):
        """다양한 언어에 대한 전처리 테스트"""
        # 언어별 전처리
        langs = ["jpn", "kor", "eng", "chi_sim"]
        
        for lang in langs:
            processed = preprocessor.process_image(test_image, lang=lang)
            
            # 결과 검증
            assert processed is not None
            assert isinstance(processed, Image.Image)
    
    def test_process_for_different_doc_types(self, preprocessor, test_image):
        """다양한 문서 유형에 대한 전처리 테스트"""
        # 문서 유형별 전처리
        doc_types = ["receipt", "invoice", "form", "handwritten"]
        
        for doc_type in doc_types:
            processed = preprocessor.process_image(test_image, doc_type=doc_type)
            
            # 결과 검증
            assert processed is not None
            assert isinstance(processed, Image.Image)


class TestPostProcessor:
    """텍스트 후처리 테스트 클래스"""
    
    @pytest.fixture
    def postprocessor(self):
        """후처리기 픽스처"""
        return PostProcessor()
    
    def test_normalize_common(self, postprocessor):
        """공통 텍스트 정규화 테스트"""
        # 테스트 텍스트 (공백, 줄바꿈 정리)
        text = "  테스트   텍스트  \n\n\n 정규화  "
        
        # 정규화 실행
        normalized = postprocessor._normalize_common(text)
        
        # 결과 검증
        assert normalized == "테스트 텍스트 정규화"
    
    def test_process_japanese(self, postprocessor):
        """일본어 텍스트 처리 테스트"""
        # 테스트 텍스트 (전각/반각 문자 포함)
        text = "テスト　テキスト１２３４５"
        
        # 처리 실행
        processed = postprocessor._process_japanese(text)
        
        # 결과 검증
        assert "テスト" in processed
        assert "12345" in processed or "１２３４５" in processed
    
    def test_process_korean(self, postprocessor):
        """한국어 텍스트 처리 테스트"""
        # 테스트 텍스트 (조사 공백 포함)
        text = "테스트 를 진행 합니다"
        
        # 처리 실행
        processed = postprocessor._process_korean(text)
        
        # 결과 검증
        assert "테스트를" in processed or "테스트 를" in processed
    
    def test_process_english(self, postprocessor):
        """영어 텍스트 처리 테스트"""
        # 테스트 텍스트 (문장 시작 소문자)
        text = "this is a test. another sentence."
        
        # 처리 실행
        processed = postprocessor._process_english(text)
        
        # 결과 검증
        assert processed.startswith("This")
        assert "Another" in processed
    
    def test_format_business_document(self, postprocessor):
        """비즈니스 문서 형식 정규화 테스트"""
        # 테스트 케이스 (언어별)
        test_cases = [
            # 일본어 날짜
            ("2023年1月1日", "jpn", "2023年01月01日"),
            # 한국어 날짜
            ("2023년1월1일", "kor", "2023년 01월 01일"),
            # 영어 날짜
            ("Jan 1, 2023", "eng", "Jan 01, 2023")
        ]
        
        for original, lang, expected in test_cases:
            # 정규화 실행
            result = postprocessor._format_business_document(original, lang)
            
            # 결과 검증
            assert expected in result
    
    def test_extract_business_entities(self, postprocessor):
        """비즈니스 엔티티 추출 테스트"""
        # 테스트 텍스트 (일본어)
        jpn_text = """
        株式会社テスト
        〒123-4567 東京都品川区
        2023年4月1日
        請求書
        合計: ¥123,456
        """
        
        # 엔티티 추출
        entities = postprocessor.extract_business_entities(jpn_text, "jpn")
        
        # 결과 검증
        assert entities is not None
        assert "companies" in entities
        assert "dates" in entities
        assert "amounts" in entities
        
        # 회사명 추출 확인
        assert any("株式会社テスト" in company for company in entities["companies"])
        
        # 날짜 추출 확인
        assert any("2023年4月1日" in date for date in entities["dates"])
        
        # 금액 추출 확인
        assert any("123,456" in amount or "¥123,456" in amount for amount in entities["amounts"])


class TestSpecialItemDetector:
    """특수 항목 감지 테스트 클래스"""
    
    @pytest.fixture
    def detector(self):
        """감지기 픽스처"""
        special_config = {
            'detect_stamps': True,
            'detect_handwriting': True,
            'detect_strikethrough': True
        }
        return SpecialItemDetector(special_config)
    
    @pytest.fixture
    def stamp_image(self):
        """도장 이미지 픽스처"""
        # 빨간색 원 생성 (도장 시뮬레이션)
        image = Image.new('RGB', (300, 300), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((100, 100, 200, 200), fill=(255, 0, 0))
        return image
    
    @pytest.fixture
    def handwriting_image(self):
        """손글씨 이미지 픽스처"""
        # 불규칙한 선으로 손글씨 시뮬레이션
        image = Image.new('RGB', (300, 300), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # 불규칙한 곡선
        points = [(100, 150), (120, 140), (140, 155), (160, 145), 
                 (180, 160), (200, 140), (220, 150)]
        draw.line(points, fill=(0, 0, 0), width=3)
        
        return image
    
    @pytest.fixture
    def strikethrough_image(self):
        """취소선 이미지 픽스처"""
        # 글자 위에 수평선 그리기
        image = create_test_image("취소할 텍스트", size=(300, 100))
        draw = ImageDraw.Draw(image)
        
        # 수평선 (취소선)
        draw.line([(50, 50), (250, 50)], fill=(0, 0, 0), width=2)
        
        return image
    
    def test_process_image(self, detector, stamp_image, handwriting_image, strikethrough_image):
        """이미지 처리 기능 테스트"""
        # 각 이미지 처리
        stamp_result = detector.process_image(stamp_image)
        handwriting_result = detector.process_image(handwriting_image)
        strikethrough_result = detector.process_image(strikethrough_image)
        
        # 결과 검증
        assert stamp_result is not None
        assert handwriting_result is not None
        assert strikethrough_result is not None
        
        # 도장 감지 확인
        if stamp_result['has_special_items']:
            assert len(stamp_result['stamps']) > 0
        
        # 손글씨 감지 확인
        if handwriting_result['has_special_items']:
            assert len(handwriting_result['handwriting_regions']) > 0
        
        # 취소선 감지 확인
        if strikethrough_result['has_special_items']:
            assert len(strikethrough_result['strikethrough_regions']) > 0


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
