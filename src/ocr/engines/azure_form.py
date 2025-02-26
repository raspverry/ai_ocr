"""
Azure Form Recognizer OCR 엔진
- Azure Form Recognizer를 사용한 문서 인식
- 양식 및 표 구조 추출에 특화
"""

import io
import logging
from typing import Dict, Any, Optional, Union, List
import numpy as np
from PIL import Image
import azure.ai.formrecognizer as form_recognizer

from src.core.config import config
from src.ocr.engines.base import BaseOCREngine

# 로거 설정
logger = logging.getLogger(__name__)


class AzureFormEngine(BaseOCREngine):
    """Azure Form Recognizer OCR 엔진"""
    
    def __init__(self):
        """초기화"""
        super().__init__()
        self.name = "azure_form"
        self.client = None
        
        # Azure Form Recognizer 초기화
        self._initialize_client()
    
    def _initialize_client(self):
        """Azure Form Recognizer 클라이언트 초기화"""
        try:
            # 설정에서 Azure 정보 가져오기
            endpoint = config.get('ocr.azure_form_endpoint')
            key = config.get('ocr.azure_form_key')
            
            if endpoint and key:
                # Azure 인증 및 클라이언트 생성
                self.credential = form_recognizer.AzureKeyCredential(key)
                self.client = form_recognizer.DocumentAnalysisClient(
                    endpoint=endpoint,
                    credential=self.credential
                )
                logger.info("Azure Form Recognizer 클라이언트 초기화 성공")
            else:
                logger.warning("Azure Form Recognizer 엔드포인트 또는 키가 설정되지 않았습니다.")
        
        except Exception as e:
            logger.error(f"Azure Form Recognizer 초기화 오류: {e}")
            self.client = None
    
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
                {"error": "Azure Form Recognizer가 초기화되지 않았습니다."}
            )
        
        try:
            # 이미지 전처리
            pil_image = self.preprocess_image(image)
            
            # 바이트로 변환
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            image_data = img_byte_arr.read()
            
            # Azure Form Recognizer 언어 매핑
            language_map = {
                'jpn': 'ja',
                'eng': 'en',
                'kor': 'ko',
                'chi_sim': 'zh-hans',
                'chi_tra': 'zh-hant'
            }
            
            norm_lang = self.normalize_language_code(lang)
            azure_lang = language_map.get(norm_lang)
            
            # Azure Form Recognizer 분석 실행
            poller = self.client.begin_analyze_document(
                "prebuilt-read",
                document=image_data,
                locale=azure_lang
            )
            
            # 폴링 결과 대기
            result = poller.result()
            
            # 결과 처리
            if not result.pages or len(result.pages) == 0:
                return self.format_result("", norm_lang, 0.0)
            
            # 텍스트 추출
            full_text = []
            confidence_sum = 0.0
            confidence_count = 0
            
            for page in result.pages:
                page_text = []
                
                for line in page.lines:
                    page_text.append(line.content)
                    
                    # 신뢰도 수집
                    if hasattr(line, 'confidence'):
                        confidence_sum += line.confidence
                        confidence_count += 1
                
                # 페이지 텍스트를 전체 텍스트에 추가
                full_text.append("\n".join(page_text))
            
            # 전체 텍스트 및 평균 신뢰도
            combined_text = "\n\n".join(full_text)
            avg_confidence = confidence_sum / confidence_count if confidence_count > 0 else 0.0
            
            # 언어 감지
            detected_lang = None
            if hasattr(result, 'locale'):
                # Azure 언어 코드를 테서랙트 코드로 변환
                reverse_language_map = {v: k for k, v in language_map.items()}
                detected_lang = reverse_language_map.get(result.locale)
            
            # 상세 결과 구성
            detailed_result = {
                'pages': [],
                'words': [],
                'tables': []
            }
            
            # 페이지 정보 수집
            for page_idx, page in enumerate(result.pages):
                page_info = {
                    'page_num': page_idx + 1,
                    'width': page.width,
                    'height': page.height,
                    'unit': page.unit,
                    'lines': []
                }
                
                # 라인 정보 수집
                for line in page.lines:
                    line_info = {
                        'text': line.content,
                        'confidence': line.confidence if hasattr(line, 'confidence') else 0.0,
                        'bbox': [
                            line.polygon[0].x, line.polygon[0].y,
                            line.polygon[2].x, line.polygon[2].y
                        ],
                        'words': []
                    }
                    
                    # 단어 정보 수집
                    for word in line.spans:
                        word_info = {
                            'text': word.content,
                            'confidence': word.confidence if hasattr(word, 'confidence') else 0.0,
                            'bbox': [
                                word.bounding_box[0].x, word.bounding_box[0].y,
                                word.bounding_box[2].x, word.bounding_box[2].y
                            ]
                        }
                        
                        line_info['words'].append(word_info)
                        detailed_result['words'].append(word_info)
                    
                    page_info['lines'].append(line_info)
                
                detailed_result['pages'].append(page_info)
            
            # 표 정보 수집
            if hasattr(result, 'tables'):
                for table_idx, table in enumerate(result.tables):
                    table_info = {
                        'table_id': table_idx + 1,
                        'rows': table.row_count,
                        'columns': table.column_count,
                        'cells': []
                    }
                    
                    # 셀 정보 수집
                    for cell in table.cells:
                        cell_info = {
                            'text': cell.content,
                            'row_index': cell.row_index,
                            'column_index': cell.column_index,
                            'row_span': cell.row_span,
                            'column_span': cell.column_span,
                            'confidence': cell.confidence if hasattr(cell, 'confidence') else 0.0,
                            'bbox': [
                                cell.bounding_box[0].x, cell.bounding_box[0].y,
                                cell.bounding_box[2].x, cell.bounding_box[2].y
                            ]
                        }
                        
                        table_info['cells'].append(cell_info)
                    
                    detailed_result['tables'].append(table_info)
            
            # 최종 결과 반환
            final_lang = detected_lang or norm_lang
            return self.format_result(combined_text, final_lang, avg_confidence, detailed_result)
        
        except Exception as e:
            logger.error(f"Azure Form Recognizer 인식 오류: {e}")
            return self.format_result(
                "", 
                lang or config.get('ocr.default_language', 'jpn'), 
                0.0, 
                {"error": str(e)}
            )
    
    async def analyze_form(self, 
                          image: Union[Image.Image, np.ndarray], 
                          form_type: str = "prebuilt-document") -> Dict[str, Any]:
        """
        이미지에서 양식 분석
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
            form_type: 양식 유형 (prebuilt-document, prebuilt-receipt, prebuilt-invoice, prebuilt-idcard, ...)
            
        Returns:
            양식 분석 결과
        """
        # API 클라이언트 확인
        if self.client is None:
            return {"error": "Azure Form Recognizer가 초기화되지 않았습니다."}
        
        try:
            # 이미지 전처리
            pil_image = self.preprocess_image(image)
            
            # 바이트로 변환
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            image_data = img_byte_arr.read()
            
            # Azure Form Recognizer 분석 실행
            poller = self.client.begin_analyze_document(
                form_type,
                document=image_data
            )
            
            # 폴링 결과 대기
            result = poller.result()
            
            # 결과 매핑 (form_type에 따라 다름)
            form_result = {}
            
            # 기본 문서 필드
            if hasattr(result, 'documents') and result.documents:
                for doc in result.documents:
                    doc_fields = {}
                    
                    for field_name, field in doc.fields.items():
                        if hasattr(field, 'value'):
                            if hasattr(field.value, 'content'):
                                doc_fields[field_name] = {
                                    'value': field.value.content,
                                    'confidence': field.confidence if hasattr(field, 'confidence') else 0.0
                                }
                            else:
                                doc_fields[field_name] = {
                                    'value': field.value,
                                    'confidence': field.confidence if hasattr(field, 'confidence') else 0.0
                                }
                    
                    form_result['fields'] = doc_fields
                    form_result['doc_type'] = doc.doc_type
                    break  # 첫 번째 문서만 처리
            
            # 표 정보
            if hasattr(result, 'tables'):
                tables = []
                for table in result.tables:
                    table_data = {
                        'rows': table.row_count,
                        'columns': table.column_count,
                        'cells': []
                    }
                    
                    for cell in table.cells:
                        cell_data = {
                            'text': cell.content,
                            'row': cell.row_index,
                            'column': cell.column_index,
                            'row_span': cell.row_span,
                            'column_span': cell.column_span
                        }
                        table_data['cells'].append(cell_data)
                    
                    tables.append(table_data)
                
                form_result['tables'] = tables
            
            # KV 페어 (키-값 쌍)
            if hasattr(result, 'key_value_pairs'):
                kv_pairs = {}
                for kv in result.key_value_pairs:
                    if hasattr(kv.key, 'content') and hasattr(kv.value, 'content'):
                        key = kv.key.content
                        value = kv.value.content
                        confidence = kv.confidence if hasattr(kv, 'confidence') else 0.0
                        kv_pairs[key] = {
                            'value': value,
                            'confidence': confidence
                        }
                
                form_result['key_value_pairs'] = kv_pairs
            
            # 엔티티
            if hasattr(result, 'entities'):
                entities = []
                for entity in result.entities:
                    entity_data = {
                        'category': entity.category,
                        'content': entity.content,
                        'confidence': entity.confidence if hasattr(entity, 'confidence') else 0.0
                    }
                    
                    # 하위 속성 (있는 경우)
                    if hasattr(entity, 'properties') and entity.properties:
                        props = {}
                        for prop in entity.properties:
                            props[prop.name] = {
                                'value': prop.value,
                                'confidence': prop.confidence if hasattr(prop, 'confidence') else 0.0
                            }
                        entity_data['properties'] = props
                    
                    entities.append(entity_data)
                
                form_result['entities'] = entities
            
            return form_result
        
        except Exception as e:
            logger.error(f"Azure Form 분석 오류: {e}")
            return {"error": str(e)}
