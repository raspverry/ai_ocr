ocr-service/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py            # API 라우트 정의
│   │   └── models.py            # API 요청/응답 모델
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # 설정 관리
│   │   └── logging.py           # 로깅 설정
│   │
│   ├── ocr/
│   │   ├── __init__.py
│   │   ├── engines/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # 기본 OCR 엔진 인터페이스
│   │   │   ├── custom_model.py  # 딥러닝 기반 커스텀 OCR
│   │   │   ├── tesseract.py     # 테서랙트 OCR
│   │   │   ├── google_vision.py # Google Cloud Vision OCR
│   │   │   └── azure_form.py    # Azure Form Recognizer
│   │   │
│   │   ├── ensemble.py          # OCR 엔진 앙상블
│   │   ├── preprocessor.py      # 이미지 전처리
│   │   ├── postprocessor.py     # 텍스트 후처리
│   │   └── special_handlers.py  # 도장, 손글씨 등 특수 항목 처리
│   │
│   ├── document/
│   │   ├── __init__.py
│   │   ├── pdf_processor.py     # PDF 처리
│   │   └── orientation.py       # 방향 감지 및 보정
│   │
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── field_config.py      # 필드 설정 관리
│   │   ├── llm_processor.py     # LLM 기반 데이터 추출
│   │   └── csv_exporter.py      # CSV 내보내기
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   └── manager.py           # 파일 스토리지 관리
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   └── helpers.py           # 유틸리티 함수
│   │
│   ├── web/
│   │   ├── __init__.py
│   │   ├── app.py               # 웹 앱
│   │   ├── routes.py            # 웹 라우트
│   │   ├── static/              # 정적 파일 (CSS, JS 등)
│   │   ├── templates/           # HTML 템플릿
│   │   └── forms.py             # 웹 폼
│   │
│   └── worker/
│       ├── __init__.py
│       ├── tasks.py             # 작업 정의
│       └── start.py             # 작업자 실행 스크립트
│
├── models/                      # OCR 모델 파일
│
├── configs/
│   └── default.yml              # 기본 설정
│
├── scripts/
│   ├── download_models.py       # 모델 다운로드 스크립트
│   └── install_dependencies.sh  # 의존성 설치 스크립트
│
├── docker/
│   ├── Dockerfile               # 애플리케이션 Dockerfile
│   └── Dockerfile.worker        # 작업자 Dockerfile
│
├── tests/                       # 테스트 코드
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_ocr.py
│   └── test_extraction.py
│
├── .env.example                 # 환경 변수 예시
├── requirements.txt             # Python 패키지
├── docker-compose.yml           # Docker Compose 설정
├── Dockerfile                   # 메인 Dockerfile
├── main.py                      # 애플리케이션 진입점
└── README.md                    # 문서
