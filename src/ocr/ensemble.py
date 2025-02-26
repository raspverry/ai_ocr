"""
OCR 엔진 앙상블 모듈
- 여러 OCR 엔진 결과 통합
- 가중치 기반 앙상블
- 캐싱 지원
"""

import io
import json
import hashlib
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
import numpy as np
import redis

from src.core.config import config
from src.ocr.engines.base import BaseOCREngine
from src.ocr.engines.custom_model import CustomModelEngine
from src.ocr.engines.tesseract import TesseractEngine
from src.ocr.engines.google_vision import GoogleVisionEngine
from src.ocr.engines.azure_form import AzureFormEngine
from src.ocr.special_handlers import SpecialItemDetector
from src.ocr.postprocessor import PostProcessor

# 로거 설정
logger = logging.getLogger(__name__)


class OCREngine:
    """OCR 엔진 앙상블 클래스"""
    
    def __init__(self):
        """초기화"""
        # OCR 엔진 설정
        self.use_custom_model = config.get('ocr.use_custom_model', True)
        self.use_tesseract = config.get('ocr.use_tesseract', True)
        self.use_google_vision = config.get('ocr.use_google_vision', True)
        self.use_azure_form = config.get('ocr.use_azure_form', True)
        
        # 앙상블 가중치
        self.weights = config.get('ocr.ensemble_weights', {
            'custom_model': 0.5,
            'tesseract': 0.2,
            'google_vision': 0.2,
            'azure_form': 0.1
        })
        
        # 신뢰도 임계값
        self.confidence_threshold = config.get('ocr.confidence_threshold', 0.85)
        
        # 특수 항목 처리
        special_config = {
            'detect_stamps': config.get('ocr.special_items.detect_stamps', True),
            'detect_handwriting': config.get('ocr.special_items.detect_handwriting', True),
            'detect_strikethrough': config.get('ocr.special_items.detect_strikethrough', True)
        }
        self.special_detector = SpecialItemDetector(special_config)
        
        # 텍스트 후처리
        self.post_processor = PostProcessor()
        
        # OCR 엔진 초기화
        self.engines = {}
        self._initialize_engines()
        
        # 캐싱 설정
        self.cache_enabled = config.get('storage.cache_enabled', True)
        self.cache_ttl = config.get('storage.cache_ttl', 3600)
        
        if self.cache_enabled:
            try:
                redis_url = config.get('queue.redis_url', 'redis://localhost:6379/0')
                self.cache = redis.Redis.from_url(redis_url)
                logger.info("Redis 캐시 초기화 성공")
            except Exception as e:
                logger.error(f"Redis 캐시 초기화 오류: {e}")
                self.cache_enabled = False
                self.cache = None
    
    def _initialize_engines(self):
        """OCR 엔진 초기화"""
        try:
            # 커스텀 모델 엔진
            if self.use_custom_model:
                self.engines['custom_model'] = CustomModelEngine()
                logger.info("커스텀 OCR 모델 초기화 성공")
            
            # 테서랙트 엔진
            if self.use_tesseract:
                self.engines['tesseract'] = TesseractEngine()
                logger.info("테서랙트 OCR 엔진 초기화 성공")
            
            # Google Vision 엔진
            if self.use_google_vision:
                self.engines['google_vision'] = GoogleVisionEngine()
                logger.info("Google Vision OCR 엔진 초기화 성공")
            
            # Azure Form Recognizer 엔진
            if self.use_azure_form:
                self.engines['azure_form'] = AzureFormEngine()
                logger.info("Azure Form Recognizer OCR 엔진 초기화 성공")
            
            # 최소 하나의 엔진 필요
            if not self.engines:
                logger.warning("활성화된 OCR 엔진이 없습니다. 기본 테서랙트 엔진을 사용합니다.")
                self.engines['tesseract'] = TesseractEngine()
        
        except Exception as e:
            logger.error(f"OCR 엔진 초기화 오류: {e}")
            # 오류 발생 시 테서랙트 엔진이라도 초기화
            if 'tesseract' not in self.engines:
                self.engines['tesseract'] = TesseractEngine()
    
    async def recognize_text(self, 
                           image: Image.Image, 
                           lang: Optional[str] = None, 
                           use_cache: bool = True) -> Dict[str, Any]:
        """
        이미지에서 텍스트 인식
        
        Args:
            image: PIL 이미지
            lang: 언어 코드 (None이면 자동 감지)
            use_cache: 캐시 사용 여부
        
        Returns:
            인식 결과
        """
        # 캐시 확인
        if use_cache and self.cache_enabled:
            cache_result = self._check_cache(image, lang)
            if cache_result:
                logger.info("캐시에서 OCR 결과 로드")
                return cache_result
        
        # 특수 항목 감지
        special_items = self.special_detector.process_image(image)
        
        # OCR 엔진별 인식 병렬 실행
        engine_results = await self._run_ocr_engines(image, lang)
        
        # 결과가 없으면 오류 반환
        if not engine_results:
            return {
                'text': '',
                'language': lang or config.get('ocr.default_language', 'jpn'),
                'confidence': 0.0,
                'special_items': special_items,
                'error': 'OCR 엔진 결과 없음'
            }
        
        # 앙상블 결과 계산
        ensemble_result = self._ensemble_results(engine_results, lang)
        
        # 특수 항목 정보 추가
        ensemble_result['special_items'] = special_items
        
        # 후처리
        processed_result = self.post_processor.process(ensemble_result)
        
        # 캐시에 저장
        if use_cache and self.cache_enabled:
            self._save_to_cache(image, lang, processed_result)
        
        return processed_result
    
    async def _run_ocr_engines(self, 
                              image: Image.Image, 
                              lang: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        모든 OCR 엔진으로 인식 실행
        
        Args:
            image: PIL 이미지
            lang: 언어 코드
        
        Returns:
            엔진별 인식 결과
        """
        # 각 엔진의 인식 태스크 생성
        tasks = []
        for engine_name, engine in self.engines.items():
            tasks.append(self._run_single_engine(engine_name, engine, image, lang))
        
        # 모든 태스크 병렬 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 매핑
        engine_results = {}
        for i, (engine_name, _) in enumerate(self.engines.items()):
            if isinstance(results[i], Exception):
                logger.error(f"{engine_name} OCR 오류: {results[i]}")
                continue
            
            engine_results[engine_name] = results[i]
        
        return engine_results
    
    async def _run_single_engine(self, 
                               engine_name: str, 
                               engine: BaseOCREngine, 
                               image: Image.Image, 
                               lang: Optional[str] = None) -> Dict[str, Any]:
        """
        단일 OCR 엔진으로 인식 실행
        
        Args:
            engine_name: 엔진 이름
            engine: OCR 엔진 인스턴스
            image: PIL 이미지
            lang: 언어 코드
        
        Returns:
            인식 결과
        """
        try:
            # 엔진 실행
            result = await engine.recognize(image, lang)
            
            logger.debug(f"{engine_name} OCR 결과: {result.get('confidence', 0):.2f} 신뢰도")
            return result
        
        except Exception as e:
            logger.error(f"{engine_name} OCR 오류: {e}")
            # 실패 시 최소한의 결과 반환
            return {
                'text': '',
                'language': lang or config.get('ocr.default_language', 'jpn'),
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _ensemble_results(self, 
                         engine_results: Dict[str, Dict[str, Any]], 
                         lang: Optional[str] = None) -> Dict[str, Any]:
        """
        OCR 엔진 결과 앙상블
        
        Args:
            engine_results: 엔진별 인식 결과
            lang: 언어 코드
        
        Returns:
            앙상블 결과
        """
        if not engine_results:
            return {
                'text': '',
                'language': lang or config.get('ocr.default_language', 'jpn'),
                'confidence': 0.0,
                'error': 'OCR 결과 없음'
            }
        
        # 언어 결정 (투표 방식)
        detected_languages = []
        for engine_name, result in engine_results.items():
            if 'language' in result and result['language']:
                detected_languages.append(result['language'])
        
        if detected_languages:
            # 가장 빈번한 언어 선택
            language_counts = {}
            for detected_lang in detected_languages:
                language_counts[detected_lang] = language_counts.get(detected_lang, 0) + 1
            
            final_language = max(language_counts.items(), key=lambda x: x[1])[0]
        else:
            final_language = lang or config.get('ocr.default_language', 'jpn')
        
        # 가중치 기반 텍스트 선택
        weighted_texts = []
        total_weight = 0.0
        
        for engine_name, result in engine_results.items():
            if 'text' not in result or not result['text'].strip():
                continue
            
            # 신뢰도 및 가중치 계산
            confidence = result.get('confidence', 0.0)
            engine_weight = self.weights.get(engine_name, 0.0)
            
            if confidence >= self.confidence_threshold:
                weighted_score = confidence * engine_weight
                weighted_texts.append((result['text'], weighted_score))
                total_weight += weighted_score
        
        if not weighted_texts:
            # 신뢰도 높은 결과가 없으면 가장 긴 텍스트 선택
            all_texts = [(result.get('text', ''), len(result.get('text', ''))) 
                          for engine_name, result in engine_results.items() 
                          if 'text' in result and result['text'].strip()]
            
            if all_texts:
                # 길이 기준으로 정렬하여 가장 긴 텍스트 선택
                all_texts.sort(key=lambda x: x[1], reverse=True)
                final_text = all_texts[0][0]
                
                # 평균 신뢰도 계산
                confidences = [result.get('confidence', 0.0) for result in engine_results.values()]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            else:
                final_text = ""
                avg_confidence = 0.0
        else:
            # 가중치 기반 텍스트 선택
            if total_weight > 0:
                # 가장 높은 가중치 점수를 가진 텍스트 선택
                weighted_texts.sort(key=lambda x: x[1], reverse=True)
                final_text = weighted_texts[0][0]
                
                # 가중치 평균 신뢰도 계산
                weighted_confidences = []
                for engine_name, result in engine_results.items():
                    if 'confidence' in result:
                        weighted_confidences.append(
                            (result['confidence'], self.weights.get(engine_name, 0.0))
                        )
                
                if weighted_confidences:
                    total_conf_weight = sum(weight for _, weight in weighted_confidences)
                    if total_conf_weight > 0:
                        avg_confidence = sum(conf * weight for conf, weight in weighted_confidences) / total_conf_weight
                    else:
                        avg_confidence = sum(conf for conf, _ in weighted_confidences) / len(weighted_confidences)
                else:
                    avg_confidence = 0.0
            else:
                final_text = ""
                avg_confidence = 0.0
        
        # 결과 반환
        return {
            'text': final_text,
            'language': final_language,
            'confidence': avg_confidence,
            'engine_results': engine_results  # 디버깅용 세부 결과
        }
    
    def _calculate_image_hash(self, image: Image.Image) -> str:
        """
        이미지 해시 계산 (캐시 키용)
        
        Args:
            image: PIL 이미지
        
        Returns:
            이미지 해시 문자열
        """
        # 이미지를 바이트로 변환
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=95)
        img_bytes = img_byte_arr.getvalue()
        
        # MD5 해시 계산
        return hashlib.md5(img_bytes).hexdigest()
    
    def _check_cache(self, 
                    image: Image.Image, 
                    lang: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        캐시에서 OCR 결과 확인
        
        Args:
            image: PIL 이미지
            lang: 언어 코드
        
        Returns:
            캐시된 OCR 결과 (없으면 None)
        """
        if not self.cache_enabled or not self.cache:
            return None
        
        try:
            # 캐시 키 생성
            image_hash = self._calculate_image_hash(image)
            lang_suffix = lang or 'auto'
            cache_key = f"ocr:{image_hash}:{lang_suffix}"
            
            # 캐시 확인
            cached_data = self.cache.get(cache_key)
            if not cached_data:
                return None
            
            # JSON 파싱
            return json.loads(cached_data)
        
        except Exception as e:
            logger.warning(f"캐시 확인 오류: {e}")
            return None
    
    def _save_to_cache(self, 
                      image: Image.Image, 
                      lang: Optional[str], 
                      result: Dict[str, Any]) -> None:
        """
        OCR 결과를 캐시에 저장
        
        Args:
            image: PIL 이미지
            lang: 언어 코드
            result: OCR 결과
        """
        if not self.cache_enabled or not self.cache:
            return
        
        try:
            # 캐시 키 생성
            image_hash = self._calculate_image_hash(image)
            lang_suffix = lang or 'auto'
            cache_key = f"ocr:{image_hash}:{lang_suffix}"
            
            # 디버깅용 세부 결과는 캐시에서 제외
            cache_result = result.copy()
            if 'engine_results' in cache_result:
                del cache_result['engine_results']
            
            # JSON 직렬화 및 저장
            self.cache.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(cache_result)
            )
            
            logger.debug(f"OCR 결과 캐시 저장: {cache_key}")
        
        except Exception as e:
            logger.warning(f"캐시 저장 오류: {e}")
