# 배포 가이드

이 문서는 초고정밀 멀티랭귀지 OCR 시스템의 설치 및 배포 방법을 안내합니다.

## 목차

1. [시스템 요구사항](#시스템-요구사항)
2. [Docker를 이용한 배포](#docker를-이용한-배포)
3. [수동 설치](#수동-설치)
4. [클라우드 환경 배포](#클라우드-환경-배포)
5. [보안 설정](#보안-설정)
6. [성능 최적화](#성능-최적화)
7. [배포 후 확인](#배포-후-확인)
8. [문제 해결](#문제-해결)

## 시스템 요구사항

### 하드웨어 요구사항
- **CPU**: 최소 4코어 이상 (8코어 이상 권장)
- **RAM**: 최소 8GB (16GB 이상 권장)
- **저장 공간**: 최소 20GB의 여유 공간
- **GPU**: OCR 성능 향상을 위한 NVIDIA GPU (선택 사항)

### 소프트웨어 요구사항
- **운영 체제**: Ubuntu 20.04 LTS 이상, CentOS 8 이상, 또는 macOS 10.15 이상
- **Docker**: 20.10 이상 (Docker 배포 시)
- **Docker Compose**: 2.0 이상 (Docker 배포 시)
- **Python**: 3.8 이상 (수동 설치 시)
- **Redis**: 6.0 이상 (작업 큐 관리용)
- **CUDA**: 11.0 이상 (GPU 사용 시)

## Docker를 이용한 배포

Docker를 이용한 배포는 가장 간단하고 권장되는 방법입니다.

### 1. 사전 준비

시스템에 Docker와 Docker Compose가 설치되어 있는지 확인하세요:

```bash
docker --version
docker-compose --version
```

설치되어 있지 않다면 [Docker 공식 문서](https://docs.docker.com/get-docker/)를 참조하여 설치하세요.

### 2. 저장소 복제

```bash
git clone https://github.com/yourusername/precision-ocr-system.git
cd precision-ocr-system
```

### 3. 환경 변수 설정

제공된 예시 파일을 복사하여 환경 설정을 구성합니다:

```bash
cp .env.example .env
```

텍스트 편집기로 `.env` 파일을 열고 다음 항목을 설정하세요:

- 외부 API 키 (Google Cloud, Azure, OpenAI 등)
- 저장소 설정 (S3, GCS 등 사용 시)
- Redis 연결 정보 (필요시)
- 네트워크 및 보안 설정

### 4. Docker 이미지 빌드 및 실행

```bash
docker-compose up -d
```

이 명령은 필요한 모든 서비스(웹 서버, 작업자, Redis)를 빌드하고 시작합니다.

### 5. OCR 모델 다운로드

컨테이너가 실행된 후, OCR 모델을 다운로드합니다:

```bash
docker-compose exec web python -m scripts.download_models
```

### 6. 배포 확인

브라우저에서 `http://localhost:8000`에 접속하여 시스템이 정상적으로 작동하는지 확인합니다.

## 수동 설치

Docker를 사용할 수 없거나 특별한 시스템 구성이 필요할 경우 수동 설치 방법을 이용할 수 있습니다.

### 1. 시스템 패키지 설치

Ubuntu 20.04 LTS 기준:

```bash
# 시스템 패키지 설치
apt-get update
apt-get install -y \
    python3 python3-pip python3-dev \
    tesseract-ocr libtesseract-dev \
    tesseract-ocr-jpn tesseract-ocr-kor tesseract-ocr-chi-sim tesseract-ocr-chi-tra \
    mecab libmecab-dev mecab-ipadic-utf8 \
    redis-server \
    build-essential \
    poppler-utils

# 일본어 MeCab 사전 설치
git clone --depth 1 https://github.com/neologd/mecab-ipadic-neologd.git /tmp/mecab-ipadic-neologd
cd /tmp/mecab-ipadic-neologd
./bin/install-mecab-ipadic-neologd -n -y
cd -
rm -rf /tmp/mecab-ipadic-neologd
```

### 2. 저장소 복제 및 Python 패키지 설치

```bash
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
```

### 3. 필요한 디렉토리 생성

```bash
mkdir -p storage/{uploads,processed,temp,results,exports}
mkdir -p models/tessdata
mkdir -p logs
```

### 4. OCR 모델 다운로드

```bash
python -m scripts.download_models
```

### 5. Redis 서버 실행 (이미 실행 중이 아닌 경우)

```bash
redis-server &
```

### 6. 백그라운드 작업자 실행

새 터미널 세션에서:

```bash
source venv/bin/activate  # 가상 환경 사용 시
python -m src.worker.start
```

### 7. API 서버 실행

새 터미널 세션에서:

```bash
source venv/bin/activate  # 가상 환경 사용 시
python main.py
```

### 8. 배포 확인

브라우저에서 `http://localhost:8000`에 접속하여 시스템이 정상적으로 작동하는지 확인합니다.

## 클라우드 환경 배포

### AWS 배포

#### 1. EC2 인스턴스 설정
- Amazon Linux 2 또는 Ubuntu 20.04 LTS AMI 선택
- 최소 t3.large 인스턴스 유형 (4vCPU, 8GB RAM)
- GPU 활용을 위해 g4dn.xlarge 이상 인스턴스 고려
- 최소 20GB 스토리지 할당

#### 2. 보안 그룹 설정
- HTTP(80), HTTPS(443) 포트 개방
- SSH 접속용 포트(22) 제한적 개방

#### 3. Docker 설치 및 시스템 배포
```bash
sudo yum update -y  # Amazon Linux 2
sudo amazon-linux-extras install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/download/v2.15.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 저장소 복제 및 배포
git clone https://github.com/yourusername/precision-ocr-system.git
cd precision-ocr-system
cp .env.example .env
# .env 파일 편집
docker-compose up -d
```

### Google Cloud Platform 배포

#### 1. Compute Engine VM 인스턴스 설정
- Ubuntu 20.04 LTS 이미지 선택
- e2-standard-4 이상 머신 유형 (4vCPU, 16GB RAM)
- GPU 활용을 위해 NVIDIA T4 또는 V100 GPU 추가
- 부팅 디스크 크기 최소 20GB

#### 2. 방화벽 규칙 설정
- HTTP(80), HTTPS(443) 포트 개방
- SSH 접속용 포트(22) 제한적 개방

#### 3. Docker 설치 및 시스템 배포
```bash
# Docker 설치
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install -y docker-ce docker-compose

# 저장소 복제 및 배포
git clone https://github.com/yourusername/precision-ocr-system.git
cd precision-ocr-system
cp .env.example .env
# .env 파일 편집
docker-compose up -d
```

## 보안 설정

### 1. HTTPS 설정

Nginx를 사용하여 HTTPS를 구성합니다:

```bash
# Nginx 설치
apt-get install -y nginx

# Let's Encrypt 인증서 발급
apt-get install -y certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com
```

제공된 `configs/nginx.conf` 파일을 참고하여 Nginx 설정을 조정하세요.

### 2. 인증 설정

`.env` 파일에서 다음 변수를 설정하여 사용자 인증을 활성화합니다:

```
OCR_AUTH_ENABLED=True
OCR_USER_REGISTRATION=False
```

관리자 계정의 사용자 이름과 비밀번호를 환경 변수로 설정합니다:

```
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_secure_password
```

### 3. API 키 보안

외부 API 키(Google Cloud, Azure, OpenAI 등)를 직접 소스 코드나 `.env` 파일에 저장하지 말고, 보안 비밀 관리 도구를 사용하는 것이 좋습니다.

**AWS Secrets Manager 사용 예:**
```bash
# 비밀 생성
aws secretsmanager create-secret --name ocr-service-api-keys --secret-string '{
  "OPENAI_API_KEY": "your-api-key",
  "AZURE_FORM_KEY": "your-azure-key",
  "GOOGLE_API_KEY": "your-google-key"
}'

# 애플리케이션에서 비밀 로드
# 코드에서 AWS SDK를 사용하여 비밀을 로드하는 로직 구현
```

## 성능 최적화

### 1. 작업자 수 조정

작업 처리량을 최적화하기 위해 작업자 수를 서버 CPU 코어 수에 맞게 조정합니다:

```
# .env 파일에서
OCR_MAX_WORKERS=8  # CPU 코어 수에 맞게 조정
```

### 2. GPU 가속 활성화

GPU를 사용할 수 있는 환경에서는 `.env` 파일에서 다음과 같이 설정합니다:

```
NVIDIA_VISIBLE_DEVICES=all  # Docker에서 GPU 사용
```

Docker Compose 파일에 GPU 지원을 추가합니다:

```yaml
services:
  worker:
    # ... 기존 설정 ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### 3. 캐싱 최적화

Redis 캐싱을 활성화하여 반복적인 OCR 요청의 성능을 개선합니다:

```
# .env 파일에서
OCR_CACHE_ENABLED=True
OCR_CACHE_TTL=3600  # 캐시 유효 시간(초)
```

## 배포 후 확인

### 1. 서비스 상태 확인

```bash
# Docker 배포 시
docker-compose ps

# 개별 서비스 로그 확인
docker-compose logs -f web
docker-compose logs -f worker
```

### 2. API 상태 확인

```bash
curl http://localhost:8000/api/v1/health
```

정상적인 응답 예시:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": 1672531200,
  "redis": "ok",
  "engines": {
    "custom_model": true,
    "tesseract": true,
    "google_vision": false,
    "azure_form": false
  }
}
```

### 3. 테스트 문서 처리

웹 인터페이스(`http://localhost:8000`)에서 샘플 문서를 업로드하여 OCR 처리 기능을 테스트하세요.

## 문제 해결

### 일반적인 문제

#### Docker 컨테이너가 시작되지 않음
```bash
# 로그 확인
docker-compose logs

# 네트워크 및 포트 충돌 확인
netstat -tuln

# 컨테이너 재시작
docker-compose down
docker-compose up -d
```

#### OCR 엔진 초기화 실패
```bash
# Tesseract 설치 확인
tesseract --version

# 언어 데이터 확인
tesseract --list-langs

# 모델 다운로드 스크립트 실행
python -m scripts.download_models
```

#### Redis 연결 오류
```bash
# Redis 서버 실행 확인
redis-cli ping  # "PONG" 응답 확인

# Redis 연결 설정 확인
cat .env | grep REDIS
```

#### 메모리 부족 오류
```bash
# 메모리 사용량 확인
free -h

# Docker 컨테이너 메모리 제한 조정
# docker-compose.yml 편집:
services:
  worker:
    # ... 기존 설정 ...
    deploy:
      resources:
        limits:
          memory: 4G  # 메모리 제한 증가
```

### 로그 확인

문제 해결을 위해 로그를 자세히 확인하세요:

```bash
# 애플리케이션 로그
cat logs/ocr_service.log

# 오류 로그
cat logs/error.log

# Docker 로그
docker-compose logs -f
```

### 지원 문의

기술적인 문제가 발생하면 GitHub 이슈를 통해 문의하거나 프로젝트 관리자에게 연락하세요.

---

이 배포 가이드는 초고정밀 멀티랭귀지 OCR 시스템의 기본적인 설치 및 배포 방법을 설명합니다. 특정 환경이나 요구사항에 따라 설정을 조정해야 할 수 있습니다.
