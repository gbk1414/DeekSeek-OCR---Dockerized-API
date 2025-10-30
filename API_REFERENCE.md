# DeepSeek-OCR API Reference

이 문서는 DeepSeek-OCR Dockerized API의 전체 REST API 엔드포인트를 설명합니다.

## 📋 목차

- [개요](#개요)
- [인증](#인증)
- [기본 URL](#기본-url)
- [응답 형식](#응답-형식)
- [엔드포인트](#엔드포인트)
  - [Health Check](#health-check)
  - [이미지 OCR](#이미지-ocr)
  - [PDF OCR](#pdf-ocr)
  - [배치 처리](#배치-처리)
- [프롬프트 가이드](#프롬프트-가이드)
- [에러 처리](#에러-처리)
- [사용 예제](#사용-예제)

---

## 개요

DeepSeek-OCR API는 GPU 가속 OCR 서비스로, 이미지와 PDF 문서를 마크다운 형식으로 변환합니다. vLLM 백엔드를 사용하여 고성능 처리를 제공합니다.

**주요 기능:**
- 단일 이미지 OCR 처리
- 다중 페이지 PDF 처리
- 배치 파일 처리
- 사용자 정의 프롬프트 지원
- 레이아웃 인식 문서 변환

**기술 스택:**
- FastAPI
- vLLM (GPU 가속)
- DeepSeek-OCR 모델
- PyMuPDF (PDF 처리)

---

## 인증

현재 버전은 인증을 요구하지 않습니다. 프로덕션 환경에서는 API 키 또는 OAuth2 인증 추가를 권장합니다.

---

## 기본 URL

```
http://localhost:8000
```

원격 서버의 경우:
```
https://your-domain.com
```

---

## 응답 형식

모든 API 응답은 JSON 형식입니다.

### OCRResponse (단일 이미지)

```json
{
  "success": true,
  "result": "마크다운 형식의 OCR 결과...",
  "error": null,
  "page_count": 1
}
```

### BatchOCRResponse (PDF)

```json
{
  "success": true,
  "results": [
    {
      "success": true,
      "result": "페이지 1 OCR 결과...",
      "error": null,
      "page_count": 1
    },
    {
      "success": true,
      "result": "페이지 2 OCR 결과...",
      "error": null,
      "page_count": 2
    }
  ],
  "total_pages": 2,
  "filename": "document.pdf"
}
```

---

## 엔드포인트

### Health Check

#### GET `/`

서버 상태 확인 (간단)

**요청:**
```bash
curl http://localhost:8000/
```

**응답:**
```json
{
  "message": "DeepSeek-OCR API is running",
  "status": "healthy"
}
```

---

#### GET `/health`

서버 상태 상세 확인

**요청:**
```bash
curl http://localhost:8000/health
```

**응답:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_path": "/app/models/deepseek-ai/DeepSeek-OCR",
  "cuda_available": true,
  "cuda_device_count": 1
}
```

**응답 필드:**
- `status`: 서버 상태 (`healthy` 또는 `unhealthy`)
- `model_loaded`: 모델 로드 여부
- `model_path`: 모델 경로
- `cuda_available`: CUDA(GPU) 사용 가능 여부
- `cuda_device_count`: 사용 가능한 GPU 수

---

### 이미지 OCR

#### POST `/ocr/image`

단일 이미지 파일을 OCR 처리합니다.

**요청 파라미터:**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `file` | File | ✅ | 이미지 파일 (JPG, PNG, JPEG 등) |
| `prompt` | string | ❌ | 사용자 정의 프롬프트 (기본값: `<image>\n<|grounding|>Convert the document to markdown.`) |

**요청 예제:**

```bash
# 기본 프롬프트 사용
curl -X POST "http://localhost:8000/ocr/image" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document_page1.jpg"

# 사용자 정의 프롬프트
curl -X POST "http://localhost:8000/ocr/image" \
  -F "file=@receipt.jpg" \
  -F "prompt=<image>\n<|grounding|>Extract all text and numbers from this receipt."
```

**Python 예제:**

```python
import requests

url = "http://localhost:8000/ocr/image"

# 기본 프롬프트
with open("image.jpg", "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)
    print(response.json())

# 사용자 정의 프롬프트
with open("image.jpg", "rb") as f:
    files = {"file": f}
    data = {"prompt": "<image>\nFree OCR."}
    response = requests.post(url, files=files, data=data)
    print(response.json())
```

**응답:**

```json
{
  "success": true,
  "result": "# Document Title\n\nThis is the extracted content...",
  "error": null,
  "page_count": 1
}
```

**지원 이미지 형식:**
- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff, .tif)
- GIF (.gif)

---

### PDF OCR

#### POST `/ocr/pdf`

PDF 파일의 모든 페이지를 OCR 처리합니다.

**요청 파라미터:**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `file` | File | ✅ | PDF 파일 |
| `prompt` | string | ❌ | 사용자 정의 프롬프트 (모든 페이지에 적용) |

**요청 예제:**

```bash
# 기본 프롬프트 사용
curl -X POST "http://localhost:8000/ocr/pdf" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"

# 사용자 정의 프롬프트
curl -X POST "http://localhost:8000/ocr/pdf" \
  -F "file=@tables.pdf" \
  -F "prompt=<image>\n<|grounding|>Extract all tables as markdown tables."
```

**Python 예제:**

```python
import requests

url = "http://localhost:8000/ocr/pdf"

# 기본 프롬프트
with open("document.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)
    result = response.json()

    # 각 페이지 결과 출력
    for page in result["results"]:
        if page["success"]:
            print(f"=== Page {page['page_count']} ===")
            print(page["result"])
        else:
            print(f"Page {page['page_count']} failed: {page['error']}")

# 사용자 정의 프롬프트
with open("document.pdf", "rb") as f:
    files = {"file": f}
    data = {"prompt": "<image>\nFree OCR."}
    response = requests.post(url, files=files, data=data)
    print(response.json())
```

**응답:**

```json
{
  "success": true,
  "results": [
    {
      "success": true,
      "result": "# Page 1 Content\n\nFirst page text...",
      "error": null,
      "page_count": 1
    },
    {
      "success": true,
      "result": "# Page 2 Content\n\nSecond page text...",
      "error": null,
      "page_count": 2
    }
  ],
  "total_pages": 2,
  "filename": "document.pdf"
}
```

**처리 설정:**
- DPI: 144 (기본값)
- 각 페이지는 순차적으로 처리됩니다
- 대용량 PDF의 경우 처리 시간이 오래 걸릴 수 있습니다

---

### 배치 처리

#### POST `/ocr/batch`

여러 파일(이미지 및 PDF)을 한 번에 처리합니다.

**요청 파라미터:**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `files` | File[] | ✅ | 여러 파일 (이미지 및/또는 PDF) |
| `prompt` | string | ❌ | 사용자 정의 프롬프트 (모든 파일에 적용) |

**요청 예제:**

```bash
# 여러 파일 처리
curl -X POST "http://localhost:8000/ocr/batch" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@image1.jpg" \
  -F "files=@document.pdf" \
  -F "files=@image2.png"

# 사용자 정의 프롬프트
curl -X POST "http://localhost:8000/ocr/batch" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "prompt=<image>\nFree OCR."
```

**Python 예제:**

```python
import requests

url = "http://localhost:8000/ocr/batch"

# 여러 파일 열기
files_to_process = [
    ("files", ("image1.jpg", open("image1.jpg", "rb"), "image/jpeg")),
    ("files", ("document.pdf", open("document.pdf", "rb"), "application/pdf")),
    ("files", ("image2.png", open("image2.png", "rb"), "image/png"))
]

response = requests.post(url, files=files_to_process)
result = response.json()

# 결과 확인
if result["success"]:
    for item in result["results"]:
        print(f"\n=== {item['filename']} ===")
        if item["result"]["success"]:
            # 이미지인 경우
            if "result" in item["result"] and isinstance(item["result"]["result"], str):
                print(item["result"]["result"])
            # PDF인 경우
            elif "results" in item["result"]:
                for page in item["result"]["results"]:
                    print(f"Page {page['page_count']}: {page['result'][:100]}...")

# 파일 닫기
for _, (_, file_obj, _) in files_to_process:
    file_obj.close()
```

**응답:**

```json
{
  "success": true,
  "results": [
    {
      "filename": "image1.jpg",
      "result": {
        "success": true,
        "result": "OCR result for image1...",
        "error": null,
        "page_count": 1
      }
    },
    {
      "filename": "document.pdf",
      "result": {
        "success": true,
        "results": [
          {
            "success": true,
            "result": "Page 1 content...",
            "error": null,
            "page_count": 1
          }
        ],
        "total_pages": 1,
        "filename": "document.pdf"
      }
    }
  ]
}
```

**참고:**
- 배치 처리는 순차적으로 진행됩니다
- 하나의 파일이 실패해도 나머지 파일은 계속 처리됩니다
- 대용량 파일이 많은 경우 타임아웃에 주의하세요

---

## 프롬프트 가이드

DeepSeek-OCR는 특수 토큰을 지원하는 프롬프트 시스템을 사용합니다.

### 필수 토큰

- `<image>` - 모든 프롬프트의 시작 부분에 필수

### 선택적 토큰

- `<|grounding|>` - 레이아웃 인식 처리 활성화 (문서 구조 보존)
- `<|ref|>...<|/ref|>` - 이미지 내 특정 텍스트 위치 지정

### 일반적인 프롬프트 패턴

#### 1. 문서를 마크다운으로 변환 (기본값)

```
<image>
<|grounding|>Convert the document to markdown.
```

**용도:** 문서의 레이아웃과 구조를 보존하면서 마크다운으로 변환

**결과 예시:**
```markdown
# Document Title

## Section 1

This is paragraph text...

- Bullet point 1
- Bullet point 2

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
```

---

#### 2. 순수 OCR (마크다운 없음)

```
<image>
Free OCR.
```

**용도:** 포맷팅 없이 순수 텍스트만 추출

**결과 예시:**
```
Document Title
Section 1
This is paragraph text...
Bullet point 1
Bullet point 2
Column 1 Column 2
Data 1 Data 2
```

---

#### 3. 이미지 OCR (문서가 아닌 일반 이미지)

```
<image>
<|grounding|>OCR this image.
```

**용도:** 사진, 스크린샷 등 일반 이미지의 텍스트 추출

---

#### 4. 표 추출

```
<image>
<|grounding|>Extract all tables as markdown tables.
```

**용도:** 문서 내 표를 마크다운 표 형식으로 추출

---

#### 5. 그림/차트 분석

```
<image>
Parse the figure.
```

**용도:** 그림, 차트, 다이어그램의 내용 분석

---

#### 6. 이미지 상세 설명

```
<image>
Describe this image in detail.
```

**용도:** 이미지의 전반적인 내용 설명

---

#### 7. 특정 텍스트 위치 찾기

```
<image>
Locate <|ref|>특정 텍스트<|/ref|> in the image.
```

**용도:** 이미지 내 특정 텍스트의 위치 확인

---

### 프롬프트 작성 팁

1. **항상 `<image>`로 시작**: 이 토큰은 필수입니다
2. **레이아웃 보존이 필요한 경우 `<|grounding|>` 사용**: 문서 구조가 중요한 경우
3. **명확한 지시**: 원하는 출력 형식을 명확히 기술
4. **언어 지원**: 한국어, 영어 등 다양한 언어 지원

---

## 에러 처리

### 일반적인 에러 응답

**실패한 요청:**

```json
{
  "success": false,
  "result": null,
  "error": "Error message describing what went wrong",
  "page_count": null
}
```

### HTTP 상태 코드

| 코드 | 설명 |
|------|------|
| 200 | 성공 (에러가 있어도 `success: false`로 표시될 수 있음) |
| 422 | 유효성 검증 실패 (파일 형식 오류 등) |
| 500 | 서버 내부 오류 |
| 503 | 서비스 사용 불가 (모델 로드 실패 등) |

### 일반적인 에러 시나리오

#### 1. 모델이 로드되지 않음

```json
{
  "detail": "Model not loaded"
}
```

**해결 방법:**
- `/health` 엔드포인트로 모델 상태 확인
- Docker 로그 확인: `docker-compose logs -f deepseek-ocr`

#### 2. 파일 형식 오류

```json
{
  "success": false,
  "error": "Cannot identify image file"
}
```

**해결 방법:**
- 지원되는 이미지 형식 확인 (JPG, PNG, etc.)
- 파일이 손상되지 않았는지 확인

#### 3. GPU 메모리 부족

```json
{
  "success": false,
  "error": "CUDA out of memory"
}
```

**해결 방법:**
- `MAX_CONCURRENCY` 설정 감소
- `GPU_MEMORY_UTILIZATION` 감소
- 다른 GPU 프로세스 종료

#### 4. 타임아웃

클라이언트 측 타임아웃 에러

**해결 방법:**
- 클라이언트 타임아웃 설정 증가
- 대용량 파일은 작은 파일로 분할
- 서버 성능 확인

---

## 사용 예제

### 1. Python 클라이언트 클래스

```python
import requests
from typing import List, Optional, Dict, Any

class DeepSeekOCRClient:
    """DeepSeek-OCR API 클라이언트"""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 300):
        """
        클라이언트 초기화

        Args:
            base_url: API 서버 URL
            timeout: 요청 타임아웃 (초)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def health_check(self) -> Dict[str, Any]:
        """서버 상태 확인"""
        response = requests.get(f"{self.base_url}/health", timeout=10)
        return response.json()

    def process_image(
        self,
        image_path: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        이미지 OCR 처리

        Args:
            image_path: 이미지 파일 경로
            prompt: 사용자 정의 프롬프트 (선택사항)

        Returns:
            OCR 결과 딕셔너리
        """
        with open(image_path, 'rb') as f:
            files = {"file": f}
            data = {"prompt": prompt} if prompt else {}
            response = requests.post(
                f"{self.base_url}/ocr/image",
                files=files,
                data=data,
                timeout=self.timeout
            )
        return response.json()

    def process_pdf(
        self,
        pdf_path: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        PDF OCR 처리

        Args:
            pdf_path: PDF 파일 경로
            prompt: 사용자 정의 프롬프트 (선택사항)

        Returns:
            OCR 결과 딕셔너리
        """
        with open(pdf_path, 'rb') as f:
            files = {"file": f}
            data = {"prompt": prompt} if prompt else {}
            response = requests.post(
                f"{self.base_url}/ocr/pdf",
                files=files,
                data=data,
                timeout=self.timeout
            )
        return response.json()

    def process_batch(
        self,
        file_paths: List[str],
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        배치 파일 처리

        Args:
            file_paths: 파일 경로 리스트
            prompt: 사용자 정의 프롬프트 (선택사항)

        Returns:
            OCR 결과 딕셔너리
        """
        files = []
        file_objects = []

        try:
            for path in file_paths:
                f = open(path, 'rb')
                file_objects.append(f)
                files.append(("files", f))

            data = {"prompt": prompt} if prompt else {}
            response = requests.post(
                f"{self.base_url}/ocr/batch",
                files=files,
                data=data,
                timeout=self.timeout
            )
            return response.json()

        finally:
            # 파일 닫기
            for f in file_objects:
                f.close()


# 사용 예제
if __name__ == "__main__":
    client = DeepSeekOCRClient()

    # Health check
    health = client.health_check()
    print(f"Server status: {health['status']}")
    print(f"Model loaded: {health['model_loaded']}")

    # 이미지 처리
    result = client.process_image("document.jpg")
    if result["success"]:
        print("Image OCR Result:")
        print(result["result"])

    # PDF 처리 (사용자 정의 프롬프트)
    result = client.process_pdf(
        "document.pdf",
        prompt="<image>\nFree OCR."
    )
    if result["success"]:
        for page in result["results"]:
            print(f"\n=== Page {page['page_count']} ===")
            print(page["result"])

    # 배치 처리
    result = client.process_batch([
        "image1.jpg",
        "document.pdf",
        "image2.png"
    ])
    print(f"Batch processing: {len(result['results'])} files processed")
```

---

### 2. JavaScript/Node.js 클라이언트

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

class DeepSeekOCRClient {
    constructor(baseUrl = 'http://localhost:8000', timeout = 300000) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.timeout = timeout;
    }

    async healthCheck() {
        const response = await axios.get(`${this.baseUrl}/health`, {
            timeout: 10000
        });
        return response.data;
    }

    async processImage(imagePath, prompt = null) {
        const formData = new FormData();
        formData.append('file', fs.createReadStream(imagePath));
        if (prompt) {
            formData.append('prompt', prompt);
        }

        const response = await axios.post(
            `${this.baseUrl}/ocr/image`,
            formData,
            {
                headers: formData.getHeaders(),
                timeout: this.timeout
            }
        );
        return response.data;
    }

    async processPDF(pdfPath, prompt = null) {
        const formData = new FormData();
        formData.append('file', fs.createReadStream(pdfPath));
        if (prompt) {
            formData.append('prompt', prompt);
        }

        const response = await axios.post(
            `${this.baseUrl}/ocr/pdf`,
            formData,
            {
                headers: formData.getHeaders(),
                timeout: this.timeout
            }
        );
        return response.data;
    }

    async processBatch(filePaths, prompt = null) {
        const formData = new FormData();

        filePaths.forEach(path => {
            formData.append('files', fs.createReadStream(path));
        });

        if (prompt) {
            formData.append('prompt', prompt);
        }

        const response = await axios.post(
            `${this.baseUrl}/ocr/batch`,
            formData,
            {
                headers: formData.getHeaders(),
                timeout: this.timeout
            }
        );
        return response.data;
    }
}

// 사용 예제
(async () => {
    const client = new DeepSeekOCRClient();

    // Health check
    const health = await client.healthCheck();
    console.log(`Server status: ${health.status}`);

    // 이미지 처리
    const imageResult = await client.processImage('document.jpg');
    if (imageResult.success) {
        console.log('Image OCR Result:', imageResult.result);
    }

    // PDF 처리
    const pdfResult = await client.processPDF('document.pdf');
    if (pdfResult.success) {
        pdfResult.results.forEach(page => {
            console.log(`\n=== Page ${page.page_count} ===`);
            console.log(page.result);
        });
    }
})();
```

---

### 3. cURL 고급 예제

#### 이미지 처리 후 결과를 파일로 저장

```bash
curl -X POST "http://localhost:8000/ocr/image" \
  -F "file=@document.jpg" \
  | jq -r '.result' > output.md
```

#### PDF 처리 후 각 페이지를 별도 파일로 저장

```bash
# PDF 처리
response=$(curl -s -X POST "http://localhost:8000/ocr/pdf" \
  -F "file=@document.pdf")

# jq로 각 페이지 추출
echo "$response" | jq -r '.results[] | "=== Page \(.page_count) ===\n\(.result)\n"' > output.md
```

#### 배치 처리

```bash
curl -X POST "http://localhost:8000/ocr/batch" \
  -F "files=@image1.jpg" \
  -F "files=@document.pdf" \
  -F "files=@image2.png" \
  -F "prompt=<image>\nFree OCR." \
  | jq '.'
```

---

### 4. OpenAPI/Swagger UI

API 서버는 자동으로 생성된 인터랙티브 API 문서를 제공합니다.

**Swagger UI 접속:**
```
http://localhost:8000/docs
```

**ReDoc 접속:**
```
http://localhost:8000/redoc
```

**OpenAPI JSON 스키마:**
```
http://localhost:8000/openapi.json
```

브라우저에서 직접 API를 테스트하고 요청/응답을 확인할 수 있습니다.

---

## 성능 고려사항

### 처리 시간

| 파일 타입 | 평균 처리 시간 |
|-----------|----------------|
| 단일 이미지 (1024x768) | 2-5초 |
| PDF 1페이지 | 3-6초 |
| PDF 10페이지 | 30-60초 |
| PDF 100페이지 | 5-10분 |

*처리 시간은 GPU 성능, 이미지 해상도, 복잡도에 따라 다릅니다.*

### 최적화 팁

1. **GPU 메모리 사용률 조정**
   ```yaml
   # docker-compose.yml
   environment:
     - GPU_MEMORY_UTILIZATION=0.9  # 0.1-1.0
   ```

2. **동시 처리 수 조정**
   ```yaml
   environment:
     - MAX_CONCURRENCY=100  # GPU 메모리에 따라 조정
   ```

3. **대용량 PDF는 분할 처리**
   - 100페이지 이상의 PDF는 작은 파일로 분할
   - 배치 처리로 여러 파일 동시 처리

4. **타임아웃 설정**
   - 클라이언트 타임아웃을 충분히 길게 설정 (5-10분)
   - Nginx 사용 시 `proxy_read_timeout` 증가

---

## 보안 권장사항

### 프로덕션 환경

1. **API 키 인증 추가**
   - FastAPI의 `Depends`로 인증 미들웨어 구현
   - API 키를 환경 변수로 관리

2. **HTTPS 사용**
   - Let's Encrypt로 SSL 인증서 설치
   - Nginx 리버스 프록시 사용

3. **Rate Limiting**
   - Nginx의 `limit_req` 모듈 사용
   - FastAPI-Limiter 라이브러리 사용

4. **파일 크기 제한**
   ```yaml
   # docker-compose.yml
   environment:
     - MAX_FILE_SIZE=100MB
   ```

5. **IP 화이트리스트**
   - Nginx에서 허용된 IP만 접근 허용
   - 방화벽 설정

---

## 문제 해결

### API가 응답하지 않음

```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f deepseek-ocr

# Health check
curl http://localhost:8000/health
```

### 처리가 너무 느림

```bash
# GPU 사용률 확인
nvidia-smi -l 1

# 동시 처리 수 증가 (docker-compose.yml)
MAX_CONCURRENCY=100

# GPU 메모리 사용률 증가
GPU_MEMORY_UTILIZATION=0.95
```

### 메모리 부족 에러

```bash
# 동시 처리 수 감소
MAX_CONCURRENCY=10

# GPU 메모리 사용률 감소
GPU_MEMORY_UTILIZATION=0.7

# 다른 GPU 프로세스 종료
nvidia-smi
kill <PID>
```

---

## 추가 리소스

- [README.md](README.md) - 프로젝트 개요 및 설치 가이드
- [CLAUDE.md](CLAUDE.md) - 개발자 가이드
- [REMOTE_SERVER_GUIDE.md](REMOTE_SERVER_GUIDE.md) - 원격 서버 설정 가이드
- [DeepSeek-OCR GitHub](https://github.com/deepseek-ai/DeepSeek-OCR) - 원본 프로젝트

---

## 변경 이력

### v1.0.0 (2024-01-XX)
- 초기 API 릴리스
- 이미지, PDF, 배치 처리 엔드포인트
- 사용자 정의 프롬프트 지원
- Health check 엔드포인트

---

## 라이선스

이 프로젝트는 DeepSeek-OCR 프로젝트와 동일한 라이선스를 따릅니다.
