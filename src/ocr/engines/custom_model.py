"""
딥러닝 기반 커스텀 OCR 엔진
- TrOCR 모델 기반 OCR 엔진
- 언어별 특화 모델 지원
"""

import os
import logging
from typing import Dict, Any, Optional, Union, List
import numpy as np
from PIL import Image
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

from src.core.config import config
from src.ocr.engines.base import BaseOCREngine

# 로거 설정
logger = logging.getLogger(__name__)


class CustomModelEngine(BaseOCREngine):
    """TrOCR 기반 커스텀 OCR 엔진"""
    
    def __init__(self):
        """초기화"""
        super().__init__()
        self.name = "custom_trocr"
        self.models = {}
        self.processors = {}
        
        # CUDA 사용 가능 여부 확인
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"TrOCR 모델 실행 장치: {self.device}")
        
        # 모델 초기화
        self._initialize_models()
    
    def _initialize_models(self):
        """언어별 TrOCR 모델 초기화"""
        model_dir = config.get('ocr.model_dir', './models')
        
        # 지원 언어 목록
        languages = config.get('ocr.supported_languages', {
            'jpn': '일본어',
            'eng': '영어',
            'kor': '한국어',
            'chi_sim': '중국어 간체',
            'chi_tra': '중국어 번체'
        }).keys()
        
        # 언어별 모델 로드
        for lang in languages:
            try:
                if lang == 'jpn':
                    # 일본어 모델
                    processor_path = os.path.join(model_dir, 'trocr', 'japanese')
                    model_path = processor_path
                    
                    # 모델 파일이 없으면 Hugging Face에서 직접 로드
                    if not os.path.exists(model_path):
                        logger.info(f"로컬에 일본어 TrOCR 모델이 없어 Hugging Face에서 다운로드합니다.")
                        processor_path = "microsoft/trocr-base-japanese"
                        model_path = "microsoft/trocr-base-japanese"
                    
                    self.processors[lang] = TrOCRProcessor.from_pretrained(processor_path)
                    self.models[lang] = VisionEncoderDecoderModel.from_pretrained(model_path)
                    self.models[lang].to(self.device)
                    logger.info(f"일본어 TrOCR 모델 로드 완료")
                
                elif lang == 'eng':
                    # 영어 모델
                    processor_path = os.path.join(model_dir, 'trocr', 'printed')
                    model_path = processor_path
                    
                    # 모델 파일이 없으면 Hugging Face에서 직접 로드
                    if not os.path.exists(model_path):
                        logger.info(f"로컬에 영어 TrOCR 모델이 없어 Hugging Face에서 다운로드합니다.")
                        processor_path = "microsoft/trocr-base-printed"
                        model_path = "microsoft/trocr-base-printed"
                    
                    self.processors[lang] = TrOCRProcessor.from_pretrained(processor_path)
                    self.models[lang] = VisionEncoderDecoderModel.from_pretrained(model_path)
                    self.models[lang].to(self.device)
                    logger.info(f"영어 TrOCR 모델 로드 완료")
                
                # 다른 언어에 대한 모델 로드 로직 추가 (아직 공식 모델이 없는 경우 영어 모델 활용)
                elif lang in ['kor', 'chi_sim', 'chi_tra']:
                    # 해당 언어 전용 모델이 있는지 확인
                    lang_path = os.path.join(model_dir, 'trocr', lang)
                    
                    if os.path.exists(lang_path):
                        # 언어별 특화 모델이 있으면 로드
                        self.processors[lang] = TrOCRProcessor.from_pretrained(lang_path)
                        self.models[lang] = VisionEncoderDecoderModel.from_pretrained(lang_path)
                        self.models[lang].to(self.device)
                        logger.info(f"{lang} TrOCR 모델 로드 완료")
                    else:
                        # 없으면 영어 모델 대체 사용
                        logger.warning(f"{lang}용 TrOCR 모델이 없어 영어 모델로 대체합니다.")
                        if 'eng' not in self.processors:
                            # 영어 모델도 없으면 로드
                            processor_path = "microsoft/trocr-base-printed"
                            model_path = "microsoft/trocr-base-printed"
                            
                            self.processors['eng'] = TrOCRProcessor.from_pretrained(processor_path)
                            self.models['eng'] = VisionEncoderDecoderModel.from_pretrained(model_path)
                            self.models['eng'].to(self.device)
                        
                        # 영어 모델 복사
                        self.processors[lang] = self.processors['eng']
                        self.models[lang] = self.models['eng']
            
            except Exception as e:
                logger.error(f"TrOCR {lang} 모델 로드 오류: {e}")
    
    async def recognize(self, image: Union[Image.Image, np.ndarray], lang: Optional[str] = None) -> Dict[str, Any]:
        """
        이미지에서 텍스트 인식
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
            lang: 언어 코드 (None이면 자동 감지)
        
        Returns:
            인식 결과 (텍스트, 언어, 신뢰도 등)
        """
        try:
            # 이미지 전처리
            pil_image = self.preprocess_image(image)
            pil_image = self.ensure_rgb_image(pil_image)
            
            # 언어 코드 정규화
            norm_lang = self.normalize_language_code(lang)
            
            # 언어 모델이 없으면 기본 언어 사용
            if norm_lang not in self.models:
                default_lang = config.get('ocr.default_language', 'jpn')
                logger.warning(f"언어 '{norm_lang}'에 대한 모델이 없습니다. 기본 언어({default_lang})로 대체합니다.")
                norm_lang = default_lang
                
                # 기본 언어 모델도 없으면 오류
                if norm_lang not in self.models:
                    return self.format_result("", norm_lang, 0.0, {"error": "지원되지 않는 언어입니다."})
            
            # 프로세서 및 모델 선택
            processor = self.processors[norm_lang]
            model = self.models[norm_lang]
            
            # 이미지 전처리
            pixel_values = processor(images=pil_image, return_tensors="pt").pixel_values.to(self.device)
            
            # 추론
            with torch.no_grad():
                generated_ids = model.generate(
                    pixel_values,
                    max_length=256,
                    num_beams=5,
                    early_stopping=True,
                    return_dict_in_generate=True,
                    output_scores=True
                )
            
            # 텍스트 디코딩
            generated_text = processor.batch_decode(generated_ids.sequences, skip_special_tokens=True)[0]
            
            # 신뢰도 계산
            confidence = 0.0
            if hasattr(generated_ids, 'sequences_scores'):
                # 시퀀스 점수를 신뢰도로 변환 (log softmax에서 확률로)
                confidence = torch.exp(generated_ids.sequences_scores[0]).item()
            else:
                # 점수가 없으면 중간 정도의 신뢰도 할당
                confidence = 0.7
            
            return self.format_result(generated_text, norm_lang, confidence)
        
        except Exception as e:
            logger.error(f"TrOCR 인식 오류: {e}")
            return self.format_result("", lang or config.get('ocr.default_language', 'jpn'), 0.0, {"error": str(e)})
    
    async def recognize_batch(self, 
                             images: List[Union[Image.Image, np.ndarray]], 
                             lang: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        이미지 배치에서 텍스트 인식
        
        Args:
            images: PIL 이미지 또는 NumPy 배열 목록
            lang: 언어 코드 (None이면 자동 감지)
        
        Returns:
            인식 결과 목록
        """
        results = []
        
        # 언어 코드 정규화
        norm_lang = self.normalize_language_code(lang)
        
        # 언어 모델이 없으면 기본 언어 사용
        if norm_lang not in self.models:
            default_lang = config.get('ocr.default_language', 'jpn')
            norm_lang = default_lang
        
        batch_size = config.get('document.batch_size', 8)
        
        # 배치 처리
        for i in range(0, len(images), batch_size):
            batch = images[i:i+batch_size]
            
            try:
                # 이미지 전처리
                pil_images = [self.preprocess_image(img) for img in batch]
                pil_images = [self.ensure_rgb_image(img) for img in pil_images]
                
                # 프로세서 및 모델 선택
                processor = self.processors[norm_lang]
                model = self.models[norm_lang]
                
                # 이미지 전처리 (배치)
                inputs = processor(images=pil_images, return_tensors="pt", padding=True)
                pixel_values = inputs.pixel_values.to(self.device)
                
                # 추론
                with torch.no_grad():
                    generated_ids = model.generate(
                        pixel_values,
                        max_length=256,
                        num_beams=5,
                        early_stopping=True,
                        return_dict_in_generate=True,
                        output_scores=True
                    )
                
                # 텍스트 디코딩
                generated_texts = processor.batch_decode(generated_ids.sequences, skip_special_tokens=True)
                
                # 신뢰도 계산
                confidences = []
                if hasattr(generated_ids, 'sequences_scores'):
                    confidences = [torch.exp(score).item() for score in generated_ids.sequences_scores]
                else:
                    confidences = [0.7] * len(generated_texts)  # 기본 신뢰도
                
                # 결과 추가
                for text, conf in zip(generated_texts, confidences):
                    results.append(self.format_result(text, norm_lang, conf))
            
            except Exception as e:
                logger.error(f"TrOCR 배치 인식 오류: {e}")
                # 오류 시 빈 결과 추가
                for _ in range(len(batch)):
                    results.append(self.format_result("", norm_lang, 0.0, {"error": str(e)}))
        
        return results
