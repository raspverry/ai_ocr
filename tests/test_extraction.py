"""
데이터 추출 관련 테스트 모듈
- LLM 기반 필드 추출 테스트
- CSV 내보내기 테스트
"""

import os
import json
import csv
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from src.extraction.llm_processor import LLMProcessor
from src.extraction.field_config import FieldConfig
from src.extraction.csv_exporter import CSVExporter


class TestLLMProcessor:
    """LLM 프로세서 테스트 클래스"""
    
    @pytest.fixture
    def sample_ocr_text(self):
        """샘플 OCR 텍스트 픽스처"""
        return """
        株式会社テスト
        〒123-4567 東京都新宿区西新宿1-1-1
        TEL: 03-1234-5678
        
        請求書 No.2023-001
        
        発行日: 2023年4月1日
        支払期限: 2023年4月30日
        
        商品名                 数量    単価      金額
        ソフトウェア開発        1     500,000    500,000
        サーバー保守            2     100,000    200,000
        
        小計                              700,000
        消費税 (10%)                       70,000
        合計                              770,000
        """
    
    @pytest.fixture
    def sample_fields(self):
        """샘플 필드 설정 픽스처"""
        return [
            {
                "name": "invoice_number",
                "type": "text",
                "context": "請求書 No.|Invoice No."
            },
            {
                "name": "date",
                "type": "date",
                "context": "発行日|Issue Date"
            },
            {
                "name": "company_name",
                "type": "company",
                "context": "会社名|Company"
            },
            {
                "name": "total_amount",
                "type": "amount",
                "context": "合計|Total"
            },
            {
                "name": "tax_amount",
                "type": "amount",
                "context": "消費税|Tax"
            }
        ]
    
    @patch('openai.ChatCompletion.create')
    def test_extract_fields_openai(self, mock_openai, sample_ocr_text, sample_fields):
        """OpenAI를 통한 필드 추출 테스트"""
        # 모의 OpenAI 응답 설정
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "invoice_number": "2023-001",
            "date": "2023-04-01",
            "company_name": "株式会社テスト",
            "total_amount": 770000,
            "tax_amount": 70000
        })
        mock_openai.return_value = mock_response
        
        # LLM 프로세서 설정
        llm_processor = LLMProcessor()
        llm_processor.provider = 'openai'
        
        # 필드 추출 실행
        result = llm_processor.extract_fields(sample_ocr_text, sample_fields, "jpn")
        
        # 결과 검증
        assert 'fields' in result
        assert result['fields']['invoice_number'] == "2023-001"
        assert result['fields']['date'] == "2023-04-01"
        assert result['fields']['company_name'] == "株式会社テスト"
        assert result['fields']['total_amount'] == 770000
        assert result['fields']['tax_amount'] == 70000
    
    @patch('anthropic.Anthropic')
    def test_extract_fields_anthropic(self, mock_anthropic, sample_ocr_text, sample_fields):
        """Anthropic을 통한 필드 추출 테스트"""
        # 모의 Anthropic 응답 설정
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = json.dumps({
            "invoice_number": "2023-001",
            "date": "2023-04-01",
            "company_name": "株式会社テスト",
            "total_amount": 770000,
            "tax_amount": 70000
        })
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        # LLM 프로세서 설정
        llm_processor = LLMProcessor()
        llm_processor.provider = 'anthropic'
        llm_processor.anthropic_client = mock_client
        
        # 필드 추출 실행
        result = llm_processor.extract_fields(sample_ocr_text, sample_fields, "jpn")
        
        # 결과 검증
        assert 'fields' in result
        assert result['fields']['invoice_number'] == "2023-001"
        assert result['fields']['date'] == "2023-04-01"
        assert result['fields']['company_name'] == "株式会社テスト"
        assert result['fields']['total_amount'] == 770000
        assert result['fields']['tax_amount'] == 70000
    
    def test_build_prompt(self, sample_ocr_text, sample_fields):
        """프롬프트 생성 테스트"""
        # LLM 프로세서 생성
        llm_processor = LLMProcessor()
        
        # 필드 설명 준비
        field_descriptions = llm_processor._prepare_field_descriptions(sample_fields, "jpn")
        
        # 프롬프트 생성
        prompt = llm_processor._build_prompt(sample_ocr_text, field_descriptions, "jpn")
        
        # 결과 검증
        assert prompt is not None
        assert isinstance(prompt, str)
        assert "일본어 문서에서 다음 필드를 추출하세요" in prompt
        assert "invoice_number" in prompt
        assert "date" in prompt
        assert "company_name" in prompt
        assert "total_amount" in prompt
        assert "tax_amount" in prompt
        assert "JSON 형식" in prompt
        assert sample_ocr_text in prompt
    
    def test_parse_response_valid_json(self):
        """유효한 JSON 응답 파싱 테스트"""
        # 샘플 JSON 응답
        sample_response = """
        ```json
        {
            "invoice_number": "2023-001",
            "date": "2023-04-01",
            "company_name": "株式会社テスト",
            "total_amount": 770000,
            "tax_amount": 70000
        }
        ```
        """
        
        # 필드 설정
        fields = [
            {"name": "invoice_number", "type": "text"},
            {"name": "date", "type": "date"},
            {"name": "company_name", "type": "company"},
            {"name": "total_amount", "type": "amount"},
            {"name": "tax_amount", "type": "amount"}
        ]
        
        # LLM 프로세서 생성
        llm_processor = LLMProcessor()
        
        # 응답 파싱
        result = llm_processor._parse_response(sample_response, fields)
        
        # 결과 검증
        assert result is not None
        assert isinstance(result, dict)
        assert result["invoice_number"] == "2023-001"
        assert result["date"] == "2023-04-01"
        assert result["company_name"] == "株式会社テスト"
        assert result["total_amount"] == 770000
        assert result["tax_amount"] == 70000
    
    def test_parse_response_invalid_json(self):
        """잘못된 JSON 응답 파싱 테스트"""
        # 잘못된 형식의 JSON 응답
        sample_response = """
        This is not a valid JSON response.
        ```
        {
            "invoice_number": "2023-001",
            missing quotes and comma
            "total_amount": 770000
        }
        ```
        """
        
        # 필드 설정
        fields = [
            {"name": "invoice_number", "type": "text"},
            {"name": "date", "type": "date"},
            {"name": "company_name", "type": "company"},
            {"name": "total_amount", "type": "amount"},
            {"name": "tax_amount", "type": "amount"}
        ]
        
        # LLM 프로세서 생성
        llm_processor = LLMProcessor()
        
        # 응답 파싱
        result = llm_processor._parse_response(sample_response, fields)
        
        # 결과 검증
        assert result is not None
        assert isinstance(result, dict)
        assert len(result) == 0  # 파싱 실패로 빈 딕셔너리 반환


class TestFieldConfig:
    """필드 설정 테스트 클래스"""
    
    @pytest.fixture
    def temp_config_file(self):
        """임시 설정 파일 픽스처"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            f.write(b'[]')
            temp_path = f.name
        
        yield temp_path
        
        # 테스트 후 파일 삭제
        os.unlink(temp_path)
    
    def test_get_fields(self, temp_config_file):
        """필드 설정 가져오기 테스트"""
        # 테스트 필드 데이터
        test_fields = [
            {
                "name": "test_field",
                "type": "text",
                "context": "테스트|test"
            }
        ]
        
        # 임시 파일에 필드 데이터 저장
        with open(temp_config_file, 'w') as f:
            json.dump(test_fields, f)
        
        # 필드 설정 로드
        field_config = FieldConfig(temp_config_file)
        
        # 필드 가져오기 테스트
        fields = field_config.get_fields()
        
        # 결과 검증
        assert len(fields) == 1
        assert fields[0]["name"] == "test_field"
        assert fields[0]["type"] == "text"
        assert fields[0]["context"] == "테스트|test"
    
    def test_get_field(self, temp_config_file):
        """특정 필드 가져오기 테스트"""
        # 테스트 필드 데이터
        test_fields = [
            {
                "name": "field1",
                "type": "text"
            },
            {
                "name": "field2",
                "type": "date"
            }
        ]
        
        # 임시 파일에 필드 데이터 저장
        with open(temp_config_file, 'w') as f:
            json.dump(test_fields, f)
        
        # 필드 설정 로드
        field_config = FieldConfig(temp_config_file)
        
        # 특정 필드 가져오기 테스트
        field = field_config.get_field("field2")
        
        # 결과 검증
        assert field is not None
        assert field["name"] == "field2"
        assert field["type"] == "date"
        
        # 존재하지 않는 필드 테스트
        field = field_config.get_field("nonexistent")
        assert field is None
    
    def test_add_field(self, temp_config_file):
        """필드 추가 테스트"""
        # 필드 설정 생성
        field_config = FieldConfig(temp_config_file)
        
        # 새 필드 추가
        new_field = {
            "name": "new_field",
            "type": "text",
            "context": "새 필드|new field"
        }
        result = field_config.add_field(new_field)
        
        # 결과 검증
        assert result == True
        
        # 필드 확인
        fields = field_config.get_fields()
        assert len(fields) == 1
        assert fields[0]["name"] == "new_field"
        
        # 중복 필드 추가 시도
        result = field_config.add_field(new_field)
        assert result == False  # 중복으로 인한 실패
    
    def test_update_field(self, temp_config_file):
        """필드 업데이트 테스트"""
        # 테스트 필드 데이터
        test_fields = [
            {
                "name": "field1",
                "type": "text",
                "context": "원본 컨텍스트"
            }
        ]
        
        # 임시 파일에 필드 데이터 저장
        with open(temp_config_file, 'w') as f:
            json.dump(test_fields, f)
        
        # 필드 설정 로드
        field_config = FieldConfig(temp_config_file)
        
        # 필드 업데이트
        updated_field = {
            "name": "field1",
            "type": "text",
            "context": "업데이트된 컨텍스트"
        }
        result = field_config.update_field("field1", updated_field)
        
        # 결과 검증
        assert result == True
        
        # 필드 확인
        field = field_config.get_field("field1")
        assert field["context"] == "업데이트된 컨텍스트"
        
        # 존재하지 않는 필드 업데이트 시도
        result = field_config.update_field("nonexistent", updated_field)
        assert result == False
    
    def test_delete_field(self, temp_config_file):
        """필드 삭제 테스트"""
        # 테스트 필드 데이터
        test_fields = [
            {"name": "field1", "type": "text"},
            {"name": "field2", "type": "date"}
        ]
        
        # 임시 파일에 필드 데이터 저장
        with open(temp_config_file, 'w') as f:
            json.dump(test_fields, f)
        
        # 필드 설정 로드
        field_config = FieldConfig(temp_config_file)
        
        # 필드 삭제
        result = field_config.delete_field("field1")
        
        # 결과 검증
        assert result == True
        
        # 필드 확인
        fields = field_config.get_fields()
        assert len(fields) == 1
        assert fields[0]["name"] == "field2"
        
        # 존재하지 않는 필드 삭제 시도
        result = field_config.delete_field("nonexistent")
        assert result == False


class TestCSVExporter:
    """CSV 내보내기 테스트 클래스"""
    
    @pytest.fixture
    def sample_extracted_data(self):
        """샘플 추출 데이터 픽스처"""
        return {
            "invoice_number": "2023-001",
            "date": "2023-04-01",
            "company_name": "株式会社テスト",
            "total_amount": 770000,
            "tax_amount": 70000
        }
    
    @pytest.fixture
    def sample_multiple_data(self):
        """샘플 다중 추출 데이터 픽스처"""
        return [
            {
                "invoice_number": "2023-001",
                "date": "2023-04-01",
                "company_name": "株式会社テスト",
                "total_amount": 770000,
                "tax_amount": 70000
            },
            {
                "invoice_number": "2023-002",
                "date": "2023-04-15",
                "company_name": "テスト株式会社",
                "total_amount": 550000,
                "tax_amount": 55000
            }
        ]
    
    @patch('src.extraction.field_config.FieldConfig.get_fields')
    def test_export_single(self, mock_get_fields, sample_extracted_data):
        """단일 데이터 내보내기 테스트"""
        # 필드 설정 모의 객체 설정
        mock_get_fields.return_value = [
            {"name": "invoice_number"},
            {"name": "date"},
            {"name": "company_name"},
            {"name": "total_amount"},
            {"name": "tax_amount"}
        ]
        
        # CSV 내보내기
        exporter = CSVExporter()
        result = exporter.export_single(sample_extracted_data)
        
        # 결과 검증
        assert result is not None
        
        # 메모리 버퍼에서 CSV 읽기
        result.seek(0)
        reader = csv.reader(result.read().decode('utf-8-sig').splitlines())
        rows = list(reader)
        
        # 헤더 검증
        assert rows[0] == ["invoice_number", "date", "company_name", "total_amount", "tax_amount"]
        
        # 데이터 검증
        assert rows[1][0] == "2023-001"
        assert rows[1][1] == "2023-04-01"
        assert rows[1][2] == "株式会社テスト"
        assert rows[1][3] == "770000"
        assert rows[1][4] == "70000"
    
    @patch('src.extraction.field_config.FieldConfig.get_fields')
    def test_export_multiple(self, mock_get_fields, sample_multiple_data):
        """다중 데이터 내보내기 테스트"""
        # 필드 설정 모의 객체 설정
        mock_get_fields.return_value = [
            {"name": "invoice_number"},
            {"name": "date"},
            {"name": "company_name"},
            {"name": "total_amount"},
            {"name": "tax_amount"}
        ]
        
        # 추가 열 데이터
        additional_columns = {
            "document_id": ["doc1", "doc2"],
            "timestamp": ["2023-04-02", "2023-04-16"]
        }
        
        # CSV 내보내기
        exporter = CSVExporter()
        result = exporter.export_multiple(sample_multiple_data, additional_columns=additional_columns)
        
        # 결과 검증
        assert result is not None
        
        # 메모리 버퍼에서 CSV 읽기
        result.seek(0)
        reader = csv.reader(result.read().decode('utf-8-sig').splitlines())
        rows = list(reader)
        
        # 헤더 검증 (추가 열 포함)
        assert "document_id" in rows[0]
        assert "timestamp" in rows[0]
        assert "invoice_number" in rows[0]
        
        # 데이터 검증
        assert "doc1" in rows[1]
        assert "doc2" in rows[2]
        assert "2023-001" in rows[1]
        assert "2023-002" in rows[2]
    
    def test_export_to_file(self, sample_extracted_data, tmp_path):
        """파일로 내보내기 테스트"""
        # 임시 파일 경로
        temp_file = os.path.join(tmp_path, "export.csv")
        
        # CSV 내보내기
        exporter = CSVExporter()
        result = exporter.export_single(sample_extracted_data, file_path=temp_file)
        
        # 결과 검증
        assert result == temp_file
        assert os.path.exists(temp_file)
        
        # 파일에서 CSV 읽기
        with open(temp_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # 데이터 검증
        assert len(rows) == 2  # 헤더 + 데이터 행
        assert "2023-001" in rows[1]
        assert "株式会社テスト" in rows[1]
    
    @patch('src.extraction.field_config.FieldConfig.get_fields')
    def test_export_fields_template(self, mock_get_fields):
        """필드 템플릿 내보내기 테스트"""
        # 필드 설정 모의 객체 설정
        mock_get_fields.return_value = [
            {"name": "field1", "type": "text", "context": "컨텍스트1", "regex": "패턴1"},
            {"name": "field2", "type": "date", "context": "컨텍스트2"}
        ]
        
        # 필드 템플릿 내보내기
        exporter = CSVExporter()
        result = exporter.export_fields_template()
        
        # 결과 검증
        assert result is not None
        
        # 메모리 버퍼에서 CSV 읽기
        result.seek(0)
        reader = csv.reader(result.read().decode('utf-8-sig').splitlines())
        rows = list(reader)
        
        # 헤더 검증
        assert rows[0] == ["name", "type", "context", "regex"]
        
        # 데이터 검증
        assert rows[1][0] == "field1"
        assert rows[1][1] == "text"
        assert rows[1][2] == "컨텍스트1"
        assert rows[1][3] == "패턴1"
        
        assert rows[2][0] == "field2"
        assert rows[2][1] == "date"
        assert rows[2][2] == "컨텍스트2"
        assert rows[2][3] == ""  # 비어있는 regex
