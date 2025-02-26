#!/usr/bin/env python3
"""
OCR 모델 다운로드 스크립트
- 필요한 모델 파일 다운로드 및 설치
- 모델 디렉토리 구조 생성
"""

import os
import sys
import logging
import argparse
import requests
import zipfile
import gzip
import tarfile
import shutil
from pathlib import Path
from huggingface_hub import snapshot_download

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("model_downloader")

# 모델 기본 디렉토리
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

# 모델 URL 정의
MODEL_URLS = {
    # TrOCR 모델 (HuggingFace에서 자동 다운로드)
    "trocr_japanese": "microsoft/trocr-base-japanese",
    "trocr_printed": "microsoft/trocr-base-printed",
    
    # Tesseract 학습 데이터 (직접 다운로드, 필요한 경우에만)
    "tessdata_best_jpn": "https://github.com/tesseract-ocr/tessdata_best/raw/main/jpn.traineddata",
    "tessdata_best_kor": "https://github.com/tesseract-ocr/tessdata_best/raw/main/kor.traineddata",
    "tessdata_best_eng": "https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata",
    "tessdata_best_chi_sim": "https://github.com/tesseract-ocr/tessdata_best/raw/main/chi_sim.traineddata",
    "tessdata_best_chi_tra": "https://github.com/tesseract-ocr/tessdata_best/raw/main/chi_tra.traineddata",
}

def download_file(url, dest_path):
    """
    파일 다운로드
    
    Args:
        url: 다운로드 URL
        dest_path: 저장 경로
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"다운로드 완료: {url} -> {dest_path}")
        return True
    
    except Exception as e:
        logger.error(f"다운로드 오류 ({url}): {e}")
        return False

def download_huggingface_model(model_id, save_dir):
    """
    HuggingFace 모델 다운로드
    
    Args:
        model_id: 모델 ID
        save_dir: 저장 디렉토리
    """
    try:
        logger.info(f"HuggingFace 모델 다운로드 중: {model_id}")
        local_dir = snapshot_download(
            repo_id=model_id,
            local_dir=save_dir,
            local_dir_use_symlinks=False
        )
        logger.info(f"모델 다운로드 완료: {model_id} -> {local_dir}")
        return True
    
    except Exception as e:
        logger.error(f"HuggingFace 모델 다운로드 오류 ({model_id}): {e}")
        return False

def extract_archive(archive_path, extract_dir):
    """
    압축 파일 추출
    
    Args:
        archive_path: 압축 파일 경로
        extract_dir: 추출 디렉토리
    """
    try:
        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
        
        elif archive_path.endswith('.tar.gz') or archive_path.endswith('.tgz'):
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(extract_dir)
        
        elif archive_path.endswith('.gz'):
            output_path = os.path.splitext(archive_path)[0]
            with gzip.open(archive_path, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        
        else:
            logger.warning(f"지원하지 않는 압축 형식: {archive_path}")
            return False
        
        logger.info(f"압축 해제 완료: {archive_path} -> {extract_dir}")
        return True
    
    except Exception as e:
        logger.error(f"압축 해제 오류 ({archive_path}): {e}")
        return False

def download_tessdata():
    """Tesseract 학습 데이터 다운로드"""
    tessdata_dir = os.path.join(MODEL_DIR, "tessdata")
    os.makedirs(tessdata_dir, exist_ok=True)
    
    # 언어별 학습 데이터 다운로드
    languages = ["jpn", "kor", "eng", "chi_sim", "chi_tra"]
    success_count = 0
    
    for lang in languages:
        url_key = f"tessdata_best_{lang}"
        if url_key in MODEL_URLS:
            dest_path = os.path.join(tessdata_dir, f"{lang}.traineddata")
            
            # 이미 있으면 건너뛰기
            if os.path.exists(dest_path):
                logger.info(f"테서랙트 데이터 이미 존재: {dest_path}")
                success_count += 1
                continue
            
            # 다운로드
            if download_file(MODEL_URLS[url_key], dest_path):
                success_count += 1
    
    logger.info(f"테서랙트 데이터 다운로드 완료: {success_count}/{len(languages)} 언어")

def download_trocr_models():
    """TrOCR 모델 다운로드"""
    # 모델 디렉토리 생성
    trocr_dir = os.path.join(MODEL_DIR, "trocr")
    os.makedirs(trocr_dir, exist_ok=True)
    
    # 일본어 모델
    jpn_dir = os.path.join(trocr_dir, "japanese")
    if not os.path.exists(jpn_dir) or not os.listdir(jpn_dir):
        download_huggingface_model(MODEL_URLS["trocr_japanese"], jpn_dir)
    else:
        logger.info(f"TrOCR 일본어 모델 이미 존재: {jpn_dir}")
    
    # 영어 모델
    eng_dir = os.path.join(trocr_dir, "printed")
    if not os.path.exists(eng_dir) or not os.listdir(eng_dir):
        download_huggingface_model(MODEL_URLS["trocr_printed"], eng_dir)
    else:
        logger.info(f"TrOCR 영어 모델 이미 존재: {eng_dir}")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="OCR 모델 다운로드 스크립트")
    parser.add_argument("--model-dir", default=MODEL_DIR, help="모델 디렉토리 경로")
    parser.add_argument("--force", action="store_true", help="기존 모델 덮어쓰기")
    parser.add_argument("--trocr-only", action="store_true", help="TrOCR 모델만 다운로드")
    parser.add_argument("--tessdata-only", action="store_true", help="Tesseract 데이터만 다운로드")
    
    args = parser.parse_args()
    
    # 모델 디렉토리 설정
    global MODEL_DIR
    MODEL_DIR = args.model_dir
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    logger.info(f"모델 다운로드 시작 (대상 디렉토리: {MODEL_DIR})")
    
    # 강제 덮어쓰기 옵션
    if args.force:
        logger.warning("강제 덮어쓰기 모드 활성화: 기존 모델을 덮어씁니다")
    
    # TrOCR 모델 다운로드
    if not args.tessdata_only:
        download_trocr_models()
    
    # Tesseract 학습 데이터 다운로드
    if not args.trocr_only:
        download_tessdata()
    
    logger.info("모델 다운로드 완료")
    return 0

if __name__ == "__main__":
    sys.exit(main())
