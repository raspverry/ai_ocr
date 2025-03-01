# 개발 가이드

## 목차
- [소개](#소개)
- [시스템 아키텍처](#시스템-아키텍처)
- [개발 환경 설정](#개발-환경-설정)
- [코드 구조](#코드-구조)
- [주요 모듈 및 클래스](#주요-모듈-및-클래스)
- [OCR 엔진 앙상블 메커니즘](#ocr-엔진-앙상블-메커니즘)
- [LLM 기반 데이터 추출](#llm-기반-데이터-추출)
- [작업 큐 및 비동기 처리](#작업-큐-및-비동기-처리)
- [스토리지 관리](#스토리지-관리)
- [웹 인터페이스](#웹-인터페이스)
- [API 참조](#api-참조)
- [단위 테스트](#단위-테스트)
- [문제 해결 및 디버깅](#문제-해결-및-디버깅)
- [기여 가이드라인](#기여-가이드라인)

## 소개

초고정밀 멀티랭귀지 OCR 시스템은 다양한 OCR 엔진을 앙상블하여 99.5% 이상의 정확도를 제공하는 문서 인식 및 데이터 추출 시스템입니다. 이 개발 가이드는 시스템의 구조, 주요 컴포넌트, 확장 방법을 설명합니다.

### 핵심 기능

- 다국어 지원: 일본어, 한국어, 영어, 중국어(간체/번체)
- PDF 자동 방향 보정: 기울어지거나 회전된 페이지 자동 감지 및 보정
- 고정확도 OCR: 여러 OCR 엔진 앙상블로 최고 수준 정확도 제공
- 특수 항목 인식: 도장, 손글씨, 취소선 등 인식
- LLM 기반 데이터 추출: 설정 가능한 필드 자동 추출
- CSV 내보내기: 추출된 데이터를 CSV로 저장
- 웹 인터페이스: 직관적인 웹 UI로 문서 관리 및 추출 결과 검토

## 시스템 아키텍처

시스템은 다음과 같은 주요 컴포넌트로 구성됩니다:

1. **FastAPI 웹 서버**: RESTful API 및 웹 인터페이스 제공
2. **OCR 엔진 앙상블**: 다양한 OCR 엔진의 결과를 조합하여 최고의 정확도 달성
3. **Redis 작업 큐**: 비동기 작업 처리 및 분산 처리
4. **스토리지 관리**: 로컬 또는 클라우드 스토리지를 통한 문서 및 결과 관리
5. **LLM 프로세서**: 대형 언어 모델을 활용한 고급 데이터 추출
6. **모니터링 시스템**: 시스템 성능 및 오류 모니터링

각 컴포넌트는 모듈화되어 있으며, 독립적으로 확장 가능합니다.

## 개발 환경 설정

### 요구 사항
- Python 3.8+
- Redis 6.0+
- Docker 및 Docker Compose (권장)
- 최소 8GB RAM
- (선택) NVIDIA GPU with CUDA 11.0+

### 로컬 개발 환경 설정

1. 저장소 클론
```bash
git clone https://github.com/yourusername/precision-ocr-system.git
cd precision-ocr-system
```

2. 가상 환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

4. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일을 편집하여 API 키 및 구성 설정
```

5. OCR 모델 다운로드
```bash
python -m scripts.download_models
```

6. Redis 서버 실행
```bash
redis-server
```

7. 개발 서버 실행
```bash
# 터미널 1: API 서버 실행
python main.py

# 터미널 2: 작업 큐 작업자 실행
python -m src.worker.start
```

### Docker를 사용한 개발

Docker를 사용하여 개발 환경을 설정할 수도 있습니다:

```bash
# 이미지 빌드
docker-compose build

# 서비스 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

## 코드 구조

프로젝트는 다음과 같은 디렉토리 구조를 따릅니다:

```
ocr-service/
├── src/                   # 소스 코드
│   ├── api/               # API 관련 코드
│   ├── core/              # 핵심 기능 및 설정
│   ├── ocr/               # OCR 엔진 및 처리
│   ├── document/          # 문서 처리
│   ├── extraction/        # LLM 기반 데이터 추출
│   ├── storage/           # 스토리지 관리
│   ├── utils/             # 유틸리티 함수
│   ├── web/               # 웹 UI
│   └── worker/            # 백그라운드 작업자
├── models/                # OCR 모델 저장소
├── configs/               # 설정 파일
├── scripts/               # 유틸리티 스크립트
├── docker/                # Docker 구성
├── tests/                 # 테스트 코드
├── .env.example           # 환경 변수 예시
├── requirements.txt       # Python 패키지
├── docker-compose.yml     # Docker Compose 설정
├── Dockerfile             # Dockerfile
└── main.py                # 애플리케이션 진입점
```

## 주요 모듈 및 클래스

### 1. OCR 관련 모듈
- `src/ocr/engines/`: 다양한 OCR 엔진 구현
- `src/ocr/ensemble.py`: OCR 엔진 앙상블 관리
- `src/ocr/preprocessor.py`: 이미지 전처리
- `src/ocr/postprocessor.py`: OCR 결과 후처리
- `src/ocr/special_handlers.py`: 도장, 손글씨 등 특수 항목 처리

### 2. 문서 처리 모듈
- `src/document/pdf_processor.py`: PDF 파일 처리
- `src/document/orientation.py`: 문서 방향 감지 및 보정

### 3. 데이터 추출 모듈
- `src/extraction/llm_processor.py`: LLM 기반 데이터 추출
- `src/extraction/field_config.py`: 추출 필드 구성 관리
- `src/extraction/csv_exporter.py`: 추출 데이터 CSV 내보내기

### 4. 코어 모듈
- `src/core/config.py`: 애플리케이션 설정 관리
- `src/core/logging.py`: 로깅 구성

### 5. 작업자 모듈
- `src/worker/tasks.py`: 백그라운드 작업 정의
- `src/worker/start.py`: 작업자 프로세스 시작

### 6. API 및 웹 모듈
- `src/api/routes.py`: API 엔드포인트
- `src/web/routes.py`: 웹 UI 엔드포인트

## OCR 엔진 앙상블 메커니즘

OCR 엔진 앙상블은 여러 OCR 엔진의 결과를 조합하여 정확도를 높이는 핵심 기능입니다.

### 앙상블 작동 방식

```python
# src/ocr/ensemble.py의 _ensemble_results 메서드 참조
def _ensemble_results(self, engine_results, lang):
    # 언어 결정 (투표 방식)
    detected_languages = [result['language'] for result in engine_results]
    
    # 가중치 기반 텍스트 선택
    weighted_texts = []
    for engine_name, result in engine_results.items():
        confidence = result.get('confidence', 0.0)
        engine_weight = self.weights.get(engine_name, 0.0)
        
        if confidence >= self.confidence_threshold:
            weighted_score = confidence * engine_weight
            weighted_texts.append((result['text'], weighted_score))
    
    # 가장 높은 가중치 점수를 가진 텍스트 선택
    final_text = weighted_texts[0][0] if weighted_texts else ""
```

### 새 OCR 엔진 추가하기

새 OCR 엔진을 앙상블에 추가하려면:

1. `src/ocr/engines/` 디렉토리에 새 엔진 클래스 생성
2. `BaseOCREngine` 클래스 상속 및 `recognize` 메서드 구현
3. `src/ocr/engines/__init__.py`에 엔진 등록
4. 설정에서 새 엔진 활성화 및 가중치 설정

## LLM 기반 데이터 추출

LLM 프로세서는 OCR 결과에서 구조화된 필드 데이터를 추출합니다.

### 주요 기능

- 프롬프트 엔지니어링으로 효과적인 데이터 추출
- 다양한 필드 유형 지원 (텍스트, 날짜, 금액, 회사명 등)
- 여러 LLM 공급자 지원 (OpenAI, Anthropic)

### 필드 구성 예시

```json
{
  "name": "invoice_number",
  "type": "text",
  "context": "청구서 번호|請求書番号|インボイス番号|No.|番号",
  "regex": "(\\d{1,3}[\\-\\.]\\d{1,3}[\\-\\.]\\d{1,5})"
}
```

### LLM 공급자 추가하기

새 LLM 공급자를 추가하려면:

1. `src/extraction/llm_processor.py`에 새 공급자 메서드 추가
2. `_call_llm` 메서드에서 공급자 처리 추가
3. 환경 변수 및 설정 업데이트

## 작업 큐 및 비동기 처리

작업 큐는 Redis와 RQ(Redis Queue)를 사용하여 구현되며, 장시간 실행되는 작업의 비동기 처리를 지원합니다.

### 작업 정의 및 등록

```python
# 작업 정의 예시
def process_document(file_bytes, file_name, options):
    # 비동기 래퍼
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            process_document_async(file_bytes, file_name, options)
        )
        return result
    finally:
        loop.close()

# 작업 등록 (API 라우트에서)
job = queue.enqueue(
    process_document,
    args=(file_bytes, file.filename, options),
    job_timeout=3600  # 1시간 타임아웃
)
```

### 작업자 관리

작업자 프로세스는 `src/worker/start.py`에서 관리됩니다. 여러 작업자 프로세스를 병렬로 실행할 수 있습니다:

```bash
# 4개의 작업자 프로세스 시작
OCR_MAX_WORKERS=4 python -m src.worker.start
```

## 스토리지 관리

스토리지 관리자는 파일 저장, 검색, 삭제를 처리하며 여러 백엔드(로컬, S3, GCS)를 지원합니다.

### 스토리지 백엔드 사용

```python
# 스토리지 관리자 초기화
storage_manager = StorageManager()

# 파일 저장
file_path = await storage_manager.save_file(file_bytes, file_name)

# 파일 검색
content = await storage_manager.get_file(file_path)

# 파일 삭제
success = await storage_manager.delete_file(file_path)
```

### 새 스토리지 백엔드 추가하기

새 스토리지 백엔드를 추가하려면:

1. `src/storage/manager.py`에 새 백엔드 메서드 추가
2. `_initialize_storage` 메서드에서 백엔드 초기화 추가
3. 각 동작(저장, 검색, 삭제)에 대한 백엔드별 구현 추가

## 웹 인터페이스

웹 인터페이스는 FastAPI, Jinja2 템플릿, Bootstrap으로 구현됩니다.

### 주요 페이지
- 홈: `/`
- 업로드: `/upload`
- 문서 목록: `/documents`
- 결과 보기: `/result/{task_id}`
- 데이터 추출: `/extraction/{task_id}`
- 설정: `/settings`

### 템플릿 구조
- `src/web/templates/layout.html`: 기본 레이아웃
- `src/web/templates/*.html`: 개별 페이지 템플릿

### 정적 자산
- `src/web/static/css/`: CSS 파일
- `src/web/static/js/`: JavaScript 파일
- `src/web/static/images/`: 이미지 파일

## API 참조

RESTful API는 JSON 응답을 제공하며 다음과 같은 주요 엔드포인트를 포함합니다:

### OCR 관련 엔드포인트
- `POST /api/v1/ocr`: 문서 업로드 및 OCR 처리
- `GET /api/v1/ocr/{task_id}`: OCR 작업 결과 조회

### 데이터 추출 엔드포인트
- `POST /api/v1/extraction/{task_id}`: OCR 결과에서 데이터 추출
- `GET /api/v1/extraction/{task_id}`: 추출 작업 결과 조회
- `GET /api/v1/extraction/{task_id}/csv`: 추출 데이터를 CSV로 내보내기

### 설정 엔드포인트
- `GET /api/v1/fields`: 추출 필드 설정 조회
- `POST /api/v1/fields`: 추출 필드 설정 업데이트

### 상태 확인 엔드포인트
- `GET /api/v1/health`: 시스템 상태 확인
- `GET /api/v1/languages`: 지원 언어 목록 조회

## 단위 테스트

단위 테스트는 `tests/` 디렉토리에 있으며 pytest로 실행됩니다:

```bash
# 모든 테스트 실행
pytest

# 특정 모듈 테스트
pytest tests/test_ocr.py

# 커버리지 보고서 생성
pytest --cov=src tests/
```

### 테스트 구조
- `tests/test_api.py`: API 엔드포인트 테스트
- `tests/test_ocr.py`: OCR 엔진 및 앙상블 테스트
- `tests/test_extraction.py`: 데이터 추출 테스트

## 문제 해결 및 디버깅

### 로깅

시스템은 구조화된 로깅을 사용하며, 다음과 같이 관리됩니다:

```python
# 로거 가져오기
logger = logging.getLogger(__name__)

# 다양한 로그 레벨
logger.debug("디버그 메시지")
logger.info("정보 메시지")
logger.warning("경고 메시지")
logger.error("오류 메시지", exc_info=True)  # 예외 스택 트레이스 포함
```

로그 파일은 `logs/` 디렉토리에 저장됩니다.

### 디버그 모드

디버그 모드를 활성화하려면:

```bash
# 환경 변수 설정
OCR_DEBUG=True

# 또는 .env 파일에서 설정
# OCR_DEBUG=True
```

디버그 모드에서는:
- 상세 로깅 활성화
- OCR 엔진별 결과 포함
- LLM 원본 응답 포함

### 일반적인 문제 해결

1. **OCR 인식 오류**
   - 이미지 전처리 매개변수 조정
   - 앙상블 가중치 조정
   - 언어 코드 명시적 지정

2. **Redis 연결 오류**
   - Redis 서버 실행 중인지 확인
   - 연결 URL 확인 (`OCR_REDIS_URL` 환경 변수)

3. **LLM API 오류**
   - API 키 확인
   - 프롬프트 길이 확인
   - 응답 형식 확인

## 기여 가이드라인

### 개발 워크플로
1. 이슈 생성 또는 기존 이슈 할당
2. 새 브랜치 생성 (`git checkout -b feature/my-feature`)
3. 코드 작성 및 테스트
4. 커밋 및 푸시 (`git push origin feature/my-feature`)
5. 풀 리퀘스트 생성

### 코드 스타일
- PEP 8 스타일 가이드 준수
- 명확한 함수 및 변수 이름 사용
- 적절한 주석 및 문서화 유지

### 테스트
- 모든 새 기능에 대한 단위 테스트 작성
- 기존 테스트가 통과하는지 확인
- 적절한 코드 커버리지 유지

### 코드 리뷰
- 모든 풀 리퀘스트는 최소 1명의 리뷰어가 승인해야 함
- 코드 품질, 성능, 보안에 중점을 둔 리뷰
- 건설적인 피드백 제공

---

이 개발 가이드는 초고정밀 멀티랭귀지 OCR 시스템의 개발에 대한 종합적인 개요를 제공합니다. 추가 질문이나 문제점은 GitHub 이슈를 통해 문의해 주세요.
