"""
이미지 전처리 모듈
- OCR 정확도 향상을 위한 이미지 전처리
- 언어별 최적화된 이미지 처리
- 노이즈 제거 및 이미지 품질 개선
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional, Union, Tuple
from PIL import Image, ImageFilter, ImageEnhance
import cv2

# 로거 설정
logger = logging.getLogger(__name__)


class Preprocessor:
    """OCR 이미지 전처리 클래스"""
    
    def __init__(self):
        """초기화"""
        # 언어별 최적 처리 파라미터
        self.lang_params = {
            'jpn': {
                'binarization_method': 'adaptive',  # 이진화 방법
                'threshold': 180,                   # 고정 임계값
                'block_size': 15,                   # 적응형 임계값 블록 크기
                'c_value': 9,                       # 적응형 임계값 조정값
                'blur_kernel': 3,                   # 블러 커널 크기
                'denoise_h': 10,                    # 노이즈 제거 강도
                'edge_enhancement': 1.5,            # 에지 강화 계수
                'contrast': 1.3,                    # 대비 조정 계수
                'sharpness': 1.4                    # 선명도 조정 계수
            },
            'kor': {
                'binarization_method': 'adaptive',
                'threshold': 180,
                'block_size': 13,
                'c_value': 8,
                'blur_kernel': 3,
                'denoise_h': 10,
                'edge_enhancement': 1.4,
                'contrast': 1.2,
                'sharpness': 1.3
            },
            'eng': {
                'binarization_method': 'adaptive',
                'threshold': 190,
                'block_size': 11,
                'c_value': 7,
                'blur_kernel': 3,
                'denoise_h': 8,
                'edge_enhancement': 1.3,
                'contrast': 1.2,
                'sharpness': 1.2
            },
            'chi_sim': {
                'binarization_method': 'adaptive',
                'threshold': 175,
                'block_size': 15,
                'c_value': 9,
                'blur_kernel': 3,
                'denoise_h': 10,
                'edge_enhancement': 1.4,
                'contrast': 1.3,
                'sharpness': 1.4
            },
            'chi_tra': {
                'binarization_method': 'adaptive',
                'threshold': 175,
                'block_size': 15,
                'c_value': 9,
                'blur_kernel': 3,
                'denoise_h': 10,
                'edge_enhancement': 1.4,
                'contrast': 1.3,
                'sharpness': 1.4
            }
        }
        
        # 문서 유형별 최적 처리 파라미터
        self.doc_type_params = {
            'receipt': {
                'binarization_method': 'adaptive',
                'threshold': 200,
                'block_size': 15,
                'c_value': 5,
                'blur_kernel': 3,
                'denoise_h': 12,
                'edge_enhancement': 1.6,
                'contrast': 1.4,
                'sharpness': 1.5
            },
            'invoice': {
                'binarization_method': 'adaptive',
                'threshold': 190,
                'block_size': 15,
                'c_value': 7,
                'blur_kernel': 3,
                'denoise_h': 10,
                'edge_enhancement': 1.4,
                'contrast': 1.3,
                'sharpness': 1.3
            },
            'form': {
                'binarization_method': 'adaptive',
                'threshold': 180,
                'block_size': 19,
                'c_value': 11,
                'blur_kernel': 5,
                'denoise_h': 15,
                'edge_enhancement': 1.3,
                'contrast': 1.1,
                'sharpness': 1.2
            },
            'handwritten': {
                'binarization_method': 'adaptive',
                'threshold': 170,
                'block_size': 21,
                'c_value': 13,
                'blur_kernel': 5,
                'denoise_h': 15,
                'edge_enhancement': 1.2,
                'contrast': 1.5,
                'sharpness': 1.6
            }
        }
    
    def process_image(self, 
                     image: Union[Image.Image, np.ndarray], 
                     lang: str = "eng", 
                     doc_type: Optional[str] = None) -> Image.Image:
        """
        OCR용 이미지 전처리
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
            lang: 언어 코드 (jpn, kor, eng, chi_sim, chi_tra)
            doc_type: 문서 유형 (receipt, invoice, form, handwritten)
        
        Returns:
            전처리된 PIL 이미지
        """
        try:
            # PIL 이미지로 변환
            if isinstance(image, np.ndarray):
                # OpenCV 배열 (BGR)을 PIL 이미지 (RGB)로 변환
                if len(image.shape) == 3:
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(image)
            else:
                pil_image = image
            
            # 이미지가 너무 작으면 스케일 업
            width, height = pil_image.size
            min_dim = min(width, height)
            if min_dim < 600:
                scale_factor = 600 / min_dim
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
                logger.debug(f"이미지 크기 조정: {width}x{height} -> {new_width}x{new_height}")
            
            # 언어 파라미터 선택
            if lang not in self.lang_params:
                lang = "eng"  # 지원하지 않는 언어면 영어로 대체
            
            params = self.lang_params[lang].copy()
            
            # 문서 유형별 파라미터 오버라이드
            if doc_type in self.doc_type_params:
                params.update(self.doc_type_params[doc_type])
            
            # OpenCV 처리를 위한 변환
            cv_image = np.array(pil_image)
            if len(cv_image.shape) == 3:
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
            
            # 그레이스케일 변환
            if len(cv_image.shape) == 3:
                gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = cv_image
            
            # 각 처리 단계 적용
            processed = self._apply_processing_pipeline(gray, params)
            
            # 결과 이미지를 PIL로 변환
            result_image = Image.fromarray(processed)
            
            return result_image
        
        except Exception as e:
            logger.error(f"이미지 전처리 오류: {e}")
            # 오류 발생 시 원본 이미지 반환
            return pil_image if isinstance(image, Image.Image) else Image.fromarray(image)
    
    def _apply_processing_pipeline(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """
        이미지 처리 파이프라인 적용
        
        Args:
            image: 그레이스케일 NumPy 배열
            params: 처리 파라미터
        
        Returns:
            처리된 NumPy 배열
        """
        # 1. 노이즈 제거 (블러)
        blur_kernel = params.get('blur_kernel', 3)
        if blur_kernel > 0:
            blurred = cv2.GaussianBlur(image, (blur_kernel, blur_kernel), 0)
        else:
            blurred = image
        
        # 2. 노이즈 제거 (비-로컬 평균)
        denoise_h = params.get('denoise_h', 10)
        if denoise_h > 0:
            denoised = cv2.fastNlMeansDenoising(blurred, None, denoise_h, 7, 21)
        else:
            denoised = blurred
        
        # 3. 대비 조정
        alpha = params.get('contrast', 1.0)  # 대비 인자 (1.0보다 크면 대비 증가)
        beta = 0  # 밝기 조정
        contrasted = cv2.convertScaleAbs(denoised, alpha=alpha, beta=beta)
        
        # 4. 이진화
        binarization_method = params.get('binarization_method', 'adaptive')
        
        if binarization_method == 'adaptive':
            # 적응형 이진화
            block_size = params.get('block_size', 11)
            c_value = params.get('c_value', 7)
            
            # 블록 크기는 홀수여야 함
            if block_size % 2 == 0:
                block_size += 1
            
            binary = cv2.adaptiveThreshold(
                contrasted, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, block_size, c_value
            )
        else:
            # 단순 이진화
            threshold = params.get('threshold', 180)
            _, binary = cv2.threshold(contrasted, threshold, 255, cv2.THRESH_BINARY)
        
        # 5. 에지 강화
        edge_enhancement = params.get('edge_enhancement', 1.0)
        if edge_enhancement > 1.0:
            # 에지 감지
            edges = cv2.Canny(contrasted, 50, 150)
            
            # 에지 강화
            edge_enhanced = cv2.addWeighted(binary, 1.0, edges, edge_enhancement - 1.0, 0)
        else:
            edge_enhanced = binary
        
        # 6. 모폴로지 연산 (작은 노이즈 제거)
        kernel = np.ones((2, 2), np.uint8)
        morphed = cv2.morphologyEx(edge_enhanced, cv2.MORPH_OPEN, kernel)
        
        # 7. 선명화
        sharpness = params.get('sharpness', 1.0)
        if sharpness > 1.0:
            # 언샤프 마스킹
            blurred = cv2.GaussianBlur(morphed, (0, 0), 3)
            sharpened = cv2.addWeighted(morphed, sharpness, blurred, -(sharpness - 1), 0)
        else:
            sharpened = morphed
        
        return sharpened
    
    def process_handwritten(self, image: Union[Image.Image, np.ndarray]) -> Image.Image:
        """
        손글씨 이미지용 특화 전처리
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
        
        Returns:
            전처리된 PIL 이미지
        """
        # 손글씨용 특화 파라미터 사용
        return self.process_image(image, doc_type="handwritten")
    
    def process_receipt(self, image: Union[Image.Image, np.ndarray]) -> Image.Image:
        """
        영수증 이미지용 특화 전처리
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
        
        Returns:
            전처리된 PIL 이미지
        """
        # 영수증용 특화 파라미터 사용
        return self.process_image(image, doc_type="receipt")
    
    def enhance_for_stamps(self, image: Union[Image.Image, np.ndarray]) -> Image.Image:
        """
        도장 인식에 최적화된 전처리
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
        
        Returns:
            전처리된 PIL 이미지
        """
        try:
            # PIL 이미지로 변환
            if isinstance(image, np.ndarray):
                # OpenCV 배열 (BGR)을 PIL 이미지 (RGB)로 변환
                if len(image.shape) == 3:
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(image)
            else:
                pil_image = image
            
            # OpenCV 처리를 위한 변환
            cv_image = np.array(pil_image)
            if len(cv_image.shape) == 3:
                # HSV 색 공간으로 변환
                hsv = cv2.cvtColor(cv_image, cv2.COLOR_RGB2HSV)
                
                # 빨간색 영역 마스크 (일본식 도장은 주로 빨간색)
                lower_red1 = np.array([0, 100, 100])
                upper_red1 = np.array([10, 255, 255])
                lower_red2 = np.array([160, 100, 100])
                upper_red2 = np.array([180, 255, 255])
                
                mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
                mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
                red_mask = mask1 + mask2
                
                # 노이즈 제거
                kernel = np.ones((5, 5), np.uint8)
                red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
                
                # 원본 이미지와 마스크 결합
                result = cv2.bitwise_and(cv_image, cv_image, mask=red_mask)
                
                # 결과 이미지를 PIL로 변환
                result_image = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
                
                return result_image
            else:
                # 그레이스케일 이미지는 그대로 반환
                return pil_image
        
        except Exception as e:
            logger.error(f"도장 전처리 오류: {e}")
            return pil_image
    
    def enhance_for_strikethrough(self, image: Union[Image.Image, np.ndarray]) -> Image.Image:
        """
        취소선 인식에 최적화된 전처리
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
        
        Returns:
            전처리된 PIL 이미지
        """
        try:
            # PIL 이미지로 변환
            if isinstance(image, np.ndarray):
                # OpenCV 배열 (BGR)을 PIL 이미지 (RGB)로 변환
                if len(image.shape) == 3:
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(image)
            else:
                pil_image = image
            
            # OpenCV 처리를 위한 변환
            cv_image = np.array(pil_image)
            if len(cv_image.shape) == 3:
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
            
            # 그레이스케일 변환
            if len(cv_image.shape) == 3:
                gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = cv_image
            
            # 가우시안 블러
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # 에지 감지
            edges = cv2.Canny(blurred, 50, 150)
            
            # 선 감지를 위한 모폴로지 연산
            kernel = np.ones((1, 15), np.uint8)  # 수평선 강조
            dilated = cv2.dilate(edges, kernel, iterations=1)
            
            # 결과 이미지를 PIL로 변환
            result_image = Image.fromarray(dilated)
            
            return result_image
        
        except Exception as e:
            logger.error(f"취소선 전처리 오류: {e}")
            return pil_image
    
    def remove_background(self, image: Union[Image.Image, np.ndarray]) -> Image.Image:
        """
        배경 제거 (텍스트 강조)
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
        
        Returns:
            배경이 제거된 PIL 이미지
        """
        try:
            # PIL 이미지로 변환
            if isinstance(image, np.ndarray):
                # OpenCV 배열 (BGR)을 PIL 이미지 (RGB)로 변환
                if len(image.shape) == 3:
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(image)
            else:
                pil_image = image
            
            # OpenCV 처리를 위한 변환
            cv_image = np.array(pil_image)
            if len(cv_image.shape) == 3:
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
            
            # 그레이스케일 변환
            if len(cv_image.shape) == 3:
                gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = cv_image
            
            # 가우시안 블러
            blurred = cv2.GaussianBlur(gray, (7, 7), 0)
            
            # 적응형 이진화
            binary = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 11, 2
            )
            
            # 노이즈 제거
            kernel = np.ones((3, 3), np.uint8)
            opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            
            # 텍스트 영역 확장
            dilated = cv2.dilate(opened, kernel, iterations=1)
            
            # 마스크 적용
            if len(cv_image.shape) == 3:
                # 컬러 이미지의 경우
                result = cv2.bitwise_and(cv_image, cv_image, mask=dilated)
                
                # 배경을 흰색으로 설정
                white_bg = np.ones_like(cv_image, np.uint8) * 255
                bg_mask = cv2.bitwise_not(dilated)
                background = cv2.bitwise_and(white_bg, white_bg, mask=bg_mask)
                
                # 전경과 배경 결합
                result = cv2.add(result, background)
                
                # BGR to RGB
                result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
            else:
                # 그레이스케일 이미지의 경우
                result = cv2.bitwise_and(gray, gray, mask=dilated)
                
                # 배경을 흰색으로 설정
                white_bg = np.ones_like(gray, np.uint8) * 255
                bg_mask = cv2.bitwise_not(dilated)
                background = cv2.bitwise_and(white_bg, white_bg, mask=bg_mask)
                
                # 전경과 배경 결합
                result = cv2.add(result, background)
            
            # 결과 이미지를 PIL로 변환
            result_image = Image.fromarray(result)
            
            return result_image
        
        except Exception as e:
            logger.error(f"배경 제거 오류: {e}")
            return pil_image


class DocumentPreprocessor:
    """문서 이미지 전처리 클래스"""
    
    def __init__(self):
        """초기화"""
        self.preprocessor = Preprocessor()
    
    def process_document(self, 
                        image: Union[Image.Image, np.ndarray], 
                        lang: str = "eng", 
                        doc_type: Optional[str] = None) -> Dict[str, Any]:
        """
        문서 이미지 분석 및 최적 전처리
        
        Args:
            image: PIL 이미지 또는 NumPy 배열
            lang: 언어 코드
            doc_type: 문서 유형
        
        Returns:
            전처리 결과 및 분석 정보
        """
        # PIL 이미지로 변환
        if isinstance(image, np.ndarray):
            # OpenCV 배열 (BGR)을 PIL 이미지 (RGB)로 변환
            if len(image.shape) == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image)
        else:
            pil_image = image
        
        # 결과 저장 딕셔너리
        result = {
            'processed_image': None,
            'language': lang,
            'doc_type': doc_type,
            'has_handwriting': False,
            'has_stamps': False,
            'has_table': False,
            'has_strikethrough': False,
            'regions': []
        }
        
        try:
            # 기본 전처리
            processed_image = self.preprocessor.process_image(pil_image, lang, doc_type)
            result['processed_image'] = processed_image
            
            # OpenCV 처리를 위한 변환
            cv_image = np.array(pil_image)
            if len(cv_image.shape) == 3:
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
            
            # 그레이스케일 변환
            if len(cv_image.shape) == 3:
                gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = cv_image
            
            # 도장 감지 (일본 비즈니스 문서)
            if lang == "jpn":
                has_stamps, stamp_regions = self._detect_stamps(cv_image)
                result['has_stamps'] = has_stamps
                if has_stamps:
                    for region in stamp_regions:
                        result['regions'].append({
                            'type': 'stamp',
                            'bbox': region,
                            'confidence': 0.8  # 임의 신뢰도
                        })
            
            # 손글씨 감지
            has_handwriting, handwriting_regions = self._detect_handwriting(gray)
            result['has_handwriting'] = has_handwriting
            if has_handwriting:
                for region in handwriting_regions:
                    result['regions'].append({
                        'type': 'handwriting',
                        'bbox': region,
                        'confidence': 0.7  # 임의 신뢰도
                    })
            
            # 표 감지
            has_table, table_regions = self._detect_tables(gray)
            result['has_table'] = has_table
            if has_table:
                for region in table_regions:
                    result['regions'].append({
                        'type': 'table',
                        'bbox': region,
                        'confidence': 0.9  # 임의 신뢰도
                    })
            
            # 취소선 감지
            has_strikethrough, strikethrough_regions = self._detect_strikethrough(gray)
            result['has_strikethrough'] = has_strikethrough
            if has_strikethrough:
                for region in strikethrough_regions:
                    result['regions'].append({
                        'type': 'strikethrough',
                        'bbox': region,
                        'confidence': 0.6  # 임의 신뢰도
                    })
            
            # 문서 유형 추론 (지정되지 않은 경우)
            if doc_type is None:
                result['doc_type'] = self._infer_document_type(
                    cv_image, 
                    has_handwriting, 
                    has_table, 
                    has_stamps
                )
        
        except Exception as e:
            logger.error(f"문서 전처리 오류: {e}")
            result['processed_image'] = pil_image  # 오류 시 원본 이미지 반환
            result['error'] = str(e)
        
        return result
    
    def _detect_stamps(self, image: np.ndarray) -> Tuple[bool, List[List[int]]]:
        """
        도장 감지
        
        Args:
            image: OpenCV 이미지 (BGR)
        
        Returns:
            도장 포함 여부, 도장 영역 목록 [[x1, y1, x2, y2], ...]
        """
        stamp_regions = []
        
        # HSV 색 공간으로 변환
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 빨간색 영역 마스크 (일본식 도장은 주로 빨간색)
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = mask1 + mask2
        
        # 노이즈 제거
        kernel = np.ones((5, 5), np.uint8)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
        
        # 윤곽선 검출
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 도장 후보 필터링
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 500:  # 너무 작은 영역 무시
                continue
            
            # 경계 상자
            x, y, w, h = cv2.boundingRect(contour)
            
            # 종횡비 검사 (도장은 대체로 원형 또는 정사각형에 가까움)
            aspect_ratio = float(w) / h if h > 0 else 0
            if 0.5 <= aspect_ratio <= 2.0:
                stamp_regions.append([x, y, x + w, y + h])
        
        return len(stamp_regions) > 0, stamp_regions
    
    def _detect_handwriting(self, image: np.ndarray) -> Tuple[bool, List[List[int]]]:
        """
        손글씨 영역 감지
        
        Args:
            image: 그레이스케일 OpenCV 이미지
        
        Returns:
            손글씨 포함 여부, 손글씨 영역 목록 [[x1, y1, x2, y2], ...]
        """
        handwriting_regions = []
        
        # 이진화
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 노이즈 제거
        kernel = np.ones((3, 3), np.uint8)
        opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # 획 두께 변환 (Stroke Width Transform 간소화 버전)
        dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
        
        # 텍스트 영역 확장
        dilated = cv2.dilate(opening, kernel, iterations=2)
        
        # 윤곽선 검출
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 손글씨 후보 필터링
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 200:  # 너무 작은 영역 무시
                continue
            
            # 경계 상자
            x, y, w, h = cv2.boundingRect(contour)
            
            # ROI 추출
            roi = dist_transform[y:y+h, x:x+w]
            
            if roi.size == 0:
                continue
            
            # 획 두께 통계
            mean_width = np.mean(roi[roi > 0]) if np.any(roi > 0) else 0
            std_width = np.std(roi[roi > 0]) if np.any(roi > 0) else 0
            
            # 손글씨 특성: 획 두께 변화가 크고, 평균 두께가 인쇄된 텍스트와 다름
            if std_width / (mean_width + 1e-6) > 0.5 or mean_width > 3.0:
                handwriting_regions.append([x, y, x + w, y + h])
        
        return len(handwriting_regions) > 0, handwriting_regions
    
    def _detect_tables(self, image: np.ndarray) -> Tuple[bool, List[List[int]]]:
        """
        표 영역 감지
        
        Args:
            image: 그레이스케일 OpenCV 이미지
        
        Returns:
            표 포함 여부, 표 영역 목록 [[x1, y1, x2, y2], ...]
        """
        table_regions = []
        
        # 에지 감지
        edges = cv2.Canny(image, 50, 150)
        
        # 선 검출을 위한 모폴로지 연산
        kernel_h = np.ones((1, 30), np.uint8)  # 수평선 강조
        kernel_v = np.ones((30, 1), np.uint8)  # 수직선 강조
        
        dilated_h = cv2.dilate(edges, kernel_h, iterations=1)
        dilated_v = cv2.dilate(edges, kernel_v, iterations=1)
        
        # 수평선 및 수직선 결합
        table_mask = cv2.bitwise_or(dilated_h, dilated_v)
        
        # 표 영역 확장
        kernel = np.ones((5, 5), np.uint8)
        table_mask = cv2.dilate(table_mask, kernel, iterations=2)
        
        # 윤곽선 검출
        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 표 후보 필터링
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 5000:  # 너무 작은 영역 무시
                continue
            
            # 경계 상자
            x, y, w, h = cv2.boundingRect(contour)
            
            # 종횡비 검사 (표는 일반적으로 너비가 높이보다 크거나 비슷함)
            aspect_ratio = float(w) / h if h > 0 else 0
            if 0.5 <= aspect_ratio <= 5.0:
                # 선의 밀도 계산
                roi = table_mask[y:y+h, x:x+w]
                line_density = np.sum(roi > 0) / (w * h)
                
                # 일정 선 밀도 이상인 경우 표로 간주
                if line_density > 0.05:
                    table_regions.append([x, y, x + w, y + h])
        
        return len(table_regions) > 0, table_regions
    
    def _detect_strikethrough(self, image: np.ndarray) -> Tuple[bool, List[List[int]]]:
        """
        취소선 감지
        
        Args:
            image: 그레이스케일 OpenCV 이미지
        
        Returns:
            취소선 포함 여부, 취소선 영역 목록 [[x1, y1, x2, y2], ...]
        """
        strikethrough_regions = []
        
        # 에지 감지
        edges = cv2.Canny(image, 50, 150)
        
        # 허프 라인 변환
        lines = cv2.HoughLinesP(
            edges, 1, np.pi/180, threshold=50, 
            minLineLength=50, maxLineGap=10
        )
        
        if lines is None:
            return False, []
        
        # 이진화
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 각 선에 대해
        for line in lines:
            x1, y1, x2, y2 = line[0]
            
            # 선 길이 계산
            line_length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            
            # 선 기울기 계산
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            
            # 수평에 가까운 선 (취소선은 주로 수평)
            is_horizontal = abs(angle) < 20 or abs(angle) > 160
            
            if is_horizontal and line_length > 50:
                # 선 주변 영역 확인
                margin = 10
                y_min = max(0, min(y1, y2) - margin)
                y_max = min(image.shape[0], max(y1, y2) + margin)
                x_min = max(0, min(x1, x2) - margin)
                x_max = min(image.shape[1], max(x1, x2) + margin)
                
                # 선 주변 영역에 텍스트가 있는지 확인
                roi = binary[y_min:y_max, x_min:x_max]
                text_density = np.sum(roi > 0) / (roi.size + 1e-6)
                
                # 텍스트 영역 위에 있는 선만 취소선으로 간주
                if text_density > 0.1:
                    strikethrough_regions.append([x_min, y_min, x_max, y_max])
        
        return len(strikethrough_regions) > 0, strikethrough_regions
    
    def _infer_document_type(self, 
                            image: np.ndarray, 
                            has_handwriting: bool, 
                            has_table: bool, 
                            has_stamps: bool) -> str:
        """
        문서 유형 추론
        
        Args:
            image: OpenCV 이미지 (BGR)
            has_handwriting: 손글씨 포함 여부
            has_table: 표 포함 여부
            has_stamps: 도장 포함 여부
        
        Returns:
            추론된 문서 유형
        """
        # 이미지 크기
        height, width = image.shape[:2]
        
        # 연관 점수
        scores = {
            'receipt': 0,
            'invoice': 0,
            'form': 0,
            'handwritten': 0
        }
        
        # 종횡비 기반 점수
        aspect_ratio = width / height
        if 0.2 <= aspect_ratio <= 0.5:  # 좁고 긴 형태
            scores['receipt'] += 2
        elif 0.5 < aspect_ratio <= 0.9:  # 세로가 더 긴 형태
            scores['form'] += 1
        elif 0.9 < aspect_ratio <= 1.1:  # 정사각형에 가까운 형태
            scores['form'] += 1
        elif 1.1 < aspect_ratio <= 1.5:  # 약간 가로가 긴 형태
            scores['invoice'] += 1
        else:  # 매우 가로가 긴 형태
            scores['invoice'] += 2
        
        # 특성 기반 점수
        if has_handwriting:
            scores['handwritten'] += 3
            scores['form'] += 1
        
        if has_table:
            scores['invoice'] += 2
            scores['form'] += 1
        
        if has_stamps:
            scores['invoice'] += 1
            scores['form'] += 1
        
        # 최고 점수 문서 유형 반환
        return max(scores.items(), key=lambda x: x[1])[0]
