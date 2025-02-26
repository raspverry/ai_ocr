"""
파일 스토리지 관리 모듈
- 로컬 파일 시스템, S3, GCS 지원
- 파일 저장, 조회, 삭제 기능
- 임시 파일 관리
"""

import os
import io
import uuid
import logging
import tempfile
from typing import Dict, Any, List, Optional, Union, BinaryIO
from pathlib import Path

from src.core.config import config

# 로거 설정
logger = logging.getLogger(__name__)

# 선택적 라이브러리 임포트
try:
    import boto3
    from botocore.exceptions import ClientError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    logger.warning("boto3 라이브러리가 설치되지 않았습니다. S3 스토리지를 사용할 수 없습니다.")

try:
    from google.cloud import storage as gcs_storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    logger.warning("google-cloud-storage 라이브러리가 설치되지 않았습니다. GCS 스토리지를 사용할 수 없습니다.")


class StorageManager:
    """파일 스토리지 관리 클래스"""
    
    def __init__(self):
        """초기화"""
        # 스토리지 설정
        self.storage_type = config.get('storage.type', 'local').lower()
        self.local_path = config.get('storage.local_path', './storage')
        self.s3_bucket = config.get('storage.s3_bucket', 'ocr-documents')
        self.gcs_bucket = config.get('storage.gcs_bucket', 'ocr-documents')
        
        # 클라이언트 초기화
        self.s3_client = None
        self.gcs_client = None
        
        # 스토리지 초기화
        self._initialize_storage()
    
    def _initialize_storage(self):
        """스토리지 초기화"""
        # 로컬 스토리지
        if self.storage_type == 'local':
            os.makedirs(self.local_path, exist_ok=True)
            logger.info(f"로컬 스토리지 초기화 성공: {self.local_path}")
        
        # S3 스토리지
        elif self.storage_type == 's3':
            if not S3_AVAILABLE:
                logger.error("boto3 라이브러리가 설치되지 않아 S3 스토리지를 사용할 수 없습니다.")
                return
            
            try:
                self.s3_client = boto3.client('s3')
                logger.info("S3 스토리지 초기화 성공")
            except Exception as e:
                logger.error(f"S3 클라이언트 초기화 오류: {e}")
        
        # GCS 스토리지
        elif self.storage_type == 'gcs':
            if not GCS_AVAILABLE:
                logger.error("google-cloud-storage 라이브러리가 설치되지 않아 GCS 스토리지를 사용할 수 없습니다.")
                return
            
            try:
                self.gcs_client = gcs_storage.Client()
                logger.info("GCS 스토리지 초기화 성공")
            except Exception as e:
                logger.error(f"GCS 클라이언트 초기화 오류: {e}")
        
        else:
            logger.warning(f"지원하지 않는 스토리지 유형: {self.storage_type}, 로컬 스토리지로 대체합니다.")
            self.storage_type = 'local'
            os.makedirs(self.local_path, exist_ok=True)
    
    async def save_file(self, file_bytes: bytes, file_name: str) -> str:
        """
        파일 저장
        
        Args:
            file_bytes: 파일 내용
            file_name: 파일 이름
        
        Returns:
            저장 경로
        """
        try:
            # 고유 폴더 ID 생성
            folder_id = str(uuid.uuid4())
            path = f"{folder_id}/{file_name}"
            
            # 스토리지 유형에 따라 저장
            if self.storage_type == 'local':
                # 로컬 파일 시스템
                folder_path = os.path.join(self.local_path, folder_id)
                os.makedirs(folder_path, exist_ok=True)
                
                file_path = os.path.join(folder_path, file_name)
                with open(file_path, 'wb') as f:
                    f.write(file_bytes)
                
                logger.info(f"파일 저장 완료 (로컬): {file_path}")
                return path
            
            elif self.storage_type == 's3' and self.s3_client:
                # S3 버킷
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=path,
                    Body=file_bytes
                )
                
                logger.info(f"파일 저장 완료 (S3): {path}")
                return path
            
            elif self.storage_type == 'gcs' and self.gcs_client:
                # GCS 버킷
                bucket = self.gcs_client.bucket(self.gcs_bucket)
                blob = bucket.blob(path)
                blob.upload_from_string(file_bytes)
                
                logger.info(f"파일 저장 완료 (GCS): {path}")
                return path
            
            else:
                raise ValueError(f"스토리지를 사용할 수 없습니다: {self.storage_type}")
        
        except Exception as e:
            logger.error(f"파일 저장 오류: {e}")
            raise
    
    async def save_file_object(self, file_obj: BinaryIO, file_name: str) -> str:
        """
        파일 객체 저장
        
        Args:
            file_obj: 파일 객체
            file_name: 파일 이름
        
        Returns:
            저장 경로
        """
        file_bytes = file_obj.read()
        return await self.save_file(file_bytes, file_name)
    
    async def get_file(self, path: str) -> bytes:
        """
        파일 조회
        
        Args:
            path: 파일 경로
        
        Returns:
            파일 내용
        """
        try:
            # 스토리지 유형에 따라 조회
            if self.storage_type == 'local':
                # 로컬 파일 시스템
                file_path = os.path.join(self.local_path, path)
                with open(file_path, 'rb') as f:
                    return f.read()
            
            elif self.storage_type == 's3' and self.s3_client:
                # S3 버킷
                response = self.s3_client.get_object(
                    Bucket=self.s3_bucket,
                    Key=path
                )
                return response['Body'].read()
            
            elif self.storage_type == 'gcs' and self.gcs_client:
                # GCS 버킷
                bucket = self.gcs_client.bucket(self.gcs_bucket)
                blob = bucket.blob(path)
                return blob.download_as_bytes()
            
            else:
                raise ValueError(f"스토리지를 사용할 수 없습니다: {self.storage_type}")
        
        except Exception as e:
            logger.error(f"파일 조회 오류: {e}")
            raise
    
    async def get_file_stream(self, path: str) -> BinaryIO:
        """
        파일 스트림 조회
        
        Args:
            path: 파일 경로
        
        Returns:
            파일 스트림
        """
        # 파일 내용 가져오기
        content = await self.get_file(path)
        
        # 메모리 스트림 생성
        stream = io.BytesIO(content)
        stream.seek(0)
        
        return stream
    
    async def delete_file(self, path: str) -> bool:
        """
        파일 삭제
        
        Args:
            path: 파일 경로
        
        Returns:
            성공 여부
        """
        try:
            # 스토리지 유형에 따라 삭제
            if self.storage_type == 'local':
                # 로컬 파일 시스템
                file_path = os.path.join(self.local_path, path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"파일 삭제 완료 (로컬): {file_path}")
                    return True
                else:
                    logger.warning(f"파일이 존재하지 않습니다: {file_path}")
                    return False
            
            elif self.storage_type == 's3' and self.s3_client:
                # S3 버킷
                self.s3_client.delete_object(
                    Bucket=self.s3_bucket,
                    Key=path
                )
                logger.info(f"파일 삭제 완료 (S3): {path}")
                return True
            
            elif self.storage_type == 'gcs' and self.gcs_client:
                # GCS 버킷
                bucket = self.gcs_client.bucket(self.gcs_bucket)
                blob = bucket.blob(path)
                blob.delete()
                logger.info(f"파일 삭제 완료 (GCS): {path}")
                return True
            
            else:
                raise ValueError(f"스토리지를 사용할 수 없습니다: {self.storage_type}")
        
        except Exception as e:
            logger.error(f"파일 삭제 오류: {e}")
            return False
    
    async def delete_folder(self, folder_path: str) -> bool:
        """
        폴더 삭제
        
        Args:
            folder_path: 폴더 경로
        
        Returns:
            성공 여부
        """
        try:
            # 스토리지 유형에 따라 폴더 삭제
            if self.storage_type == 'local':
                # 로컬 파일 시스템
                full_path = os.path.join(self.local_path, folder_path)
                if os.path.exists(full_path) and os.path.isdir(full_path):
                    import shutil
                    shutil.rmtree(full_path)
                    logger.info(f"폴더 삭제 완료 (로컬): {full_path}")
                    return True
                else:
                    logger.warning(f"폴더가 존재하지 않습니다: {full_path}")
                    return False
            
            elif self.storage_type == 's3' and self.s3_client:
                # S3 버킷 (폴더 개념이 없으므로 접두사로 처리)
                response = self.s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix=folder_path
                )
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        self.s3_client.delete_object(
                            Bucket=self.s3_bucket,
                            Key=obj['Key']
                        )
                
                logger.info(f"폴더 삭제 완료 (S3): {folder_path}")
                return True
            
            elif self.storage_type == 'gcs' and self.gcs_client:
                # GCS 버킷 (폴더 개념이 없으므로 접두사로 처리)
                bucket = self.gcs_client.bucket(self.gcs_bucket)
                blobs = bucket.list_blobs(prefix=folder_path)
                
                for blob in blobs:
                    blob.delete()
                
                logger.info(f"폴더 삭제 완료 (GCS): {folder_path}")
                return True
            
            else:
                raise ValueError(f"스토리지를 사용할 수 없습니다: {self.storage_type}")
        
        except Exception as e:
            logger.error(f"폴더 삭제 오류: {e}")
            return False
    
    async def list_files(self, folder_path: str) -> List[str]:
        """
        폴더 내 파일 목록 조회
        
        Args:
            folder_path: 폴더 경로
        
        Returns:
            파일 경로 목록
        """
        try:
            files = []
            
            # 스토리지 유형에 따라 파일 목록 조회
            if self.storage_type == 'local':
                # 로컬 파일 시스템
                full_path = os.path.join(self.local_path, folder_path)
                if os.path.exists(full_path) and os.path.isdir(full_path):
                    for file_name in os.listdir(full_path):
                        if os.path.isfile(os.path.join(full_path, file_name)):
                            files.append(os.path.join(folder_path, file_name))
            
            elif self.storage_type == 's3' and self.s3_client:
                # S3 버킷
                response = self.s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix=folder_path
                )
                
                if 'Contents' in response:
                    files = [obj['Key'] for obj in response['Contents']]
            
            elif self.storage_type == 'gcs' and self.gcs_client:
                # GCS 버킷
                bucket = self.gcs_client.bucket(self.gcs_bucket)
                blobs = bucket.list_blobs(prefix=folder_path)
                
                files = [blob.name for blob in blobs]
            
            else:
                raise ValueError(f"스토리지를 사용할 수 없습니다: {self.storage_type}")
            
            return files
        
        except Exception as e:
            logger.error(f"파일 목록 조회 오류: {e}")
            return []
    
    def create_temp_file(self, content: bytes = None) -> str:
        """
        임시 파일 생성
        
        Args:
            content: 파일 내용 (선택 사항)
        
        Returns:
            임시 파일 경로
        """
        try:
            # 임시 파일 생성
            fd, temp_path = tempfile.mkstemp()
            os.close(fd)
            
            # 내용 쓰기 (있는 경우)
            if content is not None:
                with open(temp_path, 'wb') as f:
                    f.write(content)
            
            return temp_path
        
        except Exception as e:
            logger.error(f"임시 파일 생성 오류: {e}")
            raise
    
    def create_temp_dir(self) -> str:
        """
        임시 디렉토리 생성
        
        Returns:
            임시 디렉토리 경로
        """
        try:
            # 임시 디렉토리 생성
            temp_dir = tempfile.mkdtemp()
            return temp_dir
        
        except Exception as e:
            logger.error(f"임시 디렉토리 생성 오류: {e}")
            raise
    
    def get_public_url(self, path: str, expires: int = 3600) -> Optional[str]:
        """
        파일 공개 URL 생성 (클라우드 스토리지 전용)
        
        Args:
            path: 파일 경로
            expires: 만료 시간 (초)
        
        Returns:
            공개 URL 또는 None
        """
        try:
            # 스토리지 유형에 따라 URL 생성
            if self.storage_type == 's3' and self.s3_client:
                # S3 버킷
                return self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.s3_bucket,
                        'Key': path
                    },
                    ExpiresIn=expires
                )
            
            elif self.storage_type == 'gcs' and self.gcs_client:
                # GCS 버킷
                bucket = self.gcs_client.bucket(self.gcs_bucket)
                blob = bucket.blob(path)
                return blob.generate_signed_url(
                    version='v4',
                    expiration=datetime.timedelta(seconds=expires),
                    method='GET'
                )
            
            else:
                # 로컬 스토리지는 공개 URL 지원하지 않음
                logger.warning(f"'{self.storage_type}' 스토리지는 공개 URL을 지원하지 않습니다.")
                return None
        
        except Exception as e:
            logger.error(f"공개 URL 생성 오류: {e}")
            return None
