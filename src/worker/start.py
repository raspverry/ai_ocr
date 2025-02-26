#!/usr/bin/env python3
"""
OCR 작업자 프로세스 시작 스크립트
- RQ 작업자 시작
- 백그라운드 작업 처리
"""

import os
import sys
import logging
import redis
from rq import Worker, Queue, Connection
import signal
import multiprocessing

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ocr_worker")

# 설정 로드
from src.core.config import config

# Redis 연결 설정
REDIS_URL = config.get('queue.redis_url', 'redis://localhost:6379/0')
QUEUE_NAME = config.get('queue.queue_name', 'ocr_tasks')
MAX_WORKERS = config.get('queue.max_workers', 4)

# 정상 종료 처리
def handle_shutdown(signum, frame):
    """종료 시그널 처리"""
    logger.info(f"종료 시그널 수신 ({signum}), 작업자 종료 중...")
    sys.exit(0)

def start_worker(worker_id):
    """작업자 프로세스 시작"""
    logger.info(f"작업자 {worker_id} 시작")
    
    # 종료 시그널 핸들러 등록
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    try:
        # Redis 연결
        redis_conn = redis.Redis.from_url(REDIS_URL)
        
        # 작업자 설정
        with Connection(redis_conn):
            worker = Worker([Queue(QUEUE_NAME)], name=f"worker-{worker_id}")
            
            # 작업자 시작
            worker.work(with_scheduler=True)
    
    except Exception as e:
        logger.error(f"작업자 {worker_id} 오류: {e}")
    
    logger.info(f"작업자 {worker_id} 종료")

def main():
    """메인 함수"""
    logger.info(f"OCR 작업자 프로세스 시작 (작업자 수: {MAX_WORKERS})")
    logger.info(f"Redis URL: {REDIS_URL}")
    logger.info(f"큐 이름: {QUEUE_NAME}")
    
    try:
        # Redis 연결 테스트
        redis_conn = redis.Redis.from_url(REDIS_URL)
        if not redis_conn.ping():
            logger.error("Redis 연결 실패")
            return 1
        
        # 종료 시그널 핸들러 등록
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
        
        # 다중 작업자 시작
        processes = []
        
        for i in range(MAX_WORKERS):
            process = multiprocessing.Process(target=start_worker, args=(i+1,))
            processes.append(process)
            process.start()
        
        # 작업자 프로세스 대기
        for process in processes:
            process.join()
        
        return 0
    
    except Exception as e:
        logger.error(f"작업자 시작 오류: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
