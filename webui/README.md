# DeepSeek-OCR Web UI

로컬 PC에서 실행하여 원격 DeepSeek-OCR API 서버를 브라우저로 사용하는 독립형 Web UI입니다.

## 🚀 빠른 시작

```bash
# 기본 실행 (localhost:8000 API 사용)
python webui_standalone.py

# 원격 서버 지정
python webui_standalone.py --server http://YOUR_SERVER_IP:8000

# 포트 변경
python webui_standalone.py --port 9000
```

브라우저가 자동으로 열립니다: `http://localhost:8080`

## 📖 상세 가이드

자세한 사용법은 [WEBUI_STANDALONE_GUIDE.md](WEBUI_STANDALONE_GUIDE.md)를 참고하세요.

## 💡 주요 기능

- ✅ **드래그 앤 드롭** 파일 업로드
- ✅ **실시간 진행 상황** 표시
- ✅ **커스텀 프롬프트** 지원
- ✅ **ZIP 다운로드** 로 결과 수신
- ✅ **원격 서버 연결** 지원

## 🔧 요구사항

```bash
pip install fastapi uvicorn requests python-multipart
```

## 📊 사용 흐름

```
1. 원격 서버에서 Docker API 실행
   └─> docker-compose up -d

2. 로컬 PC에서 Web UI 실행
   └─> python webui_standalone.py --server http://server:8000

3. 브라우저에서 파일 업로드 및 처리
   └─> http://localhost:8080

4. 결과 ZIP 다운로드
```

## 🌐 원격 서버 설정

원격 서버 설정은 상위 디렉토리의 [REMOTE_SERVER_GUIDE.md](../REMOTE_SERVER_GUIDE.md)를 참고하세요.
