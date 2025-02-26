"""
설정 관리 모듈
- YAML 설정 파일 및 환경 변수에서 설정 로드
- 전역 설정 객체 제공
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """설정 관리 클래스"""
    _instance = None
    
    def __new__(cls):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """초기화 (한 번만 실행)"""
        if self._initialized:
            return
        
        self._config_data = {}
        self._load_default_config()
        self._load_env_vars()
        self._initialized = True
    
    def _load_default_config(self):
        """기본 설정 파일 로드"""
        config_path = os.getenv('CONFIG_PATH', 'configs/default.yml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f)
            print(f"설정 파일 로드: {config_path}")
        except Exception as e:
            print(f"설정 파일 로드 실패: {e}")
            # 설정 파일이 없는 경우 기본 빈 설정 사용
            self._config_data = {}
    
    def _load_env_vars(self):
        """환경 변수에서 설정 오버라이드"""
        # 모든 OCR_ 접두사 환경 변수 처리
        for key, value in os.environ.items():
            if key.startswith('OCR_'):
                # 환경 변수 이름을 설정 키로 변환 (OCR_REDIS_URL -> queue.redis_url)
                config_key = key[4:].lower()
                
                # 점(.)으로 구분된 계층 구조 처리
                parts = config_key.split('_')
                
                # 첫 번째 부분은 최상위 섹션
                section = parts[0]
                
                # 나머지 부분은 하위 키
                if len(parts) > 1:
                    subsection = '_'.join(parts[1:])
                    
                    # 섹션이 없으면 생성
                    if section not in self._config_data:
                        self._config_data[section] = {}
                    
                    # 값 설정 (자료형 변환 시도)
                    self._config_data[section][subsection] = self._parse_value(value)
                else:
                    # 최상위 키인 경우
                    self._config_data[section] = self._parse_value(value)
        
        # 특수 환경 변수 처리
        if 'REDIS_URL' in os.environ:
            self._config_data.setdefault('queue', {})['redis_url'] = os.environ['REDIS_URL']
        
        if 'PORT' in os.environ:
            port = int(os.environ['PORT'])
            self._config_data.setdefault('app', {})['api_port'] = port
            self._config_data.setdefault('app', {})['web_port'] = port
        
        # API 키 환경 변수
        if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
            self._config_data.setdefault('ocr', {})['google_credentials'] = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
        
        if 'AZURE_FORM_KEY' in os.environ:
            self._config_data.setdefault('ocr', {})['azure_form_key'] = os.environ['AZURE_FORM_KEY']
        
        if 'AZURE_FORM_ENDPOINT' in os.environ:
            self._config_data.setdefault('ocr', {})['azure_form_endpoint'] = os.environ['AZURE_FORM_ENDPOINT']
        
        if 'OPENAI_API_KEY' in os.environ:
            self._config_data.setdefault('extraction', {}).setdefault('llm', {})['openai_api_key'] = os.environ['OPENAI_API_KEY']
        
        if 'ANTHROPIC_API_KEY' in os.environ:
            self._config_data.setdefault('extraction', {}).setdefault('llm', {})['anthropic_api_key'] = os.environ['ANTHROPIC_API_KEY']
    
    def _parse_value(self, value: str) -> Any:
        """문자열 값을 적절한 자료형으로 변환"""
        # 불리언 값 처리
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        
        # 정수 처리
        try:
            return int(value)
        except ValueError:
            pass
        
        # 실수 처리
        try:
            return float(value)
        except ValueError:
            pass
        
        # 기본 문자열 반환
        return value
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정 값 가져오기 (점 표기법 지원)"""
        parts = key.split('.')
        
        # 설정에서 값 탐색
        current = self._config_data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def set(self, key: str, value: Any) -> None:
        """설정 값 설정 (점 표기법 지원)"""
        parts = key.split('.')
        
        # 마지막 부분을 제외한 모든 부분은 딕셔너리 경로
        current = self._config_data
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        
        # 마지막 부분은 실제 키
        current[parts[-1]] = value
    
    def get_all(self) -> Dict[str, Any]:
        """모든 설정 반환"""
        return self._config_data.copy()
    
    def save(self, path: Optional[str] = None) -> None:
        """설정을 파일에 저장"""
        if path is None:
            path = os.getenv('CONFIG_PATH', 'configs/default.yml')
        
        # 디렉토리 생성
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        # 파일 저장
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config_data, f, default_flow_style=False, allow_unicode=True)


# 전역 설정 객체
config = Config()
