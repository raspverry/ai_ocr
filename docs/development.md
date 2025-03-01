# 개발 가이드

## 목차
- [소개](#소개)
- [개발 환경 설정](#개발-환경-설정)
- [프로젝트 구조](#프로젝트-구조)
- [코딩 표준](#코딩-표준)
- [Git 워크플로우](#git-워크플로우)
- [테스트](#테스트)
- [문서화](#문서화)
- [배포 준비](#배포-준비)

## 소개
이 개발 가이드는 팀 멤버들이 프로젝트 개발 환경을 설정하고, 코딩 표준을 이해하며, 효과적으로 협업할 수 있도록 도와줍니다.

## 개발 환경 설정

### 필수 소프트웨어
- Node.js (v18.x 이상)
- npm (v9.x 이상) 또는 yarn (v1.22.x 이상)
- Git (v2.30.x 이상)
- Docker Desktop (v20.10.x 이상)
- IDE: VS Code (권장) 또는 WebStorm

### VS Code 권장 확장 프로그램
- ESLint
- Prettier
- Docker
- GitLens
- EditorConfig for VS Code

### 로컬 환경 구성

1. 저장소 복제
```bash
git clone https://github.com/your-organization/your-project.git
cd your-project
```

2. 의존성 설치
```bash
npm install
# 또는
yarn install
```

3. 환경 변수 설정
```bash
cp .env.example .env.local
# .env.local 파일을 열고 필요한 환경 변수를 설정하세요
```

4. 개발 서버 실행
```bash
npm run dev
# 또는
yarn dev
```

5. 로컬 데이터베이스 설정 (Docker 사용)
```bash
docker-compose -f docker-compose.dev.yml up -d
```

## 프로젝트 구조

```
├── src/                  # 소스 코드
│   ├── api/              # API 엔드포인트
│   ├── components/       # UI 컴포넌트
│   ├── config/           # 구성 파일
│   ├── hooks/            # 커스텀 훅
│   ├── models/           # 데이터 모델
│   ├── pages/            # 페이지 컴포넌트
│   ├── services/         # 서비스 레이어
│   ├── styles/           # 글로벌 스타일
│   ├── utils/            # 유틸리티 함수
│   └── App.js            # 루트 컴포넌트
├── public/               # 정적 파일
├── tests/                # 테스트 파일
├── docs/                 # 문서
├── .eslintrc.js          # ESLint 설정
├── .prettierrc           # Prettier 설정
├── jest.config.js        # Jest 설정
├── package.json          # 프로젝트 메타데이터
├── README.md             # 프로젝트 소개
└── docker-compose.yml    # Docker Compose 설정
```

## 코딩 표준

### JavaScript/TypeScript 표준
- ES6+ 문법 사용
- 명시적인 타입 선언 (TypeScript)
- 함수형 프로그래밍 패턴 권장
- 비동기 코드에는 async/await 사용

### 코드 포맷팅
- 들여쓰기: 2 또는 4 스페이스
- 세미콜론: 사용
- 문자열: 작은따옴표 사용
- 최대 줄 길이: 100자

### 네이밍 컨벤션
- 변수 및 함수: camelCase
- 클래스: PascalCase
- 상수: UPPER_SNAKE_CASE
- 컴포넌트 파일: PascalCase.jsx 또는 PascalCase.tsx
- 유틸리티 파일: camelCase.js 또는 camelCase.ts

### 컴포넌트 설계
- 재사용 가능한 컴포넌트 작성
- Prop 타입 검증 (PropTypes 또는 TypeScript 인터페이스)
- 관심사 분리 원칙 준수
- 상태 관리는 필요한 최상위 레벨에서만 수행

## Git 워크플로우

### 브랜치 전략
- `main`: 프로덕션 코드
- `develop`: 개발 중인 코드
- `feature/*`: 새로운 기능 개발
- `bugfix/*`: 버그 수정
- `hotfix/*`: 긴급 프로덕션 수정

### 커밋 메시지 규칙
```
<타입>(<범위>): <제목>

<본문>

<푸터>
```

타입:
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 포맷팅, 세미콜론 누락 등
- `refactor`: 코드 리팩토링
- `test`: 테스트 추가 또는 수정
- `chore`: 빌드 프로세스, 도구 변경 등

예시:
```
feat(auth): 사용자 로그인 기능 구현

- OAuth2 인증 추가
- 로그인 상태 유지 기능 구현
- 세션 관리 로직 개선

Closes #123
```

### Pull Request (PR) 프로세스
1. 기능 브랜치 생성 및 작업
2. 테스트 작성 및 통과 확인
3. PR 생성 및 설명 작성
4. 코드 리뷰 요청
5. 피드백 수정
6. 승인 후 머지

## 테스트

### 테스트 유형
- 단위 테스트: 개별 함수 및 컴포넌트 테스트
- 통합 테스트: 여러 컴포넌트 또는 서비스 간의 상호작용 테스트
- E2E 테스트: 사용자 시나리오를 시뮬레이션하는 테스트

### 테스트 실행
```bash
# 모든 테스트 실행
npm test

# 특정 테스트 파일 실행
npm test -- path/to/test.js

# 테스트 커버리지 보고서 생성
npm test -- --coverage
```

### 테스트 작성 가이드라인
- 각 기능마다 최소 하나의 테스트 작성
- 테스트 이름은 명확하게 작성 (`it should...`)
- 테스트 간에 상태가 공유되지 않도록 설계
- Mocking을 통한 의존성 격리

## 문서화

### 코드 문서화
- JSDoc 스타일 주석 사용
- 복잡한 함수는 입/출력 파라미터 및 예외 사항 문서화
- 핵심 비즈니스 로직에 주석 추가

예시:
```javascript
/**
 * 사용자 인증을 처리합니다.
 * @param {string} username - 사용자 아이디
 * @param {string} password - 사용자 비밀번호
 * @returns {Promise<Object>} 인증된 사용자 정보와 토큰
 * @throws {AuthError} 인증 실패 시 발생
 */
async function authenticateUser(username, password) {
  // 로직...
}
```

### API 문서화
- OpenAPI (Swagger) 명세 사용
- 각 엔드포인트별 요청/응답 형식 문서화
- 인증 요구사항 명시

## 배포 준비

### 빌드 프로세스
```bash
# 프로덕션 빌드
npm run build

# 빌드 산출물 확인
ls -la dist/
```

### 코드 품질 검사
```bash
# 린트 검사
npm run lint

# 타입 검사 (TypeScript)
npm run type-check
```

### 성능 최적화
- 번들 크기 분석
- 지연 로딩 구현
- 이미지 최적화
- 캐싱 전략 설정

---

문서 버전: 1.0.0  
최종 업데이트: 2025-03-01
