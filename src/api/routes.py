"""
API 라우트 모듈
- OCR 처리 API 엔드포인트
- 데이터 추출 API 엔드포인트
- 작업 상태 조회 API 엔드포인트
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import json
import rq
from rq.job import Job
import redis

from src.core.config import config
from src.api.models import OCRRequest, OCRResponse, OCRResult, ExtractionRequest, ExtractionResult
from src.worker.tasks import process_document, extract_data_from_document

# 로거 설정
logger = logging.getLogger(__name__)

# Redis 연결
try:
    redis_conn = redis.Redis.from_url(config.get('queue.redis_url', 'redis://localhost:6379/0'))
    queue = rq.Queue(config.get('queue.queue_name', 'ocr_tasks'), connection=redis_conn)
    logger.info("Redis 작업 큐 초기화 성공")
except Exception as e:
    logger.error(f"Redis 작업 큐 초기화 오류: {e}")
    redis_conn = None
    queue = None

# 라우터 생성
router = APIRouter(prefix="/api/v1")


# OCR 처리 API
@router.post("/ocr", response_model=OCRResponse)
async def ocr_document(
    file: UploadFile = File(...),
    options: str = Form("{}")
):
    """
    문서에서 텍스트 추출 API
    
    Args:
        file: PDF 또는 이미지 파일
        options: JSON 문자열 (OCRRequest 모델)
    
    Returns:
        작업 ID 및 상태
    """
    try:
        # 작업 큐 확인
        if queue is None:
            raise HTTPException(status_code=503, detail="작업 큐를 사용할 수 없습니다.")
        
        # 파일 확장자 확인
        file_ext = os.path.splitext(file.filename)[1].lower()
        supported_types = [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif"]
        
        if file_ext not in supported_types:
            raise HTTPException(
                status_code=400, 
                detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(supported_types)}"
            )
        
        # 옵션 파싱
        try:
            options_dict = json.loads(options)
        except json.JSONDecodeError:
            options_dict = {}
        
        # 파일 내용 읽기
        file_bytes = await file.read()
        
        # 작업 큐에 추가
        job = queue.enqueue(
            process_document,
            args=(file_bytes, file.filename, options_dict),
            job_timeout=config.get('queue.timeout', 3600)  # 기본 1시간 타임아웃
        )
        
        logger.info(f"OCR 작업 큐에 추가: {job.id}, 파일: {file.filename}")
        
        return {
            "task_id": job.id,
            "status": "processing"
        }
    
    except HTTPException as e:
        # HTTP 예외는 그대로 전달
        raise
    
    except Exception as e:
        logger.error(f"OCR 요청 처리 오류: {e}")
        raise HTTPException(status_code=500, detail=f"OCR 요청 처리 오류: {str(e)}")


@router.get("/ocr/{task_id}", response_model=Union[OCRResult, OCRResponse])
async def get_ocr_result(task_id: str):
    """
    OCR 작업 결과 조회 API
    
    Args:
        task_id: 작업 ID
    
    Returns:
        OCR 처리 결과 또는 상태
    """
    try:
        # Redis 연결 확인
        if redis_conn is None:
            raise HTTPException(status_code=503, detail="Redis 연결을 사용할 수 없습니다.")
        
        # 작업 가져오기
        try:
            job = Job.fetch(task_id, connection=redis_conn)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"작업을 찾을 수 없습니다: {task_id}")
        
        # 작업 상태 확인
        if job.is_finished:
            return job.result
        elif job.is_failed:
            return {
                "status": "error",
                "error": str(job.exc_info)
            }
        else:
            return {
                "status": "processing",
                "task_id": task_id
            }
    
    except HTTPException as e:
        # HTTP 예외는 그대로 전달
        raise
    
    except Exception as e:
        logger.error(f"결과 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"결과 조회 오류: {str(e)}")


@router.post("/extraction/{task_id}", response_model=OCRResponse)
async def extract_data(
    task_id: str,
    options: str = Form("{}")
):
    """
    OCR 결과에서 데이터 추출 API
    
    Args:
        task_id: OCR 작업 ID
        options: JSON 문자열 (ExtractionRequest 모델)
    
    Returns:
        추출 작업 ID 및 상태
    """
    try:
        # 작업 큐 확인
        if queue is None:
            raise HTTPException(status_code=503, detail="작업 큐를 사용할 수 없습니다.")
        
        # Redis 연결 확인
        if redis_conn is None:
            raise HTTPException(status_code=503, detail="Redis 연결을 사용할 수 없습니다.")
        
        # OCR 작업 확인
        try:
            ocr_job = Job.fetch(task_id, connection=redis_conn)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"OCR 작업을 찾을 수 없습니다: {task_id}")
        
        # OCR 작업 완료 확인
        if not ocr_job.is_finished:
            raise HTTPException(status_code=400, detail="OCR 작업이 아직 완료되지 않았습니다.")
        
        # 옵션 파싱
        try:
            options_dict = json.loads(options)
        except json.JSONDecodeError:
            options_dict = {}
        
        # 추출 작업 큐에 추가
        extraction_job = queue.enqueue(
            extract_data_from_document,
            args=(task_id, options_dict),
            job_timeout=config.get('queue.timeout', 3600)  # 기본 1시간 타임아웃
        )
        
        logger.info(f"데이터 추출 작업 큐에 추가: {extraction_job.id}, OCR 작업: {task_id}")
        
        return {
            "task_id": extraction_job.id,
            "status": "processing"
        }
    
    except HTTPException as e:
        # HTTP 예외는 그대로 전달
        raise
    
    except Exception as e:
        logger.error(f"데이터 추출 요청 오류: {e}")
        raise HTTPException(status_code=500, detail=f"데이터 추출 요청 오류: {str(e)}")


@router.get("/extraction/{task_id}", response_model=Union[ExtractionResult, OCRResponse])
async def get_extraction_result(task_id: str):
    """
    데이터 추출 작업 결과 조회 API
    
    Args:
        task_id: 작업 ID
    
    Returns:
        추출 결과 또는 상태
    """
    try:
        # Redis 연결 확인
        if redis_conn is None:
            raise HTTPException(status_code=503, detail="Redis 연결을 사용할 수 없습니다.")
        
        # 작업 가져오기
        try:
            job = Job.fetch(task_id, connection=redis_conn)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"작업을 찾을 수 없습니다: {task_id}")
        
        # 작업 상태 확인
        if job.is_finished:
            return job.result
        elif job.is_failed:
            return {
                "status": "error",
                "error": str(job.exc_info)
            }
        else:
            return {
                "status": "processing",
                "task_id": task_id
            }
    
    except HTTPException as e:
        # HTTP 예외는 그대로 전달
        raise
    
    except Exception as e:
        logger.error(f"추출 결과 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"추출 결과 조회 오류: {str(e)}")


@router.get("/extraction/{task_id}/csv")
async def get_extraction_csv(task_id: str):
    """
    데이터 추출 결과를 CSV로 내보내기
    
    Args:
        task_id: 작업 ID
    
    Returns:
        CSV 파일 다운로드
    """
    try:
        # Redis 연결 확인
        if redis_conn is None:
            raise HTTPException(status_code=503, detail="Redis 연결을 사용할 수 없습니다.")
        
        # 작업 가져오기
        try:
            job = Job.fetch(task_id, connection=redis_conn)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"작업을 찾을 수 없습니다: {task_id}")
        
        # 작업 완료 확인
        if not job.is_finished:
            raise HTTPException(status_code=400, detail="추출 작업이 아직 완료되지 않았습니다.")
        
        # 결과 가져오기
        result = job.result
        
        # 필드 데이터 확인
        if not result or 'fields' not in result:
            raise HTTPException(status_code=404, detail="추출된 필드 데이터가 없습니다.")
        
        # CSV 생성
        from src.extraction.csv_exporter import CSVExporter
        
        exporter = CSVExporter()
        csv_data = exporter.export_single(result['fields'])
        
        # CSV 파일 다운로드 응답
        return StreamingResponse(
            iter([csv_data.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment;filename=extraction_{task_id}.csv"
            }
        )
    
    except HTTPException as e:
        # HTTP 예외는 그대로 전달
        raise
    
    except Exception as e:
        logger.error(f"CSV 내보내기 오류: {e}")
        raise HTTPException(status_code=500, detail=f"CSV 내보내기 오류: {str(e)}")


@router.get("/fields")
async def get_extraction_fields():
    """
    추출 필드 설정 조회 API
    
    Returns:
        필드 설정 목록
    """
    try:
        from src.extraction.field_config import FieldConfig
        
        field_config = FieldConfig()
        fields = field_config.get_fields()
        
        return {"fields": fields}
    
    except Exception as e:
        logger.error(f"필드 설정 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"필드 설정 조회 오류: {str(e)}")


@router.post("/fields")
async def update_extraction_fields(fields: List[Dict[str, Any]]):
    """
    추출 필드 설정 업데이트 API
    
    Args:
        fields: 새 필드 설정 목록
    
    Returns:
        성공 여부
    """
    try:
        from src.extraction.field_config import FieldConfig
        
        field_config = FieldConfig()
        
        # 모든 필드 확인
        for field in fields:
            if 'name' not in field:
                raise HTTPException(status_code=400, detail="모든 필드에 'name' 키가 필요합니다.")
        
        # 필드 업데이트
        field_config.fields = fields
        field_config._save_fields()
        
        logger.info(f"필드 설정 업데이트: {len(fields)}개의 필드")
        
        return {"success": True, "count": len(fields)}
    
    except HTTPException as e:
        # HTTP 예외는 그대로 전달
        raise
    
    except Exception as e:
        logger.error(f"필드 설정 업데이트 오류: {e}")
        raise HTTPException(status_code=500, detail=f"필드 설정 업데이트 오류: {str(e)}")


@router.get("/languages")
async def get_supported_languages():
    """
    지원 언어 목록 조회 API
    
    Returns:
        지원 언어 목록
    """
    return {
        "languages": config.get('ocr.supported_languages', {
            "jpn": "일본어",
            "eng": "영어",
            "kor": "한국어",
            "chi_sim": "중국어 간체",
            "chi_tra": "중국어 번체"
        })
    }


@router.get("/health")
async def health_check():
    """
    서비스 상태 확인 API
    
    Returns:
        서비스 상태 정보
    """
    try:
        # Redis 연결 확인
        redis_status = False
        if redis_conn is not None:
            try:
                redis_status = redis_conn.ping()
            except:
                pass
        
        # 엔진 설정 가져오기
        engines = {
            "custom_model": config.get('ocr.use_custom_model', True),
            "tesseract": config.get('ocr.use_tesseract', True),
            "google_vision": config.get('ocr.use_google_vision', False),
            "azure_form": config.get('ocr.use_azure_form', False)
        }
        
        return {
            "status": "ok",
            "version": "1.0.0",
            "timestamp": time.time(),
            "redis": "ok" if redis_status else "error",
            "engines": engines
        }
    
    except Exception as e:
        logger.error(f"상태 확인 오류: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
