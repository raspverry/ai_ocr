# 배포 가이드

## 목차
- [소개](#소개)
- [요구사항](#요구사항)
- [배포 환경](#배포-환경)
- [배포 단계](#배포-단계)
- [배포 검증](#배포-검증)
- [문제 해결](#문제-해결)
- [롤백 절차](#롤백-절차)

## 소개
이 문서는 애플리케이션 배포 프로세스에 대한 가이드입니다. 개발 환경에서 프로덕션 환경으로 안전하고 효율적으로 애플리케이션을 배포하는 방법을 설명합니다.

## 요구사항
배포를 진행하기 전에 다음 요구사항을 충족해야 합니다:

- Git 저장소에 대한 접근 권한
- 배포 대상 서버에 대한 SSH 접근 권한
- Docker 및 Docker Compose 설치 (버전 20.10.x 이상)
- 환경별 설정 파일 (.env)
- 배포 권한이 있는 계정

## 배포 환경
시스템은 다음과 같은 환경으로 구성되어 있습니다:

1. **개발 환경 (Development)**: 개발자들이 기능을 개발하고, 테스트하는 환경
2. **스테이징 환경 (Staging)**: 프로덕션과 유사한 환경에서 QA 테스트를 수행하는 환경
3. **프로덕션 환경 (Production)**: 실제 사용자가 접근하는 운영 환경

## 배포 단계

### 1. 배포 준비
```bash
# 저장소 최신 상태로 업데이트
git pull origin main

# 의존성 패키지 설치 확인
npm install

# 빌드 실행
npm run build
```

### 2. 도커 이미지 생성
```bash
# 도커 이미지 빌드
docker build -t myapp:latest .

# 이미지 태그 설정 (환경별)
docker tag myapp:latest myapp:prod-$(date +%Y%m%d)
```

### 3. 배포 실행
```bash
# 도커 컴포즈로 배포
docker-compose -f docker-compose.prod.yml up -d

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f
```

### 4. 서비스 상태 확인
```bash
# 컨테이너 상태 확인
docker ps

# 서비스 헬스체크
curl -I https://your-service-url.com/health
```

## 배포 검증
배포 후 다음 항목을 검증하세요:

1. 애플리케이션이 정상적으로 시작되는지 확인
2. 주요 기능이 정상 동작하는지 확인
3. 데이터베이스 마이그레이션이 성공적으로 실행되었는지 확인
4. 모니터링 시스템에서 이상 징후가 없는지 확인

## 문제 해결

### 일반적인 문제

#### 1. 서비스가 시작되지 않는 경우
```bash
# 로그 확인
docker logs container_name

# 환경 변수 확인
docker exec container_name env
```

#### 2. 데이터베이스 연결 오류
```bash
# 데이터베이스 접속 테스트
docker exec container_name ping database_host

# 데이터베이스 상태 확인
docker exec database_container pg_isready
```

## 롤백 절차
배포에 문제가 발생한 경우 다음 절차에 따라 롤백을 수행하세요:

```bash
# 이전 버전으로 롤백
docker-compose -f docker-compose.prod.yml down
docker tag myapp:prod-previous myapp:latest
docker-compose -f docker-compose.prod.yml up -d

# 롤백 이력 기록
echo "Rollback performed at $(date)" >> rollback.log
```

## 자동화된 배포
CI/CD 파이프라인을 통한 자동 배포를 구성하는 경우:

1. GitHub Actions 또는 Jenkins 설정 파일을 확인하세요
2. 자동 테스트가 통과하는지 확인하세요
3. 단계별 승인 프로세스에 따라 배포를 진행하세요

---

문서 버전: 1.0.0  
최종 업데이트: 2025-03-01
