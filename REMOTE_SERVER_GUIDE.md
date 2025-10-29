# 원격 서버 사용 가이드 (Remote Server Setup Guide)

이 가이드는 DeepSeek-OCR Docker 서비스를 원격 서버에 배포하고, 로컬 PC에서 파일을 전송하여 OCR 처리 결과를 받는 방법을 설명합니다.

---

## 📋 목차

1. [아키텍처 개요](#아키텍처-개요)
2. [원격 서버 설정](#원격-서버-설정)
3. [로컬 클라이언트 설정](#로컬-클라이언트-설정)
4. [사용 예제](#사용-예제)
5. [보안 설정](#보안-설정)
6. [문제 해결](#문제-해결)

---

## 아키텍처 개요

```
┌─────────────────┐                    ┌──────────────────┐
│   로컬 PC       │                    │   원격 서버       │
│                 │                    │                  │
│  ┌───────────┐  │                    │  ┌────────────┐  │
│  │ PDF/Image │  │   HTTPS/HTTP       │  │   Docker   │  │
│  │  Files    │──┼───────────────────>│  │ DeepSeek   │  │
│  └───────────┘  │                    │  │    OCR     │  │
│                 │                    │  └────────────┘  │
│  ┌───────────┐  │   OCR Results      │       │         │
│  │ Markdown  │<─┼────────────────────│  ┌────▼──────┐  │
│  │  Results  │  │                    │  │   GPU     │  │
│  └───────────┘  │                    │  │  (NVIDIA) │  │
│                 │                    │  └───────────┘  │
│  remote_ocr_    │                    │                 │
│  client.py      │                    │  FastAPI:8000  │
└─────────────────┘                    └──────────────────┘
```

---

## 원격 서버 설정

### 1. 서버 요구사항

**하드웨어**:
- NVIDIA GPU (최소 12GB VRAM, 권장 16GB+)
- 시스템 RAM: 32GB 이상
- 스토리지: 50GB 이상

**소프트웨어**:
- Ubuntu 20.04+ / CentOS 8+
- Docker 20.10+
- Docker Compose 2.0+
- NVIDIA Container Toolkit
- NVIDIA Drivers (CUDA 11.8+ 지원)

### 2. Docker 서비스 설치

서버에 SSH로 접속한 후:

```bash
# 1. 저장소 클론
git clone https://github.com/your-repo/DeepSeek-OCR-Dockerized-API.git
cd DeepSeek-OCR-Dockerized-API

# 2. 모델 다운로드
mkdir -p models
huggingface-cli download deepseek-ai/DeepSeek-OCR \
    --local-dir models/deepseek-ai/DeepSeek-OCR

# 3. Docker 이미지 빌드
docker-compose build

# 4. 서비스 시작
docker-compose up -d

# 5. 상태 확인
docker-compose logs -f deepseek-ocr
curl http://localhost:8000/health
```

### 3. 외부 접근 설정

#### Option A: 방화벽 포트 개방 (간단한 방법)

```bash
# 방화벽에서 8000 포트 개방
sudo ufw allow 8000/tcp

# 또는 iptables 사용
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
```

**docker-compose.yml 수정**:
```yaml
services:
  deepseek-ocr:
    ports:
      - "0.0.0.0:8000:8000"  # 모든 인터페이스에서 접근 허용
```

**재시작**:
```bash
docker-compose down
docker-compose up -d
```

**테스트**:
```bash
# 서버의 외부 IP를 확인
curl ifconfig.me

# 로컬 PC에서 접속 테스트
curl http://YOUR_SERVER_IP:8000/health
```

#### Option B: Nginx 리버스 프록시 (권장 - HTTPS 지원)

**Nginx 설치**:
```bash
sudo apt-get update
sudo apt-get install nginx certbot python3-certbot-nginx
```

**Nginx 설정** (`/etc/nginx/sites-available/deepseek-ocr`):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 파일 업로드 크기 제한 증가 (PDF 처리용)
    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 타임아웃 설정 (OCR 처리 시간 고려)
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
}
```

**Nginx 활성화**:
```bash
sudo ln -s /etc/nginx/sites-available/deepseek-ocr /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**SSL 인증서 설치 (무료 Let's Encrypt)**:
```bash
sudo certbot --nginx -d your-domain.com
```

이제 `https://your-domain.com`으로 접속 가능합니다.

#### Option C: SSH 터널링 (개발/테스트용)

로컬 PC에서 SSH 터널 생성:

```bash
# 로컬의 8000 포트를 원격 서버의 8000 포트로 포워딩
ssh -L 8000:localhost:8000 user@remote-server-ip

# 이제 로컬에서 http://localhost:8000 으로 접속 가능
```

---

## 로컬 클라이언트 설정

### 1. 의존성 설치

로컬 PC에서:

```bash
# Python 패키지 설치
pip install requests pyyaml pillow

# 클라이언트 스크립트 다운로드
# (이미 저장소를 클론한 경우 생략)
```

### 2. 설정 파일 생성

**샘플 설정 파일 생성**:
```bash
python remote_ocr_client.py --create-config
```

**remote_config.yaml 편집**:
```yaml
# 원격 서버 URL (Nginx 사용 시 https, 직접 접근 시 http)
server_url: 'https://your-domain.com'
# server_url: 'http://YOUR_SERVER_IP:8000'

# API 키 (선택사항 - 보안 설정 시)
api_key: null

# 타임아웃 (초)
timeout: 300

# 결과 저장 디렉토리
output_dir: 'ocr_results'

# 기본 프롬프트
default_prompt: '<image>\n<|grounding|>Convert the document to markdown.'

# 출력 파일 접미사
output_suffix: '-OCR'
```

---

## 사용 예제

### 기본 사용법

**1. 단일 PDF 처리**:
```bash
python remote_ocr_client.py \
    --server https://your-domain.com \
    --file document.pdf
```

**2. 여러 파일 처리**:
```bash
python remote_ocr_client.py \
    --server https://your-domain.com \
    --file file1.pdf file2.jpg file3.png
```

**3. 폴더 내 모든 PDF 처리**:
```bash
python remote_ocr_client.py \
    --server https://your-domain.com \
    --folder data/ \
    --pattern "*.pdf"
```

**4. 커스텀 프롬프트 사용**:
```bash
# 일반 OCR (마크다운 변환 없이)
python remote_ocr_client.py \
    --server https://your-domain.com \
    --file document.pdf \
    --prompt "<image>\nFree OCR."

# 표 추출
python remote_ocr_client.py \
    --server https://your-domain.com \
    --file document.pdf \
    --prompt "<image>\n<|grounding|>Extract all tables as markdown."
```

**5. 출력 디렉토리 지정**:
```bash
python remote_ocr_client.py \
    --server https://your-domain.com \
    --file document.pdf \
    --output my_results/
```

### 설정 파일 사용

**remote_config.yaml 생성 후**:
```bash
# 설정 파일의 server_url 사용
python remote_ocr_client.py --file document.pdf

# 특정 설정 파일 사용
python remote_ocr_client.py \
    --config production_config.yaml \
    --file document.pdf
```

### Python 코드에서 사용

```python
from remote_ocr_client import RemoteOCRClient

# 클라이언트 초기화
client = RemoteOCRClient(
    server_url='https://your-domain.com',
    output_dir='results',
    timeout=300
)

# 단일 파일 처리
result = client.process_file('document.pdf')
if result and result['success']:
    output_file = client.save_result(result)
    print(f"Result saved to: {output_file}")

# 배치 처리
stats = client.process_batch([
    'file1.pdf',
    'file2.jpg',
    'file3.png'
])

print(f"Processed: {stats['successful']}/{stats['total']}")
```

---

## 보안 설정

### 1. API 키 인증 추가

**start_server.py 수정** (서버 측):

```python
from fastapi import Header, HTTPException

# API 키 설정
API_KEY = "your-secret-api-key-here"

async def verify_api_key(authorization: str = Header(None)):
    if authorization is None:
        raise HTTPException(status_code=401, detail="API key required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    key = authorization.replace("Bearer ", "")
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return key

# 엔드포인트에 의존성 추가
@app.post("/ocr/pdf")
async def process_pdf_endpoint(
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key)
):
    # ... 기존 코드
```

**클라이언트 사용**:
```bash
python remote_ocr_client.py \
    --server https://your-domain.com \
    --api-key your-secret-api-key-here \
    --file document.pdf
```

또는 **remote_config.yaml**에 추가:
```yaml
api_key: 'your-secret-api-key-here'
```

### 2. IP 화이트리스트 (Nginx)

```nginx
# /etc/nginx/sites-available/deepseek-ocr
server {
    # ... 기존 설정

    # 특정 IP만 허용
    allow 123.123.123.123;  # 허용할 IP
    allow 124.124.0.0/16;   # IP 범위 허용
    deny all;               # 나머지는 거부

    location / {
        # ... 기존 설정
    }
}
```

### 3. Rate Limiting (요청 제한)

**Nginx 설정**:
```nginx
# /etc/nginx/nginx.conf
http {
    # 클라이언트 IP당 분당 10개 요청으로 제한
    limit_req_zone $binary_remote_addr zone=ocr_limit:10m rate=10r/m;

    # ... 기존 설정
}

# /etc/nginx/sites-available/deepseek-ocr
server {
    location / {
        limit_req zone=ocr_limit burst=5 nodelay;
        # ... 기존 설정
    }
}
```

### 4. HTTPS 강제

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    # SSL 인증서
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # ... 나머지 설정
}
```

---

## 문제 해결

### 연결 오류

**증상**: `Cannot connect to server`

**해결**:
```bash
# 1. 서버에서 Docker 컨테이너 상태 확인
docker-compose ps

# 2. 로그 확인
docker-compose logs -f deepseek-ocr

# 3. 방화벽 확인
sudo ufw status
sudo iptables -L -n | grep 8000

# 4. 포트 리스닝 확인
sudo netstat -tlnp | grep 8000

# 5. 서버 health 확인
curl http://localhost:8000/health
```

### 타임아웃 오류

**증상**: `Request timeout`

**해결**:
```bash
# 클라이언트 타임아웃 증가
python remote_ocr_client.py \
    --server https://your-domain.com \
    --file document.pdf \
    --timeout 600  # 10분

# Nginx 타임아웃 증가 (서버 측)
# /etc/nginx/sites-available/deepseek-ocr
location / {
    proxy_read_timeout 600s;
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;
}
```

### 파일 업로드 크기 제한

**증상**: `413 Request Entity Too Large`

**해결 (Nginx)**:
```nginx
# /etc/nginx/sites-available/deepseek-ocr
server {
    client_max_body_size 200M;  # 최대 200MB
    # ...
}
```

```bash
sudo systemctl restart nginx
```

### GPU 메모리 부족

**증상**: 서버 로그에 `CUDA out of memory`

**해결**:
```yaml
# docker-compose.yml
environment:
  - MAX_CONCURRENCY=5      # 동시 처리 수 감소
  - GPU_MEMORY_UTILIZATION=0.7  # GPU 메모리 사용률 감소
```

```bash
docker-compose down
docker-compose up -d
```

### SSL 인증서 오류

**증상**: `SSL certificate verify failed`

**해결**:
```python
# remote_ocr_client.py 에서 SSL 검증 비활성화 (개발 환경만)
response = requests.post(url, files=files, verify=False)
```

또는:
```bash
# Let's Encrypt 인증서 갱신
sudo certbot renew
```

---

## 성능 최적화

### 서버 측

**1. GPU 메모리 최적화**:
```yaml
# docker-compose.yml
environment:
  - GPU_MEMORY_UTILIZATION=0.9  # 고성능 GPU의 경우
  - MAX_CONCURRENCY=20          # GPU 메모리에 따라 조정
```

**2. 동시 처리 워커 증가**:
```yaml
# docker-compose.yml
environment:
  - NUM_WORKERS=64  # CPU 코어 수에 맞춰 조정
```

### 클라이언트 측

**1. 병렬 처리**:
```python
from concurrent.futures import ThreadPoolExecutor
from remote_ocr_client import RemoteOCRClient

client = RemoteOCRClient(server_url='https://your-domain.com')

files = ['file1.pdf', 'file2.pdf', 'file3.pdf']

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(client.process_file, f) for f in files]
    results = [f.result() for f in futures]
```

**2. 배치 사이즈 조정**:
```bash
# 대량 파일을 작은 배치로 나누어 처리
find data/ -name "*.pdf" | head -10 | xargs python remote_ocr_client.py --server ... --file
```

---

## 모니터링

### 서버 리소스 모니터링

**GPU 사용률**:
```bash
watch -n 1 nvidia-smi
```

**컨테이너 리소스**:
```bash
docker stats deepseek-ocr-vllm
```

**로그 모니터링**:
```bash
tail -f remote_ocr_client.log  # 클라이언트
docker-compose logs -f --tail=100 deepseek-ocr  # 서버
```

---

## 요약

### 서버 설정 체크리스트

- [ ] Docker 및 NVIDIA Container Toolkit 설치
- [ ] 모델 다운로드 (models/deepseek-ai/DeepSeek-OCR)
- [ ] docker-compose.yml 설정 확인
- [ ] Docker 컨테이너 실행 (`docker-compose up -d`)
- [ ] 방화벽 포트 개방 또는 Nginx 설정
- [ ] SSL 인증서 설치 (선택사항)
- [ ] API 키 인증 설정 (선택사항)
- [ ] Health check 확인 (`curl /health`)

### 클라이언트 사용 체크리스트

- [ ] Python 및 의존성 패키지 설치
- [ ] remote_config.yaml 생성 및 설정
- [ ] 서버 연결 테스트
- [ ] 샘플 파일로 테스트
- [ ] 결과 확인

---

## 추가 리소스

- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
- [DeepSeek-OCR GitHub](https://github.com/deepseek-ai/DeepSeek-OCR)

---

**문제가 발생하면 로그를 확인하세요**:
- 클라이언트: `remote_ocr_client.log`
- 서버: `docker-compose logs -f deepseek-ocr`
