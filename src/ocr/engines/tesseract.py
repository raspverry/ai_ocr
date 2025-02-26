"""
테서랙트 OCR 엔진
- Tesseract OCR을 사용한 텍스트 인식
- 다국어 지원 및 이미지 전처리 최적화
"""

import os
import logging
import tempfile
from typing import Dict, Any, Optional, Union, List
import numpy as np
from PIL import Image
import cv2
import pytesseract
from pytesseract import Output

from src.core.config import config
from src.ocr.engines.base import BaseOCREngine

# 로거 설정
logger = logging.getLogger(__name__)


class TesseractEngine(BaseOCREngine):
    """테서랙트 OCR 엔진"""
    
    def __init__(self):
        """초기화"""
        super().__init__()
        self.name = "tesseract"
        
        # 테서랙트 설정
        self.tesseract_path = config.get('ocr.tesseract_path', '/usr/bin/tesseract')
        self.tessdata_dir = os.path.join(config.get('ocr.model_dir', './models'), 'tessdata')
        
        # 테서랙트 경로 설정
        if self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
        
        # 언어별 최적 PSM(Page Segmentation Mode) 설정
        self.lang_psm = {
            'jpn': 6,  # 일본어: 단일 텍스트 블록
            'kor': 6,  # 한국어: 단일 텍스트 블록
            'eng': 3,  # 영어: 자동 페이지 세그멘테이션
            'chi_sim': 6,  # 중국어 간체: 단일 텍스트 블록
            'chi_tra': 6   # 중국어 번체: 단일 텍스트 블록
        }
        
        # 테서랙트 지원 언어 확인
        self._check_tesseract_languages()
    
    def _check_tesseract_languages(self):
        """테서랙트 지원 언어 확인"""
        try:
            # 테서랙트 설치 확인
            pytesseract.get_tesseract_version()
            
            # 지원 언어 목록 가져오기
            supported_langs = pytesseract.get_languages()
            
            # 환경 변수가 설정되어 있으면 언어 확인 스킵
            if os.environ.get('TESSDATA_PREFIX') or os.environ.get('TESSERACT_PREFIX'):
                return
            
            # 테서랙트 언어 데이터 확인
            languages = config.get('ocr.supported_languages', {
                'jpn': '일본어',
                'eng': '영어',
                'kor': '한국어',
                'chi_sim': '중국어 간체',
                'chi_tra': '중국어 번체'
            }).keys()
            
            missing_langs = [lang for lang in languages if lang not in supported_langs]
            
            if missing_langs:
                logger.warning(f"테서랙트에서 지원하지 않는 언어: {', '.join(missing_langs)}")
                logger.warning(f"테서랙트 지원 언어: {', '.join(supported_langs)}")
                
                # 사용자 정의 tessdata 디렉토리 확인
                if os.path.exists(self.tessdata_dir):
                    logger.info(f"사용자 정의 tessdata 디렉토리 사용: {self.tessdata_dir}")
                    logger.info(f"TESSDATA_PREFIX 환경 변수를 설정하거나 언어 데이터를 설치하세요.")
        
        except Exception as e:
            logger.error(f"테서랙트 언어 확인 오류: {e}")
    
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
            preprocessed_image = self._preprocess_for_tesseract(image)
            
            # 언어 코드 정규화
            norm_lang = self.normalize_language_code(lang)
            
            # 언어별 최적 PSM 설정
            psm = self.lang_psm.get(norm_lang, 3)
            
            # 사용자 정의 tessdata 디렉토리가 있으면 설정
            config_args = []
            if os.path.exists(self.tessdata_dir):
                config_args.append(f'--tessdata-dir {self.tessdata_dir}')
            
            # 테서랙트 OCR 설정
            custom_config = f'--oem 1 --psm {psm} {" ".join(config_args)}'
            
            # 상세 OCR 데이터 추출
            ocr_data = pytesseract.image_to_data(
                preprocessed_image,
                lang=norm_lang,
                output_type=Output.DICT,
                config=custom_config
            )
            
            # 텍스트 및 신뢰도 추출
            text_parts = []
            conf_values = []
            
            for i in range(len(ocr_data['text'])):
                # 빈 텍스트 및 낮은 신뢰도 항목 필터링
                if ocr_data['text'][i].strip() and int(ocr_data['conf'][i]) > 0:
                    text_parts.append(ocr_data['text'][i])
                    conf_values.append(float(ocr_data['conf'][i]))
            
            # 결과 텍스트 생성
            if text_parts:
                full_text = ' '.join(text_parts)
                avg_confidence = sum(conf_values) / len(conf_values) / 100.0  # 0-1 범위로 정규화
            else:
                full_text = ""
                avg_confidence = 0.0
            
            # 테서랙트 추가 데이터 수집
            extra_data = {
                'words': [],
                'blocks': []
            }
            
            # 단어 및 블록 정보 추출
            for i in range(len(ocr_data['text'])):
                if ocr_data['text'][i].strip() and int(ocr_data['conf'][i]) > 0:
                    word = {
                        'text': ocr_data['text'][i],
                        'confidence': float(ocr_data['conf'][i]) / 100.0,
                        'bbox': [
                            ocr_data['left'][i],
                            ocr_data['top'][i],
                            ocr_data['left'][i] + ocr_data['width'][i],
                            ocr_data['top'][i] + ocr_data['height'][i]
                        ],
                        'block_num': ocr_data['block_num'][i],
                        'line_num': ocr_data['line_num'][i]
                    }
                    extra_data['words'].append(word)
            
            # 블록 번호별로 단어 그룹화
            blocks = {}
            for word in extra_data['words']:
                block_key = (word['block_num'], word['line_num'])
                if block_key not in blocks:
                    blocks[block_key] = {
                        'text': word['text'],
                        'confidence': word['confidence'],
                        'bbox': word['bbox'].copy(),
                        'words': [word]
                    }
                else:
                    blocks[block_key]['text'] += ' ' + word['text']
                    blocks[block_key]['confidence'] = (blocks[block_key]['confidence'] + word['confidence']) / 2
                    # 바운딩 박스 업데이트
                    blocks[block_key]['bbox'][0] = min(blocks[block_key]['bbox'][0], word['bbox'][0])
                    blocks[block_key]['bbox'][1] = min(blocks[block_key]['bbox'][1], word['bbox'][1])
                    blocks[block_key]['bbox'][2] = max(blocks[block_key]['bbox'][2], word['bbox'][2])
                    blocks[block_key]['bbox'][3] = max(blocks[block_key]['bbox'][3], word['bbox'][3])
                    blocks[block_key]['words'].append(word)
            
            extra_data['blocks'] = list(blocks.values())
            
            return self.format_result(full_text, norm_lang, avg_confidence, extra_data)
        
        except Exception as e:
            logger.error(f"테서랙트 인식 오류: {e}")
            return self.format_result("", lang or config.get('ocr.default_language', 'jpn'), 0.0, {"error": str(e)})
    
    def _preprocess_for_tesseract(self, image: Union[Image.Image, np.ndarray]) -> Image.Image:
        """
        테서랙트에 최적화된 이미지 전처리
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
            
        Returns:
            전처리된 PIL 이미지
        """
        # PIL 이미지로 변환
        pil_image = self.preprocess_image(image)
        
        # OpenCV 형식으로 변환
        img_array = np.array(pil_image)
        if len(img_array.shape) == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # 그레이스케일 변환
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY) if len(img_array.shape) == 3 else img_array
        
        # 이미지 전처리 파이프라인
        
        # 1. 노이즈 제거
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # 2. 이미지 해상도 향상
        # 2-a. 적응형 히스토그램 평활화
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        equalized = clahe.apply(denoised)
        
        # 2-b. 대비 조정
        alpha = 1.5  # 대비 인자 (1.0보다 크면 대비 증가)
        beta = 10    # 밝기 조정 (양수는 밝게, 음수는 어둡게)
        adjusted = cv2.convertScaleAbs(equalized, alpha=alpha, beta=beta)
        
        # 3. 이진화
        # 3-a. 적응형 이진화 (블록 단위로 임계값 계산)
        binary = cv2.adaptiveThreshold(
            adjusted, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # 3-b. 모폴로지 연산 (작은 노이즈 제거, 글자 연결)
        kernel = np.ones((1, 1), np.uint8)  # 커널 크기 조정 가능
        morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # 4. 선명화
        sharpen_kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened = cv2.filter2D(morph, -1, sharpen_kernel)
        
        # 결과 이미지를 PIL 형식으로 변환
        result_image = Image.fromarray(sharpened)
        
        return result_image
    
    async def recognize_multiple_scales(self, 
                                       image: Union[Image.Image, np.ndarray], 
                                       lang: Optional[str] = None) -> Dict[str, Any]:
        """
        여러 스케일에서 이미지 인식 (작은 텍스트 인식에 유용)
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
            lang: 언어 코드
            
        Returns:
            가장 좋은 인식 결과
        """
        # 이미지 전처리
        pil_image = self.preprocess_image(image)
        
        # 이미지 크기
        width, height = pil_image.size
        
        # 스케일 팩터
        scale_factors = [1.0, 1.5, 2.0]
        
        best_result = None
        best_confidence = -1
        
        # 각 스케일에서 인식
        for scale in scale_factors:
            # 이미지 크기 조정
            scaled_width = int(width * scale)
            scaled_height = int(height * scale)
            scaled_image = pil_image.resize((scaled_width, scaled_height), Image.LANCZOS)
            
            # OCR 인식
            result = await self.recognize(scaled_image, lang)
            
            # 더 좋은 결과인지 확인
            if result['confidence'] > best_confidence and result['text'].strip():
                best_result = result
                best_confidence = result['confidence']
        
        return best_result or await self.recognize(pil_image, lang)
