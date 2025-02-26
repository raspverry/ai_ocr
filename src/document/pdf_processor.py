"""
PDF 처리 모듈
- PDF 파일을 이미지로 변환
- 페이지 방향 감지 및 보정
- 페이지 추출 및 병합
"""

import io
import os
import logging
from typing import Dict, Any, List, Optional, Union, Tuple, BinaryIO
import numpy as np
from PIL import Image
import pdf2image
import PyPDF2
import tempfile

from src.core.config import config
from src.document.orientation import detect_orientation, correct_orientation

# 로거 설정
logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF 문서 처리 클래스"""
    
    def __init__(self):
        """초기화"""
        # PDF 설정
        self.pdf_dpi = config.get('document.pdf_dpi', 300)
        self.max_pdf_pages = config.get('document.max_pdf_pages', 100)
        self.image_max_size = config.get('document.image_max_size', 4000)
        
        # PDF 변환 옵션
        self.conversion_options = {
            'dpi': self.pdf_dpi,
            'fmt': 'jpeg',
            'thread_count': 4,
            'grayscale': False,
            'use_cropbox': True,
            'strict': False
        }
    
    def convert_to_images(self, pdf_content: Union[bytes, BinaryIO], 
                         start_page: int = 1, 
                         end_page: Optional[int] = None, 
                         check_orientation: bool = True) -> List[Dict[str, Any]]:
        """
        PDF를 이미지 목록으로 변환
        
        Args:
            pdf_content: PDF 파일 내용 (바이트 또는 파일 객체)
            start_page: 시작 페이지 번호 (1부터 시작)
            end_page: 종료 페이지 번호 (None이면 마지막 페이지까지)
            check_orientation: 페이지 방향 감지 및 보정 여부
            
        Returns:
            페이지 이미지 및 메타데이터 목록
        """
        try:
            # PDF 바이트 처리
            if not isinstance(pdf_content, bytes):
                pdf_bytes = pdf_content.read()
            else:
                pdf_bytes = pdf_content
            
            # PDF 메타데이터 및 페이지 수 확인
            metadata = self._extract_pdf_metadata(pdf_bytes)
            total_pages = metadata.get('total_pages', 0)
            
            if total_pages == 0:
                logger.error("페이지가 없는 PDF입니다.")
                return []
            
            if total_pages > self.max_pdf_pages:
                logger.warning(f"PDF 페이지 수({total_pages})가 최대 허용 수({self.max_pdf_pages})를 초과합니다.")
                total_pages = self.max_pdf_pages
            
            # 시작/종료 페이지 조정
            start_page = max(1, min(start_page, total_pages))
            if end_page is None:
                end_page = total_pages
            else:
                end_page = max(start_page, min(end_page, total_pages))
            
            # PDF를 이미지로 변환
            logger.info(f"PDF를 이미지로 변환 중 (페이지 {start_page}-{end_page})...")
            
            conversion_options = self.conversion_options.copy()
            conversion_options['first_page'] = start_page
            conversion_options['last_page'] = end_page
            
            # PDF 변환 (pdf2image 라이브러리 사용)
            images = pdf2image.convert_from_bytes(
                pdf_bytes,
                **conversion_options
            )
            
            logger.info(f"PDF에서 {len(images)}개의 이미지를 생성했습니다.")
            
            # 결과 페이지 목록
            result_pages = []
            
            # 각 페이지 처리
            for i, image in enumerate(images):
                page_num = start_page + i
                
                try:
                    # 이미지 크기 제한 (메모리 사용량 제어)
                    width, height = image.size
                    max_size = self.image_max_size
                    
                    if width > max_size or height > max_size:
                        scale = min(max_size / width, max_size / height)
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        image = image.resize((new_width, new_height), Image.LANCZOS)
                        logger.debug(f"페이지 {page_num} 크기 조정: {width}x{height} -> {new_width}x{new_height}")
                    
                    # 페이지 방향 감지 및 보정
                    orientation = 0
                    if check_orientation:
                        orientation = detect_orientation(image)
                        logger.debug(f"페이지 {page_num} 방향: {orientation}도")
                        
                        if orientation != 0:
                            image = correct_orientation(image, orientation)
                    
                    # 결과에 추가
                    result_pages.append({
                        'page_num': page_num,
                        'image': image,
                        'width': image.width,
                        'height': image.height,
                        'orientation': orientation,
                        'dpi': self.pdf_dpi
                    })
                
                except Exception as e:
                    logger.error(f"페이지 {page_num} 처리 오류: {e}")
                    # 오류 발생해도 계속 진행
            
            return result_pages
        
        except Exception as e:
            logger.error(f"PDF 변환 오류: {e}")
            return []
    
    def _extract_pdf_metadata(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        PDF 메타데이터 추출
        
        Args:
            pdf_bytes: PDF 파일 내용 (바이트)
            
        Returns:
            PDF 메타데이터
        """
        try:
            metadata = {}
            
            # PDF 읽기
            with io.BytesIO(pdf_bytes) as pdf_stream:
                pdf_reader = PyPDF2.PdfReader(pdf_stream)
                
                # 페이지 수
                metadata['total_pages'] = len(pdf_reader.pages)
                
                # 기본 메타데이터
                info = pdf_reader.metadata
                if info:
                    for key in info:
                        # 키가 /로 시작하면 제거
                        clean_key = key[1:] if key.startswith('/') else key
                        metadata[clean_key] = info[key]
                
                # 페이지 크기
                page_sizes = []
                for i, page in enumerate(pdf_reader.pages):
                    if i >= 10:  # 최대 10개 페이지만 확인
                        break
                    
                    if page.mediabox:
                        width = float(page.mediabox.width)
                        height = float(page.mediabox.height)
                        page_sizes.append({'width': width, 'height': height})
                
                if page_sizes:
                    metadata['page_sizes'] = page_sizes
                
                # 암호화 여부
                metadata['is_encrypted'] = pdf_reader.is_encrypted
            
            return metadata
        
        except Exception as e:
            logger.error(f"PDF 메타데이터 추출 오류: {e}")
            return {'total_pages': 0, 'error': str(e)}
    
    def extract_text_with_pdfminer(self, pdf_bytes: bytes) -> List[str]:
        """
        PDFMiner를 사용한 PDF 텍스트 추출 (레이아웃 보존)
        
        Args:
            pdf_bytes: PDF 파일 내용 (바이트)
            
        Returns:
            페이지별 텍스트 목록
        """
        try:
            # PDFMiner는 필요할 때 임포트
            from pdfminer.high_level import extract_pages
            from pdfminer.layout import LTTextContainer
            import io
            
            result_pages = []
            
            # PDF 읽기
            with io.BytesIO(pdf_bytes) as pdf_stream:
                # 각 페이지 처리
                for page_layout in extract_pages(pdf_stream):
                    page_text = []
                    
                    # 텍스트 컨테이너 추출
                    for element in page_layout:
                        if isinstance(element, LTTextContainer):
                            page_text.append(element.get_text())
                    
                    # 페이지 텍스트 병합
                    result_pages.append("".join(page_text))
            
            return result_pages
        
        except ImportError:
            logger.error("PDFMiner 라이브러리가 설치되지 않았습니다.")
            return []
        
        except Exception as e:
            logger.error(f"PDFMiner 텍스트 추출 오류: {e}")
            return []
    
    def merge_pdfs(self, pdf_list: List[bytes], output_path: str) -> bool:
        """
        여러 PDF 파일 병합
        
        Args:
            pdf_list: PDF 파일 목록 (바이트)
            output_path: 출력 파일 경로
            
        Returns:
            성공 여부
        """
        try:
            merger = PyPDF2.PdfMerger()
            
            # 각 PDF 추가
            for pdf_bytes in pdf_list:
                with io.BytesIO(pdf_bytes) as pdf_stream:
                    merger.append(pdf_stream)
            
            # 병합 PDF 저장
            with open(output_path, 'wb') as f:
                merger.write(f)
            
            merger.close()
            logger.info(f"{len(pdf_list)}개의 PDF를 병합했습니다: {output_path}")
            
            return True
        
        except Exception as e:
            logger.error(f"PDF 병합 오류: {e}")
            return False
    
    def split_pdf(self, pdf_bytes: bytes, output_dir: str) -> List[str]:
        """
        PDF 파일을 페이지별로 분할
        
        Args:
            pdf_bytes: PDF 파일 내용 (바이트)
            output_dir: 출력 디렉토리 경로
            
        Returns:
            생성된 PDF 파일 경로 목록
        """
        try:
            # 출력 디렉토리 생성
            os.makedirs(output_dir, exist_ok=True)
            
            # PDF 읽기
            with io.BytesIO(pdf_bytes) as pdf_stream:
                pdf_reader = PyPDF2.PdfReader(pdf_stream)
                total_pages = len(pdf_reader.pages)
                
                output_files = []
                
                # 각 페이지를 개별 PDF로 저장
                for page_num in range(total_pages):
                    output_path = os.path.join(output_dir, f"page_{page_num+1}.pdf")
                    
                    # 새 PDF 생성
                    pdf_writer = PyPDF2.PdfWriter()
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                    
                    # 저장
                    with open(output_path, 'wb') as f:
                        pdf_writer.write(f)
                    
                    output_files.append(output_path)
            
            logger.info(f"PDF를 {len(output_files)}개의 페이지로 분할했습니다.")
            return output_files
        
        except Exception as e:
            logger.error(f"PDF 분할 오류: {e}")
            return []
    
    def add_pages_to_pdf(self, base_pdf_bytes: bytes, images: List[Image.Image], output_path: str) -> bool:
        """
        기존 PDF에 이미지 페이지 추가
        
        Args:
            base_pdf_bytes: 기본 PDF 파일 내용 (바이트)
            images: 추가할 이미지 목록
            output_path: 출력 파일 경로
            
        Returns:
            성공 여부
        """
        try:
            # 이미지를 임시 PDF로 변환
            temp_pdf_paths = []
            
            for i, image in enumerate(images):
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    temp_path = tmp.name
                    temp_pdf_paths.append(temp_path)
                    
                    # 이미지를 PDF로 저장
                    image.convert('RGB').save(temp_path, 'PDF')
            
            # 기본 PDF 읽기
            with io.BytesIO(base_pdf_bytes) as pdf_stream:
                pdf_reader = PyPDF2.PdfReader(pdf_stream)
                pdf_writer = PyPDF2.PdfWriter()
                
                # 기존 페이지 복사
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
                
                # 이미지 PDF 페이지 추가
                for temp_path in temp_pdf_paths:
                    with open(temp_path, 'rb') as f:
                        img_pdf = PyPDF2.PdfReader(f)
                        pdf_writer.add_page(img_pdf.pages[0])
                
                # 결과 PDF 저장
                with open(output_path, 'wb') as f:
                    pdf_writer.write(f)
            
            # 임시 파일 정리
            for temp_path in temp_pdf_paths:
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            logger.info(f"PDF에 {len(images)}개의 이미지 페이지를 추가했습니다: {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"PDF 페이지 추가 오류: {e}")
            
            # 임시 파일 정리
            for temp_path in temp_pdf_paths:
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            return False
