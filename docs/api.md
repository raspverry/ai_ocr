# 초고정밀 OCR 시스템 API 문서

## 개요

초고정밀 OCR 시스템은 PDF 및 이미지 파일에서 텍스트를 추출하고 구조화된 데이터를 추출하기 위한 RESTful API를 제공합니다. 이 문서는 API 엔드포인트, 요청 및 응답 형식, 인증 방법에 대한 상세 정보를 제공합니다.

**API 기본 URL**: `http://your-server:8000/api/v1`

## 인증

API 요청에는 API 키 인증이 필요합니다. API 키는 HTTP 헤더에 포함해야 합니다.

```
X-API-Key: your_api_key
```

API 키는 관리자에게 문의하여 발급받을 수 있습니다.

## 주요 엔드포인트

### 1. OCR 처리

#### POST /ocr

PDF 또는 이미지 파일을 업로드하여 OCR 처리를 요청합니다.

**요청**

- `multipart/form-data` 형식으로 요청
- 파일과 옵션 파라미터 포함

**파라미터**

| 이름 | 유형 | 필수 | 설명 |
|------|------|------|------|
| file | File | 예 | PDF 또는 이미지 파일 (지원 형식: PDF, JPG, JPEG, PNG, TIFF, BMP, GIF) |
| options | JSON 문자열 | 아니오 | OCR 처리 옵션 (아래 참조) |

**옵션 JSON 예시**

```json
{
  "language": "jpn",
  "extract_entities": true,
  "use_cache": true,
  "return_images": false
}
```

**옵션 설명**

| 옵션 | 유형 | 기본값 | 설명 |
|------|------|--------|------|
| language | 문자열 | null | 언어 코드 (null: 자동 감지, 지원 언어: jpn, eng, kor, chi_sim, chi_tra) |
| extract_entities | 불리언 | true | 엔티티(회사명, 날짜, 금액 등) 추출 여부 |
| use_cache | 불리언 | true | 캐시 사용 여부 |
| return_images | 불리언 | false | 이미지 데이터 반환 여부 (base64 인코딩) |

**응답**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing"
}
```

### 2. OCR 결과 조회

#### GET /ocr/{task_id}

OCR 작업의 결과 또는 현재 상태를 조회합니다.

**파라미터**

| 이름 | 위치 | 유형 | 필수 | 설명 |
|------|------|------|------|------|
| task_id | Path | 문자열 | 예 | OCR 작업 ID |

**응답 (처리 중)**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing"
}
```

**응답 (완료)**

```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "example.pdf",
  "file_type": ".pdf",
  "text": "추출된 전체 텍스트...",
  "confidence": 0.95,
  "language": "jpn",
  "pages": [
    {
      "page_num": 1,
      "text": "페이지 1 텍스트...",
      "language": "jpn",
      "confidence": 0.96,
      "orientation": 0,
      "special_items": {
        "has_stamps": true,
        "has_handwriting": false,
        "has_table": true,
        "has_strikethrough": false,
        "regions": [...]
      },
      "entities": {...}
    },
    // 추가 페이지...
  ],
  "entities": {
    "companies": ["주식회사 A", "株式会社 B"],
    "dates": ["2023-01-15", "2023年02月20日"],
    "amounts": ["¥100,000", "¥50,000"],
    // 추가 엔티티...
  },
  "process_time": 5.43
}
```

**응답 (오류)**

```json
{
  "status": "error",
  "error": "오류 메시지"
}
```

### 3. 데이터 추출

#### POST /extraction/{task_id}

OCR 결과에서 구조화된 데이터 추출을 요청합니다.

**파라미터**

| 이름 | 위치 | 유형 | 필수 | 설명 |
|------|------|------|------|------|
| task_id | Path | 문자열 | 예 | OCR 작업 ID |
| options | Form | JSON 문자열 | 아니오 | 추출 옵션 |

**옵션 JSON 예시**

```json
{
  "fields": [
    {
      "name": "invoice_number",
      "type": "text",
      "context": "청구서 번호|請求書番号",
      "regex": "(\\d{1,3}[\\-\\.]\\d{1,3}[\\-\\.]\\d{1,5})"
    },
    {
      "name": "date",
      "type": "date",
      "context": "날짜|発行日|日付",
      "regex": "(\\d{4}[-/年\\.]{1,2}\\d{1,2}[-/月\\.]{1,2}\\d{1,2}[日]?)"
    },
    {
      "name": "total_amount",
      "type": "amount",
      "context": "총액|合計|総額",
      "regex": "([¥￥]?\\s*[\\d,\\.]+\\s*[円]?)"
    }
  ],
  "language": "jpn"
}
```

**응답**

```json
{
  "task_id": "660f9500-e29b-41d4-a716-446655440000",
  "status": "processing"
}
```

### 4. 데이터 추출 결과 조회

#### GET /extraction/{task_id}

데이터 추출 작업의 결과 또는 현재 상태를 조회합니다.

**파라미터**

| 이름 | 위치 | 유형 | 필수 | 설명 |
|------|------|------|------|------|
| task_id | Path | 문자열 | 예 | 추출 작업 ID |

**응답 (완료)**

```json
{
  "ocr_task_id": "550e8400-e29b-41d4-a716-446655440000",
  "fields": {
    "invoice_number": "A-123-45678",
    "date": "2023-01-15",
    "total_amount": 100000,
    "company_name": "주식회사 A",
    "tax_amount": 10000
  },
  "confidence": {
    "invoice_number": 0.95,
    "date": 0.98,
    "total_amount": 0.92,
    "company_name": 0.88,
    "tax_amount": 0.90
  },
  "language": "jpn",
  "process_time": 2.31
}
```

### 5. CSV 내보내기

#### GET /extraction/{task_id}/csv

데이터 추출 결과를 CSV 형식으로 내보냅니다.

**파라미터**

| 이름 | 위치 | 유형 | 필수 | 설명 |
|------|------|------|------|------|
| task_id | Path | 문자열 | 예 | 추출 작업 ID |

**응답**

CSV 파일 다운로드 (Content-Type: text/csv)

### 6. 필드 설정 조회

#### GET /fields

추출 필드 설정을 조회합니다.

**응답**

```json
{
  "fields": [
    {
      "name": "invoice_number",
      "type": "text",
      "context": "청구서 번호|請求書番号|インボイス番号|No.|番号",
      "regex": "(\\d{1,3}[\\-\\.]\\d{1,3}[\\-\\.]\\d{1,5})"
    },
    // 추가 필드...
  ]
}
```

### 7. 필드 설정 업데이트

#### POST /fields

추출 필드 설정을 업데이트합니다.

**요청 본문**

```json
[
  {
    "name": "invoice_number",
    "type": "text",
    "context": "청구서 번호|請求書番号|インボイス番号|No.|番号",
    "regex": "(\\d{1,3}[\\-\\.]\\d{1,3}[\\-\\.]\\d{1,5})"
  },
  {
    "name": "new_field",
    "type": "text",
    "context": "새 필드|新しいフィールド",
    "regex": "(.*)"
  }
]
```

**응답**

```json
{
  "success": true,
  "count": 2
}
```

### 8. 지원 언어 조회

#### GET /languages

지원되는 언어 목록을 조회합니다.

**응답**

```json
{
  "languages": {
    "jpn": "일본어",
    "eng": "영어",
    "kor": "한국어",
    "chi_sim": "중국어 간체",
    "chi_tra": "중국어 번체"
  }
}
```

### 9. 시스템 상태 확인

#### GET /health

시스템 상태를 확인합니다.

**응답**

```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": 1645678901,
  "redis": "ok",
  "engines": {
    "custom_model": true,
    "tesseract": true,
    "google_vision": false,
    "azure_form": false
  }
}
```

## 오류 코드

| 코드 | 설명 |
|------|------|
| 400 | 잘못된 요청 (요청 파라미터 오류) |
| 401 | 인증 실패 (API 키 오류) |
| 403 | 권한 없음 |
| 404 | 리소스 찾을 수 없음 |
| 413 | 요청 엔티티가 너무 큼 (파일 크기 초과) |
| 415 | 지원하지 않는 미디어 타입 (파일 형식 오류) |
| 429 | 요청이 너무 많음 (비율 제한 초과) |
| 500 | 내부 서버 오류 |
| 503 | 서비스 사용 불가 (작업 큐 연결 오류) |

## 클라이언트 예제

### Python

```python
import requests
import json

API_URL = "http://your-server:8000/api/v1"
API_KEY = "your_api_key"

headers = {
    "X-API-Key": API_KEY
}

# OCR 처리 요청
def process_document(file_path, options=None):
    url = f"{API_URL}/ocr"
    
    files = {
        "file": open(file_path, "rb")
    }
    
    data = {}
    if options:
        data["options"] = json.dumps(options)
    
    response = requests.post(url, files=files, data=data, headers=headers)
    return response.json()

# OCR 결과 조회
def get_ocr_result(task_id):
    url = f"{API_URL}/ocr/{task_id}"
    response = requests.get(url, headers=headers)
    return response.json()

# 데이터 추출 요청
def extract_data(ocr_task_id, fields=None):
    url = f"{API_URL}/extraction/{ocr_task_id}"
    
    data = {}
    if fields:
        data["options"] = json.dumps({"fields": fields})
    
    response = requests.post(url, data=data, headers=headers)
    return response.json()

# 데이터 추출 결과 CSV 다운로드
def download_csv(task_id, output_path):
    url = f"{API_URL}/extraction/{task_id}/csv"
    response = requests.get(url, headers=headers)
    
    with open(output_path, "wb") as f:
        f.write(response.content)
    
    return output_path
```

### JavaScript

```javascript
const API_URL = "http://your-server:8000/api/v1";
const API_KEY = "your_api_key";

// OCR 처리 요청
async function processDocument(file, options = {}) {
  const formData = new FormData();
  formData.append("file", file);
  
  if (Object.keys(options).length > 0) {
    formData.append("options", JSON.stringify(options));
  }
  
  const response = await fetch(`${API_URL}/ocr`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY
    },
    body: formData
  });
  
  return await response.json();
}

// OCR 결과 조회
async function getOcrResult(taskId) {
  const response = await fetch(`${API_URL}/ocr/${taskId}`, {
    headers: {
      "X-API-Key": API_KEY
    }
  });
  
  return await response.json();
}

// 데이터 추출 요청
async function extractData(ocrTaskId, fields = null) {
  const formData = new FormData();
  
  if (fields) {
    formData.append("options", JSON.stringify({ fields }));
  }
  
  const response = await fetch(`${API_URL}/extraction/${ocrTaskId}`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY
    },
    body: formData
  });
  
  return await response.json();
}

// 데이터 추출 결과 CSV 다운로드
async function downloadCsv(taskId) {
  const response = await fetch(`${API_URL}/extraction/${taskId}/csv`, {
    headers: {
      "X-API-Key": API_KEY
    }
  });
  
  const blob = await response.blob();
  return blob;
}
```

## 제한 사항

1. 최대 파일 크기: 20MB
2. 최대 PDF 페이지 수: 100페이지
3. 최대 요청 수: 분당 100회 (API 키 기준)
4. 작업 타임아웃: 1시간

## 지원 및 문의

API 사용 중 문제가 발생하면 GitHub 이슈를 통해 문의하거나 support@ocr-service.com으로 이메일을 보내주세요.
