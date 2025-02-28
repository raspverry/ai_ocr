"""
웹 라우트 정의 모듈
- 웹 UI 엔드포인트 정의
- 페이지 렌더링 및 처리
"""

import os
import logging
from typing import Dict, Any, Optional, List
import aiofiles
import json
import redis
from rq.job import Job

from fastapi import APIRouter, Request, Depends, HTTPException, File, UploadFile, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.core.config import config
from src.web.forms import UploadForm, ExtractionForm, SettingsForm, LoginForm
from src.storage.manager import StorageManager
from src.worker.tasks import process_document, extract_data_from_document, export_data_to_csv

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 설정
router = APIRouter()

# Redis 연결
try:
    redis_conn = redis.Redis.from_url(config.get('queue.redis_url', 'redis://localhost:6379/0'))
    logger.info("Redis 연결 성공")
except Exception as e:
    logger.error(f"Redis 연결 오류: {e}")
    redis_conn = None


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    홈페이지
    
    Args:
        request: FastAPI 요청 객체
        
    Returns:
        HTML 응답
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "page": "home"}
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    로그인 페이지
    
    Args:
        request: FastAPI 요청 객체
        
    Returns:
        HTML 응답
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "page": "login", "form": LoginForm()}
    )


@router.post("/login")
async def login(request: Request, form_data: LoginForm = Depends()):
    """
    로그인 처리
    
    Args:
        request: FastAPI 요청 객체
        form_data: 로그인 폼 데이터
        
    Returns:
        리다이렉트 응답
    """
    # 로그인 검증 (실제 구현에서는 데이터베이스 조회 필요)
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    
    if form_data.username == admin_username and form_data.password == admin_password:
        # 로그인 성공
        request.session["user"] = {"username": admin_username, "role": "admin"}
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # 로그인 실패
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "page": "login",
            "form": form_data,
            "error": "잘못된 사용자 이름 또는 비밀번호입니다."
        },
        status_code=status.HTTP_401_UNAUTHORIZED
    )


@router.get("/logout")
async def logout(request: Request):
    """
    로그아웃 처리
    
    Args:
        request: FastAPI 요청 객체
        
    Returns:
        리다이렉트 응답
    """
    # 세션에서 사용자 정보 제거
    if "user" in request.session:
        del request.session["user"]
    
    return RedirectResponse(url="/login")


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """
    업로드 페이지
    
    Args:
        request: FastAPI 요청 객체
        
    Returns:
        HTML 응답
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "page": "upload", "form": UploadForm()}
    )


@router.post("/upload")
async def upload(
    request: Request,
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    extract_entities: bool = Form(True)
):
    """
    파일 업로드 및 처리
    
    Args:
        request: FastAPI 요청 객체
        file: 업로드된 파일
        language: 언어 코드
        extract_entities: 엔티티 추출 여부
        
    Returns:
        리다이렉트 응답 또는 에러 페이지
    """
    # 파일 확장자 확인
    file_ext = os.path.splitext(file.filename)[1].lower()
    supported_types = [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif"]
    
    if file_ext not in supported_types:
        templates = request.app.state.templates
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "page": "upload",
                "form": UploadForm(),
                "error": f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(supported_types)}"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # 파일 내용 읽기
        file_bytes = await file.read()
        
        # 처리 옵션
        options = {
            "language": language,
            "extract_entities": extract_entities,
            "use_cache": True,
            "return_images": False
        }
        
        # 작업 큐에 추가 (Redis 필요)
        if redis_conn is None:
            raise HTTPException(status_code=503, detail="작업 큐를 사용할 수 없습니다.")
        
        # 작업 큐 생성
        queue = rq.Queue(config.get('queue.queue_name', 'ocr_tasks'), connection=redis_conn)
        
        # 작업 큐에 추가
        job = queue.enqueue(
            process_document,
            args=(file_bytes, file.filename, options),
            job_timeout=config.get('queue.timeout', 3600)  # 기본 1시간 타임아웃
        )
        
        logger.info(f"OCR 작업 큐에 추가: {job.id}, 파일: {file.filename}")
        
        # 작업 ID를 세션에 저장 (사용자별 작업 추적)
        if "tasks" not in request.session:
            request.session["tasks"] = []
        
        request.session["tasks"].append({
            "id": job.id,
            "type": "ocr",
            "filename": file.filename,
            "timestamp": time.time()
        })
        
        # 결과 페이지로 리다이렉트
        return RedirectResponse(
            url=f"/result/{job.id}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    except Exception as e:
        logger.error(f"업로드 처리 오류: {e}")
        templates = request.app.state.templates
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "page": "upload",
                "form": UploadForm(),
                "error": f"파일 처리 오류: {str(e)}"
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/result/{task_id}", response_class=HTMLResponse)
async def result_page(request: Request, task_id: str):
    """
    결과 페이지
    
    Args:
        request: FastAPI 요청 객체
        task_id: 작업 ID
        
    Returns:
        HTML 응답
    """
    templates = request.app.state.templates
    
    # Redis 확인
    if redis_conn is None:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "page": "error",
                "error": "Redis 연결을 사용할 수 없습니다."
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    try:
        # 작업 가져오기
        job = Job.fetch(task_id, connection=redis_conn)
        
        # 작업 상태 확인
        if job.is_finished:
            # 완료된 작업
            result = job.result
            return templates.TemplateResponse(
                "result.html",
                {
                    "request": request,
                    "page": "result",
                    "task_id": task_id,
                    "result": result,
                    "status": "completed"
                }
            )
        elif job.is_failed:
            # 실패한 작업
            return templates.TemplateResponse(
                "result.html",
                {
                    "request": request,
                    "page": "result",
                    "task_id": task_id,
                    "error": str(job.exc_info),
                    "status": "failed"
                }
            )
        else:
            # 진행 중인 작업
            return templates.TemplateResponse(
                "result.html",
                {
                    "request": request,
                    "page": "result",
                    "task_id": task_id,
                    "status": "processing"
                }
            )
    
    except Exception as e:
        logger.error(f"결과 페이지 오류: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "page": "error",
                "error": f"결과 조회 오류: {str(e)}"
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(
    request: Request,
    page: int = 1,
    items_per_page: int = None
):
    """
    문서 목록 페이지
    
    Args:
        request: FastAPI 요청 객체
        page: 페이지 번호
        items_per_page: 페이지당 항목 수
        
    Returns:
        HTML 응답
    """
    templates = request.app.state.templates
    
    # 페이지당 항목 수 설정
    if items_per_page is None:
        items_per_page = config.get('web.items_per_page', 20)
    
    # 사용자 작업 목록 (세션에서 가져오기)
    tasks = request.session.get("tasks", [])
    
    # 페이지네이션
    total_items = len(tasks)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    # 현재 페이지 항목
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    current_items = tasks[start_idx:end_idx]
    
    return templates.TemplateResponse(
        "documents.html",
        {
            "request": request,
            "page": "documents",
            "items": current_items,
            "current_page": page,
            "total_pages": total_pages,
            "total_items": total_items,
            "items_per_page": items_per_page
        }
    )


@router.get("/extraction/{task_id}", response_class=HTMLResponse)
async def extraction_page(request: Request, task_id: str):
    """
    데이터 추출 페이지
    
    Args:
        request: FastAPI 요청 객체
        task_id: OCR 작업 ID
        
    Returns:
        HTML 응답
    """
    templates = request.app.state.templates
    
    # Redis 확인
    if redis_conn is None:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "page": "error",
                "error": "Redis 연결을 사용할 수 없습니다."
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    try:
        # OCR 작업 가져오기
        ocr_job = Job.fetch(task_id, connection=redis_conn)
        
        # OCR 작업 완료 확인
        if not ocr_job.is_finished:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "page": "error",
                    "error": "OCR 작업이 아직 완료되지 않았습니다."
                },
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # OCR 결과
        ocr_result = ocr_job.result
        
        # 필드 설정 가져오기
        from src.extraction.field_config import FieldConfig
        field_config = FieldConfig()
        fields = field_config.get_fields()
        
        return templates.TemplateResponse(
            "extraction.html",
            {
                "request": request,
                "page": "extraction",
                "task_id": task_id,
                "ocr_result": ocr_result,
                "fields": fields,
                "form": ExtractionForm()
            }
        )
    
    except Exception as e:
        logger.error(f"추출 페이지 오류: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "page": "error",
                "error": f"추출 페이지 오류: {str(e)}"
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/extraction/{task_id}")
async def extraction_submit(
    request: Request,
    task_id: str,
    fields: str = Form(None)
):
    """
    데이터 추출 요청 처리
    
    Args:
        request: FastAPI 요청 객체
        task_id: OCR 작업 ID
        fields: 필드 설정 (JSON 문자열)
        
    Returns:
        리다이렉트 응답
    """
    # Redis 확인
    if redis_conn is None:
        raise HTTPException(status_code=503, detail="Redis 연결을 사용할 수 없습니다.")
    
    try:
        # 필드 설정 파싱
        fields_data = None
        if fields:
            try:
                fields_data = json.loads(fields)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="필드 설정이 올바른 JSON 형식이 아닙니다.")
        
        # 추출 옵션
        options = {
            "fields": fields_data
        }
        
        # 작업 큐 생성
        queue = rq.Queue(config.get('queue.queue_name', 'ocr_tasks'), connection=redis_conn)
        
        # 작업 큐에 추가
        job = queue.enqueue(
            extract_data_from_document,
            args=(task_id, options),
            job_timeout=config.get('queue.timeout', 3600)  # 기본 1시간 타임아웃
        )
        
        logger.info(f"데이터 추출 작업 큐에 추가: {job.id}, OCR 작업: {task_id}")
        
        # 작업 ID를 세션에 저장 (사용자별 작업 추적)
        if "tasks" not in request.session:
            request.session["tasks"] = []
        
        request.session["tasks"].append({
            "id": job.id,
            "type": "extraction",
            "ocr_task_id": task_id,
            "timestamp": time.time()
        })
        
        # 결과 페이지로 리다이렉트
        return RedirectResponse(
            url=f"/extraction_result/{job.id}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    except HTTPException as e:
        # HTTP 예외는 그대로 전달
        raise
    
    except Exception as e:
        logger.error(f"데이터 추출 요청 오류: {e}")
        raise HTTPException(status_code=500, detail=f"데이터 추출 요청 오류: {str(e)}")


@router.get("/extraction_result/{task_id}", response_class=HTMLResponse)
async def extraction_result_page(request: Request, task_id: str):
    """
    데이터 추출 결과 페이지
    
    Args:
        request: FastAPI 요청 객체
        task_id: 추출 작업 ID
        
    Returns:
        HTML 응답
    """
    templates = request.app.state.templates
    
    # Redis 확인
    if redis_conn is None:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "page": "error",
                "error": "Redis 연결을 사용할 수 없습니다."
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    try:
        # 작업 가져오기
        job = Job.fetch(task_id, connection=redis_conn)
        
        # 작업 상태 확인
        if job.is_finished:
            # 완료된 작업
            result = job.result
            return templates.TemplateResponse(
                "extraction_result.html",
                {
                    "request": request,
                    "page": "extraction_result",
                    "task_id": task_id,
                    "result": result,
                    "status": "completed"
                }
            )
        elif job.is_failed:
            # 실패한 작업
            return templates.TemplateResponse(
                "extraction_result.html",
                {
                    "request": request,
                    "page": "extraction_result",
                    "task_id": task_id,
                    "error": str(job.exc_info),
                    "status": "failed"
                }
            )
        else:
            # 진행 중인 작업
            return templates.TemplateResponse(
                "extraction_result.html",
                {
                    "request": request,
                    "page": "extraction_result",
                    "task_id": task_id,
                    "status": "processing"
                }
            )
    
    except Exception as e:
        logger.error(f"추출 결과 페이지 오류: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "page": "error",
                "error": f"추출 결과 조회 오류: {str(e)}"
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """
    설정 페이지
    
    Args:
        request: FastAPI 요청 객체
        
    Returns:
        HTML 응답
    """
    templates = request.app.state.templates
    
    # 현재 설정 가져오기
    from src.extraction.field_config import FieldConfig
    field_config = FieldConfig()
    fields = field_config.get_fields()
    
    # OCR 엔진 설정
    ocr_settings = {
        "use_custom_model": config.get('ocr.use_custom_model', True),
        "use_tesseract": config.get('ocr.use_tesseract', True),
        "use_google_vision": config.get('ocr.use_google_vision', False),
        "use_azure_form": config.get('ocr.use_azure_form', False),
        "confidence_threshold": config.get('ocr.confidence_threshold', 0.85),
        "detect_stamps": config.get('ocr.special_items.detect_stamps', True),
        "detect_handwriting": config.get('ocr.special_items.detect_handwriting', True),
        "detect_strikethrough": config.get('ocr.special_items.detect_strikethrough', True)
    }
    
    # 지원 언어
    supported_languages = config.get('ocr.supported_languages', {
        'jpn': '일본어',
        'eng': '영어',
        'kor': '한국어',
        'chi_sim': '중국어 간체',
        'chi_tra': '중국어 번체'
    })
    
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "page": "settings",
            "fields": fields,
            "ocr_settings": ocr_settings,
            "languages": supported_languages,
            "form": SettingsForm()
        }
    )


@router.post("/settings")
async def settings_submit(
    request: Request,
    form_data: SettingsForm = Depends()
):
    """
    설정 저장
    
    Args:
        request: FastAPI 요청 객체
        form_data: 설정 폼 데이터
        
    Returns:
        리다이렉트 응답
    """
    try:
        # 필드 설정 업데이트
        from src.extraction.field_config import FieldConfig
        field_config = FieldConfig()
        
        # 폼 데이터에서 필드 설정 파싱
        if form_data.fields:
            try:
                fields_data = json.loads(form_data.fields)
                field_config.fields = fields_data
                field_config._save_fields()
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="필드 설정이 올바른 JSON 형식이 아닙니다.")
        
        # 설정 페이지로 리다이렉트
        return RedirectResponse(
            url="/settings",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    except HTTPException as e:
        # HTTP 예외는 그대로 전달
        raise
    
    except Exception as e:
        logger.error(f"설정 저장 오류: {e}")
        raise HTTPException(status_code=500, detail=f"설정 저장 오류: {str(e)}")


@router.get("/export/{task_id}")
async def export_csv(request: Request, task_id: str):
    """
    데이터 추출 결과를 CSV로 내보내기
    
    Args:
        request: FastAPI 요청 객체
        task_id: 추출 작업 ID
        
    Returns:
        CSV 파일 다운로드
    """
    # Redis 확인
    if redis_conn is None:
        raise HTTPException(status_code=503, detail="Redis 연결을 사용할 수 없습니다.")
    
    try:
        # 작업 가져오기
        job = Job.fetch(task_id, connection=redis_conn)
        
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
        from fastapi.responses import StreamingResponse
        
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

# 상태 확인 API
@router.get("/status")
async def status():
    """
    시스템 상태 확인
    
    Returns:
        JSON 응답
    """
    from src.ocr.ensemble import OCREngine
    
    # Redis 연결 확인
    redis_status = False
    if redis_conn is not None:
        try:
            redis_status = redis_conn.ping()
        except:
            pass
    
    # OCR 엔진 확인
    ocr_engine = OCREngine()
    engine_status = {
        "custom_model": hasattr(ocr_engine, 'engines') and 'custom_model' in ocr_engine.engines,
        "tesseract": hasattr(ocr_engine, 'engines') and 'tesseract' in ocr_engine.engines,
        "google_vision": hasattr(ocr_engine, 'engines') and 'google_vision' in ocr_engine.engines,
        "azure_form": hasattr(ocr_engine, 'engines') and 'azure_form' in ocr_engine.engines
    }
    
    return {
        "status": "ok",
        "redis": redis_status,
        "ocr_engines": engine_status,
        "version": "1.0.0"
    }
