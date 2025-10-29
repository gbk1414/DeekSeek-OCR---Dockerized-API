# Web UI Standalone 사용 가이드

로컬 PC에서 실행하는 독립형 Web UI로 원격 DeepSeek-OCR API 서버를 브라우저로 편리하게 사용할 수 있습니다.

---

## 📋 개요

### 아키텍처

```
┌─────────────────────┐                    ┌──────────────────────┐
│   로컬 PC           │                    │   원격 서버 (Docker)  │
│                     │                    │                      │
│  ┌───────────────┐  │                    │  ┌────────────────┐  │
│  │  브라우저      │  │                    │  │  start_server  │  │
│  │  (Web UI)     │  │                    │  │  (API Server)  │  │
│  └───────┬───────┘  │                    │  └───────┬────────┘  │
│          │          │                    │          │           │
│  ┌───────▼───────┐  │   HTTP Requests    │  ┌───────▼────────┐  │
│  │ webui_        │  ├───────────────────>│  │  /ocr/image   │  │
│  │ standalone.py │  │   (파일 업로드)     │  │  /ocr/pdf     │  │
│  └───────────────┘  │                    │  │  /health      │  │
│   localhost:8080    │                    │  └───────────────┘  │
└─────────────────────┘                    │   port 8000         │
                                           └──────────────────────┘
```

---

## 🚀 빠른 시작

### 1. 원격 서버에 API 띄우기

```bash
# 원격 서버에서
cd DeekSeek-OCR-Dockerized-API
docker-compose up -d

# API 확인
curl http://localhost:8000/health
```

### 2. 로컬 PC에서 Web UI 실행

```bash
# 로컬 PC에서
cd DeekSeek-OCR-Dockerized-API

# 기본 실행 (localhost:8000 API 서버 사용)
python webui_standalone.py

# 원격 서버 지정
python webui_standalone.py --server http://YOUR_SERVER_IP:8000

# 포트 변경
python webui_standalone.py --server http://YOUR_SERVER_IP:8000 --port 9000

# 브라우저 자동 열기 비활성화
python webui_standalone.py --no-browser
```

### 3. 브라우저에서 사용

자동으로 브라우저가 열립니다:
```
http://localhost:8080
```

---

## ⚙️ 설정 옵션

### 명령줄 옵션

| 옵션 | 짧은 형식 | 기본값 | 설명 |
|------|----------|--------|------|
| `--server` | `-s` | `http://localhost:8000` | API 서버 URL |
| `--port` | `-p` | `8080` | 로컬 Web UI 포트 |
| `--no-browser` | - | False | 브라우저 자동 열기 비활성화 |

### 환경 변수

```bash
# API 서버 URL 환경 변수로 설정
export DEEPSEEK_OCR_SERVER=http://your-server.com:8000
python webui_standalone.py
```

---

## 📖 사용 예제

### 예제 1: 로컬 Docker API 사용

```bash
# 1. 로컬에서 Docker API 실행
docker-compose up -d

# 2. Web UI 실행 (기본 localhost:8000)
python webui_standalone.py

# 브라우저 자동 열림: http://localhost:8080
```

### 예제 2: 원격 서버 API 사용

```bash
# 원격 서버가 https://ocr.company.com 에 있는 경우
python webui_standalone.py --server https://ocr.company.com

# 또는 IP 주소로
python webui_standalone.py --server http://192.168.1.100:8000
```

### 예제 3: 팀 환경 설정

**서버 관리자**:
```bash
# 서버에 API 배포
docker-compose up -d

# 방화벽 포트 개방
sudo ufw allow 8000/tcp
```

**팀원들** (각자 로컬 PC에서):
```bash
# 설정 파일 생성
echo "export DEEPSEEK_OCR_SERVER=http://team-server:8000" >> ~/.bashrc
source ~/.bashrc

# Web UI 실행
python webui_standalone.py

# 이제 모두가 같은 서버를 사용하면서 각자 브라우저로 작업
```

---

## 🔧 기능

### 파일 업로드
- **드래그 앤 드롭** 지원
- **다중 파일 선택** 가능
- 지원 형식: PDF, JPG, PNG, BMP, TIFF, WEBP

### 커스텀 프롬프트
- 마크다운 변환: `<image>\n<|grounding|>Convert the document to markdown.`
- 일반 OCR: `<image>\nFree OCR.`
- 표 추출: `<image>\n<|grounding|>Extract all tables as markdown.`

### 실시간 진행 상황
- 진행률 표시
- 현재 처리 중인 파일명 표시
- 성공/실패 카운트

### 결과 다운로드
- 모든 결과를 하나의 ZIP 파일로 다운로드
- 각 파일은 .md (마크다운) 형식

---

## 🔒 보안 고려사항

### 로컬 네트워크에서만 사용

기본적으로 `0.0.0.0`으로 바인딩되어 같은 네트워크의 다른 PC에서도 접근 가능합니다.

**로컬에서만 사용하려면**:
```python
# webui_standalone.py 수정
uvicorn.run(
    app,
    host="127.0.0.1",  # localhost만 허용
    port=args.port,
)
```

### HTTPS 사용 (원격 서버)

원격 서버는 HTTPS를 사용하는 것을 권장합니다:

```bash
# Nginx + Let's Encrypt 사용
sudo certbot --nginx -d your-domain.com

# Web UI에서 사용
python webui_standalone.py --server https://your-domain.com
```

---

## 🐛 문제 해결

### 1. API 서버 연결 실패

**증상**: Web UI에서 "❌ API 서버 연결 실패" 표시

**해결**:
```bash
# API 서버가 실행 중인지 확인
curl http://YOUR_SERVER_IP:8000/health

# 방화벽 확인
sudo ufw status
sudo ufw allow 8000/tcp

# Docker 컨테이너 확인
docker-compose ps
docker-compose logs -f
```

### 2. 포트 충돌

**증상**: `Address already in use`

**해결**:
```bash
# 다른 포트 사용
python webui_standalone.py --port 9000

# 또는 기존 프로세스 종료
lsof -ti:8080 | xargs kill -9
```

### 3. 파일 업로드 실패

**증상**: 업로드 시 오류 발생

**해결**:
```bash
# 임시 디렉토리 권한 확인
ls -la /tmp/deepseek_ocr_webui/

# 디스크 공간 확인
df -h

# 로그 확인 (webui_standalone.py 실행 중인 터미널)
```

### 4. 처리 속도가 느림

**원인**: 네트워크 속도, 서버 부하

**해결**:
- 큰 파일은 여러 번에 나눠서 처리
- 네트워크 연결 확인
- 서버 GPU 사용률 확인 (`nvidia-smi`)

---

## 💡 팁

### 1. 여러 서버 사용

서버별로 별칭 만들기:

```bash
# ~/.bashrc 또는 ~/.zshrc
alias ocr-local="python webui_standalone.py --server http://localhost:8000"
alias ocr-prod="python webui_standalone.py --server https://ocr.company.com"
alias ocr-dev="python webui_standalone.py --server http://192.168.1.100:8000"

# 사용
ocr-prod  # 운영 서버 사용
ocr-dev   # 개발 서버 사용
```

### 2. 백그라운드 실행

```bash
# nohup으로 백그라운드 실행
nohup python webui_standalone.py --server http://remote-server:8000 --no-browser > webui.log 2>&1 &

# 나중에 브라우저에서 http://localhost:8080 접속
```

### 3. 자동 시작 (macOS/Linux)

**systemd 서비스** (Linux):
```ini
# /etc/systemd/system/deepseek-webui.service
[Unit]
Description=DeepSeek OCR Web UI
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/DeekSeek-OCR-Dockerized-API
ExecStart=/usr/bin/python3 webui_standalone.py --server http://your-server:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable deepseek-webui
sudo systemctl start deepseek-webui
```

### 4. Docker로 Web UI 실행 (선택사항)

Web UI도 Docker로 실행할 수 있습니다:

```dockerfile
# Dockerfile.webui
FROM python:3.9-slim
WORKDIR /app
COPY webui_standalone.py .
RUN pip install fastapi uvicorn requests python-multipart
CMD ["python", "webui_standalone.py", "--server", "http://api-server:8000", "--port", "8080"]
```

```bash
docker build -f Dockerfile.webui -t deepseek-webui .
docker run -p 8080:8080 deepseek-webui
```

---

## 📊 성능 비교

| 항목 | Web UI Standalone | 직접 API 호출 | 기존 webui.py (통합) |
|------|-------------------|---------------|----------------------|
| **서버 부하** | 낮음 (파일만 전송) | 낮음 | 높음 (파일 저장+처리) |
| **사용 편의성** | ★★★★★ | ★★☆☆☆ | ★★★★★ |
| **네트워크 효율** | 높음 | 높음 | 중간 |
| **유지보수** | 쉬움 (HTML 수정 즉시 반영) | N/A | 어려움 (Docker 재빌드) |
| **다중 사용자** | 각자 로컬 실행 | 각자 구현 | 서버에서 처리 |

---

## 🎯 요약

### 서버 설정 (1회만)
1. Docker로 API 서버 실행: `docker-compose up -d`
2. 방화벽 포트 개방: `sudo ufw allow 8000/tcp`

### 로컬 사용 (매번)
1. Web UI 실행: `python webui_standalone.py --server http://SERVER_IP:8000`
2. 브라우저에서 파일 업로드 및 처리
3. 결과 ZIP 다운로드

### 장점
- ✅ 서버는 가볍게 (API만 제공)
- ✅ 로컬은 편리하게 (브라우저 UI)
- ✅ 개발이 쉬움 (HTML 수정 즉시 반영)
- ✅ 팀 공유 가능 (모두가 같은 API 서버 사용)

---

## 📚 관련 문서

- [README.md](README.md) - 프로젝트 전체 개요
- [REMOTE_SERVER_GUIDE.md](REMOTE_SERVER_GUIDE.md) - 원격 서버 설정 상세
- [CLAUDE.md](CLAUDE.md) - 개발자 가이드
