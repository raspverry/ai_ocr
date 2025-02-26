# 초고정밀 멀티랭귀지 OCR 시스템

일본 비즈니스 문서를 위한 초정밀 OCR 시스템으로, 다양한 OCR 엔진을 앙상블하여 99.5% 이상의 정확도를 제공합니다.

## 주요 기능

- **다국어 지원**: 일본어, 한국어, 영어, 중국어(간체/번체) 지원
- **PDF 자동 방향 보정**: 기울어지거나 회전된 페이지 자동 감지 및 보정
- **고정확도 OCR**: 여러 OCR 엔진 앙상블로 최고 수준 정확도 제공
  - **특수 항목 인식**: 도장, 손글씨, 수정된 텍스트 등 인식
  - **앙상블 접근법**: TrOCR, Tesseract, Google Vision, Azure Form Recognizer 결합
- **LLM 기반 데이터 추출**: 설정 가능한 필드 자동 추출
- **CSV 내보내기**: 추출된 데이터를 CSV로 저장
- **웹 인터페이스**: 직관적인 웹 UI로 문서 관리 및 추출 결과 검토

## 시스템 아키텍처

![시스템 아키텍처](./docs/images/architecture.png)

## 시스템 요구사항

- Python 3.8+
- Redis 6.0+
- Docker 및 Docker Compose(권장)
- 최소 8GB RAM
- (선택) NVIDIA GPU with CUDA 11.0+

## 빠른 시작 (Docker)

```bash
# 1. 저장소 복제
git clone https://github.com/yourusername/precision-ocr-system.git
cd precision-ocr-system

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 API 키 등 설정

# 3. Docker로 실행
docker-compose up -d

# 4. 웹 접속 (브라우저에서)
# http://localhost:8000
```

## 수동 설치

<details>
<summary>펼쳐서 자세한 설치 방법 보기</summary>

### 1. 사전 요구사항

Ubuntu 20.04 LTS에서의 설치 예시:

```bash
# 시스템 패키지 설치
apt-get update
apt-get install -y \
    python3 python3-pip python3-dev \
    tesseract-ocr libtesseract-dev \
    tesseract-ocr-jpn tesseract-ocr-kor tesseract-ocr-chi-sim tesseract-ocr-chi-tra \
    mecab libmecab-dev mecab-ipadic-utf8 \
    redis-server \
    build-essential

# 일본어 MeCab 사전 설치
git clone --depth 1 https://github.com/neologd/mecab-ipadic-neologd.git
cd mecab-ipadic-neologd
./bin/install-mecab-ipadic-neologd -n -y
cd ..
```

### 2. 애플리케이션 설치

```bash
# 저장소 복제
git clone https://github.com/yourusername/precision-ocr-system.git
cd precision-ocr-system

# 가상 환경 생성 (선택 사항)
python3 -m venv venv
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 설정

# OCR 모델 다운로드
python -m scripts.download_models
```

### 3. 애플리케이션 실행

```bash
# Redis 서버 실행 (이미 실행 중이 아닌 경우)
redis-server &

# 백그라운드 작업자 실행
python -m src.worker.start

# API 서버 실행
python main.py
```

### 4. 웹 접속
브라우저에서 `http://localhost:8000` 접속

</details>

## 사용 방법

### 웹 인터페이스 사용

1. **로그인**: 시스템에 로그인 (기본 계정: admin/admin)
2. **문서 업로드**: "새 문서 업로드" 버튼을 클릭하여 PDF 또는 이미지 파일 업로드
3. **처리 대기**: OCR 처리가 완료될 때까지 대기 (처리 상태 실시간 확인 가능)
4. **결과 확인**: 처리 완료 후 텍스트 추출 결과 확인
5. **필드 추출**: "데이터 추출" 탭에서 추출된 key-value 확인 및 편집
6. **CSV 내보내기**: "내보내기" 버튼으로 추출 데이터를 CSV로 저장

### 설정 페이지

"설정" 메뉴에서 다음을 구성할 수 있습니다:

1. **추출 필드 설정**:
   - 필드 이름 (예: "invoice_number", "date", "total_amount")
   - 필드 유형 (텍스트, 날짜, 금액, 회사명 등)
   - 추출 컨텍스트 (해당 필드 주변에 나타나는 텍스트)
   - 정규식 패턴 (해당하는 경우)

2. **OCR 엔진 설정**:
   - 사용할 OCR 엔진 선택
   - 엔진별 가중치 조정
   - 신뢰도 임계값 설정

3. **처리 옵션**:
   - 이미지 전처리 설정
   - 후처리 옵션
   - 캐싱 설정

## API 사용

RESTful API를 통해 시스템을 프로그래밍 방식으로 사용할 수 있습니다:

```bash
# 문서 OCR 처리 요청
curl -X POST \
  -F "file=@your_document.pdf" \
  -F "options={\"language\":\"jpn\", \"extract_entities\":true}" \
  http://localhost:8000/api/v1/ocr

# 처리 결과 확인
curl http://localhost:8000/api/v1/ocr/{task_id}

# 추출 필드 설정 가져오기
curl http://localhost:8000/api/v1/extraction/fields

# CSV 내보내기
curl -X GET \
  -o extracted_data.csv \
  http://localhost:8000/api/v1/extraction/{task_id}/csv
```

## 디렉토리 구조

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

## 확장성 및 성능

- **수평적 확장**: Docker Swarm 또는 Kubernetes를 통해 여러 작업자 노드로 확장
- **분산 처리**: Redis 작업 큐를 통한 효율적인 작업 분배
- **캐싱**: 이미지 해시 기반 캐싱으로 반복 처리 방지
- **배치 처리**: 대용량 문서 효율적 처리

## 문제 해결

<details>
<summary>자주 발생하는 문제</summary>

### 설치 문제

- **Tesseract 오류**: `apt-get install tesseract-ocr` 명령으로 재설치
- **MeCab 사전 오류**: `mecab-ipadic-neologd` 사전 수동 설치 확인
- **Redis 연결 오류**: Redis 서버 실행 중인지 확인 (`redis-cli ping`)

### 성능 문제

- **메모리 부족**: `docker-compose.yml`에서 메모리 제한 증가
- **느린 처리 속도**: GPU 지원 활성화 또는 배치 크기 조정
- **낮은 OCR 정확도**: 특정 문서 유형에 맞게 앙상블 가중치 조정

### 일반적인 오류

- **파일 형식 오류**: 지원되는 파일 형식(PDF, JPG, PNG) 사용
- **API 키 오류**: `.env` 파일에서 Google/Azure API 키 확인
- **언어 감지 실패**: 수동으로 언어 지정 (`language` 옵션 사용)

</details>

## 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 기여 방법

1. 이슈 제기 또는 기능 요청
2. 풀 리퀘스트 제출
3. 코드 리뷰 참여

---

문서에 대한 질문이나 도움이 필요하면 GitHub 이슈를 통해 문의하세요.
