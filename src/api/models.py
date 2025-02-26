"""
API 요청/응답 모델 모듈
- Pydantic 모델 정의
- API 요청 및 응답 검증
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field


class OCRRequest(BaseModel):
    """OCR 처리 요청 모델"""
    
    language: Optional[str] = Field(
        default=None,
        description="언어 코드 (자동 감지하려면 비워두기)"
    )
    
    use_cache: bool = Field(
        default=True,
        description="캐시 사용 여부"
    )
    
    extract_entities: bool = Field(
        default=True,
        description="엔티티 추출 여부 (회사명, 날짜, 금액 등)"
    )
    
    return_images: bool = Field(
        default=False,
        description="이미지 데이터 반환 여부 (base64 인코딩)"
    )


class OCRResponse(BaseModel):
    """OCR 작업 상태 응답 모델"""
    
    task_id: Optional[str] = Field(
        default=None,
        description="작업 ID"
    )
    
    status: str = Field(
        description="작업 상태 (processing, error)"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="오류 메시지 (오류 발생 시)"
    )


class OCRPage(BaseModel):
    """OCR 페이지 결과 모델"""
    
    page_num: int = Field(
        description="페이지 번호"
    )
    
    text: str = Field(
        description="추출된 텍스트"
    )
    
    language: str = Field(
        description="감지된 언어 코드"
    )
    
    confidence: float = Field(
        description="인식 신뢰도 (0.0-1.0)"
    )
    
    entities: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="추출된 엔티티 (회사명, 날짜, 금액 등)"
    )
    
    special_items: Optional[Dict[str, Any]] = Field(
        default=None,
        description="특수 항목 (도장, 손글씨, 취소선 등)"
    )
    
    image: Optional[str] = Field(
        default=None,
        description="페이지 이미지 데이터 (base64 인코딩)"
    )
    
    engine_results: Optional[Dict[str, Any]] = Field(
        default=None,
        description="OCR 엔진별 결과 (디버그 모드에서만)"
    )


class OCRResult(BaseModel):
    """OCR 처리 결과 모델"""
    
    file_id: Optional[str] = Field(
        default=None,
        description="파일 ID"
    )
    
    file_name: Optional[str] = Field(
        default=None,
        description="파일명"
    )
    
    file_type: Optional[str] = Field(
        default=None,
        description="파일 유형"
    )
    
    text: Optional[str] = Field(
        default=None,
        description="전체 추출 텍스트"
    )
    
    confidence: Optional[float] = Field(
        default=None,
        description="전체 인식 신뢰도 (0.0-1.0)"
    )
    
    language: Optional[str] = Field(
        default=None,
        description="주요 감지 언어"
    )
    
    pages: List[OCRPage] = Field(
        default_factory=list,
        description="페이지별 OCR 결과"
    )
    
    entities: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="문서 전체 엔티티"
    )
    
    process_time: float = Field(
        description="처리 시간 (초)"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="오류 메시지 (오류 발생 시)"
    )


class ExtractionRequest(BaseModel):
    """데이터 추출 요청 모델"""
    
    fields: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="추출할 필드 목록 (없으면 기본 필드 사용)"
    )
    
    language: Optional[str] = Field(
        default=None,
        description="언어 코드 (OCR 감지 언어를 사용하려면 비워두기)"
    )


class ExtractionResult(BaseModel):
    """데이터 추출 결과 모델"""
    
    ocr_task_id: str = Field(
        description="OCR 작업 ID"
    )
    
    fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="추출된 필드 값"
    )
    
    confidence: Dict[str, float] = Field(
        default_factory=dict,
        description="필드별 신뢰도 (0.0-1.0)"
    )
    
    language: str = Field(
        description="사용된 언어 코드"
    )
    
    process_time: float = Field(
        description="처리 시간 (초)"
    )
    
    raw_response: Optional[str] = Field(
        default=None,
        description="LLM 원본 응답 (디버그 모드에서만)"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="오류 메시지 (오류 발생 시)"
    )
