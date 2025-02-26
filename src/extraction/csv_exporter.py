"""
CSV 내보내기 모듈
- 추출된 필드 데이터를 CSV 파일로 내보내기
- 다국어 지원
"""

import csv
import os
import io
import logging
from typing import Dict, Any, List, Optional, Union, BinaryIO
from pathlib import Path
from src.extraction.field_config import FieldConfig

# 로거 설정
logger = logging.getLogger(__name__)


class CSVExporter:
    """추출 데이터를 CSV로 내보내는 클래스"""
    
    def __init__(self):
        """초기화"""
        self.field_config = FieldConfig()
    
    def export_single(self, 
                     extracted_data: Dict[str, Any], 
                     file_path: Optional[str] = None) -> Union[str, BinaryIO]:
        """
        단일 문서 데이터 내보내기
        
        Args:
            extracted_data: 추출된 필드 데이터
            file_path: 저장할 파일 경로 (None이면 메모리에 저장)
        
        Returns:
            파일 경로 또는 파일 객체
        """
        # 필드 목록 가져오기
        fields = self.field_config.get_fields()
        
        # 헤더 구성
        header = [field['name'] for field in fields]
        
        # 데이터 행 구성
        row = [extracted_data.get(field_name, '') for field_name in header]
        
        # CSV 파일로 저장 또는 메모리에 저장
        if file_path:
            return self._save_to_file([header, row], file_path)
        else:
            return self._save_to_memory([header, row])
    
    def export_multiple(self, 
                       extracted_data_list: List[Dict[str, Any]], 
                       file_path: Optional[str] = None,
                       additional_columns: Optional[Dict[str, List[Any]]] = None) -> Union[str, BinaryIO]:
        """
        여러 문서 데이터 내보내기
        
        Args:
            extracted_data_list: 추출된 필드 데이터 목록
            file_path: 저장할 파일 경로 (None이면 메모리에 저장)
            additional_columns: 추가 열 데이터 (예: document_id, timestamp 등)
        
        Returns:
            파일 경로 또는 파일 객체
        """
        if not extracted_data_list:
            logger.warning("내보낼 데이터가 없습니다.")
            return "" if file_path else io.BytesIO()
        
        # 필드 목록 가져오기
        fields = self.field_config.get_fields()
        
        # 기본 헤더 구성
        header = [field['name'] for field in fields]
        
        # 추가 열이 있으면 헤더에 추가
        if additional_columns:
            for col_name in additional_columns.keys():
                if col_name not in header:
                    header.insert(0, col_name)  # 추가 열을 앞에 배치
        
        # 모든 데이터 행 구성
        rows = []
        rows.append(header)  # 헤더 행 추가
        
        for i, extracted_data in enumerate(extracted_data_list):
            row = []
            
            # 추가 열 데이터 추가
            if additional_columns:
                for col_name in header:
                    if col_name in additional_columns:
                        # 인덱스가 범위를 벗어나면 빈 값 사용
                        if i < len(additional_columns[col_name]):
                            row.append(additional_columns[col_name][i])
                        else:
                            row.append('')
                    elif col_name in extracted_data:
                        row.append(extracted_data.get(col_name, ''))
                    else:
                        row.append('')
            else:
                # 추가 열 없이 추출 데이터만 사용
                row = [extracted_data.get(field_name, '') for field_name in header]
            
            rows.append(row)
        
        # CSV 파일로 저장 또는 메모리에 저장
        if file_path:
            return self._save_to_file(rows, file_path)
        else:
            return self._save_to_memory(rows)
    
    def _save_to_file(self, rows: List[List[Any]], file_path: str) -> str:
        """
        데이터를 CSV 파일로 저장
        
        Args:
            rows: CSV 행 데이터 (첫 번째 행은 헤더)
            file_path: 저장할 파일 경로
        
        Returns:
            저장된 파일 경로
        """
        try:
            # 디렉토리 생성
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # UTF-8 BOM 인코딩으로 저장 (Excel 호환)
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            
            logger.info(f"CSV 파일 저장: {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"CSV 파일 저장 오류: {str(e)}")
            raise
    
    def _save_to_memory(self, rows: List[List[Any]]) -> BinaryIO:
        """
        데이터를 메모리 내 CSV로 저장
        
        Args:
            rows: CSV 행 데이터 (첫 번째 행은 헤더)
        
        Returns:
            CSV 데이터가 포함된 BytesIO 객체
        """
        try:
            # UTF-8 BOM 인코딩으로 메모리에 저장 (Excel 호환)
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerows(rows)
            
            # BytesIO로 변환
            memory_file = io.BytesIO()
            memory_file.write(csv_buffer.getvalue().encode('utf-8-sig'))
            memory_file.seek(0)
            
            logger.info("CSV 데이터를 메모리에 저장")
            return memory_file
        
        except Exception as e:
            logger.error(f"CSV 메모리 저장 오류: {str(e)}")
            raise
    
    def export_fields_template(self, file_path: Optional[str] = None) -> Union[str, BinaryIO]:
        """
        필드 설정 템플릿 내보내기
        
        Args:
            file_path: 저장할 파일 경로 (None이면 메모리에 저장)
        
        Returns:
            파일 경로 또는 파일 객체
        """
        # 필드 목록 가져오기
        fields = self.field_config.get_fields()
        
        # 템플릿 헤더
        header = ['name', 'type', 'context', 'regex']
        
        # 템플릿 행 구성
        rows = [header]
        for field in fields:
            row = [
                field['name'],
                field.get('type', 'text'),
                field.get('context', ''),
                field.get('regex', '')
            ]
            rows.append(row)
        
        # CSV 파일로 저장 또는 메모리에 저장
        if file_path:
            return self._save_to_file(rows, file_path)
        else:
            return self._save_to_memory(rows)
    
    def import_fields_from_csv(self, file_path: str) -> bool:
        """
        CSV 파일에서 필드 설정 가져오기
        
        Args:
            file_path: CSV 파일 경로
        
        Returns:
            성공 여부
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"파일을 찾을 수 없음: {file_path}")
                return False
            
            # CSV 파일 읽기
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                # 필수 열 확인
                required_columns = ['name', 'type']
                for column in required_columns:
                    if column not in reader.fieldnames:
                        logger.error(f"CSV 파일에 필수 열이 없음: {column}")
                        return False
                
                # 필드 설정 초기화
                new_fields = []
                
                # 각 행을 필드 설정으로 변환
                for row in reader:
                    field = {
                        'name': row['name'],
                        'type': row['type']
                    }
                    
                    # 선택적 열 추가
                    if 'context' in row and row['context']:
                        field['context'] = row['context']
                    
                    if 'regex' in row and row['regex']:
                        field['regex'] = row['regex']
                    
                    new_fields.append(field)
                
                # 필드 설정 저장
                self.field_config.fields = new_fields
                self.field_config._save_fields()
                
                logger.info(f"CSV에서 {len(new_fields)}개의 필드 설정을 가져왔습니다.")
                return True
        
        except Exception as e:
            logger.error(f"CSV에서 필드 설정 가져오기 오류: {str(e)}")
            return False
