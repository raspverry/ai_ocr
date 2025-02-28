"""
API 관련 테스트 모듈
- API 엔드포인트 테스트
- 요청 및 응답 검증
"""

import os
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# 메인 애플리케이션 로드
from main import app
from src.api.models import OCRRequest, OCRResponse

# 테스트 클라이언트 생성
client = TestClient(app)


class TestAPI:
    """API 테스트 클래스"""
    
    @pytest.fixture
    def sample_pdf(self):
        """샘플 PDF 픽스처"""
        # 테스트 데이터 디렉토리
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # 샘플 PDF 파일 경로
        pdf_path = os.path.join(data_dir, 'sample.pdf')
        
        # 샘플 PDF 파일이 없으면 생성
        if not os.path.exists(pdf_path):
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            # 샘플 PDF 생성
            c = canvas.Canvas(pdf_path, pagesize=letter)
            c.drawString(100, 750, "Sample PDF for Testing")
            c.drawString(100, 700, "일본어 샘플 텍스트: これはテストです")
            c.drawString(100, 650, "한국어 샘플 텍스트: 테스트입니다")
            c.save()
        
        return pdf_path
    
    @pytest.fixture
    def mock_redis(self):
        """Redis 모의 객체 픽스처"""
        with patch('redis.Redis') as mock:
            # Redis 연결 성공 시뮬레이션
            mock.return_value.ping.return_value = True
            yield mock
    
    @pytest.fixture
    def mock_rq(self):
        """RQ 모의 객체 픽스처"""
        with patch('rq.Queue') as mock:
            # 작업 ID 시뮬레이션
            mock_job = MagicMock()
            mock_job.id = "test-job-id"
            mock.return_value.enqueue.return_value = mock_job
            yield mock
    
    def test_health_check(self):
        """서비스 상태 확인 API 테스트"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_languages_endpoint(self):
        """지원 언어 목록 API 테스트"""
        response = client.get("/api/v1/languages")
        
        assert response.status_code == 200
        assert "languages" in response.json()
        assert isinstance(response.json()["languages"], dict)
        
        # 지원 언어 확인
        languages = response.json()["languages"]
        assert "jpn" in languages
        assert "eng" in languages
        assert "kor" in languages
    
    def test_ocr_endpoint_invalid_file(self):
        """OCR API 잘못된 파일 테스트"""
        # 텍스트 파일 생성
        with open("test.txt", "w") as f:
            f.write("This is a test.")
        
        # 잘못된 파일 형식 제출
        with open("test.txt", "rb") as f:
            response = client.post(
                "/api/v1/ocr",
                files={"file": ("test.txt", f, "text/plain")},
                data={"options": "{}"}
            )
        
        # 파일 삭제
        os.remove("test.txt")
        
        # 응답 검증
        assert response.status_code == 400
        assert "지원하지 않는 파일 형식입니다" in response.json()["detail"]
    
    def test_ocr_endpoint_success(self, sample_pdf, mock_redis, mock_rq):
        """OCR API 성공 테스트"""
        # OCR 요청 옵션
        options = json.dumps({
            "language": "jpn",
            "extract_entities": True,
            "use_cache": True
        })
        
        # API 요청
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/api/v1/ocr",
                files={"file": ("sample.pdf", f, "application/pdf")},
                data={"options": options}
            )
        
        # 응답 검증
        assert response.status_code == 200
        assert response.json()["task_id"] == "test-job-id"
        assert response.json()["status"] == "processing"
    
    @patch('rq.job.Job.fetch')
    def test_get_ocr_result_processing(self, mock_job_fetch, mock_redis):
        """OCR 결과 조회 API 처리 중 테스트"""
        # 작업 상태 시뮬레이션
        mock_job = MagicMock()
        mock_job.is_finished = False
        mock_job.is_failed = False
        mock_job_fetch.return_value = mock_job
        
        # API 요청
        response = client.get("/api/v1/ocr/test-job-id")
        
        # 응답 검증
        assert response.status_code == 200
        assert response.json()["status"] == "processing"
        assert response.json()["task_id"] == "test-job-id"
    
    @patch('rq.job.Job.fetch')
    def test_get_ocr_result_completed(self, mock_job_fetch, mock_redis):
        """OCR 결과 조회 API 완료 테스트"""
        # 작업 결과 시뮬레이션
        mock_result = {
            "file_id": "test-file-id",
            "file_name": "sample.pdf",
            "text": "Sample PDF for Testing\n일본어 샘플 텍스트: これはテストです\n한국어 샘플 텍스트: 테스트입니다",
            "language": "jpn",
            "confidence": 0.95,
            "pages": [
                {
                    "page_num": 1,
                    "text": "Sample PDF for Testing\n일본어 샘플 텍스트: これはテストです\n한국어 샘플 텍스트: 테스트입니다",
                    "language": "jpn",
                    "confidence": 0.95
                }
            ],
            "process_time": 1.5
        }
        
        mock_job = MagicMock()
        mock_job.is_finished = True
        mock_job.is_failed = False
        mock_job.result = mock_result
        mock_job_fetch.return_value = mock_job
        
        # API 요청
        response = client.get("/api/v1/ocr/test-job-id")
        
        # 응답 검증
        assert response.status_code == 200
        assert response.json()["file_name"] == "sample.pdf"
        assert response.json()["language"] == "jpn"
        assert response.json()["confidence"] == 0.95
        assert len(response.json()["pages"]) == 1
    
    @patch('rq.job.Job.fetch')
    def test_get_ocr_result_failed(self, mock_job_fetch, mock_redis):
        """OCR 결과 조회 API 실패 테스트"""
        # 작업 실패 시뮬레이션
        mock_job = MagicMock()
        mock_job.is_finished = False
        mock_job.is_failed = True
        mock_job.exc_info = "테스트 오류 메시지"
        mock_job_fetch.return_value = mock_job
        
        # API 요청
        response = client.get("/api/v1/ocr/test-job-id")
        
        # 응답 검증
        assert response.status_code == 200
        assert response.json()["status"] == "error"
        assert response.json()["error"] == "테스트 오류 메시지"
    
    def test_fields_endpoint(self):
        """필드 설정 조회 API 테스트"""
        response = client.get("/api/v1/fields")
        
        assert response.status_code == 200
        assert "fields" in response.json()
        assert isinstance(response.json()["fields"], list)
    
    @patch('src.extraction.field_config.FieldConfig')
    def test_update_fields_endpoint(self, mock_field_config):
        """필드 설정 업데이트 API 테스트"""
        # 테스트 필드 데이터
        test_fields = [
            {
                "name": "test_field",
                "type": "text",
                "context": "테스트|test",
                "regex": "[a-z0-9]+"
            }
        ]
        
        # API 요청
        response = client.post(
            "/api/v1/fields",
            json=test_fields
        )
        
        # 응답 검증
        assert response.status_code == 200
        assert response.json()["success"] == True
        assert response.json()["count"] == 1
        
        # 필드 설정 업데이트 확인
        mock_field_config.return_value._save_fields.assert_called_once()
