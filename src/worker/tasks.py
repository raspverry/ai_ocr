"""
백그라운드 작업 정의 모듈
- OCR 처리 작업
- 데이터 추출 작업
- 문서 변환 작업
"""

import io
import os
import json
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from PIL import Image
import redis

from src.core.config import config
from src.document.pdf_processor import PDFProcessor
from src.ocr.ensemble import OCREngine
from src.ocr.preprocessor import Preprocessor, DocumentPreprocessor
from src.ocr.postprocessor import PostProcessor
from src.extraction.llm_processor import LLMProcessor
from src.extraction.csv_exporter import CSVExporter
from src.storage.manager import StorageManager

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis 연결
try:
    redis_conn = redis.Redis.from_url(config.get('queue.redis_url', 'redis://localhost:6379/0'))
    logger.info("Redis 연결 성공")
except Exception as e:
    logger.error(f"Redis 연결 오류: {e}")
    redis_conn = None


async def process_document_async(file_bytes: bytes, 
                                file_name: str, 
                                options: Dict[str, Any]) -> Dict[str, Any]:
    """
    문서 처리 작업 (비동기 버전)
    
    Args:
        file_bytes: 파일 바이트
        file_name: 파일 이름
        options: 처리 옵션
    
    Returns:
        처리 결과
    """
    start_time = time.time()
    
    try:
        # 옵션 확인
        language = options.get('language')
        use_cache = options.get('use_cache', True)
        extract_entities = options.get('extract_entities', True)
        return_images = options.get('return_images', False)
        check_orientation = options.get('check_orientation', True)
        
        # 파일 확장자 확인
        file_ext = os.path.splitext(file_name)[1].lower()
        
        # 필요한 컴포넌트 초기화
        pdf_processor = PDFProcessor()
        ocr_engine = OCREngine()
        doc_preprocessor = DocumentPreprocessor()
        post_processor = PostProcessor()
        storage_manager = StorageManager()
        
        # 파일 저장
        file_path = await storage_manager.save_file(file_bytes, file_name)
        
        # 처리 결과
        result = {
            "file_id": file_path.split("/")[0],
            "file_name": file_name,
            "file_type": file_ext,
            "process_time": time.time(),
            "pages": []
        }
        
        # PDF 처리
        if file_ext == ".pdf":
            logger.info(f"PDF 문서 처리 시작: {file_name}")
            
            # PDF를 이미지로 변환 및 방향 보정
            page_results = pdf_processor.convert_to_images(
                file_bytes, 
                check_orientation=check_orientation
            )
            
            if not page_results:
                raise ValueError("PDF 변환 실패")
            
            # 각 페이지 처리
            for page_result in page_results:
                page_num = page_result['page_num']
                image = page_result['image']
                orientation = page_result['orientation']
                
                logger.info(f"PDF 페이지 {page_num}/{len(page_results)} 처리 중")
                
                # 이미지 전처리
                doc_info = doc_preprocessor.process_document(image, language)
                processed_image = doc_info['processed_image']
                
                # OCR 텍스트 인식
                ocr_result = await ocr_engine.recognize_text(processed_image, language, use_cache)
                
                # 후처리
                processed_result = post_processor.process(ocr_result)
                
                # 언어 정보 (자동 감지된 경우)
                if language is None and 'language' in processed_result:
                    language = processed_result['language']
                
                # 페이지 결과 저장
                page_info = {
                    "page_num": page_num,
                    "text": processed_result["text"],
                    "language": processed_result["language"],
                    "confidence": processed_result["confidence"],
                    "orientation": orientation
                }
                
                # 문서 분석 정보 포함
                if doc_info['has_special_items']:
                    page_info["special_items"] = {
                        "has_stamps": doc_info['has_stamps'],
                        "has_handwriting": doc_info['has_handwriting'],
                        "has_table": doc_info['has_table'],
                        "has_strikethrough": doc_info['has_strikethrough'],
                        "regions": doc_info['regions']
                    }
                
                # 엔티티 추출 (요청된 경우)
                if extract_entities:
                    entities = post_processor.extract_business_entities(
                        processed_result["text"], 
                        processed_result["language"]
                    )
                    if entities:
                        page_info["entities"] = entities
                
                # 이미지 데이터 포함 (요청된 경우)
                if return_images:
                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG", quality=80)
                    page_info["image_data"] = buffer.getvalue()
                
                # 디버깅용 엔진별 결과 포함
                if config.get('app.debug', False) and "engine_results" in processed_result:
                    page_info["engine_results"] = processed_result["engine_results"]
                
                result["pages"].append(page_info)
            
        # 이미지 파일 처리
        elif file_ext in [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif"]:
            logger.info(f"이미지 문서 처리 시작: {file_name}")
            
            # 이미지 불러오기
            image = Image.open(io.BytesIO(file_bytes))
            
            # 문서 전처리
            doc_info = doc_preprocessor.process_document(image, language)
            processed_image = doc_info['processed_image']
            
            # OCR 텍스트 인식
            ocr_result = await ocr_engine.recognize_text(processed_image, language, use_cache)
            
            # 후처리
            processed_result = post_processor.process(ocr_result)
            
            # 언어 정보 (자동 감지된 경우)
            if language is None and 'language' in processed_result:
                language = processed_result['language']
            
            # 결과 저장
            page_info = {
                "page_num": 1,
                "text": processed_result["text"],
                "language": processed_result["language"],
                "confidence": processed_result["confidence"],
                "orientation": 0  # 기본값
            }
            
            # 문서 분석 정보 포함
            if doc_info['has_stamps'] or doc_info['has_handwriting'] or doc_info['has_table'] or doc_info['has_strikethrough']:
                page_info["special_items"] = {
                    "has_stamps": doc_info['has_stamps'],
                    "has_handwriting": doc_info['has_handwriting'],
                    "has_table": doc_info['has_table'],
                    "has_strikethrough": doc_info['has_strikethrough'],
                    "regions": doc_info['regions']
                }
            
            # 엔티티 추출 (요청된 경우)
            if extract_entities:
                entities = post_processor.extract_business_entities(
                    processed_result["text"], 
                    processed_result["language"]
                )
                if entities:
                    page_info["entities"] = entities
            
            # 이미지 데이터 포함 (요청된 경우)
            if return_images:
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=80)
                page_info["image_data"] = buffer.getvalue()
            
            # 디버깅용 엔진별 결과 포함
            if config.get('app.debug', False) and "engine_results" in processed_result:
                page_info["engine_results"] = processed_result["engine_results"]
            
            result["pages"].append(page_info)
        
        else:
            raise ValueError(f"지원하지 않는 파일 형식: {file_ext}")
        
        # 결과 정리
        if result["pages"]:
            # 전체 텍스트 및 신뢰도 계산
            all_text = "\n\n".join([page["text"] for page in result["pages"]])
            avg_confidence = sum([page["confidence"] for page in result["pages"]]) / len(result["pages"])
            
            result["text"] = all_text
            result["confidence"] = avg_confidence
            result["language"] = result["pages"][0]["language"]
            
            # 문서 전체 엔티티 추출
            if extract_entities:
                all_entities = {}
                
                for page in result["pages"]:
                    if "entities" in page:
                        for entity_type, entities in page["entities"].items():
                            if entity_type not in all_entities:
                                all_entities[entity_type] = []
                            all_entities[entity_type].extend(entities)
                
                # 중복 제거
                for entity_type in all_entities:
                    all_entities[entity_type] = list(set(all_entities[entity_type]))
                
                result["entities"] = all_entities
        
        # 처리 시간 업데이트
        result["process_time"] = time.time() - start_time
        
        return result
    
    except Exception as e:
        logger.error(f"문서 처리 오류: {e}", exc_info=True)
        return {
            "error": str(e),
            "file_name": file_name,
            "process_time": time.time() - start_time
        }


def process_document(file_bytes: bytes, 
                    file_name: str, 
                    options: Dict[str, Any]) -> Dict[str, Any]:
    """
    문서 처리 작업 (동기 래퍼)
    
    Args:
        file_bytes: 파일 바이트
        file_name: 파일 이름
        options: 처리 옵션
    
    Returns:
        처리 결과
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(process_document_async(file_bytes, file_name, options))
        return result
    finally:
        loop.close()


async def extract_data_from_document_async(ocr_task_id: str, 
                                         options: Dict[str, Any]) -> Dict[str, Any]:
    """
    OCR 결과에서 구조화된 데이터 추출 (비동기 버전)
    
    Args:
        ocr_task_id: OCR 작업 ID
        options: 추출 옵션
    
    Returns:
        추출 결과
    """
    start_time = time.time()
    
    try:
        # Redis 연결 확인
        if redis_conn is None:
            raise ValueError("Redis 연결을 사용할 수 없습니다.")
        
        # 작업 조회
        from rq.job import Job
        
        try:
            ocr_job = Job.fetch(ocr_task_id, connection=redis_conn)
        except Exception as e:
            raise ValueError(f"OCR 작업을 찾을 수 없습니다: {ocr_task_id}")
        
        # OCR 작업 완료 확인
        if not ocr_job.is_finished:
            raise ValueError("OCR 작업이 아직 완료되지 않았습니다.")
        
        # OCR 결과 가져오기
        ocr_result = ocr_job.result
        
        if not ocr_result or "text" not in ocr_result:
            raise ValueError("유효한 OCR 결과가 없습니다.")
        
        # 추출 옵션
        language = options.get('language') or ocr_result.get('language')
        fields = options.get('fields')
        
        # LLM 프로세서 초기화
        llm_processor = LLMProcessor()
        
        # LLM으로 데이터 추출
        extraction_result = llm_processor.extract_fields(ocr_result["text"], fields, language)
        
        # 결과 구성
        result = {
            "ocr_task_id": ocr_task_id,
            "fields": extraction_result.get("fields", {}),
            "language": language,
            "process_time": time.time() - start_time
        }
        
        # 디버그 모드인 경우 원본 응답 포함
        if config.get('app.debug', False) and "raw_response" in extraction_result:
            result["raw_response"] = extraction_result["raw_response"]
        
        return result
    
    except Exception as e:
        logger.error(f"데이터 추출 오류: {e}", exc_info=True)
        return {
            "error": str(e),
            "ocr_task_id": ocr_task_id,
            "process_time": time.time() - start_time
        }


def extract_data_from_document(ocr_task_id: str, 
                              options: Dict[str, Any]) -> Dict[str, Any]:
    """
    OCR 결과에서 구조화된 데이터 추출 (동기 래퍼)
    
    Args:
        ocr_task_id: OCR 작업 ID
        options: 추출 옵션
    
    Returns:
        추출 결과
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(extract_data_from_document_async(ocr_task_id, options))
        return result
    finally:
        loop.close()


async def generate_pdf_report_async(ocr_task_id: str, 
                                   extraction_task_id: Optional[str] = None) -> Dict[str, Any]:
    """
    OCR 및 추출 결과로 PDF 보고서 생성 (비동기 버전)
    
    Args:
        ocr_task_id: OCR 작업 ID
        extraction_task_id: 추출 작업 ID (선택 사항)
    
    Returns:
        보고서 생성 결과
    """
    start_time = time.time()
    
    try:
        # Redis 연결 확인
        if redis_conn is None:
            raise ValueError("Redis 연결을 사용할 수 없습니다.")
        
        # OCR 작업 조회
        from rq.job import Job
        
        try:
            ocr_job = Job.fetch(ocr_task_id, connection=redis_conn)
        except Exception as e:
            raise ValueError(f"OCR 작업을 찾을 수 없습니다: {ocr_task_id}")
        
        # OCR 작업 완료 확인
        if not ocr_job.is_finished:
            raise ValueError("OCR 작업이 아직 완료되지 않았습니다.")
        
        # OCR 결과 가져오기
        ocr_result = ocr_job.result
        
        # 추출 작업 결과 (있는 경우)
        extraction_result = None
        
        if extraction_task_id:
            try:
                extraction_job = Job.fetch(extraction_task_id, connection=redis_conn)
                
                if extraction_job.is_finished:
                    extraction_result = extraction_job.result
            except Exception as e:
                logger.warning(f"추출 작업 조회 오류: {e}")
        
        # TODO: PDF 보고서 생성 로직 구현
        # 실제 구현 시 reportlab, FPDF 또는 다른 PDF 생성 라이브러리 사용
        
        # 임시 결과
        result = {
            "ocr_task_id": ocr_task_id,
            "extraction_task_id": extraction_task_id,
            "report_url": None,  # 생성된 PDF URL
            "process_time": time.time() - start_time
        }
        
        return result
    
    except Exception as e:
        logger.error(f"PDF 보고서 생성 오류: {e}", exc_info=True)
        return {
            "error": str(e),
            "ocr_task_id": ocr_task_id,
            "extraction_task_id": extraction_task_id,
            "process_time": time.time() - start_time
        }


def generate_pdf_report(ocr_task_id: str, 
                       extraction_task_id: Optional[str] = None) -> Dict[str, Any]:
    """
    OCR 및 추출 결과로 PDF 보고서 생성 (동기 래퍼)
    
    Args:
        ocr_task_id: OCR 작업 ID
        extraction_task_id: 추출 작업 ID (선택 사항)
    
    Returns:
        보고서 생성 결과
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(generate_pdf_report_async(ocr_task_id, extraction_task_id))
        return result
    finally:
        loop.close()


async def export_data_to_csv_async(task_ids: List[str], 
                                 options: Dict[str, Any]) -> Dict[str, Any]:
    """
    여러 작업의 추출 데이터를 CSV로 내보내기 (비동기 버전)
    
    Args:
        task_ids: 추출 작업 ID 목록
        options: CSV 내보내기 옵션
    
    Returns:
        CSV 내보내기 결과
    """
    start_time = time.time()
    
    try:
        # Redis 연결 확인
        if redis_conn is None:
            raise ValueError("Redis 연결을 사용할 수 없습니다.")
        
        # 작업 조회
        from rq.job import Job
        
        # 추출 결과 수집
        extraction_results = []
        
        for task_id in task_ids:
            try:
                job = Job.fetch(task_id, connection=redis_conn)
                
                if job.is_finished:
                    result = job.result
                    if result and "fields" in result:
                        extraction_results.append(result)
            except Exception as e:
                logger.warning(f"작업 조회 오류 ({task_id}): {e}")
        
        if not extraction_results:
            raise ValueError("내보낼 추출 결과가 없습니다.")
        
        # CSV 내보내기 옵션
        file_path = options.get('file_path')
        additional_columns = options.get('additional_columns', {})
        
        # CSV 내보내기
        csv_exporter = CSVExporter()
        
        # 추출된 필드 데이터 추출
        fields_list = [result["fields"] for result in extraction_results]
        
        # CSV 내보내기
        if file_path:
            output_path = csv_exporter.export_multiple(fields_list, file_path, additional_columns)
            csv_data = None
        else:
            csv_data = csv_exporter.export_multiple(fields_list, additional_columns=additional_columns)
            output_path = None
        
        # 결과 반환
        result = {
            "task_ids": task_ids,
            "count": len(extraction_results),
            "file_path": output_path,
            "csv_data": csv_data.getvalue() if csv_data else None,
            "process_time": time.time() - start_time
        }
        
        return result
    
    except Exception as e:
        logger.error(f"CSV 내보내기 오류: {e}", exc_info=True)
        return {
            "error": str(e),
            "task_ids": task_ids,
            "process_time": time.time() - start_time
        }


def export_data_to_csv(task_ids: List[str], 
                      options: Dict[str, Any]) -> Dict[str, Any]:
    """
    여러 작업의 추출 데이터를 CSV로 내보내기 (동기 래퍼)
    
    Args:
        task_ids: 추출 작업 ID 목록
        options: CSV 내보내기 옵션
    
    Returns:
        CSV 내보내기 결과
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(export_data_to_csv_async(task_ids, options))
        return result
    finally:
        loop.close()
