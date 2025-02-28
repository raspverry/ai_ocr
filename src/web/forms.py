"""
웹 폼 정의 모듈
- 로그인, 업로드, 설정 등 폼 정의
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class LoginForm(BaseModel):
    """로그인 폼"""
    username: str = Field(..., title="사용자 이름")
    password: str = Field(..., title="비밀번호")
    remember_me: bool = Field(default=False, title="로그인 상태 유지")
    
    @validator('username')
    def username_must_not_be_empty(cls, value):
        if not value.strip():
            raise ValueError('사용자 이름을 입력해주세요')
        return value
    
    @validator('password')
    def password_must_not_be_empty(cls, value):
        if not value.strip():
            raise ValueError('비밀번호를 입력해주세요')
        return value


class UploadForm(BaseModel):
    """파일 업로드 폼"""
    file: Any = Field(..., title="파일")
    language: Optional[str] = Field(None, title="언어 코드")
    extract_entities: bool = Field(default=True, title="엔티티 추출 여부")
    
    class Config:
        arbitrary_types_allowed = True


class ExtractionField(BaseModel):
    """추출 필드 설정"""
    name: str = Field(..., title="필드 이름")
    type: str = Field(default="text", title="필드 유형")
    context: Optional[str] = Field(None, title="컨텍스트")
    regex: Optional[str] = Field(None, title="정규식 패턴")


class ExtractionForm(BaseModel):
    """데이터 추출 폼"""
    fields: Optional[List[ExtractionField]] = Field(None, title="추출 필드 목록")
    language: Optional[str] = Field(None, title="언어 코드")
    
    @validator('fields')
    def validate_fields(cls, values):
        """필드 유효성 검사"""
        if values:
            # 필드 이름 중복 확인
            field_names = [field.name for field in values]
            if len(field_names) != len(set(field_names)):
                raise ValueError('필드 이름이 중복되었습니다.')
        
        return values


class SettingsForm(BaseModel):
    """설정 폼"""
    fields: Optional[str] = Field(None, title="필드 설정 (JSON)")
    use_custom_model: bool = Field(default=True, title="커스텀 모델 사용")
    use_tesseract: bool = Field(default=True, title="Tesseract 사용")
    use_google_vision: bool = Field(default=False, title="Google Vision 사용")
    use_azure_form: bool = Field(default=False, title="Azure Form Recognizer 사용")
    confidence_threshold: float = Field(default=0.85, title="신뢰도 임계값")
    detect_stamps: bool = Field(default=True, title="도장 감지")
    detect_handwriting: bool = Field(default=True, title="손글씨 감지")
    detect_strikethrough: bool = Field(default=True, title="취소선 감지")
    
    @validator('confidence_threshold')
    def validate_confidence_threshold(cls, value):
        """신뢰도 임계값 유효성 검사"""
        if value < 0.0 or value > 1.0:
            raise ValueError('신뢰도 임계값은 0.0에서 1.0 사이여야 합니다.')
        
        return value
