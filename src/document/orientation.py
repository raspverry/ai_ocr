"""
페이지 방향 감지 및 보정 모듈
- 텍스트 기반 방향 감지
- 문서 경계 감지
- 회전 보정
"""

import math
import logging
import numpy as np
from typing import Union, List, Dict, Any, Tuple
from PIL import Image
import cv2

# 로거 설정
logger = logging.getLogger(__name__)


def detect_orientation(image: Union[Image.Image, np.ndarray]) -> int:
    """
    이미지 방향 감지 (0, 90, 180, 270도)
    
    Args:
        image: PIL 이미지 또는 NumPy 배열
    
    Returns:
        감지된 회전 각도 (0, 90, 180, 270)
    """
    try:
        # PIL 이미지를 NumPy 배열로 변환
        if isinstance(image, Image.Image):
            cv_image = np.array(image)
            
            # RGB to BGR 변환 (OpenCV는 BGR 사용)
            if len(cv_image.shape) == 3:
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
        else:
            cv_image = image
        
        # 그레이스케일 변환
        if len(cv_image.shape) == 3:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = cv_image
        
        # 노이즈 제거
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 적응형 이진화
        thresh = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # 텍스트 영역 감지를 위한 확장
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
        dilate = cv2.dilate(thresh, kernel, iterations=1)
        
        # 윤곽선 감지
        contours, _ = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 텍스트 라인 선별 (작은 영역 제외)
        min_area = gray.shape[0] * gray.shape[1] * 0.001  # 이미지 크기의 0.1%
        text_lines = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
        
        if not text_lines:
            logger.debug("텍스트 라인을 찾을 수 없습니다.")
            return 0  # 기본 방향
        
        # 텍스트 라인 각도 분석
        angles = []
        for cnt in text_lines:
            rect = cv2.minAreaRect(cnt)
            angle = rect[2]
            
            # OpenCV는 -90 ~ 0도 사이의 각도 반환
            if angle < -45:
                angle = 90 + angle
            
            angles.append(angle)
        
        # 각도 히스토그램 분석 (5도 간격으로 양자화)
        hist = {}
        for angle in angles:
            bucket = round(angle / 5) * 5
            hist[bucket] = hist.get(bucket, 0) + 1
        
        # 가장 빈번한 각도 버킷 찾기
        if not hist:
            return 0
        
        most_common_bucket = max(hist.items(), key=lambda x: x[1])[0]
        
        # 문서 방향 결정
        if -10 <= most_common_bucket <= 10:
            return 0  # 정상 방향
        elif 40 <= most_common_bucket <= 50:
            return 90  # 90도 시계 방향 회전
        elif -50 <= most_common_bucket <= -40:
            return 270  # 270도 시계 방향 회전 (90도 반시계)
        elif (most_common_bucket >= 80) or (most_common_bucket <= -80):
            return 180  # 180도 회전
        
        # 특별한 패턴을 찾지 못하면 기본 방향
        return 0
    
    except Exception as e:
        logger.error(f"방향 감지 오류: {e}")
        return 0  # 오류 시 기본 방향


def detect_skew_angle(image: Union[Image.Image, np.ndarray]) -> float:
    """
    이미지의 미세한 기울기 각도 감지
    
    Args:
        image: PIL 이미지 또는 NumPy 배열
    
    Returns:
        감지된 기울기 각도 (도 단위, -45 ~ 45)
    """
    try:
        # PIL 이미지를 NumPy 배열로 변환
        if isinstance(image, Image.Image):
            cv_image = np.array(image)
            
            # RGB to BGR 변환 (OpenCV는 BGR 사용)
            if len(cv_image.shape) == 3:
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
        else:
            cv_image = image
        
        # 그레이스케일 변환
        if len(cv_image.shape) == 3:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = cv_image
        
        # 노이즈 제거
        blur = cv2.GaussianBlur(gray, (9, 9), 0)
        
        # Canny 에지 감지
        edges = cv2.Canny(blur, 50, 150, apertureSize=3)
        
        # 확률적 허프 라인 변환
        lines = cv2.HoughLinesP(
            edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10
        )
        
        if lines is None or len(lines) == 0:
            return 0.0
        
        # 수평선 각도 계산
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            
            # 수직에 가까운 선 제외 (수평선만 고려)
            if x2 - x1 == 0:
                continue
            
            angle = math.atan2(y2 - y1, x2 - x1) * 180.0 / np.pi
            
            # -45 ~ 45 범위로 정규화
            if angle < -45:
                angle += 90
            elif angle > 45:
                angle -= 90
            
            angles.append(angle)
        
        if not angles:
            return 0.0
        
        # 각도 히스토그램 분석
        hist = {}
        for angle in angles:
            # 0.5도 단위로 양자화
            bucket = round(angle * 2) / 2
            hist[bucket] = hist.get(bucket, 0) + 1
        
        # 가장 빈번한 각도 반환
        if not hist:
            return 0.0
        
        most_common_angle = max(hist.items(), key=lambda x: x[1])[0]
        return most_common_angle
    
    except Exception as e:
        logger.error(f"기울기 감지 오류: {e}")
        return 0.0


def correct_orientation(image: Image.Image, angle: int) -> Image.Image:
    """
    이미지 방향 보정
    
    Args:
        image: PIL 이미지
        angle: 회전 각도 (0, 90, 180, 270)
    
    Returns:
        보정된 PIL 이미지
    """
    if angle == 0:
        return image
    
    # PIL의 회전 함수 사용
    if angle == 90:
        return image.transpose(Image.ROTATE_270)  # 반시계 90도 = 시계 270도
    elif angle == 180:
        return image.transpose(Image.ROTATE_180)
    elif angle == 270:
        return image.transpose(Image.ROTATE_90)  # 반시계 270도 = 시계 90도
    
    # 다른 각도는 그대로 반환
    return image


def correct_skew(image: Image.Image, angle: float) -> Image.Image:
    """
    이미지 기울기 보정
    
    Args:
        image: PIL 이미지
        angle: 기울기 각도 (도 단위)
    
    Returns:
        보정된 PIL 이미지
    """
    # 각도 범위 확인
    if abs(angle) < 0.1:  # 0.1도 이하는 무시
        return image
    
    # NumPy 배열로 변환
    cv_image = np.array(image)
    
    # 이미지 중심점
    height, width = cv_image.shape[:2]
    center = (width // 2, height // 2)
    
    # 회전 변환 행렬
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # 회전 후 이미지 크기 계산
    abs_cos = abs(rotation_matrix[0, 0])
    abs_sin = abs(rotation_matrix[0, 1])
    bound_w = int(height * abs_sin + width * abs_cos)
    bound_h = int(height * abs_cos + width * abs_sin)
    
    # 변환 행렬 조정 (중심 유지)
    rotation_matrix[0, 2] += bound_w / 2 - center[0]
    rotation_matrix[1, 2] += bound_h / 2 - center[1]
    
    # 회전 적용
    rotated = cv2.warpAffine(cv_image, rotation_matrix, (bound_w, bound_h), flags=cv2.INTER_LINEAR)
    
    # PIL 이미지로 변환
    if len(rotated.shape) == 3:
        return Image.fromarray(cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB))
    else:
        return Image.fromarray(rotated)


def detect_document_bounds(image: Union[Image.Image, np.ndarray]) -> List[List[int]]:
    """
    문서 경계 감지
    
    Args:
        image: PIL 이미지 또는 NumPy 배열
    
    Returns:
        문서 경계 좌표 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    """
    try:
        # PIL 이미지를 NumPy 배열로 변환
        if isinstance(image, Image.Image):
            cv_image = np.array(image)
            
            # RGB to BGR 변환 (OpenCV는 BGR 사용)
            if len(cv_image.shape) == 3:
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
        else:
            cv_image = image
        
        # 그레이스케일 변환
        if len(cv_image.shape) == 3:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = cv_image
        
        # 이미지 크기
        height, width = gray.shape
        
        # 이미지 전처리
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 에지 감지
        edges = cv2.Canny(blur, 75, 200)
        
        # 경계 닫기
        kernel = np.ones((5, 5), np.uint8)
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # 윤곽선 감지
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 가장 큰 윤곽선 찾기
        if not contours:
            # 윤곽선이 없으면 전체 이미지 경계 반환
            return [[0, 0], [width, 0], [width, height], [0, height]]
        
        max_contour = max(contours, key=cv2.contourArea)
        
        # 윤곽선 단순화
        epsilon = 0.02 * cv2.arcLength(max_contour, True)
        approx = cv2.approxPolyDP(max_contour, epsilon, True)
        
        # 사각형이 아니면 전체 이미지 경계 반환
        if len(approx) != 4:
            # 면적이 이미지의 50% 이상인 경우 전체 이미지 경계 반환
            if cv2.contourArea(max_contour) > (width * height * 0.5):
                return [[0, 0], [width, 0], [width, height], [0, height]]
            
            # 그렇지 않으면 바운딩 박스 반환
            rect = cv2.minAreaRect(max_contour)
            box = cv2.boxPoints(rect)
            return box.tolist()
        
        # 포인트 정리
        points = approx.reshape(4, 2).tolist()
        
        # 시계 방향으로 정렬
        centroid = np.mean(points, axis=0)
        points.sort(key=lambda p: math.atan2(p[1] - centroid[1], p[0] - centroid[0]))
        
        return points
    
    except Exception as e:
        logger.error(f"문서 경계 감지 오류: {e}")
        
        # 오류 시 전체 이미지 경계 반환
        if isinstance(image, Image.Image):
            width, height = image.size
        else:
            height, width = image.shape[:2]
        
        return [[0, 0], [width, 0], [width, height], [0, height]]


def crop_and_correct_document(image: Image.Image) -> Image.Image:
    """
    문서 자르기 및 원근 보정
    
    Args:
        image: PIL 이미지
    
    Returns:
        보정된 PIL 이미지
    """
    try:
        # NumPy 배열로 변환
        cv_image = np.array(image)
        
        # RGB to BGR 변환 (OpenCV는 BGR 사용)
        if len(cv_image.shape) == 3:
            cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
        
        # 문서 경계 감지
        bounds = detect_document_bounds(cv_image)
        
        # 이미지 크기
        height, width = cv_image.shape[:2]
        
        # 면적이 이미지의 75% 이상이면 그대로 반환
        contour_area = cv2.contourArea(np.array(bounds))
        image_area = width * height
        
        if contour_area > (image_area * 0.75):
            return image
        
        # 원근 변환을 위한 대상 좌표
        # 시계 방향으로 정렬된 좌표: 좌상, 우상, 우하, 좌하
        src_pts = np.array(bounds, dtype=np.float32)
        
        # 대상 크기 계산
        width_a = np.sqrt(((bounds[1][0] - bounds[0][0]) ** 2) + ((bounds[1][1] - bounds[0][1]) ** 2))
        width_b = np.sqrt(((bounds[2][0] - bounds[3][0]) ** 2) + ((bounds[2][1] - bounds[3][1]) ** 2))
        max_width = max(int(width_a), int(width_b))
        
        height_a = np.sqrt(((bounds[3][0] - bounds[0][0]) ** 2) + ((bounds[3][1] - bounds[0][1]) ** 2))
        height_b = np.sqrt(((bounds[2][0] - bounds[1][0]) ** 2) + ((bounds[2][1] - bounds[1][1]) ** 2))
        max_height = max(int(height_a), int(height_b))
        
        # 대상 좌표
        dst_pts = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]
        ], dtype=np.float32)
        
        # 원근 변환 행렬
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        
        # 원근 변환 적용
        warped = cv2.warpPerspective(cv_image, matrix, (max_width, max_height))
        
        # PIL 이미지로 변환
        if len(warped.shape) == 3:
            return Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))
        else:
            return Image.fromarray(warped)
    
    except Exception as e:
        logger.error(f"문서 보정 오류: {e}")
        return image  # 오류 시 원본 반환
