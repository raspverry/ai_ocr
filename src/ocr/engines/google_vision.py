"""
Google Cloud Vision OCR 엔진
- Google Cloud Vision API를 사용한 텍스트 인식
- 일본어 및 다국어 문서에 최적화된 설정
"""

import os
import io
import logging
from typing import Dict, Any, Optional, Union, List
import numpy as np
from PIL import Image
from google.cloud import vision
from google.cloud.vision_v1 import types
from google.cloud import translate_v2 as translate

from src.core.config import config
from src.ocr.engines.base import BaseOCREngine

# 로거 설정
logger = logging.getLogger(__name__)


class GoogleVisionEngine(BaseOCREngine):
    """Google Cloud Vision OCR 엔진"""
    
    def __init__(self):
        """초기화"""
        super().__init__()
        self.name = "google_vision"
        self.client = None
        self.translate_client = None
        
        # Google Cloud Vision API 초기화
        self._initialize_client()
    
    def _initialize_client(self):
        """Google Cloud Vision API 클라이언트 초기화"""
        try:
            # 환경 변수에서 인증 정보 확인
            credentials = config.get('ocr.google_credentials')
            
            if credentials:
                # 명시적 인증 정보 설정
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials
            
            # Vision API 클라이언트 생성
            self.client = vision.ImageAnnotatorClient()
            
            # Translate API 클라이언트 생성 (언어 감지용)
            self.translate_client = translate.Client()
            
            logger.info("Google Cloud Vision API 클라이언트 초기화 성공")
        
        except Exception as e:
            logger.error(f"Google Cloud Vision API 초기화 오류: {e}")
            self.client = None
            self.translate_client = None
    
    async def recognize(self, image: Union[Image.Image, np.ndarray], lang: Optional[str] = None) -> Dict[str, Any]:
        """
        이미지에서 텍스트 인식
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
            lang: 언어 코드 (None이면 자동 감지)
        
        Returns:
            인식 결과 (텍스트, 언어, 신뢰도 등)
        """
        # API 클라이언트 확인
        if self.client is None:
            return self.format_result(
                "", 
                lang or config.get('ocr.default_language', 'jpn'), 
                0.0, 
                {"error": "Google Cloud Vision API가 초기화되지 않았습니다."}
            )
        
        try:
            # 이미지 전처리
            pil_image = self.preprocess_image(image)
            
            # 바이트로 변환
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='PNG')
            content = img_byte_arr.getvalue()
            
            # Vision API 이미지 생성
            vision_image = vision.Image(content=content)
            
            # 언어 힌트 설정
            image_context = vision.ImageContext()
            
            if lang:
                # 테서랙트 언어 코드를 Google Vision API 코드로 변환
                lang_code_map = {
                    'jpn': 'ja',
                    'eng': 'en',
                    'kor': 'ko',
                    'chi_sim': 'zh-Hans',
                    'chi_tra': 'zh-Hant'
                }
                norm_lang = self.normalize_language_code(lang)
                vision_lang = lang_code_map.get(norm_lang, 'en')
                image_context.language_hints = [vision_lang]
            
            # OCR 실행 (document_text_detection은 문서에 최적화됨)
            response = self.client.document_text_detection(
                image=vision_image,
                image_context=image_context
            )
            
            # 결과 처리
            texts = []
            confidence_sum = 0.0
            confidence_count = 0
            
            # 전체 텍스트 추출
            if response.text_annotations:
                full_text = response.text_annotations[0].description
            else:
                full_text = ""
            
            # 페이지 신뢰도 계산
            if response.full_text_annotation and response.full_text_annotation.pages:
                for page in response.full_text_annotation.pages:
                    for block in page.blocks:
                        confidence_sum += block.confidence
                        confidence_count += 1
            
            avg_confidence = confidence_sum / confidence_count if confidence_count > 0 else 0.0
            
            # 언어 감지
            detected_lang = None
            
            # API 응답에서 언어 확인
            if response.full_text_annotation and response.full_text_annotation.pages:
                for page in response.full_text_annotation.pages:
                    for block in page.blocks:
                        if hasattr(block, 'property') and hasattr(block.property, 'detected_languages'):
                            for language in block.property.detected_languages:
                                if language.language_code:
                                    # Google 언어 코드를 테서랙트 코드로 변환
                                    lang_map = {
                                        'ja': 'jpn',
                                        'en': 'eng',
                                        'ko': 'kor',
                                        'zh-Hans': 'chi_sim',
                                        'zh-CN': 'chi_sim',
                                        'zh-Hant': 'chi_tra',
                                        'zh-TW': 'chi_tra'
                                    }
                                    detected_lang = lang_map.get(language.language_code)
                                    break
                        if detected_lang:
                            break
                    if detected_lang:
                        break
            
            # Translate API로 언어 감지 (백업 방법)
            if not detected_lang and self.translate_client and full_text.strip():
                try:
                    # 텍스트 샘플로 언어 감지
                    text_sample = full_text[:1000]  # 긴 텍스트 제한
                    detection = self.translate_client.detect_language(text_sample)
                    
                    if detection:
                        lang_code = detection['language']
                        # Google 언어 코드를 테서랙트 코드로 변환
                        lang_map = {
                            'ja': 'jpn',
                            'en': 'eng',
                            'ko': 'kor',
                            'zh-CN': 'chi_sim',
                            'zh-TW': 'chi_tra'
                        }
                        detected_lang = lang_map.get(lang_code)
                
                except Exception as e:
                    logger.warning(f"언어 감지 오류: {e}")
            
            # 최종 언어 결정
            final_lang = detected_lang or self.normalize_language_code(lang)
            
            # 상세 결과 추출
            detailed_result = {
                'blocks': [],
                'words': []
            }
            
            if response.full_text_annotation and response.full_text_annotation.pages:
                # 블록 정보 추출
                for page in response.full_text_annotation.pages:
                    for i, block in enumerate(page.blocks):
                        block_text = ""
                        block_confidence = 0.0
                        block_words = []
                        
                        # 블록 바운딩 박스
                        if block.bounding_box:
                            vertices = block.bounding_box.vertices
                            bbox = [
                                vertices[0].x, vertices[0].y,
                                vertices[2].x, vertices[2].y
                            ]
                        else:
                            bbox = [0, 0, 0, 0]
                        
                        # 블록 내 단어 추출
                        for paragraph in block.paragraphs:
                            for word in paragraph.words:
                                word_text = ''.join([symbol.text for symbol in word.symbols])
                                block_text += word_text + " "
                                
                                # 단어 바운딩 박스
                                if word.bounding_box:
                                    word_vertices = word.bounding_box.vertices
                                    word_bbox = [
                                        word_vertices[0].x, word_vertices[0].y,
                                        word_vertices[2].x, word_vertices[2].y
                                    ]
                                else:
                                    word_bbox = [0, 0, 0, 0]
                                
                                # 단어 정보
                                word_info = {
                                    'text': word_text,
                                    'confidence': word.confidence,
                                    'bbox': word_bbox
                                }
                                
                                block_words.append(word_info)
                                detailed_result['words'].append(word_info)
                        
                        # 블록 정보
                        block_info = {
                            'text': block_text.strip(),
                            'confidence': block.confidence,
                            'bbox': bbox,
                            'words': block_words
                        }
                        
                        detailed_result['blocks'].append(block_info)
            
            return self.format_result(full_text, final_lang, avg_confidence, detailed_result)
        
        except Exception as e:
            logger.error(f"Google Vision OCR 오류: {e}")
            return self.format_result(
                "", 
                lang or config.get('ocr.default_language', 'jpn'), 
                0.0, 
                {"error": str(e)}
            )
    
    async def detect_document_features(self, 
                                      image: Union[Image.Image, np.ndarray]) -> Dict[str, Any]:
        """
        문서의 다양한 특징 감지 (표, 양식, 로고 등)
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
            
        Returns:
            감지된 특징
        """
        # API 클라이언트 확인
        if self.client is None:
            return {"error": "Google Cloud Vision API가 초기화되지 않았습니다."}
        
        try:
            # 이미지 전처리
            pil_image = self.preprocess_image(image)
            
            # 바이트로 변환
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='PNG')
            content = img_byte_arr.getvalue()
            
            # Vision API 이미지 생성
            vision_image = vision.Image(content=content)
            
            # 특징 감지 API 요청
            document_response = self.client.document_text_detection(image=vision_image)
            label_response = self.client.label_detection(image=vision_image)
            
            # 결과 처리
            features = {
                'tables': [],
                'forms': False,
                'logos': [],
                'labels': []
            }
            
            # 표 감지 (간소화된 휴리스틱 방법)
            if document_response.full_text_annotation and document_response.full_text_annotation.pages:
                for page in document_response.full_text_annotation.pages:
                    # 일정한 간격으로 배열된 단어 찾기
                    if hasattr(page, 'tables'):
                        for table in page.tables:
                            table_info = {
                                'rows': table.rows,
                                'cols': table.cols,
                                'cells': []
                            }
                            
                            for cell in table.cells:
                                cell_text = ""
                                for paragraph in cell.paragraphs:
                                    for word in paragraph.words:
                                        word_text = ''.join([symbol.text for symbol in word.symbols])
                                        cell_text += word_text + " "
                                
                                table_info['cells'].append({
                                    'text': cell_text.strip(),
                                    'row': cell.row_span,
                                    'col': cell.col_span
                                })
                            
                            features['tables'].append(table_info)
            
            # 라벨 추출
            if label_response.label_annotations:
                for label in label_response.label_annotations:
                    features['labels'].append({
                        'description': label.description,
                        'score': label.score
                    })
                    
                    # 로고 관련 라벨 확인
                    if 'logo' in label.description.lower() or 'brand' in label.description.lower():
                        features['logos'].append({
                            'description': label.description,
                            'score': label.score
                        })
            
            # 양식 문서 여부 추정
            if document_response.full_text_annotation:
                text = document_response.full_text_annotation.text.lower()
                form_keywords = ['form', 'application', 'registration', '申請書', '応募', '登録', 'フォーム']
                
                for keyword in form_keywords:
                    if keyword in text:
                        features['forms'] = True
                        break
            
            return features
        
        except Exception as e:
            logger.error(f"Google Vision 특징 감지 오류: {e}")
            return {"error": str(e)}
