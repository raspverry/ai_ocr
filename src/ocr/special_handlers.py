"""
특수 항목 처리 모듈
- 도장, 손글씨, 취소선 등 특수 항목 인식 및 처리
- 고급 이미지 처리 기법 활용
"""

import cv2
import numpy as np
from PIL import Image
import logging
from typing import Dict, Any, List, Tuple, Optional

# 로거 설정
logger = logging.getLogger(__name__)


class SpecialItemDetector:
    """특수 항목(도장, 손글씨, 취소선 등) 감지 및 처리 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        초기화
        
        Args:
            config: 특수 항목 감지 관련 설정
        """
        self.detect_stamps = config.get('detect_stamps', True)
        self.detect_handwriting = config.get('detect_handwriting', True)
        self.detect_strikethrough = config.get('detect_strikethrough', True)
        
        # 도장 감지 설정
        self.stamp_params = {
            'min_radius': 30,
            'max_radius': 150,
            'red_threshold': 0.6,  # 빨간색 도장에 대한 임계값
            'circle_threshold': 0.7  # 원형 도장에 대한 임계값
        }
        
        # 손글씨 감지 설정
        self.handwriting_params = {
            'stroke_width_threshold': 1.5,
            'stroke_variance_threshold': 0.5
        }
        
        # 취소선 감지 설정
        self.strikethrough_params = {
            'line_thickness_min': 2,
            'line_thickness_max': 10,
            'min_line_length': 50
        }
    
    def process_image(self, image: Image.Image) -> Dict[str, Any]:
        """
        이미지에서 특수 항목 처리
        
        Args:
            image: PIL 이미지
        
        Returns:
            특수 항목 정보 딕셔너리
        """
        # PIL 이미지를 OpenCV 형식으로 변환
        cv_image = self._pil_to_cv(image)
        
        # 이미지 전처리
        processed_image = self._preprocess_image(cv_image)
        
        # 결과 저장 딕셔너리
        results = {
            'has_special_items': False,
            'stamps': [],
            'handwriting_regions': [],
            'strikethrough_regions': []
        }
        
        # 도장 감지
        if self.detect_stamps:
            stamps = self._detect_stamps(cv_image, processed_image)
            if stamps:
                results['stamps'] = stamps
                results['has_special_items'] = True
        
        # 손글씨 감지
        if self.detect_handwriting:
            handwriting_regions = self._detect_handwriting(cv_image, processed_image)
            if handwriting_regions:
                results['handwriting_regions'] = handwriting_regions
                results['has_special_items'] = True
        
        # 취소선 감지
        if self.detect_strikethrough:
            strikethrough_regions = self._detect_strikethrough(cv_image, processed_image)
            if strikethrough_regions:
                results['strikethrough_regions'] = strikethrough_regions
                results['has_special_items'] = True
        
        return results
    
    def _pil_to_cv(self, pil_image: Image.Image) -> np.ndarray:
        """PIL 이미지를 OpenCV 형식으로 변환"""
        # RGB to BGR 변환을 위한 복사
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    def _preprocess_image(self, cv_image: np.ndarray) -> Dict[str, np.ndarray]:
        """
        이미지 전처리
        
        Args:
            cv_image: OpenCV 이미지
        
        Returns:
            전처리된 이미지를 포함하는 딕셔너리
        """
        # 그레이스케일 변환
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # 노이즈 제거
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # 이진화
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 컬러 관련 처리를 위한 HSV 변환
        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
        
        # 에지 감지
        edges = cv2.Canny(denoised, 50, 150)
        
        return {
            'gray': gray,
            'denoised': denoised,
            'binary': binary,
            'hsv': hsv,
            'edges': edges
        }
    
    def _detect_stamps(self, 
                       original_image: np.ndarray, 
                       processed_images: Dict[str, np.ndarray]) -> List[Dict[str, Any]]:
        """
        이미지에서 도장 감지
        
        Args:
            original_image: 원본 OpenCV 이미지
            processed_images: 전처리된 이미지 딕셔너리
        
        Returns:
            감지된 도장 목록
        """
        stamps = []
        height, width = original_image.shape[:2]
        
        # 1. 원형 도장 감지 (Hough Circles)
        circles = cv2.HoughCircles(
            processed_images['gray'],
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=100,
            param2=30,
            minRadius=self.stamp_params['min_radius'],
            maxRadius=self.stamp_params['max_radius']
        )
        
        if circles is not None:
            circles = np.round(circles[0, :]).astype(int)
            
            for (x, y, r) in circles:
                # 범위 확인
                if x < 0 or y < 0 or x >= width or y >= height:
                    continue
                
                # 도장 영역 추출
                roi = original_image[max(0, y-r):min(height, y+r), max(0, x-r):min(width, x+r)]
                if roi.size == 0:
                    continue
                
                # 빨간색 비율 확인 (일본식 도장은 주로 빨간색)
                is_red_stamp = self._check_red_ratio(roi)
                
                # 원형 밀도 확인
                circularity = self._check_circularity(
                    processed_images['binary'][max(0, y-r):min(height, y+r), max(0, x-r):min(width, x+r)]
                )
                
                # 도장으로 판단
                if is_red_stamp or circularity > self.stamp_params['circle_threshold']:
                    stamps.append({
                        'type': 'stamp',
                        'position': {'x': int(x), 'y': int(y)},
                        'radius': int(r),
                        'is_red': is_red_stamp,
                        'confidence': float(circularity if not is_red_stamp else max(0.9, circularity))
                    })
        
        # 2. 사각형 도장 감지 (일반적으로 빨간색)
        red_mask = self._extract_red_regions(processed_images['hsv'])
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # 너무 작거나 큰 영역 무시
            min_area = np.pi * (self.stamp_params['min_radius'] ** 2) * 0.8
            max_area = np.pi * (self.stamp_params['max_radius'] ** 2) * 1.5
            
            if min_area <= area <= max_area:
                x, y, w, h = cv2.boundingRect(contour)
                
                # 비율 검사 (도장은 대체로 정사각형에 가까움)
                aspect_ratio = float(w) / h if h > 0 else 0
                if 0.5 <= aspect_ratio <= 2.0:
                    # 이미 감지된 원형 도장과 겹치는지 확인
                    if not self._overlaps_with_existing_stamps(stamps, x, y, max(w, h)/2):
                        stamps.append({
                            'type': 'stamp',
                            'position': {'x': int(x + w/2), 'y': int(y + h/2)},
                            'radius': int(max(w, h)/2),
                            'is_red': True,
                            'confidence': 0.85
                        })
        
        return stamps
    
    def _check_red_ratio(self, image: np.ndarray) -> bool:
        """이미지에서 빨간색 비율 확인"""
        if image.size == 0:
            return False
        
        # HSV로 변환
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 빨간색 영역 마스크 (HSV에서 H값이 약 0-10 또는 160-180)
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = mask1 + mask2
        
        # 빨간색 픽셀 비율 계산
        red_ratio = np.sum(red_mask > 0) / (image.shape[0] * image.shape[1])
        
        return red_ratio > self.stamp_params['red_threshold']
    
    def _extract_red_regions(self, hsv_image: np.ndarray) -> np.ndarray:
        """HSV 이미지에서 빨간색 영역 추출"""
        # 빨간색 영역 마스크 (HSV에서 H값이 약 0-10 또는 160-180)
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv_image, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv_image, lower_red2, upper_red2)
        red_mask = mask1 + mask2
        
        # 노이즈 제거
        kernel = np.ones((5, 5), np.uint8)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
        
        return red_mask
    
    def _check_circularity(self, binary_roi: np.ndarray) -> float:
        """이진화된 ROI의 원형 정도 계산"""
        if binary_roi.size == 0:
            return 0.0
        
        # 윤곽선 찾기
        contours, _ = cv2.findContours(binary_roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return 0.0
        
        # 가장 큰 윤곽선 사용
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        
        if area == 0:
            return 0.0
        
        # 원주 계산
        perimeter = cv2.arcLength(largest_contour, True)
        
        # 완벽한 원의 경우 4π×area/perimeter² = 1
        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
        
        return min(circularity, 1.0)  # 0-1 범위로 제한
    
    def _overlaps_with_existing_stamps(self, 
                                      stamps: List[Dict[str, Any]], 
                                      x: int, 
                                      y: int, 
                                      radius: float) -> bool:
        """새로운 도장이 기존 도장과 겹치는지 확인"""
        for stamp in stamps:
            sx, sy = stamp['position']['x'], stamp['position']['y']
            sr = stamp['radius']
            
            # 두 원 중심 간의 거리
            distance = np.sqrt((x - sx)**2 + (y - sy)**2)
            
            # 거리가 두 반지름의 합보다 작으면 겹침
            if distance < (radius + sr):
                return True
        
        return False
    
    def _detect_handwriting(self, 
                           original_image: np.ndarray, 
                           processed_images: Dict[str, np.ndarray]) -> List[Dict[str, Any]]:
        """
        이미지에서 손글씨 영역 감지
        
        Args:
            original_image: 원본 OpenCV 이미지
            processed_images: 전처리된 이미지 딕셔너리
        
        Returns:
            감지된 손글씨 영역 목록
        """
        handwriting_regions = []
        
        # 필기체 감지를 위한 선폭 변환(SWT) 기반 접근법
        # 기본 이진화 이미지
        binary = processed_images['binary']
        
        # 거리 변환
        dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        
        # 골격화 (가장 중심선만 남김)
        skeleton = self._skeletonize(binary)
        
        # 각 골격 픽셀에서 원본 거리 변환 값 가져오기 = 선폭
        stroke_widths = []
        coords = np.where(skeleton > 0)
        
        if len(coords[0]) == 0:
            return handwriting_regions
        
        for y, x in zip(coords[0], coords[1]):
            stroke_widths.append(dist_transform[y, x])
        
        stroke_widths = np.array(stroke_widths)
        
        # 선폭 통계 계산
        mean_width = np.mean(stroke_widths) if len(stroke_widths) > 0 else 0
        std_width = np.std(stroke_widths) if len(stroke_widths) > 0 else 0
        width_variance = std_width / mean_width if mean_width > 0 else 0
        
        # 손글씨 특성: 선폭 변화가 크고, 평균 선폭이 인쇄된 텍스트보다 일반적으로 더 두껍거나 더 얇음
        is_handwritten = (mean_width > self.handwriting_params['stroke_width_threshold'] or 
                          width_variance > self.handwriting_params['stroke_variance_threshold'])
        
        if not is_handwritten:
            return handwriting_regions
        
        # 텍스트 영역 감지
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(binary, kernel, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # 너무 작은 영역 무시
            if area < 500:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            # 비율 검사 (글자 영역은 일반적으로 너무 길지 않음)
            aspect_ratio = float(w) / h if h > 0 else 0
            if 0.2 <= aspect_ratio <= 5.0:
                # ROI 추출
                roi_binary = binary[y:y+h, x:x+w]
                
                # ROI 내의 골격화 및 선폭 분석
                roi_skeleton = self._skeletonize(roi_binary)
                roi_dist = cv2.distanceTransform(roi_binary, cv2.DIST_L2, 5)
                
                roi_coords = np.where(roi_skeleton > 0)
                if len(roi_coords[0]) == 0:
                    continue
                
                roi_widths = []
                for ry, rx in zip(roi_coords[0], roi_coords[1]):
                    roi_widths.append(roi_dist[ry, rx])
                
                roi_widths = np.array(roi_widths)
                
                # ROI 선폭 통계
                roi_mean_width = np.mean(roi_widths) if len(roi_widths) > 0 else 0
                roi_std_width = np.std(roi_widths) if len(roi_widths) > 0 else 0
                roi_variance = roi_std_width / roi_mean_width if roi_mean_width > 0 else 0
                
                # 손글씨 특성 확인
                if roi_mean_width > self.handwriting_params['stroke_width_threshold'] or roi_variance > self.handwriting_params['stroke_variance_threshold']:
                    # 사각형이 너무 크면 하위 영역으로 나눔
                    if w * h > 50000:
                        # 더 작은 사각형으로 분할 (분할 로직 추가 필요)
                        pass
                    else:
                        handwriting_regions.append({
                            'type': 'handwriting',
                            'position': {'x': int(x), 'y': int(y)},
                            'width': int(w),
                            'height': int(h),
                            'confidence': min(1.0, 0.6 + roi_variance)
                        })
        
        return handwriting_regions
    
    def _skeletonize(self, binary_image: np.ndarray) -> np.ndarray:
        """이진화 이미지의 골격화"""
        skeleton = np.zeros(binary_image.shape, dtype=np.uint8)
        temp_img = binary_image.copy()
        
        kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        
        while True:
            # 열기 연산
            eroded = cv2.erode(temp_img, kernel)
            # 팽창 연산
            dilated = cv2.dilate(eroded, kernel)
            # 차이 계산
            temp = cv2.subtract(temp_img, dilated)
            # 골격에 추가
            skeleton = cv2.bitwise_or(skeleton, temp)
            # 다음 반복을 위해 잠식 이미지 저장
            temp_img = eroded.copy()
            
            # 더 이상 잠식될 픽셀이 없으면 종료
            if cv2.countNonZero(temp_img) == 0:
                break
        
        return skeleton
    
    def _detect_strikethrough(self, 
                             original_image: np.ndarray, 
                             processed_images: Dict[str, np.ndarray]) -> List[Dict[str, Any]]:
        """
        이미지에서 취소선 감지
        
        Args:
            original_image: 원본 OpenCV 이미지
            processed_images: 전처리된 이미지 딕셔너리
        
        Returns:
            감지된 취소선 영역 목록
        """
        strikethrough_regions = []
        
        # 에지 이미지 사용
        edges = processed_images['edges']
        
        # 허프 라인 변환으로 직선 감지
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi/180,
            threshold=50,
            minLineLength=self.strikethrough_params['min_line_length'],
            maxLineGap=10
        )
        
        if lines is None:
            return strikethrough_regions
        
        # 감지된 각 선에 대해
        for line in lines:
            x1, y1, x2, y2 = line[0]
            
            # 선 길이 계산
            line_length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            
            # 선 두께 추정
            line_mask = np.zeros_like(edges)
            cv2.line(line_mask, (x1, y1), (x2, y2), 255, 1)
            
            # 원본 이진화 이미지와 교차하는 영역 계산
            intersection = cv2.bitwise_and(processed_images['binary'], line_mask)
            
            # 추정된 선 두께 계산
            thickness = np.sum(intersection) / (255 * line_length) if line_length > 0 else 0
            
            # 선 기울기 계산
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            
            # 수평에 가까운 선 (취소선은 주로 수평)
            is_horizontal = abs(angle) < 20 or abs(angle) > 160
            
            # 조건에 맞는 선만 취소선으로 간주
            if (is_horizontal and 
                self.strikethrough_params['line_thickness_min'] <= thickness <= self.strikethrough_params['line_thickness_max']):
                
                # 주변 텍스트 존재 여부 확인 (취소선은 텍스트 위에 있어야 함)
                margin = 10
                y_min = max(0, min(y1, y2) - margin)
                y_max = min(original_image.shape[0], max(y1, y2) + margin)
                x_min = max(0, min(x1, x2) - margin)
                x_max = min(original_image.shape[1], max(x1, x2) + margin)
                
                roi_binary = processed_images['binary'][y_min:y_max, x_min:x_max]
                
                # ROI에 충분한 텍스트가 있는지 확인
                text_density = np.sum(roi_binary) / (255 * roi_binary.size) if roi_binary.size > 0 else 0
                
                if text_density > 0.1:  # 10% 이상의 픽셀이 텍스트인 경우
                    strikethrough_regions.append({
                        'type': 'strikethrough',
                        'start': {'x': int(x1), 'y': int(y1)},
                        'end': {'x': int(x2), 'y': int(y2)},
                        'thickness': float(thickness),
                        'confidence': min(1.0, 0.7 + text_density)
                    })
        
        return strikethrough_regions
