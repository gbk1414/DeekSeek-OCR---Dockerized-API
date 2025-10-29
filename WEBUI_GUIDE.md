# DeepSeek-OCR Web UI 사용 가이드

이 가이드는 DeepSeek-OCR Web UI를 사용하여 브라우저에서 직접 파일을 업로드하고 OCR 처리 결과를 다운로드하는 방법을 설명합니다.

---

## 📋 목차

1. [Web UI 특징](#web-ui-특징)
2. [시작하기](#시작하기)
3. [사용 방법](#사용-방법)
4. [고급 설정](#고급-설정)
5. [문제 해결](#문제-해결)

---

## Web UI 특징

### 주요 기능

✅ **드래그 앤 드롭 업로드**
- 여러 파일을 한 번에 업로드 가능
- PDF, JPG, PNG 등 다양한 형식 지원

✅ **배치 OCR 처리**
- 업로드된 모든 파일을 자동으로 순차 처리
- 실시간 진행 상황 표시

✅ **커스텀 프롬프트**
- 원하는 OCR 처리 방식 지정 가능
- 마크다운 변환, 일반 OCR 등 선택 가능

✅ **ZIP 다운로드**
- 처리 완료 후 모든 결과를 하나의 ZIP 파일로 다운로드
- 각 파일은 마크다운(.md) 형식으로 저장

✅ **사용자 친화적 인터페이스**
- 직관적인 UI
- 한국어 지원
- 실시간 진행률 표시

---

## 시작하기

### 1. Docker 컨테이너 실행 (Web UI 모드)

#### Option A: docker-compose 사용 (권장)

```bash
# Web UI 전용 docker-compose 파일 사용
docker-compose -f docker-compose-webui.yml up -d

# 로그 확인
docker-compose -f docker-compose-webui.yml logs -f
```

#### Option B: 기존 docker-compose.yml 수정

```yaml
# docker-compose.yml
services:
  deepseek-ocr:
    # ... 기존 설정
    environment:
      - SERVER_MODE=webui  # 이 줄 추가
      # ... 나머지 환경 변수
    volumes:
      - ./webui_uploads:/app/webui_uploads  # 업로드 디렉토리 추가
      - ./webui_results:/app/webui_results  # 결과 디렉토리 추가
```

```bash
docker-compose up -d
```

#### Option C: Docker run 직접 실행

```bash
docker run -d \
  --name deepseek-ocr-webui \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/webui_uploads:/app/webui_uploads \
  -v $(pwd)/webui_results:/app/webui_results \
  -e SERVER_MODE=webui \
  -e MODEL_PATH=/app/models/deepseek-ai/DeepSeek-OCR \
  -e MAX_CONCURRENCY=5 \
  deepseek-ocr
```

### 2. Web UI 접속

브라우저에서 다음 주소로 접속:

```
http://localhost:8001
```

또는 원격 서버의 경우:

```
http://YOUR_SERVER_IP:8001
```

**참고**:
- API 모드는 8000 포트 사용
- Web UI 모드는 8001 포트 사용

---

## 사용 방법

### 기본 사용 순서

#### 1단계: 파일 업로드

**방법 1: 드래그 앤 드롭**
1. 처리할 PDF 또는 이미지 파일을 준비
2. 파일을 브라우저의 업로드 영역으로 드래그
3. 놓으면 자동으로 파일 목록에 추가됨

**방법 2: 파일 선택**
1. 업로드 영역 클릭
2. 파일 선택 대화상자에서 파일 선택 (여러 파일 동시 선택 가능)
3. 확인 버튼 클릭

#### 2단계: 프롬프트 설정 (선택사항)

기본 프롬프트는 마크다운 변환입니다. 원하는 경우 프롬프트를 변경할 수 있습니다:

**일반 마크다운 변환 (기본값)**:
```
<image>
<|grounding|>Convert the document to markdown.
```

**일반 OCR (구조 없이 텍스트만)**:
```
<image>
Free OCR.
```

**이미지 OCR**:
```
<image>
<|grounding|>OCR this image.
```

**표 추출**:
```
<image>
<|grounding|>Extract all tables as markdown.
```

#### 3단계: OCR 처리 시작

1. "OCR 처리 시작" 버튼 클릭
2. 진행 상황 확인:
   - 진행률 바로 전체 진행도 확인
   - 현재 처리 중인 파일명 표시
   - 처리된 파일 수 / 전체 파일 수 표시

#### 4단계: 결과 다운로드

1. 처리 완료 후 "결과 다운로드 (ZIP)" 버튼 표시
2. 버튼 클릭하여 ZIP 파일 다운로드
3. ZIP 파일 압축 해제하면 각 파일의 OCR 결과(.md 파일) 확인 가능

---

## 고급 설정

### 여러 파일 처리 예제

#### 예제 1: 논문 PDF 처리

```
1. 논문 PDF 파일 3개 업로드
2. 프롬프트: <image>\n<|grounding|>Convert the document to markdown.
3. 처리 시작
4. 결과: paper1.md, paper2.md, paper3.md가 포함된 ZIP 다운로드
```

#### 예제 2: 영수증 이미지 OCR

```
1. 영수증 이미지 10개 업로드
2. 프롬프트: <image>\nFree OCR.
3. 처리 시작
4. 결과: 각 영수증의 텍스트가 추출된 .md 파일들이 ZIP으로 제공
```

#### 예제 3: 표가 많은 문서

```
1. 표가 포함된 PDF 업로드
2. 프롬프트: <image>\n<|grounding|>Extract all tables as markdown.
3. 처리 시작
4. 결과: 표가 마크다운 형식으로 변환된 파일 다운로드
```

### 성능 최적화

**대량 파일 처리 시**:

1. **GPU 메모리 설정 조정**:
```yaml
# docker-compose-webui.yml
environment:
  - MAX_CONCURRENCY=10  # 동시 처리 증가
  - GPU_MEMORY_UTILIZATION=0.9  # GPU 메모리 사용률 증가
```

2. **배치 크기 조정**:
- 한 번에 너무 많은 파일(50개 이상)을 업로드하지 말고 여러 번에 나누어 처리
- 큰 PDF는 페이지 수가 많을 경우 시간이 오래 걸릴 수 있음

3. **타임아웃 설정**:
```yaml
# nginx.conf (리버스 프록시 사용 시)
proxy_read_timeout 600s;
proxy_connect_timeout 600s;
```

---

## 원격 서버에서 사용

### Nginx 리버스 프록시 설정

**파일 업로드 크기 제한 증가**:

```nginx
# /etc/nginx/sites-available/deepseek-ocr
server {
    listen 80;
    server_name your-domain.com;

    # 업로드 크기 제한 증가 (대용량 PDF용)
    client_max_body_size 500M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # 타임아웃 설정 (OCR 처리 시간 고려)
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;

        # 버퍼 설정
        proxy_buffering off;
    }
}
```

### HTTPS 설정

```bash
# Let's Encrypt SSL 인증서 설치
sudo certbot --nginx -d your-domain.com

# 이제 https://your-domain.com 으로 접속 가능
```

---

## 문제 해결

### 일반적인 문제

#### 1. 파일 업로드 실패

**증상**: 파일 업로드 시 오류 발생

**해결**:
```bash
# 파일 크기 확인 (기본 제한: 100MB)
# docker-compose-webui.yml에서 조정 가능하나, Nginx 사용 시 Nginx 설정도 확인

# 지원되는 파일 형식 확인
지원 형식: .pdf, .jpg, .jpeg, .png, .bmp, .tiff, .webp
```

#### 2. 처리 중 멈춤

**증상**: 진행률이 특정 파일에서 멈춤

**해결**:
```bash
# 컨테이너 로그 확인
docker-compose -f docker-compose-webui.yml logs -f

# GPU 메모리 확인
nvidia-smi

# 컨테이너 재시작
docker-compose -f docker-compose-webui.yml restart
```

#### 3. ZIP 다운로드 실패

**증상**: 다운로드 버튼 클릭 시 오류

**해결**:
```bash
# 결과 디렉토리 권한 확인
ls -la webui_results/

# 디렉토리가 없으면 생성
mkdir -p webui_results

# 컨테이너 내부 확인
docker exec -it deepseek-ocr-webui ls -la /app/webui_results/
```

#### 4. 메모리 부족 오류

**증상**: 대량 파일 처리 시 실패

**해결**:
```yaml
# docker-compose-webui.yml
environment:
  - MAX_CONCURRENCY=3  # 동시 처리 수 감소
  - GPU_MEMORY_UTILIZATION=0.7  # GPU 메모리 사용률 감소
```

```bash
# 컨테이너 재시작
docker-compose -f docker-compose-webui.yml down
docker-compose -f docker-compose-webui.yml up -d
```

#### 5. Web UI가 표시되지 않음

**증상**: 브라우저에서 접속 시 연결 실패

**해결**:
```bash
# 컨테이너 상태 확인
docker-compose -f docker-compose-webui.yml ps

# 포트 바인딩 확인
docker-compose -f docker-compose-webui.yml port deepseek-ocr-webui 8000

# 방화벽 확인
sudo ufw allow 8000/tcp

# 로그 확인
docker-compose -f docker-compose-webui.yml logs -f
```

### 디버깅 팁

**1. 브라우저 개발자 도구 확인**:
- F12 키를 눌러 개발자 도구 열기
- Console 탭에서 JavaScript 오류 확인
- Network 탭에서 API 요청/응답 확인

**2. 컨테이너 내부 확인**:
```bash
# 컨테이너 접속
docker exec -it deepseek-ocr-webui bash

# 업로드 디렉토리 확인
ls -la /app/webui_uploads/

# 결과 디렉토리 확인
ls -la /app/webui_results/

# 프로세스 확인
ps aux | grep python
```

**3. 로그 모니터링**:
```bash
# 실시간 로그 확인
docker-compose -f docker-compose-webui.yml logs -f --tail=100
```

---

## API 모드와 Web UI 모드 비교

| 기능 | API 모드 | Web UI 모드 |
|------|----------|-------------|
| **사용 방법** | curl, Python 클라이언트 | 브라우저 |
| **파일 업로드** | 수동 (코드 필요) | 드래그 앤 드롭 |
| **배치 처리** | 직접 구현 필요 | 자동 처리 |
| **결과 다운로드** | API 응답으로 수신 | ZIP 파일 |
| **진행 상황** | 수동 폴링 | 실시간 표시 |
| **적합한 사용자** | 개발자, 자동화 | 일반 사용자 |

### 모드 전환

**API 모드로 전환**:
```bash
# docker-compose.yml의 SERVER_MODE 제거 또는 주석 처리
docker-compose up -d
```

**Web UI 모드로 전환**:
```bash
# docker-compose-webui.yml 사용
docker-compose -f docker-compose-webui.yml up -d
```

**두 모드 동시 실행** (권장하지 않음 - GPU 메모리 제약):
```bash
# 포트를 다르게 설정하여 실행
# API: 포트 8000
# Web UI: 포트 8001
```

---

## 보안 고려사항

### 1. 파일 자동 삭제

Web UI는 24시간 이상 된 업로드/결과 파일을 자동으로 삭제합니다.

### 2. 업로드 제한

대량 업로드를 방지하기 위해 Nginx에서 rate limiting 설정:

```nginx
# /etc/nginx/nginx.conf
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=10r/m;

# /etc/nginx/sites-available/deepseek-ocr
location /webui/process {
    limit_req zone=upload_limit burst=5;
    # ... 나머지 설정
}
```

### 3. 인증 추가 (선택사항)

간단한 Basic Auth 추가:

```nginx
# /etc/nginx/sites-available/deepseek-ocr
location / {
    auth_basic "DeepSeek-OCR Web UI";
    auth_basic_user_file /etc/nginx/.htpasswd;
    # ... 나머지 설정
}
```

```bash
# .htpasswd 파일 생성
sudo htpasswd -c /etc/nginx/.htpasswd username
```

---

## 요약

### Web UI 사용 체크리스트

- [ ] Docker 컨테이너를 Web UI 모드로 실행
- [ ] 브라우저에서 http://localhost:8000 접속
- [ ] 파일을 드래그 앤 드롭으로 업로드
- [ ] 필요시 커스텀 프롬프트 입력
- [ ] "OCR 처리 시작" 버튼 클릭
- [ ] 진행 상황 확인
- [ ] 처리 완료 후 ZIP 파일 다운로드
- [ ] ZIP 압축 해제하여 결과 확인

### 주요 명령어

```bash
# Web UI 시작
docker-compose -f docker-compose-webui.yml up -d

# 로그 확인
docker-compose -f docker-compose-webui.yml logs -f

# 재시작
docker-compose -f docker-compose-webui.yml restart

# 중지
docker-compose -f docker-compose-webui.yml down

# GPU 사용률 확인
nvidia-smi
```

---

## 추가 리소스

- [README.md](README.md) - 프로젝트 전체 개요
- [REMOTE_SERVER_GUIDE.md](REMOTE_SERVER_GUIDE.md) - 원격 서버 설정
- [DOCKER_README.md](DOCKER_README.md) - Docker 설정 상세

**문제가 발생하면**:
1. 컨테이너 로그 확인: `docker-compose -f docker-compose-webui.yml logs -f`
2. 브라우저 개발자 도구 확인 (F12)
3. GPU 메모리 확인: `nvidia-smi`
