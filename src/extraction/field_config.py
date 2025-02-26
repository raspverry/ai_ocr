"""
필드 설정 관리 모듈
- 추출 필드 설정 로드, 저장, 수정
- 웹 UI에서 설정 가능
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from src.core.config import config

# 로거 설정
logger = logging.getLogger(__name__)


class FieldConfig:
    """필드 설정 관리 클래스"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        초기화
        
        Args:
            config_file: 필드 설정 파일 경로 (None이면 기본 경로 사용)
        """
        self.config_file = config_file or os.path.join('configs', 'fields.json')
        
        # 기본 필드 설정
        self.default_fields = config.get('extraction.default_fields', [])
        
        # 사용자 정의 필드 로드
        self.fields = self._load_fields()
    
    def _load_fields(self) -> List[Dict[str, Any]]:
        """
        필드 설정 파일 로드
        
        Returns:
            필드 설정 목록
        """
        try:
            # 파일이 존재하면 로드
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    fields = json.load(f)
                logger.info(f"필드 설정 로드: {len(fields)}개의 필드")
                return fields
            
            # 파일이 없으면 기본 필드 반환
            logger.info(f"필드 설정 파일이 없습니다. 기본 설정 사용 ({len(self.default_fields)}개의 필드)")
            return self.default_fields
        
        except Exception as e:
            logger.error(f"필드 설정 로드 오류: {str(e)}")
            return self.default_fields
    
    def get_fields(self) -> List[Dict[str, Any]]:
        """
        모든 필드 설정 가져오기
        
        Returns:
            필드 설정 목록
        """
        return self.fields.copy()
    
    def get_field(self, field_name: str) -> Optional[Dict[str, Any]]:
        """
        특정 필드 설정 가져오기
        
        Args:
            field_name: 필드 이름
        
        Returns:
            필드 설정 (없으면 None)
        """
        for field in self.fields:
            if field['name'] == field_name:
                return field.copy()
        return None
    
    def add_field(self, field: Dict[str, Any]) -> bool:
        """
        새 필드 추가
        
        Args:
            field: 추가할 필드 설정
        
        Returns:
            성공 여부
        """
        # 필수 키 확인
        if 'name' not in field:
            logger.error("필드에 'name' 키가 없습니다.")
            return False
        
        # 중복 확인
        for existing_field in self.fields:
            if existing_field['name'] == field['name']:
                logger.warning(f"이미 존재하는 필드 이름: {field['name']}")
                return False
        
        # 필드 추가
        self.fields.append(field)
        
        # 설정 저장
        self._save_fields()
        logger.info(f"새 필드 추가: {field['name']}")
        
        return True
    
    def update_field(self, field_name: str, updated_field: Dict[str, Any]) -> bool:
        """
        기존 필드 업데이트
        
        Args:
            field_name: 업데이트할 필드 이름
            updated_field: 새 필드 설정
        
        Returns:
            성공 여부
        """
        # 필드 찾기
        for i, field in enumerate(self.fields):
            if field['name'] == field_name:
                # 이름 변경 없이 업데이트하는 경우
                if updated_field.get('name') == field_name:
                    self.fields[i] = updated_field
                    self._save_fields()
                    logger.info(f"필드 업데이트: {field_name}")
                    return True
                
                # 이름 변경하는 경우 (중복 확인)
                for other_field in self.fields:
                    if other_field['name'] == updated_field['name'] and other_field != field:
                        logger.warning(f"이미 존재하는 필드 이름: {updated_field['name']}")
                        return False
                
                # 업데이트
                self.fields[i] = updated_field
                self._save_fields()
                logger.info(f"필드 업데이트: {field_name} -> {updated_field['name']}")
                return True
        
        logger.warning(f"필드를 찾을 수 없음: {field_name}")
        return False
    
    def delete_field(self, field_name: str) -> bool:
        """
        필드 삭제
        
        Args:
            field_name: 삭제할 필드 이름
        
        Returns:
            성공 여부
        """
        initial_length = len(self.fields)
        self.fields = [field for field in self.fields if field['name'] != field_name]
        
        if len(self.fields) < initial_length:
            self._save_fields()
            logger.info(f"필드 삭제: {field_name}")
            return True
        
        logger.warning(f"필드를 찾을 수 없음: {field_name}")
        return False
    
    def reset_to_default(self) -> None:
        """기본 필드로 초기화"""
        self.fields = self.default_fields.copy()
        self._save_fields()
        logger.info("필드 설정을 기본값으로 재설정")
    
    def _save_fields(self) -> None:
        """필드 설정 파일 저장"""
        try:
            # 디렉토리 생성
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # 파일 저장
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.fields, f, indent=2, ensure_ascii=False)
            
            logger.info(f"필드 설정 저장: {self.config_file}")
        
        except Exception as e:
            logger.error(f"필드 설정 저장 오류: {str(e)}")
