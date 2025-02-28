"""
로깅 관리 모듈
- 통합 로깅 시스템 설정
- 로그 포맷팅 및 핸들러 설정
- 로그 레벨 관리
"""

import os
import sys
import logging
import logging.handlers
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from src.core.config import config


class LoggingManager:
    """로깅 시스템 관리 클래스"""
    
    # 싱글톤 인스턴스
    _instance = None
    
    def __new__(cls):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super(LoggingManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """로거 초기화"""
        if self._initialized:
            return
        
        # 로그 디렉토리 설정
        self.log_dir = config.get('logging.log_dir', 'logs')
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        
        # 로그 레벨 설정
        self.log_level_str = config.get('logging.log_level', 'INFO')
        self.log_level = getattr(logging, self.log_level_str)
        
        # 로그 파일 설정
        self.log_file = config.get('logging.log_file', os.path.join(self.log_dir, 'ocr_service.log'))
        self.error_log_file = config.get('logging.error_log_file', os.path.join(self.log_dir, 'error.log'))
        
        # 로그 포맷 설정
        self.log_format = config.get(
            'logging.log_format', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # JSON 로깅 활성화 여부
        self.json_logging = config.get('logging.json_format', False)
        
        # 로깅 시스템 설정
        self._configure_logging()
        
        # 전역 예외 핸들러 설정
        self._set_global_exception_handler()
        
        self._initialized = True
    
    def _configure_logging(self):
        """로깅 시스템 설정"""
        # 루트 로거 설정
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # 기존 핸들러 제거
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 포맷터 설정
        if self.json_logging:
            formatter = self._get_json_formatter()
        else:
            formatter = logging.Formatter(self.log_format)
        
        # 콘솔 핸들러 추가
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # 파일 핸들러 추가 (전체 로그)
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # 오류 로그 파일 핸들러 추가
        error_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
        
        # OCR 서비스 로거 설정
        ocr_logger = logging.getLogger('ocr_service')
        ocr_logger.setLevel(self.log_level)
        
        # 개발 모드에서는 디버그 정보 출력
        if config.get('app.debug', False):
            # 추가 디버그 핸들러 설정
            debug_handler = logging.StreamHandler(sys.stderr)
            debug_handler.setLevel(logging.DEBUG)
            debug_formatter = logging.Formatter('%(levelname)s [%(filename)s:%(lineno)d]: %(message)s')
            debug_handler.setFormatter(debug_formatter)
            ocr_logger.addHandler(debug_handler)
    
    def _get_json_formatter(self):
        """JSON 포맷 로거 설정"""
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                    'level': record.levelname,
                    'name': record.name,
                    'message': record.getMessage(),
                }
                
                # 예외 정보 추가
                if record.exc_info:
                    log_data['exception'] = self.formatException(record.exc_info)
                
                # 추가 정보 포함
                if hasattr(record, 'extra') and record.extra:
                    log_data.update(record.extra)
                
                return json.dumps(log_data)
        
        return JsonFormatter()
    
    def _set_global_exception_handler(self):
        """전역 예외 핸들러 설정"""
        def global_exception_handler(exc_type, exc_value, exc_traceback):
            """처리되지 않은 예외를 로깅"""
            if issubclass(exc_type, KeyboardInterrupt):
                # 키보드 인터럽트는 기본 처리
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            # 오류 로깅
            logger = logging.getLogger('ocr_service')
            logger.critical(
                "처리되지 않은 예외",
                exc_info=(exc_type, exc_value, exc_traceback)
            )
        
        # 전역 예외 핸들러 설정
        sys.excepthook = global_exception_handler
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        특정 이름의 로거 가져오기
        
        Args:
            name: 로거 이름
        
        Returns:
            설정된 로거 인스턴스
        """
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)
        return logger
    
    def set_log_level(self, level: str):
        """
        로그 레벨 변경
        
        Args:
            level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
            new_level = getattr(logging, level)
            
            # 루트 로거 레벨 변경
            logging.getLogger().setLevel(new_level)
            
            # 모든 핸들러 레벨 변경 (ERROR 핸들러 제외)
            for handler in logging.getLogger().handlers:
                if handler.name != 'error_handler':
                    handler.setLevel(new_level)
            
            self.log_level = new_level
            self.log_level_str = level
            
            logger = logging.getLogger('ocr_service')
            logger.info(f"로그 레벨이 {level}로 변경되었습니다.")


# 전역 로깅 매니저 인스턴스
logging_manager = LoggingManager()


def get_logger(name: str) -> logging.Logger:
    """
    특정 이름의 로거 가져오기 (편의 함수)
    
    Args:
        name: 로거 이름
    
    Returns:
        설정된 로거 인스턴스
    """
    return logging_manager.get_logger(name)


def log_extra(logger: logging.Logger, level: str, message: str, extra: Dict[str, Any]):
    """
    추가 정보와 함께 로깅
    
    Args:
        logger: 로거 인스턴스
        level: 로그 레벨
        message: 로그 메시지
        extra: 추가 데이터
    """
    if level.upper() == 'DEBUG':
        logger.debug(message, extra={'extra': extra})
    elif level.upper() == 'INFO':
        logger.info(message, extra={'extra': extra})
    elif level.upper() == 'WARNING':
        logger.warning(message, extra={'extra': extra})
    elif level.upper() == 'ERROR':
        logger.error(message, extra={'extra': extra})
    elif level.upper() == 'CRITICAL':
        logger.critical(message, extra={'extra': extra})
